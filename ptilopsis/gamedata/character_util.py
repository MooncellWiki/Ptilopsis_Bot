"""客户端 ``Torappu.CharacterUtil`` / ``TalentDataBundle`` 里与展示相关的规则。

以下规则来自 2.7.61/2.7.71 的反编译,页面生成时按它们选候选、判隐藏,
而不是依赖数组顺序或 ``[-1]``:

- ``TalentDataBundle.DoGetTalent`` / ``CharacterUtil.TryGetTrait``:候选按
  (解锁条件, 潜能要求) 降序排序,取第一个满足当前 (精英, 等级, 潜能) 的;
  候选列表为空或 null 时视为没有。
- ``CharacterUtil.CheckIfCharTalentHideOnUI``:天赋为 null、描述或名字为空、
  或 ``isHideTalent`` 时不在界面上展示。
- ``CharacterData.GetRawDescriptionFormatByTraitBlackboard``:无特性候选时
  用 ``description``;否则 ``overrideDescripton`` 非空就用它,再用该候选的
  黑板做占位符替换。
"""

from collections.abc import Sequence
from typing import Protocol

from ptilopsis.gamedata.character_table import (
    BlackboardDataPair,
    CharacterData,
    CharacterDataTalentDataBundle,
    CharacterDataUnlockCondition,
    EvolvePhase,
    RarityRank,
    TalentData,
)

__all__ = [
    "MAX_POTENTIAL_RANK",
    "is_talent_hidden_on_ui",
    "phase_index",
    "rarity_stars",
    "select_candidate",
    "trait_description",
    "unlock_satisfied",
    "visible_talent_candidates",
]

MAX_POTENTIAL_RANK = 5
"""potentialRank 取值 0..5,对应潜能 1..6。"""


class Candidate(Protocol):
    """特性 / 天赋 / 模组候选共有的解锁字段。"""

    @property
    def unlock_condition(self) -> CharacterDataUnlockCondition | None: ...

    @property
    def required_potential_rank(self) -> int: ...


def phase_index(phase: str | None) -> int:
    """``"PHASE_2"`` → 2;未知取值按 0。"""

    if not phase:
        return 0
    try:
        return int(EvolvePhase[phase])
    except KeyError:
        return 0


def rarity_stars(rarity: str | None) -> int:
    """``"TIER_6"`` → 6;未知取值按 0。"""

    if not rarity:
        return 0
    try:
        return int(RarityRank[rarity]) + 1
    except KeyError:
        return 0


def _unlock_key(condition: CharacterDataUnlockCondition | None) -> tuple[int, int]:
    if condition is None:
        return (0, 0)
    return (phase_index(condition.phase), condition.level)


def unlock_satisfied(
    condition: CharacterDataUnlockCondition | None, level: int, phase: int
) -> bool:
    """``CharacterData.UnlockCondition.Validate``。"""

    if condition is None:
        return True
    required_phase = phase_index(condition.phase)
    if phase > required_phase:
        return True
    return phase == required_phase and level >= condition.level


def select_candidate[T: Candidate](
    candidates: Sequence[T] | None, *, level: int, phase: int, potential: int
) -> T | None:
    """``TalentDataBundle.DoGetTalent`` / ``CharacterUtil.TryGetTrait``。"""

    if not candidates:
        return None
    ordered = sorted(
        candidates,
        key=lambda c: (_unlock_key(c.unlock_condition), c.required_potential_rank),
        reverse=True,
    )
    for candidate in ordered:
        if (
            unlock_satisfied(candidate.unlock_condition, level, phase)
            and potential >= candidate.required_potential_rank
        ):
            return candidate
    return None


def is_talent_hidden_on_ui(talent: TalentData | None) -> bool:
    """``CharacterUtil.CheckIfCharTalentHideOnUI``。"""

    if talent is None:
        return True
    if not talent.description or not talent.name:
        return True
    return talent.is_hide_talent


def visible_talent_candidates(
    bundle: CharacterDataTalentDataBundle | None,
) -> list[TalentData]:
    """一个天赋槽里会在界面上出现过的候选,按解锁顺序排列。

    wiki 的天赋列表展示全部成长阶段,所以不像客户端只取当前那一个。
    """

    if bundle is None or not bundle.candidates:
        return []
    visible = [c for c in bundle.candidates if not is_talent_hidden_on_ui(c)]
    return sorted(
        visible,
        key=lambda c: (_unlock_key(c.unlock_condition), c.required_potential_rank),
    )


def trait_description(
    char: CharacterData, *, level: int, phase: int, potential: int
) -> tuple[str | None, list[BlackboardDataPair] | None]:
    """``CharacterData.GetRawDescriptionFormatByTraitBlackboard`` 的取值部分。

    返回 (未做占位符替换的描述, 用于替换的黑板);没有特性候选时黑板为 None,
    调用方直接用描述。
    """

    if char.trait is None:
        return char.description, None
    candidate = select_candidate(
        char.trait.candidates, level=level, phase=phase, potential=potential
    )
    if candidate is None:
        return char.description, None
    description = candidate.override_descripton or char.description
    return description, candidate.blackboard
