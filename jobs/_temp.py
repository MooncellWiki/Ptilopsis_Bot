import csv
import io
import re

from utils.job import Job


class Temp(Job):
    def update_enemyId(self):
        enemy_handbook_table = self.getgd("excel/enemy_handbook_table.json")

        enemys = self.wiki.category("分类:敌人")

        for enemy_key in enemy_handbook_table:
            enemy_datum = enemy_handbook_table[enemy_key]

            if enemy_datum["name"] in enemys:
                old_text = self.wiki.read(enemy_datum["name"])
                replace_text = "{{{{敌人信息/common\n|id={id}\n|名称={name}\n|index={index}\n".format(
                    id=enemy_datum["sortId"],
                    name=enemy_datum["name"],
                    index=enemy_datum["enemyIndex"],
                )
            elif enemy_datum["name"] + "(敌方)" in enemys:
                old_text = self.wiki.read(enemy_datum["name"] + "(敌方)")
                replace_text = "{{{{敌人信息/common\n|id={id}\n|名称={name}(敌方)\n|显示名={name}\n|index={index}\n".format(
                    id=enemy_datum["sortId"],
                    name=enemy_datum["name"],
                    index=enemy_datum["enemyIndex"],
                )
            else:
                print(enemy_datum["name"], "页面未建立.")
                continue

            n1 = old_text.find("{{敌人信息/common")
            n2 = old_text.find("|地位级别")

            if n1 == -1 or n2 == -1:
                print(enemy_datum["name"], "not find.")
                continue

            new_text = old_text[:n1] + replace_text + old_text[n2:]
            if new_text != old_text:
                print(enemy_datum["name"], "Different.")
                old_id = re.search(r"\|id=([0-9]*)\n", old_text).group(1)
                new_id = re.search(r"\|id=([0-9]*)\n", new_text).group(1)
                print(f"old: {old_id}  new: {new_id}")
                # print(new_text)

                # self.wiki.edit(
                #     title=enemy_datum['name'],
                #     text=new_text,
                #     summary='修正sortId'
                # )
                # # print(content)
                # print('Updated: {}.'.format(enemy_datum['name']))

    def add_stage_drop(self):
        stage_table = self.getgd("excel/stage_table.json")
        roguelike_table = self.getgd("excel/roguelike_table.json")

        stage_list = self.wiki.category("分类:普通难度关卡")

        for stage_name in stage_list:
            content = self.wiki.read(stage_name)
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
                        self.wiki.edit(
                            title=stage_name,
                            text=content,
                            summary="添加模板:关卡材料掉落",
                        )
                        # print(content)
                        print(f"添加: {stage_name}.")
                    else:
                        print("已有:", stage_name)
                else:
                    if content.find("==材料掉落==\n{{关卡材料掉落}}") == -1:
                        print("无需添加:", stage_name)
                    else:
                        content = content.replace(
                            "==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==",
                            "==注释与链接==",
                        )
                        content = content.replace(
                            "==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==",
                            "==注释与链接==",
                        )
                        self.wiki.edit(
                            title=stage_name,
                            text=content,
                            summary="删去模板:关卡材料掉落",
                        )
                        # print(content)
                        print("删去多余:", stage_name)
            else:
                print("No stage id found:", stage_name)
                for sid in roguelike_table["stages"]:
                    if (
                        roguelike_table["stages"][sid]["code"]
                        + " "
                        + roguelike_table["stages"][sid]["name"]
                        == stage_name
                    ):
                        content = content.replace(
                            "|关卡类型", f"|关卡id={sid}\n|关卡类型"
                        )
                        self.wiki.edit(
                            title=stage_name,
                            text=content,
                            summary="添加肉鸽关卡stageId",
                        )
                        # print(content)
                        print("添加肉鸽关卡stageId:", stage_name)
                        break
                if content.find("==材料掉落==\n{{关卡材料掉落}}") == -1:
                    print("无需添加:", stage_name)
                else:
                    content = content.replace(
                        "==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==",
                        "==注释与链接==",
                    )
                    content = content.replace(
                        "==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==",
                        "==注释与链接==",
                    )
                    self.wiki.edit(
                        title=stage_name, text=content, summary="删去模板:关卡材料掉落"
                    )
                    # print(content)
                    print("删去多余:", stage_name)

    def test_yinyang(self):
        stage_table = self.getgd("excel/stage_table.json")

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
                    level_table = self.getgd(
                        "levels/" + stage_detail["levelId"] + ".json"
                    )
                except:
                    print(f"Cannot find level data of {stage_page_name}.")
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
            # print(stage_page_name)
            # flag = False
            # for tile in level_table['mapData']['tiles']:
            #     if 'yinyang' in tile['tileKey'] and tile['tileKey'] != 'tile_yinyang_switch':
            #         flag = True
            #         if not tile_diff(tile['blackboard']):
            #             print('Warning:', stage_page_name, tile['blackboard'])
            # if not flag:
            #     print(stage_page_name, '无晦明')

            for tile in level_table["mapData"]["tiles"]:
                if tile["effects"] is not None:
                    print(
                        stage_page_name,
                        stage_detail["stageId"],
                        tile["tileKey"],
                        "effects",
                    )

    def test_id(self):
        id_csv, id_table = self.wiki.read("干员一览/干员id"), {}
        reader = csv.DictReader(io.StringIO(id_csv))
        for row in reader:
            id_table[row["name"]] = {
                "id": row["sortId"],
                "approach": row["approach"],
                "date": row["date"],
            }
        print(id_table)
