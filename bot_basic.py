import os
import re
import time

from bot_textStyle import RichTextStyles
from wikiapi import *


def get_basic_info(char_detail, char_key, team_table, gamedata_const, stories_table, skin_table, id_table):
    if id_table[char_detail['name']]['approach']:
        itemObtainApproach = id_table[char_detail['name']]['approach']
    else:
        itemObtainApproach = char_detail['itemObtainApproach']
    basic_info = '{{{{Charinfo\n|干员名={name}\n|干员外文名={english_name}\n|干员序号={char_id}\n|特性={description}\n|稀有度={rarity}\n|职业={profession}\n|团队={team}\n|情报编号={displayNumber}\n|默认logo={displayLogo}\n|获得方式={itemObtainApproach}\n|位置={position}\n|标签={tagList}\n|画师={drawName}\n|配音={infoName}'.format(
        name = char_detail['name'],
        english_name = char_detail['appellation'],
        char_id = id_table[char_detail['name']]['id'],
        displayLogo = trans_display_logo(char_detail['displayLogo']),
        description = replace_basic_desc(char_detail['description']).replace('\\n', '<br/>'),
        rarity = char_detail['rarity'],
        profession = trans_profession(char_detail['profession']),
        team = team_table[str(char_detail['team'])]['teamName'],
        displayNumber = char_detail['displayNumber'],
        itemObtainApproach = itemObtainApproach,
        position = trans_position(char_detail['position']),
        tagList = ' '.join(char_detail['tagList']),
        drawName = stories_table['handbookDict'][char_key]['drawName'],
        infoName = stories_table['handbookDict'][char_key]['infoName']
    )
    if char_detail['trait'] != None:
        override_desc_text = ''
        override_desc_list = ['', '', '']
        for desc in char_detail['trait']['candidates']:
            if desc['overrideDescripton'] != None:
                desc_dic = {}
                for i in desc['blackboard']:
                    if i['value'] != int(i['value']):
                        desc_dic[i['key'].replace('.', '').replace(']', '').replace('[', '')] = i['value']
                    else:
                        desc_dic[i['key'].replace('.', '').replace(']', '').replace('[', '')] = int(i['value'])
                override_desc = desc['overrideDescripton'].replace('-{-', '{').replace('{-', '{').replace('\\n', '<br/>')
                override_desc = replace_key(replace_upper(override_desc))
                override_desc = override_desc.replace(':0%}', ':.0%}').replace(':0.0%}', ':0.1%}').replace(':0.0}', '}')
                override_desc = RichTextStyles(gamedata_const).compile(override_desc)
                override_desc = override_desc.format(**desc_dic)

                override_desc_list[desc['unlockCondition']['phase']] = override_desc
        if override_desc_list[2] != '':
            override_desc_text = '|特性2={}\n'.format(override_desc_list[2]) + override_desc_text
        if override_desc_list[1] != '':
            override_desc_text = '|特性1={}\n'.format(override_desc_list[1]) + override_desc_text
        if override_desc_list[0] != '':
            override_desc_text = '|特性={}\n'.format(override_desc_list[0]) + override_desc_text
        num1 = basic_info.find('|特性=')
        num2 = basic_info.find('|稀有度=')
        basic_info = basic_info[:num1] + override_desc_text + basic_info[num2:]

    basic_info += '\n'
    special_skin_id = 1
    for phase_id in skin_table['buildinEvolveMap'][char_key]:
        desc = skin_table['charSkins'][skin_table['buildinEvolveMap'][char_key][phase_id]]['displaySkin']['content']
        if desc != None:
            desc = desc.replace('\n', '<br/>')
        basic_info += '\n|精英{phase_id}描述={des}'.format(
            phase_id = phase_id,
            des = desc
        )
    for skin_key in skin_table['charSkins']:
        if char_key in skin_key:
            if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'] != '默认服装':
                basic_info += '\n|时装{skin_id}名称={name}\n|时装{skin_id}系列={group}\n|时装{skin_id}color={color}\n|时装{skin_id}描述={des}'.format(
                    skin_id = special_skin_id,
                    name = skin_table['charSkins'][skin_key]['displaySkin']['skinName'],
                    color = skin_table['charSkins'][skin_key]['displaySkin']['colorList'][0],
                    group = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'],
                    des = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>', '').replace('</color>', '').replace('\r', '').replace('\n', '<br/>')
                )
                special_skin_id += 1
    basic_info += '\n}}'
    return basic_info


def get_phases_data(char_detail):
    phases_data = '{{属性\n'

    for phases_num in range(len(char_detail['phases'])):
        if phases_num == 0:
            blockCnt = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['blockCnt']
            blockCnt_2 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['blockCnt']
            block_data = str(blockCnt)
            cost = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['cost']
            cost_data = str(cost)
        else:
            # blockCnt_2 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['blockCnt']
            # if blockCnt != blockCnt_2:
            #     block_data += '→' + str(blockCnt_2)
            #     blockCnt = blockCnt_2
            blockCnt_2 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['blockCnt']
            block_data += '→' + str(blockCnt_2)
            cost_2 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['cost']
            if cost != cost_2:
                cost_data += '→' + str(cost_2)
                cost = cost_2
    if blockCnt_2 == char_detail['phases'][0]['attributesKeyFrames'][0]['data']['blockCnt']:
        block_data = str(char_detail['phases'][0]['attributesKeyFrames'][0]['data']['blockCnt'])

    phases_data += '|再部署=' + str(int(char_detail['phases'][0]['attributesKeyFrames'][0]['data']['respawnTime'])) + 's\n'
    phases_data += '|部署费用=' + cost_data + '\n'
    phases_data += '|阻挡数=' + block_data + '\n'
    phases_data += '|攻击速度=' + str(char_detail['phases'][0]['attributesKeyFrames'][0]['data']['baseAttackTime']) + 's\n'
    for phases_num in range(len(char_detail['phases'])):
        if phases_num == 0:
            phases_data += '|精英0_1级_生命上限={hp_0}\n|精英0_1级_攻击={atk_0}\n|精英0_1级_防御={def_0}\n|精英0_1级_法术抗性={res_0}\n'.format(
                hp_0 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['maxHp'],
                atk_0 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['atk'],
                def_0 = char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['def'],
                res_0 = int(char_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['magicResistance'])
            )
        phases_data += '|精英{num}_满级={lv}\n|精英{num}_满级_生命上限={hp}\n|精英{num}_满级_攻击={atk}\n|精英{num}_满级_防御={defence}\n|精英{num}_满级_法术抗性={res}\n'.format(
            num = phases_num,
            lv = char_detail['phases'][phases_num]['maxLevel'],
            hp = char_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['maxHp'],
            atk = char_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['atk'],
            defence = char_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['def'],
            res = int(char_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['magicResistance'])
        )

    favorKey_data = '|信赖加成_生命上限=' + str(char_detail['favorKeyFrames'][1]['data']['maxHp']) + '\n' + '|信赖加成_攻击=' + str(
        char_detail['favorKeyFrames'][1]['data']['atk']) + '\n' + '|信赖加成_防御=' + str(
        char_detail['favorKeyFrames'][1]['data']['def']) + '\n'

    # for favorKey in char_detail['favorKeyFrames'][0]['data']:
    #     if char_detail['favorKeyFrames'][0]['data'][favorKey] != 0 and char_detail['favorKeyFrames'][0]['data'][favorKey] != False:
    #         print(char_detail['name'] + ' -- 0 :  ' +  favorKey)
    #     if char_detail['favorKeyFrames'][1]['data'][favorKey] != 0 and char_detail['favorKeyFrames'][1]['data'][favorKey] != False:
    #         print(char_detail['name'] + ' -- 1 :  ' +  favorKey)

    phases_data += favorKey_data + "}}"

    return phases_data


def get_range_data(char_detail):
    range_data = '{{干员攻击范围\n'

    for range_num in range(len(char_detail['phases'])):
        range_data += '|精英{}范围={}\n'.format(range_num, char_detail['phases'][range_num]['rangeId'])
    range_data += '}}'
    return range_data


def get_talent_list(char_detail):
    talent_list = '{{天赋列表\n'
    for talent_id in range(len(char_detail['talents'])):
        talent_table = char_detail['talents'][talent_id]['candidates']
        for talent_table_id in range(len(talent_table)):
            talent_description = replace_talpu(talent_table[talent_table_id]['description'])
            talent_condition = get_tal_condition(talent_table[talent_table_id]['requiredPotentialRank'],
                                                 talent_table[talent_table_id]['unlockCondition']['phase'],
                                                 talent_table[talent_table_id]['unlockCondition']['level'])

            talent_list += '|第' + trans_id(talent_id + 1) + '天赋' + str(talent_table_id + 1) + '=' + \
                           talent_table[talent_table_id]['name'] + '\n'
            talent_list += '|第' + trans_id(talent_id + 1) + '天赋' + str(
                talent_table_id + 1) + '条件=' + talent_condition + '\n'
            talent_list += '|第' + trans_id(talent_id + 1) + '天赋' + str(
                talent_table_id + 1) + '效果=' + talent_description + '\n'
    talent_list += '}}'
    return talent_list


def get_potential_list(char_detail):
    if char_detail['potentialRanks']:
        potential_list = '{{潜能提升\n'
        for potential_id in range(len(char_detail['potentialRanks'])):
            potential_list += '|潜能' + str(potential_id + 2) + '=' + char_detail['potentialRanks'][potential_id][
                'description'] + '\n'
        potential_list += '}}'
    else:
        potential_list = '该干员无法提升潜能'
    return potential_list


def get_skill_list(char_detail, skill_table, gamedata_const):
    skill_list = ''

    if char_detail['skills']:
        for skill_id in range(len(char_detail['skills'])):
            if char_detail['skills'][skill_id]['skillId'] == None:
                continue
            skill_data = skill_table[char_detail['skills'][skill_id]['skillId']]
            skill_list += '\n\'\'\'技能{num}（{skill_cond}开放）\'\'\'\n{{{{技能\n|技能名={skill_name}\n|技能类型1={type1}{type2}'.format(
                num = skill_id + 1,
                skill_cond = get_tal_condition(0, char_detail['skills'][skill_id]['unlockCond']['phase'],
                                               char_detail['skills'][skill_id]['unlockCond']['level']),
                skill_name = skill_data['levels'][0]['name'],
                type1 = trans_sp_type(skill_data['levels'][0]['spData']['spType']),
                type2 = trans_skill_type(skill_data['levels'][0]['skillType'])
            )
            if skill_data['levels'][0]['rangeId']:
                skill_list += '\n|技能范围={skill_range}'.format(skill_range = skill_data['levels'][0]['rangeId'])
                for i in skill_data['levels']:
                    if i['rangeId'] != skill_data['levels'][0]['rangeId']:
                        print('技能{}范围随等级变化'.format(skill_id + 1))
                        break
            for level_id in range(len(skill_table[char_detail['skills'][skill_id]['skillId']]['levels'])):
                skill_dic = {}
                for i in skill_data['levels'][level_id]['blackboard']:
                    if i['value'] != int(i['value']):
                        skill_dic[i['key'].replace('.', '').replace(']', '').replace('[', '')] = i['value']
                    else:
                        skill_dic[i['key'].replace('.', '').replace(']', '').replace('[', '')] = int(i['value'])
                skill_description = skill_data['levels'][level_id]['description'].replace('-{-', '{').replace('{-',
                                                                                                              '{').replace(
                    '\\n', '<br/>')
                skill_description = replace_key(replace_upper(skill_description))
                skill_description = skill_description.replace(':0%}', ':.0%}').replace(':0.0%}', ':0.1%}').replace(
                    ':0.0}', '}')
                skill_description = RichTextStyles(gamedata_const).compile(skill_description)
                skill_description = skill_description.format(**skill_dic)

                if skill_data['levels'][level_id]['duration'] == 0 or skill_data['levels'][level_id]['duration'] == -1:
                    skill_duration = ''
                elif skill_data['levels'][level_id]['duration'] == int(skill_data['levels'][level_id]['duration']):
                    skill_duration = str(int(skill_data['levels'][level_id]['duration']))
                else:
                    skill_duration = str(skill_data['levels'][level_id]['duration'])
                if level_id >= 7:
                    skill_num = '专精' + str(level_id - 6)
                else:
                    skill_num = str(level_id + 1)
                skill_list += '\n|技能{num}描述={desc}\n|技能{num}初始={initSp}\n|技能{num}消耗={spCost}\n|技能{num}持续={duration}'.format(
                    num = skill_num,
                    desc = skill_description,
                    initSp = skill_data['levels'][level_id]['spData']['initSp'],
                    spCost = skill_data['levels'][level_id]['spData']['spCost'],
                    duration = skill_duration
                )
            skill_list += '\n}}'
    else:
        skill_list = '\n该干员没有技能'

    return skill_list


def get_building_skill(building_data, char_key):
    building_skill = '{{后勤技能\n'
    building_skill_count = 1
    if char_key in building_data['chars']:
        char_building_skill = building_data['chars'][char_key]
        for building_skill_id in range(len(char_building_skill['buffChar'])):
            for building_skill_id_2 in range(len(char_building_skill['buffChar'][building_skill_id]['buffData'])):
                temp = char_building_skill['buffChar'][building_skill_id]['buffData'][building_skill_id_2]
                buff_name = building_data['buffs'][temp['buffId']]['buffName']
                buff_cond = [temp['cond']['phase'], temp['cond']['level']]
                buff_cond_lv = ''
                if buff_cond[1] != 1:
                    buff_cond_lv = '|后勤技能' + str(building_skill_count) + '等级=' + str(buff_cond[1]) + '级\n'
                building_skill += '|后勤技能' + str(building_skill_count) + '=' + buff_name + '\n' + '|后勤技能' + str(
                    building_skill_count) + '阶段=精英' + str(buff_cond[0]) + '\n' + buff_cond_lv
                building_skill_count += 1
    building_skill += '}}\n<!--如需修改技能信息，请前往[[后勤技能一览]]页面-->'
    return building_skill


def get_token_info(char_detail, update_token_page, character_table):
    if char_detail['tokenKey'] == None:
        return ''
    token_info = '==召唤物信息==\n{{{{参阅|{token_name}|该持有者的召唤物}}}}'.format(
        token_name = character_table[char_detail['tokenKey']]['name']
    )
    token_key_list = [char_detail['tokenKey']]
    for skill in char_detail['skills']:
        if skill['overrideTokenKey'] != None:
            token_key_list.append(skill['overrideTokenKey'])
    for token_key in token_key_list:
        token_detail = character_table[token_key]
        token_page = '==召唤物信息==\n{{{{召唤物信息\n|中文名称={name_cn}\n|外文名称={appellation}\n|持有者={owner}\n|使用条件=—'.format(
            name_cn = token_detail['name'],
            appellation = token_detail['appellation'],
            owner = char_detail['name'],
        )
        token_page += '\n|部署位置='
        token_page += {'MELEE': '近战位', 'RANGED': '远程位', 'ALL': '近战/远程位'}[token_detail['position']]
        token_page += '\n|攻击范围={rangeId}'.format(
            rangeId = token_detail['phases'][0]['rangeId']
        )
        for phases_num in range(1, len(token_detail['phases'])):
            if token_detail['phases'][phases_num]['rangeId'] != token_detail['phases'][0]['rangeId']:
                print('召唤物{} rangeId changes.'.format(token_detail['name']))
                break
        for phases_num in range(len(token_detail['phases'])):
            token_page += '\n|精英{num}_1级_生命上限={hp}\n|精英{num}_1级_攻击={atk}\n|精英{num}_1级_防御={defence}\n|精英{num}_1级_法术抗性={magicResistance}'.format(
                num = phases_num,
                hp = token_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['maxHp'],
                atk = token_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['atk'],
                defence = token_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['def'],
                magicResistance = int(token_detail['phases'][phases_num]['attributesKeyFrames'][0]['data']['magicResistance'])
            )
            token_page += '\n|精英{num}_满级={level}'.format(
                num = phases_num,
                level = token_detail['phases'][phases_num]['maxLevel']
            )
            token_page += '\n|精英{num}_满级_生命上限={hp}\n|精英{num}_满级_攻击={atk}\n|精英{num}_满级_防御={defence}\n|精英{num}_满级_法术抗性={magicResistance}'.format(
                num = phases_num,
                hp = token_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['maxHp'],
                atk = token_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['atk'],
                defence = token_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['def'],
                magicResistance = int(token_detail['phases'][phases_num]['attributesKeyFrames'][1]['data']['magicResistance'])
            )
        token_page += '\n|再部署时间={respawnTime}s\n|部署费用={cost}\n|阻挡数={blockCnt}\n|攻击间隔={baseAttackTime}s\n|嘲讽等级={tauntLevel}\n|部署占用数=?\n}}}}'.format(
            respawnTime = token_detail['phases'][0]['attributesKeyFrames'][1]['data']['respawnTime'],
            cost = token_detail['phases'][0]['attributesKeyFrames'][1]['data']['cost'],
            blockCnt = token_detail['phases'][0]['attributesKeyFrames'][1]['data']['blockCnt'],
            baseAttackTime = token_detail['phases'][0]['attributesKeyFrames'][1]['data']['baseAttackTime'],
            tauntLevel = token_detail['phases'][0]['attributesKeyFrames'][1]['data']['tauntLevel']
        )
        token_page += '\n==召唤物模型==\n{{TokenDoll}}'

        if update_token_page == True:
            write_wiki_minor(se, url, token_detail['name'], token_page, '')
            print(token_page)
            print('召唤物 ' + token_detail['name'] + ' done.')
    return token_info


def get_phase_list(char_detail, item_table, gamedata_const):
    phase_list = '{{精英化材料\n'
    if len(char_detail['phases']) >= 2:
        for phase_id in range(1, len(char_detail['phases'])):
            money = gamedata_const['evolveGoldCost'][char_detail['rarity']][phase_id - 1]
            if int(money / 10000) == money / 10000:
                money_str = str(int(money / 10000))
            else:
                money_str = str(float(money / 10000))
            material_list = '{{材料消耗|龙门币|' + money_str + 'w}}'
            for material_id in range(len(char_detail['phases'][phase_id]['evolveCost'])):
                material_list += ' {{材料消耗|' + \
                                 item_table['items'][char_detail['phases'][phase_id]['evolveCost'][material_id]['id']][
                                     'name'] + '|' + str(
                    char_detail['phases'][phase_id]['evolveCost'][material_id]['count']) + '}}'
            phase_list += '|精' + str(phase_id) + '=' + material_list + '\n'
        phase_list += '}}'
    else:
        phase_list = '该干员无法精英化'
    return phase_list


def get_skill_levelUp_list(char_detail, skill_table, item_table):
    skill_levelUp_list = '{{技能升级材料\n'
    if char_detail['skills']:
        for allSkillLvlup_id in range(len(char_detail['allSkillLvlup'])):
            skill_levelUp_list += '|' + str(allSkillLvlup_id + 2) + '='
            common_material_list = ''
            for common_material_id in range(len(char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'])):
                if common_material_list == '':
                    common_material_list = '{{材料消耗|' + item_table['items'][
                        char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['id']][
                        'name'] + '|' + str(
                        char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['count']) + '}}'
                else:
                    common_material_list += ' {{材料消耗|' + item_table['items'][
                        char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['id']][
                        'name'] + '|' + str(
                        char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['count']) + '}}'
            skill_levelUp_list += common_material_list + '\n'

        for skill_id in range(len(char_detail['skills'])):
            skill_detail = skill_table[char_detail['skills'][skill_id]['skillId']]['levels']
            if char_detail['skills'][skill_id]['levelUpCostCond']:
                for i in [8, 9, 10]:
                    skill_levelup_material = char_detail['skills'][skill_id]['levelUpCostCond'][i - 8]['levelUpCost']
                    material_list = ''
                    for material_id in range(len(skill_levelup_material)):
                        if material_list == '':
                            material_list = '{{材料消耗|' + item_table['items'][skill_levelup_material[material_id]['id']][
                                'name'] + '|' + str(skill_levelup_material[material_id]['count']) + '}}'
                        else:
                            material_list += ' {{材料消耗|' + \
                                             item_table['items'][skill_levelup_material[material_id]['id']][
                                                 'name'] + '|' + str(
                                skill_levelup_material[material_id]['count']) + '}}'
                    skill_levelUp_list += '|' + trans_id(skill_id + 1) + str(i) + '=' + material_list + '\n'
        skill_levelUp_list += '}}'
    else:
        skill_levelUp_list = '该干员没有技能'
    return skill_levelUp_list


def get_related_item(char_detail, item_table):
    if char_detail['potentialItemId']:
        return '{{{{相关道具\n|干员简介={itemUsage}\n|干员简介补充={itemDesc}\n|信物用途={potentialUsage}\n|信物描述={potentialDesc}\n}}}}'.format(
            itemUsage = char_detail['itemUsage'],
            itemDesc = char_detail['itemDesc'],
            potentialDesc = item_table['items'][char_detail['potentialItemId']]['description'],
            potentialUsage = item_table['items'][char_detail['potentialItemId']]['usage']
        )
    else:
        return '{{{{相关道具\n|干员简介={itemUsage}\n|干员简介补充={itemDesc}\n}}}}'.format(
            itemUsage = char_detail['itemUsage'],
            itemDesc = char_detail['itemDesc']
        )


def get_stories_list(char_detail, stories_table, char_key):
    stories_list_set = '{{人员档案set\n'
    stories1 = stories_table['handbookDict'][char_key]['storyTextAudio'][0]['stories'][0]['storyText']
    stories2 = stories_table['handbookDict'][char_key]['storyTextAudio'][1]['stories'][0]['storyText']
    stories3 = ''
    for i in stories_table['handbookDict'][char_key]['storyTextAudio']:
        if i['storyTitle'] == '临床诊断分析':
            stories3 = i['stories'][0]['storyText']

    doc_exp, doc2 = replace_doc_exp(stories1)
    doc7 = replace_basic_doc(stories1, '矿石病感染情况')
    p = r"确认为(.*)感染者"
    pattern1 = re.compile(p)
    result = re.search(pattern1, doc7)
    if result:
        doc8 = result.group(1) + '感染者'
    else:
        doc8 = doc7

    stories_list_set += '|性别={doc1}\n|{doc_exp}={doc2}\n|出身地={doc3}\n|生日={doc4}\n|种族={doc5}\n|身高={doc6}\n|矿石病感染情况={doc7}\n|是否感染者={doc8}\n\n|物理强度={test1}\n|战场机动={test2}\n|生理耐受={test3}\n|战术规划={test4}\n|战斗技巧={test5}\n|源石技艺适应性={test6}\n\n|体细胞与源石融合率={data1}\n|血液源石结晶密度={data2}\n}}}}'.format(
        doc1 = replace_basic_doc(stories1, '性别'),
        # doc_exp = doc_exp,
        doc_exp = '战斗经验',
        doc2 = doc2,
        doc3 = replace_basic_doc(stories1, '出身地'),
        doc4 = replace_basic_doc(stories1, '生日'),
        doc5 = replace_basic_doc(stories1, '种族'),
        doc6 = replace_basic_doc(stories1, '身高'),
        doc7 = doc7,
        doc8 = doc8,
        test1 = replace_basic_doc(stories2, '物理强度'),
        test2 = replace_basic_doc(stories2, '战场机动'),
        test3 = replace_basic_doc(stories2, '生理耐受'),
        test4 = replace_basic_doc(stories2, '战术规划'),
        test5 = replace_basic_doc(stories2, '战斗技巧'),
        test6 = replace_basic_doc(stories2, '源石技艺适应性'),
        data1 = replace_basic_doc(stories3, '体细胞与源石融合率').replace(' ', ''),
        data2 = replace_basic_doc(stories3, '血液源石结晶密度').replace(' ', '')
    )

    stories_list = '\n{{人员档案\n'
    char_stories = stories_table['handbookDict'][char_key]
    for stories_id in range(len(char_stories['storyTextAudio'])):
        storyText = char_stories['storyTextAudio'][stories_id]['stories'][0]['storyText']
        storyText = storyText.replace('\r\n', '<br/>').replace('\n', '<br/>')
        if char_detail['name'] == '伊芙利特':
            storyText = handle_ifrit(storyText)
        storyTitle = char_stories['storyTextAudio'][stories_id]['storyTitle']
        storyCondition_id = char_stories['storyTextAudio'][stories_id]['stories'][0]['unLockType']
        if storyCondition_id == 0:
            storyCondition = '初始开放'
        elif storyCondition_id == 1:
            storyCondition = char_stories['storyTextAudio'][stories_id]['stories'][0]['unLockString']
        elif storyCondition_id == 2:
            storyCondition = replace_story_condition(
                char_stories['storyTextAudio'][stories_id]['stories'][0]['unLockString'],
                char_stories['storyTextAudio'][stories_id]['stories'][0]['unLockParam'])
        stories_list += '|档案' + str(stories_id + 1) + '=' + storyTitle + '\n|档案' + str(
            stories_id + 1) + '条件=' + storyCondition + '\n|档案' + str(stories_id + 1) + '文本=' + storyText + '\n'
    stories_list += '}}'
    return stories_list_set, stories_list


def trans_id(id):
    return {
        1: '一',
        2: '二',
        3: '三',
    }[id]


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


def trans_display_logo(displayLogo):
    try:
        return {
            'logo_abyssal': '深海猎人',
            'logo_blacksteel': '黑钢',
            'logo_kazimierz': '卡西米尔',
            'logo_kjerag': '谢拉格',
            'logo_Laterano': '拉特兰',
            'logo_Leithanien': '莱塔尼亚',
            'logo_lungmen': '龙门',
            'logo_penguin': '企鹅物流',
            'logo_rhine': '莱茵生命',
            'logo_rhodes': '罗德岛',
            'logo_rim': '雷姆必拓',
            'logo_ursus': '乌萨斯',
            'logo_victoria': '维多利亚',
            'logo_siesta': '汐斯塔',
            'logo_yan': '炎国',
            'logo_babel': '巴别塔',
        }[displayLogo]
    except:
        print('出现未知logo: {}.'.format(displayLogo))
        return '未知logo'


def trans_skill_type(skillType):
    return {
        0: '',
        1: '\n|技能类型2=手动触发',
        2: '\n|技能类型2=自动触发',
    }[skillType]


def trans_sp_type(spType):
    return {
        1: '自动回复',
        2: '攻击回复',
        4: '受击回复',
        8: '被动',
    }[spType]


def trans_position(position):
    return {
        'MELEE': '近战位',
        'RANGED': '远程位',
        'ALL': '近战/远程位'
    }[position]


def replace_upper(text):
    p1 = r"(.*)({[A-Z][_A-Z]+)(.*)"
    pattern = re.compile(p1)
    result = re.search(pattern, text)
    if result:
        text = result.group(1) + result.group(2).lower() + result.group(3)
        text = replace_upper(text)
    return text


def replace_key(text):
    p1 = r"(.*)\{([^\:\}]*)(.*)"
    pattern = re.compile(p1)
    result = re.search(pattern, text)
    if result:
        text = replace_key(result.group(1)) + '{' + result.group(2).replace('.', '').replace(']', '').replace('[',
                                                                                                              '') + replace_key(
            result.group(3))
    return text


def replace_basic_desc(text):
    p1 = r"(.*)<\@ba\.kw>(.*)<\/>(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + '{{color|#00B0FF|' + result.group(2) + '}}' + result.group(3)
        text = replace_basic_desc(text)
        # print(result.groups())
    return text


def replace_talpu(text):
    p1 = r"(.*)<\@ba\.talpu>(.*)<\/>(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + '{{color|#F49800|' + result.group(2) + '}}' + result.group(3)
        text = replace_talpu(text)
        # print(result.groups())
    return text


def replace_story_condition(text, num):
    p1 = r"(.*)信赖(.*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        text = result.group(1) + '信赖至' + str(num) + '%' + result.group(2)
        # print(result.groups())
    return text


def replace_basic_doc(text, cond):
    p1 = r"【{doc}】(\s*)([^\n]*)".format(doc = cond)
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        return result.group(2).rstrip()
    return ''


def replace_doc_exp(text):
    p1 = r"【([^【]*)经验】(\s*)([^\n]*)"
    pattern1 = re.compile(p1)
    result = re.search(pattern1, text)
    if result:
        return result.group(1) + '经验', result.group(3).rstrip()
    return '', ''


def handle_ifrit(text):
    text = text.replace('|', '<nowiki>|</nowiki>')
    text = text.replace('=', '<nowiki>=</nowiki>')
    return text


def get_tal_condition(potentialRank, phase, level):
    condition = ''
    if phase == 0:
        condition += '精英0'
    elif phase == 1:
        condition += '精英1'
    elif phase == 2:
        condition += '精英2'
    if level != 1:
        condition += ' ' + str(level) + '级'
    if potentialRank != 0:
        condition += ' 潜能' + str(potentialRank + 1)
    return condition


def create_char(se, url, old_num, character_table, skill_table, building_data, item_table, team_table, gamedata_const, stories_table, skin_table, id_table):
    content = '''{{{{pathnav2|干员一览}}}}
{{{{ads/normal}}}}{{{{ads/mobile}}}}
==干员信息==
{basic_info}
==获得方式==
{{{{干员获得方式}}}}
==属性==
{phases_data}
==攻击范围==
{range_data}
==天赋==
{talents}
==潜能提升==
{potential}
==技能=={skill}
==后勤技能==
{building}
{token_info}
==精英化材料==
{phase}
==技能升级材料==
{skill_levelup}
==相关道具==
{related_item}
==干员档案==
{stories}
==语音记录==
{{{{参阅三|{{{{FULLPAGENAME}}}}|yy}}}}
{{{{:{{{{FULLPAGENAME}}}}/语音记录}}}}
==干员模型==
{{{{doll}}}}
==注释与链接==
<references/>
{{{{干员导航}}}}'''

    fin = ''
    for char in character_table:
        char_detail = character_table[char]
        if (char_detail['name'] in id_table and old_num >= int(id_table[char_detail['name']]['id'])) or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        # if char_detail['name'] not in ['煌', '温蒂'] or char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
        # if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            if char_detail['name'] not in id_table and char_detail['profession'] not in ['TRAP', 'TOKEN']:
                print('Missing New Character {}!'.format(char_detail['name']))
            continue

        # fin2 = read_wiki_repeat(se, url, char_detail['name'])

        update_token_page = False

        basic_info = get_basic_info(char_detail, char, team_table, gamedata_const, stories_table, skin_table, id_table)
        phases_data = get_phases_data(char_detail)
        range_data = get_range_data(char_detail)
        talent_list = get_talent_list(char_detail)
        potential_list = get_potential_list(char_detail)
        skill_list = get_skill_list(char_detail, skill_table, gamedata_const)
        building_skill = get_building_skill(building_data, char)
        token_info = get_token_info(char_detail, update_token_page, character_table)
        phase_list = get_phase_list(char_detail, item_table, gamedata_const)
        skill_levelUp_list = get_skill_levelUp_list(char_detail, skill_table, item_table)
        related_item = get_related_item(char_detail, item_table)
        stories_list_set, stories_list = get_stories_list(char_detail, stories_table, char)
        stories_list = stories_list_set + stories_list

        char_info = content.format(
            name = char_detail['name'],
            basic_info = basic_info,
            phases_data = phases_data,
            range_data = range_data,
            talents = talent_list,
            potential = potential_list,
            skill = skill_list,
            building = building_skill,
            token_info = token_info,
            phase = phase_list,
            skill_levelup = skill_levelUp_list,
            related_item = related_item,
            stories = stories_list
        )
        fin = char_info

        # num1 = fin2.find('==属性==')
        # num2 = fin2.find('==攻击范围==')
        # fin = fin2[:num1] + '==属性==\n' + phases_data + '\n' + fin2[num2:]

        write_wiki_minor(se, url, char_detail['name'], fin, '')
        # print(fin)
        print('Create: {}.'.format(char_detail['name']))

        redirect_text = '#redirect [[{}]]'.format(char_detail['name'])
        write_wiki(se, url, char_detail['appellation'], redirect_text, '')
