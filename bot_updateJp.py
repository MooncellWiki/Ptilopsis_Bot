import re
import time

from wikiapi import *


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
                    unlock_condition = replace_story_condition(charword_table[charword_id]['lockDescription'], charword_table[charword_id]['unlockParam'][0]['valueInt']).replace('以查看更多信息', '以查看')
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


def update_charword_jp(se, url, character_table, charword_table, character_table_jp, charword_table_jp):
    for char in character_table_jp:
        char_detail = character_table[char]
        if char_detail['name'] in ['安洁莉娜'] or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        # if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue
        else:
            fin = read_wiki(se, url, character_table[char]['name'] + '/语音记录')
            charword_data = get_charword_data_jp(char, char_detail['name'], charword_table, charword_table_jp)
            charword_data += '\n<noinclude>[[分类:有官方日文文本的干员语音]]</noinclude>'

            if fin != charword_data:
                num_trial = 5
                for i in range(num_trial):
                    try:
                        write_wiki_minor(se, url, char_detail['name'] + '/语音记录', charword_data, '')
                        # print(fin)
                        print('Update: {}.'.format(char_detail['name'] + '/语音记录'))
                        break
                    except:
                        if i < num_trial:
                            print('Write {} fail. Try again.'.format(char_detail['name'] + '/语音记录'))
                        else:
                            print('Write {} fail. Skip.'.format(char_detail['name'] + '/语音记录'))


def update_skill_name(se, url, character_table, skill_table, character_table_jp, skill_table_jp, character_table_en, skill_table_en):
    for char in character_table_jp:
        char_detail = character_table[char]
        # if char_detail['name'] != '能天使' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue
        else:
            fin3 = read_wiki_repeat(se, url, char_detail['name'])
            fin2 = fin3

            if char_detail['skills']:
                count = 0
                for skills_cont in char_detail['skills']:
                    count += 1
                    skill_name = skill_table[skills_cont['skillId']]['levels'][0]['name']
                    skill_name_jp = skill_table_jp[skills_cont['skillId']]['levels'][0]['name']
                    if skills_cont['skillId'] in skill_table_en:
                        skill_name_en = skill_table_en[skills_cont['skillId']]['levels'][0]['name']
                    else:
                        skill_name_en = ''

                    num1 = fin2.find('|技能名={}'.format(skill_name))
                    num2 = -1
                    for i in range(count):
                        num2 = fin2.find('|技能类型1=', num2 + 1)
                    fin2 = fin2[:num1] + '|技能名={}\n'.format(skill_name) + '|技能名jp={}\n'.format(skill_name_jp) + '|技能名en={}\n'.format(skill_name_en) + fin2[num2:]
            fin = fin2

            if fin != fin3:
                write_wiki_minor(se, url, char_detail['name'], fin, '')
                print(char_detail['name'] + ' updated.')


def update_char_name(se, url, character_table, character_table_jp):
    for char in character_table_jp:
        char_detail = character_table[char]
        # if char_detail['name'] != '能天使' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue
        else:
            fin2 = read_wiki_repeat(se, url, char_detail['name'])

            name_jp = character_table_jp[char]['name']

            num1 = fin2.find('|干员名={}'.format(char_detail['name']))
            num2 = fin2.find('|干员外文名=')
            fin = fin2[:num1] + '|干员名={}\n'.format(char_detail['name']) + '|干员名jp={}\n'.format(name_jp) + fin2[num2:]
            
            if fin != fin2:
                write_wiki_minor(se, url, char_detail['name'], fin, '')
                print(char_detail['name'] + ' updated.')


def update_furni_info(se, url, building_data, building_data_jp, building_data_en):
    for furni in building_data['customData']['furnitures']:
        if furni not in building_data_jp['customData']['furnitures'] or furni not in building_data_en['customData']['furnitures']:
            continue
        furni_data_cn = building_data['customData']['furnitures'][furni]
        furni_data_jp = building_data_jp['customData']['furnitures'][furni]
        furni_data_en = building_data_en['customData']['furnitures'][furni]

        fin2 = read_wiki_repeat(se, url, furni_data_cn['name'])

        num1 = fin2.find('|描述=')
        num2 = fin2.find('|用途=')
        fin = fin2[:num1] + '|描述={}\n|描述jp={}\n|描述en={}\n'.format(furni_data_cn['description'], furni_data_jp['description'], furni_data_en['description']) + fin2[num2:]
        num1 = fin.find('|名称=')
        num2 = fin.find('|iconId=')
        fin = fin[:num1] + '|名称={}\n|名称jp={}\n|名称en={}\n'.format(furni_data_cn['name'], furni_data_jp['name'], furni_data_en['name']) + fin[num2:]

        if fin != fin2:
            write_wiki(se, url, furni_data_cn['name'], fin, '')
            print(furni_data_cn['name'], 'updated.')

