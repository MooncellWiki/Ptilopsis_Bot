import bson
import io
import json
import time
import os
import zipfile
import hashlib
import requests
import unitypack
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from retrying import retry


class Unpacker:
    def __init__(self, config, region='CN'):
        self.ua = {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 6.0.1; vivo X9L Build/MMB29M)'}
        self.config = config['serverList']
        self.version_dir = config['version']
        with open(self.version_dir, 'r') as f:
            self.version = json.load(f)
        print(f"[{region} VERSION]: {self.version[region]['resVersion']}")
        self.hot_update_list = {}

    def check_update(self, region='CN'):
        local_version = self.version[region]['resVersion']
        if local_version != self.get_version(region):
            print(f"[{region} UPDATE] New version detected. Start to update.")
            self.get_update_list(region)
            self.get_all_ab(region)
            print('Finish download all AB.')
            self.unpack_all_data(region)
            print('Finish decrypt all gamedata.')
            print(self.config[region]['updateMsg'].format(self.version[region]['clientVersion'],
                                                          self.version[region]['resVersion']))
            return True
        return False

    def check_all_update(self):
        flag = False
        for r in self.config:
            if r != 'CN':
                print(f"Start to check {r} server.")
                flag ^= self.check_update(region=r)
        return flag

    @retry(stop_max_attempt_number=3)
    def get_version(self, region='CN'):
        with open(self.version_dir, 'r') as f:
            version = json.load(f)
        # version
        url = self.config[region]['configUrl'] + 'Android/version'
        # url += f'?sign={int(time.time())}'
        ret1 = requests.get(url, headers=self.ua).json()
        version[region]['resVersion'] = ret1['resVersion']
        version[region]['clientVersion'] = ret1['clientVersion']
        # network_config
        url = self.config[region]['configUrl'] + 'network_config'
        ret2 = requests.get(url, headers=self.ua).json()
        ret2 = json.loads(ret2['content'])
        if ret2['funcVer'] != version[region]['funcVer']:
            print(f"{region} server network config update to {ret2['funcVer']}.")
        version[region]['funcVer'] = ret2['funcVer']

        self.version = version
        with open(self.version_dir, 'w') as f:
            json.dump(version, f, indent=4)
        return ret1['resVersion']

    @retry(stop_max_attempt_number=3)
    def get_update_list(self, region='CN'):
        res_version = self.version[region]['resVersion']
        os.makedirs(os.path.join('Unpacker', self.config[region]['folder']), exist_ok=True)
        dir = os.path.join('Unpacker', self.config[region]['folder'], 'hot_update_list.json')
        url = "{}assets/{}/hot_update_list.json".format(self.config[region]['resUrl'], res_version)
        ret = requests.get(url, headers=self.ua).json()
        with open(dir, 'w') as f:
            json.dump(ret, f, indent=4)
        self.hot_update_list[region] = ret
        return ret

    def get_all_ab(self, region='CN'):
        if region not in self.hot_update_list:
            self.get_update_list(region=region)
        hot_update_list = self.hot_update_list[region]

        for ab_info in filter(lambda x: x['name'].startswith(self.config[region]['files']), hot_update_list['abInfos']):
            if not self.compare_ab_md5(md5=ab_info['md5'], path=ab_info['name'], region=region):
                self.get_ab(path=ab_info['name'], region=region)

    @retry(stop_max_attempt_number=3)
    def get_ab(self, path, region='CN'):
        res_version = self.version[region]['resVersion']
        dir = os.path.dirname(path)
        no_postfix = os.path.splitext(os.path.split(path)[-1])[0]
        url = "{0}assets/{1}/{2}_{3}.dat".format(
            self.config[region]['resUrl'],
            res_version,
            dir.replace('/', '_'),
            no_postfix.replace('#', '__')
        )
        r = requests.get(url, headers=self.ua)
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(f"./Unpacker/{self.config[region]['folder']}/ab/")
        print(f"download: {path}")

    def compare_ab_md5(self, md5, path, region='CN'):
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

    def unpack_all_data(self, region='CN'):
        if region not in self.hot_update_list:
            self.get_update_list(region=region)
        hot_update_list = self.hot_update_list[region]

        for ab_info in filter(lambda x: x['name'].startswith(self.config[region]['files']), hot_update_list['abInfos']):
            try:
                self.unpack_data(ab_info['name'], region=region)
            except:
                print(f"Unpack {ab_info['name']} fail.")

    def unpack_data(self, path, region='CN'):
        ab_dir = os.path.join(f"./Unpacker/{self.config[region]['folder']}/ab", path)
        if not os.path.exists(ab_dir):
            self.get_ab(path=path, region=region)
        with open(ab_dir, 'rb') as f:
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
            fbs_flag = 'enableFlatBuffers' in self.config[region] and self.config[region]['enableFlatBuffers']
            if fbs_flag:
                os.makedirs(f"./Unpacker/{self.config[region]['folder']}/flatbuffers", exist_ok=True)
            for data, data_path_id in dataArr:
                ori_path = path_dict[data_path_id]
                full_path = os.path.join(f"./Unpacker/{self.config[region]['folder']}",
                                         ori_path[ori_path.find('gamedata'):])
                dir_path = os.path.dirname(full_path)
                if dir_path not in dir_set:
                    os.makedirs(dir_path, exist_ok=True)
                    dir_set.add(dir_path)

                if full_path.endswith('.bytes'):
                    if full_path.endswith('.lua.bytes'):
                        full_path = full_path[:-6]
                    else:
                        full_path = full_path[:-6] + '.json'
                    # is_sign = True if '/levels/' not in full_path else False
                    if fbs_flag:
                        fbs_name = None
                        fbs_path = f"./Unpacker/{self.config[region]['folder']}/flatbuffers"
                        for k in self.config[region]['flatBuffers']:
                            if k in full_path:
                                fbs_name = k
                                continue
                        if fbs_name is not None:
                            with open(f"{fbs_path}/{fbs_name}.bytes", mode='wb') as f:
                                f.write(bytes(data.script)[128:])
                            os.system(f"flatc.exe -o {fbs_path} --no-warnings --json --strict-json --natural-utf8 --defaults-json --raw-binary ./OpenArknightsFBS/FBS/{fbs_name}.fbs -- {fbs_path}/{fbs_name}.bytes")
                            with open(f"{fbs_path}/{fbs_name}.json", mode='r', encoding='utf-8') as f:
                                jsons = json.loads(f.read())
                                if fbs_name == 'activity_table':
                                    for (k_act, v_act) in jsons['dynActs'].items():
                                        if 'base64' in v_act:
                                            jsons['dynActs'][k_act] = bson.decode(base64.b64decode(v_act['base64']))
                            with open(f"{os.path.dirname(full_path)}/{fbs_name}.json", mode='w', encoding='utf-8') as f:
                                f.write(json.dumps(jsons, indent=2, ensure_ascii=False))
                            continue
                    if '/levels/' not in full_path:
                        is_sign = True
                        script = self._CrypticConverter_A(data.script,
                                                          bytes(self.config[region]['chatMask'], encoding='utf-8'), is_sign)
                        try:
                            file_content = json.dumps(bson.decode(script), indent=2, ensure_ascii=False)
                            with open(full_path, 'w') as dist:
                                dist.write(file_content)
                                dists.append(full_path)
                        except:
                            with open(full_path, 'wb') as dist:
                                dist.write(script)
                                dists.append(full_path)
                    else:
                        try:
                            script = data.script[128:]
                            file_content = json.dumps(bson.decode(script), indent=2, ensure_ascii=False)
                            with open(full_path, 'w') as dist:
                                dist.write(file_content)
                                dists.append(full_path)
                        except:
                            is_sign = False
                            script = self._CrypticConverter_A(data.script,
                                                              bytes(self.config[region]['chatMask'], encoding='utf-8'), is_sign)
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
