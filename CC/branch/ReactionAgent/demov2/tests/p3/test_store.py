"""P3-T8 canonical candidate store tests (final_plan §6.9)."""
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.validate import validate_candidate
from reaction_agent.p3.store import CandidateStore
from reaction_agent.p3.schemas import EvidenceKind, SiteEligibility
from reaction_agent.hashing import stable_id


def _store_with_candidate(train_view, oct_transform, store):
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(oct_transform, query)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(oct_transform, site, query)
    # R3-E: the candidate_id must use the SAME versioned preimage as the
    # production kernel/store so the ledger binding validates.
    candidate_id = stable_id(
        "cand", {"identity": report.canonical_product, "version": "p3-1"}
    )
    validation, cal = validate_candidate(
        dev, oct_transform, site, report, query,
        candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    store.add(
        donor_id=dev.donor_id,
        reaction_id=dev.context.reaction_id,
        lineage_id=ref.lineage_id,
        report=report, transform=oct_transform, site=site,
        validation=validation, candidate_analogy_ledger=cal,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    return dev, site, report


def test_identical_structure_merges_evidence(train_view, oct_transform):
    store = CandidateStore(
        run_id="r", case_id="c", query_id="q", fold_id="f",
        snapshot_id="s", snapshot_hash="h",
        query=normalize_query("CCCCCCCCO"), evidence_kind=EvidenceKind.synthetic_fixture,
    )
    _store_with_candidate(train_view, oct_transform, store)
    _store_with_candidate(train_view, oct_transform, store)  # same product again
    candidates = store.finalize()
    assert len(candidates) == 1
    # Evidence is preserved across both generation paths.
    assert len(candidates[0].generation_paths) == 2
    assert len(candidates[0].transformation_ids) >= 1


def test_candidate_id_system_generated_recomputable(train_view, oct_transform):
    store = CandidateStore(
        run_id="r", case_id="c", query_id="q", fold_id="f",
        snapshot_id="s", snapshot_hash="h",
        query=normalize_query("CCCCCCCCO"), evidence_kind=EvidenceKind.synthetic_fixture,
    )
    dev, site, report = _store_with_candidate(train_view, oct_transform, store)
    candidates = store.finalize()
    expected = stable_id("cand", {"identity": report.canonical_product, "version": "p3-1"})
    assert candidates[0].candidate_id == expected


def test_lane_strict_origin_kernel(train_view, oct_transform):
    store = CandidateStore(
        run_id="r", case_id="c", query_id="q", fold_id="f",
        snapshot_id="s", snapshot_hash="h",
        query=normalize_query("CCCCCCCCO"), evidence_kind=EvidenceKind.synthetic_fixture,
    )
    _store_with_candidate(train_view, oct_transform, store)
    candidates = store.finalize()
    assert candidates[0].lane == "strict"
    assert candidates[0].origin == "deterministic_kernel"
    assert candidates[0].evidence_kind is EvidenceKind.synthetic_fixture


def test_evidence_kind_declared(train_view, oct_transform):
    store = CandidateStore(
        run_id="r", case_id="c", query_id="q", fold_id="f",
        snapshot_id="s", snapshot_hash="h",
        query=normalize_query("CCCCCCCCO"), evidence_kind=EvidenceKind.synthetic_fixture,
    )
    _store_with_candidate(train_view, oct_transform, store)
    candidates = store.finalize()
    assert candidates[0].evidence_kind.value == "synthetic_fixture"


# -- R2-F candidate merge evidence preservation -------------------------------


def test_candidate_merge_preserves_per_path_ledgers(train_view, oct_transform):
    from reaction_agent.p3.store import CandidateStore, _product_identity
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(oct_transform, query)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(oct_transform, site, query)
    candidate_id = stable_id(
        "cand", {"identity": report.canonical_product, "version": "p3-1"}
    )
    validation, cal = validate_candidate(
        dev, oct_transform, site, report, query, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    # R3-E: the second path carries its OWN ledger whose source matches the
    # path source ledger (a mismatched ledger/source pair is now rejected).
    cal_second = cal.model_copy(update={
        "ledger_id": cal.ledger_id + "_second",
        "source_ledger_id": "srl_SECOND",
    })
    store = CandidateStore(run_id="r", case_id="c", query_id="q", fold_id="f",
                           snapshot_id="s", snapshot_hash="h",
                           query=query, evidence_kind=EvidenceKind.synthetic_fixture)
    # Add the SAME product via TWO paths with DIFFERENT source ledgers.
    store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
              report=report, transform=oct_transform, site=site,
              validation=validation, candidate_analogy_ledger=cal,
              source_ledger_id=dev.context.source_ledger.ledger_id)
    store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
              report=report, transform=oct_transform, site=site,
              validation=validation, candidate_analogy_ledger=cal_second,
              source_ledger_id="srl_SECOND")
    candidates = store.finalize()
    assert len(candidates) == 1
    c = candidates[0]
    assert len(c.candidate_evidence_paths) == 2
    # Both source ledgers are preserved per-path (R2-F: never only the first).
    assert {p.source_ledger_id for p in c.candidate_evidence_paths} == {
        dev.context.source_ledger.ledger_id, "srl_SECOND",
    }
    assert set(c.source_ledger_ids) == {dev.context.source_ledger.ledger_id, "srl_SECOND"}


def test_candidate_merge_preserves_per_path_validation(train_view, oct_transform):
    from reaction_agent.p3.store import CandidateStore
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(oct_transform, query)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(oct_transform, site, query)
    candidate_id = stable_id(
        "cand", {"identity": report.canonical_product, "version": "p3-1"}
    )
    v1, cal1 = validate_candidate(
        dev, oct_transform, site, report, query, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    v2 = v1.model_copy(update={"reason_codes": ["second_path_note"]})
    store = CandidateStore(run_id="r", case_id="c", query_id="q", fold_id="f",
                           snapshot_id="s", snapshot_hash="h",
                           query=query, evidence_kind=EvidenceKind.synthetic_fixture)
    store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
              report=report, transform=oct_transform, site=site,
              validation=v1, candidate_analogy_ledger=cal1,
              source_ledger_id=dev.context.source_ledger.ledger_id)
    store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
              report=report, transform=oct_transform, site=site,
              validation=v2, candidate_analogy_ledger=cal1,
              source_ledger_id=dev.context.source_ledger.ledger_id)
    c = store.finalize()[0]
    reasons = {tuple(p.validation.reason_codes) for p in c.candidate_evidence_paths}
    assert len(reasons) == 2, "per-path validation must be preserved"


def test_candidate_merge_order_invariant(train_view, oct_transform):
    from reaction_agent.p3.store import CandidateStore
    from reaction_agent.p3.fixtures import find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    donor, ref = find_donor_ref(train_view, "fx_oct")
    dev = load_reaction_evidence(train_view, donor.donor_id, ref)
    query = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(oct_transform, query)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(oct_transform, site, query)
    candidate_id = stable_id(
        "cand", {"identity": report.canonical_product, "version": "p3-1"}
    )
    validation, cal = validate_candidate(
        dev, oct_transform, site, report, query, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    cal_second = cal.model_copy(update={
        "ledger_id": cal.ledger_id + "_second",
        "source_ledger_id": "srl_SECOND",
    })

    def _run():
        store = CandidateStore(run_id="r", case_id="c", query_id="q", fold_id="f",
                               snapshot_id="s", snapshot_hash="h",
                               query=query, evidence_kind=EvidenceKind.synthetic_fixture)
        store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
                  report=report, transform=oct_transform, site=site,
                  validation=validation, candidate_analogy_ledger=cal,
                  source_ledger_id=dev.context.source_ledger.ledger_id)
        store.add(donor_id=dev.donor_id, reaction_id="fx_oct", lineage_id=ref.lineage_id,
                  report=report, transform=oct_transform, site=site,
                  validation=validation, candidate_analogy_ledger=cal_second,
                  source_ledger_id="srl_SECOND")
        return store.finalize()

    c1 = _run()[0]
    c2 = _run()[0]
    assert c1.candidate_id == c2.candidate_id
    assert [p.source_ledger_id for p in c1.candidate_evidence_paths] == \
        [p.source_ledger_id for p in c2.candidate_evidence_paths]


def test_isotope_identity_not_incorrectly_deduped():
    from reaction_agent.p3.store import _product_identity
    from reaction_agent.p3.schemas import NormalizationPolicy
    policy = NormalizationPolicy(version="p3-1", isotope_policy="preserve_isotopes",
                                 stereo_policy="ignore_stereo_for_identity")
    id_c12 = _product_identity("C", policy)
    id_c13 = _product_identity("[13CH4]", policy)
    assert id_c12 != id_c13, "isotope-labelled product must not dedup with C12"
