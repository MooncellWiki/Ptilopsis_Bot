"""把维护者提供的干员按表内顺序追加到干员序号表。"""

import csv
import io
import re
from datetime import datetime

import anyio

from ptilopsis.config import get_settings
from ptilopsis.utils.job import SkipJob, job
from ptilopsis.utils.wiki import Wiki

TITLE = "干员一览/干员id"
FIELDS = ["name", "rarity", "approach", "date"]


def append_rows(current: str, additions: str) -> str:
    existing = csv.DictReader(io.StringIO(current))
    incoming = csv.DictReader(io.StringIO(additions))
    if existing.fieldnames != ["sortId", *FIELDS] or incoming.fieldnames != FIELDS:
        raise ValueError("干员序号 CSV 表头不符")
    known = {row["name"]: row for row in existing}
    sort_id = max(int(row["sortId"]) for row in known.values())
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for row in incoming:
        if None in row or any(not row[key] for key in FIELDS):
            raise ValueError("新增干员行缺列或有空值")
        name = row["name"]
        if row["rarity"] not in {"3", "4", "5"}:
            raise ValueError(f"稀有度应为 3、4 或 5：{name}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", row["date"]):
            raise ValueError(f"实装时间应为 YYYY-MM-DD HH:MM：{name}")
        datetime.fromisoformat(row["date"])
        if name in known:
            if any(known[name][key] != row[key] for key in FIELDS):
                raise ValueError(f"干员已有不一致的序号表记录：{name}")
            continue
        sort_id += 1
        writer.writerow([sort_id, *(row[key] for key in FIELDS)])
        known[name] = row
    if not output.tell():
        return current
    return current.rstrip("\n") + "\n" + output.getvalue().rstrip("\n")


@job
async def append(wiki: Wiki) -> None:
    path = get_settings().operator_ids_csv
    if not path:
        raise SkipJob("请通过 PTILOPSIS_OPERATOR_IDS_CSV 指定新增干员 CSV")
    current = (await wiki.read_revisions([TITLE])).get(TITLE)
    if not current or current.redirect or current.contentmodel != "text":
        raise SkipJob(f"找不到可更新的 {TITLE}")
    additions = await anyio.Path(path).read_text(encoding="utf-8-sig")
    await wiki.edit_revision(
        current, append_rows(current.text, additions), "补录新增干员序号", bot=True
    )
