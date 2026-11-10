"""实验 1(E1)产物优先 novel 提案的编译与核验(E6;预注册
``PREREG_EXP1_PRODUCT_FIRST_FEEDBACK_2026-11-05`` §4.3/§5)。

范围:LLM 只声明**产物**(product_smiles + 可选 coproducts),程序用
``recorded_source.compile_recorded_reaction``(与库记录同一编译器/同一
形式归一算子)反推原子映射、编译执行、以 strict 身份多重集核对产物
集合;核验失败返回**白名单字段**(预注册 §5)供反馈轮使用。本模块
零金标、零题面、零模型调用、不碰判分。

入口矩阵(与实施书 §1 对齐;方案甲 2026-11-06):

| # | 入口 | 消费 | 校验/事务 |
| 1 | compile_novel_product_first | 底物 SMILES + 模型声明的产物组分 + proposal_id | 产物可解析(product_unparseable);compile_recorded_reaction(同一单一构建源,formnorm 归一)返回 compiled/unsupported;RecordedSourceError(不可解析)同接;失败 ⇒ 白名单 failure_kind |
| 2 | 主产物重指派 | 编译 spec 的 principal/coproducts + **formnorm 归一后的**声明产物 | 声明产物(单一组分)落在执行组分中 ⇒ 主产物改为声明组分并同步 coproducts(全组分多重集不变,expectation 仍为完整净产物集合);不在 ⇒ 不重指派并记录(principal_reassigned=false + reason) |
| 3 | 分桶(方案甲) | compile_recorded_reaction 的 ``formnorm.mapping_artifacts``(mapped_lhs/mapped_rhs/donor_map;同一编译链的映射事实) | 七条件全满足 ⇒ full;否则声明桶两档(declared_recognized / declared_unrecognized);算不出来 ⇒ fail-closed 声明桶 + reason(禁止静默 full)。**映射事实源按显式开关区分(R2 P1-4)**:B/C 编译路径缺/空映射材料直接 ``mapping_artifacts_missing`` fail-closed,只有 A 臂离线读数显式传 ``allow_replay=True`` 才走重放 |
| 4 | A 臂离线同尺读数 | 池 spec 的 edits/alignment/expectation 经 ``atom_tool.render + execute_edits`` 重放 | 只读离线函数;不改变 A 臂任何在线行为(事件/载荷/提示词零触碰) |

**量纲(只对主产物计;冻结 §4.3)**:

- 新增重原子 = 编译 spec 的 ``add_atom`` 编辑数(= 主产物里未映射到
  底物的重原子数);
- 移除重原子 = 底物中未映射进主产物的重原子数;
- 新增片段 = 新增原子按键连通性分块,每块连同其与底物的连接键算一个
  片段。

**七条件(全满足 ⇒ full;任一不满足 ⇒ 声明桶)**:新增 ≤8、移除 ≤8、
新增片段 ≤2、每片段命中 §4.3.1 白名单(图匹配;质子化/电荷归一,
H ±1)、连接点合法(经 O/N/S 杂原子或 C–C 键连到骨架,不允许无锚
孤立新增原子)、产物元素 ⊆ CHNOPS+Se+卤素、移除部分 ∈ §4.3.2 小离去
基白名单或在模型声明的共产物中出现(重元素对账;H/电荷不计)。

**白名单的图身份(2026-11-06 R2 P1-5)**:每张模板都是**受控整体候选**
(``bond_order_candidates``)——若干条完整归一化图,匹配时按整图判定;
不允许“把每根边的允许键级各自放宽再自由组合”。例:CO2 只收
`C(=O)–O`(恰一根 C=O),全单键 `C(O)O` 不匹配;NO2 至少要有一根
N=O;PO3 是 `P(=O)(O)(O)`;SO3 是 `S(=O)(=O)(O)`。H ±1 容差与电荷
归一(芳香按凯库勒)照旧。

**声明桶两档**:``declared_recognized``(片段命中 §4.3.3 已知半分子表
但超出限值)与 ``declared_unrecognized``(对不上任何表 / 域外元素 /
移除未声明)。判定口径见 ``_classify_bucket``:识别档要求**所有**超限
片段都能对上已知表且无域外元素/未声明移除;任一“对不上任何表”的片段
⇒ 未识别档(诊断优先,不掩盖幻觉)。

**披露项(不改变桶)**:``net_zero_rewrite``——新增 = 移除 = 0 但存在
断/成键(异构化、重排、原子对换)⇒ 照进 full,单独打旗标计数。

边界(不认证的东西):编译只证明"从底物出发按模型声明的完整净产物
集合可复现执行";不认证反应机制、催化循环、元素/电荷配平,也不认证
生物可行性(沿 recorded_source 既有边界声明)。分桶判据是工程门 +
化学评审采信的片段白名单,不是反应真伪判定;``供体/元素配平`` 类
化学合法性只做到冻结文本写明的重元素对账,不做电荷/氧化还原配平。
"""

from __future__ import annotations

import hashlib
import json
from itertools import permutations

from rdkit import Chem

from .chemstate import ChemicalStateError, strict_identity_of
from .controlled_vocab import (
    ALIGNMENT_STATUS_RESOLVED,
    BOND_ORDER_TOKENS,
    EDIT_OPS,
)
from .recorded_source import RecordedSourceError, compile_recorded_reaction
from .s5b_compiler import S5bCompileError

# 编辑操作词表单一来源(受控词表 CI:不得手写 op 字面量)
_OP_BREAK, _OP_FORM, _OP_CHANGE, _OP_ADD_ATOM = EDIT_OPS

# ---- 冻结参数(预注册 §4.3;2026-11-06 方案甲) ----

ADDED_HEAVY_ATOMS_BACKSTOP = 8
REMOVED_HEAVY_ATOMS_BACKSTOP = 8
MAX_ADDED_FRAGMENTS = 2

# **deprecated**:旧单阈值常量,仅为旧导入兼容保留;**不得参与任何
# 判据**(新判据见 ``_evaluate_conditions``;该值只作 A 臂/离线脚本
# 的历史引用面)。
MAX_ADDED_HEAVY_ATOMS_MAIN = ADDED_HEAVY_ATOMS_BACKSTOP

NOVEL_BUCKET_POLICY_VERSION = "novel-product-first-bucket-2"

VERIFICATION_TIER_FULL = "full"
VERIFICATION_TIER_DECLARED = "declared"
VERIFICATION_TIERS = (VERIFICATION_TIER_FULL, VERIFICATION_TIER_DECLARED)

BUCKET_KIND_FULL = "full"
BUCKET_KIND_DECLARED_RECOGNIZED = "declared_recognized"
BUCKET_KIND_DECLARED_UNRECOGNIZED = "declared_unrecognized"
BUCKET_KINDS = (BUCKET_KIND_FULL, BUCKET_KIND_DECLARED_RECOGNIZED,
                BUCKET_KIND_DECLARED_UNRECOGNIZED)

# 产物元素域(§4.3 条件 6;H 不在重原子域内)
PRODUCT_ELEMENT_DOMAIN = frozenset(
    {"C", "N", "O", "P", "S", "Se", "F", "Cl", "Br", "I"})

# 产物优先编译 spec 的 transformation_ref（不是库记录 ID）
PRODUCT_FIRST_TRANSFORMATION_REF = "novel-product-first"

# 失败类别（**严格回显预注册 §5 白名单**；新增类别须先改预注册）
FAILURE_PRODUCT_UNPARSEABLE = "product_unparseable"
FAILURE_NO_STRUCTURE_CORRESPONDENCE = "no_structure_correspondence"
FAILURE_MAPPING_ENUMERATION_TRUNCATED = "mapping_enumeration_truncated"
FAILURE_AMBIGUOUS_MAPPING = "ambiguous_mapping"
FAILURE_PRODUCT_SET_MISMATCH = "product_set_mismatch"
FAILURE_COMPILE_UNSUPPORTED = "compile_unsupported"
NOVEL_VERIFICATION_FAILURE_KINDS = (
    FAILURE_PRODUCT_UNPARSEABLE,
    FAILURE_NO_STRUCTURE_CORRESPONDENCE,
    FAILURE_MAPPING_ENUMERATION_TRUNCATED,
    FAILURE_AMBIGUOUS_MAPPING,
    FAILURE_PRODUCT_SET_MISMATCH,
    FAILURE_COMPILE_UNSUPPORTED,
)

# ---- §4.3.1 新增片段白名单(15 个图模板) ----
#
# 17 行白名单归并为 15 个**图**模板:
# - "O(H)" 与 "H2O 的 O" 是同一张图(单 O)→ 合并;
# - "O2(允许两块不相连)" 不设独立图模板:两块单 O 由 O 模板 × 片段数
#   ≤2 覆盖;相连 O–O 由 OOH 模板(H 容差覆盖 0 H)覆盖;
# - "F/Cl/Br/I" 一个模板(元素集合)。
#
# 每个原子给 ``h`` 名义区间;匹配时容差 ±1(下限截 0)——覆盖质子化/
# 电荷归一。
#
# **受控整体候选(2026-11-06 R2 P1-5 回修)**:每条边**不再**独立给“允许
# 键级集合”(旧写法 ``orders`` 会让各边自由组合,把全单键的非白名单片段
# 误判成 CO2/NO2/PO3/SO3)。现在每个模板显式声明
# ``bond_order_candidates``:每条候选是与 ``bonds`` **逐位对齐**的完整
# 键级下标元组(0=single,1=double,2=triple),匹配按整图候选判定。
# 不等价候选必须逐条列出;等价标签(如 CO2 的两根 C–O 互换)由原子
# 置换穷举覆盖,不重复声明。``_validate_whitelist_rows`` 在 import 时
# 机械拒绝任何缺候选/长度不符/残留 ``orders`` 的行。
_ADDED_TEMPLATE_ROWS: list[dict] = [
    {"name": "O", "atoms": [{"elements": ["O"], "h": [0, 1]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "N", "atoms": [{"elements": ["N"], "h": [1, 2]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "C", "atoms": [{"elements": ["C"], "h": [2, 3]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "S", "atoms": [{"elements": ["S"], "h": [0, 1]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "Se", "atoms": [{"elements": ["Se"], "h": [0, 1]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "halogen",
     "atoms": [{"elements": ["F", "Cl", "Br", "I"], "h": [0, 0]}],
     "bonds": [], "bond_order_candidates": [()]},
    # CO:羰基化插入(C≡O 的净结果是骨架上的 C=O 羰基;C 无 H)
    {"name": "CO",
     "atoms": [{"elements": ["C"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 0]}],
     "bonds": [{"i": 0, "j": 1}],
     "bond_order_candidates": [(1,)]},
    # CHO:甲酰基(C=O 且 C 带 1 H)
    {"name": "CHO",
     "atoms": [{"elements": ["C"], "h": [1, 1]},
               {"elements": ["O"], "h": [0, 0]}],
     "bonds": [{"i": 0, "j": 1}],
     "bond_order_candidates": [(1,)]},
    # OOH:过氧(O–O 单键;H 容差覆盖 O2 的 0 H 与 OOH 的 1 H)
    {"name": "OOH",
     "atoms": [{"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}],
     "bond_order_candidates": [(0,)]},
    # CO2:羧化 ⇒ 只接受羧基/羧酸根归一形态:C 连两个 O,且恰一根 C=O
    # (double)+ 一根 C–O(single)。全单键 C(O)O(缩醛/偕二醇形态)不匹配。
    {"name": "CO2",
     "atoms": [{"elements": ["C"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}],
     "bond_order_candidates": [(1, 0)]},
    # C2H3O(乙酰):C–C 单键 + 羰基 C=O
    {"name": "C2H3O",
     "atoms": [{"elements": ["C"], "h": [0, 0]},
               {"elements": ["C"], "h": [2, 3]},
               {"elements": ["O"], "h": [0, 0]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}],
     "bond_order_candidates": [(0, 1)]},
    # CONH2(氨甲酰):C–N 单键 + 羰基 C=O
    {"name": "CONH2",
     "atoms": [{"elements": ["C"], "h": [0, 0]},
               {"elements": ["N"], "h": [1, 2]},
               {"elements": ["O"], "h": [0, 0]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}],
     "bond_order_candidates": [(0, 1)]},
    # NO2(硝基):N 连 2 O 且**至少一根 N=O**。
    # - (1, 0) = 电荷分离式 [N+](=O)[O-] 经 formnorm 电荷归一后的形态;
    # - (1, 1) = 中性五价硝基 N(=O)=O(RDKit/常见 SMILES 写法);
    # 全单键 N(O)O(N 上两根 N–O 单键,如 N(OH)2 型)不得匹配。
    {"name": "NO2",
     "atoms": [{"elements": ["N"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 0]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}],
     "bond_order_candidates": [(1, 0), (1, 1)]},
    # PO3(磷酸化):P 连 3 O,恰一根 P=O + 两根 P–O(磷酸/磷酸酯归一
    # 形态)。全单键 P(O)(O)O(亚磷酸型,非 §4.3.1 的磷酸化片段)不匹配。
    {"name": "PO3",
     "atoms": [{"elements": ["P"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}, {"i": 0, "j": 3}],
     "bond_order_candidates": [(1, 0, 0)]},
    # SO3(硫酸化):S 连 3 O,两根 S=O + 一根 S–O(硫酸/硫酸酯归一形态)。
    # 全单键 S(O)(O)O(亚硫酸型)不匹配。
    {"name": "SO3",
     "atoms": [{"elements": ["S"], "h": [0, 0]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}, {"i": 0, "j": 3}],
     "bond_order_candidates": [(1, 1, 0)]},
]

# 与白名单模板一一对应的 H 容差(±1;下限截 0)
_H_TOLERANCE = 1

# ---- §4.3.2 小离去基白名单(重原子图匹配;H/电荷不计) ----
#
# 同一条“受控整体候选”规则(R2 P1-5):每个模板显式列整图候选,禁止逐边
# 独立放宽。
_LEAVING_GROUP_ROWS: list[dict] = [
    {"name": "H2O", "atoms": [{"elements": ["O"], "h": [0, 1]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "NH3", "atoms": [{"elements": ["N"], "h": [0, 3]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "H2S", "atoms": [{"elements": ["S"], "h": [0, 2]}],
     "bonds": [], "bond_order_candidates": [()]},
    {"name": "HX",
     "atoms": [{"elements": ["F", "Cl", "Br", "I"], "h": [0, 1]}],
     "bonds": [], "bond_order_candidates": [()]},
    # CO2 / 甲酸(重原子图相同:C 连 2 O)。两类归一形态:
    # - (1, 0) = 甲酸/甲酸根或羧酸型 C(=O)–O;
    # - (1, 1) = 完整 CO2 分子 O=C=O(离去 CO2 的形态)。
    # 全单键 C(O)O 不匹配。
    {"name": "CO2_or_formate",
     "atoms": [{"elements": ["C"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}],
     "bond_order_candidates": [(1, 0), (1, 1)]},
    # 乙酸(C–C + 羧基):恰一根 C=O + 一根 C–O;全单键 C–C(O)O 不匹配。
    {"name": "acetate",
     "atoms": [{"elements": ["C"], "h": [0, 1]},
               {"elements": ["C"], "h": [2, 3]},
               {"elements": ["O"], "h": [0, 1]},
               {"elements": ["O"], "h": [0, 1]}],
     "bonds": [{"i": 0, "j": 1}, {"i": 0, "j": 2}, {"i": 0, "j": 3}],
     "bond_order_candidates": [(0, 1, 0)]},
]

# ---- §4.3.3 已知半分子表(只用于 declared_recognized;重元素组成) ----
#
# 数值以冻结 §4.3.3 的重原子数为准;组成按“转移基团(酰基/糖基/
# 核苷酸基)”口径:
# - 生物素酰 15 = 生物素 C10H16N2O3S 去 OH 的酰基 C10H15N2O2S
#   (评审 §3A 的 C10H16N2O3S=16 是生物素本体,差一个 O;按冻结值 15);
# - 焦磷酸 7 = 焦磷酸基 P2O5(两个 P + 桥 O + 两个 =O + 两个 OH);
# - 其余与评审 §3A 的组成一致。
_KNOWN_MOIETY_ROWS: dict[str, dict] = {
    "isopentenyl": {"heavy_atoms": 5, "elements": {"C": 5}},
    "malonyl": {"heavy_atoms": 6, "elements": {"C": 3, "O": 3}},
    "succinyl": {"heavy_atoms": 7, "elements": {"C": 4, "O": 3}},
    "pyrophosphate": {"heavy_atoms": 7,
                      "elements": {"P": 2, "O": 5}},
    "ribosyl": {"heavy_atoms": 9, "elements": {"C": 5, "O": 4}},
    "glucosyl": {"heavy_atoms": 11, "elements": {"C": 6, "O": 5}},
    "lipoyl": {"heavy_atoms": 11,
               "elements": {"C": 8, "O": 1, "S": 2}},
    "glucuronyl": {"heavy_atoms": 12, "elements": {"C": 6, "O": 6}},
    "biotinyl": {"heavy_atoms": 15,
                 "elements": {"C": 10, "N": 2, "O": 2, "S": 1}},
    "farnesyl": {"heavy_atoms": 15, "elements": {"C": 15}},
    "glutathione": {"heavy_atoms": 20,
                    "elements": {"C": 10, "N": 3, "O": 6, "S": 1}},
    "phosphopantetheine": {"heavy_atoms": 22,
                           "elements": {"C": 11, "N": 2, "O": 7,
                                        "P": 1, "S": 1}},
    "AMP": {"heavy_atoms": 23,
            "elements": {"C": 10, "N": 5, "O": 7, "P": 1}},
    "ADP-ribose": {"heavy_atoms": 35,
                   "elements": {"C": 15, "N": 5, "O": 13, "P": 2}},
    "coenzyme_A": {"heavy_atoms": 48,
                   "elements": {"C": 21, "N": 7, "O": 16, "P": 3,
                                "S": 1}},
}


def _canonical_json_sha256(payload) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_whitelist_rows(rows: list[dict], *, label: str) -> None:
    """白名单**整图候选**的机械护栏(R2 P1-5,import 时执行)。

    拒绝:缺 ``bond_order_candidates``、候选为空、候选长度与 ``bonds``
    不符、键级下标越界、残留旧逐边 ``orders`` 键。任何一条不满足即在
    import 期抛 ``ValueError``——防止有人把“逐边独立放宽”重新写回来。
    """
    if not rows:
        raise ValueError(f"{label}: 空白名单")
    for row in rows:
        name = str(row.get("name") or "")
        if not name:
            raise ValueError(f"{label}: 模板缺 name")
        bonds = list(row.get("bonds") or [])
        for bond in bonds:
            if "orders" in bond:
                raise ValueError(
                    f"{label}:{name} 残留逐边 orders;"
                    "已改用整图 bond_order_candidates")
        candidates = row.get("bond_order_candidates")
        if not isinstance(candidates, (list, tuple)) or not candidates:
            raise ValueError(
                f"{label}:{name} 缺整图候选 bond_order_candidates")
        for candidate in candidates:
            if len(candidate) != len(bonds):
                raise ValueError(
                    f"{label}:{name} 候选长度 {len(candidate)} 与键数 "
                    f"{len(bonds)} 不符")
            for order_index in candidate:
                if not 0 <= int(order_index) < len(BOND_ORDER_TOKENS):
                    raise ValueError(
                        f"{label}:{name} 键级下标越界 {order_index}")


_validate_whitelist_rows(_ADDED_TEMPLATE_ROWS, label="added_fragment_whitelist")
_validate_whitelist_rows(_LEAVING_GROUP_ROWS, label="leaving_group_whitelist")


ADDED_FRAGMENT_WHITELIST = tuple(
    dict(row) for row in _ADDED_TEMPLATE_ROWS)
LEAVING_GROUP_WHITELIST = tuple(
    dict(row) for row in _LEAVING_GROUP_ROWS)
KNOWN_MOIETY_TABLE = {
    name: dict(row) for name, row in _KNOWN_MOIETY_ROWS.items()}

ADDED_FRAGMENT_WHITELIST_SHA256 = _canonical_json_sha256(
    list(ADDED_FRAGMENT_WHITELIST))
LEAVING_GROUP_WHITELIST_SHA256 = _canonical_json_sha256(
    list(LEAVING_GROUP_WHITELIST))
KNOWN_MOIETY_TABLE_SHA256 = _canonical_json_sha256(
    KNOWN_MOIETY_TABLE)
NOVEL_BUCKET_TABLE_SHA256 = _canonical_json_sha256({
    "added_fragment_whitelist": list(ADDED_FRAGMENT_WHITELIST),
    "leaving_group_whitelist": list(LEAVING_GROUP_WHITELIST),
    "known_moiety_table": KNOWN_MOIETY_TABLE,
})

# 底层 unsupported reason → 白名单 failure_kind 的**唯一映射**(单一来源;
# 交付书列全表)。record_unparseable 走 RecordedSourceError 分支。
_UNSUPPORTED_REASON_TO_FAILURE = {
    "no_structure_correspondence": FAILURE_NO_STRUCTURE_CORRESPONDENCE,
    "mapping_enumeration_truncated": FAILURE_MAPPING_ENUMERATION_TRUNCATED,
    "ambiguous_mapping": FAILURE_AMBIGUOUS_MAPPING,
    "product_set_mismatch": FAILURE_PRODUCT_SET_MISMATCH,
}
# 明确归 product_unparseable 的底层 kind（记录侧/产物侧不可解析）
_UNPARSEABLE_REASONS = frozenset({
    "record_unparseable",
    "record_donor_unparseable",
    "record_products_unparseable",
})

_PRINCIPAL_REASON_MULTI_COMPONENT = "declared_product_multi_component"
_PRINCIPAL_REASON_NOT_IN_EXECUTED = "declared_product_not_in_executed_components"
_PRINCIPAL_REASON_COMPONENT_MULTISET_MISMATCH = \
    "executed_component_multiset_mismatch"

# 分桶 fail-closed 原因码(算不出来 ⇒ declared_unrecognized,禁止静默 full)
# ``mapping_artifacts_missing`` 在 R2 P1-4 后也覆盖“B/C 编译资料缺失/空”
# ——该情形**不再**回落到 A 臂离线重放。
BUCKET_REASON_MAPPING_ARTIFACTS_MISSING = "mapping_artifacts_missing"
BUCKET_REASON_MAPPING_ARTIFACTS_UNPARSEABLE = "mapping_artifacts_unparseable"
BUCKET_REASON_SUBSTRATE_UNPARSEABLE = "substrate_unparseable_for_bucket"
BUCKET_REASON_DONOR_HEAVY_MISMATCH = "donor_heavy_atom_count_mismatch"
BUCKET_REASON_PRINCIPAL_UNRESOLVED = "principal_component_unresolved"
BUCKET_REASON_PRINCIPAL_AMBIGUOUS = "principal_component_ambiguous"
BUCKET_REASON_SPEC_REPLAY_FAILED = "spec_replay_failed"
BUCKET_REASON_DECLARED_COPRODUCT_UNPARSEABLE = \
    "declared_coproduct_unparseable"

# 条件原因码(逐条;报告 reason 列表,不短路口径)
BUCKET_REASON_ADDED_BACKSTOP = "added_heavy_atoms_backstop_exceeded"
BUCKET_REASON_REMOVED_BACKSTOP = "removed_heavy_atoms_backstop_exceeded"
BUCKET_REASON_TOO_MANY_FRAGMENTS = "too_many_added_fragments"
BUCKET_REASON_FRAGMENT_NOT_WHITELISTED = "added_fragment_not_whitelisted"
BUCKET_REASON_FRAGMENT_NO_ANCHOR = "added_fragment_without_anchor"
BUCKET_REASON_FRAGMENT_BAD_ANCHOR = "added_fragment_anchor_not_allowed"
BUCKET_REASON_ELEMENT_OUT_OF_DOMAIN = "product_element_out_of_domain"
BUCKET_REASON_REMOVED_NOT_ACCOUNTED = "removed_part_not_accounted"

_BOND_TYPE_TO_TOKEN = {
    Chem.BondType.SINGLE: BOND_ORDER_TOKENS[0],
    Chem.BondType.DOUBLE: BOND_ORDER_TOKENS[1],
    Chem.BondType.TRIPLE: BOND_ORDER_TOKENS[2],
}
_TOKEN_TO_BOND_ORDER_INDEX = {
    token: index for index, token in enumerate(BOND_ORDER_TOKENS)}


def _strict_key(smiles: str) -> str | None:
    """strict 身份键（与 compile 产物集合 gate 同一事实源）；不可解析 ⇒
    None。"""
    try:
        return strict_identity_of(str(smiles))
    except Exception:  # noqa: BLE001 —— 不可解析由调用方按失败处理
        return None


def _single_component(smiles: str) -> tuple[str | None, list[str]]:
    """SMILES → (单组分 canonical SMILES | None, 全部组分 canonical 列表)。"""
    mol = Chem.MolFromSmiles(str(smiles or ""))
    if mol is None:
        return None, []
    frags = list(Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True))
    canon = [Chem.MolToSmiles(frag) for frag in frags]
    if len(canon) != 1:
        return None, canon
    return canon[0], canon


def _failure(failure_kind: str, *, reason: str = "",
             executed_components: list[str] | None = None,
             extra: dict | None = None) -> dict:
    """统一失败返回：``feedback`` 只含预注册 §5 白名单字段（可直接渲染/
    登记），``diagnostics`` 为内部审计字段（**不得**进模型反馈）。"""
    feedback: dict = {"failure_kind": failure_kind}
    if failure_kind == FAILURE_PRODUCT_SET_MISMATCH and executed_components:
        feedback["executed_components"] = [
            str(x) for x in executed_components][:8]
    return {
        "status": "failed",
        "failure_kind": failure_kind,
        "feedback": feedback,
        "diagnostics": {"reason": str(reason or failure_kind),
                        **dict(extra or {})},
    }


def _reassign_principal_components(
        parts: list[str], declared_eff: str) -> tuple[bool, str, str]:
    """主产物重指派的**唯一判定**(组件级;单位负控直接调本函数)。

    parts = [编译中心组分, *其余组分]（编译 spec 的 principal 先）。
    declared_eff = formnorm 归一后的声明产物（严格身份比对用同一事实源）。

    返回 (reassigned, reason, declared_component)：
    - 声明产物是单一组分且 strict 身份等于中心组分 ⇒ 不重指派(reason="");
    - 命中其余组分之一 ⇒ 重指派(声明的那个成为中心组分,原中心组分
      并入其余组分,多重集不变);
    - 多组分声明 ⇒ 不重指派(multi_component);
    - 不在执行组分中 ⇒ 不重指派(not_in_executed_components)。
    """
    canon, _components = _single_component(declared_eff)
    if canon is None:
        return False, _PRINCIPAL_REASON_MULTI_COMPONENT, ""
    declared_key = _strict_key(canon)
    part_keys = [_strict_key(p) for p in parts]
    if declared_key is not None and declared_key == part_keys[0]:
        return False, "", parts[0]
    if declared_key is not None and declared_key in part_keys[1:]:
        return True, "", parts[part_keys.index(declared_key)]
    return False, _PRINCIPAL_REASON_NOT_IN_EXECUTED, ""


def _map_unsupported(reason: str) -> str:
    if reason in _UNPARSEABLE_REASONS:
        return FAILURE_PRODUCT_UNPARSEABLE
    return _UNSUPPORTED_REASON_TO_FAILURE.get(reason,
                                              FAILURE_COMPILE_UNSUPPORTED)


# ---------------------------------------------------------------- 图工具

def _kekulized_copy(mol: Chem.Mol) -> Chem.Mol:
    out = Chem.Mol(mol)
    try:
        Chem.Kekulize(out, clearAromaticFlags=True)
    except Exception:  # noqa: BLE001 —— 少数结构不可凯库勒化:按原样
        pass
    return out


def _bond_order_token(bond: Chem.Bond) -> str:
    return _BOND_TYPE_TO_TOKEN.get(bond.GetBondType(), "")


def _component_indices(mol: Chem.Mol) -> list[tuple[int, ...]]:
    return [tuple(int(i) for i in comp)
            for comp in Chem.GetMolFrags(mol)]


def _component_identity(mol: Chem.Mol, indices: tuple[int, ...]) -> str | None:
    """组分(连接分量)身份键:抽子图后 strict_identity_of(去 map 号;
    只删不相连组分,不切键,不会改变边界 H)。"""
    keep = set(indices)
    rw = Chem.RWMol(mol)
    for idx in sorted(set(range(mol.GetNumAtoms())) - keep, reverse=True):
        rw.RemoveAtom(int(idx))
    sub = rw.GetMol()
    try:
        Chem.SanitizeMol(sub)
    except Exception:  # noqa: BLE001
        return None
    for atom in sub.GetAtoms():
        if atom.GetAtomMapNum():
            atom.SetAtomMapNum(0)
    try:
        return strict_identity_of(Chem.MolToSmiles(sub))
    except Exception:  # noqa: BLE001
        return None


def _principal_component(
        mol: Chem.Mol, principal_smiles: str) -> tuple[tuple[int, ...] | None,
                                                     str]:
    """返回 (主产物组分索引 | None, reason)。0 个/多个同身份组分 ⇒
    fail-closed(不猜重复组分哪一份是主产物)。"""
    target = _strict_key(principal_smiles)
    if target is None:
        return None, BUCKET_REASON_PRINCIPAL_UNRESOLVED
    matches = [comp for comp in _component_indices(mol)
               if _component_identity(mol, comp) == target]
    if not matches:
        from .recorded_source import normalize_record_side_smiles

        norm_res = normalize_record_side_smiles(str(principal_smiles or ""))
        if norm_res.get("status") == "applied":
            norm_target = _strict_key(str(norm_res.get("normalized") or ""))
            if norm_target is not None:
                matches = [
                    comp for comp in _component_indices(mol)
                    if _component_identity(mol, comp) == norm_target
                ]
    if not matches:
        return None, BUCKET_REASON_PRINCIPAL_UNRESOLVED
    if len(matches) > 1:
        return None, BUCKET_REASON_PRINCIPAL_AMBIGUOUS
    return matches[0], ""


def _fragment_graph(mol: Chem.Mol, atom_indices: list[int]) -> dict:
    """片段图:重原子元素 + H 数 + 内部键级(凯库勒空间)。"""
    local = {int(idx): pos for pos, idx in enumerate(atom_indices)}
    atoms = []
    for idx in atom_indices:
        atom = mol.GetAtomWithIdx(int(idx))
        atoms.append({"element": atom.GetSymbol(),
                      "h": int(atom.GetTotalNumHs())})
    bonds = []
    for bond in mol.GetBonds():
        a, b = int(bond.GetBeginAtomIdx()), int(bond.GetEndAtomIdx())
        if a in local and b in local:
            bonds.append({"i": local[a], "j": local[b],
                          "order": _bond_order_token(bond)})
    return {"atoms": atoms, "bonds": bonds}


def _decompose(mol: Chem.Mol, atom_indices: set[int]) -> list[list[int]]:
    """按分子键图把给定原子集合分解为连通块(块内只走给定原子之间的键)。"""
    remaining = set(int(i) for i in atom_indices)
    out: list[list[int]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        comp = [seed]
        while stack:
            cur = stack.pop()
            for neighbor in mol.GetAtomWithIdx(cur).GetNeighbors():
                nxt = int(neighbor.GetIdx())
                if nxt in remaining:
                    remaining.remove(nxt)
                    stack.append(nxt)
                    comp.append(nxt)
        out.append(sorted(comp))
    return out


def _anchor_bonds(mol: Chem.Mol, fragment: set[int],
                  allowed: set[int]) -> list[dict]:
    """片段原子 → 骨架原子(同一主产物组分内、非片段原子)的连接键。"""
    anchors: list[dict] = []
    for bond in mol.GetBonds():
        a, b = int(bond.GetBeginAtomIdx()), int(bond.GetEndAtomIdx())
        if (a in fragment) == (b in fragment):
            continue
        frag_atom, skel_atom = (a, b) if a in fragment else (b, a)
        if skel_atom not in allowed:
            continue
        anchors.append({
            "fragment_element":
                mol.GetAtomWithIdx(frag_atom).GetSymbol(),
            "skeleton_element":
                mol.GetAtomWithIdx(skel_atom).GetSymbol(),
            "order": _bond_order_token(bond),
        })
    return anchors


def _h_allowed(value: int, nominal: list[int]) -> bool:
    low = max(0, int(nominal[0]) - _H_TOLERANCE)
    high = int(nominal[1]) + _H_TOLERANCE
    return low <= int(value) <= high


def _template_candidates(template: dict) -> list[tuple[str, ...]]:
    """模板的整图候选:每条候选 = 与 ``bonds`` 逐位对齐的键级 token 元组。

    候选由模板显式声明(``bond_order_candidates``);本函数只做 token
    翻译,**不做**逐边集合的笛卡尔积展开(那是 P1-5 的缺陷来源)。
    """
    bonds = list(template.get("bonds") or [])
    candidates: list[tuple[str, ...]] = []
    for candidate in template.get("bond_order_candidates") or []:
        if len(candidate) != len(bonds):
            continue
        candidates.append(tuple(
            BOND_ORDER_TOKENS[int(index)] for index in candidate))
    return candidates


def _match_template(fragment: dict, template: dict) -> dict | None:
    """片段图 ↔ 模板图同构(元素/内部键级/H 容差 ±1;键数相等)。

    键级按模板声明的**整图候选**逐条判定(同一候选内所有边必须同时
    命中),不允许把各边的允许键级自由组合。返回匹配映射
    (模板原子序 ↔ 片段原子序 + 命中的候选)或 None。
    """
    atoms = fragment.get("atoms") or []
    t_atoms = template.get("atoms") or []
    if len(atoms) != len(t_atoms):
        return None
    frag_bonds = list(fragment.get("bonds") or [])
    t_bonds = list(template.get("bonds") or [])
    if len(frag_bonds) != len(t_bonds):
        return None
    candidates = _template_candidates(template)
    if not candidates:
        return None
    n = len(atoms)
    for perm in permutations(range(n)):
        # perm[local] = template atom index
        ok = True
        for local, t_index in enumerate(perm):
            atom = atoms[local]
            t_atom = t_atoms[t_index]
            if atom.get("element") not in \
                    set(t_atom.get("elements") or []):
                ok = False
                break
            if not _h_allowed(int(atom.get("h") or 0),
                              list(t_atom.get("h") or [0, 0])):
                ok = False
                break
        if not ok:
            continue
        for candidate in candidates:
            # 整图候选:模板边 → 具体键级 token(逐位对齐;模板原子序空间)
            expected: dict[tuple[int, int], str] = {}
            for bond, token in zip(t_bonds, candidate):
                pair = tuple(sorted((int(bond["i"]), int(bond["j"]))))
                expected[pair] = token
            if len(expected) != len(t_bonds):
                continue
            seen_pairs = set()
            for bond in frag_bonds:
                a, b = perm[int(bond["i"])], perm[int(bond["j"])]
                pair = tuple(sorted((a, b)))
                if pair not in expected:
                    ok = False
                    break
                if str(bond.get("order")) != expected[pair]:
                    ok = False
                    break
                seen_pairs.add(pair)
            if ok and seen_pairs == set(expected):
                return {"permutation": list(perm),
                        "bond_orders": list(candidate)}
            ok = True
    return None


def _match_composition(elements_counter: dict[str, int],
                       row: dict) -> bool:
    if int(sum(elements_counter.values())) != int(row.get("heavy_atoms") or 0):
        return False
    return dict(elements_counter) == dict(row.get("elements") or {})


def _known_moiety_for(elements_counter: dict[str, int]) -> str:
    for name in sorted(KNOWN_MOIETY_TABLE):
        if _match_composition(elements_counter, KNOWN_MOIETY_TABLE[name]):
            return name
    return ""


def _elements_counter(mol: Chem.Mol, indices) -> dict[str, int]:
    counter: dict[str, int] = {}
    for idx in indices:
        atom = mol.GetAtomWithIdx(int(idx))
        if int(atom.GetAtomicNum()) <= 1:
            continue
        symbol = atom.GetSymbol()
        counter[symbol] = counter.get(symbol, 0) + 1
    return counter


def _whitelist_for_fragment(fragment: dict,
                            rows: list[dict]) -> str:
    for row in rows:
        if _match_template(fragment, row) is not None:
            return str(row.get("name") or "")
    return ""


def _build_fragment_record(mol: Chem.Mol, indices: list[int],
                           *, skeleton: set[int] | None = None,
                           whitelist_rows: list[dict] | None = None) -> dict:
    graph = _fragment_graph(mol, indices)
    counter = _elements_counter(mol, indices)
    record = {
        "atom_count": int(sum(counter.values())),
        "elements": dict(sorted(counter.items())),
        "h_counts": [int(atom.get("h") or 0)
                     for atom in graph.get("atoms") or []],
        "internal_bonds": [
            {**bond} for bond in graph.get("bonds") or []],
        "anchors": _anchor_bonds(mol, set(indices), skeleton or set()),
        "whitelist_match": "",
        "known_moiety": _known_moiety_for(counter),
    }
    if whitelist_rows:
        record["whitelist_match"] = _whitelist_for_fragment(
            graph, whitelist_rows)
    return record


# ------------------------------------------------------- 分桶主逻辑

def _unavailable_bucket(reason: str, policy_version: str,
                        table_sha256: str) -> dict:
    """算不出来的统一 fail-closed 返回(声明桶·未识别,禁止静默 full)。"""
    return {
        "bucket_kind": BUCKET_KIND_DECLARED_UNRECOGNIZED,
        "verification_tier": VERIFICATION_TIER_DECLARED,
        "metrics": {"available": False, "reason": str(reason)},
        "conditions": {},
        "reasons": [str(reason)],
        "net_zero_rewrite": False,
        "policy_version": str(policy_version),
        "table_sha256": str(table_sha256),
        "fail_closed": True,
    }


def _net_zero_rewrite(spec: dict, added: int | None,
                      removed: int | None) -> bool:
    if added != 0 or removed != 0:
        return False
    for edit in (spec.get("edits") or []):
        if str(edit.get("op")) in {_OP_BREAK, _OP_FORM}:
            return True
    return False


def _evaluate_conditions(metrics: dict, spec: dict) -> tuple[dict, list[str]]:
    added = int(metrics.get("added_heavy_atoms") or 0)
    removed = int(metrics.get("removed_heavy_atoms") or 0)
    added_fragments = list(metrics.get("added_fragments") or [])
    removed_fragments = list(metrics.get("removed_fragments") or [])
    product_elements = set(metrics.get("product_elements") or [])
    conditions: dict[str, bool] = {}
    reasons: list[str] = []

    conditions["1_added_heavy_atoms_le_backstop"] = \
        added <= ADDED_HEAVY_ATOMS_BACKSTOP
    if not conditions["1_added_heavy_atoms_le_backstop"]:
        reasons.append(BUCKET_REASON_ADDED_BACKSTOP)

    conditions["2_removed_heavy_atoms_le_backstop"] = \
        removed <= REMOVED_HEAVY_ATOMS_BACKSTOP
    if not conditions["2_removed_heavy_atoms_le_backstop"]:
        reasons.append(BUCKET_REASON_REMOVED_BACKSTOP)

    conditions["3_added_fragments_le_max"] = \
        len(added_fragments) <= MAX_ADDED_FRAGMENTS
    if not conditions["3_added_fragments_le_max"]:
        reasons.append(BUCKET_REASON_TOO_MANY_FRAGMENTS)

    conditions["4_added_fragments_whitelisted"] = all(
        bool(fragment.get("whitelist_match")) for fragment in added_fragments)
    if not conditions["4_added_fragments_whitelisted"]:
        reasons.append(BUCKET_REASON_FRAGMENT_NOT_WHITELISTED)

    # 条件 5:每个新增片段至少一根锚键连到骨架;锚键骨架端 ∈ C/N/O/S
    # （C–C 与 C–O/C–N/O–P 等正常有机键;卤素挂 C 也在此面),键级
    # single/double。无锚或锚到非有机骨架 ⇒ 拒。
    anchored = True
    for fragment in added_fragments:
        anchors = list(fragment.get("anchors") or [])
        if not anchors:
            anchored = False
            reasons.append(BUCKET_REASON_FRAGMENT_NO_ANCHOR)
            continue
        for anchor in anchors:
            if str(anchor.get("skeleton_element")) not in {"C", "N", "O", "S"} \
                    or str(anchor.get("order")) not in set(
                        BOND_ORDER_TOKENS[:2]):
                anchored = False
                reasons.append(BUCKET_REASON_FRAGMENT_BAD_ANCHOR)
                break
    conditions["5_added_fragments_anchored"] = anchored

    out_of_domain = sorted(product_elements - PRODUCT_ELEMENT_DOMAIN)
    conditions["6_product_elements_in_domain"] = not out_of_domain
    for element in out_of_domain:
        reasons.append(f"{BUCKET_REASON_ELEMENT_OUT_OF_DOMAIN}:{element}")

    undeclared_ok = True
    for u_smi in (spec.get("undeclared_coproducts") or []):
        from .recorded_source import normalize_record_side_smiles

        u_cands = [str(u_smi or "")]
        norm_u = normalize_record_side_smiles(str(u_smi or ""))
        if norm_u.get("status") == "applied":
            u_cands.append(str(norm_u.get("normalized") or ""))
        u_matched = False
        for u_cand in u_cands:
            u_mol = Chem.MolFromSmiles(u_cand)
            if u_mol is None or u_mol.GetNumAtoms() == 0:
                continue
            u_kmol = _kekulized_copy(u_mol)
            u_fg = _fragment_graph(u_kmol, list(range(u_kmol.GetNumAtoms())))
            if _whitelist_for_fragment(u_fg, list(LEAVING_GROUP_WHITELIST)):
                u_matched = True
                break
        if not u_matched:
            undeclared_ok = False
            break
    conditions["7_removed_part_accounted"] = (
        undeclared_ok
        and all(bool(fragment.get("accounted")) for fragment in removed_fragments)
    )
    if not conditions["7_removed_part_accounted"]:
        reasons.append(BUCKET_REASON_REMOVED_NOT_ACCOUNTED)

    metrics["net_zero_rewrite"] = _net_zero_rewrite(
        spec, added, removed)
    return conditions, reasons


def _classify_bucket(conditions: dict, reasons: list[str],
                     metrics: dict) -> str:
    if all(bool(value) for value in conditions.values()):
        return BUCKET_KIND_FULL
    # 域外元素 / 移除未声明 ⇒ 未识别(冻结文本明列)
    if not conditions.get("6_product_elements_in_domain", False):
        return BUCKET_KIND_DECLARED_UNRECOGNIZED
    if not conditions.get("7_removed_part_accounted", False):
        return BUCKET_KIND_DECLARED_UNRECOGNIZED
    added_fragments = list(metrics.get("added_fragments") or [])
    removed_fragments = list(metrics.get("removed_fragments") or [])
    recognized_fragments = 0
    for fragment in added_fragments:
        if fragment.get("known_moiety"):
            recognized_fragments += 1
            continue
        if not fragment.get("whitelist_match"):
            # 有片段对不上任何表 ⇒ 未识别(不拿另一个已知片段掩盖)
            return BUCKET_KIND_DECLARED_UNRECOGNIZED
    for fragment in removed_fragments:
        if fragment.get("known_moiety"):
            recognized_fragments += 1
            continue
        if not (fragment.get("whitelist_match")
                or fragment.get("accounted")):
            return BUCKET_KIND_DECLARED_UNRECOGNIZED
    if recognized_fragments:
        return BUCKET_KIND_DECLARED_RECOGNIZED
    return BUCKET_KIND_DECLARED_UNRECOGNIZED


def _finalize_bucket(metrics: dict, spec: dict, *,
                     policy_version: str, table_sha256: str,
                     fail_closed_reason: str = "") -> dict:
    if fail_closed_reason:
        return _unavailable_bucket(
            fail_closed_reason, policy_version, table_sha256)
    # 披露:spec 的 add_atom 重原子编辑数(冻结量纲的等价表述)。正常
    # 路径两者相等;模型把新增原子放进共产物时可能不等 —— 量纲按
    # "只对主产物计",差异机器披露,不静默。
    spec_add = sum(
        1 for edit in (spec.get("edits") or [])
        if str(edit.get("op")) == _OP_ADD_ATOM
        and str(edit.get("element") or "").upper() != "H")
    metrics["spec_add_atom_edits"] = int(spec_add)
    metrics["add_atom_edits_match_main_product"] = bool(
        int(spec_add) == int(metrics.get("added_heavy_atoms") or 0))
    conditions, reasons = _evaluate_conditions(metrics, spec)
    bucket_kind = _classify_bucket(conditions, reasons, metrics)
    return {
        "bucket_kind": bucket_kind,
        "verification_tier": (VERIFICATION_TIER_FULL
                              if bucket_kind == BUCKET_KIND_FULL
                              else VERIFICATION_TIER_DECLARED),
        "metrics": metrics,
        "conditions": conditions,
        "reasons": reasons,
        "net_zero_rewrite": bool(metrics.get("net_zero_rewrite")),
        "policy_version": str(policy_version),
        "table_sha256": str(table_sha256),
        "fail_closed": False,
    }


def _account_removed_fragments(
        removed_fragments: list[dict],
        declared_coproduct_elements: dict[str, int]) -> None:
    """条件 7 对账:逐块先查小离去基白名单;剩余未认领部分整组按重
    元素多重集与声明共产物对账(贪心消耗;H/电荷不计)。"""
    unaccounted: list[dict] = []
    for fragment in removed_fragments:
        if fragment.get("whitelist_match"):
            fragment["accounted"] = True
        else:
            unaccounted.append(fragment)
    if not unaccounted:
        return
    remaining = dict(declared_coproduct_elements)
    combined: dict[str, int] = {}
    for fragment in unaccounted:
        for element, count in (fragment.get("elements") or {}).items():
            combined[element] = combined.get(element, 0) + int(count)
    enough = all(int(remaining.get(element, 0)) >= int(count)
                 for element, count in combined.items())
    if not enough:
        for fragment in unaccounted:
            fragment["accounted"] = False
        return
    for fragment in unaccounted:
        fragment["accounted"] = True
    # 递减声明共产物余额(只用于本次判定;不回写输入)
    for element, count in combined.items():
        remaining[element] = int(remaining[element]) - int(count)


def _metrics_from_mapping_artifacts(
        *, spec: dict, substrate_smiles: str,
        declared_coproducts: list[str],
        mapping_artifacts: dict) -> tuple[dict | None, str]:
    mapped_lhs = str(mapping_artifacts.get("mapped_lhs") or "")
    mapped_rhs = str(mapping_artifacts.get("mapped_rhs") or "")
    if not mapped_lhs or not mapped_rhs:
        return None, BUCKET_REASON_MAPPING_ARTIFACTS_MISSING
    lhs_mol = Chem.MolFromSmiles(mapped_lhs)
    rhs_mol = Chem.MolFromSmiles(mapped_rhs)
    if lhs_mol is None or rhs_mol is None:
        return None, BUCKET_REASON_MAPPING_ARTIFACTS_UNPARSEABLE
    substrate_mol = Chem.MolFromSmiles(str(substrate_smiles or ""))
    if substrate_mol is None:
        return None, BUCKET_REASON_SUBSTRATE_UNPARSEABLE
    substrate_heavy = _elements_counter(
        substrate_mol, range(substrate_mol.GetNumAtoms()))
    donor_heavy = _elements_counter(lhs_mol, range(lhs_mol.GetNumAtoms()))
    if substrate_heavy != donor_heavy:
        # formnorm 只做 Uncharge(重原子图不变);组成不符 ⇒ 映射事实
        # 与当前底物不同源 ⇒ fail-closed,不静默算差集
        return None, BUCKET_REASON_DONOR_HEAVY_MISMATCH
    lhs_maps = {int(atom.GetAtomMapNum()) for atom in lhs_mol.GetAtoms()
                if int(atom.GetAtomicNum()) > 1}
    if 0 in lhs_maps:
        return None, BUCKET_REASON_MAPPING_ARTIFACTS_UNPARSEABLE
    rhs_maps = {int(atom.GetAtomMapNum()) for atom in rhs_mol.GetAtoms()
                if int(atom.GetAtomicNum()) > 1}
    if 0 in rhs_maps:
        return None, BUCKET_REASON_MAPPING_ARTIFACTS_UNPARSEABLE
    # 新增映射 = 主产物组分里未在 donor 出现的 map 号;但主产物要先
    # 定位。这里用“主产物里 map 不在 lhs_maps”的新增原子;移除侧 =
    # 底物 map 不在「主产物 map 集合」里(可能进共产物,也算移除)。
    principal, reason = _principal_component(
        rhs_mol, str(spec.get("product_smiles") or ""))
    if principal is None:
        return None, reason
    principal_maps = {int(rhs_mol.GetAtomWithIdx(int(i)).GetAtomMapNum())
                      for i in principal}
    added_indices = {
        int(atom.GetIdx()) for atom in rhs_mol.GetAtoms()
        if int(atom.GetAtomicNum()) > 1
        and int(atom.GetAtomMapNum()) not in lhs_maps
        and int(atom.GetIdx()) in set(principal)}
    removed_indices = {
        int(atom.GetIdx()) for atom in lhs_mol.GetAtoms()
        if int(atom.GetAtomicNum()) > 1
        and int(atom.GetAtomMapNum()) not in principal_maps}
    return _metrics_from_components_substrate(
        substrate_mol=lhs_mol, rhs_mol=rhs_mol,
        principal_set=set(principal),
        declared_coproducts=declared_coproducts,
        added_indices=added_indices,
        removed_substrate_indices=removed_indices,
        mapping_source="formnorm.mapping_artifacts")


def _metrics_from_spec_replay(
        *, spec: dict, substrate_smiles: str,
        declared_coproducts: list[str]) -> tuple[dict | None, str]:
    """A 臂离线读数:同一编译链的 render + edits 重放(零 LLM、零在线
    行为)。主产物组分内的新增/移除量纲与 B/C 同一函数口径。"""
    from ..services.atom_tool import execute_edits, render

    try:
        rendered = render(str(substrate_smiles or ""), "S")
        executed = execute_edits(rendered, list(spec.get("edits") or []))
    except Exception:  # noqa: BLE001
        return None, BUCKET_REASON_SPEC_REPLAY_FAILED
    if not executed.get("ok"):
        return None, BUCKET_REASON_SPEC_REPLAY_FAILED
    product_mapped = str(executed.get("product_mapped_smiles") or "")
    rhs_mol = Chem.MolFromSmiles(product_mapped)
    substrate_mol = Chem.MolFromSmiles(str(rendered.smiles or ""))
    if rhs_mol is None or substrate_mol is None:
        return None, BUCKET_REASON_SPEC_REPLAY_FAILED
    map_to_idx = {int(atom.GetAtomMapNum()): int(atom.GetIdx())
                  for atom in rhs_mol.GetAtoms()}
    if 0 in map_to_idx:
        return None, BUCKET_REASON_SPEC_REPLAY_FAILED
    id_to_idx = dict(executed.get("atom_id_map") or {})
    principal, reason = _principal_component(
        rhs_mol, str(spec.get("product_smiles") or ""))
    if principal is None:
        return None, reason
    principal_set = set(principal)
    added_indices: set[int] = set()
    for edit in (spec.get("edits") or []):
        if str(edit.get("op")) != _OP_ADD_ATOM:
            continue
        if str(edit.get("element") or "").upper() == "H":
            continue
        new_id = str(edit.get("new_atom_id") or "")
        if new_id not in id_to_idx:
            return None, BUCKET_REASON_SPEC_REPLAY_FAILED
        idx = map_to_idx.get(int(id_to_idx[new_id]) + 1)
        if idx is None:
            return None, BUCKET_REASON_SPEC_REPLAY_FAILED
        if idx in principal_set:
            added_indices.add(idx)
    removed_substrate_indices: set[int] = set()
    for atom_id, substrate_idx in (rendered.atom_id_map or {}).items():
        if int(substrate_mol.GetAtomWithIdx(int(substrate_idx))
               .GetAtomicNum()) <= 1:
            continue
        if atom_id not in id_to_idx:
            continue
        product_idx = map_to_idx.get(int(id_to_idx[atom_id]) + 1)
        if product_idx is None:
            return None, BUCKET_REASON_SPEC_REPLAY_FAILED
        if product_idx not in principal_set:
            removed_substrate_indices.add(int(substrate_idx))
    return _metrics_from_components_substrate(
        substrate_mol=substrate_mol, rhs_mol=rhs_mol, principal_set=principal_set,
        declared_coproducts=declared_coproducts,
        added_indices=added_indices,
        removed_substrate_indices=removed_substrate_indices,
        mapping_source="atom_tool.render+execute_edits")


def _metrics_from_components_substrate(
        *, substrate_mol: Chem.Mol, rhs_mol: Chem.Mol,
        principal_set: set[int], declared_coproducts: list[str],
        added_indices: set[int], removed_substrate_indices: set[int],
        mapping_source: str) -> tuple[dict | None, str]:
    """A 臂离线路径的度量装配(移除片段在底物图上分解)。"""
    added_fragments = []
    for indices in _decompose(rhs_mol, added_indices):
        record = _build_fragment_record(
            rhs_mol, indices, skeleton=principal_set,
            whitelist_rows=list(ADDED_FRAGMENT_WHITELIST))
        added_fragments.append(record)
    removed_fragments = []
    for indices in _decompose(substrate_mol, removed_substrate_indices):
        record = _build_fragment_record(
            substrate_mol, indices,
            skeleton=set(range(substrate_mol.GetNumAtoms())) - set(indices),
            whitelist_rows=list(LEAVING_GROUP_WHITELIST))
        removed_fragments.append(record)
    declared_coproduct_elements: dict[str, int] = {}
    for smiles in declared_coproducts or []:
        mol = Chem.MolFromSmiles(str(smiles or ""))
        if mol is None:
            return None, BUCKET_REASON_DECLARED_COPRODUCT_UNPARSEABLE
        for element, count in _elements_counter(
                mol, range(mol.GetNumAtoms())).items():
            declared_coproduct_elements[element] = \
                declared_coproduct_elements.get(element, 0) + int(count)
    _account_removed_fragments(
        removed_fragments, declared_coproduct_elements)
    product_elements = sorted(_elements_counter(
        rhs_mol, range(rhs_mol.GetNumAtoms())))
    metrics = {
        "available": True,
        "mapping_source": str(mapping_source),
        "added_heavy_atoms": int(sum(
            fragment["atom_count"] for fragment in added_fragments)),
        "removed_heavy_atoms": int(sum(
            fragment["atom_count"] for fragment in removed_fragments)),
        "added_fragment_count": len(added_fragments),
        "added_fragments": added_fragments,
        "removed_fragments": removed_fragments,
        "product_elements": product_elements,
        "declared_coproduct_elements": dict(
            sorted(declared_coproduct_elements.items())),
        "net_zero_rewrite": False,
    }
    return metrics, ""


def compute_novel_bucket(
    *, spec: dict, substrate_smiles: str,
    declared_product: str = "",
    declared_coproducts: list[str] | None = None,
    mapping_artifacts: dict | None = None,
    allow_replay: bool = False,
    policy_version: str = NOVEL_BUCKET_POLICY_VERSION,
    table_sha256: str = NOVEL_BUCKET_TABLE_SHA256,
) -> dict:
    """方案甲复合判据的分桶入口(单一函数;三臂同口径)。

    映射事实源按**显式开关**区分(R2 P1-4):

    - ``mapping_artifacts`` 给出且非空(B/C 臂:``compile_recorded_reaction``
      的 ``formnorm.mapping_artifacts``)⇒ 直接用同源映射事实;
    - ``mapping_artifacts`` 是 None/空 dict 且 ``allow_replay=True``
      (**仅** A 臂离线读数 ``compute_arm_a_bucket_readout`` 这样调用)⇒
      用同一编译链的 render + edits 重放;
    - ``mapping_artifacts`` 是 None/空 dict 且 ``allow_replay=False``
      (B/C 编译路径的默认)⇒ **不**转重放,直接 fail-closed
      ``mapping_artifacts_missing``(禁止把 B/C 的缺失资料静默换成 A 专用路径);
    - 非 dict 值 ⇒ fail-closed ``mapping_artifacts_unparseable``;
    - 任何算不出来的情形 ⇒ declared_unrecognized + reason(fail-closed)。

    返回 ``bucket_kind`` / ``verification_tier`` / ``metrics`` /
    ``conditions`` / ``reasons`` / ``net_zero_rewrite`` /
    ``policy_version`` / ``table_sha256`` / ``fail_closed``。
    """
    declared_coproducts = [str(c) for c in (declared_coproducts or [])]
    if mapping_artifacts is not None and not isinstance(mapping_artifacts, dict):
        return _unavailable_bucket(
            BUCKET_REASON_MAPPING_ARTIFACTS_UNPARSEABLE,
            policy_version, table_sha256)
    artifacts = dict(mapping_artifacts) if mapping_artifacts else {}
    if artifacts:
        metrics, reason = _metrics_from_mapping_artifacts(
            spec=spec, substrate_smiles=substrate_smiles,
            declared_coproducts=declared_coproducts,
            mapping_artifacts=artifacts)
    elif allow_replay:
        metrics, reason = _metrics_from_spec_replay(
            spec=spec, substrate_smiles=substrate_smiles,
            declared_coproducts=declared_coproducts)
    else:
        metrics, reason = None, BUCKET_REASON_MAPPING_ARTIFACTS_MISSING
    if metrics is None:
        return _unavailable_bucket(reason, policy_version, table_sha256)
    return _finalize_bucket(
        metrics, spec, policy_version=policy_version,
        table_sha256=table_sha256)


def compute_arm_a_bucket_readout(
    spec: dict, substrate_smiles: str,
    declared_coproducts: list[str] | None = None) -> dict:
    """A 臂**离线**同尺读数(零 LLM;不改变 A 臂任何在线行为)。

    与 B/C 共用同一 ``compute_novel_bucket`` / 三张表 / 七条件;映射
    事实来自池 spec 的 edits 在同一编译链上的 render+edits 重放。
    ``allow_replay=True`` 是 A 离线读数的**唯一**授权点(R2 P1-4):
    B/C 编译路径不传该开关,缺映射材料一律 fail-closed。
    ``declared_coproducts`` 缺省 = spec 的 coproducts(A 臂的共产物
    就是 spec 里声明的其余组分)。
    """
    coproducts = ([str(c) for c in declared_coproducts]
                  if declared_coproducts is not None
                  else [str(c) for c in (spec.get("coproducts") or [])])
    return compute_novel_bucket(
        spec=spec, substrate_smiles=substrate_smiles,
        declared_product=str(spec.get("product_smiles") or ""),
        declared_coproducts=coproducts,
        mapping_artifacts=None,
        allow_replay=True)


def classify_bucket_metrics(metrics: dict,
                            spec: dict | None = None) -> dict:
    """**合成/离线**度量 → 分桶判定(与编译链同一 ``_finalize_bucket``)。

    供单测直接构造不可达/合成形态(无锚片段、已知半分子组成、未认领
    移除)验证判定函数;不伪造编译结果,也不进任何在线路径。
    """
    return _finalize_bucket(
        dict(metrics), dict(spec or {}),
        policy_version=NOVEL_BUCKET_POLICY_VERSION,
        table_sha256=NOVEL_BUCKET_TABLE_SHA256)


def _try_compile_fallback_edits(
    *,
    substrate_isomeric: str,
    declared_product: str,
    declared_coproducts: list[str],
    record_id: str,
    fallback_edits: list[dict],
) -> dict | None:
    """P2-2:确定性反推失败时的显式原子编辑兜底核验。

    仅在 ``compile_recorded_reaction`` 确定性反推以 ``compile_unsupported``、
    ``mapping_enumeration_truncated`` 或 ``no_structure_correspondence``
    拒收且调用方提供非空 ``fallback_edits`` 时触发:
    - 经 ``atom_tool.render + validate_edits + execute_edits`` 零妥协执行;
    - 经 ``_evaluate_novel_p1_candidate`` 核验执行组分与声明产物集合一致;
    - 经 ``compute_novel_bucket(..., allow_replay=True)`` 走完全相同的
      方案甲七条件分桶判据。
    """
    from ..services.atom_tool import execute_edits, render, validate_edits
    from .recorded_source import (
        RECORD_SIDE_FORMNORM_PARAM_SHA256,
        RECORD_SIDE_FORMNORM_VERSION,
        _evaluate_novel_p1_candidate,
        _executed_components_strict,
        _strict_of,
        normalize_record_side_transaction,
    )
    from .s5b_compiler import (
        S5B_COMPILER_VERSION,
        _product_components_identity_problem,
        _split_components,
    )

    edits_clean = [dict(e) for e in fallback_edits if isinstance(e, dict)]
    if not edits_clean:
        return None
    try:
        current = render(substrate_isomeric, "S")
        verdict = validate_edits(current, edits_clean)
        if not verdict.get("ok"):
            return None
        execution = execute_edits(current, edits_clean)
        if not execution.get("ok"):
            return None
    except Exception:  # noqa: BLE001
        return None

    donor_to_current: dict[str, str] = {}
    current_to_donor: dict[str, str] = {}
    for idx, atom_id in enumerate(sorted(current.atom_id_map), 1):
        d_id = f"D_{idx}"
        donor_to_current[d_id] = str(atom_id)
        current_to_donor[str(atom_id)] = d_id
    next_map = len(donor_to_current) + 1
    center_current_ids: set[str] = set()
    for ed in edits_clean:
        op = str(ed.get("op") or "")
        if op == _OP_ADD_ATOM:
            new_id = str(ed.get("new_atom_id") or "")
            anchor_id = str(ed.get("atom1") or ed.get("anchor_atom") or "")
            if new_id:
                d_id = f"D_{next_map}"
                next_map += 1
                donor_to_current[d_id] = new_id
                current_to_donor[new_id] = d_id
                center_current_ids.add(new_id)
            if anchor_id:
                center_current_ids.add(anchor_id)
        else:
            for k in ("atom1", "atom2", "atom"):
                aid = str(ed.get(k) or "")
                if aid:
                    center_current_ids.add(aid)
    center_ids = sorted(
        current_to_donor[aid]
        for aid in center_current_ids
        if aid in current_to_donor
    )
    if not center_ids:
        center_ids = sorted(donor_to_current)[:1]
    try:
        principal, coproducts = _split_components(
            execution, current, center_ids, donor_to_current
        )
    except Exception:  # noqa: BLE001
        return None

    target = str(execution["product_smiles"])
    spec_cand = {
        "key": f"rec-{record_id}",
        "product_smiles": principal,
        "coproducts": coproducts,
        "coefficient": 1,
        "transformation_ref": str(record_id),
        "origin_group_key": f"rec-source:{record_id}",
        "edits": edits_clean,
        "donor": {"center_atom_ids": center_ids},
        "alignment": {
            "status": ALIGNMENT_STATUS_RESOLVED,
            "donor_to_current": donor_to_current,
            "equivalence_classes": [],
            "ref": f"fallback-edits:{record_id}",
        },
        "expectation": {"target_smiles": target},
        "compile": {
            "compiler_version": S5B_COMPILER_VERSION,
            "mapping_origin": "fallback_edits",
            "n_alignments_total": 1,
            "n_equivalent_alignments": 1,
            "truncated": False,
        },
    }
    if _product_components_identity_problem(spec_cand) is not None:
        return None

    products_raw = [declared_product, *declared_coproducts]
    formnorm_entries = [
        {
            "side": "lhs",
            "field": "donor_smiles",
            "entry_index": 0,
            "smiles": str(substrate_isomeric),
        }
    ]
    for i, p in enumerate(products_raw):
        formnorm_entries.append(
            {"side": "rhs", "field": "products", "entry_index": i, "smiles": str(p)}
        )
    formnorm_tx = normalize_record_side_transaction(formnorm_entries)
    products_eff = [str(v) for v in formnorm_tx["values"][1:]]

    # 判定纯底物脱落组分(不含新增原子),供 P1-1 编译门对未声明脱落小分子对账
    product_mol = Chem.MolFromSmiles(target)
    exec_id_to_idx = {
        str(k): int(v) for k, v in (execution.get("atom_id_map") or {}).items()
    }
    sub_exec_indices = {
        exec_id_to_idx[aid]
        for aid in (current.atom_id_map or {})
        if aid in exec_id_to_idx
    }
    substrate_only_stricts: list[str] = []
    if product_mol is not None:
        for frag in Chem.GetMolFrags(
            product_mol, asMols=False, sanitizeFrags=False
        ):
            if set(frag) <= sub_exec_indices:
                piece = Chem.MolFromSmiles(
                    Chem.MolFragmentToSmiles(product_mol, list(frag))
                )
                if piece is not None:
                    s_key = _strict_of(Chem.MolToSmiles(piece))
                    if s_key is not None:
                        substrate_only_stricts.append(s_key)

    p1_gate = _evaluate_novel_p1_candidate(
        {"spec": spec_cand},
        products_eff,
        {"removed_component_stricts": []},
        products_raw=products_raw,
    )
    if not p1_gate.get("gate_ok") and substrate_only_stricts:
        # 扣除声明主产物与声明共产物后剩余的纯底物脱落组分
        rem_stricts = list(substrate_only_stricts)
        for decl_s in [_strict_of(p) for p in products_eff]:
            if decl_s is not None and decl_s in rem_stricts:
                rem_stricts.remove(decl_s)
        if rem_stricts:
            p1_gate = _evaluate_novel_p1_candidate(
                {"spec": spec_cand},
                products_eff,
                {"removed_component_stricts": rem_stricts},
                products_raw=products_raw,
            )
    if not p1_gate.get("gate_ok"):
        return None

    return {
        "status": "compiled",
        "spec": spec_cand,
        "novel_p1_gate": p1_gate,
        "n_bond_diff": len(edits_clean),
        "formnorm": {
            "status": str(formnorm_tx["status"]),
            "version": RECORD_SIDE_FORMNORM_VERSION,
            "param_sha256": RECORD_SIDE_FORMNORM_PARAM_SHA256,
            "transaction": formnorm_tx,
            "mapping_artifacts": None,
        },
        "diagnostics": {
            "record_id": record_id,
            "target_smiles": target,
            "fallback_edits_used": True,
        },
        "_allow_replay_bucket": True,
        "_exec_components": _executed_components_strict(target),
    }


def compile_novel_product_first(
    substrate_smiles: str,
    product_smiles: str,
    coproducts: list[str] | None = None,
    proposal_id: str = "",
    *,
    fallback_edits: list[dict] | None = None,
) -> dict:
    """产物优先 novel 提案 → 可执行 spec + 核验分桶（单一构建源）。

    返回两种形态:

    - 编译成功::

        {"status": "compiled", "spec": {...}, "verification_tier":
         "full"|"declared", "bucket_kind": "full"|
         "declared_recognized"|"declared_unrecognized",
         "added_heavy_atoms": n, "removed_heavy_atoms": n,
         "added_fragment_count": n, "net_zero_rewrite": bool,
         "bucket_policy_version": str, "bucket_table_sha256": str,
         "bucket_conditions": {...}, "bucket_reasons": [...],
         "bucket_metrics": {...},
         "principal_reassigned": bool, "principal_reassign_reason": str,
         "declared_product": str, "declared_coproducts": [str],
         "compiled_principal": str, "compiled_coproducts": [str],
         "formnorm_status": str, "formnorm_normalized_products": [str],
         "diagnostics": {...}}

      spec 与池条目同形（product_smiles/coproducts/coefficient/
      transformation_ref/origin_group_key/edits/donor/alignment/
      expectation/compile），另带 ``novel_product_first`` 溯源块；
      ``transformation_ref`` 固定为 ``novel-product-first``。

    - 编译/核验失败::

        {"status": "failed", "failure_kind": <白名单>,
         "feedback": {failure_kind[, executed_components]},
         "diagnostics": {...}}

    主产物重指派（PF11）：声明产物按 **formnorm 归一后的值**做 strict
    身份比对——声明产物是执行组分之一 ⇒ 主产物改为该组分、原主产物
    并入 coproducts（全组分多重集不变，expectation 仍是完整净产物
    集合）；否则保留编译器中心组分并记 ``principal_reassigned=false``
    与原因。
    """
    declared_product = str(product_smiles or "")
    declared_coproducts = [str(c) for c in (coproducts or [])]
    record_id = f"novel-pf:{str(proposal_id or '')}"
    # ---- 声明侧形态预检（不做任何推导；不可解析 ⇒ product_unparseable）----
    if Chem.MolFromSmiles(declared_product) is None:
        return _failure(FAILURE_PRODUCT_UNPARSEABLE,
                        reason="declared_product_unparseable",
                        extra={"declared_product_length":
                               len(declared_product)})
    declared_canon, _declared_components = _single_component(
        declared_product)
    # ---- M1 修复(2026-11-06):底物规范化对齐生产执行器 ----
    # 生产执行器 expand_hypothesis_production 消费 substrate_state.smiles_isomeric
    # (= strict_identity_of 同源规范化 CXSMILES 身份键);编译前先用同一函数
    # 规范化底物串,消除非 canonical 输入写法引起的原子序漂移(M1)。
    # 底物不可解析或未过 CX 守卫 ⇒ fail-closed 结构化失败返回(不抛未捕获异常)。
    try:
        substrate_isomeric = strict_identity_of(str(substrate_smiles or ""))
    except ChemicalStateError as exc:
        kind = str((getattr(exc, "detail", {}) or {}).get("kind") or "")
        return _failure(
            FAILURE_COMPILE_UNSUPPORTED,
            reason=kind or "substrate_unparseable",
            extra={"raised": type(exc).__name__})
    try:
        compiled = compile_recorded_reaction(
            substrate_smiles=substrate_isomeric,
            donor_smiles=substrate_isomeric,
            products=[declared_product, *declared_coproducts],
            record_id=record_id,
            formnorm_source_ref={
                "channel": "novel_product_first",
                "asset_sha256": "",
                "record_key": record_id,
                "matched_side_or_component": {"novel_product_first": True},
            },
            novel_product_first_principal=declared_product,
        )
        if str(compiled.get("status")) != "compiled" and declared_coproducts:
            from .recorded_source import _is_co2_or_formate_smiles

            co2_cops = [
                c for c in declared_coproducts if _is_co2_or_formate_smiles(c)
            ]
            other_cops = [
                c for c in declared_coproducts
                if not _is_co2_or_formate_smiles(c)
            ]
            if co2_cops:
                alt = compile_recorded_reaction(
                    substrate_smiles=substrate_isomeric,
                    donor_smiles=substrate_isomeric,
                    products=[declared_product, *other_cops],
                    record_id=record_id,
                    formnorm_source_ref={
                        "channel": "novel_product_first",
                        "asset_sha256": "",
                        "record_key": record_id,
                        "matched_side_or_component": {
                            "novel_product_first": True
                        },
                    },
                    novel_product_first_principal=declared_product,
                )
                alt_gate = dict(alt.get("novel_p1_gate") or {})
                alt_undec = list(alt_gate.get("undeclared_coproducts") or [])
                alt_co2 = [
                    u for u in alt_undec if _is_co2_or_formate_smiles(u)
                ]
                if (
                    str(alt.get("status")) == "compiled"
                    and len(alt_co2) >= len(co2_cops)
                ):
                    claimed: list[str] = []
                    rem_undec: list[str] = []
                    for u in alt_undec:
                        if (
                            len(claimed) < len(co2_cops)
                            and _is_co2_or_formate_smiles(u)
                        ):
                            claimed.append(u)
                        else:
                            rem_undec.append(u)
                    alt_gate["compiled_coproducts"] = (
                        list(alt_gate.get("compiled_coproducts") or [])
                        + claimed
                    )
                    alt_gate["undeclared_coproducts"] = rem_undec
                    alt["novel_p1_gate"] = alt_gate
                    compiled = alt
    except RecordedSourceError as exc:
        kind = str((getattr(exc, "detail", {}) or {}).get("kind") or "")
        mapped = (FAILURE_PRODUCT_UNPARSEABLE if kind in _UNPARSEABLE_REASONS
                  else FAILURE_COMPILE_UNSUPPORTED)
        return _failure(mapped, reason=kind or "record_side_unparseable",
                        extra={"raised": type(exc).__name__})
    except S5bCompileError as exc:
        return _failure(FAILURE_COMPILE_UNSUPPORTED,
                        reason=str((getattr(exc, "detail", {}) or {}).get(
                            "kind") or getattr(exc, "kind", "")
                            or "compile_internal_error"),
                        extra={"raised": type(exc).__name__})
    if str(compiled.get("status")) != "compiled":
        reason = str(compiled.get("reason") or "")
        detail = dict(compiled.get("detail") or {})
        executed = (detail.get("executed_components")
                    or detail.get("executed_union_declared_components")
                    or [])
        failure_kind = _map_unsupported(reason)
        if fallback_edits and failure_kind in (
            FAILURE_COMPILE_UNSUPPORTED,
            FAILURE_MAPPING_ENUMERATION_TRUNCATED,
            FAILURE_NO_STRUCTURE_CORRESPONDENCE,
        ):
            fb_compiled = _try_compile_fallback_edits(
                substrate_isomeric=substrate_isomeric,
                declared_product=declared_product,
                declared_coproducts=declared_coproducts,
                record_id=record_id,
                fallback_edits=fallback_edits,
            )
            if fb_compiled is not None:
                compiled = fb_compiled
        if str(compiled.get("status")) != "compiled":
            return _failure(failure_kind, reason=reason,
                            executed_components=[str(x) for x in executed],
                            extra={"all_reasons":
                                   list(detail.get("all_reasons") or [])[:8]})
    spec = dict(compiled.get("spec") or {})
    formnorm = dict(compiled.get("formnorm") or {})
    tx = dict(formnorm.get("transaction") or {})
    tx_values = [str(v) for v in (tx.get("values") or [])]
    # formnorm 事务顺序 = [donor, products...]；归一后的声明产物值
    declared_eff = (tx_values[1] if len(tx_values) > 1
                    else declared_product)
    compiled_principal = str(spec.get("product_smiles") or "")
    compiled_coproducts = [str(c) for c in (spec.get("coproducts") or [])]
    parts = [compiled_principal, *compiled_coproducts]
    # ---- 全组分多重集自洽门（重指派只换角色，不增删组分）----
    target = str((spec.get("expectation") or {}).get("target_smiles") or "")
    _target_single, target_components = _single_component(target)
    if sorted(filter(None, (_strict_key(p) for p in parts))) != \
            sorted(filter(None, (_strict_key(p) for p in target_components))):
        return _failure(
            FAILURE_COMPILE_UNSUPPORTED,
            reason=_PRINCIPAL_REASON_COMPONENT_MULTISET_MISMATCH,
            extra={"compiled_parts": parts[:8],
                   "target_components": target_components[:8]})
    # ---- 主产物重指派（PF11）与 P1-1 未声明脱落碎片分流 ----
    p1_gate = dict(compiled.get("novel_p1_gate") or {})
    undeclared_coproducts = [
        str(c) for c in (p1_gate.get("undeclared_coproducts") or [])
    ]
    if p1_gate and (
        undeclared_coproducts
        or sorted(
            filter(
                None,
                (_strict_key(c) for c in (p1_gate.get("compiled_coproducts") or [])),
            )
        )
        != sorted(filter(None, (_strict_key(c) for c in declared_coproducts)))
    ):
        compiled_principal = str(p1_gate["compiled_principal"])
        compiled_coproducts = [
            str(c) for c in (p1_gate.get("compiled_coproducts") or [])
        ]
        principal_reassigned = _strict_key(parts[0]) != _strict_key(
            compiled_principal
        )
        reassign_reason = ""
        spec["product_smiles"] = compiled_principal
        spec["coproducts"] = list(compiled_coproducts)
        if undeclared_coproducts:
            spec["undeclared_coproducts"] = list(undeclared_coproducts)
    else:
        principal_reassigned, reassign_reason, declared_component = \
            _reassign_principal_components(parts, declared_eff)
        if principal_reassigned:
            idx = parts.index(declared_component)
            spec["product_smiles"] = parts[idx]
            spec["coproducts"] = [parts[0]] + parts[1:idx] + parts[idx + 1:]
            compiled_principal = parts[idx]
            compiled_coproducts = list(spec["coproducts"])
    # ---- 方案甲分桶（七条件;单一函数;三臂同口径）----
    # R2 P1-4:``mapping_artifacts`` **原样**传入(不把缺失/空值折成 None
    # 再走 A 重放)。B/C 路径不传 ``allow_replay``,故 formnorm 缺该键 /
    # 空 dict / 非 dict ⇒ declared_unrecognized + mapping_artifacts_missing
    # (或 _unparseable),禁止静默 full。
    bucket = compute_novel_bucket(
        spec=spec, substrate_smiles=substrate_isomeric,
        declared_product=declared_product,
        declared_coproducts=declared_coproducts,
        mapping_artifacts=formnorm.get("mapping_artifacts"),
        allow_replay=bool(compiled.get("_allow_replay_bucket")))
    tier = str(bucket["verification_tier"])
    metrics = dict(bucket.get("metrics") or {})
    # 产物优先 spec 溯源（进 action payload/审计；不含金标/题面）
    spec["transformation_ref"] = PRODUCT_FIRST_TRANSFORMATION_REF
    spec["novel_product_first"] = {
        "version": "novel-product-first-2",
        "proposal_id": str(proposal_id or ""),
        "declared_product": declared_product,
        "declared_coproducts": declared_coproducts,
        "compiled_principal": compiled_principal,
        "compiled_coproducts": compiled_coproducts,
        "verification_tier": tier,
        "bucket_kind": str(bucket["bucket_kind"]),
        "added_heavy_atoms": int(metrics.get("added_heavy_atoms")
                                 if metrics.get("available") else -1),
        "removed_heavy_atoms": int(metrics.get("removed_heavy_atoms")
                                   if metrics.get("available") else -1),
        "added_fragment_count": int(metrics.get("added_fragment_count")
                                    if metrics.get("available") else -1),
        "net_zero_rewrite": bool(bucket.get("net_zero_rewrite")),
        "bucket_policy_version": str(bucket["policy_version"]),
        "bucket_table_sha256": str(bucket["table_sha256"]),
        "bucket_reasons": list(bucket.get("reasons") or []),
        "principal_reassigned": principal_reassigned,
        "principal_reassign_reason": reassign_reason,
        "record_side_form_norm": str(formnorm.get("status") or "unknown"),
        "compiler_mapping_origin": str(
            (spec.get("compile") or {}).get("mapping_origin") or ""),
    }
    return {
        "status": "compiled",
        "spec": spec,
        "verification_tier": tier,
        "bucket_kind": str(bucket["bucket_kind"]),
        # 方案甲字段的短名别名(与 bucket_* 同值;派工单字段名对齐)
        "metrics": metrics,
        "reasons": list(bucket.get("reasons") or []),
        "policy_version": str(bucket["policy_version"]),
        "added_heavy_atoms": int(
            metrics.get("added_heavy_atoms")
            if metrics.get("available") else -1),
        "removed_heavy_atoms": int(
            metrics.get("removed_heavy_atoms")
            if metrics.get("available") else -1),
        "added_fragment_count": int(
            metrics.get("added_fragment_count")
            if metrics.get("available") else -1),
        "net_zero_rewrite": bool(bucket.get("net_zero_rewrite")),
        "bucket_policy_version": str(bucket["policy_version"]),
        "bucket_table_sha256": str(bucket["table_sha256"]),
        "bucket_conditions": dict(bucket.get("conditions") or {}),
        "bucket_reasons": list(bucket.get("reasons") or []),
        "bucket_metrics": metrics,
        "principal_reassigned": principal_reassigned,
        "principal_reassign_reason": reassign_reason,
        "declared_product": declared_product,
        "declared_coproducts": declared_coproducts,
        "declared_product_normalized": declared_eff,
        "compiled_principal": compiled_principal,
        "compiled_coproducts": compiled_coproducts,
        "formnorm_status": str(formnorm.get("status") or "unknown"),
        "formnorm_normalized_products": tx_values[1:],
        "diagnostics": {
            "record_id": record_id,
            "n_bond_diff": int(compiled.get("n_bond_diff") or 0),
            "compile_diagnostics": dict(compiled.get("diagnostics") or {}),
        },
    }


__all__ = [
    "ADDED_HEAVY_ATOMS_BACKSTOP",
    "REMOVED_HEAVY_ATOMS_BACKSTOP",
    "MAX_ADDED_FRAGMENTS",
    "MAX_ADDED_HEAVY_ATOMS_MAIN",
    "NOVEL_BUCKET_POLICY_VERSION",
    "NOVEL_BUCKET_TABLE_SHA256",
    "ADDED_FRAGMENT_WHITELIST",
    "LEAVING_GROUP_WHITELIST",
    "KNOWN_MOIETY_TABLE",
    "PRODUCT_ELEMENT_DOMAIN",
    "PRODUCT_FIRST_TRANSFORMATION_REF",
    "VERIFICATION_TIER_FULL",
    "VERIFICATION_TIER_DECLARED",
    "VERIFICATION_TIERS",
    "BUCKET_KIND_FULL",
    "BUCKET_KIND_DECLARED_RECOGNIZED",
    "BUCKET_KIND_DECLARED_UNRECOGNIZED",
    "BUCKET_KINDS",
    "FAILURE_PRODUCT_UNPARSEABLE",
    "FAILURE_NO_STRUCTURE_CORRESPONDENCE",
    "FAILURE_MAPPING_ENUMERATION_TRUNCATED",
    "FAILURE_AMBIGUOUS_MAPPING",
    "FAILURE_PRODUCT_SET_MISMATCH",
    "FAILURE_COMPILE_UNSUPPORTED",
    "NOVEL_VERIFICATION_FAILURE_KINDS",
    "compute_novel_bucket",
    "compute_arm_a_bucket_readout",
    "classify_bucket_metrics",
    "compile_novel_product_first",
]