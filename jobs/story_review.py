from utils.job import Job


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


def update_story_review(gamedata, story_review_table, character_table, building_data, item_table, zone_table):
    content = '__TOC__\n'
    content_dict = {
        'ACTIVITY_STORY': [],
        'MINI_STORY': [],
        'MAIN_STORY': []
    }
    activity_table_title = '''{{{{锚点|{name}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name}</big></big>
|-
! class="nomobile"|[[文件:情报处理室 {name}.png|160px|link={name}]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
'''
    mini_table_title = '''{{{{锚点|{name}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name}</big></big>
|-
! class="nomobile"|[[文件:情报处理室 {name}.png|160px|link={name}]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
'''
    main_table_title = '''{{{{锚点|{name2}}}}}
{{| class="wikitable" style="position:relative; text-align:center; width:100%; max-width:1000px; display:table; font-size:14px;"
! colspan="2" style="text-align:center;"|<big><big>{name1}</big></big>
|-
! class="nomobile"|[[文件:章节名称 {name2}.png|160px|link=关卡一览#主线关卡一览]]
|<div style="clear:both; overflow:auto; width:100%; height:360px; background:transparent;">
{{|
'''
    for event in story_review_table:
        event_table = ''
        if story_review_table[event]['actType'] == 'ACTIVITY_STORY':
            event_table += activity_table_title.format(name = story_review_table[event]['name'])
        elif story_review_table[event]['actType'] == 'MINI_STORY':
            event_table += mini_table_title.format(name = story_review_table[event]['name'])
        elif story_review_table[event]['actType'] == 'MAIN_STORY':
            event_table += main_table_title.format(
                name1 = zone_table['zones'][story_review_table[event]['id']]['zoneNameFirst'] + ' ' +
                        zone_table['zones'][story_review_table[event]['id']]['zoneNameSecond'],
                name2 = zone_table['zones'][story_review_table[event]['id']]['zoneNameFirst']
            )

        story_list = []
        for story in story_review_table[event]['infoUnlockDatas']:
            if story['storyInfo']:
                try:
                    story_info = gamedata.get_txt('story/[uc]' + story['storyInfo'] + '.txt', 'cn').rstrip().replace(
                        '\n', '<br/>')
                except:
                    print('路径名错误：', 'story/[uc]' + story['storyInfo'] + '.txt')
                    story_info = '{{color|red|剧情简介文件路径错误}}'
            else:
                story_info = ''
            story_list.append(
                '{{{{剧情简介|{}|{}|{}|{}}}}}'.format(story['storyCode'], story['storyName'], story['avgTag'], story_info))
        event_table += '\n|-\n'.join(story_list) + '\n|}</div>'
        if story_review_table[event]['rewards']:
            event_table += '\n|-\n!解锁报酬\n|' + ''.join(
                [parse_item(item, character_table, building_data, item_table) for item in
                    story_review_table[event]['rewards']])
        event_table += '\n|}\n'
        content_dict[story_review_table[event]['actType']].append(event_table)
    content += '==公共事务实录==\n' + ''.join(content_dict['ACTIVITY_STORY'])
    content += '==特别行动记述==\n' + ''.join(content_dict['MINI_STORY'])
    content += '==主线剧情==\n' + ''.join(content_dict['MAIN_STORY'])

    return content


class StoryReview(Job):
    def _run(self):
        story_review_table = self.getgd('excel/story_review_table.json')
        character_table = self.getgd('excel/character_table.json')
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')
        zone_table = self.getgd('excel/zone_table.json')

        content = update_story_review(self.gamedata, story_review_table, character_table, building_data, item_table,
            zone_table)

        self.wiki.edit(
            title = '用户:Seniorious/情报处理室',
            text = content,
            summary = 'update'
        )
        # print(content)
        print('Updated: {}.'.format('用户:Seniorious/情报处理室'))
