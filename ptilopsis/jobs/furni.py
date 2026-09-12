from collections import Counter
from typing import Annotated

from ptilopsis.gamedata.building_data import (
    BuildingData,
    BuildingDataCustomData,
    BuildingDataCustomDataFurnitureData,
)
from ptilopsis.gamedata.item_table import InventoryData, ItemData
from ptilopsis.gamedata.shop_client_table import ShopClientData
from ptilopsis.jobs.params import ItemTable, ShopClientTable, table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def custom_data(building_data: BuildingData) -> BuildingDataCustomData:
    """家具 / 套装 / 主题等自定义数据;表里没有时按空表处理。"""

    return building_data.custom_data or BuildingDataCustomData()


def item_name(items: dict[str, ItemData], item_id: str | None) -> str:
    return (items[item_id or ""].name or "").rstrip()


def find_duplicates(building_data: BuildingData) -> set[str]:
    """同名家具(不同主题各有一款)的名字,它们的页面名要加主题后缀区分。"""

    furnitures = custom_data(building_data).furnitures or {}
    counts = Counter(furni.name or "" for furni in furnitures.values())
    return {name for name, count in counts.items() if count > 1}


def furni_theme_name(building_data: BuildingData, furni_id: str | None) -> str:
    """家具所属套件的主题名,散件返回空串。"""

    data = custom_data(building_data)
    themes = data.themes or {}
    for group in (data.groups or {}).values():
        if furni_id in (group.furniture or []):
            return themes[group.theme_id or ""].name or ""
    return ""


def furni_destroy_text(furni_data, items: dict[str, ItemData]) -> str:
    if furni_data.can_be_destroy:
        product = item_name(items, furni_data.processed_product_id)
        return f"{{{{材料消耗|{product}|{furni_data.processed_product_count}}}}}"
    return "不可分解"


def furni_sub_type_text(building_data: BuildingData, sub_type: str) -> str:
    sub_types = custom_data(building_data).sub_types or {}
    if sub_type in sub_types:
        return f"\n|子类型={sub_types[sub_type].name}"
    return ""


async def update_furni(
    wiki: Wiki,
    building_data: BuildingData,
    item_table: InventoryData,
    duplicates: set[str],
) -> None:
    data = custom_data(building_data)
    items = item_table.items or {}
    types = data.types or {}
    pages: list[tuple[str, BuildingDataCustomDataFurnitureData]] = []
    for furni_data in (data.furnitures or {}).values():
        furni_data.name = (furni_data.name or "").strip()
        page_name = furni_data.name
        if page_name in duplicates:
            themes = furni_theme_name(building_data, furni_data.id)
            if themes == "":
                themes = "散件"
            page_name += f"（{themes}）"
        pages.append((page_name, furni_data))

    # 一次性批量读取全部家具页,再逐个比对、按需编辑
    texts = await wiki.read_many(page_name for page_name, _ in pages)
    for page_name, furni_data in pages:
        origin_text = texts[page_name]

        num1 = origin_text.find("|描述=")
        num2 = origin_text.find("|", num1 + 4)
        new_text = (
            origin_text[:num1]
            + "|描述={}\n".format((furni_data.description or "").replace("\n", "<br>"))
            + origin_text[num2:]
        )

        furni_destroy = furni_destroy_text(furni_data, items)

        num1 = origin_text.find("|类型=")
        num2 = origin_text.find("|描述=")
        new_text = (
            new_text[:num1]
            + "|类型={type}{subType}\n|稀有度={rarity}\n|氛围={comfort}\n|分解获得={destroyObtain}\n|大小={size}\n".format(
                type=types[furni_data.type].name,
                subType=furni_sub_type_text(building_data, furni_data.sub_type),
                rarity=furni_data.rarity,
                comfort=furni_data.comfort,
                destroyObtain=furni_destroy,
                size=str(furni_data.width)
                + "×"
                + str(furni_data.depth)
                + "×"
                + str(furni_data.height),
            )
            + new_text[num2:]
        )

        if origin_text != new_text:
            await wiki.edit(title=page_name, text=new_text, summary="update")
            # logger.info(new_text)
            logger.info(f"Update: {page_name}.")
        else:
            logger.info(f"Same: {page_name}.")


async def create_furni(
    wiki: Wiki,
    building_data: BuildingData,
    item_table: InventoryData,
    duplicates: set[str],
) -> None:
    furni_list = await wiki.category("分类:家具")

    furni_format = """{{{{家具信息
|名称={name}
|iconId={id}
|类型={type}{subType}
|稀有度={rarity}
|氛围={comfort}
|分解获得={destroyObtain}
|大小={size}
|描述={description}
|用途={usage}
|获得方式={obtainApproach}
|所属套装={themes}
|所属组件={groups}
}}}}"""
    individual_furni = []

    data = custom_data(building_data)
    items = item_table.items or {}
    types = data.types or {}
    themes_data = data.themes or {}
    for furni_data in (data.furnitures or {}).values():
        furni_data.name = (furni_data.name or "").strip()
        if furni_data.name in ["taptap街机", "bilibili地毯"]:
            continue
        if furni_data.name in furni_list and furni_data.name not in duplicates:
            continue
        furni_destroy = furni_destroy_text(furni_data, items)

        groups = ""
        themes = ""
        for group in (data.groups or {}).values():
            if furni_data.id in (group.furniture or []):
                groups = group.name or ""
                themes = themes_data[group.theme_id or ""].name or ""
                break

        if groups == "":
            individual_furni.append(f"{{{{家具|{furni_data.name}}}}}")

        furni_info = furni_format.format(
            name=furni_data.name,
            id=furni_data.id,
            type=types[furni_data.type].name,
            subType=furni_sub_type_text(building_data, furni_data.sub_type),
            rarity=furni_data.rarity,
            comfort=furni_data.comfort,
            destroyObtain=furni_destroy,
            size=str(furni_data.width)
            + "×"
            + str(furni_data.depth)
            + "×"
            + str(furni_data.height),
            description=(furni_data.description or "").replace("\n", "<br>"),
            usage=furni_data.usage,
            obtainApproach=furni_data.obtain_approach,
            themes=themes,
            groups=groups,
        )

        if furni_data.name in duplicates:
            if themes == "":
                themes = "散件"
            page_name = furni_data.name + f"（{themes}）"
            if page_name in furni_list:
                continue
            furni_info = furni_info[:-2] + "|重指定=1\n}}"
        else:
            page_name = furni_data.name

        await wiki.edit(
            title=page_name, text=furni_info, createonly=True, summary="init"
        )
        # logger.info(furni_info)
        logger.info(f"Created: {page_name}.")

    if individual_furni != []:
        await wiki.edit(
            title="首页/新增单件",
            text="".join(individual_furni),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(''.join(individual_furni))
        logger.info("Updated: {}.".format("首页/新增单件"))


def theme_preview_pic(shop_client_table: ShopClientData, theme_id: str | None) -> str:
    """商店推荐位里该主题的总览图参数;没有对应推荐位时为空串。"""

    for shop_furni in shop_client_table.recommend_list or []:
        if shop_furni.template_type != "NORFURN":
            continue
        template_param = shop_furni.template_param
        furn_param = template_param.normal_furn_param if template_param else None
        if furn_param is None or furn_param.furn_pack_id != theme_id:
            continue
        group_list = shop_furni.group_list or []
        data_list = (group_list[0].data_list if group_list else None) or []
        if not data_list or data_list[0].param_1 is None:
            continue
        return "|总览图片=" + data_list[0].param_1
    return ""


async def create_themes(
    wiki: Wiki, building_data: BuildingData, shop_client_table: ShopClientData
) -> None:
    themes_list = await wiki.category("分类:家具主题")

    themes_info = """{{{{pathnav2|家具一览}}}}
==总览==
{{{{家具主题总览|{themesName}|{description}|主题图片={themeId}{previewPic}}}}}
==快速布置==
{{|class="wikitable" style="text-align:center; white-space:normal; display:table; width:500px;"
!width="60%"|家具
!width="20%"|数量
!width="20%"|家具氛围值{quickSetupFurni}
|-
!colspan="2"|总计
|{furniComfort}
|}}
{{|class="wikitable" style="text-align:center; white-space:normal; display:table; width:500px;"
!style="width:60%;"|主题
!style="width:20%;"|套件数量
!style="width:20%;"|氛围值{quickSetupGroups}
|-
!colspan="2"|总计
|{groupsComfort}
|}}
{{|class="wikitable" style="text-align:center; white-space:normal; display:table; width:500px;"
|width="80%"|家具氛围值
|width="20%"|{furniComfort}
|-
|width="80%"|主题氛围值
|width="20%"|{groupsComfort}
|-
!width="80%"|氛围值总计
|width="20%"|{totalComfort}
|}}
{refContent}==套件=={groupsContent}"""

    new_theme = []

    data = custom_data(building_data)
    furnitures = data.furnitures or {}
    for themes, themesData in (data.themes or {}).items():
        themesData.name = (themesData.name or "").strip()
        if themesData.name in themes_list:
            continue
        # if themesData['name'] != '神农祭庙会':
        #     continue

        groupsContent = ""
        quickSetupFurni = ""
        quickSetupGroups = ""
        refId = 1
        refFlag = False
        refContent = ""
        furniComfort = groupsComfort = 0
        quickSetupDict: dict[str, int] = {}

        for quickFurni in themesData.quick_setup or []:
            furniture_id = quickFurni.furniture_id or ""
            if furniture_id in quickSetupDict:
                quickSetupDict[furniture_id] += 1
            else:
                quickSetupDict[furniture_id] = 1

        for quickFurniId in quickSetupDict:
            quickFurniComfort = furnitures[quickFurniId].comfort
            quickFurniComfort = quickFurniComfort * min(6, quickSetupDict[quickFurniId])
            furniComfort += quickFurniComfort
            quickSetupFurni += (
                f"\n|-\n|[[{furnitures[quickFurniId].name}]]"
                f"\n|{quickSetupDict[quickFurniId]}\n|{quickFurniComfort}"
            )
            if quickSetupDict[quickFurniId] > 6:
                quickSetupFurni += (
                    f'<ref name=注"{refId}">相同家具只有前6件能够获得氛围</ref>'
                )
                refId += 1
                refFlag = True
        if refFlag:
            refContent = "<references />\n"

        for groups, groupsData in (data.groups or {}).items():
            if themes in groups:
                groupsContent += f"\n'''{groupsData.name}'''\n"
                groupsComfort += groupsData.comfort
                quickSetupGroups += (
                    f"\n|-\n|{groupsData.name}\n|{groupsData.count}"
                    f"\n|{groupsData.comfort}"
                )
                for groupFurni in groupsData.furniture or []:
                    if groupFurni not in furnitures:
                        continue
                    groupsContent += f"{{{{家具|{furnitures[groupFurni].name}}}}}"

        totalComfort = furniComfort + groupsComfort

        preview_pic = theme_preview_pic(shop_client_table, themesData.id)

        themesContent = themes_info.format(
            themesName=themesData.name.replace("/", ""),
            themeId=themesData.id,
            previewPic=preview_pic,
            description=themesData.desc,
            quickSetupFurni=quickSetupFurni,
            furniComfort=furniComfort,
            quickSetupGroups=quickSetupGroups,
            groupsComfort=groupsComfort,
            totalComfort=totalComfort,
            groupsContent=groupsContent,
            refContent=refContent,
        )

        new_theme.append(
            "{{{{家具主题|{name}}}}}".format(name=themesData.name.replace("/", ""))
        )

        await wiki.edit(
            title=themesData.name,
            text=themesContent,
            summary="init",
            createonly=True,
            bot=None,
            minor=True,
        )
        # logger.info(themesContent)
        logger.info(f"Created: {themesData.name}.")

    if new_theme != []:
        await wiki.edit(
            title="首页/新增主题",
            text=" ".join(new_theme),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(' '.join(new_theme))
        logger.info("Updated: {}.".format("首页/新增主题"))


@job
async def run(
    wiki: Wiki,
    building_data: Annotated[BuildingData, table("building_data")],
    item_table: ItemTable,
    shop_client_table: ShopClientTable,
) -> None:
    # 先算重名家具再建页,主题页里引用的家具名要和家具页一致
    duplicates = find_duplicates(building_data)
    await create_themes(wiki, building_data, shop_client_table)
    await create_furni(wiki, building_data, item_table, duplicates)


@job
async def update(
    wiki: Wiki,
    building_data: Annotated[BuildingData, table("building_data")],
    item_table: ItemTable,
) -> None:
    await update_furni(wiki, building_data, item_table, find_duplicates(building_data))
