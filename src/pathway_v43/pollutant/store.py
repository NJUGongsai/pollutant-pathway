"""PollutantPathwayStore — 新模式的独立 SQLite 账本(v3 回修,S1)。

v3(ppv1-store-3,R3 回修 2026-10-06)相对 v2 的变化(R2-08/09/10):
- **语义/出现拆分彻底化(R2-08)**:`representation_fidelity` 移出
  state 的不可变语义载荷 —— states 行只存严格分子事实(身份键成分:
  规范结构/形式电荷/立体与同位素状态/CN);每次出现的原始串、
  structure_origin、分轴 representation_fidelity、source_refs
  (event/position/role)全部存 appearance。同图不同来源 fidelity
  共存、互不升级;严格事实不同仍拒;
- **真实提交入口完整参照校验(R2-09)**:submit_event 以
  event.participants **实际派生**参与物引用(少报产物不得成功);
  事务内校验事件↔假设内容关系(同父路径、底物锚点、participants
  一致)、投影只指本事件产物、展开互斥且无悬空引用;首次违约 ⇒
  结构化错误 + 零写入回滚;重放核验**全部**必要记录
  (states/state_appearances/hypotheses/report_projections/
  expansion_plans),缺任一 ⇒ Ppv1LedgerCorrupt,不静默成功;
- **对象 schema 版本门接入 writer(R2-10)**:任何写入前校验事务内
  每个对象 dict 的版本(states/hypothesis/event/投影/计划),未知
  版本拒绝且零写入;event 持久 payload 保存 schema_version;
  版本常量引用 profile(不散落字面量)。

既有不变量:独立文件(run 目录内 pollutant_pathway.sqlite),不迁移、
不改写 legacy v43-store-* 账本;事件提交/投影/展开计划同事务一致;
幂等键 (run_id, parent_path_id, hypothesis_id, context_hash,
event_semantics_hash);同键异内容 Ppv1EventConflict(不覆盖)。

版本兼容口径:v3 起states 表语义块不再含 representation_fidelity
(R2-08 布局变化),v2(ppv1-store-2)文件按未知版本拒绝 —— v2 仅
存在于合成测试目录,无线上数据,不提供迁移;legacy v43-store-1/2
旧库仍走 legacy_reader 的显式版本名单(只读),不受影响。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..domain.models import canonical_json, content_hash, now_iso
from .events import (
    PPV1_EVENT_SUPPORTED_VERSIONS,
    PPV1_EXPANSION_POLICY_VERSION,
    PPV1_REPORT_PROJECTION_VERSION,
    PathwayEvent,
)
from .profile import (
    PPV1_CHEMSTATE_SCHEMA_VERSION,
    PPV1_HYPOTHESIS_SCHEMA_VERSION,
    PPV1_PROVENANCE_SCHEMA_VERSION,
    PPV1_STORE_SCHEMA_VERSION,
)

# 读取门引用 profile 常量(单一事实源;不散落字面量,R2-10)
PPV1_STORE_SUPPORTED_VERSIONS = (PPV1_STORE_SCHEMA_VERSION,)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS states (
    state_id   TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state_appearances (
    state_id    TEXT NOT NULL,
    appearance_hash TEXT NOT NULL,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (state_id, appearance_hash)
);
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id  TEXT PRIMARY KEY,
    parent_path_id TEXT NOT NULL,
    context_hash   TEXT NOT NULL DEFAULT '',
    payload        TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    event_id           TEXT PRIMARY KEY,
    run_id             TEXT NOT NULL,
    parent_path_id     TEXT NOT NULL,
    hypothesis_id      TEXT NOT NULL,
    context_hash       TEXT NOT NULL,
    event_semantics_hash TEXT NOT NULL,
    payload            TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    UNIQUE (run_id, parent_path_id, hypothesis_id, context_hash,
            event_semantics_hash)
);
CREATE TABLE IF NOT EXISTS report_projections (
    event_id  TEXT PRIMARY KEY,
    payload   TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS expansion_plans (
    event_id  TEXT PRIMARY KEY,
    payload   TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance_records (
    record_id TEXT PRIMARY KEY,
    run_id    TEXT NOT NULL,
    payload   TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ppv1_events_run
    ON events (run_id, parent_path_id);
CREATE INDEX IF NOT EXISTS idx_ppv1_hyp_parent
    ON hypotheses (parent_path_id);
"""

# ChemicalState 的严格分子事实(身份键成分;参与冲突判定)。
# v3:representation_fidelity 移出(R2-08)——保真度描述"该次出现
# 的表示与原始记录的关系",属出现层,不是分子身份事实。
_STATE_SEMANTIC_FIELDS = (
    "state_id", "smiles_isomeric", "cn_identity", "formal_charge",
    "stereo_information_status", "isotope_information_status",
    "schema_version",
)
# 出现记录字段(同一结构不同来路各自保留;不参与冲突判定)
_STATE_APPEARANCE_FIELDS = (
    "structure_smiles_raw", "structure_origin", "source_refs",
    "representation_fidelity", "original_structure_available",
)


class Ppv1StoreSchemaError(RuntimeError):
    """未知 schema 版本(fail-closed;在写入之前拒绝,文件字节不变)。"""


class Ppv1EventConflict(RuntimeError):
    """同幂等键已提交但内容不同 / 同 state_id 语义不同(不覆盖)。"""

    def __init__(self, event_id: str, detail: dict):
        super().__init__(f"幂等键冲突:{event_id} 已提交但内容不同")
        self.detail = {"event_id": event_id, **detail}


class Ppv1LedgerCorrupt(RuntimeError):
    """重放/读取发现账本不完整或损坏(fail-closed;不默默成功)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class Ppv1ObjectSchemaError(RuntimeError):
    """事务内对象 dict 的 schema/版本未知或缺失(R2-10;写前拒绝)。

    对象字典没有"无版本"的历史格式:缺 schema_version 即非法形状,
    显式拒绝(不静默按当前版本解析);legacy 旧库的兼容路径在
    legacy_reader 的版本化名单,不在此处扩展。
    """

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class Ppv1SubmitContractError(RuntimeError):
    """提交事务参照/语义契约违反(R2-09;结构化,零写入回滚)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _check_object_version(kind: str, version, supported: tuple) -> None:
    """对象版本门(R2-10):未知/缺失 ⇒ 结构化拒绝,写入前拦截。"""
    if version not in supported:
        raise Ppv1ObjectSchemaError(
            f"{kind} schema 版本未知:{version!r}(支持 {list(supported)};"
            "fail-closed,不静默按当前版本写入)",
            {"object_kind": kind, "schema_version": version,
             "supported": list(supported)})


def _split_state_payload(state_dict: dict) -> tuple[dict, dict]:
    semantic = {k: state_dict.get(k) for k in _STATE_SEMANTIC_FIELDS}
    appearance = {k: state_dict.get(k) for k in _STATE_APPEARANCE_FIELDS}
    appearance["state_id"] = state_dict["state_id"]
    return semantic, appearance


def _semantic_conflict_detail(existing: dict, semantic: dict) -> list[str]:
    return sorted(k for k in set(existing) | set(semantic)
                  if existing.get(k) != semantic.get(k))


class PollutantPathwayStore:
    """新模式账本(事件/投影/展开三集合;同事务提交;schema 前置门)。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        path = Path(self.db_path)
        existing = path.is_file()
        if existing:
            # 已有文件:任何 DDL/写入之前验证 schema(F08;字节不变)
            probe = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            probe.row_factory = sqlite3.Row
            try:
                row = probe.execute(
                    "SELECT value FROM meta WHERE key='schema_version'"
                ).fetchone()
                version = row["value"] if row else None
            except sqlite3.Error:
                version = None  # 无 meta 表 → 非本仓账本
            finally:
                probe.close()
            if version not in PPV1_STORE_SUPPORTED_VERSIONS:
                raise Ppv1StoreSchemaError(
                    f"账本 schema 版本未知:{version!r}(支持 "
                    f"{list(PPV1_STORE_SUPPORTED_VERSIONS)};读取在写入"
                    "之前拒绝,文件未被修改)",
                    {"schema_version": version})
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        if existing:
            # 已有库不得被静默改写版本号(不应发生:版本已核对)
            row = self.conn.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
            if row is None or row["value"] != PPV1_STORE_SCHEMA_VERSION:
                self.conn.close()
                raise Ppv1StoreSchemaError(
                    "账本版本核对后发生变化(并发写?;fail-closed)",
                    {"observed": row["value"] if row else None})
        else:
            self.conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES "
                "('schema_version', ?)", (PPV1_STORE_SCHEMA_VERSION,))
        self.conn.commit()

    # ------------------------------------------------------------ 校验

    def verify_schema(self) -> None:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        version = row["value"] if row else None
        if version not in PPV1_STORE_SUPPORTED_VERSIONS:
            raise Ppv1StoreSchemaError(
                f"账本 schema 版本未知:{version!r}(支持 "
                f"{list(PPV1_STORE_SUPPORTED_VERSIONS)};不猜测解析)",
                {"schema_version": version})

    # ------------------------------------------------------------ 状态(语义/出现拆分)

    def put_state(self, state_dict: dict) -> None:
        """ChemicalState 落账(R2-08:语义幂等校验 + 出现记录追加)。

        - 版本门(R2-10):schema_version 未知/缺失 ⇒ 写前拒绝;
        - 语义块(严格分子事实)已存在且不同 → 冲突(真身份碰撞);
          representation_fidelity **不是**语义成分 —— 同图不同来源
          fidelity 共存、互不升级(R2-08);
        - 出现记录(原始串/来源/位置/分轴保真)按内容哈希追加,重复
          幂等,不同来源**全部保留**(不覆盖、不丢失)。
        """
        _check_object_version("chemstate",
                              state_dict.get("schema_version"),
                              (PPV1_CHEMSTATE_SCHEMA_VERSION,))
        semantic, appearance = _split_state_payload(state_dict)
        sid = state_dict["state_id"]
        semantic_json = json.dumps(semantic, ensure_ascii=False,
                                   sort_keys=True)
        appearance_json = json.dumps(appearance, ensure_ascii=False,
                                     sort_keys=True)
        appearance_hash = content_hash(appearance)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT payload FROM states WHERE state_id = ?",
                (sid,)).fetchone()
            if row is not None:
                existing_semantic = json.loads(row["payload"])
                if existing_semantic != semantic:
                    raise Ppv1EventConflict(
                        f"state:{sid}",
                        {"kind": "state_semantic_conflict",
                         "differing_fields": _semantic_conflict_detail(
                             existing_semantic, semantic)})
            else:
                self.conn.execute(
                    "INSERT INTO states (state_id, payload, created_at)"
                    " VALUES (?, ?, ?)",
                    (sid, semantic_json, now_iso()))
            # 出现记录:追加(同哈希幂等;不同来源共存)
            self.conn.execute(
                "INSERT OR IGNORE INTO state_appearances (state_id,"
                " appearance_hash, payload, created_at)"
                " VALUES (?, ?, ?, ?)",
                (sid, appearance_hash, appearance_json, now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_state(self, state_id: str) -> dict | None:
        """读取状态(v3 返回形状,R2-08;消费方兼容说明)。

        返回 dict:
        - **语义事实**(顶层):state_id / smiles_isomeric / cn_identity
          / formal_charge / stereo_information_status /
          isotope_information_status / schema_version —— 严格分子
          事实,与 state_id 一一对应;
        - **appearances**(顶层键):全部出现记录列表(按落账顺序),
          每项含 structure_smiles_raw / structure_origin /
          source_refs(event/position/role)/ **分轴
          representation_fidelity** / original_structure_available;
        - 顶层另镜像**首个**出现的 appearance 字段(含
          representation_fidelity),仅为旧消费方兼容 —— 需要某来源
          的保真度时**必须**按出现取
          `appearances[i]["representation_fidelity"]`,不得把顶层
          镜像当作"该结构在所有来源下的保真度"(R2-08:不把某来源
          的 unknown 升级成另一来源的 full,也不反向降级)。
        """
        row = self.conn.execute(
            "SELECT payload FROM states WHERE state_id = ?",
            (state_id,)).fetchone()
        if row is None:
            return None
        semantic = json.loads(row["payload"])
        appearances = [json.loads(r["payload"]) for r in self.conn.execute(
            "SELECT payload FROM state_appearances WHERE state_id = ?"
            " ORDER BY rowid", (state_id,)).fetchall()]
        out = dict(semantic)
        out["appearances"] = appearances
        if appearances:
            for k in _STATE_APPEARANCE_FIELDS:
                if k in appearances[0]:
                    out[k] = appearances[0][k]
        return out

    def state_appearances(self, state_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT payload FROM state_appearances WHERE state_id = ?"
            " ORDER BY rowid", (state_id,)).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    # ------------------------------------------------------------ 假设(草稿,幂等)

    def put_hypothesis(self, hypothesis_dict: dict,
                       context_hash: str = "") -> None:
        _check_object_version("hypothesis",
                              hypothesis_dict.get("schema_version"),
                              (PPV1_HYPOTHESIS_SCHEMA_VERSION,))
        hid = hypothesis_dict["hypothesis_id"]
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT payload FROM hypotheses WHERE hypothesis_id = ?",
                (hid,)).fetchone()
            if row is not None:
                if content_hash(json.loads(row["payload"])) != content_hash(
                        hypothesis_dict):
                    raise Ppv1EventConflict(
                        f"hypothesis:{hid}", {})
                self.conn.rollback()
                return
            self.conn.execute(
                "INSERT INTO hypotheses (hypothesis_id, parent_path_id,"
                " context_hash, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (hid, hypothesis_dict["parent_path_id"], context_hash,
                 json.dumps(hypothesis_dict, ensure_ascii=False,
                            sort_keys=True), now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_hypothesis(self, hypothesis_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM hypotheses WHERE hypothesis_id = ?",
            (hypothesis_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    # ------------------------------------------------------------ provenance(F10)

    def put_provenance(self, record_id: str, run_id: str,
                       payload: dict) -> None:
        _check_object_version("provenance",
                              payload.get("schema_version"),
                              (PPV1_PROVENANCE_SCHEMA_VERSION,))
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT payload FROM provenance_records WHERE record_id = ?",
                (record_id,)).fetchone()
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if row is not None:
                if content_hash(json.loads(row["payload"])) != content_hash(
                        payload):
                    raise Ppv1EventConflict(
                        f"provenance:{record_id}",
                        {"kind": "provenance_payload_mismatch"})
                self.conn.rollback()
                return
            self.conn.execute(
                "INSERT INTO provenance_records (record_id, run_id, payload,"
                " created_at) VALUES (?, ?, ?, ?)",
                (record_id, run_id, encoded, now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_provenance(self, record_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM provenance_records WHERE record_id = ?",
            (record_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    # ------------------------------------------------------------ 事件提交(R2-09)

    @staticmethod
    def _derived_state_refs(event: PathwayEvent) -> set[str]:
        """参与物引用以 event.participants 实际派生(R2-09)。"""
        return {p["state_ref"] for p in event.participants}

    @staticmethod
    def _product_state_refs(event: PathwayEvent) -> set[str]:
        return {p["state_ref"] for p in event.participants
                if p.get("side") == "product"}

    def _check_hypothesis_event_relation(
            self, eid: str, hypothesis_dict: dict,
            event: PathwayEvent) -> None:
        """事件 ↔ 假设内容关系(R2-09;违反 ⇒ 结构化契约错误)。

        - parent_path_id 一致;
        - participants 非空且与事件参与物一致(计量账目同源);
        - substrate_state_ref 属反应物侧 primary_substrate 锚点。
        """
        if hypothesis_dict.get("parent_path_id") != event.parent_path_id:
            raise Ppv1SubmitContractError(
                f"事件 {eid} 与假设 {event.hypothesis_id} 的 "
                "parent_path_id 不一致",
                {"event_id": eid, "hypothesis_id": event.hypothesis_id,
                 "kind": "hypothesis_parent_mismatch",
                 "event_parent": event.parent_path_id,
                 "hypothesis_parent":
                     hypothesis_dict.get("parent_path_id")})
        hyp_participants = hypothesis_dict.get("participants") or []
        if not hyp_participants:
            raise Ppv1SubmitContractError(
                f"事件 {eid} 关联假设的 participants 为空",
                {"event_id": eid, "hypothesis_id": event.hypothesis_id,
                 "kind": "hypothesis_participants_empty"})
        anchor = any(
            p.get("side") == "reactant"
            and p.get("role") == "primary_substrate"
            and p.get("state_ref") == hypothesis_dict.get(
                "substrate_state_ref")
            for p in hyp_participants)
        if not anchor:
            raise Ppv1SubmitContractError(
                f"事件 {eid} 关联假设的 substrate_state_ref 不属于反应物"
                "侧 primary_substrate 锚点",
                {"event_id": eid, "hypothesis_id": event.hypothesis_id,
                 "kind": "substrate_anchor_mismatch",
                 "substrate_state_ref":
                     hypothesis_dict.get("substrate_state_ref")})
        if canonical_json(hyp_participants) != canonical_json(
                event.participants):
            raise Ppv1SubmitContractError(
                f"事件 {eid} 参与物与假设 {event.hypothesis_id} 的 "
                "participants 不一致",
                {"event_id": eid, "hypothesis_id": event.hypothesis_id,
                 "kind": "hypothesis_participants_mismatch"})

    def _check_projection_scope(self, eid: str, projection: dict,
                                product_refs: set[str]) -> None:
        """投影只指向本事件产物(R2-09)。"""
        max_reportable = projection.get("max_reportable")
        if isinstance(max_reportable, bool) \
                or not isinstance(max_reportable, int) \
                or max_reportable < 1:
            raise Ppv1SubmitContractError(
                f"事件 {eid} 报告投影 max_reportable 非法:"
                f"{max_reportable!r}",
                {"event_id": eid, "kind": "invalid_max_reportable",
                 "max_reportable": max_reportable})
        unknown = [r.get("state_ref") for r in
                   projection.get("product_ranks") or []
                   if r.get("state_ref") not in product_refs]
        if unknown:
            raise Ppv1SubmitContractError(
                f"事件 {eid} 报告投影引用了非本事件产物的状态:"
                f"{sorted(set(unknown))[:5]}",
                {"event_id": eid, "kind": "projection_ref_out_of_products",
                 "unknown_refs": sorted(set(unknown))})

    def _check_expansion_plan(self, eid: str, plan: dict,
                              product_refs: set[str]) -> None:
        """展开计划:产物范围合法、状态互斥、无悬空引用(R2-09)。"""
        from .events import EXPANSION_STATUSES
        seen_refs: set[str] = set()
        for entry in plan.get("entries") or []:
            ref = entry.get("state_ref")
            if ref not in product_refs:
                raise Ppv1SubmitContractError(
                    f"事件 {eid} 展开计划引用了非本事件产物的状态:"
                    f"{ref!r}",
                    {"event_id": eid,
                     "kind": "expansion_ref_out_of_products",
                     "state_ref": ref})
            if ref in seen_refs:
                raise Ppv1SubmitContractError(
                    f"事件 {eid} 展开计划对同一产物 {ref} 给出多个状态"
                    "(expanded/deferred/not_tracked 互斥)",
                    {"event_id": eid, "kind": "expansion_status_conflict",
                     "state_ref": ref})
            seen_refs.add(ref)
            if entry.get("status") not in EXPANSION_STATUSES:
                raise Ppv1SubmitContractError(
                    f"事件 {eid} 展开计划状态非法:{entry.get('status')!r}",
                    {"event_id": eid, "kind": "invalid_expansion_status",
                     "state_ref": ref,
                     "status": entry.get("status")})

    def _collect_state_writes(
            self, eid: str, states: list[dict]) -> tuple[dict, list]:
        """随事务 states → (待插语义表, 待插出现记录)。

        已存在/待插语义相同 ⇒ 幂等;不同 ⇒ 语义冲突(回滚)。
        同一 state_id 多次出现(先保留全部 occurrence 再归并身份,
        R2-08)语义必然一致(由结构派生),不一致即冲突。
        """
        pending_semantics: dict[str, dict] = {}
        appearance_writes: list[tuple[str, str, str]] = []
        for state_dict in states:
            _check_object_version("chemstate",
                                  state_dict.get("schema_version"),
                                  (PPV1_CHEMSTATE_SCHEMA_VERSION,))
            semantic, appearance = _split_state_payload(state_dict)
            sid = state_dict["state_id"]
            known = pending_semantics.get(sid)
            if known is None:
                row = self.conn.execute(
                    "SELECT payload FROM states WHERE state_id = ?",
                    (sid,)).fetchone()
                if row is not None:
                    known = json.loads(row["payload"])
            if known is not None and known != semantic:
                raise Ppv1EventConflict(
                    eid, {"kind": "state_semantic_conflict",
                          "state_id": sid,
                          "differing_fields": _semantic_conflict_detail(
                              known, semantic)})
            pending_semantics[sid] = semantic
            appearance_writes.append((
                sid, content_hash(appearance),
                json.dumps(appearance, ensure_ascii=False, sort_keys=True)))
        return pending_semantics, appearance_writes

    def submit_event(
        self,
        event: PathwayEvent,
        *,
        report_projection: dict,
        expansion_plan: dict,
        states: list[dict],
        hypothesis_dict: dict | None = None,
    ) -> dict:
        """事件 + 投影 + 展开计划 + 参与物状态(+假设)同事务提交。

        事务内契约(R2-09/R2-10;任一违约 ⇒ 结构化错误 + 零写入回滚):
        - 版本门(写前):states/hypothesis/event/投影/计划的对象版本
          必须已知(R2-10);
        - 参与物引用以 event.participants 实际派生:独立
          participant_state_refs 少报/多报 ⇒ 拒绝;全部参与物 state
          必须随事务提供或已在库,且语义与引用身份一致;
        - 事件 ↔ 假设内容关系:parent_path_id 一致、底物锚点属于
          反应物 primary_substrate、participants 非空且与事件一致;
          已存在同 ID 假设时,随事务提交不同内容 ⇒ 冲突(不静默忽略);
        - 投影只指向本事件产物;展开计划产物范围合法、
          expanded/deferred/not_tracked 互斥、无悬空引用;
        - 重放(同幂等键):核验**全部**必要记录(states/
          state_appearances/hypotheses/report_projections/
          expansion_plans)齐全且一致;缺任一 ⇒ Ppv1LedgerCorrupt
          (首版策略:报损坏,不做自动恢复),绝不静默 created=False。
        """
        eid = event.event_id
        semantics = event.event_semantics_hash
        # ---- 版本门:任何写入之前(R2-10)----
        _check_object_version("event", event.schema_version,
                              PPV1_EVENT_SUPPORTED_VERSIONS)
        if hypothesis_dict is not None:
            _check_object_version("hypothesis",
                                  hypothesis_dict.get("schema_version"),
                                  (PPV1_HYPOTHESIS_SCHEMA_VERSION,))
        _check_object_version(
            "report_projection",
            (report_projection or {}).get("projection_version"),
            (PPV1_REPORT_PROJECTION_VERSION,))
        _check_object_version(
            "expansion_plan", (expansion_plan or {}).get("policy_version"),
            (PPV1_EXPANSION_POLICY_VERSION,))
        for state_dict in states or []:
            _check_object_version("chemstate",
                                  state_dict.get("schema_version"),
                                  (PPV1_CHEMSTATE_SCHEMA_VERSION,))

        derived_refs = self._derived_state_refs(event)
        product_refs = self._product_state_refs(event)
        if not event.participants:
            raise Ppv1SubmitContractError(
                f"事件 {eid} participants 为空(计量账目不可为空)",
                {"event_id": eid, "kind": "event_participants_empty"})
        if sorted(set(event.participant_state_refs or [])) != \
                sorted(derived_refs):
            raise Ppv1SubmitContractError(
                f"事件 {eid} 的 participant_state_refs 与 participants "
                "实际派生的引用集不一致(参与物引用以 participants "
                "为准;少报/多报均拒绝)",
                {"event_id": eid, "kind": "participant_state_refs_mismatch",
                 "declared": sorted(set(event.participant_state_refs or [])),
                 "derived_from_participants": sorted(derived_refs)})

        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.conn.execute(
                "SELECT * FROM events WHERE event_id = ?", (eid,)).fetchone()
            if existing is None:
                dup = self.conn.execute(
                    "SELECT event_id FROM events WHERE run_id = ? AND"
                    " parent_path_id = ? AND hypothesis_id = ? AND"
                    " context_hash = ? AND event_semantics_hash = ?",
                    (event.run_id, event.parent_path_id,
                     event.hypothesis_id, event.context_hash, semantics),
                ).fetchone()
                if dup is not None and dup["event_id"] != eid:
                    raise Ppv1EventConflict(
                        dup["event_id"], {"submitted_event_id": eid})
            if existing is not None:
                if existing["event_semantics_hash"] != semantics:
                    raise Ppv1EventConflict(
                        eid, {"kind": "event_semantics_mismatch",
                              "existing_hash":
                                  existing["event_semantics_hash"],
                              "submitted_hash": semantics})
                # ---- 重放:核验全部必要记录(R2-09)----
                # 账本行必须真实存在 —— 随事务再提供的 states 不修补
                # 缺失行(删行后重放 ⇒ 报损坏,不静默成功/不自动恢复)
                self._collect_state_writes(eid, states or [])
                missing_states = [
                    ref for ref in sorted(derived_refs)
                    if self.conn.execute(
                        "SELECT 1 FROM states WHERE state_id = ?",
                        (ref,)).fetchone() is None]
                if missing_states:
                    raise Ppv1LedgerCorrupt(
                        f"重放 {eid} 发现参与物状态行缺失:"
                        f"{missing_states[:5]}(账本不完整;不默默成功)",
                        {"event_id": eid, "table": "states",
                         "missing_state_refs": missing_states})
                no_appearance = [
                    ref for ref in sorted(derived_refs)
                    if self.conn.execute(
                        "SELECT 1 FROM state_appearances WHERE state_id = ?"
                        " LIMIT 1", (ref,)).fetchone() is None]
                if no_appearance:
                    raise Ppv1LedgerCorrupt(
                        f"重放 {eid} 发现状态出现记录缺失:"
                        f"{no_appearance[:5]}(账本不完整;不默默成功)",
                        {"event_id": eid, "table": "state_appearances",
                         "states_without_appearances": no_appearance})
                hyp_row = self.conn.execute(
                    "SELECT payload FROM hypotheses WHERE hypothesis_id ="
                    " ?", (event.hypothesis_id,)).fetchone()
                if hyp_row is None:
                    raise Ppv1LedgerCorrupt(
                        f"重放 {eid} 缺少关联假设行(账本不完整;"
                        "不默默成功)",
                        {"event_id": eid, "table": "hypotheses",
                         "hypothesis_id": event.hypothesis_id})
                stored_hyp = json.loads(hyp_row["payload"])
                if hypothesis_dict is not None:
                    if content_hash(stored_hyp) != content_hash(
                            hypothesis_dict):
                        raise Ppv1EventConflict(
                            eid, {"kind": "hypothesis_payload_mismatch",
                                  "hypothesis_id": event.hypothesis_id})
                self._check_hypothesis_event_relation(eid, stored_hyp,
                                                      event)
                for table, payload in (
                        ("report_projections", report_projection),
                        ("expansion_plans", expansion_plan)):
                    row = self.conn.execute(
                        f"SELECT payload FROM {table} WHERE event_id = ?",
                        (eid,)).fetchone()
                    if row is None:
                        raise Ppv1LedgerCorrupt(
                            f"重放 {eid} 缺少附随记录 {table}(账本不完整;"
                            "不默默成功)", {"event_id": eid, "table": table})
                    if content_hash(json.loads(row["payload"])) != \
                            content_hash(payload):
                        raise Ppv1EventConflict(
                            eid, {"table": table,
                                  "kind": "attached_payload_mismatch"})
                self.conn.rollback()
                return {"created": False, "event_id": eid}
            # ---- 首次提交:先全部校验,后写入(失败零写入)----
            pending_semantics, appearance_writes = \
                self._collect_state_writes(eid, states or [])
            missing_refs = [
                ref for ref in sorted(derived_refs)
                if ref not in pending_semantics
                and self.conn.execute(
                    "SELECT 1 FROM states WHERE state_id = ?",
                    (ref,)).fetchone() is None]
            if missing_refs:
                raise Ppv1LedgerCorrupt(
                    f"事件引用的状态缺失:{sorted(missing_refs)[:5]}"
                    "(事务回滚;不产生悬空引用)",
                    {"event_id": eid, "missing_state_refs":
                        sorted(missing_refs)})
            hyp_row = self.conn.execute(
                "SELECT payload FROM hypotheses WHERE hypothesis_id = ?",
                (event.hypothesis_id,)).fetchone()
            if hyp_row is not None:
                stored_hyp = json.loads(hyp_row["payload"])
                if hypothesis_dict is not None \
                        and content_hash(stored_hyp) != content_hash(
                            hypothesis_dict):
                    raise Ppv1EventConflict(
                        eid, {"kind": "hypothesis_payload_mismatch",
                              "hypothesis_id": event.hypothesis_id,
                              "note": "库中已有同 ID 假设且内容不同;"
                                      "随事务提交的不同内容不静默忽略"})
                self._check_hypothesis_event_relation(eid, stored_hyp,
                                                      event)
            else:
                if hypothesis_dict is None \
                        or hypothesis_dict["hypothesis_id"] != \
                        event.hypothesis_id:
                    raise Ppv1LedgerCorrupt(
                        "事件缺少关联假设(须随事务提供 hypothesis_dict "
                        "或先落账)", {"event_id": eid,
                                       "hypothesis_id":
                                           event.hypothesis_id})
                self._check_hypothesis_event_relation(eid, hypothesis_dict,
                                                      event)
            self._check_projection_scope(eid, report_projection,
                                         product_refs)
            self._check_expansion_plan(eid, expansion_plan, product_refs)
            # ---- 写入(全部校验通过)----
            for sid, semantic in pending_semantics.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO states (state_id, payload,"
                    " created_at) VALUES (?, ?, ?)",
                    (sid, json.dumps(semantic, ensure_ascii=False,
                                     sort_keys=True), now_iso()))
            for sid, appearance_hash, appearance_json \
                    in appearance_writes:
                self.conn.execute(
                    "INSERT OR IGNORE INTO state_appearances (state_id,"
                    " appearance_hash, payload, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (sid, appearance_hash, appearance_json, now_iso()))
            if hyp_row is None:
                self.conn.execute(
                    "INSERT INTO hypotheses (hypothesis_id, parent_path_id,"
                    " context_hash, payload, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (hypothesis_dict["hypothesis_id"],
                     hypothesis_dict["parent_path_id"], event.context_hash,
                     json.dumps(hypothesis_dict, ensure_ascii=False,
                                sort_keys=True), now_iso()))
            self.conn.execute(
                "INSERT INTO events (event_id, run_id, parent_path_id,"
                " hypothesis_id, context_hash, event_semantics_hash,"
                " payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (eid, event.run_id, event.parent_path_id,
                 event.hypothesis_id, event.context_hash, semantics,
                 json.dumps({
                     "schema_version": event.schema_version,
                     "participants": event.participants,
                     "participant_state_refs":
                         event.participant_state_refs,
                     "catalytic_support": event.catalytic_support,
                 }, ensure_ascii=False, sort_keys=True), now_iso()))
            self.conn.execute(
                "INSERT INTO report_projections (event_id, payload,"
                " created_at) VALUES (?, ?, ?)",
                (eid, json.dumps(report_projection, ensure_ascii=False,
                                 sort_keys=True), now_iso()))
            self.conn.execute(
                "INSERT INTO expansion_plans (event_id, payload,"
                " created_at) VALUES (?, ?, ?)",
                (eid, json.dumps(expansion_plan, ensure_ascii=False,
                                 sort_keys=True), now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return {"created": True, "event_id": eid}

    # ------------------------------------------------------------ 查询

    def get_event(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        return dict(row) if row else None

    def find_event(self, run_id: str, parent_path_id: str,
                   hypothesis_id: str, context_hash: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM events WHERE run_id = ? AND parent_path_id = ?"
            " AND hypothesis_id = ? AND context_hash = ?",
            (run_id, parent_path_id, hypothesis_id, context_hash),
        ).fetchone()
        return dict(row) if row else None

    def report_projection(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM report_projections WHERE event_id = ?",
            (event_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def expansion_plan(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM expansion_plans WHERE event_id = ?",
            (event_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_events(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE run_id = ? ORDER BY created_at,"
            " event_id", (run_id,)).fetchall()
        return [dict(r) for r in rows]

    def counts(self) -> dict:
        one = lambda sql: self.conn.execute(sql).fetchone()[0]  # noqa: E731
        return {
            "states": one("SELECT COUNT(*) FROM states"),
            "state_appearances": one(
                "SELECT COUNT(*) FROM state_appearances"),
            "hypotheses": one("SELECT COUNT(*) FROM hypotheses"),
            "events": one("SELECT COUNT(*) FROM events"),
            "report_projections": one(
                "SELECT COUNT(*) FROM report_projections"),
            "expansion_plans": one(
                "SELECT COUNT(*) FROM expansion_plans"),
            "provenance_records": one(
                "SELECT COUNT(*) FROM provenance_records"),
        }

    def close(self) -> None:
        self.conn.close()
