# 化学评审请求 r33 —— v4b stereo 消解实施采纳核对（短轮）

> 触发点：AGENTS.md 通道 A（v4b 回修轮化学面采纳核对；零金标零题面，
> 规则级自包含）。上游：你 r28 回应的 E1-E3（stereo 消解设计评审）。
> 本请求只核对实施是否忠实你 r28 的条件。

## 实施自报（commit 9a0a60ea，请读码核对）

消解谓词四条件（s5b_compiler.py 模块头 §W-V4b 注释与你 r28 条款对照）：
1. lhs 原子 CHI_TETRAHEDRAL_CW/CCW ∧ rhs 无手性声明（CHI_UNSPECIFIED）；
2. 该原子全部 lhs 键均单键（sp3；双键/累积烯中央原子天然不满足 ⇒
   非四面体轴手性不消解）；
3. 该原子涉及的键变化全部为 change_bond_order single→double/triple
   （无 form/break/芳香——键表顺序不变，CW/CCW 标签无重解读风险）；
4. 至少一个该型变化。
反例族全拒：stereo_created / 仍四面体中心的断成键（有机磷硫水解、
SN2 配体交换）/ 非四面体标签 / 纯立体翻转——一律维持
stereo_edit_unsupported。执行后 rhs 立体同源复核（不等 ⇒ 
stereo_derived_mismatch 结构化拒）；spec 机读诊断
stereo_dissolution_applied:maps；E/Z 不在放行面也不在拒面（原子
四面体检测面；执行产物 E/Z 未指派对声明 E/Z 参考走 cn_only 如实
miss）。

## 评审问题（S1-S3 逐条）

- S1：四条件谓词是否完整覆盖你 r28 E1-E3 的边界（漏了哪个反例族？
  E/Z 处置是否与你的"两头如实"预期一致？）
- S2：执行后同源复核（stereo_derived_mismatch）作为机读强制是否
  达到你 E2-③ 的要求（"消解后仍为立体中心不放行"是否被该复核
  隐式覆盖，还是需显式断言？）
- S3：诚实披露核对：本轮消解只恢复 1 题（bt0002#r0032 非手性底物
  1-苯乙醇→苯乙酮 cn 层）+ 24 stereo_created 维持拒 + 8 翻转维持
  + 5 显式氢价态墙（execution 诚实拒）——该分解与你 r28 E1-1 的
  预警（立体创建/非四面体是主流不可修面）是否一致？有无你认为
  应修而未修的类？

## 回复格式

S1-S3 逐条一句话结论+展开；总判定（采纳成立/有条件+条件）；不确定
写不确定。你只读评审（可用读取工具，变更集中在
src/pathway_v43/pollutant/{s5b_compiler,recorded_source}.py）。
