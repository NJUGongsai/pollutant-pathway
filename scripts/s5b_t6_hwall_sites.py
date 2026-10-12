#!/usr/bin/env python3
"""s5b_t6_hwall_sites.py — T6 任务 C：hwall 指纹新 strict 的脱氢位点机械统计。

任务书：docs/TASK_S5B_RERANK_PROBE_T6_2026-10-12.md。
题域标签：298 / RHEA 通用酶学 / 已见题。数字一律带此标签，不外推 dev。

识别（程序重现，不依赖已易失的 /tmp/recon_c11_c12 旧脚本）：
  hwall 集 = c12 新 strict（c11 桶≠strict 且 c12 桶=strict）∩
  {c11 同题 payload 原文含 "AtomValenceException" 且 c12 同题不含}。
  对账预期 20 题；不符以本次程序识别为准并如实报告差异。

统计（RDKit 机械 diff，不做化学可行性判断）：
  对每题首个 strict 命中事件：底物 SMILES（batch_manifest entries.
  substrate_smiles）→ 主产物 SMILES（事件 principal_product state）。
  rdFMCS（按元素比原子、按键级比键、环匹配环）建立原子对应后：
  - 变化键：键级改变/断裂/新成，按两端原子元素对分桶（C-O/C-N/C-C/C-S/
    其他）；新原子参与的键按「已匹配元素-新原子元素」计入新成键；
  - 脱氢位点：对应原子 H 数下降（GetTotalNumHs 差），按 C/N/O/S/其他
    分桶；每事件脱氢总数 = 位点降幅之和；H 增位点单独列示；
  - 异常单列（机械判据，非化学判断）：解析/MCS 失败；净 ΔH≥0 但存在
    脱氢位点；碳上得氢；底物骨架重原子未匹配；脱氢在 N/O/S 但键变化
    全不涉及杂原子。

红线：零模型零网络零 LLM；synced/analysis 只读；不触碰判分代码；
不 commit 不 push。

用法：
    python3 scripts/s5b_t6_hwall_sites.py \
        [--batch12 reports/ppv1_s5b/chain12_s5b_298_v4b_20261012] \
        [--batch11 reports/ppv1_s5b/chain11_s5b_298_v4_20261010]

输出（analysis/ 下，t6_ 前缀）：
    t6_hwall_sites.md    人读版（位点分布表 + 异常单列）
    t6_hwall_sites.json  机器数据（逐题 diff 明细、识别对账、provenance）
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import rdFMCS

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_TAG = "298 / RHEA 通用酶学 / 已见题"
EXPECTED_HWALL = 20
CANON_PAIRS = {"C-C", "C-N", "C-O", "C-S"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def metrics_rows(batch: Path) -> dict[str, dict]:
    m = load_json(batch / "metrics.json")
    return {str(r["qid"]): r for r in m.get("per_qid") or []}


def case_map(batch: Path) -> dict[str, dict]:
    out = {}
    for cf in (batch / "synced" / "cases").glob("RXNG_*.json"):
        c = load_json(cf)
        out[str(c["qid"])] = c
    return out


def payload_path(batch: Path, case: dict) -> Path:
    return (batch / "synced" / "runs" / str(case["run_id"]) /
            "native_export" / str(case["export_digest"])[:24] /
            "payload.json")


def payload_text(batch: Path, case: dict) -> str:
    return payload_path(batch, case).read_text(encoding="utf-8")


def payload_json(batch: Path, case: dict) -> dict:
    return load_json(payload_path(batch, case))


def bond_label(a1: Chem.Atom, a2: Chem.Atom) -> str:
    e1, e2 = a1.GetSymbol(), a2.GetSymbol()
    if e1 > e2:
        e1, e2 = e2, e1
    pair = f"{e1}-{e2}"
    return pair if pair in CANON_PAIRS else f"other({pair})"


def elem_bucket(sym: str) -> str:
    return sym if sym in {"C", "N", "O", "S"} else f"other({sym})"


def diff_substrate_product(sub_smi: str, prod_smi: str) -> dict:
    """底物→主产物的机械 diff。返回位点统计；不做化学判断。"""
    out: dict = {"bond_change": Counter(), "bond_broken": Counter(),
                 "bond_formed": Counter(), "dehydro": Counter(),
                 "h_gain": Counter(), "dehydro_total": 0,
                 "h_gain_total": 0, "net_dh": None,
                 "unmatched_sub_heavy": 0, "unmatched_prod_heavy": 0,
                 "unmatched_sub_elements": Counter(),
                 "unmatched_prod_elements": Counter(),
                 "status": "ok"}
    sub = Chem.MolFromSmiles(sub_smi)
    prod = Chem.MolFromSmiles(prod_smi)
    if sub is None or prod is None:
        out["status"] = "parse_failure"
        return out
    try:
        mcs = rdFMCS.FindMCS(
            [sub, prod], atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            ringMatchesRingOnly=True, completeRingsOnly=True,
            matchValences=False, timeout=30)
        query = Chem.MolFromSmarts(mcs.smartsString) \
            if mcs.numAtoms and mcs.smartsString else None
        sub_m = sub.GetSubstructMatches(query, uniquify=False,
                                        maxMatches=200) if query else []
        prod_m = prod.GetSubstructMatches(query, uniquify=False,
                                          maxMatches=200) if query else []
    except Exception as exc:  # noqa: BLE001 — 机械统计兜底披露
        out["status"] = f"mcs_error:{type(exc).__name__}"
        return out
    if not sub_m or not prod_m:
        out["status"] = "mcs_empty_or_no_match"
        return out
    # 对称原子（如多个 O）会有多个匹配解：确定性选「未匹配重原子总数
    # 最少 → 匹配对间键差异最小（断+成+级变）→ 字典序」的 (sub,prod)
    # 配对；全部为机械记账判据，不引入化学判断。
    sub_heavy = [a.GetAtomicNum() > 1 for a in sub.GetAtoms()]
    prod_heavy = [a.GetAtomicNum() > 1 for a in prod.GetAtoms()]

    def qbond_map(mol, match):
        """匹配原子间的键：query 坐标 → 键级。"""
        pos = {a: k for k, a in enumerate(match)}
        res = {}
        for b in mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in pos and j in pos:
                res[frozenset((pos[i], pos[j]))] = b.GetBondType()
        return res

    sm_list = sorted(sub_m[:200])
    pm_list = sorted(prod_m[:200])
    sm_maps = [(sm, qbond_map(sub, sm)) for sm in sm_list]
    pm_maps = [(pm, qbond_map(prod, pm)) for pm in pm_list]

    def diff_score(smap, pmap) -> int:
        n = 0
        for k in set(smap) | set(pmap):
            a, b = smap.get(k), pmap.get(k)
            if a is None or b is None or a != b:
                n += 1
        return n

    best = None
    for sm, smap in sm_maps:
        sset = set(sm)
        s_un = sum(1 for i in range(sub.GetNumAtoms())
                   if i not in sset and sub_heavy[i])
        for pm, pmap in pm_maps:
            pset = set(pm)
            p_un = sum(1 for i in range(prod.GetNumAtoms())
                       if i not in pset and prod_heavy[i])
            key = (s_un + p_un, diff_score(smap, pmap), sm, pm)
            if best is None or key < best[0]:
                best = (key, sm, pm)
    _, sm_best, pm_best = best
    # GetSubstructMatches 与 query 原子序对齐 ⇒ 同下标配对即对应原子
    sub2p = {s: p for s, p in zip(sm_best, pm_best)}
    p2s = {p: s for s, p in sub2p.items()}

    # 剩余配对（确定性记账规则，非化学判断）：MCS 之外的同元素重原子
    # （如羟基 O 转移为羰基 O）按原子序号顺序一配一；配上的原子随后
    # 照常参与键级对照与 H 差统计。元素不同或数量不等时剩余原子保持
    # 未匹配并披露。
    used_p = set(p2s)
    sub_left = [a.GetIdx() for a in sub.GetAtoms()
                if a.GetIdx() not in sub2p and a.GetAtomicNum() > 1]
    prod_left = [a.GetIdx() for a in prod.GetAtoms()
                 if a.GetIdx() not in used_p and a.GetAtomicNum() > 1]
    prod_by_elem: dict[str, list[int]] = {}
    for i in prod_left:
        prod_by_elem.setdefault(prod.GetAtomWithIdx(i).GetSymbol(),
                                []).append(i)
    for i in sub_left:
        cand = prod_by_elem.get(sub.GetAtomWithIdx(i).GetSymbol())
        if cand:
            j = cand.pop(0)
            sub2p[i] = j
            p2s[j] = i

    # 匹配原子间的键：键级对照
    prod_bond_by_pair: dict[frozenset, Chem.BondType] = {}
    for b in prod.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in p2s and j in p2s:
            prod_bond_by_pair[frozenset((p2s[i], p2s[j]))] = b.GetBondType()
    matched_sub_bonds: set[frozenset] = set()
    for b in sub.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i not in sub2p or j not in sub2p:
            continue
        fs = frozenset((i, j))
        matched_sub_bonds.add(fs)
        pbt = prod_bond_by_pair.get(fs)
        label = bond_label(sub.GetAtomWithIdx(min(i, j)),
                           sub.GetAtomWithIdx(max(i, j)))
        if pbt is None:
            out["bond_broken"][label] += 1
        elif pbt != b.GetBondType():
            out["bond_change"][label] += 1
    for fs, pbt in prod_bond_by_pair.items():
        if fs not in matched_sub_bonds:
            i, j = sorted(fs)
            out["bond_formed"][bond_label(sub.GetAtomWithIdx(i),
                                          sub.GetAtomWithIdx(j))] += 1
    # 未匹配端点的产物键（新重原子接入）
    for b in prod.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        mi, mj = p2s.get(i), p2s.get(j)
        if (mi is None) != (mj is None):
            anchored = sub.GetAtomWithIdx(mi if mi is not None else mj)
            fresh = prod.GetAtomWithIdx(i if mi is None else j)
            out["bond_formed"][bond_label(anchored, fresh)] += 1

    # 脱氢 / 得氢位点（对应原子 H 数差）
    for s, p in sub2p.items():
        a, bAt = sub.GetAtomWithIdx(s), prod.GetAtomWithIdx(p)
        nh_sub, nh_prod = a.GetTotalNumHs(), bAt.GetTotalNumHs()
        if nh_prod < nh_sub:
            out["dehydro"][elem_bucket(a.GetSymbol())] += nh_sub - nh_prod
        elif nh_prod > nh_sub:
            out["h_gain"][elem_bucket(a.GetSymbol())] += nh_prod - nh_sub
    out["dehydro_total"] = sum(out["dehydro"].values())
    out["h_gain_total"] = sum(out["h_gain"].values())

    def total_h(mol: Chem.Mol) -> int:
        n = sum(a.GetTotalNumHs() for a in mol.GetAtoms())
        return n + sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 1)

    out["net_dh"] = total_h(prod) - total_h(sub)
    for a in sub.GetAtoms():
        if a.GetIdx() not in sub2p and a.GetAtomicNum() > 1:
            out["unmatched_sub_heavy"] += 1
            out["unmatched_sub_elements"][a.GetSymbol()] += 1
    for a in prod.GetAtoms():
        if a.GetIdx() not in p2s and a.GetAtomicNum() > 1:
            out["unmatched_prod_heavy"] += 1
            out["unmatched_prod_elements"][a.GetSymbol()] += 1
    return out


def anomalies_of(d: dict) -> list[str]:
    """机械异常判据（披露用，非化学判断）。"""
    flags = []
    if d["status"] != "ok":
        return [f"stat_failure:{d['status']}"]
    if d["net_dh"] is not None and d["net_dh"] >= 0 and d["dehydro_total"]:
        flags.append("net_dh_nonneg_with_dehydro_sites")
    if d["h_gain"].get("C", 0):
        flags.append("h_gain_on_carbon")
    all_bonds = {**d["bond_change"], **d["bond_formed"],
                 **d["bond_broken"]}
    het_bonds = sum(v for k, v in all_bonds.items() if k != "C-C")
    if sum(d["bond_broken"].values()) and sum(d["bond_formed"].values()):
        flags.append("matched_pair_connectivity_differs")
    het_dehydro = sum(v for k, v in d["dehydro"].items()
                      if k in ("N", "O", "S"))
    if het_dehydro and not het_bonds:
        flags.append("het_dehydro_without_het_bond_change")
    if d["unmatched_sub_heavy"]:
        flags.append("substrate_heavy_atom_unmatched")
    return flags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch12", type=Path,
                    default=REPO_ROOT / "reports/ppv1_s5b/"
                            "chain12_s5b_298_v4b_20261012")
    ap.add_argument("--batch11", type=Path,
                    default=REPO_ROOT / "reports/ppv1_s5b/"
                            "chain11_s5b_298_v4_20261010")
    args = ap.parse_args()
    RDLogger.DisableLog("rdApp.*")
    b12, b11 = args.batch12, args.batch11
    out_dir = b12 / "analysis"

    m12 = metrics_rows(b12)
    m11 = metrics_rows(b11)
    cases12 = case_map(b12)
    cases11 = case_map(b11)
    manifest = load_json(b12 / "synced/batch_manifest.json")
    substrate = {str(e["qid"]): str(e.get("substrate_smiles") or "")
                 for e in manifest.get("entries") or []}
    rd = load_json(b12 / "analysis/rescore_detail.json")
    pq = rd["per_qid"]

    def status_of(row):
        return str((row.get("main") or {}).get("match_status"))

    new_strict35 = sorted(
        q for q in m12
        if status_of(m12[q]) == "matched_strict"
        and status_of(m11[q]) != "matched_strict")

    hwall, val_note = [], {"c11_payload_missing": [], "not_hwall": []}
    for q in new_strict35:
        if q not in cases11:
            val_note["c11_payload_missing"].append(q)
            continue
        try:
            c11_txt = payload_text(b11, cases11[q])
        except OSError:
            val_note["c11_payload_missing"].append(q)
            continue
        c12_txt = payload_text(b12, cases12[q]) if q in cases12 else ""
        c11_v = "AtomValenceException" in c11_txt
        c12_v = "AtomValenceException" in (c12_txt or "")
        if c11_v and not c12_v:
            hwall.append(q)
        else:
            val_note["not_hwall"].append(
                {"qid": q, "c11_valence": c11_v, "c12_valence": c12_v})
    print(f"[HWALL] 新 strict {len(new_strict35)}; hwall 识别 "
          f"{len(hwall)} 题（对账预期 {EXPECTED_HWALL}）")
    if len(hwall) != EXPECTED_HWALL:
        print(f"[DIFF] 与对账报告 20 题不符，以本次程序识别为准；"
              f"未入集的新 strict（c11/c12 valence 态）: "
              f"{json.dumps(val_note['not_hwall'], ensure_ascii=False)}")

    rows = []
    for q in hwall:
        d = pq[q]
        payload = payload_json(b12, cases12[q])
        state_smiles = {
            str(s.get("state_id")): str(
                (s.get("payload") or {}).get("smiles_isomeric")
                or (s.get("payload") or {}).get("cn_identity") or "")
            for s in payload.get("states") or []}
        hit = next((c for c in sorted(d["candidate_events"],
                                      key=lambda c: c["position"])
                    if c["strict_hit"]), None)
        if hit is None:
            rows.append({"qid": q, "status": "no_strict_hit_in_rescore"})
            continue
        ev = next((e for e in payload.get("events") or []
                   if str(e.get("event_id")) == hit["event_id"]), None)
        body = (ev or {}).get("payload") or {}
        if isinstance(body, str):
            body = json.loads(body)
        parts = body.get("participants") or []
        products = [p for p in parts if str(p.get("side")) == "product"]
        principal = [p for p in products
                     if str(p.get("role")) == "principal_product"]
        use = principal or products
        prod_smi = ";".join(sorted(
            state_smiles.get(str(p.get("state_ref")), "") for p in use))
        sub_smi = substrate.get(q, "")
        diff = diff_substrate_product(sub_smi, prod_smi)
        rows.append({
            "qid": q,
            "c12_rank": (m12[q]["main"] or {}).get("rank"),
            "hit_position": hit["position"],
            "n_strict_hit_events": sum(
                1 for c in d["candidate_events"] if c["strict_hit"]),
            "event_id": hit["event_id"],
            "substrate_smiles": sub_smi,
            "principal_product_smiles": prod_smi,
            "n_principal_product_states": len(use),
            "diff": {k: (dict(v) if isinstance(v, Counter) else v)
                     for k, v in diff.items()},
            "anomalies": anomalies_of(diff),
        })
        r = rows[-1]
        print(f"[SITE] {q[:20]}… rank={r['c12_rank']} "
              f"脱氢总数={r['diff'].get('dehydro_total')} "
              f"位点={json.dumps(r['diff'].get('dehydro', {}))} "
              f"键变={json.dumps(r['diff'].get('bond_change', {}))} "
              f"异常={r['anomalies']}")

    ok_rows = [r for r in rows if (r.get("diff") or {}).get("status") == "ok"]
    dehydro_elems, bond_change, bond_formed, bond_broken = \
        Counter(), Counter(), Counter(), Counter()
    dehydro_total_all = 0
    for r in ok_rows:
        dehydro_elems.update(r["diff"]["dehydro"])
        bond_change.update(r["diff"]["bond_change"])
        bond_formed.update(r["diff"]["bond_formed"])
        bond_broken.update(r["diff"]["bond_broken"])
        dehydro_total_all += r["diff"]["dehydro_total"]
    anomaly_rows = [r for r in rows if r.get("anomalies")]

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True).stdout.strip()
    result = {
        "provenance": {
            "domain_tag": DOMAIN_TAG,
            "local_git_head": head,
            "batch12": str(b12), "batch11": str(b11),
            "identification": (
                "hwall = c12 新 strict ∩ {c11 payload 含 "
                "AtomValenceException 且 c12 不含}；程序重现，未依赖 "
                "/tmp/recon_c11_c12 旧脚本"),
            "n_new_strict": len(new_strict35),
            "n_hwall": len(hwall),
            "expected_hwall": EXPECTED_HWALL,
            "identification_matches_recon": len(hwall) == EXPECTED_HWALL,
            "identification_note": val_note,
            "llm_calls": 0, "network_calls": 0,
            "mechanics": ("rdFMCS(CompareElements,CompareOrder,"
                          "ringMatchesRingOnly,completeRingsOnly) 原子对应；"
                          "对称解取未匹配重原子最少、字典序决胜的配对；"
                          "MCS 外同元素剩余重原子按序号顺序确定性一配一"
                          "（记账规则，非化学判断）后照常做键级对照与 "
                          "GetTotalNumHs 差；仅机械统计，不做化学可行性"
                          "判断"),
        },
        "hwall_qids": hwall,
        "rows": rows,
        "aggregate": {
            "dehydro_by_element": dict(dehydro_elems),
            "bond_change_by_pair": dict(bond_change),
            "bond_formed_by_pair": dict(bond_formed),
            "bond_broken_by_pair": dict(bond_broken),
            "dehydro_total_sum": dehydro_total_all,
            "n_events_ok": len(ok_rows),
            "n_rows_with_anomaly": len(anomaly_rows),
        },
    }
    (out_dir / "t6_hwall_sites.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")

    md = [f"# T6 任务 C：hwall 指纹新 strict 脱氢位点机械统计"
          f"（题域 {DOMAIN_TAG}）\n"]
    md.append(f"- 识别：{len(new_strict35)} 道新 strict 中程序识别 hwall "
              f"{len(hwall)} 题（对账预期 20，"
              f"{'一致' if len(hwall) == EXPECTED_HWALL else '不一致——以本次程序识别为准'}）；"
              f"识别法 = c11 payload 含 AtomValenceException 且 c12 消失"
              f"（未依赖 /tmp 旧脚本）")
    md.append("- 统计面：每题首个 strict 命中事件的底物 → 主产物"
              "（principal_product），rdFMCS 原子对应后做键/H 机械 diff；"
              "仅结构事实，化学解读归 mimo 下轮\n")
    md.append("## 位点分布聚合\n")
    md.append(f"- 脱氢位点元素分布：{dict(sorted(dehydro_elems.items()))}")
    md.append(f"- 每事件脱氢总数合计：{dehydro_total_all}"
              f"（{len(ok_rows)} 个可统计事件）")
    md.append(f"- 变化键（键级改变，按两端元素）：{dict(bond_change)}")
    md.append(f"- 新成键（含新重原子接入）：{dict(bond_formed)}")
    md.append(f"- 断键：{dict(bond_broken)}\n")
    md.append("## 逐题表\n")
    md.append("| qid | rank | 脱氢总数 | 脱氢位点(元素) | 变化键 | 得氢位点 |"
              " 异常 |")
    md.append("|---|---:|---:|---|---|---|---|")
    for r in rows:
        df = r.get("diff") or {}
        md.append(
            f"| {r['qid'][:20]}… | {r.get('c12_rank')} "
            f"| {df.get('dehydro_total','-')} "
            f"| {json.dumps(df.get('dehydro',{}), ensure_ascii=False)} "
            f"| {json.dumps(df.get('bond_change',{}), ensure_ascii=False)} "
            f"| {json.dumps(df.get('h_gain',{}), ensure_ascii=False)} "
            f"| {','.join(r.get('anomalies') or []) or '-'} |")
    md.append("\n## 异常单列（机械判据，非化学判断）\n")
    if anomaly_rows:
        for r in anomaly_rows:
            df = r.get("diff") or {}
            md.append(
                f"- {r['qid'][:24]}… anomalies="
                f"{','.join(r.get('anomalies') or [])}"
                f"；net ΔH={df.get('net_dh')}；未匹配底物重原子="
                f"{df.get('unmatched_sub_heavy')} "
                f"{json.dumps(df.get('unmatched_sub_elements',{}), ensure_ascii=False)}")
    else:
        md.append("- 无")
    md.append("\n> 边界：本表只产出结构事实（键类型/脱氢元素/数量），"
              "不做氧化还原模式判断或可行性门；化学解读由 mimo 下轮评审。")
    (out_dir / "t6_hwall_sites.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")
    print(f"[OUT] {out_dir}/t6_hwall_sites.md t6_hwall_sites.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
