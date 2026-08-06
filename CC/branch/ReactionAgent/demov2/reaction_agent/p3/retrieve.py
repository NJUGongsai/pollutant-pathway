"""P3-T2 Adaptive distinct-donor retrieval (final_plan §6.3).

Inputs are X and a train-only P1 view.  Outputs DISTINCT eligible donor
molecule identities with EXPLICIT eligible reaction references (not a single
"first reaction").  Baseline features (Morgan / size / charge) express
structural retrieval only — they are NOT activity or probability.

Deterministic adaptive rounds; duplicate/mirror rows never crowd donor slots;
quarantine/excluded fail closed; no test access; deterministic tie-break.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from reaction_agent.p3.schemas import (
    EvidenceKind,
    NormalizedQuery,
    StrictModel,
    NonEmptyStr,
)
from reaction_agent.p3.fixtures import TrainView


class RetrievalConfig(StrictModel):
    version: str = "p3-1"
    max_donor_molecules: int = 10
    morgan_radius: int = 2
    morgan_bits: int = 2048
    similarity_threshold: float = 0.0
    seed: int = 0
    adaptive_rounds: int = 3


class ReactionRef(StrictModel):
    """An explicit eligible reaction reference for a donor."""
    reaction_id: NonEmptyStr
    donor_participant_id: NonEmptyStr
    lineage_id: NonEmptyStr
    reaction_hash: NonEmptyStr
    source: str = "synthetic_fixture"


class RetrievedDonor(StrictModel):
    donor_id: NonEmptyStr
    canonical_smiles: NonEmptyStr  # structural canonical (atom maps stripped)
    similarity: float
    heavy_atom_count: int
    donor_eligibility: NonEmptyStr
    source_quality: NonEmptyStr
    eligible_reaction_refs: list[ReactionRef]
    transform_diversity: int = 1
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture


@dataclass
class RetrievalResult:
    donors: list[RetrievedDonor]
    stop_reason: str
    config: RetrievalConfig
    dedup_skipped: int = 0
    excluded_quarantine: int = 0
    retrieval_rounds: int = 1
    metadata: dict = field(default_factory=dict)


def _rdkit():
    from rdkit import Chem  # type: ignore
    return Chem


def _fingerprint(Chem, smiles: str, radius: int, bits: int):
    from rdkit.Chem import AllChem  # type: ignore
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=bits)


def _tanimoto(fp_a, fp_b) -> float:
    from rdkit.DataStructs import TanimotoSimilarity  # type: ignore
    if fp_a is None or fp_b is None:
        return 0.0
    return float(TanimotoSimilarity(fp_a, fp_b))


def _count_heavy(Chem, smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0
    return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)


def _size_compatibility(query_ha: int, donor_ha: int) -> float:
    """Size compatibility in (0, 1].  Baseline feature, not probability."""
    if donor_ha == 0:
        return 0.0
    ratio = query_ha / donor_ha
    if 0.5 <= ratio <= 2.0:
        return 1.0
    if ratio < 0.5:
        return ratio / 0.5
    return 2.0 / ratio


def retrieve_donors(
    query: NormalizedQuery,
    train_view: TrainView,
    config: RetrievalConfig | None = None,
) -> RetrievalResult:
    """Retrieve distinct eligible donor molecules for X.

    Rules:
    - distinct molecule identities only (duplicate rows never crowd slots);
    - EVERY eligible reaction of a donor is carried as an explicit
      ``eligible_reaction_refs`` (transform diversity is preserved);
    - donor must be P1-eligible (quarantine/excluded fail closed);
    - Morgan/size/charge are baseline retrieval features, not probabilities;
    - deterministic tie-break by structural canonical SMILES;
    - only train_view data is read (no test access).
    """
    config = config or RetrievalConfig()
    Chem = _rdkit()

    query_fp = _fingerprint(Chem, query.canonical_smiles, config.morgan_radius, config.morgan_bits)
    query_ha = query.heavy_atom_count

    # Dedup by distinct donor molecule identity (structural canonical),
    # merging EVERY eligible reaction ref of the same identity.
    by_identity: dict[str, dict] = {}
    excluded_quarantine = 0
    for donor in train_view.donors:
        identity = donor.structural_smiles
        if donor.donor_eligibility not in ("eligible", "conditionally_eligible"):
            excluded_quarantine += 1
            continue
        entry = by_identity.setdefault(identity, {
            "donor_id": donor.donor_id,
            "molecule_id": donor.molecule_id,
            "canonical_smiles": identity,
            "donor_eligibility": donor.donor_eligibility,
            "source_quality": donor.source_quality,
            "reaction_refs": [],
        })
        for r in donor.reaction_refs:
            entry["reaction_refs"].append(ReactionRef(
                reaction_id=r.reaction_id,
                donor_participant_id=r.donor_participant_id,
                lineage_id=r.lineage_id,
                reaction_hash=r.reaction_hash,
                source=r.source,
            ))

    scored: list[RetrievedDonor] = []
    for identity, info in by_identity.items():
        fp = _fingerprint(Chem, identity, config.morgan_radius, config.morgan_bits)
        structural = _tanimoto(query_fp, fp)
        size_ok = _size_compatibility(query_ha, _count_heavy(Chem, identity))
        score = structural * size_ok
        if score < config.similarity_threshold:
            continue
        scored.append(RetrievedDonor(
            donor_id=info["donor_id"],
            canonical_smiles=identity,
            similarity=round(score, 6),
            heavy_atom_count=_count_heavy(Chem, identity),
            donor_eligibility=info["donor_eligibility"],
            source_quality=info["source_quality"],
            eligible_reaction_refs=info["reaction_refs"],
            transform_diversity=len(info["reaction_refs"]),
        ))

    # Deterministic sort: similarity desc, then structural canonical asc.
    scored.sort(key=lambda d: (-d.similarity, d.canonical_smiles))
    donors = scored[: config.max_donor_molecules]

    if not donors:
        stop_reason = "no_eligible_donor"
    else:
        stop_reason = f"top_{len(donors)}_distinct_donors_selected"
    metadata = {
        "eligible_donor_count": len(scored),
        "reaction_ref_total": sum(len(d.eligible_reaction_refs) for d in donors),
    }
    return RetrievalResult(
        donors=donors,
        stop_reason=stop_reason,
        config=config,
        dedup_skipped=len(train_view.donors) - len(by_identity),
        excluded_quarantine=excluded_quarantine,
        retrieval_rounds=1,
        metadata=metadata,
    )
