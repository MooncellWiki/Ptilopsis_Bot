from utils.job import Job
from utils.richTextStyles import RichTextStyles

import re
import json

class Temp(Job):
    def _run(self):
        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')

        enemys = self.wiki.category('分类:敌人')

        for enemy_key in enemy_handbook_table:
            enemy_datum = enemy_handbook_table[enemy_key]

            if enemy_datum['name'] in enemys:
                old_text = self.wiki.read(enemy_datum['name'])
                replace_text = '{{{{敌人信息/common\n|id={id}\n|名称={name}\n|index={index}\n'.format(
                    id = enemy_datum['sortId'],
                    name = enemy_datum['name'],
                    index = enemy_datum['enemyIndex']
                )
            elif enemy_datum['name']+'(敌方)' in enemys:
                old_text = self.wiki.read(enemy_datum['name']+'(敌方)')
                replace_text = '{{{{敌人信息/common\n|id={id}\n|名称={name}(敌方)\n|显示名={name}\n|index={index}\n'.format(
                    id = enemy_datum['sortId'],
                    name = enemy_datum['name'],
                    index = enemy_datum['enemyIndex']
                )
            else:
                print(enemy_datum['name'], '页面未建立.')
                continue

            n1 = old_text.find('{{敌人信息/common')
            n2 = old_text.find('|地位级别')

            if n1 == -1 or n2 == -1:
                print(enemy_datum['name'], 'not find.')
                continue

            new_text = old_text[:n1] + replace_text + old_text[n2:]
            if new_text != old_text:
                print(enemy_datum['name'], 'Different.')
                old_id = re.search(r'\|id=([0-9]*)\n', old_text).group(1)
                new_id = re.search(r'\|id=([0-9]*)\n', new_text).group(1)
                print(f'old: {old_id}  new: {new_id}')
                # print(new_text)

                # self.wiki.edit(
                #     title = enemy_datum['name'],
                #     text = new_text,
                #     summary = '修正sortId'
                # )
                # # print(content)
                # print('Updated: {}.'.format(enemy_datum['name']))

    def _test(self):
        stage_table = self.getgd('excel/stage_table.json')
        roguelike_table = self.getgd('excel/roguelike_table.json')

        stage_list = self.wiki.category('分类:普通难度关卡')

        for stage_name in stage_list:
            content = self.wiki.read(stage_name)
            result = re.search('\|关卡id=(.+?)\n', content)
            if result:
                stage_id = result.group(1)
                stage_detail = stage_table['stages'][stage_id]
                if len(list(filter(lambda x:x['dropType'] in [2,3,4], stage_detail['stageDropInfo']['displayDetailRewards']))) > 0:
                    if content.find('==材料掉落==\n{{关卡材料掉落}}') == -1:
                        if content.find('==注释与链接==') == -1:
                            content = content.replace('{{关卡导航}}', '==注释与链接==\n<references/>\n{{关卡导航}}')
                        content = content.replace('==注释与链接==', '==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==')
                        self.wiki.edit(
                            title = stage_name,
                            text = content,
                            summary = '添加模板:关卡材料掉落'
                        )
                        # print(content)
                        print('添加: {}.'.format(stage_name))
                    else:
                        print('已有:', stage_name)
                else:
                    if content.find('==材料掉落==\n{{关卡材料掉落}}') == -1:
                        print('无需添加:', stage_name)
                    else:
                        content = content.replace('==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==', '==注释与链接==')
                        content = content.replace('==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==', '==注释与链接==')
                        self.wiki.edit(
                            title = stage_name,
                            text = content,
                            summary = '删去模板:关卡材料掉落'
                        )
                        # print(content)
                        print('删去多余:', stage_name)
            else:
                print('No stage id found:', stage_name)
                for sid in roguelike_table['stages']:
                    if roguelike_table['stages'][sid]['code'] + ' ' + roguelike_table['stages'][sid]['name'] == stage_name:
                        content = content.replace('|关卡类型', '|关卡id={}\n|关卡类型'.format(sid))
                        self.wiki.edit(
                            title = stage_name,
                            text = content,
                            summary = '添加肉鸽关卡stageId'
                        )
                        # print(content)
                        print('添加肉鸽关卡stageId:', stage_name)
                        break
                if content.find('==材料掉落==\n{{关卡材料掉落}}') == -1:
                    print('无需添加:', stage_name)
                else:
                    content = content.replace('==材料掉落==\n{{关卡材料掉落}}\n==注释与链接==', '==注释与链接==')
                    content = content.replace('==材料掉落==\n{{关卡材料掉落}}\n\n==注释与链接==', '==注释与链接==')
                    self.wiki.edit(
                        title = stage_name,
                        text = content,
                        summary = '删去模板:关卡材料掉落'
                    )
                    # print(content)
                    print('删去多余:', stage_name)

    def test_power(self):
        character_table = self.getgd('excel/character_table.json')
        handbook_team_table = self.getgd('excel/handbook_team_table.json')

        def get_power(k):
            if k == None:
                return '-'
            if k in handbook_team_table:
                return handbook_team_table[k]['powerName']
            else:
                return '?'

        for char_key in character_table:
            char_info = character_table[char_key]
            if char_info['profession'] == 'TRAP' or char_info['profession'] == 'TOKEN':
                continue
            print('%s: %s/%s/%s' % (char_info['name'], get_power(char_info['nationId']), get_power(char_info['groupId']), get_power(char_info['teamId'])))

    def test_p_name(self):
        handbook_team_table = self.getgd('excel/handbook_team_table.json')

        content = ''

        for p in handbook_team_table.values():
            if p['powerName'] == '无团队':
                continue
            p_name = f"分类:属于{p['powerName']}的干员"
            self.wiki.edit(
                title = p_name,
                text = content,
                summary = 'init'
            )
            # print(content)
            print('Created: {}.'.format(p_name))

    def test_yinyang(self):
        stage_table = self.getgd('excel/stage_table.json')

        for stage_id in stage_table['stages']:
            stage_detail = stage_table['stages'][stage_id]
            if stage_detail['stageType'] not in ['MAIN', 'SUB', 'DAILY', 'ACTIVITY', 'SPECIAL_STORY'] or stage_detail[
                'difficulty'] == 'FOUR_STAR':
                continue
            stage_page_name = stage_detail['code'].strip() + ' ' + stage_detail['name'].strip()
            if 'WR-' not in stage_detail['code']:
                continue

            if stage_detail['levelId']:
                try:
                    level_table = self.getgd('levels/' + stage_detail['levelId'] + '.json')
                except:
                    print('Cannot find level data of {}.'.format(stage_page_name))
                    continue
            else:
                continue

            def tile_diff(t):
                flag = 0
                if t is None:
                    return False
                if t[0]['key'] == 'dynamic' and t[0]['valueStr'] == None:
                    flag += 1
                if t[1]['key'] == 'buff_yinyang[same].atk_scale' and t[1]['value'] == 0.6 and t[1]['valueStr'] == None:
                    flag += 1
                if t[2]['key'] == 'buff_yinyang[diff].atk_scale' and t[2]['value'] == 1.4 and t[2]['valueStr'] == None:
                    flag += 1
                if flag == 3:
                    return True
                else:
                    return False

            print(stage_page_name)
            flag = False
            for tile in level_table['mapData']['tiles']:
                if 'yinyang' in tile['tileKey'] and tile['tileKey'] != 'tile_yinyang_switch':
                    flag = True
                    if not tile_diff(tile['blackboard']):
                        print('Warning:', stage_page_name, tile['blackboard'])
            if not flag:
                print(stage_page_name, '无晦明')


