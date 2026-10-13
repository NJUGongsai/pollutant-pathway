# 任务书：ppv1-criteria-v2 判分面豁免实施（2026-10-13）

> 主会话起草，交实施子代理。零上下文可接。
> 上游：teacher T-1 裁定（b 档）+ CS2c 探针/补证（N1''=13）+ mimo r36 九条件 + 冻结前拍板包（docs/TEACHER_T1_FREEZE_DECISION_PACKAGE_2026-10-13.md，CC 已拍板"冻结+授权实施"）。**必读**：拍板包全文、mimo 回应 docs/mimo_ppv1_chem_review_response_r36.md、补证 reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/cs2c_side_predicates.md。

## 0. 一句话目标

在判分侧（evaluation.py）实现"参与物集合比较轴"的 T-1 豁免：产物侧 H₂O/H⁺/Pi/PPi、反应物侧仅 H₂O/H⁺，配三谓词守门+逐边披露+单归属断言+NC-12 前提域重写，判据版本升 ppv1-criteria-v2，预注册先行。**生成侧零改动。**

## 1. 设计定稿（拍板包+mimo 9 条件的代码形态）

### 1.1 豁免逻辑（只动 evaluation 参与物集合比较轴，edge 匹配段）

- **作用点**：edge 匹配的参与物集合比较（evaluation.py:1062-1068 区域，reactants==from_states ∧ products==to_states 两侧）。
- **逐侧过滤**：事件侧多余参与物（extras）按侧别判定——产物侧 extras ∈ {H₂O,H⁺,Pi,PPi} 的 cn 身份（版本化哈希集）；反应物侧 extras 仅 ∈ {H₂O,H⁺}。
- **三谓词（全过才豁免，任一不过=该 extras 维持比较）**：
  1. **记录已声明**：该共底物身份在来源记录方程里声明（消费事件/假设的 provenance 回溯——补证已实证 payload 可判；判不了=unknown=不通过，fail-closed）；
  2. **元素可追溯**：豁免实例涉及的 O（水）/P（Pi/PPi）在事件**非豁免反应物**侧计数 >0（补证的"无中生水"拦截形态：反应物 O=0 而产物豁免水 ⇒ 拒豁免）；计数判据照抄补证脚本口径；
  3. **cn 身份成员**：extras 的 cn_identity ∈ 豁免身份哈希集（sha256 前 16 位版本化；与 COMPLETION_LICENSED_IDENTITIES 交集=∅ 的断言写死为常量测试）。
- **完备二分+单归属**：每条 extras 恰好一个 tier 标签（v1_exempt / not_exempt_maintains_partial）；T1′ 档未实施 ⇒ 未声明多余产物**维持 partial**（明字常量注释+测试）；判定粒度=身份+侧+角色。
- **披露**：豁免发生时逐边机读 `exempted_participants`（身份/侧/tier/谓词三布尔），进 evaluation 输出与判分聚合（批级计数汇总）。
- **参考侧监控**：统计参考侧出现 v1 豁免身份的次数（应为 0；非 0=退出条件信号，批级披露字段）。

### 1.2 版本与措辞

- 判据版本常量：ppv1-criteria-v1 → **ppv1-criteria-v2**（evaluation/scoring 侧版本承载；不动 EDIT_PROTOCOL/ATOMTOOL/池策略）。
- **NC-12 前提域重写**："本通道 matched_strict 恒 0" → "**未获豁免披露的本通道 matched_strict 恒 0**"（tests/test_ppv1_s5b_cosub_d2.py 的 NC-12 断言与 recorded_source 相关注释措辞同步；不静默删除旧文字，改动处注明 v2 依据）。
- 机器挡板（裁定条件 1）：豁免清单内身份构造非法断言（含碳身份禁入豁免构造——CO₂/HCO₃⁻ 已知 v2 冲突点登记为 known gap 注释）+ 辅因子硬拒绝表（NAD(P)/ATP/CoA/FAD/THF/O₂/NH₃/T1′ 恒不忽略族：进比较面绝不豁免，测试负控钉死）。

### 1.3 判分输出（双口径）

- 新批次起 v2 为正式口径；判分输出并列现行 v1 口径敏感性（沿用 report 的老口径并列先例：v1 重算豁免关=现有行为字节不变，v2 开豁免=新行为——同批双跑或同遍双记，实现者按 evaluation 现结构择小侵入者，报告里写明选择）。
- post-hoc 标签+位次/新覆盖分离计数（沿用 W0 诊断口径）。

## 2. 预注册（实施的第一步，不是附属）

写 `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`：冻结方向限定版清单+三谓词+完备二分+披露契约+退出条件（omitted_coproduct_scope 落地即废止）+known gaps（CO₂ 冲突/追溯计数判据的保守性）+生效口径（新批次起，旧批零回写）+预期（13 题模拟下界，非承诺）+mimo r36 九条件逐条落字对照表。状态 preregistration_pending_final_confirmation（交 CC 最终确认读）。

## 3. 红线

1. 生成侧（runflow/production/queue/builder/events）**零改动**——本任务只动判分侧+测试。
2. 豁免关闭时（默认 v1 兼容开关）既有判分行为**字节不变**——既有 2098 全量测试零翻转（版本字面量与 NC-12 措辞导致的预期翻转除外，逐 nodeid 列出）。
3. 测试用合成夹具，零金标零真实 qid（13 题的形态用合成例复刻：已声明水豁免 strict/无中生水拦截/Pi 反应物侧不豁/NAD 挂名不洗/未声明多余维持 partial/H⁺与[H]不合流/参考侧出现豁免身份的退出信号）。
4. 不 push；判分代码改动后本机全量回归+G01 隔离跑（先例命令查近期交付书）。
5. 实施完成后交主会话核对，再走 Codex 正链复审（判据级变更必须过审才生效）——本任务不含发车。

## 4. 分步

1. 读拍板包+mimo r36+补证报告→写预注册（§2）→交主会话转 CC 确认（不阻塞代码实施，预注册内容与代码同轮交付）。
2. evaluation 豁免实现（§1.1/1.2），版本常量与披露字段。
3. 测试矩阵：合成正负控 ≥12 件（§3.3 列的六形态+单归属断言+计数监控）。
4. 全量回归 not slow（基线 2098/0/16）+G01。
5. 字节不变探针：豁免关（v1 口径）下对 T3 已落盘 rescore 基线重算，298/298 桶与 rank 零漂移（用 scripts/s5b_offline_rescore.py 先例）。
6. 豁免开（v2 口径）下重算 chain12：与 CS2c 严格版对照，解锁题数应=13±（候选集同批冻结，理论应精确一致；不一致=实现与探针判据有出入，逐题 diff 找出并如实报告——探针判据 vs 实现判据的差是合法性发现，不是硬凑对齐）。
7. 交付书 docs/POLLUTANT_PATHWAY_CRITERIA_V2_DELIVERY_2026-10-13.md（改动面/测试数字/字节不变探针/v2 重算对照/known limits）。

## 5. 排障表

| 症状 | 处置 |
|---|---|
| provenance 回溯判不了"已声明" | fail-closed（unknown=不豁免）+known limit 登记；不造数据 |
| 元素计数判据与补证脚本不一致 | 以补证脚本口径为准（它过了验证门）；差异如实披露 |
| v2 重算与 13 不一致 | 逐题 diff 归因（探针模拟 vs 真实 evaluation 的谓词差），如实报告 |
| 既有测试翻转 | 逐 nodeid 分类（版本/NC-12 措辞=预期；行为红=停下报告） |

## 6. 回传义务

1. 预注册路径+状态；2. 改动文件清单与性质；3. 测试矩阵件数+全量/G01 数字；4. 字节不变探针结果；5. v2 重算对照（=13 与否+差异归因）；6. 交付书路径；7. known limits。不 commit 不 push（主会话核对后提交）。
