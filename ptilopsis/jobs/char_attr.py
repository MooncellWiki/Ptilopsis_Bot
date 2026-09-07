from typing import Any

from ptilopsis.gamedata.character_table import CharacterData, CharacterTable
from ptilopsis.gamedata.character_util import (
    MAX_POTENTIAL_RANK,
    is_talent_hidden_on_ui,
    rarity_stars,
    select_candidate,
)
from ptilopsis.gamedata.uniequip_table import UniEquipTable
from ptilopsis.jobs.basic import (
    favor_attributes,
    load_id_table,
    phase_attributes,
    sub_profession_name,
    trans_profession,
)
from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles

# 潜能加成的属性名 → 累加到哪个面板值
POTENTIAL_ATTRIBUTES = {
    "MAX_HP": "maxHp",
    "ATK": "atk",
    "DEF": "defence",
    "MAGIC_RESISTANCE": "magicResistance",
    "COST": "cost",
    "ATTACK_SPEED": "attackSpeed",
    "RESPAWN_TIME": "respawnTime",
}


def max_talent_remarks(char: CharacterData, rts: RichTextStyles) -> list[str]:
    """满精英、满级、满潜能时客户端会展示的各天赋描述。"""

    phases = char.phases or []
    if not phases:
        return []
    remarks = []
    for bundle in char.talents or []:
        talent = select_candidate(
            bundle.candidates,
            level=phases[-1].max_level,
            phase=len(phases) - 1,
            potential=MAX_POTENTIAL_RANK,
        )
        if talent is None or is_talent_hidden_on_ui(talent):
            continue
        remarks.append(rts.compile(talent.description))
    return remarks


def get_char_attr(
    character_table: dict[str, CharacterData],
    uniequip_table: UniEquipTable,
    id_table: dict[str, Any],
    rts: RichTextStyles,
) -> str:
    content = []
    for char in character_table.values():
        if char.profession in ("TRAP", "TOKEN"):
            continue
        phases = char.phases or []
        if not phases:
            continue
        final = phase_attributes(phases[-1])[-1]
        favor = favor_attributes(char)

        panel: dict[str, float] = {
            "maxHp": final.max_hp + favor.max_hp,
            "atk": final.atk + favor.atk,
            "defence": final.def_ + favor.def_,
            "magicResistance": final.magic_resistance,
            "cost": final.cost,
            "blockCnt": final.block_cnt,
            "attackSpeed": final.attack_speed,
            "respawnTime": final.respawn_time,
        }

        for potential_rank in char.potential_ranks or []:
            if potential_rank.type != "BUFF":
                continue
            attributes = potential_rank.buff.attributes if potential_rank.buff else None
            for modifier in (
                attributes.attribute_modifiers if attributes else None
            ) or []:
                key = POTENTIAL_ATTRIBUTES.get(modifier.attribute_type)
                if key is None:
                    logger.info(
                        "Error! Char {name} attributeType {num} don't know!".format(
                            name=char.name, num=modifier.attribute_type
                        )
                    )
                    continue
                panel[key] += modifier.value

        desc = "|[[{name}]]||{rarity}||{profession}||{subProfession}||{maxHp:.0f}||{atk:.0f}||{defence:.0f}||{magicResistance:.0f}||{cost:.0f}||{blockCnt:.0f}||{attackSpeed:.0f}||{baseAttackTime}s||data-sort-value={respawnTime:.0f}|{respawnTime:.0f}s".format(
            name=char.name,
            rarity=rarity_stars(char.rarity),
            profession=trans_profession(char.profession),
            subProfession=sub_profession_name(
                uniequip_table, char.sub_profession_id
            ).strip(),
            baseAttackTime=final.base_attack_time,
            **panel,
        )
        remarks = max_talent_remarks(char, rts)
        if remarks:
            desc += f'\n|- class="expand-child" style="font-size:85%; line-height:1.2; color:gray;"\n|colspan="13"|{"<br/>".join(remarks)}'

        content.append(
            {
                "sortId": id_table[char.name]["id"] if char.name in id_table else 1000,
                "text": desc,
            }
        )

    table = """{{cbox2|lv=2|text=以下为全体干员\'\'\'满精英化 满级 满潜能 满信赖\'\'\'时的面板白值，\'\'\'不包括\'\'\'天赋、模组和技能加成。}}
{|class="wikitable sortable" style="text-align:center; width:1000px; display:table; white-space:normal;"
!名字!!稀有度!!职业!!分支!!生命!!攻击!!防御!!法抗!!费用!!阻挡!!攻速!!攻击间隔!!再部署
|-
"""
    table += "\n|-\n".join(
        [
            data["text"]
            for data in sorted(content, key=lambda x: x["sortId"], reverse=True)
        ]
    )
    table += "\n|}"

    return table


@job
def run(ctx: JobContext) -> None:
    character_table = CharacterTable.validate_python(
        ctx.getgd("excel/character_table.json")
    )
    uniequip_table = UniEquipTable.model_validate(
        ctx.getgd("excel/uniequip_table.json")
    )
    id_table = load_id_table(ctx)
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    content = get_char_attr(character_table, uniequip_table, id_table, rts)

    ctx.wiki.edit(title="用户:Seniorious/attribute", text=content, summary="update")
    logger.info("Updated: {}.".format("用户:Seniorious/attribute"))
