class Job:
    def __init__(self, wiki, gamedata):
        self.wiki = wiki
        self.gamedata = gamedata

    def run(self):
        try:
            self._run()
        except Exception as e:
            print(e)

    def getgd(self, path, region='CN'):
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return:dict
        """
        return self.gamedata.get(path, region)

    def getgd_txt(self, path, region='CN'):
        """
        :param path:
        :param region: 服务器: CN,US,JP,KR,TW
        :return: string
        """
        return self.gamedata.get_txt(path, region)

    def _run(self):
        pass
