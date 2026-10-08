"""PathwayStore — 化学路径图的 SQLite 账本(领域事实,非执行状态)。

职责(任务书 §1.1):
- 保存 run_id、root、compounds、reaction_events、event_products、
  path_instances、frontier 状态与 graph_revision;
- 同一幂等键重复提交返回已提交结果;同键内容变化报冲突;
- 事件、产物、路径实例在同一 SQLite 事务内提交,并推进 graph_revision;
- 路径状态分清(frontier/expanded/deferred/awaiting_prediction/dead_end/
  depth_limit/rejected),不删除任何候选。

path_id / event_id 是由内容派生的稳定 ID;S11 等展示名由 domain.pathway
按需计算,本表不存、更不解析。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..domain.models import (
    PATH_STATUS_DEFERRED,
    PATH_STATUS_EXPANDED,
    PATH_STATUS_FRONTIER,
    PATH_STATUS_REJECTED,
    Compound,
    PathInstance,
    ReactionEvent,
    content_hash,
    stable_id,
)

STORE_SCHEMA_VERSION = "v43-store-2"  # v2:reaction_events.model_ref(模型决策引用)


class EventConflict(RuntimeError):
    """同一幂等键已提交但内容不同(fail-closed,不静默覆盖)。"""

    def __init__(self, event_id: str, detail: dict) -> None:
        super().__init__(f"幂等键冲突:{event_id} 已提交但证据内容不同")
        self.detail = {"event_id": event_id, **detail}


def root_path_id(run_id: str, root_cn: str) -> str:
    return stable_id("p", run_id, "root", root_cn)


def event_id_for(run_id: str, parent_path_id: str, substrate_identity: str,
                 evidence_id: str) -> str:
    return stable_id("ev", run_id, parent_path_id, substrate_identity, evidence_id)


def product_path_id(run_id: str, event_id: str, position: int) -> str:
    return stable_id("p", run_id, event_id, str(position))


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compounds (
    cn             TEXT PRIMARY KEY,
    example_smiles TEXT NOT NULL,
    first_path_id  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reaction_events (
    event_id           TEXT PRIMARY KEY,
    run_id             TEXT NOT NULL,
    parent_path_id     TEXT NOT NULL,
    substrate_identity TEXT NOT NULL,
    evidence_id        TEXT NOT NULL,
    evidence_hash      TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    kind               TEXT NOT NULL,
    condition_fit      TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    UNIQUE (run_id, parent_path_id, substrate_identity, evidence_id)
);
CREATE TABLE IF NOT EXISTS event_products (
    event_id       TEXT NOT NULL,
    position       INTEGER NOT NULL,
    product_identity TEXT NOT NULL,
    product_smiles TEXT NOT NULL,
    product_smiles_full TEXT NOT NULL,
    PRIMARY KEY (event_id, position)
);
CREATE TABLE IF NOT EXISTS path_instances (
    path_id           TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL,
    parent_path_id    TEXT,
    event_id          TEXT,
    product_position  INTEGER,
    substrate_identity TEXT NOT NULL,
    status            TEXT NOT NULL,
    depth             INTEGER NOT NULL,
    status_reason     TEXT NOT NULL DEFAULT '',
    seq               INTEGER NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_paths_run_status
    ON path_instances (run_id, status, seq);
CREATE INDEX IF NOT EXISTS idx_paths_parent
    ON path_instances (parent_path_id);
"""


class PathwayStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (STORE_SCHEMA_VERSION,),
        )
        self.conn.commit()

    def _migrate(self) -> None:
        """轻量迁移:v1(v43-store-1)账本补 model_ref 列(v2 语义)。

        v1 列语义不变,补列后旧库可读可写;跨版本 run 的恢复仍被 run
        身份核对拒绝,这里的迁移只为账本文件本身可检查、可追加。
        """
        cols = {
            r["name"] for r in self.conn.execute(
                "PRAGMA table_info(reaction_events)").fetchall()
        }
        if "model_ref" not in cols:
            self.conn.execute(
                "ALTER TABLE reaction_events ADD COLUMN model_ref"
                " TEXT NOT NULL DEFAULT ''"
            )

    # ------------------------------------------------------------ 事务辅助

    def _begin(self) -> None:
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN IMMEDIATE")

    def _next_seq(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(MAX(seq), -1) + 1 AS n FROM path_instances "
            "WHERE run_id = (SELECT value FROM meta WHERE key='current_run')"
        ).fetchone()
        return int(row["n"])

    def graph_revision(self) -> int:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='graph_revision'"
        ).fetchone()
        return int(row["value"]) if row else 0

    # ------------------------------------------------------------ run / root

    def ensure_run(self, run_id: str, root_smiles: str, root_cn: str) -> str:
        """登记 run 与根路径(幂等);返回根 path_id。"""
        rid = root_path_id(run_id, root_cn)
        self._begin()
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('current_run', ?)",
                (run_id,),
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO compounds (cn, example_smiles, first_path_id)"
                " VALUES (?, ?, ?)",
                (root_cn, root_smiles, rid),
            )
            row = self.conn.execute(
                "SELECT path_id FROM path_instances WHERE path_id = ?", (rid,)
            ).fetchone()
            if row is None:
                self.conn.execute(
                    "INSERT INTO path_instances (path_id, run_id, parent_path_id,"
                    " event_id, product_position, substrate_identity, status,"
                    " depth, status_reason, seq, created_at)"
                    " VALUES (?, ?, NULL, NULL, NULL, ?, ?, 0, '', 0,"
                    " datetime('now'))",
                    (rid, run_id, root_cn, PATH_STATUS_FRONTIER),
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return rid

    def current_run(self) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key='current_run'"
        ).fetchone()
        return row["value"] if row else None

    # ------------------------------------------------------------ 查询

    def get_path(self, path_id: str) -> PathInstance | None:
        row = self.conn.execute(
            "SELECT * FROM path_instances WHERE path_id = ?", (path_id,)
        ).fetchone()
        return self._row_to_path(row) if row else None

    def list_paths(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM path_instances WHERE run_id = ? ORDER BY seq", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def list_frontier(self, run_id: str) -> list[PathInstance]:
        rows = self.conn.execute(
            "SELECT * FROM path_instances WHERE run_id = ? AND status = ?"
            " ORDER BY seq",
            (run_id, PATH_STATUS_FRONTIER),
        ).fetchall()
        return [self._row_to_path(r) for r in rows]

    def get_event(self, event_id: str) -> ReactionEvent | None:
        row = self.conn.execute(
            "SELECT * FROM reaction_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def event_products(self, event_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? ORDER BY position",
            (event_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def events(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM reaction_events WHERE run_id = ? ORDER BY created_at,"
            " event_id",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_events_by_kind(self, kind: str) -> int:
        """按 kind 计数(持久事实源:提案预算记账用)。"""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM reaction_events WHERE kind = ?", (kind,)
        ).fetchone()
        return int(row[0])

    def get_compound(self, cn: str) -> Compound | None:
        row = self.conn.execute(
            "SELECT * FROM compounds WHERE cn = ?", (cn,)
        ).fetchone()
        return Compound(**dict(row)) if row else None

    def counts(self) -> dict:
        one = lambda sql: self.conn.execute(sql).fetchone()[0]  # noqa: E731
        return {
            "compounds": one("SELECT COUNT(*) FROM compounds"),
            "reaction_events": one("SELECT COUNT(*) FROM reaction_events"),
            "event_products": one("SELECT COUNT(*) FROM event_products"),
            "path_instances": one("SELECT COUNT(*) FROM path_instances"),
            "frontier": one(
                "SELECT COUNT(*) FROM path_instances WHERE status='frontier'"
            ),
            "graph_revision": self.graph_revision(),
        }

    # ------------------------------------------------------------ 提交

    def submit_event(
        self,
        *,
        run_id: str,
        parent_path_id: str,
        substrate_identity: str,
        evidence: dict,
        products: list[dict],
        expandable_path_ids: list[str],
        deferred_path_ids: list[str],
        model_ref: str = "",
    ) -> dict:
        """提交 反应事件 + 有序产物 + 产物路径实例(单事务,幂等)。

        - 幂等键 (run_id, parent_path_id, substrate_identity, evidence_id):
          已提交且证据哈希一致 → 返回已有结果(created=False),不再重复入账;
        - 同键不同内容 → EventConflict;
        - 每个产物一条 PathInstance(不同路线各自入边);产物路径状态由调用方
          传入的 expandable / deferred 名单决定(frontier 或 deferred);
        - model_ref:模型决策引用(ARCHITECTURE §6 事件保存模型决策引用;
          确定性通路为空串)。
        """
        evidence_id = evidence["evidence_id"]
        # 证据内容哈希:优先用检索方写入的 _content_hash;裸证据卡(测试/
        # 直调)则就地计算 —— 排除时间戳等易变字段,保证幂等判定一致
        ev_hash = evidence.get("_content_hash")
        if not ev_hash:
            ev_hash = content_hash(
                {k: v for k, v in evidence.items()
                 if k not in ("created_at", "_content_hash")}
            )
        eid = event_id_for(run_id, parent_path_id, substrate_identity, evidence_id)

        self._begin()
        try:
            existing = self.conn.execute(
                "SELECT * FROM reaction_events WHERE event_id = ?", (eid,)
            ).fetchone()
            if existing is not None:
                if existing["evidence_hash"] != ev_hash:
                    self.conn.rollback()
                    raise EventConflict(
                        eid,
                        {"existing_hash": existing["evidence_hash"],
                         "submitted_hash": ev_hash},
                    )
                result = self._existing_event_result(eid)
                self.conn.rollback()  # 只读重放,不开新事务
                return result

            seq_base = self._next_seq()
            cur = self.conn.execute(
                "INSERT INTO reaction_events (event_id, run_id, parent_path_id,"
                " substrate_identity, evidence_id, evidence_hash, source_id,"
                " kind, condition_fit, model_ref, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (eid, run_id, parent_path_id, substrate_identity, evidence_id,
                 ev_hash, evidence.get("source_id", ""), evidence["kind"],
                 evidence.get("condition_fit", "unknown"), model_ref),
            )
            assert cur.rowcount == 1
            # 产物保留其在证据卡中的**原始位次**(前序产物被校验拒绝时位次
            # 稀疏但不重排):路径 ID、event_products.position、展示名全部
            # 以原始位次为准,绝不按提交列表重新编号
            expandable_set = set(expandable_path_ids)
            deferred_set = set(deferred_path_ids)
            for order_index, prod in enumerate(products):
                pos = int(prod["position"])
                pcn = prod["product_identity"]
                pid = product_path_id(run_id, eid, pos)
                self.conn.execute(
                    "INSERT OR IGNORE INTO compounds (cn, example_smiles,"
                    " first_path_id) VALUES (?, ?, ?)",
                    (pcn, prod.get("product_smiles_full", prod["product_smiles"]),
                     pid),
                )
                self.conn.execute(
                    "INSERT INTO event_products (event_id, position,"
                    " product_identity, product_smiles, product_smiles_full)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (eid, pos, pcn, prod["product_smiles"],
                     prod.get("product_smiles_full", prod["product_smiles"])),
                )
                if pid in expandable_set:
                    status = PATH_STATUS_FRONTIER
                elif pid in deferred_set:
                    status = PATH_STATUS_DEFERRED
                else:
                    status = PATH_STATUS_REJECTED
                self.conn.execute(
                    "INSERT INTO path_instances (path_id, run_id, parent_path_id,"
                    " event_id, product_position, substrate_identity, status,"
                    " depth, status_reason, seq, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?, datetime('now'))",
                    (pid, run_id, parent_path_id, eid, pos, pcn,
                     status, seq_base + order_index),
                )
            parent_row = self.conn.execute(
                "SELECT depth FROM path_instances WHERE path_id = ?",
                (parent_path_id,),
            ).fetchone()
            parent_depth = int(parent_row["depth"]) if parent_row else 0
            self.conn.execute(
                "UPDATE path_instances SET depth = ? WHERE parent_path_id = ?",
                (parent_depth + 1, parent_path_id),
            )
            self.conn.execute(
                "UPDATE path_instances SET status = ?, status_reason = ?"
                " WHERE path_id = ?",
                (PATH_STATUS_EXPANDED, "committed_event", parent_path_id),
            )
            rev = self.graph_revision() + 1
            self.conn.execute(
                "INSERT INTO meta (key, value) VALUES ('graph_revision', ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(rev),),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        result = self._existing_event_result(eid)
        result["created"] = True
        return result

    def set_path_status(self, path_id: str, status: str, reason: str = "") -> None:
        self._begin()
        try:
            cur = self.conn.execute(
                "UPDATE path_instances SET status = ?, status_reason = ?"
                " WHERE path_id = ?",
                (status, reason, path_id),
            )
            if cur.rowcount != 1:
                self.conn.rollback()
                raise KeyError(f"路径不存在:{path_id}")
            self.conn.commit()
        except Exception:
            if self.conn.in_transaction:
                self.conn.rollback()
            raise

    def refresh_depths(self, run_id: str) -> None:
        """按父链重算全部路径深度(防 UPDATE 批量语义偏差;提交后调用)。"""
        paths = {p["path_id"]: p for p in self.list_paths(run_id)}
        changed = False
        for pid, p in paths.items():
            depth, cur, hops = 0, p, 0
            while cur["parent_path_id"] is not None:
                cur = paths[cur["parent_path_id"]]
                depth += 1
                hops += 1
                if hops > len(paths):
                    raise ValueError("路径父链出现环")
            if depth != p["depth"]:
                self.conn.execute(
                    "UPDATE path_instances SET depth = ? WHERE path_id = ?",
                    (depth, pid),
                )
                changed = True
        if changed:
            self.conn.commit()

    # ------------------------------------------------------------ 内部

    def _existing_event_result(self, event_id: str) -> dict:
        event = self.get_event(event_id)
        products = self.event_products(event_id)
        paths = self.conn.execute(
            "SELECT * FROM path_instances WHERE event_id = ? ORDER BY seq",
            (event_id,),
        ).fetchall()
        return {
            "created": False,
            "event_id": event_id,
            "event": dict(event.__dict__) if event else None,
            "products": products,
            "path_ids": [dict(r)["path_id"] for r in paths],
        }

    @staticmethod
    def _row_to_path(row: sqlite3.Row) -> PathInstance:
        return PathInstance(
            path_id=row["path_id"], run_id=row["run_id"],
            parent_path_id=row["parent_path_id"], event_id=row["event_id"],
            product_position=row["product_position"],
            substrate_identity=row["substrate_identity"], status=row["status"],
            depth=row["depth"], status_reason=row["status_reason"],
            seq=row["seq"], created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> ReactionEvent:
        return ReactionEvent(
            event_id=row["event_id"], run_id=row["run_id"],
            parent_path_id=row["parent_path_id"],
            substrate_identity=row["substrate_identity"],
            evidence_id=row["evidence_id"], evidence_hash=row["evidence_hash"],
            source_id=row["source_id"], kind=row["kind"],
            condition_fit=row["condition_fit"], created_at=row["created_at"],
            model_ref=row["model_ref"] if "model_ref" in row.keys() else "",
        )

    def close(self) -> None:
        self.conn.close()
