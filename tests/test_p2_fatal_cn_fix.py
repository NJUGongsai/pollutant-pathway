"""P2 v2card fatal 修复回归（2026-10-26）。

任务：`docs/T_P2_FATAL_DIAGNOSIS_2026-10-26.md` 判定 B（代码/序列化
bug）。根因：`build_chemical_state` 用**带原子映射号的原始 SMILES**
算 `cn_identity`，而 `state_id`/`smiles_isomeric` 与
`validate_state_object` 的重推导都走**去映射号身份键**；同一对象
两个 CN 来源分裂，首消费报 `state_fact_rederivation_mismatch`。

本文件只覆盖修复口径（零金标、零题面、零模型、零网络）：

1. 带映射号产物（诊断里的 v2 novel-1/novel-2 脱敏结构）经
   `build_chemical_state` + `validate_state_object` 必须 PASS，
   且 CN 不含 `:数字` 原子映射注解；
2. 工厂 CN == 从 `smiles_isomeric` 重推的 CN（逐字）；
3. v2 novel-1 / novel-2 回放：不再触发
   `state_fact_rederivation_mismatch`；novel-2 的 pending 行为不变
   （调度/认领是纯账本动作，状态重推导不写队列）；
4. 负控：raw 指向另一个分子时仍拒绝（同源校验未被放宽）。

合成底物用 CCO（与真实 298 集合零重叠）；novel 产物串来自诊断证据
`docs/review_evidence/p2_fatal_diagnosis_2026-10-26/inputs.json`。
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.domain.identity import cn_identity as legacy_cn_identity  # noqa: E402
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    ChemicalState,
    ChemicalStateError,
    build_chemical_state,
    validate_state_object,
)
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.profile import (  # noqa: E402
    build_profile_identity_block,
)
from pathway_v43.pollutant.queue import schedule_hypotheses  # noqa: E402
from pathway_v43.pollutant.search import (  # noqa: E402
    SearchLedger,
    search_policy_version,
)
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402

# v2card 录制响应的 novel-1/novel-2 产物（诊断 inputs.json；脱敏结构，
# 不含底物/题面）。novel-1 与 v1 的同一产物同 InChIKey。
V2_NOVEL1 = (
    "[CH3:1][C@:2]12[CH2:3][CH2:4]C(=O)[CH2:7][C@@H:8]1[CH2:9][CH2:10]"
    "[C@@H:11]1[C@@H:12]2[CH2:13][CH2:14][C@:15]2([CH3:16])[C@@H:17]"
    "([OH:18])[CH2:19][CH2:20][C@@H:21]12")
V2_NOVEL2 = (
    "[CH3:1][C@:2]12[CH2:3][CH2:4][C@@H:5]([OH:6])[CH2:7][C@@H:8]1"
    "[CH2:9][CH2:10][C@@H:11]1[C@@H:12]2[CH2:13][CH2:14][C@:15]2"
    "([CH3:16])[CH:17]=[CH:19][CH2:20][C@@H:21]12")
# v1card 的同一 novel-1 产物（无映射号；兼容性正控）。
V1_NOVEL1 = (
    "C[C@]12CCC(=O)C[C@@H]1CC[C@@H]1[C@@H]2CC[C@]2(C)[C@@H](O)CC[C@@H]12")
TARGET_STATE_ID = "cs_a1ec01b3e472d011d8b8"
V1_CN = "CC12CCC3C(CCC4CC(=O)CCC43C)C1CCC2O"

_MAP_ANNOTATION = re.compile(r":\d+")


def _build(smiles: str) -> ChemicalState:
    return build_chemical_state(
        smiles, "source_product", [{"record": "p2-fatal-synthetic"}])


def _assert_valid(state: ChemicalState) -> None:
    try:
        validate_state_object(state)
    except ChemicalStateError as exc:
        pytest.fail(
            "state 首消费被拒: kind="
            f"{exc.detail.get('kind')!r} detail="
            f"{exc.detail.get('mismatches') or exc.detail}")


def _spec(product_smiles: str, key: str) -> dict:
    """最小冻结 spec（只走 prepare_hypothesis 的状态构建路径）。"""
    return {
        "key": key,
        "product_smiles": product_smiles,
        "coefficient": 1,
        "transformation_ref": key,
        "origin_group_key": f"rec-source:{key}",
        "edits": [],
        "donor": {"center_atom_ids": []},
        "alignment": {"status": "resolved"},
        "expectation": {"target_smiles": product_smiles},
    }


# ---------------------------------------------------------------- 1


@pytest.mark.parametrize("smiles", [V2_NOVEL1, V2_NOVEL2],
                         ids=["novel-1", "novel-2"])
def test_mapped_product_builds_and_passes_first_consumption(
        smiles: str) -> None:
    """带原子映射号的产物：工厂产物必须过首消费验，CN 不含映射号。"""
    state = _build(smiles)
    _assert_valid(state)
    assert ":[" not in state.smiles_isomeric
    assert state.smiles_isomeric == _build(state.smiles_isomeric)\
        .smiles_isomeric
    assert _MAP_ANNOTATION.search(state.cn_identity) is None
    # from_dict 恢复入口与工厂共用同一验证源。
    restored = ChemicalState.from_dict(state.to_dict())
    assert restored.to_dict() == state.to_dict()


# ---------------------------------------------------------------- 2


@pytest.mark.parametrize("smiles", [V2_NOVEL1, V2_NOVEL2, V1_NOVEL1],
                         ids=["novel-1", "novel-2", "v1-novel-1"])
def test_factory_cn_equals_rederived_cn(smiles: str) -> None:
    """工厂 CN == 从 smiles_isomeric 重推的 CN（逐字）。"""
    state = _build(smiles)
    rederived = _build(state.smiles_isomeric)
    assert state.cn_identity == rederived.cn_identity
    assert state.cn_identity == legacy_cn_identity(state.smiles_isomeric)
    assert state.state_id == rederived.state_id


def test_v1_identity_and_cn_unchanged() -> None:
    """兼容性正控：无映射号输入的 state_id/CN 与历史记录逐字相同。"""
    state = _build(V1_NOVEL1)
    assert state.state_id == TARGET_STATE_ID
    assert state.cn_identity == V1_CN
    _assert_valid(state)


# ---------------------------------------------------------------- 3


def _replay(product_smiles: str, key: str) -> dict:
    substrate = build_chemical_state(
        "CCO", "raw_input", [{"record": "p2-fatal-synthetic-substrate"}])
    return prepare_hypothesis(
        _spec(product_smiles, key), parent_path_id="p2-fatal-replay",
        substrate_state=substrate, transformation_ref=key)


def _validate_prepared(prepared: dict) -> None:
    """复刻 audit.py:512 的首次消费守卫（直接 states 对象）。"""
    for state in prepared["states"].values():
        _assert_valid(state)


def test_v2_novel_replay_no_rederivation_mismatch() -> None:
    """v2 novel-1/novel-2 回放：不再触发 CN 重推导分歧。"""
    novel1 = _replay(V2_NOVEL1, "V2-FATAL-NOVEL1")
    novel2 = _replay(V2_NOVEL2, "V2-FATAL-NOVEL2")
    _validate_prepared(novel1)
    _validate_prepared(novel2)
    product1 = novel1["states"][novel1["product_states"][0].state_id]
    assert product1.state_id == TARGET_STATE_ID
    assert _MAP_ANNOTATION.search(product1.cn_identity) is None


def test_v2_novel2_action_stays_pending(tmp_path) -> None:
    """novel-1 回放成功后，novel-2 仍是 pending（调度行为不变）。

    录制 run 的队列事实：novel-1 的 expand action 为 claimed、novel-2
    为 pending（诊断 §1）。修复只改状态 CN 计算，不写队列；本测试用
    临时账本复现“两条 novel 入队 → 认领 novel-1 → 校验状态”的顺序，
    断言 novel-2 的 action 状态未被重推导副作用改动。
    """
    run_id = "p2-fatal-pending"
    store = PollutantPathwayStore(tmp_path / "p2-fatal-pending.sqlite")
    art = ArtifactStore(tmp_path / "runs", run_id)
    ledger = SearchLedger(store, art, run_id)
    policy = build_profile_identity_block()
    ledger.register_search_run(run_id, policy)

    novel1 = _replay(V2_NOVEL1, "V2-FATAL-NOVEL1")
    novel2 = _replay(V2_NOVEL2, "V2-FATAL-NOVEL2")
    h1 = novel1["hypothesis"].hypothesis_id
    h2 = novel2["hypothesis"].hypothesis_id
    out = schedule_hypotheses(
        ledger, run_id=run_id, parent_path_id="p2-fatal-replay",
        context_ref="p2-fatal-context", parent_search_revision=0,
        pool=[
            {"hypothesis_key": "novel-1", "hypothesis_id": h1, "rank": 1,
             "payload": {"task_key": "tk-novel-1"}},
            {"hypothesis_key": "novel-2", "hypothesis_id": h2, "rank": 2,
             "payload": {"task_key": "tk-novel-2"}},
        ],
        policy_version=search_policy_version(), depth=1)
    selected = {row["hypothesis_id"]: row for row in out["selected"]}
    assert set(selected) == {h1, h2}
    assert all(row["status"] == "pending" for row in selected.values())

    ledger.claim_action(selected[h1]["action_id"], worker_id="w-p2-fatal")
    _validate_prepared(novel1)
    assert ledger.action(selected[h2]["action_id"])["status"] == "pending"
    # novel-2 自身也能过状态验，但校验不改变其待执行状态。
    _validate_prepared(novel2)
    assert ledger.action(selected[h2]["action_id"])["status"] == "pending"


# ---------------------------------------------------------------- 4


@pytest.mark.parametrize("other", ["CCO", V2_NOVEL2],
                         ids=["map-free-other", "mapped-other"])
def test_raw_pointing_to_another_molecule_still_rejected(
        other: str) -> None:
    """负控：CN 同源化不得放宽 raw→strict 同源身份核。"""
    state = _build(V2_NOVEL1)
    tampered = dataclasses.replace(state, structure_smiles_raw=other)
    with pytest.raises(ChemicalStateError) as excinfo:
        validate_state_object(tampered)
    assert excinfo.value.detail["kind"] == "raw_identity_mismatch"
    assert excinfo.value.detail["state_id"] == TARGET_STATE_ID


def test_mapped_raw_of_same_molecule_still_accepted() -> None:
    """正控：同一分子的另一种映射号写法（同图异拼写）仍接受。"""
    state = _build(V2_NOVEL1)
    # 映射号顺序/编号不同、括号冗余不同，但分子图相同。
    rewritten = (
        "[CH3:7][C@:8]12[CH2:9][CH2:10]C(=O)[CH2:11][C@@H:12]1[CH2:13]"
        "[CH2:14][C@@H:15]1[C@@H:16]2[CH2:17][CH2:18][C@:19]2([CH3:20])"
        "[C@@H:21]([OH:22])[CH2:23][CH2:24][C@@H:25]12")
    tampered = dataclasses.replace(state, structure_smiles_raw=rewritten)
    validate_state_object(tampered)
