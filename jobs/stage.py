import json

from utils.job import Job
from utils.richTextStyles import RichTextStyles


def parse_stage_type(stage_type):
    try:
        return {
            'MAIN': '主线',
            'SUB': '支线',
            'DAILY': '日常',
            'GUIDE': '教程',
            'ACTIVITY': '活动',
            'CAMPAIGN': '剿灭',
            'SPECIAL_STORY': '特殊剧情'
        }[stage_type]
    except:
        print('Unknown stage_type', stage_type)
        return '未知类型'


def parse_drop_type(drop_type):
    return {
        0: 'None',
        1: '首次掉落',
        2: '常规掉落',
        3: '特殊掉落',
        4: '额外物资',
        5: '作战失败返回',
        6: '报酬',  # 剿灭给的合成玉
        7: '幸运掉落',  # 家具
        8: '三星获得'
    }[drop_type]


def parse_occ_type(occ_percent, drop_type, if_furni):
    if if_furni:
        ex = ':2='
    else:
        ex = ':'
    if drop_type in [4, 6, 7]:
        return ''
    elif drop_type == 8:
        return ex + '三星获得'
    elif drop_type == 1:
        return ex + '首次掉落'
    else:
        return ex + {
            0: '固定掉落',  # Always
            1: '大概率',  # Almost
            2: '概率掉落',  # Usual
            3: '小概率',  # Often
            4: '罕见',  # Sometimes
            5: '从不',  # Never
            6: '完成'  # Complete
        }[occ_percent]


def parse_rune_profession(professionMask):
    if professionMask == 0:
        return '未知职业范围'
    p_list = bin(professionMask)[2:]
    p_list = '0' * (10 - len(p_list)) + p_list
    p_text = []
    if p_list[0] == '1':
        p_text.append('先锋')
    if p_list[1] == '1':
        p_text.append('障碍物')
    if p_list[2] == '1':
        p_text.append('召唤物')
    if p_list[3] == '1':
        p_text.append('特种')
    if p_list[4] == '1':
        p_text.append('术师')
    if p_list[5] == '1':
        p_text.append('辅助')
    if p_list[6] == '1':
        p_text.append('医疗')
    if p_list[7] == '1':
        p_text.append('重装')
    if p_list[8] == '1':
        p_text.append('狙击')
    if p_list[9] == '1':
        p_text.append('近卫')
    return '和'.join(p_text) + '干员'


def parse_rune(runes):
    runes_text = []
    for rune in runes:
        text = []
        if rune['difficultyMask'] == 2:  # 突袭
            pass
        elif rune['difficultyMask'] == 1:  # 普通
            text.append('普通难度')
        elif rune['difficultyMask'] == 0:  # 未知
            text.append('未知关卡难度')

        if rune['buildableMask'] == 3:  # 全部单位
            pass
        elif rune['buildableMask'] == 2:  # 远程单位
            text.append('远程单位')
        elif rune['buildableMask'] == 1:  # 近战单位
            text.append('近战单位')
        elif rune['buildableMask'] == 0:  # 未知
            text.append('未知单位')

        if rune['professionMask'] != 1023:
            text.append(parse_rune_profession(rune['professionMask']))
        text.append(rune['key'])

        blackboard = []
        for i in rune['blackboard']:
            text2 = '{}: {}'.format(i['key'], i['value'])
            if i['valueStr'] != None:
                text2 += ' ({})'.format(i['valueStr'])
            blackboard.append(text2)

        runes_text.append(' '.join(text) + ': ' + ', '.join(blackboard) + '\n')
    return ''.join(runes_text)


def parse_drop_item(drop_item, character_table, building_data, item_table):
    try:
        if drop_item['type'] == 'CHAR':
            return character_table[drop_item['id']]['name']
        elif drop_item['type'] == 'FURN':
            return building_data['customData']['furnitures'][drop_item['id']]['name']
        elif drop_item['type'] in ['MATERIAL', 'CARD_EXP', 'TKT_RECRUIT', 'GOLD', 'ACTIVITY_COIN', 'ACTIVITY_ITEM',
            'ET_STAGE', 'DIAMOND', 'DIAMOND_SHD', 'LGG_SHD', 'HGG_SHD']:
            return item_table['items'][drop_item['id']]['name'].rstrip()
        else:
            print('Unknown drop item {}'.format(drop_item['id']))
            return item_table['items'][drop_item['id']]['name'].rstrip()
    except:
        return '物品{}'.format(drop_item['id'])


def parse_overwritten_data(overwritten_data, count):
    return_data = ''
    if overwritten_data['name']['m_defined'] == True:
        return_data += '|敌人{count}显示名={value}\n'.format(
            count = count,
            value = overwritten_data['name']['m_value']
        )
    if overwritten_data['attributes']['maxHp']['m_defined'] == True:
        return_data += '|敌人{count}生命值={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['maxHp']['m_value']
        )
    if overwritten_data['attributes']['atk']['m_defined'] == True:
        return_data += '|敌人{count}攻击力={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['atk']['m_value']
        )
    if overwritten_data['attributes']['def']['m_defined'] == True:
        return_data += '|敌人{count}防御力={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['def']['m_value']
        )
    if overwritten_data['attributes']['magicResistance']['m_defined'] == True:
        return_data += '|敌人{count}法术抗性={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['magicResistance']['m_value']
        )
    if overwritten_data['attributes']['baseAttackTime']['m_defined'] == True:
        return_data += '|敌人{count}攻击间隔={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['baseAttackTime']['m_value']
        )
    if overwritten_data['attributes']['massLevel']['m_defined'] == True:
        return_data += '|敌人{count}重量等级={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['massLevel']['m_value']
        )
    if overwritten_data['attributes']['moveSpeed']['m_defined'] == True:
        return_data += '|敌人{count}移动速度={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['moveSpeed']['m_value']
        )
    if overwritten_data['attributes']['hpRecoveryPerSec']['m_defined'] == True:
        return_data += '|敌人{count}生命恢复速度={value}\n'.format(
            count = count,
            value = overwritten_data['attributes']['hpRecoveryPerSec']['m_value']
        )
    if overwritten_data['rangeRadius']['m_defined'] == True:
        return_data += '|敌人{count}攻击范围半径={value}\n'.format(
            count = count,
            value = overwritten_data['rangeRadius']['m_value']
        )
    return return_data


def analyze_rewards(rewards, character_table, building_data, item_table):
    reward_list = [[], [], [], [], [], [], [], [], []]
    for reward in rewards:
        if reward['type'] == 'FURN':
            reward_item = ':家具=yes:1={name}{occ_type}'.format(
                name = parse_drop_item(reward, character_table, building_data, item_table),
                occ_type = parse_occ_type(reward['occPercent'], reward['dropType'], True)
            )
        else:
            reward_item = '{name}{occ_type}'.format(
                name = parse_drop_item(reward, character_table, building_data, item_table),
                occ_type = parse_occ_type(reward['occPercent'], reward['dropType'], False)
            )
        reward_list[reward['dropType']].append(reward_item)
    reward_list[1] = reward_list[8] + reward_list[1]
    reward_list[8] = []

    rewards_data = ''
    for drop_type in range(9):
        if reward_list[drop_type] != []:
            rewards_data += '|{drop_type}={content}\n'.format(
                drop_type = parse_drop_type(drop_type),
                content = ','.join(reward_list[drop_type])
            )
    return rewards_data


def analyze_level_info(level_table):
    level_info = ''
    level_info += '|部署上限={}\n'.format(level_table['options']['characterLimit'])
    level_info += '|初始COST={}\n'.format(level_table['options']['initialCost'])
    level_info += '|COST上限={}\n'.format(level_table['options']['maxCost'])
    level_info += '|目标点耐久={}\n'.format(level_table['options']['maxLifePoint'])
    enemy_count = 0
    min_time = 0.0
    for wave in level_table['waves']:
        min_time += wave['preDelay'] + wave['postDelay']
        for fragment in wave['fragments']:
            min_time += fragment['preDelay']
            min_time += max(
                [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']])
            for unit in fragment['actions']:
                if unit['actionType'] == 0 and unit['key'] != '':
                    enemy_count += unit['count']
    level_info += '|敌人数量={}\n'.format(enemy_count)
    level_info += '|地图大小={}×{}\n'.format(level_table['mapData']['width'], level_table['mapData']['height'])
    if abs(min_time - int(min_time)) < 0.0001:
        level_info += '|最短用时={}分{}秒\n'.format(int(min_time / 60), int(min_time % 60))
    else:
        level_info += '|最短用时={}分{:.1f}秒\n'.format(int(min_time / 60), min_time % 60)
    return level_info


def analyze_char_card_info(level_table, stage_page_name, character_table, skill_table):
    char_pre = ''
    favor_point = []
    try:
        for char_card in level_table['predefines']['characterCards']:
            char_card_name = character_table[char_card['inst']['characterKey']]['name']
            if char_card['skillIndex'] != -1:
                skill_name = skill_table[
                    character_table[char_card['inst']['characterKey']]['skills'][char_card['skillIndex']][
                        'skillId']]['levels'][0]['name']
            else:
                skill_name = ''
            char_pre += '{{{{编队单位|{}|{}|{}|{}|{}'.format(
                char_card_name,
                char_card['inst']['phase'],
                char_card['inst']['level'],
                skill_name,
                char_card['mainSkillLvl'],
            )
            if char_card['inst']['potentialRank'] != 0:
                char_pre += '||{}'.format(char_card['inst']['potentialRank'] + 1)
            char_pre += '}}'
            favor_point.append('{}信赖为{}'.format(char_card_name, char_card['inst']['favorPoint'] * 2))
        if char_pre != '':
            char_pre = '''
==固定编队==
{{| class="wikitable hlist logo mw-collapsed mw-collapsible" style="text-align:center; width:567px; white-space:normal;"
!style="background-color:#0098DC;color:#FFFFFF"|固定编队
|-
|{}
|-
!备注
|-
|{}
|}}'''.format(char_pre, '，'.join(favor_point))
    except:
        print(stage_page_name, 'characterCards error.')

    return char_pre

def get_enemy_data(level_table, enemy_table, enemy_database):
    enemy_data = '\n==敌方情报==\n{{敌方情报\n'
    count = 1
    enemy_num_dict = {}
    for wave in level_table['waves']:
        for fragment in wave['fragments']:
            for unit in fragment['actions']:
                if unit['actionType'] == 0:
                    if unit['key'] not in enemy_num_dict:
                        enemy_num_dict[unit['key']] = unit['count']
                    else:
                        enemy_num_dict[unit['key']] += unit['count']
    for enemy in level_table['enemyDbRefs']:
        if enemy['id'] not in enemy_num_dict:
            continue
        if enemy['useDb'] == False:
            enemy_data += '|敌人{count}={name}\n'.format(
                count = count,
                name = enemy['overwrittenData']['name']['m_value']
            )
            enemy_data += '|敌人{count}数量={enemy_num}\n'.format(
                count = count,
                enemy_num = enemy_num_dict[enemy['id']]
            )
            enemy_data += '|敌人{count}级别={level}\n'.format(
                count = count,
                level = enemy['level']
            )
            enemy_data += '|敌人{}备注=需人工复查！\n'.format(count)
        else:
            if enemy['id'] in enemy_table:
                enemy_name = enemy_table[enemy['id']]['name']
                if enemy_name in ['W', '泥岩']:
                    enemy_data += '|敌人{count}={name}(敌方)\n|敌人{count}显示名={name}\n'.format(
                        count = count,
                        name = enemy_name
                    )
                else:
                    enemy_data += '|敌人{count}={name}\n'.format(
                        count = count,
                        name = enemy_name
                    )
            else:
                enemy_name = ''
                for enemy_content in enemy_database['enemies']:
                    if enemy_content['Key'] == enemy['id']:
                        enemy_name = enemy_content['Value'][0]['enemyData']['name']['m_value']
                enemy_data += '|敌人{count}={name}\n'.format(
                    count = count,
                    name = enemy_name
                )
            enemy_data += '|敌人{count}数量={enemy_num}\n'.format(
                count = count,
                enemy_num = enemy_num_dict[enemy['id']]
            )
            enemy_data += '|敌人{count}级别={level}\n'.format(
                count = count,
                level = enemy['level']
            )
            if enemy['overwrittenData'] != None:
                enemy_data += parse_overwritten_data(enemy['overwrittenData'], count)
        count += 1
    enemy_data += '}}'
    return enemy_data


def get_normal_data(stage_detail, stage_table, zone_table, character_table, building_data, item_table, level_table,
        rts):
    stage_data = '\n==普通==\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    if stage_detail['hilightMark'] == True:
        stage_data += '|子类型=难关\n'
    elif stage_detail['appearanceStyle'] == 4:
        stage_data += '|子类型=绝境\n'
    elif stage_detail['appearanceStyle'] == 5:
        stage_data += '|子类型=迷雾\n'
    if stage_detail['bossMark'] == True:
        stage_data += '|领袖标志=Yes\n'
    stage_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    if stage_detail['levelId'] == None:
        stage_data += '|战斗关卡=false\n'
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        unlock_cond = '{num}星通关[[{code} {name}]]'.format(
            num = unlock_id['completeState'],
            code = stage_table['stages'][unlock_id['stageId']]['code'],
            name = stage_table['stages'][unlock_id['stageId']]['name']
        )
        unlock_cond_list.append(unlock_cond)
    stage_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    stage_data += '|推荐等级={}\n'.format(stage_detail['dangerLevel'])
    if zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst']:
        stage_data += '|所属区域={name_1} {name_2}\n'.format(
            name_1 = zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst'],
            name_2 = zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    else:
        stage_data += '|所属区域={name_2}\n'.format(
            name_2 = zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if stage_detail['description']:
        stage_data += '|关卡描述={desc}\n'.format(
            desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
        )
    else:
        stage_data += '|关卡描述=\n'
    stage_data += '|作战消耗={}\n'.format(stage_detail['apCost'])
    if stage_detail['canPractice'] == True:
        stage_data += '|演习消耗={}\n'.format(stage_detail['practiceTicketCost'])
    else:
        stage_data += '|演习消耗=-1\n'
    if stage_detail['stageDropInfo']['displayDetailRewards']:
        stage_data += analyze_rewards(stage_detail['stageDropInfo']['displayDetailRewards'], character_table,
            building_data, item_table)
    if stage_detail['levelId']:
        if 'tags' in level_table['mapData'] and level_table['mapData']['tags'] != None:
            stage_data += '|地形tag={}\n'.format(','.join(level_table['mapData']['tags']))
    stage_data += '}}'

    return stage_data


def get_4star_data(stage_detail, stage_table, zone_table, character_table, building_data, item_table, level_table, rts):
    stage_4star_data = '\n==突袭==\n{{突袭关卡信息\n'
    stage_4star_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_4star_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_4star_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    stage_4star_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        if stage_table['stages'][unlock_id['stageId']]['code'] != stage_detail['code']:
            unlock_cond = '{num}星通关[[{code} {name}]]'.format(
                num = unlock_id['completeState'],
                code = stage_table['stages'][unlock_id['stageId']]['code'],
                name = stage_table['stages'][unlock_id['stageId']]['name']
            )
        else:
            unlock_cond = '{num}星通关[[#普通|{code} {name}]]普通难度'.format(
                num = unlock_id['completeState'],
                code = stage_table['stages'][unlock_id['stageId']]['code'],
                name = stage_table['stages'][unlock_id['stageId']]['name']
            )
        unlock_cond_list.append(unlock_cond)
    stage_4star_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    stage_4star_data += '|推荐等级={}\n'.format(stage_detail['dangerLevel'])
    if zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst']:
        stage_4star_data += '|所属区域={name_1} {name_2}\n'.format(
            name_1 = zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst'],
            name_2 = zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    else:
        stage_4star_data += '|所属区域={name_2}\n'.format(
            name_2 = zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    climit = 0
    ebuff = {'atk': 1.0, 'def': 1.0, 'max_hp': 1.0, 'flag': 0}
    for rune in level_table['runes']:
        if rune['key'] in ['gbuff_placable_char_num', 'global_placable_char_num_add']:
            climit = int(rune['blackboard'][0]['value'])
        if rune['key'] in ['enemy_attribute_mul', 'ebuff_attribute']:
            ebuff['flag'] = 1
            for i in rune['blackboard']:
                ebuff[i['key']] = i['value']
    stage_4star_data += '|部署上限={}\n'.format(level_table['options']['characterLimit'] + climit)
    stage_4star_data += '|初始COST={}\n'.format(level_table['options']['initialCost'])
    stage_4star_data += '|COST上限={}\n'.format(level_table['options']['maxCost'])
    stage_4star_data += '|关卡描述={desc}\n'.format(
        desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
    )
    stage_4star_data += '|作战消耗={}\n'.format(stage_detail['apCost'])
    if stage_detail['canPractice'] == True:
        stage_4star_data += '|演习消耗={}\n'.format(stage_detail['practiceTicketCost'])
    else:
        stage_4star_data += '|演习消耗=-1\n'
    if stage_detail['stageDropInfo']['displayDetailRewards']:
        stage_4star_data += analyze_rewards(stage_detail['stageDropInfo']['displayDetailRewards'], character_table,
            building_data, item_table)
    stage_4star_data += '<!--|情报=\n'
    if ebuff['flag'] == 1:
        ebuff_desc = []
        if ebuff['atk'] != 1.0:
            ebuff_desc.append('攻击力提升至{0:.0%}'.format(ebuff['atk']))
        if ebuff['def'] != 1.0:
            ebuff_desc.append('防御力提升至{0:.0%}'.format(ebuff['def']))
        if ebuff['max_hp'] != 1.0:
            ebuff_desc.append('生命值提升至{0:.0%}'.format(ebuff['max_hp']))
        if ebuff_desc != []:
            stage_4star_data += '敌方单位的' + '，'.join(ebuff_desc) + '\n'
        else:
            stage_4star_data += '敌方单位无变化\n'
    stage_4star_data += parse_rune(level_table['runes'])
    stage_4star_data += '-->\n}}'

    return stage_4star_data


def get_campaign_data(stage_detail, stage_table, campaign_table, character_table, building_data, item_table, level_table, rts):
    stage_data = '\n==关卡==\n{{剿灭关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    if '_r_' in stage_detail['stageId']:
        stage_data += '|剿灭委托=true\n'
    stage_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    stage_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        unlock_cond = '{num}星通关[[{code} {name}]]'.format(
            num = unlock_id['completeState'],
            code = stage_table['stages'][unlock_id['stageId']]['code'],
            name = stage_table['stages'][unlock_id['stageId']]['name']
        )
        unlock_cond_list.append(unlock_cond)
    stage_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    if stage_detail['zoneId'] in campaign_table['campaignZones']:
        stage_data += '|所属区域={name}\n'.format(
                name = campaign_table['campaignZones'][stage_detail['zoneId']]['name']
            )
    else:
        stage_data += '|所属区域=NONE\n'
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if stage_detail['description']:
        stage_data += '|关卡描述={desc}\n'.format(
            desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
        )
    else:
        stage_data += '|关卡描述=\n'
    stage_data += '|作战消耗={}\n'.format(stage_detail['apCost'])
    campaign_detail = campaign_table['campaigns'][stage_detail['stageId']]
    if campaign_detail['dropGains']['PERMANENT']['gainLadders'] != []:
        gain_flag = 'PERMANENT'
    else:
        gain_flag = 'ROTATE'
    if campaign_detail['dropGains'][gain_flag]['displayDetailRewards']:
        stage_data += analyze_rewards(campaign_detail['dropGains'][gain_flag]['displayDetailRewards'], character_table,
            building_data, item_table)
    for idx, ladder in enumerate(campaign_detail['dropGains'][gain_flag]['gainLadders'], start = 1):
        stage_data += '|理智返还{}=+{}\n'.format(idx, ladder['apFailReturn'])
    for idx, ladder in enumerate(campaign_detail['dropGains'][gain_flag]['gainLadders'], start = 1):
        if ladder['displayDiamondShdNum'] == 0:
            stage_data += '|合成玉获得{}=+{}\n'.format(idx, ladder['displayDiamondShdNum'])
        else:
            stage_data += '|合成玉获得{}=+约{}\n'.format(idx, ladder['displayDiamondShdNum'])
    if stage_detail['levelId']:
        if 'tags' in level_table['mapData'] and level_table['mapData']['tags'] != None:
            stage_data += '|地形tag={}\n'.format(','.join(level_table['mapData']['tags']))
    stage_data += '}}'

    return stage_data


def get_crisis_data(stage_detail, level_table, rts):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡类型={}\n'.format('活动')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    stage_data += '|解锁条件={}\n'.format('—')
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format(stage_detail['code'])
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if 'description' in stage_detail:
        stage_desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))  # crisis_info
    elif 'desc' in stage_detail:
        stage_desc = rts.compile(stage_detail['desc'].replace('\\n', '<br/>'))  # weedy
    else:
        stage_desc = ''
    stage_data += '|关卡描述={desc}\n'.format(
        desc = stage_desc
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    stage_data += '}}'

    return stage_data


def get_roguelike_data(stage_detail, level_table, rts):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡id={}\n'.format(stage_detail['id'])
    stage_data += '|关卡类型={}\n'.format('活动')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    stage_data += '|解锁条件={}\n'.format('—')
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format('—')
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    stage_data += '|关卡描述={desc}\n'.format(
        desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    stage_data += '}}'

    return stage_data


def get_roguelike_4star_data(stage_detail, level_table, rts):
    stage_4star_data = '\n==紧急作战==\n{{突袭关卡信息\n'
    stage_4star_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_4star_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_4star_data += '|关卡类型={}\n'.format('活动')
    stage_4star_data += '|子类型={}\n'.format('紧急作战')
    stage_4star_data += '|关卡难度={}\n'.format('FOUR_STAR')
    stage_4star_data += '|解锁条件={}\n'.format('-')
    stage_4star_data += '|所属区域={}\n'.format('-')
    climit = 0
    ebuff = {'atk': 1.0, 'def': 1.0, 'max_hp': 1.0, 'flag': 0}
    for rune in level_table['runes']:
        if rune['key'] in ['gbuff_placable_char_num', 'global_placable_char_num_add']:
            climit = int(rune['blackboard'][0]['value'])
        if rune['key'] in ['enemy_attribute_mul', 'ebuff_attribute']:
            ebuff['flag'] = 1
            for i in rune['blackboard']:
                ebuff[i['key']] = i['value']
    stage_4star_data += '|部署上限={}\n'.format(level_table['options']['characterLimit'] + climit)
    stage_4star_data += '|初始COST={}\n'.format(level_table['options']['initialCost'])
    stage_4star_data += '|COST上限={}\n'.format(level_table['options']['maxCost'])
    stage_4star_data += '|关卡描述={desc}\n'.format(
        desc = rts.compile(stage_detail['eliteDesc'].replace('\\n', '<br/>'))
    )
    stage_4star_data += '|作战消耗={}\n'.format(0)
    stage_4star_data += '|演习消耗=-1\n'
    stage_4star_data += '<!--|情报=\n'
    if ebuff['flag'] == 1:
        ebuff_desc = []
        if ebuff['atk'] != 1.0:
            ebuff_desc.append('攻击力提升至{0:.0%}'.format(ebuff['atk']))
        if ebuff['def'] != 1.0:
            ebuff_desc.append('防御力提升至{0:.0%}'.format(ebuff['def']))
        if ebuff['max_hp'] != 1.0:
            ebuff_desc.append('生命值提升至{0:.0%}'.format(ebuff['max_hp']))
        if ebuff_desc != []:
            stage_4star_data += '敌方单位的' + '，'.join(ebuff_desc) + '\n'
        else:
            stage_4star_data += '敌方单位无变化\n'
    stage_4star_data += '-->\n}}'

    return stage_4star_data


def get_memory_data(stage_detail, level_table, rts, character_table, building_data, item_table):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format('悖论模拟')
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format('悖论模拟')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    unlock_cond = ''
    for p in stage_detail['unlockParam']:
        if unlock_cond != '':
            unlock_cond += '，'
        if p['unlockType'] == 1:
            unlock_cond += '提升至精英阶段{}等级{}'.format(p['unlockParam1'], p['unlockParam2'])
        elif p['unlockType'] == 2:
            unlock_cond += '提升信赖至{}'.format(p['unlockParam1'])
        else:
            print('Unknown unlockType', p['unlockType'])
    unlock_cond = '干员\'\'\'[[{}]]\'\'\''.format(character_table[stage_detail['charId']]['name']) + unlock_cond
    stage_data += '|解锁条件={}\n'.format(unlock_cond)
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format(stage_detail['zoneId'])
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    stage_data += '|关卡描述={desc}\n'.format(
        desc = rts.compile(stage_detail['description'].replace('\n', '<br/>'))
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    reward_item = ['{}:三星获得'.format(parse_drop_item(r, character_table, building_data, item_table)) for r in stage_detail['rewardItem']]
    stage_data += '|首次掉落=' + ','.join(reward_item) + '\n'
    stage_data += '}}'

    return stage_data


class Stage(Job):
    def _run(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        stage_table = self.getgd('excel/stage_table.json')
        zone_table = self.getgd('excel/zone_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:普通难度关卡')
        # stage_list = self.wiki.category('分类:剿灭关卡')
        new_stage_list = []

        for stage_id in stage_table['stages']:
            stage_detail = stage_table['stages'][stage_id]
            if stage_detail['stageType'] not in ['MAIN', 'SUB', 'DAILY', 'ACTIVITY', 'SPECIAL_STORY'] or stage_detail[
                'difficulty'] == 'FOUR_STAR':
            # if stage_detail['stageType'] not in ['CAMPAIGN'] or stage_detail['difficulty'] == 'FOUR_STAR':
                continue
            stage_page_name = stage_detail['code'] + ' ' + stage_detail['name'].rstrip()
            if stage_page_name in stage_list:
                continue
            # if stage_detail['code'] not in ['GT-HX-3']:
            #     continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_normal_data(stage_detail, stage_table, zone_table, character_table, building_data,
                item_table, level_table, rts)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''
            stage_4star_data = get_4star_data(stage_table['stages'][stage_detail['hardStagedId']], stage_table,
                zone_table, character_table, building_data, item_table, level_table, rts) if stage_detail[
                'hardStagedId'] else ''
            if len(list(filter(lambda x:x['dropType'] in [2,3,4], stage_detail['stageDropInfo']['displayDetailRewards']))) > 0:
                stage_drop = '\n==材料掉落==\n{{关卡材料掉落}}'
            else:
                stage_drop = ''
            char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table)

            stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_4star_data + stage_enemy_data + char_pre + stage_drop + '\n==注释与链接==\n<references/>\n{{关卡导航}}'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title = stage_detail['code'],
                text = stage_redirect,
                summary = 'init',
                createonly = '1'
            )
            self.wiki.edit(
                title = stage_page_name,
                text = stage_content,
                summary = 'init',
                bot = None,
                minor = True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

            new_stage_list.append('* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title = '首页/新增关卡',
                text = '\n'.join(new_stage_list),
                summary = 'init',
                bot = None,
                minor = True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def _run_campaign(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        stage_table = self.getgd('excel/stage_table.json')
        campaign_table = self.getgd('excel/campaign_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:剿灭关卡')
        new_stage_list = []

        for stage_id in stage_table['stages']:
            stage_detail = stage_table['stages'][stage_id]
            if stage_detail['stageType'] != 'CAMPAIGN':
                continue
            stage_page_name = stage_detail['code'] + ' ' + stage_detail['name'].rstrip()
            if stage_page_name in stage_list:
                continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_campaign_data(stage_detail, stage_table, campaign_table, character_table, building_data, item_table, level_table, rts)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''
            char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table)
            rewards = '''\n==作战进度奖励==
{| class="wikitable mw-collapsible mw-collapsed" style="text-align:center;width:600px;"
!style="width:200px;color:white;font-weight:bold;background-color:#575757;"|击溃人数
!style="width:400px;color:white;font-weight:bold;background-color:#575757;"|奖励'''
            for r in campaign_table['campaigns'][stage_detail['stageId']]['breakLadders']:
                items = ' '.join([
                    '{{{{材料消耗|{}|{}}}}}'.format(
                        parse_drop_item(rw, character_table, building_data, item_table),
                        rw['count']
                    ) for rw in r['rewards']
                ])
                rewards += '\n|-\n|{}||{}'.format(
                    r['killCnt'],
                    items
                )
                if r['breakFeeAdd'] != 0:
                    rewards += ' {{材料消耗|合成玉|i+}}(+' + str(r['breakFeeAdd']) + ')'
            rewards += '\n|}'

            stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_enemy_data + char_pre + rewards + '\n==注释与链接==\n<references/>\n{{关卡导航}}'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title = stage_detail['name'],
                text = stage_redirect,
                summary = 'init',
                createonly = '1'
            )
            self.wiki.edit(
                title = stage_page_name,
                text = stage_content,
                summary = 'init',
                bot = None,
                minor = True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

            new_stage_list.append('* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title = '首页/新增关卡',
                text = '\n'.join(new_stage_list),
                summary = 'init',
                bot = None,
                minor = True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def _run_crisis(self):
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        # 从 crisis_info 读
        with open('crisis_info.json', 'r', encoding = 'utf-8') as file:
            stage_table = json.loads(file.read())
        for stage_key in stage_table['data']['seasonInfo'][0]['stages']:
            stage_detail = stage_table['data']['seasonInfo'][0]['stages'][stage_key]

            # 从 weedy 读
            # session = requests.Session()
            # stage_list = session.get('https://weedy.baka.icu/crisis/today').json()['stages']
            # stage_list = [stage_list[0]]
            # for stage_key in stage_list:
            #     stage_detail = stage_key
            #     stage_detail['levelId'] = 'Obt/rune/level_rune_04-01'

            stage_page_name = stage_detail['code'] + ' ' + stage_detail['name'].rstrip()

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_crisis_data(stage_detail, level_table, rts)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''

            stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_enemy_data + '\n==合约详情==\n{{合约详情}}\n==注释与链接==\n<references/>\n{{关卡导航}}\n[[分类:危机合约关卡]]'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title = stage_detail['name'],
                text = stage_redirect,
                summary = 'init',
                createonly = '1'
            )
            self.wiki.edit(
                title = stage_page_name,
                text = stage_content,
                summary = 'init',
                bot = None,
                minor = True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

    def _run_rogue_like(self):
        roguelike_table = self.getgd('excel/roguelike_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        for stage_key in roguelike_table['stages']:
            stage_detail = roguelike_table['stages'][stage_key]
            if stage_detail['difficulty'] == 'FOUR_STAR':
                continue

            stage_page_name = stage_detail['code'] + ' ' + stage_detail['name'].rstrip()

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_roguelike_data(stage_detail, level_table, rts)
            linkedStage = [k for k in roguelike_table['stages'] if
                roguelike_table['stages'][k]['linkedStageId'] == stage_key]
            if len(linkedStage) >= 1:
                stage_4star_data = get_roguelike_4star_data(roguelike_table['stages'][linkedStage[0]], level_table, rts)
            else:
                stage_4star_data = ''
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''

            stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_4star_data + stage_enemy_data + '\n==注释与链接==\n<references/>\n{{关卡导航}}\n[[分类:集成战略关卡]]'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title = stage_detail['name'],
                text = stage_redirect,
                summary = 'init',
                createonly = '1'
            )
            self.wiki.edit(
                title = stage_page_name,
                text = stage_content,
                summary = 'init',
                bot = None,
                minor = True,
                createonly = '1'
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

    def _run_memory(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        handbook_info_table = self.getgd('excel/handbook_info_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:悖论模拟关卡')
        for stage_detail in handbook_info_table['handbookStageData'].values():
            stage_page_name = '悖论模拟 {}'.format(stage_detail['name'])
            if stage_page_name in stage_list:
                continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_memory_data(stage_detail, level_table, rts, character_table, building_data, item_table)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''
            char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table)

            stage_content = '{{pathnav2|关卡一览}}\n__NOTOC__' + stage_normal_data + stage_enemy_data + char_pre + '\n==注释与链接==\n<references/>\n{{关卡导航}}'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title = stage_detail['name'],
                text = stage_redirect,
                summary = 'init',
                createonly = '1'
            )
            self.wiki.edit(
                title = stage_page_name,
                text = stage_content,
                summary = 'init',
                bot = None,
                minor = True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

    def _run_enemy_data(self, level_table):
        enemy_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        return get_enemy_data(level_table, enemy_table, enemy_database)
