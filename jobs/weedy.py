from datetime import datetime

import pytz
import requests

from utils.job import Job


def update_yellow(wiki):
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
}}}}<noinclude>[[分类:需要长期关注及更新的条目]]</noinclude>'''

    session = requests.Session()
    good_list = session.get('https://weedy.baka.icu/shop/high').json()['goodList']
    # print(good_list)

    content = template.format(
        star6 = good_list[0]['displayName'],
        star5 = good_list[1]['displayName'],
        potential5_1 = good_list[4]['displayName'].replace('遗产信物', ''),
        potential5_2 = good_list[5]['displayName'].replace('遗产信物', ''),
        potential6_1 = good_list[6]['displayName'].replace('皇家信物', ''),
        potential6_2 = good_list[7]['displayName'].replace('皇家信物', ''),
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

    wiki.edit(
        title = '高级凭证区',
        text = content,
        summary = 'update'
    )
    # print(content)
    print('Updated: {}.'.format('高级凭证区'))


def update_rune(wiki):
    template = '''<section begin={date} />
===={date}====
{{|class="wikitable mw-collapsible mw-collapsed mw-collapsible-dark" style="display:table; text-align:center; width:500px;"
! colspan=12 |{stage_type}：{code} {name}
|-
!width=100px |支援合约
! 
! colspan=5 |任选合约{content}
|}}
<section end={date} />'''

    rank0 = '|rowspan={} style="background:#90C21D;width:50px;"'
    rank1 = '\n|-style="background:#8A8A8A;color:#fff;"\n|style="background:#A8A9AB;width:50px;"|\'\'\'等级1\'\'\''
    rank2 = '\n|-style="background:#313131;color:#fff;"\n|style="background:#727375;"|\'\'\'等级2\'\'\''
    rank3 = '\n|-style="background:#A20616;color:#fff;"\n|style="background:#B65A65;"|\'\'\'等级3\'\'\''

    session = requests.Session()
    stage_list = session.get('https://weedy.baka.icu/crisis/today').json()['stages']

    content = ''
    for stage in stage_list:
        rune_list = {0: [], 1: [], 2: [], 3: []}
        text = ''
        for rune_key in stage['runes']:
            rune_list[stage['runes'][rune_key]['points']].append(
                '|{{{{危机合约词条|{key}|{name}|{point}|{desc}}}}}'.format(
                    key = rune_key,
                    name = stage['runes'][rune_key]['name'],
                    point = stage['runes'][rune_key]['points'],
                    desc = stage['runes'][rune_key]['desc']
                )
            )
        rank_count = 3
        for r in rune_list:
            if r != 0 and 0 < len(rune_list[r]) < 5:
                rune_list[r] += '|' * (5 - len(rune_list[r]))
            if len(rune_list[r]) == 0:
                rank_count -= 1
        rune_text = ['\n'.join(rune_list[r]) for r in rune_list]
        if rune_text[1] != '':
            text += rank1 + '\n' + rune_text[1].replace('|{{', '|width=50px|{{')
        if rune_text[2] != '':
            text += rank2 + '\n' + rune_text[2]
        if rune_text[3] != '':
            text += rank3 + '\n' + rune_text[3]
        if rune_text[0] != '':
            num1 = text.find('|style="background')
            text = text[:num1] + rank0.format(rank_count) + rune_text[0] + '\n' + text[num1:]
        content += template.format(
            stage_type = '训练场' if 'tr' in stage['id'] else '轮换行动地点',
            # date = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y年%m月%d日 %H:%M'),
            date = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y年%m月%d日'),
            code = stage['code'],
            name = stage['name'],
            content = text
        )

    wiki.edit(
        title = '用户:Seniorious/daily-rune',
        text = content,
        summary = 'update'
    )
    # print(content)
    print('Updated: {}.'.format('daily-rune'))


class Weedy(Job):
    def _run(self):
        if datetime.now(pytz.timezone('Asia/Shanghai')).isoweekday() == 4:
            update_yellow(self.wiki)
        update_rune(self.wiki)