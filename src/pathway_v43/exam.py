"""EC298 单步外考 — 输入隔离、引擎臂、agent 臂与冻结评分器(零 LLM 判分)。

阶段任务书:docs/TASK_V43_EC298.md。与 dev 批跑(pathway_v43.batch)复用
同一套 worker/闸门/导出机制,但输入来自冻结 298 题卷的一次性白名单。

- **输入隔离**(``build_exam_inputs``):从冻结 questions.jsonl 一次性提取
  运行侧白名单 ``exam_inputs.jsonl`` —— 每行仅 qid / substrate_smiles /
  input_index;products_smiles、category、raw_reaction、金标标签一律不进
  运行侧文件(金标只在判分阶段打开,判分零 LLM)。输出存在即拒绝重写。
- **引擎臂**(``run_engine_arm``):冻结 V43Engine + 已校验 assets 逐题
  单步 ``engine.predict(top_k=10)``,零模型费用;每题保存有序 Top-10 与
  **完整候选池身份表**(判分后三档诊断用);引擎/资产 SHA 逐题落档。
  N 进程序行分片(引擎进程身份护栏 = 一进程一引擎)。
- **agent 臂**(``run_exam_agent``):复用 BatchCoordinator,exam manifest
  由白名单直接构造;qid 即 route_id(显式映射,绝不从目录名 rsplit 反推);
  预算 max_depth=1 / max_expansions=1(单步);共享闸门
  ``max_in_flight=40`` 限制同时在途请求数;40 worker 并行。
- **在途证据**(``inflight_evidence``):每题预测响应产物流里记录
  sent_at_epoch/done_at_epoch/request_id/HTTP status/usage
  (llm_client 落盘)→ 计算峰值同时得到提供方正常响应的请求重叠数;
  限流拒绝/连接失败不计入达标峰值。
- **冻结评分器**(``score_exam``):金标集合 cn 身份(v3
  eawag_lookup._cn_identity 同口径,charge-normalized stereo-blind)对
  有序候选逐一比较,任一金标产物命中即取该题首个命中 rank;分母恒为
  全部 298 题(空/部分答卷计入,不剔除)。hit@1/3/5 主对照;agent 的
  hit@10 恒等于 hit@5(输出宽度上限,如实标注)。

红线:本模块不把 products_smiles/category 写进 PredictionTask、检索查询
或模型请求;判分读取金标发生在全部原始答卷封存之后;不因分数改配置。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXAM_SCHEMA_VERSION = "v43-exam-1"

EXAM_SPLIT_NAME = "exam298"          # manifest["split"];run_id 前缀
EXAM_WORKERS = 40
EXAM_MAX_IN_FLIGHT = 40
EXAM_MAX_DEPTH = 1
EXAM_MAX_EXPANSIONS = 1
EXAM_FRONTIER_WIDTH = 5
EXAM_ENGINE_TOP_K = 10


class ExamError(RuntimeError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- 输入隔离


def build_exam_inputs(questions_path: str | Path,
                      out_path: str | Path) -> dict:
    """一次性白名单提取(qid/substrate/input_index);存在即拒绝重写。"""
    questions_path = Path(questions_path)
    out_path = Path(out_path)
    if out_path.exists():
        raise ExamError(
            f"白名单已存在,拒绝重写(一次性提取):{out_path}",
            {"path": str(out_path)})
    rows = []
    seen: set[str] = set()
    for idx, line in enumerate(questions_path.read_text(
            encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        rec = json.loads(line)
        qid = rec.get("qid")
        if not qid or qid in seen:
            raise ExamError("题卷 qid 缺失或重复(fail-closed)",
                            {"index": idx, "qid": qid})
        seen.add(qid)
        substrate = rec.get("substrate_smiles")
        if not substrate:
            raise ExamError("题卷缺 substrate_smiles",
                            {"index": idx, "qid": qid})
        # 白名单字段:仅此三项;金标/类别/原始反应一律不提取
        rows.append({"input_index": idx, "qid": qid,
                     "substrate_smiles": substrate})
    if not rows:
        raise ExamError("题卷为空", {"path": str(questions_path)})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, out_path)
    return {
        "schema_version": EXAM_SCHEMA_VERSION,
        "kind": "exam_input_whitelist",
        "n_questions": len(rows),
        "n_unique_qids": len(seen),
        "order": "original_questions_file_order",
        "questions_sha256": _sha256_file(questions_path),
        "exam_inputs_sha256": _sha256_file(out_path),
        "gold_fields_excluded": ["products_smiles", "category",
                                 "raw_reaction"],
    }


def load_exam_inputs(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8")) \
        if str(path).endswith(".json") else None
    rows = []
    if data is not None:
        raise ExamError("期望 JSONL 白名单,得到 JSON", {"path": str(path)})
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    for r in rows:
        if set(r) != {"input_index", "qid", "substrate_smiles"}:
            raise ExamError(
                "白名单字段超出 qid/substrate_smiles/input_index(金标隔离被破坏)",
                {"row_keys": sorted(r)})
    return rows


# ---------------------------------------------------------------- 引擎臂

_ENGINE_CHUNK_ENTRY = (
    "import sys, json\n"
    "from pathway_v43.exam import engine_chunk_entry\n"
    "engine_chunk_entry(sys.argv[1], sys.argv[2], int(sys.argv[3]))\n"
)


def engine_chunk_entry(input_path: str, out_path: str, top_k: int) -> None:
    """子进程入口:读分片输入 JSONL → 逐题预测 → 写分片结果 JSONL。"""
    from .config import resolve_config

    cfg = resolve_config()
    rows = [json.loads(l) for l in Path(input_path).read_text(
        encoding="utf-8").splitlines() if l.strip()]
    summary = _engine_chunk(cfg, rows, Path(out_path), top_k)
    print(json.dumps(summary, ensure_ascii=False))


def _engine_chunk(config, rows: list[dict], out_path: Path,
                  top_k: int) -> dict:
    """单进程引擎分片:逐题单步 predict(引擎进程身份护栏 = 一进程一引擎)。"""
    from .adapters.v3_engine import get_engine
    from .domain.identity import cn_identity

    engine = get_engine(config)
    asset_identity = engine.asset_identity()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_ok = n_empty = 0
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            qid = r["qid"]
            smiles = r["substrate_smiles"]
            rec: dict = {"qid": qid, "input_index": r["input_index"],
                         "status": "ok"}
            try:
                cands = engine.predict(smiles, qid, top_k=top_k)
                products = []
                pool_identities = []
                for c in cands:
                    ident = c.get("product_identity") or cn_identity(
                        c.get("product_smiles", "")) or ""
                    products.append({
                        "engine_rank": c.get("engine_rank"),
                        "product_smiles": c.get("product_smiles", ""),
                        "product_identity": ident,
                        "cand_id": c.get("cand_id"),
                        "source_id": c.get("source_id"),
                        "kind": c.get("kind"),
                        "score": c.get("score")})
                    pool_identities.append(ident)
                rec["top10"] = products
                rec["pool_identities"] = pool_identities
                if products:
                    n_ok += 1
                else:
                    rec["status"] = "empty"
                    n_empty += 1
            except Exception as exc:  # 显式失败行,计入分母
                rec["status"] = "failed"
                rec["failed"] = f"{type(exc).__name__}:{str(exc)[:200]}"
                rec["top10"] = []
                rec["pool_identities"] = []
                n_empty += 1
            rec["asset_identity"] = asset_identity
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)
                    + "\n")
    return {"n_rows": len(rows), "n_ok": n_ok, "n_empty_or_failed": n_empty}


def run_engine_arm(exam_inputs_path: str | Path, out_dir: str | Path,
                   *, workers: int = EXAM_WORKERS,
                   v3_code_root: str | None = None,
                   assets_root: str | None = None,
                   top_k: int = EXAM_ENGINE_TOP_K) -> dict:
    """引擎臂:N 进程分片并行(零模型费用)→ 冻结 input_index 顺序归并。"""
    rows = load_exam_inputs(exam_inputs_path)
    out_dir = Path(out_dir)
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    env.setdefault("PYTHONPATH", str(repo_root / "src"))
    if v3_code_root:
        env.setdefault("V3_CODE_ROOT", str(v3_code_root))
    if assets_root:
        env.setdefault("V43_ASSET_ROOT", str(assets_root))
    procs = []
    for w in range(workers):
        sub = [r for i, r in enumerate(rows) if i % workers == w]
        if not sub:
            continue
        sub_in = chunks_dir / f"chunk_{w:02d}.input.jsonl"
        with sub_in.open("w", encoding="utf-8") as f:
            for r in sub:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)
                        + "\n")
        log = (chunks_dir / f"chunk_{w:02d}.log").open("wb")
        procs.append((w, subprocess.Popen(
            [sys.executable, "-c", _ENGINE_CHUNK_ENTRY,
             str(sub_in), str(chunks_dir / f"chunk_{w:02d}.jsonl"),
             str(top_k)],
            stdout=log, stderr=log, env=env, cwd=str(repo_root))))
    fail = []
    for w, p in procs:
        code = p.wait()
        if code != 0:
            fail.append(w)
    if fail:
        raise ExamError(f"引擎臂分片失败:{fail}",
                        {"chunks": fail})
    # 归并:冻结 input_index 顺序
    merged = {}
    for w in range(workers):
        p = chunks_dir / f"chunk_{w:02d}.jsonl"
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                merged[rec["qid"]] = rec
    out_path = out_dir / "engine_results.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(merged[r["qid"]],
                               ensure_ascii=False, sort_keys=True) + "\n")
    n_ok = sum(1 for r in rows
               if merged[r["qid"]].get("status") == "ok")
    meta = {
        "schema_version": EXAM_SCHEMA_VERSION,
        "kind": "engine_arm_results",
        "n_questions": len(rows),
        "n_status_ok": n_ok,
        "n_empty_or_failed": len(rows) - n_ok,
        "workers": workers,
        "top_k": top_k,
        "engine_results_sha256": _sha256_file(out_path),
        "exam_inputs_sha256": _sha256_file(exam_inputs_path),
        "all_rows_kept": True,
    }
    (out_dir / "engine_arm_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    return meta


# ---------------------------------------------------------------- agent 臂


def _exam_manifest(rows: list[dict], exam_inputs_sha: str) -> dict:
    """白名单 → BatchCoordinator manifest(route_id = qid,显式映射)。"""
    return {
        "schema_version": EXAM_SCHEMA_VERSION,
        "kind": "batch_input_manifest",
        "split": EXAM_SPLIT_NAME,
        "route_order": [r["qid"] for r in rows],
        "routes": [{"route_id": r["qid"],
                    "root_smiles": r["substrate_smiles"],
                    "root_smiles_sha256": hashlib.sha256(
                        r["substrate_smiles"].encode("utf-8")).hexdigest()}
                   for r in rows],
        "source": {"exam_inputs_sha256": exam_inputs_sha},
        "whitelist_fields": ["root_smiles", "root_smiles_sha256",
                             "route_id"],
        "gold_fields_excluded": True,
    }


def run_exam_agent(*, batch_root: Path, exam_inputs_path: Path,
                   runs_root: Path, config: dict, model_choice: str = "real",
                   env_file: str | None = None,
                   workers: int = EXAM_WORKERS,
                   max_in_flight: int = EXAM_MAX_IN_FLIGHT) -> dict:
    """agent 臂:单步预算 + 40 worker + max_in_flight=40 共享闸门。"""
    from .adapters.llm_client import real_provider_env
    from .batch import (
        BatchCoordinator, batch_identity_conflict_check, build_batch_identity,
        load_env_file, run_id_for_route,
    )
    from .output.export_v3 import load_export_policy

    batch_root = Path(batch_root)
    runs_root = Path(runs_root)
    exam_inputs_path = Path(exam_inputs_path)
    rows = load_exam_inputs(exam_inputs_path)
    manifest = _exam_manifest(rows, _sha256_file(exam_inputs_path))
    config = json.loads(json.dumps(config))
    config["rate"]["max_in_flight"] = max_in_flight
    export_policy = load_export_policy(
        config.get("export_policy_overrides") or {})

    model_block: dict = {}
    if model_choice == "fake":
        model_block = {"provider": "fake", "model_id": "fake-scripted-v1",
                       "request_params": {}, "timeout_s": 0.0}
    elif model_choice == "off":
        raise ExamError("外考 agent 臂必须是真实模型(不提供 off 模式)",
                        {"model_choice": model_choice})
    else:
        if env_file:
            os.environ.update(load_env_file(env_file))
        env = real_provider_env()
        missing = [k for k, ok in (
            ("V43_LLM_BASE_URL", env["base_url_set"]),
            ("V43_LLM_API_KEY", env["api_key_set"]),
            ("V43_LLM_MODEL", env["model_set"]),
        ) if not ok]
        if missing:
            return {"status": "not_run:no_credentials_or_access",
                    "missing_env": missing}
        from .adapters.llm_client import resolve_model_setup

        setup = resolve_model_setup(
            "openai_compatible",
            request_params=config["model_request_params"],
            timeout_s=config["llm_timeout_s"])
        required = config.get("provider_price_snapshot", {}).get("model_id")
        if required and setup.model_id != required:
            return {"status": "not_run:model_id_mismatch",
                    "required": required, "actual": setup.model_id}
        model_block = {"provider": "openai_compatible",
                       "model_id": setup.model_id,
                       "request_params": dict(setup.request_params),
                       "timeout_s": float(setup.timeout_s)}

    # exam manifest 落盘后构建批次身份(与 dev 同一身份机制)
    manifest_path = batch_root / "input_manifest.json"
    batch_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    identity = build_batch_identity(
        split=EXAM_SPLIT_NAME, input_manifest_path=manifest_path,
        config=config, provider=model_block["provider"],
        model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"],
        export_policy=export_policy)
    batch_identity_conflict_check(batch_root, identity)
    (batch_root / "batch_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")

    coordinator = BatchCoordinator(
        batch_root=batch_root, runs_root=runs_root, manifest=manifest,
        identity=identity, config=config,
        provider=model_block["provider"], model_id=model_block["model_id"],
        request_params=model_block["request_params"],
        timeout_s=model_block["timeout_s"], export_policy=export_policy,
        max_parallel=int(config.get("max_parallel", workers)),
        poll_interval_s=float(config.get("poll_interval_s", 10.0)),
        worker_wall_clock_cap_s=float(
            config.get("worker_wall_clock_cap_s", 8 * 3600)),
        max_worker_respawns=int(config.get("max_worker_respawns", 2)),
    )
    terminal = coordinator.run_to_completion()
    run_ids = [run_id_for_route(identity["short"], EXAM_SPLIT_NAME, rid)
               for rid in manifest["route_order"]]
    return {
        "batch_short": identity["short"],
        "n_questions": len(rows),
        "terminal_states": terminal,
        "run_ids": run_ids,
        "batch_root": str(batch_root),
        "runs_root": str(runs_root),
    }


# ---------------------------------------------------------------- 在途证据


def inflight_evidence(runs_root: Path, run_ids: list[str]) -> dict:
    """响应产物 → 每请求 (sent, done, request_id, status, usage) 表 +
    峰值同时在途数(仅提供方正常响应计入;闸门拒绝/失败不计)。

    口径(2026-09-29 K2 固定为半开区间):区间为
    ``[sent_at_epoch, done_at_epoch)``;同一时刻的事件先处理完成
    (done, -1)再处理发出 (sent, +1),即边界相接的两个区间不计重叠。
    ``sent_at_epoch``/``done_at_epoch`` 是 epoch 墙钟时间戳
    (``time.time()``);单调时钟仅用于 ``elapsed_s`` 计时,不参与排序。
    """
    spans = []
    n_failed = 0
    for run_id in run_ids:
        results = Path(runs_root) / run_id / "results"
        if not results.is_dir():
            continue
        for task_dir in sorted(results.iterdir()):
            for rp in sorted(task_dir.glob("prediction_response.*.json")):
                try:
                    payload = json.loads(
                        rp.read_text(encoding="utf-8")).get("payload", {})
                except Exception:
                    continue
                transport = payload.get("transport") or {}
                if transport.get("ok") is not True \
                        or transport.get("status") != 200:
                    n_failed += 1
                    continue
                sent = transport.get("sent_at_epoch")
                done = transport.get("done_at_epoch")
                if sent is None or done is None:
                    continue
                spans.append({
                    "run_id": run_id, "task_id": task_dir.name,
                    "sent_at": sent, "done_at": done,
                    "request_id": transport.get("request_id"),
                    "status": transport.get("status"),
                    "usage": transport.get("usage") or {},
                })
    events: list[tuple[float, int]] = []
    for s in spans:
        events.append((s["sent_at"], 1))
        events.append((s["done_at"], -1))
    # 半开区间 [sent, done):同一时刻先处理完成(-1)再处理发出(+1),
    # 边界相接的两个区间不计入同时在途。
    events.sort(key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _, delta in events:
        cur += delta
        peak = max(peak, cur)
    return {
        "n_provider_ok_responses": len(spans),
        "n_failed_or_rejected": n_failed,
        "peak_in_flight_provider_ok": peak,
        "requests": spans,
        "note": ("峰值按请求发出/响应结束的 epoch 墙钟时间戳以半开区间"
                 "[sent_at_epoch, done_at_epoch)重叠计算,同一时刻先处理"
                 "完成再处理发出;限流拒绝、连接失败与本地排队不计入达标峰值"),
    }


# ---------------------------------------------------------------- 冻结评分器

SCORER_VERSION = "v43-ec298-scorer-1"


def _cn(identity_module, smiles: str) -> str | None:
    return identity_module.cn_identity(smiles)


def score_exam(*, agent_predictions_path: str | Path,
               engine_results_path: str | Path | None,
               gold_questions_path: str | Path,
               out_path: str | Path) -> dict:
    """冻结判分(零 LLM;金标仅在此处打开)。

    - 主指标 hit@1/3/5,分母恒为 298(空/部分/失败行计入);
    - 每 agent_rank 之外另报 engine_rank(引擎臂 Top-10 内);
    - 三档(新引擎完整候选池,判分后诊断):Top-10 已含金标 / 池内
      Top-10 外 / 池内无金标。
    """
    from .domain import identity as identity_module

    gold: dict[str, dict] = {}
    for line in Path(gold_questions_path).read_text(
            encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        gold[rec["qid"]] = rec

    per_question = []
    n = 0
    pred_path = Path(agent_predictions_path)
    engine = {}
    if engine_results_path and Path(engine_results_path).is_file():
        for line in Path(engine_results_path).read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                engine[rec["qid"]] = rec
    for line in pred_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n += 1
        row = json.loads(line)
        qid = row["route_id"]
        if qid not in gold:
            raise ExamError("答卷 qid 不在金标(判分失败)",
                            {"qid": qid})
        products = []
        for step in row.get("steps", []):
            products.extend(step.get("predicted_products", []))
        gold_products = gold[qid].get("products_smiles", [])
        # 首个命中 rank:有序候选逐一 cn 身份,命中任一金标即取该名次
        gold_ids = set()
        for p in gold_products:
            ident = _cn(identity_module, p)
            if ident:
                gold_ids.add(ident)
        rank = None
        seen: set[str] = set()
        r = 0
        for p in products:
            r += 1
            ident = _cn(identity_module, p)
            if ident is None or ident in seen:
                continue
            seen.add(ident)
            if ident in gold_ids and rank is None:
                rank = r
        engine_rank = None
        pool_tier = None
        eng = engine.get(qid)
        if eng and eng.get("status") == "ok":
            er = 0
            seen_e: set[str] = set()
            for entry in eng.get("top10", []):
                er += 1
                ident = entry.get("product_identity")
                if not ident or ident in seen_e:
                    continue
                seen_e.add(ident)
                if ident in gold_ids:
                    engine_rank = er
                    break
            pool_ids = set()
            for ident in eng.get("pool_identities", []):
                if ident:
                    pool_ids.add(ident)
            hit_identities = gold_ids & pool_ids
            if engine_rank is not None:
                pool_tier = "gold_in_top10"
            elif hit_identities:
                pool_tier = "gold_in_pool_beyond_top10"
            else:
                pool_tier = "gold_not_in_pool"
        per_question.append({
            "qid": qid,
            "category": gold[qid].get("category"),
            "n_gold_products": len(gold_products),
            "agent_rank": rank,
            "engine_rank": engine_rank,
            "pool_tier": pool_tier,
            "n_predicted": len(products),
        })
    total = len(per_question)

    def hits(k: int, key: str) -> int:
        return sum(1 for q in per_question
                   if q[key] is not None and q[key] <= k)

    summary = {
        "schema_version": EXAM_SCHEMA_VERSION,
        "scorer_version": SCORER_VERSION,
        "identity": "cn (v3 eawag_lookup._cn_identity 同口径:"
                    "charge-normalized stereo-blind)",
        "n_questions": total,
        "agent": {"hit@1": hits(1, "agent_rank"),
                  "hit@3": hits(3, "agent_rank"),
                  "hit@5": hits(5, "agent_rank"),
                  "hit@10": hits(5, "agent_rank"),
                  "hit@10_note": "agent 每步最多报告五个候选,"
                                 "hit@10 恒等于 hit@5(输出宽度上限,"
                                 "不代表第 6-10 位性能)",
                  "n_miss": sum(1 for q in per_question
                                if q["agent_rank"] is None)},
        "engine_top10": {"hit@1": hits(1, "engine_rank"),
                         "hit@3": hits(3, "engine_rank"),
                         "hit@5": hits(5, "engine_rank"),
                         "hit@10": hits(10, "engine_rank"),
                         "n_miss": sum(1 for q in per_question
                                       if q["engine_rank"] is None)},
        "pool_tiers": {
            "gold_in_top10": sum(1 for q in per_question
                                 if q["pool_tier"] == "gold_in_top10"),
            "gold_in_pool_beyond_top10": sum(
                1 for q in per_question
                if q["pool_tier"] == "gold_in_pool_beyond_top10"),
            "gold_not_in_pool": sum(1 for q in per_question
                                    if q["pool_tier"] == "gold_not_in_pool"),
        },
        "paired_delta_note": "逐题配对净增减见 per_question "
                             "(agent_rank/engine_rank 比较)",
    }
    result = {"summary": summary, "per_question": per_question}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    os.replace(tmp, out_path)
    return result
