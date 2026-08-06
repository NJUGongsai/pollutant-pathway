"""P3-T8 Canonical candidate store (final_plan §6.9).

- canonical_product_identity is the dedup key (stereo/isotope-agnostic)
- identical structures merge, but generation paths / support lineage /
  transform / site / source ledger evidence are NEVER dropped
- candidate_id is system-generated and recomputable from identity + version
  (never derived from an arbitrary input string)
"""
from __future__ import annotations

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.p3.schemas import (
    CandidateValidation,
    ConditionedSite,
    EvidenceKind,
    GenerationReport,
    NormalizedQuery,
    ResolvedDonorEvidence,
    StrictCandidate,
    StrictTransformation,
)
from reaction_agent.schemas.ledger import CandidateAnalogyLedger


def _product_identity(smiles: str, policy=None) -> str:
    """Canonical product identity used for dedup (R2-A/R2-F).

    Uses the SAME policy as the query identity: stereo-agnostic but isotope-
    preserving (a stereo-agnostic identity must NOT delete isotope markers,
    and isotope-labelled products must NOT be incorrectly deduped).
    """
    from reaction_agent.p3.identity import canonical_identity
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return smiles
    clean = Chem.RemoveHs(mol)
    if policy is not None:
        return canonical_identity(
            Chem.MolToSmiles(clean, isomericSmiles=True),
            stereo_policy=policy.stereo_policy,
            isotope_policy=policy.isotope_policy,
        )
    return canonical_identity(Chem.MolToSmiles(clean, isomericSmiles=True))


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


class CandidateStore:
    """Immutable-merge candidate store keyed by canonical product identity."""

    def __init__(
        self,
        *,
        run_id: str,
        case_id: str,
        query_id: str,
        fold_id: str,
        snapshot_id: str,
        snapshot_hash: str,
        query: NormalizedQuery,
        evidence_kind: EvidenceKind,
    ) -> None:
        self.run_id = run_id
        self.case_id = case_id
        self.query_id = query_id
        self.fold_id = fold_id
        self.snapshot_id = snapshot_id
        self.snapshot_hash = snapshot_hash
        self.query = query
        self.evidence_kind = evidence_kind
        self._entries: dict[str, dict] = {}

    def add(
        self,
        *,
        donor_id: str,
        reaction_id: str,
        lineage_id: str,
        report: GenerationReport,
        transform: StrictTransformation,
        site: ConditionedSite,
        validation: CandidateValidation,
        candidate_analogy_ledger: CandidateAnalogyLedger,
        source_ledger_id: str,
    ) -> str:
        """Merge one generation path into the canonical candidate (R2-F).

        Every path keeps its own evidence path (donor/reaction/lineage/
        transform/site/generation/source-ledger/candidate-ledger/validation).

        R3-E: the path is content-addressedly bound (path_id/path_hash) to
        its linkage fields AND the parent run namespace.
        """
        from reaction_agent.p3.schemas import (
            CandidateEvidencePath,
            compute_candidate_path_binding,
        )
        identity = _product_identity(report.canonical_product, self.query.normalization_policy)
        path_id, path_hash = compute_candidate_path_binding(
            donor_id=donor_id,
            reaction_id=reaction_id,
            lineage_id=lineage_id,
            transformation_id=transform.transformation_id,
            site_id=site.site_id,
            generation_report=report,
            source_ledger_id=source_ledger_id,
            candidate_analogy_ledger=candidate_analogy_ledger,
            run_id=self.run_id,
            case_id=self.case_id,
            query_id=self.query_id,
            fold_id=self.fold_id,
            snapshot_id=self.snapshot_id,
            snapshot_hash=self.snapshot_hash,
        )
        path = CandidateEvidencePath(
            donor_id=donor_id,
            reaction_id=reaction_id,
            lineage_id=lineage_id,
            transformation_id=transform.transformation_id,
            site_id=site.site_id,
            generation_report=report,
            source_ledger_id=source_ledger_id,
            candidate_analogy_ledger=candidate_analogy_ledger,
            validation=validation,
            path_id=path_id,
            path_hash=path_hash,
        )
        entry = self._entries.setdefault(identity, {
            "identity": identity,
            "generation_paths": [],
            "support_lineage_ids": [],
            "transformation_ids": [],
            "site_ids": [],
            "source_ledger_ids": [],
            "evidence_paths": [],
            "validation": validation,
            "candidate_analogy_ledger": candidate_analogy_ledger,
        })
        entry["generation_paths"].append(report)
        entry["evidence_paths"].append(path)
        entry["support_lineage_ids"].extend(transform.source_lineage_ids)
        entry["transformation_ids"].append(transform.transformation_id)
        entry["site_ids"].append(site.site_id)
        entry["source_ledger_ids"].append(source_ledger_id)
        # Validation must hold for every path merged into a strict candidate.
        if not validation.failure_code:
            if entry["validation"].failure_code:
                entry["validation"] = validation
        return identity

    def finalize(self) -> list[StrictCandidate]:
        candidates: list[StrictCandidate] = []
        for entry in self._entries.values():
            validation = entry["validation"]
            if validation.failure_code:
                continue  # rejected paths never enter the strict lane
            candidate_id = stable_id("cand", {
                "identity": entry["identity"],
                "version": "p3-1",
            })
            candidate = StrictCandidate(
                candidate_id=candidate_id,
                run_id=self.run_id,
                case_id=self.case_id,
                query_id=self.query_id,
                fold_id=self.fold_id,
                snapshot_id=self.snapshot_id,
                snapshot_hash=self.snapshot_hash,
                canonical_product_identity=entry["identity"],
                lane="strict",
                origin="deterministic_kernel",
                generation_paths=entry["generation_paths"],
                support_lineage_ids=_dedup_keep_order(entry["support_lineage_ids"]),
                transformation_ids=_dedup_keep_order(entry["transformation_ids"]),
                site_ids=_dedup_keep_order(entry["site_ids"]),
                validation=validation,
                source_ledger_ids=_dedup_keep_order(entry["source_ledger_ids"]),
                candidate_analogy_ledger=entry["candidate_analogy_ledger"],
                candidate_evidence_paths=entry["evidence_paths"],
                provenance=[
                    f"run:{self.case_id}",
                    f"query:{self.query_id}",
                    f"fold:{self.fold_id}",
                    f"kernel:p3-1",
                ],
                evidence_kind=self.evidence_kind,
            )
            candidates.append(candidate)
        # Deterministic ordering by candidate identity.
        candidates.sort(key=lambda c: c.candidate_id)
        return candidates
