import re

from utils.job import Job


def get_charword_data(char_id, char_name, charword_table):
    char_word = '''<noinclude>
==语音记录==
</noinclude>{{#invoke:VoiceTable|table|表格标题=语音记录
<noinclude>|可播放=1</noinclude>'''
    for charword_id in charword_table:
        if char_id in charword_id:
            char_word += '\n'
            if charword_table[charword_id]['unlockType'] == 'DIRECT':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}=\n|中文{id}={text_cn}\n|语音{id}={voice}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav'
                )
            elif charword_table[charword_id]['unlockType'] == 'AWAKE':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}=\n|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav',
                    unlock_condition = charword_table[charword_id]['lockDescription'].replace('以查看更多信息', '以查看')
                )
            elif charword_table[charword_id]['unlockType'] == 'FAVOR':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}=\n|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav',
                    unlock_condition = replace_story_condition(charword_table[charword_id]['lockDescription'],
                        charword_table[charword_id]['unlockParam'][0]['valueInt']).replace('以查看更多信息', '以查看')
                )
    char_word += '}}'
    return char_word


def update_charword_data(char_id, char_name, origin_text, charword_table):
    char_word = '''<noinclude>
==语音记录==
</noinclude>{{#invoke:VoiceTable|table|表格标题=语音记录
<noinclude>|可播放=1</noinclude>'''
    for charword_id in charword_table:
        if char_id in charword_id:
            char_word += '\n'
            text_id = charword_table[charword_id]['voiceIndex']
            text_jp = '|日文{id}=\n'.format(id = text_id)
            num1 = origin_text.find('|日文{id}='.format(id = text_id))
            if num1 != -1:
                num2 = origin_text.find('|中文{id}='.format(id = text_id))
                text_jp = origin_text[num1:num2]

            if charword_table[charword_id]['unlockType'] == 'DIRECT':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n{text_jp}|中文{id}={text_cn}\n|语音{id}={voice}\n'.format(
                    id = text_id,
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp,
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav'
                )
            elif charword_table[charword_id]['unlockType'] == 'AWAKE':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n{text_jp}|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = text_id,
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp,
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav',
                    unlock_condition = charword_table[charword_id]['lockDescription'].replace('以查看更多信息', '以查看')
                )
            elif charword_table[charword_id]['unlockType'] == 'FAVOR':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n{text_jp}|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = text_id,
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp,
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav',
                    unlock_condition = replace_story_condition(charword_table[charword_id]['lockDescription'],
                        charword_table[charword_id]['unlockParam'][0]['valueInt']).replace('以查看更多信息', '以查看')
                )
    char_word += '}}'
    return char_word


def replace_story_condition(text, num):
    p1 = r"(.*)信赖(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + '信赖至' + str(num) + '%' + result.group(2)
    return text


def create_charword(wiki, character_table, charword_table):
    charword_list = wiki.category('分类:干员语音')

    for char_id in character_table:
        char_detail = character_table[char_id]
        if (char_detail['name'] + '/语音记录') in charword_list or char_detail['profession'] == 'TRAP' or char_detail[
            'profession'] == 'TOKEN':
            # if char_detail['name'] != '苇草' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        charword_data = get_charword_data(char_id, char_detail['name'], charword_table)

        wiki.edit(
            title = char_detail['name'] + '/语音记录',
            text = charword_data,
            summary = 'init'
        )
        # print(charword_data)
        print('Created: {}.'.format(char_detail['name'] + '/语音记录'))


def update_charword(wiki, character_table, charword_table):
    for char in character_table:
        char_detail = character_table[char]
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            # if char_detail['name'] != '安洁莉娜' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        origin_text = wiki.read(char_detail['name'] + '/语音记录')

        new_text = update_charword_data(char, char_detail['name'], origin_text, charword_table)
        num1 = origin_text.find('\n<noinclude>[[分类')
        if num1 != -1:
            new_text += origin_text[num1:]

        if origin_text != new_text:
            wiki.edit(
                title = char_detail['name'] + '/语音记录',
                text = new_text,
                summary = 'update'
            )
            # print(new_text)
            print('Update: {}.'.format(char_detail['name'] + '/语音记录'))
        else:
            print('Same: {}.'.format(char_detail['name'] + '/语音记录'))


class Charword(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')

        create_charword(self.wiki, character_table, charword_table)

    def _run_update(self):
        character_table = self.getgd('excel/character_table.json')
        charword_table = self.getgd('excel/charword_table.json')

        update_charword(self.wiki, character_table, charword_table)
