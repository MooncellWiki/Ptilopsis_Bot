from ptilopsis.config import config

# from ptilopsis.jobs.basic import Basic
# from ptilopsis.jobs.charword import Charword
# from ptilopsis.jobs.sidebar import Sidebar
# from ptilopsis.jobs.skin import Skin
# from ptilopsis.jobs.stage import Stage
# from ptilopsis.jobs.furni import Furni
# from ptilopsis.jobs.weedy import Weedy
from ptilopsis.utils.data import GameData

# from ptilopsis.utils.wiki import Wiki
# from ptilopsis.jobs._temp import Temp
# from ptilopsis.jobs.enemy import Enemy
# from ptilopsis.jobs.route import Route
# from ptilopsis.jobs.furni import Furni
# from ptilopsis.jobs.item import Item
# from ptilopsis.jobs.skin import Skin
# from ptilopsis.jobs.stage import Stage

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
