from ptilopsis.config import config

# from ptilopsis.jobs import _temp, enemy, furni, item, route, skin, stage
from ptilopsis.utils.data import GameData

# from ptilopsis.utils.job import JobContext
# from ptilopsis.utils.wiki import Wiki

if __name__ == "__main__":
    # wiki = Wiki(config['apiUrl'], config['username'], config['password'],
    #             ('dev' if '-dev' in sys.argv else 'product'))
    gameData = GameData(config=config, source="Unpacker")
    # ctx = JobContext(wiki, gameData)

    # stage.run(ctx)
    # enemy.run(ctx)
    # enemy.update_data(ctx)
    # skin.run(ctx)
    # print('flag1')
    # furni.run(ctx)
    # print('flag2')
    # item.run(ctx)
    # route.run(ctx)

    # up = Unpacker(config)
    # up.get_all_ab()
    # up.unpack_all_data()
    # up.get_ab("arts/teamicon/team_icon_hub.ab")
    # up.unpack_data("gamedata/excel/building_data.ab")
