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
| 1 | parse_model_proposals | 模型响应文本(脚本/恢复) | JSON 解析(失败 ⇒ 结构失败,非格式反馈);proposals[] 形状契约(dict/list/字段);允许 ID 集(池内假设引用须 ∈ 冻结池);novel 必须带 proposal_context(reference_hypothesis_ids/output_origin 明示,不伪造来源)**与 reaction_spec(完整反应内容;缺 ⇒ json_field 错误)**;**reaction_spec 禁三键 participants/co_substrate_states/declared_copy_components 的判据按臂不同:atom_edit 分支拒收(D2b:池侧声明事实,模型不透传);产物优先分支(含 B/C 两臂)静默忽略并在 entry.ignored_spec_keys 记录键名(CC 2026-11-06 拍板 PC8:事件参与物只能来自编译器生成的 spec,模型自写键一律不消费)**;空列表/弃权合法;rank 引稳定 ID 且须在提案集内;解析结果只是提案,不是 recorded 状态 |
| 2 | classify_format_error | 解析失败的错误分类 | 仅 json_field/json_type/allowed_id/syntax 四类可进格式反馈;not_json ⇒ structure_unparseable(记结构失败,零反馈轮) |
| 3 | register_format_feedback_round | 反馈轮计数(持久事实源)+ 错误载荷 | model_requests 行(purpose=format_feedback;scripted/fake 网络 0;real 走 register_model_request 即时占额 —— 传入模型对象不自动补预算);轮数 = 同 action 的既有 format_feedback 请求数,超 max_format_feedback_rounds ⇒ 结构化拒(结构失败保持,不以反馈重试到通过);每轮持久记录输入/错误类别/反馈版本/次数 |
| 4 | latest_format_feedback_round(P1-2 余项,2026-10-16;收口轮同日) | resume 重入反馈分支的既有轮查找(先复用后新登记) | **复用前统一身份核验门(所有状态分支共用一套判据)**:最新轮 = 第 rounds_used 轮,request_id 由原登记键确定性重算(同键复算,不是换键);**计数>0 却查不到应有原行 ⇒ 结构化拒(不返回 None 走新登记,不以新键洗坏记录)**;查到行后逐列核 purpose/run_id/action_id/attempt_id/provider_kind/retry_of 与原登记及本调用一致,**payload_hash 按同源确定性重算核验(登记载荷无时间戳,时间由 model_requests.created_at 承载)**;任一不符 ⇒ feedback_round_identity_corrupt 结构化拒(坏记录保全,不分配新轮掩盖);行状态机消费(responded⇒R3 重放/failed⇒唯一重试终态链/registered⇒补首发)在 ppv1_real_fetch(消费已核验行) |

计数语义(与 S3a 十上限的关系,任务书 §5.3):格式反馈轮数是**同任务
JSON 修复轮数**,不是 hypothesis 语义 attempt —— 不占/不改写
max_attempts_per_hypothesis;反馈轮走 model_requests 持久计数,真实
provider 的反馈轮额外受 max_real_model_requests 预算(register 侧
拒绝,网络发送被阻止)。chemical_reproposal 首版 off:SMILES 解析
失败记结构失败,化学重提案数 0/路径 unsupported 如实披露。
"""

from __future__ import annotations

import json

from ..domain.models import content_hash, stable_id
from .profile import (
    FORMAT_FEEDBACK_POLICY_VERSION,
    FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST,
    NOVEL_PROTOCOL_ATOM_EDIT,
    NOVEL_PROTOCOL_BLIND_FIRST,
    NOVEL_PROTOCOL_PRODUCT_FIRST,
    NOVEL_PROTOCOLS,
    format_feedback_policy_version_for,
    validate_frozen_format_feedback_policy,
    validate_novel_protocol,
)
from .search import (
    PROVIDER_KINDS,
    PROVIDER_KIND_SCRIPTED,
    SearchBudgetExhausted,
    SearchContractError,
    SearchLedger,
)

MODEL_PROTOCOL_VERSION = "ppv1-model-proposals-2"
# EXP1(2026-11-05):product_first 路径的协议版本(A 臂记录旧值 ⇒ A 臂
# 载荷/登记字节不变)。novel 的 reaction_spec 只需 product_smiles
# (+可选 coproducts),由程序编译核验。
MODEL_PROTOCOL_VERSION_PRODUCT_FIRST = "ppv1-model-proposals-3"
MODEL_PROTOCOL_VERSIONS = (MODEL_PROTOCOL_VERSION,
                           MODEL_PROTOCOL_VERSION_PRODUCT_FIRST)
PURPOSE_FORMAT_FEEDBACK = "format_feedback"

# 程序核验失败(仅 product_first 路径可反馈;预注册 §5 白名单内容)
NOVEL_VERIFICATION_FAILED_KIND = "novel_verification_failed"

# ---- D2b(2026-11-06):novel reaction_spec 禁键(解析层堵口)----
# 这三个键属**池侧声明事实**,不是模型可写的反应内容:
#   * participants —— 显式参与物覆盖(角色/系数;production.
#     prepare_hypothesis 的池条目契约;缺省装配 = 底物 1 + 主产物 1 +
#     共同产物逐条);
#   * co_substrate_states —— 共底物 B 状态装配(记录侧声明在位时由
#     build_product_state 严格身份重建);
#   * declared_copy_components —— 声明式拷贝组分状态。
# **按臂的判据(CC 2026-11-06 拍板 PC8 后定稿)**:
#   * ``atom_edit`` 分支(A 臂,D2b 验收面):整 dict 透传
#     (entry["reaction_spec"] = dict(...))会把模型自写的角色/系数/
#     state_ref 送进下游装配 —— 等于让模型直接写权威参与物事实。故
#     **一律记格式错误**(json_field;detail 带
#     novel_reaction_spec_forbidden_keys),不透传。
#   * 产物优先分支(B / C 两臂):模型多写的这些键**静默忽略**并在
#     entry.ignored_spec_keys 记录键名(事件参与物只能来自编译器生成的
#     spec,模型自写键不消费;不再记格式错误 —— PC8)。
#
# **唯一例外 = 既有池侧共底物声明路径**:池条目 spec 由
# production/hypothesis 侧构造(池条目/记录侧 corpus 块声明/证据卡),
# **不经 parse_model_proposals**,本检查只作用于模型响应解析,不给池
# 条目或记录侧声明加门(正控见 tests/pollutant/
# test_exp1_hardening_d2b_d4.py::test_d2b_pool_side_cosubstrate_
# declaration_positive_control)。
#
# 版本取舍(2026-11-06):不收严协议版本 —— MODEL_PROTOCOL_VERSION 嵌在
# A 臂请求载荷(protocol_version 字段)与登记身份里,升版会改 A 臂字节
# 与既有批身份;解析层拒收属 bug 修复性质,按格式错误处理即可。
NOVEL_REACTION_SPEC_FORBIDDEN_KEYS = (
    "participants", "co_substrate_states", "declared_copy_components")

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
# EXP1:product_first 路径额外可反馈"程序核验失败"(ppv1-format-feedback-2;
# A 臂 v1 策略块下本类别不可登记 —— 见 register_format_feedback_round)
FEEDBACK_ELIGIBLE_PRODUCT_FIRST = frozenset(
    set(FEEDBACK_ELIGIBLE) | {NOVEL_VERIFICATION_FAILED_KIND})


class ModelProtocolError(SearchContractError):
    """模型协议契约违反(结构化;解析失败分类携带在 detail)。"""


def _format_error(kind: str, reason: str, detail: dict | None = None,
                  *, model_protocol_version: str | None = None) -> None:
    raise ModelProtocolError(
        f"模型响应协议错误({kind}):{reason}",
        {"kind": kind,
         "model_protocol_version": (model_protocol_version
                                    or MODEL_PROTOCOL_VERSION),
         **(detail or {})})


def protocol_version_for(feedback_policy_version: str | None) -> str:
    """冻结反馈策略版本 → proposals 协议版本(单一映射)。"""
    if feedback_policy_version == FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST:
        return MODEL_PROTOCOL_VERSION_PRODUCT_FIRST
    return MODEL_PROTOCOL_VERSION


def _reject_novel_reaction_spec_forbidden_keys(
        reaction_spec: dict, *, index: int, hypothesis_id: str,
        model_protocol_version: str) -> None:
    """D2b:atom_edit 分支 novel reaction_spec 禁键拒收(A 臂判据)。

    只查**模型响应里的** reaction_spec(本入口专有);池侧声明路径
    (池条目 spec / 记录侧 corpus 块)不调用本函数,因此不受影响。
    **产物优先分支(B/C 臂)不调用本函数** —— 那些臂对同一批键走
    「静默忽略 + entry.ignored_spec_keys 记录」(PC8,CC 2026-11-06
    拍板),事件参与物只来自编译器生成的 spec。
    命中任一禁键 ⇒ ModelProtocolError(kind=json_field_error,detail
    含 ``novel_reaction_spec_forbidden_keys`` 实际命中列表)。
    """
    found = [key for key in NOVEL_REACTION_SPEC_FORBIDDEN_KEYS
             if key in reaction_spec]
    if not found:
        return
    _format_error(
        FORMAT_ERROR_JSON_FIELD,
        f"proposals[{index}] 的 reaction_spec 携带禁键 {found}"
        "(participants/co_substrate_states/declared_copy_components 是"
        "池侧声明事实:参与物角色/系数与共底物/拷贝组分状态只能由冻结"
        "池条目与记录侧声明给出,模型响应不得透传;从 reaction_spec 删去"
        "这三个键后重新提交)",
        {"index": index, "hypothesis_id": hypothesis_id,
         "novel_reaction_spec_forbidden_keys": found},
        model_protocol_version=model_protocol_version)


def parse_model_proposals(
    response_text: str,
    *,
    allowed_hypothesis_ids: list[str] | set[str] | frozenset[str],
    protocol: str | None = None,
) -> dict:
    """解析模型响应的 proposals[](每项一条独立反应假设)。

    ``protocol``:``atom_edit``(缺省 = A 臂现行:novel 须带完整原子
    编辑五字段)/ ``product_first_feedback``(B 臂:novel 的
    ``reaction_spec`` 只需 ``product_smiles`` + 可选 ``coproducts``,
    由程序编译核验;协议版本记 ``ppv1-model-proposals-3``)/
    ``product_first_feedback_blind_first``(C 臂:与 B 臂同一产物优先
    解析分支;盲写/合并两阶段调用共用本判据)。
    **atom_edit 分支逐字节/逐判据不变**(旧值 ``ppv1-model-proposals-2``)。

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
        内容不能授有效 hypothesis)**;``reaction_spec`` 里模型自写的
        **池侧声明键**(``participants`` / ``co_substrate_states`` /
        ``declared_copy_components`` 等多余键)按臂处理:
        **atom_edit 分支拒收**(D2b:池侧声明事实,模型响应不得透传;
        池侧共底物声明路径不经本入口 ⇒ 不受影响);
        **产物优先分支(B/C 臂)静默忽略**并在
        ``entry.ignored_spec_keys`` 记录键名(PC8:事件参与物只能来自
        编译器生成的 spec);
      * 共同产物与备选不混:proposal 内的 `coproducts`(list)是
        **该假设内部**的共同产物声明,不作为独立提案出现(发现
        顶层的 coproduct 形状混淆 ⇒ syntax 契约错误);
    - `rank_hypotheses`(可选,list)引用的 id 必须在提案集合内
      (引稳定 ID;排序是建议次序,不是已核实状态);
    - 空列表/弃权合法:proposals=[] ⇒ abstained=True;
    - 返回 {proposals, rank_hypotheses, abstained, protocol_version}。
    """
    protocol_value = (NOVEL_PROTOCOL_ATOM_EDIT if protocol is None
                      else str(protocol))
    if protocol_value not in NOVEL_PROTOCOLS:
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"protocol 非法值:{protocol!r}(允许 {list(NOVEL_PROTOCOLS)})")
    # 产物优先分支(EXP1 B 臂 product_first_feedback + C 臂 blind_first
    # 共用同一解析判据;两臂协议版本同为 -3)
    product_first_path = protocol_value in (NOVEL_PROTOCOL_PRODUCT_FIRST,
                                            NOVEL_PROTOCOL_BLIND_FIRST)
    model_version = (
        MODEL_PROTOCOL_VERSION_PRODUCT_FIRST
        if product_first_path
        else MODEL_PROTOCOL_VERSION)
    if not isinstance(response_text, str):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"响应必须是 JSON 文本,得到 {type(response_text).__name__}",
            model_protocol_version=model_version)
    try:
        payload = json.loads(response_text)
    except (ValueError, TypeError) as exc:
        _format_error(
            FORMAT_ERROR_STRUCTURE_UNPARSEABLE,
            f"响应不可解析为 JSON(结构失败,不进格式反馈;不能以反馈"
            f"改分子再试到通过):{str(exc)[:160]}",
            model_protocol_version=model_version)
    if not isinstance(payload, dict):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"响应顶层必须是 dict,得到 {type(payload).__name__}",
            model_protocol_version=model_version)
    if "proposals" not in payload:
        _format_error(
            FORMAT_ERROR_JSON_FIELD,
            "响应缺 proposals 字段(每项一条独立反应假设;空列表/"
            "弃权合法)", model_protocol_version=model_version)
    proposals_raw = payload["proposals"]
    if not isinstance(proposals_raw, list):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"proposals 必须是 list,得到 {type(proposals_raw).__name__}",
            model_protocol_version=model_version)
    allowed = set(allowed_hypothesis_ids or [])
    proposals: list[dict] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(proposals_raw):
        if not isinstance(item, dict):
            _format_error(
                FORMAT_ERROR_JSON_TYPE,
                f"proposals[{i}] 必须是 dict,得到 {type(item).__name__}",
                {"index": i}, model_protocol_version=model_version)
        if "coproducts" in item and "hypothesis_id" not in item:
            _format_error(
                FORMAT_ERROR_SYNTAX,
                f"proposals[{i}] 携带 coproducts 但不是假设提案(共同"
                "产物是假设内部声明,不作为独立提案;备选与共同产物"
                "不混队)", {"index": i},
                model_protocol_version=model_version)
        hypothesis_id = str(item.get("hypothesis_id") or "")
        if not hypothesis_id:
            _format_error(
                FORMAT_ERROR_JSON_FIELD,
                f"proposals[{i}] 缺 hypothesis_id(引用冻结池稳定 ID,"
                "或 novel 时经 proposal_context 声明)", {"index": i},
                model_protocol_version=model_version)
        if hypothesis_id in seen_ids:
            _format_error(
                FORMAT_ERROR_SYNTAX,
                f"proposals[{i}] 重复引用 {hypothesis_id}(幂等引用,"
                "不重复提案)", {"index": i, "hypothesis_id": hypothesis_id},
                model_protocol_version=model_version)
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
                    {"index": i, "hypothesis_id": hypothesis_id},
                    model_protocol_version=model_version)
            refs = context.get("reference_hypothesis_ids")
            if not isinstance(refs, list) or \
                    any(str(r) not in allowed for r in refs):
                _format_error(
                    FORMAT_ERROR_ALLOWED_ID,
                    f"proposals[{i}] 的 proposal_context.reference_"
                    "hypothesis_ids 必须是冻结池 ID 子集",
                    {"index": i, "hypothesis_id": hypothesis_id,
                     "reference_hypothesis_ids": refs},
                    model_protocol_version=model_version)
            if not str(context.get("output_origin") or ""):
                _format_error(
                    FORMAT_ERROR_JSON_FIELD,
                    f"proposals[{i}] 的 proposal_context 缺 output_origin"
                    "(明示来源)",
                    {"index": i, "hypothesis_id": hypothesis_id},
                    model_protocol_version=model_version)
            if product_first_path:
                # ---- EXP1:产物优先 novel(只声明产物;程序编译核验) ----
                reaction_spec = item.get("reaction_spec")
                if not isinstance(reaction_spec, dict) or not reaction_spec:
                    _format_error(
                        FORMAT_ERROR_JSON_FIELD,
                        f"proposals[{i}] 池外 novel 提案 {hypothesis_id} 缺"
                        " reaction_spec(产物优先协议:reaction_spec."
                        "product_smiles 必填,可选 coproducts;无产物不能"
                        "授有效 hypothesis)",
                        {"index": i, "hypothesis_id": hypothesis_id,
                         "novel_reaction_spec_missing": True},
                        model_protocol_version=model_version)
                # ---- PC8(CC 2026-11-06 拍板):产物优先分支对模型自写
                # 的池侧声明键(participants/co_substrate_states/
                # declared_copy_components 等 reaction_spec 多余键)**静默
                # 忽略并记录键名** —— 事件参与物只能来自编译器生成的
                # spec,模型响应不得透传角色/系数/共底物/拷贝组分。
                # (atom_edit 分支维持 D2b 的拒收判据,见下方 else 分支;
                # 本次只翻转产物优先分支,helper 与常量原样保留。)
                ignored_spec_keys = sorted(
                    key for key in reaction_spec
                    if key not in ("product_smiles", "coproducts"))
                product_smiles = reaction_spec.get("product_smiles")
                if not isinstance(product_smiles, str) or \
                        not product_smiles.strip():
                    _format_error(
                        FORMAT_ERROR_JSON_FIELD,
                        f"proposals[{i}] 的 reaction_spec.product_smiles "
                        "必须是非空字符串(产物优先协议只声明产物)",
                        {"index": i, "hypothesis_id": hypothesis_id,
                         "novel_product_smiles_missing": True},
                        model_protocol_version=model_version)
                spec_coproducts = reaction_spec.get("coproducts")
                if spec_coproducts is not None and \
                        not isinstance(spec_coproducts, list):
                    _format_error(
                        FORMAT_ERROR_JSON_TYPE,
                        f"proposals[{i}] 的 reaction_spec.coproducts 必须"
                        "是 list(可选;每个元素是 SMILES 字符串)",
                        {"index": i, "hypothesis_id": hypothesis_id},
                        model_protocol_version=model_version)
                if isinstance(spec_coproducts, list) and any(
                        not isinstance(c, str) for c in spec_coproducts):
                    _format_error(
                        FORMAT_ERROR_JSON_TYPE,
                        f"proposals[{i}] 的 reaction_spec.coproducts 元素"
                        "必须是 SMILES 字符串",
                        {"index": i, "hypothesis_id": hypothesis_id},
                        model_protocol_version=model_version)
                entry["origin"] = "novel"
                entry["proposal_context"] = dict(context)
                # 只保留产物优先协议消费的两键(模型多写的 edits/donor
                # 等一律忽略 —— 产物优先语义不消费原子编辑);被忽略的
                # 多余键名逐条记录(PC8 机器断言面;空列表也附加)
                entry["ignored_spec_keys"] = list(ignored_spec_keys)
                entry["reaction_spec"] = {
                    "product_smiles": product_smiles.strip(),
                    "coproducts": [str(c) for c in (spec_coproducts or [])],
                }
                raw_fb_edits = (
                    reaction_spec.get("fallback_edits")
                    if isinstance(reaction_spec.get("fallback_edits"), list)
                    else reaction_spec.get("edits")
                )
                if isinstance(raw_fb_edits, list):
                    fb_clean = [
                        dict(e) for e in raw_fb_edits if isinstance(e, dict)
                    ]
                    if fb_clean:
                        entry["fallback_edits"] = fb_clean
            else:
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
                         "novel_reaction_spec_missing": True},
                        model_protocol_version=model_version)
                # D2b:novel reaction_spec 禁键拒收(atom_edit 分支原本整
                # dict 原样透传 ⇒ 三键可混入下游 prepare_hypothesis 的
                # 参与物/共底物装配;现一律格式错误,不透传一条)
                _reject_novel_reaction_spec_forbidden_keys(
                    reaction_spec, index=i, hypothesis_id=hypothesis_id,
                    model_protocol_version=model_version)
                entry["origin"] = "novel"
                entry["proposal_context"] = dict(context)
                entry["reaction_spec"] = dict(reaction_spec)
        coproducts = item.get("coproducts")
        if coproducts is not None and not isinstance(coproducts, list):
            _format_error(
                FORMAT_ERROR_JSON_TYPE,
                f"proposals[{i}] 的 coproducts 必须是 list(假设内部共同"
                "产物声明)", {"index": i},
                model_protocol_version=model_version)
        if coproducts is not None:
            entry["coproducts"] = [str(c) for c in coproducts]
        proposals.append(entry)
    rank_raw = payload.get("rank_hypotheses")
    if rank_raw is None:
        rank_raw = [p["hypothesis_id"] for p in proposals]
    if not isinstance(rank_raw, list):
        _format_error(
            FORMAT_ERROR_JSON_TYPE,
            f"rank_hypotheses 必须是 list,得到 {type(rank_raw).__name__}",
            model_protocol_version=model_version)
    rank: list[str] = []
    for i, rid in enumerate(rank_raw):
        rid = str(rid)
        if rid not in seen_ids:
            _format_error(
                FORMAT_ERROR_ALLOWED_ID,
                f"rank_hypotheses[{i}] 引用未在提案集合内的 {rid}"
                "(rank 引稳定 ID)",
                {"index": i, "hypothesis_id": rid},
                model_protocol_version=model_version)
        rank.append(rid)
    return {"proposals": proposals, "rank_hypotheses": rank,
            "abstained": not proposals,
            "protocol_version": model_version}


def _feedback_versions(ledger: SearchLedger, run_id: str) -> dict:
    """冻结策略块 → 反馈版本/协议版本/可反馈类别(单一映射,登记与
    复用人共用;A 臂 v1 块 ⇒ 旧类别与旧版本)。"""
    policy = feedback_policy_from_ledger(ledger, run_id)
    feedback_version = str(policy["version"])
    eligible = (FEEDBACK_ELIGIBLE_PRODUCT_FIRST
                if feedback_version ==
                FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
                else FEEDBACK_ELIGIBLE)
    return {
        "policy": policy,
        "feedback_version": feedback_version,
        "model_protocol_version": protocol_version_for(feedback_version),
        "eligible": eligible,
    }


def feedback_policy_from_ledger(ledger: SearchLedger,
                                run_id: str) -> dict:
    """从 run 的冻结策略块读取格式反馈策略(严格消费;块缺/坏 ⇒
    SearchRecoveryError 由 _limits 同源包装,不补默认)。

    EXP1:期望版本按**同一冻结块里的 ``novel_protocol``** 判定(A 臂/
    旧块无该键 ⇒ atom_edit ⇒ ``ppv1-format-feedback-1``;product_first
    ⇒ ``ppv1-format-feedback-2``),两版各自可过、严格相等 —— 旧 run
    的 v1 块不受影响,坏/错配块消费前拒。
    """
    block = ledger.search_policy_block(run_id)
    block_dict = block if isinstance(block, dict) else {}
    policy = block_dict.get("format_feedback_policy")
    try:
        protocol = validate_novel_protocol(block_dict.get("novel_protocol"))
        expected = format_feedback_policy_version_for(protocol)
        return validate_frozen_format_feedback_policy(
            policy, expected_version=expected)
    except ValueError as exc:
        raise ModelProtocolError(
            f"run {run_id} 的冻结格式反馈策略块非法(严格核验,不补"
            f"默认、不猜迁移):{exc}",
            {"run_id": run_id, "kind": "format_feedback_policy_corrupt",
             "reason": str(exc)[:300]}) from exc


def format_feedback_rounds_used(ledger: SearchLedger,
                                action_id: str) -> int:
    """同 action 已发生的格式反馈轮数(持久事实源 = model_requests
    行;不是内存计数,内存重置仍从记录复算)。

    chain14 transport 重试(2026-10-15):``retry_of != ''`` 的行是既有
    轮的传输重试(同轮的第二次 HTTP 逻辑尝试),不是新的一轮 —— 计数
    排除,反馈轮预算语义不变(传输重试不越 max_format_feedback_
    rounds)。"""
    row = ledger.conn.execute(
        "SELECT COUNT(*) FROM model_requests WHERE action_id = ? AND"
        " purpose = ? AND retry_of = ''",
        (action_id, PURPOSE_FORMAT_FEEDBACK)).fetchone()
    return int(row[0])


def latest_format_feedback_round(
    ledger: SearchLedger,
    *,
    run_id: str,
    action_id: str,
    attempt_id: str,
    provider_kind: str,
    error: ModelProtocolError,
    response_excerpt: str,
    round_index: int | None = None,
) -> dict | None:
    """同 action 指定/最新一轮格式反馈的登记行(无轮 ⇒ None;复用前
    统一身份核验,任一不符 ⇒ 结构化拒)。

    ``round_index``:EXP1 多轮循环(B 臂至多 3 轮)按**具体轮号**取原行
    —— 缺省 None = 既有语义(取第 rounds_used 轮 = 最新轮,A 臂单轮
    路径逐字节不变);轮号 > 已登记轮数 ⇒ None(调用方走新轮登记,
    轮数/每题预算判据不变)。

    chain14 P1-2 余项(2026-10-16 复核 §⑤.1):resume 重入反馈分支时
    **先查既有轮** —— 有轮 ⇒ 复用该行(原请求键
    ``format-feedback:{action}:{round}``,不分配新轮、不为恢复另发
    付费请求),其未消费的完整响应经 ppv1_real_fetch 行状态机零调用
    消费(responded+完整 blob ⇒ R3 重放;failed ⇒ 唯一重试终态链;
    registered ⇒ 补首发;坏 blob/错身份 ⇒ 维持拒绝)。无既有轮才走
    新轮登记(register_format_feedback_round 的轮数/每题预算判据
    不变 —— 预算第 4 次发送前拒保持)。

    **P1-2 收口轮(2026-10-16 第四轮,findings §三)**:复用之前
    **统一核验原登记身份/内容/执行引用**,由所有适用状态分支共用
    (本门在 ppv1_real_fetch 状态机之前一次性闭合,responded/sent/
    registered/failed 消费的均为已核验行)。判据清单(全或无;任一
    不符 ⇒ ``feedback_round_identity_corrupt`` 结构化拒,坏记录
    保全,不分配新轮掩盖、不重算新键):

    1. **原键确定性重算**:轮序由持久计数承载(format_feedback_
       rounds_used,retry_of='' 行)⇒ 最新轮 = 第 rounds_used 轮,
       其 request_id 由原登记键 (action, round) 重算 —— 同键复算,
       不是换键;跨 attempt/跨通道不跨源复用(request_id 派生输入
       含两者);
    2. **计数>0 却查不到应有原行 ⇒ 结构化拒**:原行 request_id 被
       改坏(键缺失)时不返回 None —— 返回 None 会让调用侧走新轮
       登记(rounds_used+1 构成新键)另发一次并洗掉坏记录;结构化
       拒绝维持原状(零新增调用、零新轮);
    3. **逐列身份一致**:查到行的 purpose/run_id/action_id/
       attempt_id/provider_kind/retry_of 必须与原登记事实(即本
       调用身份:同一 run/action/attempt/通道;反馈轮首发行
       retry_of='')逐列一致 —— 存储行被改坏后原参数查找仍命中
       (request_id 列未被改),列比对揭示篡改;
    4. **payload_hash 同源确定性重算核验**:反馈登记载荷只含同源
       可重算内容(版本/轮次/错误类别/错误明细/响应摘录;登记时间
       由 model_requests.created_at 承载,不在载荷内 ⇒ 无
       recorded_at 可重算冒充),按本调用当前解析错误与重放响应
       重算 content_hash 并与存储 payload_hash 比对 —— 原行
       payload_hash 被改坏、或原登记并非本次错误/响应 ⇒ 拒(不以
       重新生成内容身份洗掉坏记录)。

    行状态机消费(responded⇒R3 重放/failed⇒唯一重试终态链/
    registered⇒补首发)在 ppv1_real_fetch。"""
    rounds_used = format_feedback_rounds_used(ledger, action_id)
    if rounds_used <= 0:
        return None
    target_round = (rounds_used if round_index is None
                    else int(round_index))
    if target_round <= 0 or target_round > rounds_used:
        # 该轮尚未登记(多轮循环的下一个待登记轮)⇒ None,由调用方走
        # 新轮登记(轮数上限判据不变)
        return None

    def _reject(reason: str, message: str, **extra) -> None:
        raise ModelProtocolError(
            message,
            {"kind": "feedback_round_identity_corrupt",
             "reason": reason, "rounds_used": rounds_used, **extra})

    request_id = stable_id(
        "sreq", str(run_id), str(attempt_id), str(provider_kind),
        f"format-feedback:{action_id}:{target_round}")
    row = ledger.conn.execute(
        "SELECT * FROM model_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    if row is None:
        # 判据 2:计数>0 却查不到应有原行 ⇒ 结构化拒(不返回 None 走
        # 新登记 —— 那会以 rounds_used+1 另配新轮/新键洗掉坏记录;
        # 维持原状:零新增调用、零新轮、坏行保全)
        _reject(
            "original_row_missing",
            f"格式反馈轮计数 {rounds_used}>0 但按原登记键重算的请求"
            f"{request_id} 查不到原行(原行 request_id 被改坏/键缺失;"
            "结构化拒,不返回无轮、不分配新轮另发、不重算新键掩盖;"
            "坏记录保全)")
    feedback = dict(row)
    conflicts: dict = {}
    purpose = str(feedback.get("purpose") or "")
    if purpose != PURPOSE_FORMAT_FEEDBACK:
        conflicts["purpose"] = purpose
    if str(feedback.get("run_id") or "") != str(run_id):
        conflicts["run_id"] = str(feedback.get("run_id") or "")
    if str(feedback.get("action_id") or "") != str(action_id):
        conflicts["action_id"] = str(feedback.get("action_id") or "")
    if str(feedback.get("attempt_id") or "") != str(attempt_id):
        conflicts["attempt_id"] = str(feedback.get("attempt_id") or "")
    if str(feedback.get("provider_kind") or "") != str(provider_kind):
        conflicts["provider_kind"] = str(feedback.get("provider_kind") or "")
    if str(feedback.get("retry_of") or "") != "":
        conflicts["retry_of"] = str(feedback.get("retry_of") or "")
    versions = _feedback_versions(ledger, run_id)
    expected_payload = {
        "feedback_version": versions["feedback_version"],
        "model_protocol_version": versions["model_protocol_version"],
        "round": target_round,
        "error_kind": str(error.detail.get("kind") or ""),
        "error_detail": dict(error.detail),
        "response_excerpt": str(response_excerpt)[:2000],
    }
    stored_hash = str(feedback.get("payload_hash") or "")
    if stored_hash != content_hash(expected_payload):
        conflicts["payload_hash"] = stored_hash
    if conflicts:
        # 判据 3/4:逐列身份或原登记内容与本调用不符 ⇒ 结构化拒
        # (purpose 被篡改且仍被计数排除的旧路径由同键重登记撞
        # S3A-04 同键身份冲突兜底,不掩盖)
        _reject(
            "identity_conflict",
            f"格式反馈轮 {feedback.get('request_id')} 复用前统一身份"
            f"核验失败({sorted(conflicts)};原登记身份/内容/执行引用"
            "与本调用不一致;坏记录保全,不分配新轮掩盖、不重算新键、"
            "不重新生成内容身份,维持拒绝)",
            request_id=str(feedback.get("request_id") or ""),
            conflicts=conflicts)
    return feedback


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
      EXP1:product_first 臂(v2 策略块)额外允许
      ``novel_verification_failed``(程序核验失败;内容按预注册 §5
      白名单),A 臂 v1 策略块下该类别仍不可登记;
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
    versions = _feedback_versions(ledger, run_id)
    kind = str(error.detail.get("kind") or "")
    if kind not in versions["eligible"]:
        eligible = sorted(versions["eligible"])
        raise ModelProtocolError(
            f"错误类别 {kind!r} 不可进格式反馈(当前策略 "
            f"{versions['feedback_version']} 仅 {eligible};"
            "structure_unparseable 记结构失败)",
            {"kind": "feedback_ineligible_error", "error_kind": kind,
             "feedback_version": versions["feedback_version"]})
    policy = versions["policy"]
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
             "policy_version": versions["feedback_version"]})
    round_index = rounds_used + 1
    # P1-2 收口轮(2026-10-16 findings §三):载荷只含**同源确定性
    # 可重算**内容(版本/轮次/错误类别/错误明细/响应摘录)—— 登记时间
    # 由 model_requests.created_at 持久承载,不入载荷 ⇒ payload_hash
    # 可在复用前按本调用事实重算核验(latest_format_feedback_round
    # 判据 4),不存在"以新 recorded_at 重新生成 payload 冒充原内容"
    # 的面。同键幂等(S3A-04 r3)因此对完好行也逐列可核。
    payload = {
        "feedback_version": versions["feedback_version"],
        "model_protocol_version": versions["model_protocol_version"],
        "round": round_index,
        "error_kind": kind,
        "error_detail": dict(error.detail),
        "response_excerpt": str(response_excerpt)[:2000],
    }
    return ledger.register_model_request(
        run_id=run_id, action_id=action_id, attempt_id=attempt_id,
        provider_kind=provider_kind,
        request_key=f"format-feedback:{action_id}:{round_index}",
        purpose=PURPOSE_FORMAT_FEEDBACK, payload=payload)
