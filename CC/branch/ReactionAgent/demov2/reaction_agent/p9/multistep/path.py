"""P9-T4: Path utilities — dedup, uncertainty, canonical signatures.

``canonical_path_signature`` produces a hashable signature for a path (used for
dedup). ``PathDedup`` tracks unique paths and alternative path counts per
target molecule.
"""
from __future__ import annotations

from collections import defaultdict

from reaction_agent.hashing import canonical_hash
from reaction_agent.p9.multistep.schemas import MultiStepPath, PathUncertainty


def canonical_path_signature(path: MultiStepPath) -> str:
    """Compute a canonical, hashable signature for a path.

    The signature is based on the ordered sequence of nodes (canonical SMILES)
    and edge IDs. Two paths with the same nodes and edges in the same order
    have the same signature.
    """
    return canonical_hash({
        "nodes": path.nodes,
        "edge_ids": path.edge_ids,
    })


class PathDedup:
    """Deduplicate paths and track alternative path counts per target molecule.

    Usage::

        dedup = PathDedup()
        dedup.add(path1)
        dedup.add(path2)
        count = dedup.alternative_paths(target_mol)  # number of distinct paths
        uncertainty = dedup.uncertainty(target_mol)  # PathUncertainty object
    """

    def __init__(self) -> None:
        self._signatures: set[str] = set()
        self._target_counts: dict[str, int] = defaultdict(int)

    def add(self, path: MultiStepPath) -> bool:
        """Add a path. Returns True if it was new (not a duplicate)."""
        sig = canonical_path_signature(path)
        if sig in self._signatures:
            return False
        self._signatures.add(sig)
        # Count paths to each target
        if path.nodes:
            target = path.nodes[-1]
            self._target_counts[target] += 1
        return True

    def alternative_paths(self, target_molecule: str) -> int:
        """Number of distinct paths reaching the target molecule."""
        return self._target_counts.get(target_molecule, 0)

    def uncertainty(self, target_molecule: str) -> PathUncertainty:
        """Get a PathUncertainty object for a target molecule."""
        return PathUncertainty(
            target_molecule=target_molecule,
            alternative_paths=self.alternative_paths(target_molecule),
        )

    def __contains__(self, path: MultiStepPath) -> bool:
        sig = canonical_path_signature(path)
        return sig in self._signatures