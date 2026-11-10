"""S5b 判分与报告 —— 封存答卷后的零 LLM 聚合(双口径;契约登记
s5b-scoring-1)。

职责与边界:

- 跑完封存答卷后执行:**金标只在此时进入判分进程**(参考图从批根
  gitignored 目录装载;判分零 LLM、零网络);
- 逐 qid 走 ``evaluate_scientific``(真实数据门按其当前签名接线:
  ``data_scope=real`` + 预注册批准记录(批根 preregistration_approval
  .json,主会话在用户确认读后落盘);未批准 ⇒ 结构化拒,不评);
- **主口径(新,预注册 §5.2)**:参考边召回 hit@1/@3/@5 —— 每题命中
  ⇔ 该题参考边 ``match_status=matched_strict``;候选事件清单 = 配对
  导出中反应物侧含根参考节点严格命中状态的全部已提交事件,按事件
  提交时序 ``(created_at, event_id)`` 升序;rank = 首个 matched_strict
  事件位次(1-based);分母固定 = 全部注册 qid(失败/unknown/qid 缺配/
  预算漏展开/空候选全算未命中);
- **老口径敏感性表(第二口径,预注册 §5.4 + codex S5B-L02 订正)**:
  复刻 v43-ec298-scorer-2 官方主口径 —— 候选 = 配对导出事件(同上
  报告序)的报告投影产物(``report_projections.product_ranks`` 按
  ``report_rank`` 序)的产物 SMILES **展平成串**(每串一个候选;K 槽
  = 产物字符串,不是事件);``report_rank=None`` 的宽度外产物**不进
  候选序列**(L02 #3:只消费非 None 位次,宽度外产物计数披露);逐
  候选整串 ``cn_identity`` ∈ 该题金标产物 cn 身份集合(任一相等即中,
  首中位次;复用 ``exam_v2.first_hit_rank`` 只读,不重写);另报
  多组分 any-of 第三表(``component_mode``,探索性,不与主表混算);
- **失败/unknown/预算漏展开展开单列**(match_status 全桶 +
  not_evaluated 原因);
- CI:主口径 bootstrap 95% 按 source group 聚类重采样(S1 一题一组;
  如实披露:S1 单题簇不消除跨题相关——codex L02 #5);S2 按底物归并
  敏感性 + Wilson 95% 按题敏感性;
- 报告:技术版 + 大白话版,数字一律带题域标签 **298**,不外推 dev;
  主口径与老口径并列,通过线判定带口径声明(预注册 §5.3)。

判分产物只落批根(gitignored);metrics/聚合表不含金标 SMILES 取值
(命中/位次/桶标签是判分结论,非金标内容)。

S5b HIT50 v3 回修(S5B-V3-01,2026-10-10,正链复审 §4.1/§5 D1;
匹配/排序/口径判定零触碰):

- **判分入口严格 data_scope 校验**:``score_s5b_batch`` 首消费与
  评测器 ``resolve_data_scope`` 共用同一判据 —— 显式空串/None/bool/
  数值/未知字符串("Real" 等变体)⇒ S5bScoringError(kind=
  s5b_data_scope_invalid)先于任何批文件装载拒;完全省略参数的既有
  签名默认 real 保留(provenance 机读);CLI choices 不代 API 校验;
- **§9-4 独立 basis 门 shape 全集核**:real 档 bases_by_graph 缺
  coverage/缺 bases/空/非 dict/缺键/foreign 键/非 qid_strict 字符串
  ⇒ 先拒零 metrics;门只核档位与覆盖、不核映射(gate_scope 机读
  落字);synthetic 档回退配对不受影响。
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from ..domain.identity import cn_identity
from .evaluation import (
    CRITERIA_V4_BUCKET_MATCHED,
    CRITERIA_V4_BUCKET_NO_EVENT,
    CRITERIA_V4_BUCKET_PARTIAL,
    CRITERIA_V4_BUCKET_PRODUCT_MISMATCH,
    CRITERIA_V4_BUCKET_REFERENCE_INVALID,
    CRITERIA_V4_BUCKETS,
    CRITERIA_V4_HIT_MODE_SCOPE,
    CRITERIA_V4_METRIC_DISCIPLINE_NOTE,
    CRITERIA_V4_METRIC_NAME,
    CRITERIA_V5_BUCKET_MATCHED,
    CRITERIA_V5_BUCKET_NO_EVENT,
    CRITERIA_V5_BUCKET_PARTIAL,
    CRITERIA_V5_BUCKET_PRODUCT_MISMATCH,
    CRITERIA_V5_BUCKET_REFERENCE_INVALID,
    CRITERIA_V5_BUCKETS,
    CRITERIA_V5_C4STAR_DISPLAY_NAME,
    CRITERIA_V5_C4STAR_RULE_VERSION,
    CRITERIA_V5_C4STAR_SCOPE_NOTE,
    CRITERIA_V5_COPRODUCT_TRACEABILITY_ALLOWED,
    CRITERIA_V5_HIT_MODE_SCOPE,
    CRITERIA_V5_METRIC_DISCIPLINE_NOTE,
    CRITERIA_V5_METRIC_NAME,
    PPV1_CRITERIA_V5_PREREG_DOC,
    PPV1_CRITERIA_V1,
    PPV1_CRITERIA_V4,
    PPV1_CRITERIA_V5,
    PPV1_EVALUATION_VERSION,
    EvaluationContractError,
    evaluate_scientific,
    native_export_reader_from_ledger,
    resolve_criteria_version,
    resolve_data_scope,
)
from .profile import (
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
)
from .reference_graph import load_reference_graph

S5B_SCORING_VERSION = "s5b-scoring-1"

# 预注册批准状态(冻结稿升格 2026-10-09:preregistration_confirmed;
# 兼容 approved/confirmed——凡非空且不以 pending 开头即视为已批准,
# 传给评测器时统一映射为其契约要求的 "approved")
_PREREG_APPROVAL_FILE = "preregistration_approval.json"
_PREREG_DOC_NAME = "POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md"

# 通过线(预注册 §5.3 冻结;历史参照线锚 = 老口径首轮数字,主口径
# 系统性更严——结论句必须双口径并列,不得单报主口径宣称达到)
S5B_PASS_LINES = {"hit@1": 116, "hit@3": 128, "hit@5": 130}

# 老口径 caliber 策略(L02 #3 默认:非 None 位次才进候选序列;
# 字段可调留待回修代理订正稿落字后切换)
S5B_DEFAULT_CALIBER_POLICY = {
    "old_caliber": "v43-ec298-scorer-2-official-any-one",
    "report_rank_none_policy": "exclude_from_candidates",
    "disclose_width_capped_products": True,
    "component_anyof_table": True,
}

_BOOTSTRAP_SEED = 20261009
_BOOTSTRAP_ITERS = 2000


class S5bScoringError(RuntimeError):
    """判分契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 预注册门

# R1(S5b W6):批准状态共用枚举白名单 —— approved/confirmed/
# preregistration_confirmed 视为已批准;rejected/空白/not_approved/
# pending 族/未知取值一律拒(旧实现"非空且不含 pending 即通过"会把
# rejected/not_approved 误放行)。归一 helper 也验证(两处同一白名单,
# 不另造第二套判据)。
PREREG_APPROVAL_APPROVED_STATUSES = frozenset((
    "approved", "confirmed", "preregistration_confirmed"))


def preregistration_approved(preregistration: dict | None) -> bool:
    """批准判定(R1 白名单):approval_status ∈ 白名单(大小写不敏感、
    两侧空白归一)⇒ 已批准;其余一切取值(含 rejected/not_approved/
    pending 族/空白/未知)⇒ 拒。"""
    status = str((preregistration or {}).get("approval_status") or
                 "").strip().lower()
    return status in PREREG_APPROVAL_APPROVED_STATUSES


def normalize_preregistration(preregistration: dict | None) -> dict | None:
    """传给 evaluate_scientific 前归一(其契约要求 approval_status
    恰为 "approved";白名单内三值归一,其余字段原样透传)。

    R1:非白名单取值 ⇒ S5bScoringError(结构化拒;归一入口不静默洗
    白 rejected/not_approved/未知状态)。``None``(合成口径无预注册
    记录;真实口径的门已在上游拒绝 None)原样透传 —— 评测器自身的
    pending_preregistration 状态语义兜底,不伪造 approved。"""
    if preregistration is None:
        return None
    prereg = dict(preregistration)
    status = str(prereg.get("approval_status") or "").strip().lower()
    if status not in PREREG_APPROVAL_APPROVED_STATUSES:
        raise S5bScoringError(
            f"预注册批准状态非法:{status!r}(白名单 = "
            f"{sorted(PREREG_APPROVAL_APPROVED_STATUSES)};"
            "rejected/not_approved/pending/未知一律拒,不静默归一)",
            {"kind": "s5b_preregistration_status_invalid",
             "approval_status": status,
             "allowed": sorted(PREREG_APPROVAL_APPROVED_STATUSES)})
    prereg["approval_status"] = "approved"
    return prereg


def preregistration_from_doc(
        doc_path: str | Path | None = None) -> dict | None:
    """从冻结稿状态行读批准(机读行
    ``preregistration_status = <值>``;非 pending ⇒ 已批准)。

    缺省路径 = 本仓 docs/ 冻结稿(Remote worktree 同仓部署时在位);
    文件缺席/无状态行 ⇒ None(fail-closed 由调用方门拒,不猜)。
    """
    if doc_path is None:
        from ..config import repo_root

        doc_path = repo_root() / "docs" / _PREREG_DOC_NAME
    path = Path(doc_path)
    if not path.is_file():
        return None
    import re

    match = re.search(
        r"preregistration_status\s*=\s*([A-Za-z0-9_\-]+)",
        path.read_text(encoding="utf-8"))
    if match is None:
        return None
    status = match.group(1)
    if not preregistration_approved({"approval_status": status}):
        return {"approval_status": status, "preregistration_id": ""}
    return {
        "approval_status": status,
        "preregistration_id": "prereg-s5b-2026-10-09",
        "source": f"preregistration_doc:{path.name}",
    }


# ---------------------------------------------------------------- 主入口


def score_s5b_batch(
    batch_root: str | Path,
    *,
    runs_root: str | Path,
    data_scope: str = "real",
    preregistration: dict | None = None,
    caliber_policy: dict | None = None,
    domain_tag: str = "298",
    criteria_version: str = PPV1_CRITERIA_V1,
    disclosure_criteria_versions: tuple[str, ...] = (),
) -> dict:
    """判分主入口:逐 qid evaluate_scientific → 双口径聚合 → 报告落盘。

    - data_scope=real(正式)⇒ 预注册批准记录必给(批根
      ``preregistration_approval.json`` 或参数;approval_status=
      approved)——评测器既有门(real ∧ 未批准 ⇒ 拒);
    - 失败题(无导出)不进 native_path_exports ⇒ 评测器按 qid 缺配
      not_evaluated(留分母算未命中);
    - **ppv1-criteria-v2**:`criteria_version` 缺省 v1 = 豁免关(既有
      判分行为不变,metrics 零新键);显式 v2 = T-1 豁免口径
      (teacher 裁定;评测/判分经 ``resolve_criteria_version`` 同一
      判据,fail-closed),聚合附 ``criteria_v2`` 块(评测器批级
      汇总透传:豁免计数 + 参考侧 v1 身份监控);v1 headline 不变;
    - **ppv1-criteria-v3**:显式 v3 = T-D-A/B 披露轴(档 A;承载
      v2 判分语义)经同一 ``resolve_criteria_version`` 判据启用;
      聚合附 ``criteria_v3`` 块透传(分臂计数/单归属/双满足/碳酸
      体系排除/参数指纹/恒空 ``tautomer_promoted_nodes``);
      **不授 strict、不进 hit@1**;v1/v2 缺省零新键;
    - **ppv1-criteria-v4**:显式 v4 = ``matched_product_hit`` 主口径
      (§1–§4;评测/判分经同一 ``resolve_criteria_version``);逐题附
      ``product_hit`` 行、聚合附独立 ``matched_product_hit_caliber``
      块(§3 五桶 + 独立 hit@K;与 ``main_caliber`` 的 v2 strict
      **分列**,禁止同名);``criteria_v4`` 批级块透传;
      ``disclosure_criteria_versions`` 可并列 v3 披露轴(v4 决定
      命中、v3 归一披露互不改写);
    - **ppv1-criteria-v5**:显式 v5 = ``role_bound_product_hit``
      (v4 全部条件 + 事件产物侧 role 恰好 ``principal_product`` 的
      收紧;评测/判分经同一 ``resolve_criteria_version``);逐题附
      ``role_bound_hit`` 行、聚合附独立
      ``role_bound_product_hit_caliber`` 块(§2.2 五桶 + 独立
      hit@K + §5.1/§5.2 披露轴;与 ``main_caliber`` 的 v2 strict
      及 v4 ``matched_product_hit_caliber`` **分列**,禁止同名);
      ``criteria_v5`` 批级块透传;v4 块不产生(不混写);
    - 返回完整聚合 dict;metrics.json / report.md / report_plain.md
      落批根。
    """
    # ---- 判据版本首消费校验(v1/v2/v3 同一判据
    # resolve_criteria_version;白名单外值一律结构化拒) ----
    resolve_criteria_version(criteria_version)
    # ---- S5B-V3-01:判分入口严格 data_scope 校验(先于任何批文件装载;
    # 与评测首消费共用 resolve_data_scope 同一判据,异常包装为本契约
    # S5bScoringError;CLI choices 不代 API 校验 —— 本函数是公开
    # score API 的权威门)。完全省略参数 ⇒ 既有签名默认 real 保留
    # (provenance 机读进聚合)。 ----
    try:
        data_scope, data_scope_provenance = resolve_data_scope(
            data_scope, field="data_scope", default="real",
            present=True)
    except EvaluationContractError as exc:
        raise S5bScoringError(
            f"data_scope 非法:{exc}(判分入口先拒;显式空/null/bool/"
            "数值/未知字符串不得进判分,也不得绕过 real 门;"
            "允许 {real, synthetic_rule_level};缺省=签名默认 real)", {
                **{k: v for k, v in dict(exc.detail or {}).items()
                   if k != "kind"},
                "kind": "s5b_data_scope_invalid",
                "shared_judgment": "evaluation.resolve_data_scope",
                "note": ("CLI choices 只是输入便利;公开 API 以本门为"
                         "权威判据(评测/判分同源)")}) from exc
    # 缺省语义登记:完全省略参数 ⇒ 签名默认 real(与显式传 "real"
    # 同值;provenance 机读披露该规则,缺省与显式坏值不混类)
    data_scope_provenance = dict(data_scope_provenance)
    data_scope_provenance["signature_default"] = "real"
    batch_root = Path(batch_root)
    runs_root = Path(runs_root)
    manifest = json.loads(
        (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
    split_manifest = json.loads(
        (batch_root / "split_manifest.json").read_text(encoding="utf-8"))
    order = [str(q) for q in manifest.get("registration_order") or []]
    entries = {str(e["qid"]): e for e in manifest.get("entries") or []}
    if not order:
        raise S5bScoringError(
            "批清单注册序为空(零题;fail-closed)", {
                "kind": "s5b_scoring_empty_batch",
                "batch_root": str(batch_root)})
    prereg = preregistration
    if prereg is None:
        approval_path = batch_root / _PREREG_APPROVAL_FILE
        if approval_path.is_file():
            prereg = json.loads(
                approval_path.read_text(encoding="utf-8"))
    if prereg is None:
        prereg = preregistration_from_doc()
    if data_scope == "real" and not preregistration_approved(prereg):
        raise S5bScoringError(
            "data_scope=real 而预注册批准记录缺席/未批准(评测器既有门:"
            "真实数据评测须用户/teacher 完成题源/金标/样本量/阈值/预算"
            "裁定;fail-closed 不评。批准通道按优先级:显式参数 > 批根 "
            f"{_PREREG_APPROVAL_FILE} > 冻结稿状态行(非 pending 即"
            "已批准,兼容 preregistration_confirmed))", {
                "kind": "s5b_preregistration_not_approved",
                "data_scope": data_scope,
                "approval_status": str(
                    (prereg or {}).get("approval_status") or ""),
                "approval_path": str(
                    batch_root / _PREREG_APPROVAL_FILE)})
    # ---- 装载:参考图(金标入判分进程)+ 导出(经首消费读取) ----
    graphs: dict[str, dict] = {}
    graph_by_qid: dict[str, str] = {}
    for qid in order:
        entry = entries[qid]
        graph = load_reference_graph(
            batch_root / str(entry["graph_rel"]))
        graphs[graph["reference_graph_id"]] = graph
        graph_by_qid[qid] = graph["reference_graph_id"]
    exports: list[dict] = []
    export_payloads: dict[str, dict] = {}
    cases = {}
    for qid in order:
        case = _read_case(batch_root, qid)
        cases[qid] = case
        digest = str((case or {}).get("export_digest") or "")
        run_id = str((entries[qid] or {}).get("run_id") or "")
        if digest and run_id:
            exports.append({
                "run_id": run_id, "export_digest": digest, "qid": qid,
                "lossy_projection": False,
            })
    reader = _batch_export_reader(runs_root, export_payloads)
    evaluation_input = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "run_identity": {
            "run_id": f"s5b-batch:{manifest.get('batch_tag') or 's5b'}",
            "profile_version": PPV1_PROFILE_SCHEMA_VERSION,
            "export_schema_version": PPV1_NATIVE_EXPORT_VERSION,
        },
        "native_path_exports": exports,
        "reference_graph_manifest": [
            {"reference_graph_id": graphs[graph_by_qid[qid]]
             ["reference_graph_id"],
             "sha256": str(entries[qid]["graph_sha256"]),
             "domain": domain_tag,
             "track": "known_evidence_reconstruction",
             "qid": qid}
            for qid in order],
        "split_manifest": split_manifest,
        "domain": domain_tag,
        "track": "known_evidence_reconstruction",
        "metric_policy_version": "ppv1-evaluation-metrics-proposed",
        "preregistration_id": str(
            (prereg or {}).get("preregistration_id")
            or "prereg-s5b-pending"),
        "scoring_policy_version": "ppv1-evaluation-scoring-proposed",
        "missingness_policy_version":
            "ppv1-evaluation-missingness-proposed",
        "data_scope": data_scope,
        "interface_verification": False,
        "model_provider_policy": {
            "provider_kind": "real",
            "authorization": str(
                (prereg or {}).get("user_authorization")
                or "s5b-launch-authorized-by-user-2026-10-09"),
        },
    }
    output = evaluate_scientific(
        evaluation_input, reference_graphs=graphs,
        native_export_reader=reader,
        preregistration=normalize_preregistration(prereg),
        criteria_version=criteria_version,
        disclosure_criteria_versions=disclosure_criteria_versions)
    # ---- W-V6.1(mimo r27 判断面一附条件;§9-④ 程序门,随 v3 交付
    # 工程落地):评分聚合前落程序检查 —— data_scope=real ∧ 任一
    # pairing basis 非 qid_strict ⇒ S5bScoringError(结构化、机器可读
    # detail)。与 evaluation-5 代码守卫(评测器内 real 首消费拒
    # root_identity_fallback)双保险:本门在**判分入口**独立复核
    # 评测器产出的 bases_by_graph,不依赖评测器内部异常路径;真实批
    # 判分聚合/落盘前 fail-closed。synthetic 档不受影响(合成回退
    # basis 聚合照旧)。 ----
    # ---- S5B-V3-01 同门补齐(正链复审 §4.1/§5 D1):独立 basis 门
    # shape 全集核 —— expected graphIds 非空、bases_by_graph 类型/
    # 非空/键集精确覆盖注册图(缺键/foreign 键拒)、值全 qid_strict
    # 字符串;缺 coverage/缺 bases/空/缺键/foreign/非 strict 负控先
    # 拒零 metrics(本门先于逐题聚合循环)。**门只核档位与覆盖,不核
    # 映射**(qid↔图映射正确性由评测器权威链负责;本门不替代
    # source/reference 绑定,也不证明 qid 真值)。 ----
    if data_scope == "real":
        pairing_block = ((output or {}).get("coverage_report") or {}) \
            .get("pairing")
        bases = pairing_block.get("bases_by_graph") \
            if isinstance(pairing_block, dict) else None
        expected_graph_ids = sorted(graphs)
        gate_reasons: list[str] = []
        non_strict: dict[str, str] = {}
        if bases is None:
            gate_reasons.append("bases_by_graph_missing")
        elif not isinstance(bases, dict):
            gate_reasons.append("bases_by_graph_not_dict")
        elif not bases:
            gate_reasons.append("bases_by_graph_empty")
        else:
            observed_keys = {str(g) for g in bases}
            expected_keys = set(expected_graph_ids)
            missing_keys = sorted(expected_keys - observed_keys)
            foreign_keys = sorted(observed_keys - expected_keys)
            if missing_keys:
                gate_reasons.append("bases_by_graph_missing_keys")
            if foreign_keys:
                gate_reasons.append("bases_by_graph_foreign_keys")
            for graph_id, basis_value in sorted(bases.items()):
                if not isinstance(basis_value, str) \
                        or basis_value != "qid_strict":
                    non_strict[str(graph_id)] = (
                        basis_value if isinstance(basis_value, str)
                        else repr(basis_value))
            if non_strict:
                gate_reasons.append("bases_not_all_qid_strict")
        if gate_reasons:
            raise S5bScoringError(
                "data_scope=real 而配对 basis 门未过(§9-4 程序门:"
                f"{';'.join(gate_reasons)};真实批须 bases_by_graph 非空"
                "且精确覆盖全部注册图、值全为 qid_strict;判分入口独立"
                "复核,先于聚合/落盘;与 evaluation-5 首消费守卫双"
                "保险)", {
                    "kind": "s5b_real_pairing_not_all_qid_strict",
                    "data_scope": data_scope,
                    "reasons": gate_reasons,
                    "non_qid_strict_bases": non_strict,
                    "n_graphs": (len(bases)
                                 if isinstance(bases, dict) else 0),
                    "expected_graph_ids": expected_graph_ids,
                    "missing_graph_ids": sorted(
                        set(expected_graph_ids)
                        - ({str(g) for g in bases}
                           if isinstance(bases, dict) else set())),
                    "foreign_graph_ids": sorted(
                        ({str(g) for g in bases}
                         if isinstance(bases, dict) else set())
                        - set(expected_graph_ids)),
                    "gate_scope": (
                        "本门只核配对档位与键覆盖(全局 bases_by_graph "
                        "对注册图集合的精确覆盖、值全 qid_strict),"
                        "不核 qid↔图映射正确性 —— 映射由评测器权威链"
                        "(evaluation-4/5 配对守卫)负责;本门不证明 "
                        "qid 真值"),
                    "note": ("预注册 §9-4 配对硬门:coverage_report."
                             "pairing.bases_by_graph 须全为 qid_strict;"
                             "synthetic 档回退配对不受本门影响")})
    # ---- 逐题双口径 rank / 桶 ----
    caliber = dict(S5B_DEFAULT_CALIBER_POLICY)
    caliber.update(caliber_policy or {})
    per_qid: list[dict] = []
    sample_by_graph = {
        str(s.get("reference_graph_id")): s
        for s in output.get("sample_results") or []}
    for qid in order:
        graph_id = graph_by_qid[qid]
        sample = sample_by_graph.get(graph_id)
        case = cases.get(qid) or {}
        row = {
            "qid": qid,
            "run_id": str((entries[qid] or {}).get("run_id") or ""),
            "run_status": str(case.get("status") or "no_case"),
            "stop_reason": str(case.get("stop_reason") or ""),
        }
        payload = _paired_payload(export_payloads, sample)
        row["main"] = _main_caliber_row(sample, payload, graphs[graph_id])
        if criteria_version == PPV1_CRITERIA_V4:
            # ppv1-criteria-v4:独立行(不混入 main;与 strict 分列)
            row["product_hit"] = _product_hit_row(
                sample, payload, graphs[graph_id])
        if criteria_version == PPV1_CRITERIA_V5:
            # ppv1-criteria-v5:独立行(不混入 main、不覆盖 v4 行)
            row["role_bound_hit"] = _role_bound_hit_row(
                sample, payload, graphs[graph_id])
        row["old"] = _old_caliber_row(
            sample, payload, graphs[graph_id], caliber)
        per_qid.append(row)
    denominator = len(order)
    main_hits = {
        f"hit@{k}": sum(1 for r in per_qid
                        if (r["main"]["rank"] or math.inf) <= k)
        for k in (1, 3, 5)}
    old_hits = {
        f"hit@{k}": sum(1 for r in per_qid
                        if (r["old"]["rank"] or math.inf) <= k)
        for k in (1, 3, 5)}
    old_anyof_hits = {
        f"hit@{k}": sum(1 for r in per_qid
                        if (r["old"]["anyof_rank"] or math.inf) <= k)
        for k in (1, 3, 5)}
    buckets = _bucket_counts(per_qid)
    # ---- W0(S5b):聚合诊断 U/H5/L + 分桶/状态表闭合断言 ----
    # U = 全部合法已提交 root 事件的 strict 匹配题数(取消 K 的候选
    # 覆盖上限诊断;不改正式尺子);H5 = 正式 strict@5;L = U − H5。
    # 断言 0 ≤ H1 ≤ H3 ≤ H5 ≤ U ≤ 分母(违例 ⇒ fail-closed,判分产物
    # 不落盘);判分互斥桶(match_status)总 = 分母;运行状态附表
    # 总 = 分母(两表分开,叠加桶不重复计分母)。
    u_hits = sum(1 for r in per_qid
                 if str(r["main"].get("match_status")) == "matched_strict")
    h1 = int(main_hits["hit@1"])
    h3 = int(main_hits["hit@3"])
    h5 = int(main_hits["hit@5"])
    if not (0 <= h1 <= h3 <= h5 <= u_hits <= denominator):
        raise S5bScoringError(
            "聚合诊断单调性断言失败(0≤H1≤H3≤H5≤U≤分母;判分产物"
            "不落盘,fail-closed)", {
                "kind": "s5b_aggregate_monotonicity_violation",
                "H1": h1, "H3": h3, "H5": h5, "U": u_hits,
                "denominator": denominator})
    match_status_total = sum(
        v for k, v in buckets.items() if not k.startswith("run_"))
    run_status_total = sum(
        v for k, v in buckets.items() if k.startswith("run_"))
    run_status_table = _run_status_counts(per_qid)
    if match_status_total != denominator:
        raise S5bScoringError(
            f"判分互斥桶(match_status)总和 {match_status_total} ≠ 分母 "
            f"{denominator}(fail-closed;叠加桶不得重复计分母)", {
                "kind": "s5b_match_status_bucket_total_mismatch",
                "total": match_status_total,
                "denominator": denominator})
    if sum(run_status_table.values()) != denominator:
        raise S5bScoringError(
            f"运行状态附表总和 {sum(run_status_table.values())} ≠ 分母 "
            f"{denominator}(fail-closed)", {
                "kind": "s5b_run_status_total_mismatch",
                "denominator": denominator})
    aggregate = {
        "s5b_scoring_version": S5B_SCORING_VERSION,
        "data_scope": data_scope,
        # S5B-V3-01:机读归一来源(explicit | missing_field_default;
        # 本入口缺省=签名默认 real;显式坏值在入口首消费处拒)
        "data_scope_provenance": data_scope_provenance,
        "domain_tag": domain_tag,
        "denominator": denominator,
        "aggregate_diagnosis": {
            "U_strict_matched_questions": u_hits,
            "H1": h1, "H3": h3, "H5": h5,
            "L_below_k": u_hits - h5,
            "definition": (
                "W0 聚合诊断:U=全部合法已提交 root 事件的 strict 匹配"
                "题数(K 取消的候选覆盖上限);H5=正式 strict@5;"
                "L=U−H5(排序损失)。U<150 ⇒ 优先供给/生成;U≥150 而 "
                "H5<150 ⇒ 主攻排序。诊断不改正式尺子;不向预测侧回传"
                "逐题目标/reference/正确 source ID/oracle 事件序"),
            "monotonicity_assertion": "0<=H1<=H3<=H5<=U<=denominator: ok",
        },
        "run_status_table": run_status_table,
        "main_caliber": {
            **{k: v for k, v in main_hits.items()},
            **{f"{k}_rate": round(v / denominator, 4)
               for k, v in main_hits.items()},
            "definition": ("参考边召回(matched_strict;候选=根严格命中"
                           "反应物侧的全部已提交事件按(created_at,"
                           "event_id)升序;分母固定=注册 qid 数)"),
            "pass_lines": dict(S5B_PASS_LINES),
            "pass_line_semantics": (
                "历史参照线锚(老口径首轮数字;主口径系统性更严,达标"
                "难度更高;结论必须双口径并列,见预注册 §5.3)"),
        },
        "old_caliber_sensitivity": {
            **{k: v for k, v in old_hits.items()},
            **{f"{k}_rate": round(v / denominator, 4)
               for k, v in old_hits.items()},
            "definition": (
                "v43-ec298-scorer-2 官方主口径复刻:候选=报告投影产物"
                " SMILES 展平成串(K 槽=产物字符串),逐候选整串 cn "
                "identity ∈ 金标产物 cn 集合(任一相等即中,首中位次;"
                "不可解析占名次不命中;重复身份跳过);report_rank=None "
                "宽度外产物不进候选序列(L02 订正口径)"),
        },
        "old_caliber_anyof_multicomponent": {
            **{k: v for k, v in old_anyof_hits.items()},
            "note": ("多组分 any-of 敏感性(含 . 候选任一组分命中即中;"
                     "探索性另表,不与主表混算)"),
        },
        "buckets": buckets,
        "caliber_policy": dict(caliber),
        "per_qid": per_qid,
        "evaluator_output_status": str(output.get("status") or ""),
        "evaluator_pairing_bases": (
            (output.get("coverage_report") or {}).get("pairing")
            or {}).get("bases_by_graph") or {},
    }
    # ---- ppv1-criteria-v2:评测器批级汇总透传(启用豁免口径时;v1
    # 缺省 metrics 零新键 = 既有判分产物字节不变;v3 承载 v2 语义,
    # 块内容与 v2 逐位一致) ----
    if output.get("criteria_v2") is not None:
        aggregate["criteria_v2"] = output["criteria_v2"]
    # ---- ppv1-criteria-v3:批级披露块透传(仅 v3;档 A 只披露,不授
    # strict、不进 hit@1;v1/v2 缺省零新键) ----
    if output.get("criteria_v3") is not None:
        aggregate["criteria_v3"] = output["criteria_v3"]
    # ---- ppv1-criteria-v4:独立主口径块(仅 v4;与 strict 分列,
    # 禁止同名/跨版本比较;v1/v2/v3 缺省 metrics 零新键) ----
    if criteria_version == PPV1_CRITERIA_V4:
        aggregate["matched_product_hit_caliber"] = \
            _product_hit_caliber_block(
                [row["product_hit"] for row in per_qid], denominator)
        if output.get("criteria_v4") is not None:
            aggregate["criteria_v4"] = output["criteria_v4"]
    # ---- ppv1-criteria-v5:独立主口径块(仅 v5;与 strict/v4 分列,
    # 禁止同名/跨版本比较;v1/v2/v3/v4 缺省零新键) ----
    if criteria_version == PPV1_CRITERIA_V5:
        aggregate["role_bound_product_hit_caliber"] = \
            _role_bound_hit_caliber_block(
                [row["role_bound_hit"] for row in per_qid], denominator,
                domain_tag=domain_tag)
        if output.get("criteria_v5") is not None:
            aggregate["criteria_v5"] = output["criteria_v5"]
    aggregate["confidence_intervals"] = _confidence_intervals(
        per_qid, entries, denominator)
    metrics_path = batch_root / "metrics.json"
    metrics_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    report_md = render_report(aggregate, output)
    (batch_root / "report.md").write_text(report_md, encoding="utf-8")
    (batch_root / "report_plain.md").write_text(
        render_plain_report(aggregate), encoding="utf-8")
    aggregate["report_paths"] = {
        "metrics": str(metrics_path),
        "technical": str(batch_root / "report.md"),
        "plain": str(batch_root / "report_plain.md"),
    }
    return aggregate


# ---------------------------------------------------------------- 读取器


def _batch_export_reader(runs_root: Path,
                         cache: dict[str, dict]):
    """按导出条目 run_id 建权威 ledger 的首消费读取器(批量分发)。"""
    ledgers: dict[str, object] = {}

    def reader(entry: dict) -> dict:
        run_id = str(entry.get("run_id") or "")
        digest = str(entry.get("export_digest") or "")
        if run_id not in ledgers:
            from .search import SearchLedger
            from .store import PollutantPathwayStore
            from ..storage.artifact_store import ArtifactStore

            store = PollutantPathwayStore(
                runs_root / run_id / "pollutant.sqlite")
            artifacts = ArtifactStore(runs_root, run_id)
            ledgers[run_id] = SearchLedger(store, artifacts, run_id)
        ledger = ledgers[run_id]
        from .native_export import read_native_export

        read_back = read_native_export(
            ledger, runs_root / run_id, digest)
        payload = read_back.get("payload") or {}
        cache[digest] = payload
        return {"payload": payload}

    return reader


def _paired_payload(cache: dict[str, dict], sample: dict | None) -> dict:
    if not sample:
        return {}
    pairing = (sample or {}).get("pairing") or {}
    digest = str(pairing.get("consumed_export_digest") or "")
    if digest and digest in cache:
        return cache[digest]
    return {}


def _read_case(batch_root: Path, qid: str) -> dict | None:
    path = batch_root / "cases" / f"{qid}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------- 主口径


def _root_strict_states(sample: dict, graph: dict) -> set[str]:
    """根参考节点(参考边 from 侧)的严格命中状态集合。"""
    root_node_ids: set[str] = set()
    for edge in graph.get("edges") or []:
        root_node_ids.update(str(x) for x in edge.get("from_node_ids"))
    states: set[str] = set()
    for entry in (sample or {}).get("predicted_node_matches") or []:
        if str(entry.get("node_id")) in root_node_ids and \
                str(entry.get("match_status")) == "strict_structure":
            states.update(str(s) for s in entry.get("matched_state_ids"))
    return states


def _candidate_events(payload: dict, root_states: set[str]) -> list[dict]:
    """候选事件(反应物侧含根严格命中状态),按 (created_at, event_id)
    升序(提交时序 = 报告序的确定性代理;冻结后不得按结果重排)。"""
    if not payload or not root_states:
        return []
    out: list[dict] = []
    for event in payload.get("events") or []:
        body = event.get("payload")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                body = {}
        reactants = {str(p.get("state_ref") or "")
                     for p in (body or {}).get("participants") or []
                     if isinstance(p, dict)
                     and str(p.get("side")) == "reactant"}
        if reactants & root_states:
            out.append({
                "event_id": str(event.get("event_id") or ""),
                "created_at": str(event.get("created_at") or ""),
            })
    out.sort(key=lambda e: (e["created_at"], e["event_id"]))
    return out


def _main_caliber_row(sample: dict | None, payload: dict,
                      graph: dict) -> dict:
    """主口径逐题行:rank(首 matched_strict 事件位次)/桶/披露。"""
    if not sample:
        return {"rank": None, "match_status": "not_evaluated_no_sample",
                "note": "评测器无该样本输出(失败题留分母)"}
    status = str(sample.get("scoring_status") or "")
    edge_matches = sample.get("predicted_edge_matches") or []
    if not edge_matches:
        return {"rank": None, "match_status": "not_evaluated_no_edges",
                "scoring_status": status}
    edge = edge_matches[0]
    match_status = str(edge.get("match_status") or "unmatched")
    if status != "scored" or match_status != "matched_strict":
        reasons = [
            str(e.get("kind")) for e in
            (sample.get("scoring_errors") or [])][:4]
        return {"rank": None, "match_status": match_status,
                "scoring_status": status,
                "scoring_error_kinds": reasons}
    root_states = _root_strict_states(sample, graph)
    candidates = _candidate_events(payload, root_states)
    matched_ids = [str(e.get("event_id"))
                   for e in (edge.get("matched_events") or [])]
    rank = None
    for position, candidate in enumerate(candidates, 1):
        if candidate["event_id"] in matched_ids:
            rank = position
            break
    return {
        "rank": rank,
        "match_status": match_status,
        "n_candidate_events": len(candidates),
        "n_matched_events": len(matched_ids),
        "matched_event_not_in_candidates": bool(
            matched_ids and rank is None),
    }


# ---------------------------------------------------------------- 老口径


def _product_hit_row(sample: dict | None, payload: dict,
                     graph: dict) -> dict:
    """ppv1-criteria-v4 逐题行(matched_product_hit;与 strict 分列)。

    - 桶 = 评测器 ``sample['criteria_v4']['bucket']``(§3 五桶,互斥);
    - rank = 命中事件在**预先固定**候选序(_candidate_events:按
      (created_at, event_id) 升序;冻结后不得按结果重排)中的首个
      位次;非命中(partial/mismatch/no_event/reference_invalid)
      一律 rank=None(不改写为命中);
    - 命中事件不在候选序 ⇒ rank=None 且机读
      ``matched_event_not_in_candidates``(不静默按命中算 hit@1);
    - 本函数只消费 v4 输出的 ``criteria_v4`` 块;v1/v2/v3 输出不吃。
    """
    if not sample:
        return {"rank": None, "bucket": CRITERIA_V4_BUCKET_NO_EVENT,
                "matched_product_hit": False,
                "product_hit_partial": False,
                "product_hit_events": [],
                "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
                "n_candidate_events": 0,
                "matched_event_not_in_candidates": False,
                "note": "评测器无该样本输出(失败题留分母)"}
    block = sample.get("criteria_v4") or {}
    bucket = str(block.get("bucket") or CRITERIA_V4_BUCKET_NO_EVENT)
    if bucket not in CRITERIA_V4_BUCKETS:
        bucket = CRITERIA_V4_BUCKET_NO_EVENT
    hit_events = sorted(str(x) for x in
                        (block.get("product_hit_events") or []))
    root_states = _root_strict_states(sample, graph)
    candidates = _candidate_events(payload, root_states)
    rank = None
    if bucket == CRITERIA_V4_BUCKET_MATCHED:
        hit_ids = set(hit_events)
        for position, candidate in enumerate(candidates, 1):
            if candidate["event_id"] in hit_ids:
                rank = position
                break
    return {
        "rank": rank,
        "bucket": bucket,
        "matched_product_hit": bucket == CRITERIA_V4_BUCKET_MATCHED,
        "product_hit_partial": bucket == CRITERIA_V4_BUCKET_PARTIAL,
        "product_hit_partial_v4_sense": bool(
            block.get("product_hit_partial_v4_sense")),
        "product_hit_partial_outside_legacy_partial": bool(
            block.get("product_hit_partial_outside_legacy_partial")),
        "product_hit_events": hit_events,
        "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
        "n_candidate_events": len(candidates),
        "matched_event_not_in_candidates": bool(
            bucket == CRITERIA_V4_BUCKET_MATCHED and hit_events
            and rank is None),
    }


def _product_hit_caliber_block(rows: list[dict],
                               denominator: int) -> dict:
    """批级 matched_product_hit 口径块(§3 五桶 + hit@K;与 strict 分列)。

    桶和 = 分母(fail-closed);hit@1 ≤ hit@3 ≤ hit@5 ≤ 命中题数
    (rank 归属错误机读单列,不静默)。
    """
    counts = {bucket: 0 for bucket in CRITERIA_V4_BUCKETS}
    for row in rows:
        bucket = str(row.get("bucket") or CRITERIA_V4_BUCKET_NO_EVENT)
        if bucket not in counts:
            bucket = CRITERIA_V4_BUCKET_NO_EVENT
        counts[bucket] += 1
    if sum(counts.values()) != denominator:
        raise S5bScoringError(
            f"matched_product_hit 桶和 {sum(counts.values())} ≠ 分母 "
            f"{denominator}(fail-closed;斜杠桶不得重复计分母)", {
                "kind": "s5b_matched_product_hit_bucket_total_mismatch",
                "total": sum(counts.values()),
                "denominator": denominator})
    hits = {f"hit@{k}": sum(
        1 for row in rows if (row.get("rank") or math.inf) <= k)
        for k in (1, 3, 5)}
    matched = counts[CRITERIA_V4_BUCKET_MATCHED]
    if not (0 <= hits["hit@1"] <= hits["hit@3"] <= hits["hit@5"]
            <= matched):
        raise S5bScoringError(
            "matched_product_hit 聚合单调性断言失败"
            "(0≤hit@1≤hit@3≤hit@5≤命中题数;判分产物不落盘)", {
                "kind": "s5b_matched_product_hit_monotonicity_violation",
                "hit@1": hits["hit@1"], "hit@3": hits["hit@3"],
                "hit@5": hits["hit@5"], "matched": matched,
                "denominator": denominator})
    attribution_errors = [
        row for row in rows
        if row.get("matched_event_not_in_candidates")]
    return {
        "criteria_version": PPV1_CRITERIA_V4,
        "metric_name": CRITERIA_V4_METRIC_NAME,
        "metric_name_discipline": CRITERIA_V4_METRIC_DISCIPLINE_NOTE,
        "hit_mode_scope": CRITERIA_V4_HIT_MODE_SCOPE,
        **hits,
        **{f"{k}_rate": round(v / denominator, 4)
           for k, v in hits.items()},
        "matched_product_hit": matched,
        "product_hit_partial": counts[CRITERIA_V4_BUCKET_PARTIAL],
        "buckets": dict(sorted(counts.items())),
        "denominator": denominator,
        "rank_attribution_errors": len(attribution_errors),
        "definition": (
            "matched_product_hit(§1):存在同一个合法事件 E,底物严格"
            "身份 S ∈ R_E 且参考边声明的主产物身份集合 P ⊆ T_E;"
            "身份函数 strict_identity_of(与 v2 同一函数);P 只取"
            "产物侧 principal_product 节点;禁止跨事件拼答案"),
        "separate_from_strict": True,
        "comparability_note": (
            "本块与 main_caliber(v2 strict)分列;禁止跨版本比较 "
            "strict 数,禁止把 matched_product_hit 表述为 strict 或"
            "「反应预测正确率」"),
        "buckets_note": (
            "§3 五桶互斥;分母固定,失败/无效题不剔除;"
            "product_hit_partial 不记为命中"),
        "product_hit_partial_bucket_rule": (
            "product_hit_partial 沿既有 coverage 轴:仅当参考边旧状态"
            "为 matched_participant_coverage_partial 且 v4 未命中时"
            "计入;旧 unmatched_required_node_uncovered 题按 "
            "unmatched_product_mismatch 计,其「部分主产物命中」另以 "
            "product_hit_partial_v4_sense / "
            "product_hit_partial_outside_legacy_partial 披露"),
    }


# ---------------------------------------------------------------- ppv1-criteria-v5


def _role_bound_hit_row(sample: dict | None, payload: dict,
                        graph: dict) -> dict:
    """ppv1-criteria-v5 逐题行(role_bound_product_hit;与 strict/v4 分列)。

    - 桶 = 评测器 ``sample['criteria_v5']['bucket']``(§2.2 五桶,互斥);
    - rank = 首个 v5 命中事件在**与 v4 同一条**预先固定候选序
      (``_candidate_events``:按 (created_at, event_id) 升序)中的
      位次;非命中一律 rank=None;
    - §5.1 披露 = 该 rank 事件(第一个满足 §1 的合法事件,不得事后
      挑事件)的 6 字段 + 该题全部合格事件最大产物种数;
    - §5.2 = 评测器的 C4*(按声明的非氢元素预算)单事件判定块:四状态、
      reason codes、逐元素 Dp/Dt/Dc 与余量、清单/计量完整度、独立
      执行覆盖(``not_verified``);只作披露,不改 hit/rank/bucket。
    """
    if not sample:
        return {"rank": None, "bucket": CRITERIA_V5_BUCKET_NO_EVENT,
                "role_bound_product_hit": False,
                "product_hit_partial": False,
                "role_bound_hit_events": [],
                "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
                "n_candidate_events": 0,
                "matched_event_not_in_candidates": False,
                "disclosure": None,
                "max_product_species_any_qualifying_event": None,
                "note": "评测器无该样本输出(失败题留分母)"}
    block = sample.get("criteria_v5") or {}
    bucket = str(block.get("bucket") or CRITERIA_V5_BUCKET_NO_EVENT)
    if bucket not in CRITERIA_V5_BUCKETS:
        bucket = CRITERIA_V5_BUCKET_NO_EVENT
    hit_events = sorted(str(x) for x in
                        (block.get("role_bound_hit_events") or []))
    root_states = _root_strict_states(sample, graph)
    candidates = _candidate_events(payload, root_states)
    rank = None
    chosen_event_id = None
    if bucket == CRITERIA_V5_BUCKET_MATCHED:
        hit_ids = set(hit_events)
        for position, candidate in enumerate(candidates, 1):
            if candidate["event_id"] in hit_ids:
                rank = position
                chosen_event_id = candidate["event_id"]
                break
    disclosure = None
    disclosure_event_id = None
    if chosen_event_id is not None:
        # 事件级披露行在**边判定块**里(criteria_v5.events);样本级块只
        # 有聚合字段。逐边扫,取首个同 event_id 的合格行。
        for edge in sample.get("predicted_edge_matches") or []:
            edge_block = edge.get("criteria_v5") or {}
            for row in edge_block.get("events") or []:
                if str(row.get("event_id")) == chosen_event_id and \
                        row.get("eligible"):
                    disclosure = {
                        key: row.get(key) for key in (
                            "event_id", "n_product_species_total",
                            "n_principal_species", "n_coproduct_species",
                            "n_other_role_species", "n_multirole_species",
                            "n_participant_entries",
                            "n_role_missing_entries",
                            "n_role_unknown_entries",
                            "role_missing_or_unknown_present",
                            "product_species_bucket",
                            "coproduct_traceability",
                            "coproduct_traceability_reason",
                            "c4star_budget")}
                    disclosure_event_id = chosen_event_id
                    break
            if disclosure is not None:
                break
    return {
        "rank": rank,
        "bucket": bucket,
        "role_bound_product_hit": bucket == CRITERIA_V5_BUCKET_MATCHED,
        "product_hit_partial": bucket == CRITERIA_V5_BUCKET_PARTIAL,
        "role_bound_hit_events": hit_events,
        "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
        "n_candidate_events": len(candidates),
        "matched_event_not_in_candidates": bool(
            bucket == CRITERIA_V5_BUCKET_MATCHED and hit_events
            and rank is None),
        "disclosure": disclosure,
        "disclosure_event_id": disclosure_event_id,
        "max_product_species_any_qualifying_event": block.get(
            "max_product_species_any_qualifying_event"),
    }


def _criteria_v5_species_bucket_label(n_species) -> str:
    """§5.1 ``product_species_bucket`` 分桶(判分层聚合用;同评测器口径)。"""
    if n_species is None:
        return "no_sample"
    try:
        n = int(n_species)
    except (TypeError, ValueError):
        return "unknown"
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 4:
        return "3-4"
    if n <= 8:
        return "5-8"
    return ">8"


def _role_bound_hit_caliber_block(rows: list[dict],
                                  denominator: int,
                                  *,
                                  domain_tag: str | None = None) -> dict:
    """批级 role_bound_product_hit 口径块(§2.2 五桶 + hit@K + §5 披露)。

    - 桶和 = 分母(fail-closed);0 ≤ hit@1 ≤ hit@3 ≤ hit@5 ≤ 命中题数
      (v5 单调性在**题内**由构造保证;跨 k 单调性在此断言);
    - §5.1 披露分布只对**命中题**的 rank 首事件聚合;无披露行的命中题
      单列 ``n_hit_without_disclosure``(不静默);
    - §5.2 C4*(按声明的非氢元素预算)只对**命中题**首事件聚合:四状态
      分布 + reason code 分布 + Dp/Dt/Dc 非零计数 + 可算账计数;
      ``traceable``/``untraceable`` 只是机器枚举,展示须写「按声明的
      非氢预算覆盖/超支」,不得裸称来源已核;
    - ``[biosysmodb121]`` 只作披露:``main_caliber_eligible=False``
      且带「仅披露」标记(预注册 §3 硬规则);298/dev 标记为
      ``pending_cc_signature``(本预注册不自动授主口径)。
    """
    counts = {bucket: 0 for bucket in CRITERIA_V5_BUCKETS}
    for row in rows:
        bucket = str(row.get("bucket") or CRITERIA_V5_BUCKET_NO_EVENT)
        if bucket not in counts:
            bucket = CRITERIA_V5_BUCKET_NO_EVENT
        counts[bucket] += 1
    if sum(counts.values()) != denominator:
        raise S5bScoringError(
            f"role_bound_product_hit 桶和 {sum(counts.values())} ≠ 分母 "
            f"{denominator}(fail-closed;斜杠桶不得重复计分母)", {
                "kind": "s5b_role_bound_product_hit_bucket_total_mismatch",
                "total": sum(counts.values()),
                "denominator": denominator})
    hits = {f"hit@{k}": sum(
        1 for row in rows if (row.get("rank") or math.inf) <= k)
        for k in (1, 3, 5)}
    matched = counts[CRITERIA_V5_BUCKET_MATCHED]
    if not (0 <= hits["hit@1"] <= hits["hit@3"] <= hits["hit@5"]
            <= matched):
        raise S5bScoringError(
            "role_bound_product_hit 聚合单调性断言失败"
            "(0≤hit@1≤hit@3≤hit@5≤命中题数;判分产物不落盘)", {
                "kind":
                    "s5b_role_bound_product_hit_monotonicity_violation",
                "hit@1": hits["hit@1"], "hit@3": hits["hit@3"],
                "hit@5": hits["hit@5"], "matched": matched,
                "denominator": denominator})
    attribution_errors = [
        row for row in rows
        if row.get("matched_event_not_in_candidates")]
    species_bucket_counts: dict[str, int] = {}
    traceability_counts: dict[str, int] = {}
    traceability_reason_counts: dict[str, int] = {}
    n_hit_with_disclosure = 0
    n_budget_computable = 0
    n_budget_not_computable = 0
    n_dp_positive = 0
    n_dt_positive = 0
    n_dc_positive = 0
    n_surplus_positive = 0
    max_species_distribution: dict[str, int] = {}
    for row in rows:
        disclosure = row.get("disclosure")
        if row.get("bucket") == CRITERIA_V5_BUCKET_MATCHED:
            if not disclosure:
                continue
            n_hit_with_disclosure += 1
            label = str(disclosure.get("product_species_bucket")
                        or "unknown")
            species_bucket_counts[label] = (
                species_bucket_counts.get(label, 0) + 1)
            trace = str(disclosure.get("coproduct_traceability")
                        or "unknown")
            traceability_counts[trace] = (
                traceability_counts.get(trace, 0) + 1)
            budget = disclosure.get("c4star_budget") or {}
            for code in (str(x) for x in budget.get("reason_codes") or []):
                for part in code.split(";"):
                    if part:
                        traceability_reason_counts[part] = (
                            traceability_reason_counts.get(part, 0) + 1)
            if budget:
                if budget.get("budget_account_computable"):
                    n_budget_computable += 1
                else:
                    n_budget_not_computable += 1
                n_dp_positive += int(bool(budget.get("dp_positive")))
                n_dt_positive += int(bool(budget.get("dt_positive")))
                n_dc_positive += int(bool(budget.get("dc_positive")))
                n_surplus_positive += int(bool(budget.get("surplus_positive")))
        max_label = _criteria_v5_species_bucket_label(
            row.get("max_product_species_any_qualifying_event"))
        max_species_distribution[max_label] = (
            max_species_distribution.get(max_label, 0) + 1)
    domain = str(domain_tag or "")
    if domain == "biosysmodb121":
        qualification = {
            "domain_tag": domain,
            "main_caliber_eligible": False,
            "disclosure_only": True,
            "disclosure_label": "[biosysmodb121·披露]",
            "note": ("预注册 §3:该域参考侧主/共产物标签自述不可区分"
                     "(417/417 principal_vs_coproduct_undistinguished)"
                     "⇒ v5 只作披露,不进主成绩、不与 298 并列、"
                     "不得对外汇报"),
        }
    else:
        qualification = {
            "domain_tag": domain,
            "main_caliber_eligible": False,
            "disclosure_only": False,
            "disclosure_label": "(pending CC signature)",
            "note": ("预注册 §3/§11:298 的 v5 主口径资格须 CC 签字 "
                     "+ T4c 零模型重放 + 翻转核对全部通过后另行拍板;"
                     "本块不自动授主口径"),
        }
    return {
        "criteria_version": PPV1_CRITERIA_V5,
        "metric_name": CRITERIA_V5_METRIC_NAME,
        "metric_name_discipline": CRITERIA_V5_METRIC_DISCIPLINE_NOTE,
        "hit_mode_scope": CRITERIA_V5_HIT_MODE_SCOPE,
        "preregistration_doc": PPV1_CRITERIA_V5_PREREG_DOC,
        **hits,
        **{f"{k}_rate": round(v / denominator, 4)
           for k, v in hits.items()},
        "role_bound_product_hit": matched,
        "product_hit_partial": counts[CRITERIA_V5_BUCKET_PARTIAL],
        "buckets": dict(sorted(counts.items())),
        "denominator": denominator,
        "rank_attribution_errors": len(attribution_errors),
        "disclosure_axis_5_1": {
            "scope": ("每题首个 v5 命中事件(固定候选序),不得事后挑"
                      "事件;只汇总命中题"),
            "n_hit_with_disclosure": n_hit_with_disclosure,
            "n_hit_without_disclosure": matched - n_hit_with_disclosure,
            "product_species_bucket": dict(
                sorted(species_bucket_counts.items())),
            "max_product_species_any_qualifying_event_bucket": dict(
                sorted(max_species_distribution.items())),
            "fields": [
                "n_product_species_total", "n_principal_species",
                "n_coproduct_species", "n_other_role_species",
                "n_participant_entries", "product_species_bucket"],
            "note": ("§5.1 只披露多报程度,不进命中、不改位次;"
                     "n_multirole_species 为对账辅助(同一身份多角色)"),
        },
        "disclosure_axis_5_2": {
            "status": "implemented_c4star",
            "rule_version": CRITERIA_V5_C4STAR_RULE_VERSION,
            "display_name": CRITERIA_V5_C4STAR_DISPLAY_NAME,
            "implemented_rules": ["c4star_declared_non_hydrogen_budget"],
            "allowed_outputs": list(
                CRITERIA_V5_COPRODUCT_TRACEABILITY_ALLOWED),
            "scope": ("只对 v5 命中题的首个命中事件(固定候选序)聚合;"
                      "四状态 + reason code + 缺口计数;不得外推为整个"
                      "题域的化学正确率"),
            "counts": dict(sorted(traceability_counts.items())),
            "reason_code_counts": dict(
                sorted(traceability_reason_counts.items())),
            "budget_account_computable": n_budget_computable,
            "budget_account_not_computable": n_budget_not_computable,
            "dp_positive": n_dp_positive,
            "dt_positive": n_dt_positive,
            "dc_positive": n_dc_positive,
            "surplus_positive": n_surplus_positive,
            "display_discipline_note": (
                "traceable/untraceable 只是兼容枚举;展示必须写明「按"
                "声明的非氢预算覆盖/超支」,不得裸称「来源已核」;正"
                "剩余不等于完整配平"),
            "scope_note": CRITERIA_V5_C4STAR_SCOPE_NOTE,
        },
        "domain_qualification": qualification,
        "definition": (
            "role_bound_product_hit(§1):存在同一个合法事件 E,底物"
            "严格身份 S ∈ R_E 且参考边声明的主产物身份集合 P ⊆ "
            "T_E^principal(事件产物侧 role 恰好 principal_product 的"
            "身份集合);role 缺失/其它 fail-closed 不进集合;合法事件"
            "五条件与 P 的定义逐字沿用 v4;禁止跨事件拼答案"),
        "separate_from_strict": True,
        "separate_from_v4": True,
        "comparability_note": (
            "本块与 main_caliber(v2 strict)及 matched_product_hit"
            "(v4 永久基线)分列;v4 数永不覆盖;禁止跨版本比较 strict "
            "数,禁止把 role_bound_product_hit 表述为 strict 或"
            "「反应预测正确率」"),
        "buckets_note": (
            "§2.2 五桶互斥;分母固定,失败/无效题不剔除;"
            "product_hit_partial 不记为命中;partial/unmatched 由 v5 "
            "重算,不继承 v4 的 2/140 定版数"),
        "product_hit_partial_bucket_rule": (
            "按预注册 §2.2 字面 trigger(多主产物题同一事件命中部分"
            "参考主产物,role 过滤后);v4 旧 coverage 轴归属另以 "
            "product_hit_partial_legacy_coverage_axis 并列披露"),
    }


def _old_caliber_row(sample: dict | None, payload: dict, graph: dict,
                     caliber: dict) -> dict:
    """老口径敏感性逐题行(官方整串 any-one;+ 多组分 any-of 另列)。

    L02 订正口径:候选序列 = 配对导出事件(§5.2 报告序)的报告投影
    产物展平成串;report_rank=None(宽度外)不进候选序列,计数披露;
    判定 = ``exam_v2.first_hit_rank``(整串 cn ∈ 金标 cn 集合,任一
    相等即中;不可解析占名次;重复身份跳过)。
    """
    from ..exam_v2 import first_hit_rank

    gold_ids: set[str] = set()
    root_node_ids = {str(x) for edge in graph.get("edges") or []
                     for x in (edge.get("from_node_ids") or [])}
    for node in graph.get("nodes") or []:
        if str(node.get("node_id")) not in root_node_ids:
            ident = cn_identity(str(node.get("structure_smiles")))
            if ident:
                gold_ids.add(ident)
    if not sample or str(sample.get("scoring_status")) != "scored":
        return {"rank": None, "anyof_rank": None,
                "n_candidates": 0, "gold_ids_empty": not gold_ids,
                "note": "not scored(失败/qid 缺配留分母)"}
    root_states = _root_strict_states(sample, graph)
    candidates: list[str] = []
    width_capped = 0
    state_smiles = _state_smiles_of(payload)
    for event in _candidate_events(payload, root_states):
        projection = _projection_of(payload, event["event_id"])
        ranks = [r for r in (projection.get("product_ranks") or [])
                 if isinstance(r, dict)
                 and r.get("report_rank") is not None]
        ranks.sort(key=lambda r: int(r["report_rank"]))
        for rank_entry in ranks:
            smiles = state_smiles.get(
                str(rank_entry.get("state_ref") or ""))
            if smiles:
                candidates.append(smiles)
        width_capped += sum(
            1 for r in (projection.get("product_ranks") or [])
            if isinstance(r, dict) and r.get("report_rank") is None)
    rank = first_hit_rank(candidates, gold_ids)
    anyof_rank = None
    if caliber.get("component_anyof_table"):
        anyof_rank = first_hit_rank(
            candidates, gold_ids, component_mode=True)
    return {
        "rank": rank,
        "anyof_rank": anyof_rank,
        "n_candidates": len(candidates),
        "width_capped_products": width_capped,
        "gold_ids_empty": not gold_ids,
    }


def _state_smiles_of(payload: dict) -> dict[str, str]:
    """导出 states 行 → {state_id: smiles_isomeric}。"""
    out: dict[str, str] = {}
    for row in payload.get("states") or []:
        body = row.get("payload")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                body = {}
        if isinstance(body, dict):
            out[str(row.get("state_id"))] = str(
                body.get("smiles_isomeric") or "")
    return out


def _projection_of(payload: dict, event_id: str) -> dict:
    for row in payload.get("report_projections") or []:
        if str(row.get("event_id")) == str(event_id):
            body = row.get("payload")
            if isinstance(body, str):
                try:
                    return json.loads(body)
                except (ValueError, TypeError):
                    return {}
            return body if isinstance(body, dict) else {}
    return {}


# ---------------------------------------------------------------- 桶与 CI


def _bucket_counts(per_qid: list[dict]) -> dict:
    """判分互斥桶(match_status;每题恰一桶,总和 = 分母;W0 闭合)。"""
    buckets: dict[str, int] = {}
    for row in per_qid:
        key = str(row["main"].get("match_status") or "unknown")
        buckets[key] = buckets.get(key, 0) + 1
    return dict(sorted(buckets.items()))


def _run_status_counts(per_qid: list[dict]) -> dict:
    """运行状态附表(每题恰一项,总和 = 分母;与判分桶分开,
    叠加桶不重复计分母)。"""
    table: dict[str, int] = {}
    for row in per_qid:
        status = str(row.get("run_status") or "no_case")
        table[status] = table.get(status, 0) + 1
    return dict(sorted(table.items()))


def _confidence_intervals(per_qid: list[dict], entries: dict,
                          denominator: int) -> dict:
    """CI:主口径 bootstrap 95% 按 source group(S1 一题一组)聚类
    重采样 + S2 按底物归并敏感性 + Wilson 95% 按题敏感性。

    如实披露(codex L02 #5):S1 是单题簇,related 标签不归并跨 qid
    ——S1 主 bootstrap 不消除跨题相关;S2 提供按底物归并的保守档。
    """
    hit_flags = [1 if (row["main"]["rank"] or math.inf) <= 3 else 0
                 for row in per_qid]
    out: dict = {}
    for k in (1, 3, 5):
        flags = [1 if (row["main"]["rank"] or math.inf) <= k else 0
                 for row in per_qid]
        out[f"hit@{k}"] = {
            "bootstrap_s1_by_source_group": _bootstrap_ci(flags),
            "bootstrap_s2_by_substrate": _bootstrap_ci(
                flags, groups=_substrate_groups(per_qid, entries)),
            "wilson_per_question": _wilson_ci(sum(flags), denominator),
        }
    out["disclosure"] = (
        "S1 一题一组(单题簇):主 bootstrap 不消除跨题相关(related "
        "标签不归并跨 qid;codex S5B-L02 #5 如实披露);S2 按底物归并"
        "为保守敏感性档;Wilson 按题为题级敏感性(预注册 §7)")
    return out


def _substrate_groups(per_qid: list[dict], entries: dict) -> list[int]:
    groups: dict[str, int] = {}
    ids: list[int] = []
    for row in per_qid:
        substrate = str(
            (entries.get(row["qid"]) or {}).get("substrate_smiles")
            or row["qid"])
        if substrate not in groups:
            groups[substrate] = len(groups)
        ids.append(groups[substrate])
    return ids


def _bootstrap_ci(flags: list[int], groups: list[int] | None = None,
                  iterations: int = _BOOTSTRAP_ITERS,
                  seed: int = _BOOTSTRAP_SEED) -> dict:
    """百分位 bootstrap 95%(按题或按聚类组重采样;固定种子可重放)。"""
    if not flags:
        return {"low": None, "high": None, "note": "零样本"}
    rng = random.Random(seed)
    n = len(flags)
    if groups is None:
        samples = []
        for _ in range(iterations):
            draws = [flags[rng.randrange(n)] for _ in range(n)]
            samples.append(sum(draws) / n)
    else:
        by_group: dict[int, list[int]] = {}
        for flag, group in zip(flags, groups):
            by_group.setdefault(group, []).append(flag)
        group_list = [v for v in by_group.values()]
        n_groups = len(group_list)
        samples = []
        for _ in range(iterations):
            total = 0
            count = 0
            for _ in range(n_groups):
                group = group_list[rng.randrange(n_groups)]
                total += sum(group)
                count += len(group)
            samples.append(total / count if count else 0.0)
    samples.sort()
    low = samples[int(0.025 * (iterations - 1))]
    high = samples[int(0.975 * (iterations - 1))]
    return {"low": round(low, 4), "high": round(high, 4),
            "iterations": iterations, "seed": seed}


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> dict:
    """Wilson 95% 区间(按题二项;预注册 §7 敏感性档)。"""
    if n <= 0:
        return {"low": None, "high": None}
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"low": round(max(0.0, center - margin), 4),
            "high": round(min(1.0, center + margin), 4)}


# ---------------------------------------------------------------- 报告


def render_report(aggregate: dict, evaluator_output: dict) -> str:
    """技术版报告(md;数字带题域标签 298,双口径并列)。"""
    main = aggregate["main_caliber"]
    old = aggregate["old_caliber_sensitivity"]
    anyof = aggregate["old_caliber_anyof_multicomponent"]
    lines: list[str] = []
    lines.append(f"# PPV1 S5b 判分报告(题域 {aggregate['domain_tag']})")
    lines.append("")
    lines.append(
        f"- 分母:固定 {aggregate['denominator']} 题(失败/unknown/"
        f"qid 缺配/预算漏展开/空候选全算未命中;不剔题)")
    lines.append(
        f"- 评测器状态:{aggregate['evaluator_output_status']}"
        "(程序只发 pending 族;最终状态由用户/teacher 裁定)")
    lines.append(
        f"- 数据口径:data_scope={aggregate['data_scope']};判分零 LLM;"
          "金标只在判分进程出现")
    lines.append("")
    lines.append("## 主口径(新,参考边召回 hit@K)")
    lines.append("")
    lines.append("| 档 | 命中 | 比例 | 通过线(参照锚) |")
    lines.append("|---|---|---|---|")
    for k in (1, 3, 5):
        lines.append(
            f"| hit@{k} | {main[f'hit@{k}']} | "
            f"{main[f'hit@{k}_rate']:.2%} | "
            f"≥ {S5B_PASS_LINES[f'hit@{k}']}(老口径首轮锚) |")
    lines.append("")
    lines.append(
        f"- 定义:{main['definition']}")
    lines.append(
        f"- 通过线语义:{main['pass_line_semantics']}")
    lines.append("")
    v4_caliber = aggregate.get("matched_product_hit_caliber")
    if v4_caliber:
        lines.append(
            "## matched_product_hit 口径(ppv1-criteria-v4;与上一节 "
            "strict 分列,不得同名/不得跨版本比较)")
        lines.append("")
        lines.append("| 档 | 计数 | 比例 |")
        lines.append("|---|---|---|")
        for k in (1, 3, 5):
            lines.append(
                f"| hit@{k} | {v4_caliber[f'hit@{k}']} | "
                f"{v4_caliber[f'hit@{k}_rate']:.2%} |")
        lines.append("")
        lines.append(
            f"- 命中(matched_product_hit):"
            f"{v4_caliber['matched_product_hit']}/"
            f"{aggregate['denominator']}")
        lines.append(
            "- 分桶(§3 五桶;互斥):" + "; ".join(
                f"{bucket}={count}" for bucket, count
                in v4_caliber["buckets"].items()))
        lines.append(f"- 定义:{v4_caliber['definition']}")
        lines.append(
            f"- 命名纪律:{v4_caliber['metric_name_discipline']}")
        lines.append(f"- {v4_caliber['comparability_note']}")
        lines.append("")
    lines.append("## 老口径敏感性表(与 116/128/130 历史锚同口径)")
    lines.append("")
    lines.append("| 档 | 命中 | 比例 |")
    lines.append("|---|---|---|")
    for k in (1, 3, 5):
        lines.append(
            f"| hit@{k} | {old[f'hit@{k}']} | "
            f"{old[f'hit@{k}_rate']:.2%} |")
    lines.append("")
    lines.append(f"- 定义:{old['definition']}")
    lines.append(
        "- 两口径数字差 = 口径差(不是系统性能差);差异方向按预注册"
        " §5.1 差异清单预披露(新口径系统性更严)")
    lines.append("")
    lines.append("## 多组分 any-of 敏感性(探索性另表)")
    lines.append("")
    lines.append(f"- hit@1/@3/@5 = "
                 f"{anyof['hit@1']}/{anyof['hit@3']}/{anyof['hit@5']}"
                 f"(题域 298;不与主表混算)")
    lines.append("")
    lines.append("## 分桶(失败/unknown/预算漏展开单列;判分互斥桶总=分母)")
    lines.append("")
    for bucket, count in aggregate["buckets"].items():
        lines.append(f"- {bucket}: {count}")
    lines.append("")
    lines.append("## 运行状态附表(总和=分母;与判分桶分开)")
    lines.append("")
    for status, count in (aggregate.get("run_status_table")
                          or {}).items():
        lines.append(f"- {status}: {count}")
    lines.append("")
    diagnosis = aggregate.get("aggregate_diagnosis") or {}
    if diagnosis:
        lines.append("## 聚合诊断 U/H5/L(W0;不改正式尺子)")
        lines.append("")
        lines.append(
            f"- U(strict 匹配题数) = {diagnosis.get('U_strict_matched_questions')};"
            f"H5 = {diagnosis.get('H5')};L = U−H5 = "
            f"{diagnosis.get('L_below_k')}")
        lines.append(
            "- U<150 ⇒ 优先供给/生成;U≥150 而 H5<150 ⇒ 主攻排序"
            "(诊断只选通用问题方向,不向预测侧回传逐题目标)")
        lines.append("")
    ci = aggregate.get("confidence_intervals") or {}
    lines.append("## 置信区间(95%)")
    lines.append("")
    for k in ("hit@1", "hit@3", "hit@5"):
        block = ci.get(k) or {}
        lines.append(
            f"- {k}:S1 bootstrap "
            f"[{block.get('bootstrap_s1_by_source_group', {}).get('low')}"
            f", "
            f"{block.get('bootstrap_s1_by_source_group', {}).get('high')}]"
            f";S2 按底物 "
            f"[{block.get('bootstrap_s2_by_substrate', {}).get('low')}"
            f", "
            f"{block.get('bootstrap_s2_by_substrate', {}).get('high')}]"
            f";Wilson 按题 "
            f"[{block.get('wilson_per_question', {}).get('low')}, "
            f"{block.get('wilson_per_question', {}).get('high')}]")
    if ci.get("disclosure"):
        lines.append(f"- {ci['disclosure']}")
    lines.append("")
    lines.append("## 结论句式(冻结,预注册 §1)")
    lines.append("")
    lines.append(
        "> 在已见 298 题、冻结配置下的已知证据重建成绩(题域 298,"
        "RHEA 通用酶学;dev 题域结果不外推、不混报)。主口径与老口径"
        "并列报告;通过线锚是老口径历史数字,主口径达到同数字的难度"
        "高于老系统(预注册 §5.3 语义限定)。")
    lines.append("")
    lines.append(
        "- key_intermediate_recall 本题域恒空不可评(298 卷无 "
        "intermediate 节点;不得把空桶读成已测得 0)")
    lines.append(
        "- 评审后置声明:出题后结果化学复核(AGENTS 三触发点之 3)"
        "未在本报告内执行;mimo 评审独立性不做背书")
    lines.append("")
    return "\n".join(lines)


def render_plain_report(aggregate: dict) -> str:
    """大白话版报告(结论先行;数字带题域标签 298)。"""
    main = aggregate["main_caliber"]
    old = aggregate["old_caliber_sensitivity"]
    denom = aggregate["denominator"]
    lines = [
        "# S5b 跑分结果(大白话版)",
        "",
        f"一句话:298 道题(题域 298,微生物酶促污染物转化),"
        f"新口径答对 {main['hit@1']}/{denom}(hit@1),"
        f"{main['hit@3']}/{denom}(hit@3),"
        f"{main['hit@5']}/{denom}(hit@5);",
        f"和老公式对齐的算法(可比老系统 116/128/130 那条线)是 "
        f"{old['hit@1']}/{old['hit@3']}/{old['hit@5']}。",
        "",
        "解释两句:",
        "- 新口径更严:要求整条反应(两边都对上)才算对;"
        "老公式只看产物列表里有没有一个对上。",
        "- 两个数字是两把尺子,不能直接比高低;"
        "差多少是尺子差,不是系统差。",
        "",
        f"分母规矩:{denom} 题一题不剔——模型没答、超时、崩了的题"
        "都算没答对,单独列在分桶表里,不藏。",
        "",
        "这批数字只在题域 298 里说话,不代表 dev 题域,"
        "也不外推到别的题。",
        "",
    ]
    buckets = aggregate.get("buckets") or {}
    if buckets:
        lines.append("分桶速览(每类多少题):")
        for bucket, count in buckets.items():
            lines.append(f"- {bucket}:{count} 题")
        lines.append("")
    v4_caliber = aggregate.get("matched_product_hit_caliber")
    if v4_caliber:
        lines.append(
            "另有 ppv1-criteria-v4 的 matched_product_hit 尺子"
            "(只看主产物身份是否在同一个事件里命中,不是 strict):")
        lines.append(
            f"- 命中 {v4_caliber['matched_product_hit']}/{denom} 题;"
            f"hit@1/3/5 = {v4_caliber['hit@1']}/{v4_caliber['hit@3']}/"
            f"{v4_caliber['hit@5']}")
        lines.append(
            "- 两把尺子分列报告,不能跨版本比 strict 数;"
            "本数字也不等于「反应预测正确率」。")
        lines.append("")
    lines.append(
        "通过线(≥116/128/130)是老系统的历史线,只是参照锚;"
        "是否算\"达到\",要用户/老师按两把尺子分别裁定,程序不代定。")
    return "\n".join(lines)
