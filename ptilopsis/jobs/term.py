from ptilopsis.jobs.params import GamedataConst, RichText
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


@job
def run(wiki: Wiki, gamedata_const: GamedataConst, rts: RichText) -> None:
    term_list = []
    for t in (gamedata_const.term_description_dict or {}).values():
        desc = rts.compile(t.description).replace("\n", "<br>")
        term_list.append(f"{{{{术语释义|{t.term_name}|{desc}|id={t.term_id}}}}}")

    content = "\n\n".join(term_list)

    wiki.edit(
        title="用户:Seniorious/term",
        text=content,
        summary="update",
        bot=None,
        minor=True,
    )
    logger.info("Updated: {}.".format("用户:Seniorious/term"))
