"""P3 capability detection: chemistry backend, mappers, real snapshot, donor."""
from reaction_agent.p3.capability import (
    build_capability_status,
    probe_automatic_donor,
    probe_chemistry_backend,
    probe_explicit_map_validator,
    probe_mcs_diagnostic,
    probe_real_snapshot,
    probe_strict_atom_mapper,
)
from reaction_agent.p3.schemas import CapabilityState, EvidenceKind


def test_chemistry_backend_available():
    cap = probe_chemistry_backend()
    assert cap.component == "chemistry_backend"
    assert cap.state is CapabilityState.available
    assert cap.version


def test_explicit_map_validator_available():
    cap = probe_explicit_map_validator()
    assert cap.component == "explicit_map_validator"
    assert cap.state is CapabilityState.available


# -- R2-H: RDKit is NOT a strict atom mapper --------------------------------


def test_rdkit_is_not_reported_as_strict_atom_mapper():
    cap = probe_strict_atom_mapper()
    assert cap.component == "strict_atom_mapper"
    assert cap.state is CapabilityState.unavailable  # no learned mapper wired


def test_mcs_diagnostic_available_but_never_strict():
    cap = probe_mcs_diagnostic()
    assert cap.component == "mcs_diagnostic"
    # diagnostic availability is independent; it is NEVER a strict mapper.
    assert cap.state in (CapabilityState.available, CapabilityState.unavailable)
    assert "never" in cap.detail.lower()


def test_explicit_map_validator_capability_separate():
    # The explicit-map validator and the strict mapper are SEPARATE probes.
    explicit = probe_explicit_map_validator()
    strict = probe_strict_atom_mapper()
    assert explicit.component != strict.component
    assert explicit.state is CapabilityState.available
    # even if RDKit is available for explicit maps, strict mapper stays off
    assert strict.state is not CapabilityState.available


def test_mcs_diagnostic_never_satisfies_strict_mapping_gate():
    from reaction_agent.mapping.adapter import RealMapperAdapter
    # RealMapperAdapter with rdkit uses MCS fallback for un-mapped reactions;
    # that fallback must NOT flip strict_atom_mapper_available.
    status, _ = build_capability_status("r", "q", "f", "c", snapshot_path=None)
    assert status.explicit_map_validator_available is True
    assert status.mcs_diagnostic_available is True
    assert status.strict_atom_mapper_available is False


def test_real_snapshot_unavailable_without_path():
    cap = probe_real_snapshot(None)
    assert cap.component == "real_snapshot"
    assert cap.state is CapabilityState.unavailable
    assert cap.evidence_kind is EvidenceKind.blocked


def test_real_snapshot_missing_path_fails_closed():
    cap = probe_real_snapshot("/nonexistent/snapshot/dir")
    assert cap.state is CapabilityState.unavailable


def test_automatic_donor_requires_snapshot():
    assert probe_automatic_donor(snapshot_ok=False).state is CapabilityState.unavailable
    assert probe_automatic_donor(snapshot_ok=True).state is CapabilityState.unavailable


def test_capability_status_flags_consistent():
    status, blockers = build_capability_status(
        "run_x", "q_x", "fold_x", "case_x", snapshot_path=None
    )
    assert status.chemistry_backend_available is True
    assert status.explicit_map_validator_available is True
    assert status.strict_atom_mapper_available is False
    assert status.mcs_diagnostic_available is True
    assert status.real_snapshot_available is False
    assert status.automatic_donor_available is False
    assert len(blockers) >= 2  # real_snapshot + automatic_donor (+ strict mapper)
    assert all(b.category == "system" for b in blockers)
