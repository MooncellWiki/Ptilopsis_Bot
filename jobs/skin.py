from utils.job import Job
import json
import re


def get_skin_info(char_key, skin_table):
    basic_info = ''
    for phase_id in skin_table['buildinEvolveMap'][char_key]:
        basic_info += '\n|精英{phase_id}描述={des}'.format(
            phase_id = phase_id,
            des = skin_table['charSkins'][skin_table['buildinEvolveMap'][char_key][phase_id]]['displaySkin'][
                'content'].replace('\n', '<br/>')
        )
    skin_desc = {}
    for skin_key in skin_table['charSkins']:
        if char_key in skin_key:
            if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'] != '默认服装':
                order = skin_table['charSkins'][skin_key]['displaySkin']['onYear'] * 12 + \
                        skin_table['charSkins'][skin_key]['displaySkin']['onPeriod']
                skin_desc[
                    order] = '\n|时装{{skin_id}}名称={name}\n|时装{{skin_id}}系列={group}\n|时装{{skin_id}}color={color}\n|时装{{skin_id}}描述={des}'.format(
                    name = skin_table['charSkins'][skin_key]['displaySkin']['skinName'],
                    color = skin_table['charSkins'][skin_key]['displaySkin']['colorList'][0],
                    group = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupName'],
                    des = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>',
                        '').replace('</color>', '').replace('\r', '').replace('\n', '<br/>')
                )
    special_skin_id = 1
    skin_desc_sorted = [skin_desc[k] for k in sorted(skin_desc.keys())]
    for desc in skin_desc_sorted:
        basic_info += desc.format(skin_id = special_skin_id)
        special_skin_id += 1
    basic_info += '\n}}'
    return basic_info, special_skin_id - 1


def update_skin(wiki, character_table, skin_table, skin_list):
    skin_data = []
    for char_id in character_table:
        char_detail = character_table[char_id]
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue
        if skin_list and char_detail['name'] not in skin_list:
            # if char_detail['name'] != '芙蓉':
            continue

        origin_text = wiki.read(char_detail['name'])
        num1 = origin_text.find('\n|精英0描述')
        num2 = origin_text.find('==获得方式==')
        skin_info, count = get_skin_info(char_id, skin_table)
        new_text = origin_text[:num1] + skin_info + '\n' + origin_text[num2:]
        skin_data.append('1={name}:skin={count}'.format(
            name = char_detail['name'],
            count = count
        ))

        if origin_text != new_text:
            wiki.edit(
                title = char_detail['name'],
                text = new_text,
                summary = 'update',
                bot = None,
                minor = True
            )
            # print(new_text)
            print('Update: {}.'.format(char_detail['name']))
        else:
            print('Same: {}.'.format(char_detail['name']))

    wiki.edit(
        title = '首页/亮点干员/新增皮肤/数据',
        text = ','.join(skin_data),
        summary = 'update',
        bot = None,
        minor = True
    )
    # print(','.join(skin_data))
    print('Update: {}.'.format('首页/亮点干员/新增皮肤/数据'))


def update_randomFig(wiki, character_table, skin_table):
    skin_list = {}
    fin = '<choose uncached before="[[文件:" after="|右|555px]]">'
    for skin_key in skin_table['charSkins']:
        skin_content = skin_table['charSkins'][skin_key]
        if skin_content['displaySkin']['skinGroupSortIndex'] in [-50, -30, 0, 1]:
            continue
        if skin_content['displaySkin']['skinGroupName'] == '默认服装':
            fin += '\n<option>立绘 {name} 2.png|link={name}</option>'.format(
                name = character_table[skin_content['charId']]['name']
            )
        else:
            char_name = character_table[skin_content['charId']]['name']
            if char_name in skin_list:
                skin_list[char_name] += 1
            else:
                skin_list[char_name] = 1

    for char in skin_list:
        for skin_num in range(skin_list[char]):
            fin += '\n<option>立绘 {name} skin{id}.png|link={name}</option>'.format(
                name = char,
                id = skin_num + 1
            )
    fin += '\n</choose>'

    wiki.edit(
        title = '模板:随机干员立绘',
        text = fin,
        summary = 'update'
    )
    # print(fin)
    print('Update: {}.'.format('模板:随机干员立绘'))


def update_skin_handbook(wiki, character_table, skin_table):
    skin_format = '''{{{{锚点|{skinKey}}}}}
\'\'\'{name}\'\'\'
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
}}}}'''

    skin_char = {}
    max_index = 0
    for skin_key in skin_table['charSkins']:
        if skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex'] > max_index:
            max_index = skin_table['charSkins'][skin_key]['displaySkin']['skinGroupSortIndex']

    skin_group_order = ['' for x in range(max_index)]
    skin_group_list1 = {}
    skin_group_list2 = {}

    for skin_key in skin_table['charSkins']:
        skin_info = skin_table['charSkins'][skin_key]
        if skin_info['displaySkin']['skinGroupName'] != '默认服装' and 'token' not in skin_key:
            if skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] == '':
                skin_group_order[skin_info['displaySkin']['skinGroupSortIndex'] - 1] = skin_info['displaySkin'][
                    'skinGroupName']
                skin_group_list1[skin_info['displaySkin']['skinGroupName']] = []
                skin_group_list2[skin_info['displaySkin']['skinGroupName']] = []

            if skin_table['charSkins'][skin_key]['charId'] not in skin_char:
                skin_char[skin_table['charSkins'][skin_key]['charId']] = 0

            skin_char[skin_info['charId']] += 1
            skin_text1 = skin_format.format(
                skinKey = skin_info['portraitId'].replace('#', ''),
                name = character_table[skin_info['charId']]['name'],
                skinName = skin_info['displaySkin']['skinName'],
                skinNo = skin_char[skin_info['charId']],
                modelName = skin_info['displaySkin']['modelName'],
                drawerName = skin_info['displaySkin']['drawerName'],
                skinGroupId = skin_info['displaySkin']['skinGroupId'],
                skinGroupName = skin_info['displaySkin']['skinGroupName'],
                content = skin_table['charSkins'][skin_key]['displaySkin']['content'].replace('<color name=#ffffff>',
                    '').replace('</color>', '').replace('\r', '').replace('\n', '<br/>'),
                dialog = skin_info['displaySkin']['dialog'],
                usage = skin_info['displaySkin']['usage'],
                description = skin_info['displaySkin']['description'],
                obtainApproach = skin_info['displaySkin']['obtainApproach']
            )
            skin_text2 = '{{{{皮肤头像|{name}|90px|{skinNo}|link=#{skinKey}}}}}'.format(
                name = character_table[skin_info['charId']]['name'],
                skinNo = skin_char[skin_info['charId']],
                skinKey = skin_info['portraitId'].replace('#', '')
            )
            skin_group_list1[skin_info['displaySkin']['skinGroupName']].append(skin_text1)
            skin_group_list2[skin_info['displaySkin']['skinGroupName']].append(skin_text2)

    handbook = '__NOTOC__\n{|class="wikitable" style="width:1000px; white-space:normal; display:table;"\n!皮肤组\n!干员'
    for group_name in skin_group_order:
        if group_name != '':
            handbook += '\n|-\n|\'\'\'{groupName}\'\'\'\n|'.format(
                groupName = group_name
            ) + ''.join(skin_group_list2[group_name])
    handbook += '\n|}'
    for group_name in skin_group_order:
        if group_name != '':
            handbook += '\n=={}==\n'.format(group_name)
            handbook += '\n'.join(skin_group_list1[group_name])

    wiki.edit(
        title = '用户:Seniorious/skins',
        text = handbook,
        summary = 'update'
    )
    # print(handbook)
    print('Update: {}.'.format('用户:Seniorious/skins'))


def update_outfit_gallery(wiki, skin_table, character_table):
    skin_half_format = '''{{{{{{{{时装回廊/半身像
|干员名={char}
|时装序号={{skin_id}}{tag}
|干员外文名={appellation}
|时装名={skin_name}{anchor}
|时装系列={skin_series}
}}}}}}}}'''

    brand_list = {}
    for brand in skin_table['brandList']:
        for group in skin_table['brandList'][brand]['groupList']:
            brand_list[group] = skin_table['brandList'][brand]['brandName'].replace('/', '-').rstrip()

    skin_dict = {}
    char_count = {}
    for skin_key in skin_table['charSkins']:
        skin_info = skin_table['charSkins'][skin_key]
        if skin_info['displaySkin']['skinGroupName'] != '默认服装' and 'token' not in skin_key:
            appellation = skin_info['displaySkin']['modelName']
            if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(65, 91):
                appellation = appellation.upper()
            if skin_info['displaySkin']['displayTagId'] != None:
                tag = '\n|时装注释={}'.format(skin_info['displaySkin']['displayTagId'])
            else:
                tag = ''
            if skin_info['charId'] not in char_count:
                char_count[skin_info['charId']] = 0
            char_count[skin_info['charId']] += 1
            skin_name = skin_info['displaySkin']['skinName'].rstrip()
            if ' ' in skin_name:
                anchor = '\n|锚点={}'.format(skin_name.replace(' ', '_'))
            else:
                anchor = ''
            skin_half_desc = skin_half_format.format(
                char = character_table[skin_info['charId']]['name'],
                tag = tag,
                appellation = appellation,
                skin_name = skin_name,
                anchor = anchor,
                skin_series = brand_list[skin_info['displaySkin']['skinGroupId']]
            )
            order = skin_info['displaySkin']['onYear'] * 12 + skin_info['displaySkin']['onPeriod']
            if order not in skin_dict:
                skin_dict[order] = {
                    'title': 'Y-{} {:0>2d}'.format(skin_info['displaySkin']['onYear'],
                        skin_info['displaySkin']['onPeriod']),
                    'content': {}
                }
            sort_key = skin_info['displaySkin']['getTime'] + skin_info['displaySkin']['sortId']
            while sort_key in skin_dict[order]['content']:
                sort_key += 0.1
                print('时装回廊 sort_key 重复')
            skin_dict[order]['content'][sort_key] = (skin_info['charId'], skin_half_desc)
            # if skin_key != "char_123_fang@winter#1":
            #     skin_dict[order]['content'][skin_info['displaySkin']['sortId']] = (skin_info['charId'], skin_half_desc)
            # else:
            #     skin_dict[order]['content'][skin_info['displaySkin']['sortId'] - 4] = (
            #         skin_info['charId'], skin_half_desc)

    skin_dict_sorted = [skin_dict[k] for k in sorted(skin_dict.keys(), reverse = True)]

    fin = ''
    template_text = []
    for month in skin_dict_sorted:
        fin += '==={}===\n'.format(month['title'])
        for desc_key in sorted(month['content'].keys()):
            desc = month['content'][desc_key]
            fin += desc[1].format(skin_id = char_count[desc[0]])
            char_count[desc[0]] -= 1
        fin += '\n'
    fin = '{{#Widget:Garansandbox/brandbtn}}<div class="contentcontainer"><div class="halfimgcontainer">\n__NOTOC__\n' \
          + fin + '</div><div class="brandbtncontainer"><div class="brandbtncontroler">{{#Widget:Brandbtn}}</div></div></div>'

    wiki.edit(
        # title = '用户:Seniorious/gallery',
        title = '模板:时装回廊',
        text = fin,
        summary = 'update'
    )
    # print(fin)
    # print('Update: {}.'.format('用户:Seniorious/gallery'))
    print('Update: {}.'.format('模板:时装回廊'))


def update_outfit_brand(wiki, skin_table, character_table):
    skin_half_format = '''{{{{时装回廊/半身像
|干员名={char}
|时装序号={skin_id}{tag}
|干员外文名={appellation}
|时装名={skin_name}{anchor}
|时装系列={skin_brand}
}}}}'''

    skin_format = '''
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
}}}}'''

    brand_format = '''__NOTOC__
{{{{时装回廊/轮播{pic}
|名称={brand}
|简介={brand_desc}
}}}}
<div class="centercontainer"><div class="centercontroler">
{half_content}</div></div>{detail_content}'''
    
    skin_list = []
    for skin_key in skin_table['charSkins']:
        skin_info = skin_table['charSkins'][skin_key]
        if skin_info['displaySkin']['skinGroupName'] == '默认服装' or 'token' in skin_key:
            continue
        skin_list.append(skin_info)
    skin_list.sort(key = lambda x: x['displaySkin']['getTime'] + x['displaySkin']['sortId'])

    brand_list = {}
    skin_dict = {}
    for v in sorted(skin_table['brandList'].values(), key = lambda x: x['sortId']):
        brand_name = v['brandName'].replace('/', '-').rstrip()
        skin_dict[brand_name] = {
            'brandName': v['brandName'],
            'description': v['description'].replace('\n', '<br/>'),
            'kvImgNum': len(v['kvImgIdList']),
            'half_content': '',
            'detail_content': {}
        }
        for group in v['groupList']:
            brand_list[group] = brand_name

    char_count = {}
    for skin_info in skin_list:
        appellation = skin_info['displaySkin']['modelName']
        if ord(appellation[0]) in range(97, 123) or ord(appellation[0]) in range(65, 91):
            appellation = appellation.upper()
        if skin_info['displaySkin']['displayTagId'] != None:
            tag = '\n|时装注释={}'.format(skin_info['displaySkin']['displayTagId'])
        else:
            tag = ''
        if skin_info['charId'] not in char_count:
            char_count[skin_info['charId']] = 0
        char_count[skin_info['charId']] += 1
        skin_name = skin_info['displaySkin']['skinName'].rstrip()
        if ' ' in skin_name:
            anchor = '\n|锚点={}'.format(skin_name.replace(' ', '_'))
        else:
            anchor = ''
        skin_brand = brand_list[skin_info['displaySkin']['skinGroupId']]
        skin_half_desc = skin_half_format.format(
            char = character_table[skin_info['charId']]['name'],
            tag = tag,
            appellation = appellation,
            skin_name = skin_name,
            skin_id = char_count[skin_info['charId']],
            anchor = anchor,
            skin_brand = skin_brand
        )
        skin_dict[skin_brand]['half_content'] += skin_half_desc

        skin_detail_desc = skin_format.format(
            anchor = '{{{{锚点|{}}}}}\n'.format(skin_name.replace(' ', '_')) if ' ' in skin_name else '',
            name = character_table[skin_info['charId']]['name'],
            skinName = skin_name,
            skinNo = char_count[skin_info['charId']],
            drawerName = skin_info['displaySkin']['drawerName'].rstrip(),
            skinGroupName = skin_info['displaySkin']['skinGroupName'].rstrip(),
            content = skin_info['displaySkin']['content'].replace('<color name=#ffffff>',
                '').replace('</color>', '').replace('\r', '').replace('\n', '<br/>'),
            obtainApproach = skin_info['displaySkin']['obtainApproach'],

            dialog = skin_info['displaySkin']['dialog'],
            usage = skin_info['displaySkin']['usage'],
            description = skin_info['displaySkin']['description']
        )
        skin_dict[skin_brand]['detail_content'][skin_name] = skin_detail_desc

    for brand in skin_dict:
        pic = ''
        detail = ''
        flag_new = False

        try:
            old_content = wiki.read('时装回廊/' + brand)

            for i in range(skin_dict[brand]['kvImgNum'] + 1):
                result = re.search(r'\|图{}=([\s\S]+?)\n\|'.format(i+1), old_content)
                if result:
                    pic += '\n|图{}={}'.format(i+1, result.group(1).rstrip())
                else:
                    pic += '\n|图{}='.format(i+1)

            for skin_name in skin_dict[brand]['detail_content']:
                origin_detail = skin_dict[brand]['detail_content'][skin_name]
                result = re.search(r'=={}==([\s\S]+?)\n'.format(skin_name)+'\}\}', old_content)
                if result:
                    text_part = result.group(1).rstrip()
                    result2 = re.search(r'\|获得途径([\s\S]+?)\|dialog', text_part)
                    if result2:
                        result3 = re.search(r'\|获得途径([\s\S]+?)\|dialog', origin_detail).group(1).rstrip()
                        origin_detail = origin_detail.replace(result3, result2.group(1).rstrip())
                    else:
                        print(skin_name, '获取方式 未匹配')
                else:
                    print(skin_name, 'detail 未匹配')
                detail += origin_detail
            flag_new = False
        except:
            pic = ''.join(['\n|图{}='.format(i + 1) for i in range(skin_dict[brand]['kvImgNum'] + 1)])
            for s in skin_dict[brand]['detail_content']:
                detail += skin_dict[brand]['detail_content'][s]
            flag_new = True

        content = brand_format.format(
            pic = pic,
            brand = brand,
            brand_desc = skin_dict[brand]['description'],
            half_content = skin_dict[brand]['half_content'],
            detail_content = detail,
        )
        wiki.edit(
            title = '时装回廊/' + brand,
            text = content,
            summary = 'init' if flag_new else 'update'
        )
        # print(content)
        if flag_new:
            print('Create: {}.'.format('时装回廊/' + brand))
        else:
            print('Update: {}.'.format('时装回廊/' + brand))


class Skin(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        skin_table = self.getgd('excel/skin_table.json')

        update_randomFig(self.wiki, character_table, skin_table)
        # update_skin_handbook(self.wiki, character_table, skin_table)
        update_outfit_gallery(self.wiki, skin_table, character_table)
        update_outfit_brand(self.wiki, skin_table, character_table)

    def _run_update(self, skin_list = None):
        character_table = self.getgd('excel/character_table.json')
        skin_table = self.getgd('excel/skin_table.json')

        update_skin(self.wiki, character_table, skin_table, skin_list)
