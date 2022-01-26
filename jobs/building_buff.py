from utils.job import Job
from utils.richTextStyles import RichTextStyles


# def special_buff(buff_name, description):
#     if buff_name == '坚毅随和':
#         description = description.replace('额外恢复心情}}', '额外恢复心情}}{{color|#F49800|（心情每小时恢复+0.15）}}')
#     elif buff_name == '神经质':
#         description += '{{color|#F49800|（心情每小时消耗+1.5）}}'
#     elif buff_name == '至察':
#         description += '{{color|#F49800|（心情每小时消耗+0.5）}}'
#     elif buff_name in ['裁缝·α', '裁缝·β']:
#         description = description.replace('影响概率）', '影响概率）{{color|#F49800|（同类效果取最高）}}')
#     return description


def get_building_buff(building_data, rts):
    buff_format = '''{{{{后勤技能信息
|技能名={name}
|房间={room}
|技能图标={icon}
|技能描述={description}
}}}}'''
    room_format = '''=={roomName}==
{{|class="wikitable mw-collapsible mw-collapsed logo" style="text-align:center; width:100%; max-width:1000px; display:table; white-space:normal;"
! colspan="4" | {roomName}
|-
! width="30px" |
! width="100px" |名称
! width="520px" |描述
! width="350px" |持有干员
|-
{buffInfoAll}
|}}'''
    buff_text = {}
    for room in building_data['rooms']:
        buff_text[room] = {}

    for buff in building_data['buffs']:
        buff_data = building_data['buffs'][buff]
        if buff_data['buffName'] not in buff_text[buff_data['roomType']]:
            buff_text[buff_data['roomType']][buff_data['buffName']] = {
                'sortId': buff_data['sortId'],
                'text': buff_format.format(
                    name = buff_data['buffName'],
                    room = building_data['rooms'][buff_data['roomType']]['name'],
                    icon = buff_data['skillIcon'],
                    # description = special_buff(buff_data['buffName'], rts.compile(buff_data['description']))
                    description = buff_data['description']
                )
            }

    content = ''
    for room_id in buff_text:
        if buff_text[room_id] != {}:
            content += room_format.format(
                roomName = building_data['rooms'][room_id]['name'],
                buffInfoAll = '\n|-\n'.join([buff_data['text'] for buff_data in
                    sorted(buff_text[room_id].values(), key = lambda x: x['sortId'], reverse = True)])
            ) + '\n'
    return content


class BuildingBuff(Job):
    def _run(self):
        building_data = self.getgd('excel/building_data.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        origin_text = self.wiki.read('后勤技能一览')
        flag = origin_text.find('==控制中枢==')
        head = origin_text[:flag].rstrip()
        content = head + '\n' + get_building_buff(building_data, rts).rstrip()

        if content != origin_text:
            self.wiki.edit(
                title = '后勤技能一览',
                text = content,
                summary = 'update',
                bot = None,
                minor = True
            )
            # print(content)
            print('Updated: {}.'.format('后勤技能一览'))
        else:
            print('Same: {}.'.format('后勤技能一览'))
