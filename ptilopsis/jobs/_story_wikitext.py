"""剧情模拟器参数、剧情导航、关卡跳转的现有 Wiki 格式。"""

import re
from collections.abc import Iterable

from ptilopsis.jobs._story_catalog import NavGroup, Script, script_path, title_key
from ptilopsis.wikitext import inline_template

STORY_TEMPLATE = "剧情模拟器"
NAVIGATION = "模板:剧情导航"
DATA_REFERENCE = "{{:{{PAGENAME}}/data}}"
NAV_FOOTER = (
    "</div>__NOTOC__<includeonly>{{#ifeq:{{{nocat|no}}}|yes||[[分类:剧情]]}}"
    "</includeonly><noinclude>[[分类:PRTS导航模板]]</noinclude>"
)

# 模拟器的三个 Widget 参数包含一层模板。只改文本数据之前的参数。
STORY_HEAD = re.compile(
    r"(?im)^[ \t]*\{\{\s*(?:(?:模板|Template):\s*)?剧情模拟器\s*"
    r"(?P<params>(?:\{\{[^{}]*\}\}|(?!\|\s*文本数据\s*=)[^{}])*+)"
    r"(?P<anchor>\|\s*文本数据\s*=)"
)
METADATA = re.compile(r"\|\s*(文本路径|剧情类型|剧情分组)\s*=([^|{}\n]*)")
INLINE_END = re.compile(r"(?m)^\}\}[ \t]*$")
SUBPAGE_REQUIRED = re.compile(r"~{3,}|[|]|\{\{|\}\}|\[\[|<!--|</?nowiki\b", re.I)
NAV_LINK = re.compile(r"\[\[([^]|\n]+)(?:\|[^]\n]*)?\]\]")
SECTION = re.compile(r"(?m)^==(?!=)[ \t]*(.*?)[ \t]*==[ \t]*$")


def _fields(story: Script) -> dict[str, str]:
    return {"文本路径": story.path, "剧情类型": story.kind, "剧情分组": story.group}


def render_story(story: Script, script: str, *, subpage: bool) -> str:
    parameters = {
        "图片数据": "{{Widget:Data_Image}}",
        "角色数据": "{{Widget:Data_Char}}",
        "音频数据": "{{Widget:Data_Audio}}",
        **_fields(story),
    }
    body = DATA_REFERENCE if subpage else script
    tail = "[[分类:干员密录]]" if story.kind == "干员密录" else "{{剧情导航}}"
    call = inline_template(
        STORY_TEMPLATE,
        *(f"{key}={value}" for key, value in parameters.items() if value),
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


def _render_navbox(groups: Iterable[NavGroup], list_title: str) -> tuple[str, str]:
    link = f"[[剧情一览|{list_title}]]"
    mobile = [
        '{| class="wikitable nodesktop navigation-not-searchable" '
        'style="white-space:normal;display:table;text-align:left;width:720px;"',
        "|-",
        f'! colspan="3" style="font-size:20px;text-align:center;"|{link}',
    ]
    desktop = [
        f"{{{{Navbox|state=uncollapsed|name={{{{PAGENAME}}}}|title={link}|listclass=hlist"
    ]
    for number, group in enumerate(groups, 1):
        desktop.append(
            f"|group{number}={group.label}\n|list{number}=\n{{{{Navbox|child"
        )
        if group.manual:
            mobile.extend(["|-", f'! rowspan="{len(group.rows)}"|{group.label}'])
        for row_number, row in enumerate(group.rows, 1):
            links = [f"[[{story.title}|{story.label}]]" for story in row.stories]
            list_items = "".join(f"<li>{item}</li>" for item in links)
            dots = "{{dot}}".join(links)
            if group.manual:
                if row_number > 1:
                    mobile.append("|-")
                mobile.extend([f"! {row.label}", f"| {dots}"])
                desktop.append(
                    f"|group{row_number}={row.label}|list{row_number}={list_items}"
                )
            else:
                mobile.extend(
                    [
                        "|-",
                        f'! width="120px"|{group.label}',
                        f'! width="40px"|{row.label}',
                        f'| width="560px"|{dots}',
                    ]
                )
                desktop[-1] += (
                    f"|group{row_number}={row.label}|list{row_number}={list_items}"
                )
        desktop[-1] += "}}"
    mobile.append("|}")
    desktop.append("}}")
    return "\n".join(mobile) + "\n", "\n".join(desktop) + "\n"


def render_navigation(main: Iterable[NavGroup], activities: Iterable[NavGroup]) -> str:
    mobile_main, desktop_main = _render_navbox(main, "主线剧情一览")
    mobile_act, desktop_act = _render_navbox(activities, "活动剧情一览")
    return (
        mobile_main
        + mobile_act
        + '<div class="nomobile">'
        + desktop_main
        + desktop_act
        + NAV_FOOTER
    )


def navigation_links(text: str) -> set[str]:
    return {title_key(title) for title in NAV_LINK.findall(text)} - {"剧情一览"}


def render_stage_links(
    title: str, stories: dict[str, Script], *, combined: bool = True
) -> str:
    code, _, name = title.partition(" ")
    if (
        combined
        and stories.keys() == {"BEG", "END"}
        and all(story.title == f"{title}/{tag}" for tag, story in stories.items())
    ):
        return inline_template("剧情跳转/关卡", code, name)
    labels = {
        "NBT": title.replace(" ", "<br>", 1),
        "BEG": f"{code}<br>行动前",
        "END": f"{code}<br>行动后",
    }
    return "\n".join(
        inline_template("剧情跳转", f"text={labels[tag]}", f"link={stories[tag].title}")
        for tag in ("NBT", "BEG", "END")
        if tag in stories
    )


def add_stage_links(source: str, title: str, stories: dict[str, Script]) -> str | None:
    """为关卡补写剧情小节，或为只有一个生成的跳转的小节补齐前后篇。"""
    sections = list(SECTION.finditer(source))
    boundaries = [m.start() for m in sections[1:]] + [len(source)]
    normal = next(
        ((m, end) for m, end in zip(sections, boundaries) if m[1] == "普通"), None
    )
    if not normal:
        return None
    heading, end = normal
    if not re.search(r"\{\{\s*普通关卡信息\b", source[heading.end() : end]):
        return None
    generated = render_stage_links(title, stories)
    existing = [(i, m) for i, m in enumerate(sections) if m[1] == "剧情"]
    if not existing:
        return (
            source[: heading.start()]
            + f"==剧情==\n{generated}\n"
            + source[heading.start() :]
        )
    if len(existing) != 1:
        return None
    index, heading = existing[0]
    end = sections[index + 1].start() if index + 1 < len(sections) else len(source)
    original = source[heading.end() : end].strip()
    if original == generated:
        return source
    for tag, story in stories.items():
        if original == render_stage_links(title, {tag: story}, combined=False):
            return source[: heading.end()] + f"\n{generated}\n" + source[end:]
    return None
