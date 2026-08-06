"""R4-C: StrictCandidate MUST bind the FULL nested generation + ledger content.

ChatGPT P3 Round 3 audit independently showed that the following forgeries
were accepted by ``StrictCandidate.model_validate``:
- forged_unhashed_nested_generation_accepted=True
- forged_unhashed_nested_ledger_accepted=True
- orphan_support_lineage_accepted=True
- forged_parent_generation_content_accepted=True

The candidate path preimage only projected a few generation/ledger fields,
and the validator only compared generation IDs (never content) and used a
subset (not exact-equality) check for support lineages.

Every mutation below must be REJECTED by the production validator.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.p3.mutations_round3 import _valid_candidate


@pytest.fixture(scope="module")
def candidate():
    return _valid_candidate()


def _revalidate(cand):
    type(cand).model_validate(cand.model_dump(mode="python"))


# -- generation nested content -----------------------------------------------


def test_generation_raw_product_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"raw_product": "FORGED"})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_edit_application_log_tamper_rejected(candidate):
    from reaction_agent.p3.schemas import EditApplicationLog
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={
                "edit_application_log": [EditApplicationLog(step="FORGED")],
            })
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_changed_atoms_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"changed_atoms": [999]})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_changed_bonds_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"changed_bonds": [999]})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_sanitize_report_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"sanitize_report": "FORGED"})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_dedup_key_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"dedup_key": "FORGED"})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_generation_canonical_product_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={"canonical_product": "FORGED"})
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


# -- candidate analogy ledger nested content ---------------------------------


def test_ledger_inherited_assumptions_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"inherited_assumptions": ["FORGED"]}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_ledger_evidence_ids_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"evidence_ids": ["FORGED"]}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_ledger_unknowns_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"unknowns": ["FORGED"]}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_ledger_balance_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"candidate_balance_status": "FORGED"}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_ledger_formal_transfers_tamper_rejected(candidate):
    # octanol has no formal transfers by default; tamper a field that IS
    # populated and content-bearing (ledger_id + evidence ids).
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"ledger_id": "FORGED_LEDGER"}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_ledger_unknown_cofactors_tamper_rejected(candidate):
    forged = candidate.model_copy(update={
        "candidate_analogy_ledger": candidate.candidate_analogy_ledger.model_copy(
            update={"unknown_actual_cofactors": ["FORGED"]}
        ),
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


# -- top-level / parent binding ----------------------------------------------


def test_parent_generation_content_with_same_id_rejected(candidate):
    # Same generation_id, different content on the PARENT generation_paths.
    forged = candidate.model_copy(update={
        "generation_paths": [
            candidate.generation_paths[0].model_copy(update={
                "canonical_product": "FORGED",
                "dedup_key": "FORGED",
            })
        ],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_orphan_support_lineage_rejected(candidate):
    forged = candidate.model_copy(update={
        "support_lineage_ids": candidate.support_lineage_ids + ["lin_ORPHAN"],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_missing_support_lineage_rejected(candidate):
    forged = candidate.model_copy(update={
        "support_lineage_ids": [],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_duplicate_support_lineage_rejected(candidate):
    forged = candidate.model_copy(update={
        "support_lineage_ids": candidate.support_lineage_ids[:1]
        + candidate.support_lineage_ids,
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_path_parent_namespace_mismatch_rejected(candidate):
    # Path smuggled from a different run namespace must be rejected.
    forged = candidate.model_copy(update={"run_id": "run_OTHER"})
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_extraneous_generation_path_rejected(candidate):
    # A generation_paths entry that has no matching evidence path.
    extra = candidate.generation_paths[0].model_copy(update={"generation_id": "gen_EXTRA"})
    forged = candidate.model_copy(update={
        "generation_paths": candidate.generation_paths + [extra],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_empty_generation_paths_rejected(candidate):
    # A candidate without any generation report is incomplete.
    forged = candidate.model_copy(update={"generation_paths": []})
    with pytest.raises(ValidationError):
        _revalidate(forged)


def test_forged_path_generation_not_in_parent_rejected(candidate):
    # Adversarial: forge a path's generation report (new generation_id +
    # tampered content), recompute the content-addressed path binding, and
    # reuse the same donor/transformation/site/lineage/source_ledger IDs.
    # The reverse direction check must reject it (its generation content is
    # absent from the candidate's declared generation_paths).
    from reaction_agent.p3.schemas import compute_candidate_path_binding
    path = candidate.candidate_evidence_paths[0]
    forged_gen = path.generation_report.model_copy(update={
        "generation_id": "gen_FORGED",
        "canonical_product": "FORGED",
    })
    pid, phash = compute_candidate_path_binding(
        donor_id=path.donor_id, reaction_id=path.reaction_id,
        lineage_id=path.lineage_id, transformation_id=path.transformation_id,
        site_id=path.site_id, generation_report=forged_gen,
        source_ledger_id=path.source_ledger_id,
        candidate_analogy_ledger=path.candidate_analogy_ledger,
        run_id=candidate.run_id, case_id=candidate.case_id,
        query_id=candidate.query_id, fold_id=candidate.fold_id,
        snapshot_id=candidate.snapshot_id, snapshot_hash=candidate.snapshot_hash,
    )
    forged_path = path.model_copy(update={
        "generation_report": forged_gen, "path_id": pid, "path_hash": phash,
    })
    forged = candidate.model_copy(update={
        "candidate_evidence_paths": [forged_path],
    })
    with pytest.raises(ValidationError):
        _revalidate(forged)


# -- legal candidate still validates -----------------------------------------


def test_legal_candidate_still_validates(candidate):
    _revalidate(candidate)
    assert candidate.candidate_evidence_paths[0].path_hash