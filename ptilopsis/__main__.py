import os

import click
import sentry_sdk

from ptilopsis.config import config, get_settings
from ptilopsis.jobs.activity import Activity
from ptilopsis.jobs.basic import Basic
from ptilopsis.jobs.building_buff import BuildingBuff
from ptilopsis.jobs.char_attr import CharAttr
from ptilopsis.jobs.charword import Charword
from ptilopsis.jobs.enemy import Enemy
from ptilopsis.jobs.furni import Furni
from ptilopsis.jobs.item import Item
from ptilopsis.jobs.medal import Medal
from ptilopsis.jobs.mission import Mission
from ptilopsis.jobs.newModule import NewModule
from ptilopsis.jobs.sidebar import Sidebar
from ptilopsis.jobs.skin import Skin
from ptilopsis.jobs.stage import Stage
from ptilopsis.jobs.story_review import StoryReview
from ptilopsis.jobs.term import Term
from ptilopsis.jobs.update_jp import UpdateJp
from ptilopsis.jobs.weedy import Weedy
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.wiki import Wiki

MODES = ["new", "regular", "special", "demand", "jp", "weedy"]


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--check",
    "check_mode",
    flag_value="cn",
    default=None,
    help="检查 CN 服是否有新版本，无更新则退出",
)
@click.option(
    "--check-jp",
    "check_mode",
    flag_value="jp",
    help="检查 JP / US / KR 服是否有新版本",
)
@click.option(
    "--check-global",
    "check_mode",
    flag_value="global",
    help="检查所有海外服后退出",
)
@click.option(
    "--remote",
    is_flag=True,
    help="使用 ArknightsGameData 仓库作为数据源，结束后自动提交推送",
)
@click.option(
    "--force",
    is_flag=True,
    help="即便没有新版本也强制运行（仅对 --check 生效）",
)
@click.option(
    "--dev",
    "dev",
    is_flag=True,
    help="Wiki 客户端预览模式，仅打印将要提交的内容，不实际写入",
)
@click.argument("modes", nargs=-1, type=click.Choice(MODES))
def main(
    check_mode: str | None,
    remote: bool,
    force: bool,
    dev: bool,
    modes: tuple[str, ...],
) -> None:
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=1.0)

    # 有 Wiki 任务时先校验凭据再跑检查，缺失时不做任何网络请求就退出
    if modes:
        settings.require_wiki_credentials()

    if remote:
        os.system("git submodule update --init --remote --recursive")
        game_config = config.model_copy(update={"version": "version_remote.json"})
    else:
        game_config = config
    gameData = GameData(config=game_config, source="thirdparty/ArknightsGameData")

    if check_mode == "cn":
        os.system("git submodule update --remote")
        if not gameData.unpacker.check_update() and not force:
            gameData.unpacker.commit_version()
            logger.info("No version update. Program exit.")
            return
    elif check_mode == "jp":
        sign1 = gameData.unpacker.check_update("JP")
        sign2 = gameData.unpacker.check_update("US")
        gameData.unpacker.check_update("KR")
        if not sign1 and not sign2:
            gameData.unpacker.commit_version()
            logger.info("No version update. Program exit.")
            return
    elif check_mode == "global":
        gameData.unpacker.check_all_update()
        gameData.unpacker.commit_version()
        return

    if not modes:
        gameData.unpacker.commit_version()
        _push_remote(remote)
        return

    username, password = settings.require_wiki_credentials()
    wiki = Wiki(
        config.api_url,
        username,
        password,
        "dev" if dev else "product",
    )
    # 登录成功后才推进版本号：登录失败（凭据缺失/过期/被吊销）时保持旧版本，
    # 下一次运行仍能检测到更新并重跑，而不是被误判为「无更新」而跳过
    gameData.unpacker.commit_version()
    flag_new_char = False
    if "new" in modes:
        Sidebar(wiki, gameData).update()  # 先sidebar，避免影响old_num
        flag_new_char = Basic(wiki, gameData).run()
        Charword(wiki, gameData).run()

    if "regular" in modes:
        BuildingBuff(wiki, gameData).run()
        Stage(wiki, gameData).run()
        Enemy(wiki, gameData).run()
        Enemy(wiki, gameData).update_data()
        Skin(wiki, gameData).run()
        Furni(wiki, gameData).run()
        Item(wiki, gameData).run()
        NewModule(wiki, gameData).run()

        Activity(wiki, gameData).run()
        Mission(wiki, gameData).run()
        CharAttr(wiki, gameData).run()
        Medal(wiki, gameData).run()
        StoryReview(wiki, gameData).run()
        Term(wiki, gameData).run()

    if "special" in modes:
        # Furni(wiki, gameData).update()
        Basic(wiki, gameData).update()  # 干员详情
        Basic(wiki, gameData).update_handbook()  # 干员密录
        Stage(wiki, gameData).run_memory()  # 悖论模拟
        Stage(wiki, gameData).run_campaign()  # 剿灭
        # Stage(wiki, gameData).run_crisis()  # 需crisis_info
        # Stage(wiki, gameData).run_id('levels/activities/act2autochess')
        # Stage(wiki, gameData).run_rogue_like()
        # Stage(wiki, gameData).run_recalrune()
        Charword(wiki, gameData).update()

        # from ptilopsis.jobs.route import Route
        # Route(wiki, gameData).run()
        # from ptilopsis.jobs.formula import Formula
        # Formula(wiki, gameData).run()
        # from ptilopsis.jobs.range import Range
        # Range(wiki, gameData).run()

    if "demand" in modes or flag_new_char:
        pass
        # from ptilopsis.jobs.demand import Demand
        # Demand(wiki, gameData).run()

    if "jp" in modes:
        Charword(wiki, gameData).update()
        UpdateJp(wiki, gameData).run()

    if "weedy" in modes:
        Weedy(wiki, gameData).run()

    _push_remote(remote)


def _push_remote(remote: bool) -> None:
    """--remote 模式下把更新后的数据与版本号提交推送。"""
    if not remote:
        return
    os.system("git add .")
    os.system('git commit -m "remote update"')
    os.system("git push")


if __name__ == "__main__":
    main()
