import sys
from config import config
from utils.data_local import GameData
from utils.wiki import Wiki

from jobs.basic import Basic
from jobs.charword import Charword
from jobs.sidebar import Sidebar
from jobs.demand import Demand

from jobs.building_buff import BuildingBuff
from jobs.stage import Stage
from jobs.furni import Furni
from jobs.item import Item
from jobs.skin import Skin

from jobs.activity import Activity
from jobs.mission import Mission
from jobs.char_attr import CharAttr
from jobs.medal import Medal
from jobs.story_review import StoryReview

from jobs.update_jp import UpdateJp

from jobs.range import Range
from jobs.formula import Formula
from jobs.route import Route
from jobs.crisis import Crisis
from jobs.weedy import Weedy

if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'],
                ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config = config, source = 'ArknightsGameData')
    # gameData = GameData(config = config, source = 'UnpackerData')

    if 'update-new' in sys.argv:
        old_num = 150
        Basic(wiki, gameData)._run_update(old_num)  # 需id_table
        Charword(wiki, gameData).run()
        Sidebar(wiki, gameData)._run_update(old_num)  # 需id_table
        Demand(wiki, gameData).run()

    if 'update-daily' in sys.argv:
        BuildingBuff(wiki, gameData).run()
        Stage(wiki, gameData).run()
        Furni(wiki, gameData).run()
        # Item(wiki, gameData).run()

        Activity(wiki, gameData).run()
        Mission(wiki, gameData).run()
        CharAttr(wiki, gameData).run()  # 需id_table
        Medal(wiki, gameData).run()
        StoryReview(wiki, gameData).run()

    if 'update-skin' in sys.argv:
        Skin(wiki, gameData)._run_update(skin_list = [''])
        Skin(wiki, gameData).run()

    if 'update-jp' in sys.argv:
        UpdateJp(wiki, gameData).run()

    if 'update-special' in sys.argv:
        Furni(wiki, gameData)._run_update()
        Charword(wiki, gameData)._run_update()

    if 'update-weedy' in sys.argv:
        Weedy(wiki, gameData).run()

    # Route(wiki, gameData).run()
    # Formula(wiki, gameData).run()
    # Range(wiki, gameData).run()
    # Crisis(wiki, gameData).run()  # 需crisis_info

