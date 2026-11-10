"""P2 `v1card` 模式离线实施测试（2026-10-21）。

任务书：docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md §3.3（7 条最小实现
合同）；预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` §2.2/§2.3。

覆盖（§3.3 第 6 条逐项）：
- A（v1card）用户载荷与 v1 B 臂逐字节等价（system prompt 除外）；
- v2 prompt 哈希不变（两臂同 v2 prompt）；
- A/B 身份键（version/schema/descriptor/RDKit/prompt hash/summary）；
- resume 版本拒错（缺失/换版本/坏值）；
- 双跑字节一致；
- v1 证据函数未被改（锚定 r2 补丁前基线哈希）与 off 路径零漂移。

环境纪律：零模型零网络（scripted 桩同载荷路径）；零金标零题面
（合成分子与真实 298 集合零重叠）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.candidate_evidence import (  # noqa: E402
    CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION,
    CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2,
    candidate_evidence_payload,
    substrate_evidence_payload,
)
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    PROPOSALS_PROMPT_VERSION_V2,
    ScriptedRealModelAdapter,
    _PROPOSALS_SYSTEM_PROMPT,
    proposals_system_prompt,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    _resolve_evidence_card_version,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_PROFILE_POLICY,
)

# 集成冻结点（2026-10-21 P2 集成，chemfix N 轮）：
# - V1 prompt 自 r2 实现起逐字节不变；
# - V2 prompt 以 chemfix 最终版（N1/N2/N5 收口）后的值为准，
#   取代 r2 的 89311fdb… 与上一版 e2aa2bbf…。两臂共用本常量。
V1_PROMPT_SHA256 = (
    "fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e")
V2_PROMPT_SHA256 = (
    "c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598")
# r2 补丁前基线（docs/review_evidence/p2_evidence_card_v2_2026-10-21/
# off_path_baseline.json）的 v1 证据/off 载荷哈希。
V1_CANDIDATE_EVIDENCE_SHA256 = (
    "61cd96a9a0f012e132d45a67ccc93df1b27a8e9d4cf1ce9cd7553de5d52e8960")
V1_SUBSTRATE_EVIDENCE_SHA256 = (
    "18a62e52fd5cb9519bbb577067e9a7c6b4fec3ebd5f917e524523e96490475d3")
OFF_PATH_A_PAYLOAD_SHA256 = (
    "c2526a7fb47b43dc08ca5422d01787456581777ed4014087aece2c09bce1799d")
OFF_PATH_B_PAYLOAD_SHA256 = (
    "b8f66ed9367c4325fc48ec07aec96ceb0d32c2fd215fd856deb2851a4621981e")


def _spec() -> dict:
    """合成池条目；与 r2 off-path 基线探针同一输入（哈希锚定可比）。"""
    return {
        "key": "rec-P2OFF-0001@L3", "product_smiles": "CC=O",
        "coefficient": 1,
        "transformation_ref": "P2OFF-0001@L3",
        "origin_group_key": "rec-source:P2OFF-0001@L3",
        "edits": [
            {"op": "change_bond_order", "atom1": "S_C_2",
             "atom2": "S_O_1", "from_order": "single",
             "to_order": "double"},
            {"op": "add_atom", "element": "O",
             "new_atom_id": "SN_O_1", "atom1": "S_C_2"},
        ],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {
            "status": "resolved",
            "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
            "equivalence_classes": [],
            "ref": "recorded-inferred:P2OFF-0001@L3"},
        "expectation": {"target_smiles": "CC=O"},
        "compile": {
            "compiler_version": "synthetic", "mapping_origin": "inferred",
            "n_alignments_total": 2, "n_equivalent_alignments": 2,
            "truncated": False, "template_center_maps": [1, 2]},
        "requirements": [
            {"key": "oxygen_regime", "level": "preference",
             "value": "aerobic", "basis": "observed_condition_reference"}],
    }


def _plan(spec: dict) -> dict:
    return {"pools": {"CCO": [spec]},
            "model": {"provider_kind": "scripted"}}


def _sha_json(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _start(tmp_path: Path, name: str, *, version: str | None,
           enabled: bool = True, run_id: str | None = None,
           model_id: str | None = None, spec: dict | None = None) -> tuple:
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id=model_id or f"p2-v1card-{name}")
    out = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / name,
        run_id=run_id or name, smiles="CCO",
        plan=_plan(_spec() if spec is None else spec), model=model,
        profile_policy=dict(S5B_DEFAULT_PROFILE_POLICY),
        evidence_card_enabled=enabled,
        evidence_card_version=version)
    return model, out


def _identity(runs_root: Path, run_id: str) -> dict:
    return json.loads(
        (runs_root / run_id / "run_identity.json").read_text())


# ---------------------------------------------------------------- 载荷字节


def test_v1card_user_payload_byte_identical_to_v1_b(tmp_path) -> None:
    """§3.3.2/§3.3.6：A 臂（v2 prompt + v1 卡）用户载荷 == v1 B 臂
    逐字节；只有 system prompt 不同。"""
    # 同 run_id、不同 runs root ⇒ parent_path/hypothesis_id 同一，载荷
    # 可直接逐字节比较（不是同形，而是同字节）。
    model_v1b, out_v1b = _start(
        tmp_path, "v1b", version=None, enabled=True,
        run_id="byte-arm", model_id="p2-byte-model")
    model_a, out_a = _start(
        tmp_path, "v1card", version="v1card", enabled=True,
        run_id="byte-arm", model_id="p2-byte-model")

    assert out_v1b["evidence_card_enabled"] is True
    assert out_v1b.get("evidence_card_version") is None
    assert out_a["evidence_card_enabled"] is True
    assert out_a["evidence_card_version"] == "v1card"

    payload_v1b = model_v1b.seen_user_payloads[0]
    payload_a = model_a.seen_user_payloads[0]
    assert payload_a == payload_v1b
    assert hashlib.sha256(payload_a.encode("utf-8")).hexdigest() == \
        hashlib.sha256(payload_v1b.encode("utf-8")).hexdigest()

    # system prompt 是唯一差异：v1 B=v1 prompt，A=v2 prompt
    assert model_v1b.seen_system_prompts == [_PROPOSALS_SYSTEM_PROMPT]
    assert model_a.seen_system_prompts == [proposals_system_prompt("v2")]
    assert model_a.seen_system_prompts != model_v1b.seen_system_prompts

    # 载荷是 v1 卡：v1 schema 标识 + v1 独有字段在位 + v2 字段缺席
    payload = json.loads(payload_a)
    assert payload["candidate_evidence_schema_version"] == \
        CANDIDATE_EVIDENCE_SCHEMA_VERSION == "candidate-evidence-2"
    assert "source" in payload["pool_hypotheses"][0]["evidence"]
    assert "coefficient_status" in json.dumps(
        payload["pool_hypotheses"][0]["evidence"])
    substrate = payload["substrate_evidence"]
    assert substrate["descriptor_version"] == \
        CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION == \
        "candidate-evidence-descr-2"
    assert "gasteiger_charges_reference" in substrate
    assert "molecular_formula" in substrate
    for v2_only in ("functional_group_delta", "product_delta"):
        assert v2_only not in payload["pool_hypotheses"][0]["evidence"]
    # 默认 JSON 分隔符（与 v1 B 同；不得用 v2 B 的紧凑分隔符）
    assert payload_a == json.dumps(
        payload, ensure_ascii=False, sort_keys=True)
    assert ", " in payload_a and ": " in payload_a


def test_arms_share_v2_prompt_but_v2_arm_payload_unchanged(tmp_path) -> None:
    """v1card 接线不得扰动 v2 B 臂：同 v2 prompt、v2 schema、紧凑分隔符。"""
    model_b, out_b = _start(
        tmp_path, "v2b", version="v2", enabled=True)
    assert out_b["evidence_card_version"] == "v2"
    assert model_b.seen_system_prompts == [proposals_system_prompt("v2")]
    raw_b = model_b.seen_user_payloads[0]
    payload_b = json.loads(raw_b)
    assert payload_b["candidate_evidence_schema_version"] == \
        CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2 == "candidate-evidence-3"
    assert payload_b["substrate_evidence"]["descriptor_version"] == \
        CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2 == \
        "candidate-evidence-descr-3"
    assert "source" not in payload_b["pool_hypotheses"][0]["evidence"]
    assert "functional_group_delta" in payload_b["pool_hypotheses"][0][
        "evidence"]
    assert ", " not in raw_b and ": " not in raw_b


# ---------------------------------------------------------------- prompt/证据


def test_v2_prompt_hash_unchanged_and_v1_evidence_frozen() -> None:
    """§3.3.6：v2 prompt 哈希不变；v1 证据函数输出与 r2 基线逐字节同。"""
    assert PROPOSALS_PROMPT_VERSION == V1_PROMPT_SHA256
    assert PROPOSALS_PROMPT_VERSION_V2 == V2_PROMPT_SHA256
    assert PROPOSALS_PROMPT_VERSION_V2 == hashlib.sha256(
        proposals_system_prompt("v2").encode("utf-8")).hexdigest()
    assert proposals_system_prompt(None) == _PROPOSALS_SYSTEM_PROMPT
    assert proposals_system_prompt("v1") == _PROPOSALS_SYSTEM_PROMPT

    spec = _spec()
    substrate = build_chemical_state("CCO", "raw_input",
                                     [{"record": "p2-v1card-synth"}])
    prepared = prepare_hypothesis(
        spec, parent_path_id="p2-off-path", substrate_state=substrate,
        transformation_ref=str(spec["transformation_ref"]))
    evidence_v1 = candidate_evidence_payload(spec=spec, prepared=prepared)
    substrate_v1 = substrate_evidence_payload("CCO")
    assert _sha_json(evidence_v1) == V1_CANDIDATE_EVIDENCE_SHA256
    assert _sha_json(substrate_v1) == V1_SUBSTRATE_EVIDENCE_SHA256
    # v1 独有事实在位（v2 字段不在）
    assert "source" in evidence_v1
    assert "coefficient_status" in json.dumps(evidence_v1)
    assert "functional_group_delta" not in evidence_v1
    assert "gasteiger_charges_reference" in substrate_v1
    assert "molecular_formula" in substrate_v1


# ---------------------------------------------------------------- 身份


def test_arms_identity_keys(tmp_path) -> None:
    """§3.3.4：A=v1card/v1 schema/descr；B=v2/v3；两臂 prompt=v2 SHA。"""
    _model_a, out_a = _start(tmp_path, "id-a", version="v1card",
                             enabled=True)
    _model_b, out_b = _start(tmp_path, "id-b", version="v2", enabled=True)
    identity_a = _identity(tmp_path / "id-a", "id-a")
    identity_b = _identity(tmp_path / "id-b", "id-b")

    strategy_a = identity_a["strategy"]
    assert strategy_a["evidence_card_version"] == "v1card"
    assert strategy_a["candidate_evidence_schema_version"] == \
        "candidate-evidence-2"
    assert strategy_a["candidate_evidence_descriptor_version"] == \
        "candidate-evidence-descr-2"
    assert strategy_a["rdkit_version"]
    assert identity_a["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION_V2

    strategy_b = identity_b["strategy"]
    assert strategy_b["evidence_card_version"] == "v2"
    assert strategy_b["candidate_evidence_schema_version"] == \
        "candidate-evidence-3"
    assert strategy_b["candidate_evidence_descriptor_version"] == \
        "candidate-evidence-descr-3"
    assert identity_b["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION_V2

    assert strategy_a["evidence_card_enabled"] is True
    assert strategy_b["evidence_card_enabled"] is True
    assert strategy_a["evidence_card_version"] != \
        strategy_b["evidence_card_version"]
    assert out_a["evidence_card_version"] == "v1card"
    assert out_b["evidence_card_version"] == "v2"


def test_off_path_identity_and_summary_have_no_v1card_keys(tmp_path) -> None:
    """§3.3.5：缺省/v1 路径 strategy/summary 不出现任何版本新键。"""
    for version, name in ((None, "off-default"), ("v1", "off-v1")):
        _model, out = _start(tmp_path, name, version=version, enabled=False)
        identity = _identity(tmp_path / name, name)
        strategy = identity["strategy"]
        for key in ("evidence_card_version",
                    "candidate_evidence_schema_version",
                    "candidate_evidence_descriptor_version",
                    "rdkit_version"):
            assert key not in strategy, (name, key)
        assert identity["prediction"]["prompt_versions"]["proposals"] == \
            PROPOSALS_PROMPT_VERSION
        assert "evidence_card_version" not in out
        assert out["evidence_card_enabled"] is False


def test_off_path_payload_hashes_match_r2_baseline(tmp_path) -> None:
    """§3.3.5：off 路径（v1 prompt + v1 无证据/有证据）载荷与 r2
    基线逐字节同（负控：任何 v2/v1card 键泄漏都会改哈希）。"""
    model_a, _out_a = _start(
        tmp_path, "base-a", version=None, enabled=False,
        run_id="p2-off-A", model_id="p2-off-A")
    model_b, _out_b = _start(
        tmp_path, "base-b", version=None, enabled=True,
        run_id="p2-off-B", model_id="p2-off-B")
    assert hashlib.sha256(
        model_a.seen_user_payloads[0].encode("utf-8")).hexdigest() == \
        OFF_PATH_A_PAYLOAD_SHA256
    assert hashlib.sha256(
        model_b.seen_user_payloads[0].encode("utf-8")).hexdigest() == \
        OFF_PATH_B_PAYLOAD_SHA256
    assert model_a.seen_system_prompts == [_PROPOSALS_SYSTEM_PROMPT]
    assert model_b.seen_system_prompts == [_PROPOSALS_SYSTEM_PROMPT]


# ---------------------------------------------------------------- 拒错


def test_v1card_requires_evidence_enabled_true(tmp_path) -> None:
    """§3.3.3：v1card + enabled=false ⇒ 结构化拒（不静默降级）。"""
    with pytest.raises(PPV1RunError) as excinfo:
        _start(tmp_path, "bad-flag", version="v1card", enabled=False)
    assert excinfo.value.detail.get("kind") == "v1card_requires_evidence"
    # 拒绝发生在创建 run 目录之前：同 id 可重试（无空目录阻塞）
    assert not (tmp_path / "bad-flag").exists()

    # v1card run 的 resume 也不接受 false
    _model, _out = _start(tmp_path, "flag-run", version="v1card",
                          enabled=True)
    with pytest.raises(PPV1RunError) as excinfo:
        resume_ppv1_run(
            config=resolve_config(), runs_root=tmp_path / "flag-run",
            run_id="flag-run", model=ScriptedRealModelAdapter(),
            evidence_card_enabled=False, evidence_card_version="v1card")
    assert excinfo.value.detail.get("kind") == "v1card_requires_evidence"


def test_invalid_version_values_still_rejected(tmp_path) -> None:
    """§3.3.1：其它非法值仍按原判据拒绝（含拼写近似/大写/非字符串）。"""
    assert _resolve_evidence_card_version(None) is None
    assert _resolve_evidence_card_version("v1") is None
    assert _resolve_evidence_card_version("v1card") == "v1card"
    assert _resolve_evidence_card_version("v2") == "v2"
    for bad in ("V1CARD", "v1-card", "v1_card", "v3", "", 1, True):
        with pytest.raises(PPV1RunError) as excinfo:
            _resolve_evidence_card_version(bad)
        assert excinfo.value.detail.get("kind") == \
            "evidence_card_version_invalid", bad
    with pytest.raises(PPV1RunError) as excinfo:
        _start(tmp_path, "bad-version", version="v1-card", enabled=True)
    assert excinfo.value.detail.get("kind") == \
        "evidence_card_version_invalid"
    assert not (tmp_path / "bad-version").exists()


def test_v1card_resume_version_gate(tmp_path) -> None:
    """§3.3.4：resume 版本缺失/不符 ⇒ evidence_card_version_mismatch；
    同版本正常续跑；坏值 ⇒ corrupt。"""
    def _resume(name: str, *, version, model_id: str, enabled: bool = True):
        return resume_ppv1_run(
            config=resolve_config(), runs_root=tmp_path / name,
            run_id=name, model=ScriptedRealModelAdapter(model_id=model_id),
            evidence_card_enabled=enabled,
            evidence_card_version=version)

    model_id_a = "p2-v1card-resume-a"
    _model, _out = _start(tmp_path, "resume-a", version="v1card",
                          enabled=True, model_id=model_id_a)
    for version in (None, "v1", "v2"):
        with pytest.raises(PPV1RunError) as excinfo:
            _resume("resume-a", version=version, model_id=model_id_a)
        assert excinfo.value.detail.get("kind") == \
            "evidence_card_version_mismatch", version
        assert excinfo.value.detail.get("saved") == "v1card"
        assert excinfo.value.detail.get("current") == (
            None if version in (None, "v1") else version)
    # 同版本 ⇒ 正常续跑（已完成 run 幂等）
    out = _resume("resume-a", version="v1card", model_id=model_id_a)
    assert out["evidence_card_version"] == "v1card"
    assert out["resumed"] is True

    # 反向：v2 run 不接受 v1card resume
    model_id_b = "p2-v1card-resume-b"
    _model, _out = _start(tmp_path, "resume-b", version="v2", enabled=True,
                          model_id=model_id_b)
    with pytest.raises(PPV1RunError) as excinfo:
        _resume("resume-b", version="v1card", model_id=model_id_b)
    assert excinfo.value.detail.get("kind") == \
        "evidence_card_version_mismatch"
    assert excinfo.value.detail.get("saved") == "v2"
    assert excinfo.value.detail.get("current") == "v1card"

    # 保存身份中的坏版本值 ⇒ corrupt（fail-closed，不猜）
    model_id_c = "p2-v1card-resume-c"
    _model, _out = _start(tmp_path, "resume-c", version="v1card",
                          enabled=True, model_id=model_id_c)
    identity_path = tmp_path / "resume-c" / "resume-c" / "run_identity.json"
    identity = json.loads(identity_path.read_text())
    identity["strategy"]["evidence_card_version"] = "v1cardX"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    with pytest.raises(PPV1RunError) as excinfo:
        _resume("resume-c", version="v1card", model_id=model_id_c)
    assert excinfo.value.detail.get("kind") == \
        "evidence_card_version_corrupt"
    assert excinfo.value.detail.get("saved") == "v1cardX"


# ---------------------------------------------------------------- 确定性


def test_v1card_double_run_byte_identical(tmp_path) -> None:
    """§3.3.6：双跑（不同 runs root、同 run_id/输入）逐字节一致。"""
    model_1, _out_1 = _start(
        tmp_path, "double-1", version="v1card", enabled=True,
        run_id="double-arm", model_id="p2-double-model")
    model_2, _out_2 = _start(
        tmp_path, "double-2", version="v1card", enabled=True,
        run_id="double-arm", model_id="p2-double-model")
    assert model_1.seen_system_prompts == model_2.seen_system_prompts
    assert model_1.seen_user_payloads == model_2.seen_user_payloads
    payload = json.loads(model_1.seen_user_payloads[0])
    entry = payload["pool_hypotheses"][0]["evidence"]
    substrate = payload["substrate_evidence"]
    assert _sha_json(entry) == _sha_json(
        json.loads(model_2.seen_user_payloads[0])["pool_hypotheses"][0][
            "evidence"])
    assert _sha_json(substrate) == _sha_json(
        json.loads(model_2.seen_user_payloads[0])["substrate_evidence"])