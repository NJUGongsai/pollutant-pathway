#!/usr/bin/env python
"""EXP1 声明桶离线读数脚本(E11;零 LLM、只读账本)。

用途:实验 1 B/C 臂里,产物优先提案**编译执行成功但进声明桶**的条目
(方案甲七条件任一不满足;``verification_tier == "declared"``)——不
提交事件、不进主成绩(预注册 §4.3 D3),只记在 decide 结论的
``declared_bucket``。声明桶两档 ``bucket_kind``:
``declared_recognized``(片段命中 §4.3.3 已知半分子表)与
``declared_unrecognized``(对不上任何表 / 域外元素 / 移除未声明)。
本脚本只读该结论,按 v4 规则(同一条目内底物在反应物侧 + 主产物集合
⊆ 该条目产物集合)对题集算"若计入"的命中,供离线读数与披露。

红线:
- 零模型调用、零网络、不改任何 run/store(只读 sqlite 之外的
  decide outcome artifact 与题集文件);
- 不 import evaluation.py / s5b_scoring.py(判分代码零改动);
- 逐题明细(含产物 SMILES)只写 ``--per-qid-out``(默认
  ``reports/manual_review/`` 下,gitignored);``--out`` 聚合只含计数。

用法::

    python scripts/eval/exp1_declared_bucket.py \\
        --batch-root runs/exp1_b \\
        --runs-root runs \\
        --questions <题卷 jsonl> \\
        --out docs/reviews/evidence/exp1_.../declared_bucket.json \\
        --per-qid-out reports/manual_review/exp1_declared_bucket/per_qid.json \\
        --domain-tag b121

题卷 jsonl 每行至少含 ``qid`` / ``substrate_smiles`` / ``products_smiles``
(可选 ``raw_reaction``,形如 ``A.B>>C.D``)。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "exp1-declared-bucket-2"

_BUCKET_RECOGNIZED = "declared_recognized"
_BUCKET_UNRECOGNIZED = "declared_unrecognized"


def _bucket_kind(item: dict) -> str:
    """桶分类(旧 run 无该键 ⇒ unknown;不猜成任何一档)。"""
    kind = str(item.get("bucket_kind") or "")
    return kind or "unknown"


def _canon(smiles: str) -> str | None:
    """RDKit 规范 SMILES(不可解析 ⇒ None;身份比较单一事实源)。"""
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        mol = Chem.MolFromSmiles(str(smiles or ""))
        if mol is None:
            return None
        return Chem.MolToSmiles(mol)
    except Exception:  # noqa: BLE001 —— 不可解析按无身份处理
        return None


def _split_reaction(raw: str) -> tuple[list[str], list[str]]:
    text = str(raw or "")
    if ">>" not in text:
        return [], []
    lhs, rhs = text.split(">>", 1)
    return ([p for p in lhs.split(".") if p],
            [p for p in rhs.split(".") if p])


def _load_questions(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _gold_index(question: dict) -> dict:
    """题目的 v4 判据输入:反应物侧 canonical 集合 + 产物 canonical 集合
    + 底物是否在反应物侧(题面底物 || raw_reaction 左端)。"""
    raw = str(question.get("raw_reaction") or "")
    lhs_raw, rhs_raw = _split_reaction(raw)
    substrate_canon = _canon(str(question.get("substrate_smiles") or ""))
    reactants = {_canon(s) for s in (lhs_raw or [
        str(question.get("substrate_smiles") or "")])}
    products = {_canon(s) for s in (rhs_raw or [
        str(s) for s in (question.get("products_smiles") or [])])}
    reactants = {x for x in reactants if x}
    return {
        "reactants": reactants,
        "products": {x for x in products if x},
        "substrate_on_reactant_side": bool(substrate_canon) and (
            substrate_canon in reactants),
        "reactant_side_known": bool(raw),
    }


def _decide_outcomes(run_dir: Path) -> list[dict]:
    """run 目录下全部 expansion_outcome artifact(只读;坏文件跳过)。"""
    results = run_dir / "results"
    if not results.is_dir():
        return []
    found: list[dict] = []
    for path in sorted(results.glob("*/expansion_outcome.json")):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            continue
        outcome = payload.get("outcome")
        if not isinstance(outcome, dict):
            continue
        if str(outcome.get("kind")) != "scheduled":
            continue
        detail = outcome.get("detail") or {}
        model = detail.get("model") if isinstance(detail, dict) else None
        if not isinstance(model, dict):
            continue
        declared = model.get("declared_bucket")
        if not isinstance(declared, list) or not declared:
            continue
        found.append({"path": str(path), "declared_bucket": declared,
                      "model": model})
    return found


def _per_entry_hits(declared: list[dict], gold: dict) -> list[dict]:
    rows: list[dict] = []
    substrate_ok = bool(gold.get("substrate_on_reactant_side"))
    for item in declared:
        spec = dict(item.get("reaction_spec") or {})
        effective_principal = str(spec.get("product_smiles")
                                  or item.get("compiled_principal") or "")
        declared_product = str(item.get("declared_product") or "")
        principal_key = _canon(effective_principal)
        # v4 规则:同一条目内底物在反应物侧 + 主产物集合 ⊆ 该条目产物集合
        would_hit = bool(substrate_ok and principal_key
                         and principal_key in gold["products"])
        rows.append({
            "hypothesis_id": str(item.get("hypothesis_id") or ""),
            "verification_tier": str(item.get("verification_tier") or ""),
            "bucket_kind": _bucket_kind(item),
            "declared_product": declared_product,
            "effective_principal": effective_principal,
            "coproducts": [str(c) for c in (spec.get("coproducts") or [])],
            "added_heavy_atoms": item.get("added_heavy_atoms"),
            "removed_heavy_atoms": item.get("removed_heavy_atoms"),
            "added_fragment_count": item.get("added_fragment_count"),
            "net_zero_rewrite": bool(item.get("net_zero_rewrite")),
            "bucket_reasons": [str(r) for r in
                               (item.get("bucket_reasons") or [])],
            "would_hit": would_hit,
            "substrate_reactant_side_ok": substrate_ok,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="exp1_declared_bucket",
        description="EXP1 声明桶离线读数(零 LLM;只读 decide 结论)")
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--questions", required=True,
                        help="题卷 jsonl(每行 qid/substrate_smiles/"
                             "products_smiles[,raw_reaction])")
    parser.add_argument("--out", required=True,
                        help="聚合读数 JSON 输出路径(只含计数)")
    parser.add_argument("--per-qid-out", default="",
                        help="逐题明细 JSON 输出路径(gitignored;含 "
                             "SMILES)")
    parser.add_argument("--domain-tag", default="",
                        help="题域标签(如 b121 / 298;对外数字必带)")
    args = parser.parse_args(argv)

    batch_root = Path(args.batch_root)
    runs_root = Path(args.runs_root)
    questions = _load_questions(Path(args.questions))
    if not questions:
        print("题卷为空", file=sys.stderr)
        return 2

    per_qid: list[dict] = []
    n_entries = n_hits = 0
    n_qid_with_bucket = n_qid_with_hit = 0
    by_bucket = {_BUCKET_RECOGNIZED: 0, _BUCKET_UNRECOGNIZED: 0,
                 "unknown": 0}
    n_qid_with_recognized = 0
    for question in questions:
        qid = str(question.get("qid") or "")
        run_input_path = batch_root / "run_inputs" / f"{qid}.json"
        if not run_input_path.is_file():
            per_qid.append({"qid": qid, "run_id": "", "n_entries": 0,
                            "n_would_hit": 0, "entries": [],
                            "by_bucket": dict(by_bucket),
                            "status": "run_input_missing"})
            continue
        run_input = json.loads(run_input_path.read_text(encoding="utf-8"))
        run_id = str(run_input.get("run_id") or "")
        run_dir = runs_root / run_id
        outcomes = _decide_outcomes(run_dir)
        gold = _gold_index(question)
        entries: list[dict] = []
        for outcome in outcomes:
            entries.extend(_per_entry_hits(outcome["declared_bucket"], gold))
        hits = sum(1 for e in entries if e["would_hit"])
        qid_by_bucket = {_BUCKET_RECOGNIZED: 0, _BUCKET_UNRECOGNIZED: 0,
                         "unknown": 0}
        for entry in entries:
            kind = str(entry.get("bucket_kind") or "unknown")
            by_bucket[kind] = by_bucket.get(kind, 0) + 1
            qid_by_bucket[kind] = qid_by_bucket.get(kind, 0) + 1
        n_entries += len(entries)
        n_hits += hits
        if entries:
            n_qid_with_bucket += 1
        if hits:
            n_qid_with_hit += 1
        if qid_by_bucket[_BUCKET_RECOGNIZED]:
            n_qid_with_recognized += 1
        per_qid.append({"qid": qid, "run_id": run_id,
                        "n_entries": len(entries), "n_would_hit": hits,
                        "by_bucket": qid_by_bucket,
                        "status": "ok" if entries else "no_declared_bucket",
                        "entries": entries})

    aggregate = {
        "script": "exp1_declared_bucket",
        "version": SCRIPT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "batch_root": str(batch_root),
        "runs_root": str(runs_root),
        "questions": str(args.questions),
        "domain_tag": str(args.domain_tag),
        "n_questions": len(questions),
        "n_questions_with_declared_bucket": n_qid_with_bucket,
        "n_questions_with_recognized": n_qid_with_recognized,
        "n_declared_entries": n_entries,
        "n_declared_entries_by_bucket": dict(by_bucket),
        "n_would_hit_entries": n_hits,
        "n_questions_with_any_hit": n_qid_with_hit,
        "per_qid_counts": [
            {"qid": row["qid"], "n_entries": row["n_entries"],
             "n_would_hit": row["n_would_hit"],
             "by_bucket": row["by_bucket"],
             "status": row["status"]}
            for row in per_qid],
        "note": ("声明桶不进事件、不进主成绩;本读数只是'若计入'的离线"
                 "披露,不改任何已冻结判定(预注册 §4.3 D3 / §6);"
                 "declared_recognized 与 declared_unrecognized 分档计数"),
        "llm_calls": 0,
        "scoring_code_touched": False,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2)
                        + "\n", encoding="utf-8")
    if args.per_qid_out:
        per_path = Path(args.per_qid_out)
        per_path.parent.mkdir(parents=True, exist_ok=True)
        per_path.write_text(json.dumps({"version": SCRIPT_VERSION,
                                        "domain_tag": str(args.domain_tag),
                                        "per_qid": per_qid},
                                       ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({k: aggregate[k] for k in (
        "n_questions", "n_questions_with_declared_bucket",
        "n_questions_with_recognized", "n_declared_entries",
        "n_declared_entries_by_bucket", "n_would_hit_entries",
        "n_questions_with_any_hit")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())