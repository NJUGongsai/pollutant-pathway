"""Capability detection + typed blockers (CHATGPT_P3 prompt §1/§5/§7).

Determines per-run availability of:
- chemistry backend (RDKit)
- atom mapper (P1 RealMapperAdapter probe)
- real frozen snapshot artifact
- automatic donor index (a train-only P1 view)

When a capability is absent, the kernel returns a typed BLOCKED outcome
(KernelFailure category="system"), it does NOT fabricate chemical results.
"""
from __future__ import annotations

from typing import Callable

from reaction_agent.p3.schemas import (
    CapabilityState,
    ComponentCapability,
    EvidenceKind,
)


def _probe_import(module: str) -> str:
    """Return the module version string, or '' if unavailable."""
    try:
        imported = __import__(module)
    except ImportError:
        return ""
    version = getattr(imported, "__version__", None)
    return str(version) if version else "available"


def probe_chemistry_backend() -> ComponentCapability:
    version = _probe_import("rdkit")
    if not version:
        return ComponentCapability(
            component="chemistry_backend",
            state=CapabilityState.unavailable,
            detail="rdkit not importable — chemistry operations BLOCKED",
        )
    from rdkit import rdBase  # type: ignore
    return ComponentCapability(
        component="chemistry_backend",
        state=CapabilityState.available,
        version=rdBase.rdkitVersion if hasattr(rdBase, "rdkitVersion") else version,
        detail="rdkit importable",
        evidence_kind=EvidenceKind.real,
    )


def probe_explicit_map_validator() -> ComponentCapability:
    """The P1 adapter can validate EXPLICIT atom maps (not a learned mapper)."""
    from reaction_agent.mapping.adapter import RealMapperAdapter

    try:
        adapter = RealMapperAdapter(backend="rdkit")
    except Exception as exc:  # noqa: BLE001 - probe must never raise
        return ComponentCapability(
            component="explicit_map_validator",
            state=CapabilityState.unavailable,
            detail=f"RealMapperAdapter probe failed: {exc}",
        )
    if not adapter.is_available():
        return ComponentCapability(
            component="explicit_map_validator",
            state=CapabilityState.unavailable,
            detail="RealMapperAdapter backend not importable — mapping BLOCKED",
        )
    return ComponentCapability(
        component="explicit_map_validator",
        state=CapabilityState.available,
        version="rdkit",
        detail="RealMapperAdapter validates explicit atom maps (formal, not mechanism)",
        evidence_kind=EvidenceKind.real,
    )


def probe_strict_atom_mapper() -> ComponentCapability:
    """A true learned atom mapper (rxnmapper/rxn4chemistry) is NOT wired."""
    try:
        import rxnmapper  # noqa: F401
        return ComponentCapability(
            component="strict_atom_mapper",
            state=CapabilityState.available,
            version="rxnmapper",
            detail="rxnmapper importable",
            evidence_kind=EvidenceKind.real,
        )
    except ImportError:
        return ComponentCapability(
            component="strict_atom_mapper",
            state=CapabilityState.unavailable,
            detail="no learned atom mapper backend wired (rxnmapper/rxn4chemistry absent)",
        )


def probe_mcs_diagnostic() -> ComponentCapability:
    """RDKit MCS fallback exists as a DIAGNOSTIC, never as strict mapping."""
    return ComponentCapability(
        component="mcs_diagnostic",
        state=(
            CapabilityState.available
            if _probe_import("rdkit")
            else CapabilityState.unavailable
        ),
        version="rdkit",
        detail="MCS is a diagnostic fallback; it never satisfies strict mapping",
        evidence_kind=EvidenceKind.diagnostic,
    )


def probe_real_snapshot(
    snapshot_path: str | None = None,
    loader: Callable | None = None,
) -> ComponentCapability:
    """Probe for a frozen immutable real snapshot artifact.

    A snapshot is "real" when it exists on disk, is complete
    (build_status == complete), passes the P1 loader hash verification and is
    declared with evidence_kind != synthetic_fixture.
    """
    if not snapshot_path:
        return ComponentCapability(
            component="real_snapshot",
            state=CapabilityState.unavailable,
            detail="no snapshot path/id supplied — real snapshot BLOCKED",
        )
    if loader is None:
        from reaction_agent.snapshot.loader import load_snapshot

        loader = load_snapshot
    try:
        record = loader(snapshot_path)
    except Exception as exc:  # noqa: BLE001 - probe must never raise
        return ComponentCapability(
            component="real_snapshot",
            state=CapabilityState.unavailable,
            detail=f"snapshot load failed: {type(exc).__name__}: {exc}",
        )
    manifest = record.manifest
    if manifest is None or manifest.build_status != "complete":
        return ComponentCapability(
            component="real_snapshot",
            state=CapabilityState.unavailable,
            detail="snapshot manifest missing or not complete",
        )
    return ComponentCapability(
        component="real_snapshot",
        state=CapabilityState.available,
        version=manifest.snapshot_hash,
        detail=f"snapshot {record.snapshot_id} loaded, hash verified",
        evidence_kind=EvidenceKind.real,
    )


def probe_automatic_donor(snapshot_ok: bool) -> ComponentCapability:
    """Automatic donor retrieval needs a real train-only P1 view.

    Without a real snapshot there is no real train view; without a train view
    there is no automatic donor index.  Synthetic train views are explicit
    synthetic_fixture and cannot satisfy a real-evidence Gate.
    """
    if not snapshot_ok:
        return ComponentCapability(
            component="automatic_donor",
            state=CapabilityState.unavailable,
            detail="no real snapshot -> no real train-only donor view",
        )
    return ComponentCapability(
        component="automatic_donor",
        state=CapabilityState.unavailable,
        detail="real train-only donor view not wired in this environment",
    )


def build_capability_status(
    run_id: str,
    query_id: str,
    fold_id: str,
    case_id: str,
    snapshot_path: str | None = None,
) -> tuple:
    """Build a CapabilityStatus and a list of system blockers.

    Returns (capability_status, system_failures).
    """
    from reaction_agent.p3.schemas import CapabilityStatus, KernelFailure

    chemistry = probe_chemistry_backend()
    explicit_validator = probe_explicit_map_validator()
    strict_mapper = probe_strict_atom_mapper()
    mcs_diag = probe_mcs_diagnostic()
    snapshot = probe_real_snapshot(snapshot_path)
    donor = probe_automatic_donor(snapshot.state is CapabilityState.available)

    components = [
        chemistry, explicit_validator, strict_mapper, mcs_diag, snapshot, donor,
    ]
    status = CapabilityStatus(
        run_id=run_id,
        query_id=query_id,
        fold_id=fold_id,
        case_id=case_id,
        components=components,
        chemistry_backend_available=chemistry.state is CapabilityState.available,
        explicit_map_validator_available=explicit_validator.state is CapabilityState.available,
        strict_atom_mapper_available=strict_mapper.state is CapabilityState.available,
        mcs_diagnostic_available=mcs_diag.state is CapabilityState.available,
        real_snapshot_available=snapshot.state is CapabilityState.available,
        automatic_donor_available=donor.state is CapabilityState.available,
    )

    blockers: list[KernelFailure] = []
    for comp in components:
        if comp.state is not CapabilityState.available:
            blockers.append(KernelFailure(
                failure_code="CAPABILITY_UNAVAILABLE",
                category="system",
                reason=f"{comp.component} unavailable",
                component=comp.component,
                detail=comp.detail,
            ))
    return status, blockers
