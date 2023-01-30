import json
import sys

from config import config
from jobs._temp import Temp
# from jobs.basic import Basic
# from jobs.charword import Charword
from jobs.route import Route
# from jobs.sidebar import Sidebar
# from jobs.skin import Skin
# from jobs.stage import Stage
# from jobs.furni import Furni
# from jobs.weedy import Weedy
from jobs.enemy import Enemy
from utils.data import GameData
from utils.unpacker import Unpacker
from utils.wiki import Wiki

from jobs.enemy import Enemy
from jobs.furni import Furni
from jobs.item import Item
from jobs.skin import Skin
from jobs.stage import Stage

if __name__ == '__main__':
    wiki = Wiki(config['apiUrl'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config=config, source='Unpacker')

    # with open('/Users/Josiah/Desktop/Arknight/PRTS_bot/UnpackerData/levels/obt/rune/level_rune_04-01.json', 'r', encoding='utf-8') as f:
    #     print(Stage(wiki, gameData)._run_enemy_data(json.loads(f.read())))

    # Stage(wiki, gameData).run()
    # Enemy(wiki, gameData).run()
    # Enemy(wiki, gameData).update_data()
    # Skin(wiki, gameData).run()
    # print('flag1')
    # Furni(wiki, gameData).run()
    # print('flag2')
    # Item(wiki, gameData).run()
    Route(wiki,gameData).run()

    # up = Unpacker(config)
    # up.get_all_ab()
    # up.unpack_all_data()
    # up.get_ab("arts/teamicon/team_icon_hub.ab")
    # up.unpack_data("gamedata/excel/building_data.ab")
