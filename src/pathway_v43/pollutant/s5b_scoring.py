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
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from ..domain.identity import cn_identity
from .evaluation import (
    PPV1_EVALUATION_VERSION,
    evaluate_scientific,
    native_export_reader_from_ledger,
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

    缺省路径 = 本仓 docs/ 冻结稿(Chenyu worktree 同仓部署时在位);
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
) -> dict:
    """判分主入口:逐 qid evaluate_scientific → 双口径聚合 → 报告落盘。

    - data_scope=real(正式)⇒ 预注册批准记录必给(批根
      ``preregistration_approval.json`` 或参数;approval_status=
      approved)——评测器既有门(real ∧ 未批准 ⇒ 拒);
    - 失败题(无导出)不进 native_path_exports ⇒ 评测器按 qid 缺配
      not_evaluated(留分母算未命中);
    - 返回完整聚合 dict;metrics.json / report.md / report_plain.md
      落批根。
    """
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
        preregistration=normalize_preregistration(prereg))
    # ---- W-V6.1(mimo r27 判断面一附条件;§9-④ 程序门,随 v3 交付
    # 工程落地):评分聚合前落程序检查 —— data_scope=real ∧ 任一
    # pairing basis 非 qid_strict ⇒ S5bScoringError(结构化、机器可读
    # detail)。与 evaluation-5 代码守卫(评测器内 real 首消费拒
    # root_identity_fallback)双保险:本门在**判分入口**独立复核
    # 评测器产出的 bases_by_graph,不依赖评测器内部异常路径;真实批
    # 判分聚合/落盘前 fail-closed。synthetic 档不受影响(合成回退
    # basis 聚合照旧)。 ----
    if data_scope == "real":
        bases = dict((((output or {}).get("coverage_report") or {})
                      .get("pairing") or {}).get("bases_by_graph") or {})
        non_strict = {g: str(b) for g, b in sorted(bases.items())
                      if str(b) != "qid_strict"}
        if non_strict:
            raise S5bScoringError(
                "data_scope=real 而存在非 qid_strict 的配对 basis(§9-4 "
                "程序门:真实批须全 qid_strict;判分入口独立复核,先于"
                "聚合/落盘;与 evaluation-5 首消费守卫双保险)", {
                    "kind": "s5b_real_pairing_not_all_qid_strict",
                    "data_scope": data_scope,
                    "non_qid_strict_bases": non_strict,
                    "n_graphs": len(bases),
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
    lines.append(
        "通过线(≥116/128/130)是老系统的历史线,只是参照锚;"
        "是否算\"达到\",要用户/老师按两把尺子分别裁定,程序不代定。")
    return "\n".join(lines)
