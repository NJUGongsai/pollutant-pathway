#!/usr/bin/env python3
"""v3.5 environmental runtime-asset resolver (P0-1 fix, 2026-09-18).

The colleague review of commit 3de20ba found that a fresh clone cannot run
v3.5 because the default retrieval corpus (reaction_analogy/data/corpus_env/)
is deliberately NOT in git (repo discipline: large regenerable artifacts stay
out; provenance via sha256 manifests).  This module makes the asset root
EXPLICIT and every load FAIL-CLOSED:

  Resolution order for the environmental asset root:
    1. --env-data-root <dir>            (CLI, highest priority)
    2. $DEPENDING_V35_DATA_ROOT         (environment variable)
    3. repo-relative staging            (reaction_analogy/data/ — dev mode)

  Expected layout under the root (the versioned runtime-asset package):
    corpus_env/corpus_v1.jsonl          retrieval corpus records
    corpus_env/donor_index.jsonl        retrieval donor index
    library/library_full.jsonl          environmental lookup library
    calibrators/calibrator_v34.json     per-source isotonic (v3.4)
    calibrators/calibrator_v35.json     + donor-Tanimoto transfer iso (v3.5)
    MANIFEST.sha256                     "<sha256>  <relative path>" lines

  In repo-relative (dev) mode the layout is the historical one:
    data/corpus_env/{corpus_v1,donor_index}.jsonl
    data/env_expand/library_full.jsonl
    data/bbd_v34/calibrator_v3{4,5}.json
    data/env_expand/CORPUS_ENV.sha256   (committed dev manifest for the
                                         untracked corpus_env bytes)

  Fail-closed contract (MUST hold, covered by tests):
    - root missing / corpus files missing -> EnvAssetError (no fallback to
      the legacy corpus_v1, ever);
    - any SHA mismatch against MANIFEST.sha256 -> EnvAssetError;
    - the caller must abort the run (non-zero exit), never silently
      continue with a different corpus/library/calibrator.

Answer-key isolation: this module only reads public runtime assets.
"""
from __future__ import annotations

import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, ".."))

ENV_DATA_ROOT_ENV = "DEPENDING_V35_DATA_ROOT"

# files that MUST exist + be SHA-verified for a v3.5 run
PACKAGE_LAYOUT = {
    "corpus_v1": "corpus_env/corpus_v1.jsonl",
    "donor_index": "corpus_env/donor_index.jsonl",
    "library": "library/library_full.jsonl",
    "calibrator_v34": "calibrators/calibrator_v34.json",
    "calibrator_v35": "calibrators/calibrator_v35.json",
    "ranker_uspto": "rankers/uspto_ranker.txt",
    "ranker_envipath": "rankers/envipath_ranker.txt",
    "ranker_retrieval": "rankers/retrieval_ranker.txt",
    "manifest": "MANIFEST.sha256",
}
REPO_LAYOUT = {
    "corpus_v1": "reaction_analogy/data/corpus_env/corpus_v1.jsonl",
    "donor_index": "reaction_analogy/data/corpus_env/donor_index.jsonl",
    "library": "reaction_analogy/data/env_expand/library_full.jsonl",
    "calibrator_v34": "data/bbd_v34/calibrator_v34.json",
    "calibrator_v35": "data/bbd_v34/calibrator_v35.json",
    "ranker_uspto": "data/bbd_v31/uspto_ranker.txt",
    "ranker_envipath": "data/bbd_v31/envipath_ranker.txt",
    "ranker_retrieval": "data/bbd_v31/retrieval_ranker.txt",
    "manifest": "reaction_analogy/data/env_expand/CORPUS_ENV.sha256",
}


class EnvAssetError(RuntimeError):
    """Fail-closed asset resolution error (P0-1 contract)."""


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest(path: str) -> dict[str, str]:
    """Parse "<sha256>  <relative path>" lines -> {relpath: sha256}."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            out[parts[1].strip().lstrip("*")] = parts[0]
    return out


def resolve_env_data_root(cli_root: str | None = None) -> tuple[str, str]:
    """Resolve the environmental asset root.

    Returns (root, mode) where mode is "cli" | "env" | "repo".  Raises
    EnvAssetError when nothing usable exists (fail-closed BEFORE any
    corpus loading; never falls back to the legacy corpus_v1).
    """
    if cli_root:
        if not os.path.isdir(cli_root):
            raise EnvAssetError(
                f"--env-data-root does not exist: {cli_root}")
        return os.path.abspath(cli_root), "cli"
    env_root = os.environ.get(ENV_DATA_ROOT_ENV)
    if env_root:
        if not os.path.isdir(env_root):
            raise EnvAssetError(
                f"{ENV_DATA_ROOT_ENV} does not exist: {env_root}")
        return os.path.abspath(env_root), "env"
    # repo-relative dev staging: only usable when corpus_env is staged
    if os.path.isfile(os.path.join(_REPO, REPO_LAYOUT["corpus_v1"])):
        return _REPO, "repo"
    raise EnvAssetError(
        "v3.5 environmental runtime assets not found. This fresh clone does "
        "not ship corpus_env (repo policy: large regenerable assets stay out "
        "of git). Fix: (a) install the versioned runtime-asset package "
        "depending_v35_environment_runtime_assets_<date>.tar.gz and pass "
        "--env-data-root <dir>, or (b) set "
        f"{ENV_DATA_ROOT_ENV}=<dir>, or (c) stage "
        "reaction_analogy/data/corpus_env/ from the package. "
        "There is NO silent fallback to the legacy corpus.")


def _layout_for(root: str) -> dict[str, str]:
    """Package layout if the root looks like a package, else repo layout."""
    if os.path.isfile(os.path.join(root, PACKAGE_LAYOUT["manifest"])):
        return PACKAGE_LAYOUT
    return REPO_LAYOUT


def verify_env_assets(root: str, mode: str) -> dict:
    """Verify presence + SHA256 of every required asset.  Fail-closed.

    Returns an identity dict for run_report.json:
      {asset_mode, corpus_v1_path/sha256/bytes, donor_index_*, library_*,
       calibrator_v34_*, calibrator_v35_*}
    Raises EnvAssetError on any missing file or SHA mismatch.
    """
    layout = _layout_for(root)
    files: dict[str, str] = {}
    for key in ("corpus_v1", "donor_index", "library",
                "calibrator_v34", "calibrator_v35",
                "ranker_uspto", "ranker_envipath", "ranker_retrieval"):
        p = os.path.join(root, layout[key])
        if not os.path.isfile(p):
            raise EnvAssetError(
                f"environmental runtime asset missing: {p} "
                f"(root={root}, mode={mode}) — aborting (fail-closed).")
        files[key] = p

    manifest_path = os.path.join(root, layout["manifest"])
    if not os.path.isfile(manifest_path):
        raise EnvAssetError(
            f"asset manifest missing: {manifest_path} (root={root}) — "
            f"aborting (fail-closed).")
    expected = _read_manifest(manifest_path)

    identity: dict = {"asset_mode": mode, "asset_root": root}
    for key, p in files.items():
        actual = _sha256(p)
        rel = os.path.relpath(p, root)
        want = expected.get(rel)
        if want is None:
            raise EnvAssetError(
                f"asset not listed in manifest (manifest={manifest_path}, "
                f"entry={rel}) — aborting (fail-closed).")
        if want != actual:
            raise EnvAssetError(
                f"asset SHA mismatch: {p}\n  manifest={want}\n  actual  ="
                f"{actual} — aborting (fail-closed).")
        identity[f"{key}_path"] = p
        identity[f"{key}_sha256"] = actual
        identity[f"{key}_bytes"] = os.path.getsize(p)
    return identity


def resolve_and_verify(cli_root: str | None = None) -> dict:
    """Resolve + verify in one call.  Returns the identity dict.

    On ANY failure prints the error and raises EnvAssetError; callers must
    exit non-zero (see the entries — they never continue on this error).
    """
    root, mode = resolve_env_data_root(cli_root)
    return verify_env_assets(root, mode)


def calibrator_path(identity: dict, version: str) -> str:
    """Explicit calibrator selection (P0-2): 'v34' -> v34 json, 'v35' ->
    v35 json.  No directory-scanning, no auto-upgrade, ever."""
    key = f"calibrator_{version}_path"
    if key not in identity:
        raise EnvAssetError(
            f"unknown calibrator version {version!r} "
            f"(identity keys: {sorted(identity)})")
    return identity[key]


if __name__ == "__main__":
    # manual probe: python env_asset_root.py [--env-data-root DIR]
    root_arg = sys.argv[sys.argv.index("--env-data-root") + 1] \
        if "--env-data-root" in sys.argv else None
    try:
        ident = resolve_and_verify(root_arg)
        print("ASSETS OK")
        for k in sorted(ident):
            print(f"  {k}: {ident[k]}")
    except EnvAssetError as e:
        print(f"ASSETS FAIL-CLOSED: {e}", file=sys.stderr)
        sys.exit(2)
