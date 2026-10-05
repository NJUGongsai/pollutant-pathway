"""PollutantPathwayStore — 新模式的独立 SQLite 账本(实施书 §3.1/§5.3,S1)。

- **独立文件**(run 目录内 pollutant_pathway.sqlite):不迁移、不改写
  legacy PathwayStore 的 v43-store-2 账本;schema 未知 fail-closed;
- 事件提交、报告投影、展开计划在同一 SQLite 事务内一致落账;
- 幂等键 (run_id, parent_path_id, hypothesis_id, context_hash,
  event_semantics_hash):同键同内容重放返回已有结果;同键异内容 →
  Ppv1EventConflict(不覆盖);
- ChemicalState 以 state_id 幂等落账(同 id 同内容幂等);
- 草稿识别:states/hypotheses 可先写(草稿),events 表的行即"已提交"
  事实;恢复方读取时以 events 是否有该幂等键判定提交与否(§5.3)。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..domain.models import content_hash, now_iso
from .events import PathwayEvent
from .profile import PPV1_STORE_SCHEMA_VERSION

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
CREATE INDEX IF NOT EXISTS idx_ppv1_events_run
    ON events (run_id, parent_path_id);
CREATE INDEX IF NOT EXISTS idx_ppv1_hyp_parent
    ON hypotheses (parent_path_id);
"""


class Ppv1StoreSchemaError(RuntimeError):
    """未知 schema 版本(fail-closed;不按旧结构静默解析)。"""


class Ppv1EventConflict(RuntimeError):
    """同幂等键已提交但事件内容不同(不覆盖)。"""

    def __init__(self, event_id: str, detail: dict):
        super().__init__(
            f"幂等键冲突:{event_id} 已提交但事件语义不同")
        self.detail = {"event_id": event_id, **detail}


class PollutantPathwayStore:
    """新模式账本(事件/投影/展开三集合;同事务提交)。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self.conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (PPV1_STORE_SCHEMA_VERSION,))
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

    # ------------------------------------------------------------ 草稿(幂等)

    def put_state(self, state_dict: dict) -> None:
        """ChemicalState 落账(同 id 幂等;同 id 异内容冲突)。"""
        sid = state_dict["state_id"]
        payload_hash = content_hash(state_dict)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT payload FROM states WHERE state_id = ?",
                (sid,)).fetchone()
            if row is not None:
                if content_hash(__import__("json").loads(row["payload"])) \
                        != payload_hash:
                    raise Ppv1EventConflict(
                        f"state:{sid}",
                        {"existing_hash": row["payload"][:16],
                         "submitted_hash": payload_hash})
                self.conn.rollback()
                return
            import json

            self.conn.execute(
                "INSERT INTO states (state_id, payload, created_at)"
                " VALUES (?, ?, ?)",
                (sid, json.dumps(state_dict, ensure_ascii=False,
                                 sort_keys=True), now_iso()))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def put_hypothesis(self, hypothesis_dict: dict,
                       context_hash: str = "") -> None:
        hid = hypothesis_dict["hypothesis_id"]
        import json

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

    # ------------------------------------------------------------ 事件提交

    def submit_event(
        self,
        event: PathwayEvent,
        *,
        report_projection: dict,
        expansion_plan: dict,
        states: list[dict],
    ) -> dict:
        """事件 + 投影 + 展开计划 + 参与物状态 同事务提交(幂等)。

        同幂等键重放:返回已有结果(created=False);同键不同事件语义 →
        Ppv1EventConflict。投影/展开计划属事件附随内容:同键重放时按
        内容哈希核对,不同内容报冲突(不得借重放改投影)。
        """
        import json

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
                    # 同语义不同 ID(不应发生:ID 派生自同键)——防御性冲突
                    raise Ppv1EventConflict(
                        dup["event_id"], {"submitted_event_id": eid})
            if existing is not None:
                if existing["event_semantics_hash"] != semantics:
                    raise Ppv1EventConflict(
                        eid, {"existing_hash": existing[
                            "event_semantics_hash"],
                            "submitted_hash": semantics})
                # 投影/展开内容核对(同键不同内容 = 冲突)
                for table, payload in (("report_projections",
                                        report_projection),
                                       ("expansion_plans", expansion_plan)):
                    row = self.conn.execute(
                        f"SELECT payload FROM {table} WHERE event_id = ?",
                        (eid,)).fetchone()
                    if row is not None and content_hash(
                            json.loads(row["payload"])) != content_hash(
                            payload):
                        raise Ppv1EventConflict(
                            eid, {"table": table,
                                  "reason": "attached_payload_mismatch"})
                self.conn.rollback()
                return {"created": False, "event_id": eid}
            for state_dict in states:
                sid = state_dict["state_id"]
                self.conn.execute(
                    "INSERT OR IGNORE INTO states (state_id, payload,"
                    " created_at) VALUES (?, ?, ?)",
                    (sid, json.dumps(state_dict, ensure_ascii=False,
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
        import json

        return json.loads(row["payload"]) if row else None

    def expansion_plan(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM expansion_plans WHERE event_id = ?",
            (event_id,)).fetchone()
        import json

        return json.loads(row["payload"]) if row else None

    def get_state(self, state_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM states WHERE state_id = ?",
            (state_id,)).fetchone()
        import json

        return json.loads(row["payload"]) if row else None

    def get_hypothesis(self, hypothesis_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM hypotheses WHERE hypothesis_id = ?",
            (hypothesis_id,)).fetchone()
        import json

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
            "hypotheses": one("SELECT COUNT(*) FROM hypotheses"),
            "events": one("SELECT COUNT(*) FROM events"),
            "report_projections": one(
                "SELECT COUNT(*) FROM report_projections"),
            "expansion_plans": one("SELECT COUNT(*) FROM expansion_plans"),
        }

    def close(self) -> None:
        self.conn.close()
