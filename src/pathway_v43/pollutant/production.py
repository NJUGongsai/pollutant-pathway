"""S3b 生产链 —— 固定 AtomTool → 供体诊断 → center evidence converter →
audit → admission → 事件提交(实施书 §6.1;契约随 search-5 登记)。

固定调用链(**顺序不可调换**;每段用现成冻结接口,不另造判据):

    AtomTool 真实输出(render + execute_edits)
      → check_edit_against_donor(供体诊断,含 proof_record)
      → center_evidence_from_donor_diagnostic(converter,不另手造 verified)
      → audit_hypothesis(首消费守卫:state/context/hypothesis/ledger)
      → decide_admission(R1–R7 决策表)
      → build/submit_event(公共 store writer,全部首消费验证)
      → complete_action(搜索记账;B4 后半段)

异常义务(R8 P2 ⑧,S3 首个生产 caller):**AuditContractError 不得吞成
verified/R6/成功提交** —— 本模块任何函数都不捕获 AuditContractError
(原样上抛,中止本次 admission/提交;写入只发生在 audit+admission
之后,异常 ⇒ 零事件/零提交/零完成)。调用方(runflow 驱动)只在
action 分发层窄捕获以记录方法失败并调度独立备选,不以捕获结果
继续本次 admission/submit。三个 None 与缺 proof 保持 unknown:
execution_ok=False 的诊断三判定字段全 None、center_evidence 空,
converter 仍返回版本/来源元数据 + center_match=None —— audit 保留
中心 unknown,admission 按 R5 有界探索,不授 verified;缺证据/映射
的 None 或空 payload 不是契约异常也不是执行失败。执行失败
(execution_ok=False)记方法失败(method_failed),不伪装成功工具
结果,允许调度独立备选。

入口矩阵:

| # | 入口 | 消费 | 校验/事务 |
| 1 | prepare_hypothesis | 池条目 spec(产物/共同产物/要求/依赖/工具输入) | build_chemical_state 工厂守卫(对工具已确定的产品只能引用,不暗改结构);build_hypothesis 全部 H02/H03/锚点/要求契约;spec 契约(缺产物/坏编辑形状结构化拒) |
| 2 | execute_atomtool_expansion | 底物 SMILES + 编辑协议 | 冻结 AtomTool render/execute_edits(真实执行,不伪造);check_edit_against_donor 冻结契约;converter 透传绑定证据载荷;零写账 |
| 3 | expand_hypothesis_production | 冻结假设/状态/上下文 + action 认领 | audit_hypothesis 首消费守卫(state/context 对象验证;center_evidence 绑定/类型/复算 —— 契约异常上抛);decide_admission 决策表;事件提交走 ledger.submit_action_event(公共 writer,冻结身份);complete_action(S3A-02 完整权威核验) |
| 4 | persist_context / load_context | PathContext 对象 / 存储载荷 | 写:to_dict 全语义载荷;读:read_search_artifact(H07 包装)+ PathContext.from_dict 内容身份核验(首消费守卫;篡改语义字段保留旧 context_id ⇒ 拒)+ **S5a r3(S5A-05)引用绑定核验**:H07+from_dict 完成后、返回/派生/评估/审核前,核请求 context_ref == 恢复载荷 context_id —— 旧 `ctx:<ref>` 地址下的自洽新身份 ⇒ 结构化拒(旧引用不复用;合法重建须存新地址沿新引用;保全坏 artifact,不重封覆盖、不猜迁移、不默发新引用;selfhash 重算正确不能替代旧引用绑定)。runflow decide/expand/scenario_transition 与 endpoint 三处派生消费共用本入口的同一守卫,不各自另造规则 |
| 5 | build_cyclic_dependency | 依赖 spec(共底物循环 H04) | Dependency 契约(status 三值;resolution_log 逐轴事实源);缺启动供给 ⇒ unresolved + unresolved_initial_supply(不称化学不可能);有支持 ⇒ supported 不自动阻断 |

分段负控(任务书 §6.1;对应测试逐段断言):合法工具链;工具
execution_ok=False;缺/歧义映射;strict 目标偏离;proof 更改/跨假设
复用;复杂共底物不能只凭配平升级(completion_license 由 audit 既有
判据保留);契约异常中止本次 audit/admission/成功提交。
"""

from __future__ import annotations

from .audit import (
    AuditContractError,
    AdmissionPolicy,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from .chemstate import build_chemical_state
from .events import (
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from .hypothesis import Participant, build_hypothesis
from .path_context import (
    ConditionContractError,
    Dependency,
    PathContext,
    SUPPORT_AXIS_INITIAL_SUPPLY,
)
from .search import (
    COMMIT_KIND_EVENT,
    SearchContractError,
    SearchCrashInjection,
    SearchLedger,
    read_search_artifact,
)
from ..domain.models import content_hash
from ..services.atom_tool import execute_edits, render

SEARCH_PRODUCTION_VERSION = "ppv1-search-production-2"
# -2(S5a 回修 r3,2026-10-09,复审 R3 §4 S5A-05):load_context 首消费
# 增加引用绑定核验 —— H07+from_dict 完成后、实际消费前,请求
# context_ref 必须等于恢复载荷 context_id;旧 ctx: 存储键下的自洽
# 新身份(重算 selfhash/重封 H07 均不豁免)⇒ 结构化拒。冻结判据四
# "重建半边"的兑现:合法新内容新 ID 存新地址沿新引用,旧引用不复用。
# production 链其余行为零变化。-1 报告按既有版本门策略消费。
CONTEXT_ARTIFACT_NAME = "path_context"

# admission 处置与驱动语义的映射(expand/retain_conditional ⇒ 事件可
# 提交(后者 unknown 保留有界探索);reject ⇒ 不提交;defer ⇒ 假设
# 保留不提交当前场景)
ADMISSION_SUBMITTABLE = frozenset({"expand", "retain_conditional"})


class ProductionContractError(SearchContractError):
    """生产链输入/形状契约违反(结构化,零写入)。"""


# ---------------------------------------------------------------- 假设构建


def build_product_state(smiles: str, *, source_refs: list[dict] | None,
                        origin: str = "source_product"):
    """构建产物状态(工厂守卫;对工具已确定的产品只能引用 —— 状态
    身份由结构内容派生,调用方不得暗改结构;executed 产物经同一工厂
    与声明产物同构时同 state_id)。"""
    return build_chemical_state(smiles, origin, source_refs or [])


def build_cyclic_dependency(spec: dict) -> Dependency:
    """H04 共底物循环依赖构建(§5.2:有启动供应/再生支持不能自动阻断;
    缺支持标 unresolved_initial_supply,按显式、版本化策略处理,不称
    化学不可能)。

    spec: {"dependency_id", "kind"=cosubstrate_supply, "statement",
    "cyclic": bool, "initial_supply": "supported"|"missing",
    "source_refs": [...]}
    - initial_supply=missing ⇒ status=unresolved,statement 带
      unresolved_initial_supply 标记(audit 依赖轴 unknown ⇒ R5
      retain_conditional,不 reject;不能称化学不可能);
    - supported ⇒ resolution_log 记 initial_supply 轴 supported
      (Dependency 从轨迹同源重推导 status;不自动阻断)。
    """
    if not isinstance(spec, dict) or not spec.get("dependency_id"):
        raise ProductionContractError(
            "依赖 spec 缺 dependency_id", {"kind": "dependency_spec_invalid"})
    dep_id = str(spec["dependency_id"])
    kind = str(spec.get("kind") or "cosubstrate_supply")
    statement = str(spec.get("statement") or "")
    initial_supply = str(spec.get("initial_supply") or "")
    if initial_supply not in ("supported", "missing"):
        raise ProductionContractError(
            f"依赖 {dep_id} 的 initial_supply 非法:{initial_supply!r}"
            "(supported|missing;显式声明,不猜)",
            {"kind": "dependency_initial_supply_invalid",
             "dependency_id": dep_id})
    resolution_log: list[dict] = []
    status = "unresolved"
    if initial_supply == "supported":
        resolution_log.append({
            "support_axis": SUPPORT_AXIS_INITIAL_SUPPLY,
            "resolution": "supported",
            "source_ref": str((spec.get("source_refs") or [""])[0]),
        })
        status = "supported"
    else:
        statement = (statement + ";" if statement else "") + (
            "unresolved_initial_supply(共底物循环缺启动/再生供给支持;"
            "按显式、版本化策略处理,不称化学不可能)")
    return Dependency(
        dependency_id=dep_id, kind=kind, statement=statement,
        status=status,
        source_refs=tuple(str(r) for r in (spec.get("source_refs") or [])),
        resolution_log=tuple(resolution_log))


def prepare_hypothesis(
    spec: dict,
    *,
    parent_path_id: str,
    substrate_state,
    source_refs: list[dict] | None = None,
    transformation_ref: str = "",
) -> dict:
    """池条目 spec → 冻结假设 + 状态集 + 工具输入(单一构建源:调度
    (取 hypothesis_id 进 action 身份)与执行(重建同一对象)共用,
    同输入同 ID,不各写第二套派生)。

    spec 契约(缺/坏 ⇒ ProductionContractError,零写入):
    - product_smiles:主产物(工具已确定,引用不改);
    - coproducts:共同产物 SMILES 列表(假设内部共同产物,不与备选
      混队);
    - edits/donor/alignment/expectation:AtomTool 编辑协议输入
      (check_edit_against_donor 的契约形状);
    - requirements:必要要求 dict 列表(build_hypothesis 契约);
    - dependencies:依赖 spec 列表(H04,经 build_cyclic_dependency);
    - participants:可选显式参与物覆盖(系数/角色;默认底物 1 + 主
      产物 1 + 共同产物逐条,系数按声明或 unknown)。
    返回 {hypothesis, states, product_states, tool_inputs, spec_digest}。
    """
    if not isinstance(spec, dict):
        raise ProductionContractError(
            f"池条目 spec 必须是 dict,得到 {type(spec).__name__}",
            {"kind": "spec_invalid_type"})
    product_smiles = str(spec.get("product_smiles") or "")
    if not product_smiles:
        raise ProductionContractError(
            "池条目缺 product_smiles(工具已确定的主产物,只能引用)",
            {"kind": "spec_missing_product"})
    coproducts = spec.get("coproducts") or []
    if not isinstance(coproducts, list):
        raise ProductionContractError(
            "coproducts 必须是 list(假设内部共同产物)",
            {"kind": "spec_coproducts_invalid"})
    for field in ("edits", "donor", "alignment", "expectation"):
        value = spec.get(field)
        if field == "edits" and not isinstance(value, list):
            raise ProductionContractError(
                f"spec.edits 必须是 list(冻结 AtomTool 编辑协议),得到 "
                f"{type(value).__name__}",
                {"kind": "spec_edits_invalid"})
        if field != "edits" and not isinstance(value, dict):
            raise ProductionContractError(
                f"spec.{field} 必须是 dict(供体诊断输入契约),得到 "
                f"{type(value).__name__}",
                {"kind": f"spec_{field}_invalid"})
    refs = source_refs or [{"record": "synthetic-pool-spec"}]
    product_state = build_product_state(product_smiles, source_refs=refs)
    coproduct_states = [
        build_product_state(str(c), source_refs=refs) for c in coproducts]
    dependencies = [
        build_cyclic_dependency(d)
        for d in (spec.get("dependencies") or [])]
    participants_spec = spec.get("participants")
    if participants_spec is not None:
        participants = [
            Participant(**dict(p)) for p in participants_spec]
    else:
        coefficient = spec.get("coefficient")
        coefficient_status = ("known" if coefficient is not None
                              else "unknown")
        participants = [
            Participant(
                state_ref=substrate_state.state_id, side="reactant",
                role="primary_substrate",
                coefficient=(coefficient if coefficient is not None else None),
                coefficient_status=coefficient_status),
            Participant(
                state_ref=product_state.state_id, side="product",
                role="principal_product",
                coefficient=(coefficient if coefficient is not None else None),
                coefficient_status=coefficient_status),
        ]
        for state in coproduct_states:
            participants.append(Participant(
                state_ref=state.state_id, side="product", role="coproduct",
                coefficient=None, coefficient_status="unknown"))
    requirements = [
        dict(r) for r in (spec.get("requirements") or [])]
    hypothesis = build_hypothesis(
        parent_path_id=parent_path_id,
        substrate_state_ref=substrate_state.state_id,
        participants=participants,
        participant_list_status=str(spec.get("participant_list_status")
                                    or "partial"),
        step_scope=str(spec.get("step_scope") or "net_reaction"),
        transformation_ref=transformation_ref,
        requirements=requirements,
        dependency_refs=[d.dependency_id for d in dependencies],
        origin_group_key=str(spec.get("origin_group_key") or ""))
    states = {substrate_state.state_id: substrate_state,
              product_state.state_id: product_state}
    for state in coproduct_states:
        states[state.state_id] = state
    tool_inputs = {
        "edits": list(spec["edits"]),
        "donor": dict(spec["donor"]),
        "alignment": dict(spec["alignment"]),
        "expectation": dict(spec["expectation"]),
    }
    return {
        "hypothesis": hypothesis,
        "states": states,
        "product_states": [product_state] + coproduct_states,
        "dependencies": dependencies,
        "tool_inputs": tool_inputs,
        "spec_digest": content_hash(spec),
        "hypothesis_dict": hypothesis.to_dict(),
    }


# ---------------------------------------------------------------- 工具执行


def execute_atomtool_expansion(*, substrate_smiles: str, tool_inputs: dict,
                               render_name: str = "S") -> dict:
    """固定链第一段:冻结 AtomTool 真实渲染+执行 → 供体诊断 →
    converter(**零写账**;返回全部真实执行事实)。

    - render/execute_edits 是冻结工具的真实调用(不伪造、不 mock
      结果;工具内部失败如实返回 ok=False);
    - check_edit_against_donor 消费真实执行输出(current/donor/
      alignment/expectation/result/edits 全输入集;诊断自带
      proof_record 供 audit 内部复算);
    - converter 不另手造 verified 中心结论(透传诊断绑定证据载荷;
      execution_ok=False ⇒ 三判定字段 None + center_evidence 空字典
      ⇒ converter 返回元数据 + center_match=None —— None 是未评估,
     不是通过);
    - 保存真实执行前后/atom_id_map/edits/donor/alignment/expectation/
      result(供审计与恢复消费)。
    """
    edits = tool_inputs.get("edits") or []
    current = render(substrate_smiles, render_name)
    result = execute_edits(current, edits)
    diagnostic = check_edit_against_donor(
        current={"smiles": substrate_smiles,
                 "atom_id_map": dict(current.atom_id_map)},
        donor=dict(tool_inputs.get("donor") or {}),
        alignment=dict(tool_inputs.get("alignment") or {}),
        expectation=dict(tool_inputs.get("expectation") or {}),
        result=result, edits=edits)
    center_evidence = center_evidence_from_donor_diagnostic(diagnostic)
    return {
        "production_version": SEARCH_PRODUCTION_VERSION,
        "substrate_smiles": substrate_smiles,
        "render": {
            "input_smiles": current.smiles,
            "canonical_smiles": current.canonical_smiles,
            "atom_id_map": dict(current.atom_id_map),
        },
        "result": dict(result),
        "execution_ok": bool(result.get("ok")),
        "diagnostic": diagnostic.to_dict(),
        "center_evidence": dict(center_evidence),
        "tool_inputs": {
            "edits": list(edits),
            "donor": dict(tool_inputs.get("donor") or {}),
            "alignment": dict(tool_inputs.get("alignment") or {}),
            "expectation": dict(tool_inputs.get("expectation") or {}),
        },
    }


# ---------------------------------------------------------------- 上下文持久


def persist_context(artifact_store, context: PathContext) -> str:
    """上下文持久化(artifact;载荷 = to_dict 全语义字段;context_id
    内容身份冻结)。返回 context_id(= 存储键)。"""
    if artifact_store is None:
        raise ProductionContractError(
            "持久化上下文需要 artifact_store", {"kind": "artifact_store_missing"})
    artifact_store.write(
        f"ctx:{context.context_id}", CONTEXT_ARTIFACT_NAME,
        context.to_dict())
    return context.context_id


def load_context(artifact_store, context_ref: str) -> PathContext:
    """上下文首消费(H07 完整性包装 + from_dict 内容身份核验 + S5a r3
    引用绑定核验)。

    三层守卫逐层分测、共用本入口(消费侧单一守卫,不各自另造规则):

    - H07:信封 hash/可解析(保全原文件,search.read_search_artifact);
    - from_dict 内容身份:载荷 context_id 与按全部语义字段同源重算
      一致(篡改任何语义字段保留旧 context_id ⇒ 拒,不得洗绿);
    - **S5A-05(r3)引用绑定**:H07+from_dict 完成后、返回/派生/评估/
      审核前,核**请求 context_ref == 恢复载荷 context_id** —— selfhash
      重算正确不能替代旧引用绑定:旧 ``ctx:<context_ref>`` 存储键下
      换入自洽新 context_id(重封 H07 亦同)⇒ 结构化拒,披露期望
      引用/实际身份;坏 artifact 保全,不重封覆盖、不猜迁移、不默发
      新引用。合法重建语义上下文(冻结判据四"重建半边")须用新
      context_id 存**新地址**并沿新引用首消费(保留 parent_context_
      ref 链),旧地址/旧引用不复用。
    """
    if artifact_store is None:
        raise ProductionContractError(
            "读取上下文需要 artifact_store", {"kind": "artifact_store_missing"})
    envelope = read_search_artifact(
        artifact_store, f"ctx:{context_ref}", CONTEXT_ARTIFACT_NAME)
    context = PathContext.from_dict(envelope["payload"])
    # ---- S5A-05(S5a r3):首消费引用绑定(消费侧守卫;冻结侧
    # path_context 判决零改动)。from_dict 只证明载荷自洽,不证明
    # 请求/行动引用的就是这份内容 —— 旧地址下的新身份即旧引用
    # 复用,须在实际消费前拒(ConditionContractError 与内容身份
    # 同族,公共 resume 边界同形结构化失败,不吞成 run_error)。 ----
    if context.context_id != context_ref:
        raise ConditionContractError(
            "上下文引用绑定不一致:请求 context_ref 与恢复载荷"
            " context_id 不符(旧 ctx: 存储键下的自洽新身份 ⇒ 拒;"
            "合法重建须用新 context_id 存新地址并沿新引用首消费,"
            "旧引用不复用;坏 artifact 保全,不重封覆盖、不猜迁移、"
            "不默发新引用;selfhash 重算正确不能替代引用绑定)",
            {"kind": "context_reference_binding_mismatch",
             "expected_context_ref": str(context_ref),
             "recovered_context_id": context.context_id,
             "storage_key": f"ctx:{context_ref}",
             "parent_context_ref": context.parent_context_ref})
    return context


# ---------------------------------------------------------------- 生产链


def expand_hypothesis_production(
    ledger: SearchLedger,
    action_id: str,
    *,
    prepared: dict,
    context: PathContext,
    worker_id: str,
    attempt_id: str,
    task_key: str,
    substrate_state,
    limits: dict,
    depth: int,
    parent_search_revision: int = 0,
    admission_policy: AdmissionPolicy | None = None,
    write_bundle: bool = False,
    crash_after: str | None = None,
) -> dict:
    """固定生产链的 admission/提交段(§6.1;AuditContractError 原样
    上抛 —— 本函数不捕获,中止本次 admission/提交,零事件/零提交/
    零完成写入)。

    返回(结构化,不返回裸 bool):
    - status=method_failed:工具 execution_ok=False(诊断三 None,
      converter 元数据 + center_match=None;不伪装成功工具结果;调用
      方记方法失败并调度独立备选);
    - status=rejected / deferred:admission R1/R2/R3/R4(不提交事件;
      deferred 假设保留 —— 调用方按需 put_hypothesis 留痕);
    - status=submitted:事件经公共 writer 提交 + 搜索记账闭合(附
      展开计划驱动后续 followup;expand/retain_conditional 均提交,
      后者 unknown 保留)。

    crash_after 注入点(测试 B3/B4 边界,非生产路径):
    "bundle_written"(bundle 落盘、事件未提交)、"event_submitted"
    (事件已提交、记账未闭合)—— 抛 SearchCrashInjection。
    """
    hypothesis = prepared["hypothesis"]
    states: dict = prepared["states"]
    tool_inputs = prepared["tool_inputs"]

    def _report(status: str, **extra) -> dict:
        """生产链结论的持久报告 artifact(审查/复核用;派生报告,不是
        事件权威 —— 事件/假设/状态权威在公共 store,以公共 writer 为
        准)。写入失败按 artifact 契约上抛(不可覆盖)。"""
        payload = {
            "production_version": SEARCH_PRODUCTION_VERSION,
            "action_id": action_id, "attempt_id": attempt_id,
            "status": status, **extra}
        if isinstance(payload.get("event"), object) and                 not isinstance(payload.get("event"), (dict, list, str, int,
                                                       float, bool, type(None))):
            payload["event"] = None  # 事件权威在公共 store;报告只带 event_id
        if ledger.artifact_store is not None and task_key:
            ledger.artifact_store.write(
                task_key, "production_report", payload)
        return payload

    execution = execute_atomtool_expansion(
        substrate_smiles=substrate_state.smiles_isomeric,
        tool_inputs=tool_inputs)
    if not execution["execution_ok"]:
        # 执行失败:方法失败(不是契约异常;不伪装成功工具结果)。
        # 诊断三判定字段 None、center_evidence 空 —— converter 元数据
        # 已在 execution 内(None = 未评估,不是通过)。
        return _report("method_failed", execution=execution, admission=None,
                       event=None)
    # ---- audit(AuditContractError 原样上抛;首消费守卫在 audit 内) ----
    audit = audit_hypothesis(
        hypothesis, run_id=ledger.run_id or "", states=states,
        context=context, center_evidence=execution["center_evidence"])
    disposition, reasons = decide_admission(audit, policy=admission_policy)
    admission = {"disposition": disposition, "reasons": list(reasons)}
    if disposition not in ADMISSION_SUBMITTABLE:
        return _report(
            "deferred" if disposition == "defer" else "rejected",
            execution=execution, admission=admission, event=None,
            audit=audit.to_dict())
    # ---- 展开计划(宽度/深度预算不足只影响 followup,不删事件事实) ----
    # W1 #9(S5b HIT50):重复 state_ref 在计划生产者按 **distinct 状态**
    # 生成唯一调度条目(同 state 重复入队的展开/投影条目折叠;事件参与
    # 物/occurrence/计量语义不受本去重影响 —— 参与物侧完整保留在事件
    # 载荷,store 首提出现绑定按全部参与物闭合)。
    product_refs: list[str] = []
    for state in prepared["product_states"]:
        if state.state_id not in product_refs:
            product_refs.append(state.state_id)
    width = int(limits["max_product_expansion_width"])
    max_depth = int(limits["max_search_depth"])
    child_depth = int(depth) + 1
    expanded: list[str] = []
    deferred_products: list[str] = []
    plan_reasons: dict[str, str] = {}
    if child_depth > max_depth:
        deferred_products = list(product_refs)
        for ref in product_refs:
            plan_reasons[ref] = "depth_limit"
    else:
        # W1 #10:expanded/deferred 的取位序 = 参与物声明序(调用方
        # 冻结的产物位次),不是通用化学优先级;超出宽度走 deferred
        # (计划 reason 显式记 basis,不冒充化学排序)
        expanded = product_refs[:width]
        deferred_products = product_refs[width:]
        for ref in deferred_products:
            plan_reasons[ref] = "product_width_limit"
    max_reportable = max(1, min(width if width > 0 else 1, 4))
    event = build_pathway_event(
        hypothesis, run_id=ledger.run_id or "",
        context_hash=context.context_id)
    report_projection = build_report_projection(
        hypothesis, max_reportable=max_reportable,
        ranked_state_refs=product_refs)
    expansion_plan = build_expansion_plan(
        hypothesis, expanded=expanded, deferred=deferred_products,
        not_tracked=[], reasons=plan_reasons)
    states_dicts = [s.to_dict() for s in states.values()]
    hypothesis_dict = hypothesis.to_dict()
    if write_bundle:
        ledger.write_commit_bundle(
            action_id=action_id, attempt_id=attempt_id, event=event,
            report_projection=report_projection.to_dict(),
            expansion_plan=expansion_plan.to_dict(),
            states=states_dicts, hypothesis_dict=hypothesis_dict,
            task_key=task_key)
        if crash_after == "bundle_written":
            raise SearchCrashInjection(
                "bundle 已写、事件未提交(B3 注入点)",
                {"action_id": action_id, "task_key": task_key})
    submitted = ledger.submit_action_event(
        action_id, event, report_projection=report_projection.to_dict(),
        expansion_plan=expansion_plan.to_dict(), states=states_dicts,
        hypothesis_dict=hypothesis_dict, worker_id=worker_id)
    if crash_after == "event_submitted":
        raise SearchCrashInjection(
            "事件已提交、搜索记账未闭合(B4 注入点)",
            {"action_id": action_id, "event_id": event.event_id,
             "submitted": submitted})
    completed = ledger.complete_action(
        action_id, worker_id=worker_id, outcome_kind=COMMIT_KIND_EVENT,
        event_id=event.event_id)
    return _report(
        "submitted", execution=execution, admission=admission,
        audit=audit.to_dict(), event=event, event_id=event.event_id,
        submitted=submitted, completed=completed,
        expansion_plan=expansion_plan.to_dict(),
        report_projection=report_projection.to_dict(),
        child_depth=child_depth,
        parent_search_revision=int(parent_search_revision))
