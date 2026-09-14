import re
from typing import Annotated

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.charword_table import (
    CharWordData,
    CharWordTable,
    VoiceLangData,
)
from ptilopsis.jobs.params import category, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def norm_text(t: str) -> str:
    result = t.replace("Dr.{@nickname}", "{{DrName|前缀=Dr.}}")
    result = result.replace("{@nickname}", "{{DrName}}")
    result = result.replace("~~~", "<nowiki>~~~</nowiki>")
    return result.rstrip()


def concat_id(
    voice_data: CharWordData, char_name: str, flag_CN: bool, text_jp: str = ""
) -> str:
    idx = voice_data.voice_index
    title = (voice_data.voice_title or "").rstrip()
    text = (
        f"|标题{idx}={title}\n"
        f"|日文{idx}={norm_text(text_jp)}\n"
        f"|中文{idx}={norm_text(voice_data.voice_text or '')}\n"
        f"|语音{idx}={char_name} {title}.wav\n"
    )
    if flag_CN:
        text += f"|中文语音{idx}={char_name} {title} CN.wav\n"
    unlock_param = voice_data.unlock_param or []
    if voice_data.unlock_type == "DIRECT":
        pass
    elif voice_data.unlock_type == "FAVOR":
        # if voice_data['lockDescription'] != '提升信赖以查看更多信息':
        #     unlock_cond = voice_data['lockDescription'].rstrip()
        #     logger.info('new voice favor unlock description for',
        #                 voice_data['charWordId'])
        # else:
        unlock_cond = f"提升信赖至{unlock_param[0].value_int}%以查看"
        text += f"|条件{idx}={unlock_cond}\n"
    elif voice_data.unlock_type == "AWAKE":
        unlock_cond = f"提升至精英阶段{unlock_param[0].value_int}以查看"
        text += f"|条件{idx}={unlock_cond}\n"
    else:
        text += f"|条件{idx}={(voice_data.lock_description or '').rstrip()}\n"
        logger.info("new voice unlock type for", voice_data.char_word_id)
    return text


def get_charword_data(
    word_key: str,
    file_name: str,
    char_words: dict[str, CharWordData],
    flag_CN: bool,
    text_jp_dict: dict[str, str] | None = None,
    title: str = "语音记录",
) -> str:
    char_word = f"<noinclude>\n=={title}==\n"
    if flag_CN:
        char_word += "{{#Widget:VoiceLangSelector}}\n"
    char_word += (
        f"<!--{word_key}-->" + "\n</noinclude>{{#invoke:VoiceTable|table|表格标题="
    )
    char_word += f"{title}\n<noinclude>|可播放=1</noinclude>"
    char_word += f"\n|语音key={word_key}"
    for data in sorted(
        filter(lambda x: x.word_key == word_key, char_words.values()),
        key=lambda x: x.voice_index,
    ):
        if text_jp_dict is not None and str(data.voice_index) in text_jp_dict:
            char_word += "\n" + concat_id(
                data, file_name, flag_CN, text_jp=text_jp_dict[str(data.voice_index)]
            )
        else:
            char_word += "\n" + concat_id(data, file_name, flag_CN)
    char_word += "}}"
    return char_word


def word_key_list(char_id: str, char_words: dict[str, CharWordData]) -> list[str]:
    key_list: list[str] = []
    for word in filter(lambda x: x.char_id == char_id, char_words.values()):
        if word.word_key is not None and word.word_key not in key_list:
            key_list.append(word.word_key)
    return key_list


def _table_title(section: str) -> str:
    """页面片段里 ``|表格标题=`` 后的标题;找不到时与旧代码一样直接报错。"""

    matched = re.search(r"\|表格标题=(.*)", section)
    if matched is None:
        raise ValueError("语音记录片段里没有 |表格标题=")
    return matched.group(1).rstrip()


def _has_mandarin(voice_lang_dict: dict[str, VoiceLangData], word_key: str) -> bool:
    """这组语音是否配了普通话。"""
    return word_key in voice_lang_dict and "CN_MANDARIN" in (
        voice_lang_dict[word_key].dict_ or {}
    )


async def create_charword(
    wiki: Wiki,
    char_list: list[tuple[str, str]],
    char_words: dict[str, CharWordData],
    voice_lang_dict: dict[str, VoiceLangData],
) -> None:
    for char_id, char_name in char_list:
        key_list = word_key_list(char_id, char_words)
        if key_list == []:
            continue

        content = ""
        for k in key_list:
            flag_CN = _has_mandarin(voice_lang_dict, k)
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace("#", "-")
            content += get_charword_data(k, file_name, char_words, flag_CN) + "\n"
        content = content.rstrip()

        await wiki.edit(
            title=char_name + "/语音记录",
            text=content,
            summary="init",
            bot=None,
            minor=True,
        )
        # logger.info(content)
        logger.info("Created: {}.".format(char_name + "/语音记录"))


def _key_lists(
    char_list: list[tuple[str, str]], char_words: dict[str, CharWordData]
) -> list[tuple[str, str, list[str]]]:
    """每个干员的 wordkey 列表(含阿米娅升变的特殊处理),没有语音的干员略过。"""
    result: list[tuple[str, str, list[str]]] = []
    for char_id, char_name in char_list:
        key_list = word_key_list(char_id, char_words)
        # 处理阿米娅升变
        if char_id == "char_1001_amiya2":
            key_list.append("char_1001_amiya2")
        if char_id == "char_002_amiya":
            key_list.remove("char_1001_amiya2")
        if key_list == []:
            continue
        result.append((char_id, char_name, key_list))
    return result


async def update_charword(
    wiki: Wiki,
    char_list: list[tuple[str, str]],
    char_words: dict[str, CharWordData],
    voice_lang_dict: dict[str, VoiceLangData],
) -> None:
    targets = _key_lists(char_list, char_words)
    # 语音记录页面一次批量读完;页面不存在时和原来的 wiki.read 一样抛 KeyError
    pages = await wiki.read_many(f"{char_name}/语音记录" for _, char_name, _ in targets)
    for char_id, char_name, key_list in targets:
        origin_text = pages[char_name + "/语音记录"]
        origin_text += "=="
        new_text = ""
        for k in key_list:
            flag_CN = _has_mandarin(voice_lang_dict, k)
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace("#", "-")
            result = re.search(rf"<!--{k}-->([\s\S]*?)==", origin_text)
            if result:
                title = _table_title(result.group(1))
                result_jp = re.findall(r"\|日文([0-9]+?)=(.+?)\n", result.group(1))
                d = dict(result_jp)
                new_text += get_charword_data(
                    k, file_name, char_words, flag_CN, text_jp_dict=d, title=title
                )
            else:
                logger.info(char_name, "no wordkey found.")
                new_text += get_charword_data(k, file_name, char_words, flag_CN)
            new_text += "\n"

        origin_text = origin_text[:-2]
        flag = origin_text.find("<noinclude>[[分类")
        if flag != -1:
            new_text += origin_text[flag:]
        new_text = new_text.rstrip()

        if origin_text != new_text:
            await wiki.edit(
                title=char_name + "/语音记录", text=new_text, summary="update"
            )
            # logger.info(new_text)
            logger.info("Update: {}.".format(char_name + "/语音记录"))
        else:
            logger.info("Same: {}.".format(char_name + "/语音记录"))


async def update_charword_jp(
    wiki: Wiki,
    char_list: list[tuple[str, str]],
    char_words: dict[str, CharWordData],
    voice_lang_dict: dict[str, VoiceLangData],
    char_words_jp: dict[str, CharWordData],
    mode: str = "JP",
) -> None:
    targets = _key_lists(char_list, char_words)
    pages = await wiki.read_many(f"{char_name}/语音记录" for _, char_name, _ in targets)
    for char_id, char_name, key_list in targets:
        origin_text = pages[char_name + "/语音记录"]
        origin_text += "=="
        new_text = ""
        for k in key_list:
            flag_CN = _has_mandarin(voice_lang_dict, k)
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace("#", "-")
            text_jp_dict = {
                str(d.voice_index): d.voice_text or ""
                for d in filter(lambda x: x.word_key == k, char_words_jp.values())
            }
            result = re.search(rf"<!--{k}-->([\s\S]*?)==", origin_text)
            if result:
                title = _table_title(result.group(1))
                # 处理泥岩新语音
                result_jp = re.findall(r"\|日文([0-9]+?)=(.+?)\n", result.group(1))
                for k0, v0 in result_jp:
                    if k0 not in text_jp_dict:
                        text_jp_dict[k0] = v0
                # 处理end
                new_text += get_charword_data(
                    k,
                    file_name,
                    char_words,
                    flag_CN,
                    text_jp_dict=text_jp_dict,
                    title=title,
                )
            else:
                new_text += get_charword_data(
                    k, file_name, char_words, flag_CN, text_jp_dict=text_jp_dict
                )
            new_text += "\n"
        origin_text = origin_text[:-2]
        if mode == "US":
            new_text += "<noinclude>[[分类:有官方英文文本的干员语音]]</noinclude>"
        else:
            new_text += "<noinclude>[[分类:有官方日文文本的干员语音]]</noinclude>"

        if origin_text != new_text:
            await wiki.edit(
                title=char_name + "/语音记录",
                text=new_text,
                summary="update",
            )
            # logger.info(new_text)
            logger.info("Update: {}.".format(char_name + "/语音记录"))
        else:
            logger.info("Same: {}.".format(char_name + "/语音记录"))


def char_filter(char_tuple: tuple[str, CharacterData]) -> bool:
    if char_tuple[1].profession == "TRAP" or char_tuple[1].profession == "TOKEN":
        return False
    # if char_tuple[1]['name'] not in ['泥岩', '阿米娅', '阿米娅(近卫)']:
    #     return False
    return True


@job
async def run(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
    charword_page_list: Annotated[list[str], category("分类:干员语音")],
) -> None:
    voice_lang_dict = charword_table.voice_lang_dict or {}
    char_words = charword_table.char_words or {}

    char_list: list[tuple[str, str]] = []
    for char_id, char in character_table.items():
        if char.profession == "TRAP" or char.profession == "TOKEN":
            continue
        name = char.name or ""
        if name + "/语音记录" in charword_page_list:
            continue
        char_list.append((char_id, name))

    await create_charword(wiki, char_list, char_words, voice_lang_dict)


@job
async def update(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
) -> None:
    voice_lang_dict = charword_table.voice_lang_dict or {}
    char_words = charword_table.char_words or {}

    char_list = [
        (k, v.name or "") for k, v in filter(char_filter, character_table.items())
    ]
    char_list.append(("char_1001_amiya2", "阿米娅(近卫)"))
    await update_charword(wiki, char_list, char_words, voice_lang_dict)


@job
async def update_jp(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
    character_table_jp: Annotated[
        dict[str, CharacterData], table("character_table", "JP")
    ],
    charword_table_jp: Annotated[CharWordTable, table("charword_table", "JP")],
    charword_table_en: Annotated[CharWordTable, table("charword_table", "US")],
) -> None:
    voice_lang_dict = charword_table.voice_lang_dict or {}
    char_words = charword_table.char_words or {}

    en_list = [
        "char_457_blitz",
        "char_456_ash",
        "char_458_rfrost",
        "char_459_tachak",
    ]

    char_list: list[tuple[str, str]] = []
    char_list_en: list[tuple[str, str]] = []
    for char_id in character_table_jp:
        if char_id not in character_table:
            logger.info(f"Character {char_id} not find.")
            continue
        char = character_table[char_id]
        if char.profession == "TRAP" or char.profession == "TOKEN":
            continue
        if char_id in en_list:
            char_list_en.append((char_id, char.name or ""))
        else:
            char_list.append((char_id, char.name or ""))
    char_list.append(("char_1001_amiya2", "阿米娅(近卫)"))
    await update_charword_jp(
        wiki, char_list, char_words, voice_lang_dict, charword_table_jp.char_words or {}
    )
    await update_charword_jp(
        wiki,
        char_list_en,
        char_words,
        voice_lang_dict,
        charword_table_en.char_words or {},
        mode="US",
    )
