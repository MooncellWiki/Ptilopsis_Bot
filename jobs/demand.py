import copy
from utils.job import Job

mat_dic = {}


def trans_rarity(rarity):
    return {
        0: '一星',
        1: '二星',
        2: '三星',
        3: '四星',
        4: '五星',
        5: '六星'
    }[rarity]


def mat_add(mat_type, material, char_name, amount):
    if material not in mat_dic:
        mat_dic[material] = {}
    if char_name not in mat_dic[material]:
        mat_dic[material][char_name] = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
    mat_dic[material][char_name][str(mat_type)] += amount


def update_mat_demand(wiki, character_table, item_table):
    for char in character_table:
        char_detail = character_table[char]
        if char_detail['profession'] == 'TRAP' or char_detail['profession'] == 'TOKEN':
            continue

        for phase_id in range(1, len(char_detail['phases'])):
            if char_detail['phases'][phase_id]['evolveCost']:
                for material_id in range(len(char_detail['phases'][phase_id]['evolveCost'])):
                    mat_add(1, char_detail['phases'][phase_id]['evolveCost'][material_id]['id'], char,
                        char_detail['phases'][phase_id]['evolveCost'][material_id]['count'])

        if char_detail['skills']:
            for allSkillLvlup_id in range(len(char_detail['allSkillLvlup'])):
                if char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost']:
                    for common_material_id in range(len(char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'])):
                        mat_add(2, char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['id'],
                            char, char_detail['allSkillLvlup'][allSkillLvlup_id]['lvlUpCost'][common_material_id]['count'])

            for skill_id in range(len(char_detail['skills'])):
                if char_detail['skills'][skill_id]['levelUpCostCond']:
                    for i in [8, 9, 10]:
                        skill_levelup_material = char_detail['skills'][skill_id]['levelUpCostCond'][i - 8][
                            'levelUpCost']
                        if skill_levelup_material:
                            for material_id in range(len(skill_levelup_material)):
                                mat_add(skill_id + 3, skill_levelup_material[material_id]['id'], char,
                                    skill_levelup_material[material_id]['count'])

    for material in mat_dic:
        origin_text = wiki.read(item_table['items'][material]['name'].rstrip())
        count1 = count2 = count3 = 0
        mat_desc = ''
        mat_text = ['', '', '', '', '', '']
        for mat_char in mat_dic[material]:
            count1 += mat_dic[material][mat_char]['1']
            count2 += mat_dic[material][mat_char]['2']
            sum3 = mat_dic[material][mat_char]['3'] + mat_dic[material][mat_char]['4'] + mat_dic[material][mat_char][
                '5']
            count3 += sum3
            if sum3 == 0:
                num3 = '0'
            else:
                if character_table[mat_char]['rarity'] == 5 or character_table[mat_char]['name'] == '阿米娅':
                    num3 = '{}/{}/{}'.format(mat_dic[material][mat_char]['3'], mat_dic[material][mat_char]['4'],
                        mat_dic[material][mat_char]['5'])
                else:
                    num3 = '{}/{}'.format(mat_dic[material][mat_char]['3'], mat_dic[material][mat_char]['4'])
            mat_text[character_table[mat_char]['rarity']] += '\n|{char_name}|{num1}|{num2}|{num3}'.format(
                char_name = character_table[mat_char]['name'],
                num1 = mat_dic[material][mat_char]['1'],
                num2 = mat_dic[material][mat_char]['2'],
                num3 = num3
            )
        for i in reversed(range(len(mat_text))):
            if mat_text[i] != '':
                if mat_desc == '':
                    mat_desc = '<tabber>\n' + trans_rarity(i) + '=\n{{需求材料干员\n|稀有度=' + str(i) + mat_text[i] + '\n}}'
                else:
                    mat_desc += '\n|-|\n' + trans_rarity(i) + '=\n{{需求材料干员\n|稀有度=' + str(i) + mat_text[i] + '\n}}'
        if mat_desc != '':
            mat_desc += '\n</tabber>\n'
        mat_desc = '==干员需求==\n精英化材料：{num1}<br/>技能1→7材料：{num2}<br/>技能专精材料：{num3}<br/>\'\'\'总计：{num4}\'\'\'\n'.format(
            num1 = count1,
            num2 = count2,
            num3 = count3,
            num4 = count1 + count2 + count3
        ) + mat_desc

        num_flag1 = origin_text.find('==干员需求==')
        num_flag2 = origin_text.find('==材料掉落==')
        if num_flag2 != -1:
            new_text = origin_text[:num_flag1] + mat_desc + origin_text[num_flag2:]
        else:
            new_text = origin_text[:num_flag1] + mat_desc + '==注释与链接==\n<references/>\n{{道具导航}}'

        # edit wiki
        if origin_text != new_text:
            wiki.edit(
                title = item_table['items'][material]['name'].rstrip(),
                text = new_text,
                summary = 'update',
            )
            # print(new_text)
            print('Update: {}.'.format(item_table['items'][material]['name'].rstrip()))
        else:
            print('Same: {}.'.format(item_table['items'][material]['name'].rstrip()))


class Demand(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        item_table = self.getgd('excel/item_table.json')
        char_patch_table = self.getgd('excel/char_patch_table.json')
        
        character_table_new = copy.deepcopy(character_table)
        for k in char_patch_table['patchChars']:
            character_table_new[k] = char_patch_table['patchChars'][k]
        character_table_new['char_1001_amiya2']['name'] = '阿米娅(近卫)'
        character_table_new['char_1001_amiya2']['phases'] = character_table['char_508_aguard']['phases']
        character_table_new['char_1001_amiya2']['allSkillLvlup'] = character_table['char_508_aguard']['allSkillLvlup']

        update_mat_demand(self.wiki, character_table_new, item_table)
