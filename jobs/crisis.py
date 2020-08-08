from utils.job import Job
from utils.richTextStyles import RichTextStyles

import json
import requests

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


def get_normal_data(stage_detail, level_table, rts):
    stage_data = '\n{{普通关卡信息\n'
    stage_data += '|关卡代号={}\n'.format(stage_detail['code'])
    stage_data += '|关卡名={}\n'.format(stage_detail['name'])
    stage_data += '|关卡类型={}\n'.format('活动')
    stage_data += '|关卡难度={}\n'.format('NORMAL')
    stage_data += '|解锁条件={}\n'.format('—')
    stage_data += '|推荐等级={}\n'.format('—')
    stage_data += '|所属区域={}\n'.format(stage_detail['code'])
    if stage_detail['levelId']:
        stage_data += '|部署上限={}\n'.format(level_table['options']['characterLimit'])
        stage_data += '|初始COST={}\n'.format(level_table['options']['initialCost'])
        stage_data += '|COST上限={}\n'.format(level_table['options']['maxCost'])
        stage_data += '|目标点耐久={}\n'.format(level_table['options']['maxLifePoint'])
        enemy_count = 0
        min_time = 0.0
        for wave in level_table['waves']:
            min_time += wave['preDelay'] + wave['postDelay']
            for fragment in wave['fragments']:
                min_time += fragment['preDelay']
                min_time += max(
                    [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']])
                for unit in fragment['actions']:
                    if unit['actionType'] == 0:
                        enemy_count += unit['count']
        stage_data += '|敌人数量={}\n'.format(enemy_count)
        stage_data += '|地图大小={}×{}\n'.format(level_table['mapData']['width'], level_table['mapData']['height'])
        if abs(min_time - int(min_time)) < 0.00001:
            stage_data += '|最短用时={}分{}秒\n'.format(int(min_time / 60), int(min_time % 60))
        else:
            stage_data += '|最短用时={}分{:.1f}秒\n'.format(int(min_time / 60), min_time % 60)
    stage_data += '|关卡描述={desc}\n'.format(
        # desc = rts.compile(stage_detail['description'].replace('\\n', '<br/>'))
        desc = rts.compile(stage_detail['desc'].replace('\\n', '<br/>'))
    )
    stage_data += '|作战消耗={}\n'.format(0)
    stage_data += '|演习消耗=-1\n'
    stage_data += '}}'

    return stage_data


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
            enemy_data += '|敌人{}备注=需人工复查！\n'.format(count)
        else:
            if enemy['id'] in enemy_table:
                enemy_data += '|敌人{count}={name}\n'.format(
                    count = count,
                    name = enemy_table[enemy['id']]['name']
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


class Crisis(Job):
    def _run(self):
        # with open('crisis_info.json', 'r', encoding = 'utf-8') as file:
        #     stage_table = json.loads(file.read())
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        session = requests.Session()
        stage_list = session.get('https://weedy.baka.icu/crisis/today').json()['stages']
        stage_list = [stage_list[0]]

        # for stage_key in stage_table['data']['seasonInfo'][0]['stages']:
        #     stage_detail = stage_table['data']['seasonInfo'][0]['stages'][stage_key]
        for stage_key in stage_list:
            stage_detail = stage_key
            stage_detail['levelId'] = 'Obt/rune/level_rune_04-01'

            stage_page_name = stage_detail['code'] + ' ' + stage_detail['name'].rstrip()

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                level_table = {}

            stage_normal_data = get_normal_data(stage_detail, level_table, rts)
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

    def _run_enemy_data(self, level_table):
        enemy_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        return get_enemy_data(level_table, enemy_table, enemy_database)

