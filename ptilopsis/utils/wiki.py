"""MediaWiki API 客户端(async,httpx2 + HTTP/2)。

用 :meth:`Wiki.login` 构造;所有请求走同一个连接池。读取用
:meth:`Wiki.read`,一次要读很多页面时用 :meth:`Wiki.read_many`,它把标题按
50 个一批合并成一个 ``action=query``。csrf token 按会话缓存,只在服务器报
``badtoken`` 时重新取。编辑类操作用锁串行,避免并发写页面。
"""

from collections.abc import Iterable
from typing import Any
from urllib.parse import quote

import anyio
import httpx2
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from ptilopsis.log import logger
from ptilopsis.utils.http import log_retry, make_client

__all__ = ["Wiki", "WikiError"]

READ_CHUNK = 50
"""一次 ``action=query`` 里带的标题数;普通用户上限 50,bot 有 apihighlimits 才是 500。"""


class WikiError(RuntimeError):
    """API 返回了 ``error`` 字段。"""

    def __init__(self, code: str, info: str) -> None:
        super().__init__(f"{code}: {info}")
        self.code = code
        self.info = info


def _transient(name: str) -> Any:
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(httpx2.HTTPError),
        before_sleep=log_retry(name),
        reraise=True,
    )


class Wiki:
    def __init__(
        self,
        api_url: str,
        mode: str = "product",
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        self.api_url = api_url
        self.mode = mode
        self.client = client or make_client()
        self._csrf_token: str | None = None
        self._write_lock = anyio.Lock()

    @classmethod
    async def login(
        cls,
        api_url: str,
        username: str,
        password: str,
        mode: str = "product",
        client: httpx2.AsyncClient | None = None,
    ) -> "Wiki":
        """登录并返回客户端;登录失败抛 RuntimeError。"""
        wiki = cls(api_url, mode, client)
        token = await wiki._query({"meta": "tokens", "type": "login"})
        res = await wiki._post(
            {
                "action": "login",
                "lgname": username,
                "lgpassword": password,
                "lgtoken": token["query"]["tokens"]["logintoken"],
            }
        )
        if res["login"]["result"] != "Success":
            raise RuntimeError(res["login"]["reason"])
        return wiki

    async def aclose(self) -> None:
        await self.client.aclose()

    # ----- 底层请求 -----

    @_transient("wiki.get")
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = await self.client.get(self.api_url, params={"format": "json", **params})
        resp.raise_for_status()
        return resp.json()

    @_transient("wiki.post")
    async def _post(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        resp = await self.client.post(
            self.api_url, data={"format": "json", **data}, **kwargs
        )
        resp.raise_for_status()
        return resp.json()

    async def _query(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get({"action": "query", **params})

    async def csrf_token(self, refresh: bool = False) -> str:
        token = None if refresh else self._csrf_token
        if token is None:
            res = await self._query({"meta": "tokens"})
            token = self._csrf_token = res["query"]["tokens"]["csrftoken"]
        return token

    async def _write(self, action: str, data: dict[str, Any], **kwargs: Any) -> Any:
        """带 csrf token 的写操作;token 失效时刷新后重试一次。"""
        async with self._write_lock:
            for attempt in range(2):
                post_data = {
                    "action": action,
                    "token": await self.csrf_token(refresh=attempt > 0),
                    **data,
                }
                res = await self._post(post_data, **kwargs)
                error = res.get("error")
                if error is None:
                    return res
                if error.get("code") == "badtoken" and attempt == 0:
                    continue
                raise WikiError(error.get("code", ""), error.get("info", ""))
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _form(args: dict[str, Any], boolargs: set[str]) -> dict[str, Any]:
        """把 None 过滤掉,布尔标志按 MediaWiki 的习惯传 ``"1"``。"""
        data: dict[str, Any] = {}
        for key, value in args.items():
            if value is None:
                continue
            if key in boolargs:
                if value:
                    data[key] = "1"
            else:
                data[key] = value
        return data

    # ----- 编辑 -----

    async def edit(
        self,
        title: str | None = None,
        pageid: int | str | None = None,
        section: int | str | None = None,
        sectiontitle: str | None = None,
        text: str | None = None,
        summary: str | None = None,
        minor: bool | None = None,
        # 布尔标志传 None 表示不带这个参数;历史调用里 createonly 也有传 "1" 的
        bot: bool | None = True,
        createonly: bool | str | None = None,
        nocreate: bool | None = None,
        prependtext: str | None = None,
        appendtext: str | None = None,
        redirect: bool | None = None,
        contentformat: str | None = None,
        contentmodel: str | None = None,
    ) -> dict[str, Any] | None:
        """
        :param title: 要编辑的页面标题。不能与pageid一起使用。
        :param pageid:要编辑的页面的页面 ID。不能与title一起使用。
        :param section:段落数。0用于首段，new用于新的段落。NOTICE:会覆盖==xx==的部分
        :param sectiontitle:新段落的标题。
        :param text:页面内容。
        :param summary:编辑摘要。当section=new且未设置sectiontitle时，还包括小节标题。
        :param minor:小编辑。
        :param bot:机器人编辑。
        :param createonly:不要编辑页面，如果已经存在。
        :param nocreate:如果该页面不存在，则抛出一个错误。
        :param prependtext:将该文本添加到该页面的开始。覆盖text。
        :param appendtext:将该文本添加到该页面的结尾。覆盖text。
        :param redirect:自动解决重定向。
        :param contentformat:用于输入文本的内容序列化格式。application/json、
            text/plain、text/css、text/x-wiki、text/javascript
        :param contentmodel:新内容的内容模型。GadgetDefinition、Scribunto、
            sanitized-css、flow-board、wikitext、javascript、json、css、text、smw/schema
        :return: API 返回的 JSON;dev 模式下只打印参数并返回 None
        """
        args = locals().copy()
        args.pop("self")
        if self.mode != "product":
            logger.info("\n" + str(args) + "\n")
            return None
        boolargs = {"minor", "createonly", "nocreate", "redirect", "bot"}
        return await self._write("edit", self._form(args, boolargs))

    async def protect(
        self,
        title: str | None = None,
        pageid: int | str | None = None,
        protections: str | None = None,
        reason: str | None = None,
        cascade: bool | None = None,
    ) -> dict[str, Any] | None:
        """
        :param title:要（解除）保护的页面标题。不能与pageid一起使用。
        :param pageid:要（解除）保护的页面ID。不能与title一起使用。
        :param protections:保护等级列表，格式：action=level（例如edit=sysop）。
            等级all意味着任何人都可以执行操作，也就是说没有限制。
            注意：未列出的操作将移除限制。
        :param reason:（解除）保护的原因。
        :param cascade:启用连锁保护（也就是保护包含于此页面的页面）。
            如果所有提供的保护等级不支持连锁，就将其忽略。
        """
        args = locals().copy()
        args.pop("self")
        if self.mode != "product":
            logger.info("\n" + "\n" + str(args) + "\n")
            return None
        return await self._write(
            "protect", {"expiry": "infinite", **self._form(args, {"cascade"})}
        )

    async def upload(
        self,
        filepath: str,
        filename: str,
        comment: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        """
        :param filepath:文件路径
        :param filename:目标文件名
        :param comment:上传注释。如果没有指定text，那么它也被用于新文件的初始页面文本。
        :param text:用于新文件的初始页面文本。
        """
        content = await anyio.Path(filepath).read_bytes()
        data = self._form(
            {
                "filename": filename,
                "ignorewarnings": "1",
                "comment": comment,
                "text": text,
            },
            set(),
        )
        return await self._write(
            "upload", data, files={"file": (quote(filename), content)}
        )

    # ----- 读取 -----

    @staticmethod
    def _page_text(page: dict[str, Any]) -> str | None:
        revisions = page.get("revisions")
        if not revisions:
            return None
        return revisions[0]["*"]

    async def read(self, title: str) -> str:
        """
        :param title: 名称空间:页面名
        :return: wikitext;页面不存在时抛 KeyError
        """
        res = await self._query(
            {"titles": title, "prop": "revisions", "rvprop": "content"}
        )
        for page in res["query"]["pages"].values():
            text = self._page_text(page)
            if text is None:
                raise KeyError(title)
            return text
        raise KeyError(title)

    async def read_many(self, titles: Iterable[str]) -> dict[str, str]:
        """批量读取,返回 ``{标题: wikitext}``;不存在的页面不在结果里。

        每 :data:`READ_CHUNK` 个标题合并成一个请求。结果按调用方写的标题索引
        (服务器会把下划线、首字母大小写规范化,这里映射回去)。响应超过 API
        大小上限时 MediaWiki 会把部分页面的内容截掉,这些页面再单独读一次。
        """
        titles = list(dict.fromkeys(titles))
        result: dict[str, str] = {}
        for start in range(0, len(titles), READ_CHUNK):
            chunk = titles[start : start + READ_CHUNK]
            requested = set(chunk)
            res = await self._query(
                {
                    "titles": "|".join(chunk),
                    "prop": "revisions",
                    "rvprop": "content",
                }
            )
            query = res["query"]
            aliases: dict[str, list[str]] = {}
            for item in query.get("normalized", []):
                aliases.setdefault(item["to"], []).append(item["from"])
            truncated: list[str] = []
            for page in query.get("pages", {}).values():
                if "missing" in page:
                    continue
                title = page["title"]
                keys = [t for t in (title, *aliases.get(title, [])) if t in requested]
                text = self._page_text(page)
                if text is None:
                    truncated.extend(keys)
                else:
                    for key in keys:
                        result[key] = text
            for title in truncated:
                result[title] = await self.read(title)
        return result

    async def category(self, category: str) -> list[str]:
        CM_LIMIT = 1000
        cat_page_list: list[str] = []
        params: dict[str, Any] = {
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": CM_LIMIT,
            "cmprop": "ids|title|sortkey",
        }
        ret = (await self._query(params))["query"]["categorymembers"]
        cat_page_list.extend(page["title"] for page in ret)

        while len(ret) >= CM_LIMIT:
            cmprefix = ret[-1]["sortkey"]
            ret = (await self._query({**params, "cmstarthexsortkey": cmprefix}))[
                "query"
            ]["categorymembers"]
            cat_page_list.pop()  # 两次查询的头尾会重复，移除其中一个
            cat_page_list.extend(page["title"] for page in ret)
        return cat_page_list
