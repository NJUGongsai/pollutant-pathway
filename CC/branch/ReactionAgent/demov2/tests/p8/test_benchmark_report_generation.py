"""T4 Round 2 RED tests — benchmark report generation reproducibility + frozen-policy pin.

Round 1 findings (SB-R1-01 / SB-R1-02):
- SB-R1-01: the committed benchmark report must pin the FROZEN relaxation
  policy artifact's content_hash — not an in-memory twin built via
  ``RelaxationPolicy.create()``. The report's policy.content_hash must equal
  ``load_policy(<frozen artifact>).content_hash``.
- SB-R1-02: there must be a committed, deterministic generation entry that
  regenerates ``reports/p8/`` from the frozen artifact (no one-off ad-hoc call).

Must FAIL (RED) until ``reaction_agent.p8.benchmark.generate_stage_b_demo_report``
exists.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reaction_agent.p8.policy import load_policy
from reaction_agent.p8.benchmark import (  # noqa: F401  (RED: absent)
    generate_stage_b_demo_report,
)

# Repo-relative paths — resolve from this test file so the assertions are
# independent of the pytest cwd.
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../demov2
FROZEN_POLICY_PATH = REPO_ROOT / "reports/p8/relaxation_policy_p8-generalized-relaxation_v1.0.0.json"
COMMITTED_JSON = REPO_ROOT / "reports/p8/p8_stage_b_benchmark.json"
COMMITTED_MD = REPO_ROOT / "reports/p8/P8_STAGE_B_BENCHMARK_REPORT.md"


class TestReportPinsFrozenPolicy:
    """SB-R1-01: the committed report must reference the FROZEN artifact."""

    def test_committed_report_hash_matches_frozen_artifact(self):
        frozen = load_policy(FROZEN_POLICY_PATH)
        committed = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        assert committed["policy"]["content_hash"] == frozen.content_hash, (
            "committed benchmark report pins a non-frozen (twin) policy "
            f"{committed['policy']['content_hash'][:12]}…; frozen artifact is "
            f"{frozen.content_hash[:12]}…"
        )

    def test_committed_report_policy_id_and_version_match(self):
        frozen = load_policy(FROZEN_POLICY_PATH)
        committed = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        assert committed["policy"]["policy_id"] == frozen.policy_id
        assert committed["policy"]["version"] == frozen.version


class TestGeneratorReproducibility:
    """SB-R1-02: a committed, deterministic generator reproduces the artifacts."""

    def test_generator_loads_frozen_artifact_not_twin(self, tmp_path: Path):
        frozen = load_policy(FROZEN_POLICY_PATH)
        md = tmp_path / "bench.md"
        js = tmp_path / "bench.json"
        generate_stage_b_demo_report(md, js, policy_path=FROZEN_POLICY_PATH)
        gen = json.loads(js.read_text(encoding="utf-8"))
        # the generator must load_policy() the frozen artifact — output hash == frozen
        assert gen["policy"]["content_hash"] == frozen.content_hash

    def test_generator_reproduces_committed_json(self, tmp_path: Path):
        md = tmp_path / "bench.md"
        js = tmp_path / "bench.json"
        generate_stage_b_demo_report(md, js, policy_path=FROZEN_POLICY_PATH)
        committed = json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))
        generated = json.loads(js.read_text(encoding="utf-8"))
        assert generated == committed

    def test_generator_reproduces_committed_md(self, tmp_path: Path):
        md = tmp_path / "bench.md"
        js = tmp_path / "bench.json"
        generate_stage_b_demo_report(md, js, policy_path=FROZEN_POLICY_PATH)
        assert md.read_text(encoding="utf-8") == COMMITTED_MD.read_text(encoding="utf-8")

    def test_generator_is_deterministic_across_runs(self, tmp_path: Path):
        # two runs from the same frozen policy produce byte-identical artifacts
        md1, js1 = tmp_path / "b1.md", tmp_path / "b1.json"
        md2, js2 = tmp_path / "b2.md", tmp_path / "b2.json"
        generate_stage_b_demo_report(md1, js1, policy_path=FROZEN_POLICY_PATH)
        generate_stage_b_demo_report(md2, js2, policy_path=FROZEN_POLICY_PATH)
        assert js1.read_text(encoding="utf-8") == js2.read_text(encoding="utf-8")
        assert md1.read_text(encoding="utf-8") == md2.read_text(encoding="utf-8")
