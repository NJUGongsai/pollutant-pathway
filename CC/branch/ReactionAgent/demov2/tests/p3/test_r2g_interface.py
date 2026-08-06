"""R2-G P3->P4 frozen interface namespace + manifest tests."""
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.manifest import (
    build_interface_manifest,
    manifest_schema_hash,
    model_fields_of,
)
from reaction_agent.p3.schemas import (
    CapabilityStatus,
    CandidateTrace,
    ConditionedSite,
    KernelFailure,
    KernelRunManifest,
    NormalizedQuery,
    ResolvedDonorEvidence,
    StrictCandidate,
    StrictTransformation,
)

_NAMESPACE = {"run_id", "case_id", "query_id", "fold_id", "snapshot_id", "snapshot_hash"}


def _collect_nested_namespaces(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "run_id" and isinstance(v, str):
                acc.append(obj)
            _collect_nested_namespaces(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_nested_namespaces(v, acc)


def test_every_p3_output_has_full_run_namespace():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3",
                   mode="fixture")
    # NormalizedQuery.
    assert _NAMESPACE <= set(r.normalized_query.model_fields)
    # Candidates (StrictCandidate).
    for candidate in r.candidates:
        assert _NAMESPACE <= set(candidate.model_fields)
        for path in candidate.candidate_evidence_paths:
            # per-path linkage fields (R2-F); run namespace lives on the parent.
            assert "donor_id" in path.model_fields
            assert "reaction_id" in path.model_fields
            assert "lineage_id" in path.model_fields
            assert "source_ledger_id" in path.model_fields
    # Trace namespace already required.
    assert _NAMESPACE <= set(r.trace.model_fields)
    # Schema-level: every interface model carries the run namespace.
    for cls in (
        NormalizedQuery, ResolvedDonorEvidence, StrictTransformation,
        ConditionedSite, StrictCandidate, CandidateTrace,
    ):
        fields = set(model_fields_of(cls))
        missing = _NAMESPACE - fields
        assert not missing, f"{cls.__name__} missing namespace fields: {sorted(missing)}"


def test_cross_object_run_namespace_consistency():
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3",
                   mode="fixture")
    ns = (r.manifest.run_id, r.manifest.case_id, r.manifest.query_id,
          r.manifest.fold_id)
    # NormalizedQuery namespace == run manifest namespace.
    q = r.normalized_query
    assert (q.run_id, q.case_id, q.query_id, q.fold_id) == ns
    # Candidates namespace == run manifest namespace.
    for c in r.candidates:
        assert (c.run_id, c.case_id, c.query_id, c.fold_id) == ns
        for path in c.candidate_evidence_paths:
            assert path.generation_report is not None


def test_interface_manifest_matches_model_fields():
    manifest = build_interface_manifest()
    for name, cls in (
        ("KernelRunManifest", KernelRunManifest),
        ("NormalizedQuery", NormalizedQuery),
        ("ResolvedDonorEvidence", ResolvedDonorEvidence),
        ("StrictTransformation", StrictTransformation),
        ("ConditionedSite", ConditionedSite),
        ("StrictCandidate", StrictCandidate),
        ("CandidateTrace", CandidateTrace),
        ("KernelFailure", KernelFailure),
        ("CapabilityStatus", CapabilityStatus),
    ):
        entry = manifest["interfaces"][name]
        assert entry["fields"] == model_fields_of(cls), (
            f"manifest fields for {name} drifted from the live model"
        )


def test_interface_schema_hash_recomputable():
    manifest = build_interface_manifest()
    h1 = manifest_schema_hash(manifest)
    manifest2 = build_interface_manifest()
    assert h1 == manifest_schema_hash(manifest2)
    # A schema drift (e.g. adding a field) must change the hash.
    manifest2["interfaces"]["NormalizedQuery"]["fields"] += ["bogus_new_field"]
    assert h1 != manifest_schema_hash(manifest2)


def test_p4_can_deserialize_without_p3_mutable_objects():
    # P4 consumes only the serialized P3 interface objects (JSON).  It must
    # not need to import P3 internal mutable objects.
    r = run_kernel(input_smiles="CCCCCCCCO", case_id="c1", fold_id="fold_fx_p3",
                   mode="fixture")
    dumped = r.model_dump(mode="json")
    # Round-trip through plain dicts (what P4 would see) — no P3 internals.
    assert "candidates" in dumped
    for candidate in dumped["candidates"]:
        assert "candidate_id" in candidate
        assert "candidate_evidence_paths" in candidate
        assert "run_id" in candidate
        assert "case_id" in candidate
        assert "query_id" in candidate
        assert "fold_id" in candidate
