"""S3b 模型假设协议 —— proposals[] 解析与有界格式反馈(实施书 §5.3;
契约随 search-6 / format-feedback-1 登记;**S3b r2:协议版本
ppv1-model-proposals-1 → -2 —— novel 池外提案必须携带完整
reaction_spec 反应内容**)。

范围:PPV1 新任务的模型响应协议 `proposals[]`(每项一条独立反应
假设;内部共同产物集合与 participants/来源/条件/依赖按既有契约)、
`rank_hypotheses`(引稳定 ID)、novel 有界 proposal_context;**只有
JSON 字段/类型、允许 ID、语法契约错误可进格式反馈**(独立有界策略
ppv1-format-feedback-1,默认 0 轮;结构无法解析记结构失败,不能以
格式反馈改分子再试到通过)。模型不直接写 SQLite/frontier/条件事实/
策略(本层只解析与登记,消费在调度/生产链)。

**S3b r2(S3B-05)**:novel 池外提案不再只是计数披露 —— 每条 novel
提案必须声明**明确反应内容**(`reaction_spec`:与冻结池条目同形状的
假设载荷,product_smiles/edits/donor/alignment/expectation 等按
既有 prepare_hypothesis 契约)与**来源**(`proposal_context`:
reference_hypothesis_ids/output_origin 明示,不伪造来源);驱动消费
novel 为独立假设(结构身份/参与物/系数/共同产物/条件/依赖经既有
契约构造)入有界调度,走固定工具→audit→admission→submit。缺
reaction_spec ⇒ json_field 格式错误(可进有界反馈;无足够内容不能
授有效 hypothesis,不伪造内容);reaction_spec 内容非法(结构/契约)
在构造/执行侧结构化拒,不是格式反馈(不以反馈改分子再试到通过)。
空池时驱动仍组装底物档案并消费模型响应(合法空列表/弃权保持)。

入口矩阵:

| # | 入口 | 消费 | 校验/事务 |
| 1 | parse_model_proposals | 模型响应文本(脚本/恢复) | JSON 解析(失败 ⇒ 结构失败,非格式反馈);proposals[] 形状契约(dict/list/字段);允许 ID 集(池内假设引用须 ∈ 冻结池);novel 必须带 proposal_context(reference_hypothesis_ids/output_origin 明示,不伪造来源)**与 reaction_spec(完整反应内容;缺 ⇒ json_field 错误)**;空列表/弃权合法;rank 引稳定 ID 且须在提案集内;解析结果只是提案,不是 recorded 状态 |
| 2 | classify_format_error | 解析失败的错误分类 | 仅 json_field/json_type/allowed_id/syntax 四类可进格式反馈;not_json ⇒ structure_unparseable(记结构失败,零反馈轮) |
| 3 | register_format_feedback_round | 反馈轮计数(持久事实源)+ 错误载荷 | model_requests 行(purpose=format_feedback;scripted/fake 网络 0;real 走 register_model_request 即时占额 —— 传入模型对象不自动补预算);轮数 = 同 action 的既有 format_feedback 请求数,超 max_format_feedback_rounds ⇒ 结构化拒(结构失败保持,不以反馈重试到通过);每轮持久记录输入/错误类别/反馈版本/次数 |

计数语义(与 S3a 十上限的关系,任务书 §5.3):格式反馈轮数是**同任务
JSON 修复轮数**,不是 hypothesis 语义 attempt —— 不占/不改写
max_attempts_per_hypothesis;反馈轮走 model_requests 持久计数,真实
provider 的反馈轮额外受 max_real_model_requests 预算(register 侧
拒绝,网络发送被阻止)。chemical_reproposal 首版 off:SMILES 解析
失败记结构失败,化学重提案数 0/路径 unsupported 如实披露。
"""

from __future__ import annotations

import json

from ..domain.models import now_iso
from .profile import (
    FORMAT_FEEDBACK_POLICY_VERSION,
    validate_frozen_format_feedback_policy,
)
from .search import (
    PROVIDER_KINDS,
    PROVIDER_KIND_SCRIPTED,
    SearchBudgetExhausted,
    SearchContractError,
    SearchLedger,
)

MODEL_PROTOCOL_VERSION = "ppv1-model-proposals-2"
PURPOSE_FORMAT_FEEDBACK = "format_feedback"

# ---- 错误分类(只有前四类可进格式反馈;structure_unparseable 不可) ----

FORMAT_ERROR_JSON_FIELD = "json_field_error"
FORMAT_ERROR_JSON_TYPE = "json_type_error"
FORMAT_ERROR_ALLOWED_ID = "allowed_id_error"
FORMAT_ERROR_SYNTAX = "syntax_contract_error"
FORMAT_ERROR_STRUCTURE_UNPARSEABLE = "structure_unparseable"
FORMAT_ERROR_KINDS = frozenset({
    FORMAT_ERROR_JSON_FIELD, FORMAT_ERROR_JSON_TYPE,
    FORMAT_ERROR_ALLOWED_ID, FORMAT_ERROR_SYNTAX,
    FORMAT_ERROR_STRUCTURE_UNPARSEABLE,
})
FEEDBACK_ELIGIBLE = frozenset({
    FORMAT_ERROR_JSON_FIELD, FORMAT_ERROR_JSON_TYPE,
    FORMAT_ERROR_ALLOWED_ID, FORMAT_ERROR_SYNTAX,
})


class ModelProtocolError(SearchContractError):
    """模型协议契约违反(结构化;解析失败分类携带在 detail)。"""


def _format_error(kind: str, reason: str, detail: dict | None = None) -> None:
    raise ModelProtocolError(
        f"模型响应协议错误({kind}):{reason}",
        {"kind": kind, "model_protocol_version": MODEL_PROTOCOL_VERSION,
         **(detail or {})})


def parse_model_proposals(
    response_text: str,
    *,
    allowed_hypothesis_ids: list[str] | set[str] | frozenset[str],
) -> dict:
    """解析模型响应的 proposals[](每项一条独立反应假设)。

    - response_text 非 JSON ⇒ structure_unparseable(**结构失败**,
      不进格式反馈 —— 不能以格式反馈改分子再试到通过);
    - 顶层必须是 dict 且含 "proposals" list(缺字段/坏类型 ⇒ 格式
      错误,可进有界反馈);
    - 每项 proposal 必须是 dict:
      * 引用冻结池假设:`hypothesis_id` ∈ allowed(备选反应假设引
        稳定 ID;模型 rank 不把选择升成 recorded —— 解析结果只是
        提案引用);
      * novel 池外提案:必须携带 `proposal_context`(dict,含
        `reference_hypothesis_ids`(可空,池内参考)与 `output_origin`
        (明示来源,如 "novel_outside_pool"),不伪造来源)**与
        `reaction_spec`(dict,与冻结池条目同形状的完整反应内容 ——
        product_smiles/edits/donor/alignment/expectation 等按既有
        prepare_hypothesis 契约;缺 ⇒ json_field 格式错误,无足够
        内容不能授有效 hypothesis)**;
      * 共同产物与备选不混:proposal 内的 `coproducts`(list)是
        **该假设内部**的共同产物声明,不作为独立提案出现(发现
        顶层的 coproduct 形状混淆 ⇒ syntax 契约错误);
    - `rank_hypotheses`(可选,list)引用的 id 必须在提案集合内
      (引稳定 ID;排序是建议次序,不是已核实状态);
    - 空列表/弃权合法:proposals=[] ⇒ abstained=True;
    - 返回 {proposals, rank_hypotheses, abstained, protocol_version}。
    """
    if not isinstance(response_text, str):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"响应必须是 JSON 文本,得到 {type(response_text).__name__}")
    try:
        payload = json.loads(response_text)
    except (ValueError, TypeError) as exc:
        _format_error(
            FORMAT_ERROR_STRUCTURE_UNPARSEABLE,
            f"响应不可解析为 JSON(结构失败,不进格式反馈;不能以反馈"
            f"改分子再试到通过):{str(exc)[:160]}")
    if not isinstance(payload, dict):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"响应顶层必须是 dict,得到 {type(payload).__name__}")
    if "proposals" not in payload:
        _format_error(
            FORMAT_ERROR_JSON_FIELD,
            "响应缺 proposals 字段(每项一条独立反应假设;空列表/"
            "弃权合法)")
    proposals_raw = payload["proposals"]
    if not isinstance(proposals_raw, list):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"proposals 必须是 list,得到 {type(proposals_raw).__name__}")
    allowed = set(allowed_hypothesis_ids or [])
    proposals: list[dict] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(proposals_raw):
        if not isinstance(item, dict):
            _format_error(
                FORMAT_ERROR_JSON_TYPE,
                f"proposals[{i}] 必须是 dict,得到 {type(item).__name__}",
                {"index": i})
        if "coproducts" in item and "hypothesis_id" not in item:
            _format_error(
                FORMAT_ERROR_SYNTAX,
                f"proposals[{i}] 携带 coproducts 但不是假设提案(共同"
                "产物是假设内部声明,不作为独立提案;备选与共同产物"
                "不混队)", {"index": i})
        hypothesis_id = str(item.get("hypothesis_id") or "")
        if not hypothesis_id:
            _format_error(
                FORMAT_ERROR_JSON_FIELD,
                f"proposals[{i}] 缺 hypothesis_id(引用冻结池稳定 ID,"
                "或 novel 时经 proposal_context 声明)", {"index": i})
        if hypothesis_id in seen_ids:
            _format_error(
                FORMAT_ERROR_SYNTAX,
                f"proposals[{i}] 重复引用 {hypothesis_id}(幂等引用,"
                "不重复提案)", {"index": i, "hypothesis_id": hypothesis_id})
        seen_ids.add(hypothesis_id)
        entry: dict = {"hypothesis_id": hypothesis_id}
        if hypothesis_id in allowed:
            entry["origin"] = "frozen_pool"
        else:
            context = item.get("proposal_context")
            if not isinstance(context, dict):
                _format_error(
                    FORMAT_ERROR_JSON_FIELD,
                    f"proposals[{i}] 引用池外假设 {hypothesis_id} 但缺"
                    " proposal_context(novel 有界:reference_hypothesis_"
                    "ids/output_origin 明示,不伪造来源)",
                    {"index": i, "hypothesis_id": hypothesis_id})
            refs = context.get("reference_hypothesis_ids")
            if not isinstance(refs, list) or \
                    any(str(r) not in allowed for r in refs):
                _format_error(
                    FORMAT_ERROR_ALLOWED_ID,
                    f"proposals[{i}] 的 proposal_context.reference_"
                    "hypothesis_ids 必须是冻结池 ID 子集",
                    {"index": i, "hypothesis_id": hypothesis_id,
                     "reference_hypothesis_ids": refs})
            if not str(context.get("output_origin") or ""):
                _format_error(
                    FORMAT_ERROR_JSON_FIELD,
                    f"proposals[{i}] 的 proposal_context 缺 output_origin"
                    "(明示来源)",
                    {"index": i, "hypothesis_id": hypothesis_id})
            # ---- S3b r2(S3B-05):novel 必须携带完整反应内容 ----
            reaction_spec = item.get("reaction_spec")
            if not isinstance(reaction_spec, dict) or not reaction_spec:
                _format_error(
                    FORMAT_ERROR_JSON_FIELD,
                    f"proposals[{i}] 池外 novel 提案 {hypothesis_id} 缺"
                    " reaction_spec(完整反应内容:product_smiles/edits/"
                    "donor/alignment/expectation 按既有假设契约;无足够"
                    "内容不能授有效 hypothesis,不伪造内容)",
                    {"index": i, "hypothesis_id": hypothesis_id,
                     "novel_reaction_spec_missing": True})
            entry["origin"] = "novel"
            entry["proposal_context"] = dict(context)
            entry["reaction_spec"] = dict(reaction_spec)
        coproducts = item.get("coproducts")
        if coproducts is not None and not isinstance(coproducts, list):
            _format_error(
                FORMAT_ERROR_JSON_TYPE,
                f"proposals[{i}] 的 coproducts 必须是 list(假设内部共同"
                "产物声明)", {"index": i})
        if coproducts is not None:
            entry["coproducts"] = [str(c) for c in coproducts]
        proposals.append(entry)
    rank_raw = payload.get("rank_hypotheses")
    if rank_raw is None:
        rank_raw = [p["hypothesis_id"] for p in proposals]
    if not isinstance(rank_raw, list):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"rank_hypotheses 必须是 list,得到 {type(rank_raw).__name__}")
    rank: list[str] = []
    for i, rid in enumerate(rank_raw):
        rid = str(rid)
        if rid not in seen_ids:
            _format_error(
                FORMAT_ERROR_ALLOWED_ID,
                f"rank_hypotheses[{i}] 引用未在提案集合内的 {rid}"
                "(rank 引稳定 ID)",
                {"index": i, "hypothesis_id": rid})
        rank.append(rid)
    return {"proposals": proposals, "rank_hypotheses": rank,
            "abstained": not proposals,
            "protocol_version": MODEL_PROTOCOL_VERSION}


def feedback_policy_from_ledger(ledger: SearchLedger,
                                run_id: str) -> dict:
    """从 run 的冻结策略块读取格式反馈策略(严格消费;块缺/坏 ⇒
    SearchRecoveryError 由 _limits 同源包装,不补默认)。"""
    block = ledger.search_policy_block(run_id)
    policy = (block or {}).get("format_feedback_policy") \
        if isinstance(block, dict) else None
    try:
        return validate_frozen_format_feedback_policy(policy)
    except ValueError as exc:
        raise ModelProtocolError(
            f"run {run_id} 的冻结格式反馈策略块非法(严格核验,不补"
            f"默认、不猜迁移):{exc}",
            {"run_id": run_id, "kind": "format_feedback_policy_corrupt",
             "reason": str(exc)[:300]}) from exc


def format_feedback_rounds_used(ledger: SearchLedger,
                                action_id: str) -> int:
    """同 action 已发生的格式反馈轮数(持久事实源 = model_requests
    行;不是内存计数,内存重置仍从记录复算)。"""
    row = ledger.conn.execute(
        "SELECT COUNT(*) FROM model_requests WHERE action_id = ? AND"
        " purpose = ?", (action_id, PURPOSE_FORMAT_FEEDBACK)).fetchone()
    return int(row[0])


def register_format_feedback_round(
    ledger: SearchLedger,
    *,
    run_id: str,
    action_id: str,
    attempt_id: str,
    error: ModelProtocolError,
    response_excerpt: str,
    provider_kind: str = PROVIDER_KIND_SCRIPTED,
) -> dict:
    """登记一轮有界格式反馈(每轮持久记录输入/错误类别/反馈版本/
    次数;受独立有限策略约束;超限 ⇒ 结构化拒,结构失败保持)。

    - 只有 FEEDBACK_ELIGIBLE 类错误可登记(not_json 的
      structure_unparseable 在调用侧直接记结构失败,不经本入口);
    - 轮数 = 同 action 既有 format_feedback 请求数;≥ 策略上限 ⇒
      SearchBudgetExhausted(reason_category=budget_limit)—— 反馈停,
      上一次解析失败作为结构失败保持;
    - scripted/fake 恒 network 0;real 走 register_model_request 的
      即时占额(真实请求额度 0 ⇒ 登记被拒,网络发送被阻止;传入
      模型对象不自动补预算);
    - request_key 派生自 (action, 轮次) —— 幂等;payload 持久记录
      错误类别/版本/次数/响应摘录。
    """
    if provider_kind not in PROVIDER_KINDS:
        raise ModelProtocolError(
            f"provider_kind 非法:{provider_kind!r}",
            {"kind": "invalid_provider_kind",
             "provider_kind": provider_kind})
    kind = str(error.detail.get("kind") or "")
    if kind not in FEEDBACK_ELIGIBLE:
        eligible = sorted(FEEDBACK_ELIGIBLE)
        raise ModelProtocolError(
            f"错误类别 {kind!r} 不可进格式反馈(仅 {eligible};"
            "structure_unparseable 记结构失败)",
            {"kind": "feedback_ineligible_error", "error_kind": kind})
    policy = feedback_policy_from_ledger(ledger, run_id)
    rounds_used = format_feedback_rounds_used(ledger, action_id)
    max_rounds = int(policy["max_format_feedback_rounds"])
    if rounds_used >= max_rounds:
        raise SearchBudgetExhausted(
            f"格式反馈轮数超上限(同任务 JSON 修复轮数 {rounds_used} ≥ "
            f"max_format_feedback_rounds={max_rounds};结构失败保持,"
            "不以反馈重试到通过;该轮数不是 hypothesis 语义 attempt)",
            {"kind": "format_feedback_budget_exhausted",
             "limit_key": "max_format_feedback_rounds",
             "max": max_rounds, "used": rounds_used,
             "policy_version": FORMAT_FEEDBACK_POLICY_VERSION})
    round_index = rounds_used + 1
    payload = {
        "feedback_version": FORMAT_FEEDBACK_POLICY_VERSION,
        "model_protocol_version": MODEL_PROTOCOL_VERSION,
        "round": round_index,
        "error_kind": kind,
        "error_detail": dict(error.detail),
        "response_excerpt": str(response_excerpt)[:2000],
        "recorded_at": now_iso(),
    }
    return ledger.register_model_request(
        run_id=run_id, action_id=action_id, attempt_id=attempt_id,
        provider_kind=provider_kind,
        request_key=f"format-feedback:{action_id}:{round_index}",
        purpose=PURPOSE_FORMAT_FEEDBACK, payload=payload)
