#!/usr/bin/env python3
"""P0 fix tests (colleague review 2026-09-18): v3.5 asset resolution and
explicit calibrator versioning.

Coverage (their §"必须补的最小测试"):
  1. v34 explicitly loads the v34 calibrator           -> test_t1_v34_loads_v34
  2. v35 explicitly loads the v35 calibrator           -> test_t2_v35_loads_v35
  3. v34/v35 run-report identity fields are correct    -> test_t3_identity_fields
  4. corpus_env missing -> fail-closed                 -> test_t4_missing_failclosed
  5. corpus_env SHA wrong -> fail-closed               -> test_t5_sha_failclosed
  6. staged assets run 2 non-gold parents end-to-end   -> test_t6_staged_smoke
  7. lookup rows precede prediction rows + provenance  -> test_t7_order_provenance
  8. never reads soil/sludge restricted answers        -> test_t8_no_gold

Run:  python tests/test_v35_p0_fixes.py [test_name ...]   (no args = all fast
tests; T3/T6/T7 run the full engine stack once via a single batch run —
slow tests are skipped unless requested explicitly or ALL is given.)

A smoke CSV of NON-GOLD parents (public environmental compounds from the
crawled packages; no colleague answer key involved) is used for the engine
tests.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_RA = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, _RA)

FAST_ONLY = not (len(sys.argv) > 1)
WANTED = set(sys.argv[1:]) or {"FAST"}

SMOKE_PARENTS = [
    # public environmental compounds (crawled package educts; non-gold)
    ("T1", "ClCCCl"),                      # 1,2-dichloroethane
    ("T2", "CCNc1nc(Cl)nc(NC(C)C)n1"),     # atrazine
]

RESTRICTED_MARKERS = [
    "soil_sludge", "SOIL_SLUDGE", "restricted_answer",
    "KNOWN_PATHWAY_POLLUTANT_RESTRICTED",
]


def run(name):
    return name in WANTED or "ALL" in WANTED


def _fresh_import(mod_name):
    """Import a module fresh (drop cached) to test load-time behaviour."""
    for m in list(sys.modules):
        if m == mod_name or m.startswith(mod_name + "."):
            del sys.modules[m]
    return __import__(mod_name)


def test_t1_v34_loads_v34():
    X = _fresh_import("expand_bbd_routes")
    X._G_V34_CALIB = None
    X._G_V34_VERSION = None
    X._G_V34_CALIB_PATH = None
    calib = X._load_v34_calibrator(version="v34")
    assert calib, "v34 calibrator failed to load"
    assert X._G_V34_VERSION == "v34"
    assert X._G_V34_CALIB_PATH.endswith("calibrator_v34.json"), \
        f"v34 mode loaded {X._G_V34_CALIB_PATH}"
    assert calib._tan_cuts is None, \
        "v34 calibrator must NOT carry the v35 Tanimoto transfer iso"
    return "T1 OK: --scoring v34 -> calibrator_v34.json (no transfer iso)"


def test_t2_v35_loads_v35():
    X = _fresh_import("expand_bbd_routes")
    X._G_V34_CALIB = None
    X._G_V34_VERSION = None
    X._G_V34_CALIB_PATH = None
    calib = X._load_v34_calibrator(version="v35")
    assert calib, "v35 calibrator failed to load"
    assert X._G_V34_VERSION == "v35"
    assert X._G_V34_CALIB_PATH.endswith("calibrator_v35.json"), \
        f"v35 mode loaded {X._G_V34_CALIB_PATH}"
    assert calib._tan_cuts is not None, \
        "v35 calibrator must carry the Tanimoto transfer iso"
    return "T2 OK: --scoring v35 -> calibrator_v35.json (transfer iso present)"


def test_t4_missing_failclosed():
    """corpus_env missing -> EnvAssetError (no legacy fallback)."""
    EAR = _fresh_import("env_asset_root")
    with tempfile.TemporaryDirectory() as td:
        # a root with NO corpus at all
        try:
            EAR.verify_env_assets(td, "cli")
            raise AssertionError("verify must fail on empty root")
        except EAR.EnvAssetError:
            pass
        # resolution: fake env var pointing nowhere
        os.environ[EAR.ENV_DATA_ROOT_ENV] = os.path.join(td, "nope")
        try:
            EAR.resolve_env_data_root(None)
            raise AssertionError("resolve must fail on missing root")
        except EAR.EnvAssetError:
            pass
        finally:
            del os.environ[EAR.ENV_DATA_ROOT_ENV]
    return "T4 OK: missing corpus_env -> EnvAssetError (fail-closed)"


def test_t5_sha_failclosed():
    """corpus_env present but bytes altered -> SHA mismatch -> abort."""
    EAR = _fresh_import("env_asset_root")
    with tempfile.TemporaryDirectory() as td:
        # build a minimal corrupt package: copy the real staged package then
        # flip one byte of the corpus
        src = os.path.join(_RA, "deliverables",
                           "depending_v35_environment_runtime_assets_"
                           "2026-09-18")
        if not os.path.isdir(src):
            return ("T5 SKIP: staged package not built "
                    "(run build_v35_asset_package.py first)")
        for rel in ("corpus_env", "library", "calibrators", "rankers",
                    "MANIFEST.sha256"):
            s = os.path.join(src, rel)
            d = os.path.join(td, rel)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        corpus = os.path.join(td, "corpus_env", "corpus_v1.jsonl")
        with open(corpus, "ab") as f:
            f.write(b"# mutation: one extra byte\n")
        try:
            EAR.verify_env_assets(td, "cli")
            raise AssertionError("verify must fail on SHA mismatch")
        except EAR.EnvAssetError as e:
            assert "SHA mismatch" in str(e), f"unexpected error: {e}"
    return "T5 OK: corrupted corpus bytes -> SHA mismatch abort"


def test_t8_no_gold():
    """Static check: no v3.5 source reads restricted/answer files."""
    import glob
    offenders = []
    for py in glob.glob(os.path.join(_RA, "*.py")):
        name = os.path.basename(py)
        if not any(k in name for k in ("v34", "v35", "env_", "predict_env",
                                       "single_smiles", "eval_env")):
            continue
        text = open(py, encoding="utf-8", errors="replace").read()
        for marker in RESTRICTED_MARKERS:
            if marker in text:
                offenders.append((name, marker))
    assert not offenders, f"gold references found: {offenders}"
    return "T8 OK: no v3.5 source references soil/sludge restricted answers"


def _batch_run(scoring, out_dir, env_root):
    """Run the batch driver once on the smoke parents (full stack)."""
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "parents.csv")
    with open(csv_path, "w") as f:
        f.write("case_id,parent_smiles\n")
        for cid, smi in SMOKE_PARENTS:
            f.write(f"{cid},{smi}\n")
    cmd = [sys.executable,
           os.path.join(_RA, "predict_env_batch_v35.py"),
           "--parents-csv", csv_path, "--out-dir", out_dir,
           "--top-k", "10", "--scoring", scoring,
           "--env-data-root", env_root]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=_RA,
                       timeout=1800)
    return r


def test_t3_identity_fields():
    if FAST_ONLY and "T3" not in WANTED:
        return "T3 SKIP (slow)"
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(_RA, "deliverables",
                            "depending_v35_environment_runtime_assets_"
                            "2026-09-18")
        out = os.path.join(td, "run")
        for scoring in ("v34", "v35"):
            r = _batch_run(scoring, os.path.join(out, scoring), root)
            assert r.returncode == 0, f"{scoring} run failed: {r.stderr[-800:]}"
            rep = json.load(open(os.path.join(out, scoring,
                                              "run_report.json")))
            ident = rep["identity"]
            for field in ("scoring_mode", "calibrator_version",
                          "calibrator_path", "calibrator_bytes",
                          "calibrator_sha256",
                          "environment_library_sha256",
                          "corpus_v1_sha256", "donor_index_sha256",
                          "git_commit"):
                assert field in ident, f"{scoring}: missing {field}"
                assert ident[field] not in ("", None), \
                    f"{scoring}: empty {field}"
            assert ident["scoring_mode"] == scoring
            assert ident["calibrator_version"] == scoring
            assert ident["calibrator_path"].endswith(
                f"calibrator_{scoring}.json"), ident["calibrator_path"]
            v34sha = json.load(open(
                os.path.join(root, "calibrators",
                             "calibrator_v34.json")))  # existence only
            if scoring == "v34":
                assert ident["calibrator_sha256"] == _sha(
                    os.path.join(root, "calibrators",
                                 "calibrator_v34.json"))
            else:
                assert ident["calibrator_sha256"] == _sha(
                    os.path.join(root, "calibrators",
                                 "calibrator_v35.json"))
    return ("T3 OK: run_report.identity complete + version-correct "
            "(v34 and v35)")


def test_t6_staged_smoke():
    if FAST_ONLY and "T6" not in WANTED:
        return "T6 SKIP (slow)"
    with tempfile.TemporaryDirectory() as td:
        # unpack the tar.gz like a fresh-clone consumer would
        import tarfile
        tarball = os.path.join(
            _RA, "deliverables",
            "depending_v35_environment_runtime_assets_2026-09-18.tar.gz")
        with tarfile.open(tarball) as tf:
            tf.extractall(td)
        root = os.path.join(td, "depending_v35_environment_runtime_assets_"
                          "2026-09-18")
        out = os.path.join(td, "run")
        r = _batch_run("v35", out, root)
        assert r.returncode == 0, f"staged run failed: {r.stderr[-800:]}"
        preds = [json.loads(line) for line in
                 open(os.path.join(out, "predictions.jsonl"))]
        assert len(preds) == len(SMOKE_PARENTS)
        for p in preds:
            assert p["top_products"], "no predictions emitted"
        # fail-closed negative: point at a dir WITHOUT assets
        r2 = _batch_run("v35", os.path.join(td, "run2"), td)
        assert r2.returncode == 2, \
            f"missing assets must exit 2, got {r2.returncode}"
        assert "fail-closed" in r2.stderr, r2.stderr[-500:]
    return "T6 OK: staged assets run 2 non-gold parents; missing -> exit 2"


def test_t7_order_provenance():
    if FAST_ONLY and "T7" not in WANTED:
        return "T7 SKIP (slow)"
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(_RA, "deliverables",
                            "depending_v35_environment_runtime_assets_"
                            "2026-09-18")
        out = os.path.join(td, "run")
        r = _batch_run("v35", out, root)
        assert r.returncode == 0, r.stderr[-800:]
        preds = [json.loads(line) for line in
                 open(os.path.join(out, "predictions.jsonl"))]
        for p in preds:
            layers = [t["layer"] for t in p["top_products"]]
            if "lookup" in layers and "prediction" in layers:
                first_pred = layers.index("prediction")
                last_look = len(layers) - 1 - layers[::-1].index("lookup")
                assert last_look < first_pred, \
                    f"lookup rows must precede prediction rows: {layers}"
            for t in p["top_products"]:
                if t["layer"] == "lookup":
                    assert t.get("eawag_reactions"), \
                        "lookup row missing eawag_reactions provenance"
                    assert t["source"] == "eawag_lookup"
                else:
                    assert "v34_regime" in t, \
                        "prediction row missing v34_regime audit field"
                    assert t["product_identity"], \
                        "prediction row missing product_identity"
    return "T7 OK: lookup-first order + provenance + audit fields preserved"


def _sha(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


ALL_TESTS = [test_t1_v34_loads_v34, test_t2_v35_loads_v35,
             test_t3_identity_fields, test_t4_missing_failclosed,
             test_t5_sha_failclosed, test_t6_staged_smoke,
             test_t7_order_provenance, test_t8_no_gold]


def main() -> int:
    results = []
    failed = []
    for t in ALL_TESTS:
        try:
            results.append(t())
            print(results[-1], flush=True)
        except AssertionError as e:
            failed.append((t.__name__, str(e)))
            print(f"{t.__name__} FAIL: {e}", flush=True)
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, f"{type(e).__name__}: {e}"))
            print(f"{t.__name__} ERROR: {type(e).__name__}: {e}", flush=True)
    print(f"\n{len(results) - len([r for r in results if 'SKIP' in r])} "
          f"passed, {len(failed)} failed", flush=True)
    if failed:
        for name, msg in failed:
            print(f"  FAILED {name}: {msg}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
