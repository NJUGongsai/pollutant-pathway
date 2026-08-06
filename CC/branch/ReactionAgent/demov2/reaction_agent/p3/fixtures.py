"""P3 synthetic fixtures built through the real P1 machinery.

Every fixture is declared ``synthetic_fixture``.  The fixture builder runs the
P1 pipeline (RealMapperAdapter -> roles -> lineage -> source ledger ->
eligibility) on explicitly atom-mapped synthetic reactions so the P3 kernel is
exercised against REAL P1 outputs.  These fixtures NEVER masquerade as real
evidence; any report that consumes them must keep the evidence_kind flag.

Covered reaction classes:
- rxn_oct      : primary alcohol -> aldehyde (oxidation; bond order + H change)
- rxn_reduction: aldehyde -> primary alcohol (bond order decrease + H add)
- rxn_decarb   : carboxylic acid -> alkane + CO2 (bond delete + atom removal)
- rxn_hydrolysis: ester + H2O -> acid + alcohol (bond delete + atom transfer)

The P1 lineage regression (proline / 2-oxoglutarate / O2) is NOT claimed here:
real cases were quarantined in P1 (see P1 final pass §2.1).  Synthetic
hydroxylation is therefore not offered as a real-evidence substitute.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rdkit import Chem  # type: ignore

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.mapping.adapter import RealMapperAdapter
from reaction_agent.schemas.evidence import ReactionEvidence, ReactionParticipant
from reaction_agent.schemas.p1_entities import (
    NormalizedReactionRecord,
    ResolvedTransformedLineage,
)
from reaction_agent.provenance import SourceRecordProvenance
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.ledger import SourceReactionLedger
from reaction_agent.schemas.common import EligibilityStatus


@dataclass
class FixtureReaction:
    """A complete synthetic donor reaction with its P1-derived outputs."""
    name: str
    reaction_id: str
    reactant_smiles: list[str]
    product_smiles: list[str]
    direction: str
    evidence: ReactionEvidence
    mapping_report: MappingReport
    participants: list[ReactionParticipant]
    lineages: list[ResolvedTransformedLineage]
    source_ledger: SourceReactionLedger
    eligibility: Any  # EligibilityDecision
    donor_participant_id: str
    donor_eligibility: Any  # DonorEligibilityAssessment
    source_ledger_id: str = ""
    evidence_kind: str = "synthetic_fixture"


def strip_atom_maps(smiles: str) -> str:
    """Return the structural canonical SMILES with atom map numbers removed."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return smiles
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol)


def _parse_fragment_maps(smiles: str) -> list[int]:
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"fixture fragment unparseable: {smiles}"
    maps = [a.GetAtomMapNum() for a in mol.GetAtoms()]
    return sorted(m for m in maps if m > 0)


def _mapped_fraction(mol) -> float:
    total = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() > 1)
    if total == 0:
        return 0.0
    mapped = sum(1 for a in mol.GetAtoms() if a.GetAtomMapNum() > 0 and a.GetAtomicNum() > 1)
    return mapped / total


def build_fixture_reaction(
    *,
    name: str,
    reactant_smiles: list[str],
    product_smiles: list[str],
    direction: str = "forward",
    source_name: str = "synthetic_fixture",
    donor_fragment: int = 0,
) -> FixtureReaction:
    """Run the real P1 pipeline on a synthetic atom-mapped reaction."""
    reaction_id = f"fx_{name}"
    reaction_smiles = ".".join(reactant_smiles) + ">>" + ".".join(product_smiles)
    prov = SourceRecordProvenance(
        source_name=source_name,
        source_version="1",
        source_record_id=f"{reaction_id}_rec",
        source_file_hash=canonical_hash({"fixture": name}),
        raw_record_hash=canonical_hash({"reaction": reaction_smiles}),
        normalizer_version="p1-1",
        created_by_build_id="p3-fixture-builder",
    )
    record = NormalizedReactionRecord(
        reaction_id=reaction_id,
        source_record_id=f"{reaction_id}_rec",
        normalized_reaction=reaction_smiles,
        raw_reaction=reaction_smiles,
        direction=direction,
        provenance=prov,
    )
    mapper = RealMapperAdapter(backend="rdkit")
    if not mapper.is_available():
        raise RuntimeError("RDKit mapper unavailable — cannot build fixtures")
    mapping_report = mapper.map_reaction(record)

    # Build participants (one per fragment, mapped SMILES preserved).
    # stoichiometry + provenance are set EXPLICITLY so the P1 source ledger
    # records source_completeness=complete (no-fabrication: defaults are not
    # recorded facts).
    provenance_tag = [f"fx:{reaction_id}:rec"]
    participants: list[ReactionParticipant] = []
    for frag_index, frag in enumerate(reactant_smiles):
        mol = Chem.MolFromSmiles(frag)
        maps = _parse_fragment_maps(frag)
        canonical = Chem.MolToSmiles(mol)  # preserves atom map numbers
        participants.append(ReactionParticipant(
            participant_id=f"{reaction_id}_reactant_{frag_index}",
            molecule_id=f"A_{name}_{frag_index}",
            canonical_smiles=canonical,
            side="reactant",
            stoichiometry=1,
            atom_map_numbers=maps,
            mapped_fraction=_mapped_fraction(mol),
            donor_eligibility=True,
            provenance=list(provenance_tag),
        ))
    for frag_index, frag in enumerate(product_smiles):
        mol = Chem.MolFromSmiles(frag)
        maps = _parse_fragment_maps(frag)
        canonical = Chem.MolToSmiles(mol)
        participants.append(ReactionParticipant(
            participant_id=f"{reaction_id}_product_{frag_index}",
            molecule_id=f"B_{name}_{frag_index}",
            canonical_smiles=canonical,
            side="product",
            stoichiometry=1,
            atom_map_numbers=maps,
            mapped_fraction=_mapped_fraction(mol),
            provenance=list(provenance_tag),
        ))

    # Roles (never deletes participants).
    from reaction_agent.roles.resolver import resolve_roles, assess_donor_eligibility
    participants = resolve_roles(participants)

    # Lineage.
    from reaction_agent.lineage.resolver import build_lineage_graph, resolve_lineages
    graph = build_lineage_graph(participants, mapping_report)
    lineages = resolve_lineages(graph)

    # Source ledger + eligibility.
    from reaction_agent.ledgers.source_builder import build_source_ledger
    from reaction_agent.eligibility.engine import decide_eligibility
    evidence = ReactionEvidence(
        reaction_id=reaction_id,
        source_record_id=f"{reaction_id}_rec",
        source_name=source_name,
        raw_reaction=reaction_smiles,
        normalized_reaction=reaction_smiles,
        direction=direction,
        participants=participants,
        mapping_report=mapping_report,
        resolved_transformed_lineages=[l.lineage_id for l in lineages],
        source_reaction_ledger=None,
        snapshot_id="fx_snapshot_p3",
    )
    ledger = build_source_ledger(evidence, lineages)
    eligibility = decide_eligibility(evidence, ledger, lineages)

    evidence = evidence.model_copy(update={"source_reaction_ledger": ledger})

    # Designated donor participant (the transformed substrate fragment).
    donor_participant_id = f"{reaction_id}_reactant_{donor_fragment}"
    donor_participant = next(
        p for p in participants if p.participant_id == donor_participant_id
    )
    donor_eligibility = assess_donor_eligibility(donor_participant, mapping_report)

    return FixtureReaction(
        name=name,
        reaction_id=reaction_id,
        reactant_smiles=reactant_smiles,
        product_smiles=product_smiles,
        direction=direction,
        evidence=evidence,
        mapping_report=mapping_report,
        participants=participants,
        lineages=lineages,
        source_ledger=ledger,
        eligibility=eligibility,
        donor_participant_id=donor_participant_id,
        donor_eligibility=donor_eligibility,
        source_ledger_id=ledger.ledger_id,
    )


def load_fixture_reactions() -> dict[str, FixtureReaction]:
    """Build all core synthetic donor reactions."""
    fixtures = {}

    fixtures["rxn_oct"] = build_fixture_reaction(
        name="oct",
        reactant_smiles=["[CH3:1][CH2:2][CH2:3][CH2:4][CH2:5][CH2:6][CH2:7][CH2:8][OH:9]"],
        product_smiles=["[CH3:1][CH2:2][CH2:3][CH2:4][CH2:5][CH2:6][CH2:7][CH:8]=[O:9]"],
    )

    # Second complete reaction of the SAME donor (octanol) with a DIFFERENT
    # transform: dehydration -> oct-1-ene + H2O.  The kernel must process ALL
    # eligible reactions of donor A (transform diversity), not just the first.
    fixtures["rxn_oct_dehyd"] = build_fixture_reaction(
        name="oct_dehyd",
        reactant_smiles=["[CH3:1][CH2:2][CH2:3][CH2:4][CH2:5][CH2:6][CH2:7][CH2:8][OH:9]"],
        product_smiles=[
            "[CH3:1][CH2:2][CH2:3][CH2:4][CH2:5][CH2:6][CH:7]=[CH2:8]",
            "[OH2:9]",
        ],
    )

    fixtures["rxn_reduction"] = build_fixture_reaction(
        name="reduction",
        reactant_smiles=["[CH3:1][CH2:2][CH2:3][CH:4]=[O:5]"],
        product_smiles=["[CH3:1][CH2:2][CH2:3][CH2:4][O:5][H:6]"],
    )

    fixtures["rxn_decarb"] = build_fixture_reaction(
        name="decarb",
        reactant_smiles=["[CH3:1][CH2:2][CH2:3][C:4](=[O:6])[OH:5]"],
        product_smiles=[
            "[CH3:1][CH2:2][CH3:3]",
            "[O:5]=[C:4]=[O:6]",
        ],
    )

    fixtures["rxn_hydrolysis"] = build_fixture_reaction(
        name="hydrolysis",
        reactant_smiles=[
            "[CH3:1][C:2](=[O:3])[O:4][CH2:5][CH3:6]",
            "[OH2:7]",
        ],
        product_smiles=[
            "[CH3:1][C:2](=[O:3])[O:7][H:9]",
            "[CH3:6][CH2:5][O:4][H:8]",
        ],
    )

    return fixtures


# -- Train view (P3-T2 input) ------------------------------------------------

@dataclass
class ReactionRef:
    """An explicit reference to one eligible complete reaction of a donor."""
    reaction_id: str
    donor_participant_id: str
    lineage_id: str
    reaction_hash: str
    source: str = "synthetic_fixture"


@dataclass
class DonorEntry:
    """A DISTINCT donor molecule identity with all its eligible reactions."""
    donor_id: str
    molecule_id: str
    canonical_smiles: str       # mapped SMILES of the primary donor participant
    structural_smiles: str      # stripped canonical identity (dedup key)
    donor_eligibility: str
    source_quality: str
    fold_id: str
    reaction_refs: list[ReactionRef]


@dataclass
class TrainView:
    """Train-only donor index.  Contains NO test query / reaction / truth.

    Fold identity + snapshot identity are authoritative and immutable here;
    they may NOT be overridden by callers (R2-B fold authority).

    R5-C: ``authority_manifest`` — when set, it is the FROZEN P1/P2 authority
    root (a trusted manifest built BEFORE the run).  The train view's
    snapshot hash and every reaction's authority hash must then be verified
    against this frozen root, NEVER against a caller-recomputed hash.  A
    mutation can change candidate reaction content but must preserve the
    frozen expected root — so a fully-synchronized strip produces an
    authority mismatch.
    """
    fold_id: str
    snapshot_id: str
    snapshot_hash: str
    donors: list[DonorEntry]
    reactions: dict[str, FixtureReaction]
    # R7-B: the authority root is EITHER a fixture manifest (synthetic_fixture)
    # OR a production handle (the only type accepted as a production
    # authority) — never a bare dict / relabeled kind string.
    authority_manifest: "FixtureAuthorityManifest | ProductionAuthorityHandle | None" = None


@dataclass
class FixtureAuthorityManifest:
    """R5-C / R6-C / R7-B: the frozen FIXTURE authority root for a train view.

    Built by ``build_fixture_authority_manifest`` from the REAL P1 snapshot
    builder pipeline (``compute_snapshot_hash`` — the same canonical content
    payload the P1 loader verifies).  The manifest is frozen BEFORE any
    mutation; the P3 loader verifies the train view against it.

    R7-B: this is a FIXTURE-only type.  ``kind`` is FIXED at
    ``"synthetic_fixture"`` — ``__post_init__`` rejects any other value, so a
    caller cannot relabel a fixture manifest as a production authority via
    ``dataclasses.replace``.  The production loader requires a separate
    ``ProductionAuthorityHandle`` type (see below); a fixture manifest is
    NEVER accepted as a production authority, regardless of its self-hash.

    - ``snapshot_id`` / ``snapshot_hash``: the frozen P1 snapshot identity.
    - ``reaction_hashes``: reaction_id -> expected reaction authority hash,
      derived from the COMPLETE reaction evidence (participants, ledger,
      mapping, lineages, raw reaction) at freeze time.
    - ``provenance``: verifiable provenance of the frozen snapshot /
      lineage / ledger / eligibility data authority this root was derived
      from.
    - ``manifest_hash``: the canonical self-hash of the manifest; the loader
      recomputes it and rejects any tampered snapshot identity / version /
      reaction hash (cross-bound).  The self-hash is an INTEGRITY check only
      — it is never a provenance authority by itself.
    """
    snapshot_id: str
    snapshot_hash: str
    reaction_hashes: dict[str, str]
    version: str = "p3-r6-1"
    kind: str = "synthetic_fixture"
    provenance: str = ""
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        # R7-B: the fixture kind is FIXED — a caller can never relabel this
        # object as a production authority (dataclasses.replace re-runs this).
        if self.kind != "synthetic_fixture":
            raise ValueError(
                "FixtureAuthorityManifest.kind must be 'synthetic_fixture'; "
                "a fixture manifest can never be relabelled as production"
            )


# Backward-compatible alias used by earlier rounds (R5-C/R6-C) — the fixture
# authority type.  Production authority is a separate type (R7-B).
FrozenAuthorityManifest = FixtureAuthorityManifest


class _ProductionAuthorityProof:
    """Module-private token that gates construction of ``ProductionAuthorityHandle``.

    The token is created once at import time and is never exported.  A public
    caller cannot obtain it, so it cannot construct a production authority
    handle.  Only the internal P1/P2 authority adapter (which verifies the
    real P1/P2 snapshot/lineage/ledger/eligibility artifacts) can create one.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<p3-production-authority-proof>"


_PRODUCTION_AUTHORITY_PROOF = _ProductionAuthorityProof()


@dataclass
class ProductionAuthorityHandle:
    """R7-B: the ONLY type accepted as a production (P1/P2) authority root.

    This is a distinct type from ``FixtureAuthorityManifest``.  The
    constructor requires the module-private proof token
    ``_PRODUCTION_AUTHORITY_PROOF`` (never exported); a public caller cannot
    construct one, and a fixture manifest can NEVER be converted into one.
    Only the internal adapter ``_build_production_authority_handle`` — which
    verifies the real P1/P2 snapshot / lineage / ledger / eligibility
    artifacts — can create a production handle.

    ``kind`` is a fixed property returning ``"production"``: the type itself
    IS the production claim, so there is no mutable kind field to relabel.

    While the real P1/P2 root is unavailable, no production handle exists and
    the real loader / kernel return ``PRODUCTION_AUTHORITY_UNAVAILABLE``
    (typed BLOCKED) — they never manufacture a production root.
    """
    snapshot_id: str
    snapshot_hash: str
    reaction_hashes: dict[str, str]
    version: str = "p3-r7-1"
    provenance: str = ""
    manifest_hash: str = ""
    _proof: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._proof is not _PRODUCTION_AUTHORITY_PROOF:
            raise TypeError(
                "ProductionAuthorityHandle is not constructible by callers; "
                "only the internal P1/P2 authority adapter can create one"
            )

    @property
    def kind(self) -> str:
        return "production"


def _authority_manifest_canonical(
    root: "FixtureAuthorityManifest | ProductionAuthorityHandle",
) -> dict:
    """R6-C / R7-B: the canonical preimage of the authority root's self-hash.

    Works for BOTH the fixture manifest and the production handle (the type
    itself is the kind authority; the self-hash is an integrity check only).
    """
    return {
        "snapshot_id": root.snapshot_id,
        "snapshot_hash": root.snapshot_hash,
        "reaction_hashes": dict(sorted(root.reaction_hashes.items())),
        "version": root.version,
        "kind": root.kind,
        "provenance": root.provenance,
    }


def authority_manifest_hash(
    root: "FixtureAuthorityManifest | ProductionAuthorityHandle",
) -> str:
    """R6-C / R7-B: the canonical self-hash of an authority root.

    Integrity check only — it never grants production authority.  A caller
    that recomputes the self-hash of a fixture manifest still cannot make it
    a ``ProductionAuthorityHandle``.
    """
    return canonical_hash(_authority_manifest_canonical(root))


def build_fixture_authority_manifest(
    fixtures: dict[str, FixtureReaction],
) -> FixtureAuthorityManifest:
    """R5-C / R6-C / R7-B: freeze the FIXTURE authority root for a set of
    fixture reactions.

    Uses the REAL P1 snapshot builder's canonical content pipeline
    (``compute_snapshot_hash``) so the snapshot hash is the P1 authority
    hash — never a P3-caller-recomputed value.  Each reaction's expected
    authority hash is the canonical reaction hash of the COMPLETE record at
    freeze time.

    R6-C / R7-B: the returned object is ALWAYS a ``FixtureAuthorityManifest``
    (``kind="synthetic_fixture"`` fixed by the type).  It is a FIXTURE
    authority — it can never be accepted as a production (P1/P2) authority by
    the production loader, and it can never be relabelled as one (the kind is
    immutable).  A production root is a separate ``ProductionAuthorityHandle``
    type that only the internal P1/P2 authority adapter can create.

    The manifest is frozen BEFORE any mutation: a mutation that strips the
    reaction content can recompute the local reaction hash / train-view hash,
    but it CANNOT change this manifest (the expected root stays frozen), so
    the loader detects the mismatch.
    """
    from reaction_agent.config import BuildConfig
    from reaction_agent.snapshot.builder import (
        SnapshotEvidenceItem,
        compute_snapshot_hash,
    )

    cfg = BuildConfig(
        input_source="p3_fixture_authority",
        output_snapshot_root="/tmp/p3_fixture_authority_unused",
        mapper_backend="rdkit",
        mapper_version="p1-1",
        normalization_version="p1-1",
        role_policy_version="p1-1",
        lineage_resolver_version="p1-1",
        ledger_version="p1-1",
        eligibility_policy_version="p1-1",
        random_seed=0,
    )
    items = [
        SnapshotEvidenceItem(
            reaction_evidence=fx.evidence,
            source_ledger=fx.source_ledger,
            lineages=fx.lineages,
        )
        for fx in fixtures.values()
    ]
    snapshot_hash = compute_snapshot_hash(cfg, items)
    snapshot_id = f"snap_{snapshot_hash[:12]}"
    reaction_hashes = {
        fx.reaction_id: canonical_reaction_hash(fx)
        for fx in fixtures.values()
    }
    root = FixtureAuthorityManifest(
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        reaction_hashes=reaction_hashes,
        kind="synthetic_fixture",
        provenance=(
            "p1-snapshot-builder:fixture:demov2"
            f":{cfg.normalization_version}:{REACTION_AUTHORITY_VERSION}"
        ),
    )
    root = FixtureAuthorityManifest(
        **{**root.__dict__, "manifest_hash": authority_manifest_hash(root)}
    )
    return root


def _build_production_authority_handle(
    snapshot_id: str,
    snapshot_hash: str,
    reaction_hashes: dict[str, str],
    *,
    provenance: str,
    version: str = "p3-r7-1",
) -> ProductionAuthorityHandle:
    """R7-B: INTERNAL adapter — the ONLY way a ``ProductionAuthorityHandle``
    can be created.

    The caller (inside the P3 kernel boundary) is responsible for having
    VERIFIED the real P1/P2 snapshot / lineage / ledger / eligibility
    artifacts before calling this.  While the real P1/P2 root is unavailable,
    this adapter is never called and the real loader / kernel return
    ``PRODUCTION_AUTHORITY_UNAVAILABLE`` (typed BLOCKED) instead of
    manufacturing a production root.

    The constructor requires the module-private proof token, so a public
    caller can never forge a production handle.
    """
    handle = ProductionAuthorityHandle(
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        reaction_hashes=reaction_hashes,
        version=version,
        provenance=provenance,
        _proof=_PRODUCTION_AUTHORITY_PROOF,
    )
    return ProductionAuthorityHandle(
        **{**handle.__dict__, "manifest_hash": authority_manifest_hash(handle)}
    )


def find_donor_ref(train_view: "TrainView", reaction_id: str):
    """Return (donor, reaction_ref) for a train-view reaction id."""
    for donor in train_view.donors:
        for ref in donor.reaction_refs:
            if ref.reaction_id == reaction_id:
                return donor, ref
    raise KeyError(f"reaction {reaction_id} not in train view")


# -- Reaction authority (R3-B) ----------------------------------------------

REACTION_AUTHORITY_VERSION = "p3-r3-1"


def _strip_runtime_metrics(d: dict) -> dict:
    """Remove non-semantic wall-clock timing from a mapping report dump.

    R4-B: ``mapper_parameters.runtime_ms`` is a performance metric, NOT
    reaction semantics.  It is explicitly excluded from the authority
    preimage (declared non-semantic here); a timing difference must never
    change the reaction authority hash.
    """
    if "mapper_parameters" in d and isinstance(d["mapper_parameters"], dict):
        d["mapper_parameters"] = {
            k: v for k, v in d["mapper_parameters"].items() if k != "runtime_ms"
        }
    return d


def reaction_authority_preimage(fixture: "FixtureReaction") -> dict:
    """Canonical reaction authority preimage (R3-B, R4-B).

    Covers the COMPLETE auditable reaction content — never a projection that
    a forge could sidestep:
    - the FULL reaction evidence record (raw_reaction, normalized reaction,
      direction, source metadata incl. source_name/version/uri, participants
      with formal_charge / changed_atom_fraction / role_hypotheses /
      donor_eligibility / provenance / atom maps, mapping report,
      fragment_lineage_graph, ambiguity_sets, transformation_hypotheses,
      provenance, quality_report, snapshot_id, quarantine, source ledger);
    - the resolved lineages (full objects, sorted);
    - eligibility + donor eligibility;
    - the donor participant binding;
    - component/schema versions.

    Every collection is canonically sorted so a semantically irrelevant input
    reordering cannot change the hash; ANY semantic field change MUST change
    the hash (R4-B).
    """
    import json as _json

    from reaction_agent.p3.schemas import P3_SCHEMA_VERSION

    evidence = fixture.evidence.model_dump(mode="json")
    # Canonicalize every collection so reordering is semantically inert.
    evidence["participants"] = sorted(
        evidence["participants"], key=lambda d: d["participant_id"]
    )
    evidence["resolved_transformed_lineages"] = sorted(
        evidence["resolved_transformed_lineages"]
    )
    evidence["ambiguity_sets"] = sorted(
        evidence["ambiguity_sets"],
        key=lambda d: _json.dumps(d, sort_keys=True, default=str),
    )
    evidence["transformation_hypotheses"] = sorted(
        evidence["transformation_hypotheses"]
    )
    evidence["fragment_lineage_graph"] = dict(
        sorted(evidence["fragment_lineage_graph"].items())
    )
    evidence["quality_report"] = dict(sorted(evidence["quality_report"].items()))
    if evidence.get("mapping_report") is not None:
        evidence["mapping_report"] = _strip_runtime_metrics(
            evidence["mapping_report"]
        )
    return {
        "reaction_authority_version": REACTION_AUTHORITY_VERSION,
        "schema_version": P3_SCHEMA_VERSION,
        "reaction_id": fixture.reaction_id,
        "evidence": evidence,
        "mapping_report": _strip_runtime_metrics(
            fixture.mapping_report.model_dump(mode="json")
        ),
        "resolved_lineages": sorted(
            (l.model_dump(mode="json") for l in fixture.lineages),
            key=lambda d: d["lineage_id"],
        ),
        "source_ledger": fixture.source_ledger.model_dump(mode="json"),
        "eligibility": fixture.eligibility.model_dump(mode="json"),
        "donor_eligibility": fixture.donor_eligibility.model_dump(mode="json"),
        "donor_participant_id": fixture.donor_participant_id,
    }


def canonical_reaction_hash(fixture: "FixtureReaction") -> str:
    """Derive the reaction authority hash from the complete preimage (R3-B).

    Every ``ReactionRef.reaction_hash`` MUST be this value; the loader
    recomputes it from the live record and never trusts a stored string.
    """
    return canonical_hash(reaction_authority_preimage(fixture))


def _train_view_preimage(fold_id: str, donors: list) -> dict:
    """Shared snapshot preimage used by BOTH build and recompute (R3-B).

    Includes the complete, sorted reaction references WITH their authority
    hashes — a forged or stale ref changes the snapshot hash.
    """
    return {
        "fold": fold_id,
        "snapshot_authority_version": REACTION_AUTHORITY_VERSION,
        "donors": sorted(
            [
                {
                    "identity": d.structural_smiles,
                    "donor_id": d.donor_id,
                    "molecule_id": d.molecule_id,
                    "donor_eligibility": d.donor_eligibility,
                    "refs": sorted(
                        [
                            {
                                "reaction_id": r.reaction_id,
                                "donor_participant_id": r.donor_participant_id,
                                "lineage_id": r.lineage_id,
                                "reaction_hash": r.reaction_hash,
                            }
                            for r in d.reaction_refs
                        ],
                        key=lambda r: r["reaction_id"],
                    ),
                }
                for d in donors
            ],
            key=lambda d: d["identity"],
        ),
    }


def recompute_train_view_hash(train_view: "TrainView") -> str:
    """Deterministically recompute the fold snapshot hash from donor entries.

    R3-B: covers fold + complete sorted reaction references including every
    ``ReactionRef.reaction_hash`` (the reaction authority binding).
    """
    return canonical_hash(_train_view_preimage(train_view.fold_id, train_view.donors))


def validate_train_view_authority(train_view: "TrainView") -> None:
    """Verify the frozen train-only view authority (R2-B fold isolation).

    R5-C / R6-C: the train view MUST carry a frozen authority manifest
    (fail-closed when absent — a manually-constructed train view without an
    upstream authority handle is not a production authority).  The manifest
    is verified as a cross-bound authority root:

    - the manifest self-hash recomputes from its fields (snapshot identity,
      reaction hashes, version, kind, provenance) — a tampered root is
      rejected;
    - the manifest reaction ID set must EXACTLY equal the train view's
      reaction refs — a missing OR extra reaction ID fails closed (no
      ``continue``);
    - every ReactionRef.reaction_hash must equal the frozen expected hash
      derived from the COMPLETE reaction evidence at freeze time.  A caller
      that recomputes the local reaction hash AND the train view hash from
      stripped content still cannot change the frozen expected root →
      FROZEN_REACTION_HASH_MISMATCH.

    Raises FoldIsolationError on:
    - missing authority manifest (MISSING_AUTHORITY);
    - snapshot_hash mismatch (tampered / repackaged train view);
    - empty fold/snapshot identity;
    - a donor entry whose fold differs from the train view fold;
    - manifest self-hash mismatch, missing/extra reaction IDs, or any
      frozen-authority mismatch (expected root violation).
    """
    from reaction_agent.p3.load import FoldIsolationError

    if not train_view.fold_id or not train_view.snapshot_id:
        raise FoldIsolationError("train view missing fold_id / snapshot_id")
    if not train_view.snapshot_hash:
        raise FoldIsolationError("train view missing snapshot_hash")
    # R6-C: the train view MUST carry an upstream authority handle.
    manifest = train_view.authority_manifest
    if manifest is None:
        raise FoldIsolationError(
            "train view carries no frozen authority manifest (upstream "
            "authority required)",
            failure_code="MISSING_AUTHORITY",
        )
    # R7-B: the authority root MUST be a typed fixture manifest or a typed
    # production handle — never a bare dict / relabeled object.  A caller
    # cannot smuggle a forged authority root through a plain object.
    if not isinstance(
        manifest, (FixtureAuthorityManifest, ProductionAuthorityHandle)
    ):
        raise FoldIsolationError(
            "train view carries an invalid authority root: must be a "
            "FixtureAuthorityManifest or ProductionAuthorityHandle, got "
            f"{type(manifest).__name__}",
            failure_code="INVALID_AUTHORITY_ROOT",
        )
    # Fold-pollution check BEFORE the hash recompute so a donor smuggled in
    # from another fold is reported as FOLD_ISOLATION, not as a hash mismatch.
    for donor in train_view.donors:
        if donor.fold_id and donor.fold_id != train_view.fold_id:
            raise FoldIsolationError(
                f"donor {donor.donor_id} fold {donor.fold_id!r} != "
                f"train view fold {train_view.fold_id!r}",
                failure_code="FOLD_ISOLATION",
            )
    expected = recompute_train_view_hash(train_view)
    if train_view.snapshot_hash != expected:
        raise FoldIsolationError(
            f"train view snapshot_hash mismatch: stored {train_view.snapshot_hash[:12]} "
            f"!= recomputed {expected[:12]}",
            failure_code="FOLD_AUTHORITY_HASH",
        )
    # R6-C: the manifest must be self-consistent (cross-bound snapshot
    # identity / version / reaction hashes / kind / provenance).
    if not manifest.manifest_hash:
        raise FoldIsolationError(
            "frozen authority manifest missing its self-hash",
            failure_code="FROZEN_MANIFEST_SELF_HASH_MISSING",
        )
    recomputed_manifest_hash = authority_manifest_hash(manifest)
    if recomputed_manifest_hash != manifest.manifest_hash:
        raise FoldIsolationError(
            f"frozen authority manifest self-hash mismatch: stored "
            f"{manifest.manifest_hash[:12]} != recomputed "
            f"{recomputed_manifest_hash[:12]} (tampered snapshot identity / "
            f"version / reaction hash)",
            failure_code="FROZEN_MANIFEST_SELF_HASH_MISMATCH",
        )
    # R6-C: EXACT-SET matching — the manifest reaction ID set must equal the
    # train view's reaction refs.  Missing OR extra reaction IDs fail closed
    # (no ``continue``).
    manifest_reaction_ids = set(manifest.reaction_hashes)
    tv_reaction_ids = {
        ref.reaction_id for donor in train_view.donors for ref in donor.reaction_refs
    }
    missing_ids = sorted(tv_reaction_ids - manifest_reaction_ids)
    extra_ids = sorted(manifest_reaction_ids - tv_reaction_ids)
    if missing_ids:
        raise FoldIsolationError(
            f"frozen authority manifest is missing expected reaction IDs "
            f"{missing_ids} (train view references them but the frozen root "
            f"does not)",
            failure_code="FROZEN_MISSING_REACTION_ID",
        )
    if extra_ids:
        raise FoldIsolationError(
            f"frozen authority manifest declares extra reaction IDs "
            f"{extra_ids} (not present in the train view)",
            failure_code="FROZEN_EXTRA_REACTION_ID",
        )
    # The P3 train-view snapshot hash (a DIFFERENT preimage from the P1
    # authority snapshot hash) is independently verified above.  The
    # authority binding that matters for the A/B-only strip is the
    # REACTION-level frozen hash: every ReactionRef.reaction_hash must equal
    # the frozen expected hash derived from the COMPLETE reaction evidence at
    # freeze time.  A caller that recomputes the local reaction hash AND the
    # train view hash from stripped content still cannot change the frozen
    # expected root → FROZEN_REACTION_HASH_MISMATCH.
    for donor in train_view.donors:
        for ref in donor.reaction_refs:
            expected_rx = manifest.reaction_hashes[ref.reaction_id]
            if ref.reaction_hash != expected_rx:
                raise FoldIsolationError(
                    f"reaction {ref.reaction_id} ReactionRef.reaction_hash "
                    f"{ref.reaction_hash[:12]} != FROZEN authority reaction "
                    f"hash {expected_rx[:12]} (fully-synchronized strip: "
                    f"the caller recomputed the local hash but the frozen "
                    f"root still governs)",
                    failure_code="FROZEN_REACTION_HASH_MISMATCH",
                )


def select_primary_lineage(fixture: FixtureReaction):
    """Select the primary A->B lineage for the designated donor.

    Among resolved lineages whose reactant is the donor, prefer the one whose
    product is a transformed product (not a small coproduct like CO2/H2O).
    """
    from reaction_agent.schemas.common import ParticipantRole

    donor = fixture.donor_participant_id
    candidates = [
        l for l in fixture.lineages
        if l.reactant_participant_id == donor
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    role_by_id = {
        p.participant_id: max(
            (h.role for h in p.role_hypotheses),
            key=lambda r: next(
                (h.score for h in p.role_hypotheses if h.role == r), 0.0
            ),
        )
        for p in fixture.participants
    }
    scored = sorted(
        candidates,
        key=lambda l: 0
        if role_by_id.get(l.product_participant_id)
        == ParticipantRole.transformed_product
        else 1,
    )
    return scored[0]


def build_train_view(
    fixtures: dict[str, FixtureReaction],
    *,
    authority_manifest: "FixtureAuthorityManifest | ProductionAuthorityHandle | None" = None,
) -> TrainView:
    """Build a train-only donor index from synthetic fixture reactions.

    Only reactions whose P1 eligibility allows production use are indexed
    (conditional_eligible / strict_eligible).  Donors are DEDUPLICATED by
    structural molecule identity; every eligible reaction of the same donor
    is preserved as an explicit ReactionRef (transform diversity is never
    lost during dedup).

    R6-C: the train view ALWAYS carries a frozen authority manifest.  When
    the caller does not provide one, the FIXTURE authority (explicitly
    ``synthetic_fixture`` semantics) is frozen from the REAL P1 snapshot
    builder pipeline and attached.  A manually-constructed ``TrainView``
    without an authority manifest is rejected by the loader (fail-closed).
    """
    fold_id = "fold_fx_p3"
    by_identity: dict[str, list[tuple[FixtureReaction, ReactionParticipant]]] = {}
    for fixture in fixtures.values():
        if fixture.eligibility.eligibility not in (
            EligibilityStatus.strict_eligible,
            EligibilityStatus.conditional_eligible,
        ):
            continue
        donor = next(
            p for p in fixture.participants
            if p.participant_id == fixture.donor_participant_id
        )
        structural = strip_atom_maps(donor.canonical_smiles)
        by_identity.setdefault(structural, []).append((fixture, donor))

    donors: list[DonorEntry] = []
    for structural in sorted(by_identity):
        entries = sorted(by_identity[structural], key=lambda e: e[0].reaction_id)
        first_fixture, first_donor = entries[0]
        refs: list[ReactionRef] = []
        for fx, donor_p in entries:
            lineage = select_primary_lineage(fx)
            refs.append(ReactionRef(
                reaction_id=fx.reaction_id,
                donor_participant_id=donor_p.participant_id,
                lineage_id=lineage.lineage_id if lineage else "",
                # R3-B: the ref is bound to the COMPLETE reaction authority
                # preimage, never a {reaction, reaction_id} projection.
                reaction_hash=canonical_reaction_hash(fx),
            ))
        donors.append(DonorEntry(
            donor_id=stable_id("donor", {"identity": structural}),
            molecule_id=first_donor.molecule_id,
            canonical_smiles=first_donor.canonical_smiles,
            structural_smiles=structural,
            donor_eligibility=first_fixture.donor_eligibility.eligibility,
            source_quality="synthetic_fixture",
            fold_id=fold_id,
            reaction_refs=refs,
        ))

    snapshot_hash = canonical_hash(_train_view_preimage(fold_id, donors))
    if authority_manifest is None:
        # R6-C: freeze the FIXTURE authority from the frozen P1 pipeline so
        # the train view never exists without an upstream authority handle.
        authority_manifest = build_fixture_authority_manifest(fixtures)
    return TrainView(
        fold_id=fold_id,
        snapshot_id="fx_snapshot_p3",
        snapshot_hash=snapshot_hash,
        donors=donors,
        reactions=fixtures,
        authority_manifest=authority_manifest,
    )


# -- Query cases -------------------------------------------------------------

@dataclass
class QueryCase:
    """A query + expected machinery outcome for contract tests."""
    case_id: str
    query_smiles: str
    expected_product: str | None  # canonical product (strip stereo/isotope) or None
    expect_site: bool
    expect_candidate: bool
    note: str


def build_query_cases() -> list[QueryCase]:
    return [
        QueryCase(
            case_id="case_octanol",
            query_smiles="CCCCCCCCO",
            expected_product="CCCCCCCC=O",
            expect_site=True,
            expect_candidate=True,
            note="octanol -> octanal regression (final_plan §6.7)",
        ),
        QueryCase(
            case_id="case_butanol",
            query_smiles="CCCCO",
            expected_product="CCCC=O",
            expect_site=True,
            expect_candidate=True,
            note="generic primary alcohol -> aldehyde",
        ),
        QueryCase(
            case_id="case_no_alcohol",
            query_smiles="CCCCC",
            expected_product=None,
            expect_site=False,
            expect_candidate=False,
            note="alkane: no compatible site",
        ),
        QueryCase(
            case_id="case_secondary_alcohol",
            query_smiles="CC(C)O",
            expected_product=None,
            expect_site=False,
            expect_candidate=False,
            note="secondary alcohol: wrong functional group for primary-alcohol transform",
        ),
        QueryCase(
            case_id="case_diol_symmetric",
            query_smiles="OCCCCCCO",
            expected_product="O=CCCCCCO",
            expect_site=True,
            expect_candidate=True,
            note="symmetric diol: sites symmetry-deduped to one site",
        ),
        QueryCase(
            case_id="case_invalid",
            query_smiles="C1CC1C(C(C",
            expected_product=None,
            expect_site=False,
            expect_candidate=False,
            note="unparseable input -> typed InvalidQueryError",
        ),
    ]
