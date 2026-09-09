"""游戏富文本(``<@style>…</>``、``<$term>…</>``、``<color=…>…</color>``)的解析与渲染。

解析规则逐条对应客户端 ``Torappu.SharedFormatUtil``(2.7.71 反编译):

- ``FormatRichTextTag``:逐字符扫描,遇 ``<`` 开始收集标签名,遇 ``>`` 结束。
  收集到的标签若能与当前打开的标签配对,则由 handler 收尾并返回;否则若它是
  起始标签就递归解析其内容;两者都不是则把 ``<tag>`` 原样输出。
- ``CheckIfStartTag``:``color*`` / ``b`` / ``i`` / ``@*`` / ``$*`` / ``p=*``
  视为起始标签。
- ``RichTextConvertTagsHandler``:``<@x>`` 用 ``richTextStyles[x.lower()]`` 做
  ``string.Format``,样式不存在时记错误并原样返回内容;``<$x>`` 返回内容本身;
  ``color`` / ``i`` / ``b`` 透传。
- ``SharedFormatRichTextFromData``:最后把字面量 ``\\n`` 换成换行。

解析器只负责识别结构,把 ``<color=#X>{0}</color>`` 变成 ``{{color|X|…}}`` 还是
``<span>`` 由 :class:`Renderer` 决定。``<$term>`` 在客户端里由另一套可点击文本
逻辑弹出释义,这里交给 renderer 决定要不要展开成 wiki 模板或 tooltip。
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ptilopsis.log import logger

__all__ = [
    "HtmlRenderer",
    "PlainRenderer",
    "Renderer",
    "RichText",
    "TermDescription",
    "WikiRenderer",
    "is_start_tag",
]


@dataclass(frozen=True, slots=True)
class TermDescription:
    """gamedata_const.termDescriptionDict 的一项(clz_Torappu_TermDescriptionData)。"""

    term_id: str
    term_name: str
    description: str

    @classmethod
    def from_raw(cls, raw: Any) -> "TermDescription":
        """接受原始 dict 或 ``gamedata_const.TermDescriptionData`` 模型。"""

        if isinstance(raw, Mapping):
            return cls(
                term_id=raw.get("termId") or "",
                term_name=raw.get("termName") or "",
                description=raw.get("description") or "",
            )
        return cls(
            term_id=getattr(raw, "term_id", None) or "",
            term_name=getattr(raw, "term_name", None) or "",
            description=getattr(raw, "description", None) or "",
        )


class Renderer(Protocol):
    """把一段已配对的标签及其内容渲染成目标格式。

    ``content`` 已经是渲染过的内层文本(嵌套标签先于外层完成)。
    """

    newline: str
    """``compile`` 把字面量 ``\\n`` 换成什么。"""

    def style(self, style_id: str, template: str | None, content: str) -> str:
        """``<@style_id>content</>``;``template`` 是 richTextStyles 里的模板,
        未知样式时为 None(客户端此时原样返回 content)。"""
        ...

    def term(self, term_id: str, term: TermDescription | None, content: str) -> str:
        """``<$term_id>content</>``;未知术语时 ``term`` 为 None。"""
        ...

    def color(self, color: str, content: str) -> str:
        """``<color=color>content</color>``。"""
        ...

    def italic(self, content: str) -> str: ...

    def bold(self, content: str) -> str: ...


_COLOR_TEMPLATE = re.compile(r"^<color=(?P<color>[^>]*)>\{0\}</color>$")


def _apply_template(template: str, content: str) -> str:
    """richTextStyles 的模板是 ``string.Format`` 格式串,占位符只有 ``{0}``。"""

    return template.replace("{0}", content)


class WikiRenderer:
    """输出 PRTS wiki 模板:颜色用 ``{{color|…}}``,术语用 ``{{术语|…}}``。"""

    newline = "<br/>"

    def style(self, style_id: str, template: str | None, content: str) -> str:
        if template is None:
            return content
        if matched := _COLOR_TEMPLATE.match(template):
            return self.color(matched["color"], content)
        # <i>{0}</i>、{0} 之类:MediaWiki 直接支持这些 HTML 标签
        return _apply_template(template, content)

    def term(self, term_id: str, term: TermDescription | None, content: str) -> str:
        if term is None:
            return content
        return f"{{{{术语|{term.term_id}|{content}}}}}"

    def color(self, color: str, content: str) -> str:
        return f"{{{{color|{color}|{content}}}}}"

    def italic(self, content: str) -> str:
        return f"<i>{content}</i>"

    def bold(self, content: str) -> str:
        return f"<b>{content}</b>"


class PlainRenderer:
    """丢掉所有标记,只留文字。用于术语释义等不能再嵌套标记的场合。"""

    newline = "\n"

    def style(self, style_id: str, template: str | None, content: str) -> str:
        return content

    def term(self, term_id: str, term: TermDescription | None, content: str) -> str:
        return content

    def color(self, color: str, content: str) -> str:
        return content

    def italic(self, content: str) -> str:
        return content

    def bold(self, content: str) -> str:
        return content


class HtmlRenderer:
    """输出内联 HTML,给 ``敌人一览/数据`` 这类由前端脚本消费的 JSON 用。

    术语展开成 ``mc-tooltips`` 结构,释义文本用 :class:`PlainRenderer` 去掉标记,
    避免 tooltip 里再嵌 tooltip。
    """

    newline = "<br>"

    def __init__(self, *, term_tooltips: bool = True) -> None:
        self.term_tooltips = term_tooltips
        # 由 RichText 在绑定时注入,用来渲染术语释义
        self._strip: RichText | None = None

    def bind(self, rich_text: "RichText") -> None:
        self._strip = RichText(
            rich_text.styles, rich_text.terms, PlainRenderer(), warn_unknown=False
        )

    def style(self, style_id: str, template: str | None, content: str) -> str:
        if template is None:
            return content
        if matched := _COLOR_TEMPLATE.match(template):
            return self.color(matched["color"], content)
        return _apply_template(template, content)

    def term(self, term_id: str, term: TermDescription | None, content: str) -> str:
        if term is None or not self.term_tooltips:
            return content
        description = term.description
        if self._strip is not None:
            description = self._strip.compile(description, convert_newline=False)
        return (
            '<span class="mc-tooltips">'
            f"<span>{content}</span>"
            f"<span>{description}</span>"
            "</span>"
        )

    def color(self, color: str, content: str) -> str:
        return f'<span style="color:{color};">{content}</span>'

    def italic(self, content: str) -> str:
        return f"<i>{content}</i>"

    def bold(self, content: str) -> str:
        return f"<b>{content}</b>"


def is_start_tag(tag: str) -> bool:
    """``SharedFormatUtil.CheckIfStartTag``。"""

    if not tag:
        return False
    return (
        tag.startswith("color")
        or tag == "b"
        or tag == "i"
        or tag.startswith("@")
        or tag.startswith("$")
        or tag.startswith("p=")
    )


class RichText:
    """按客户端规则解析富文本,渲染交给 :class:`Renderer`。

    ``styles`` 是 ``gamedata_const.richTextStyles``,``terms`` 是
    ``gamedata_const.termDescriptionDict``(原始 dict、``TermDescriptionData`` 模型
    或 :class:`TermDescription` 都可以)。
    """

    def __init__(
        self,
        styles: Mapping[str, str],
        terms: Mapping[str, Any],
        renderer: Renderer,
        *,
        warn_unknown: bool = True,
    ) -> None:
        # 客户端查表前会把样式 id 转小写,这里同样按小写索引
        self.styles: dict[str, str] = {k.lower(): v for k, v in styles.items()}
        self.terms: dict[str, TermDescription] = {
            k: v if isinstance(v, TermDescription) else TermDescription.from_raw(v)
            for k, v in terms.items()
        }
        self.renderer = renderer
        self.warn_unknown = warn_unknown
        bind = getattr(renderer, "bind", None)
        if callable(bind):
            bind(self)

    @classmethod
    def from_gamedata_const(cls, gamedata_const: Any, renderer: Renderer) -> "RichText":
        """``gamedata_const`` 是 ``gamedata_const.GameDataConsts`` 模型或原始 dict。"""

        if isinstance(gamedata_const, Mapping):
            styles = gamedata_const.get("richTextStyles")
            terms = gamedata_const.get("termDescriptionDict")
        else:
            styles = getattr(gamedata_const, "rich_text_styles", None)
            terms = getattr(gamedata_const, "term_description_dict", None)
        return cls(styles or {}, terms or {}, renderer)

    def compile(self, text: str | None, *, convert_newline: bool = True) -> str:
        """渲染整段文本;``None`` 视为空串。

        ``convert_newline`` 对应客户端最后一步把字面量 ``\\n`` 换成换行,
        目标写法由 ``renderer.newline`` 决定。
        """

        if not text:
            return ""
        result, _ = self._format(text, 0, None)
        if convert_newline:
            result = result.replace("\\n", self.renderer.newline)
        return result

    # ``SharedFormatUtil.FormatRichTextTag`` 的直译。返回 (渲染结果, 新的读取位置)。
    def _format(self, source: str, pos: int, open_tag: str | None) -> tuple[str, int]:
        out: list[str] = []
        length = len(source)
        tag_start = -1  # -1 表示不在标签内
        while pos < length:
            char = source[pos]
            pos += 1
            if char == "<":
                # 上一个 "<" 还没收到 ">" 就又来了一个:前一段按普通文字输出
                if tag_start >= 0 and pos - 1 > tag_start:
                    out.append("<" + source[tag_start : pos - 1])
                tag_start = pos
            elif char == ">" and tag_start >= 0:
                tag = source[tag_start : pos - 1]
                tag_start = -1
                closed = self._handle(open_tag, tag, "".join(out))
                if closed is not None:
                    return closed, pos
                if is_start_tag(tag):
                    nested, pos = self._format(source, pos, tag)
                    out.append(nested)
                else:
                    out.append(f"<{tag}>")
            elif tag_start < 0:
                out.append(char)
        # 收到 "<" 之后直到结尾都没有 ">":客户端把它当普通文字保留
        if tag_start >= 0 and length > tag_start:
            out.append("<" + source[tag_start:])
        return "".join(out), pos

    # ``SharedFormatUtil.RichTextConvertTagsHandler`` 的直译。
    # ``end_tag`` 与 ``open_tag`` 配对时返回渲染结果,否则返回 None。
    def _handle(self, open_tag: str | None, end_tag: str, content: str) -> str | None:
        if not open_tag:
            return None
        renderer = self.renderer
        if open_tag.startswith("@"):
            if end_tag != "/":
                return None
            style_id = open_tag[1:].lower()
            template = self.styles.get(style_id)
            if template is None and self.warn_unknown:
                logger.warning(f"Rich text style not found: [{open_tag}]")
            return renderer.style(style_id, template, content)
        if open_tag.startswith("color"):
            if end_tag != "/color":
                return None
            return renderer.color(open_tag[open_tag.find("=") + 1 :], content)
        if open_tag == "i":
            return renderer.italic(content) if end_tag == "/i" else None
        if open_tag == "b":
            return renderer.bold(content) if end_tag == "/b" else None
        if open_tag.startswith("$"):
            if end_tag != "/":
                return None
            term_id = open_tag[1:]
            term = self.terms.get(term_id)
            if term is None and self.warn_unknown:
                logger.warning(f"Term description not found: [{open_tag}]")
            return renderer.term(term_id, term, content)
        return None
