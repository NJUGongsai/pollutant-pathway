# M4-A — enviPath 显式 [H] → 隐式 H 重编码（hfix）

把 `reaction_v3/data/lib_envipath/templates.tsv.gz` 的 286 条 SMIRKS 中、以显式氢原子
`[H]` / `[#1]` / `[H:n]` 写在反应物/产物模式里的规则，重编码为隐式 H，使 RDKit SMARTS
能匹配隐式 H 的 SMILES 底物，同时保留迁移变换（round-trip 保真）。owner: CC。

## 根因
RDKit SMARTS `[#6][H]` 表示“碳上连着显式氢原子”，而 SMILES 是隐式 H，二者不匹配。
实测 `[#6][H]` 匹配 `CCO` = 0 次；`[#6]` = 2 次。

## 方法（保真）
对含显式 H 的 SMIRKS（educt>>product 两侧同步）：
1. 未映射 spectator/leaving `[H]`：删除该 `[H]` 节点与其键。
2. 带 map 的 `[H:n]`（H 原子参与迁移）：在两侧同步删除，H 计数交由 RDKit 隐式处理。
   铁则：同 map 号两侧同步删，保持 atom-map 对齐。
实现走 RDKit `ReactionFromSmarts` 取两侧 mol → 遍历删原子序 1 原子 → `MolToSmarts` 回写，
不用文本正则（见 `reencode.py`）。

## 产物（本目录）
- `templates_implicitH.jsonl` — 286 条（226 条改写 + 60 条不变），含 lhs/rhs 显式 H 与 mapped H 计数。
- `match_report.json` — 匹配解锁前/后（donor 级 + 跨 83 parent 级）。
- `roundtrip_report.json` — round-trip canary（reference = 原 SMIRKS 施于 AddHs(donor)；candidate = 重编码 SMIRKS 施于隐式 donor；fidelity = reference 产物 ⊆ candidate 产物）。
- `candidates_hfix.json` — 286 条重编码规则施于 83 parents 的候选并集，旧池 union 来自
  `reaction_analogy/data/retrieval_v1/queries.jsonl`（RA-M1 候选池，为“含旧池 union”所需）。
- `test_hfix.py` — RED→GREEN 测试。
- `reencode.py` / `run_hfix.py` — 核心逻辑与编排脚本。

## 关键结果
- 匹配解锁（donor 级，143 条有 donor 的规则）：**52 → 137**。
- 匹配解锁（跨 83 parent 的规则数）：**36 → 109**；覆盖 parent：**50 → 80 / 83**。
- round-trip canary（checked 对）：447/528 保真（ok+ok_extra），84.7%。

## 已知边界（fail-closed，正文可查 roundtrip_report.json）
1. `orig_no_match`（67 对）：原规则即使对显式化氢的 donor 也匹配不上（芳香/kekulé、电荷、
   链长等先验阻抗，非重编码引入）。
2. `residual_H_query`（48 对）：反应物仍含 `[#1,...]` 列表元素或递归 `$(...[H])`，此类
   氢查询无法匹配隐式 H（与 H 节点删除正交的独立隐患，不在本棒范围）。
3. `reencode_gen_failure`（33 对，8 条规则）：(a) RDKit RunReactants 在反应中心上的
   隐式 H/手性 stereo 交互；(b) 脱烷基/去甲基化中 mapped-H 氢迁移语义需显式 Hn 等价表达。
   失败产物被 drop（fail-closed），绝不输出错误价态产物。

## 铁律
fail-closed；RED→GREEN；确定性双跑（已字节一致）+ MANIFEST；答案隔离（未读 restricted
answer key，未 import route_a_audit/recall.py）；工作区 commit 不 push。