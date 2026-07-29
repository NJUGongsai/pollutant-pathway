import pytest
from reaction_agent.config import BuildConfig, get_build_info

def test_explicit_snapshot_path_required():
    with pytest.raises(Exception):
        BuildConfig(input_source="x", output_snapshot_root="snap")  # 缺 mapper_backend 等

def test_unknown_config_field_rejected():
    with pytest.raises(Exception):
        BuildConfig(input_source="x", output_snapshot_root="snap",
                    mapper_backend="fake", random_seed=42, timeout=300,
                    strict_mode=True, normalization_version="1",
                    role_policy_version="1", lineage_resolver_version="1",
                    ledger_version="1", eligibility_policy_version="1",
                    mapper_version="1", bogus_field="nope")

def test_seed_required_and_stable():
    c = BuildConfig(input_source="in", output_snapshot_root="out",
                    mapper_backend="fake", mapper_version="1",
                    normalization_version="1", role_policy_version="1",
                    lineage_resolver_version="1", ledger_version="1",
                    eligibility_policy_version="1", random_seed=42,
                    timeout=300, strict_mode=True)
    assert c.random_seed == 42

def test_deterministic_config_serialization():
    c1 = BuildConfig(input_source="in", output_snapshot_root="out",
                     mapper_backend="fake", mapper_version="1",
                     normalization_version="1", role_policy_version="1",
                     lineage_resolver_version="1", ledger_version="1",
                     eligibility_policy_version="1", random_seed=42,
                     timeout=300, strict_mode=True)
    s1 = c1.canonical_json()
    c2 = BuildConfig(**{**c1.model_dump()})
    assert c2.canonical_json() == s1

def test_get_build_info_deterministic():
    info = get_build_info()
    assert info.package_version
    assert info.schema_version
    assert info.python_version

from reaction_agent.provenance import assert_no_legacy_write, SourceRecordProvenance

def test_legacy_write_refused():
    with pytest.raises(PermissionError):
        assert_no_legacy_write("../benchmark/canonical_identity.py")

def test_demov2_write_allowed():
    assert_no_legacy_write("reports/p1/x.json")  # 不 raise

def test_provenance_required_fields():
    with pytest.raises(Exception):
        SourceRecordProvenance(source_name="rhea")  # 缺其余必填

def test_provenance_no_unknown_silent_fill():
    # 不得静默把 unknown 填进 strict
    p = SourceRecordProvenance(source_name="rhea", source_version="1",
                               source_record_id="r1", source_file_hash="h",
                               raw_record_hash="h", normalizer_version="1",
                               created_by_build_id="b1")
    assert p.source_record_id == "r1"

# -- L2 security-review 回归: no-legacy-write 绕过向量 --

@pytest.mark.parametrize("bypass", [
    "../benchmark/../benchmark/canonical_identity.py",  # 路径穿越归一化
    "..//benchmark/canonical_identity.py",              # 双斜杠
    "../core/x.json",                                    # core 目录
    "../reports/p0/anything.json",                       # P0 报告区
])
def test_legacy_write_bypass_vectors_refused(bypass):
    with pytest.raises(PermissionError):
        assert_no_legacy_write(bypass)

def test_legacy_write_case_variant_refused():
    # macOS APFS 不区分大小写: ../Benchmark 应同样被拒 (H2)
    with pytest.raises(PermissionError):
        assert_no_legacy_write("../Benchmark/canonical_identity.py")

def test_legacy_write_substring_false_positive_allowed():
    # 合法 P1 路径含 "benchmark" 子串不应被误拒 (M3)
    assert_no_legacy_write("reports/p1/benchmark_comparison.json")  # 不 raise

def test_legacy_write_demov2_reports_p1_allowed():
    # demov2 内的 reports/p1 路径合法 (不是 ../reports/p0)
    assert_no_legacy_write("reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md")  # 不 raise

