"""gamedata 原始数据的 pydantic 模型。

- 各 ``<table>.py``:由 ``scripts/gen_gamedata_models.py`` 从
  thirdparty/OpenArknightsFBS/FBS 生成,整张表建模,请勿手改;上游 FBS 更新后
  ``uv run python scripts/gen_gamedata_models.py --all`` 重新生成即可。
  ``levels/*.json`` 的模型在 ``level_data``(来自 ``prts___levels.fbs``)。
- ``range_table`` / ``battle_misc_table`` / ``roguelike_table``:没有 FBS schema 的
  普通 JSON 表,按同样的约定手写。
- ``character_util``:客户端 CharacterUtil 里的候选选择与隐藏规则;
  ``enemy_util``:enemy_database 的索引。

job 里不要直接 ``model_validate``,用 ``ptilopsis.jobs.params`` 里的依赖注入。
空值约定见 ``_base``:string / table / vector 一律 ``T | None``,
让 pyright 在编译期就指出没有判空的访问。
"""
