from unittest.mock import AsyncMock

import pytest

from ptilopsis.config import config
from ptilopsis.gamedata.enemy_database import EnemyDatabaseEnemyLevel
from ptilopsis.gamedata.enemy_handbook_table import (
    EnemyHandBookData,
    EnemyHandBookDataGroup,
)
from ptilopsis.jobs.enemy import run
from ptilopsis.utils.richtext import RichText, WikiRenderer
from ptilopsis.utils.wiki import Wiki


@pytest.mark.anyio
@pytest.mark.parametrize("template", [None, "敌人信息/完整级别"])
async def test_enemy_run_creates_levels_with_selected_template(
    template: str | None,
) -> None:
    wiki = AsyncMock(spec=Wiki)
    wiki.create.return_value = True
    handbook = EnemyHandBookDataGroup(
        enemy_data={
            "test_enemy": EnemyHandBookData(name="测试敌人", enemy_id="test_enemy"),
            "existing_enemy": EnemyHandBookData(
                name="已有敌人", enemy_id="existing_enemy"
            ),
        }
    )
    levels = [
        EnemyDatabaseEnemyLevel.model_validate(
            {
                "level": 0,
                "enemyData": {
                    "attributes": {
                        "maxHp": {"m_defined": True, "m_value": 45000},
                        "atk": {"m_defined": True, "m_value": 1600},
                        "def": {"m_defined": True, "m_value": 500},
                        "baseAttackTime": {"m_defined": True, "m_value": 4.0},
                    }
                },
            }
        ),
        EnemyDatabaseEnemyLevel.model_validate(
            {
                "level": 1,
                "enemyData": {
                    "attributes": {
                        "maxHp": {"m_defined": True, "m_value": 60000},
                        "atk": {"m_defined": True, "m_value": 0},
                        "def": {"m_defined": False, "m_value": 999},
                        "tauntLevel": {"m_defined": True, "m_value": -2},
                    },
                    "talentBlackboard": [{"key": "test_key", "value": 1}],
                },
            }
        ),
    ]

    await run.func(
        wiki,
        config.model_copy(update={"enemy_level_template": template}),
        handbook,
        {"test_enemy": levels},
        RichText({}, {}, WikiRenderer()),
        ["已有敌人"],
    )

    calls = wiki.create.await_args_list
    assert [call.kwargs["title"] for call in calls] == ["测试敌人", "测试敌人/spine"]
    second_level = calls[0].kwargs["text"].split("==级别1==", 1)[1]
    assert "|最大生命值=60000\n" in second_level
    assert "|攻击力=0\n" in second_level
    assert '|天赋=<!--[\n    {\n        "key": "test_key",' in second_level
    if template:
        assert f"{{{{{template}\n" in second_level
        assert "|防御力=500\n" in second_level
        assert "|攻击间隔=4.0\n" in second_level
        assert "|基础嘲讽等级=-2\n" in second_level
        assert "|数值变更=最大生命值,攻击力,基础嘲讽等级\n" in second_level
    else:
        assert "{{敌人信息/levelcontent\n" in second_level
        assert "|防御力=" not in second_level
        assert "|数值变更=" not in second_level
