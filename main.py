import sys
import os

from config import config
from jobs.activity import Activity
from jobs.basic import Basic
from jobs.building_buff import BuildingBuff
from jobs.char_attr import CharAttr
from jobs.charword import Charword
from jobs.demand import Demand
from jobs.enemy import Enemy
from jobs.furni import Furni
from jobs.formula import Formula
from jobs.item import Item
from jobs.medal import Medal
from jobs.mission import Mission
from jobs.route import Route
from jobs.range import Range
from jobs.sidebar import Sidebar
from jobs.skin import Skin
from jobs.stage import Stage
from jobs.story_review import StoryReview
from jobs.update_jp import UpdateJp
from jobs.weedy import Weedy
from utils.data_local import GameData
from utils.wiki import Wiki

if __name__ == '__main__':
    wiki = Wiki(config['api_url'], config['username'], config['password'], ('dev' if '-dev' in sys.argv else 'product'))
    if '--git-repo' in sys.argv:
        gameData = GameData(config=config, source='ArknightsGameData')
    else:
        gameData = GameData(config=config, source='UnpackerCN')
        # gameData = GameData(config=config, source='ArknightsGameData')
        # gameData = GameData(config=config, source='UnpackerData')
        if '--check' in sys.argv:
            if not gameData.unpacker.check_update():
                print('No version update. Program exit.')
                exit()

    if 'new' in sys.argv:
        old_num = 186
        Basic(wiki, gameData).update(old_num)
        Charword(wiki, gameData).run()
        Sidebar(wiki, gameData).update(old_num)

    if 'daily' in sys.argv:
        BuildingBuff(wiki, gameData).run()
        Stage(wiki, gameData).run()
        Furni(wiki, gameData).run()
        Item(wiki, gameData).run()
        # Enemy(wiki, gameData).run()
        Enemy(wiki, gameData).update_data()

        Activity(wiki, gameData).run()
        Mission(wiki, gameData).run()
        CharAttr(wiki, gameData).run()
        Medal(wiki, gameData).run()
        StoryReview(wiki, gameData).run()

    if 'skin' in sys.argv:
        Skin(wiki, gameData).update(skin_list=[])
        Skin(wiki, gameData).run()

    if 'demand' in sys.argv:
        Demand(wiki, gameData).run()

    if 'special' in sys.argv:
        # Furni(wiki, gameData).update()
        # Charword(wiki, gameData).update()
        # Route(wiki, gameData).run()
        # Formula(wiki, gameData).run()
        # Range(wiki, gameData).run()
        Basic(wiki, gameData).update_handbook()  # 干员密录
        Stage(wiki, gameData).run_memory()  # 悖论模拟
        # Stage(wiki, gameData).run_crisis()  # 需crisis_info
        # Stage(wiki, gameData).run_campaign()
        # Stage(wiki, gameData).run_id('levels/activities')

    if 'jp' in sys.argv:
        Charword(wiki, gameData).update_jp()
        UpdateJp(wiki, gameData).run()

    if 'weedy' in sys.argv:
        Weedy(wiki, gameData).run()
