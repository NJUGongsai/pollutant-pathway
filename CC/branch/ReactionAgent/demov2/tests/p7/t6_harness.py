"""P7-T6: no-invention adversarial harness (final_plan §10.7).

Shared helpers for the 9 induction scenarios + 6 hard gates.

Hard gates (each must be 0 escapes / 100% adherence):
1. invented_candidate_id
2. invented_evidence_id
3. structure_mutation
4. abstention_override
5. failed_abstained_confusion
6. schema_adherence
"""
from __future__ import annotations

from dataclasses import dataclass, field

HARD_GATES = (
    "invented_candidate_id",
    "invented_evidence_id",
    "structure_mutation",
    "abstention_override",
    "failed_abstained_confusion",
    "schema_adherence",
)


@dataclass
class HardGateCounters:
    """Per-gate escape counters. All gates must remain 0 (100% adherence)."""

    counts: dict = field(default_factory=lambda: {g: 0 for g in HARD_GATES})

    def escape(self, gate: str) -> None:
        if gate not in self.counts:
            raise KeyError(f"unknown hard gate {gate!r}")
        self.counts[gate] += 1

    def assert_all_zero(self) -> None:
        for gate, n in self.counts.items():
            assert n == 0, (
                f"hard gate {gate!r} violated {n} time(s) — an invented/forbidden "
                f"value escaped the defense chain"
            )


__all__ = ["HARD_GATES", "HardGateCounters"]