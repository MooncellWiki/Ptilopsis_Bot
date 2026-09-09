"""把各 job 生成的页面落盘,供重构前后做 diff。

    PYTHONHASHSEED=0 uv run python scripts/parity_jobs.py out/jobs_before
    PYTHONHASHSEED=0 uv run python scripts/parity_jobs.py out/jobs_after \
        --jobs stage.run item.run
    diff -r out/jobs_before out/jobs_after

不登录 wiki:``edit`` / ``protect`` 只记录不提交;``read`` 匿名读取真实页面并缓存到
``.cache/wiki/``,前后两次运行看到的是同一份页面;``category`` 默认返回空列表,
让"只处理尚未建页的条目"这类 job 把所有条目都跑一遍(少数 job 需要真实分类,见
REAL_CATEGORY_JOBS)。

每个 job 用全新的 GameData,避免 job 之间通过共享的表互相污染。
数据按 version_local.json 里的国服版本从 torappu 读取(有本地缓存)。
"""

import argparse
import hashlib
import json
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

import ptilopsis
from ptilopsis.config import config
from ptilopsis.jobs import discover_jobs
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import JobContext, get_job, registered_jobs

ROOT = Path(__file__).resolve().parent.parent
# 缓存与海外服子模块都用主仓库里的那份,worktree 里跑也一样
MAIN_ROOT = Path("/Users/starheart/Documents/PythonWorkspace/Ptilopsis_Bot")
CACHE_ROOT = MAIN_ROOT / ".cache"
YOSTAR_DIR = MAIN_ROOT / "thirdparty" / "ArknightsGameData_YoStar"
WIKI_CACHE = CACHE_ROOT / "wiki"
TORAPPU_CACHE = CACHE_ROOT / "torappu"

REAL_CATEGORY_JOBS = {"enemy.update_immune"}
"""category 返回真实成员的 job(其余返回空列表以覆盖全部条目)。"""

SKIP_JOBS = {"weedy.run"}
"""不读任何 gamedata 且依赖外部服务的 job。"""


def _safe_name(title: str) -> str:
    keep = "".join(c if c.isalnum() or c in "-_.()" else "_" for c in title)
    return keep[:80] + "_" + hashlib.sha1(title.encode()).hexdigest()[:8]


class RecordingWiki:
    def __init__(self, api_url: str) -> None:
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Ptilopsis parity (read only)"
        self.edits: list[dict[str, Any]] = []
        self.real_categories = False

    # ---- 记录 ----

    def edit(self, **kwargs: Any) -> None:
        self.edits.append({k: v for k, v in kwargs.items() if v is not None})

    def protect(self, **kwargs: Any) -> None:
        return None

    def upload(self, *args: Any, **kwargs: Any) -> None:
        return None

    # ---- 匿名读取(带缓存) ----

    @staticmethod
    def _retry(fetch: Callable[[], Any]) -> Any:
        for attempt in range(4):
            try:
                return fetch()
            except requests.RequestException:
                time.sleep(2 * (attempt + 1))
        return fetch()

    def _cached(self, kind: str, key: str, fetch) -> Any:
        path = WIKI_CACHE / kind / (_safe_name(key) + ".json")
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        value = self._retry(fetch)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return value

    def read(self, title: str) -> str:
        def fetch():
            res = self.session.get(
                self.api_url,
                params={
                    "format": "json",
                    "action": "query",
                    "titles": title,
                    "prop": "revisions",
                    "rvprop": "content",
                    "rvslots": "main",
                },
                timeout=60,
            )
            res.raise_for_status()
            pages = res.json()["query"]["pages"]
            page = next(iter(pages.values()))
            if "revisions" not in page:
                return None
            return page["revisions"][0]["slots"]["main"]["*"]

        text = self._cached("read", title, fetch)
        if text is None:
            # 与 Wiki.read 对不存在页面的行为一致:KeyError
            raise KeyError("revisions")
        return text

    def category(self, category: str) -> list[str]:
        if not self.real_categories:
            return []

        def fetch():
            members: list[str] = []
            params = {
                "format": "json",
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": 500,
                "cmprop": "title",
            }
            while True:
                res = self.session.get(self.api_url, params=params, timeout=60)
                res.raise_for_status()
                data = res.json()
                members.extend(p["title"] for p in data["query"]["categorymembers"])
                if "continue" not in data:
                    return members
                params.update(data["continue"])

        return self._cached("category", category, fetch)


def dump_edits(wiki: RecordingWiki, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for edit in wiki.edits:
        title = str(edit.get("title", edit.get("pageid", "?")))
        counts[title] = counts.get(title, 0) + 1
        suffix = "" if counts[title] == 1 else f"__{counts[title]}"
        text = edit.get("text")
        meta = {k: v for k, v in edit.items() if k not in ("text",)}
        body = json.dumps(meta, ensure_ascii=False, sort_keys=True) + "\n"
        if text is not None:
            body += "----\n" + str(text)
        (out_dir / f"{_safe_name(title)}{suffix}.wiki").write_text(
            body, encoding="utf-8"
        )


def run(out_dir: Path, names: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    for name in names:
        job = get_job(name)
        wiki = RecordingWiki(config.api_url)
        wiki.real_categories = name in REAL_CATEGORY_JOBS
        gamedata = GameData(
            config=config, yostar_dir=YOSTAR_DIR, cache_dir=TORAPPU_CACHE
        )
        started = time.time()
        try:
            job.run(JobContext(wiki, gamedata))  # type: ignore[arg-type]
            status[name] = f"ok {len(wiki.edits)} edits {time.time() - started:.0f}s"
        except Exception as exc:
            status[name] = f"FAIL {type(exc).__name__}: {exc}"
            (out_dir / name).mkdir(parents=True, exist_ok=True)
            (out_dir / name / "_traceback.txt").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        dump_edits(wiki, out_dir / name)
        logger.info(f"[parity] {name}: {status[name]}")
        (out_dir / "_status.txt").write_text(
            "".join(f"{k}: {v}\n" for k, v in status.items()), encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--jobs", nargs="*", default=None)
    args = parser.parse_args()
    logger.info(f"[parity] ptilopsis from {Path(ptilopsis.__file__).parent}")
    discover_jobs()
    names = args.jobs or sorted(
        job.name for job in registered_jobs() if job.name not in SKIP_JOBS
    )
    run(args.out_dir, names)


if __name__ == "__main__":
    main()
