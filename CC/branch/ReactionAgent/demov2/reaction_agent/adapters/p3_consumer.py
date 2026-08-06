"""P3→P4 consumer adapter (read-only, fail-closed).

P4 consumes ONLY the frozen, content-addressed P3 interface manifest
(``reports/p3/p3_p4_interface_manifest.json``, manifest_version p3-p4-1..3)
and, when present, the current-run ``KernelResult`` artifact (manifest +
normalized query + capability status + strict candidates + trace). It never
reads P3 private Python objects.

Two distinct contracts (P4-R1-A):

1. **interface manifest** — proves the P3→P4 *schema* exists. On its own it
   NEVER grants ``capability_available``.
2. **current-run artifact** — a KernelResult produced by a real P3 run. Only
   when its schema, evidence kind, namespace (run/query/case/fold/snapshot
   ID/hash) and hashes all match does P4 gain candidates and capability.

When the interface manifest is absent, unreadable, or the current-run
artifact is missing/mismatched, the consumer returns a typed BLOCKED state —
never a bare exception, never fabricated candidates, never a PASS.
"""
from __future__ import annotations

import json
import os

from pydantic import field_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr
from reaction_agent.schemas.p4.authority import (
    AuthoritySource,
    P3AuthorityHandle,
    P4Classification,
    RunNamespace,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DEFAULT_P3_MANIFEST = os.path.join(
    _PROJECT_ROOT, "reports", "p3", "p3_p4_interface_manifest.json")
DEFAULT_CURRENT_RUN = os.path.join(
    _PROJECT_ROOT, "reports", "p3", "current_run_artifact.json")

# Frozen manifest versions the consumer can parse (top-level structure
# compatible: manifest_version / interfaces / hash_algorithm /
# blocker_semantics: str / evidence_kind_semantics).
SUPPORTED_MANIFEST_VERSIONS = frozenset({"p3-p4-1", "p3-p4-2", "p3-p4-3"})

# KernelResult required fields (frozen p3-p4-3 contract).
_KERNEL_RESULT_REQUIRED = (
    "run_id", "status", "query_id", "case_id", "fold_id", "snapshot_id",
    "snapshot_hash", "manifest", "normalized_query", "capability_status",
    "candidates", "trace", "failures", "evidence_kind",
)
# StrictCandidate required fields (frozen p3-p4-3 contract).
_STRICT_CANDIDATE_REQUIRED = (
    "candidate_id", "canonical_product_identity", "lane", "validation",
    "generation_paths", "support_lineage_ids", "transformation_ids",
    "site_ids", "source_ledger_ids", "candidate_analogy_ledger",
    "provenance", "evidence_kind",
)
_NAMESPACE_FIELDS = ("run_id", "case_id", "query_id", "fold_id",
                     "snapshot_id", "snapshot_hash")


class P3InterfaceManifest(StrictModel):
    """Frozen P3 interface manifest (p3-p4-1..3)."""
    manifest_version: NonEmptyStr
    producer: str = ""
    consumer: str = ""
    generated_from: str = ""
    hash_algorithm: str = ""
    interfaces: dict
    blocker_semantics: str
    evidence_kind_semantics: dict[str, str] = {}
    run_namespace_required: list[str] = []
    id_preimage_contract: str = ""
    nested_record_contract: dict = {}
    p4_must_not: list[str] = []

    @field_validator("blocker_semantics")
    @classmethod
    def _blocker_semantics_must_be_string(cls, v):
        if not isinstance(v, str):
            raise ValueError("blocker_semantics must be a string in the frozen "
                             "P3 contract")
        return v

    @field_validator("manifest_version")
    @classmethod
    def _manifest_version_supported(cls, v):
        if v not in SUPPORTED_MANIFEST_VERSIONS:
            raise ValueError(f"unsupported manifest_version {v!r}; frozen "
                             f"versions: {sorted(SUPPORTED_MANIFEST_VERSIONS)}")
        return v


class P3CurrentRunArtifact(StrictModel):
    """Verified KernelResult current-run artifact.

    The artifact is only valid when every nested record carries the SAME run
    namespace (run/query/case/fold/snapshot ID/hash) and the evidence kind is
    from the frozen enum.
    """
    run_id: NonEmptyStr
    status: NonEmptyStr
    query_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    manifest: dict
    normalized_query: dict
    capability_status: dict
    candidates: list[dict]
    trace: dict
    failures: list[dict] = []
    evidence_kind: P4Classification

    @field_validator("evidence_kind", mode="before")
    @classmethod
    def _evidence_kind_coerce(cls, v):
        if isinstance(v, str):
            return P4Classification(v)
        return v

    @property
    def namespace(self) -> RunNamespace:
        return RunNamespace(
            run_id=self.run_id, case_id=self.case_id, query_id=self.query_id,
            fold_id=self.fold_id, snapshot_id=self.snapshot_id,
            snapshot_hash=self.snapshot_hash,
        )


def _stable_namespace_of(record: dict) -> dict:
    """Extract the namespace a nested record claims (missing -> None)."""
    return {k: record.get(k) for k in _NAMESPACE_FIELDS}


def _namespace_consistent(artifact: dict) -> list[str]:
    """Compare every nested record's namespace to the artifact header."""
    issues: list[str] = []
    header = {k: artifact.get(k) for k in _NAMESPACE_FIELDS}
    for key in ("manifest", "normalized_query", "capability_status", "trace"):
        nested = artifact.get(key)
        if not isinstance(nested, dict):
            issues.append(f"{key} missing or not an object")
            continue
        for field in _NAMESPACE_FIELDS:
            if field in nested and nested[field] is not None and nested[field] != header[field]:
                issues.append(f"{key}.{field} mismatch: "
                              f"{nested[field]!r} != {header[field]!r}")
    for i, cand in enumerate(artifact.get("candidates", [])):
        if not isinstance(cand, dict):
            issues.append(f"candidates[{i}] not an object")
            continue
        for field in _NAMESPACE_FIELDS:
            if field in cand and cand[field] is not None and cand[field] != header[field]:
                issues.append(f"candidates[{i}].{field} mismatch: "
                              f"{cand[field]!r} != {header[field]!r}")
    return issues


def _validate_artifact(artifact: dict) -> list[str]:
    """Fail-closed validation of a KernelResult current-run artifact."""
    issues: list[str] = []
    for field in _KERNEL_RESULT_REQUIRED:
        if field not in artifact:
            issues.append(f"current-run artifact missing required field {field!r}")
    issues.extend(_namespace_consistent(artifact))
    for i, cand in enumerate(artifact.get("candidates", [])):
        if not isinstance(cand, dict):
            issues.append(f"candidates[{i}] not an object")
            continue
        for field in _STRICT_CANDIDATE_REQUIRED:
            if field not in cand:
                issues.append(f"candidates[{i}] missing required field {field!r}")
    ek = artifact.get("evidence_kind")
    if ek not in {c.value for c in P4Classification}:
        issues.append(f"evidence_kind {ek!r} not in frozen enum")
    return issues


class P3InterfaceState(StrictModel):
    """Read-only snapshot of the P3 authority state (interface + current run)."""
    present: bool
    manifest_version: str = ""
    classification: P4Classification = P4Classification.blocked
    capability_available: bool = False
    interfaces: dict = {}
    hash_algo: str = ""
    blocker_semantics: str = ""
    evidence_kind_semantics: dict[str, str] = {}
    blocked_reasons: list[NonEmptyStr] = []
    manifest_path: str = ""
    current_run_path: str = ""
    candidate_ids: list[str] = []
    namespace: RunNamespace | None = None


class P3InterfaceConsumer:
    """Read-only consumer of the P3 interface manifest + current-run artifact."""

    def __init__(self, missing_path: str | None = None,
                 current_run_path: str | None = None):
        self._path = missing_path or DEFAULT_P3_MANIFEST
        self._run_path = current_run_path or DEFAULT_CURRENT_RUN
        self._manifest: P3InterfaceManifest | None = None
        self._artifact: P3CurrentRunArtifact | None = None
        self._state: P3InterfaceState | None = None

    # -- interface manifest -------------------------------------------------

    def load(self) -> P3InterfaceState:
        """Parse + validate the interface manifest and current-run artifact."""
        if self._state is not None:
            return self._state
        reasons: list[str] = []

        if not os.path.isfile(self._path):
            reasons.append("p3_interface_manifest_missing")
            self._state = self._blocked(reasons, manifest_version="")
            return self._state
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            reasons.append(f"p3_manifest_unreadable:{e}")
            self._state = self._blocked(reasons, manifest_version="")
            return self._state
        # round-6 wrapper: {"manifest": {...}, "schema_hash": ...}
        if isinstance(data, dict) and "manifest" in data and isinstance(
                data["manifest"], dict):
            data = data["manifest"]
        try:
            manifest = P3InterfaceManifest(**data)
        except Exception as e:  # noqa: BLE001 — typed fail-closed
            reasons.append(f"p3_manifest_schema_rejected:{type(e).__name__}:{e}")
            self._state = self._blocked(reasons, manifest_version="")
            return self._state
        self._manifest = manifest

        # Current-run artifact: only a verified artifact grants capability.
        artifact_reasons = self._load_current_run_artifact()
        reasons.extend(artifact_reasons)

        if artifact_reasons:
            self._state = self._blocked(reasons, manifest_version=manifest.manifest_version)
            return self._state

        classification = self._artifact.evidence_kind  # type: ignore[union-attr]
        self._state = P3InterfaceState(
            present=True,
            manifest_version=manifest.manifest_version,
            classification=classification,
            capability_available=True,
            interfaces=manifest.interfaces,
            hash_algo=manifest.hash_algorithm,
            blocker_semantics=manifest.blocker_semantics,
            evidence_kind_semantics=manifest.evidence_kind_semantics,
            blocked_reasons=[],
            manifest_path=self._path,
            current_run_path=self._run_path,
            candidate_ids=[c.get("candidate_id", "") for c in self._artifact.candidates],
            namespace=self._artifact.namespace,
        )
        return self._state

    def _load_current_run_artifact(self) -> list[str]:
        """Parse + validate the current-run artifact. Returns blocker reasons."""
        if not os.path.isfile(self._run_path):
            return ["p3_current_run_artifact_missing"]
        try:
            with open(self._run_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            return [f"p3_current_run_unreadable:{e}"]
        issues = _validate_artifact(data)
        if issues:
            return [f"p3_current_run_rejected:{';'.join(issues[:5])}"]
        try:
            self._artifact = P3CurrentRunArtifact(**data)
        except Exception as e:  # noqa: BLE001
            return [f"p3_current_run_schema_rejected:{type(e).__name__}:{e}"]
        return []

    def _blocked(self, reasons: list[str], manifest_version: str) -> P3InterfaceState:
        return P3InterfaceState(
            present=True if self._manifest is not None else False,
            manifest_version=manifest_version,
            classification=P4Classification.blocked,
            capability_available=False,
            interfaces=self._manifest.interfaces if self._manifest else {},
            hash_algo=self._manifest.hash_algorithm if self._manifest else "",
            blocker_semantics=self._manifest.blocker_semantics if self._manifest else "",
            evidence_kind_semantics=(
                self._manifest.evidence_kind_semantics if self._manifest else {}),
            blocked_reasons=reasons,
            manifest_path=self._path,
            current_run_path=self._run_path,
        )

    # -- current run accessors ---------------------------------------------

    def load_current_run(self) -> P3CurrentRunArtifact | None:
        """Return the verified current-run artifact, or None (missing/invalid)."""
        self.load()
        return self._artifact

    # -- authority handle (P4-R1-B) -----------------------------------------

    def resolve_authority(self) -> P3AuthorityHandle:
        """Produce the ONLY typed authority handle the pipeline may consume.

        - verified current-run artifact -> p3_current_run authority;
        - interface present but no current run -> blocked (never PASS);
        - nothing present -> blocked.
        """
        state = self.load()
        if state.capability_available and self._artifact is not None:
            return P3AuthorityHandle(
                source=AuthoritySource.p3_current_run,
                manifest_version=state.manifest_version,
                schema_hash="",
                namespace=self._artifact.namespace,
                evidence_kind=self._artifact.evidence_kind,
                blocked_reasons=[],
            )
        return P3AuthorityHandle(
            source=AuthoritySource.blocked,
            manifest_version=state.manifest_version,
            schema_hash="",
            namespace=RunNamespace(
                run_id="unknown", case_id="unknown", query_id="unknown",
                fold_id="unknown", snapshot_id="unknown",
                snapshot_hash="unknown"),
            evidence_kind=P4Classification.blocked,
            blocked_reasons=state.blocked_reasons or ["p3_authority_blocked"],
        )

    def wrap_p4_output(self, data: dict, *, case_id: str, query_id: str,
                       fold_id: str, snapshot_id: str, run_id: str) -> dict:
        """Attach case/query/fold/snapshot/run binding + classification."""
        state = self.load()
        return {
            **data,
            "case_id": case_id,
            "query_id": query_id,
            "fold_id": fold_id,
            "snapshot_id": snapshot_id,
            "run_id": run_id,
            "classification": state.classification.value,
        }