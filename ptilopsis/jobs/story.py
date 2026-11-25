"""发布剧情页、剧情导航和旧版模拟器数据。"""

import json
from collections import Counter
from pathlib import Path

import anyio

from ptilopsis.config import get_settings
from ptilopsis.jobs._story_catalog import Catalog, Script, script_path, title_key
from ptilopsis.jobs._story_wikitext import (
    NAV_FOOTER,
    NAVIGATION,
    SUBPAGE_REQUIRED,
    add_stage_links,
    add_story_fields,
    navigation_links,
    render_navigation,
    render_story,
    replace_story_script,
)
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import SkipJob, job
from ptilopsis.utils.wiki import PageRevision, Wiki


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
    wiki: Wiki, story: Script, current: PageRevision | None, script: str | None
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
        await wiki.edit(
            title=story.title,
            text=render_story(story, script, subpage=subpage),
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
    candidates = []
    for path, story in catalog.stories.items():
        live_titles = catalog.published.get(path, set())
        if exports is not None and path not in exports:
            continue
        if exports is None and story.title in catalog.complete:
            continue
        if len(live_titles) > 1 or titles[title_key(story.title)] > 1:
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
        await _sync_story(wiki, story, current, script)


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
async def navigation(wiki: Wiki, catalog: Catalog) -> None:
    current = (await wiki.read_revisions([NAVIGATION])).get(NAVIGATION)
    if not current or current.redirect or current.contentmodel != "wikitext":
        raise SkipJob(f"找不到可更新的 {NAVIGATION}")
    text = render_navigation(catalog.main, catalog.activities)
    lost = navigation_links(current.text) - navigation_links(text)
    if lost or not current.text.rstrip().endswith(NAV_FOOTER):
        sample = "、".join(sorted(lost)[:5])
        logger.warning(f"剧情导航含有当前资源版本或特例配置未覆盖的内容：{sample}")
        return
    await wiki.edit_revision(current, text, "更新剧情导航", bot=None)


@job
async def stage_links(wiki: Wiki, catalog: Catalog) -> None:
    stages: dict[str, dict[str, Script]] = {}
    unindexed = [
        story.title
        for story in catalog.stories.values()
        if not catalog.published.get(story.path) and story.kind != "干员密录"
    ]
    resolved = await wiki.resolve(unindexed)
    for story in catalog.stories.values():
        title, _, tag = story.title.rpartition("/")
        if story.kind == "干员密录" or tag not in {"BEG", "END", "NBT"}:
            continue
        published = catalog.published.get(story.path, set())
        if published != {story.title} and resolved.get(story.title) != story.title:
            continue
        stages.setdefault(title, {})[tag] = story
    revisions = await wiki.read_revisions(stages)
    for title, current in revisions.items():
        if current.redirect or current.contentmodel != "wikitext":
            continue
        if text := add_stage_links(current.text, title, stages[title]):
            await wiki.edit_revision(current, text, "更新关卡剧情跳转")


WIDGETS = {
    "story_variables.json": ("Widget:Data_Audio", "wikitext"),
    "data_image.txt": ("Widget:Data_Image", "wikitext"),
    "data_char.txt": ("Widget:Data_Char", "wikitext"),
    "character.json": ("Widget:Data_Link", "text"),
    "data_override.txt": ("Widget:Data_Override", "wikitext"),
    "Arknights-ScenarioSimulator.html": ("Widget:ScenarioSimulator", "wikitext"),
}


def _widget_keys(filename: str, text: str) -> set[str]:
    if filename in {"story_variables.json", "character.json"}:
        data = json.loads(text)
        if not isinstance(data, dict) or not data:
            raise ValueError(f"{filename} 必须是非空 JSON 对象")
        if filename == "character.json" and any(
            not isinstance(character, dict)
            or not isinstance(character.get("array"), list)
            or "groups" in character
            for character in data.values()
        ):
            raise ValueError("character.json 需要旧版模拟器的角色映射")
        return set(data)
    if filename in {"data_image.txt", "data_char.txt"}:
        keys = set()
        for row in text.strip().splitlines():
            key, _, url = row.partition(",")
            if not key or not url.startswith(("https://", "http://")):
                raise ValueError(f"{filename} 中有无效资源行：{key!r}")
            keys.add(key)
        return keys
    if filename == "data_override.txt":
        body = text.partition("<includeonly>")[2].partition("</includeonly>")[0]
        if not body.strip():
            raise ValueError(f"{filename} 缺少 includeonly 中的覆盖指令")
        keys = set()
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            key, sep, _ = line.partition("=" if line.startswith("title:") else ";")
            keys.add(key if sep else line)
        return keys
    if "<includeonly>" not in text or 'id="datas_txt"' not in text:
        raise ValueError(f"{filename} 缺少旧版模拟器的 Widget 内容")
    return set()


async def _sync_widget(wiki: Wiki, filename: str, text: str) -> None:
    title, model = WIDGETS[filename]
    current = (await wiki.read_revisions([title])).get(title)
    if not current or current.redirect or current.contentmodel != model:
        raise SkipJob(f"{title} 不存在或内容模型不符（应为 {model}）")
    text = text.rstrip("\n")
    if current.text == text:
        return
    missing = _widget_keys(filename, current.text) - _widget_keys(filename, text)
    if missing:
        logger.warning(f"{title} 导出缺少 {len(missing)} 条线上数据，跳过")
        return
    if filename.endswith(".json") and json.loads(text) == json.loads(current.text):
        return
    await wiki.edit_revision(current, text, "同步剧情模拟器数据")


@job
async def audio(wiki: Wiki, data: GameData) -> None:
    """用同一资源版本的 story_variables.json 更新 Data_Audio。"""
    await _sync_widget(
        wiki, "story_variables.json", await data.get_txt("story/story_variables.json")
    )


@job
async def publish_widgets(wiki: Wiki) -> None:
    """按文件发布旧版模拟器的导出数据和 Widget。"""
    directory = _export_dir()
    files = [directory / name for name in WIDGETS if (directory / name).is_file()]
    if not files:
        raise SkipJob(f"{directory} 没有可发布的旧版模拟器文件")
    for path in files:
        await _sync_widget(
            wiki, path.name, await anyio.Path(path).read_text(encoding="utf-8-sig")
        )
