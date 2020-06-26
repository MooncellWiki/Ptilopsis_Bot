from bot_textStyle import RichTextStyles
from wikiapi import *


def special_buff(buffName , description):
    if buffName == '坚毅随和':
        description = description.replace('额外降低心情消耗}}', '额外降低心情消耗}}{{color|#F49800|（心情每小时消耗-0.15）}}')
    elif buffName == '神经质':
        description += '{{color|#F49800|（心情每小时消耗+1.5）}}'
    elif buffName == '至察':
        description += '{{color|#F49800|（心情每小时消耗+0.5）}}'
    elif buffName in ['裁缝·α', '裁缝·β']:
        description = description.replace('影响概率）', '影响概率）{{color|#F49800|（同类效果取最高）}}')
    return description


def update_buildingBuff_list(se, url, buildingData, gamedata_const):
    buffFormat = '''{{{{后勤技能信息
|技能名={name}
|房间={room}
|技能图标={icon}
|技能描述={description}
}}}}'''
    roomFormat = '''=={roomName}==
{{|class="wikitable mw-collapsible mw-collapsed logo" style="text-align:center; width:100%; max-width:1000px; display:table; white-space:normal;"
! colspan="4" | {roomName}
|-
! width="30px" |
! width="100px" |名称
! width="520px" |描述
! width="350px" |持有干员{buffInfoAll}
|}}'''
    fin = ''
    buffText = {}
    buffOrder = {}

    for room in buildingData['rooms']:
        buffText[room] = {}
        buffOrder[room] = []

    for buff in buildingData['buffs']:
        buffData = buildingData['buffs'][buff]
        if buff in ['meet_spd[0010]', 'manu_prod_limit&cost[0000]']:
            continue
        
        text = buffFormat.format(
            name = buffData['buffName'],
            room = buildingData['rooms'][buffData['roomType']]['name'],
            icon = buffData['skillIcon'],
            description = special_buff(buffData['buffName'], RichTextStyles(gamedata_const).compile(buffData['description']))
        )
        if buffData['sortId'] in buffText[buffData['roomType']]:
            if '\n|-\n{}'.format(text) != buffText[buffData['roomType']][buffData['sortId']]:
                buffText[buffData['roomType']][buffData['sortId']] += '\n|-\n{}'.format(text)
                print(buffData['buffName'], ' has same sortId.')
            else:
                print(buffData['buffName'], ' duplicated.')
        else:
            buffOrder[buffData['roomType']].append(buffData['sortId'])
            buffText[buffData['roomType']][buffData['sortId']] = '\n|-\n{}'.format(text)

    for roomId in buffOrder:
        buffOrder[roomId].sort(reverse=True)
        roomInfo = ''
        for sortId in buffOrder[roomId]:
            roomInfo += buffText[roomId][sortId]
        if buffOrder[roomId] != []:
            fin += roomFormat.format(
                    roomName = buildingData['rooms'][roomId]['name'],
                    buffInfoAll = roomInfo
                ) + '\n'

    write_wiki_minor(se, url, '后勤技能一览', fin, '')
    # print(fin)
    print('Update: 后勤技能一览.')


def update_buildingBuff_data(se, url, buildingData, character_table, gamedata_const):
    roomFormat = '''=={roomName}==
{{|class="wikitable" style="text-align:center; width:100%; max-width:1000px; display:table; white-space:normal;"
!width="60%"|描述
!width="40%"|干员{buffInfoAll}
|}}'''

    fin = ''
    roomData = {}
    buffSet = {}
    buffDescSet = {}
    for room in buildingData['rooms']:
        roomData[room] = ''
        buffDescSet[room] = {}

    for char in buildingData['chars']:
        char_buffData = buildingData['chars'][char]
        for buffId in char_buffData['buffChar']:
            for buffId2 in buffId['buffData']:
                if buffId2['buffId'] not in buffSet:
                    buffSet[buffId2['buffId']] = []
                buffSet[buffId2['buffId']].append('{{{{干员头像|{name}|elite=精英{phase}}}}}'.format(
                    name = character_table[char]['name'],
                    phase = buffId2['cond']['phase']
                ))

    for buff in buildingData['buffs']:
        buffData = buildingData['buffs'][buff]

        if buffData['description'] not in buffDescSet[buffData['roomType']]:
            buffDescSet[buffData['roomType']][buffData['description']] = []
        buffDescSet[buffData['roomType']][buffData['description']] += buffSet[buff]

    for roomId in roomData:
        for buffDesc in buffDescSet[roomId]:
            roomData[roomId] += '\n|-\n|{desc}\n|{chars}'.format(
                desc = RichTextStyles(gamedata_const).compile(buffDesc),
                chars = ' '.join(buffDescSet[roomId][buffDesc])
            )
        if roomData[roomId] != '':
            roomInfo = roomFormat.format(
                roomName = buildingData['rooms'][roomId]['name'],
                buffInfoAll = roomData[roomId]
            )
            fin += roomInfo + '\n'

    write_wiki_minor(se, url, '用户:Seniorious/base', fin, '')
    # print(fin)
    print('Update: 用户:Seniorious/base.')