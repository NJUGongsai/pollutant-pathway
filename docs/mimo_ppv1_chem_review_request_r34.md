# 化学评审请求 r34 —— D2 共底物参与物语义实施采纳核对（场景 1，判据冻结前）

> 触发点：AGENTS.md 通道 A。上游：你 r32（设计轮 16 条条件）与设计书
> docs/S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md（§12
> T-1~T-5 处置记录）。本请求核对 D2 编译实施是否忠实设计与你 r32 的
> 条件。零金标零题面，规则级自包含。

## 实施自报（commit 2e679b31，请读码核对）

- 三分类守门（recorded_source._classify_cosubstrate_candidate，**编译器内部规则不进事件协议**——选项 b 降级为守门基底层按设计书执行）：component 候选三分支——整组分拷贝子集有条件放行（22 spec/15 题，1.7%）、键合融合保守拒（984，74.4%）、不可归属保守拒（22）
- 方案 a 事件表示：B 进反应物侧参与物（role=cosubstrate/系数 unknown）、B 来源整组分产物**声明式拷贝**（不执行、中心 unknown、来源字段完整）——事件装配 _attach_cosubstrate_spec_fields + production.prepare_hypothesis 扩
- union gate：compile_recorded_reaction 可选参数（缺省 None ⇒ EAWAG 字节等价；strict_identity_of 键空间统一+一致性披露+declared_copy_mismatch 拒因）
- NC-10 事件级不变量（production._check_cosubstrate_event_invariant，提交前）：记录全部共底物 ⊆ 事件 reactant cosubstrate state_refs ∧ 记录产物多重集 == 事件产物参与物多重集（执行 ∪ 拷贝）
- NC-12 批级熔断：e2e 断言本通道 matched_strict == 0
- CS2c 披露表：corpus 面键合拒/诚实 partial vs EAWAG 面 68 隐式书写形态（照旧 add_atom 可 strict）两面并列；记录写了水 118 题
- T1′ 三条落字 + r32 十六条落字（交付书 §对应节）；版本 corpus-retrieval-3/recorded-source-3/pool-policy-5

## 评审问题（D1-D6 逐条）

- D1（三分类守门）：原子归属三分类与设计书 §五.1/五.2 的忠实性——键合融合拒 74.4% 大头是否如设计预期（"保守面既定"）？有无你认为该放行而拒/该拒而放行的类？
- D2（声明式拷贝语义）：B 来源产物组分拷贝（不执行、中心 unknown）的化学诚实性——拷贝组分进事件参与物而非执行产物，与"程序上诚实但化学上误导"的边界在哪里？declared_copy_mismatch 拒因够不够？
- D3（事件不变量 NC-10）：提交前双断言（共底物 ⊆ reactants ∧ 产物多重集 == 执行∪拷贝）是否封死 r28 R2-2 的"伪装通道"残余？
- D4（union gate 键空间统一）：strict_identity_of 统一后 EAWAG 路径字节等价的声明（隔离子进程 8 真实底物零字节差）可采信吗？
- D5（NC-12 熔断+T1′ 边界）：本通道 matched_strict 恒 0 的结构性钉子与 T1′ 三条落字（产物侧辅因子恒不忽略/反应物侧仅 H₂O 特例/拷贝与忽略差集互斥）是否防住 r30 G2-b 的"A→P+NADH 洗成 strict"路径？
- D6（总判定）：采纳成立/有条件+条件清单；与冻结判据一~五冲突检查（P1 义务）。

## 回复格式

D1-D6 逐条一句话结论+展开；不确定写不确定+缺什么证据；执行类断言标"待执行验证"；不修改任何文件。你只读评审（变更集中在 src/pathway_v43/pollutant/{recorded_source,production}.py 与 D2 交付书）。
