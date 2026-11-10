"""v3 冻结预测格式导出器 — 从候选裁决产物 + PathwayStore 已提交事实
确定性投影(零 LLM)。

导出契约(TASK_V43_EXPORT_DEV §1 / v3 PROTOCOL §4):一行一路线 JSONL

    {"route_id": "pb_0002", "root_smiles": "<原始输入 SMILES>",
     "steps": [{"parent_smiles": "...", "predicted_products": ["...", ...]}]}

投影规则(全部固定并随导出元数据落盘;哈希进 batch identity):

- **答卷主源 = 候选裁决产物**(``results/<task>/report_adjudication.json``):
  显式 schema 分派 —— v1(旧 run)可报告集合必须与账本事件产物逐位一致;
  v2(EC298 Phase B)按 ``report_rank`` 投影报告列表,账本只交叉核对
  ``committed_event_ref`` 指向的产物及其 position/raw/cn,可报告集合可以
  大于已提交事件产物集合;未提交的可报告产品进入该父步骤但不产生子步骤,
  父节点无事件但有占位候选时仍生成父步骤(冻结策略明示并有测试)。
  ``expand_selected=false`` 的可报告候选(暂缓展开/仅报告)同样进该步
  答卷。检索原始卡(top5_candidates 视图)、模型原文、被拒产品一律不进
  答卷;草稿产物(另一文件名)永不进入本导出。
- **账本交叉核对**:每个已提交事件必须存在对应裁决产物,且其可报告
  集合与 event_products 逐位一致;裁决缺失/身份不符/位次不符 = 账本
  损坏,fail-closed 不静默删边。裁决产物读取时重核 payload 哈希。
- ``root_smiles`` = run_identity ``inputs.root_smiles`` 的**真实原始输入**;
  不用 path_id、显示名或 cn 规范身份冒充原始 SMILES。
- ``parent_smiles`` / ``predicted_products`` 使用原始 SMILES:父 = 首现
  父路径的创建边 ``product_smiles_full``(缺省回落 ``product_smiles``),
  根 = run_identity 原始输入;产物 = 裁决条目 ``product_smiles_full``
  (回落 ``product_smiles``)。cn 身份字符串绝不充当 raw 产物(raw_sb
  口径保电荷,提前中和会把 raw_sb 对照口径污染成 cn)。
- 步序:按父路径 ``seq`` 升序(= BFS 发现序;与事件提交顺序一致)。
  同父重复出现按**首现身份合并**(v3 评测器 duplicate-parent 语义),
  合并保留首现 raw 形并在元数据记录其余 raw 形变体(信息损失如实留痕)。
- 排名:产物按裁决 ``report_rank`` 升序(= 事件内保存 ``position`` 的
  已接纳顺序);同父重复产物保留首现排名;每父上限 = 导出策略
  ``products_per_parent_cap``(默认 5,即"每步最多报告五个候选")。
  排序依据是**已验证的报告位次**,不是检索证据排名。
- 校验:根/父/产物 SMILES 必须可解析且 ``cn_identity(raw)`` 与账本
  存储身份一致;不一致 → LedgerCorrupt 结构化失败,不静默删边。唯一
  例外:零事件的失败 run(如 invalid_input)输出显式空答卷并在元数据
  标注 ``root_unparseable``。
- 确定性:同一账本 revision + 同一裁决产物 + 同一导出策略重复导出,
  predictions.jsonl 逐字节一致(无时间戳进答卷行;元数据除 generated_at
  外亦确定)。
    - 新鲜度:元数据记录账本 graph_revision 与导出策略哈希;``verify``
      发现 revision/策略落后即判过期,过期文件不得进入判分;另核对答卷
      文件自身 SHA 与候选裁决集合指纹(新增/删减/篡改裁决、事件变动或
      策略变动都使旧导出过期)。

导出是派生结果,可随时重建;本模块不调用引擎、不加载模型、无网络。
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..domain.identity import cn_identity
from ..domain.models import canonical_json, content_hash
from ..services.report_adjudication import (
    REPORT_ADJUDICATION_SCHEMA_V1,
    REPORT_ADJUDICATION_SCHEMA_V2,
    AdjudicationError,
    resolve_adjudication_validation_refs,
)

EXPORT_SCHEMA_VERSION = "v43-export-v3-2"

EXPORT_POLICY_DEFAULTS: dict = {
    # 每父产物上限(任务书 §0:每步最多报告五个有序候选;排序依据 =
    # 已验证报告位次,与检索证据排名无关)
    "products_per_parent_cap": 5,
    # 产物/父 raw 形取值规则:product_smiles_full 优先(身份承载形),
    # 缺失回落 product_smiles;绝不使用 cn 身份字符串
    "raw_smiles_field": "product_smiles_full_fallback_product_smiles",
    # 同父分子(同 cn 身份)多来路:按首现父路径合并(v3 评测器语义)
    "parent_merge": "first_seen_identity_by_parent_seq",
    # 步序:父路径 seq 升序(BFS 发现序,与提交顺序一致)
    "step_order": "parent_seq",
    # 同父重复产物:保留首现排名
    "in_parent_dedupe": "keep_first_rank",
    # 同一父路径多个已提交事件(仅合成账本/历史 run 出现):按稳定提交
    # 次序(created_at, event_id)合并可报告列表
    "multi_event_merge": "commit_order_created_at_then_event_id",
}


class ExportError(RuntimeError):
    """导出失败(结构化;不含密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class LedgerCorrupt(ExportError):
    """账本/裁决产物损坏或不一致(fail-closed,不静默删边)。"""


class ExportStale(ExportError):
    """已存在导出落后于账本 revision 或导出策略(过期文件不得判分)。"""


def load_export_policy(overrides: dict | None = None) -> dict:
    pol = dict(EXPORT_POLICY_DEFAULTS)
    for k, v in (overrides or {}).items():
        if k in pol:
            pol[k] = v
        else:
            raise ExportError(f"未知导出策略键:{k}", {"key": k})
    return pol


def export_policy_hash(policy: dict) -> str:
    return hashlib.sha256(canonical_json(policy).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 只读账本


class _ReadOnlyLedger:
    """只读账本访问(URI mode=ro;导出绝不写 pathway.sqlite)。"""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        if not path.is_file():
            raise ExportError(f"账本不存在:{path}", {"path": str(path)})
        try:
            self.conn = sqlite3.connect(
                f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise LedgerCorrupt(f"账本无法打开(只读):{exc}",
                                {"path": str(path)}) from exc
        self.conn.row_factory = sqlite3.Row
        self._require_tables()

    def _require_tables(self) -> None:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r["name"] for r in rows}
        missing = {"meta", "compounds", "reaction_events", "event_products",
                   "path_instances"} - names
        if missing:
            raise LedgerCorrupt(
                f"账本缺表:{sorted(missing)}", {"missing": sorted(missing)})

    def graph_revision(self) -> int:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='graph_revision'").fetchone()
        return int(row["value"]) if row else 0

    def current_run(self) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='current_run'").fetchone()
        return row["value"] if row else None

    def paths(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM path_instances WHERE run_id = ? ORDER BY seq",
            (run_id,)).fetchall()
        return [dict(r) for r in rows]

    def events(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM reaction_events WHERE run_id = ?"
            " ORDER BY created_at, event_id", (run_id,)).fetchall()
        return [dict(r) for r in rows]

    def event_products(self, event_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM event_products WHERE event_id = ?"
            " ORDER BY position", (event_id,)).fetchall()
        return [dict(r) for r in rows]

    def product_path(self, event_id: str, position: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM path_instances WHERE event_id = ?"
            " AND product_position = ?",
            (event_id, position)).fetchone()
        return dict(row) if row else None


def _raw_of(product_row: dict) -> str:
    """产物 raw SMILES 固定规则:product_smiles_full 优先,回落 product_smiles。"""
    raw = (product_row.get("product_smiles_full") or "").strip()
    if not raw:
        raw = (product_row.get("product_smiles") or "").strip()
    if not raw:
        raise LedgerCorrupt(
            "事件产物缺 raw SMILES(product_smiles_full 与 product_smiles 皆空)",
            {"event_id": product_row.get("event_id"),
             "position": product_row.get("position")})
    return raw


# ------------------------------------------------------- 候选裁决产物读取


def load_adjudications(run_dir: str | Path) -> tuple[dict[str, list[dict]], str]:
    """results/ 扫描候选裁决产物 → (path_id → [payload], schema 版本)。

    - 显式 schema 分派:``v43-report-adjudication-1``(旧)与
      ``v43-report-adjudication-2``(Phase B v2)各自走专属投影;同一 run
      混用两代 schema 拒绝;未知 schema 拒绝;读取时重核 payload 哈希;
      v2 载荷读取时执行完整不变量校验(草稿产物为另一文件名,永不进入
      本扫描,不可导出)。
    - 同一 path_id 的多份裁决对应同父路径多个已提交事件(合成账本/历史
      run 形态),按稳定提交次序 (信封 created_at, event_id) 排列;正常
      工作流每父路径恰一份最终裁决。
    """
    from ..services.report_adjudication import validate_adjudication_payload

    results_dir = Path(run_dir) / "results"
    if not results_dir.is_dir():
        return {}, REPORT_ADJUDICATION_SCHEMA_V1
    index: dict[str, list[tuple[tuple, dict]]] = {}
    schemas: set[str] = set()
    for task_dir in sorted(results_dir.iterdir()):
        path = task_dir / "report_adjudication.json"
        if not path.is_file():
            continue
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LedgerCorrupt(
                f"裁决产物无法解析:{path}", {"error": str(exc)[:200]})
        payload = envelope.get("payload", {})
        stored = envelope.get("payload_hash")
        actual = content_hash(payload)
        if stored != actual:
            raise LedgerCorrupt(
                f"裁决产物哈希不符:{path}",
                {"stored": str(stored)[:12], "actual": actual[:12]})
        schema = payload.get("schema_version")
        if schema == REPORT_ADJUDICATION_SCHEMA_V2:
            schemas.add(schema)
            try:
                validate_adjudication_payload(payload)
            except Exception as exc:
                raise LedgerCorrupt(
                    f"v2 裁决不变量校验失败:{path}",
                    {"error": str(exc)[:200],
                     "detail": getattr(exc, "detail", {})})
        elif schema == REPORT_ADJUDICATION_SCHEMA_V1:
            schemas.add(schema)
        else:
            raise LedgerCorrupt(
                f"未知候选裁决 schema:{path}",
                {"schema_version": schema})
        pid = payload.get("path_id")
        if not pid:
            raise LedgerCorrupt(
                f"裁决产物缺 path_id:{path}", {})
        index.setdefault(pid, []).append(
            ((envelope.get("created_at") or ""),
             payload.get("event_id") or "", payload))
    if len(schemas) > 1:
        raise LedgerCorrupt(
            "同一 run 混用新旧候选裁决 schema(不静默重解释)",
            {"schemas": sorted(schemas)})
    schema = (sorted(schemas) or [REPORT_ADJUDICATION_SCHEMA_V1])[0]
    out: dict[str, list[dict]] = {}
    for pid, items in index.items():
        items.sort(key=lambda t: (t[0], t[1]))
        payloads = [t[2] for t in items]
        event_ids = [p.get("event_id") for p in payloads]
        if len(set(event_ids)) != len(event_ids):
            raise LedgerCorrupt(
                f"同一父路径出现重复 event_id 的裁决:{pid}",
                {"event_ids": event_ids})
        out[pid] = payloads
    return out, schema


# ---------------------------------------------------------------- 投影


@dataclass
class _Projection:
    """一次导出的中间投影(供测试与诊断检查)。"""

    root_smiles: str
    root_identity: str
    steps: list[dict] = field(default_factory=list)
    n_committed_products: int = 0
    n_reportable_products: int = 0
    n_report_only_products: int = 0
    n_products_emitted: int = 0
    n_truncated_products: int = 0
    n_reportable_not_expanded: int = 0
    n_merged_parents: int = 0
    n_parents_no_reportable: int = 0
    parent_raw_form_variants: dict[str, list[str]] = field(default_factory=dict)


def project_route(
    ledger: _ReadOnlyLedger, run_dir: Path, run_id: str,
    root_smiles: str, root_identity: str | None,
    policy: dict,
    adjudications: dict[str, list[dict]] | None = None,
    schema: str | None = None,
) -> _Projection:
    """schema 分派入口:v1(旧)/v2(Phase B)候选裁决各走专属投影;
    schema 由 load_adjudications 判定。答卷主源是裁决产物;账本用于
    交叉核对与父 raw 形。"""
    if adjudications is None:
        adjudications, schema = load_adjudications(run_dir)
    if schema == REPORT_ADJUDICATION_SCHEMA_V2:
        return _project_route_v2(ledger, run_dir, run_id, root_smiles,
                                 root_identity, policy, adjudications)
    return _project_route_v1(ledger, run_dir, run_id, root_smiles,
                             root_identity, policy, adjudications)


def _project_route_v2(
    ledger: _ReadOnlyLedger, run_dir: Path, run_id: str, root_smiles: str,
    root_identity: str | None, policy: dict,
    adjudications: dict[str, list[dict]],
) -> _Projection:
    """v2 裁决投影(Phase B §4):可报告列表与已提交事件产物解耦。

    - ``predicted_products`` 按裁决 ``report_rank`` 投影(原始 SMILES,
      重算身份核对,不信任缓存);账本只交叉核对 ``committed_event_ref``
      指向的产物及其 position/raw/cn,不再要求整个可报告列表等于
      event_products;
    - 未提交的可报告产品进入该父步骤,但不产生子步骤;
    - 父节点完全没有 ReactionEvent 但存在最终可报告候选:仍生成一个父
      步骤(冻结策略 ``no_event_reportable=allow_report_only_step``);
      既无事件也无占位候选的裁决不产生步骤;
    - 草稿产物(另一文件名)永不进入本投影;非 final schema 状态直接
      结构化失败。
    """
    proj = _Projection(root_smiles=root_smiles, root_identity=root_identity or "")
    paths = ledger.paths(run_id)
    events_by_parent: dict[str, list[dict]] = {}
    for ev in ledger.events(run_id):
        events_by_parent.setdefault(ev["parent_path_id"], []).append(ev)

    def parent_raw(p: dict) -> str:
        if p["parent_path_id"] is None:
            return proj.root_smiles
        if p["event_id"] is None or p["product_position"] is None:
            raise LedgerCorrupt(
                "非根路径缺创建边引用(账本损坏)",
                {"path_id": p["path_id"]})
        row = ledger.conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? AND position = ?",
            (p["event_id"], p["product_position"])).fetchone()
        if row is None:
            raise LedgerCorrupt(
                "父路径找不到创建边产物行(账本损坏)",
                {"path_id": p["path_id"], "event_id": p["event_id"],
                 "position": p["product_position"]})
        return _raw_of(dict(row))

    def entry_raw(e: dict) -> str:
        raw = (e.get("product_smiles_full") or "").strip() \
            or (e.get("product_smiles") or "").strip()
        if not raw:
            raise LedgerCorrupt(
                "裁决条目缺 raw SMILES",
                {"path_id": e.get("path_id"),
                 "evidence_id": e.get("evidence_id"),
                 "position": e.get("position")})
        return raw

    cap = int(policy["products_per_parent_cap"])
    merged: dict[str, dict] = {}  # parent identity → 投影状态
    for p in sorted(paths, key=lambda q: (q["seq"], q["path_id"])):
        pid = p["path_id"]
        adjs = adjudications.get(pid, [])
        committed = events_by_parent.get(pid, [])
        if not adjs:
            if committed:
                raise LedgerCorrupt(
                    "已提交事件缺少候选裁决产物(答卷主源缺失,fail-closed)",
                    {"path_id": pid,
                     "event_id": committed[0]["event_id"]})
            # 无事件且无裁决:awaiting/dead_end/depth_limit 等停留路径,
            # 无可报告候选,不产生步骤
            continue
        adj_event_ids: list[str | None] = []
        for a in adjs:
            if a.get("stage") != "final":
                raise LedgerCorrupt(
                    "非最终裁决进入导出(草稿不可导出)",
                    {"path_id": pid, "stage": a.get("stage")})
            # Phase B R1 P1-2:可报告条目必须能按 validation_ref 回查真实
            # 验证产物(validation.json / cardval.*.json),缺失/错指/哈希
            # 不符 → 结构化失败,不静默导出
            try:
                resolve_adjudication_validation_refs(run_dir, a)
            except AdjudicationError as exc:
                raise LedgerCorrupt(
                    f"裁决验证引用回查失败:{exc}",
                    {"path_id": pid, "detail": getattr(exc, "detail", {})})
            adj_event_ids.append((a.get("event") or {}).get("event_id"))
        for ev in committed:
            if ev["event_id"] not in adj_event_ids:
                raise LedgerCorrupt(
                    "已提交事件缺少对应候选裁决产物(不静默删边)",
                    {"path_id": pid, "event_id": ev["event_id"]})
        has_event = any(eid is not None for eid in adj_event_ids)
        n_ranked_any = sum(
            1 for a in adjs for e in a.get("products", [])
            if e.get("reportable"))
        if not has_event and n_ranked_any == 0:
            # 无事件且无占位候选:no_event 空裁决不产生步骤(冻结策略明示)
            continue
        # 步骤状态:首现路径建 state(raw 形 = 创建边)
        state = merged.get(p["substrate_identity"])
        if state is None:
            raw_parent = parent_raw(p)
            parsed = cn_identity(raw_parent)
            if parsed is None:
                raise LedgerCorrupt(
                    "父 SMILES 不可解析(账本损坏)",
                    {"path_id": pid,
                     "substrate_identity": p["substrate_identity"]})
            if parsed != p["substrate_identity"]:
                raise LedgerCorrupt(
                    "父 raw SMILES 与账本身份不一致",
                    {"path_id": pid, "raw": raw_parent,
                     "expected": p["substrate_identity"],
                     "computed": parsed})
            state = {"raw": raw_parent, "products": [], "seen": set(),
                     "n_reportable": 0, "n_not_expanded": 0}
            merged[p["substrate_identity"]] = state
        n_path_reportable = 0
        for adj in adjs:
            ev_id = (adj.get("event") or {}).get("event_id")
            if ev_id is not None:
                ev = next((e for e in committed
                           if e["event_id"] == ev_id), None)
                if ev is None:
                    raise LedgerCorrupt(
                        "裁决 event_id 在账本不存在(账本损坏)",
                        {"path_id": pid, "event_id": ev_id})
                # 账本侧校验:事件产物 raw 可解析且与存储身份一致
                ledger_products = ledger.event_products(ev_id)
                for q in ledger_products:
                    proj.n_committed_products += 1
                    lraw = _raw_of(q)
                    lparsed = cn_identity(lraw)
                    if lparsed is None or lparsed != q["product_identity"]:
                        raise LedgerCorrupt(
                            "账本产物 raw SMILES 与存储身份不一致(损坏)",
                            {"event_id": ev_id,
                             "position": q["position"], "raw": lraw,
                             "stored": q["product_identity"],
                             "computed": lparsed})
                # 逐位对账:committed 条目 ⇄ 账本事件产物(position/raw/cn);
                # 不再要求整个可报告列表等于 event_products
                committed_entries = [
                    e for e in adj.get("products", [])
                    if e.get("committed_event_ref") == ev_id]
                by_pos = {e.get("position"): e for e in committed_entries}
                ledger_by_pos = {q["position"]: q for q in ledger_products}
                if set(by_pos) != set(ledger_by_pos):
                    raise LedgerCorrupt(
                        "裁决已提交条目与账本事件产物位次集合不一致",
                        {"path_id": pid, "event_id": ev_id,
                         "adjudication_positions": sorted(
                             str(k) for k in by_pos),
                         "ledger_positions": sorted(
                             str(k) for k in ledger_by_pos)})
                for pos, q in ledger_by_pos.items():
                    e = by_pos[pos]
                    if e.get("cn_identity") != q["product_identity"]:
                        raise LedgerCorrupt(
                            "裁决已提交条目与账本产物身份不一致",
                            {"path_id": pid, "event_id": ev_id,
                             "position": pos,
                             "adjudication": e.get("cn_identity"),
                             "ledger": q["product_identity"]})
                    if entry_raw(e) != _raw_of(q):
                        raise LedgerCorrupt(
                            "裁决已提交条目与账本产物 raw SMILES 不一致",
                            {"path_id": pid, "event_id": ev_id,
                             "position": pos})
                    prow = ledger.product_path(ev_id, pos)
                    if prow is None:
                        raise LedgerCorrupt(
                            "已提交条目在账本无产物路径(账本损坏)",
                            {"path_id": pid, "event_id": ev_id,
                             "position": pos})
                    if bool(e.get("expand_selected")) \
                            and prow["status"] == "deferred":
                        raise LedgerCorrupt(
                            "expand_selected 与账本路径状态矛盾(应为 frontier 系)",
                            {"path_id": pid,
                             "product_path": prow["path_id"],
                             "status": prow["status"]})
            # 占位候选投影:未提交的可报告产品同样进本父步骤(无子步骤)
            ranked = sorted(
                (e for e in adj.get("products", []) if e.get("reportable")),
                key=lambda e: (e.get("report_rank") or 0))
            for e in ranked:
                proj.n_reportable_products += 1
                if e.get("committed_event_ref") is None:
                    proj.n_report_only_products += 1
                if not e.get("expand_selected"):
                    proj.n_reportable_not_expanded += 1
                    state["n_not_expanded"] += 1
                raw = entry_raw(e)
                ident = e.get("cn_identity")
                parsed = cn_identity(raw)
                if parsed is None:
                    raise LedgerCorrupt(
                        "产物 SMILES 不可解析(裁决损坏)",
                        {"path_id": pid,
                         "report_rank": e.get("report_rank"),
                         "raw": raw})
                if parsed != ident:
                    raise LedgerCorrupt(
                        "产物 raw SMILES 与重算身份不一致",
                        {"path_id": pid,
                         "report_rank": e.get("report_rank"),
                         "raw": raw, "expected": ident,
                         "computed": parsed})
                if ident in state["seen"]:
                    continue  # 同父重复产物保留首现排名
                state["seen"].add(ident)
                state["products"].append(raw)
            n_path_reportable += len(ranked)
        state["n_reportable"] += n_path_reportable
        if n_path_reportable == 0:
            proj.n_parents_no_reportable += 1

    # 同父身份多来路的 raw 形变体(信息损失记录,不改变首现选择)
    for p in sorted(paths, key=lambda q: (q["seq"], q["path_id"])):
        state = merged.get(p["substrate_identity"])
        if state is None:
            continue
        variant = parent_raw(p)
        variants = proj.parent_raw_form_variants.setdefault(
            p["substrate_identity"], [])
        if variant not in variants:
            variants.append(variant)

    for ident, state in merged.items():
        variants = proj.parent_raw_form_variants.get(ident) or [state["raw"]]
        if len(variants) > 1:
            proj.n_merged_parents += 1
        emitted = state["products"][:cap]
        proj.n_truncated_products += len(state["products"]) - len(emitted)
        proj.n_products_emitted += len(emitted)
        proj.steps.append({
            "parent_smiles": state["raw"],
            "predicted_products": emitted,
        })
    return proj


def _project_route_v1(
    ledger: _ReadOnlyLedger, run_dir: Path, run_id: str,
    root_smiles: str, root_identity: str | None,
    policy: dict,
    adjudications: dict[str, list[dict]],
) -> _Projection:
    """v1 裁决(旧 run)投影:历史语义逐条保持 —— 可报告集合必须与
    账本事件产物逐位一致,未提交候选不可报告。"""
    proj = _Projection(root_smiles=root_smiles, root_identity=root_identity or "")
    paths = ledger.paths(run_id)
    events_by_parent: dict[str, list[dict]] = {}
    for ev in ledger.events(run_id):
        events_by_parent.setdefault(ev["parent_path_id"], []).append(ev)

    # 父路径 raw 形:根用 run_identity 原始输入;非根 = 创建边产物的
    # product_smiles_full(回落 product_smiles)。同父身份多来路时收集
    # 全部 raw 变体,首现(按父路径 seq)者入答卷,其余入元数据。
    def parent_raw(p: dict) -> str:
        if p["parent_path_id"] is None:
            return proj.root_smiles
        if p["event_id"] is None or p["product_position"] is None:
            raise LedgerCorrupt(
                "非根路径缺创建边引用(账本损坏)",
                {"path_id": p["path_id"]})
        row = ledger.conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? AND position = ?",
            (p["event_id"], p["product_position"])).fetchone()
        if row is None:
            raise LedgerCorrupt(
                "父路径找不到创建边产物行(账本损坏)",
                {"path_id": p["path_id"], "event_id": p["event_id"],
                 "position": p["product_position"]})
        return _raw_of(dict(row))

    cap = int(policy["products_per_parent_cap"])
    merged: dict[str, dict] = {}  # parent identity → 投影状态
    for p in sorted(paths, key=lambda q: (q["seq"], q["path_id"])):
        pid = p["path_id"]
        adjs = adjudications.get(pid, [])
        committed = events_by_parent.get(pid, [])
        if not adjs:
            if committed:
                raise LedgerCorrupt(
                    "已提交事件缺少候选裁决产物(答卷主源缺失,fail-closed)",
                    {"path_id": pid,
                     "event_id": committed[0]["event_id"]})
            # 无事件且无裁决:awaiting/dead_end/depth_limit 等停留路径,
            # 无可报告候选,不产生步骤
            continue
        adj_event_ids = [a.get("event_id") for a in adjs]
        for ev in committed:
            if ev["event_id"] not in adj_event_ids:
                raise LedgerCorrupt(
                    "已提交事件缺少对应候选裁决产物(不静默删边)",
                    {"path_id": pid, "event_id": ev["event_id"]})
        state = merged.get(p["substrate_identity"])
        n_path_reportable = 0
        for adj in adjs:
            ev = next((e for e in committed
                       if e["event_id"] == adj.get("event_id")), None)
            if ev is None:
                raise LedgerCorrupt(
                    "裁决产物 event_id 在账本不存在(账本损坏)",
                    {"path_id": pid, "event_id": adj.get("event_id")})
            # 账本侧校验:事件产物 raw 可解析且与存储身份一致
            ledger_products = ledger.event_products(ev["event_id"])
            for q in ledger_products:
                proj.n_committed_products += 1
                lraw = _raw_of(q)
                lparsed = cn_identity(lraw)
                if lparsed is None or lparsed != q["product_identity"]:
                    raise LedgerCorrupt(
                        "账本产物 raw SMILES 与存储身份不一致(损坏)",
                        {"event_id": ev["event_id"],
                         "position": q["position"], "raw": lraw,
                         "stored": q["product_identity"],
                         "computed": lparsed})
            # 裁决侧:可报告集合与账本事件产物逐位一致(顺序=位次)
            reportable = sorted(
                (e for e in adj.get("entries", []) if e.get("reportable")),
                key=lambda e: (e.get("report_rank") or 0))
            reportable_ids = [e["product_identity"] for e in reportable]
            ledger_ids = [q["product_identity"] for q in ledger_products]
            if reportable_ids != ledger_ids:
                raise LedgerCorrupt(
                    "裁决可报告集合与账本事件产物不一致(不静默删边)",
                    {"path_id": pid, "event_id": ev["event_id"],
                     "adjudication_n": len(reportable_ids),
                     "ledger_n": len(ledger_ids)})
            # 步骤状态:首现路径建 state(raw 形 = 创建边)
            if state is None:
                raw_parent = parent_raw(p)
                parsed = cn_identity(raw_parent)
                if parsed is None:
                    raise LedgerCorrupt(
                        "父 SMILES 不可解析(账本损坏)",
                        {"path_id": pid,
                         "substrate_identity": p["substrate_identity"]})
                if parsed != p["substrate_identity"]:
                    raise LedgerCorrupt(
                        "父 raw SMILES 与账本身份不一致",
                        {"path_id": pid, "raw": raw_parent,
                         "expected": p["substrate_identity"],
                         "computed": parsed})
                state = {"raw": raw_parent, "products": [], "seen": set(),
                         "n_reportable": 0, "n_not_expanded": 0}
                merged[p["substrate_identity"]] = state
            for entry in reportable:
                proj.n_reportable_products += 1
                if not entry.get("expand_selected"):
                    proj.n_reportable_not_expanded += 1
                    state["n_not_expanded"] += 1
                raw = (entry.get("product_smiles_full") or "").strip() \
                    or (entry.get("product_smiles") or "").strip()
                if not raw:
                    raise LedgerCorrupt(
                        "裁决条目缺 raw SMILES",
                        {"path_id": pid,
                         "report_rank": entry.get("report_rank")})
                ident = entry.get("product_identity")
                parsed = cn_identity(raw)
                if parsed is None:
                    raise LedgerCorrupt(
                        "产物 SMILES 不可解析(裁决/账本损坏)",
                        {"path_id": pid,
                         "report_rank": entry.get("report_rank"),
                         "raw": raw})
                if parsed != ident:
                    raise LedgerCorrupt(
                        "产物 raw SMILES 与账本身份不一致",
                        {"path_id": pid,
                         "report_rank": entry.get("report_rank"),
                         "raw": raw, "expected": ident,
                         "computed": parsed})
                # 可报告候选必须有账本产物路径(展开或暂缓),拒因留痕
                ev_id = adj.get("event_id")
                prow = ledger.product_path(ev_id, entry.get("position", -1)) \
                    if ev_id else None
                if prow is None:
                    raise LedgerCorrupt(
                        "可报告候选在账本无产物路径(账本损坏)",
                        {"path_id": pid, "event_id": ev_id,
                         "position": entry.get("position")})
                if bool(entry.get("expand_selected")) \
                        and prow["status"] == "deferred":
                    raise LedgerCorrupt(
                        "expand_selected 与账本路径状态矛盾(应为 frontier 系)",
                        {"path_id": pid,
                         "product_path": prow["path_id"],
                         "status": prow["status"]})
                if ident in state["seen"]:
                    continue  # 同父重复产物保留首现排名
                state["seen"].add(ident)
                state["products"].append(raw)
            n_path_reportable += len(reportable)
        state["n_reportable"] += n_path_reportable
        if n_path_reportable == 0:
            proj.n_parents_no_reportable += 1

    # 同父身份多来路的 raw 形变体(信息损失记录,不改变首现选择)
    for p in sorted(paths, key=lambda q: (q["seq"], q["path_id"])):
        state = merged.get(p["substrate_identity"])
        if state is None:
            continue
        variant = parent_raw(p)
        variants = proj.parent_raw_form_variants.setdefault(
            p["substrate_identity"], [])
        if variant not in variants:
            variants.append(variant)

    for ident, state in merged.items():
        variants = proj.parent_raw_form_variants.get(ident) or [state["raw"]]
        if len(variants) > 1:
            proj.n_merged_parents += 1
        emitted = state["products"][:cap]
        proj.n_truncated_products += len(state["products"]) - len(emitted)
        proj.n_products_emitted += len(emitted)
        proj.steps.append({
            "parent_smiles": state["raw"],
            "predicted_products": emitted,
        })
    return proj


def check_adjudication_schema_identity(
    run_dir: str | Path, identity: dict,
) -> tuple[str | None, str, dict[str, list[dict]]]:
    """裁决 schema ⇄ run identity 声明一致性(任务书 Phase B §4:
    "裁决/账本/身份不一致时拒绝";R3 review 补强)。

    - 身份声明为 v2 而实际**非空**裁决集合为 v1(或反之)→ LedgerCorrupt
      —— 导出走哪套投影由实际 schema 分派,但分派结果不得与身份声明矛盾
      (身份声明的预期 schema 不是投影选择器,是一致性核对基准);
    - v2 裁决出现在无身份声明的旧 run → LedgerCorrupt(v2 只由写入
      identity 块的新代码产生;无声明 + v2 文件 = 被篡改/拼装);
    - 身份声明 v2 + 空裁决集合 = 合法状态(全部路径停待预测),放行;
    - 无身份声明的旧 run + v1 裁决 = 历史兼容,放行。

    返回 (expected, actual, adjudications)。导出与 verify 都调用。
    """
    expected = (identity.get("adjudication") or {}).get("schema_version")
    adjs, actual = load_adjudications(run_dir)
    if adjs:
        if expected and actual != expected:
            raise LedgerCorrupt(
                "裁决 schema 与 run identity 声明不一致(拒绝导出,不静默"
                "按实际 schema 重解释)",
                {"expected": expected, "actual": actual,
                 "n_adjudications": sum(len(v) for v in adjs.values())})
        if actual == REPORT_ADJUDICATION_SCHEMA_V2 and not expected:
            raise LedgerCorrupt(
                "v2 裁决出现在无身份声明的旧 run(身份与裁决不一致)",
                {"actual": actual,
                 "n_adjudications": sum(len(v) for v in adjs.values())})
    return expected, actual, adjs


def adjudication_fingerprint(run_dir: str | Path,
                             expected_schema: str | None = None) -> dict:
    """候选裁决集合指纹(元数据与 verify 新鲜度用;任务书 Phase B §4)。

    聚合全部最终裁决的 payload 内容哈希 + 已提交事件引用;裁决的任何
    新增/删减/篡改都会改变聚合值,使既有导出过期。

    expected_schema:run identity 声明的裁决 schema(Phase B R2)。
    裁决文件为空属 v2 run 的**合法状态**(如全部路径停待预测),此时
    schema 如实记 expected_schema(默认回退 v1 仅用于无身份声明的旧
    run)——空集合的指纹确定可复算,删光裁决文件必然与导出时指纹不符。
    """
    adjs, schema = load_adjudications(run_dir)
    if not adjs and expected_schema:
        schema = expected_schema
    payload_hashes = sorted(content_hash(p) for ps in adjs.values()
                            for p in ps)
    committed_event_ids = sorted({
        (p.get("event") or {}).get("event_id") or p.get("event_id") or ""
        for ps in adjs.values() for p in ps
    } - {""})
    policy_versions = sorted({
        str((p.get("policy") or {}).get("policy_version", ""))
        for ps in adjs.values() for p in ps
    } - {""})
    aggregate = hashlib.sha256(
        "\n".join([schema] + policy_versions + payload_hashes).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": schema,
        "policy_versions": policy_versions,
        "n_adjudications": sum(len(ps) for ps in adjs.values()),
        "payload_hashes_sha256": aggregate,
        "committed_event_ids": committed_event_ids,
    }


def _load_run_identity(run_dir: Path) -> dict:
    path = run_dir / "run_identity.json"
    if not path.is_file():
        raise ExportError(
            f"run_identity.json 缺失:{run_dir}(导出需要真实原始输入)",
            {"run_dir": str(run_dir)})
    return json.loads(path.read_text(encoding="utf-8"))


def _identity_fingerprint(identity: dict) -> str:
    from ..storage.run_identity import identity_fingerprint

    return identity_fingerprint(identity)


def export_run_v3(
    runs_root: str | Path,
    run_id: str,
    *,
    route_id: str | None = None,
    policy: dict | None = None,
    verify_only: bool = False,
) -> dict:
    """导出一个 run → ``<runs_root>/<run_id>/predictions.jsonl`` + 元数据。

    route_id:答卷行 route_id(缺省 = run_id;批跑由协调器传冻结映射)。
    verify_only:只核对现有导出是否新鲜(账本 revision + 策略哈希),
    不重写文件。
    """
    runs_root = Path(runs_root)
    run_dir = runs_root / run_id
    pol = load_export_policy(policy)
    pol_sha = export_policy_hash(pol)
    identity = _load_run_identity(run_dir)
    ledger = _ReadOnlyLedger(run_dir / "pathway.sqlite")

    ledger_run = ledger.current_run()
    if ledger_run is not None and ledger_run != run_id:
        raise LedgerCorrupt(
            "账本 current_run 与请求 run_id 不一致",
            {"ledger_run": ledger_run, "requested": run_id})
    revision = ledger.graph_revision()

    meta_path = run_dir / "export_metadata.json"
    if verify_only:
        if not (run_dir / "predictions.jsonl").is_file() or not meta_path.is_file():
            raise ExportStale(
                f"导出不存在:{run_dir}/predictions.jsonl", {"run_id": run_id})
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("ledger_graph_revision") != revision:
            raise ExportStale(
                "导出过期:账本 revision 已推进",
                {"exported_revision": meta.get("ledger_graph_revision"),
                 "current_revision": revision})
        if meta.get("export_policy_sha256") != pol_sha:
            raise ExportStale(
                "导出过期:导出策略变化", {"policy_sha256": pol_sha})
        if meta.get("run_identity_fingerprint") != _identity_fingerprint(identity):
            raise ExportStale(
                "导出过期:run 身份指纹变化", {"run_id": run_id})
        # 答卷文件自身 SHA(新旧导出都有 predictions_sha256 字段)
        actual_sha = hashlib.sha256(
            (run_dir / "predictions.jsonl").read_bytes()).hexdigest()
        if meta.get("predictions_sha256") != actual_sha:
            raise ExportStale(
                "导出过期:答卷文件内容与记录 SHA 不符(被篡改或替换)",
                {"recorded": str(meta.get("predictions_sha256"))[:12],
                 "actual": actual_sha[:12]})
        # 候选裁决集合指纹(新增/删减/篡改裁决 → 过期)。Phase B R2:
        # 预期 schema 以 **run identity 声明**为准,不从现存文件反推 ——
        # 删光裁决文件不会把 v2 run 伪装成 v1;v2 run 元数据缺指纹块或
        # 字段不完整即过期;合法空裁决集合按 identity 预期 schema 出确定
        # 指纹,删光文件必然失配。仅无身份声明的 v1 旧 run 保留无块兼容。
        expected_adj_schema, _actual_adj_schema, _adjs = \
            check_adjudication_schema_identity(run_dir, identity)
        current_adj = adjudication_fingerprint(
            run_dir, expected_schema=expected_adj_schema)
        block = meta.get("adjudication")
        if expected_adj_schema == REPORT_ADJUDICATION_SCHEMA_V2:
            if not isinstance(block, dict):
                raise ExportStale(
                    "导出过期:v2 裁决缺候选裁决指纹块(新鲜度门禁不可跳过)",
                    {"run_id": run_id,
                     "expected_schema": REPORT_ADJUDICATION_SCHEMA_V2})
            missing = [k for k in ("schema_version", "policy_versions",
                                   "n_adjudications",
                                   "payload_hashes_sha256",
                                   "committed_event_ids")
                       if k not in block]
            if missing:
                raise ExportStale(
                    "导出过期:裁决指纹块字段不完整",
                    {"run_id": run_id, "missing": missing})
        if block is not None and block != current_adj:
            raise ExportStale(
                "导出过期:候选裁决集合变化(新增/删减/篡改或事件引用变动)",
                {"recorded_n": block.get("n_adjudications"),
                 "current_n": current_adj["n_adjudications"],
                 "recorded_aggregate":
                     str(block.get("payload_hashes_sha256"))[:12],
                 "current_aggregate":
                     current_adj["payload_hashes_sha256"][:12]})
        return {"ok": True, "verified": True, "metadata": meta}

    root_smiles = (identity.get("inputs") or {}).get("root_smiles", "")
    root_identity = (identity.get("inputs") or {}).get("root_identity")
    # R3:裁决 schema ⇄ 身份声明一致性(不越过;不一致即结构化失败)
    expected_adj_schema, actual_adj_schema, adjs = \
        check_adjudication_schema_identity(run_dir, identity)
    proj = project_route(ledger, run_dir, run_id, root_smiles, root_identity,
                         pol, adjudications=adjs, schema=actual_adj_schema)

    line = {
        "route_id": route_id or run_id,
        "root_smiles": root_smiles,
        "steps": proj.steps,
    }
    line_text = json.dumps(line, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n"
    pred_path = run_dir / "predictions.jsonl"
    tmp = run_dir / "predictions.jsonl.tmp"
    tmp.write_text(line_text, encoding="utf-8")
    os.replace(tmp, pred_path)

    # 零事件且根不可解析(如 invalid_input run):显式空答卷,如实标注
    root_unparseable = False
    if proj.n_reportable_products == 0 and not proj.steps:
        if cn_identity(root_smiles) is None:
            root_unparseable = True

    prev_meta = None
    if meta_path.is_file():
        try:
            prev_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            prev_meta = None
    superseded = None
    if prev_meta and prev_meta.get("ledger_graph_revision") != revision:
        superseded = {
            "previous_ledger_revision": prev_meta.get("ledger_graph_revision"),
            "previous_predictions_sha256":
                prev_meta.get("predictions_sha256"),
        }

    meta = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "run_id": run_id,
        "route_id": line["route_id"],
        "ledger_graph_revision": revision,
        "ledger_current_run": ledger_run,
        "run_identity_fingerprint": _identity_fingerprint(identity),
        "export_policy": pol,
        "export_policy_sha256": pol_sha,
        "predictions_sha256": hashlib.sha256(
            line_text.encode("utf-8")).hexdigest(),
        "predictions_lines": 1,
        "adjudication": adjudication_fingerprint(
            run_dir, expected_schema=expected_adj_schema),
        "counts": {
            "n_steps": len(proj.steps),
            "n_committed_products": proj.n_committed_products,
            "n_reportable_products": proj.n_reportable_products,
            "n_report_only_products": proj.n_report_only_products,
            "n_products_emitted": proj.n_products_emitted,
            "n_truncated_products": proj.n_truncated_products,
            "n_reportable_not_expanded": proj.n_reportable_not_expanded,
            "n_merged_parents": proj.n_merged_parents,
            "n_parents_no_reportable": proj.n_parents_no_reportable,
        },
        "parent_raw_form_variants": proj.parent_raw_form_variants,
        "root_unparseable": root_unparseable,
        "superseded": superseded,
    }
    tmp = run_dir / "export_metadata.json.tmp"
    tmp.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    os.replace(tmp, meta_path)
    return {
        "ok": True,
        "predictions_path": str(pred_path),
        "metadata_path": str(meta_path),
        "predictions_sha256": meta["predictions_sha256"],
        "metadata": meta,
    }
