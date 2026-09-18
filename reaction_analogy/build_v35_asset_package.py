#!/usr/bin/env python3
"""Build the v3.5 environmental runtime-asset package (P0-1 fix).

Colleague review (2026-09-18) requires a standalone, versioned runtime asset
package so a fresh clone can run v3.5 without the dev machine's untracked
corpus_env.  This builder stages and tars:

  depending_v35_environment_runtime_assets_<date>/
    corpus_env/corpus_v1.jsonl          deployment retrieval corpus
    corpus_env/donor_index.jsonl        deployment donor index
    corpus_env_eval/corpus_v1.jsonl     local-eval corpus (holdout excluded)
    corpus_env_eval/donor_index.jsonl
    library/library_full.jsonl          environmental lookup library
    calibrators/calibrator_v34.json     per-source isotonic (v3.4)
    calibrators/calibrator_v35.json     + donor-Tanimoto transfer iso (v3.5)
    MANIFEST.files                      name + bytes table
    MANIFEST.sha256                     "<sha256>  <relative path>" lines
    README.md                           install + fail-closed contract

Outputs (in --out-dir):
  depending_v35_environment_runtime_assets_<date>.tar.gz
  depending_v35_environment_runtime_assets_<date>.tar.gz.identity.txt
  depending_v35_environment_runtime_assets_<date>.tar.gz.validation.txt
    (validation.txt is appended by run_p0_validation.py after checks pass)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, ".."))

SOURCES = {
    "corpus_env/corpus_v1.jsonl":
        "reaction_analogy/data/corpus_env/corpus_v1.jsonl",
    "corpus_env/donor_index.jsonl":
        "reaction_analogy/data/corpus_env/donor_index.jsonl",
    "corpus_env_eval/corpus_v1.jsonl":
        "reaction_analogy/data/corpus_env_eval/corpus_v1.jsonl",
    "corpus_env_eval/donor_index.jsonl":
        "reaction_analogy/data/corpus_env_eval/donor_index.jsonl",
    "library/library_full.jsonl":
        "reaction_analogy/data/env_expand/library_full.jsonl",
    "calibrators/calibrator_v34.json":
        "data/bbd_v34/calibrator_v34.json",
    "calibrators/calibrator_v35.json":
        "data/bbd_v34/calibrator_v35.json",
    "rankers/uspto_ranker.txt":
        "data/bbd_v31/uspto_ranker.txt",
    "rankers/envipath_ranker.txt":
        "data/bbd_v31/envipath_ranker.txt",
    "rankers/retrieval_ranker.txt":
        "data/bbd_v31/retrieval_ranker.txt",
}

README = """# depending v3.5 environmental runtime assets

Versioned runtime assets for the v3.5 environmental caliber (soil/sludge
repair round 2, 2026-09-18).  The depending repo deliberately does NOT track
these large regenerable artifacts (repo data policy); this package is the
authoritative distribution unit.

## Contents

  corpus_env/        deployment retrieval corpus (corpus_v1 + 5,497
                     environmental reaction records + EAWAG-BBD)
  corpus_env_eval/   local-evaluation corpus (holdout parents' reactions
                     excluded — for the leave-parent-out caliber only)
  library/           environmental lookup library (EAWAG-BBD + EAWAG-SOIL/
                     SLUDGE/SEDIMENT packages, 4,454 rows, 2,678 donors)
  calibrators/       calibrator_v34.json (per-source isotonic) and
                     calibrator_v35.json (+ donor-Tanimoto transfer iso)
  MANIFEST.files     name + bytes
  MANIFEST.sha256    "<sha256>  <relative path>" — the load-time contract

## Install (fresh clone)

  tar xzf depending_v35_environment_runtime_assets_<date>.tar.gz
  # option A (explicit):
  python reaction_analogy/predict_env_batch_v35.py \\
      --parents-csv <csv> --out-dir <dir> \\
      --env-data-root <path-to-unpacked-dir>
  # option B (environment variable):
  export DEPENDING_V35_DATA_ROOT=<path-to-unpacked-dir>
  # option C (repo staging): copy corpus_env/ into
  # reaction_analogy/data/corpus_env/ (dev mode; SHA-verified against
  # reaction_analogy/data/env_expand/CORPUS_ENV.sha256)

## Fail-closed contract

  Every v3.5 run resolves the asset root (CLI --env-data-root >
  $DEPENDING_V35_DATA_ROOT > repo staging) and verifies each required
  file's SHA256 against MANIFEST.sha256 BEFORE loading anything.  Missing
  file, missing manifest entry, or byte mismatch aborts the run with a
  non-zero exit — there is NO silent fallback to the legacy corpus_v1.

## Calibrator versioning (P0-2)

  --scoring v34 -> calibrators/calibrator_v34.json (per-source isotonic)
  --scoring v35 -> calibrators/calibrator_v35.json (+ Tanimoto transfer)
  The scoring mode IS the calibrator version; no auto-upgrade ever happens.
  run_report.json records scoring_mode, calibrator_path/version/bytes/
  sha256, environment_library_sha256, corpus_v1_sha256,
  donor_index_sha256, asset_mode/root and git_commit.
"""


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir",
                    default=os.path.join(_HERE, "deliverables"))
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    pkg_name = f"depending_v35_environment_runtime_assets_{args.date}"
    stage = os.path.join(args.out_dir, pkg_name)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    manifest_lines = []
    files_table = []
    for rel, src in SOURCES.items():
        src_abs = os.path.join(_REPO, src)
        if not os.path.isfile(src_abs):
            print(f"FATAL: source missing: {src_abs}", flush=True)
            return 2
        dst = os.path.join(stage, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src_abs, dst)
        h = sha256_file(dst)
        manifest_lines.append(f"{h}  {rel}")
        files_table.append({"path": rel, "bytes": os.path.getsize(dst),
                            "sha256": h})

    with open(os.path.join(stage, "MANIFEST.sha256"), "w") as f:
        f.write("\n".join(manifest_lines) + "\n")
    with open(os.path.join(stage, "MANIFEST.files"), "w") as f:
        json.dump({"package": pkg_name, "files": files_table}, f, indent=1)
    with open(os.path.join(stage, "README.md"), "w") as f:
        f.write(README)

    tar_path = os.path.join(args.out_dir, pkg_name + ".tar.gz")
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(stage, arcname=pkg_name)

    tar_sha = sha256_file(tar_path)
    git_commit = os.popen(
        f"git -C {_REPO} rev-parse HEAD").read().strip()
    identity = {
        "package": pkg_name + ".tar.gz",
        "tar_sha256": tar_sha,
        "tar_bytes": os.path.getsize(tar_path),
        "git_commit": git_commit,
        "n_files": len(SOURCES),
        "manifest_sha256": sha256_file(
            os.path.join(stage, "MANIFEST.sha256")),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": files_table,
    }
    with open(tar_path + ".identity.txt", "w") as f:
        json.dump(identity, f, indent=1, ensure_ascii=False)

    print(f"package built: {tar_path}")
    print(f"  tar sha256: {tar_sha}")
    print(f"  tar bytes: {identity['tar_bytes']:,}")
    print(f"  files: {len(SOURCES)} + manifests + README")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
