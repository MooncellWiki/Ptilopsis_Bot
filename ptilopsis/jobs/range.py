from ptilopsis.log import logger
from ptilopsis.utils.job import JobContext, job

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


def skill_range(wiki, raneg_table):
    for rangeId in raneg_table:
        index = [0, 0, 0, 0]
        for grid in raneg_table[rangeId]["grids"]:
            index[0] = min(grid["row"], index[0])
            index[1] = max(grid["row"], index[1])
            index[2] = min(grid["col"], index[2])
            index[3] = max(grid["col"], index[3])
        rangeRow = index[1] - index[0] + 1
        rangeCol = index[3] - index[2] + 1
        rangeFigTable = [[0] * rangeCol for i in range(rangeRow)]
        for grid in raneg_table[rangeId]["grids"]:
            rangeFigTable[grid["row"] - index[0]][grid["col"] - index[2]] = 1
            if (grid["row"], grid["col"]) == (0, 0):
                rangeFigTable[grid["row"] - index[0]][grid["col"] - index[2]] = 2
        if rangeFigTable[0 - index[0]][0 - index[2]] == 0:
            rangeFigTable[0 - index[0]][0 - index[2]] = 2
        svgStr = (
            svgHeadTemplate.format(
                0, 0, 26 * rangeCol, 26 * rangeRow, 26 * rangeCol, 26 * rangeRow
            )
            + svgDefStr
        )
        for y in range(len(rangeFigTable)):
            for x in range(len(rangeFigTable[y])):
                if rangeFigTable[y][x] == 1:
                    svgStr += svgRectTemplate.format(2, x * 26 + 2, y * 26 + 2)
                elif rangeFigTable[y][x] == 2:
                    svgStr += svgRectTemplate.format(1, x * 26 + 1, y * 26 + 1)
        svgStr += "</svg>"
        Str = (
            "<includeonly>"
            + svgStr
            + "</includeonly><noinclude>{{#Widget:Range/"
            + rangeId
            + f"|width={26 * rangeCol}px|height={26 * rangeRow}px"
            + "}}</noinclude>"
        )

        wiki.edit(
            title="Widget:Range/" + rangeId, text=Str, summary="init", createonly="1"
        )
        # logger.info(Str)
        logger.info("Updated: {}.".format("Widget:Range/" + rangeId))


@job
def run(ctx: JobContext) -> None:
    range_table = ctx.getgd("excel/range_table.json")
    skill_range(ctx.wiki, range_table)
