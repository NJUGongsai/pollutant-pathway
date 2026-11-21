#!/usr/bin/env python3
"""score_disclosure_v4cn.py — v1.3 T1-A/T2-H 双口径披露判分（严格 v4 / 电荷中和 v4-cn）。

题域标签：``--domain-tag`` 显式传入；本阶段只用两域调参集（B121 261 题 /
298 196 题），不触碰留出集。

两套数
------
1. **严格 v4**：读取官方批已判分的 ``metrics_v4.json``（冻结口径，不重判）；
2. **v4-cn 披露口径**：金标参考节点与提交事件状态都先做**受护栏约束的**
   电荷中和，再走同一 ``evaluate_scientific(criteria_version=ppv1-criteria-v4)``
   判分链。

护栏（T2-H，依据 mimo 2026-11-13 评审回复第 3.4 节；采信到与程序证据互证为止）
-----------------------------------------------------------------------
1. **中和不变量**：重原子图 / 键级 / 元素序列 / 同位素 / 立体（含手性标记与
   键立体）/ 自由基电子 / 组分数全不变，才允许判同一产物；否则回退原串并
   记机读原因（``invariant_broken``）。
2. **身份同源**：中和后的身份串由 ``chemstate._identity_key``（与 v4 参考侧
   ``strict_identity_of`` 同一套 CXSMILES 身份机器）生成，不用纯
   ``MolToSmiles`` 往返；并逐条自检 ``strict_identity_of(key) == key``
   （幂等），不通过则回退（``identity_roundtrip_failed``）。
3. **净电荷保护**：``0 → 非 0``、符号翻转或``|q|``变大 ⇒ 回退
   （``net_charge_changed``）。**口径说明**：只做后向收敛（带电→中性）不算
   变化，否则乙酸根 −1→0 也会被回退，v4-cn 口径将退化为空操作，与评审
   已同意的磷酸/磺酸/烯醇负离子子项自相矛盾；实现取"中和只能降低带电
   程度"的保守读法，并在 ``--self-check`` 的算子行为表里逐条钉死。
4. **盐 / 反离子单列**：多组分结构一律 ``salt_not_normalized``（不静默
   去盐、不静默计命中；这是防止 ``[Cl-] → HCl`` 类错误改写的硬闸）。
5. **排除清单**（主窗口保守默认）：碳酸体系（CO₂ / HCO₃⁻ / CO₃²⁻）、
   NH₃ / NH₄⁺、CN⁻ / HCN、SCN⁻、H⁺ / H₃O⁺ 不参与中和合并
   （``excluded_family``）；按题统计受影响数。
6. **逐侧留痕**：逐题记参考侧 / 预测侧各自 ``normalization_status``、
   是否真的改写、中和前后净电荷与组分数；每个翻转标注产物侧 / 底物侧。
7. **派生字段披露**：身份轴改写时重算 ``cn_identity`` 与 ``formal_charge``；
   ``state_id`` **保持原值**（不透明出现键），逐题记
   ``derived_fields_policy = identity_axis_only``（见报告 §T2-H）。
8. **自检扩展**：不中和路径复现官方 ``metrics_v4.json``（原有）；
   中和幂等、零静默回退、身份往返自检；``--emit-operator-table`` 产出
   固定夹具的机读算子行为表（只含夹具名与布尔/计数，不含 SMILES）。
9. **重算与分桶**：``--legacy-flips`` 可传入旧版（commit ``78654bf``）
   逐题结果，输出加固前后逐题差异并按原因分桶。

实现方式（不改冻结判分器）
--------------------------
- 参考图复制后替换节点 ``structure_smiles`` 为中和后的身份串，并重算
  ``reference_graph_sha256`` 供 manifest 声明；图 id / 边 / 角色不变；
- 导出 payload 经官方 ``read_native_export`` 读取后，在内存中替换 states 的
  ``smiles_isomeric`` / ``cn_identity`` / ``formal_charge``（身份轴），
  ``state_id`` 不变；
- v4 判定仍由 ``evaluation.py`` 的既有 v4 代码执行（身份函数不变，只是
  输入已中和）；新口径完全写在本脚本里。

输出（``--out-dir``，gitignored）
---------------------------------
- ``disclosure_v4cn_<domain>.json``：两套 Hit@1/@3/@5、跳变百分比、桶变化；
- ``flips_v4cn_<domain>.jsonl``：100% 逐题翻转明细（含 qid 与逐侧留痕）；
- ``self_check_<domain>.json``：严格路径自检 + 中和路径自检；
- ``operator_table_<domain>.json``（``--self-check``）：算子行为表（无 SMILES）。

用法
----
    python scripts/eval/score_disclosure_v4cn.py \
        --batch-root .../batch_b121_tuning_v44next_v12 \
        --runs-root  .../runs_b121_tuning_v44next_v12 \
        --out-dir    reports/manual_review/v13_t1_2026-11-13/t1a_b121 \
        --domain-tag biosysmodb121 [--self-check]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from rdkit import Chem, RDLogger  # noqa: E402
from rdkit.Chem.MolStandardize import rdMolStandardize  # noqa: E402

from pathway_v43.domain.identity import (  # noqa: E402
    cn_identity,
    normalize_charge_smiles,
)
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    ChemicalStateError,
    _identity_key,
    strict_identity_of,
)
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    PPV1_CRITERIA_V4,
    PPV1_EVALUATION_VERSION,
    evaluate_scientific,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    load_reference_graph,
    reference_graph_sha256,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    _batch_export_reader,
    _paired_payload,
    _product_hit_row,
    normalize_preregistration,
    preregistration_approved,
)

RDLogger.DisableLog("rdApp.*")

# ---------------------------------------------------------------------------
# 护栏常量与核心算子
# ---------------------------------------------------------------------------

STATUS_APPLIED = "applied"
STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_EXCLUDED_FAMILY = "excluded_family"
STATUS_SALT = "salt_not_normalized"
STATUS_NET_CHARGE = "net_charge_changed"
STATUS_INVARIANT = "invariant_broken"
STATUS_FAILED = "failed"

# 任务书 §6.5 排除清单（主窗口保守默认）
EXCLUDED_FAMILIES: dict[str, tuple[str, ...]] = {
    "carbonate_system": ("O=C=O", "O=C(O)[O-]", "O=C([O-])[O-]"),
    "ammonia_ammonium": ("N", "[NH4+]"),
    "cyanide_hcn": ("[C-]#N", "C#N"),
    "thiocyanate": ("[S-]C#N", "SC#N"),
    "proton_hydronium": ("[H+]", "[OH3+]"),
}

# 算子行为表夹具（合成分子，非金标、非题面；id → SMILES）。
# 覆盖面按 mimo 2026-11-13 回复 §2.1–2.8 组织。
FIXTURES: tuple[tuple[str, str], ...] = (
    ("quaternary_ammonium", "C[N+](C)(C)C"),
    ("quaternary_ammonium_chloride", "C[N+](C)(C)C.[Cl-]"),
    ("pyridinium", "c1cc[nH+]cc1"),
    ("glycine_zwitterion", "[NH3+]CC(=O)[O-]"),
    ("betaine_inner_salt", "C[N+](C)(C)CC(=O)[O-]"),
    ("nitro_neutral", "C[N+](=O)[O-]"),
    ("n_oxide_neutral", "C[N+](C)[O-]"),
    ("azoxylium", "C[N+]=NC"),
    ("phosphate_dianion", "O=P([O-])([O-])O"),
    ("sulfate_monoanion", "OS(=O)(=O)[O-]"),
    ("sulfonate_aryl", "c1ccccc1S(=O)(=O)[O-]"),
    ("coa_thioester_like", "CC(=O)SCCNC(=O)CCNC(=O)OC(C)(C)C"),
    ("sodium_salt", "[Na+].[O-]C(=O)C"),
    ("chloride_ammonium_salt", "[Cl-].C[NH3+]"),
    ("enolate", "CC([O-])=CC=O"),
    ("carbonate_dianion", "O=C([O-])[O-]"),
    ("bicarbonate", "O=C(O)[O-]"),
    ("carbon_dioxide", "O=C=O"),
    ("ammonium", "[NH4+]"),
    ("cyanide", "[C-]#N"),
    ("thiocyanate", "[S-]C#N"),
    ("hydronium", "[OH3+]"),
    ("methyl_radical", "[CH3]"),
    ("enhanced_stereo", "F[C@H](Cl)Br |&1:1|"),
    ("uncharged_acetate_acid", "CC(=O)O"),
)


@lru_cache(maxsize=1)
def _uncharger() -> rdMolStandardize.Uncharger:
    return rdMolStandardize.Uncharger()


def _net_charge(mol: Chem.Mol) -> int:
    return sum(atom.GetFormalCharge() for atom in mol.GetAtoms())


def _invariant_signature(mol: Chem.Mol) -> dict:
    """中和不变量签名：重原子图/键级 + 元素序列 + 同位素 + 立体 + 自由基。

    H 数与形式电荷**不入签名**（口径允许它们变化）；原子映射号先去（非身份）。
    """
    probe = Chem.RWMol(mol)
    for atom in probe.GetAtoms():
        atom.SetFormalCharge(0)
        atom.SetNumExplicitHs(0)
        atom.SetNoImplicit(True)
        atom.SetAtomMapNum(0)
    return {
        "graph": Chem.MolToSmiles(probe, isomericSmiles=False),
        "elements": tuple(atom.GetSymbol() for atom in mol.GetAtoms()),
        "isotopes": tuple(atom.GetIsotope() for atom in mol.GetAtoms()),
        "radicals": tuple(
            atom.GetNumRadicalElectrons() for atom in mol.GetAtoms()),
        "chiral_tags": tuple(
            str(atom.GetChiralTag()) for atom in mol.GetAtoms()),
        "bond_stereo": tuple(
            str(bond.GetStereo()) for bond in mol.GetBonds()),
        "n_frags": len(Chem.GetMolFrags(mol)),
    }


@lru_cache(maxsize=1)
def _excluded_identity_registry() -> dict[str, str]:
    """排除清单 → {strict identity: family}；解析失败的条目直接缺省。"""
    registry: dict[str, str] = {}
    for family, smiles_list in EXCLUDED_FAMILIES.items():
        for smiles in smiles_list:
            try:
                key = strict_identity_of(smiles)
            except (ChemicalStateError, ValueError, TypeError):
                continue
            if key:
                registry.setdefault(key, family)
    return registry


def _classify_salt(mol: Chem.Mol) -> str:
    """多组分 ⇒ 盐/混合物（不做去反离子，也不吃中和）。"""
    if len(Chem.GetMolFrags(mol)) <= 1:
        return ""
    return "multi_fragment"


def neutralize_checked(smiles: str) -> dict:
    """受护栏约束的电荷中和；任何回退都带机读状态，不抛异常。

    返回字段（逐侧留痕用）：
    ``input`` / ``output`` / ``status`` / ``reason`` / ``rewritten`` /
    ``net_charge_before`` / ``net_charge_after`` / ``n_frags_before`` /
    ``permanent_charge_retained`` / ``legacy_rewrite`` /
    ``identity_roundtrip_ok``。
    """
    text = str(smiles or "")
    record: dict = {
        "input": text,
        "output": text,
        "status": STATUS_NOT_APPLICABLE,
        "reason": "",
        "rewritten": False,
        "net_charge_before": None,
        "net_charge_after": None,
        "n_frags_before": None,
        "permanent_charge_retained": False,
        "legacy_rewrite": False,
        "identity_roundtrip_ok": None,
    }
    if not text.strip():
        record["reason"] = "empty_smiles"
        return record
    try:
        mol = Chem.MolFromSmiles(text)
    except Exception:  # noqa: BLE001 —— 解析器任何异常都按不可解析处理
        mol = None
    if mol is None:
        record.update({"status": STATUS_FAILED, "reason": "parse_failed"})
        return record
    try:
        identity_before = _identity_key(mol)
    except (ChemicalStateError, ValueError, TypeError) as exc:
        record.update({
            "status": STATUS_FAILED,
            "reason": f"identity_unavailable:{type(exc).__name__}",
        })
        return record
    charge_before = _net_charge(mol)
    record["net_charge_before"] = charge_before
    record["n_frags_before"] = len(Chem.GetMolFrags(mol))
    try:
        legacy = normalize_charge_smiles(text)
    except Exception:  # noqa: BLE001
        legacy = None
    record["legacy_rewrite"] = bool(legacy is not None and legacy != text)

    # 5. 排除清单（先于一切改写判定）
    family = _excluded_identity_registry().get(identity_before)
    if family:
        record.update({
            "status": STATUS_EXCLUDED_FAMILY,
            "reason": f"never_exempt_family:{family}",
        })
        return record

    # 4. 盐 / 反离子单列
    salt_reason = _classify_salt(mol)
    if salt_reason:
        record.update({"status": STATUS_SALT, "reason": salt_reason})
        return record

    # 短路：净电中性且无任何带电荷原子 ⇒ 不往返
    if charge_before == 0 and all(
            atom.GetFormalCharge() == 0 for atom in mol.GetAtoms()):
        record["reason"] = "neutral_no_formal_charge"
        return record

    # 3. 中和（RDKit Uncharger；与 domain.identity 同一算子）
    try:
        neutral = _uncharger().uncharge(Chem.Mol(mol))
        Chem.SanitizeMol(neutral)
    except Exception as exc:  # noqa: BLE001
        record.update({
            "status": STATUS_FAILED,
            "reason": f"uncharge_error:{type(exc).__name__}",
        })
        return record
    charge_after = _net_charge(neutral)
    record["net_charge_after"] = charge_after

    # 1. 不变量
    if _invariant_signature(mol) != _invariant_signature(neutral):
        record.update({
            "status": STATUS_INVARIANT,
            "reason": "heavy_graph_or_stereo_changed",
        })
        return record

    # 3. 净电荷保护（只允许"带电 → 更中性"，不允许 0→带电/符号翻转/变大）
    if charge_before == 0 and charge_after != 0:
        record.update({
            "status": STATUS_NET_CHARGE,
            "reason": "zero_to_nonzero",
        })
        return record
    if charge_before != 0 and charge_after != 0:
        if (charge_before > 0) != (charge_after > 0):
            record.update({
                "status": STATUS_NET_CHARGE, "reason": "sign_flip"})
            return record
        if abs(charge_after) > abs(charge_before):
            record.update({
                "status": STATUS_NET_CHARGE, "reason": "charge_grew"})
            return record
        record["permanent_charge_retained"] = True

    # 2. 身份同源（CXSMILES，与 v4 参考侧同一机器）+ 幂等自检
    try:
        identity_after = _identity_key(neutral)
        roundtrip_ok = strict_identity_of(identity_after) == identity_after
    except (ChemicalStateError, ValueError, TypeError) as exc:
        record.update({
            "status": STATUS_FAILED,
            "reason": f"identity_roundtrip_error:{type(exc).__name__}",
            "identity_roundtrip_ok": False,
        })
        return record
    record["identity_roundtrip_ok"] = roundtrip_ok
    if not roundtrip_ok:
        record.update({
            "status": STATUS_FAILED,
            "reason": "identity_roundtrip_failed",
        })
        return record

    if identity_after == identity_before:
        record["reason"] = "identity_unchanged"
        return record

    record.update({
        "status": STATUS_APPLIED,
        "reason": "charge_only_rewrite",
        "output": identity_after,
        "rewritten": True,
    })
    return record


def _neutralize(smiles: str) -> str:
    """电荷中和（受护栏）；不可中和 / 被排除时保留原文。"""
    return neutralize_checked(smiles)["output"]


def _neutral_graph(graph: dict, records: dict | None = None) -> dict:
    out = json.loads(json.dumps(graph))
    collected = records if records is not None else {}
    for node in out.get("nodes") or []:
        smiles = node.get("structure_smiles")
        if not smiles:
            continue
        record = neutralize_checked(str(smiles))
        collected[str(node.get("node_id"))] = record
        node["structure_smiles"] = record["output"]
    return out


def _neutral_payload(payload: dict, records: dict | None = None) -> dict:
    out = json.loads(json.dumps(payload))
    collected = records if records is not None else {}
    for state in out.get("states") or []:
        if not isinstance(state, dict):
            continue
        body = state.get("payload")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                body = {}
            state["payload"] = body
        if not isinstance(body, dict) or not body.get("smiles_isomeric"):
            continue
        record = neutralize_checked(str(body["smiles_isomeric"]))
        collected[str(state.get("state_id"))] = record
        if record["status"] != STATUS_APPLIED:
            continue
        # 身份轴改写：smiles_isomeric / cn_identity / formal_charge；
        # state_id 保持原值（不透明出现键），见模块 docstring 第 7 条。
        body["smiles_isomeric"] = record["output"]
        body["cn_identity"] = str(cn_identity(record["output"]) or "")
        if record["net_charge_after"] is not None:
            body["formal_charge"] = record["net_charge_after"]
        body["v4cn_derived_fields_policy"] = "identity_axis_only"
    return out


def _record_summary(records: dict) -> dict:
    """逐侧留痕汇总：状态直方图 + 改写数；不含 SMILES。"""
    histogram: dict[str, int] = {}
    reasons: dict[str, int] = {}
    n_changed = 0
    n_legacy_rewrite = 0
    for record in (records or {}).values():
        histogram[record["status"]] = histogram.get(record["status"], 0) + 1
        if record.get("reason"):
            key = str(record["reason"]).split(":", 1)[0]
            reasons[key] = reasons.get(key, 0) + 1
        if record.get("rewritten"):
            n_changed += 1
        if record.get("legacy_rewrite"):
            n_legacy_rewrite += 1
    return {
        "n_structures": len(records or {}),
        "status_histogram": dict(sorted(histogram.items())),
        "reason_histogram": dict(sorted(reasons.items())),
        "n_rewritten": n_changed,
        "n_legacy_rewrites_suppressed": sum(
            1 for record in (records or {}).values()
            if record.get("legacy_rewrite") and not record.get("rewritten")),
        "n_legacy_rewrite": n_legacy_rewrite,
        "changed_state_ids": sorted(
            key for key, record in (records or {}).items()
            if record.get("rewritten")),
    }


# ---------------------------------------------------------------------------
# 批根装载与判分（结构不变）
# ---------------------------------------------------------------------------


def _load_batch(batch_root: Path, runs_root: Path):
    manifest = json.loads(
        (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
    split_manifest = json.loads(
        (batch_root / "split_manifest.json").read_text(encoding="utf-8"))
    order = [str(q) for q in manifest.get("registration_order") or []]
    entries = {str(e["qid"]): e for e in manifest.get("entries") or []}
    prereg_path = batch_root / "preregistration_approval.json"
    prereg = (
        json.loads(prereg_path.read_text(encoding="utf-8"))
        if prereg_path.is_file() else None)
    if not preregistration_approved(prereg):
        raise SystemExit("预注册批准记录缺席/未批准；本脚本只读已批准批根")
    return manifest, split_manifest, order, entries, prereg


def _build_inputs(batch_root: Path, runs_root: Path, neutralize: bool,
                  domain_tag: str):
    manifest, split_manifest, order, entries, prereg = _load_batch(
        batch_root, runs_root)
    graphs: dict[str, dict] = {}
    graph_by_qid: dict[str, str] = {}
    graph_records: dict[str, dict] = {}
    for qid in order:
        entry = entries[qid]
        graph = load_reference_graph(batch_root / str(entry["graph_rel"]))
        records: dict = {}
        if neutralize:
            graph = _neutral_graph(graph, records)
        graph_records[str(graph["reference_graph_id"])] = records
        graphs[str(graph["reference_graph_id"])] = graph
        graph_by_qid[qid] = str(graph["reference_graph_id"])

    cache: dict[str, dict] = {}
    raw_reader = _batch_export_reader(runs_root, cache)
    reader_cache: dict[str, dict] = {}
    payload_records: dict[str, dict] = {}

    def reader(entry: dict) -> dict:
        raw = raw_reader(entry)
        payload = raw.get("payload") or {}
        if not neutralize:
            reader_cache[str(entry.get("export_digest"))] = payload
            return {"payload": payload}
        records: dict = {}
        neutral = _neutral_payload(payload, records)
        payload_records[str(entry.get("export_digest"))] = records
        reader_cache[str(entry.get("export_digest"))] = neutral
        return {"payload": neutral}

    exports: list[dict] = []
    cases: dict[str, dict] = {}
    for qid in order:
        case_path = batch_root / "cases" / f"{qid}.json"
        case = (
            json.loads(case_path.read_text(encoding="utf-8"))
            if case_path.is_file() else {})
        cases[qid] = case
        digest = str(case.get("export_digest") or "")
        run_id = str((entries[qid] or {}).get("run_id") or "")
        if digest and run_id:
            exports.append({
                "run_id": run_id, "export_digest": digest, "qid": qid,
                "lossy_projection": False,
            })
    evaluation_input = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "run_identity": {
            "run_id": f"s5b-batch:{manifest.get('batch_tag') or 's5b'}",
            "profile_version": PPV1_PROFILE_SCHEMA_VERSION,
            "export_schema_version": PPV1_NATIVE_EXPORT_VERSION,
        },
        "native_path_exports": exports,
        "reference_graph_manifest": [
            {
                "reference_graph_id": graph_by_qid[qid],
                "sha256": reference_graph_sha256(graphs[graph_by_qid[qid]])
                if neutralize else str(entries[qid]["graph_sha256"]),
                "domain": domain_tag,
                "track": "known_evidence_reconstruction",
                "qid": qid,
            }
            for qid in order
        ],
        "split_manifest": split_manifest,
        "domain": domain_tag,
        "track": "known_evidence_reconstruction",
        "metric_policy_version": "ppv1-evaluation-metrics-proposed",
        "preregistration_id": str(
            (prereg or {}).get("preregistration_id")
            or "prereg-s5b-pending"),
        "scoring_policy_version": "ppv1-evaluation-scoring-proposed",
        "missingness_policy_version":
            "ppv1-evaluation-missingness-proposed",
        "data_scope": "real",
        "interface_verification": False,
        "model_provider_policy": {
            "provider_kind": "real",
            "authorization": str(
                (prereg or {}).get("user_authorization")
                or "s5b-launch-authorized-by-user-2026-10-09"),
        },
    }
    output = evaluate_scientific(
        evaluation_input, reference_graphs=graphs,
        native_export_reader=reader,
        preregistration=normalize_preregistration(prereg),
        criteria_version=PPV1_CRITERIA_V4)
    rows: list[dict] = []
    sample_by_graph = {
        str(s.get("reference_graph_id")): s
        for s in output.get("sample_results") or []}
    for qid in order:
        graph_id = graph_by_qid[qid]
        sample = sample_by_graph.get(graph_id)
        graph = graphs[graph_id]
        payload = _paired_payload(reader_cache, sample)
        digest = str((cases.get(qid) or {}).get("export_digest") or "")
        rows.append({
            "qid": qid,
            "run_id": str((entries[qid] or {}).get("run_id") or ""),
            "run_status": str((cases.get(qid) or {}).get("status")
                              or "no_case"),
            "product_hit": _product_hit_row(sample, payload, graph),
            "sample": sample,
            "payload": payload,
            "graph": graph,
            "normalization": {
                "reference": graph_records.get(graph_id) or {},
                "prediction": payload_records.get(digest) or {},
            },
        })
    return output, rows


def _hits(rows: list[dict], key: str) -> dict:
    return {
        f"hit@{k}": sum(
            1 for row in rows
            if (row[key].get("rank") or math.inf) <= k)
        for k in (1, 3, 5)
    }


def _strict_rows_from_metrics(metrics_path: Path) -> dict[str, dict]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return {
        str(row.get("qid")): row for row in metrics.get("per_qid") or []
    }


def _compare_self_check(ours: list[dict], official: dict[str, dict]) -> list:
    diffs = []
    for row in ours:
        qid = row["qid"]
        off = official.get(qid) or {}
        fields = []
        mine = row["product_hit"]
        theirs = off.get("product_hit") or {}
        for key in ("rank", "bucket", "matched_product_hit"):
            if mine.get(key) != theirs.get(key):
                fields.append({
                    "field": f"product_hit.{key}",
                    "ours": mine.get(key), "official": theirs.get(key)})
        if sorted(mine.get("product_hit_events") or []) != sorted(
                theirs.get("product_hit_events") or []):
            fields.append({
                "field": "product_hit.product_hit_events",
                "ours": sorted(mine.get("product_hit_events") or []),
                "official": sorted(theirs.get("product_hit_events") or [])})
        if fields:
            diffs.append({"qid": qid, "fields": fields})
    return diffs


def _bucket_counts(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        bucket = str(row["product_hit"].get("bucket") or "")
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# 中和路径自检 + 算子行为表
# ---------------------------------------------------------------------------


def _self_check_neutralization(rows: list[dict]) -> dict:
    """中和路径自检：幂等、零静默回退、身份往返、逐侧状态覆盖。"""
    records: list[dict] = []
    for row in rows:
        normalization = row.get("normalization") or {}
        records.extend((normalization.get("reference") or {}).values())
        records.extend((normalization.get("prediction") or {}).values())
    idempotence_violations: list[str] = []
    applied = [record for record in records if record["status"] == STATUS_APPLIED]
    for record in applied:
        again = neutralize_checked(record["output"])
        if again["output"] != record["output"]:
            idempotence_violations.append(record["input"])
    status_histogram: dict[str, int] = {}
    reason_histogram: dict[str, int] = {}
    n_silent = 0
    for record in records:
        status_histogram[record["status"]] = \
            status_histogram.get(record["status"], 0) + 1
        if record.get("reason"):
            key = str(record["reason"]).split(":", 1)[0]
            reason_histogram[key] = reason_histogram.get(key, 0) + 1
        if record["status"] != STATUS_APPLIED and not record.get("reason"):
            n_silent += 1
    n_failed = status_histogram.get(STATUS_FAILED, 0)
    return {
        "n_records": len(records),
        "n_applied": len(applied),
        "status_histogram": dict(sorted(status_histogram.items())),
        "reason_histogram": dict(sorted(reason_histogram.items())),
        "n_idempotence_violations": len(idempotence_violations),
        "idempotence_violations": idempotence_violations[:20],
        "n_silent_reverts": n_silent,
        "n_failed": n_failed,
        "ok": (not idempotence_violations) and n_silent == 0 and n_failed == 0,
    }


def probe_operator_table() -> dict:
    """固定夹具算子行为表：只出夹具名 + 布尔/计数，不含 SMILES。"""
    rows = []
    for fixture_id, smiles in FIXTURES:
        record = neutralize_checked(smiles)
        rows.append({
            "fixture_id": fixture_id,
            "status": record["status"],
            "reason": str(record["reason"]).split(":", 1)[0],
            "rewritten": bool(record["rewritten"]),
            "net_charge_before": record["net_charge_before"],
            "net_charge_after": record["net_charge_after"],
            "n_frags_before": record["n_frags_before"],
            "permanent_charge_retained": record["permanent_charge_retained"],
            "legacy_rewrite": record["legacy_rewrite"],
            "identity_roundtrip_ok": record["identity_roundtrip_ok"],
        })
    return {
        "fixture_count": len(rows),
        "status_histogram": {
            status: sum(1 for row in rows if row["status"] == status)
            for status in sorted({row["status"] for row in rows})
        },
        "fixtures": rows,
    }


# ---------------------------------------------------------------------------
# 翻转归因
# ---------------------------------------------------------------------------


def _prediction_side_flags(payload: dict, changed_ids: set[str]) -> dict:
    """预测侧改写落在反应物还是产物（按候选事件参与物归类）。"""
    result = {"reactant": False, "product": False}
    if not changed_ids:
        return result
    for event in payload.get("events") or []:
        body = event.get("payload")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                body = {}
        for participant in (body or {}).get("participants") or []:
            if str(participant.get("state_ref") or "") not in changed_ids:
                continue
            side = str(participant.get("side") or "")
            if side in result:
                result[side] = True
    return result


def _attribution(row: dict) -> dict:
    normalization = row.get("normalization") or {}
    reference = normalization.get("reference") or {}
    prediction = normalization.get("prediction") or {}
    ref_roles = {
        str(node.get("role"))
        for node in (row.get("graph") or {}).get("nodes") or []
        if (reference.get(str(node.get("node_id"))) or {}).get("rewritten")
    }
    changed_states = {
        str(state_id) for state_id, record in prediction.items()
        if record.get("rewritten")
    }
    pred_sides = _prediction_side_flags(row.get("payload") or {},
                                        changed_states)
    substrate_side = ("root" in ref_roles) or pred_sides["reactant"]
    product_side = ("principal_product" in ref_roles) or pred_sides["product"]
    if substrate_side and product_side:
        label = "both_sides"
    elif product_side:
        label = "product_side"
    elif substrate_side:
        label = "substrate_side"
    else:
        label = "none"
    return {
        "label": label,
        "reference_roles_rewritten": sorted(ref_roles),
        "prediction_reactant_rewritten": pred_sides["reactant"],
        "prediction_product_rewritten": pred_sides["product"],
        "n_prediction_states_rewritten": len(changed_states),
    }


def _legacy_bucket(row: dict, direction: str | None) -> str:
    """加固前后差异的原因桶：取被护栏拦下的改写状态（无 SMILES）。"""
    if direction is None:
        return "no_change"
    normalization = row.get("normalization") or {}
    statuses = set()
    for side in ("reference", "prediction"):
        for record in (normalization.get(side) or {}).values():
            if record.get("legacy_rewrite") and not record.get("rewritten"):
                statuses.add(record["status"])
    if not statuses:
        return "same_rewrite_set"
    return "+".join(sorted(statuses))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--domain-tag", required=True)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--emit-operator-table", action="store_true",
                        help="输出固定夹具的机读算子行为表（无 SMILES）")
    parser.add_argument("--legacy-flips", default="",
                        help="旧版（commit 78654bf）flips jsonl，用于前后差异分桶")
    parser.add_argument("--strict-metrics", default="",
                        help="严格 v4 逐题谱系（缺省 <batch-root>/metrics_v4.json）")
    args = parser.parse_args(argv)

    batch_root = Path(args.batch_root).resolve()
    runs_root = Path(args.runs_root).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.emit_operator_table:
        table = probe_operator_table()
        (out_dir / "operator_table_all.json").write_text(
            json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(table["status_histogram"], ensure_ascii=False))

    metrics_path = (Path(args.strict_metrics).resolve()
                    if args.strict_metrics
                    else batch_root / "metrics_v4.json")
    official_rows = _strict_rows_from_metrics(metrics_path)

    report: dict = {
        "domain_tag": args.domain_tag,
        "batch_root": str(batch_root),
        "strict_source": "metrics_v4.json (frozen judge, read-only)",
        "v4cn_definition": (
            "guarded charge neutralization (invariants + CX identity + net "
            "charge + salt/family exclusions) on gold node structures and "
            "submitted state smiles; v4 code path unchanged"),
        "denominator": len(official_rows),
    }

    if args.self_check:
        _, strict_rows = _build_inputs(
            batch_root, runs_root, neutralize=False,
            domain_tag=args.domain_tag)
        diffs = _compare_self_check(strict_rows, official_rows)
        report["self_check"] = {
            "n_compared": len(strict_rows),
            "n_diffs": len(diffs),
            "diffs": diffs,
            "strict_hits": _hits(strict_rows, "product_hit"),
            "strict_buckets": _bucket_counts(strict_rows),
        }
        if diffs:
            (out_dir / f"self_check_{args.domain_tag}.json").write_text(
                json.dumps(report["self_check"], ensure_ascii=False,
                           indent=1),
                encoding="utf-8")
            print(json.dumps(report["self_check"], ensure_ascii=False,
                             indent=1))
            return 3

    _, cn_rows = _build_inputs(
        batch_root, runs_root, neutralize=True, domain_tag=args.domain_tag)

    if args.self_check:
        neutral_check = _self_check_neutralization(cn_rows)
        report["self_check"]["neutralization"] = neutral_check
        report["self_check"]["operator_table"] = probe_operator_table()
        (out_dir / f"self_check_{args.domain_tag}.json").write_text(
            json.dumps(report["self_check"], ensure_ascii=False, indent=1),
            encoding="utf-8")
        if not neutral_check["ok"]:
            print(json.dumps(neutral_check, ensure_ascii=False, indent=1))
            return 3

    strict_hits = {
        "hit@1": sum(1 for qid in official_rows
                     if ((official_rows[qid].get("product_hit") or {})
                         .get("rank") or math.inf) <= 1),
        "hit@3": sum(1 for qid in official_rows
                     if ((official_rows[qid].get("product_hit") or {})
                         .get("rank") or math.inf) <= 3),
        "hit@5": sum(1 for qid in official_rows
                     if ((official_rows[qid].get("product_hit") or {})
                         .get("rank") or math.inf) <= 5),
    }
    cn_hits = _hits(cn_rows, "product_hit")
    denominator = len(official_rows)
    legacy = {}
    if args.legacy_flips:
        legacy_path = Path(args.legacy_flips)
        if legacy_path.is_file():
            for line in legacy_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    legacy[str(row.get("qid"))] = row
    flips = []
    reason_buckets: dict[str, int] = {}
    side_buckets: dict[str, int] = {}
    for row in cn_rows:
        qid = row["qid"]
        before = (official_rows.get(qid) or {}).get("product_hit") or {}
        after = row["product_hit"]
        before_rank = before.get("rank")
        after_rank = after.get("rank")
        direction = None
        if before_rank is None and after_rank is not None:
            direction = "new_hit"
        elif before_rank is not None and after_rank is None:
            direction = "lost_hit"
        elif before_rank != after_rank:
            direction = "rank_changed"
        attribution = _attribution(row)
        bucket = _legacy_bucket(row, direction)
        if direction:
            reason_buckets[bucket] = reason_buckets.get(bucket, 0) + 1
            side_buckets[attribution["label"]] = \
                side_buckets.get(attribution["label"], 0) + 1
        flip = {
            "qid": qid,
            "run_id": row["run_id"],
            "before_rank": before_rank,
            "after_rank": after_rank,
            "before_bucket": before.get("bucket"),
            "after_bucket": after.get("bucket"),
            "direction": direction,
            "before_events": before.get("product_hit_events") or [],
            "after_events": after.get("product_hit_events") or [],
            "reference_side": _record_summary(
                (row.get("normalization") or {}).get("reference") or {}),
            "prediction_side": _record_summary(
                (row.get("normalization") or {}).get("prediction") or {}),
            "attribution": attribution,
            "guard_bucket": bucket,
        }
        legacy_row = legacy.get(qid)
        if legacy_row is not None:
            flip["legacy_after_rank"] = legacy_row.get("after_rank")
            flip["legacy_differs"] = (
                legacy_row.get("after_rank") != after_rank)
        flips.append(flip)
    report.update({
        "strict_v4": {
            "matched_product_hit": strict_hits,
            "buckets": {
                str(k): v for k, v in (
                    (json.loads(metrics_path.read_text(
                        encoding="utf-8"))
                     .get("matched_product_hit_caliber") or {}).get("buckets")
                    or {}).items()},
        },
        "v4cn": {
            "matched_product_hit": cn_hits,
            "buckets": _bucket_counts(cn_rows),
        },
        "delta": {
            key: {
                "absolute": cn_hits[key] - strict_hits[key],
                "pct": round(
                    (cn_hits[key] - strict_hits[key]) / strict_hits[key]
                    * 100, 2) if strict_hits[key] else None,
            }
            for key in ("hit@1", "hit@3", "hit@5")
        },
        "flips": {
            "n_total": sum(1 for f in flips if f["direction"]),
            "n_new_hit": sum(1 for f in flips
                             if f["direction"] == "new_hit"),
            "n_lost_hit": sum(1 for f in flips
                              if f["direction"] == "lost_hit"),
            "n_rank_changed": sum(1 for f in flips
                                  if f["direction"] == "rank_changed"),
            "reason_buckets": dict(sorted(reason_buckets.items())),
            "attribution_buckets": dict(sorted(side_buckets.items())),
        },
        "n_flips_files": 1,
    })
    if legacy:
        report["legacy_comparison"] = {
            "n_common_qids": sum(1 for flip in flips if "legacy_differs"
                                 in flip),
            "n_after_rank_differs": sum(
                1 for flip in flips if flip.get("legacy_differs")),
            "reason_buckets": {
                bucket: sum(1 for flip in flips
                            if flip.get("legacy_differs")
                            and flip["guard_bucket"] == bucket)
                for bucket in sorted({flip["guard_bucket"] for flip in flips
                                      if flip.get("legacy_differs")})
            },
        }
    (out_dir / f"disclosure_v4cn_{args.domain_tag}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / f"flips_v4cn_{args.domain_tag}.jsonl").open(
            "w", encoding="utf-8") as handle:
        for flip in flips:
            handle.write(json.dumps(flip, ensure_ascii=False) + "\n")
    print(json.dumps({
        "domain_tag": args.domain_tag,
        "denominator": denominator,
        "strict_v4": strict_hits,
        "v4cn": cn_hits,
        "delta": report["delta"],
        "flips": report["flips"],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())