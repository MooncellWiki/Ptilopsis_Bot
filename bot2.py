from wikiapi import *
import re
import sys
import time
import bot_updateJp

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

building_data_jp = json.loads(open(path_jp + 'excel/building_data.json', 'r', encoding='utf-8').read())
character_table_jp = json.loads(open(path_jp + 'excel/character_table.json', 'r', encoding='utf-8').read())
skill_table_jp = json.loads(open(path_jp + 'excel/skill_table.json', 'r', encoding='utf-8').read())
charword_table_jp = json.loads(open(path_jp + 'excel/charword_table.json', 'r', encoding='utf-8').read())
building_data_en = json.loads(open(path_us + 'excel/building_data.json', 'r', encoding='utf-8').read())
character_table_en = json.loads(open(path_us + 'excel/character_table.json', 'r', encoding='utf-8').read())
skill_table_en = json.loads(open(path_us + 'excel/skill_table.json', 'r', encoding='utf-8').read())

bot_updateJp.update_char_name(se, url, character_table, character_table_jp, character_table_en)
bot_updateJp.update_skill_name(se, url, character_table, skill_table, character_table_jp, skill_table_jp, character_table_en, skill_table_en)
bot_updateJp.update_charword_jp(se, url, character_table, charword_table, character_table_jp, charword_table_jp)
bot_updateJp.update_furni_info(se, url, building_data, building_data_jp, building_data_en)


