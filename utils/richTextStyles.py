import re


class RichTextStyles:
    richTextStyles = {}

    def __init__(self, gamedata_const):
        self.richTextStyles = gamedata_const['richTextStyles']
        for s in self.richTextStyles:
            temp = self.richTextStyles[s]
            if temp.find('</color>') != -1:
                self.richTextStyles[s] = temp.replace('<color=', "{{color|").replace('>{0}</color>', '|')

    def tran(self, matched):
        code = matched.group(1)[2:-1]
        return self.richTextStyles[code.lower()]

    def compile(self, s):
        pattern = re.compile('(<@[^>]*>)')
        t = re.sub(pattern, self.tran, s)
        t = t.replace('</>', '}}')
        return t
