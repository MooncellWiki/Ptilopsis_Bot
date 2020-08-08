import sys
import json
from config import config
from utils.data_local import GameData
from utils.wiki import Wiki

# from jobs.route import Route
# from jobs.gacha import Gacha
# from jobs.crisis import Crisis
# from jobs.stage import Stage
from jobs.weedy import Weedy
from jobs.basic import Basic


if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    # gameData = GameData(config = config, source = 'ArknightsGameData')
    gameData = GameData(config = config, source = 'UnpackerData')

    # with open('/Users/Josiah/Desktop/Arknight/PRTS_bot/UnpackerData/levels/obt/rune/level_rune_04-01.json', 'r', encoding = 'utf-8') as f:
    #     print(Stage(wiki, gameData)._run_enemy_data(json.loads(f.read())))

    # Route(wiki, gameData).run()
    Weedy(wiki, gameData).run()
    # Basic(wiki, gameData)._run_update(147)
    # Crisis(wiki, gameData).run()
