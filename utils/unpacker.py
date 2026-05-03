import io
import json
import time
import os
import zipfile
import hashlib
import requests
from retrying import retry


class Unpacker:
    def __init__(self, config, region="CN"):
        self.ua = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)"
        }
        self.config = config["serverList"]
        self.version_dir = config["version"]
        with open(self.version_dir, "r") as f:
            self.version = json.load(f)
        print(f"[{region} VERSION]: {self.version[region]['resVersion']}")
        self.hot_update_list = {}
        self.manifest_idx = {}

    def check_update(self, region="CN"):
        local_version = self.version[region]["resVersion"]
        if local_version != self.get_version(region):
            if region == "CN":
                print(f"[{region} UPDATE] New version detected. Start to update.")
                self.get_update_list(region)
                self.load_idx(region)
                # self.get_all_ab(region)
                # print('Finish download all AB.')
                print(
                    self.config[region]["updateMsg"].format(
                        self.version[region]["clientVersion"],
                        self.version[region]["resVersion"],
                    )
                )
            else:
                print(f"[{region} UPDATE] New version detected.")
            return True
        return False

    def check_all_update(self):
        flag = False
        for r in self.config:
            if r != "CN":
                print(f"Start to check {r} server.")
                flag ^= self.check_update(region=r)
        return flag

    @retry(stop_max_attempt_number=3)
    def get_version(self, region="CN"):
        with open(self.version_dir, "r") as f:
            version = json.load(f)
        # version
        url = self.config[region]["configUrl"] + "Android/version"
        # url += f'?sign={int(time.time())}'
        ret1 = requests.get(url, headers=self.ua).json()
        version[region]["resVersion"] = ret1["resVersion"]
        version[region]["clientVersion"] = ret1["clientVersion"]
        # network_config
        url = self.config[region]["configUrl"] + "network_config"
        ret2 = requests.get(url, headers=self.ua).json()
        ret2 = json.loads(ret2["content"])
        if ret2["funcVer"] != version[region]["funcVer"]:
            print(f"{region} server network config update to {ret2['funcVer']}.")
        version[region]["funcVer"] = ret2["funcVer"]

        self.version = version
        with open(self.version_dir, "w") as f:
            json.dump(version, f, indent=4)
        return ret1["resVersion"]

    @retry(stop_max_attempt_number=3)
    def get_update_list(self, region="CN"):
        res_version = self.version[region]["resVersion"]
        os.makedirs(
            os.path.join("Unpacker", self.config[region]["folder"]), exist_ok=True
        )
        dir = os.path.join(
            "Unpacker", self.config[region]["folder"], "hot_update_list.json"
        )
        url = "{}assets/{}/hot_update_list.json".format(
            self.config[region]["resUrl"], res_version
        )
        ret = requests.get(url, headers=self.ua).json()
        with open(dir, "w") as f:
            json.dump(ret, f, indent=4)
        self.hot_update_list[region] = ret
        return ret

    def load_idx(self, region="CN"):
        if "manifestName" not in self.hot_update_list[region]:
            return
        idx_path = self.hot_update_list[region]["manifestName"]
        url = "{0}assets/{1}/{2}.dat".format(
            self.config[region]["resUrl"],
            self.version[region]["resVersion"],
            idx_path[:-4],
        )
        r = requests.get(url, headers=self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(
            f"./Unpacker/{self.config[region]['folder']}/ab/"
        )
        fbs_path = f"./Unpacker/{self.config[region]['folder']}/flatbuffers"
        os.makedirs(
            f"./Unpacker/{self.config[region]['folder']}/flatbuffers", exist_ok=True
        )
        with open(
            f"./Unpacker/{self.config[region]['folder']}/ab/{idx_path}", "rb"
        ) as f:
            data = f.read()
        with open(f"{fbs_path}/ResourceManifest.bytes", mode="wb") as f:
            f.write(bytes(data)[128:])
        os.system(
            f"{os.path.join('.', 'flatc')} -o {fbs_path} --no-warnings --json --strict-json --natural-utf8 --defaults-json --raw-binary ./ResourceManifest.fbs -- {fbs_path}/ResourceManifest.bytes"
        )
        with open(f"{fbs_path}/ResourceManifest.json", mode="r", encoding="utf-8") as f:
            jsons = json.loads(f.read())
        gamedata_idx = {"bundleToAsset": {}, "assetToBundle": {}}
        for asset in jsons["assetToBundleList"]:
            if asset["assetName"].startswith("gamedata"):
                gamedata_idx["assetToBundle"][asset["assetName"]] = jsons["bundles"][
                    asset["bundleIndex"]
                ]["name"]
                if (
                    jsons["bundles"][asset["bundleIndex"]]["name"]
                    not in gamedata_idx["bundleToAsset"]
                ):
                    gamedata_idx["bundleToAsset"][
                        jsons["bundles"][asset["bundleIndex"]]["name"]
                    ] = []
                gamedata_idx["bundleToAsset"][
                    jsons["bundles"][asset["bundleIndex"]]["name"]
                ].append(asset["assetName"])
        with open(
            f"./Unpacker/{self.config[region]['folder']}/idx.json",
            mode="w",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(gamedata_idx, indent=2, ensure_ascii=False))
            self.manifest_idx = gamedata_idx

    def get_all_ab(self, region="CN"):
        if region not in self.hot_update_list:
            self.get_update_list(region=region)
        hot_update_list = self.hot_update_list[region]

        for ab_info in filter(
            lambda x: (
                x["name"].startswith(self.config[region]["files"])
                or x["name"] in self.manifest_idx["bundleToAsset"]
            ),
            hot_update_list["abInfos"],
        ):
            if not self.compare_ab_md5(
                md5=ab_info["md5"], path=ab_info["name"], region=region
            ):
                self.get_ab(path=ab_info["name"], region=region)

    @retry(stop_max_attempt_number=3)
    def get_ab(self, path, region="CN"):
        res_version = self.version[region]["resVersion"]
        dir = os.path.dirname(path)
        no_postfix = os.path.splitext(os.path.split(path)[-1])[0]
        url = "{0}assets/{1}/{2}_{3}.dat".format(
            self.config[region]["resUrl"],
            res_version,
            dir.replace("/", "_"),
            no_postfix.replace("#", "__"),
        )
        r = requests.get(url, headers=self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(
            f"./Unpacker/{self.config[region]['folder']}/ab/"
        )
        print(f"download: {path}")

    def compare_ab_md5(self, md5, path, region="CN"):
        ab_dir = os.path.join(f"./Unpacker/{self.config[region]['folder']}/ab", path)
        if not os.path.exists(ab_dir):
            return False
        with open(ab_dir, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        if file_hash.hexdigest() != md5:
            return False
        else:
            return True
