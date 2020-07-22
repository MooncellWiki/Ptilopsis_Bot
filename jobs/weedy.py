from datetime import datetime

import pytz
import requests

from utils.job import Job

template = '''<noinclude>{{{{cbox2|lv=1|title=该页面可能与实际情况不符，<br>如有差错可以随时进行编辑<br>PRTS的建设离不开每一位用户的建设与支持}}}}</noinclude>{{{{高级凭证区商品一览
|当期6星={star6}
|当期5星={star5}
|当期5星信物1={potential5_1}
|当期5星信物2={potential5_2}
|当期6星信物1={potential6_1}
|当期6星信物2={potential6_2}
|当期素材1={material1}
|当期素材2={material2}
|当期素材3={material3}
|当期素材4={material4}
|当期素材5={material5}
|当期素材6={material6}
|寻访池开启时间={time_begin}
|寻访池关闭时间={time_end}
|}}<noinclude>[[分类:需要长期关注及更新的条目]]</noinclude>'''


class Weedy(Job):
    def _run(self):
        session = requests.Session()
        good_list = session.get('https://weedy.baka.icu/shop/high').json()['goodList']
        # print(good_list)

        content = template.format(
            star6 = good_list[0]['displayName'],
            star5 = good_list[1]['displayName'],
            potential5_1 = good_list[4]['displayName'],
            potential5_2 = good_list[5]['displayName'],
            potential6_1 = good_list[6]['displayName'],
            potential6_2 = good_list[7]['displayName'],
            material1 = good_list[8]['displayName'],
            material2 = good_list[9]['displayName'],
            material3 = good_list[10]['displayName'],
            material4 = good_list[11]['displayName'],
            material5 = good_list[12]['displayName'],
            material6 = good_list[13]['displayName'],
            time_begin = datetime.fromtimestamp(good_list[0]['goodStartTime'], pytz.timezone('Asia/Shanghai')).strftime(
                '%Y-%m-%d %H:%M'),
            time_end = datetime.fromtimestamp(good_list[0]['goodEndTime'], pytz.timezone('Asia/Shanghai')).strftime(
                '%Y-%m-%d %H:%M')
        )

        self.wiki.edit(
            title = '高级凭证区',
            text = content,
            summary = 'update'
        )
        # print(content)
        print('Updated: {}.'.format('高级凭证区'))
