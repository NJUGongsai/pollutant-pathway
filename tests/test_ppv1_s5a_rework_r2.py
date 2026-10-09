"""S5a 回修 r2 回归(复审 POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R2_2026-10-09
§4 唯一残余 P1 S5A-02:要求侧显式非规范/键量纲不支持单位在映射首
消费处收口;契约 ppv1-evaluation-2 → -3 / template-2 → -3 /
profile-21 → -22)。

全部为合成规则级夹具(零金标/题面/网络/LLM/费用;数字不外推
dev/298)。B1 六案与评审 conditions 专项同案构造(真实公共链
``start_run`` → ``read_native_export`` 首读 → ``evaluate_scientific``):
四个不支持单位案实际降档 unknown 族、两个合法正控保持;判别回归
要求**合法事实在场 + necessity 来源在场**(不用 facts=[] 天然
unknown 冒充单位分支)。B2 守门钉住 checked 构造器值清 None 与
两序事实(文字与实现同真)。r1 的 20 条件案(18 旧同源 + 2
required_absent 单列)全保持。
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.pollutant import evaluation as _evaluation_module  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    classify_condition_requirement,
    evaluate_scientific,
)
from pathway_v43.pollutant.path_context import build_condition_fact  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    PPV1_PREREGISTRATION_TEMPLATE_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    PPV1_REFERENCE_GRAPH_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from pathway_v43.pollutant.preregistration import (  # noqa: E402
    build_preregistration_template,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    validate_reference_graph,
)
from test_ppv1_s5a_evaluator import _plan, _reader, _run  # noqa: E402
from test_ppv1_s5a_schema import (  # noqa: E402
    condition_scope,
    synth_evaluation_input,
    synth_reference_graph,
)


def _detailed(requirement: dict, facts: list) -> dict:
    """S5A-02 详细分类器(经模块属性取用:父基线缺 r2 行为 ⇒ 逐
    nodeid 真实红,不是 collection 错误)。"""
    return _evaluation_module._classify_condition_requirement_detailed(
        requirement, facts)


def req(key, value, **kwargs):
    return {**condition_scope(key, value),
            "subject_scenario_ref": "", **kwargs}


def fact(key, value, status="known_present", unit=""):
    return {"key": key, "value": value, "status": status,
            "unit": unit, "source_ref": "src:synthetic-observation"}


def _evaluate_graph(tmp_path: Path, run_id: str, digest: str,
                    graph: dict) -> dict:
    validate_reference_graph(graph)
    evaluation_input = synth_evaluation_input(
        graphs=[graph],
        exports=[{"run_id": run_id, "export_digest": digest}])
    evaluation_input["run_identity"]["run_id"] = run_id
    return evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=_reader(
            tmp_path / "runs", run_id),
        preregistration=build_preregistration_template())


# --------------------------------------------- S5A-02 r2 单位首消费收口(单元)

# 评审 R2 §4.1 B1 六案(要求侧单位;事实与必要性来源均合法在场)
_B1_CASES = [
    # (name, key, value, unit, facts, expected, unit_kind)
    ("B1_requirement_K_298_vs_25C", "temperature_C", "298", "K",
     [lambda: fact("temperature_C", 25, unit="C")],
     "condition_unknown", "requirement_unit_noncanonical"),
    ("B1_requirement_K_25_vs_25C", "temperature_C", "25", "K",
     [lambda: fact("temperature_C", 25, unit="C")],
     "condition_unknown", "requirement_unit_noncanonical"),
    ("B1_requirement_F_77_vs_25C", "temperature_C", "77", "F",
     [lambda: fact("temperature_C", 25, unit="C")],
     "condition_unknown", "requirement_unit_noncanonical"),
    ("B1_dimensionless_unit_unexpected", "electron_acceptor", "O2",
     "mg/L", [lambda: fact("electron_acceptor", "O2")],
     "condition_unknown", "requirement_unit_unexpected"),
    ("B1_requirement_C_25_vs_25C", "temperature_C", "25", "C",
     [lambda: fact("temperature_C", 25, unit="C")],
     "compatible", None),
    ("B1_requirement_unit_empty_25_vs_25C", "temperature_C", "25", "",
     [lambda: fact("temperature_C", 25, unit="C")],
     "compatible", "requirement_unit_not_declared"),
]


def _b1_case(name: str):
    for row in _B1_CASES:
        if row[0] == name:
            return row
    raise KeyError(name)


@pytest.mark.parametrize("name", [row[0] for row in _B1_CASES])
def test_s5a02_r2_b1_six_cases_classifier(name: str) -> None:
    """B1 六案(公共单条分类器):四不支持单位案降 unknown 族(机读
    reason=requirement_unit_not_representable,保留原 unit/value/key);
    合法 C 与空单位正控保持 compatible。"""
    _name, key, value, unit, fact_makers, expected, unit_kind = \
        _b1_case(name)
    requirement = req(key, value, unit=unit)
    facts = [make() for make in fact_makers]
    result = _detailed(requirement, facts)
    assert result["classification"] == expected, name
    if expected == "condition_unknown":
        # 评审 B1 契约:不能丢 unit 后授 compatible/conflict;unknown
        # 由单位分支产生(reason 区分,不是缺事实/无来源)
        assert result["frozen_status"] is None, name
        assert "requirement_unit_not_representable" in result["reason"], \
            name
        assert "no_applicable_fact" not in result["reason"], name
        assert "necessity_unsourced" not in result["reason"], name
        disclosure = result["mapping_disclosures"][0]
        assert disclosure["kind"] == unit_kind, name
        assert disclosure["key"] == key, name
        assert disclosure["unit"] == unit, name
        assert disclosure["value"] == repr(value), name
        assert disclosure["reason"] == unit_kind, name
        if unit_kind == "requirement_unit_noncanonical":
            assert "K" in disclosure["allowed_units"] or \
                "C" in disclosure["allowed_units"], name
    else:
        # 合法正控:分类不降档;C 案无披露,空单位案披露 canonical-by-key
        unit_kinds = [d["kind"] for d in result["mapping_disclosures"]
                      if str(d.get("kind", "")).startswith(
                          "requirement_unit")]
        assert unit_kinds == ([unit_kind] if unit_kind else []), name
        if unit_kind == "requirement_unit_not_declared":
            disclosure = next(d for d in result["mapping_disclosures"]
                              if d["kind"] == unit_kind)
            assert disclosure["reason"] == \
                "requirement_unit_canonical_by_key", name
            assert result["frozen_status"] == "satisfied", name


def test_s5a02_r2_unit_branch_not_masked_by_missing_facts() -> None:
    """判别回归(评审 §4.2.3):合法事实在场 + necessity 来源在场 +
    非规范要求单位 ⇒ unknown 的 reason 是单位原因;同案把单位改成
    空单位 ⇒ compatible —— 证明 unknown 来自单位分支,不是用
    facts=[] 天然 unknown 冒充。"""
    facts = [fact("temperature_C", 25, unit="C")]
    requirement_k = req("temperature_C", "298", unit="K")
    assert requirement_k["source_refs"]  # necessity 来源在场
    result = _detailed(requirement_k, facts)
    assert result["classification"] == "condition_unknown"
    assert "requirement_unit_not_representable" in result["reason"]
    # 同案值 298、空单位(按键规范单位约定)⇒ 点值不相交 ⇒ conflict
    # (canonical-by-key 默认下的合法判定;证明单位分支才是四降案
    # unknown 的来源,而非事实缺席)
    result_empty = _detailed(req("temperature_C", "298", unit=""), facts)
    assert result_empty["classification"] == "essential_conflict"
    assert result_empty["frozen_status"] == "conflict"
    # 值与事实同值(25)时空单位 ⇒ compatible(canonical-by-key 默认)
    result_same = _detailed(req("temperature_C", "25", unit=""), facts)
    assert result_same["classification"] == "compatible"


def test_s5a02_r2_requirement_vs_fact_unit_semantics_split() -> None:
    """要求侧 canonical-by-key 默认与事实侧来源单位三态分立:

    - 空要求单位 ⇒ 按键规范单位约定(合法不降档);
    - 事实侧 temperature 缺单位 ⇒ 仍 source_unit_unknown(unknown),
      不因要求侧默认而升级;
    - 事实侧显式规范单位 C ⇒ 合法正控保持。"""
    facts_no_unit = [fact("temperature_C", 25, unit="")]
    result = _detailed(req("temperature_C", "25", unit=""),
                       facts_no_unit)
    assert result["classification"] == "condition_unknown"
    assert "source_unit_unknown" in result["reason"]
    assert result["frozen_status"] == "unknown"
    # 事实侧非规范单位 ⇒ unit_mismatch(事实三态既有路线保持)
    result_mismatch = _detailed(
        req("temperature_C", "25", unit=""),
        [fact("temperature_C", 25, unit="K")])
    assert result_mismatch["classification"] == "condition_unknown"
    assert "unit_mismatch" in result_mismatch["reason"]
    # 事实侧显式规范单位 + 空要求单位 ⇒ compatible(两侧各自合法)
    result_canonical = _detailed(
        req("temperature_C", "25", unit=""),
        [fact("temperature_C", 25, unit="C")])
    assert result_canonical["classification"] == "compatible"
    # pH 无量纲键:空单位本就合法(无披露,不因 UNIT_REQUIRED 误伤)
    result_ph = _detailed(req("pH", "6.5-7.5"),
                          [fact("pH", 7)])
    assert result_ph["classification"] == "compatible"
    unit_kinds = [d["kind"] for d in result_ph["mapping_disclosures"]]
    assert "requirement_unit_not_declared" not in unit_kinds


def test_s5a02_r2_preference_with_unrepresentable_unit_stays_unknown() \
        -> None:
    """preference 轴遇无法表示的单位 ⇒ 同沿 unknown 族(值轴探针
    不消费不可表示要求;preference 永不门禁语义不受影响)。"""
    facts = [fact("temperature_C", 25, unit="C")]
    result = _detailed(
        req("temperature_C", "25", unit="K", required="preference"),
        facts)
    assert result["classification"] == "condition_unknown"
    assert "requirement_unit_not_representable" in result["reason"]
    # 合法 preference 保持(满足 ⇒ compatible,不门禁)
    ok = _detailed(
        req("temperature_C", "25", unit="C", required="preference"),
        facts)
    assert ok["classification"] == "compatible"


# ------------------------------------------- S5A-02 r2 公共链端到端 + 聚合

@pytest.mark.parametrize("name,expected", [
    (row[0], row[5]) for row in _B1_CASES])
def test_s5a02_r2_b1_end_to_end_public_chain_and_aggregate(
        tmp_path: Path, name: str, expected: str) -> None:
    """B1 六案端到端(真实公共链):sample 桶与聚合
    environment_conflict_rate 同源 —— 四不支持单位案不再记
    compatible/essential_conflict;两合法正控保持;details 携带单位
    reason 码、mapping_disclosures 机读保留原 unit/value/key。"""
    _name, key, value, unit, fact_makers, _expected, unit_kind = \
        _b1_case(name)
    plan = _plan(select=1)
    plan["condition_facts"] = [make() for make in fact_makers]
    graph = synth_reference_graph(graph_id="rg-" + name)
    graph["edges"] = graph["edges"][:1]
    graph["edges"][0]["condition_requirements"] = [
        req(key, value, unit=unit)]
    for node in graph["nodes"]:
        node["condition_scope"] = []
    run_id = "condition-r2-" + name
    runs_root, out = _run(tmp_path / name, run_id, plan)
    digest = out["native_export"]["export_digest"]
    output = _evaluate_graph(tmp_path / name, run_id, digest, graph)
    sample = output["sample_results"][0]
    assert sample["scoring_status"] == "scored", name
    conflicts = sample["environment_conflicts"]
    assert conflicts["buckets"] == {expected: 1}, name
    # 聚合同源传导(公开 sample 结果 → 聚合不得仍记 compatible/conflict)
    metric = next(m for m in output["aggregate_metrics"]
                  if m["metric_id"] == "environment_conflict_rate")
    assert metric["buckets"] == {expected: 1}, name
    if expected == "condition_unknown":
        detail = next(d for d in conflicts["details"]
                      if d["key"] == key)
        assert "requirement_unit_not_representable" in detail["reason"]
        disclosures = [d for d in conflicts["mapping_disclosures"]
                       if d.get("kind") == unit_kind]
        assert disclosures, name
        assert disclosures[0]["unit"] == unit, name
        assert disclosures[0]["value"] == repr(value), name
        assert disclosures[0]["key"] == key, name


# ------------------------------------------------------- B2 文字↔实现同真

def test_s5a02_r2_b2_checked_builder_and_order_gates() -> None:
    """B2 事实纠错守门(评审 R2 §5-B2):合法公共链的 unknown 事实经
    checked ``build_condition_fact`` 值清 None(不带身份)⇒

    - 同键**相反** present×absent 事实:两序均 unknown(承诺范围);
    - known×unknown 混合:两序均按已知事实裁决(present ⇒ compatible/
      absent ⇒ essential_conflict;mimo 的"任意多事实 unknown 且顺序
      相关"读码推论不成立,如实钉住);
    - 直接 dataclass 绕过 checked 构造器的低层次序差异另列 P2,
      不在本契约内(不测、不背书)。"""
    built = build_condition_fact(
        key="electron_acceptor", value="O2", status="unknown")
    assert built.value is None  # checked 构造器:unknown 值不可知
    present = fact("electron_acceptor", "O2")
    absent = fact("electron_acceptor", "O2", "known_absent")
    unknown = fact("electron_acceptor", "O2", "unknown")
    requirement = req("electron_acceptor", "O2")
    for fs in ([present, absent], [absent, present]):
        result = _detailed(requirement, fs)
        assert result["classification"] == "condition_unknown"
        assert "conflicting_applicable_facts" in result["reason"]
    for fs in ([present, unknown], [unknown, present]):
        assert classify_condition_requirement(requirement, fs) == \
            "compatible"
    for fs in ([absent, unknown], [unknown, absent]):
        assert classify_condition_requirement(requirement, fs) == \
            "essential_conflict"


# --------------------------------------- r1 条件案全保持(18 旧同源 + 2 单列)

_R1_CONDITION_CASES = [
    "missing_fact", "same_known_present", "opposite_known_present",
    "same_known_absent", "other_known_absent", "numeric_known_absent",
    "entity_other_known_absent", "canonical_unit_positive",
    "unit_unknown", "unit_mismatch_K", "unit_noncanonical_F",
    "conflicting_facts_conflict_first",
    "conflicting_facts_satisfied_first", "necessity_no_source",
    "zero_point_present", "negative_interval_present",
    "dict_interval_present", "matrix_label_unresolved",
    "required_absent_fact_absent", "required_absent_fact_present",
]


def test_s5a02_r2_r1_condition_cases_all_preserved() -> None:
    """单位收口不破坏 r1 的 20 条件案口径(18 旧同源对照 + 2
    required_absent 单列 not_representable)。"""
    from test_ppv1_s5a_rework_r1 import _condition_case
    for name in _R1_CONDITION_CASES:
        requirement, facts, expected, _frozen = _condition_case(name)
        assert classify_condition_requirement(requirement, facts) == \
            expected, name


# ------------------------------------------------------ 契约版本与冻结守卫

_FROZEN_SHA256 = "7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872" \
    "efedf5f886503c4907064e4"
_FREEZE_RECORD_SHA256 = "6e046e2970a102c63e693cebb81f2564b5d79fea" \
    "1b6e7a776b0fc00c09662610"

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FROZEN_DOC = _REPO_ROOT / "docs" / \
    "POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md"
_FREEZE_RECORD_DOC = _REPO_ROOT / "docs" / \
    "POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md"
# G01 安全隔离树按白名单只复制 src/tests/configs/scripts/assets,
# 不含 docs/ ⇒ 冻结文本守卫在隔离树内显式跳过(不凑执行),字节完整性
# 由证据层 shasum 封包核验(见 review_evidence r2 目录 frozen_
# integrity.json);仓内树与父全量 worktree 内该文件在场,守卫执行。


@pytest.mark.skipif(
    not _FROZEN_DOC.exists() or not _FREEZE_RECORD_DOC.exists(),
    reason="frozen criteria text not copied into allowlisted isolation "
           "trees (G01 boundary); byte integrity verified at the "
           "evidence level (shasum in review_evidence package)")
def test_s5a_r2_contract_version_registration_and_frozen_integrity() \
        -> None:
    """S5a 回修 r2:评测契约 -2→-3、模板 -2→-3、profile -21→-22
    (S5A-02 单位收口语义由 evaluation-3 承载;reference-graph/
    split-manifest 字段形状零变化);criteria-v1 冻结正文与
    FREEZE_RECORD 逐字节不改(单位是消费侧语义)。"""
    assert PPV1_EVALUATION_VERSION == "ppv1-evaluation-5"
    assert PPV1_PREREGISTRATION_TEMPLATE_VERSION == \
        "ppv1-preregistration-template-3"
    # S5a 回修 r3:profile -22→-23(S5A-05 消费侧引用绑定 +
    # 五处 P2 文案;evaluation-3/template-3 版本号不变);
    # S5b 启动批:evaluation-3→-4(qid 感知配对)+ profile -23→-24;
    # S5b 启动批回修:evaluation-4→-5(real 档配对禁
    # root_identity_fallback,S5B-L01)+ profile -24→-25
    assert PPV1_PROFILE_SCHEMA_VERSION == "ppv1-profile-25"
    assert PPV1_REFERENCE_GRAPH_VERSION == "ppv1-reference-graph-1"
    assert PPV1_SPLIT_MANIFEST_VERSION == "ppv1-split-manifest-1"
    repo = Path(__file__).resolve().parents[1]
    frozen = repo / "docs" / "POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md"
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == \
        _FROZEN_SHA256
    record = repo / "docs" / "POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md"
    assert hashlib.sha256(record.read_bytes()).hexdigest() == \
        _FREEZE_RECORD_SHA256
