import os

import click
import sentry_sdk

from ptilopsis.config import config, get_settings
from ptilopsis.jobs import (
    activity,
    basic,
    building_buff,
    char_attr,
    charword,
    enemy,
    furni,
    item,
    medal,
    mission,
    newModule,
    sidebar,
    skin,
    stage,
    story_review,
    term,
    update_jp,
    weedy,
)
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import JobContext
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
    ctx = JobContext(wiki, gameData)
    flag_new_char = False
    if "new" in modes:
        sidebar.update(ctx)  # 先sidebar，避免影响old_num
        flag_new_char = bool(basic.run(ctx))
        charword.run(ctx)

    if "regular" in modes:
        building_buff.run(ctx)
        stage.run(ctx)
        enemy.run(ctx)
        enemy.update_data(ctx)
        skin.run(ctx)
        furni.run(ctx)
        item.run(ctx)
        newModule.run(ctx)

        activity.run(ctx)
        mission.run(ctx)
        char_attr.run(ctx)
        medal.run(ctx)
        story_review.run(ctx)
        term.run(ctx)

    if "special" in modes:
        # furni.update(ctx)
        basic.update(ctx)  # 干员详情
        basic.update_handbook(ctx)  # 干员密录
        stage.run_memory(ctx)  # 悖论模拟
        stage.run_campaign(ctx)  # 剿灭
        # stage.run_crisis(ctx)  # 需crisis_info
        # stage.run_id(ctx, "levels/activities/act2autochess")
        # stage.run_rogue_like(ctx)
        # stage.run_recalrune(ctx)
        charword.update(ctx)

        # from ptilopsis.jobs import route
        # route.run(ctx)
        # from ptilopsis.jobs import formula
        # formula.run(ctx)
        # from ptilopsis.jobs import range
        # range.run(ctx)

    if "demand" in modes or flag_new_char:
        pass
        # from ptilopsis.jobs import demand
        # demand.run(ctx)

    if "jp" in modes:
        charword.update(ctx)
        update_jp.run(ctx)

    if "weedy" in modes:
        weedy.run(ctx)

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
