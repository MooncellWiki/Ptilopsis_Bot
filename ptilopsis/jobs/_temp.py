import csv
import io
import re

from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job


@job
def update_enemyId(ctx: JobContext) -> None:
    enemy_handbook_table = ctx.getgd("excel/enemy_handbook_table.json")

    enemys = ctx.wiki.category("分类:敌人")

    for enemy_key in enemy_handbook_table:
        enemy_datum = enemy_handbook_table[enemy_key]

        if enemy_datum["name"] in enemys:
            old_text = ctx.wiki.read(enemy_datum["name"])
            replace_text = (
                "{{{{敌人信息/common\n|id={id}\n|名称={name}\n|index={index}\n".format(
                    id=enemy_datum["sortId"],
                    name=enemy_datum["name"],
                    index=enemy_datum["enemyIndex"],
                )
            )
        elif enemy_datum["name"] + "(敌方)" in enemys:
            old_text = ctx.wiki.read(enemy_datum["name"] + "(敌方)")
            replace_text = "{{{{敌人信息/common\n|id={id}\n|名称={name}(敌方)\n|显示名={name}\n|index={index}\n".format(
                id=enemy_datum["sortId"],
                name=enemy_datum["name"],
                index=enemy_datum["enemyIndex"],
            )
        else:
            logger.info(enemy_datum["name"], "页面未建立.")
            continue

        n1 = old_text.find("{{敌人信息/common")
        n2 = old_text.find("|地位级别")

        if n1 == -1 or n2 == -1:
            logger.info(enemy_datum["name"], "not find.")
            continue

        new_text = old_text[:n1] + replace_text + old_text[n2:]
        if new_text != old_text:
            logger.info(enemy_datum["name"], "Different.")
            old_id = re.search(r"\|id=([0-9]*)\n", old_text).group(1)
            new_id = re.search(r"\|id=([0-9]*)\n", new_text).group(1)
            logger.info(f"old: {old_id}  new: {new_id}")
            # logger.info(new_text)

            # ctx.wiki.edit(
            #     title=enemy_datum['name'],
            #     text=new_text,
            #     summary='修正sortId'
            # )
            # # logger.info(content)
            # logger.info('Updated: {}.'.format(enemy_datum['name']))


@job
def add_stage_drop(ctx: JobContext) -> None:
    stage_table = ctx.getgd("excel/stage_table.json")
    roguelike_table = ctx.getgd("excel/roguelike_table.json")

    stage_list = ctx.wiki.category("分类:普通难度关卡")

    for stage_name in stage_list:
        content = ctx.wiki.read(stage_name)
        result = re.search("\\|关卡id=(.+?)\n", content)
        if result:
            stage_id = result.group(1)
            stage_detail = stage_table["stages"][stage_id]
            if (
                len(
                    list(
                        filter(
                            lambda x: x["dropType"] in [2, 3, 4],
                            stage_detail["stageDropInfo"]["displayDetailRewards"],
                        )
                    )
                )
                > 0
            ):
                if content.find("==材料掉落==\n{{关卡材料掉落}}") == -1:
                    if content.find("==注释与链接==") == -1:
                        content = content.replace(
                            "{{关卡导航}}",
                            "==注释与链接==\n<references/>\n{{关卡导航}}",
                        )
                    content = content.replace(
                        "==注释与链接==",
                        "==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==",
                    )
                    ctx.wiki.edit(
                        title=stage_name,
                        text=content,
                        summary="添加模板:关卡材料掉落",
                    )
                    # logger.info(content)
                    logger.info(f"添加: {stage_name}.")
                else:
                    logger.info("已有:", stage_name)
            else:
                if content.find("==材料掉落==\n{{关卡材料掉落}}") == -1:
                    logger.info("无需添加:", stage_name)
                else:
                    content = content.replace(
                        "==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==",
                        "==注释与链接==",
                    )
                    content = content.replace(
                        "==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==",
                        "==注释与链接==",
                    )
                    ctx.wiki.edit(
                        title=stage_name,
                        text=content,
                        summary="删去模板:关卡材料掉落",
                    )
                    # logger.info(content)
                    logger.info("删去多余:", stage_name)
        else:
            logger.info("No stage id found:", stage_name)
            for sid in roguelike_table["stages"]:
                if (
                    roguelike_table["stages"][sid]["code"]
                    + " "
                    + roguelike_table["stages"][sid]["name"]
                    == stage_name
                ):
                    content = content.replace("|关卡类型", f"|关卡id={sid}\n|关卡类型")
                    ctx.wiki.edit(
                        title=stage_name,
                        text=content,
                        summary="添加肉鸽关卡stageId",
                    )
                    # logger.info(content)
                    logger.info("添加肉鸽关卡stageId:", stage_name)
                    break
            if content.find("==材料掉落==\n{{关卡材料掉落}}") == -1:
                logger.info("无需添加:", stage_name)
            else:
                content = content.replace(
                    "==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==",
                    "==注释与链接==",
                )
                content = content.replace(
                    "==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==",
                    "==注释与链接==",
                )
                ctx.wiki.edit(
                    title=stage_name, text=content, summary="删去模板:关卡材料掉落"
                )
                # logger.info(content)
                logger.info("删去多余:", stage_name)


@job
def test_yinyang(ctx: JobContext) -> None:
    stage_table = ctx.getgd("excel/stage_table.json")

    for stage_id in stage_table["stages"]:
        stage_detail = stage_table["stages"][stage_id]
        if (
            stage_detail["stageType"]
            not in ["MAIN", "SUB", "DAILY", "ACTIVITY", "SPECIAL_STORY"]
            or stage_detail["difficulty"] == "FOUR_STAR"
        ):
            continue
        stage_page_name = (
            stage_detail["code"].strip() + " " + stage_detail["name"].strip()
        )
        # if 'WR-' not in stage_detail['code']:
        #     continue

        if stage_detail["levelId"]:
            try:
                level_table = ctx.getgd("levels/" + stage_detail["levelId"] + ".json")
            except:
                logger.info(f"Cannot find level data of {stage_page_name}.")
                continue
        else:
            continue

        # def tile_diff(t):
        #     flag = 0
        #     if t is None:
        #         return False
        #     if t[0]['key'] == 'dynamic' and t[0]['valueStr'] == None:
        #         flag += 1
        #     if t[1]['key'] == 'buff_yinyang[same].atk_scale' and t[1]['value'] == 0.6 and t[1]['valueStr'] == None:
        #         flag += 1
        #     if t[2]['key'] == 'buff_yinyang[diff].atk_scale' and t[2]['value'] == 1.4 and t[2]['valueStr'] == None:
        #         flag += 1
        #     if flag == 3:
        #         return True
        #     else:
        #         return False
        #
        # logger.info(stage_page_name)
        # flag = False
        # for tile in level_table['mapData']['tiles']:
        #     if 'yinyang' in tile['tileKey'] and tile['tileKey'] != 'tile_yinyang_switch':
        #         flag = True
        #         if not tile_diff(tile['blackboard']):
        #             logger.info('Warning:', stage_page_name, tile['blackboard'])
        # if not flag:
        #     logger.info(stage_page_name, '无晦明')

        for tile in level_table["mapData"]["tiles"]:
            if tile["effects"] is not None:
                logger.info(
                    stage_page_name,
                    stage_detail["stageId"],
                    tile["tileKey"],
                    "effects",
                )


@job
def test_id(ctx: JobContext) -> None:
    id_csv, id_table = ctx.wiki.read("干员一览/干员id"), {}
    reader = csv.DictReader(io.StringIO(id_csv))
    for row in reader:
        id_table[row["name"]] = {
            "id": row["sortId"],
            "approach": row["approach"],
            "date": row["date"],
        }
    logger.info(id_table)
