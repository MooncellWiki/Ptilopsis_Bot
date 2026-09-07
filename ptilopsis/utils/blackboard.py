"""黑板占位符(``{atk:0%}``、``{-cost}``)的格式化。

对应客户端 ``Torappu.FormatUtil.FormatParamedText`` / ``_FormatParamedItem``
(2.7.71 反编译):

- 扫描 ``{`` … ``}``,每一段单独格式化;``{`` 之后直到结尾没有 ``}`` 的部分原样保留。
- 单个占位符先去掉空格,key 是第一段连续的 ``[A-Za-z0-9.@\\[\\]_]``,其余是
  ``string.Format`` 的格式串(``:0%`` 等)。
- key 转小写后在黑板里大小写不敏感地查找;黑板项若带 ``valueStr`` 则是字符串值,
  查数值时会被跳过。
- 占位符第二个字符是 ``-``(``{-atk:0%}``)时把值取反。
- 找不到 key 时客户端记 LogError 并把 ``{…}`` 原样留下,这里同样保留并 warning。

数值本身按 .NET 的 ``Single`` 格式化规则输出,见 :func:`format_number`。
"""

import re
import string
import struct
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ptilopsis.log import logger

__all__ = ["blackboard_values", "format_number", "format_paramed_text"]

_KEY_CHARS = frozenset(string.ascii_letters + string.digits + ".@[]_")

# .NET 自定义数值格式里我们会遇到的子集:0% / 0.0% / 0.0 / 0 / #.##
_CUSTOM_FORMAT = re.compile(r"^(?P<int>[0#]+)(?:\.(?P<frac>[0#]+))?(?P<percent>%)?$")

# Number.Formatting.cs:自定义格式串下 Single 先取 7 位有效数字
_SINGLE_PRECISION_CUSTOM_FORMAT = 7


def blackboard_values(pairs: Iterable[Any] | None) -> dict[str, float]:
    """把 ``[{"key", "value", "valueStr"}]``(dict 或带同名属性的对象)转成
    ``{key.lower(): value}``。带 ``valueStr`` 的项是字符串值,不收录。"""

    values: dict[str, float] = {}
    if pairs is None:
        return values
    for pair in pairs:
        if isinstance(pair, Mapping):
            key, value, value_str = (
                pair.get("key"),
                pair.get("value"),
                pair.get("valueStr"),
            )
        else:
            key = getattr(pair, "key", None)
            value = getattr(pair, "value", None)
            value_str = getattr(pair, "value_str", None)
        if not key or value_str or value is None:
            continue
        values[key.lower()] = float(value)
    return values


def _to_single(value: float) -> float:
    """黑板的 value 是 C# ``float``,先按单精度截断再谈格式化。"""

    return struct.unpack("<f", struct.pack("<f", value))[0]


def _round_significant(value: Decimal, digits: int) -> Decimal:
    if value == 0:
        return value
    exponent = value.adjusted() - digits + 1
    return value.quantize(Decimal(1).scaleb(exponent), rounding=ROUND_HALF_UP)


def _shortest_single_repr(value: float) -> str:
    """``Single.ToString()``:能无损还原该单精度值的最短十进制表示。"""

    for precision in range(1, 10):
        text = f"{value:.{precision}g}"
        if _to_single(float(text)) == value:
            break
    else:
        text = repr(value)
    if "e" in text or "E" in text:
        text = f"{Decimal(text):f}"
    return text


def format_number(
    value: float, spec: str | None, *, strip_integral_decimals: bool = True
) -> str:
    """按 ``string.Format("{0:spec}", (float)value)`` 的规则输出。

    - 无格式串:``Single.ToString()``,即最短可还原表示(2 → "2",0.22 → "0.22")。
    - 自定义格式串(``0%``、``0.0``…):先取 7 位有效数字,再按格式串要求的小数位
      四舍五入(远离零),``%`` 表示乘 100。

    ``strip_integral_decimals`` 是 wiki 侧的约定:``0.0`` 这类格式下整数值不带
    小数尾巴("2" 而不是 "2.0"),百分比不受影响。
    """

    single = _to_single(value)
    if spec is None or spec == "":
        return _shortest_single_repr(single)
    matched = _CUSTOM_FORMAT.match(spec)
    if matched is None:
        logger.warning(f"Unsupported number format [{spec}], using default")
        return _shortest_single_repr(single)

    number = _round_significant(Decimal(single), _SINGLE_PRECISION_CUSTOM_FORMAT)
    percent = matched["percent"] is not None
    if percent:
        number *= 100
    fraction = matched["frac"] or ""
    rounded = number.quantize(Decimal(1).scaleb(-len(fraction)), rounding=ROUND_HALF_UP)
    text = f"{rounded:f}"
    if rounded == 0:
        text = text.lstrip("-")
    if "." in text:
        # ``#`` 位是可选位,末尾的 0 省略;``0`` 位必须保留
        optional = len(fraction) - len(fraction.rstrip("#"))
        integer, _, decimals = text.partition(".")
        keep = len(decimals) - optional
        decimals = decimals[:keep] + decimals[keep:].rstrip("0")
        if strip_integral_decimals and not percent and set(decimals) <= {"0"}:
            decimals = ""
        text = f"{integer}.{decimals}" if decimals else integer
    return text + ("%" if percent else "")


def _format_item(
    item: str, blackboard: Mapping[str, float], *, strip_integral_decimals: bool
) -> str:
    """``FormatUtil._FormatParamedItem``:``item`` 是含花括号的单个占位符。"""

    item = item.replace(" ", "")
    start = end = -1
    for index, char in enumerate(item):
        if char in _KEY_CHARS:
            if start < 0:
                start = index
        elif start >= 0:
            end = index
            break
    if start < 0 or end < 0:
        logger.warning(f"Invalid paramed text format in [{item}]")
        return item
    key = item[start:end]
    value = blackboard.get(key.lower())
    if value is None:
        logger.warning(f"Param [{key}] not found in blackboard [{item}]")
        return item
    if item[1] == "-":
        value = -value
    rest = item[end:]
    if rest == "}":
        spec = None
    elif rest.startswith(":") and rest.endswith("}"):
        spec = rest[1:-1]
    else:
        logger.warning(f"Invalid paramed text format in [{item}]")
        return item
    return format_number(value, spec, strip_integral_decimals=strip_integral_decimals)


def format_paramed_text(
    text: str | None,
    blackboard: Mapping[str, float] | None,
    *,
    strip_integral_decimals: bool = True,
) -> str:
    """``FormatUtil.FormatParamedText``:把 ``text`` 里的占位符换成黑板值。

    ``blackboard`` 用 :func:`blackboard_values` 得到;为 None 时原样返回。
    """

    if not text:
        return ""
    if blackboard is None:
        return text
    out: list[str] = []
    in_item = False
    start = -1
    for index, char in enumerate(text):
        if char == "{":
            in_item = True
            start = index
        elif char == "}":
            if in_item:
                out.append(
                    _format_item(
                        text[start : index + 1],
                        blackboard,
                        strip_integral_decimals=strip_integral_decimals,
                    )
                )
            in_item = False
        elif not in_item:
            out.append(char)
    if in_item:
        out.append(text[start:])
    return "".join(out)
