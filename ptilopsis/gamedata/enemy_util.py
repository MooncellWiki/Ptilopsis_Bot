"""enemy_database 的辅助函数。

``enemy_database.json`` 的 ``enemies`` 在 JSON 里是 ``[{"Key": id, "Value": [各级别]}]``
(FBS 里的 ``kvp__``),多数 job 需要按敌人 id 查各级别数据,这里统一建索引。
"""

from collections.abc import Iterable, Mapping

from ptilopsis.gamedata.enemy_database import EnemyDatabase, EnemyDatabaseEnemyLevel
from ptilopsis.gamedata.enemy_handbook_table import EnemyHandBookData

__all__ = ["UNLISTED_ENEMY", "EnemySortKey", "enemy_sort_keys", "index_enemy_levels"]

type EnemySortKey = tuple[int, int]
UNLISTED_ENEMY: EnemySortKey = (2, 0)


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


def enemy_sort_keys(
    handbook: Mapping[str, EnemyHandBookData], database_ids: Iterable[str]
) -> dict[str, EnemySortKey]:
    """图鉴按 sortId 升序，未收录的条目按 enemy_database 原始顺序排在后面。"""

    keys = {enemy_id: (1, position) for position, enemy_id in enumerate(database_ids)}
    keys.update({enemy_id: (0, entry.sort_id) for enemy_id, entry in handbook.items()})
    return keys
