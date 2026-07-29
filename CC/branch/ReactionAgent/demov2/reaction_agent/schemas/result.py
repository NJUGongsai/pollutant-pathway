"""PredictionResult schema with complete cross-field state machine.

Four states with strict invariants (final_design §22.5, ADR-0005):

completed:
  status=completed, decision=predicted, candidates>=1
  abstention=null, failure=null, partial_reason=null

abstained:
  status=abstained, decision=abstained, candidates=0
  abstention with scientific reason required
  failure=null, partial_reason=null

partial:
  status=partial, decision=partial
  partial_reason required and non-empty
  failure=null

failed:
  status=failed, decision=failed
  failure with system reason required
  abstention=null (NEVER scientific abstention on failed)
"""

from reaction_agent.schemas.common import (
    StrictModel,
    NonEmptyStr,
    ResultStatus,
    DecisionKind,
    ScientificAbstentionReason,
    SystemFailureReason,
)
from reaction_agent.schemas.candidate import Candidate
from pydantic import model_validator


class Abstention(StrictModel):
    """Scientific abstention record."""
    reason_code: ScientificAbstentionReason
    stage: str = ""
    detail: str = ""


class Failure(StrictModel):
    """System/infrastructure failure record.
    Must NEVER use scientific abstention reasons."""
    reason_code: SystemFailureReason
    detail: str = ""


class StageSummary(StrictModel):
    """D→T→S→Δ→Y→L→R/A audit trace (final_design §20)."""
    donor_evidence_ids: list[NonEmptyStr] = []
    transformation_hypothesis_ids: list[NonEmptyStr] = []
    site_hypothesis_ids: list[NonEmptyStr] = []
    graph_edit_ids: list[NonEmptyStr] = []
    candidate_ids: list[NonEmptyStr] = []
    ledger_ids: list[NonEmptyStr] = []
    rank_result: dict[str, str] = {}
    decision_result: dict[str, str] = {}


class PredictionResult(StrictModel):
    """Final prediction result with enforced state machine invariants.

    State machine:
    ┌───────────┬────────────┬───────────┬───────────┬────────────────┬─────────┐
    │ status    │ decision   │ candidates│ abstention│ failure        │ partial │
    ├───────────┼────────────┼───────────┼───────────┼────────────────┼─────────┤
    │ completed │ predicted  │ >=1       │ null      │ null           │ null    │
    │ abstained │ abstained  │ 0         │ required  │ null           │ null    │
    │ partial   │ partial    │ any       │ optional* │ null           │ required│
    │ failed    │ failed     │ any       │ null      │ required(sys)  │ null    │
    └───────────┴────────────┴───────────┴───────────┴────────────────┴─────────┘

    * partial: abstention allowed but not required per final_design.
    """
    run_id: NonEmptyStr
    status: ResultStatus
    decision: DecisionKind
    normalized_query: NonEmptyStr
    snapshot_id: NonEmptyStr
    candidates: list[Candidate] = []
    abstention: Abstention | None = None
    partial_reason: str | None = None
    failure: Failure | None = None
    stage_summary: StageSummary | None = None
    manifest_uri: NonEmptyStr = "pending"
    resource_uris: list[NonEmptyStr] = []

    @model_validator(mode="after")
    def enforce_state_machine(self):
        s = self.status
        d = self.decision

        # -- status/decision must match --
        status_decision_map = {
            ResultStatus.completed: DecisionKind.predicted,
            ResultStatus.abstained: DecisionKind.abstained,
            ResultStatus.partial: DecisionKind.partial,
            ResultStatus.failed: DecisionKind.failed,
        }
        expected_decision = status_decision_map.get(s)
        if d != expected_decision:
            raise ValueError(
                f"status={s.value} requires decision={expected_decision.value}, "
                f"got decision={d.value}"
            )

        # -- completed --
        if s == ResultStatus.completed:
            if len(self.candidates) < 1:
                raise ValueError("completed status requires at least 1 candidate")
            if self.abstention is not None:
                raise ValueError("completed status must not have abstention")
            if self.failure is not None:
                raise ValueError("completed status must not have failure")
            if self.partial_reason is not None:
                raise ValueError("completed status must not have partial_reason")

        # -- abstained --
        elif s == ResultStatus.abstained:
            if len(self.candidates) != 0:
                raise ValueError("abstained status requires 0 candidates")
            if self.abstention is None:
                raise ValueError("abstained status requires abstention with scientific reason")
            if self.failure is not None:
                raise ValueError("abstained status must not have failure")
            if self.partial_reason is not None:
                raise ValueError("abstained status must not have partial_reason")

        # -- partial --
        elif s == ResultStatus.partial:
            if self.partial_reason is None or self.partial_reason == "":
                raise ValueError("partial status requires non-empty partial_reason")
            if self.failure is not None:
                raise ValueError("partial status must not have failure")

        # -- failed --
        elif s == ResultStatus.failed:
            if self.failure is None:
                raise ValueError("failed status requires failure with system reason")
            if self.abstention is not None:
                raise ValueError(
                    "failed status must not have scientific abstention"
                )
            if self.partial_reason is not None:
                raise ValueError("failed status must not have partial_reason")

        return self
