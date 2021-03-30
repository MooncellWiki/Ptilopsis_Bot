import json
import os

from utils.unpacker import Unpacker


class GameData:
    def __init__(self, config, source='Unpacker'):
        self.data = {}
        self.source = source
        self.config = config
        print(f"start with {self.source} mode")
        if self.source == 'Unpacker':
            self.unpacker = Unpacker(config)

    def get(self, path, region):
        r = region.lower() if self._source() != 'Unpacker' else region.upper()
        fullpath = os.path.join(self._source(), self.config['serverList'][r]['folder'], 'gamedata', path)
        if fullpath in self.data:
            return self.data[fullpath]
        else:
            if self._source() == 'Unpacker' and not os.path.exists(fullpath):
                if 'excel' not in path:
                    self.unpacker.config[region]['files'] = 'gamedata'
                self.unpacker.get_all_ab(region)
                self.unpacker.unpack_all_data(region)
            with open(fullpath, 'r', encoding='utf-8') as file:
                data = json.loads(file.read())
                if 'excel' in fullpath:
                    self.data[fullpath] = data
                return data

    def get_txt(self, path, region):
        r = region.lower() if self._source() != 'Unpacker' else region.upper()
        fullpath = os.path.join(self._source(), self.config['serverList'][r]['folder'], 'gamedata', path)
        with open(fullpath, 'r', encoding='utf-8') as file:
            text = file.read()
            return text

    def _source(self):
        return self.source
