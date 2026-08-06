"""P7 T0① kernel-integration pin tests.

RED until the Gate-P3 strict kernel (``reaction_agent/p3/``) and the Gate-P4
inference kernel (``reaction_agent/inference/`` + ``adapters/`` + ``runtime/``
+ ``schemas/p4/`` + ``policies/p4_decision_policy``) are ported into this
branch; GREEN once the port lands. The pins assert the ported packages import
and the P3 kernel runs end-to-end in fixture mode in the combined tree.

Scope boundary: these pins cover T0① (port landed) ONLY. They do NOT exercise
``handle_predict`` wiring (T0②) — that is suspended pending a CC scope decision
on the missing P3→P4 input bridge (``evidence_records`` / ``structural_contexts``
/ ``feature_evidence_ids`` are not in the P3→P4 frozen artifact contract; see
Leader Round 2 in the issue thread). No bridge code is pre-written here.
"""
from __future__ import annotations


def test_p3_strict_kernel_importable():
    """P3 package + kernel entry point resolve in the combined tree."""
    from reaction_agent.p3 import (  # noqa: F401
        KernelResult,
        KernelRunManifest,
        StrictCandidate,
    )
    from reaction_agent.p3.kernel import run_kernel  # noqa: F401

    assert KernelResult is not None
    assert StrictCandidate is not None
    assert KernelRunManifest is not None
    assert callable(run_kernel)


def test_p3_run_kernel_fixture_returns_typed_result():
    """P3 deterministic baseline kernel runs in fixture mode => typed KernelResult.

    Fixture mode uses synthetic donor evidence (no real snapshot / no LLM), so
    the run is deterministic + replayable. The pin only asserts a typed
    ``KernelResult`` is produced (completed / blocked / failed are all valid —
    scientific stops are typed, never exceptions).
    """
    from reaction_agent.p3.kernel import run_kernel
    from reaction_agent.p3.schemas import KernelResult, KernelStatus

    # Fixture fold is frozen as fold_fx_p3 (P3 synthetic donor train view);
    # the query mirrors tests/p3/test_lifecycle (octanol oxidation fixture).
    result = run_kernel(
        input_smiles="CCCCCCCCO",
        case_id="c_pin",
        fold_id="fold_fx_p3",
        mode="fixture",
        seed=0,
    )
    assert isinstance(result, KernelResult)
    assert result.status in {
        KernelStatus.completed,
        KernelStatus.blocked,
        KernelStatus.failed,
    }
    # Frozen namespace is carried on the manifest.
    assert result.manifest.run_id == result.run_id
    assert result.manifest.case_id == result.case_id


def test_p4_inference_kernel_importable():
    """P4 inference + adapter + runtime + p4 schemas + policy resolve together."""
    from reaction_agent.adapters.p3_consumer import P3InterfaceConsumer  # noqa: F401
    from reaction_agent.inference.predictor import (  # noqa: F401
        PipelineOutcome,
        run_p4_pipeline,
    )
    from reaction_agent.policies.p4_decision_policy import P4_POLICY_VERSION
    from reaction_agent.runtime.run import ImmutableRunStore  # noqa: F401
    from reaction_agent.schemas.p4.authority import P3AuthorityHandle  # noqa: F401
    from reaction_agent.schemas.result import PredictionResult  # noqa: F401

    assert P4_POLICY_VERSION  # non-empty frozen version string
    assert callable(run_p4_pipeline)
    assert PipelineOutcome is not None
    assert PredictionResult is not None
    assert P3AuthorityHandle is not None
    assert P3InterfaceConsumer is not None
    assert ImmutableRunStore is not None
