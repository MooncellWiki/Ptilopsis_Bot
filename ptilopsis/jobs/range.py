"""攻击范围图:按 range_table 给每个范围生成 ``Widget:Range/<id>`` 的 SVG。"""

from ptilopsis.gamedata.range_table import RangeData
from ptilopsis.jobs.params import RangeTable
from ptilopsis.log import logger
from ptilopsis.utils.job import job
from ptilopsis.utils.wiki import Wiki

svgHeadTemplate = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'viewBox="{} {} {} {}" '
    'style="vertical-align:top;width:{}px;height:{}px;'
    'width:<!--{{$width|default:""|regex_replace:"/(script|<script)/":""}}-->!important;'
    'height:<!--{{$height|default:""|regex_replace:"/(script|<script)/":""}}-->!important">'
)
svgDefStr = (
    "<defs>"
    '<rect id="1" fill="#27a6f3" width="22" height="22"/>'
    '<rect id="2" fill="none" stroke="gray" stroke-width="2" width="20" height="20"/>'
    "</defs>"
)
svgRectTemplate = '<use xlink:href="#{}" x="{}" y="{}"/>'


async def skill_range(wiki: Wiki, range_table: dict[str, RangeData]) -> None:
    for range_id, range_data in range_table.items():
        grids = range_data.grids or []
        # [最小行, 最大行, 最小列, 最大列],原点 (0, 0) 总在范围内
        index = [0, 0, 0, 0]
        for grid in grids:
            index[0] = min(grid.row, index[0])
            index[1] = max(grid.row, index[1])
            index[2] = min(grid.col, index[2])
            index[3] = max(grid.col, index[3])
        range_row = index[1] - index[0] + 1
        range_col = index[3] - index[2] + 1
        # 1 = 范围内格子,2 = 干员所在格
        fig_table = [[0] * range_col for _ in range(range_row)]
        for grid in grids:
            fig_table[grid.row - index[0]][grid.col - index[2]] = 1
            if (grid.row, grid.col) == (0, 0):
                fig_table[grid.row - index[0]][grid.col - index[2]] = 2
        if fig_table[0 - index[0]][0 - index[2]] == 0:
            fig_table[0 - index[0]][0 - index[2]] = 2
        svg = (
            svgHeadTemplate.format(
                0, 0, 26 * range_col, 26 * range_row, 26 * range_col, 26 * range_row
            )
            + svgDefStr
        )
        for y, row in enumerate(fig_table):
            for x, cell in enumerate(row):
                if cell == 1:
                    svg += svgRectTemplate.format(2, x * 26 + 2, y * 26 + 2)
                elif cell == 2:
                    svg += svgRectTemplate.format(1, x * 26 + 1, y * 26 + 1)
        svg += "</svg>"
        text = (
            "<includeonly>"
            + svg
            + "</includeonly><noinclude>{{#Widget:Range/"
            + range_id
            + f"|width={26 * range_col}px|height={26 * range_row}px"
            + "}}</noinclude>"
        )

        await wiki.edit(
            title="Widget:Range/" + range_id, text=text, summary="init", createonly="1"
        )
        logger.info(f"Updated: Widget:Range/{range_id}.")


@job
async def run(wiki: Wiki, range_table: RangeTable) -> None:
    await skill_range(wiki, range_table)
