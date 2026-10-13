"""F3 受控词表 CI 双向断言(老师提效包 F3;57ea99b4 aromatic 事故防再犯)。

背景(57ea99b4,2026-10-09):S5b 应急提示词手写键级词表
"single|double|triple|aromatic",执行器 ``_BOND_TOKENS`` 只认凯库勒
三词;模型按提示词规范输出 ``to_order=aromatic``,执行器 KeyError
整题崩溃(chenyu 冒烟 2/10 题)。根因 = 提示词词表与执行器词表两处
手写、无同步机制。本测试族 = 防再犯的 CI 侧;单一来源侧见
``src/pathway_v43/pollutant/controlled_vocab.py``。

断言族(任务书 F3 a-d 全量落地):

- **T1 哈希稳定(设计红线)**:提示词改为 controlled_vocab 拼接生成后,
  渲染字节须与基线 8da11cb7 手写版逐字节一致
  (PROPOSALS_PROMPT_VERSION = 基线冻结 sha256)——批身份/resume
  语义零影响;此后词表演进 ⇒ 哈希自动升版走既有流程,不静默漂移;
- **T2-T8 提示词 ↔ 执行器双向同步(检测器,即 aromatic 事故的直接
  防再犯面)**:
  T2 正向:``"op"`` 声明 ⊆ EDIT_OPS(声明位教执行器不认的词 ⇒ 红);
  T3 正向:编辑协议 v2 废除词(remove_atom/remove_bond/add_bond)与
  图事实词 aromatic 在提示词任何形式零出现;
  T4 双向:from_order/to_order 枚举声明 == 凯库勒三词集合(加词/
  删词 ⇒ 红;aromatic 事故位);实例值(Example 段)⊆ 词表;
  T5 双向:output_origin 声明 == OUTPUT_ORIGINS;
  T6 正向:alignment status 示范 ⊆ ALIGNMENT_STATUSES;ambiguous/
  unavailable 不入提示词(审计判定值,豁免登记);
  T7 反向:op 词表四成员全部在提示词声明位可达(删声明 ⇒ 红);
  T8 内部词表(状态/展开/deferred/provider/侧别/角色/生产报告)
  零入提示词(带引号 JSON 值形式零出现——提示词不教模型内部词);
- **T9 权威同源**:controlled_vocab 各族集合 == 权威模块常量集合
  (集合化零抄漏;BOND_ORDER_TOKENS 保序快照钉死渲染序);
- **T10 孪生映射一致**:atom_tool._BOND_ORDER_N / s5b_compiler
  _ORDER_OF_TOKEN / _ORDER_NAME / _BOND_TOKENS 键值域双向一致
  (执行器间词表不同步 ⇒ 红);
- **T11 字面量消费点登记(ast 源码扫描;任务 d"覆盖各消费方首消费
  点"的落地)**:
  发现集(消费方源码中精确等于受控词的字符串常量,剥 docstring,
  含 dict 键/JoinedStr 静态段)⊆ 登记集 —— 新写受控字面量必须登记,
  防"悄悄绕过常量纪律";登记词 ∈ 当前词表并集 —— 权威改值 ⇒ 旧
  字面量过期 ⇒ 红(字面量过期检测)。删字面量不破(演进自由)。
  能力边界(如实登记):断言基于词值不基于位置语义,同词异义的巧合
  覆盖(如 model_requests 状态 "failed" 恰与 ATTEMPT_STATUS_FAILED
  同词)属保守面;"该比较位本应用哪个族"的位置语义由既有行为测试
  族承载,不在本面;
- **T12 execution_graph 运行时词域**:图键级事实词 ⊆ 凯库勒三词 ∪
  {aromatic}(只读图描述),苯(芳香)与乙醇(脂肪)实盘锚定;
- **D1-D7 漂移注入(任务 c;对提示词副本注入,检测器必须红)**:
  D1 键级枚举混入 aromatic(复现 57ea99b4 前形态);
  D2 键级枚举删 triple;D3 add_atom 声明位换 remove_atom(协议 v2
  废除词);D4 break_bond 全词换 remove_bond;D5 output_origin 换
  非法值;D6 alignment status 换非法值;D7 add_atom 全词换不可达词
  (执行器词在提示词失可达)。

环境纪律:零网络零模型零花费;只读源码与常量,不改任何被测文件。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant import controlled_vocab as cv  # noqa: E402
from pathway_v43.pollutant.controlled_vocab import (  # noqa: E402
    ALIGNMENT_STATUSES,
    BOND_ORDER_TOKENS,
    EDIT_OPS,
    GRAPH_ORDER_AROMATIC,
    INTERNAL_ONLY_VOCABS,
    OUTPUT_ORIGINS,
    RETIRED_EDIT_OPS,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    _PROPOSALS_SYSTEM_PROMPT,
    execution_graph_payload,
)

PROMPT = _PROPOSALS_SYSTEM_PROMPT

# ---------------------------------------------------------------- 检测器

_OP_DECL_RE = re.compile(r'"op":\s*"([^"]+)"')
_ORDER_DECL_RE = re.compile(r'"(?:from_order|to_order)":\s*"([^"]+)"')
_OUTPUT_ORIGIN_RE = re.compile(r'"output_origin":\s*"([^"]+)"')
_STATUS_DECL_RE = re.compile(r'"status":\s*"([^"]+)"')


def _assert_prompt_vocab_sync(prompt: str) -> None:
    """提示词 ↔ 执行器受控词表双向同步断言(核心防再犯检测器)。

    对任意提示词文本执行;主断言测试对真实提示词调用(须全绿),
    漂移注入测试对注入副本调用(须红)—— 检测器对 57ea99b4 事故
    形态(键级枚举混入 aromatic)与全部 D1-D7 注入形态必须能红。
    """
    legal_ops = set(EDIT_OPS)
    legal_orders = set(BOND_ORDER_TOKENS)
    # T2 正向:op 声明 ⊆ 执行器四操作(声明位教坏词 ⇒ 红)
    ops = set(_OP_DECL_RE.findall(prompt))
    assert ops <= legal_ops, (
        f"提示词声明了执行器不认的 op(57ea99b4 事故同型):"
        f"{sorted(ops - legal_ops)}")
    # T7 反向:四操作全声明(删操作声明 ⇒ 提示词词表不全 ⇒ 红)
    assert ops == legal_ops, (
        f"提示词 op 声明不全(执行器词表漂移):"
        f"缺 {sorted(legal_ops - ops)}")
    # T4 双向:键级枚举声明 == 凯库勒三词(加词/删词 ⇒ 红)
    order_values = _ORDER_DECL_RE.findall(prompt)
    enum_words: set[str] = set()
    for value in order_values:
        if "|" in value:
            enum_words |= set(value.split("|"))
    assert enum_words == legal_orders, (
        f"提示词键级枚举声明 != 执行器凯库勒词表:声明 {sorted(enum_words)}"
        f" vs 执行器 {sorted(legal_orders)}(多 {sorted(enum_words - legal_orders)}"
        f" / 少 {sorted(legal_orders - enum_words)})")
    instance_orders = {v for v in order_values if "|" not in v}
    assert instance_orders <= legal_orders, (
        f"提示词键级实例值越界:{sorted(instance_orders - legal_orders)}")
    # T5 双向:output_origin 声明 == 词表
    origins = set(_OUTPUT_ORIGIN_RE.findall(prompt))
    assert origins == set(OUTPUT_ORIGINS), (
        f"提示词 output_origin 声明 {sorted(origins)} != "
        f"受控词表 {sorted(OUTPUT_ORIGINS)}")
    # T6 正向:alignment status 示范 ⊆ 审计词表
    statuses = set(_STATUS_DECL_RE.findall(prompt))
    assert statuses <= set(ALIGNMENT_STATUSES), (
        f"提示词 alignment status 示范 {sorted(statuses)} 越界"
        f"(合法 {sorted(ALIGNMENT_STATUSES)})")
    # T3 正向:协议 v2 废除词与图事实词 aromatic 在提示词零出现
    # (任何形式;aromatic 是 execution_graph 只读图事实词,混入
    # edits 可编辑词面即 57ea99b4 根因)
    for word in RETIRED_EDIT_OPS:
        assert word not in prompt, (
            f"编辑协议 v2 废除词 {word!r} 出现在提示词(执行器 v2 面"
            f"一律 unknown_op 拒,提示词不得教学)")
    assert GRAPH_ORDER_AROMATIC not in prompt, (
        "图事实词 'aromatic' 出现在提示词 —— 它是 execution_graph 的"
        "只读键级描述词,不是可编辑键级词(57ea99b4 根因即两面混写)")
    # T8 内部词表零入提示词(带引号 JSON 值形式;纯文本叙述中的
    # 普通英文单词不触发)
    for family, words in INTERNAL_ONLY_VOCABS.items():
        for word in words:
            assert f'"{word}"' not in prompt, (
                f"内部词表 {family} 的词 {word!r} 以声明值形式出现在"
                f"提示词(提示词不教模型内部状态/载荷词)")


# ---------------------------------------------------------------- T1 哈希

# 基线 8da11cb7(手写提示词版)的 sha256 —— 单一来源拼接改造后渲染
# 字节必须逐字节不变(设计红线:PROPOSALS_PROMPT_VERSION 是内容哈希,
# 升版 = 批身份变化;本改造不升版)。此后任何词表演进改变拼接结果 ⇒
# 本断言红 ⇒ 显式决定升版,不静默漂移。
BASELINE_PROMPT_SHA256_8DA11CB7 = (
    "e28b5342b0036a6af0893ca310045bed9d0e9d8bfc85f3d21c880e9a7917b962")
BASELINE_PROMPT_BYTES = 4360


def test_t1_prompt_hash_stable_to_baseline() -> None:
    """单一来源拼接改造不升版:提示词字节与基线 8da11cb7 一致。"""
    assert PROPOSALS_PROMPT_VERSION == BASELINE_PROMPT_SHA256_8DA11CB7, (
        "提示词内容哈希漂移:单一来源拼接的渲染字节与基线 8da11cb7 "
        "不一致 —— 若为有意的词表演进,须显式升 PROPOSALS_PROMPT_"
        "VERSION 并重跑批身份影响评估,不得静默漂移")
    assert len(PROMPT.encode("utf-8")) == BASELINE_PROMPT_BYTES


# ------------------------------------------------- T2-T8 提示词双向同步

def test_t2_to_t8_prompt_vocab_synced() -> None:
    """真实提示词过全检测器(op/order/origin/status/内部词表)。"""
    _assert_prompt_vocab_sync(PROMPT)


def test_t4_order_alternation_is_generated_not_handwritten() -> None:
    """键级枚举声明值 = 单一来源生成串(拼接证据,防手写回潮)。"""
    assert cv.BOND_ORDER_ALTERNATION == "single|double|triple"
    assert PROMPT.count(f'"from_order": "{cv.BOND_ORDER_ALTERNATION}"') == 1
    assert PROMPT.count(f'"to_order": "{cv.BOND_ORDER_ALTERNATION}"') == 1


def test_t6_alignment_exemptions_registered() -> None:
    """alignment 词表 ambiguous/unavailable 不入提示词(豁免登记)。

    resolved 是提示词示范值(模型侧 alignment 契约);ambiguous/
    unavailable 是审计判定值,只在审计/编译侧消费 —— 豁免 = 如实
    登记"仅内部使用不入提示词",CI 保证它们不在提示词出现。
    """
    for word in ("ambiguous", "unavailable"):
        assert word in ALIGNMENT_STATUSES
        assert f'"{word}"' not in PROMPT


# ---------------------------------------------------------------- T9 同源

def test_t9_vocab_families_match_authority_modules() -> None:
    """controlled_vocab 各族集合 == 权威模块常量(集合化零抄漏)。"""
    from pathway_v43.pollutant.events import EXPANSION_STATUSES
    from pathway_v43.pollutant.hypothesis import (
        PARTICIPANT_ROLES,
        PARTICIPANT_SIDES,
    )
    from pathway_v43.pollutant.queue import DEFERRED_TYPES
    from pathway_v43.pollutant.search import (
        PROVIDER_KINDS,
    )
    from pathway_v43.services.atom_tool import _BOND_ORDER_N, _BOND_TOKENS

    # 编辑协议族(执行器权威)
    assert tuple(EDIT_OPS) == ("break_bond", "form_bond",
                               "change_bond_order", "add_atom")
    assert BOND_ORDER_TOKENS == ("single", "double", "triple")  # 保序
    assert set(_BOND_TOKENS) == set(BOND_ORDER_TOKENS)
    assert set(_BOND_ORDER_N) == set(BOND_ORDER_TOKENS)
    assert set(_BOND_ORDER_N.values()) == {1, 2, 3}
    assert cv.EDIT_OP_FIELDS == {
        "break_bond": frozenset({"op", "atom1", "atom2"}),
        "form_bond": frozenset({"op", "atom1", "atom2"}),
        "change_bond_order": frozenset(
            {"op", "atom1", "atom2", "from_order", "to_order"}),
        "add_atom": frozenset(
            {"op", "atom1", "element", "new_atom_id"}),
    }
    # 状态机族(search 权威)
    assert cv.ACTION_STATUSES == frozenset(
        {"pending", "claimed", "done", "deferred", "blocked"})
    assert cv.ATTEMPT_STATUSES == frozenset(
        {"open", "recorded", "failed", "abandoned"})
    assert cv.ACTION_STATUSES | cv.ATTEMPT_STATUSES == set(
        _ACTION_WORDS_FROM_SEARCH())
    # 展开计划族(events 权威)
    assert cv.EXPANSION_STATUSES == EXPANSION_STATUSES == frozenset(
        {"expanded", "deferred", "not_tracked"})
    assert cv.PLAN_STATUS_INCOMPLETE == "incomplete"
    # deferred 两类(queue 权威)
    assert cv.DEFERRED_TYPES == DEFERRED_TYPES == frozenset(
        {"coproduct_deferred", "alternative_reaction_deferred"})
    # provider 族(search 权威)
    assert cv.PROVIDER_KINDS == PROVIDER_KINDS == frozenset(
        {"real", "scripted", "fake"})
    # 侧别/角色族(hypothesis 权威)
    assert cv.PARTICIPANT_SIDES == PARTICIPANT_SIDES == frozenset(
        {"reactant", "product"})
    assert cv.PARTICIPANT_ROLES == PARTICIPANT_ROLES == frozenset(
        {"primary_substrate", "cosubstrate", "principal_product",
         "coproduct", "unknown"})
    # output_origin / alignment / 生产报告族(首次常量化,值域钉死)
    assert cv.OUTPUT_ORIGINS == frozenset({"novel_outside_pool"})
    assert cv.ALIGNMENT_STATUSES == frozenset(
        {"resolved", "ambiguous", "unavailable"})
    assert cv.PRODUCTION_REPORT_STATUSES == frozenset(
        {"method_failed", "deferred", "rejected", "submitted"})
    # 基础属性健全性
    for family in (cv.ACTION_STATUSES, cv.ATTEMPT_STATUSES,
                   cv.EXPANSION_STATUSES, cv.DEFERRED_TYPES,
                   cv.PROVIDER_KINDS, cv.PARTICIPANT_SIDES,
                   cv.PARTICIPANT_ROLES, cv.OUTPUT_ORIGINS,
                   cv.ALIGNMENT_STATUSES, cv.PRODUCTION_REPORT_STATUSES):
        assert isinstance(family, frozenset) and family


def _ACTION_WORDS_FROM_SEARCH() -> set[str]:
    """从 search 权威常量直接组装(与 controlled_vocab 集合化对照)。"""
    from pathway_v43.pollutant.search import (
        ACTION_STATUS_BLOCKED,
        ACTION_STATUS_CLAIMED,
        ACTION_STATUS_DEFERRED,
        ACTION_STATUS_DONE,
        ACTION_STATUS_PENDING,
        ATTEMPT_STATUS_ABANDONED,
        ATTEMPT_STATUS_FAILED,
        ATTEMPT_STATUS_OPEN,
        ATTEMPT_STATUS_RECORDED,
    )

    return {ACTION_STATUS_PENDING, ACTION_STATUS_CLAIMED, ACTION_STATUS_DONE,
            ACTION_STATUS_DEFERRED, ACTION_STATUS_BLOCKED,
            ATTEMPT_STATUS_OPEN, ATTEMPT_STATUS_RECORDED,
            ATTEMPT_STATUS_FAILED, ATTEMPT_STATUS_ABANDONED}


# ---------------------------------------------------------------- T10 孪生

def test_t10_twin_bond_order_mappings_consistent() -> None:
    """执行器间键级孪生映射双向一致(atom_tool/s5b_compiler)。"""
    from rdkit import Chem

    from pathway_v43.pollutant.s5b_compiler import (
        _ORDER_NAME,
        _ORDER_OF_TOKEN,
    )
    from pathway_v43.services.atom_tool import _BOND_TOKENS, _BOND_ORDER_N

    # s5b_compiler 的 token→BondType 映射与执行器 _BOND_TOKENS 同构
    # (键值完全相等;编译侧加/改键级词 ⇒ 不同步红)
    assert _ORDER_OF_TOKEN == _BOND_TOKENS
    # 执行器序数表键域 == 键级词表
    assert set(_BOND_ORDER_N) == set(_BOND_TOKENS)
    assert set(_BOND_ORDER_N.values()) == {1, 2, 3}
    # BondType→token 反向映射:凯库勒三词 + aromatic(编译侧芳香比较
    # 的图事实条目;值域不得越出凯库勒词表 ∪ {aromatic})
    assert set(_ORDER_NAME) == {
        Chem.BondType.SINGLE, Chem.BondType.DOUBLE, Chem.BondType.TRIPLE,
        Chem.BondType.AROMATIC}
    assert set(_ORDER_NAME.values()) <= set(_BOND_TOKENS) | {
        GRAPH_ORDER_AROMATIC}
    # _ORDER_NAME 的三词条目与 _BOND_TOKENS 反向一致
    for token, bond_type in _BOND_TOKENS.items():
        assert _ORDER_NAME[bond_type] == token


def test_t12_execution_graph_order_tokens_in_fact_vocab() -> None:
    """execution_graph 键级事实词 ⊆ 凯库勒三词 ∪ {aromatic}(运行时)。

    苯(芳香底物,Kekulize 成功 ⇒ 凯库勒 single/double)与乙醇(全
    single)实盘锚定;图键级词是只读事实描述,永不越出图事实词域。
    """
    graph_aromatic = execution_graph_payload("c1ccccc1")
    orders_aromatic = {b["order"] for b in graph_aromatic["bonds"]}
    assert orders_aromatic <= cv.GRAPH_ORDER_FACT_TOKENS
    assert orders_aromatic == {"single", "double"}  # 凯库勒化后
    graph_aliphatic = execution_graph_payload("CCO")
    orders_aliphatic = {b["order"] for b in graph_aliphatic["bonds"]}
    assert orders_aliphatic == {"single"}
    assert cv.GRAPH_ORDER_FACT_TOKENS == (
        frozenset(BOND_ORDER_TOKENS) | {GRAPH_ORDER_AROMATIC})


# ------------------------------------------------- T11 字面量消费点登记

# 受控词字面量登记集((文件名, 词) 基线快照,2026-10-11 于 8da11cb7
# +F3 改动后由 ast 扫描生成,人工核对后冻结)。语义见文件头 T11。
# 维护规则:
# - 消费方新写受控词字面量 ⇒ 发现集新增 ⇒ 发现 ⊆ 登记破 ⇒ 红 ⇒
#   显式登记(或改走 controlled_vocab 常量引用);
# - 权威词表改值/删词 ⇒ 登记词 ∉ 当前并集 ⇒ 红 ⇒ 同步字面量;
# - 删除字面量不破(演进自由,登记残留无害)。
REGISTERED_LITERAL_SINKS: frozenset[tuple[str, str]] = frozenset({
    # atom_tool.py(执行器权威定义面 + v2 拒因路径)
    ("atom_tool.py", "add_atom"), ("atom_tool.py", "add_bond"),
    ("atom_tool.py", "aromatic"), ("atom_tool.py", "break_bond"),
    ("atom_tool.py", "change_bond_order"), ("atom_tool.py", "double"),
    ("atom_tool.py", "form_bond"), ("atom_tool.py", "remove_bond"),
    ("atom_tool.py", "single"), ("atom_tool.py", "triple"),
    # audit.py(对齐状态校验 + 编辑词消费)
    ("audit.py", "add_atom"), ("audit.py", "ambiguous"),
    ("audit.py", "break_bond"), ("audit.py", "change_bond_order"),
    ("audit.py", "double"), ("audit.py", "form_bond"),
    ("audit.py", "product"), ("audit.py", "reactant"),
    ("audit.py", "resolved"), ("audit.py", "single"),
    ("audit.py", "triple"), ("audit.py", "unavailable"),
    ("audit.py", "unknown"),
    ("chemstate.py", "unknown"),
    ("endpoint.py", "failed"), ("endpoint.py", "incomplete"),
    ("endpoint.py", "product"), ("endpoint.py", "unknown"),
    ("evaluation.py", "coproduct"), ("evaluation.py", "failed"),
    # ppv1-criteria-v2(2026-10-13):声明链状态字面量
    # _CRITERIA_V2_DECL_RESOLVED = "resolved"(与对齐状态词表同词形、
    # 不同语义域;按 T11 维护规则显式登记)
    ("evaluation.py", "pending"), ("evaluation.py", "product"),
    ("evaluation.py", "reactant"), ("evaluation.py", "real"),
    ("evaluation.py", "resolved"), ("evaluation.py", "scripted"),
    ("evaluation.py", "submitted"), ("evaluation.py", "unknown"),
    ("events.py", "deferred"), ("events.py", "expanded"),
    ("events.py", "not_tracked"), ("events.py", "unknown"),
    ("hypothesis.py", "coproduct"), ("hypothesis.py", "cosubstrate"),
    ("hypothesis.py", "primary_substrate"),
    ("hypothesis.py", "principal_product"), ("hypothesis.py", "product"),
    ("hypothesis.py", "reactant"), ("hypothesis.py", "unknown"),
    ("legacy_reader.py", "unknown"),
    ("native_export.py", "recorded"),
    ("native_result.py", "blocked"), ("native_result.py", "coproduct"),
    ("native_result.py", "deferred"),
    ("path_context.py", "recorded"), ("path_context.py", "unknown"),
    ("pool_audit.py", "unknown"),
    # T1a(2026-10-12,s5b-pool-policy-6):pool_diagnostics.candidates
    # 行的 channel 字段自变量("recorded";corpus/analog 非受控词)
    ("s5b_builder.py", "recorded"),
    ("production.py", "coproduct"), ("production.py", "cosubstrate"),
    ("production.py", "deferred"), ("production.py", "method_failed"),
    ("production.py", "primary_substrate"),
    ("production.py", "principal_product"), ("production.py", "product"),
    ("production.py", "reactant"), ("production.py", "rejected"),
    ("production.py", "submitted"), ("production.py", "unknown"),
    ("provenance.py", "recorded"), ("provenance.py", "unknown"),
    ("queue.py", "alternative_reaction_deferred"),
    ("queue.py", "blocked"), ("queue.py", "claimed"),
    ("queue.py", "coproduct_deferred"), ("queue.py", "deferred"),
    ("queue.py", "expanded"), ("queue.py", "method_failed"),
    ("queue.py", "not_tracked"), ("queue.py", "unknown"),
    # real_model.py(execution_graph 内联键级映射 + 适配器标识词)
    ("real_model.py", "aromatic"), ("real_model.py", "double"),
    ("real_model.py", "failed"), ("real_model.py", "fake"),
    ("real_model.py", "single"), ("real_model.py", "triple"),
    ("real_model.py", "unknown"),
    ("recorded_source.py", "add_atom"), ("recorded_source.py", "coproduct"),
    ("recorded_source.py", "cosubstrate"),
    ("recorded_source.py", "primary_substrate"),
    ("recorded_source.py", "principal_product"),
    ("recorded_source.py", "product"), ("recorded_source.py", "reactant"),
    ("recorded_source.py", "unknown"),
    ("reference_graph.py", "coproduct"),
    ("reference_graph.py", "principal_product"),
    ("reference_graph.py", "unknown"),
    ("runflow.py", "blocked"), ("runflow.py", "claimed"),
    ("runflow.py", "deferred"), ("runflow.py", "done"),
    ("runflow.py", "method_failed"),
    ("runflow.py", "novel_outside_pool"), ("runflow.py", "pending"),
    ("runflow.py", "product"), ("runflow.py", "rejected"),
    ("runflow.py", "unknown"),
    ("s5b_builder.py", "principal_product"), ("s5b_builder.py", "product"),
    ("s5b_builder.py", "reactant"), ("s5b_builder.py", "real"),
    ("s5b_builder.py", "unknown"),
    ("s5b_cli.py", "real"), ("s5b_cli.py", "scripted"),
    ("s5b_compiler.py", "add_atom"), ("s5b_compiler.py", "aromatic"),
    ("s5b_compiler.py", "break_bond"),
    ("s5b_compiler.py", "change_bond_order"),
    ("s5b_compiler.py", "double"), ("s5b_compiler.py", "form_bond"),
    ("s5b_compiler.py", "resolved"), ("s5b_compiler.py", "single"),
    ("s5b_compiler.py", "triple"),
    ("s5b_orchestrator.py", "failed"),
    ("s5b_orchestrator.py", "pending"),
    ("s5b_orchestrator.py", "real"),
    ("s5b_orchestrator.py", "unknown"),
    ("s5b_scoring.py", "reactant"), ("s5b_scoring.py", "real"),
    ("s5b_scoring.py", "unknown"),
    ("s5b_worker.py", "failed"), ("s5b_worker.py", "real"),
    ("search.py", "abandoned"), ("search.py", "blocked"),
    ("search.py", "claimed"), ("search.py", "deferred"),
    ("search.py", "done"), ("search.py", "failed"),
    ("search.py", "fake"), ("search.py", "open"),
    ("search.py", "pending"), ("search.py", "real"),
    ("search.py", "recorded"), ("search.py", "scripted"),
    ("search.py", "submitted"), ("search.py", "unknown"),
    ("store.py", "incomplete"), ("store.py", "primary_substrate"),
    ("store.py", "product"), ("store.py", "reactant"),
    ("store.py", "submitted"),
    ("substrate_profile.py", "unknown"),
    ("v3_projection.py", "product"), ("v3_projection.py", "reactant"),
    ("v3_projection.py", "recorded"),
})

_VOCAB_UNION: set[str] = (
    set(EDIT_OPS) | set(RETIRED_EDIT_OPS) | set(BOND_ORDER_TOKENS)
    | {GRAPH_ORDER_AROMATIC} | cv.ACTION_STATUSES | cv.ATTEMPT_STATUSES
    | cv.EXPANSION_STATUSES | {cv.PLAN_STATUS_INCOMPLETE}
    | cv.DEFERRED_TYPES | cv.PROVIDER_KINDS | cv.PARTICIPANT_SIDES
    | cv.PARTICIPANT_ROLES | cv.OUTPUT_ORIGINS | cv.ALIGNMENT_STATUSES
    | cv.PRODUCTION_REPORT_STATUSES)

_SCAN_ROOT = (Path(__file__).resolve().parents[1] / "src"
              / "pathway_v43")
_SCAN_FILES = sorted((_SCAN_ROOT / "pollutant").glob("*.py")) + [
    _SCAN_ROOT / "services" / "atom_tool.py"]
_SCAN_SKIP = {"controlled_vocab.py"}  # 单一来源定义面,非消费面


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """标记 docstring 常量节点 id(模块/类/函数首个 Expr 语句)。"""
    marked: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and \
                    isinstance(body[0].value, ast.Constant) and \
                    isinstance(body[0].value.value, str):
                marked.add(id(body[0].value))
    return marked


def _discover_controlled_literal_sinks() -> set[tuple[str, str]]:
    """发现集:消费方源码中精确等于受控词的字符串常量(ast,剥 docstring)。

    注:chemstate.py 等既有源文件 docstring 含历史遗留无效转义序列
    (下划线前反斜杠,DeprecationWarning)—— 非本轮触碰面,不修源码,
    本处局部忽略该编译期警告(只忽略 DeprecationWarning,其他异常照抛)。
    """
    import warnings

    found: set[tuple[str, str]] = set()
    for path in _SCAN_FILES:
        if path.name in _SCAN_SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            tree = ast.parse(text)
        marked = _docstring_node_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and \
                    isinstance(node.value, str) and \
                    id(node) not in marked and \
                    node.value in _VOCAB_UNION:
                found.add((path.name, node.value))
    return found


def test_t11_literal_sinks_registered_and_current() -> None:
    """字面量消费点:发现 ⊆ 登记(新写须登记)+ 登记词 ∈ 当前词表。"""
    discovered = _discover_controlled_literal_sinks()
    unregistered = discovered - set(REGISTERED_LITERAL_SINKS)
    assert not unregistered, (
        f"消费方源码出现未登记的受控词字面量(须登记进 REGISTERED_"
        f"LITERAL_SINKS 或改走 controlled_vocab 常量引用):"
        f"{sorted(unregistered)}")
    stale = {item for item in REGISTERED_LITERAL_SINKS
             if item[1] not in _VOCAB_UNION}
    assert not stale, (
        f"登记的受控词字面量已不在当前词表(权威词表改值/删词 ⇒ "
        f"字面量过期,须同步消费方):{sorted(stale)}")


def test_t11_scan_surface_is_complete() -> None:
    """扫描面 = pollutant 全家 + atom_tool(glob 动态枚举,新文件自动入面)。"""
    names = {path.name for path in _SCAN_FILES}
    for required in ("real_model.py", "runflow.py", "store.py", "queue.py",
                     "audit.py", "search.py", "events.py", "hypothesis.py",
                     "production.py", "s5b_compiler.py", "atom_tool.py"):
        assert required in names, f"扫描面缺失 {required}"


# ------------------------------------------------- D1-D7 漂移注入(红)

def test_d1_drift_injection_aromatic_in_order_vocab() -> None:
    """复现 57ea99b4 前形态:键级枚举混入 aromatic ⇒ 检测器必须红。"""
    bad = PROMPT.replace(cv.BOND_ORDER_ALTERNATION,
                         cv.BOND_ORDER_ALTERNATION + "|aromatic")
    assert bad != PROMPT  # 注入生效
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d2_drift_injection_drop_triple() -> None:
    """删执行器词 triple ⇒ 键级枚举双向断言红。"""
    bad = PROMPT.replace("|triple", "")
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d3_drift_injection_retired_op_in_declaration() -> None:
    """声明位教协议 v2 废除词 remove_atom ⇒ 正向断言红。"""
    bad = PROMPT.replace('"op": "add_atom"', '"op": "remove_atom"')
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d4_drift_injection_retired_op_word() -> None:
    """提示词出现废除词 remove_bond(全词替换)⇒ 红。"""
    bad = PROMPT.replace("break_bond", "remove_bond")
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d5_drift_injection_output_origin() -> None:
    """output_origin 换非法值 ⇒ 双向断言红。"""
    bad = PROMPT.replace("novel_outside_pool", "invented_by_model")
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d6_drift_injection_alignment_status() -> None:
    """alignment status 示范换非法值 ⇒ 正向断言红。"""
    bad = PROMPT.replace('"status": "resolved"', '"status": "guess"')
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_d7_drift_injection_op_not_reachable() -> None:
    """add_atom 全词换 insert_atom ⇒ 执行器词在提示词失可达 ⇒ 红。"""
    bad = PROMPT.replace("add_atom", "insert_atom")
    assert bad != PROMPT
    with pytest.raises(AssertionError):
        _assert_prompt_vocab_sync(bad)


def test_drift_injection_family_raises_specific_message() -> None:
    """注入红须携带定位信息(多/少词逐项列出,非笼统失败)。"""
    bad = PROMPT.replace(cv.BOND_ORDER_ALTERNATION,
                         cv.BOND_ORDER_ALTERNATION + "|aromatic")
    with pytest.raises(AssertionError, match="aromatic"):
        _assert_prompt_vocab_sync(bad)
    bad_drop = PROMPT.replace("|triple", "")
    with pytest.raises(AssertionError, match="triple"):
        _assert_prompt_vocab_sync(bad_drop)
