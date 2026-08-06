"""P4 PASS-capable synthetic contract fixture (explicitly synthetic_fixture).

This fixture exercises P4 *machinery* only — evidence identity/dedup,
support aggregation, counterevidence, strict ranking, applicability, typed
abstention, PredictionResult invariants, and immutable run/replay. It never
claims real evidence, real chemistry, or production performance. The fixture
is the PASS-capable baseline used by the mutation runner: each mutation must
flip a specific PASS → FAIL (never a BLOCKED baseline pretending to be a
caught mutation).

Scenario: query X is an alcohol; donor reaction R1 is an alcohol oxidation
(ethanol -> acetaldehyde, transform T1). Four+ evidence rows exercise the
dedup dimensions (mirror / same-publication / mapper duplicate / different
source, same transform / fully different source).
"""
from __future__ import annotations

from reaction_agent.schemas.common import (
    Lane,
    MappingStatus,
    MappingQualityClass,
    LedgerBalanceStatus,
    ParticipantRole,
    SourceAssignmentMethod,
)
from reaction_agent.schemas.evidence import (
    ReactionEvidence,
    ReactionParticipant,
    RoleHypothesis,
)
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.ledger import (
    RoleAssignment,
    SourceReactionLedger,
    AddedAtomSource,
)
from reaction_agent.schemas.p1_entities import ResolvedTransformedLineage

POLICY_VERSION = "p4-policy-1"


def _participant(pid: str, side: str, smiles: str, amn: list[int] | None = None,
                 role: str = "transformed_substrate") -> ReactionParticipant:
    return ReactionParticipant(
        participant_id=pid,
        molecule_id=f"mol_{pid}",
        canonical_smiles=smiles,
        side=side,
        stoichiometry=1,
        formal_charge=0,
        atom_map_numbers=amn or [],
        mapped_fraction=1.0 if amn else 0.0,
        changed_atom_fraction=0.0,
        role_hypotheses=[RoleHypothesis(role=ParticipantRole(role), score=0.9)],
        donor_eligibility=True,
        provenance=["fixture:participant"],
    )


def _ledger(rid: str, balance: LedgerBalanceStatus, cb: int = 0,
            added: list[AddedAtomSource] | None = None) -> SourceReactionLedger:
    return SourceReactionLedger(
        ledger_id=f"srl_{rid}",
        reaction_evidence_id=rid,
        balance_status=balance,
        charge_balance=cb,
        added_atom_sources=added or [],
        cofactor_changes=[],
        role_assignments=[
            RoleAssignment(participant_id="r1", role=ParticipantRole.transformed_substrate, score=0.9),
            RoleAssignment(participant_id="p1", role=ParticipantRole.transformed_product, score=0.9),
        ],
        unknowns=[],
        hydrogen_policy="explicit",
        proton_policy="unknown",
        electron_policy="unknown",
        source_completeness="complete",
        mapping_completeness="complete",
    )


def _evidence(*, rid: str, source: str, version: str, record: str,
              pub: str, raw: str = "CCO>>CC=O", norm: str = "CCO>>CC=O",
              lineage: str = "lin_d1", transforms: tuple[str, ...] = ("t1",),
              mapping_status: MappingStatus = MappingStatus.fully_mapped,
              balance: LedgerBalanceStatus = LedgerBalanceStatus.fully_balanced_explicit_reaction,
              quality: MappingQualityClass = MappingQualityClass.high_quality) -> ReactionEvidence:
    r1 = _participant("r1", "reactant", "CCO", amn=[1, 2])
    p1 = _participant("p1", "product", "CC=O", amn=[1, 2], role="transformed_product")
    return ReactionEvidence(
        reaction_id=rid,
        source_record_id=record,
        source_name=source,
        source_version=version,
        source_uri_or_citation=pub,
        raw_reaction=raw,
        normalized_reaction=norm,
        direction="forward",
        participants=[r1, p1],
        resolved_transformed_lineages=[lineage],
        transformation_hypotheses=list(transforms),
        source_reaction_ledger=_ledger(rid, balance),
        quality_report={
            "mapping_status": mapping_status.value,
            "quality": quality.value,
            "source_assignment_method": SourceAssignmentMethod.formal_mapped.value,
        },
        provenance=["fixture:evidence"],
        snapshot_id="snap_c589494081df",
    )


def build_evidence_records() -> list[ReactionEvidence]:
    """Five evidence rows covering mirror / publication / mapper dedup.

    - ev_d1        : source rhea v1 record REC-101, pub smith2020
    - ev_d1_mirror : source rhea_mirror v1 record REC-101M, SAME pub + reaction
                     -> dedup via same_publication / same_normalized_reaction
    - ev_d4        : source rhea v1 record REC-404, SAME raw + reaction + lineage
                     -> dedup via mapper_duplicate / same_donor_transform
    - ev_d2        : source uniprot-catalysed v2 REC-202, pub jones2021, SAME
                     transform -> INDEPENDENT (different source lineage)
    - ev_d3        : source rhea v1 REC-303, pub lee2019, DIFFERENT transform t2
                     -> independent observation (competing transform candidate)
    """
    return [
        _evidence(rid="ev_d1", source="rhea", version="v1", record="REC-101",
                  pub="pub:smith2020"),
        _evidence(rid="ev_d1_mirror", source="rhea_mirror", version="v1",
                  record="REC-101M", pub="pub:smith2020"),
        _evidence(rid="ev_d4", source="rhea", version="v1", record="REC-404",
                  pub="pub:smith2020"),
        _evidence(rid="ev_d2", source="uniprot-catalysed", version="2",
                  record="REC-202", pub="pub:jones2021"),
        _evidence(rid="ev_d3", source="rhea", version="v1", record="REC-303",
                  pub="pub:lee2019", raw="CC(C)O>>CC(C)=O",
                  norm="CC(C)O>>CC(C)=O", lineage="lin_d2", transforms=("t2",),
                  mapping_status=MappingStatus.partially_mapped,
                  quality=MappingQualityClass.acceptable),
    ]


def build_strict_candidate() -> Candidate:
    """Validated strict candidate for the alcohol oxidation product."""
    return Candidate(
        candidate_id="cand_ox_001",
        canonical_product="CC=O",
        lane=Lane.strict,
        origin="agent_selected_from_evidence_space",
        generation_paths=[{"transform_id": "t1", "site_id": "site_c1",
                           "graph_edit_id": "delta_1"}],
        support_lineage_ids=["lin_d1"],
        transformation_ids=["t1"],
        site_ids=["site_c1"],
        validation={
            "valid_molecule": True,
            "transform_fidelity": "exact",
            "precondition_recheck": "passed",
            "heavy_atom_source_accounting": "complete",
            "candidate_analogy_ledger_valid": True,
            "no_relaxation": True,
            "no_critical_ambiguity": True,
        },
        source_ledger_ids=["srl_ev_d1"],
        candidate_analogy_ledger_id="cal_cand_ox_001",
        provenance=["fixture:candidate"],
    )


def build_structural_context() -> dict:
    """Per-feature ordinal structural observations for the fixture candidate.

    Ordinals {0,1,2,3}; these simulate what P3/P1 chemistry would provide.
    Absent here, a feature is ``not_observable`` (never fabricated).
    """
    return {
        "donor_similarity": 3,          # high donor structural similarity
        "transform_support": 3,         # transform T1 recurs in evidence
        "site_compatibility": 3,        # query site matches donor site
        "mapping_lineage_quality": 3,   # fully_mapped + high quality
        "source_quality": 2,            # reputable sources
        "ledger_completeness": 3,       # fully balanced ledgers
        "evidence_independence": 2,     # 2 independent groups
        "retrieval_stability": 3,       # stable across retrieval rounds
    }


def build_feature_evidence_binding() -> dict:
    """Per-feature evidence bindings (P4-R1-G): the evidence ids that genuinely
    produced each structural feature — never the full evidence set.

    Keys accept both the ranking key and the support key spelling.
    """
    return {
        "donor_similarity": ["ev_d1", "ev_d2"],
        "donor_structural_similarity": ["ev_d1", "ev_d2"],
        "transform_support": ["ev_d1", "ev_d2"],
        "transform_recurrence": ["ev_d1", "ev_d2"],
        "site_compatibility": ["ev_d1"],
        "mapping_lineage_quality": ["ev_d1", "ev_d4"],
        "source_quality": ["ev_d1", "ev_d2", "ev_d3"],
        "ledger_completeness": ["ev_d1", "ev_d4"],
        "retrieval_stability": ["ev_d1", "ev_d2"],
    }


def build_query() -> dict:
    """Canonical query request (P4 normalizes + hashes it).

    Carries the frozen run namespace (run/query/case/fold/snapshot ID/hash)
    that must exact-match the authority handle (P4-R1-D).
    """
    return {
        "query_smiles": "CCO",
        "run_id": "run_abc",
        "query_id": "q_1",
        "case_id": "case_1",
        "fold_id": "fold_1",
        "snapshot_id": "snap_c589494081df",
        "snapshot_hash": "deadbeef" * 4,
        "fold_view_id": "train_only_v1",
        "requested_lanes": ["strict"],
        "top_k": 3,
        "policy_version": POLICY_VERSION,
    }
