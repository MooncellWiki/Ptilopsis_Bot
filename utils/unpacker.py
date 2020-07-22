import io
import os
import zipfile

import requests
import unitypack
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Unpacker:
    def __init__(self, config):
        self.ua = {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)'}
        self.config = config
        self.version = {}
        self.HotUpdateList = {}

    def getVersion(self, region):
        if region in self.version:
            return self.version[region]['resVersion']
        if not self._checkRegion(region):
            print('wrong region\n only support ' + ' '.join(self.config['serverList'].keys()))
            return
        r = None
        if len(self.config["serverList"][region]["baseUrl"]) != 0:
            r = requests.get(self.config["serverList"][region]["baseUrl"] + 'version', headers=self.ua).json()
        else:
            r = requests.get(self.config["serverList"][region]["url"] + 'version', headers=self.ua).json()
        self.version[region] = r
        return r['resVersion']

    def _checkRegion(self, region):
        return region in self.config['serverList']

    def getHotUpdateListFile(self, region, res_version=''):
        if region in self.HotUpdateList:
            return self.HotUpdateList[region]
        if not self._checkRegion(region):
            print('wrong region\n only support ' + ' '.join(self.config['serverList'].keys()))
            return
        if len(res_version) == 0:
            res_version = self.getVersion(region)
        r = requests.get(
            "{0}assets/{1}/hot_update_list.json".format(self.config['serverList'][region]['url'], res_version),
            headers=self.ua).json()
        self.HotUpdateList[region] = r
        return r

    def getAB(self, path, region, res_version=''):
        if not self._checkRegion(region):
            print('wrong region\n only support ' + ' '.join(self.config['serverList'].keys()))
            return
        if len(res_version) == 0:
            res_version = self.getVersion(region)
        dir = os.path.dirname(path)
        no_postfix = os.path.splitext(os.path.split(path)[-1])[0]
        r = requests.get(
            "{0}assets/{1}/{2}_{3}.dat".format(self.config['serverList'][region]['url'], res_version,
                                               dir.replace('/', '_'),
                                               no_postfix),
            headers=self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall('./ab/' + self.config['serverList'][region]["folder"])

    def UnpackGameData(self, path, region):
        with open(os.path.join('./ab', self.config['serverList'][region]['folder'], 'gamedata', path), 'rb')as f:
            bundle = unitypack.load(f)
            count = 0
            dataArr = []
            for asset in bundle.assets:
                for id, obj in asset.objects.items():
                    if obj.type == 'TextAsset':
                        count += 1
                        dataArr.append(obj.read())
            if count == 1:
                dirpath = \
                    os.path.split(
                        os.path.join('./gamedata', self.config['serverList'][region]['folder'], 'gamedata', path))[0]
            else:
                dirpath = \
                    os.path.splitext(
                        os.path.join('./gamedata', self.config['serverList'][region]['folder'], 'gamedata', path))[0]
            os.makedirs(dirpath, exist_ok=True)
            dists = []
            for data in dataArr:
                if data.name.endswith('.lua'):
                    is_sign = self.config["serverList"][region]['luaSign']
                else:
                    is_sign = self.config["serverList"][region]['tableSign']
                decrypted = self._CrypticConverter_A(data.script,
                                                     bytes(self.config['serverList'][region]['chatMask'],
                                                           encoding='utf-8'),
                                                     is_sign)
                with open(os.path.join(dirpath, data.name if data.name.find('.') != -1 else data.name + '.json'),
                          'wb') as dist:
                    dist.write(decrypted)
                    dists.append(os.path.join(dirpath, data.name if data.name.find('.') != -1 else data.name + '.json'))
            return dists

    @staticmethod
    def _CrypticConverter_A(data, key, is_sign=True):
        if is_sign:
            data = data[128:]
        iv = key[16:]
        key = key[0:16]
        cipher = AES.new(iv=iv, key=key, mode=AES.MODE_CBC)
        decrypted = bytearray(unpad(cipher.decrypt(data), 16, 'pkcs7')[16:])
        for i in range(16):
            decrypted[i] ^= iv[i]
        return decrypted
