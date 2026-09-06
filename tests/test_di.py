from typing import Annotated

import pytest

from ptilopsis.utils.di import Depends, Resolver, analyze


class Client:
    pass


class SubClient(Client):
    pass


class Settings:
    pass


PROVIDED = (Client, Settings)


def resolver(**objects) -> Resolver:
    return Resolver({Client: objects.get("client", Client()), Settings: Settings()})


def test_provided_types_are_injected_by_annotation() -> None:
    def task(client: Client, settings: Settings) -> tuple[Client, Settings]:
        return client, settings

    client = Client()
    got_client, got_settings = resolver(client=client).solve(analyze(task, PROVIDED))
    assert got_client is client and isinstance(got_settings, Settings)


def test_subclass_annotation_matches_provider() -> None:
    def task(client: SubClient) -> SubClient:
        return client

    # 提供的是 SubClient 的实例时,注解写子类也能拿到
    dependant = analyze(task, (SubClient, Settings))
    client = SubClient()
    assert (
        Resolver({SubClient: client, Settings: Settings()}).solve(dependant) is client
    )


def test_depends_as_default_and_annotated() -> None:
    def table(client: Client) -> dict:
        return {"client": client}

    def task(
        a: Annotated[dict, Depends(table)], b: dict = Depends(table)
    ) -> tuple[dict, dict]:
        return a, b

    a, b = resolver().solve(analyze(task, PROVIDED))
    assert a is b  # 同一次解析里缓存


def test_use_cache_false_reruns_dependency() -> None:
    calls = []

    def counter() -> int:
        calls.append(1)
        return len(calls)

    def task(
        a: Annotated[int, Depends(counter, use_cache=False)],
        b: Annotated[int, Depends(counter, use_cache=False)],
    ) -> tuple[int, int]:
        return a, b

    assert resolver().solve(analyze(task, PROVIDED)) == (1, 2)


def test_nested_dependencies_resolve_in_order() -> None:
    order = []

    def first(client: Client) -> str:
        order.append("first")
        return "f"

    def second(f: Annotated[str, Depends(first)]) -> str:
        order.append("second")
        return f + "s"

    def task(s: Annotated[str, Depends(second)], f: Annotated[str, Depends(first)]):
        return s, f

    assert resolver().solve(analyze(task, PROVIDED)) == ("fs", "f")
    assert order == ["first", "second"]


def test_missing_annotation_fails_at_analysis() -> None:
    def task(client):
        return client

    with pytest.raises(TypeError, match="has no annotation"):
        analyze(task, PROVIDED)


def test_unknown_type_fails_at_analysis() -> None:
    def task(count: int) -> int:
        return count

    with pytest.raises(TypeError, match="cannot inject parameter 'count'"):
        analyze(task, PROVIDED)


def test_var_args_are_rejected() -> None:
    def task(*args: Client) -> None:
        return None

    with pytest.raises(TypeError, match="injectable by keyword"):
        analyze(task, PROVIDED)


def test_circular_dependency_is_detected() -> None:
    def a(b_value: int = Depends(lambda: 0)) -> int:
        return b_value

    def b(a_value: int = Depends(a)) -> int:
        return a_value

    # 把 a 的依赖改指回 b,构成 a -> b -> a
    a.__defaults__ = (Depends(b),)
    with pytest.raises(TypeError, match="circular dependency"):
        analyze(b, PROVIDED)


def test_depends_requires_callable() -> None:
    with pytest.raises(TypeError):
        Depends("not callable")  # type: ignore[arg-type]
