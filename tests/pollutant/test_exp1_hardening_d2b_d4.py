"""EXP1 硬化 D2b + D4 实施测试(任务书
``docs/tasks/active/TASK_EXP1_HARDEN_D2B_D4_IMPL_2026-11-06.md`` §3)。

环境纪律:零真实模型、零网络、零金标、零题面 —— 全部走
``ScriptedRealModelAdapter`` 与合成通用分子(乙醇/乙酸/水/甲烷级);
判分代码(evaluation.py / s5b_scoring.py)零 import。

覆盖面:
- D2b 负控×3:atom_edit 分支 novel ``reaction_spec`` 分别携带
  ``participants`` / ``co_substrate_states`` / ``declared_copy_components``
  ⇒ 各自格式错误 + detail 禁键标记;
- D2b 翻转(CC 2026-11-06 拍板 PC8):product_first 分支同一批键改回
  **静默忽略 + entry.ignored_spec_keys 记录**(不抛错;事件参与物只能
  来自编译器生成的 spec);atom_edit 分支的拒收判据不动;
- D2b 正控:不带三键 ⇒ 两分支照常解析;池条目提案(非 novel)不受
  影响(检查只作用于 novel reaction_spec);
- D2b 正控(例外路径):池侧共底物声明路径(``prepare_hypothesis``
  池条目 spec,三键全带)照常装配 —— 本检查只在模型响应解析入口;
- D4 冻结:发车后 ``orchestration.json`` 含 sampling 块,当前全
  ``provider_default_unset``;同批根续跑同值放行、改值拒;D4 之前的
  旧批无键 ⇒ 发车侧拒绝升级(loader 单独读取仍返回 None);
- D4 装载器 fail-closed:坏块(非对象/键集不符/值非法)结构化拒;
- D4 身份:run identity / ``_prediction_block`` 出现 sampling 字段
  (A 臂也写);发送侧实际设参时(注入 temperature=0.2 的假发送配置)
  冻结值反映实际值;off(无模型)不加该键(旧 off 身份逐字段不变);
- A 臂字节硬门:系统提示词与用户载荷 sha256 == PF7 基线(与
  tests/pollutant/test_exp1_product_first.py 同一基线;此处独立双抄
  冻结字面量,两个文件各自把关)。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.model_protocol import (  # noqa: E402
    FORMAT_ERROR_JSON_FIELD,
    NOVEL_REACTION_SPEC_FORBIDDEN_KEYS,
    ModelProtocolError,
    parse_model_proposals,
)
from pathway_v43.pollutant.production import (  # noqa: E402
    build_product_state,
    prepare_hypothesis,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    NOVEL_PROTOCOL_ATOM_EDIT,
    NOVEL_PROTOCOL_PRODUCT_FIRST,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    SAMPLING_PARAM_KEYS,
    SAMPLING_PARAM_UNSET,
    ScriptedRealModelAdapter,
    build_proposals_user_payload,
    proposals_system_prompt,
    sampling_params_sent,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    _prediction_block,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_SAMPLING_PARAMS_KEY,
    S5bOrchestratorError,
    load_sampling_params,
    run_s5b_batch,
)

# ---------------------------------------------------------------- 合成夹具

SUBSTRATE = "CCO"                    # 乙醇(通用合成分子;零题面)
PRODUCT = "CC=O"                     # 乙醛
WATER = "O"                          # 通用共底物
COPY_FRAGMENT = "C"                  # 通用拷贝组分片段(甲烷)

# PF7 基线(与 tests/pollutant/test_exp1_product_first.py 同一冻结值;
# 刻意双抄:两个文件各自独立把关 A 臂字节)
PF7_PROMPT_SHA256 = \
    "c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598"
PF7_PAYLOAD_SHA256 = \
    "aab7d6e4d18043b3976e43e2bddf04ae866fed9f418dc8039bbe8786c0f6bcff"
PF7_SUBSTRATE = "CCO"
PF7_ATOM_ID_MAP = {"0": "C", "1": "C", "2": "O", "3": "H", "4": "H",
                   "5": "H", "6": "H", "7": "H", "8": "H"}
PF7_POOL_ENTRIES = [
    {"hypothesis_id": "SYN-POOL-001", "product_smiles": "CC(=O)O",
     "transformation_ref": "rhea:12345", "coproducts": []},
    {"hypothesis_id": "SYN-POOL-002", "product_smiles": "O=Cc1ccccc1",
     "transformation_ref": "rhea:67890", "coproducts": ["O"]},
]

ATOM_SPEC = {
    "product_smiles": PRODUCT,
    "coproducts": [],
    "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
               "atom2": "S_O_1", "from_order": "single",
               "to_order": "double"}],
    "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_C_2": "S_C_2",
                                       "S_O_1": "S_O_1"},
                  "ref": "self-declared"},
    "expectation": {"target_smiles": PRODUCT},
}

FORBIDDEN_VALUES = {
    # 每个禁键给一个"看起来合法"的真值形状(证明拒收不靠值形状)
    "participants": [
        {"state_ref": "cs_fake", "side": "reactant",
         "role": "cosubstrate", "coefficient": "1",
         "coefficient_status": "known"}],
    "co_substrate_states": [
        {"smiles": WATER, "state_ref": "cs_fake", "source_ref": "corpus"}],
    "declared_copy_components": [
        {"smiles": COPY_FRAGMENT, "state_ref": "cs_fake",
         "component_source": "record_declared_copy", "record_key": "r",
         "provenance_sha256": "0" * 64}],
}


def _novel_item(product: str = PRODUCT,
                reaction_spec: dict | None = None) -> dict:
    return {
        "hypothesis_id": "novel-1",
        "proposal_context": {"reference_hypothesis_ids": [],
                             "output_origin": "novel_outside_pool"},
        "reaction_spec": (dict(ATOM_SPEC) if reaction_spec is None
                          else reaction_spec),
    }


def _response(proposals: list[dict]) -> str:
    return json.dumps({
        "proposals": proposals,
        "rank_hypotheses": [p["hypothesis_id"] for p in proposals]},
        ensure_ascii=False)


def _atom_spec_with(key: str) -> dict:
    spec = json.loads(json.dumps(ATOM_SPEC))
    spec[key] = json.loads(json.dumps(FORBIDDEN_VALUES[key]))
    return spec


def _pf_spec_with(key: str) -> dict:
    return {"product_smiles": PRODUCT,
            key: json.loads(json.dumps(FORBIDDEN_VALUES[key]))}


# ======================================================== D2b 负控(atom_edit)

@pytest.mark.parametrize("key", list(NOVEL_REACTION_SPEC_FORBIDDEN_KEYS))
def test_d2b_atom_edit_rejects_forbidden_key(key: str) -> None:
    """neg×3:atom_edit 分支 novel reaction_spec 的任一禁键 ⇒ 格式错误
    (kind=json_field_error)且 detail 带实际命中的禁键标记。"""
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(
            _response([_novel_item(reaction_spec=_atom_spec_with(key))]),
            allowed_hypothesis_ids=[])
    detail = excinfo.value.detail
    assert detail["kind"] == FORMAT_ERROR_JSON_FIELD
    assert detail["novel_reaction_spec_forbidden_keys"] == [key]
    assert detail["hypothesis_id"] == "novel-1"
    assert detail["index"] == 0


def test_d2b_detail_lists_all_hit_keys() -> None:
    """三个禁键同时出现 ⇒ detail 完整列出(不吞键,便于处置)。"""
    spec = json.loads(json.dumps(ATOM_SPEC))
    for key in NOVEL_REACTION_SPEC_FORBIDDEN_KEYS:
        spec[key] = json.loads(json.dumps(FORBIDDEN_VALUES[key]))
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(_response([_novel_item(reaction_spec=spec)]),
                              allowed_hypothesis_ids=[])
    assert excinfo.value.detail["novel_reaction_spec_forbidden_keys"] == \
        list(NOVEL_REACTION_SPEC_FORBIDDEN_KEYS)


# ================================================ D2b 忽略+记录(product_first)

@pytest.mark.parametrize("key", list(NOVEL_REACTION_SPEC_FORBIDDEN_KEYS))
def test_d2b_product_first_ignores_and_records_forbidden_key(
        key: str) -> None:
    """产品优先分支(CC 2026-11-06 PC8 拍板):模型多写的池侧声明键
    **静默忽略** —— 不抛错、reaction_spec 只保留 product_smiles/
    coproducts,被忽略的键名记录在 entry.ignored_spec_keys。

    atom_edit 分支的拒收判据(D2b 验收面)不受影响,见上方负控。"""
    out = parse_model_proposals(
        _response([_novel_item(reaction_spec=_pf_spec_with(key))]),
        allowed_hypothesis_ids=[],
        protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    entry = out["proposals"][0]
    assert entry["reaction_spec"] == {"product_smiles": PRODUCT,
                                      "coproducts": []}
    assert entry["ignored_spec_keys"] == [key]
    assert out["protocol_version"] == "ppv1-model-proposals-3"


# ======================================================== D2b 正控(两臂)

def test_d2b_clean_novel_parses_in_both_arms() -> None:
    """正控:不带三键的 novel 提案两分支照常解析(拒收不误伤合法面)。"""
    atom_out = parse_model_proposals(
        _response([_novel_item()]), allowed_hypothesis_ids=[])
    assert atom_out["proposals"][0]["reaction_spec"]["product_smiles"] == \
        PRODUCT
    assert atom_out["protocol_version"] == "ppv1-model-proposals-2"

    pf_out = parse_model_proposals(
        _response([_novel_item(reaction_spec={"product_smiles": PRODUCT})]),
        allowed_hypothesis_ids=[],
        protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    assert pf_out["proposals"][0]["reaction_spec"] == {
        "product_smiles": PRODUCT, "coproducts": []}
    assert pf_out["protocol_version"] == "ppv1-model-proposals-3"


def test_d2b_pool_entry_proposals_unaffected() -> None:
    """检查只作用于 novel reaction_spec:池条目引用(origin=frozen_pool)
    不受影响(不把合法池路径一并拒)。"""
    out = parse_model_proposals(
        _response([{"hypothesis_id": "SYN-POOL-001",
                    "coproducts": ["O"]}]),
        allowed_hypothesis_ids=["SYN-POOL-001"])
    assert out["proposals"][0]["origin"] == "frozen_pool"
    # 池条目即使携带同名键也不经 reaction_spec 解析(不读该字段)
    out2 = parse_model_proposals(
        _response([{"hypothesis_id": "SYN-POOL-001",
                    "reaction_spec": _atom_spec_with("participants")}]),
        allowed_hypothesis_ids=["SYN-POOL-001"])
    assert out2["proposals"][0]["origin"] == "frozen_pool"


# ===================================== D2b 正控(例外:池侧共底物声明路径)

def test_d2b_pool_side_cosubstrate_declaration_positive_control() -> None:
    """例外路径正控:池侧共底物声明(三键全带)不经
    parse_model_proposals,照常经 prepare_hypothesis 装配 —— 新检查只
    加在模型响应解析入口,不给池条目/记录侧声明加门。

    同一份 reaction_spec 形状若作为**模型响应**提交 ⇒ 被拒(证明门
    确实在,而不是没生效)。
    """
    substrate_state = build_product_state(
        SUBSTRATE, source_refs=[{"record": "d2b-exception-sub"}])
    product_state = build_product_state(
        PRODUCT, source_refs=[{"record": "d2b-exception-prod"}])
    water_state = build_product_state(
        WATER, source_refs=[{"record": "corpus"}])
    copy_state = build_product_state(
        COPY_FRAGMENT,
        source_refs=[{"record": "synthetic-cosub-record-1",
                      "component_source": "record_declared_copy"}])
    pool_spec = {
        **json.loads(json.dumps(ATOM_SPEC)),
        "participants": [
            {"state_ref": substrate_state.state_id, "side": "reactant",
             "role": "primary_substrate", "coefficient": "1",
             "coefficient_status": "known"},
            {"state_ref": water_state.state_id, "side": "reactant",
             "role": "cosubstrate", "coefficient": None,
             "coefficient_status": "unknown"},
            {"state_ref": product_state.state_id, "side": "product",
             "role": "principal_product", "coefficient": "1",
             "coefficient_status": "known"},
            {"state_ref": copy_state.state_id, "side": "product",
             "role": "coproduct", "coefficient": None,
             "coefficient_status": "unknown"},
        ],
        "co_substrate_states": [
            {"smiles": WATER, "state_ref": water_state.state_id,
             "source_ref": "corpus"}],
        "declared_copy_components": [
            {"smiles": COPY_FRAGMENT, "state_ref": copy_state.state_id,
             "component_source": "record_declared_copy",
             "record_key": "synthetic-cosub-record-1",
             "provenance_sha256": "0" * 64}],
        "cosubstrate_event_contract": {
            "record_key": "synthetic-cosub-record-1",
            "co_substrates": [{"smiles": WATER}],
            "record_products": [PRODUCT, COPY_FRAGMENT],
            "copy_state_refs": [copy_state.state_id]},
    }
    prepared = prepare_hypothesis(
        pool_spec, parent_path_id="pp-d2b-exception",
        substrate_state=substrate_state)
    disclosure = prepared["cosubstrate_disclosure"]
    assert disclosure is not None
    assert disclosure["declaration_sources"] == \
        ["cosubstrate_event_contract"]
    assert water_state.state_id in disclosure["co_substrate_state_refs"]
    copies = disclosure["declared_copy_components"]
    assert [c["smiles"] for c in copies] == [COPY_FRAGMENT]
    assert copies[0]["execution_status"] == "declared_not_executed"
    assert copies[0]["state_ref"] == copy_state.state_id
    assert copy_state.state_id in prepared["states"]

    # 同一 reaction_spec 形状走**模型响应**解析入口 ⇒ 拒(门在)
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(
            _response([_novel_item(reaction_spec={
                k: v for k, v in pool_spec.items()
                if k in ("product_smiles", "coproducts", "edits", "donor",
                         "alignment", "expectation", "participants",
                         "co_substrate_states",
                         "declared_copy_components")})]),
            allowed_hypothesis_ids=[])
    assert excinfo.value.detail["novel_reaction_spec_forbidden_keys"] == \
        ["participants", "co_substrate_states", "declared_copy_components"]


# ======================================================== D4 单一来源函数

def test_d4_sampling_params_single_source() -> None:
    """单一来源函数:未设 ⇒ 每键 provider_default_unset;设了 ⇒ 值原样
    (不推断提供者默认、不复制入参、不改键集)。"""
    assert sampling_params_sent() == {
        key: SAMPLING_PARAM_UNSET for key in SAMPLING_PARAM_KEYS}
    assert sampling_params_sent({}) == sampling_params_sent()
    sent = sampling_params_sent({"temperature": 0.2, "top_p": 0.9,
                                 "reasoning_effort": "max"})
    assert sent["temperature"] == 0.2
    assert sent["top_p"] == 0.9
    assert sent["top_k"] == SAMPLING_PARAM_UNSET
    # 非采样键(request_params 里的思考参数)不进采样快照
    assert "reasoning_effort" not in sent
    # 入参不被改写(只读函数)
    params = {"temperature": 0.2}
    sampling_params_sent(params)
    assert params == {"temperature": 0.2}


# ======================================================== D4 发车冻结

def _scripted_batch(tmp_path: Path, tag: str) -> Path:
    questions = tmp_path / f"q-{tag}.jsonl"
    questions.write_text(json.dumps(
        {"qid": "SYNTH-D4-1", "substrate_smiles": SUBSTRATE,
         "products_smiles": [PRODUCT],
         "raw_reaction": f"{SUBSTRATE}>>{PRODUCT}"}) + "\n",
        encoding="utf-8")
    batch_root = tmp_path / f"batch-{tag}"
    build_question_batch(
        questions, batch_root, batch_tag=f"d4-{tag}",
        pool_provider=lambda s: [{
            "key": "rec-SYNTH_D4@L3", "product_smiles": PRODUCT,
            "coefficient": 1, "transformation_ref": "SYNTH_D4@L3",
            "origin_group_key": "rec-source:SYNTH_D4@L3",
            "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                       "atom2": "S_O_1", "from_order": "single",
                       "to_order": "double"}],
            "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
            "alignment": {"status": "resolved",
                          "donor_to_current": {"S_C_2": "S_C_2",
                                               "S_O_1": "S_O_1"},
                          "equivalence_classes": [],
                          "ref": "align-d4"},
            "expectation": {"target_smiles": PRODUCT}}],
        provider_kind="scripted", synthetic_review=True)
    return batch_root


def test_d4_orchestration_freeze_and_resume(tmp_path, monkeypatch) -> None:
    """发车冻结:orchestration.json 含 sampling 块且全
    provider_default_unset;同批根续跑同值放行;改值 ⇒ 冲突拒。"""
    stub = tmp_path / "stub.json"
    stub.write_text(json.dumps({"strategy": "responses",
                                "responses": [
                                    '{"proposals": [], '
                                    '"rank_hypotheses": []}']}),
                    encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub))
    batch_root = _scripted_batch(tmp_path, "freeze")
    runs_root = tmp_path / "runs-freeze"
    run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                  poll_s=0.05, gate_max_calls=50)

    frozen = json.loads((batch_root / "orchestration.json").read_text(
        encoding="utf-8"))
    assert S5B_SAMPLING_PARAMS_KEY in frozen
    block = frozen[S5B_SAMPLING_PARAMS_KEY]
    assert set(block) == set(SAMPLING_PARAM_KEYS)
    assert set(block.values()) == {SAMPLING_PARAM_UNSET}
    # 装载器读回同值(单一验证源)
    assert load_sampling_params(batch_root) == block

    # 同批根续跑(同值)⇒ 放行(已完成的题 SKIP)
    run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                  poll_s=0.05, gate_max_calls=50)
    assert load_sampling_params(batch_root) == block

    # 改冻结值(改成合法数值)⇒ 批身份冲突拒
    tampered = dict(frozen)
    tampered[S5B_SAMPLING_PARAMS_KEY] = {
        **block, "temperature": 0.2}
    (batch_root / "orchestration.json").write_text(
        json.dumps(tampered, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(batch_root, runs_root=runs_root, workers=1,
                      poll_s=0.05, gate_max_calls=50)
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"
    assert excinfo.value.detail["requested_sampling_params"][
        "temperature"] == SAMPLING_PARAM_UNSET


def test_d4_old_batch_without_block_rejected_at_launch(tmp_path) -> None:
    """D4 之前的旧批(冻结副本无 sampling 块):发车侧不得静默升级成
    带采样身份的批(结构化拒);loader 单独读取仍按契约返回 None。"""
    batch_root = _scripted_batch(tmp_path, "old")
    # 只有版本键的旧形状冻结副本(无 sampling 块)
    (batch_root / "orchestration.json").write_text(json.dumps({
        "orchestrator_version": "s5b-orchestrator-3"}), encoding="utf-8")
    assert load_sampling_params(batch_root) is None
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(batch_root, runs_root=tmp_path / "runs-old",
                      workers=1, poll_s=0.05, gate_max_calls=50)
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"
    assert excinfo.value.detail["reason"] == \
        "frozen_sampling_params_missing"


# ======================================================== D4 装载器

def _write_orch(root: Path, payload) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "orchestration.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return root


def test_d4_loader_absent_is_none(tmp_path) -> None:
    """orchestration.json 缺席 / 在场但无该键 ⇒ None(旧批合法读取)。"""
    assert load_sampling_params(tmp_path / "no-such-batch") is None
    assert load_sampling_params(
        _write_orch(tmp_path / "no-key",
                    {"orchestrator_version": "s5b-orchestrator-3"})) is None


def test_d4_loader_accepts_legal_block(tmp_path) -> None:
    """合法块原样读回(数值/布尔/字符串都合法)。"""
    block = {**{key: SAMPLING_PARAM_UNSET for key in SAMPLING_PARAM_KEYS},
             "temperature": 0.2, "top_p": 1, "seed": 42}
    out = load_sampling_params(
        _write_orch(tmp_path / "legal",
                    {S5B_SAMPLING_PARAMS_KEY: block}))
    assert out == {key: block[key] for key in SAMPLING_PARAM_KEYS}


@pytest.mark.parametrize("block", [
    ["not", "an", "object"],
    "provider_default_unset",
    None,
    {key: SAMPLING_PARAM_UNSET
     for key in SAMPLING_PARAM_KEYS if key != "temperature"},   # 缺键
    {**{key: SAMPLING_PARAM_UNSET for key in SAMPLING_PARAM_KEYS},
     "unexpected_knob": 1},                                     # 未知键
])
def test_d4_loader_bad_block_shapes_fail_closed(tmp_path, block) -> None:
    """坏块(非对象/缺键/未知键)⇒ 结构化拒,不当缺省。"""
    root = _write_orch(tmp_path / "batch",
                       {S5B_SAMPLING_PARAMS_KEY: block})
    with pytest.raises(S5bOrchestratorError) as excinfo:
        load_sampling_params(root)
    assert excinfo.value.detail["kind"] == "s5b_sampling_params_invalid"


@pytest.mark.parametrize("value", [None, [], {}, "", True, 0.0])
def test_d4_loader_bad_values_fail_closed(tmp_path, value) -> None:
    """null/对象/数组/空串 ⇒ 拒;布尔与数值(含 0.0)是合法发送值。"""
    block = {**{key: SAMPLING_PARAM_UNSET for key in SAMPLING_PARAM_KEYS},
             "temperature": value}
    root = _write_orch(tmp_path / "batch",
                       {S5B_SAMPLING_PARAMS_KEY: block})
    if isinstance(value, (bool, int, float)) and value is not None:
        assert load_sampling_params(root)["temperature"] == value
        return
    with pytest.raises(S5bOrchestratorError) as excinfo:
        load_sampling_params(root)
    assert excinfo.value.detail["kind"] == "s5b_sampling_params_invalid"


def test_d4_loader_unreadable_orchestration_fail_closed(tmp_path) -> None:
    """冻结副本不可解析 ⇒ fail-closed(不静默当旧批)。"""
    root = tmp_path / "corrupt"
    root.mkdir()
    (root / "orchestration.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        load_sampling_params(root)
    assert excinfo.value.detail["kind"] == "s5b_sampling_params_invalid"


# ======================================================== D4 run identity

class _SamplingStub(ScriptedRealModelAdapter):
    """scripted 桩 + 与真实适配器同形的 request_params 身份块(离线,
    零网络;用于证明"发送侧设了什么,run identity 就记什么")。"""

    def __init__(self, request_params: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.request_params = dict(request_params or {})

    def identity_block(self) -> dict:
        block = super().identity_block()
        block["request_params"] = dict(self.request_params)
        return block


def _run_a_arm(tmp_path: Path, run_id: str, model) -> dict:
    plan = {"pools": {SUBSTRATE: [{
                "key": "rec-SYNTH_D4@L3", "product_smiles": PRODUCT,
                "coefficient": 1, "transformation_ref": "SYNTH_D4@L3",
                "origin_group_key": "rec-source:SYNTH_D4@L3",
                "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                           "atom2": "S_O_1", "from_order": "single",
                           "to_order": "double"}],
                "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
                "alignment": {"status": "resolved",
                              "donor_to_current": {"S_C_2": "S_C_2",
                                                   "S_O_1": "S_O_1"},
                              "equivalence_classes": [],
                              "ref": "align-d4"},
                "expectation": {"target_smiles": PRODUCT}}]},
            "model": {"provider_kind": "scripted"}}
    return start_ppv1_run(
        config=resolve_config(),
        runs_root=tmp_path / "runs", run_id=run_id, smiles=SUBSTRATE,
        plan=plan, model=model, scripted=True,
        evidence_card_enabled=True, evidence_card_version="v1card",
        novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT)


def test_d4_run_identity_records_sampling_and_a_arm_bytes(tmp_path) -> None:
    """A 臂 run identity 出现 sampling 字段(默认全 provider_default_unset);
    系统提示词仍 == PF7 基线,载荷零采样键(硬门)。"""
    model = _SamplingStub(
        strategy="responses",
        responses=['{"proposals": [], "rank_hypotheses": []}'])
    _run_a_arm(tmp_path, "d4-a", model)
    identity = json.loads(
        (tmp_path / "runs" / "d4-a" / "run_identity.json").read_text(
            encoding="utf-8"))
    sampling = identity["prediction"]["sampling_params"]
    assert set(sampling) == set(SAMPLING_PARAM_KEYS)
    assert set(sampling.values()) == {SAMPLING_PARAM_UNSET}
    # profile 块本任务不动(见交付书:采样参数归 prediction 块单一去处)
    assert "sampling_params" not in identity["profile"]
    # A 臂系统提示词字节硬门
    assert model.seen_system_prompts[0] == proposals_system_prompt("v2")
    assert hashlib.sha256(
        model.seen_system_prompts[0].encode("utf-8")).hexdigest() == \
        PF7_PROMPT_SHA256
    # 实跑载荷同样零采样键(采样快照不进请求体)
    run_payload = json.loads(model.seen_user_payloads[0])
    assert "sampling_params" not in run_payload
    for key in SAMPLING_PARAM_KEYS:
        assert key not in run_payload


def test_d4_real_adapter_params_reflected_in_identity(tmp_path,
                                                    monkeypatch) -> None:
    """发送侧真设采样参数(注入 temperature=0.2/top_p=0.9 的假发送
    配置)⇒ 冻结快照反映实际值,其余键仍 provider_default_unset。"""
    from pathway_v43.adapters.llm_client import OpenAICompatibleClient
    from pathway_v43.pollutant.real_model import RealModelAdapter

    monkeypatch.delenv("V43_LLM_REQUEST_PARAMS", raising=False)
    monkeypatch.delenv("V43_LLM_RATE_GATE", raising=False)
    client = OpenAICompatibleClient(
        base_url="http://offline.invalid", api_key="offline-key",
        model="synthetic-model", request_params={
            "temperature": 0.2, "top_p": 0.9})
    adapter = RealModelAdapter(client)
    block = _prediction_block(adapter)
    assert block["sampling_params"]["temperature"] == 0.2
    assert block["sampling_params"]["top_p"] == 0.9
    for key in SAMPLING_PARAM_KEYS:
        if key not in ("temperature", "top_p"):
            assert block["sampling_params"][key] == SAMPLING_PARAM_UNSET
    # 单一来源一致性:函数(适配器 request_params) == 身份块字段
    assert block["sampling_params"] == sampling_params_sent(
        adapter.request_params)


def test_d4_off_prediction_block_unchanged() -> None:
    """无模型(off,不发送)不写 sampling 键 —— 旧 off 身份块逐字段不变
    (integration/test_prediction_recovery.py 的精确 dict 断言同口径)。"""
    block = _prediction_block(None)
    assert block == {
        "enabled": False, "provider": "off", "model_id": "",
        "prompt_versions": {}, "policy_version": "v43-predpol-3",
        "policy": {}}


def test_d4_payload_builder_has_no_sampling_keys() -> None:
    """A 臂载荷构造器零新增键:采样快照只进身份/冻结,不进请求体。"""
    payload = build_proposals_user_payload(
        substrate_smiles=PF7_SUBSTRATE, atom_id_map=PF7_ATOM_ID_MAP,
        pool_entries=PF7_POOL_ENTRIES)
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == \
        PF7_PAYLOAD_SHA256
    body = json.loads(payload)
    for key in SAMPLING_PARAM_KEYS:
        assert key not in body
    assert "sampling_params" not in body


def test_d4_sampling_is_not_a_request_param_family() -> None:
    """采样键集与 llm_client 的请求参数禁令不冲突:temperature 不在
    request_params 家族(它是 policy 单通道),快照只读请求参数。"""
    from pathway_v43.adapters.llm_client import (
        FORBIDDEN_REQUEST_PARAM_KEYS,
    )

    assert "temperature" in FORBIDDEN_REQUEST_PARAM_KEYS
    # 采样键集与禁令键共同构成"发送侧可见"面:快照把未设记 unset,
    # 不把禁令键当作已发送
    assert sampling_params_sent({"top_p": 0.5})["temperature"] == \
        SAMPLING_PARAM_UNSET