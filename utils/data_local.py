import json
import os


class GameData:
    def __init__(self, config, source='ArknightsGameData'):
        self.data = {}
        self.source = source
        self.config = config

    def get(self, path, region):
        fullpath = os.path.join(self._source(), self.config['unpacker']['serverList'][region]['folder'], 'gamedata',
                                path)
        if fullpath in self.data:
            return self.data[fullpath]
        else:
            with open(fullpath, 'r', encoding = 'utf-8') as file:
                data = json.loads(file.read())
                self.data[fullpath] = data
                return data

    def get_txt(self, path, region):
        fullpath = os.path.join(self._source(), self.config['unpacker']['serverList'][region]['folder'], 'gamedata',
                                path)
        with open(fullpath, 'r', encoding = 'utf-8') as file:
            text = file.read()
            return text

    def _source(self):
        return self.source
