"""工作流节点 — 每个副作用都以 task_id 幂等(恢复重放安全)。

任务书 §2/§4 的关键幂等点:
- retrieve_reactions:重放时先读 results/<task_id>/retrieval.json,命中即
  复用,不重新检索(真实检索计数器不增);
- commit_pathway:PathwayStore.submit_event 同幂等键重放返回已提交结果,
  不重复入账;同键不同内容由 EventConflict 拒绝;
- call_model:调用前查同键预测产物(prediction.json / response.aN);
  请求先落 issued 调用记录再发外部请求 —— "请求已发出但响应未落盘"的
  悬空状态以 prediction_orphan.aN 审计卡如实记录后重试,不声称恰好一次。

崩溃注入(crash_after)仅供恢复测试使用:在指定节点副作用落盘后、
LangGraph 写下个 checkpoint 前以 os._exit(70) 硬杀进程。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..domain import pathway as pw
from ..domain.identity import cn_identity
from ..domain.models import (
    PATH_STATUS_AWAITING_PREDICTION,
    PATH_STATUS_DEAD_END,
    PATH_STATUS_DEPTH_LIMIT,
    EVIDENCE_KIND_NOVEL,
    EVIDENCE_KIND_RECORDED,
    PREDICTION_MODE_ANALOGY,
    PREDICTION_MODE_NOVEL,
    PREDICTION_MODE_RANK,
    STRATEGY_VERSION,
    stable_id,
)
from ..domain.policy import (
    PREDICTION_POLICY_DEFAULTS,
    classify_evidence as classify_evidence_policy,
    decide_prediction_route,
    schedule_products,
    select_frontier,
    stop_reason,
)
from ..services.prediction import (
    ParsedPrediction,
    PredictionTaskError,
    build_prediction_task,
    build_proposed_card,
    parse_model_response,
    prediction_task_id,
    sibling_task_block,
    task_input_hash,
    task_user_payload,
)
from ..services.reaction_finder import ReactionContext
from ..services.report_adjudication import (
    REPORT_ADJUDICATION_POLICY_DEFAULTS,
    STAGE_FINAL,
    adjudicate_parent,
    cardval_artifact_name,
    validate_adjudication_payload,
    validate_card_for_reporting,
)
from ..storage.pathway_store import PathwayStore
from ..validation.gates import (
    gate_atom_mapping_declared,
    gate_direction_source,
    gate_recorded_eligibility,
    gate_smiles,
    validate_event_products,
)
from .state import WorkflowState


@dataclass
class Services:
    """节点共享的服务束(存储/产物/检索/模型 + 身份与测试钩子)。"""

    store: PathwayStore
    artifacts: object                    # ArtifactStore
    finder: object                       # ReactionFinder
    runs_dir: str
    asset_identity: dict                 # retrieval_asset_identity / scripted
    strategy: dict                       # max_depth / max_expansions / max_frontier_width
    model: object | None = None          # ModelSetup | None(off/未配置)
    crash_after: str | None = None       # 测试注入点

    @property
    def prediction_policy(self) -> dict:
        return (self.model.policy if self.model is not None
                else PREDICTION_POLICY_DEFAULTS)

    @property
    def model_enabled(self) -> bool:
        return self.model is not None and self.model.provider != "off"


def task_id_for(svc: Services, path_id: str, phase: str, substrate_identity: str) -> str:
    """任务幂等键:run_id + path_id + phase + 规范输入 + 资产/策略版本。"""
    return stable_id(
        "T", svc.store.current_run() or "", path_id, phase, substrate_identity,
        STRATEGY_VERSION, svc.asset_identity.get("manifest_sha256", ""),
        svc.asset_identity.get("source_file_sha256", ""),
    )


def _maybe_crash(svc: Services, node_name: str) -> None:
    if svc.crash_after == node_name:
        # 测试注入:硬杀进程,不留 checkpoint(模拟副作用落盘后中断)
        os._exit(70)


def _read_decision(svc: Services, decision_task_id: str) -> dict:
    return svc.artifacts.read(decision_task_id, "decision")["payload"]


def _novel_dead_route(svc: Services, state: WorkflowState, mode: str) -> bool:
    """novel 弃权/失败 = dead_end 的判据(call_model 与 apply_prediction 共用)。

    报告 §12.5 设计决策:无证据(dead_end)路径上的 novel 弃权/失败记
    dead_end,而非 awaiting。call_model 正常路径与崩溃恢复重放路径
    (prediction.json 已落盘、checkpoint 未写 → apply_prediction 接手落账)
    必须用同一判据,保证同一局面不因崩溃时点不同产生两种账本状态。
    """
    decision = _read_decision(svc, state["decision_task_id"])
    return (decision.get("outcome") == "dead_end"
            and mode == PREDICTION_MODE_NOVEL)


# ---------------------------------------------------------------- 节点


def normalize_input(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        smiles = state["root_smiles"]
        ok, reason = gate_smiles(smiles)
        if not ok:
            return {
                "phase": "failed",
                "stop_reason": "invalid_input",
                "error": {"gate": "smiles", "message": reason},
            }
        root_cn = cn_identity(smiles) or smiles
        root_pid = svc.store.ensure_run(run_id, smiles, root_cn)
        return {
            "root_cn": root_cn,
            "active_path_id": root_pid,
            "graph_revision": svc.store.graph_revision(),
        }

    return node


def select_frontier_node(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        if state.get("phase") == "failed":
            return {"phase": "export"}
        run_id = state["run_id"]
        budget = _refresh_budget(svc, state)
        # 深度到限的 frontier 路径先明示为 depth_limit(状态分清,不隐瞒)
        for path in svc.store.list_frontier(run_id):
            if path.depth >= budget["max_depth"]:
                svc.store.set_path_status(
                    path.path_id, PATH_STATUS_DEPTH_LIMIT,
                    f"depth_limit:{path.depth}>={budget['max_depth']}",
                )
        frontier = svc.store.list_frontier(run_id)
        nxt, note = select_frontier(
            [p.to_dict() for p in frontier],
            budget["used_expansions"], budget["max_expansions"],
            budget["max_depth"],
        )
        if nxt is None:
            return {"phase": "export", "active_path_id": "", "budget": budget}
        return {
            "active_path_id": nxt["path_id"],
            "active_substrate_identity": nxt["substrate_identity"],
            "phase": "explore",
            "budget": budget,
            # 迭代隔离:进入新路径前清空上一路径的预测/裁决草稿引用。
            # (真实事故:predicted_evidence_id 跨迭代泄漏 → 下一路径
            #  validate/commit 误入提案卡分支 KeyError,或更糟 —— 静默
            #  提交错误证据卡。State 引用必须随迭代重置。)
            "retrieval_task_id": "",
            "retrieval_reused": False,
            "decision_task_id": "",
            "validation_task_id": "",
            "adjudication_task_id": "",
            "prediction_mode": "",
            "prediction_task_id": "",
            "prediction_response_ref": "",
            "predicted_evidence_id": "",
            "prediction_failed": False,
            "last_outcome": "",
        }

    return node


def _refresh_budget(svc: Services, state: WorkflowState) -> dict:
    """预算记账以持久事实源为准(检索产物数 / 调用记录数 / 提案事件数)。"""
    budget = dict(state["budget"])
    budget["used_expansions"] = svc.artifacts.count_retrievals()
    budget["used_llm_calls"] = svc.artifacts.count_llm_calls()
    budget["used_proposals"] = svc.store.count_events_by_kind(
        EVIDENCE_KIND_NOVEL)
    budget.setdefault("max_llm_calls", 0)
    budget.setdefault("used_llm_calls", 0)
    budget.setdefault("max_proposals", 0)
    budget.setdefault("used_proposals", 0)
    return budget


def retrieve_reactions(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        task_id = task_id_for(svc, path_id, "retrieval", substrate_identity)
        budget = _refresh_budget(svc, state)
        existing = svc.artifacts.read(task_id, "retrieval")
        if existing is None:
            path = svc.store.get_path(path_id)
            ancestry = pw.ancestry_chain_records(svc.store, path_id)
            ctx = ReactionContext(
                run_id=run_id, path_id=path_id,
                substrate_smiles=path.substrate_identity,  # 服务层按身份检索
                substrate_identity=path.substrate_identity,
                ancestry=ancestry,
            )
            envelope = svc.finder.find(ctx)
            svc.artifacts.write(task_id, "retrieval", envelope)
            _maybe_crash(svc, "retrieve_reactions")  # 检索已落盘,checkpoint 未写
        # 预算记账以持久事实为准(已落盘检索产物数):恢复重放不丢计数,
        # 也不会因复用产物而漏记本次展开(P1 修复:此前重放路径会突破预算)
        budget["used_expansions"] = svc.artifacts.count_retrievals()
        return {
            "retrieval_task_id": task_id,
            "retrieval_reused": existing is not None,
            "budget": budget,
            "phase": "classify",
        }

    return node


def classify_evidence(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        envelope = svc.artifacts.read(state["retrieval_task_id"], "retrieval")
        task_id = task_id_for(svc, path_id, "decision", substrate_identity)
        # 幂等重放:decision 已落盘(如供体裁决后硬杀的恢复)→ 原样复用,
        # 不重写不可变产物(created_at 变化会造成 ArtifactConflict)
        existing = svc.artifacts.read(task_id, "decision")
        if existing is not None:
            payload = existing["payload"]
            return {
                "decision_task_id": task_id,
                "last_outcome": payload["outcome"],
                "prediction_mode": payload.get("prediction_mode", ""),
                "budget": _refresh_budget(svc, state),
            }
        decision = classify_evidence_policy(
            envelope["payload"]["evidences"], run_id, path_id, substrate_identity
        )
        # Phase C:供体适用性资格(确定性纯函数;来源找回 ≠ 迁移资格)。
        # 仅当存在预测性证据时计算并随 decision 不可变落盘;recorded-only
        # 的 decision 载荷保持原形状(旧审计兼容)。
        # Phase D D1:reactant_similar 通道按当前底物召回相似供体(相似度
        # 只决定召回次序;资格仍走全部门禁),与卡内 donor_refs 去重合并。
        eligibility = None
        if any(e.get("kind") in ("rule_application", "analog_reaction")
               and e.get("condition_fit") != "conflict"
               for e in envelope["payload"]["evidences"]):
            from ..services.analog_source import similar_donor_refs
            from ..services.donor_applicability import (
                ApplicabilityPolicy, build_eligibility,
            )

            pol = svc.prediction_policy
            threshold = float(pol.get("reactant_similar_threshold", 0.0))
            top_k = int(pol.get("reactant_similar_top_k", 0))
            if not pol.get("reactant_similar_enabled", True):
                threshold, top_k = 0.0, 0
            resolver = getattr(svc.finder, "analog_resolver", None)
            similar_refs = similar_donor_refs(
                resolver, substrate_identity,
                threshold=threshold, top_k=top_k)
            from ..services.analog_source import SIMILARITY_VERSION

            eligibility = build_eligibility(
                envelope["payload"]["evidences"], substrate_identity,
                ApplicabilityPolicy(
                    max_donor_candidates=int(
                        pol.get("max_analogy_donor_candidates", 3)),
                    similarity_threshold=threshold if similar_refs else 0.0,
                    similarity_top_k=top_k if similar_refs else 0,
                    similarity_version=(
                        SIMILARITY_VERSION if similar_refs else ""),
                ),
                similar_refs=similar_refs,
            )
            decision.analogy_eligibility = eligibility
        # 预测协议路由(任务书 §2;确定性纯函数;模型未配置→空,走原语义)
        budget = _refresh_budget(svc, state)
        path = svc.store.get_path(path_id)
        mode, route_reason = decide_prediction_route(
            decision.outcome,
            envelope["payload"]["evidences"],
            substrate_identity,
            svc.prediction_policy,
            model_enabled=svc.model_enabled,
            llm_remaining=int(budget.get("max_llm_calls", 0))
            - int(budget.get("used_llm_calls", 0)),
            proposals_remaining=int(budget.get("max_proposals", 0))
            - int(budget.get("used_proposals", 0)),
            eligibility=eligibility,
        )
        decision.prediction_mode = mode
        decision.prediction_reason = route_reason
        svc.artifacts.write(task_id, "decision", decision.to_dict())
        _maybe_crash(svc, "classify_evidence")  # 供体裁决已落盘,checkpoint 未写
        return {
            "decision_task_id": task_id,
            "last_outcome": decision.outcome,
            "prediction_mode": mode,
            "budget": budget,
        }

    return node


# ------------------------------------------------------- 预测分支(§2/§4)


def _prediction_task_id(svc: Services, state: WorkflowState, mode: str,
                        retrieval_payload: dict,
                        retrieval_payload_hash: str) -> str:
    model_block = svc.model.identity_block() if svc.model else {}
    return prediction_task_id(
        run_id=state["run_id"], path_id=state["active_path_id"],
        substrate_identity=state["active_substrate_identity"],
        retrieval_payload_hash=retrieval_payload_hash, mode=mode,
        model_id=model_block.get("model_id", ""),
        prompt_versions=model_block.get("prompt_versions", {}),
        policy_version=svc.prediction_policy.get("policy_version", ""),
        strategy_version=STRATEGY_VERSION,
    )


def prepare_prediction(svc: Services) -> Callable[[WorkflowState], dict]:
    """组装 PredictionTask(完整祖先链+证据+预算+兄弟)并落盘(不可变)。"""
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        mode = state["prediction_mode"]
        retrieval_env = svc.artifacts.read(state["retrieval_task_id"], "retrieval")
        payload = retrieval_env["payload"]
        r_hash = retrieval_env["payload_hash"]
        task_id = _prediction_task_id(svc, state, mode, payload, r_hash)
        existing = svc.artifacts.read(task_id, "prediction_task")
        if existing is None:
            path = svc.store.get_path(path_id)
            molecule_render = None
            # Phase C:analogy 资格块随 decision 不可变落盘,这里只读传递
            eligibility = None
            if mode == PREDICTION_MODE_ANALOGY:
                decision_env = svc.artifacts.read(
                    state["decision_task_id"], "decision")
                eligibility = (decision_env["payload"] or {}).get(
                    "analogy_eligibility")
                from ..services.atom_tool import AtomToolError, roundtrip

                try:
                    render = roundtrip(path.substrate_identity, name="S")
                except AtomToolError as exc:
                    # 表示有损:类比编辑不可能,如实停待预测(拒因留痕)
                    return _hold_or_dead(
                        svc, state, f"representation_lossy:{exc.reason}",
                        outcome_on_dead="dead_end",
                    )
                molecule_render = {
                    "molecode": render.molecode,
                    "atom_ids": render.atom_ids,
                    "canonical_smiles": render.canonical_smiles,
                }
            try:
                task = build_prediction_task(
                    store=svc.store, run_id=run_id, path_id=path_id,
                    substrate_identity=substrate_identity,
                    substrate_smiles=path.substrate_identity,
                    root_smiles=state["root_smiles"], mode=mode,
                    retrieval_payload=payload, retrieval_payload_hash=r_hash,
                    conditions=payload.get("conditions"),
                    model_block=(svc.model.identity_block() if svc.model
                                 else {}),
                    policy=svc.prediction_policy,
                    budget={
                        **dict(state["budget"]),
                        "active_depth": path.depth if path else 0,
                    },
                    molecule_render=molecule_render,
                    # 已有兄弟路径(任务书 §2):同父已提交的其他产物路径
                    siblings=sibling_task_block(svc.store, path_id),
                    analogy_eligibility=eligibility,
                )
            except PredictionTaskError as exc:
                return _hold_or_dead(svc, state, f"task_error:{exc.reason}",
                                     outcome_on_dead="dead_end")
            task["task_ref"] = task_id
            task["input_hash"] = task_input_hash(task)
            svc.artifacts.write(task_id, "prediction_task", task)
            _maybe_crash(svc, "prepare_prediction")
        return {
            "prediction_task_id": task_id,
            "phase": "call_model",
        }

    return node


def _hold_or_dead(svc: Services, state: WorkflowState, reason: str,
                  outcome_on_dead: str = "awaiting") -> dict:
    """预测不可行的显式停留:留拒因,不假成功。"""
    status = (PATH_STATUS_AWAITING_PREDICTION if outcome_on_dead == "awaiting"
              else PATH_STATUS_DEAD_END)
    svc.store.set_path_status(state["active_path_id"], status, reason[:300])
    return {"phase": "select", "last_outcome": "prediction_unavailable",
            "prediction_mode": "", "prediction_failed": True}


def call_model(svc: Services) -> Callable[[WorkflowState], dict]:
    """外部调用(唯一出网点)+ 调用状态持久化 + 显式重试(任务书 §4)。

    同键重放:prediction.json 已存在 → 直接复用;response.aN 已存在 →
    不重新调用。悬空(请求已发出、响应未落盘)→ prediction_orphan.aN
    审计卡 + 重试为下一 attempt;重试总上限 = 1 + max_parse_retries。
    """
    def node(state: WorkflowState) -> dict:
        task_id = state["prediction_task_id"]
        mode = state["prediction_mode"]
        done = svc.artifacts.read(task_id, "prediction")
        if done is not None:
            return {"phase": "apply_prediction",
                    "prediction_response_ref": _resp_ref(done["payload"])}
        task_env = svc.artifacts.read(task_id, "prediction_task")
        task = task_env["payload"]
        candidate_ids = [c["evidence_id"] for c in task.get("candidates", [])]
        policy = svc.prediction_policy
        max_attempts = 1 + int(policy.get("max_parse_retries", 0))
        system_prompt = _prompt_for(svc, mode)

        attempt = 1
        parsed: ParsedPrediction | None = None
        while attempt <= max_attempts:
            resp_env = svc.artifacts.read(
                task_id, f"prediction_response.a{attempt}")
            if resp_env is None:
                call_env = svc.artifacts.read(
                    task_id, f"prediction_call.a{attempt}")
                if call_env is None:
                    # LLM 预算守卫:重试也是真实花费,发出前以持久计数核对
                    budget_now = _refresh_budget(svc, state)
                    if svc.artifacts.count_llm_calls() >= int(
                            budget_now.get("max_llm_calls", 0) or 0):
                        parsed = ParsedPrediction(
                            ok=False, mode=mode,
                            error_kind="llm_budget_exhausted",
                            error_message="调用预算已耗尽,不再发出新请求")
                        break
                    request_payload = {
                        "mode": mode, "task_id": task_id,
                        "input_hash": task.get("input_hash", ""),
                        "user_payload": task_user_payload(task),
                    }
                    from ..adapters.llm_client import request_hash

                    svc.artifacts.write(task_id, f"prediction_call.a{attempt}", {
                        "status": "issued",
                        "attempt": attempt,
                        "model": {"provider": svc.model.provider,
                                  "model_id": svc.model.model_id},
                        "request_hash": request_hash(request_payload),
                        "idempotency_key": f"{task_id}#a{attempt}",
                        "system_prompt_sha256": _sha_of(system_prompt),
                    })
                    _maybe_crash(svc, "call_model")  # 悬空注入点(请求已登记)
                    resp = svc.model.client.complete(
                        mode=mode, system_prompt=system_prompt,
                        user_payload=request_payload["user_payload"],
                        idempotency_key=f"{task_id}#a{attempt}",
                    )
                    parsed = parse_model_response(mode, resp.raw_text,
                                                  candidate_ids)
                    svc.artifacts.write(
                        task_id, f"prediction_response.a{attempt}", {
                            "status": ("completed" if resp.ok else
                                       "transport_failed"),
                            "attempt": attempt,
                            "transport": resp.to_dict(),
                            "parsed": parsed.to_dict(),
                        })
                    _maybe_crash(svc, "call_model_response")  # 响应已落盘
                else:
                    # 悬空:请求已登记但响应未落盘(前进程中断)——
                    # 如实写孤儿审计卡,再以下一 attempt 重试;
                    # 不声称恰好一次(任务书 §4)
                    svc.artifacts.write(
                        task_id, f"prediction_orphan.a{attempt}", {
                            "orphan": "request_issued_no_response",
                            "call_ref": f"prediction_call.a{attempt}",
                            "request_hash":
                                call_env["payload"].get("request_hash"),
                            "idempotency_key":
                                call_env["payload"].get("idempotency_key"),
                            "model": call_env["payload"].get("model"),
                            "disposition": (
                                f"retried_as_attempt_{attempt + 1}"
                                if attempt < max_attempts else
                                "no_retry_budget_left"
                            ),
                        })
                    if attempt >= max_attempts:
                        parsed = ParsedPrediction(
                            ok=False, mode=mode,
                            error_kind="dangling_call_no_retry_budget")
                        break
                    attempt += 1
                    continue
            else:
                parsed = ParsedPrediction(**resp_env["payload"]["parsed"])
            if parsed.ok:
                break
            if attempt >= max_attempts:
                break
            attempt += 1

        if parsed is None:  # 防御:不应到达
            parsed = ParsedPrediction(ok=False, mode=mode,
                                      error_kind="no_attempt")
        outcome, payload = _finalize_parsed(
            svc, state, task, task_id, parsed, attempt)
        svc.artifacts.write(task_id, "prediction", payload)
        _maybe_crash(svc, "prediction_recorded")
        budget = _refresh_budget(svc, state)
        if outcome in ("held", "abstained", "failed"):
            # 显式停留,不假成功:
            # - held → 待预测(证据在,模型暂缓);
            # - novel 弃权/失败且原决策是 dead_end → dead_end(不虚构进展);
            # - 其余失败/弃权 → 待预测(可审计后重试)。
            dead_route = _novel_dead_route(svc, state, mode)
            status = (PATH_STATUS_DEAD_END if dead_route
                      else PATH_STATUS_AWAITING_PREDICTION)
            if outcome == "held":
                reason = f"model_hold:{payload.get('reason', '')[:200]}"
            elif outcome == "abstained":
                reason = f"model_abstain:{payload.get('reason', '')[:200]}"
            else:
                reason = (f"prediction_failed:"
                          f"{payload.get('fail_reason', '')[:250]}")
            svc.store.set_path_status(state["active_path_id"], status,
                                      reason[:300])
            return {
                "phase": "select",
                "last_outcome": "prediction_unavailable",
                "prediction_mode": "",
                "prediction_failed": True,
                "prediction_response_ref": _resp_ref(payload),
                "budget": budget,
            }
        return {
            "phase": "apply_prediction",
            "prediction_response_ref": _resp_ref(payload),
            "budget": budget,
        }

    return node


def _resp_ref(payload: dict) -> str:
    return f"{payload.get('task_id', '')}#a{payload.get('attempt', 0)}"


def _sha_of(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prompt_for(svc: Services, mode: str) -> str:
    """按模式装载提示词(版本已在 ModelSetup 校验)。"""
    fname = {"rank_candidates": "ranker.md",
             "analogy_edit": "analogy_editor.md",
             "novel_proposal": "novel_proposal.md"}[mode]
    path = Path(svc.model.prompts_root) / fname
    return path.read_text(encoding="utf-8")


def _finalize_parsed(svc: Services, state: WorkflowState, task: dict,
                     task_id: str, parsed: ParsedPrediction,
                     attempt: int) -> tuple[str, dict]:
    """解析结果 → prediction.json(最终结构化预测;未通过的提案不入账)。"""
    base = {
        "schema_version": "v43-prediction-result-1",
        "task_kind": "prediction_result",
        "task_id": task_id,
        "task_ref": task_id,
        "run_id": state["run_id"],
        "path_id": state["active_path_id"],
        "mode": parsed.mode,
        "attempt": attempt,
        "parsed": parsed.to_dict(),
        "model": task.get("model", {}),
        "policy_version": task.get("policy_version", ""),
    }
    if not parsed.ok:
        base["outcome"] = "failed"
        base["fail_reason"] = f"{parsed.error_kind}:{parsed.error_message}"
        return "failed", base
    if parsed.mode == PREDICTION_MODE_RANK:
        if parsed.decision == "select":
            base["outcome"] = "selected"
            base["selected_evidence_id"] = parsed.selected_evidence_id
            base["order"] = parsed.order
            base["reasons"] = parsed.reasons
            return "selected", base
        base["outcome"] = "held"
        base["reason"] = parsed.reason
        return "held", base
    if parsed.mode == PREDICTION_MODE_ANALOGY:
        if parsed.decision == "abstain":
            base["outcome"] = "abstained"
            base["reason"] = parsed.reason
            return "abstained", base
        return _apply_analogy(svc, state, task, task_id, parsed, attempt, base)
    # novel_proposal
    if parsed.decision == "abstain" or not parsed.products:
        base["outcome"] = "abstained"
        base["reason"] = parsed.reason or "model_proposed_no_products"
        return "abstained", base
    return _apply_novel(state, task, task_id, parsed, attempt, base)


def _apply_analogy(svc: Services, state: WorkflowState, task: dict,
                   task_id: str, parsed: ParsedPrediction, attempt: int,
                   base: dict) -> tuple[str, dict]:
    """类比编辑(Phase C 编辑协议 v2;任务书 §4/C2/C3)。

    顺序:① referenced_evidence_id 与选定供体一致;② 编辑结构化校验;
    ③ 当前图副本上按列表顺序执行(逐步前提 + 最终 sanitize);
    ④ 目标 MoleCode 独立解析并与执行结果图逐项对账(canonical 终判);
    ⑤ 空 edits 仅当目标图==当前图且策略允许 no-op。任一步失败写结构化
    rejected(带操作索引/供体/对齐/资产引用),不假成功。通过的提案仍走
    既有 validate_event_products 全部门禁。
    """
    from ..services.atom_tool import (
        check_target_consistency,
        execute_edits,
        validate_edits,
    )

    donor_block = task.get("donor") or {}
    donor = donor_block.get("donor") or {}
    current_render = _real_render(state)
    checks = {
        "protocol_version": donor_block.get("edit_protocol_version", ""),
        "donor_reference": {
            "task_evidence_id": donor_block.get("evidence_id", ""),
            "record_id": donor.get("record_id", ""),
            "asset_file": donor.get("asset_file", ""),
            "asset_sha256": donor.get("asset_sha256", ""),
            "line_no": donor.get("line_no"),
        },
        "edit_validation": {"ok": False, "reasons": []},
        "edit_execution": {"ok": False, "reasons": []},
        "target_consistency": {"ok": False, "reasons": []},
    }

    def _reject(first_reason: str) -> tuple[str, dict]:
        base["outcome"] = "rejected"
        base["fail_reason"] = f"atomtool:{first_reason}"[:300]
        base["atomtool_checks"] = checks
        return "failed", base

    # ① 引用一致:模型引用的证据必须是任务书选定供体所属证据(不串线)
    if (parsed.referenced_evidence_id or "") \
            != donor_block.get("evidence_id", ""):
        checks["donor_reference"]["mismatch"] = {
            "model_referenced": parsed.referenced_evidence_id,
            "selected": donor_block.get("evidence_id", ""),
        }
        return _reject(
            f"donor_reference_mismatch:model={parsed.referenced_evidence_id!r}"
            f"_selected={donor_block.get('evidence_id', '')!r}")
    # ② 结构化校验(op/字段/引用/新 ID;拒因带 edit[i])
    val = validate_edits(current_render, parsed.edits)
    checks["edit_validation"] = val
    if not val["ok"]:
        return _reject(val["reasons"][0])
    # ③ 顺序执行(事务;键存在性/原键级在执行时点的图上核验)
    exe = execute_edits(current_render, parsed.edits)
    checks["edit_execution"] = {
        "ok": exe["ok"], "reasons": exe["reasons"],
        "product_smiles": exe.get("product_smiles", ""),
    }
    if not exe["ok"]:
        return _reject(exe["reasons"][0])
    # ④ 目标对账(独立解析目标文本 → ID 级图 + canonical SMILES)
    tgt = check_target_consistency(current_render, exe, parsed.target_molecode)
    checks["target_consistency"] = tgt
    if not tgt["ok"]:
        return _reject(tgt["reasons"][0])
    # ⑤ no-op 策略:空编辑仅当目标图与当前图确实相同且策略允许
    if not parsed.edits:
        if not svc.prediction_policy.get("allow_noop_edit", False):
            return _reject("noop_edit_not_allowed:empty_edits_rejected")
    product_smiles = exe["product_smiles"]
    products = [{
        "position": 0,
        "product_smiles": product_smiles,
        "product_smiles_full": product_smiles,
        "product_identity": cn_identity(product_smiles) or product_smiles,
        "score": 0.0,
        "score_semantics":
            "model_proposal_qualitative_only_no_calibrated_probability",
    }]
    card = build_proposed_card(
        run_id=state["run_id"], path_id=state["active_path_id"],
        substrate_identity=state["active_substrate_identity"],
        mode=PREDICTION_MODE_ANALOGY, parsed=parsed, task=task,
        task_id=task_id, products=products,
        donor_ref=donor_block.get("donor"), atomtool_checks=checks,
    )
    base.update({
        "outcome": "proposed",
        "proposed_card": card,
        "products_smiles": [p["product_smiles"] for p in products],
        "atomtool_checks": checks,
    })
    return "proposed", base


def _real_render(state: WorkflowState):
    """当前分子的真实 MoleculeRender(Analogy 编辑核验用)。"""
    from ..services.atom_tool import roundtrip

    return roundtrip(state["active_substrate_identity"], name="S")


def _apply_novel(state: WorkflowState, task: dict, task_id: str,
                 parsed: ParsedPrediction, attempt: int,
                 base: dict) -> tuple[str, dict]:
    """无证据提案:有序产物构造提案卡(门禁在 validate_products)。"""
    products = []
    for pos, p in enumerate(parsed.products):
        smi = p["smiles"]
        products.append({
            "position": pos,
            "product_smiles": smi,
            "product_smiles_full": smi,
            "product_identity": cn_identity(smi) or smi,
            "note": p.get("note", ""),
            "score": 0.0,
            "score_semantics":
                "model_proposal_qualitative_only_no_calibrated_probability",
        })
    card = build_proposed_card(
        run_id=state["run_id"], path_id=state["active_path_id"],
        substrate_identity=state["active_substrate_identity"],
        mode=PREDICTION_MODE_NOVEL, parsed=parsed, task=task,
        task_id=task_id, products=products,
    )
    base.update({
        "outcome": "proposed",
        "proposed_card": card,
        "products_smiles": [p["product_smiles"] for p in products],
    })
    return "proposed", base


def apply_prediction(svc: Services) -> Callable[[WorkflowState], dict]:
    """预测结果 → 选卡/提案入校验流;held/abstained/failed 显式停留。"""
    def node(state: WorkflowState) -> dict:
        task_id = state["prediction_task_id"]
        result = svc.artifacts.read(task_id, "prediction")["payload"]
        outcome = result.get("outcome")
        if outcome == "selected":
            return {
                "last_outcome": "commit_recorded",
                "predicted_evidence_id": result["selected_evidence_id"],
                "prediction_failed": False,
            }
        if outcome == "proposed":
            card = result["proposed_card"]
            return {
                "last_outcome": "commit_recorded",
                "predicted_evidence_id": card["evidence_id"],
                "prediction_failed": False,
            }
        # held / abstained / failed / rejected:显式停留,原因入账。
        # 本分支是崩溃恢复重放路径(prediction.json 已落盘而 checkpoint 未写,
        # call_model 直接 done→apply_prediction,跳过 finalize 落账)的唯一
        # 落账点:与 call_model 用同一判据,恢复确定性(修复前引用恒为空的
        # _novel_route,novel 弃权/失败被错标 awaiting_prediction)。
        if outcome == "held":
            reason = f"model_hold:{result.get('reason', '')[:200]}"
            status = PATH_STATUS_AWAITING_PREDICTION
        elif outcome == "abstained":
            reason = f"model_abstain:{result.get('reason', '')[:200]}"
            status = (PATH_STATUS_DEAD_END
                      if _novel_dead_route(svc, state,
                                           result.get("mode", ""))
                      else PATH_STATUS_AWAITING_PREDICTION)
        else:  # failed/rejected
            reason = f"prediction_failed:{result.get('fail_reason', '')[:250]}"
            status = (PATH_STATUS_DEAD_END
                      if _novel_dead_route(svc, state,
                                           result.get("mode", ""))
                      else PATH_STATUS_AWAITING_PREDICTION)
        svc.store.set_path_status(state["active_path_id"], status,
                                  reason[:300])
        return {"phase": "select", "last_outcome": "prediction_unavailable",
                "prediction_mode": "", "prediction_failed": True}

    return node


def _load_proposed_card(svc: Services, state: WorkflowState) -> dict:
    """从 prediction 产物取模型提案卡;缺失 = 结构化错误(不裸 KeyError)。"""
    task_id = state.get("prediction_task_id") or ""
    pred = svc.artifacts.read(task_id, "prediction") if task_id else None
    proposed = ((pred or {}).get("payload") or {}).get("proposed_card")
    if proposed is None:
        raise NodeStateError(
            "证据卡缺失:predicted_evidence_id 不在当前路径检索集,"
            "且预测产物无提案卡(可能是状态跨迭代泄漏)",
            {"path_id": state.get("active_path_id", ""),
             "evidence_id": state.get("predicted_evidence_id", ""),
             "prediction_task_id": task_id})
    return proposed


class NodeStateError(RuntimeError):
    """节点前置引用缺失(结构化;fail-closed,不含密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def validate_products_node(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        retrieval = svc.artifacts.read(state["retrieval_task_id"], "retrieval")["payload"]
        decision = _read_decision(svc, state["decision_task_id"])
        evidence_id = (state.get("predicted_evidence_id")
                       or decision.get("accepted_evidence_id"))
        card = next(
            (e for e in retrieval["evidences"]
             if e["evidence_id"] == evidence_id), None)
        card_in_retrieval = card  # 提案卡不在检索集;区分两条入口
        if card is None:
            # 模型提案卡:全文在 prediction.json(不可变产物)
            card = _load_proposed_card(svc, state)
        dir_ok, dir_reason = gate_direction_source(card)
        map_ok, map_reason = gate_atom_mapping_declared(card)
        # Phase B R1 修复:recorded 卡完整资格门禁(同底物/精确挂牌/条件;
        # 与任务候选筛选、路由、逐卡验证同一判据)—— 模型选中的脏卡
        # (异底物/方向错/donor 不精确)在此全部拒绝,不凭 evidence_id 升格
        elig_ok, elig_reason = gate_recorded_eligibility(card,
                                                         substrate_identity)
        # Phase C R2 复核:模型 rank 选择的检索层卡必须是 recorded。
        # 原始 rule/analog 卡各走 analogy_edit/novel 的适用性与编辑流程,
        # 不得因模型选择在验证层变成可提交产物(防御层:任务候选筛选与
        # 最终候选裁决之外再挡一道;提案卡不在检索集,不受此限)。
        if (state.get("predicted_evidence_id")
                and card_in_retrieval is not None
                and card_in_retrieval.get("kind") != EVIDENCE_KIND_RECORDED):
            elig_ok = False
            elig_reason = (
                "rank_selected_non_recorded:"
                f"kind={card.get('kind')};模型 rank 选择必须限于合格"
                "recorded 卡,原始规则/类比卡不得经 rank 直接提交")
        chain = pw.ancestry_chain(svc.store, path_id)
        ancestry_cns = pw.ancestry_identities(chain)
        children = svc.store.list_paths(run_id)
        sibling_cns = {
            p["substrate_identity"] for p in children
            if p["parent_path_id"] == path_id
        }
        # 模型提案加元素变化门禁(外源氧显式规则;recorded 不适用)
        check_elements = card.get("kind") == EVIDENCE_KIND_NOVEL or (
            card.get("kind") == "analog_reaction"
            and card.get("match_type") == "model_analogy_transfer"
        )
        verdicts = validate_event_products(
            evidence=card, ancestry_cns=ancestry_cns,
            existing_sibling_cns=sibling_cns,
            substrate_smiles=substrate_identity,
            check_elements=check_elements,
        )
        if not dir_ok:
            for v in verdicts:
                v.accepted = False
                v.reasons.insert(0, dir_reason)
        if not elig_ok:
            for v in verdicts:
                v.accepted = False
                v.reasons.insert(0, elig_reason)
        task_id = task_id_for(svc, path_id, "validation", substrate_identity)
        payload = {
            "evidence_id": card["evidence_id"],
            "evidence_kind": card.get("kind"),
            "predicted_by_model": bool(
                (card.get("source_record") or {}).get("predicted_by_model")),
            "gates": {
                "direction_source": {"ok": dir_ok, "reason": dir_reason},
                "atom_mapping": {"ok": map_ok, "reason": map_reason,
                                 "value": card.get("atom_mapping")},
                "recorded_eligibility": {"ok": elig_ok,
                                         "reason": elig_reason},
            },
            "verdicts": [v.to_dict() for v in verdicts],
            "n_accepted": sum(1 for v in verdicts if v.accepted),
            "n_total": len(verdicts),
        }
        svc.artifacts.write(task_id, "validation", payload)
        outcome = "commit_recorded" if payload["n_accepted"] > 0 else "dead_end"
        return {
            "validation_task_id": task_id,
            "last_outcome": outcome,
            "error": {} if (dir_ok and elig_ok) else {
                "gate": "recorded_eligibility" if not elig_ok
                else "direction_source",
                "message": elig_reason if not elig_ok else dir_reason},
        }

    return node


def adjudication_task_id_for(svc: Services, path_id: str,
                             substrate_identity: str) -> str:
    """候选裁决任务幂等键:裁决策略版本进入键(Phase B §3.5)。"""
    return stable_id(
        "T", svc.store.current_run() or "", path_id, "adjudication",
        substrate_identity, STRATEGY_VERSION,
        REPORT_ADJUDICATION_POLICY_DEFAULTS["policy_version"],
        svc.asset_identity.get("manifest_sha256", ""),
        svc.asset_identity.get("source_file_sha256", ""),
    )


def _resolve_selected_card(svc: Services, state: WorkflowState,
                           retrieval_payload: dict) -> tuple[dict, dict]:
    """选中卡解析:检索卡或模型提案卡;返回 (card, decision)。"""
    decision = _read_decision(svc, state["decision_task_id"])
    evidence_id = (state.get("predicted_evidence_id")
                   or decision.get("accepted_evidence_id"))
    card = next(
        (e for e in retrieval_payload["evidences"]
         if e["evidence_id"] == evidence_id), None)
    if card is None:
        # 模型提案卡:全文在 prediction.json(不可变产物)
        card = _load_proposed_card(svc, state)
    return card, decision


def _prediction_context(svc: Services, state: WorkflowState) -> tuple:
    """预测分支上下文(任务/结果产物;无预测分支为 (None, None))。"""
    if not state.get("prediction_task_id"):
        return None, None
    pred_task = svc.artifacts.read(
        state["prediction_task_id"], "prediction_task")["payload"]
    pred_env = svc.artifacts.read(state["prediction_task_id"], "prediction")
    return pred_task, (pred_env["payload"] if pred_env else None)


def _adjudication_scope(retrieval_payload: dict,
                        pred_result: dict | None) -> list[tuple[dict, str]]:
    """审查范围(任务书 Phase B §2 下限):本父检索产物 + 模型提案卡。"""
    scope: list[tuple[dict, str]] = [
        (e, "retrieval") for e in retrieval_payload.get("evidences", [])]
    if (pred_result or {}).get("proposed_card"):
        scope.append((pred_result["proposed_card"], "model_proposal"))
    return scope


def _load_card_validations(svc: Services, adj_task_id: str,
                           scope: list[tuple[dict, str]],
                           selected_evidence_id: str,
                           *, compute_missing: bool,
                           substrate_identity: str = "",
                           ancestry_cns: list[str] | None = None,
                           policy: dict | None = None
                           ) -> tuple[dict[str, dict], dict[str, dict]]:
    """逐卡验证产物装配 → (payloads, refs)。

    refs[eid] = {"task_id", "artifact", "payload_sha256"}(Phase B R1 P1-2:
    裁决可回查的验证产物引用,来自落盘信封的真实哈希)。
    compute_missing=True(adjudicate 阶段)允许从不可变输入计算并落盘;
    False(commit 阶段)只读,缺失即结构化错误 —— 事件提交后兄弟路径集合
    已变化,重算会破坏草稿一致性。"""
    out: dict[str, dict] = {}
    refs: dict[str, dict] = {}
    for card, layer in scope:
        eid = card["evidence_id"]
        if eid == selected_evidence_id:
            continue
        name = cardval_artifact_name(eid)
        env = svc.artifacts.read(adj_task_id, name)
        if env is None:
            if not compute_missing:
                raise NodeStateError(
                    "逐卡验证产物缺失(裁决草稿应已固定)",
                    {"adjudication_task_id": adj_task_id,
                     "evidence_id": eid})
            env = svc.artifacts.write(adj_task_id, name,
                                      validate_card_for_reporting(
                                          card=card,
                                          substrate_identity=substrate_identity,
                                          ancestry_cns=ancestry_cns or [],
                                          entry_layer=layer,
                                          policy=policy))
        out[eid] = env["payload"]
        refs[eid] = {"task_id": adj_task_id, "artifact": name,
                     "payload_sha256": env["payload_hash"]}
    return out, refs


def adjudicate_candidates(svc: Services) -> Callable[[WorkflowState], dict]:
    """候选报告裁决(Phase B):先固定验证/排序草稿,再决定提交。

    - 每张审查范围内卡逐卡过确定性门禁(未选中卡每卡一份不可变产物);
    - 草稿(report_adjudication_draft)落盘后才有事件提交;导出只读最终
      产物,草稿永不可导出(任务书 Phase B §3.5);
    - 选中卡合格产品 > 0 → 提交事件;否则显式 no_event 终态最终化后
      mark_dead_end,不为出分偷换其他卡提交。
    """
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        retrieval_payload = svc.artifacts.read(
            state["retrieval_task_id"], "retrieval")["payload"]
        card, decision = _resolve_selected_card(svc, state, retrieval_payload)
        validation = svc.artifacts.read(state["validation_task_id"],
                                        "validation")
        pred_task, pred_result = _prediction_context(svc, state)
        adj_task_id = adjudication_task_id_for(svc, path_id,
                                               substrate_identity)
        policy = dict(REPORT_ADJUDICATION_POLICY_DEFAULTS)
        ancestry_cns = pw.ancestry_identities(
            pw.ancestry_chain(svc.store, path_id))
        scope = _adjudication_scope(retrieval_payload, pred_result)
        if validation is None:
            raise NodeStateError(
                "选中卡验证产物缺失:adjudicate 必须在 validate_products 后",
                {"path_id": path_id,
                 "validation_task_id": state.get("validation_task_id")})
        # 选中卡引用原 validation.json(Phase B R1 P1-2)
        validation_refs = {
            card["evidence_id"]: {
                "task_id": state["validation_task_id"],
                "artifact": "validation",
                "payload_sha256": validation["payload_hash"],
            }
        }
        card_validations, cardval_refs = _load_card_validations(
            svc, adj_task_id, scope, card["evidence_id"],
            compute_missing=True, substrate_identity=substrate_identity,
            ancestry_cns=ancestry_cns, policy=policy)
        validation_refs.update(cardval_refs)

        def adjudicate(stage: str, event_commit: dict | None = None,
                       no_event_reason: str = "") -> dict:
            return adjudicate_parent(
                run_id=run_id, path_id=path_id,
                substrate_identity=substrate_identity,
                retrieval_payload=retrieval_payload,
                decision_payload=decision,
                prediction_task=pred_task, prediction_result=pred_result,
                selected_evidence_id=card["evidence_id"],
                selected_card=card,
                selected_validation=validation["payload"],
                card_validations=card_validations,
                validation_refs=validation_refs, stage=stage,
                event_commit=event_commit,
                no_event_reason=no_event_reason, policy=policy)

        draft = adjudicate("draft")
        svc.artifacts.write(adj_task_id, "report_adjudication_draft", draft)
        _maybe_crash(svc, "adjudicate_candidates")  # 草稿已落盘,事件未提交
        n_selected_reportable = sum(
            1 for r in draft["products"]
            if r["evidence_id"] == card["evidence_id"]
            and r["report_rank"] is not None)
        if n_selected_reportable > 0:
            return {
                "adjudication_task_id": adj_task_id,
                "last_outcome": "commit_recorded",
            }
        # 选中卡全被拒/资格复验失败:显式 no_event 终态最终化(不偷换
        # 其他卡提交);拒因区分"资格失败"与"产物全拒"(R1:状态清晰)
        sel_card = next((c for c in draft["cards"]
                         if c["evidence_id"] == card["evidence_id"]), {})
        if not sel_card.get("card_eligible", True):
            no_event_reason = (
                "selected_card_ineligible:"
                + ";".join(sel_card.get("card_reasons", []))[:200])
        else:
            no_event_reason = "selected_card_all_products_rejected"
        final = adjudicate(STAGE_FINAL, no_event_reason=no_event_reason)
        svc.artifacts.write(adj_task_id, "report_adjudication", final)
        _maybe_crash(svc, "adjudication_finalized")  # 终态已写,checkpoint 未写
        return {
            "adjudication_task_id": adj_task_id,
            "last_outcome": "dead_end",
        }

    return node


def commit_pathway(svc: Services) -> Callable[[WorkflowState], dict]:
    """幂等提交选中卡事件 → 写含真实事件引用的最终裁决(Phase B §3.5
    顺序:先固定验证/排序草稿,再幂等提交事件,最后最终化)。

    重放确定性:提交位次取自草稿(事件提交会改变兄弟路径集合,裁决一律
    以草稿为准重算);submit_event 同键幂等;最终裁决同输入重算,同键同
    内容幂等 —— 三处硬杀(草稿后/事件后/最终化后)复跑得同一账本与裁决。
    """
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        retrieval_payload = svc.artifacts.read(
            state["retrieval_task_id"], "retrieval")["payload"]
        card, decision = _resolve_selected_card(svc, state, retrieval_payload)
        validation = svc.artifacts.read(state["validation_task_id"],
                                        "validation")
        evidence_id = card["evidence_id"]
        model_ref = ""
        if state.get("prediction_task_id") and state.get(
                "predicted_evidence_id"):
            # 模型决策引用(选中既有卡或提案卡都记录;ARCHITECTURE §6)
            pred = svc.artifacts.read(state["prediction_task_id"], "prediction")
            if pred is not None:
                model_ref = (f"prediction:{state['prediction_task_id']}"
                             f"#a{pred['payload'].get('attempt', 0)}")
        pred_task, pred_result = _prediction_context(svc, state)
        adj_task_id = adjudication_task_id_for(svc, path_id,
                                               substrate_identity)
        policy = dict(REPORT_ADJUDICATION_POLICY_DEFAULTS)
        scope = _adjudication_scope(retrieval_payload, pred_result)
        if validation is None:
            raise NodeStateError(
                "选中卡验证产物缺失(commit 需要引用 validation.json)",
                {"path_id": path_id,
                 "validation_task_id": state.get("validation_task_id")})
        validation_refs = {
            evidence_id: {
                "task_id": state["validation_task_id"],
                "artifact": "validation",
                "payload_sha256": validation["payload_hash"],
            }
        }
        card_validations, cardval_refs = _load_card_validations(
            svc, adj_task_id, scope, evidence_id, compute_missing=False)
        validation_refs.update(cardval_refs)
        draft_env = svc.artifacts.read(adj_task_id, "report_adjudication_draft")
        if draft_env is None:
            raise NodeStateError(
                "候选裁决草稿缺失:必须先经 adjudicate_candidates 固定草稿"
                "再提交事件",
                {"path_id": path_id,
                 "adjudication_task_id": adj_task_id})
        draft = draft_env["payload"]
        # 提交集 = 草稿中选中卡**占用报告位次**的产物(committed ⇒
        # reportable 不变量;超出报告宽度的合格产物不提交,留拒因)。
        # 不重算,保证草稿→提交→最终裁决一致;恢复重放读同一份草稿。
        ranked_selected = sorted(
            (r for r in draft["products"]
             if r["evidence_id"] == evidence_id
             and r["report_rank"] is not None),
            key=lambda r: r["report_rank"])
        commit_positions = [r["position"] for r in ranked_selected]
        if not commit_positions:
            raise NodeStateError(
                "草稿中选中卡无可报告产物,不应进入提交",
                {"path_id": path_id, "evidence_id": evidence_id})
        products = [p for p in card["products"]
                    if p["position"] in set(commit_positions)]
        width = dict(state["budget"])["max_frontier_width"]
        expandable, deferred = schedule_products(
            [{"position": pos} for pos in commit_positions], width)
        expandable_pos = {p["position"] for p in expandable}
        deferred_pos = {p["position"] for p in deferred}
        from ..storage.pathway_store import event_id_for, product_path_id

        eid = event_id_for(run_id, path_id, substrate_identity, evidence_id)
        expandable_ids = [
            product_path_id(run_id, eid, p["position"]) for p in expandable
        ]
        deferred_ids = [
            product_path_id(run_id, eid, p["position"]) for p in deferred
        ]
        result = svc.store.submit_event(
            run_id=run_id, parent_path_id=path_id,
            substrate_identity=substrate_identity, evidence=card,
            products=products, expandable_path_ids=expandable_ids,
            deferred_path_ids=deferred_ids, model_ref=model_ref,
        )
        _maybe_crash(svc, "commit_event")  # 事件已提交,最终裁决未写
        final = adjudicate_parent(
            run_id=run_id, path_id=path_id,
            substrate_identity=substrate_identity,
            retrieval_payload=retrieval_payload,
            decision_payload=decision,
            prediction_task=pred_task, prediction_result=pred_result,
            selected_evidence_id=evidence_id, selected_card=card,
            selected_validation=validation["payload"],
            card_validations=card_validations,
            validation_refs=validation_refs, stage=STAGE_FINAL,
            event_commit={"event_id": result["event_id"],
                          "expand_positions": sorted(expandable_pos),
                          "deferred_positions": sorted(deferred_pos)},
            policy=policy)
        svc.artifacts.write(adj_task_id, "report_adjudication", final)
        svc.store.refresh_depths(run_id)
        _maybe_crash(svc, "commit_pathway")  # 账本+最终裁决已写,checkpoint 未写
        return {
            "graph_revision": svc.store.graph_revision(),
            "phase": "select",
            "last_outcome": "commit_recorded",
        }

    return node


def mark_awaiting_prediction(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        decision = _read_decision(svc, state["decision_task_id"])
        reason = decision["reason"]
        # Phase C:预测路由的具体拒因(no_mapping/applicability_failed/…)
        # 随停留状态入账,不在报告里退化成笼统的"仅有规则/类比证据"
        prediction_reason = decision.get("prediction_reason", "")
        if prediction_reason and prediction_reason not in reason:
            reason = f"{reason};prediction:{prediction_reason}"
        svc.store.set_path_status(
            state["active_path_id"], PATH_STATUS_AWAITING_PREDICTION,
            reason[:300],
        )
        return {"phase": "select"}

    return node


def mark_dead_end(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        path_id = state["active_path_id"]
        reason = ""
        decision_task = state.get("decision_task_id")
        if decision_task:
            reason = _read_decision(svc, decision_task)["reason"]
        validation_task = state.get("validation_task_id")
        if validation_task:
            vp = svc.artifacts.read(validation_task, "validation")
            if vp and vp["payload"]["n_accepted"] == 0:
                reason = "all_products_rejected:" + ";".join(
                    r for v in vp["payload"]["verdicts"]
                    for r in v["reasons"]
                )[:300]
        svc.store.set_path_status(path_id, PATH_STATUS_DEAD_END, reason[:300])
        return {"phase": "select"}

    return node


def export_results(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        from ..output.report import write_report

        run_id = state["run_id"]
        budget = _refresh_budget(svc, state)
        paths = svc.store.list_paths(run_id)
        any_awaiting = any(
            p["status"] == PATH_STATUS_AWAITING_PREDICTION for p in paths
        )
        frontier_remaining = sum(
            1 for p in paths if p["status"] == "frontier"
        )
        llm_exhausted = (
            int(budget.get("max_llm_calls", 0)) > 0
            and int(budget.get("used_llm_calls", 0))
            >= int(budget.get("max_llm_calls", 0))
        )
        reason = state.get("stop_reason") or stop_reason(
            any_awaiting=any_awaiting,
            used_expansions=budget["used_expansions"],
            max_expansions=budget["max_expansions"],
            frontier_remaining=frontier_remaining,
            llm_budget_exhausted=llm_exhausted,
        )
        write_report(svc.store, Path(svc.runs_dir), run_id, state, reason)
        return {"phase": "done", "stop_reason": reason, "budget": budget}

    return node
