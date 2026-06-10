import os
import re

from ptilopsis.log import logger
from ptilopsis.utils.job import Job


class LangType:
    def __init__(self, charword_table):
        self.voice_type = {}
        self.word_type = {}
        self.voice_path = {}
        for k, v in charword_table["voiceLangTypeDict"].items():
            if v["name"].endswith("文"):
                self.voice_type[k] = v["name"][:-1] + "语"
            else:
                self.voice_type[k] = v["name"]
            self.voice_path[k] = f"voice_{v['groupType'].lower()}"
        # self.voice_type['CN_MANDARIN'] = '中文'
        # self.voice_type['CN_TOPOLECT'] = '方言'
        self.voice_path["CN_MANDARIN"] = "voice_cn"
        self.voice_path["JP"] = "voice"
        self.voice_path["LINKAGE"] = "voice"
        self.default_type = charword_table["charDefaultTypeDict"]

    def get_voice_type(self, lang_key):
        return self.voice_type.get(lang_key, "未知")

    def get_voice_path(self, lang_key):
        return self.voice_path.get(lang_key, "voice")

    def get_default_type(self, char_id):
        return self.default_type.get(char_id, "CN_MANDARIN")


def norm_text(t, lang=None):
    if lang != None and lang not in [
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


def charword_data(
    char_id,
    char_name,
    lt,
    skin_table,
    charword_table,
    char_words_jp=None,
    char_words_en=None,
    char_words_kr=None,
    char_words_tw=None,
    old_words="",
    title="语音记录",
    mode="create",
):
    content = (
        "<noinclude>\n=="
        + title
        + "==\n</noinclude>{{#widget:VoiceTable}}{{VoiceTable|表格标题="
    )
    content += f"{title}\n|语音key={char_id}\n|路径="
    char_words = charword_table["charWords"]

    # 语音路径
    path_list = [""]
    override_path_list = [""]
    fallback_flag = ""
    for lang_k, char_lang in filter(
        lambda x: x[1]["charId"] == char_id, charword_table["voiceLangDict"].items()
    ):
        default_type = lt.get_default_type(char_lang["charId"])
        suffix = ""
        if lang_k != char_lang["charId"]:
            suffix = f"({lang_k})"
            for skin_v in filter(
                lambda x: x["voiceId"] == lang_k, skin_table["charSkins"].values()
            ):
                suffix = f"({skin_v['displaySkin']['skinName']})"
                if skin_v["voiceType"] == "ILLUST":
                    fallback_flag = ":1"
                break
            if lang_k == "char_311_mudrok#1":
                suffix = "(摘下头盔时)"
                fallback_flag = ""
        if char_id == "char_4067_lolxh":
            suffix = "(猫形态)" if lang_k == "char_4067_lolxh" else ""
        if suffix in ["(char_1001_amiya2)", "(char_1037_amiya3)"]:
            continue
        for lang, lang_v in char_lang["dict"].items():
            char_voice_type = lt.get_voice_type(lang)
            char_voice_path = lt.get_voice_path(lang)
            if "voicePath" in lang_v and lang_v["voicePath"] is not None:
                p = lang_v["voicePath"]
                if p.endswith("/"):
                    p = p[:-1]
                char_voice_path = os.path.basename(p).lower()
            word_key_id = lang_v["wordkey"].lower().replace("#", "__").replace("/", "_")
            path = f"{char_voice_type}{suffix}:{char_voice_path}/{word_key_id}"
            if lang == default_type and lang_k == char_lang["charId"]:
                path_list[0] = path
            else:
                path_list.append(path)
            if fallback_flag != "":
                path = f"{char_voice_type}{suffix}{fallback_flag}:{char_voice_path}/{char_id}"
                if lang == default_type:
                    override_path_list[0] = path
                else:
                    override_path_list.append(path)
    content += ",".join(path_list)
    if override_path_list.__len__() > 1 or override_path_list[0] != "":
        content += "\n|覆盖路径=" + ",".join(override_path_list)

    # 语音文本
    text_dict = {}
    other_lang_words = {
        "日文": char_words_jp,
        "英文": char_words_en,
        "韩文": char_words_kr,
        "繁体中文": char_words_tw,
    }
    official_flag = {"日文": False, "英文": False, "韩文": False, "繁体中文": False}
    current_lang_set = set(re.findall(r"{{VoiceData/word\|(.+?)\|", old_words))
    for lang_k, char_lang in filter(
        lambda x: x[1]["charId"] == char_id, charword_table["voiceLangDict"].items()
    ):
        suffix1, suffix2 = "", ""
        if lang_k in [
            "char_4067_lolxh#1",
            "char_311_mudrok#1",
            "char_1001_amiya2",
            "char_1037_amiya3",
        ]:
            continue
        if lang_k != char_lang["charId"]:
            suffix2 = f"({lang_k})"
            for skin_v in filter(
                lambda x: x["voiceId"] == lang_k, skin_table["charSkins"].values()
            ):
                suffix2 = f"({skin_v['displaySkin']['skinName']})"
                break
        for word_key in char_lang["wordkeys"]:
            word_lang = "中文"
            suffix1_custom_flag = True
            for k, v in filter(
                lambda x: x[1]["wordkey"] == word_key, char_lang["dict"].items()
            ):
                if charword_table["voiceLangTypeDict"][k]["groupType"] != "CUSTOM":
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
            exists_flag = {
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
            for l in charword_table["voiceLangGroupTypeDict"]["CUSTOM"]["members"]:
                if l == "CN_TOPOLECT":
                    continue
                l_name = charword_table["voiceLangTypeDict"][l]["name"]
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
                filter(lambda x: x[1]["wordKey"] == word_key, char_words.items()),
                key=lambda x: x[1]["voiceIndex"],
            ):
                if text_data["voiceIndex"] not in text_dict:
                    text_dict[text_data["voiceIndex"]] = {
                        "text": "",
                        "title": "",
                        "condition": "",
                        "voiceId": "",
                        "placeType": "",
                    }
                # 先处理异客语音皮的厨放，全部优先wiki文本
                if char_id == "char_472_pasngr" and suffix2 == "(今昔须臾之梦)":
                    result1 = re.search(
                        re.compile(
                            rf"\|台词{text_data['voiceIndex']}=([\s\S]+?)\|语音"
                        ),
                        old_words,
                    )
                    exists_flag = dict(
                        list(
                            {
                                "中文": {"flag": True, "wiki_key": "中文(今昔须臾之梦)"}
                            }.items()
                        )
                        + list(exists_flag.items())
                    )
                    for other_lang in exists_flag:
                        if exists_flag[other_lang]["flag"] is True:
                            if result1:
                                other_lang_re = (
                                    exists_flag[other_lang]["wiki_key"]
                                    .replace(")", r"\)")
                                    .replace("(", r"\(")
                                )
                                result2 = re.search(
                                    re.compile(
                                        rf"{{{{VoiceData/word\|{other_lang_re}\|([\s\S]*?)}}}}{{{{"
                                    ),
                                    result1.group(1),
                                )
                                if result2 is None:
                                    result2 = re.search(
                                        re.compile(
                                            rf"{{{{VoiceData/word\|{other_lang_re}\|([\s\S]*?)}}}}$"
                                        ),
                                        result1.group(1),
                                    )
                                if result2:
                                    text_dict[text_data["voiceIndex"]]["text"] += (
                                        f"{{{{VoiceData/word|{other_lang}{suffix1}{suffix2}|"
                                        + result2.group(1).strip()
                                        + "}}"
                                    )
                                    continue
                        if (
                            other_lang in other_lang_words
                            and other_lang_words[other_lang] is not None
                            and text_id in other_lang_words[other_lang]
                        ):
                            text_dict[text_data["voiceIndex"]]["text"] += (
                                f"{{{{VoiceData/word|{other_lang}{suffix1}{suffix2}|{norm_text(other_lang_words[other_lang][text_id]['voiceText'], other_lang)}}}}}"
                            )
                    continue
                # 以上

                unlock_cond = ""
                if text_data["unlockType"] == "DIRECT":
                    pass
                elif text_data["unlockType"] == "FAVOR":
                    unlock_cond = "提升信赖至{}%以查看".format(
                        text_data["unlockParam"][0]["valueInt"]
                    )
                elif text_data["unlockType"] == "AWAKE":
                    unlock_cond = "提升至精英阶段{}以查看".format(
                        text_data["unlockParam"][0]["valueInt"]
                    )
                else:
                    unlock_cond = text_data["lockDescription"].strip()
                    logger.info("new voice unlock type for", text_data["charWordId"])
                text_dict[text_data["voiceIndex"]]["title"] = text_data[
                    "voiceTitle"
                ].strip()
                text_dict[text_data["voiceIndex"]]["condition"] = unlock_cond
                text_dict[text_data["voiceIndex"]]["voiceId"] = text_data[
                    "voiceId"
                ].strip()
                text_dict[text_data["voiceIndex"]]["placeType"] = text_data["placeType"]
                text_dict[text_data["voiceIndex"]]["text"] += (
                    f"{{{{VoiceData/word|{word_lang}{suffix1}{suffix2}|{norm_text(text_data['voiceText'], word_lang)}}}}}"
                )
                if mode == "update":
                    result1 = re.search(
                        re.compile(
                            rf"\|台词{text_data['voiceIndex']}=([\s\S]+?)\|语音"
                        ),
                        old_words,
                    )
                    for other_lang in exists_flag:
                        if suffix1 == "-方言" and other_lang != "繁体中文":
                            continue
                        if (
                            other_lang in other_lang_words
                            and other_lang_words[other_lang] is not None
                            and text_id in other_lang_words[other_lang]
                        ):
                            text_dict[text_data["voiceIndex"]]["text"] += (
                                f"{{{{VoiceData/word|{other_lang}{suffix1}{suffix2}|{norm_text(other_lang_words[other_lang][text_id]['voiceText'], other_lang)}}}}}"
                            )
                            official_flag[other_lang] = True
                            continue
                        if exists_flag[other_lang]["flag"] is True:
                            if result1:
                                other_lang_re = (
                                    exists_flag[other_lang]["wiki_key"]
                                    .replace(")", r"\)")
                                    .replace("(", r"\(")
                                )
                                result2 = re.search(
                                    re.compile(
                                        rf"{{{{VoiceData/word\|{other_lang_re}\|([\s\S]*?)}}}}{{{{"
                                    ),
                                    result1.group(1),
                                )
                                if result2 is None:
                                    result2 = re.search(
                                        re.compile(
                                            rf"{{{{VoiceData/word\|{other_lang_re}\|([\s\S]*?)}}}}$"
                                        ),
                                        result1.group(1),
                                    )
                                if result2:
                                    text_dict[text_data["voiceIndex"]]["text"] += (
                                        f"{{{{VoiceData/word|{other_lang}{suffix1}{suffix2}|"
                                        + result2.group(1).strip()
                                        + "}}"
                                    )
                            else:
                                text_dict[text_data["voiceIndex"]]["text"] += (
                                    f"{{{{VoiceData/word|{other_lang}{suffix1}{suffix2}|}}}}"
                                )
                else:
                    if suffix1 == "":
                        text_dict[text_data["voiceIndex"]]["text"] += (
                            f"{{{{VoiceData/word|日文{suffix2}|}}}}"
                        )

    # 内容拼合
    for idx, word_piece in text_dict.items():
        content += "\n\n|标题{id}={title}\n|台词{id}={text}\n|语音{id}={voice}\n|触发类型{id}={place_type}".format(
            id=idx,
            title=word_piece["title"],
            text=word_piece["text"],
            voice=word_piece["voiceId"] + ".wav",
            place_type=word_piece["placeType"],
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


def create_charword(wiki, char_list, skin_table, charword_table):
    charword_table["charDefaultTypeDict"]["char_1001_amiya2"] = "JP"
    charword_table["charDefaultTypeDict"]["char_1037_amiya3"] = "JP"
    lt = LangType(charword_table)
    for char_id, char_name in char_list:
        if (
            char_id not in charword_table["voiceLangDict"]
            or char_id == "char_311_mudrok#1"
        ):
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
        wiki.edit(
            title=char_name + "/语音记录",
            text=content,
            summary="init",
            bot=None,
            minor=True,
            createonly=True,
        )
        # logger.info(content)
        logger.info("Created: {}.".format(char_name + "/语音记录"))


def update_charword(
    wiki,
    char_list,
    skin_table,
    charword_table,
    charword_table_jp,
    charword_table_en,
    charword_table_kr,
    charword_table_tw,
):
    charword_table["charDefaultTypeDict"]["char_1001_amiya2"] = "JP"
    charword_table["charDefaultTypeDict"]["char_1037_amiya3"] = "JP"
    lt = LangType(charword_table)
    for char_id, char_name in char_list:
        if char_id not in charword_table["voiceLangDict"] or char_id in [
            "char_311_mudrok#1",
            "char_4087_ines",
        ]:
            continue

        old = wiki.read(char_name + "/语音记录")
        content = charword_data(
            char_id,
            char_name,
            lt,
            skin_table,
            charword_table,
            charword_table_jp["charWords"],
            charword_table_en["charWords"],
            charword_table_kr["charWords"],
            None,
            old_words=old,
            title="语音记录",
            mode="update",
        )
        if old != content:
            wiki.edit(
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


class Charword(Job):
    def _run(self):
        character_table = self.getgd("excel/character_table.json")
        charword_table = self.getgd("excel/charword_table.json")
        skin_table = self.getgd("excel/skin_table.json")

        charword_page_list = self.wiki.category("分类:干员语音")
        char_list = []
        for char_id in character_table:
            if (
                character_table[char_id]["profession"] == "TRAP"
                or character_table[char_id]["profession"] == "TOKEN"
            ):
                continue
            if character_table[char_id]["name"] + "/语音记录" in charword_page_list:
                continue
            char_list.append((char_id, character_table[char_id]["name"].strip()))

        create_charword(self.wiki, char_list, skin_table, charword_table)

    def update(self):
        character_table = self.getgd("excel/character_table.json")
        charword_table = self.getgd("excel/charword_table.json")
        charword_table_jp = self.getgd("excel/charword_table.json", "JP")
        charword_table_en = self.getgd("excel/charword_table.json", "US")
        charword_table_kr = self.getgd("excel/charword_table.json", "KR")
        # charword_table_tw = self.getgd('excel/charword_table.json', 'TW')
        skin_table = self.getgd("excel/skin_table.json")

        char_list = []
        for char_id in character_table:
            if (
                character_table[char_id]["profession"] == "TRAP"
                or character_table[char_id]["profession"] == "TOKEN"
            ):
                continue
            if char_id in [
                "char_512_aprot",
                "char_511_asnipe",
                "char_510_amedic",
                "char_509_acast",
                "char_508_aguard",
            ]:
                continue
            char_list.append((char_id, character_table[char_id]["name"].strip()))
        # char_list.append(('char_1001_amiya2', '阿米娅(近卫)'))
        # char_list.append(('char_1037_amiya3', '阿米娅(医疗)'))

        update_charword(
            self.wiki,
            char_list,
            skin_table,
            charword_table,
            charword_table_jp,
            charword_table_en,
            charword_table_kr,
            None,
        )
