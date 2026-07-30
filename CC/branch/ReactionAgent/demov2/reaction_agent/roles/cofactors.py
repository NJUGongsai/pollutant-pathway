"""Read-only COFACTORS loader (§11.3).

Legacy ``../benchmark/canonical_identity.py`` defines ``COFACTORS`` as a
``frozenset`` of canonical SMILES for common cofactors / carriers / small
inorganics. The module imports ``rdkit`` at the top, and rdkit is absent in
this environment (Preflight BLOCKED). Direct import would fail with
``ModuleNotFoundError``.

This loader extracts the ``COFACTORS`` literal via AST parsing — it reads the
source file, locates the ``COFACTORS = frozenset({...})`` assignment, and
collects the string constants. This:

- NEVER executes the legacy module (no rdkit dependency, no side effects).
- NEVER modifies the legacy file (read-only; SHA-256 verified pre+post).
- Records the source file SHA-256 so consumers can pin the prior provenance.

§11.3 discipline: the returned list is ONLY a prior. It must never be used to
delete a participant, assign a ground-truth role, exclude from atom balance,
or block a transformed lineage.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

# Legacy source path: ``../benchmark/canonical_identity.py`` relative to the
# ``demov2/`` project root. Resolved via Path so the loader works regardless
# of CWD. ``__file__`` = ``demov2/reaction_agent/roles/cofactors.py``;
# four ``.parent`` calls climb to ``ReactionAgent/`` where ``benchmark/``
# actually lives (confirmed by Preflight: relative_path ``../benchmark``).
LEGACY_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "benchmark"
    / "canonical_identity.py"
)

# Module-level cache: (sorted_names, source_hash). ``load_cofactors`` is
# deterministic and idempotent; caching avoids re-reading the file on every
# call. The cache is populated on first call and never mutated thereafter.
_CACHE: tuple[list[str], str] | None = None


def _extract_cofactors_literals(source: str) -> list[str]:
    """Extract the COFACTORS frozenset string literals via AST.

    Returns the list of string constants inside ``COFACTORS = frozenset({...})``.
    Raises ``ValueError`` if the assignment is not found or is not a frozenset
    of string constants (defensive: guards against legacy file restructuring).
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Name) and target.id == "COFACTORS"):
                continue
            value = node.value
            if not (isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "frozenset"):
                raise ValueError(
                    "COFACTORS is not a frozenset() call — legacy file "
                    "structure changed; loader must be updated"
                )
            if not value.args:
                raise ValueError("COFACTORS frozenset() has no argument")
            arg = value.args[0]
            if not isinstance(arg, ast.Set):
                raise ValueError(
                    "COFACTORS frozenset() argument is not a set literal"
                )
            literals: list[str] = []
            for elt in arg.elts:
                if not isinstance(elt, ast.Constant) or not isinstance(
                    elt.value, str
                ):
                    raise ValueError(
                        "COFACTORS contains a non-string constant — loader "
                        "only supports string SMILES literals"
                    )
                literals.append(elt.value)
            return literals
    raise ValueError(
        "COFACTORS assignment not found in legacy canonical_identity.py"
    )


def _compute_source_hash(path: Path) -> str:
    """SHA-256 of the legacy file bytes (content-addressed provenance)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cofactors() -> tuple[list[str], str]:
    """Load the legacy COFACTORS list as a prior, with source hash.

    Returns ``(sorted_unique_names, source_hash)`` where:
    - ``sorted_unique_names`` is the sorted, de-duplicated list of canonical
      SMILES strings from the legacy ``COFACTORS`` frozenset. These are the
      legacy canonical forms (produced by ``Chem.MolToSmiles``); re-
      canonicalization is deferred to rdkit (absent). Values are returned
      as-is per §11.3 "读取并 canonicalize COFACTORS list" — the legacy
      already canonicalized them.
    - ``source_hash`` is the SHA-256 of ``canonical_identity.py`` (matches
      the Preflight frozen reference ``6003f4bc…eb2d0``).

    The list is ONLY a prior (§11.3). Never use it to delete a participant,
    assign a ground-truth role, exclude from atom balance, or block a
    transformed lineage.

    Idempotent: repeated calls return identical results (cached).
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    if not LEGACY_PATH.exists():
        raise FileNotFoundError(
            f"legacy canonical_identity.py not found at {LEGACY_PATH}"
        )

    source = LEGACY_PATH.read_text(encoding="utf-8")
    raw_literals = _extract_cofactors_literals(source)
    # Sorted + de-duplicated for determinism. frozenset is already unique,
    # but sorting makes the output stable across Python versions / set order.
    sorted_unique = sorted(set(raw_literals))
    src_hash = _compute_source_hash(LEGACY_PATH)

    _CACHE = (sorted_unique, src_hash)
    return _CACHE
