import os
import re
from typing import Annotated, Any

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.charword_table import CharWordData, CharWordTable
from ptilopsis.gamedata.skin_table import SkinTable
from ptilopsis.jobs.params import category, table
from ptilopsis.jobs.skin import display_skin
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


class LangType:
    """语音语种的展示名、文件路径与各干员的默认语种,由 charword_table 构造。"""

    def __init__(self, charword_table: CharWordTable) -> None:
        self.voice_type: dict[str, str] = {}
        self.word_type: dict[str, str] = {}
        self.voice_path: dict[str, str] = {}
        for k, v in (charword_table.voice_lang_type_dict or {}).items():
            name = v.name or ""
            if name.endswith("文"):
                self.voice_type[k] = name[:-1] + "语"
            else:
                self.voice_type[k] = name
            self.voice_path[k] = f"voice_{v.group_type.lower()}"
        # self.voice_type['CN_MANDARIN'] = '中文'
        # self.voice_type['CN_TOPOLECT'] = '方言'
        self.voice_path["CN_MANDARIN"] = "voice_cn"
        self.voice_path["JP"] = "voice"
        self.voice_path["LINKAGE"] = "voice"
        self.default_type = charword_table.char_default_type_dict or {}

    def get_voice_type(self, lang_key: str) -> str:
        return self.voice_type.get(lang_key, "未知")

    def get_voice_path(self, lang_key: str) -> str:
        return self.voice_path.get(lang_key, "voice")

    def get_default_type(self, char_id: str) -> str:
        return self.default_type.get(char_id, "CN_MANDARIN")


def norm_text(t: str, lang: str | None = None) -> str:
    if lang is not None and lang not in [
        "中文",
        "方言",
        "中文-普通话",
        "中文-方言",
        "繁体中文",
        "中文(繁体)",
    ]:
        add = f"|语言={lang}"
    else:
        add = ""
    result = t.replace("Dr.{@nickname}", f"{{{{DrName|前缀=Dr.{add}}}}}")
    result = result.replace("Dr. {@nickname}", f"{{{{DrName|前缀=Dr.{add}}}}}")
    result = result.replace("{@nickname}", f"{{{{DrName{add}}}}}")
    result = result.replace("~~~", "<nowiki>~~~</nowiki>")
    result = result.replace("[[", "<nowiki>[[").replace("]]", "]]</nowiki>")
    return result.strip()


def _word(lang: str, text: str) -> str:
    """一条 ``{{VoiceData/word|<语言>|<文本>}}``。"""
    return f"{{{{VoiceData/word|{lang}|{text}}}}}"


def _old_word(old_piece: str, wiki_key: str) -> str | None:
    """从旧页面的一条台词里取出 ``{{VoiceData/word|<wiki_key>|...}}`` 的文本。"""
    key_re = wiki_key.replace(")", r"\)").replace("(", r"\(")
    result = re.search(rf"{{{{VoiceData/word\|{key_re}\|([\s\S]*?)}}}}{{{{", old_piece)
    if result is None:
        result = re.search(rf"{{{{VoiceData/word\|{key_re}\|([\s\S]*?)}}}}$", old_piece)
    return result.group(1).strip() if result else None


def charword_data(
    char_id: str,
    char_name: str,
    lt: LangType,
    skin_table: SkinTable,
    charword_table: CharWordTable,
    char_words_jp: dict[str, CharWordData] | None = None,
    char_words_en: dict[str, CharWordData] | None = None,
    char_words_kr: dict[str, CharWordData] | None = None,
    char_words_tw: dict[str, CharWordData] | None = None,
    old_words: str = "",
    title: str = "语音记录",
    mode: str = "create",
) -> str:
    content = (
        "<noinclude>\n=="
        + title
        + "==\n</noinclude>{{#widget:VoiceTable}}{{VoiceTable|表格标题="
    )
    content += f"{title}\n|语音key={char_id}\n|路径="
    char_words = charword_table.char_words or {}
    voice_lang_dict = charword_table.voice_lang_dict or {}
    voice_lang_type_dict = charword_table.voice_lang_type_dict or {}
    char_skins = skin_table.char_skins or {}

    # 语音路径
    path_list = [""]
    override_path_list = [""]
    fallback_flag = ""
    for lang_k, char_lang in filter(
        lambda x: x[1].char_id == char_id, voice_lang_dict.items()
    ):
        default_type = lt.get_default_type(char_id)
        suffix = ""
        if lang_k != char_id:
            suffix = f"({lang_k})"
            for skin_v in filter(lambda x: x.voice_id == lang_k, char_skins.values()):
                suffix = f"({display_skin(skin_v).skin_name})"
                if skin_v.voice_type == "ILLUST":
                    fallback_flag = ":1"
                break
            if lang_k == "char_311_mudrok#1":
                suffix = "(摘下头盔时)"
                fallback_flag = ""
        if char_id == "char_4067_lolxh":
            suffix = "(猫形态)" if lang_k == "char_4067_lolxh" else ""
        if suffix in ["(char_1001_amiya2)", "(char_1037_amiya3)"]:
            continue
        for lang, lang_v in (char_lang.dict_ or {}).items():
            char_voice_type = lt.get_voice_type(lang)
            char_voice_path = lt.get_voice_path(lang)
            if lang_v.voice_path is not None:
                p = lang_v.voice_path
                if p.endswith("/"):
                    p = p[:-1]
                char_voice_path = os.path.basename(p).lower()
            word_key_id = (
                (lang_v.wordkey or "").lower().replace("#", "__").replace("/", "_")
            )
            path = f"{char_voice_type}{suffix}:{char_voice_path}/{word_key_id}"
            if lang == default_type and lang_k == char_id:
                path_list[0] = path
            else:
                path_list.append(path)
            if fallback_flag != "":
                path = (
                    f"{char_voice_type}{suffix}{fallback_flag}"
                    f":{char_voice_path}/{char_id}"
                )
                if lang == default_type:
                    override_path_list[0] = path
                else:
                    override_path_list.append(path)
    content += ",".join(path_list)
    if len(override_path_list) > 1 or override_path_list[0] != "":
        content += "\n|覆盖路径=" + ",".join(override_path_list)

    # 语音文本
    text_dict: dict[int, dict[str, str]] = {}
    other_lang_words = {
        "日文": char_words_jp,
        "英文": char_words_en,
        "韩文": char_words_kr,
        "繁体中文": char_words_tw,
    }
    official_flag = {"日文": False, "英文": False, "韩文": False, "繁体中文": False}
    current_lang_set = set(re.findall(r"{{VoiceData/word\|(.+?)\|", old_words))
    custom_members = (charword_table.voice_lang_group_type_dict or {})[
        "CUSTOM"
    ].members or []
    for lang_k, char_lang in filter(
        lambda x: x[1].char_id == char_id, voice_lang_dict.items()
    ):
        suffix1, suffix2 = "", ""
        if lang_k in [
            "char_4067_lolxh#1",
            "char_311_mudrok#1",
            "char_1001_amiya2",
            "char_1037_amiya3",
        ]:
            continue
        if lang_k != char_id:
            suffix2 = f"({lang_k})"
            for skin_v in filter(lambda x: x.voice_id == lang_k, char_skins.values()):
                suffix2 = f"({display_skin(skin_v).skin_name})"
                break
        lang_infos = char_lang.dict_ or {}
        for word_key in char_lang.wordkeys or []:
            word_lang = "中文"
            suffix1_custom_flag = True
            for k, v in filter(lambda x: x[1].wordkey == word_key, lang_infos.items()):
                if voice_lang_type_dict[k].group_type != "CUSTOM":
                    suffix1_custom_flag = False
                    break
                suffix1 = {
                    "CN_TOPOLECT": "-方言",
                    "ITA": "-意大利语版",
                    "GER": "-德语版",
                    "RUS": "-俄语版",
                }.get(k, k)
            if not suffix1_custom_flag:
                suffix1 = ""
            if suffix1 in ["-意大利语版"]:
                continue
            exists_flag: dict[str, dict[str, Any]] = {
                "日文": {"flag": False, "wiki_key": ""},
                "英文": {"flag": False, "wiki_key": ""},
                "韩文": {"flag": False, "wiki_key": ""},
                "繁体中文": {"flag": False, "wiki_key": ""},
            }
            for i in ["日文", "日语"]:
                if f"{i}{suffix1}{suffix2}" in current_lang_set:
                    exists_flag["日文"]["flag"] = True
                    exists_flag["日文"]["wiki_key"] = f"{i}{suffix1}{suffix2}"
            for i in ["英文", "英语"]:
                if f"{i}{suffix1}{suffix2}" in current_lang_set:
                    exists_flag["英文"]["flag"] = True
                    exists_flag["英文"]["wiki_key"] = f"{i}{suffix1}{suffix2}"
            for i in ["韩文", "韩语"]:
                if f"{i}{suffix1}{suffix2}" in current_lang_set:
                    exists_flag["韩文"]["flag"] = True
                    exists_flag["韩文"]["wiki_key"] = f"{i}{suffix1}{suffix2}"
            for i in ["繁体中文", "中文(繁体)"]:
                if f"{i}{suffix1}{suffix2}" in current_lang_set:
                    exists_flag["繁体中文"]["flag"] = True
                    exists_flag["繁体中文"]["wiki_key"] = f"{i}{suffix1}{suffix2}"
            for lang_id in custom_members:
                if lang_id == "CN_TOPOLECT":
                    continue
                l_name = voice_lang_type_dict[lang_id].name or ""
                if l_name.endswith("语") or l_name.endswith("文"):
                    potential_l_key = [l_name[:-1] + "文", l_name[:-1] + "语"]
                else:
                    potential_l_key = [l_name]
                for i in potential_l_key:
                    if f"{i}{suffix1}{suffix2}" in current_lang_set:
                        if l_name[:-1] + "文" not in exists_flag:
                            exists_flag[l_name[:-1] + "文"] = {
                                "flag": True,
                                "wiki_key": "",
                            }
                        exists_flag[l_name[:-1] + "文"]["flag"] = True
                        exists_flag[l_name[:-1] + "文"]["wiki_key"] = (
                            f"{i}{suffix1}{suffix2}"
                        )
            for text_id, text_data in sorted(
                filter(lambda x: x[1].word_key == word_key, char_words.items()),
                key=lambda x: x[1].voice_index,
            ):
                idx = text_data.voice_index
                if idx not in text_dict:
                    text_dict[idx] = {
                        "text": "",
                        "title": "",
                        "condition": "",
                        "voiceId": "",
                        "placeType": "",
                    }
                # 先处理异客语音皮的厨放，全部优先wiki文本
                if char_id == "char_472_pasngr" and suffix2 == "(今昔须臾之梦)":
                    result1 = re.search(rf"\|台词{idx}=([\s\S]+?)\|语音", old_words)
                    exists_flag = {
                        "中文": {"flag": True, "wiki_key": "中文(今昔须臾之梦)"},
                        **exists_flag,
                    }
                    for other_lang in exists_flag:
                        lang_key = f"{other_lang}{suffix1}{suffix2}"
                        if exists_flag[other_lang]["flag"] is True and result1:
                            old_word = _old_word(
                                result1.group(1), exists_flag[other_lang]["wiki_key"]
                            )
                            if old_word is not None:
                                text_dict[idx]["text"] += _word(lang_key, old_word)
                                continue
                        other_words = other_lang_words.get(other_lang)
                        if other_words is not None and text_id in other_words:
                            text_dict[idx]["text"] += _word(
                                lang_key,
                                norm_text(
                                    other_words[text_id].voice_text or "", other_lang
                                ),
                            )
                    continue
                # 以上

                unlock_cond = ""
                unlock_param = text_data.unlock_param or []
                if text_data.unlock_type == "DIRECT":
                    pass
                elif text_data.unlock_type == "FAVOR":
                    unlock_cond = f"提升信赖至{unlock_param[0].value_int}%以查看"
                elif text_data.unlock_type == "AWAKE":
                    unlock_cond = f"提升至精英阶段{unlock_param[0].value_int}以查看"
                else:
                    unlock_cond = (text_data.lock_description or "").strip()
                    logger.info("new voice unlock type for", text_data.char_word_id)
                text_dict[idx]["title"] = (text_data.voice_title or "").strip()
                text_dict[idx]["condition"] = unlock_cond
                text_dict[idx]["voiceId"] = (text_data.voice_id or "").strip()
                text_dict[idx]["placeType"] = text_data.place_type
                text_dict[idx]["text"] += _word(
                    f"{word_lang}{suffix1}{suffix2}",
                    norm_text(text_data.voice_text or "", word_lang),
                )
                if mode == "update":
                    result1 = re.search(rf"\|台词{idx}=([\s\S]+?)\|语音", old_words)
                    for other_lang in exists_flag:
                        if suffix1 == "-方言" and other_lang != "繁体中文":
                            continue
                        lang_key = f"{other_lang}{suffix1}{suffix2}"
                        other_words = other_lang_words.get(other_lang)
                        if other_words is not None and text_id in other_words:
                            text_dict[idx]["text"] += _word(
                                lang_key,
                                norm_text(
                                    other_words[text_id].voice_text or "", other_lang
                                ),
                            )
                            official_flag[other_lang] = True
                            continue
                        if exists_flag[other_lang]["flag"] is True:
                            if result1:
                                old_word = _old_word(
                                    result1.group(1),
                                    exists_flag[other_lang]["wiki_key"],
                                )
                                if old_word is not None:
                                    text_dict[idx]["text"] += _word(lang_key, old_word)
                            else:
                                text_dict[idx]["text"] += _word(lang_key, "")
                else:
                    if suffix1 == "":
                        text_dict[idx]["text"] += _word(f"日文{suffix2}", "")

    # 内容拼合
    for idx, word_piece in text_dict.items():
        content += (
            f"\n\n|标题{idx}={word_piece['title']}"
            f"\n|台词{idx}={word_piece['text']}"
            f"\n|语音{idx}={word_piece['voiceId']}.wav"
            f"\n|触发类型{idx}={word_piece['placeType']}"
        )
        if word_piece["condition"] != "":
            content += f"\n|条件{idx}={word_piece['condition']}"
    content += "\n}}<noinclude>[[分类:干员语音]]"
    official_flag["繁体中文"] = False  # 繁中暂不考虑加分类
    for lang in official_flag:
        if official_flag[lang] is True:
            content += f"[[分类:有官方{lang}文本的干员语音]]"
    content += "</noinclude>"

    return content


def _set_amiya_default_type(charword_table: CharWordTable) -> None:
    """升变阿米娅在 charDefaultTypeDict 里没有记录,按日语处理。"""
    if charword_table.char_default_type_dict is None:
        charword_table.char_default_type_dict = {}
    charword_table.char_default_type_dict["char_1001_amiya2"] = "JP"
    charword_table.char_default_type_dict["char_1037_amiya3"] = "JP"


async def create_charword(
    wiki: Wiki,
    char_list: list[tuple[str, str]],
    skin_table: SkinTable,
    charword_table: CharWordTable,
) -> None:
    _set_amiya_default_type(charword_table)
    lt = LangType(charword_table)
    voice_lang_dict = charword_table.voice_lang_dict or {}
    for char_id, char_name in char_list:
        if char_id not in voice_lang_dict or char_id == "char_311_mudrok#1":
            continue

        content = charword_data(
            char_id,
            char_name,
            lt,
            skin_table,
            charword_table,
            title="语音记录",
            mode="create",
        )
        await wiki.edit(
            title=char_name + "/语音记录",
            text=content,
            summary="init",
            bot=None,
            minor=True,
            createonly=True,
        )
        # logger.info(content)
        logger.info("Created: {}.".format(char_name + "/语音记录"))


def _updatable(
    char_list: list[tuple[str, str]], voice_lang_dict: dict[str, Any]
) -> list[tuple[str, str]]:
    """有语音配置、且不在例外名单里的干员。"""
    return [
        (char_id, char_name)
        for char_id, char_name in char_list
        if char_id in voice_lang_dict
        and char_id not in ["char_311_mudrok#1", "char_4087_ines"]
    ]


async def update_charword(
    wiki: Wiki,
    char_list: list[tuple[str, str]],
    skin_table: SkinTable,
    charword_table: CharWordTable,
    charword_table_jp: CharWordTable | None,
    charword_table_en: CharWordTable | None,
    charword_table_kr: CharWordTable | None,
    charword_table_tw: CharWordTable | None,
) -> None:
    _set_amiya_default_type(charword_table)
    lt = LangType(charword_table)
    voice_lang_dict = charword_table.voice_lang_dict or {}
    targets = _updatable(char_list, voice_lang_dict)
    # 几百个语音记录页面一次批量读完;页面不存在时和原来的 wiki.read 一样抛 KeyError
    old_pages = await wiki.read_many(
        f"{char_name}/语音记录" for _, char_name in targets
    )
    for char_id, char_name in targets:
        old = old_pages[char_name + "/语音记录"]
        # 海外服文本暂不写入,其它语言的台词沿用页面上已有的
        content = charword_data(
            char_id,
            char_name,
            lt,
            skin_table,
            charword_table,
            None,
            None,
            None,
            None,
            old_words=old,
            title="语音记录",
            mode="update",
        )
        if old != content:
            await wiki.edit(
                title=char_name + "/语音记录",
                text=content,
                summary="update",
                bot=None,
                minor=True,
            )
            # logger.info(content)
            logger.info("Updated: {}.".format(char_name + "/语音记录"))
        else:
            logger.info("Same: {}.".format(char_name + "/语音记录"))


@job
async def run(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
    skin_table: Annotated[SkinTable, table("skin_table")],
    charword_page_list: Annotated[list[str], category("分类:干员语音")],
) -> None:
    char_list: list[tuple[str, str]] = []
    for char_id, char in character_table.items():
        if char.profession == "TRAP" or char.profession == "TOKEN":
            continue
        name = char.name or ""
        if name + "/语音记录" in charword_page_list:
            continue
        char_list.append((char_id, name.strip()))

    await create_charword(wiki, char_list, skin_table, charword_table)


@job
async def update(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    charword_table: Annotated[CharWordTable, table("charword_table")],
    charword_table_jp: Annotated[CharWordTable, table("charword_table", "JP")],
    charword_table_en: Annotated[CharWordTable, table("charword_table", "US")],
    charword_table_kr: Annotated[CharWordTable, table("charword_table", "KR")],
    # charword_table_tw: Annotated[CharWordTable, table("charword_table", "TW")],
    skin_table: Annotated[SkinTable, table("skin_table")],
) -> None:
    char_list: list[tuple[str, str]] = []
    for char_id, char in character_table.items():
        if char.profession == "TRAP" or char.profession == "TOKEN":
            continue
        if char_id in [
            "char_512_aprot",
            "char_511_asnipe",
            "char_510_amedic",
            "char_509_acast",
            "char_508_aguard",
        ]:
            continue
        char_list.append((char_id, (char.name or "").strip()))
    # char_list.append(('char_1001_amiya2', '阿米娅(近卫)'))
    # char_list.append(('char_1037_amiya3', '阿米娅(医疗)'))

    await update_charword(
        wiki,
        char_list,
        skin_table,
        charword_table,
        charword_table_jp,
        charword_table_en,
        charword_table_kr,
        None,
    )
