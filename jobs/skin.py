import re

from utils.job import Job


def get_skin_info(char_key, skin_table, drawer):
    basic_info = ""
    # 常规皮肤description
    if char_key == "char_1001_amiya2":
        phase_desc = skin_table["charSkins"][
            skin_table["buildinPatchMap"]["char_002_amiya"][char_key]
        ]["displaySkin"]["content"]
        phase_desc = phase_desc.replace("\n", "<br/>")
        basic_info += f"\n|精英2介绍={phase_desc}"
    else:
        for phase_no in skin_table["buildinEvolveMap"][char_key]:
            phase_desc = skin_table["charSkins"][
                skin_table["buildinEvolveMap"][char_key][phase_no]
            ]["displaySkin"]["content"]
            phase_drawer_list = skin_table["charSkins"][
                skin_table["buildinEvolveMap"][char_key]["0"]
            ]["displaySkin"]["drawerList"]
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
    skin_filter = lambda x: (
        x["charId"] == char_key and x["displaySkin"]["skinGroupName"] != "默认服装"
    )
    if char_key == "char_002_amiya" or char_key == "char_1001_amiya2":
        skin_filter = lambda x: (
            x["charId"] == "char_002_amiya"
            and x["tmplId"] == char_key
            and x["displaySkin"]["skinGroupName"] != "默认服装"
        )
    order_func = lambda x: (
        x["displaySkin"]["onYear"] * 100 + x["displaySkin"]["onPeriod"]
    )
    for skin_content in sorted(
        filter(skin_filter, skin_table["charSkins"].values()), key=order_func
    ):
        basic_info += (
            f"\n|时装{skin_counter}名称={skin_content['displaySkin']['skinName']}"
        )
        if skin_content["displaySkin"]["drawerList"] is not None:
            skin_drawer = ",".join(skin_content["displaySkin"]["drawerList"])
        else:
            skin_drawer = ""
        if skin_drawer != drawer:
            basic_info += f"\n|时装{skin_counter}画师={skin_drawer}"
        basic_info += (
            f"\n|时装{skin_counter}系列={skin_content['displaySkin']['skinGroupName']}"
        )
        skin_color = skin_content["displaySkin"]["colorList"][0]
        if not skin_color.startswith("#") and len(skin_color) == 6:
            skin_color = "#" + skin_color
        basic_info += f"\n|时装{skin_counter}颜色={skin_color}"
        skin_desc = re.sub(
            r"<color name=[^>]*>", "", skin_content["displaySkin"]["content"]
        )
        skin_desc = (
            skin_desc.replace("</color>", "").replace("\r", "").replace("\n", "<br/>")
        )
        basic_info += f"\n|时装{skin_counter}介绍={skin_desc}"
        skin_counter += 1
    basic_info += "\n<!--"
    return basic_info, skin_counter - 1


def update_skin(wiki, character_table, skin_table, skin_list):
    skin_data = []
    name_to_id = {v["name"].strip(): k for k, v in character_table.items()}
    name_to_id["阿米娅(近卫)"] = "char_1001_amiya2"
    name_to_id["阿米娅(医疗)"] = "char_1037_amiya3"
    for skin_char_name in skin_list:
        skin_char_id = name_to_id[skin_char_name]

        origin_text = wiki.read(skin_char_name)
        if skin_char_id in ["char_1001_amiya2", "char_1037_amiya3"]:
            num1 = origin_text.find("\n|精英2介绍")
        else:
            num1 = origin_text.find("\n|精英0介绍")
        num2 = origin_text.find("上方为自动更新部分，您的修改可能会被覆盖")
        try:
            origin_drawer = ",".join(
                skin_table["charSkins"][
                    skin_table["buildinEvolveMap"][skin_char_id]["0"]
                ]["displaySkin"]["drawerList"]
            )
        except:
            if skin_char_id in ["char_1001_amiya2", "char_1037_amiya3"]:
                origin_drawer = ",".join(
                    skin_table["charSkins"][
                        skin_table["buildinPatchMap"]["char_002_amiya"][
                            "char_1001_amiya2"
                        ]
                    ]["displaySkin"]["drawerList"]
                )
            else:
                origin_drawer = ""
        skin_info, count = get_skin_info(skin_char_id, skin_table, origin_drawer)
        # new_text = origin_text[:num1] + skin_info + '\n' + origin_text[num2:]
        new_text = origin_text[:num1] + skin_info + origin_text[num2:]

        if origin_text != new_text:
            skin_data.append(f"1={skin_char_name}:skin={count}")
            wiki.edit(
                title=skin_char_name,
                text=new_text,
                summary="update",
                bot=None,
                minor=True,
            )
            # print(new_text)
            print(f"Updated: {skin_char_name}.")
        else:
            print(f"Same: {skin_char_name}.")

    if skin_data != [] and skin_list != None:
        wiki.edit(
            title="首页/亮点干员/新增皮肤/数据",
            text=",".join(skin_data),
            summary="update",
            bot=None,
            minor=True,
        )
        # print(','.join(skin_data))
        print("Updated: {}.".format("首页/亮点干员/新增皮肤/数据"))


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
#     # print(fin)
#     print('Updated: {}.'.format('模板:随机干员立绘'))


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
#         if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex'] > max_index:
#             max_index = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex']
#
#     skin_group_order = ['' for x in range(max_index)]
#     skin_group_list1 = {}
#     skin_group_list2 = {}
#
#     for skin_key in skin_table['charSkins']:
#         skin_info = skin_table['charSkins'][skin_key]
#         if skin_info['displaySkin']['skinGroupName'] != '默认服装' and 'token' not in skin_key:
#             if skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] == '':
#                 skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] = skin_info['displaySkin'][
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
#                 content = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>',
#                     '').replace('</color>', '').replace('\r', '').replace('\n', '<br/>'),
#                 dialog = skin_info['displaySkin']['dialog'],
#                 usage = skin_info['displaySkin']['usage'],
#                 description = skin_info['displaySkin']['description'],
#                 obtainApproach = skin_info['displaySkin']['obtainApproach']
#             )
#             skin_text2 = '{{{{皮肤头像|{name}|90px|{skinNo}|link=#{skinKey}}}}}'.format(
#                 name = character_table[skin_info['charId']]['name'],
#                 skinNo = skin_char[skin_info['charId']],
#                 skinKey = skin_info['portraitId'].replace('#', '')
#             )
#             skin_group_list1[skin_info['displaySkin']['skinGroupName']].append(skin_text1)
#             skin_group_list2[skin_info['displaySkin']['skinGroupName']].append(skin_text2)
#
#     handbook = '__NOTOC__\n{|class="wikitable" style="width:1000px; white-space:normal; display:table;"\n!皮肤组\n!干员'
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
#     # print(handbook)
#     print('Updated: {}.'.format('用户:Seniorious/skins'))


def update_outfit_gallery(wiki, skin_table, character_table):
    skin_half_format = """{{{{{{{{时装回廊/半身像
|干员名={char}
|时装序号={{skin_id}}{tag}
|干员外文名={appellation}
|时装名={skin_name}{anchor}
|时装系列={skin_series}
}}}}}}}}"""

    brand_list = {}
    for brand in skin_table["brandList"]:
        for group in skin_table["brandList"][brand]["groupList"]:
            brand_list[group["skinGroupId"]] = (
                skin_table["brandList"][brand]["brandName"].replace("/", "-").rstrip()
            )

    skin_dict = {}
    char_count = {}
    for skin_key in skin_table["charSkins"]:
        skin_info = skin_table["charSkins"][skin_key]
        if (
            skin_info["displaySkin"]["skinGroupName"] != "默认服装"
            and "token" not in skin_key
        ):
            appellation = skin_info["displaySkin"]["modelName"]
            if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(
                65, 91
            ):
                appellation = appellation.upper()
            if skin_info["displaySkin"]["displayTagId"] != None:
                tag = "\n|时装注释={}".format(skin_info["displaySkin"]["displayTagId"])
            else:
                tag = ""
            if (
                skin_info["charId"] == "char_002_amiya"
                and skin_info["tmplId"] == "char_1001_amiya2"
            ):
                skin_char_id = "char_1001_amiya2"
                skin_char_name = "阿米娅(近卫)"
            elif (
                skin_info["charId"] == "char_002_amiya"
                and skin_info["tmplId"] == "char_1037_amiya3"
            ):
                skin_char_id = "char_1037_amiya3"
                skin_char_name = "阿米娅(医疗)"
            else:
                skin_char_id = skin_info["charId"]
                skin_char_name = character_table[skin_char_id]["name"]
            if skin_char_id not in char_count:
                char_count[skin_char_id] = 0
            char_count[skin_char_id] += 1
            skin_name = skin_info["displaySkin"]["skinName"].rstrip()
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
                skin_series=brand_list[skin_info["displaySkin"]["skinGroupId"]],
            )
            order = (
                skin_info["displaySkin"]["onYear"] * 100
                + skin_info["displaySkin"]["onPeriod"]
            )
            if order not in skin_dict:
                skin_dict[order] = {
                    "title": "Y-{} {:0>2d}".format(
                        skin_info["displaySkin"]["onYear"],
                        skin_info["displaySkin"]["onPeriod"],
                    ),
                    "content": {},
                }
            sort_key = (
                skin_info["displaySkin"]["getTime"] + skin_info["displaySkin"]["sortId"]
            )
            while sort_key in skin_dict[order]["content"]:
                sort_key += 0.1
                print("时装回廊 sort_key 重复")
            skin_dict[order]["content"][sort_key] = (skin_char_id, skin_half_desc)
            # if skin_key != "char_123_fang@winter#1":
            #     skin_dict[order]['content'][skin_info['displaySkin']['sortId']] = (skin_char_id, skin_half_desc)
            # else:
            #     skin_dict[order]['content'][skin_info['displaySkin']['sortId'] - 4] = (
            #         skin_char_id, skin_half_desc)

    skin_dict_sorted = [skin_dict[k] for k in sorted(skin_dict.keys(), reverse=True)]

    fin = ""
    template_text = []
    for month in skin_dict_sorted:
        fin += "==={}===\n".format(month["title"])
        for desc_key in sorted(month["content"].keys()):
            desc = month["content"][desc_key]
            fin += desc[1].format(skin_id=char_count[desc[0]])
            char_count[desc[0]] -= 1
        fin += "\n"
    fin = (
        '{{#Widget:Garansandbox/brandbtn}}<div class="contentcontainer"><div class="halfimgcontainer">\n__NOTOC__\n'
        + fin
        + '</div><div class="brandbtncontainer"><div class="brandbtncontroler">{{#Widget:Brandbtn}}</div></div></div>'
    )

    wiki.edit(title="模板:时装回廊", text=fin, summary="update")
    # print(fin)
    print("Updated: {}.".format("模板:时装回廊"))


def update_outfit_brand(wiki, skin_table, character_table):
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

    skin_list = []
    for skin_key in skin_table["charSkins"]:
        skin_info = skin_table["charSkins"][skin_key]
        if (
            skin_info["displaySkin"]["skinGroupName"] == "默认服装"
            or "token" in skin_key
        ):
            continue
        skin_list.append(skin_info)
    skin_list.sort(
        key=lambda x: x["displaySkin"]["getTime"] + x["displaySkin"]["sortId"]
    )

    brand_list = {}
    skin_dict = {}
    for v in sorted(skin_table["brandList"].values(), key=lambda x: x["sortId"]):
        brand_name = v["brandName"].replace("/", "-").rstrip()
        skin_dict[brand_name] = {
            "brandName": v["brandName"],
            "description": v["description"].replace("\n", "<br/>"),
            "kvImgNum": len(v["kvImgIdList"]),
            "half_content": "",
            "detail_content": {},
        }
        for group in v["groupList"]:
            brand_list[group["skinGroupId"]] = brand_name

    char_count = {}
    for skin_info in skin_list:
        appellation = skin_info["displaySkin"]["modelName"]
        if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(
            65, 91
        ):
            appellation = appellation.upper()
        if skin_info["displaySkin"]["displayTagId"] != None:
            tag = "\n|时装注释={}".format(skin_info["displaySkin"]["displayTagId"])
        else:
            tag = ""
        if (
            skin_info["charId"] == "char_002_amiya"
            and skin_info["tmplId"] == "char_1001_amiya2"
        ):
            skin_char_id = "char_1001_amiya2"
            skin_char_name = "阿米娅(近卫)"
        elif (
            skin_info["charId"] == "char_002_amiya"
            and skin_info["tmplId"] == "char_1037_amiya3"
        ):
            skin_char_id = "char_1037_amiya3"
            skin_char_name = "阿米娅(医疗)"
        else:
            skin_char_id = skin_info["charId"]
            skin_char_name = character_table[skin_char_id]["name"]
        if skin_char_id not in char_count:
            char_count[skin_char_id] = 0
        char_count[skin_char_id] += 1
        skin_name = skin_info["displaySkin"]["skinName"].rstrip()
        if " " in skin_name:
            anchor = "\n|锚点={}".format(skin_name.replace(" ", "_"))
        else:
            anchor = ""
        skin_brand = brand_list[skin_info["displaySkin"]["skinGroupId"]]
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

        content_desc = re.sub(
            r"<color name=[^>]*>", "", skin_info["displaySkin"]["content"]
        )
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
            drawerName=",".join(skin_info["displaySkin"]["drawerList"]),
            skinGroupName=skin_info["displaySkin"]["skinGroupName"].rstrip(),
            content=content_desc,
            obtainApproach=skin_info["displaySkin"]["obtainApproach"],
            dialog=skin_info["displaySkin"]["dialog"],
            usage=skin_info["displaySkin"]["usage"],
            description=skin_info["displaySkin"]["description"],
        )
        skin_dict[skin_brand]["detail_content"][skin_name] = skin_detail_desc

    for brand in skin_dict:
        pic = ""
        detail = ""
        old_content = ""
        flag_new = False

        try:
            old_content = wiki.read("时装回廊/" + brand)

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
                        result3 = (
                            re.search(r"\|获得途径([\s\S]+?)\|dialog", origin_detail)
                            .group(1)
                            .rstrip()
                        )
                        origin_detail = origin_detail.replace(
                            result3, result2.group(1).rstrip()
                        )
                    else:
                        print(skin_name, "获取方式 未匹配")
                else:
                    print(skin_name, "detail 未匹配")
                detail += origin_detail
            flag_new = False
        except:
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
            wiki.edit(
                title="时装回廊/" + brand,
                text=content,
                summary="init" if flag_new else "update",
            )
            # print(content)
            if flag_new:
                print("Created: {}.".format("时装回廊/" + brand))
            else:
                print("Updated: {}.".format("时装回廊/" + brand))


def update_logo_link(wiki, skin_table):
    logo_set = set(
        s["displaySkin"]["skinGroupName"] for s in skin_table["charSkins"].values()
    )
    logo_set.discard("默认服装")
    logo_set.discard(None)
    for l in logo_set:
        if "/" in l:
            link_title = f"文件:Skin logo {l}.png"
            x = l.find("/")
            content = f"#redirect [[文件:Skin logo {l[:x]}.png]]"
            wiki.edit(
                title=link_title,
                text=content,
                summary="redirect skin logo",
                createonly=True,
            )
            # print(link_title, content)


class Skin(Job):
    def _run(self):
        character_table = self.getgd("excel/character_table.json")
        skin_table = self.getgd("excel/skin_table.json")
        handbook_info_table = self.getgd("excel/handbook_info_table.json")

        gallery = self.wiki.read("模板:时装回廊")
        old_skin = []
        result = re.findall(r"{{时装回廊/半身像\n([\s\S]*?)\n}}", gallery)
        for skin in result:
            r = re.search(r"\|干员名=([^\n]+?)\n[\s\S]*?\|时装名=([^\n]+?)\n", skin)
            char_name, skin_name = r.group(1), r.group(2)
            old_skin.append(f"{char_name} {skin_name}")
        cid_list = {k: v["name"].strip() for k, v in character_table.items()}
        cid_list["char_1001_amiya2"] = "阿米娅(近卫)"
        cid_list["char_1037_amiya3"] = "阿米娅(医疗)"
        skin_list = []
        for skin_key, skin_info in skin_table["charSkins"].items():
            if (
                skin_info["displaySkin"]["skinGroupName"] == "默认服装"
                or "token" in skin_key
            ):
                continue
            if (
                skin_info["charId"] == "char_002_amiya"
                and skin_info["tmplId"] == "char_1001_amiya2"
            ):
                skin_char_key = "char_1001_amiya2"
            if (
                skin_info["charId"] == "char_1037_amiya3"
                and skin_info["tmplId"] == "char_1037_amiya3"
            ):
                skin_char_key = "char_1037_amiya3"
            else:
                skin_char_key = skin_info["charId"]
            k = f"{cid_list[skin_char_key]} {skin_info['displaySkin']['skinName'].strip()}"
            if k not in old_skin:
                skin_list.append(cid_list[skin_char_key])
                print(f"新时装：{k}")
        # skin_list = ['阿米娅(近卫)']
        if skin_list is not None:
            update_skin(self.wiki, character_table, skin_table, skin_list)

        # update_randomFig(self.wiki, character_table, skin_table)
        # update_skin_handbook(self.wiki, character_table, skin_table)
        update_outfit_gallery(self.wiki, skin_table, character_table)
        update_outfit_brand(self.wiki, skin_table, character_table)
        update_logo_link(self.wiki, skin_table)
