"""Eligibility / quarantine engine package (final_design §10.4, ADR-0004).

Re-exports the public API. The single policy authority is
``reaction_agent.policies.partial_eligibility`` — this package classifies
evidence into a matrix state and delegates eligibility/bucket/quarantine
decisions to ``get_row(state)``. It does NOT duplicate the matrix.
"""

from reaction_agent.eligibility.engine import (
    decide_eligibility,
    build_quarantine_record,
    ENGINE_VERSION,
)

__all__ = ["decide_eligibility", "build_quarantine_record", "ENGINE_VERSION"]
