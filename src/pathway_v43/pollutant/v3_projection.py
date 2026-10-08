"""S4b v3 有损投影适配 —— native result → v3 形态的显式 lossy 视图
(契约 ppv1-v3-projection-1 登记;legacy export_v3.py 冻结零触碰)。

任务书 §2.C:旧 v3 适配必须是**显式有损投影**,本模块逐条落实:

- 载荷顶层 ``lossy_projection: true`` 恒置(读取侧校验该标记,
  篡改 ⇒ 拒);
- ``native_reference``:原生正式导出引用(export_digest / 原生
  content_digest / 原生结果 artifact task_key)—— 投影永远可回溯
  原生权威;
- ``information_losses``:结构化信息损失清单(来路/共同产物/备选
  /条件依赖/audit+proof scope/deferred 与未展开集合/endpoint 证据
  等级/预算停止原因/unknown 与 partial 具体轴/系数/路径身份/
  来源 provenance),逐项带 native_authority 指回原生字段组;
- ``unprojectable_summaries``:不可投影字段的摘要或引用(计数/键
  清单/状态值,不展开全文);
- ``adapter_version`` / 原生图修订与来源 identity(native_graph_
  revision:graph facts digest 聚合 + 契约版本);
- **不把 v3 报告位置约束反向写成 PPV1 事件事实;不把 v3 的单一
  路径/旧报告字段解释为原生完整语义**:步骤只携带 v3 冻结字段
  (parent_smiles/predicted_products),每步 = 一个已提交事件(不按
  CN 合并同父 —— 同父多事件保留为多步,但事件/假设身份不进 v3
  字段,列为损失);本模块**没有**任何投影 → 原生事实/事件/状态
  的转换入口,反向消费在契约上禁止(boundary.reverse_consumption=
  forbidden);投影与原生结果**不得计为两条路径**(F03);
- 不为填满旧字段编造终点/矿化/解毒/来源支持:endpoint/账目/证据
  全部留在 unprojectable_summaries(原生权威),v3 steps 只是结构
  投影。

确定性:载荷无时间戳、canonical 键序、事件按 event_id 稳定排序
⇒ 同事实+同版本 ⇒ 同 projection_digest、同字节(幂等落盘;事实
变化 = 新 digest = 新目录,旧投影保全)。

双向引用边界:

- 正向(native → v3):投影引用原生导出 digest;读取时核对原生
  导出 manifest 文件存在(断裂 ⇒ v3_native_reference_missing 拒);
- 反向(v3 → native 发现,不反写):``list_v3_projections_for_
  native`` 从投影目录按 native 引用反查(**读文件,不改原生**);
  原生 manifest 不内嵌投影清单(原生不可变,投影可后生成)。

**S4-C04 回修(确认复核 §4;契约 ppv1-v3-projection-2)—— 构建
与首消费验证真实原生来源**:

- 构建侧(``build_v3_projection``)不再裸信调用方传入的 native_
  result/native_export:**先经 read_native_export 首消费**核验该
  导出(ledger 权威/manifest/payload/引用/策略/事实),并要求
  传入的 native_result 与该导出的 payload 同一(canonical 字节
  同源)、run/内容 digest/导出摘要绑定一致 —— 假 native(删
  events/deferred 后自洽重算 digest)配真 export 引用 ⇒ 拒;
- 读取侧(``read_v3_projection``,可选传 ledger 走完整原生首消费)
  不只核投影自 hash/版本/lossy 标记/原生 manifest 文件存在:
  ① native_reference 与真实 manifest 的内部一致(export digest/
  content digest/task_key/payload sha/graph revision aggregate/
  run_id 两两绑定);② 投影已表达字段(route.steps/root_smiles/
  unprojectable_summaries/information_losses/run_id)**由该原生
  payload 按登记 adapter 同源复算比对** —— projection-only 自洽
  改内容(重算 projection_digest 换新目录)配真 reference ⇒ 拒;
  已验证原生存在/投影自 hash 不是投影证书。

读取失败结构化拒(kind):``v3_projection_missing`` /
``v3_projection_corrupt``(不可解析/标记篡改) /
``v3_projection_version_unknown`` / ``v3_projection_digest_mismatch``
/ ``v3_native_reference_missing`` / ``v3_projection_source_binding_
mismatch``(S4-C04:来源绑定/同源复算不符)。零写入,原文件保全。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..domain.models import canonical_json, content_hash
from .native_export import (
    NATIVE_EXPORT_MANIFEST_FILE,
    NATIVE_EXPORT_PAYLOAD_FILE,
    NATIVE_EXPORT_SUBDIR,
    graph_facts_digests,
    read_native_export,
)
from .native_result import NATIVE_RESULT_TASK_KEY
from .profile import (
    PPV1_ENDPOINT_POLICY_VERSION,
    PPV1_ENDPOINT_SCHEMA_VERSION,
    PPV1_NATIVE_RESULT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    PPV1_RUNFLOW_SCHEMA_VERSION,
    PPV1_SEARCH_SCHEMA_VERSION,
    PPV1_V3_PROJECTION_VERSION,
)

V3_PROJECTION_SUBDIR = "v3_projection"
V3_PROJECTION_FILE = "projection.json"
V3_REVERSE_CONSUMPTION = "forbidden"


class V3ProjectionContractError(RuntimeError):
    """v3 有损投影契约违反(结构化 fail-closed;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 损失清单

_INFORMATION_LOSSES = (
    {
        "axis": "route_origins",
        "detail": ("v3 步骤不携带来路/parent/context/事件身份;同 CN "
                   "不同来路在 v3 字段层不可区分(本适配不按 CN 合并,"
                   "同父多事件保留为多步,但链接身份丢失)"),
        "native_authority": "native payload: events/state_appearances/paths",
    },
    {
        "axis": "coproducts",
        "detail": ("共同产物与主产物混入同一无差别产物列表;产物角色/"
                   "位次语义不进 v3 字段"),
        "native_authority": "native payload: events.participants[].role",
    },
    {
        "axis": "alternative_reactions",
        "detail": "同父备选反应关系(各自独立假设/事件)在 v3 形态不可表达",
        "native_authority": "native payload: alternatives",
    },
    {
        "axis": "conditions_dependencies",
        "detail": "条件/环境事实与依赖(含未解决依赖)不在 v3 字段",
        "native_authority": "native payload: contexts/endpoint_record",
    },
    {
        "axis": "audit_proof_scope",
        "detail": "audit 结论/准入/证明范围与失败原因不进 v3 字段",
        "native_authority": "native payload: audit_production_reports",
    },
    {
        "axis": "deferred_unexpanded",
        "detail": "deferred(两类)与 blocked/未展开集合不在 v3 字段",
        "native_authority": "native payload: deferred_entries/blocked_entries",
    },
    {
        "axis": "endpoint_evidence_level",
        "detail": ("endpoint 分账(四分账/证据等级/独立支持计数)不可投影;"
                   "v3 步骤不得解释为矿化/去除/解毒结论"),
        "native_authority": "native payload: endpoint_record",
    },
    {
        "axis": "budget_stop_reason",
        "detail": "预算预约/消耗与搜索停止原因不进 v3 字段",
        "native_authority": "native payload: budget/stop 记录",
    },
    {
        "axis": "unknown_partial_axes",
        "detail": "unknown/partial 的具体轴(系数未知/条件未知/依赖未决)丢失",
        "native_authority": "native payload: endpoint_record.bookkeeping",
    },
    {
        "axis": "coefficients",
        "detail": "参与物系数/系数状态(账目闭合)不在 v3 字段",
        "native_authority": "native payload: events.participants[].coefficient",
    },
    {
        "axis": "path_identity",
        "detail": "根/子路径身份与深度结构在 v3 单路线形态不可表达",
        "native_authority": "native payload: paths",
    },
    {
        "axis": "source_provenance",
        "detail": "来源引用/provenance 记录不进 v3 字段",
        "native_authority": "native payload: provenance_records",
    },
)


def _state_smiles_map(native_result: dict) -> dict[str, str]:
    """state_id → smiles_isomeric(严格结构串;不猜、不中和电荷)。"""
    out: dict[str, str] = {}
    for row in native_result.get("states") or []:
        payload = row.get("payload")
        payload = (json.loads(payload) if isinstance(payload, str)
                   else payload) or {}
        state_id = str(row.get("state_id") or "")
        smiles = str(payload.get("smiles_isomeric") or "")
        if state_id and smiles:
            out[state_id] = smiles
    return out


def _root_smiles(run_dir: Path) -> str:
    """root_smiles = run_identity 的真实原始输入(与冻结 v3 导出同
    规则;不用 path_id/显示名/cn 冒充)。缺身份文件 ⇒ 结构化拒。"""
    identity_path = run_dir / "run_identity.json"
    if not identity_path.is_file():
        raise V3ProjectionContractError(
            f"run_identity.json 缺失:{run_dir}(投影需要真实原始输入;"
            "不猜默认)",
            {"kind": "v3_identity_missing", "path": str(identity_path)})
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    root_smiles = str((identity.get("inputs") or {}).get("root_smiles")
                      or "")
    if not root_smiles:
        raise V3ProjectionContractError(
            "run_identity 缺 inputs.root_smiles(不猜默认)",
            {"kind": "v3_identity_missing", "path": str(identity_path)})
    return root_smiles


def _route_steps(native_result: dict,
                 state_smiles: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """v3 步骤投影(每步 = 一个已提交事件,按 event_id 稳定排序)。

    - parent_smiles = 事件的 reactant 侧参与物结构(首个;多 reactant
      ⇒ 动态损失条目披露);
    - predicted_products = product 侧参与物结构(事件内顺序,含共同
      产物 —— 角色丢失已在固定损失清单列示);
    - state 缺失 ⇒ 结构化拒(不猜结构、不删边);
    - 不按 CN 合并同父(合并会伪造单一反应;同父多事件 = 多步)。
    """
    steps: list[dict] = []
    dynamic_losses: list[dict] = []
    for event in native_result.get("events") or []:
        payload = event.get("payload")
        payload = (json.loads(payload) if isinstance(payload, str)
                   else payload) or {}
        participants = payload.get("participants") or []
        event_id = str(event.get("event_id") or "")
        reactants = [p for p in participants
                     if isinstance(p, dict) and p.get("side") == "reactant"]
        products = [p for p in participants
                    if isinstance(p, dict) and p.get("side") == "product"]
        if not reactants:
            raise V3ProjectionContractError(
                f"事件 {event_id} 无 reactant 侧参与物(无法投影 "
                "parent_smiles;不猜结构)",
                {"kind": "v3_projection_event_structure_invalid",
                 "event_id": event_id})
        parent_ref = str(reactants[0].get("state_ref") or "")
        parent_smiles = state_smiles.get(parent_ref)
        if parent_smiles is None:
            raise V3ProjectionContractError(
                f"事件 {event_id} 的底物状态 {parent_ref} 不在原生载荷"
                "(投影不猜结构、不删边)",
                {"kind": "v3_projection_state_missing",
                 "event_id": event_id, "state_ref": parent_ref})
        if len(reactants) > 1:
            dynamic_losses.append({
                "axis": "multi_reactant_events_collapse",
                "detail": (f"事件 {event_id} 有 {len(reactants)} 个 "
                           "reactant 侧参与物;v3 parent_smiles 只取首个"
                           "(其余在原生载荷)"),
                "native_authority": f"native payload: events[{event_id}]",
            })
        predicted_products: list[str] = []
        for p in products:
            state_ref = str(p.get("state_ref") or "")
            smiles = state_smiles.get(state_ref)
            if smiles is None:
                raise V3ProjectionContractError(
                    f"事件 {event_id} 的产物状态 {state_ref} 不在原生载荷"
                    "(投影不猜结构、不删边)",
                    {"kind": "v3_projection_state_missing",
                     "event_id": event_id, "state_ref": state_ref})
            predicted_products.append(smiles)
        steps.append({
            "parent_smiles": parent_smiles,
            "predicted_products": predicted_products,
        })
    return steps, dynamic_losses


def _verify_native_source_binding(ledger, native_result: dict,
                                  native_export: dict,
                                  run_dir: Path) -> dict:
    """S4-C04 构建侧源绑定:投影输入必须是**当前 run 已验证的原生
    结果与其正式导出**(已验证原生存在不是裸对象的证书)。

    - native_result 自身内容 digest 复算(裸对象不是权威);
    - native_result.run_id 与 ledger 绑定;
    - native_export 的 export_digest 经 ``read_native_export`` 完整
      首消费(manifest/payload/权威引用/策略/事实 digest 全核;
      endpoint 首消费先行)—— 与读取侧共用同一原生消费/绑定源;
    - 该导出的 manifest.content_digest/payload 必须与传入的
      native_result 同一(整对象比对):假 native(删 events/
      deferred 后自洽重算 digest)配真 export 引用 ⇒ 拒;
    - 调用方给的 payload_sha256(如有)与 manifest 一致。
    """
    content_digest = str(native_result.get("content_digest") or "")
    if not content_digest or content_hash(
            {k: v for k, v in native_result.items()
             if k != "content_digest"}) != content_digest:
        raise V3ProjectionContractError(
            "投影输入的 native_result 内容 digest 复算不一致(裸对象"
            "不是权威;构建消费已验证原生来源,不猜不补)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "native_result_content_digest"})
    if str(native_result.get("run_id") or "") != str(ledger.run_id):
        raise V3ProjectionContractError(
            "投影输入的 native_result 与当前 run 不符(run 绑定;"
            "跨 run 混搭不投影)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "native_result_run_binding",
             "native_result_run_id": str(native_result.get("run_id") or ""),
             "ledger_run_id": str(ledger.run_id)})
    export_digest = str((native_export or {}).get("export_digest") or "")
    if not export_digest:
        raise V3ProjectionContractError(
            "投影输入缺 native_export.export_digest(原生引用锚;"
            "不猜默认)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "native_export_digest_missing"})
    verified = read_native_export(ledger, run_dir, export_digest)
    manifest = verified["manifest"]
    if str(manifest.get("content_digest")) != content_digest:
        raise V3ProjectionContractError(
            "投影输入的 native_result 与其引用的导出 content_digest"
            " 不一致(混搭真 export 引用 + 假 native;拒)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "export_content_digest_binding",
             "native_result_content_digest": content_digest,
             "manifest_content_digest":
                 str(manifest.get("content_digest") or "")})
    declared_sha = str((native_export or {}).get("payload_sha256") or "")
    if declared_sha and declared_sha != str(manifest.get("payload_sha256")):
        raise V3ProjectionContractError(
            "投影输入的 native_export.payload_sha256 与导出 manifest"
            " 不符(引用锚不一致;拒)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "export_payload_sha_binding",
             "declared": declared_sha[:12],
             "manifest": str(manifest.get("payload_sha256"))[:12]})
    if verified["payload"] != native_result:
        raise V3ProjectionContractError(
            "投影输入的 native_result 不是该导出的原生载荷(整对象"
            "比对不符;假 native 不能配真 export 引用)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "native_payload_identity",
             "export_digest": export_digest})
    return verified


# ---------------------------------------------------------------- 构建


def _derived_projection_content(native_result: dict,
                                run_dir: Path) -> dict:
    """登记 adapter 的同源派生内容(S4-C04 单一来源):构建写入与
    读取复算共用 —— 步骤/动态损失/信息损失清单/不可投影摘要/
    root_smiles/run_id 全部由**该原生载荷**确定性派生,不各算一套。"""
    steps, dynamic_losses = _route_steps(
        native_result, _state_smiles_map(native_result))
    losses = list(_INFORMATION_LOSSES) + dynamic_losses
    if not steps:
        losses.append({
            "axis": "no_committed_events_empty_answer",
            "detail": ("无已提交事件 ⇒ v3 答卷为空步骤(root_smiles 仍为"
                       "真实输入;空答卷不是终点/去除结论)"),
            "native_authority": "native payload: events",
        })
    return {
        "run_id": str(native_result.get("run_id") or ""),
        "route_steps": steps,
        "root_smiles": _root_smiles(run_dir),
        "information_losses": losses,
        "unprojectable_summaries": _unprojectable_summaries(
            native_result, native_result.get("endpoint_record") or {}),
    }


def build_v3_projection(ledger, native_result: dict, *,
                        native_export: dict,
                        run_dir: str | Path) -> dict:
    """native result → v3 有损投影载荷(确定性;纯派生零写入)。

    native_export = export_native_result 的返回(原生引用锚);
    native_result 必须是 build_native_result 的产物(其 endpoint 记录
    已通过首消费 —— 过期记录不投影成"正式结果")。

    S4-C04:构建先经 ``_verify_native_source_binding`` 验证真实原生
    来源(传入对象 = 当前 run 已验证导出的原生载荷),假 native +
    真 export 引用不再照收。
    """
    run_dir = Path(run_dir)
    _verify_native_source_binding(
        ledger, native_result, native_export, run_dir)
    content_digest = str(native_result["content_digest"])
    derived = _derived_projection_content(native_result, run_dir)
    graph_facts = graph_facts_digests(ledger)
    payload = {
        "schema_version": PPV1_V3_PROJECTION_VERSION,
        "lossy_projection": True,
        "adapter_version": PPV1_V3_PROJECTION_VERSION,
        "run_id": ledger.run_id,
        "native_reference": {
            "native_export_digest": str(native_export["export_digest"]),
            "native_result_content_digest": content_digest,
            "native_result_task_key": f"{NATIVE_RESULT_TASK_KEY}:"
                                      f"{content_digest[:24]}",
            "native_export_payload_sha256":
                str(native_export.get("payload_sha256") or ""),
        },
        "native_graph_revision": {
            "aggregate_digest": content_hash(graph_facts),
            "basis": ("graph_facts_digests(与 native_export manifest 同源"
                      "单一函数;PPV1 graph revision 等价身份)"),
            "contract_versions": {
                "profile": PPV1_PROFILE_SCHEMA_VERSION,
                "runflow": PPV1_RUNFLOW_SCHEMA_VERSION,
                "search": PPV1_SEARCH_SCHEMA_VERSION,
                "endpoint": PPV1_ENDPOINT_SCHEMA_VERSION,
                "endpoint_policy": PPV1_ENDPOINT_POLICY_VERSION,
                "native_result": PPV1_NATIVE_RESULT_VERSION,
            },
        },
        "route": {
            "route_id": ledger.run_id,
            "root_smiles": derived["root_smiles"],
            "steps": derived["route_steps"],
        },
        "information_losses": derived["information_losses"],
        "unprojectable_summaries": derived["unprojectable_summaries"],
        "boundary": {
            "reverse_consumption": V3_REVERSE_CONSUMPTION,
            "not_counted_as_extra_path": True,
            "notes": (
                "本投影是 native result 的有损视图:不得反写原生事实/"
                "事件/状态;不得从 v3 步骤位置推导事件身份或终点结论;"
                "投影与原生结果不得计为两条路径(F03);矿化/去除/解毒"
                "结论只能来自原生 endpoint 分账(证据等级权威)"),
        },
    }
    payload["projection_digest"] = content_hash(
        {k: v for k, v in payload.items() if k != "projection_digest"})
    return payload


def _unprojectable_summaries(native_result: dict,
                             endpoint_record: dict) -> dict:
    """不可投影字段的摘要或引用(计数/键清单/状态值;不展开全文,
    全文在 native_reference 指向的原生载荷)。"""
    deferred = native_result.get("deferred_entries") or []
    blocked = native_result.get("blocked_entries") or []
    alternatives = native_result.get("alternatives") or []
    coproducts = native_result.get("coproducts") or []
    bookkeeping = endpoint_record.get("bookkeeping") or {}
    evidence_summary = endpoint_record.get("evidence_summary") or {}
    conditions = endpoint_record.get("conditions_snapshot") or {}
    route_conditions = endpoint_record.get("route_condition_assessment") or {}
    stop = (endpoint_record.get("search_stop_reason") or {})
    inherited = endpoint_record.get(
        "inherited_unresolved_dependencies") or []
    return {
        "endpoint_assessment": endpoint_record.get(
            "chemical_endpoint_assessment"),
        "execution_status": endpoint_record.get("execution_status"),
        "bookkeeping_status": endpoint_record.get("bookkeeping_status"),
        "root_carbon_fate_status": bookkeeping.get("root_carbon_fate_status"),
        "co2_product_occurrences": len(
            bookkeeping.get("co2_product_occurrences") or []),
        "co2_aggregated": bookkeeping.get("co2_aggregated"),
        "independent_source_support_count": evidence_summary.get(
            "independent_source_support_count"),
        "inherited_unresolved_dependency_ids": sorted(
            str(d.get("dependency_id") or "") for d in inherited),
        "necessary_condition_unknown_keys": list(
            route_conditions.get("necessary_condition_unknown_keys")
            or []),
        "necessary_condition_conflict_keys": list(
            route_conditions.get("necessary_condition_conflict_keys")
            or []),
        "stop_reason_primary": stop.get("primary"),
        "stop_other_reasons": list(stop.get("other_reasons") or []),
        "unexplored_counts": {
            k: v for k, v in (stop.get("unexplored") or {}).items()
            if isinstance(v, int)},
        "deferred_entry_count": len(deferred),
        "deferred_types": sorted({
            str(d.get("deferred_type") or "") for d in deferred}),
        "blocked_entry_count": len(blocked),
        "alternative_group_count": len(alternatives),
        "coproduct_event_count": len(coproducts),
        "condition_keys_known": list(
            conditions.get("condition_keys_known") or []),
        "condition_keys_unknown": list(
            conditions.get("condition_keys_unknown") or []),
        "audit_report_count": len(
            native_result.get("audit_production_reports") or []),
        "provenance_record_count": len(
            native_result.get("provenance_records") or []),
        "note": ("全部值为摘要/计数;不可投影字段全文在原生导出"
                 "(native_reference);不得据本摘要下化学结论"),
    }


# ---------------------------------------------------------------- 落盘/读取


_SEQ = [0]


def _write_immutable(path: Path, data: bytes) -> bool:
    if path.exists():
        if path.read_bytes() == data:
            return False
        raise V3ProjectionContractError(
            f"投影文件已存在且内容不同(不可变;保全原文件不覆盖):"
            f"{path}",
            {"kind": "v3_projection_conflict", "path": str(path)})
    _SEQ[0] += 1
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{_SEQ[0]}.tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return True


def persist_v3_projection(run_dir: str | Path, payload: dict) -> dict:
    """投影落盘(确定性幂等;事实变化 = 新 digest 新目录,旧文件保全)。"""
    run_dir = Path(run_dir)
    digest = str(payload["projection_digest"])
    out_dir = run_dir / V3_PROJECTION_SUBDIR / digest[:24]
    text = canonical_json(payload) + "\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / V3_PROJECTION_FILE
    created = _write_immutable(path, text.encode("utf-8"))
    return {
        "projection_digest": digest,
        "dir": str(out_dir),
        "path": str(path),
        "schema_version": PPV1_V3_PROJECTION_VERSION,
        "created": created,
        "note": ("v3 有损投影(lossy_projection);读取/消费走 "
                 "read_v3_projection;反向消费禁止"),
    }


def _load_projection(run_dir: Path, projection_digest: str) -> dict:
    path = (run_dir / V3_PROJECTION_SUBDIR
            / str(projection_digest)[:24] / V3_PROJECTION_FILE)
    if not path.is_file():
        raise V3ProjectionContractError(
            f"投影文件缺失:{path}(按 digest 显式消费,不猜默认)",
            {"kind": "v3_projection_missing", "path": str(path),
             "projection_digest": str(projection_digest)})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise V3ProjectionContractError(
            f"投影不可反序列化:{path}(保全原文件)",
            {"kind": "v3_projection_corrupt", "path": str(path),
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if str(payload.get("projection_digest") or "") != str(projection_digest):
        raise V3ProjectionContractError(
            "投影 digest 与请求不符(路径/内容身份断裂;保全原文件)",
            {"kind": "v3_projection_digest_mismatch",
             "requested": str(projection_digest),
             "payload": str(payload.get("projection_digest") or "")})
    if str(payload.get("schema_version") or "") != PPV1_V3_PROJECTION_VERSION:
        raise V3ProjectionContractError(
            f"投影 schema 版本未知:{payload.get('schema_version')!r}"
            f"(当前 {PPV1_V3_PROJECTION_VERSION};fail-closed 不猜迁移)",
            {"kind": "v3_projection_version_unknown",
             "schema_version": str(payload.get("schema_version") or "")})
    if payload.get("lossy_projection") is not True:
        raise V3ProjectionContractError(
            "投影缺 lossy_projection=true 标记(有损标记被篡改/缺失 ⇒ "
            "拒;不得冒充无损 v3 结果)",
            {"kind": "v3_projection_corrupt",
             "lossy_projection": payload.get("lossy_projection")})
    return payload


def read_v3_projection(run_dir: str | Path, projection_digest: str, *,
                       ledger=None) -> dict:
    """投影读取(首消费:integrity → 版本门 → lossy 标记 → 原生引用
    绑定 + 同源复算;零写入)。

    S4-C04:已验证原生存在/投影自 hash不是投影证书 —— 读取核:

    - ledger 传入时先走 ``read_native_export`` 完整原生首消费
      (权威引用/策略/事实 digest;与构建侧共用同一绑定源);
    - native_reference 与真实原生导出 manifest 的内部一致(export
      digest/core digest 复算/payload sha/content digest/task_key/
      graph revision aggregate/run_id 两两绑定);
    - 投影已表达字段(route.steps/root_smiles/unprojectable_
      summaries/information_losses/run_id)由该原生 payload 按登记
      adapter(``_derived_projection_content`` 单一来源)同源复算比对
      —— projection-only 自洽改内容 + 真 reference ⇒ 拒。
    """
    run_dir = Path(run_dir)
    payload = _load_projection(run_dir, projection_digest)
    recomputed = content_hash(
        {k: v for k, v in payload.items() if k != "projection_digest"})
    if recomputed != str(payload.get("projection_digest")):
        raise V3ProjectionContractError(
            "投影内容 digest 复算不一致(完整性失败;保全原文件,不以"
            "重算新 ID 洗白)",
            {"kind": "v3_projection_digest_mismatch",
             "path": str(run_dir / V3_PROJECTION_SUBDIR
                         / str(projection_digest)[:24]
                         / V3_PROJECTION_FILE)})
    # ---- S4-C04:原生来源绑定(先可传 ledger 走完整原生首消费) ----
    reference = dict(payload.get("native_reference") or {})
    native_export_digest = str(reference.get("native_export_digest") or "")
    if not native_export_digest:
        raise V3ProjectionContractError(
            "投影缺 native_reference.native_export_digest(引用断裂;"
            "不猜补)",
            {"kind": "v3_native_reference_missing",
             "native_export_digest": ""})
    if ledger is not None:
        try:
            read_native_export(ledger, run_dir, native_export_digest)
        except Exception as exc:  # noqa: BLE001 —— 原生首消费失败如实拒
            raise V3ProjectionContractError(
                f"投影引用的原生导出首消费失败:{native_export_digest}"
                "(投影的原生来源必须先经原生首消费;不吞成成功)",
                {"kind": "v3_projection_source_binding_mismatch",
                 "check": "native_export_first_consumption",
                 "native_export_digest": native_export_digest,
                 "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    # 文件级绑定:manifest/payload 本体 + 引用内部一致
    native_manifest, native_payload = _load_bound_native_export(
        run_dir, native_export_digest, payload)
    # ---- S4-C04:已表达字段按登记 adapter 同源复算比对 ----
    expected = _derived_projection_content(native_payload, run_dir)
    mismatches: list[str] = []
    if str(payload.get("run_id") or "") != expected["run_id"]:
        mismatches.append("run_id")
    route = dict(payload.get("route") or {})
    if list(route.get("steps") or []) != expected["route_steps"]:
        mismatches.append("route.steps")
    if str(route.get("root_smiles") or "") != expected["root_smiles"]:
        mismatches.append("route.root_smiles")
    if list(payload.get("information_losses") or []) != \
            expected["information_losses"]:
        mismatches.append("information_losses")
    if dict(payload.get("unprojectable_summaries") or {}) != \
            expected["unprojectable_summaries"]:
        mismatches.append("unprojectable_summaries")
    if mismatches:
        raise V3ProjectionContractError(
            f"投影的已表达字段与按登记 adapter 从其原生载荷同源复算的"
            f"内容不符:{sorted(mismatches)}(有损投影不许可捏造/删除"
            "已提交事件、deferred 或其它已表达事实;自洽重算 projection"
            "_digest 换新目录不洗白;保全原文件)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "adapter_derived_content",
             "mismatched_fields": sorted(mismatches),
             "native_export_digest": native_export_digest})
    return payload


def _load_bound_native_export(run_dir: Path, export_digest: str,
                              projection_payload: dict) -> tuple[dict, dict]:
    """S4-C04 文件级来源绑定:读取投影引用的原生导出 manifest+payload
    并核内部一致(与构建侧 read_native_export 共用绑定语义;无 ledger
    的发现接口也核到内容绑定,不再只列文件/只查存在)。

    返回 (manifest, payload);文件缺失 ⇒ v3_native_reference_missing;
    绑定不符 ⇒ v3_projection_source_binding_mismatch。"""
    out_dir = run_dir / NATIVE_EXPORT_SUBDIR / str(export_digest)[:24]
    manifest_path = out_dir / NATIVE_EXPORT_MANIFEST_FILE
    payload_path = out_dir / NATIVE_EXPORT_PAYLOAD_FILE
    if not manifest_path.is_file() or not payload_path.is_file():
        raise V3ProjectionContractError(
            f"投影的原生导出引用不可解析:{export_digest or '<空>'}"
            "(引用断裂 ⇒ 拒;不猜补)",
            {"kind": "v3_native_reference_missing",
             "native_export_digest": export_digest,
             "expected_manifest": str(manifest_path)})
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        native_payload = json.loads(
            payload_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise V3ProjectionContractError(
            f"投影的原生导出文件不可解析:{out_dir}(引用断裂 ⇒ 拒)",
            {"kind": "v3_native_reference_missing",
             "native_export_digest": export_digest,
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    reference = dict(projection_payload.get("native_reference") or {})
    binding: list[str] = []
    if str(manifest.get("export_digest") or "") != export_digest:
        binding.append("manifest_export_digest")
    core_recomputed = content_hash(
        {k: v for k, v in manifest.items() if k != "export_digest"})
    if core_recomputed != str(manifest.get("export_digest") or ""):
        binding.append("manifest_core_digest")
    payload_sha = hashlib.sha256(
        payload_path.read_bytes()).hexdigest()
    if payload_sha != str(manifest.get("payload_sha256") or ""):
        binding.append("payload_sha256")
    if content_hash({k: v for k, v in native_payload.items()
                     if k != "content_digest"}) \
            != str(native_payload.get("content_digest") or ""):
        binding.append("payload_content_digest")
    if str(native_payload.get("content_digest") or "") != \
            str(manifest.get("content_digest") or ""):
        binding.append("manifest_content_digest")
    if str(reference.get("native_result_content_digest") or "") != \
            str(manifest.get("content_digest") or ""):
        binding.append("reference_content_digest")
    if str(reference.get("native_export_payload_sha256") or "") != \
            str(manifest.get("payload_sha256") or ""):
        binding.append("reference_payload_sha256")
    authority = dict(manifest.get("authority_references") or {})
    if str(reference.get("native_result_task_key") or "") != \
            str(authority.get("native_result_task_key") or ""):
        binding.append("reference_native_task_key")
    if str(projection_payload.get("run_id") or "") != \
            str(manifest.get("run_id") or "") \
            or str(native_payload.get("run_id") or "") != \
            str(manifest.get("run_id") or ""):
        binding.append("run_id")
    graph_revision = dict(projection_payload.get(
        "native_graph_revision") or {})
    if str(graph_revision.get("aggregate_digest") or "") != \
            content_hash(manifest.get("graph_facts") or {}):
        binding.append("graph_revision_aggregate")
    if binding:
        raise V3ProjectionContractError(
            f"投影与原生导出的来源绑定不一致:{sorted(binding)}"
            "(已验证原生存在/投影自 hash 不是投影证书;混搭 digest/"
            "task_key/sha 或换 manifest 不洗白;保全原文件)",
            {"kind": "v3_projection_source_binding_mismatch",
             "check": "native_reference_internal_consistency",
             "binding_failures": sorted(binding),
             "native_export_digest": export_digest})
    return manifest, native_payload


def list_v3_projections_for_native(
        run_dir: str | Path, *, native_export_digest: str | None = None,
        native_content_digest: str | None = None) -> list[dict]:
    """反查引用某原生结果的全部投影(**双向引用的只读反向**:读
    投影文件匹配 native 引用;不修改原生 manifest/任何文件)。

    匹配键:native_export_digest 或 native_content_digest(至少给一个;
    两者都给 ⇒ 交集语义)。
    """
    if native_export_digest is None and native_content_digest is None:
        raise V3ProjectionContractError(
            "反查需要至少一个匹配键(native_export_digest 或 "
            "native_content_digest)",
            {"kind": "v3_reverse_lookup_key_missing"})
    root = Path(run_dir) / V3_PROJECTION_SUBDIR
    if not root.is_dir():
        return []
    out: list[dict] = []
    for digest_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        path = digest_dir / V3_PROJECTION_FILE
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue  # 损坏投影只跳过反查(读取面另行 fail-closed)
        ref = payload.get("native_reference") or {}
        if native_export_digest is not None and \
                str(ref.get("native_export_digest") or "") \
                != str(native_export_digest):
            continue
        if native_content_digest is not None and \
                str(ref.get("native_result_content_digest") or "") \
                != str(native_content_digest):
            continue
        out.append({
            "projection_digest": str(payload.get("projection_digest") or ""),
            "dir": str(digest_dir),
            "lossy_projection": payload.get("lossy_projection") is True,
        })
    return out
