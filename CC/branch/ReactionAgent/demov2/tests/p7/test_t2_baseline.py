"""T2 RED tests — mandatory baseline gate (final_plan §10.3).

Must FAIL (RED) until ``reaction_agent/agent/baseline.py`` exists.

Scope (final_plan §10.3):
- Agent loop's FIRST step must obtain a deterministic baseline run via MCP
  predict. Bypass paths are all typed-rejected:
  1. skip baseline
  2. direct call to the low-level structure generator
  3. access to test labels
- P7-T0②-02 contract: a blocked-kernel baseline failure surfaces as a TYPED
  failure (never a bare exception piercing the agent loop).
"""
from __future__ import annotations

import pytest

from reaction_agent.agent.baseline import (
    BaselineGate,
    BaselineViolationError,
    SkipBaselineError,
    DirectStructureGeneratorError,
    LabelAccessViolationError,
)
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import (
    TOOL_PREDICT,
    ReactionMCPKernel,
    resolve_prediction_result,
)
from reaction_agent.schemas.result import PredictionResult


def _completed_result(run_id: str = "run_baseline") -> PredictionResult:
    from reaction_agent.schemas.candidate import Candidate
    from reaction_agent.schemas.common import DecisionKind, Lane, ResultStatus

    return PredictionResult(
        run_id=run_id,
        status=ResultStatus.completed,
        decision=DecisionKind.predicted,
        normalized_query="CCCCCCCCO",
        snapshot_id="snap_baseline",
        candidates=[Candidate(
            candidate_id="c1",
            canonical_product="C",
            lane=Lane.strict,
            origin="test",
        )],
    )


def _make_gate(tmp_path, predictor):
    runs = RunStore(tmp_path / "runs")
    idem = IdempotencyStore(tmp_path / "idem")
    kernel = ReactionMCPKernel(
        run_store=runs, idem_store=idem, predictor=predictor
    )
    gate = BaselineGate(
        kernel=kernel,
        run_store=runs,
        predict_payload={
            "substrate_smiles": "CCCCCCCCO",
            "idempotency_key": "k_t2_baseline",
            "snapshot_id": "snap_baseline",
        },
    )
    return gate


# -- mandatory baseline via MCP predict --

class TestMandatoryBaseline:
    def test_baseline_obtained_via_mcp_predict(self, tmp_path):
        gate = _make_gate(tmp_path, lambda payload: _completed_result())
        result = gate.obtain_baseline()
        assert isinstance(result, PredictionResult)
        assert result.run_id == "run_baseline"

    def test_skip_baseline_when_none_obtained(self, tmp_path):
        gate = _make_gate(tmp_path, lambda payload: _completed_result())
        # No obtain_baseline call yet -> agent step must be typed-rejected.
        with pytest.raises(SkipBaselineError):
            gate.require_baseline()

    def test_skip_baseline_is_typed_violation(self):
        assert issubclass(SkipBaselineError, BaselineViolationError)


# -- bypass pins: skip baseline / direct structure generator / test labels --

class TestBypassPins:
    def test_direct_structure_generator_rejected(self, tmp_path):
        gate = _make_gate(tmp_path, lambda payload: _completed_result())
        with pytest.raises(DirectStructureGeneratorError):
            gate.reject_direct_structure_generator()

    def test_direct_structure_generator_typed(self):
        assert issubclass(DirectStructureGeneratorError, BaselineViolationError)

    def test_test_label_access_rejected(self, tmp_path):
        gate = _make_gate(tmp_path, lambda payload: _completed_result())
        with pytest.raises(LabelAccessViolationError):
            gate.reject_test_label_access()

    def test_test_label_access_typed(self):
        assert issubclass(LabelAccessViolationError, BaselineViolationError)


# -- P7-T0②-02: blocked-kernel baseline failure is TYPED, not bare exception --

class TestBlockedKernelTyped:
    def test_blocked_kernel_failure_is_typed(self, tmp_path):
        """A predictor that raises (blocked kernel) must surface as a typed
        BaselineViolationError, never a bare exception piercing the loop."""
        def failing_predictor(payload):
            raise RuntimeError("kernel blocked")

        gate = _make_gate(tmp_path, failing_predictor)
        with pytest.raises(BaselineViolationError):
            gate.obtain_baseline()

    def test_blocked_kernel_not_bare_runtime_error(self, tmp_path):
        def failing_predictor(payload):
            raise RuntimeError("kernel blocked")

        gate = _make_gate(tmp_path, failing_predictor)
        try:
            gate.obtain_baseline()
        except BaselineViolationError:
            pass  # expected typed
        except Exception as exc:  # noqa: BLE001
            pytest.fail(
                f"blocked kernel leaked bare {type(exc).__name__}: "
                f"{exc} (must be typed BaselineViolationError)"
            )

    def test_resolution_failure_is_typed(self, tmp_path):
        """A run whose resolution fails (missing in the gate's store) must be
        a typed BaselineViolationError, never a bare RunNotFoundError.

        Real sabotage: the kernel writes the run into ``kernel_runs``, but the
        gate resolves against a SEPARATE empty store ``gate_runs`` — so
        ``resolve_prediction_result`` genuinely raises RunNotFoundError, which
        the widened envelope folds into a typed BaselineViolationError.
        """
        from reaction_agent.agent.baseline import BaselineGate as G
        from reaction_agent.mcp.errors import RunNotFoundError
        from reaction_agent.mcp.idempotency import IdempotencyStore as IS
        from reaction_agent.mcp.runs import RunStore as RS
        from reaction_agent.mcp.tools import ReactionMCPKernel as K

        payload = {
            "substrate_smiles": "CCCCCCCCO",
            "idempotency_key": "k_t2_res_missing",
            "snapshot_id": "snap_baseline",
        }
        kernel_runs = RS(tmp_path / "runs_kernel")
        gate_runs = RS(tmp_path / "runs_gate")  # separate, EMPTY
        idem = IS(tmp_path / "idem_kernel")
        kernel = K(
            run_store=kernel_runs,
            idem_store=idem,
            predictor=lambda p: _completed_result(),
        )
        gate = G(
            kernel=kernel,
            run_store=gate_runs,
            predict_payload=payload,
        )

        # Precondition: the kernel writes the run into kernel_runs, but the
        # gate's store is empty -> resolve_prediction_result must raise.
        out = kernel.handle(TOOL_PREDICT, payload)
        run_id = out["run_id"]
        with pytest.raises(RunNotFoundError):
            gate_runs.get_run(run_id)

        with pytest.raises(BaselineViolationError):
            gate.obtain_baseline()

    def test_require_baseline_returns_deep_copy(self, tmp_path):
        """require_baseline returns a deep copy so callers cannot mutate the
        cached baseline (immutability contract)."""
        gate = _make_gate(tmp_path, lambda payload: _completed_result())
        gate.obtain_baseline()
        b1 = gate.require_baseline()
        b2 = gate.require_baseline()
        assert b1 is not b2  # distinct objects
        b1.normalized_query = "MUTATED"
        assert gate.require_baseline().normalized_query == "CCCCCCCCO"