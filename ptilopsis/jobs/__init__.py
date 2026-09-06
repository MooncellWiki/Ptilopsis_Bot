"""各类 Wiki 更新任务。

每个子模块用 ``@job`` 注册自己的入口,:func:`discover_jobs` 把它们全部导入;
``__main__`` 再按 job 名编排各模式的执行顺序。
"""

import importlib
import pkgutil

__all__ = ["discover_jobs"]


def discover_jobs() -> None:
    """导入本包下的全部 job 模块(下划线开头的草稿和 params 除外)。"""

    for module in pkgutil.iter_modules(__path__):
        if module.name.startswith("_") or module.name == "params":
            continue
        importlib.import_module(f"{__name__}.{module.name}")
