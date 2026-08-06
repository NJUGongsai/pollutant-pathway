"""R2-F strict candidate validation + store tests."""
import pytest
from pydantic import ValidationError

from reaction_agent.p3.fixtures import (
    build_train_view,
    find_donor_ref,
    load_fixture_reactions,
)
from reaction_agent.p3.load import load_reaction_evidence
from reaction_agent.p3.normalize import normalize_query
from reaction_agent.p3.sites import enumerate_sites
from reaction_agent.p3.transform import extract_transform
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.validate import validate_candidate
from reaction_agent.p3.schemas import (
    CandidateEvidencePath,
    CandidateValidation,
    EvidenceKind,
    GenerationReport,
    SiteEligibility,
    StrictCandidate,
)
from reaction_agent.hashing import stable_id


def _oct_ctx():
    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    return dev, tr


def _validated(report=None):
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    rep = report or generate_product(tr, site, q)
    candidate_id = stable_id("cand", {"identity": rep.canonical_product})
    return validate_candidate(
        dev, tr, site, rep, q, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )


def test_wrong_product_same_heavy_atom_count_rejected():
    # octanal (CCCCCCCC=O) vs octan-2-one (CCCCCCC(C)=O) both have 9 heavy
    # atoms.  The validator must reject the WRONG product via edit replay.
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    real = generate_product(tr, site, q)
    forged = real.model_copy(update={
        "canonical_product": "CCCCCCC(C)=O",  # wrong isomer, same heavy-atom count
        "raw_product": "CCCCCCC(C)=O",
    })
    validation, _ = validate_candidate(
        dev, tr, site, forged, q, candidate_id=stable_id("cand", {"identity": forged.canonical_product}),
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    assert validation.transform_fidelity is False
    assert validation.failure_code == "EDIT_REPLAY_MISMATCH"


def test_wrong_generation_transform_id_rejected():
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    rep = generate_product(tr, site, q)
    forged = rep.model_copy(update={"transformation_id": "tr_WRONG"})
    validation, _ = validate_candidate(
        dev, tr, site, forged, q,
        candidate_id=stable_id("cand", {"identity": rep.canonical_product}),
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    assert validation.failure_code == "WRONG_GENERATION_TRANSFORM_ID"


def test_wrong_generation_site_id_rejected():
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    rep = generate_product(tr, site, q)
    forged = rep.model_copy(update={"site_id": "site_WRONG"})
    validation, _ = validate_candidate(
        dev, tr, site, forged, q,
        candidate_id=stable_id("cand", {"identity": rep.canonical_product}),
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    assert validation.failure_code == "WRONG_GENERATION_SITE_ID"


def test_missing_required_edit_rejected():
    # A report claiming the UNEDITED query (missing the required bond change)
    # must be rejected by replay.
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    forged = GenerationReport(
        generation_id="gen_forged", transformation_id=tr.transformation_id,
        site_id=site.site_id, canonical_product="CCCCCCCCO",  # unchanged (edit missing)
        component_version="p3-1",
    )
    validation, _ = validate_candidate(
        dev, tr, site, forged, q,
        candidate_id=stable_id("cand", {"identity": forged.canonical_product}),
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    assert validation.transform_fidelity is False


def test_forged_source_ledger_rejected():
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    rep = generate_product(tr, site, q)
    validation, _ = validate_candidate(
        dev, tr, site, rep, q,
        candidate_id=stable_id("cand", {"identity": rep.canonical_product}),
        source_ledger_id="srl_FORGED",  # NOT the donor authority ledger
    )
    assert validation.candidate_ledger_valid is False
    assert validation.failure_code == "FORGED_SOURCE_LEDGER"


def test_unknown_candidate_id_rejected():
    from reaction_agent.schemas.ledger import LedgerReferenceRegistry
    from reaction_agent.schemas.ledger import validate_candidate_ledger_references
    from reaction_agent.schemas.errors import UnknownReferenceError
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    bad = CandidateAnalogyLedger(
        ledger_id="cal", source_ledger_id="srl_ok", candidate_id="cand_UNKNOWN",
    )
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset(["srl_ok"]), candidate_ids=frozenset(["cand_ok"]),
    )
    with pytest.raises(UnknownReferenceError):
        validate_candidate_ledger_references(bad, registry)


def test_formal_balance_is_derived_not_hardcoded():
    # octanal has a derived charge_delta (oxidation removes 2 H -> charge 0,
    # no heavy atoms added/removed).  The ledger balance must be derived, not
    # a fixed hardcoded zero with empty balances that ignores the transform.
    dev, tr = _oct_ctx()
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q) if s.eligibility is SiteEligibility.eligible][0]
    rep = generate_product(tr, site, q)
    _, cal = validate_candidate(
        dev, tr, site, rep, q,
        candidate_id=stable_id("cand", {"identity": rep.canonical_product}),
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    balance = cal.formal_balance_under_assumptions
    assert balance is not None
    assert "DERIVED" in " ".join(balance.assumption_notes).upper() or \
        any("derived" in n.lower() for n in balance.assumption_notes)


def test_critical_contradiction_rejected_from_strict_lane():
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    with pytest.raises(ValidationError):
        StrictCandidate(
            candidate_id="cand_cc", canonical_product_identity="C=O",
            lane="strict", origin="deterministic_kernel", generation_paths=[],
            support_lineage_ids=[], transformation_ids=[], site_ids=[],
            validation=CandidateValidation(
                valid_molecule=True, transform_fidelity=True,
                precondition_recheck=True, formal_source_accounting=True,
                candidate_ledger_valid=True, critical_contradiction=True,
            ),
            source_ledger_ids=[],
            candidate_analogy_ledger=CandidateAnalogyLedger(
                ledger_id="cal", source_ledger_id="srl", candidate_id="cand_cc",
            ),
            provenance=[],
        )


def test_failure_code_rejected_even_if_flags_true():
    from reaction_agent.schemas.ledger import CandidateAnalogyLedger
    with pytest.raises(ValidationError):
        StrictCandidate(
            candidate_id="cand_fc", canonical_product_identity="C=O",
            lane="strict", origin="deterministic_kernel", generation_paths=[],
            support_lineage_ids=[], transformation_ids=[], site_ids=[],
            validation=CandidateValidation(
                valid_molecule=True, transform_fidelity=True,
                precondition_recheck=True, formal_source_accounting=True,
                candidate_ledger_valid=True, failure_code="SOMETHING",
            ),
            source_ledger_ids=[],
            candidate_analogy_ledger=CandidateAnalogyLedger(
                ledger_id="cal", source_ledger_id="srl", candidate_id="cand_fc",
            ),
            provenance=[],
        )
