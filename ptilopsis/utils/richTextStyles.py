import re


class RichTextStyles:
    def __init__(self, gamedata_const):
        self.richTextStyles_t: dict = gamedata_const["richTextStyles"]
        self.termDescriptionDict_t: dict = gamedata_const["termDescriptionDict"]
        self.richTextStyles: dict = {}
        self.termDescriptionDict: dict = {}
        for s in self.richTextStyles_t:
            temp = self.richTextStyles_t[s]
            if temp.find("</color>") != -1:
                self.richTextStyles[s] = temp.replace("<color=", "{{color|").replace(
                    ">{0}</color>", "|"
                )
        for k in self.termDescriptionDict_t:
            temp2 = self.termDescriptionDict_t[k]
            self.termDescriptionDict[k] = f"{{{{术语|{temp2['termId']}|"

    def tran1(self, matched):
        code = matched.group(1)
        if code.lower() in self.richTextStyles:
            return self.richTextStyles[code.lower()]
        elif code in self.termDescriptionDict:
            return self.termDescriptionDict[code]
        else:
            return "{{"

    def tran2(self, matched):
        code = matched.group(1)
        if code in self.termDescriptionDict:
            return self.termDescriptionDict[code]
        else:
            return "{{"

    def compile(self, s):
        if s is None:
            return ""
        pattern = re.compile("<+@([^>]*)>")
        t = re.sub(pattern, self.tran1, s)
        pattern = re.compile(r"<+\$([^>]*)>")
        t = re.sub(pattern, self.tran2, t)
        t = re.sub(r"<color=([^>]*)>", r"{{color|\1|", t)
        t = t.replace("</>", "}}")
        t = t.replace("<>", "}}")
        t = t.replace("</color>", "}}")
        return t
