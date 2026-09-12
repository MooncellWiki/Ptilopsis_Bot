from collections.abc import Iterable, Iterator

from ptilopsis.gamedata.character_table import CharacterData, ItemBundle
from ptilopsis.gamedata.character_util import rarity_stars
from ptilopsis.gamedata.item_table import InventoryData
from ptilopsis.jobs import params
from ptilopsis.jobs.basic import item_name
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

# {材料 id: {干员 id: {需求类型: 数量}}}
# 需求类型:1 精英化、2 技能 1→7、3/4/5 一/二/三技能专精
MaterialDemand = dict[str, dict[str, dict[str, int]]]


def trans_rarity(rarity: int) -> str:
    """稀有度下标(0 起)→ 页面上的 tab 名。"""

    return {0: "一星", 1: "二星", 2: "三星", 3: "四星", 4: "五星", 5: "六星"}[rarity]


def rarity_index(char: CharacterData) -> int:
    """``TIER_n`` → ``n - 1``,与旧数据里的数字稀有度一致。"""

    return rarity_stars(char.rarity) - 1


def iter_costs(bundles: Iterable[ItemBundle] | None) -> Iterator[tuple[str, int]]:
    """``(材料 id, 数量)``;没有 id 的条目跳过。"""

    for bundle in bundles or []:
        if bundle.id is not None:
            yield bundle.id, bundle.count


def mat_add(
    mat_dic: MaterialDemand, mat_type: int, material: str, char_name: str, amount: int
) -> None:
    char_demand = mat_dic.setdefault(material, {}).setdefault(
        char_name, {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    )
    char_demand[str(mat_type)] += amount


def collect_demand(character_table: dict[str, CharacterData]) -> MaterialDemand:
    """统计每种材料被哪些干员的精英化 / 技能升级 / 专精需要多少。"""

    mat_dic: MaterialDemand = {}
    for char_key, char in character_table.items():
        if char.profession in ("TRAP", "TOKEN"):
            continue

        for phase in (char.phases or [])[1:]:
            for material, count in iter_costs(phase.evolve_cost):
                mat_add(mat_dic, 1, material, char_key, count)

        if char.skills:
            for level_cost in char.all_skill_lvlup or []:
                for material, count in iter_costs(level_cost.lvl_up_cost):
                    mat_add(mat_dic, 2, material, char_key, count)

            for skill_id, skill in enumerate(char.skills):
                if skill.level_up_cost_cond:
                    for i in [8, 9, 10]:
                        for material, count in iter_costs(
                            skill.level_up_cost_cond[i - 8].level_up_cost
                        ):
                            mat_add(mat_dic, skill_id + 3, material, char_key, count)
    return mat_dic


async def update_mat_demand(
    wiki: Wiki, character_table: dict[str, CharacterData], item_table: InventoryData
) -> None:
    mat_dic = collect_demand(character_table)
    # 所有材料页面一次批量读完,页面不存在时和逐个读一样抛 KeyError
    texts = await wiki.read_many(
        item_name(item_table, material).rstrip() for material in mat_dic
    )
    for material in mat_dic:
        origin_text = texts[item_name(item_table, material).rstrip()]
        count1 = count2 = count3 = 0
        mat_desc = ""
        mat_text = ["", "", "", "", "", ""]
        for mat_char, demand in mat_dic[material].items():
            char = character_table[mat_char]
            count1 += demand["1"]
            count2 += demand["2"]
            sum3 = demand["3"] + demand["4"] + demand["5"]
            count3 += sum3
            if sum3 == 0:
                num3 = "0"
            elif rarity_index(char) == 5 or char.name == "阿米娅":
                num3 = "{}/{}/{}".format(demand["3"], demand["4"], demand["5"])
            else:
                num3 = "{}/{}".format(demand["3"], demand["4"])
            mat_text[rarity_index(char)] += (
                "\n|{char_name}|{num1}|{num2}|{num3}".format(
                    char_name=char.name, num1=demand["1"], num2=demand["2"], num3=num3
                )
            )
        for i in reversed(range(len(mat_text))):
            if mat_text[i] != "":
                if mat_desc == "":
                    mat_desc = (
                        "<tabber>\n"
                        + trans_rarity(i)
                        + "=\n{{需求材料干员\n|稀有度="
                        + str(i)
                        + mat_text[i]
                        + "\n}}"
                    )
                else:
                    mat_desc += (
                        "\n|-|\n"
                        + trans_rarity(i)
                        + "=\n{{需求材料干员\n|稀有度="
                        + str(i)
                        + mat_text[i]
                        + "\n}}"
                    )
        if mat_desc != "":
            mat_desc += "\n</tabber>\n"
        mat_desc = (
            f"==干员需求==\n精英化材料：{count1}<br/>技能1→7材料：{count2}<br/>技能专精材料：{count3}<br/>'''总计：{count1 + count2 + count3}'''\n"
            + mat_desc
        )

        # 新版，widget
        title = item_name(item_table, material).strip()
        mat_desc = f"==干员需求==\n{{{{#widget:ItemDemand|item={title}}}}}\n"

        num_flag1 = origin_text.find("==干员需求==")
        num_flag2 = origin_text.find("==材料掉落==")
        if num_flag2 != -1:
            new_text = origin_text[:num_flag1] + mat_desc + origin_text[num_flag2:]
        else:
            new_text = (
                origin_text[:num_flag1]
                + mat_desc
                + "==注释与链接==\n<references/>\n{{道具导航}}"
            )

        # edit wiki
        if origin_text != new_text:
            await wiki.edit(title=title, text=new_text, summary="update")
            # logger.info(new_text)
            logger.info(f"Update: {title}.")
        # else:
        #     logger.info('Same: {}.'.format(title))


def merge_patch_chars(
    character_table: dict[str, CharacterData], char_patch_table: params.CharPatchTable
) -> dict[str, CharacterData]:
    """把升变干员并进干员表;阿米娅(近卫)沿用近卫阿米娅的精英化与技能升级材料。"""

    for key, patch in (char_patch_table.patch_chars or {}).items():
        # char_patch_table 里的 CharacterData 是另一份同构模型,转成干员表的
        character_table[key] = CharacterData.model_validate(
            patch.model_dump(by_alias=True)
        )
    amiya2 = character_table["char_1001_amiya2"]
    aguard = character_table["char_508_aguard"]
    amiya2.name = "阿米娅(近卫)"
    amiya2.phases = aguard.phases
    amiya2.all_skill_lvlup = aguard.all_skill_lvlup
    return character_table


@job
async def run(
    wiki: Wiki,
    character_table: params.CharacterTable,
    item_table: params.ItemTable,
    char_patch_table: params.CharPatchTable,
    id_table: params.CharIdTable,
) -> None:
    character_table = merge_patch_chars(character_table, char_patch_table)

    def sort_id(key: str) -> int:
        name = character_table[key].name
        return id_table[name]["id"] if name in id_table else 9999

    character_table_new = {
        k: character_table[k] for k in sorted(character_table, key=sort_id)
    }

    await update_mat_demand(wiki, character_table_new, item_table)
