import io
import json
import os
import time
import zipfile

import requests
import unitypack
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from retrying import retry


class UnpackerCN:
    def __init__(self, config):
        self.ua = {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)'}
        self.config = config['serverList']['cn']
        self.config_global = config['serverList']
        with open('./version.json', 'r') as f:
            self.res_version = json.load(f)['cn']['resVersion']
        self.hot_update_list = {'abInfos': []}
        print('Current local CN version:', self.res_version)

    def check_update(self):
        local_version = self.res_version
        if local_version != self.get_version():
            print('New version detect. Start to update gamedata.')
            self.get_update_list()
            self.get_all_gamedata()
            print('Finish download all gamedata AB.')
            self.unpack_all_gamedata()
            print('Finish decrypt all gamedata.')
            print('Current local CN version:', self.res_version)
            return True
        return False

    @retry(stop_max_attempt_number=3)
    def get_version(self):
        # url = self.config['baseUrl'] + 'version?sign={}'.format(int(time.time()))
        url = self.config['baseUrl'] + 'version'
        ret = requests.get(url, headers=self.ua).json()
        self.res_version = ret['resVersion']

        with open('./version.json', 'r') as f:
            version = json.load(f)
        version['cn']['resVersion'] = ret['resVersion']
        version['cn']['clientVersion'] = ret['clientVersion']
        with open('./version.json', 'w') as f:
            json.dump(version, f, indent=4)
        return ret['resVersion']

    @retry(stop_max_attempt_number=3)
    def check_version_global(self):
        with open('./version.json', 'r') as f:
            version = json.load(f)
        for region in self.config_global:
            url = self.config_global[region]['baseUrl'] + 'version'
            ret = requests.get(url, headers=self.ua).json()
            version[region]['resVersion'] = ret['resVersion']
            version[region]['clientVersion'] = ret['clientVersion']
            print(self.config_global[region]['updateMsg'].format(ret['clientVersion'], ret['resVersion']))

            url = self.config_global[region]['baseUrl'].replace('Android/', 'network_config')
            ret = requests.get(url, headers=self.ua).json()
            network_config = json.loads(ret['content'])
            if network_config['funcVer'] != version[region]['funcVer']:
                print(f"{region.upper()} server network config update to {network_config['funcVer']}")
                version[region]['funcVer'] = network_config['funcVer']
        with open('./version.json', 'w') as f:
            json.dump(version, f, indent=4)

    @retry(stop_max_attempt_number=3)
    def get_update_list(self):
        res_version = self.res_version
        ret = requests.get("{}assets/{}/hot_update_list.json".format(self.config['url'], res_version),
                           headers=self.ua).json()
        self.hot_update_list = ret
        return ret

    def get_ab(self, path):
        res_version = self.res_version
        dir = os.path.dirname(path)
        no_postfix = os.path.splitext(os.path.split(path)[-1])[0]
        url = "{0}assets/{1}/{2}_{3}.dat".format(
            self.config['url'],
            res_version,
            dir.replace('/', '_'),
            no_postfix.replace('#', '__')
        )
        r = requests.get(url, headers=self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall('./UnpackerCN/ab/')
        print(f'download: {path}')

    def get_all_gamedata(self):
        res_version = self.res_version
        hot_update_list = self.hot_update_list

        for ab_info in filter(lambda x: x['name'].startswith('gamedata'), hot_update_list['abInfos']):
            dir = os.path.dirname(ab_info['name'])
            no_postfix = os.path.splitext(os.path.split(ab_info['name'])[-1])[0]
            url = "{0}assets/{1}/{2}_{3}.dat".format(
                self.config['url'],
                res_version,
                dir.replace('/', '_'),
                no_postfix.replace('#', '__')
            )
            r = requests.get(url, headers=self.ua)
            zipfile.ZipFile(io.BytesIO(r.content)).extractall('./UnpackerCN/ab/')
            print(f"download: {ab_info['name']}")

    def unpack_all_gamedata(self):
        hot_update_list = self.hot_update_list

        for ab_info in filter(lambda x: x['name'].startswith('gamedata'), hot_update_list['abInfos']):
            self.unpack_data(ab_info['name'])

    def unpack_data(self, path):
        with open(os.path.join('./UnpackerCN/ab', path), 'rb') as f:
            bundle = unitypack.load(f)
            dataArr = []
            path_list = []
            for asset in bundle.assets:
                for id, obj in asset.objects.items():
                    if obj.type == 'TextAsset':
                        dataArr.append((obj.read(), obj.path_id))
                    elif obj.type == 'AssetBundle':
                        path_list.extend(obj.read()['m_Container'])
            path_dict = {x[1]['asset'].path_id: x[0] for x in path_list}

            dir_set = set()
            dists = []
            for data, data_path_id in dataArr:
                ori_path = path_dict[data_path_id]
                full_path = os.path.join('./UnpackerCN', ori_path[ori_path.find('gamedata'):])
                dir_path = os.path.dirname(full_path)
                if dir_path not in dir_set:
                    os.makedirs(dir_path, exist_ok=True)
                    dir_set.add(dir_path)

                if full_path.endswith('.bytes'):
                    if full_path.endswith('.lua.bytes'):
                        full_path = full_path[:-6]
                    else:
                        full_path = full_path[:-6] + '.json'
                    is_sign = True if '/levels/' not in full_path else False
                    script = self._CrypticConverter_A(data.script,
                                                      bytes(self.config['chatMask'], encoding='utf-8'), is_sign)
                    with open(full_path, 'wb') as dist:
                        dist.write(script)
                        dists.append(full_path)
                else:
                    script = data.script
                    with open(full_path, 'w') as dist:
                        dist.write(script)
                        dists.append(full_path)
            return dists

    @staticmethod
    def _CrypticConverter_A(data, key, is_sign=True):
        if is_sign:
            data = data[128:]
        iv = key[16:]
        key = key[0:16]
        cipher = AES.new(iv=iv, key=key, mode=AES.MODE_CBC)
        # decrypted = bytearray(unpad(cipher.decrypt(data), 16, 'pkcs7')[16:])
        # for i in range(16):
        #     decrypted[i] ^= iv[i]
        decrypted = bytearray(cipher.decrypt(data)[16:])
        for i in range(16):
            decrypted[i] ^= iv[i]
        decrypted = unpad(decrypted, 16, 'pkcs7')
        return decrypted
