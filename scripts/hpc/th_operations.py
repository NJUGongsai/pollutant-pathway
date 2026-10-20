#!/usr/bin/env python
"""T-H r2 操作入口；不改科学判据，不调用模型（phase 的一次恢复除外）。"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

OUTPUTS = ("metrics.json", "report.md", "report_plain.md")
STABLE_FIELDS = (
    "data_scope", "domain_tag", "denominator", "main_caliber",
    "old_caliber_sensitivity", "old_caliber_anyof_multicomponent",
    "buckets", "aggregate_diagnosis", "run_status_table", "criteria_v2",
    "per_qid", "evaluator_pairing_bases", "caliber_policy",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                              indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preserve(source, target):
    """相同内容可复用；任何不同的既有证据不覆盖。"""
    source, target = Path(source), Path(target)
    if target.exists():
        if source.read_bytes() != target.read_bytes():
            raise RuntimeError(f"既有产物不同，保全并停：{target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as out:
        out.write(source.read_bytes())


def mutable(batch):
    if batch.name == "t_h_s5b_298_20261020":
        raise RuntimeError("旧事故批只读，不得由本入口改写")
    if any((batch / name).exists() for name in
           ("SEALED", ".sealed", "sealed.json", "th_sealed.json")):
        raise RuntimeError("批根已有封存标识，不再执行写操作")


@contextmanager
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def registered(batch, label="full"):
    manifest = read(batch / "batch_manifest.json")
    entries = {str(e["qid"]): e for e in manifest["entries"]}
    order = [str(q) for q in manifest["registration_order"]]
    if label in ("smoke2", "smoke10"):
        order = order[:2 if label == "smoke2" else 10]
    return manifest, entries, order


def case_failure(case):
    text = json.dumps({key: case.get(key) for key in
                       ("failure_kind", "error", "run_error", "stderr_tail")},
                      ensure_ascii=False).lower()
    return case.get("status") == "failed" or bool(case.get("run_error")), text


def snapshot(batch, runs, qid, run_id, case, label, attempt):
    target = batch / "monitoring" / qid / f"attempt{attempt}"
    target.mkdir(parents=True, exist_ok=False)
    preserve(batch / "cases" / f"{qid}.json", target / "case.json")
    run_dir = runs / run_id
    if run_dir.is_dir():
        shutil.copytree(run_dir, target / "run", symlinks=True)
    for name in ("orchestration.json", "profile_policy.json",
                 "budget_no_cap.json", "batch_report.json", "progress.json"):
        if (batch / name).is_file():
            preserve(batch / name, target / name)
    if (batch / "gate").is_dir():
        shutil.copytree(batch / "gate", target / "gate", symlinks=True)
    job_id = os.environ.get("SLURM_JOB_ID", "")
    log = Path.cwd() / f"th_run_{job_id}.out"
    if job_id and log.is_file():
        preserve(log, target / log.name)
    write(target / "evidence.json", {
        "recorded_at": now(), "phase": label, "qid": qid,
        "run_id": run_id, "case_sha256": sha(target / "case.json"),
        "failure_kind": case.get("failure_kind"),
        "note": "完整现场在本目录；不删改 runstate/driver；不是 flake 放行",
    })
    return target


def phase_guard(batch, runs, env_file, label, wrapper_status=0):
    """仅明确恢复/崩溃家族同题同参重试一次；其它失败留证停报。"""
    mutable(batch)
    from chain13_run_wrapper import CHAIN13_PROFILE
    from pathway_v43.pollutant.s5b_orchestrator import run_s5b_batch, summarize_batch
    with lock(batch / ".th_phase.lock"):
        manifest, entries, order = registered(batch, label)
        register_path = batch / "monitoring" / "failure_register.json"
        registry = read(register_path) if register_path.exists() else {}
        unresolved = []
        if wrapper_status:
            stage = batch / "monitoring" / f"{label}_wrapper_{os.environ.get('SLURM_JOB_ID', 'manual')}"
            stage.mkdir(parents=True, exist_ok=True)
            for name in ("orchestration.json", "profile_policy.json", "batch_report.json",
                         "progress.json", "budget_no_cap.json"):
                if (batch / name).is_file():
                    preserve(batch / name, stage / name)
            log = Path.cwd() / f"th_run_{os.environ.get('SLURM_JOB_ID', '')}.out"
            if log.is_file():
                preserve(log, stage / log.name)
            write(stage / "failure.json", {"wrapper_exit_code": wrapper_status,
                                          "phase": label, "recorded_at": now(),
                                          "note": "非零先留证，guard 后停止；不自动改配置"})
        for qid in order:
            case_path = batch / "cases" / f"{qid}.json"
            if not case_path.is_file():
                if wrapper_status:
                    continue
                raise RuntimeError("阶段终态缺失，停止，不猜测恢复")
            case = read(case_path)
            failed, text = case_failure(case)
            if not failed:
                continue
            record = registry.setdefault(qid, {"retry_count": 0,
                                                "evidence": []})
            attempt = len(record["evidence"]) + 1
            evidence = snapshot(batch, runs, qid, str(entries[qid]["run_id"]),
                                case, label, attempt)
            record["evidence"].append(str(evidence))
            record["last_phase"] = label
            record["last_status"] = "failed_retained"
            write(register_path, registry)
            if "unregistered_cx_class" in text:
                record["last_status"] = "hard_stop_cx"
                write(register_path, registry)
                raise RuntimeError("出现 unregistered_cx_class，完整现场已保全，立即停报 CC")
            recovery = any(marker in text for marker in
                           ("recover", "resume", "crash", "ledgerrolledback",
                            "worker_exit_without_case", "worker_timeout_killed"))
            unsafe_retry = any(marker in text for marker in
                               ("identity", "integrity", "schema", "budget",
                                "mismatch", "frozen", "artifact", "configured",
                                "forbidden", "unauthorized", "permission"))
            if not recovery and not unsafe_retry:
                record["last_status"] = "other_failed_terminal_registered"
                write(register_path, registry)
                continue
            if wrapper_status:
                unresolved.append(qid)
                continue
            if not recovery or unsafe_retry or record["retry_count"] >= 1:
                unresolved.append(qid)
                continue
            # 已保全完整 run/日志/state/validation 后，只移动失败 case。
            # 公共 qids 执行域 + worker 的 run_identity→resume 路径；
            # 没有修改 runstate、driver 或任何冻结身份。
            record["retry_count"] = 1
            record["last_status"] = "retry_started"
            write(register_path, registry)
            case_path.rename(evidence / "case.original.json")
            try:
                run_s5b_batch(
                    batch, runs_root=runs, env_file=env_file, workers=8,
                    max_in_flight=8, gate_rpm=200, gate_tpm=3_000_000,
                    gate_max_calls=4470, profile_policy=CHAIN13_PROFILE,
                    evidence_card_enabled=False, qids=[qid])
            finally:
                if not case_path.exists():
                    shutil.copyfile(evidence / "case.original.json", case_path)
            retried = read(case_path)
            again, after = case_failure(retried)
            record["last_status"] = "retry_failed" if again else "retry_recovered"
            write(register_path, registry)
            if "unregistered_cx_class" in after:
                raise RuntimeError("重试出现 CX，停止；原现场已保全")
            if again:
                retry_evidence = snapshot(batch, runs, qid, str(entries[qid]["run_id"]),
                                          retried, label, len(record["evidence"]) + 1)
                record["evidence"].append(str(retry_evidence))
                write(register_path, registry)
                unresolved.append(qid)
        status = {"phase": label, "checked": len(order),
                  "unresolved_failures": len(unresolved), "recorded_at": now(),
                  "zero_cx": True, "failure_register": str(register_path)}
        status["wrapper_exit_code"] = wrapper_status
        status["passed"] = not unresolved and not wrapper_status
        if unresolved or wrapper_status:
            write(batch / f"th_{label}_status.json", status)
            raise RuntimeError(f"{len(unresolved)} 件失败已留证登记，停止并报 CC；不静默 flake 放行")
        # 单题重试会把 batch_report 写成单题视角；恢复本阶段汇总。
        report = read(batch / "batch_report.json") if (batch / "batch_report.json").exists() else {}
        report.update(summarize_batch(batch, order))
        write(batch / "batch_report.json", report)
        write(batch / f"th_{label}_status.json", status)
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))


def probe(batch):
    mutable(batch)
    _, entries, order = registered(batch)
    total = {"files": len(order), "specs_total": 0, "remap_applied": 0,
             "remap_add_atom_ge1": 0, "remap_add_atom_ge2": 0}
    by_channel, by_qid = {}, {}
    for qid in order:
        run_input = read(batch / entries[qid]["run_input_rel"])
        counts = {"remap": 0, "add": 0, "add_multi": 0}
        for specs in (run_input.get("plan", {}).get("pools") or {}).values():
            for spec in specs:
                total["specs_total"] += 1
                remap = spec.get("template_remap") or {}
                if not remap.get("applied"):
                    continue
                n_add = sum(e.get("op") == "add_atom" for e in spec.get("edits") or [])
                channel = str(spec.get("key") or "unknown").split(":", 1)[0]
                row = by_channel.setdefault(channel, {"remap": 0, "add": 0,
                                                       "add_multi": 0})
                for key, amount in (("remap", 1), ("add", int(n_add >= 1)),
                                    ("add_multi", int(n_add >= 2))):
                    counts[key] += amount
                    row[key] += amount
        if counts["remap"]:
            by_qid[qid] = counts
        total["remap_applied"] += counts["remap"]
        total["remap_add_atom_ge1"] += counts["add"]
        total["remap_add_atom_ge2"] += counts["add_multi"]
    result = {**total, "questions_remap": len(by_qid),
              "questions_with_add": sum(v["add"] > 0 for v in by_qid.values()),
              "questions_with_multi_add": sum(v["add_multi"] > 0 for v in by_qid.values()),
              "by_channel": by_channel, "by_qid": by_qid,
              "note": "298 post-hoc；只读本批 run_inputs.plan.pools；非成绩/化学有效性证明"}
    write(batch / "p2_face_measure.json", result)
    print(json.dumps(total, sort_keys=True))


def prepare(batch, records):
    mutable(batch)
    if not (batch / "build_identity.json").is_file():
        raise RuntimeError("缺 build_identity.json；build 完成前不创建 r2 旁件")
    if not isinstance(read(batch / "build_identity.json"), dict):
        raise RuntimeError("build_identity.json 不可作为旁块消费")
    registered(batch)  # build 完成前不创建任何 r2 旁件。
    approval = read(records / "preregistration_approval.json")
    for info in approval["preregistration_docs"].values():
        source = records / Path(info["path"]).name
        if sha(source) != info["sha256"]:
            raise RuntimeError("原批准文本快照 sha 不符，不重写审批")
        preserve(source, batch / "record" / "approved_text" / source.name)
    for name in ("preregistration_approval.json", "budget_no_cap.json"):
        preserve(records / name, batch / name)
    write(batch / "record" / "r2_operations.json", {
        "source_commit": "c360e7428a9b765636922282f27c65e917071460",
        "original_approval_sha256": sha(records / "preregistration_approval.json"),
        "authority": "docs/HANDOFF_T_H_RELAUNCH_2026-10-20.md §3；CC 见放行自动续跑",
        "note": "原审批未修改；r2 操作补充，不是新预注册或代签",
        "batch_root": str(batch), "prepared_at": now()})
    probe(batch)


def score_all(batch, runs, scorer=None):
    mutable(batch)
    phase_status = batch / "th_full_status.json"
    if phase_status.exists() and not read(phase_status).get("passed"):
        raise RuntimeError("full 阶段已有明确异常停点，不继续 score")
    with lock(batch / ".th_score.lock"):
        done = batch / "th_score_complete.json"
        if done.exists():
            receipt = read(done)
            if not all((batch / name).is_file() and sha(batch / name) == value
                       for name, value in receipt["outputs_sha256"].items()):
                raise RuntimeError("评分完成标识与现存产物不符，留证停报")
            print("TH-SCORE-ALREADY-COMPLETE")
            return
        if scorer is None:
            from pathway_v43.pollutant.s5b_scoring import score_s5b_batch
            from chain13_gate import score_gate
            if score_gate(str(batch)):
                raise RuntimeError("全 qid 未终态，不判分")
            scorer = score_s5b_batch
        aggregates = {}
        for version in ("v1", "v3", "v2"):
            aggregate = scorer(batch, runs_root=runs, data_scope="real",
                               criteria_version=f"ppv1-criteria-{version}")
            aggregates[version] = aggregate
            for name in OUTPUTS:
                preserve(batch / name, batch / f"{name}.{version}")
        v3, v2 = aggregates["v3"], aggregates["v2"]
        disclosure = v3.get("criteria_v3") or {}
        if (disclosure.get("tier") != "disclosure_only"
                or disclosure.get("strict_promotion") is not False
                or disclosure.get("hit_at_1_effect") != "none"
                or disclosure.get("tautomer_promoted_nodes") != []):
            raise RuntimeError("V3 披露档断言失败，已保留三版现场，不封存")
        differences = [key for key in STABLE_FIELDS if v3.get(key) != v2.get(key)]
        if differences:
            write(batch / "th_score_difference.json", {"stable_field_differences": differences})
            raise RuntimeError("V3/V2 稳定科学字段出现差异，停止交付")
        write(batch / "criteria_v3_disclosure.json", disclosure)
        names = [f"{name}.{version}" for version in ("v1", "v2", "v3")
                 for name in OUTPUTS] + list(OUTPUTS) + ["criteria_v3_disclosure.json"]
        receipt = {"completed_at": now(), "headline": "ppv1-criteria-v2",
                   "disclosure": "ppv1-criteria-v3; disclosure_only; no hit uplift",
                   "stable_fields_compared": list(STABLE_FIELDS),
                   "stable_field_differences": differences,
                   "other_different_fields": sorted(key for key in set(v3) | set(v2)
                                                  if key not in STABLE_FIELDS and v3.get(key) != v2.get(key)),
                   "outputs_sha256": {name: sha(batch / name) for name in names}}
        write(done, receipt)
        print("TH-SCORE-PASS: v1/v3/v2 preserved; root headline=v2; V3 no uplift")


def active_job(job_id):
    result = subprocess.run(["squeue", "-h", "-j", str(job_id), "-o", "%T"],
                            check=True, capture_output=True, text=True)
    return result.stdout.strip()


def launch(args):
    batch, runs, ws, code = args.batch_root, args.runs_root, args.ws, args.code
    mutable(batch)
    state_path = ws / "operations" / f"{batch.name}.json"
    with lock(state_path.with_suffix(".lock")):
        state = read(state_path) if state_path.exists() else {"jobs": {}}
        if state.get("pending_submission"):
            raise RuntimeError("此前提交意图尚无可靠作业号；先核 squeue/sacct，禁止盲重投")
        prior = state["jobs"].get(args.phase)
        if prior and active_job(prior["job_id"]):
            print(json.dumps({"status": "already_queued_or_running", **prior}))
            return
        if args.phase == "build":
            if (batch / "batch_manifest.json").exists():
                print("TH-BUILD-ALREADY-PRESENT: 不覆盖，请核 build gate 后 prepare")
                return
            if batch.exists() and any(batch.iterdir()):
                raise RuntimeError("r2 批根已有不完整资料，保全停报，不覆盖 build")
        elif args.phase == "run":
            for name in ("batch_manifest.json", "build_identity.json",
                         "preregistration_approval.json", "budget_no_cap.json",
                         "p2_face_measure.json"):
                if not (batch / name).is_file():
                    raise RuntimeError(f"run 前置缺 {name}")
            if (batch / "th_full_status.json").exists() and read(batch / "th_full_status.json").get("passed"):
                print("TH-RUN-ALREADY-COMPLETE: 进入 score，不重复发车")
                return
            # 已终态但未获 T-H guard 认证时只复核，不能再次发模型请求。
            _, _, order = registered(batch)
            if all((batch / "cases" / f"{q}.json").is_file() and
                   read(batch / "cases" / f"{q}.json").get("status") in
                   ("completed", "failed") for q in order):
                print("TH-RUN-TERMINAL: 先执行 phase --label full 复核，禁止重复发车")
                return
        else:
            if (batch / "th_score_complete.json").exists():
                print("TH-SCORE-ALREADY-COMPLETE")
                return
            if not (batch / "th_full_status.json").is_file() or not read(batch / "th_full_status.json").get("passed"):
                raise RuntimeError("score 前先取得 T-H full 门通过记录")
        if prior and not args.resume:
            raise RuntimeError("本阶段已有结束作业；先核日志/门，必要时显式 --resume 同参重投")
        if prior and sum(item["phase"] == args.phase for item in state.get("history", [])) >= 2:
            raise RuntimeError("本阶段同参重投已用一次，连续失败停报 CC")
        env = dict(os.environ, WS=str(ws), CODE=str(code), BATCH_ROOT=str(batch),
                   RUNS_ROOT=str(runs), BATCH_TAG="t-h-s5b-298-20261020r2")
        state["pending_submission"] = {"phase": args.phase, "recorded_at": now(),
                                       "batch_root": str(batch),
                                       "note": "提交前落意图；无可靠 job_id 时先核调度器，不盲重投"}
        write(state_path, state)
        result = subprocess.run(["sbatch", "--parsable", "--export=ALL",
                                 f"--job-name=th-r2-{args.phase}",
                                 str(code / "scripts/hpc" / f"sbatch_th_{args.phase}.sh")],
                                cwd=code, env=env, check=True,
                                capture_output=True, text=True)
        job_id = result.stdout.strip().split(";", 1)[0]
        if not job_id.isdigit():
            raise RuntimeError("sbatch 作业号不可解析，保留输出并核 squeue，不盲重投")
        record = {"job_id": job_id, "phase": args.phase, "submitted_at": now(),
                  "batch_root": str(batch), "runs_root": str(runs)}
        state["jobs"][args.phase] = record
        state.setdefault("history", []).append(record)
        state.pop("pending_submission", None)
        write(state_path, state)
        print(json.dumps(record, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("phase", "probe", "prepare", "score", "launch", "prebuild", "check-mutable"))
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--label", choices=("smoke2", "smoke10", "full"), default="full")
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--phase", choices=("build", "run", "score"))
    parser.add_argument("--ws", type=Path, default=Path.home() / "ppv1_hpc")
    parser.add_argument("--code", type=Path, default=Path.home() / "EnzymeAgent/v43cTH")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--wrapper-status", type=int, default=0)
    args = parser.parse_args()
    if args.command in ("phase", "score", "launch") and args.runs_root is None:
        parser.error("此命令必须显式 --runs-root")
    if args.command == "phase":
        if args.env_file is None:
            parser.error("phase 必须给同一 --env-file")
        phase_guard(args.batch_root, args.runs_root, args.env_file, args.label, args.wrapper_status)
    elif args.command == "probe":
        probe(args.batch_root)
    elif args.command == "prepare":
        if args.record_dir is None:
            parser.error("prepare 必须给原批准快照 --record-dir")
        prepare(args.batch_root, args.record_dir)
    elif args.command == "score":
        score_all(args.batch_root, args.runs_root)
    elif args.command in ("prebuild", "check-mutable"):
        mutable(args.batch_root)
        if args.command == "prebuild" and args.batch_root.exists() and any(args.batch_root.iterdir()):
            raise RuntimeError("新 build 批根非空，保全停报；不覆盖")
    else:
        if args.phase is None:
            parser.error("launch 必须给 --phase")
        launch(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"TH-OPERATIONS-STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
