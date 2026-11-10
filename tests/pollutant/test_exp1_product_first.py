"""EXP1「产物优先 + 核验反馈」实施测试(PF1–PF11;实施书 §3)。

环境纪律:零真实模型、零网络、零金标、零题面 —— 全部走
``ScriptedRealModelAdapter``(与真实适配器同一 ppv1_real_fetch 调用序)
与合成通用分子(乙醇/乙酸/苯酚方向,与真实题卷零关系)。判分代码
(evaluation.py / s5b_scoring.py)在本文件里零 import。

覆盖(与实施书 §3 一一对应):
- PF1 产物优先正控:编译执行成功 ⇒ full 级、事件提交、主产物=声明产物;
- PF2 第 1 轮不可解析第 2 轮修正 ⇒ 恰 1 个反馈轮、第 2 轮落事件;
- PF3 3 轮全失败 ⇒ novel 丢弃、池条目照常落事件、无 PPV1RunError;
- PF4 新增重原子 > 阈值 ⇒ 声明桶(不提交事件)+ 阈值边界正控;
- PF5 对冲(共产物塞无关分子)⇒ 不落事件;product_set_mismatch 反馈
  只带 executed_components;
- PF6 反馈白名单(机器断言键集封闭);
- PF7 A 臂逐字节等价(基线哈希 = 改动前采集值);
- PF8 反馈轮登记后崩溃 ⇒ resume 复用同一轮、不另发请求;
- PF9 第 5 次真实请求在登记处被拒(拒绝先于网络);
- PF10 开关/版本 fail-closed(批冻结、旧批不升级、两版反馈块各自可过);
- PF11 主产物重指派(断裂型反应;不在执行组分 ⇒ 不重指派并记录)。

EXP1 C 臂增量(2026-11-06,PC1–PC8;实施书 §10):
- PC1 盲写载荷零池内容(pool_hypotheses=[]、池 ID/池产物不出现在
  载荷文本;系统提示词 v2_pf_blind);
- PC2 合并载荷:恰一条目带 origin=blind_first(可排序 prepared ID)、
  模型位次以第②阶段排序为准、产物落事件;
- PC3 反馈轮两阶段共用(盲写 2 轮 + 合并 1 轮 = 3,总请求 5);
- PC4 预算(第 6 次真实请求登记处拒);
- PC5 阶段间崩溃(crash_after=after_blind_response)⇒ resume 复用
  盲写响应、零重发;
- PC6 A/B 臂载荷与提示词哈希不变(改动前基线;b_payload_base 与
  a_payload 同值)+ B 臂 run 级回归;
- PC7 盲写全失败(轮耗尽/弃权)⇒ 合并照常、池条目落事件;
- PC8(CC 追加)模型自写池侧声明键 ⇒ 静默忽略 + 记录键名(B/C 两臂),
  事件参与物只来自编译器生成的 spec。

EXP1 C 臂 P1 回修(2026-11-06,回应 docs/reviews/codex/
EXP1_CARM_CODEX_REVIEW_2026-11-06.md §4/§5;PC9–PC12):
- PC9a(P1-1 反例 A)两阶段自报 ID 同名(产物不同)且合并响应显式排序
  [新 novel, 池, 盲写] ⇒ 位次按合并 prepared ID 生效(新 1/池 2/盲写 3),
  note 位次键 = prepared ID 命名空间(自报 ID 不覆盖);
- PC9b(P1-1 反例 B)合并响应完全不提盲写 prepared ID ⇒ 盲写条目
  rank_basis=deterministic_fallback、排在显式排序之后(不继承同名新提案);
- PC10(P1-2 反例)盲写自报 ID 与真实池逻辑 key 同名 ⇒ 合并载荷里只有
  盲写条目带 origin=blind_first,真实池条目无 origin;
- PC11(P1-3 反例,B 臂)核验失败/早轮被反馈冲掉的提案的三键仍在 note;
  clean 响应与 A 臂零新键(正控);
- PC12(P1-3 同款,C 臂)合并阶段(及盲写+合并两阶段)带三键且核验失败
  ⇒ note 仍记录键名。

EXP1 方案甲分桶(2026-11-06,冻结预注册 §4.3;PF12–PF21):
- PF12 条件 1(新增 ≤8 兜底):+10 C 链 ⇒ declared_unrecognized;
- PF13 条件 2(移除 ≤8 兜底):癸基乙酸酯 → 乙酸 + 癸醇(移除 10)⇒
  declared_unrecognized;
- PF14 条件 3(新增片段 ≤2):3 个白名单单原子片段 ⇒ declared;2 个
  片段(双羟化)⇒ full;
- PF15 条件 4(白名单图匹配):+4 C 非白名单片段 ⇒ declared_unrecognized;
  PO₃/SO₃ 4 原子白名单 ⇒ full;NOVEL_BIG(+6)⇒ declared_unrecognized;
- PF16 条件 5(连接点):编译器先拒无锚新增原子(center_empty:
  added_without_anchor)⇒ 该形态在编译链不可达;合成度量单测覆盖
  分桶函数的 no-anchor / bad-anchor 拒因;
- PF17 条件 6(元素域):含 Si 产物 ⇒ declared_unrecognized;
- PF18 条件 7(移除对账):水解离去基(O)⇒ full;大块移除但共产物
  声明接住(乙醇)⇒ full;未声明大块移除在编译链被 product_set_mismatch
  先拒(不可达证据)+ 合成度量单测覆盖未认领拒因;
- PF19 净零改写旗标:异构化(乙醇 → 二甲醚)⇒ full + net_zero=True;
  羟化 ⇒ net_zero=False;
- PF20 已知半分子表:CoA/GSH/糖基组成 ⇒ declared_recognized;对不上
  表的组成 ⇒ declared_unrecognized(合成度量单测);
- PF21 H 容差/质子化归一 + A 臂离线同尺读数 + 策略身份字段。
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import stable_id  # noqa: E402
from pathway_v43.pollutant.chemstate import (  # noqa: E402
    build_chemical_state,
)
from pathway_v43.pollutant.model_protocol import (  # noqa: E402
    FEEDBACK_ELIGIBLE,
    NOVEL_REACTION_SPEC_FORBIDDEN_KEYS,
    NOVEL_VERIFICATION_FAILED_KIND,
    ModelProtocolError,
    format_feedback_rounds_used,
    latest_format_feedback_round,
    parse_model_proposals,
    register_format_feedback_round,
)
from pathway_v43.pollutant.novel_product_first import (  # noqa: E402
    ADDED_HEAVY_ATOMS_BACKSTOP,
    BUCKET_KIND_DECLARED_RECOGNIZED,
    BUCKET_KIND_DECLARED_UNRECOGNIZED,
    BUCKET_KIND_FULL,
    FAILURE_PRODUCT_SET_MISMATCH,
    FAILURE_PRODUCT_UNPARSEABLE,
    KNOWN_MOIETY_TABLE,
    MAX_ADDED_FRAGMENTS,
    NOVEL_BUCKET_POLICY_VERSION,
    NOVEL_BUCKET_TABLE_SHA256,
    REMOVED_HEAVY_ATOMS_BACKSTOP,
    VERIFICATION_TIER_DECLARED,
    VERIFICATION_TIER_FULL,
    _classify_bucket,
    _known_moiety_for,
    _reassign_principal_components,
    classify_bucket_metrics,
    compile_novel_product_first,
    compute_arm_a_bucket_readout,
    compute_novel_bucket,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    FORMAT_FEEDBACK_POLICY_VERSION,
    FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST,
    NOVEL_PROTOCOL_ATOM_EDIT,
    NOVEL_PROTOCOL_BLIND_FIRST,
    NOVEL_PROTOCOL_PRODUCT_FIRST,
    build_profile_identity_block,
    format_feedback_policy_version_for,
    validate_format_feedback_policy,
    validate_frozen_format_feedback_policy,
)
from pathway_v43.pollutant.production import (  # noqa: E402
    prepare_hypothesis,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION_V2,
    PROPOSALS_PROMPT_VERSION_V2_PF,
    PROPOSALS_PROMPT_VERSION_V2_PF_BLIND,
    S5B_REAL_MODEL_VERSION,
    ScriptedRealModelAdapter,
    build_proposals_user_payload,
    proposals_prompt_version,
    proposals_system_prompt,
    render_verification_feedback,
)
from pathway_v43.pollutant.runflow import (  # noqa: E402
    PPV1RunError,
    resume_ppv1_run,
    start_ppv1_run,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    build_question_batch,
)
from pathway_v43.pollutant.s5b_orchestrator import (  # noqa: E402
    S5B_ARM_EXACT_BUDGETS,
    S5B_DEFAULT_PROFILE_POLICY,
    S5bOrchestratorError,
    load_novel_protocol,
    normalize_novel_protocol,
    run_s5b_batch,
    validate_case,
    validate_product_first_budget,
    validate_profile_policy,
)
from pathway_v43.pollutant.search import (  # noqa: E402
    ACTION_KIND_EXPAND_HYPOTHESIS,
    SearchBudgetExhausted,
    SearchCrashInjection,
    SearchLedger,
    search_policy_version,
)


# ---------------------------------------------------------------- 固定基线

# PF7 基线(改动前 @ 8a5af65 采集;主会话同值核对)
SUBSTRATE_SMILES = "CCO"
ATOM_ID_MAP = {"0": "C", "1": "C", "2": "O", "3": "H", "4": "H",
               "5": "H", "6": "H", "7": "H", "8": "H"}
POOL_ENTRIES = [
    {"hypothesis_id": "SYN-POOL-001", "product_smiles": "CC(=O)O",
     "transformation_ref": "rhea:12345", "coproducts": []},
    {"hypothesis_id": "SYN-POOL-002", "product_smiles": "O=Cc1ccccc1",
     "transformation_ref": "rhea:67890", "coproducts": ["O"]},
]
PF7_PROMPT_SHA256 = \
    "c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598"
PF7_PAYLOAD_SHA256 = \
    "aab7d6e4d18043b3976e43e2bddf04ae866fed9f418dc8039bbe8786c0f6bcff"

# 池条目(合成;CCO → CC=O,与各 PF 用例的 novel 产物不同以免去重合并)
POOL_SPEC = {
    "key": "rec-SYNTH_POOL_A@L3", "product_smiles": "CC=O",
    "coefficient": 1,
    "transformation_ref": "SYNTH_POOL_A@L3",
    "origin_group_key": "rec-source:SYNTH_POOL_A@L3",
    "edits": [
        {"op": "change_bond_order", "atom1": "S_C_2",
         "atom2": "S_O_1", "from_order": "single", "to_order": "double"},
    ],
    "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_C_2": "S_C_2",
                                       "S_O_1": "S_O_1"},
                  "equivalence_classes": [], "ref": "align-pool-A"},
    "expectation": {"target_smiles": "CC=O"},
}
# 产物优先用例(方案甲 2026-11-06)
NOVEL_OK = "CC(=O)O"          # +1 O(白名单)⇒ full
NOVEL_PO3 = "CCOP(=O)(O)O"    # +PO3(4 原子白名单)⇒ full(条件 4 边界正控)
NOVEL_SO3 = "CCOS(=O)(=O)O"   # +SO3(4 原子白名单)⇒ full
NOVEL_C4_CHAIN = "CCCCCCO"    # +4 C 非白名单片段 ⇒ declared_unrecognized
NOVEL_BIG = "OCCCCCC(=O)O"    # +5(C4 链 + O)⇒ declared_unrecognized
NOVEL_C10_CHAIN = "OCCCCCCCCCCCC"  # +10 C ⇒ 条件 1 反例
NOVEL_SI = "CCO[Si](C)(C)C"   # 产物含 Si ⇒ 条件 6 反例
NOVEL_3_FRAGS = "NC(F)(O)CO"  # +N/F/O 三块(各自白名单)⇒ 条件 3 反例
NOVEL_2_FRAGS = "OCC(=O)O"    # +2 个 O 两块 ⇒ full(条件 3 正控)
NOVEL_NET_ZERO = "COC"        # 乙醇 → 二甲醚(净零改写)⇒ full + 旗标
NOVEL_BAD_SMILES = "not_a_smiles"      # product_unparseable
NOVEL_UNSUPPORTED = "CC(=O)O.O"        # compile_unsupported


# ---------------------------------------------------------------- 夹具助手

def _profile(max_real: int = 4, rounds: int = 3, *,
             max_alt: int = 12, max_actions: int = 48) -> dict:
    return {
        "search_limits": {
            **S5B_DEFAULT_PROFILE_POLICY["search_limits"],
            "max_alternative_hypotheses_per_parent": int(max_alt),
            "max_total_search_actions": int(max_actions),
            "max_real_model_requests": int(max_real),
        },
        "format_feedback_policy": {
            "max_format_feedback_rounds": int(rounds),
        },
    }


def _novel(product: str, hypothesis_id: str = "novel-1",
           coproducts: list[str] | None = None) -> dict:
    spec: dict = {"product_smiles": product}
    if coproducts is not None:
        spec["coproducts"] = list(coproducts)
    return {
        "hypothesis_id": hypothesis_id,
        "proposal_context": {"reference_hypothesis_ids": [],
                             "output_origin": "novel_outside_pool"},
        "reaction_spec": spec,
    }


def _response(proposals: list[dict], rank: list[str] | None = None) -> str:
    return json.dumps({
        "proposals": proposals,
        "rank_hypotheses": rank or [p["hypothesis_id"] for p in proposals]},
        ensure_ascii=False)


def _pool_hypothesis_id(run_id: str) -> str:
    """池条目在 decide 里的稳定 hypothesis_id(与驱动同源口径)。"""
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        SUBSTRATE_SMILES, "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(POOL_SPEC), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(POOL_SPEC.get("transformation_ref") or ""))
    return prepared["hypothesis"].hypothesis_id


class _CountingStub(ScriptedRealModelAdapter):
    """记录 _complete 调用次数的 scripted 桩(与真实适配器同一调用序)。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.complete_calls = 0

    def _complete(self, *, system_prompt, user_payload, idempotency_key):
        self.complete_calls += 1
        return super()._complete(system_prompt=system_prompt,
                                 user_payload=user_payload,
                                 idempotency_key=idempotency_key)


def _start(tmp_path: Path, run_id: str, model, *,
           novel_protocol: str = NOVEL_PROTOCOL_PRODUCT_FIRST,
           profile: dict | None = None,
           smiles: str = SUBSTRATE_SMILES,
           pool: dict | None = None,
           evidence_card_enabled: bool = True,
           evidence_card_version: str | None = "v1card",
           crash_after: str | None = None,
           provider_kind: str = "scripted",
           runs_subdir: str = "runs") -> dict:
    runs_root = tmp_path / runs_subdir
    plan = {"pools": (pool if pool is not None
                      else ({SUBSTRATE_SMILES: [dict(POOL_SPEC)]}
                            if smiles == SUBSTRATE_SMILES else {})),
            "model": {"provider_kind": provider_kind}}
    return start_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id=run_id,
        smiles=smiles, plan=plan, model=model,
        profile_policy=profile or _profile(),
        evidence_card_enabled=evidence_card_enabled,
        evidence_card_version=evidence_card_version,
        novel_protocol=novel_protocol, scripted=True,
        crash_after=crash_after)


def _db(runs_root: Path, run_id: str) -> sqlite3.Connection:
    return sqlite3.connect(str(runs_root / run_id / "pollutant.sqlite"))


def _model_notes(runs_root: Path, run_id: str) -> list[dict]:
    notes: list[dict] = []
    for path in sorted((runs_root / run_id / "results").glob(
            "*/expansion_outcome.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))["payload"]
        outcome = payload.get("outcome") or {}
        if str(outcome.get("kind")) == "scheduled":
            notes.append(dict((outcome.get("detail") or {}).get("model")
                              or {}))
    return notes


def _principal_products(runs_root: Path, run_id: str) -> list[str]:
    conn = _db(runs_root, run_id)
    try:
        states = {row[0]: json.loads(row[1]).get("smiles_isomeric")
                  for row in conn.execute("SELECT state_id, payload"
                                          " FROM states")}
        out: list[str] = []
        for (raw,) in conn.execute("SELECT payload FROM events"):
            participants = json.loads(raw).get("participants") or []
            for participant in participants:
                if participant.get("role") == "principal_product":
                    out.append(states.get(participant.get("state_ref"), ""))
        return out
    finally:
        conn.close()


def _all_event_components(runs_root: Path, run_id: str) -> list[str]:
    conn = _db(runs_root, run_id)
    try:
        states = {row[0]: json.loads(row[1]).get("smiles_isomeric")
                  for row in conn.execute("SELECT state_id, payload"
                                          " FROM states")}
        out: list[str] = []
        for (raw,) in conn.execute("SELECT payload FROM events"):
            for participant in json.loads(raw).get("participants") or []:
                if participant.get("side") == "product":
                    out.append(states.get(participant.get("state_ref"), ""))
        return out
    finally:
        conn.close()


def _principal_products_in_submission_order(
        runs_root: Path, run_id: str) -> list[str]:
    """事件按 (created_at, event_id) 提交序的 principal 产物序
    (提交序 = 调度 effective_rank 序;PC9 位次断言的事实源)。"""
    conn = _db(runs_root, run_id)
    try:
        states = {row[0]: json.loads(row[1]).get("smiles_isomeric")
                  for row in conn.execute("SELECT state_id, payload"
                                          " FROM states")}
        out: list[str] = []
        for (raw,) in conn.execute(
                "SELECT payload FROM events ORDER BY created_at, event_id"):
            for participant in json.loads(raw).get("participants") or []:
                if participant.get("role") == "principal_product":
                    out.append(states.get(participant.get("state_ref"), ""))
        return out
    finally:
        conn.close()


def _expand_payloads(runs_root: Path, run_id: str) -> dict[str, dict]:
    """expand 动作的冻结任务输入,按 **prepared hypothesis ID** 建表
    (model_rank / effective_rank / rank_basis / logical_proposal_id 的
    唯一事实源;同一 prepared ID 只应有一条)。"""
    conn = _db(runs_root, run_id)
    try:
        out: dict[str, dict] = {}
        for (raw,) in conn.execute("SELECT payload FROM search_actions"):
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if isinstance(payload, dict) and \
                    payload.get("prepared_hypothesis_id"):
                out[str(payload["prepared_hypothesis_id"])] = payload
        return out
    finally:
        conn.close()


def _request_rows(runs_root: Path, run_id: str) -> list[tuple]:
    conn = _db(runs_root, run_id)
    try:
        return conn.execute(
            "SELECT request_id, purpose, status FROM model_requests"
            " ORDER BY purpose, created_at").fetchall()
    finally:
        conn.close()


def _decide_action_id(runs_root: Path, run_id: str) -> str:
    conn = _db(runs_root, run_id)
    try:
        return str(conn.execute(
            "SELECT action_id FROM search_actions WHERE action_kind ="
            " 'decide' AND status = 'done'").fetchone()[0])
    finally:
        conn.close()


def _ledger(runs_root: Path, run_id: str) -> SearchLedger:
    from pathway_v43.pollutant.store import PollutantPathwayStore

    store = PollutantPathwayStore(runs_root / run_id / "pollutant.sqlite")
    return SearchLedger(store, None, run_id)


def _verification_error(failures: list[dict]) -> ModelProtocolError:
    return ModelProtocolError(
        "核验失败", {"kind": NOVEL_VERIFICATION_FAILED_KIND,
                    "failures": failures})


# ======================================================== PF1 正控

def test_pf1_product_first_positive_control(tmp_path) -> None:
    """产物优先正控:乙醇 → 乙酸(编译执行成功)⇒ full 级、事件提交、
    主产物 = 声明产物;无反馈轮。"""
    run_id = "pf1"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK)])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    out = _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    assert out["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    # 方案甲冻结参数进 B 臂 run 摘要(与代码常量逐项相等)
    assert out["novel_bucket_policy_version"] == NOVEL_BUCKET_POLICY_VERSION
    assert out["added_heavy_atoms_backstop"] == ADDED_HEAVY_ATOMS_BACKSTOP
    assert out["removed_heavy_atoms_backstop"] == \
        REMOVED_HEAVY_ATOMS_BACKSTOP
    assert out["max_added_fragments"] == MAX_ADDED_FRAGMENTS
    assert out["novel_bucket_table_sha256"] == NOVEL_BUCKET_TABLE_SHA256
    # R2 P1-5(2026-11-06):白名单改为受控整体候选 ⇒ 两表 SHA 更新
    # (``novel-product-first-bucket-2``;旧 -1 值不再适用,历史见交付书 §11.4/§11.13)
    assert out["novel_bucket_table_sha256_by_table"] == {
        "added_fragment_whitelist":
            "543517a239d26a2e12d0c36eb4f8e778312072b75f4a3c62538c8be889dda4b3",
        "leaving_group_whitelist":
            "e6922e857569fefbbabee802a6592f9fe14f0e2f73a6942eb8a4d891b322c047",
        "known_moiety_table":
            "fa7707bdbbe7be51d3bdc81455e85f2a7b66b6dd328824faa60420c2b73f0643",
    }
    assert "max_added_heavy_atoms_main" not in out
    assert out["format_feedback_policy_version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
    # 事件:主产物 = 声明产物
    assert "CC(=O)O" in _principal_products(runs_root, run_id)
    # note:full 级编译清单 + 0 反馈轮
    notes = _model_notes(runs_root, run_id)
    assert notes and notes[0]["verification_rounds"] == 0
    assert notes[0]["novel_bucket_policy_version"] == \
        NOVEL_BUCKET_POLICY_VERSION
    assert notes[0]["added_heavy_atoms_backstop"] == \
        ADDED_HEAVY_ATOMS_BACKSTOP
    compiled = notes[0]["novel_compiled"]
    assert len(compiled) == 1
    assert compiled[0]["verification_tier"] == VERIFICATION_TIER_FULL
    assert compiled[0]["bucket_kind"] == BUCKET_KIND_FULL
    assert compiled[0]["added_heavy_atoms"] == 1
    assert compiled[0]["removed_heavy_atoms"] == 0
    assert compiled[0]["added_fragment_count"] == 1
    assert compiled[0]["net_zero_rewrite"] is False
    assert compiled[0]["bucket_reasons"] == []
    assert compiled[0]["reaction_spec"]["product_smiles"] == NOVEL_OK
    assert compiled[0]["reaction_spec"]["transformation_ref"] == \
        "novel-product-first"
    assert notes[0]["declared_bucket"] == []
    # 身份:novel_protocol 进 profile 块 + v2_pf prompt 哈希进预测块
    identity = json.loads(
        (runs_root / run_id / "run_identity.json").read_text(
            encoding="utf-8"))
    assert identity["profile"]["novel_protocol"] == \
        NOVEL_PROTOCOL_PRODUCT_FIRST
    assert identity["profile"]["format_feedback_policy"]["version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
    assert identity["prediction"]["prompt_versions"]["proposals"] == \
        PROPOSALS_PROMPT_VERSION_V2_PF
    # B 臂系统提示词 = v2_pf(与证据卡无关)
    assert model.seen_system_prompts[0] == proposals_system_prompt("v2_pf")


# ======================================================== PF2 反馈轮

def test_pf2_feedback_round_then_success(tmp_path) -> None:
    """第 1 轮产物不可解析 ⇒ 登记 1 个反馈轮(kind=
    novel_verification_failed,failure_kind=product_unparseable);第 2 轮
    成功落事件;轮数计数 = 1;登记载荷可按同一失败集确定性重算。"""
    run_id = "pf2"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_OK)])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    rows = _request_rows(runs_root, run_id)
    assert [r[1] for r in rows].count("format_feedback") == 1
    assert model.complete_calls == 2
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["verification_rounds"] == 1
    assert len(notes[0]["novel_compiled"]) == 1
    assert "CC(=O)O" in _principal_products(runs_root, run_id)
    # 轮数事实源 + 反馈轮身份门可按同一失败集重算(确定性载荷)
    action_id = _decide_action_id(runs_root, run_id)
    ledger = _ledger(runs_root, run_id)
    assert format_feedback_rounds_used(ledger, action_id) == 1
    reused = latest_format_feedback_round(
        ledger, run_id=run_id, action_id=action_id, attempt_id="",
        provider_kind="scripted",
        error=_verification_error([{
            "hypothesis_id": "novel-1",
            "failure_kind": FAILURE_PRODUCT_UNPARSEABLE}]),
        response_excerpt=_response([_novel(NOVEL_BAD_SMILES)]),
        round_index=1)
    assert reused is not None and reused["purpose"] == "format_feedback"


# ======================================================== PF3 全失败

def test_pf3_all_rounds_fail_pool_still_scheduled(tmp_path) -> None:
    """3 轮全部核验失败 ⇒ novel 丢弃、池条目照常排期并落事件、无
    PPV1RunError;第 4 次反馈登记被拒(轮数上限)。"""
    run_id = "pf3"
    pool_id = _pool_hypothesis_id(run_id)
    failing = _response([{"hypothesis_id": pool_id},
                         _novel(NOVEL_UNSUPPORTED)])
    model = _CountingStub(
        strategy="responses", responses=[failing] * 4,
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    out = _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 4   # 1 首发 + 3 反馈(第 5 次不发)
    rows = _request_rows(runs_root, run_id)
    assert [r[1] for r in rows] == ["format_feedback"] * 3 + ["proposals"]
    # 池条目照常落事件(novel 丢弃,不连坐)
    assert _principal_products(runs_root, run_id) == ["CC=O"]
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"] == []
    assert notes[0]["declared_bucket"] == []
    assert notes[0]["verification_rounds"] == 3
    assert notes[0]["verification_rounds_exhausted"]["kind"] == \
        "format_feedback_budget_exhausted"
    assert notes[0]["verification_failures"] == [{
        "hypothesis_id": "novel-1",
        "failure_kind": "compile_unsupported"}]
    assert "CC(=O)O.O" not in _all_event_components(runs_root, run_id)


# ======================================================== PF4 声明桶

def test_pf4_declared_bucket_not_event(tmp_path) -> None:
    """方案甲:白名单 4 原子片段(磷酸化/硫酸化)⇒ full(新边界正控);
    非白名单片段(+4 C 链 / NOVEL_BIG)⇒ declared_unrecognized,不提交
    事件。原 NOVEL_BOUNDARY(+4 C)语义由 full 改 declared_unrecognized
    (冻结 §4.3 条件 4)。"""
    # 新边界正控:PO3 4 重原子、单片段、命中白名单 ⇒ full
    for product in (NOVEL_PO3, NOVEL_SO3):
        boundary = compile_novel_product_first(
            SUBSTRATE_SMILES, product, [], "novel-boundary")
        assert boundary["status"] == "compiled"
        assert boundary["added_heavy_atoms"] == 4
        assert boundary["added_fragment_count"] == 1
        assert boundary["bucket_kind"] == BUCKET_KIND_FULL
        assert boundary["verification_tier"] == VERIFICATION_TIER_FULL
        assert boundary["bucket_metrics"]["added_fragments"][0][
            "whitelist_match"] in {"PO3", "SO3"}
    # 非白名单 +4 C ⇒ declared_unrecognized(原 NOVEL_BOUNDARY 翻转)
    chain4 = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_C4_CHAIN, [], "novel-chain4")
    assert chain4["status"] == "compiled"
    assert chain4["added_heavy_atoms"] == 4
    assert chain4["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert chain4["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_fragment_not_whitelisted" in chain4["bucket_reasons"]
    # 集成:非白名单 6 原子加成 ⇒ 声明桶、不落事件
    run_id = "pf4"
    pool_id = _pool_hypothesis_id(run_id)
    model = _CountingStub(
        strategy="responses",
        responses=[_response([{"hypothesis_id": pool_id},
                              _novel(NOVEL_BIG)])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"] == []
    declared = notes[0]["declared_bucket"]
    assert len(declared) == 1
    assert declared[0]["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert declared[0]["bucket_kind"] == \
        BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert declared[0]["added_heavy_atoms"] == 6
    assert declared[0]["hypothesis_id"] == "novel-1"
    assert declared[0]["bucket_policy_version"] == \
        NOVEL_BUCKET_POLICY_VERSION
    # 不提交事件:唯一事件是池条目;声明产物组件不出现在事件里
    assert _principal_products(runs_root, run_id) == ["CC=O"]
    assert "O=C(O)CCCCCO" not in _all_event_components(runs_root, run_id)


# ======================================================== PF5 对冲

def test_pf5_hedge_and_product_set_mismatch(tmp_path) -> None:
    """共产物位塞 5 个无关分子 ⇒ 执行无法复现 ⇒ 不落事件;
    product_set_mismatch 反馈只带 executed_components(白名单)。"""
    hedge = compile_novel_product_first(
        SUBSTRATE_SMILES, "CC=O", ["C", "C", "C", "C", "C"], "novel-hedge")
    assert hedge["status"] == "failed"
    assert hedge["failure_kind"] in {"compile_unsupported",
                                     "product_set_mismatch",
                                     "no_structure_correspondence"}
    assert "executed_components" not in hedge["feedback"]
    # 对冲:声明了仅部分离去原子构成的共产物("C")⇒ 执行产出("CC")与声明组分集合不可复现
    mismatch = compile_novel_product_first(
        "CC(=O)OC(C)C", "CC(=O)O", ["C"], "novel-mismatch")
    assert mismatch["status"] == "failed"
    assert mismatch["failure_kind"] == FAILURE_PRODUCT_SET_MISMATCH
    assert mismatch["feedback"]["failure_kind"] == \
        FAILURE_PRODUCT_SET_MISMATCH
    assert mismatch["feedback"]["executed_components"], \
        "product_set_mismatch 必须携带程序执行出的组分"
    # P1-1:只声明主产物、未声明非白名单脱落块(-C3H7)⇒ 过编译门进方案甲声明桶
    undeclared_large = compile_novel_product_first(
        "CC(=O)OC(C)C", "CC(=O)O", [], "novel-undeclared-large")
    assert undeclared_large["status"] == "compiled"
    assert undeclared_large["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert undeclared_large["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    # 集成:该提案在 run 内不落事件(池条目照常);同一对冲响应重复
    # 至轮数用尽 ⇒ 以最后一次可解析响应为准,失败项如实落账
    run_id = "pf5"
    pool_id = _pool_hypothesis_id(run_id)
    hedge_response = _response(
        [{"hypothesis_id": pool_id},
         _novel("CC=O", coproducts=["C", "C", "C", "C", "C"])])
    model = _CountingStub(
        strategy="responses", responses=[hedge_response] * 4,
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"] == []
    assert notes[0]["verification_failures"], "对冲提案必须记核验失败"
    assert _principal_products(runs_root, run_id) == ["CC=O"]
    assert len(_all_event_components(runs_root, run_id)) == 1


# ======================================================== PF6 白名单

def test_pf6_feedback_whitelist_keys(tmp_path) -> None:
    """每轮反馈载荷键集合 ⊆ 预注册 §5 白名单;无池命中、无参考图字段。"""
    run_id = "pf6"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_OK)])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model)
    assert len(model.seen_user_payloads) == 2
    payload = json.loads(model.seen_user_payloads[1])
    feedback = payload["format_feedback"]
    assert set(feedback) == {"failures", "round", "rounds_left"}
    assert feedback["round"] == 1 and feedback["rounds_left"] == 2
    for failure in feedback["failures"]:
        assert set(failure) <= {"hypothesis_id", "failure_kind",
                                "executed_components"}
        if failure.get("failure_kind") != "product_set_mismatch":
            assert "executed_components" not in failure
    text = json.dumps(feedback, ensure_ascii=False)
    for forbidden in ("gold", "reference_graph", "pool_hypotheses",
                      "response_excerpt", "max_added_heavy_atoms",
                      "score", "hit"):
        assert forbidden not in text
    # 旧形状(A 臂格式反馈)仍带 response_excerpt/note —— B 臂分支已分离
    legacy = json.loads(build_proposals_user_payload(
        substrate_smiles=SUBSTRATE_SMILES, atom_id_map=ATOM_ID_MAP,
        pool_entries=[], feedback_error={"kind": "json_field_error",
                                         "response_excerpt": "x"}))
    assert set(legacy["format_feedback"]) == {
        "error_kind", "response_excerpt", "note"}
    # 渲染器的键集封闭(直接负控:不该出现的键被丢弃)
    rendered = render_verification_feedback({
        "failures": [{"hypothesis_id": "novel-9",
                      "failure_kind": "product_unparseable",
                      "executed_components": ["X"],
                      "gold_product": "SECRET"}],
        "round": 1, "rounds_left": 2, "threshold": 4})
    assert rendered == {"failures": [{"hypothesis_id": "novel-9",
                                      "failure_kind": "product_unparseable"}],
                        "round": 1, "rounds_left": 2}


# ======================================================== PF7 A 臂字节

def test_pf7_a_arm_bytes_unchanged(tmp_path) -> None:
    """A 臂(novel_protocol=atom_edit)请求载荷与系统提示词逐字节等价:
    基线哈希 = 改动前采集值;A 臂 run 仍取 v2 提示词(v1card)。"""
    assert hashlib.sha256(
        proposals_system_prompt("v2").encode("utf-8")).hexdigest() == \
        PF7_PROMPT_SHA256
    payload = build_proposals_user_payload(
        substrate_smiles=SUBSTRATE_SMILES, atom_id_map=ATOM_ID_MAP,
        pool_entries=POOL_ENTRIES)
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == \
        PF7_PAYLOAD_SHA256
    assert S5B_REAL_MODEL_VERSION == "s5b-real-model-1"
    assert PROPOSALS_PROMPT_VERSION_V2 == PF7_PROMPT_SHA256
    assert proposals_prompt_version("v2") == PF7_PROMPT_SHA256
    assert proposals_prompt_version("v2_pf") != PF7_PROMPT_SHA256
    # A 臂 run:提示词仍是 v2(不是 v2_pf),载荷无 format_feedback
    run_id = "pf7-a"
    model = _CountingStub(
        strategy="responses",
        responses=['{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    out = _start(tmp_path, run_id, model,
                 novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert model.seen_system_prompts[0] == proposals_system_prompt("v2")
    assert "format_feedback" not in model.seen_user_payloads[0]
    assert "novel_protocol" not in out
    # 方案甲身份字段只进 B/C 臂: A 臂 run 摘要 / note / profile 零新键
    for key in ("novel_bucket_policy_version", "added_heavy_atoms_backstop",
                "removed_heavy_atoms_backstop", "max_added_fragments",
                "novel_bucket_table_sha256",
                "novel_bucket_table_sha256_by_table"):
        assert key not in out, key
    identity = json.loads(
        (tmp_path / "runs" / run_id / "run_identity.json").read_text(
            encoding="utf-8"))
    assert "novel_protocol" not in identity["profile"]
    for key in ("novel_bucket_policy_version", "added_heavy_atoms_backstop",
                "removed_heavy_atoms_backstop", "max_added_fragments",
                "novel_bucket_table_sha256",
                "novel_bucket_table_sha256_by_table"):
        assert key not in identity["profile"], key
    a_notes = _model_notes(tmp_path / "runs", run_id)
    assert a_notes
    for key in ("novel_bucket_policy_version", "added_heavy_atoms_backstop",
                "removed_heavy_atoms_backstop", "max_added_fragments",
                "novel_bucket_table_sha256",
                "novel_bucket_table_sha256_by_table", "declared_bucket",
                "bucket_kind"):
        assert key not in a_notes[0], key
    assert identity["profile"]["format_feedback_policy"]["version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION


# ======================================================== PF8 崩溃恢复

def test_pf8_resume_reuses_feedback_round(tmp_path) -> None:
    """反馈轮登记后注入崩溃 ⇒ resume 复用同一轮(既有身份核验门),
    不另发请求、不分配新轮、不重算新键。"""
    run_id = "pf8"
    runs_root = tmp_path / "runs"
    first = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    with pytest.raises(SearchCrashInjection):
        _start(tmp_path, run_id, first, crash_after="after_feedback_registered")
    before = _request_rows(runs_root, run_id)
    assert [r[1] for r in before] == ["format_feedback", "proposals"]
    resumed = _CountingStub(
        strategy="responses", responses=[_response([_novel(NOVEL_OK)])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    out = resume_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id=run_id,
        model=resumed, evidence_card_enabled=True,
        evidence_card_version="v1card",
        novel_protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    after = _request_rows(runs_root, run_id)
    assert [(r[0], r[1]) for r in after] == \
        [(r[0], r[1]) for r in before], \
        "resume 不得新增/重配反馈轮(同轮复用同一 request_id)"
    assert [r[2] for r in after if r[1] == "format_feedback"] == \
        ["responded"]
    assert resumed.complete_calls == 1      # 只发未消费的那一轮
    assert first.complete_calls == 1        # 崩溃前只发过首发
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["verification_rounds"] == 1
    assert len(notes[0]["novel_compiled"]) == 1
    assert out["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST


# ======================================================== PF9 预算

def test_pf9_fifth_request_refused_at_registration(tmp_path) -> None:
    """第 5 次真实请求在登记处被拒(拒绝先于网络):1 首发 + 3 反馈 =
    4 行,第 4 次反馈登记抛 format_feedback_budget_exhausted。"""
    run_id = "pf9"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)])] * 5,
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    out = _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 4
    rows = _request_rows(runs_root, run_id)
    assert len(rows) == 4
    action_id = _decide_action_id(runs_root, run_id)
    ledger = _ledger(runs_root, run_id)
    with pytest.raises(SearchBudgetExhausted) as excinfo:
        register_format_feedback_round(
            ledger, run_id=run_id, action_id=action_id, attempt_id="",
            error=_verification_error([{
                "hypothesis_id": "novel-1",
                "failure_kind": FAILURE_PRODUCT_UNPARSEABLE}]),
            response_excerpt="{}", provider_kind="real")
    assert excinfo.value.detail["kind"] == \
        "format_feedback_budget_exhausted"
    assert len(_request_rows(runs_root, run_id)) == 4   # 拒绝零写入


# ======================================================== PF10 开关

def _scripted_batch(tmp_path: Path, tag: str) -> Path:
    questions = tmp_path / f"q-{tag}.jsonl"
    questions.write_text(json.dumps(
        {"qid": "SYNTH-EXP1-1", "substrate_smiles": SUBSTRATE_SMILES,
         "products_smiles": ["CC=O"],
         "raw_reaction": "CCO>>CC=O"}) + "\n", encoding="utf-8")
    batch_root = tmp_path / f"batch-{tag}"
    build_question_batch(
        questions, batch_root, batch_tag=f"exp1-{tag}",
        pool_provider=lambda s: [dict(POOL_SPEC)],
        provider_kind="scripted", synthetic_review=True)
    return batch_root


def test_pf10_novel_protocol_fail_closed(tmp_path, monkeypatch) -> None:
    """orchestration.json 的 novel_protocol:坏值 ⇒ 结构化拒;缺键 ⇒
    atom_edit;旧批不得被静默升级成 B 臂;worker 侧换臂拒;B 臂预算
    上限 fail-closed。"""
    assert normalize_novel_protocol(None) == NOVEL_PROTOCOL_ATOM_EDIT
    assert normalize_novel_protocol("product_first_feedback") == \
        NOVEL_PROTOCOL_PRODUCT_FIRST
    with pytest.raises(S5bOrchestratorError) as excinfo:
        normalize_novel_protocol("product_first")
    assert excinfo.value.detail["kind"] == "s5b_novel_protocol_invalid"
    # 装载器:缺席/缺键 ⇒ atom_edit;坏值 ⇒ 拒
    empty = tmp_path / "empty-batch"
    empty.mkdir()
    assert load_novel_protocol(empty) == NOVEL_PROTOCOL_ATOM_EDIT
    missing = tmp_path / "missing-key"
    missing.mkdir()
    (missing / "orchestration.json").write_text(
        json.dumps({"orchestrator_version": "s5b-orchestrator-3"}),
        encoding="utf-8")
    assert load_novel_protocol(missing) == NOVEL_PROTOCOL_ATOM_EDIT
    bad = tmp_path / "bad-value"
    bad.mkdir()
    (bad / "orchestration.json").write_text(
        json.dumps({"novel_protocol": "product_first"}), encoding="utf-8")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        load_novel_protocol(bad)
    assert excinfo.value.detail["kind"] == "s5b_novel_protocol_invalid"
    # B 臂预算上限 fail-closed(> 4 请求 / > 3 轮)
    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_product_first_budget(
            NOVEL_PROTOCOL_PRODUCT_FIRST,
            _profile(max_real=5, rounds=3))
    assert excinfo.value.detail["kind"] == \
        "s5b_product_first_budget_invalid"
    with pytest.raises(S5bOrchestratorError):
        validate_product_first_budget(
            NOVEL_PROTOCOL_PRODUCT_FIRST, _profile(max_real=4, rounds=4))
    validate_product_first_budget(
        NOVEL_PROTOCOL_PRODUCT_FIRST, _profile(max_real=4, rounds=3))
    # 双版反馈策略块:严格相等(两版各自可过,错配拒)
    v1_block = {"version": FORMAT_FEEDBACK_POLICY_VERSION,
                "max_format_feedback_rounds": 0}
    v2_block = {"version": FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST,
                "max_format_feedback_rounds": 3}
    assert validate_frozen_format_feedback_policy(v1_block)["version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION
    assert validate_frozen_format_feedback_policy(
        v2_block, expected_version=
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST)["version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
    for block, expected in ((v2_block, FORMAT_FEEDBACK_POLICY_VERSION),
                            (v1_block,
                             FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST)):
        with pytest.raises(ValueError):
            validate_frozen_format_feedback_policy(
                block, expected_version=expected)
    # 装配语义:省略 version ⇒ 按期望版本补齐(A 臂 v1);显式错版 ⇒ 拒
    assert validate_format_feedback_policy(
        {"max_format_feedback_rounds": 3},
        expected_version=FORMAT_FEEDBACK_POLICY_VERSION) == {
            "version": FORMAT_FEEDBACK_POLICY_VERSION,
            "max_format_feedback_rounds": 3}
    with pytest.raises(ValueError):
        validate_format_feedback_policy(
            {"version": FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST,
             "max_format_feedback_rounds": 3},
            expected_version=FORMAT_FEEDBACK_POLICY_VERSION)
    # profile 身份块:仅 B 臂写 novel_protocol 键(A 臂逐字节零新键)
    assert "novel_protocol" not in build_profile_identity_block()
    b_block = build_profile_identity_block(
        novel_protocol=NOVEL_PROTOCOL_PRODUCT_FIRST,
        format_feedback_policy={"max_format_feedback_rounds": 3})
    assert b_block["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    assert b_block["format_feedback_policy"]["version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
    # 批冻结:非法值先拒;B 批写键 + case 披露;A 批零新键
    stub_path = tmp_path / "stub.json"
    stub_path.write_text(json.dumps({"strategy": "responses",
                                     "responses": ["{\"proposals\": []}"]}),
                         encoding="utf-8")
    monkeypatch.setenv("S5B_MODEL_STUB_SCRIPT", str(stub_path))
    bad_root = _scripted_batch(tmp_path, "bad-protocol")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(bad_root, runs_root=tmp_path / "runs-bad", workers=1,
                      poll_s=0.05, gate_max_calls=50,
                      novel_protocol="product_first")
    assert excinfo.value.detail["kind"] == "s5b_novel_protocol_invalid"
    b_root = _scripted_batch(tmp_path, "b")
    report = run_s5b_batch(
        b_root, runs_root=tmp_path / "runs-b", workers=1, poll_s=0.05,
        gate_max_calls=50, evidence_card_enabled=True,
        novel_protocol=NOVEL_PROTOCOL_PRODUCT_FIRST,
        profile_policy=_profile())
    frozen = json.loads((b_root / "orchestration.json").read_text())
    assert frozen["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    assert report["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    case = json.loads(
        (b_root / "cases" / "SYNTH-EXP1-1.json").read_text())
    assert case["status"] == "completed"
    assert case["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    # B 批换回 A 臂发车 ⇒ 冲突拒(冻结副本是权威;A 臂传合法 1/0 预算以隔离测冲突门)
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(b_root, runs_root=tmp_path / "runs-b", workers=1,
                      poll_s=0.05, gate_max_calls=50,
                      evidence_card_enabled=True,
                      profile_policy=_profile(max_real=1, rounds=0))
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"
    # A 批(旧形状)不得被升级成 B 臂
    a_root = _scripted_batch(tmp_path, "a")
    run_s5b_batch(a_root, runs_root=tmp_path / "runs-a", workers=1,
                  poll_s=0.05, gate_max_calls=50,
                  evidence_card_enabled=True,
                  profile_policy=_profile(max_real=1, rounds=0))
    a_frozen = json.loads((a_root / "orchestration.json").read_text())
    assert "novel_protocol" not in a_frozen
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(a_root, runs_root=tmp_path / "runs-a", workers=1,
                      poll_s=0.05, gate_max_calls=50,
                      evidence_card_enabled=True,
                      novel_protocol=NOVEL_PROTOCOL_PRODUCT_FIRST,
                      profile_policy=_profile())
    assert excinfo.value.detail["kind"] == "s5b_orchestration_conflict"
    # case 接纳面:A 臂 case 出现 novel_protocol 键 ⇒ 跨臂污染拒
    verdict = validate_case(
        {**case, "novel_protocol": NOVEL_PROTOCOL_PRODUCT_FIRST},
        "SYNTH-EXP1-1", expected_novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert not verdict["ok"]
    assert "novel_protocol_unexpected" in verdict["reasons"]
    # worker 侧换臂拒(可信批上下文显式传 B,冻结副本无键)
    from pathway_v43.pollutant.s5b_worker import worker_main

    (a_root / "profile_policy.json").write_text(
        json.dumps(S5B_DEFAULT_PROFILE_POLICY), encoding="utf-8")
    (a_root / "orchestration.json").write_text(json.dumps(
        {"orchestrator_version": "s5b-orchestrator-3",
         "evidence_card_enabled": True}), encoding="utf-8")
    rc = worker_main(["--batch-root", str(a_root),
                      "--runs-root", str(tmp_path / "runs-worker"),
                      "--qid", "SYNTH-EXP1-1",
                      "--novel-protocol",
                      NOVEL_PROTOCOL_PRODUCT_FIRST])
    assert rc == 5
    worker_case = json.loads(
        (a_root / "cases" / "SYNTH-EXP1-1.json").read_text())
    assert worker_case["failure_kind"] == "novel_protocol_mismatch"
    assert worker_case["detail"]["kind"] == "novel_protocol_mismatch"


# ======================================================== PF11 重指派

def test_pf11_principal_reassignment(tmp_path) -> None:
    """断裂型反应:LLM 声明的主产物不是编译器中心组分 ⇒ 主产物按声明
    重指派(全组分多重集不变);声明产物不在执行组分 ⇒ 不重指派并
    记录原因。"""
    # 单位判定:命中其余组分 ⇒ 重指派;不在执行组分 ⇒ 不重指派
    assert _reassign_principal_components(
        ["CC(=O)O", "CCO"], "CCO") == (True, "", "CCO")
    assert _reassign_principal_components(
        ["CC(=O)O", "CCO"], "CC(=O)O") == (False, "", "CC(=O)O")
    not_in = _reassign_principal_components(
        ["CC(=O)O", "CCO"], "CCC")
    assert not_in[0] is False
    assert not_in[1] == "declared_product_not_in_executed_components"
    multi = _reassign_principal_components(
        ["CC(=O)O", "CCO"], "CCO.CC")
    assert multi[0] is False
    assert multi[1] == "declared_product_multi_component"
    # 集成:乙酸乙酯断裂 ⇒ 编译器中心组分 = 乙酸;声明主产物 = 乙醇
    emitted = compile_novel_product_first(
        "CCOC(=O)C", "CCO", ["CC(=O)O"], "novel-cleavage")
    assert emitted["status"] == "compiled"
    assert emitted["principal_reassigned"] is True
    assert emitted["spec"]["product_smiles"] == "CCO"
    assert emitted["spec"]["coproducts"] == ["CC(=O)O"]
    assert emitted["spec"]["expectation"]["target_smiles"] == "CC(=O)O.CCO"
    run_id = "pf11"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel("CCO",
                                    coproducts=["CC(=O)O"])])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model, smiles="CCOC(=O)C", pool={})
    runs_root = tmp_path / "runs"
    assert _principal_products(runs_root, run_id) == ["CCO"]
    assert sorted(_all_event_components(runs_root, run_id)) == \
        sorted(["CC(=O)O", "CCO"])
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"][0]["principal_reassigned"] is True


# ======================================================== 方案甲七条件(2026-11-06)

def _synthetic_metrics(*, added_fragments=None, removed_fragments=None,
                       added_heavy_atoms=None, removed_heavy_atoms=None,
                       product_elements=None) -> dict:
    """合成度量(只喂分桶判定函数;不伪造编译结果)。"""
    added = list(added_fragments or [])
    removed = list(removed_fragments or [])
    return {
        "available": True,
        "mapping_source": "synthetic_unit_test",
        "added_heavy_atoms": int(
            sum(f["atom_count"] for f in added)
            if added_heavy_atoms is None else added_heavy_atoms),
        "removed_heavy_atoms": int(
            sum(f["atom_count"] for f in removed)
            if removed_heavy_atoms is None else removed_heavy_atoms),
        "added_fragment_count": len(added),
        "added_fragments": added,
        "removed_fragments": removed,
        "product_elements": list(product_elements or ["C", "O"]),
        "declared_coproduct_elements": {},
        "net_zero_rewrite": False,
    }


def _added_fragment(elements: dict, *, whitelist: str = "",
                    known: str = "", anchors=None) -> dict:
    return {
        "atom_count": int(sum(elements.values())),
        "elements": dict(elements),
        "h_counts": [],
        "internal_bonds": [],
        "anchors": list(anchors if anchors is not None else [{
            "fragment_element": "C", "skeleton_element": "C",
            "order": "single"}]),
        "whitelist_match": whitelist,
        "known_moiety": known,
    }


def _removed_fragment(elements: dict, *, whitelist: str = "",
                      known: str = "", accounted: bool = False) -> dict:
    return {
        "atom_count": int(sum(elements.values())),
        "elements": dict(elements),
        "h_counts": [],
        "internal_bonds": [],
        "anchors": [],
        "whitelist_match": whitelist,
        "known_moiety": known,
        "accounted": accounted,
    }


def test_pf12_condition1_added_backstop() -> None:
    """条件 1:新增重原子 > 8 ⇒ 声明桶(兜底护栏;同时因 C10 链不命中
    白名单进 declared_unrecognized)。"""
    out = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_C10_CHAIN, [], "c1")
    assert out["status"] == "compiled"
    assert out["added_heavy_atoms"] == 10
    assert out["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert out["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_heavy_atoms_backstop_exceeded" in out["bucket_reasons"]
    # +9 原子(恰超 1)⇒ 同一兜底拒因
    nine = compile_novel_product_first(
        SUBSTRATE_SMILES, "OCCCCCCCCCCC", [], "c1-nine")
    assert nine["status"] == "compiled"
    assert nine["added_heavy_atoms"] == 9
    assert nine["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_heavy_atoms_backstop_exceeded" in nine["bucket_reasons"]
    # 正控:PO3 4 原子 ≤ 8 且白名单 ⇒ full(PF4 已断言;此处对齐条件表)
    control = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_PO3, [], "c1-control")
    assert control["added_heavy_atoms"] <= ADDED_HEAVY_ATOMS_BACKSTOP
    assert control["bucket_kind"] == BUCKET_KIND_FULL


def test_pf13_condition2_removed_backstop() -> None:
    """条件 2:移除重原子 > 8 ⇒ 声明桶;= 8 且共产物声明接住 ⇒ full。"""
    over = compile_novel_product_first(
        "CC(=O)OCCCCCCCCCC", "CC(=O)O", ["CCCCCCCCCC"], "c2-over")
    assert over["status"] == "compiled"
    assert over["removed_heavy_atoms"] == 10
    assert over["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "removed_heavy_atoms_backstop_exceeded" in over["bucket_reasons"]
    # 正控:移除恰 8、整块在声明共产物中 ⇒ 条件 2/7 都过 ⇒ full
    boundary = compile_novel_product_first(
        "CC(=O)OCCCCCCCC", "CC(=O)O", ["CCCCCCCC"], "c2-boundary")
    assert boundary["status"] == "compiled"
    assert boundary["removed_heavy_atoms"] == \
        REMOVED_HEAVY_ATOMS_BACKSTOP
    assert boundary["bucket_kind"] == BUCKET_KIND_FULL
    assert boundary["bucket_metrics"]["removed_fragments"][0][
        "accounted"] is True


def test_pf14_condition3_fragment_count() -> None:
    """条件 3:新增片段 ≤ 2;3 个白名单单原子片段 ⇒ 声明桶;2 块 ⇒ full。"""
    three = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_3_FRAGS, [], "c3-three")
    assert three["status"] == "compiled"
    assert three["added_heavy_atoms"] == 3
    assert three["added_fragment_count"] == 3
    assert three["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert three["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "too_many_added_fragments" in three["bucket_reasons"]
    # 每块各自命中白名单(条件 4 不是失败原因)
    assert all(f["whitelist_match"]
               for f in three["bucket_metrics"]["added_fragments"])
    two = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_2_FRAGS, [], "c3-two")
    assert two["status"] == "compiled"
    assert two["added_fragment_count"] == MAX_ADDED_FRAGMENTS
    assert two["bucket_kind"] == BUCKET_KIND_FULL


def test_pf15_condition4_whitelist_graph_match() -> None:
    """条件 4:+4 C 非白名单片段 ⇒ declared_unrecognized;PO3/SO3(4 原子
    白名单)⇒ full。"""
    chain4 = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_C4_CHAIN, [], "c4-chain")
    assert chain4["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_fragment_not_whitelisted" in chain4["bucket_reasons"]
    for product, name in ((NOVEL_PO3, "PO3"), (NOVEL_SO3, "SO3")):
        good = compile_novel_product_first(
            SUBSTRATE_SMILES, product, [], f"c4-{name}")
        assert good["bucket_kind"] == BUCKET_KIND_FULL
        assert good["bucket_metrics"]["added_fragments"][0][
            "whitelist_match"] == name
    # NOVEL_BIG(C4 链 + 2 O,单块 C4O2)⇒ 非白名单片段仍拒
    big = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_BIG, [], "c4-big")
    assert big["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert big["added_heavy_atoms"] == 6
    assert big["added_fragment_count"] == 1
    assert big["bucket_metrics"]["added_fragments"][0][
        "whitelist_match"] == ""


def test_pf16_condition5_anchor() -> None:
    """条件 5:无锚孤立新增原子。编译链先行拒(center_empty:
    added_without_anchor)⇒ 该形态在真实链路不可达;分桶函数仍实现
    no-anchor / bad-anchor 拒因(合成度量单测),fail-closed 不静默 full。"""
    out = compile_novel_product_first("CCO", "CCO.C", [], "c5")
    assert out["status"] == "failed"
    assert "added_without_anchor" in out["diagnostics"]["reason"]
    no_anchor = classify_bucket_metrics(_synthetic_metrics(
        added_fragments=[_added_fragment({"C": 1}, whitelist="C",
                                         anchors=[])]))
    assert no_anchor["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_fragment_without_anchor" in no_anchor["reasons"]
    bad_anchor = classify_bucket_metrics(_synthetic_metrics(
        added_fragments=[_added_fragment(
            {"C": 1}, whitelist="C",
            anchors=[{"fragment_element": "C", "skeleton_element": "P",
                      "order": "single"}])]))
    assert bad_anchor["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "added_fragment_anchor_not_allowed" in bad_anchor["reasons"]


def test_pf17_condition6_product_element_domain() -> None:
    """条件 6:产物含域外元素(Si)⇒ declared_unrecognized。"""
    out = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_SI, [], "c6")
    assert out["status"] == "compiled"
    assert "Si" in out["bucket_metrics"]["product_elements"]
    assert out["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "product_element_out_of_domain:Si" in out["bucket_reasons"]


def test_pf18_condition7_removed_accounting() -> None:
    """条件 7:小离去基白名单 ⇒ full;大块移除但声明共产物接住 ⇒ full;
    未声明的移除在编译链被 product_set_mismatch 先拒(不可达证据);
    分桶函数对未认领移除 fail-closed(合成度量)。"""
    water = compile_novel_product_first(
        SUBSTRATE_SMILES, "CC", ["O"], "c7-water")
    assert water["status"] == "compiled"
    assert water["removed_heavy_atoms"] == 1
    assert water["bucket_kind"] == BUCKET_KIND_FULL
    assert water["bucket_metrics"]["removed_fragments"][0][
        "whitelist_match"] == "H2O"
    declared = compile_novel_product_first(
        "CCCCCCCCCC(=O)OCC", "CCCCCCCCCC(=O)O", ["CCO"], "c7-declared")
    assert declared["status"] == "compiled"
    assert declared["removed_heavy_atoms"] == 3
    assert declared["bucket_kind"] == BUCKET_KIND_FULL
    assert declared["bucket_metrics"]["removed_fragments"][0][
        "accounted"] is True
    # P1-1 + 条件 7:未声明非白名单脱落块(-CH3)过编译门进方案甲 ⇒ declared_unrecognized
    undeclared = compile_novel_product_first(
        SUBSTRATE_SMILES, "CO", [], "c7-undeclared")
    assert undeclared["status"] == "compiled"
    assert undeclared["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert undeclared["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "removed_part_not_accounted" in undeclared["bucket_reasons"]
    # 分桶函数负控(合成):移除 C2 非白名单、未认领 ⇒ 未识别
    unaccounted = classify_bucket_metrics(_synthetic_metrics(
        removed_fragments=[_removed_fragment({"C": 2}, accounted=False)],
        product_elements=["C", "O"]))
    assert unaccounted["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "removed_part_not_accounted" in unaccounted["reasons"]


def test_pf19_net_zero_rewrite_flag(tmp_path) -> None:
    """披露项:新增=移除=0 且有断/成键 ⇒ full + net_zero 旗标;普通
    羟化不误报。"""
    iso = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_NET_ZERO, [], "nz")
    assert iso["status"] == "compiled"
    assert iso["added_heavy_atoms"] == 0
    assert iso["removed_heavy_atoms"] == 0
    assert iso["net_zero_rewrite"] is True
    assert iso["bucket_kind"] == BUCKET_KIND_FULL
    hydroxy = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_OK, [], "nz-control")
    assert hydroxy["net_zero_rewrite"] is False
    # 集成级:异构化提案照常落事件,note 带旗标
    run_id = "pf19"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_NET_ZERO)])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model, pool={})
    runs_root = tmp_path / "runs"
    assert "COC" in _principal_products(runs_root, run_id)
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"][0]["net_zero_rewrite"] is True


def test_pf20_known_moiety_table_classification() -> None:
    """已知半分子表:CoA/GSH/糖基组成 ⇒ declared_recognized;对不上表的
    组成 ⇒ declared_unrecognized。表的冻结重原子数逐项核对。"""
    frozen = {
        "isopentenyl": 5, "malonyl": 6, "succinyl": 7,
        "pyrophosphate": 7, "ribosyl": 9, "glucosyl": 11,
        "lipoyl": 11, "glucuronyl": 12, "biotinyl": 15,
        "farnesyl": 15, "glutathione": 20,
        "phosphopantetheine": 22, "AMP": 23, "ADP-ribose": 35,
        "coenzyme_A": 48,
    }
    assert set(KNOWN_MOIETY_TABLE) == set(frozen)
    for name, count in frozen.items():
        assert KNOWN_MOIETY_TABLE[name]["heavy_atoms"] == count, name
        assert sum(KNOWN_MOIETY_TABLE[name]["elements"].values()) == count
    # 组成 → 命中(单测;表只作 declared_recognized 判定)
    assert _known_moiety_for({"C": 21, "N": 7, "O": 16, "P": 3,
                              "S": 1}) == "coenzyme_A"
    assert _known_moiety_for({"C": 10, "N": 3, "O": 6,
                              "S": 1}) == "glutathione"
    assert _known_moiety_for({"C": 6, "O": 5}) == "glucosyl"
    assert _known_moiety_for({"C": 4}) == ""
    # 分桶判定:已知半分子超限 ⇒ recognized;对不上表 ⇒ unrecognized
    coa = _added_fragment(
        {"C": 21, "N": 7, "O": 16, "P": 3, "S": 1}, known="coenzyme_A")
    recognized = classify_bucket_metrics(_synthetic_metrics(
        added_fragments=[coa], product_elements=["C", "N", "O", "P", "S"]))
    assert recognized["bucket_kind"] == BUCKET_KIND_DECLARED_RECOGNIZED
    assert "added_heavy_atoms_backstop_exceeded" in recognized["reasons"]
    garbage = classify_bucket_metrics(_synthetic_metrics(
        added_fragments=[_added_fragment({"C": 4})]))
    assert garbage["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED


def test_pf21_h_tolerance_protonation_and_a_arm_readout(tmp_path) -> None:
    """H 数容差 ±1 / 质子化归一:同一片段不同质子化写法同判定;A 臂
    离线同尺读数与 B/C 同一函数同一结果(不改变 A 臂在线行为)。"""
    # 端到端:羧酸根 vs 羧酸(formnorm Uncharge 归一)⇒ 同一 full
    anion = compile_novel_product_first(
        SUBSTRATE_SMILES, "CC(=O)[O-]", [], "h-anion")
    acid = compile_novel_product_first(
        SUBSTRATE_SMILES, "CC(=O)O", [], "h-acid")
    assert anion["status"] == acid["status"] == "compiled"
    assert anion["formnorm_status"] == "applied"
    assert anion["bucket_kind"] == acid["bucket_kind"] == BUCKET_KIND_FULL
    assert anion["added_heavy_atoms"] == acid["added_heavy_atoms"] == 1
    # 模板匹配的 H 容差(合成):O h2 / N h3 / C h4 仍在 ±1 内
    for elements, h, whitelist in (({"O": 1}, 2, "O"),
                                   ({"N": 1}, 3, "N"),
                                   ({"C": 1}, 4, "C")):
        fragment = _added_fragment(elements, whitelist=whitelist)
        fragment["h_counts"] = [h]
        result = classify_bucket_metrics(_synthetic_metrics(
            added_fragments=[fragment]))
        assert result["bucket_kind"] == BUCKET_KIND_FULL, elements
    # A 臂离线读数:同一编译链 render+edits,与 B/C 同函数同判
    from pathway_v43.pollutant.recorded_source import (
        compile_recorded_reaction,
    )

    for products, expected in ((["CCCCO"], BUCKET_KIND_DECLARED_UNRECOGNIZED),
                               (["CC(=O)O"], BUCKET_KIND_FULL),
                               (["CC", "O"], BUCKET_KIND_FULL),
                               (["COC"], BUCKET_KIND_FULL)):
        compiled = compile_recorded_reaction(
            substrate_smiles=SUBSTRATE_SMILES,
            donor_smiles=SUBSTRATE_SMILES, products=products,
            record_id="a-arm-readout")
        assert compiled["status"] == "compiled", products
        readout = compute_arm_a_bucket_readout(
            dict(compiled["spec"]), SUBSTRATE_SMILES)
        assert readout["bucket_kind"] == expected, products
        assert readout["policy_version"] == NOVEL_BUCKET_POLICY_VERSION
    assert readout["metrics"]["mapping_source"] == \
        "atom_tool.render+execute_edits"


# ================================== R2 回修(P1-4 / P1-5;PF22–PF25,2026-11-06)
#
# 依据 docs/reviews/codex/EXP1_CARM_CODEX_REVIEW_R2_2026-11-06.md §4/§7。
# 全部为合成分子、零金标、零题面、零真实模型。

def _patch_mapping_artifacts(monkeypatch, variant: str) -> None:
    """**故障注入(非自然缺件)**:真实 ``compile_recorded_reaction`` 正常
    返回后,把 ``formnorm.mapping_artifacts`` 删键(``drop``)或置空 dict
    (``empty``)。不声称当前编译器会自然缺件,只验证 B/C 的缺件门。"""
    from pathway_v43.pollutant import novel_product_first as module

    real = module.compile_recorded_reaction

    def wrapper(*args, **kwargs):
        compiled = real(*args, **kwargs)
        formnorm = compiled.get("formnorm")
        if isinstance(formnorm, dict):
            if variant == "drop":
                formnorm.pop("mapping_artifacts", None)
            elif variant == "empty":
                formnorm["mapping_artifacts"] = {}
            else:  # pragma: no cover —— 测试自身防线
                raise AssertionError(f"未知变体 {variant}")
        return compiled

    monkeypatch.setattr(module, "compile_recorded_reaction", wrapper)


def test_pf22_missing_mapping_artifacts_fail_closed(monkeypatch) -> None:
    """P1-4:B/C 缺编译映射 ≠ 走 A 专用重放。

    故障注入两种变体(键缺失 / 空 dict,均**非自然缺件**)⇒
    ``compile_novel_product_first`` 必须 declared_unrecognized +
    ``mapping_artifacts_missing``,度量不可用(-1,不伪造);同树正常羟化
    正控仍 full;``compute_arm_a_bucket_readout``(A 离线重放)仍可用,
    且只有 ``allow_replay=True`` 才放行重放。
    """
    # 正控(未注入):CCO → OCCO(+1 O)⇒ full
    control = compile_novel_product_first(
        SUBSTRATE_SMILES, "OCCO", [], "p1-4-control")
    assert control["status"] == "compiled"
    assert control["bucket_kind"] == BUCKET_KIND_FULL
    assert control["bucket_metrics"]["mapping_source"] == \
        "formnorm.mapping_artifacts"

    for variant in ("drop", "empty"):
        with monkeypatch.context() as patch:
            _patch_mapping_artifacts(patch, variant)
            out = compile_novel_product_first(
                SUBSTRATE_SMILES, "OCCO", [], f"p1-4-{variant}")
        assert out["status"] == "compiled", variant
        assert out["verification_tier"] == VERIFICATION_TIER_DECLARED
        assert out["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
        assert out["bucket_reasons"] == ["mapping_artifacts_missing"]
        assert out["bucket_metrics"]["available"] is False
        assert "mapping_source" not in out["bucket_metrics"]
        # 度量不可用时计数为 -1(不拿重放数冒充)
        assert out["added_heavy_atoms"] == -1
        assert out["removed_heavy_atoms"] == -1
        assert out["added_fragment_count"] == -1
        assert out["spec"]["novel_product_first"]["bucket_kind"] == \
            BUCKET_KIND_DECLARED_UNRECOGNIZED
        # 不因缺件而改编译产物本身(只关分桶)
        assert out["compiled_principal"] == control["compiled_principal"]

    # 同一 spec:默认(不授权重放)⇒ fail-closed;显式 allow_replay ⇒ 重放
    from pathway_v43.pollutant.recorded_source import (
        compile_recorded_reaction,
    )

    compiled = compile_recorded_reaction(
        substrate_smiles=SUBSTRATE_SMILES, donor_smiles=SUBSTRATE_SMILES,
        products=["CC(=O)O"], record_id="p1-4-api")
    assert compiled["status"] == "compiled"
    spec = dict(compiled["spec"])
    blocked = compute_novel_bucket(
        spec=spec, substrate_smiles=SUBSTRATE_SMILES,
        declared_product="CC(=O)O", mapping_artifacts=None)
    assert blocked["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert blocked["reasons"] == ["mapping_artifacts_missing"]
    assert blocked["fail_closed"] is True
    replayed = compute_novel_bucket(
        spec=spec, substrate_smiles=SUBSTRATE_SMILES,
        declared_product="CC(=O)O", mapping_artifacts=None,
        allow_replay=True)
    assert replayed["bucket_kind"] == BUCKET_KIND_FULL
    assert replayed["metrics"]["mapping_source"] == \
        "atom_tool.render+execute_edits"
    # A 臂离线读数走同一授权点(正控:重放仍可用)
    readout = compute_arm_a_bucket_readout(spec, SUBSTRATE_SMILES)
    assert readout["bucket_kind"] == BUCKET_KIND_FULL
    assert readout["metrics"]["mapping_source"] == \
        "atom_tool.render+execute_edits"
    # 非 dict 映射材料 ⇒ 明确 unparseable(不混淆成 missing)
    garbage = compute_novel_bucket(
        spec=spec, substrate_smiles=SUBSTRATE_SMILES,
        declared_product="CC(=O)O", mapping_artifacts="not-a-dict")
    assert garbage["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert garbage["reasons"] == ["mapping_artifacts_unparseable"]


def test_pf23_missing_mapping_artifacts_no_event(
        tmp_path, monkeypatch) -> None:
    """P1-4 事件层:同一故障注入(键缺失)下 B 臂 run 链不得把该 novel
    提交成事件;池条目照常落事件;note 里该提案落 ``declared_bucket``
    且 reason 为 ``mapping_artifacts_missing``。"""
    run_id = "pf23"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel("OCCO", "novel-1")])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    with monkeypatch.context() as patch:
        _patch_mapping_artifacts(patch, "drop")
        _start(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    products = _principal_products(runs_root, run_id)
    assert "OCCO" not in products          # novel 未提交
    assert "CC=O" in products              # 池条目照常
    notes = _model_notes(runs_root, run_id)
    assert notes and notes[0]["novel_compiled"] == []
    declared = notes[0]["declared_bucket"]
    assert [entry["hypothesis_id"] for entry in declared] == ["novel-1"]
    assert declared[0]["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert declared[0]["bucket_reasons"] == ["mapping_artifacts_missing"]
    assert notes[0]["network_request_count"] == 0


def test_pf24_whitelist_whole_graph_no_false_full(tmp_path) -> None:
    """P1-5:图白名单按**整图受控候选**判定(禁止逐边放宽)。

    公共编译链三条(R2 §4 原反例 + 羧化正控),再走事件层:
    - ``CCO → CCOC(O)O``(新增片段 C/O/O 全单键)⇒ declared_unrecognized;
    - ``CCO → CCON(O)O``(新增片段 N/O/O 全单键)⇒ declared_unrecognized;
    - ``CCO → CCOC(=O)O``(羧基 C(=O)–O)⇒ full;
    事件层只有羧化正控提交,两条反例不落事件。
    """
    for product, tag in (("CCOC(O)O", "co2-all-single"),
                         ("CCON(O)O", "no2-all-single")):
        out = compile_novel_product_first(
            SUBSTRATE_SMILES, product, [], f"p1-5-{tag}")
        assert out["status"] == "compiled", tag
        assert out["verification_tier"] == VERIFICATION_TIER_DECLARED, tag
        assert out["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED, tag
        assert "added_fragment_not_whitelisted" in out["bucket_reasons"], tag
        fragment = out["bucket_metrics"]["added_fragments"][0]
        assert fragment["whitelist_match"] == "", tag
        assert {bond["order"] for bond in fragment["internal_bonds"]} == \
            {"single"}, tag
    good = compile_novel_product_first(
        SUBSTRATE_SMILES, "CCOC(=O)O", [], "p1-5-carboxyl")
    assert good["bucket_kind"] == BUCKET_KIND_FULL
    fragment = good["bucket_metrics"]["added_fragments"][0]
    assert fragment["whitelist_match"] == "CO2"
    assert sorted(bond["order"] for bond in fragment["internal_bonds"]) == \
        ["double", "single"]
    # ---- 事件层(编译 → 桶 → 事件)----
    run_id = "pf24"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel("CCOC(O)O", "n1"),
                              _novel("CCON(O)O", "n2"),
                              _novel("CCOC(=O)O", "n3")])],
        call_account_path=tmp_path / "runs" / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model, pool={})
    runs_root = tmp_path / "runs"
    products = _principal_products(runs_root, run_id)
    assert "CCOC(=O)O" in products
    assert "CCOC(O)O" not in products
    assert "CCON(O)O" not in products
    notes = _model_notes(runs_root, run_id)
    assert [entry["hypothesis_id"] for entry in notes[0]["novel_compiled"]] \
        == ["n3"]
    assert {entry["hypothesis_id"]
            for entry in notes[0]["declared_bucket"]} == {"n1", "n2"}


def _whole_fragment(smiles: str, elements: set[str]) -> dict:
    """从真实 RDKit 分子里取指定元素的重原子构成片段图(matcher 级单测;
    不经过编译器 —— 不代表该形态在编译链可达)。"""
    from rdkit import Chem
    from pathway_v43.pollutant.novel_product_first import _fragment_graph

    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, smiles
    indices = [atom.GetIdx() for atom in mol.GetAtoms()
               if atom.GetSymbol() in elements]
    return _fragment_graph(mol, indices)


def _fragment_at(smiles: str, indices: list[int]) -> dict:
    """从真实分子的指定原子序取片段图(分子比片段大时用;原子序按
    SMILES 书写顺序,RDKit 解析确定)。"""
    from rdkit import Chem
    from pathway_v43.pollutant.novel_product_first import _fragment_graph

    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, smiles
    return _fragment_graph(mol, list(indices))


def test_pf25_whitelist_candidates_matcher_and_guard() -> None:
    """P1-5:受控候选表 + 机械护栏 + 受影响模板的近邻反例。

    编译链可达的近邻反例走公共链;不可编译/带电荷的形态用 matcher 级
    (真实 RDKit 分子取片段图)覆盖并**如实标注不可达**。
    """
    from pathway_v43.pollutant.novel_product_first import (
        ADDED_FRAGMENT_WHITELIST,
        LEAVING_GROUP_WHITELIST,
        _match_template,
        _whitelist_for_fragment,
    )

    added = list(ADDED_FRAGMENT_WHITELIST)
    leaving = list(LEAVING_GROUP_WHITELIST)
    # ---- 表结构:每行都是整图候选,禁止残留逐边 orders ----
    for rows in (added, leaving):
        for row in rows:
            assert row["bond_order_candidates"], row["name"]
            assert all("orders" not in bond for bond in row["bonds"])
            for bond in row["bonds"]:
                assert set(bond) == {"i", "j"}, row["name"]
    counts = {row["name"]: len(row["bond_order_candidates"]) for row in added}
    assert counts == {
        "O": 1, "N": 1, "C": 1, "S": 1, "Se": 1, "halogen": 1,
        "CO": 1, "CHO": 1, "OOH": 1, "CO2": 1, "C2H3O": 1, "CONH2": 1,
        "NO2": 2, "PO3": 1, "SO3": 1,
    }
    leaving_counts = {
        row["name"]: len(row["bond_order_candidates"]) for row in leaving}
    assert leaving_counts == {
        "H2O": 1, "NH3": 1, "H2S": 1, "HX": 1,
        "CO2_or_formate": 2, "acetate": 1,
    }
    # ---- 机械护栏:旧逐边写法会被 import 期校验拒 ----
    from pathway_v43.pollutant.novel_product_first import (
        _validate_whitelist_rows,
    )

    with pytest.raises(ValueError, match="逐边 orders"):
        _validate_whitelist_rows([{
            "name": "bad", "atoms": [{"elements": ["O"], "h": [0, 0]}],
            "bonds": [{"i": 0, "j": 1, "orders": [0, 1]}]}],
            label="unit")
    with pytest.raises(ValueError, match="缺整图候选"):
        _validate_whitelist_rows([{
            "name": "bad", "atoms": [{"elements": ["O"], "h": [0, 0]}],
            "bonds": []}], label="unit")
    with pytest.raises(ValueError, match="候选长度"):
        _validate_whitelist_rows([{
            "name": "bad", "atoms": [{"elements": ["O"], "h": [0, 0]}],
            "bonds": [{"i": 0, "j": 1}],
            "bond_order_candidates": [(0, 1)]}], label="unit")

    # ---- matcher 级:新增片段(整分子即片段) ----
    added_cases = (
        ("C(=O)O", {"C", "O"}, "CO2"),      # 羧基/羧酸 D,S
        ("C(O)O", {"C", "O"}, ""),          # 全单键 C(O)O 不得匹配
        ("[N+](=O)[O-]", {"N", "O"}, "NO2"),  # 电荷分离式硝基
        ("CN(=O)=O", {"N", "O"}, "NO2"),    # 五价硝基 D,D
        ("N(O)O", {"N", "O"}, ""),          # 全单键 N(O)O 不得匹配
        ("OP(=O)O", {"P", "O"}, "PO3"),     # P(=O)(O)(O)
        ("OP(O)O", {"P", "O"}, ""),         # 亚磷酸型全单键
        ("OS(=O)=O", {"S", "O"}, "SO3"),    # S(=O)2(O)
        ("OS(O)O", {"S", "O"}, ""),         # 亚硫酸型全单键
    )
    for smiles, elements, expected in added_cases:
        matched = _whitelist_for_fragment(
            _whole_fragment(smiles, elements), added)
        assert matched == expected, (smiles, matched, expected)
    # 乙酰模板的近邻对(分子比片段大:取羰基 C + 甲基 C + O 三原子图;
    # ``CCOC(C)=O`` / ``CCOC(C)O`` 的原子序 C0-C1-O2-C3(-C4)=O5)
    assert _whitelist_for_fragment(
        _fragment_at("CCOC(C)=O", [3, 4, 5]), added) == "C2H3O"
    assert _whitelist_for_fragment(
        _fragment_at("CCOC(C)O", [3, 4, 5]), added) == ""
    # ---- matcher 级:离去基 ----
    leaving_cases = (
        ("C(=O)O", {"C", "O"}, "CO2_or_formate"),   # 甲酸 D,S
        ("O=C=O", {"C", "O"}, "CO2_or_formate"),    # CO2 D,D
        ("C(O)O", {"C", "O"}, ""),                  # 全单键不匹配
        ("CC(=O)O", {"C", "O"}, "acetate"),         # 乙酸/乙酸根
        ("CC(O)O", {"C", "O"}, ""),                 # 偕二醇型不匹配
    )
    for smiles, elements, expected in leaving_cases:
        matched = _whitelist_for_fragment(
            _whole_fragment(smiles, elements), leaving)
        assert matched == expected, (smiles, matched, expected)
    # CO2 模板只接受"恰一根 C=O":两根全双键的 O=C=O 不作为新增片段
    co2_row = next(row for row in added if row["name"] == "CO2")
    assert _match_template(
        _whole_fragment("O=C=O", {"C", "O"}), co2_row) is None

    # ---- 公共编译链可达的近邻反例(同规则全表检查) ----
    # PO3:全单键 P(O)(O)O(亚磷酸型)此前被判 full,现在非白名单
    po3_bad = compile_novel_product_first(
        SUBSTRATE_SMILES, "CCOP(O)(O)O", [], "p1-5-po3-single")
    assert po3_bad["status"] == "compiled"
    assert po3_bad["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert po3_bad["bucket_metrics"]["added_fragments"][0][
        "whitelist_match"] == ""
    # SO3:全单键 S(O)(O)O(亚硫酸型)同理
    so3_bad = compile_novel_product_first(
        SUBSTRATE_SMILES, "CCOS(O)(O)O", [], "p1-5-so3-single")
    assert so3_bad["status"] == "compiled"
    assert so3_bad["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert so3_bad["bucket_metrics"]["added_fragments"][0][
        "whitelist_match"] == ""
    # 正常 PO3/SO3 正控仍 full
    for product, name in (("CCOP(=O)(O)O", "PO3"),
                          ("CCOS(=O)(=O)O", "SO3")):
        good = compile_novel_product_first(
            SUBSTRATE_SMILES, product, [], f"p1-5-{name}")
        assert good["bucket_kind"] == BUCKET_KIND_FULL
        assert good["bucket_metrics"]["added_fragments"][0][
            "whitelist_match"] == name

    # ---- 离去基侧(公共链):全单键 C–C(O)O / C(O)O 不再冒充乙酸/甲酸 ----
    gem_diacyl = compile_novel_product_first(
        "CC(O)(O)CC", "CC", ["CC(O)O"], "p1-5-leave-acetate")
    assert gem_diacyl["status"] == "compiled"
    removed = gem_diacyl["bucket_metrics"]["removed_fragments"][0]
    assert removed["whitelist_match"] == ""       # 旧实现误标 acetate
    assert removed["accounted"] is True           # 由声明共产物整组对账接住
    assert gem_diacyl["bucket_kind"] == BUCKET_KIND_FULL
    gem_diol = compile_novel_product_first(
        "CC(O)O", "C", ["C(O)O"], "p1-5-leave-formate")
    assert gem_diol["status"] == "compiled"
    assert gem_diol["bucket_metrics"]["removed_fragments"][0][
        "whitelist_match"] == ""                  # 旧实现误标 CO2_or_formate
    # 离去基正控:脱羧放出的 CO2(C=O + C–O 归一形态)与 C–C 断裂离去的
    # 乙酸(CCC(=O)O → C + CC(=O)O)均命中对应白名单
    decarboxyl = compile_novel_product_first(
        "CC(=O)O", "CC", ["O=C=O"], "p1-5-decarboxyl")
    assert decarboxyl["status"] == "compiled"
    assert decarboxyl["bucket_metrics"]["removed_fragments"][0][
        "whitelist_match"] == "CO2_or_formate"
    assert decarboxyl["bucket_kind"] == BUCKET_KIND_FULL
    leave_acetate_pos = compile_novel_product_first(
        "CCC(=O)O", "C", ["CC(=O)O"], "p1-5-leave-acetate-pos")
    assert leave_acetate_pos["status"] == "compiled"
    assert leave_acetate_pos["bucket_metrics"]["removed_fragments"][0][
        "whitelist_match"] == "acetate"
    assert leave_acetate_pos["bucket_kind"] == BUCKET_KIND_FULL

    # ---- 不可达披露:新增侧 NO2 的带电正控被编译器先拒 ----
    nitro = compile_novel_product_first(
        SUBSTRATE_SMILES, "CCO[N+](=O)[O-]", [], "p1-5-nitro-charged")
    assert nitro["status"] == "failed"
    assert nitro["diagnostics"]["reason"] == "new_atom_charge_unsupported"
    # ⇒ 新增侧 NO2 的编译链正控不可达;上面的 matcher 级用例是该模板
    #   唯一的可达证明,不冒充公共链已通过。


# ============================================== 解析协议分支(单位级)

def test_parse_product_first_protocol_branch() -> None:
    """product_first 解析分支:novel 只声明产物;缺 product_smiles ⇒
    json_field 可反馈错误(协议版本 -3);atom_edit 分支判别语义不变。"""
    parsed = parse_model_proposals(
        _response([_novel("CC=O")]),
        allowed_hypothesis_ids=[], protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    assert parsed["protocol_version"] == "ppv1-model-proposals-3"
    assert parsed["proposals"][0]["reaction_spec"] == {
        "product_smiles": "CC=O", "coproducts": []}
    # 模型多写的原子编辑键一律忽略(产物优先语义不消费 edits)
    extra = _novel("CC=O")
    extra["reaction_spec"]["edits"] = [{"op": "break_bond", "atom1": "x",
                                        "atom2": "y"}]
    parsed_extra = parse_model_proposals(
        _response([extra]), allowed_hypothesis_ids=[],
        protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    assert set(parsed_extra["proposals"][0]["reaction_spec"]) == {
        "product_smiles", "coproducts"}
    missing = _novel("")
    missing["reaction_spec"] = {"coproducts": ["O"]}
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(
            _response([missing]), allowed_hypothesis_ids=[],
            protocol=NOVEL_PROTOCOL_PRODUCT_FIRST)
    assert excinfo.value.detail["kind"] == "json_field_error"
    assert excinfo.value.detail["model_protocol_version"] == \
        "ppv1-model-proposals-3"
    assert excinfo.value.detail["kind"] in FEEDBACK_ELIGIBLE
    # atom_edit 分支:novel 缺 reaction_spec 仍按旧判据拒(协议版本 -2);
    # 只带 product_smiles 的 spec 在解析层照旧通过(深层校验属执行侧,
    # 本次不得收紧 A 臂判据)
    atom_edit_ok = parse_model_proposals(
        _response([_novel("CC=O")]), allowed_hypothesis_ids=[],
        protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert atom_edit_ok["protocol_version"] == "ppv1-model-proposals-2"
    no_spec = _novel("CC=O")
    no_spec.pop("reaction_spec")
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(
            _response([no_spec]), allowed_hypothesis_ids=[],
            protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert excinfo.value.detail["model_protocol_version"] == \
        "ppv1-model-proposals-2"
    # 未知协议值 fail-closed
    with pytest.raises(ModelProtocolError):
        parse_model_proposals('{"proposals": []}',
                              allowed_hypothesis_ids=[], protocol="pf")
    # 反馈策略版本按协议映射(单一来源)
    assert format_feedback_policy_version_for(NOVEL_PROTOCOL_ATOM_EDIT) == \
        FORMAT_FEEDBACK_POLICY_VERSION
    assert format_feedback_policy_version_for(
        NOVEL_PROTOCOL_PRODUCT_FIRST) == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST

# ============================================== EXP1 C 臂(PC1–PC8)
#
# C 臂 = product_first_feedback_blind_first:第①阶段盲写(载荷零池
# 条目/零池证据,v2_pf_blind),第②阶段合并(现行池条目 + 已核验盲写
# 提案,origin=blind_first,v2_pf);反馈轮两阶段共用同一 action 的持久
# 计数(上限 3);预算 5 请求(盲写 1 + 合并 1 + 反馈 3)。
# PC8(CC 2026-11-06 追加):模型自写池侧声明键 ⇒ 静默忽略 + 记录键名,
# 事件参与物只来自编译器生成的 spec。

def _blind_profile(max_real: int = 5, rounds: int = 3, *,
                   max_alt: int = 12, max_actions: int = 48) -> dict:
    return _profile(max_real=max_real, rounds=rounds,
                    max_alt=max_alt, max_actions=max_actions)


def _start_blind(tmp_path: Path, run_id: str, model, *,
                 max_real: int = 5, rounds: int = 3,
                 **kwargs) -> dict:
    return _start(tmp_path, run_id, model,
                  novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST,
                  profile=_blind_profile(max_real=max_real, rounds=rounds),
                  **kwargs)


def _blind_prepared_id(run_id: str, product: str = NOVEL_OK,
                       hypothesis_id: str = "novel-1") -> str:
    """盲写 full 级条目在合并载荷/事件里的 prepared hypothesis ID
    （与驱动同源口径:compile_novel_product_first + prepare_hypothesis
    同一构建源;source_refs 不参与 hypothesis_id 派生,仍按驱动同参数
    重算以防将来漂移）。"""
    compiled = compile_novel_product_first(
        SUBSTRATE_SMILES, product, [], hypothesis_id)
    assert compiled["status"] == "compiled"
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        SUBSTRATE_SMILES, "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(compiled["spec"]), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(compiled["spec"].get("transformation_ref")
                               or ""),
        source_refs=[{"record":
                      "novel-model-proposal:product_first:blind_first"}])
    return prepared["hypothesis"].hypothesis_id


def _merge_novel_prepared_id(run_id: str, product: str,
                             hypothesis_id: str = "novel-1") -> str:
    """合并阶段新 novel 的 prepared hypothesis ID(与驱动同源口径:
    _run_decide 以 source_refs=[novel-model-proposal:product_first:full]
    prepare;hypothesis_id 不因 source_refs 漂移,仍按同参数重算)。"""
    compiled = compile_novel_product_first(
        SUBSTRATE_SMILES, product, [], hypothesis_id)
    assert compiled["status"] == "compiled"
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        SUBSTRATE_SMILES, "raw_input",
        [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(compiled["spec"]), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(compiled["spec"].get("transformation_ref")
                               or ""),
        source_refs=[{"record": "novel-model-proposal:product_first:full"}])
    return prepared["hypothesis"].hypothesis_id


def _decide_context_ref(runs_root: Path, run_id: str) -> str:
    conn = _db(runs_root, run_id)
    try:
        return str(conn.execute(
            "SELECT context_ref FROM search_actions WHERE action_kind ="
            " 'decide' ORDER BY created_at LIMIT 1").fetchone()[0])
    finally:
        conn.close()


# ======================================================== PC1 盲写载荷

def test_pc1_blind_payload_has_zero_pool_content(tmp_path) -> None:
    """盲写请求(seen_user_payloads[0])机器断言:pool_hypotheses == [];
    池条目 ID 与池产物 SMILES 不出现在载荷文本任何位置;底物/执行图/
    底物档案卡在场;系统提示词 = v2_pf_blind(合并 = v2_pf)。"""
    run_id = "pc1"
    pool_id = _pool_hypothesis_id(run_id)
    blind_id = _blind_prepared_id(run_id)
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK)]),
                   _response([{"hypothesis_id": pool_id},
                              {"hypothesis_id": blind_id}])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model)
    assert out["novel_protocol"] == NOVEL_PROTOCOL_BLIND_FIRST
    assert out["format_feedback_policy_version"] == \
        FORMAT_FEEDBACK_POLICY_VERSION_PRODUCT_FIRST
    blind_text = model.seen_user_payloads[0]
    blind_payload = json.loads(blind_text)
    assert blind_payload["pool_hypotheses"] == []
    assert pool_id not in blind_text
    assert "CC=O" not in blind_text          # 池产物 SMILES
    assert blind_payload["substrate_smiles"] == SUBSTRATE_SMILES
    assert blind_payload["execution_graph"]
    assert blind_payload["substrate_evidence"]
    assert model.seen_system_prompts[0] == \
        proposals_system_prompt("v2_pf_blind")
    assert model.seen_system_prompts[1] == proposals_system_prompt("v2_pf")
    # run 身份:profile 臂 + 双 prompt 版本(盲写/合并)
    identity = json.loads(
        (tmp_path / "runs" / run_id / "run_identity.json").read_text(
            encoding="utf-8"))
    assert identity["profile"]["novel_protocol"] == \
        NOVEL_PROTOCOL_BLIND_FIRST
    prompt_versions = identity["prediction"]["prompt_versions"]
    assert prompt_versions["proposals"] == PROPOSALS_PROMPT_VERSION_V2_PF
    assert prompt_versions["proposals_blind"] == \
        PROPOSALS_PROMPT_VERSION_V2_PF_BLIND


# ======================================================== PC2 合并载荷

def test_pc2_merge_payload_marks_blind_entry(tmp_path) -> None:
    """合并载荷:恰一条目带 origin=blind_first,其 hypothesis_id = 盲写
    prepared hypothesis ID、product_smiles = 盲写声明产物;模型位次以
    第②阶段排序为准(C3);该产物落事件且参与物来自编译 spec。"""
    run_id = "pc2"
    pool_id = _pool_hypothesis_id(run_id)
    blind_id = _blind_prepared_id(run_id)
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK)]),
                   _response([{"hypothesis_id": blind_id},
                              {"hypothesis_id": pool_id}])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    _start_blind(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    merge = json.loads(model.seen_user_payloads[1])
    pool_entries = merge["pool_hypotheses"]
    assert len(pool_entries) == 2                  # 池 1 + 盲写 1
    marked = [e for e in pool_entries
              if e.get("origin") == "blind_first"]
    assert len(marked) == 1
    assert marked[0]["hypothesis_id"] == blind_id
    assert marked[0]["product_smiles"] == NOVEL_OK
    assert marked[0]["transformation_ref"] == "novel-product-first"
    # A/B 语义不受影响:其余池条目不带 origin 键
    assert all("origin" not in e for e in pool_entries
               if e is not marked[0])
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["blind_compiled"][0]["prepared_hypothesis_id"] == \
        blind_id
    # C3:模型位次 = 盲写 prepared ID 在合并 rank 中的位次(第 1 位)
    assert notes[0]["model_rank_by_id"]["novel-1"] == 1
    # 事件:盲写产物落事件,参与物来自编译 spec(非模型自写内容)
    direct = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_OK, [], "novel-1")
    compiled_components = [direct["spec"]["product_smiles"], *(
        direct["spec"].get("coproducts") or [])]
    assert NOVEL_OK in _principal_products(runs_root, run_id)
    assert sorted(_all_event_components(runs_root, run_id)) == sorted(
        ["CC=O", *compiled_components])


# ======================================================== PC3 反馈共用

def test_pc3_feedback_rounds_shared_across_stages(tmp_path) -> None:
    """盲写阶段烧 2 轮 ⇒ 合并阶段只剩 1 轮:总请求 = 1 盲写 + 2 盲写
    反馈 + 1 合并 + 1 合并反馈 = 5;合并第 2 次失败 ⇒ 轮数上限路径
    (verification_rounds_exhausted),不 run 拒。"""
    run_id = "pc3"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)]),      # 盲写首发
                   _response([_novel(NOVEL_BAD_SMILES)]),      # 盲写反馈 1
                   _response([_novel(NOVEL_OK)]),              # 盲写反馈 2
                   _response([_novel(NOVEL_UNSUPPORTED,
                                     hypothesis_id="novel-merge")]),
                   _response([_novel(NOVEL_UNSUPPORTED,
                                     hypothesis_id="novel-merge")])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 5
    rows = _request_rows(runs_root, run_id)
    assert [r[1] for r in rows].count("proposals") == 2
    assert [r[1] for r in rows].count("format_feedback") == 3
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["blind_stage"]["rounds_used"] == 2
    assert notes[0]["verification_rounds"] == 3
    assert notes[0]["verification_rounds_exhausted"]["kind"] == \
        "format_feedback_budget_exhausted"
    assert notes[0]["verification_failures"] == [{
        "hypothesis_id": "novel-merge",
        "failure_kind": "compile_unsupported"}]
    # 盲写通过的那一条照常落事件(合并新 novel 丢弃,不连坐)
    assert NOVEL_OK in _principal_products(runs_root, run_id)


# ======================================================== PC4 预算

def test_pc4_sixth_real_request_refused_at_registration(tmp_path) -> None:
    """预算:5 请求的 C 臂 run 跑完后,第 6 次真实请求在登记处被拒
    (SearchBudgetExhausted / limit_key=max_real_model_requests,拒绝
    先于网络;参照 PF9 姿势)。C 臂发车预算纪律:5/3 合法,6/3 拒。"""
    # C1 预算纪律(发车侧 fail-closed)
    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_product_first_budget(
            NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(max_real=6))
    assert excinfo.value.detail["kind"] == \
        "s5b_product_first_budget_invalid"
    with pytest.raises(S5bOrchestratorError):
        validate_product_first_budget(
            NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(rounds=4))
    validate_product_first_budget(
        NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(max_real=5, rounds=3))

    run_id = "pc4"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_OK)]),
                   _response([_novel(NOVEL_UNSUPPORTED,
                                     hypothesis_id="novel-merge")]),
                   _response([_novel(NOVEL_UNSUPPORTED,
                                     hypothesis_id="novel-merge")])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    # provider_kind=real:每次登记占 max_real_model_requests 额度
    # (scripted 桩零网络;只验证登记面预算,不冒充真实调用)
    _start_blind(tmp_path, run_id, model, provider_kind="real")
    runs_root = tmp_path / "runs"
    assert len(_request_rows(runs_root, run_id)) == 5
    ledger = _ledger(runs_root, run_id)
    probe = ledger.enqueue_action(
        run_id=run_id,
        parent_path_id=stable_id("spath", run_id, "root"),
        context_ref=_decide_context_ref(runs_root, run_id),
        subject_ref="pc4-budget-probe",
        action_kind=ACTION_KIND_EXPAND_HYPOTHESIS,
        parent_search_revision=0, policy_version=search_policy_version(),
        payload={"task_key": "pc4-budget-probe"}, depth=1)
    receipt = ledger.claim_action(probe["action_id"], worker_id="pc4")
    assert receipt["claimed"]
    with pytest.raises(SearchBudgetExhausted) as excinfo:
        ledger.register_model_request(
            run_id=run_id, action_id=probe["action_id"],
            attempt_id=(receipt.get("attempt_refs") or [""])[0],
            provider_kind="real", request_key="pc4-sixth",
            purpose="proposals")
    assert excinfo.value.detail["limit_key"] == "max_real_model_requests"
    # 拒绝零写入(不会多出第 6 行)
    assert len(_request_rows(runs_root, run_id)) == 5


# ======================================================== PC5 阶段间崩溃

def test_pc5_resume_reuses_blind_response(tmp_path) -> None:
    """盲写响应已落盘、合并调用前崩溃 ⇒ resume:盲写 request_id 不变
    (同键复用、状态 responded、零重发),resumed.complete_calls == 1
    (只发合并调用)。"""
    run_id = "pc5"
    runs_root = tmp_path / "runs"
    first = _CountingStub(
        strategy="responses", responses=[_response([_novel(NOVEL_OK)])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    with pytest.raises(SearchCrashInjection):
        _start_blind(tmp_path, run_id, first,
                     crash_after="after_blind_response")
    before = _request_rows(runs_root, run_id)
    assert [r[1] for r in before] == ["proposals"]
    blind_request_id = before[0][0]
    assert before[0][2] == "responded"
    assert first.complete_calls == 1
    resumed = _CountingStub(
        strategy="responses", responses=['{"proposals": [], '
                                         '"rank_hypotheses": []}'],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    out = resume_ppv1_run(
        config=resolve_config(), runs_root=runs_root, run_id=run_id,
        model=resumed, evidence_card_enabled=True,
        evidence_card_version="v1card",
        novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST)
    after = _request_rows(runs_root, run_id)
    assert len(after) == 2
    assert (blind_request_id, "proposals", "responded") in after
    assert resumed.complete_calls == 1        # 只发合并调用
    assert first.complete_calls == 1          # 崩溃前只发过盲写
    assert out["novel_protocol"] == NOVEL_PROTOCOL_BLIND_FIRST
    assert NOVEL_OK in _principal_products(runs_root, run_id)

    # ---- 扩展:阶段①烧 2 轮后崩溃 ⇒ resume 必须按轮号复用两轮原行
    # (零重发),阶段②从第 3 号轮继续(轮号基准 = 阶段①结束计数) ----
    run_id_b = "pc5b"
    runs_root_b = tmp_path / "runs-b"
    first_b = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_BAD_SMILES)]),
                   _response([_novel(NOVEL_OK)])],
        call_account_path=runs_root_b / run_id_b / "s5b_real_calls.jsonl")
    with pytest.raises(SearchCrashInjection):
        _start_blind(tmp_path, run_id_b, first_b,
                     runs_subdir="runs-b",
                     crash_after="after_blind_response")
    before_b = _request_rows(runs_root_b, run_id_b)
    assert [r[1] for r in before_b] == ["format_feedback",
                                        "format_feedback", "proposals"]
    assert [r[2] for r in before_b] == ["responded"] * 3
    assert first_b.complete_calls == 3
    resumed_b = _CountingStub(
        strategy="responses", responses=['{"proposals": [], '
                                         '"rank_hypotheses": []}'],
        call_account_path=runs_root_b / run_id_b / "s5b_real_calls.jsonl")
    resume_ppv1_run(
        config=resolve_config(), runs_root=runs_root_b, run_id=run_id_b,
        model=resumed_b, evidence_card_enabled=True,
        evidence_card_version="v1card",
        novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST)
    after_b = _request_rows(runs_root_b, run_id_b)
    # 崩溃前的 3 行(盲写 + 2 反馈)原样保留;resume 只新增 1 次合并调用
    assert [(r[0], r[1]) for r in after_b[:3]] == \
        [(r[0], r[1]) for r in before_b]
    assert len(after_b) == 4
    assert resumed_b.complete_calls == 1
    assert NOVEL_OK in _principal_products(runs_root_b, run_id_b)


# ======================================================== PC6 A/B 不变

# 主会话改动前采集(@ 8a5af65 工作树;baseline_probe.py 同姿势)
PC6_A_PROMPT = \
    "c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598"
PC6_A_PAYLOAD = \
    "aab7d6e4d18043b3976e43e2bddf04ae866fed9f418dc8039bbe8786c0f6bcff"
PC6_B_PROMPT = \
    "4a7b16282969e42ff7d2e56d93347d40b8fc8b6b1a43365ff6127b4d0e7a62d9"
PC6_B_PAYLOAD_FEEDBACK = \
    "aa69777d99069caf9e5534f39e8dfd5e839ab48be780b3b954ce05c527711b9f"
PC6_VERIFICATION_FAILURES = [
    {"hypothesis_id": "novel-1", "failure_kind": "product_unparseable"},
    {"hypothesis_id": "novel-2", "failure_kind": "product_set_mismatch",
     "executed_components": ["CC=O", "C"]},
]


def test_pc6_a_b_arm_bytes_unchanged(tmp_path) -> None:
    """加入 C 臂代码后 A / B 臂载荷与提示词哈希不变(基线 = 改动前采集;
    b_payload_base 与 a_payload 同值)。"""
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    a_prompt = proposals_system_prompt("v2")
    b_prompt = proposals_system_prompt("v2_pf")
    a_payload = build_proposals_user_payload(
        substrate_smiles=SUBSTRATE_SMILES, atom_id_map=ATOM_ID_MAP,
        pool_entries=POOL_ENTRIES)
    b_payload_base = build_proposals_user_payload(
        substrate_smiles=SUBSTRATE_SMILES, atom_id_map=ATOM_ID_MAP,
        pool_entries=POOL_ENTRIES)
    b_payload_feedback = build_proposals_user_payload(
        substrate_smiles=SUBSTRATE_SMILES, atom_id_map=ATOM_ID_MAP,
        pool_entries=POOL_ENTRIES,
        feedback_error={"failures": PC6_VERIFICATION_FAILURES,
                        "round": 1, "rounds_left": 2})
    assert _sha(a_prompt) == PC6_A_PROMPT == PF7_PROMPT_SHA256
    assert _sha(a_payload) == PC6_A_PAYLOAD == PF7_PAYLOAD_SHA256
    assert _sha(b_prompt) == PC6_B_PROMPT
    assert _sha(b_payload_base) == PC6_A_PAYLOAD
    assert _sha(b_payload_feedback) == PC6_B_PAYLOAD_FEEDBACK
    # B 臂 run 级回归(PF1 断言面照旧):v2_pf 提示词 + 基础载荷无
    # format_feedback、池条目无 origin 键(条件渲染不泄漏到 A/B)
    run_id = "pc6"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK)]),
                   '{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model)
    assert model.seen_system_prompts[0] == proposals_system_prompt("v2_pf")
    assert model.seen_user_payloads[0] != "" and \
        "format_feedback" not in model.seen_user_payloads[0]
    base_payload = json.loads(model.seen_user_payloads[0])
    assert base_payload["pool_hypotheses"]
    assert all("origin" not in entry
               for entry in base_payload["pool_hypotheses"])
    assert NOVEL_OK in _principal_products(tmp_path / "runs", run_id)


# ======================================================== PC7 盲写全失败

def test_pc7_blind_all_failed_merge_still_runs(tmp_path) -> None:
    """盲写阶段零通过(3 轮耗尽 / 直接弃权)⇒ 合并调用照常(只有池
    条目)、池条目落事件、无 run_error。"""
    # (a) 3 轮耗尽:1 盲写 + 3 反馈 = 4,合并 = 1(共 5)
    run_id = "pc7a"
    pool_id = _pool_hypothesis_id(run_id)
    failing = _response([_novel(NOVEL_UNSUPPORTED)])
    model = _CountingStub(
        strategy="responses",
        responses=[failing] * 4 + [_response([{"hypothesis_id": pool_id}])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 5
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["blind_compiled"] == []
    assert notes[0]["blind_stage"]["rounds_used"] == 3
    assert notes[0]["blind_stage"]["failed_proposals"] >= 1
    assert notes[0]["novel_compiled"] == []
    assert _principal_products(runs_root, run_id) == ["CC=O"]
    # (b) 直接弃权:1 盲写 + 1 合并 = 2 请求
    run_id_b = "pc7b"
    pool_id_b = _pool_hypothesis_id(run_id_b)
    model_b = _CountingStub(
        strategy="responses",
        responses=['{"proposals": [], "rank_hypotheses": []}',
                   _response([{"hypothesis_id": pool_id_b}])],
        call_account_path=tmp_path / "runs" / run_id_b
        / "s5b_real_calls.jsonl")
    out_b = _start_blind(tmp_path, run_id_b, model_b)
    assert out_b["stop_reason"] != "run_error"
    assert model_b.complete_calls == 2
    notes_b = _model_notes(runs_root, run_id_b)
    assert notes_b[0]["blind_stage"]["rounds_used"] == 0
    assert notes_b[0]["blind_compiled"] == []
    assert _principal_products(runs_root, run_id_b) == ["CC=O"]


# ======================================================== PC8 三键忽略+记录

PC8_SYNTHETIC_KEYS = {
    "participants": [
        {"state_ref": "cs_fake", "side": "reactant", "role": "cosubstrate",
         "coefficient": "1", "coefficient_status": "known"}],
    "co_substrate_states": [
        {"smiles": "O", "state_ref": "cs_fake", "source_ref": "corpus"}],
    "declared_copy_components": [
        {"smiles": "C", "state_ref": "cs_fake",
         "component_source": "record_declared_copy", "record_key": "r",
         "provenance_sha256": "0" * 64}],
}


def _novel_with_synthetic_keys(product: str = NOVEL_OK,
                               hypothesis_id: str = "novel-1") -> dict:
    item = _novel(product, hypothesis_id=hypothesis_id)
    item["reaction_spec"] = {
        "product_smiles": product,
        **{key: json.loads(json.dumps(value))
           for key, value in PC8_SYNTHETIC_KEYS.items()},
    }
    return item


@pytest.mark.parametrize("protocol", [NOVEL_PROTOCOL_PRODUCT_FIRST,
                                      NOVEL_PROTOCOL_BLIND_FIRST])
def test_pc8_parse_ignores_and_records_synthetic_keys(protocol) -> None:
    """单元级:产物优先分支(B/C)对模型自写三键不抛错;entry.
    ignored_spec_keys == 排序后的多余键集;reaction_spec 只留
    product_smiles/coproducts。"""
    out = parse_model_proposals(
        _response([_novel_with_synthetic_keys()]),
        allowed_hypothesis_ids=[], protocol=protocol)
    entry = out["proposals"][0]
    assert entry["reaction_spec"] == {"product_smiles": NOVEL_OK,
                                      "coproducts": []}
    assert entry["ignored_spec_keys"] == sorted(PC8_SYNTHETIC_KEYS)
    # 正控(clean novel):ignored_spec_keys 恒存在且为空列表
    clean = parse_model_proposals(
        _response([_novel(NOVEL_OK)]), allowed_hypothesis_ids=[],
        protocol=protocol)
    assert clean["proposals"][0]["ignored_spec_keys"] == []
    # atom_edit 分支的拒收判据不动(D2b 验收面)
    with pytest.raises(ModelProtocolError) as excinfo:
        parse_model_proposals(
            _response([_novel_with_synthetic_keys()]),
            allowed_hypothesis_ids=[], protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert excinfo.value.detail["novel_reaction_spec_forbidden_keys"] == \
        list(NOVEL_REACTION_SPEC_FORBIDDEN_KEYS)


def test_pc8_b_arm_ignores_keys_and_events_match_control(tmp_path) -> None:
    """B 臂:novel reaction_spec 携带三键 vs 对照(不带)⇒ 两 run 事件
    参与物完全一致;note.novel_ignored_spec_keys 记录三键;novel_compiled
    条目的 reaction_spec 无三键且与 compile_novel_product_first 直算
    产物集合一致。"""
    runs_root = tmp_path / "runs"
    control_id, keyed_id = "pc8-b-control", "pc8-b-keyed"
    control = _CountingStub(
        strategy="responses", responses=[_response([_novel(NOVEL_OK)])],
        call_account_path=runs_root / control_id / "s5b_real_calls.jsonl")
    _start(tmp_path, control_id, control, pool={})
    keyed = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys()])],
        call_account_path=runs_root / keyed_id / "s5b_real_calls.jsonl")
    _start(tmp_path, keyed_id, keyed, pool={})
    # ① 事件参与物完全一致(principal + 全组分)
    assert _principal_products(runs_root, keyed_id) == \
        _principal_products(runs_root, control_id)
    assert sorted(_all_event_components(runs_root, keyed_id)) == \
        sorted(_all_event_components(runs_root, control_id))
    # ② note 记录被忽略的键名
    notes = _model_notes(runs_root, keyed_id)
    assert notes[0]["novel_ignored_spec_keys"] == {
        "novel-1": sorted(PC8_SYNTHETIC_KEYS)}
    assert _model_notes(runs_root, control_id)[0].get(
        "novel_ignored_spec_keys") is None
    # ③ 编译 spec 无三键,产物集合 = 直算编译结果
    entry = notes[0]["novel_compiled"][0]
    spec = entry["reaction_spec"]
    for key in PC8_SYNTHETIC_KEYS:
        assert key not in spec
    direct = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_OK, [], "novel-1")
    assert sorted([spec["product_smiles"], *spec.get("coproducts", [])]) == \
        sorted([direct["spec"]["product_smiles"],
                *direct["spec"].get("coproducts", [])])
    assert entry["ignored_spec_keys"] == sorted(PC8_SYNTHETIC_KEYS)


def test_pc8_c_arm_blind_stage_ignores_keys_and_records(tmp_path) -> None:
    """C 臂:盲写阶段带三键 ⇒ 同样被忽略 + 记录(note.novel_ignored_spec
    keys 含盲写自报 ID;blind_compiled.reaction_spec 无三键),事件
    参与物 = 编译 spec。"""
    run_id = "pc8-c"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys()]),
                   '{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    _start_blind(tmp_path, run_id, model, pool={})
    runs_root = tmp_path / "runs"
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_ignored_spec_keys"] == {
        "novel-1": sorted(PC8_SYNTHETIC_KEYS)}
    blind_entry = notes[0]["blind_compiled"][0]
    for key in PC8_SYNTHETIC_KEYS:
        assert key not in blind_entry["reaction_spec"]
    direct = compile_novel_product_first(
        SUBSTRATE_SMILES, NOVEL_OK, [], "novel-1")
    assert sorted(_all_event_components(runs_root, run_id)) == sorted(
        [direct["spec"]["product_smiles"],
         *direct["spec"].get("coproducts", [])])
    assert blind_entry["ignored_spec_keys"] == sorted(PC8_SYNTHETIC_KEYS)


# ============================================== P1 回修(PC9–PC12,2026-11-06)
#
# 依据 docs/reviews/codex/EXP1_CARM_CODEX_REVIEW_2026-11-06.md:
#   * P1-1 跨阶段自报 ID 合法同名 ⇒ 位次只认合并阶段 prepared ID,
#     自报 ID 仅披露;同名时新提案优先,未被提及的盲写条目 fallback;
#   * P1-2 origin 按盲写条目的 prepared hypothesis ID 标,不按内部池
#     逻辑 key / 自报 ID 字串匹配;
#   * P1-3 B 臂每次成功解析后累积所有 novel 的 ignored_spec_keys
#     (同 ID 跨轮并集),失败/早轮条目的键名不从 note 消失;
#     C 臂两阶段同一张表(解析即汇总)。
# 全部 scripted、零真实模型/零网络;合成通用分子(乙醇/乙醛/乙酸/丙酸)。

# ======================================================== PC9a P1-1 反例 A

def test_pc9a_cross_stage_same_self_report_id_explicit_rank(tmp_path) -> None:
    """P1-1 反例 A(显式排序):阶段①盲写与阶段②新提案都用自报 ID
    ``novel-1``(产物不同,不去重);合并 rank = [新novel-1, 池prepared,
    盲写prepared] ⇒ 新丙酸 rank 1、池 rank 2、盲写乙酸 rank 3。

    note 位次键只按 prepared ID 命名空间(自报 ID 不覆盖新提案位次),
    自报 ID 只出现在 ``model_rank_self_reported_ids`` 披露字段。"""
    run_id = "pc9a"
    pool_id = _pool_hypothesis_id(run_id)
    blind_id = _blind_prepared_id(run_id)                  # 盲写乙酸
    new_id = _merge_novel_prepared_id(run_id, "CCC(=O)O")  # 合并新丙酸
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK, "novel-1")]),
                   _response([_novel("CCC(=O)O", "novel-1"),
                              {"hypothesis_id": pool_id},
                              {"hypothesis_id": blind_id}],
                             rank=["novel-1", pool_id, blind_id])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model)
    assert out["stop_reason"] != "run_error"
    runs_root = tmp_path / "runs"
    notes = _model_notes(runs_root, run_id)
    # ① 披露:三个条目都在 prepared ID 命名空间,自报 ID 不占位次键
    assert notes[0]["model_rank_by_id"] == {
        new_id: 1, pool_id: 2, blind_id: 3}
    assert "novel-1" not in notes[0]["model_rank_by_id"]
    assert notes[0]["model_rank_self_reported_ids"] == {
        "novel-1": {"position": 1, "prepared_hypothesis_id": new_id}}
    # ② 展开载荷:prepared ID 各自的 explicit rank 生效(不互相覆盖)
    payloads = _expand_payloads(runs_root, run_id)
    assert payloads[new_id]["effective_rank"] == 1
    assert payloads[new_id]["rank_basis"] == "model_selection"
    assert payloads[new_id]["logical_proposal_id"] == "novel-1"
    assert payloads[pool_id]["effective_rank"] == 2
    assert payloads[pool_id]["rank_basis"] == "model_selection"
    assert payloads[blind_id]["effective_rank"] == 3
    assert payloads[blind_id]["model_rank"] == 3
    assert payloads[blind_id]["rank_basis"] == "model_selection"
    # ③ 事件提交序 = 位次序(新丙酸 → 池乙醛 → 盲写乙酸)
    assert _principal_products_in_submission_order(runs_root, run_id) == [
        "CCC(=O)O", "CC=O", "CC(=O)O"]


# ======================================================== PC9b P1-1 反例 B

def test_pc9b_cross_stage_unmentioned_blind_falls_back(tmp_path) -> None:
    """P1-1 反例 B(未提及 fallback):合并 rank 只写
    [新novel-1, 池prepared],完全不提盲写 prepared ID ⇒ 盲写乙酸
    ``rank_basis=deterministic_fallback``、排在两个显式排序条目之后
    (不继承同名新提案的 rank 1)。"""
    run_id = "pc9b"
    pool_id = _pool_hypothesis_id(run_id)
    blind_id = _blind_prepared_id(run_id)
    new_id = _merge_novel_prepared_id(run_id, "CCC(=O)O")
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK, "novel-1")]),
                   _response([_novel("CCC(=O)O", "novel-1"),
                              {"hypothesis_id": pool_id}],
                             rank=["novel-1", pool_id])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model)
    assert out["stop_reason"] != "run_error"
    runs_root = tmp_path / "runs"
    notes = _model_notes(runs_root, run_id)
    # 未提及的盲写 prepared ID 不得借同名自报 ID 取得显式位次
    assert notes[0]["model_rank_by_id"] == {new_id: 1, pool_id: 2}
    assert blind_id not in notes[0]["model_rank_by_id"]
    payloads = _expand_payloads(runs_root, run_id)
    assert payloads[new_id]["effective_rank"] == 1
    assert payloads[pool_id]["effective_rank"] == 2
    assert payloads[blind_id]["model_rank"] is None
    assert payloads[blind_id]["effective_rank"] == 3
    assert payloads[blind_id]["rank_basis"] == "deterministic_fallback"
    assert _principal_products_in_submission_order(runs_root, run_id) == [
        "CCC(=O)O", "CC=O", "CC(=O)O"]


# ======================================================== PC10 P1-2 反例

def test_pc10_origin_marks_only_blind_prepared_id(tmp_path) -> None:
    """P1-2 反例:盲写自报 ID 与真实池逻辑 key 同名(产物不同)⇒ 合并
    载荷里真实池条目**无** origin 键、盲写条目 origin=blind_first,
    两者 hypothesis_id 不同(来源按 prepared ID 判定,不按字串)。"""
    run_id = "pc10"
    pool_key = str(POOL_SPEC["key"])       # 真实池逻辑 key
    pool_id = _pool_hypothesis_id(run_id)
    blind_id = _blind_prepared_id(run_id, hypothesis_id=pool_key)
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK, pool_key)]),
                   _response([{"hypothesis_id": pool_id},
                              {"hypothesis_id": blind_id}])],
        call_account_path=tmp_path / "runs" / run_id
        / "s5b_real_calls.jsonl")
    _start_blind(tmp_path, run_id, model)
    runs_root = tmp_path / "runs"
    # 盲写条目的自报 ID 确实撞上池逻辑 key(前提成立)
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["blind_compiled"][0]["hypothesis_id"] == pool_key
    assert notes[0]["blind_compiled"][0]["prepared_hypothesis_id"] == \
        blind_id
    merge = json.loads(model.seen_user_payloads[1])
    entries = merge["pool_hypotheses"]
    assert len(entries) == 2
    by_id = {str(entry["hypothesis_id"]): entry for entry in entries}
    assert pool_id != blind_id
    assert "origin" not in by_id[pool_id], \
        "真实池条目不得被同名盲写自报 ID 误标 blind_first"
    assert by_id[pool_id]["product_smiles"] == "CC=O"
    assert by_id[blind_id]["origin"] == "blind_first"
    assert by_id[blind_id]["product_smiles"] == NOVEL_OK
    # 两条都照常落事件(来源标记错误不连累调度)
    assert sorted(_principal_products(runs_root, run_id)) == sorted(
        ["CC=O", NOVEL_OK])


# ======================================================== PC11 P1-3(B 臂)

def test_pc11_b_arm_accumulates_ignored_keys_across_rounds(
        tmp_path) -> None:
    """P1-3 反例(B 臂):①带三键 + ``product_smiles`` 不可解析、0 反馈
    轮 ⇒ note 记录三键;②第一轮带三键的合法 novel + 另一条失败 novel,
    反馈后弃权 ⇒ 早轮三键仍在 note;③clean 响应 ⇒ note 无该键、
    A 臂零新键(正控)。"""
    expected = {"novel-1": sorted(PC8_SYNTHETIC_KEYS)}
    runs_root = tmp_path / "runs"

    # ① 核验失败(0 反馈轮):失败条目不进 novel_compiled,键名仍须留痕
    run_id = "pc11a"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys(
            NOVEL_BAD_SMILES)])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id, model, profile=_profile(rounds=0))
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_compiled"] == []
    assert notes[0]["verification_failures"] == [{
        "hypothesis_id": "novel-1",
        "failure_kind": FAILURE_PRODUCT_UNPARSEABLE}]
    assert notes[0]["novel_ignored_spec_keys"] == expected
    assert model.complete_calls == 1        # 0 反馈轮
    assert _principal_products(runs_root, run_id) == ["CC=O"]

    # ② 早轮被反馈冲掉:末轮弃权 ⇒ 早轮三键仍在 note;P0-1 下早轮 full 条目跨轮保留
    run_id_b = "pc11b"
    model_b = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys(NOVEL_OK),
                              _novel(NOVEL_BAD_SMILES, "novel-2")]),
                   '{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=runs_root / run_id_b / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id_b, model_b)
    notes_b = _model_notes(runs_root, run_id_b)
    assert model_b.complete_calls == 2      # 1 首发 + 1 反馈
    assert len(notes_b[0]["novel_compiled"]) == 1  # P0-1:早轮 full 跨轮保留
    assert notes_b[0]["novel_ignored_spec_keys"] == expected

    # ③ 正控:clean 响应零新键;++ A 臂零新键
    run_id_c = "pc11c"
    model_c = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK)])],
        call_account_path=runs_root / run_id_c / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id_c, model_c)
    notes_c = _model_notes(runs_root, run_id_c)
    assert notes_c[0]["novel_compiled"]
    assert notes_c[0].get("novel_ignored_spec_keys") is None
    run_id_d = "pc11d"
    model_d = _CountingStub(
        strategy="responses",
        responses=['{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=runs_root / run_id_d / "s5b_real_calls.jsonl")
    _start(tmp_path, run_id_d, model_d,
           novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    notes_d = _model_notes(runs_root, run_id_d)
    assert notes_d[0].get("novel_ignored_spec_keys") is None


# ======================================================== PC12 P1-3(C 臂)

def test_pc12_c_arm_merge_stage_ignored_keys_recorded(tmp_path) -> None:
    """P1-3 同款(C 臂):合并阶段新提案带三键且核验失败 ⇒ note 仍记录
    键名(盲写+合并两阶段同一张累积表;仅非空时写该键)。"""
    runs_root = tmp_path / "runs"

    # ① 合并阶段唯一提案带三键且不可解析(0 轮)⇒ 键名留痕
    run_id = "pc12a"
    model = _CountingStub(
        strategy="responses",
        responses=['{"proposals": [], "rank_hypotheses": []}',
                   _response([_novel_with_synthetic_keys(
                       NOVEL_BAD_SMILES, "novel-merge")])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl")
    out = _start_blind(tmp_path, run_id, model, rounds=0)
    assert out["stop_reason"] != "run_error"
    notes = _model_notes(runs_root, run_id)
    assert notes[0]["novel_ignored_spec_keys"] == {
        "novel-merge": sorted(PC8_SYNTHETIC_KEYS)}
    assert notes[0]["verification_failures"] == [{
        "hypothesis_id": "novel-merge",
        "failure_kind": FAILURE_PRODUCT_UNPARSEABLE}]
    assert _principal_products(runs_root, run_id) == ["CC=O"]   # 池不连坐

    # ② 两阶段并集:盲写段带三键(合法)+ 合并段带三键(失败、烧 1 轮)
    run_id_b = "pc12b"
    model_b = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys(NOVEL_OK)]),
                   _response([_novel_with_synthetic_keys(
                       NOVEL_BAD_SMILES, "novel-merge")]),
                   '{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=runs_root / run_id_b / "s5b_real_calls.jsonl")
    out_b = _start_blind(tmp_path, run_id_b, model_b, rounds=1)
    assert out_b["stop_reason"] != "run_error"
    notes_b = _model_notes(runs_root, run_id_b)
    assert notes_b[0]["novel_ignored_spec_keys"] == {
        "novel-1": sorted(PC8_SYNTHETIC_KEYS),
        "novel-merge": sorted(PC8_SYNTHETIC_KEYS)}
    # 盲写合法条目照常落事件,合并失败条目不落
    assert NOVEL_OK in _principal_products(runs_root, run_id_b)
    assert "CC=O" in _principal_products(runs_root, run_id_b)

    # ③ 同 ID 跨轮并集:盲写反馈轮重提同一 ID、多余键变少 ⇒ 早轮键名
    # 不因末轮条目更短而丢失(C 臂两阶段同一张累积表)
    run_id_c = "pc12c"
    partial = _novel(NOVEL_OK, "novel-1")
    partial["reaction_spec"] = {
        "product_smiles": NOVEL_OK,
        "participants": json.loads(json.dumps(
            PC8_SYNTHETIC_KEYS["participants"]))}
    model_c = _CountingStub(
        strategy="responses",
        responses=[_response([_novel_with_synthetic_keys(
                       NOVEL_BAD_SMILES, "novel-1")]),
                   _response([partial]),
                   '{"proposals": [], "rank_hypotheses": []}'],
        call_account_path=runs_root / run_id_c / "s5b_real_calls.jsonl")
    out_c = _start_blind(tmp_path, run_id_c, model_c, rounds=1)
    assert out_c["stop_reason"] != "run_error"
    notes_c = _model_notes(runs_root, run_id_c)
    assert notes_c[0]["novel_ignored_spec_keys"] == {
        "novel-1": sorted(PC8_SYNTHETIC_KEYS)}
    assert NOVEL_OK in _principal_products(runs_root, run_id_c)


# ============================================== E1(M1):底物规范化对齐生产执行器

def test_pf_m1_noncanonical_substrate_end_to_end(tmp_path) -> None:
    """M1 修复(2026-11-06):产物优先编译入口先以 strict_identity_of
    (与 substrate_state.smiles_isomeric 同源)规范化底物串,消除非
    canonical 输入写法导致的编译/生产执行原子序漂移。

    覆盖:
    - 苯酚非 canonical 合法写法 ``c1ccccc1O``(修复前生产执行撞
      ``AtomValenceException``)与 ``c1ccc(O)cc1``(修复前静默产出
      错位异构体 ``Oc1cccc(O)c1``)→ 邻苯二酚 ``Oc1ccccc1O``:
      ① compile_novel_product_first 编译通过 + execute_atomtool_expansion
        在 substrate_state.smiles_isomeric(``Oc1ccccc1``)上执行通过且
        产出 ``Oc1ccccc1O``;
      ② B 臂与 C 臂完整 runflow 端到端落事件,主产物为 ``Oc1ccccc1O``;
    - 底物不可解析或未过 CX 守卫 ⇒ fail-closed 结构化失败返回(不抛未捕获异常)。
    """
    from pathway_v43.pollutant.production import execute_atomtool_expansion

    catechol = "Oc1ccccc1O"
    runs_root = tmp_path / "runs"

    for tag, raw_phenol in (("valence", "c1ccccc1O"),
                            ("isomer", "c1ccc(O)cc1")):
        substrate_state = build_chemical_state(raw_phenol, "raw_input")
        assert substrate_state.smiles_isomeric == "Oc1ccccc1"
        assert substrate_state.smiles_isomeric != raw_phenol

        # ① 编译 + 生产执行器同源规范底物执行验证
        compiled = compile_novel_product_first(
            raw_phenol, catechol, [], f"m1-{tag}")
        assert compiled["status"] == "compiled", tag
        assert compiled["verification_tier"] == VERIFICATION_TIER_FULL, tag
        assert compiled["bucket_kind"] == BUCKET_KIND_FULL, tag
        execution = execute_atomtool_expansion(
            substrate_smiles=substrate_state.smiles_isomeric,
            tool_inputs=compiled["spec"])
        assert execution["execution_ok"] is True, (tag, execution["result"])
        assert execution["result"]["product_smiles"] == catechol, tag
        assert execution["center_evidence"]["center_match"] is True, tag

        # ② B 臂完整 runflow 端到端落事件(prepare + expand + audit + store)
        run_id_b = f"m1-b-{tag}"
        model_b = _CountingStub(
            strategy="responses",
            responses=[_response([_novel(catechol, "novel-1")])],
            call_account_path=runs_root / run_id_b / "s5b_real_calls.jsonl")
        out_b = _start(
            tmp_path, run_id_b, model_b, smiles=raw_phenol, pool={})
        assert out_b["stop_reason"] != "run_error", tag
        assert _principal_products(runs_root, run_id_b) == [catechol], tag
        notes_b = _model_notes(runs_root, run_id_b)
        assert len(notes_b[0]["novel_compiled"]) == 1, tag

        # ③ C 臂完整 runflow 端到端落事件(盲写阶段编译 + 合并阶段排序 + 生产落库)
        run_id_c = f"m1-c-{tag}"
        model_c = _CountingStub(
            strategy="responses",
            responses=[_response([_novel(catechol, "novel-1")]),
                       '{"proposals": [], "rank_hypotheses": []}'],
            call_account_path=runs_root / run_id_c / "s5b_real_calls.jsonl")
        out_c = _start_blind(
            tmp_path, run_id_c, model_c, smiles=raw_phenol, pool={})
        assert out_c["stop_reason"] != "run_error", tag
        assert _principal_products(runs_root, run_id_c) == [catechol], tag
        notes_c = _model_notes(runs_root, run_id_c)
        assert len(notes_c[0]["blind_compiled"]) == 1, tag

    # ④ 底物不可解析 / 未过 CX 守卫 ⇒ fail-closed 结构化失败返回(不抛异常)
    for bad_sub in ("not_a_smiles", "", "CCO |r|"):
        failed = compile_novel_product_first(bad_sub, catechol, [], "m1-bad")
        assert failed["status"] == "failed", bad_sub
        assert failed["failure_kind"] == "compile_unsupported", bad_sub


# ======================================================== F1 发车预算按臂精确相等与顶层错位键拦截

def test_f1_exact_arm_budget_and_top_level_misplaced_keys_rejected(
    tmp_path,
) -> None:
    """发车前加固(F1):validate_product_first_budget 按臂精确相等 + 顶层错位键拒。

    - 正控:
      * A 臂(atom_edit / None):1/0(及 S5B_DEFAULT_PROFILE_POLICY / None)通过;
      * B 臂(product_first_feedback):4/3 通过;
      * C 臂(product_first_feedback_blind_first):5/3 通过;
    - 负控:
      * B/C 臂预算偏小(1/0、2/1、3/2、4/2、C 臂传 4/3、None 缺省 1/0)被拒;
      * B/C 臂预算偏大(B 臂传 5/3、C 臂传 6/3、B 臂 4/4、C 臂 5/4)被拒;
      * A 臂非 1/0(2/0、1/1、4/3、5/3、0/0)被拒;
      * 顶层错位写法:``policy = dict(S5B_DEFAULT_PROFILE_POLICY);
        policy['max_real_model_requests'] = 4;
        policy['max_format_feedback_rounds'] = 3`` 传给
        ``validate_profile_policy``、``validate_product_first_budget`` 及
        ``run_s5b_batch`` 时一律结构化拒(先于 orchestration.json 落盘)。
    """
    assert S5B_ARM_EXACT_BUDGETS == {
        NOVEL_PROTOCOL_ATOM_EDIT: (1, 0),
        NOVEL_PROTOCOL_PRODUCT_FIRST: (4, 3),
        NOVEL_PROTOCOL_BLIND_FIRST: (5, 3),
    }

    # ---- 1. 正控:三臂精确预算全部通过 ----
    validate_product_first_budget(None, None)
    validate_product_first_budget(
        NOVEL_PROTOCOL_ATOM_EDIT, _profile(max_real=1, rounds=0))
    validate_product_first_budget(
        NOVEL_PROTOCOL_PRODUCT_FIRST, _profile(max_real=4, rounds=3))
    validate_product_first_budget(
        NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(max_real=5, rounds=3))

    # ---- 2. 负控:B 臂偏小与偏大预算一律被拒 ----
    for bad_req, bad_rounds in (
        (1, 0), (2, 1), (3, 2), (4, 2), (3, 3), (0, 0),
        (5, 3), (6, 3), (4, 4), (5, 4),
    ):
        with pytest.raises(S5bOrchestratorError) as excinfo:
            validate_product_first_budget(
                NOVEL_PROTOCOL_PRODUCT_FIRST,
                _profile(max_real=bad_req, rounds=bad_rounds))
        assert excinfo.value.detail["kind"] == \
            "s5b_product_first_budget_invalid", (bad_req, bad_rounds)
    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_product_first_budget(NOVEL_PROTOCOL_PRODUCT_FIRST, None)
    assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"

    # ---- 3. 负控:C 臂偏小(含 4/3)与偏大预算一律被拒 ----
    for bad_req, bad_rounds in (
        (1, 0), (2, 1), (3, 2), (4, 3), (5, 2), (0, 0),
        (6, 3), (5, 4), (6, 4),
    ):
        with pytest.raises(S5bOrchestratorError) as excinfo:
            validate_product_first_budget(
                NOVEL_PROTOCOL_BLIND_FIRST,
                _blind_profile(max_real=bad_req, rounds=bad_rounds))
        assert excinfo.value.detail["kind"] == \
            "s5b_product_first_budget_invalid", (bad_req, bad_rounds)
    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_product_first_budget(NOVEL_PROTOCOL_BLIND_FIRST, None)
    assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"

    # ---- 4. 负控:A 臂非 1/0 预算一律被拒 ----
    for bad_req, bad_rounds in (
        (2, 0), (1, 1), (4, 3), (5, 3), (0, 0), (1, 2),
    ):
        with pytest.raises(S5bOrchestratorError) as excinfo:
            validate_product_first_budget(
                NOVEL_PROTOCOL_ATOM_EDIT,
                _profile(max_real=bad_req, rounds=bad_rounds))
        assert excinfo.value.detail["kind"] == \
            "s5b_product_first_budget_invalid", (bad_req, bad_rounds)

    # ---- 4b. 负控:三臂 max_alternative_hypotheses_per_parent != 12 一律被拒 ----
    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_product_first_budget(
            NOVEL_PROTOCOL_ATOM_EDIT, S5B_DEFAULT_PROFILE_POLICY)
    assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"
    assert excinfo.value.detail["reason"] == "max_alternative_hypotheses_per_parent_mismatch"

    for proto, base_prof in (
        (NOVEL_PROTOCOL_ATOM_EDIT, _profile(max_real=1, rounds=0)),
        (NOVEL_PROTOCOL_PRODUCT_FIRST, _profile(max_real=4, rounds=3)),
        (NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(max_real=5, rounds=3)),
    ):
        for bad_alt in (0, 8, 10, 16):
            bad_prof = copy.deepcopy(base_prof)
            bad_prof["search_limits"]["max_alternative_hypotheses_per_parent"] = bad_alt
            with pytest.raises(S5bOrchestratorError) as excinfo:
                validate_product_first_budget(proto, bad_prof)
            assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"
            assert excinfo.value.detail["reason"] == "max_alternative_hypotheses_per_parent_mismatch"

    # ---- 4c. 负控:三臂 max_total_search_actions != 48 一律被拒 ----
    for proto, base_prof in (
        (NOVEL_PROTOCOL_ATOM_EDIT, _profile(max_real=1, rounds=0)),
        (NOVEL_PROTOCOL_PRODUCT_FIRST, _profile(max_real=4, rounds=3)),
        (NOVEL_PROTOCOL_BLIND_FIRST, _blind_profile(max_real=5, rounds=3)),
    ):
        for bad_actions in (0, 20, 47, 49, 100):
            bad_prof = copy.deepcopy(base_prof)
            bad_prof["search_limits"]["max_total_search_actions"] = bad_actions
            with pytest.raises(S5bOrchestratorError) as excinfo:
                validate_product_first_budget(proto, bad_prof)
            assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"
            assert excinfo.value.detail["reason"] == "max_total_search_actions_mismatch"

    # ---- 5. 负控:顶层错位写法(F1 原发车单 bug 形态)在全部入口被拒 ----
    misplaced_policy = dict(S5B_DEFAULT_PROFILE_POLICY)
    misplaced_policy["max_real_model_requests"] = 4
    misplaced_policy["max_format_feedback_rounds"] = 3

    with pytest.raises(S5bOrchestratorError) as excinfo:
        validate_profile_policy(misplaced_policy)
    assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"
    assert excinfo.value.detail["reason"] == \
        "profile_policy_unknown_top_level_keys"
    assert excinfo.value.detail["unknown_top_level_keys"] == [
        "max_format_feedback_rounds", "max_real_model_requests"
    ]

    for proto in (
        NOVEL_PROTOCOL_ATOM_EDIT,
        NOVEL_PROTOCOL_PRODUCT_FIRST,
        NOVEL_PROTOCOL_BLIND_FIRST,
    ):
        with pytest.raises(S5bOrchestratorError) as excinfo:
            validate_product_first_budget(proto, misplaced_policy)
        assert excinfo.value.detail["kind"] == \
            "s5b_product_first_budget_invalid"
        assert excinfo.value.detail["reason"] == \
            "profile_policy_unknown_top_level_keys"

    # 顶层错位写法传给 run_s5b_batch(含 B 臂与 A 臂)⇒ 先于冻结文件写入直接拒
    b_misplaced_root = _scripted_batch(tmp_path, "b-misplaced")
    with pytest.raises(S5bOrchestratorError) as excinfo:
        run_s5b_batch(
            b_misplaced_root,
            runs_root=tmp_path / "runs-b-misplaced",
            workers=1,
            poll_s=0.05,
            gate_max_calls=50,
            evidence_card_enabled=True,
            novel_protocol=NOVEL_PROTOCOL_PRODUCT_FIRST,
            profile_policy=misplaced_policy,
        )
    assert excinfo.value.detail["kind"] == "s5b_product_first_budget_invalid"
    assert excinfo.value.detail["reason"] == \
        "profile_policy_unknown_top_level_keys"
    assert not (b_misplaced_root / "orchestration.json").exists()
    assert not (b_misplaced_root / "profile_policy.json").exists()


# ======================================================== 3a:P0-1 / P0-2 / P0-3 / P1-1 / P1-2 正负控测试

class _TransportFailingStub(_CountingStub):
    """在第 ``fail_at_call`` 次 _complete 调用(0-based)返回传输失败 LLMResponse。"""

    def __init__(self, *, fail_at_call: int, **kwargs):
        super().__init__(**kwargs)
        self.fail_at_call = int(fail_at_call)

    def _complete(self, *, system_prompt, user_payload, idempotency_key):
        idx = self.complete_calls
        if idx == self.fail_at_call:
            self.complete_calls += 1
            from pathway_v43.adapters.llm_client import LLMResponse
            return LLMResponse(
                ok=False,
                error_kind="timeout",
                error_message="simulated_timeout_or_429",
            )
        return super()._complete(
            system_prompt=system_prompt,
            user_payload=user_payload,
            idempotency_key=idempotency_key,
        )


def test_p0_1_cross_round_retention_rank_synthesis_and_dedup(tmp_path) -> None:
    """P0-1(B 臂):跨轮保留已通过 full 核验的 novel 提案 + 排序合成 + 净反应签名去重。

    - 正控 1:第 0 轮通过 novel-early(CC(=O)O, full)和 novel-po3(CCOP(=O)(O)O, full),
      同时 novel-bad 失败触发第 1 轮;第 1 轮只显式重排 novel-late(OCC(=O)O, full)
      且未复述早轮两条 ⇒ 合成顺序为:
      [末轮显式 novel-late] → [早轮 novel-early, novel-po3(按首次通过轮次→轮内位次)]
      → [未显式排序的池条目 CC=O];
    - 正控 2:同净反应签名去重(早轮 novel-early 与末轮 novel-dup 写同一产物 CC(=O)O),
      只落 1 条事件且位次取最优;
    - 负控:早轮仅过 declared 桶(NOVEL_BIG)或核验失败(NOVEL_BAD_SMILES)的条目不进入
      跨轮 full 保留集、不落事件。
    """
    from pathway_v43.pollutant.chemstate import strict_identity_of

    runs_root = tmp_path / "runs"
    run_id = "p0-1-b-synth"
    r0 = _response(
        [
            _novel(NOVEL_OK, "novel-early"),
            _novel(NOVEL_PO3, "novel-po3"),
            _novel(NOVEL_BIG, "novel-declared"),
            _novel(NOVEL_BAD_SMILES, "novel-bad"),
        ],
        rank=["novel-early", "novel-po3", "novel-declared", "novel-bad"],
    )
    r1 = _response(
        [
            _novel(NOVEL_2_FRAGS, "novel-late"),
            _novel(NOVEL_OK, "novel-dup"),
        ],
        rank=["novel-late", "novel-dup"],
    )
    model = _CountingStub(
        strategy="responses",
        responses=[r0, r1],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start(tmp_path, run_id, model)
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 2
    products = _principal_products_in_submission_order(runs_root, run_id)
    # 顺序:末轮显式(novel-late: O=C(O)CO, novel-dup/early 去重: CC(=O)O)
    #       → 早轮未复述(novel-po3: O=P(O)(O)OCC)
    #       → 未被显式排序的池条目(CC=O)
    assert products == [
        strict_identity_of(NOVEL_2_FRAGS),
        strict_identity_of(NOVEL_OK),
        strict_identity_of(NOVEL_PO3),
        "CC=O",
    ]
    assert strict_identity_of(NOVEL_BIG) not in products


def test_p0_1_c_arm_merge_rank_synthesis_and_blind_slot_reservation(
    tmp_path,
) -> None:
    """P0-1(C 臂):合并阶段排序合成 + 扩展宽度截断时为盲写条目至少保留 1 个名额。

    - 正控 1:盲写段通过 blind-1(CC(=O)O),合并段只显式排 1 条池条目(pool_1),
      另 1 条池条目(pool_2)未显式排 ⇒ 合成顺序为:
      [合并显式排序 pool_1] → [盲写通过未复述 blind-1] → [未排序池条目 pool_2];
    - 正控 2:当 max_alternative_hypotheses_per_parent=1(仅够 1 个名额)且合并段只显式排
      pool_1 时,截断后仍为盲写通过条目保留至少 1 个名额(blind-1 落事件);
    - 负控:当盲写段无通过条目时,池条目正常使用名额,不空占。
    """
    runs_root = tmp_path / "runs"

    pool_b_compiled = compile_novel_product_first(
        SUBSTRATE_SMILES, "CCOC", [], "synth-pool-b")
    assert pool_b_compiled["status"] == "compiled"
    pool_spec_2 = {
        **dict(pool_b_compiled["spec"]),
        "key": "rec-SYNTH_POOL_B@L3",
        "transformation_ref": "SYNTH_POOL_B@L3",
        "origin_group_key": "rec-source:SYNTH_POOL_B@L3",
    }
    two_pools = {SUBSTRATE_SMILES: [dict(POOL_SPEC), pool_spec_2]}

    # 先算出 pool_1 在 run 内的 hypothesis_id
    run_id_order = "p0-1-c-order"
    pool_1_id = _pool_hypothesis_id(run_id_order)
    model_order = _CountingStub(
        strategy="responses",
        responses=[
            _response([_novel(NOVEL_OK, "blind-1")]),
            _response([{"hypothesis_id": pool_1_id}], rank=[pool_1_id]),
        ],
        call_account_path=runs_root / run_id_order / "s5b_real_calls.jsonl",
    )
    out_order = _start_blind(
        tmp_path, run_id_order, model_order, rounds=1, pool=two_pools)
    assert out_order["stop_reason"] != "run_error"
    assert _principal_products_in_submission_order(runs_root, run_id_order) == [
        "CC=O", NOVEL_OK, "CCOC"
    ]

    # 扩展宽度截断 = 1:合并段只排 pool_1,但盲写 blind-1 至少保底 1 个名额
    run_id_cap = "p0-1-c-cap1"
    pool_1_id_cap = _pool_hypothesis_id(run_id_cap)
    cap_profile = _blind_profile(max_real=5, rounds=3)
    cap_profile["search_limits"] = {
        **cap_profile["search_limits"],
        "max_alternative_hypotheses_per_parent": 1,
    }
    model_cap = _CountingStub(
        strategy="responses",
        responses=[
            _response([_novel(NOVEL_OK, "blind-1")]),
            _response([{"hypothesis_id": pool_1_id_cap}], rank=[pool_1_id_cap]),
        ],
        call_account_path=runs_root / run_id_cap / "s5b_real_calls.jsonl",
    )
    out_cap = _start(
        tmp_path, run_id_cap, model_cap,
        novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST,
        profile=cap_profile,
        pool=two_pools,
    )
    assert out_cap["stop_reason"] != "run_error"
    assert _principal_products_in_submission_order(runs_root, run_id_cap) == [
        NOVEL_OK
    ]

    # 负控:盲写段弃权(无盲写通过条目)+ 截断=1 ⇒ pool_1 正常拿到名额
    run_id_neg = "p0-1-c-cap1-nobld"
    pool_1_id_neg = _pool_hypothesis_id(run_id_neg)
    model_neg = _CountingStub(
        strategy="responses",
        responses=[
            '{"proposals": [], "rank_hypotheses": []}',
            _response([{"hypothesis_id": pool_1_id_neg}], rank=[pool_1_id_neg]),
        ],
        call_account_path=runs_root / run_id_neg / "s5b_real_calls.jsonl",
    )
    out_neg = _start(
        tmp_path, run_id_neg, model_neg,
        novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST,
        profile=cap_profile,
        pool=two_pools,
    )
    assert out_neg["stop_reason"] != "run_error"
    assert _principal_products_in_submission_order(runs_root, run_id_neg) == [
        "CC=O"
    ]


def test_p0_2_subsequent_round_transport_failure_fallback(tmp_path) -> None:
    """P0-2:后续轮(反馈轮 / 合并轮)传输失败回退到已落账已核验状态,记 transport_aborted_round,
    兜底零补发请求;仅首轮首发失败且无任何可用候选时走 run 级失败。"""
    runs_root = tmp_path / "runs"

    # ① 正控 A(B 臂第 1 轮反馈传输失败):第 0 轮有 full 提案 + 失败提案 ⇒ 回退保留第 0 轮 full + 池
    run_b = "p0-2-b-fb-abort"
    model_b = _TransportFailingStub(
        fail_at_call=1,
        strategy="responses",
        responses=[
            _response([_novel(NOVEL_OK, "novel-ok"),
                       _novel(NOVEL_BAD_SMILES, "novel-bad")]),
        ],
        call_account_path=runs_root / run_b / "s5b_real_calls.jsonl",
    )
    out_b = _start(tmp_path, run_b, model_b)
    assert out_b["stop_reason"] != "run_error"
    assert model_b.complete_calls == 2  # 首发 1 次 + 失败反馈 1 次,零补发
    notes_b = _model_notes(runs_root, run_b)
    assert notes_b[0]["transport_aborted_round"]["round"] == 1
    assert notes_b[0]["transport_aborted_round"]["stage"] == "feedback"
    assert _principal_products_in_submission_order(runs_root, run_b) == [
        NOVEL_OK, "CC=O"
    ]

    # ② 正控 B(C 臂合并轮首发传输失败):盲写段通过 blind-1,合并段 call_index=1 传输失败 ⇒ 回退保留 blind-1 + 池
    run_c = "p0-2-c-merge-abort"
    model_c = _TransportFailingStub(
        fail_at_call=1,
        strategy="responses",
        responses=[_response([_novel(NOVEL_OK, "blind-1")])],
        call_account_path=runs_root / run_c / "s5b_real_calls.jsonl",
    )
    out_c = _start_blind(tmp_path, run_c, model_c, rounds=1)
    assert out_c["stop_reason"] != "run_error"
    assert model_c.complete_calls == 2  # 盲写首发 1 次 + 合并首发失败 1 次,零补发
    notes_c = _model_notes(runs_root, run_c)
    assert notes_c[0]["transport_aborted_round"]["round"] == 0
    assert notes_c[0]["transport_aborted_round"]["stage"] == "merge_initial"
    assert _principal_products_in_submission_order(runs_root, run_c) == [
        NOVEL_OK, "CC=O"
    ]

    # ③ 正控 C(B 臂第 0 轮首发失败,但有本地候选池):回退到池条目,记 transport_aborted_round
    run_pool_only = "p0-2-b-r0-with-pool"
    model_pool = _TransportFailingStub(
        fail_at_call=0,
        strategy="responses",
        responses=[],
        call_account_path=runs_root / run_pool_only / "s5b_real_calls.jsonl",
    )
    out_pool = _start(tmp_path, run_pool_only, model_pool)
    assert out_pool["stop_reason"] != "run_error"
    assert model_pool.complete_calls == 1
    notes_pool = _model_notes(runs_root, run_pool_only)
    assert notes_pool[0]["transport_aborted_round"]["round"] == 0
    assert notes_pool[0]["transport_aborted_round"]["stage"] == "initial"
    assert _principal_products_in_submission_order(runs_root, run_pool_only) == [
        "CC=O"
    ]

    # ④ 负控(第 0 轮首发失败且空池无任何可用候选):必须走 run 级失败
    run_empty_fail = "p0-2-b-r0-empty-fail"
    model_empty = _TransportFailingStub(
        fail_at_call=0,
        strategy="responses",
        responses=[],
        call_account_path=runs_root / run_empty_fail / "s5b_real_calls.jsonl",
    )
    out_empty = _start(tmp_path, run_empty_fail, model_empty, pool={})
    assert out_empty["stop"]["run_error"]["kind"] == "real_model_transport_failure"


# ======================================================== B1 & B2 回修用例

def test_b1_a_arm_transport_failure_with_pool_fallback(tmp_path) -> None:
    """B1 正控:A 臂(atom_edit)首发请求传输失败且候选池非空时,
    与 B/C 同样按确定性池序排期,记 transport_aborted_round(stage=initial),零补发请求。"""
    runs_root = tmp_path / "runs"
    run_id = "b1-a-fallback-with-pool"
    model = _TransportFailingStub(
        fail_at_call=0,
        strategy="responses",
        responses=[],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start(tmp_path, run_id, model,
                 novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT)
    assert out["stop_reason"] != "run_error"
    assert model.complete_calls == 1  # 仅首发 1 次,零补发
    notes = _model_notes(runs_root, run_id)
    assert notes
    assert notes[0]["transport_aborted_round"] == {
        "round": 0,
        "stage": "initial",
        "request_id": notes[0]["request_id"],
        "error_kind": "timeout",
    }
    assert _principal_products_in_submission_order(runs_root, run_id) == ["CC=O"]


def test_b1_a_arm_transport_failure_empty_pool_fails(tmp_path) -> None:
    """B1 负控:A 臂首发请求传输失败且空池无任何候选时,必须走 run 级失败。"""
    runs_root = tmp_path / "runs"
    run_id = "b1-a-empty-pool-fails"
    model = _TransportFailingStub(
        fail_at_call=0,
        strategy="responses",
        responses=[],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start(tmp_path, run_id, model,
                 novel_protocol=NOVEL_PROTOCOL_ATOM_EDIT,
                 pool={})
    assert out["stop"]["run_error"]["kind"] == "real_model_transport_failure"


def test_b2_c_arm_width_12_no_pool_eviction(tmp_path) -> None:
    """B2(C 臂):统一备选上限至 12,8 条池条目 + 3 条盲写 full 条目时,
    池条目全部进入执行宽度、无一被挤出。"""
    runs_root = tmp_path / "runs"
    run_id = "b2-c-width12"

    pool_products = [
        "CC=O", "CCOC", "CCOCC", "CC(=O)O",
        "CC(C)O", "C=C", "CO", "CCOP(=O)(O)O"
    ]
    pool_entries_list = []
    for idx, prod in enumerate(pool_products):
        if prod == "CC=O":
            pool_entries_list.append(dict(POOL_SPEC))
        else:
            comp = compile_novel_product_first(
                SUBSTRATE_SMILES, prod, [], f"pool-prod-{idx}")
            assert comp["status"] == "compiled", (prod, comp)
            pool_entries_list.append({
                **dict(comp["spec"]),
                "key": f"rec-SYNTH_POOL_{idx}@{prod}",
                "transformation_ref": f"SYNTH_POOL_{idx}",
                "origin_group_key": f"rec-source:SYNTH_POOL_{idx}",
            })
    assert len(pool_entries_list) == 8
    eight_pools = {SUBSTRATE_SMILES: pool_entries_list}

    blind_products = ["CC(C)=O", "C1CO1", "O=CCO"]
    blind_proposals = [
        _novel(p, f"blind-{idx}") for idx, p in enumerate(blind_products, 1)
    ]

    model = _CountingStub(
        strategy="responses",
        responses=[
            _response(blind_proposals),
            '{"proposals": [], "rank_hypotheses": []}',
        ],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start_blind(
        tmp_path, run_id, model, rounds=1, pool=eight_pools)
    assert out["stop_reason"] != "run_error"

    submitted_prods = _principal_products_in_submission_order(runs_root, run_id)
    assert len(submitted_prods) == 11
    for p in pool_products:
        assert p in submitted_prods, f"池条目产物 {p} 不得被挤出执行宽度"
    for bp in blind_products:
        assert bp in submitted_prods, f"盲写产物 {bp} 应在执行宽度内"

    # 负控:人为锁在旧宽度 8(max_alternative_hypotheses_per_parent=8)⇒ 必有池条目被挤出
    run_id_old = "b2-c-width8-eviction"
    old_profile = _blind_profile(max_real=5, rounds=3, max_alt=8)
    model_old = _CountingStub(
        strategy="responses",
        responses=[
            _response(blind_proposals),
            '{"proposals": [], "rank_hypotheses": []}',
        ],
        call_account_path=runs_root / run_id_old / "s5b_real_calls.jsonl",
    )
    out_old = _start(
        tmp_path, run_id_old, model_old,
        novel_protocol=NOVEL_PROTOCOL_BLIND_FIRST,
        profile=old_profile,
        pool=eight_pools,
    )
    assert out_old["stop_reason"] != "run_error"
    old_submitted = _principal_products_in_submission_order(runs_root, run_id_old)
    assert len(old_submitted) == 8, "旧宽度 8 下最多容纳 8 条"
    evicted_pools = [p for p in pool_products if p not in old_submitted]
    assert len(evicted_pools) >= 1, "旧宽度 8 下必有池条目被挤出"


def test_p0_3_empty_pool_no_local_candidate_attaches_detail_model(
    tmp_path,
) -> None:
    """P0-3:空池且无 full novel 候选走 no_local_candidate 分支时,decide 账本挂 detail.model。"""
    runs_root = tmp_path / "runs"
    run_id = "p0-3-empty-pool"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel(NOVEL_BIG, "novel-decl")])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start(tmp_path, run_id, model, pool={})
    assert "no_local_candidate" in (out["stop"].get("other_reasons") or [])
    no_cand_models = []
    for path in sorted((runs_root / run_id / "results").glob(
            "*/expansion_outcome.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))["payload"]
        outcome = payload.get("outcome") or {}
        if str(outcome.get("kind")) == "no_local_candidate":
            no_cand_models.append(
                dict((outcome.get("detail") or {}).get("model") or {}))
    assert len(no_cand_models) == 1, "空池 no_local_candidate 必须挂 detail.model"
    assert no_cand_models[0]["novel_protocol"] == NOVEL_PROTOCOL_PRODUCT_FIRST
    assert len(no_cand_models[0]["declared_bucket"]) == 1
    assert (
        no_cand_models[0]["declared_bucket"][0]["bucket_kind"]
        == BUCKET_KIND_DECLARED_UNRECOGNIZED
    )


def test_p1_1_compile_gate_undeclared_leaving_group_and_co2_formate(
    tmp_path,
) -> None:
    """P1-1:编译门放行未声明的底物断键脱落碎片,白名单内进 full 并标 coproduct_undeclared;
    脱羧双形态(O=C=O / O=CO)等价判定且保留执行器实际形态;超白名单进声明桶。"""
    from pathway_v43.pollutant.hypothesis import (
        PARTICIPANT_ROLE_COPRODUCT_UNDECLARED,
        PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
        PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    )

    # ① 正控:苯甲酸(O=C(O)c1ccccc1)→ 苯(c1ccccc1),模型未声明脱羧副产物
    #    执行器实际产出甲酸形态 O=CO(与 O=C=O 共享 CO2_or_formate 白名单行)
    decarb = compile_novel_product_first(
        "O=C(O)c1ccccc1", "c1ccccc1", [], "p1-1-decarb")
    assert decarb["status"] == "compiled"
    assert decarb["verification_tier"] == VERIFICATION_TIER_FULL
    assert decarb["bucket_kind"] == BUCKET_KIND_FULL
    assert decarb["spec"]["coproducts"] == []
    assert decarb["spec"]["undeclared_coproducts"] == ["O=CO"]

    # 生产事件里未声明脱落碎片角色标 coproduct_undeclared,且保持执行器实际形态 O=CO
    runs_root = tmp_path / "runs"
    run_id = "p1-1-decarb-run"
    model = _CountingStub(
        strategy="responses",
        responses=[_response([_novel("c1ccccc1", "novel-decarb")])],
        call_account_path=runs_root / run_id / "s5b_real_calls.jsonl",
    )
    out = _start(tmp_path, run_id, model, smiles="O=C(O)c1ccccc1", pool={})
    assert out["stop_reason"] != "run_error"
    conn = _db(runs_root, run_id)
    try:
        states = {
            row[0]: json.loads(row[1]).get("smiles_isomeric")
            for row in conn.execute("SELECT state_id, payload FROM states")
        }
        event_rows = conn.execute("SELECT payload FROM events").fetchall()
        assert len(event_rows) == 1
        participants = json.loads(event_rows[0][0])["participants"]
        role_by_smiles = {
            states[p["state_ref"]]: p["role"] for p in participants
        }
    finally:
        conn.close()
    assert role_by_smiles["O=C(O)c1ccccc1"] == PARTICIPANT_ROLE_PRIMARY_SUBSTRATE
    assert role_by_smiles["c1ccccc1"] == PARTICIPANT_ROLE_PRINCIPAL_PRODUCT
    assert role_by_smiles["O=CO"] == PARTICIPANT_ROLE_COPRODUCT_UNDECLARED

    # ② 正控:羧酸根底物([O-]C(=O)c1ccccc1)模型显式写 coproducts=["O=C=O"]
    #    (与执行器实际断键产出的甲酸根 O=C[O-] 互为 CO2_or_formate 双形态)
    #    编译门按双形态等价放行,且 spec["coproducts"] 保留执行器实际形态 O=C[O-](不改写成模型写的 O=C=O);
    #    中性底物已可复现编译为 O=C=O 的正控保持原字节不变
    decarb_co2 = compile_novel_product_first(
        "[O-]C(=O)c1ccccc1", "c1ccccc1", ["O=C=O"], "p1-1-decarb-co2")
    assert decarb_co2["status"] == "compiled"
    assert decarb_co2["verification_tier"] == VERIFICATION_TIER_FULL
    assert decarb_co2["spec"]["coproducts"] == ["O=C[O-]"]
    assert decarb_co2["spec"].get("undeclared_coproducts", []) == []

    decarb_co2_neutral = compile_novel_product_first(
        "O=C(O)c1ccccc1", "c1ccccc1", ["O=C=O"], "p1-1-decarb-co2-neutral")
    assert decarb_co2_neutral["status"] == "compiled"
    assert decarb_co2_neutral["verification_tier"] == VERIFICATION_TIER_FULL
    assert decarb_co2_neutral["spec"]["coproducts"] == ["O=C=O"]

    # ③ 负控:超白名单未声明脱落碎片(丙酯水解未声明丙醇)⇒ 进声明桶 declared_unrecognized
    out_wl = compile_novel_product_first(
        "CC(=O)OCCC", "CC(=O)O", [], "p1-1-out-wl")
    assert out_wl["status"] == "compiled"
    assert out_wl["verification_tier"] == VERIFICATION_TIER_DECLARED
    assert out_wl["bucket_kind"] == BUCKET_KIND_DECLARED_UNRECOGNIZED
    assert "removed_part_not_accounted" in out_wl["bucket_reasons"]


def test_p1_2_ambiguous_mapping_disambiguation_by_principal_product() -> None:
    """P1-2:多映射时仅当所有候选映射的主产物严格身份相同且等于声明产物才消歧;
    主产物不同仍判 ambiguous_mapping。"""
    from pathway_v43.pollutant.recorded_source import compile_recorded_reaction

    # ① 正控:多候选映射产生不同脱落组分集合(COC(=O)CC(=O)O → CC(=O)O),
    #    但所有候选映射的主产物严格身份均等于声明主产物 CC(=O)O ⇒ 消歧通过
    sym_ok = compile_novel_product_first(
        "COC(=O)CC(=O)O", "CC(=O)O", [], "p1-2-sym-ok")
    assert sym_ok["status"] == "compiled"

    # ② 负控:两个候选映射分别产出 octan-3-one 与 octan-2-one 两种不同主产物
    #    ⇒ 主产物不同,仍判 ambiguous_mapping
    asym_sub = "CCC(=O)CCCC(C)O"
    donor_sub = "CC(=O)CCCC(C)O"
    donor_prod = "CCCCCC(C)=O"
    res_asym = compile_recorded_reaction(
        substrate_smiles=asym_sub,
        donor_smiles=donor_sub,
        products=[donor_prod],
        record_id="test:p1-2-asym",
        novel_product_first_principal=donor_prod,
    )
    assert res_asym["status"] == "unsupported"
    assert res_asym["reason"] == "ambiguous_mapping"
    assert res_asym["detail"]["competing_targets"] == [
        "CCCCCC(=O)CC.O", "CCCCCCC(C)=O.O"
    ]


def test_p2_1a_self_donor_full_skeleton_avoids_false_ambiguous_alignment() -> None:
    """P2-1a:自供体(donor_smiles == substrate_smiles)编译保留供体全量重原子与键,
    消除两壳层截断把远端(L3)不对称基团误认成对称位点的伪 ambiguous_alignment。"""
    # 合成不对称二醇:两端 C(O)CC 局部两壳层完全相同,但左端连 Cl(距离反应中心 >2 键)
    sub = "OCCCCC(O)CCCl"
    prod = "O=CCCCC(O)CCCl"
    out = compile_novel_product_first(sub, prod, [], "p2-1a-asym-diol")
    assert out["status"] == "compiled"
    assert out["verification_tier"] == VERIFICATION_TIER_FULL
    assert out["bucket_kind"] == BUCKET_KIND_FULL
    assert out["compiled_principal"] == "O=CCCCC(O)CCCl"


def test_p2_1b_infer_bond_diff_fallback_min_k_no_truncation() -> None:
    """P2-1b:_infer_bond_diff_fallback 按键差阶次 k=1..2 分层且命中最小键差即停,
    并消除多对称芳香环水解裂解时 k=2 组合叠加引起的伪 mapping_enumeration_truncated。"""
    # 合成含对称双苯环的酯水解(n_union = n_donor + 1):k=1 单键断裂唯一可解,
    # 旧版因 continue no-op 滑入全部 C(|E|,2) 双键组合触 800 上限截断
    sub = "O=C(Oc1ccccc1)C(Cc1ccccc1)Cc1ccccc1"
    prod = "O=C(O)C(Cc1ccccc1)Cc1ccccc1"
    cop = "Oc1ccccc1"
    out = compile_novel_product_first(sub, prod, [cop], "p2-1b-hydrolysis")
    assert out["status"] == "compiled"
    assert out["verification_tier"] == VERIFICATION_TIER_FULL
    assert out["bucket_kind"] == BUCKET_KIND_FULL


def test_p2_2_fallback_edits_hybrid_compilation() -> None:
    """P2-2:确定性反推不可达(如多键开环水合)时,若提供合法 fallback_edits,
    经 render + validate_edits + execute_edits 与 P1-1/七条件同尺核验后可编译入桶;
    坏 edits 或产物不匹配仍被 fail-closed 拒绝。"""
    from pathway_v43.pollutant.novel_product_first import (
        FAILURE_NO_STRUCTURE_CORRESPONDENCE,
    )

    # 合成三键开环水合:四面体烷 C12C3C1C23 开三根 C-C 键并水合为正丁醇 CCCCO
    # (n_union=5 > n_donor=4 且需断 3 键 > _INFER_BOND_DIFF_LIMIT=2,
    # 确定性子结构同构返 no_structure_correspondence)
    sub = "C12C3C1C23"
    prod = "CCCCO"
    no_fb = compile_novel_product_first(sub, prod, [], "p2-2-no-fb")
    assert no_fb["status"] == "failed"
    assert no_fb["failure_kind"] == FAILURE_NO_STRUCTURE_CORRESPONDENCE

    valid_edits = [
        {"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_3"},
        {"op": "break_bond", "atom1": "S_C_1", "atom2": "S_C_4"},
        {"op": "break_bond", "atom1": "S_C_2", "atom2": "S_C_4"},
        {
            "op": "add_atom",
            "atom1": "S_C_1",
            "element": "O",
            "new_atom_id": "N_O_1",
        },
    ]
    with_fb = compile_novel_product_first(
        sub, prod, [], "p2-2-with-fb", fallback_edits=valid_edits
    )
    assert with_fb["status"] == "compiled"
    assert with_fb["verification_tier"] == VERIFICATION_TIER_FULL
    assert with_fb["bucket_kind"] == BUCKET_KIND_FULL
    assert (
        with_fb["diagnostics"]["compile_diagnostics"]["fallback_edits_used"]
        is True
    )

    # 负控:fallback_edits 执行产物与声明产物不符 ⇒ 保持原失败类别拒收
    wrong_fb = compile_novel_product_first(
        sub, "CCCCCO", [], "p2-2-wrong-fb", fallback_edits=valid_edits
    )
    assert wrong_fb["status"] == "failed"
    assert wrong_fb["failure_kind"] == FAILURE_NO_STRUCTURE_CORRESPONDENCE




