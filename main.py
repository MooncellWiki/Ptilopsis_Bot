import os
import sys

from config import config

from jobs.basic import Basic
from jobs.building_buff import BuildingBuff
from jobs.charword import Charword
from jobs.enemy import Enemy
from jobs.furni import Furni
from jobs.item import Item
from jobs.sidebar import Sidebar
from jobs.skin import Skin
from jobs.stage import Stage
from utils.data import GameData
from utils.wiki import Wiki

if __name__ == '__main__':
    wiki = Wiki(config['apiUrl'], config['username'], config['password'], ('dev' if '-dev' in sys.argv else 'product'))
    if '--remote' in sys.argv:
        conf_remote = config
        conf_remote['version'] = 'version_remote.json'
        gameData = GameData(config=conf_remote, source='Unpacker')
    else:
        gameData = GameData(config=config, source='Unpacker')
    if '--check' in sys.argv:
        if not gameData.unpacker.check_update():
            print('No version update. Program exit.')
            exit()
    elif '--check-jp' in sys.argv:
        sign1 = gameData.unpacker.check_update('JP')
        sign2 = gameData.unpacker.check_update('US')
        if not sign1 and not sign2:
            print('No version update. Program exit.')
            exit()
    elif '--check-global' in sys.argv:
        gameData.unpacker.check_all_update()
        exit()

    if 'new' in sys.argv:
        Sidebar(wiki, gameData).update() # 先sidebar，避免影响old_num
        Basic(wiki, gameData).run()
        Charword(wiki, gameData).run()

    if 'regular' in sys.argv:
        BuildingBuff(wiki, gameData).run()
        Stage(wiki, gameData).run()
        Enemy(wiki, gameData).run()
        Enemy(wiki, gameData).update_data()
        Skin(wiki, gameData).run()
        Furni(wiki, gameData).run()
        Item(wiki, gameData).run()

        from jobs.activity import Activity
        Activity(wiki, gameData).run()
        from jobs.mission import Mission
        Mission(wiki, gameData).run()
        from jobs.char_attr import CharAttr
        CharAttr(wiki, gameData).run()
        from jobs.medal import Medal
        Medal(wiki, gameData).run()
        from jobs.story_review import StoryReview
        StoryReview(wiki, gameData).run()
        from jobs.term import Term
        Term(wiki, gameData).run()

    if 'special' in sys.argv:
        # Furni(wiki, gameData).update()
        # Charword(wiki, gameData).update()
        Basic(wiki, gameData).update_handbook()  # 干员密录
        Stage(wiki, gameData).run_memory()  # 悖论模拟
        # Stage(wiki, gameData).run_crisis()  # 需crisis_info
        # Stage(wiki, gameData).run_campaign()
        # Stage(wiki, gameData).run_id('levels/obt/rune/level_rune_07-01.json')
        
        # from jobs.route import Route
        # Route(wiki, gameData).run()
        # from jobs.formula import Formula
        # Formula(wiki, gameData).run()
        # from jobs.range import Range
        # Range(wiki, gameData).run()

    if 'demand' in sys.argv:
        from jobs.demand import Demand
        Demand(wiki, gameData).run()

    if 'jp' in sys.argv:
        Charword(wiki, gameData).update_jp()
        from jobs.update_jp import UpdateJp
        UpdateJp(wiki, gameData).run()

    if 'weedy' in sys.argv:
        from jobs.weedy import Weedy
        Weedy(wiki, gameData).run()

    if '--remote' in sys.argv:
        os.system('git add .')
        os.system('git commit -m "remote update"')
        os.system('git push')
