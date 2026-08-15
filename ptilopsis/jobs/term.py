from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job
from ptilopsis.utils.richTextStyles import RichTextStyles


@job
def run(ctx: JobContext) -> None:
    character_table = ctx.getgd("excel/character_table.json")
    gamedata_const = ctx.getgd("excel/gamedata_const.json")
    rts = RichTextStyles(ctx.getgd("excel/gamedata_const.json"))

    term_list = []
    for t in gamedata_const["termDescriptionDict"].values():
        desc = rts.compile(t["description"]).replace("\n", "<br>")
        term_list.append(f"{{{{术语释义|{t['termName']}|{desc}|id={t['termId']}}}}}")

    content = "\n\n".join(term_list)

    ctx.wiki.edit(
        title="用户:Seniorious/term",
        text=content,
        summary="update",
        bot=None,
        minor=True,
    )
    # logger.info(content)
    logger.info("Updated: {}.".format("用户:Seniorious/term"))
