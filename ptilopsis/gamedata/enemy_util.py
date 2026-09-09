"""enemy_database 的辅助函数。

``enemy_database.json`` 的 ``enemies`` 在 JSON 里是 ``[{"Key": id, "Value": [各级别]}]``
(FBS 里的 ``kvp__``),多数 job 需要按敌人 id 查各级别数据,这里统一建索引。
"""

from ptilopsis.gamedata.enemy_database import EnemyDatabase, EnemyDatabaseEnemyLevel

__all__ = ["index_enemy_levels"]


def index_enemy_levels(
    database: EnemyDatabase,
) -> dict[str, list[EnemyDatabaseEnemyLevel]]:
    """``{enemyId: [level 0, level 1, ...]}``;缺 Key / Value 的条目跳过。"""

    index: dict[str, list[EnemyDatabaseEnemyLevel]] = {}
    for entry in database.enemies or []:
        if entry.key is None or entry.value is None:
            continue
        index[entry.key] = entry.value
    return index
