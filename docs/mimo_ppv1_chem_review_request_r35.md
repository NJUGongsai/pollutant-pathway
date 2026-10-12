# 化学评审请求 r35 —— chain12 298 批次结果化学复核（场景 3，跑分后）

> 触发点：AGENTS.md 三触发点之 3（出题后对答题结果：跑分/终测后的结果化学复核，后置，不改已冻结判定）。上游：你 r33（hwall 采纳条件三条）、r34（D2 共底物实施采纳）。证据基础：对账报告 docs/S5B_CHAIN11_TO_CHAIN12_RECON_2026-10-12.md（含六张表与归因指纹）。
> 题域标签：**298 / RHEA 通用酶学 / 已见题**，已知证据重建，不外推。
> 零金标：本请求只含聚合计数与规则级机制描述；判分报告（reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/report.md）仅含计数不露金标结构，可读；金标文件（reference_graphs/）本地不存在且不许读。

## 结果自报（可读码与判分报告核对）

**批次构成（多因子，如实声明）**：chain11（10-10 发车，compiler s5b-compiler-1）→ chain12（10-12 发车，compiler s5b-compiler-3）之间变化不只有 D2+hwall，还含 v4b 立体消解/推断映射深层门/诚实计量线、D2-R1/R2/R3、AtomTool-2（hwall，v43-atomtool-1→2）、F3 词表 CI。两链各自独立真实调模型（候选集非配对固定），归因混采样方差——以下是指纹证据不是配对实验。

**判分（严格口径，分母固定 298，判分零 LLM）**：hit@1/3/5 = 92/126/130；U(strict)=130、H5=130、L=0；分桶 strict 130 / partial 43 / uncovered 125。对比 chain11：76/101/103、106/37/155。

**迁移**：hit@1 保留 62 / 新增 30 / 退步 14；35 道新 strict 中 hwall 间接指纹 20 道（c11 同题 AtomValenceException 在 c12 消失，全库 52→16 题）、D2 直接指纹（declared_copy_components）**0 道**。

**hwall 机制回顾（r33 你附条件采纳）**：execute_edits 的 change_bond_order 分支在键级升高时，对变化键两端点的括号显式氢（numExplicitHs，noImplicit 记账）按级差消耗、存量不足截 0——脱氢记账语义；边界负控：真实超价仍拒（clamp/季碳无 H/form_bond/醚 O）、图中独立 H 原子含同位素 [2H] 不在放宽面。深查样例：苯甲醇类 C–O single→double（醇→酮/醛氧化）在 c11 sanitize_failed、c12 编译成功排 rank1。

**D2 双刃发现**：c12 全库 13 道 declared_copy_components 题零道进 strict，且 3 道旧 strict 被拉成 partial、14 道 hit@1 退步中 4 道带 D2 指纹。机制：事件诚实保留共底物 B 参与物与声明式拷贝产物后，参考为 root-only 视图时参与物覆盖变 superset ⇒ 按冻结判分规则判 partial。与 D2 设计书"诚实拷贝型候选主要贡献 partial"预期一致，量化首次落地。

## 评审问题（M1–M5 逐条）

- **M1（hwall 新命中的化学合法性）**：20 道带 hwall 指纹的新 strict 主通道为键级升高类（醇→酮/醛氧化等）。从化学面看，"括号显式氢按级差消耗"的记账语义放开的这类编译，是否存在"记账上通了但化学上不该通"的边界情形（如本不该脱氢的位点、互变异构、芳香体系被部分打断）？
- **M2（hwall 边界钉得够不够）**：现行负控族（真实超价拒/季碳无 H/form_bond 不放宽/独立 H 原子含同位素/醚 O 非氢价态）在化学上是否足以钉死放宽面？你认为还有哪类结构应补负控？
- **M3（D2 双刃的判分立场）**：来源 A+B→多产物、事件诚实保留 B 与拷贝产物、参考 root-only ⇒ superset ⇒ partial（"诚实=partial"）。从化学评审立场：这个立场是否正确且应维持（vs 生成侧删共底物换 strict）？与你在 r32/r34 认可的 T1′（产物侧辅因子恒不忽略）与 NC-12（本通道 matched_strict 恒 0 熔断）一致性如何？
- **M4（退步的化学解读方向）**：14 道退步中 4 道带 D2 指纹（3 道→partial 与 superset 机制一致）、1 道 c12 出现 valence 异常、其余掉位。从化学面看，这些退步更可能是候选/排序方差还是语义变化副作用？（只问解读方向，不改已冻结判定。）
- **M5（总判定）**：chain12 的 92/130 结果在化学面上有无红旗——应视为可疑/无效的命中类？复核结论对下一轮（125 uncovered 供给线、43 partial 细分、38 题后位答案重排）有无化学侧优先级建议？

## 回复格式

M1–M5 逐条一句话结论+展开；不确定写不确定+缺什么证据；执行类断言标"待执行验证"；不修改任何文件。你只读评审：可读 docs/S5B_CHAIN11_TO_CHAIN12_RECON_2026-10-12.md、判分报告 report.md、源码 src/pathway_v43/services/atom_tool.py 与 src/pathway_v43/pollutant/{recorded_source,production}.py；不得读取金标/题面文件；本请求复核为后置，不改已冻结判定，采纳走下一轮预注册。
