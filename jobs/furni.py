from utils.job import Job


def update_furni_desc(wiki, building_data):
    for furni in building_data['customData']['furnitures']:
        furni_data = building_data['customData']['furnitures'][furni]

        origin_text = wiki.read(furni_data['name'])

        num1 = origin_text.find('|描述=')
        num2 = origin_text.find('|', num1 + 4)
        new_text = origin_text[:num1] + '|描述={}\n'.format(furni_data['description']) + origin_text[num2:]

        if origin_text != new_text:
            wiki.edit(
                title = furni_data['name'],
                text = new_text,
                summary = 'update'
            )
            # print(new_text)
            print('Update: {}.'.format(furni_data['name']))
        else:
            print('Same: {}.'.format(furni_data['name']))


def create_furni(wiki, building_data, item_table):
    furni_list = wiki.category('分类:家具')

    furni_format = '''{{{{家具信息
|名称={name}
|iconId={id}
|类型={type}
|稀有度={rarity}
|氛围={comfort}
|分解获得={destroyObtain}
|大小={size}
|描述={description}
|用途={usage}
|获得方式={obtainApproach}
|所属套装={themes}
|所属组件={groups}
}}}}'''
    individual_furni = []

    for furni in building_data['customData']['furnitures']:
        furni_data = building_data['customData']['furnitures'][furni]
        if furni_data['name'] in furni_list or furni_data['name'] in ['taptap街机', 'bilibili地毯']:
            continue
        if furni_data['canBeDestroy'] == True:
            furni_destroy = '{{{{材料消耗|{name}|{number}}}}}'.format(
                name = item_table['items'][furni_data['processedProductId']]['name'],
                number = furni_data['processedProductCount']
            )
        else:
            furni_destroy = '不可分解'

        groups = ''
        themes = ''
        for groupsId in building_data['customData']['groups']:
            groupsData = building_data['customData']['groups'][groupsId]
            if furni_data['id'] in groupsData['furniture']:
                groups = groupsData['name']
                themes = building_data['customData']['themes'][groupsData['themeId']]['name']
                break

        if groups == '':
            individual_furni.append('{{{{家具|{}}}}}'.format(furni_data['name']))

        furni_info = furni_format.format(
            name = furni_data['name'],
            id = furni_data['id'],
            type = building_data['customData']['types'][furni_data['type']]['name'],
            rarity = furni_data['rarity'],
            comfort = furni_data['comfort'],
            size = str(furni_data['width']) + '×' + str(furni_data['depth']) + '×' + str(furni_data['height']),
            usage = furni_data['usage'],
            themes = themes,
            groups = groups,
            description = furni_data['description'],
            obtainApproach = furni_data['obtainApproach'],
            destroyObtain = furni_destroy
        )

        wiki.edit(
            title = furni_data['name'],
            text = furni_info,
            summary = 'init'
        )
        # print(furni_info)
        print('Created: {}.'.format(furni_data['name']))

    if individual_furni != []:
        wiki.edit(
            title = '首页/新增单件',
            text = ''.join(individual_furni),
            summary = 'update',
            bot = None,
            minor = True
        )
        # print(''.join(individual_furni))
        print('Updated: {}.'.format('首页/新增单件'))


def create_themes(wiki, building_data):
    themes_list = wiki.category('分类:家具主题')

    themes_info = '''{{{{pathnav2|家具一览}}}}
==总览==
{{{{家具主题总览|{themesName}|{description}}}}}
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
{refContent}==套件=={groupsContent}'''

    new_theme = []

    for themes in building_data['customData']['themes']:
        themesData = building_data['customData']['themes'][themes]
        if themesData['name'] in themes_list:
            continue
        # if themesData['name'] != '快捷连锁披萨店':
            # continue

        groupsContent = ''
        quickSetupFurni = ''
        quickSetupGroups = ''
        refId = 1
        refFlag = False
        refContent = ''
        furniComfort = groupsComfort = 0
        quickSetupDict = {}

        for quickFurni in themesData['quickSetup']:
            if quickFurni['furnitureId'] in quickSetupDict:
                quickSetupDict[quickFurni['furnitureId']] += 1
            else:
                quickSetupDict[quickFurni['furnitureId']] = 1

        for quickFurniId in quickSetupDict:
            quickFurniComfort = building_data['customData']['furnitures'][quickFurniId]['comfort']
            quickFurniComfort = quickFurniComfort * min(6, quickSetupDict[quickFurniId])
            furniComfort += quickFurniComfort
            quickSetupFurni += '\n|-\n|[[{name}]]\n|{count}\n|{comfort}'.format(
                name = building_data['customData']['furnitures'][quickFurniId]['name'],
                count = quickSetupDict[quickFurniId],
                comfort = quickFurniComfort
            )
            if quickSetupDict[quickFurniId] > 6:
                quickSetupFurni += '<ref name=注"{}">相同家具只有前6件能够获得氛围</ref>'.format(refId)
                refId += 1
                refFlag = True
        if refFlag:
            refContent = '<references />\n'

        for groups in building_data['customData']['groups']:
            if themes in groups:
                groupsData = building_data['customData']['groups'][groups]
                groupsContent += '\n\'\'\'{name}\'\'\'\n'.format(
                    name = groupsData['name']
                )
                groupsComfort += groupsData['comfort']
                quickSetupGroups += '\n|-\n|{name}\n|{count}\n|{comfort}'.format(
                    name = groupsData['name'],
                    count = groupsData['count'],
                    comfort = groupsData['comfort']
                )
                for groupFurni in groupsData['furniture']:
                    groupsContent += '{{{{家具|{name}}}}}'.format(
                        name = building_data['customData']['furnitures'][groupFurni]['name']
                    )

        totalComfort = furniComfort + groupsComfort

        themesContent = themes_info.format(
            themesName = building_data['customData']['themes'][themes]['name'].replace('/', ''),
            description = building_data['customData']['themes'][themes]['desc'],
            quickSetupFurni = quickSetupFurni,
            furniComfort = furniComfort,
            quickSetupGroups = quickSetupGroups,
            groupsComfort = groupsComfort,
            totalComfort = totalComfort,
            groupsContent = groupsContent,
            refContent = refContent
        )

        new_theme.append('{{{{家具主题|{name}}}}}'.format(
            name = themesData['name'].replace('/', '')
        ))

        wiki.edit(
            title = themesData['name'],
            text = themesContent,
            summary = 'init',
            createonly = True,
            bot = None,
            minor = True
        )
        # print(themesContent)
        print('Created: {}.'.format(themesData['name']))

    if new_theme != []:
        wiki.edit(
            title = '首页/新增主题',
            text = ' '.join(new_theme),
            summary = 'update',
            bot = None,
            minor = True
        )
        # print(' '.join(new_theme))
        print('Updated: {}.'.format('首页/新增主题'))


class Furni(Job):
    def _run(self):
        building_data = self.getgd('excel/building_data.json')
        item_table = self.getgd('excel/item_table.json')

        create_themes(self.wiki, building_data)
        create_furni(self.wiki, building_data, item_table)

    def _run_update(self):
        building_data = self.getgd('excel/building_data.json')

        update_furni_desc(self.wiki, building_data)
