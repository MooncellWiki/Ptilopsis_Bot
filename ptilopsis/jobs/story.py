"""发布供 StoryPlayer 使用的剧情页。"""

import json
from collections import Counter
from pathlib import Path

import anyio

from ptilopsis.config import get_settings
from ptilopsis.jobs._story_catalog import Catalog, Script, script_path, title_key
from ptilopsis.jobs._story_wikitext import (
    SUBPAGE_REQUIRED,
    add_display_title,
    add_story_fields,
    render_story,
    replace_story_script,
)
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import SkipJob, job
from ptilopsis.utils.wiki import PageRevision, Wiki

DISPLAY_TITLES_PATH = Path(__file__).with_name("story_display_titles.json")


async def _read_display_titles() -> dict[str, str]:
    return json.loads(await anyio.Path(DISPLAY_TITLES_PATH).read_bytes())


async def _sync_data_page(
    wiki: Wiki, title: str, text: str, *, replace_existing: bool
) -> bool:
    current = (await wiki.read_revisions([title])).get(title)
    if current is None:
        result = await wiki.edit(
            title=title,
            text=text,
            summary="发布剧本数据",
            contentmodel="text",
            createonly=True,
        )
        if result is not None or wiki.mode == "dev":
            return True
        # createonly 撞到并发创建时，重新确认内容再链接过去。
        current = (await wiki.read_revisions([title])).get(title)
    if current and not current.redirect and current.contentmodel == "text":
        if current.text == text:
            return True
        if replace_existing:
            return await wiki.edit_revision(current, text, "同步剧本数据")
    logger.warning(f"已有无法接管的剧本数据页：{title}")
    return False


async def _sync_story(
    wiki: Wiki,
    story: Script,
    current: PageRevision | None,
    script: str | None,
    display_title: str | None = None,
) -> None:
    if script is not None:
        script = script.lstrip("\ufeff").replace("\r\n", "\n").strip("\n")
        if not script.strip():
            logger.warning(f"跳过空剧本：{story.path}")
            return
    if current is None:
        if script is None:
            return
        subpage = bool(SUBPAGE_REQUIRED.search(script))
        if subpage and not await _sync_data_page(
            wiki, f"{story.title}/data", script, replace_existing=False
        ):
            return
        text = render_story(story, script, subpage=subpage)
        if display_title:
            text = add_display_title(text, display_title)
        await wiki.edit(
            title=story.title,
            text=text,
            summary="发布剧情",
            createonly=True,
        )
        return
    if current.redirect or current.contentmodel != "wikitext":
        logger.warning(f"已有无法接管的剧情页：{current.title}")
        return
    text = add_story_fields(current.text, story)
    if text is None:
        logger.warning(f"剧情模拟器调用与剧本不匹配：{current.title} ({story.path})")
        return
    summary = "补齐剧情模拟器的 Cargo 参数"
    if script is not None:
        subpage = bool(SUBPAGE_REQUIRED.search(script))
        patched = replace_story_script(text, script, subpage=subpage)
        if patched is None:
            logger.warning(f"无法确认文本数据的边界：{current.title}")
            return
        text, had_subpage = patched
        if (subpage or had_subpage) and not await _sync_data_page(
            wiki, f"{current.title}/data", script, replace_existing=had_subpage
        ):
            return
        summary = "同步剧本和剧情模拟器参数"
    await wiki.edit_revision(current, text, summary)


async def _sync_pages(
    wiki: Wiki,
    catalog: Catalog,
    *,
    data: GameData | None = None,
    exports: dict[str, Path] | None = None,
) -> None:
    titles = Counter(title_key(story.title) for story in catalog.stories.values())
    display_titles = await _read_display_titles()
    candidates = []
    for path, story in catalog.stories.items():
        if exports is not None and path not in exports:
            continue
        if exports is None and story.title in catalog.complete:
            continue
        if path in catalog.ambiguous_paths or titles[title_key(story.title)] > 1:
            logger.warning(f"剧情标题或路径重复，跳过：{story.title} ({path})")
            continue
        candidates.append(story)

    revisions = await wiki.read_revisions(story.title for story in candidates)
    logger.info(f"待核对剧情页 {len(candidates)} 个，其中已有 {len(revisions)} 个")
    for story in candidates:
        current = revisions.get(story.title)
        script = None
        if exports is not None:
            script = await anyio.Path(exports[story.path]).read_text(
                encoding="utf-8-sig"
            )
        elif data is not None and current is None:
            try:
                script = await data.get_txt(f"story/{story.path}.txt")
            except FileNotFoundError:
                logger.warning(f"资源版本缺少剧本：{story.path}")
                continue
        await _sync_story(
            wiki, story, current, script, display_titles.get(title_key(story.title))
        )


@job
async def pages(wiki: Wiki, data: GameData, catalog: Catalog) -> None:
    """从 torappu 建新剧情页并补齐旧页的 Cargo 参数。"""
    await _sync_pages(wiki, catalog, data=data)


@job
async def backfill(wiki: Wiki, catalog: Catalog) -> None:
    """仅补齐已有剧情页的 Cargo 参数。"""
    await _sync_pages(wiki, catalog)


def _export_dir() -> Path:
    directory = get_settings().story_export_dir
    if not directory or not directory.is_dir():
        raise SkipJob("请将 PTILOPSIS_STORY_EXPORT_DIR 指向剧情导出目录")
    return directory


@job
async def publish_scripts(wiki: Wiki, catalog: Catalog) -> None:
    """发布指定目录 txtdata/ 下的剧本，用于定向同步已有页面的剧本。"""
    directory = _export_dir() / "txtdata"
    exports = {}
    for path in sorted(directory.rglob("*.txt")):
        relative = script_path(path.relative_to(directory).as_posix())
        if relative in catalog.stories and path.is_file():
            exports[relative] = path
        else:
            logger.warning(f"导出目录中有无法匹配剧情页的剧本：{relative}")
    if not exports:
        raise SkipJob(f"{directory} 没有可发布的剧本")
    await _sync_pages(wiki, catalog, exports=exports)


@job
async def display_titles(wiki: Wiki) -> None:
    """给既有剧情页补上从旧播放器迁移的显示标题。"""
    titles = await _read_display_titles()
    for title, page in (await wiki.read_revisions(titles)).items():
        if not page.redirect and page.contentmodel == "wikitext":
            text = add_display_title(page.text, titles[title])
            await wiki.edit_revision(page, text, "为剧情页补写显示标题")
