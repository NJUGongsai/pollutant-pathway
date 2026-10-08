"""Assert R6 observed storage behavior, NOT expectations after a repair.

Reads saved synthetic probe output only; does not import the repository,
run probes, create databases, or modify existing evidence.
"""
from pathlib import Path
import json
import sys

EXPECTED_HEAD = "6d9020130a481866ce2f3b79933907a33d8cfc9e"
HERE = Path(__file__).resolve().parent
CANDIDATES = (
    HERE / "r6_storage_boundary_probe.output.jsonl",
    HERE / "r6_storage_boundary_probe.output.jsonl",
)
if len(sys.argv) > 2:
    raise SystemExit("usage: storage_assert_observed.py [saved_output.jsonl]")
output = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else next(
    (p for p in CANDIDATES if p.is_file()), None)
if output is None:
    raise SystemExit("saved R6 storage output not found next to this script")
rows = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
assert len(rows) == 18, ("expected 17 cases + 1 metadata", len(rows))
metadata = [r for r in rows if r.get("type") == "metadata"]
assert len(metadata) == 1, "expected exactly one metadata record"
assert metadata[0]["actual_head"] == EXPECTED_HEAD
assert metadata[0]["expected_head"] == EXPECTED_HEAD
assert metadata[0]["bytecode_disabled"] is True
cases = [r for r in rows if "probe" in r]
assert len(cases) == 17
by_name = {r["probe"]: r for r in cases}
assert len(by_name) == 17, "duplicate case names"
expected_names = {
    "existing_state_first_valid",
    "existing_state_first_cn_identity",
    "existing_state_first_schema_version",
    "existing_state_first_state_id",
    "existing_appearance_bad_hash_first",
    "existing_hypothesis_first_valid",
    "existing_hypothesis_first_assumptions",
    "existing_hypothesis_first_inner_id",
    "existing_hypothesis_first_schema",
    "existing_hypothesis_first_participant_entry",
    "existing_hypothesis_self_consistent_bad_participant",
    "ambiguous_first_without_explicit_state_rejected",
    "ambiguous_first_explicit_state_control",
    "multi_occurrence_manifest_normal",
    "multi_occurrence_manifest_remove_manifest_A_only",
    "multi_occurrence_manifest_remove_row_A_only",
    "multi_occurrence_manifest_remove_manifest_and_row_A",
}
assert set(by_name) == expected_names, ("case-name mismatch", set(by_name) ^ expected_names)


def created(stage):
    assert "error" not in stage, stage
    assert stage["result"]["created"] is True, stage
    assert stage["event_present"] is True, stage
    assert stage["counts_preserved"] is False, stage
    before, after = stage["counts_before"], stage["counts_after"]
    for table in ("events", "report_projections", "expansion_plans"):
        assert after[table] == before[table] + 1, (table, stage)


def idempotent(stage):
    assert "error" not in stage, stage
    assert stage["result"]["created"] is False, stage
    assert stage["counts_preserved"] is True, stage
    assert stage["counts_before"] == stage["counts_after"], stage
    assert stage["event_present"] is True, stage


def rejected(stage, kind, error="Ppv1LedgerCorrupt", event_present=False):
    assert "result" not in stage, stage
    assert stage["error"] == error, stage
    assert stage["detail"]["kind"] == kind, stage
    assert stage["counts_preserved"] is True, stage
    assert stage["counts_before"] == stage["counts_after"], stage
    assert stage["event_present"] is event_present, stage


# Observe the four current gaps: first submit writes, replay detects damage.
for name, kind in (
    ("existing_state_first_cn_identity", "state_row_corrupt"),
    ("existing_state_first_schema_version", "state_schema_corrupt"),
    ("existing_state_first_state_id", "state_inner_id_corrupt"),
    ("existing_appearance_bad_hash_first", "appearance_hash_corrupt"),
):
    case = by_name[name]
    created(case["first"])
    rejected(case["replay"], kind, event_present=True)

# Legal pre-stored state/hypothesis and explicit ambiguous-source controls.
for name in (
    "existing_state_first_valid",
    "existing_hypothesis_first_valid",
    "ambiguous_first_explicit_state_control",
):
    created(by_name[name]["first"])
    idempotent(by_name[name]["replay"])

# The existing hypothesis checks are fixed: reject before any new writes.
for name, kind in (
    ("existing_hypothesis_first_assumptions", "hypothesis_payload_id_corrupt"),
    ("existing_hypothesis_first_inner_id", "hypothesis_id_corrupt"),
    ("existing_hypothesis_first_schema", "hypothesis_schema_corrupt"),
    # Entry mutation changes the content ID, so this earlier check is expected.
    ("existing_hypothesis_first_participant_entry", "hypothesis_payload_id_corrupt"),
):
    rejected(by_name[name]["first"], kind)
case = by_name["existing_hypothesis_self_consistent_bad_participant"]
assert case["row_id"] == case["inner_id"] == case["rederived_payload_id"]
rejected(case["first"], "hypothesis_participants_corrupt")
assert case["first"]["detail"]["reason"]["kind"] == "participant_entry_id_mismatch"
case = by_name["ambiguous_first_without_explicit_state_rejected"]
rejected(case["first"], "appearance_source_ambiguous", "Ppv1SubmitContractError")
assert len(case["first"]["detail"]["candidate_appearance_hashes"]) == 2

# Distinct occurrences of one state are accepted, and their initial manifest
# is complete. Current removal of one manifest occurrence still escapes.
for mode in (
    "normal", "remove_manifest_A_only", "remove_row_A_only",
    "remove_manifest_and_row_A",
):
    case = by_name["multi_occurrence_manifest_" + mode]
    created(case["first"])
    idempotent(case["normal_replay"])
    assert case["product_entries_count"] == 2
    original = case["original_manifest"]
    assert len(original) == 3
    assert len({(e["state_id"], e["appearance_hash"]) for e in original}) == 3
    assert len({e["state_id"] for e in original}) == 2
    refs = case["distinct_source_refs"]
    assert len(refs) == 2
    assert {p["structure_smiles_raw"] for p in refs} == {"CC=O", "O=CC"}
    assert {json.dumps(p["source_refs"], sort_keys=True) for p in refs} == {
        json.dumps([{"record": "prod-A"}], sort_keys=True),
        json.dumps([{"record": "prod-B"}], sort_keys=True),
    }
    saved = case["saved_manifest"]
    remaining = case["remaining_product_appearances"]
    if mode in ("remove_manifest_A_only", "remove_manifest_and_row_A"):
        assert len(saved) == 2
        assert {e["state_id"] for e in saved} == {e["state_id"] for e in original}
        assert all(e["appearance_hash"] != case["removed_A_hash"] for e in saved)
        idempotent(case["replay"])
    elif mode == "remove_row_A_only":
        assert saved == original
        rejected(case["replay"], "event_appearance_manifest_entry_missing", event_present=True)
        assert case["replay"]["detail"]["appearance_hash"] == case["removed_A_hash"]
    else:
        assert saved == original
        idempotent(case["replay"])
    if mode in ("remove_row_A_only", "remove_manifest_and_row_A"):
        assert len(remaining) == 1
        assert remaining[0]["source_refs"] == [{"record": "prod-B"}]
    else:
        assert len(remaining) == 2

print("R6 OBSERVED behavior verified: 17 cases + 1 metadata; this is not a post-repair acceptance test.")
