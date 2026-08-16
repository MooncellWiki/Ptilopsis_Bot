import copy
import json
import os
import re
from collections.abc import Callable, Sequence

import requests
from pydantic import BaseModel, ValidationError

from ptilopsis.gamedata.stage import (
    StageData,
    StageDataDisplayDetailRewards,
    StageTable,
)
from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles
from ptilopsis.wikitext import WikiTemplate, inline_template

# 渲染视图,字段与页面上的 wiki 模板参数一一对应


class DropView(BaseModel):
    name: str
    furniture: bool = False
    occurrence: str = ""


class RewardGroupView(BaseModel):
    label: str
    drops: list[DropView]


class LevelInfoView(BaseModel):
    character_limit: int
    initial_cost: int
    max_cost: int
    max_life_point: int
    enemy_count: str
    map_size: str
    time_label: str
    time: str


class BlackboardView(BaseModel):
    # 黑板值只会被 str() 进注释,类型放宽到上游可能出现的所有形态:
    # 收窄成 int | float 会让一条注释的降级变成整个 job 的 ValidationError
    key: str
    value: int | float | str | None
    value_str: str | None


class TileEffectView(BaseModel):
    name: str
    blackboards: list[list[BlackboardView]]


class SandboxMapView(BaseModel):
    code: str
    name: str
    stage_id: str


class BasicStageView(BaseModel):
    heading: str | None = None
    code: str
    name: str
    stage_id: str
    map_override: str = ""
    stage_type: str
    subtype: str | None = None
    boss: bool = False
    difficulty: str | None = None
    battle_stage: bool | None = None
    unlock_condition: str | None = None
    recommended_level: str | None = None
    zone: str | None = None
    level: LevelInfoView | None = None
    description: str | None = None
    ap_cost: int | None = None
    practice_cost: int | None = None
    resource_overview: list[str] | None = None
    action_cost: int | None = None
    power_cost: int | None = None
    rewards: list[RewardGroupView] = []
    tile_effects: list[TileEffectView] = []
    terrain_tags: list[str] | None = None
    sandbox_map: SandboxMapView | None = None


class AssaultStageView(BaseModel):
    heading: str
    code: str
    name: str
    stage_type: str
    subtype: str | None = None
    difficulty: str
    unlock_condition: str
    recommended_level: str | None = None
    zone: str
    character_limit: int
    initial_cost: int
    max_cost: int
    description: str
    ap_cost: int
    practice_cost: int
    rewards: list[RewardGroupView] = []
    intelligence: list[str] = []


class CampaignStageView(BaseModel):
    code: str
    name: str
    stage_id: str
    commission: bool
    stage_type: str
    difficulty: str
    unlock_condition: str
    zone: str
    level: LevelInfoView | None = None
    description: str
    ap_cost: int
    rewards: list[RewardGroupView] = []
    ap_returns: list[str] = []
    diamond_rewards: list[str] = []
    terrain_tags: list[str] | None = None


class EnemyOverrideView(BaseModel):
    label: str
    # 覆盖值原样进模板,构造时就 str() 掉:上游给什么类型都不会校验失败,
    # 且与重构前的 "{}".format(m_value) 逐字节一致(None 也渲染成 None)
    value: str


class EnemyView(BaseModel):
    index: int
    name: str
    count: str
    level: int
    display_name: str | None = None
    count_lower: str | None = None
    note: str | None = None
    overrides: list[EnemyOverrideView] = []


class SquadUnitView(BaseModel):
    name: str
    simulation: bool = False
    phase: int | str = ""
    level: int | str = ""
    skill_name: str = ""
    main_skill_level: int | str = ""
    potential: int | None = None


class SquadSectionView(BaseModel):
    title: str
    units: list[SquadUnitView]
    note: str


class CampaignProgressItemView(BaseModel):
    name: str
    count: int


class CampaignProgressRowView(BaseModel):
    kill_count: int
    items: list[CampaignProgressItemView]
    break_fee_add: int


class CampaignProgressView(BaseModel):
    rows: list[CampaignProgressRowView]


class NormalPageView(BaseModel):
    normal: BasicStageView
    assault: AssaultStageView | None = None
    enemies: list[EnemyView] | None = None
    squads: list[SquadSectionView] = []
    material_drop: bool = False


class CampaignPageView(BaseModel):
    stage: CampaignStageView
    enemies: list[EnemyView] | None = None
    squads: list[SquadSectionView] = []
    progress: CampaignProgressView


class RoguelikePageView(BaseModel):
    normal: BasicStageView
    assault: AssaultStageView | None = None
    enemies: list[EnemyView] | None = None


class BasicPageView(BaseModel):
    stage: BasicStageView
    enemies: list[EnemyView] | None = None
    squads: list[SquadSectionView] = []


class RecalRunePageView(BasicPageView):
    display_title: str


class DisambiguationLinkView(BaseModel):
    page_name: str
    activity_name: str | None = None


def parse_stage_type(stage_type):
    return {
        "MAIN": "主线",
        "SUB": "支线",
        "DAILY": "日常",
        "GUIDE": "教程",
        "ACTIVITY": "活动",
        "CAMPAIGN": "剿灭",
        "SPECIAL_STORY": "特殊剧情",
        "CLIMB_TOWER": "保全派驻",
    }.get(stage_type, "未知类型")


def parse_drop_type(drop_type):
    return {
        0: "None",
        1: "首次掉落",
        2: "常规掉落",
        3: "特殊掉落",
        4: "额外物资",
        5: "作战失败返回",
        6: "报酬",  # 剿灭给的合成玉
        7: "幸运掉落",  # 家具
        8: "三星获得",
        "NONE": "None",
        "ONCE": "首次掉落",
        "NORMAL": "常规掉落",
        "SPECIAL": "特殊掉落",
        "ADDITIONAL": "额外物资",
        "APRETURN": "作战失败返回",
        "DIAMOND_MATERIAL": "报酬",  # 剿灭给的合成玉
        "FUNITURE_DROP": "幸运掉落",  # 家具
        "COMPLETE": "三星获得",
    }.get(drop_type, "None")


def parse_occ_type(occ_percent, drop_type, if_furni):
    if if_furni:
        ex = ":2="
    else:
        ex = ":"
    if drop_type in [4, 6, 7] or drop_type in [
        "ADDITIONAL",
        "DIAMOND_MATERIAL",
        "FUNITURE_DROP",
    ]:
        return ""
    elif drop_type == 8 or drop_type == "COMPLETE":
        return ex + "三星获得"
    elif drop_type == 1 or drop_type == "ONCE":
        return ex + "首次掉落"
    else:
        return ex + {
            0: "固定掉落",  # Always
            1: "大概率",  # Almost
            2: "概率掉落",  # Usual
            3: "小概率",  # Often
            4: "罕见",  # Sometimes
            5: "从不",  # Never
            6: "完成",  # Complete
            "ALWAYS": "固定掉落",  # Always
            "ALMOST": "大概率",  # Almost
            "USUAL": "概率掉落",  # Usual
            "OFTEN": "小概率",  # Often
            "SOMETIMES": "罕见",  # Sometimes
            "NEVER": "从不",  # Never
            "DEFINITELY_BUFF": "完成",  # Complete
        }.get(occ_percent, "未知类型")


def parse_rune_profession(professionMask):
    if professionMask == 0:
        return "未知职业范围"
    p_list = bin(professionMask)[2:]
    p_list = "0" * (10 - len(p_list)) + p_list
    p_text = []
    if p_list[0] == "1":
        p_text.append("先锋")
    if p_list[1] == "1":
        p_text.append("障碍物")
    if p_list[2] == "1":
        p_text.append("召唤物")
    if p_list[3] == "1":
        p_text.append("特种")
    if p_list[4] == "1":
        p_text.append("术师")
    if p_list[5] == "1":
        p_text.append("辅助")
    if p_list[6] == "1":
        p_text.append("医疗")
    if p_list[7] == "1":
        p_text.append("重装")
    if p_list[8] == "1":
        p_text.append("狙击")
    if p_list[9] == "1":
        p_text.append("近卫")
    return "和".join(p_text) + "干员"


def build_rune_buffs(runes: list[dict]) -> tuple[int, list[str]]:
    """扫描 runes,取出部署位增减和敌方属性加成。

    返回 (部署上限增量, 情报行)。突袭和集成战略紧急作战两处都要这份结果。
    """

    climit = 0
    ebuff = {"atk": 1.0, "def": 1.0, "max_hp": 1.0, "flag": 0}
    for rune in runes:
        if rune["key"] in ["gbuff_placable_char_num", "global_placable_char_num_add"]:
            climit = int(rune["blackboard"][0]["value"])
        if rune["key"] in ["enemy_attribute_mul", "ebuff_attribute"]:
            ebuff["flag"] = 1
            for item in rune["blackboard"]:
                ebuff[item["key"]] = item["value"]

    intelligence = []
    if ebuff["flag"] == 1:
        ebuff_desc = []
        if ebuff["atk"] != 1.0:
            ebuff_desc.append("攻击力提升至{:.0%}".format(ebuff["atk"]))
        if ebuff["def"] != 1.0:
            ebuff_desc.append("防御力提升至{:.0%}".format(ebuff["def"]))
        if ebuff["max_hp"] != 1.0:
            ebuff_desc.append("生命值提升至{:.0%}".format(ebuff["max_hp"]))
        if ebuff_desc:
            intelligence.append("敌方单位的" + "，".join(ebuff_desc))
        else:
            intelligence.append("敌方单位无变化")
    return climit, intelligence


def build_rune_lines(runes: list[dict]) -> list[str]:
    rune_lines = []
    for rune in runes:
        text = []
        if rune["difficultyMask"] == 2 or rune["difficultyMask"] in [
            "FOUR_STAR",
            "SIX_STAR",
        ]:  # 突袭
            pass
        elif rune["difficultyMask"] == 1 or rune["difficultyMask"] == "NORMAL":  # 普通
            text.append("普通难度")
        elif rune["difficultyMask"] == "EASY":  # 普通
            text.append("简单难度")
        elif rune["difficultyMask"] == 0 or rune["difficultyMask"] == "NONE":  # 未知
            text.append("未知关卡难度")

        if rune["buildableMask"] == 3 or rune["buildableMask"] == "ALL":  # 全部单位
            pass
        elif (
            rune["buildableMask"] == 2 or rune["buildableMask"] == "RANGED"
        ):  # 远程单位
            text.append("远程单位")
        elif rune["buildableMask"] == 1 or rune["buildableMask"] == "MELEE":  # 近战单位
            text.append("近战单位")
        elif rune["buildableMask"] == 0 or rune["buildableMask"] == "NONE":  # 未知
            text.append("未知单位")

        if rune["professionMask"] != 1023:
            if isinstance(rune["professionMask"], int):
                text.append(parse_rune_profession(rune["professionMask"]))
            else:
                text.append(rune["professionMask"])
        text.append(rune["key"])

        blackboard = []
        for i in rune["blackboard"]:
            text2 = "{}: {}".format(i["key"], i["value"])
            if i["valueStr"] is not None:
                text2 += " ({})".format(i["valueStr"])
            blackboard.append(text2)

        rune_lines.append(" ".join(text) + ": " + ", ".join(blackboard))
    return rune_lines


def parse_drop_item(
    item_type: str,
    item_id: str,
    character_table: dict,
    building_data: dict,
    item_table: dict,
) -> str:
    """把掉落物的类型与 id 翻译成 wiki 上的显示名。

    掉落在数据里有两种载体:关卡的 displayDetailRewards 已经建模成
    StageDataDisplayDetailRewards,而回忆关卡的 rewardItem、剿灭进度奖励仍是
    裸 dict。取字段这一步留给调用方,这里只认类型和 id。
    """

    try:
        if item_type == "CHAR":
            return character_table[item_id]["name"]
        if item_type == "FURN":
            return building_data["customData"]["furnitures"][item_id]["name"]
        if item_type in [
            "MATERIAL",
            "CARD_EXP",
            "TKT_RECRUIT",
            "GOLD",
            "ACTIVITY_COIN",
            "ACTIVITY_ITEM",
            "ET_STAGE",
            "DIAMOND",
            "DIAMOND_SHD",
            "LGG_SHD",
            "HGG_SHD",
        ]:
            return item_table["items"][item_id]["name"].strip()
        logger.info(f"Unknown drop item {item_id}")
        return item_table["items"][item_id]["name"].strip()
    except (AttributeError, KeyError, TypeError):
        return f"物品{item_id}"


def build_enemy_overrides(overwritten_data: dict) -> list[EnemyOverrideView]:
    fields = [
        (("name",), "显示名"),
        (("attributes", "maxHp"), "生命值"),
        (("attributes", "atk"), "攻击力"),
        (("attributes", "def"), "防御力"),
        (("attributes", "magicResistance"), "法术抗性"),
        (("attributes", "baseAttackTime"), "攻击间隔"),
        (("attributes", "massLevel"), "重量等级"),
        (("attributes", "moveSpeed"), "移动速度"),
        (("attributes", "hpRecoveryPerSec"), "生命恢复速度"),
        (("rangeRadius",), "攻击范围半径"),
        (("lifePointReduce",), "目标价值"),
    ]
    overrides = []
    for path, label in fields:
        value = overwritten_data
        for key in path:
            value = value[key]
        if value["m_defined"]:
            overrides.append(
                EnemyOverrideView(label=label, value=str(value["m_value"]))
            )
    return overrides


def build_reward_groups(
    rewards: Sequence[dict | StageDataDisplayDetailRewards],
    character_table: dict,
    building_data: dict,
    item_table: dict,
) -> list[RewardGroupView]:
    reward_list = {
        "NONE": [],
        "ONCE": [],
        "NORMAL": [],
        "SPECIAL": [],
        "ADDITIONAL": [],
        "APRETURN": [],
        "DIAMOND_MATERIAL": [],
        "FUNITURE_DROP": [],
        "COMPLETE": [],
        "CHARM_DROP": [],
        "OVERRIDE_DROP": [],
        "ITEM_RETURN": [],
    }
    for raw_reward in rewards:
        # 关卡表里的掉落已经建模,剿灭的 dropGains 仍是裸 dict,这里统一成模型
        if isinstance(raw_reward, StageDataDisplayDetailRewards):
            reward = raw_reward
        else:
            reward = StageDataDisplayDetailRewards.model_validate(raw_reward)
        furniture = reward.type == "FURN"
        occurrence = parse_occ_type(reward.occ_percent, reward.drop_type, furniture)
        occurrence_prefix = ":2=" if furniture else ":"
        if occurrence.startswith(occurrence_prefix):
            occurrence = occurrence.removeprefix(occurrence_prefix)
        drop = DropView(
            name=parse_drop_item(
                reward.type, reward.id, character_table, building_data, item_table
            ),
            furniture=furniture,
            occurrence=occurrence,
        )
        if reward.drop_type not in reward_list:
            reward_list[reward.drop_type] = []
        reward_list[reward.drop_type].append(drop)
    reward_list["ONCE"] = reward_list["COMPLETE"] + reward_list["ONCE"]
    reward_list["COMPLETE"] = []

    groups = []
    for drop_type in reward_list:
        label = parse_drop_type(drop_type)
        drops = reward_list[drop_type]
        if drops and label != "None":
            group = RewardGroupView(label=label, drops=drops)
            groups.append(group)
            if drop_type == 2 or drop_type == "NORMAL":
                logger.info("\t—— " + render_reward_group(group))
    return groups


def analyze_action(actions, normal_hidden_group, notCount_list):
    action_list = [ActionInfo(action) for action in actions]
    pack_dict = {}
    for action in action_list:
        if action.random_key is not None and action.random_pack is not None:
            if (
                action.random_pack in pack_dict
                and pack_dict[action.random_pack] != action.random_key
            ):
                logger.info(
                    "Error: randomSpawnGroupPackKey duplicate! "
                    f"({action.random_key} - {action.random_pack})"
                )
            pack_dict[action.random_pack] = action.random_key
    for action in action_list:
        action.update_pack(pack_dict)
    min_time, action_enemy_min, action_enemy_max = 0.0, 0, 0
    fragment_flag = False

    def time_filter(action):
        return action.hidden_group is None or action.hidden_group in normal_hidden_group

    def num_filter(action):
        return (action.key is not None or action.random_key is not None) and (
            action.hidden_group is None or action.hidden_group in normal_hidden_group
        )

    time_dict = {"fix_time": -1.0, "random_group": {}}
    num_dict = {"base_num": 0, "random_group": {}}
    # 最短用时
    for action in filter(time_filter, action_list):
        fragment_flag = True
        if action.random_key is not None:
            if action.random_key not in time_dict["random_group"]:
                time_dict["random_group"][action.random_key] = {
                    "single": 1000000.0,
                    "pack": {},
                }
            if action.random_pack is not None:
                if (
                    action.random_pack
                    not in time_dict["random_group"][action.random_key]["pack"]
                ):
                    time_dict["random_group"][action.random_key]["pack"][
                        action.random_pack
                    ] = -1.0
                time_dict["random_group"][action.random_key]["pack"][
                    action.random_pack
                ] = max(
                    action.time,
                    time_dict["random_group"][action.random_key]["pack"][
                        action.random_pack
                    ],
                )
            else:
                time_dict["random_group"][action.random_key]["single"] = min(
                    action.time, time_dict["random_group"][action.random_key]["single"]
                )
        else:
            time_dict["fix_time"] = max(action.time, time_dict["fix_time"])
    if time_dict["random_group"] != {}:
        pack_time_list = [0.0]
        for action_k_iter in time_dict["random_group"]:
            pack_time = 1000000.0
            if time_dict["random_group"][action_k_iter]["pack"] != {}:
                pack_time = min(
                    pack_time,
                    min(time_dict["random_group"][action_k_iter]["pack"].values()),
                )
            if time_dict["random_group"][action_k_iter]["single"] != {}:
                pack_time = min(
                    pack_time,
                    max(time_dict["random_group"][action_k_iter]["single"], 0),
                )
            pack_time_list.append(pack_time)
        min_time = max(0.0, time_dict["fix_time"], min(pack_time_list))
    else:
        min_time = max(0.0, time_dict["fix_time"])

    # 敌人数量
    for action in filter(num_filter, action_list):
        if action.key in notCount_list:
            continue
        if action.random_key is not None:
            if action.random_key not in num_dict["random_group"]:
                num_dict["random_group"][action.random_key] = {"single": [], "pack": {}}
            if action.random_pack is not None:
                if (
                    action.random_pack
                    not in num_dict["random_group"][action.random_key]["pack"]
                ):
                    num_dict["random_group"][action.random_key]["pack"][
                        action.random_pack
                    ] = 0
                num_dict["random_group"][action.random_key]["pack"][
                    action.random_pack
                ] += action.count
            else:
                num_dict["random_group"][action.random_key]["single"].append(
                    action.count
                )
        else:
            num_dict["base_num"] += action.count
    if num_dict["random_group"] != {}:
        for action_k_iter in num_dict["random_group"]:
            pack_min, pack_max = 100000, -1
            if num_dict["random_group"][action_k_iter]["pack"] != {}:
                pack_min = min(
                    pack_min,
                    min(num_dict["random_group"][action_k_iter]["pack"].values()),
                )
                pack_max = max(
                    pack_max,
                    max(num_dict["random_group"][action_k_iter]["pack"].values()),
                )
            if num_dict["random_group"][action_k_iter]["single"] != []:
                pack_min = min(
                    pack_min, min(num_dict["random_group"][action_k_iter]["single"])
                )
                pack_max = max(
                    pack_max, max(num_dict["random_group"][action_k_iter]["single"])
                )
            action_enemy_min += pack_min
            action_enemy_max += pack_max
        action_enemy_min += num_dict["base_num"]
        action_enemy_max += num_dict["base_num"]
    else:
        action_enemy_min = num_dict["base_num"]
        action_enemy_max = num_dict["base_num"]

    return min_time, action_enemy_min, action_enemy_max, fragment_flag


def build_level_info(
    level_table: dict, not_count_list: dict, *, use_countdown: bool = False
) -> LevelInfoView:
    enemy_count = {"min": 0, "max": 0}
    min_time = 0.0
    normal_hidden_group = analyze_normal_hidden_group(level_table)
    not_count_list_level = copy.deepcopy(not_count_list)
    for enemy in level_table["enemyDbRefs"]:
        if enemy["useDb"] is False:
            try:
                if enemy["overwrittenData"]["notCountInTotal"]["m_defined"] is True:
                    if enemy["overwrittenData"]["notCountInTotal"]["m_value"] is True:
                        if enemy["id"] not in not_count_list_level:
                            not_count_list_level[enemy["id"]] = []
                        not_count_list_level[enemy["id"]].append(enemy["level"])
            except (KeyError, TypeError):
                continue
    for wave in level_table["waves"]:
        min_time += wave["preDelay"] + wave["postDelay"]
        for fragment in wave["fragments"]:
            time, action_enemy_min, action_enemy_max, fragment_flag = analyze_action(
                fragment["actions"], normal_hidden_group, not_count_list_level
            )
            enemy_count["min"] += action_enemy_min
            enemy_count["max"] += action_enemy_max
            if fragment_flag:
                min_time += fragment["preDelay"]
                min_time += time
    if enemy_count["min"] == enemy_count["max"]:
        enemy_count_text = str(enemy_count["min"])
    else:
        enemy_count_text = f"{enemy_count['min']}~{enemy_count['max']}"

    if use_countdown and level_table["options"]["maxPlayTime"] > 0:
        max_play_time = level_table["options"]["maxPlayTime"]
        time_label = "倒计时"
        time_text = f"{int(max_play_time / 60)}分{int(max_play_time % 60)}秒"
    elif abs(min_time - int(min_time)) < 0.0001:
        time_label = "最短用时"
        time_text = f"{int(min_time / 60)}分{int(min_time % 60)}秒"
    else:
        time_label = "最短用时"
        time_text = f"{int(min_time / 60)}分{min_time % 60:.1f}秒"

    return LevelInfoView(
        character_limit=level_table["options"]["characterLimit"],
        initial_cost=level_table["options"]["initialCost"],
        max_cost=level_table["options"]["maxCost"],
        max_life_point=level_table["options"]["maxLifePoint"],
        enemy_count=enemy_count_text,
        map_size=(
            f"{len(level_table['mapData']['map'][0])}×"
            f"{len(level_table['mapData']['map'])}"
        ),
        time_label=time_label,
        time=time_text,
    )


def analyze_normal_hidden_group(level_table):
    normal_hidden_group = []
    if level_table["runes"]:
        try:
            for rune in level_table["runes"]:
                if (
                    rune["difficultyMask"] == 1 or rune["difficultyMask"] == "NORMAL"
                ) and rune["key"] == "level_hidden_group_enable":
                    for d in rune["blackboard"]:
                        if d["key"] == "key":
                            normal_hidden_group.append(d["valueStr"])
        except Exception:
            logger.info("hiddenGroup解析出错.")
    return normal_hidden_group


def build_char_card_info(
    level_table, stage_page_name, character_table, skill_table, stage_charId=None
) -> SquadSectionView | None:
    units = []
    memory_desc = ""
    favor_point, fp_set = [], set()
    try:
        if (
            level_table["predefines"] is None
            or "characterCards" not in level_table["predefines"]
        ):
            return None
        for char_card in level_table["predefines"]["characterCards"]:
            char_card_name = character_table[char_card["inst"]["characterKey"]]["name"]
            if (
                stage_charId is not None
                and char_card["inst"]["characterKey"] == stage_charId
            ):
                units.append(SquadUnitView(name=char_card_name, simulation=True))
                memory_desc = "模拟对象干员的状态数据与玩家持有的一致，请以实际情况为准"
                continue
            if char_card["skillIndex"] != -1:
                skill_name = skill_table[
                    character_table[char_card["inst"]["characterKey"]]["skills"][
                        char_card["skillIndex"]
                    ]["skillId"]
                ]["levels"][0]["name"]
            else:
                skill_name = ""
            potential_rank = char_card["inst"]["potentialRank"]
            units.append(
                SquadUnitView(
                    name=char_card_name,
                    phase={
                        "PHASE_0": 0,
                        "PHASE_1": 1,
                        "PHASE_2": 2,
                        "PHASE_3": 3,
                    }.get(char_card["inst"]["phase"], char_card["inst"]["phase"]),
                    level=char_card["inst"]["level"],
                    skill_name=skill_name,
                    main_skill_level=char_card["mainSkillLvl"],
                    potential=potential_rank + 1 if potential_rank != 0 else None,
                )
            )
            this_p = min(200, char_card["inst"]["favorPoint"] * 2)
            fp_set.add(this_p)
            favor_point.append(f"{char_card_name}信赖值为{this_p}%")
        if units:
            if favor_point and memory_desc:
                memory_desc = "<br>" + memory_desc
            if len(fp_set) == 1 and len(favor_point) > 1:
                if stage_charId is not None:
                    fp_desc = (
                        f"本关卡除模拟对象干员外的随队干员信赖值都为{fp_set.pop()}%"
                    )
                else:
                    fp_desc = f"本关卡随队干员信赖值都为{fp_set.pop()}%"
            else:
                fp_desc = "，".join(favor_point)
            return SquadSectionView(
                title="固定编队", units=units, note=fp_desc + memory_desc
            )
    # ValidationError 也要接住:干员数据缺字段时只该丢掉这一关的固定编队,
    # 不能让异常冒泡打断整轮三千多个关卡的生成
    except (IndexError, KeyError, TypeError, ValidationError):
        logger.info(f"{stage_page_name}: characterCards error.")
    return None


def build_char_insert_info(
    level_table, stage_page_name, character_table, skill_table
) -> SquadSectionView | None:
    units = []
    favor_point, fp_set = [], set()
    try:
        if (
            level_table["predefines"] is None
            or "characterInsts" not in level_table["predefines"]
        ):
            return None
        for char_insert in level_table["predefines"]["characterInsts"]:
            char_insert_name = character_table[char_insert["inst"]["characterKey"]][
                "name"
            ]
            if char_insert["skillIndex"] != -1:
                skill_name = skill_table[
                    character_table[char_insert["inst"]["characterKey"]]["skills"][
                        char_insert["skillIndex"]
                    ]["skillId"]
                ]["levels"][0]["name"]
            else:
                skill_name = ""
            potential_rank = char_insert["inst"]["potentialRank"]
            units.append(
                SquadUnitView(
                    name=char_insert_name,
                    phase={
                        "PHASE_0": 0,
                        "PHASE_1": 1,
                        "PHASE_2": 2,
                        "PHASE_3": 3,
                    }.get(
                        char_insert["inst"]["phase"],
                        char_insert["inst"]["phase"],
                    ),
                    level=char_insert["inst"]["level"],
                    skill_name=skill_name,
                    main_skill_level=char_insert["mainSkillLvl"],
                    potential=potential_rank + 1 if potential_rank != 0 else None,
                )
            )
            this_p = min(200, char_insert["inst"]["favorPoint"] * 2)
            fp_set.add(this_p)
            favor_point.append(f"{char_insert_name}信赖值为{this_p}%")
        if units:
            if len(fp_set) == 1 and len(favor_point) > 1:
                fp_desc = f"本关卡已部署干员信赖值都为{fp_set.pop()}%"
            else:
                fp_desc = "，".join(favor_point)
            return SquadSectionView(title="已部署干员", units=units, note=fp_desc)
    except (IndexError, KeyError, TypeError, ValidationError):
        logger.info(f"{stage_page_name}: characterInsts error.")
    return None


def build_squad_sections(
    level_table: dict,
    stage_page_name: str,
    character_table: dict,
    skill_table: dict,
    *,
    stage_char_id: str | None = None,
    include_inserted: bool = True,
) -> list[SquadSectionView]:
    sections = []
    fixed = build_char_card_info(
        level_table,
        stage_page_name,
        character_table,
        skill_table,
        stage_charId=stage_char_id,
    )
    if fixed is not None:
        sections.append(fixed)
    if include_inserted:
        inserted = build_char_insert_info(
            level_table, stage_page_name, character_table, skill_table
        )
        if inserted is not None:
            sections.append(inserted)
    return sections


def build_tile_effects(
    level_table: dict, stage_tile_info: dict
) -> list[TileEffectView]:
    try:
        tiles = level_table["mapData"]["tiles"]
        if not tiles:
            return []
    except (KeyError, TypeError):
        return []
    tile_blackboard_dict = {}
    for tile in filter(lambda x: x["blackboard"], tiles):
        if tile["tileKey"] not in tile_blackboard_dict:
            tile_blackboard_dict[tile["tileKey"]] = []
        if tile["blackboard"] not in tile_blackboard_dict[tile["tileKey"]]:
            tile_blackboard_dict[tile["tileKey"]].append(tile["blackboard"])
    if tile_blackboard_dict == {}:
        return []

    effects = []
    for tile_key, blackboards in tile_blackboard_dict.items():
        tile_info = stage_tile_info.get(tile_key)
        if hasattr(tile_info, "name"):
            tile_name = tile_info.name
        elif tile_info is not None:
            tile_name = tile_info["name"]
        else:
            tile_name = tile_key
        effects.append(
            TileEffectView(
                name=tile_name,
                blackboards=[
                    [
                        BlackboardView(
                            key=item["key"],
                            value=item["value"],
                            value_str=item["valueStr"],
                        )
                        for item in blackboard
                    ]
                    for blackboard in blackboards
                ],
            )
        )
    return effects


def build_enemies(
    level_table: dict,
    enemy_table: dict,
    enemy_database: dict,
    flag_skip0: bool,
) -> list[EnemyView]:
    def enemyDbRefs_sort(item):
        if item["id"] in enemy_table:
            return enemy_table[item["id"]]["sortId"]
        else:
            return 9999999

    normal_hidden_group = analyze_normal_hidden_group(level_table)
    enemy_count_dict = {}
    for wave in level_table["waves"]:
        for fragment in wave["fragments"]:
            action_list = [ActionInfo(action) for action in fragment["actions"]]
            pack_dict = {}
            actions_count_type = {}
            for action in action_list:
                if action.random_key is not None and action.random_pack is not None:
                    pack_dict[action.random_pack] = action.random_key
                if action.key is not None and action.key not in enemy_count_dict:
                    enemy_count_dict[action.key] = {"min": 0, "max": 0}
                if action.key is not None and action.key not in actions_count_type:
                    actions_count_type[action.key] = {"min": 0, "max": 0}
            for action in action_list:
                action.update_pack(pack_dict)
            actions_count = {"fixed": copy.deepcopy(actions_count_type), "random": {}}
            for action in action_list:
                if (action.key is not None or action.random_key is not None) and (
                    action.hidden_group is None
                    or action.hidden_group in normal_hidden_group
                ):
                    if action.random_key is not None:
                        if action.random_key not in actions_count["random"]:
                            actions_count["random"][action.random_key] = {
                                "single": [],
                                "pack": {},
                            }
                        if action.random_pack is not None:
                            if (
                                action.random_pack
                                not in actions_count["random"][action.random_key][
                                    "pack"
                                ]
                            ):
                                actions_count["random"][action.random_key]["pack"][
                                    action.random_pack
                                ] = copy.deepcopy(actions_count_type)
                            if action.key is not None:
                                actions_count["random"][action.random_key]["pack"][
                                    action.random_pack
                                ][action.key]["min"] += action.count
                                actions_count["random"][action.random_key]["pack"][
                                    action.random_pack
                                ][action.key]["max"] += action.count
                        else:
                            actions_count["random"][action.random_key]["single"].append(
                                copy.deepcopy(actions_count_type)
                            )
                            if action.key is not None:
                                actions_count["random"][action.random_key]["single"][
                                    -1
                                ][action.key]["min"] = action.count
                                actions_count["random"][action.random_key]["single"][
                                    -1
                                ][action.key]["max"] = action.count
                    else:
                        if action.key is not None:
                            actions_count["fixed"][action.key]["min"] += action.count
                            actions_count["fixed"][action.key]["max"] += action.count
            if actions_count["random"] != {}:
                for k_iter in actions_count["random"]:
                    if actions_count["random"][k_iter]["pack"] != {}:
                        for count_p in actions_count["random"][k_iter]["pack"].values():
                            actions_count["random"][k_iter]["single"].append(count_p)
                    if actions_count["random"][k_iter]["single"] != {}:
                        for enemy_k in actions_count_type:
                            actions_count["fixed"][enemy_k]["min"] += min(
                                x[enemy_k]["min"]
                                for x in actions_count["random"][k_iter]["single"]
                            )
                            actions_count["fixed"][enemy_k]["max"] += max(
                                x[enemy_k]["max"]
                                for x in actions_count["random"][k_iter]["single"]
                            )
            for k in enemy_count_dict:
                if k in actions_count["fixed"]:
                    enemy_count_dict[k]["min"] += actions_count["fixed"][k]["min"]
                    enemy_count_dict[k]["max"] += actions_count["fixed"][k]["max"]
    enemy_num_dict = {}
    for k in enemy_count_dict:
        if enemy_count_dict[k]["min"] == enemy_count_dict[k]["max"]:
            enemy_num_dict[k] = f"{enemy_count_dict[k]['min']}"
        else:
            enemy_num_dict[k] = (
                f"{enemy_count_dict[k]['min']},{enemy_count_dict[k]['max']}"
            )
    enemy_db_refs_sorted = sorted(level_table["enemyDbRefs"], key=enemyDbRefs_sort)
    enemies = []
    for enemy in enemy_db_refs_sorted:
        if enemy["id"] not in enemy_num_dict:
            enemy_num_dict[enemy["id"]] = "0"
        if flag_skip0 and enemy_num_dict[enemy["id"]] == "0":
            continue
        count_text = enemy_num_dict[enemy["id"]]
        if "," in count_text:
            count_lower, count_upper = count_text.split(",")
        else:
            count_lower, count_upper = None, count_text

        display_name = None
        note = None
        overrides = []
        # 只有明确的 False 才读 overwrittenData;useDb 缺失(None)时仍然查表,
        # 与 build_level_info 里对同一字段的判断保持一致
        if enemy["useDb"] is False:
            enemy_name = enemy["overwrittenData"]["name"]["m_value"]
            note = "需人工复查！"
        else:
            if enemy["id"] in enemy_table:
                enemy_name = enemy_table[enemy["id"]]["name"]
                if enemy_name in ["W", "泥岩", "多萝西", "弑君者"]:
                    display_name = enemy_name
                    enemy_name += "(敌方)"
            else:
                enemy_name = ""
                for enemy_content in enemy_database["enemies"]:
                    if enemy_content["Key"] == enemy["id"]:
                        enemy_name = enemy_content["Value"][0]["enemyData"]["name"][
                            "m_value"
                        ]
            if enemy["overwrittenData"] is not None:
                overrides = build_enemy_overrides(enemy["overwrittenData"])

        enemies.append(
            EnemyView(
                index=len(enemies) + 1,
                name=enemy_name,
                display_name=display_name,
                count=count_upper,
                count_lower=count_lower,
                level=enemy["level"],
                note=note,
                overrides=overrides,
            )
        )
    return enemies


def format_zone(zone_table: dict, zone_id: str) -> str:
    """拼接所属区域名。

    zone_table 里有 62 个区域(guide_1、camp_zone_* 等)两个名字字段都是 null,
    此处刻意保留旧行为输出字面量 None,而不是让参数从 wikitext 里消失 ——
    MediaWiki 模板对「参数缺失」和「参数为 None」的处理并不相同。
    """
    zone_data = zone_table["zones"][zone_id]
    if zone_data["zoneNameFirst"]:
        return f"{zone_data['zoneNameFirst']} {zone_data['zoneNameSecond']}"
    return f"{zone_data['zoneNameSecond']}"


def build_normal_stage(
    stage: StageData,
    table: StageTable,
    zone_table: dict,
    character_table: dict,
    building_data: dict,
    item_table: dict,
    level_table: dict,
    not_count_list: dict,
    compile_rich_text: Callable[[str], str],
    map_override: str = "",
) -> BasicStageView:
    subtype = None
    if stage.hilight_mark:
        subtype = "难关"
    elif stage.appearance_style == "HIGH_DIFFICULTY":
        subtype = "绝境"
    elif stage.appearance_style == "MIST_OPS":
        subtype = "迷雾"

    unlock_conditions = []
    for unlock in stage.unlock_condition:
        previous_stage = table.stages[unlock.stage_id]
        if_tough = ""
        if previous_stage.difficulty == "SIX_STAR":
            if_tough = "险地"
        elif (
            previous_stage.diff_group == "TOUGH"
            and previous_stage.appearance_style != "HIGH_DIFFICULTY"
        ):
            if_tough = "磨难"
        rank = {"PASS": 2, "COMPLETE": 3}.get(
            unlock.complete_state, unlock.complete_state
        )
        unlock_conditions.append(
            f"{rank}星通关[[{if_tough}{previous_stage.code} {previous_stage.name}]]"
        )

    zone = format_zone(zone_table, stage.zone_id)

    description = ""
    if stage.description:
        description = compile_rich_text(stage.description.replace("\\n", "<br/>"))

    rewards = []
    if stage.stage_drop_info.display_detail_rewards:
        rewards = build_reward_groups(
            stage.stage_drop_info.display_detail_rewards,
            character_table,
            building_data,
            item_table,
        )

    tile_effects = []
    terrain_tags = None
    if stage.level_id:
        tile_effects = build_tile_effects(level_table, table.tile_info)
        if "tags" in level_table["mapData"]:
            terrain_tags = level_table["mapData"]["tags"]

    view = BasicStageView(
        heading="普通",
        code=(stage.code or "").strip(),
        name=(stage.name or "").strip(),
        stage_id=stage.stage_id,
        map_override=map_override,
        stage_type=parse_stage_type(stage.stage_type),
        subtype=subtype,
        boss=stage.boss_mark,
        difficulty=stage.difficulty,
        # levelId 缺失(None)才算非战斗关卡;空字符串不是,与地图信息的截断判断不同
        battle_stage=stage.level_id is not None,
        unlock_condition=", ".join(unlock_conditions),
        recommended_level=stage.danger_level or "-",
        zone=zone,
        level=(
            build_level_info(level_table, not_count_list) if stage.level_id else None
        ),
        description=description,
        ap_cost=stage.ap_cost,
        practice_cost=stage.practice_ticket_cost if stage.can_practice else -1,
        rewards=rewards,
        tile_effects=tile_effects,
        terrain_tags=terrain_tags,
    )
    return view


def build_4star_stage(
    stage: StageData,
    table: StageTable,
    zone_table: dict,
    character_table: dict,
    building_data: dict,
    item_table: dict,
    level_table: dict,
    compile_rich_text: Callable[[str], str],
) -> AssaultStageView:
    unlock_conditions = []
    for unlock in stage.unlock_condition:
        previous_stage = table.stages[unlock.stage_id]
        rank = {"PASS": 2, "COMPLETE": 3}.get(
            unlock.complete_state, unlock.complete_state
        )
        if previous_stage.code != stage.code:
            unlock_condition = (
                f"{rank}星通关[[{previous_stage.code} {previous_stage.name}]]"
            )
        else:
            unlock_condition = (
                f"{rank}星通关[[#普通|{previous_stage.code} "
                f"{previous_stage.name}]]普通难度"
            )
        unlock_conditions.append(unlock_condition)

    zone = format_zone(zone_table, stage.zone_id)

    climit, intelligence = build_rune_buffs(level_table["runes"])

    rewards = []
    if stage.stage_drop_info.display_detail_rewards:
        rewards = build_reward_groups(
            stage.stage_drop_info.display_detail_rewards,
            character_table,
            building_data,
            item_table,
        )

    intelligence.extend(build_rune_lines(level_table["runes"]))

    view = AssaultStageView(
        heading="突袭",
        code=(stage.code or "").strip(),
        name=(stage.name or "").strip(),
        stage_type=parse_stage_type(stage.stage_type),
        difficulty=stage.difficulty,
        unlock_condition=", ".join(unlock_conditions),
        recommended_level=str(stage.danger_level),
        zone=zone,
        character_limit=level_table["options"]["characterLimit"] + climit,
        initial_cost=level_table["options"]["initialCost"],
        max_cost=level_table["options"]["maxCost"],
        description=compile_rich_text(
            (stage.description or "").replace("\\n", "<br/>")
        ),
        ap_cost=stage.ap_cost,
        practice_cost=stage.practice_ticket_cost if stage.can_practice else -1,
        rewards=rewards,
        intelligence=intelligence,
    )
    return view


def build_campaign_stage(
    stage: StageData,
    table: StageTable,
    campaign_table: dict,
    character_table: dict,
    building_data: dict,
    item_table: dict,
    level_table: dict,
    not_count_list: dict,
    compile_rich_text: Callable[[str], str],
) -> CampaignStageView:
    unlock_conditions = []
    for unlock in stage.unlock_condition:
        previous_stage = table.stages[unlock.stage_id]
        rank = {"PASS": 2, "COMPLETE": 3}.get(
            unlock.complete_state, unlock.complete_state
        )
        unlock_conditions.append(
            f"{rank}星通关[[{previous_stage.code} {previous_stage.name}]]"
        )

    if stage.zone_id in campaign_table["campaignZones"]:
        zone = campaign_table["campaignZones"][stage.zone_id]["name"]
    else:
        zone = "NONE"

    description = ""
    if stage.description:
        description = compile_rich_text(stage.description.replace("\\n", "<br/>"))

    campaign_detail = campaign_table["campaigns"][stage.stage_id]
    if campaign_detail["dropGains"]["PERMANENT"]["gainLadders"] != []:
        gain_flag = "PERMANENT"
    else:
        gain_flag = "ROTATE"

    rewards = []
    if campaign_detail["dropGains"][gain_flag]["displayDetailRewards"]:
        rewards = build_reward_groups(
            campaign_detail["dropGains"][gain_flag]["displayDetailRewards"],
            character_table,
            building_data,
            item_table,
        )

    gain_ladders = campaign_detail["dropGains"][gain_flag]["gainLadders"]
    ap_returns = [f"+{ladder['apFailReturn']}" for ladder in gain_ladders]
    diamond_rewards = []
    for ladder in gain_ladders:
        if ladder["displayDiamondShdNum"] == 0:
            diamond_rewards.append(f"+{ladder['displayDiamondShdNum']}")
        else:
            diamond_rewards.append(f"+约{ladder['displayDiamondShdNum']}")

    terrain_tags = None
    if stage.level_id and "tags" in level_table["mapData"]:
        terrain_tags = level_table["mapData"]["tags"]

    view = CampaignStageView(
        code=(stage.code or "").strip(),
        name=(stage.name or "").strip(),
        stage_id=stage.stage_id,
        commission="_r_" in stage.stage_id,
        stage_type=parse_stage_type(stage.stage_type),
        difficulty=stage.difficulty,
        unlock_condition=", ".join(unlock_conditions),
        zone=zone,
        level=(
            build_level_info(level_table, not_count_list) if stage.level_id else None
        ),
        description=description,
        ap_cost=stage.ap_cost,
        rewards=rewards,
        ap_returns=ap_returns,
        diamond_rewards=diamond_rewards,
        terrain_tags=terrain_tags,
    )
    return view


def build_crisis_stage(
    stage_detail: dict,
    level_table: dict,
    not_count_list: dict,
    compile_rich_text: Callable[[str], str],
) -> BasicStageView:
    if "description" in stage_detail:
        stage_desc = compile_rich_text(
            stage_detail["description"].replace("\\n", "<br/>")
        )
    elif "desc" in stage_detail:
        stage_desc = compile_rich_text(stage_detail["desc"].replace("\\n", "<br/>"))
    else:
        stage_desc = ""

    view = BasicStageView(
        code=stage_detail["code"].strip(),
        name=stage_detail["name"].strip(),
        stage_id=stage_detail["stageId"],
        stage_type="活动",
        difficulty="NORMAL",
        unlock_condition="—",
        recommended_level="—",
        zone=stage_detail["code"].strip(),
        level=(
            build_level_info(level_table, not_count_list)
            if stage_detail["levelId"]
            else None
        ),
        description=stage_desc,
        ap_cost=0,
        practice_cost=-1,
    )
    return view


def build_roguelike_stage(
    stage_detail: dict,
    level_table: dict,
    not_count_list: dict,
    compile_rich_text: Callable[[str], str],
) -> BasicStageView:
    terrain_tags = None
    if stage_detail["levelId"] and "tags" in level_table["mapData"]:
        terrain_tags = level_table["mapData"]["tags"]
    view = BasicStageView(
        heading="普通",
        code=stage_detail["code"].strip(),
        name=stage_detail["name"].strip(),
        stage_id=stage_detail["id"],
        stage_type="活动",
        difficulty="NORMAL",
        unlock_condition="—",
        recommended_level="—",
        zone="—",
        level=(
            build_level_info(level_table, not_count_list)
            if stage_detail["levelId"]
            else None
        ),
        description=compile_rich_text(
            stage_detail["description"].replace("\\n", "<br/>")
        ),
        ap_cost=0,
        practice_cost=-1,
        terrain_tags=terrain_tags,
    )
    return view


def build_roguelike_4star_stage(
    stage_detail: dict,
    level_table: dict,
    compile_rich_text: Callable[[str], str],
) -> AssaultStageView:
    climit, intelligence = build_rune_buffs(level_table["runes"])

    view = AssaultStageView(
        heading="紧急作战",
        code=stage_detail["code"].strip(),
        name=stage_detail["name"].strip(),
        stage_type="活动",
        subtype="紧急作战",
        difficulty="FOUR_STAR",
        unlock_condition="-",
        zone="-",
        character_limit=level_table["options"]["characterLimit"] + climit,
        initial_cost=level_table["options"]["initialCost"],
        max_cost=level_table["options"]["maxCost"],
        description=compile_rich_text(
            stage_detail["eliteDesc"].replace("\\n", "<br/>")
        ),
        ap_cost=0,
        practice_cost=-1,
        intelligence=intelligence,
    )
    return view


def build_memory_stage(
    stage_detail,
    level_table,
    compile_rich_text,
    character_table,
    building_data,
    item_table,
    notCount_list,
) -> BasicStageView:
    unlock_cond = ""
    for p in stage_detail["unlockParam"]:
        if unlock_cond != "":
            unlock_cond += "，"
        if p["unlockType"] == 1 or p["unlockType"] == "AWAKE":
            unlock_cond += "提升至精英阶段{}等级{}".format(
                p["unlockParam1"], p["unlockParam2"]
            )
        elif p["unlockType"] == 2 or p["unlockType"] == "FAVOR":
            unlock_cond += "提升信赖至{}".format(p["unlockParam1"])
        else:
            logger.info("Unknown unlockType", p["unlockType"])
    unlock_cond = (
        "干员'''[[{}]]'''".format(character_table[stage_detail["charId"]]["name"])
        + unlock_cond
    )

    reward_items = [
        DropView(
            name=parse_drop_item(
                r["type"], r["id"], character_table, building_data, item_table
            ),
            occurrence="三星获得",
        )
        for r in stage_detail["rewardItem"]
    ]
    terrain_tags = None
    if stage_detail["levelId"] and "tags" in level_table["mapData"]:
        terrain_tags = level_table["mapData"]["tags"]
    view = BasicStageView(
        code="悖论模拟",
        name=stage_detail["name"].strip(),
        stage_id=stage_detail["stageId"],
        stage_type="悖论模拟",
        difficulty="NORMAL",
        unlock_condition=unlock_cond,
        recommended_level="—",
        zone=stage_detail["zoneId"],
        level=(
            build_level_info(level_table, notCount_list)
            if stage_detail["levelId"]
            else None
        ),
        description=compile_rich_text(
            stage_detail["description"].replace("\n", "<br/>")
        ),
        ap_cost=0,
        practice_cost=-1,
        rewards=[RewardGroupView(label="首次掉落", drops=reward_items)],
        terrain_tags=terrain_tags,
    )
    return view


def build_sandbox_v2_stage(
    stage_detail: dict,
    compile_rich_text: Callable[[str], str],
    level_table: dict,
    not_count_list: dict,
) -> BasicStageView:
    terrain_tags = None
    if stage_detail["levelId"] and "tags" in level_table["mapData"]:
        terrain_tags = level_table["mapData"]["tags"]
    view = BasicStageView(
        code=stage_detail["code"],
        name=stage_detail["name"],
        stage_id=stage_detail["stageId"],
        stage_type="生息演算",
        level=(
            build_level_info(level_table, not_count_list, use_countdown=True)
            if stage_detail["levelId"]
            else None
        ),
        description=compile_rich_text(
            stage_detail["description"].replace("\\n", "<br/>").replace("\n", "<br/>")
        ),
        action_cost=stage_detail["actionCost"],
        terrain_tags=terrain_tags,
        sandbox_map=SandboxMapView(
            code=stage_detail["code"],
            name=stage_detail["name"],
            stage_id=stage_detail["stageId"],
        ),
    )
    return view


def build_recal_rune_stage(
    stage_detail: dict,
    compile_rich_text: Callable[[str], str],
    level_table: dict,
    not_count_list: dict,
) -> BasicStageView:
    terrain_tags = None
    if stage_detail["levelId"] and "tags" in level_table["mapData"]:
        terrain_tags = level_table["mapData"]["tags"]
    view = BasicStageView(
        code=stage_detail["levelCode"],
        name=stage_detail["levelName"],
        stage_id=stage_detail["stageId"],
        stage_type="全息作战矩阵",
        level=(
            build_level_info(level_table, not_count_list)
            if stage_detail["levelId"]
            else None
        ),
        description=compile_rich_text(
            stage_detail["levelDesc"].replace("\\n", "<br/>").replace("\n", "<br/>")
        ),
        ap_cost=0,
        practice_cost=-1,
        terrain_tags=terrain_tags,
    )
    return view


# --- 渲染:把视图序列化成 wikitext。纯参数表的模板用 WikiTemplate,
#     带自由文本/wikitable 的部分(固定编队表格、剿灭进度表、特殊地形注释、
#     各页面骨架)直接拼字符串。 ---


def render_drop(drop: DropView) -> str:
    # 家具的参数位置与普通物品不同: :家具=yes:1=名称[:2=概率]
    if drop.furniture:
        text = f":家具=yes:1={drop.name}"
        if drop.occurrence:
            text += f":2={drop.occurrence}"
        return text
    text = drop.name
    if drop.occurrence:
        text += f":{drop.occurrence}"
    return text


def render_reward_group(group: RewardGroupView) -> str:
    return ",".join(render_drop(drop) for drop in group.drops)


def add_level_info(template: WikiTemplate, level: LevelInfoView) -> None:
    # 用量标签是动态键名(最短用时/倒计时),声明式方案表达不了,直接拼 dict
    template.add_all(
        {
            "部署上限": level.character_limit,
            "初始COST": level.initial_cost,
            "COST上限": level.max_cost,
            "目标点耐久": level.max_life_point,
            "敌人数量": level.enemy_count,
            "地图大小": level.map_size,
            level.time_label: level.time,
        }
    )


def render_blackboard(blackboard: list[BlackboardView]) -> str:
    # 一组黑板键值,以制表符起首、逗号空格结尾,占据独立的一行
    parts = []
    for item in blackboard:
        part = f"{item.key} {item.value}"
        if item.value_str is not None:
            part += f" {item.value_str}"
        parts.append(part)
    return "\t" + ", ".join(parts) + ", "


def render_tile(tile: TileEffectView) -> str:
    lines = [f"{tile.name}:"]
    lines.extend(render_blackboard(b) for b in tile.blackboards)
    return "\n".join(lines)


def render_tile_effects(tiles: list[TileEffectView]) -> str:
    # 特殊地形黑板数据包在 HTML 注释里,仅作为编辑者复查的参考
    body = "\n".join(render_tile(tile) for tile in tiles)
    return f"<!--\n{body}\n-->"


def render_basic_stage(stage: BasicStageView) -> str:
    blocks = []
    if stage.heading is not None:
        blocks.append(f"=={stage.heading}==")
    template = WikiTemplate("普通关卡信息")
    template.add("关卡代号", stage.code)
    template.add("关卡名", stage.name)
    template.add("关卡id", stage.stage_id)
    template.add_optional("地图预览override", stage.map_override)
    template.add("关卡类型", stage.stage_type)
    template.add_if_set("子类型", stage.subtype)
    if stage.boss:
        template.add("领袖标志", "Yes")
    template.add_if_set("关卡难度", stage.difficulty)
    # 仅 False 时输出;None / True 都不输出
    if stage.battle_stage is False:
        template.add("战斗关卡", "false")
    template.add_if_set("解锁条件", stage.unlock_condition)
    template.add_if_set("推荐等级", stage.recommended_level)
    template.add_if_set("所属区域", stage.zone)
    if stage.level is not None:
        add_level_info(template, stage.level)
    template.add_if_set("关卡描述", stage.description)
    template.add_if_set("作战消耗", stage.ap_cost)
    template.add_if_set("演习消耗", stage.practice_cost)
    if stage.resource_overview is not None:
        template.add(
            "资源概览",
            "".join(inline_template("资源概览", r) for r in stage.resource_overview),
        )
    template.add_if_set("action消耗", stage.action_cost)
    template.add_if_set("power消耗", stage.power_cost)
    for reward in stage.rewards:
        template.add(reward.label, render_reward_group(reward))
    if stage.tile_effects:
        template.add("特殊地形效果", render_tile_effects(stage.tile_effects))
    if stage.terrain_tags is not None:
        template.add("地形tag", ",".join(stage.terrain_tags))
    if stage.sandbox_map is not None:
        template.add(
            "特殊地图",
            "<tabber>\n"
            "实景地图=\n"
            f'<img alt="{stage.sandbox_map.code} {stage.sandbox_map.name} 地图" '
            'loading="lazy" '
            f'src="//torappu.prts.wiki/assets/map_preview/'
            f'{stage.sandbox_map.stage_id}.png" width="580"/>\n'
            "|-|\n"
            "全地图={{#Widget:XbMapViewer|data={{:{{FULLPAGENAME}}/data}}}}\n"
            "</tabber>",
        )
    blocks.append(str(template))
    return "\n".join(blocks)


def render_assault_stage(stage: AssaultStageView) -> str:
    template = WikiTemplate("突袭关卡信息")
    template.add("关卡代号", stage.code)
    template.add("关卡名", stage.name)
    template.add("关卡类型", stage.stage_type)
    template.add_if_set("子类型", stage.subtype)
    template.add("关卡难度", stage.difficulty)
    template.add("解锁条件", stage.unlock_condition)
    template.add_if_set("推荐等级", stage.recommended_level)
    template.add("所属区域", stage.zone)
    template.add_all(
        {
            "部署上限": stage.character_limit,
            "初始COST": stage.initial_cost,
            "COST上限": stage.max_cost,
        }
    )
    template.add("关卡描述", stage.description)
    template.add_all({"作战消耗": stage.ap_cost, "演习消耗": stage.practice_cost})
    for reward in stage.rewards:
        template.add(reward.label, render_reward_group(reward))
    # 情报保留在注释中,供编辑者复查;没有情报时注释里也不留空行
    template.add_raw("\n".join(["<!--|情报=", *stage.intelligence, "-->"]))
    return f"=={stage.heading}==\n{template}"


def render_campaign_stage(stage: CampaignStageView) -> str:
    template = WikiTemplate("剿灭关卡信息")
    template.add("关卡代号", stage.code)
    template.add("关卡名", stage.name)
    template.add("关卡id", stage.stage_id)
    if stage.commission:
        template.add("剿灭委托", "true")
    template.add("关卡类型", stage.stage_type)
    template.add("关卡难度", stage.difficulty)
    template.add("解锁条件", stage.unlock_condition)
    template.add("所属区域", stage.zone)
    if stage.level is not None:
        add_level_info(template, stage.level)
    template.add("关卡描述", stage.description)
    template.add("作战消耗", stage.ap_cost)
    for reward in stage.rewards:
        template.add(reward.label, render_reward_group(reward))
    for index, value in enumerate(stage.ap_returns, 1):
        template.add(f"理智返还{index}", value)
    for index, value in enumerate(stage.diamond_rewards, 1):
        template.add(f"合成玉获得{index}", value)
    if stage.terrain_tags is not None:
        template.add("地形tag", ",".join(stage.terrain_tags))
    return f"==关卡==\n{template}"


def add_enemy_params(template: WikiTemplate, enemy: EnemyView) -> None:
    # 敌人参数键名带序号,显式拼出比再加一层抽象更清楚
    index = enemy.index
    template.add(f"敌人{index}", enemy.name)
    if enemy.display_name is not None:
        template.add(f"敌人{index}显示名", enemy.display_name)
    template.add(f"敌人{index}数量", enemy.count)
    if enemy.count_lower is not None:
        template.add(f"敌人{index}数量下限", enemy.count_lower)
    template.add(f"敌人{index}级别", enemy.level)
    if enemy.note is not None:
        template.add(f"敌人{index}备注", enemy.note)
    for override in enemy.overrides:
        template.add(f"敌人{index}{override.label}", override.value)


def render_enemies(enemies: list[EnemyView]) -> str:
    template = WikiTemplate("敌方情报")
    for enemy in enemies:
        add_enemy_params(template, enemy)
    return f"==敌方情报==\n{template}"


def render_squad_unit(unit: SquadUnitView) -> str:
    if unit.simulation:
        return inline_template("悖论模拟对象", unit.name)
    args = [unit.name, unit.phase, unit.level, unit.skill_name, unit.main_skill_level]
    if unit.potential is not None:
        # 潜能是第 6 个位置参数,前面补一个空位(第 5 位留空)
        args += ["", unit.potential]
    return inline_template("编队单位", *args)


def render_squad(section: SquadSectionView) -> str:
    units = "".join(render_squad_unit(unit) for unit in section.units)
    return (
        f"=={section.title}==\n"
        '{| class="wikitable hlist logo mw-collapsed mw-collapsible" '
        'style="text-align:center; width:567px; white-space:normal;"\n'
        f'!style="background-color:#0098DC;color:#FFFFFF"|{section.title}\n'
        f"|-\n"
        f"|{units}\n"
        f"|-\n"
        f"!备注\n"
        f"|-\n"
        f"|{section.note}\n"
        f"|}}"
    )


def render_squads(squads: list[SquadSectionView]) -> str:
    return "\n".join(render_squad(section) for section in squads)


def render_progress_items(items: list[CampaignProgressItemView]) -> str:
    parts = [inline_template("材料消耗", item.name, item.count) for item in items]
    return " ".join(parts)


def render_progress_row(row: CampaignProgressRowView) -> str:
    text = f"|-\n|{row.kill_count}||{render_progress_items(row.items)}"
    if row.break_fee_add:
        text += f" {inline_template('材料消耗', '合成玉', 'i+')}(+{row.break_fee_add})"
    return text + "\n"


def render_campaign_progress(progress: CampaignProgressView) -> str:
    rows = "".join(render_progress_row(row) for row in progress.rows)
    return (
        "==作战进度奖励==\n"
        '{| class="wikitable mw-collapsible mw-collapsed" '
        'style="text-align:center;width:600px;"\n'
        '!style="width:200px;color:white;font-weight:bold;'
        'background-color:#575757;"|击溃人数\n'
        '!style="width:400px;color:white;font-weight:bold;'
        'background-color:#575757;"|奖励\n'
        f"{rows}"
        "|}"
    )


# --- 页面骨架:各 page 模板,把上面的片段按页面布局组合。 ---


def render_normal_page(page: NormalPageView) -> str:
    blocks = ["{{pathnav2|关卡一览}}", render_basic_stage(page.normal)]
    if page.assault is not None:
        blocks.append(render_assault_stage(page.assault))
    if page.enemies is not None:
        blocks.append(render_enemies(page.enemies))
    if page.squads:
        blocks.append(render_squads(page.squads))
    if page.material_drop:
        blocks.append("==材料掉落==\n{{关卡材料掉落}}")
    blocks.append("==注释与链接==\n<references/>\n{{关卡导航}}")
    return "\n".join(blocks)


def render_campaign_page(page: CampaignPageView) -> str:
    blocks = ["{{pathnav2|关卡一览}}", render_campaign_stage(page.stage)]
    if page.enemies is not None:
        blocks.append(render_enemies(page.enemies))
    if page.squads:
        blocks.append(render_squads(page.squads))
    blocks.append(render_campaign_progress(page.progress))
    blocks.append("==注释与链接==\n<references/>\n{{关卡导航}}")
    return "\n".join(blocks)


def render_basic_page(
    page: BasicPageView,
    *,
    notoc: bool = False,
    extra_sections: list[str] | None = None,
    categories: list[str] | None = None,
) -> str:
    """危机合约/悖论模拟/生息演算/训练场/全息作战矩阵/id 页面共用。

    带 __NOTOC__ 的页面(crisis/memory/mechanism/id)把 notoc 置 True;
    生息演算历来不带,不要顺手打开。
    extra_sections 插在敌方情报与固定编队之后、注释与链接之前(如危机合约的合约详情),
    categories 追加在 {{关卡导航}} 之后(如分类:危机合约关卡)。
    """
    blocks = ["{{pathnav2|关卡一览}}"]
    if notoc:
        blocks.append("__NOTOC__")
    blocks.append(render_basic_stage(page.stage))
    if page.enemies is not None:
        blocks.append(render_enemies(page.enemies))
    if page.squads:
        blocks.append(render_squads(page.squads))
    if extra_sections:
        blocks.extend(extra_sections)
    blocks.append("==注释与链接==\n<references/>\n{{关卡导航}}")
    if categories:
        blocks.extend(categories)
    return "\n".join(blocks)


def render_roguelike_page(page: RoguelikePageView) -> str:
    blocks = ["{{pathnav2|关卡一览}}", render_basic_stage(page.normal)]
    if page.assault is not None:
        blocks.append(render_assault_stage(page.assault))
    if page.enemies is not None:
        blocks.append(render_enemies(page.enemies))
    blocks.append("==注释与链接==\n<references/>\n{{关卡导航}}")
    blocks.append("[[分类:集成战略关卡]]")
    return "\n".join(blocks)


def render_recal_rune_page(page: RecalRunePageView) -> str:
    blocks = [
        "{{pathnav2|关卡一览}}",
        f"<noinclude>{{{{DISPLAYTITLE:{page.display_title}}}}}</noinclude>",
    ]
    blocks.append(render_basic_stage(page.stage))
    if page.enemies is not None:
        blocks.append(render_enemies(page.enemies))
    if page.squads:
        blocks.append(render_squads(page.squads))
    blocks.append("==注释与链接==\n<references/>\n{{关卡导航}}")
    return "\n".join(blocks)


def render_disambiguation(links: list[DisambiguationLinkView]) -> str:
    lines = ["{{消歧义页}}", "<big><big>你要找的结果可能如下：</big></big>"]
    for link in links:
        line = f"*<big>'''[[{link.page_name}]]'''"
        if link.activity_name is not None:
            line += f"（[[{link.activity_name}]]关卡）"
        line += "</big>"
        lines.append(line)
    return "\n".join(lines)


class ActionInfo:
    def __init__(self, action):
        if (action["actionType"] == 0 or action["actionType"] == "SPAWN") and action[
            "key"
        ] != "":
            self.key = action["key"]
        else:
            self.key = None
        if self.key is not None:
            self.time = action["preDelay"] + (action["count"] - 1) * action["interval"]
            self.count = action["count"]
        else:
            self.time = 0.0
            self.count = 0
        if "hiddenGroup" in action and action["hiddenGroup"] is not None:
            self.hidden_group = action["hiddenGroup"]
        else:
            self.hidden_group = None
        self.random_type = 0
        if (
            "randomSpawnGroupKey" in action
            and action["randomSpawnGroupKey"] is not None
        ):
            self.random_key = action["randomSpawnGroupKey"]
            self.random_type += 1
        else:
            self.random_key = None
        if (
            "randomSpawnGroupPackKey" in action
            and action["randomSpawnGroupPackKey"] is not None
        ):
            self.random_pack = action["randomSpawnGroupPackKey"]
            self.random_type += 2
        else:
            self.random_pack = None

    def update_pack(self, pack_dict):
        if self.random_key is None and self.random_pack is not None:
            if self.random_pack in pack_dict:
                self.random_key = pack_dict[self.random_pack]
            else:
                logger.info(
                    f"Error: cannot find random_key for pack {self.random_pack}"
                )


def check_duplicate(ctx: JobContext) -> dict[str, str]:
    """同名关卡代号 -> 消歧义页 wikitext。"""
    stage_table = ctx.getgd("excel/stage_table.json")
    activity_table = ctx.getgd("excel/activity_table.json")

    stage_code_dict, duplicate_dict = {}, {}
    for s in stage_table["stages"].values():
        if s["name"] is None or s["code"] is None:
            continue
        if (
            s["difficulty"] in ["FOUR_STAR", "SIX_STAR"]
            or s["stageType"] == "GUIDE"
            or s["diffGroup"] in ["EASY", "TOUGH"]
        ):
            continue
        if s["code"] not in stage_code_dict:
            stage_code_dict[s["code"].strip()] = []
        stage_code_dict[s["code"].strip()].append(s["stageId"])
    for code, s_list in stage_code_dict.items():
        if len(s_list) > 1:
            links = []
            seen_links = set()
            for sid in s_list:
                activity_name = None
                if stage_table["stages"][sid]["stageType"] == "ACTIVITY":
                    result = re.search("^([^_]+)[_-]", sid)
                    act_id = result.group(1)
                    if act_id in activity_table["basicInfo"]:
                        activity_name = activity_table["basicInfo"][act_id][
                            "name"
                        ].replace("#", "/0")
                page_name = "{} {}".format(
                    stage_table["stages"][sid]["code"].strip(),
                    stage_table["stages"][sid]["name"].strip(),
                )
                link_key = (page_name, activity_name)
                if link_key not in seen_links:
                    links.append(
                        DisambiguationLinkView(
                            page_name=page_name,
                            activity_name=activity_name,
                        )
                    )
                    seen_links.add(link_key)
            duplicate_dict[code] = render_disambiguation(links)
    # logger.info(json.dumps(duplicate_dict, indent=4, ensure_ascii=False))
    return duplicate_dict


def _get_list_notCountInTotal(ctx: JobContext):
    enemy_database = ctx.getgd("levels/enemydata/enemy_database.json")
    notCount_list = {}
    try:
        for enemy in enemy_database["enemies"]:
            for enemy_level in enemy["Value"]:
                if "notCountInTotal" in enemy_level["enemyData"]:
                    if enemy_level["enemyData"]["notCountInTotal"]["m_defined"] is True:
                        if (
                            enemy_level["enemyData"]["notCountInTotal"]["m_value"]
                            is True
                        ):
                            if enemy["Key"] not in notCount_list:
                                notCount_list[enemy["Key"]] = []
                            notCount_list[enemy["Key"]].append(enemy_level["level"])
                    elif (
                        enemy["Key"] in notCount_list
                        and enemy_level["level"] - 1 in notCount_list[enemy["Key"]]
                    ):
                        notCount_list[enemy["Key"]].append(enemy_level["level"])
        return notCount_list
    except Exception:
        return {}


@job
def run(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    item_table = ctx.getgd("excel/item_table.json")
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    stage_table = ctx.getgd("excel/stage_table.json")
    typed_stage_table = StageTable.model_validate(stage_table)
    zone_table = ctx.getgd("excel/zone_table.json")
    redirect_table = ctx.getgd("battle/battle_misc_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    stage_list = ctx.wiki.category("分类:普通难度关卡")
    new_stage_list = []
    duplicate_dict = check_duplicate(ctx)
    notCount_list = _get_list_notCountInTotal(ctx)

    for stage_id in stage_table["stages"]:
        stage_detail = stage_table["stages"][stage_id]
        if stage_detail["name"] is None or stage_detail["code"] is None:
            continue
        if (
            stage_detail["stageType"]
            not in [
                "MAIN",
                "SUB",
                "DAILY",
                "ACTIVITY",
                "SPECIAL_STORY",
                "CLIMB_TOWER",
            ]
            or stage_detail["difficulty"] in ["FOUR_STAR"]
            or stage_detail["diffGroup"] in ["EASY"]
        ):
            continue
        stage_detail["name"] = {
            "act21side_01_t": "新城区大街(德克萨斯)",
            "act21side_02_t": "萨卢佐家(拉普兰德2)",
            "act21side_03_m2": "后巷(拉普兰德1)",
            "act21side_04_m1": "萨卢佐家(拉普兰德1)",
            "act21side_05_m1": "后巷(乔万娜)",
            "act21side_05_t": "后巷(拉普兰德2)",
            "act21side_06_t": "新城区大街(丹布朗)",
        }.get(stage_id, stage_detail["name"].strip())
        # 表里的副本就是下面要渲染的那一关,改名后直接用它,不再单独校验一份
        typed_stage_table.stages[stage_id].name = stage_detail["name"]
        typed_stage = typed_stage_table.stages[stage_id]
        stage_page_name = stage_detail["code"].strip() + " " + stage_detail["name"]
        if stage_detail["difficulty"] == "SIX_STAR":
            stage_page_name = "险地" + stage_page_name
        elif (
            stage_detail["diffGroup"] == "TOUGH"
            and stage_detail["appearanceStyle"] != "HIGH_DIFFICULTY"
        ):
            stage_page_name = "磨难" + stage_page_name
        if stage_page_name in stage_list:
            continue
        # if stage_detail['code'] not in ['IG-DF-6']:
        #     continue

        map_override = ""
        if stage_detail["levelId"]:
            try:
                if stage_detail["levelId"] in redirect_table["levelScenePairs"]:
                    level_table = ctx.getgd(
                        "levels/"
                        + redirect_table["levelScenePairs"][stage_detail["levelId"]][
                            "levelId"
                        ].lower()
                        + ".json"
                    )
                    if (
                        redirect_table["levelScenePairs"][stage_detail["levelId"]][
                            "hookedMapPreviewId"
                        ]
                        is not None
                    ):
                        map_override = redirect_table["levelScenePairs"][
                            stage_detail["levelId"]
                        ]["hookedMapPreviewId"]
                else:
                    level_table = ctx.getgd(
                        "levels/" + stage_detail["levelId"].lower() + ".json"
                    )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        normal_stage = build_normal_stage(
            typed_stage,
            typed_stage_table,
            zone_table,
            character_table,
            building_data,
            item_table,
            level_table,
            notCount_list,
            rts.compile,
            map_override=map_override,
        )
        enemies = (
            _build_enemy_views(ctx, level_table) if stage_detail["levelId"] else None
        )
        assault_stage = (
            build_4star_stage(
                typed_stage_table.stages[typed_stage.hard_staged_id],
                typed_stage_table,
                zone_table,
                character_table,
                building_data,
                item_table,
                level_table,
                rts.compile,
            )
            if stage_detail["hardStagedId"]
            else None
        )
        has_material_drop = any(
            reward["dropType"] in [2, 3, 4]
            for reward in stage_detail["stageDropInfo"]["displayDetailRewards"]
        )
        if stage_detail["levelId"]:
            squads = build_squad_sections(
                level_table, stage_page_name, character_table, skill_table
            )
        else:
            squads = []

        stage_content = render_normal_page(
            NormalPageView(
                normal=normal_stage,
                assault=assault_stage,
                enemies=enemies,
                squads=squads,
                material_drop=has_material_drop,
            )
        )
        stage_redirect = f"#redirect [[{stage_page_name}]]"

        # old = ctx.wiki.read(stage_page_name)
        # result = re.search('(\n==敌方情报==\n[\s\S]*?)\n==', old)
        # if result:
        #     stage_content = old.replace(result.group(1), stage_enemy_data)
        # else:
        #     continue

        # result2 = re.search(r"\|额外物资=(.*?)\n", stage_normal_data)
        # if not result2:
        #     continue
        # old = ctx.wiki.read(stage_page_name)
        # result1 = re.search(r"\|额外物资=(.*?)\n", old)
        # if result1 and result2:
        #     stage_content = old.replace(result1.group(1), result2.group(1))
        #     if stage_content != old:
        #         logger.info(f'{stage_page_name} differenet. update.')
        #         ctx.wiki.edit(
        #             title=stage_page_name,
        #             text=stage_content,
        #             summary='update'
        #         )
        #     else:
        #         logger.info(f'{stage_page_name} same.')
        # else:
        #     continue

        if stage_detail["code"].strip() in duplicate_dict:
            ctx.wiki.edit(
                title=stage_detail["code"].strip(),
                text=duplicate_dict[stage_detail["code"].strip()],
                summary="消歧义",
            )
        else:
            if stage_detail["difficulty"] == "SIX_STAR":
                redirect_title = "险地" + stage_detail["code"].strip()
            elif (
                stage_detail["diffGroup"] == "TOUGH"
                and stage_detail["appearanceStyle"] != "HIGH_DIFFICULTY"
            ):
                redirect_title = "磨难" + stage_detail["code"].strip()
            else:
                redirect_title = stage_detail["code"].strip()
            ctx.wiki.edit(
                title=redirect_title,
                text=stage_redirect,
                summary="init",
                createonly="1",
            )
        ctx.wiki.edit(
            title=stage_detail["stageId"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            createonly="1",
            bot=None,
            minor=True,
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")

        new_stage_list.append(f"* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            text="\n".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_campaign(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    item_table = ctx.getgd("excel/item_table.json")
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    stage_table = ctx.getgd("excel/stage_table.json")
    typed_stage_table = StageTable.model_validate(stage_table)
    campaign_table = ctx.getgd("excel/campaign_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    stage_list = ctx.wiki.category("分类:剿灭关卡")
    new_stage_list = []
    notCount_list = _get_list_notCountInTotal(ctx)

    for stage_id in stage_table["stages"]:
        stage_detail = stage_table["stages"][stage_id]
        if stage_detail["stageType"] != "CAMPAIGN":
            continue
        stage_page_name = (
            stage_detail["code"].strip() + " " + stage_detail["name"].strip()
        )
        if stage_page_name in stage_list:
            continue

        if stage_detail["levelId"]:
            try:
                level_table = ctx.getgd(
                    "levels/" + stage_detail["levelId"].lower() + ".json"
                )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        campaign_stage = build_campaign_stage(
            typed_stage_table.stages[stage_id],
            typed_stage_table,
            campaign_table,
            character_table,
            building_data,
            item_table,
            level_table,
            notCount_list,
            rts.compile,
        )
        enemies = (
            _build_enemy_views(ctx, level_table) if stage_detail["levelId"] else None
        )
        squads = build_squad_sections(
            level_table,
            stage_page_name,
            character_table,
            skill_table,
            include_inserted=False,
        )
        progress_rows = []
        for r in campaign_table["campaigns"][stage_detail["stageId"]]["breakLadders"]:
            progress_rows.append(
                CampaignProgressRowView(
                    kill_count=r["killCnt"],
                    items=[
                        CampaignProgressItemView(
                            name=parse_drop_item(
                                reward["type"],
                                reward["id"],
                                character_table,
                                building_data,
                                item_table,
                            ),
                            count=reward["count"],
                        )
                        for reward in r["rewards"]
                    ],
                    break_fee_add=r["breakFeeAdd"],
                )
            )

        stage_content = render_campaign_page(
            CampaignPageView(
                stage=campaign_stage,
                enemies=enemies,
                squads=squads,
                progress=CampaignProgressView(rows=progress_rows),
            )
        )
        stage_redirect = f"#redirect [[{stage_page_name}]]"

        ctx.wiki.edit(
            title=stage_detail["name"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_detail["stageId"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            bot=None,
            minor=True,
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")

        new_stage_list.append(f"* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            text="\n".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_crisis(ctx: JobContext) -> None:
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))
    notCount_list = _get_list_notCountInTotal(ctx)

    # 从 crisis_info 读
    # https://weedy.prts.wiki/crisis_info.json
    # with open('crisis_info.json', 'r', encoding='utf-8') as file:
    #     stage_table = json.loads(file.read())['info']['mapStageDataMap']
    # # for stage_key in stage_table['data']['seasonInfo'][0]['stages']:
    # #     stage_detail = stage_table['data']['seasonInfo'][0]['stages'][stage_key]
    # #     stage_detail['stageId'] = stage_key
    # #     stage_detail['levelId'] = 'Obt/rune/' + stage_key
    # for stage_x in stage_table.values():
    #     stage_detail = stage_x

    # 从 weedy 读
    session = requests.Session()
    stage_list = session.get("https://weedy.prts.wiki/crisis_info.json").json()["info"][
        "mapStageDataMap"
    ]
    for stage_detail in stage_list.values():
        stage_page_name = (
            stage_detail["code"].strip() + " " + stage_detail["name"].strip()
        )

        if stage_detail["levelId"]:
            try:
                level_table = ctx.getgd(
                    "levels/" + stage_detail["levelId"].lower() + ".json"
                )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        crisis_stage = build_crisis_stage(
            stage_detail, level_table, notCount_list, rts.compile
        )
        enemies = (
            _build_enemy_views(ctx, level_table) if stage_detail["levelId"] else None
        )

        stage_content = render_basic_page(
            BasicPageView(stage=crisis_stage, enemies=enemies),
            notoc=True,
            extra_sections=["==合约详情==\n{{合约详情}}"],
            categories=["[[分类:危机合约关卡]]"],
        )
        stage_redirect = f"#redirect [[{stage_page_name}]]"

        ctx.wiki.edit(
            title=stage_detail["name"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            bot=None,
            minor=True,
            createonly="1",
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")


@job
def run_rogue_like(ctx: JobContext) -> None:
    # roguelike_table = ctx.getgd('excel/roguelike_table.json')
    roguelike_table = ctx.getgd("excel/roguelike_topic_table.json")
    roguelike_table = roguelike_table["details"]["rogue_6"]
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    notCount_list = _get_list_notCountInTotal(ctx)

    for stage_key in roguelike_table["stages"]:
        stage_detail = roguelike_table["stages"][stage_key]
        if stage_detail["difficulty"] == "FOUR_STAR":
            continue
        if stage_key == "ro4_b_9":
            continue

        stage_page_name = (
            stage_detail["code"].strip() + " " + stage_detail["name"].strip()
        )

        if stage_detail["levelId"]:
            try:
                if (
                    stage_detail["levelReplaceIds"]
                    and len(stage_detail["levelReplaceIds"]) >= 1
                ):
                    level_table = ctx.getgd(
                        "levels/" + stage_detail["levelReplaceIds"][0].lower() + ".json"
                    )
                else:
                    level_table = ctx.getgd(
                        "levels/" + stage_detail["levelId"].lower() + ".json"
                    )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        normal_stage = build_roguelike_stage(
            stage_detail, level_table, notCount_list, rts.compile
        )
        linkedStage = [
            k
            for k in roguelike_table["stages"]
            if roguelike_table["stages"][k]["linkedStageId"] == stage_key
        ]
        if len(linkedStage) >= 1:
            assault_stage = build_roguelike_4star_stage(
                roguelike_table["stages"][linkedStage[0]],
                level_table,
                rts.compile,
            )
        else:
            assault_stage = None
        enemies = (
            _build_enemy_views(ctx, level_table) if stage_detail["levelId"] else None
        )

        stage_content = render_roguelike_page(
            RoguelikePageView(
                normal=normal_stage,
                assault=assault_stage,
                enemies=enemies,
            )
        )
        stage_redirect = f"#redirect [[{stage_page_name}]]"

        ctx.wiki.edit(
            title=stage_detail["name"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            bot=None,
            minor=True,
            createonly="1",
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")


@job
def run_memory(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    item_table = ctx.getgd("excel/item_table.json")
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    handbook_info_table = ctx.getgd("excel/handbook_info_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    stage_list = ctx.wiki.category("分类:悖论模拟关卡")
    new_stage_list = []
    notCount_list = _get_list_notCountInTotal(ctx)

    for stage_detail in handbook_info_table["handbookStageData"].values():
        stage_page_name = "悖论模拟 {}".format(stage_detail["name"].strip())
        if stage_page_name in stage_list:
            continue
        if stage_detail["levelId"]:
            try:
                level_table = ctx.getgd(
                    "levels/" + stage_detail["levelId"].lower() + ".json"
                )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        memory_stage = build_memory_stage(
            stage_detail,
            level_table,
            rts.compile,
            character_table,
            building_data,
            item_table,
            notCount_list,
        )
        enemies = (
            _build_enemy_views(ctx, level_table) if stage_detail["levelId"] else None
        )
        squads = build_squad_sections(
            level_table,
            stage_page_name,
            character_table,
            skill_table,
            stage_char_id=stage_detail["charId"],
        )

        stage_content = render_basic_page(
            BasicPageView(
                stage=memory_stage,
                enemies=enemies,
                squads=squads,
            ),
            notoc=True,
        )
        stage_redirect = f"#redirect [[{stage_page_name}]]"

        ctx.wiki.edit(
            title=stage_detail["name"].strip(),
            text=stage_redirect,
            summary="init",
            createonly="1",
        )
        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            createonly="1",
            bot=None,
            minor=True,
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")

        new_stage_list.append(f"\n* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            appendtext="".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_sandbox(ctx: JobContext) -> None:
    # sandbox_table = ctx.getgd('excel/sandbox_table.json')
    sandbox_table = ctx.getgd("excel/sandbox_perm_table.json")
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    stage_list = ctx.wiki.category("分类:生息演算关卡")
    new_stage_list = []
    notCount_list = _get_list_notCountInTotal(ctx)

    # sandbox_stage_list = sandbox_table['sandboxActTables']
    sandbox_stage_list = sandbox_table["detail"]["SANDBOX_V2"]

    for act_key in sandbox_stage_list:
        for stage_id, stage_data in sandbox_stage_list[act_key]["stageData"].items():
            stage_data["name"] = stage_data["name"].strip()
            stage_page_name = f"{stage_data['code']} {stage_data['name']}(沙洲遗闻)"
            if stage_page_name in stage_list:
                continue
            # if stage_data['name'] not in ['炎岩关']:
            #     continue

            if stage_data["levelId"]:
                try:
                    level_table = ctx.getgd(
                        "levels/" + stage_data["levelId"].lower() + ".json"
                    )
                except Exception:
                    logger.info(f"Cannot find level data of {stage_page_name}.")
                    continue
            else:
                level_table = {}

            sandbox_stage = build_sandbox_v2_stage(
                stage_data, rts.compile, level_table, notCount_list
            )
            enemies = (
                _build_enemy_views(ctx, level_table) if stage_data["levelId"] else None
            )
            if stage_data["levelId"]:
                squads = build_squad_sections(
                    level_table, stage_page_name, character_table, skill_table
                )
            else:
                squads = []
            # 生息演算页面不加 __NOTOC__,与 crisis/memory/mechanism/id 不同
            stage_content = render_basic_page(
                BasicPageView(
                    stage=sandbox_stage,
                    enemies=enemies,
                    squads=squads,
                ),
            )

            # old = ctx.wiki.read(stage_page_name)
            # result = re.search('(\n==敌方情报==\n[\s\S]*?)\n==', old)
            # if result:
            #     stage_content = old.replace(result.group(1), stage_enemy_data)
            # else:
            #     continue

            ctx.wiki.edit(
                title=stage_page_name + "/data",
                text=json.dumps(level_table, ensure_ascii=False),
                summary="init",
                createonly=True,
                contentmodel="json",
            )
            ctx.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary="init",
                createonly=True,
                bot=None,
                minor=True,
            )
            # logger.info(stage_content)
            logger.info(f"Created: {stage_page_name}.")

            new_stage_list.append(f"\n* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            appendtext="".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_mechanism(ctx: JobContext) -> None:
    story_review_meta_table = ctx.getgd("excel/story_review_meta_table.json")
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")

    new_stage_list = []
    notCount_list = _get_list_notCountInTotal(ctx)

    for stage_data in story_review_meta_table["trainingCampData"]["stageData"].values():
        stage_page_name = f"{stage_data['code']} {stage_data['name'].strip()}"
        # if stage_page_name in stage_list:
        #     continue

        if stage_data["levelId"]:
            try:
                level_table = ctx.getgd(
                    "levels/" + stage_data["levelId"].lower() + ".json"
                )
            except Exception:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            level_table = {}

        mechanism_stage = BasicStageView(
            code=stage_data["code"],
            name=stage_data["name"].strip(),
            stage_id=stage_data["stageId"],
            stage_type="训练场",
            difficulty="NORMAL",
            unlock_condition="—",
            recommended_level="—",
            zone="-",
            level=build_level_info(level_table, notCount_list),
            description=stage_data["description"],
            ap_cost=0,
            practice_cost=-1,
        )

        enemies = _build_enemy_views(ctx, level_table)
        squads = build_squad_sections(
            level_table, stage_page_name, character_table, skill_table
        )
        stage_content = render_basic_page(
            BasicPageView(
                stage=mechanism_stage,
                enemies=enemies,
                squads=squads,
            ),
            notoc=True,
        )

        ctx.wiki.edit(
            title=stage_page_name,
            text=stage_content,
            summary="init",
            bot=None,
            minor=True,
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_page_name}.")
        new_stage_list.append(f"\n* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            appendtext="".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(''.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_recalrune(ctx: JobContext) -> None:
    crisis_v2_table = ctx.getgd("excel/crisis_v2_table.json")
    recalrune_table = crisis_v2_table["recalRuneData"]
    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    stage_list = ctx.wiki.category("分类:全息作战矩阵关卡")
    new_stage_list = []
    notCount_list = _get_list_notCountInTotal(ctx)

    for season_info in recalrune_table["seasons"].values():
        for stage_id, stage_data in season_info["stages"].items():
            stage_data["levelName"] = stage_data["levelName"].strip()
            stage_page_name = (
                f"全息{stage_data['levelCode']} "
                f"{stage_data['levelName'].replace('#', '＃')}"
            )
            if stage_page_name in stage_list:
                continue
            # if stage_data['levelName'] not in ['#爱国者之死']:
            #     continue

            if stage_data["levelId"]:
                try:
                    level_table = ctx.getgd(
                        "levels/" + stage_data["levelId"].lower() + ".json"
                    )
                except Exception:
                    logger.info(f"Cannot find level data of {stage_page_name}.")
                    continue
            else:
                level_table = {}

            recal_rune_stage = build_recal_rune_stage(
                stage_data, rts.compile, level_table, notCount_list
            )
            enemies = (
                _build_enemy_views(ctx, level_table) if stage_data["levelId"] else None
            )
            if stage_data["levelId"]:
                squads = build_squad_sections(
                    level_table, stage_page_name, character_table, skill_table
                )
            else:
                squads = []
            stage_content = render_recal_rune_page(
                RecalRunePageView(
                    stage=recal_rune_stage,
                    enemies=enemies,
                    squads=squads,
                    display_title=(
                        f"全息{stage_data['levelCode']} {stage_data['levelName']}"
                    ),
                )
            )
            stage_redirect = f"#redirect [[{stage_page_name}]]"

            ctx.wiki.edit(
                title=f"全息{stage_data['levelCode']}",
                text=stage_redirect,
                summary="init",
                createonly="1",
            )
            ctx.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary="init",
                createonly=True,
                bot=None,
                minor=True,
            )
            # logger.info(stage_content)
            logger.info(f"Created: {stage_page_name}.")

            new_stage_list.append(f"\n* [[{stage_page_name}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            appendtext="".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


@job
def run_id(ctx: JobContext, path) -> None:
    # if ctx.gamedata._source() != 'Unpacker':
    #     return

    character_table = ctx.getgd("excel/character_table.json")
    skill_table = ctx.getgd("excel/skill_table.json")
    stage_table = ctx.getgd("excel/stage_table.json")
    stage_id_list = []
    for s in stage_table["stages"].values():
        if s["levelId"] is not None:
            stage_id_list.append("levels/" + s["levelId"].lower() + ".json")
    notCount_list = _get_list_notCountInTotal(ctx)

    filelist = []
    base_dir = "./thirdparty/ArknightsGameData/zh_CN/gameData/"

    def get_files(curr_path):
        if ".DS_Store" in curr_path:
            return
        if os.path.isfile(os.path.join(base_dir, curr_path)):
            filelist.append(curr_path)
        else:
            for f in os.listdir(os.path.join(base_dir, curr_path)):
                get_files(os.path.join(curr_path, f))

    get_files(path)

    new_stage_list = []
    for file in filelist:
        stage_id = os.path.splitext(os.path.split(file)[1])[0]
        if file.lower() in stage_id_list:
            logger.info(stage_id, "already in stage_table. Pass.")
            continue
        level_table = ctx.getgd(file.lower())

        unknown_stage = BasicStageView(
            code="—",
            name=stage_id,
            stage_id=stage_id.replace("level_", ""),
            stage_type="活动",
            difficulty="NORMAL",
            unlock_condition="—",
            recommended_level="—",
            zone="-",
            level=build_level_info(level_table, notCount_list),
            description="",
            ap_cost=0,
            practice_cost=-1,
        )

        enemies = _build_enemy_views(ctx, level_table)
        squads = build_squad_sections(
            level_table, stage_id, character_table, skill_table
        )
        stage_content = render_basic_page(
            BasicPageView(
                stage=unknown_stage,
                enemies=enemies,
                squads=squads,
            ),
            notoc=True,
        )

        ctx.wiki.edit(
            title=stage_id, text=stage_content, summary="init", bot=None, minor=True
        )
        # logger.info(stage_content)
        logger.info(f"Created: {stage_id}.")
        new_stage_list.append(f"\n* [[{stage_id}]]")

    if new_stage_list != []:
        ctx.wiki.edit(
            title="首页/新增关卡",
            appendtext="".join(new_stage_list),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info('\n'.join(new_stage_list))
        logger.info("Updated: {}.".format("首页/新增关卡"))


def _build_enemy_views(ctx: JobContext, level_table, flag_skip0=False):
    enemy_table = ctx.getgd("excel/enemy_handbook_table.json")
    enemy_database = ctx.getgd("levels/enemydata/enemy_database.json")
    return build_enemies(
        level_table, enemy_table["enemyData"], enemy_database, flag_skip0
    )
