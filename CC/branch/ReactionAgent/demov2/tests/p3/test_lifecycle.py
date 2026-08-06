"""P3-T9 lifecycle + kernel integration tests (final_plan §6.10, §15.4)."""
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.schemas import KernelStatus, EvidenceKind


def test_completed_lifecycle_octanol():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    assert r.status is KernelStatus.completed
    # octanol donor has 2 eligible reactions (oxidation + dehydration) -> both
    # transforms are processed and both candidates are produced (R2-B).
    identities = {c.canonical_product_identity for c in r.candidates}
    assert "CCCCCCCC=O" in identities      # octanal
    assert "C=CCCCCCC" in identities        # oct-1-ene
    stages = [s.stage.value for s in r.trace.stages]
    assert "CANDIDATES_VALIDATED" in stages
    assert "SITES_ENUMERATED" in stages
    assert r.manifest.manifest_hash


def test_replay_same_result():
    r1 = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture", seed=0)
    r2 = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture", seed=0)
    assert r1.run_id == r2.run_id
    assert r1.manifest.request_hash == r2.manifest.request_hash
    assert [c.candidate_id for c in r1.candidates] == [c.candidate_id for c in r2.candidates]
    assert [c.canonical_product_identity for c in r1.candidates] == \
        [c.canonical_product_identity for c in r2.candidates]


def test_system_failure_separate_from_scientific():
    # Real mode without a real snapshot -> typed system blockers, NOT a
    # scientific abstention.
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="real")
    assert r.status is KernelStatus.blocked
    assert all(f.category == "system" for f in r.failures)
    assert any(f.failure_code == "CAPABILITY_UNAVAILABLE" for f in r.failures)
    assert r.evidence_kind is EvidenceKind.blocked


def test_scientific_stop_not_system_failure():
    r = run_kernel(input_smiles="CCCCC", case_id="c2", fold_id="fold_fx_p3", mode="fixture")
    assert r.status is KernelStatus.completed
    assert r.candidates == []
    assert all(f.category == "scientific" for f in r.failures)
    assert any(f.failure_code == "NO_COMPATIBLE_SITE" for f in r.failures)


def test_invalid_input_scientific():
    r = run_kernel(input_smiles="C1CC1C(C(C", case_id="c3", fold_id="fold_fx_p3", mode="fixture")
    assert r.status is KernelStatus.completed
    assert r.candidates == []
    assert any(f.failure_code == "INVALID_INPUT" and f.category == "scientific"
               for f in r.failures)


def test_no_llm_structure_creation():
    # The kernel only emits structures through the deterministic compiler;
    # candidate identities are canonical SMILES, never free-text.
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    for candidate in r.candidates:
        assert candidate.origin == "deterministic_kernel"
        assert candidate.canonical_product_identity.startswith(("C", "O", "N", "c", "n", "o", "["))
        assert "SMILES" not in candidate.canonical_product_identity.upper()


def test_no_invented_ids():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    candidate_ids = {c.candidate_id for c in r.candidates}
    # All candidate IDs are system-generated and recomputable.
    for cid in candidate_ids:
        assert cid.startswith("cand_")
    # Trace references only real IDs.
    for stage in r.trace.stages:
        for eid in stage.evidence_ids:
            assert eid


def test_candidate_donor_context_labeled_assumptions():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    assert r.candidates
    cal = r.candidates[0].candidate_analogy_ledger
    assert "donor_context_is_assumption_not_x_y_fact" in cal.inherited_assumptions
    assert cal.inherited_donor_context[0].is_assumption is True


def test_evidence_kind_propagated():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    assert r.evidence_kind is EvidenceKind.synthetic_fixture
    assert r.candidates[0].evidence_kind is EvidenceKind.synthetic_fixture
    assert r.trace.evidence_kind is EvidenceKind.synthetic_fixture


def test_formal_mapping_not_mechanism():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    # The donor mapping report must not claim mechanistic origin.
    donor_evidence = None  # reconstructed below from the fixture train view
    from reaction_agent.p3.fixtures import build_train_view, load_fixture_reactions
    tv = build_train_view(load_fixture_reactions())
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    report = dev.context.mapping_report
    assert report.mechanistic_atom_origin is None
    assert report.source_assignment_method.value == "formal_mapped"


# -- R2-A evidence kind propagation ------------------------------------------


def _collect_evidence_kinds(obj, acc):
    """Collect every evidence_kind string on a JSON-serialized P3 result."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "evidence_kind" and isinstance(v, str):
                acc.append(v)
            else:
                _collect_evidence_kinds(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_evidence_kinds(v, acc)


def test_fixture_run_contains_no_real_evidence_labels():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    # Scope: run DATA objects only (query / candidates / trace / result).
    # capability_status components are ENVIRONMENT probes (RDKit is genuinely
    # real; snapshot genuinely blocked) and are intentionally excluded here.
    data = {
        "normalized_query": r.normalized_query.model_dump(mode="json"),
        "candidates": [c.model_dump(mode="json") for c in r.candidates],
        "trace": r.trace.model_dump(mode="json"),
        "result": {"evidence_kind": r.evidence_kind.value},
    }
    acc = []
    _collect_evidence_kinds(data, acc)
    assert acc, "expected evidence_kind fields on the result data"
    assert "real" not in acc, f"fixture run data leaks real evidence labels: {acc}"
    assert all(k == "synthetic_fixture" for k in acc), f"unexpected kinds: {acc}"
    # NormalizedQuery inside the fixture run must be synthetic_fixture.
    assert r.normalized_query.evidence_kind is EvidenceKind.synthetic_fixture
    assert r.manifest is not None


def test_real_mode_cannot_consume_synthetic_train_view():
    from reaction_agent.p3.fixtures import build_train_view, load_fixture_reactions
    synthetic = build_train_view(load_fixture_reactions())
    r = run_kernel(
        input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="real",
        train_view=synthetic,
    )
    assert r.status is KernelStatus.blocked
    assert all(f.category == "system" for f in r.failures)


def test_evidence_kind_cross_object_consistency():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3", mode="fixture")
    assert r.evidence_kind is EvidenceKind.synthetic_fixture
    assert r.normalized_query.evidence_kind is EvidenceKind.synthetic_fixture
    assert r.trace.evidence_kind is EvidenceKind.synthetic_fixture
    for candidate in r.candidates:
        assert candidate.evidence_kind is EvidenceKind.synthetic_fixture
