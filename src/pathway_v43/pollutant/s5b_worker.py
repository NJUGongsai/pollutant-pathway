"""S5b worker —— 一题一进程的 PPV1 run 执行入口(编排器子进程)。

``python -m pathway_v43.pollutant.s5b_worker --batch-root R --runs-root
D --qid Q``(由 s5b_orchestrator 派生;OMP_NUM_THREADS=1)。

职责:

- 装配批根冻结的 profile_policy(单步预算;十上限 + 格式反馈策略);
- 装配 RealModelAdapter(凭证只从 env ``V43_LLM_*``;调用账本落
  run 目录);
- run 不存在 ⇒ ``start_ppv1_run``;已存在 ⇒ ``resume_ppv1_run``
  (幂等续跑;身份核对/冻结计划/恢复全走公共链);
- 结束(成功或失败)落终态 case 文件 ``cases/<qid>.json``:
  stop_reason/endpoint 四分账/export_digest/模型调用与 usage 汇总
  (从 ledger model_requests 表与调用账本复算,不信内存);
- worker 自身不判分、不碰金标(金标只在 s5b_scoring 判分进程)。

崩溃语义:进程死亡 ⇒ 无 case 文件 ⇒ 编排器记失败补位(留分母);
重跑同批 ⇒ resume 续跑(B1–B4 公共恢复)。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

S5B_WORKER_VERSION = "s5b-worker-1"

# R4:case 载荷 schema(编排器 validated case reader 校验同一常量)
S5B_CASE_SCHEMA_VERSION = "s5b-case-1"


def worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="s5b_worker")
    parser.add_argument("--batch-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--qid", required=True)
    parser.add_argument(
        "--evidence-card-flag", choices=["true", "false"], default=None,
        help="可信批上下文显式传预期开关(协调者派发恒传,取冻结副本"
             "同值;缺席 = 手动/测试直连路径,显式进手动模式)")
    parser.add_argument("--fail-fast-env-check", action="store_true",
                        help="只做凭证存在性检查(冒烟段 0 前置)")
    args = parser.parse_args(argv)
    batch_root = Path(args.batch_root)
    runs_root = Path(args.runs_root)
    qid = str(args.qid)
    expected_flag = ({"true": True, "false": False}
                     [args.evidence_card_flag]
                     if args.evidence_card_flag is not None else None)
    sys.path.insert(0, str(_repo_src_path(batch_root)))

    from pathway_v43.config import resolve_config
    from pathway_v43.adapters.rate_gate import GateCorrupt
    from pathway_v43.pollutant.real_model import (
        RealModelAdapter,
        RealModelNotConfigured,
        S5B_CALL_ACCOUNT_FILE,
    )
    from pathway_v43.pollutant.runflow import (
        PPV1RunError,  # noqa: F401 —— 失败包装的公共类型(文档性导入)
        resume_ppv1_run,
        start_ppv1_run,
    )
    from pathway_v43.workflow.runner import RunAlreadyExists  # noqa: F401

    run_input = json.loads(
        (batch_root / "run_inputs" / f"{qid}.json").read_text(
            encoding="utf-8"))
    run_id = str(run_input["run_id"])
    plan = dict(run_input.get("plan") or {})
    profile_policy = json.loads(
        (batch_root / "profile_policy.json").read_text(encoding="utf-8"))
    import os

    # ---- chain14:批级证据卡开关(worker 侧同判据核对;先于任何
    # run 启动/发送)。单一验证源 load_evidence_card_flag:冻结副本
    # 缺键/坏值 ⇒ 结构化失败 case(fail-closed,不当缺省)。
    # chain14 P1-4(2026-10-16 Codex 代审回修):可信批上下文(协调者
    # 派发,--evidence-card-flag 显式传预期 bool)下**冻结副本必须在位
    # 且同值** —— 缺席=拒(evidence_card_frozen_copy_missing,不回退;
    # 旧实现 None→True 让"已冻结 A 丢副本"静默变 B 错账),同值核过
    # 才放行;换臂(预期≠冻结副本)=拒(evidence_card_flag_mismatch)。
    # 手动/测试直连路径(未传预期值)且副本缺席 ⇒ 显式进手动模式
    # (现行行为 on;case 以 evidence_card_mode 披露,不冒充冻结批)。 ----
    from pathway_v43.pollutant.s5b_orchestrator import (
        load_evidence_card_flag,
    )

    try:
        frozen_flag = load_evidence_card_flag(batch_root)
    except Exception as exc:  # noqa: BLE001 —— 冻结副本缺键/坏值先拒
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "failed",
            "failure_kind": "evidence_card_flag_invalid",
            "error": f"批级证据卡开关装载失败:{exc}"[:300],
            "detail": dict(getattr(exc, "detail", {}) or {}),
        })
        return 5
    evidence_card_mode = "frozen_batch"
    if expected_flag is not None:
        # 可信批上下文:预期 bool 由协调者从冻结参数显式传入
        if frozen_flag is None:
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": "evidence_card_frozen_copy_missing",
                "error": ("可信批上下文预期开关已显式传入而批根冻结副本"
                          "缺席(orchestration.json 不在;已冻结 A/B 丢副本"
                          "≠手动批,缺席=拒不回退 —— P1-4 fail-closed)"),
                "detail": {"kind": "evidence_card_frozen_copy_missing",
                           "expected_evidence_card_enabled":
                               bool(expected_flag)},
            })
            return 5
        if frozen_flag != expected_flag:
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": "evidence_card_flag_mismatch",
                "error": ("可信批上下文预期开关与冻结副本不一致(换臂拒;"
                          "A/B 唯一差分变量中途换臂禁止)"),
                "detail": {"kind": "evidence_card_flag_mismatch",
                           "expected_evidence_card_enabled":
                               bool(expected_flag),
                           "frozen_evidence_card_enabled":
                               bool(frozen_flag)},
            })
            return 5
        evidence_card_enabled = frozen_flag
    elif frozen_flag is None:
        # 手动/测试直连路径(无协调者、无冻结副本):显式进手动模式,
        # 现行行为 on(case 披露,不冒充冻结批)
        evidence_card_enabled = True
        evidence_card_mode = "manual_no_frozen_copy"
    else:
        evidence_card_enabled = frozen_flag

    stub_path = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    if stub_path:
        # scripted 模型桩(测试/冒烟:与真实适配器同一取响应调用序;
        # provider_kind 按 plan 注册 ⇒ scripted 网络 0、不占真实额度;
        # 不冒充在线模型验证)
        from pathway_v43.pollutant.real_model import (
            S5B_CALL_ACCOUNT_FILE,
            ScriptedRealModelAdapter,
        )

        stub = json.loads(Path(stub_path).read_text(encoding="utf-8"))
        model = ScriptedRealModelAdapter(
            strategy=str(stub.get("strategy") or "first_pool"),
            responses=[str(r) for r in (stub.get("responses") or [])],
            fail_with=dict(stub.get("fail_with") or {}),
            call_account_path=runs_root / run_id / S5B_CALL_ACCOUNT_FILE)
    else:
        from pathway_v43.pollutant.real_model import (
            RealModelAdapter,
            RealModelNotConfigured,
            S5B_CALL_ACCOUNT_FILE,
        )

        try:
            model = RealModelAdapter.from_env(
                call_account_path=runs_root / run_id /
                S5B_CALL_ACCOUNT_FILE)
        except RealModelNotConfigured as exc:
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": "model_not_configured",
                "error": str(exc), "detail": dict(exc.detail),
            })
            return 2
        except GateCorrupt as exc:
            # v3-R2 残余 C:worker 侧存储冻结块首消费 —— 客户端闸门
            # 装配(打开既有 gate 状态)即发现存储派生 bound/hash 与
            # 同源重算不一致 ⇒ 结构化失败 case(失败题留分母,零发送;
            # 保全坏记录,身份摘要重算正常不能洗掉存储坏字段)
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": "budget_guard_invalid",
                "error": f"闸门金额守卫存储冻结块校验失败:{exc}"[:300],
                "detail": dict(getattr(exc, "detail", {}) or {}),
            })
            return 5
        # ---- S5B-V3-02:real 批金额守卫先于传输核(worker 公开入口) ----
        # 公共链的守卫 = 协调者写入闸门状态文件的冻结配置(worker 经
        # V43_LLM_RATE_GATE 装配);本核对闭合"绕开编排器手动起 worker"
        # 的口子:real 批无闸门/无金额配置/配置与批根 budget_guard.json
        # 不一致 ⇒ 先拒(失败题留分母,不发送)。
        guard_verdict = _verify_budget_guard(
            batch_root, model, manifest_provider_kind(
                batch_root / "batch_manifest.json"))
        if guard_verdict is not None:
            _write_case(batch_root, {
                "qid": qid, "run_id": run_id, "status": "failed",
                "failure_kind": guard_verdict["failure_kind"],
                "error": guard_verdict["error"],
                "detail": guard_verdict.get("detail") or {},
            })
            return 5
    if args.fail_fast_env_check:
        # R4:env_check_only **另文件**(cases/env_check/ 之下),不写
        # 正式 completed 终态(不占 298 终态、不进 SKIP/汇总/评分面)
        _write_env_check_case(batch_root, {
            "qid": qid, "run_id": run_id,
            "case_schema_version": S5B_CASE_SCHEMA_VERSION,
            "status": "env_check_only",
            "note": "仅凭证存在性检查(worker --fail-fast-env-check);"
                    "另文件承载,不是正式 completed 终态",
        })
        return 0
    config = resolve_config()
    run_dir = runs_root / run_id
    try:
        if (run_dir / "run_identity.json").is_file():
            # chain14 P1-3(2026-10-16 Codex 代审回修):resume 签名无
            # profile_policy 参数 —— 旧实现传 profile_policy=None 使
            # 合法中断 run 被TypeError 写成失败终态。profile 策略在
            # start 时已冻结进 run 身份,resume 只核对不重传。
            summary = resume_ppv1_run(
                config=config, runs_root=runs_root, run_id=run_id,
                model=model, evidence_card_enabled=evidence_card_enabled)
        else:
            summary = start_ppv1_run(
                config=config, runs_root=runs_root, run_id=run_id,
                smiles=str(run_input["substrate_smiles"]), plan=plan,
                model=model, profile_policy=profile_policy,
                evidence_card_enabled=evidence_card_enabled)
    except RunAlreadyExists as exc:  # 并发同 run 罕见:失败补位
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "failed",
            "failure_kind": "run_already_exists",
            "error": str(exc)[:300],
        })
        return 3
    except Exception as exc:  # noqa: BLE001 —— 失败题留分母,如实记录
        # 任何 run 级失败:失败题留分母;如实记录结构化原因
        detail = dict(getattr(exc, "detail", {}) or {})
        _write_case(batch_root, {
            "qid": qid, "run_id": run_id, "status": "failed",
            "failure_kind": str(detail.get("kind") or
                                type(exc).__name__),
            "error": f"{type(exc).__name__}: {exc}"[:400],
            "evidence_card_enabled": bool(evidence_card_enabled),
            "evidence_card_mode": evidence_card_mode,
            "model_calls": _count_model_calls(run_dir),
            "model_call_retries": _count_model_retries(run_dir),
            "usage": _usage_summary(run_dir),
        })
        return 4
    _write_case(batch_root, {
        "qid": qid,
        "run_id": run_id,
        "case_schema_version": S5B_CASE_SCHEMA_VERSION,
        "status": "completed",
        "stop_reason": str(summary.get("stop_reason") or ""),
        "run_error": dict(
            (summary.get("stop") or {}).get("run_error") or {}),
        "endpoint": dict(summary.get("endpoint") or {}),
        "endpoint_status": str(
            (summary.get("endpoint") or {}).get("status") or ""),
        "export_digest": str(
            (summary.get("native_export") or {}).get("export_digest")
            or ""),
        "counts": dict(summary.get("counts") or {}),
        # chain14 披露:本 run 消费的证据卡开关(A/B 唯一差分变量)+
        # 开关装载模式(冻结批同值核过 / 手动无冻结副本显式披露)+
        # transport 重试计数(每次 HTTP 尝试 = 一次 issued 请求)
        "evidence_card_enabled": bool(evidence_card_enabled),
        "evidence_card_mode": evidence_card_mode,
        "model_calls": _count_model_calls(run_dir),
        "model_call_retries": _count_model_retries(run_dir),
        "usage": _usage_summary(run_dir),
    })
    return 0


def _repo_src_path(batch_root: Path) -> Path:
    """仓 src 路径(worker 与 src 同仓部署;沿 tests 惯例插入)。"""
    return Path(__file__).resolve().parents[2]


def manifest_provider_kind(manifest_path: Path) -> str:
    """批清单声明的 provider_kind(real=付费 HTTP 发送链)。"""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "real"  # 清单不可读 ⇒ 保守按 real(缺预算配置同样先拒)
    return str(manifest.get("provider_kind") or "real")


def _verify_budget_guard(batch_root: Path, model,
                         provider_kind: str) -> dict | None:
    """S5B-V3-02:real 批 worker 侧金额守卫核对(先于传输)。

    返回 None = 通过;返回 dict = 结构化拒(失败题留分母,零发送):
    - 无闸门(bypass 协调者)⇒ budget_guard_missing;
    - 闸门无金额配置 ⇒ budget_guard_missing;
    - 闸门配置 config_sha256 ≠ 批根 budget_guard.json ⇒
      budget_guard_mismatch(不静默混用两套价格/帽);
    - **P4c no-cap(2026-10-12 用户决定)**:闸门无金额配置而批根有
      合法 ``budget_no_cap.json`` 标记 ⇒ **通过**(金额检查显式跳过;
      调用数门/速率门/并发门在闸门照常生效;同判据
      ``load_budget_no_cap_marker``,坏标记 fail-closed 拒,标记+
      数值闸门并存 ⇒ mismatch 拒)。
    scripted 桩路径不经本核对(网络 0;provider_kind≠real)。"""
    if provider_kind != "real":
        return None
    gate = getattr(getattr(model, "client", None), "gate", None)
    if gate is None:
        return {
            "failure_kind": "budget_guard_missing",
            "error": ("real 批 worker 无批级闸门(V43_LLM_RATE_GATE 缺"
                      "席;金额硬帽不经协调者冻结 ⇒ 先于传输拒,零发送)"),
            "detail": {"kind": "budget_guard_missing"},
        }
    try:
        cost_config = gate.cost_guard_summary()
    except Exception as exc:  # noqa: BLE001 —— GateCorrupt 同样先拒
        return {
            "failure_kind": "budget_guard_invalid",
            "error": f"闸门金额守卫配置坏形状:{exc}"[:300],
            "detail": dict(getattr(exc, "detail", {}) or {}),
        }
    from pathway_v43.pollutant.s5b_orchestrator import (
        load_budget_no_cap_marker,
    )

    try:
        no_cap_marker = load_budget_no_cap_marker(batch_root)
    except Exception as exc:  # noqa: BLE001 —— 坏标记 fail-closed 先拒
        return {
            "failure_kind": "budget_guard_invalid",
            "error": f"批级 no-cap 标记坏形状:{exc}"[:300],
            "detail": dict(getattr(exc, "detail", {}) or {}),
        }
    if cost_config is None:
        if no_cap_marker is None:
            return {
                "failure_kind": "budget_guard_missing",
                "error": ("闸门状态无金额守卫配置(real 批每次付费发送前"
                          "必须原子预留;未经 s5b_cli budget 冻结 ⇒ 先拒)"),
                "detail": {"kind": "budget_guard_missing"},
            }
        # P4c:no-cap 显式标记在案(用户决定)⇒ 金额检查跳过;调用数门
        # (gate.max_calls)/速率门/并发门不受影响;usage(token/调用数)
        # 照记(s5b_real_calls.jsonl 账本/批报告 account)。
        return None
    if no_cap_marker is not None:
        return {
            "failure_kind": "budget_guard_mismatch",
            "error": ("闸门含数值金额配置而批根带 no-cap 标记(互斥冲突;"
                      "单一事实源破裂,先于传输拒,零发送)"),
            "detail": {"kind": "budget_guard_mismatch",
                       "no_cap_marker": no_cap_marker.get("marker")},
        }
    from pathway_v43.pollutant.s5b_orchestrator import (
        S5B_BUDGET_GUARD_FILE,
    )

    budget_path = batch_root / S5B_BUDGET_GUARD_FILE
    if not budget_path.is_file():
        return {
            "failure_kind": "budget_guard_missing",
            "error": (f"批根缺 {S5B_BUDGET_GUARD_FILE}(real 批发车硬"
                      "门;先于传输拒)"),
            "detail": {"kind": "budget_guard_missing",
                       "expected_file": str(budget_path)},
        }
    from pathway_v43.pollutant.s5b_orchestrator import (
        load_budget_guard,
    )

    try:
        batch_config = load_budget_guard(batch_root)
    except Exception as exc:  # noqa: BLE001 —— 坏配置同样先拒
        return {
            "failure_kind": "budget_guard_invalid",
            "error": f"批根金额守卫配置坏形状:{exc}"[:300],
            "detail": {"kind": "budget_guard_invalid"},
        }
    if batch_config is None or \
            str(batch_config.get("config_sha256")) != \
            str(cost_config.get("config_sha256")):
        return {
            "failure_kind": "budget_guard_mismatch",
            "error": ("闸门冻结金额配置与批根 budget_guard.json 不一致"
                      "(单一事实源破裂;不静默混用,先于传输拒)"),
            "detail": {
                "kind": "budget_guard_mismatch",
                "gate_config_sha256": str(
                    cost_config.get("config_sha256")),
                "batch_config_sha256": str(
                    (batch_config or {}).get("config_sha256")),
            },
        }
    return None


def _count_model_calls(run_dir: Path) -> int:
    db = run_dir / "pollutant.sqlite"
    if not db.is_file():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM model_requests").fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def _count_model_retries(run_dir: Path) -> int:
    """chain14:transport 重试计数(model_requests 中 retry_of != ''
    的行;每次重试 = 一次显式新 issued 请求,诚实计数)。"""
    db = run_dir / "pollutant.sqlite"
    if not db.is_file():
        return 0
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM model_requests WHERE"
                " retry_of != ''").fetchone()
            return int(row[0] or 0)
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def _usage_summary(run_dir: Path) -> dict:
    """从逐调用账本复算 usage(known 小计;缺 usage 保守预留)。"""
    path = run_dir / "s5b_real_calls.jsonl"
    summary = {"present": False, "input_tokens": 0, "output_tokens": 0,
               "total_tokens": 0, "calls_with_usage": 0,
               "calls_without_usage": 0}
    if not path.is_file():
        return summary
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            status = str(record.get("status") or "")
            if status not in ("responded", "failed"):
                continue
            usage = record.get("usage") or {}
            if usage:
                summary["present"] = True
                summary["calls_with_usage"] += 1
                summary["input_tokens"] += int(
                    usage.get("input_tokens") or 0)
                summary["output_tokens"] += int(
                    usage.get("output_tokens") or 0)
                summary["total_tokens"] += int(
                    usage.get("total_tokens") or 0)
            else:
                summary["calls_without_usage"] += 1
    except (ValueError, OSError):
        return summary
    return summary


def _write_case(batch_root: Path, payload: dict) -> None:
    """终态 case 原子落盘(R4:tmp + os.replace + case schema 版本)。"""
    import os

    from pathway_v43.domain.models import now_iso

    path = batch_root / "cases" / f"{payload['qid']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("case_schema_version", S5B_CASE_SCHEMA_VERSION)
    payload["worker_version"] = S5B_WORKER_VERSION
    payload["recorded_at"] = now_iso()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_env_check_case(batch_root: Path, payload: dict) -> None:
    """R4:env check 结果另文件(cases/env_check/ 之下;不进正式终态)。"""
    import os

    from pathway_v43.domain.models import now_iso

    path = batch_root / "cases" / "env_check" / f"{payload['qid']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["worker_version"] = S5B_WORKER_VERSION
    payload["recorded_at"] = now_iso()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


if __name__ == "__main__":  # pragma: no cover —— 子进程入口
    raise SystemExit(worker_main())
