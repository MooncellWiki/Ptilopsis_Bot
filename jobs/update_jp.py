import re

from utils.job import Job


def get_charword_data_jp(char_id, char_name, charword_table, charword_table_jp):
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
                text_jp = charword_table_jp[charword_id]['voiceText']
                text_jp = text_jp.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}={text_jp}\n|中文{id}={text_cn}\n|语音{id}={voice}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav'
                )
            elif charword_table[charword_id]['unlockType'] == 'AWAKE':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                text_jp = charword_table_jp[charword_id]['voiceText']
                text_jp = text_jp.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}={text_jp}\n|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    voice = char_name + ' ' + charword_table[charword_id]['voiceTitle'] + '.wav',
                    unlock_condition = charword_table[charword_id]['lockDescription'].replace('以查看更多信息', '以查看')
                )
            elif charword_table[charword_id]['unlockType'] == 'FAVOR':
                text = charword_table[charword_id]['voiceText']
                text = text.replace('Dr.{@nickname}', '{{DrName|前缀=Dr.}}')
                text = text.replace('{@nickname}', '{{DrName}}')
                text_jp = charword_table_jp[charword_id]['voiceText']
                text_jp = text_jp.replace('{@nickname}', '{{DrName}}')
                char_word += '|标题{id}={title}\n|日文{id}={text_jp}\n|中文{id}={text_cn}\n|语音{id}={voice}\n|条件{id}={unlock_condition}\n'.format(
                    id = charword_table[charword_id]['voiceIndex'],
                    title = charword_table[charword_id]['voiceTitle'],
                    text_cn = text.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
                    text_jp = text_jp.rstrip().replace('~~~', '<nowiki>~~~</nowiki>'),
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


def update_charword_jp(wiki, character_table, charword_table, character_table_jp, charword_table_jp):
    for char in character_table_jp:
        char_detail = character_table[char]

        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        origin_text = wiki.read(character_table[char]['name'] + '/语音记录')
        new_text = get_charword_data_jp(char, char_detail['name'], charword_table, charword_table_jp)
        new_text += '\n<noinclude>[[分类:有官方日文文本的干员语音]]</noinclude>'

        # edit wiki
        if origin_text != new_text:
            # print(new_text)
            wiki.edit(
                title = char_detail['name'] + '/语音记录',
                text = new_text,
                summary = 'update',
            )
            print('Update: {}.'.format(char_detail['name'] + '/语音记录'))
        else:
            print('Same: {}.'.format(char_detail['name'] + '/语音记录'))


def update_skill_and_name(wiki, character_table, skill_table, character_table_jp, skill_table_jp, character_table_en,
        skill_table_en):
    for char in character_table_jp:
        char_detail = character_table[char]
        # if char_detail['name'] != '能天使' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        origin_text = wiki.read(character_table[char]['name'])
        new_text = origin_text

        # update skill name
        if char_detail['skills']:
            count = 0
            for skills_cont in char_detail['skills']:
                count += 1
                skill_name = skill_table[skills_cont['skillId']]['levels'][0]['name']
                skill_name_jp = skill_table_jp[skills_cont['skillId']]['levels'][0]['name']
                skill_name_en = skill_table_en[skills_cont['skillId']]['levels'][0]['name'] if skills_cont[
                                                                                                   'skillId'] in skill_table_en else ''

                num1 = new_text.find('|技能名={}'.format(skill_name))
                num2 = -1
                for i in range(count):
                    num2 = new_text.find('|技能类型1=', num2 + 1)
                new_text = new_text[:num1] + '|技能名={}\n'.format(skill_name) + '|技能名jp={}\n'.format(
                    skill_name_jp) + '|技能名en={}\n'.format(skill_name_en) + new_text[num2:]

        # update char name
        name_jp = character_table_jp[char]['name']
        name_en = character_table_en[char]['name'] if char in character_table_en else char_detail['name']

        num1 = new_text.find('|干员名={}'.format(char_detail['name']))
        num2 = new_text.find('|干员外文名=')
        new_text = new_text[:num1] + '|干员名={}\n'.format(char_detail['name']) + '|干员名jp={}\n'.format(name_jp) + new_text[
        num2:]

        num1 = new_text.find('{{pathnav2|干员一览}}')
        new_text = '{{{{干员页面名|{}|{}|{}}}}}'.format(char_detail['name'], name_en, name_jp) + new_text[num1:]

        # edit wiki
        if origin_text != new_text:
            # print(new_text)
            wiki.edit(
                title = char_detail['name'],
                text = new_text,
                summary = 'update',
            )
            print('Update: {}.'.format(char_detail['name']))
        else:
            print('Same: {}.'.format(char_detail['name']))

        if char_detail['name'] != name_jp:
            redirect_text = '#redirect [[{}]]'.format(char_detail['name'])
            wiki.edit(
                title = name_jp,
                text = redirect_text,
                summary = 'init',
                createonly = '1'
            )


def update_furni_info(wiki, building_data, building_data_jp, building_data_en):
    for furni in building_data['customData']['furnitures']:
        if furni not in building_data_jp['customData']['furnitures'] or furni not in building_data_en['customData'][
            'furnitures']:
            continue
        furni_data_cn = building_data['customData']['furnitures'][furni]
        furni_data_jp = building_data_jp['customData']['furnitures'][furni]
        furni_data_en = building_data_en['customData']['furnitures'][furni]

        origin_text = wiki.read(furni_data_cn['name'])
        new_text = origin_text

        # update info
        num1 = new_text.find('|描述=')
        num2 = new_text.find('|用途=')
        new_text = new_text[:num1] + '|描述={}\n|描述jp={}\n|描述en={}\n'.format(furni_data_cn['description'],
            furni_data_jp['description'],
            furni_data_en['description']) + new_text[num2:]
        num1 = new_text.find('|名称=')
        num2 = new_text.find('|iconId=')
        new_text = new_text[:num1] + '|名称={}\n|名称jp={}\n|名称en={}\n'.format(furni_data_cn['name'],
            furni_data_jp['name'],
            furni_data_en['name']) + new_text[num2:]

        # edit wiki
        if origin_text != new_text:
            # print(new_text)
            wiki.edit(
                title = furni_data_cn['name'],
                text = new_text,
                summary = 'update',
            )
            print('Update: {}.'.format(furni_data_cn['name']))
        else:
            print('Same: {}.'.format(furni_data_cn['name']))


class UpdateJp(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        charword_table = self.getgd('excel/charword_table.json')
        building_data = self.getgd('excel/building_data.json')

        character_table_jp = self.getgd('excel/character_table.json', 'jp')
        skill_table_jp = self.getgd('excel/skill_table.json', 'jp')
        charword_table_jp = self.getgd('excel/charword_table.json', 'jp')
        building_data_jp = self.getgd('excel/building_data.json', 'jp')

        character_table_en = self.getgd('excel/character_table.json', 'us')
        skill_table_en = self.getgd('excel/skill_table.json', 'us')
        charword_table_en = self.getgd('excel/charword_table.json', 'us')
        building_data_en = self.getgd('excel/building_data.json', 'us')

        update_charword_jp(self.wiki, character_table, charword_table, character_table_jp, charword_table_jp)
        update_skill_and_name(self.wiki, character_table, skill_table, character_table_jp, skill_table_jp,
            character_table_en, skill_table_en)
        update_furni_info(self.wiki, building_data, building_data_jp, building_data_en)
