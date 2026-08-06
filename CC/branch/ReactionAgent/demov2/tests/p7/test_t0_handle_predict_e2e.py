"""P7 T0② handle_predict end-to-end pin (RED first).

Asserts criterion (6): ``handle_predict`` runs the deterministic predictor
(P3 kernel → bridge → P4 pipeline) and the resulting run manifest resolves a
typed ``PredictionResult``.

RED until ``reaction_agent.adapters.p3_p4_bridge.run_deterministic_predict``
and the ``predictor`` hook on ``ReactionMCPKernel`` (+ the
``resolve_prediction_result`` helper) are implemented.
"""
from __future__ import annotations

from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import TOOL_PREDICT, ReactionMCPKernel
from reaction_agent.schemas.result import PredictionResult


def test_handle_predict_produces_typed_prediction_result(tmp_path):
    from reaction_agent.adapters.p3_p4_bridge import run_deterministic_predict
    from reaction_agent.mcp.tools import resolve_prediction_result

    runs = RunStore(tmp_path / "runs")
    idem = IdempotencyStore(tmp_path / "idem")
    artifact = tmp_path / "current_run.json"

    def predictor(payload: dict) -> PredictionResult:
        return run_deterministic_predict(
            payload, current_run_path=str(artifact)
        )

    kernel = ReactionMCPKernel(
        run_store=runs, idem_store=idem, predictor=predictor
    )

    out = kernel.handle(
        TOOL_PREDICT,
        {
            "substrate_smiles": "CCCCCCCCO",
            "idempotency_key": "k_e2e_1",
            "snapshot_id": "snap_pin",
        },
    )

    # Existing P6 return contract preserved (additive wiring).
    assert out["run_id"]
    assert out["manifest_uri"].startswith("reactionagent://runs/")
    assert out["status"] == "frozen"

    # NEW (T0②): typed PredictionResult resolvable from the run.
    result = resolve_prediction_result(runs, out["run_id"])
    assert isinstance(result, PredictionResult), (
        "run manifest must resolve a typed PredictionResult"
    )
    assert result.status.value in {"completed", "abstained", "failed"}


def test_handle_predict_without_predictor_preserves_p6_behavior(tmp_path):
    """With no predictor wired, handle_predict keeps the P6 run-lifecycle
    behavior (no PredictionResult) — additive, no regression."""
    runs = RunStore(tmp_path / "runs")
    idem = IdempotencyStore(tmp_path / "idem")
    kernel = ReactionMCPKernel(run_store=runs, idem_store=idem)

    out = kernel.handle(
        TOOL_PREDICT,
        {
            "substrate_smiles": "CCO",
            "idempotency_key": "k_p6_1",
            "snapshot_id": "snap_p6",
        },
    )
    assert out["status"] == "frozen"
    assert resolve_prediction_result(runs, out["run_id"]) is None
