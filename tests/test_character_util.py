from ptilopsis.gamedata.character_table import (
    BlackboardDataPair,
    CharacterData,
    CharacterDataTalentDataBundle,
    CharacterDataTraitData,
    CharacterDataTraitDataBundle,
    CharacterDataUnlockCondition,
    TalentData,
)
from ptilopsis.gamedata.character_util import (
    MAX_POTENTIAL_RANK,
    is_talent_hidden_on_ui,
    phase_index,
    rarity_stars,
    select_candidate,
    trait_description,
    visible_talent_candidates,
)


def talent(phase: str, level: int, potential: int, **kwargs) -> TalentData:
    return TalentData(
        unlock_condition=CharacterDataUnlockCondition(phase=phase, level=level),
        required_potential_rank=potential,
        name=kwargs.pop("name", "天赋"),
        description=kwargs.pop("description", "效果"),
        **kwargs,
    )


def test_phase_index_and_rarity() -> None:
    assert phase_index("PHASE_2") == 2
    assert phase_index("UNKNOWN") == 0
    assert phase_index(None) == 0
    assert rarity_stars("TIER_6") == 6
    assert rarity_stars("TIER_X") == 0


def test_select_candidate_prefers_highest_satisfied_condition() -> None:
    # 故意打乱顺序:客户端会先按 (解锁条件, 潜能) 降序再取第一个满足的
    candidates = [
        talent("PHASE_1", 1, 0, description="e1"),
        talent("PHASE_0", 1, 0, description="e0"),
        talent("PHASE_2", 1, 0, description="e2"),
        talent("PHASE_2", 1, 5, description="e2p5"),
    ]
    pick = select_candidate(candidates, level=1, phase=2, potential=5)
    assert pick is not None and pick.description == "e2p5"
    pick = select_candidate(candidates, level=1, phase=2, potential=0)
    assert pick is not None and pick.description == "e2"
    pick = select_candidate(candidates, level=30, phase=1, potential=5)
    assert pick is not None and pick.description == "e1"
    pick = select_candidate(candidates, level=1, phase=0, potential=0)
    assert pick is not None and pick.description == "e0"


def description_at(candidates: list[TalentData], level: int, phase: int) -> str:
    pick = select_candidate(candidates, level=level, phase=phase, potential=0)
    assert pick is not None
    return pick.description or ""


def test_select_candidate_level_within_phase() -> None:
    candidates = [talent("PHASE_0", 1, 0), talent("PHASE_0", 30, 0, description="lv30")]
    assert description_at(candidates, 29, 0) == "效果"
    assert description_at(candidates, 30, 0) == "lv30"
    # 精英 1 时不看等级
    assert description_at(candidates, 1, 1) == "lv30"


def test_select_candidate_handles_null_and_unsatisfied() -> None:
    assert select_candidate(None, level=1, phase=0, potential=0) is None
    assert select_candidate([], level=1, phase=0, potential=0) is None
    assert (
        select_candidate([talent("PHASE_2", 1, 0)], level=1, phase=1, potential=0)
        is None
    )


def test_talent_hidden_rules() -> None:
    assert is_talent_hidden_on_ui(None)
    assert is_talent_hidden_on_ui(talent("PHASE_0", 1, 0, description=None))
    assert is_talent_hidden_on_ui(talent("PHASE_0", 1, 0, name=None))
    assert is_talent_hidden_on_ui(talent("PHASE_0", 1, 0, is_hide_talent=True))
    assert not is_talent_hidden_on_ui(talent("PHASE_0", 1, 0))


def test_visible_talent_candidates_filters_and_sorts() -> None:
    bundle = CharacterDataTalentDataBundle(
        candidates=[
            talent("PHASE_2", 1, 0, description="e2"),
            talent("PHASE_0", 1, 5, description="e0p5"),
            talent("PHASE_0", 1, 0, description="e0"),
            talent("PHASE_1", 1, 0, is_hide_talent=True),
        ]
    )
    assert [c.description for c in visible_talent_candidates(bundle)] == [
        "e0",
        "e0p5",
        "e2",
    ]
    assert visible_talent_candidates(None) == []
    assert (
        visible_talent_candidates(CharacterDataTalentDataBundle(candidates=None)) == []
    )


def test_trait_description_uses_override_and_candidate_blackboard() -> None:
    char = CharacterData(
        description="默认{value}",
        trait=CharacterDataTraitDataBundle(
            candidates=[
                CharacterDataTraitData(
                    unlock_condition=CharacterDataUnlockCondition(
                        phase="PHASE_0", level=1
                    ),
                    blackboard=[BlackboardDataPair(key="value", value=1.0)],
                ),
                CharacterDataTraitData(
                    unlock_condition=CharacterDataUnlockCondition(
                        phase="PHASE_2", level=1
                    ),
                    override_descripton="精二{value}",
                    blackboard=[BlackboardDataPair(key="value", value=2.0)],
                ),
            ]
        ),
    )
    text, blackboard = trait_description(
        char, level=1, phase=0, potential=MAX_POTENTIAL_RANK
    )
    assert (
        text == "默认{value}" and blackboard is not None and blackboard[0].value == 1.0
    )
    text, blackboard = trait_description(
        char, level=1, phase=2, potential=MAX_POTENTIAL_RANK
    )
    assert (
        text == "精二{value}" and blackboard is not None and blackboard[0].value == 2.0
    )


def test_trait_description_without_trait() -> None:
    char = CharacterData(description="默认")
    assert trait_description(char, level=1, phase=0, potential=0) == ("默认", None)
    char = CharacterData(description="默认", trait=CharacterDataTraitDataBundle())
    assert trait_description(char, level=1, phase=0, potential=0) == ("默认", None)
