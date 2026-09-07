import pytest

from ptilopsis.utils.blackboard import (
    blackboard_values,
    format_number,
    format_paramed_text,
)


def test_blackboard_values_lowercases_keys_and_skips_string_values() -> None:
    values = blackboard_values(
        [
            {"key": "atk_scale_AOE", "value": 1.5, "valueStr": None},
            {"key": "Attack@Stun", "value": 2.0, "valueStr": ""},
            {"key": "buff_id", "value": 0.0, "valueStr": "some_buff"},
        ]
    )
    assert values == {"atk_scale_aoe": 1.5, "attack@stun": 2.0}
    assert blackboard_values(None) == {}


@pytest.mark.parametrize(
    ("value", "spec", "expected"),
    [
        (0.3, "0%", "30%"),
        (0.125, "0%", "13%"),  # 精确的中点:.NET 远离零
        (0.145, "0%", "15%"),  # float 0.145 略小于 0.145,但先取 7 位有效数字
        (-0.22, "0%", "-22%"),
        (0.125, "0.0%", "12.5%"),
        (1.5, "0.0", "1.5"),
        (1.55, "0.0", "1.6"),
        (2.0, "0.0", "2"),
        (2.0, "0", "2"),
        (2.4, "0", "2"),
        (2.0, None, "2"),
        (0.22, None, "0.22"),
        (1500.0, None, "1500"),
        (30.0, "", "30"),
        (0.0, "0%", "0%"),
        (-0.001, "0%", "0%"),
        (1.25, "#.##", "1.25"),
        (1.2, "#.##", "1.2"),
    ],
)
def test_format_number(value: float, spec: str | None, expected: str) -> None:
    assert format_number(value, spec) == expected


def test_format_number_can_keep_decimals_like_the_client() -> None:
    assert format_number(2.0, "0.0", strip_integral_decimals=False) == "2.0"


BLACKBOARD = {"atk": 0.3, "attack@move_speed": -0.22, "duration": 20.0, "cost": 4.0}


def test_placeholders_are_replaced() -> None:
    assert (
        format_paramed_text("攻击力提升{atk:0%},持续{duration}秒", BLACKBOARD)
        == "攻击力提升30%,持续20秒"
    )


def test_key_lookup_is_case_insensitive_and_keeps_symbols() -> None:
    assert format_paramed_text("{ATTACK@MOVE_SPEED:0%}", BLACKBOARD) == "-22%"


def test_leading_minus_negates_value() -> None:
    # 客户端:占位符第二个字符是 - 时把值取反再格式化
    assert format_paramed_text("降低{-attack@move_speed:0%}", BLACKBOARD) == "降低22%"
    assert format_paramed_text("-{-atk:0%}", BLACKBOARD) == "--30%"


def test_spaces_inside_placeholder_are_ignored() -> None:
    assert format_paramed_text("{ atk : 0% }", BLACKBOARD) == "30%"


def test_missing_key_keeps_placeholder() -> None:
    assert format_paramed_text("{nope:0%}和{atk:0%}", BLACKBOARD) == "{nope:0%}和30%"


def test_unterminated_brace_is_kept() -> None:
    assert format_paramed_text("a{atk", BLACKBOARD) == "a{atk"


def test_invalid_placeholder_is_kept() -> None:
    assert format_paramed_text("{}", BLACKBOARD) == "{}"


def test_none_blackboard_returns_text_unchanged() -> None:
    assert format_paramed_text("{atk:0%}", None) == "{atk:0%}"
    assert format_paramed_text(None, BLACKBOARD) == ""
