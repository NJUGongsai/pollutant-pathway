#!/usr/bin/env python
"""v4 / v4.3 引擎资产对拍(零 LLM,确定性引擎,双臂独立子进程)。

用法:

    python scripts/compare_asset_roots.py                       # 跑两臂并比较
    python scripts/compare_asset_roots.py --arm old --out a.json --v3-root ../dependingv3 --v4-root ../dependingv4
    python scripts/compare_asset_roots.py --arm new --out b.json --v3-root ../dependingv3 --assets-root assets

两臂:
  old = v4 pathway_agent.engine.V3Engine + 原 dependingv3/assets
  new = v4.3 pathway_v43 适配器     + 本仓 assets/v3_reactions

同一解释器、同一 v3 代码、字节一致的 13 个 v3 运行数据文件、OMP_NUM_THREADS=1。
比较规范产物身份、候选数、候选顺序、source/layer、engine_rank、共同 score 字段
与 score_semantics;v4.3 新增透传的来源字段单独检查,不计入对拍差异。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 对拍比较的字段(两臂序列化共有;浮点已统一 round(·,6),做精确相等)
COMPARE_FIELDS = (
    "rank",
    "engine_rank",
    "layer",
    "product_smiles",
    "product_identity",
    "source",
    "score",
    "score_semantics",
    "v34_regime",
    "eawag_reactions",
    "p_uspto",
    "p_envipath",
    "p_retrieval",
    "ion_filtered",
    "wildcard_filtered",
    "charge_variants",
)

# v4.3 新增透传字段:只做存在性/语义检查,不参与两臂相等比较
NEW_ONLY_FIELDS = ("donor_exact_match", "n_evidence", "cofactor_filtered",
                   "filtered", "product_smiles_full", "tanimoto")


# ---------------------------------------------------------------- 两臂运行体

def _run_arm_old(args: argparse.Namespace, out_path: Path) -> None:  # pragma: no cover
    """旧臂:v4 V3Engine + 原 v3/assets。独立进程内执行。"""
    v3_root = Path(args.v3_root).resolve()
    v4_root = Path(args.v4_root).resolve()
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["DEPENDING_V3_ROOT"] = str(v3_root)  # v4 引擎也在 import 前注入
    for p in (str(v4_root / "src"), str(v3_root / "src" / "depending")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from pathway_agent.engine import V3Engine as V4Engine  # type: ignore

    engine = V4Engine(v3_root)
    _run_fixtures(engine, args, out_path,
                  asset_root=str(v3_root / "assets"), arm="old")


def _run_arm_new(args: argparse.Namespace, out_path: Path) -> None:  # pragma: no cover
    """新臂:v4.3 适配器 + 本仓 assets/v3_reactions。独立进程内执行。"""
    v3_root = Path(args.v3_root).resolve()
    assets_root = Path(args.assets_root).resolve()
    os.environ["OMP_NUM_THREADS"] = "1"
    if str(REPO_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "src"))
    from pathway_v43.config import resolve_config
    from pathway_v43.adapters.v3_engine import get_engine

    config = resolve_config(str(v3_root), str(assets_root))
    engine = get_engine(config)
    _run_fixtures(engine, args, out_path,
                  asset_root=str(config.v3_run_root.resolve()), arm="new")


def _run_fixtures(engine, args: argparse.Namespace, out_path: Path,
                  asset_root: str, arm: str) -> None:  # pragma: no cover
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))["fixtures"]
    results = []
    for fixture in fixtures:
        name = fixture["name"]
        smiles = fixture["smiles"]
        case_id = f"parity_{name}"
        try:
            merged = engine.expand_merged(smiles, case_id)
        except Exception as exc:
            # 运行期异常 ≠ “不可解析输入”:单独记录,比较阶段按失败处理,
            # 绝不因两臂同错而误报通过。
            results.append({
                "name": name, "smiles": smiles,
                "runtime_failure": True,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })
            continue
        if "error" in merged:
            results.append({
                "name": name, "smiles": smiles, "parseable": False,
                "error_type": merged["error"],
            })
            continue
        try:
            cands = engine.predict(smiles, case_id, top_k=None)
        except Exception as exc:
            results.append({
                "name": name, "smiles": smiles, "parseable": True,
                "runtime_failure": True,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })
            continue
        results.append({
            "name": name,
            "smiles": smiles,
            "parseable": True,
            "canonical_smiles": merged.get("canonical_smiles"),
            "n_lookup": merged.get("n_lookup"),
            "n_pred_candidates": merged.get("n_pred_candidates"),
            "budget_cut": merged.get("budget_cut"),
            "n_candidates": len(cands),
            "candidates": cands,
        })
    from platform import platform as _platform, python_version

    out = {
        "arm": arm,
        "asset_root": asset_root,
        "v3_code_root": str(Path(args.v3_root).resolve()),
        "fixtures_path": str(Path(args.fixtures).resolve()),
        "python": python_version(),
        "platform": _platform(),
        "results": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[{arm}] wrote {out_path}", flush=True)


# ---------------------------------------------------------------- 比较

def _categories_of(cands: list[dict]) -> set[str]:
    """从实际候选推导来源类别(合并 source 如 "uspto+retrieval" 按词素拆分)。"""
    cats: set[str] = set()
    for c in cands:
        src = str(c.get("source", ""))
        if c.get("layer") == "lookup" or src == "eawag_lookup":
            cats.add("eawag_lookup")
        if "retrieval" in src:
            cats.add("retrieval")
        if "envipath" in src:
            cats.add("envipath")
        if "uspto" in src:
            cats.add("uspto")
        if "+" in src:
            cats.add("merged_multi_source")
    return cats


def _check_expectations(expect: dict, results: dict) -> list[dict]:
    """按夹具声明验收两臂的实际结果(解析状态/候选数/lookup 命中/来源类别)。

    任一臂不满足即产出 diff(整个夹具判 FAIL);预期来自
    tests/fixtures/asset_wiring_parents.json,而非两臂是否恰好一致。
    """
    diffs: list[dict] = []
    for arm in ("old", "new"):
        r = results[arm]
        if expect.get("parseable") is False:
            if r.get("runtime_failure"):
                diffs.append({"field": f"{arm}.runtime_failure",
                              "expect": "unparseable_parent",
                              "actual": r.get("error_type")})
            elif r.get("parseable") is not False:
                diffs.append({"field": f"{arm}.parseable",
                              "expect": False, "actual": r.get("parseable")})
            elif r.get("error_type") != "unparseable_parent":
                diffs.append({"field": f"{arm}.error_type",
                              "expect": "unparseable_parent",
                              "actual": r.get("error_type")})
            elif r.get("candidates"):
                diffs.append({"field": f"{arm}.candidates",
                              "expect": "空", "actual": len(r["candidates"])})
            continue
        # parseable=True 的夹具:不许任何运行失败
        if r.get("runtime_failure"):
            diffs.append({"field": f"{arm}.runtime_failure", "expect": None,
                          "actual": f"{r.get('error_type')}: {r.get('error', '')}"})
            continue
        if r.get("parseable") is not True:
            diffs.append({"field": f"{arm}.parseable", "expect": True,
                          "actual": r.get("parseable"),
                          "error": r.get("error_type")})
            continue
        min_n = expect.get("min_candidates")
        if min_n is not None and r.get("n_candidates", 0) < int(min_n):
            diffs.append({"field": f"{arm}.n_candidates",
                          "expect": f">= {min_n}", "actual": r.get("n_candidates")})
        expect_hit = expect.get("lookup_hit")
        actual_hit = (r.get("n_lookup") or 0) > 0
        if expect_hit is not None and actual_hit != bool(expect_hit):
            diffs.append({"field": f"{arm}.lookup_hit",
                          "expect": bool(expect_hit), "actual": actual_hit})
        declared = set(expect.get("categories", []))
        found = _categories_of(r.get("candidates", []))
        missing = sorted(declared - found)
        if missing:
            diffs.append({"field": f"{arm}.categories", "expect": sorted(declared),
                          "missing": missing})
    return diffs


def _coverage_problems(fixtures: list[dict], old: dict, new: dict) -> list[dict]:
    """两臂结果必须与声明的夹具名单完全一致:不得缺失、不得多余、不得重名。"""
    declared = [f["name"] for f in fixtures]
    problems: list[dict] = []
    if len(set(declared)) != len(declared):
        dupes = sorted({n for n in declared if declared.count(n) > 1})
        problems.append({"issue": "duplicate_fixture_names", "names": dupes})
    declared_set = set(declared)
    for arm_name, arm in (("old", old), ("new", new)):
        names = [str(r.get("name")) for r in arm.get("results", [])]
        if len(set(names)) != len(names):
            dupes = sorted({n for n in names if names.count(n) > 1})
            problems.append({"issue": f"{arm_name}_duplicate_result_names",
                             "names": dupes})
        missing = sorted(declared_set - set(names))
        if missing:
            problems.append({"issue": f"{arm_name}_missing_fixtures",
                             "names": missing})
        extra = sorted(set(names) - declared_set)
        if extra:
            problems.append({"issue": f"{arm_name}_unexpected_fixtures",
                             "names": extra})
    return problems


def _compare_arms(old: dict, new: dict, fixtures: list[dict]) -> dict:
    expect_by_name = {f["name"]: f.get("expect", {}) for f in fixtures}
    old_by_name = {r["name"]: r for r in old["results"]}
    new_by_name = {r["name"]: r for r in new["results"]}
    fixture_report: list[dict] = []
    all_ok = True

    # 夹具全集核对(回归:P2):两臂同时遗漏夹具不得误报通过
    coverage = _coverage_problems(fixtures, old, new)
    if coverage:
        all_ok = False
        fixture_report.append({
            "name": "__coverage__", "ok": False,
            "coverage_problems": coverage, "diffs": coverage,
            "n_candidates": {"old": None, "new": None},
            "declared_categories": [], "found_categories": [],
            "n_diff_fields": len(coverage),
        })

    for name in dict.fromkeys(f["name"] for f in fixtures):
        ro, rn = old_by_name.get(name), new_by_name.get(name)
        if ro is None or rn is None:
            continue  # 缺失已由 __coverage__ 记录
        diffs: list[dict] = []
        expect = expect_by_name.get(name, {})
        if ro.get("parseable") != rn.get("parseable"):
            diffs.append({"field": "parseable", "old": ro.get("parseable"),
                          "new": rn.get("parseable")})
        if not ro.get("parseable"):
            if ro.get("error_type") != rn.get("error_type"):
                diffs.append({"field": "error_type", "old": ro.get("error_type"),
                              "new": rn.get("error_type")})
        else:
            for field in ("canonical_smiles", "n_lookup", "n_pred_candidates",
                          "budget_cut", "n_candidates"):
                if ro.get(field) != rn.get(field):
                    diffs.append({"field": field, "old": ro.get(field),
                                  "new": rn.get(field)})
            co, cn = ro.get("candidates", []), rn.get("candidates", [])
            for idx in range(min(len(co), len(cn))):
                a, b = co[idx], cn[idx]
                for field in COMPARE_FIELDS:
                    if a.get(field) != b.get(field):
                        diffs.append({
                            "field": f"candidates[{idx}].{field}",
                            "old": a.get(field), "new": b.get(field),
                            "old_product": a.get("product_smiles", "")[:60],
                            "new_product": b.get("product_smiles", "")[:60],
                        })
            # v4.3 新增字段:单独检查(lookup 层必须有证据字段),不算对拍差异
            new_only_report = []
            for idx, b in enumerate(cn):
                if b.get("layer") == "lookup":
                    ok = (b.get("donor_exact_match") is True
                          and isinstance(b.get("n_evidence"), int)
                          and b.get("n_evidence", 0) >= 1
                          and bool(b.get("eawag_reactions")))
                    if not ok:
                        new_only_report.append({"index": idx})
            if not diffs and new_only_report:
                diffs.append({"field": "new_only_lookup_fields",
                              "note": "v4.3 lookup 候选缺少预期来源字段",
                              "indices": new_only_report})
        # 预期验收:任一臂不满足夹具声明即 FAIL(防“两臂同错”误报)
        diffs.extend(_check_expectations(expect, {"old": ro, "new": rn}))
        ok = not diffs
        all_ok = all_ok and ok
        fixture_report.append({
            "name": name, "ok": ok,
            "n_candidates": {"old": ro.get("n_candidates"),
                             "new": rn.get("n_candidates")},
            "declared_categories": sorted(set(expect.get("categories", []))),
            "found_categories": sorted(_categories_of(rn.get("candidates", [])))
            if rn.get("parseable") else [],
            "n_diff_fields": len(diffs),
            "diffs": diffs[:40],
        })
    return {"ok": all_ok, "fixtures": fixture_report,
            "env": {"python_old": old.get("python"), "python_new": new.get("python"),
                    "asset_root_old": old.get("asset_root"),
                    "asset_root_new": new.get("asset_root"),
                    "v3_code_root": old.get("v3_code_root")}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--arm", choices=["old", "new"], default=None,
                        help="只运行单臂并写 JSON(父流程内部用)")
    parser.add_argument("--v3-root", default=str(REPO_ROOT.parent / "dependingv3"))
    parser.add_argument("--v4-root", default=str(REPO_ROOT.parent / "dependingv4"))
    parser.add_argument("--assets-root", default=str(REPO_ROOT / "assets"))
    parser.add_argument(
        "--fixtures",
        default=str(REPO_ROOT / "tests" / "fixtures" / "asset_wiring_parents.json"),
    )
    parser.add_argument("--out", default=None, help="单臂结果 JSON(--arm 模式)")
    parser.add_argument(
        "--out-dir", default=str(REPO_ROOT / "reports" / "asset_wiring_parity"),
        help="父流程两臂原始结果与比较报告目录",
    )
    args = parser.parse_args(argv)

    if args.arm:
        if not args.out:
            parser.error("--arm 模式需要 --out")
        out_path = Path(args.out).resolve()
        if args.arm == "old":
            _run_arm_old(args, out_path)
        else:
            _run_arm_new(args, out_path)
        return 0

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    old_path, new_path = out_dir / "arm_old.json", out_dir / "arm_new.json"
    common = [
        "--v3-root", args.v3_root, "--v4-root", args.v4_root,
        "--assets-root", args.assets_root, "--fixtures", args.fixtures,
    ]
    env = dict(os.environ, OMP_NUM_THREADS="1")
    print("== arm old: v4 V3Engine + v3/assets ==", flush=True)
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--arm", "old",
         "--out", str(old_path), *common],
        check=True, env=env,
    )
    print("== arm new: pathway_v43 + v4.3 assets ==", flush=True)
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--arm", "new",
         "--out", str(new_path), *common],
        check=True, env=env,
    )
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))["fixtures"]
    report = _compare_arms(old, new, fixtures)
    cmp_path = out_dir / "comparison.json"
    cmp_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"comparison written: {cmp_path}")
    for f in report["fixtures"]:
        mark = "PASS" if f["ok"] else "FAIL"
        print(f"  [{mark}] {f['name']}: "
              f"old={f['n_candidates'].get('old')} new={f['n_candidates'].get('new')} "
              f"diffs={f['n_diff_fields']}")
        for d in f["diffs"][:5]:
            print(f"         {d}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
