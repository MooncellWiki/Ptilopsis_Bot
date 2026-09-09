import re
from typing import Annotated

from ptilopsis.gamedata.building_data import BuildingData, BuildingDataCustomData
from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.charword_table import CharWordData, CharWordTable
from ptilopsis.gamedata.skill_table import SkillDataBundle
from ptilopsis.jobs.params import table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def _norm_cn(text: str) -> str:
    text = text.replace("Dr.{@nickname}", "{{DrName|前缀=Dr.}}")
    text = text.replace("{@nickname}", "{{DrName}}")
    return text.rstrip().replace("~~~", "<nowiki>~~~</nowiki>")


def _norm_jp(text: str) -> str:
    text = text.replace("{@nickname}", "{{DrName}}")
    return text.rstrip().replace("~~~", "<nowiki>~~~</nowiki>")


def get_charword_data_jp(
    char_id: str,
    char_name: str,
    char_words: dict[str, CharWordData],
    char_words_jp: dict[str, CharWordData],
) -> str:
    char_word = """<noinclude>
==语音记录==
</noinclude>{{#invoke:VoiceTable|table|表格标题=语音记录
<noinclude>|可播放=1</noinclude>"""
    for charword_id, data in char_words.items():
        if char_id not in charword_id:
            continue
        char_word += "\n"
        if data.unlock_type not in ("DIRECT", "AWAKE", "FAVOR"):
            continue
        idx = data.voice_index
        title = data.voice_title
        text_cn = _norm_cn(data.voice_text or "")
        text_jp = _norm_jp(char_words_jp[charword_id].voice_text or "")
        char_word += (
            f"|标题{idx}={title}\n|日文{idx}={text_jp}\n|中文{idx}={text_cn}\n"
            f"|语音{idx}={char_name} {title}.wav\n"
        )
        if data.unlock_type == "AWAKE":
            unlock_condition = (data.lock_description or "").replace(
                "以查看更多信息", "以查看"
            )
            char_word += f"|条件{idx}={unlock_condition}\n"
        elif data.unlock_type == "FAVOR":
            unlock_condition = replace_story_condition(
                data.lock_description or "",
                (data.unlock_param or [])[0].value_int,
            ).replace("以查看更多信息", "以查看")
            char_word += f"|条件{idx}={unlock_condition}\n"
    char_word += "}}"
    return char_word


def replace_story_condition(text: str, num: int) -> str:
    p1 = r"(.*)信赖(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + "信赖至" + str(num) + "%" + result.group(2)
    return text


# out of date
def update_charword_jp(
    wiki: Wiki,
    character_table: dict[str, CharacterData],
    charword_table: CharWordTable,
    character_table_jp: dict[str, CharacterData],
    charword_table_jp: CharWordTable,
) -> None:
    char_words = charword_table.char_words or {}
    char_words_jp = charword_table_jp.char_words or {}
    for char in character_table_jp:
        char_detail = character_table[char]

        if char_detail.profession == "TRAP" or char_detail.profession == "TOKEN":
            continue
        name = char_detail.name or ""

        origin_text = wiki.read(name + "/语音记录")
        new_text = get_charword_data_jp(char, name, char_words, char_words_jp)
        new_text += "\n<noinclude>[[分类:有官方日文文本的干员语音]]</noinclude>"

        # edit wiki
        if origin_text != new_text:
            # logger.info(new_text)
            wiki.edit(
                title=name + "/语音记录",
                text=new_text,
                summary="update",
            )
            logger.info("Update: {}.".format(name + "/语音记录"))
        else:
            logger.info("Same: {}.".format(name + "/语音记录"))


def _skill_name(bundle: SkillDataBundle) -> str | None:
    """技能 1 级时的名字。"""
    levels = bundle.levels or []
    return levels[0].name


def update_skill_and_name(
    wiki: Wiki,
    character_table: dict[str, CharacterData],
    skill_table: dict[str, SkillDataBundle],
    character_table_jp: dict[str, CharacterData],
    skill_table_jp: dict[str, SkillDataBundle],
    character_table_en: dict[str, CharacterData],
    skill_table_en: dict[str, SkillDataBundle],
) -> None:
    for char in character_table_jp:
        char_detail = character_table[char]
        # if (char_detail['name'] != '能天使' or char_detail['profession'] == 'TRAP'
        #         or char_detail['profession'] == 'TOKEN'):
        if char_detail.profession == "TRAP" or char_detail.profession == "TOKEN":
            continue
        if char_detail.is_not_obtainable is True:
            continue
        name = char_detail.name or ""

        try:
            origin_text = wiki.read(name)
            new_text = origin_text
        except Exception:
            continue

        # update skill name
        if char_detail.skills:
            count = 0
            for skills_cont in char_detail.skills:
                count += 1
                skill_id = skills_cont.skill_id
                if skill_id is None:
                    continue
                skill_name = _skill_name(skill_table[skill_id])
                skill_name_jp = _skill_name(skill_table_jp[skill_id])
                skill_name_en = (
                    _skill_name(skill_table_en[skill_id])
                    if skill_id in skill_table_en
                    else ""
                )

                num1 = new_text.find(f"|技能名={skill_name}")
                if num1 == -1:
                    continue
                num2 = -1
                for i in range(count):
                    num2 = new_text.find("|技能类型1=", num2 + 1)
                new_text = (
                    new_text[:num1]
                    + f"|技能名={skill_name}\n"
                    + f"|技能名jp={skill_name_jp}\n"
                    + f"|技能名en={skill_name_en}\n"
                    + new_text[num2:]
                )

        # update char name
        name_jp = character_table_jp[char].name
        name_en = character_table_en[char].name if char in character_table_en else name

        num1 = new_text.find(f"|干员名={name}")
        num2 = new_text.find("|干员外文名=")
        if num1 == -1 or num2 == -1:
            continue
        new_text = (
            new_text[:num1]
            + f"|干员名={name}\n"
            + f"|干员名jp={name_jp}\n"
            + new_text[num2:]
        )

        num1 = new_text.find("{{pathnav2|干员一览}}")
        new_text = f"{{{{干员页面名|{name}|{name_en}|{name_jp}}}}}" + new_text[num1:]

        # edit wiki
        if origin_text != new_text:
            # logger.info(new_text)
            wiki.edit(
                title=name,
                text=new_text,
                summary="update",
            )
            logger.info(f"Update: {name}.")
        else:
            logger.info(f"Same: {name}.")

        if name != name_jp:
            redirect_text = f"#redirect [[{name}]]"
            wiki.edit(title=name_jp, text=redirect_text, summary="init", createonly="1")


def _custom_data(building_data: BuildingData) -> BuildingDataCustomData:
    """家具、主题、套装数据;整张表都有,缺失视为数据异常。"""
    if building_data.custom_data is None:
        raise ValueError("building_data 缺少 customData")
    return building_data.custom_data


def update_furni_info(
    wiki: Wiki,
    building_data: BuildingData,
    building_data_jp: BuildingData,
    building_data_en: BuildingData,
) -> None:
    custom_cn = _custom_data(building_data)
    furnitures_cn = custom_cn.furnitures or {}
    furnitures_jp = _custom_data(building_data_jp).furnitures or {}
    furnitures_en = _custom_data(building_data_en).furnitures or {}
    for furni in furnitures_cn:
        if furni not in furnitures_jp or furni not in furnitures_en:
            continue
        furni_data_cn = furnitures_cn[furni]
        furni_data_jp = furnitures_jp[furni]
        furni_data_en = furnitures_en[furni]

        page_name = furni_data_cn.name or ""
        if page_name in ["松软沙发"]:
            themes = ""
            for groups_data in (custom_cn.groups or {}).values():
                if furni_data_cn.id in (groups_data.furniture or []):
                    theme_id = groups_data.theme_id or ""
                    themes = (custom_cn.themes or {})[theme_id].name or ""
                    break
            page_name += f"（{themes}）"
        origin_text = wiki.read(page_name)
        new_text = origin_text

        # update info
        num1 = new_text.find("|描述=")
        num2 = new_text.find("|用途=")
        new_text = (
            new_text[:num1]
            + f"|描述={furni_data_cn.description}\n"
            + f"|描述jp={furni_data_jp.description}\n"
            + f"|描述en={furni_data_en.description}\n"
            + new_text[num2:]
        )
        num1 = new_text.find("|名称=")
        num2 = new_text.find("|iconId=")
        new_text = (
            new_text[:num1]
            + f"|名称={furni_data_cn.name}\n"
            + f"|名称jp={furni_data_jp.name}\n"
            + f"|名称en={furni_data_en.name}\n"
            + new_text[num2:]
        )

        # edit wiki
        if origin_text != new_text:
            # logger.info(new_text)
            wiki.edit(
                title=page_name,
                text=new_text,
                summary="update",
            )
            logger.info(f"Update: {page_name}.")
        else:
            logger.info(f"Same: {page_name}.")


@job
def run(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    skill_table: Annotated[dict[str, SkillDataBundle], table("skill_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
    building_data: Annotated[BuildingData, table("building_data")],
    character_table_jp: Annotated[
        dict[str, CharacterData], table("character_table", "JP")
    ],
    skill_table_jp: Annotated[dict[str, SkillDataBundle], table("skill_table", "JP")],
    charword_table_jp: Annotated[CharWordTable, table("charword_table", "JP")],
    building_data_jp: Annotated[BuildingData, table("building_data", "JP")],
    character_table_en: Annotated[
        dict[str, CharacterData], table("character_table", "US")
    ],
    skill_table_en: Annotated[dict[str, SkillDataBundle], table("skill_table", "US")],
    charword_table_en: Annotated[CharWordTable, table("charword_table", "US")],
    building_data_en: Annotated[BuildingData, table("building_data", "US")],
) -> None:
    # charword / building 三服的表留给暂未启用的语音、家具更新
    # update_charword_jp(
    #     wiki, character_table, charword_table, character_table_jp, charword_table_jp
    # )
    update_skill_and_name(
        wiki,
        character_table,
        skill_table,
        character_table_jp,
        skill_table_jp,
        character_table_en,
        skill_table_en,
    )
