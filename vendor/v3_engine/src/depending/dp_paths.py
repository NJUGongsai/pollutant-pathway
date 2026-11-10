"""dependingv3 central path resolution — the SINGLE source of truth.

Kills the historical hardcoded ``/Volumes/CC/Enzyme_Agent/depending`` ROOT
(19 files carried it in dependingv2).  All engine-side assets live under
``<repo>/assets/`` which is the unpacked 2026-09-18 frozen runtime-asset
package (corpus_env / library / calibrators / rankers / MANIFEST.sha256 —
fail-closed verified by ``env_asset_root`` at runtime) extended with the
engine assets that stayed repo-side (templates / envipath / eawag).

Override for deployments (remote etc.)::

    export DEPENDING_V3_ROOT=/path/to/dependingv3
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))

REPO_ROOT = os.environ.get("DEPENDING_V3_ROOT") or os.path.normpath(
    os.path.join(_HERE, "..", ".."))
ASSETS = os.path.join(REPO_ROOT, "assets")


def asset(*parts: str) -> str:
    """Absolute path under assets/ (e.g. asset('rankers', 'uspto_ranker.txt'))."""
    return os.path.join(ASSETS, *parts)
