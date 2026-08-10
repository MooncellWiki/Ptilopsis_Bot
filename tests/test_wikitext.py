from ptilopsis.wikitext import WikiTemplate, inline_template


def test_multiline_template_puts_one_param_per_line() -> None:
    template = WikiTemplate("蚀刻章")
    template.add("名称", "测试奖章")
    template.add("稀有度", 2)

    assert str(template) == "{{蚀刻章\n|名称=测试奖章\n|稀有度=2\n}}"


def test_template_without_params_still_closes() -> None:
    assert str(WikiTemplate("关卡导航")) == "{{关卡导航\n}}"


def test_add_keeps_empty_value_but_add_optional_skips_it() -> None:
    template = WikiTemplate("蚀刻章")
    template.add("描述", "")
    template.add("获得方式", None)
    template.add_optional("套组", "")
    template.add_optional("奖励", [])

    assert str(template) == "{{蚀刻章\n|描述=\n|获得方式=\n}}"


def test_add_optional_keeps_zero() -> None:
    # 0 是有意义的参数值,不能和空字符串一样被跳过
    template = WikiTemplate("普通关卡信息").add_optional("作战消耗", 0)

    assert str(template) == "{{普通关卡信息\n|作战消耗=0\n}}"


def test_add_all_keeps_dict_order() -> None:
    template = WikiTemplate("普通关卡信息")
    template.add_all({"关卡代号": "1-7", "关卡名": "淬火", "关卡id": "main_01-07"})

    assert str(template) == (
        "{{普通关卡信息\n|关卡代号=1-7\n|关卡名=淬火\n|关卡id=main_01-07\n}}"
    )


def test_add_all_keeps_empty_value_but_add_all_optional_skips_it() -> None:
    template = WikiTemplate("普通关卡信息")
    template.add_all({"关卡代号": "1-7", "关卡名": ""})
    template.add_all_optional({"子类型": None, "关卡难度": "", "推荐等级": "精一30"})

    assert str(template) == (
        "{{普通关卡信息\n|关卡代号=1-7\n|关卡名=\n|推荐等级=精一30\n}}"
    )


def test_add_all_interleaves_with_single_adds() -> None:
    # 批量与单个混用时,参数顺序仍然是调用顺序
    template = WikiTemplate("蚀刻章")
    template.add_optional("套组", "测试套组")
    template.add_all({"名称": "甲", "稀有度": 2})
    template.add("镀层方式", "")

    assert str(template) == (
        "{{蚀刻章\n|套组=测试套组\n|名称=甲\n|稀有度=2\n|镀层方式=\n}}"
    )


def test_add_block_starts_value_on_the_next_line() -> None:
    template = WikiTemplate("蚀刻章/套组预览")
    template.add("名称", "测试")
    template.add_block("内容", "{{蚀刻章\n|名称=甲\n}}\n{{蚀刻章\n|名称=乙\n}}")

    assert str(template) == (
        "{{蚀刻章/套组预览\n"
        "|名称=测试\n"
        "|内容=\n"
        "{{蚀刻章\n|名称=甲\n}}\n"
        "{{蚀刻章\n|名称=乙\n}}\n"
        "}}"
    )


def test_add_block_with_empty_body_does_not_emit_a_blank_line() -> None:
    template = WikiTemplate("蚀刻章/套组预览").add_block("内容", "")

    assert str(template) == "{{蚀刻章/套组预览\n|内容=\n}}"


def test_add_returns_self_for_chaining() -> None:
    template = WikiTemplate("蚀刻章").add("名称", "甲").add_optional("套组", "乙")

    assert str(template) == "{{蚀刻章\n|名称=甲\n|套组=乙\n}}"


def test_inline_template_uses_positional_params() -> None:
    assert inline_template("材料消耗", "龙门币", 100) == "{{材料消耗|龙门币|100}}"


def test_inline_template_without_params() -> None:
    assert inline_template("关卡导航") == "{{关卡导航}}"
