import os
import importlib.metadata
import pytest
from reaction_agent.config import BuildConfig, get_build_info
from reaction_agent.provenance import (
    assert_no_legacy_write,
    SourceRecordProvenance,
    _PROJECT_ROOT,
)

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

# -- Fix Round 1: IMPORTANT-1 guard 返回解析后绝对路径契约 --

def test_legacy_write_returns_resolved_absolute_path():
    # 合法路径：guard 必须返回解析后的绝对路径供调用方实际写入 (IMPORTANT-1)。
    # 调用方必须用该返回值写入——这样 guard 的路径解释与实际写入路径一致。
    resolved = assert_no_legacy_write("reports/p1/x.json")  # 不 raise
    assert os.path.isabs(resolved)
    expected = os.path.realpath(os.path.join(_PROJECT_ROOT, "reports", "p1", "x.json"))
    assert resolved == expected

def test_legacy_write_cwd_relative_returns_resolved_path():
    # `benchmark/x` (无 `../`，纯 CWD 相对) 是 IMPORTANT-1 的核心绕过向量：
    # 若调用方 CWD 在 parent，open("benchmark/x") 会写入 legacy ../benchmark/x。
    # Guard 闭合方式：将相对路径基于项目根 demov2/ 解析，返回解析后的绝对路径；
    # 调用方必须用返回值写入。此处验证 guard 的契约边界——
    #   (1) 不 raise（demov2/benchmark/x 不是 legacy）
    #   (2) 返回的是项目根下的绝对路径，而非 CWD 相对路径
    resolved = assert_no_legacy_write("benchmark/x")  # 不 raise
    assert os.path.isabs(resolved)
    # 解析到项目根下 (demov2/benchmark/x)，而非 legacy (../benchmark/x = parent/benchmark/x)
    expected = os.path.realpath(os.path.join(_PROJECT_ROOT, "benchmark", "x"))
    assert resolved == expected
    # 双重确认：返回路径不在 legacy 目录下（parent 的 benchmark）
    legacy_parent_benchmark = os.path.realpath(
        os.path.join(_PROJECT_ROOT, "..", "benchmark")
    )
    assert not (resolved == legacy_parent_benchmark
                or resolved.startswith(legacy_parent_benchmark + os.sep))

# -- Fix Round 1: MINOR-2 package_version 单源化 --

def test_package_version_sourced_from_metadata():
    # package_version 必须单源化自 importlib.metadata (MINOR-2)，不得硬编码。
    # metadata 缺失时 fallback "0.0.0"。
    info = get_build_info()
    try:
        expected = importlib.metadata.version("reaction-analogy-agent")
    except importlib.metadata.PackageNotFoundError:
        expected = "0.0.0"
    assert info.package_version == expected


