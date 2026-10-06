"""legacy 只读适配 — 旧 v43 账本到新表示(v4 回修,S1)。

v4(2026-10-06 R4 回修)相对 v3 的变化(R3-11 + R3-10 导入侧):
- **archive 来源核对(R3-11)**:子底物的来源指针指向**存在但错误**的
  产物行时,核对指针行的结构/CN(重算)与子底物声明的 CN/身份 ——
  矛盾 ⇒ CN-only + 原因 `substrate_archive_identity_mismatch`,不再把
  错误引用当完整结构(不借乙酸冒充乙醛);
- **根核对(R3-11)**:root_smiles 重算旧身份(chemstate/legacy CN 同源),
  与库声明的 root CN 矛盾 ⇒ CN-only + 原因
  `root_smiles_identity_mismatch`,不再直接把 root_smiles 当 raw_input
  无注记;
- **所有公开导入入口守版本门(R3-11)**:import_legacy_event(单事件)
  与 import_legacy_run 同口径 —— 旧库 store schema 未知版本拒绝 +
  run identity 显式未来版本拒绝(fail-closed,旧库零写回);
- **导入重放不得先 put 绕过(R3-10)**:import_legacy_run 的重放路径
  (event 已存)先校验已存记录完整性(provenance 缺/损 ⇒ 结构化损坏
  错误;其余由 submit_event 重放分支从已存行复算),**不先 put_state
  补依赖**再报 n_replayed;仅首次导入(event 不存在)走 put+submit。

v3(2026-10-06 R3 回修)相对 v2 的变化(R2-08/R2-11/P2):
- **先保留全部 occurrence 再归并分子身份(R2-08)**:同事件同图不同
  位置(position 0="CC=O"、position 1="O=CC")、root 再次出现
  (CCO→CC=O→CCO 循环)全部保留为出现记录 —— states 载荷以出现
  **列表**传递,不再先按 state_id 建字典覆盖;报告/展开引用按
  物种去重(同物种一次),出现层保留每个原始位次与原串;
- **根身份依据实际父关系确认(R2-11)**:root 须同时满足
  parent_path_id 为空 AND 无 event/product_position 指针 AND
  substrate_identity 与 run identity 的根身份一致;子路径
  parent_path_id 非空但指针损坏 ⇒ CN-only + 原因说明,绝不借根
  结构冒充;
- **provenance 引用可解析(P2)**:导入假设的 provenance_refs 指向
  新账本 record_id(映射到新记录),legacy evidence_id 保留在
  provenance 载荷(legacy_evidence_id/legacy_source_id),旧 ID
  不再作为不可解析的悬空引用。

既有不变量:只读(sqlite ro URI,不经 PathwayStore 构造);旧库零
写回(字节不变);novel 平列表挂 legacy_relationship_unspecified 不
猜分组(A04);旧账本 schema 未知 fail-closed。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..domain.identity import cn_identity as _legacy_cn_identity
from ..domain.models import EVIDENCE_KIND_NOVEL, content_hash, stable_id
from ..storage.run_identity import SUPPORTED_IDENTITY_SCHEMA_VERSIONS
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
from .profile import PPV1_PROVENANCE_SCHEMA_VERSION
from .provenance import map_legacy_card
from .store import Ppv1LedgerCorrupt

SUPPORTED_LEGACY_STORE_VERSIONS = ("v43-store-1", "v43-store-2")

# 子路径来源指针损坏/矛盾的降级原因码(R2-11/R3-11;保留在 source_refs
# 与 uncertainty_notes 中,不吞掉)
CN_ONLY_REASON_SUBSTRATE_ARCHIVE_MISSING = "substrate_archive_missing"
CN_ONLY_REASON_CHILD_MISSING_ARCHIVE_POINTERS = \
    "child_missing_archive_pointers"
CN_ONLY_REASON_ROOT_IDENTITY_UNCONFIRMED = "root_identity_unconfirmed"
CN_ONLY_REASON_ARCHIVE_POINTERS_BROKEN = "archive_pointers_broken"
# R3-11:指针/根的内容与声明身份矛盾(存在但错误)
CN_ONLY_REASON_SUBSTRATE_ARCHIVE_IDENTITY_MISMATCH = \
    "substrate_archive_identity_mismatch"
CN_ONLY_REASON_ROOT_SMILES_IDENTITY_MISMATCH = \
    "root_smiles_identity_mismatch"


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


def _gate_legacy_store_version(conn: sqlite3.Connection) -> None:
    """旧库 store schema 版本门(所有公开导入入口共同执行,R3-11)。"""
    meta = conn.execute(
        "SELECT value FROM meta WHERE key='schema_version'").fetchone()
    version = meta["value"] if meta else None
    if version not in SUPPORTED_LEGACY_STORE_VERSIONS:
        raise LegacyStoreError(
            f"旧账本 schema 版本未知:{version!r}(支持 "
            f"{SUPPORTED_LEGACY_STORE_VERSIONS};fail-closed 不猜)",
            {"schema_version": version})


def read_legacy_events(run_dir: str | Path) -> list[dict]:
    """只读列出旧账本事件(含产物行;零写回)。"""
    conn = _read_only_conn(Path(run_dir) / "pathway.sqlite")
    try:
        _gate_legacy_store_version(conn)
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


def _legacy_root_identity(run_dir: Path) -> tuple[str | None, str | None]:
    """run identity 的 (root_smiles, root_identity);缺/坏 ⇒ (None,None)。

    R3-11:run_identity.json 的 schema_version 显式未来/未知版本 ⇒
    LegacyStoreError(所有导入入口共同拒绝,与 store 版本门同口径);
    文件缺失/解析失败 ⇒ (None,None)(根无法确认,走 CN-only 降级)。
    """
    ident = run_dir / "run_identity.json"
    if not ident.is_file():
        return None, None
    try:
        data = json.loads(ident.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    version = data.get("schema_version")
    if version is not None and version not in \
            SUPPORTED_IDENTITY_SCHEMA_VERSIONS:
        raise LegacyStoreError(
            f"旧 run identity schema 版本未知:{version!r}(支持 "
            f"{list(SUPPORTED_IDENTITY_SCHEMA_VERSIONS)};fail-closed,"
            "不猜测解析)",
            {"schema_version": version, "path": str(ident)})
    inputs = data.get("inputs", {})
    return (inputs.get("root_smiles"), inputs.get("root_identity"))


def _legacy_cn_of(structure: str | None) -> str | None:
    """结构串 → 旧口径 CN(chemstate cn_identity 同源);失败 ⇒ None。"""
    if not isinstance(structure, str) or not structure.strip():
        return None
    try:
        return _legacy_cn_identity(structure)
    except Exception:
        return None


def _substrate_structure_for_path(
    conn: sqlite3.Connection, run_dir: Path, path_id: str,
) -> tuple[str, str, str]:
    """父路径底物结构来源 → (structure_or_cn, source_kind, reason)。

    source_kind ∈ {"archive", "root", "cn_only"};reason 是 cn_only
    降级的原因码(archive/root 为空串)。

    R2-11:root 身份须依据**实际父关系**确认 —— parent_path_id 为空
    AND event/product_position 指针为空 AND substrate_identity 与
    run identity 根身份一致,三者同时成立才算 root;子路径
    (parent 非空)指针损坏 ⇒ cn_only(child_missing_archive_
    pointers),绝不借根结构冒充;指针残缺/矛盾 ⇒ cn_only 并保留
    原因码。

    R3-11 内容核对:
    - root:root_smiles **重算旧身份**(chemstate/legacy CN 同源)须与
      库声明的 root_identity 一致 —— 矛盾 ⇒ cn_only
      (root_smiles_identity_mismatch),不把矛盾根串当 raw_input;
    - archive:指针行的结构/CN(重算)须与子底物声明的 substrate_
      identity 一致且行内自洽 —— 指向存在但错误的产物行 ⇒ cn_only
      (substrate_archive_identity_mismatch),不把错误引用当完整结构。
    """
    row = conn.execute(
        "SELECT * FROM path_instances WHERE path_id = ?", (path_id,)).fetchone()
    if row is None:
        raise LegacyStoreError(
            f"旧账本缺路径:{path_id}", {"path_id": path_id})
    parent_id = row["parent_path_id"]
    event_ptr = row["event_id"]
    pos_ptr = row["product_position"]
    if parent_id is None and event_ptr is None and pos_ptr is None:
        root_smiles, root_identity = _legacy_root_identity(run_dir)
        if root_smiles and root_identity \
                and row["substrate_identity"] == root_identity:
            # R3-11 根核对:root_smiles 重算旧身份,与声明根身份矛盾 ⇒
            # 不当 raw_input(降级 CN-only 并保留原因)
            if _legacy_cn_of(root_smiles) == root_identity:
                return root_smiles, "root", ""
            return (row["substrate_identity"], "cn_only",
                    CN_ONLY_REASON_ROOT_SMILES_IDENTITY_MISMATCH)
        # 指针全空但身份无法与 run 根确认一致 ⇒ 不借根结构
        return (row["substrate_identity"], "cn_only",
                CN_ONLY_REASON_ROOT_IDENTITY_UNCONFIRMED)
    if event_ptr is not None and pos_ptr is not None:
        prod = conn.execute(
            "SELECT * FROM event_products WHERE event_id = ? AND"
            " position = ?",
            (event_ptr, pos_ptr)).fetchone()
        if prod is not None:
            # R3-11 archive 来源核对:指针行的结构/CN 与子底物声明的
            # 身份一致且行内自洽 ⇒ 才可用其结构;矛盾 ⇒ CN-only+原因
            product_structure = (prod["product_smiles_full"]
                                 or prod["product_smiles"])
            recomputed_cn = _legacy_cn_of(product_structure)
            row_consistent = (
                prod["product_identity"] == row["substrate_identity"]
                and recomputed_cn == prod["product_identity"])
            if row_consistent:
                return product_structure, "archive", ""
            return (row["substrate_identity"], "cn_only",
                    CN_ONLY_REASON_SUBSTRATE_ARCHIVE_IDENTITY_MISMATCH)
        # 指针齐全但存档行缺失:CN-only(不借根结构;F09)
        return (row["substrate_identity"], "cn_only",
                CN_ONLY_REASON_SUBSTRATE_ARCHIVE_MISSING)
    # 指针残缺:子路径丢来源指针 / 矛盾指针 ⇒ CN-only,保留原因
    reason = (CN_ONLY_REASON_CHILD_MISSING_ARCHIVE_POINTERS
              if parent_id is not None
              else CN_ONLY_REASON_ARCHIVE_POINTERS_BROKEN)
    return row["substrate_identity"], "cn_only", reason


def import_legacy_event(
    run_dir: str | Path,
    legacy_event: dict,
    *,
    new_run_id: str,
) -> dict:
    """单条旧事件 → 新表示(hypothesis + 事件 + 缺省投影/展开 + 状态)。

    返回 {"hypothesis", "event", "report_projection", "expansion_plan",
    "states", "provenance", "provenance_record_id", "uncertainty_notes",
    "context_hash", "event_id", "hypothesis_id"}。

    - **states 是出现列表,不按 state_id 去重**(R2-08):同事件同图
      不同位置的每个产物出现、与底物同图的产物出现,各生成一条
      state 载荷;分子身份归并由 store 落账时完成(语义幂等 + 出现
      追加)。缺省投影/展开是**只读导入占位**(位次=legacy 位次、
      展开 not_tracked、原因 legacy_import_no_expansion_info);
      报告/展开引用按物种去重(同物种一次报告,不因平列表位次
      重复报告),去重在 reasons 留痕;
    - provenance_refs 指向新账本 record_id(P2:导入后可按
      get_provenance 解析);legacy evidence_id 保存在 provenance
      载荷的 legacy_evidence_id/legacy_source_id;
    - **R3-11 版本门**:本入口与 import_legacy_run 同口径 —— 旧库
      store schema 未知版本、run identity 显式未来版本 ⇒
      LegacyStoreError(旧库零写回)。
    """
    run_dir = Path(run_dir)
    conn = _read_only_conn(run_dir / "pathway.sqlite")
    try:
        # R3-11:所有公开导入入口共同守版本门(store schema + run identity)
        _gate_legacy_store_version(conn)
        _legacy_root_identity(run_dir)  # 未来 identity 版本 ⇒ 显式拒绝
        substrate_source, source_kind, cn_reason = \
            _substrate_structure_for_path(
                conn, run_dir, legacy_event["parent_path_id"])
    finally:
        conn.close()

    uncertainty_notes: list[str] = []
    if source_kind == "cn_only":
        substrate_state = build_chemical_state_from_cn_only(
            legacy_event["substrate_identity"],
            source_refs=[{"role": "legacy_path_substrate",
                          "path_id": legacy_event["parent_path_id"],
                          "reason": cn_reason}])
        reason_detail = {
            CN_ONLY_REASON_SUBSTRATE_ARCHIVE_MISSING: "存档行缺失",
            CN_ONLY_REASON_CHILD_MISSING_ARCHIVE_POINTERS:
                "子路径来源指针残缺",
            CN_ONLY_REASON_ROOT_IDENTITY_UNCONFIRMED:
                "根身份无法与 run 根确认一致",
            CN_ONLY_REASON_ARCHIVE_POINTERS_BROKEN: "指针残缺/矛盾",
            CN_ONLY_REASON_SUBSTRATE_ARCHIVE_IDENTITY_MISMATCH:
                "来源指针指向存在但身份矛盾的产物行(不借错误结构)",
            CN_ONLY_REASON_ROOT_SMILES_IDENTITY_MISMATCH:
                "root_smiles 重算身份与声明根身份矛盾(不用矛盾根串)",
        }.get(cn_reason, "来源不可用")
        uncertainty_notes.append(
            f"substrate_structure_legacy_cn_only:{cn_reason}:历史路径"
            f"只余 CN({reason_detail}),结构/立体/原始电荷未知;不以根"
            "结构或错误引用冒充子底物")
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
    # R2-08:产物出现全部保留(不按 state_id 建字典覆盖)
    product_state_dicts: list[dict] = []
    n_product_occurrences = 0
    for prod in legacy_event.get("products", []):
        full = prod.get("product_smiles_full") or prod.get("product_smiles")
        state = build_chemical_state(
            full, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
            source_refs=[{"role": "legacy_event_product",
                          "event_id": legacy_event["event_id"],
                          "position": prod.get("position")}],
            fidelity=archive_recovered_fidelity())
        product_state_dicts.append(state.to_dict())
        n_product_occurrences += 1
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

    provenance_record_id = stable_id("ppprov", legacy_event["event_id"])
    hypothesis = build_hypothesis(
        parent_path_id=legacy_event["parent_path_id"],
        substrate_state_ref=substrate_state.state_id,
        participants=participants,
        participant_list_status=PARTICIPANT_LIST_UNKNOWN,
        step_scope="unknown",
        # P2:引用映射到新账本 record_id(可解析);旧 evidence_id
        # 保留在 provenance 载荷
        provenance_refs=[provenance_record_id],
        model_decision_ref=model_ref,
        legacy_relationship_status=relationship_status,
        origin_group_key=legacy_event["evidence_id"],
    )
    event = build_pathway_event(
        hypothesis, run_id=new_run_id, context_hash=context_hash,
        catalytic_support=[],
    )
    # 报告/展开引用按物种去重(同图产物一次;出现层保留全部位次)
    product_refs_ordered: list[str] = []
    for p in participants:
        if p.side == PARTICIPANT_SIDE_PRODUCT \
                and p.state_ref not in product_refs_ordered:
            product_refs_ordered.append(p.state_ref)
    report_reasons = [
        "legacy_import:位次=旧账本产物位次,仅作占位",
    ]
    if n_product_occurrences > len(product_refs_ordered):
        report_reasons.append(
            f"legacy_import_product_dedup:旧事件 {n_product_occurrences} 个"
            "产物位次归并为同图物种一次报告(原始位次/原串保留在出现"
            "记录,不冒称只有一个来源出现)")
    report = build_report_projection(
        hypothesis, max_reportable=max(1, len(product_refs_ordered)),
        ranked_state_refs=product_refs_ordered,
        reasons=report_reasons,
    )
    expansion = build_expansion_plan(
        hypothesis, expanded=[], deferred=[], not_tracked=product_refs_ordered,
        reasons={ref: "legacy_import_no_expansion_info" for
                 ref in product_refs_ordered},
    )
    # model_ref 非空 ⇒ 模型决策参与(F10:导入不丢模型来源)
    provenance = map_legacy_card({
        "evidence_id": legacy_event.get("evidence_id", ""),
        "kind": legacy_event.get("kind", ""),
        "source_id": legacy_event.get("source_id", ""),
        "match_type": ("model_analogy_transfer" if model_ref else ""),
        "asset_sources": [],
        "source_record": ({"predicted_by_model": True} if model_ref
                          else {}),
    })
    states = [substrate_state.to_dict(), *product_state_dicts]

    return {
        "hypothesis": hypothesis,
        "event": event,
        "report_projection": report.to_dict(),
        "expansion_plan": expansion.to_dict(),
        "states": states,
        "provenance": provenance.to_dict(),
        "provenance_record_id": provenance_record_id,
        "uncertainty_notes": uncertainty_notes,
        "context_hash": context_hash,
        "event_id": event.event_id,
        "hypothesis_id": hypothesis.hypothesis_id,
    }


def _verify_imported_provenance(target_store, imported: dict,
                                new_run_id: str) -> None:
    """导入重放路径的 provenance 完整性核验(R3-10;不补账)。

    缺失/版本未知/内容与重推导值不符 ⇒ Ppv1LedgerCorrupt(结构化损坏
    错误;不先 put 补回依赖)。states/appearances/hypotheses/projections
    /plans 及行内容由 submit_event 重放分支从已存行复算。
    """
    record_id = imported["provenance_record_id"]
    stored = target_store.get_provenance(record_id)
    if stored is None:
        raise Ppv1LedgerCorrupt(
            f"重放导入(new_run_id={new_run_id})缺 provenance 记录"
            f"{record_id}(账本不完整;不补账、不默默成功)",
            {"table": "provenance_records", "record_id": record_id,
             "kind": "provenance_record_missing",
             "legacy_evidence_id":
                 imported["provenance"].get("legacy_evidence_id", "")})
    if stored.get("schema_version") != PPV1_PROVENANCE_SCHEMA_VERSION:
        raise Ppv1LedgerCorrupt(
            f"重放导入(new_run_id={new_run_id})的 provenance 记录"
            f"{record_id} schema 版本未知(损坏)",
            {"table": "provenance_records", "record_id": record_id,
             "kind": "provenance_schema_corrupt",
             "schema_version": stored.get("schema_version")})
    if content_hash(stored) != content_hash(imported["provenance"]):
        raise Ppv1LedgerCorrupt(
            f"重放导入(new_run_id={new_run_id})的 provenance 记录"
            f"{record_id} 内容与重推导值不一致(损坏)",
            {"table": "provenance_records", "record_id": record_id,
             "kind": "provenance_payload_corrupt"})


def import_legacy_run(
    run_dir: str | Path,
    *,
    new_run_id: str,
    target_store,
) -> dict:
    """整个旧 run 只读导入到新模式账本(逐事件;零写回旧库)。

    - 每事件:先判 event 是否已在目标账本 —— **首次导入**(event 不
      存在)走 states(出现列表,R2-08)/hypothesis/provenance 先行
      落账 + 事件/投影/展开同事务提交;**重放**(event 已存在)不先
      put 补账:provenance 显式核(缺/损 ⇒ 结构化损坏错误),其余
      必要记录由 submit_event 重放分支从已存行复算(R3-10 反例:
      先 put_state 补依赖再报 n_replayed=1 不再发生);
    - 幂等:完整且一致的重放返回 n_replayed 计数,不重复入账;
    - 连续多步路径(共享中间物)与 root 循环再出现正常导入
      (R2-08:同一结构不同来源/保真度是出现记录追加,不是身份冲突)。
    """
    run_dir = Path(run_dir)
    events = read_legacy_events(run_dir)
    n_created = 0
    n_replayed = 0
    notes: list[str] = []
    for legacy_event in events:
        imported = import_legacy_event(run_dir, legacy_event,
                                       new_run_id=new_run_id)
        if target_store.get_event(imported["event"].event_id) is not None:
            # 重放:不先 put 补账 —— 先校验已存记录完整性(R3-10)
            _verify_imported_provenance(target_store, imported, new_run_id)
            target_store.submit_event(
                imported["event"],
                report_projection=imported["report_projection"],
                expansion_plan=imported["expansion_plan"],
                states=imported["states"],
                hypothesis_dict=imported["hypothesis"].to_dict())
            n_replayed += 1
        else:
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
        notes.extend(imported["uncertainty_notes"])

    return {"n_events": len(events), "n_created": n_created,
            "n_replayed": n_replayed, "uncertainty_notes": notes,
            "legacy_run_dir": str(run_dir),
            "import_run_id": stable_id("ppimp", str(run_dir))}
