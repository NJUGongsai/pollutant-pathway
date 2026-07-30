"""P1-T4 Atom-mapping adapter — contract tests.

Tests define the contract for the AtomMapper Protocol + FakeAtomMapper +
compute_quality_flags + RealMapperAdapter skeleton.

Design references (training/chatgpt_p1_train.md):
- §10.1: Adapter protocol — must capture mapper_name/version/parameters/
  input_hash/output_hash/runtime/timeout/status/quality_flags.
- §10.2: Frozen mapping statuses (fully_mapped/partially_mapped/unmapped/
  mapping_failed/mapping_ambiguous). "调用成功" ≠ "fully_mapped".
- §10.3: 8 quality dimensions.
- §10.4: Formal ≠ mechanistic — generic mapper produces formal ONLY, never
  auto-generates mechanistic_atom_origin.
- §10.5: MCS/center-pair fallback must set fallback_method, downgrade status,
  not enter strict, not pretend full mapping.
- §10.6: Required test cases.
- §10.7: When real mapper unavailable, T4 marks UNIT_CONTRACT_COMPLETE /
  INTEGRATION_BLOCKED (not PASS).

Integration test discipline (per user instruction): no skipif. When the real
mapper is unavailable (Preflight BLOCKED: rdkit/numpy/networkx/scipy absent),
the integration test verifies the adapter correctly reports INTEGRATION_BLOCKED
— it does NOT skip.
"""
import os
import time

import pytest

from reaction_agent.schemas.common import (
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
)
from reaction_agent.schemas.mapping import MappingReport, FormalSourceAssignment
from reaction_agent.schemas.p1_entities import NormalizedReactionRecord


# -- Fixtures --

def _record(
    reaction_id: str = "r1",
    normalized_reaction: str = "CCO>>CC=O",
    source_record_id: str = "s1",
) -> NormalizedReactionRecord:
    """Deterministic NormalizedReactionRecord for unit tests."""
    return NormalizedReactionRecord(
        reaction_id=reaction_id,
        normalized_reaction=normalized_reaction,
        source_record_id=source_record_id,
    )


# =====================================================================
# Step 2 (brief): Protocol + fake mapper tests (RED → GREEN)
# =====================================================================

def test_fake_mapper_returns_mapping_report():
    """§10.1: FakeAtomMapper.map_reaction returns a MappingReport."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    assert isinstance(rep, MappingReport)
    assert rep.mapping_status in MappingStatus
    assert rep.mapper_name == "fake"


def test_fully_mapped_status():
    """§10.2: fully_mapped status is produced correctly."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    assert m.map_reaction(_record()).mapping_status == MappingStatus.fully_mapped


def test_mapping_failed_not_full():
    """§10.2: mapping_failed is distinct from fully_mapped."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="mapping_failed")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped
    assert rep.mapping_status == MappingStatus.mapping_failed


def test_mapper_does_not_create_mechanism():
    """§10.4: Generic mapper produces formal mapping ONLY — no mechanistic evidence."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    # formal_mapped_source_assignment is the typed formal object (authoritative)
    assert rep.formal_mapped_source_assignment is not None
    # mechanistic_atom_origin must NEVER be auto-populated by a generic mapper
    assert rep.mechanistic_atom_origin is None
    # flat mechanistic_origin_evidence_ids must be empty (no unbound evidence)
    assert rep.mechanistic_origin_evidence_ids == []


def test_quality_flags_computed():
    """§10.3: compute_quality_flags returns a list of quality dimension strings."""
    from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    flags = compute_quality_flags(rep)
    assert isinstance(flags, list)
    assert len(flags) > 0
    # Each flag must be a non-empty string
    for f in flags:
        assert isinstance(f, str) and len(f) > 0


def test_mcs_fallback_not_strict():
    """§10.5: MCS fallback must NOT produce fully_mapped status."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="partially_mapped", fallback="mcs")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped
    assert rep.fallback_method == "mcs"


# =====================================================================
# Additional §10.6 contract tests
# =====================================================================

def test_unmapped_status():
    """§10.6: unmapped status is produced correctly."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="unmapped")
    rep = m.map_reaction(_record())
    assert rep.mapping_status == MappingStatus.unmapped
    assert rep.mapped_heavy_atom_fraction == 0.0


def test_mapping_ambiguous_status():
    """§10.6: mapping_ambiguous status is produced correctly."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="mapping_ambiguous")
    rep = m.map_reaction(_record())
    assert rep.mapping_status == MappingStatus.mapping_ambiguous


def test_mcs_fallback_downgrades_full_to_partial():
    """§10.5: Even if status=fully_mapped is requested, MCS fallback must downgrade.

    MCS fallback must never pretend full atom correspondence (§10.5: '不伪装成
    full atom correspondence'). The adapter must enforce this invariant even
    when the caller passes an inconsistent status+fallback combination.
    """
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped", fallback="mcs")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped
    assert rep.fallback_method == "mcs"
    # assignment_method must reflect MCS (formal_mcs), not formal_mapped
    assert rep.formal_mapped_source_assignment.assignment_method == (
        SourceAssignmentMethod.formal_mcs
    )


def test_center_pair_fallback_not_strict():
    """§10.5: center-pair diagnostic fallback must NOT produce fully_mapped."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped", fallback="center_pair")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped
    assert rep.fallback_method == "center_pair"


def test_duplicate_map_ids_flagged():
    """§10.6: duplicate map IDs must set map_number_uniqueness=False."""
    from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
    m = FakeAtomMapper(status="fully_mapped", duplicate_map_ids=True)
    rep = m.map_reaction(_record())
    assert rep.map_number_uniqueness is False
    flags = compute_quality_flags(rep)
    assert any("duplicate_map_ids=detected" in f for f in flags)


def test_symmetry_ambiguity_flagged():
    """§10.6: symmetric atoms must set symmetry_ambiguity=True."""
    from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
    m = FakeAtomMapper(status="fully_mapped", symmetry_ambiguity=True)
    rep = m.map_reaction(_record())
    assert rep.symmetry_ambiguity is True
    flags = compute_quality_flags(rep)
    assert any("symmetry_ambiguity=detected" in f for f in flags)


def test_resonance_tautomer_ambiguity_flagged():
    """§10.6: resonance/tautomer ambiguity must be flagged."""
    from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
    m = FakeAtomMapper(status="fully_mapped", resonance_tautomer_ambiguity=True)
    rep = m.map_reaction(_record())
    assert rep.resonance_tautomer_ambiguity is True
    flags = compute_quality_flags(rep)
    assert any("resonance_tautomer_ambiguity=detected" in f for f in flags)


def test_deterministic_output_same_input_hash():
    """§10.1: Same input must produce same input_hash and output_hash."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    rep1 = m.map_reaction(_record())
    rep2 = m.map_reaction(_record())
    assert rep1.input_hash == rep2.input_hash
    assert rep1.output_hash == rep2.output_hash


def test_different_input_different_hash():
    """§10.1: Different input must produce different input_hash."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    rep1 = m.map_reaction(_record(reaction_id="r1", normalized_reaction="CCO>>CC=O"))
    rep2 = m.map_reaction(_record(reaction_id="r2", normalized_reaction="CC>>CC"))
    assert rep1.input_hash != rep2.input_hash


def test_input_hash_output_hash_non_empty():
    """§10.1: input_hash and output_hash must be non-empty strings."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    assert isinstance(rep.input_hash, str) and len(rep.input_hash) > 0
    assert isinstance(rep.output_hash, str) and len(rep.output_hash) > 0


def test_mapper_version_non_empty():
    """§10.1: mapper_version must be non-empty."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    assert isinstance(rep.mapper_version, str) and len(rep.mapper_version) > 0


def test_mapper_parameters_contain_timeout():
    """§10.1: mapper_parameters must capture timeout (§10.1 capture list)."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(timeout=60)
    rep = m.map_reaction(_record())
    assert "timeout" in rep.mapper_parameters
    assert rep.mapper_parameters["timeout"] == "60"


def test_formal_assignment_typed_object_present():
    """§10.4: formal_mapped_source_assignment is a typed FormalSourceAssignment."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    fma = rep.formal_mapped_source_assignment
    assert fma is not None
    assert isinstance(fma, FormalSourceAssignment)
    assert fma.mapper_name == "fake"
    # Formal assignment has atom pairs (typed, not arbitrary dict)
    assert len(fma.mapped_atom_pairs) > 0


def test_formal_assignment_absent_when_failed():
    """When mapping fails, formal assignment may be empty but must not be mechanistic."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="mapping_failed")
    rep = m.map_reaction(_record())
    # Even on failure, mechanistic evidence must not be fabricated
    assert rep.mechanistic_atom_origin is None
    assert rep.mechanistic_origin_evidence_ids == []


def test_quality_flags_eight_dimensions():
    """§10.3: compute_quality_flags must cover all 8 quality dimensions."""
    from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    flags = compute_quality_flags(rep)
    flag_text = " ".join(flags)
    # All 8 §10.3 dimensions must be present
    required = [
        "map_number_uniqueness",
        "mapped_heavy_atom_fraction",
        "changed_atom_coverage",
        "reactant_product_map_consistency",
        "duplicate_map_ids",
        "unmapped_changed_atoms",
        "symmetry_ambiguity",
        "resonance_tautomer_ambiguity",
    ]
    for dim in required:
        assert dim in flag_text, f"quality flag {dim!r} missing from {flags!r}"


def test_quality_flags_attached_to_report():
    """The report's quality_flags field is populated with computed flags."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    assert len(rep.quality_flags) > 0
    # All 8 dimensions present in the report's quality_flags
    flag_text = " ".join(rep.quality_flags)
    assert "map_number_uniqueness" in flag_text


def test_timeout_parameter_recorded():
    """§10.1: timeout is captured in mapper_parameters."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(timeout=120)
    rep = m.map_reaction(_record())
    assert rep.mapper_parameters["timeout"] == "120"


def test_invalid_status_rejected():
    """FakeAtomMapper rejects unknown status strings."""
    from reaction_agent.mapping.adapter import FakeAtomMapper
    with pytest.raises((ValueError, KeyError)):
        FakeAtomMapper(status="not_a_real_status")


def test_atom_mapper_protocol_satisfied():
    """FakeAtomMapper satisfies the AtomMapper Protocol structurally."""
    from reaction_agent.mapping.base import AtomMapper
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper()
    # Structural check: has map_reaction method
    assert hasattr(m, "map_reaction")
    assert callable(m.map_reaction)
    # AtomMapper is a Protocol — structural typing, not runtime isinstance
    # but we verify the method signature is compatible


# =====================================================================
# Step 6 (brief): Real mapper integration — no skip, INTEGRATION_BLOCKED aware
# =====================================================================

def test_real_mapper_integration_handles_unavailable_backend():
    """§10.7: When real mapper is unavailable, adapter must report INTEGRATION_BLOCKED.

    This test does NOT use skipif — it always runs. When the real mapper
    backend is unavailable (Preflight BLOCKED: rdkit/numpy/networkx/scipy
    absent), the test verifies that RealMapperAdapter correctly raises
    NotImplementedError with the INTEGRATION_BLOCKED marker. When the backend
    IS available, the test runs the actual integration.

    Per user instruction: skipif would produce a skip (violating 'zero skip'
    discipline). Instead, the unavailable case is a passing assertion.
    """
    from reaction_agent.mapping.adapter import RealMapperAdapter

    backend = os.environ.get("P1_REAL_MAPPER_AVAILABLE", "rdkit")
    a = RealMapperAdapter(backend=backend)

    if a.is_available():
        # Real mapper available — run actual integration
        rep = a.map_reaction(_record())
        assert rep.mapper_name != "fake"
        assert rep.mapper_version
        assert isinstance(rep, MappingReport)
    else:
        # Mapper unavailable — adapter must report INTEGRATION_BLOCKED.
        # This is NOT a skip: the adapter explicitly raises so the gate
        # can act on the blocked state (§10.7).
        with pytest.raises(NotImplementedError, match="INTEGRATION_BLOCKED"):
            a.map_reaction(_record())
        # The adapter must also expose its unavailable state for gate checks
        assert a.is_available() is False


def test_real_mapper_adapter_supported_backends():
    """RealMapperAdapter declares its supported backends."""
    from reaction_agent.mapping.adapter import RealMapperAdapter
    assert hasattr(RealMapperAdapter, "SUPPORTED_BACKENDS")
    assert "rdkit" in RealMapperAdapter.SUPPORTED_BACKENDS


def test_real_mapper_adapter_rejects_unknown_backend():
    """RealMapperAdapter rejects an unknown backend name."""
    from reaction_agent.mapping.adapter import RealMapperAdapter
    with pytest.raises((ValueError, KeyError)):
        RealMapperAdapter(backend="unknown_mapper_xyz")


def test_real_mapper_adapter_probes_backend():
    """RealMapperAdapter probes backend availability on construction."""
    from reaction_agent.mapping.adapter import RealMapperAdapter
    a = RealMapperAdapter(backend="rdkit")
    # is_available returns a bool (True if rdkit importable, False otherwise)
    assert isinstance(a.is_available(), bool)


# =====================================================================
# Typed/flat consistency (§10.4 + Section 10/12 ADR-0003)
# =====================================================================

def test_typed_flat_consistency_formal():
    """§10: formal typed assignment_method is consistent with flat field.

    When formal_mapped_source_assignment is set, the flat
    source_assignment_method is derived from the typed object (not set
    independently). This is enforced by MappingReport's model_validator.
    """
    from reaction_agent.mapping.adapter import FakeAtomMapper
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    fma = rep.formal_mapped_source_assignment
    assert rep.source_assignment_method == fma.assignment_method
    assert rep.source_assignment_quality == fma.assignment_quality
    assert rep.source_assignment_ambiguity == fma.assignment_ambiguity
