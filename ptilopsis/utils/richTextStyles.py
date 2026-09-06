"""``RichTextStyles(gamedata_const).compile(text)``:各 job 沿用的富文本入口。

解析规则见 :mod:`ptilopsis.utils.richtext`;这里只保留旧接口。历史行为里
``compile`` 不处理字面量 ``\\n``,由调用方自行换成 ``<br/>``,这一点维持不变,
需要一步到位的新代码直接用 :class:`~ptilopsis.utils.richtext.RichText`。
"""

from collections.abc import Mapping
from typing import Any

from ptilopsis.utils.richtext import Renderer, RichText, WikiRenderer

__all__ = ["RichTextStyles"]


class RichTextStyles:
    def __init__(
        self, gamedata_const: Mapping[str, Any], renderer: Renderer | None = None
    ) -> None:
        self.rich_text = RichText.from_gamedata_const(
            gamedata_const, renderer or WikiRenderer()
        )

    def compile(self, s: str | None) -> str:
        return self.rich_text.compile(s, convert_newline=False)
