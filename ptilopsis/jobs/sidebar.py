import csv
import io
import re

from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job


def update_menusidebar(wiki, old_num, id_table, character_table):
    char_list = [character_table[char]["name"] for char in character_table]
    new_num = max([id_table[char]["id"] for char in id_table if char in char_list])
    if new_num <= old_num:
        return

    origin_text = wiki.read("MediaWiki:MenuSidebar")
    num1 = origin_text.find("*[[干员一览")
    num2 = origin_text.find("*[[干员一览")

    content = ""
    for name in id_table:
        if int(id_table[name]["id"]) > old_num:
            content = f"**[[{name}]]\n" + content
        trans = origin_text.find(f"**[[{name}]]")
        if 1 < trans and trans < num1:
            num1 = trans
    new_text = origin_text[:num1] + content + origin_text[num2:]

    wiki.edit(
        title="MediaWiki:MenuSidebar",
        text=new_text,
        summary="update",
        bot=None,
        minor=True,
    )
    # logger.info(new_text)
    logger.info("Update: {}.".format("MediaWiki:MenuSidebar"))


def update_mainpage(wiki, old_num, id_table):
    # 已弃用

    fin2 = wiki.read("首页")
    num1 = fin2.find("==近期新增==")
    num2 = fin2.find("==网站信息==")

    content = ""
    for name in id_table:
        if int(id_table[name]["id"]) > old_num:
            content = f"{{{{干员头像|{name}|80px}}}} " + content
    content = "==近期新增==\n===新增干员===\n" + content[:-1] + "\n"
    fin = fin2[:num1] + content + fin2[num2:]

    wiki.edit(title="首页", text=fin, summary="update")
    logger.info(fin)
    logger.info("Update: {}.".format("首页"))


def update_gameinfo(wiki, old_num, id_table, character_table):
    char_list = [character_table[char]["name"] for char in character_table]
    new_num = max([id_table[char]["id"] for char in id_table if char in char_list])
    if new_num <= old_num:
        return

    origin_text = wiki.read("PRTS:Gameinfo/国服/干员一览")
    new_text = re.sub(
        r"cnotrs />([0-9]*)<section", f"cnotrs />{new_num}<section", origin_text
    )
    new_text = re.sub(
        r"cnprevotrs />([0-9]*)<section", f"cnprevotrs />{old_num}<section", new_text
    )
    wiki.edit(
        title="PRTS:Gameinfo/国服/干员一览",
        text=new_text,
        summary="update",
        bot=None,
        minor=True,
    )
    # logger.info(new_text)
    logger.info("Update: {}.".format("PRTS:Gameinfo/国服/干员一览"))


@job
def update(ctx: JobContext) -> None:
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
    character_table = ctx.getgd("excel/character_table.json")
    old_num, char_list = -1, ctx.wiki.category("分类:干员")
    for char_key in character_table:
        name = character_table[char_key]["name"]
        if name in id_table and name in char_list and id_table[name]["id"] > old_num:
            old_num = id_table[name]["id"]
    update_menusidebar(ctx.wiki, old_num, id_table, character_table)
    update_gameinfo(ctx.wiki, old_num, id_table, character_table)
