import json
import os
from typing import TYPE_CHECKING

from ptilopsis.log import logger
from ptilopsis.utils.unpacker import Unpacker

if TYPE_CHECKING:
    from ptilopsis.config import Config


class GameData:
    def __init__(self, config: "Config", source="Unpacker"):
        self.data = {}
        self.source = source
        self.config = config
        logger.info(f"start with {self.source} mode")
        self.unpacker = Unpacker(config)
        self.source_YoStar = "thirdparty/ArknightsGameData_YoStar"

    def get(self, path, region):
        # r = region.lower() if self._source(region) != 'Unpacker' else region.upper()
        r = region
        fullpath = os.path.join(
            self._source(region),
            self.config.server_list[r].folder,
            "gamedata",
            path,
        )
        if fullpath in self.data:
            return self.data[fullpath]
        else:
            if self._source(region) == "Unpacker" and not os.path.exists(fullpath):
                if "excel" not in path:
                    self.unpacker.config[region].files = "gamedata"
                if region == "CN":
                    self.unpacker.get_version(region)
                    self.unpacker.get_update_list(region)
                    self.unpacker.load_idx(region)
                    self.unpacker.get_all_ab(region)
                    self.unpacker.unpack_all_data(region)
                    # 数据确实解包落盘后再推进版本号，避免中途失败留下假的「已是最新」
                    self.unpacker.commit_version()
            with open(fullpath, encoding="utf-8") as file:
                data = json.loads(file.read())
                if "excel" in fullpath:
                    self.data[fullpath] = data
                return data

    def get_txt(self, path, region):
        # r = region.lower() if self._source(region) != 'Unpacker' else region.upper()\
        r = region
        fullpath = os.path.join(
            self._source(region),
            self.config.server_list[r].folder,
            "gamedata",
            path,
        )
        with open(fullpath, encoding="utf-8") as file:
            text = file.read()
            return text

    def _source(self, region):
        if region == "CN" or region == "TW":
            return self.source
        else:
            return self.source_YoStar
