"""run / resume 入口 — 身份核对、存储与 checkpoint 装配、恢复语义。

- run:先写 run_identity.json(代码/资产/策略/模型/提示词/MoleCode 身份),
  再进图;``migrate_from`` 提供第一阶段旧 run 的**显式**迁移入口(只读旧
  身份取输入与策略,新身份记录迁移来源,旧目录零改动);
- resume:重建当前身份与已存身份逐字段核对(代码/资产/策略/模型/提示词/
  MoleCode 任一变更即拒绝),并核对 DB graph_revision 不低于 checkpoint 内
  记录(账本被回退/换库即拒绝);第一阶段旧 run 直接 resume 会被身份门槛
  拒绝 —— 这是设计行为,不是故障;
- checkpoint(pathway 检查点)与 path 账本(pathway.sqlite)是两个独立
  持久化,恢复语义靠 task_id 幂等 + graph_revision 对齐(任务书 §2)。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..adapters.v3_engine import v3_code_identity
from ..config import V43Config
from ..domain.identity import cn_identity
from ..domain.models import STRATEGY_VERSION
from ..storage.artifact_store import ArtifactStore
from ..storage.pathway_store import PathwayStore
from ..storage.run_identity import (
    build_run_identity,
    check_resume_identity,
    load_run_identity,
    retrieval_asset_identity,
    scripted_asset_identity,
    write_run_identity,
)
from .graph import build_graph
from .nodes import Services
from .state import WorkflowState


class RunError(RuntimeError):
    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


class RunAlreadyExists(RunError):
    def __init__(self, run_id: str, run_dir: Path) -> None:
        super().__init__(
            f"run 已存在:{run_id}(重复执行请用 resume --run-id {run_id})",
            {"run_id": run_id, "run_dir": str(run_dir)},
        )


class RunNotFound(RunError):
    def __init__(self, run_id: str, runs_root: Path) -> None:
        super().__init__(
            f"run 不存在或缺少 run_identity.json:{run_id}",
            {"run_id": run_id, "runs_root": str(runs_root)},
        )


class LedgerRolledBack(RunError):
    def __init__(self, state_revision: int, store_revision: int) -> None:
        super().__init__(
            f"resume 拒绝:账本 graph_revision({store_revision})低于检查点记录"
            f"({state_revision}),pathway.sqlite 可能被回退或换库",
            {"checkpoint_revision": state_revision,
             "store_revision": store_revision},
        )


@dataclass
class RunHandle:
    run_dir: Path
    store: PathwayStore
    artifacts: ArtifactStore
    services: Services


def strategy_dict(max_depth: int, max_expansions: int,
                  max_frontier_width: int,
                  max_llm_calls: int = 0,
                  max_proposals: int = 0) -> dict:
    return {
        "max_depth": max_depth,
        "max_expansions": max_expansions,
        "max_frontier_width": max_frontier_width,
        "max_llm_calls": max_llm_calls,
        "max_proposals": max_proposals,
    }


def _build_identity(
    config: V43Config, run_id: str, smiles: str, root_cn: str | None,
    strategy: dict, asset_identity: dict, prediction: dict | None,
) -> dict:
    return build_run_identity(
        run_id=run_id, root_smiles=smiles, root_cn=root_cn or smiles,
        strategy={"version": STRATEGY_VERSION, **strategy},
        asset_identity=asset_identity,
        v3_code_identity=v3_code_identity(config.v3_code_root),
        prediction=prediction,
    )


def open_run(config: V43Config, runs_root: str | Path, run_id: str,
             finder, asset_identity: dict, strategy: dict,
             model=None, crash_after: str | None = None) -> RunHandle:
    runs_dir = Path(runs_root) / run_id
    store = PathwayStore(runs_dir / "pathway.sqlite")
    artifacts = ArtifactStore(runs_root, run_id)
    services = Services(
        store=store, artifacts=artifacts, finder=finder, runs_dir=str(runs_dir),
        asset_identity=asset_identity, strategy=strategy, model=model,
        crash_after=crash_after,
    )
    return RunHandle(run_dir=runs_dir, store=store, artifacts=artifacts,
                     services=services)


def _checkpointer(run_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(run_dir / "checkpoint.sqlite"),
                           check_same_thread=False)
    return conn


def _prediction_block(model) -> dict:
    """run_identity.prediction 块(off 也记录,保证身份可比)。"""
    if model is not None:
        return model.identity_block()
    from ..domain.policy import PREDICTION_POLICY_VERSION

    return {
        "enabled": False, "provider": "off", "model_id": "",
        "prompt_versions": {}, "policy_version": PREDICTION_POLICY_VERSION,
        "policy": {},
    }


def start_run(
    *,
    config: V43Config,
    runs_root: str | Path,
    run_id: str,
    smiles: str,
    max_depth: int,
    max_expansions: int,
    max_frontier_width: int,
    finder,
    scripted: bool = False,
    model=None,
    crash_after: str | None = None,
    migrate_from: str | None = None,
    max_llm_calls: int = 0,
    max_proposals: int = 0,
) -> dict:
    runs_root = Path(runs_root)
    run_dir = runs_root / run_id
    if (run_dir / "run_identity.json").is_file():
        raise RunAlreadyExists(run_id, run_dir)

    migrated_block = None
    if migrate_from is not None:
        old = load_run_identity(runs_root, migrate_from)
        if old is None:
            raise RunNotFound(migrate_from, runs_root)
        if not smiles or smiles == "":
            smiles = old["inputs"]["root_smiles"]
        # 显式迁移:旧身份只读;新身份记录来源与旧指纹,便于审计
        from ..storage.run_identity import identity_fingerprint

        migrated_block = {
            "from_run_id": migrate_from,
            "from_identity_fingerprint": identity_fingerprint(old),
            "from_strategy": old.get("strategy"),
            "note": ("explicit migration: old run left untouched; direct "
                     "resume of the old run is rejected by identity check"),
        }

    root_cn = cn_identity(smiles)
    strategy = strategy_dict(max_depth, max_expansions, max_frontier_width,
                             max_llm_calls, max_proposals)
    if model is not None:
        # 缺省 LLM/提案额度随展开额度派生(仍写入身份,可显式覆盖)
        if strategy["max_llm_calls"] == 0:
            strategy["max_llm_calls"] = max_expansions + 2
        if strategy["max_proposals"] == 0:
            strategy["max_proposals"] = max_expansions
    asset_identity = (
        scripted_asset_identity() if scripted
        else retrieval_asset_identity(config)
    )
    identity = _build_identity(
        config, run_id, smiles, root_cn, strategy, asset_identity,
        _prediction_block(model),
    )
    if migrated_block is not None:
        identity["migrated_from"] = migrated_block
    write_run_identity(runs_root, identity)

    handle = open_run(config, runs_root, run_id, finder, asset_identity,
                      strategy, model=model, crash_after=crash_after)
    checkpointer_conn = _checkpointer(handle.run_dir)
    from langgraph.checkpoint.sqlite import SqliteSaver

    app = build_graph(handle.services, SqliteSaver(checkpointer_conn))
    initial: WorkflowState = {
        "run_id": run_id,
        "root_smiles": smiles,
        "budget": {
            "max_depth": max_depth,
            "max_expansions": max_expansions,
            "max_frontier_width": max_frontier_width,
            "used_expansions": 0,
            "max_llm_calls": strategy["max_llm_calls"],
            "used_llm_calls": 0,
            "max_proposals": strategy["max_proposals"],
            "used_proposals": 0,
        },
        "phase": "init",
    }
    final = app.invoke(
        initial, {"configurable": {"thread_id": run_id}}
    )
    checkpointer_conn.close()
    return _summary(handle, final)


def resume_run(
    *,
    config: V43Config,
    runs_root: str | Path,
    run_id: str,
    finder=None,
    model=None,
    crash_after: str | None = None,
) -> dict:
    runs_root = Path(runs_root)
    saved = load_run_identity(runs_root, run_id)
    if saved is None:
        raise RunNotFound(run_id, runs_root)
    saved_mode = (saved.get("asset_identity") or {}).get("mode", "repo_assets")
    current_asset = (
        scripted_asset_identity() if saved_mode == "scripted_fixture"
        else retrieval_asset_identity(config)
    )
    strategy = {
        k: saved["strategy"].get(k, 0)
        for k in ("max_depth", "max_expansions", "max_frontier_width",
                  "max_llm_calls", "max_proposals")
    }
    saved_prediction = saved.get("prediction") or {}
    if not saved_prediction.get("enabled"):
        current_prediction = _prediction_block(None)
    else:
        if model is None:
            raise RunError(
                f"run {run_id} 以 provider="
                f"{saved_prediction.get('provider')} 启用模型,resume 必须以"
                "相同身份重建模型(如 --model fake --fake-script ...);"
                "不静默以无模型继续",
                {"saved_provider": saved_prediction.get("provider")},
            )
        current_prediction = _prediction_block(model)
        # 预测策略取值以保存身份为准(resume 不改策略)
        if model is not None:
            model.policy = dict(saved_prediction.get("policy") or {})
    current = _build_identity(
        config, run_id, saved["inputs"]["root_smiles"],
        saved["inputs"].get("root_identity"), strategy, current_asset,
        current_prediction,
    )
    check_resume_identity(saved, current)

    if finder is None:
        finder = _finder_for(config, saved_mode)

    handle = open_run(
        config, runs_root, run_id,
        finder=finder, asset_identity=current_asset, strategy=strategy,
        model=model, crash_after=crash_after,
    )
    checkpointer_conn = _checkpointer(handle.run_dir)
    from langgraph.checkpoint.sqlite import SqliteSaver

    app = build_graph(handle.services, SqliteSaver(checkpointer_conn))
    thread_cfg = {"configurable": {"thread_id": run_id}}
    snapshot = app.get_state(thread_cfg)
    if not snapshot.values:
        checkpointer_conn.close()
        raise RunError(
            f"run {run_id} 没有可恢复的检查点(首个 checkpoint 前中断应直接重跑"
            " run);run_identity.json 已存在,请先删除该 run 目录",
            {"run_id": run_id, "run_dir": str(handle.run_dir)},
        )
    state_revision = int(snapshot.values.get("graph_revision") or 0)
    store_revision = handle.store.graph_revision()
    if store_revision < state_revision:
        checkpointer_conn.close()
        raise LedgerRolledBack(state_revision, store_revision)

    final = app.invoke(None, thread_cfg)  # 恢复语义:从检查点续跑(安装版实测)
    checkpointer_conn.close()
    return _summary(handle, final, resumed=True,
                    checkpoint_revision=state_revision)


def _finder_for(config: V43Config, mode: str):
    if mode == "scripted_fixture":
        raise RunError(
            "scripted 夹具 run 的 resume 必须显式提供同一 ScriptedReactionFinder"
            "(含预设证据);CLI 无法跨进程重建脚本检索器",
            {"mode": mode},
        )
    from ..adapters.v3_engine import get_engine
    from ..services.reaction_finder import EngineReactionFinder

    return EngineReactionFinder(get_engine(config), config)


def _summary(handle: RunHandle, final: dict, resumed: bool = False,
             checkpoint_revision: int = 0) -> dict:
    return {
        "run_id": handle.services.store.current_run(),
        "stop_reason": final.get("stop_reason", ""),
        "phase": final.get("phase", ""),
        "error": final.get("error", {}),
        "budget": dict(final.get("budget", {})),
        "graph_revision": handle.store.graph_revision(),
        "counts": handle.store.counts(),
        "resumed": resumed,
        "checkpoint_revision": checkpoint_revision,
    }
