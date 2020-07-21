import re
import time
from datetime import datetime, timedelta
import pytz

from wikiapi import *

table_title = '{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:800px;"'


def parse_reward(reward, item_table, building_data, character_table, skin_table):
    if reward['type'] == 'FURN':
        return '{{{{关卡报酬|家具=yes|{name}||50px}}}}'.format(
            name = building_data['customData']['furnitures'][reward['id']]['name']
        )
    elif reward['type'] == 'CHAR':
        return '{{{{招聘合同|{name}|50}}}}'.format(
            name = character_table[reward['id']]['name']
        )
    elif reward['type'] == 'CHAR_SKIN':
        skin_count = 0
        char_key = skin_table['charSkins'][reward['id']]['charId'] + '@'
        for skin_id in skin_table['charSkins']:
            if char_key in skin_id:
                skin_count += 1
            if reward['id'] == skin_id:
                break
        return '{{{{皮肤头像|{name}|50px|{no}}}}}'.format(
            name = character_table[skin_table['charSkins'][reward['id']]['charId']]['name'],
            no = skin_count
        )
    else:
        return '{{{{材料消耗|{name}|{count}|50px}}}}'.format(
            name = item_table['items'][reward['id']]['name'],
            count = reward['count']
        )


def parse_collection(collection, item_table, building_data, character_table, skin_table):
    if collection['itemType'] == 'FURN':
        return '{{{{关卡报酬|家具=yes|{name}||50px}}}}'.format(
            name = building_data['customData']['furnitures'][collection['itemId']]['name']
        )
    elif collection['itemType'] == 'CHAR':
        return '{{{{招聘合同|{name}|50}}}}'.format(
            name = character_table[collection['itemId']]['name']
        )
    elif collection['itemType'] == 'CHAR_SKIN':
        skin_count = 0
        char_key = skin_table['charSkins'][collection['itemId']]['charId'] + '@'
        for skin_id in skin_table['charSkins']:
            if char_key in skin_id:
                skin_count += 1
            if collection['itemId'] == skin_id:
                break
        return '{{{{皮肤头像|{name}|50px|{no}}}}}'.format(
            name = character_table[skin_table['charSkins'][collection['itemId']]['charId']]['name'],
            no = skin_count
        )
    else:
        return '{{{{材料消耗|{name}|{count}|50px}}}}'.format(
            name = item_table['items'][collection['itemId']]['name'],
            count = collection['itemCnt']
        )


def update_activity(se, url, activity_table, item_table, building_data, character_table, skin_table):
    activity_dict = {}
    for activity in activity_table['missionData']:
        activity_dict[activity['id']] = {
            'id': activity['id'],
            'description': activity['description'],
            'missionGroup': activity['missionGroup'],
            'rewards': ''
        }
        for reward in activity['rewards']:
            activity_dict[activity['id']]['rewards'] += parse_reward(reward, item_table, building_data, character_table, skin_table)
    activity_text_dict = {}
    for mission in activity_table['missionGroup']:
        activity_text_dict[mission['id']] = ''
        if activity_table['basicInfo'][mission['id']]['startTime'] != mission['startTs'] or activity_table['basicInfo'][mission['id']]['rewardEndTime'] != mission['endTs']:
            print(mission['id'], 'time not match!')
        start_time = datetime.fromtimestamp(activity_table['basicInfo'][mission['id']]['startTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.fromtimestamp(activity_table['basicInfo'][mission['id']]['endTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        end_time2 = datetime.fromtimestamp(activity_table['basicInfo'][mission['id']]['rewardEndTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        activity_text_dict[mission['id']] += table_title + '\n!colspan="3"|开始时间:{s_t}<br/>结束时间:{e_t}<br/>兑换结束时间:{e_t2}'.format(
            s_t = start_time,
            e_t = end_time,
            e_t2 = end_time2
        ) + '\n|-\n!id||内容||奖励'
        for mission_id in mission['missionIds']:
            if activity_dict[mission_id]['missionGroup'] != mission['id']:
                print(mission_id, 'group not match!')
            activity_text_dict[mission['id']] += '\n|-\n|{id}\n|{desc}\n|{reward}'.format(
                id = activity_dict[mission_id]['id'],
                desc = activity_dict[mission_id]['description'],
                reward = activity_dict[mission_id]['rewards']
            )
        activity_text_dict[mission['id']] += '\n|}'
    activity_text = '==活动=='
    for act_info in activity_table['basicInfo']:
        activity_text += '\n==={name}===\n'.format(
            name = activity_table['basicInfo'][act_info]['name']
        )
        if act_info in activity_text_dict:
            activity_text += activity_text_dict[act_info]
        else:
            activity_text += '{|class = "wikitable" style = "text-align:center; display:table; white-space:normal; width:800px;"'
            activity_text += '\n!colspan="3"|开始时间:{s_t}<br/>结束时间:{e_t}<br/>兑换结束时间:{e_t2}'.format(
                s_t = datetime.fromtimestamp(activity_table['basicInfo'][act_info]['startTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S'),
                e_t = datetime.fromtimestamp(activity_table['basicInfo'][act_info]['endTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S'),
                e_t2 = datetime.fromtimestamp(activity_table['basicInfo'][act_info]['rewardEndTime'], pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
            ) + '\n|}'

        if activity_table['basicInfo'][act_info]['type'] == 'COLLECTION':
            item_list = '\n' + table_title + '\n!colspan="8"|奖励列表\n|-'
            item_list += '\n!width="12.5%"|点数\n!width="12.5%"|奖励'*4
            item_count = 0
            for collection in activity_table['activity']['COLLECTION'][act_info]['collections']:
                if item_count % 4 == 0:
                    item_list += '\n|-'
                item_list += '\n|{point}\n|{item}'.format(
                    point = '{{{{材料消耗|{name}|{count}|50px}}}}'.format(
                        name = item_table['items'][collection['pointId']]['name'],
                        count = collection['pointCnt']
                    ),
                    item = parse_collection(collection, item_table, building_data, character_table, skin_table)
                )
                item_count += 1
            item_list += '\n|}'
            activity_text += item_list
        elif activity_table['basicInfo'][act_info]['type'] == 'CHECKIN_ONLY':
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += '\n!累积登录!!奖励'
            for day in activity_table['activity']['CHECKIN_ONLY'][act_info]['checkInList']:
                reward_list = ''
                for reward in activity_table['activity']['CHECKIN_ONLY'][act_info]['checkInList'][day]['itemList']:
                    reward_list += parse_reward(reward, item_table, building_data, character_table, skin_table)
                item_list += '\n|-\n|累积登录第{days}天\n|{item}'.format(
                    days = activity_table['activity']['CHECKIN_ONLY'][act_info]['checkInList'][day]['order'],
                    item = reward_list
                )
            item_list += '\n|}'
            activity_text += item_list
        elif activity_table['basicInfo'][act_info]['type'] == 'TYPE_ACT4D0':
            milestone_name = item_table['items'][activity_table['activity']['TYPE_ACT4D0'][act_info]['tokenItem']['id']]['name']
            item_list = '\n{|class = "wikitable mw-collapsible mw-collapsed" style = "text-align:center; display:table; white-space:normal; width:500px;"'
            item_list += '\n!道具点数!!奖励'
            milestone_list = {}
            order_max = 0
            for milestone in activity_table['activity']['TYPE_ACT4D0'][act_info]['mileStoneItemList']:
                order_max = max(milestone['orderId'], order_max)
                milestone_list[milestone['orderId']] = '\n|-\n|{{{{材料消耗|{name}|{tokenNum}|50px}}}}\n|{item}'.format(
                    name = milestone_name,
                    tokenNum = milestone['tokenNum'],
                    item = parse_reward(milestone['item'], item_table, building_data, character_table, skin_table)
                )
            for milestone in activity_table['activity']['TYPE_ACT4D0'][act_info]['mileStoneStoryList']:
                order_max = max(milestone['orderId'], order_max)
                milestone_list[milestone['orderId']] = '\n|-\n|{{{{材料消耗|{name}|{tokenNum}|50px}}}}\n|{desc}'.format(
                    name = milestone_name,
                    tokenNum = milestone['tokenNum'],
                    desc = milestone['desc']
                )
            for i in range(1, order_max + 1):
                item_list += milestone_list[i]
            item_list += '\n|}'
            activity_text += item_list

    write_wiki(se, url, '用户:Seniorious/activities', activity_text, '')
    # print(activity_text)
    print('Update: 用户:Seniorious/activities.')

