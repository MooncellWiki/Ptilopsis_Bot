from ptilopsis.log import logger
from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles


class Sample(Job):
    def _run(self):
        character_table = self.getgd("excel/character_table.json")
        rts = RichTextStyles(self.getgd("excel/gamedata_const.json"))

        content = ""

        self.wiki.edit(title="", text=content, summary="update")
        # logger.info(content)
        logger.info("Updated: {}.".format(""))
