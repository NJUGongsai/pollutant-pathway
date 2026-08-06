"""P7 T7 agent incremental evaluation pin tests (RED first).

T7 evolves the agent loop from a skeleton into a real run that consumes a
(scripted) provider's action stream to drive expand/compare/choose/prioritize/
stop over a mandatory baseline. It then runs a three-way comparison
(deterministic baseline / agent evidence expansion+selection / fixed non-agent
expansion) over 7 metrics, and closes P7-T6-02 via an end-to-end provider-
scripted induction proving all 6 hard gates stay zero.

RED until ``AgentLoop.run`` + ``reaction_agent/agent/evaluation.py`` land.
"""
from __future__ import annotations

import json
import os

import pytest

from reaction_agent.agent.baseline import BaselineGate
from reaction_agent.agent.loop import AgentLoop
from reaction_agent.agent.provider import FakeProvider, ProviderSpec
from reaction_agent.mcp.idempotency import IdempotencyStore
from reaction_agent.mcp.runs import RunStore
from reaction_agent.mcp.tools import ReactionMCPKernel
from reaction_agent.adapters.p3_p4_bridge import run_deterministic_predict
from tests.p7.t6_harness import HardGateCounters

SUBSTRATE = "CCCCCCCCO"
SNAP = "snap_t7"


def _make_gate(tmp_path) -> BaselineGate:
    runs = RunStore(tmp_path / "runs")
    idem = IdempotencyStore(tmp_path / "idem")
    artifact = tmp_path / "cra.json"

    def predictor(payload):
        return run_deterministic_predict(payload, current_run_path=str(artifact))

    kernel = ReactionMCPKernel(run_store=runs, idem_store=idem, predictor=predictor)
    return BaselineGate(
        kernel=kernel,
        run_store=runs,
        predict_payload={
            "substrate_smiles": SUBSTRATE,
            "idempotency_key": "k_t7",
            "snapshot_id": SNAP,
        },
    )


def _baseline_candidate_ids(gate) -> list[str]:
    r = gate.obtain_baseline()
    return [c.candidate_id for c in r.candidates]


def _baseline_evidence_ids(gate) -> list[str]:
    r = gate.obtain_baseline()
    return list(r.stage_summary.donor_evidence_ids) if r.stage_summary else []


@pytest.fixture
def gate(tmp_path):
    return _make_gate(tmp_path)


@pytest.fixture
def baseline_ids(gate):
    return _baseline_candidate_ids(gate)


class TestRunConsumesProvider:
    def test_run_drives_valid_actions_and_selects(self, gate, baseline_ids):
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=10)
        actions = [
            {"tool": "expand_evidence", "evidence_id": _baseline_evidence_ids(gate)[0]},
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        provider = ScriptedProvider(spec, actions)
        loop = AgentLoop(provider=provider, baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=10)
        # baseline obtained first (mandatory)
        assert result.baseline is not None
        assert result.baseline.run_id
        # agent selected the chosen candidate
        assert baseline_ids[0] in result.selected_candidate_ids
        # tool calls recorded (expand + choose; stop ends)
        assert result.tool_calls >= 2
        assert result.abstained is False

    def test_run_abstains_when_no_choose(self, gate, baseline_ids):
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=10)
        actions = [{"tool": "prioritize", "candidate_id": baseline_ids[0]}, {"tool": "stop"}]
        loop = AgentLoop(provider=ScriptedProvider(spec, actions), baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=10)
        assert result.abstained is True  # no choose_t_s -> no selection -> abstained
        assert result.selected_candidate_ids == ()


class TestRunRejectsInventions:
    def test_invented_candidate_id_rejected_not_selected(self, gate, baseline_ids):
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=10)
        invented = "cand_NOT_IN_RUN"
        actions = [
            {"tool": "choose_t_s", "candidate_id": invented},
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        loop = AgentLoop(provider=ScriptedProvider(spec, actions), baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=10)
        # invented rejected — not in selection
        assert invented not in result.selected_candidate_ids
        # valid one still selected (run continued past rejection)
        assert baseline_ids[0] in result.selected_candidate_ids
        assert any(r["reason"] == "grounding" for r in result.rejections)

    def test_invented_evidence_id_rejected(self, gate, baseline_ids):
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=10)
        invented = "ev_NOT_IN_RUN"
        actions = [{"tool": "expand_evidence", "evidence_id": invented}, {"tool": "stop"}]
        loop = AgentLoop(provider=ScriptedProvider(spec, actions), baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=10)
        assert invented not in result.grounded_evidence_ids
        assert any(r["reason"] == "grounding" for r in result.rejections)

    def test_unauthorized_tool_rejected(self, gate, baseline_ids):
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=10)
        actions = [
            {"tool": "generate_structure", "smiles": "C1=CC=CC=C1INVENTED"},
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        loop = AgentLoop(provider=ScriptedProvider(spec, actions), baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=10)
        # forbidden tool rejected, run continued to the valid choose
        assert any(r["reason"] == "allowlist_violation" for r in result.rejections)
        assert baseline_ids[0] in result.selected_candidate_ids


class TestEndToEndInductionHardGates:
    def test_full_induction_hardgates_all_zero(self, gate, baseline_ids):
        """P7-T6-02: a provider scripting the full induction set (invented
        candidate/evidence ID + unauthorized tool-call) through a complete
        agent run -> all 6 hard gates stay zero (every invention rejected).
        Pre-assertion: the scripted actions DO contain the inventions."""
        from reaction_agent.agent.evaluation import ScriptedProvider

        spec = ProviderSpec(provider="fake", model="m", max_calls=20)
        invented_cand = "cand_INVENTED_xyz"
        invented_ev = "ev_INVENTED_xyz"
        invented_smiles = "C1=CC=CC=C1INVENTED"
        actions = [
            {"tool": "expand_evidence", "evidence_id": invented_ev},
            {"tool": "choose_t_s", "candidate_id": invented_cand},
            {"tool": "generate_structure", "smiles": invented_smiles},
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        # PRE-ASSERTION: the induction is real (inventions are in the script)
        scripted_tools = [a["tool"] for a in actions]
        assert "generate_structure" in scripted_tools
        assert invented_cand in [a.get("candidate_id") for a in actions]
        assert invented_ev in [a.get("evidence_id") for a in actions]
        # none of the invented IDs are in the run
        assert invented_cand not in baseline_ids

        counters = HardGateCounters()
        loop = AgentLoop(provider=ScriptedProvider(spec, actions), baseline_gate=gate)
        result = loop.run(SUBSTRATE, max_steps=20, counters=counters)
        # 6 hard gates all zero (every invention rejected, none escaped)
        counters.assert_all_zero()
        # final selection has NO invented IDs
        assert invented_cand not in result.selected_candidate_ids
        assert invented_ev not in result.grounded_evidence_ids
        # the one valid choose still landed
        assert baseline_ids[0] in result.selected_candidate_ids


class TestThreeWayAndMetrics:
    def test_three_way_comparison(self, gate, baseline_ids, tmp_path):
        from reaction_agent.agent.evaluation import (
            run_three_way,
            ScriptedProvider,
        )
        from reaction_agent.agent.provider import ProviderSpec

        spec = ProviderSpec(provider="fake", model="m", max_calls=20)
        agent_actions = [
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        three = run_three_way(
            SUBSTRATE,
            agent_actions,
            baseline_gate=gate,
            agent_provider=ScriptedProvider(spec, agent_actions),
            runs=3,
        )
        assert three.baseline is not None
        assert three.agent is not None
        assert three.fixed is not None
        # all three carry the same run namespace (same substrate)
        assert three.baseline.normalized_query == SUBSTRATE

    def test_metrics_candidate_recall_and_tool_calls(self, gate, baseline_ids, tmp_path):
        from reaction_agent.agent.evaluation import (
            ScriptedProvider,
            compute_metrics,
            run_three_way,
        )
        from reaction_agent.agent.provider import ProviderSpec

        spec = ProviderSpec(provider="fake", model="m", max_calls=20)
        agent_actions = [
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        three = run_three_way(
            SUBSTRATE, agent_actions, baseline_gate=gate,
            agent_provider=ScriptedProvider(spec, agent_actions),
            runs=3,
        )
        m = compute_metrics(three)
        # 7 metrics present
        for name in (
            "candidate_recall", "ranking_risk", "abstention", "evidence_quality",
            "tool_calls", "latency_token_cost", "repeated_run_agreement",
        ):
            assert hasattr(m, name), f"metric {name!r} missing"
        # agent selected the baseline's first candidate -> recall >= 1/N
        assert m.candidate_recall > 0.0
        assert m.tool_calls >= 1
        # determinism: repeated runs identical
        assert m.repeated_run_agreement is True

    def test_report_written_and_traceable(self, gate, baseline_ids, tmp_path):
        from reaction_agent.agent.evaluation import (
            ScriptedProvider,
            compute_metrics,
            run_three_way,
            write_report,
        )
        from reaction_agent.agent.provider import ProviderSpec

        spec = ProviderSpec(provider="fake", model="m", max_calls=20)
        agent_actions = [
            {"tool": "choose_t_s", "candidate_id": baseline_ids[0]},
            {"tool": "stop"},
        ]
        three = run_three_way(
            SUBSTRATE, agent_actions, baseline_gate=gate,
            agent_provider=ScriptedProvider(spec, agent_actions),
            runs=2,
        )
        out = tmp_path / "reports" / "p7" / "t7_evaluation.json"
        write_report(three, compute_metrics(three), out)
        assert out.exists()
        data = json.loads(out.read_text())
        # data traceable to typed result (baseline run_id carried into report)
        assert data["baseline"]["run_id"] == three.baseline.run_id
        assert "metrics" in data
        assert "agent" in data and "fixed" in data
