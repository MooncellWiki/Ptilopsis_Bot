import pytest

from ptilopsis.jobs.operator_ids import append_rows


def test_append_preserves_existing_order_and_can_be_retried() -> None:
    current = "sortId,name,rarity,approach,date\n440,塔露拉,5,限定寻访,2026-11-01 12:00"
    additions = (
        "name,rarity,approach,date\n"
        "干员甲,3,凭证交易所,2026-11-25 12:00\n"
        "干员乙,5,标准寻访,2026-11-25 12:00\n"
    )
    updated = append_rows(current, additions)
    assert updated == current + (
        "\n441,干员甲,3,凭证交易所,2026-11-25 12:00"
        "\n442,干员乙,5,标准寻访,2026-11-25 12:00"
    )
    assert append_rows(updated, additions) == updated
    with pytest.raises(ValueError, match="已有不一致"):
        append_rows(updated, additions.replace("凭证交易所", "标准寻访"))
