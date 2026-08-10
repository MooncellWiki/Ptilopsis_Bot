"""Wikitext 结构化节点。

{{模板名|参数=值}} 调用的序列化规则是固定的——一行一个参数、顺序即加入顺序、
空参数按需省略——这些规则集中在这里实现,调用方只负责描述有哪些参数。
"""

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
        self._params: list[tuple[str, str]] = []

    def add(self, key: str, value: object) -> Self:
        self._params.append((key, format_value(value)))
        return self

    def add_optional(self, key: str, value: object) -> Self:
        """值为空时跳过该参数。"""

        if is_empty(value):
            return self
        return self.add(key, value)

    def add_block(self, key: str, body: str) -> Self:
        """值占多行的参数,内容从等号的下一行开始。"""

        return self.add(key, f"\n{body}" if body else "")

    def __str__(self) -> str:
        lines = ["{{" + self.name]
        lines.extend(f"|{key}={value}" for key, value in self._params)
        lines.append("}}")
        return "\n".join(lines)
