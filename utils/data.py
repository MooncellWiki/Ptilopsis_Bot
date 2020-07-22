import copy
import json
import os

import git

from utils.unpacker import Unpacker


class GameData:
    def __init__(self, config):
        self.data = {}
        self.source = config['source']
        self.config = config
        print('start with ' + self.source + ' mode')
        if config['source'] == 'repo':
            if os.path.exists('./repo/.git'):
                repo = git.Repo('./repo/')
                print('repo already exist')
            else:
                if not os.path.exists('./repo'):
                    os.mkdir('repo')
                print('start clone ' + config['repo'])
                repo = git.Repo.clone_from(url=config['repo'], to_path='repo', multi_options=["--depth 1"])
            print('start pull')
            repo.remote('origin').pull()
            print('pull finished')
        else:
            self.unpacker = Unpacker(config['unpacker'])
            print('国服当前版本:' + self.unpacker.getVersion('cn'))

    def get(self, path, region):
        fullpath = os.path.join(self._source(), self.config['unpacker']['serverList'][region]['folder'], 'gamedata',
                                path)
        if fullpath in self.data:
            return copy.deepcopy(self.data[fullpath])
        else:
            if self.source == 'unpacker' and not os.path.exists(path):
                self.unpacker.getAB("gamedata/" + path, region)
                self.unpacker.UnpackGameData(path, region)
            with open(fullpath, 'r', encoding='utf-8') as file:
                data = json.loads(file.read())
                self.data[fullpath] = data
                return copy.deepcopy(data)

    def _source(self):
        return './repo' if self.source == 'repo' else './gamedata'
