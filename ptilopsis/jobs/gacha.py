import json
from typing import Any

import anyio

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.jobs.params import CharacterTable, RichText
from ptilopsis.log import logger
from ptilopsis.utils import richtext
from ptilopsis.utils.http import make_client
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def get_gacha_mainpage(
    character_table: dict[str, CharacterData],
    gacha_data: dict[str, Any],
    rts: richtext.RichText,
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


async def get_gacha_list(wiki: Wiki) -> None:
    a = {"国服寻访": [], "国际服寻访": []}

    page_list = await wiki.category("分类:国服寻访")
    # logger.info(page_list)
    texts = await wiki.read_many(page_list)
    for page in page_list:
        a["国服寻访"].append({"name": page, "text": texts[page]})

    page_list = await wiki.category("分类:国际服寻访")
    # logger.info(page_list)
    texts = await wiki.read_many(page_list)
    for page in page_list:
        a["国际服寻访"].append({"name": page, "text": texts[page]})

    await anyio.Path("test_gacha.txt").write_text(
        json.dumps(a, ensure_ascii=False, indent=4)
    )


async def update_gacha_list(wiki: Wiki) -> None:
    content = json.loads(await anyio.Path("test_gacha.txt").read_text(encoding="utf-8"))

    for page in content["国服寻访"]:
        await wiki.edit(title=page["name"], text=page["text"], summary="删除序号")
        # logger.info(page['text'])
    for page in content["国际服寻访"]:
        await wiki.edit(title=page["name"], text=page["text"], summary="删除序号")
        # logger.info(page['text'])


@job
async def run(wiki: Wiki, character_table: CharacterTable, rts: RichText) -> None:
    # await get_gacha_list(wiki)
    # await update_gacha_list(wiki)

    async with make_client() as client:
        resp = await client.get("https://weedy.baka.icu/gacha/LIMITED_9_0_3")
        resp.raise_for_status()
        gacha_data = resp.json()["detail"]

    logger.info("request success.")
    content = get_gacha_mainpage(character_table, gacha_data, rts)

    await wiki.edit(title="用户:Seniorious/test", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/test"))
