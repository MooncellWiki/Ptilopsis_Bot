import pytest

from ptilopsis.utils.richtext import (
    HtmlRenderer,
    PlainRenderer,
    RichText,
    WikiRenderer,
    is_start_tag,
)

STYLES = {
    "ba.vup": "<color=#0098DC>{0}</color>",
    "ba.kw": "<color=#00B0FF>{0}</color>",
    "ba.pn": "<i>{0}</i>",
    "cc.talpu": "{0}",
}
TERMS = {
    "ba.stun": {"termId": "ba.stun", "termName": "晕眩", "description": "无法移动"},
    "ba.buffres": {
        "termId": "ba.buffres",
        "termName": "抵抗",
        "description": "<$ba.stun>晕眩</>等异常状态的<@ba.kw>持续时间减半</>",
    },
}
GAMEDATA_CONST = {"richTextStyles": STYLES, "termDescriptionDict": TERMS}


@pytest.fixture
def wiki() -> RichText:
    return RichText(STYLES, TERMS, WikiRenderer())


def test_color_style_becomes_color_template(wiki: RichText) -> None:
    assert wiki.compile("<@ba.vup>攻击力</>提升") == "{{color|#0098DC|攻击力}}提升"


def test_style_lookup_is_case_insensitive(wiki: RichText) -> None:
    # 客户端查表前 ToLower
    assert wiki.compile("<@Ba.VUP>x</>") == "{{color|#0098DC|x}}"


def test_non_color_style_applies_template_instead_of_breaking(wiki: RichText) -> None:
    assert wiki.compile("<@ba.pn>斜体</>文本") == "<i>斜体</i>文本"
    assert wiki.compile("<@cc.talpu>纯文本</>") == "纯文本"


def test_unknown_style_keeps_content(wiki: RichText) -> None:
    # RichTextConvertTagsHandler:Rich text style not found → 原样返回内容
    assert wiki.compile("<@ba.unknown>未知</>") == "未知"


def test_known_term_becomes_term_template(wiki: RichText) -> None:
    assert wiki.compile("<$ba.stun>晕眩</>") == "{{术语|ba.stun|晕眩}}"


def test_unknown_term_keeps_content(wiki: RichText) -> None:
    assert wiki.compile("<$ba.nope>不存在</>") == "不存在"


def test_nested_tags_close_innermost_first(wiki: RichText) -> None:
    assert (
        wiki.compile("<@ba.vup>外层<@ba.kw>内层</>尾</>")
        == "{{color|#0098DC|外层{{color|#00B0FF|内层}}尾}}"
    )


def test_color_tag_passthrough(wiki: RichText) -> None:
    assert wiki.compile("<color=#FF0000>红</color>") == "{{color|#FF0000|红}}"


def test_italic_and_bold(wiki: RichText) -> None:
    assert wiki.compile("<i>斜</i><b>粗</b>") == "<i>斜</i><b>粗</b>"


def test_unknown_tag_is_kept_literally(wiki: RichText) -> None:
    # <替身> 之类不是富文本标签,客户端原样输出
    assert (
        wiki.compile("<替身>状态下<size=20>字</size>")
        == "<替身>状态下<size=20>字</size>"
    )


def test_mismatched_close_tag_is_kept_literally(wiki: RichText) -> None:
    # <@x> 只能由 </> 收尾;遇到 </color> 时按普通文字输出,继续找 </>
    assert wiki.compile("<@ba.vup>a</color>b</>") == "{{color|#0098DC|a</color>b}}"


def test_unterminated_tag_is_kept(wiki: RichText) -> None:
    assert wiki.compile("a<@ba.vup") == "a<@ba.vup"
    assert wiki.compile("a<<@ba.vup>b</>") == "a{{color|#0098DC|b}}"


def test_stray_close_tag_at_top_level_is_literal(wiki: RichText) -> None:
    assert wiki.compile("a</>b") == "a</>b"


def test_newline_conversion(wiki: RichText) -> None:
    assert wiki.compile("一\\n二") == "一<br/>二"
    assert wiki.compile("一\\n二", convert_newline=False) == "一\\n二"


def test_none_and_empty(wiki: RichText) -> None:
    assert wiki.compile(None) == ""
    assert wiki.compile("") == ""


def test_plain_renderer_strips_everything() -> None:
    plain = RichText(STYLES, TERMS, PlainRenderer())
    assert (
        plain.compile("<@ba.vup>a<$ba.stun>b</></>\\n<color=#fff>c</color>") == "ab\nc"
    )


def test_html_renderer_term_tooltip_uses_stripped_description() -> None:
    html = RichText(STYLES, TERMS, HtmlRenderer())
    assert (
        html.compile("<@ba.vup>攻击力</>")
        == '<span style="color:#0098DC;">攻击力</span>'
    )
    assert html.compile("<$ba.buffres>抵抗</>") == (
        '<span class="mc-tooltips"><span>抵抗</span>'
        "<span>晕眩等异常状态的持续时间减半</span></span>"
    )


def test_is_start_tag() -> None:
    assert is_start_tag("@ba.vup")
    assert is_start_tag("$ba.stun")
    assert is_start_tag("color=#fff")
    assert is_start_tag("i") and is_start_tag("b")
    assert not is_start_tag("/")
    assert not is_start_tag("替身")
    assert not is_start_tag("")


def test_from_gamedata_const_dict() -> None:
    rts = RichText.from_gamedata_const(GAMEDATA_CONST, WikiRenderer())
    assert rts.compile("<@ba.vup>a</>\\nb") == "{{color|#0098DC|a}}<br/>b"
    assert rts.compile(None) == ""


def test_from_gamedata_const_with_html_renderer() -> None:
    rts = RichText.from_gamedata_const(GAMEDATA_CONST, HtmlRenderer())
    assert rts.compile("<@ba.kw>x</>") == '<span style="color:#00B0FF;">x</span>'
