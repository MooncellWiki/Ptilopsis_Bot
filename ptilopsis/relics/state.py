import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path

STATE_SCHEMA = "prts-relic-state/v1"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_state(path: Path, api_url: str) -> dict:
    state = (
        json.loads(path.read_text(encoding="utf-8-sig"))
        if path.exists()
        else {"schema": STATE_SCHEMA, "pages": {}, "api_url": api_url}
    )
    if state.get("schema") != STATE_SCHEMA or not isinstance(state.get("pages"), dict):
        raise ValueError("维护状态文件格式不正确")
    # The original builder was exclusively for PRTS and had no api_url field.
    if state.get("api_url", "https://prts.wiki/api.php") != api_url:
        raise ValueError("维护状态文件属于另一个 Wiki")
    state["api_url"] = api_url
    pending = state.setdefault("pending", {})
    if not isinstance(pending, dict):
        raise ValueError("维护状态 pending 无效")
    for entry in [*state["pages"].values(), *pending.values()]:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("managed"), dict)
            or not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in entry["managed"].items()
            )
        ):
            raise ValueError("维护状态中的 managed 字段无效")
        if "latest_theme" in entry and (
            type(entry["latest_theme"]) is not int or entry["latest_theme"] < 1
        ):
            raise ValueError("维护状态中的 latest_theme 字段无效")
    return state


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def state_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    try:
        stream = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(f"收藏品任务已在运行或遗留锁尚未清理：{lock}") from exc
    try:
        with stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()
