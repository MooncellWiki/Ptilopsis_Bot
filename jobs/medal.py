from utils.job import Job
from utils.richTextStyles import RichTextStyles


def parse_item(item, character_table, building_data, item_table):
    if item['type'] == 'CHAR':
        return character_table[item['id']]['name']
    elif item['type'] == 'FURN':
        return building_data['customData']['furnitures'][item['id']]['name']
    elif item['id'] in item_table['items']:
        return '{{{{材料消耗|{}|{}}}}}'.format(
            item_table['items'][item['id']]['name'].rstrip(),
            item['count']
        )
    else:
        print('Unknown reward item {}.'.format(item['id']))


def update_medal(medal_table, character_table, building_data, item_table, rts):
    medal_template = '''{{{{蚀刻章
{group}|名称={name}
|稀有度={rarity}
|描述={desc}
|获得方式={getMethod}{advanceMethod}{reward}
}}}}'''

    medal_dict = {}
    for medal_type in medal_table['medalTypeData']:
        medal_dict[medal_type] = {}
    for medal in medal_table['medalList']:
        reward_list = ' '.join(
            [' '.join([parse_item(item, character_table, building_data, item_table) for item in item_group['itemList']])
             for item_group in medal['medalRewardGroup']])
        if reward_list != '':
            reward_list = '\n|奖励=' + reward_list
        medal_dict[medal['medalType']][medal['medalId']] = {
            'group': '',
            'name': medal['medalName'],
            'rarity': medal['rarity'],
            'desc': rts.compile(medal['description'].replace('\n', '<br/>')) if medal['description'] != None else '',
            'getMethod': medal['getMethod'] if medal['getMethod'] != None else '',
            'advancedMedal': medal['advancedMedal'] if medal['advancedMedal'] != None else '',
            'originMedal': medal['originMedal'] if medal['originMedal'] != None else '',
            'reward': reward_list,
            'preMedalIdList': medal['preMedalIdList']
        }
    for medal_type in medal_dict:
        for medal_key in medal_dict[medal_type]:
            medal = medal_dict[medal_type][medal_key]
            if medal['advancedMedal'] != '':
                medal_dict[medal_type][medal_key]['advancedMedal'] = '\n|镀层方式={}'.format(
                    medal_dict[medal_type][medal['advancedMedal']]['getMethod']
                )
            if medal['getMethod'] == '' and medal['preMedalIdList'] != []:
                medal_dict[medal_type][medal_key]['getMethod'] = '获得{}枚前置蚀刻章（即本套组除此蚀刻章外的所有蚀刻章）'.format(
                    len(medal['preMedalIdList'])
                )
    for medal_type in medal_table['medalTypeData']:
        for medal_group in medal_table['medalTypeData'][medal_type]['groupData']:
            for medal_key in medal_group['medalId']:
                medal_dict[medal_type][medal_key]['group'] = '|套组={}\n'.format(
                    medal_group['groupName']
                )
    content = ''
    for medal_type in medal_table['medalTypeData']:
        content += '=={}==\n'.format(medal_table['medalTypeData'][medal_type]['medalName'])
        for medal_key in medal_dict[medal_type]:
            if medal_dict[medal_type][medal_key]['group'] == '' and medal_dict[medal_type][medal_key][
                'originMedal'] == '':
                content += medal_template.format(
                    group=medal_dict[medal_type][medal_key]['group'],
                    name=medal_dict[medal_type][medal_key]['name'],
                    rarity=medal_dict[medal_type][medal_key]['rarity'],
                    desc=medal_dict[medal_type][medal_key]['desc'],
                    getMethod=medal_dict[medal_type][medal_key]['getMethod'],
                    advanceMethod=medal_dict[medal_type][medal_key]['advancedMedal'],
                    reward=medal_dict[medal_type][medal_key]['reward'],
                ) + '\n'
        for medal_group in reversed(medal_table['medalTypeData'][medal_type]['groupData']):
            group_content, advance_flag = '', ''
            for medal_key in medal_group['medalId']:
                group_content += medal_template.format(
                    group=medal_dict[medal_type][medal_key]['group'],
                    name=medal_dict[medal_type][medal_key]['name'],
                    rarity=medal_dict[medal_type][medal_key]['rarity'],
                    desc=medal_dict[medal_type][medal_key]['desc'],
                    getMethod=medal_dict[medal_type][medal_key]['getMethod'],
                    advanceMethod=medal_dict[medal_type][medal_key]['advancedMedal'],
                    reward=medal_dict[medal_type][medal_key]['reward'],
                ) + '\n'
                if medal_dict[medal_type][medal_key]['advancedMedal'] != '':
                    advance_flag = '\n|镀层=1'
            content += '''==={title_name}===
{{{{蚀刻章/套组预览
|名称={name}{advance}
|标题名称={title_name}
|标题背景=
|介绍={desc}
|内容=
{group_content}}}}}
'''.format(
                name=medal_group['groupName'].replace('蚀刻章套组', ''),
                advance=advance_flag,
                title_name=medal_group['groupName'],
                desc=medal_group['groupDesc'].replace('\n', '<br/>'),
                group_content=group_content
            )

    return content


class Medal(Job):
    def _run(self):
        medal_table = self.getgd('excel/medal_table.json')
        item_table = self.getgd('excel/item_table.json')
        building_data = self.getgd('excel/building_data.json')
        character_table = self.getgd('excel/character_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        content = update_medal(medal_table, character_table, building_data, item_table, rts)

        self.wiki.edit(
            title='用户:Seniorious/medal',
            text=content,
            summary='update',
            bot = None,
            minor = True
        )
        # print(content)
        print('Updated: {}.'.format('用户:Seniorious/medal'))
