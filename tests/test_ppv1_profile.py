"""S0 profile 注册与新旧身份分开的测试(规则级夹具;无金标/无付费实验)。

覆盖:
- profile 常量与身份块(build_profile_identity_block 全版本/开关校验);
- code_identity 分集:legacy 排除 pollutant/、pollutant 含全树;
- build_run_identity 的 profile 块与 legacy 缺省行为;
- check_resume_identity:profile 差异拒绝、v1 旧身份缺 profile 字段按
  legacy 兼容读取;
- runner:pollutant 执行流未交付显式拒绝(不建目录)、未知 profile 拒绝;
- CLI --profile 参数存在且合法值集正确。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant import profile as ppv1_profile  # noqa: E402
from pathway_v43.storage import run_identity as ri  # noqa: E402


# ---------------------------------------------------------------- 常量与校验


def test_profile_names_registry() -> None:
    assert ri.PROFILE_LEGACY_V43 == "legacy_v43"
    assert ri.PROFILE_POLLUTANT_PATHWAY_V1 == "pollutant_pathway_v1"
    assert ri.KNOWN_PROFILES == frozenset(
        {"legacy_v43", "pollutant_pathway_v1"})
    assert ppv1_profile.PPV1_PROFILE_NAME == ri.PROFILE_POLLUTANT_PATHWAY_V1


def test_identity_schema_version_bumped() -> None:
    # v2:profile 块进入身份;v1 旧身份在读取端按 legacy 兼容
    assert ri.IDENTITY_SCHEMA_VERSION == "v43-identity-2"


def test_ppv1_identity_block_contract_versions() -> None:
    block = ri and ppv1_profile.build_profile_identity_block()
    assert block["name"] == "pollutant_pathway_v1"
    # v16(S4b):正式文件导出 + v3 有损投影
    # (native-export-1 / native-export-policy-1 / v3-projection-1;
    # endpoint-1 / endpoint-policy-1 / native-result-1 沿 S4a)
    assert block["schema_version"] == "ppv1-profile-16"
    contracts = block["contracts"]
    for key, prefix in (
        ("chemstate", "ppv1-chemstate-"),
        ("hypothesis", "ppv1-hypothesis-"),
        ("event", "ppv1-event-"),
        ("store", "ppv1-store-"),
        ("context", "ppv1-context-"),
        ("dependency", "ppv1-dependency-"),
        ("provenance", "ppv1-provenance-"),
        ("substrate_profile", "ppv1-substrate-profile-"),
        ("audit", "ppv1-audit-"),
        ("admission_policy", "ppv1-admission-"),
        ("donor_diagnostic", "ppv1-donor-diagnostic-"),
        ("pool_audit", "ppv1-pool-audit-"),
        ("pool_order", "ppv1-pool-order-"),
        ("input_preview", "ppv1-input-preview-"),
        ("condition_assessment", "ppv1-condition-assessment-"),
        ("search", "ppv1-search-"),
    ):
        assert contracts[key].startswith(prefix), key
    assert contracts["search"] == "ppv1-search-6"  # S3b r2 调度恢复闭合(r6)
    assert contracts["format_feedback"] == "ppv1-format-feedback-1"
    assert contracts["gate_mapper"] == "ppv1-gate-mapper-3"
    assert contracts["legacy_gate_ref"] == "frozen_hit60_gate"


def test_ppv1_identity_block_default_switches() -> None:
    block = ppv1_profile.build_profile_identity_block()
    assert block["input_preview_policy"] == "off"
    assert block["chemical_reproposal"] == "off"
    assert block["search_intent"] == "exploration"
    # S3a:search-limits 由 -2-proposed 草案升为实际可执行版本 v3
    assert block["search_limits"]["version"] == "ppv1-search-limits-3"
    assert block["search_limits"]["max_total_search_actions"] == 10
    # S3b:独立有界格式反馈策略(默认 0 轮;非 search_limits 旧字段)
    assert block["format_feedback_policy"] == {
        "version": "ppv1-format-feedback-1",
        "max_format_feedback_rounds": 0}
    # S4b:正式文件导出/v3 有损投影入 delivered_stages(S5 未交付)
    assert block["delivered_stages"] == \
        "S0-S2,S3a-base,S3b,S4a-endpoint,S4b-export"


@pytest.mark.parametrize("field,bad", [
    ("input_preview_policy", "filter"),
    ("input_preview_policy", None),
    ("chemical_reproposal", "maybe"),
    ("search_intent", "anything_goes"),
])
def test_ppv1_identity_block_fail_closed(field: str, bad) -> None:
    with pytest.raises(ValueError):
        ppv1_profile.build_profile_identity_block(**{field: bad})


def test_search_limits_validation() -> None:
    with pytest.raises(ValueError, match="未知搜索上限键"):
        ppv1_profile.build_profile_identity_block(search_limits={"nope": 1})
    with pytest.raises(ValueError, match="超出允许范围"):
        ppv1_profile.build_profile_identity_block(
            search_limits={"max_total_search_actions": 999999})
    with pytest.raises(ValueError, match="必须是整数"):
        ppv1_profile.build_profile_identity_block(
            search_limits={"max_search_depth": "3"})
    ok = ppv1_profile.build_profile_identity_block(
        search_limits={"max_search_depth": 3})
    assert ok["search_limits"]["max_search_depth"] == 3
    # P2-4 配置往返:完整序列化输出可原样回灌(含 version 字符串键)
    full = ok["search_limits"]
    round_trip = ppv1_profile.build_profile_identity_block(
        search_limits=full)["search_limits"]
    assert round_trip == full
    with pytest.raises(ValueError, match="search_limits.version"):
        ppv1_profile.build_profile_identity_block(
            search_limits={"version": "ppv1-search-limits-1-proposed"})
    # P2-4 零预算夹具合法(独立零深度/零预算,不再笼统拒绝)
    zero = ppv1_profile.build_profile_identity_block(
        search_limits={"max_search_depth": 0,
                       "max_total_search_actions": 0})["search_limits"]
    assert zero["max_search_depth"] == 0
    assert zero["max_total_search_actions"] == 0
    # P0-3 建议小值(备选假设 2/尝试 2/产物宽度 2/深度 3/总 action 10)
    ranges = ppv1_profile.SEARCH_LIMITS_RANGES
    small = {"max_alternative_hypotheses_per_parent": 2,
             "max_attempts_per_hypothesis": 2,
             "max_product_expansion_width": 2, "max_search_depth": 3,
             "max_total_search_actions": 10}
    for k, v in small.items():
        lo, hi = ranges[k]
        assert lo <= v <= hi


# ---------------------------------------------------------------- code 分集


def test_code_identity_excludes_pollutant_for_legacy() -> None:
    legacy = ri.code_identity(ri.PROFILE_LEGACY_V43)
    assert not any(
        p.startswith(ri.PROFILE_EXCLUSIVE_PACKAGE_PREFIX)
        for p in legacy["files"])
    assert legacy["profile"] == "legacy_v43"


def test_code_identity_pollutant_includes_full_tree() -> None:
    pp = ri.code_identity(ri.PROFILE_POLLUTANT_PATHWAY_V1)
    assert any(
        p.startswith(ri.PROFILE_EXCLUSIVE_PACKAGE_PREFIX)
        for p in pp["files"])
    assert pp["profile"] == "pollutant_pathway_v1"


def test_code_identity_unknown_profile_rejected() -> None:
    with pytest.raises(ValueError, match="未知 profile"):
        ri.code_identity("something_else")


def test_code_identity_legacy_stable_under_pollutant_changes(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """加/改 pollutant/ 文件不改变 legacy 身份(分集的程序证据)。"""
    before = ri.code_identity(ri.PROFILE_LEGACY_V43)["aggregate_sha256"]
    extra = (Path(ppv1_profile.__file__).parent / "_s0_probe_tmp.py")
    try:
        extra.write_text("# probe\n", encoding="utf-8")
        after = ri.code_identity(ri.PROFILE_LEGACY_V43)["aggregate_sha256"]
        assert before == after
        pp = ri.code_identity(ri.PROFILE_POLLUTANT_PATHWAY_V1)
        assert pp["aggregate_sha256"] != before
        assert "pathway_v43/pollutant/_s0_probe_tmp.py" in pp["files"]
    finally:
        extra.unlink(missing_ok=True)


# ---------------------------------------------------------------- build/核对


def _minimal_identity(profile: str, profile_policy=None) -> dict:
    return ri.build_run_identity(
        run_id="r-test", root_smiles="CCO", root_cn="CCO",
        strategy={"max_depth": 2, "max_expansions": 5,
                  "max_frontier_width": 3},
        asset_identity=ri.scripted_asset_identity(),
        v3_code_identity={"mode": "scripted_fixture"},
        prediction={"enabled": False, "provider": "off", "model_id": "",
                    "prompt_versions": {}, "policy_version": "x",
                    "policy": {}},
        profile=profile,
        **({"profile_policy": profile_policy}
           if profile_policy is not None else {}),
    )


def test_build_run_identity_default_is_legacy() -> None:
    identity = _minimal_identity(ri.PROFILE_LEGACY_V43)
    assert identity["profile"] == {"name": "legacy_v43"}
    assert identity["schema_version"] == "v43-identity-2"
    # 身份可 JSON 往返(落盘格式)
    assert json.loads(json.dumps(identity))["profile"] == {"name": "legacy_v43"}


def test_build_run_identity_legacy_rejects_profile_policy() -> None:
    with pytest.raises(ValueError, match="legacy_v43 不接受 profile_policy"):
        _minimal_identity(ri.PROFILE_LEGACY_V43,
                          profile_policy={"input_preview_policy": "off"})


def test_build_run_identity_pollutant_block() -> None:
    identity = _minimal_identity(
        ri.PROFILE_POLLUTANT_PATHWAY_V1,
        profile_policy={"input_preview_policy": "diagnostic"},
    )
    assert identity["profile"]["name"] == "pollutant_pathway_v1"
    assert identity["profile"]["input_preview_policy"] == "diagnostic"
    assert identity["code_identity"]["profile"] == "pollutant_pathway_v1"


def test_build_run_identity_unknown_profile_rejected() -> None:
    with pytest.raises(ValueError, match="未知 profile"):
        _minimal_identity("nope")


def test_check_resume_identity_profile_mismatch_rejected() -> None:
    saved = _minimal_identity(ri.PROFILE_POLLUTANT_PATHWAY_V1)
    current = _minimal_identity(ri.PROFILE_POLLUTANT_PATHWAY_V1)
    ri.check_resume_identity(saved, current)  # 同 profile 通过(其余一致)
    legacy_now = _minimal_identity(ri.PROFILE_LEGACY_V43)
    with pytest.raises(ri.IdentityMismatch) as exc_info:
        ri.check_resume_identity(saved, legacy_now)
    assert "profile" in exc_info.value.detail["differences"]


def test_check_resume_identity_v1_missing_profile_read_as_legacy() -> None:
    """v43-identity-1 旧身份无 profile 字段:按 legacy 读取,不因缺字段拒。"""
    saved = _minimal_identity(ri.PROFILE_LEGACY_V43)
    saved.pop("profile")  # 模拟 v1 旧格式
    current = _minimal_identity(ri.PROFILE_LEGACY_V43)
    # 其余字段一致(除 code_identity 会因本仓升级变化——这里换成 saved 的
    # 值以单测 profile 维度本身)
    current["code_identity"] = saved["code_identity"]
    ri.check_resume_identity(saved, current)


def test_identity_fingerprint_includes_profile() -> None:
    a = _minimal_identity(ri.PROFILE_LEGACY_V43)
    b = _minimal_identity(ri.PROFILE_LEGACY_V43)
    b["profile"] = {"name": "legacy_v43", "note": "changed"}
    assert ri.identity_fingerprint(a) != ri.identity_fingerprint(b)


# ---------------------------------------------------------------- runner/CLI


def test_start_run_pollutant_dispatches_to_runflow(tmp_path: Path) -> None:
    """S3b 行为翻转(2026-10-08,原 S3a fail-closed 拒绝按交付解除):
    公共 start_run 对 pollutant_pathway_v1 分流到独立 PPV1 执行流 ——
    建独立 run 目录(run_identity + pollutant.sqlite,不落 legacy
    PathwayStore);空计划 ⇒ 池无候选诚实停止。E2E 见
    tests/test_ppv1_s3b_runner.py。"""
    from pathway_v43.config import resolve_config
    from pathway_v43.workflow.runner import start_run

    runs_root = tmp_path / "runs"
    out = start_run(
        config=resolve_config(), runs_root=runs_root,
        run_id="ppv1-probe", smiles="CCO", max_depth=2,
        max_expansions=5, max_frontier_width=3,
        finder=object(), scripted=True,
        profile=ri.PROFILE_POLLUTANT_PATHWAY_V1,
    )
    assert out["profile"] == "pollutant_pathway_v1"
    assert (runs_root / "ppv1-probe" / "run_identity.json").is_file()
    assert (runs_root / "ppv1-probe" / "pollutant.sqlite").is_file()
    assert not (runs_root / "ppv1-probe" / "pathway.sqlite").exists()
    assert out["counts"]["events"] == 0
    assert out["stop"]["unexplored"]["pending_actions"] == 0


def test_start_run_unknown_profile_rejected(tmp_path: Path) -> None:
    from pathway_v43.config import resolve_config
    from pathway_v43.workflow.runner import RunError, start_run

    with pytest.raises(RunError, match="未知 profile"):
        start_run(
            config=resolve_config(), runs_root=tmp_path / "runs",
            run_id="bad-profile", smiles="CCO", max_depth=2,
            max_expansions=5, max_frontier_width=3,
            finder=object(), scripted=True, profile="nope",
        )
    assert not (tmp_path / "runs" / "bad-profile").exists()


def test_cli_profile_flag_choices() -> None:
    from pathway_v43.__main__ import build_parser

    parser = build_parser()
    args = parser.parse_args([
        "run", "--smiles", "CCO", "--run-id", "x",
        "--profile", "legacy_v43"])
    assert args.profile == "legacy_v43"
    args2 = parser.parse_args([
        "run", "--smiles", "CCO", "--run-id", "x",
        "--profile", "pollutant_pathway_v1"])
    assert args2.profile == "pollutant_pathway_v1"
    with pytest.raises(SystemExit):
        parser.parse_args([
            "run", "--smiles", "CCO", "--run-id", "x", "--profile", "zzz"])
