"""极简的 FastAPI 风格依赖注入,移植自 torappu.core.di(去掉了 async)。

*dependant* 是一个由 :class:`Resolver` 而不是调用方填参数的可调用对象。
它的每个参数必须是下面两种之一:

* ``param: Annotated[T, Depends(fn)]`` 或 ``param: T = Depends(fn)``:调用 ``fn``
  (它自己也是 dependant)并注入返回值。结果按 :class:`Resolver` 缓存,同一个
  依赖在一次解析里(直接或间接)被多个参数引用时只跑一次。
* ``param: SomeType``:注入 resolver 创建时按该类型提供的对象(``Wiki``、
  ``GameData`` 等,见 ``ptilopsis.utils.job.PROVIDED_TYPES``)。子类注解也能
  匹配。

签名在 :func:`analyze` 里一次性分析,注入不了的参数在注册(导入)时就报错,
而不是等调度器跑到它。
"""

import inspect
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin, get_type_hints

__all__ = ["Dependant", "Depends", "DependsMarker", "Param", "Resolver", "analyze"]


class DependsMarker:
    """把参数标记成"调用 ``dependency`` 的结果"。用 :func:`Depends` 构造。"""

    __slots__ = ("dependency", "use_cache")

    def __init__(
        self, dependency: Callable[..., Any], *, use_cache: bool = True
    ) -> None:
        if not callable(dependency):
            raise TypeError(f"Depends() expects a callable, got {dependency!r}")
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self) -> str:
        return f"Depends({_describe(self.dependency)})"


def Depends(dependency: Callable[..., Any], *, use_cache: bool = True) -> Any:
    """标记参数由 ``dependency`` 的返回值注入。

    返回类型写成 ``Any`` 是为了能直接当默认值用(``x: dict = Depends(f)``)
    而不让类型检查器抱怨;和 FastAPI 的做法一样。
    """

    return DependsMarker(dependency, use_cache=use_cache)


@dataclass(frozen=True, slots=True)
class Param:
    """一个参数怎么取值:``provided``(按类型提供)与 ``depends`` 二选一。"""

    name: str
    provided: type | None = None
    depends: DependsMarker | None = None
    dependant: "Dependant | None" = None


@dataclass(frozen=True, slots=True)
class Dependant:
    call: Callable[..., Any]
    params: tuple[Param, ...]


def _describe(call: Callable[..., Any]) -> str:
    return getattr(call, "__qualname__", None) or repr(call)


def _type_hints(call: Callable[..., Any]) -> dict[str, Any]:
    target = call.__init__ if inspect.isclass(call) else call
    try:
        return get_type_hints(target, include_extras=True)
    except Exception:
        # 例如签名里某个 TYPE_CHECKING 才导入的前向引用;只要需要注入的
        # 参数本身能解析,用原始注解就够了
        return {}


def _match_provider(annotation: Any, provided: tuple[type, ...]) -> type | None:
    if not inspect.isclass(annotation):
        return None
    for candidate in provided:
        if issubclass(candidate, annotation):
            return candidate
    return None


def analyze(
    call: Callable[..., Any],
    provided: Iterable[type],
    *,
    _stack: tuple[Callable[..., Any], ...] = (),
) -> Dependant:
    """构建 ``call`` 的依赖树。

    参数既没有 ``Depends`` 标记也不是 ``provided`` 里的类型时抛 ``TypeError``,
    循环依赖同样抛 ``TypeError``。
    """

    provided = tuple(provided)
    if call in _stack:
        chain = " -> ".join(_describe(c) for c in (*_stack, call))
        raise TypeError(f"circular dependency: {chain}")
    stack = (*_stack, call)

    try:
        signature = inspect.signature(call)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"cannot inspect the signature of {_describe(call)}") from exc
    hints = _type_hints(call)

    params: list[Param] = []
    for param in signature.parameters.values():
        if param.kind not in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            raise TypeError(
                f"{_describe(call)}: parameter {param.name!r} must be injectable "
                "by keyword (no *args, **kwargs or positional-only parameters)"
            )

        annotation = hints.get(param.name, param.annotation)
        depends = param.default if isinstance(param.default, DependsMarker) else None
        if get_origin(annotation) is Annotated:
            annotation, *extras = get_args(annotation)
            markers = [extra for extra in extras if isinstance(extra, DependsMarker)]
            if markers:
                if depends is not None:
                    raise TypeError(
                        f"{_describe(call)}: parameter {param.name!r} has Depends() "
                        "both as its default and inside Annotated[...]"
                    )
                depends = markers[-1]

        if depends is not None:
            params.append(
                Param(
                    name=param.name,
                    depends=depends,
                    dependant=analyze(depends.dependency, provided, _stack=stack),
                )
            )
            continue

        if annotation is param.empty:
            raise TypeError(
                f"{_describe(call)}: parameter {param.name!r} has no annotation; "
                "annotate it with a provided type or mark it with Depends(...)"
            )
        provider = _match_provider(annotation, provided)
        if provider is None:
            expected = ", ".join(t.__name__ for t in provided)
            raise TypeError(
                f"{_describe(call)}: cannot inject parameter {param.name!r} "
                f"(annotation {annotation!r}); annotate it with one of {expected} "
                "or mark it with Depends(...)"
            )
        params.append(Param(name=param.name, provided=provider))

    return Dependant(call=call, params=tuple(params))


class Resolver:
    """对一组固定的提供对象解析 dependant;一个 resolver 就是一次运行的缓存。"""

    def __init__(self, provided: Mapping[type, Any]) -> None:
        self._provided = dict(provided)
        self._cache: dict[Callable[..., Any], Any] = {}

    def solve_params(self, dependant: Dependant) -> dict[str, Any]:
        """按声明顺序解析 ``dependant`` 的每个参数。"""

        kwargs: dict[str, Any] = {}
        for param in dependant.params:
            if param.depends is not None and param.dependant is not None:
                kwargs[param.name] = self._solve_depends(param.depends, param.dependant)
            elif param.provided is not None:
                kwargs[param.name] = self._provided[param.provided]
            else:  # pragma: no cover - analyze() 不会生成这样的 Param
                raise TypeError(f"unresolvable parameter {param.name!r}")
        return kwargs

    def solve(self, dependant: Dependant) -> Any:
        """解析参数并调用 ``dependant.call``。"""

        return dependant.call(**self.solve_params(dependant))

    def _solve_depends(self, depends: DependsMarker, dependant: Dependant) -> Any:
        key = depends.dependency
        if depends.use_cache and key in self._cache:
            return self._cache[key]
        value = self.solve(dependant)
        if depends.use_cache:
            self._cache[key] = value
        return value
