from utils.job import Job
import re


def find(j, name, p):
    for item in j:
        if j[item][name] == p:
            return item
        else:
            return None


def get_id_by_name(item_table, name):
    for item in item_table['items']:
        if item_table['items'][item]['name'].rstrip() == name:
            return item_table['items'][item]['itemId']


def build_time(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)


def trans_rarity(rarity):
    return {
        'TIER_1': 0,
        'TIER_2': 1,
        'TIER_3': 2,
        'TIER_4': 3,
        'TIER_5': 4,
        'TIER_6': 5
    }.get(rarity, rarity)


basic_info4 = '==基础信息==\n{{{{道具信息\n|名称={name}\n|itemId={itemId}\n|iconId={iconId}\n|描述={description}\n|用途={usage}\n|' \
              '获得方式={obtainApproach}\n|稀有度={rarity}\n|id={id}\n|分类={sort}\n}}}}\n'
basic_info3 = '==基础信息==\n{{{{道具信息\n|名称={name}\n|itemId={itemId}\n|iconId={iconId}\n|描述={description}\n|用途={usage}\n|' \
              '稀有度={rarity}\n|id={id}\n|分类={sort}\n}}}}\n'
basic_mf = '{{{{道具配方/制造站\n|产物={name}\n|产物数量={count}\n|仓库消耗={weight}\n|' \
           '时间消耗={costPoint}\n|制造站等级需求={roomLevel}\n'
basic_wf = '{{{{道具配方/加工站\n|产物={name}\n|产物数量={count}\n|龙门币消耗={goldCost}\n|' \
           '心情消耗={apCost:.0f}\n|加工站等级需求={roomLevel}\n|副产物总概率={extraOutcomeRate:.0f}\n'


class Item(Job):
    def _run(self):
        stage_table = self.getgd('excel/stage_table.json')
        item_table = self.getgd('excel/item_table.json')
        building_data = self.getgd('excel/building_data.json')
        items = self.wiki.category('分类:道具')
        u_items = self.wiki.category('分类:未实装道具')
        for item in item_table['items']:
            citem = item_table['items'][item]
            if citem['name'].strip() in u_items:
                continue
            if citem['name'].strip() in items:
                continue
            if 'hideInItemGet' in citem and citem['hideInItemGet']:
                continue
            if citem['itemId'] in ['act1bossrush_relic_04', 'act13side_prestige_armorless', 'act2bossrush_relic_04', 'act3bossrush_relic_04', 'act4bossrush_relic_04']:
                continue
            if citem['itemId'] in ['LINKAGE_TKT_GACHA_10_1701', 'LINKAGE_TKT_GACHA_10_4801']:
                continue
            if citem['name'].find('的信物') != -1:
                sort = '信物'
            elif citem['name'].find('的中坚信物') != -1:
                sort = '中坚信物'
            elif citem['name'].find('信物') != -1:
                sort = '通用信物'
            elif citem['name'].find('芯片组') > 0:
                sort = '芯片组'
            elif citem['name'].find('双芯片') > 0:
                sort = '双芯片'
            elif citem['name'].find('芯片') > 0:
                sort = '芯片'
            else:
                try:
                    if int(item) / 10000 >= 1:
                        sort = '材料'
                    else:
                        sort = '其他道具'
                    if int(item) == 73:
                        print()
                except Exception as e:
                    sort = '其他道具'
            if item_table['items'][item]['obtainApproach']:
                tbasic_info = basic_info4.format(
                    name=citem['name'].strip(),
                    itemId=citem['itemId'],
                    iconId=citem['iconId'] if citem['iconId'] is not None else '',
                    description=citem['description'] if citem['description'] is not None else '',
                    usage=citem['usage'] if citem['usage'] is not None else '',
                    obtainApproach=citem['obtainApproach'],
                    rarity=trans_rarity(citem['rarity']),
                    id=citem['sortId'],
                    sort=sort)
            else:
                tbasic_info = basic_info3.format(
                    name=citem['name'].strip(),
                    itemId=citem['itemId'],
                    iconId=citem['iconId'] if citem['iconId'] is not None else '',
                    description=citem['description'] if citem['description'] is not None else '',
                    usage=citem['usage'] if citem['usage'] is not None else '',
                    rarity=trans_rarity(citem['rarity']),
                    id=citem['sortId'],
                    sort=sort
                )
            if citem['buildingProductList']:
                tmf = ''
                twf = ''
                for d in citem['buildingProductList']:
                    cRoomType = d['roomType']
                    cFormulaId = d['formulaId']
                    if cRoomType == 'MANUFACTURE':
                        cf = building_data['manufactFormulas'][cFormulaId]
                        tmf += basic_mf.format(
                            name=item_table['items'][cf['itemId']]['name'].rstrip(),
                            count=cf['count'],
                            weight=cf['weight'],
                            costPoint=build_time(cf['costPoint']),
                            roomLevel=cf['requireRooms'][0]['roomLevel']
                        )
                        tstr = ''
                        for i in range(0, cf['costs'].__len__()):
                            tstr = tstr + '|原料' + str(i) + '=' + item_table['items'][cf['costs'][i]['id']][
                                'name'].rstrip() + '\n|原料' \
                                   + str(i) + '数量=' + str(cf['costs'][i]['count']) + '\n'
                        tmf = tmf + tstr
                        tmf = tmf + '}}'
                    elif cRoomType == 'WORKSHOP':
                        cf = building_data['workshopFormulas'][cFormulaId]
                        twf += basic_wf.format(
                            name=item_table['items'][cf['itemId']]['name'].rstrip(),
                            count=cf['count'],
                            goldCost=cf['goldCost'],
                            apCost=cf['apCost'] / 360000,
                            roomLevel=cf['requireRooms'][0]['roomLevel'],
                            extraOutcomeRate=cf['extraOutcomeRate'] * 100)
                        tstr = ''
                        for i in range(0, cf['costs'].__len__()):
                            tstr = tstr + '|原料' + str(i + 1) + '=' + item_table['items'][cf['costs'][i]['id']][
                                'name'].rstrip() + '\n|原料' \
                                   + str(i + 1) + '数量=' + str(cf['costs'][i]['count']) + '\n'
                        totalWeight = 0
                        for oc in cf['extraOutcomeGroup']:
                            totalWeight += oc['weight']
                        for i in range(0, cf['extraOutcomeGroup'].__len__()):
                            tstr = tstr + '|副产物' + str(i + 1) + '=' + \
                                   item_table['items'][cf['extraOutcomeGroup'][i]['itemId']]['name'].rstrip() + \
                                   '\n|副产物' + str(i + 1) + '掉率=' + str(
                                round((cf['extraOutcomeGroup'][i]['weight'] / totalWeight * 100), 1)) + '\n'
                        if cf['requireStages']:
                            twf = twf + '|通关评价=' + str(cf['requireStages'][0]['rank']) + \
                                  '\n|关卡=' + stage_table['stages'][cf['requireStages'][0]['stageId']]['code'] + \
                                  '\n|通关条件=' + stage_table['stages'][cf['requireStages'][0]['stageId']]['name'] + '\n'
                        twf = twf + tstr + '}}'
                    else:
                        print('error')
                if tmf:
                    tbasic_info = tbasic_info + '==制造站==\n' + tmf + '\n'
                if twf:
                    tbasic_info = tbasic_info + '==加工站==\n' + twf
                if sort:
                    tbasic_info = tbasic_info + '==材料掉落=='
                # 更新副产物
                # if twf:
                #     old = self.wiki.read(citem['name'].rstrip())
                #     result = re.search(r"==加工站==\n([\s\S]*?)\n+==", old)
                #     if result:
                #         new = old.replace(result.group(1), twf)
                #     else:
                #         new = old
                #     if new != old and citem['name'] != '家具零件':
                #         # print(new)
                #         self.wiki.edit(title=citem['name'].rstrip(), text=new)
                #         print("edit", citem['name'].rstrip())
                #     else:
                #         print(citem['name'].rstrip(), 'same')
            fin = '{{Navigator|道具一览}}\n' + tbasic_info + '\n{{道具导航}}'
            # print(fin)
            try:
                self.wiki.edit(title=citem['name'].rstrip(), text=fin, summary='item init', createonly=True)
            except:
                print('Fail editing Page:', citem['name'])
