"""新 job 的模板:复制成 ``ptilopsis/jobs/<名字>.py`` 后改写。

参数按注解注入:``Wiki`` 直接给,各张表与富文本转换器用
:mod:`ptilopsis.jobs.params` 里的别名(``CharacterTable``、``RichText`` 等)。
下划线开头的文件不会被 ``discover_jobs`` 导入。
"""

from ptilopsis.jobs.params import CharacterTable, RichText
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki


@job
async def run(wiki: Wiki, character_table: CharacterTable, rts: RichText) -> None:
    content = ""
    # for char in character_table.values():
    #     content += rts.compile(char.description) + "\n"

    await wiki.edit(title="", text=content, summary="update")
    # logger.info(content)
    logger.info("Updated: {}.".format(""))
