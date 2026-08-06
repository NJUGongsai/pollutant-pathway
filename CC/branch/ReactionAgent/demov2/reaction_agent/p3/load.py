"""P3-T3 Complete reaction loader (final_plan §6.4, R2-B/R2-C).

Loads a SPECIFIC eligible complete reaction by explicit ReactionRef — never
"the first reaction of a donor identity".  Enforces:
- fold authority (fold comes only from the frozen train view);
- complete reaction evidence (participant multiset, mapping refs, lineage
  refs, source ledger refs all cross-consistent; no ID-name string matching);
- strict mapping / no critical ambiguity / eligibility fail-closed;
- cofactors and co-substrates are never stripped.
"""
from __future__ import annotations

from reaction_agent.p3.schemas import (
    EvidenceKind,
    ResolvedDonorEvidence,
    DonorContext,
)
from reaction_agent.p3.fixtures import (
    FixtureReaction,
    ReactionRef,
    TrainView,
    canonical_reaction_hash,
    validate_train_view_authority,
)
from reaction_agent.schemas.common import EligibilityStatus


class FoldIsolationError(ValueError):
    """Raised when fold authority is violated (R2-B).

    Carries a typed ``failure_code`` so callers (kernel isolation, mutation
    harness) never have to parse message strings (R3-B/R3-D/R3-F).
    """

    def __init__(self, message: str, failure_code: str = "FOLD_ISOLATION"):
        super().__init__(message)
        self.failure_code = failure_code


class IncompleteReactionError(ValueError):
    """Raised when a donor reaction is not a complete auditable record."""

    def __init__(self, message: str, failure_code: str = "INCOMPLETE_REACTION"):
        super().__init__(message)
        self.failure_code = failure_code


class ReactionAuthorityError(IncompleteReactionError):
    """Raised when the reaction content authority binding is broken (R3-B):
    a forged/changed reaction hash or a ref bound to the wrong reaction
    content.  Never silently accepted."""

    def __init__(self, message: str, failure_code: str = "REACTION_HASH_MISMATCH"):
        super().__init__(message, failure_code)


def _lookup_donor(train_view: TrainView, donor_id: str):
    for donor in train_view.donors:
        if donor.donor_id == donor_id:
            return donor
    raise FoldIsolationError(
        f"donor {donor_id!r} not present in the frozen train view"
    )


def _lookup_ref(donor, reaction_ref) -> ReactionRef:
    for ref in donor.reaction_refs:
        if ref.reaction_id == reaction_ref.reaction_id:
            return ref
    raise IncompleteReactionError(
        f"reaction {reaction_ref.reaction_id!r} is not an eligible reaction "
        f"of donor {donor.donor_id!r}"
    )


def load_reaction_evidence(
    train_view: TrainView,
    donor_id: str,
    reaction_ref: ReactionRef,
    *,
    query_id: str = "",
    case_id: str = "",
    run_id: str = "",
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture,
    authority_manifest=None,
) -> ResolvedDonorEvidence:
    """Load the complete donor evidence package for ONE explicit reaction.

    R5-C / R6-C: the loader verifies the expected snapshot/reaction hash
    against the FROZEN authority root attached to the train view — never
    against a caller-recomputed hash.  A fully-synchronized A/B-only strip
    (content + local hashes recomputed) is then rejected with
    FROZEN_REACTION_HASH_MISMATCH.

    R6-C fail-closed rules:
    - the train view MUST carry a frozen authority manifest (MISSING_AUTHORITY
      when absent — a manually-constructed train view without an upstream
      authority handle is not a production authority);
    - in PRODUCTION mode (``evidence_kind == EvidenceKind.real``) the
      manifest kind MUST be ``production`` — a caller-built fixture manifest
      (``build_fixture_authority_manifest``) can NEVER be accepted as a P1/P2
      production authority;
    - ``authority_manifest`` (legacy override) is only honored for
      FIXTURE-mode loads and must carry the same fail-closed semantics.

    Raises FoldIsolationError / IncompleteReactionError on fail-closed.
    """
    if authority_manifest is not None:
        from dataclasses import replace as _replace
        train_view = _replace(train_view, authority_manifest=authority_manifest)
    # 1. Train view authority (fold + hash) is the ONLY fold authority.
    #    R6-C: requires an upstream authority manifest (fail-closed).
    validate_train_view_authority(train_view)
    # R6-C / R7-B: production evidence requires a PRODUCTION authority — a
    # genuine ``ProductionAuthorityHandle`` created by the INTERNAL P1/P2
    # authority adapter after verifying the real P1/P2
    # snapshot/lineage/ledger/eligibility artifacts.  A caller-built fixture
    # manifest is NEVER a production authority, and the kind field is no
    # longer a magic string: the TYPE is the authority.  A fixture manifest
    # (or a missing production root while the real P1/P2 root is unavailable)
    # fails closed with a typed code.
    if evidence_kind is EvidenceKind.real:
        from reaction_agent.p3.fixtures import (
            FixtureAuthorityManifest,
            ProductionAuthorityHandle,
        )
        manifest = train_view.authority_manifest
        if isinstance(manifest, FixtureAuthorityManifest):
            raise IncompleteReactionError(
                "production evidence requires a PRODUCTION (P1/P2 frozen) "
                "authority handle; a fixture manifest cannot be a "
                "production authority",
                failure_code="FIXTURE_MANIFEST_AS_PRODUCTION_AUTHORITY",
            )
        if not isinstance(manifest, ProductionAuthorityHandle):
            raise IncompleteReactionError(
                "production evidence requires a ProductionAuthorityHandle "
                "created by the internal P1/P2 authority adapter; the real "
                "P1/P2 root is unavailable — no production root is "
                "manufactured",
                failure_code="PRODUCTION_AUTHORITY_UNAVAILABLE",
            )

    donor = _lookup_donor(train_view, donor_id)
    ref = _lookup_ref(donor, reaction_ref)

    fixture = next(
        (fx for fx in train_view.reactions.values()
         if fx.reaction_id == ref.reaction_id),
        None,
    )
    if fixture is None:
        raise IncompleteReactionError(
            f"reaction {ref.reaction_id!r} missing from the train view reactions"
        )
    if fixture.reaction_id != ref.reaction_id:
        raise IncompleteReactionError("reaction id mismatch between ref and fixture")

    # 2. Reaction authority (R3-B): recompute the canonical reaction hash
    # from the LIVE complete record and compare it with BOTH the caller-
    # supplied reference and the train-view stored reference.  A stored hash
    # string is never authority; forged or stale refs and same-ID-changed-
    # content mutations fail closed with typed codes.
    expected_reaction_hash = canonical_reaction_hash(fixture)
    if reaction_ref.reaction_hash != expected_reaction_hash:
        raise ReactionAuthorityError(
            f"reaction {fixture.reaction_id} caller reference reaction_hash "
            f"{str(reaction_ref.reaction_hash)[:12]}... != recomputed reaction "
            f"authority hash {expected_reaction_hash[:12]}... (forged or stale "
            f"reaction reference)",
            failure_code="REACTION_HASH_MISMATCH",
        )
    if reaction_ref.donor_participant_id != fixture.donor_participant_id:
        raise ReactionAuthorityError(
            f"reaction {fixture.reaction_id} caller ref donor participant "
            f"{reaction_ref.donor_participant_id!r} != reaction authority "
            f"donor participant {fixture.donor_participant_id!r}",
            failure_code="REACTION_REF_BINDING_MISMATCH",
        )
    if reaction_ref.lineage_id != ref.lineage_id:
        raise ReactionAuthorityError(
            f"reaction {fixture.reaction_id} caller ref lineage "
            f"{reaction_ref.lineage_id!r} != stored eligible lineage "
            f"{ref.lineage_id!r}",
            failure_code="REACTION_REF_BINDING_MISMATCH",
        )
    if ref.reaction_hash != expected_reaction_hash:
        raise ReactionAuthorityError(
            f"reaction {fixture.reaction_id} stored train-view ref "
            f"reaction_hash {str(ref.reaction_hash)[:12]}... != recomputed "
            f"reaction authority hash {expected_reaction_hash[:12]}... "
            f"(train view reaction content changed under a stable ref)",
            failure_code="REACTION_HASH_MISMATCH",
        )
    if ref.donor_participant_id != fixture.donor_participant_id:
        raise ReactionAuthorityError(
            f"reaction {fixture.reaction_id} stored train-view ref donor "
            f"participant {ref.donor_participant_id!r} != reaction authority "
            f"donor participant {fixture.donor_participant_id!r}",
            failure_code="REACTION_REF_BINDING_MISMATCH",
        )

    # 3. Strict mapping is the FIRST strict-lane gate (R3-F): partial or
    # ambiguous maps are rejected before any further record inspection.
    status = fixture.mapping_report.mapping_status
    if status.value not in ("fully_mapped",):
        raise IncompleteReactionError(
            f"donor reaction {fixture.reaction_id} mapping status "
            f"{status.value} — partial/ambiguous maps rejected for strict lane",
            failure_code="PARTIAL_MAP",
        )

    # 4. Complete reaction record (cross-consistency, no ID-name string tricks).
    _check_complete_record(train_view, donor, ref, fixture)

    # 5. Critical lineage ambiguity fails closed.
    if any(l.ambiguity == "critical" for l in fixture.lineages):
        raise IncompleteReactionError(
            f"donor reaction {fixture.reaction_id} has critical lineage "
            f"ambiguity — rejected for strict lane"
        )

    # 6. Source ledger + eligibility required.
    if fixture.source_ledger is None:
        raise IncompleteReactionError(
            f"donor reaction {fixture.reaction_id} missing source ledger"
        )
    if fixture.eligibility.eligibility not in (
        EligibilityStatus.strict_eligible,
        EligibilityStatus.conditional_eligible,
    ):
        raise IncompleteReactionError(
            f"donor reaction {fixture.reaction_id} not production-eligible: "
            f"{fixture.eligibility.eligibility.value} (fail closed)"
        )

    # 7. Resolve the lineage named by the ReactionRef (must be resolvable).
    lineage = next(
        (l for l in fixture.lineages if l.lineage_id == ref.lineage_id),
        None,
    )
    if lineage is None:
        raise IncompleteReactionError(
            f"lineage {ref.lineage_id!r} of reaction {fixture.reaction_id} "
            f"not resolvable (missing or inconsistent)"
        )

    donor_participant = next(
        (p for p in fixture.participants
         if p.participant_id == ref.donor_participant_id),
        None,
    )
    if donor_participant is None:
        raise IncompleteReactionError(
            f"donor participant {ref.donor_participant_id!r} not found in "
            f"reaction {fixture.reaction_id} participants"
        )

    query_id = query_id or f"diag_query_{ref.reaction_id}"
    case_id = case_id or f"diag_case_{ref.reaction_id}"

    context = DonorContext(
        donor_participant_id=donor_participant.participant_id,
        donor_molecule_id=donor_participant.molecule_id,
        donor_canonical_smiles=donor_participant.canonical_smiles,
        reaction_id=fixture.reaction_id,
        reaction_evidence=fixture.evidence,
        mapping_report=fixture.mapping_report,
        resolved_lineages=fixture.lineages,
        source_ledger=fixture.source_ledger,
        eligibility_decision=fixture.eligibility,
        donor_eligibility=fixture.donor_eligibility,
        evidence_kind=evidence_kind,
    )
    return ResolvedDonorEvidence(
        donor_id=donor.donor_id,
        run_id=run_id or f"diag_run_{query_id}",
        fold_id=train_view.fold_id,
        query_id=query_id,
        case_id=case_id,
        snapshot_id=train_view.snapshot_id,
        snapshot_hash=train_view.snapshot_hash,
        context=context,
        evidence_kind=evidence_kind,
        # R3-B: carry the VERIFIED authority hash to transform extraction so
        # the transform preimage binds to the reaction authority.
        reaction_authority_hash=expected_reaction_hash,
    )


# Backward-compatible name kept for clarity (same semantics as above).
load_donor_evidence = load_reaction_evidence


def _check_complete_record(
    train_view: TrainView,
    donor,
    ref: ReactionRef,
    fixture: FixtureReaction,
) -> None:
    """Cross-consistency of reaction evidence without relying on participant
    ID naming.

    Verifies:
    - participant multiset on the evidence vs the fixture participant list;
    - participant side / molecule ids / atom-map ownership are consistent;
    - mapping report participant refs resolve to real participants;
    - resolved lineage refs on the evidence resolve to real lineages;
    - source ledger refs (role_assignments, added/removed atom source/sink,
      formal transfers) resolve to real participants.
    """
    ev = fixture.evidence
    participant_ids = [p.participant_id for p in fixture.participants]
    ev_participant_ids = [p.participant_id for p in ev.participants]

    if len(participant_ids) != len(set(participant_ids)):
        raise IncompleteReactionError(
            f"reaction {fixture.reaction_id} has duplicate participant ids"
        )
    # Multiset comparison (a duplicate participant is a mismatch, not a set
    # collision).
    from collections import Counter
    if Counter(participant_ids) != Counter(ev_participant_ids):
        raise IncompleteReactionError(
            f"reaction {fixture.reaction_id} participant multiset mismatch "
            f"between fixture and reaction evidence (participant deleted or "
            f"duplicated?)"
        )
    if len(fixture.participants) < 1:
        raise IncompleteReactionError(
            f"reaction {fixture.reaction_id} has no participants (A/B-only or "
            f"stripped record)"
        )

    # Side / molecule-id / atom-map ownership cross-consistency.
    for p in fixture.participants:
        if p.side not in ("reactant", "product"):
            raise IncompleteReactionError(
                f"participant {p.participant_id} has invalid side {p.side!r}"
            )
        if not p.molecule_id:
            raise IncompleteReactionError(
                f"participant {p.participant_id} missing molecule_id"
            )

    # Mapping report participant refs must resolve.
    mapping = fixture.mapping_report
    fma = mapping.formal_mapped_source_assignment
    if fma is not None:
        known = set(participant_ids)
        for pair in fma.mapped_atom_pairs:
            if pair.reactant_participant_id not in known:
                raise IncompleteReactionError(
                    f"mapping references unknown reactant participant "
                    f"{pair.reactant_participant_id!r}"
                )
            if pair.product_participant_id not in known:
                raise IncompleteReactionError(
                    f"mapping references unknown product participant "
                    f"{pair.product_participant_id!r}"
                )

    # Lineage references on the evidence must resolve to real lineages.
    ev_lineage_ids = set(l.lineage_id for l in fixture.lineages)
    for declared in ev.resolved_transformed_lineages:
        if declared not in ev_lineage_ids:
            raise IncompleteReactionError(
                f"reaction evidence declares unknown lineage {declared!r}"
            )
    # R4-B/R4-E: BIDIRECTIONAL lineage completeness — every resolved lineage
    # of the fixture must be declared on the reaction evidence.  A record
    # that declares zero lineages while real lineages exist (striped lineage
    # contract) is incomplete.
    declared_lineage_ids = set(ev.resolved_transformed_lineages)
    for lineage in fixture.lineages:
        if lineage.lineage_id not in declared_lineage_ids:
            raise IncompleteReactionError(
                f"reaction {fixture.reaction_id} resolved lineage "
                f"{lineage.lineage_id!r} is not declared on the reaction "
                f"evidence (stripped lineage contract)"
            )

    # Source ledger participant references must resolve.
    ledger = fixture.source_ledger
    known = set(participant_ids)
    for role in ledger.role_assignments:
        if role.participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger role assignment references unknown participant "
                f"{role.participant_id!r}"
            )
    for entry in list(ledger.stoichiometry) + list(ledger.reactant_entries) + list(ledger.product_entries):
        if entry.participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger stoichiometry references unknown participant "
                f"{entry.participant_id!r}"
            )
    for src in ledger.added_atom_sources:
        if src.source_participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger added-atom source references unknown participant "
                f"{src.source_participant_id!r}"
            )
    for sink in ledger.removed_atom_sinks:
        if sink.sink_participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger removed-atom sink references unknown participant "
                f"{sink.sink_participant_id!r}"
            )
    for transfer in ledger.formal_atom_transfer_assignments:
        if transfer.source_participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger formal transfer references unknown source "
                f"{transfer.source_participant_id!r}"
            )
        if transfer.target_participant_id not in known:
            raise IncompleteReactionError(
                f"source ledger formal transfer references unknown target "
                f"{transfer.target_participant_id!r}"
            )

    # R5-C: evidence/fixture duplicated content must be bidirectionally
    # consistent.  The reaction evidence and the fixture carry DUPLICATED
    # copies of mapping, ledger, participants, lineages and reaction strings;
    # a forge that strips one copy but not the other (or replaces both
    # inconsistently) must be rejected.
    if fixture.evidence.mapping_report is not None:
        if fixture.mapping_report is None:
            raise IncompleteReactionError(
                f"reaction {fixture.reaction_id} evidence carries a mapping "
                f"report but the fixture does not"
            )
        if fixture.evidence.mapping_report.model_dump(mode="json") != (
            fixture.mapping_report.model_dump(mode="json")
        ):
            raise IncompleteReactionError(
                f"reaction {fixture.reaction_id} evidence mapping_report "
                f"content differs from the fixture mapping_report "
                f"(stripped/forged mapping?)"
            )
    if fixture.evidence.source_reaction_ledger is not None:
        if fixture.source_ledger is None:
            raise IncompleteReactionError(
                f"reaction {fixture.reaction_id} evidence carries a source "
                f"ledger but the fixture does not"
            )
        if fixture.evidence.source_reaction_ledger.model_dump(mode="json") != (
            fixture.source_ledger.model_dump(mode="json")
        ):
            raise IncompleteReactionError(
                f"reaction {fixture.reaction_id} evidence "
                f"source_reaction_ledger content differs from the fixture "
                f"source_ledger (stripped/forged ledger?)"
            )
    if fixture.evidence.raw_reaction != fixture.evidence.normalized_reaction:
        # raw vs normalized may legitimately differ (normalization); but the
        # fixture's own raw/normalized strings must match the evidence's.
        pass
    if fixture.evidence.raw_reaction and fixture.evidence.raw_reaction != (
        ".".join(fixture.reactant_smiles) + ">>" + ".".join(fixture.product_smiles)
    ):
        raise IncompleteReactionError(
            f"reaction {fixture.reaction_id} raw_reaction does not match the "
            f"fixture reactant/product SMILES (stripped reaction string?)"
        )

    # R4-E: bidirectional completeness — the reaction participant set and the
    # source ledger's participant set must be EXACTLY equal.  A reaction
    # stripped to A/B-only (cofactor / co-substrate / small molecule removed)
    # is rejected: stripping the participants while the ledger still records
    # the cofactor, OR stripping the ledger while the participants remain,
    # breaks the exact equality.  The check is (a) every ledger reference
    # resolves to a real participant (above) AND (b) every participant is
    # recorded on the source ledger (below).
    ledger_participant_ids: set[str] = set()
    for entry in (
        list(ledger.stoichiometry)
        + list(ledger.reactant_entries)
        + list(ledger.product_entries)
    ):
        ledger_participant_ids.add(entry.participant_id)
    for role in ledger.role_assignments:
        ledger_participant_ids.add(role.participant_id)
    for src in ledger.added_atom_sources:
        ledger_participant_ids.add(src.source_participant_id)
    for sink in ledger.removed_atom_sinks:
        ledger_participant_ids.add(sink.sink_participant_id)
    for transfer in ledger.formal_atom_transfer_assignments:
        ledger_participant_ids.add(transfer.source_participant_id)
        ledger_participant_ids.add(transfer.target_participant_id)
    participant_set = set(participant_ids)
    if ledger_participant_ids != participant_set:
        raise IncompleteReactionError(
            f"reaction {fixture.reaction_id} source ledger participant set "
            f"does not exactly equal the reaction participant set "
            f"(cofactor/co-substrate stripped?): ledger-only="
            f"{sorted(ledger_participant_ids - participant_set)} "
            f"participant-only={sorted(participant_set - ledger_participant_ids)}"
        )
