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
from ..storage.pathway_store import PathwayStore
from ..validation.gates import (
    gate_atom_mapping_declared,
    gate_direction_source,
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
        decision = classify_evidence_policy(
            envelope["payload"]["evidences"], run_id, path_id, substrate_identity
        )
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
        )
        decision.prediction_mode = mode
        decision.prediction_reason = route_reason
        task_id = task_id_for(svc, path_id, "decision", substrate_identity)
        svc.artifacts.write(task_id, "decision", decision.to_dict())
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
            if mode == PREDICTION_MODE_ANALOGY:
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
    """类比编辑:AtomTool 复验受限编辑 → 提案卡(映射/表示失败=显式拒绝)。"""
    from ..services.atom_tool import check_edit_references, check_target_molecode

    donor_block = task.get("donor") or {}
    current_render = _real_render(state)
    # 编辑引用核验(引用了不存在的原子/键 → 显式拒)
    ref_ok, ref_reasons = check_edit_references(current_render, parsed.edits)
    target = check_target_molecode(current_render, parsed.target_molecode)
    checks = {
        "edit_references": {"ok": ref_ok, "reasons": ref_reasons},
        "target_molecode": target,
    }
    if not ref_ok or not target["ok"]:
        base["outcome"] = "rejected"
        base["fail_reason"] = "atomtool:" + ";".join(
            ref_reasons + target.get("reasons", []))[:300]
        base["atomtool_checks"] = checks
        return "failed", base
    product_smiles = target["target_smiles"]
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
        if card is None:
            # 模型提案卡:全文在 prediction.json(不可变产物)
            pred = svc.artifacts.read(state["prediction_task_id"], "prediction")
            card = pred["payload"]["proposed_card"]
        dir_ok, dir_reason = gate_direction_source(card)
        map_ok, map_reason = gate_atom_mapping_declared(card)
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
            "error": {} if dir_ok else {"gate": "direction_source",
                                        "message": dir_reason},
        }

    return node


def commit_pathway(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        run_id = state["run_id"]
        path_id = state["active_path_id"]
        substrate_identity = state["active_substrate_identity"]
        retrieval = svc.artifacts.read(state["retrieval_task_id"], "retrieval")["payload"]
        decision = _read_decision(svc, state["decision_task_id"])
        validation = svc.artifacts.read(state["validation_task_id"], "validation")
        evidence_id = (state.get("predicted_evidence_id")
                       or decision.get("accepted_evidence_id"))
        card = next(
            (e for e in retrieval["evidences"]
             if e["evidence_id"] == evidence_id), None)
        model_ref = ""
        if state.get("prediction_task_id") and state.get(
                "predicted_evidence_id"):
            # 模型决策引用(选中既有卡或提案卡都记录;ARCHITECTURE §6)
            pred = svc.artifacts.read(state["prediction_task_id"], "prediction")
            if pred is not None:
                model_ref = (f"prediction:{state['prediction_task_id']}"
                             f"#a{pred['payload'].get('attempt', 0)}")
        if card is None:
            # 模型提案卡:从 prediction 产物取(全文不可变落盘)
            pred = svc.artifacts.read(state["prediction_task_id"], "prediction")
            card = pred["payload"]["proposed_card"]
        accepted_positions = {
            v["position"] for v in validation["payload"]["verdicts"]
            if v["accepted"]
        } if validation else {p["position"] for p in card["products"]}
        products = [
            p for p in card["products"] if p["position"] in accepted_positions
        ]
        width = dict(state["budget"])["max_frontier_width"]
        expandable, deferred = schedule_products(
            [{"position": p["position"]} for p in products], width
        )
        expandable_pos = {p["position"] for p in expandable}
        deferred_pos = {p["position"] for p in deferred}
        from ..storage.pathway_store import event_id_for, product_path_id

        eid = event_id_for(run_id, path_id, substrate_identity,
                           card["evidence_id"])
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
        svc.store.refresh_depths(run_id)
        _maybe_crash(svc, "commit_pathway")  # 账本已提交,checkpoint 未写
        return {
            "graph_revision": svc.store.graph_revision(),
            "phase": "select",
            "last_outcome": "commit_recorded",
        }

    return node


def mark_awaiting_prediction(svc: Services) -> Callable[[WorkflowState], dict]:
    def node(state: WorkflowState) -> dict:
        decision = _read_decision(svc, state["decision_task_id"])
        svc.store.set_path_status(
            state["active_path_id"], PATH_STATUS_AWAITING_PREDICTION,
            decision["reason"],
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
