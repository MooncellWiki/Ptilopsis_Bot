import os
import re

from utils.job import Job


def norm_text(t):
    result = t.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
    result = result.replace('{@nickname}', '{{DrName}}')
    result = result.replace('~~~', '<nowiki>~~~</nowiki>')
    return result.strip()


def charword_data_new(char_id, char_name, charword_table, char_words_jp=None, char_words_en=None, char_words_kr=None, char_words_tw=None, old_words=None, title='语音记录', mode='create'):
    content = '<noinclude>\n==' + title + '==\n</noinclude>{{#widget:VoiceTable}}{{VoiceTable|表格标题='
    content += f"{title}\n|语音key={char_id}\n|路径="
    char_lang = charword_table['voiceLangDict'][char_id]
    char_words = charword_table['charWords']

    # 语音路径
    default_type = charword_table['charDefaultTypeDict']
    lang_type = {'CN_MANDARIN': '中文', 'CN_TOPOLECT': '方言', 'JP': '日文', 'EN': '英文', 'KR': '韩文', 'LINKAGE': '联动', 'ITA': '意大利文'}
    lang_path = {'CN_MANDARIN': 'voice_cn', 'CN_TOPOLECT': 'voice_custom', 'JP': 'voice', 'EN': 'voice_en', 'KR': 'voice_kr',  'LINKAGE': 'voice', 'ITA': 'voice_custom'}
    path_list = ['']
    for lang in char_lang['dict']:
        char_lang_type = lang_type.get(lang, '未知')
        char_lang_path = lang_path.get(lang, 'voice_custom')
        if 'voicePath' in char_lang['dict'][lang]:
            p = char_lang['dict'][lang]['voicePath']
            if p.endswith('/'):
                p = p[:-1]
            char_lang_path = os.path.basename(p).lower()
        word_key_id = char_lang['dict'][lang]['wordkey'].lower().replace('#', '__').replace('/', '_')
        path = f"{char_lang_type}:{char_lang_path}/{word_key_id}"
        if char_id in default_type and lang == default_type[char_id]:
            path_list[0] = path
        else:
            path_list.append(path)
    # special case
    if char_id == 'char_311_mudrok':
        path_list.append('日文(摘下头盔时):voice/char_311_mudrok__1')
        path_list.append('中文(摘下头盔时):voice_cn/char_311_mudrok__1')
    if char_id == 'char_113_cqbw':
        path_list.append('日文(恍惚):voice/char_113_cqbw_epoque__7')
        path_list.append('中文(恍惚):voice_cn/char_113_cqbw_epoque__7')
    if char_id == 'char_472_pasngr':
        path_list.append('日文(今昔须臾之梦):voice/char_472_pasngr_epoque__17')
        path_list.append('中文(今昔须臾之梦):voice_cn/char_472_pasngr_epoque__17')
    if char_id == 'char_4067_lolxh':
        path_list = list(map(lambda x: x.replace('文:voice','文(猫形态):voice'), path_list))
        path_list.append('日文:voice/char_4067_lolxh__1')
        path_list.append('中文:voice_cn/char_4067_lolxh__1')
    content += ','.join(path_list)

    # 语音文本
    text_dict = {}
    official_flag = {'日文': False, '英文': False, '韩文': False, '中文(繁体)': False, '意大利文': False}
    other_lang_words = {
        '日文': char_words_jp,
        '英文': char_words_en,
        '韩文': char_words_kr,
        '中文(繁体)': char_words_tw,
        '意大利文': []
    }
    for word_key in char_lang['wordkeys']:
        word_lang = '中文'
        for k, v in char_lang['dict'].items():
            if v['wordkey'] == word_key and k == 'CN_TOPOLECT':
                word_lang = '方言'
            if v['wordkey'] == word_key and k == 'ITA':
                word_lang = '意大利文'
        if word_lang in ['意大利文']:
            continue 
        for text_id, text_data in sorted(filter(lambda x: x[1]['wordKey'] == word_key, char_words.items()),
                                         key=lambda x: x[1]['voiceIndex']):
            if text_data['voiceIndex'] not in text_dict:
                text_dict[text_data['voiceIndex']] = {
                    'text': '',
                    'title': '',
                    'condition': '',
                    'voiceId': ''
                }
                unlock_cond = ''
                if text_data['unlockType'] == 'DIRECT':
                    pass
                elif text_data['unlockType'] == 'FAVOR':
                    unlock_cond = '提升信赖至{}%以查看'.format(text_data['unlockParam'][0]['valueInt'])
                elif text_data['unlockType'] == 'AWAKE':
                    unlock_cond = '提升至精英阶段{}以查看'.format(text_data['unlockParam'][0]['valueInt'])
                else:
                    unlock_cond = text_data['lockDescription'].strip()
                    print('new voice unlock type for', text_data['charWordId'])
                text_dict[text_data['voiceIndex']]['title'] = text_data['voiceTitle'].strip()
                text_dict[text_data['voiceIndex']]['condition'] = unlock_cond
                text_dict[text_data['voiceIndex']]['voiceId'] = text_data['voiceId'].strip()
            text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{word_lang}|{norm_text(text_data['voiceText'])}}}}}"
            if word_lang in ['方言', '意大利文']:
                continue
            if mode == 'update':
                for other_lang, other_words in other_lang_words.items():
                    if text_id in other_words:
                        text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{other_lang}|{norm_text(other_words[text_id]['voiceText'])}}}}}"
                        official_flag[other_lang] = True
                    elif official_flag[other_lang] is True:
                        print('lack of official words for', text_id, f"({char_id} {char_name})")
                        text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{other_lang}|}}}}"
                    else:
                        result1 = re.search(re.compile(f"\|台词{text_data['voiceIndex']}=(.+?)\n"), old_words)
                        if result1:
                            result2 = re.search(re.compile(f"{{{{VoiceData/word\|{other_lang}\|(.*?)}}}}{{{{"), result1.group(1))
                            if result2 is None:
                                result2 = re.search(re.compile(f"{{{{VoiceData/word\|{other_lang}\|(.*?)}}}}$"), result1.group(1))
                            if result2:
                                text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{other_lang}|" + result2.group(1) + '}}'
            else:
                text_dict[text_data['voiceIndex']]['text'] += '{{VoiceData/word|日文|}}'
    # special case
    if char_id == 'char_113_cqbw' and mode == 'update':
        word_lang, word_key = '中文(恍惚)', 'char_113_cqbw_epoque#7'
        for text_id, text_data in sorted(filter(lambda x: x[1]['wordKey'] == word_key, char_words.items()),
                                         key=lambda x: x[1]['voiceIndex']):
            text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{word_lang}|{norm_text(text_data['voiceText'])}}}}}"
    if char_id == 'char_472_pasngr' and mode == 'update':
        word_lang, word_key = '中文(今昔须臾之梦)', 'char_472_pasngr_epoque#17'
        for text_id, text_data in sorted(filter(lambda x: x[1]['wordKey'] == word_key, char_words.items()),
                                         key=lambda x: x[1]['voiceIndex']):
            # text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{word_lang}|{norm_text(text_data['voiceText'])}}}}}"
            result1 = re.search(re.compile(f"\|台词{text_data['voiceIndex']}=(.+?)\n"), old_words)
            if result1:
                result2 = re.search(re.compile('{{VoiceData/word\|中文\(今昔须臾之梦\)\|(.*?)}}{{'), result1.group(1))
                if result2 is None:
                    result2 = re.search(re.compile('{{VoiceData/word\|中文\(今昔须臾之梦\)\|(.*?)}}$'), result1.group(1))
                if result2:
                    text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|中文(今昔须臾之梦)|" + result2.group(1) + '}}'
                result2 = re.search(re.compile('{{VoiceData/word\|日文\(今昔须臾之梦\)\|(.*?)}}{{'), result1.group(1))
                if result2 is None:
                    result2 = re.search(re.compile('{{VoiceData/word\|日文\(今昔须臾之梦\)\|(.*?)}}$'), result1.group(1))
                if result2:
                    text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|日文(今昔须臾之梦)|" + result2.group(1) + '}}'

    # 内容拼合
    if char_id == 'char_1001_amiya2':
        voice_file_name = '阿米娅'
    else:
        voice_file_name = char_name
    for idx, word_piece in text_dict.items():
        content += '\n\n|标题{id}={title}\n|台词{id}={text}\n|语音{id}={voice}'.format(
            id=idx,
            title=word_piece['title'],
            text=word_piece['text'],
            # voice=voice_file_name + ' ' + word_piece['title'] + '.wav'
            voice=word_piece['voiceId'] + '.wav'
        )
        if word_piece['condition'] != '':
            content += f"\n|条件{idx}={word_piece['condition']}"
    content += '\n}}<noinclude>[[分类:干员语音]]'
    official_flag['中文(繁体)'] = False  # 繁中暂不考虑加分类
    for lang in official_flag:
        if official_flag[lang] is True:
            content += f"[[分类:有官方{lang}文本的干员语音]]"
    content += '</noinclude>'

    return content


def charword_data(char_id, char_name, charword_table, char_words_jp=None, char_words_en=None, old_words=None, title='语音记录', mode='create'):
    char_words = charword_table['charWords']
    char_lang = charword_table['voiceLangDict'][char_id]
    content = '<noinclude>\n==' + title + '==\n</noinclude>{{#widget:VoiceTable}}{{VoiceTable|表格标题='
    content += f"{title}\n|语音key={char_id}\n|路径="
    path_list = ['']
    wordkeys_list = {k: [] for k in char_lang['wordkeys']}
    for lang in char_lang['dict']:
        lang_type = {'CN_MANDARIN': '中文', 'JP': '日文', 'CN_TOPOLECT': '方言', 'LINKAGE': '联动', 'EN': '英文', 'KR': '韩文'}.get(lang, '未知')
        path = {'CN_MANDARIN': 'voice_cn', 'JP': 'voice', 'EN': 'voice_en', 'KR': 'voice_kr', 'CN_TOPOLECT': 'voice_custom', 'LINKAGE': 'voice'}.get(lang, 'voice')
        if 'voicePath' in char_lang['dict'][lang]:
            p = char_lang['dict'][lang]['voicePath']
            if p.endswith('/'):
                p = p[:-1]
            path = os.path.basename(p).lower()
        word_key_id = char_lang['dict'][lang]['wordkey'].lower().replace('#', '__').replace('/', '_')
        lang_path = f"{lang_type}:{path}/{word_key_id}"
        if char_id in charword_table['charDefaultTypeDict'] and lang == charword_table['charDefaultTypeDict'][char_id]:
            path_list[0] = lang_path
        else:
            path_list.append(lang_path)
        if char_lang['dict'][lang]['wordkey'] in wordkeys_list:
            wordkeys_list[char_lang['dict'][lang]['wordkey']].append(lang)
        else:
            print('Unknown wordkey for character', char_id, char_name)
    if char_id == 'char_311_mudrok':
        path_list.append('日文(摘下头盔时):voice/char_311_mudrok__1')
    if char_id == 'char_113_cqbw':
        path_list.append('日文(恍惚):voice/char_113_cqbw_epoque__7')
        path_list.append('中文(恍惚):voice_cn/char_113_cqbw_epoque__7')
    content += ','.join(path_list)

    if mode == 'update':
        if char_id not in ['char_457_blitz', 'char_456_ash', 'char_458_rfrost', 'char_459_tachak']:
            char_words_2, lang_2 = char_words_jp['charWords'], '日文'
        else:
            char_words_2, lang_2 = char_words_en['charWords'], '英文'
    else:
        char_words_2, lang_2 = None, '日文'
    official_flag = True
    text_dict = {}
    for word_key in char_lang['wordkeys']:
        if 'CN_MANDARIN' in wordkeys_list[word_key] or 'JP' in wordkeys_list[word_key]:
            word_lang = '中文'
        elif 'CN_TOPOLECT' in wordkeys_list[word_key]:
            word_lang = '方言'
        elif 'LINKAGE' in wordkeys_list[word_key]:
            word_lang = '联动'
        else:
            print('Unknown language type', wordkeys_list[word_key] ,'for character', char_id, char_name)
            word_lang = '未知'
        for text_id, text_data in sorted(filter(lambda x: x[1]['wordKey'] == word_key, char_words.items()),
                                         key=lambda x: x[1]['voiceIndex']):
            if text_data['voiceIndex'] not in text_dict:
                text_dict[text_data['voiceIndex']] = {
                    'text': '',
                    'title': '',
                    'condition': ''
                }
                unlock_cond = ''
                if text_data['unlockType'] == 'DIRECT':
                    pass
                elif text_data['unlockType'] == 'FAVOR':
                    unlock_cond = '提升信赖至{}%以查看'.format(text_data['unlockParam'][0]['valueInt'])
                elif text_data['unlockType'] == 'AWAKE':
                    unlock_cond = '提升至精英阶段{}以查看'.format(text_data['unlockParam'][0]['valueInt'])
                else:
                    unlock_cond = text_data['lockDescription'].strip()
                    print('new voice unlock type for', text_data['charWordId'])
                text_dict[text_data['voiceIndex']]['title'] = text_data['voiceTitle'].strip()
                text_dict[text_data['voiceIndex']]['condition'] = unlock_cond
            text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{word_lang}|{norm_text(text_data['voiceText'])}}}}}"
            if word_lang == '中文' or len(char_lang['wordkeys']) == 1:
                if mode == 'update':
                    if text_id in char_words_2:
                        text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{lang_2}|" + norm_text(char_words_2[text_id]['voiceText']) + '}}'
                    else:
                        official_flag = False
                        result1 = re.search(re.compile(f"\|台词{text_data['voiceIndex']}=(.+?)\n"), old_words)
                        if result1:
                            result2 = re.search(re.compile(f"{{{{VoiceData/word\|{lang_2}\|(.*?)}}}}{{{{"), result1.group(1))
                            if result2 is None:
                                result2 = re.search(re.compile(f"{{{{VoiceData/word\|{lang_2}\|(.*?)}}}}$"), result1.group(1))
                            if result2:
                                text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{lang_2}|" + result2.group(1) + '}}'
                            else:
                                text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{lang_2}|}}}}"
                        else:
                            text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{lang_2}|}}}}"
                else:
                    official_flag = False
                    text_dict[text_data['voiceIndex']]['text'] += f"{{{{VoiceData/word|{lang_2}|}}}}"
    if char_id == 'char_1001_amiya2':
        voice_file_name = '阿米娅'
    else:
        voice_file_name = char_name
    for idx, word_piece in text_dict.items():
        content += '\n\n|标题{id}={title}\n|台词{id}={text}\n|语音{id}={voice}'.format(
            id=idx,
            title=word_piece['title'],
            text=word_piece['text'],
            voice=voice_file_name + ' ' + word_piece['title'].rstrip() + '.wav'
        )
        if word_piece['condition'] != '':
            content += f"\n|条件{idx}={word_piece['condition']}"
    content += '\n}}'
    if official_flag == True:
        content += f"<noinclude>[[分类:干员语音]][[分类:有官方{lang_2}文本的干员语音]]</noinclude>"
    else:
        content += f"<noinclude>[[分类:干员语音]]</noinclude>"
    return content


def create_charword(wiki, char_list, charword_table):
    charword_table['charDefaultTypeDict']['char_1001_amiya2'] = 'JP'
    for char_id, char_name in char_list:
        if char_id not in charword_table['voiceLangDict'] or char_id == 'char_311_mudrok#1':
            continue

        content = charword_data_new(char_id, char_name, charword_table, title='语音记录', mode='create')
        wiki.edit(
            title=char_name + '/语音记录',
            text=content,
            summary='init',
            bot=None,
            minor=True,
            createonly=True
        )
        # print(content)
        print('Created: {}.'.format(char_name + '/语音记录'))


def update_charword(wiki, char_list, charword_table, charword_table_jp, charword_table_en, charword_table_kr, charword_table_tw):
    charword_table['charDefaultTypeDict']['char_1001_amiya2'] = 'JP'
    for char_id, char_name in char_list:
        if char_id not in charword_table['voiceLangDict'] or char_id == 'char_311_mudrok#1':
            continue

        old = wiki.read(char_name + '/语音记录')
        content = charword_data_new(char_id, char_name, charword_table, char_words_jp=charword_table_jp['charWords'], char_words_en=charword_table_en['charWords'], char_words_kr=charword_table_kr['charWords'], char_words_tw=charword_table_tw['charWords'], old_words=old, title='语音记录', mode='update')
        if old != content:
            wiki.edit(
                title=char_name + '/语音记录',
                text=content,
                summary='update',
                bot=None,
                minor=True
            )
            # print(content)
            print('Updated: {}.'.format(char_name + '/语音记录'))
        else:
            print('Same: {}.'.format(char_name + '/语音记录'))


class Charword(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')

        charword_page_list = self.wiki.category('分类:干员语音')
        char_list = []
        for char_id in character_table:
            if character_table[char_id]['profession'] == 'TRAP' or character_table[char_id]['profession'] == 'TOKEN':
                continue
            if character_table[char_id]['name'] + '/语音记录' in charword_page_list:
                continue
            char_list.append((char_id, character_table[char_id]['name'].strip()))

        create_charword(self.wiki, char_list, charword_table)

    def update(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')
        charword_table_jp = self.getgd('excel/charword_table.json', 'JP')
        charword_table_en = self.getgd('excel/charword_table.json', 'US')
        charword_table_kr = self.getgd('excel/charword_table.json', 'KR')
        charword_table_tw = self.getgd('excel/charword_table.json', 'TW')

        char_list = []
        for char_id in character_table:
            if character_table[char_id]['profession'] == 'TRAP' or character_table[char_id]['profession'] == 'TOKEN':
                continue
            if char_id in ['char_512_aprot', 'char_511_asnipe', 'char_510_amedic', 'char_509_acast', 'char_508_aguard']:
                continue
            char_list.append((char_id, character_table[char_id]['name'].strip()))
        char_list.append(('char_1001_amiya2', '阿米娅(近卫)'))

        update_charword(self.wiki, char_list, charword_table, charword_table_jp, charword_table_en, charword_table_kr, charword_table_tw)
