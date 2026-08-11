"""Wikitext 结构化节点。

{{模板名|参数=值}} 调用的序列化规则是固定的——一行一个参数、顺序即加入顺序、
空参数按需省略——这些规则集中在这里实现,调用方只负责描述有哪些参数。
"""

from collections.abc import Mapping
from typing import Self


def format_value(value: object) -> str:
    """把参数值转成 wikitext,None 视为空值。"""

    if value is None:
        return ""
    return str(value)


def is_empty(value: object) -> bool:
    """None、空字符串和空容器算空值;数字 0 不算。"""

    if value is None:
        return True
    if isinstance(value, str | list | tuple | dict | set):
        return not value
    return False


def inline_template(name: str, *args: object) -> str:
    """行内模板调用 {{名称|参数1|参数2}},参数按位置排列。"""

    return "{{" + "|".join([name, *(format_value(arg) for arg in args)]) + "}}"


class WikiTemplate:
    """跨行的 {{模板名|参数=值}} 调用,每个参数占一行。

    `add` 总是输出参数,`add_optional` 在值为空时跳过。某个参数是否输出常常
    取决于别的字段(如蚀刻章的 |镀层方式= 取决于 has_advanced),这类条件直接
    用 if 写在调用处,不必再为它设计一层表达方式。
    """

    def __init__(self, name: str) -> None:
        self.name = name
        # key 为 None 的项是 add_raw 追加的自由文本行,不参与 |key=value 的拼接
        self._params: list[tuple[str | None, str]] = []

    def add(self, key: str, value: object) -> Self:
        self._params.append((key, format_value(value)))
        return self

    def add_optional(self, key: str, value: object) -> Self:
        """值为空时跳过该参数。"""

        if is_empty(value):
            return self
        return self.add(key, value)

    def add_if_set(self, key: str, value: object) -> Self:
        """值为 None 时跳过该参数,空字符串仍然输出 |key=。

        与 add_optional 的区别在于对"空"的定义:这里 None 表示这类页面根本
        没有该参数,空字符串表示参数存在但取值为空。MediaWiki 里参数缺失与
        参数为空会走不同的 {{#if:}} 分支,两者不能混为一谈。
        """

        if value is None:
            return self
        return self.add(key, value)

    def add_all(self, params: Mapping[str, object]) -> Self:
        """按 dict 的书写顺序批量加入参数,写法接近页面上的参数表。"""

        for key, value in params.items():
            self.add(key, value)
        return self

    def add_all_optional(self, params: Mapping[str, object]) -> Self:
        """批量加入参数,值为空的跳过。"""

        for key, value in params.items():
            self.add_optional(key, value)
        return self

    def add_block(self, key: str, body: str) -> Self:
        """值占多行的参数,内容从等号的下一行开始。"""

        return self.add(key, f"\n{body}" if body else "")

    def add_raw(self, text: str) -> Self:
        """原样追加自由文本,不做 |key=value 的拆分。

        用于模板内部的自由文本(如突袭关卡信息里留在注释中的情报),
        这类内容不是参数表的一部分,序列化规则管不到它。用 None 而不是空
        字符串作键,免得和某个真的算出空键名的参数撞上。
        """

        self._params.append((None, text))
        return self

    def __str__(self) -> str:
        lines = ["{{" + self.name]
        for key, value in self._params:
            lines.append(value if key is None else f"|{key}={value}")
        lines.append("}}")
        return "\n".join(lines)
