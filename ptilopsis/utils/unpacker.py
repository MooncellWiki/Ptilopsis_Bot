import json
from typing import TYPE_CHECKING

import requests
from retrying import retry

from ptilopsis.log import logger
from ptilopsis.utils.torappu import TorappuClient

if TYPE_CHECKING:
    from ptilopsis.config import Config


class Unpacker:
    """各服版本号的检查与记录。

    国服版本以 torappu 上「gamedata 已解包完成」的最新版本为准,这样官方刚推送
    但 torappu 还没解完的版本不会被误判成可用;海外服仍直接查官方 CDN。
    """

    def __init__(self, config: "Config", torappu: TorappuClient | None = None):
        self.ua = {
            "User-Agent": (
                "Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)"
            )
        }
        self.config = config.server_list
        self.torappu = torappu or TorappuClient(config.torappu_url)
        self.version_dir = config.version
        with open(self.version_dir) as f:
            self.version = json.load(f)
        logger.info(f"[CN VERSION]: {self.version['CN']['resVersion']}")
        self._version_dirty = False
        """内存中的版本号是否有尚未落盘的变更，见 get_version / commit_version。"""

    def check_update(self, region="CN"):
        local_version = self.version[region]["resVersion"]
        if local_version != self.get_version(region):
            logger.info(f"[{region} UPDATE] New version detected.")
            if region == "CN":
                logger.info(
                    self.config[region].update_msg.format(
                        self.version[region]["clientVersion"],
                        self.version[region]["resVersion"],
                    )
                )
            return True
        return False

    def check_all_update(self):
        flag = False
        for r in self.config:
            if r != "CN":
                logger.info(f"Start to check {r} server.")
                flag ^= self.check_update(region=r)
        return flag

    def get_version(self, region="CN"):
        """拉取远端版本号，只更新内存状态，落盘需显式调用 commit_version()。

        推迟落盘是为了避免「版本号已推进但后续步骤失败」时状态被写死：
        下一次运行会因为本地版本已等于远端而误判为无更新，从而静默跳过一轮更新。
        """
        if region == "CN":
            return self._get_version_torappu(region)
        return self._get_version_official(region)

    def _get_version_torappu(self, region: str) -> str:
        """国服:torappu 上 gamedata 已就绪的最新版本(funcVer 不再维护)。"""
        latest = self.torappu.latest_version()
        self.version[region]["resVersion"] = latest.res_version
        self.version[region]["clientVersion"] = latest.client_version
        self._version_dirty = True
        return latest.res_version

    @retry(stop_max_attempt_number=3)
    def _get_version_official(self, region: str) -> str:
        """海外服:官方 CDN 的 version 与 network_config。"""
        version = self.version
        # version
        url = self.config[region].config_url + "Android/version"
        # url += f'?sign={int(time.time())}'
        ret1 = requests.get(url, headers=self.ua).json()
        version[region]["resVersion"] = ret1["resVersion"]
        version[region]["clientVersion"] = ret1["clientVersion"]
        # network_config
        url = self.config[region].config_url + "network_config"
        ret2 = requests.get(url, headers=self.ua).json()
        ret2 = json.loads(ret2["content"])
        if ret2["funcVer"] != version[region]["funcVer"]:
            logger.info(f"{region} server network config update to {ret2['funcVer']}.")
        version[region]["funcVer"] = ret2["funcVer"]

        self.version = version
        self._version_dirty = True
        return ret1["resVersion"]

    def commit_version(self):
        """把内存中的版本号写回 version_*.json；无待落盘变更时为空操作。"""
        if not self._version_dirty:
            return
        with open(self.version_dir, "w") as f:
            json.dump(self.version, f, indent=4)
        self._version_dirty = False
