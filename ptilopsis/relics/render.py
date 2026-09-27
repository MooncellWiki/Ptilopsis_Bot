import html
import re
from typing import Any

RARITIES = {"NORMAL": 0, "RARE": 1, "SUPER_RARE": 2}
GENERIC_OBTAIN = "在集成战略模式中获得"
SUMMARY = "(Page Upload)"
UPDATE_SUMMARY = "(Page Update)"

PREAMBLE = (
    "{{Cbox2|mdi=true|icon=information-v"
    "ariant-circle|text='''在非标准模式下，一些特殊收"
    "藏品可能会通过坎诺特的商店以源石锭标价出售'''，此时：\n* '''低"
    "稀有度'''收藏品售价8源石锭\n* {{color|#2ac5c9|'"
    "''中稀有度'''}}收藏品售价12源石锭\n* {{color|#7d"
    "0022|'''高稀有度'''}}收藏品售价16源石锭\n若无特殊说明，"
    "下列的“商店售价”为不受收藏品和对应主题下负面效果等影响时的基础售价<"
    "br>部分收藏品的稀有度在不同主题中会发生变化，本表格模板标题使用的收"
    "藏品稀有度默认为'''当期主题'''下的稀有度，关于不同主题下的稀有度"
    "，请您以对应主题下的“售价”为准}}\n{{Cbox2|mdi=true"
    "|icon=information-variant-circle|te"
    "xt=本表格中“主题”一栏中存在部分通用角标以展示部分不便在表格中标注"
    '的信息，以下是部分角标：<br><span style="backgr'
    "ound:#2f2f2f;color:white;padding:0p"
    "x 5px;border: 1px solid #ffffff85;b"
    "order-radius:2px;box-shadow: 0 0 5p"
    'x 1px #5f5f5fa1;">{{mdi|alpha-x-box'
    "-outline}}</span> 标志表示收藏品为【内容拓展·X】加"
    "入的收藏品<br/>'''{{模板:收藏品/角标|notrade}}'"
    "'' 标志表示收藏品不可在【失与得】节点被交换出去。<br/>'''{"
    "{模板:收藏品/角标|stack}}''' 标志表示收藏品拥有计数机制"
    "，会对其对应条件进行计数。在查看已持有收藏品时会显示目前其已叠加的层数"
    "。<br/>'''{{模板:收藏品/角标|oneoff}}''' 标志"
    "表示收藏品为一次性收藏品，其生效后即无法再次生效（查看收藏品时标记为'"
    "''已使用'''）<br>\n如果您想查看本页面会出现的所有角标，您应当"
    "查阅页面[[模板:收藏品/角标]]\n}}"
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"应为字符串或 null，实际为 {type(value).__name__}")
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(v for v in values if v))


def wiki_text(value: str) -> str:
    text = html.escape(value, quote=True)
    for char in "|{}[]":
        text = text.replace(char, f"&#{ord(char)};")
    return text.replace("\n", "<br/>")


def rogue_number(identifier: Any) -> int:
    match = re.match(r"^rogue_(\d+)_", clean(identifier))
    if not match:
        raise ValueError(f"无法识别 rogue_数字_ 编号：{identifier!r}")
    return int(match.group(1))


def validate_title(title: Any) -> str:
    if not isinstance(title, str) or not title or title != title.strip():
        raise ValueError(f"页面标题为空或含首尾空白：{title!r}")
    if any(c in title for c in "#<>[]{}|\r\n\t") or any(ord(c) < 32 for c in title):
        raise ValueError(f"页面标题含不支持字符：{title!r}")
    if len(title.encode("utf-8")) > 255:
        raise ValueError(f"页面标题超过 255 UTF-8 字节：{title}")
    return title


def title_key(title: str) -> str:
    return " ".join(title.replace("_", " ").split()).casefold()


def normalize_themes(relic: dict[str, Any]) -> list[dict[str, Any]]:
    entries = relic.get("value")
    if not isinstance(entries, list) or not entries:
        raise ValueError("value 必须是非空主题数组")
    themes: list[dict[str, Any]] = []
    seen: set[int] = set()
    for entry in entries:
        theme_name = clean(entry["theme"])
        raw = entry["value"]
        rows = raw if isinstance(raw, list) else [raw]
        if not theme_name or not rows or not all(isinstance(v, dict) for v in rows):
            raise ValueError("主题名称为空或主题 value 不是字典/非空字典数组")
        numbers = {rogue_number(row["key"]) for row in rows}
        if len(numbers) != 1:
            raise ValueError(f"{theme_name} 的多个 value 跨越不同 rogue 编号")
        number = numbers.pop()
        if number < 1 or number in seen:
            raise ValueError(f"主题编号必须为不重复的正整数：{number}")
        seen.add(number)
        rarities = {row["rarity"] for row in rows}
        if len(rarities) != 1 or not rarities.issubset(RARITIES):
            raise ValueError(f"{theme_name} 稀有度未知或多个变体稀有度冲突：{rarities}")
        for row in rows:
            if row.get("type") != "RELIC":
                raise ValueError(f"{row['key']} 不是 RELIC")
            rogue_number(row["iconId"])
            for field in ("description", "usage", "obtainApproach", "unlockCondDesc"):
                clean(row.get(field))
        themes.append(
            {
                "number": number,
                "name": theme_name,
                "rows": rows,
                "rarity": RARITIES[next(iter(rarities))],
            }
        )
    return sorted(themes, key=lambda theme: theme["number"])


def variant_label(row: dict[str, Any], index: int) -> str:
    if "difficulty" in row:
        difficulty = row["difficulty"]
        if difficulty not in {0, 3, 6, 9}:
            raise ValueError(f"未知难度阈值：{difficulty}")
        return "{{color|#d800db|难度" + str(difficulty) + "及以上生效：}}"
    suffix = row["key"].rsplit("_", 1)[-1]
    if suffix in {"a", "b", "c"}:
        difficulty = {"a": 3, "b": 6, "c": 9}[suffix]
    elif index == 0:
        difficulty = 0
    else:
        raise ValueError(f"未知难度变体，不能推测阈值：{row['key']}")
    return "{{color|#d800db|难度" + str(difficulty) + "及以上生效：}}"


def merge_field(
    rows: list[dict[str, Any]], field: str, *, labeled: bool = False, omit: str = ""
) -> str:
    values = [clean(row.get(field)) for row in rows]
    values = ["" if value == omit else value for value in values]
    distinct = unique(values)
    if not distinct:
        return ""
    if not labeled or len(rows) == 1 or (field != "usage" and len(set(values)) == 1):
        return "<br/><br/>".join(wiki_text(value) for value in distinct)
    return "<br/>".join(
        f"{variant_label(row, i)}{wiki_text(value) if value else '－'}"
        for i, (row, value) in enumerate(zip(rows, values))
    )


def render_relic(
    relic: dict[str, Any],
    preamble: str,
    prefix: str = "",
    *,
    theme_numbers: set[int] | None = None,
) -> dict[str, Any]:
    name = clean(relic["name"])
    if not name:
        raise ValueError("收藏品名称为空")
    title = validate_title(prefix + name)
    themes = normalize_themes(relic)
    latest = themes[-1]
    # Stable max chooses the first/base variant on equal numeric theme IDs.
    rows = [row for theme in themes for row in theme["rows"]]
    icon = max(rows, key=lambda row: rogue_number(row["iconId"]))["iconId"]
    descriptions = unique([clean(row.get("description")) for row in latest["rows"]])
    warnings = []
    if any(len(theme["rows"]) > 1 for theme in themes):
        warnings.append("含难度变体：效果按难度0/3/6/9及以上生效展示；描述去重合并")
    if len(themes) > 6:
        warnings.append("含主题7或更高编号；需先部署配套动态 common 模板及 Lua 模块")
    older_descriptions = {
        clean(row.get("description")) for theme in themes[:-1] for row in theme["rows"]
    }
    if older_descriptions - set(descriptions) - {""}:
        warnings.append("旧主题存在不同描述；按预设仅取最新主题描述")
    lines = [
        preamble,
        "",
        "{{收藏品/common",
        f"|名称={wiki_text(name)}",
        f"|iconId={icon}",
        f"|稀有度={latest['rarity']}",
        f"|描述={merge_field(latest['rows'], 'description')}",
    ]
    theme_meta = []
    selected = [
        theme
        for theme in themes
        if theme_numbers is None or theme["number"] in theme_numbers
    ]
    if not selected:
        raise ValueError("收藏品不包含指定主题")
    for number, theme in enumerate(selected, 1):
        variants = theme["rows"]
        price = (theme["rarity"] + 2) * 4
        obtain = merge_field(
            variants, "obtainApproach", labeled=True, omit=GENERIC_OBTAIN
        )
        unlock = merge_field(variants, "unlockCondDesc", labeled=True)
        lines.extend(
            [
                f"|主题{number}={wiki_text(theme['name'])}",
                f"|角标{number}=",
                f"|售价{number}={price}",
                f"|效果{number}={merge_field(variants, 'usage', labeled=True)}",
                f"|获取条件{number}={obtain}",
                f"|解锁条件{number}={unlock}",
            ]
        )
        theme_meta.append(
            {
                "number": number,
                "source_number": theme["number"],
                "name": theme["name"],
                "rarity": theme["rarity"],
                "price": price,
                "keys": [row["key"] for row in variants],
                "descriptions": unique(
                    [clean(row.get("description")) for row in variants]
                ),
            }
        )
    lines.append("}}")
    result = {
        "title": title,
        "name": name,
        "text": "\n".join(lines) + "\n",
        "iconId": icon,
        "latest_theme": latest["number"],
        "rarity": latest["rarity"],
        "themes": theme_meta,
        "warnings": warnings,
    }
    if theme_numbers is not None:
        # Complete source order is needed when backfilling an older selected theme.
        # Headers above intentionally still use the latest theme of this relic.
        result["theme_order"] = [wiki_text(theme["name"]) for theme in themes]
    return result
