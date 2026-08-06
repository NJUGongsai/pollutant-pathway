"""R3-E CandidateEvidencePath integrity tests.

Round 2 defect: ``StrictCandidate`` only checked that each path source ledger
appears in the parent list.  Forged path transformations and forged nested
candidate-ledger source IDs passed model validation:

    forged_path_transform_accepted=True
    forged_path_ledger_accepted=True

Round 3 contract:
- generation report transformation/site == path transformation/site;
- nested candidate ledger source == path source ledger;
- nested candidate ledger candidate ID == parent candidate ID;
- path validation satisfies strict-lane rules;
- path transformation/site/lineage/source IDs belong to the parent;
- parent ID sets EXACTLY equal the union of path IDs;
- parent generation paths exactly correspond to path generation reports;
- strict candidates have at least one evidence path;
- a content-addressed path ID/hash immutably binds the path to the parent
  run namespace (donor, reaction, lineage, transformation, site, generation,
  source ledger and candidate ledger in the preimage).
"""
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
from reaction_agent.p3.generate import generate_product
from reaction_agent.p3.transform import extract_transform
from reaction_agent.p3.validate import validate_candidate
from reaction_agent.p3.schemas import (
    CandidateEvidencePath,
    CandidateValidation,
    SiteEligibility,
    StrictCandidate,
)
from reaction_agent.schemas.ledger import CandidateAnalogyLedger
from reaction_agent.hashing import stable_id


def _parts():
    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    tr = extract_transform(dev, lineage_id=ref.lineage_id)
    q = normalize_query("CCCCCCCCO")
    site = [s for s in enumerate_sites(tr, q)
            if s.eligibility is SiteEligibility.eligible][0]
    report = generate_product(tr, site, q)
    candidate_id = stable_id("cand", {
        "identity": report.canonical_product, "version": "p3-1",
    })
    validation, cal = validate_candidate(
        dev, tr, site, report, q, candidate_id=candidate_id,
        source_ledger_id=dev.context.source_ledger.ledger_id,
    )
    return {
        "dev": dev, "ref": ref, "tr": tr, "q": q, "site": site,
        "report": report, "validation": validation, "cal": cal,
        "candidate_id": candidate_id,
    }


def _namespace():
    return {
        "run_id": "run_r3e", "case_id": "case_r3e", "query_id": "q_r3e",
        "fold_id": "fold_fx_p3", "snapshot_id": "fx_snapshot_p3",
        "snapshot_hash": "h_snapshot",
    }


def _binding(parts, **overrides):
    """Compute the content-addressed path binding for (possibly overridden)
    path fields.  Raises AttributeError before R3-E exists."""
    from reaction_agent.p3.schemas import compute_candidate_path_binding
    ns = _namespace()
    fields = {
        "donor_id": parts["dev"].donor_id,
        "reaction_id": parts["ref"].reaction_id,
        "lineage_id": parts["ref"].lineage_id,
        "transformation_id": parts["tr"].transformation_id,
        "site_id": parts["site"].site_id,
        "generation_report": parts["report"],
        "source_ledger_id": parts["dev"].context.source_ledger.ledger_id,
        "candidate_analogy_ledger": parts["cal"],
    }
    fields.update(overrides)
    return compute_candidate_path_binding(**fields, **ns)


def _mk_path(parts, **overrides):
    """Build a valid path, then apply post-hoc field overrides via
    model_copy (as a forger would — bypassing construction)."""
    path_id, path_hash = _binding(parts)
    fields = {
        "donor_id": parts["dev"].donor_id,
        "reaction_id": parts["ref"].reaction_id,
        "lineage_id": parts["ref"].lineage_id,
        "transformation_id": parts["tr"].transformation_id,
        "site_id": parts["site"].site_id,
        "generation_report": parts["report"],
        "source_ledger_id": parts["dev"].context.source_ledger.ledger_id,
        "candidate_analogy_ledger": parts["cal"],
        "validation": parts["validation"],
        "path_id": path_id,
        "path_hash": path_hash,
    }
    fields.update(overrides)
    return CandidateEvidencePath(**fields)


def _mk_candidate(parts, paths, **overrides):
    ns = _namespace()
    fields = {
        "candidate_id": parts["candidate_id"],
        "canonical_product_identity": parts["report"].canonical_product,
        "lane": "strict",
        "origin": "deterministic_kernel",
        "generation_paths": [p.generation_report for p in paths],
        "support_lineage_ids": [p.lineage_id for p in paths],
        "transformation_ids": [p.transformation_id for p in paths],
        "site_ids": [p.site_id for p in paths],
        "validation": parts["validation"],
        "source_ledger_ids": [p.source_ledger_id for p in paths],
        "candidate_analogy_ledger": parts["cal"],
        "candidate_evidence_paths": paths,
        "provenance": ["kernel:p3-1"],
        **ns,
    }
    fields.update(overrides)
    return StrictCandidate(**fields)


# -- the audit reproduction --------------------------------------------------


def test_forged_path_transform_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={
        "generation_report": parts["report"].model_copy(
            update={"transformation_id": "tr_FORGED"}),
    })
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_forged_path_site_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={
        "generation_report": parts["report"].model_copy(
            update={"site_id": "site_FORGED"}),
    })
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_forged_nested_ledger_source_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={
        "candidate_analogy_ledger": parts["cal"].model_copy(
            update={"source_ledger_id": "srl_FORGED"}),
    })
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_forged_nested_ledger_candidate_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={
        "candidate_analogy_ledger": parts["cal"].model_copy(
            update={"candidate_id": "cand_FORGED"}),
    })
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_forged_lineage_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={"lineage_id": "lin_FORGED"})
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_forged_source_ledger_id_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={"source_ledger_id": "srl_FORGED"})
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_tampered_path_hash_rejected():
    parts = _parts()
    path = _mk_path(parts)
    forged = path.model_copy(update={"path_hash": "h" * 64})
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_parent_namespace_rebinding_rejected():
    # A path bound to one run namespace cannot be smuggled into a candidate
    # of ANOTHER namespace.
    parts = _parts()
    path = _mk_path(parts)
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [path], run_id="run_OTHER")


def test_failing_path_validation_rejected():
    parts = _parts()
    # a path whose validation carries a failure code must not enter strict
    path = _mk_path(parts)
    forged = path.model_copy(update={
        "validation": CandidateValidation(
            valid_molecule=True, transform_fidelity=True,
            precondition_recheck=True, formal_source_accounting=True,
            candidate_ledger_valid=True, failure_code="SMUGGLED",
        ),
    })
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [forged])


def test_parent_id_sets_must_equal_path_union():
    parts = _parts()
    path = _mk_path(parts)
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [path],
                      transformation_ids=[path.transformation_id, "tr_EXTRA"])
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [path], source_ledger_ids=[])


def test_strict_candidate_requires_at_least_one_path():
    parts = _parts()
    with pytest.raises(ValidationError):
        _mk_candidate(parts, [])


def test_valid_path_chain_accepted():
    parts = _parts()
    path = _mk_path(parts)
    candidate = _mk_candidate(parts, [path])
    assert candidate.candidate_evidence_paths[0].path_hash == path.path_hash
    assert candidate.candidate_evidence_paths[0].path_id == path.path_id


def test_path_preimage_covers_required_linkage():
    from reaction_agent.p3.schemas import candidate_path_preimage
    parts = _parts()
    ns = _namespace()
    preimage = candidate_path_preimage(
        donor_id=parts["dev"].donor_id,
        reaction_id=parts["ref"].reaction_id,
        lineage_id=parts["ref"].lineage_id,
        transformation_id=parts["tr"].transformation_id,
        site_id=parts["site"].site_id,
        generation_report=parts["report"],
        source_ledger_id=parts["dev"].context.source_ledger.ledger_id,
        candidate_analogy_ledger=parts["cal"],
        **ns,
    )
    for key in (
        "donor_id", "reaction_id", "lineage_id", "transformation_id",
        "site_id", "generation", "source_ledger_id", "candidate_ledger",
        "run_id", "case_id", "query_id", "fold_id", "snapshot_id",
        "snapshot_hash",
    ):
        assert key in preimage, f"path preimage missing {key!r}"


def test_two_paths_merge_keeps_both_bindings():
    # Merge via the production store keeps every path with its own binding.
    from reaction_agent.p3.store import CandidateStore
    from reaction_agent.p3.schemas import EvidenceKind
    parts = _parts()
    store = CandidateStore(
        run_id="run_r3e", case_id="case_r3e", query_id="q_r3e",
        fold_id="fold_fx_p3", snapshot_id="fx_snapshot_p3",
        snapshot_hash="h_snapshot", query=parts["q"],
        evidence_kind=EvidenceKind.synthetic_fixture,
    )
    for _ in range(2):
        store.add(
            donor_id=parts["dev"].donor_id,
            reaction_id=parts["ref"].reaction_id,
            lineage_id=parts["ref"].lineage_id,
            report=parts["report"], transform=parts["tr"], site=parts["site"],
            validation=parts["validation"],
            candidate_analogy_ledger=parts["cal"],
            source_ledger_id=parts["dev"].context.source_ledger.ledger_id,
        )
    candidates = store.finalize()
    assert len(candidates) == 1
    assert len(candidates[0].candidate_evidence_paths) == 2
    for path in candidates[0].candidate_evidence_paths:
        assert path.path_id and path.path_hash
