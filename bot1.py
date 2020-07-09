from wikiapi import *
import re
import sys
import time
import bot_basic
import bot_furni
import bot_buildingBuff
import bot_charword
import bot_demand
import bot_formula
import bot_skin
import bot_mission
import bot_sidebar
import bot_stage
import bot_activity
import bot_charattr

url = 'http://edit.ak.mooncell.wiki/api.php'
se = login_wiki('botPtilopsis', sys.argv[1], url)
path = './ArknightsGameData/zh_CN/gamedata/'
path_jp = './ArknightsGameData/ja_JP/gamedata/'
path_us = './ArknightsGameData/en_US/gamedata/'
path_kr = './ArknightsGameData/ko_KR/gamedata/'

character_table = json.loads(open(path + 'excel/character_table.json', 'r', encoding='utf-8').read())
skill_table = json.loads(open(path + 'excel/skill_table.json', 'r', encoding='utf-8').read())
charword_table = json.loads(open(path + 'excel/charword_table.json', 'r', encoding='utf-8').read())
building_data = json.loads(open(path + 'excel/building_data.json', 'r', encoding='utf-8').read())
item_table = json.loads(open(path + 'excel/item_table.json', 'r', encoding='utf-8').read())
team_table = json.loads(open(path + 'excel/handbook_team_table.json', 'r', encoding='utf-8').read())
gamedata_const = json.loads(open(path + 'excel/gamedata_const.json', 'r', encoding='utf-8').read())
stories_table = json.loads(open(path + 'excel/handbook_info_table.json', 'r', encoding='utf-8').read())
skin_table = json.loads(open(path + 'excel/skin_table.json', 'r', encoding='utf-8').read())
id_table = json.loads(open('character_id.json', 'r', encoding='utf-8').read())
mission_table = json.loads(open(path + 'excel/mission_table.json', 'r', encoding='utf-8').read())
activity_table = json.loads(open(path + 'excel/activity_table.json', 'r', encoding='utf-8').read())
stage_table = json.loads(open(path + 'excel/stage_table.json', 'r', encoding = 'utf-8').read())

# old_num = 139
# skin_list = []

# bot_basic.create_char(se, url, old_num, character_table, skill_table, building_data, item_table, team_table, gamedata_const, stories_table, skin_table, id_table)
# bot_charword.create_charword(se, url, old_num, character_table, charword_table, id_table)
# bot_sidebar.update_sidebar(se, url, old_num, id_table)
# bot_skin.update_randomFig(se, url, character_table, skin_table)
# bot_demand.update_mat_demand(se, url, character_table, item_table)

bot_buildingBuff.update_buildingBuff_list(se, url, building_data, gamedata_const)
bot_stage.create_stage(se, url, building_data, item_table, character_table, gamedata_const, stage_table, path)
bot_furni.create_furni(se, url, building_data, item_table)
bot_furni.create_themes(se, url, building_data)
# bot_skin.update_skin(se, url, character_table, skin_table, skin_list)

bot_mission.update_mission(se, url, mission_table, item_table, gamedata_const)
bot_activity.update_activity(se, url, activity_table, item_table, building_data, character_table, skin_table, gamedata_const)
bot_charattr.get_char_attr(se, url, character_table, id_table)
bot_skin.update_skin_handbook(se, url, character_table, skin_table)
bot_formula.update_workshop_formulas(se, url, building_data, item_table, stage_table)
# bot_buildingBuff.update_buildingBuff_data(se, url, building_data, character_table, gamedata_const)

# bot_furni.update_furni_desc(se, url, building_data, item_table)
# bot_charword.update_charword(se, url, character_table, charword_table)

