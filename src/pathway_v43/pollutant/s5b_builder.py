"""S5b 题卷构建器 —— questions.jsonl → PPV1 run 输入 + 参考图/清单
(预注册 §2/§3 转换规则落地;契约登记 s5b-builder-1)。

职责与边界:

- 输入 = 题卷 questions.jsonl(每行 qid/substrate_smiles/products_smiles
  [金标]/...;运行时在 Chenyu 给真实路径,测试用合成夹具);
- 输出根**必须落在 gitignored 目录**(仓内只允许 ``reports/ppv1_s5b/``
  之下的路径;仓外路径合法;仓内其它路径 fail-closed 拒)——金标承载物
  (参考图 JSON、run 输入的题面+池)只进 gitignored,仓内代码/文档零
  金标取值;
- 每题产出一个 G1 参考图(一题一图,预注册 §2):root qid 进
  source_refs(evaluation-4 图侧一致性核)、参考边 = 底物→全部金标
  产物节点、全 principal(§3.2)、participant_list_status=partial +
  固定披露(§3.3)、step_scope=net_reaction 无守恒声明(§3.1)、
  node/edge status=reference_only(§3.4)、condition_requirements 空 +
  scenario_scope=rhea_generic_enzymology_no_scenario(§3.6)、
  known_gaps 固定清单仅披露不豁免(§4)、S1 一题一组(§7;跨题重复
  底物标 related,其余 unknown,永不 independent);
- 每题产出一条 PPV1 run 输入(根底物=substrate、无人工条件注入、
  模型 provider_kind=real;池 = 注入的 pool_provider 的确定性检索结果,
  **底物侧检索,零金标消费**);
- 冻结注册序 = questions.jsonl 行序(codex 复审 §5:构建器清单序是首
  注册锚,不得目录遍历偶然序/内容择优;重复 qid fail-closed 拒);
- 判分零 LLM;金标只在封存答卷后的判分进程(s5b_scoring)进入。

本模块不做真实模型调用、不写仓内文件(除调用方给定的 gitignored
输出根);合成测试夹具的 qid/分子与真实 298 集合零重叠由测试纪律
保证(本模块对 qid 前缀不做真实集校验,如实披露)。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import V43Config
from ..domain.models import stable_id
from .chemstate import build_chemical_state
from .profile import (
    PPV1_REFERENCE_GRAPH_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from .reference_graph import (
    reference_graph_sha256,
    validate_reference_graph,
)

S5B_BUILDER_VERSION = "s5b-builder-1"

# 仓内唯一允许的输出根(gitignored;.gitignore 由本批同步登记)
S5B_GITIGNORED_REPO_ROOT = "reports/ppv1_s5b"

# 固定披露(预注册 §3/§4;known_gaps 仅披露,不豁免分母)
S5B_KNOWN_GAPS = (
    "cofactors_cosubstrates_stripped_per_extraction_rules_2026_09_22",
    "no_per_question_conditions_metadata",
    "principal_vs_coproduct_undistinguished",
    "identity_underestimation_charge_difference_cn_only",
    "identity_underestimation_stereo_difference_cn_only",
    "identity_underestimation_tautomer_no_match",
    "no_balanced_coefficients_no_conservation_claim",
)
S5B_SCENARIO_SCOPE = "rhea_generic_enzymology_no_scenario"
S5B_SPLIT_RULE_VERSION = "ppv1-s5b-split-1"

# 参与物覆盖披露句(预注册 §3.3 固定披露句)
S5B_PARTICIPANT_DISCLOSURE = (
    "参与物 = 提取后的含碳组分;辅因子/共底物(NAD(P)±/H、ATP、GSH、"
    "水、金属离子、>80 字符大分子辅因子)按 2026-09-22 提取规则未列"
    "(反应物侧共剥 473 项);本参考边无配平系数(coefficient_status="
    "unknown),不作元素/电荷/电子供体计量声明,不构成守恒已核;"
    "本卷金标无角色标注,全列主产物是口径选择,不是化学认定;小分子"
    "共产物不豁免召回;相同结构的共同产物按结构集合匹配,份数不在"
    "判分面")


class S5bBuilderError(RuntimeError):
    """构建器契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 输出根守卫


def check_output_root(output_root: str | Path, *,
                      repo_root: str | Path | None = None) -> Path:
    """金标承载物的输出根守卫:仓内只许 gitignored 授权根。

    - 仓外路径:合法(Chenyu 部署批次根本在仓外);
    - 仓内路径:必须位于 ``reports/ppv1_s5b/`` 之下(该根已进
      .gitignore;其它仓内路径 ⇒ 结构化拒,零写入)。
    """
    root = Path(output_root).resolve()
    if repo_root is None:
        from ..config import repo_root as _repo_root

        repo_root = _repo_root()
    repo = Path(repo_root).resolve()
    try:
        rel = root.relative_to(repo)
    except ValueError:
        return root  # 仓外:合法
    rel_posix = rel.as_posix()
    if rel_posix == S5B_GITIGNORED_REPO_ROOT or rel_posix.startswith(
            S5B_GITIGNORED_REPO_ROOT + "/"):
        return root
    raise S5bBuilderError(
        f"金标承载物输出根不合法:{root}(仓内路径只允许 "
        f"{S5B_GITIGNORED_REPO_ROOT}/ 之下的 gitignored 根;零写入)",
        {"kind": "s5b_output_root_unauthorized",
         "output_root": str(root), "repo_relative": rel_posix,
         "authorized_repo_root": S5B_GITIGNORED_REPO_ROOT})


# ---------------------------------------------------------------- 题卷读取


def load_questions(questions_path: str | Path) -> list[dict]:
    """读题卷(逐行 JSON;qid 唯一性核验;冻结注册序 = 行序)。

    返回逐行 dict(含金标 products_smiles——只允许流入 gitignored
    输出根,见 check_output_root)。缺 qid/substrate/products 字段 ⇒
    结构化拒(不静默跳行)。
    """
    path = Path(questions_path)
    if not path.is_file():
        raise S5bBuilderError(
            f"题卷文件不存在:{path}", {"kind": "s5b_questions_missing",
                                    "path": str(path)})
    questions: list[dict] = []
    seen_qids: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except ValueError as exc:
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行不可解析为 JSON:{exc}",
                    {"kind": "s5b_questions_unparseable", "line": line_no,
                     "path": str(path)}) from exc
            if not isinstance(record, dict):
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行不是 JSON 对象",
                    {"kind": "s5b_questions_not_object", "line": line_no})
            qid = str(record.get("qid") or "")
            substrate = str(record.get("substrate_smiles") or "")
            products = record.get("products_smiles")
            if not qid or not substrate or not isinstance(products, list):
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行缺 qid/substrate_smiles/"
                    "products_smiles(缺字段明确失败,不静默跳行)",
                    {"kind": "s5b_questions_field_missing",
                     "line": line_no, "qid": qid})
            if qid in seen_qids:
                raise S5bBuilderError(
                    f"题卷 qid 重复:{qid}(qid 是样本↔导出配对键,重复即"
                    "歧义;fail-closed)", {
                        "kind": "s5b_questions_duplicate_qid", "qid": qid})
            seen_qids.add(qid)
            questions.append(record)
    if not questions:
        raise S5bBuilderError(
            "题卷为空(零题;fail-closed)", {
                "kind": "s5b_questions_empty", "path": str(path)})
    return questions


# ---------------------------------------------------------------- 参考图


def build_reference_graph(question: dict, *, repeated_substrate: bool,
                          domain: str = "298") -> dict:
    """一题一图(G1;预注册 §2/§3 全规则;金标产物进 nodes/to 参与物)。

    - root_entity:strict_structure_identity 由 PPV1 严格身份机制对
      substrate 现算(298 底物全显式 SMILES,不走 cn_only 分支);
    - 参考边 = 根 → 全部金标产物(一题一条边;共同产物不被报告 K 删);
    - 全部金标产物 role=principal_product(§3.2 口径,非化学认定);
    - source group S1 一题一组;重复底物 related,其余 unknown,永不
      independent(§7);
    - creation_review=pending_user_teacher_review(真实数据待评审;
      合成夹具由调用方如实改标 synthetic_rule_level)。
    """
    qid = str(question["qid"])
    substrate = str(question["substrate_smiles"])
    products = [str(p) for p in question["products_smiles"]]
    if not products:
        raise S5bBuilderError(
            f"题 {qid} 金标产物为空(空产物不合法;fail-closed)",
            {"kind": "s5b_empty_products", "qid": qid})
    try:
        state = build_chemical_state(substrate, "raw_input",
                                     [{"record": f"s5b-question:{qid}"}])
    except Exception as exc:  # noqa: BLE001 —— 结构化包装
        raise S5bBuilderError(
            f"题 {qid} 底物不可解析(严格身份现算失败):{exc}",
            {"kind": "s5b_substrate_unparseable", "qid": qid}) from exc
    graph_id = s5b_graph_id(qid)
    prov_id = f"prov-{qid}"
    group_id = f"sg-{qid}"
    root_node_id = f"n-{qid}-root"
    product_node_ids = [f"n-{qid}-p{i + 1}"
                        for i in range(len(products))]
    nodes = [
        {
            "node_id": root_node_id,
            "state_identity": f"strict:{state.smiles_isomeric}",
            "structure_smiles": substrate,
            "structure_identity_scope": "strict_structure",
            "role": "root",
            "occurrence_id": f"occ-{qid}-root",
            "source_group_refs": [group_id],
            "condition_scope": [],
            "provenance_refs": [prov_id],
            "node_status": "reference_only",
        },
    ]
    for i, product in enumerate(products):
        nodes.append({
            "node_id": product_node_ids[i],
            "state_identity": f"strict-ref:{product}",
            "structure_smiles": product,
            "structure_identity_scope": "strict_structure",
            "role": "principal_product",
            "occurrence_id": f"occ-{qid}-p{i + 1}",
            "source_group_refs": [group_id],
            "condition_scope": [],
            "provenance_refs": [prov_id],
            "node_status": "reference_only",
        })
    participants = [
        {"node_id": root_node_id, "side": "reactant", "role": "substrate",
         "coefficient": None, "coefficient_status": "unknown"},
    ]
    for node_id in product_node_ids:
        participants.append({
            "node_id": node_id, "side": "product",
            "role": "principal_product", "coefficient": None,
            "coefficient_status": "unknown",
        })
    graph = {
        "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
        "reference_graph_id": graph_id,
        "domain": domain,
        "track": "known_evidence_reconstruction",
        "root_entity": {
            "entity_id": f"root-{qid}",
            "structure_smiles_raw": substrate,
            "strict_structure_identity": state.smiles_isomeric,
            "formal_charge": state.formal_charge,
            "stereo_information_status": state.stereo_information_status,
            "isotope_information_status": state.isotope_information_status,
            "source_refs": [qid],
        },
        "nodes": nodes,
        "edges": [
            {
                "edge_id": f"e-{qid}",
                "from_node_ids": [root_node_id],
                "to_node_ids": list(product_node_ids),
                "transformation_ref": qid,
                "transformation_signature_status":
                    "unsigned_directional_record",
                "participants": participants,
                "participant_list_status": "partial",
                "coefficient_status": "unknown",
                "step_scope": "net_reaction",
                "condition_requirements": [],
                "scenario_scope": S5B_SCENARIO_SCOPE,
                "provenance_refs": [prov_id],
                "source_group_refs": [group_id],
                "evidence_basis": "database_recorded_reaction",
                "edge_status": "reference_only",
            },
        ],
        "endpoint_annotations": [],
        "source_groups": [
            {
                "source_group_id": group_id,
                "independence_status":
                    "related" if repeated_substrate else "unknown",
                "member_records": [qid],
                "note": (
                    "S1 一题一组(预注册 §7);" +
                    ("跨题重复底物(related)" if repeated_substrate
                     else "单出现底物(unknown:研究级独立性未审计)") +
                    ";任何题不标 independent"),
            },
        ],
        "split_assignment": {
            "split": "held_out",
            "split_rule_version": S5B_SPLIT_RULE_VERSION,
            "route_group_keys": [qid],
        },
        "coverage_statement": {
            "covered_axes": ["single_step_net_reaction"],
            "known_gaps": list(S5B_KNOWN_GAPS),
            "not_evaluable_node_ids": [],
            "not_evaluable_edge_ids": [],
        },
        "provenance_manifest": [
            {
                "provenance_id": prov_id,
                "source_group_id": group_id,
                "source_origin": "database",
                "evidence_basis": "database_recorded_reaction",
                "citation_ref": qid,
                "structure_match_scope": "strict_structure",
                "observation_scope": (
                    "recorded_only+V6_chemistry_audit_and_microbe_confirmed"
                    "_literature_screening(count_level_fact)"),
                "source_conditions": [],
                "independent_status":
                    "related" if repeated_substrate else "unknown",
            },
        ],
        "creation_review": {
            "review_status": "pending_user_teacher_review",
            "reviewer": "s5b-builder",
            "note": (
                "S5b 构建器按预注册转换规则生成(真实题卷;评审后置——"
                "mimo 三触发点按 AGENTS.md 执行);" +
                S5B_PARTICIPANT_DISCLOSURE),
        },
    }
    validate_reference_graph(graph)
    return graph


def s5b_graph_id(qid: str) -> str:
    """rg298-<qid 派生稳定 ID>(预注册 §2)。"""
    return f"rg298-{stable_id('s5bg', str(qid))[:16]}"


def s5b_run_id(qid: str, batch_tag: str) -> str:
    """每题一个独立 run 的稳定 run_id。"""
    return f"{batch_tag}-{stable_id('s5br', str(qid))[:16]}"


# ---------------------------------------------------------------- run 输入


def build_run_input(question: dict, *, batch_tag: str,
                    pools: dict[str, list[dict]],
                    provider_kind: str = "real") -> dict:
    """每 qid 一条 PPV1 run 输入(根底物=substrate;无人工条件注入)。

    plan.pools = pool_provider 对该底物的检索结果(底物侧,零金标);
    plan.model.provider_kind=real(real 登记占 max_real_model_requests
    额度;额度由 profile_policy.search_limits 显式放开)。
    """
    qid = str(question["qid"])
    substrate = str(question["substrate_smiles"])
    return {
        "qid": qid,
        "run_id": s5b_run_id(qid, batch_tag),
        "substrate_smiles": substrate,
        "plan": {
            "pools": {substrate: [dict(s) for s in pools.get(substrate)
                                  or []]},
            "model": {"provider_kind": provider_kind},
        },
        "note": (
            "S5b run 输入:根底物=题面 substrate_smiles;无人工条件注入"
            "(condition_facts 空);池 = 底物侧确定性检索(零金标消费)"),
    }


# ---------------------------------------------------------------- 池供给


# W4 池策略版本(冻结候选配置:raw 预算/池宽/阈值/补位/融合规则;
# 变化 ⇒ 升版本 ⇒ 新身份)
# s5b-pool-policy-7(C 线,2026-10-14,共底物伴生供给;设计书
# C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md 冻结条款 + 实施任务书
# TASK_C_COSUB_IMPL_2026-10-14.md 落地):池**成员**变化 ⇒ 按既有身份
# 规则升版——analog 通道对齐前置门(template_elements_fit)拒的候选,
# 按**语义 a(伴生供给)**计算伴生供给(s5b-analog-cosub-supply-1):
# 模板 lhs 组分按「与底物最大 Tanimoto(Morgan r2 b2048 立体盲,与
# analog 检索同参数)= 主反应物」判主(与 noalign 归因探针 main_idx
# 同口径;并列取后位,同源实现),扣除**选定 main_idx 位置那一份**
# 后其余组分(**精确多重集**,lhs 组分序;2 H₂O ≠ 1 H₂O;同 CN 的
# 相反立体结构不互换——REAUDIT P1-BUILD-01 回修,2026-10-19)并入
# 底物侧重过元素门后编译;主反应物 cn 不可解析 ⇒ 不供给(fail-closed,
# 防"对齐到供给主副本"错形;锚面实测 0 行);**wildcard 袋整袋不供给**
# (P2-WILDCARD-01 回修,2026-10-19:裸 * 与 [H]*[H]/*C=O 等含未定义
# dummy 原子组分走同一判据 `_cosub_has_wildcard_atom`,status=
# wildcard_blocked;恢复冻结设计"本轮登记不供给、定义另行拍板"边界,
# 收窄须 CC 授权词)。编译成功的供给候选带**完整声明面**:
# spec participants 显式(reactant/primary_substrate + reactant/
# cosubstrate 逐供给组分 + product/principal_product + product/
# coproduct)+ co_substrate_states + declared_copy_components(空
# 数组,合法声明)+ cosubstrate_event_contract(NC-10 复用 corpus
# 消费面,production.prepare_hypothesis 事件级断言;record_products
# 轴 = 执行净产物全量——analog 产物执行派生不复制 donor rhs,W1 #2)
# + record_equation/record_equation_ref(pred1 消费契约发射源,
# criteria-v2 预注册 §二.1;内容 = 模板记录原样两侧去 map 组分,
# 精确多重集)。**spectator 披露**:未被模板变换消费的供给组分(map
# 全保留且不涉任何键/电荷/手性变化且身份两侧净零)逐条在
# co_substrate_states[].spectator/consumption_status 标记,不静默。
# **池策略配置本身零变化**(raw 预算/池宽/阈值/补位/融合/去重/候选
# 序/截断位置全部不动——单变量=共底物伴生供给)。供给救援失败的
# 候选维持既有 no_alignment 口径;供给过门后编译失败的候选按真实
# 拒因计数(不再计 no_alignment;该类行本次实际消耗了编译预算)。
# 诊断追加 analog_cosub_supply_* 计数(向后兼容追加字段)。
# s5b-pool-policy-6(T1a,2026-10-12,池层逐候选谱系诊断):**池成员与
# 池策略配置零变化**(raw 预算/池宽/阈值/补位/融合/去重/三通道候选
# 序/截断位置全部不动;控制流零改动)——可观测性变化升版:池构建
# 诊断从聚合计数升为逐候选明细行(``pool_diagnostics.candidates``,
# 每候选一行:channel/record_key/outcome/reason/merged_into/pool_
# rank/signature_head;compiled/compile_rejected/merged_into/pool_
# truncated 四态与既有聚合计数逐项闭合)。run_inputs/plan.pools
# 冻结内容字节不变(诊断只进 batch_manifest 条目,追加字段向后
# 兼容;既有聚合字段零变化)。
# s5b-pool-policy-5(W-D2,2026-10-10,共底物参与物显式语义 D2 编译
# 实现轮):池**成员**变化 ⇒ 按既有身份规则升版——corpus component
# -with-co-substrate 候选中的**整组分拷贝子集**经原子归属三分类
# 守门(s5b-corpus-retrieval-3)重新入池(spec 携带显式 participants/
# co_substrate_states/declared_copy_components/cosubstrate_event_
# contract;事件级 NC-10 不变量在 production.prepare_hypothesis);
# 键合融合/不可归属/不可解析/空可执行子集仍守门拒。**池策略配置
# 本身零变化**(raw 预算/池宽/阈值/补位/融合/去重/EAWAG 候选序/
# corpus_channel 语义全部不动);新入池 spec 在现行 P1 参与物集合
# 语义下事件恒 matched_participant_coverage_partial(W-D2-R1 范围
# 限定:结构性无 strict 通路仅对当前剥除 B/copy 的 root-only 参考
# 构建口径成立——NC-12 批级熔断按该参考范围限定;合法完整 B/copy
# 参考可 strict,非漂移;hit@1 预期贡献 = 0,诚实预期落字);
# 同净反应签名去重含拷贝组分(net_reaction_signature W-D2 扩展,
# 与整串/其他通道同净反应合并留痕不双占槽)。
# s5b-pool-policy-4(W-V4b,2026-10-10,编译墙深层修复轮):池**成员**
# 变化 ⇒ 按既有身份规则升版——recorded 直通两通道(EAWAG + corpus
# 整串)的编译面因公共编译判据链修复而扩大(s5b-compiler-2 stereo
# 消解 + s5b-recorded-source-2 推断映射预算/枚举面扩展);**池策略
# 配置本身零变化**(raw 预算/池宽/阈值/补位/融合/去重/EAWAG 候选
# 序/corpus_channel 语义全部不动);cosubstrate 许可规则
# (s5b-corpus-retrieval-2)零触碰。
# s5b-pool-policy-3(W-V4.1-R1,2026-10-10,Codex v4 复审 S5B-V4-01
# 回修):corpus 通道供给面许可变化——component-with-co-substrate
# 候选在 find_corpus_recorded_exact 编译前结构化 unsupported
# (s5b-corpus-retrieval-2),不再入池。**池成员变化 ⇒ 按既有身份
# 规则升版**(corpus 通道池成员收缩:组分级 spec 归零,整串/whole
# spec 不变);EAWAG 候选序/引擎 lookup 序仍零变化,corpus 候选
# 追加在后;同净反应签名去重/失败补位/池宽/融合语义不变;
# corpus_channel 消融开关语义不变(生产默认 True)。
# s5b-pool-policy-2(W-V4.1,2026-10-10):recorded 精确源通道新增
# corpus_v1(RHEA/enviPath)直通供给(find_corpus_recorded_exact;
# 用户六决策 ①②③)——EAWAG 候选序保持引擎 lookup 序零变化,corpus
# 候选按(tier strict→cn, 整串→组分, 行号)序**追加在后**;同净反应
# 签名去重/失败补位/池宽语义不变;corpus_channel 参数仅供消融对照
# (生产默认 True;False=纯 EAWAG 面,池深前后对照探针用)。
S5B_POOL_POLICY_VERSION = "s5b-pool-policy-7"
S5B_POOL_RAW_TOP = 24           # raw 检索预算(每通道)
S5B_POOL_MAX = 8                # 最终可用池宽(独特净反应槽)
S5B_POOL_THRESHOLD = 0.45       # 相似度阈值(首轮)
S5B_POOL_FALLBACK_THRESHOLD = 0.40  # 输入侧条件降阈值(不足时)
S5B_POOL_MIN_UNIQUE = 3         # 独特候选不足该数才降阈值
S5B_POOL_DIAG_SIG_HEAD_TOKENS = 4   # T1a:candidates 行签名头截取 token 数

# C 线共底物伴生供给登记面(语义 a;设计书 §二/§三.5;探针参考
# reports/ppv1_s5b/c_probe_cosubgate_2026-10-14/unlock_sim.py)
S5B_ANALOG_COSUB_SUPPLY_VERSION = "s5b-analog-cosub-supply-1"


def _net_reaction_signature(spec: dict) -> tuple:
    """独特净反应签名(委托 s5b_compiler.net_reaction_signature 单一
    构建源;W3 decide 侧与 W4 池侧共用同一判据)。"""
    from .s5b_compiler import net_reaction_signature

    return net_reaction_signature(spec)


# ---------------------------------------------------------------- 共底物伴生供给
# (C 线,s5b-analog-cosub-supply-1;语义 a;实现口径与探针
# unlock_sim.py 逐条对齐,差异处如实注明)


def _cosub_strip_map(smiles: str) -> str:
    """单组分去 atom map 并 canonical(与探针 strip_map 同口径;
    解析失败返回原文)。"""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(str(smiles or ""))
    if mol is None:
        return str(smiles or "")
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    try:
        return Chem.MolToSmiles(mol)
    except Exception:
        return str(smiles or "")


def _cosub_heavy_count(smiles: str) -> int:
    """重原子数(main 检索 fallback;解析失败 = -1,同归因探针)。"""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(str(smiles or ""))
    return mol.GetNumHeavyAtoms() if mol is not None else -1


def _cosub_has_wildcard_atom(stripped_component: str) -> bool:
    """组分是否含**未定义 dummy 原子(P2-WILDCARD-01 回修,2026-10-19:
    冻结边界“wildcard 袋本轮不供给、定义另行拍板”的判据面——裸 ``*``
    与 [H]*[H] / *C=O 等含 dummy 原子组分同属未定义通配,统一拦截;
    此前仅拦裸 ``*``、放行具体小分子组分是未授权的收窄,已回退;
    收窄须 CC 授权词)。解析失败回退串面 ``*`` 探测(坏组分由编译层
    结构化拒,此处不猜结构)。"""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    text = str(stripped_component or "")
    if not text:
        return False
    mol = Chem.MolFromSmiles(text)
    if mol is None:
        return "*" in text
    return any(atom.GetAtomicNum() == 0 for atom in mol.GetAtoms())


def _cosub_tanimoto_to_substrate(component_smiles: str,
                                 substrate_fp) -> float | None:
    """组分↔底物 Tanimoto(Morgan r2 b2048 立体盲;与 analog 检索
    SIMILARITY_FP_* 同参数;任一端不可解析 ⇒ None)。"""
    from rdkit import Chem, DataStructs, RDLogger
    from rdkit.Chem import rdMolDescriptors

    from ..services.analog_source import (
        SIMILARITY_FP_BITS,
        SIMILARITY_FP_CHIRALITY,
        SIMILARITY_FP_RADIUS,
    )

    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(str(component_smiles or ""))
    if mol is None or substrate_fp is None:
        return None
    try:
        fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(
            mol, SIMILARITY_FP_RADIUS, nBits=SIMILARITY_FP_BITS,
            useChirality=SIMILARITY_FP_CHIRALITY)
        return DataStructs.TanimotoSimilarity(fp, substrate_fp)
    except Exception:
        return None


def _substrate_fingerprint(substrate_smiles: str):
    """底物检索指纹(与 analog_source._reactant_fingerprint 同参数;
    失败 ⇒ None)。"""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdMolDescriptors

    from ..services.analog_source import (
        SIMILARITY_FP_BITS,
        SIMILARITY_FP_CHIRALITY,
        SIMILARITY_FP_RADIUS,
    )

    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(str(substrate_smiles or ""))
    if mol is None:
        return None
    try:
        return rdMolDescriptors.GetMorganFingerprintAsBitVect(
            mol, SIMILARITY_FP_RADIUS, nBits=SIMILARITY_FP_BITS,
            useChirality=SIMILARITY_FP_CHIRALITY)
    except Exception:
        return None


def analog_cosub_supply(*, mapped_lhs: str, mapped_rhs: str,
                        substrate_smiles: str) -> dict:
    """语义 a(伴生供给)供给计算(纯函数;不编译不执行)。

    规则(设计书 §二;探针 unlock_sim.py 语义 a 同口径):
    - 主反应物 = 模板 lhs 组分中与底物 Tanimoto 最大者(并列取后
      位,与归因探针 max((sim, idx)) 一致;全不可解析时回退重原子
      数最大,并列取先位);
    - 供给 = lhs 组分(精确多重集,组分序)**扣除选定 ``main_idx``
      位置那一份**后的全体(P1-BUILD-01 回修,2026-10-19:按**位置**
      扣除,不是删"第一份同 CN"——CN 是归一身份键,同 CN 的相反
      立体结构不得互换;其余 mapped lhs 组分按**原序原样保留**;
      两份完全同结构仍恰供一份。同一规则贯通供给/spectator/声明
      装配——三处均按本返回值原序消费,不另造份数判据);
    - 主反应物 cn 不可解析 ⇒ 不供给(fail-closed:无法判主时供给会
      退化成"对齐到供给主副本"的错形;归因锚面实测 0 行,如实披露);
    - 供给组分含**未定义 dummy 原子** ⇒ 整袋不供给 status=
      wildcard_blocked(P2-WILDCARD-01 回修,2026-10-19:恢复冻结设计
      "wildcard 袋本轮不供给、定义另行拍板"的边界——裸 ``*`` 与
      [H]*[H] / *C=O 等含通配原子组分走**同一条**判据
      (`_cosub_has_wildcard_atom`);此前只阻裸 ``*``、让具体小分子
      组分按自身身份供给/披露是未授权的收窄,收窄须 CC 授权词;
      锚面 75 行 dummy 袋整袋拦截,其中 35 行裸通配);
    - 无可供给组分(纯主单组分袋)⇒ status=no_supply。

    返回::

        {"status": "no_supply" | "wildcard_blocked" | "supply",
         "supply": [(mapped_comp, stripped_comp), …],  # lhs 组分序
         "main_idx": int, "main_copies": int,
         "main_cn": str | None}
    """
    from ..domain.identity import cn_identity

    lhs_comps = [c for c in str(mapped_lhs or "").split(".") if c]
    if len(lhs_comps) <= 1:
        return {"status": "no_supply", "supply": [], "main_idx": -1,
                "main_copies": 0, "main_cn": None}
    stripped = [_cosub_strip_map(c) for c in lhs_comps]
    sub_fp = _substrate_fingerprint(substrate_smiles)
    pair_sims = [(sim, idx) for idx, comp in enumerate(stripped)
                 if (sim := _cosub_tanimoto_to_substrate(
                     comp, sub_fp)) is not None]
    if pair_sims:
        main_idx = max(pair_sims)[1]      # 并列取后位(归因探针同口径)
    else:
        main_idx = max(range(len(stripped)),
                       key=lambda i: _cosub_heavy_count(stripped[i]))
    main_cn = cn_identity(stripped[main_idx]) \
        if stripped[main_idx] else None
    if main_cn is None:
        return {"status": "no_supply", "supply": [], "main_idx": main_idx,
                "main_copies": 0, "main_cn": None}
    supply: list[tuple[str, str]] = []
    main_copies = 0
    for index, (mapped_comp, stripped_comp) in enumerate(
            zip(lhs_comps, stripped)):
        comp_cn = cn_identity(stripped_comp) if stripped_comp else None
        if comp_cn == main_cn:
            main_copies += 1
        if index == main_idx:
            # 扣除**选定主位那一份**(P1-BUILD-01:位置扣除,不是第一份
            # 同 CN;其余组分含同 CN 的其他份按原序原样保留)
            continue
        supply.append((mapped_comp, stripped_comp))
    if not supply:
        return {"status": "no_supply", "supply": [], "main_idx": main_idx,
                "main_copies": main_copies, "main_cn": main_cn}
    if any(_cosub_has_wildcard_atom(stripped_comp)
           for _mc, stripped_comp in supply):
        return {"status": "wildcard_blocked", "supply": supply,
                "main_idx": main_idx, "main_copies": main_copies,
                "main_cn": main_cn}
    return {"status": "supply", "supply": supply, "main_idx": main_idx,
            "main_copies": main_copies, "main_cn": main_cn}


def _cosub_supply_spectators(mapped_lhs: str, mapped_rhs: str,
                             supply: list[tuple[str, str]]) -> list[bool]:
    """供给组分 spectator 判定(设计书 §三.5:未被模板变换消费的
    供给组分逐条披露,不得静默)。

    返回与 ``supply`` **同序对齐的布尔列表**(同去 map 身份的重复
    供给组分按模板袋位置逐条区分,不按键折叠)。判定:

    - 组分全部 map 号 ∈ 保留集(lhs∩rhs),不涉任何键变化/电荷变化/
      手性变化/元素变化,且该组分去 map 身份出现在 rhs 组分身份多重
      集(两侧净零)⇒ spectator(簿记过路;机制身份两侧净零 = 内部
      不一致的机制声明,逐条披露不删);
    - 其余 ⇒ 非 spectator(被变换消费;consumption 保持 unknown 不猜)。
    判定失败(模板侧解析异常)⇒ 全部 False(fail-open 只对坏输入,
    坏输入由编译层结构化拒;不静默断言旁观)。
    """
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    out: list[bool] = [False for _mc, _sc in supply]
    try:
        from ..domain.identity import cn_identity

        lhs = Chem.MolFromSmiles(str(mapped_lhs or ""))
        rhs = Chem.MolFromSmiles(str(mapped_rhs or ""))
        if lhs is None or rhs is None:
            return out
        lhs_maps = {a.GetAtomMapNum() for a in lhs.GetAtoms()
                    if a.GetAtomMapNum()}
        rhs_maps = {a.GetAtomMapNum() for a in rhs.GetAtoms()
                    if a.GetAtomMapNum()}
        retained = lhs_maps & rhs_maps
        map_to_lhs_idx = {a.GetAtomMapNum(): a.GetIdx()
                          for a in lhs.GetAtoms() if a.GetAtomMapNum()}
        map_to_rhs_idx = {a.GetAtomMapNum(): a.GetIdx()
                          for a in rhs.GetAtoms() if a.GetAtomMapNum()}

        def bond_table(mol) -> dict:
            table = {}
            for bond in mol.GetBonds():
                ni = bond.GetBeginAtom().GetAtomMapNum()
                nj = bond.GetEndAtom().GetAtomMapNum()
                if ni and nj:
                    table[frozenset((ni, nj))] = str(bond.GetBondType())
            return table

        lb, rb = bond_table(lhs), bond_table(rhs)
        touched_maps = {m for pair in set(lb) | set(rb)
                        if lb.get(pair) != rb.get(pair)
                        for m in pair}
        altered_maps = set(touched_maps)
        for num in retained:
            la = lhs.GetAtomWithIdx(map_to_lhs_idx[num])
            ra = rhs.GetAtomWithIdx(map_to_rhs_idx[num])
            if la.GetFormalCharge() != ra.GetFormalCharge() \
                    or la.GetChiralTag() != ra.GetChiralTag() \
                    or la.GetSymbol() != ra.GetSymbol():
                altered_maps.add(num)
        rhs_mol = Chem.MolFromSmiles(
            _cosub_strip_map(str(mapped_rhs or "")))
        rhs_identities = set()
        if rhs_mol is not None:
            for frag in Chem.GetMolFrags(rhs_mol, asMols=True,
                                         sanitizeFrags=True):
                frag_cn = cn_identity(Chem.MolToSmiles(frag))
                if frag_cn is not None:
                    rhs_identities.add(frag_cn)
        for index, (mapped_comp, stripped_comp) in enumerate(supply):
            comp_mol = Chem.MolFromSmiles(str(mapped_comp or ""))
            if comp_mol is None:
                continue
            comp_maps = {a.GetAtomMapNum() for a in comp_mol.GetAtoms()
                         if a.GetAtomMapNum()}
            comp_cn = cn_identity(stripped_comp) if stripped_comp else None
            untouched = bool(comp_maps) and comp_maps <= retained \
                and not (comp_maps & altered_maps)
            out[index] = bool(
                untouched and comp_cn is not None
                and comp_cn in rhs_identities)
    except Exception:
        return [False for _mc, _sc in supply]
    return out


def analog_record_equation(mapped_lhs: str, mapped_rhs: str) -> dict:
    """模板记录方程声明(pred1 消费契约形态,criteria-v2 预注册
    §二.1:``{"reactants": [{"smiles", "role"?}…], "products": […]}``)。

    内容 = 模板记录**原样两侧**去 map 组分(精确多重集,组分序);
    role 缺省(记录方程无角色信息,消费侧按通配)。供给源=声明源=
    模板记录,pred1 证据含义 = "记录声明了它"(防自我背书误读,
    设计书 §三.5)。
    """
    lhs_comps = [_cosub_strip_map(c)
                 for c in str(mapped_lhs or "").split(".") if c]
    rhs_comps = [_cosub_strip_map(c)
                 for c in str(mapped_rhs or "").split(".") if c]
    return {
        "reactants": [{"smiles": c} for c in lhs_comps],
        "products": [{"smiles": c} for c in rhs_comps],
    }


def _attach_analog_cosub_supply_fields(
        spec: dict, *, record_key: str, substrate_smiles: str,
        supply: list[tuple[str, str]], spectators: list[bool],
        record_equation: dict,
        execution_input_smiles: str) -> None:
    """C 线伴生供给候选的声明面装配(与 corpus 通道
    recorded_source._attach_cosubstrate_spec_fields 同源机制;协议层
    零新发明:role 复用既有枚举,系数全 unknown,NC-10 复用
    production.prepare_hypothesis 事件级消费面)。

    - participants 显式(reactant/primary_substrate + reactant/
      cosubstrate 逐供给组分(精确多重集,重复参与物经
      normalize_participants 保留歧义不合并)+ product/principal_
      product + product/coproduct);
    - participant_list_status=declared_complete(参与物清单完整度
      声明;计量/配平完整性不描述,系数恒 unknown);
    - co_substrate_states(供给组分状态装配,同源 build_chemical_
      state 严格身份内容寻址,prepare 重建同 ID)+ 逐条 spectator/
      consumption_status 披露;
    - declared_copy_components = [](空数组 = 合法声明;analog 通道
      无"声明未执行"拷贝组分——产物全部执行派生);
    - cosubstrate_event_contract:NC-10 事件级不变量输入;
      record_products 轴 = **执行净产物全量**(analog 通道产物执行
      派生、不复制 donor rhs,W1 #2;与记录方程的模板记录两侧是
      两个不同声明面,后者只服务 pred1 记录声明,不进 NC-10 计量
      轴);
    - record_equation + record_equation_ref(pred1 消费契约发射源;
      ref 确定性 = analog-supply:<record_key>,同模板同方程 ⇒ 幂等)。
    """
    from .chemstate import build_chemical_state, strict_identity_of

    def _state_ref(smiles: str) -> str:
        state = build_chemical_state(
            str(smiles), "source_product", [{"record": record_key}])
        return str(state.state_id)

    def _strict(smiles: str) -> str:
        ident = strict_identity_of(str(smiles))
        return str(ident) if ident is not None else str(smiles)

    substrate_ref = _state_ref(substrate_smiles)

    def _participant(state_ref: str, side: str, role: str) -> dict:
        return {"state_ref": str(state_ref), "side": side,
                "role": role, "coefficient": None,
                "coefficient_status": "unknown"}

    b_entries: list[dict] = []
    for index, (_mapped_comp, stripped_comp) in enumerate(supply):
        is_spectator = bool(spectators[index])
        b_entries.append({
            "smiles": str(stripped_comp),
            "state_ref": _state_ref(stripped_comp),
            "source_ref": record_key,
            "strict_identity": _strict(stripped_comp),
            "supply_index": index,
            "spectator": is_spectator,
            "consumption_status": ("spectator_pass_through"
                                   if is_spectator else "unknown"),
        })
    product_refs = [(_state_ref(str(spec["product_smiles"])),
                     "principal_product")]
    product_refs.extend(
        (_state_ref(str(c)), "coproduct")
        for c in (spec.get("coproducts") or []))
    participants = [_participant(substrate_ref, "reactant",
                                 "primary_substrate")]
    participants.extend(
        _participant(e["state_ref"], "reactant", "cosubstrate")
        for e in b_entries)
    participants.extend(
        _participant(ref, "product", role)
        for ref, role in product_refs)
    spec["participants"] = participants
    spec["participant_list_status"] = "declared_complete"
    spec["co_substrate_states"] = b_entries
    spec["declared_copy_components"] = []
    spec["cosubstrate_event_contract"] = {
        "record_key": record_key,
        "co_substrates": [
            {"smiles": str(stripped_comp),
             "strict_identity": _strict(stripped_comp)}
            for stripped_comp in dict.fromkeys(
                sc for _mc, sc in supply)],
        "record_products": [str(spec["product_smiles"])]
        + [str(c) for c in (spec.get("coproducts") or [])],
        "copy_state_refs": [],
        "co_substrate_state_refs": [e["state_ref"] for e in b_entries],
        "invariant_note": (
            "NC-10 (W-D2 corpus consumer surface reused; "
            "s5b-analog-cosub-supply-1): applicability is owned by the "
            "record-side single declaration source (this contract as "
            "the dict; no corpus block on analog specs); declared "
            "companion co-substrates MUST be a subset of the event "
            "reactant-side cosubstrate state_refs AND record_products "
            "(the EXECUTED net product set — analog products are "
            "execution-derived, not donor-copied, W1 #2) MUST equal "
            "the event product-participant multiset; asserted at "
            "production.prepare_hypothesis before the event is "
            "submitted; spec-layer gate pass does NOT substitute the "
            "event-layer check"),
        "supply_semantics": {
            "version": S5B_ANALOG_COSUB_SUPPLY_VERSION,
            "supply_rule": ("semantics_a_companion_supply: template-bag "
                            "co-substrates join the candidate net reaction "
                            "as companion participants (exact multiset, "
                            "lhs component order; the copy at the selected "
                            "main_idx position is deducted and all other "
                            "mapped lhs components are kept as-is in "
                            "original order — REAUDIT P1-BUILD-01; "
                            "2 H2O != 1 H2O)"),
            "direction_limitation_note": (
                "supply does NOT filter by side: both-side components are "
                "supplied as declared (H2O/H+ both sides; Pi/PPi product "
                "side as declared by the record) — the exemption-side "
                "direction limitation (reactant side H2O/H+ only, "
                "phosphorylation discriminator) is owned by the frozen "
                "evaluation face (evaluation.py PPV1_CRITERIA_V2 exemption "
                "sets, cf. evaluation.py:201,871-875), not by this supply "
                "layer"),
            "main_detection": ("max Tanimoto(component, substrate), ties "
                               "to the later component (noalign "
                               "attribution main_idx caliber); unparseable "
                               "main cn -> no supply (fail-closed)"),
            "spectator_disclosure": (
                "co_substrate_states[].spectator/consumption_status; "
                "spectator = supplied component untouched by the "
                "template transformation with net-zero identity across "
                "both sides; disclosed per item, never silent"),
            "wildcard_bags": ("any supplied component containing an "
                              "undefined dummy atom (bare '*', [H]*[H], "
                              "*C=O, …) blocks the whole bag "
                              "(status=wildcard_blocked; registered, not "
                              "defined; frozen boundary restored per "
                              "REAUDIT P2-WILDCARD-01 — any narrowing "
                              "requires an explicit CC authorization)"),
            "record_equation_ref": f"analog-supply:{record_key}",
        },
    }
    spec["record_equation"] = record_equation
    spec["record_equation_ref"] = f"analog-supply:{record_key}"
    # 执行输入显式声明(伴生供给参与执行:edits 对底物+供给编译,
    # 运行期执行/审计须渲染同一输入;production.prepare_hypothesis
    # 首消费核验组分严格身份多重集 == 底物 ⊕ 声明供给,fail-closed)
    spec["execution_input_smiles"] = str(execution_input_smiles)


def default_pool_provider(config: V43Config | None, *,
                           max_pool: int = S5B_POOL_MAX,
                           raw_top: int = S5B_POOL_RAW_TOP,
                           threshold: float = S5B_POOL_THRESHOLD,
                           fallback_threshold: float =
                           S5B_POOL_FALLBACK_THRESHOLD,
                           min_unique_targets: int = S5B_POOL_MIN_UNIQUE,
                           engine=None,
                           corpus_channel: bool = True):
    """真实跑的缺省池供给(W4:编译后补位 + 有界输入侧动态检索;零金标)。

    通道与融合(顺序即池序;冻结配置):
    1. **recorded 精确源**(W2,``recorded_source.find_recorded_exact``):
       strict exact 在前(引擎 lookup 置顶序),CN candidate 次之 ——
       两级都不越模型选择,只供给候选;
    1b. **corpus recorded 直通**(W-V4.1,``recorded_source.find_corpus_
       recorded_exact``;s5b-pool-policy-2 新增,决策 ①②③;
       **s5b-pool-policy-3(W-V4.1-R1)**:component-with-co-substrate
       候选编译前结构化 unsupported,池成员收缩为整串/whole spec,
       检索层共用许可规则见 s5b-corpus-retrieval-2;
       **s5b-pool-policy-5(W-D2)**:component-with-co-substrate 候选
       经原子归属三分类守门(s5b-corpus-retrieval-3)——整组分拷贝
       子集重新入池(spec 携带显式参与物/拷贝声明;事件恒 partial,
       结构性无 strict 通路,NC-12 熔断;hit@1 预期贡献 = 0),
       键合融合/不可归属子集守门拒不入池):RHEA/
       enviPath 主语料候选按(tier strict→cn、整串→组分、行号)序
       **追加在 EAWAG 候选之后**(EAWAG 面零变化,单变量归因);
       corpus 身份缺失/哈希不符 ⇒ fail-closed 抛错(不静默降级);
       ``corpus_channel=False`` 仅供消融对照(池深前后对照探针;
       生产默认 True);
    2. **类比模板**(analog_source.templates_similar_to,阈值
       ``threshold``、raw 预算 ``raw_top``):按相似度降序;
    3. 逐候选经 ``s5b_compiler``(W1 共同编译器)编译 —— **编译成功才
       进可执行池**;失败结构化原因计数(不支持层面如实披露);
       **检索序保留**(不按 key 字典序重排 —— 旧实现按 key 排序会无意
       覆盖原检索排名);
       **W-V3(S5b-pool-pregate-1)**:对齐必要条件前置 —— 模板 lhs
       元素多重集 ⊄ 底物 ⇒ 编译必 no_alignment(同源 helper
       ``template_elements_fit``;判据单一来源),在检索层拒、省编译
       预算;失败仍按 no_alignment 同口径计数(诊断另计
       ``analog_pregate_skipped``),池成员/失败语义零变化;
    4. 独特净反应槽去重(同签名合并 provenance;首个保留;corpus 与
       EAWAG 同净反应亦合并 —— 不重复占槽);
    5. **失败补位**:编译失败的候选不占槽 —— raw 前 N 全 unsupported
       而第 N+1 合法时第 N+1 可入池(旧实现 top_k=池宽导致前 8 全败
       无补位,是已证源码问题);
    6. 独特可用候选 < ``min_unique_targets`` 且 ``threshold`` >
       ``fallback_threshold`` ⇒ **仅输入侧条件**降至
       ``fallback_threshold`` 重检索(raw/池宽不变;不支持不强补满);
    7. 池宽截断 ``max_pool``(计数单位 = 独特净反应,不是 source)。

    config/engine 为 None(测试/无资产)⇒ 对应通道关闭(空池 + 模型
    novel 提案仍合法:S3B-05)。**零金标消费**:只看 substrate_smiles。
    provider.last_diagnostics 记录最近一次调用的通道/编译/去重诊断
    (build_question_batch 落 manifest 条目)。s5b-pool-policy-6(T1a,
    2026-10-12)起含逐候选谱系行 ``candidates``:每候选(编译成功/
    失败/被并/被截断)一行,纯诊断追加 —— 池成员/控制流/run_inputs
    字节零变化。
    s5b-pool-policy-7(C 线,2026-10-14):W-V3 前置门拒的 analog 候选
    按**语义 a 伴生供给**救援(analog_cosub_supply;模板袋共底物并
    入底物侧重过门编译,声明面 = participants/co_substrate_states/
    declared_copy_components/cosubstrate_event_contract/record_
    equation;wildcard 袋不供给;救援失败维持 no_alignment 原口径;
    池宽/阈值/排序/融合序零变化——单变量=共底物伴生供给)。
    """
    diagnostics: dict = {}

    def provider(substrate_smiles: str) -> list[dict]:
        substrate = str(substrate_smiles)
        diagnostics.clear()
        # ---- T1a(s5b-pool-policy-6):逐候选谱系行(纯诊断,零控制流) ----
        # 每候选一行:三通道产出点记 compiled/compile_rejected;去重/
        # 截断段回填 merged_into/pool_rank/pool_truncated。行不进 spec
        # 本体(池载荷/run_inputs 字节零污染),经 row_by_spec 以 spec
        # 对象 id 关联(编译成功行与 spec 一一对应;行 schema 见版本
        # 注释 s5b-pool-policy-6)。
        candidate_rows: list[dict] = []
        row_by_spec: dict[int, dict] = {}

        def _signature_head(spec: dict) -> list[str]:
            return [str(tok) for tok in _net_reaction_signature(spec)
                    ][:int(S5B_POOL_DIAG_SIG_HEAD_TOKENS)]

        def _diag_row(channel: str, record_key: str, outcome: str, *,
                      reason: str | None = None,
                      merged_into: str | None = None,
                      pool_rank: int | None = None,
                      signature_head: list[str] | None = None) -> dict:
            row: dict = {"channel": channel, "record_key": record_key,
                         "outcome": outcome, "reason": reason,
                         "merged_into": merged_into,
                         "pool_rank": pool_rank,
                         "signature_head": signature_head}
            candidate_rows.append(row)
            return row

        if config is None and engine is None:
            diagnostics.update({
                "pool_policy_version": S5B_POOL_POLICY_VERSION,
                "channels": [], "candidates": [],
                "note": "无 config/engine:空池(novel 合法)"})
            return []
        ordered: list[dict] = []   # (编译成功的 spec,按融合序)
        seen_keys: set[str] = set()
        compile_failures: dict[str, int] = {}
        n_recorded_strict = n_recorded_cn = 0
        n_corpus_strict = n_corpus_cn = 0
        n_cosub_specs = 0          # W-D2:共底物声明型池供给 spec 数

        def _record_compiled(spec: dict) -> None:
            ordered.append(spec)
            seen_keys.add(str(spec["key"]))

        def _record_failure(reason: str) -> None:
            compile_failures[reason] = compile_failures.get(reason, 0) + 1

        # ---- 通道 1:recorded 精确源(W2;engine 注入时) ----
        if engine is not None:
            from .recorded_source import find_recorded_exact

            exact = find_recorded_exact(
                substrate_smiles=substrate, engine=engine,
                max_reactions=raw_top)
            for cand in exact.get("candidates") or []:
                if cand.get("tier") == "recorded_strict_exact":
                    n_recorded_strict += 1
                else:
                    n_recorded_cn += 1
                # T1a:候选定位键(EAWAG 行取 record_id;spec key =
                # rec-<rid>,closure 用)
                cand_key = str(cand.get("record_key")
                               or cand.get("record_id") or "")
                spec = cand.get("compile")
                if spec is None:
                    fail_reason = str(cand.get("compile_reason")
                                      or "recorded_compile_failed")
                    _record_failure(fail_reason)
                    _diag_row("recorded", cand_key, "compile_rejected",
                              reason=fail_reason)
                    continue
                _record_compiled(spec)
                row_by_spec[id(spec)] = _diag_row(
                    "recorded", cand_key, "compiled",
                    signature_head=_signature_head(spec))
            diagnostics.update({
                "recorded_diagnostics": dict(
                    exact.get("diagnostics") or {})})

        # ---- 通道 1b:corpus recorded 直通(W-V4.1;engine 注入时) ----
        if engine is not None and corpus_channel:
            from .recorded_source import find_corpus_recorded_exact

            corpus_exact = find_corpus_recorded_exact(
                substrate_smiles=substrate, engine=engine,
                max_reactions=raw_top)
            for cand in corpus_exact.get("candidates") or []:
                if cand.get("tier") == "recorded_strict_exact":
                    n_corpus_strict += 1
                else:
                    n_corpus_cn += 1
                # T1a:候选定位键(corpus 行取 record_key(行级唯一;
                # spec key = rec-<record_key>);缺省回退 record_id)
                cand_key = str(cand.get("record_key")
                               or cand.get("record_id") or "")
                spec = cand.get("compile")
                if spec is None:
                    fail_reason = str(cand.get("compile_reason")
                                      or "recorded_compile_failed")
                    _record_failure(fail_reason)
                    _diag_row("corpus", cand_key, "compile_rejected",
                              reason=fail_reason)
                    continue
                _record_compiled(spec)
                row_by_spec[id(spec)] = _diag_row(
                    "corpus", cand_key, "compiled",
                    signature_head=_signature_head(spec))
            diagnostics.update({
                "corpus_diagnostics": dict(
                    corpus_exact.get("diagnostics") or {})})

        # ---- 通道 2/3:类比模板 + 编译(失败补位) ----
        analog_specs: list[dict] = []
        if config is not None:
            from ..services.analog_source import AnalogSourceResolver

            resolver = AnalogSourceResolver(config)

            def _compile_analog_refs(refs) -> None:
                from .s5b_compiler import (
                    compile_donor_template,
                    template_elements_fit,
                )

                def _finish_analog_spec(out: dict, record_id) -> dict:
                    spec = dict(out["spec"])
                    spec["key"] = f"tpl-{record_id}"
                    spec["transformation_ref"] = str(record_id)
                    spec["origin_group_key"] = (
                        f"analog-template:{record_id}")
                    spec["coefficient"] = 1
                    return spec

                for ref in refs:
                    # ---- W-V3(S5b-pool-pregate-1):对齐必要条件前置 ----
                    # 模板 lhs 元素 ⊄ 底物 ⇒ 编译必 no_alignment(同源
                    # helper template_elements_fit;判据单一来源,前置
                    # 只省编译预算,不改池成员/失败原因口径——no_alignment
                    # 计数含前置拒;诊断另计 analog_pregate_skipped)
                    if not template_elements_fit(
                            str(ref.mapped_lhs or ""), substrate):
                        # ---- C 线(s5b-pool-policy-7):语义 a 伴生供给
                        # 救援——前置门拒的候选按模板袋伴生供给重过门
                        # (单变量=共底物伴生供给;救援不适用/仍不过门
                        # 维持既有 no_alignment 口径,零漂移;wildcard
                        # 袋不供给,维持拦截)
                        supply = analog_cosub_supply(
                            mapped_lhs=str(ref.mapped_lhs or ""),
                            mapped_rhs=str(ref.mapped_rhs or ""),
                            substrate_smiles=substrate)
                        sub_supplied = substrate
                        supply_rescued = False
                        if supply["status"] == "wildcard_blocked":
                            diagnostics["analog_cosub_supply_"
                                         "wildcard_blocked"] = int(
                                diagnostics.get(
                                    "analog_cosub_supply_"
                                    "wildcard_blocked", 0)) + 1
                        elif supply["status"] == "supply":
                            sub_supplied = substrate + "." + ".".join(
                                sc for _mc, sc in supply["supply"])
                            if template_elements_fit(
                                    str(ref.mapped_lhs or ""), sub_supplied):
                                diagnostics["analog_cosub_supply_"
                                             "compile_attempted"] = int(
                                    diagnostics.get(
                                        "analog_cosub_supply_"
                                        "compile_attempted", 0)) + 1
                                out = compile_donor_template(
                                    mapped_lhs=str(ref.mapped_lhs or ""),
                                    mapped_rhs=str(ref.mapped_rhs or ""),
                                    center_atoms=[int(x) for x in
                                                  (ref.center_atoms
                                                   or [])],
                                    substrate_smiles=sub_supplied,
                                    record_id=str(ref.record_id or "tpl"),
                                    mapping_origin="native",
                                    alignment_ref=(
                                        f"corpus-template:"
                                        f"{ref.record_id}"),
                                    key_prefix="tpl")
                                if out.get("status") == "compiled":
                                    spec = _finish_analog_spec(
                                        out, ref.record_id)
                                    _attach_analog_cosub_supply_fields(
                                        spec,
                                        record_key=str(spec["key"]),
                                        substrate_smiles=substrate,
                                        supply=supply["supply"],
                                        spectators=_cosub_supply_spectators(
                                            str(ref.mapped_lhs or ""),
                                            str(ref.mapped_rhs or ""),
                                            supply["supply"]),
                                    record_equation=analog_record_equation(
                                        str(ref.mapped_lhs or ""),
                                        str(ref.mapped_rhs or "")),
                                    execution_input_smiles=sub_supplied)
                                    analog_specs.append(spec)
                                    row_by_spec[id(spec)] = _diag_row(
                                        "analog", str(spec["key"]),
                                        "compiled",
                                        signature_head=_signature_head(
                                            spec))
                                    diagnostics["analog_cosub_supply_"
                                                "rescued"] = int(
                                        diagnostics.get(
                                            "analog_cosub_supply_"
                                            "rescued", 0)) + 1
                                    supply_rescued = True
                                else:
                                    # 供给过门后编译失败:按真实拒因计数
                                    #(本次实际消耗编译预算,不再计
                                    # no_alignment——失败原因如实披露)
                                    fail_reason = str(out.get("reason"))
                                    _record_failure(fail_reason)
                                    _diag_row(
                                        "analog",
                                        f"tpl-{ref.record_id}",
                                        "compile_rejected",
                                        reason=fail_reason)
                                    supply_rescued = True  # 已处置
                        if not supply_rescued:
                            _record_failure("no_alignment")
                            _diag_row("analog", f"tpl-{ref.record_id}",
                                      "compile_rejected",
                                      reason="no_alignment")
                            diagnostics["analog_pregate_skipped"] = \
                                int(diagnostics.get("analog_pregate_skipped",
                                                    0)) + 1
                        continue
                    out = compile_donor_template(
                        mapped_lhs=str(ref.mapped_lhs or ""),
                        mapped_rhs=str(ref.mapped_rhs or ""),
                        center_atoms=[int(x) for x in
                                      (ref.center_atoms or [])],
                        substrate_smiles=substrate,
                        record_id=str(ref.record_id or "tpl"),
                        mapping_origin="native",
                        alignment_ref=(
                            f"corpus-template:{ref.record_id}"),
                        key_prefix="tpl")
                    if out.get("status") != "compiled":
                        fail_reason = str(out.get("reason"))
                        _record_failure(fail_reason)
                        _diag_row("analog", f"tpl-{ref.record_id}",
                                  "compile_rejected", reason=fail_reason)
                        continue
                    spec = _finish_analog_spec(out, ref.record_id)
                    analog_specs.append(spec)
                    row_by_spec[id(spec)] = _diag_row(
                        "analog", str(spec["key"]), "compiled",
                        signature_head=_signature_head(spec))

            refs = resolver.templates_similar_to(
                substrate, threshold=threshold, top_k=raw_top)
            _compile_analog_refs(refs)
            # ---- W4 #5:独特不足 ⇒ 输入侧条件降阈值(raw/池宽不变) ----
            n_unique = len({_net_reaction_signature(s)
                            for s in ordered + analog_specs})
            threshold_dropped = False
            if n_unique < int(min_unique_targets) \
                    and float(threshold) > float(fallback_threshold):
                threshold_dropped = True
                more = resolver.templates_similar_to(
                    substrate, threshold=float(fallback_threshold),
                    top_k=raw_top)
                seen_records = {str(r.record_id) for r in refs}
                _compile_analog_refs(
                    [r for r in more
                     if str(r.record_id) not in seen_records])
            diagnostics.update({
                "analog_threshold": float(threshold),
                "analog_threshold_dropped": threshold_dropped})

        # ---- 通道融合(池序):recorded strict/cn → analog(相似度序)----
        merged: list[dict] = []
        signature_of: dict[tuple, dict] = {}
        for spec in ordered + analog_specs:
            sig = _net_reaction_signature(spec)
            if sig in signature_of:
                # 同独特净反应:合并 provenance,不重复挤占槽(W4)
                first = signature_of[sig]
                first.setdefault("compile", {}).setdefault(
                    "merged_source_keys", []).append(str(spec["key"]))
                # T1a:被并候选行回填(指向幸存 key;与 merged_source_
                # keys 闭合;signature_head 按行 schema 仅 compiled 非空)
                merged_row = row_by_spec.get(id(spec))
                if merged_row is not None:
                    merged_row["outcome"] = "merged_into"
                    merged_row["merged_into"] = str(first["key"])
                    merged_row["signature_head"] = None
                continue
            signature_of[sig] = spec
            merged.append(spec)
            # W-D2-R1(Codex D2 复审 §6 P2-3 计数标签精度):
            # n_cosubstrate_declared_specs 计**去重后池槽**——旧实现
            # 在去重前递增,3 来源 spec 经同净反应签名合并成 2 槽时
            # 计 3,与 count_unit 标签"去重后"不符。去重前的编译
            # 候选数由 corpus_diagnostics.n_cosubstrate_component_
            # compiled 承接(检索层口径,含被池侧合并的候选)。
            if spec.get("cosubstrate_event_contract") is not None:
                n_cosub_specs += 1
        # ---- T1a:截断前排序位回填(1 基;超出池宽 ⇒ pool_truncated;
        # 排序/截断本身零改动,只读 merged 序) ----
        for rank, spec in enumerate(merged, start=1):
            rank_row = row_by_spec.get(id(spec))
            if rank_row is not None:
                rank_row["pool_rank"] = rank
                if rank > int(max_pool):
                    rank_row["outcome"] = "pool_truncated"
                    rank_row["signature_head"] = None
        diagnostics.update({
            "pool_policy_version": S5B_POOL_POLICY_VERSION,
            "n_recorded_strict_exact": n_recorded_strict,
            "n_recorded_cn_candidate": n_recorded_cn,
            "n_corpus_strict_exact": n_corpus_strict,
            "n_corpus_cn_candidate": n_corpus_cn,
            # W-D2(T-4/R32-CS5-3):共底物拷贝型池供给计数 + 计数标签
            # 进数据(文档标签不替代机读标签;R31-4 纪律覆盖拆分后
            # 新类目)。n_cosubstrate_declared_specs 计**去重后池供给
            # spec 数**(W-D2-R1 修正:去重后、截断前——去重前编译
            # 候选数见 corpus_diagnostics.n_cosubstrate_component_
            # compiled;不凭本字段计算命中或池净槽),事件数在其下游、
            # 判分后 partial 命中数须另以 n_cosubstrate_partial_
            # matches 披露(带 partial 语义标签,不与 hit 混列)。
            "n_cosubstrate_declared_specs": n_cosub_specs,
            "cosubstrate_pool_labels": {
                "count_unit": "pool_specs(去重后、截断前)",
                "count_basis": "supply_face",
                "count_precision_note": (
                    "W-D2-R1: counted AFTER same-net-reaction signature "
                    "dedup and BEFORE max_pool truncation; pre-dedup "
                    "compiled candidate counts live in "
                    "corpus_diagnostics.n_cosubstrate_component_compiled "
                    "(retrieval face); do not derive hit counts or net "
                    "pool slots from this field"),
                "expected_match_semantics": (
                    "pool specs, not events; cosubstrate-declared "
                    "events match matched_participant_coverage_partial "
                    "under current P1 (no strict path under the "
                    "CURRENT ROOT-ONLY (B/copy-stripped) reference "
                    "construction scope — NC-12 batch fuse scoped to "
                    "that reference construction only; a legal "
                    "complete B/copy reference may legitimately match "
                    "strict, which is not drift; hit@1 expected "
                    "contribution = 0)"),
                "policy7_supply_note": (
                    "s5b-pool-policy-7: analog companion-supply specs "
                    "(co_substrate_states + cosubstrate_event_contract + "
                    "record_equation) join n_cosubstrate_declared_specs; "
                    "under criteria-v2 with a resolvable declaration "
                    "chain (provenance_records.record_equation), "
                    "bookkeeping-extra events may rise to exact "
                    "(v1_exempt tier); the unlock face is a compile "
                    "face, NOT a hit prediction"),
            },
            "n_analog_compiled": len(analog_specs),
            "n_unique_net_reactions": len(merged),
            "n_pool_returned": min(len(merged), int(max_pool)),
            "compile_failure_histogram": dict(
                sorted(compile_failures.items())),
            # C 线(s5b-pool-policy-7):伴生供给诊断(追加字段,向后
            # 兼容;rescued = 供给过门且编译成功入池的候选数;
            # compile_attempted = 供给过门后实际发起的编译次数(成功
            # 与失败都计;失败拒因进 compile_failure_histogram,不再计
            # no_alignment);wildcard_blocked = wildcard 袋维持拦截数)
            "analog_cosub_supply_version": S5B_ANALOG_COSUB_SUPPLY_VERSION,
            "analog_cosub_supply_rescued": int(
                diagnostics.get("analog_cosub_supply_rescued", 0)),
            "analog_cosub_supply_compile_attempted": int(
                diagnostics.get("analog_cosub_supply_compile_attempted", 0)),
            "analog_cosub_supply_wildcard_blocked": int(
                diagnostics.get("analog_cosub_supply_wildcard_blocked", 0)),
            # T1a:逐候选谱系行(追加字段,向后兼容;行 schema 见
            # s5b-pool-policy-6 版本注释)
            "candidates": candidate_rows,
        })
        return merged[:int(max_pool)]

    provider.last_diagnostics = diagnostics
    return provider


# ---------------------------------------------------------------- 主入口


def build_question_batch(
    questions_path: str | Path,
    output_root: str | Path,
    *,
    batch_tag: str = "s5b-298",
    pool_provider=None,
    provider_kind: str = "real",
    repo_root: str | Path | None = None,
    question_limit: int | None = None,
    synthetic_review: bool = False,
) -> dict:
    """构建题卷批:参考图 + run 输入 + split 清单 + 批次清单。

    输出(output_root 之下;金标承载物,必须 gitignored 根):
    - ``reference_graphs/<graph_id>.json``(298 图,含金标产物);
    - ``run_inputs/<qid>.json``(每 qid 一条 run 输入);
    - ``split_manifest.json``;
    - ``batch_manifest.json``(冻结注册序、qid→run_id/graph 映射、
      题卷 SHA256;**不含金标取值**,可作判分输入的配对单一来源)。

    synthetic_review=True(测试夹具)⇒ 参考图 creation_review 改标
    synthetic_rule_level(如实)。
    """
    root = check_output_root(output_root, repo_root=repo_root)
    questions = load_questions(questions_path)
    if question_limit is not None:
        questions = questions[:int(question_limit)]
    substrate_counts: dict[str, int] = {}
    for record in questions:
        substrate_counts[str(record["substrate_smiles"])] = \
            substrate_counts.get(
                str(record["substrate_smiles"]), 0) + 1
    graphs_dir = root / "reference_graphs"
    inputs_dir = root / "run_inputs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    provider = pool_provider if pool_provider is not None \
        else default_pool_provider(None)
    entries: list[dict] = []
    for record in questions:
        qid = str(record["qid"])
        substrate = str(record["substrate_smiles"])
        graph = build_reference_graph(
            record, repeated_substrate=substrate_counts[substrate] > 1)
        if synthetic_review:
            graph["creation_review"] = {
                "review_status": "synthetic_rule_level",
                "reviewer": "s5b-builder",
                "note": "S5b 构建器合成夹具(无真实金标)",
            }
        graph_path = graphs_dir / f"{graph['reference_graph_id']}.json"
        graph_path.write_text(
            json.dumps(graph, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
        pools = {substrate: provider(substrate)}
        pool_specs = pools[substrate]
        pool_diag = dict(getattr(provider, "last_diagnostics", None) or {})
        run_input = build_run_input(
            record, batch_tag=batch_tag, pools=pools,
            provider_kind=provider_kind)
        input_path = inputs_dir / f"{qid}.json"
        input_path.write_text(
            json.dumps(run_input, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
        entries.append({
            "qid": qid,
            "run_id": run_input["run_id"],
            "reference_graph_id": graph["reference_graph_id"],
            "graph_rel": f"reference_graphs/"
                         f"{graph['reference_graph_id']}.json",
            "graph_sha256": reference_graph_sha256(graph),
            "run_input_rel": f"run_inputs/{qid}.json",
            "substrate_smiles": substrate,
            "pool_size": len(pool_specs),
            "pool_diagnostics": pool_diag,
            "n_gold_products": len(record["products_smiles"]),
            "repeated_substrate": substrate_counts[substrate] > 1,
        })
    split_manifest = {
        "schema_version": PPV1_SPLIT_MANIFEST_VERSION,
        "split_manifest_id": f"sm-s5b-{batch_tag}",
        "split_rule_version": S5B_SPLIT_RULE_VERSION,
        "input_data_manifest_hash": _file_sha256(questions_path),
        "assignments": [
            {"reference_graph_id": e["reference_graph_id"],
             "source_group_id": f"sg-{e['qid']}",
             "split": "held_out"}
            for e in entries],
        "unseen_exclusion_manifest": {
            "track": "unseen_path_inference", "excluded": []},
    }
    (root / "split_manifest.json").write_text(
        json.dumps(split_manifest, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    questions_sha = _file_sha256(questions_path)
    manifest = {
        "s5b_builder_version": S5B_BUILDER_VERSION,
        "batch_tag": batch_tag,
        "questions_source": str(Path(questions_path)),
        "questions_source_sha256": questions_sha,
        "n_questions": len(entries),
        "provider_kind": provider_kind,
        "registration_order": [e["qid"] for e in entries],
        "entries": entries,
        "gold_policy": (
            "参考图/题面承载物只落本 gitignored 根;本清单零金标取值;"
            "判分时金标才进入判分进程(s5b_scoring;零 LLM)"),
    }
    (root / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    return manifest


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(
        Path(path).read_bytes()).hexdigest()
