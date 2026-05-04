import time

from ptilopsis.utils.job import Job


class NewModule(Job):
    def _run(self):
        module_table = self.getgd("excel/uniequip_table.json")
        character_table = self.getgd("excel/character_table.json")

        cur_ts = int(time.time())
        latest_modules_tracks = []
        for track in module_table["equipTrackDict"]:
            if track["timeStamp"] >= cur_ts - 2592000:  # 30*24*3600 一个月
                latest_modules_tracks.append(track)

        module_list = []
        for track in latest_modules_tracks:
            for mod in track["trackList"]:
                if mod["type"] != "INITIAL" and (
                    mod["archiveShowTimeEnd"] > cur_ts or mod["archiveShowTimeEnd"] < 0
                ):
                    mod_data = module_table["equipDict"][mod["equipId"]]
                    mod_type = mod_data["typeName2"]
                    char_name = character_table[mod["charId"]]["name"]
                    module_list.append(
                        f"1={char_name}:2={mod_data['typeName1']}-{mod_type}:3={mod_data['uniEquipName']}"
                    )

        content = ",".join(module_list)

        self.wiki.edit(
            title="首页/亮点干员/新增模组/数据",
            text=content,
            summary="update",
            bot=None,
            minor=False,
        )
        # print(content)
        print("Updated: {}.".format("首页/新增模组"))
