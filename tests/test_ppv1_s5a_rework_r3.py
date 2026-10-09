"""S5a 回修 r3 回归(复审 R3 POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R3_
2026-10-09 §4 S5A-05 + §8 五案矩阵;契约登记 ppv1-search-production-2 /
ppv1-profile-23,evaluation-3/template-3 版本号不变 —— 五处 P2 文案
为拟冻结前同步)。

S5A-05:共同 ``production.load_context`` 在 H07 + ``from_dict`` 完成
后、实际消费前核**请求 context_ref == 恢复载荷 context_id** ——
selfhash 重算正确不能替代旧引用绑定;旧 ``ctx:<ref>`` 存储键下的
自洽新身份(重封 H07 亦同)⇒ 结构化拒(kind
``context_reference_binding_mismatch``,披露期望引用/实际身份),
坏 artifact 保全,不重封覆盖、不猜迁移、不默发新引用。冻结侧
path_context 判决零触碰(守卫在 production 消费侧)。

五案(1–3 复用复审 R3 §4.2 mimo 专项的原输入构造;4 为复审未执行
的建议补控,本轮自构造;5 为须构造的合法新地址正控,自构造):

1. 正常 checked unknown None 与正常公开 resume 保持(unit + 公共链);
2. 原 context_id + 改内容(重封 H07)继续 ``context_content_
   identity_mismatch`` 拒(from_dict 层先于绑定层,既有防线保持);
3. 直构 unknown+实体值的自洽新 context_id + 重封 H07 但旧 ctx:
   存储键 ⇒ 首消费 binding mismatch 拒(原反例翻转);
4. checked 正规合法新内容 + 新 context_id 但旧地址 ⇒ 同样拒
   (内容合法不豁免地址绑定;同载荷存自己的新地址可正常消费);
5. 合法新内容新 ID **新地址** + parent_context_ref 链允许;正常
   子上下文/场景转换保持(transition 派生子 ctx 存新地址、followup
   沿新引用)。

消费入口矩阵(共用同一守卫,不各自造规则):
runflow ``_run_decide``/``_run_expand``/``_run_transition`` +
endpoint ``_inherited_unresolved_dependencies``/
``_route_condition_assessments``/``_route_conditions_snapshot`` ——
全部经 ``production.load_context``。公开 resume 首消费拒后不派生/
评估/audit/提交坏上下文事件;既有无关 retrieve/claim 写入**逐表
如实披露**(search_actions/search_commit_records/budget_
reservations 各 +1,不伪报全表零变化)。

全部为合成规则级夹具(零金标/题面/网络/LLM/费用;数字不外推
dev/298)。红绿分类:对直接父 39d739d 同字节 —— 案 3/4 及公共链
案 3/4 与 endpoint/守卫为行为红,入口矩阵静态守卫与版本字面量为
字段/版本红,案 1/2/5 与正控为父绿;无 collection 红(父上模块
均已存在)。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import content_hash  # noqa: E402
from pathway_v43.pollutant.endpoint import (  # noqa: E402
    EndpointContractError,
    _inherited_unresolved_dependencies,
    _route_condition_assessments,
    _route_conditions_snapshot,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    ConditionContractError,
    ConditionFact,
    Dependency,
    PathContext,
    Requirement,
    build_condition_fact,
    build_path_context,
    build_requirement,
    derive_child_context,
)
from pathway_v43.pollutant.production import (  # noqa: E402
    CONTEXT_ARTIFACT_NAME,
    SEARCH_PRODUCTION_VERSION,
    load_context,
    persist_context,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    PPV1_PREREGISTRATION_TEMPLATE_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    PPV1_REFERENCE_GRAPH_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from pathway_v43.pollutant.search import SearchCrashInjection  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import resume_run, start_run  # noqa: E402
from test_ppv1_s4a_endpoint import spec  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src" / "pathway_v43" / "pollutant"


# ------------------------------------------------------ 夹具与突变工具


def _req() -> Requirement:
    return build_requirement(
        key="electron_acceptor", level="essential", value="O2",
        source_refs=["src:synthetic-necessity"])


def _base_facts() -> list[ConditionFact]:
    """评审 R3 §4.2 mimo 专项原输入同形:同键 unknown + known_present
    两条(checked 构造 ⇒ unknown 值清 None)。"""
    return [build_condition_fact(key="electron_acceptor", value=None,
                                 status="unknown"),
            build_condition_fact(key="electron_acceptor", value="O2",
                                 status="known_present")]


def _binding_kind(exc: Exception) -> str:
    return getattr(exc, "detail", {}).get("kind", "")


def _ctx_files(artifacts: ArtifactStore) -> list[Path]:
    return sorted(artifacts.base.glob(
        f"ctx:*/{CONTEXT_ARTIFACT_NAME}.json"))


def _recompute_id_for_payload(payload: dict) -> str:
    """按复审 mimo 专项的原方法重算载荷身份(直构 fake 对象走官方
    _recompute_context_hash;不经过 checked 构造器)。"""
    fake = PathContext.__new__(PathContext)
    for field, value in payload.items():
        if field != "assessed_scope":
            setattr(fake, field, value)
    fake.condition_facts = [ConditionFact(**f)
                            for f in payload["condition_facts"]]
    fake.accumulated_requirements = [Requirement(**r)
                                      for r in
                                      payload["accumulated_requirements"]]
    fake.dependencies = [Dependency(**d)
                         for d in payload["dependencies"]]
    from pathway_v43.pollutant.path_context import \
        _recompute_context_hash
    return _recompute_context_hash(fake)


def _mutate_self_consistent_new_id(artifacts: ArtifactStore,
                                   ref: str) -> tuple[dict, str]:
    """复审原反例:unknown 事实改实体值 + 直构重算新 context_id +
    重封 H07 payload_hash,**旧 ctx: 存储键不动**。返回
    (mutation envelope, new_id);原文件被覆写为突变后形态。"""
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["condition_facts"][0]["value"] = "O2"
    new_id = _recompute_id_for_payload(envelope["payload"])
    envelope["payload"]["context_id"] = new_id
    envelope["payload_hash"] = content_hash(envelope["payload"])
    path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return envelope, new_id


def _mutate_checked_legal_new_content(artifacts: ArtifactStore,
                                      ref: str,
                                      new_payload: dict) -> dict:
    """案 4 突变:把**checked 正规合法新内容**(build_path_context
    产物)整体写入旧 ctx: 地址(重封 H07)。合法内容 + 旧地址 ⇒
    仍须拒;返回突变后 envelope。"""
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"] = new_payload
    envelope["payload_hash"] = content_hash(new_payload)
    path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return envelope


def _table_snapshot(sqlite_path: Path) -> dict:
    """只读全表快照(复审 mimo 专项同口径;逐表计数用)。"""
    uri = f"file:{sqlite_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    out: dict = {}
    for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
            " ORDER BY name").fetchall():
        name = str(row[0])
        out[name] = [dict(r) for r in conn.execute(
            f'SELECT * FROM "{name}" ORDER BY rowid')]
    conn.close()
    return out


def _table_deltas(before: dict, after: dict) -> dict:
    return {name: len(after.get(name, [])) - len(before.get(name, []))
            for name in sorted(set(before) | set(after))}


def _start_after_claim(runs_root: Path, run_id: str) -> ArtifactStore:
    """复审 mimo 专项同形公共 start(after_claim 硬注入;plan 带
    condition_facts 与 CCO 池)。返回该 run 的 ArtifactStore。"""
    plan = {
        "condition_facts": [
            {"key": "electron_acceptor", "value": "O2",
             "status": "unknown", "source_ref": "src:synthetic-unknown"},
            {"key": "electron_acceptor", "value": "O2",
             "status": "known_present",
             "source_ref": "src:synthetic-present"}],
        "pools": {"CCO": [spec("A", "CC=O", "donor-A",
                               coproducts=["[H][H]"],
                               requirements=[{
                                   "key": "electron_acceptor",
                                   "level": "essential", "value": "O2",
                                   "source_refs":
                                       ["src:synthetic-necessity"]}])]},
        "schedule_budget": {"max_select": 1},
    }
    with pytest.raises(SearchCrashInjection):
        start_run(config=resolve_config(), runs_root=runs_root,
                  run_id=run_id, smiles="CCO", max_depth=2,
                  max_expansions=5, max_frontier_width=2,
                  finder=object(), scripted=True,
                  profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan,
                  crash_after="after_claim")
    return ArtifactStore(runs_root, run_id)


def _public_resume(runs_root: Path, run_id: str) -> dict:
    return resume_run(config=resolve_config(), runs_root=runs_root,
                      run_id=run_id)


# ------------------------------------------------------ 案 1–5(unit 级)


def test_s5a_r3_case1_normal_checked_unknown_roundtrip(tmp_path) -> None:
    """案 1(unit 半边):正常 checked unknown 值 None;persist→load
    往返幂等,恢复 context_id == 请求 ref(父绿正控)。"""
    artifacts = ArtifactStore(tmp_path / "runs", "r3c1")
    context = build_path_context(
        condition_facts=_base_facts(),
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    ref = persist_context(artifacts, context)
    loaded = load_context(artifacts, ref)
    assert loaded.context_id == ref
    assert loaded.condition_facts[0].value is None
    assert loaded.condition_facts[0].status == "unknown"
    assert loaded.to_dict() == context.to_dict()


def test_s5a_r3_case2_old_id_changed_content_still_rejected(
        tmp_path) -> None:
    """案 2:原 context_id + 改内容(unknown 值改实体值)+ 重封 H07
    ⇒ ``context_content_identity_mismatch`` 保持(from_dict 内容身份
    层先于绑定层;父绿 —— 既有防线不动)。"""
    artifacts = ArtifactStore(tmp_path / "runs", "r3c2")
    context = build_path_context(
        condition_facts=_base_facts(),
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    ref = persist_context(artifacts, context)
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["condition_facts"][0]["value"] = "O2"
    # 保留旧 context_id,仅重封外层
    envelope["payload_hash"] = content_hash(envelope["payload"])
    path.write_text(json.dumps(envelope, indent=2,
                               ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ConditionContractError) as ei:
        load_context(artifacts, ref)
    assert _binding_kind(ei.value) == "context_content_identity_mismatch"


def test_s5a_r3_case3_self_consistent_new_id_old_address_rejected(
        tmp_path) -> None:
    """案 3(原反例翻转):直构 unknown+实体值的自洽新 context_id +
    重封 H07,但旧 ctx: 存储键 ⇒ 首消费 ``context_reference_binding_
    mismatch``;披露期望引用/实际身份;坏 artifact 保全(字节等于
    突变形态);无新引用签发(不新增 ctx 文件)。父上 load 成功 ⇒
    行为红。"""
    artifacts = ArtifactStore(tmp_path / "runs", "r3c3")
    context = build_path_context(
        condition_facts=_base_facts(),
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    ref = persist_context(artifacts, context)
    mutation, new_id = _mutate_self_consistent_new_id(artifacts, ref)
    assert new_id != ref
    with pytest.raises(ConditionContractError) as ei:
        load_context(artifacts, ref)
    detail = getattr(ei.value, "detail", {})
    assert detail.get("kind") == "context_reference_binding_mismatch"
    assert detail.get("expected_context_ref") == ref
    assert detail.get("recovered_context_id") == new_id
    assert detail.get("storage_key") == f"ctx:{ref}"
    # 坏 artifact 保全:未被改写覆盖、未被删除
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    assert json.loads(path.read_text(encoding="utf-8")) == mutation
    # 不默发新引用:ctx 文件集合不变(仍只有旧地址一份)
    assert [p.name for p in _ctx_files(artifacts)] == \
        [f"{CONTEXT_ARTIFACT_NAME}.json"]
    # 新身份存自己的新地址才是合法重建(参照正控,见案 5)


def test_s5a_r3_case4_checked_legal_new_content_old_address_rejected(
        tmp_path) -> None:
    """案 4(本轮自构造,复审未执行的建议补控):checked 正规合法
    新内容(build_path_context 产物,全部事实经 checked 构造器)+
    自洽新 context_id,写入**旧地址** ⇒ 同样 binding mismatch 拒
    (内容合法不豁免地址绑定);同一载荷存自己的新地址可正常消费
    (冻结判据四"重建半边"的合法半边)。父上旧地址 load 成功 ⇒
    行为红。"""
    artifacts = ArtifactStore(tmp_path / "runs", "r3c4")
    context = build_path_context(
        condition_facts=_base_facts(),
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    ref = persist_context(artifacts, context)
    # checked 正规合法新内容:合法重建的语义上下文(新增一条已知道)
    legal_new = build_path_context(
        condition_facts=[build_condition_fact(
            key="electron_acceptor", value="O2",
            status="known_present", source_ref="src:synthetic-present-2")],
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    assert legal_new.context_id != ref
    mutation = _mutate_checked_legal_new_content(
        artifacts, ref, legal_new.to_dict())
    with pytest.raises(ConditionContractError) as ei:
        load_context(artifacts, ref)
    detail = getattr(ei.value, "detail", {})
    assert detail.get("kind") == "context_reference_binding_mismatch"
    assert detail.get("expected_context_ref") == ref
    assert detail.get("recovered_context_id") == legal_new.context_id
    # 坏 artifact 保全(合法载荷原样留在旧地址)
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    assert json.loads(path.read_text(encoding="utf-8")) == mutation
    # 同一载荷存自己的新地址 ⇒ 合法重建,正常首消费
    new_ref = persist_context(artifacts, legal_new)
    assert new_ref == legal_new.context_id
    assert load_context(artifacts, new_ref).context_id == new_ref


def test_s5a_r3_case5_legal_new_id_new_address_parent_chain(
        tmp_path) -> None:
    """案 5(本轮自构造的合法新地址正控):合法新内容新 ID 新地址 +
    parent_context_ref 链允许 —— derive_child_context 产新 ID,存新
    地址,沿新引用首消费;父上下文旧地址照常可消费;场景转换子
    上下文保持(父绿正控,修复不得误伤)。"""
    artifacts = ArtifactStore(tmp_path / "runs", "r3c5")
    parent = build_path_context(
        condition_facts=_base_facts(),
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    parent_ref = persist_context(artifacts, parent)
    restored = load_context(artifacts, parent_ref)
    child = derive_child_context(
        restored,
        scenario_transition={"source_ref": "user:switch-anaerobic",
                             "new_phase_id": "phase-1",
                             "new_scenario_ref": "scenario-anaerobic"},
        step_edge_ref="hyp-r3c5")
    assert child.context_id != parent_ref
    assert child.parent_context_ref == parent_ref
    child_ref = persist_context(artifacts, child)
    assert child_ref == child.context_id
    loaded_child = load_context(artifacts, child_ref)
    assert loaded_child.context_id == child_ref
    assert loaded_child.parent_context_ref == parent_ref
    # 父上下文仍在旧地址合法可消费;地址与身份一一对应
    assert load_context(artifacts, parent_ref).context_id == parent_ref
    files = _ctx_files(artifacts)
    assert len(files) == 2
    for file in files:
        envelope = json.loads(file.read_text(encoding="utf-8"))
        address_id = file.parent.name[len("ctx:"):]
        assert envelope["payload"]["context_id"] == address_id


# ------------------------------------------------------ 公共链五案


def test_s5a_r3_case1_public_control_resume_preserved(tmp_path) -> None:
    """案 1(公共链半边):正常公开 resume 保持 —— after_claim 硬注入
    后合法恢复,事件恰 1、无错误(父绿正控;修复不得误伤合法
    恢复)。"""
    runs_root = tmp_path / "runs"
    artifacts = _start_after_claim(runs_root, "r3pc1")
    files = _ctx_files(artifacts)
    assert len(files) == 1
    envelope = json.loads(files[0].read_text(encoding="utf-8"))
    assert envelope["payload"]["condition_facts"][0]["value"] is None
    out = _public_resume(runs_root, "r3pc1")
    assert out["resumed"] is True
    conn = sqlite3.connect(str(runs_root / "r3pc1" / "pollutant.sqlite"))
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM events").fetchone()[0] == 1
    finally:
        conn.close()


def test_s5a_r3_case2_public_old_id_rejected_with_table_disclosure(
        tmp_path) -> None:
    """案 2(公共链):原 context_id + 改内容 ⇒ resume 以
    ``context_content_identity_mismatch`` 失败;events 0;既有无关
    retrieve/claim 写入逐表如实披露(search_actions/commit_records/
    budget_reservations 各 +1,其余表零变化 —— 不伪报全表零变化;
    父绿 —— 既有行为)。"""
    runs_root = tmp_path / "runs"
    run_id = "r3pc2"
    artifacts = _start_after_claim(runs_root, run_id)
    ref = json.loads(_ctx_files(artifacts)[0].read_text(
        encoding="utf-8"))["payload"]["context_id"]
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["condition_facts"][0]["value"] = "O2"
    envelope["payload_hash"] = content_hash(envelope["payload"])
    path.write_text(json.dumps(envelope, indent=2,
                               ensure_ascii=False), encoding="utf-8")
    before = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    with pytest.raises(ConditionContractError) as ei:
        _public_resume(runs_root, run_id)
    assert _binding_kind(ei.value) == "context_content_identity_mismatch"
    after = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    deltas = _table_deltas(before, after)
    assert deltas["events"] == 0
    assert deltas["search_actions"] == 1
    assert deltas["search_commit_records"] == 1
    assert deltas["budget_reservations"] == 1
    assert {name for name, delta in deltas.items()
            if delta not in (0, 1)} == set()
    assert [name for name, delta in deltas.items() if delta == 1] == \
        ["budget_reservations", "search_actions",
         "search_commit_records"]


def test_s5a_r3_case3_public_new_id_old_address_rejected(
        tmp_path) -> None:
    """案 3(公共链,原反例翻转):自洽新 context_id + 重封 H07 但旧
    ctx 存储键 ⇒ 公开 resume **首消费拒**(context_reference_binding_
    mismatch 上抛,不吞);不派生/评估/audit/提交坏上下文事件
    (events 0);坏 artifact 保全;无新引用签发(ctx 文件集合不变);
    无关 retrieve/claim 写入逐表披露。父上 resume 成功且 events 0→1
    ⇒ 行为红。"""
    runs_root = tmp_path / "runs"
    run_id = "r3pc3"
    artifacts = _start_after_claim(runs_root, run_id)
    files = _ctx_files(artifacts)
    assert len(files) == 1
    ref = json.loads(files[0].read_text(
        encoding="utf-8"))["payload"]["context_id"]
    mutation, new_id = _mutate_self_consistent_new_id(artifacts, ref)
    before = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    with pytest.raises(ConditionContractError) as ei:
        _public_resume(runs_root, run_id)
    detail = getattr(ei.value, "detail", {})
    assert detail.get("kind") == "context_reference_binding_mismatch"
    assert detail.get("expected_context_ref") == ref
    assert detail.get("recovered_context_id") == new_id
    after = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    deltas = _table_deltas(before, after)
    # 拒绝后零坏上下文事件/派生/审核提交
    assert deltas["events"] == 0
    assert deltas["endpoint_records"] == 0
    assert deltas["stop_reason_records"] == 0
    # 既有无关 retrieve/claim 写入如实披露(与案 2 同形)
    assert [name for name, delta in deltas.items() if delta == 1] == \
        ["budget_reservations", "search_actions",
         "search_commit_records"]
    # 坏 artifact 保全;ctx 文件集合不变(不默发新引用)
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    assert json.loads(path.read_text(encoding="utf-8")) == mutation
    assert [p.name for p in _ctx_files(artifacts)] == \
        [f"{CONTEXT_ARTIFACT_NAME}.json"]


def test_s5a_r3_case4_public_checked_legal_old_address_rejected(
        tmp_path) -> None:
    """案 4(公共链,自构造):checked 正规合法新内容 + 新 context_id
    写旧地址 ⇒ 公开 resume 同样首消费拒 binding mismatch;events 0;
    坏(合法载荷占旧地址)artifact 保全。父上 resume 成功 ⇒ 行为红。"""
    runs_root = tmp_path / "runs"
    run_id = "r3pc4"
    artifacts = _start_after_claim(runs_root, run_id)
    ref = json.loads(_ctx_files(artifacts)[0].read_text(
        encoding="utf-8"))["payload"]["context_id"]
    legal_new = build_path_context(
        condition_facts=[build_condition_fact(
            key="electron_acceptor", value="O2",
            status="known_present", source_ref="src:synthetic-present-2")],
        accumulated_requirements=[_req()],
        assessment_scope=["electron_acceptor"])
    assert legal_new.context_id != ref
    mutation = _mutate_checked_legal_new_content(
        artifacts, ref, legal_new.to_dict())
    before = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    with pytest.raises(ConditionContractError) as ei:
        _public_resume(runs_root, run_id)
    detail = getattr(ei.value, "detail", {})
    assert detail.get("kind") == "context_reference_binding_mismatch"
    assert detail.get("recovered_context_id") == legal_new.context_id
    after = _table_snapshot(runs_root / run_id / "pollutant.sqlite")
    deltas = _table_deltas(before, after)
    assert deltas["events"] == 0
    path = artifacts._path(f"ctx:{ref}", CONTEXT_ARTIFACT_NAME)
    assert json.loads(path.read_text(encoding="utf-8")) == mutation


def test_s5a_r3_case5_public_legal_transition_chain_preserved(
        tmp_path) -> None:
    """案 5(公共链,自构造正控):合法场景转换链保持 —— 显式
    source_ref 转换派生子上下文(**新 ID 新地址**),followup retrieve
    沿新 context_ref;全 run 所有 ctx 地址与载荷身份一一对应
    (无任何旧地址复用);父绿(修复不误伤合法转换)。"""
    runs_root = tmp_path / "runs"
    run_id = "r3pc5"
    plan = {
        "condition_facts": [
            {"key": "electron_acceptor", "value": "O2",
             "status": "unknown", "source_ref": "src:synthetic-unknown"}],
        "pools": {"CCO": [spec("A", "CC=O", "donor-A",
                               coproducts=["[H][H]"],
                               requirements=[{
                                   "key": "electron_acceptor",
                                   "level": "essential", "value": "O2",
                                   "source_refs":
                                       ["src:synthetic-necessity"]}])]},
        "scenario_transitions": [{
            "after_hypothesis_key": "A",
            "transition": {"source_ref": "user:switch-anaerobic",
                           "new_phase_id": "phase-1",
                           "new_scenario_ref": "scenario-anaerobic"}}],
        "schedule_budget": {"max_select": 1},
    }
    start_run(config=resolve_config(), runs_root=runs_root,
              run_id=run_id, smiles="CCO", max_depth=2,
              max_expansions=5, max_frontier_width=2,
              finder=object(), scripted=True,
              profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    artifacts = ArtifactStore(runs_root, run_id)
    files = _ctx_files(artifacts)
    payload_by_address: dict[str, dict] = {}
    for file in files:
        envelope = json.loads(file.read_text(encoding="utf-8"))
        address_id = file.parent.name[len("ctx:"):]
        # 修复后全部地址与载荷身份一一对应(合法链零旧地址复用)
        assert envelope["payload"]["context_id"] == address_id
        payload_by_address[address_id] = envelope["payload"]
    assert any(p.get("phase_id") == "phase-1"
               for p in payload_by_address.values())
    child_ids = [aid for aid, p in payload_by_address.items()
                 if p.get("phase_id") == "phase-1"]
    conn = sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    try:
        transitions = conn.execute(
            "SELECT * FROM search_actions WHERE action_kind ="
            " 'scenario_transition'").fetchall()
        assert len(transitions) == 1
        assert transitions[0]["status"] == "done"
        followups = [r for r in conn.execute(
            "SELECT * FROM search_actions WHERE action_kind ="
            " 'retrieve' ORDER BY created_at, action_id").fetchall()
            if (json.loads(r["payload"]) or {}).get("source_event_id")]
        assert followups
        # followup 沿新引用(子新 ID,不落旧地址)
        assert {str(r["context_ref"]) for r in followups} == set(child_ids)
        # 子上下文保留 parent_context_ref 链(指向根)
        root_ids = [aid for aid, p in payload_by_address.items()
                    if p.get("phase_id") != "phase-1"]
        assert root_ids
        for child_id in child_ids:
            assert payload_by_address[child_id][
                "parent_context_ref"] in root_ids
    finally:
        conn.close()


# ------------------------------------------------------ endpoint 入口


def test_s5a_r3_endpoint_entries_reuse_common_guard(tmp_path) -> None:
    """入口矩阵(endpoint 三处):坏上下文(新 ID 占旧地址)在
    endpoint 派生消费同样被共同守卫拒 —— F02 依赖继承与条件评估
    包成 ``endpoint_context_consumption_failed``(错误文本披露绑定
    kind);条件快照直构入口直接上抛 binding mismatch。父上共同
    load 返回新身份 ⇒ 消费不拒,行为红。"""
    runs_root = tmp_path / "runs"
    run_id = "r3ep"
    artifacts = _start_after_claim(runs_root, run_id)
    ref = json.loads(_ctx_files(artifacts)[0].read_text(
        encoding="utf-8"))["payload"]["context_id"]
    _mutate_self_consistent_new_id(artifacts, ref)
    # 让 resume 走到首消费拒(decide 落账携带旧 context_ref)
    with pytest.raises(ConditionContractError):
        _public_resume(runs_root, run_id)
    from pathway_v43.pollutant.store import PollutantPathwayStore
    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    from pathway_v43.pollutant.search import SearchLedger
    ledger = SearchLedger(store, artifacts, run_id)
    with pytest.raises(EndpointContractError) as ei:
        _inherited_unresolved_dependencies(ledger)
    assert ei.value.detail.get("kind") == \
        "endpoint_context_consumption_failed"
    cause = getattr(ei.value, "__cause__", None)
    assert _binding_kind(cause) == "context_reference_binding_mismatch"
    with pytest.raises(EndpointContractError) as ei2:
        _route_condition_assessments(ledger)
    assert ei2.value.detail.get("kind") == \
        "endpoint_context_consumption_failed"
    cause2 = getattr(ei2.value, "__cause__", None)
    assert _binding_kind(cause2) == "context_reference_binding_mismatch"
    with pytest.raises(ConditionContractError) as ei3:
        _route_conditions_snapshot(ledger)
    assert _binding_kind(ei3.value) == "context_reference_binding_mismatch"


# ------------------------------------------------------ 入口矩阵守门


def test_s5a_r3_entry_matrix_static_guard() -> None:
    """入口矩阵守门(静态):三个 runflow 执行入口(decide/expand/
    scenario_transition)与三个 endpoint 派生入口全部经
    production.load_context 同一守卫;production 侧含引用绑定核验;
    runflow/endpoint/search/path_context/store 本轮零源码触碰。"""
    runflow_src = (_SRC / "runflow.py").read_text(encoding="utf-8")
    endpoint_src = (_SRC / "endpoint.py").read_text(encoding="utf-8")
    production_src = (_SRC / "production.py").read_text(encoding="utf-8")
    # runflow:三个执行入口各自调用共同 load_context(decide/expand/
    # transition 的 receipt context_ref)
    assert runflow_src.count("load_context(self.ledger.artifact_store") == 3
    assert "from .production import" in runflow_src
    # endpoint:三个派生入口(依赖继承/条件评估/条件快照)
    assert endpoint_src.count(
        "context = load_context(ledger.artifact_store, context_ref)") \
        + endpoint_src.count(
            "context = load_context(ledger.artifact_store, str(row"
            "[\"context_ref\"]))") == 3
    # production:共同守卫含首消费引用绑定核验与结构化披露
    assert "context_reference_binding_mismatch" in production_src
    assert "expected_context_ref" in production_src
    assert "recovered_context_id" in production_src
    assert "旧引用不复用" in production_src


# ------------------------------------------------------ 契约版本登记

_FROZEN_SHA256 = "7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872" \
    "efedf5f886503c4907064e4"
_FREEZE_RECORD_SHA256 = "6e046e2970a102c63e693cebb81f2564b5d79fea" \
    "1b6e7a776b0fc00c09662610"
_PATH_CONTEXT_SHA256 = "971ad00f42fc56915bad3724300759aa86552bf0" \
    "8199f8335c7f0286b40d588d"
_FROZEN_DOC = _REPO_ROOT / "docs" / \
    "POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md"
_FREEZE_RECORD_DOC = _REPO_ROOT / "docs" / \
    "POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD_V1_2026-10-08.md"
# G01 安全隔离树按白名单只复制 src/tests/configs/scripts/assets,
# 不含 docs/ ⇒ 冻结文本守卫在隔离树内显式跳过(不凑执行),字节
# 完整性由证据层 shasum 封包核验(见 review_evidence r3 目录
# frozen_integrity.json);仓内树与父全量 worktree 内守卫执行。


@pytest.mark.skipif(
    not _FROZEN_DOC.exists() or not _FREEZE_RECORD_DOC.exists(),
    reason="frozen criteria text not copied into allowlisted isolation "
           "trees (G01 boundary); byte integrity verified at the "
           "evidence level (shasum in review_evidence package)")
def test_s5a_r3_contract_version_registration_and_frozen_integrity() \
        -> None:
    """S5a 回修 r3:production 链 -1→-2(S5A-05 首消费引用绑定,由
    search-production-2 承载)、profile -22→-23(聚合登记);evaluation-3
    / template-3 **版本号不变**(五处 known×unknown 限定物种键等 P2
    文案为拟冻结前同步,非语义变更);reference-graph-1/split-manifest-1
    不变;criteria-v1 冻结正文/FREEZE_RECORD/path_context 冻结判决
    逐字节不改(绑定守卫在 production 消费侧)。"""
    assert SEARCH_PRODUCTION_VERSION == "ppv1-search-production-2"
    assert PPV1_PROFILE_SCHEMA_VERSION == "ppv1-profile-23"
    assert PPV1_EVALUATION_VERSION == "ppv1-evaluation-3"
    assert PPV1_PREREGISTRATION_TEMPLATE_VERSION == \
        "ppv1-preregistration-template-3"
    assert PPV1_REFERENCE_GRAPH_VERSION == "ppv1-reference-graph-1"
    assert PPV1_SPLIT_MANIFEST_VERSION == "ppv1-split-manifest-1"
    assert hashlib.sha256(
        _FROZEN_DOC.read_bytes()).hexdigest() == _FROZEN_SHA256
    assert hashlib.sha256(
        _FREEZE_RECORD_DOC.read_bytes()).hexdigest() == \
        _FREEZE_RECORD_SHA256
    assert hashlib.sha256(
        (_SRC / "path_context.py").read_bytes()).hexdigest() == \
        _PATH_CONTEXT_SHA256


def test_s5a_r3_p2_text_sync_species_key_limitation() -> None:
    """搭车 P2 文字同步(复审 R3 §5 五处):known×unknown 限定物种键
    (非物种键任一适用 unknown 仍 condition_unknown)、删合法链
    "顺序相关"尾巴;condition_unknown 具体枚举、canonical-by-key 代价、
    value 仅 repr 展示、实体只证存在不证浓度、指标只分桶且正式分母
    TBD 落进 proposed 模板文本(仍 proposed 不冻结,版本号不变)。"""
    from pathway_v43.pollutant.preregistration import \
        build_preregistration_template
    rule = build_preregistration_template()["condition_policy"]["rule"]
    assert "仅物种键" in rule
    assert "非物种键任一适用 unknown 事实" in rule
    assert "两序结果一致" in rule
    assert "顺序相关" not in rule
    assert "condition_unknown(具体枚举" in rule
    assert "repr 展示串" in rule
    assert "不证浓度/阈值达标" in rule
    assert "正式分母 TBD" in rule
    evaluation_src = (_SRC / "evaluation.py").read_text(encoding="utf-8")
    assert "仅物种键" in evaluation_src
    # 旧"顺序相关"断言尾巴已删(仅 r3 同步说明引用该删除时出现)
    assert "既有实现,顺序相关" not in evaluation_src
    assert "裁决,顺序相关" not in evaluation_src
    profile_src = (_SRC / "profile.py").read_text(encoding="utf-8")
    assert "仅物种键" in profile_src
