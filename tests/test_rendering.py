import pytest
from jinja2 import UndefinedError

from ptilopsis.rendering import wikitext_environment


def test_wikitext_delimiters_do_not_conflict_with_mediawiki() -> None:
    template = wikitext_environment.from_string(
        "<% if enabled %>{{材料消耗|<< name >>|1}}<% endif %>\n{{#widget:VoiceTable}}"
    )

    assert template.render(enabled=True, name="固源岩") == (
        "{{材料消耗|固源岩|1}}\n{{#widget:VoiceTable}}"
    )


def test_missing_template_variable_raises() -> None:
    template = wikitext_environment.from_string("<< missing >>")

    with pytest.raises(UndefinedError):
        template.render()


def test_wikitext_is_not_html_escaped() -> None:
    template = wikitext_environment.from_string("<< value >>")

    assert template.render(value="<br/>&") == "<br/>&"


def test_all_wikitext_templates_compile() -> None:
    for template_name in wikitext_environment.list_templates():
        wikitext_environment.get_template(template_name)
