"""P3→P4 consumer adapter (read-only; typed BLOCKED when P3 missing)."""
from __future__ import annotations

import json
import os
import pytest

from reaction_agent.adapters.p3_consumer import (
    P3InterfaceConsumer,
    P3InterfaceState,
    DEFAULT_P3_MANIFEST,
)
from reaction_agent.schemas.p4.authority import P4Classification

FROZEN_MANIFEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fixtures", "p4", "p3_p4_interface_manifest_frozen.json")


def test_missing_manifest_is_typed_blocked():
    """P3→P4: absent p3_p4_interface_manifest.json => typed BLOCKED, never PASS."""
    consumer = P3InterfaceConsumer(missing_path="/nonexistent/p3_p4_interface_manifest.json")
    state = consumer.load()
    assert isinstance(state, P3InterfaceState)
    assert state.present is False
    assert state.classification == P4Classification.blocked
    assert not state.capability_available
    assert state.blocked_reasons


def test_interface_manifest_alone_is_typed_blocked():
    """P3→P4: an interface manifest without a current-run artifact is BLOCKED,
    never PASS-capable (the manifest proves schema, not capability)."""
    consumer = P3InterfaceConsumer(
        missing_path=FROZEN_MANIFEST,
        current_run_path="/nonexistent/current_run_artifact.json")
    state = consumer.load()
    assert isinstance(state, P3InterfaceState)
    assert state.present is True
    assert state.classification == P4Classification.blocked
    assert not state.capability_available
    assert any("current_run" in r for r in state.blocked_reasons)


def test_reads_only_frozen_json_manifest(tmp_path):
    """P3→P4: consumer reads only the frozen JSON interface, never Python
    internals; the frozen p3-p4-3 top-level fields are parsed."""
    with open(FROZEN_MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    p = tmp_path / "p3_p4_interface_manifest.json"
    p.write_text(json.dumps(manifest))
    consumer = P3InterfaceConsumer(missing_path=str(p))
    state = consumer.load()
    assert state.present is True
    assert state.manifest_version == "p3-p4-3"
    assert "KernelResult" in state.interfaces
    assert "StrictCandidate" in state.interfaces
    assert state.classification == P4Classification.blocked  # no current run
    assert not state.capability_available


def test_output_bindings_and_classification():
    """P3→P4: adapter outputs carry case/query/fold/snapshot/run binding."""
    consumer = P3InterfaceConsumer(missing_path="/nonexistent/manifest.json")
    out = consumer.wrap_p4_output(
        data={"kind": "diagnostic"},
        case_id="case_1",
        query_id="q_1",
        fold_id="fold_1",
        snapshot_id="snap_x",
        run_id="run_x",
    )
    assert out["case_id"] == "case_1"
    assert out["query_id"] == "q_1"
    assert out["fold_id"] == "fold_1"
    assert out["snapshot_id"] == "snap_x"
    assert out["run_id"] == "run_x"
    assert out["classification"] in {c.value for c in P4Classification}