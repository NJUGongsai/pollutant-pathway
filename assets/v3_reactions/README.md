# depending v3.5 environmental runtime assets

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
  python reaction_analogy/predict_env_batch_v35.py \
      --parents-csv <csv> --out-dir <dir> \
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
