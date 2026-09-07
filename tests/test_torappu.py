"""torappu 客户端:URL 编码、版本挑选、404 处理与目录遍历,全部离线。"""

import json
from typing import Any

import pytest
import requests

from ptilopsis.utils.torappu import READY_MARKER, TorappuClient, TorappuVersion

BASE = "https://torappu.example"
V = "26-09-03-04-06-00_ed95a2"


class FakeResponse:
    def __init__(self, status: int, body: Any = b"") -> None:
        self.status_code = status
        if isinstance(body, bytes):
            self.content = body
        else:
            self.content = json.dumps(body).encode("utf-8")

    def json(self) -> Any:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """按完整 URL 路由的假 Session,记录所有请求。"""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str]] = []

    def _resolve(self, method: str, url: str) -> FakeResponse:
        self.calls.append((method, url))
        body = self.routes.get(url)
        if body is None:
            return FakeResponse(404)
        if isinstance(body, FakeResponse):
            return body
        return FakeResponse(200, body)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._resolve("GET", url)

    def head(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._resolve("HEAD", url)


def make_client(routes: dict[str, Any]) -> tuple[TorappuClient, FakeSession]:
    session = FakeSession(routes)
    return TorappuClient(BASE, session=session), session  # type: ignore[arg-type]


def version(id_: int, res: str, ready: bool = True) -> dict[str, Any]:
    return {
        "id": id_,
        "clientVersion": "2.7.71",
        "resVersion": res,
        "isReady": ready,
        "assetMappingStatus": "ready",
    }


def test_gamedata_url_encodes_brackets_but_keeps_slashes() -> None:
    client, _ = make_client({})
    url = client.gamedata_url(V, "story/[uc]info/obt/memory/story_demkni_1_1.txt")
    assert url == (
        f"{BASE}/gamedata/{V}/story/%5Buc%5Dinfo/obt/memory/story_demkni_1_1.txt"
    )


def test_files_url_encodes_whole_path_as_one_segment() -> None:
    client, _ = make_client({})
    url = client.files_url(f"gamedata/{V}/story/[uc]info")
    assert url == f"{BASE}/api/v1/files/gamedata%2F{V}%2Fstory%2F%5Buc%5Dinfo"


def test_fetch_returns_bytes_and_404_becomes_file_not_found() -> None:
    client, session = make_client(
        {f"{BASE}/gamedata/{V}/excel/item_table.json": b'{"items": {}}'}
    )
    assert client.fetch(V, "excel/item_table.json") == b'{"items": {}}'
    with pytest.raises(FileNotFoundError):
        client.fetch(V, "excel/nope.json")
    # 404 不重试
    assert session.calls.count(("GET", f"{BASE}/gamedata/{V}/excel/nope.json")) == 1


def test_list_versions_sorted_by_id() -> None:
    client, _ = make_client(
        {f"{BASE}/api/v1/version": [version(3, "c"), version(1, "a"), version(2, "b")]}
    )
    assert [v.res_version for v in client.list_versions()] == ["a", "b", "c"]
    assert isinstance(client.list_versions()[0], TorappuVersion)


def test_latest_version_skips_versions_without_ready_marker() -> None:
    client, session = make_client(
        {
            f"{BASE}/api/v1/version": [
                version(1, "old"),
                version(2, "ready"),
                version(3, "extracting"),
                version(4, "bundles-pending", ready=False),
            ],
            # 只有 ready 这一版有标记
            f"{BASE}/gamedata/ready/{READY_MARKER}": {"schema_version": 1},
        }
    )
    latest = client.latest_version()
    assert latest.res_version == "ready"
    # isReady=False 的版本连标记都不用查
    assert not any(
        url.startswith(f"{BASE}/gamedata/bundles-pending/") for _, url in session.calls
    )


def test_latest_version_raises_when_nothing_ready() -> None:
    client, _ = make_client({f"{BASE}/api/v1/version": [version(1, "a")]})
    with pytest.raises(RuntimeError, match="no version with ready gamedata"):
        client.latest_version()


def _listing(path: str, children: list[tuple[str, bool]]) -> dict[str, Any]:
    return {
        "dir": {"name": path.rsplit("/", 1)[-1], "path": path, "is_dir": True},
        "children": [
            {
                "name": name,
                "path": f"{path}/{name}",
                "size": 0 if is_dir else 10,
                "is_dir": is_dir,
            }
            for name, is_dir in children
        ],
    }


def _files_route(path: str) -> str:
    return f"{BASE}/api/v1/files/" + f"gamedata/{V}/{path}".replace("/", "%2F")


def test_walk_recurses_into_directories() -> None:
    root = f"gamedata/{V}"
    client, _ = make_client(
        {
            _files_route("levels"): _listing(
                f"{root}/levels", [("obt", True), ("levels_meta.json", False)]
            ),
            _files_route("levels/obt"): _listing(
                f"{root}/levels/obt", [("main", True)]
            ),
            _files_route("levels/obt/main"): _listing(
                f"{root}/levels/obt/main", [("level_main_01-01.json", False)]
            ),
        }
    )
    assert sorted(client.walk(V, "levels")) == [
        "levels/levels_meta.json",
        "levels/obt/main/level_main_01-01.json",
    ]


def test_walk_on_a_file_yields_itself() -> None:
    path = "levels/obt/main/level_main_01-01.json"
    client, _ = make_client(
        {
            # 目录接口对文件报 500
            _files_route(path): FakeResponse(500, {"detail": "not a directory"}),
            f"{BASE}/gamedata/{V}/{path}": b"{}",
        }
    )
    assert list(client.walk(V, path)) == [path]


def test_walk_missing_directory_raises() -> None:
    client, _ = make_client({})
    with pytest.raises(FileNotFoundError):
        list(client.walk(V, "levels/nope"))
