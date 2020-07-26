import json

from utils.job import Job


def update_menusidebar(wiki, old_num, id_table):
    origin_text = wiki.read('MediaWiki:MenuSidebar')
    num1 = origin_text.find('*[[干员一览')
    num2 = origin_text.find('*[[干员一览')

    content = ''
    for name in id_table:
        if int(id_table[name]['id']) > old_num:
            content = '**[[{}]]\n'.format(name) + content
        trans = origin_text.find('**[[{}]]'.format(name))
        if 1 < trans and trans < num1:
            num1 = trans
    new_text = origin_text[:num1] + content + origin_text[num2:]

    wiki.edit(
        title = 'MediaWiki:MenuSidebar',
        text = new_text,
        summary = 'update',
        bot = None,
        minor = True
    )
    # print(new_text)
    print('Update: {}.'.format('MediaWiki:MenuSidebar'))


def update_mainpage(wiki, old_num, id_table):
    fin2 = wiki.read('首页')
    num1 = fin2.find('==近期新增==')
    num2 = fin2.find('==网站信息==')

    content = ''
    for name in id_table:
        if int(id_table[name]['id']) > old_num:
            content = '{{{{干员头像|{}|80px}}}} '.format(name) + content
    content = '==近期新增==\n===新增干员===\n' + content[:-1] + '\n'
    fin = fin2[:num1] + content + fin2[num2:]

    wiki.edit(
        title = '首页',
        text = fin,
        summary = 'update'
    )
    print(fin)
    print('Update: {}.'.format('首页'))


class Sidebar(Job):
    def _run(self):
        pass

    def _run_update(self, old_num):
        with open('character_id.json', 'r', encoding = 'utf-8') as file:
            id_table = json.loads(file.read())
        update_menusidebar(self.wiki, old_num, id_table)
