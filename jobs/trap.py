import re
import json
import asyncio
import zipfile
from io import BytesIO
from typing import cast

import UnityPy
import requests
import mwparserfromhell
from mwparserfromhell import parse
from mwparserfromhell.wikicode import Template
from torappu.core import main as torappu_exporter
from torappu.core.task.task import Client
from torappu.core.task.utils import build_container_path, read_obj
from torappu.models import Version
from UnityPy import Environment
from UnityPy.classes import MonoBehaviour, PPtr
from UnityPy.classes.generated import ComponentPair

from utils.data import GameData
from utils.job import Job
from utils.richTextStyles import BBKeyReplace, RichTextStyles
from utils.wiki import Wiki


def fetch_json(url: str) -> dict:
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def fetch_data(url: str) -> bytes:
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content


def has_template_in_text(name: str, code: mwparserfromhell.wikicode.Wikicode) -> bool:
    for template in code.filter_templates(recursive=False):
        template = cast(mwparserfromhell.wikicode.Template, template)
        if template.name.strip() == name:
            return True
    return False


def update_trap_template_ids(
    code, trapid
) -> tuple[mwparserfromhell.wikicode.Wikicode, bool]:
    changed = False
    for template in code.filter_templates(recursive=False):
        template = cast(mwparserfromhell.wikicode.Template, template)
        if template.name.strip() == "装置信息":
            existed_ids = template.get("装置id").value.strip()
            if existed_ids:
                ids = existed_ids.split(",")
            else:
                ids = []
            if trapid not in ids:
                ids.append(trapid)
                template.add("装置id", (",".join(ids)) + "\n")
                changed = True
            break
    return code, changed


TRAP_DATA_PATH = {
    "customed_trapid": "装置id",  # 匠心手加
    "name": "名称",
    "description": "描述",
    "appellation": "英文名",
    "phases": {
        0: {
            "rangeId": "攻击范围",
            "attributesKeyFrames": {
                0: {
                    "level": "阶段1等级",
                    "data": {
                        "maxHp": "阶段1生命值",
                        "atk": "阶段1攻击力",
                        "def": "阶段1防御力",
                        "magicResistance": "阶段1法术抗性",
                        "cost": "部署费用",
                        "blockCnt": "阻挡数",
                        "baseAttackTime": "攻击间隔",
                        "respawnTime": "再部署时间",
                        "spRecoveryPerSec": "技力恢复速度",
                        "tauntLevel": "嘲讽等级",
                        "stunImmune": "眩晕抗性",
                        "silenceImmune": "沉默抗性",
                        "sleepImmune": "沉睡抗性",
                        "frozenImmune": "冻结抗性",
                    },
                },
                1: {
                    "level": "阶段2等级",
                    "data": {
                        "maxHp": "阶段2生命值",
                        "atk": "阶段2攻击力",
                        "def": "阶段2防御力",
                        "magicResistance": "阶段2法术抗性",
                    },
                },
            },
        }
    },
}


class Trap(Job):
    def __init__(self, wiki: Wiki, gamedata: GameData):
        super().__init__(wiki, gamedata)
        self.region = self.gamedata.unpacker.region
        self.hotupdate_list = self.gamedata.unpacker.get_update_list(self.region)
        self.char_data = self.getgd("excel/character_table.json", self.region)
        self.skill_data = self.getgd("excel/skill_table.json", self.region)
        for k, v in self.char_data.items():
            v["customed_trapid"] = k
        self.rts = RichTextStyles(self.getgd("excel/gamedata_const.json", self.region))
        # self.gamedata.unpacker.get_update_list()
        # self.gamedata.unpacker.load_idx()
        # self.gamedata.unpacker.get_all_ab()
        # self.gamedata.unpacker.check_update()
        # self.gamedata.unpacker.unpack_all_data()
        version = self.gamedata.unpacker.version[self.region]
        self.resVersion = version["resVersion"]
        self.clientVersion = version["clientVersion"]
        self.client: Client | None = None
        self.asset_env: Environment | None = None

    def to_string(self, value):
        if isinstance(value, bool):
            return "有" if value else "无"
        if isinstance(value, str):
            return self.rts.compile(value)
        return str(value)

    def param_strip(self, text: str):
        return text.strip() + "\n"

    def zip_enter(self, text):
        return re.sub(r"\n+", "\n", str(text))

    def get_tokens_prefab(self) -> list[str]:
        return [
            i["name"]
            for i in self.hotupdate_list["abInfos"]
            if i["name"].startswith("pkgrps/btl_pfb_tokens")
        ]

    def get_unity_env(self):
        assets = []
        for path in self.get_tokens_prefab():
            pathx = path.replace("/", "_").replace(".ab", ".dat")
            bin_data = fetch_data(
                f"https://ak.hycdn.cn/assetbundle/official/Android/assets/{self.resVersion}/{pathx}"
            )
            folder = zipfile.ZipFile(BytesIO(bin_data))
            assets.append(folder.open(path))
        return UnityPy.load(*assets)

    def get_wiki_traps(self):
        pagel: dict = self.wiki.ask(query="[[分类:装置]]|?装置id|?装置名称|limit=1000")
        pagel: dict = pagel["results"]
        cleaned_pagel = {}
        for key, value in pagel.items():
            printouts = value["printouts"]
            if not printouts["装置id"]:
                continue
            for i in printouts["装置id"]:
                cleaned_pagel[i] = {
                    "id": i,
                    "trapname": printouts["装置名称"][0],
                    "wikipage": value["fulltext"],
                }
        existed_pages = [value["wikipage"] for key, value in cleaned_pagel.items()]
        return cleaned_pagel, existed_pages

    def char_data_fill(self, text, path, data):
        result = {}
        for key, value in path.items():
            if type(value) is str:
                if key in data.keys() and data[key] is not None:
                    result[value] = self.to_string(data[key])
            else:
                result.update(self.char_data_fill(text, value, data[key]))
        return {k: str(v) for k, v in result.items()}

    def skill_data_fill(self, data):
        SP_TYPE = {
            "INCREASE_WITH_TIME": "自动回复",
            "INCREASE_WHEN_ATTACK": "攻击回复",
            "INCREASE_WHEN_TAKEN_DAMAGE": "受击回复",
            8: "被动",
        }
        SKILL_TYPE = {"PASSIVE": "被动", "MANUAL": "手动触发", "AUTO": "自动触发"}

        result = {}
        result["技能名"] = data["levels"][0]["name"]
        result["技能类型1"] = SP_TYPE[data["levels"][0]["spData"]["spType"]]

        if data["levels"][0]["spData"]["spType"] != 8:
            result["技能类型2"] = SKILL_TYPE[data["levels"][0]["skillType"]]

        if (
            "rangeId" in data["levels"][0].keys()
            and data["levels"][0]["rangeId"] is not None
        ):
            result["技能范围"] = data["levels"][0]["rangeId"]

        for i in range(0, len(data["levels"])):
            result[f"技能{i + 1}初始"] = data["levels"][i]["spData"]["initSp"]
            result[f"技能{i + 1}消耗"] = data["levels"][i]["spData"]["spCost"]

            if data["levels"][i]["duration"] > 0:
                result[f"技能{i + 1}持续"] = data["levels"][i]["duration"]

            if (
                "description" in data["levels"][i].keys()
                and data["levels"][i]["description"] is not None
            ):
                result[f"技能{i + 1}描述"] = self.rts.compile(
                    BBKeyReplace().compile(
                        data["levels"][i]["description"],
                        data["levels"][i]["blackboard"],
                    )
                )
            else:
                result[f"技能{i + 1}描述"] = "-"

        return {k: str(v) for k, v in result.items()}

    async def generate_trap_text(self, key, value):
        content = parse("")

        title = value["name"]
        # 添加装置信息模板
        trap_info_template = Template("装置信息\n")
        content.append("==装置信息==\n")
        content.append(trap_info_template)

        for k, v in self.char_data_fill("", TRAP_DATA_PATH, value).items():
            trap_info_template.add(k, self.param_strip(v))

        filled_asset_data = await self.asset_data_fill(key)
        for k, v in filled_asset_data.items():
            trap_info_template.add(k, self.param_strip(v))

        # 添加装置技能部分
        content.append("\n==装置技能==\n")
        if value["skills"] and len(value["skills"]) > 0:
            if len(value["skills"]) > 1:
                content.append(
                    "'''{{color|red|该装置拥有多个技能，技能携带情况请查阅对应关卡！}}'''\n\n\n"
                )
            for i in range(0, len(value["skills"])):
                content.append(f"'''技能{i + 1}'''\n")
                skill_template = Template("装置技能\n")
                for k, v in self.skill_data_fill(
                    self.skill_data[value["skills"][i]["skillId"]]
                ).items():
                    skill_template.add(k, self.param_strip(v))
                content.append(skill_template)
        else:
            content.append("该装置无技能\n")

        # 添加出场关卡部分
        content.append("\n==出场关卡==\n")
        unveil_template = Template("装置出场关卡")
        if title != value["name"]:
            unveil_template.add(1, value["name"], showkey=False)
        content.append(unveil_template)

        # 添加 spine
        content.append("\n==装置模型==\n")
        spine_template = Template("spineId")
        spine_template.add("id", value["customed_trapid"])
        content.append(spine_template)

        def trapside():
            if filled_asset_data.get("阵营") is not None:
                return filled_asset_data.get("阵营") + "装置"
            else:
                return "我方装置"
        print(content)
        return {
            "name": value["name"].strip(),
            "pagetitle": title.strip(),
            "content": self.zip_enter(content).strip(),
            "trapid": key.strip(),
            "side": trapside(),
            "装置页面": "是" if value["name"] != title else None,
        }

    def edit_trap_page(self, value):
        title = value["pagetitle"]
        trapid = value["trapid"]
        content = value["content"]

        def safe_read(t: str) -> str:
            try:
                return self.wiki.read(t) or ""
            except Exception:
                return ""

        candidates: list[tuple[str, str]] = [
            (title, "main"),
            (f"{title}(装置)", "alt"),
            (f"{title}({trapid})", "unique"),
        ]

        for cand_title, kind in candidates:
            raw = safe_read(cand_title)

            if not raw:
                self.wiki.edit(
                    title=cand_title,
                    text=content,
                    summary="//Edit by bot.",
                    minor=True,
                )
                return

            code = parse(raw)

            if kind in ("main", "alt"):
                if has_template_in_text("装置信息", code):
                    code, changed = update_trap_template_ids(code, trapid)
                    if changed:
                        self.wiki.edit(
                            title=cand_title,
                            text=str(code),
                            summary="//Update ids by bot.",
                            minor=True,
                        )
                        return
                else:
                    continue

            if kind == "unique":
                self.wiki.edit(
                    title=cand_title,
                    text=content,
                    summary="//Edit by bot.",
                    minor=True,
                )
                return


    async def load_anon(self, client: Client, env: Environment):
        paths = [
            *await client.resolve_by_prefix("anon/"),
            *await client.resolve_by_prefix("refs/"),
        ]
        for path in paths:
            env.load_file(path, is_dependency=True)

    async def asset_data_fill(self, id):
        SCRIPT_SET = {
            "Trap",
            "MapDependentTrap",
            "BossHudTrap",
            "SandboxResTrap",
            "GiantTrap",
        }
        CATEGORY = {1: "默认", 2: "装置", 4: "障碍物"}
        SIDE = {0: "无阵营", 1: "我方", 2: "敌方", 4: "中立"}
        OPTION = {0: "否", 1: "是"}
        CARD_POLICY = {0: "默认", 1: "唯一", 2: "队列"}
        DEPLOY = {0: "无", 1: "部署于近战位", 2: "部署于远程位", 3: "部署于近战/远程位"}
        WITHDRAW = {0: "不可撤回", 1: "不可撤回", 2: "部署后可撤回", 3: "始终可撤回"}

        ab_list = {
            bundle
            for asset, bundle in self.client.asset_to_bundle.items()
            if asset.startswith("battle/prefabs/[uc]tokens/%s" % (id))
            # if asset.startswith("pkgrps/btl_pfb_tokens_i%s" % (id))
        }
        paths = await self.client.resolves(list(ab_list))
        ab_path = paths[0][1]
        env = UnityPy.load(ab_path)
        await self.load_anon(self.client, env)
        container_map = build_container_path(env)

        objs = list(filter(lambda obj: obj.type.name == "MonoBehaviour", env.objects))
        # print(asset.container)
        dyn_path = f"dyn/battle/prefabs/[uc]tokens/{id}.prefab"
        unanon_assets = cast(
            "list[ComponentPair[PPtr[MonoBehaviour]]]",
            self.asset_env.container[dyn_path].read().m_Component,
        )
        for pptr in unanon_assets:
            pptr_mono_behaviour = pptr.component.deref_parse_as_object()
            objs.append(pptr_mono_behaviour.object_reader)
        result = {}
        for obj in objs:
            # 先筛类型
            if (data := read_obj(MonoBehaviour, obj)) is None:
                continue
            if not data.m_Script:
                continue
            try:
                class_name = data.m_Script.read().m_ClassName
            except Exception:
                continue
            if class_name not in SCRIPT_SET:
                continue
            # 再筛装置名
            path = (
                container_map[obj.path_id]
                .replace("dyn/battle/prefabs/[uc]tokens/", "")
                .replace(".prefab", "")
            )
            if path != id:
                continue
            # workwork
            tree = obj.read_typetree()
            result["实体类型"] = CATEGORY[tree["_category"]]
            result["阵营"] = SIDE[tree["_sideType"]]
            result["阻挡半径"] = "{:.4f}".format(tree["_blockRadiusSquare"] ** 0.5)
            result["重写地块"] = OPTION[tree["_rewriteTileOptions"]]
            result["再部署策略"] = CARD_POLICY[tree["_cardPolicy"]]
            result["占用部署数"] = tree["_occupiedRemainingCharacterCnt"]
            result["部署条件"] = DEPLOY[tree["_buildCondition"]["buildableType"]]
            result["撤回策略"] = WITHDRAW[
                (tree["_withdrawable"] << 1) + tree["_ignoreParentWithdrawable"]
            ]
            return {k: str(v) for k, v in result.items()}
        return result

    async def _run(self):
        self.client: Client = await torappu_exporter(
            Version(res_version=self.resVersion, client_version=self.clientVersion),
            None,
            [],
            ["GameData"],
        )
        self.asset_env = self.get_unity_env()
        wikidata, existed_pages = self.get_wiki_traps()
        missing_traps = {
            key: value["name"].strip()
            for key, value in self.char_data.items()
            if key.startswith("trap_") and key not in wikidata
        }
        all_contents = []
        for trapid, trapname in missing_traps.items():
            all_contents.append(
                (await self.generate_trap_text(trapid, self.char_data[trapid]))
            )
        for value in all_contents:
            self.edit_trap_page(value)

        # 处理trapper部分
        self.wiki.edit(
            title="User:GuBot/temp/unwritetraps.json",
            text=json.dumps(
                list(dict.fromkeys([i["name"].strip() for i in all_contents])),
                ensure_ascii=False,
                indent=2,
            ),
            summary="//Edit by bot.",
        )
        trapsformat = {}
        for i in all_contents:
            temp = {"type": i["side"], "params": {}}
            if i["装置页面"]:
                temp["params"]["装置页面"] = "yes"
            trapsformat[i["name"]] = temp
        self.wiki.edit(
            title="User:GuBot/temp/trapsformat.json",
            text=json.dumps(trapsformat, ensure_ascii=False, indent=2),
            summary="//Edit by bot.",
        )

    def run(self):
        asyncio.run(self._run())