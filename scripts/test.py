from config import config

# from jobs.basic import Basic
# from jobs.charword import Charword
# from jobs.sidebar import Sidebar
# from jobs.skin import Skin
# from jobs.stage import Stage
# from jobs.furni import Furni
# from jobs.weedy import Weedy
from utils.data import GameData
# from utils.wiki import Wiki
# from jobs._temp import Temp
# from jobs.enemy import Enemy
# from jobs.route import Route
# from jobs.furni import Furni
# from jobs.item import Item
# from jobs.skin import Skin
# from jobs.stage import Stage

if __name__ == "__main__":
    # wiki = Wiki(config['apiUrl'], config['username'], config['password'],
    #             ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config=config, source="Unpacker")

    # Stage(wiki, gameData).run()
    # Enemy(wiki, gameData).run()
    # Enemy(wiki, gameData).update_data()
    # Skin(wiki, gameData).run()
    # print('flag1')
    # Furni(wiki, gameData).run()
    # print('flag2')
    # Item(wiki, gameData).run()
    # Route(wiki,gameData).run()

    # up = Unpacker(config)
    # up.get_all_ab()
    # up.unpack_all_data()
    # up.get_ab("arts/teamicon/team_icon_hub.ab")
    # up.unpack_data("gamedata/excel/building_data.ab")
