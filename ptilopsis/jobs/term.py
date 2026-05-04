from ptilopsis.utils.job import Job
from ptilopsis.utils.richTextStyles import RichTextStyles


class Term(Job):
    def _run(self):
        character_table = self.getgd("excel/character_table.json")
        gamedata_const = self.getgd("excel/gamedata_const.json")
        rts = RichTextStyles(self.getgd("excel/gamedata_const.json"))

        term_list = []
        for t in gamedata_const["termDescriptionDict"].values():
            desc = rts.compile(t["description"]).replace("\n", "<br>")
            term_list.append(
                f"{{{{术语释义|{t['termName']}|{desc}|id={t['termId']}}}}}"
            )

        content = "\n\n".join(term_list)

        self.wiki.edit(
            title="用户:Seniorious/term",
            text=content,
            summary="update",
            bot=None,
            minor=True,
        )
        # print(content)
        print("Updated: {}.".format("用户:Seniorious/term"))
