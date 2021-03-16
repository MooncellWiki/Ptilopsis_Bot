import json
import os
from utils.unpacker_cn import UnpackerCN


class GameData:
    def __init__(self, config, source='ArknightsGameData'):
        self.data = {}
        self.source = source
        self.config = config
        print('start with ' + self.source + ' mode')
        if self.source == 'UnpackerCN':
            self.unpacker = UnpackerCN(config['unpacker'])

    def get(self, path, region):
        if self._source() == 'UnpackerCN':
            fullpath = os.path.join(self._source(), 'gamedata', path)
        elif self._source() == 'UnpackerData':
            fullpath = os.path.join(self._source(), path)
            if path == 'levels/enemydata/enemy_database.json':
                fullpath = os.path.join(self._source(), 'levels/enemy_database.json')
        else:
            fullpath = os.path.join(self._source(), self.config['unpacker']['serverList'][region]['folder'], 'gamedata',
                path)
        if fullpath in self.data:
            return self.data[fullpath]
        else:
            with open(fullpath, 'r', encoding = 'utf-8') as file:
                data = json.loads(file.read())
                if 'excel' in fullpath:
                    self.data[fullpath] = data
                return data

    def get_txt(self, path, region):
        # fullpath = os.path.join(self._source(), self.config['unpacker']['serverList'][region]['folder'], 'gamedata',
        #     path)
        if self._source() == 'UnpackerCN':
            fullpath = os.path.join(self._source(), 'gamedata', path)
        else:
            fullpath = os.path.join('ArknightsGameData', self.config['unpacker']['serverList'][region]['folder'],
                'gamedata', path)
        with open(fullpath, 'r', encoding = 'utf-8') as file:
            text = file.read()
            return text

    def _source(self):
        return self.source
