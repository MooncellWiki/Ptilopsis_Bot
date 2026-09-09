import json
from typing import Any

import requests

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.jobs.params import CharacterTable, RichText
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.richTextStyles import RichTextStyles
from ptilopsis.utils.wiki import Wiki


def get_gacha_mainpage(
    character_table: dict[str, CharacterData],
    gacha_data: dict[str, Any],
    rts: RichTextStyles,
) -> str:
    content = "===出现概率上升===\n"
    content += "<br/>".join(
        [
            "{rarity_star}\t占{rarity}★出率的{percent:.0%}<br/>{charIdList}".format(
                rarity=op["rarityRank"] + 1,
                rarity_star=(op["rarityRank"] + 1) * "★",
                percent=op["percent"] * op["count"],
                charIdList="/".join(
                    [
                        character_table[char_key].name or ""
                        for char_key in op["charIdList"]
                    ]
                ),
            )
            for op in gacha_data["up"]
        ]
    )

    content += "\n===全部可能出现的干员===\n"
    content += "<br/>".join(
        [
            "{rarity}\t出率{totalPercent:.0%}<br/>{charIdList}".format(
                rarity=(op["rarityRank"] + 1) * "★",
                totalPercent=op["totalPercent"],
                charIdList="/".join(
                    [
                        character_table[char_key].name or ""
                        for char_key in op["charIdList"]
                    ]
                ),
            )
            for op in gacha_data["ops"]
        ]
    )

    # content += '\n===该寻访为【限定寻访】===\n'
    # content += rts.compile('在所有<@limtedGa.21>【限定寻访】</>中，每进行一次寻访，可获取一张<@limtedGa.attention>【寻访数据契约】</>，寻访十次则可获取十张<@limtedGa.attention>【寻访数据契约】</>，<@limtedGa.attention>【寻访数据契约】</>可用于当期<@limtedGa.attention>【寻访数据契约交换所】</>兑换指定干员。')
    # content += '<br/>' + rts.compile('<@limtedGa.attention>【注意】</>在当期<@limtedGa.21>【限定寻访】</>中所获得的<@limtedGa.attention>【寻访数据契约】</>存在使用期限。在当期<@limtedGa.attention>【寻访数据契约交换所】</>关闭后，剩余未兑换的<@limtedGa.attention>【寻访数据契约】</>将会被自动兑换成<@limtedGa.lAttention>【寻访参数模型】</>，每张<@limtedGa.attention>【寻访数据契约】</>自动兑换成六张<@limtedGa.lAttention>【寻访参数模型】</>。<@limtedGa.lAttention>【寻访参数模型】</>不存在使用期限，可用于<@limtedGa.lAttention>【寻访参数模型交换所】</>兑换指定物品。')

    return content


def get_gacha_list(wiki: Wiki) -> None:
    a = {"国服寻访": [], "国际服寻访": []}

    page_list = wiki.category("分类:国服寻访")
    # logger.info(page_list)
    for page in page_list:
        text = wiki.read(page)
        a["国服寻访"].append({"name": page, "text": text})

    page_list = wiki.category("分类:国际服寻访")
    # logger.info(page_list)
    for page in page_list:
        text = wiki.read(page)
        a["国际服寻访"].append({"name": page, "text": text})

    with open("test_gacha.txt", "w") as f:
        json.dump(a, f, ensure_ascii=False, indent=4)


def update_gacha_list(wiki: Wiki) -> None:
    with open("test_gacha.txt", encoding="utf-8") as f:
        content = json.loads(f.read())

    for page in content["国服寻访"]:
        wiki.edit(title=page["name"], text=page["text"], summary="删除序号")
        # logger.info(page['text'])
    for page in content["国际服寻访"]:
        wiki.edit(title=page["name"], text=page["text"], summary="删除序号")
        # logger.info(page['text'])


@job
def run(wiki: Wiki, character_table: CharacterTable, rts: RichText) -> None:
    # get_gacha_list(wiki)
    # update_gacha_list(wiki)

    session = requests.Session()
    gacha_data = session.get("https://weedy.baka.icu/gacha/LIMITED_9_0_3").json()[
        "detail"
    ]

    logger.info("request success.")
    content = get_gacha_mainpage(character_table, gacha_data, rts)

    wiki.edit(title="用户:Seniorious/test", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/test"))
