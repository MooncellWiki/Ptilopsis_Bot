import re
import time

from wikiapi import *


def update_workshop_formulas(se, url, building_data, item_table, stage_table):
    table_title = '''{| class="wikitable logo" style="text-align:center; display:table; white-space:normal;"
|-
!解锁等级!!产品!!消耗材料!!消耗龙门币!!消耗心情!!副产品产出概率!!额外解锁条件'''
    text = '\n|-\n|{}||{}||{}||{}||{}||{}||{}'

    formulas = building_data['workshopFormulas']
    formulas_content = {}
    for formula_id in formulas:
        formula = formulas[formula_id]
        require_level = '－'
        for room in formula['requireRooms']:
            if room['roomId'] == 'WORKSHOP':
                require_level = str(room['roomLevel'])
        require_stage = ', '.join(['{}星通关[[{}]]'.format(stage['rank'], stage_table['stages'][stage['stageId']]['code']) for stage in formula['requireStages']])
        if require_stage == '':
            require_stage = '－'
        formula_content = text.format(
            require_level,
            '{{{{材料消耗|{}|{}}}}}'.format(item_table['items'][formula['itemId']]['name'], formula['count']),
            ' '.join(['{{{{材料消耗|{}|{}}}}}'.format(item_table['items'][cost['id']]['name'], cost['count']) for cost in formula['costs']]),
            formula['goldCost'],
            int(formula['apCost']/360000),
            '{:.0%}'.format(formula['extraOutcomeRate']),
            require_stage
        )
        if formula['formulaType'] not in formulas_content:
            formulas_content[formula['formulaType']] = {}
        formulas_content[formula['formulaType']][formula['sortId']] = formula_content

    formulas_text = '<tabber>\n'
    formulas_text += '基建材料=\n' + table_title + ''.join([formulas_content['F_BUILDING'][formula] for formula in formulas_content['F_BUILDING']]) + '\n|}'
    formulas_text += '\n|-|\n' + '精英材料=\n' + table_title + ''.join([formulas_content['F_EVOLVE'][formula] for formula in formulas_content['F_EVOLVE']]) + '\n|}'
    formulas_text += '\n|-|\n' + '技巧概要=\n' + table_title + ''.join([formulas_content['F_SKILL'][formula] for formula in formulas_content['F_SKILL']]) + '\n|}'
    formulas_text += '\n|-|\n' + '芯片=\n' + table_title + ''.join([formulas_content['F_ASC'][formula] for formula in formulas_content['F_ASC']]) + '\n|}'
    formulas_text += '\n</tabber>'
    
    write_wiki(se, url, '用户:Seniorious/workshopFormulas', formulas_text, '')
    # print(formulas_text)
    print('Update: 用户:Seniorious/workshopFormulas.')
 