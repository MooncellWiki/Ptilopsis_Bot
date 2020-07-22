class Job:
    def __init__(self, wiki, gamedata):
        self.wiki = wiki
        self.gamedata = gamedata

    def run(self):
        try:
            self._run()
        except Exception as e:
            print(e)

    def getgd(self, path, region='cn'):
        """
        :param path:
        :param region: 服务器: cn,us,jp,kr,tw
        :return:dict
        """
        return self.gamedata.get(path, region)

    def getgd_txt(self, path, region='cn'):
        """
        :param path:
        :param region: 服务器: cn,us,jp,kr,tw
        :return: string
        """
        return self.gamedata.get_txt(path, region)

    def _run(self):
        pass
