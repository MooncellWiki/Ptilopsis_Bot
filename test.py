import sys
import json
from config import config
from utils.data_local import GameData
from utils.wiki import Wiki
from utils.unpacker_cn import UnpackerCN

# from jobs.route import Route
# from jobs.gacha import Gacha
# from jobs.crisis import Crisis
# from jobs.stage import Stage
# from jobs.weedy import Weedy
# from jobs.sidebar import Sidebar
# from jobs.skin import Skin
from jobs.stage import Stage
# from jobs.rogue_stage import RougeStage
from jobs._temp import Temp
from jobs.basic import Basic
# from jobs.charword import Charword



if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    # gameData = GameData(config = config, source = 'ArknightsGameData')
    # gameData = GameData(config = config, source = 'UnpackerData')
    gameData = GameData(config = config, source = 'UnpackerCN')

    # with open('/Users/Josiah/Desktop/Arknight/PRTS_bot/UnpackerData/levels/obt/rune/level_rune_04-01.json', 'r', encoding = 'utf-8') as f:
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

    # up = UnpackerCN(config['unpacker'])
    # up.get_all_gamedata()
    # up.unpack_all_gamedata()
    # up.get_ab("battle/prefabs/[uc]skills.ab")
    # up.unpack_data("battle/prefabs/[uc]skills.ab")

