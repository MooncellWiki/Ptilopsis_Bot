import re
import time

from wikiapi import *


def get_char_attr(se, url, character_table, id_table):
    content = {}
    for char in character_table:
        char_detail = character_table[char]
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        final_phase = char_detail['phases'][len(char_detail['phases']) - 1]

        maxHp = final_phase['attributesKeyFrames'][1]['data']['maxHp']
        atk = final_phase['attributesKeyFrames'][1]['data']['atk']
        defence = final_phase['attributesKeyFrames'][1]['data']['def']
        magicResistance = final_phase['attributesKeyFrames'][1]['data']['magicResistance']
        cost = final_phase['attributesKeyFrames'][1]['data']['cost']
        blockCnt = final_phase['attributesKeyFrames'][1]['data']['blockCnt']
        attackSpeed = final_phase['attributesKeyFrames'][1]['data']['attackSpeed']
        baseAttackTime = final_phase['attributesKeyFrames'][1]['data']['baseAttackTime']
        respawnTime = final_phase['attributesKeyFrames'][1]['data']['respawnTime']

        atk += char_detail['favorKeyFrames'][1]['data']['atk']
        defence += char_detail['favorKeyFrames'][1]['data']['def']
        maxHp += char_detail['favorKeyFrames'][1]['data']['maxHp']

        for potentialRank in char_detail['potentialRanks']:
            if potentialRank['type'] == 0:
                attributeType = potentialRank['buff']['attributes']['attributeModifiers'][0]['attributeType']
                if attributeType == 4:
                    cost += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 21:
                    respawnTime += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 1:
                    atk += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 2:
                    defence += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 0:
                    maxHp += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 3:
                    magicResistance += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                elif attributeType == 7:
                    attackSpeed += potentialRank['buff']['attributes']['attributeModifiers'][0]['value']
                else:
                    print('Error! Char {name} attributeType {num} dont know!'.format(
                        name = char_detail['name'],
                        num = attributeType
                    ))

        remark = ""
        for talent_id in range(len(char_detail['talents'])):
            talent_table = char_detail['talents'][talent_id]['candidates']
            remark += replace_talpu(talent_table[len(talent_table) - 1]['description'])
            if talent_id != len(char_detail['talents']) - 1:
                remark += "<br/>"

        desc = '|[[{name}]]||{rarity}||{profession}||{maxHp:.0f}||{atk:.0f}||{defence:.0f}||{magicResistance:.0f}||{cost:.0f}||{blockCnt:.0f}||{attackSpeed:.0f}||{baseAttackTime}s||data-sort-value={respawnTime:.0f}|{respawnTime:.0f}s'.format(
            name = char_detail['name'],
            rarity = char_detail['rarity'] + 1,
            profession = trans_profession(char_detail['profession']),
            maxHp = maxHp,
            atk = atk,
            defence = defence,
            magicResistance = magicResistance,
            cost = cost,
            blockCnt = blockCnt,
            attackSpeed = attackSpeed,
            baseAttackTime = baseAttackTime,
            respawnTime = respawnTime
        )
        desc += '\n|- class="expand-child" style="font-size:85%; line-height:1.2; color:gray;"\n|colspan="12"|{}'.format(remark)

        content[id_table[char_detail['name']]['id']] = desc

    table = '''{{cbox2|lv=2|text=以下为全体干员\'\'\'满精英化 满级 满潜能 满信赖\'\'\'时的面板白值，\'\'\'不包括\'\'\'天赋和技能加成。}}
{|class="wikitable sortable" style="text-align:center; width:1000px; display:table; white-space:normal;"
!名字!!稀有度!!职业!!生命!!攻击!!防御!!法抗!!费用!!阻挡!!攻速!!攻击间隔!!再部署'''
    for i in reversed(range(200)):
        if str(i) in content:
            table += '\n|-\n{}'.format(content[str(i)])
    table += '\n|}'

    write_wiki(se, url, '用户:Seniorious/attribute', table, '')
    # print(table)
    print('Update: 用户:Seniorious/attribute.')


def trans_profession(profession):
    return {
        'TANK': '重装',
        'PIONEER': '先锋',
        'SUPPORT': '辅助',
        'SNIPER': '狙击',
        'MEDIC': '医疗',
        'WARRIOR': '近卫',
        'CASTER': '术师',
        'SPECIAL': '特种',
    }[profession]


def replace_talpu(text):
    p1 = r"(.*)<\@ba\.talpu>(.*)<\/>(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + '{{color|#F49800|' + result.group(2) + '}}' + result.group(3)
        text = replace_talpu(text)
        # print(result.groups())
    return text
