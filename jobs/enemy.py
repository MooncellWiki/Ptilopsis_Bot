from utils.job import Job
from utils.richTextStyles import RichTextStyles

import json
import re
import bisect
import os


class RtsHtml:
    richTextStyles_t = {}
    termDescriptionDict_t = {}
    richTextStyles = {}
    termDescriptionDict = {}

    def __init__(self, gamedata_const):
        self.richTextStyles_t = gamedata_const['richTextStyles']
        self.termDescriptionDict_t = gamedata_const['termDescriptionDict']
        for s in self.richTextStyles_t:
            temp = self.richTextStyles_t[s]
            if temp.find('</color>') != -1:
                self.richTextStyles[s] = temp.replace('<color=', '<span style="color:').replace('</color>', '</span>').replace('>{', ';">{')
            else:
                self.richTextStyles[s] = '{0}'
        for k in self.termDescriptionDict_t:
            temp2 = self.termDescriptionDict_t[k]
            result = ''
            result += '<span class="mc-tooltips">'
            result += '<span>{term}</span>'
            result += '<span>{description}</span>'.format(
                description=remove_term(temp2['description'])
            )
            result += '</span>'
            self.termDescriptionDict[k] = result

    def tran1(self, matched):
        code = matched.group(1)
        if code.lower() in self.richTextStyles:
            return self.richTextStyles[code.lower()].format(matched.group(2))
        else:
            return matched.group(2)

    def tran2(self, matched):
        code = matched.group(1)
        if code in self.termDescriptionDict:
            return self.termDescriptionDict[code].format(term=matched.group(2))
        else:
            return matched.group(2)

    def compile(self, s):
        pattern = re.compile('<@([^>]*)>(.*?)<\/>')
        t = re.sub(pattern, self.tran1, s)
        pattern = re.compile('<\$([^>]*)>(.*?)<\/>')
        t = re.sub(pattern, self.tran2, t)
        return t


def remove_term(text):
    pattern = re.compile('(<\$[^>]*>)')
    t = re.sub(pattern, '', text)
    return t.replace('</>', '')


def format_abilityList(aList, rts, html=False):
    if aList is None or aList == []:
        return ''
    a_content = ''
    for aa in aList:
        if aa['textFormat'] == 'NORMAL':
            a_content += '·' + rts.compile(aa['text']) + '<br>'
        elif aa['textFormat'] == 'SILENCE':
            a_content += '※' + rts.compile(aa['text']) + '<br>'
        elif aa['textFormat'] == 'TITLE':
            if html:
                a_content += '<span style="color:#FF4F0B">' + rts.compile(aa['text']) + '</span><br>'
            else:
                a_content += '{{color|#FF4F0B|' + rts.compile(aa['text']) + '}}<br>'
        else:
            a_content += rts.compile(aa['text']) + '<br>'
    return a_content[:-4]


class ClassLevel:
    def __init__(self, level_info_list):
        self.attack = []
        self.defence = []
        self.magicRes = []
        self.maxHP = []
        self.moveSpeed = []
        self.baseAttackTime = []
        self.level = []
        # 默认YJ给的数据按序排列
        for class_level_info in reversed(level_info_list):
            self.attack.append(class_level_info['attack']['min'])
            self.defence.append(class_level_info['def']['min'])
            self.magicRes.append(class_level_info['magicRes']['min'])
            self.maxHP.append(class_level_info['maxHP']['min'])
            self.moveSpeed.append(class_level_info['moveSpeed']['min'])
            self.baseAttackTime.append(class_level_info['attackSpeed']['min'])
            self.level.append(class_level_info['classLevel'])
        self.baseAttackTime = list(reversed(self.baseAttackTime))

    def getAttack(self, target_attack):
        return self.level[max(1, bisect.bisect_right(self.attack, target_attack))-1]

    def getDef(self, target_def):
        return self.level[max(1, bisect.bisect_right(self.defence, target_def))-1]

    def getMagicRes(self, target_magicRes):
        return self.level[max(1, bisect.bisect_right(self.magicRes, target_magicRes))-1]

    def getMaxHP(self, target_maxHP):
        return self.level[max(1, bisect.bisect_right(self.maxHP, target_maxHP))-1]

    def getMoveSpeed(self, target_moveSpeed):
        return self.level[max(1, bisect.bisect_right(self.moveSpeed, target_moveSpeed))-1]

    def getBaseAttackTime(self, target_baseAttackTime):
        if target_baseAttackTime < 0:
            return self.level[len(self.level) - bisect.bisect_right(self.baseAttackTime, 1.0)]
        return self.level[len(self.level) - bisect.bisect_right(self.baseAttackTime, target_baseAttackTime)]

    def getEnemyDamageRes(self, target_enemyDamageRes):
        return self.level[max(1, bisect.bisect_right(self.moveSpeed, target_enemyDamageRes))-1]

    def getEnemyRes(self, target_enemyRes):
        return self.level[max(1, bisect.bisect_right(self.moveSpeed, target_enemyRes))-1]


class Enemy(Job):
    def _run(self):
        def get_value(idx, v, name, k):
            if idx == 0 or v['m_defined'] == True:
                if v['m_defined'] == False:
                    s = {'i': '0', 'f': '0.0', 's': '', 'b': '无'}.get(k, '')
                    if name == '攻击范围半径':
                        s = ''
                    if name == '攻击速度':
                        s = '100'
                    if name == '数量':
                        s = '1'
                else:
                    if k == 's':
                        s = rts.compile(v["m_value"]) if v["m_value"] is not None else ''
                    elif k == 'i' and v["m_value"] >= 0:
                        s = str(int(v["m_value"]) if v["m_value"] == int(v["m_value"]) else v["m_value"])
                    elif k == 'f' and v["m_value"] >= 0:
                        s = str(v["m_value"])
                    elif k == 'b':
                        s = {True: '有', False: '无'}.get(v["m_value"], '无')
                    else:
                        s = ''
                return f'\n|{name}={s}'
            else:
                return ''

        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        enemy_list = self.wiki.category('分类:敌人')
        enemy_list = [e.replace('(敌方)', '') for e in enemy_list]
        enemy_db_index = {v['Key']: idx for idx, v in enumerate(enemy_database['enemies'])}
        enemy_level_dict = {'NORMAL': '普通', 'ELITE': '精英', 'BOSS': '领袖'}
        enemy_motion_dict = {'FLY': '飞行', 'WALK': '地面'}
        enemy_applyway_dict = {'ALL': '近战 远程', 'RANGED': '远程', 'MELEE': '近战', 'NONE': '不攻击'}
        enemy_damage_dict = {'PHYSIC': '物理', 'MAGIC': '法术', 'NO_DAMAGE': '无', 'HEAL': '治疗'}
        enemy_race_dict = {r['id']: r['raceName'] for r in enemy_handbook_table['raceData'].values()}
        level_standard = ClassLevel(enemy_handbook_table['levelInfoList'])

        for enemy in enemy_handbook_table['enemyData'].values():
        #     enemy['name'] = '孽茨雷，“食腐者之王”'
        #     enemy['enemyId'] = 'enemy_1555_lrking'
        #     enemy['hideInHandbook'] = False

            enemy['name'] = enemy['name'].strip()
            if enemy['name'] in enemy_list:
            # if enemy['name'] not in ['马特奥上尉']:
                continue
            if enemy['name'] == '-' or enemy['hideInHandbook'] is True:
                continue

            # 先分析database中数据
            content_lv = ''
            attribute_data = [-1, -1, -1, -1, -1, -1, -1, -1]
            apply_way, motion = None, None
            race_tag = set()
            if enemy['enemyId'] in enemy_db_index:
                enemy_data = enemy_database['enemies'][enemy_db_index[enemy['enemyId']]]
                for idx, d in enumerate(enemy_data['Value']):
                    if d['level'] != idx:
                        print(f'enemy {enemy["name"]} database order error.')
                        continue
                    lv_data = d['enemyData']
                    for idx_a, k in enumerate(['maxHp', 'atk', 'def', 'magicResistance', 'moveSpeed', 'baseAttackTime', 'epResistance', 'epDamageResistance']):
                        if lv_data['attributes'][k]['m_defined'] is True and attribute_data[idx_a] == -1:
                            attribute_data[idx_a] = lv_data['attributes'][k]['m_value']
                    if lv_data['applyWay']['m_defined'] is True and apply_way is None:
                        apply_way = lv_data['applyWay']['m_value']
                    if lv_data['motion']['m_defined'] is True and motion is None:
                        motion = lv_data['motion']['m_value']
                    if lv_data['enemyTags']['m_defined'] is True and lv_data['enemyTags']['m_value']:
                        for t in lv_data['enemyTags']['m_value']:
                            race_tag.add(t)
                    content_lv += f'\n==级别{idx}=='
                    content_lv += f'\n{{{{敌人信息/level\n|index={idx}'
                    content_lv += get_value(idx, lv_data['description'], '描述', 's')
                    content_lv += get_value(idx, lv_data['lifePointReduce'], '数量', 'i')
                    content_lv += get_value(idx, lv_data['rangeRadius'], '攻击范围半径', 'f')
                    content_lv += get_value(idx, lv_data['attributes']['maxHp'], '最大生命值', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['atk'], '攻击力', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['def'], '防御力', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['magicResistance'], '法术抗性', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['moveSpeed'], '移动速度', 'f')
                    content_lv += get_value(idx, lv_data['attributes']['attackSpeed'], '攻击速度', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['baseAttackTime'], '攻击间隔', 'f')
                    content_lv += get_value(idx, lv_data['attributes']['hpRecoveryPerSec'], '生命恢复速度', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['spRecoveryPerSec'], 'sp恢复速度', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['massLevel'], '重量等级', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['epResistance'], '元素抗性', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['epDamageResistance'], '损伤抵抗', 'i')
                    content_lv += get_value(idx, lv_data['attributes']['stunImmune'], '眩晕抗性', 'b')
                    content_lv += get_value(idx, lv_data['attributes']['silenceImmune'], '沉默抗性', 'b')
                    content_lv += get_value(idx, lv_data['attributes']['sleepImmune'], '沉睡抗性', 'b')
                    content_lv += get_value(idx, lv_data['attributes']['frozenImmune'], '冻结抗性', 'b')
                    content_lv += get_value(idx, lv_data['attributes']['levitateImmune'], '浮空抗性', 'b')
                    content_lv += get_value(idx, lv_data['attributes']['disarmedCombatImmune'], '战栗抗性', 'b')
                    if 'talentBlackboard' in lv_data and lv_data['talentBlackboard']:
                        content_lv += '\n|天赋=<!--{}-->'.format(
                            json.dumps(lv_data['talentBlackboard'], indent=4, ensure_ascii=False)
                        )
                    content_lv += '\n}}'

            content = '{{Navigator|敌人一览}}\n{{敌人信息/common'
            content += f'\n|id={enemy["sortId"]}'
            content += f'\n|名称={enemy["name"]}'
            content += f'\n|index={enemy["enemyIndex"]}'
            content += f'\n|地位级别={enemy_level_dict.get(enemy["enemyLevel"], "其他")}'
            content += f'\n|描述={rts.compile(enemy["description"])}'
            content += f'\n|伤害类型={" ".join(enemy_damage_dict.get(x, "未知") for x in enemy["damageType"])}'
            content += f'\n|攻击方式={enemy_applyway_dict.get(apply_way, "未知")}'
            content += f'\n|行动方式={enemy_motion_dict.get(motion, "未知")}'
            if enemy['invisibleDetail'] is True:
                content += f'\n|耐久=?'
                content += f'\n|攻击力=?'
                content += f'\n|防御力=?'
                content += f'\n|移动速度=?'
                content += f'\n|攻击速度=?'
                content += f'\n|法术抗性=?'
                content += f'\n|元素抗性=?'
                content += f'\n|损伤抵抗=?'
            else:
                content += f'\n|耐久={level_standard.getMaxHP(attribute_data[0])}'
                content += f'\n|攻击力={level_standard.getAttack(attribute_data[1])}'
                content += f'\n|防御力={level_standard.getDef(attribute_data[2])}'
                content += f'\n|移动速度={level_standard.getMoveSpeed(attribute_data[4])}'
                content += f'\n|攻击速度={level_standard.getBaseAttackTime(attribute_data[5])}'
                content += f'\n|法术抗性={level_standard.getMagicRes(attribute_data[3])}'
                content += f'\n|元素抗性={level_standard.getEnemyRes(attribute_data[6])}'
                content += f'\n|损伤抵抗={level_standard.getEnemyDamageRes(attribute_data[7])}'
            if race_tag.__len__() > 0:
                content += '\n|种类=' + ','.join(enemy_race_dict.get(r, '未知') for r in race_tag)
            if 'abilityList' in enemy and enemy['abilityList'] != []:
                content += '\n|能力=' + format_abilityList(enemy['abilityList'], rts)
            if 'linkEnemies' in enemy and enemy['linkEnemies'] != []:
                link_e_list = []
                for link_e in enemy['linkEnemies']:
                    if link_e in enemy_handbook_table['enemyData']:
                        link_e_list.append(f"[[{enemy_handbook_table['enemyData'][link_e]['name'].strip()}]]")
                    else:
                        for ee in enemy_database['enemies']:
                            if ee['Key'] == link_e:
                                link_e_list.append(f"[[{ee['Value'][0]['enemyData']['name']['m_value'].strip()}]]")
                                break
                content += '\n|相关敌人=' + ','.join(link_e_list)
            content += '\n}}'

            content += content_lv + '\n==敌人模型==\n{{spine}}<references/>{{敌人导航}}'

            spine_content = {'prefix': '', 'name': '', 'skin': {'默认': {'战斗': {'file': ''}}}}
            spine_content['prefix'] = f'https://torappu.prts.wiki/assets/enemy_spine/{enemy["enemyId"]}/'
            spine_content['name'] = f'{enemy["name"]}'
            spine_content['skin']['默认']['战斗']['file'] = f'{enemy["enemyId"]}'

            self.wiki.edit(
                title=enemy['name'],
                text=content,
                summary='init',
                bot=None,
                minor=True,
                createonly='1'
            )
            self.wiki.protect(
                title=enemy['name'],
                protections='edit=autoconfirmed|move=sysop',
                reason='protect'
            )
            self.wiki.edit(
                title=enemy['name'] + '/spine',
                text=json.dumps(spine_content, indent=4, ensure_ascii=False),
                summary='init',
                bot=None,
                minor=True,
                createonly='1',
                contentmodel='json'
            )
            self.wiki.protect(
                title=enemy['name'] + '/spine',
                protections='edit=autoconfirmed|move=sysop',
                reason='protect'
            )
            # print(content)
            # print(json.dumps(spine_content, indent=4, ensure_ascii=False))
            print('Created: {}.'.format(enemy['name']))

    def update_data(self):
        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        rts_html = RtsHtml(self.getgd('excel/gamedata_const.json'))
        new_enemy_table = []

        enemy_list = self.wiki.category('分类:敌人')
        override_list = []
        for e in enemy_list:
            if '(敌方)' in e:
                override_list.append(e.replace('(敌方)', ''))

        enemy_db_index = {v['Key']: idx for idx, v in enumerate(enemy_database['enemies'])}
        enemy_level_dict = {'NORMAL': '普通', 'ELITE': '精英', 'BOSS': '领袖'}
        enemy_motion_dict = {'FLY': '飞行', 'WALK': '地面'}
        enemy_applyway_dict = {'ALL': '近战 远程', 'RANGED': '远程', 'MELEE': '近战', 'NONE': '不攻击'}
        enemy_damage_dict = {'PHYSIC': '物理', 'MAGIC': '法术', 'NO_DAMAGE': '无', 'HEAL': '治疗'}
        enemy_race_dict = {r['id']: r['raceName'] for r in enemy_handbook_table['raceData'].values()}
        level_standard = ClassLevel(enemy_handbook_table['levelInfoList'])

        for enemy in enemy_handbook_table['enemyData'].values():
            if enemy['name'] == '-':
                continue
            if enemy['hideInHandbook'] == True:
                continue

            attribute_data = [-1, -1, -1, -1, -1, -1, -1, -1]
            apply_way, motion = None, None
            race_tag = set()
            if enemy['enemyId'] in enemy_db_index:
                enemy_data = enemy_database['enemies'][enemy_db_index[enemy['enemyId']]]
                for idx, d in enumerate(enemy_data['Value']):
                    if d['level'] != idx:
                        print(f'enemy {enemy_data["name"]} database order error.')
                        continue
                    lv_data = d['enemyData']
                    for idx_a, k in enumerate(['maxHp', 'atk', 'def', 'magicResistance', 'moveSpeed', 'baseAttackTime', 'epResistance', 'epDamageResistance']):
                        if lv_data['attributes'][k]['m_defined'] is True and attribute_data[idx_a] == -1:
                            attribute_data[idx_a] = lv_data['attributes'][k]['m_value']
                    if lv_data['applyWay']['m_defined'] is True and apply_way is None:
                        apply_way = lv_data['applyWay']['m_value']
                    if lv_data['motion']['m_defined'] is True and motion is None:
                        motion = lv_data['motion']['m_value']
                    if lv_data['enemyTags']['m_defined'] is True and lv_data['enemyTags']['m_value']:
                        for t in lv_data['enemyTags']['m_value']:
                            race_tag.add(t)
            new_data = {
                # 'enemyId': enemy['enemyId'],
                'enemyIndex': enemy['enemyIndex'],
                # 'enemyTags': enemy['enemyTags'],
                'sortId': enemy['sortId'],
                'name': enemy['name'].strip(),
                'enemyLink': enemy['name'].strip(),
                'enemyRace': '其他',
                'enemyLevel': '',
                # 'description': enemy['description'],
                'attackType': enemy_applyway_dict.get(apply_way, "未知"),
                'damageType': " ".join(enemy_damage_dict.get(x, "未知") for x in enemy["damageType"]),
                'motion': enemy_motion_dict.get(motion, "未知"),
                'endure': level_standard.getMaxHP(attribute_data[0]),
                'attack': level_standard.getAttack(attribute_data[1]),
                'defence': level_standard.getDef(attribute_data[2]),
                'moveSpeed': level_standard.getMoveSpeed(attribute_data[4]),
                'attackSpeed': level_standard.getBaseAttackTime(attribute_data[5]),
                'resistance': level_standard.getMagicRes(attribute_data[3]),
                'enemyRes': level_standard.getEnemyRes(attribute_data[6]),
                'enemyDamageRes': level_standard.getEnemyDamageRes(attribute_data[7]),
                'ability': '',
                # 'isInvalidKilled': enemy['isInvalidKilled'],
                # 'overrideKillCntInfos': enemy['overrideKillCntInfos'],
            }
            if enemy['invisibleDetail'] is True:
                new_data['endure'] = '?'
                new_data['attack'] = '?'
                new_data['defence'] = '?'
                new_data['moveSpeed'] = '?'
                new_data['attackSpeed'] = '?'
                new_data['resistance'] = '?'
                new_data['enemyRes'] = '?'
                new_data['enemyDamageRes'] = '?'
            # 链接
            if new_data['enemyLink'] in override_list:
                new_data['enemyLink'] += '(敌方)'
            # 种族
            if race_tag.__len__() > 0:
                new_data['enemyRace'] = ','.join(enemy_race_dict.get(r, '未知') for r in race_tag)
            # 地位
            new_data['enemyLevel'] = enemy_level_dict.get(enemy['enemyLevel'], '其他')
            # 能力
            new_data['ability'] = format_abilityList(enemy['abilityList'], rts_html, html=True)

            new_enemy_table.append(new_data)

        self.wiki.edit(
            title='敌人一览/数据',
            text=json.dumps(new_enemy_table, ensure_ascii=False),
            summary='update'
        )
        # print(json.dumps(new_enemy_table, ensure_ascii = False))
        print('Updated: {}.'.format('敌人一览/数据'))

    def update_summary(self):
        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        pass

    def update_immune(self):
        def get_value(idx, v, name, k):
            if idx == 0 or v['m_defined'] == True:
                if v['m_defined'] == False:
                    s = {'i': '0', 'f': '0.0', 's': '', 'b': '无'}.get(k, '')
                    if name == '攻击范围半径':
                        s = ''
                    if name == '攻击速度':
                        s = '100'
                    if name == '数量':
                        s = '1'
                else:
                    if k == 's':
                        s = rts.compile(v["m_value"]) if v["m_value"] is not None else ''
                    elif k == 'i' and v["m_value"] >= 0:
                        s = str(int(v["m_value"]) if v["m_value"] == int(v["m_value"]) else v["m_value"])
                    elif k == 'f' and v["m_value"] >= 0:
                        s = str(v["m_value"])
                    elif k == 'b':
                        s = {True: '有', False: '无'}.get(v["m_value"], '无')
                    else:
                        s = ''
                return f'\n|{name}={s}'
            else:
                return ''

        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')
        enemy_database = self.getgd('levels/enemydata/enemy_database.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        enemy_list = self.wiki.category('分类:敌人')
        enemy_list_2 = {e.replace('(敌方)', ''):e for e in enemy_list}
        enemy_db_index = {v['Key']: idx for idx, v in enumerate(enemy_database['enemies'])}
        for enemy in enemy_handbook_table['enemyData'].values():
            if enemy['name'] == '-':
                continue
            old_page = self.wiki.read(enemy_list_2[enemy['name'].strip()].strip())
            new_page = old_page

            if enemy['enemyId'] in enemy_db_index:
                enemy_data = enemy_database['enemies'][enemy_db_index[enemy['enemyId']]]
                for idx, d in enumerate(enemy_data['Value']):
                    if d['level'] != idx:
                        print(f'enemy {enemy["name"]} database order error.')
                        continue
                    lv_data = d['enemyData']
                    lv_idx = new_page.find(f'==级别{idx}==')
                    lv_idx2 = new_page.find(f'==级别{idx+1}==')
                    lv_piece = new_page[lv_idx:lv_idx2]
                    new_immune = get_value(idx, lv_data['attributes']['disarmedCombatImmune'], '战栗抗性', 'b')
                    if new_immune != '' and '|战栗抗性=' not in lv_piece:
                        a = re.findall('(\|.*?抗性=.*?)\n', lv_piece)
                        if a != []:
                            flag = lv_piece.find(a[-1]) + len(a[-1])
                            lv_piece = lv_piece[:flag] + new_immune + lv_piece[flag:]
                            new_page = new_page[:lv_idx] + lv_piece + new_page[lv_idx2:]

            if new_page != old_page:
                self.wiki.edit(
                    title=enemy_list_2[enemy['name'].strip()].strip(),
                    text=new_page,
                    summary='更新抗性'
                )
                # print(new_page)
                print('Updated: {}.'.format(enemy['name']))
