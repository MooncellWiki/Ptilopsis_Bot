import csv
import io

from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles


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
    }[profession]


def get_char_attr(character_table, uniequip_table, id_table, rts):
    content = []
    for char in character_table:
        char_detail = character_table[char]
        if char_detail["profession"] == "TRAP" or char_detail["profession"] == "TOKEN":
            continue

        final_phase = char_detail["phases"][len(char_detail["phases"]) - 1]

        maxHp = final_phase["attributesKeyFrames"][1]["data"]["maxHp"]
        atk = final_phase["attributesKeyFrames"][1]["data"]["atk"]
        defence = final_phase["attributesKeyFrames"][1]["data"]["def"]
        magicResistance = final_phase["attributesKeyFrames"][1]["data"][
            "magicResistance"
        ]
        cost = final_phase["attributesKeyFrames"][1]["data"]["cost"]
        blockCnt = final_phase["attributesKeyFrames"][1]["data"]["blockCnt"]
        attackSpeed = final_phase["attributesKeyFrames"][1]["data"]["attackSpeed"]
        baseAttackTime = final_phase["attributesKeyFrames"][1]["data"]["baseAttackTime"]
        respawnTime = final_phase["attributesKeyFrames"][1]["data"]["respawnTime"]

        atk += char_detail["favorKeyFrames"][1]["data"]["atk"]
        defence += char_detail["favorKeyFrames"][1]["data"]["def"]
        maxHp += char_detail["favorKeyFrames"][1]["data"]["maxHp"]

        for potentialRank in char_detail["potentialRanks"]:
            if potentialRank["type"] == "BUFF":
                attributeType = potentialRank["buff"]["attributes"][
                    "attributeModifiers"
                ][0]["attributeType"]
                if attributeType == "MAX_HP":
                    maxHp += potentialRank["buff"]["attributes"]["attributeModifiers"][
                        0
                    ]["value"]
                elif attributeType == "ATK":
                    atk += potentialRank["buff"]["attributes"]["attributeModifiers"][0][
                        "value"
                    ]
                elif attributeType == "DEF":
                    defence += potentialRank["buff"]["attributes"][
                        "attributeModifiers"
                    ][0]["value"]
                elif attributeType == "MAGIC_RESISTANCE":
                    magicResistance += potentialRank["buff"]["attributes"][
                        "attributeModifiers"
                    ][0]["value"]
                elif attributeType == "COST":
                    cost += potentialRank["buff"]["attributes"]["attributeModifiers"][
                        0
                    ]["value"]
                elif attributeType == "ATTACK_SPEED":
                    attackSpeed += potentialRank["buff"]["attributes"][
                        "attributeModifiers"
                    ][0]["value"]
                elif attributeType == "RESPAWN_TIME":
                    respawnTime += potentialRank["buff"]["attributes"][
                        "attributeModifiers"
                    ][0]["value"]
                else:
                    logger.info(
                        "Error! Char {name} attributeType {num} don't know!".format(
                            name=char_detail["name"], num=attributeType
                        )
                    )

        desc = "|[[{name}]]||{rarity}||{profession}||{subProfession}||{maxHp:.0f}||{atk:.0f}||{defence:.0f}||{magicResistance:.0f}||{cost:.0f}||{blockCnt:.0f}||{attackSpeed:.0f}||{baseAttackTime}s||data-sort-value={respawnTime:.0f}|{respawnTime:.0f}s".format(
            name=char_detail["name"],
            rarity=char_detail["rarity"][-1],
            profession=trans_profession(char_detail["profession"]),
            subProfession=uniequip_table["subProfDict"][char_detail["subProfessionId"]][
                "subProfessionName"
            ].strip(),
            maxHp=maxHp,
            atk=atk,
            defence=defence,
            magicResistance=magicResistance,
            cost=cost,
            blockCnt=blockCnt,
            attackSpeed=attackSpeed,
            baseAttackTime=baseAttackTime,
            respawnTime=respawnTime,
        )
        if char_detail["talents"]:
            remark = "<br/>".join(
                [
                    rts.compile(talent["candidates"][-1]["description"])
                    for talent in char_detail["talents"] if talent["candidates"] is not None and talent["candidates"][-1]["description"] is not None
                ]
            )
            desc += f'\n|- class="expand-child" style="font-size:85%; line-height:1.2; color:gray;"\n|colspan="13"|{remark}'

        content.append(
            {
                "sortId": id_table[char_detail["name"]]["id"]
                if char_detail["name"] in id_table
                else 1000,
                "text": desc,
            }
        )

    table = """{{cbox2|lv=2|text=以下为全体干员\'\'\'满精英化 满级 满潜能 满信赖\'\'\'时的面板白值，\'\'\'不包括\'\'\'天赋、模组和技能加成。}}
{|class="wikitable sortable" style="text-align:center; width:1000px; display:table; white-space:normal;"
!名字!!稀有度!!职业!!分支!!生命!!攻击!!防御!!法抗!!费用!!阻挡!!攻速!!攻击间隔!!再部署
|-
"""
    table += "\n|-\n".join(
        [
            data["text"]
            for data in sorted(content, key=lambda x: x["sortId"], reverse=True)
        ]
    )
    table += "\n|}"

    return table


@job
def run(ctx: JobContext) -> None:
    character_table = ctx.getgd("excel/character_table.json")
    uniequip_table = ctx.getgd("excel/uniequip_table.json")
    # with open('character_id.json', 'r', encoding = 'utf-8') as file:
    #     id_table = json.loads(file.read())
    # id_table = json.loads(ctx.wiki.read('用户:Seniorious/CharacterId'))
    id_csv, id_table = ctx.wiki.read("干员一览/干员id"), {}
    reader = csv.DictReader(io.StringIO(id_csv))
    for row in reader:
        id_table[row["name"]] = {
            "id": int(row["sortId"]),
            "approach": row["approach"],
            "date": row["date"],
        }
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    content = get_char_attr(character_table, uniequip_table, id_table, rts)

    ctx.wiki.edit(title="用户:Seniorious/attribute", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/attribute"))
