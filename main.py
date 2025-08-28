import os
import sys
import sentry_sdk
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


sentry_sdk.init(
    dsn="https://e2e7848581775da8b4369c6b8e1856c9@ingest.sentry.mooncell.wiki/10",
    traces_sample_rate=1.0,
)
if __name__ == '__main__':
    if '--remote' in sys.argv:
        os.system('git submodule update --init --remote --recursive')
        conf_remote = config
        conf_remote['version'] = 'version_remote.json'
        gameData = GameData(config=conf_remote, source='ArknightsGameData')
    else:
        gameData = GameData(config=config, source='ArknightsGameData')
    flag_force = True if '--force' in sys.argv else False
    if '--check' in sys.argv:
        os.system('git submodule update --remote')
        if not gameData.unpacker.check_update() and not flag_force:
            print('No version update. Program exit.')
            exit()
    elif '--check-jp' in sys.argv:
        sign1 = gameData.unpacker.check_update('JP')
        sign2 = gameData.unpacker.check_update('US')
        gameData.unpacker.check_update('KR')
        if not sign1 and not sign2:
            print('No version update. Program exit.')
            exit()
    elif '--check-global' in sys.argv:
        gameData.unpacker.check_all_update()
        exit()

    wiki = Wiki(config['apiUrl'], config['username'], config['password'], ('dev' if '-dev' in sys.argv else 'product'))
    flag_new_char = False
    if 'new' in sys.argv: 
        Sidebar(wiki, gameData).update() # 先sidebar，避免影响old_num
        flag_new_char = Basic(wiki, gameData).run()
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
        Basic(wiki, gameData).update()  # 干员详情
        Basic(wiki, gameData).update_handbook()  # 干员密录
        Stage(wiki, gameData).run_memory()  # 悖论模拟
        Stage(wiki, gameData).run_campaign()  # 剿灭
        # Stage(wiki, gameData).run_crisis()  # 需crisis_info
        # Stage(wiki, gameData).run_id('levels/obt/recalrune/level_recalrune_01-01.json')
        # Stage(wiki, gameData).run_rogue_like()
        Charword(wiki, gameData).update()
        
        # from jobs.route import Route
        # Route(wiki, gameData).run()
        # from jobs.formula import Formula
        # Formula(wiki, gameData).run()
        # from jobs.range import Range
        # Range(wiki, gameData).run()

    if 'demand' in sys.argv or flag_new_char:
        pass
        # from jobs.demand import Demand
        # Demand(wiki, gameData).run()

    if 'jp' in sys.argv:
        Charword(wiki, gameData).update()
        from jobs.update_jp import UpdateJp
        UpdateJp(wiki, gameData).run()

    if 'weedy' in sys.argv:
        from jobs.weedy import Weedy
        Weedy(wiki, gameData).run()

    if '--remote' in sys.argv:
        os.system('git add .')
        os.system('git commit -m "remote update"')
        os.system('git push')
