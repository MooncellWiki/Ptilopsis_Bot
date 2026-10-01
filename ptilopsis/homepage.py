"""首页「近期新增」三个数据页的写法。

新版首页按设计稿渲染这三页,机器人直接写成模板调用,不再写自由排版的列表、
也不再需要编辑事后补活动名和分组名:

* 首页/新增关卡:一个活动 / 章节一块 ``{{首页/新增关卡}}``,分组名与本组关卡成对出现,
  关卡逐个写成 ``{{首页/新增关卡/关卡|页面名}}``——页面名里可能有半角逗号
  (如 ``6-13 没有火,没有光``),不能拼成一串再按分隔符拆;
* 首页/新增主题、首页/新增单件:一件一个 ``{{首页/家具卡|页面名}}``,主题加 ``|theme=1``。
"""

from collections.abc import Sequence

from ptilopsis.gamedata.activity_table import ActivityTable
from ptilopsis.gamedata.stage_table import StageData
from ptilopsis.gamedata.zone_table import ZoneTable
from ptilopsis.wikitext import WikiTemplate, inline_template

NEW_STAGES_PAGE = "首页/新增关卡"
NEW_THEMES_PAGE = "首页/新增主题"
NEW_FURNITURE_PAGE = "首页/新增单件"

# 模板:首页/新增关卡 接的「分组名 + 关卡」对数;超出的分组另起一块,标题照抄
MAX_GROUPS = 6

# 不属于任何活动、区域也没有名字的关卡,按关卡类型给个统称
STAGE_TYPE_TITLES = {"MAIN": "主线", "CLIMB_TOWER": "保全派驻"}


def code_prefixes(codes: Sequence[str]) -> str:
    """关卡码前缀去重后用 · 连接,作块标题的英文副题。

    ``VEC-01``、``VEC-SP01`` → ``VEC``。
    """

    return " · ".join(dict.fromkeys(c.split("-", 1)[0] for c in codes if c))


def render_stage_block(
    title: str, groups: Sequence[tuple[str, Sequence[str]]], en: str = ""
) -> str:
    """一个活动 / 章节:``groups`` 是 (分组名, 关卡页面名),不分组时分组名为空串。"""

    blocks = []
    for start in range(0, len(groups), MAX_GROUPS):
        template = WikiTemplate("首页/新增关卡").add("1", title).add_optional("en", en)
        for i, (name, pages) in enumerate(groups[start : start + MAX_GROUPS]):
            template.add(str(2 * i + 2), name)
            template.add(
                str(2 * i + 3),
                "".join(inline_template("首页/新增关卡/关卡", page) for page in pages),
            )
        blocks.append(str(template))
    return "\n".join(blocks)


def render_stage_list(title: str, entries: Sequence[tuple[str, str]]) -> str:
    """一类关卡一块、不分组(剿灭、悖论模拟、生息演算等)。

    ``entries`` 是 (关卡码, 页面名)。
    """

    return render_stage_block(
        title,
        [("", [page for _, page in entries])],
        en=code_prefixes([code for code, _ in entries]),
    )


def render_new_stages(
    stages: Sequence[tuple[StageData, str]],
    zone_table: ZoneTable,
    activity_table: ActivityTable,
) -> str:
    """stage_table 里的关卡按活动分块,块内按区域分组,顺序同传入顺序。

    块标题取活动名(zoneToActivity → basicInfo.name),分组名取区域名(zoneNameSecond),
    即编辑过去手补的那两层粗体;不属于活动的关卡以区域名作标题、不分组。
    """

    zones = zone_table.zones or {}
    zone_to_activity = activity_table.zone_to_activity or {}
    activities = activity_table.basic_info or {}

    # 块 → 区域 → [(关卡码, 页面名)];dict 保留首次出现的顺序
    events: dict[str, dict[str, list[tuple[str, str]]]] = {}
    titles: dict[str, tuple[str, bool]] = {}  # 块 → (标题, 是否按区域分组)
    for stage, page in stages:
        zone_id = stage.zone_id or ""
        zone = zones.get(zone_id)
        activity_id = zone_to_activity.get(zone_id)
        key = activity_id or zone_id
        if key not in titles:
            activity = activities.get(activity_id) if activity_id else None
            if activity is not None and activity.name:
                titles[key] = (activity.name.strip(), True)
            else:
                names = [zone.zone_name_first, zone.zone_name_second] if zone else []
                title = " ".join(n.strip() for n in names if n and n.strip())
                titles[key] = (
                    title or STAGE_TYPE_TITLES.get(stage.stage_type, ""),
                    False,
                )
        events.setdefault(key, {}).setdefault(zone_id, []).append(
            ((stage.code or "").strip(), page)
        )

    blocks = []
    for key, by_zone in events.items():
        title, grouped = titles[key]
        groups = []
        for zone_id, entries in by_zone.items():
            zone = zones.get(zone_id)
            name = (zone.zone_name_second or "").strip() if grouped and zone else ""
            groups.append((name, [page for _, page in entries]))
        codes = [code for entries in by_zone.values() for code, _ in entries]
        blocks.append(render_stage_block(title, groups, en=code_prefixes(codes)))
    return "\n".join(blocks)


def furniture_card(page: str, theme: bool = False) -> str:
    """新增家具的一张卡。``1=`` 显式写出,名字里带等号也不会被拆成命名参数。"""

    return inline_template("首页/家具卡", f"1={page}", *(["theme=1"] if theme else []))
