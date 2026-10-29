# GOAL：自迭代闭环 —— hit@1 冲 50%（方向目标）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本目标全部数字只在 298 域、
> DeepSeek 链式口径内成立，不外推 dev、不对外发布。
> **拍板记录：CC 2026-10-26 深夜～10-27 凌晨，四轮 grilling 全部确认。**
> **性质：夜间预注册 + 循环协议。本文即授权书——CC 签字后，循环在白名单内自主推进，
> 无需逐轮人工批准。**

---

## 0. CC 拍板清单（原文口径）

| # | 决策 | CC 选择 |
|---|---|---|
| 1 | 执行架构 | 本地 ZCode 定时驱动（每 30 分钟轮询），notebook 只当探针/跑批农场（A 方案不推翻） |
| 2 | 工作面 | **完整闭环：自己跑 298 full → 自己归因 → 自己整改 → 再跑**，含付费 |
| 3 | 授权形态 | 今晚签夜间预注册（=本文），白名单内 agent 自主发批 |
| 4 | 预算 | **不设上限**；逐批 token 记账落 journal |
| 5 | 模型 | DeepSeek（`deepseek-v4.1-flash-1017`，notebook 链路现成，~50 分钟/臂） |
| 6 | 基线 | P2 A 臂 **86/298 = 28.86%**（v2 口径；同 prompt `c24bee42…`、同 v1card、同池、同模型；批 `p2-298-20261026`、指纹 `fcd84049…`、code `c565cd56…`） |
| 7 | 对照设计 | 单臂改动 vs 基线；**达标轮次下一轮补跑基线臂**防跨批漂移 |
| 8 | 整改白名单 | **工程层开放 + 判分器冻结**；提示词阶梯解锁（见 §3） |
| 9 | 审查 | **每轮 patch 交 QwenReviewer 代审，PASS 才发批** |
| 10 | 空转停点 | **不设**（CC 明确选择；技术性故障停另设，见 §5） |
| 11 | P2 | 只读授权：22 题 onlyA 逐题归因可用 L2 分层框架做，不写 P2 目录 |
| 12 | 产出 | goal 文档（本文）+ 每轮 journal + 状态文件随时可看 |

## 1. 目标与基线

- **方向目标：hit@1 ≥ 50%（149/298，DeepSeek 链式口径）。** 这是跨多夜的方向，不是单夜承诺；
  夜间物理上限 ≈ 10 臂，理想链条单夜 +30~36 题（~40%）。
- **每轮硬门（过门才算数）**：
  - J1 净增 **≥ +6 题**（相对 86 链式基线，逐轮滚动）
  - J2 **g ≥ 2l 且 l ≤ 6**
  - J3 判分器冻结校验通过（§4 哈希门）
  - J4 QwenReviewer 结论 **PASS**
- 50% 达成时：停发新批，出总结报告等 CC。

## 2. 循环协议（每轮五段）

```
① 诊断：读上轮 metrics + 失分分层（composition/stereo/constitution/coverage 四层，
   复用 iter/ 现成框架；P2 只读归因同框架）→ 选本轮最大杠杆的单变量
② 方案：写 hypothesis.md（改什么/为什么/预期影响哪个桶/泛化论证——不许 qid 特判）
   + patch（只动白名单层）
③ 审查：派 QwenReviewer 子代理代审 patch（工程合理性/泛化性/黑名单违规/统计门）；
   PASS → 发批；FAIL/BLOCKED → 回修一次，再败换方向并记录
④ 跑批：notebook 上单臂 full 298（DeepSeek、新 batch_tag、smoke10 先行：
   10 题零 failed 才进 full）；运行参数沿 P2 链（入口 v2.2、锁/批准包沿用不重绑，
   提示词未解锁时 prompt SHA 必须仍为 c24bee42…）
⑤ 归因记账：score（v2 headline）→ 与基线配对 g/l → 逐题四层归因 →
   token 账落 journal → 更新状态文件 → 达标则下一轮补基线臂
```

轮次目录：notebook `/root/v43_migration/iter/rounds/nNN/`（n 序列与 r 诊断序列并行），
每轮落 `hypothesis.md / patch.diff / qwen_review.md / metrics.json / g_l.json / token.json`。

## 3. 整改白名单 / 黑名单（阶梯解锁）

**白名单（第 1 轮起开放）**：池构建与检索参数（`S5B_POOL_*`、raw_top、corpus_channel）、
编译/remap/映射逻辑（`s5b_compiler.py`）、身份归一实现、coverage/参与物装配层。
每轮**只改一个变量或一个小补丁集**，patch 里逐处注释"为什么这是泛化修复而非特判"。

**阶梯解锁（提示词层）**：~~前 2 轮提示词**冻结**~~ → **CC 2026-10-27 上午拍板"①②③全开"：
提示词层立即解锁**（原"连续 2 付费轮过门后解锁"条件作废——该条件在白名单内无可过门实验，
构成死锁，CC 知悉后全开）。每轮仍只改一处、新 prompt SHA 记入 journal、token 账基线随之刷新。
同批拍板：③判据契约线（化学评审）启动、供给面扩库立项（周期长，后排）。

**黑名单（任何轮次不可碰）**：
- `evaluation.py` 的匹配定义、`s5b_scoring.py` 主口径聚合（判分器冻结，哈希见 §4）
- 金标（`reference_graphs` 内容不入任何报告/patch/journal）
- 封存批与 P2 批根（只读除外，§6）
- qid/分子特判、放宽 strict 语义、近似匹配
- 主树 git（不 commit 不 push；改动全部在 notebook `iter/worktrees/`）

## 4. 判分器冻结校验（每轮发批前必跑）

```
evaluation.py  = 37c092310d34d9f417234ccacd508942b3ce9f4d0e
s5b_scoring.py = 4af3ed2d60f97a3460df92027d2bb2b280b92c5956e81c475ee262cf33549ca3
```
任一不匹配 → 本轮作废，回滚 patch，查谁动了判分器。`s5b_compiler.py`/`chemstate.py`
可改（改后记新哈希入 journal，并跑 Stage 1 零漂移门确认基线复现 86 链）。

## 5. 停点

| 类型 | 条件 | 动作 |
|---|---|---|
| 红线停（立即） | 金标外泄风险/P2 目录被写/判分器哈希变/盘满 | 停发批，状态文件记 RED_FLAG，不再推进 |
| 技术性故障停 | 同一技术错误连续 3 次复现（同 qid transport 失败致整批 FAILED、SSH 不可恢复、批驱动器死亡） | 停发新批，journal 记录，等待晨间人工——**技术停≠科学空转停** |
| 达成停 | hit@1 ≥ 149 | 停发新批，出总结 |
| 空转停 | **不设**（CC 2026-10-27 拍板：方向对就持续跑） | 每轮无论过门与否都完整落 journal——空转与否早上看状态文件一目了然 |

## 6. P2 只读归因（并行任务）

授权范围：读 `ppv1_hpc` 下 P2 两臂 cases/native_export/metrics，用 L2 四层框架做
22 题 onlyA 归因，产出 `docs/P2_STOPPOINT_ATTRIBUTION_<date>.md`（含时间窗漂移检查）。
**不写 P2 任何目录、不改判分、不做跨批直接比较**（只做配对与分层）。

## 7. 记账与产出

- **逐批 token 账**：每批 `projected_total_tokens` + usage 落 `token.json`，累计数进状态文件。
- **状态文件**（每轮更新，CC 随时可看）：`docs/SELF_ITERATE_STATUS.md`
  ——当前轮次/在飞批/链式基线滚动表/累计 token/RED_FLAG/下一步。
- **journal**：`docs/review_evidence/self_iterate_<date>/journal.jsonl`（本地）+
  notebook `iter/journal.jsonl` 双落。
- 所有对外引用数字带三锚（轮次 nNN + batch_tag + 口径），遵守 `docs/BIBLE/` 九条。

## 8. 签字

| 项 | 状态 |
|---|---|
| CC 签字（本文即夜间预注册） | ✅ **2026-10-27 凌晨 CC 签**（对话原文"签"；四轮 grilling 拍板 + 开工条件全绿确认后生效） |
| 目标：hit@1 ≥ 50% 方向 | 已拍板 |
| 空转不设停 / 预算不设上限 | 已拍板（风险已两次提示，CC 确认） |

**生效时刻的基线快照**：主树 HEAD `2aa4502`（fatal fix `3b53747` 已入树，chemstate 双侧 `495d3d0e…` 一致）；
判分器冻结哈希与 §4 相同；链式基线 86/298（P2 A 臂锚）；coverage 53 诊断在飞，其结果并入第一轮变量选择。