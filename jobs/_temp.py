from utils.job import Job
from utils.richTextStyles import RichTextStyles

import re

class Temp(Job):
    def _run(self):
        enemy_handbook_table = self.getgd('excel/enemy_handbook_table.json')

        enemys = self.wiki.category('分类:敌人')

        for enemy_key in enemy_handbook_table:
            enemy_datum = enemy_handbook_table[enemy_key]

            if enemy_datum['name'] not in enemys:
                print(enemy_datum['name'], '页面未建立.')
                continue
            old_text = self.wiki.read(enemy_datum['name'])
            replace_text = '{{{{敌人信息/common\n|id={id}\n|名称={name}\n|index={index}\n'.format(
                id = enemy_datum['sortId'],
                name = enemy_datum['name'],
                index = enemy_datum['enemyIndex']
            )

            n1 = old_text.find('{{敌人信息/common')
            n2 = old_text.find('|地位级别')

            if n1 == -1 or n2 == -1:
                print(enemy_datum['name'], 'not find.')
                continue

            new_text = old_text[:n1] + replace_text + old_text[n2:]
            if new_text != old_text:
                print(enemy_datum['name'], 'Different.')
                # print(new_text)

                # self.wiki.edit(
                #     title = enemy_datum['name'],
                #     text = new_text,
                #     summary = '修正sortId'
                # )
                # # print(content)
                # print('Updated: {}.'.format(enemy_datum['name']))
