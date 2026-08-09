"""gamedata 原始数据的 pydantic 模型。

类型定义参照 thirdparty/OpenArknightsFBS/FBS 下的 FlatBuffers schema,
模型与字段按 job 的实际消费需求增量添加,未消费的字段不建模。
字段名为 FBS 中 camelCase 字段的机械 snake_case 转换,不另行命名。
"""
