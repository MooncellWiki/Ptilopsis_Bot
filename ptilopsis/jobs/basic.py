import re
from collections.abc import Iterable
from typing import Annotated, Any

from ptilopsis.gamedata.battle_equip_table import BattleEquipPack
from ptilopsis.gamedata.building_data import BuildingData
from ptilopsis.gamedata.character_table import (
    AttributesData,
    AttributesDeltaData,
    CharacterData,
    CharacterDataPhaseData,
    ItemBundle,
)
from ptilopsis.gamedata.character_util import (
    MAX_POTENTIAL_RANK,
    phase_index,
    rarity_stars,
    trait_description,
    visible_talent_candidates,
)
from ptilopsis.gamedata.charword_table import CharWordTable
from ptilopsis.gamedata.gamedata_const import GameDataConsts
from ptilopsis.gamedata.handbook_info_table import (
    HandbookInfoTable,
    HandBookStoryViewData,
)
from ptilopsis.gamedata.handbook_team_table import HandbookTeamData
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.gamedata.medal_table import MedalData
from ptilopsis.gamedata.skill_table import SkillDataBundle
from ptilopsis.gamedata.skin_table import CharSkinDataDisplaySkin, SkinTable
from ptilopsis.gamedata.uniequip_table import UniEquipTable
from ptilopsis.jobs import params
from ptilopsis.log import logger
from ptilopsis.utils import richtext
from ptilopsis.utils.blackboard import blackboard_values, format_paramed_text
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

TeamTable = dict[str, HandbookTeamData]
IdTable = dict[str, dict[str, Any]]
"""wiki 上的干员序号表 ``{干员名: {id, approach, date}}``,见 ``params.CharIdTable``。"""


def phase_attributes(phase: CharacterDataPhaseData) -> list[AttributesData]:
    """一个精英阶段的属性关键帧,按等级顺序;首项是 1 级,末项是满级。"""

    frames = [frame.data for frame in (phase.attributes_key_frames or []) if frame.data]
    if not frames:
        raise ValueError(f"phase {phase.character_prefab_key!r} has no key frames")
    return frames


def favor_attributes(char: CharacterData) -> AttributesDeltaData:
    """满信赖时的加成(信赖关键帧末项)。"""

    frames = [frame.data for frame in (char.favor_key_frames or []) if frame.data]
    return frames[-1] if frames else AttributesDeltaData()


def compile_text(rts: richtext.RichText, text: str | None) -> str:
    return rts.compile(text).replace("\n", "<br/>")


def format_trait(char: CharacterData, phase: int, rts: richtext.RichText) -> str:
    """某个精英阶段满级、满潜能时客户端显示的特性文本。"""

    phases = char.phases or []
    level = phases[phase].max_level if phase < len(phases) else 1
    description, blackboard = trait_description(
        char, level=level, phase=phase, potential=MAX_POTENTIAL_RANK
    )
    if blackboard is not None:
        description = format_paramed_text(description, blackboard_values(blackboard))
    return compile_text(rts, description)


def sub_profession_name(uniequip_table: UniEquipTable, sub_profession_id: str | None):
    sub_prof = (uniequip_table.sub_prof_dict or {}).get(sub_profession_id or "")
    if sub_prof is None:
        return ""
    return sub_prof.sub_profession_name or ""


def item_name(item_table: InventoryData, item_id: str | None) -> str:
    """道具名(未去空白);道具不存在时与旧代码一样抛 ``KeyError``。"""

    if item_id is None or item_table.items is None:
        raise KeyError(item_id)
    return item_table.items[item_id].name or ""


def skin_display(
    skin_table: SkinTable, skin_id: str | None
) -> CharSkinDataDisplaySkin | None:
    """``charSkins[skin_id].displaySkin``,皮肤不存在时为 None。"""

    skin = (skin_table.char_skins or {}).get(skin_id or "")
    return skin.display_skin if skin is not None else None


def phase_drawers(skin_table: SkinTable, char_key: str) -> tuple[str, str, bool]:
    """各精英阶段立绘的画师。

    返回 ``(精英0画师, 与之不同阶段的追加行, 是否完整)``。旧实现靠异常中断:
    某阶段皮肤缺画师列表时就停在那里,保留已经拼好的部分;这里维持同样的语义,
    ``完整`` 为 False 表示中途停下。
    """

    drawer, drawer_append = "", ""
    for skin_p, skin_k in (
        (skin_table.buildin_evolve_map or {}).get(char_key, {}).items()
    ):
        display = skin_display(skin_table, skin_k)
        if display is None or display.drawer_list is None:
            return drawer, drawer_append, False
        drawer_temp = ",".join(display.drawer_list)
        if drawer == "":
            drawer = drawer_temp
        elif drawer != drawer_temp:
            drawer_append += f"\n|精英{skin_p}画师={drawer_temp}"
    return drawer, drawer_append, True


def format_cv(charword_table: CharWordTable, char_key: str) -> str:
    """各语言配音的 ``|xx配音=`` 行;没有配音数据时退化成空的日文配音行。

    旧实现同样靠异常中断:某语言缺声优列表时保留已拼好的行再补一个空的日文配音行。
    """

    voice = (charword_table.voice_lang_dict or {}).get(char_key)
    cv_dict = voice.dict_ if voice is not None else None
    if cv_dict is None:
        return "\n|日文配音="
    lang_dict: dict[str, str | None] = {
        k: v.name for k, v in (charword_table.voice_lang_type_dict or {}).items()
    }
    lang_dict["CN_MANDARIN"], lang_dict["CN_TOPOLECT"] = "中文", "中文方言"
    text = ""
    for k, info in cv_dict.items():
        if info.cv_name is None:
            return text + "\n|日文配音="
        lang = lang_dict.get(k, "未知语言")
        text += f"\n|{lang}配音={','.join(info.cv_name)}"
    return text


def get_basic_info(
    char: CharacterData,
    char_key: str,
    id_table: IdTable,
    rts: richtext.RichText,
    uniequip_table: UniEquipTable,
    team_table: TeamTable,
    skin_table: SkinTable,
    charword_table: CharWordTable,
) -> str:
    name = char.name or ""
    basic_info = "{{CharinfoV2"
    basic_info += "\n<!--下方为自动更新部分，您的修改可能会被覆盖-->"
    basic_info += f"\n|干员名={name}"
    basic_info += f"\n|干员外文名={char.appellation or ''}"
    basic_info += f"\n|干员id={char_key}"
    char_no = id_table[name]["id"] if name in id_table else -1
    basic_info += f"\n|干员序号={char_no}"
    # 特性:各精英阶段满级时的文本,与上一阶段相同则不重复输出
    traits = [format_trait(char, phase, rts) for phase in range(len(char.phases or []))]
    basic_info += (
        f"\n|特性={traits[0] if traits else compile_text(rts, char.description)}"
    )
    for phase in (1, 2):
        if phase < len(traits) and traits[phase] != traits[phase - 1]:
            basic_info += f"\n|特性{phase}={traits[phase]}"
    basic_info += f"\n|稀有度={trans_rarity(char.rarity)}"
    basic_info += f"\n|职业={trans_profession(char.profession)}"
    basic_info += (
        f"\n|分支={sub_profession_name(uniequip_table, char.sub_profession_id).strip()}"
    )
    basic_info += f"\n|情报编号={char.display_number or ''}"
    basic_info += f"\n|所属国家={trans_team(char.nation_id, team_table)}"
    basic_info += f"\n|所属组织={trans_team(char.group_id, team_table)}"
    basic_info += f"\n|所属团队={trans_team(char.team_id, team_table)}"
    basic_info += f"\n|位置={trans_position(char.position)}"
    basic_info += f"\n|标签={' '.join(char.tag_list or [])}"
    # 画师
    drawer, drawer_append, _complete = phase_drawers(skin_table, char_key)
    basic_info += f"\n|画师={drawer}" + drawer_append
    # 声优
    basic_info += format_cv(charword_table, char_key)
    # 常规皮肤description
    phase_skins = (skin_table.buildin_evolve_map or {})[char_key]
    # 旧实现每个阶段都拿精英 0 的画师列表来比较,照旧
    phase_0 = skin_display(skin_table, phase_skins.get(0))
    phase_drawer = (
        ",".join(phase_0.drawer_list)
        if phase_0 is not None and phase_0.drawer_list is not None
        else ""
    )
    for phase_no, skin_id in phase_skins.items():
        display = skin_display(skin_table, skin_id)
        phase_desc = display.content if display is not None else None
        phase_desc = phase_desc.replace("\n", "<br/>") if phase_desc is not None else ""
        basic_info += f"\n|精英{phase_no}介绍={phase_desc}"
        if phase_drawer != drawer:
            basic_info += f"\n|精英{phase_no}画师={phase_drawer}"
    # 时装
    skin_counter = 1
    costumes = [
        skin.display_skin
        for skin in (skin_table.char_skins or {}).values()
        if skin.char_id == char_key
        and skin.display_skin is not None
        and skin.display_skin.skin_group_name != "默认服装"
    ]
    for display in sorted(costumes, key=lambda x: x.on_year * 100 + x.on_period):
        basic_info += f"\n|时装{skin_counter}名称={display.skin_name}"
        if display.drawer_list is not None:
            skin_drawer = ",".join(display.drawer_list)
        else:
            skin_drawer = ""
        if skin_drawer != drawer:
            basic_info += f"\n|时装{skin_counter}画师={skin_drawer}"
        basic_info += f"\n|时装{skin_counter}系列={display.skin_group_name}"
        skin_color = display.color_list[0] if display.color_list else ""
        if not skin_color.startswith("#") and len(skin_color) == 6:
            skin_color = "#" + skin_color
        basic_info += f"\n|时装{skin_counter}颜色={skin_color}"
        skin_desc = re.sub(r"<color name=[^>]*>", "", display.content or "")
        skin_desc = (
            skin_desc.replace("</color>", "").replace("\r", "").replace("\n", "<br/>")
        )
        basic_info += f"\n|时装{skin_counter}介绍={skin_desc}"
        skin_counter += 1
    basic_info += "\n<!--上方为自动更新部分，您的修改可能会被覆盖-->"
    # 原案
    if phase_0 is not None and phase_0.designer_list is not None:
        basic_info += f"\n|原案={','.join(phase_0.designer_list)}"
    if name in id_table and id_table[name]["approach"] in ["活动获得", "限定寻访"]:
        basic_info += "\n|限定=1"
    basic_info += "\n}}"
    return basic_info


def get_char_approach(char: CharacterData, id_table: IdTable) -> str:
    name = char.name or ""
    if name in id_table and id_table[name]["approach"]:
        item_obtain_approach = id_table[name]["approach"]
    else:
        item_obtain_approach = char.item_obtain_approach or ""
    return "{{{{干员获得方式\n|获得方式={}\n|上线时间={}\n}}}}".format(
        item_obtain_approach,
        id_table[name]["date"] if name in id_table else "",
    )


def get_phases_data(
    char: CharacterData,
    char_key: str,
    uniequip_table: UniEquipTable,
    battle_equip_table: dict[str, BattleEquipPack],
    team_table: TeamTable,
) -> str:
    phases_data = "{{属性\n"
    phases = char.phases or []
    initial = phase_attributes(phases[0])[0]

    block_cnt_2 = initial.block_cnt
    block_data = str(initial.block_cnt)
    cost = initial.cost
    cost_data = str(cost)
    for phases_num in range(1, len(phases)):
        attrs = phase_attributes(phases[phases_num])[0]
        block_cnt_2 = attrs.block_cnt
        block_data += "→" + str(block_cnt_2)
        cost_2 = attrs.cost
        if cost != cost_2 or (phases_num == 1 and cost == cost_2):
            cost_data += "→" + str(cost_2)
            cost = cost_2
    if block_cnt_2 == initial.block_cnt:
        block_data = str(initial.block_cnt)

    phases_data += "|再部署=" + str(int(initial.respawn_time)) + "s\n"
    phases_data += "|部署费用=" + cost_data + "\n"
    phases_data += "|阻挡数=" + block_data + "\n"
    phases_data += "|攻击速度=" + str(initial.base_attack_time) + "s\n"
    if char.main_power is not None:
        power_list = []
        for power_value in (
            char.main_power.nation_id,
            char.main_power.group_id,
            char.main_power.team_id,
        ):
            if power_value is not None:
                p_trans = trans_team(power_value, team_table)
                if p_trans != "" and p_trans != "?":
                    power_list.append(p_trans)
        if power_list != []:
            phases_data += "|所属势力=" + ",".join(power_list) + "\n"
    if char.sub_power is not None:
        sub_power_list_lv0 = []
        for sub_power_group in char.sub_power:
            if sub_power_group is None:
                continue
            sub_power_list_lv1 = []
            for sub_power_value in (
                sub_power_group.nation_id,
                sub_power_group.group_id,
                sub_power_group.team_id,
            ):
                sp_trans = trans_team(sub_power_value, team_table)
                if sp_trans != "" and sp_trans != "?":
                    sub_power_list_lv1.append(sp_trans)
            if sub_power_list_lv1 != []:
                sub_power_list_lv0.append(",".join(sub_power_list_lv1))
        phases_data += "|隐藏势力=" + ";;".join(sub_power_list_lv0) + "\n"
    for phases_num, phase in enumerate(phases):
        frames = phase_attributes(phase)
        if phases_num == 0:
            phases_data += (
                f"|精英0_1级_生命上限={frames[0].max_hp}\n"
                f"|精英0_1级_攻击={frames[0].atk}\n"
                f"|精英0_1级_防御={frames[0].def_}\n"
                f"|精英0_1级_法术抗性={int(frames[0].magic_resistance)}\n"
            )
        phases_data += f"|精英{phases_num}_满级={phase.max_level}\n"
        phases_data += (
            f"|精英{phases_num}_满级_生命上限={frames[-1].max_hp}\n"
            f"|精英{phases_num}_满级_攻击={frames[-1].atk}\n"
            f"|精英{phases_num}_满级_防御={frames[-1].def_}\n"
            f"|精英{phases_num}_满级_法术抗性={int(frames[-1].magic_resistance)}\n"
        )

    favor = favor_attributes(char)
    favor_key_data = (
        f"|信赖加成_生命上限={favor.max_hp}\n"
        f"|信赖加成_攻击={favor.atk}\n"
        f"|信赖加成_防御={favor.def_}\n"
    )

    potential_rank_data = []
    potential_rank_type = []
    potential_ranks = char.potential_ranks or []
    for potential_rank in potential_ranks:
        modifiers = (
            potential_rank.buff.attributes.attribute_modifiers
            if potential_rank.buff and potential_rank.buff.attributes
            else None
        )
        if potential_rank.type == "BUFF" and modifiers:
            attribute_type = modifiers[0].attribute_type
            wiki_type = {
                "ATK": "atk",
                "DEF": "def",
                "MAX_HP": "hp",
                "MAGIC_RESISTANCE": "res",
                "COST": "cost",
                "ATTACK_SPEED": "interval",
                "RESPAWN_TIME": "re_deploy",
            }.get(attribute_type)
            if wiki_type is None:
                potential_rank_data.append("")
                potential_rank_type.append("")
                logger.info(
                    f"Error! Char {char.name} attributeType {attribute_type} dont know!"
                )
            else:
                potential_rank_data.append(str(int(modifiers[0].value)))
                potential_rank_type.append(wiki_type)
        else:
            potential_rank_data.append("")
            potential_rank_type.append("")
    phases_data += favor_key_data
    if len(potential_ranks) > 0 and len(potential_ranks) < 5:
        phases_data += f"|潜能上限={len(potential_ranks) + 1}\n"
    elif len(potential_ranks) == 0:
        phases_data += "|潜能上限=1\n"
    if potential_rank_data != [] and any(potential_rank_data):
        phases_data += "|潜能={}\n|潜能类型={}\n".format(
            ",".join(potential_rank_data), ",".join(potential_rank_type)
        )

    equip_dict = uniequip_table.equip_dict or {}
    uniequip_count = 0
    for equip_id in (uniequip_table.char_equip or {}).get(char_key, []):
        equip_info = equip_dict.get(equip_id)
        if equip_info is None:
            continue
        if equip_info.type == "INITIAL":
            phases_data += f"|初始模组名={equip_info.uni_equip_name}\n"
        elif equip_info.type == "ADVANCED":
            uniequip_count += 1
            phases_data += f"|模组{uniequip_count}名={equip_info.uni_equip_name}\n"
            pack = battle_equip_table.get(equip_id)
            if pack is not None and pack.phases:
                phases_data += f"|模组{uniequip_count}数据="
                phases_data += ";".join(
                    f"{x.key}:{x.value:.0f}"
                    for x in pack.phases[-1].attribute_blackboard or []
                )
                phases_data += "\n"
    phases_data += "}}"

    return phases_data


def get_range_data(char: CharacterData) -> str:
    range_data = "{{干员攻击范围\n"
    for range_num, phase in enumerate(char.phases or []):
        range_data += f"|精英{range_num}范围={phase.range_id or ''}\n"
    range_data += "}}"
    return range_data


def get_talent_list(char: CharacterData, rts: richtext.RichText) -> str:
    if char.talents is None:
        return "该干员没有天赋"
    id_char_list = ["一", "二", "三"]
    talent_list = "{{天赋列表\n"
    for bundle in char.talents:
        candidates = visible_talent_candidates(bundle)
        if not candidates:
            continue
        talent_num = id_char_list.pop(0) if id_char_list else "X"
        for index, talent in enumerate(candidates, start=1):
            condition = talent.unlock_condition
            talent_condition = get_tal_condition(
                talent.required_potential_rank,
                phase_index(condition.phase) if condition else 0,
                condition.level if condition else 1,
            )
            talent_list += f"|第{talent_num}天赋{index}={talent.name}\n"
            talent_list += f"|第{talent_num}天赋{index}条件={talent_condition}\n"
            talent_list += f"|第{talent_num}天赋{index}效果={compile_text(rts, talent.description)}\n"
    talent_list += "}}"
    return talent_list


def get_potential_list(char: CharacterData) -> str:
    if char.potential_ranks:
        potential_list = "{{潜能提升\n"
        for potential_id, rank in enumerate(char.potential_ranks):
            potential_list += f"|潜能{potential_id + 2}={rank.description or ''}\n"
        potential_list += "}}"
    else:
        potential_list = "该干员无法提升潜能"
    return potential_list


def get_skill_text(
    skill_table: dict[str, SkillDataBundle], skill_id: str, rts: richtext.RichText
) -> str:
    skill_data = skill_table.get(skill_id)
    if skill_data is None:
        logger.info(f"skillId {skill_id} not found")
        return ""
    levels = skill_data.levels or []
    if all(level.description is None for level in levels):
        # 召唤物/装置的内部技能没有描述,客户端也不展示
        logger.info(f"skillId {skill_id} has no description, skipped")
        return ""
    first = levels[0]
    skill_text = "{{{{技能\n|技能名={skill_name}\n|技能类型1={type1}{type2}".format(
        skill_name=first.name,
        type1=trans_sp_type(first.sp_data.sp_type if first.sp_data else ""),
        type2=trans_skill_type(first.skill_type),
    )
    if first.range_id:
        skill_text += f"\n|技能范围={first.range_id}"
        if any(level.range_id != first.range_id for level in levels):
            logger.info(f"技能 {first.name} 范围随等级变化")
    for idx, level_data in enumerate(levels):
        blackboard = blackboard_values(level_data.blackboard)
        # 暴雨一技能的描述引用了黑板里没有的 duration,客户端会把 {duration} 原样留下
        if skill_data.skill_id == "skchr_zebra_1":
            blackboard.setdefault("duration", level_data.duration)
        skill_description = compile_text(
            rts, format_paramed_text(level_data.description, blackboard)
        )

        if level_data.duration == 0 or level_data.duration == -1:
            skill_duration = ""
        elif level_data.duration == int(level_data.duration):
            skill_duration = str(int(level_data.duration))
        else:
            skill_duration = str(level_data.duration)
        if idx >= 7:
            skill_num = "专精" + str(idx - 6)
        else:
            skill_num = str(idx + 1)
        sp_data = level_data.sp_data
        skill_text += f"\n|技能{skill_num}描述={skill_description}\n|技能{skill_num}初始={sp_data.init_sp if sp_data else 0}\n|技能{skill_num}消耗={sp_data.sp_cost if sp_data else 0}\n|技能{skill_num}持续={skill_duration}"
    skill_text += "\n}}"
    return skill_text


def get_skill_list(
    char: CharacterData, skill_table: dict[str, SkillDataBundle], rts: richtext.RichText
) -> str:
    skill_list = ""
    if char.skills:
        for skill_id, skill in enumerate(char.skills):
            if skill.skill_id is None:
                continue
            condition = skill.unlock_cond
            skill_list += "\n'''技能{num}（{skill_cond}开放）'''\n".format(
                num=skill_id + 1,
                skill_cond=get_tal_condition(
                    0,
                    phase_index(condition.phase) if condition else 0,
                    condition.level if condition else 1,
                ),
            )
            try:
                skill_list += get_skill_text(skill_table, skill.skill_id, rts)
            except Exception:
                logger.exception(f"{char.name}技能{skill_id + 1}解析出错")
    else:
        skill_list = "\n该干员没有技能"
    return skill_list


def get_token_info(
    wiki,
    char: CharacterData,
    update_token_page: bool,
    character_table: dict[str, CharacterData],
    skill_table: dict[str, SkillDataBundle],
    rts: richtext.RichText,
) -> str:
    # 用 dict 保持顺序:先 displayTokenDict,再技能覆盖的召唤物
    token_keys: dict[str, None] = dict.fromkeys(char.display_token_dict or {})
    for skill in char.skills or []:
        if skill.override_token_key is not None:
            token_keys.setdefault(skill.override_token_key, None)
    token_info = "\n==召唤物信息=="
    if not token_keys:
        return ""
    for token_key in token_keys:
        if token_key not in character_table:
            continue
        token_info += (
            f"\n{{{{参阅|{character_table[token_key].name}|该持有者的召唤物}}}}"
        )
    for token_key in token_keys:
        token = character_table.get(token_key)
        if token is None:
            continue
        token_phases = token.phases or []
        token_page = f"==召唤物信息==\n{{{{召唤物信息\n|中文名称={token.name}\n|外文名称={token.appellation}\n|持有者={char.name}\n|使用条件=—"
        token_page += "\n|部署位置="
        token_page += {"MELEE": "近战位", "RANGED": "远程位", "ALL": "全部位"}[
            token.position
        ]
        token_page += f"\n|攻击范围={token_phases[0].range_id}"
        if any(phase.range_id != token_phases[0].range_id for phase in token_phases):
            logger.info(f"召唤物{token.name} rangeId changes.")
        for phases_num, phase in enumerate(token_phases):
            frames = phase_attributes(phase)
            token_page += f"\n|精英{phases_num}_1级_生命上限={frames[0].max_hp}\n|精英{phases_num}_1级_攻击={frames[0].atk}\n|精英{phases_num}_1级_防御={frames[0].def_}\n|精英{phases_num}_1级_法术抗性={int(frames[0].magic_resistance)}"
            token_page += f"\n|精英{phases_num}_满级={phase.max_level}"
            token_page += f"\n|精英{phases_num}_满级_生命上限={frames[-1].max_hp}\n|精英{phases_num}_满级_攻击={frames[-1].atk}\n|精英{phases_num}_满级_防御={frames[-1].def_}\n|精英{phases_num}_满级_法术抗性={int(frames[-1].magic_resistance)}"
        final = phase_attributes(token_phases[0])[-1]
        token_page += f"\n|再部署时间={final.respawn_time}s\n|部署费用={final.cost}\n|阻挡数={final.block_cnt}\n|攻击间隔={final.base_attack_time}s\n|嘲讽等级={final.taunt_level}\n|部署占用数=?\n}}}}"
        skill_list, id_count = "\n==召唤物技能==", 0
        for skill_data in token.skills or []:
            if skill_data.skill_id is None:
                continue
            id_count += 1
            condition = skill_data.unlock_cond
            skill_list += "\n'''技能{num}（{skill_cond}开放）'''\n".format(
                num=id_count,
                skill_cond=get_tal_condition(
                    0,
                    phase_index(condition.phase) if condition else 0,
                    condition.level if condition else 1,
                ),
            )
            try:
                skill_list += get_skill_text(skill_table, skill_data.skill_id, rts)
            except Exception:
                logger.exception(f"召唤物{token.name}技能解析出错")
        if id_count > 0:
            token_page += skill_list
        token_page += f"\n==召唤物模型==\n{{{{SpineId|id={token_key}}}}}"

        if update_token_page:
            wiki.edit(title=token.name, text=token_page, summary="update")
        else:
            wiki.edit(
                title=token.name,
                text=token_page,
                summary="init",
                createonly="1",
            )
        logger.info(f"Created: {token.name}.")
    return token_info


# 同名后勤技能在 wiki 上按房间 / 精英阶段区分的显示名
BUILDING_BUFF_NAME_OVERRIDES = {
    "control_dorm_rec[000]": "领袖(控制中枢)",
    "dorm_rec_all[013]": "领袖(宿舍)",
    "train_spd_doubleProf[100]": "红龙之血(精英0)",
    "train_spd_doubleProf[110]": "红龙之血(精英2)",
    "control_token_prod_spd2[000]": "以身作则(控制中枢)",
    "train_spd&profession2[440]": "以身作则(训练室)",
    "manu_prod_spd&limit&cost[200]": "得心应手(制造站)",
    "meet_spd_condChar[000]": "得心应手(会客室)",
    "control_prod_bd_spd[000]": "丰富工作经验(精英0)",
    "control_prod_bd_spd[010]": "丰富工作经验(精英2)",
    "power_rec_spd[008]": "澎湃紊流(精英0)",
    "power_rec_spd[009]": "澎湃紊流(精英1)",
    "meet_spd[1020]": "线索搜集·β(行箸)",
}


def get_building_skill(building_data: BuildingData, char_key: str) -> str:
    building_skill = "{{后勤技能"
    char_building_skill = (building_data.chars or {}).get(char_key)
    if char_building_skill is None:
        return "该干员无后勤技能"
    buffs = building_data.buffs or {}
    for building_skill_id, slot in enumerate(char_building_skill.buff_char or []):
        for building_skill_id_2, temp in enumerate(slot.buff_data or []):
            buff_count_text = (
                f"后勤技能{building_skill_id + 1}-{building_skill_id_2 + 1}"
            )
            if temp.buff_id is None:
                raise KeyError(temp.buff_id)
            buff_name = buffs[temp.buff_id].buff_name
            buff_name_extra = BUILDING_BUFF_NAME_OVERRIDES.get(temp.buff_id)
            if buff_name_extra is not None:
                buff_name = f"{buff_name_extra}\n|{buff_count_text}显示名={buff_name}"
            cond = temp.cond
            phase = trans_phase(cond.phase) if cond is not None else 0
            building_skill += (
                f"\n|{buff_count_text}={buff_name}\n|{buff_count_text}阶段=精英{phase}"
            )
            if cond is not None and cond.level != 1:
                building_skill += f"\n|{buff_count_text}等级={cond.level}级"
    if building_skill == "{{后勤技能":
        return "该干员无后勤技能"
    building_skill += "\n}}\n<!--如需修改技能信息，请前往[[后勤技能一览]]页面-->"
    return building_skill


def material_cost(item_table: InventoryData, costs: Iterable[ItemBundle]) -> str:
    return " ".join(
        f"{{{{材料消耗|{item_name(item_table, cost.id).rstrip()}|{cost.count}}}}}"
        for cost in costs
    )


def get_phase_list(
    char: CharacterData, gamedata_const: GameDataConsts, item_table: InventoryData
) -> str:
    phase_list = "{{精英化材料\n"
    phases = char.phases or []
    if len(phases) >= 2:
        for phase_id in range(1, len(phases)):
            evolve_cost = phases[phase_id].evolve_cost
            if evolve_cost is None:
                return "该干员无精英化材料需求"
            money = (gamedata_const.evolve_gold_cost or [])[
                rarity_stars(char.rarity) - 1
            ][phase_id - 1]
            if int(money / 10000) == money / 10000:
                money_str = str(int(money / 10000))
            else:
                money_str = str(float(money / 10000))
            material_list = "{{材料消耗|龙门币|" + money_str + "w}}"
            if evolve_cost:
                material_list += " " + material_cost(item_table, evolve_cost)
            phase_list += "|精" + str(phase_id) + "=" + material_list + "\n"
        phase_list += "}}"
    else:
        phase_list = "该干员无法精英化"
    return phase_list


def get_skill_levelUp_list(char: CharacterData, item_table: InventoryData) -> str:
    skill_levelup_list = "{{技能升级材料\n"
    if char.skills:
        for level_id, level_cost in enumerate(char.all_skill_lvlup or []):
            if level_cost.lvl_up_cost is None:
                return "该干员无技能升级材料需求"
            skill_levelup_list += (
                f"|{level_id + 2}={material_cost(item_table, level_cost.lvl_up_cost)}\n"
            )

        for skill_id, skill in enumerate(char.skills):
            if skill.level_up_cost_cond:
                for i in [8, 9, 10]:
                    cost = skill.level_up_cost_cond[i - 8].level_up_cost or []
                    skill_levelup_list += f"|{trans_id(skill_id + 1)}{i}={material_cost(item_table, cost)}\n"
        skill_levelup_list += "}}"
    else:
        skill_levelup_list = "该干员没有技能"
    return skill_levelup_list


EQUIP_ATTR_NAMES = {
    "max_hp": "生命",
    "atk": "攻击",
    "def": "防御",
    "magic_resistance": "法术抗性",
    "respawn_time": "再部署",
    "cost": "部署费用",
    "block_cnt": "阻挡数",
    "attack_speed": "攻击速度",
}


def get_battle_equip(
    char: CharacterData,
    char_key: str,
    battle_equip_table: dict[str, BattleEquipPack],
    uniequip_table: UniEquipTable,
    item_table: InventoryData,
    rts: richtext.RichText,
) -> list[str]:
    equip_ids = (uniequip_table.char_equip or {}).get(char_key)
    if equip_ids is None:
        return []
    content = ["\n==模组=="]
    equip_dict = uniequip_table.equip_dict or {}
    mission_dict = uniequip_table.mission_list or {}
    for equip in equip_ids:
        equip_info = equip_dict.get(equip)
        if equip_info is None:
            continue
        equip_name = (equip_info.uni_equip_name or "").strip()
        b_info = (equip_info.uni_equip_desc or "").strip().replace("\n", "<br>")
        if equip_info.type == "INITIAL":
            template = "\n==={name}===\n{{{{模组\n|名称={name}\n|基础证章=yes\n|分支={subProf}\n|模组图标={equipIcon}\n|类型图标={typeIcon}\n|基础信息={bInfo}\n}}}}"
            content.append(
                template.format(
                    name=equip_name,
                    subProf=sub_profession_name(uniequip_table, char.sub_profession_id),
                    equipIcon=equip_info.uni_equip_icon,
                    typeIcon=equip_info.type_icon,
                    bInfo=b_info,
                )
            )
        else:
            template = (
                "\n==={name}===\n<section begin=专属模组 />\n{{{{模组\n|名称={name}\n|类型={type}"
                "{typeColor}{equipIcon}{typeIcon}{params}{trait}{talent}{missions}{unlockCond}{itemCost}"
                "\n|基础信息={bInfo}\n}}}}\n<section end=专属模组 />"
            )
            if equip_info.equip_shining_color != "grey":
                type_color = f"\n|类型颜色={equip_info.equip_shining_color}"
            else:
                type_color = ""
            params, trait, talent = "", "", ""
            pack = battle_equip_table.get(equip)
            for e_lv, e_lv_data in enumerate(pack.phases or [] if pack else []):
                idx = "" if e_lv == 0 else str(e_lv + 1)
                for i in e_lv_data.attribute_blackboard or []:
                    params += "\n|{attrType}{idx}={value:.0f}".format(
                        attrType=EQUIP_ATTR_NAMES.get(i.key or "", "其他"),
                        idx=idx,
                        value=i.value,
                    )
                for e in e_lv_data.parts or []:
                    trait_bundle = e.override_trait_data_bundle
                    if trait_bundle and trait_bundle.candidates and e_lv == 0:
                        candidate = trait_bundle.candidates[0]
                        trait_text = ""
                        if candidate.additional_description is not None:
                            trait += f"\n|特性{idx}追加=yes"
                            trait_text = candidate.additional_description
                        elif candidate.override_descripton is not None:
                            trait_text = candidate.override_descripton
                        trait_text = compile_text(
                            rts,
                            format_paramed_text(
                                trait_text, blackboard_values(candidate.blackboard)
                            ),
                        )
                        if trait_text != "":
                            trait += f"\n|特性{idx}={trait_text}"
                    talent_bundle = e.add_or_override_talent_data_bundle
                    if talent_bundle and talent_bundle.candidates:
                        upgrade = talent_bundle.candidates[0].upgrade_description
                        if upgrade:
                            talent += f"\n|天赋{idx}={rts.compile(upgrade)}"
            missions = ""
            for idx, mission_id in enumerate(equip_info.mission_list or []):
                mission = mission_dict.get(mission_id)
                desc = (mission.desc if mission else None) or ""
                result = re.search(r"通关主题曲(.+?)；", desc)
                if result:
                    desc = desc.replace(result.group(1), f"[[{result.group(1)}]]")
                missions += f"\n|任务{idx + 1}={desc}"
            unlock = f"\n|解锁等级={equip_info.unlock_level}"
            favors = equip_info.unlock_favors
            if favors is not None:
                unlock_favor = "\n|解锁信赖=" + "0" if favors.get("1") == 0 else "?"
                unlock_favor += (
                    "\n|解锁信赖2=" + "50" if favors.get("2") == 2732 else "?"
                )
                unlock_favor += (
                    "\n|解锁信赖3=" + "100" if favors.get("3") == 10070 else "?"
                )
                unlock += unlock_favor
            else:
                unlock += "\n|解锁信赖=0"
            item_cost = ""
            for idx, lv_cost in enumerate((equip_info.item_cost or {}).values()):
                item_temp = []
                for i in lv_cost:
                    name = item_name(item_table, i.id)
                    if i.count < 10000:
                        item_temp.append(f"{{{{材料消耗|{name}|{i.count}}}}}")
                    else:
                        item_temp.append(
                            f"{{{{材料消耗|{name}|{i.count / 10000:.0f}万}}}}"
                        )
                if item_temp != []:
                    item_cost += "\n|材料消耗{idx}={item}".format(
                        idx="" if idx == 0 else str(idx + 1),
                        item=" ".join(item_temp),
                    )
            content.append(
                template.format(
                    name=equip_name,
                    type=f"{equip_info.type_name_1}-{equip_info.type_name_2}",
                    typeColor=type_color,
                    equipIcon=f"\n|模组图标={equip_info.uni_equip_icon}",
                    typeIcon=f"\n|类型图标={equip_info.type_icon}",
                    params=params,
                    trait=trait,
                    talent=talent,
                    missions=missions,
                    unlockCond=unlock,
                    itemCost=item_cost,
                    bInfo=b_info,
                )
            )
    return content


def get_related_item(char: CharacterData, item_table: InventoryData) -> str:
    potential_item = (item_table.items or {}).get(char.potential_item_id or "")
    if char.potential_item_id and potential_item is not None:
        return f"{{{{相关道具\n|干员简介={char.item_usage}\n|干员简介补充={char.item_desc}\n|信物用途={potential_item.usage}\n|信物描述={potential_item.description}\n}}}}"
    else:
        return f"{{{{相关道具\n|干员简介={char.item_usage}\n|干员简介补充={char.item_desc}\n}}}}"


def first_story_text(view: HandBookStoryViewData) -> str:
    """档案某一节的正文(每节只有一段)。"""

    return (view.stories or [])[0].story_text or ""


def get_stories_list(
    char: CharacterData, stories_table: HandbookInfoTable, char_key: str
) -> tuple[str, str]:
    handbook = (stories_table.handbook_dict or {}).get(char_key)
    if handbook is None:
        return "", "该干员无人员档案"
    stories_list_set = "{{人员档案set\n"
    story_views = handbook.story_text_audio or []
    stories1 = first_story_text(story_views[0])
    stories2 = first_story_text(story_views[1])
    stories3 = ""
    for i in story_views:
        if i.story_title == "临床诊断分析":
            stories3 = first_story_text(i)

    _doc_exp, doc2 = replace_doc_exp(stories1)
    doc7 = replace_basic_doc(stories1, "矿石病感染情况")
    result = re.search(r"确认为(.*)感染者", doc7)
    if result:
        doc8 = result.group(1) + "感染者"
    else:
        doc8 = doc7

    stories_list_set += "|性别={doc1}\n|{doc_exp}={doc2}\n|出身地={doc3}\n|生日={doc4}\n|种族={doc5}\n|身高={doc6}\n|矿石病感染情况={doc7}\n|是否感染者={doc8}\n\n|物理强度={test1}\n|战场机动={test2}\n|生理耐受={test3}\n|战术规划={test4}\n|战斗技巧={test5}\n|源石技艺适应性={test6}\n\n|体细胞与源石融合率={data1}\n|血液源石结晶密度={data2}\n}}}}".format(
        doc1=replace_basic_doc(stories1, "性别"),
        doc_exp="战斗经验",
        doc2=doc2,
        doc3=replace_basic_doc(stories1, "出身地"),
        doc4=replace_basic_doc(stories1, "生日"),
        doc5=replace_basic_doc(stories1, "种族"),
        doc6=replace_basic_doc(stories1, "身高"),
        doc7=doc7,
        doc8=doc8,
        test1=replace_basic_doc(stories2, "物理强度"),
        test2=replace_basic_doc(stories2, "战场机动"),
        test3=replace_basic_doc(stories2, "生理耐受"),
        test4=replace_basic_doc(stories2, "战术规划"),
        test5=replace_basic_doc(stories2, "战斗技巧"),
        test6=replace_basic_doc(stories2, "源石技艺适应性"),
        data1=replace_basic_doc(stories3, "体细胞与源石融合率").replace(" ", ""),
        data2=replace_basic_doc(stories3, "血液源石结晶密度").replace(" ", ""),
    )

    stories_list = "\n{{人员档案\n"
    for stories_id, view in enumerate(story_views):
        story = (view.stories or [])[0]
        story_text = (story.story_text or "").replace("\r\n", "\n")
        if char.name == "伊芙利特":
            story_text = handle_ifrit(story_text)
        story_title = view.story_title
        story_condition_id = story.un_lock_type
        if story_condition_id == "DIRECT":
            story_condition = "初始开放"
        elif story_condition_id == "AWAKE":
            story_condition = "提升至精英阶段2以查看"
        elif story_condition_id == "FAVOR":
            story_condition = f"提升信赖至{story.un_lock_param}%以查看"
        elif story_condition_id == "PATCH":
            story_condition = "升变解锁"
        else:
            story_condition = ""
        stories_list += (
            f"|档案{stories_id + 1}={story_title}\n"
            f"|档案{stories_id + 1}条件={story_condition}\n"
            f"|档案{stories_id + 1}文本={story_text}\n"
        )
    stories_list += "}}"
    return stories_list_set, stories_list


def get_handbook_avg(
    char: CharacterData,
    stories_table: HandbookInfoTable,
    char_key: str,
    medal_table: MedalData,
) -> str:
    handbook = (stories_table.handbook_dict or {}).get(char_key)
    if handbook is None or not handbook.handbook_avg_list:
        return ""
    avg_content = "\n==干员密录==\n{{干员密录|list="
    template = """\n{{{{干员密录/list
|精英化={phase}
|等级={lv}
|信赖={favor}{medaloverride}
|storySetName={name}{stories}
}}}}"""
    for avg in handbook.handbook_avg_list:
        phase: int | str | None = -1
        lv: int | str | None = -1
        favor: int | str | None = -1
        for p in avg.unlock_param or []:
            if p.unlock_type == "AWAKE":
                phase = p.unlock_param_1
                lv = p.unlock_param_2
            elif p.unlock_type == "FAVOR":
                favor = p.unlock_param_1
            else:
                logger.info(f"Unknown handbook_avg unLock condition for {char.name}.")
        medal_override = ""
        for medal in medal_table.medal_list or []:
            if medal.medal_type == "storyMedal" and avg.story_set_id in (
                medal.unlock_param or []
            ):
                medal_override = "\n|蚀刻章override=" + (medal.medal_id or "")
                break
        stories = ""
        avg_list = avg.avg_list or []
        for idx, story in enumerate(avg_list, start=1):
            story_txt = "{}/干员密录/{}".format("{{FULLPAGENAME}}", avg.sort_id)
            if len(avg_list) > 1:
                story_txt += f"-{story.story_sort}"
            stories += (
                f"\n|storyIntro{idx}={story.story_intro}\n|storyTxt{idx}={story_txt}"
            )
        avg_content += template.format(
            phase=phase,
            lv=lv,
            favor=favor,
            medaloverride=medal_override,
            name=avg.story_set_name,
            stories=stories,
        )
    avg_content += "\n}}"
    return avg_content


def get_handbook_stage(
    char: CharacterData,
    char_key: str,
    stories_table: HandbookInfoTable,
    item_table: InventoryData,
    rts: richtext.RichText,
) -> str:
    stage_info = (stories_table.handbook_stage_data or {}).get(char_key)
    if stage_info is None:
        return ""
    template = """
==悖论模拟==
{{{{悖论模拟
|name={stage_name}
|description={stage_desc}
|精英化={unlock_phase}
|等级={unlock_lv}
|zoneName={zoneNameForShow}
|stageName={stageNameForShow}
|picId={picId}{reward}
}}}}"""
    unlock_params = stage_info.unlock_param or []
    if len(unlock_params) != 1 or unlock_params[0].unlock_type != "AWAKE":
        logger.info(f"Unknown handbook_stage unLock condition for {char.name}.")
        unlock_phase, unlock_lv = "", ""
    else:
        unlock_phase = unlock_params[0].unlock_param_1
        unlock_lv = unlock_params[0].unlock_param_2
    reward = ""
    reward_items = stage_info.reward_item or []
    for idx, r in enumerate(reward_items, start=1):
        reward_name = item_name(item_table, r.id).rstrip()
        reward_count = r.count
        reward += f"\n|报酬内容{idx}={reward_name}\n|报酬数量{idx}={reward_count}"
    if len(reward_items) > 1:
        logger.info(f"Too many handbook_stage rewardItem for {char.name}.")
    desc = rts.compile(stage_info.description).replace("#FFFFFF", "#000000")
    return template.format(
        stage_name=stage_info.name,
        stage_desc=desc,
        zoneNameForShow="",
        stageNameForShow="",
        picId="",
        unlock_phase=unlock_phase,
        unlock_lv=unlock_lv,
        reward=reward,
    )


def trans_id(id):
    return {
        1: "一",
        2: "二",
        3: "三",
    }.get(id, "X")


def trans_profession(profession):
    return {
        "TANK": "重装",
        "PIONEER": "先锋",
        "SUPPORT": "辅助",
        "SNIPER": "狙击",
        "MEDIC": "医疗",
        "WARRIOR": "近卫",
        "CASTER": "术师",
        "SPECIAL": "特种",
    }.get(profession, profession)


def trans_team(team_id: str | None, team_table: TeamTable) -> str:
    if team_id is None:
        return ""
    team = team_table.get(team_id)
    if team is None:
        return "?"
    return team.power_name or ""


def trans_skill_type(skill_type):
    return {
        0: "",
        1: "\n|技能类型2=手动触发",
        2: "\n|技能类型2=自动触发",
        "PASSIVE": "",
        "MANUAL": "\n|技能类型2=手动触发",
        "AUTO": "\n|技能类型2=自动触发",
    }.get(skill_type, "")


def trans_sp_type(sp_type):
    # 8 不在客户端 SpType 枚举里,数据里直接是数字;模型把它转成字符串 "8"
    return {
        1: "自动回复",
        2: "攻击回复",
        4: "受击回复",
        8: "被动",
        "8": "被动",
        "INCREASE_WITH_TIME": "自动回复",
        "INCREASE_WHEN_ATTACK": "攻击回复",
        "INCREASE_WHEN_TAKEN_DAMAGE": "受击回复",
    }.get(sp_type, "")


def trans_position(position):
    return {"MELEE": "近战位", "RANGED": "远程位", "ALL": "近战/远程位"}[position]


def trans_phase(phase):
    return {"PHASE_0": 0, "PHASE_1": 1, "PHASE_2": 2, "PHASE_3": 3}.get(phase, phase)


def trans_rarity(rarity):
    return {
        "TIER_1": 0,
        "TIER_2": 1,
        "TIER_3": 2,
        "TIER_4": 3,
        "TIER_5": 4,
        "TIER_6": 5,
    }.get(rarity, rarity)


def replace_basic_doc(text, cond):
    p1 = rf"【{cond}】(\s*)([^\n]*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        return result.group(2).rstrip()
    return ""


def replace_doc_exp(text):
    p1 = r"【([^【]*)经验】(\s*)([^\n]*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        return result.group(1) + "经验", result.group(3).rstrip()
    return "", ""


def handle_ifrit(text):
    text = text.replace("|", "<nowiki>|</nowiki>")
    text = text.replace("=", "<nowiki>=</nowiki>")
    return text


def get_tal_condition(potentialRank, phase, level):
    condition = ""
    if phase == 0:
        condition += "精英0"
    elif phase == 1:
        condition += "精英1"
    elif phase == 2:
        condition += "精英2"
    if level != 1:
        condition += " " + str(level) + "级"
    if potentialRank != 0:
        condition += " 潜能" + str(potentialRank + 1)
    return condition


# {{{{ads/operator}}}}
content = """{{{{干员页面名|{name}|{name}|{name}}}}}{{{{pathnav2|干员一览}}}}
{{{{ads/normal}}}}{{{{ads/mobile}}}}
==干员信息==
{basic_info}
==获得方式==
{char_approach}
==属性==
{phases_data}
==攻击范围==
{range_data}
==天赋==
{talents}
==潜能提升==
{potential}
==技能=={skill}
==后勤技能==
{building}{token_info}
==精英化材料==
{phase}
==技能升级材料==
{skill_levelup}{equip}
==相关道具==
{related_item}
==干员档案==
{stories}
==语音记录==
{{{{参阅三|{{{{FULLPAGENAME}}}}|yy}}}}
{{{{:{{{{FULLPAGENAME}}}}/语音记录}}}}{handbook_avg}{handbook_stage}
==干员模型==
{{{{spineId}}}}
==注释与链接==
<references/>
{{{{干员导航}}}}"""


def iter_operators(character_table: dict[str, CharacterData]):
    """可获得的干员(去掉召唤物、装置和不可获得角色),名字去掉首尾空白。"""

    for char_key, char in character_table.items():
        char.name = (char.name or "").strip()
        if char.profession in ("TRAP", "TOKEN"):
            continue
        if char.is_not_obtainable:
            continue
        yield char_key, char


@job
def run(
    wiki: Wiki,
    character_table: params.CharacterTable,
    uniequip_table: params.UniEquipTable,
    battle_equip_table: params.BattleEquipTable,
    skill_table: params.SkillTable,
    building_data: params.BuildingData,
    item_table: params.ItemTable,
    team_table: params.HandbookTeamTable,
    stories_table: params.HandbookInfoTable,
    skin_table: params.SkinTable,
    gamedata_const: params.GamedataConst,
    charword_table: params.CharwordTable,
    medal_table: params.MedalTable,
    id_table: params.CharIdTable,
    rts: params.RichText,
    char_list: Annotated[list[str], params.category("分类:干员")],
) -> bool:
    flag_new_char = False
    update_token_page = False

    for char_key, char in iter_operators(character_table):
        if char.name in char_list:
            continue
        if char.name not in id_table:
            logger.info(f"Unknown Character: {char_key} {char.name}.")

        basic_info = get_basic_info(
            char,
            char_key,
            id_table,
            rts,
            uniequip_table,
            team_table,
            skin_table,
            charword_table,
        )
        char_approach = get_char_approach(char, id_table)
        phases_data = get_phases_data(
            char, char_key, uniequip_table, battle_equip_table, team_table
        )
        range_data = get_range_data(char)
        talent_list = get_talent_list(char, rts)
        potential_list = get_potential_list(char)
        skill_list = get_skill_list(char, skill_table, rts)
        token_info = get_token_info(
            wiki,
            char,
            update_token_page,
            character_table,
            skill_table,
            rts,
        )
        building_skill = get_building_skill(building_data, char_key)
        phase_list = get_phase_list(char, gamedata_const, item_table)
        skill_levelup_list = get_skill_levelUp_list(char, item_table)
        battle_equip = "".join(
            get_battle_equip(
                char,
                char_key,
                battle_equip_table,
                uniequip_table,
                item_table,
                rts,
            )
        )
        related_item = get_related_item(char, item_table)
        stories_list_set, stories_list = get_stories_list(char, stories_table, char_key)
        stories_list = stories_list_set + stories_list
        handbook_avg = get_handbook_avg(char, stories_table, char_key, medal_table)
        handbook_stage = get_handbook_stage(
            char, char_key, stories_table, item_table, rts
        )

        char_info = content.format(
            name=char.name,
            char_approach=char_approach,
            basic_info=basic_info,
            phases_data=phases_data,
            range_data=range_data,
            talents=talent_list,
            potential=potential_list,
            skill=skill_list,
            building=building_skill,
            token_info=token_info,
            phase=phase_list,
            skill_levelup=skill_levelup_list,
            equip=battle_equip,
            related_item=related_item,
            stories=stories_list,
            handbook_avg=handbook_avg,
            handbook_stage=handbook_stage,
        )

        flag_new_char = True
        wiki.edit(
            title=char.name,
            text=char_info,
            summary="init",
            bot=None,
            minor=True,
            createonly="1",
        )
        wiki.protect(
            title=char.name,
            protections="edit=autoconfirmed|move=sysop",
            reason="protect",
        )
        if char.name != char.appellation:
            redirect_text = f"#redirect [[{char.name}]]"
            wiki.edit(
                title=char.appellation,
                text=redirect_text,
                summary="init",
                createonly=True,
            )
        logger.info(f"Created: {char.name}.")

    return flag_new_char


@job
def update(
    wiki: Wiki,
    character_table: params.CharacterTable,
    uniequip_table: params.UniEquipTable,
    battle_equip_table: params.BattleEquipTable,
    building_data: params.BuildingData,
    item_table: params.ItemTable,
    team_table: params.HandbookTeamTable,
    skin_table: params.SkinTable,
    charword_table: params.CharwordTable,
    rts: params.RichText,
) -> None:
    for char_key, char in iter_operators(character_table):
        if char_key in [
            "char_512_aprot",
            "char_508_aguard",
            "char_509_acast",
            "char_511_asnipe",
            "char_510_amedic",
            "char_513_apionr",
        ]:
            continue
        origin_text = wiki.read(char.name)
        new_text = origin_text

        # 更新后勤技能
        building_skill = get_building_skill(building_data, char_key)
        num1 = new_text.find("==后勤技能==")
        num2 = new_text.find("==召唤物信息==")
        if num2 == -1:
            num2 = new_text.find("==精英化材料==")
        new_text = (
            new_text[:num1] + "==后勤技能==\n" + building_skill + "\n" + new_text[num2:]
        )

        # 更新属性
        phases_data = get_phases_data(
            char, char_key, uniequip_table, battle_equip_table, team_table
        )
        num1 = new_text.find("==属性==")
        num2 = new_text.find("==攻击范围==")
        new_text = new_text[:num1] + "==属性==\n" + phases_data + "\n" + new_text[num2:]

        # 更新模组
        equip_list = get_battle_equip(
            char,
            char_key,
            battle_equip_table,
            uniequip_table,
            item_table,
            rts,
        )
        num1 = new_text.find("==模组==")
        num2 = new_text.find("\n==相关道具==")
        if num1 == -1:
            num1 = num2
            new_text = new_text[:num1].rstrip() + "".join(equip_list) + new_text[num2:]
        else:
            equip_text = new_text[num1:num2]
            for equip in equip_list:
                result = re.search("===(.+?)===", equip)
                if not result:
                    continue
                if f"==={result.group(1)}===" not in equip_text:
                    equip_text += equip
            new_text = new_text[:num1] + equip_text + new_text[num2:]

        # 更新干员cv
        num1 = new_text.find("\n|画师=")
        num2 = new_text.find("\n|精英0介绍=")
        cv = format_cv(charword_table, char_key)
        # 这里与建页不同:画师信息不完整时整段留空
        drawer, drawer_append, complete = phase_drawers(skin_table, char_key)
        drawer = "\n|画师=" + drawer + drawer_append if complete else "\n|画师="
        new_text = new_text[:num1] + drawer + cv + new_text[num2:]

        if new_text != origin_text:
            wiki.edit(title=char.name, text=new_text, summary="update")
            logger.info(f"Updated: {char.name}.")
        else:
            logger.info(f"Same: {char.name}.")


@job
def update_handbook(
    wiki: Wiki,
    character_table: params.CharacterTable,
    item_table: params.ItemTable,
    stories_table: params.HandbookInfoTable,
    medal_table: params.MedalTable,
    rts: params.RichText,
) -> None:
    for char_key, char in iter_operators(character_table):
        handbook_avg = get_handbook_avg(char, stories_table, char_key, medal_table)
        handbook_stage = get_handbook_stage(
            char, char_key, stories_table, item_table, rts
        )

        if handbook_avg != "" or handbook_stage != "":
            origin_text = wiki.read(char.name)

            num1 = origin_text.find("/语音记录}}")
            num2 = origin_text.find("\n==干员模型==")
            num3 = origin_text.find("\n==干员异格任务==")
            if num3 > 0:
                num2 = min(num2, num3)
            new_text = (
                origin_text[:num1]
                + "/语音记录}}"
                + handbook_avg
                + handbook_stage
                + origin_text[num2:]
            )

            if new_text != origin_text:
                wiki.edit(
                    title=char.name,
                    text=new_text,
                    summary="更新干员密录&悖论模拟",
                )
                logger.info(f"Updated: {char.name}.")
            else:
                logger.info(f"Same: {char.name}.")
