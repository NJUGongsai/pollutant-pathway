#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pool_builder_parallel.py — 多进程并发候选池批次构建器（零模型调用）。

加速离线覆盖率评测中的候选池构建（8 进程并发）。
严格遵守调参集（dev_tuning）边界，默认拒绝读取或构建 holdout 题。
同时在 batch_manifest.json 中保留截断前完整候选摘要（untruncated_candidates）
以支持 GIP@16 / GIP@32 / GIP@all 与 9+ 名次分布精确统计，而 run_inputs/<qid>.json
保持与 s5b_cli build 的 max_pool 截断逐字节一致。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from pathway_v43.adapters.v3_engine import get_engine
from pathway_v43.config import resolve_config
from pathway_v43.pollutant.s5b_builder import (
    PPV1_SPLIT_MANIFEST_VERSION,
    S5B_GITIGNORED_REPO_ROOT,
    S5B_POOL_MAX,
    S5B_POOL_RAW_TOP,
    S5B_POOL_THRESHOLD,
    S5B_SPLIT_RULE_VERSION,
    _file_sha256,
    build_reference_graph,
    build_run_input,
    check_output_root,
    default_pool_provider,
    load_questions,
    reference_graph_sha256,
)
from pathway_v43.storage.build_identity import write_batch_build_identity

_worker_provider = None
_worker_max_pool: int = S5B_POOL_MAX


def _load_qids_file(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


class _LazyEngineProxy:
    def __init__(self, v3_code_root: str | None, assets_root: str | None):
        self._v3_code_root = v3_code_root
        self._assets_root = assets_root
        self._eng = None

    def _resolve(self):
        if self._eng is None:
            full_cfg = resolve_config(self._v3_code_root, self._assets_root)
            self._eng = get_engine(full_cfg)
        return self._eng

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)


def _init_worker(
    v3_code_root: str | None,
    assets_root: str | None,
    pool_mode: str,
    recorded_source: bool,
    corpus_channel: bool,
    max_pool: int,
    pool_threshold: float,
    analog_corpus: str,
    analog_channel: bool = True,
    raw_top: int = S5B_POOL_RAW_TOP,
    uspto_channel: bool = False,
    analog_retrieval_mode: str = "similarity",
    center_shell: int = 2,
    retro_channel: bool = False,
    retro_dataset: str = "rhea",
    retro_radii: tuple[int, ...] | set[int] | None = None,
    retro_retrieval_mode: str = "hybrid",
    retro_ranking_mode: str = "append",
):
    global _worker_provider, _worker_max_pool
    _worker_max_pool = int(max_pool)
    if pool_mode != "template":
        _worker_provider = default_pool_provider(None)
        return

    default_cache = (
        Path(__file__).resolve().parents[2]
        / "reports/ppv1_s5b/pool_coverage_20261109/_rc_cache"
    )
    os.environ.setdefault("V43_RECORDED_CORPUS_CACHE_DIR", str(default_cache))

    effective_corpus = "v1" if analog_corpus == "uspto" else (analog_corpus or "v1")
    effective_uspto = bool(uspto_channel or analog_corpus == "uspto")
    os.environ["V43_ANALOG_CORPUS"] = effective_corpus
    cfg = resolve_config(v3_code_root, assets_root)

    eng = None
    if recorded_source or corpus_channel:
        eng = _LazyEngineProxy(v3_code_root, assets_root)

    # 使用不截断上限 1000 获取 merged 完整序列，随后在 _process_question_item 中按 _worker_max_pool 截断
    _worker_provider = default_pool_provider(
        cfg,
        max_pool=1000,
        raw_top=int(raw_top),
        threshold=pool_threshold,
        engine=eng,
        recorded_channel=recorded_source,
        corpus_channel=corpus_channel,
        analog_channel=analog_channel,
        uspto_channel=effective_uspto,
        analog_retrieval_mode=analog_retrieval_mode,
        center_shell=int(center_shell),
        retro_channel=bool(retro_channel),
        retro_dataset=str(retro_dataset),
        retro_radii=retro_radii,
        retro_retrieval_mode=str(retro_retrieval_mode),
        retro_ranking_mode=str(retro_ranking_mode),
    )


def _process_question_item(item: tuple[dict, bool, str, str, str]) -> dict:
    global _worker_provider, _worker_max_pool
    t_q0 = time.time()
    record, is_repeated, batch_tag, domain, provider_kind = item

    qid = str(record["qid"])
    substrate = str(record["substrate_smiles"])

    graph = build_reference_graph(
        record,
        repeated_substrate=is_repeated,
        domain=domain,
    )

    if _worker_provider is not None:
        full_specs = list(_worker_provider(substrate))
        pool_diag = dict(getattr(_worker_provider, "last_diagnostics", None) or {})
    else:
        full_specs = []
        pool_diag = {}

    pool_specs = full_specs[: int(_worker_max_pool)]
    n_truncated = max(0, len(full_specs) - len(pool_specs))
    if pool_diag:
        pool_diag["n_pool_returned"] = len(pool_specs)
        pool_diag["n_pool_truncated"] = n_truncated
        cands_copy = []
        for c in pool_diag.get("candidates") or []:
            c_dict = dict(c)
            pr = c_dict.get("pool_rank")
            if pr is not None and int(pr) > int(_worker_max_pool):
                c_dict["outcome"] = "pool_truncated"
                c_dict["signature_head"] = None
            cands_copy.append(c_dict)
        pool_diag["candidates"] = cands_copy

    untruncated_candidates = []
    for s in full_specs:
        cand_summary: dict[str, Any] = {
            "key": s.get("key"),
            "transformation_ref": s.get("transformation_ref"),
            "product_smiles": s.get("product_smiles"),
            "coproducts": list(s.get("coproducts") or []),
            "merged_source_keys": list(
                (s.get("compile") or {}).get("merged_source_keys") or []
            ),
        }
        if s.get("channel"):
            cand_summary["channel"] = s.get("channel")
        if s.get("parent_reaction_ids"):
            cand_summary["parent_reaction_ids"] = list(
                s.get("parent_reaction_ids") or []
            )
        s_comp = s.get("compile") or {}
        if (
            "parent_reaction_ids" in s_comp
            or "donor_lhs_strict_keys" in s_comp
            or "merged_retro_sources" in s_comp
        ):
            cand_summary["compile"] = {
                k: s_comp[k]
                for k in (
                    "merged_source_keys",
                    "parent_reaction_ids",
                    "donor_lhs_strict_keys",
                    "donor_rhs_strict_keys",
                    "merged_retro_sources",
                )
                if k in s_comp
            }
        untruncated_candidates.append(cand_summary)

    pools = {substrate: pool_specs}
    run_input = build_run_input(
        record,
        batch_tag=batch_tag,
        pools=pools,
        provider_kind=provider_kind,
    )

    return {
        "qid": qid,
        "graph": graph,
        "run_input": run_input,
        "pool_size": len(pool_specs),
        "untruncated_pool_size": len(full_specs),
        "untruncated_candidates": untruncated_candidates,
        "pool_diagnostics": pool_diag,
        "substrate_smiles": substrate,
        "n_gold_products": len(record.get("products_smiles") or []),
        "repeated_substrate": is_repeated,
        "build_seconds": round(time.time() - t_q0, 4),
    }


def build_batch_parallel(
    questions_path: str | Path,
    output_root: str | Path,
    *,
    split_dir: str | Path | None = None,
    subset: str = "dev_tuning",
    batch_tag: str = "s5b-298",
    pool_mode: str = "template",
    recorded_source: bool = True,
    corpus_channel: bool = True,
    analog_channel: bool = True,
    max_pool: int = S5B_POOL_MAX,
    raw_top: int = S5B_POOL_RAW_TOP,
    pool_threshold: float = S5B_POOL_THRESHOLD,
    analog_corpus: str = "v1",
    uspto_channel: bool = False,
    analog_retrieval_mode: str = "similarity",
    center_shell: int = 2,
    retro_channel: bool = False,
    retro_dataset: str = "rhea",
    retro_radii: tuple[int, ...] | set[int] | None = None,
    retro_retrieval_mode: str = "hybrid",
    retro_ranking_mode: str = "append",
    provider_kind: str = "real",
    domain: str = "298",
    limit: int | None = None,
    workers: int = 8,
    v3_code_root: str | None = None,
    assets_root: str | None = None,
) -> dict:
    if subset != "dev_tuning":
        raise PermissionError(
            f"Refused subset={subset!r}: only 'dev_tuning' is permitted by redline."
        )

    t0 = time.time()
    root = check_output_root(output_root)
    all_questions = load_questions(questions_path)

    # 先在全题卷底物字符串上统计重复底物标记，随后严格过滤到 dev_tuning
    substrate_counts: dict[str, int] = {}
    for record in all_questions:
        sub = str(record["substrate_smiles"])
        substrate_counts[sub] = substrate_counts.get(sub, 0) + 1

    if split_dir is not None:
        dev_qids = _load_qids_file(Path(split_dir) / "dev_qids.txt")
        questions = [q for q in all_questions if str(q["qid"]) in dev_qids]
    else:
        questions = all_questions

    if limit is not None:
        questions = questions[: int(limit)]

    graphs_dir = root / "reference_graphs"
    inputs_dir = root / "run_inputs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    items = [
        (
            q,
            substrate_counts[str(q["substrate_smiles"])] > 1,
            batch_tag,
            domain,
            provider_kind,
        )
        for q in questions
    ]

    print(
        f"Building {len(items)} questions (subset={subset}, domain={domain}, tag={batch_tag}) "
        f"with {workers} parallel workers..."
    )
    normalized_radii = (
        tuple(sorted(int(r) for r in retro_radii))
        if retro_radii is not None
        else None
    )
    worker_init_args = (
        v3_code_root,
        assets_root,
        pool_mode,
        recorded_source,
        corpus_channel,
        max_pool,
        pool_threshold,
        analog_corpus,
        analog_channel,
        raw_top,
        uspto_channel,
        analog_retrieval_mode,
        center_shell,
        retro_channel,
        retro_dataset,
        normalized_radii,
        retro_retrieval_mode,
        retro_ranking_mode,
    )

    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker, initargs=worker_init_args
    ) as executor:
        results = list(executor.map(_process_question_item, items))

    entries: list[dict] = []
    for res in results:
        qid = res["qid"]
        graph = res["graph"]
        run_input = res["run_input"]

        graph_path = graphs_dir / f"{graph['reference_graph_id']}.json"
        graph_path.write_text(
            json.dumps(graph, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8",
        )

        input_path = inputs_dir / f"{qid}.json"
        input_path.write_text(
            json.dumps(run_input, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8",
        )

        entries.append(
            {
                "qid": qid,
                "run_id": run_input["run_id"],
                "reference_graph_id": graph["reference_graph_id"],
                "graph_rel": f"reference_graphs/{graph['reference_graph_id']}.json",
                "graph_sha256": reference_graph_sha256(graph),
                "run_input_rel": f"run_inputs/{qid}.json",
                "substrate_smiles": res["substrate_smiles"],
                "pool_size": res["pool_size"],
                "untruncated_pool_size": res["untruncated_pool_size"],
                "untruncated_candidates": res["untruncated_candidates"],
                "pool_diagnostics": res["pool_diagnostics"],
                "n_gold_products": res["n_gold_products"],
                "repeated_substrate": res["repeated_substrate"],
                "build_seconds": res["build_seconds"],
            }
        )

    split_manifest = {
        "schema_version": PPV1_SPLIT_MANIFEST_VERSION,
        "split_manifest_id": f"sm-s5b-{batch_tag}",
        "split_rule_version": S5B_SPLIT_RULE_VERSION,
        "input_data_manifest_hash": _file_sha256(questions_path),
        "assignments": [
            {
                "reference_graph_id": e["reference_graph_id"],
                "source_group_id": f"sg-{e['qid']}",
                "split": "held_out",
            }
            for e in entries
        ],
        "unseen_exclusion_manifest": {
            "track": "unseen_path_inference",
            "excluded": [],
        },
    }
    (root / "split_manifest.json").write_text(
        json.dumps(split_manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )

    effective_corpus = "v1" if analog_corpus == "uspto" else (analog_corpus or "v1")
    os.environ["V43_ANALOG_CORPUS"] = effective_corpus
    cfg = resolve_config(v3_code_root, assets_root)
    run_input_paths = {
        e["qid"]: (e["run_id"], str(inputs_dir / f"{e['qid']}.json")) for e in entries
    }
    write_batch_build_identity(root, run_input_paths=run_input_paths, config=cfg)

    wall_clock = round(time.time() - t0, 2)
    batch_manifest = {
        "batch_tag": batch_tag,
        "domain": domain,
        "subset": subset,
        "max_pool": int(max_pool),
        "pool_threshold": float(pool_threshold),
        "recorded_source": bool(recorded_source),
        "corpus_channel": bool(corpus_channel),
        "analog_channel": bool(analog_channel),
        "analog_corpus": str(analog_corpus),
        "n_questions": len(entries),
        "registration_order": [e["qid"] for e in entries],
        "entries": entries,
        "build_wall_clock_seconds": wall_clock,
    }
    (root / "batch_manifest.json").write_text(
        json.dumps(batch_manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )

    print(f"Completed build for {len(entries)} questions in {wall_clock:.2f}s -> {root}")
    return batch_manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Parallel pool builder for offline coverage")
    ap.add_argument("--questions", required=True, help="Path to questions JSONL")
    ap.add_argument("--output-root", required=True, help="Gitignored output batch root")
    ap.add_argument("--split-dir", required=True, help="Path to holdout_v1/{298,b121}")
    ap.add_argument("--subset", default="dev_tuning", choices=["dev_tuning"])
    ap.add_argument("--batch-tag", default="s0-298")
    ap.add_argument("--domain", default="298", choices=["298", "b121"])
    ap.add_argument("--pool-mode", default="template", choices=["template", "none"])
    ap.add_argument(
        "--recorded-source",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    ap.add_argument(
        "--corpus-channel",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    ap.add_argument(
        "--analog-channel",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    ap.add_argument("--max-pool", type=int, default=S5B_POOL_MAX)
    ap.add_argument("--raw-top", type=int, default=S5B_POOL_RAW_TOP)
    ap.add_argument("--pool-threshold", type=float, default=S5B_POOL_THRESHOLD)
    ap.add_argument("--analog-corpus", default="v1")
    ap.add_argument(
        "--uspto-channel",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    ap.add_argument(
        "--analog-retrieval-mode",
        default="similarity",
        choices=["similarity", "fg", "merge"],
    )
    ap.add_argument("--center-shell", type=int, default=2, choices=[1, 2, 3])
    ap.add_argument(
        "--retro-channel",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    ap.add_argument(
        "--retro-dataset",
        default="rhea",
        choices=["rhea", "mnx", "mnx+rhea"],
    )
    ap.add_argument(
        "--retro-radii",
        default=None,
        help="Comma-separated radii e.g. '6' or '2,4'",
    )
    ap.add_argument(
        "--retro-retrieval-mode",
        default="hybrid",
        choices=["hybrid", "tanimoto", "substruct", "containment"],
    )
    ap.add_argument(
        "--retro-ranking-mode",
        default="append",
        choices=["append", "unified_score"],
    )
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--v3-code-root", default=None)
    ap.add_argument("--assets-root", default=None)

    args = ap.parse_args(argv)
    parsed_radii = (
        tuple(int(x.strip()) for x in args.retro_radii.split(",") if x.strip())
        if args.retro_radii
        else None
    )
    build_batch_parallel(
        questions_path=args.questions,
        output_root=args.output_root,
        split_dir=args.split_dir,
        subset=args.subset,
        batch_tag=args.batch_tag,
        pool_mode=args.pool_mode,
        recorded_source=args.recorded_source,
        corpus_channel=args.corpus_channel,
        analog_channel=args.analog_channel,
        max_pool=args.max_pool,
        raw_top=args.raw_top,
        pool_threshold=args.pool_threshold,
        analog_corpus=args.analog_corpus,
        uspto_channel=args.uspto_channel,
        analog_retrieval_mode=args.analog_retrieval_mode,
        center_shell=args.center_shell,
        retro_channel=args.retro_channel,
        retro_dataset=args.retro_dataset,
        retro_radii=parsed_radii,
        retro_retrieval_mode=args.retro_retrieval_mode,
        retro_ranking_mode=args.retro_ranking_mode,
        domain=args.domain,
        limit=args.limit,
        workers=args.workers,
        v3_code_root=args.v3_code_root,
        assets_root=args.assets_root,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
