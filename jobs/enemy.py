from utils.job import Job
from utils.richTextStyles import RichTextStyles

import json
import re
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


def format_abilityList(aList, rts):
    if aList is None or aList == []:
        return ''
    a_content = ''
    for aa in aList:
        if aa['textFormat'] == 'NORMAL':
            a_content += '·' + rts.compile(aa['text']) + '<br>'
        elif aa['textFormat'] == 'SILENCE':
            a_content += '※' + rts.compile(aa['text']) + '<br>'
        elif aa['textFormat'] == 'TITLE':
            a_content += '{{color|#FF4F0B|' + rts.compile(aa['text']) + '}}<br>'
        else:
            a_content += rts.compile(aa['text']) + '<br>'
    return a_content[:-4]


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
        for enemy in enemy_handbook_table['enemyData'].values():
            enemy['name'] = enemy['name'].strip()
            # if enemy['name'] == '-' and enemy['enemyId'] in enemy_db_index:
            #     try:
            #         enemy['name'] = enemy_database['enemies'][enemy_db_index[enemy['enemyId']]]['Value'][0]['enemyData']['name']['m_value']
            #     except:
            #         pass
            # if enemy['name'] in enemy_list or enemy['name'] == '-':
            #     continue
            if enemy['name'] not in ['啮齿兽', '饥饿啮齿兽', '伏翼兽', '惊躁伏翼兽', '荒原窃盗者', '荒原窃盗者精英', '荒原潜伏者', '荒原潜伏者精英', '荒原劫掠者', '荒原劫掠者精英', '赏金猎人弩手', '赏金猎人弩手队长', '赏金猎人扰乱者', '赏金猎人扰乱者队长', '堕天使福尔图娜', '修道院居民', '修道院居民', '“不死的黑蛇”', '“花匠”', '艺术的慈悲!', '艺术的绝杀!', '弱弹']:
                continue
            enemy_level_dict = {'NORMAL': '普通', 'ELITE': '精英', 'BOSS': '领袖'}
            enemy_damage_dict = {'PHYSIC': '物理', 'MAGIC': '法术', 'NO_DAMAGE': '不攻击', 'HEAL': '治疗'}
            content = '{{Navigator|敌人一览}}\n{{敌人信息/common'
            content += f'\n|id={enemy["sortId"]}'
            content += f'\n|名称={enemy["name"]}'
            content += f'\n|index={enemy["enemyIndex"]}'
            content += f'\n|地位级别={enemy_level_dict.get(enemy["enemyLevel"], "其他")}'
            content += f'\n|描述={rts.compile(enemy["description"])}'
            content += f'\n|攻击方式={" ".join(enemy_damage_dict.get(x, "") for x in enemy["damageType"])}'
            # content += f'\n|耐久={enemy["endure"]}'
            # content += f'\n|攻击力={enemy["attack"]}'
            # content += f'\n|防御力={enemy["defence"]}'
            # content += f'\n|法术抗性={enemy["resistance"]}'
            if 'enemyRace' in enemy and enemy['enemyRace'] is not None:
                content += f'\n|种类={enemy["enemyRace"]}'
            if 'abilityList' in enemy and enemy['abilityList'] != []:
                content += '\n|能力=' + format_abilityList(enemy['abilityList'], rts)
            content += '\n}}'

            if enemy['enemyId'] in enemy_db_index:
                enemy_data = enemy_database['enemies'][enemy_db_index[enemy['enemyId']]]
                for idx, d in enumerate(enemy_data['Value']):
                    if d['level'] != idx:
                        print(f'enemy {enemy["name"]} database order error.')
                        continue
                    lv_data = d['enemyData']
                    content += f'\n==级别{idx}=='
                    content += f'\n{{{{敌人信息/level\n|index={idx}'
                    content += get_value(idx, lv_data['description'], '描述', 's')
                    content += get_value(idx, lv_data['lifePointReduce'], '数量', 'i')
                    content += get_value(idx, lv_data['rangeRadius'], '攻击范围半径', 'f')
                    content += get_value(idx, lv_data['attributes']['maxHp'], '最大生命值', 'i')
                    content += get_value(idx, lv_data['attributes']['atk'], '攻击力', 'i')
                    content += get_value(idx, lv_data['attributes']['def'], '防御力', 'i')
                    content += get_value(idx, lv_data['attributes']['magicResistance'], '法术抗性', 'i')
                    content += get_value(idx, lv_data['attributes']['moveSpeed'], '移动速度', 'f')
                    content += get_value(idx, lv_data['attributes']['attackSpeed'], '攻击速度', 'i')
                    content += get_value(idx, lv_data['attributes']['baseAttackTime'], '攻击间隔', 'f')
                    content += get_value(idx, lv_data['attributes']['hpRecoveryPerSec'], '生命恢复速度', 'i')
                    content += get_value(idx, lv_data['attributes']['spRecoveryPerSec'], 'sp恢复速度', 'i')
                    content += get_value(idx, lv_data['attributes']['massLevel'], '重量等级', 'i')
                    content += get_value(idx, lv_data['attributes']['stunImmune'], '眩晕抗性', 'b')
                    content += get_value(idx, lv_data['attributes']['silenceImmune'], '沉默抗性', 'b')
                    content += get_value(idx, lv_data['attributes']['sleepImmune'], '沉睡抗性', 'b')
                    content += get_value(idx, lv_data['attributes']['frozenImmune'], '冻结抗性', 'b')
                    content += get_value(idx, lv_data['attributes']['levitateImmune'], '浮空抗性', 'b')
                    if 'talentBlackboard' in lv_data and lv_data['talentBlackboard']:
                        content += '\n|天赋=<!--{}-->'.format(
                            json.dumps(lv_data['talentBlackboard'], indent=4, ensure_ascii=False)
                        )
                    content += '\n}}'
            content += '\n==敌人模型==\n{{spine}}<references/>{{敌人导航}}'

            spine_content = {'prefix': '', 'name': '', 'skin': {'默认': {'战斗': {'file': ''}}}}
            spine_content['prefix'] = f'https://static.prts.wiki/spine/enemy/{enemy["enemyId"]}/'
            spine_content['name'] = f'{enemy["name"]}'
            spine_content['skin']['默认']['战斗']['file'] = f'{enemy["enemyId"]}/{enemy["enemyId"]}'

            # self.wiki.edit(
            #     title=enemy['name'],
            #     text=content,
            #     summary='init',
            #     bot=None,
            #     minor=True,
            #     createonly='1'
            # )
            # self.wiki.protect(
            #     title=enemy['name'],
            #     protections='edit=autoconfirmed|move=sysop',
            #     reason='protect'
            # )
            # self.wiki.edit(
            #     title=enemy['name'] + '/spine',
            #     text=json.dumps(spine_content, indent=4, ensure_ascii=False),
            #     summary='init',
            #     bot=None,
            #     minor=True,
            #     createonly='1',
            #     contentmodel='json'
            # )
            # self.wiki.protect(
            #     title=enemy['name'] + '/spine',
            #     protections='edit=autoconfirmed|move=sysop',
            #     reason='protect'
            # )
            print(content)
            # print(json.dumps(spine_content, indent=4, ensure_ascii=False))
            print('Created: {}.'.format(enemy['name']))

    def update_data(self):
        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')
        gamedata_const = self.getgd('excel/gamedata_const.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))
        rts_html = RtsHtml(self.getgd('excel/gamedata_const.json'))
        new_enemy_table = []

        enemy_list = self.wiki.category('分类:敌人')
        override_list = []
        for e in enemy_list:
            if '(敌方)' in e:
                override_list.append(e.replace('(敌方)', ''))

        for enemy_data in enemy_handbook_table['enemyData'].values():
            if enemy_data['name'] == '-':
                continue
            if enemy_data['hideInHandbook'] == True:
                continue
            attack_info = enemy_data['attackType']
            new_data = {
                # 'enemyId': enemy_data['enemyId'],
                'enemyIndex': enemy_data['enemyIndex'],
                # 'enemyTags': enemy_data['enemyTags'],
                'sortId': enemy_data['sortId'],
                'name': enemy_data['name'].strip(),
                'enemyLink': enemy_data['name'].strip(),
                'enemyRace': enemy_data['enemyRace'],
                'enemyLevel': enemy_data['enemyLevel'],
                # 'description': enemy_data['description'],
                'attackType': '其他',
                'damageType': '其他',
                'endure': enemy_data['endure'],
                'attack': enemy_data['attack'],
                'defence': enemy_data['defence'],
                'resistance': enemy_data['resistance'],
                'ability': enemy_data['ability'],
                # 'isInvalidKilled': enemy_data['isInvalidKilled'],
                # 'overrideKillCntInfos': enemy_data['overrideKillCntInfos'],
            }
            # 链接
            if new_data['enemyLink'] in override_list:
                new_data['enemyLink'] += '(敌方)'
            # 种族
            if new_data['enemyRace'] is None:
                new_data['enemyRace'] = '其他'
            # 地位
            new_data['enemyLevel'] = {
                'NORMAL': '普通',
                'ELITE': '精英',
                'BOSS': '领袖'
            }.get(new_data['enemyLevel'], '其他')
            # 能力
            if new_data['ability'] is None:
                new_data['ability'] = ''
            # 攻击方式
            if '不攻击' in attack_info:
                new_data['attackType'] = '不攻击'
            elif '近战' in attack_info:
                new_data['attackType'] = '近战'
            elif '远程' in attack_info:
                new_data['attackType'] = '远程'
            # 伤害类型
            if '治疗' in attack_info:
                new_data['damageType'] = '治疗'
            elif '法术' in attack_info:
                new_data['damageType'] = '法术'
            else:
                new_data['damageType'] = '物理'
            # new_data['ability'] = remove_term(new_data['ability'])
            new_data['ability'] = rts_html.compile(new_data['ability'])

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
                    new_immune = get_value(idx, lv_data['attributes']['levitateImmune'], '浮空抗性', 'b')
                    if new_immune != '' and '|浮空抗性=' not in lv_piece:
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
