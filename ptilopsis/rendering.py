from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

wikitext_environment = Environment(
    loader=PackageLoader("ptilopsis", "templates/wikitext"),
    autoescape=False,
    undefined=StrictUndefined,
    variable_start_string="<<",
    variable_end_string=">>",
    block_start_string="<%",
    block_end_string="%>",
    comment_start_string="<#",
    comment_end_string="#>",
    keep_trailing_newline=True,
    # 块标签独占一行时不产生多余空白,模板里无需手写 -%> 控制符
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_wikitext(template_name: str, **context: Any) -> str:
    return wikitext_environment.get_template(template_name).render(**context)
