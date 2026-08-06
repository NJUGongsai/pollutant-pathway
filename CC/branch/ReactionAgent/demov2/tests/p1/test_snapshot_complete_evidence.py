"""Critical-1 (§5) — snapshot must freeze the COMPLETE evidence, not a
hand-picked whitelist projection.

Round 2 shipped a partial whitelist in
``reaction_agent/snapshot/builder.py::_canonical_record_payload`` that copied
only *some* ``ReactionEvidence`` fields plus *some* ``EligibilityDecision``
fields and only the ``record_id`` of the ``QuarantineRecord``. ChatGPT
reproduced (baseline hash
``30261902ce0e4fb7d33e214ee4c6cbcb27ca12dbd97136675ae1327e404e9f2b``) that
mutating any of the following reaction-level scientific fields left the record
/ snapshot hash UNCHANGED:

    provenance / source_uri_or_citation / fragment_lineage_graph /
    ambiguity_sets / transformation_hypotheses / quality_report / quarantine

and that the complete ``EligibilityDecision`` (required_warnings /
evidence_ids / research_diagnostic_eligibility / policy_version) and the
complete ``QuarantineRecord`` were neither hashed nor persisted.

These tests are written FIRST (R3-T2) against the target §5.3 canonical
structure::

    {
        "reaction_evidence":   evidence.model_dump(mode="json") minus circular,
        "source_ledger":       ledger.model_dump() | None,
        "resolved_lineages":   [l.model_dump() ...],
        "eligibility_decision": decision.model_dump(),
        "quarantine_record":   qr.model_dump() | None,
        "lane":                <hashed & re-derived>,
    }

They are RED against the current flat whitelist and GREEN after R3-T3.

The dual-ledger authority (§5.4) and the runtime/circular exclusion policy
(§5.3 item 4/5) are also frozen here.
"""
from __future__ import annotations

import json
import os

import pytest

from reaction_agent.config import BuildConfig
from reaction_agent.schemas.common import (
    LedgerBalanceStatus,
    LineageResolutionQuality,
    MappingQualityClass,
    MappingStatus,
    ParticipantRole,
    SourceAssignmentMethod,
)
from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
from reaction_agent.schemas.ledger import (
    RoleAssignment,
    SourceReactionLedger,
)
from reaction_agent.schemas.mapping import (
    FormalMappedAtomPair,
    FormalSourceAssignment,
    MappingReport,
)
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage
from reaction_agent.snapshot.builder import (
    SnapshotBuildError,
    SnapshotEvidenceItem,
    build_snapshot,
    compute_snapshot_hash,
)
from reaction_agent.snapshot.loader import (
    SnapshotHashMismatchError,
    load_snapshot,
)


# =====================================================================
# Fixture helpers (self-contained)
# =====================================================================

def _participant(
    pid: str,
    side: str,
    smiles: str = "CC",
    atom_map_numbers: list[int] | None = None,
    provenance: list[str] | None = None,
) -> ReactionParticipant:
    return ReactionParticipant(
        participant_id=pid,
        molecule_id=f"mol_{pid}",
        canonical_smiles=smiles,
        side=side,
        atom_map_numbers=atom_map_numbers or [],
        mapped_fraction=1.0,
        changed_atom_fraction=0.0,
        provenance=provenance or [f"prov_{pid}"],
    )


def _mapping_report(
    *,
    reactant_pid: str = "r1",
    product_pid: str = "p1",
    atom_maps: list[int] | None = None,
) -> MappingReport:
    """A fully-mapped, formal_mapped, unambiguous report with a formal pair for
    every atom map (so a lineage over ``atom_maps`` is fully supported)."""
    atom_maps = atom_maps or [1, 2]
    pairs = [
        FormalMappedAtomPair(
            reactant_participant_id=reactant_pid,
            reactant_atom_map=n,
            product_participant_id=product_pid,
            product_atom_map=n,
        )
        for n in atom_maps
    ]
    return MappingReport(
        mapper_name="fake_mapper",
        mapper_version="v1",
        mapper_parameters={"timeout": "30"},
        input_hash="inp_abc",
        output_hash="out_def",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0,
        map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="fake_mapper",
            mapper_version="v1",
            mapped_atom_pairs=pairs,
            assignment_method=SourceAssignmentMethod.formal_mapped,
            assignment_quality=MappingQualityClass.high_quality,
            assignment_ambiguity=False,
        ),
        fallback_method=None,
    )


def _ledger(
    *,
    reaction_evidence_id: str = "rxn_strict_001",
    balance_status: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
    charge_balance: int = 0,
) -> SourceReactionLedger:
    return SourceReactionLedger(
        ledger_id=f"srl_{reaction_evidence_id}",
        reaction_evidence_id=reaction_evidence_id,
        balance_status=balance_status,
        charge_balance=charge_balance,
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        ],
        hydrogen_policy="explicit",
        proton_policy="explicit",
        electron_policy="explicit",
        source_completeness="complete",
        mapping_completeness="complete",
    )


def _strict_item(
    reaction_id: str = "rxn_strict_001",
    source_name: str = "fixture_source_a",
    *,
    ledger: SourceReactionLedger | None = None,
    embedded_ledger: SourceReactionLedger | None = None,
    **evidence_overrides,
) -> SnapshotEvidenceItem:
    """A fully Critical-2-valid strict-eligible item (resolved lineage,
    complete formal pairs). Extra kwargs override reaction-level fields."""
    participants = [
        _participant("r1", "reactant", "CC", atom_map_numbers=[1, 2]),
        _participant("p1", "product", "CC", atom_map_numbers=[1, 2]),
    ]
    ev = ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"src_{reaction_id}",
        source_name=source_name,
        source_version="v1",
        raw_reaction="CC>>CC",
        normalized_reaction="CC>>CC",
        direction="forward",
        participants=participants,
        mapping_report=_mapping_report(),
        provenance=["rxn_prov_a"],
        source_reaction_ledger=embedded_ledger,
    )
    for key, value in evidence_overrides.items():
        setattr(ev, key, value)
    lineage = ResolvedTransformedLineage(
        lineage_id="lin_r1_p1",
        reactant_participant_id="r1",
        product_participant_id="p1",
        ambiguity="none",
        resolution_quality=LineageResolutionQuality.resolved,
        transformed_atom_maps=[1, 2],
        evidence_ids=["lin_ev_1"],
    )
    return SnapshotEvidenceItem(
        ev,
        ledger if ledger is not None else _ledger(reaction_evidence_id=reaction_id),
        [lineage],
    )


def _conditional_item(
    reaction_id: str = "rxn_cond_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """Heavy-atom-balanced-with-implicit-H/e → conditional_eligible."""
    item = _strict_item(
        reaction_id=reaction_id,
        source_name=source_name,
        ledger=_ledger(
            reaction_evidence_id=reaction_id,
            balance_status=LedgerBalanceStatus.heavy_atom_balanced_with_implicit_h_e_policy,
        ),
    )
    return item


def _quarantine_item(
    reaction_id: str = "rxn_quar_001",
    source_name: str = "fixture_source_a",
) -> SnapshotEvidenceItem:
    """charge_balance != 0 → critical_element_charge_contradiction → quarantine."""
    return _strict_item(
        reaction_id=reaction_id,
        source_name=source_name,
        ledger=_ledger(
            reaction_evidence_id=reaction_id,
            balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
            charge_balance=1,
        ),
    )


def _config(tmp_path) -> BuildConfig:
    return BuildConfig(
        input_source="fixture_source_a",
        output_snapshot_root=str(tmp_path / "snapshots"),
        mapper_backend="fake",
        mapper_version="p1-1",
        mapper_parameters={},
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version="p1-1",
        random_seed=42,
    )


def _build_and_get_dir(tmp_path, items):
    config = _config(tmp_path)
    manifest = build_snapshot(config, iter(items))
    snap_dir = os.path.join(config.output_snapshot_root, manifest.snapshot_id)
    return snap_dir, manifest


def _read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: str, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def _record_reaction_id(rec: dict) -> str:
    ev = rec.get("reaction_evidence")
    if isinstance(ev, dict):
        return ev["reaction_id"]
    return rec["reaction_id"]


# =====================================================================
# §5.5 — reaction-level scientific mutation must change the snapshot hash
# =====================================================================

def test_snapshot_hash_changes_when_reaction_provenance_changes(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(provenance=["rxn_prov_a", "extra_prov"])])
    assert before != after, (
        "reaction-level provenance change did not alter snapshot hash — "
        "ReactionEvidence.provenance is not covered by the content hash"
    )


def test_snapshot_hash_changes_when_source_citation_changes(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(source_uri_or_citation="doi:10.1000/xyz123")])
    assert before != after, (
        "source_uri_or_citation change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_fragment_lineage_graph_changes(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(fragment_lineage_graph={"frag_a": "frag_b"})])
    assert before != after, (
        "fragment_lineage_graph change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_reaction_ambiguity_sets_change(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(ambiguity_sets=[{"atom": "c1", "alt": "c2"}])])
    assert before != after, (
        "ambiguity_sets change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_transformation_hypotheses_change(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(transformation_hypotheses=["hyp_oxidation"])])
    assert before != after, (
        "transformation_hypotheses change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_quality_report_changes(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(quality_report={"balance_check": "passed"})])
    assert before != after, (
        "quality_report change did not alter snapshot hash"
    )


def test_snapshot_hash_changes_when_reaction_quarantine_changes(tmp_path):
    config = _config(tmp_path)
    before = compute_snapshot_hash(config, [_strict_item()])
    after = compute_snapshot_hash(
        config, [_strict_item(quarantine="manually flagged for review")])
    assert before != after, (
        "reaction-level quarantine field change did not alter snapshot hash"
    )


# =====================================================================
# §5.5 — records.jsonl must persist the COMPLETE frozen objects
# =====================================================================

_REACTION_EVIDENCE_REQUIRED_KEYS = {
    "reaction_id", "source_record_id", "source_name", "source_version",
    "source_uri_or_citation", "raw_reaction", "normalized_reaction",
    "direction", "participants", "mapping_report", "fragment_lineage_graph",
    "resolved_transformed_lineages", "ambiguity_sets",
    "transformation_hypotheses", "source_reaction_ledger", "quality_report",
    "provenance", "quarantine",
}

_DECISION_REQUIRED_KEYS = {
    "decision_id", "participant_id", "eligibility", "evaluation_bucket",
    "quarantine_behavior", "reason", "evidence_ids", "required_warnings",
    "research_diagnostic_eligibility", "policy_version",
}

_QUARANTINE_REQUIRED_KEYS = {
    "record_id", "reason", "category", "evidence_ids", "source_record_id",
    "quarantine_behavior", "notes",
}


def test_snapshot_persists_complete_reaction_evidence_model(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_strict_item()])
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    assert len(records) == 1
    rec = records[0]
    ev = rec.get("reaction_evidence")
    assert isinstance(ev, dict), (
        "records.jsonl does not persist a complete reaction_evidence object "
        "(still a flat whitelist projection)"
    )
    missing = _REACTION_EVIDENCE_REQUIRED_KEYS - set(ev)
    assert not missing, f"reaction_evidence missing scientific fields: {missing}"


def test_snapshot_persists_complete_eligibility_decision(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_strict_item()])
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = records[0]
    decision = rec.get("eligibility_decision")
    assert isinstance(decision, dict), (
        "records.jsonl does not persist a complete eligibility_decision object"
    )
    missing = _DECISION_REQUIRED_KEYS - set(decision)
    assert not missing, f"eligibility_decision missing fields: {missing}"


def test_snapshot_persists_complete_quarantine_record(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_quarantine_item()])
    records = _read_jsonl(os.path.join(snap_dir, "records.jsonl"))
    rec = records[0]
    qr = rec.get("quarantine_record")
    assert isinstance(qr, dict), (
        "records.jsonl does not persist a complete quarantine_record object "
        "(only the record_id / reason were kept)"
    )
    missing = _QUARANTINE_REQUIRED_KEYS - set(qr)
    assert not missing, f"quarantine_record missing fields: {missing}"


# =====================================================================
# §5.5 — loader must reject tampering of the complete frozen objects
# =====================================================================

def test_loader_rejects_tampered_reaction_level_provenance(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_strict_item()])
    records_path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(records_path)
    rec = records[0]
    ev = rec.get("reaction_evidence")
    assert isinstance(ev, dict), (
        "records.jsonl missing complete reaction_evidence object — cannot bind "
        "reaction-level provenance to the content hash (Critical-1 not fixed)"
    )
    ev["provenance"] = list(ev.get("provenance", [])) + ["tampered_prov"]
    _write_jsonl(records_path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_loader_rejects_tampered_decision_warning_or_evidence_ids(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_conditional_item()])
    records_path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(records_path)
    rec = records[0]
    decision = rec.get("eligibility_decision")
    assert isinstance(decision, dict), (
        "records.jsonl missing complete eligibility_decision — cannot bind "
        "decision warnings/evidence_ids to the content hash"
    )
    decision["required_warnings"] = list(decision.get("required_warnings", [])) + [
        "injected_warning"
    ]
    decision["evidence_ids"] = list(decision.get("evidence_ids", [])) + ["injected_ev"]
    _write_jsonl(records_path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


def test_loader_rejects_tampered_quarantine_record(tmp_path):
    snap_dir, _ = _build_and_get_dir(tmp_path, [_quarantine_item()])
    records_path = os.path.join(snap_dir, "records.jsonl")
    records = _read_jsonl(records_path)
    rec = records[0]
    qr = rec.get("quarantine_record")
    assert isinstance(qr, dict), (
        "records.jsonl missing complete quarantine_record — cannot bind "
        "quarantine evidence to the content hash"
    )
    qr["notes"] = "tampered: silently downgraded"
    qr["category"] = "reclassified"
    _write_jsonl(records_path, records)
    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)


# =====================================================================
# §5.4 — dual-ledger authority: embedded and external cannot disagree
# =====================================================================

def test_embedded_and_external_ledgers_cannot_disagree(tmp_path):
    """If both ReactionEvidence.source_reaction_ledger and
    SnapshotEvidenceItem.source_ledger exist and their canonical dumps differ,
    the build MUST fail closed (§5.4) — never silently ignore one."""
    external = _ledger(reaction_evidence_id="rxn_strict_001")
    # Embedded ledger disagrees (different balance_status + charge)
    embedded = _ledger(
        reaction_evidence_id="rxn_strict_001",
        balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        charge_balance=3,
    )
    item = _strict_item(ledger=external, embedded_ledger=embedded)
    config = _config(tmp_path)
    with pytest.raises(SnapshotBuildError):
        build_snapshot(config, iter([item]))


# =====================================================================
# §5.3 item 4/5 — explicit runtime/circular exclusion policy + lane binding
# =====================================================================

def test_snapshot_id_or_runtime_exclusion_policy_is_explicit(tmp_path):
    """The exclusion of ``snapshot_id`` (circular reference) must be a
    centralized, explicit, tested policy — not a silent omission."""
    from reaction_agent.snapshot import builder as builder_mod

    excluded = getattr(builder_mod, "EVIDENCE_HASH_EXCLUDED_FIELDS", None)
    assert excluded is not None, (
        "no centralized EVIDENCE_HASH_EXCLUDED_FIELDS policy constant — the "
        "snapshot_id circular exclusion is silently omitted"
    )
    assert "snapshot_id" in excluded, (
        "snapshot_id must be an explicit, documented exclusion"
    )
    config = _config(tmp_path)
    base = compute_snapshot_hash(config, [_strict_item()])
    # Mutating an excluded circular field does NOT change the hash
    excluded_change = compute_snapshot_hash(
        config, [_strict_item(snapshot_id="a_different_snapshot_id")])
    assert base == excluded_change, (
        "snapshot_id must be excluded from the content hash (circular)"
    )
    # But a non-excluded scientific field DOES change the hash
    scientific_change = compute_snapshot_hash(
        config, [_strict_item(quality_report={"k": "v"})])
    assert base != scientific_change, (
        "non-excluded scientific fields must affect the content hash"
    )


def test_lane_is_hashed_or_rederived_and_verified(tmp_path):
    """The lane must be hashed (or re-derived from the complete decision and
    strictly compared by the loader). Swapping the lane labels between a strict
    and a conditional record — while keeping counts, production membership, the
    stored record_content_hash and every decision field intact — must be
    rejected. Current code excludes lane from the record hash and never
    re-derives it, so it accepts the lane/decision disagreement."""
    strict = _strict_item(reaction_id="rxn_strict_001")
    cond = _conditional_item(reaction_id="rxn_cond_001")
    snap_dir, _ = _build_and_get_dir(tmp_path, [strict, cond])

    records_path = os.path.join(snap_dir, "records.jsonl")
    prod_path = os.path.join(snap_dir, "production_index.jsonl")

    def _swap_lanes(records: list[dict]) -> None:
        for rec in records:
            rid = _record_reaction_id(rec)
            if rid == "rxn_strict_001":
                rec["lane"] = "conditional"
            elif rid == "rxn_cond_001":
                rec["lane"] = "strict"

    records = _read_jsonl(records_path)
    _swap_lanes(records)
    _write_jsonl(records_path, records)

    prod = _read_jsonl(prod_path)
    _swap_lanes(prod)
    _write_jsonl(prod_path, prod)

    with pytest.raises(SnapshotHashMismatchError):
        load_snapshot(snap_dir)
