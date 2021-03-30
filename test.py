import json
import sys

from config import config
# from jobs._temp import Temp
# from jobs.basic import Basic
# from jobs.charword import Charword
# from jobs.route import Route
# from jobs.sidebar import Sidebar
# from jobs.skin import Skin
# from jobs.stage import Stage
# from jobs.weedy import Weedy
from utils.data import GameData
from utils.unpacker import Unpacker
from utils.wiki import Wiki

if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config=config, source='Unpacker')

    # with open('/Users/Josiah/Desktop/Arknight/PRTS_bot/UnpackerData/levels/obt/rune/level_rune_04-01.json', 'r', encoding='utf-8') as f:
    #     print(Stage(wiki, gameData)._run_enemy_data(json.loads(f.read())))

    # Route(wiki, gameData).run()
    # Weedy(wiki, gameData).run()
    # Basic(wiki, gameData)._run_handbook_update()
    # Sidebar(wiki, gameData)._run_update(150)
    # Crisis(wiki, gameData).run()
    # Skin(wiki, gameData)._run_update(skin_list=['宴', '能天使', '白金'])
    # Skin(wiki, gameData).run()
    # RougeStage(wiki, gameData).run()
    # Stage(wiki, gameData).run()
    # Temp(wiki, gameData).test_yinyang()
    # Basic(wiki, gameData)._run_update(old_num=178)
    # Charword(wiki, gameData)._run_update_jp()

    # up = Unpacker(config['unpacker'])
    # up.get_all_ab()
    # up.unpack_all_data()
    # up.get_ab("battle/prefabs/[uc]skills.ab")
    # up.unpack_data("battle/prefabs/[uc]skills.ab")
