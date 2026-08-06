"""P4-R1-G typed feature observation (final_design §16.1).

A ``FeatureObservation`` replaces the raw structural-context dict: every
feature carries its ordinal, the REAL evidence ids that produced it, the
source stage/artifact hash and the run namespace. An ordinal with no
evidence binding is NOT automatically strong support — it is a bare scalar
that can only contribute to ``unknown``/fail-closed decisions.
"""
from __future__ import annotations

from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class FeatureObservation(StrictModel):
    """One evidence-bound structural observation for one feature."""
    feature_key: NonEmptyStr
    ordinal: int | None = None
    evidence_ids: list[NonEmptyStr] = []
    source_stage: str = ""
    source_artifact_hash: str = ""
    namespace: dict = {}

    @property
    def is_observable(self) -> bool:
        return self.ordinal is not None