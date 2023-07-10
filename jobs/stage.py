import copy
import json
import os
import re
import requests

from utils.job import Job
from utils.richTextStyles import RichTextStyles


def parse_stage_type(stage_type):
    return {
        'MAIN': '主线',
        'SUB': '支线',
        'DAILY': '日常',
        'GUIDE': '教程',
        'ACTIVITY': '活动',
        'CAMPAIGN': '剿灭',
        'SPECIAL_STORY': '特殊剧情',
        'CLIMB_TOWER': '保全派驻'
    }.get(stage_type, '未知类型')


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
        8: '三星获得',
        'NONE': 'None',
        'ONCE': '首次掉落',
        'NORMAL': '常规掉落',
        'SPECIAL': '特殊掉落',
        'ADDITIONAL': '额外物资',
        'APRETURN': '作战失败返回',
        'DIAMOND_MATERIAL': '报酬',  # 剿灭给的合成玉
        'FUNITURE_DROP': '幸运掉落',  # 家具
        'COMPLETE': '三星获得'
    }.get(drop_type, 'None')


def parse_occ_type(occ_percent, drop_type, if_furni):
    if if_furni:
        ex = ':2='
    else:
        ex = ':'
    if drop_type in [4, 6, 7] or drop_type in ['ADDITIONAL', 'DIAMOND_MATERIAL', 'FUNITURE_DROP']:
        return ''
    elif drop_type == 8 or drop_type == 'COMPLETE':
        return ex + '三星获得'
    elif drop_type == 1 or drop_type == 'ONCE':
        return ex + '首次掉落'
    else:
        return ex + {
            0: '固定掉落',  # Always
            1: '大概率',  # Almost
            2: '概率掉落',  # Usual
            3: '小概率',  # Often
            4: '罕见',  # Sometimes
            5: '从不',  # Never
            6: '完成',  # Complete
            'ALWAYS': '固定掉落',  # Always
            'ALMOST': '大概率',  # Almost
            'USUAL': '概率掉落',  # Usual
            'OFTEN': '小概率',  # Often
            'SOMETIMES': '罕见',  # Sometimes
            'NEVER': '从不',  # Never
            'DEFINITELY_BUFF': '完成'  # Complete
        }.get(occ_percent, '未知类型')


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
            return item_table['items'][drop_item['id']]['name'].strip()
        else:
            print('Unknown drop item {}'.format(drop_item['id']))
            return item_table['items'][drop_item['id']]['name'].strip()
    except:
        return '物品{}'.format(drop_item['id'])


def parse_overwritten_data(overwritten_data, count):
    return_data = ''
    if overwritten_data['name']['m_defined'] == True:
        return_data += '|敌人{count}显示名={value}\n'.format(
            count=count,
            value=overwritten_data['name']['m_value']
        )
    if overwritten_data['attributes']['maxHp']['m_defined'] == True:
        return_data += '|敌人{count}生命值={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['maxHp']['m_value']
        )
    if overwritten_data['attributes']['atk']['m_defined'] == True:
        return_data += '|敌人{count}攻击力={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['atk']['m_value']
        )
    if overwritten_data['attributes']['def']['m_defined'] == True:
        return_data += '|敌人{count}防御力={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['def']['m_value']
        )
    if overwritten_data['attributes']['magicResistance']['m_defined'] == True:
        return_data += '|敌人{count}法术抗性={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['magicResistance']['m_value']
        )
    if overwritten_data['attributes']['baseAttackTime']['m_defined'] == True:
        return_data += '|敌人{count}攻击间隔={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['baseAttackTime']['m_value']
        )
    if overwritten_data['attributes']['massLevel']['m_defined'] == True:
        return_data += '|敌人{count}重量等级={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['massLevel']['m_value']
        )
    if overwritten_data['attributes']['moveSpeed']['m_defined'] == True:
        return_data += '|敌人{count}移动速度={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['moveSpeed']['m_value']
        )
    if overwritten_data['attributes']['hpRecoveryPerSec']['m_defined'] == True:
        return_data += '|敌人{count}生命恢复速度={value}\n'.format(
            count=count,
            value=overwritten_data['attributes']['hpRecoveryPerSec']['m_value']
        )
    if overwritten_data['rangeRadius']['m_defined'] == True:
        return_data += '|敌人{count}攻击范围半径={value}\n'.format(
            count=count,
            value=overwritten_data['rangeRadius']['m_value']
        )
    if overwritten_data['lifePointReduce']['m_defined'] == True:
        return_data += '|敌人{count}目标价值={value}\n'.format(
            count=count,
            value=overwritten_data['lifePointReduce']['m_value']
        )
    return return_data


def analyze_rewards(rewards, character_table, building_data, item_table):
    reward_list = {
        'NONE': [], 'ONCE': [], 'NORMAL': [], 'SPECIAL':[], 'ADDITIONAL':[], 'APRETURN': [], 'DIAMOND_MATERIAL': [],
        'FUNITURE_DROP': [], 'COMPLETE': [], 'CHARM_DROP': [], 'OVERRIDE_DROP': [], 'ITEM_RETURN': []
    }
    for reward in rewards:
        if reward['type'] == 'FURN':
            reward_item = ':家具=yes:1={name}{occ_type}'.format(
                name=parse_drop_item(reward, character_table, building_data, item_table),
                occ_type=parse_occ_type(reward['occPercent'], reward['dropType'], True)
            )
        else:
            reward_item = '{name}{occ_type}'.format(
                name=parse_drop_item(reward, character_table, building_data, item_table),
                occ_type=parse_occ_type(reward['occPercent'], reward['dropType'], False)
            )
        reward_list[reward['dropType']].append(reward_item)
    reward_list['ONCE'] = reward_list['COMPLETE'] + reward_list['ONCE']
    reward_list['COMPLETE'] = []

    rewards_data = ''
    for drop_type in reward_list:
        if reward_list[drop_type] != []:
            reward_content = ','.join(reward_list[drop_type])
            rewards_data += '|{drop_type}={content}\n'.format(
                drop_type=parse_drop_type(drop_type),
                content=reward_content
            )
            if drop_type == 2 or drop_type == 'NORMAL':
                print('\t—— ' + reward_content)
    return rewards_data


def analyze_action(actions, normal_hidden_group):
    action_list = [ActionInfo(action) for action in actions]
    pack_dict = {}
    for action in action_list:
        if action.random_key is not None and action.random_pack is not None:
            if action.random_pack in pack_dict and pack_dict[action.random_pack] != action.random_key:
                print(f"Error: randomSpawnGroupPackKey duplicate! ({action.random_key} - {action.random_pack})")
            pack_dict[action.random_pack] = action.random_key
    for action in action_list:
        action.update_pack(pack_dict)
    min_time, action_enemy_min, action_enemy_max = 0.0, 0, 0
    fragment_flag = False
    time_filter = lambda x: x.hidden_group == None or x.hidden_group in normal_hidden_group
    num_filter = lambda x: (x.key is not None or x.random_key is not None) and (x.hidden_group == None or x.hidden_group in normal_hidden_group)
    time_dict = {'fix_time': -1.0, 'random_group': {}}
    num_dict = {'base_num': 0, 'random_group': {}}
    # 最短用时
    for action in filter(time_filter, action_list):
        fragment_flag = True
        if action.random_key is not None:
            if action.random_key not in time_dict['random_group']:
                time_dict['random_group'][action.random_key] = {'single': 1000000.0, 'pack': {}}
            if action.random_pack is not None:
                if action.random_pack not in time_dict['random_group'][action.random_key]['pack']:
                    time_dict['random_group'][action.random_key]['pack'][action.random_pack] = -1.0
                time_dict['random_group'][action.random_key]['pack'][action.random_pack] = max(action.time, time_dict['random_group'][action.random_key]['pack'][action.random_pack])
            else:
                time_dict['random_group'][action.random_key]['single'] = min(action.time, time_dict['random_group'][action.random_key]['single'])
        else:
            time_dict['fix_time'] = max(action.time, time_dict['fix_time'])
    if time_dict['random_group'] != {}:
        pack_time_list = [0.0]
        for action_k_iter in time_dict['random_group']:
            pack_time = 1000000.0
            if time_dict['random_group'][action_k_iter]['pack'] != {}:
                pack_time = min(pack_time, min(time_dict['random_group'][action_k_iter]['pack'].values()))
            if time_dict['random_group'][action_k_iter]['single'] != {}:
                pack_time = min(pack_time, max(time_dict['random_group'][action_k_iter]['single'], 0))
            pack_time_list.append(pack_time)
        min_time = max(0.0, time_dict['fix_time'], min(pack_time_list))
    else:
        min_time = max(0.0, time_dict['fix_time'])

    # 敌人数量
    for action in filter(num_filter, action_list):
        if action.random_key is not None:
            if action.random_key not in num_dict['random_group']:
                num_dict['random_group'][action.random_key] = {'single': [], 'pack': {}}
            if action.random_pack is not None:
                if action.random_pack not in num_dict['random_group'][action.random_key]['pack']:
                    num_dict['random_group'][action.random_key]['pack'][action.random_pack] = 0
                num_dict['random_group'][action.random_key]['pack'][action.random_pack] += action.count
            else:
                num_dict['random_group'][action.random_key]['single'].append(action.count)
        else:
            num_dict['base_num'] += action.count
    if num_dict['random_group'] != {}:
        for action_k_iter in num_dict['random_group']:
            pack_min, pack_max = 100000, -1
            if num_dict['random_group'][action_k_iter]['pack'] != {}:
                pack_min = min(pack_min, min(num_dict['random_group'][action_k_iter]['pack'].values()))
                pack_max = max(pack_max, max(num_dict['random_group'][action_k_iter]['pack'].values()))
            if num_dict['random_group'][action_k_iter]['single'] != []:
                pack_min = min(pack_min, min(num_dict['random_group'][action_k_iter]['single']))
                pack_max = max(pack_max, max(num_dict['random_group'][action_k_iter]['single']))
            action_enemy_min += pack_min
            action_enemy_max += pack_max
        action_enemy_min += num_dict['base_num']
        action_enemy_max += num_dict['base_num']
    else:
        action_enemy_min = num_dict['base_num']
        action_enemy_max = num_dict['base_num']

    return min_time, action_enemy_min, action_enemy_max, fragment_flag


def analyze_level_info(level_table):
    level_info = ''
    level_info += '|部署上限={}\n'.format(level_table['options']['characterLimit'])
    level_info += '|初始COST={}\n'.format(level_table['options']['initialCost'])
    level_info += '|COST上限={}\n'.format(level_table['options']['maxCost'])
    level_info += '|目标点耐久={}\n'.format(level_table['options']['maxLifePoint'])
    enemy_count = {'min': 0, 'max': 0}
    min_time = 0.0
    normal_hidden_group = analyze_normal_hidden_group(level_table)
    for wave in level_table['waves']:
        min_time += wave['preDelay'] + wave['postDelay']
        for fragment in wave['fragments']:
            time, action_enemy_min, action_enemy_max, fragment_flag = analyze_action(fragment['actions'], normal_hidden_group)
            enemy_count['min'] += action_enemy_min
            enemy_count['max'] += action_enemy_max
            if fragment_flag:
                min_time += fragment['preDelay']
                min_time += time
    if enemy_count['min'] == enemy_count['max']:
        level_info += '|敌人数量={}\n'.format(enemy_count['min'])
    else:
        level_info += '|敌人数量={}~{}\n'.format(enemy_count['min'], enemy_count['max'])
    level_info += '|地图大小={}×{}\n'.format(level_table['mapData']['map'][0].__len__(), level_table['mapData']['map'].__len__())
    if abs(min_time - int(min_time)) < 0.0001:
        level_info += '|最短用时={}分{}秒\n'.format(int(min_time / 60), int(min_time % 60))
    else:
        level_info += '|最短用时={}分{:.1f}秒\n'.format(int(min_time / 60), min_time % 60)
    return level_info


def analyze_normal_hidden_group(level_table):
    normal_hidden_group = []
    if level_table['runes']:
        try:
            for rune in level_table['runes']:
                if rune['difficultyMask'] == 1 and rune['key'] == 'level_hidden_group_enable':
                    for d in rune['blackboard']:
                        if d['key'] == 'key':
                            normal_hidden_group.append(d['valueStr'])
        except:
            print('hiddenGroup解析出错.')
    return normal_hidden_group


def analyze_char_card_info(level_table, stage_page_name, character_table, skill_table, stage_charId = None):
    char_pre, memory_desc = '', ''
    favor_point, fp_set = [], set()
    try:
        if level_table['predefines'] == None or 'characterCards' not in level_table['predefines']:
            return ''
        for char_card in level_table['predefines']['characterCards']:
            char_card_name = character_table[char_card['inst']['characterKey']]['name']
            if stage_charId is not None and char_card['inst']['characterKey'] == stage_charId:
                char_pre += f"{{{{悖论模拟对象|{char_card_name}}}}}"
                memory_desc = '模拟对象干员的状态数据与玩家持有的一致，请以实际情况为准'
                continue
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
            this_p = min(200, char_card['inst']['favorPoint'] * 2)
            fp_set.add(this_p)
            favor_point.append('{}信赖值为{}%'.format(char_card_name, this_p))
        if char_pre != '':
            if favor_point != [] and memory_desc != '':
                memory_desc = '<br>' + memory_desc
            if fp_set.__len__() == 1 and favor_point.__len__() > 1:
                if stage_charId is not None:
                    fp_desc = '本关卡除模拟对象干员外的随队干员信赖值都为{}%'.format(fp_set.pop())
                else:
                    fp_desc = '本关卡随队干员信赖值都为{}%'.format(fp_set.pop())
            else:
                fp_desc = '，'.join(favor_point)
            char_pre = '''
==固定编队==
{{| class="wikitable hlist logo mw-collapsed mw-collapsible" style="text-align:center; width:567px; white-space:normal;"
!style="background-color:#0098DC;color:#FFFFFF"|固定编队
|-
|{}
|-
!备注
|-
|{}{}
|}}'''.format(char_pre, fp_desc, memory_desc)
    except:
        print(stage_page_name, 'characterCards error.')

    return char_pre


def analyze_char_insert_info(level_table, stage_page_name, character_table, skill_table):
    char_pre = ''
    favor_point, fp_set = [], set()
    try:
        if level_table['predefines'] == None or 'characterInsts' not in level_table['predefines']:
            return ''
        for char_insert in level_table['predefines']['characterInsts']:
            char_insert_name = character_table[char_insert['inst']['characterKey']]['name']
            if char_insert['skillIndex'] != -1:
                skill_name = skill_table[
                    character_table[char_insert['inst']['characterKey']]['skills'][char_insert['skillIndex']][
                        'skillId']]['levels'][0]['name']
            else:
                skill_name = ''
            char_pre += '{{{{编队单位|{}|{}|{}|{}|{}'.format(
                char_insert_name,
                char_insert['inst']['phase'],
                char_insert['inst']['level'],
                skill_name,
                char_insert['mainSkillLvl'],
            )
            if char_insert['inst']['potentialRank'] != 0:
                char_pre += '||{}'.format(char_insert['inst']['potentialRank'] + 1)
            char_pre += '}}'
            this_p = min(200, char_insert['inst']['favorPoint']*2)
            fp_set.add(this_p)
            favor_point.append('{}信赖值为{}%'.format(char_insert_name, this_p))
        if char_pre != '':
            if fp_set.__len__() == 1 and favor_point.__len__() > 1:
                fp_desc = '本关卡已部署干员信赖值都为{}%'.format(fp_set.pop())
            else:
                fp_desc = '，'.join(favor_point)
            char_pre = '''
==已部署干员==
{{| class="wikitable hlist logo mw-collapsed mw-collapsible" style="text-align:center; width:567px; white-space:normal;"
!style="background-color:#0098DC;color:#FFFFFF"|已部署干员
|-
|{}
|-
!备注
|-
|{}
|}}'''.format(char_pre, fp_desc)
    except:
        print(stage_page_name, 'characterInsts error.')

    return char_pre


def analyze_tile(level_table, stage_tile_info):
    try:
        tiles = level_table['mapData']['tiles']
        if tiles == [] or tiles == None:
            return ''
    except:
        return ''
    tile_blackboard_dict = {}
    for tile in filter(lambda x: x['blackboard'] is not None and x['blackboard'] != [], tiles):
        if tile['tileKey'] not in tile_blackboard_dict:
            tile_blackboard_dict[tile['tileKey']] = []
        if tile['blackboard'] not in tile_blackboard_dict[tile['tileKey']]:
            tile_blackboard_dict[tile['tileKey']].append(tile['blackboard'])
    if tile_blackboard_dict == {}:
        return ''
    content = '|特殊地形效果=<!--'
    for tile in tile_blackboard_dict:
        if tile in stage_tile_info:
            content += '\n' + stage_tile_info[tile]['name'] + ':'
        else:
            content += '\n' + tile + ':'
        for b in tile_blackboard_dict[tile]:
            content += '\n\t'
            for k in b:
                content += f"{k['key']} {k['value']}"
                if k['valueStr'] is not None:
                    content += f" {k['valueStr']}"
                content += ', '
    content += '\n-->\n'
    return content


def get_enemy_data(level_table, enemy_table, enemy_database):
    enemy_data = '\n==敌方情报==\n{{敌方情报\n'
    count = 1
    normal_hidden_group = analyze_normal_hidden_group(level_table)
    enemy_count_dict = {}
    for wave in level_table['waves']:
        for fragment in wave['fragments']:
            action_list = [ActionInfo(action) for action in fragment['actions']]
            pack_dict = {}
            actions_count_type = {}
            for action in action_list:
                if action.random_key is not None and action.random_pack is not None:
                    pack_dict[action.random_pack] = action.random_key
                if action.key is not None and action.key not in enemy_count_dict:
                    enemy_count_dict[action.key] = {'min': 0, 'max': 0}
                if action.key is not None and action.key not in actions_count_type:
                    actions_count_type[action.key] = {'min': 0, 'max': 0}
            for action in action_list:
                action.update_pack(pack_dict)
            actions_count = {'fixed': copy.deepcopy(actions_count_type), 'random': {}}
            for action in action_list:
                if (action.key is not None or action.random_key is not None) and (action.hidden_group == None or action.hidden_group in normal_hidden_group):
                    if action.random_key is not None:
                        if action.random_key not in actions_count['random']:
                            actions_count['random'][action.random_key] = {'single':[], 'pack': {}}
                        if action.random_pack is not None:
                            if action.random_pack not in actions_count['random'][action.random_key]['pack']:
                                actions_count['random'][action.random_key]['pack'][action.random_pack] = copy.deepcopy(actions_count_type)
                            if action.key is not None:
                                actions_count['random'][action.random_key]['pack'][action.random_pack][action.key]['min'] += action.count
                                actions_count['random'][action.random_key]['pack'][action.random_pack][action.key]['max'] += action.count
                        else:
                            actions_count['random'][action.random_key]['single'].append(copy.deepcopy(actions_count_type))
                            if action.key is not None:
                                actions_count['random'][action.random_key]['single'][-1][action.key]['min'] = action.count
                                actions_count['random'][action.random_key]['single'][-1][action.key]['max'] = action.count
                    else:
                        if action.key is not None:
                            actions_count['fixed'][action.key]['min'] += action.count
                            actions_count['fixed'][action.key]['max'] += action.count
            if actions_count['random'] != {}:
                for k_iter in actions_count['random']:
                    if actions_count['random'][k_iter]['pack'] != {}:
                        for count_p in actions_count['random'][k_iter]['pack'].values():
                            actions_count['random'][k_iter]['single'].append(count_p)
                    if actions_count['random'][k_iter]['single'] != {}:
                        for enemy_k in actions_count_type:
                            actions_count['fixed'][enemy_k]['min'] += min(x[enemy_k]['min'] for x in actions_count['random'][k_iter]['single'])
                            actions_count['fixed'][enemy_k]['max'] += max(x[enemy_k]['max'] for x in actions_count['random'][k_iter]['single'])
            for k in enemy_count_dict:
                if k in actions_count['fixed']:
                    enemy_count_dict[k]['min'] += actions_count['fixed'][k]['min']
                    enemy_count_dict[k]['max'] += actions_count['fixed'][k]['max']
    enemy_num_dict = {}
    for k in enemy_count_dict:
        if enemy_count_dict[k]['min'] == enemy_count_dict[k]['max']:
            enemy_num_dict[k] = f"{enemy_count_dict[k]['min']}"
        else:
            enemy_num_dict[k] = f"{enemy_count_dict[k]['min']},{enemy_count_dict[k]['max']}"
    for enemy in level_table['enemyDbRefs']:
        if enemy['id'] not in enemy_num_dict:
            # continue
            enemy_num_dict[enemy['id']] = '0'
        if enemy['useDb'] == False:
            enemy_data += '|敌人{count}={name}\n'.format(
                count=count,
                name=enemy['overwrittenData']['name']['m_value']
            )
            if ',' in enemy_num_dict[enemy['id']]:
                num_list = enemy_num_dict[enemy['id']].split(',')
                enemy_data += '|敌人{count}数量={enemy_num}\n|敌人{count}数量下限={enemy_num_2}\n'.format(
                    count=count,
                    enemy_num=num_list[1],
                    enemy_num_2=num_list[0]
                )
            else:
                enemy_data += '|敌人{count}数量={enemy_num}\n'.format(
                    count=count,
                    enemy_num=enemy_num_dict[enemy['id']]
                )
            enemy_data += '|敌人{count}级别={level}\n'.format(
                count=count,
                level=enemy['level']
            )
            enemy_data += '|敌人{}备注=需人工复查！\n'.format(count)
        else:
            if enemy['id'] in enemy_table:
                enemy_name = enemy_table[enemy['id']]['name']
                if enemy_name in ['W', '泥岩', '多萝西']:
                    enemy_data += '|敌人{count}={name}(敌方)\n|敌人{count}显示名={name}\n'.format(
                        count=count,
                        name=enemy_name
                    )
                else:
                    enemy_data += '|敌人{count}={name}\n'.format(
                        count=count,
                        name=enemy_name
                    )
            else:
                enemy_name = ''
                for enemy_content in enemy_database['enemies']:
                    if enemy_content['Key'] == enemy['id']:
                        enemy_name = enemy_content['Value'][0]['enemyData']['name']['m_value']
                enemy_data += '|敌人{count}={name}\n'.format(
                    count=count,
                    name=enemy_name
                )
            if ',' in enemy_num_dict[enemy['id']]:
                num_list = enemy_num_dict[enemy['id']].split(',')
                enemy_data += '|敌人{count}数量={enemy_num}\n|敌人{count}数量下限={enemy_num_2}\n'.format(
                    count=count,
                    enemy_num=num_list[1],
                    enemy_num_2=num_list[0]
                )
            else:
                enemy_data += '|敌人{count}数量={enemy_num}\n'.format(
                    count=count,
                    enemy_num=enemy_num_dict[enemy['id']]
                )
            enemy_data += '|敌人{count}级别={level}\n'.format(
                count=count,
                level=enemy['level']
            )
            if enemy['overwrittenData'] != None:
                enemy_data += parse_overwritten_data(enemy['overwrittenData'], count)
        count += 1
    enemy_data += '}}'
    return enemy_data


def get_normal_data(stage_detail, stage_table, zone_table, character_table, building_data, item_table, level_table,
                    rts):
    stage_data = '\n==普通==\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    if stage_detail['hilightMark'] == True:
        stage_data += '|子类型=难关\n'
    elif stage_detail['appearanceStyle'] == 'HIGH_DIFFICULTY':
        stage_data += '|子类型=绝境\n'
    elif stage_detail['appearanceStyle'] == 'MIST_OPS':
        stage_data += '|子类型=迷雾\n'
    if stage_detail['bossMark'] == True:
        stage_data += '|领袖标志=Yes\n'
    stage_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    if stage_detail['levelId'] == None:
        stage_data += '|战斗关卡=false\n'
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        if_tough = ''
        if stage_table['stages'][unlock_id['stageId']]['diffGroup'] == 'TOUGH' and stage_table['stages'][unlock_id['stageId']]['appearanceStyle'] != 'HIGH_DIFFICULTY':
            if_tough = '磨难'
        unlock_cond = '{num}星通关[[{ifTough}{code} {name}]]'.format(
            num={'PASS':2, 'COMPLETE':3}.get(unlock_id['completeState'], unlock_id['completeState']),
            ifTough=if_tough,
            code=stage_table['stages'][unlock_id['stageId']]['code'],
            name=stage_table['stages'][unlock_id['stageId']]['name']
        )
        unlock_cond_list.append(unlock_cond)
    stage_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    if stage_detail['dangerLevel'] == '' or stage_detail['dangerLevel'] is None:
        stage_data += '|推荐等级=-\n'
    else:
        stage_data += '|推荐等级={}\n'.format(stage_detail['dangerLevel'])
    if zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst']:
        stage_data += '|所属区域={name_1} {name_2}\n'.format(
            name_1=zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst'],
            name_2=zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    else:
        stage_data += '|所属区域={name_2}\n'.format(
            name_2=zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if stage_detail['description']:
        stage_data += '|关卡描述={desc}\n'.format(
            desc=rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
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
        stage_data += analyze_tile(level_table, stage_table['tileInfo'])
        if 'tags' in level_table['mapData'] and level_table['mapData']['tags'] != None:
            stage_data += '|地形tag={}\n'.format(','.join(level_table['mapData']['tags']))
    stage_data += '}}'

    return stage_data


def get_4star_data(stage_detail, stage_table, zone_table, character_table, building_data, item_table, level_table, rts):
    stage_4star_data = '\n==突袭==\n{{突袭关卡信息\n'
    stage_4star_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_4star_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_4star_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    stage_4star_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        if stage_table['stages'][unlock_id['stageId']]['code'] != stage_detail['code']:
            unlock_cond = '{num}星通关[[{code} {name}]]'.format(
                num={'PASS':2, 'COMPLETE':3}.get(unlock_id['completeState'], unlock_id['completeState']),
                code=stage_table['stages'][unlock_id['stageId']]['code'],
                name=stage_table['stages'][unlock_id['stageId']]['name']
            )
        else:
            unlock_cond = '{num}星通关[[#普通|{code} {name}]]普通难度'.format(
                num={'PASS':2, 'COMPLETE':3}.get(unlock_id['completeState'], unlock_id['completeState']),
                code=stage_table['stages'][unlock_id['stageId']]['code'],
                name=stage_table['stages'][unlock_id['stageId']]['name']
            )
        unlock_cond_list.append(unlock_cond)
    stage_4star_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    stage_4star_data += '|推荐等级={}\n'.format(stage_detail['dangerLevel'])
    if zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst']:
        stage_4star_data += '|所属区域={name_1} {name_2}\n'.format(
            name_1=zone_table['zones'][stage_detail['zoneId']]['zoneNameFirst'],
            name_2=zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
        )
    else:
        stage_4star_data += '|所属区域={name_2}\n'.format(
            name_2=zone_table['zones'][stage_detail['zoneId']]['zoneNameSecond']
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
        desc=rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
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


def get_campaign_data(stage_detail, stage_table, campaign_table, character_table, building_data, item_table,
                      level_table, rts):
    stage_data = '\n==关卡==\n{{剿灭关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    if '_r_' in stage_detail['stageId']:
        stage_data += '|剿灭委托=true\n'
    stage_data += '|关卡类型={}\n'.format(parse_stage_type(stage_detail['stageType']))
    stage_data += '|关卡难度={}\n'.format(stage_detail['difficulty'])
    unlock_cond_list = []
    for unlock_id in stage_detail['unlockCondition']:
        unlock_cond = '{num}星通关[[{code} {name}]]'.format(
            num={'PASS':2, 'COMPLETE':3}.get(unlock_id['completeState'], unlock_id['completeState']),
            code=stage_table['stages'][unlock_id['stageId']]['code'],
            name=stage_table['stages'][unlock_id['stageId']]['name']
        )
        unlock_cond_list.append(unlock_cond)
    stage_data += '|解锁条件={}\n'.format(', '.join(unlock_cond_list))
    if stage_detail['zoneId'] in campaign_table['campaignZones']:
        stage_data += '|所属区域={name}\n'.format(
            name=campaign_table['campaignZones'][stage_detail['zoneId']]['name']
        )
    else:
        stage_data += '|所属区域=NONE\n'
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if stage_detail['description']:
        stage_data += '|关卡描述={desc}\n'.format(
            desc=rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
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
    for idx, ladder in enumerate(campaign_detail['dropGains'][gain_flag]['gainLadders'], start=1):
        stage_data += '|理智返还{}=+{}\n'.format(idx, ladder['apFailReturn'])
    for idx, ladder in enumerate(campaign_detail['dropGains'][gain_flag]['gainLadders'], start=1):
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
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format('活动')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    stage_data += '|解锁条件={}\n'.format('—')
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format(stage_detail['code'].strip())
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    if 'description' in stage_detail:
        stage_desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))  # crisis_info
    elif 'desc' in stage_detail:
        stage_desc = rts.compile(stage_detail['desc'].replace('\\n', '<br/>'))  # weedy
    else:
        stage_desc = ''
    stage_data += '|关卡描述={desc}\n'.format(
        desc=stage_desc
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    stage_data += '}}'

    return stage_data


def get_roguelike_data(stage_detail, level_table, rts):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_data += '|关卡id={}\n'.format(stage_detail['id'])
    stage_data += '|关卡类型={}\n'.format('活动')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    stage_data += '|解锁条件={}\n'.format('—')
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format('—')
    if stage_detail['levelId']:
        stage_data += analyze_level_info(level_table)
    stage_data += '|关卡描述={desc}\n'.format(
        desc=rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    stage_data += '}}'

    return stage_data


def get_roguelike_4star_data(stage_detail, level_table, rts):
    stage_4star_data = '\n==紧急作战==\n{{突袭关卡信息\n'
    stage_4star_data += '|关卡代号={}\n'.format(stage_detail['code'].strip())
    stage_4star_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
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
        desc=rts.compile(stage_detail['eliteDesc'].replace('\\n', '<br/>'))
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
    stage_data += '|关卡名={}\n'.format(stage_detail['name'].strip())
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format('悖论模拟')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    unlock_cond = ''
    for p in stage_detail['unlockParam']:
        if unlock_cond != '':
            unlock_cond += '，'
        if p['unlockType'] == 1 or p['unlockType'] == 'AWAKE':
            unlock_cond += '提升至精英阶段{}等级{}'.format(p['unlockParam1'], p['unlockParam2'])
        elif p['unlockType'] == 2 or p['unlockType'] == 'FAVOR':
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
        desc=rts.compile(stage_detail['description'].replace('\n', '<br/>'))
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    reward_item = ['{}:三星获得'.format(parse_drop_item(r, character_table, building_data, item_table)) for r in
                   stage_detail['rewardItem']]
    stage_data += '|首次掉落=' + ','.join(reward_item) + '\n'
    stage_data += '}}'

    return stage_data


def analyze_xb_level_info(level_table):
    level_info = ''
    level_info += '|部署上限={}\n'.format(level_table['options']['characterLimit'])
    level_info += '|初始COST={}\n'.format(level_table['options']['initialCost'])
    level_info += '|COST上限={}\n'.format(level_table['options']['maxCost'])
    level_info += '|目标点耐久={}\n'.format(level_table['options']['maxLifePoint'])
    enemy_count = {'min': 0, 'max': 0}
    min_time = 0.0
    normal_hidden_group = analyze_normal_hidden_group(level_table)
    for wave in level_table['waves']:
        min_time += wave['preDelay'] + wave['postDelay']
        for fragment in wave['fragments']:
            time, action_enemy_min, action_enemy_max, fragment_flag = analyze_action(fragment['actions'], normal_hidden_group)
            enemy_count['min'] += action_enemy_min
            enemy_count['max'] += action_enemy_max
            if fragment_flag:
                min_time += fragment['preDelay']
                min_time += time
    if enemy_count['min'] == enemy_count['max']:
        level_info += '|敌人数量={}\n'.format(enemy_count['min'])
    else:
        level_info += '|敌人数量={}~{}\n'.format(enemy_count['min'], enemy_count['max'])
    level_info += '|地图大小={}×{}\n'.format(level_table['mapData']['map'][0].__len__(), level_table['mapData']['map'].__len__())
    if level_table['options']['maxPlayTime'] > 0:
        mptime = level_table['options']['maxPlayTime']
        level_info += '|倒计时={}分{}秒\n'.format(int(mptime / 60), int(mptime % 60))
    else:
        if abs(min_time - int(min_time)) < 0.0001:
            level_info += '|最短用时={}分{}秒\n'.format(int(min_time / 60), int(min_time % 60))
        else:
            level_info += '|最短用时={}分{:.1f}秒\n'.format(int(min_time / 60), min_time % 60)
    return level_info


def get_sandbox_data(stage_detail, rts, level_table, reward_data, item_data):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡id={}\n'.format(stage_detail['stageId'])
    stage_data += '|关卡类型={}\n'.format('生息演算')
    if stage_detail['levelId']:
        stage_data += analyze_xb_level_info(level_table)
    stage_data += '|关卡描述={desc}\n'.format(
        desc=rts.compile(stage_detail['description'].replace('\n', '<br/>'))
    )
    rewards = []
    for k in reward_data:
        if stage_detail['stageId'] in reward_data[k]:
            for r in reward_data[k][stage_detail['stageId']]['rewardList']:
                if item_data[r['rewardItem']]['itemType'] != 'PLACEHOLDER':
                    rewards.append(f"{{{{资源概览|{item_data[r['rewardItem']]['itemName'].strip()}}}}}")
    stage_data += '|资源概览={}\n'.format(''.join(rewards))
    stage_data += '|action消耗={}\n'.format(stage_detail['actionCost'])
    stage_data += '|power消耗={}\n'.format(stage_detail['powerCost'])
    stage_data += '|特殊地图={{#Widget:XbMapViewer|data={{:{{FULLPAGENAME}}/data}}}}\n'
    stage_data += '}}'

    return stage_data


class ActionInfo:
    def __init__(self, action):
        if action['actionType'] == 0 and action['key'] != '':
            self.key = action['key']
        else:
            self.key = None
        if self.key is not None:
            self.time = action['preDelay'] + (action['count'] - 1) * action['interval']
            self.count = action['count']
        else:
            self.time = 0.0
            self.count = 0
        if 'hiddenGroup' in action and action['hiddenGroup'] is not None:
            self.hidden_group = action['hiddenGroup']
        else:
            self.hidden_group = None
        self.random_type = 0
        if 'randomSpawnGroupKey' in action and action['randomSpawnGroupKey'] is not None:
            self.random_key = action['randomSpawnGroupKey']
            self.random_type += 1
        else:
            self.random_key = None
        if 'randomSpawnGroupPackKey' in action and action['randomSpawnGroupPackKey'] is not None:
            self.random_pack = action['randomSpawnGroupPackKey']
            self.random_type += 2
        else:
            self.random_pack = None

    def update_pack(self, pack_dict):
        if self.random_key is None and self.random_pack is not None:
            if self.random_pack in pack_dict:
                self.random_key = pack_dict[self.random_pack]
            else:
                print(f"Error: cannot find random_key for pack {self.random_pack}")


class Stage(Job):
    def check_duplicate(self):
        stage_table = self.getgd('excel/stage_table.json')
        activity_table = self.getgd('excel/activity_table.json')

        stage_code_dict, duplicate_dict = {}, {}
        for s in stage_table['stages'].values():
            if s['difficulty'] == 'FOUR_STAR' or s['stageType'] == 'GUIDE' or s['diffGroup'] in ['EASY', 'TOUGH']:
                continue
            if s['code'] not in stage_code_dict:
                stage_code_dict[s['code'].strip()] = []
            stage_code_dict[s['code'].strip()].append(s['stageId'])
        for code, s_list in stage_code_dict.items():
            if len(s_list) > 1:
                duplicate_dict[code] = '{{消歧义页}}\n<big><big>你要找的结果可能如下：</big></big>'
                for sid in s_list:
                    cat = ''
                    if stage_table['stages'][sid]['stageType'] == 'ACTIVITY':
                        result = re.search('^([^_]+)_', sid)
                        act_id = result.group(1)
                        if act_id in activity_table['basicInfo']:
                            cat = f"（[[{activity_table['basicInfo'][act_id]['name']}]]关卡）"
                    page_name = '\n*<big>\'\'\'[[{} {}]]\'\'\'{}</big>'.format(
                        stage_table['stages'][sid]['code'].strip(),
                        stage_table['stages'][sid]['name'].strip(),
                        cat
                    )
                    if page_name not in duplicate_dict[code]:
                        duplicate_dict[code] += page_name
        self.duplicate_dict = duplicate_dict
        # print(json.dumps(duplicate_dict, indent=4, ensure_ascii=False))

    def _run(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        stage_table = self.getgd('excel/stage_table.json')
        zone_table = self.getgd('excel/zone_table.json')
        redirect_table = self.getgd('battle/battle_misc_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:普通难度关卡')
        new_stage_list = []
        self.check_duplicate()

        for stage_id in stage_table['stages']:
            stage_detail = stage_table['stages'][stage_id]
            if stage_detail['stageType'] not in ['MAIN', 'SUB', 'DAILY', 'ACTIVITY', 'SPECIAL_STORY', 'CLIMB_TOWER'] or stage_detail[
                'difficulty'] == 'FOUR_STAR' or stage_detail['diffGroup'] in ['EASY']:
                continue
            stage_detail['name'] = {
                'act21side_01_t': '新城区大街(德克萨斯)',
                'act21side_02_t': '萨卢佐家(拉普兰德2)',
                'act21side_03_m2': '后巷(拉普兰德1)',
                'act21side_04_m1': '萨卢佐家(拉普兰德1)',
                'act21side_05_m1': '后巷(乔万娜)',
                'act21side_05_t': '后巷(拉普兰德2)',
                'act21side_06_t': '新城区大街(丹布朗)'
            }.get(stage_id, stage_detail['name'].strip())
            stage_page_name = stage_detail['code'].strip() + ' ' + stage_detail['name']
            if stage_detail['diffGroup'] == 'TOUGH' and stage_detail['appearanceStyle'] != 'HIGH_DIFFICULTY':
                stage_page_name = '磨难' + stage_page_name
            if stage_page_name in stage_list:
                continue
            # if stage_detail['code'] not in ['TR-3', 'IC-P-2']:
            #     continue

            if stage_detail['levelId']:
                try:
                    if stage_detail['levelId'] in redirect_table['levelScenePairs']:
                        level_table = self.getgd('levels/' + redirect_table['levelScenePairs'][stage_detail['levelId']]['levelId'].lower() + '.json')
                    else:
                        level_table = self.getgd('levels/' + stage_detail['levelId'].lower() + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}
            stage_normal_data = get_normal_data(stage_detail, stage_table, zone_table, character_table, building_data,
                                                item_table, level_table, rts)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''
            stage_4star_data = get_4star_data(stage_table['stages'][stage_detail['hardStagedId']], stage_table,
                                              zone_table, character_table, building_data, item_table, level_table,
                                              rts) if stage_detail['hardStagedId'] else ''
            if len(list(filter(lambda x: x['dropType'] in [2, 3, 4],
                               stage_detail['stageDropInfo']['displayDetailRewards']))) > 0:
                stage_drop = '\n==材料掉落==\n{{关卡材料掉落}}'
            else:
                stage_drop = ''
            if stage_detail['levelId']:
                char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table)
                char_pre += analyze_char_insert_info(level_table, stage_page_name, character_table, skill_table)
            else:
                char_pre = ''

            stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_4star_data + stage_enemy_data + char_pre + stage_drop + '\n==注释与链接==\n<references/>\n{{关卡导航}}'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            # old = self.wiki.read(stage_page_name)
            # result = re.search('(\n==敌方情报==\n[\s\S]*?)\n==', old)
            # if result:
            #     stage_content = old.replace(result.group(1), stage_enemy_data)
            # else:
            #     continue

            # result2 = re.search(r"\|额外物资=(.*?)\n", stage_normal_data)
            # if not result2:
            #     continue
            # old = self.wiki.read(stage_page_name)
            # result1 = re.search(r"\|额外物资=(.*?)\n", old)
            # if result1 and result2:
            #     stage_content = old.replace(result1.group(1), result2.group(1))
            #     if stage_content != old:
            #         print(f'{stage_page_name} differenet. update.')
            #         self.wiki.edit(
            #             title=stage_page_name,
            #             text=stage_content,
            #             summary='update'
            #         )
            #     else:
            #         print(f'{stage_page_name} same.')
            # else:
            #     continue

            if stage_detail['code'].strip() in self.duplicate_dict:
                self.wiki.edit(
                    title=stage_detail['code'].strip(),
                    text=self.duplicate_dict[stage_detail['code'].strip()],
                    summary='消歧义'
                )
            else:
                self.wiki.edit(
                    title=stage_detail['code'].strip(),
                    text=stage_redirect,
                    summary='init',
                    createonly='1'
                )
            self.wiki.edit(
                title=stage_detail['stageId'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

            new_stage_list.append('* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title='首页/新增关卡',
                text='\n'.join(new_stage_list),
                summary='update',
                bot=None,
                minor=True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def run_campaign(self):
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
            stage_page_name = stage_detail['code'].strip() + ' ' + stage_detail['name'].strip()
            if stage_page_name in stage_list:
                continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'].lower() + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_campaign_data(stage_detail, stage_table, campaign_table, character_table,
                                                  building_data, item_table, level_table, rts)
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
                title=stage_detail['name'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_detail['stageId'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

            new_stage_list.append('* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title='首页/新增关卡',
                text='\n'.join(new_stage_list),
                summary='update',
                bot=None,
                minor=True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def run_crisis(self):
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        # 从 crisis_info 读
        # https://weedy.baka.icu/crisis/today/internal
        with open('crisis_info.json', 'r', encoding='utf-8') as file:
            stage_table = json.loads(file.read())
        # for stage_key in stage_table['data']['seasonInfo'][0]['stages']:
        #     stage_detail = stage_table['data']['seasonInfo'][0]['stages'][stage_key]
        #     stage_detail['stageId'] = stage_key
        #     stage_detail['levelId'] = 'Obt/rune/' + stage_key
        for stage_x in stage_table['stages']:
            stage_detail = stage_x
            stage_detail['stageId'] = stage_detail['id']
            stage_detail['levelId'] = 'Obt/rune/' + stage_detail['id']

        # 从 weedy 读
        # session = requests.Session()
        # stage_list = session.get('https://weedy.baka.icu/crisis/today').json()['stages']
        # stage_list = [stage_list[0]]
        # for stage_key in stage_list:
        #     stage_detail = stage_key
        #     stage_detail['stageId'] = stage_detail['id']
        #     stage_detail['levelId'] = 'Obt/rune/' + stage_detail['id']

            stage_page_name = stage_detail['code'].strip() + ' ' + stage_detail['name'].strip()

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'].lower() + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_crisis_data(stage_detail, level_table, rts)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''

            stage_content = '{{pathnav2|关卡一览}}\n__NOTOC__' + stage_normal_data + stage_enemy_data + '\n==合约详情==\n{{合约详情}}\n==注释与链接==\n<references/>\n{{关卡导航}}\n[[分类:危机合约关卡]]'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            self.wiki.edit(
                title=stage_detail['name'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True,
                createonly='1'
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

    def run_rogue_like(self):
        # roguelike_table = self.getgd('excel/roguelike_table.json')
        roguelike_table = self.getgd('excel/roguelike_topic_table.json')
        roguelike_table = roguelike_table['details']['rogue_2']
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        for stage_key in roguelike_table['stages']:
            stage_detail = roguelike_table['stages'][stage_key]
            if stage_detail['difficulty'] == 'FOUR_STAR':
                continue

            stage_page_name = stage_detail['code'].strip() + ' ' + stage_detail['name'].strip()

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'].lower() + '.json')
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
                title=stage_detail['name'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True,
                createonly='1'
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

    def run_memory(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        handbook_info_table = self.getgd('excel/handbook_info_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:悖论模拟关卡')
        new_stage_list = []

        for stage_detail in handbook_info_table['handbookStageData'].values():
            stage_page_name = '悖论模拟 {}'.format(stage_detail['name'].strip())
            if stage_page_name in stage_list:
                continue
            # if stage_page_name not in ['悖论模拟 书写悲痛', '悖论模拟 御护', '悖论模拟 高效除虫', '悖论模拟 射术传承']:
            #     continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'].lower() + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_memory_data(stage_detail, level_table, rts, character_table, building_data,
                                                item_table)
            stage_enemy_data = self._run_enemy_data(level_table) if stage_detail['levelId'] else ''
            char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table, stage_charId = stage_detail['charId'])
            char_pre += analyze_char_insert_info(level_table, stage_page_name, character_table, skill_table)

            stage_content = '{{pathnav2|关卡一览}}\n__NOTOC__' + stage_normal_data + stage_enemy_data + char_pre + '\n==注释与链接==\n<references/>\n{{关卡导航}}'
            stage_redirect = '#redirect [[{}]]'.format(stage_page_name)

            # old = self.wiki.read(stage_page_name)
            # stage_content = old
            # result = re.search('(\n==固定编队==\n[\s\S]*?)\n==', stage_content)
            # if result:
            #     stage_content = stage_content.replace(result.group(1), analyze_char_card_info(level_table, stage_page_name, character_table, skill_table, stage_charId = stage_detail['charId']))
            # else:
            #     pass
            # result2 = re.search('(\n==已部署干员==\n[\s\S]*?)\n==', stage_content)
            # if result2:
            #     stage_content = stage_content.replace(result2.group(1), analyze_char_insert_info(level_table, stage_page_name, character_table, skill_table))
            # else:
            #     pass
            # if stage_content == old:
            #     continue

            self.wiki.edit(
                title=stage_detail['name'].strip(),
                text=stage_redirect,
                summary='init',
                createonly='1'
            )
            self.wiki.edit(
                title=stage_page_name,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_page_name))

            new_stage_list.append('\n* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title='首页/新增关卡',
                appendtext=''.join(new_stage_list),
                summary='update',
                bot=None,
                minor=True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def run_sandbox(self):
        sandbox_table = self.getgd('excel/sandbox_table.json')
        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        stage_list = self.wiki.category('分类:生息演算关卡')
        new_stage_list = []

        for act_key in sandbox_table['sandboxActTables']:
            for stage_id, stage_data in sandbox_table['sandboxActTables'][act_key]['stageDatas'].items():
                stage_data['name'] = stage_data['name'].strip()
                stage_page_name = f"{stage_data['code']} {stage_data['name']}"
                if stage_page_name in stage_list:
                    continue
                # if stage_data['name'] not in ['吝啬陷阱']:
                #     continue

                if stage_data['levelId']:
                    try:
                        level_table = self.getgd('levels/' + stage_data['levelId'].lower() + '.json')
                    except:
                        print('Cannot find level data of {}.'.format(stage_page_name))
                        continue
                else:
                    level_table = {}

                stage_normal_data = get_sandbox_data(stage_data, rts, level_table, sandbox_table['sandboxActTables'][act_key]['rewardConfigDatas'], sandbox_table['itemDatas'])
                stage_enemy_data = self._run_enemy_data(level_table) if stage_data['levelId'] else ''
                if stage_data['levelId']:
                    char_pre = analyze_char_card_info(level_table, stage_page_name, character_table, skill_table)
                    char_pre += analyze_char_insert_info(level_table, stage_page_name, character_table, skill_table)
                else:
                    char_pre = ''
                stage_content = '{{pathnav2|关卡一览}}' + stage_normal_data + stage_enemy_data + char_pre + '\n==注释与链接==\n<references/>\n{{关卡导航}}'

                # old = self.wiki.read(stage_page_name)
                # result = re.search('(\n==敌方情报==\n[\s\S]*?)\n==', old)
                # if result:
                #     stage_content = old.replace(result.group(1), stage_enemy_data)
                # else:
                #     continue

                self.wiki.edit(
                    title=stage_page_name+'/data',
                    text=json.dumps(level_table, ensure_ascii=False),
                    summary='init',
                    createonly=True,
                    contentmodel='json'
                )
                self.wiki.edit(
                    title=stage_page_name,
                    text=stage_content,
                    summary='init',
                    createonly=True,
                    bot=None,
                    minor=True
                )
                # print(stage_content)
                print('Created: {}.'.format(stage_page_name))

                new_stage_list.append('\n* [[{}]]'.format(stage_page_name))

        if new_stage_list != []:
            self.wiki.edit(
                title='首页/新增关卡',
                appendtext=''.join(new_stage_list),
                summary='update',
                bot=None,
                minor=True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def run_id(self, path):
        if self.gamedata._source() != 'Unpacker':
            return

        character_table = self.getgd('excel/character_table.json')
        skill_table = self.getgd('excel/skill_table.json')
        stage_table = self.getgd('excel/stage_table.json')
        stage_id_list = []
        for s in stage_table['stages'].values():
            if s['levelId'] is not None:
                stage_id_list.append('levels/' + s['levelId'].lower() + '.json')

        filelist = []
        base_dir = './Unpacker/zh_CN/gameData/'

        def get_files(curr_path):
            if '.DS_Store' in curr_path:
                return
            if os.path.isfile(os.path.join(base_dir, curr_path)):
                filelist.append(curr_path)
            else:
                for f in os.listdir(os.path.join(base_dir, curr_path)):
                    get_files(os.path.join(curr_path, f))

        get_files(path)

        new_stage_list = []
        for file in filelist:
            stage_id = os.path.splitext(os.path.split(file)[1])[0]
            if file.lower() in stage_id_list:
                print(stage_id, 'already in stage_table. Pass.')
                continue
            level_table = self.getgd(file.lower())

            stage_data = '\n{{普通关卡信息\n'
            stage_data += '|关卡代号={}\n'.format('—')
            stage_data += '|关卡名={}\n'.format(stage_id)
            stage_data += '|关卡id={}\n'.format(stage_id)
            stage_data += '|关卡类型={}\n'.format('活动')
            stage_data += '|关卡难度={}\n'.format('NORMAL')
            stage_data += '|解锁条件={}\n'.format('—')
            stage_data += '|推荐等级={}\n'.format('—')
            stage_data += '|所属区域={}\n'.format('-')
            stage_data += analyze_level_info(level_table)
            stage_data += '|关卡描述=\n'.format('-')
            stage_data += '|作战消耗={}\n'.format(0)
            stage_data += '|演习消耗=-1\n'
            stage_data += '}}'

            stage_enemy_data = self._run_enemy_data(level_table)
            char_pre = analyze_char_card_info(level_table, stage_id, character_table, skill_table)
            char_pre += analyze_char_insert_info(level_table, stage_id, character_table, skill_table)
            stage_content = '{{pathnav2|关卡一览}}\n__NOTOC__' + stage_data + stage_enemy_data + char_pre + '\n==注释与链接==\n<references/>\n{{关卡导航}}'

            self.wiki.edit(
                title=stage_id,
                text=stage_content,
                summary='init',
                bot=None,
                minor=True
            )
            # print(stage_content)
            print('Created: {}.'.format(stage_id))
            new_stage_list.append('\n* [[{}]]'.format(stage_id))

        if new_stage_list != []:
            self.wiki.edit(
                title='首页/新增关卡',
                appendtext=''.join(new_stage_list),
                summary='update',
                bot=None,
                minor=True
            )
            # print('\n'.join(new_stage_list))
            print('Updated: {}.'.format('首页/新增关卡'))

    def _run_enemy_data(self, level_table):
        enemy_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        return get_enemy_data(level_table, enemy_table['enemyData'], enemy_database)
