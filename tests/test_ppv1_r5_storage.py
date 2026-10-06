"""R5 存储与适配线回归(Codex R4 复审 R4-09/10/11 + R4-02 部分;v5)。

规则级合成夹具;临时 SQLite,无金标/封存材料。先红后绿:红验证在
基线工作树(e80f459)复跑本文件;v5 实现后全绿。

R4-09:writer 完整事实契约(全部来源核 raw 与 strict 身份;CN/立体/
同位素/保真/结构可知复推;CN-only 专用契约闭合)。
R4-10:事件出现清单(manifest)重放校验(不依赖 caller 重复提供
dict);已存 states 行/假设载荷内容复算。
R4-02(存储部分):put/submit/重放的同源 hypothesis ID 复算。
R4-11:旧导入来源关系核验(CN 相同也核)+ 记录间矛盾披露(保留
可信 raw)。
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
    build_chemical_state_from_cn_only,
)
from pathway_v43.pollutant.events import (  # noqa: E402
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from pathway_v43.pollutant.hypothesis import (  # noqa: E402
    Participant,
    build_hypothesis,
    recompute_hypothesis_id,
)
from pathway_v43.pollutant.legacy_reader import (  # noqa: E402
    import_legacy_event,
    read_legacy_events,
)
from pathway_v43.pollutant.store import (  # noqa: E402
    Ppv1LedgerCorrupt,
    Ppv1StateContractError,
    Ppv1SubmitContractError,
    PollutantPathwayStore,
)
from pathway_v43.storage.pathway_store import PathwayStore  # noqa: E402

ROOT = Path(tempfile.mkdtemp(prefix="r5_storage_"))


def state(smi, origin="source_product", refs=None):
    return build_chemical_state(smi, origin, refs)


def fixture(name):
    sub = state("CCO", "raw_input", [{"record": "sub-A"}])
    prod = state("CC=O", refs=[{"record": "prod-A"}])
    hyp = build_hypothesis(
        parent_path_id="p1", substrate_state_ref=sub.state_id,
        participants=[
            Participant(state_ref=sub.state_id, side="reactant",
                        role="primary_substrate", coefficient=None,
                        coefficient_status="unknown"),
            Participant(state_ref=prod.state_id, side="product",
                        role="principal_product", coefficient=None,
                        coefficient_status="unknown")],
        participant_list_status="partial", step_scope="net_reaction",
        origin_group_key=name)
    event = build_pathway_event(hyp, run_id=name, context_hash="ctx")
    args = {"report_projection": build_report_projection(
                hyp, max_reportable=1,
                ranked_state_refs=[prod.state_id]).to_dict(),
            "expansion_plan": build_expansion_plan(
                hyp, expanded=[prod.state_id], deferred=[],
                not_tracked=[]).to_dict(),
            "states": [sub.to_dict(), prod.to_dict()],
            "hypothesis_dict": hyp.to_dict()}
    return PollutantPathwayStore(ROOT / (name + ".sqlite")), sub, prod, \
        hyp, event, args


# ==================================================== R4-09 writer 契约


def _put_state_variant(kind):
    store = PollutantPathwayStore(ROOT / (kind + ".sqlite"))
    original = (state("[13CH3][C@H](O)CC") if kind in ("isotope_status",
                                                       "stereo_status")
                else state("CCO"))
    payload = original.to_dict()
    if kind == "cn_identity":
        payload["cn_identity"] = "CCN"
    elif kind == "isotope_status":
        payload["isotope_information_status"] = "not_applicable"
    elif kind == "stereo_status":
        payload["stereo_information_status"] = "not_applicable"
    elif kind == "fidelity_unknown_enum":
        payload["representation_fidelity"] = {
            "formal_charge": "confirmed_by_magic"}
    elif kind == "fidelity_missing_axes":
        payload["representation_fidelity"] = {}
    elif kind == "source_raw_mismatch":
        payload["structure_smiles_raw"] = "CCN"
    elif kind == "source_raw_unparseable":
        payload["structure_smiles_raw"] = "not-a-smiles"
    elif kind == "executed_raw_mismatch":
        payload["structure_origin"] = "executed_product"
        payload["structure_smiles_raw"] = "CCN"
    elif kind == "same_graph_alternate_raw":
        payload["structure_smiles_raw"] = "OCC"
    elif kind == "cn_only_forged_identity_and_facts":
        payload = build_chemical_state_from_cn_only("CCN").to_dict()
        payload["state_id"] = original.state_id
        payload["formal_charge"] = 99
        payload["original_structure_available"] = True
        payload["representation_fidelity"] = dict(
            original.representation_fidelity)
        payload["stereo_information_status"] = "not_applicable"
        payload["isotope_information_status"] = "not_applicable"
    try:
        store.put_state(payload)
        result = "accepted"
    except Ppv1StateContractError as exc:
        result = exc.detail.get("kind")
    store.close()
    return result


@pytest.mark.parametrize("kind,expected", [
    ("cn_identity", "state_fact_rederivation_mismatch"),
    ("isotope_status", "state_fact_rederivation_mismatch"),
    ("stereo_status", "state_fact_rederivation_mismatch"),
    ("fidelity_unknown_enum", "state_fidelity_contract_violated"),
    ("fidelity_missing_axes", "state_fidelity_contract_violated"),
    ("source_raw_mismatch", "raw_identity_mismatch"),
    ("source_raw_unparseable", "raw_structure_unparseable"),
    ("executed_raw_mismatch", "raw_identity_mismatch"),
    ("same_graph_alternate_raw", "accepted"),  # 同图异拼写控制保留
    ("cn_only_forged_identity_and_facts",
     "cn_only_contract_violated"),
])
def test_r4_09_put_state_fact_contract(kind, expected) -> None:
    """R4-09:公共 writer 对完整 state 复推事实(CN/立体/同位素/保真/
    结构可知/raw 身份);CN-only 专用契约;同图异拼写仍接受。"""
    assert _put_state_variant(kind) == expected


def test_r4_09_submit_event_raw_mismatch_rejected() -> None:
    """R4-09 复审反例:合法事件的产物 raw 换 CCN(跨分子)⇒ submit
    结构化拒绝零写入(v4 created=True 存下 CCN)。"""
    store, sub, prod, hyp, event, args = fixture("submit_raw_mm")
    args["states"][1]["structure_smiles_raw"] = "CCN"
    with pytest.raises(Ppv1StateContractError) as ei:
        store.submit_event(event, **args)
    assert ei.value.detail["kind"] == "raw_identity_mismatch"
    assert store.counts()["events"] == 0  # 零写入
    store.close()


# ==================================================== R4-02 入口身份复算


def test_r4_02_put_hypothesis_changed_premise_old_id_rejected() -> None:
    """R4-02 复审反例:改 assumptions 但保留旧 hypothesis_id ⇒ put
    结构化拒绝(v4 首次 put 成功)。"""
    store, sub, prod, hyp, event, args = fixture("put_hyp_old_id")
    mutated = json.loads(json.dumps(args["hypothesis_dict"]))
    mutated["assumptions"] = ["a new scientific premise"]
    assert recompute_hypothesis_id(mutated) != hyp.hypothesis_id
    with pytest.raises(Ppv1SubmitContractError) as ei:
        store.put_hypothesis(mutated)
    assert ei.value.detail["kind"] == "hypothesis_id_rederivation_mismatch"
    store.close()


def test_r4_02_submit_changed_premise_old_id_rejected() -> None:
    """R4-02:随事务提交"新增前提 + 旧 ID"⇒ submit 结构化拒绝。"""
    store, sub, prod, hyp, event, args = fixture("submit_hyp_old_id")
    mutated = json.loads(json.dumps(args["hypothesis_dict"]))
    mutated["assumptions"] = ["a new scientific premise"]
    args["hypothesis_dict"] = mutated
    with pytest.raises(Ppv1SubmitContractError) as ei:
        store.submit_event(event, **args)
    assert ei.value.detail["kind"] == "hypothesis_id_rederivation_mismatch"
    store.close()


def test_r4_02_replay_tampered_stored_hypothesis_corrupt() -> None:
    """R4-02 复审反例:改已存假设的 assumptions、重放不提供假设 dict
    ⇒ 内容身份复算发现损坏(v4 created=False 静默成功)。"""
    store, sub, prod, hyp, event, args = fixture("replay_hyp_tamper")
    store.submit_event(event, **args)
    mutated = json.loads(json.dumps(args["hypothesis_dict"]))
    mutated["assumptions"] = ["tampered premise"]
    store.conn.execute(
        "UPDATE hypotheses SET payload=? WHERE hypothesis_id=?",
        (json.dumps(mutated), hyp.hypothesis_id))
    store.conn.commit()
    args["hypothesis_dict"] = None
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **args)
    assert ei.value.detail["kind"] == "hypothesis_payload_id_corrupt"
    store.close()


# ==================================================== R4-10 出现清单/重放


def test_r4_10_replay_missing_event_appearance_corrupt() -> None:
    """R4-10 复审反例:删本事件 prod-A 出现、另 put 同物种无关
    prod-B,states=[]/hypothesis_dict=None 重放 ⇒ 损坏(v4
    created=False;"有一条同物种出现"不能代替本事件集合)。"""
    store, sub, prod, hyp, event, args = fixture("replay_missing_app")
    store.submit_event(event, **args)
    # 本事件出现集合持久在事件载荷(manifest)
    payload = json.loads(store.conn.execute(
        "SELECT payload FROM events WHERE event_id=?",
        (event.event_id,)).fetchone()["payload"])
    manifest = payload["event_appearance_manifest"]
    assert {e["state_id"] for e in manifest} >= {
        sub.state_id, prod.state_id}
    alternate = state("O=CC", refs=[{"record": "unrelated-prod-B"}])
    store.put_state(alternate.to_dict())
    row = store.conn.execute(
        "SELECT appearance_hash FROM state_appearances WHERE state_id=?"
        " ORDER BY rowid LIMIT 1", (prod.state_id,)).fetchone()
    store.conn.execute(
        "DELETE FROM state_appearances WHERE state_id=? AND"
        " appearance_hash=?", (prod.state_id, row["appearance_hash"]))
    store.conn.commit()
    args["states"] = []
    args["hypothesis_dict"] = None
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **args)
    assert ei.value.detail["kind"] == \
        "event_appearance_manifest_entry_missing"
    store.close()


@pytest.mark.parametrize("kind,expected_kind", [
    ("cn", "state_row_corrupt"),
    ("inner_state_id", "state_inner_id_corrupt"),
    ("blank_structure", "state_row_blank_structure_corrupt"),
])
def test_r4_10_replay_stored_state_tampering_corrupt(kind, expected_kind):
    """R4-10 复审反例:已存 state 行改 CN/内 ID/清空结构+电荷 99 ⇒
    重放损坏(v4 均成功;空结构不自动当 CN-only)。"""
    store, sub, prod, hyp, event, args = fixture("replay_state_" + kind)
    store.submit_event(event, **args)
    payload = json.loads(store.conn.execute(
        "SELECT payload FROM states WHERE state_id=?",
        (prod.state_id,)).fetchone()["payload"])
    if kind == "cn":
        payload["cn_identity"] = "CCN"
    elif kind == "inner_state_id":
        payload["state_id"] = "cs_different"
    elif kind == "blank_structure":
        payload["smiles_isomeric"] = ""
        payload["formal_charge"] = 99
    store.conn.execute(
        "UPDATE states SET payload=? WHERE state_id=?",
        (json.dumps(payload), prod.state_id))
    store.conn.commit()
    args["states"] = []
    args["hypothesis_dict"] = None
    with pytest.raises(Ppv1LedgerCorrupt) as ei:
        store.submit_event(event, **args)
    assert ei.value.detail["kind"] == expected_kind
    store.close()


def test_r4_10_replay_without_dicts_idempotent_control() -> None:
    """控制:完整且一致的重放(不重复提供 dict)⇒ created=False 幂等
    (无重复事件/不误报损坏)。"""
    store, sub, prod, hyp, event, args = fixture("replay_normal_ctl")
    store.submit_event(event, **args)
    counts_before = store.counts()
    args["states"] = []
    args["hypothesis_dict"] = None
    result = store.submit_event(event, **args)
    assert result["created"] is False
    assert store.counts() == counts_before
    store.close()


# ==================================================== R4-11 旧导入


def make_legacy(name, steps):
    rd = ROOT / name
    rd.mkdir(exist_ok=True)
    store = PathwayStore(rd / "pathway.sqlite")
    root_cn = state("CCO").cn_identity
    root_pid = store.ensure_run(name, "CCO", root_cn)
    (rd / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1",
        "inputs": {"root_smiles": "CCO", "root_identity": root_cn}}))
    pid, cn = root_pid, root_cn
    created = []
    for i, smis in enumerate(steps):
        products = [{"position": j, "product_smiles": smi,
                     "product_smiles_full": smi,
                     "product_identity": state(smi).cn_identity}
                    for j, smi in enumerate(smis)]
        evidence = {"evidence_id": name + "-e" + str(i),
                    "source_id": name + "-e" + str(i),
                    "kind": "recorded_reaction",
                    "condition_fit": "unknown", "products": products}
        result = store.submit_event(
            run_id=name, parent_path_id=pid, substrate_identity=cn,
            evidence=evidence, products=products,
            expandable_path_ids=[], deferred_path_ids=[])
        created.append(result)
        pid = result["path_ids"][0]
        cn = products[0]["product_identity"]
    store.close()
    return rd, root_pid, created


def test_r4_11_same_cn_wrong_relation_degraded() -> None:
    """R4-11 复审反例:多步同 CN 异手性;子路径来源指针改指向其自身
    消耗事件(父路径关系原样)⇒ 关系核验失败 ⇒ CN-only + 原因
    (v4 接受错误手性产物为 source_product 无 uncertainty;旧库字节
    不变)。"""
    left, right = "C[C@H](O)CC", "C[C@@H](O)CC"
    rd, root_pid, created = make_legacy(
        "legacy_r5_relation", [[left], [right], ["CC=O"]])
    events = read_legacy_events(rd)
    second = next(e for e in events
                  if e["parent_path_id"] == created[0]["path_ids"][0])
    conn = sqlite3.connect(rd / "pathway.sqlite")
    conn.execute("UPDATE path_instances SET event_id=? WHERE path_id=?",
                 (second["event_id"], second["parent_path_id"]))
    conn.commit()
    conn.close()
    before = (rd / "pathway.sqlite").read_bytes()
    imported = import_legacy_event(rd, second, new_run_id="r5-wrong-rel")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    # 关系断裂 ⇒ CN-only(错误手性产物不再冒充底物结构)
    assert any("substrate_source_event_relation_mismatch" in note
               for note in imported["uncertainty_notes"])
    assert sub["structure_origin"] == "legacy_cn_only"
    assert (rd / "pathway.sqlite").read_bytes() == before  # 旧库只读


def test_r4_11_event_vs_path_substrate_mismatch_disclosed() -> None:
    """R4-11 辅助反例:事件声明的底物 CN(CC N)与路径/存档 raw
    (CCO)矛盾 ⇒ 披露记录间矛盾、保留可信 raw(不为服从错误 CN 丢
    可信 raw;v4 无披露)。"""
    rd, root_pid, created = make_legacy("legacy_r5_ev_vs_path", [["CC=O"]])
    conn = sqlite3.connect(rd / "pathway.sqlite")
    conn.execute("UPDATE reaction_events SET substrate_identity=? WHERE"
                 " event_id=?", ("CCN", created[0]["event_id"]))
    conn.commit()
    conn.close()
    ev = read_legacy_events(rd)[0]
    imported = import_legacy_event(rd, ev, new_run_id="r5-ev-vs-path")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    assert any("substrate_declaration_mismatch_event_vs_path" in note
               for note in imported["uncertainty_notes"])
    assert sub["structure_smiles_raw"] == "CCO"  # 可信 raw 保留


def test_r4_11_product_declared_vs_raw_mismatch_disclosed() -> None:
    """R4-11 辅助反例:产物行声明 CN(CCN)与 raw(CC=O)矛盾 ⇒ 披露
    记录间矛盾、保留 raw(v4 无披露)。"""
    rd, root_pid, created = make_legacy("legacy_r5_prod_raw", [["CC=O"]])
    conn = sqlite3.connect(rd / "pathway.sqlite")
    conn.execute("UPDATE event_products SET product_identity=? WHERE"
                 " event_id=?", ("CCN", created[0]["event_id"]))
    conn.commit()
    conn.close()
    ev = read_legacy_events(rd)[0]
    imported = import_legacy_event(rd, ev, new_run_id="r5-prod-vs-raw")
    assert any("product_identity_vs_raw_mismatch" in note
               for note in imported["uncertainty_notes"])
    prod = next(s for s in imported["states"]
                if any(ref.get("role") == "legacy_event_product"
                       for ref in s["source_refs"]))
    assert prod["structure_smiles_raw"] == "CC=O"  # 可信 raw 保留


def test_r4_11_legal_multistep_import_control() -> None:
    """控制:合法多步导入(共享中间物)不受关系核验误伤;产物结构
    正常为 source_product。"""
    rd, root_pid, created = make_legacy("legacy_r5_legal",
                                        [["C[C@H](O)CC"], ["CC=O"]])
    events = read_legacy_events(rd)
    second = next(e for e in events
                  if e["parent_path_id"] == created[0]["path_ids"][0])
    imported = import_legacy_event(rd, second, new_run_id="r5-legal")
    sub = next(s for s in imported["states"]
               if s["state_id"] == imported["hypothesis"].substrate_state_ref)
    assert sub["structure_origin"] == "source_product"
    assert sub["structure_smiles_raw"] == "C[C@H](O)CC"
    assert not any("relation_mismatch" in note
                   for note in imported["uncertainty_notes"])
