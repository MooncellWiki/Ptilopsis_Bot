"""job 的注册、依赖注入与调度。

一个 job 就是一个用 :func:`job` 装饰的普通函数,参数按注解注入::

    from ptilopsis.jobs.params import ItemTable, RichText
    from ptilopsis.utils.job import job
    from ptilopsis.utils.wiki import Wiki

    @job
    def run(wiki: Wiki, item_table: ItemTable, rts: RichText) -> None:
        ...

``Wiki`` / ``GameData`` / ``Config`` / ``JobContext`` 按类型直接提供,其余参数
用 ``Depends`` 标记(各表的类型化模型等都在 :mod:`ptilopsis.jobs.params`),
同一次运行里相同的依赖只解析一次。

job 名默认是 ``<模块名>.<函数名>``(如 ``basic.run``),``__main__`` 用它编排
各模式下的执行顺序。依赖或 job 本身抛 :class:`SkipJob` 表示这次没事可做,
其它异常记日志后继续跑下一个 job。
"""

import inspect
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, overload

from ptilopsis.config import Config
from ptilopsis.log import logger
from ptilopsis.utils.data import GameData
from ptilopsis.utils.di import Dependant, Resolver, analyze
from ptilopsis.utils.wiki import Wiki

__all__ = [
    "PROVIDED_TYPES",
    "Job",
    "JobContext",
    "SkipJob",
    "get_job",
    "job",
    "registered_jobs",
    "run_job",
    "run_jobs",
]


@dataclass(frozen=True)
class JobContext:
    """一次运行共享的上下文:Wiki 客户端 + 游戏数据源。

    job 直接注入 ``Wiki`` / ``GameData`` 或 params 里的依赖即可;
    这个类是调度器传给 :class:`Job` 的入口,也可以整个注入。
    """

    wiki: Wiki
    gamedata: GameData

    def getgd(self, path: str, region: str = "CN") -> dict:
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return: dict
        """
        return self.gamedata.get(path, region)

    def getgd_txt(self, path: str, region: str = "CN") -> str:
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return: string
        """
        return self.gamedata.get_txt(path, region)


class SkipJob(Exception):
    """依赖或 job 本身抛出它表示这次没事可做,调度器按"跳过"而不是失败记录。"""


PROVIDED_TYPES: tuple[type, ...] = (JobContext, Wiki, GameData, Config)
"""只凭注解就能注入的类型。"""


class Job:
    """注册后的 job:函数本身 + 名字 + 分析好的依赖树。"""

    __slots__ = ("dependant", "func", "name")

    def __init__(self, func: Callable[..., Any], *, name: str) -> None:
        if not name:
            raise ValueError("a job needs a non-empty name")
        if not callable(func) or inspect.iscoroutinefunction(func):
            raise TypeError(f"job {name!r}: {func!r} must be a plain function")
        self.func = func
        self.name = name
        # 注册时就把整棵依赖树检查一遍
        self.dependant: Dependant = analyze(func, PROVIDED_TYPES)

    def __repr__(self) -> str:
        return f"<Job {self.name!r}>"

    def resolve(self, ctx: JobContext) -> dict[str, Any]:
        """解析这次运行的实参;依赖抛 :class:`SkipJob` 时原样抛出。"""

        resolver = Resolver(
            {
                JobContext: ctx,
                Wiki: ctx.wiki,
                GameData: ctx.gamedata,
                Config: ctx.gamedata.config,
            }
        )
        return resolver.solve_params(self.dependant)

    def run(self, ctx: JobContext) -> Any:
        """:meth:`resolve` 后调用函数,异常原样抛出。"""

        return self.func(**self.resolve(ctx))

    def __call__(self, ctx: JobContext) -> Any:
        """兼容旧的 ``module.run(ctx)`` 调用方式:带异常兜底地运行。"""

        return run_job(self, ctx)


_registry: dict[str, Job] = {}


def _same_definition(a: Job, b: Job) -> bool:
    # importlib.reload() 会对同一个函数再执行一次装饰器
    return (a.func.__module__, a.func.__qualname__) == (
        b.func.__module__,
        b.func.__qualname__,
    )


def register(job_: Job) -> Job:
    """登记 ``job_``;名字必须唯一。"""

    existing = _registry.get(job_.name)
    if existing is not None and not _same_definition(existing, job_):
        raise ValueError(
            f"job name {job_.name!r} is already registered by "
            f"{existing.func.__module__}.{existing.func.__qualname__}"
        )
    _registry[job_.name] = job_
    return job_


def registered_jobs() -> list[Job]:
    """按注册顺序返回全部 job。"""

    return list(_registry.values())


def get_job(name: str) -> Job:
    try:
        return _registry[name]
    except KeyError:
        known = ", ".join(sorted(_registry)) or "(none)"
        raise KeyError(f"unknown job {name!r}; registered: {known}") from None


def _default_name(func: Callable[..., Any]) -> str:
    module = func.__module__.rsplit(".", 1)[-1]
    return f"{module}.{func.__name__}"


@overload
def job(func: Callable[..., Any], /) -> Job: ...
@overload
def job(name: str | None = None, /) -> Callable[[Callable[..., Any]], Job]: ...
def job(
    func: Callable[..., Any] | str | None = None, /
) -> Job | Callable[[Callable[..., Any]], Job]:
    """把函数注册为 job。

    支持 ``@job`` 与 ``@job("custom.name")`` 两种写法;不给名字时用
    ``<模块名>.<函数名>``。装饰后得到 :class:`Job`,原函数在 ``Job.func``。
    """

    if callable(func):
        return register(Job(func, name=_default_name(func)))
    name = func

    def decorator(inner: Callable[..., Any]) -> Job:
        return register(Job(inner, name=name or _default_name(inner)))

    return decorator


def _execute(job_: Job, ctx: JobContext) -> tuple[bool, Any]:
    """返回 (是否失败, 返回值);跳过与失败都只记日志。"""

    try:
        kwargs = job_.resolve(ctx)
        logger.info(f"Starting job {job_.name}")
        result = job_.func(**kwargs)
    except SkipJob as reason:
        detail = f": {reason}" if str(reason) else ""
        logger.info(f"Skipping job {job_.name}{detail}")
        return False, None
    except Exception:
        logger.exception(f"job {job_.name} failed")
        return True, None
    logger.info(f"Finished job {job_.name}")
    return False, result


def run_job(job_: Job, ctx: JobContext) -> Any:
    """运行一个 job,返回值原样透传;跳过或失败时为 None。"""

    return _execute(job_, ctx)[1]


def run_jobs(names: Iterable[str], ctx: JobContext) -> list[str]:
    """按顺序运行 ``names`` 里的 job,返回失败的名字。

    名字先全部查一遍,写错任何一个都不会开始运行。
    """

    jobs = [get_job(name) for name in names]
    return [job_.name for job_ in jobs if _execute(job_, ctx)[0]]
