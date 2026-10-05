"""legacy 只读适配 — 旧 v43 账本到新表示(实施书 §3.1/§11 S1)。

- **只读**:以 sqlite 只读 URI 打开旧 pathway.sqlite,不经过
  PathwayStore 构造(其建表/迁移有写副作用);本模块零写回 —— 旧
  run、封存资产、旧评测程序不回写,历史导入输出写新模式自己的库/对象;
- 旧数据读出后按新表示恢复,保留原始引用与不确定字段:
  * 产物侧结构 = event_products.product_smiles_full(存档形恢复,
    representation_fidelity=archive_recovered,不冒称原实验全部结构
    细节已知);
  * 反应物侧:父路径若为事件产物 → 用其存档结构;根路径 → run
    identity inputs.root_smiles;均不可得时才退 legacy_cn_only;
  * novel 平列表(一个 evidence 多产物、无共同产物分组信息)→
    一个假设挂 legacy_relationship_unspecified,不静默拆分、不重解释
    (A04);
  * kind/source_id/match_type/asset_sources 经 provenance 映射细分,
    原字段保留。
- 旧账本 schema 未知 → fail-closed(不做"默认当作完整新契约"的读取)。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..domain.models import EVIDENCE_KIND_NOVEL, stable_id
from .chemstate import (
    REPRESENTATION_ARCHIVE_RECOVERED,
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    build_chemical_state,
    build_chemical_state_from_cn_only,
)
from .events import (
    build_expansion_plan,
    build_pathway_event,
    build_report_projection,
)
from .hypothesis import (
    PARTICIPANT_LIST_UNKNOWN,
    PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    COEFFICIENT_UNKNOWN,
    Participant,
    build_hypothesis,
)
from .provenance import map_legacy_card

SUPPORTED_LEGACY_STORE_VERSIONS = ("v43-store-1", "v43-store-2")


class LegacyStoreError(RuntimeError):
    """旧账本不可读/schema 未知/结构缺失(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _read_only_conn(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise LegacyStoreError(
            f"旧账本不存在:{path}", {"path": str(path)})
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def read_legacy_events(run_dir: str | Path) -> list[dict]:
    """只读列出旧账本事件(含产物行;零写回)。"""
    conn = _read_only_conn(Path(run_dir) / "pathway.sqlite")
    try:
        meta = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        version = meta["value"] if meta else None
        if version not in SUPPORTED_LEGACY_STORE_VERSIONS:
            raise LegacyStoreError(
                f"旧账本 schema 版本未知:{version!r}(支持 "
                f"{SUPPORTED_LEGACY_STORE_VERSIONS};fail-closed 不猜)",
                {"schema_version": version})
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM reaction_events ORDER BY created_at, event_id"
        ).fetchall()]
        for ev in events:
            ev["products"] = [dict(r) for r in conn.execute(
                "SELECT * FROM event_products WHERE event_id = ?"
                " ORDER BY position", (ev["event_id"],)).fetchall()]
        return events
    finally:
        conn.close()


def _legacy_root_smiles(run_dir: Path) -> str | None:
    ident = run_dir / "run_identity.json"
    if not ident.is_file():
        return None
    try:
        return (json.loads(ident.read_text(encoding="utf-8"))
                .get("inputs", {}).get("root_smiles"))
    except Exception:
        return None


def _substrate_structure_for_path(
    conn: sqlite3.Connection, run_dir: Path, path_id: str,
) -> tuple[str, bool, bool]:
    """父路径底物结构:(structure, is_archive_recovered, is_root)。

    父路径为事件产物 → 存档形;根路径 → run identity 原始输入
    (origin=raw_input);都不可得 → (CN, False, False)(调用方退
    legacy_cn_only)。
    """
    row = conn.execute(
        "SELECT * FROM path_instances WHERE path_id = ?", (path_id,)).fetchone()
    if row is None:
        raise LegacyStoreError(
            f"旧账本缺路径:{path_id}", {"path_id": path_id})
    if row["event_id"] is not None and row["product_position"] is not None:
        prod = conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? AND"
            " position = ?",
            (row["event_id"], row["product_position"])).fetchone()
        if prod is not None:
            return (prod["product_smiles_full"] or prod["product_smiles"],
                    True, False)
    root_smiles = _legacy_root_smiles(run_dir)
    if root_smiles:
        return root_smiles, False, True
    return row["substrate_identity"], False, False


def import_legacy_event(
    run_dir: str | Path,
    legacy_event: dict,
    *,
    new_run_id: str,
) -> dict:
    """单条旧事件 → 新表示(hypothesis + 事件 + 缺省投影/展开 + 状态)。

    返回 {"hypothesis", "event", "report_projection", "expansion_plan",
    "states", "provenance", "uncertainty_notes"}。缺省投影/展开计划只
    是**只读导入占位**(全部产物位次=legacy 位次、展开状态=not_tracked,
    原因 legacy_import_no_expansion_info);真实报告/展开决策不在此猜。
    novel 平列表:一个假设含全部产物,legacy_relationship_unspecified。
    """
    run_dir = Path(run_dir)
    conn = _read_only_conn(run_dir / "pathway.sqlite")
    try:
        substrate_smiles, recovered, is_root = \
            _substrate_structure_for_path(
                conn, run_dir, legacy_event["parent_path_id"])
        substrate_is_cn_only = (not is_root and not recovered
                                and substrate_smiles ==
                                legacy_event["substrate_identity"])
    finally:
        conn.close()

    uncertainty_notes: list[str] = []
    if substrate_is_cn_only:
        substrate_state = build_chemical_state_from_cn_only(
            legacy_event["substrate_identity"],
            source_refs=[{"role": "legacy_path_substrate",
                          "path_id": legacy_event["parent_path_id"]}])
        uncertainty_notes.append(
            "substrate_structure_legacy_cn_only:历史路径只余 CN,结构/立体未知")
    else:
        substrate_state = build_chemical_state(
            substrate_smiles,
            STRUCTURE_ORIGIN_RAW_INPUT if is_root
            else STRUCTURE_ORIGIN_SOURCE_PRODUCT,
            source_refs=[{
                "role": "legacy_path_substrate",
                "path_id": legacy_event["parent_path_id"],
                "archive_recovered": recovered,
            }],
            representation_fidelity=(
                REPRESENTATION_ARCHIVE_RECOVERED if recovered
                else "full_parse"))

    participants: list[Participant] = [
        Participant(
            state_ref=substrate_state.state_id,
            side=PARTICIPANT_SIDE_REACTANT,
            role=PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
            coefficient=None, coefficient_status=COEFFICIENT_UNKNOWN,
        )
    ]
    product_states = {}
    for prod in legacy_event.get("products", []):
        full = prod.get("product_smiles_full") or prod.get("product_smiles")
        state = build_chemical_state(
            full, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
            source_refs=[{"role": "legacy_event_product",
                          "event_id": legacy_event["event_id"],
                          "position": prod.get("position")}],
            representation_fidelity=REPRESENTATION_ARCHIVE_RECOVERED)
        product_states[state.state_id] = state
        participants.append(Participant(
            state_ref=state.state_id, side=PARTICIPANT_SIDE_PRODUCT,
            role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
            coefficient=None, coefficient_status=COEFFICIENT_UNKNOWN,
        ))

    # 平列表语义:全部产物归入同一假设;novel 显式挂牌,其余 kind 的
    # 多产物记录(同一已记录反应 ID 聚合)在 legacy 语义中即"同一反应
    # 共同产物" —— 但导入侧不重解释,统一保留 unknown 列表状态与来源
    # 引用,由后续有来源的审核确认
    legacy_novel = legacy_event.get("kind") == EVIDENCE_KIND_NOVEL
    relationship_status = ("legacy_relationship_unspecified"
                           if legacy_novel else "")
    if legacy_novel:
        uncertainty_notes.append(
            "legacy_novel_flat_product_list:历史 novel 平列表语义不明确,"
            "不猜共同产物分组,不拆成单产物反应")
    context_hash = "legacy-import"  # 导入侧无原上下文:显式常量,不伪造

    hypothesis = build_hypothesis(
        parent_path_id=legacy_event["parent_path_id"],
        substrate_state_ref=substrate_state.state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_UNKNOWN,
        step_scope="unknown",
        provenance_refs=[legacy_event["evidence_id"]],
        legacy_relationship_status=relationship_status,
        origin_group_key=legacy_event["evidence_id"],
    )
    event = build_pathway_event(
        hypothesis, run_id=new_run_id, context_hash=context_hash,
        catalytic_support=[],
    )
    product_refs = [p.state_ref for p in hypothesis.participants
                    if p.side == PARTICIPANT_SIDE_PRODUCT]
    report = build_report_projection(
        hypothesis, max_reportable=max(1, len(product_refs)),
        ranked_state_refs=product_refs,
        reasons=["legacy_import:位次=旧账本产物位次,仅作占位"],
    )
    expansion = build_expansion_plan(
        hypothesis, expanded=[], deferred=[], not_tracked=product_refs,
        reasons={ref: "legacy_import_no_expansion_info" for
                 ref in product_refs},
    )
    provenance = map_legacy_card({
        "kind": legacy_event.get("kind", ""),
        "source_id": legacy_event.get("source_id", ""),
        "match_type": "",  # 旧事件行不存 match_type;不伪造
        "asset_sources": [],
    })
    all_states = {substrate_state.state_id: substrate_state, **product_states}
    return {
        "hypothesis": hypothesis,
        "event": event,
        "report_projection": report.to_dict(),
        "expansion_plan": expansion.to_dict(),
        "states": [s.to_dict() for s in all_states.values()],
        "provenance": provenance.to_dict(),
        "uncertainty_notes": uncertainty_notes,
        "context_hash": context_hash,
        "event_id": event.event_id,
        "hypothesis_id": hypothesis.hypothesis_id,
    }


def import_legacy_run(
    run_dir: str | Path,
    *,
    new_run_id: str,
    target_store,
) -> dict:
    """整个旧 run 只读导入到新模式账本(逐事件;零写回旧库)。

    target_store:PollutantPathwayStore(新库);事件幂等重放返回
    created=False,不重复入账。
    """
    run_dir = Path(run_dir)
    events = read_legacy_events(run_dir)
    n_created = 0
    n_replayed = 0
    notes: list[str] = []
    for legacy_event in events:
        imported = import_legacy_event(run_dir, legacy_event,
                                       new_run_id=new_run_id)
        for state in imported["states"]:
            target_store.put_state(state)
        target_store.put_hypothesis(
            imported["hypothesis"].to_dict(),
            context_hash=imported["context_hash"])
        result = target_store.submit_event(
            imported["event"],
            report_projection=imported["report_projection"],
            expansion_plan=imported["expansion_plan"],
            states=imported["states"])
        if result["created"]:
            n_created += 1
        else:
            n_replayed += 1
        notes.extend(imported["uncertainty_notes"])
    return {"n_events": len(events), "n_created": n_created,
            "n_replayed": n_replayed, "uncertainty_notes": notes,
            "legacy_run_dir": str(run_dir),
            "import_run_id": stable_id("ppimp", str(run_dir))}
