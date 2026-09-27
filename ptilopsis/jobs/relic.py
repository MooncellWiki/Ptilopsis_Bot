"""Automatically create and maintain collectible pages without a manifest approval."""

import json

import anyio

from ptilopsis.config import Config, RelicConfig
from ptilopsis.log import logger
from ptilopsis.relics.merge import MergeError, common_call, merge_page
from ptilopsis.relics.render import SUMMARY, UPDATE_SUMMARY, rogue_number
from ptilopsis.relics.source import (
    RelicGlossary,
    RelicTopics,
    build_records,
    render_pages,
)
from ptilopsis.relics.state import atomic_json, digest, load_state, state_lock
from ptilopsis.utils.data import GameData
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki, WikiError


def decide(draft: dict, live: dict, previous: dict | None) -> dict:
    before = live["text"]
    result = {"action": "blocked", "text": before, "managed": {}, "reason": ""}
    if live["redirect"] or before.lstrip().lower().startswith(("#redirect", "#重定向")):
        result["reason"] = "重定向页面"
    elif live["contentmodel"] != "wikitext":
        result["reason"] = "页面不是 wikitext"
    elif not live["exists"]:
        if previous is not None:
            result["reason"] = "曾维护的页面已被删除，不自动重建"
        else:
            result.update(
                action="create",
                text=draft["text"],
                managed=common_call(draft["text"]).fields(),
            )
    else:
        try:
            current_fields = common_call(before).fields()
            previous_theme = (previous or {}).get("latest_theme", 0)
            known_themes = [previous_theme]
            for fields in (current_fields, (previous or {}).get("managed", {})):
                try:
                    known_themes.append(rogue_number(fields.get("iconId", "")))
                except ValueError:
                    pass
            if max(known_themes) > draft["latest_theme"]:
                result["reason"] = "来源版本落后于页面已使用的主题，阻止页头回退"
                return result
            merged = merge_page(
                before,
                draft["text"],
                previous["managed"] if previous else None,
                theme_order=draft.get("theme_order"),
            )
            result.update(merged)
            result["latest_theme"] = draft["latest_theme"]
            if merged["conflicts"]:
                result["reason"] = "人工修改与游戏数据同时改变同一字段"
            else:
                result["action"] = "update" if result["text"] != before else "unchanged"
        except MergeError as exc:
            result["reason"] = str(exc)
    return result


def recover_pending(title: str, live: dict, state: dict) -> bool:
    """Reconcile uncertain writes by reading; never blindly resend an edit."""
    pending = state["pending"].get(title)
    if pending is None:
        return True
    if (
        live["exists"]
        and not live["redirect"]
        and digest(live["text"]) == pending["sha256"]
    ):
        state["pages"][title] = {"managed": pending["managed"], "revid": live["revid"]}
        if "latest_theme" in pending:
            state["pages"][title]["latest_theme"] = pending["latest_theme"]
    elif (
        live["revid"] != pending["base_revid"]
        or digest(live["text"]) != pending["before_sha256"]
    ):
        return False
    del state["pending"][title]
    return True


def log_problem(title: str, status: str, reason: str) -> None:
    """Only failed, blocked or uncertain pages need per-page console output."""
    logger.warning("收藏品{}【{}】：{}", status, title, reason)


async def synchronize(wiki: Wiki, drafts: list[dict], options: RelicConfig) -> None:
    preview = wiki.mode != "product"
    stale = False
    with state_lock(options.state_file):
        state = load_state(options.state_file, wiki.api_url)
        wrote = False
        for index, draft in enumerate(drafts):
            title = draft["title"]
            stage = "读取页面失败"
            uncertain = False
            try:
                live = await wiki.read_revision(title)
                stage = "维护检查失败"
                pending = title in state["pending"]
                if not recover_pending(title, live, state):
                    result = {
                        "action": "blocked",
                        "reason": (
                            "上次写入结果不明且线上内容已变化，"
                            "请核对 pending 与页面历史"
                        ),
                    }
                else:
                    if pending and not preview:
                        atomic_json(options.state_file, state)
                    result = decide(draft, live, state["pages"].get(title))
                if result["action"] == "blocked":
                    log_problem(
                        title, "预检未通过" if preview else "未处理", result["reason"]
                    )
                    continue
                if result["action"] == "unchanged":
                    if not preview and title in state["pages"]:
                        # Record source convergence without claiming human fields.
                        state["pages"][title] = {
                            "managed": result["managed"],
                            "revid": live["revid"],
                            "latest_theme": draft["latest_theme"],
                        }
                        atomic_json(options.state_file, state)
                    continue
                if preview:
                    continue
                if wrote:
                    await anyio.sleep(options.interval)
                create = result["action"] == "create"
                operation = "创建" if create else "维护"
                stage = operation + "前保存维护状态失败"
                state["pending"][title] = {
                    "managed": result["managed"],
                    "sha256": digest(result["text"]),
                    "base_revid": live["revid"],
                    "before_sha256": digest(live["text"]),
                    "latest_theme": draft["latest_theme"],
                }
                atomic_json(options.state_file, state)
                stage = operation + "失败"
                uncertain = True
                try:
                    response = await wiki.edit(
                        title=live["title"],
                        text=result["text"],
                        summary=SUMMARY if create else UPDATE_SUMMARY,
                        bot=True,
                        assert_user="bot",
                        createonly=True if create else None,
                        nocreate=None if create else True,
                        baserevid=None if create else live["revid"],
                        starttimestamp=live["starttimestamp"],
                        contentmodel="wikitext",
                        maxlag=5,
                        watchlist="nochange",
                        retry_transport=False,
                    )
                except WikiError as exc:
                    # Explicit API errors mean this write was rejected.
                    uncertain = False
                    state["pending"].pop(title, None)
                    atomic_json(options.state_file, state)
                    if exc.code in {"editconflict", "pagedeleted", "missingtitle"}:
                        log_problem(title, stage, f"{exc}；下次运行重新读取并合并")
                        stale = True
                        wrote = True
                        continue
                    raise
                wrote = True
                if response is None and create:
                    # Someone created the title after our snapshot.
                    uncertain = False
                    del state["pending"][title]
                    atomic_json(options.state_file, state)
                    log_problem(
                        title, "创建未完成", "页面已被其他编辑者创建，下次运行重新合并"
                    )
                    stale = True
                    continue
                edit = (response or {}).get("edit", {})
                if (
                    edit.get("result") != "Success"
                    or type(edit.get("newrevid")) is not int
                    or edit["newrevid"] <= 0
                    or (create and "new" not in edit)
                ):
                    raise RuntimeError("API 未确认写入成功，保留 pending 待下一轮核对")
                uncertain = False
                stage = operation + "已成功，但保存维护状态失败"
                state["pages"][title] = {
                    "managed": result["managed"],
                    "revid": edit["newrevid"],
                    "latest_theme": draft["latest_theme"],
                }
                del state["pending"][title]
                atomic_json(options.state_file, state)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                if uncertain:
                    stage = operation + "结果未确认"
                    reason += "；已保留 pending，下次运行读取页面核对，不自动重发"
                if preview:
                    stage = "预检未通过（" + stage + "）"
                log_problem(title, stage, reason)
                for remaining in drafts[index + 1 :]:
                    log_problem(
                        remaining["title"],
                        "未处理",
                        f"本轮任务因【{title}】发生错误而中止，尚未尝试此页",
                    )
                raise
    # Do not consume a resource version while a concurrent editor left work outstanding.
    if stale:
        raise RuntimeError("部分收藏品遇到并发编辑，下次运行将重新读取并合并")


@job
async def run(wiki: Wiki, data: GameData, config: Config) -> None:
    if config.relic.source_file is not None:
        source = json.loads(config.relic.source_file.read_text(encoding="utf-8-sig"))
    else:
        topics = RelicTopics.model_validate(
            await data.get("excel/roguelike_topic_table.json", region="CN")
        )
        glossary = RelicGlossary.model_validate(
            await data.get("excel/gamedata_const.json", region="CN")
        )
        source = build_records(topics, glossary)
    # Validate and render the entire dataset before the first page read/write.
    await synchronize(wiki, render_pages(source, config.relic.themes), config.relic)
