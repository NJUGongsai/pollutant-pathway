"""PPV1 受控词表单一来源(老师提效包 F3;零模型/零行为变化)。

背景(57ea99b4 aromatic 事故,2026-10-09):S5b 应急提示词手写键级词表
"single|double|triple|aromatic",而执行器 ``_BOND_TOKENS`` 只认凯库勒
三词(single/double/triple);模型按提示词规范输出 ``to_order=aromatic``,
执行器 ``_BOND_TOKENS[to]`` 抛 KeyError 整题崩溃(RXNG_22901c/
RXNG_330df2,chenyu 冒烟 2/10)。根因是**提示词词表与执行器词表
两处手写、无同步机制**。本模块即防再犯的"单一来源":

- 全部受控词表从**执行器/权威模块既有常量导入**并集合化(零复制、
  零新事实、零行为变化;只是搬运与别名);
- 提示词的词表声明段(real_model `_PROPOSALS_SYSTEM_PROMPT`)改为由
  本模块拼接生成——渲染字节不变,PROPOSALS_PROMPT_VERSION 内容哈希
  不变(基线 8da11cb7 冻结值,见 tests/test_controlled_vocab_ci.py
  的哈希稳定断言),批身份/批 resume 语义零影响;
- CI 双向断言族见 tests/test_controlled_vocab_ci.py(提示词提取 ↔
  执行器词表双向 diff + 漂移注入复现 + 字面量消费点过期检测)。

词表权威一览(单一来源;本模块只做导入/集合化,不发明新值):

| 族 | 权威模块 | 提示词面 | 备注 |
| EDIT_OPS / EDIT_OP_FIELDS | services.atom_tool(执行器) | real_model 契约段(生成) | 编辑四操作 |
| BOND_ORDER_TOKENS | services.atom_tool ``_BOND_TOKENS`` | real_model 契约段(生成) | 凯库勒键级三词 |
| GRAPH_ORDER_AROMATIC | real_model execution_graph 图事实词 | 不入 edits 词表 | 只读图描述,非可编辑词 |
| ACTION/ATTEMPT_STATUSES | search(队列/尝试状态机) | 不入提示词(内部) | 豁免登记 |
| EXPANSION_STATUSES | events(展开计划) | 不入提示词(事件载荷契约) | + plan_status=incomplete |
| DEFERRED_TYPES | queue(deferred 两类) | 不入提示词(内部) | 豁免登记 |
| PROVIDER_KINDS | search(model 请求通道) | 不入提示词(内部) | 豁免登记 |
| PARTICIPANT_SIDES/ROLES | hypothesis(参与物侧别/角色) | 不入提示词(内部) | 字面量消费点散落 |
| OUTPUT_ORIGINS | 本模块首次常量化 | real_model 契约段(生成) | 原为提示词+runflow 两处字面量 |
| ALIGNMENT_STATUSES | audit 校验值域(原字面量) | real_model 契约段示范 resolved | ambiguous/unavailable 不入提示词 |
| PRODUCTION_REPORT_STATUSES | production._report 取值域 | 不入提示词(内部) | runflow 消费 deferred |

范围纪律(任务书 F3):
- 只做"单一来源 + CI 断言",不改任何执行器/判据/scorer 行为语义;
- 未在本轮常量化的散落字面量(runflow/store/audit/s5b_compiler 等
  消费点)不改源码(避免与并行会话冲突),由 CI 的 ast 源码扫描
  断言覆盖:消费方源码中出现的受控词字面量必须仍在权威词表内
  (权威改值 ⇒ 旧字面量过期 ⇒ CI 红,即字面量过期检测);
- 金标/题面/封存 run 零触碰;零模型零网络零花费。
"""

from __future__ import annotations

# ---- A. 编辑协议(权威 = services/atom_tool 执行器常量,直接别名) ----
# 顺序契约:EDIT_OPS 的 tuple 顺序即提示词契约段渲染顺序(内容身份的
# 一部分);执行器重排/增删 ⇒ 提示词字节或集合断言变化 ⇒ CI 红,
# 显式走 PROPOSALS_PROMPT_VERSION 升版流程,不静默漂移。
from ..services.atom_tool import (  # noqa: F401  (re-export 单一来源)
    _BOND_ORDER_N,
    _BOND_TOKENS,
    _EDIT_OP_FIELDS,
    _EDIT_OPS,
)

EDIT_OPS = _EDIT_OPS
EDIT_OP_FIELDS = _EDIT_OP_FIELDS
# 保序键级词表(single/double/triple;dict 定义序 = 提示词渲染序)
BOND_ORDER_TOKENS = tuple(_BOND_TOKENS)
BOND_ORDER_N = _BOND_ORDER_N
# 提示词契约段/执行器校验共用的枚举声明串("single|double|triple")
BOND_ORDER_ALTERNATION = "|".join(BOND_ORDER_TOKENS)

# 编辑协议 v2 严格面不认的旧词(atom_tool validate_edits/execute_edits:
# 严格四操作,旧别名一律 unknown_op 稳定拒因;remove_atom 已废除)。
# 注意:atom_tool 的旧引用核验入口 check_edit_references(Phase B 宽
# 松形状)代码里仍宽松接受 remove_bond/add_bond —— 两属不同入口面;
# 本清单锚定**提示词面**:提示词出现任一 ⇒ CI 红(提示词教模型用 v2
# 协议面会拒的词,即 aromatic 事故同型:声明位教坏词,模型照写,执行
# 侧整题拒/崩)。
RETIRED_EDIT_OPS = frozenset({"remove_atom", "remove_bond", "add_bond"})

# ---- B. 图事实词(execution_graph 键级描述;只读非可编辑) ----
# execution_graph.bonds[].order 的 fallback:芳香键如实描述为
# "aromatic"(只读事实,告知模型当前键况);edits 的 from_order/
# to_order(可编辑受控词)恒 ≠ 该词 —— 两属不同协议面,CI 断言
# 提示词 edits 词表不得混入(57ea99b4 根因即两面混写)。
GRAPH_ORDER_AROMATIC = "aromatic"
# execution_graph 键级事实词域 = 凯库勒三词 + aromatic(只读)
GRAPH_ORDER_FACT_TOKENS = frozenset(BOND_ORDER_TOKENS) | {
    GRAPH_ORDER_AROMATIC}

# ---- C. 队列/尝试状态机(权威 = search;不入提示词,豁免登记) ----
from .search import (  # noqa: F401
    ACTION_STATUS_BLOCKED,
    ACTION_STATUS_CLAIMED,
    ACTION_STATUS_DEFERRED,
    ACTION_STATUS_DONE,
    ACTION_STATUS_PENDING,
    ATTEMPT_STATUS_ABANDONED,
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_OPEN,
    ATTEMPT_STATUS_RECORDED,
    PROVIDER_KIND_FAKE,
    PROVIDER_KIND_REAL,
    PROVIDER_KIND_SCRIPTED,
    PROVIDER_KINDS,
)

ACTION_STATUSES = frozenset({
    ACTION_STATUS_PENDING, ACTION_STATUS_CLAIMED, ACTION_STATUS_DONE,
    ACTION_STATUS_DEFERRED, ACTION_STATUS_BLOCKED,
})
ATTEMPT_STATUSES = frozenset({
    ATTEMPT_STATUS_OPEN, ATTEMPT_STATUS_RECORDED, ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_ABANDONED,
})

# ---- D. 展开计划状态(权威 = events;事件载荷契约,不入提示词) ----
from .events import (  # noqa: F401
    EXPANSION_STATUS_DEFERRED,
    EXPANSION_STATUS_EXPANDED,
    EXPANSION_STATUS_NOT_TRACKED,
    EXPANSION_STATUSES,
)

# plan_status 的显式不完整声明(store 校验;原为字面量,首次常量化,
# 值不变;CI 扫描锚定 store 消费点字面量 == 本常量)
PLAN_STATUS_INCOMPLETE = "incomplete"

# ---- E. deferred 两类(权威 = queue;不入提示词,豁免登记) ----
from .queue import (  # noqa: F401
    DEFERRED_TYPE_ALTERNATIVE,
    DEFERRED_TYPE_COPRODUCT,
    DEFERRED_TYPES,
)

# ---- F. 参与物侧别/角色(权威 = hypothesis;字面量消费点散落见
# runflow/store/audit/s5b_scoring/recorded_source,CI 扫描覆盖) ----
from .hypothesis import (  # noqa: F401
    PARTICIPANT_ROLE_COPRODUCT,
    PARTICIPANT_ROLE_COSUBSTRATE,
    PARTICIPANT_ROLE_PRIMARY_SUBSTRATE,
    PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
    PARTICIPANT_ROLE_UNKNOWN,
    PARTICIPANT_ROLES,
    PARTICIPANT_SIDE_PRODUCT,
    PARTICIPANT_SIDE_REACTANT,
    PARTICIPANT_SIDES,
)

# ---- G. output_origin(原无常量:提示词契约段 + runflow 默认两处
# 字面量;本模块首次常量化,值不变;提示词改为引用,runflow 不改
# 源码由 CI 扫描锚定) ----
OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL = "novel_outside_pool"
OUTPUT_ORIGINS = frozenset({OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL})

# ---- H. alignment 状态(权威 = audit 校验值域;原为 audit 函数内
# 字面量 tuple,首次常量化,值不变;audit/s5b_compiler 不改源码由
# CI 扫描锚定。提示词契约段示范 resolved;ambiguous/unavailable
# 是审计判定值,不入提示词——CI 豁免登记) ----
ALIGNMENT_STATUS_RESOLVED = "resolved"
ALIGNMENT_STATUS_AMBIGUOUS = "ambiguous"
ALIGNMENT_STATUS_UNAVAILABLE = "unavailable"
ALIGNMENT_STATUSES = frozenset({
    ALIGNMENT_STATUS_RESOLVED, ALIGNMENT_STATUS_AMBIGUOUS,
    ALIGNMENT_STATUS_UNAVAILABLE,
})

# ---- I. 生产报告状态(production._report 取值域;runflow 消费
# deferred/rejected/submitted,CI 扫描锚定;不入提示词) ----
PRODUCTION_REPORT_STATUS_METHOD_FAILED = "method_failed"
PRODUCTION_REPORT_STATUS_DEFERRED = "deferred"
PRODUCTION_REPORT_STATUS_REJECTED = "rejected"
PRODUCTION_REPORT_STATUS_SUBMITTED = "submitted"
PRODUCTION_REPORT_STATUSES = frozenset({
    PRODUCTION_REPORT_STATUS_METHOD_FAILED,
    PRODUCTION_REPORT_STATUS_DEFERRED,
    PRODUCTION_REPORT_STATUS_REJECTED,
    PRODUCTION_REPORT_STATUS_SUBMITTED,
})

# ---- 汇总:内部词表(不入提示词的族;CI 反向断言的豁免登记面) ----
# 这些族的词只进内部状态机/事件载荷/审计,不进模型提示词 —— 提示词
# 出现任一 ⇒ CI 红(提示词不该教模型这些内部词)。
INTERNAL_ONLY_VOCABS: dict[str, frozenset[str]] = {
    "ACTION_STATUSES": ACTION_STATUSES,
    "ATTEMPT_STATUSES": ATTEMPT_STATUSES,
    "EXPANSION_STATUSES": EXPANSION_STATUSES,
    "PLAN_STATUS": frozenset({PLAN_STATUS_INCOMPLETE}),
    "DEFERRED_TYPES": DEFERRED_TYPES,
    "PROVIDER_KINDS": PROVIDER_KINDS,
    "PARTICIPANT_SIDES": PARTICIPANT_SIDES,
    "PARTICIPANT_ROLES": PARTICIPANT_ROLES,
    "PRODUCTION_REPORT_STATUSES": PRODUCTION_REPORT_STATUSES,
}
