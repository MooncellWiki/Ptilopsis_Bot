import re
from typing import Annotated, Any

from ptilopsis.gamedata.character_table import CharacterData
from ptilopsis.gamedata.skin_table import (
    CharSkinData,
    CharSkinDataDisplaySkin,
    SkinTable,
)
from ptilopsis.jobs.params import table
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


def display_skin(skin: CharSkinData) -> CharSkinDataDisplaySkin:
    """皮肤的展示数据(名字、画师、介绍等);每个皮肤都有,缺失视为数据异常。"""
    if skin.display_skin is None:
        raise ValueError(f"皮肤 {skin.skin_id} 缺少 displaySkin")
    return skin.display_skin


def _phase0_drawer(skin_table: SkinTable, char_id: str) -> str | None:
    """精英 0 立绘的画师(逗号连接);没有内建立绘记录(升变阿米娅)或缺画师时为 None。"""
    skin_id = (skin_table.buildin_evolve_map or {}).get(char_id, {}).get(0)
    skin = (skin_table.char_skins or {}).get(skin_id) if skin_id is not None else None
    if skin is None or skin.display_skin is None:
        return None
    if skin.display_skin.drawer_list is None:
        return None
    return ",".join(skin.display_skin.drawer_list)


def _skin_owner(
    skin: CharSkinData, character_table: dict[str, CharacterData]
) -> tuple[str, str | None]:
    """皮肤归属的干员 id 与页面名。

    升变阿米娅的皮肤挂在 char_002_amiya 下,按 tmplId 区分。
    """
    if skin.char_id == "char_002_amiya" and skin.tmpl_id == "char_1001_amiya2":
        return "char_1001_amiya2", "阿米娅(近卫)"
    if skin.char_id == "char_002_amiya" and skin.tmpl_id == "char_1037_amiya3":
        return "char_1037_amiya3", "阿米娅(医疗)"
    char_id = skin.char_id or ""
    return char_id, character_table[char_id].name


def get_skin_info(char_key: str, skin_table: SkinTable, drawer: str) -> tuple[str, int]:
    char_skins = skin_table.char_skins or {}
    basic_info = ""
    # 常规皮肤description
    if char_key == "char_1001_amiya2":
        patch_map = skin_table.buildin_patch_map or {}
        phase_skin = char_skins[patch_map["char_002_amiya"][char_key]]
        phase_desc = (display_skin(phase_skin).content or "").replace("\n", "<br/>")
        basic_info += f"\n|精英2介绍={phase_desc}"
    else:
        evolve_map = (skin_table.buildin_evolve_map or {})[char_key]
        for phase_no in evolve_map:
            phase_desc = display_skin(char_skins[evolve_map[phase_no]]).content
            phase_drawer_list = display_skin(char_skins[evolve_map[0]]).drawer_list
            if phase_drawer_list is not None:
                phase_drawer = ",".join(phase_drawer_list)
            else:
                phase_drawer = ""
            phase_desc = (
                phase_desc.replace("\n", "<br/>") if phase_desc is not None else ""
            )
            basic_info += f"\n|精英{phase_no}介绍={phase_desc}"
            if phase_drawer != drawer:
                basic_info += f"\n|精英{phase_no}画师={phase_drawer}"
    # 时装
    skin_counter = 1
    # 升变阿米娅的时装挂在 char_002_amiya 下,按 tmplId 区分
    if char_key == "char_002_amiya" or char_key == "char_1001_amiya2":
        owner_id, tmpl_id = "char_002_amiya", char_key
    else:
        owner_id, tmpl_id = char_key, None

    def skin_filter(x: CharSkinData) -> bool:
        return (
            x.char_id == owner_id
            and (tmpl_id is None or x.tmpl_id == tmpl_id)
            and display_skin(x).skin_group_name != "默认服装"
        )

    def order_func(x: CharSkinData) -> int:
        return display_skin(x).on_year * 100 + display_skin(x).on_period

    for skin_content in sorted(
        filter(skin_filter, char_skins.values()), key=order_func
    ):
        ds = display_skin(skin_content)
        basic_info += f"\n|时装{skin_counter}名称={ds.skin_name}"
        if ds.drawer_list is not None:
            skin_drawer = ",".join(ds.drawer_list)
        else:
            skin_drawer = ""
        if skin_drawer != drawer:
            basic_info += f"\n|时装{skin_counter}画师={skin_drawer}"
        basic_info += f"\n|时装{skin_counter}系列={ds.skin_group_name}"
        skin_color = (ds.color_list or [])[0]
        if not skin_color.startswith("#") and len(skin_color) == 6:
            skin_color = "#" + skin_color
        basic_info += f"\n|时装{skin_counter}颜色={skin_color}"
        skin_desc = re.sub(r"<color name=[^>]*>", "", ds.content or "")
        skin_desc = (
            skin_desc.replace("</color>", "").replace("\r", "").replace("\n", "<br/>")
        )
        basic_info += f"\n|时装{skin_counter}介绍={skin_desc}"
        skin_counter += 1
    basic_info += "\n<!--"
    return basic_info, skin_counter - 1


async def update_skin(
    wiki: Wiki,
    character_table: dict[str, CharacterData],
    skin_table: SkinTable,
    skin_list: list[str],
) -> None:
    char_skins = skin_table.char_skins or {}
    skin_data: list[str] = []
    name_to_id = {(v.name or "").strip(): k for k, v in character_table.items()}
    name_to_id["阿米娅(近卫)"] = "char_1001_amiya2"
    name_to_id["阿米娅(医疗)"] = "char_1037_amiya3"
    # 干员页面一次批量读完;页面不存在时和原来的 wiki.read 一样抛 KeyError
    origin_texts = await wiki.read_many(skin_list)
    for skin_char_name in skin_list:
        skin_char_id = name_to_id[skin_char_name]

        origin_text = origin_texts[skin_char_name]
        if skin_char_id in ["char_1001_amiya2", "char_1037_amiya3"]:
            num1 = origin_text.find("\n|精英2介绍")
        else:
            num1 = origin_text.find("\n|精英0介绍")
        num2 = origin_text.find("上方为自动更新部分，您的修改可能会被覆盖")
        origin_drawer = _phase0_drawer(skin_table, skin_char_id)
        if origin_drawer is None:
            if skin_char_id in ["char_1001_amiya2", "char_1037_amiya3"]:
                patch_map = skin_table.buildin_patch_map or {}
                patch_skin = char_skins[patch_map["char_002_amiya"]["char_1001_amiya2"]]
                origin_drawer = ",".join(display_skin(patch_skin).drawer_list or [])
            else:
                origin_drawer = ""
        skin_info, count = get_skin_info(skin_char_id, skin_table, origin_drawer)
        # new_text = origin_text[:num1] + skin_info + '\n' + origin_text[num2:]
        new_text = origin_text[:num1] + skin_info + origin_text[num2:]

        if origin_text != new_text:
            skin_data.append(f"1={skin_char_name}:skin={count}")
            await wiki.edit(
                title=skin_char_name,
                text=new_text,
                summary="update",
                bot=None,
                minor=True,
            )
            # logger.info(new_text)
            logger.info(f"Updated: {skin_char_name}.")
        else:
            logger.info(f"Same: {skin_char_name}.")

    if skin_data != [] and skin_list is not None:
        await wiki.edit(
            title="首页/亮点干员/新增皮肤/数据",
            text=",".join(skin_data),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(','.join(skin_data))
        logger.info("Updated: {}.".format("首页/亮点干员/新增皮肤/数据"))


# def update_randomFig(wiki, character_table, skin_table):
#     skin_list = {}
#     fin = '<choose uncached before="[[文件:" after="|右|555px]]">'
#     for skin_key in skin_table['charSkins']:
#         skin_content = skin_table['charSkins'][skin_key]
#         if skin_content['displaySkin']['skinGroupSortIndex'] in [-50, -30, 0, 1]:
#             continue
#         if skin_content['displaySkin']['skinGroupName'] == '默认服装':
#             fin += '\n<option>立绘 {name} 2.png|link={name}</option>'.format(
#                 name = character_table[skin_content['charId']]['name']
#             )
#         else:
#             char_name = character_table[skin_content['charId']]['name']
#             if char_name in skin_list:
#                 skin_list[char_name] += 1
#             else:
#                 skin_list[char_name] = 1
#
#     for char in skin_list:
#         for skin_num in range(skin_list[char]):
#             fin += '\n<option>立绘 {name} skin{id}.png|link={name}</option>'.format(
#                 name = char,
#                 id = skin_num + 1
#             )
#     fin += '\n</choose>'
#
#     wiki.edit(
#         title = '模板:随机干员立绘',
#         text = fin,
#         summary = 'update'
#     )
#     # logger.info(fin)
#     logger.info('Updated: {}.'.format('模板:随机干员立绘'))


# def update_skin_handbook(wiki, character_table, skin_table):
#     skin_format = '''{{{{锚点|{skinKey}}}}}
# \'\'\'{name}\'\'\'
# {{{{干员时装
# |干员名={name}
# |皮肤序号={skinNo}
# |时装名={skinName}
# |画师={drawerName}
# |时装组名称={skinGroupName}
# |内容={content}
# |获得途径={obtainApproach}
#
# |dialog={dialog}
# |usage={usage}
# |desc={description}
# }}}}'''
#
#     skin_char = {}
#     max_index = 0
#     for skin_key in skin_table['charSkins']:
#         if (skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex']
#                 > max_index):
#             max_index = (
#                 skin_table['charSkins'][skin_key]['displaySkin']
#                 ['skinGroupSortIndex'])
#
#     skin_group_order = ['' for x in range(max_index)]
#     skin_group_list1 = {}
#     skin_group_list2 = {}
#
#     for skin_key in skin_table['charSkins']:
#         skin_info = skin_table['charSkins'][skin_key]
#         if (skin_info['displaySkin']['skinGroupName'] != '默认服装'
#                 and 'token' not in skin_key):
#             sort_index = skin_info['displaySkin']['skinGroupSortIndex']
#             if skin_group_order[sort_index - 1] == '':
#                 skin_group_order[sort_index - 1] = skin_info['displaySkin'][
#                     'skinGroupName']
#                 skin_group_list1[skin_info['displaySkin']['skinGroupName']] = []
#                 skin_group_list2[skin_info['displaySkin']['skinGroupName']] = []
#
#             if skin_table['charSkins'][skin_key]['charId'] not in skin_char:
#                 skin_char[skin_table['charSkins'][skin_key]['charId']] = 0
#
#             skin_char[skin_info['charId']] += 1
#             skin_text1 = skin_format.format(
#                 skinKey = skin_info['portraitId'].replace('#', ''),
#                 name = character_table[skin_info['charId']]['name'],
#                 skinName = skin_info['displaySkin']['skinName'],
#                 skinNo = skin_char[skin_info['charId']],
#                 modelName = skin_info['displaySkin']['modelName'],
#                 drawerName = skin_info['displaySkin']['drawerName'],
#                 skinGroupId = skin_info['displaySkin']['skinGroupId'],
#                 skinGroupName = skin_info['displaySkin']['skinGroupName'],
#                 content = skin_table['charSkins'][skin_key]['displaySkin']['content']
#                     .replace('<color name=#ffffff>', '').replace('</color>', '')
#                     .replace('\r', '').replace('\n', '<br/>'),
#                 dialog = skin_info['displaySkin']['dialog'],
#                 usage = skin_info['displaySkin']['usage'],
#                 description = skin_info['displaySkin']['description'],
#                 obtainApproach = skin_info['displaySkin']['obtainApproach']
#             )
#             skin_text2 = '{{{{皮肤头像|{name}|90px|{skinNo}|link=#{skinKey}}}}}'
#             skin_text2 = skin_text2.format(
#                 name = character_table[skin_info['charId']]['name'],
#                 skinNo = skin_char[skin_info['charId']],
#                 skinKey = skin_info['portraitId'].replace('#', '')
#             )
#             group_name = skin_info['displaySkin']['skinGroupName']
#             skin_group_list1[group_name].append(skin_text1)
#             skin_group_list2[group_name].append(skin_text2)
#
#     handbook = ('__NOTOC__\n{|class="wikitable" '
#                 'style="width:1000px; white-space:normal; display:table;"'
#                 '\n!皮肤组\n!干员')
#     for group_name in skin_group_order:
#         if group_name != '':
#             handbook += '\n|-\n|\'\'\'{groupName}\'\'\'\n|'.format(
#                 groupName = group_name
#             ) + ''.join(skin_group_list2[group_name])
#     handbook += '\n|}'
#     for group_name in skin_group_order:
#         if group_name != '':
#             handbook += '\n=={}==\n'.format(group_name)
#             handbook += '\n'.join(skin_group_list1[group_name])
#
#     wiki.edit(
#         title = '用户:Seniorious/skins',
#         text = handbook,
#         summary = 'update'
#     )
#     # logger.info(handbook)
#     logger.info('Updated: {}.'.format('用户:Seniorious/skins'))


async def update_outfit_gallery(
    wiki: Wiki, skin_table: SkinTable, character_table: dict[str, CharacterData]
) -> None:
    skin_half_format = """{{{{{{{{时装回廊/半身像
|干员名={char}
|时装序号={{skin_id}}{tag}
|干员外文名={appellation}
|时装名={skin_name}{anchor}
|时装系列={skin_series}
}}}}}}}}"""

    brand_list: dict[str | None, str] = {}
    for brand in (skin_table.brand_list or {}).values():
        for group in brand.group_list or []:
            brand_list[group.skin_group_id] = (
                (brand.brand_name or "").replace("/", "-").rstrip()
            )

    skin_dict: dict[int, dict[str, Any]] = {}
    char_count: dict[str, int] = {}
    for skin_key, skin_info in (skin_table.char_skins or {}).items():
        ds = display_skin(skin_info)
        if ds.skin_group_name != "默认服装" and "token" not in skin_key:
            appellation = ds.model_name or ""
            if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(
                65, 91
            ):
                appellation = appellation.upper()
            if ds.display_tag_id is not None:
                tag = f"\n|时装注释={ds.display_tag_id}"
            else:
                tag = ""
            skin_char_id, skin_char_name = _skin_owner(skin_info, character_table)
            if skin_char_id not in char_count:
                char_count[skin_char_id] = 0
            char_count[skin_char_id] += 1
            skin_name = (ds.skin_name or "").rstrip()
            if " " in skin_name:
                anchor = "\n|锚点={}".format(skin_name.replace(" ", "_"))
            else:
                anchor = ""
            skin_half_desc = skin_half_format.format(
                char=skin_char_name,
                tag=tag,
                appellation=appellation,
                skin_name=skin_name,
                anchor=anchor,
                skin_series=brand_list[ds.skin_group_id],
            )
            order = ds.on_year * 100 + ds.on_period
            if order not in skin_dict:
                skin_dict[order] = {
                    "title": f"Y-{ds.on_year} {ds.on_period:0>2d}",
                    "content": {},
                }
            sort_key: float = ds.get_time + ds.sort_id
            while sort_key in skin_dict[order]["content"]:
                sort_key += 0.1
                logger.info("时装回廊 sort_key 重复")
            skin_dict[order]["content"][sort_key] = (skin_char_id, skin_half_desc)
            # if skin_key != "char_123_fang@winter#1":
            #     skin_dict[order]['content'][skin_info['displaySkin']['sortId']] = (
            #         skin_char_id, skin_half_desc)
            # else:
            #     sort_id = skin_info['displaySkin']['sortId'] - 4
            #     skin_dict[order]['content'][sort_id] = (skin_char_id, skin_half_desc)

    skin_dict_sorted = [skin_dict[k] for k in sorted(skin_dict.keys(), reverse=True)]

    fin = ""
    for month in skin_dict_sorted:
        fin += "==={}===\n".format(month["title"])
        for desc_key in sorted(month["content"].keys()):
            desc = month["content"][desc_key]
            fin += desc[1].format(skin_id=char_count[desc[0]])
            char_count[desc[0]] -= 1
        fin += "\n"
    fin = (
        '{{#Widget:Garansandbox/brandbtn}}<div class="contentcontainer">'
        '<div class="halfimgcontainer">\n__NOTOC__\n'
        + fin
        + '</div><div class="brandbtncontainer"><div class="brandbtncontroler">'
        "{{#Widget:Brandbtn}}</div></div></div>"
    )

    await wiki.edit(title="模板:时装回廊", text=fin, summary="update")
    # logger.info(fin)
    logger.info("Updated: {}.".format("模板:时装回廊"))


async def update_outfit_brand(
    wiki: Wiki, skin_table: SkinTable, character_table: dict[str, CharacterData]
) -> None:
    skin_half_format = """{{{{时装回廊/半身像
|干员名={char}
|时装序号={skin_id}{tag}
|干员外文名={appellation}
|时装名={skin_name}{anchor}
|时装系列={skin_brand}
}}}}"""

    skin_format = """
{anchor}=={skinName}==
{{{{干员时装
|干员名={name}
|皮肤序号={skinNo}
|时装名={skinName}
|画师={drawerName}
|时装组名称={skinGroupName}
|内容={content}
|获得途径={obtainApproach}

|dialog={dialog}
|usage={usage}
|desc={description}
}}}}"""

    brand_format = """__NOTOC__
{{{{时装回廊/轮播{pic}
|名称={brand}
|简介={brand_desc}
}}}}
<div class="centercontainer"><div class="centercontroler">
{half_content}</div></div>{detail_content}"""

    skin_list: list[CharSkinData] = []
    for skin_key, skin_info in (skin_table.char_skins or {}).items():
        if display_skin(skin_info).skin_group_name == "默认服装" or "token" in skin_key:
            continue
        skin_list.append(skin_info)
    skin_list.sort(key=lambda x: display_skin(x).get_time + display_skin(x).sort_id)

    brand_list: dict[str | None, str] = {}
    skin_dict: dict[str, dict[str, Any]] = {}
    for v in sorted((skin_table.brand_list or {}).values(), key=lambda x: x.sort_id):
        brand_name = (v.brand_name or "").replace("/", "-").rstrip()
        skin_dict[brand_name] = {
            "brandName": v.brand_name,
            "description": (v.description or "").replace("\n", "<br/>"),
            "kvImgNum": len(v.kv_img_id_list or []),
            "half_content": "",
            "detail_content": {},
        }
        for group in v.group_list or []:
            brand_list[group.skin_group_id] = brand_name

    char_count: dict[str, int] = {}
    for skin_info in skin_list:
        ds = display_skin(skin_info)
        appellation = ds.model_name or ""
        if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(
            65, 91
        ):
            appellation = appellation.upper()
        if ds.display_tag_id is not None:
            tag = f"\n|时装注释={ds.display_tag_id}"
        else:
            tag = ""
        skin_char_id, skin_char_name = _skin_owner(skin_info, character_table)
        if skin_char_id not in char_count:
            char_count[skin_char_id] = 0
        char_count[skin_char_id] += 1
        skin_name = (ds.skin_name or "").rstrip()
        if " " in skin_name:
            anchor = "\n|锚点={}".format(skin_name.replace(" ", "_"))
        else:
            anchor = ""
        skin_brand = brand_list[ds.skin_group_id]
        skin_half_desc = skin_half_format.format(
            char=skin_char_name,
            tag=tag,
            appellation=appellation,
            skin_name=skin_name,
            skin_id=char_count[skin_char_id],
            anchor=anchor,
            skin_brand=skin_brand,
        )
        skin_dict[skin_brand]["half_content"] += skin_half_desc

        content_desc = re.sub(r"<color name=[^>]*>", "", ds.content or "")
        content_desc = (
            content_desc.replace("</color>", "")
            .replace("\r", "")
            .replace("\n", "<br/>")
        )

        skin_detail_desc = skin_format.format(
            anchor="{{{{锚点|{}}}}}\n".format(skin_name.replace(" ", "_"))
            if " " in skin_name
            else "",
            name=skin_char_name,
            skinName=skin_name,
            skinNo=char_count[skin_char_id],
            drawerName=",".join(ds.drawer_list or []),
            skinGroupName=(ds.skin_group_name or "").rstrip(),
            content=content_desc,
            obtainApproach=ds.obtain_approach,
            dialog=ds.dialog,
            usage=ds.usage,
            description=ds.description,
        )
        skin_dict[skin_brand]["detail_content"][skin_name] = skin_detail_desc

    # 品牌页面一次批量读完;不存在的页面不在结果里,下面按 KeyError 走整页重建
    brand_pages = await wiki.read_many("时装回廊/" + brand for brand in skin_dict)
    for brand in skin_dict:
        pic = ""
        detail = ""
        old_content = ""
        flag_new = False

        try:
            old_content = brand_pages["时装回廊/" + brand]

            # range不+1了, 有一张挪出来变default
            result = re.search(r"\|default=([\s\S]+?)\n\|", old_content)
            if result:
                pic += f"\n|default={result.group(1).rstrip()}"
            else:
                pic += "\n|default="
            for i in range(skin_dict[brand]["kvImgNum"]):
                result = re.search(rf"\|图{i + 1}=([\s\S]*?)\n\|", old_content)
                if result:
                    pic += f"\n|图{i + 1}={result.group(1).rstrip()}"
                else:
                    pic += f"\n|图{i + 1}="

            for skin_name in skin_dict[brand]["detail_content"]:
                origin_detail = skin_dict[brand]["detail_content"][skin_name]
                result = re.search(
                    rf"=={skin_name}==([\s\S]+?)\n" + r"\}\}", old_content
                )
                if result:
                    text_part = result.group(1).rstrip()
                    result2 = re.search(r"\|获得途径([\s\S]+?)\|dialog", text_part)
                    if result2:
                        result3 = re.search(
                            r"\|获得途径([\s\S]+?)\|dialog", origin_detail
                        )
                        if result3 is None:
                            # 新生成的详情里一定有获得途径;没有就和旧代码一样
                            # 让外层 except 走"整页重建"的分支
                            raise ValueError(f"{skin_name} 的详情缺少获得途径")
                        origin_detail = origin_detail.replace(
                            result3.group(1).rstrip(), result2.group(1).rstrip()
                        )
                    else:
                        logger.info(skin_name, "获取方式 未匹配")
                else:
                    logger.info(skin_name, "detail 未匹配")
                detail += origin_detail
            flag_new = False
        except Exception:
            # range不+1了, 有一张挪出来变default
            pic = "\n|default="
            pic += "".join(
                [f"\n|图{i + 1}=" for i in range(skin_dict[brand]["kvImgNum"])]
            )
            for s in skin_dict[brand]["detail_content"]:
                detail += skin_dict[brand]["detail_content"][s]
            flag_new = True

        content = brand_format.format(
            pic=pic,
            brand=brand,
            brand_desc=skin_dict[brand]["description"],
            half_content=skin_dict[brand]["half_content"],
            detail_content=detail,
        )
        if content != old_content:
            await wiki.edit(
                title="时装回廊/" + brand,
                text=content,
                summary="init" if flag_new else "update",
            )
            # logger.info(content)
            if flag_new:
                logger.info("Created: {}.".format("时装回廊/" + brand))
            else:
                logger.info("Updated: {}.".format("时装回廊/" + brand))


async def update_logo_link(wiki: Wiki, skin_table: SkinTable) -> None:
    logo_set = {
        name
        for s in (skin_table.char_skins or {}).values()
        if (name := display_skin(s).skin_group_name) is not None
    }
    logo_set.discard("默认服装")
    for logo in logo_set:
        if "/" in logo:
            link_title = f"文件:Skin logo {logo}.png"
            x = logo.find("/")
            content = f"#redirect [[文件:Skin logo {logo[:x]}.png]]"
            await wiki.edit(
                title=link_title,
                text=content,
                summary="redirect skin logo",
                createonly=True,
            )
            # logger.info(link_title, content)


@job
async def run(
    wiki: Wiki,
    character_table: Annotated[dict[str, CharacterData], table("character_table")],
    skin_table: Annotated[SkinTable, table("skin_table")],
) -> None:
    gallery = await wiki.read("模板:时装回廊")
    old_skin: list[str] = []
    result = re.findall(r"{{时装回廊/半身像\n([\s\S]*?)\n}}", gallery)
    for skin in result:
        r = re.search(r"\|干员名=([^\n]+?)\n[\s\S]*?\|时装名=([^\n]+?)\n", skin)
        if r is None:
            raise ValueError(f"模板:时装回廊 里有无法解析的半身像:{skin!r}")
        char_name, skin_name = r.group(1), r.group(2)
        old_skin.append(f"{char_name} {skin_name}")
    cid_list = {k: (v.name or "").strip() for k, v in character_table.items()}
    cid_list["char_1001_amiya2"] = "阿米娅(近卫)"
    cid_list["char_1037_amiya3"] = "阿米娅(医疗)"
    skin_list: list[str] = []
    for skin_key, skin_info in (skin_table.char_skins or {}).items():
        ds = display_skin(skin_info)
        if ds.skin_group_name == "默认服装" or "token" in skin_key:
            continue
        skin_char_key, _ = _skin_owner(skin_info, character_table)
        k = f"{cid_list[skin_char_key]} {(ds.skin_name or '').strip()}"
        if k not in old_skin:
            skin_list.append(cid_list[skin_char_key])
            logger.info(f"新时装：{k}")
    # skin_list = ['阿米娅(近卫)']
    if skin_list is not None:
        await update_skin(wiki, character_table, skin_table, skin_list)

    # update_randomFig(wiki, character_table, skin_table)
    # update_skin_handbook(wiki, character_table, skin_table)
    await update_outfit_gallery(wiki, skin_table, character_table)
    await update_outfit_brand(wiki, skin_table, character_table)
    await update_logo_link(wiki, skin_table)
