"""关卡路线与出怪表(试验性,输出到用户页)。"""

from collections.abc import Sequence
from typing import Any

from ptilopsis.gamedata.enemy_handbook_table import EnemyHandBookData
from ptilopsis.gamedata.level_data import (
    GridPosition,
    LevelDataWaveData,
    LevelDataWaveDataFragmentDataActionData,
    RouteData,
    RouteDataCheckpointData,
    UnityEngineVector2,
)
from ptilopsis.jobs.params import EnemyHandbookTable, Levels
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

WAVE_TABLE_HEAD = (
    '{|class="wikitable sortable" '
    'style="text-align:center; width:800px; display:table; white-space:normal;"'
    "\n!No.!!头像!!名字!!总时间!!当前波次时间"
)
WAVE_TABLE_ROUTE_ROW = (
    '\n|- class="expand-child" '
    'style="font-size:85%; line-height:1.2; color:gray;"'
    '\n|colspan="5"|{}'
)


def format_time(time: float) -> str:
    return f"{int(time / 60)}分{time % 60:.1f}秒"


def parse_checkPointType(checkpoint_type: str, time: float, x: str, y: str) -> str:
    return {
        "MOVE": f"→({x}, {y})",
        "WAIT_FOR_SECONDS": f"(WAIT: {time}s)",
        "WAIT_FOR_PLAY_TIME": f"(WAIT_PLAY: {time}s)",
        "WAIT_CURRENT_FRAGMENT_TIME": f"(WAIT_FRAGMENT: {time}s)",
        "WAIT_CURRENT_WAVE_TIME": f"(WAIT_WAVE: {time}s)",
        "DISAPPEAR": "→通道",
        "APPEAR_AT_POS": f"→({x}, {y})",
    }.get(checkpoint_type, "(UNKNOWN)")


def parse_checkpoint(checkpoint: RouteDataCheckpointData) -> str:
    if checkpoint.randomize_reach_offset:
        logger.info("randomizeReachOffset = True")
    if checkpoint.reach_distance != 0.0:
        logger.info(f"reachDistance = {checkpoint.reach_distance}")

    position = checkpoint.position or GridPosition()
    offset = checkpoint.reach_offset or UnityEngineVector2()
    x_pos = f"{position.col}" if offset.x == 0.0 else f"{position.col + offset.x}"
    y_pos = f"{position.row}" if offset.y == 0.0 else f"{position.row + offset.y}"
    return parse_checkPointType(checkpoint.type, checkpoint.time, x_pos, y_pos)


def parse_route(route: RouteData | None) -> str | None:
    """路线写成 ``(起点)→(检查点)…→(终点)``;起点带随机范围 / 偏移。"""

    if route is None:
        return None
    start = route.start_position or GridPosition()
    end = route.end_position or GridPosition()
    random_range = route.spawn_random_range or UnityEngineVector2()
    spawn_offset = route.spawn_offset or UnityEngineVector2()

    start_x = f"{start.col}"
    if random_range.x != 0.0:
        start_x += f"±{random_range.x}"
    if spawn_offset.x != 0.0:
        start_x += f"+{spawn_offset.x}"
    start_y = f"{start.row}"
    if random_range.y != 0.0:
        start_y += f"±{random_range.y}"
    if spawn_offset.y != 0.0:
        start_y += f"+{spawn_offset.y}"
    route_result = f"({start_x}, {start_y})"
    for checkpoint in route.checkpoints or []:
        route_result += parse_checkpoint(checkpoint)
    route_result += f"→({end.col}, {end.row})"
    return route_result


def get_routes(level_routes: Sequence[RouteData | None]) -> list[str | None]:
    return [parse_route(route) for route in level_routes]


def action_span(action: LevelDataWaveDataFragmentDataActionData) -> float:
    """一个动作从片段开始到最后一次出怪的时间。"""

    return action.pre_delay + (action.count - 1) * action.interval


def get_waves(level_waves: list[LevelDataWaveData]) -> None:
    """记录按 preDelay / interval 推算的最短通关时间。"""

    min_time = 0.0
    for wave in level_waves:
        min_time += wave.pre_delay
        for fragment in wave.fragments or []:
            min_time += fragment.pre_delay
            min_time += max(action_span(action) for action in fragment.actions or [])
        min_time += wave.post_delay
    logger.info(format_time(min_time))


def count_enemy(level_waves: list[LevelDataWaveData]) -> None:
    """记录敌人总数与最短时间;随机出怪组分别按最少 / 最多统计。"""

    e_num = 0
    e_low = 0
    e_high = 0
    min_time_low = 0.0
    min_time_high = 0.0
    for wave in level_waves:
        min_time_low += wave.pre_delay
        min_time_high += wave.pre_delay
        for fragment in wave.fragments or []:
            actions = fragment.actions or []
            min_time_low += fragment.pre_delay
            min_time_high += fragment.pre_delay
            spans_low = [
                action_span(action)
                for action in actions
                if action.random_spawn_group_key is None
            ]
            spans_high = list(spans_low)

            spawn_groups: dict[str, list[LevelDataWaveDataFragmentDataActionData]] = {}
            for action in actions:
                if action.action_type != "SPAWN":
                    continue
                if action.random_spawn_group_key is not None:
                    spawn_groups.setdefault(action.random_spawn_group_key, []).append(
                        action
                    )
                else:
                    e_num += action.count
            for group in spawn_groups.values():
                counts = [a.count if a.key != "" else 0 for a in group]
                spans = [action_span(a) for a in group]
                e_low += min(counts)
                e_high += max(counts)
                spans_low.append(min(spans))
                spans_high.append(max(spans))

            if spans_low:
                min_time_low += max(spans_low)
            if spans_high:
                min_time_high += max(spans_high)

        min_time_low += wave.post_delay
    if e_low != e_high:
        logger.info(f"num: {e_low + e_num}~{e_high + e_num}")
    else:
        logger.info(f"num: {e_low + e_num}")
    if min_time_low != min_time_high:
        logger.info(f"time: {format_time(min_time_low)}~{format_time(min_time_high)}")
    else:
        logger.info(f"time: {format_time(min_time_low)}")


def get_waves_table(
    level_waves: list[LevelDataWaveData],
    routes: list[str | None],
    enemy_table: dict[str, EnemyHandBookData],
) -> str:
    """按出场时间排序的出怪表,每行下面附一行路线。"""

    total_time = 0.0
    spawns: list[dict[str, Any]] = []
    for wave in level_waves:
        wave_time = wave.pre_delay
        total_time += wave.pre_delay
        for fragment in wave.fragments or []:
            actions = fragment.actions or []
            wave_time += fragment.pre_delay
            total_time += fragment.pre_delay
            for action in actions:
                if action.action_type != "SPAWN":
                    continue
                handbook = (
                    enemy_table.get(action.key) if action.key is not None else None
                )
                name = handbook.name if handbook is not None else "未知"
                for action_count in range(action.count):
                    spawns.append(
                        {
                            "time_w": wave_time
                            + action.pre_delay
                            + action_count * action.interval,
                            "time_t": total_time
                            + action.pre_delay
                            + action_count * action.interval,
                            "name": name,
                            "route": routes[action.route_index],
                        }
                    )
            span = max(action_span(action) for action in actions)
            wave_time += span
            total_time += span
        total_time += wave.post_delay

    wave_table = WAVE_TABLE_HEAD
    for count, enemy in enumerate(sorted(spawns, key=lambda x: x["time_t"]), 1):
        wave_table += "\n|-\n|{}\n|{{{{敌人头像|{}|px=50}}}}\n|{}\n|{}\n|{}".format(
            count,
            enemy["name"],
            enemy["name"],
            format_time(enemy["time_t"]),
            format_time(enemy["time_w"]),
        )
        wave_table += WAVE_TABLE_ROUTE_ROW.format(enemy["route"])
    wave_table += "\n|}"

    return wave_table


@job
def run(wiki: Wiki, enemy_handbook_table: EnemyHandbookTable, levels: Levels) -> None:
    """把指定关卡的出怪表写到 ``用户:Seniorious/route``(调试用)。"""

    path = "levels/obt/roguelike/ro3/level_rogue3_5-1.json"
    # path = "levels/activities"
    enemy_data = enemy_handbook_table.enemy_data or {}

    for level_id in levels.list_ids(path):
        level = levels(level_id)
        routes = get_routes(level.routes or [])
        get_waves(level.waves or [])
        wave_table = get_waves_table(level.waves or [], routes, enemy_data)

        # 统计初代肉鸽各关的敌人数与最短时间(roguelike_table: RoguelikeTable):
        # for stage in (roguelike_table.stages or {}).values():
        #     if stage.level_id and stage.difficulty != "FOUR_STAR":
        #         logger.info(f"==={stage.code} {stage.name}===")
        #         count_enemy(levels(stage.level_id).waves or [])

        wiki.edit(title="用户:Seniorious/route", text=wave_table, summary="update")
        logger.info("Updated: 用户:Seniorious/route.")
