from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise


class MergeError(ValueError):
    pass


OPAQUE_OPEN = re.compile(r"<(nowiki|pre|source|syntaxhighlight|math|ref)\b[^>]*>", re.I)


def scan(text: str) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Return top-level template spans and top-level pipe/equal positions."""
    stack: list[tuple[str, int]] = []
    links = 0
    spans, pipes, equals = [], [], []
    i = 0
    while i < len(text):
        if text.startswith("<!--", i):
            end = text.find("-->", i + 4)
            if end < 0:
                raise MergeError("未闭合的注释")
            i = end + 3
            continue
        literal = OPAQUE_OPEN.match(text, i)
        if literal:
            if literal.group().endswith("/>"):
                i = literal.end()
            else:
                end = re.search(
                    r"</" + literal.group(1) + r"\s*>", text[literal.end() :], re.I
                )
                if not end:
                    raise MergeError("未闭合的文字标签：" + literal.group(1))
                i = literal.end() + end.end()
            continue
        if text.startswith("{{{{", i):
            raise MergeError(
                "存在需要完整 MediaWiki 解析器处理的连续开括号，请人工处理"
            )
        if text.startswith("{{{", i):
            stack.append(("argument", i))
            i += 3
            continue
        if text.startswith("{{", i):
            stack.append(("template", i))
            i += 2
            continue
        if stack and text.startswith("}}}" if stack[-1][0] == "argument" else "}}", i):
            kind, start = stack.pop()
            i += 3 if kind == "argument" else 2
            if not stack and kind == "template" and not links:
                spans.append((start, i))
            continue
        if text.startswith("}}", i):
            raise MergeError("存在未匹配的模板结束括号")
        if text.startswith("[[", i):
            links += 1
            i += 2
            continue
        if text.startswith("]]", i):
            if not links:
                raise MergeError("存在未匹配的链接结束括号")
            links -= 1
            i += 2
            continue
        if not stack and not links:
            if text[i] == "|":
                pipes.append(i)
            elif text[i] == "=":
                equals.append(i)
        i += 1
    if stack or links:
        raise MergeError("存在未闭合的模板、参数或链接")
    return spans, pipes, equals


@dataclass
class Parameter:
    name: str
    start: int  # Includes original whitespace; offsets refer to entire page.
    end: int
    raw: str
    name_start: int
    name_end: int

    @property
    def value(self) -> str:
        return self.raw.strip()


@dataclass
class CommonCall:
    start: int
    end: int
    params: dict[str, Parameter]

    def fields(self) -> dict[str, str]:
        return {name: param.value for name, param in self.params.items()}


def common_call(text: str) -> CommonCall:
    spans, _, _ = scan(text)
    found = []
    for start, end in spans:
        inner = text[start + 2 : end - 2]
        _, pipes, _ = scan(inner)
        name = inner[: pipes[0] if pipes else len(inner)].strip().replace("_", " ")
        name = re.sub(r"^(?:模板|template)\s*:\s*", "", name, flags=re.I)
        if name.casefold() != "收藏品/common":
            continue
        params = {}
        bounds = [*pipes, len(inner)]
        for left, right in pairwise(bounds):
            part = inner[left + 1 : right]
            _, _, equals = scan(part)
            if not equals:
                if part.strip():
                    raise MergeError("common 中存在未命名参数")
                continue
            eq = equals[0]
            key = part[:eq].strip()
            if not key or key in params:
                raise MergeError(f"common 参数名称为空或重复：{key}")
            if any(char in key for char in "{}[]<>\r\n"):
                raise MergeError(
                    "common 中存在动态或带注释的参数名，不能可靠判断字段归属"
                )
            value_start = start + 2 + left + 1 + eq + 1
            value_end = start + 2 + right
            name_start = start + 2 + left + 1 + part.index(key)
            params[key] = Parameter(
                key,
                value_start,
                value_end,
                text[value_start:value_end],
                name_start,
                name_start + len(key),
            )
        found.append(CommonCall(start, end, params))
    if len(found) != 1:
        raise MergeError(
            f"需要且只能有一个顶层 收藏品/common，实际找到 {len(found)} 个"
        )
    return found[0]


THEME_FIELD = re.compile(
    r"^(主题|角标|售价|易与售价|货币|效果|效果高度|获取条件|解锁条件)([1-9]\d*)$"
)


def theme_identity(value: str) -> str:
    """Match plain names and linked/bold names without rewriting human markup."""
    value = value.strip()
    if value.startswith("'''") and value.endswith("'''") and len(value) >= 6:
        value = value[3:-3].strip()
    link = re.fullmatch(r"\[\[([^\[\]|]+)(?:\|[^\[\]]*)?\]\]", value)
    return (link[1] if link else value).strip()


def theme_groups(fields: dict[str, str]) -> dict[int, str]:
    groups = {
        int(key[2:]): theme_identity(value)
        for key, value in fields.items()
        if re.fullmatch(r"主题[1-9]\d*", key)
    }
    if any(not value for value in groups.values()) or len(set(groups.values())) != len(
        groups
    ):
        raise MergeError("主题名称为空或重复，不能可靠匹配编号，请人工核对")
    return dict(sorted(groups.items()))


def align_themes(
    current: str,
    incoming: dict[str, str],
    baseline: dict[str, str],
    theme_order: list[str] | None = None,
) -> tuple:

    live = common_call(current)
    live_groups, incoming_groups, base_groups = (
        theme_groups(data) for data in (live.fields(), incoming, baseline)
    )
    if set(base_groups.values()) - set(live_groups.values()):
        raise MergeError("基准中的主题已被删除或改名，请人工核对主题归属后重新规划")
    sequences = [list(live_groups.values()), list(incoming_groups.values())]
    pending = list(dict.fromkeys(name for seq in sequences for name in seq))
    if theme_order is not None:
        # Ordering hints never add unselected themes to the page.
        sequences.append(
            [
                name
                for value in theme_order
                if (name := theme_identity(value)) in pending
            ]
        )
    dependencies = {name: set() for name in pending}
    for sequence in sequences:
        for previous, following in pairwise(sequence):
            dependencies[following].add(previous)
    ordered = []
    while pending:
        ready = next(
            (name for name in pending if not dependencies[name].intersection(pending)),
            None,
        )
        if ready is None:
            raise MergeError("已有主题顺序与源数据矛盾，请人工核对后重新规划")
        ordered.append(ready)
        pending.remove(ready)
    numbers = {name: index for index, name in enumerate(ordered, 1)}

    def rename_keys(data, groups):
        renamed = {}
        for key in data:
            match = THEME_FIELD.fullmatch(key)
            if match:
                prefix, number = match[1], int(match[2])
                if number not in groups:
                    raise MergeError(f"{key} 缺少对应主题，不能可靠迁移编号")
                renamed[key] = prefix + str(numbers[groups[number]])
            else:
                suffix = re.search(r"([1-9]\d*)$", key)
                if (
                    suffix
                    and int(suffix[1]) in groups
                    and numbers[groups[int(suffix[1])]] != int(suffix[1])
                ):
                    raise MergeError(f"未知编号参数 {key}，请先确认是否属于该主题")
                renamed[key] = key
        if len(set(renamed.values())) != len(renamed):
            raise MergeError("主题编号迁移产生重复字段，请人工核对")
        return renamed

    live_keys = rename_keys(live.fields(), live_groups)
    incoming_keys = rename_keys(incoming, incoming_groups)
    # An add-only baseline can contain just a few fields of a pre-existing theme.
    # Use its recorded theme anchors when available, otherwise the live layout.
    base_keys = rename_keys(baseline, {**live_groups, **base_groups})
    replacements, changes = [], []
    for old, new in live_keys.items():
        if old != new:
            param = live.params[old]
            replacements.append((param.name_start, param.name_end, new))
            changes.append({"field": old, "action": "renumber", "to": new})
    for start, end, value in sorted(replacements, reverse=True):
        current = current[:start] + value + current[end:]
    return (
        current,
        {incoming_keys[key]: value for key, value in incoming.items()},
        {base_keys[key]: value for key, value in baseline.items()},
        changes,
    )


REFRESH_FIELDS = frozenset({"iconId", "稀有度", "描述"})


def merge_page(
    current: str,
    desired: str,
    baseline: dict[str, str] | None = None,
    *,
    theme_order: list[str] | None = None,
) -> dict:
    current, incoming, base, renumbered = align_themes(
        current, common_call(desired).fields(), dict(baseline or {}), theme_order
    )
    live = common_call(current)
    next_managed = dict(base)
    preserved, changes, replacements, additions = [], [], [], []
    for name, wanted in incoming.items():
        param = live.params.get(name)
        if name in REFRESH_FIELDS:
            # These three headers are explicitly maintained from the latest theme,
            # including for pre-existing pages without an imported bot baseline.
            next_managed[name] = wanted
            if param is None:
                additions.append(f"|{name}={wanted}\n")
                changes.append({"field": name, "action": "add"})
            elif param.value != wanted:
                leading = re.match(r"\s*", param.raw).group()
                trailing = re.search(r"\s*$", param.raw).group()
                if not param.raw.strip():
                    leading = ""
                replacements.append(
                    (param.start, param.end, leading + wanted + trailing)
                )
                changes.append({"field": name, "action": "update"})
        elif param is not None:
            if param.value != wanted:
                preserved.append(
                    {"field": name, "reason": "已填写参数固定保留，不随源数据更新"}
                )
        elif name in base:
            preserved.append({"field": name, "reason": "保留人工删除的字段"})
        else:
            additions.append(f"|{name}={wanted}\n")
            next_managed[name] = wanted
            changes.append({"field": name, "action": "add"})
    if additions:
        close = live.end - 2
        separator = "" if current[:close].endswith("\n") else "\n"
        replacements.append((close, close, separator + "".join(additions)))
    output = current
    for start, end, replacement in sorted(replacements, reverse=True):
        output = output[:start] + replacement + output[end:]
    output_fields = common_call(output).fields()
    for key in list(next_managed):
        match = THEME_FIELD.fullmatch(key)
        if match:
            theme_key = "主题" + match[2]
            if theme_key in output_fields:
                next_managed.setdefault(theme_key, output_fields[theme_key])
    return {
        "text": output,
        "managed": next_managed,
        "conflicts": [],
        "preserved": preserved,
        "changes": renumbered + changes,
        "desired_fields": incoming,
    }
