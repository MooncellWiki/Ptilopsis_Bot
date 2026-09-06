"""battle_equip_table.json 的数据模型。

由 scripts/gen_gamedata_models.py 从 FBS/battle_equip_table.fbs 生成,请勿手改;
字段语义见 dump.cs 里的同名类。
"""

from __future__ import annotations

from enum import IntEnum

from pydantic import TypeAdapter

from ptilopsis.gamedata._base import GameDataModel


class UniEquipTarget(IntEnum):
    """enum__Torappu_UniEquipTarget"""

    NONE = 0
    TRAIT = 1
    TRAIT_DATA_ONLY = 2
    TALENT = 3
    TALENT_DATA_ONLY = 4
    DISPLAY = 5
    OVERWRITE_BATTLE_DATA = 6


class EvolvePhase(IntEnum):
    """enum__Torappu_EvolvePhase"""

    PHASE_0 = 0
    PHASE_1 = 1
    PHASE_2 = 2
    PHASE_3 = 3
    E_NUM = 4


class CharacterDataUnlockCondition(GameDataModel):
    """clz_Torappu_CharacterData_UnlockCondition"""

    phase: str = "PHASE_0"
    level: int = 0


class BlackboardDataPair(GameDataModel):
    """clz_Torappu_Blackboard_DataPair"""

    key: str | None = None
    value: float = 0.0
    value_str: str | None = None


class EquipTalentData(GameDataModel):
    """clz_Torappu_EquipTalentData"""

    display_range_id: bool = False
    upgrade_description: str | None = None
    talent_index: int = 0
    valid_mode_indices: list[int] | None = None
    unlock_condition: CharacterDataUnlockCondition | None = None
    required_potential_rank: int = 0
    prefab_key: str | None = None
    name: str | None = None
    description: str | None = None
    range_id: str | None = None
    blackboard: list[BlackboardDataPair] | None = None
    token_key: str | None = None
    is_hide_talent: bool = False


class TalentData(GameDataModel):
    """clz_Torappu_TalentData"""

    unlock_condition: CharacterDataUnlockCondition | None = None
    required_potential_rank: int = 0
    prefab_key: str | None = None
    name: str | None = None
    description: str | None = None
    range_id: str | None = None
    blackboard: list[BlackboardDataPair] | None = None
    token_key: str | None = None
    is_hide_talent: bool = False


class CharacterDataEquipTalentDataBundle(GameDataModel):
    """clz_Torappu_CharacterData_EquipTalentDataBundle"""

    candidates: list[EquipTalentData] | None = None


class CharacterDataEquipTraitData(GameDataModel):
    """clz_Torappu_CharacterData_EquipTraitData"""

    additional_description: str | None = None
    unlock_condition: CharacterDataUnlockCondition | None = None
    required_potential_rank: int = 0
    blackboard: list[BlackboardDataPair] | None = None
    override_descripton: str | None = None
    prefab_key: str | None = None
    range_id: str | None = None


class CharacterDataEquipTraitDataBundle(GameDataModel):
    """clz_Torappu_CharacterData_EquipTraitDataBundle"""

    candidates: list[CharacterDataEquipTraitData] | None = None


class BattleUniEquipData(GameDataModel):
    """clz_Torappu_BattleUniEquipData"""

    res_key: str | None = None
    target: str = "NONE"
    is_token: bool = False
    valid_in_game_tag: str | None = None
    valid_in_map_tag: str | None = None
    add_or_override_talent_data_bundle: CharacterDataEquipTalentDataBundle | None = None
    override_trait_data_bundle: CharacterDataEquipTraitDataBundle | None = None


class BattleEquipPerLevelPack(GameDataModel):
    """clz_Torappu_BattleEquipPerLevelPack"""

    equip_level: int = 0
    parts: list[BattleUniEquipData] | None = None
    attribute_blackboard: list[BlackboardDataPair] | None = None
    token_attribute_blackboard: dict[str, list[BlackboardDataPair]] | None = None


class BattleEquipPack(GameDataModel):
    """clz_Torappu_BattleEquipPack"""

    phases: list[BattleEquipPerLevelPack] | None = None


# root_type clz_Torappu_SimpleKVTable_clz_Torappu_BattleEquipPack
# JSON 里去掉了外层的 equips,直接是 {id: ...}
BattleEquipTable = TypeAdapter(dict[str, BattleEquipPack])


CharacterDataUnlockCondition.model_rebuild()
BlackboardDataPair.model_rebuild()
EquipTalentData.model_rebuild()
TalentData.model_rebuild()
CharacterDataEquipTalentDataBundle.model_rebuild()
CharacterDataEquipTraitData.model_rebuild()
CharacterDataEquipTraitDataBundle.model_rebuild()
BattleUniEquipData.model_rebuild()
BattleEquipPerLevelPack.model_rebuild()
BattleEquipPack.model_rebuild()
