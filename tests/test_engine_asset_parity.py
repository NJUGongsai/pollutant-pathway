"""v4 / v4.3 引擎资产对拍(slow):双臂独立子进程,全部夹具零差异。

直接驱动 scripts/compare_asset_roots.py 的父流程;原始结果与比较报告落在
reports/asset_wiring_parity/ 下。任一共有字段不一致即测试失败。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT

COMPARE_SCRIPT = REPO_ROOT / "scripts" / "compare_asset_roots.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "asset_wiring_parents.json"
OUT_DIR = REPO_ROOT / "reports" / "asset_wiring_parity"

pytestmark = pytest.mark.slow


def _python() -> str:
    """同解释器运行两臂;pytest 未在 rdkit 环境启动时提示。"""
    try:
        import lightgbm  # noqa: F401
        import rdkit  # noqa: F401
    except Exception:
        pytest.skip(
            "当前解释器缺 rdkit/lightgbm;请在 depending43 环境运行 pytest"
        )
    return sys.executable


@pytest.fixture(scope="module")
def comparison(v3_code_root, v4_code_root):
    if not FIXTURES.is_file():
        pytest.skip(f"夹具缺失:{FIXTURES}")
    cmd = [
        _python(), str(COMPARE_SCRIPT),
        "--v3-root", str(v3_code_root),
        "--v4-root", str(v4_code_root),
        "--out-dir", str(OUT_DIR),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    cmp_path = OUT_DIR / "comparison.json"
    if proc.returncode != 0 or not cmp_path.is_file():
        pytest.fail(
            "对拍脚本失败(exit={})\nstdout tail:\n{}\nstderr tail:\n{}".format(
                proc.returncode,
                "\n".join(proc.stdout.splitlines()[-20:]),
                "\n".join(proc.stderr.splitlines()[-20:]),
            )
        )
    return json.loads(cmp_path.read_text(encoding="utf-8"))


def test_all_fixtures_parity(comparison):
    assert comparison["ok"] is True, json.dumps(comparison, ensure_ascii=False)[:2000]
    for fixture in comparison["fixtures"]:
        assert fixture["ok"], (
            f"{fixture['name']}: {fixture['diffs'][:5]}"
        )


def test_parity_covers_required_categories():
    """夹具声明层面:必须覆盖 EAWAG 命中/规则/检索/合并/非法输入五类。

    实际候选与声明的一致性由比较器逐夹具强制(见
    test_category_and_count_expectations_enforced_against_actual_candidates
    与 test_real_comparison_reports_found_categories)。
    """
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))["fixtures"]
    categories = set()
    for f in fixtures:
        categories |= set(f["expect"].get("categories", []))
        if f["expect"].get("parseable") is False:
            categories.add("invalid_input")
    assert {"eawag_lookup", "retrieval", "envipath", "uspto",
            "merged_multi_source", "invalid_input"} <= categories


def test_arms_ran_on_expected_roots(comparison, v3_code_root):
    env = comparison["env"]
    assert env["asset_root_old"] == str(v3_code_root / "assets")
    assert env["asset_root_new"].startswith(str(REPO_ROOT / "assets"))
    assert env["asset_root_new"].endswith("v3_reactions")
    assert env["python_old"] == env["python_new"]


# ---------------------------------------------------------------- 比较逻辑单元测试
# 防误报回归:运行异常不得记作 parseable=False;两臂同错不得判通过;
# 预期验收必须用实际候选(解析状态/候选数/lookup 命中/来源类别)。

def _load_comparator():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "compare_asset_roots", COMPARE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))["fixtures"]


def _arm_result(name, **fields):
    base = {"name": name, "smiles": "smiles"}
    base.update(fields)
    return base


def _old_new(name, **fields):
    return (_arm_result(name, **fields), _arm_result(name, **fields))


def _placeholder(name, expect):
    """满足夹具预期的最小合法结果(类别/lookup/候选数下限全部达标)。"""
    if expect.get("parseable") is False:
        return _arm_result(name, parseable=False, error_type="unparseable_parent")
    cats = set(expect.get("categories", []))
    cands = []
    if "eawag_lookup" in cats:
        cands.append(_cand("eawag_lookup", layer="lookup"))
    if "merged_multi_source" in cats and {"uspto", "retrieval"} <= cats:
        cands.append(_cand("uspto+retrieval"))
    for c in ("uspto", "envipath", "retrieval"):
        if c in cats:
            cands.append(_cand(c))
    n = max(int(expect.get("min_candidates") or 1), len(cands))
    return _arm_result(name, parseable=True, n_candidates=n,
                       n_lookup=(1 if expect.get("lookup_hit") else 0),
                       budget_cut=False, canonical_smiles="C",
                       candidates=cands)


def _all_fixtures(fixtures, target, result):
    """为全部声明夹具给结果:target 用给定结果,其余给满足预期的占位。"""
    out = []
    for f in fixtures:
        if f["name"] == target:
            out.append(result)
        else:
            out.append(_placeholder(f["name"], f.get("expect", {})))
    return out


def test_same_runtime_failure_on_valid_fixture_fails():
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    ro, rn = _old_new("benzenediol", runtime_failure=True,
                      error_type="OSError", error="disk gone")
    report = cmp_mod._compare_arms(
        {"results": [ro]}, {"results": [rn]}, fixtures)
    assert report["ok"] is False
    ent = next(f for f in report["fixtures"] if f["name"] == "benzenediol")
    assert any(d["field"] == "old.runtime_failure" for d in ent["diffs"])
    assert any(d["field"] == "new.runtime_failure" for d in ent["diffs"])


def test_runtime_failure_in_one_arm_only_fails():
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    ok_result = _arm_result("benzenediol", parseable=True, n_candidates=97,
                            n_lookup=3, budget_cut=False, candidates=[])
    bad = _arm_result("benzenediol", runtime_failure=True,
                      error_type="KeyError")
    report = cmp_mod._compare_arms(
        {"results": [ok_result]}, {"results": [bad]}, fixtures)
    assert report["ok"] is False
    ent = next(f for f in report["fixtures"] if f["name"] == "benzenediol")
    assert ent["ok"] is False


def test_unparseable_passes_only_with_expected_error():
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    ro, rn = _old_new("unparseable", parseable=False,
                      error_type="unparseable_parent")
    report = cmp_mod._compare_arms(
        {"results": _all_fixtures(fixtures, "unparseable", ro)},
        {"results": _all_fixtures(fixtures, "unparseable", rn)}, fixtures)
    assert report["ok"] is True
    # 两臂同报 runtime 错误:不得通过
    ro2, rn2 = _old_new("unparseable", runtime_failure=True,
                        error_type="KeyError", error="boom")
    report2 = cmp_mod._compare_arms(
        {"results": _all_fixtures(fixtures, "unparseable", ro2)},
        {"results": _all_fixtures(fixtures, "unparseable", rn2)}, fixtures)
    assert report2["ok"] is False
    ent2 = next(f for f in report2["fixtures"] if f["name"] == "unparseable")
    assert ent2["ok"] is False


def _cand(source, layer="prediction"):
    c = {"source": source, "layer": layer, "product_smiles": "C",
         "product_identity": "C", "score": 0.1, "rank": 1,
         "engine_rank": 1}
    if layer == "lookup":  # v4.3 新增字段检查要求 lookup 候选带证据
        c.update({"donor_exact_match": True, "n_evidence": 1,
                  "eawag_reactions": ["BT1#1"]})
    return c


def test_category_and_count_expectations_enforced_against_actual_candidates():
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    expect = {f["name"]: f.get("expect", {}) for f in fixtures}
    # benzenediol 声明 eawag_lookup/retrieval/envipath/uspto/merged + lookup_hit
    missing_cats = [_cand("retrieval"), _cand("uspto")]
    ro, rn = _old_new("benzenediol", parseable=True, n_candidates=2,
                      n_lookup=0, budget_cut=False, candidates=missing_cats)
    report = cmp_mod._compare_arms(
        {"results": _all_fixtures(fixtures, "benzenediol", ro)},
        {"results": _all_fixtures(fixtures, "benzenediol", rn)}, fixtures)
    assert report["ok"] is False
    ent = next(f for f in report["fixtures"] if f["name"] == "benzenediol")
    diff_fields = {d["field"] for d in ent["diffs"]}
    assert "old.categories" in diff_fields and "new.categories" in diff_fields
    assert "old.lookup_hit" in diff_fields
    # 候选数低于声明下限同样 FAIL
    ro2, rn2 = _old_new("benzenediol", parseable=True, n_candidates=2,
                        n_lookup=3, budget_cut=False,
                        candidates=[_cand("eawag_lookup", layer="lookup"),
                                    _cand("retrieval"), _cand("envipath"),
                                    _cand("uspto"), _cand("uspto+retrieval")])
    report2 = cmp_mod._compare_arms(
        {"results": _all_fixtures(fixtures, "benzenediol", ro2)},
        {"results": _all_fixtures(fixtures, "benzenediol", rn2)}, fixtures)
    assert report2["ok"] is False
    ent2 = next(f for f in report2["fixtures"] if f["name"] == "benzenediol")
    assert any("n_candidates" in d["field"] for d in ent2["diffs"])
    assert expect["benzenediol"]["min_candidates"] > 5


def test_missing_fixtures_in_both_arms_fail():
    """回归(P2):两臂同时遗漏全部夹具不得误报通过。"""
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    report = cmp_mod._compare_arms({"results": []}, {"results": []}, fixtures)
    assert report["ok"] is False
    cov = [f for f in report["fixtures"] if f["name"] == "__coverage__"]
    assert len(cov) == 1
    issues = {p["issue"] for p in cov[0]["coverage_problems"]}
    assert {"old_missing_fixtures", "new_missing_fixtures"} <= issues


def test_duplicate_and_unexpected_result_names_fail():
    cmp_mod = _load_comparator()
    fixtures = _fixtures()
    dupe = _old_new("benzenediol", runtime_failure=True, error_type="X",
                    error="y")
    duped_results = [dupe[0], dupe[0]]
    report = cmp_mod._compare_arms(
        {"results": duped_results}, {"results": [dupe[1]]}, fixtures)
    assert report["ok"] is False
    cov = [f for f in report["fixtures"] if f["name"] == "__coverage__"]
    issues = {p["issue"] for p in cov[0]["coverage_problems"]}
    assert "old_duplicate_result_names" in issues
    assert "old_missing_fixtures" in issues

    unknown = _arm_result("not_declared", parseable=True, candidates=[])
    report2 = cmp_mod._compare_arms(
        {"results": [unknown]}, {"results": [unknown]}, fixtures)
    assert report2["ok"] is False
    cov2 = [f for f in report2["fixtures"] if f["name"] == "__coverage__"]
    issues2 = {p["issue"] for p in cov2[0]["coverage_problems"]}
    assert {"old_unexpected_fixtures", "new_unexpected_fixtures",
            "old_missing_fixtures", "new_missing_fixtures"} <= issues2


def test_real_comparison_reports_found_categories(comparison):
    """真实对拍报告必须包含按实际候选推导的类别,且覆盖夹具声明。"""
    for fixture in comparison["fixtures"]:
        declared = set(fixture.get("declared_categories", []))
        found = set(fixture.get("found_categories", []))
        if fixture.get("n_candidates", {}).get("new"):
            assert declared <= found, (
                f"{fixture['name']}: 声明 {sorted(declared)} 实得 {sorted(found)}")
