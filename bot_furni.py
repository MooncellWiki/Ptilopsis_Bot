import re
import time

from wikiapi import *


def update_furni(se, url, buildingData, itemTable):
    furniFormat = '''{{{{家具信息
|名称={name}
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

    for furni in buildingData['customData']['furnitures']:
        furniData = buildingData['customData']['furnitures'][furni]
        if furniData['canBeDestroy']:
            furniDestroy = '{{{{材料消耗|{name}|{number}}}}}'.format(
                name = itemTable['items'][furniData['processedProductId']]['name'],
                number = furniData['processedProductCount']
            )
        else:
            furniDestroy = '不可分解'

        groups = ''
        themes = ''
        for groupsId in buildingData['customData']['groups']:
            groupsData = buildingData['customData']['groups'][groupsId]
            if furniData['id'] in groupsData['furniture']:
                groups = groupsData['name']
                themes = buildingData['customData']['themes'][groupsData['themeId']]['name']
                break

        furniInfo = furniFormat.format(
            name = furniData['name'],
            type = buildingData['customData']['types'][furniData['type']]['name'],
            rarity = furniData['rarity'],
            comfort = furniData['comfort'],
            size = str(furniData['width']) + '×' + str(furniData['depth']) + '×' + str(furniData['height']),
            usage = furniData['usage'],
            themes = themes,
            groups = groups,
            description = furniData['description'],
            obtainApproach = furniData['obtainApproach'],
            destroyObtain = furniDestroy
        )

        write_wiki(se, url, furniData['name'], furniInfo, '')
        # print(furniInfo)
        print(furniData['name'], 'updated.')


def create_furni(se, url, buildingData, itemTable):
    res = se.post(url, data = {'format': 'json', 'action': 'query', 'list': 'categorymembers', 'cmtitle': '分类:家具', 'cmlimit': 5000})
    ret = res.json()['query']['categorymembers']
    furni_list = []
    for furni in ret:
        furni_list.append(furni['title'])

    furniFormat = '''{{{{家具信息
|名称={name}
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

    for furni in buildingData['customData']['furnitures']:
        furniData = buildingData['customData']['furnitures'][furni]
        if furniData['name'] in furni_list or furniData['name'] in ['taptap街机', 'bilibili地毯']:
            continue
        else:
            if furniData['canBeDestroy']:
                furniDestroy = '{{{{材料消耗|{name}|{number}}}}}'.format(
                    name = itemTable['items'][furniData['processedProductId']]['name'],
                    number = furniData['processedProductCount']
                )
            else:
                furniDestroy = '不可分解'

            groups = ''
            themes = ''
            for groupsId in buildingData['customData']['groups']:
                groupsData = buildingData['customData']['groups'][groupsId]
                if furniData['id'] in groupsData['furniture']:
                    groups = groupsData['name']
                    themes = buildingData['customData']['themes'][groupsData['themeId']]['name']
                    break

            if groups == '':
                individual_furni.append(furniData['name'])

            furniInfo = furniFormat.format(
                name = furniData['name'],
                type = buildingData['customData']['types'][furniData['type']]['name'],
                rarity = furniData['rarity'],
                comfort = furniData['comfort'],
                size = str(furniData['width']) + '×' + str(furniData['depth']) + '×' + str(furniData['height']),
                usage = furniData['usage'],
                themes = themes,
                groups = groups,
                description = furniData['description'],
                obtainApproach = furniData['obtainApproach'],
                destroyObtain = furniDestroy
            )

            write_wiki(se, url, furniData['name'], furniInfo, '')
            # print(furniInfo)
            print('Create: {}.'.format(furniData['name']))

    print('新家具散件:', individual_furni)


def create_themes(se, url, buildingData):
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

    for themes in buildingData['customData']['themes']:
        themesData = buildingData['customData']['themes'][themes]
        if not read_wiki_exist(se, url, themesData['name']):
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
                quickFurniComfort = buildingData['customData']['furnitures'][quickFurniId]['comfort']
                quickFurniComfort = quickFurniComfort * min(6, quickSetupDict[quickFurniId])
                furniComfort += quickFurniComfort
                quickSetupFurni += '\n|-\n|[[{name}]]\n|{count}\n|{comfort}'.format(
                    name = buildingData['customData']['furnitures'][quickFurniId]['name'],
                    count = quickSetupDict[quickFurniId],
                    comfort = quickFurniComfort
                )
                if quickSetupDict[quickFurniId] > 6:
                    quickSetupFurni += '<ref name=注"{}">相同家具只有前6件能够获得氛围</ref>'.format(refId)
                    refId += 1
                    refFlag = True
            if refFlag:
                refContent = '<references />\n'

            for groups in buildingData['customData']['groups']:
                if themes in groups:
                    groupsData = buildingData['customData']['groups'][groups]
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
                            name = buildingData['customData']['furnitures'][groupFurni]['name']
                        )

            totalComfort = furniComfort + groupsComfort

            themesContent = themes_info.format(
                themesName = buildingData['customData']['themes'][themes]['name'].replace('/', ''),
                description = buildingData['customData']['themes'][themes]['desc'],
                quickSetupFurni = quickSetupFurni,
                furniComfort = furniComfort,
                quickSetupGroups = quickSetupGroups,
                groupsComfort = groupsComfort,
                totalComfort = totalComfort,
                groupsContent = groupsContent,
                refContent = refContent
            )

            write_wiki_minor(se, url, themesData['name'], themesContent, '')
            # print(themesContent)
            print('Create: {}.'.format(themesData['name']))
