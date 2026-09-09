"""一次性 / 试验脚本。下划线开头,``discover_jobs`` 不会导入,需要时手动运行。"""

import re
from typing import Annotated

from ptilopsis.gamedata.stage_table import StageDropType
from ptilopsis.jobs.params import (
    CharIdTable,
    EnemyHandbookTable,
    Levels,
    RoguelikeTable,
    StageTable,
    category,
)
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

MATERIAL_DROP_TYPES = {
    StageDropType.NORMAL.name,
    StageDropType.SPECIAL.name,
    StageDropType.ADDITIONAL.name,
}
"""算作"材料掉落"的 dropType(旧表里写作数值 2 / 3 / 4)。"""

DROP_SECTION = "==材料掉落==\n{{关卡材料掉落}}"


def _sort_id(text: str) -> str | None:
    match = re.search(r"\|id=([0-9]*)\n", text)
    return match.group(1) if match else None


@job
def update_enemyId(
    wiki: Wiki,
    enemy_handbook_table: EnemyHandbookTable,
    enemy_pages: Annotated[list[str], category("分类:敌人")],
) -> None:
    """核对已建页敌人的 sortId / index 与图鉴是否一致(只记日志,不提交)。"""

    for enemy in (enemy_handbook_table.enemy_data or {}).values():
        name = enemy.name or ""
        if name in enemy_pages:
            old_text = wiki.read(name)
            replace_text = (
                f"{{{{敌人信息/common\n|id={enemy.sort_id}\n|名称={name}\n"
                f"|index={enemy.enemy_index}\n"
            )
        elif name + "(敌方)" in enemy_pages:
            old_text = wiki.read(name + "(敌方)")
            replace_text = (
                f"{{{{敌人信息/common\n|id={enemy.sort_id}\n|名称={name}(敌方)\n"
                f"|显示名={name}\n|index={enemy.enemy_index}\n"
            )
        else:
            logger.info(f"{name} 页面未建立.")
            continue

        n1 = old_text.find("{{敌人信息/common")
        n2 = old_text.find("|地位级别")

        if n1 == -1 or n2 == -1:
            logger.info(f"{name} not find.")
            continue

        new_text = old_text[:n1] + replace_text + old_text[n2:]
        if new_text != old_text:
            logger.info(f"{name} Different.")
            logger.info(f"old: {_sort_id(old_text)}  new: {_sort_id(new_text)}")
            # wiki.edit(title=name, text=new_text, summary="修正sortId")
            # logger.info(f"Updated: {name}.")


def _remove_drop_section(wiki: Wiki, stage_name: str, content: str) -> None:
    """页面里有 ``{{关卡材料掉落}}`` 但关卡没有材料掉落时,把这一节删掉。"""

    if content.find(DROP_SECTION) == -1:
        logger.info(f"无需添加: {stage_name}")
        return
    content = content.replace(DROP_SECTION + "\n==注释与链接==", "==注释与链接==")
    content = content.replace(DROP_SECTION + "\n\n==注释与链接==", "==注释与链接==")
    wiki.edit(title=stage_name, text=content, summary="删去模板:关卡材料掉落")
    logger.info(f"删去多余: {stage_name}")


@job
def add_stage_drop(
    wiki: Wiki,
    stage_table: StageTable,
    roguelike_table: RoguelikeTable,
    stage_pages: Annotated[list[str], category("分类:普通难度关卡")],
) -> None:
    """按关卡有没有材料掉落,给关卡页面加上或删去 ``{{关卡材料掉落}}`` 一节。"""

    stages = stage_table.stages or {}
    roguelike_stages = roguelike_table.stages or {}

    for stage_name in stage_pages:
        content = wiki.read(stage_name)
        result = re.search(r"\|关卡id=(.+?)\n", content)
        if not result:
            logger.info(f"No stage id found: {stage_name}")
            for sid, stage in roguelike_stages.items():
                if f"{stage.code} {stage.name}" == stage_name:
                    content = content.replace("|关卡类型", f"|关卡id={sid}\n|关卡类型")
                    wiki.edit(
                        title=stage_name, text=content, summary="添加肉鸽关卡stageId"
                    )
                    logger.info(f"添加肉鸽关卡stageId: {stage_name}")
                    break
            _remove_drop_section(wiki, stage_name, content)
            continue

        stage_detail = stages[result.group(1)]
        drop_info = stage_detail.stage_drop_info
        rewards = drop_info.display_detail_rewards if drop_info is not None else None
        has_material = any(r.drop_type in MATERIAL_DROP_TYPES for r in rewards or [])
        if not has_material:
            _remove_drop_section(wiki, stage_name, content)
            continue

        if content.find(DROP_SECTION) != -1:
            logger.info(f"已有: {stage_name}")
            continue
        if content.find("==注释与链接==") == -1:
            content = content.replace(
                "{{关卡导航}}", "==注释与链接==\n<references/>\n{{关卡导航}}"
            )
        content = content.replace("==注释与链接==", DROP_SECTION + "\n==注释与链接==")
        wiki.edit(title=stage_name, text=content, summary="添加模板:关卡材料掉落")
        logger.info(f"添加: {stage_name}.")


@job
def test_yinyang(stage_table: StageTable, levels: Levels) -> None:
    """列出各关卡里带 effects 的地块(排查晦明地块用)。"""

    for stage_detail in (stage_table.stages or {}).values():
        if (
            stage_detail.stage_type
            not in ("MAIN", "SUB", "DAILY", "ACTIVITY", "SPECIAL_STORY")
            or stage_detail.difficulty == "FOUR_STAR"
        ):
            continue
        code = (stage_detail.code or "").strip()
        stage_page_name = f"{code} {(stage_detail.name or '').strip()}"

        if not stage_detail.level_id:
            continue
        try:
            level = levels(stage_detail.level_id)
        except Exception:
            logger.info(f"Cannot find level data of {stage_page_name}.")
            continue

        tiles = level.map_data.tiles if level.map_data is not None else None
        for tile in tiles or []:
            if tile.effects is not None:
                logger.info(
                    f"{stage_page_name} {stage_detail.stage_id} {tile.tile_key} effects"
                )


@job
def test_id(char_id_table: CharIdTable) -> None:
    """打印 wiki 上 ``干员一览/干员id`` 解析后的内容。"""

    logger.info(char_id_table)
