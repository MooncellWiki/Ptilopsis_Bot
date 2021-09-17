import re

from utils.job import Job


def norm_text(t):
    result = t.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
    result = result.replace('{@nickname}', '{{DrName}}')
    result = result.replace('~~~', '<nowiki>~~~</nowiki>')
    return result.rstrip()


def concat_id(voice_data, char_name, text_jp=''):
    text = '|标题{id}={title}\n|日文{id}={text_jp}\n|中文{id}={text_cn}\n|语音{id}={voice}\n'.format(
        id = voice_data['voiceIndex'],
        title = voice_data['voiceTitle'].rstrip(),
        text_jp = norm_text(text_jp),
        text_cn = norm_text(voice_data['voiceText']),
        voice = char_name + ' ' + voice_data['voiceTitle'].rstrip() + '.wav'
    )
    if char_name == '白金':
        text = '|标题{id}={title}\n|日文{id}={text_jp}\n|中文{id}={text_cn}\n|语音{id}={voice}\n'.format(
            id = voice_data['voiceIndex'],
            title = voice_data['voiceTitle'].rstrip(),
            text_jp = norm_text(text_jp),
            text_cn = norm_text(voice_data['voiceText']),
            voice = ''
        )
    if voice_data['unlockType'] == 'DIRECT':
        pass
    elif voice_data['unlockType'] == 'FAVOR':
        # if voice_data['lockDescription'] != '提升信赖以查看更多信息':
        #     unlock_cond = voice_data['lockDescription'].rstrip()
        #     print('new voice favor unlock description for', voice_data['charWordId'])
        # else:
        unlock_cond = '提升信赖至{}%以查看'.format(voice_data['unlockParam'][0]['valueInt'])
        text += '|条件{id}={unlock_cond}\n'.format(
            id = voice_data['voiceIndex'],
            unlock_cond = unlock_cond
        )
    elif voice_data['unlockType'] == 'AWAKE':
        unlock_cond = '提升至精英阶段{}以查看'.format(voice_data['unlockParam'][0]['valueInt'])
        text += '|条件{id}={unlock_cond}\n'.format(
            id = voice_data['voiceIndex'],
            unlock_cond = unlock_cond
        )
    else:
        text += '|条件{id}={unlock_cond}\n'.format(
            id = voice_data['voiceIndex'],
            unlock_cond = voice_data['lockDescription'].rstrip()
        )
        print('new voice unlock type for', voice_data['charWordId'])
    return text


def get_charword_data(word_key, file_name, charword_table, text_jp_dict=None, title='语音记录'):
    char_word = '<noinclude>\n=={}==\n<!--{}-->\n'.format(title, word_key) + \
                '</noinclude>{{#invoke:VoiceTable|table|表格标题=' + title + \
                '\n<noinclude>|可播放=1</noinclude>'
    for data in sorted(filter(lambda x: x['wordKey'] == word_key, charword_table.values()),
            key = lambda x: x['voiceIndex']):
        if text_jp_dict is not None and str(data['voiceIndex']) in text_jp_dict:
            char_word += '\n' + concat_id(data, file_name, text_jp = text_jp_dict[str(data['voiceIndex'])])
        else:
            char_word += '\n' + concat_id(data, file_name)
    char_word += '}}'
    return char_word


def word_key_list(char_id, charword_table):
    key_list = []
    for key in filter(lambda x: x['charId'] == char_id, charword_table.values()):
        if key['wordKey'] not in key_list:
            key_list.append(key['wordKey'])
    return key_list


def create_charword(wiki, char_list, charword_table):
    for char_id, char_name in char_list:
        key_list = word_key_list(char_id, charword_table)
        if key_list == []:
            continue

        content = ''
        for k in key_list:
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace('#', '-')
            content += get_charword_data(k, file_name, charword_table) + '\n'
        content = content.rstrip()

        wiki.edit(
            title = char_name + '/语音记录',
            text = content,
            summary = 'init',
            bot = None,
            minor = True
        )
        # print(content)
        print('Created: {}.'.format(char_name + '/语音记录'))


def update_charword(wiki, char_list, charword_table):
    for char_id, char_name in char_list:
        key_list = word_key_list(char_id, charword_table)
        # 处理阿米娅升变
        if char_id == 'char_1001_amiya2':
            key_list.append('char_1001_amiya2')
        if char_id == 'char_002_amiya':
            key_list.remove('char_1001_amiya2')
        if key_list == []:
            continue

        origin_text = wiki.read(char_name + '/语音记录')
        origin_text += '=='
        new_text = ''
        for k in key_list:
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace('#', '-')
            result = re.search(r'<!--{}-->([\s\S]*?)=='.format(k), origin_text)
            if result:
                title = re.search(r'\|表格标题=(.*)', result.group(1)).group(1).rstrip()
                result_jp = re.findall(r'\|日文([0-9]+?)=(.+?)\n', result.group(1))
                d = {k: v for k, v in result_jp}
                new_text += get_charword_data(k, file_name, charword_table, text_jp_dict = d, title = title)
            else:
                print(char_name, 'no wordkey found.')
                new_text += get_charword_data(k, file_name, charword_table)
            new_text += '\n'

        origin_text = origin_text[:-2]
        flag = origin_text.find('<noinclude>[[分类')
        if flag != -1:
            new_text += origin_text[flag:]
        new_text = new_text.rstrip()

        if origin_text != new_text:
            wiki.edit(
                title = char_name + '/语音记录',
                text = new_text,
                summary = 'update'
            )
            # print(new_text)
            print('Update: {}.'.format(char_name + '/语音记录'))
        else:
            print('Same: {}.'.format(char_name + '/语音记录'))


def update_charword_jp(wiki, char_list, charword_table, charword_table_jp, mode='JP'):
    for char_id, char_name in char_list:
        key_list = word_key_list(char_id, charword_table)
        # 处理阿米娅升变
        if char_id == 'char_1001_amiya2':
            key_list.append('char_1001_amiya2')
        if char_id == 'char_002_amiya':
            key_list.remove('char_1001_amiya2')
        if key_list == []:
            continue

        origin_text = wiki.read(char_name + '/语音记录')
        origin_text += '=='
        new_text = ''
        for k in key_list:
            file_name = char_name
            if k != char_id:
                file_name = k.replace(char_id, char_name).replace('#', '-')
            result = re.search(r'<!--{}-->([\s\S]*?)=='.format(k), origin_text)
            if result:
                title = re.search(r'\|表格标题=(.*)', result.group(1)).group(1).rstrip()
                text_jp_dict = {str(d['voiceIndex']): d['voiceText'] for d in
                    filter(lambda x: x['wordKey'] == k, charword_table_jp.values())}
                # 处理泥岩新语音
                result_jp = re.findall(r'\|日文([0-9]+?)=(.+?)\n', result.group(1))
                for k0, v0 in result_jp:
                    if k0 not in text_jp_dict:
                        text_jp_dict[k0] = v0
                # 处理end
                new_text += get_charword_data(k, file_name, charword_table, text_jp_dict = text_jp_dict, title = title)
            else:
                text_jp_dict = {str(d['voiceIndex']): d['voiceText'] for d in
                    filter(lambda x: x['wordKey'] == k, charword_table_jp.values())}
                new_text += get_charword_data(k, file_name, charword_table, text_jp_dict = text_jp_dict)
            new_text += '\n'
        origin_text = origin_text[:-2]
        if mode == 'US':
            new_text += '<noinclude>[[分类:有官方英文文本的干员语音]]</noinclude>'
        else:
            new_text += '<noinclude>[[分类:有官方日文文本的干员语音]]</noinclude>'

        if origin_text != new_text:
            wiki.edit(
                title = char_name + '/语音记录',
                text = new_text,
                summary = 'update',
            )
            # print(new_text)
            print('Update: {}.'.format(char_name + '/语音记录'))
        else:
            print('Same: {}.'.format(char_name + '/语音记录'))


def char_filter(char_tuple):
    if char_tuple[1]['profession'] == 'TRAP' or char_tuple[1]['profession'] == 'TOKEN':
        return False
    # if char_tuple[1]['name'] not in ['泥岩', '阿米娅', '阿米娅(近卫)']:
    #     return False
    return True


class Charword(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')
        charword_table = charword_table['charWords']

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
        charword_table = charword_table['charWords']

        char_list = [(k, v['name']) for k, v in filter(char_filter, character_table.items())]
        char_list.append(('char_1001_amiya2', '阿米娅(近卫)'))
        update_charword(self.wiki, char_list, charword_table)

    def update_jp(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')
        charword_table = charword_table['charWords']

        character_table_jp = self.getgd('excel/character_table.json', 'JP')
        charword_table_jp = self.getgd('excel/charword_table.json', 'JP')

        en_list = ['char_457_blitz', 'char_456_ash', 'char_458_rfrost', 'char_459_tachak']
        charword_table_en = self.getgd('excel/charword_table.json', 'US')

        char_list, char_list_en = [], []
        for char_id in character_table_jp:
            if char_id not in character_table:
                print('Character {} not find.'.format(char_id))
                continue
            if character_table[char_id]['profession'] == 'TRAP' or character_table[char_id]['profession'] == 'TOKEN':
                continue
            if char_id in en_list:
                char_list_en.append((char_id, character_table[char_id]['name']))
            else:
                char_list.append((char_id, character_table[char_id]['name']))
        update_charword_jp(self.wiki, char_list, charword_table, charword_table_jp)
        update_charword_jp(self.wiki, char_list_en, charword_table, charword_table_en, mode='US')
