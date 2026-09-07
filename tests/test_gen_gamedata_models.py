import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "gen_gamedata_models.py"
spec = importlib.util.spec_from_file_location("gen_gamedata_models", SCRIPT)
assert spec is not None and spec.loader is not None
gen = importlib.util.module_from_spec(spec)
# dataclass 装饰器要通过 sys.modules 找回模块命名空间
sys.modules[spec.name] = gen
spec.loader.exec_module(gen)

FBS = """
// This file is auto-generated
enum enum__Torappu_EvolvePhase : int {
    PHASE_0 = 0,
    PHASE_1 = 1,
}
table clz_Torappu_AttributesData {
    maxHp: int;
    def: int;
    magicResistance: float;
    stunImmune: bool;
    phase: enum__Torappu_EvolvePhase;
}
table list_int {
    values: [int];
}
table dict__string__int {
    key: string(key);
    value: int;
}
table dict__int__list_clz_Torappu_AttributesData {
    key: int(key);
    value: [clz_Torappu_AttributesData];
}
table clz_Torappu_Sample_Inner {
    name: string;
    frames: [clz_Torappu_AttributesData];
    table: [list_int];
    favors: [dict__string__int];
    costs: [dict__int__list_clz_Torappu_AttributesData];
    extra: hg__internal__JObject;
    Key: string;
}
table dict__string__clz_Torappu_Sample_Inner {
    key: string(key);
    value: clz_Torappu_Sample_Inner;
}
table clz_Torappu_SimpleKVTable_clz_Torappu_Sample_Inner {
    samples: [dict__string__clz_Torappu_Sample_Inner];
}
root_type clz_Torappu_SimpleKVTable_clz_Torappu_Sample_Inner;
"""


def render() -> str:
    schema = gen.parse(FBS)
    return gen.Generator(schema, "sample_table").render()


def test_class_names_drop_prefix_and_underscores() -> None:
    assert gen.camel_class_name("clz_Torappu_CharacterData_TalentDataBundle") == (
        "CharacterDataTalentDataBundle"
    )
    assert gen.camel_class_name("enum__Torappu_EvolvePhase") == "EvolvePhase"


def test_scalars_get_fbs_defaults_and_references_are_optional() -> None:
    code = render()
    assert "    max_hp: int = 0" in code
    assert "    magic_resistance: float = 0.0" in code
    assert "    stun_immune: bool = False" in code
    assert "    name: str | None = None" in code
    assert "    frames: list[AttributesData] | None = None" in code


def test_enum_fields_are_str_with_zero_member_default() -> None:
    code = render()
    assert "class EvolvePhase(IntEnum):" in code
    assert "    PHASE_1 = 1" in code
    assert '    phase: str = "PHASE_0"' in code


def test_keywords_and_non_roundtrip_names_get_alias() -> None:
    code = render()
    assert '    def_: int = Field(default=0, alias="def")' in code
    assert '    key: str | None = Field(default=None, alias="Key")' in code


def test_container_tables_become_dict_and_nested_list() -> None:
    code = render()
    assert "    table: list[list[int]] | None = None" in code
    assert "    favors: dict[str, int] | None = None" in code
    assert "    costs: dict[int, list[AttributesData]] | None = None" in code
    assert "    extra: Any | None = None" in code
    assert "class DictStringInt" not in code
    assert "class ListInt" not in code


def test_simple_kv_root_becomes_type_adapter() -> None:
    code = render()
    assert "SampleTable = TypeAdapter(dict[str, SampleInner])" in code
    assert "class SimpleKVTable" not in code
    assert "SampleInner.model_rebuild()" in code


def test_generated_module_is_importable_and_validates() -> None:
    namespace: dict = {}
    exec(compile(render(), "sample_table.py", "exec"), namespace)
    table = namespace["SampleTable"].validate_python(
        {
            "a": {
                "name": None,
                "frames": [{"maxHp": 1, "def": 2, "phase": "PHASE_1"}],
                "table": [[1, 2], [3]],
                "favors": {"1": 0},
                "costs": {"1": [{"maxHp": 5}]},
                "Key": "k",
            }
        }
    )
    inner = table["a"]
    assert inner.name is None and inner.key == "k"
    assert inner.frames[0].def_ == 2 and inner.frames[0].phase == "PHASE_1"
    assert inner.costs == {1: [namespace["AttributesData"](max_hp=5)]}
