# P2 token 门设计修订选项 — 全 298 题真实池实测（2026-10-21）

> **provenance**：分析子代理，2026-10-21。只读 P2 worktree
> `/tmp/dependingv43_p2`（HEAD `11aeeaf` + r2 patch `cd8c03e0…`；未改代码）
> 与 HPC 冻结批 `t_h_s5b_298_20261020r2/run_inputs` 的本地只读副本
> （298 件）；tokenizer 为 Qwen3.5-2B 代理
> `87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4`
> （`add_special_tokens=false`）。**零模型、零判分、零金标、未读
> reference_graphs、未输出题面/SMILES、未 push**。本报告只给成本拆解与
> 修订选项的 token 投影，**不认证科学收益、不替代 CC/老师裁定、不改变
> token 门当前 FAIL 与付费批停**。最终 T-I 模型未定，所有读数须在最终
> tokenizer 上同口径复测。
>
> 证据：`docs/review_evidence/p2_token_revision_2026-10-21/`
> （脚本、result/summary JSON、verification、SHA256SUMS）。自检 9/9
> 通过：298/298 逐题 v2 A/B token 与官方预测量全等；字段阶梯逐题闭合；
> C 的 104 截断题集与官方 104 超限集全等；输出零 SMILES 命中；
> 去 `generated_at` 后重跑 canonical JSON 全等。

---

## 1. 结论（TL;DR）

| 问题 | 读数 |
|---|---|
| 增量主因 | **候选数 × 每候选约 223 token**；不是固定底物卡/格式冗余 |
| 字段占比（104 超限题） | **participants 37.4%**、edit_summary 18.3%、product_delta 11.3%、底物卡 10.3%、FG delta 8.4%、conditions 8.1%、alignment 2.8%、容器+schema 3.4% |
| 每候选边际 | **223.0 token/候选**（104 题 349 个 prepared 候选）；其中 participants 94.5、edit 46.3、product 28.5、FG 21.2、conditions 20.5、alignment 7.0、容器 5.0 |
| 13% 预算 | 平均 v2 A 2,985 token/题 ⇒ **≈388 token/题**；1 候选实测 +2.83%，2 候选 +11.33%，3 候选 +17.34%，4 候选 +24.64% |
| 结构性去重上限 | **≈1% 批合计（相对 v2 B）**（B 共享字段 −0.50%、B 共享 participant 行 −0.95%、E 无损引用化 −0.97%）；而把 104 题压到 13% 至少需削 **27,546 token（占 B 2.86%）** ⇒ **任何只做共享/引用、不删证据的选项都不可能过门** |
| 能过门的选项 | **只有 C（题级预算帽）**：C_tail 13% = **+4.86%，298/298，最大 +12.99%**；C_uniform 13% = **+3.81%，298/298，最大 +12.98%** |
| 推荐 | **C_uniform（13% 帽，全体候选同一证据等级）**；需新设计冻结/评审。若 CC 更看重“至少保留前位候选全卡”，则 C_tail；但池序位置偏差对排序实验是实质混杂 |
| 字段面 | **四个选项全部触碰冻结字段面/证据合同**；没有一个是 r2 式纯格式级改动。C 还需新增 `evidence_truncation` 披露键、按 qid 冻结的帽表、新 schema/descriptor、prompt 增补与预注册 |

一句话：**v2 的 token 增量是“每个候选真实内容”的线性成本，不是可共享的
样板；共享/引用最多省 1%，离 2.86% 的最低削减量还差一半以上。要过
13% 逐题门，只能按题预算裁证据（C），或者改门口径/分母；A/B/D 单独
都过不了，A 还会引入池序位置偏差。**

---

## 2. 口径、身份与可复现性

| 项 | 值 |
|---|---|
| P2 worktree | `/tmp/dependingv43_p2`，HEAD `11aeeafded1b41185f24de49767933709aad49db`；4 个预期改动文件（v2 实现 + 测试），运行前后 `git status` 未新增文件 |
| tokenizer | `87a7830d…`（Qwen3.5-2B 代理；最终模型未定） |
| 输入 | `/tmp/p2_token_298_inputs`，298 件；SHA-256 manifest 与官方 `p2_token_298_2026-10-21/input_manifest.json` 逐项全等（qid/文件哈希/候选数） |
| 题数/候选 | 298 题、531 候选；60 空池、92 单候选、57×2、53×3、24×4、8×5、1×6、3×8；≥2 候选 146 题 |
| 真实可请求 | 2 题各 1 条 spec 在 `prepare_hypothesis` NC-9 失败（真实批 `run_error` 同源、`model_calls=0`）；选项按 prepared 条目构造，与官方预测量同口径 |
| 重建一致性 | 逐题 v2 A/B payload 文本与 `real_model.build_proposals_user_payload` 全等；298/298 token 与官方结果全等 |
| 门槛 | 任务书 §8.1 双口径：批合计 ≤13% **且**逐题全部 ≤13%；本报告沿用，未改口径 |

**拆解方法**：以 v2 A（默认分隔符、无证据键）为 0，先换紧凑分隔符，
再依次加 `candidate_evidence_schema_version`、`substrate_evidence`、每个
候选的 `evidence:{}` 容器和 6 个字段；每步重新 `json.dumps(sort_keys)` 后
计数。逐题阶梯和 = v2 B − v2 A（298/298 闭合）。tokenizer 边界顺序
敏感性：把 6 个字段倒序加入时，104 题合计中 `edit_summary` 多 698 token、
`participants` 少 349、`product_delta` 少 349，其余字段不变，总和不变；
这是 BPE 边界效应，不是字段成本改变。

---

## 3. 成本拆解

### 3.1 104 个超限题的字段级账（v2 B − v2 A，正增量 88,134 token，净增量 66,198）

| 字段/项 | 104 题合计 tok | 每题均值 | 占正增量 | 每候选均值（349 候选） |
|---|---:|---:|---:|---:|
| `substrate_evidence` | 9,042 | 86.94 | 10.26% | — |
| `candidate_evidence_schema_version` | 1,248 | 12.00 | 1.42% | — |
| 候选 `evidence` 容器 | 1,745 | 16.78 | 1.98% | 5.00 |
| `participants` | 32,974 | 317.06 | **37.41%** | **94.48** |
| `edit_summary` | 16,168 | 155.46 | 18.34% | 46.33 |
| `product_delta` | 9,960 | 95.77 | 11.30% | 28.54 |
| `functional_group_delta` | 7,402 | 71.17 | 8.40% | 21.21 |
| `conditions_and_scope` | 7,152 | 68.77 | 8.11% | 20.49 |
| `alignment_quality` | 2,443 | 23.49 | 2.77% | 7.00 |
| **候选证据小计** | **77,844** | **748.50** | **88.33%** | **223.05** |
| 紧凑分隔符节省 | −21,936 | −210.92 | — | — |
| **净增量** | **66,198** | **636.52** | 100% | — |

- **participants 一项就占每候选成本的 42.4%**（94.5/223.0）；edit_summary
  20.8%、product_delta 12.8%、FG delta 9.5%、conditions 9.2%、alignment
  3.1%、容器 2.2%。底物卡是**每题固定 ~87 token**，与候选数无关。
- 104 题只占 298 题净增量的 **90.6%**（66,198/73,093）；其余 194 题
  净增 6,895。全 298 口径的字段占比：participants 34.86%、edit 15.91%、
  底物卡 17.68%、product 10.07%、FG 7.45%、conditions 7.30%、
  alignment 2.51%、容器+schema 4.21%；正增量 147,677，紧凑节省
  −74,584（**r2 紧凑分隔符已经拿掉了约一半毛增量**，剩下的就是真内容）。
- `requirements` 在 531 个 spec 中出现 0 次；带 `coproducts` 239/531
  （45.0%）；带 `participants`/`co_substrate_states` 105/531。真实池没有
  合成样本里的 requirements 变量可删；standard/lean 折叠为同一读数。

### 3.2 按候选数分桶：每候选字段成本几乎恒定

| 候选数/题 | 题数 | 超限 | 每候选总 tok | participants/候选 | edit/候选 | product/候选 | FG/候选 | conditions/候选 | alignment/候选 | 容器/候选 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 60 | 0 | — | — | — | — | — | — | — | — |
| 1 | 92 | 0 | 216.7 | 94.3 | 43.2 | 26.9 | 20.1 | 20.2 | 7.0 | 5.0 |
| 2 | 57 | 21 | 238.8 | 110.1 | 47.1 | 28.2 | 21.0 | 20.4 | 7.0 | 5.0 |
| 3 | 53 | 47 | 213.1 | 91.1 | 40.7 | 28.1 | 20.8 | 20.4 | 7.0 | 5.0 |
| 4 | 24 | 24 | 214.9 | 84.6 | 47.6 | 28.9 | 21.5 | 20.4 | 7.0 | 5.0 |
| 5 | 8 | 8 | 217.6 | 102.0 | 35.7 | 27.4 | 19.8 | 20.8 | 7.0 | 5.0 |
| 6+ | 4 | 4 | 268.3 | 124.6 | 59.2 | 30.3 | 21.5 | 20.7 | 7.0 | 5.0 |

关键读数：**除 participants/edit 随具体题波动外，每候选的 product/FG/
conditions/alignment/容器成本在各桶几乎一样（约 28/21/20/7/5）**。
6+ 桶的 edit 更高（59.2），participants 也更高（124.6），所以每候选
268，而不是因为“格式在长题上爆炸”。**增长来自候选数，不来自字段效率
随题变差。**

### 3.3 每题固定账与结构性算术

| 候选数/题 | 题数 | 超限 | 平均 Δ | 底物卡/题 | schema/题 | 紧凑节省/题 | 净增量/题 | 13% 预算≈388 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 60 | 0 | −4.48% | 85.2 | 12 | −254.3 | −157.1 | 过（空池只省格式） |
| 1 | 92 | 0 | +2.83% | 86.3 | 12 | −252.4 | +62.6 | 过 |
| 2 | 57 | **21** | +11.33% | 92.5 | 12 | −267.8 | +314.2 | 临界/部分超 |
| 3 | 53 | **47** | +17.34% | 87.2 | 12 | −237.6 | +492.8 | 超 |
| 4 | 24 | **24** | +24.64% | 90.0 | 12 | −232.7 | +728.8 | 超 |
| 5 | 8 | **8** | +37.96% | 77.6 | 12 | −165.6 | +1,012.0 | 超 |
| 6+ | 4 | **4** | +48.73% | 96.5 | 12 | −336.0 | +1,784.5 | 超 |

近似账：`净增量/题 ≈ n × 223 + 87 + 12 − 紧凑节省`。1 候选约
+63 token（实测 +2.83%）；2 候选约 +314（实测 +11.33%）；3 候选约
+500（实测 +17.34%）。**13% 预算 ≈388 token 的结构性边界正好落在
1 与 2 个候选之间**：1 候选全过、2 候选约三分之一超、3 候选起几乎全超。
这不是再压格式能翻的——r2 已经把紧凑分隔符用满。

### 3.4 结构性去重能省多少：上限约 1%，不够

- 104 题要全部压到 13%，按“最理想地只削超出帽的部分”计算，至少需削
  **27,546 token（占 v2 B 的 2.86%）**；8% 帽则至少需削 44,333（4.61%）。
- B_shared（只共享整字段）省 4,828 token（B 的 0.50%）；
  B_shared_rows（再加共享 participant 行）省 9,186（0.95%）；
  E_participant_ref（participant SMILES 无损引用化，1,519/1,694 行可引用）
  省 9,342（0.97%）。
- **即使把三项结构压缩都做满，也只有所需削减量的约三分之一**；而且
  这些选项单独都还有 79–95 题超限。结论：**只做共享/引用，门不可能过；
  必须删/截证据，或改门口径。**

---

## 4. 修订选项与全 298 实测

### 4.1 选项定义

| 选项 | 构造（全部保持候选集、顺序、底物/执行图不变） |
|---|---|
| **A K=1/2 min** | 池序前 K 个候选给完整 v2 证据；其余给紧凑回退 `edit_summary + alignment_quality.status`（v1 字段名，无 v2 新增 delta） |
| **A K=1/2 v1** | 前 K 个完整 v2；其余给 v1 全卡（敏感性） |
| **B shared** | 各候选**整字段完全相同**时，把该字段提到题级 `candidate_evidence_shared` 一次；候选只带差异字段 |
| **B shared rows** | 在 B 基础上，再把各候选**完全相同的 participant 行**提到题级共享一次；候选只留自身新增/差异行 |
| **E participant ref**（附加） | participant 行中与候选 `product_smiles`/`coproducts` 或题面底物完全相同的 SMILES 换成 `@product`/`@coproduct[i]`/`@substrate` 短引用；侧/角色/系数不变（无损探针） |
| **C tail 13/8%** | 题级总 token 上限 = v2 A ×(1+13%/8%)；从最后一个候选开始，按 `product_delta → conditions → alignment → participants → FG → edit_summary` 的低→高优先级逐级截断；写 `evidence_truncation` 披露 |
| **C uniform 13/8%** | 同一预算帽，但**所有候选同一证据等级**（整体降级），消除池序位置偏差；披露字段同 C |
| **D principal v1** | 仅池序第一个 prepared 候选带 v2 全量；其余保持 v1 全卡（实际等价于 A K=1 v1） |
| **D principal noev** | 仅第一个 prepared 候选带 v2 全量；其余无证据（D 的最省 token 下界/敏感性） |

> **principal 代理说明**：run_inputs 无 principal/rank 字段；D 的
> “principal”操作化为池序第一个 prepared 候选，是**代理变量**，不是
> 金标或已验证的首要候选。D 的读数不能读成“给真正首要候选加证据”。

### 4.2 全 298 批合计与逐题门

基线 v2 A 批合计 **889,587 token**；v2 B **962,680**（+8.2165%）。

| 选项 | 批合计 tok | 批合计 Δ vs v2 A | 逐题通过/298 | 超限 | 最大单题 Δ（qid） |
|---|---:|---:|---:|---:|---:|
| v2 B（参考，冻结卡） | 962,680 | +8.2165% | 194 | 104 | +64.1263%（`RXNG_1eba3a0`） |
| **A K=1 min** | 912,671 | **+2.5949%** | **283** | **15** | +17.4745%（`RXNG_1eba3a0`） |
| A K=2 min | 937,154 | +5.3471% | 238 | 60 | +23.8231%（`RXNG_8f29c4d`） |
| A K=1 v1 | 1,006,970 | +13.1952% | 165 | 133 | +92.0918%（`RXNG_1eba3a0`） |
| A K=2 v1 | 984,773 | +10.7000% | 191 | 107 | +86.5753%（`RXNG_1eba3a0`） |
| **B shared** | 957,852 | +7.6738% | 210 | 88 | +62.7551%（`RXNG_1eba3a0`） |
| **B shared rows** | 953,494 | +7.1839% | 219 | 79 | +55.7079%（`RXNG_1eba3a0`） |
| E participant ref | 953,338 | +7.1664% | 203 | 95 | +59.3431%（`RXNG_1eba3a0`） |
| **C tail 13%** | 932,792 | **+4.8567%** | **298** | **0** | **+12.9854%**（`RXNG_9683627`） |
| **C uniform 13%** | 923,479 | **+3.8099%** | **298** | **0** | **+12.9751%**（`RXNG_0eda0ec`） |
| C tail 8% | 915,196 | +2.8788% | 298 | 0 | +7.9870%（`RXNG_22901c4`） |
| C uniform 8% | 905,344 | +1.7713% | 298 | 0 | +7.9414%（`RXNG_1677ce9`） |
| D principal v1 | 1,006,970 | +13.1952% | 165 | 133 | +92.0918%（`RXNG_1eba3a0`） |
| D principal noev | 896,552 | +0.7829% | 295 | 3 | +13.4526%（`RXNG_167dfdc`） |

- **只有 C 两个 13% 变体全过**；C 的 104 个截断题集与官方 104 超限集
  **逐 qid 全等**，且没有一题需要丢底物卡。
- A K=1 min 是“非预算帽”里最好的（283/298），但仍有 15 题超：7 个
  2 候选题、3 个 4 候选、4 个 5 候选、1 个 8 候选；要全过还得在 A 上
  再套 C，等于**先对所有 146 个多候选题降证据，再对 15 题二次截断**，
  语义损失面比 C 单独大得多。
- D principal noev 有 3 题超（均为 2 候选题，+13.44～13.45%，只差
  0.45pp），说明“只给第一个候选全卡”也不是稳定过门方案；D v1 更差，
  因为 v1 卡本身比 v2 大 20.8%。
- A K=1 v1 与 D principal v1 是**同一个载荷**（前 1 个 v2 + 其余 v1），
  两者数字全等不是巧合。

### 4.3 按候选数看通过矩阵（通过/超限）

| 候选数 | 题数 | v2 B | A K=1 min | A K=2 min | B shared rows | E ref | C uniform 13% | D noev |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 60 | 60/0 | 60/0 | 60/0 | 60/0 | 60/0 | 60/0 | 60/0 |
| 1 | 92 | 92/0 | 92/0 | 92/0 | 92/0 | 92/0 | 92/0 | 92/0 |
| 2 | 57 | 36/21 | 50/7 | 36/21 | 44/13 | 35/22 | 57/0 | 54/3 |
| 3 | 53 | 6/47 | 53/0 | 36/17 | 22/31 | 14/39 | 53/0 | 53/0 |
| 4 | 24 | 0/24 | 21/3 | 12/12 | 1/23 | 2/22 | 24/0 | 24/0 |
| 5 | 8 | 0/8 | 4/4 | 2/6 | 0/8 | 0/8 | 8/0 | 8/0 |
| 6+ | 4 | 0/4 | 3/1 | 0/4 | 0/4 | 0/4 | 4/0 | 4/0 |

C 的“全过”只发生在 104 个本来会超的题上；194 个本来通过的题保持
完整 v2 B 载荷（C 只在超帽时触发）。

### 4.4 C 的截断分布：tail vs uniform

| 指标 | C tail 13% | C uniform 13% | C uniform 8% |
|---|---:|---:|---:|
| 截断题数 | 104 | 104 | 140 |
| 截断题内候选数 | 349 | 349 | 417 |
| 底物卡被丢的题 | 0 | 0 | 0 |
| 全量证据候选 | 145 | 0 | 0 |
| 部分证据候选 | 127 | 341 | 337 |
| 无证据候选 | 77 | 8 | 80 |
| 候选等级直方图 | 0:77, 1:28, 2:81, 3:1, 4:10, 5:7, 6:145 | 0:8, 1:39, 2:221, 3:18, 4:45, 5:18 | 0:80, 1:69, 2:238, 3:7, 4:20, 5:3 |
| 丢 `product_delta` | 204（58.5%） | 349（100%） | 417（100%） |
| 丢 `conditions_and_scope` | 197（56.4%） | 331（94.8%） | 414（99.3%） |
| 丢 `alignment_quality` | 187（53.6%） | 286（81.9%） | 394（94.5%） |
| 丢 `participants` | 186（53.3%） | 268（76.8%） | 387（92.8%） |
| 丢 `functional_group_delta` | 105（30.1%） | **47（13.5%）** | 149（35.7%） |
| 丢 `edit_summary` | 77（22.1%） | **8（2.3%）** | 80（19.2%） |

等级映射（两策略共用）：6=全量；5=丢 product；4=再丢 conditions；
3=再丢 alignment；2=再丢 participants（只剩 edit+FG）；1=只剩
edit_summary；0=无证据。

- **tail C** 保护池序靠前的候选（145 个保持全卡），但制造了**题内证据
  不对称**：前面的候选全卡、后面的候选可能只有 edit 或什么都没有。
  对“模型给候选排序”的 P2 实验，这是**位置偏差混杂**——池序本身可能
  与检索先验相关，会系统性利好前位候选。
- **uniform C** 所有候选同一等级，无位置偏差；代价是 participants 在
  76.8% 的截断候选里被丢（v1 信息损失大），但 **FG delta 保留 86.5%、
  edit_summary 保留 97.7%**——v2 的核心新增字段（FG delta）和主编辑摘要
  保得住，丢的主要是 v1 参与物/条件/对齐和次优 product_delta。
- 8% 帽下 uniform 会截断 140 题（连同 36 个本来过 13% 的题），80 个候选
  无证据；除非 CC 要更紧的预算，否则不建议 8%。

### 4.5 B/E 为什么只能省 ~1%

> 注意：v2 B 的 `substrate_evidence` **本来就是每题只出现一次**；
> B 要共享的是候选之间重复的整字段/participant 行，substrate 侧没有
> 第二次出现的副本可省。

- **B shared（整字段）**：146 个多候选题里，`alignment_quality` 在
  **146/146** 题所有候选完全相同（v1 字段，重复最广），
  `conditions_and_scope` 86/146（59%），FG delta 16/146（11%），
  product_delta 4/146，edit_summary 6/146。只省 4,828 token。
- **B shared rows**：1,694 个 participant 行中只有 **90 行（5.3%）**在
  同题所有候选里完全相同（60 题）；大多数 participant 行是候选特有的
  产物/副产物/角色组合，不能共享。省 9,186 token。
- **E ref**：1,519/1,694 行（89.7%）的 SMILES 与候选 product/coproduct
  或底物逐字相同，可无损换成短引用；也只省 9,342 token（B 的 0.97%）。
  BPE 对 SMILES 的编码本来就较紧，引用串本身也要 3–6 token，所以
  “换引用”没有想象中省。
- 三者都远小于最低需削的 27,546 token；**结构性去重的天花板就是
  ~1% 批合计**。这直接证明 qwen 代决“格式级已到极限”的判断在真实池
  上仍成立，且把“字段压缩”也基本封死——除非删字段/删候选证据。

---

## 5. 语义损失、披露、实现复杂度、冻结字段面

| 选项 | 语义损失 | 披露影响 | 实现复杂度 | 触碰冻结字段面？ |
|---|---|---|---|---|
| A K=1 min | 146 个多候选题的非首位候选失去 v2 FG/product/participants/conditions，仅留 edit+alignment；池序即证据等级 | 必须在 prompt/run identity 写明每个候选的证据等级；池序位置偏差 | **低**（按索引选卡；无新字段名） | **是**（每候选字段覆盖规则变化；treatment 定义变化） |
| A K=2 min | 同上，前 2 保完整；仍有 60 题超 | 同上 | 低 | 是 |
| A K=1/2 v1 | 非前 K 保留 v1 全卡；信息不比 v2 少，但 token 更差，且同载荷混用 v1/v2 schema | 必须解释 v1/v2 两种卡；schema/descriptor 身份冲突 | 中 | **是（混版，明确新 schema）** |
| B shared | 信息不丢（只搬位置）；模型须正确理解 `candidate_evidence_shared` 适用于所有候选 | 共享块语义要写进 prompt；题级结构变化覆盖 146 题 | **中高**（新题级键、participant 行多重集交集、schema/identity/resume） | **是**（新增题级键/搬移字段） |
| B shared rows | 同上；共享 participant 行必须逐字相同，不伪造/不补行 | 同上 + “共享行对每个候选都成立” | 中高 | 是 |
| E participant ref | 无损（引用可回解），但 participant 表示变了；模型须会解引用 | prompt 要定义 `@product/@coproduct[i]/@substrate`；错解会改变参与物语义 | 中 | **是**（participant 表示约定） |
| C tail 13/8% | 104 题内 145 全卡/127 部分/77 无证据；后位候选系统性少证据 | `evidence_truncation` 逐题披露 + 预注册分层分析；**位置偏差** | 中（需按 qid 的帽表/运行时 tokenizer；确定性截断测试） | **是**（新增披露键 + 条件性缺字段） |
| C uniform 13/8% | 104 题内 0 全卡/341 部分/8 无证据；participants 丢 76.8%，FG 丢 13.5%、edit 丢 2.3%；无位置偏差 | 同上；披露更整齐（同题同等级） | 中 | 是（同上） |
| D principal v1 | 非 principal 保留 v1 全卡；token 最差；principal 代理未验证 | 必须披露 principal 定义；混版 schema | 中高 | **是（混版）** |
| D principal noev | 非 principal **全无证据**；295/298，最大损失；仍有 3 题超 | 披露“只给第一个候选证据” | 中 | 是（条件性缺证据） |

**结论：四个（含附加 E）全部不是 r2 式纯格式改动。** 共同需要的身份
变化：新 schema/descriptor 版本串、prompt 增补、run identity/resume
校验、pre-registration 的 treatment 定义与分层分析；C 还额外需要
`evidence_truncation` 键和按 qid 的帽表。A/D 混用 v1/v2 卡时，还要
解决两套 descriptor 的语义边界；B/E 要解决“共享/引用”的模型解释
歧义。**没有一项可以由实施方自行拍板；都需新设计冻结/评审。**
按仓库 AGENTS.md，字段/判据变更归 CC/老师；本报告只提供投影。

---

## 6. 推荐

### 6.1 首选：**C_uniform 13%**（题级预算帽 + 全体候选同等级截断）

理由（按重要性）：

1. **唯一同时满足双口径、且不需要逐题例外的选项**：298/298、最大
   +12.98%、批合计 +3.81%。qwen 代决已明确不接受逐题例外；C 是
   “规则化例外”的替代。
2. **只动本来会失败的 104 题**：194 个本来 ≤13% 的题保持完整 v2 B
   载荷，不引入无谓语义损失；C 的截断题集与官方超限集逐 qid 全等。
3. **无池序位置偏差**：tail C 会让前位候选保留全卡、后位候选降级，
   对排序实验是实质混杂；uniform 全体同等级，排序比较更干净。
4. **保住 v2 的核心 treatment**：截断题内 FG delta 保留 86.5%、
   edit_summary 保留 97.7%；丢的主要是 v1 participants/conditions/
   alignment 和次优 product_delta，底物卡一题不丢。
5. **对最终 tokenizer 稳健**：帽是相对 v2 A 的比值，换最终 tokenizer
   后按同一规则重算帽表即可继续保证 ≤13%；A/B/D 的通过率则会随
   tokenizer 变化而漂移。
6. **批合计也低**：+3.81%，给最终 tokenizer 的波动留了余量；8% 版
   +1.77% 但截断 140 题，不建议默认用。

### 6.2 代价与必须写进预注册的事

- **104/298 题 treatment 不完整**：8 个候选完全无证据（349 中的 2.3%），
  268 个候选丢 participants（76.8%）。这不是“门过了设计就没问题”，
  而是**把 treatment 改成“v2 + 题级预算”**；token 门变成 by
  construction 通过，不能再拿它证明完整 v2 卡的可负担性。
- **完整 v2 卡的效应只能在 194 个未截断题上读**；截断的 104 题是另一个
  regime。预注册必须写：总体 + 截断/未截断分层 + 候选数分层；否则
  把截断效应和字段效应混在一起。
- **截断优先级必须冻结**：`product_delta → conditions → alignment →
  participants → FG → edit_summary`；任何事后调序/调帽都使本投影失效。
- **帽表/ tokenizer 依赖**：建议用最终 tokenizer 离线算好 **298 个 qid
  的帽表**（写入批 manifest，登记 tokenizer SHA），生产端只查表，不
  在热路径跑 tokenizer；若运行时计数，必须固定 tokenizer 版本并做
  确定性测试。这是 C 最主要的工程风险。
- **披露键成本已计入**：`evidence_truncation` 的 token 已包含在 C 的
  读数里；不是“先过门再补披露”。
- **位置偏差**：uniform 已消除；如果 CC 坚持 tail C，必须额外做
  池序置换/前位敏感性，否则 hit@1 可能被证据不对称抬高。

### 6.3 为什么不推荐 A/B/D 单独或 A/B 组合

- **A K=1 min**：283/298、15 题超，仍要再套 C；而且它对**所有 146 个
  多候选题**改变证据分配（不只 104 个超限题），把池序变成证据等级，
  对“挤位”实验是最不该引入的混杂。A K=2 更差（60 题超）。
- **B/B rows/E**：单独 79–95 题超；只省 ~1% 批合计，远低于最低需削
  2.86%。**B+C 组合**可以减少 C 的截断量（B rows 把超限题从 104 降到
  79），但代价是 146 题换成共享块 schema + prompt 解释；为 ~1% 的
  收益增加一类模型误解风险，不划算。若最终 tokenizer 让 C 的截断量
  明显变大，再考虑 B rows + C 作为减损增强。
- **D**：principal 在 run_inputs 里没有定义；v1 回退最差（133 题超）；
  noev 仍有 3 题超且非 principal 全无证据。不能作为设计修订主线。

### 6.4 需要的新冻结/评审（明确回答）

**需要，且是硬前置**。C_uniform 落地前至少要有：

1. **设计修订冻结**：帽定义（v2 A ×1.13，按最终 tokenizer）、逐 qid
   帽表、uniform 等级/字段优先级、`evidence_truncation` 键结构、
   prompt 增补、schema/descriptor 新版本（如 candidate-evidence-4 /
   descr-4）。
2. **预注册**：298 分母；treatment 定义（截断即 treatment 的一部分）；
   104/194 分层、候选数分层；strict 净失 ≤−3 停点继承；token 账；
   截断优先级不得事后调整；`evidence_truncation` 必须随 run 落盘。
3. **评审链**：Codex 正链复审（设计/实施各一轮）+ CC/老师对“口径变更”
   拍板；若评审认为“丢 participants/FG 的披露”触及化学判据，按
   mimo 场景 1 另送化学评审。B/E/A/D 若被选，同样需要各自的设计冻结；
   没有一项能走 r2 的格式级快速通道。
4. **最终 tokenizer 复测**：T-I 定模型后，用最终 tokenizer 重算 298 题
   v2 A/B 与 C 帽表，登记 SHA；本报告的代理 tokenizer 数字只作先导。

---

## 7. 限度

1. 代理 tokenizer（Qwen3.5-2B），不是 T-I 最终模型；绝对 token 数和
   通过率会随 tokenizer 变，**C 的相对帽机制最稳健，但截断分布需复测**。
2. 固定首发载荷、system+user 两段；不含格式反馈轮、传输重试、模型
   输出；不是实际费用账，也不含运行时重试的 token。
3. 298 题含 2 题 NC-9 prepare 失败（真实批 0 model_calls）；选项按
   prepared 条目构造，与官方预测量同口径；全 298 与 296 可请求口径的
   超限集合均为 104。
4. 所有选项是**载荷模拟**，除既有 v1/v2 构造函数外没有改 worktree 代码；
   生产实现（prompt、identity、resume、测试）未做。
5. B/E 的共享/引用语义未做模型行为验证；C 的截断披露对模型行为的影响
   （是否会被读成“这些候选没有证据”）未测，需在 P2 预注册里作为
   披露混杂登记。
6. D 的 principal 是池序代理，无金标/rank 依据；D 的数字不能读成
   “真正首要候选”的效应。
7. 本报告不认证化学正确性、科学收益、最终模型验证；不改已冻结判定，
   不 push。

---

## 8. 证据与自检

| 文件 | 内容 |
|---|---|
| `docs/review_evidence/p2_token_revision_2026-10-21/token_revision_options.py` | 全 298 构造 + 字段拆解 + A/B/C/D/E 选项脚本（只写证据目录） |
| `.../result.json` | 逐题 token、字段拆解、全部选项、超限 qid、C 截断明细 |
| `.../summary.json` | 聚合视图（报告引用） |
| `.../verification.json` | 9 项自检结果（官方 token 全等、闭合、C 题集全等、零 SMILES、确定性、worktree 只读） |
| `.../run.log`, `verify.log` | 运行与自检输出 |
| `.../SHA256SUMS` | 上述文件哈希 |

自检关键值：result SHA-256 `ffa83dac…`（以最终 SHA256SUMS 为准）；
去 `generated_at` 的 canonical SHA-256
`d939ec9bca49421831ee3ac2abd1104e6d3cc6ab1f1ed78065199ff9fd0d0153`；
tokenizer `87a7830d…`；worktree HEAD `11aeeaf…`；输入 298/298 与官方
manifest 全等；输出 SMILES 命中 0/544。

---

## 附录 A — 各选项超限 qid 前缀（只列前缀，不含题面/结构）

> C 两个 13% 变体均 0 超限；C 8% 也 0 超限。其余如下。

**A_K1_min（15）**：

`RXNG_0f02d5d`, `RXNG_167dfdc`, `RXNG_1eba3a0`, `RXNG_2b9dd28`, `RXNG_45d8d90`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_654cc41`, `RXNG_8687a1c`, `RXNG_8f29c4d`, `RXNG_b6e5b27`, `RXNG_efa6ffd`, `RXNG_fc90885`

**A_K2_min（60）**：

`RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_06453c8`, `RXNG_08d3aa8`, `RXNG_0eda0ec`, `RXNG_0f02d5d`, `RXNG_13a2ae2`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_1692948`, `RXNG_18a3c06`, `RXNG_1939194`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_21ed83a`, `RXNG_22901c4`, `RXNG_2492077`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_30ab410`, `RXNG_330df24`, `RXNG_39a545f`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_5132632`, `RXNG_5727b62`, `RXNG_57f8007`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_69c1854`, `RXNG_8687a1c`, `RXNG_891c844`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_9683627`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_aa8e13b`, `RXNG_b6e5b27`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cd29a64`, `RXNG_d239738`, `RXNG_d7656c5`, `RXNG_e2bf91b`, `RXNG_e47fbe8`, `RXNG_eb864c3`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`

**A_K1_v1（133）**：

`RXNG_017b29d`, `RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_06453c8`, `RXNG_0657c03`, `RXNG_08d3aa8`, `RXNG_0eda0ec`, `RXNG_0f02d5d`, `RXNG_0faafc6`, `RXNG_103c840`, `RXNG_11e08d7`, `RXNG_1314110`, `RXNG_13a2ae2`, `RXNG_1450598`, `RXNG_1529326`, `RXNG_164844b`, `RXNG_1656001`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_1692948`, `RXNG_18a3c06`, `RXNG_1939194`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_21ed83a`, `RXNG_22901c4`, `RXNG_248f2d7`, `RXNG_2492077`, `RXNG_2a1a5bf`, `RXNG_2a805c8`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_2e1157b`, `RXNG_30ab410`, `RXNG_32293b6`, `RXNG_330df24`, `RXNG_33315ca`, `RXNG_35a46ed`, `RXNG_39a545f`, `RXNG_3cdbe17`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_46c6b17`, `RXNG_47e0049`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_4c2cd0c`, `RXNG_4e05a0b`, `RXNG_4ec68aa`, `RXNG_5048373`, `RXNG_50e0f19`, `RXNG_5132632`, `RXNG_5727b62`, `RXNG_57f8007`, `RXNG_5975a92`, `RXNG_59a61f5`, `RXNG_5d15fc1`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_61667af`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_65536b4`, `RXNG_69c1854`, `RXNG_71774ff`, `RXNG_74406a7`, `RXNG_76682d9`, `RXNG_7a88659`, `RXNG_7beff03`, `RXNG_81e16d3`, `RXNG_8687a1c`, `RXNG_87e7556`, `RXNG_891c844`, `RXNG_89b8bce`, `RXNG_8bc45c2`, `RXNG_8dce8a3`, `RXNG_8e87765`, `RXNG_8ee93e3`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_93d3a3e`, `RXNG_9683627`, `RXNG_98c9304`, `RXNG_9b31382`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_a30cf37`, `RXNG_a401c95`, `RXNG_a62f2c5`, `RXNG_a7dee98`, `RXNG_a7f229a`, `RXNG_aa8e13b`, `RXNG_aefef2f`, `RXNG_b34d588`, `RXNG_b6e5b27`, `RXNG_b6f489e`, `RXNG_b978fd0`, `RXNG_b98e5b2`, `RXNG_baa4bda`, `RXNG_bff8e98`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cc87d03`, `RXNG_cd29a64`, `RXNG_cddca61`, `RXNG_d239738`, `RXNG_d41e12c`, `RXNG_d6da5d9`, `RXNG_d7656c5`, `RXNG_d80f872`, `RXNG_ddb5740`, `RXNG_e0bca29`, `RXNG_e10f66d`, `RXNG_e2bf91b`, `RXNG_e47fbe8`, `RXNG_e97de46`, `RXNG_eb7a858`, `RXNG_eb864c3`, `RXNG_ed3d707`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_f30855a`, `RXNG_fb3ab8e`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`, `RXNG_fdd3726`, `RXNG_febc7fb`, `RXNG_ffa4f99`

**A_K2_v1（107）**：

`RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_06453c8`, `RXNG_08d3aa8`, `RXNG_0eda0ec`, `RXNG_0f02d5d`, `RXNG_0faafc6`, `RXNG_103c840`, `RXNG_11e08d7`, `RXNG_13a2ae2`, `RXNG_1450598`, `RXNG_1529326`, `RXNG_164844b`, `RXNG_1656001`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_1692948`, `RXNG_18a3c06`, `RXNG_1939194`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_21ed83a`, `RXNG_22901c4`, `RXNG_2492077`, `RXNG_2a805c8`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_2e1157b`, `RXNG_30ab410`, `RXNG_32293b6`, `RXNG_330df24`, `RXNG_33315ca`, `RXNG_35a46ed`, `RXNG_39a545f`, `RXNG_3cdbe17`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_46c6b17`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_4c2cd0c`, `RXNG_4e05a0b`, `RXNG_50e0f19`, `RXNG_5132632`, `RXNG_5727b62`, `RXNG_57f8007`, `RXNG_59a61f5`, `RXNG_5d15fc1`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_61667af`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_65536b4`, `RXNG_69c1854`, `RXNG_76682d9`, `RXNG_7beff03`, `RXNG_8687a1c`, `RXNG_891c844`, `RXNG_89b8bce`, `RXNG_8bc45c2`, `RXNG_8dce8a3`, `RXNG_8e87765`, `RXNG_8ee93e3`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_9683627`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_a401c95`, `RXNG_a7dee98`, `RXNG_a7f229a`, `RXNG_aa8e13b`, `RXNG_aefef2f`, `RXNG_b6e5b27`, `RXNG_b978fd0`, `RXNG_b98e5b2`, `RXNG_baa4bda`, `RXNG_bff8e98`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cc87d03`, `RXNG_cd29a64`, `RXNG_cddca61`, `RXNG_d239738`, `RXNG_d41e12c`, `RXNG_d6da5d9`, `RXNG_d7656c5`, `RXNG_ddb5740`, `RXNG_e0bca29`, `RXNG_e10f66d`, `RXNG_e2bf91b`, `RXNG_e47fbe8`, `RXNG_e97de46`, `RXNG_eb864c3`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_f30855a`, `RXNG_fb3ab8e`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`, `RXNG_febc7fb`

**B_shared（88）**：

`RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_08d3aa8`, `RXNG_0eda0ec`, `RXNG_0f02d5d`, `RXNG_0faafc6`, `RXNG_103c840`, `RXNG_11e08d7`, `RXNG_13a2ae2`, `RXNG_1450598`, `RXNG_1529326`, `RXNG_164844b`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_1692948`, `RXNG_18a3c06`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_21ed83a`, `RXNG_22901c4`, `RXNG_2492077`, `RXNG_2a805c8`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_2e1157b`, `RXNG_30ab410`, `RXNG_330df24`, `RXNG_33315ca`, `RXNG_35a46ed`, `RXNG_39a545f`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_46c6b17`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_4c2cd0c`, `RXNG_4e05a0b`, `RXNG_50e0f19`, `RXNG_5132632`, `RXNG_57f8007`, `RXNG_59a61f5`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_69c1854`, `RXNG_76682d9`, `RXNG_8687a1c`, `RXNG_89b8bce`, `RXNG_8bc45c2`, `RXNG_8dce8a3`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_9683627`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_a401c95`, `RXNG_a7dee98`, `RXNG_a7f229a`, `RXNG_aa8e13b`, `RXNG_b6e5b27`, `RXNG_b978fd0`, `RXNG_bff8e98`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cc87d03`, `RXNG_cd29a64`, `RXNG_d239738`, `RXNG_d41e12c`, `RXNG_d6da5d9`, `RXNG_d7656c5`, `RXNG_ddb5740`, `RXNG_e0bca29`, `RXNG_e10f66d`, `RXNG_e47fbe8`, `RXNG_e97de46`, `RXNG_eb864c3`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_f30855a`, `RXNG_fb3ab8e`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`

**B_shared_rows（79）**：

`RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_08d3aa8`, `RXNG_0f02d5d`, `RXNG_0faafc6`, `RXNG_103c840`, `RXNG_11e08d7`, `RXNG_13a2ae2`, `RXNG_1450598`, `RXNG_1529326`, `RXNG_164844b`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_18a3c06`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_22901c4`, `RXNG_2492077`, `RXNG_2a805c8`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_30ab410`, `RXNG_330df24`, `RXNG_39a545f`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_4c2cd0c`, `RXNG_50e0f19`, `RXNG_5132632`, `RXNG_57f8007`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_69c1854`, `RXNG_76682d9`, `RXNG_8687a1c`, `RXNG_89b8bce`, `RXNG_8bc45c2`, `RXNG_8dce8a3`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_9683627`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_a401c95`, `RXNG_a7dee98`, `RXNG_a7f229a`, `RXNG_aa8e13b`, `RXNG_b6e5b27`, `RXNG_b978fd0`, `RXNG_bff8e98`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cc87d03`, `RXNG_cd29a64`, `RXNG_d239738`, `RXNG_d41e12c`, `RXNG_d6da5d9`, `RXNG_d7656c5`, `RXNG_ddb5740`, `RXNG_e0bca29`, `RXNG_e10f66d`, `RXNG_e47fbe8`, `RXNG_e97de46`, `RXNG_eb864c3`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_f30855a`, `RXNG_fb3ab8e`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`

**E_participant_ref（95）**：

`RXNG_036534a`, `RXNG_03ebc97`, `RXNG_0410354`, `RXNG_0436564`, `RXNG_06453c8`, `RXNG_08d3aa8`, `RXNG_0eda0ec`, `RXNG_0f02d5d`, `RXNG_0faafc6`, `RXNG_11e08d7`, `RXNG_13a2ae2`, `RXNG_1529326`, `RXNG_164844b`, `RXNG_1677ce9`, `RXNG_167dfdc`, `RXNG_1692948`, `RXNG_18a3c06`, `RXNG_1939194`, `RXNG_1ad8c65`, `RXNG_1eba3a0`, `RXNG_208874c`, `RXNG_21ed83a`, `RXNG_22901c4`, `RXNG_2492077`, `RXNG_2a805c8`, `RXNG_2b9dd28`, `RXNG_2d49e94`, `RXNG_2e1157b`, `RXNG_30ab410`, `RXNG_330df24`, `RXNG_33315ca`, `RXNG_35a46ed`, `RXNG_39a545f`, `RXNG_3cdbe17`, `RXNG_4441184`, `RXNG_45d8d90`, `RXNG_46c6b17`, `RXNG_48b725a`, `RXNG_4a529de`, `RXNG_4c2cd0c`, `RXNG_4e05a0b`, `RXNG_50e0f19`, `RXNG_5132632`, `RXNG_5727b62`, `RXNG_57f8007`, `RXNG_5e86f7e`, `RXNG_5e9b567`, `RXNG_61667af`, `RXNG_6455b8d`, `RXNG_654cc41`, `RXNG_69c1854`, `RXNG_76682d9`, `RXNG_8687a1c`, `RXNG_891c844`, `RXNG_89b8bce`, `RXNG_8bc45c2`, `RXNG_8dce8a3`, `RXNG_8e87765`, `RXNG_8f29c4d`, `RXNG_9038db2`, `RXNG_9683627`, `RXNG_a16ff40`, `RXNG_a275c52`, `RXNG_a30cf37`, `RXNG_a401c95`, `RXNG_a7dee98`, `RXNG_a7f229a`, `RXNG_aa8e13b`, `RXNG_aefef2f`, `RXNG_b6e5b27`, `RXNG_b978fd0`, `RXNG_baa4bda`, `RXNG_bff8e98`, `RXNG_c2fb10b`, `RXNG_c698e3f`, `RXNG_cd29a64`, `RXNG_d239738`, `RXNG_d41e12c`, `RXNG_d6da5d9`, `RXNG_d7656c5`, `RXNG_ddb5740`, `RXNG_e0bca29`, `RXNG_e10f66d`, `RXNG_e2bf91b`, `RXNG_e47fbe8`, `RXNG_e97de46`, `RXNG_eb864c3`, `RXNG_ef027ad`, `RXNG_efa6ffd`, `RXNG_f30855a`, `RXNG_fb3ab8e`, `RXNG_fb86653`, `RXNG_fc90885`, `RXNG_fce2c28`, `RXNG_fd4e0ba`

**D_principal_noev（3）**：

`RXNG_167dfdc`, `RXNG_2b9dd28`, `RXNG_45d8d90`

**D_principal_v1（133）**：与 `A_K1_v1` 是同一载荷（前 1 个 v2 + 其余 v1），超限 qid 集完全相同，不重复列；见 `A_K1_v1`。

**C_cap13 / C_cap13_uniform / C_cap8 / C_cap8_uniform（0）**：无超限。