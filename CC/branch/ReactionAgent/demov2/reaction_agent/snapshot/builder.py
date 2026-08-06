"""Immutable content-addressed snapshot builder (§16.1-16.6).

``build_snapshot(config, evidence_iter) -> SnapshotManifest`` runs the snapshot
finalization pipeline on pre-computed evidence items:

    source load → raw preserve → normalize → mapping → roles → lineage →
    ledger → eligibility → production/diagnostic/quarantine → manifest →
    hash → atomic finalize

The builder accepts ALREADY-COMPUTED artifacts (ReactionEvidence +
SourceReactionLedger + ResolvedTransformedLineage) from T4-T8 and runs the T9
eligibility decision (which does NOT require rdkit) to classify each record
into one of the four evaluation lanes (strict / conditional / diagnostic /
quarantine). It then builds the production / diagnostic / quarantine indices,
computes a canonical content hash, and atomically finalizes the snapshot to
``<output_snapshot_root>/<snapshot_id>/``.

Atomicity (§16.4):
1. Write all artifacts to a temp dir (``.tmp_<snapshot_id>``)
2. Verify every artifact (read back, check integrity)
3. Compute the final canonical snapshot hash
4. Write ``manifest.json`` with ``build_status="complete"`` to the temp dir
5. Atomic rename (``os.replace``) temp → final
6. If any step fails → clean up temp, re-raise; the final path is NEVER
   created incomplete. An existing complete immutable snapshot is NEVER
   overwritten (``SnapshotExistsError``).

Determinism (§16.6):
- Same source + same versions + same config → identical snapshot hash, identical
  record IDs, identical index content.
- The canonical snapshot content hash EXCLUDES timestamp, temp path, run ID,
  and unordered iteration order (record hashes are sorted before hashing).

Immutability: inputs are NOT mutated. The snapshot directory, once finalized,
is never modified by the builder.
"""
from __future__ import annotations

import hashlib
import errno
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Iterable

from reaction_agent.config import BuildConfig, BuildInfo, get_build_info
from reaction_agent.eligibility.engine import (
    decide_eligibility,
    build_quarantine_record,
    ENGINE_VERSION as ELIGIBILITY_ENGINE_VERSION,
)
from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.provenance import assert_no_legacy_write
from reaction_agent.schemas.common import (
    EligibilityStatus,
    EvaluationBucket,
    QuarantineBehavior,
)
from reaction_agent.schemas.evidence import ReactionEvidence
from reaction_agent.schemas.ledger import SourceReactionLedger
from reaction_agent.schemas.p1_entities import (
    EligibilityDecision,
    QuarantineRecord,
    ResolvedTransformedLineage,
    SnapshotManifest,
)

BUILDER_VERSION = "p1-t10-1"

# Files written to each snapshot directory
_MANIFEST_FILENAME = "manifest.json"
_PRODUCTION_INDEX = "production_index.jsonl"
_DIAGNOSTIC_INDEX = "diagnostic_index.jsonl"
_QUARANTINE_INDEX = "quarantine_index.jsonl"
_RECORDS_FILENAME = "records.jsonl"
_COMPLETE_MARKER = "COMPLETE"


# =====================================================================
# Errors
# =====================================================================

class SnapshotBuildError(RuntimeError):
    """Build failed (iteration error, verification failure, IO error)."""


class SnapshotExistsError(RuntimeError):
    """A complete immutable snapshot already exists at the target path."""


# =====================================================================
# Input item
# =====================================================================

@dataclass(frozen=True)
class SnapshotEvidenceItem:
    """One input item for the snapshot builder.

    Contains pre-computed artifacts from T4-T8. The builder runs the T9
    eligibility decision on each item to classify it into a lane.

    Immutability: frozen dataclass — fields cannot be mutated after creation.
    """

    reaction_evidence: ReactionEvidence
    source_ledger: SourceReactionLedger | None
    lineages: list[ResolvedTransformedLineage] = field(default_factory=list)


# =====================================================================
# Internal: per-record classification result
# =====================================================================

@dataclass(frozen=True)
class _ClassifiedRecord:
    """Internal: one record classified into a lane."""
    reaction_evidence: ReactionEvidence
    decision: EligibilityDecision
    quarantine_record: QuarantineRecord | None
    record_content_hash: str
    lane: str  # "strict" | "conditional" | "diagnostic" | "quarantine"
    # Source ledger + lineages retained so _record_to_jsonl can persist the
    # complete nested evidence (Critical-1) without re-deriving it.
    source_ledger: SourceReactionLedger | None = None
    lineages: list[ResolvedTransformedLineage] = field(default_factory=list)


def _classify_lane(decision: EligibilityDecision) -> str:
    """Map an EligibilityDecision to one of the four snapshot lanes.

    Lane mapping (§15.5 production index boundary):
    - strict_eligible       → "strict"       (production index, strict subset)
    - conditional_eligible  → "conditional"  (production index, conditional subset)
    - strict_prohibited     → "diagnostic"   (diagnostic index, NOT production)
    - quarantine            → "quarantine"   (quarantine index, excluded)
    """
    if decision.eligibility == EligibilityStatus.strict_eligible:
        return "strict"
    if decision.eligibility == EligibilityStatus.conditional_eligible:
        return "conditional"
    if decision.eligibility == EligibilityStatus.strict_prohibited:
        return "diagnostic"
    if decision.eligibility == EligibilityStatus.quarantine:
        return "quarantine"
    # Fail-closed: unknown eligibility → quarantine (never default to production)
    return "quarantine"


# Runtime/circular exclusion policy (§5.3 item 4). ``snapshot_id`` is the
# ONLY field excluded from the frozen ReactionEvidence content hash: it is a
# back-reference to the very snapshot being built, so including it would be a
# circular dependency (the hash would depend on itself). Every other
# scientific/audit field of ReactionEvidence is frozen and hashed. This
# exclusion is centralized here, documented, and frozen by
# ``test_snapshot_id_or_runtime_exclusion_policy_is_explicit``.
EVIDENCE_HASH_EXCLUDED_FIELDS = frozenset({"snapshot_id"})

# Fields stored alongside the canonical payload in records.jsonl but NOT part
# of the content hash (metadata only). The loader recomputes the record hash
# by stripping exactly these fields from each stored record, so builder and
# loader hash the same payload (§3.2 — one canonical object, not three).
#
# Critical-1 (§5.3): ``lane`` is now part of the hashed canonical payload (it
# is bound to the decision), and the complete ``quarantine_record`` object is
# persisted, so the old ``lane`` / ``quarantine_reason`` meta fields are gone.
# Only the self-referential ``record_content_hash`` remains a meta field.
_RECORD_META_FIELDS = ("record_content_hash",)


def _canonical_record_payload(
    evidence: ReactionEvidence,
    decision: EligibilityDecision,
    quarantine_record: QuarantineRecord | None,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
    lane: str,
) -> dict:
    """Build the single canonical content object for a record (§5.3).

    The SAME object is used for: (1) record content hash, (2) records.jsonl
    persistence, (3) loader tamper verification. Builder hashes, writer
    persists, and loader verifies ONE object — never three different ones.

    Critical-1 fix: instead of a hand-picked whitelist, the payload freezes the
    COMPLETE typed objects via ``model_dump(mode="json")``:

    - ``reaction_evidence``: the entire ``ReactionEvidence`` model minus the
      centralized circular exclusion(s) (``EVIDENCE_HASH_EXCLUDED_FIELDS`` —
      only ``snapshot_id``). This covers provenance / source_uri_or_citation /
      fragment_lineage_graph / ambiguity_sets / transformation_hypotheses /
      quality_report / quarantine / participants / mapping_report /
      embedded source_reaction_ledger — every scientific/audit field.
    - ``source_ledger``: the complete external ``SourceReactionLedger`` (the
      eligibility authority; see ``_resolve_ledger_authority`` §5.4), or None.
    - ``resolved_lineages``: the complete resolved lineages.
    - ``eligibility_decision``: the COMPLETE ``EligibilityDecision`` (including
      required_warnings / evidence_ids / research_diagnostic_eligibility /
      policy_version).
    - ``quarantine_record``: the COMPLETE ``QuarantineRecord`` or None.
    - ``lane``: bound into the hash (and independently re-derived + verified by
      the loader from ``eligibility_decision.eligibility``).

    EXCLUDES timestamp, temp path, run ID (§16.6). Any nested mutation of any
    hashed field changes the hash.
    """
    return {
        "reaction_evidence": evidence.model_dump(
            mode="json", exclude=set(EVIDENCE_HASH_EXCLUDED_FIELDS),
        ),
        "source_ledger": (
            ledger.model_dump(mode="json") if ledger is not None else None
        ),
        "resolved_lineages": [lin.model_dump(mode="json") for lin in lineages],
        "eligibility_decision": decision.model_dump(mode="json"),
        "quarantine_record": (
            quarantine_record.model_dump(mode="json")
            if quarantine_record is not None
            else None
        ),
        "lane": lane,
    }


def _record_content_hash(
    evidence: ReactionEvidence,
    decision: EligibilityDecision,
    quarantine_record: QuarantineRecord | None,
    ledger: SourceReactionLedger | None,
    lineages: list[ResolvedTransformedLineage],
    lane: str,
) -> str:
    """Compute the content hash for a single record (deterministic).

    Hashes the COMPLETE canonical payload (§5.3) — the entire ReactionEvidence
    model, external ledger, resolved lineages, complete decision, complete
    quarantine record, and lane. Any nested mutation changes the hash. Excludes
    timestamp / run ID / temp path (§16.6) and the circular snapshot_id.
    """
    payload = _canonical_record_payload(
        evidence, decision, quarantine_record, ledger, lineages, lane,
    )
    return canonical_hash(payload)


def _resolve_ledger_authority(
    reaction_id: str,
    embedded: SourceReactionLedger | None,
    external: SourceReactionLedger | None,
) -> SourceReactionLedger | None:
    """Resolve the single authoritative source ledger (§5.4 — Method B).

    Two representations of the source ledger may exist:
    - ``ReactionEvidence.source_reaction_ledger`` (embedded), and
    - ``SnapshotEvidenceItem.source_ledger`` (external — the eligibility input).

    Method B (dual representation, strong consistency):
    - both present and canonically EQUAL → use the external one (authority);
    - both present and DIFFERENT → fail closed (never build an inconsistent
      snapshot, never silently ignore one);
    - only external present → use it (normalized);
    - only embedded present → fail closed: eligibility runs on the external
      ledger, so an embedded-only ledger would be silently ignored — the
      caller must normalize it into ``SnapshotEvidenceItem.source_ledger``
      before ingestion;
    - neither present → None (eligibility fail-closes to quarantine).
    """
    if embedded is not None and external is not None:
        if embedded.model_dump(mode="json") != external.model_dump(mode="json"):
            raise SnapshotBuildError(
                f"dual ledger disagreement for reaction {reaction_id!r}: "
                f"ReactionEvidence.source_reaction_ledger (embedded) and "
                f"SnapshotEvidenceItem.source_ledger (external) are both "
                f"present but not canonically equal. Fail-closed (§5.4): a "
                f"snapshot must not be built from inconsistent ledgers."
            )
        return external
    if embedded is not None and external is None:
        raise SnapshotBuildError(
            f"dual ledger authority for reaction {reaction_id!r}: an embedded "
            f"ReactionEvidence.source_reaction_ledger is present but the "
            f"external SnapshotEvidenceItem.source_ledger is None. Eligibility "
            f"runs on the external ledger, so the embedded ledger would be "
            f"silently ignored. Normalize the ledger into "
            f"SnapshotEvidenceItem.source_ledger before ingestion (§5.4)."
        )
    return external


def _source_content_hash(classified: list[_ClassifiedRecord]) -> dict[str, str]:
    """Compute a per-source content hash from classified records (deterministic).

    For each source_name, hash the sorted list of record content hashes from
    that source. This is the ``source_files`` field in the on-disk manifest.
    Uses the already-classified record hashes — no redundant re-decision of
    eligibility (the classification is computed once in ``_classify_all``).
    """
    by_source: dict[str, list[str]] = {}
    for r in classified:
        src = r.reaction_evidence.source_name
        by_source.setdefault(src, []).append(r.record_content_hash)
    return {
        src: canonical_hash(sorted(hashes)) for src, hashes in by_source.items()
    }


def _build_config_hash(config: BuildConfig) -> str:
    """Hash the BuildConfig canonically (deterministic).

    §16.6: path fields (output_snapshot_root) and runtime-only fields (timeout)
    are EXCLUDED from the content hash — only content-affecting fields are
    hashed. This ensures two builds with the same content but different output
    paths produce the same snapshot hash.
    """
    cfg = config.model_dump(mode="json")
    # Strip path / runtime fields — they do not affect snapshot content
    content_only = {
        k: v for k, v in cfg.items()
        if k not in ("output_snapshot_root", "timeout")
    }
    return canonical_hash(content_only)


def _compute_canonical_snapshot_content(
    config: BuildConfig,
    build_info: BuildInfo,
    classified: list[_ClassifiedRecord],
    source_hashes: dict[str, str],
) -> dict:
    """Build the canonical content payload for the snapshot hash.

    §16.6: this payload EXCLUDES timestamp, temp path, run ID, and unordered
    iteration. Record hashes are sorted. Source hashes are sorted by key.
    """
    strict_records = [r for r in classified if r.lane == "strict"]
    conditional_records = [r for r in classified if r.lane == "conditional"]
    diagnostic_records = [r for r in classified if r.lane == "diagnostic"]
    quarantine_records = [r for r in classified if r.lane == "quarantine"]

    production_hashes = sorted(
        r.record_content_hash for r in strict_records + conditional_records
    )
    diagnostic_hashes = sorted(
        r.record_content_hash for r in diagnostic_records
    )
    quarantine_hashes = sorted(
        r.record_content_hash for r in quarantine_records
    )
    production_index_hash = canonical_hash(production_hashes)
    # Round 8: the diagnostic index is bound into the immutable snapshot
    # integrity — a diagnostic member can no longer be silently deleted without
    # changing the snapshot hash (R8-02 closed).
    diagnostic_index_hash = canonical_hash(diagnostic_hashes)
    quarantine_index_hash = canonical_hash(quarantine_hashes)

    # failure_counts_by_reason: count quarantine + diagnostic by reason
    failure_counts: dict[str, int] = {}
    for r in quarantine_records + diagnostic_records:
        reason = r.decision.reason
        # Bucket by a short reason key (first 60 chars for stability)
        key = reason[:60] if len(reason) > 60 else reason
        failure_counts[key] = failure_counts.get(key, 0) + 1

    all_record_hashes = sorted(r.record_content_hash for r in classified)

    return {
        "schema_version": build_info.schema_version,
        "build_config_hash": _build_config_hash(config),
        "versions": {
            "package_version": build_info.package_version,
            "mapper_version": config.mapper_version,
            "normalization_version": config.normalization_version,
            "role_policy_version": config.role_policy_version,
            "lineage_resolver_version": config.lineage_resolver_version,
            "ledger_version": config.ledger_version,
            "eligibility_policy_version": config.eligibility_policy_version,
            "eligibility_engine_version": ELIGIBILITY_ENGINE_VERSION,
            "builder_version": BUILDER_VERSION,
        },
        "source_content_hashes": dict(sorted(source_hashes.items())),
        "record_count": len(classified),
        "counts": {
            "strict": len(strict_records),
            "conditional": len(conditional_records),
            "diagnostic": len(diagnostic_records),
            "quarantine": len(quarantine_records),
        },
        "record_content_hashes": all_record_hashes,
        "production_index_hash": production_index_hash,
        "diagnostic_index_hash": diagnostic_index_hash,
        "quarantine_index_hash": quarantine_index_hash,
        "policy_version": build_info.policy_version,
    }


def _compute_snapshot_hash(canonical_content: dict) -> str:
    """Compute the final snapshot hash from the canonical content."""
    return canonical_hash(canonical_content)


def compute_snapshot_hash(
    config: BuildConfig,
    items: list[SnapshotEvidenceItem],
) -> str:
    """Compute the canonical snapshot content hash WITHOUT writing to disk.

    Deterministic: same config + same items → same hash. Does not include
    timestamp, run ID, or temp path.
    """
    build_info = get_build_info()
    classified = _classify_all(items)
    source_hashes = _source_content_hash(classified)
    canonical = _compute_canonical_snapshot_content(
        config, build_info, classified, source_hashes,
    )
    return _compute_snapshot_hash(canonical)


def _classify_all(items: list[SnapshotEvidenceItem]) -> list[_ClassifiedRecord]:
    """Run eligibility decision on all items, classify into lanes.

    Does NOT mutate inputs. Returns a list of _ClassifiedRecord.
    """
    classified: list[_ClassifiedRecord] = []
    for item in items:
        evidence = item.reaction_evidence
        # §5.4: resolve the single authoritative ledger from the embedded
        # (ReactionEvidence.source_reaction_ledger) and external
        # (SnapshotEvidenceItem.source_ledger) representations. Disagreement or
        # an ignored embedded-only ledger fails closed.
        ledger = _resolve_ledger_authority(
            evidence.reaction_id, evidence.source_reaction_ledger, item.source_ledger,
        )
        lineages = list(item.lineages)  # shallow copy — no mutation
        decision = decide_eligibility(evidence, ledger, lineages)
        quarantine_record = build_quarantine_record(decision, evidence)
        lane = _classify_lane(decision)
        record_hash = _record_content_hash(
            evidence, decision, quarantine_record, ledger, lineages, lane,
        )
        classified.append(_ClassifiedRecord(
            reaction_evidence=evidence,
            decision=decision,
            quarantine_record=quarantine_record,
            record_content_hash=record_hash,
            lane=lane,
            source_ledger=ledger,
            lineages=lineages,
        ))
    return classified


# =====================================================================
# On-disk manifest (richer than SnapshotManifest — §16.3)
# =====================================================================

def _build_on_disk_manifest(
    snapshot_id: str,
    config: BuildConfig,
    build_info: BuildInfo,
    classified: list[_ClassifiedRecord],
    source_hashes: dict[str, str],
    canonical_content: dict,
    snapshot_hash: str,
    build_id: str,
    completed_at: str,
    build_status: str,
) -> dict:
    """Build the full §16.3 on-disk manifest dict."""
    strict_records = [r for r in classified if r.lane == "strict"]
    conditional_records = [r for r in classified if r.lane == "conditional"]
    diagnostic_records = [r for r in classified if r.lane == "diagnostic"]
    quarantine_records = [r for r in classified if r.lane == "quarantine"]

    failure_counts: dict[str, int] = {}
    for r in quarantine_records + diagnostic_records:
        reason = r.decision.reason
        key = reason[:60] if len(reason) > 60 else reason
        failure_counts[key] = failure_counts.get(key, 0) + 1

    # source_counts: records per source_name
    source_counts: dict[str, int] = {}
    for r in classified:
        src = r.reaction_evidence.source_name
        source_counts[src] = source_counts.get(src, 0) + 1

    return {
        # Core SnapshotManifest fields (T2 contract)
        "snapshot_id": snapshot_id,
        "schema_version": build_info.schema_version,
        "included_strict_count": len(strict_records),
        "conditional_count": len(conditional_records),
        "diagnostic_count": len(diagnostic_records),
        "quarantine_count": len(quarantine_records),
        "build_status": build_status,
        "snapshot_hash": snapshot_hash,
        "build_id": build_id,
        "source_counts": dict(sorted(source_counts.items())),
        "policy_version": build_info.policy_version,
        # §16.3 extended fields
        "record_count": len(classified),
        "versions": canonical_content["versions"],
        "source_files": dict(sorted(source_hashes.items())),
        "failure_counts_by_reason": dict(sorted(failure_counts.items())),
        "record_content_hashes": canonical_content["record_content_hashes"],
        "production_index_hash": canonical_content["production_index_hash"],
        "diagnostic_index_hash": canonical_content["diagnostic_index_hash"],
        "quarantine_index_hash": canonical_content["quarantine_index_hash"],
        "build_config_hash": canonical_content["build_config_hash"],
        # Traceability (NOT in canonical content hash)
        "completed_at": completed_at,
        "builder_version": BUILDER_VERSION,
    }


def _record_to_jsonl(record: _ClassifiedRecord) -> dict:
    """Serialize a classified record to a JSONL line dict.

    Writes the COMPLETE canonical payload (Critical-1 §5.3 — the entire
    ReactionEvidence model, external ledger, resolved lineages, complete
    decision, complete quarantine record, and lane) plus the single meta field
    ``record_content_hash``. The loader strips the meta field
    (``_RECORD_META_FIELDS``) to recompute the hash, so the on-disk record and
    the hashed payload are the same object (§3.2).
    """
    payload = _canonical_record_payload(
        record.reaction_evidence,
        record.decision,
        record.quarantine_record,
        record.source_ledger,
        record.lineages,
        record.lane,
    )
    return {
        **payload,
        "record_content_hash": record.record_content_hash,
    }


def _write_jsonl(path: str, records: list[dict]) -> None:
    """Write records as JSONL (one JSON object per line)."""
    resolved = assert_no_legacy_write(path)
    with open(resolved, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def _write_manifest(path: str, manifest: dict) -> None:
    """Write the manifest JSON (sorted keys, deterministic)."""
    resolved = assert_no_legacy_write(path)
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")


def _verify_artifacts(snap_dir: str) -> None:
    """Verify all artifacts in the snapshot dir can be read back.

    Raises SnapshotBuildError if any artifact is missing or corrupt.
    """
    manifest_path = os.path.join(snap_dir, _MANIFEST_FILENAME)
    if not os.path.exists(manifest_path):
        raise SnapshotBuildError(f"manifest.json missing after write: {snap_dir}")
    # Read back manifest to verify it's valid JSON
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    required_keys = {"snapshot_id", "snapshot_hash", "build_status"}
    missing = required_keys - set(manifest)
    if missing:
        raise SnapshotBuildError(f"manifest.json missing keys: {missing}")
    # Verify index files are readable JSONL
    for index_name in (_PRODUCTION_INDEX, _DIAGNOSTIC_INDEX, _QUARANTINE_INDEX, _RECORDS_FILENAME):
        index_path = os.path.join(snap_dir, index_name)
        if not os.path.exists(index_path):
            raise SnapshotBuildError(f"{index_name} missing after write")
        with open(index_path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    raise SnapshotBuildError(
                        f"{index_name} line {line_no} corrupt: {e}"
                    ) from e


# =====================================================================
# Public API: build_snapshot
# =====================================================================

def build_snapshot(
    config: BuildConfig,
    evidence_iter: Iterable[SnapshotEvidenceItem],
    *,
    build_id: str | None = None,
) -> SnapshotManifest:
    """Build an immutable content-addressed snapshot. Atomic finalize.

    Pipeline (§16.1):
    1. Materialize evidence_iter (iterate once)
    2. Run T9 eligibility decision on each item → classify into lane
    3. Build production / diagnostic / quarantine indices
    4. Compute canonical snapshot hash (§16.6 — excludes timestamp/run ID)
    5. Atomic finalize (§16.4): temp dir → verify → atomic rename → complete=true

    Atomicity (§16.4):
    - All artifacts are written to a temp directory first.
    - After verification, the temp dir is atomically renamed to the final path.
    - If any step fails, the temp dir is cleaned up and the final path is
      never created.
    - An existing complete immutable snapshot is NEVER overwritten
      (``SnapshotExistsError``).

    Determinism (§16.6):
    - Same source + same versions + same config → identical snapshot hash.
    - Record hashes are sorted before hashing (input order does not matter).
    - timestamp / run ID / temp path are NOT in the canonical content hash.

    Immutability: inputs (config, evidence items) are NOT mutated.

    Concurrency: single-process batch assumed. Concurrent builds targeting the
    same snapshot_id may race on rmtree/rename (§16.4 does not require
    concurrent safety; the rmtree on a stale incomplete final dir and the
    rename of temp → final are not guarded against a concurrent writer).

    Args:
        config: BuildConfig with output_snapshot_root and version strings.
        evidence_iter: Iterable of SnapshotEvidenceItem (pre-computed T4-T8
            artifacts). Materialized once into a list.
        build_id: Optional run ID for traceability. NOT included in the
            canonical content hash.

    Returns:
        SnapshotManifest (T2 contract) with snapshot_id, hash, counts, status.

    Raises:
        SnapshotExistsError: a complete snapshot already exists at the target.
        SnapshotBuildError: build failed (iteration error, IO, verification).
    """
    build_info = get_build_info()
    if build_id is None:
        # Deterministic run ID (NOT in canonical hash; for traceability only)
        build_id = stable_id("build", {
            "builder_version": BUILDER_VERSION,
            "random_seed": config.random_seed,
        })

    # Step 1: materialize evidence_iter (iterate once)
    try:
        items = list(evidence_iter)
    except Exception as e:
        raise SnapshotBuildError(f"evidence iteration failed: {e}") from e

    # Step 2: classify all items (run T9 eligibility decision)
    classified = _classify_all(items)

    # Step 3: compute source hashes + canonical content + snapshot hash
    source_hashes = _source_content_hash(classified)
    canonical_content = _compute_canonical_snapshot_content(
        config, build_info, classified, source_hashes,
    )
    snapshot_hash = _compute_snapshot_hash(canonical_content)
    snapshot_id = stable_id("snap", canonical_content)

    # Step 4: resolve output path and check for existing snapshot
    output_root = config.output_snapshot_root
    # Guard: refuse to write to legacy paths
    output_root_resolved = assert_no_legacy_write(output_root)
    os.makedirs(output_root_resolved, exist_ok=True)
    final_dir = os.path.join(output_root_resolved, snapshot_id)

    # §16.4: do NOT overwrite an existing complete immutable snapshot
    final_manifest_path = os.path.join(final_dir, _MANIFEST_FILENAME)
    if os.path.exists(final_manifest_path):
        with open(final_manifest_path, encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("build_status") == "complete":
            raise SnapshotExistsError(
                f"complete snapshot already exists: {final_dir} "
                f"(snapshot_id={snapshot_id}). Immutable snapshots cannot be "
                f"overwritten."
            )
        # If incomplete (partial), remove it and rebuild
        shutil.rmtree(final_dir)

    # Step 5: write to temp dir
    temp_dir = os.path.join(output_root_resolved, f".tmp_{snapshot_id}")
    # Clean up any stale temp dir from a previous interrupted build
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        # Split records by lane
        strict_records = [r for r in classified if r.lane == "strict"]
        conditional_records = [r for r in classified if r.lane == "conditional"]
        diagnostic_records = [r for r in classified if r.lane == "diagnostic"]
        quarantine_records = [r for r in classified if r.lane == "quarantine"]

        # Production index = strict + conditional (excludes quarantine, §15.5)
        production_records = strict_records + conditional_records

        # Write indices (JSONL, sorted by reaction_id for determinism)
        _write_jsonl(
            os.path.join(temp_dir, _PRODUCTION_INDEX),
            [_record_to_jsonl(r) for r in sorted(production_records, key=lambda r: r.reaction_evidence.reaction_id)],
        )
        _write_jsonl(
            os.path.join(temp_dir, _DIAGNOSTIC_INDEX),
            [_record_to_jsonl(r) for r in sorted(diagnostic_records, key=lambda r: r.reaction_evidence.reaction_id)],
        )
        _write_jsonl(
            os.path.join(temp_dir, _QUARANTINE_INDEX),
            [_record_to_jsonl(r) for r in sorted(quarantine_records, key=lambda r: r.reaction_evidence.reaction_id)],
        )
        _write_jsonl(
            os.path.join(temp_dir, _RECORDS_FILENAME),
            [_record_to_jsonl(r) for r in sorted(classified, key=lambda r: r.reaction_evidence.reaction_id)],
        )

        # Build on-disk manifest with build_status="building" — complete=true
        # is set AFTER atomic rename (§16.4 H1 fix: complete LAST).
        from datetime import datetime, timezone
        completed_at = datetime.now(timezone.utc).isoformat()
        on_disk = _build_on_disk_manifest(
            snapshot_id=snapshot_id,
            config=config,
            build_info=build_info,
            classified=classified,
            source_hashes=source_hashes,
            canonical_content=canonical_content,
            snapshot_hash=snapshot_hash,
            build_id=build_id,
            completed_at=completed_at,
            build_status="building",
        )
        _write_manifest(os.path.join(temp_dir, _MANIFEST_FILENAME), on_disk)

        # Do NOT write COMPLETE marker to temp dir (§16.4 H1 fix).
        # The marker is written only after atomic rename succeeds.

        # Step 6: verify all artifacts in temp dir
        _verify_artifacts(temp_dir)

        # Step 7: atomic finalize — rename temp → final.
        # Use os.rename (NOT os.replace) so that if final_dir already exists
        # as a non-empty directory (concurrent build won the race), the rename
        # fails with ENOTEMPTY/EEXIST instead of silently overwriting (§16.4 H3 fix).
        try:
            os.rename(temp_dir, final_dir)
        except OSError as e:
            if e.errno in (errno.EEXIST, errno.ENOTEMPTY):
                # Another process completed this snapshot, or a stale dir exists.
                # Re-check: if it's now complete, refuse to overwrite.
                final_manifest = os.path.join(final_dir, _MANIFEST_FILENAME)
                if os.path.exists(final_manifest):
                    with open(final_manifest, encoding="utf-8") as f:
                        existing = json.load(f)
                    if existing.get("build_status") == "complete":
                        raise SnapshotExistsError(
                            f"complete snapshot already exists (concurrent): "
                            f"{final_dir}"
                        ) from e
                # Stale incomplete dir — remove and retry the rename
                shutil.rmtree(final_dir, ignore_errors=True)
                os.rename(temp_dir, final_dir)
            else:
                raise

        # Step 8: complete=true LAST — rewrite manifest + write COMPLETE marker
        # in the final directory. If interrupted here, the final dir has
        # build_status="building" and no marker → loader rejects, next build
        # cleans up and rebuilds (§16.4 H1 fix).
        on_disk["build_status"] = "complete"
        _write_manifest(os.path.join(final_dir, _MANIFEST_FILENAME), on_disk)

        marker_path = os.path.join(final_dir, _COMPLETE_MARKER)
        resolved_marker = assert_no_legacy_write(marker_path)
        with open(resolved_marker, "w", encoding="utf-8") as f:
            f.write(snapshot_hash)

    except Exception as e:
        # Clean up temp dir on any failure
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if isinstance(e, SnapshotExistsError):
            raise
        raise SnapshotBuildError(f"snapshot build failed: {e}") from e

    # Return SnapshotManifest (T2 contract subset)
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        schema_version=build_info.schema_version,
        included_strict_count=len(strict_records),
        conditional_count=len(conditional_records),
        diagnostic_count=len(diagnostic_records),
        quarantine_count=len(quarantine_records),
        build_status="complete",
        snapshot_hash=snapshot_hash,
        build_id=build_id,
        source_counts=dict(sorted(
            {src: sum(1 for r in classified if r.reaction_evidence.source_name == src)
             for src in source_hashes}.items()
        )),
        policy_version=build_info.policy_version,
    )
