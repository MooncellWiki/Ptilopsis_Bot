import re
import time

from wikiapi import *


def update_sidebar(se, url, old, id_table):
    update_menusidebar(se, url, old, id_table)
    update_mainpage(se, url, old, id_table)


def update_menusidebar(se, url, old_num, id_table):
    fin2 = read_wiki(se, url, 'MediaWiki:MenuSidebar')
    num1 = fin2.find('*[[干员一览]]')
    num2 = fin2.find('*[[干员一览]]')

    content = ''
    for name in id_table:
        if int(id_table[name]['id']) > old_num:
            content = '**[[{}]]\n'.format(name) + content
        trans = fin2.find('**[[{}]]'.format(name))
        if 1 < trans and trans < num1:
            num1 = trans
    fin = fin2[:num1] + content + fin2[num2:]

    write_wiki_minor(se, url, 'MediaWiki:MenuSidebar', fin, '')
    # print(fin)
    print('Update: MediaWiki:MenuSidebar.')


def update_mainpage(se, url, old_num, id_table):
    fin2 = read_wiki(se, url, '首页')
    num1 = fin2.find('==近期新增==')
    num2 = fin2.find('==网站信息==')

    content = ''
    for name in id_table:
        if int(id_table[name]['id']) > old_num:
            content = '{{{{干员头像|{}|80px}}}} '.format(name) + content
    content = '==近期新增==\n===新增干员===\n' + content[:-1] + '\n'
    fin = fin2[:num1] + content + fin2[num2:]

    write_wiki_minor(se, url, '首页', fin, '')
    # print(fin)
    print('Update: 首页.')

