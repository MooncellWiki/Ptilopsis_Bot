from utils.job import Job
from utils.richTextStyles import RichTextStyles


class Sample(Job):
    def _run(self):
        character_table = self.getgd('excel/character_table.json')
        rts = RichTextStyles(self.getgd('excel/gamedata_const.json'))

        content = ''

        self.wiki.edit(
            title='',
            text=content,
            summary='update'
        )
        # print(content)
        print('Updated: {}.'.format(''))
