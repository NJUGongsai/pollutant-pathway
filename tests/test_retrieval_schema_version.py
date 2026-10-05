"""检索产物 schema 版本校验(fable5 §5.1[缺失]/§7-2,P1b 修复)。

- envelope 版本:两个 finder 都返回 ``schema_version=v43-retrieval-2``
  (RETRIEVAL_SCHEMA_VERSION;命名风格与 PREDICTION_TASK_SCHEMA_VERSION
  等既有版本常量一致,不引入评审建议的新名字 —— 实际结构已有版本字段,
  改名会变更全部既有产物的身份);
- 消费端 fail-closed:未知版本在 retrieve(活调用)与任务组装
  (build_prediction_task)处显式 ``RetrievalSchemaError``,不落盘、
  不按旧结构静默解析;
- legacy 兼容:缺失版本字段的旧产物/手工夹具按既有结构继续可读;
  runs/ 已落盘的 ``v43-retrieval-1`` 产物在全消费链(classify/validate/
  adjudicate/commit)继续可用(旧 run 产物读取路径不受影响)。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.services.reaction_finder import (  # noqa: E402
    RETRIEVAL_SCHEMA_VERSION,
    RetrievalSchemaError,
    ScriptedReactionFinder,
    validate_retrieval_payload,
)
from pathway_v43.services.prediction import build_prediction_task  # noqa: E402
from pathway_v43.workflow import start_run  # noqa: E402

from wf_helpers import CATECHOL, evidence  # noqa: E402

S = cn_identity(CATECHOL)
P1 = cn_identity("O=CCC=CO")


def _envelope(version: str | None) -> dict:
    """ScriptedReactionFinder 的完整 envelope,只改 schema_version。

    version=None → 删除字段(模拟最早期无版本产物);其余原样保留,
    保证测试只针对版本字段,不夹带结构差异。"""
    ctx = type("Ctx", (), {})()
    ctx.run_id, ctx.path_id = "r-sv", "p-sv"
    ctx.substrate_smiles = ctx.substrate_identity = S
    ctx.ancestry, ctx.conditions = [], None
    env = ScriptedReactionFinder(
        {S: [evidence("bt0001#r0001", "recorded_reaction", S, ["O=CCC=CO"])]}
    ).find(ctx)
    if version is None:
        env.pop("schema_version", None)
    else:
        env["schema_version"] = version
    return env


class _VersionedStubFinder:
    """按构造参数原样返回 envelope 的 finder(版本字段可控)。"""

    def __init__(self, version: str | None):
        self.payload = _envelope(version)

    def find(self, ctx) -> dict:
        return self.payload


def _run(finder, tmp_path, run_id="sv"):
    return start_run(
        config=resolve_config(), runs_root=tmp_path, run_id=run_id,
        smiles=CATECHOL, max_depth=1, max_expansions=2,
        max_frontier_width=2, finder=finder, scripted=True,
    )


# ---------------------------------------------------------------- 校验函数


def test_validator_known_versions_pass():
    for v in ("v43-retrieval-1", "v43-retrieval-2"):
        payload = {"schema_version": v, "evidences": []}
        assert validate_retrieval_payload(payload) is payload


def test_validator_unknown_version_fail_closed():
    payload = {"schema_version": "v43-retrieval-99", "evidences": []}
    with pytest.raises(RetrievalSchemaError) as ei:
        validate_retrieval_payload(payload, origin="unit")
    assert "v43-retrieval-99" in str(ei.value), "报错必须点名未知版本"
    assert ei.value.detail["schema_version"] == "v43-retrieval-99"
    assert ei.value.detail["origin"] == "unit"
    assert "v43-retrieval-2" in str(ei.value), "报错列出支持版本"


def test_validator_missing_version_legacy_tolerated():
    payload = {"evidences": []}  # 早期产物/手工夹具:无版本字段
    assert validate_retrieval_payload(payload) is payload


def test_validator_non_dict_rejected():
    with pytest.raises(RetrievalSchemaError):
        validate_retrieval_payload(["not", "a", "dict"])


def test_finders_emit_versioned_envelope():
    assert RETRIEVAL_SCHEMA_VERSION == "v43-retrieval-2"
    env = _envelope("v43-retrieval-2")
    assert env["schema_version"] == RETRIEVAL_SCHEMA_VERSION


# ------------------------------------------------------- 工作流消费端接线


def test_retrieve_fail_closed_unknown_version_not_written(tmp_path):
    """活调用返回未知版本:retrieve 节点显式报错,产物不落盘。"""
    with pytest.raises(RetrievalSchemaError) as ei:
        _run(_VersionedStubFinder("v43-retrieval-99"), tmp_path)
    assert ei.value.detail["origin"] == "finder_live"
    assert not list(
        (tmp_path / "sv" / "results").glob("*/retrieval.json")
    ), "未知版本不得落盘为不可辨格式的产物"


def test_workflow_legacy_envelope_without_version_still_runs(tmp_path):
    """legacy:无版本字段的 envelope 全链可跑(旧产物/夹具读取不受影响)。"""
    summary = _run(_VersionedStubFinder(None), tmp_path, run_id="sv-legacy")
    assert summary["stop_reason"] == "completed"
    assert summary["counts"]["reaction_events"] == 1


def test_workflow_v1_envelope_still_runs(tmp_path):
    """runs/ 既有 v43-retrieval-1 产物版本:全消费链继续可用。"""
    summary = _run(_VersionedStubFinder("v43-retrieval-1"), tmp_path,
                   run_id="sv-v1")
    assert summary["stop_reason"] == "completed"
    assert summary["counts"]["reaction_events"] == 1


# ------------------------------------------------------------ 任务书组装


def test_build_prediction_task_fail_closed_on_unknown_version():
    """任务组装:未知版本先于任何素材组装显式失败(不静默按旧结构解析)。"""
    with pytest.raises(RetrievalSchemaError) as ei:
        build_prediction_task(
            store=None, run_id="r", path_id="p", substrate_identity=S,
            substrate_smiles=S, root_smiles=S, mode="rank_candidates",
            retrieval_payload=_envelope("v43-retrieval-99"),
            retrieval_payload_hash="h", conditions=None, model_block={},
            policy={}, budget={"max_depth": 1, "max_expansions": 1,
                               "used_expansions": 0},
        )
    assert ei.value.detail["origin"] == "prediction_task"
    # store=None 未被触碰:版本校验先于素材组装发生


def test_build_prediction_task_accepts_legacy_and_known(tmp_path):
    """任务组装对 legacy/已知版本照常工作(最小真实 store,rank 模式)。"""
    from pathway_v43.storage.pathway_store import PathwayStore

    store = PathwayStore(tmp_path / "p.sqlite")
    path_id = store.ensure_run("r-sv", CATECHOL, S)
    for version in (None, "v43-retrieval-1", "v43-retrieval-2"):
        task = build_prediction_task(
            store=store, run_id="r-sv", path_id=path_id,
            substrate_identity=S, substrate_smiles=S, root_smiles=CATECHOL,
            mode="rank_candidates", retrieval_payload=_envelope(version),
            retrieval_payload_hash="h", conditions=None, model_block={},
            policy={}, budget={"max_depth": 1, "max_expansions": 1,
                               "used_expansions": 0},
        )
        assert task["schema_version"] == "v43-prediction-task-3"
        assert task["mode"] == "rank_candidates"
        assert task["ancestry"], "祖先链照常组装"
