"""PollutantPathwayStore — 新模式的独立 SQLite 账本(v2 回修,S1)。

v2(ppv1-store-2,2026-10-05 回修)相对 v1 的变化(F04/F07/F08/F10):
- **schema 前置门(F08)**:打开已有文件时先读 meta.schema_version,
  未知版本在**任何 DDL/写入之前**拒绝且文件字节不变;只有新文件才
  初始化建表(区分新库初始化与已有库读取);
- **语义/出现记录拆分(F04)**:states 表只存结构语义(state_id 的
  身份事实);structure_smiles_raw/origin/source_refs 是**出现记录**,
  存 state_appearances 追加表 —— 同一结构在下一步作为底物时来源引用
  不同不再构成身份冲突,多次来源全部保留(不冲突、不覆盖、不丢失);
- **事务参照完整性(F07)**:submit_event 在同一事务内验证底物/参与物
  状态引用齐全且语义一致、事件与假设关联、投影/展开附随记录存在;
  重放遇附随记录缺失 → 账本损坏错误,不默默成功;同一 state 的既有
  语义内容不相容即回滚(不再 INSERT OR IGNORE 跳过核对);
- **provenance 表(F10)**:导入/审计的来源细分记录持久保存,可按
  记录 ID 幂等重放。

既有不变量:独立文件(run 目录内 pollutant_pathway.sqlite),不迁移、
不改写 legacy v43-store-* 账本;事件提交/投影/展开计划同事务一致;
幂等键 (run_id, parent_path_id, hypothesis_id, context_hash,
event_semantics_hash);同键异内容 Ppv1EventConflict(不覆盖)。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..domain.models import content_hash, now_iso
from .events import PathwayEvent
from .profile import PPV1_STORE_SCHEMA_VERSION

PPV1_STORE_SUPPORTED_VERSIONS = ("ppv1-store-2",)

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

# ChemicalState 的结构语义字段(身份事实;参与冲突判定)
_STATE_SEMANTIC_FIELDS = (
    "state_id", "smiles_isomeric", "cn_identity", "formal_charge",
    "stereo_information_status", "isotope_information_status",
    "representation_fidelity", "schema_version",
)
# 出现记录字段(同一结构不同来路各自保留;不参与冲突判定)
_STATE_APPEARANCE_FIELDS = (
    "structure_smiles_raw", "structure_origin", "source_refs",
    "original_structure_available",
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


def _split_state_payload(state_dict: dict) -> tuple[dict, dict]:
    semantic = {k: state_dict.get(k) for k in _STATE_SEMANTIC_FIELDS}
    appearance = {k: state_dict.get(k) for k in _STATE_APPEARANCE_FIELDS}
    appearance["state_id"] = state_dict["state_id"]
    return semantic, appearance


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
        if version != PPV1_STORE_SCHEMA_VERSION:
            raise Ppv1StoreSchemaError(
                f"账本 schema 版本未知:{version!r}(支持 "
                f"{PPV1_STORE_SCHEMA_VERSION};不猜测解析)",
                {"schema_version": version})

    # ------------------------------------------------------------ 状态(语义/出现拆分)

    def put_state(self, state_dict: dict) -> None:
        """ChemicalState 落账(F04:语义幂等校验 + 出现记录追加)。

        - 语义块(state_id 的身份事实)已存在且不同 → 冲突(真身份碰撞);
        - 出现记录(原始串/来源/出现位置)按内容哈希追加,重复幂等,
          不同来源**全部保留**(不覆盖、不丢失)。
        """
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
                    differing = sorted(
                        k for k in set(existing_semantic) | set(semantic)
                        if existing_semantic.get(k) != semantic.get(k))
                    raise Ppv1EventConflict(
                        f"state:{sid}",
                        {"kind": "state_semantic_conflict",
                         "differing_fields": differing})
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
        """读取状态(语义 + 出现记录列表;重组成 ChemicalState 形状)。"""
        row = self.conn.execute(
            "SELECT payload FROM states WHERE state_id = ?",
            (state_id,)).fetchone()
        if row is None:
            return None
        semantic = json.loads(row["payload"])
        appearances = [json.loads(r["payload"]) for r in self.conn.execute(
            "SELECT payload FROM state_appearances WHERE state_id = ?",
            (state_id,)).fetchall()]
        out = dict(semantic)
        # 出现记录:首个作为主形状,全部出现列表附加(不丢信息)
        out["appearances"] = appearances
        if appearances:
            for k in _STATE_APPEARANCE_FIELDS:
                if k in appearances[0]:
                    out[k] = appearances[0][k]
        return out

    def state_appearances(self, state_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT payload FROM state_appearances WHERE state_id = ?",
            (state_id,)).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    # ------------------------------------------------------------ 假设(草稿,幂等)

    def put_hypothesis(self, hypothesis_dict: dict,
                       context_hash: str = "") -> None:
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

    # ------------------------------------------------------------ 事件提交(F07 完整性)

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

        事务内参照完整性(F07):
        - 事件引用的全部 participant_state_refs 必须随事务提供或在库中
          已存在;随事务提供的 state 语义与库中已有语义冲突 → 回滚;
        - 事件与假设关联:hypothesis_dict 随事务写入,或已存在于库,
          缺失即回滚;
        - 重放(同幂等键)时投影/展开附随记录必须存在且内容一致:
          行缺失 → Ppv1LedgerCorrupt(账本损坏),不默默成功。
        """
        eid = event.event_id
        semantics = event.event_semantics_hash
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
                # 重放:附随记录齐全性(F07)—— 缺失 = 账本损坏
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
            # ---- 参照完整性:全部参与物状态必须可用 ----
            provided_semantics: dict[str, dict] = {}
            for state_dict in states:
                semantic, appearance = _split_state_payload(state_dict)
                sid = state_dict["state_id"]
                row = self.conn.execute(
                    "SELECT payload FROM states WHERE state_id = ?",
                    (sid,)).fetchone()
                if row is not None:
                    existing_semantic = json.loads(row["payload"])
                    if existing_semantic != semantic:
                        raise Ppv1EventConflict(
                            eid, {"kind": "state_semantic_conflict",
                                  "state_id": sid})
                else:
                    provided_semantics[sid] = semantic
                self.conn.execute(
                    "INSERT OR IGNORE INTO state_appearances (state_id,"
                    " appearance_hash, payload, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (sid, content_hash(appearance),
                     json.dumps(appearance, ensure_ascii=False,
                                sort_keys=True), now_iso()))
            missing_refs = [
                ref for ref in event.participant_state_refs
                if ref not in provided_semantics and self.conn.execute(
                    "SELECT 1 FROM states WHERE state_id = ?",
                    (ref,)).fetchone() is None]
            if missing_refs:
                raise Ppv1LedgerCorrupt(
                    f"事件引用的状态缺失:{sorted(missing_refs)[:5]}"
                    "(事务回滚;不产生悬空引用)",
                    {"event_id": eid, "missing_state_refs":
                        sorted(missing_refs)})
            for sid, semantic in provided_semantics.items():
                self.conn.execute(
                    "INSERT INTO states (state_id, payload, created_at)"
                    " VALUES (?, ?, ?)",
                    (sid, json.dumps(semantic, ensure_ascii=False,
                                     sort_keys=True), now_iso()))
            # ---- 事件与假设关联 ----
            hyp_row = self.conn.execute(
                "SELECT 1 FROM hypotheses WHERE hypothesis_id = ?",
                (event.hypothesis_id,)).fetchone()
            if hyp_row is None:
                if hypothesis_dict is None \
                        or hypothesis_dict["hypothesis_id"] != \
                        event.hypothesis_id:
                    raise Ppv1LedgerCorrupt(
                        "事件缺少关联假设(须随事务提供 hypothesis_dict "
                        "或先落账)", {"event_id": eid,
                                   "hypothesis_id": event.hypothesis_id})
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
            "expansion_plans": one("SELECT COUNT(*) FROM expansion_plans"),
            "provenance_records": one(
                "SELECT COUNT(*) FROM provenance_records"),
        }

    def close(self) -> None:
        self.conn.close()
