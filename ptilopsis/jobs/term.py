from ptilopsis.jobs.params import RawGamedataConst, RichText
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


@job
def run(wiki: Wiki, gamedata_const: RawGamedataConst, rts: RichText) -> None:
    term_list = []
    for t in gamedata_const["termDescriptionDict"].values():
        desc = rts.compile(t["description"]).replace("\n", "<br>")
        term_list.append(f"{{{{术语释义|{t['termName']}|{desc}|id={t['termId']}}}}}")

    content = "\n\n".join(term_list)

    wiki.edit(
        title="用户:Seniorious/term",
        text=content,
        summary="update",
        bot=None,
        minor=True,
    )
    logger.info("Updated: {}.".format("用户:Seniorious/term"))
