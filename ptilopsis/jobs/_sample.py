from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles


@job
def run(ctx: JobContext) -> None:
    character_table = ctx.getgd("excel/character_table.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    content = ""

    ctx.wiki.edit(title="", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format(""))
