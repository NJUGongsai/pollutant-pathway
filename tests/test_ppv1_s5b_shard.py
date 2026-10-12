"""PPV1 S5b 白名单域协调者锁测试(s5b-orchestrator-3;零网络零金标)。

覆盖(HPC 多作业分片适配轮验收):
- **同 qid 双发拒**:另一协调者持某 qid 的锁 ⇒ 后到者在该 qid 处
  结构化拒(kind=s5b_coordinator_active,conflicting_qid 披露),
  已获部分全部释放(不留半套锁);拒在 worker 派发前(fail-fast);
- **不同 qid 并发放行**:不相交 qid 白名单的两个协调者(双线程,
  每者各自派 worker 子进程)同批根并发跑完,互不拒绝;闸门/批根
  共享文件并发写盘只落完整 JSON(原子 replace);
- **断点续跑不回退**:分片跑完后整序重入 ⇒ 全 SKIP、case 字节
  不变(既有 resume 语义在白名单域锁下保持);
- **冻结参数域**:qids 白名单不进冻结副本(分片合法);分片同参
  必要性由 orchestration.json 比对守卫(含并发首写竞态:短 flock
  串行下后到者必读到先到者副本 ⇒ 不同参恰好一方冲突拒);
- **v2→v3 版本契约**:orchestration.json 的 orchestrator_version
  不一致 ⇒ 续跑拒(预注册纪律:协调语义变化须新批根);
- **白名单去重**(同 qid 重复项不产生 flock 自冲突/重复报告行)、
  **锁文件名单射**(消毒碰撞由哈希区分)、**fd 余量预检**结构化拒。

环境纪律:零网络(scripted 模型桩子进程,零真实 HTTP);密钥不落
任何文件/日志;合成 qid/分子与真实 298 金标集合零重叠(沿用
test_ppv1_s5b_runtime.py 的既有合成集)。
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_DEFAULT_PROFILE_POLICY,
    S5B_ORCHESTRATOR_VERSION,
    S5bOrchestratorError,
    read_case,
    run_s5b_batch,
)
from tests.test_ppv1_s5b_runtime import (  # noqa: E402
    SYNTH_QUESTIONS,
    synth_pool_provider,
)

# v3 新面惰性导入(父 HEAD 上缺这些符号 ⇒ 相关测试在调用点红,
# 文件其余部分仍可收集——父红绿按"行为红/版本字面量红/新面红"
# 分类留档;本树上无差别)
def _locks_cls():
    from pathway_v43.pollutant.s5b_orchestrator import \
        _WhitelistCoordinatorLocks
    return _WhitelistCoordinatorLocks


def _lock_name_fn():
    from pathway_v43.pollutant.s5b_orchestrator import _qid_lock_name
    return _qid_lock_name


def _fd_check_fn():
    from pathway_v43.pollutant.s5b_orchestrator import \
        _check_lock_fd_headroom
    return _check_lock_fd_headroom


# 分片/续跑/同 qid 拒共用同一组冻结参数(orchestration.json 比对须一致)
SHARD_RUN_PARAMS = {"workers": 2, "poll_s": 0.2, "gate_max_calls": 50}


def _build_synth_batch(root: Path, tag: str) -> Path:
    questions_path = root / "questions.jsonl"
    questions_path.write_text(
        "\n".join(json.dumps(q) for q in SYNTH_QUESTIONS) + "\n",
        encoding="utf-8")
    batch_root = root / "batch"
    build_question_batch(
        questions_path, batch_root, batch_tag=tag,
        pool_provider=synth_pool_provider,
        provider_kind="scripted", synthetic_review=True)
    return batch_root


def _run_shard(batch_root: Path, runs_root: Path, qids: list[str],
               env_stub: Path, out: dict, key: str,
               **overrides) -> None:
    """线程目标:scripted 桩 env 下跑一个分片;异常捕获不外抛。"""
    old = os.environ.get("S5B_MODEL_STUB_SCRIPT")
    os.environ["S5B_MODEL_STUB_SCRIPT"] = str(env_stub)
    try:
        params = dict(SHARD_RUN_PARAMS)
        params.update(overrides)
        out[key] = run_s5b_batch(
            batch_root, runs_root=runs_root, qids=qids, **params)
    except Exception as exc:  # noqa: BLE001 —— 线程异常捕获后在主线程断言
        out[key] = exc
    finally:
        if old is None:
            os.environ.pop("S5B_MODEL_STUB_SCRIPT", None)
        else:
            os.environ["S5B_MODEL_STUB_SCRIPT"] = old


# ---------------------------------------------------------------- 锁域单测


def test_qid_lock_names_injective(tmp_path) -> None:
    """锁文件名:不同 qid 必不同名(消毒碰撞由 sha8 区分);名字限
    文件名安全字符集;同一 qid 稳定同名(锁域判定不依赖消毒)。"""
    lock_name = _lock_name_fn()
    assert lock_name("bt0002") != lock_name("bt0003")
    # 消毒后同形("a/b" vs "a_b")但原值不同 ⇒ 哈希区分
    assert lock_name("a/b") != lock_name("a_b")
    assert lock_name("a/b") == lock_name("a/b")
    for qid in ("bt0002", "a/b", "SYNTH-Q001", "含中文的 qid"):
        name = lock_name(qid)
        assert name.endswith(".lock")
        assert all(c.isalnum() or c in "._-" for c in name)


def test_lock_domain_same_qid_conflict(tmp_path) -> None:
    """同 qid 互斥:持 {Q1} 时取 [Q1,Q2] ⇒ 在 Q1 拒(kind+qid 披露);
    失败后已获部分(无)不留残余;退出后再取成功(锁确实释放)。"""
    Locks = _locks_cls()
    with Locks(tmp_path, ["Q1"]):
        second = Locks(tmp_path, ["Q1", "Q2"])
        with pytest.raises(S5bOrchestratorError) as excinfo:
            second.acquire()
        detail = excinfo.value.detail
        assert detail["kind"] == "s5b_coordinator_active"
        assert detail["conflicting_qid"] == "Q1"
        assert second._handles == {}  # 失败自释放:未留半套锁
    # 持有者退出后同域可再取(flock 已释放)
    third = Locks(tmp_path, ["Q1", "Q2"])
    third.acquire()
    third.release()


def test_lock_domain_partial_acquire_released_on_failure(
        tmp_path) -> None:
    """部分获取后撞已持 qid ⇒ 已获部分回滚:[Q1,Q3] 撞持 {Q3},
    Q1 已获须释放(否则后续再取 Q1 会假冲突)。"""
    Locks = _locks_cls()
    with Locks(tmp_path, ["Q3"]):
        second = Locks(tmp_path, ["Q1", "Q3"])
        with pytest.raises(S5bOrchestratorError) as excinfo:
            second.acquire()
        assert excinfo.value.detail["conflicting_qid"] == "Q3"
        assert second._handles == {}  # Q1(排序先于 Q3 已获)被回滚
        # 持有者仍持 Q3:取 Q3 仍拒(锁没被失败方误伤)
        fourth = Locks(tmp_path, ["Q3"])
        with pytest.raises(S5bOrchestratorError):
            fourth.acquire()
    # 两者都退出后:全集可一次取全
    with Locks(tmp_path, ["Q1", "Q3"]):
        pass


def test_lock_domain_disjoint_pass_and_files(tmp_path) -> None:
    """不相交白名单并发放行(锁可并存);锁文件数 = 唯一 qid 数。"""
    Locks = _locks_cls()
    with Locks(tmp_path, ["Q1", "Q2"]):
        with Locks(tmp_path, ["Q3"]):
            with Locks(tmp_path, ["Q2_1"]):
                pass
    files = sorted(p.name for p in (tmp_path / "coord").glob("*.lock"))
    assert len(files) == 4  # Q1,Q2,Q3,Q2_1 各一把(不随协调者数增长)


def test_lock_fd_headroom_insufficient_rejected(
        tmp_path, monkeypatch) -> None:
    """fd 余量不足 ⇒ 结构化拒(fail-closed 提示 ulimit),不裸抛。"""
    batch_root = _build_synth_batch(tmp_path, "s5bshardfd")
    monkeypatch.setattr(
        "pathway_v43.pollutant.s5b_orchestrator.resource.getrlimit",
        lambda which: (8, 8))
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(
            batch_root, runs_root=tmp_path / "runs",
            qids=["SYNTH-Q001"], **SHARD_RUN_PARAMS)
    assert excinfo.value.detail["kind"] == \
        "s5b_lock_fd_headroom_insufficient"
    monkeypatch.undo()  # 只影响本测试(后续 run 不受限)


# ---------------------------------------------------------------- 并发分片


@pytest.fixture(scope="module")
def sharded_batch(tmp_path_factory):
    """同批根两个不相交白名单分片并发跑(module 级一次)。"""
    root = tmp_path_factory.mktemp("s5b_shard")
    batch_root = _build_synth_batch(root, "s5bshard")
    stub_path = root / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    runs_root = root / "runs"
    out: dict = {}
    t1 = threading.Thread(
        target=_run_shard,
        args=(batch_root, runs_root, ["SYNTH-Q001", "SYNTH-Q002"],
              stub_path, out, "t1"))
    t2 = threading.Thread(
        target=_run_shard,
        args=(batch_root, runs_root, ["SYNTH-Q003"], stub_path, out, "t2"))
    t1.start()
    t2.start()
    t1.join(timeout=300)
    t2.join(timeout=300)
    assert not t1.is_alive() and not t2.is_alive()
    return {"root": root, "batch_root": batch_root,
            "runs_root": runs_root, "out": out}


def test_concurrent_disjoint_shards_both_admitted_and_complete(
        sharded_batch) -> None:
    """正控:不相交白名单双协调者并发放行且各自跑完(任何全局性
    单协调者锁都会令后到线程抛 s5b_coordinator_active ⇒ 本测试红)。"""
    r1, r2 = sharded_batch["out"]["t1"], sharded_batch["out"]["t2"]
    assert isinstance(r1, dict), f"分片 1 异常:{r1!r}"
    assert isinstance(r2, dict), f"分片 2 异常:{r2!r}"
    assert r1["n_total"] == 2 and r1["n_completed"] == 2 \
        and r1["n_failed"] == 0
    assert r2["n_total"] == 1 and r2["n_completed"] == 1 \
        and r2["n_failed"] == 0
    # 三题终态 case 全在(各 worker 原子落盘;run 级目录各建各的)
    for entry in SYNTH_QUESTIONS:
        case = read_case(sharded_batch["batch_root"], entry["qid"])
        assert case is not None and case["status"] == "completed"
    # 并发写盘的共享信息文件只落完整 JSON(原子 replace;半截会解析炸)
    for rel in ("progress.json", "batch_report.json",
                "orchestration.json", "profile_policy.json",
                "gate/gate.json"):
        json.loads(
            (sharded_batch["batch_root"] / rel).read_text(
                encoding="utf-8"))
    # 闸门共享:两分片同一 gate 域(单文件;scripted 桩零真实请求)
    gate = json.loads((sharded_batch["batch_root"] / "gate" / "gate.json")
                      .read_text(encoding="utf-8"))
    assert gate["max_in_flight"] == 40 and gate["max_calls"] == 50
    # v3 落盘契约:coord/ 目录逐 qid 锁文件在位,遗留 v2 coord.lock 不再产生
    coord_files = list((sharded_batch["batch_root"] / "coord").glob(
        "*.lock"))
    assert len(coord_files) == 3
    assert not (sharded_batch["batch_root"] / "coord.lock").exists()
    # 冻结副本:qids 不进冻结域(分片合法);版本=v3
    frozen = json.loads(
        (sharded_batch["batch_root"] / "orchestration.json").read_text(
            encoding="utf-8"))
    assert frozen["orchestrator_version"] == S5B_ORCHESTRATOR_VERSION
    assert "qids" not in frozen


def test_resume_after_shards_full_order_all_skip(
        sharded_batch) -> None:
    """断点续跑不回退:分片跑完后整序重入 ⇒ 全 SKIP,case 字节不变。"""
    batch_root = sharded_batch["batch_root"]
    cases_before = {
        q["qid"]: read_case(batch_root, q["qid"]) for q in SYNTH_QUESTIONS}
    report = run_s5b_batch(
        batch_root, runs_root=sharded_batch["runs_root"],
        **SHARD_RUN_PARAMS)
    assert report["n_completed"] == 3
    assert report["skipped_already_terminal"] == 3
    assert report["n_failed"] == 0
    for qid, case in cases_before.items():
        assert read_case(batch_root, qid) == case


def test_same_qid_second_coordinator_rejected_before_dispatch(
        sharded_batch) -> None:
    """负控:同 qid 双发在锁处拒(fail-fast 于任何 worker 派发;
    不新增 run 目录/case 文件),conflicting_qid 机读披露。"""
    Locks = _locks_cls()
    batch_root = sharded_batch["batch_root"]
    runs_root = sharded_batch["runs_root"]
    run_dirs_before = sorted(p.name for p in runs_root.iterdir())
    cases_before = sorted(
        p.name for p in (batch_root / "cases").iterdir())
    with Locks(batch_root, ["SYNTH-Q001"]):
        with pytest.raises(S5bOrchestratorError) as excinfo:
            run_s5b_batch(
                batch_root, runs_root=runs_root,
                qids=["SYNTH-Q001", "SYNTH-Q002"],
                **SHARD_RUN_PARAMS)
        detail = excinfo.value.detail
        assert detail["kind"] == "s5b_coordinator_active"
        assert detail["conflicting_qid"] == "SYNTH-Q001"
    # 拒在派发前:run 目录与 case 文件零新增
    assert sorted(p.name for p in runs_root.iterdir()) == run_dirs_before
    assert sorted(p.name for p in (batch_root / "cases").iterdir()) \
        == cases_before


# ---------------------------------------------------------------- 冻结域


def test_concurrent_first_launch_param_divergence_one_side_rejected(
        tmp_path) -> None:
    """并发首写竞态关闭:两分片同刻首跑而参数不同 ⇒ 短 flock 串行下
    后到者必读到先到者副本 ⇒ 恰好一方 s5b_orchestration_conflict
    (无"双双见缺文件双写、双双放行"窗口)。"""
    root = tmp_path
    batch_root = _build_synth_batch(root, "s5bshardrace")
    stub_path = root / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    runs_root = root / "runs"
    out: dict = {}
    t1 = threading.Thread(
        target=_run_shard, args=(batch_root, runs_root,
                                 ["SYNTH-Q001"], stub_path, out, "t1"),
        kwargs={"gate_max_calls": 50})
    t2 = threading.Thread(
        target=_run_shard, args=(batch_root, runs_root,
                                 ["SYNTH-Q002"], stub_path, out, "t2"),
        kwargs={"gate_max_calls": 60})
    t1.start()
    t2.start()
    t1.join(timeout=300)
    t2.join(timeout=300)
    assert not t1.is_alive() and not t2.is_alive()
    results = list(out.values())
    conflicts = [r for r in results if isinstance(
        r, S5bOrchestratorError)
        and r.detail.get("kind") == "s5b_orchestration_conflict"]
    reports = [r for r in results if isinstance(r, dict)]
    assert len(conflicts) == 1, f"恰好一方冲突拒:{[repr(r) for r in results]}"
    assert len(reports) == 1  # 另一方按自己的参数正常跑完 1 题
    # 冻结副本唯一且与胜者一致(败者未覆盖)
    frozen = json.loads((batch_root / "orchestration.json").read_text(
        encoding="utf-8"))
    assert frozen["gate_max_calls"] == reports[0]["gate"]["max_calls"]


def test_v2_batch_root_rejected_for_v3_coordinator(tmp_path) -> None:
    """版本契约:s5b-orchestrator-2 的既有冻结副本 ⇒ v3 续跑拒
    (预注册纪律:协调语义变化须新批根;fail-closed 不静默兼容)。"""
    root = tmp_path
    batch_root = _build_synth_batch(root, "s5bshardv2")
    runs_root = root / "runs"
    v2_frozen = {
        "orchestrator_version": "s5b-orchestrator-2",
        "workers": SHARD_RUN_PARAMS["workers"],
        "max_in_flight": 40, "gate_rpm": 180,
        "gate_tpm": 2_700_000,
        "gate_max_calls": SHARD_RUN_PARAMS["gate_max_calls"],
        "budget_guard": None,
        "profile_policy": S5B_DEFAULT_PROFILE_POLICY,
        "runs_root": str(runs_root),
        "frozen_at": "2026-10-09T00:00:00",
    }
    (batch_root / "orchestration.json").write_text(
        json.dumps(v2_frozen, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(
            batch_root, runs_root=runs_root,
            qids=["SYNTH-Q001"], **SHARD_RUN_PARAMS)
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"


def test_whitelist_duplicates_deduped(tmp_path) -> None:
    """白名单重复项:去重执行(同 qid flock 自冲突防护);报告行唯一。"""
    root = tmp_path
    batch_root = _build_synth_batch(root, "s5bsharddup")
    stub_path = root / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "first_pool"}),
                         encoding="utf-8")
    out: dict = {}
    _run_shard(batch_root, root / "runs",
               ["SYNTH-Q001", "SYNTH-Q001", "SYNTH-Q001"],
               stub_path, out, "t")
    report = out["t"]
    assert isinstance(report, dict), f"异常:{report!r}"
    assert report["n_total"] == 1 and report["n_completed"] == 1
    assert len(report["cases"]) == 1
    cases = list((batch_root / "cases").glob("*.json"))
    assert len(cases) == 1


def test_orchestrator_version_is_v3() -> None:
    """版本钉死:白名单域锁语义由 s5b-orchestrator-3 承载。"""
    assert S5B_ORCHESTRATOR_VERSION == "s5b-orchestrator-3"
    # fd 预检正常余量下放行(不误拒常规批)
    _fd_check_fn()(3, 2)
