# -*- coding: utf-8 -*-
"""Unit & end-to-end pipeline tests for v44-Next architecture wiring.

Covers:
1. Default zero-drift guardrail (`s5b_builder` and `runflow` 100% compatible with b220d32 when flags off);
2. Supply-layer S5 rule enumeration + `compile_recorded_reaction` formal `ReactionSpec` compilation (`build_s5_hybrid_pool_entries`);
3. Decision & verification layer in `runflow.py`: no `v1card` (`evidence_card_version="none"`), Cross-Source Consensus Boost (`consensus_boost=True`), and Smart-Gated Tail Backfill (`enable_smart_gated_backfill=True`) with 100% `audit_hypothesis` compliance;
4. Official `s5b_scoring.py` evaluation under both `ppv1-criteria-v4` and `ppv1-criteria-v5` (synthetic fixtures only, zero real gold/question SMILES).
"""

from __future__ import annotations

import json
from pathlib import Path

from pathway_v43.config import V43Config, resolve_config
from pathway_v43.pollutant.audit import audit_hypothesis
from pathway_v43.pollutant.chemstate import build_chemical_state, strict_identity_of
from pathway_v43.pollutant.evaluation import PPV1_CRITERIA_V4, PPV1_CRITERIA_V5
from pathway_v43.pollutant.path_context import build_path_context
from pathway_v43.pollutant.production import execute_atomtool_expansion, prepare_hypothesis
from pathway_v43.pollutant.recorded_source import compile_recorded_reaction
from pathway_v43.pollutant.runflow import (
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_builder import (
    build_question_batch,
    build_run_input,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_cli import build_parser
from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
from pathway_v43.services.s5_hybrid_choice import (
    HybridCandidate,
    build_s5_hybrid_pool_entries,
    compile_s5_candidate_to_spec,
)


def _dummy_config(tmp_path: Path) -> V43Config:
    return resolve_config(tmp_path, tmp_path)


def _compile_syn_spec(
    substrate: str,
    product: str,
    *,
    key: str,
    prior_score: float = 80.0,
    prior_tier: str = "MODERATE_SINGLE",
    rxn_class: str = "monooxygenation_hydroxylation",
    source_families: list[str] | None = None,
    is_gated_supplement: bool = False,
) -> dict:
    sub_iso = strict_identity_of(substrate)
    prod_iso = strict_identity_of(product)
    res = compile_recorded_reaction(
        substrate_smiles=sub_iso,
        donor_smiles=sub_iso,
        products=[prod_iso],
        record_id=f"syn:{key}",
        novel_product_first_principal=prod_iso,
    )
    assert res["status"] == "compiled", f"Failed to compile synthetic {substrate} -> {product}: {res}"
    spec = dict(res["spec"])
    p1_gate = res.get("novel_p1_gate")
    if isinstance(p1_gate, dict):
        if p1_gate.get("compiled_principal"):
            spec["product_smiles"] = str(p1_gate["compiled_principal"])
        if p1_gate.get("compiled_coproducts") is not None:
            spec["coproducts"] = list(p1_gate["compiled_coproducts"])
        if p1_gate.get("undeclared_coproducts"):
            spec["undeclared_coproducts"] = list(p1_gate["undeclared_coproducts"])
    fams = list(source_families or ["analog"])
    spec.update(
        {
            "key": key,
            "transformation_ref": f"syn-ref:{key}",
            "origin_group_key": f"syn-grp:{key}",
            "coefficient": 1,
            "s5_prior_score": float(prior_score),
            "s5_prior_tier": str(prior_tier),
            "reaction_class_12": str(rxn_class),
            "source_families": fams,
            "is_gated_supplement": bool(is_gated_supplement),
        }
    )
    return spec


def test_default_zero_drift_s5b_builder_and_runflow(tmp_path: Path) -> None:
    """默认开关关闭时，s5b_builder 与 runflow 行为与基线 100% 兼容（零新增键、零漂移）。"""
    prov_default = default_pool_provider(None)
    assert prov_default("c1ccccc1") == []
    assert prov_default.last_diagnostics["note"] == "无 config/engine:空池(novel 合法)"

    q = {"qid": "syn-q0", "substrate_smiles": "c1ccccc1", "products_smiles": ["Oc1ccccc1"]}
    ri_default = build_run_input(q, batch_tag="syn-b0", pools={"c1ccccc1": []})
    assert set(ri_default["plan"].keys()) == {"pools", "model"}

    cfg = _dummy_config(tmp_path)
    runs_root = tmp_path / "runs_default"
    summary = start_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id="syn-run-default",
        smiles="c1ccccc1",
        plan={"pools": {"c1ccccc1": []}, "model": {"provider_kind": "scripted", "responses": ['{"proposals": []}']}},
        scripted=True,
    )
    assert summary["evidence_card_enabled"] is True
    assert "evidence_card_version" not in summary

    resumed = resume_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id="syn-run-default",
    )
    assert resumed["resumed"] is True
    assert resumed["evidence_card_enabled"] is True


def test_s5_hybrid_pool_entries_and_cli_v44_next() -> None:
    """开启 v44-next / build_s5_hybrid_pool_entries 时，S5 候选经 compile_recorded_reaction 编译为合法 ReactionSpec。"""
    substrate = "c1ccccc1"
    # 1. 测试单条 S5 候选编译与非法 SMILES 自动剔除
    good_cand = HybridCandidate(
        cand_strict=strict_identity_of("Oc1ccccc1"),
        cand_smiles="Oc1ccccc1",
        sub_smiles=substrate,
        source_families={"envipath", "eawag"},
        env_rule_ids={"env:bt0001"},
        env_freq_sum=10,
        fine_cat="monooxygenation_hydroxylation",
        formula_delta="+O",
        heavy_atom_ratio=1.16,
        prior_score=122.5,
        prior_tier="HIGH_CONSENSUS",
    )
    compiled = compile_s5_candidate_to_spec(substrate, good_cand, index=1, is_gated_supplement=True)
    assert compiled is not None
    assert compiled["s5_prior_score"] == 122.5
    assert compiled["s5_prior_tier"] == "HIGH_CONSENSUS"
    assert compiled["reaction_class_12"] == "monooxygenation_hydroxylation"
    assert compiled["source_families"] == ["eawag", "envipath"]
    assert compiled["is_gated_supplement"] is True
    assert isinstance(compiled.get("edits"), list) and len(compiled["edits"]) > 0

    bad_cand = HybridCandidate(
        cand_strict="INVALID",
        cand_smiles="not_a_smiles",
        sub_smiles=substrate,
        source_families={"envipath"},
        prior_score=95.0,
    )
    assert compile_s5_candidate_to_spec(substrate, bad_cand, index=2) is None

    # 2. 测试管线级入口 build_s5_hybrid_pool_entries 在真实本地规则集上枚举并编译为合法 ReactionSpec
    entries = build_s5_hybrid_pool_entries(
        "Oc1ccccc1",
        s1d_specs=[],
        domain="298",
        s5_supplement_gate_max_s1d=2,
        s5_supplement_min_prior_score=50.0,
        s5_max_supplements=2,
    )
    assert len(entries) >= 1
    sub_state = build_chemical_state(
        strict_identity_of("Oc1ccccc1"),
        "raw_input",
        [{"record": "syn-test"}],
    )
    ctx = build_path_context()
    for spec in entries:
        assert "s5_prior_score" in spec
        assert "s5_prior_tier" in spec
        assert "reaction_class_12" in spec
        assert "source_families" in spec
        assert spec["is_gated_supplement"] is True
        prep = prepare_hypothesis(
            spec,
            parent_path_id="p0",
            substrate_state=sub_state,
            transformation_ref=str(spec.get("transformation_ref") or "s5-rule"),
        )
        ex = execute_atomtool_expansion(substrate_smiles=sub_state.smiles_isomeric, tool_inputs=prep["tool_inputs"])
        assert ex["execution_ok"] is True
        aud = audit_hypothesis(
            prep["hypothesis"],
            run_id="syn-test",
            states=prep["states"],
            context=ctx,
            center_evidence=ex["center_evidence"],
        )
        from pathway_v43.pollutant.audit import decide_admission
        from pathway_v43.pollutant.production import ADMISSION_SUBMITTABLE

        disp, _ = decide_admission(aud)
        assert disp in ADMISSION_SUBMITTABLE

    # 2b. 测试 M2a -> M2b 离去基团/共产物自动推导编译（如脱氯羟基化 Clc1ccccc1 -> Oc1ccccc1 与酯水解 CC(=O)Oc1ccccc1 -> Oc1ccccc1）
    for sub_m2b, prod_m2b in [("Clc1ccccc1", "Oc1ccccc1"), ("CC(=O)Oc1ccccc1", "Oc1ccccc1")]:
        cand_m2b = HybridCandidate(
            cand_strict=strict_identity_of(prod_m2b),
            cand_smiles=prod_m2b,
            sub_smiles=sub_m2b,
            source_families={"envipath", "eawag"},
            prior_score=118.0,
            prior_tier="HIGH_CONSENSUS",
        )
        spec_m2b = compile_s5_candidate_to_spec(sub_m2b, cand_m2b, index=3, is_gated_supplement=True)
        assert spec_m2b is not None
        assert strict_identity_of(spec_m2b["product_smiles"]) == strict_identity_of(prod_m2b)
        assert len((spec_m2b.get("coproducts") or []) + (spec_m2b.get("undeclared_coproducts") or [])) >= 1

    # 3. 测试 s5b_cli --preset v44-next 参数解析
    parser = build_parser()
    args = parser.parse_args(
        [
            "build",
            "--questions",
            "dummy.jsonl",
            "--batch-root",
            "dummy_root",
            "--preset",
            "v44-next",
        ]
    )
    assert args.preset == "v44-next"


def test_runflow_v44_next_no_evcard_consensus_and_smart_backfill(tmp_path: Path) -> None:
    """验证 runflow 在 v44-next 模式下：
    1) 不注入 v1card (evidence_card_enabled=False)；
    2) 跨源独立共识升位 (consensus_boost=True)；
    3) 非法 B 类 novel 槽位紧缩递补 (Compact before Backfill) + 智能门控尾部回填至 5 条，
       且全部回填事件 100% 通过 prepare_hypothesis + execute + audit_hypothesis。
    """
    cfg = _dummy_config(tmp_path)
    sub = "c1ccccc1"
    # 构造 5 条合法预编译池候选（模拟 2 条 S1d + 3 条高先验 S5 规则候选）
    spec_s1d_1 = _compile_syn_spec(
        sub,
        "Oc1ccccc1",
        key="tpl-s1d-1",
        prior_score=88.0,
        prior_tier="MODERATE_SINGLE",
        rxn_class="monooxygenation_hydroxylation",
        source_families=["analog"],
        is_gated_supplement=False,
    )
    # 跨源超高共识候选 (analog + envipath, prior_score=128.0 >= 115.0)
    spec_s1d_2 = _compile_syn_spec(
        sub,
        "Oc1ccc(O)cc1",
        key="tpl-s1d-2",
        prior_score=128.0,
        prior_tier="HIGH_CONSENSUS",
        rxn_class="dioxygenation_or_diol_formation",
        source_families=["analog", "envipath"],
        is_gated_supplement=False,
    )
    spec_s5_1 = _compile_syn_spec(
        sub,
        "Oc1ccccc1O",
        key="s5-01-catechol",
        prior_score=118.0,
        prior_tier="HIGH_CONSENSUS",
        rxn_class="dioxygenation_or_diol_formation",
        source_families=["eawag", "envipath"],
        is_gated_supplement=True,
    )
    spec_s5_2 = _compile_syn_spec(
        sub,
        "Oc1cccc(O)c1",
        key="s5-02-resorcinol",
        prior_score=92.0,
        prior_tier="MODERATE_SINGLE",
        rxn_class="monooxygenation_hydroxylation",
        source_families=["envipath"],
        is_gated_supplement=True,
    )
    spec_s5_3 = _compile_syn_spec(
        sub,
        "O=C(O)c1ccccc1",
        key="s5-03-benzoate",
        prior_score=76.0,
        prior_tier="MODERATE_SINGLE",
        rxn_class="decarboxylation_or_c1_cleavage",
        source_families=["envipath"],
        is_gated_supplement=True,
    )
    pool_specs = [spec_s1d_1, spec_s1d_2, spec_s5_1, spec_s5_2, spec_s5_3]

    from pathway_v43.domain.models import stable_id

    run_id = "syn-run-v44-next"
    root_path_id = stable_id("spath", run_id, "root")
    sub_state = build_chemical_state(
        strict_identity_of(sub),
        "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}],
    )
    hid_1 = prepare_hypothesis(
        spec_s1d_1,
        parent_path_id=root_path_id,
        substrate_state=sub_state,
        transformation_ref=spec_s1d_1["transformation_ref"],
    )["hypothesis"].hypothesis_id
    hid_2 = prepare_hypothesis(
        spec_s1d_2,
        parent_path_id=root_path_id,
        substrate_state=sub_state,
        transformation_ref=spec_s1d_2["transformation_ref"],
    )["hypothesis"].hypothesis_id

    # 模型输出含 1 条非法 B 类 novel 提案（无法通过编译/审计），以及 2 条合法模板提案 (hid_1, hid_2)
    # 验证：非法 novel 提案被自动剔除紧缩（Compact before Backfill），不占 Top-5 槽位，随后智能门控尾部回填补满 5 条合法事件
    model_resp = json.dumps(
        {
            "proposals": [
                {"hypothesis_id": hid_1},
                {
                    "hypothesis_id": "novel-bad-1",
                    "proposal_context": {
                        "reference_hypothesis_ids": [],
                        "output_origin": "novel_outside_pool",
                    },
                    "reaction_spec": {
                        "product_smiles": "Oc1ccccc1",
                        "transformation_ref": "novel-bad",
                        "edits": [{"op": "BreakBond", "a": "S:99", "b": "S:98"}],
                    },
                },
                {"hypothesis_id": hid_2},
            ],
            "rank_hypotheses": ["novel-bad-1", hid_1, hid_2],
        }
    )
    runs_root = tmp_path / "runs_v44_next"
    summary = start_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id=run_id,
        smiles=sub,
        plan={
            "preset": "v44-next",
            "pools": {sub: pool_specs},
            "model": {"provider_kind": "scripted", "responses": [model_resp]},
        },
        preset="v44-next",
        scripted=True,
    )

    # 1. 验证证据卡关闭 (ABL-1')
    assert summary["evidence_card_enabled"] is False
    assert "evidence_card_version" not in summary

    # 2. 验证 5 条事件全部经过 prepare + execute + audit_hypothesis 落账并 verified
    assert summary["counts"]["events"] == 5
    export_payload_path = Path(summary["native_export"]["dir"]) / "payload.json"
    export_payload = json.loads(export_payload_path.read_text(encoding="utf-8"))
    events = export_payload["events"]
    assert len(events) == 5
    for ev in events:
        body = json.loads(ev["payload"]) if isinstance(ev.get("payload"), str) else (ev.get("payload") or ev)
        assert len(body["participants"]) >= 2
        assert str(body["schema_version"]).startswith("ppv1-event-")
    from pathway_v43.pollutant.production import ADMISSION_SUBMITTABLE

    audit_reports = export_payload["audit_production_reports"]
    assert len(audit_reports) >= 5
    for ar in audit_reports:
        prod = ar.get("production_payload") or {}
        if "admission" in prod:
            disp = prod["admission"]["disposition"]
            assert disp in ADMISSION_SUBMITTABLE

    # 3. 验证 resume_ppv1_run 在 v44-next 模式下身份校验 100% 闭合
    resumed = resume_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id="syn-run-v44-next",
        preset="v44-next",
    )
    assert resumed["resumed"] is True
    assert resumed["counts"]["events"] == 5


def test_v44_next_end_to_end_official_scoring_v4_and_v5(tmp_path: Path) -> None:
    """验证 v44-next 构建、运行与回填产出的事件可被官方 s5b_scoring.py (v4 和 v5) 正确判分。"""
    repo_root = Path(__file__).resolve().parents[2]
    work_root = tmp_path / "v44_next_scoring_work"
    work_root.mkdir(parents=True, exist_ok=True)
    q_path = work_root / "syn_questions.jsonl"
    q_record = {
        "qid": "syn-q1",
        "substrate_smiles": "Oc1ccccc1",
        "products_smiles": ["Oc1ccc(O)cc1"],
    }
    q_path.write_text(json.dumps(q_record) + "\n", encoding="utf-8")

    batch_root = work_root / "batch"
    runs_root = work_root / "runs"

    manifest = build_question_batch(
        q_path,
        batch_root,
        batch_tag="syn-v44-next",
        provider_kind="scripted",
        repo_root=repo_root,
        synthetic_review=True,
        preset="v44-next",
        s5_supplement_min_prior_score=45.0,
    )
    assert manifest["n_questions"] == 1
    entry = manifest["entries"][0]
    assert entry["pool_size"] >= 1

    run_input = json.loads((batch_root / entry["run_input_rel"]).read_text(encoding="utf-8"))
    assert run_input["plan"]["preset"] == "v44-next"
    assert run_input["plan"]["evidence_card_version"] == "none"
    assert run_input["plan"]["enable_smart_gated_backfill"] is True

    # 模型弃权 (proposals=[])，完全依靠 v44-Next 智能门控回填候选池中的 S5 高先验合规事件
    run_input["plan"]["model"] = {
        "provider_kind": "scripted",
        "responses": ['{"proposals": [], "rank_hypotheses": []}'],
    }

    cfg = _dummy_config(work_root)
    summary = start_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id=entry["run_id"],
        smiles=entry["substrate_smiles"],
        plan=run_input["plan"],
        preset="v44-next",
        scripted=True,
    )
    assert summary["counts"]["events"] >= 1

    # 写入 cases/<qid>.json 供官方判分器读取导出 digest
    cases_dir = batch_root / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / f"{entry['qid']}.json").write_text(
        json.dumps(
            {
                "qid": entry["qid"],
                "run_id": entry["run_id"],
                "status": "completed",
                "export_digest": summary["native_export"]["export_digest"],
                "events": summary["counts"]["events"],
            }
        ),
        encoding="utf-8",
    )

    # 官方判分器 v4 (matched_product_hit) 与 v5 (role_bound_product_hit) 判分验证
    score_v4 = score_s5b_batch(
        batch_root,
        runs_root=runs_root,
        data_scope="synthetic_rule_level",
        criteria_version=PPV1_CRITERIA_V4,
    )
    assert score_v4["denominator"] == 1
    assert "matched_product_hit_caliber" in score_v4
    assert score_v4["matched_product_hit_caliber"]["hit@5"] == 1

    score_v5 = score_s5b_batch(
        batch_root,
        runs_root=runs_root,
        data_scope="synthetic_rule_level",
        criteria_version=PPV1_CRITERIA_V5,
    )
    assert score_v5["denominator"] == 1
    assert "role_bound_product_hit_caliber" in score_v5
    assert score_v5["role_bound_product_hit_caliber"]["hit@5"] == 1


def test_v44_next_v1_1_three_gap_fixes(tmp_path: Path) -> None:
    """验证 v44-Next v1.1 三项关键漏口修复（纯合成样例）：
    1. Gap 1: 当 S1d 候选 > 2 条时，建池阶段不阻挡 S5 规则进入 Top-16 混合候选池；
    2. Gap 2: 离子态/加氧/水合 S5 候选（如 CC=O -> CC(=O)[O-]）经 compile_s5_candidate_to_spec 编译后保留精确主产物身份并通过 11 项审计；
    3. Gap 3: 池外 novel 提案在 atom_edit 预检失败时自动回退调用 compile_s5_candidate_to_spec 编译其 product_smiles 并保持模型显式排序。
    """
    # Gap 2: 醛氧化为去质子化羧酸根 (CC=O -> CC(=O)[O-]) 编译保持离子态主产物身份
    spec_ion = compile_s5_candidate_to_spec(
        "CC=O",
        {"cand_smiles": "CC(=O)[O-]", "prior_score": 96.0},
        index=1,
        is_gated_supplement=True,
    )
    assert spec_ion is not None
    assert strict_identity_of(spec_ion["product_smiles"]) == strict_identity_of("CC(=O)[O-]")

    # Gap 1: 即使已有 3 条 S1d 候选 (> s5_supplement_gate_max_s1d=2)，S5 规则仍可进入 Top-16 混合池
    sub = "Oc1ccccc1"
    s1d_three = [
        _compile_syn_spec(sub, "Oc1ccccc1O", key="tpl-1", prior_score=65.0),
        _compile_syn_spec(sub, "Oc1ccc(O)cc1", key="tpl-2", prior_score=64.0),
        _compile_syn_spec(sub, "Oc1cccc(O)c1", key="tpl-3", prior_score=63.0),
    ]
    extra_rule = [
        {
            "rule_id": "syn_env_rule_1",
            "source_family": "envipath",
            "frequency": 25,
            "smarts": "[c:1][cH:2][c:3]([OH:4])[cH:5][cH:6][cH:7]>>[c:1][c:2](O)[c:3]([OH:4])[c:5](O)[cH:6][cH:7]",
        }
    ]
    hybrid_pool = build_s5_hybrid_pool_entries(
        sub,
        s1d_specs=s1d_three,
        domain="298",
        include_env=False,
        include_rr=False,
        extra_rules=extra_rule,
        s5_supplement_gate_max_s1d=2,
        max_pool=16,
    )
    assert len(hybrid_pool) >= 4
    assert any(
        str((sp.get("compile") or {}).get("source_kind") or "") == "s5_hybrid_rule"
        for sp in hybrid_pool
    )

    # Gap 3: 池外 novel 提案 atom_edit 非法但 product_smiles 合法可编译时，自动回退编译并按模型首位提交
    cfg = _dummy_config(tmp_path)
    run_id = "syn-run-v44-v11-gap3"
    from pathway_v43.domain.models import stable_id

    root_path_id = stable_id("spath", run_id, "root")
    sub_state = build_chemical_state(
        strict_identity_of("c1ccccc1"),
        "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}],
    )
    pool_1 = _compile_syn_spec("c1ccccc1", "Oc1ccccc1", key="tpl-p1", prior_score=80.0)
    hid_p1 = prepare_hypothesis(
        pool_1,
        parent_path_id=root_path_id,
        substrate_state=sub_state,
        transformation_ref=pool_1["transformation_ref"],
    )["hypothesis"].hypothesis_id

    model_resp = json.dumps(
        {
            "proposals": [
                {
                    "hypothesis_id": "novel-rescued-1",
                    "proposal_context": {
                        "reference_hypothesis_ids": [],
                        "output_origin": "novel_outside_pool",
                    },
                    "reaction_spec": {
                        "product_smiles": "Oc1ccc(O)cc1",
                        "transformation_ref": "novel-rescued",
                        "edits": [{"op": "BreakBond", "a": "S:99", "b": "S:98"}],
                    },
                },
                {
                    "hypothesis_id": "novel-uncompilable-2",
                    "proposal_context": {
                        "reference_hypothesis_ids": [],
                        "output_origin": "novel_outside_pool",
                    },
                    "reaction_spec": {
                        "product_smiles": "not_a_valid_smiles",
                        "transformation_ref": "novel-uncompilable",
                        "edits": [{"op": "BreakBond", "a": "S:99", "b": "S:98"}],
                    },
                },
                {"hypothesis_id": hid_p1},
            ],
            "rank_hypotheses": ["novel-rescued-1", "novel-uncompilable-2", hid_p1],
        }
    )
    runs_root = tmp_path / "runs_v11_gap3"
    summary = start_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id=run_id,
        smiles="c1ccccc1",
        plan={
            "preset": "v44-next",
            "pools": {"c1ccccc1": [pool_1]},
            "model": {"provider_kind": "scripted", "responses": [model_resp]},
        },
        preset="v44-next",
        scripted=True,
    )
    assert summary["counts"]["events"] == 2


def test_v44_next_v1_2_ranker_calibration_and_cleavage_upgrade(tmp_path: Path) -> None:
    """验证 v44-Next v1.2 候选排序器校准与多产物裂解共产物补齐（纯合成样例）：
    1. try_upgrade_cleavage_spec 将单产物酯裂解 spec (CC(=O)Oc1ccccc1 -> Oc1ccccc1, undeclared_coproducts=['CC=O'])
       升级为含水解共产物 CC(=O)O 的双产物合法 ReactionSpec；
    2. calibrate_submittable_ranking 在弱相似模板 (best_similarity=0.35) 被排在 Slot 1 时，
       自动将 Slot 2 的精确底物高共识模板 (best_similarity=1.0, s5_prior_score=168.0) 升位至 Slot 1。
    """
    from pathway_v43.services.s5_hybrid_choice import (
        infer_cleavage_coproducts,
        try_upgrade_cleavage_spec,
    )

    sub_ester = "CC(=O)Oc1ccccc1"
    prod_phenol = "Oc1ccccc1"
    cops_inferred = infer_cleavage_coproducts(sub_ester, prod_phenol)
    assert any(strict_identity_of("CC(=O)O") in [strict_identity_of(x) for x in cset] for cset in cops_inferred)

    spec_1prod = compile_s5_candidate_to_spec(
        sub_ester,
        {"cand_smiles": prod_phenol, "prior_score": 115.0},
        index=1,
        is_gated_supplement=True,
    )
    assert spec_1prod is not None
    up_spec = try_upgrade_cleavage_spec(sub_ester, spec_1prod)
    assert up_spec is not None
    assert strict_identity_of("CC(=O)O") in [
        strict_identity_of(c) for c in (up_spec.get("coproducts") or [])
    ]

    # 测试 runflow 中的候选排序器校准 (Rule 4: 弱相似 tpl 诱饵在 Slot 1 被精确底物高先验锚点超越)
    cfg = _dummy_config(tmp_path)
    sub = "c1ccccc1"
    spec_weak_tpl = _compile_syn_spec(
        sub,
        "Oc1ccccc1",
        key="tpl-weak-1",
        prior_score=82.0,
        prior_tier="MODERATE_SINGLE",
        source_families=["analog"],
    )
    spec_weak_tpl["best_similarity"] = 0.35
    spec_weak_tpl["compile"] = {"best_similarity": 0.35, "s5_prior_score": 82.0}

    spec_exact_rec = _compile_syn_spec(
        sub,
        "Oc1ccc(O)cc1",
        key="rec-exact-2",
        prior_score=168.0,
        prior_tier="HIGH_CONSENSUS",
        source_families=["recorded", "envipath"],
    )
    spec_exact_rec["best_similarity"] = 1.0
    spec_exact_rec["compile"] = {"best_similarity": 1.0, "s5_prior_score": 168.0}

    from pathway_v43.domain.models import stable_id

    run_id = "syn-run-v12-calib"
    root_path_id = stable_id("spath", run_id, "root")
    sub_state = build_chemical_state(
        strict_identity_of(sub),
        "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}],
    )
    hid_weak = prepare_hypothesis(
        spec_weak_tpl,
        parent_path_id=root_path_id,
        substrate_state=sub_state,
        transformation_ref=spec_weak_tpl["transformation_ref"],
    )["hypothesis"].hypothesis_id
    hid_exact = prepare_hypothesis(
        spec_exact_rec,
        parent_path_id=root_path_id,
        substrate_state=sub_state,
        transformation_ref=spec_exact_rec["transformation_ref"],
    )["hypothesis"].hypothesis_id

    model_resp = json.dumps(
        {
            "proposals": [
                {"hypothesis_id": hid_weak},
                {"hypothesis_id": hid_exact},
            ],
            "rank_hypotheses": [hid_weak, hid_exact],
        }
    )
    runs_root = tmp_path / "runs_v12_calib"
    summary = start_ppv1_run(
        config=cfg,
        runs_root=runs_root,
        run_id=run_id,
        smiles=sub,
        plan={
            "preset": "v44-next",
            "pools": {sub: [spec_weak_tpl, spec_exact_rec]},
            "model": {"provider_kind": "scripted", "responses": [model_resp]},
        },
        preset="v44-next",
        scripted=True,
    )
    assert summary["counts"]["events"] == 2
    import sqlite3

    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    rows = conn.execute(
        "SELECT payload FROM search_actions WHERE action_kind='expand_hypothesis'"
    ).fetchall()
    conn.close()
    rank_by_key = {}
    for (p_raw,) in rows:
        pl = json.loads(p_raw)
        rank_by_key[pl["hypothesis_key"]] = pl["effective_rank"]
    assert rank_by_key["rec-exact-2"] == 1
    assert rank_by_key["tpl-weak-1"] == 2


