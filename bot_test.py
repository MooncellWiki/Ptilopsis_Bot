from wikiapi import *
import re
import time

url = 'http://edit.ak.mooncell.wiki/api.php'
se = login_wiki('botPtilopsis', 'sr4-bTG-mky-Sfs', url)

a = read_wiki_repeat(se, url, '用户:Seniorious')
print(a)

b = a + '\ntest action: {}.'.format(time.time())
write_wiki(se, url, '用户:Seniorious', b, 'test action')



