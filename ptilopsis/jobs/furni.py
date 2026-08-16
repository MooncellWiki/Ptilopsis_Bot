from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job


def update_furni(wiki, building_data, item_table):
    for furni in building_data["customData"]["furnitures"]:
        furni_data = building_data["customData"]["furnitures"][furni]
        furni_data["name"] = furni_data["name"].strip()
        page_name = furni_data["name"]
        if page_name in duplicate_list:
            themes = ""
            for groupsId in building_data["customData"]["groups"]:
                groupsData = building_data["customData"]["groups"][groupsId]
                if furni_data["id"] in groupsData["furniture"]:
                    themes = building_data["customData"]["themes"][
                        groupsData["themeId"]
                    ]["name"]
                    break
            if themes == "":
                themes = "散件"
            page_name += f"（{themes}）"

        origin_text = wiki.read(page_name)

        num1 = origin_text.find("|描述=")
        num2 = origin_text.find("|", num1 + 4)
        new_text = (
            origin_text[:num1]
            + "|描述={}\n".format(furni_data["description"].replace("\n", "<br>"))
            + origin_text[num2:]
        )

        if furni_data["canBeDestroy"] == True:
            furni_destroy = "{{{{材料消耗|{name}|{number}}}}}".format(
                name=item_table["items"][furni_data["processedProductId"]][
                    "name"
                ].rstrip(),
                number=furni_data["processedProductCount"],
            )
        else:
            furni_destroy = "不可分解"

        num1 = origin_text.find("|类型=")
        num2 = origin_text.find("|描述=")
        if furni_data["subType"] in building_data["customData"]["subTypes"]:
            sub_type = "\n|子类型={}".format(
                building_data["customData"]["subTypes"][furni_data["subType"]]["name"]
            )
        else:
            sub_type = ""
        new_text = (
            new_text[:num1]
            + "|类型={type}{subType}\n|稀有度={rarity}\n|氛围={comfort}\n|分解获得={destroyObtain}\n|大小={size}\n".format(
                type=building_data["customData"]["types"][furni_data["type"]]["name"],
                subType=sub_type,
                rarity=furni_data["rarity"],
                comfort=furni_data["comfort"],
                destroyObtain=furni_destroy,
                size=str(furni_data["width"])
                + "×"
                + str(furni_data["depth"])
                + "×"
                + str(furni_data["height"]),
            )
            + new_text[num2:]
        )

        if origin_text != new_text:
            wiki.edit(title=page_name, text=new_text, summary="update")
            # logger.info(new_text)
            logger.info(f"Update: {page_name}.")
        else:
            logger.info(f"Same: {page_name}.")


def create_furni(wiki, building_data, item_table):
    furni_list = wiki.category("分类:家具")

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

    for furni in building_data["customData"]["furnitures"]:
        furni_data = building_data["customData"]["furnitures"][furni]
        furni_data["name"] = furni_data["name"].strip()
        if furni_data["name"] in ["taptap街机", "bilibili地毯"]:
            continue
        if (
            furni_data["name"] in furni_list
            and furni_data["name"] not in duplicate_list
        ):
            continue
        if furni_data["canBeDestroy"] == True:
            furni_destroy = "{{{{材料消耗|{name}|{number}}}}}".format(
                name=item_table["items"][furni_data["processedProductId"]][
                    "name"
                ].rstrip(),
                number=furni_data["processedProductCount"],
            )
        else:
            furni_destroy = "不可分解"

        groups = ""
        themes = ""
        for groupsId in building_data["customData"]["groups"]:
            groupsData = building_data["customData"]["groups"][groupsId]
            if furni_data["id"] in groupsData["furniture"]:
                groups = groupsData["name"]
                themes = building_data["customData"]["themes"][groupsData["themeId"]][
                    "name"
                ]
                break

        if groups == "":
            individual_furni.append("{{{{家具|{}}}}}".format(furni_data["name"]))

        if furni_data["subType"] in building_data["customData"]["subTypes"]:
            sub_type = "\n|子类型={}".format(
                building_data["customData"]["subTypes"][furni_data["subType"]]["name"]
            )
        else:
            sub_type = ""

        furni_info = furni_format.format(
            name=furni_data["name"],
            id=furni_data["id"],
            type=building_data["customData"]["types"][furni_data["type"]]["name"],
            subType=sub_type,
            rarity=furni_data["rarity"],
            comfort=furni_data["comfort"],
            destroyObtain=furni_destroy,
            size=str(furni_data["width"])
            + "×"
            + str(furni_data["depth"])
            + "×"
            + str(furni_data["height"]),
            description=furni_data["description"].replace("\n", "<br>"),
            usage=furni_data["usage"],
            obtainApproach=furni_data["obtainApproach"],
            themes=themes,
            groups=groups,
        )

        if furni_data["name"] in duplicate_list:
            if themes == "":
                themes = "散件"
            page_name = furni_data["name"] + f"（{themes}）"
            if page_name in furni_list:
                continue
            furni_info = furni_info[:-2] + "|重指定=1\n}}"
        else:
            page_name = furni_data["name"]

        wiki.edit(title=page_name, text=furni_info, createonly=True, summary="init")
        # logger.info(furni_info)
        logger.info(f"Created: {page_name}.")

    if individual_furni != []:
        wiki.edit(
            title="首页/新增单件",
            text="".join(individual_furni),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(''.join(individual_furni))
        logger.info("Updated: {}.".format("首页/新增单件"))


def create_themes(wiki, building_data, shop_client_table):
    themes_list = wiki.category("分类:家具主题")

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

    for themes in building_data["customData"]["themes"]:
        themesData = building_data["customData"]["themes"][themes]
        themesData["name"] = themesData["name"].strip()
        if themesData["name"] in themes_list:
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
        quickSetupDict = {}

        for quickFurni in themesData["quickSetup"]:
            if quickFurni["furnitureId"] in quickSetupDict:
                quickSetupDict[quickFurni["furnitureId"]] += 1
            else:
                quickSetupDict[quickFurni["furnitureId"]] = 1

        for quickFurniId in quickSetupDict:
            quickFurniComfort = building_data["customData"]["furnitures"][quickFurniId][
                "comfort"
            ]
            quickFurniComfort = quickFurniComfort * min(6, quickSetupDict[quickFurniId])
            furniComfort += quickFurniComfort
            quickSetupFurni += "\n|-\n|[[{name}]]\n|{count}\n|{comfort}".format(
                name=building_data["customData"]["furnitures"][quickFurniId]["name"],
                count=quickSetupDict[quickFurniId],
                comfort=quickFurniComfort,
            )
            if quickSetupDict[quickFurniId] > 6:
                quickSetupFurni += (
                    f'<ref name=注"{refId}">相同家具只有前6件能够获得氛围</ref>'
                )
                refId += 1
                refFlag = True
        if refFlag:
            refContent = "<references />\n"

        for groups in building_data["customData"]["groups"]:
            if themes in groups:
                groupsData = building_data["customData"]["groups"][groups]
                groupsContent += "\n'''{name}'''\n".format(name=groupsData["name"])
                groupsComfort += groupsData["comfort"]
                quickSetupGroups += "\n|-\n|{name}\n|{count}\n|{comfort}".format(
                    name=groupsData["name"],
                    count=groupsData["count"],
                    comfort=groupsData["comfort"],
                )
                for groupFurni in groupsData["furniture"]:
                    if groupFurni not in building_data["customData"]["furnitures"]:
                        continue
                    groupsContent += "{{{{家具|{name}}}}}".format(
                        name=building_data["customData"]["furnitures"][groupFurni][
                            "name"
                        ]
                    )

        totalComfort = furniComfort + groupsComfort

        preview_pic = ""
        for shop_furni in filter(
            lambda x: x["templateType"] == "NORFURN", shop_client_table["recommendList"]
        ):
            try:
                if (
                    shop_furni["templateParam"]["normalFurnParam"]["furnPackId"]
                    == building_data["customData"]["themes"][themes]["id"]
                ):
                    preview_pic = (
                        "|总览图片="
                        + shop_furni["groupList"][0]["dataList"][0]["param1"]
                    )
                    break
            except:
                continue

        themesContent = themes_info.format(
            themesName=building_data["customData"]["themes"][themes]["name"].replace(
                "/", ""
            ),
            themeId=building_data["customData"]["themes"][themes]["id"],
            previewPic=preview_pic,
            description=building_data["customData"]["themes"][themes]["desc"],
            quickSetupFurni=quickSetupFurni,
            furniComfort=furniComfort,
            quickSetupGroups=quickSetupGroups,
            groupsComfort=groupsComfort,
            totalComfort=totalComfort,
            groupsContent=groupsContent,
            refContent=refContent,
        )

        new_theme.append(
            "{{{{家具主题|{name}}}}}".format(name=themesData["name"].replace("/", ""))
        )

        wiki.edit(
            title=themesData["name"],
            text=themesContent,
            summary="init",
            createonly=True,
            bot=None,
            minor=True,
        )
        # logger.info(themesContent)
        logger.info("Created: {}.".format(themesData["name"]))

    if new_theme != []:
        wiki.edit(
            title="首页/新增主题",
            text=" ".join(new_theme),
            summary="update",
            bot=None,
            minor=True,
        )
        # logger.info(' '.join(new_theme))
        logger.info("Updated: {}.".format("首页/新增主题"))


duplicate_list = []


@job
def run(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    item_table = ctx.getgd("excel/item_table.json")
    shop_client_table = ctx.getgd("excel/shop_client_table.json")

    check_duplicate(ctx)
    create_themes(ctx.wiki, building_data, shop_client_table)
    create_furni(ctx.wiki, building_data, item_table)


@job
def update(ctx: JobContext) -> None:
    building_data = ctx.getgd("excel/building_data.json")
    item_table = ctx.getgd("excel/item_table.json")

    update_furni(ctx.wiki, building_data, item_table)


def check_duplicate(ctx: JobContext):
    building_data = ctx.getgd("excel/building_data.json")

    furni_dict = {}
    furnitures = building_data["customData"]["furnitures"]
    for furni in furnitures.values():
        if furni["name"] not in furni_dict:
            furni_dict[furni["name"]] = []
        furni_dict[furni["name"]].append(furni["id"])
    for name, f_list in furni_dict.items():
        if len(f_list) > 1:
            duplicate_list.append(name)
