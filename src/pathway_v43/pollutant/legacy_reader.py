"""legacy 只读适配 — 旧 v43 账本到新表示(v2 回修,S1)。

v2(2026-10-05 回修)相对 v1 的变化(F09/F10/F04):
- **子路径缺存档不借根结构(F09)**:只有经路径关系确认的根节点
  (event_id 与 product_position 均空)才允许使用 run identity 的
  root_smiles;子路径找不到来源产物行 ⇒ 退 CN-only 只读状态并留
  未知说明,**绝不**以根污染物结构冒充子底物;
- **模型来源保留(F10)**:旧事件行的 model_ref 非空 ⇒ provenance
  映射按模型提案/类比处理,不再丢失;来源细分记录随导入持久保存到
  新账本 provenance_records;
- **存档形分轴保真(F04/F05)**:产物与子底物的存档结构按
  archive_recovered 分轴 fidelity 构建(立体/同位素 absent_in_
  archive,电荷 as_written);CN-only 按 CN-only 分轴(电荷 unknown)。

既有不变量:只读(sqlite ro URI,不经 PathwayStore 构造);旧库零
写回(字节不变);novel 平列表挂 legacy_relationship_unspecified 不
猜分组(A04);旧账本 schema 未知 fail-closed。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..domain.models import EVIDENCE_KIND_NOVEL
from .chemstate import (
    STRUCTURE_ORIGIN_RAW_INPUT,
    STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    archive_recovered_fidelity,
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
) -> tuple[str, str]:
    """父路径底物结构来源 → (structure_or_cn, source_kind)。

    source_kind ∈ {"archive"(事件产物存档形), "root"(经路径关系确认的
    根节点原始输入), "cn_only"(子路径缺存档 —— 退 CN,绝不借根
    结构冒充,F09)}。
    """
    row = conn.execute(
        "SELECT * FROM path_instances WHERE path_id = ?", (path_id,)).fetchone()
    if row is None:
        raise LegacyStoreError(
            f"旧账本缺路径:{path_id}", {"path_id": path_id})
    is_root = row["event_id"] is None and row["product_position"] is None
    if not is_root:
        prod = conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? AND"
            " position = ?",
            (row["event_id"], row["product_position"])).fetchone()
        if prod is not None:
            return (prod["product_smiles_full"] or prod["product_smiles"],
                    "archive")
        # 子路径缺存档:CN-only(不借根结构;F09)
        return row["substrate_identity"], "cn_only"
    root_smiles = _legacy_root_smiles(run_dir)
    if root_smiles:
        return root_smiles, "root"
    # 根节点连身份文件都缺:CN-only(如实)
    return row["substrate_identity"], "cn_only"


def import_legacy_event(
    run_dir: str | Path,
    legacy_event: dict,
    *,
    new_run_id: str,
) -> dict:
    """单条旧事件 → 新表示(hypothesis + 事件 + 缺省投影/展开 + 状态)。

    返回 {"hypothesis", "event", "report_projection", "expansion_plan",
    "states", "provenance", "provenance_record_id", "uncertainty_notes",
    "context_hash", "event_id", "hypothesis_id"}。缺省投影/展开计划是
    **只读导入占位**(全部产物位次=legacy 位次、展开 not_tracked、
    原因 legacy_import_no_expansion_info;与真实决策区分,不把
    not_tracked 当化学终点)。
    """
    run_dir = Path(run_dir)
    conn = _read_only_conn(run_dir / "pathway.sqlite")
    try:
        substrate_source, source_kind = _substrate_structure_for_path(
            conn, run_dir, legacy_event["parent_path_id"])
    finally:
        conn.close()

    uncertainty_notes: list[str] = []
    if source_kind == "cn_only":
        substrate_state = build_chemical_state_from_cn_only(
            legacy_event["substrate_identity"],
            source_refs=[{"role": "legacy_path_substrate",
                          "path_id": legacy_event["parent_path_id"],
                          "reason": "substrate_archive_missing"}])
        uncertainty_notes.append(
            "substrate_structure_legacy_cn_only:历史路径只余 CN"
            "(存档缺失),结构/立体/原始电荷未知;不以根结构冒充子底物")
    else:
        substrate_state = build_chemical_state(
            substrate_source,
            STRUCTURE_ORIGIN_RAW_INPUT if source_kind == "root"
            else STRUCTURE_ORIGIN_SOURCE_PRODUCT,
            source_refs=[{
                "role": "legacy_path_substrate",
                "path_id": legacy_event["parent_path_id"],
                "source_kind": source_kind,
            }],
            fidelity=(archive_recovered_fidelity()
                      if source_kind == "archive" else None))

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
            fidelity=archive_recovered_fidelity())
        product_states[state.state_id] = state
        participants.append(Participant(
            state_ref=state.state_id, side=PARTICIPANT_SIDE_PRODUCT,
            role=PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
            coefficient=None, coefficient_status=COEFFICIENT_UNKNOWN,
        ))

    legacy_novel = legacy_event.get("kind") == EVIDENCE_KIND_NOVEL
    relationship_status = ("legacy_relationship_unspecified"
                           if legacy_novel else "")
    if legacy_novel:
        uncertainty_notes.append(
            "legacy_novel_flat_product_list:历史 novel 平列表语义不明确,"
            "不猜共同产物分组,不拆成单产物反应")
    model_ref = str(legacy_event.get("model_ref", "") or "")
    if model_ref:
        uncertainty_notes.append(
            f"legacy_model_decision:{model_ref[:120]}(模型决策引用随导入"
            "保留,来源细分按模型提案处理)")
    context_hash = "legacy-import"  # 导入侧无原上下文:显式常量,不伪造

    hypothesis = build_hypothesis(
        parent_path_id=legacy_event["parent_path_id"],
        substrate_state_ref=substrate_state.state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_UNKNOWN,
        step_scope="unknown",
        provenance_refs=[legacy_event["evidence_id"]],
        model_decision_ref=model_ref,
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
    # model_ref 非空 ⇒ 模型决策参与(F10:导入不丢模型来源)
    provenance = map_legacy_card({
        "kind": legacy_event.get("kind", ""),
        "source_id": legacy_event.get("source_id", ""),
        "match_type": ("model_analogy_transfer" if model_ref else ""),
        "asset_sources": [],
        "source_record": ({"predicted_by_model": True} if model_ref
                          else {}),
    })
    all_states = {substrate_state.state_id: substrate_state, **product_states}
    from ..domain.models import stable_id

    return {
        "hypothesis": hypothesis,
        "event": event,
        "report_projection": report.to_dict(),
        "expansion_plan": expansion.to_dict(),
        "states": [s.to_dict() for s in all_states.values()],
        "provenance": provenance.to_dict(),
        "provenance_record_id": stable_id(
            "ppprov", legacy_event["event_id"]),
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

    - 每事件:states/hypothesis/provenance 先行落账,事件+投影+展开
      同事务提交(事务要求假设关联,store v2);
    - 幂等:重放返回 created=False,不重复入账;
    - 连续多步路径(共享中间物)正常导入(F04:同一结构不同来源引用
      是出现记录追加,不构成身份冲突)。
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
        target_store.put_provenance(
            imported["provenance_record_id"], new_run_id,
            imported["provenance"])
        result = target_store.submit_event(
            imported["event"],
            report_projection=imported["report_projection"],
            expansion_plan=imported["expansion_plan"],
            states=imported["states"],
            hypothesis_dict=imported["hypothesis"].to_dict())
        if result["created"]:
            n_created += 1
        else:
            n_replayed += 1
        notes.extend(imported["uncertainty_notes"])
    from ..domain.models import stable_id

    return {"n_events": len(events), "n_created": n_created,
            "n_replayed": n_replayed, "uncertainty_notes": notes,
            "legacy_run_dir": str(run_dir),
            "import_run_id": stable_id("ppimp", str(run_dir))}
