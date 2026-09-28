"""MediaWiki API 客户端(async,httpx2 + HTTP/2)。

用 :meth:`Wiki.login` 构造;所有请求走同一个连接池。读取用
:meth:`Wiki.read`,一次要读很多页面时用 :meth:`Wiki.read_many`,它把标题按
50 个一批合并成一个 ``action=query``;要在读到的版本上改写页面时用
:meth:`Wiki.read_revisions`,它额外带回版本号与时间戳供编辑冲突检测。
csrf token 按会话缓存,只在服务器报 ``badtoken`` 时重新取。编辑类操作用锁
串行,避免并发写页面;登录后还会查询账号适用的写配额并本地限速,撞限时
冷却重试(见 :mod:`ptilopsis.utils.ratelimit`)。
"""

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import anyio
import httpx2
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from ptilopsis.log import logger
from ptilopsis.utils.http import log_retry, make_client
from ptilopsis.utils.ratelimit import (
    DEFAULT_COOLDOWN,
    TokenBucket,
    parse_ratelimits,
)

__all__ = ["PageRevision", "Wiki", "WikiError"]

READ_CHUNK = 50
"""一次 ``action=query`` 里带的标题数;普通用户上限 50,bot 有 apihighlimits 才是 500。"""


class WikiError(RuntimeError):
    """API 返回了 ``error`` 字段。"""

    def __init__(self, code: str, info: str) -> None:
        super().__init__(f"{code}: {info}")
        self.code = code
        self.info = info


@dataclass(frozen=True)
class PageRevision:
    """页面最新版本的快照,:meth:`Wiki.read_revisions` 的结果。"""

    title: str
    """服务器规范化后的标题。"""
    text: str
    revid: int
    timestamp: str
    """该版本的保存时间,改写页面时作为 ``basetimestamp``。"""
    starttimestamp: str
    """读取时的服务器时间,改写页面时作为 ``starttimestamp``。"""
    redirect: bool
    contentmodel: str


def _transient(name: str) -> Any:
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(httpx2.HTTPError),
        before_sleep=log_retry(name),
        reraise=True,
    )


MAX_RETRY_AFTER = 300
"""429 时按 ``Retry-After`` 等待的上限(秒):等更久说明问题不在节奏,直接失败更好。"""


async def _respect_retry_after(resp: httpx2.Response) -> None:
    """HTTP 429(CDN / 反代层限流)时按 ``Retry-After`` 头等待后再重试。

    这和 MediaWiki 自己的配额无关;等待后照常 ``raise_for_status``,抛出的
    异常属于 :class:`httpx2.HTTPError`,会被 ``_transient`` 重试。头缺失或
    不是秒数时按默认冷却处理,过长的值截到上限。
    """
    if resp.status_code != 429:
        return
    try:
        delay = int(resp.headers.get("retry-after", ""))
    except ValueError:
        delay = int(DEFAULT_COOLDOWN)
    delay = min(delay, MAX_RETRY_AFTER)
    if delay > 0:
        logger.warning(f"HTTP 429; sleeping {delay}s before next attempt")
        await anyio.sleep(delay)


class Wiki:
    def __init__(
        self,
        api_url: str,
        mode: str = "product",
        client: httpx2.AsyncClient | None = None,
        rate_safety: float = 0.8,
        write_min_interval: float = 0.0,
    ) -> None:
        self.api_url = api_url
        self.mode = mode
        self.client = client or make_client()
        self._csrf_token: str | None = None
        self._write_lock = anyio.Lock()
        self._rate_safety = rate_safety
        self._write_min_interval = write_min_interval
        self._buckets: dict[str, TokenBucket] = {}
        """登录后发现配额后,每个写动作一个桶;查不到时全是 passthrough。"""
        self._default_bucket = TokenBucket(None, 0.0)
        self._read_bucket = TokenBucket(None, 0.0)
        self._last_write = 0.0

    @classmethod
    async def login(
        cls,
        api_url: str,
        username: str,
        password: str,
        mode: str = "product",
        client: httpx2.AsyncClient | None = None,
        rate_safety: float = 0.8,
        write_min_interval: float = 0.0,
    ) -> "Wiki":
        """登录并返回客户端;登录失败抛 RuntimeError。"""
        wiki = cls(api_url, mode, client, rate_safety, write_min_interval)
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
        await wiki._discover_rate_limits()
        return wiki

    async def aclose(self) -> None:
        await self.client.aclose()

    # ----- 底层请求 -----

    @_transient("wiki.get")
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._read_bucket.acquire()
        resp = await self.client.get(self.api_url, params={"format": "json", **params})
        await _respect_retry_after(resp)
        resp.raise_for_status()
        return resp.json()

    @_transient("wiki.post")
    async def _post(
        self,
        data: dict[str, Any],
        *,
        write_action: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if write_action is not None:
            # 放在 HTTP 重试内部,每次实际写请求都取令牌并更新发送时刻。
            await self._pace_write(write_action)
            self._last_write = time.monotonic()
        resp = await self.client.post(
            self.api_url, data={"format": "json", **data}, **kwargs
        )
        await _respect_retry_after(resp)
        resp.raise_for_status()
        return resp.json()

    async def _discover_rate_limits(self) -> None:
        """登录后查一次当前账号适用的写配额并建桶;查不到就保持不限速。"""
        try:
            res = await self._query({"meta": "userinfo", "uiprop": "ratelimits"})
            limits = parse_ratelimits(res["query"]["userinfo"].get("ratelimits") or {})
        except Exception:
            # 配额只是护栏,查询失败不该挡住任务;真撞了还有 ratelimited 重试兜底
            logger.opt(exception=True).warning(
                "Rate limit discovery failed; writes stay unpaced"
            )
            return
        self._buckets = {
            action: TokenBucket(rl.limit, rl.period, safety=self._rate_safety)
            for action, rl in limits.items()
        }
        if read := limits.get("read"):
            self._read_bucket = TokenBucket(
                read.limit, read.period, safety=self._rate_safety
            )
        detail = (
            ", ".join(
                f"{a} {rl.limit}/{rl.period:g}s" for a, rl in sorted(limits.items())
            )
            or "none (noratelimit?)"
        )
        logger.info(f"Rate limits for this account: {detail}")

    async def _query(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._get({"action": "query", **params})

    async def csrf_token(self, refresh: bool = False) -> str:
        token = None if refresh else self._csrf_token
        if token is None:
            res = await self._query({"meta": "tokens"})
            token = self._csrf_token = res["query"]["tokens"]["csrftoken"]
        return token

    async def _pace_write(self, action: str) -> None:
        """写前限速:取该动作的令牌桶,再保证与上一次写请求的间隔不小于下限。"""
        await self._buckets.get(action, self._default_bucket).acquire()
        if self._write_min_interval > 0:
            delay = self._write_min_interval - (time.monotonic() - self._last_write)
            if delay > 0:
                await anyio.sleep(delay)

    async def _write(self, action: str, data: dict[str, Any], **kwargs: Any) -> Any:
        """带 csrf token 的写操作;token 失效时刷新重试一次,撞限时冷却后重试。"""
        refresh_token = False
        async with self._write_lock:
            for attempt in range(3):
                post_data = {
                    "action": action,
                    "token": await self.csrf_token(refresh=refresh_token),
                    **data,
                }
                res = await self._post(post_data, write_action=action, **kwargs)
                error = res.get("error")
                if error is None:
                    return res
                code = error.get("code", "")
                if code == "badtoken" and attempt < 2:
                    refresh_token = True
                    continue
                if code == "ratelimited" and attempt < 2:
                    bucket = self._buckets.get(action, self._default_bucket)
                    logger.warning(
                        f"Rate limited on {action}; cooling down before retry"
                    )
                    await bucket.cooldown()
                    continue
                raise WikiError(code, error.get("info", ""))
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
        basetimestamp: str | None = None,
        starttimestamp: str | None = None,
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
        :param basetimestamp:所基于版本的时间戳,页面在此之后被改过时报 editconflict。
        :param starttimestamp:开始编辑的时间,页面在此之后被删除时报 pagedeleted。
            两者都取自 :meth:`read_revisions` 的结果。
        :return: API 返回的 JSON;dev 模式下只打印参数并返回 None,
            ``createonly`` 而页面已存在时也返回 None
        """
        args = locals().copy()
        args.pop("self")
        if self.mode != "product":
            logger.info("\n" + str(args) + "\n")
            return None
        boolargs = {"minor", "createonly", "nocreate", "redirect", "bot"}
        try:
            return await self._write("edit", self._form(args, boolargs))
        except WikiError as e:
            # createonly 的本意就是「已存在则不动」,各 job 每次都会对已有页面调用
            if createonly and e.code == "articleexists":
                logger.info(f"Page already exists, skip: {title or pageid}")
                return None
            raise

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

    async def read_revisions(self, titles: Iterable[str]) -> dict[str, PageRevision]:
        """批量读取页面最新版本,返回 ``{标题: PageRevision}``;不存在的页面不在结果里。

        分批、标题映射与截断后单独重读的规则同 :meth:`read_many`,只是多带回
        版本号、时间戳、内容模型和是否为重定向,供改写页面时检测编辑冲突。
        """
        titles = list(dict.fromkeys(titles))
        chunks = [titles[i : i + READ_CHUNK] for i in range(0, len(titles), READ_CHUNK)]
        result: dict[str, PageRevision] = {}
        while chunks:
            chunk = chunks.pop(0)
            requested = set(chunk)
            res = await self._query(
                {
                    "titles": "|".join(chunk),
                    "prop": "revisions|info",
                    "rvprop": "ids|timestamp|content",
                    "curtimestamp": 1,
                }
            )
            query = res["query"]
            aliases: dict[str, list[str]] = {}
            for item in query.get("normalized", []):
                aliases.setdefault(item["to"], []).append(item["from"])
            for page in query.get("pages", {}).values():
                if "missing" in page or "invalid" in page:
                    continue
                title = page["title"]
                keys = [t for t in (title, *aliases.get(title, [])) if t in requested]
                text = self._page_text(page)
                if text is None:
                    if len(chunk) == 1:
                        raise KeyError(title)
                    chunks.extend([key] for key in keys)
                    continue
                revision = page["revisions"][0]
                snapshot = PageRevision(
                    title=title,
                    text=text,
                    revid=revision["revid"],
                    timestamp=revision["timestamp"],
                    starttimestamp=res["curtimestamp"],
                    redirect="redirect" in page,
                    contentmodel=page.get("contentmodel", "wikitext"),
                )
                for key in keys:
                    result[key] = snapshot
        return result

    async def category(self, category: str) -> list[str]:
        CM_LIMIT = 1000  # noqa: N806
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
