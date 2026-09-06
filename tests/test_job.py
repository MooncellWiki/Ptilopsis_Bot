from typing import Annotated, Any

import pytest

import ptilopsis.utils.job as job_module
from ptilopsis.jobs.params import RichText, category, gamedata
from ptilopsis.utils.data import GameData
from ptilopsis.utils.di import Depends
from ptilopsis.utils.job import (
    Job,
    JobContext,
    SkipJob,
    get_job,
    job,
    registered_jobs,
    run_job,
    run_jobs,
)
from ptilopsis.utils.wiki import Wiki


class FakeWiki:
    def __init__(self) -> None:
        self.edits: list[dict[str, Any]] = []
        self.categories: list[str] = []

    def edit(self, **kwargs: Any) -> None:
        self.edits.append(kwargs)

    def category(self, name: str) -> list[str]:
        self.categories.append(name)
        return ["页面甲", "页面乙"]

    def read(self, title: str) -> str:
        return "name,sortId,approach,date\n阿米娅,1,初始,2019-05-01\n"


class FakeGameData:
    config = None

    def __init__(self) -> None:
        self.reads: list[str] = []

    def get(self, path: str, region: str = "CN") -> dict:
        self.reads.append(path)
        if path.endswith("gamedata_const.json"):
            return {
                "richTextStyles": {"ba.vup": "<color=#0098DC>{0}</color>"},
                "termDescriptionDict": {},
            }
        return {"path": path}


@pytest.fixture
def ctx() -> JobContext:
    return JobContext(wiki=FakeWiki(), gamedata=FakeGameData())  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def isolated_registry():
    saved = dict(job_module._registry)
    job_module._registry.clear()
    yield
    job_module._registry.clear()
    job_module._registry.update(saved)


def test_bare_decorator_names_job_after_module_and_function() -> None:
    @job
    def run(wiki: Wiki) -> str:
        return "ok"

    assert isinstance(run, Job)
    assert run.name == "test_job.run"
    assert get_job("test_job.run") is run
    assert registered_jobs() == [run]


def test_named_decorator() -> None:
    @job("custom.name")
    def run(wiki: Wiki) -> None:
        return None

    assert run.name == "custom.name"


def test_duplicate_name_from_different_function_is_rejected() -> None:
    @job("dup")
    def one(wiki: Wiki) -> None:
        return None

    with pytest.raises(ValueError, match="already registered"):

        @job("dup")
        def two(wiki: Wiki) -> None:
            return None


def test_bad_signature_fails_at_registration() -> None:
    with pytest.raises(TypeError, match="cannot inject"):

        @job
        def run(count: int) -> None:
            return None


def test_provided_types_and_params_are_injected(ctx: JobContext) -> None:
    @job
    def run(
        wiki: Wiki,
        data: GameData,
        context: JobContext,
        item_table: Annotated[dict, gamedata("excel/item_table.json")],
        rts: RichText,
        pages: Annotated[list[str], category("分类:干员")],
    ) -> dict:
        return {
            "wiki": wiki,
            "data": data,
            "context": context,
            "item_table": item_table,
            "text": rts.compile("<@ba.vup>x</>"),
            "pages": pages,
        }

    result = run_job(run, ctx)
    assert result is not None
    assert result["wiki"] is ctx.wiki and result["data"] is ctx.gamedata
    assert result["context"] is ctx
    assert result["item_table"] == {"path": "excel/item_table.json"}
    assert result["text"] == "{{color|#0098DC|x}}"
    assert result["pages"] == ["页面甲", "页面乙"]


def test_gamedata_with_model_validates(ctx: JobContext) -> None:
    from pydantic import BaseModel

    class Table(BaseModel):
        path: str

    @job
    def run(table: Annotated[Table, gamedata("excel/x.json", model=Table)]) -> str:
        return table.path

    assert run_job(run, ctx) == "excel/x.json"


def test_legacy_context_signature_still_works(ctx: JobContext) -> None:
    @job
    def run(context: JobContext) -> str:
        return context.getgd("excel/y.json")["path"]

    assert run_job(run, ctx) == "excel/y.json"
    # 旧的 module.run(ctx) 调用方式
    assert run(ctx) == "excel/y.json"


def test_run_jobs_reports_failures_and_skips(ctx: JobContext) -> None:
    order: list[str] = []

    @job("t.ok")
    def ok(wiki: Wiki) -> None:
        order.append("ok")

    def nothing_to_do(wiki: Wiki) -> None:
        raise SkipJob("no new version")

    @job("t.skip")
    def skipped(flag: Annotated[None, Depends(nothing_to_do)]) -> None:
        order.append("skip")

    @job("t.boom")
    def boom(wiki: Wiki) -> None:
        raise RuntimeError("boom")

    @job("t.after")
    def after(wiki: Wiki) -> None:
        order.append("after")

    failed = run_jobs(["t.ok", "t.skip", "t.boom", "t.after"], ctx)
    assert failed == ["t.boom"]
    assert order == ["ok", "after"]


def test_run_jobs_rejects_unknown_name_before_running(ctx: JobContext) -> None:
    order: list[str] = []

    @job("t.ok")
    def ok(wiki: Wiki) -> None:
        order.append("ok")

    with pytest.raises(KeyError, match=r"unknown job 't\.nope'"):
        run_jobs(["t.ok", "t.nope"], ctx)
    assert order == []
