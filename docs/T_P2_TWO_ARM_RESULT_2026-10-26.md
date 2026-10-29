# P2 正式两臂批结果（2026-10-26）：A=v1card 对照 / B=v2card 试验

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）；与 dev 域双向不外推。**
> 批次：`p2-298-20261026`（同 seed/build、指纹 `fcd84049…`、code `c565cd56…`、prompt `c24bee42…`、模型 `deepseek-v4.1-flash-1017`、workers 8、no-cap）。
> **唯一变量：`evidence_card_version`（A=v1card / B=v2）**。两臂同批同窗。
> 工程链：锁 `828c527b…`、批准包 `c0b4c381…`/canonical `d950bf1d…`、运行配置 `f8089791…`、`source_commit=11aeeaf…`（不 commit）。

## 0. 一句话

两臂 full 298 均通过终态门（0 failed / 0 pending / 0 fatal）。**B（v2 卡）显著低于 A（v1 卡）：
headline v2 口径 hit@1 68 vs 86（B−A = −18 题），strict 102 vs 119（净 −17），unmatched 155 vs 140。
预注册 §6.1 科学停点触发（strict 净失 −17 ≤ −3），须停点复盘，不改判、不写结论词。**

## 1. 运行与终态门

| 项 | A=v1card | B=v2card |
|---|---|---|
| smoke2 / smoke10 | 两臂共用（B 发车时完成，各 2/2、10/10 passed） | 同左 |
| full 时窗 | 13:11:17Z → 14:03:15Z（约 52 min） | 10:39:21Z → 11:26:14Z（约 47 min） |
| driver pid | 43617 | 39962 |
| 终态门 | `passed=true`、reasons=[] | `passed=true`、reasons=[] |
| checked / completed | 298 / 295 | 298 / 294 |
| failed / pending / fatal / 内容失败 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| run failures（模型结构失败） | 1（`RXNG_93161cb8…`） | 2（`RXNG_59a40849…`、`RXNG_28cc9c75…`） |
| 结构性零调用 | 2（`RXNG_7a886593…`、`RXNG_ed3d7072…`） | 2（**同两道题**，臂无关结构） |
| cases_digest | `0df3058c…b51ad7` | `a98be233…6011b` |
| score | rc=0，v1+v2，headline=v2，9 件产物 | 同 |
| stop.json / driver FINAL | 无 / `ok=true`、`lockin_changed_midrun=[]` | 同 |

## 2. 结果（分母固定 298，data_scope=real）

### 2.1 主表

| 指标 | A v1 口径 | B v1 口径 | **A v2 口径（headline）** | **B v2 口径（headline）** | **B−A（v2）** |
|---|---:|---:|---:|---:|---:|
| hit@1 | 81（27.18%） | 64（21.48%） | **86（28.86%）** | **68（22.82%）** | **−18** |
| hit@3 | 107（35.91%） | 96（32.21%） | **112（37.58%）** | **101（33.89%）** | **−11** |
| hit@5 | 114（38.26%） | 97（32.55%） | **119（39.93%）** | **102（34.23%）** | **−17** |
| strict U | 114 | 97 | **119** | **102** | **−17** |
| partial | 44 | 46 | 39 | 41 | +2 |
| unmatched | 140 | 155 | 140 | 155 | **+15** |
| 老口径敏感性 hit@1 | 126 | 117 | 126 | 117 | −9 |

### 2.2 配对（逐题，headline v2）

| 口径 | both | onlyB | onlyA |
|---|---:|---:|---:|
| hit@1 | 64 | 4 | **22** |
| hit@3 | 94 | 7 | 18 |
| hit@5 | 97 | 5 | 22 |

- strict 翻转：**B 得 5 题、A 得 22 题**（净 −17）；v1 敏感性口径完全同构（strict −17）。
- 95% CI（S1 by source group，hit@1）：A v2 [0.2383, 0.3423]；B v2 [0.1812, 0.2785]。

### 2.3 豁免对称性

两臂 `criteria_v2` 完全对称：各 **5 条 H2O 豁免**（A strict 114→119、B 97→102；
`tier_counts` A {v1_exempt:10, not_exempt:84}、B {v1_exempt:10, not_exempt:87}）。
**B−A 的差距与 v2 豁免无关**（两臂同加 5）。

### 2.4 token

| 项 | A | B | B−A |
|---|---:|---:|---:|
| full `projected_total_tokens` | 3,960,074 | 3,621,410 | **−338,664（−8.55%）** |
| 输入侧预测量（代理 tokenizer） | 1,385,752 | 1,091,679 | −21.22% |
| over_plan_band / cost | false / no_snapshot | 同 | — |

B 更省 token（实际 −8.6%，因含输出与反馈轮，小于输入侧 −21%），代价是 strict −17。

## 3. 科学停点（触发）

预注册 §6.1：**全局或任一分族 v2 strict 净失 ≤ −3 ⇒ 停点复盘**。本批全局 strict 净失
**−17 ≤ −3**，触发。按预注册：停点复盘三出口（设计失败 / 局部噪声 / 需另轮预注册），
**不自动改判、不写"v2 卡无效/有效"结论词**；复盘归 CC/老师裁定。本批无分族表
（metrics 无 family/stratum 字段），只有全局口径。

## 4. 解释边界（必须随数字引用）

1. **B−A 是"同一 v2 prompt 下 v2 卡 vs v1 卡"的整包效应**（预注册 §2.5/§2.6 披露）：
   v2 prompt 描述的是 v2 字段集，A 臂的 v1 卡没有这些字段——**prompt-卡不匹配面在 A 臂更大**，
   但本批结果是 prompt 匹配的 B 反而更低；不得读成纯卡版本因果，也不得读成纯体积/字段效应。
2. **不跨批比较**：不得把本批 A 86/298 或 B 68/298 与旧批 89/298、v44 94/298、chain14 91/298
   直接比较（代码、tag、批根、窗口、分母构成不同）。仅可作量级观察：A 臂量级与历史 v1 卡批相近，
   掉分集中在 B 侧。
3. post-hoc 已见题；298 域不外推 dev。
4. `evaluator_output_status=pending_user_teacher_decision`；v2 为敏感性口径、headline 固定 v2。
5. 失败/零调用全留分母：两臂结构性零调用是**同样两道题**（`cosubstrate_copy_in_expectation`，臂无关）；
   模型结构失败 A 1 / B 2。
6. 两臂 full 不在同一时间窗（B 上午、A 下午），模型服务侧行为漂移未证伪——属复盘待查项，
   本报告不归因。

## 5. 证据

- 两臂结果与配对：`docs/review_evidence/p2_launch_2026-10-26/`（B）、`docs/review_evidence/p2_launch_A_2026-10-26/`（A，含 `paired_summary.json`）
- B 单臂报告：`docs/T_P2_B_ARM_RESULT_2026-10-26.md`
- 身份 v2 / 入口 v2.2 / fatal 修复与复验：`docs/review_evidence/p2_nb_identity_2026-10-26-v2/`、`p2_nb_entry_2026-10-26-v2-2/`、`p2_fatal_fix_verify_2026-10-26/`、`p2_fatal_reverify_2026-10-26/`
- 批准包：`docs/P2_APPROVAL_PACKAGE_2026-10-21/`（`c0b4c381…`）

## 6. 待 CC/老师裁定

1. §6.1 停点复盘的出口选择（设计失败 / 局部噪声 / 另轮预注册）；
2. `evaluator_output_status` 的 teacher 裁定；
3. 是否对本批做失分归因（B 侧 22 题 onlyA 的逐题 diff）与两臂时间窗漂移检查。