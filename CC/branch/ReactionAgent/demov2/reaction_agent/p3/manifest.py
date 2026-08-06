"""P3->P4 frozen interface manifest builder (R2-G, R3-I).

The manifest is DERIVED from the actual Pydantic model fields + JSON schema,
never from a hand-copied field list.  A schema drift changes the schema hash
and makes the interface contract test FAIL.

R3-I: the manifest is COMPLETE for every model P4 consumes — including the
nested records (``CandidateEvidencePath``, ``GenerationReport``,
``CandidateValidation``, ``CandidateAnalogyLedger``) — and declares the
explicit nested-record contract: nested records are NOT independently
addressable; every evidence path is content-addressedly bound to the parent
run namespace through ``path_id`` / ``path_hash``.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.p3.schemas import (
    P3_SCHEMA_VERSION,
    AtomStateChange,
    BondChange,
    CandidateEvidencePath,
    CandidateTrace,
    CandidateValidation,
    CapabilityStatus,
    ComponentCapability,
    ComponentVersion,
    ConditionedSite,
    DonorContext,
    EditApplicationLog,
    GenerationReport,
    KernelFailure,
    KernelResult,
    KernelRunManifest,
    NormalizationPolicy,
    NormalizedQuery,
    RemovedSinkAssignment,
    ResolvedDonorEvidence,
    SitePrecondition,
    StageTraceEntry,
    StrictCandidate,
    StrictTransformation,
    TransferredAtom,
)
from reaction_agent.schemas.ledger import CandidateAnalogyLedger

MANIFEST_VERSION = "p3-p4-3"

_INTERFACE_MODELS = {
    # top-level run envelope
    "KernelResult": KernelResult,
    "KernelRunManifest": KernelRunManifest,
    "NormalizedQuery": NormalizedQuery,
    "ResolvedDonorEvidence": ResolvedDonorEvidence,
    "StrictTransformation": StrictTransformation,
    "ConditionedSite": ConditionedSite,
    "StrictCandidate": StrictCandidate,
    "CandidateTrace": CandidateTrace,
    "KernelFailure": KernelFailure,
    "CapabilityStatus": CapabilityStatus,
    # R3-I: nested records P4 actually consumes
    "CandidateEvidencePath": CandidateEvidencePath,
    "GenerationReport": GenerationReport,
    "CandidateValidation": CandidateValidation,
    "CandidateAnalogyLedger": CandidateAnalogyLedger,
    "EditApplicationLog": EditApplicationLog,
    # supporting typed structures
    "DonorContext": DonorContext,
    "StageTraceEntry": StageTraceEntry,
    "BondChange": BondChange,
    "AtomStateChange": AtomStateChange,
    "TransferredAtom": TransferredAtom,
    "RemovedSinkAssignment": RemovedSinkAssignment,
    "SitePrecondition": SitePrecondition,
    "NormalizationPolicy": NormalizationPolicy,
    "ComponentCapability": ComponentCapability,
    "ComponentVersion": ComponentVersion,
}

_RUN_NAMESPACE_FIELDS = (
    "run_id", "case_id", "query_id", "fold_id", "snapshot_id", "snapshot_hash",
)

# Nested records that carry NO standalone run namespace; they are bound to
# the parent namespace through the evidence-path content hash (R3-I option 2).
_NESTED_BOUND_MODELS = (
    "CandidateEvidencePath",
    "GenerationReport",
    "CandidateValidation",
    "CandidateAnalogyLedger",
    "EditApplicationLog",
    "StageTraceEntry",
    "BondChange",
    "AtomStateChange",
    "TransferredAtom",
    "RemovedSinkAssignment",
    "SitePrecondition",
    "NormalizationPolicy",
    "ComponentCapability",
    "ComponentVersion",
    "DonorContext",
)

NESTED_RECORD_CONTRACT = {
    "mode": "parent_namespace_content_binding",
    "description": (
        "Nested records are NOT independently transmitted or addressable. "
        "Every CandidateEvidencePath is content-addressedly bound to the "
        "parent StrictCandidate run namespace: path_id/path_hash are "
        "computed from a preimage that includes donor, reaction, lineage, "
        "transformation, site, generation report, source ledger, candidate "
        "analogy ledger AND the full parent run namespace "
        "(run_id/case_id/query_id/fold_id/snapshot_id/snapshot_hash). "
        "StrictCandidate recomputes the binding and rejects any mismatch, "
        "so a nested record can never be smuggled across runs or forged in "
        "isolation."
    ),
    "binding_fields": ["path_id", "path_hash"],
    "binding_version": "p3-r3-1",
    "preimage_includes": [
        "donor_id", "reaction_id", "lineage_id", "transformation_id",
        "site_id", "generation", "source_ledger_id", "candidate_ledger",
        "run_id", "case_id", "query_id", "fold_id", "snapshot_id",
        "snapshot_hash",
    ],
    "enforced_by": [
        "reaction_agent.p3.schemas.CandidateEvidencePath._linkage_consistent",
        "reaction_agent.p3.schemas.StrictCandidate._evidence_paths_binding",
    ],
}


def model_fields_of(cls) -> list[str]:
    return list(cls.model_fields.keys())


def model_required_fields_of(cls) -> list[str]:
    return sorted(
        name for name, field in cls.model_fields.items() if field.is_required()
    )


def model_schema_hash(cls) -> str:
    schema = cls.model_json_schema()
    return canonical_hash(schema)


def build_interface_manifest() -> dict:
    """Build the P3->P4 interface manifest from the live Pydantic models.

    R5-D: the manifest is a FRESH deep copy on every call — the shared
    module-level ``NESTED_RECORD_CONTRACT`` (and any other nested dict/list)
    is never returned by reference, so a caller's tamper cannot mutate the
    builder's global state for subsequent calls.
    """
    import copy as _copy

    interfaces: dict[str, dict] = {}
    for name, cls in _INTERFACE_MODELS.items():
        fields = model_fields_of(cls)
        interfaces[name] = {
            "schema_version": P3_SCHEMA_VERSION,
            "fields": fields,
            "required_fields": model_required_fields_of(cls),
            "run_namespace_fields": (
                [] if name in _NESTED_BOUND_MODELS
                else [f for f in fields if f in _RUN_NAMESPACE_FIELDS]
            ),
            "namespace_binding": (
                "content-addressed to parent run namespace via "
                "CandidateEvidencePath.path_hash"
                if name in _NESTED_BOUND_MODELS else "direct"
            ),
            "schema_hash": model_schema_hash(cls),
        }
    return {
        "manifest_version": MANIFEST_VERSION,
        "producer": "P3 strict one-step kernel",
        "consumer": "P4 (evidence/ranking/abstention)",
        "generated_from": "live_pydantic_models",
        "hash_algorithm": "sha256 (reaction_agent.hashing.canonical_hash)",
        "run_namespace_required": list(_RUN_NAMESPACE_FIELDS),
        "evidence_kind_semantics": {
            "real": "real evidence",
            "synthetic_fixture": "synthetic fixture (machinery only)",
            "blocked": "capability absent (typed blocker)",
            "diagnostic": "diagnostic / non-production",
        },
        "blocker_semantics": (
            "KernelFailure.category=system with failure_code=CAPABILITY_UNAVAILABLE "
            "means the item cannot be satisfied in this environment; P4 must not "
            "treat it as a scientific abstention or a PASS."
        ),
        "id_preimage_contract": (
            "IDs are system-generated and recomputable from canonical "
            "preimages; never derived from arbitrary input strings. "
            "reaction_hash derives from the complete reaction authority "
            "preimage; canonical_transform_hash/transformation_id derive "
            "from ONE shared transform preimage and are recomputable from "
            "the transform fields; path_id/path_hash derive from the "
            "evidence-path preimage including the parent namespace."
        ),
        "nested_record_contract": _copy.deepcopy(NESTED_RECORD_CONTRACT),
        "p4_must_not": [
            "read P3 internal mutable objects",
            "trust stored status strings over artifacts",
            "treat synthetic_fixture as real evidence",
            "treat CAPABILITY_UNAVAILABLE as scientific abstention",
            "use nested records independently of the parent candidate "
            "namespace binding",
        ],
        "interfaces": interfaces,
    }


# Explicitly declared NON-semantic display fields.  These are documentation
# metadata only (who produced / consumed / generated the manifest, and which
# hash function is used).  They are excluded from the semantic contract
# hash; EVERY other top-level manifest field is semantic and must be covered
# (R4-D).  Any future semantic field added to the manifest is automatically
# covered because it is not in this set (fail-closed on unknown fields).
NON_SEMANTIC_MANIFEST_FIELDS = frozenset({
    "producer",
    "consumer",
    "generated_from",
    "hash_algorithm",
})


def manifest_schema_hash(manifest: dict) -> str:
    """Hash of the FULL canonical semantic manifest contract (R4-D, R5-D).

    R5-D: the hash is computed over the COMPLETE canonical manifest dump
    (every top-level field AND every nested interface field, including any
    unknown semantic field added in the future).  Only the explicitly
    declared non-semantic display fields (NON_SEMANTIC_MANIFEST_FIELDS) are
    excluded via an explicit, versioned JSON path allowlist.  Interfaces are
    NOT hand-projected into a fixed subset — a new field added to any
    interface (e.g. ``interfaces.StrictCandidate.unknown_semantic_contract``)
    is automatically covered (fail-closed on unknown fields).

    The preimage is canonicalized through ``canonical_hash`` (sorted keys),
    so equivalent dict ordering never changes the hash.  Non-semantic
    display fields (producer/consumer/generated_from/hash_algorithm) may
    change without changing the hash.
    """
    preimage = {
        key: value
        for key, value in manifest.items()
        if key not in NON_SEMANTIC_MANIFEST_FIELDS
    }
    return canonical_hash(preimage)
