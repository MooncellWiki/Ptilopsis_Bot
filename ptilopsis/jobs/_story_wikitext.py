"""剧情页和剧本参数的现有 Wiki 格式。"""

import re

from ptilopsis.jobs._story_catalog import Script, script_path
from ptilopsis.wikitext import inline_template

STORY_TEMPLATE = "剧情模拟器"
DATA_REFERENCE = "{{:{{PAGENAME}}/data}}"
# 模拟器的三个 Widget 参数包含一层模板。只改文本数据之前的参数。
STORY_HEAD = re.compile(
    r"(?im)^[ \t]*\{\{\s*(?:(?:模板|Template):\s*)?剧情模拟器\s*"
    r"(?P<params>(?:\{\{[^{}]*\}\}|(?!\|\s*文本数据\s*=)[^{}])*+)"
    r"(?P<anchor>\|\s*文本数据\s*=)"
)
METADATA = re.compile(r"\|\s*(文本路径|剧情类型|剧情分组)\s*=([^|{}\n]*)")
INLINE_END = re.compile(r"(?m)^\}\}[ \t]*$")
SUBPAGE_REQUIRED = re.compile(r"~{3,}|[|]|\{\{|\}\}|\[\[|<!--|</?nowiki\b", re.I)
DISPLAY_TITLE = re.compile(r"\{\{\s*(?:DISPLAYTITLE|显示标题|顯示標題)\s*:", re.I)


def add_display_title(source: str, title: str) -> str:
    """给已有剧情页补显示标题，保留现有的 MediaWiki 显示标题。"""
    if not STORY_HEAD.search(source) or DISPLAY_TITLE.search(source):
        return source
    return f"{{{{DISPLAYTITLE:{title}}}}}\n{source}"


def _fields(story: Script) -> dict[str, str]:
    return {"文本路径": story.path, "剧情类型": story.kind, "剧情分组": story.group}


def render_story(story: Script, script: str, *, subpage: bool) -> str:
    body = DATA_REFERENCE if subpage else script
    tail = "[[分类:干员密录]]" if story.kind == "干员密录" else "{{剧情导航}}"
    call = inline_template(
        STORY_TEMPLATE,
        *(f"{key}={value}" for key, value in _fields(story).items() if value),
        f"文本数据=\n{body}\n",
    )
    return f"{call}\n{tail}"


def add_story_fields(source: str, story: Script) -> str | None:
    """补齐已有模拟器调用的空字段。多个调用或路径不符时返回 None。"""
    heads = list(STORY_HEAD.finditer(source))
    if len(heads) != 1:
        return None
    head = heads[0]
    fields = _fields(story)
    existing = list(METADATA.finditer(head["params"]))
    keys = {match[1] for match in existing}
    if len(keys) != len(existing):
        return None
    for match in existing:
        if match[1] == "文本路径" and match[2].strip():
            if script_path(match[2]) != story.path:
                return None
    params = METADATA.sub(
        lambda match: match[0] if match[2].strip() else match[0] + fields[match[1]],
        head["params"],
    )
    params += "".join(
        f"|{key}={value}" for key, value in fields.items() if key not in keys
    )
    start, end = head.span("params")
    return source[:start] + params + source[end:]


def replace_story_script(
    source: str, script: str, *, subpage: bool
) -> tuple[str, bool] | None:
    """替换旧工具格式中的文本数据，返回新正文和是否本来就引用 /data。"""
    found = STORY_HEAD.search(source)
    if not found:
        return None
    end = INLINE_END.search(source, found.end())
    if not end:
        return None
    old = source[found.end() : end.start()].strip()
    if old == DATA_REFERENCE:
        return source, True
    if not old or SUBPAGE_REQUIRED.search(old):
        return None
    body = DATA_REFERENCE if subpage else script
    return f"{source[: found.end()]}\n{body}\n{source[end.start() :]}", False
