"""job 函数可以直接注入的现成依赖(见 :mod:`ptilopsis.utils.job`)。

用法::

    from typing import Annotated

    @job
    def run(
        wiki: Wiki,
        item_table: RawItemTable,
        stage_table: Annotated[dict[str, Any], gamedata("excel/stage_table.json")],
        rts: RichText,
        char_list: Annotated[list[str], category("分类:干员")],
    ) -> None: ...

``RawXxx`` 是尚未建模的原始 dict;要类型化的表给 ``gamedata`` 传 ``model``。
"""

import csv
import io
from typing import TYPE_CHECKING, Annotated, Any

from ptilopsis.utils.data import GameData
from ptilopsis.utils.di import Depends
from ptilopsis.utils.richTextStyles import RichTextStyles
from ptilopsis.utils.wiki import Wiki

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "CharIdTable",
    "RawBuildingData",
    "RawCharacterTable",
    "RawGamedataConst",
    "RawItemTable",
    "RawSkillTable",
    "RawSkinTable",
    "RawUniEquipTable",
    "RichText",
    "category",
    "gamedata",
    "gamedata_text",
]


def gamedata(path: str, model: Any = None, region: str = "CN") -> Any:
    """``gamedata/<path>`` 解码后的 JSON;给 ``model`` 时校验成 pydantic 模型
    (``BaseModel`` 或 ``TypeAdapter`` 都可以)。

    同一路径在一次 job 运行里只读一次;excel 表由 GameData 跨 job 缓存。
    """

    validate: Callable[[Any], Any] | None = None
    if model is not None:
        validate = getattr(model, "validate_python", None) or model.model_validate

    def dependency(data: GameData) -> Any:
        raw = data.get(path, region)
        return validate(raw) if validate is not None else raw

    dependency.__qualname__ = f"gamedata({path!r})"
    return Depends(dependency)


def gamedata_text(path: str, region: str = "CN") -> Any:
    """``gamedata/<path>`` 的原始文本(剧情等非 JSON 文件)。"""

    def dependency(data: GameData) -> str:
        return data.get_txt(path, region)

    dependency.__qualname__ = f"gamedata_text({path!r})"
    return Depends(dependency)


RawCharacterTable = Annotated[dict[str, Any], gamedata("excel/character_table.json")]
RawSkillTable = Annotated[dict[str, Any], gamedata("excel/skill_table.json")]
RawItemTable = Annotated[dict[str, Any], gamedata("excel/item_table.json")]
RawBuildingData = Annotated[dict[str, Any], gamedata("excel/building_data.json")]
RawSkinTable = Annotated[dict[str, Any], gamedata("excel/skin_table.json")]
RawUniEquipTable = Annotated[dict[str, Any], gamedata("excel/uniequip_table.json")]
RawGamedataConst = Annotated[dict[str, Any], gamedata("excel/gamedata_const.json")]


def _rich_text(data: GameData) -> RichTextStyles:
    return RichTextStyles(data.get("excel/gamedata_const.json", "CN"))


RichText = Annotated[RichTextStyles, Depends(_rich_text)]
"""按 gamedata_const 构造的富文本转换器。"""


def _char_id_table(wiki: Wiki) -> dict[str, dict[str, Any]]:
    """wiki 上维护的 ``干员一览/干员id`` 表:``{干员名: {id, approach, date}}``。"""

    reader = csv.DictReader(io.StringIO(wiki.read("干员一览/干员id")))
    return {
        row["name"]: {
            "id": int(row["sortId"]),
            "approach": row["approach"],
            "date": row["date"],
        }
        for row in reader
    }


CharIdTable = Annotated[dict[str, dict[str, Any]], Depends(_char_id_table)]
"""``干员一览/干员id`` 解析后的干员序号 / 获得方式 / 上线时间。"""


def category(name: str) -> Any:
    """wiki 分类 ``name`` 下的全部页面标题。"""

    def dependency(wiki: Wiki) -> list[str]:
        return wiki.category(name)

    dependency.__qualname__ = f"category({name!r})"
    return Depends(dependency)
