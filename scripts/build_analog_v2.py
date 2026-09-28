"""Phase D D2:corpus_templates v1 → v2 离线重映射管线(零网络、零金标)。

只读输入 ``assets/analog/corpus_templates_v1.jsonl``;输出完整替代版
``assets/analog/corpus_templates_v2.jsonl`` + 机器可读 provenance
(``reports/phase_d/v2_remap_provenance.jsonl`` + 漏斗 summary)。

**不看任何 dev/298 金标、不接触预测目标**;重映射条件是纯结构条件:
v1 模板在 ``extract_donor_transform`` 下不可判定(实测全部为
transform_no_change —— 映射号两侧完全一致,真实反应发生在未映射区)
才尝试。映射号只从模板自身反应物/产物建立(MCS 公共骨架 + 两侧独有
原子),确定性 tie-break(两侧各取字典序最小匹配;对称等价选择是同构
的,不影响化学内容)。

状态:
- ``unchanged``:v1 变换可判定(14355 行,字节原样);
- ``remapped``:重映射成功且过全部机器门禁(替换 mapped_lhs/rhs +
  center_atoms,其余字段原样,附加 ``v2_remap`` 块);
- ``rejected``:重映射失败/门禁不过(v1 原语义保留,不删除)。

映射工具:``v43-analogmap-1``(纯确定性算法,无模型权重;配置与
"weights: none"随 provenance 记录)。行级一一对应(v1 17183 行 ↔ v2
17183 行;96 个重复 record_id 是 v1 事实,登记于 summary,不删行)。

用法:
  OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/build_analog_v2.py \
      [--workers 4] [--mcs-timeout 10]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import rdFMCS

RDLogger.DisableLog("rdApp.*")

from pathway_v43.services.analog_source import _lhs_rhs, _strip_map  # noqa: E402
from pathway_v43.services.donor_applicability import (  # noqa: E402
    extract_donor_transform,
)

REPO = Path(__file__).resolve().parents[1]
V1 = REPO / "assets" / "analog" / "corpus_templates_v1.jsonl"
V2 = REPO / "assets" / "analog" / "corpus_templates_v2.jsonl"
PROV = REPO / "reports" / "phase_d" / "v2_remap_provenance.jsonl"
SUMMARY = REPO / "reports" / "phase_d" / "v2_remap_summary.json"

TOOL_NAME = "v43-analogmap-1"
TOOL_CONFIG = {
    "kind": "deterministic_mcs_mapping",
    "mcs_atom_compare": "CompareElements",
    "mcs_bond_compare": "CompareOrder",
    "mcs_ring_matches_ring_only": True,
    "mcs_complete_rings_only": False,
    "mcs_match_valences": False,
    "match_selection": "lexicographic_min_each_side",
    "numbering": "common_atoms_by_lhs_idx_then_side_uniques",
    "center_rule": "endpoints_of_bond_changes_and_added_bonds_plus_added_"
                   "removed_h_delta_charge_maps",
    "smiles_form": "aromatic_perception_as_parsed",
}
TOOL_WEIGHTS = "none (algorithmic; no model weights)"

_MAX_MATCHES = 64  # 每侧 MCS 匹配枚举上限(超出取已枚举集的最小者)


def _sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _center_from_transform(t: dict) -> list[int]:
    center: set[int] = set()
    for ch in t["bond_changes"]:
        center.update((int(ch["map1"]), int(ch["map2"])))
    for ch in t["added_bonds"]:
        center.update((int(ch["map1"]), int(ch["map2"])))
    center.update(int(k) for k in t["added_atoms"])
    center.update(int(k) for k in t["removed_atoms"])
    center.update(int(k) for k in t["h_gain_maps"])
    center.update(int(k) for k in t["h_loss_maps"])
    center.update(int(k) for k in t["charge_changed_maps"])
    return sorted(center)


def remap(lhs_smiles: str, rhs_smiles: str, *, mcs_timeout: float):
    """裸 lhs/rhs → (mapped_lhs, mapped_rhs, center_atoms, 拒因)。"""
    lm = Chem.MolFromSmiles(lhs_smiles)
    rm = Chem.MolFromSmiles(rhs_smiles)
    if lm is None or rm is None:
        return None, "unparseable_side"
    try:
        # RDKit 2026.03 API:FindMCS 只接受位置参数或 MCSParameters;
        # 默认 AtomTyper=CompareElements / BondTyper=CompareOrder 正是
        # 本工具声明的比较语义,显式固定防漂移
        params = rdFMCS.MCSParameters()
        params.Timeout = int(mcs_timeout)
        params.AtomCompareParameters.MatchValences = False
        params.AtomCompareParameters.RingMatchesRingOnly = True
        params.AtomCompareParameters.CompleteRingsOnly = False
        mcs = rdFMCS.FindMCS([lm, rm], params)
    except Exception:
        return None, "mcs_exception"
    if mcs.canceled:
        return None, "mcs_timeout"
    if mcs.numAtoms == 0 or not mcs.smartsString:
        return None, "mcs_empty"
    query = Chem.MolFromSmarts(mcs.smartsString)
    lm_m = lm.GetSubstructMatches(query, uniquify=False,
                                  maxMatches=_MAX_MATCHES)
    rm_m = rm.GetSubstructMatches(query, uniquify=False,
                                  maxMatches=_MAX_MATCHES)
    if not lm_m or not rm_m:
        return None, "mcs_no_match"
    l_match, r_match = min(lm_m), min(rm_m)

    numbering: dict[tuple[str, int], int] = {}
    nxt = 1
    for li, ri in zip(l_match, r_match):
        numbering[("lhs", li)] = nxt
        numbering[("rhs", ri)] = nxt
        nxt += 1
    for a in lm.GetAtoms():
        if ("lhs", a.GetIdx()) not in numbering:
            numbering[("lhs", a.GetIdx())] = nxt
            nxt += 1
    for a in rm.GetAtoms():
        if ("rhs", a.GetIdx()) not in numbering:
            numbering[("rhs", a.GetIdx())] = nxt
            nxt += 1

    lm2, rm2 = Chem.Mol(lm), Chem.Mol(rm)
    for a in lm2.GetAtoms():
        a.SetAtomMapNum(numbering[("lhs", a.GetIdx())])
    for a in rm2.GetAtoms():
        a.SetAtomMapNum(numbering[("rhs", a.GetIdx())])
    mapped_lhs = Chem.MolToSmiles(lm2)
    mapped_rhs = Chem.MolToSmiles(rm2)

    t, reason = extract_donor_transform(mapped_lhs, mapped_rhs)
    if t is None:
        return None, f"remap_still_no_transform:{reason}"
    center = _center_from_transform(t)
    if not center:
        return None, "empty_center"
    return (mapped_lhs, mapped_rhs, center), ""


def machine_checks(row_v2: dict, lhs_orig: str, rhs_orig: str) -> list[str]:
    """任务书 §3.3 机器门禁(全部通过才可 remapped);返回拒因列表。"""
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.donor_applicability import assess_donor

    bad: list[str] = []
    lhs, rhs = row_v2["mapped_lhs"], row_v2["mapped_rhs"]
    lm, rm = Chem.MolFromSmiles(lhs), Chem.MolFromSmiles(rhs)
    # 1) 两侧可解析
    if lm is None or rm is None:
        return ["unparseable"]
    lm_nos = [a.GetAtomMapNum() for a in lm.GetAtoms() if a.GetAtomMapNum()]
    rm_nos = [a.GetAtomMapNum() for a in rm.GetAtoms() if a.GetAtomMapNum()]
    # 2) 映射号各侧唯一
    if len(lm_nos) != len(set(lm_nos)) or len(rm_nos) != len(set(rm_nos)):
        bad.append("duplicate_map_no")
    # 3) 保留原子元素一致 + 5) 变化非空(经提取器)
    t, reason = extract_donor_transform(lhs, rhs)
    if t is None:
        bad.append(f"transform_undecidable:{reason}")
        t = None
    # 4) 去映射两侧与原记录一致(化学内容未被映射过程改变)
    if cn_identity(_strip_map(lhs)) != cn_identity(lhs_orig) \
            or cn_identity(_strip_map(rhs)) != cn_identity(rhs_orig):
        bad.append("stripped_structure_changed")
    # 6) 中心与变化一致
    if t is not None:
        expect = _center_from_transform(t)
        if sorted(row_v2["center_atoms"]) != expect:
            bad.append("center_inconsistent_with_transform")
    # 7) 提取器可判定已覆盖(3);8) assess_donor 不抛异常
    ref = {
        "record_id": row_v2.get("record_id", ""),
        "index": "analog_corpus_templates",
        "asset_file": "analog/corpus_templates_v2.jsonl",
        "asset_sha256": "0" * 64,
        "line_no": 0,
        "mapping_quality": "mapped_bijection",
        "reactant_smiles": _strip_map(lhs),
        "product_smiles": _strip_map(rhs),
        "mapped_lhs": lhs, "mapped_rhs": rhs,
        "center_atoms": list(row_v2["center_atoms"]),
    }
    for probe in (lhs_orig, rhs_orig):
        try:
            assess_donor(ref, _strip_map(probe))
        except Exception as exc:  # noqa: BLE001 —— 门禁要求"不抛异常"
            bad.append(f"assess_donor_raises:{type(exc).__name__}")
            break
    return bad


def process_line(args: tuple) -> dict:
    line, line_no, mcs_timeout = args
    row = json.loads(line)
    lhs_v1, rhs_v1 = _lhs_rhs(row)
    lhs_orig, rhs_orig = _strip_map(lhs_v1), _strip_map(rhs_v1)
    t_v1, v1_reason = extract_donor_transform(lhs_v1, rhs_v1)
    out = {
        "template_id": row.get("template_id", ""),
        "record_id": str(row.get("record_id", "")),
        "v1_line_no": line_no,
        "v1_line_sha256": _sha(line),
        "status": "unchanged",
        "reason": "",
        "v1_reason": v1_reason,
        "row": None,          # None = 原行字节输出
        "mapped_lhs_v1": lhs_v1, "mapped_rhs_v1": rhs_v1,
        "center_v1": [int(x) for x in (row.get("center_atoms") or [])],
    }
    if t_v1 is not None:
        return out  # v1 可判定:不动
    out["status"], out["reason"] = "remap_candidate", v1_reason
    if not lhs_orig or not rhs_orig:
        out["status"], out["reason"] = "rejected", "empty_stripped_side"
        return out
    # 结构无变化门(复核发现的系统性缺陷:电子转移/离子对/转运类模板
    # 去映射两侧本就同分子;MCS 受单连通分量限制会匹配其中一个组分,
    # 把其余组分伪造成 add/rem —— 任何映射对无结构变化反应都无意义)
    from pathway_v43.domain.identity import cn_identity

    if cn_identity(lhs_orig) == cn_identity(rhs_orig):
        out["status"], out["reason"] = "rejected", "no_structural_change"
        return out
    res, rsn = remap(lhs_orig, rhs_orig, mcs_timeout=mcs_timeout)
    if res is None:
        out["status"], out["reason"] = "rejected", rsn
        return out
    mapped_lhs, mapped_rhs, center = res
    row_v2 = dict(row)
    row_v2["mapped_lhs"] = mapped_lhs
    row_v2["mapped_rhs"] = mapped_rhs
    row_v2["center_atoms"] = center
    qc = dict(row.get("qc_flags") or {})
    qc["element_balance"] = True   # 机器门禁 3 重算
    qc["bijection"] = True         # 门禁 2 重算(各侧唯一)
    qc["v2_recomputed"] = True
    row_v2["qc_flags"] = qc
    row_v2["v2_remap"] = {
        "status": "remapped",
        "tool": TOOL_NAME,
        "from_v1_mapping": {"lhs": lhs_v1, "rhs": rhs_v1},
        "v1_failure_reason": v1_reason,
    }
    bad = machine_checks(row_v2, lhs_orig, rhs_orig)
    if bad:
        out["status"], out["reason"] = "rejected", ";".join(bad)
        return out
    out["status"], out["reason"] = "remapped", ""
    out["row"] = row_v2
    out["mapped_lhs_v2"] = mapped_lhs
    out["mapped_rhs_v2"] = mapped_rhs
    out["center_v2"] = center
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mcs-timeout", type=float, default=10.0)
    args = ap.parse_args()

    lines = [ln for ln in V1.read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    jobs = [(ln, i + 1, args.mcs_timeout) for i, ln in enumerate(lines)]
    t0 = time.time()
    results: list[dict] = []
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            results = list(ex.map(process_line, jobs, chunksize=16))
    else:
        results = [process_line(j) for j in jobs]

    V2.parent.mkdir(parents=True, exist_ok=True)
    PROV.parent.mkdir(parents=True, exist_ok=True)
    v2_sha = _sha("")  # placeholder, replaced below
    with open(V2, "w", encoding="utf-8") as f2, \
            open(PROV, "w", encoding="utf-8") as fp:
        for i, (ln, res) in enumerate(zip(lines, results), 1):
            if res["row"] is not None:
                out_line = json.dumps(
                    res["row"], ensure_ascii=False, sort_keys=False)
            else:
                out_line = ln  # unchanged/rejected:v1 原行字节
            f2.write(out_line + "\n")
            prov = {k: v for k, v in res.items() if k != "row"}
            prov["v2_line_no"] = i
            prov["v2_line_sha256"] = _sha(out_line)
            prov["tool"] = {
                "name": TOOL_NAME, "config": TOOL_CONFIG,
                "weights": TOOL_WEIGHTS,
                "rdkit": Chem.rdBase.rdkitVersion,
            }
            fp.write(json.dumps(prov, ensure_ascii=False) + "\n")

    from collections import Counter

    status_count = Counter(r["status"] for r in results)
    reject_reasons = Counter(
        r["reason"] for r in results if r["status"] == "rejected")
    rid_count = Counter(r["record_id"] for r in results)
    dup_rids = {k: v for k, v in rid_count.items() if v > 1}
    v2_bytes = V2.stat().st_size
    summary = {
        "v1_file": str(V1.relative_to(REPO)),
        "v2_file": str(V2.relative_to(REPO)),
        "v1_sha256": hashlib.sha256(V1.read_bytes()).hexdigest(),
        "v2_sha256": hashlib.sha256(V2.read_bytes()).hexdigest(),
        "v1_bytes": V1.stat().st_size,
        "v2_bytes": v2_bytes,
        "n_v1_lines": len(lines),
        "n_v2_lines": len(results),
        "line_level_one_to_one": len(lines) == len(results),
        "funnel": {
            "total": len(results),
            "unchanged_v1_decidable": status_count.get("unchanged", 0),
            "remap_candidates_v1_undecidable": status_count.get(
                "remap_candidate", 0),
            "remapped": status_count.get("remapped", 0),
            "rejected": status_count.get("rejected", 0),
            "rejected_reasons": dict(reject_reasons),
        },
        "record_id_note": {
            "n_unique_record_ids": len(rid_count),
            "n_duplicate_record_ids": len(dup_rids),
            "max_rows_per_record_id": max(rid_count.values()),
            "policy": "v1 事实:96 个 record_id 多行(template_id 行级唯一);"
                      "v2 行级一一对应,不删行(任务书 §3.2 '不删除' 红线)",
        },
        "tool": {"name": TOOL_NAME, "config": TOOL_CONFIG,
                 "weights": TOOL_WEIGHTS,
                 "rdkit": Chem.rdBase.rdkitVersion},
        "gold_contact": "none",
        "elapsed_s": round(time.time() - t0, 1),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(summary["funnel"], ensure_ascii=False, indent=2))
    print("v2 sha256:", summary["v2_sha256"])
    print("elapsed:", summary["elapsed_s"], "s")
    del v2_sha


if __name__ == "__main__":
    main()
