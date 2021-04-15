import re


class RichTextStyles:
    richTextStyles_t = {}
    termDescriptionDict_t = {}
    richTextStyles = {}
    termDescriptionDict = {}

    def __init__(self, gamedata_const):
        self.richTextStyles_t = gamedata_const['richTextStyles']
        self.termDescriptionDict_t = gamedata_const['termDescriptionDict']
        for s in self.richTextStyles_t:
            temp = self.richTextStyles_t[s]
            if temp.find('</color>') != -1:
                self.richTextStyles[s] = temp.replace('<color=', "{{color|").replace('>{0}</color>', '|')
        for k in self.termDescriptionDict_t:
            temp2 = self.termDescriptionDict_t[k]
            self.termDescriptionDict[k] = f"{{{{术语释义|术语={temp2['termName']}|"

    def tran1(self, matched):
        code = matched.group(1)[2:-1]
        return self.richTextStyles[code.lower()]

    def tran2(self, matched):
        code = matched.group(1)[2:-1]
        return self.termDescriptionDict[code]

    def compile(self, s):
        pattern = re.compile('(<@[^>]*>)')
        t = re.sub(pattern, self.tran1, s)
        pattern = re.compile('(<\$[^>]*>)')
        t = re.sub(pattern, self.tran2, t)
        t = t.replace('</>', '}}')
        return t
