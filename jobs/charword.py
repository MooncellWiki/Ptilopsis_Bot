import os
import re

from utils.job import Job


def norm_text(t):
    result = t.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
    result = result.replace('{@nickname}', '{{DrName}}')
    result = result.replace('~~~', '<nowiki>~~~</nowiki>')
    return result.strip()


def charword_data(char_id, char_name, charword_table, char_words_jp=None, char_words_en=None, old_words=None, title='语音记录', mode='create'):
    char_words = charword_table['charWords']
    char_lang = charword_table['voiceLangDict'][char_id]
    content = '<noinclude>\n==' + title + '==\n</noinclude>{{#widget:VoiceTable}}{{VoiceTable|表格标题='
    content += f"{title}\n|语音key={char_id}\n|路径="
    path_list = ['']
    wordkeys_list = {k: [] for k in char_lang['wordkeys']}
    for lang in char_lang['dict']:
        lang_type = {'CN_MANDARIN': '中文', 'JP': '日文', 'CN_TOPOLECT': '方言', 'LINKAGE': '联动'}.get(lang, '未知')
        path = {'CN_MANDARIN': 'voice_cn', 'JP': 'voice', 'CN_TOPOLECT': 'voice_custom', 'LINKAGE': 'voice'}.get(lang, 'voice')
        if 'voicePath' in char_lang['dict'][lang]:
            p = char_lang['dict'][lang]['voicePath']
            if p.endswith('/'):
                p = p[:-1]
            path = os.path.basename(p).lower()
        word_key_id = char_lang['dict'][lang]['wordkey'].lower().replace('#', '__').replace('/', '_')
        lang_path = f"{lang_type}:{path}/{word_key_id}"
        if lang == charword_table['charDefaultTypeDict'][char_id]:
            path_list[0] = lang_path
        else:
            path_list.append(lang_path)
        if char_lang['dict'][lang]['wordkey'] in wordkeys_list:
            wordkeys_list[char_lang['dict'][lang]['wordkey']].append(lang)
        else:
            print('Unknown wordkey for character', char_id, char_name)
    if char_id == 'char_311_mudrok':
        path_list.append('日文(摘下头盔时):voice/char_311_mudrok__1')
    content += ','.join(path_list)

    if mode == 'update':
        if char_id not in ['char_457_blitz', 'char_456_ash', 'char_458_rfrost', 'char_459_tachak']:
            char_words_2, lang_2 = char_words_jp['charWords'], '日文'
        else:
            char_words_2, lang_2 = char_words_en['charWords'], '英文'
    else:
        char_words_2, lang_2 = None, ''
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

        content = charword_data(char_id, char_name, charword_table, title='语音记录', mode='create')
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


def update_charword(wiki, char_list, charword_table, charword_table_jp, charword_table_en):
    charword_table['charDefaultTypeDict']['char_1001_amiya2'] = 'JP'
    for char_id, char_name in char_list:
        if char_id not in charword_table['voiceLangDict'] or char_id == 'char_311_mudrok#1':
            continue

        old = wiki.read(char_name + '/语音记录')
        content = charword_data(char_id, char_name, charword_table, char_words_jp=charword_table_jp, char_words_en=charword_table_en, old_words=old, title='语音记录', mode='update')
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
            char_list.append((char_id, character_table[char_id]['name']))

        create_charword(self.wiki, char_list, charword_table)

    def update(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')
        charword_table_jp = self.getgd('excel/charword_table.json', 'JP')
        charword_table_en = self.getgd('excel/charword_table.json', 'US')

        char_list = []
        for char_id in character_table:
            if character_table[char_id]['profession'] == 'TRAP' or character_table[char_id]['profession'] == 'TOKEN':
                continue
            char_list.append((char_id, character_table[char_id]['name']))
        char_list.append(('char_1001_amiya2', '阿米娅(近卫)'))

        update_charword(self.wiki, char_list, charword_table, charword_table_jp, charword_table_en)
