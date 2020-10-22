import io
import os
import time
import zipfile
import json

import requests
import unitypack
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class UnpackerCN:
    def __init__(self, config, update = True):
        self.ua = {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)'}
        self.config = config['serverList']['cn']
        with open('./version.json', 'r') as f:
            self.res_version = json.load(f)['cn']['resVersion']
        with open('./UnpackerCN/hot_update_list.json', 'r') as f:
            self.hot_update_list = json.load(f)
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

    def get_version(self):
        url = self.config['baseUrl'] + 'version?sign={}'.format(int(time.time()))
        ret = requests.get(url, headers = self.ua).json()
        self.res_version = ret['resVersion']

        with open('./version.json', 'r') as f:
            ori_ver = json.load(f)
        ori_ver['cn'] = ret
        with open('./version.json', 'w') as f:
            json.dump(ori_ver, f, indent = 4)
        return ret['resVersion']

    def get_update_list(self):
        res_version = self.res_version
        ret = requests.get("{}assets/{}/hot_update_list.json".format(self.config['url'], res_version),
            headers = self.ua).json()
        self.hot_update_list = ret
        with open('./UnpackerCN/hot_update_list.json', 'w') as f:
            json.dump(ret, f, indent = 4)
        return ret

    def get_ab(self, path):
        res_version = self.res_version
        dir = os.path.dirname(path)
        no_postfix = os.path.splitext(os.path.split(path)[-1])[0]
        r = requests.get(
            "{0}assets/{1}/{2}_{3}.dat".format(self.config['url'], res_version, dir.replace('/', '_'), no_postfix),
            headers = self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall('./UnpackerCN/ab/')

    def get_all_gamedata(self):
        res_version = self.res_version
        hot_update_list = self.hot_update_list

        for ab_info in filter(lambda x: x['name'].startswith('gamedata'), hot_update_list['abInfos']):
            dir = os.path.dirname(ab_info['name'])
            no_postfix = os.path.splitext(os.path.split(ab_info['name'])[-1])[0]
            r = requests.get(
                "{0}assets/{1}/{2}_{3}.dat".format(self.config['url'], res_version, dir.replace('/', '_'), no_postfix),
                headers = self.ua)
            zipfile.ZipFile(io.BytesIO(r.content)).extractall('./UnpackerCN/ab/')

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
                dir_path = os.path.split(full_path)[0]
                if dir_path not in dir_set:
                    os.makedirs(dir_path, exist_ok = True)
                    dir_set.add(dir_path)

                if full_path.endswith('.bytes'):
                    if full_path.endswith('.lua.bytes'):
                        full_path = full_path[:-6]
                    else:
                        full_path = full_path[:-6] + '.json'
                    is_sign = True if '/levels/' not in full_path else False
                    script = self._CrypticConverter_A(data.script,
                        bytes(self.config['chatMask'], encoding = 'utf-8'), is_sign)
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
        cipher = AES.new(iv = iv, key = key, mode = AES.MODE_CBC)
        decrypted = bytearray(unpad(cipher.decrypt(data), 16, 'pkcs7')[16:])
        for i in range(16):
            decrypted[i] ^= iv[i]
        return decrypted
