"""BBD_DATA_ROOT — migrated data-asset resolver (T6-2 data migration, 2026-09-15).

Assets that left the git repo for the Hugging Face dataset
``WQRCE/EnzymeCAGE-bbd-data`` (private; teacher-side hosted) and are resolved
here, with repo-relative fallback for still-in-repo assets:

  reaction_analogy/data/corpus_v1/    retrieval corpus (runtime, Engine C)
  data/bbd_v31/*.txt                  v3.1 per-source rankers (runtime)
  data/bbd_v3/ranker_model.txt        v3 ranker (legacy predict chain)
  data/bbd_v5/eawag_candidates.jsonl  EAWAG train cache (v5 ranker training)
  bbd_predictions/ v2/v3/v31 pools    historical eval pools (scorer inputs)

Resolution order for ``resolve("<repo-relative path>")``:

  1. ``$BBD_DATA_ROOT/<repo-relative path>``  — HF cache download directory
     (same relative layout as the repo), if it exists;
  2. the repo-relative path itself — still-tracked assets and pre-migration
     checkouts keep working unchanged (fail-open to the historical layout).

Set ``BBD_DATA_ROOT`` to the local HF dataset cache dir, e.g.::

  export BBD_DATA_ROOT=~/hf_cache/EnzymeCAGE-bbd-data
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, ".."))


def resolve(repo_rel: str) -> str:
    """Resolve a repo-relative data path against BBD_DATA_ROOT, then repo."""
    root = os.environ.get("BBD_DATA_ROOT")
    if root:
        cand = os.path.join(root, repo_rel)
        if os.path.exists(cand):
            return cand
    return os.path.join(_REPO, repo_rel)
