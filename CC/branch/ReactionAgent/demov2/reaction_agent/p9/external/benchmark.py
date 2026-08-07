"""P9-T3: Benchmark default off + lane non-contamination (Phase A criteria 7-8).

- benchmark default off: external evidence is NOT included in the default
  benchmark; it must be explicitly enabled (``include_external=True``).
- lane non-contamination: external records carry a pinned ``lane="external"``
  (Literal) so they can never be promoted into the strict lane's candidate set.
"""
from __future__ import annotations

from reaction_agent.schemas.common import StrictModel


class BenchmarkConfig(StrictModel):
    """Benchmark configuration. External evidence is OFF by default."""

    include_external: bool = False


def is_external_in_benchmark(cfg: BenchmarkConfig) -> bool:
    """Whether external evidence participates in a benchmark run.

    Default is False (benchmark default off). Only an explicit opt-in enables
    external evidence.
    """
    return cfg.include_external