import sys
from config import config
from utils.data_local import GameData
from utils.wiki import Wiki

# from jobs.route import Route
# from jobs.gacha import Gacha
# from jobs.crisis import Crisis
from jobs.weedy import Weedy


if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    # gameData = GameData(config = config, source = 'ArknightsGameData')
    gameData = GameData(config = config, source = 'UnpackerData')

    Weedy(wiki, gameData).run()

