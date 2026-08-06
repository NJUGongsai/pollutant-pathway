"""P1 Preflight contract tests (Task 0).

Tests the real-resource inventory per chatgpt_p1_train.md §6.

TDD: written RED first, implementation in scripts/p1_preflight.py makes it GREEN.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import pytest

DEMOV2_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(DEMOV2_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture(scope="module")
def pf():
    """Import the preflight module (must be implemented to pass)."""
    return importlib.import_module("p1_preflight")


# ============================================================
# runtime_inventory
# ============================================================

REQUIRED_RUNTIME_KEYS = {
    "python_version", "platform", "working_directory",
    "pydantic_version", "pytest_version",
    "rdkit", "numpy", "networkx", "scipy", "mapper_backend",
}


class TestRuntimeInventory:
    def test_returns_dict_with_required_keys(self, pf):
        rt = pf.runtime_inventory()
        assert isinstance(rt, dict)
        missing = REQUIRED_RUNTIME_KEYS - set(rt.keys())
        assert not missing, f"missing keys: {missing}"

    def test_python_version_is_string(self, pf):
        rt = pf.runtime_inventory()
        assert isinstance(rt["python_version"], str) and rt["python_version"]

    def test_pydantic_version_present(self, pf):
        rt = pf.runtime_inventory()
        # P0 requires pydantic; must be a version string
        assert rt["pydantic_version"] is not None
        assert isinstance(rt["pydantic_version"], str)

    def test_pytest_version_present(self, pf):
        rt = pf.runtime_inventory()
        assert rt["pytest_version"] is not None
        assert isinstance(rt["pytest_version"], str)

    def test_mapper_backend_matches_live_rdkit_state(self, pf):
        rt = pf.runtime_inventory()
        if rt["rdkit"] is None:
            assert rt["mapper_backend"] is None
        else:
            assert "rdkit" in rt["mapper_backend"]
            assert "mcs" in rt["mapper_backend"]

    def test_working_directory_is_demov2(self, pf):
        rt = pf.runtime_inventory()
        assert rt["working_directory"] == DEMOV2_ROOT

    def test_chem_deps_are_none_or_version_string(self, pf):
        rt = pf.runtime_inventory()
        for dep in ("rdkit", "numpy", "networkx", "scipy"):
            v = rt[dep]
            assert v is None or isinstance(v, str), f"{dep}={v!r}"


# ============================================================
# legacy_inventory
# ============================================================

EXPECTED_LEGACY_PATHS = {
    "../benchmark/canonical_identity.py",
    "../benchmark",
    "../core",
}


class TestLegacyInventory:
    def test_returns_dict_with_legacy_sources_key(self, pf):
        lg = pf.legacy_inventory()
        assert isinstance(lg, dict)
        assert "legacy_sources" in lg
        assert isinstance(lg["legacy_sources"], list)

    def test_each_item_has_required_fields(self, pf):
        lg = pf.legacy_inventory()
        for item in lg["legacy_sources"]:
            for field in ("relative_path", "absolute_path", "exists", "sha256", "size"):
                assert field in item, f"item missing {field}: {item}"

    def test_expected_legacy_paths_present(self, pf):
        lg = pf.legacy_inventory()
        paths = {item["relative_path"] for item in lg["legacy_sources"]}
        missing = EXPECTED_LEGACY_PATHS - paths
        assert not missing, f"missing legacy paths: {missing}"

    def test_canonical_identity_file_exists_with_sha256(self, pf):
        lg = pf.legacy_inventory()
        for item in lg["legacy_sources"]:
            if item["relative_path"] == "../benchmark/canonical_identity.py":
                assert item["exists"] is True, "canonical_identity.py must exist (read-only legacy)"
                assert item["sha256"] is not None, "file must have sha256"
                assert isinstance(item["sha256"], str) and len(item["sha256"]) == 64
                return
        pytest.fail("canonical_identity.py entry not found")


# ============================================================
# real_source_inventory
# ============================================================


class TestRealSourceInventory:
    def test_returns_dict_with_required_keys(self, pf):
        src = pf.real_source_inventory()
        assert isinstance(src, dict)
        for k in ("candidate_env_keys_present", "real_reaction_source_found", "data_root_scan_allowed"):
            assert k in src, f"missing {k}"

    def test_real_reaction_source_found_matches_declared_assets(self, pf):
        src = pf.real_source_inventory()
        assert src["real_reaction_source_found"] is True
        assert src["reaction_count"] == 3601
        assert src["reaction_center_overlap_count"] == src["reaction_count"]

    def test_data_root_scan_not_allowed(self, pf):
        src = pf.real_source_inventory()
        # Must NOT scan entire home dir
        assert src["data_root_scan_allowed"] is False

    def test_env_keys_only_records_key_names_not_values(self, pf):
        src = pf.real_source_inventory()
        keys = src["candidate_env_keys_present"]
        assert isinstance(keys, list)
        # every entry must be a string key name, never a value
        for k in keys:
            assert isinstance(k, str)


# ============================================================
# case_inventory
# ============================================================

EXPECTED_PROLINE_REACTION = (
    "2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2"
)
EXPECTED_FORBIDDEN_LINEAGE = "2-oxoglutarate -> hydroxyproline"


class TestCaseInventory:
    def test_returns_dict_with_proline_2og(self, pf):
        case = pf.case_inventory()
        assert isinstance(case, dict)
        assert "proline_2og" in case

    def test_proline_reaction_string_exact(self, pf):
        case = pf.case_inventory()
        assert case["proline_2og"]["reaction"] == EXPECTED_PROLINE_REACTION

    def test_expected_lineages_present(self, pf):
        case = pf.case_inventory()
        lineages = case["proline_2og"]["expected_lineages"]
        assert isinstance(lineages, list)
        assert "proline -> hydroxyproline" in lineages
        assert "2-oxoglutarate -> succinate" in lineages

    def test_forbidden_lineage_exact(self, pf):
        case = pf.case_inventory()
        assert case["proline_2og"]["forbidden_lineage"] == EXPECTED_FORBIDDEN_LINEAGE

    def test_source_record_found_comes_from_structure_audit(self, pf):
        case = pf.case_inventory()
        assert case["proline_2og"]["source_record_found"] is True
        assert case["proline_2og"]["structure_match_count"] > 0
        assert case["proline_2og"]["source_ids"]


# ============================================================
# evaluate_stop_condition — three branches
# ============================================================


class TestEvaluateStopCondition:
    def test_go_when_all_present(self, pf):
        rt = {"rdkit": "2024.3.5"}
        src = {"real_reaction_source_found": "rhea"}
        case = {"proline_2og": {"source_record_found": "rhea:12345"}}
        status, reasons = pf.evaluate_stop_condition(rt, src, case)
        assert status == "GO"
        assert reasons == []

    def test_partial_when_only_rdkit_absent(self, pf):
        rt = {"rdkit": None}
        src = {"real_reaction_source_found": "rhea"}
        case = {"proline_2og": {"source_record_found": "rhea:12345"}}
        status, reasons = pf.evaluate_stop_condition(rt, src, case)
        assert status == "PARTIAL"
        assert "rdkit_absent" in reasons
        assert "real_reaction_source_not_confirmed" not in reasons
        assert "required_case_missing" not in reasons

    def test_blocked_when_source_missing(self, pf):
        rt = {"rdkit": "2024.3.5"}
        src = {"real_reaction_source_found": None}
        case = {"proline_2og": {"source_record_found": "rhea:12345"}}
        status, reasons = pf.evaluate_stop_condition(rt, src, case)
        assert status == "BLOCKED"
        assert "real_reaction_source_not_confirmed" in reasons

    def test_blocked_when_case_missing(self, pf):
        rt = {"rdkit": "2024.3.5"}
        src = {"real_reaction_source_found": "rhea"}
        case = {"proline_2og": {"source_record_found": None}}
        status, reasons = pf.evaluate_stop_condition(rt, src, case)
        assert status == "BLOCKED"
        assert "required_case_missing" in reasons

    def test_blocked_when_all_three_missing(self, pf):
        rt = {"rdkit": None}
        src = {"real_reaction_source_found": None}
        case = {"proline_2og": {"source_record_found": None}}
        status, reasons = pf.evaluate_stop_condition(rt, src, case)
        assert status == "BLOCKED"
        assert "rdkit_absent" in reasons
        assert "real_reaction_source_not_confirmed" in reasons
        assert "required_case_missing" in reasons


# ============================================================
# main — writes P1_PREFLIGHT.json, exit code contract
# ============================================================


class TestMain:
    def test_main_writes_json_with_required_shape(self, pf):
        # main() writes to reports/p1/P1_PREFLIGHT.json relative to cwd
        # Run from DEMOV2_ROOT so the path resolves correctly
        original = os.getcwd()
        try:
            os.chdir(DEMOV2_ROOT)
            exit_code = pf.main()
        finally:
            os.chdir(original)

        json_path = os.path.join(DEMOV2_ROOT, "reports", "p1", "P1_PREFLIGHT.json")
        assert os.path.isfile(json_path), "P1_PREFLIGHT.json not written"
        with open(json_path) as f:
            report = json.load(f)
        for k in ("status", "blockers", "runtime", "legacy", "real_source", "case"):
            assert k in report, f"report missing {k}"
        assert report["status"] in ("GO", "PARTIAL", "BLOCKED")
        assert isinstance(report["blockers"], list)
        # exit code contract: 0 only if GO
        if report["status"] == "GO":
            assert exit_code == 0
        else:
            assert exit_code == 1
