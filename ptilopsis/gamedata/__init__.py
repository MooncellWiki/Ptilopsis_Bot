"""gamedata 原始数据的 pydantic 模型。

- ``character_table`` / ``skill_table`` / ``uniequip_table`` / ``battle_equip_table``
  / ``handbook_team_table`` / ``gamedata_const``:由 ``scripts/gen_gamedata_models.py``
  从 thirdparty/OpenArknightsFBS/FBS 生成,整张表建模,请勿手改。上游 FBS 更新后
  重新生成即可。
- ``stage`` / ``medal``:早于生成器的手写模型,只包含 job 消费的字段。
- ``character_util``:客户端 CharacterUtil 里的候选选择与隐藏规则。

生成模型的空值约定见 ``_base``:string / table / vector 一律 ``T | None``,
让 pyright 在编译期就指出没有判空的访问。
"""
