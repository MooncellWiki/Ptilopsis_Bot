import re
import time

from wikiapi import *


def get_skin_info(char_key, skin_table):
    basic_info = ''
    special_skin_id = 1
    for phase_id in skin_table['buildinEvolveMap'][char_key]:
        basic_info += '\n|精英{phase_id}描述={des}'.format(
            phase_id = phase_id,
            des = skin_table['charSkins'][skin_table['buildinEvolveMap'][char_key][phase_id]]['displaySkin']['content'].replace('\n','<br/>')
        )
    for skin_key in skin_table['charSkins']:
        if char_key in skin_key:
            if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'] != '默认服装':
                basic_info += '\n|时装{skin_id}名称={name}\n|时装{skin_id}系列={group}\n|时装{skin_id}color={color}\n|时装{skin_id}描述={des}'.format(
                    skin_id = special_skin_id,
                    name =  skin_table['charSkins'][skin_key]['displaySkin']['skinName'],
                    color = skin_table['charSkins'][skin_key]['displaySkin']['colorList'][0],
                    group = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'],
                    des = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>','').replace('</color>','').replace('\r','').replace('\n','<br/>')
                    )
                special_skin_id += 1
    basic_info += '\n}}'
    return basic_info


def update_randomFig(se, url, character_table, skin_table):
    skin_list = {}
    fin = '<choose uncached before="[[文件:" after="|右|555px]]">'
    for skin_key in skin_table['charSkins']:
        skin_content = skin_table['charSkins'][skin_key]
        if skin_content['displaySkin']['skinGroupSortIndex'] in [-50, -30, 0, 1]:
            continue
        if skin_content['displaySkin']['skinGroupName'] == '默认服装':
            fin += '\n<option>立绘 {name} 2.png|link={name}</option>'.format(
                name = character_table[skin_content['charId']]['name']
            )
        else:
            char_name = character_table[skin_content['charId']]['name']
            if char_name in skin_list:
                skin_list[char_name] += 1
            else:
                skin_list[char_name] = 1

    for char in skin_list:
        for skin_num in range(skin_list[char]):
            fin += '\n<option>立绘 {name} skin{id}.png|link={name}</option>'.format(
                name = char,
                id = skin_num + 1
            )
    fin += '\n</choose>'

    write_wiki(se, url, '模板:随机干员立绘', fin, '')
    # print(fin)
    print('Update: 模板:随机干员立绘.')


def update_skin(se, url, character_table, skin_table, skin_list):
    for char in character_table:
        char_detail = character_table[char]
        if char_detail['name'] not in skin_list or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        # if char_detail['name'] != '芙蓉' or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        # if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue
        
        fin2 = read_wiki_repeat(se, url, char_detail['name'])

        num1 = fin2.find('\n|精英0描述')
        num2 = fin2.find('==获得方式==')
        fin = fin2[:num1] + get_skin_info(char, skin_table) + '\n' + fin2[num2:]

        write_wiki_minor(se, url, char_detail['name'], fin, '')
        # print(fin)
        print('Update: {}.'.format(char_detail['name']))


def update_skin_handbook(se, url, character_table, skin_table):
    skin_format = '''{{{{锚点|{skinKey}}}}}
\'\'\'{name}\'\'\'
{{{{干员时装
|干员名={name}
|皮肤序号={skinNo}
|时装名={skinName}
|画师={drawerName}
|时装组名称={skinGroupName}
|内容={content}
|获得途径={obtainApproach}

|dialog={dialog}
|usage={usage}
|desc={description}
}}}}'''

    skin_char = {}
    max_index = 0
    for skin_key in skin_table['charSkins']:
        if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex'] > max_index:
            max_index = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex']

    skin_group_order = ['' for x in range(max_index)]
    skin_group_list1 = {}
    skin_group_list2 = {}

    for skin_key in skin_table['charSkins']:
        skin_info = skin_table['charSkins'][skin_key]
        if skin_info['displaySkin']['skinGroupName'] != '默认服装' and 'token' not in skin_key:
            if skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] == '':
                skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] = skin_info['displaySkin']['skinGroupName']
                skin_group_list1[skin_info['displaySkin']['skinGroupName']] = []
                skin_group_list2[skin_info['displaySkin']['skinGroupName']] = []

            if skin_table['charSkins'][skin_key]['charId'] not in skin_char:
                skin_char[skin_table['charSkins'][skin_key]['charId']] = 0

            skin_char[skin_info['charId']] += 1
            skin_text1 = skin_format.format(
                skinKey = skin_info['portraitId'].replace('#', ''),
                name = character_table[skin_info['charId']]['name'],
                skinName = skin_info['displaySkin']['skinName'],
                skinNo = skin_char[skin_info['charId']],
                modelName = skin_info['displaySkin']['modelName'],
                drawerName = skin_info['displaySkin']['drawerName'],
                skinGroupId = skin_info['displaySkin']['skinGroupId'],
                skinGroupName = skin_info['displaySkin']['skinGroupName'],
                content = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>','').replace('</color>','').replace('\r','').replace('\n','<br/>'),
                dialog = skin_info['displaySkin']['dialog'],
                usage = skin_info['displaySkin']['usage'],
                description = skin_info['displaySkin']['description'],
                obtainApproach = skin_info['displaySkin']['obtainApproach']
            )
            skin_text2 = '{{{{皮肤头像|{name}|90px|{skinNo}|link=#{skinKey}}}}}'.format(
                name = character_table[skin_info['charId']]['name'],
                skinNo = skin_char[skin_info['charId']],
                skinKey = skin_info['portraitId'].replace('#', '')
            )
            skin_group_list1[skin_info['displaySkin']['skinGroupName']].append(skin_text1)
            skin_group_list2[skin_info['displaySkin']['skinGroupName']].append(skin_text2)

    handbook = '__NOTOC__\n{|class="wikitable" style="width:1000px; white-space:normal; display:table;"\n!皮肤组\n!干员'
    for group_name in skin_group_order:
        if group_name != '':
            handbook += '\n|-\n|\'\'\'{groupName}\'\'\'\n|'.format(
                groupName = group_name
            ) + ''.join(skin_group_list2[group_name])
    handbook += '\n|}'
    for group_name in skin_group_order:
        if group_name != '':
            handbook += '\n=={}==\n'.format(group_name)
            handbook += '\n'.join(skin_group_list1[group_name])

    write_wiki(se, url, '用户:Seniorious/skins', handbook, '')
    # print(handbook)
    print('Update: 用户:Seniorious/skins.')
