"""生成模型共用的基类与约定。

FlatBuffers 里 string / table / vector 字段都是可选的,解包成 JSON 后就是
``null``,而且哪一个字段会是 null 随版本变化(2.7.71 才第一次出现
``talents[].candidates`` 为 null)。因此生成的模型把这三类字段一律声明成
``T | None = None``,标量按 FBS 默认值(0 / 0.0 / False)。pyright 在
``standard`` 模式下会对未判空的 ``for x in model.candidates`` 报错,
这类问题就能在提交前而不是线上暴露。

枚举字段声明成 ``str``(JSON 里就是成员名),对应的 ``IntEnum`` 只用来
比较顺序或列举已知取值;这样上游新增枚举成员不会让整张表校验失败。
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

__all__ = ["GameDataModel"]


class GameDataModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        # 早期数据里枚举曾以数字出现,别让它变成整表校验失败
        coerce_numbers_to_str=True,
    )
