from utils.job import Job
import time

class NewModule(Job):
    def _run(self):
        module_table = self.getgd('excel/uniequip_table')
        character_table = self.getgd('excel/character_table.json')
        
        latest_modules_tracks = []
        max_track_limit = 8
        for track in module_table['equipTrackDict'].values():
            if len(latest_modules_track) < max_track_limit:
                latest_modules_tracks.append(track)
            elif track['timeStamp'] > latest_modules_tracks[max_track_limit-1]['timeStamp']:
                latest_modules_tracks.append(track)
                latest_modules_tracks.pop(0)
        
        module_list = []
        cur_ts = int(time.time())
        for track in latest_modules_tracks:
            for mod in track['trackList']:
                if mod['type'] != "INITIAL" and mod['archiveShowTimeEnd'] < cur_ts:
                    mod_data = module_table['equipDict'][mod['equipId']]
                    mod_type = mod_data['typeName2']
                    char_name = character_table[mod['charId']]['name']
                    module_list.append(f"1={char_name}:2={mod_data['typeName1']}-{mod_type}:3={mod_data['uniEquipName']}")
        
        content = ','.join(module_list)

        self.wiki.edit(
            title='首页/亮点干员/新增模组/数据',
            text=content,
            summary='update',
            bot = None,
            minor = False
        )
        # print(content)
        # print('Updated: {}.'.format('用户:Seniorious/term'))
