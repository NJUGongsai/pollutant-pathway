#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pool_coverage_eval.py — 候选池覆盖率离线评测脚本（零调用，零费用）。

输入：
  --batch-root: 已 build 的批根（含 batch_manifest.json, run_inputs/, reference_graphs/）
  --questions: 题卷 questions.jsonl 路径（只读调参集题目的 substrate_smiles 与源记录 ID 元数据；
               金标产物字段只从 reference_graphs 在确定性身份判定函数内部消费）
  --split-dir: 拆分目录（含 dev_qids.txt 与 holdout_qids.txt）
  --config-name: 配置标识（如 S0, S0_prime, S1a, S2r 等）
  --domain: dev-298 或 biosysmodb121
  --out-dir: 聚合指标输出目录（reports/POOL_COVERAGE_2026-11-09/，零 qid、零 SMILES）
  --mr-dir: 逐题明细私有目录（reports/manual_review/pool_coverage_2026-11-09/，gitignored）

默认模式：
  --subset dev_tuning（严禁读取或评测 holdout 题）
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from statistics import median

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

from pathway_v43.domain.identity import normalize_charge_smiles
from pathway_v43.pollutant.chemstate import strict_identity_of


@lru_cache(maxsize=None)
def k_strict(s: str | None) -> str | None:
    if not s:
        return None
    try:
        return strict_identity_of(str(s))
    except Exception:
        return None


@lru_cache(maxsize=None)
def k_charge(s: str | None) -> str | None:
    if not s:
        return None
    try:
        n = normalize_charge_smiles(str(s))
        return k_strict(n) if n else None
    except Exception:
        return None


@lru_cache(maxsize=None)
def unmap_strict_set(mapped_smiles: str) -> frozenset[str]:
    """去除原子映射编号后，返回整串及各组分的 strict_identity 集合。"""
    if not mapped_smiles:
        return frozenset()
    try:
        m = Chem.MolFromSmiles(str(mapped_smiles))
        if m is None:
            return frozenset()
        for a in m.GetAtoms():
            a.SetAtomMapNum(0)
        unmapped = Chem.MolToSmiles(m)
        out: set[str] = set()
        whole = k_strict(unmapped)
        if whole:
            out.add(whole)
        for comp in unmapped.split("."):
            if comp:
                st = k_strict(comp)
                if st:
                    out.add(st)
        return frozenset(out)
    except Exception:
        return frozenset()


def covers(
    gold: list[str], products: list[tuple[str, str]], key, role_aware: bool
) -> bool:
    """P subset of T_E under key; role_aware keeps only principal_product."""
    if not gold:
        return False
    g = {key(x) for x in gold}
    if None in g:
        return False
    t = {key(s) for s, role in products if (not role_aware) or role == "principal_product"}
    t.discard(None)
    return g <= t


def get_channel(key: str, chan_map: dict[str, str] | None = None) -> str:
    k = str(key)
    if k.startswith(("tpl-uspto:", "uspto-")):
        return "uspto"
    if chan_map and k in chan_map:
        ch = chan_map[k]
        return "retrorules" if ch == "retro" else ch
    if k.startswith("rec-corpus:") or k.startswith("rec-rhea:") or "@L" in k:
        return "corpus"
    if k.startswith("rec-"):
        return "recorded"
    if k.startswith("tpl-"):
        return "analog"
    if k.startswith(("retro-", "rr-", "rtpl-", "rrtpl-")):
        return "retrorules"
    return "other"


def load_list(path: Path | str) -> list[str]:
    return [
        x.strip()
        for x in Path(path).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def load_template_raw_pairs(assets_root: Path) -> dict[str, tuple[str, str]]:
    """读取 analog 模板的原始 (mapped_lhs, mapped_rhs) 映射对（按需惰性解析 RDKit）。"""
    raw_by_tpl: dict[str, tuple[str, str]] = {}
    tpl_paths = [
        assets_root / "analog" / "corpus_templates_v2.jsonl",
        assets_root / "analog" / "corpus_templates_v1.jsonl",
    ]
    for p in tpl_paths:
        if not p.is_file():
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                tid = str(row.get("template_id") or row.get("rule_id") or "")
                rec_id = str(row.get("record_id") or "")
                pair = (
                    str(row.get("mapped_lhs") or ""),
                    str(row.get("mapped_rhs") or ""),
                )
                if tid:
                    raw_by_tpl[tid] = pair
                    raw_by_tpl[f"tpl-{tid}"] = pair
                if rec_id:
                    raw_by_tpl[rec_id] = pair
                    raw_by_tpl[f"tpl-{rec_id}"] = pair
    return raw_by_tpl


def load_retro_self_record_indices(
    assets_root: Path,
    q_sub_gold_by_qid: dict[str, tuple[str | None, set[str]]],
) -> tuple[dict[str, set[str]], dict[str, list[tuple[str, str]]]]:
    """为调参集题目加载源反应 ID 集合（含 corpus_v1 RHEA 四向 ID）及 RetroRules 父反应最大半径供体映射对。"""
    self_ids_by_qid: dict[str, set[str]] = {qid: set() for qid in q_sub_gold_by_qid}
    qids_by_sub_strict: dict[str, list[str]] = {}
    for qid, (sub_st, _g_sts) in q_sub_gold_by_qid.items():
        if sub_st:
            qids_by_sub_strict.setdefault(sub_st, []).append(qid)

    corpus_v1 = assets_root / "v3_reactions" / "corpus_env" / "corpus_v1.jsonl"
    if corpus_v1.is_file() and qids_by_sub_strict:
        with open(corpus_v1, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                donors = [r.get("donor_A_smiles")] + (r.get("donor_components") or [])
                matched_subs: set[str] = set()
                for d in donors:
                    if d:
                        st = k_strict(d)
                        if st and st in qids_by_sub_strict:
                            matched_subs.add(st)
                if not matched_subs:
                    continue
                sid = str(r.get("source_id") or "")
                rid = str(r.get("record_id") or "")
                if r.get("parse_note") == "envipath-educt" and sid:
                    for ds in matched_subs:
                        for qid in qids_by_sub_strict[ds]:
                            self_ids_by_qid[qid].add(sid)
                    continue
                prods = [r.get("product_B_smiles")] + (r.get("product_components") or [])
                p_stricts = {k_strict(p) for p in prods if p}
                p_stricts.discard(None)
                for ds in matched_subs:
                    for qid in qids_by_sub_strict[ds]:
                        _, g_sts = q_sub_gold_by_qid[qid]
                        if g_sts and (g_sts <= p_stricts):
                            if sid:
                                self_ids_by_qid[qid].add(sid)
                                self_ids_by_qid[qid].add(sid.upper())
                            if rid:
                                self_ids_by_qid[qid].add(rid)
                            if r.get("source_type") == "rhea" and r.get("master_id") is not None:
                                m_id = int(r["master_id"])
                                for offset in range(4):
                                    self_ids_by_qid[qid].add(f"RHEA:{m_id + offset}")

    rxn_max_pairs: dict[str, list[tuple[str, str]]] = {}
    rxn_max_rad: dict[str, int] = {}
    derived_dir = assets_root / "retrorules" / "derived"
    for meta_name in ("rhea_retro_index.meta.json", "mnx_retro_index.meta.json"):
        mp = derived_dir / meta_name
        if not mp.is_file():
            continue
        meta_obj = json.loads(mp.read_text(encoding="utf-8"))
        for tpl in meta_obj.get("templates") or []:
            rmax = int(tpl.get("radius_max") or 0)
            if rmax < 8:
                continue
            lhs_m = str(tpl.get("lhs_mapped_smiles") or "")
            rhs_m = str(tpl.get("rhs_mapped_smiles") or "")
            if not lhs_m or not rhs_m:
                continue
            pair = (lhs_m, rhs_m)
            rxns = list(tpl.get("reactions") or []) + list(tpl.get("rhea_reactions") or [])
            for rxn_id in rxns:
                prev = rxn_max_rad.get(rxn_id, -1)
                if rmax > prev:
                    rxn_max_rad[rxn_id] = rmax
                    rxn_max_pairs[rxn_id] = [pair]
                elif rmax == prev:
                    lst = rxn_max_pairs.setdefault(rxn_id, [])
                    if len(lst) < 4 and pair not in lst:
                        lst.append(pair)

    return self_ids_by_qid, rxn_max_pairs


def _is_source_key_self_record(
    source_key: str,
    chan: str,
    sub_strict: str | None,
    gold_stricts: set[str],
    q_rxn_id: str,
    raw_by_tpl: dict[str, tuple[str, str]] | None,
    *,
    substrate_smiles: str = "",
    gold_smiles_list: list[str] | None = None,
    q_self_source_ids: set[str] | None = None,
    retro_info: dict | None = None,
    rxn_max_pairs: dict[str, list[tuple[str, str]]] | None = None,
) -> bool:
    """判定单条候选来源键是否属于该题自身的来源记录（任务书 §3 指标 4）：
    来源记录 ID 一致，或「底物 + 主产物」严格身份同时一致。
    """
    if q_rxn_id and q_rxn_id in source_key:
        return True
    if chan in ("recorded", "corpus"):
        # recorded 与 corpus 均由题面底物精确检索所得，当其命中金标时底物+主产物同时一致
        return True
    if chan == "analog" and raw_by_tpl:
        pair = raw_by_tpl.get(source_key) or raw_by_tpl.get(source_key[4:])
        if pair and sub_strict and gold_stricts:
            lhs_stricts = unmap_strict_set(pair[0])
            rhs_stricts = unmap_strict_set(pair[1])
            if sub_strict in lhs_stricts and gold_stricts <= rhs_stricts:
                return True
    if chan == "retrorules":
        if q_rxn_id and q_rxn_id in source_key:
            return True
        all_q_ids = set(q_self_source_ids or set())
        if q_rxn_id:
            all_q_ids.add(q_rxn_id)
        if retro_info is not None:
            from pathway_v43.services.retro_source import check_retro_self_record

            res = check_retro_self_record(
                retro_info,
                question_source_ids=all_q_ids,
                substrate_smiles=substrate_smiles,
                gold_principal_smiles=gold_smiles_list or [],
            )
            if res.get("is_self_record"):
                return True
            parent_ids = (
                retro_info.get("parent_reaction_ids")
                or (retro_info.get("compile") or {}).get("parent_reaction_ids")
                or (retro_info.get("retro_meta") or {}).get("parent_reaction_ids")
                or []
            )
            if rxn_max_pairs and sub_strict and gold_stricts:
                for rxn_id in parent_ids:
                    for max_lhs, max_rhs in rxn_max_pairs.get(str(rxn_id), ()):
                        if (
                            sub_strict in unmap_strict_set(max_lhs)
                            and gold_stricts <= unmap_strict_set(max_rhs)
                        ):
                            return True
    return False


def evaluate_batch(
    batch_root: Path,
    split_dir: Path,
    questions_path: Path | None,
    subset: str = "dev_tuning",
    unlock_token_file: str = "",
    expected_token_sha256: str = "",
    config_name: str = "S0",
    domain: str = "dev-298",
    raw_by_tpl: dict[str, tuple[str, str]] | None = None,
    assets_root: Path | None = None,
) -> tuple[dict, list[dict]]:
    manifest_path = batch_root / "batch_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing batch_manifest.json in {batch_root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    dev_qids = set(load_list(split_dir / "dev_qids.txt"))
    hold_qids = set(load_list(split_dir / "holdout_qids.txt"))

    if subset != "dev_tuning":
        unlocked = False
        if unlock_token_file and expected_token_sha256:
            got = hashlib.sha256(Path(unlock_token_file).read_bytes()).hexdigest()
            if got == expected_token_sha256:
                unlocked = True
        if not unlocked:
            raise PermissionError(
                f"Refused subset={subset!r}: holdout items are locked; only 'dev_tuning' is allowed."
            )
        target_qids = (dev_qids | hold_qids) if subset == "full" else hold_qids
    else:
        target_qids = dev_qids

    # 只读取 target_qids 内的输入底物与源记录 ID（严禁读取 holdout 题，也不在此处读取金标产物）
    source_record_by_qid: dict[str, dict] = {}
    if questions_path and questions_path.is_file():
        with open(questions_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                q = json.loads(line)
                qid = str(q.get("qid") or "")
                if qid not in target_qids:
                    continue
                source_record_by_qid[qid] = {
                    "qid": qid,
                    "substrate_smiles": str(q.get("substrate_smiles") or ""),
                    "reaction_id": str(q.get("_reaction_id") or q.get("reaction_id") or ""),
                    "pathway": str(q.get("_pathway") or ""),
                }

    rows: list[dict] = []
    compile_failures = Counter()
    total_compile_rejected = 0
    total_pool_truncated = 0
    questions_with_truncation = 0
    questions_with_retro_slot_top8 = 0
    questions_with_retro_slot_all = 0
    questions_with_retro_compiled_or_merged = 0
    build_times: list[float] = []

    has_retro_batch = any(
        bool((e.get("pool_diagnostics") or {}).get("retro_diagnostics"))
        for e in manifest["entries"]
        if str(e.get("qid")) in target_qids
    )
    self_ids_by_qid: dict[str, set[str]] = {}
    rxn_max_pairs: dict[str, list[tuple[str, str]]] = {}
    if has_retro_batch and assets_root is not None and assets_root.is_dir():
        q_sub_gold_by_qid: dict[str, tuple[str | None, set[str]]] = {}
        for e in manifest["entries"]:
            qid = str(e["qid"])
            if qid not in target_qids:
                continue
            sub_st = k_strict(str(e["substrate_smiles"]))
            graph = json.loads((batch_root / e["graph_rel"]).read_text(encoding="utf-8"))
            gold_s = {
                k_strict(str(n.get("structure_smiles") or ""))
                for n in (graph.get("nodes") or [])
                if n.get("role") == "principal_product"
            }
            gold_s.discard(None)
            q_sub_gold_by_qid[qid] = (sub_st, gold_s)
        self_ids_by_qid, rxn_max_pairs = load_retro_self_record_indices(
            assets_root, q_sub_gold_by_qid
        )

    for e in manifest["entries"]:
        qid = str(e["qid"])
        if qid not in target_qids:
            continue

        substrate = str(e["substrate_smiles"])
        sub_strict = k_strict(substrate)

        if e.get("build_seconds") is not None:
            build_times.append(float(e["build_seconds"]))

        # 读取参考图（仅在确定性身份比较中使用）
        graph_path = batch_root / e["graph_rel"]
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        gold = sorted(
            {
                str(n.get("structure_smiles") or "")
                for n in graph.get("nodes") or []
                if n.get("role") == "principal_product"
            }
            - {""}
        )
        gold_stricts = {k_strict(g) for g in gold if k_strict(g)}

        # 读取 run_inputs（截断后实际候选池）
        run_input_path = batch_root / e["run_input_rel"]
        run_input = json.loads(run_input_path.read_text(encoding="utf-8"))
        pools = (run_input.get("plan") or {}).get("pools") or {}
        pool = pools.get(substrate)
        if pool is None and len(pools) == 1:
            pool = next(iter(pools.values()))
        pool = [s for s in (pool or []) if isinstance(s, dict)]
        pool_size = len(pool)

        # 若 manifest entry 带有截断前完整候选摘要，则用于 GIP@16/32/all 与 9+ 名次评估
        untruncated_cands = e.get("untruncated_candidates")
        if isinstance(untruncated_cands, list) and len(untruncated_cands) >= pool_size:
            eval_cands = untruncated_cands
        else:
            eval_cands = pool
        untruncated_pool_size = len(eval_cands)

        # 诊断信息：构建通道映射、统计编译拒绝与池截断
        diag = e.get("pool_diagnostics") or {}
        chan_map: dict[str, str] = {}
        q_truncated = 0
        for cand_diag in diag.get("candidates") or []:
            rk = str(cand_diag.get("record_key") or "")
            ch = str(cand_diag.get("channel") or "")
            if rk and ch:
                chan_map[rk] = ch
                chan_map[f"rec-{rk}"] = ch
            outcome = cand_diag.get("outcome")
            if outcome == "compile_rejected":
                reason = str(cand_diag.get("reason") or "unknown")
                compile_failures[reason] += 1
                total_compile_rejected += 1
            elif outcome == "pool_truncated":
                q_truncated += 1
                total_pool_truncated += 1
        if q_truncated > 0 or untruncated_pool_size > pool_size:
            questions_with_truncation += 1

        q_meta = source_record_by_qid.get(qid, {})
        q_rxn_id = str(q_meta.get("reaction_id") or "")
        if not q_rxn_id:
            m_rxn = re.search(r"__(BSY-[A-Za-z0-9_]+)", qid)
            if m_rxn:
                q_rxn_id = m_rxn.group(1)
        q_self_ids = set(self_ids_by_qid.get(qid, set()))
        if q_rxn_id:
            q_self_ids.add(q_rxn_id)

        # 构建 RetroRules 候选键 -> 元数据映射（支持主键及被合并至其他槽位的 merged_source_keys）
        retro_info_by_key: dict[str, dict] = {}
        r_diag = diag.get("retro_diagnostics") or {}
        if int(r_diag.get("retro_n_compiled") or 0) > 0:
            questions_with_retro_compiled_or_merged += 1
        for rc in r_diag.get("retro_candidates") or []:
            sk = str(rc.get("spec_key") or "")
            if sk:
                retro_info_by_key[sk] = rc
        for p_spec in pool:
            pk = str(p_spec.get("key") or "")
            if pk and (p_spec.get("channel") in ("retro", "retrorules") or "retro_meta" in p_spec):
                retro_info_by_key.setdefault(pk, p_spec)
            m_retro = (p_spec.get("compile") or {}).get("merged_retro_sources") or {}
            for mk_r, mr_info in m_retro.items():
                retro_info_by_key.setdefault(str(mk_r), mr_info)
        for u_spec in eval_cands:
            uk = str(u_spec.get("key") or "")
            if uk and (
                u_spec.get("channel") in ("retro", "retrorules")
                or "parent_reaction_ids" in (u_spec.get("compile") or {})
            ):
                retro_info_by_key.setdefault(uk, u_spec)
            m_retro = (u_spec.get("compile") or {}).get("merged_retro_sources") or {}
            for mk_r, mr_info in m_retro.items():
                retro_info_by_key.setdefault(str(mk_r), mr_info)

        # 逐候选评测（在 eval_cands 上评测全部名次）
        cand_hits_rb: list[bool] = []
        cand_hits_ra: list[bool] = []
        cand_is_primary_self: list[bool] = []
        cand_is_all_self: list[bool] = []
        cand_primary_channels: list[str] = []
        cand_all_channels: list[set[str]] = []

        for i, cand in enumerate(eval_cands):
            pp = [(cand.get("product_smiles"), "principal_product")] + [
                (c, "coproduct") for c in (cand.get("coproducts") or [])
            ]
            hit_rb = covers(gold, pp, k_strict, False)
            hit_ra = covers(gold, pp, k_strict, True)
            cand_hits_rb.append(hit_rb)
            cand_hits_ra.append(hit_ra)

            ckey = str(cand.get("key") or "")
            p_chan = get_channel(ckey, chan_map)
            cand_primary_channels.append(p_chan)

            merged_keys = list(
                cand.get("merged_source_keys")
                or (cand.get("compile") or {}).get("merged_source_keys")
                or []
            )
            all_keys = [ckey] + [str(mk) for mk in merged_keys if mk]
            all_chans = {get_channel(k, chan_map) for k in all_keys}
            cand_all_channels.append(all_chans)

            prim_self = False
            all_self = False
            if hit_rb:
                tref = str(cand.get("transformation_ref") or ckey)
                prim_retro_info = retro_info_by_key.get(ckey) or (
                    cand if p_chan == "retrorules" else None
                )
                prim_self = _is_source_key_self_record(
                    ckey,
                    p_chan,
                    sub_strict,
                    gold_stricts,
                    q_rxn_id,
                    raw_by_tpl,
                    substrate_smiles=substrate,
                    gold_smiles_list=gold,
                    q_self_source_ids=q_self_ids,
                    retro_info=prim_retro_info,
                    rxn_max_pairs=rxn_max_pairs,
                ) or (
                    tref != ckey
                    and _is_source_key_self_record(
                        tref,
                        p_chan,
                        sub_strict,
                        gold_stricts,
                        q_rxn_id,
                        raw_by_tpl,
                        substrate_smiles=substrate,
                        gold_smiles_list=gold,
                        q_self_source_ids=q_self_ids,
                        retro_info=prim_retro_info,
                        rxn_max_pairs=rxn_max_pairs,
                    )
                )
                key_self_flags = [
                    _is_source_key_self_record(
                        k,
                        get_channel(k, chan_map),
                        sub_strict,
                        gold_stricts,
                        q_rxn_id,
                        raw_by_tpl,
                        substrate_smiles=substrate,
                        gold_smiles_list=gold,
                        q_self_source_ids=q_self_ids,
                        retro_info=retro_info_by_key.get(k),
                        rxn_max_pairs=rxn_max_pairs,
                    )
                    for k in all_keys
                ]
                all_self = all(key_self_flags)
            cand_is_primary_self.append(prim_self)
            cand_is_all_self.append(all_self)

        if any(ch == "retrorules" for ch in cand_primary_channels[:8]):
            questions_with_retro_slot_top8 += 1
        if any(ch == "retrorules" for ch in cand_primary_channels):
            questions_with_retro_slot_all += 1

        first_rank_rb = None
        for i, h in enumerate(cand_hits_rb, 1):
            if h:
                first_rank_rb = i
                break

        first_rank_ra = None
        for i, h in enumerate(cand_hits_ra, 1):
            if h:
                first_rank_ra = i
                break

        def hit_at_k(
            k: int,
            role_aware: bool = False,
            ex_self_mode: str = "none",
        ) -> bool:
            hits = cand_hits_ra if role_aware else cand_hits_rb
            for i, h in enumerate(hits):
                if i >= k:
                    break
                if not h:
                    continue
                if ex_self_mode == "primary" and cand_is_primary_self[i]:
                    continue
                if ex_self_mode == "all_sources" and cand_is_all_self[i]:
                    continue
                return True
            return False

        gip_8 = hit_at_k(8, False, "none")
        gip_16 = hit_at_k(16, False, "none")
        gip_32 = hit_at_k(32, False, "none")
        gip_all = any(cand_hits_rb)
        gip_at_pool = hit_at_k(pool_size, False, "none")

        # 主口径剔除自记录：按候选槽主来源键判定（同时保留合并来源存活口径供对照）
        gip_8_ex_self = hit_at_k(8, False, "primary")
        gip_16_ex_self = hit_at_k(16, False, "primary")
        gip_32_ex_self = hit_at_k(32, False, "primary")
        gip_all_ex_self = hit_at_k(len(eval_cands), False, "primary")

        gip_8_ex_self_merged = hit_at_k(8, False, "all_sources")
        gip_16_ex_self_merged = hit_at_k(16, False, "all_sources")
        gip_32_ex_self_merged = hit_at_k(32, False, "all_sources")
        gip_all_ex_self_merged = hit_at_k(len(eval_cands), False, "all_sources")

        gip_ra_8 = hit_at_k(8, True, "none")
        gip_ra_all = any(cand_hits_ra)

        if first_rank_rb is None:
            rank_bucket = "none"
        elif first_rank_rb == 1:
            rank_bucket = "1"
        elif first_rank_rb <= 3:
            rank_bucket = "2-3"
        elif first_rank_rb <= 8:
            rank_bucket = "4-8"
        else:
            rank_bucket = "9+"

        hit_channels_top8_prim = {
            cand_primary_channels[i] for i, h in enumerate(cand_hits_rb[:8]) if h
        }
        hit_channels_top8_merged: set[str] = set()
        for i, h in enumerate(cand_hits_rb[:8]):
            if h:
                hit_channels_top8_merged |= cand_all_channels[i]

        sole_channel_prim = (
            next(iter(hit_channels_top8_prim))
            if len(hit_channels_top8_prim) == 1
            else None
        )
        sole_channel_merged = (
            next(iter(hit_channels_top8_merged))
            if len(hit_channels_top8_merged) == 1
            else None
        )

        is_self_gip8 = any(
            s for h, s in zip(cand_hits_rb[:8], cand_is_primary_self[:8]) if h
        )
        is_self_only_gip8 = gip_8 and (not gip_8_ex_self)

        row = {
            "qid": qid,
            "pool_size": pool_size,
            "untruncated_pool_size": untruncated_pool_size,
            "empty_pool": pool_size == 0,
            "gip_rb_8": gip_8,
            "gip_rb_16": gip_16,
            "gip_rb_32": gip_32,
            "gip_rb_all": gip_all,
            "gip_rb_at_pool": gip_at_pool,
            "gip_ra_8": gip_ra_8,
            "gip_ra_all": gip_ra_all,
            "first_rank_rb": first_rank_rb,
            "rank_bucket": rank_bucket,
            "is_self_record_gip8": is_self_gip8,
            "is_self_only_gip8": is_self_only_gip8,
            "gip_rb_8_ex_self": gip_8_ex_self,
            "gip_rb_16_ex_self": gip_16_ex_self,
            "gip_rb_32_ex_self": gip_32_ex_self,
            "gip_rb_all_ex_self": gip_all_ex_self,
            "gip_rb_8_ex_self_merged": gip_8_ex_self_merged,
            "gip_rb_16_ex_self_merged": gip_16_ex_self_merged,
            "gip_rb_32_ex_self_merged": gip_32_ex_self_merged,
            "gip_rb_all_ex_self_merged": gip_all_ex_self_merged,
            "channels_hit_8": sorted(hit_channels_top8_prim),
            "channels_hit_8_with_merged": sorted(hit_channels_top8_merged),
            "sole_channel_8": sole_channel_prim,
            "sole_channel_8_with_merged": sole_channel_merged,
            "wrong_pool_8": (pool_size > 0 and not gip_8),
            "wrong_pool_at_pool": (pool_size > 0 and not gip_at_pool),
        }
        rows.append(row)

    denom = len(rows)
    if denom == 0:
        raise ValueError("No questions found for evaluation")

    n_gip_8 = sum(1 for r in rows if r["gip_rb_8"])
    n_gip_16 = sum(1 for r in rows if r["gip_rb_16"])
    n_gip_32 = sum(1 for r in rows if r["gip_rb_32"])
    n_gip_all = sum(1 for r in rows if r["gip_rb_all"])
    n_gip_ra_8 = sum(1 for r in rows if r["gip_ra_8"])

    n_gip_8_ex_self = sum(1 for r in rows if r["gip_rb_8_ex_self"])
    n_gip_16_ex_self = sum(1 for r in rows if r["gip_rb_16_ex_self"])
    n_gip_32_ex_self = sum(1 for r in rows if r["gip_rb_32_ex_self"])
    n_gip_all_ex_self = sum(1 for r in rows if r["gip_rb_all_ex_self"])

    n_gip_8_ex_self_m = sum(1 for r in rows if r["gip_rb_8_ex_self_merged"])
    n_gip_16_ex_self_m = sum(1 for r in rows if r["gip_rb_16_ex_self_merged"])
    n_gip_32_ex_self_m = sum(1 for r in rows if r["gip_rb_32_ex_self_merged"])
    n_gip_all_ex_self_m = sum(1 for r in rows if r["gip_rb_all_ex_self_merged"])

    n_self_gip8 = sum(1 for r in rows if r["is_self_record_gip8"])
    n_self_only_gip8 = sum(1 for r in rows if r["is_self_only_gip8"])
    self_rate_gip8 = (n_self_gip8 / n_gip_8) if n_gip_8 > 0 else 0.0
    self_only_rate_gip8 = (n_self_only_gip8 / n_gip_8) if n_gip_8 > 0 else 0.0

    n_wrong_8 = sum(1 for r in rows if r["wrong_pool_8"])
    n_wrong_at_pool = sum(1 for r in rows if r["wrong_pool_at_pool"])
    n_empty = sum(1 for r in rows if r["empty_pool"])

    pool_sizes = sorted(r["pool_size"] for r in rows)
    p_med = median(pool_sizes)
    p_90 = pool_sizes[min(len(pool_sizes) - 1, int(len(pool_sizes) * 0.90))]

    untrunc_sizes = sorted(r["untruncated_pool_size"] for r in rows)
    u_med = median(untrunc_sizes)
    u_90 = untrunc_sizes[min(len(untrunc_sizes) - 1, int(len(untrunc_sizes) * 0.90))]

    rank_dist = dict(Counter(r["rank_bucket"] for r in rows))

    chan_counts = Counter()
    sole_counts = Counter()
    chan_counts_merged = Counter()
    sole_counts_merged = Counter()
    for r in rows:
        if r["gip_rb_8"]:
            for ch in r["channels_hit_8"]:
                chan_counts[ch] += 1
            if r["sole_channel_8"]:
                sole_counts[r["sole_channel_8"]] += 1
            for ch in r["channels_hit_8_with_merged"]:
                chan_counts_merged[ch] += 1
            if r["sole_channel_8_with_merged"]:
                sole_counts_merged[r["sole_channel_8_with_merged"]] += 1

    wall_clock_s = manifest.get("build_wall_clock_seconds")
    mean_q_build_s = (
        round(sum(build_times) / len(build_times), 4) if build_times else None
    )

    summary = {
        "config_name": config_name,
        "domain": domain,
        "subset": subset,
        "denominator": denom,
        "GIP_at_8": {"count": n_gip_8, "pct": round(n_gip_8 / denom * 100, 2)},
        "GIP_at_16": {"count": n_gip_16, "pct": round(n_gip_16 / denom * 100, 2)},
        "GIP_at_32": {"count": n_gip_32, "pct": round(n_gip_32 / denom * 100, 2)},
        "GIP_at_all": {"count": n_gip_all, "pct": round(n_gip_all / denom * 100, 2)},
        "GIP_role_aware_at_8": {
            "count": n_gip_ra_8,
            "pct": round(n_gip_ra_8 / denom * 100, 2),
        },
        "GIP_at_8_ex_self": {
            "count": n_gip_8_ex_self,
            "pct": round(n_gip_8_ex_self / denom * 100, 2),
        },
        "GIP_at_16_ex_self": {
            "count": n_gip_16_ex_self,
            "pct": round(n_gip_16_ex_self / denom * 100, 2),
        },
        "GIP_at_32_ex_self": {
            "count": n_gip_32_ex_self,
            "pct": round(n_gip_32_ex_self / denom * 100, 2),
        },
        "GIP_at_all_ex_self": {
            "count": n_gip_all_ex_self,
            "pct": round(n_gip_all_ex_self / denom * 100, 2),
        },
        "GIP_ex_self_surviving_merged": {
            "GIP_at_8": {
                "count": n_gip_8_ex_self_m,
                "pct": round(n_gip_8_ex_self_m / denom * 100, 2),
            },
            "GIP_at_16": {
                "count": n_gip_16_ex_self_m,
                "pct": round(n_gip_16_ex_self_m / denom * 100, 2),
            },
            "GIP_at_32": {
                "count": n_gip_32_ex_self_m,
                "pct": round(n_gip_32_ex_self_m / denom * 100, 2),
            },
            "GIP_at_all": {
                "count": n_gip_all_ex_self_m,
                "pct": round(n_gip_all_ex_self_m / denom * 100, 2),
            },
        },
        "self_record": {
            "n_self_any_slot_gip8": n_self_gip8,
            "self_record_rate_in_gip8": round(self_rate_gip8 * 100, 2),
            "n_self_only_gip8": n_self_only_gip8,
            "self_only_rate_in_gip8": round(self_only_rate_gip8 * 100, 2),
        },
        "wrong_pool_rate_at_8": {
            "count": n_wrong_8,
            "pct": round(n_wrong_8 / denom * 100, 2),
        },
        "wrong_pool_rate_at_max_pool": {
            "count": n_wrong_at_pool,
            "pct": round(n_wrong_at_pool / denom * 100, 2),
        },
        "empty_pool_rate": {"count": n_empty, "pct": round(n_empty / denom * 100, 2)},
        "pool_width": {
            "median": p_med,
            "p90": p_90,
            "min": min(pool_sizes),
            "max": max(pool_sizes),
            "untruncated_median": u_med,
            "untruncated_p90": u_90,
            "untruncated_max": max(untrunc_sizes),
        },
        "gold_rank_distribution": {
            "rank_1": rank_dist.get("1", 0),
            "rank_2_3": rank_dist.get("2-3", 0),
            "rank_4_8": rank_dist.get("4-8", 0),
            "rank_9_plus": rank_dist.get("9+", 0),
            "not_in_pool": rank_dist.get("none", 0),
        },
        "channel_attribution_top8": {
            "any": dict(sorted(chan_counts.items())),
            "sole": dict(sorted(sole_counts.items())),
            "including_merged_sources": {
                "any": dict(sorted(chan_counts_merged.items())),
                "sole": dict(sorted(sole_counts_merged.items())),
            },
        },
        "build_and_compile_stats": {
            "build_wall_clock_seconds": wall_clock_s,
            "mean_question_build_seconds": mean_q_build_s,
            "total_compile_rejected": total_compile_rejected,
            "total_pool_truncated": total_pool_truncated,
            "questions_with_pool_truncation": questions_with_truncation,
            "compile_failures_top10": dict(compile_failures.most_common(10)),
        },
    }
    if has_retro_batch:
        summary["retro_slot_occupancy"] = {
            "questions_with_retro_slot_top8": questions_with_retro_slot_top8,
            "questions_with_retro_slot_top8_pct": round(
                questions_with_retro_slot_top8 / denom * 100, 2
            ),
            "questions_with_retro_slot_all": questions_with_retro_slot_all,
            "questions_with_retro_slot_all_pct": round(
                questions_with_retro_slot_all / denom * 100, 2
            ),
            "questions_with_retro_compiled_or_merged": questions_with_retro_compiled_or_merged,
            "questions_with_retro_compiled_or_merged_pct": round(
                questions_with_retro_compiled_or_merged / denom * 100, 2
            ),
        }
    return summary, rows


def main(argv=None) -> int:
    default_assets = str(Path(__file__).resolve().parents[2] / "assets")
    ap = argparse.ArgumentParser(description="Candidate pool offline coverage evaluation")
    ap.add_argument(
        "--batch-root", required=True, help="Batch directory containing batch_manifest.json"
    )
    ap.add_argument(
        "--split-dir", required=True, help="Path to holdout_v1/{298,b121}"
    )
    ap.add_argument(
        "--questions",
        required=False,
        default=None,
        help="Questions jsonl for source record ID metadata",
    )
    ap.add_argument(
        "--assets-root",
        required=False,
        default=default_assets,
        help="Assets directory for template donor lookup",
    )
    ap.add_argument(
        "--subset", default="dev_tuning", choices=["dev_tuning", "full", "holdout"]
    )
    ap.add_argument("--config-name", default="S0")
    ap.add_argument(
        "--domain",
        default="dev-298",
        choices=["298", "dev-298", "b121", "biosysmodb121"],
    )
    ap.add_argument(
        "--out-dir",
        required=True,
        help="Summary output directory (reports/POOL_COVERAGE_2026-11-09/)",
    )
    ap.add_argument(
        "--mr-dir",
        required=True,
        help="Manual review TSV directory (gitignored)",
    )
    ap.add_argument("--unlock-token-file", default="")
    ap.add_argument("--expected-token-sha256", default="")

    args = ap.parse_args(argv)

    batch_root = Path(args.batch_root).resolve()
    split_dir = Path(args.split_dir).resolve()
    questions_path = Path(args.questions).resolve() if args.questions else None
    out_dir = Path(args.out_dir).resolve()
    mr_dir = Path(args.mr_dir).resolve()
    assets_root = Path(args.assets_root).resolve() if args.assets_root else None

    raw_by_tpl = None
    if assets_root and assets_root.is_dir():
        raw_by_tpl = load_template_raw_pairs(assets_root)

    summary, rows = evaluate_batch(
        batch_root=batch_root,
        split_dir=split_dir,
        questions_path=questions_path,
        subset=args.subset,
        unlock_token_file=args.unlock_token_file,
        expected_token_sha256=args.expected_token_sha256,
        config_name=args.config_name,
        domain=args.domain,
        raw_by_tpl=raw_by_tpl,
        assets_root=assets_root,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_file = out_dir / f"coverage_{args.domain}_{args.config_name}.json"
    summary_file.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # 写入私有逐题 TSV（gitignored）
    mr_sub = mr_dir / f"{args.domain}_{args.config_name}"
    mr_sub.mkdir(parents=True, exist_ok=True)
    tsv_file = mr_sub / "per_qid_coverage.tsv"
    fieldnames = [
        "qid",
        "pool_size",
        "untruncated_pool_size",
        "empty_pool",
        "gip_rb_8",
        "gip_rb_16",
        "gip_rb_32",
        "gip_rb_all",
        "gip_ra_8",
        "first_rank_rb",
        "rank_bucket",
        "is_self_record_gip8",
        "is_self_only_gip8",
        "gip_rb_8_ex_self",
        "gip_rb_8_ex_self_merged",
        "channels_hit_8",
        "channels_hit_8_with_merged",
        "sole_channel_8",
        "sole_channel_8_with_merged",
        "wrong_pool_8",
    ]
    with open(tsv_file, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for r in rows:
            row_copy = dict(r)
            row_copy["channels_hit_8"] = ",".join(r["channels_hit_8"])
            row_copy["channels_hit_8_with_merged"] = ",".join(
                r["channels_hit_8_with_merged"]
            )
            writer.writerow(row_copy)

    print(
        f"[{args.domain} {args.config_name}] Evaluation complete on subset '{args.subset}' (n={summary['denominator']}):"
    )
    print(
        f"  GIP@8: {summary['GIP_at_8']['count']}/{summary['denominator']} ({summary['GIP_at_8']['pct']}%) "
        f"| ex-self (slot): {summary['GIP_at_8_ex_self']['count']} ({summary['GIP_at_8_ex_self']['pct']}%) "
        f"| ex-self (merged): {summary['GIP_ex_self_surviving_merged']['GIP_at_8']['count']} ({summary['GIP_ex_self_surviving_merged']['GIP_at_8']['pct']}%)"
    )
    print(
        f"  GIP@16: {summary['GIP_at_16']['count']} | GIP@32: {summary['GIP_at_32']['count']} | GIP@all: {summary['GIP_at_all']['count']}"
    )
    print(
        f"  Wrong Pool@8: {summary['wrong_pool_rate_at_8']['count']} ({summary['wrong_pool_rate_at_8']['pct']}%) "
        f"| Empty: {summary['empty_pool_rate']['count']} ({summary['empty_pool_rate']['pct']}%)"
    )
    print(
        f"  Pool Width: median={summary['pool_width']['median']}, P90={summary['pool_width']['p90']} "
        f"(untruncated median={summary['pool_width']['untruncated_median']}, P90={summary['pool_width']['untruncated_p90']})"
    )
    print(f"  Rank Dist: {summary['gold_rank_distribution']}")
    print(
        f"  Channels (slot): {summary['channel_attribution_top8']['any']} (Sole: {summary['channel_attribution_top8']['sole']})"
    )
    print(
        f"  Channels (incl. merged): {summary['channel_attribution_top8']['including_merged_sources']['any']} "
        f"(Sole: {summary['channel_attribution_top8']['including_merged_sources']['sole']})"
    )
    print(f"  Summary saved: {summary_file}")
    print(f"  Per-qid TSV saved: {tsv_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
