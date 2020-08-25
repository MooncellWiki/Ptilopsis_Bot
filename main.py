import sys

from config import config
from jobs.activity import Activity
from jobs.basic import Basic
from jobs.building_buff import BuildingBuff
from jobs.char_attr import CharAttr
from jobs.charword import Charword
from jobs.demand import Demand
from jobs.furni import Furni
from jobs.item import Item
from jobs.medal import Medal
from jobs.mission import Mission
from jobs.sidebar import Sidebar
from jobs.skin import Skin
from jobs.stage import Stage
from jobs.story_review import StoryReview
from jobs.update_jp import UpdateJp
from jobs.weedy import Weedy
from utils.data_local import GameData
from utils.wiki import Wiki

if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
        ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config = config, source = 'ArknightsGameData')
    # gameData = GameData(config = config, source = 'UnpackerData')

    if 'new' in sys.argv:
        old_num = 157
        Basic(wiki, gameData)._run_update(old_num)  # 需id_table
        Charword(wiki, gameData).run()
        Sidebar(wiki, gameData)._run_update(old_num)  # 需id_table

    if 'daily' in sys.argv:
        BuildingBuff(wiki, gameData).run()
        Stage(wiki, gameData).run()
        Furni(wiki, gameData).run()
        Item(wiki, gameData).run()

        Activity(wiki, gameData).run()
        Mission(wiki, gameData).run()
        CharAttr(wiki, gameData).run()  # 需id_table
        Medal(wiki, gameData).run()
        StoryReview(wiki, gameData).run()

    if 'skin' in sys.argv:
        Skin(wiki, gameData)._run_update(skin_list = [''])
        Skin(wiki, gameData).run()

    if 'demand' in sys.argv:
        Demand(wiki, gameData).run()

    if 'special' in sys.argv:
        Furni(wiki, gameData)._run_update()
        Charword(wiki, gameData)._run_update()

    if 'jp' in sys.argv:
        UpdateJp(wiki, gameData).run()

    if 'weedy' in sys.argv:
        Weedy(wiki, gameData).run()

    # Route(wiki, gameData).run()
    # Formula(wiki, gameData).run()
    # Range(wiki, gameData).run()
    # Crisis(wiki, gameData).run()  # 需crisis_info
