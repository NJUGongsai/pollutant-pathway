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

import json

from .audit import (
    AuditContractError,
    AdmissionPolicy,
    audit_hypothesis,
    center_evidence_from_donor_diagnostic,
    check_edit_against_donor,
    decide_admission,
)
from .chemstate import build_chemical_state, strict_identity_of
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
from .profile import PPV1_PROVENANCE_SCHEMA_VERSION
from .search import (
    COMMIT_KIND_EVENT,
    SearchContractError,
    SearchCrashInjection,
    SearchLedger,
    read_search_artifact,
)
from ..domain.identity import cn_identity
from ..domain.models import content_hash
from ..services.atom_tool import execute_edits, render

SEARCH_PRODUCTION_VERSION = "ppv1-search-production-2"
# -2(S5a 回修 r3,2026-10-09,复审 R3 §4 S5A-05):load_context 首消费
# 增加引用绑定核验 —— H07+from_dict 完成后、实际消费前,请求
# context_ref 必须等于恢复载荷 context_id;旧 ctx: 存储键下的自洽新
# 身份(重算 selfhash/重封 H07 均不豁免)⇒ 结构化拒。冻结判据四
# "重建半边"的兑现:合法新内容新 ID 存新地址沿新引用,旧引用不复用。
# production 链其余行为零变化。-1 报告按既有版本门策略消费。
# W-D2-R1(2026-10-11,S5B-D2-01 回修;Codex D2 复审 §4/§8):
# prepare_hypothesis 的 NC-10 触发条件改挂记录侧单一声明来源
# (_cosubstrate_record_declaration;装配数组可删不再能关闭守卫)。
# 本语义差异按 D2 的登记面登记为 s5b-corpus-retrieval-4(共底物
# 事件契约消费语义;recorded_source.py 版本注释)——search-production
# 版本维持 -2(该契约自 D2 起即由 corpus-retrieval 语义块承载,不
# 硬升无关契约;复审 §7"按既有版本身份规则登记差异")。
# W-D2-R2(2026-10-11,S5B-D2-01 产物侧残余;Codex D2-R1 复审
# §4.2/§4.3/§8):NC-10 的记录产物权威改为**同源权威消费**——记录
# 装配在 contract.record_products 与 corpus.record_products 两处
# 声明同一产物(recorded_source 同一列表生成);首次消费先按既有
# strict_identity_of 键空间以**多重集**核对两处声明一致性(重复
# 组分保留意义,不用集合并集隐藏分歧;合法同义表示按 strict 键
# 规范),双来源在位而分歧 ⇒ 首次消费结构化拒(kind=
# cosubstrate_record_products_divergent;坏声明保全,不以被收缩的
# 一侧作新全量,不重算新身份洗掉);无第二来源(corpus 块不带
# record_products 列表)⇒ 单来源合法默认路径按既有契约处理,不全
# 面拒绝。配套 P2 落字:披露新增 consumer_discipline(消费者联读
# 生产报告义务与禁句)/bystander_cosubstrates(旁观型 unknown 机读
# 注记)/record_products_sources(实际消费的声明来源)。消费语义
# 差异按登记面升版 s5b-corpus-retrieval-5(recorded_source.py 版本
# 注释);search-production 维持 -2。
# W-D2-R3(2026-10-11,S5B-D2-01 最后残余;Codex D2-R2 复审
# §4.2/§4.3/§8):第二产物声明的**存在性与格式消费**分开"字段确
# 未声明"与"字段在位但损坏"——corpus.record_products 键在位而值
# 为 null/string/dict/bool 等非 list ⇒ 坏声明,首次消费结构化拒
# (kind=cosubstrate_corpus_record_products_corrupt;detail 披露
# 字段/类型/原因并保全原始坏值),不得以 isinstance(list) 作为
# 是否存在的判定把类型错误静默解释成"没有第二来源"降级成合法
# 单来源;键不在位(无第二声明处)⇒ 单来源合法默认路径维持。
# 同根同规则覆盖记录侧声明入口(_cosubstrate_record_declaration:
# corpus 块带 record_products 键即在位声明——空 list 是有效声明,
# 与非 list 坏形状同样不当缺省;在位而缺 contract ⇒ 缺契约拒,
# 不是回落 plain A→P)。contract 侧既有 list 门(cosubstrate_
# contract_missing)不退回;有效 list 继续走 strict 身份多重集同
# 源核验,重复组分保留意义。消费语义差异按登记面升版
# s5b-corpus-retrieval-6(recorded_source.py 版本注释);search-
# production 维持 -2。
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


def _verify_execution_input(spec: dict, *, substrate_state,
                            co_sub_entries: list[dict]) -> str | None:
    """C 线(s5b-analog-cosub-supply-1)执行输入首消费核验。

    spec 声明 ``execution_input_smiles``(伴生供给候选:edits 对底物
    +供给编译,运行期执行/审计渲染同一输入)⇒ 核验其组分严格身份
    多重集 == 底物 ⊕ 声明供给(精确多重集;不验字符串拼写,验分子
    内容——渲染 ID 由分子内容确定)。声明在而键缺失/形状坏/多重集
    不等 ⇒ ProductionContractError(零事件/零提交)。无声明(键不在)
    ⇒ None = 既有路径零变化(corpus 旁观 B 不参与执行,无此键)。
    """
    declared = spec.get("execution_input_smiles")
    if declared is None:
        return None
    if not isinstance(declared, str) or not declared.strip():
        raise ProductionContractError(
            "execution_input_smiles 在位但非法(必须非空 str)",
            {"kind": "execution_input_invalid",
             "value_type": type(declared).__name__})
    from rdkit import Chem as _Chem

    mol = _Chem.MolFromSmiles(declared)
    if mol is None:
        raise ProductionContractError(
            "execution_input_smiles 不可解析(执行输入声明带病;fail-"
            "closed,不以不可渲染输入进执行)",
            {"kind": "execution_input_unparseable",
             "smiles": declared[:200]})
    declared_components = [_Chem.MolToSmiles(frag)
                           for frag in _Chem.GetMolFrags(
                               mol, asMols=True, sanitizeFrags=True)]
    try:
        declared_keys = sorted(strict_identity_of(c)
                               for c in declared_components)
        required_keys = sorted(
            [strict_identity_of(substrate_state.smiles_isomeric)]
            + [strict_identity_of(str(e.get("smiles") or ""))
               for e in co_sub_entries])
    except Exception as exc:  # noqa: BLE001 —— 身份失败 = 声明带病
        raise ProductionContractError(
            "执行输入/声明的供给组分严格身份失败(声明带病;fail-closed)",
            {"kind": "execution_input_identity_failed",
             "reason": str(exc)[:200]}) from exc
    if declared_keys != required_keys:
        raise ProductionContractError(
            "执行输入多重集 != 底物 ⊕ 声明供给(伴生供给执行契约;"
            "不得以其他分子冒充执行输入)",
            {"kind": "execution_input_multiset_mismatch",
             "declared_component_identities": declared_keys[:8],
             "required_component_identities": required_keys[:8]})
    return declared


def _record_equation_provenance(spec: dict) -> dict | None:
    """C 线声明链发射输入(s5b-analog-cosub-supply-1,2026-10-14;
    pred1 消费契约 = ppv1-criteria-v2 预注册 §二.1)。

    spec 携带 ``record_equation``(记录方程声明)与
    ``record_equation_ref``(provenance record_id)**成对**声明 ⇒
    返回 {record_id, payload};hypothesis.provenance_refs = [ref] 且
    事件提交前 ``ledger.store.put_provenance`` 落同行 —— 判分侧
    pred1 链(event → hypothesis.provenance_refs → payload.
    provenance_records 行 → 行 payload.record_equation)可解析。

    fail-closed:任一在位而不成对、形状非法(reactants/products 非
    非空 list、条目缺 smiles)、或任一条目 cn_identity 不可解析 ⇒
    结构化拒(不发射不可核声明 —— 判分侧对不可解析声明按 unknown
    fail-closed,发射侧同口径,不让声明链带病上线)。
    返回 None = 无声明(既有路径零变化,provenance_refs 保持 [])。
    """
    ref = spec.get("record_equation_ref")
    equation = spec.get("record_equation")
    if ref is None and equation is None:
        return None
    if not isinstance(ref, str) or not ref:
        raise ProductionContractError(
            "record_equation_ref 在位但非法(必须非空 str;声明链引用"
            "不得悬空)",
            {"kind": "record_equation_ref_invalid",
             "value_type": type(ref).__name__})
    if not isinstance(equation, dict):
        raise ProductionContractError(
            "record_equation_ref 在位而 record_equation 缺失/非 dict"
            "(声明成对契约;缺方程 = 声明链带病,拒)",
            {"kind": "record_equation_missing",
             "record_equation_ref": ref})
    normalized: dict[str, list] = {}
    for side in ("reactants", "products"):
        entries = equation.get(side)
        if not isinstance(entries, list) or not entries:
            raise ProductionContractError(
                f"record_equation.{side} 缺失/非 list/为空(消费契约"
                "要求两侧非空条目表;fail-closed)",
                {"kind": "record_equation_side_invalid",
                 "record_equation_ref": ref, "side": side})
        side_entries: list[dict] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ProductionContractError(
                    f"record_equation.{side}[{index}] 非 dict(条目契约:"
                    "{'smiles': str, 'role'?: str})",
                    {"kind": "record_equation_entry_invalid",
                     "record_equation_ref": ref, "side": side,
                     "index": index})
            smiles = str(entry.get("smiles") or "")
            if not smiles or cn_identity(smiles) is None:
                raise ProductionContractError(
                    f"record_equation.{side}[{index}] smiles 缺失或不可"
                    "解析(判分侧 cn_identity 逐条目消费;不可解析声明"
                    "= 全事件 unknown fail-closed,发射侧不发射带病条目)",
                    {"kind": "record_equation_entry_unparseable",
                     "record_equation_ref": ref, "side": side,
                     "index": index, "smiles": smiles[:200]})
            item: dict = {"smiles": smiles}
            role = entry.get("role")
            if role not in (None, ""):
                item["role"] = str(role)
            side_entries.append(item)
        normalized[side] = side_entries
    payload = {
        "schema_version": PPV1_PROVENANCE_SCHEMA_VERSION,
        "record_id": ref,
        "record_equation": normalized,
        "declaration_source": "analog_template_record",
        "record_key": str((spec.get("cosubstrate_event_contract")
                           or {}).get("record_key") or ""),
        "evidence_meaning": (
            "pred1 = 'the record declared it' (supply source = "
            "declaration source = template record; no self-endorsement)"),
    }
    return {"record_id": ref, "payload": payload}


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
      产物 1 + 共同产物逐条,系数按声明或 unknown);
    - **W-D2 共底物字段(s5b-corpus-retrieval-3 消费面;**W-D2-R1
      (S5B-D2-01 回修):激活条件 = 记录侧单一声明来源(contract 为
      dict 或 corpus 块声明 B/copy),装配数组非空与否不参与判定**;
      两处声明均无的 spec 路径行为零变化)**:
      * ``co_substrate_states``:[{smiles, state_ref, source_ref}]
        ——B 状态经同源 build_product_state 重建(严格身份内容
        寻址;声明 state_ref 与重建 ID 不一致 ⇒ 拒);声明在位时
        该数组缺失/null/非 list ⇒ 结构化拒(不静默归一成空列表,
        不降级成无共底物缺省装配);
      * ``declared_copy_components``:[{smiles, state_ref,
        component_source=record_declared_copy, record_key,
        provenance_sha256}] ——拷贝组分状态(与 coproduct 同轨的
        产物状态;component_source 非法 ⇒ 拒;数组形状契约同上);
      * ``cosubstrate_event_contract``:{record_key, co_substrates,
        record_products, copy_state_refs} ——NC-10 事件级端到端
        不变量的记录侧输入(本函数消费并断言:声明共底物(contract
        ∪ corpus 合并)⊆ 事件 reactant 侧 cosubstrate 参与物 ∧
        记录产物多重集 == 事件产物参与物多重集 ∧ 拷贝组分全部被
        引用 ∧ 拷贝不进执行期望 NC-9;任一不满足 ⇒ 零事件零提交;
        **W-D2-R2:记录产物在 contract 与 corpus 两处声明时,首次
        消费先按 strict 身份键多重集核同源一致性,分歧 ⇒ 结构化拒
        (cosubstrate_record_products_divergent),不以被收缩一侧作
        新全量;单来源(无第二声明处)合法路径按既有契约处理**);
      * participants 必须显式(共底物语义不进缺省装配——记录侧声明
        在位时省略 participants ⇒ 拒,不得默认装配 A→P)。
    返回 {hypothesis, states, product_states, tool_inputs,
    spec_digest, hypothesis_dict, cosubstrate_disclosure}。
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
    # ---- W-D2(S5b-corpus-retrieval-3 消费面):共底物参与物状态装配
    # + NC-10 事件级端到端不变量(mimo r32 R32-CS3-3;设计 §四.3)。
    # ---- W-D2-R1(S5B-D2-01 回修,2026-10-11;Codex D2 复审 §4/§8):
    # 触发条件改挂**记录侧单一声明来源**(_cosubstrate_record_
    # declaration:contract 为 dict 或 corpus 块声明 B/copy)——
    # 不由可删的装配数组是否非空决定。声明在 ⇒ 装配数组缺失/null/
    # 非 list 先结构化拒(不静默 or-[] 归一)、participants 必须显式
    # (缺省装配不覆盖共底物语义)、NC-10 断言无条件执行(旧条件
    # b_states/copy_states 双空即跳过,是四反例绕过根因)。B 与拷贝
    # 状态经同源 build_product_state 构建(严格身份内容寻址,与
    # recorded_source 装配期同 state_id);任一不满足 ⇒
    # ProductionContractError(零事件/零提交;spec 层 gate 通过不
    # 替代事件层核对)。适用入口(runflow decide 池条目/decide novel
    # 提案/expand 重放与公开 resume)全部经本单一构建源共用同一
    # 核验,不在各入口复制不同规则。合法旁观 B 的 copy=[](数组
    # 在位、类型合法)不拒。
    declaration = _cosubstrate_record_declaration(spec)
    if declaration is not None:
        contract = spec.get("cosubstrate_event_contract")
        if not isinstance(contract, dict) or not isinstance(
                contract.get("record_products"), list):
            raise ProductionContractError(
                "共底物 spec 缺 cosubstrate_event_contract(NC-10 事件"
                "级不变量需要记录侧声明;record_products 必填)",
                {"kind": "cosubstrate_contract_missing",
                 "declaration_sources": declaration["sources"]})
        participants_spec = spec.get("participants")
        if not isinstance(participants_spec, list) or not participants_spec:
            raise ProductionContractError(
                "共底物 spec 必须显式声明 participants(B 与拷贝组分"
                "装配契约;缺省装配不覆盖共底物语义)",
                {"kind": "cosubstrate_participants_required",
                 "declaration_sources": declaration["sources"]})
        for field in ("co_substrate_states",
                      "declared_copy_components"):
            value = spec.get(field)
            if not isinstance(value, list):
                raise ProductionContractError(
                    "共底物 spec 的装配数组缺失/null/非 list(记录侧"
                    "已声明 B/copy ⇒ 装配数组必须显式在位;静默归一成"
                    "空列表 = 删字段关闭 NC-10 的 S5B-D2-01 绕过形态,"
                    "不得降级成无共底物缺省装配)",
                    {"kind": "cosubstrate_assembly_missing",
                     "field": field,
                     "value_type": type(value).__name__,
                     "declaration_sources": declaration["sources"]})
    co_sub_entries = [dict(e) for e in
                      (spec.get("co_substrate_states") or [])]
    copy_entries = [dict(e) for e in
                    (spec.get("declared_copy_components") or [])]
    cosub_disclosure: dict | None = None
    b_states: dict = {}
    copy_states: dict = {}
    if declaration is not None:
        for e in co_sub_entries:
            state = build_product_state(
                str(e.get("smiles") or ""),
                source_refs=[{"record": str(
                    e.get("source_ref") or "corpus")}])
            declared_ref = str(e.get("state_ref") or state.state_id)
            if declared_ref != state.state_id:
                raise ProductionContractError(
                    "共底物状态引用与重建身份不一致(不得以其他分子"
                    "冒充该状态)",
                    {"kind": "cosubstrate_state_ref_mismatch",
                     "declared_state_ref": declared_ref,
                     "rebuilt_state_id": state.state_id})
            b_states[state.state_id] = state
        for e in copy_entries:
            if str(e.get("component_source")) != "record_declared_copy":
                raise ProductionContractError(
                    "拷贝组分 component_source 非法(只认 record_"
                    "declared_copy;R32-CS1-1 机读标签)",
                    {"kind": "cosubstrate_copy_source_invalid",
                     "component_source": str(e.get("component_source"))})
            state = build_product_state(
                str(e.get("smiles") or ""),
                source_refs=[{
                    "record": str(e.get("record_key") or "corpus"),
                    "component_source": "record_declared_copy"}])
            declared_ref = str(e.get("state_ref") or state.state_id)
            if declared_ref != state.state_id:
                raise ProductionContractError(
                    "拷贝组分状态引用与重建身份不一致",
                    {"kind": "cosubstrate_state_ref_mismatch",
                     "declared_state_ref": declared_ref,
                     "rebuilt_state_id": state.state_id})
            copy_states[state.state_id] = state
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
    # ---- C 线声明链发射输入(s5b-analog-cosub-supply-1;pred1 消费
    # 契约 criteria-v2 预注册 §二.1):spec 携带 record_equation/
    # record_equation_ref 成对声明 ⇒ provenance_refs 进假设身份,
    # 发射载荷随 prepared 交给提交段(put_provenance 先于事件提交)。
    # 无声明 spec ⇒ provenance_refs 保持 [](假设身份/载荷零变化)。
    record_equation_provenance = _record_equation_provenance(spec)
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
        provenance_refs=(
            [record_equation_provenance["record_id"]]
            if record_equation_provenance is not None else None),
        origin_group_key=str(spec.get("origin_group_key") or ""))
    states = {substrate_state.state_id: substrate_state,
              product_state.state_id: product_state}
    for state in coproduct_states:
        states[state.state_id] = state
    product_states_out = [product_state] + coproduct_states
    if declaration is not None:
        # ---- C 线(s5b-analog-cosub-supply-1)执行输入首消费核验:
        # 伴生供给参与执行 —— edits 对底物+供给编译,运行期执行/审计
        # 必须渲染同一输入。spec 声明 execution_input_smiles 时,其
        # 组分严格身份多重集必须 == 底物 ⊕ 声明供给(精确多重集,
        # 防以其他分子冒充执行输入);声明在而核验不过 ⇒ 结构化拒
        #(零事件/零提交)。核验通过 ⇒ 执行输入随 tool_inputs 下传
        #(expand 段按声明渲染;无声明路径零变化)。----
        execution_input = _verify_execution_input(
            spec, substrate_state=substrate_state,
            co_sub_entries=co_sub_entries)
    else:
        execution_input = None
    if declaration is not None:
        # ---- 状态映射扩(B 与拷贝组分;设计 §四.3:拷贝产物 state
        # 与 coproduct 同轨——0e.5 followup 消费链照池宽纪律)。
        # W-D2-R1:本块改由记录侧声明触发(旧条件 b_states or
        # copy_states 在两侧同删时静默跳过 NC-10,即 S5B-D2-01)。
        # ----
        states.update(b_states)
        states.update(copy_states)
        product_states_out.extend(
            copy_states[k] for k in sorted(copy_states))
        cosub_disclosure = _check_cosubstrate_event_invariant(
            spec, participants=participants, states=states,
            b_states=b_states, copy_states=copy_states,
            declaration=declaration)
    tool_inputs = {
        "edits": list(spec["edits"]),
        "donor": dict(spec["donor"]),
        "alignment": dict(spec["alignment"]),
        "expectation": dict(spec["expectation"]),
    }
    if execution_input is not None:
        tool_inputs["execution_input_smiles"] = execution_input
    return {
        "hypothesis": hypothesis,
        "states": states,
        "product_states": product_states_out,
        "dependencies": dependencies,
        "tool_inputs": tool_inputs,
        "spec_digest": content_hash(spec),
        "hypothesis_dict": hypothesis.to_dict(),
        "cosubstrate_disclosure": cosub_disclosure,
        # C 线(s5b-analog-cosub-supply-1):记录方程发射载荷(提交段
        # put_provenance 消费;None = 无声明,既有路径零变化)
        "record_equation_provenance": record_equation_provenance,
    }


def _cosubstrate_record_declaration(spec: dict) -> dict | None:
    """记录侧单一声明来源(W-D2-R1/S5B-D2-01 回修,2026-10-11;Codex
    D2 复审 §4/§8)——NC-10 触发条件的唯一判定函数。

    共底物语义适用性 = spec 携带**记录侧声明**:
    ``cosubstrate_event_contract`` 为 dict,或 ``corpus`` 块声明
    B/copy(co_substrates 非空或**record_products 键在位**——只有 D2
    component 分支装配的 corpus 块携带这些字段;whole/EAWAG spec 两处
    均无声明)。**装配数组(co_substrate_states/declared_copy_
    components)是否非空不参与判定**——同一记录把 B 与拷贝两侧同时
    删/置空/置 null/省略后,旧触发条件静默关闭守卫、缺省装配退化回
    A→P,即复审四反例(strip_both_empty/missing/null、all_arrays_
    missing_participants_default)的绕过形态。

    W-D2-R3(S5B-D2-01 最后残余;Codex D2-R2 复审 §4.2/§4.3/§8):
    corpus 侧产物声明的存在性 = **键在位**,不是"是 list 且非空"
    ——键在位而值为空 list(有效声明,按多重集比较)或 null/非
    list 坏形状(进守卫后由轴 0 首次消费结构化拒披露)都构成记录
    侧声明,不得把类型错误解释成"corpus 未声明"而静默回落 plain
    A→P 缺省装配(同根规则的声明入口;守卫主体在
    _check_cosubstrate_event_invariant 轴 0)。键不在位 = 字段确未
    声明 ⇒ 该侧不声明。

    返回 None = 两处记录侧声明均不在 ⇒ 非 D2 共底物 spec(其余 spec
    路径行为零变化);返回 dict = {declared_b_smiles(contract ∪
    corpus 合并去重保序), sources, contract_declared_b,
    corpus_declared_b}——合并集喂 NC-10 轴 1(声明共底物 ⊆ 事件
    reactant 侧 cosubstrate 参与物):contract 单侧被清空而 corpus
    仍声明 B 时,守卫不得失效(声明来源两处任一在位即约束)。
    """
    contract = spec.get("cosubstrate_event_contract")
    corpus = spec.get("corpus")
    contract_present = isinstance(contract, dict)
    corpus_b: list[str] = []
    corpus_declared = False
    if isinstance(corpus, dict):
        corpus_b = [str(e.get("smiles")) for e in
                    (corpus.get("co_substrates") or [])
                    if isinstance(e, dict) and e.get("smiles")]
        # W-D2-R3:键在位即声明(空 list/坏形状不当缺省;坏形状由
        # 守卫轴 0 首次消费结构化拒披露,不在此处清洗或解释)。
        corpus_declared = bool(corpus_b) or (
            "record_products" in corpus)
    if not contract_present and not corpus_declared:
        return None
    contract_b: list[str] = []
    if contract_present:
        contract_b = [str(e.get("smiles")) for e in
                      (contract.get("co_substrates") or [])
                      if isinstance(e, dict) and e.get("smiles")]
    sources = (["cosubstrate_event_contract"] if contract_present else []
               ) + (["corpus"] if corpus_declared else [])
    return {
        "declared_b_smiles": list(
            dict.fromkeys(contract_b + corpus_b)),
        "sources": sources,
        "contract_declared_b": contract_b,
        "corpus_declared_b": corpus_b,
    }


def _record_products_multiset_keys(products: list) -> list:
    """记录产物声明多重集键(W-D2-R2,S5B-D2-01 产物侧残余;Codex
    D2-R1 复审 §4.2/§4.3)。

    每个组分取**既有 strict_identity_of 严格身份键**(与 state_id/
    NC-10 其余轴同一事实源——合法同义表示按 strict 键规范,不另开
    化学比较器);不可解析条目以原始串为键保守参与比对(等值只在
    两侧同为该不可解析串时成立;解析面失败仍由轴 2 的 any-None
    拒绝承接,本函数不新增解析判据)。返回排序键列表——**重复组分
    保留**(多重集语义),不用集合并集隐藏分歧。"""
    keys: list = []
    for p in products:
        raw = str(p)
        try:
            keys.append(strict_identity_of(raw))
        except Exception:
            keys.append("unparseable:" + raw)
    return sorted(keys)


def _check_cosubstrate_event_invariant(
        spec: dict, *, participants: list, states: dict,
        b_states: dict, copy_states: dict,
        declaration: dict) -> dict:
    """NC-10 事件级端到端不变量(mimo r32 R32-CS3-3 必加;事件提交
    前断言,任一不满足 ⇒ ProductionContractError ⇒ 零事件/零提交):

    0. **同源权威消费(W-D2-R2,S5B-D2-01 产物侧残余;Codex D2-R1
       复审 §4.2/§4.3;W-D2-R3 补存在性/格式消费,Codex D2-R2 复审
       §4.2/§4.3/§8)**:适用记录在多处声明同一产物
       (contract.record_products 与 corpus.record_products——
       recorded_source 装配期同一列表生成)时,首次消费先按既有
       strict_identity_of 键空间以**多重集**核对两处声明一致性
       (重复组分保留意义,不用集合并集隐藏分歧;合法同义表示按
       strict 键规范);双来源在位而分歧 ⇒ 首次消费结构化拒
       (kind=cosubstrate_record_products_divergent)——不得选被改
       的一侧作为新全量,不重算新身份洗掉坏声明;坏输入保全
       (detail 披露两侧多重集)。**第二产物声明的存在性 = 键在位**
       (W-D2-R3):corpus.record_products 键在位而值为 null/string/
       dict/bool 等非 list ⇒ 坏声明,首次消费结构化拒(kind=
       cosubstrate_corpus_record_products_corrupt,detail 披露字段/
       类型/原因并保全原始坏值),不得以 isinstance(list) 为是否
       存在的判定把类型错误解释成"没有第二来源"静默降级成合法单
       来源;键不在位(字段确未声明)⇒ 单来源 = contract 侧,合法
       默认路径按既有契约处理,不全面拒绝;空 list 是有效声明按
       既有多重集比较,不当缺省。无第二来源的合法默认路径不全面
       拒绝;不另开化学比较器,不重扫语料,不要求抵抗全库协同
       改写(两侧同被改后无历史证据可判别的形态不在本契约内);
    1. 记录声明的全部共底物严格身份 ⊆ 事件 reactant 侧 cosubstrate
       state_refs 的状态严格身份(spec 层 gate 通过不替代事件层核对
       —— B 与拷贝同丢会退化回 A→P 可 exact 的 R2-2 禁形态,且
       add_atom 负控对零产物贡献 B 空转,此不变量是唯一事件层闸;
       W-D2-R1:声明共底物集 = contract ∪ corpus 记录侧单一声明来源
       合并(_cosubstrate_record_declaration),contract 单侧清空
       不关闭本轴);
    2. 记录产物多重集 == 事件产物参与物多重集(执行组分 ∪ 声明拷贝
       组分;**W-D2-R2:记录产物权威在轴 0 同源核验后消费**);
    3. 全部参与物 state_ref 可解析(装配不得静默丢参与物);
    4. 拷贝组分全部被产物侧参与物引用且 component_source 机读标签
       在位(R32-CS1-1:身份轴 = 记录声明可核,生成轴 = 未执行,
       两轴不得合并成"已生成/已核实");
    5. NC-9:拷贝组分不得出现在 expectation.target_smiles 的组分集
       (拷贝不进执行期望;edits/alignment 通道由编译器结构性排除
       + NC-3 断言)。

    返回机读披露字典(随生产报告 artifact 落盘):declared_copy_
    components + expectation_covered_state_refs + coproduct_
    participants 字段说明(R32-CS1-1/CS5-2:"按 role 聚合,不表示
    执行覆盖")。W-D2-R2 披露新增:record_products_sources(轴 0
    实际消费/核验的声明来源)、consumer_discipline(消费者联读
    生产报告义务与禁句,Codex D2-R1 复审 §5 P2-1)、bystander_
    cosubstrates(旁观型 B 的 unknown 机读注记,P2-2)。
    """
    contract = spec.get("cosubstrate_event_contract") or {}
    # ---- (0) 同源权威消费(W-D2-R2;记录产物多处声明的首次消费)----
    # contract.record_products 在 prepare 的 contract-missing 检查后
    # 必为 list;corpus 侧 record_products 的存在性 = **键在位**
    # (W-D2-R3,S5B-D2-01 最后残余;Codex D2-R2 复审 §4.2/§4.3/§8):
    # whole/EAWAG spec 的 corpus 块不带该键 ⇒ 字段确未声明的单来源
    # 合法默认路径;键在位而值非 list ⇒ 坏声明首消费结构化拒,不以
    # isinstance(list) 为存在判定静默降级成单来源。
    contract_products = contract.get("record_products")
    corpus_block = spec.get("corpus")
    corpus_products_key_present = (
        isinstance(corpus_block, dict)
        and "record_products" in corpus_block)
    corpus_products = (corpus_block.get("record_products")
                       if corpus_products_key_present else None)
    record_products_sources = ["cosubstrate_event_contract"]
    if corpus_products_key_present and \
            not isinstance(corpus_products, list):
        # 坏声明保全(不清洗不重算):detail 披露字段/类型/原因与
        # 原始值(JSON 安全化;不可序列化时截断 repr 兜底)。
        try:
            preserved_declaration = json.loads(
                json.dumps(corpus_products))
        except (TypeError, ValueError):
            preserved_declaration = repr(corpus_products)[:200]
        raise ProductionContractError(
            "NC-10 记录产物第二声明处在位损坏:corpus.record_products"
            " 键在位而值非 list(字段明确在位而损坏;不得把类型错误"
            "解释成'没有第二来源'降级成合法单来源;坏声明保全,不"
            "清洗不重算新身份)",
            {"kind": "cosubstrate_corpus_record_products_corrupt",
             "axis": "record_products_multiset_same_source",
             "field": "corpus.record_products",
             "declared_value_type": type(corpus_products).__name__,
             "reason": "second_declaration_present_but_not_list",
             "corpus_record_products_raw": preserved_declaration,
             "declaration_sources": ["cosubstrate_event_contract",
                                     "corpus"]})
    if isinstance(contract_products, list) and \
            isinstance(corpus_products, list):
        contract_keys = _record_products_multiset_keys(contract_products)
        corpus_keys = _record_products_multiset_keys(corpus_products)
        if contract_keys != corpus_keys:
            raise ProductionContractError(
                "NC-10 记录产物声明同源分歧:contract 与 corpus 两处"
                "声明同一记录的产物,首次消费按 strict 身份多重集核对"
                "不一致(不得以被收缩的一侧作新全量;坏声明保全,不"
                "重算新身份洗掉;同根覆盖 contract 单侧收缩与 corpus "
                "单侧收缩)",
                {"kind": "cosubstrate_record_products_divergent",
                 "axis": "record_products_multiset_same_source",
                 "declaration_sources": ["cosubstrate_event_contract",
                                         "corpus"],
                 "contract_product_identities": contract_keys[:8],
                 "corpus_product_identities": corpus_keys[:8]})
        record_products_sources = ["cosubstrate_event_contract",
                                   "corpus"]
    record_products = [str(p) for p in (contract_products or [])]
    # ---- (3) 参与物状态可解析 ----
    unresolved = sorted({str(p.state_ref) for p in participants
                         if p.state_ref not in states})
    if unresolved:
        raise ProductionContractError(
            "共底物事件参与物引用了未装配的状态(装配不得静默丢"
            "参与物;NC-10 前置)",
            {"kind": "cosubstrate_participant_state_unresolved",
             "unresolved_state_refs": unresolved[:8]})
    # ---- (1) 声明共底物 ⊆ reactant 侧 cosubstrate 参与物 ----
    # W-D2-R1:声明集 = 记录侧单一声明来源合并(contract ∪ corpus;
    # _cosubstrate_record_declaration 已去重保序)——contract 单侧
    # 被清空而 corpus 仍声明 B 时,本轴不得失效。
    reactant_cosub_ids = {
        states[p.state_ref].smiles_isomeric for p in participants
        if p.side == "reactant" and p.role == "cosubstrate"}
    declared_b = set()
    for smiles in declaration["declared_b_smiles"]:
        try:
            ident = strict_identity_of(str(smiles))
        except Exception as exc:
            raise ProductionContractError(
                "记录侧共底物声明不可解析(NC-10 契约输入失败)",
                {"kind": "cosubstrate_contract_unparseable",
                 "smiles": str(smiles)[:200],
                 "reason": str(exc)[:200]}) from exc
        if ident is not None:
            declared_b.add(ident)
    missing_b = sorted(declared_b - reactant_cosub_ids)
    if missing_b:
        raise ProductionContractError(
            "NC-10 事件级不变量违反:记录声明的共底物未全部进入事件"
            " reactant 侧 cosubstrate 参与物(记录保真违例;B 与拷贝"
            " 同丢会退化回可 exact 的假单步形态)",
            {"kind": "cosubstrate_event_invariant_violation",
             "axis": "declared_cosubstrates_subset",
             "missing_strict_identities": missing_b[:8],
             "event_reactant_cosubstrate_identities":
                 sorted(reactant_cosub_ids)[:8]})
    # ---- (2) 记录产物多重集 == 事件产物参与物多重集 ----
    product_ids = sorted(
        states[p.state_ref].smiles_isomeric for p in participants
        if p.side == "product")
    recorded_ids: list = []
    for p in record_products:
        try:
            recorded_ids.append(strict_identity_of(p))
        except Exception:
            recorded_ids.append(None)
    recorded_sorted = sorted(x for x in recorded_ids if x is not None)
    if any(x is None for x in recorded_ids) or \
            product_ids != recorded_sorted:
        raise ProductionContractError(
            "NC-10 事件级不变量违反:事件产物参与物多重集 != 记录产物"
            "多重集(执行组分 ∪ 声明拷贝组分必须等于记录全量)",
            {"kind": "cosubstrate_event_invariant_violation",
             "axis": "record_products_multiset",
             "event_product_identities": product_ids[:8],
             "recorded_product_identities": recorded_sorted[:8]})
    # ---- (4) 拷贝组分被产物侧引用 + 机读标签在位 ----
    product_refs = {str(p.state_ref) for p in participants
                    if p.side == "product"}
    untracked_copies = sorted(set(copy_states) - product_refs)
    if untracked_copies:
        raise ProductionContractError(
            "NC-10 事件级不变量违反:拷贝组分未被事件产物侧参与物"
            "引用(拷贝组分是声明参与物,不得静默丢弃)",
            {"kind": "cosubstrate_event_invariant_violation",
             "axis": "declared_copy_components_tracked",
             "untracked_copy_state_refs": untracked_copies[:8]})
    # ---- (5) NC-9:拷贝不得进执行期望 ----
    target = str((spec.get("expectation") or {}).get("target_smiles")
                 or "")
    from rdkit import Chem as _Chem
    target_mol = _Chem.MolFromSmiles(target) if target else None
    target_ids: set = set()
    if target_mol is not None:
        for frag in _Chem.GetMolFrags(target_mol, asMols=True,
                                      sanitizeFrags=True):
            try:
                target_ids.add(strict_identity_of(
                    _Chem.MolToSmiles(frag)))
            except Exception:
                pass
    copy_ids = {s.smiles_isomeric for s in copy_states.values()}
    leaked = sorted(copy_ids & target_ids)
    if leaked:
        raise ProductionContractError(
            "NC-9 违例:拷贝组分出现在 expectation.target_smiles 执行"
            "期望内(拷贝组分不经执行通道;设计 §四.3.4 禁止事项)",
            {"kind": "cosubstrate_copy_in_expectation",
             "leaked_strict_identities": leaked[:8]})
    # ---- 机读披露(R32-CS1-1/CS5-2;进数据不进文档) ----
    expectation_covered = [
        p.state_ref for p in participants
        if p.side == "product" and p.state_ref not in copy_states]
    # P2-2(Codex D2-R1 复审 §5;W-D2-R2 落字):旁观型 B 机读注记——
    # 声明 B 无同身份产物侧对应不等于已消耗/催化作用已证;系数与
    # 消耗方向保持 unknown(不新开字段协议,披露层注记)。
    product_id_set = set(product_ids)
    bystander_cosubstrates = [
        {"state_ref": str(ref), "smiles": str(state.smiles_isomeric),
         "consumption_status": "unknown",
         "note": ("declared co-substrate with no identity-preserving "
                  "product-side counterpart in this event; the record "
                  "declaration does NOT prove consumption or a "
                  "catalytic role; consumption/catalysis and "
                  "coefficient stay unknown; any B-derived declared "
                  "copy component carries its own "
                  "declared_not_executed status")}
        for ref, state in sorted(b_states.items())
        if state.smiles_isomeric not in product_id_set]
    return {
        "declared_copy_components": [
            {"state_ref": str(e.get("state_ref")),
             "smiles": str(e.get("smiles")),
             "component_source": "record_declared_copy",
             "record_key": str(e.get("record_key")),
             "provenance_sha256": str(e.get("provenance_sha256")),
             "execution_status": "declared_not_executed",
             "center_status": "unknown"}
            for e in (spec.get("declared_copy_components") or [])],
        "co_substrate_state_refs": sorted(b_states),
        "declaration_sources": list(declaration["sources"]),
        "record_products_sources": list(record_products_sources),
        "trigger_semantics": (
            "W-D2-R1 (S5B-D2-01): NC-10 applicability is decided by the "
            "record-side single declaration source (cosubstrate_event_"
            "contract dict OR corpus block declaring B/copy; the corpus "
            "record_products KEY being in place is a declaration, "
            "W-D2-R3 — an empty list is a valid declaration and a "
            "non-list value is a corrupt declaration that gets a "
            "first-consumption structured reject, neither is treated "
            "as undeclared); assembly "
            "arrays being missing/null/empty cannot disable the guard "
            "and participants omission cannot default to plain A->P "
            "assembly"),
        "expectation_covered_state_refs": expectation_covered,
        "consumer_discipline": (
            "downstream consumer obligations (W-D2-R2, Codex D2-R1 "
            "review section 5 P2-1): role=coproduct does NOT indicate "
            "executed generation; execution coverage MUST be read "
            "jointly with the same-batch production report "
            "(expectation_covered_state_refs + per-component "
            "execution_status), never from role alone; "
            "identity-consistent-with-record, formation-not-executed "
            "and stoichiometry-unknown are separate columns and must "
            "not be merged; banned claims: 'all atoms have sources' "
            "and 'copy generated/verified' must NOT be asserted from "
            "this disclosure"),
        "bystander_cosubstrates": bystander_cosubstrates,
        "coproduct_participants_field_note": (
            "coproduct_participants aggregates by role and does NOT "
            "indicate execution coverage; declared-copy components "
            "are declared_not_executed with center=unknown (identity "
            "axis = record-declared and verifiable; formation axis = "
            "not executed; the two axes must not be merged into "
            "'generated/verified')"),
        "invariant": "checked(NC-10: declared cosubstrates subset-of "
                     "event reactant cosubstate refs AND record "
                     "product multiset == event product participant "
                     "multiset; declared-B set = contract UNION corpus "
                     "record-side declaration, W-D2-R1; record product "
                     "authority = same-source multiset verification "
                     "across the declarations ACTUALLY consumed "
                     "(record_products_sources above; contract AND "
                     "corpus when both are in-place lists, W-D2-R2) "
                     "before the axis-2 comparison; an in-place second "
                     "declaration whose value is not a list is a "
                     "first-consumption structured reject "
                     "(cosubstrate_corpus_record_products_corrupt) and "
                     "never reaches this checked disclosure, W-D2-R3; "
                     "a corpus block whose record_products key is "
                     "absent is a legitimate single-source path, not "
                     "a verified second source)",
        "stoichiometry_status": (
            "unknown(coefficients all unknown;participant_list_status"
            "=declared_complete describes list completeness only, "
            "NOT stoichiometric/balance completeness — R32-CS1-3)"),
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
        # W-D2(R32-CS1-1/CS5-2):共底物披露随事件输出(机器可核对的
        # 执行覆盖面 + 拷贝组分声明;无共底物 spec ⇒ 零字段零变化)
        if prepared.get("cosubstrate_disclosure") is not None:
            payload["cosubstrate_disclosure"] = prepared[
                "cosubstrate_disclosure"]
        if ledger.artifact_store is not None and task_key:
            ledger.artifact_store.write(
                task_key, "production_report", payload)
        return payload

    # ---- C 线(s5b-analog-cosub-supply-1):执行输入 = prepare 段
    # 首消费核验过的声明(伴生供给:edits 对底物+供给编译,渲染同一
    # 输入;无声明 ⇒ 裸底物,既有行为逐字节不变)----
    execution_input_smiles = str(
        tool_inputs.get("execution_input_smiles")
        or substrate_state.smiles_isomeric)
    execution = execute_atomtool_expansion(
        substrate_smiles=execution_input_smiles,
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
    # ---- C 线声明链发射(run 期,worker 事件提交路径;
    # s5b-analog-cosub-supply-1;pred1 消费契约 = criteria-v2 预注册
    # §二.1):prepared 携带记录方程发射载荷时,事件提交前先把来源记
    # 录方程落 provenance_records(公共 store writer 幂等;声明内容 =
    # 候选装配时的模板记录方程,同一数据源不另造)。行先于事件存在
    # ⇒ 提交后声明链 event → hypothesis.provenance_refs → provenance
    # _records 行(record_id 匹配)→ record_equation 可解析;无声明
    # 路径零调用(既有行为逐字节不变)。deferred/rejected 不发射
    #(声明链只对提交事件可消费)。
    record_equation_provenance = prepared.get(
        "record_equation_provenance")
    if record_equation_provenance is not None:
        ledger.store.put_provenance(
            str(record_equation_provenance["record_id"]),
            ledger.run_id or "",
            dict(record_equation_provenance["payload"]))
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
