import os

import anyio
import click
import sentry_sdk

from ptilopsis.config import Config, Settings, config, get_settings
from ptilopsis.jobs import discover_jobs
from ptilopsis.log import logger
from ptilopsis.utils.data import YOSTAR_DIR, GameData
from ptilopsis.utils.job import JobContext, run_jobs
from ptilopsis.utils.wiki import Wiki

MODE_JOBS: dict[str, list[str]] = {
    # 先 sidebar，避免影响 old_num
    "new": ["sidebar.update", "basic.run", "charword.run"],
    "regular": [
        "building_buff.run",
        "stage.run",
        "enemy.run",
        "enemy.update_data",
        "skin.run",
        "furni.run",
        "item.run",
        "relic.run",
        "newModule.run",
        "activity.run",
        "mission.run",
        "char_attr.run",
        "medal.run",
        "story_review.run",
        "term.run",
    ],
    "special": [
        # "furni.update",
        "basic.update",  # 干员详情
        "basic.update_handbook",  # 干员密录
        "stage.run_memory",  # 悖论模拟
        "stage.run_campaign",  # 剿灭
        # "stage.run_crisis",  # 需 crisis_info
        # "stage.run_rogue_like",
        # "stage.run_recalrune",
        "charword.update",
        # "route.run", "formula.run", "range.run",
    ],
    # "demand.run" 尚未启用
    "demand": [],
    "jp": ["charword.update", "update_jp.run"],
    "weedy": ["weedy.run"],
    "relic": ["relic.run"],
}
"""各模式按顺序执行的 job 名(``<模块>.<函数>``),多个模式按这里的键顺序合并。"""

MODES = list(MODE_JOBS)


def jobs_for(modes: tuple[str, ...]) -> list[str]:
    return list(
        dict.fromkeys(
            name for mode, names in MODE_JOBS.items() if mode in modes for name in names
        )
    )


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
    help="CI 模式：版本记录用 version_remote.json，拉取海外服数据子模块，"
    "结束后自动提交推送",
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
@click.option(
    "--relic-source",
    type=click.Path(exists=True, dir_okay=False),
    help="收藏品本地 JSON；省略时直接读取当前 CN 游戏资源",
)
@click.option(
    "--relic-state",
    type=click.Path(dir_okay=False),
    help="收藏品长期维护状态路径；可沿用旧脚本的 state 文件",
)
@click.option(
    "--relic-theme",
    "relic_themes",
    type=click.IntRange(min=1),
    multiple=True,
    help="只维护指定 rogue_N 主题编号的收藏品；可重复指定，覆盖 relic.themes 配置",
)
def main(
    check_mode: str | None,
    remote: bool,
    force: bool,
    dev: bool,
    modes: tuple[str, ...],
    relic_source: str | None,
    relic_state: str | None,
    relic_themes: tuple[int, ...],
) -> None:
    if relic_themes and "relic.run" not in jobs_for(modes):
        raise click.UsageError("--relic-theme 需要 relic 或 regular 模式")
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=1.0)

    # 有 Wiki 任务时先校验凭据再跑检查，缺失时不做任何网络请求就退出
    if modes:
        settings.require_wiki_credentials()

    if remote:
        # 国服数据在线读 torappu，只有海外服还依赖子模块
        os.system(f"git submodule update --init --remote -- {YOSTAR_DIR}")
        game_config = config.model_copy(update={"version": "version_remote.json"})
    else:
        game_config = config
    if relic_source is not None or relic_state is not None or relic_themes:
        relic_options = game_config.relic.model_dump()
        if relic_source is not None:
            relic_options["source_file"] = relic_source
        if relic_state is not None:
            relic_options["state_file"] = relic_state
        if relic_themes:
            relic_options["themes"] = sorted(set(relic_themes))
        game_config = game_config.model_copy(
            update={"relic": type(game_config.relic).model_validate(relic_options)}
        )

    # 网络 I/O 全部在 anyio 事件循环里跑（与 torappu 一致）；git 操作留在外面
    should_push = anyio.run(
        _amain, game_config, settings, check_mode, force, dev, modes
    )
    if should_push:
        _push_remote(remote)


async def _amain(
    game_config: Config,
    settings: Settings,
    check_mode: str | None,
    force: bool,
    dev: bool,
    modes: tuple[str, ...],
) -> bool:
    """检查版本、跑 job；返回是否需要提交推送。"""
    partial_relic_run = bool(game_config.relic.themes) and "relic.run" in jobs_for(
        modes
    )
    advance_version = not dev and not partial_relic_run
    gameData = GameData(config=game_config)
    try:
        if check_mode == "cn":
            if not await gameData.unpacker.check_update() and not force:
                if advance_version:
                    gameData.unpacker.commit_version()
                logger.info("No version update. Program exit.")
                return False
        elif check_mode == "jp":
            sign1 = await gameData.unpacker.check_update("JP")
            sign2 = await gameData.unpacker.check_update("US")
            await gameData.unpacker.check_update("KR")
            if not sign1 and not sign2:
                if advance_version:
                    gameData.unpacker.commit_version()
                logger.info("No version update. Program exit.")
                return False
        elif check_mode == "global":
            await gameData.unpacker.check_all_update()
            if advance_version:
                gameData.unpacker.commit_version()
            return False

        if not modes:
            if advance_version:
                gameData.unpacker.commit_version()
            return not dev

        username, password = settings.require_wiki_credentials()
        wiki = await Wiki.login(
            game_config.api_url,
            username,
            password,
            "dev" if dev else "product",
        )
        try:
            discover_jobs()
            failed = await run_jobs(jobs_for(modes), JobContext(wiki, gameData))
            if failed:
                logger.error(f"{len(failed)} job(s) failed: {', '.join(failed)}")
                raise click.ClickException(
                    "任务失败，未推进资源版本：" + ", ".join(failed)
                )
            # 局部主题更新也不消费整个版本，后续全量运行仍能处理剩余主题。
            if advance_version:
                gameData.unpacker.commit_version()
            elif partial_relic_run:
                logger.info("本轮仅维护指定收藏品主题，不推进整体资源版本。")
        finally:
            await wiki.aclose()
    finally:
        await gameData.aclose()
    return not dev


def _push_remote(remote: bool) -> None:
    """--remote 模式下把更新后的数据与版本号提交推送。"""
    if not remote:
        return
    os.system("git add .")
    os.system('git commit -m "remote update"')
    os.system("git push")


if __name__ == "__main__":
    main()
