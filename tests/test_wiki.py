"""Wiki 客户端:登录、批量读取、csrf token 缓存与 badtoken 重试,全部离线。"""

import json
from typing import Any
from urllib.parse import parse_qs

import httpx2
import pytest

from ptilopsis.utils.wiki import READ_CHUNK, Wiki, WikiError

pytestmark = pytest.mark.anyio

API = "https://wiki.example/api.php"


class FakeMediaWiki:
    """能应付登录、tokens、titles 查询与 edit 的最小 MediaWiki。"""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requests: list[dict[str, str]] = []
        self.token_serial = 0
        self.edits: list[dict[str, str]] = []
        self.reject_tokens: set[str] = set()
        self.error: dict[str, str] | None = None
        """设置后所有 edit 都返回这个错误。"""

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        params = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}
        if request.method == "POST":
            params |= {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.requests.append(params)
        return httpx2.Response(200, content=json.dumps(self.handle(params)).encode())

    def handle(self, p: dict[str, str]) -> Any:
        action = p["action"]
        if action == "query" and p.get("meta") == "tokens":
            if p.get("type") == "login":
                return {"query": {"tokens": {"logintoken": "LOGIN"}}}
            self.token_serial += 1
            return {"query": {"tokens": {"csrftoken": f"CSRF{self.token_serial}"}}}
        if action == "login":
            ok = p["lgpassword"] == "secret" and p["lgtoken"] == "LOGIN"
            return {
                "login": {"result": "Success"}
                if ok
                else {"result": "Failed", "reason": "Incorrect password"}
            }
        if action == "query" and "titles" in p:
            return self.query_pages(p["titles"].split("|"))
        if action == "edit":
            if self.error is not None:
                return {"error": self.error}
            if p["token"] in self.reject_tokens:
                return {"error": {"code": "badtoken", "info": "Invalid CSRF token."}}
            self.edits.append(p)
            return {"edit": {"result": "Success", "title": p["title"]}}
        raise AssertionError(p)

    def query_pages(self, titles: list[str]) -> Any:
        pages: dict[str, Any] = {}
        normalized = []
        for i, title in enumerate(titles):
            canonical = title.replace("_", " ")
            if canonical != title:
                normalized.append({"from": title, "to": canonical})
            if canonical not in self.pages:
                pages[str(-(i + 1))] = {"title": canonical, "missing": ""}
                continue
            page: dict[str, Any] = {"pageid": i + 1, "title": canonical}
            # 用 None 模拟超出结果大小上限、内容被截掉的页面(只在批量请求里发生)
            if self.pages[canonical] is not None or len(titles) == 1:
                page["revisions"] = [{"*": self.pages[canonical] or "single"}]
            pages[str(i + 1)] = page
        return {"query": {"normalized": normalized, "pages": pages}}


def make_wiki(pages: dict[str, Any], mode: str = "product") -> tuple[Wiki, Any]:
    server = FakeMediaWiki(pages)
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(server))
    return Wiki(API, mode, client=http), server


async def test_login_success_and_failure() -> None:
    server = FakeMediaWiki({})
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(server))
    wiki = await Wiki.login(API, "bot", "secret", client=http)
    assert isinstance(wiki, Wiki)
    assert [r["action"] for r in server.requests] == ["query", "login"]

    http = httpx2.AsyncClient(transport=httpx2.MockTransport(server))
    with pytest.raises(RuntimeError, match="Incorrect password"):
        await Wiki.login(API, "bot", "wrong", client=http)


async def test_read_single_page_and_missing() -> None:
    wiki, _ = make_wiki({"阿米娅": "text"})
    assert await wiki.read("阿米娅") == "text"
    with pytest.raises(KeyError):
        await wiki.read("不存在")


async def test_read_many_batches_titles_and_maps_normalized_names() -> None:
    pages = {f"干员{i}": f"text{i}" for i in range(READ_CHUNK + 5)}
    pages["Some Page"] = "spaced"
    wiki, server = make_wiki(pages)

    titles = [*pages, "Some_Page", "缺失的页面"]
    got = await wiki.read_many(titles)

    assert got == {**pages, "Some_Page": "spaced"}
    # 55 + 2 个标题分两批;缺失页面被省略,不再单独请求
    assert len(server.requests) == 2
    assert len(server.requests[0]["titles"].split("|")) == READ_CHUNK


async def test_read_many_refetches_truncated_pages_individually() -> None:
    wiki, server = make_wiki({"a": "A", "b": None, "c": "C"})
    got = await wiki.read_many(["a", "b", "c"])
    assert got == {"a": "A", "b": "single", "c": "C"}
    assert [r["titles"] for r in server.requests] == ["a|b|c", "b"]


async def test_edit_caches_csrf_token_and_retries_on_badtoken() -> None:
    wiki, server = make_wiki({})
    await wiki.edit(title="页面", text="1", summary="s", minor=True, bot=None)
    await wiki.edit(title="页面", text="2", summary="s", createonly="1")
    # 两次编辑只取一次 token
    assert sum(1 for r in server.requests if r.get("meta") == "tokens") == 1
    assert server.edits[0]["token"] == "CSRF1"
    assert server.edits[0]["minor"] == "1" and "bot" not in server.edits[0]
    assert server.edits[1]["bot"] == "1" and server.edits[1]["createonly"] == "1"

    # token 失效:刷新后重试一次成功
    server.reject_tokens.add("CSRF1")
    await wiki.edit(title="页面", text="3")
    assert server.edits[-1]["token"] == "CSRF2"

    # 其它错误直接抛出
    server.error = {"code": "protectedpage", "info": "This page is protected."}
    with pytest.raises(WikiError, match="protectedpage"):
        await wiki.edit(title="页面", text="4")


async def test_dev_mode_does_not_write() -> None:
    wiki, server = make_wiki({}, mode="dev")
    assert await wiki.edit(title="页面", text="1") is None
    assert await wiki.protect(title="页面", protections="edit=sysop") is None
    assert server.requests == []
