# 任务书：L2 Stage 2 —— 判分侧身份归一试点

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 数值只在该题域成立，与 dev 域双向不外推。
> **性质：零模型、零付费。** 全部改动只在 notebook `iter/worktrees/` 副本里，**不碰生产代码**。
> 预注册：`docs/L2_STAGE2_PILOT_PREREG_2026-10-26.md`（签字版 SHA256 `7ca3c0301deb7f120b7150f92cca60cdc8441ae2bc72b8e58141a3181c189e74`）。
> **CC 2026-10-26 已签字：Step 1–2 授权执行；Step 3 待诊断门通过后另行确认。**

---

## 0. 现状（Stage 1 已交付，直接用）

| 项 | 结果 | 出处 |
|---|---|---|
| 全 298 池重建 | **298/298 一致**（成员/顺序/spec/`template_remap`/诊断全无差异），16 shard 用时 7m59s | `docs/L2_STAGE1_FULL298_REPLAY_2026-10-26.md` |
| 全 298 全链重放 | v2 = **89/118/125**、**126/53/119**；v1 = 84/113/120、121/58/119；逐题 status/rank **298/298** | 同上 |
| 语义口径 | 286/298 立即全等；12 题仅差时间戳派生引用（已逐 artifact 证明） | 同上 |
| 证明边界 | 只覆盖单次模型调用；多轮 format-feedback / 多 decide **0 题未覆盖** | 同上 §7 |
| 工作区 | notebook `/root/v43_migration/iter/`（data/ bin/ rounds/ worktrees/） | — |

---

## 1. 目标与阶段

**试点假设**：94 题 unmatched + 41 题 partial 中，存在"化学身份等价但字符串/映射号表示不同"导致的未判等。

三阶段，任一阶段不达标即停：

| 阶段 | 做什么 | 停点 |
|---|---|---|
| Step 1 | 建正负控样本（预注册 §5 的 P1–P3 / N1–N4） | 负控本身建不出 → 停 |
| Step 2 | **诊断门**：全 298 量化"canonical 化能回收多少题" | 可回收 **< 10 题** → 停，换试点 |
| Step 3 | 只在 `iter/worktrees/` 实现 canonical 化 patch | 触碰黑名单任一形态 → 作废 |
| Step 4 | 全 298 重放验证（J1–J5） | 任一不满足 → 记未达标，停 |

---

## 2. 红线（含 CC 2026-10-26 不撞车约束）

1. **只写 `/root/v43_migration/iter/`**；不写 `iter/data/`（只读）、不写 `/root/v43_migration/ppv1_hpc/`。
2. **P2 B 臂归另一个窗口**：不碰 P2 批根/runs；开工前 `ps` 看有没有 P2 在跑；不在同一目录并发写。
3. **不改生产代码**：`/root/v43_migration/v43cP2` 只读；一切改动在 `iter/worktrees/identity/` 副本里，产出是 **patch**，不是部署。
4. **不改判据定义**：只允许预注册 §1 白名单（身份 canonicalization / 比较实现修复）；
   黑名单（放宽 strict 条件、近似匹配、qid 特判、改主口径聚合）一律禁止。
5. 零模型调用、零付费；不 commit、不 push。
6. 金标只在 700 目录内消费；报告只写聚合与 qid 级，不抄参考图内容。
7. 开工与收工各核一次三件套哈希（`evaluation.py=37c09231…`、`s5b_scoring.py=4af3ed2d…`、`s5b_compiler.py=58cf3dc9…`）；
   **另需记录 `chemstate.py` 的当前哈希**（另一窗口 2026-10-26 15:49 改过 P2 CN 修复，本试点基线以此为准并在报告披露）。
   **试点诊断与验证全程用当前代码（含该修复），不得回到修前版本。**

---

## 3. 分步

### Step 0：环境与不撞车（10 分钟）
```bash
bash scripts/hpc/nb_ssh.sh "ps -eo pid,etime,cmd --sort=-etime | head -15; df -h / | tail -1"
bash scripts/hpc/nb_ssh.sh "sha256sum /root/v43_migration/v43cP2/src/pathway_v43/pollutant/{evaluation.py,s5b_scoring.py,s5b_compiler.py} /root/v43_migration/v43cP2/src/pathway_v43/pollutant/chemstate.py"
```
记录：主机名、时间、P2 是否在跑、四个哈希。

### Step 1：建正负控（半天内）
在 `iter/rounds/r001/controls/` 落：
- 正控 P1–P3、负控 N1–N4，每条给出：输入对（两个身份串）、期望判等/不等、实际判等/不等、判定函数与文件:行号。
- 来源优先用仓内已有测试样例或 r2 真实态；**不得编造化学结构**，构造不出就如实写"无法构造"并停在 Step 1。
- 判定函数用当前实现（raw 口径），证明负控在 raw 下已正确（这保证 baseline 不含"该判不等的被判等"）。

### Step 2：诊断门（核心，零 LLM）
对全 298 题：
1. 从 r2 `metrics.json` 的 `per_qid` 取全部非 strict 题（119 unmatched + 53 partial），**按四桶分报**：`unmatched 非 remap（94）` / `unmatched remap（25）` / `partial 非空池（41）` / `空池（12）`。**不得只看 94+41**——remap 桶里的 identity 题会漏。
2. 对每题，取参考图必要节点身份集合与候选事件身份集合（**只读 v2 判分链路已用的数据**）。
3. 计算两个口径：
   - `raw`：当前实现（应复现基线：这些题确实 unmatched/partial）
   - `canonical`：仅对身份串做白名单归一（映射号/芳香-Kekulé/显式隐式H/括号冗余），**不改节点/边判定结构**
4. 输出：`可回收上限` = canonical 下新增 strict 的题数；逐题给"原来哪两个身份串被误判不等"。
5. 另做**假阳性防护**：canonical 口径下若出现"原本 unmatched 变 strict 但化学上不该等"的题，计入 `suspicious` 列表并单独披露（这是放宽判据的征兆）。

**门限**：可回收 ≥ 10 题且 suspicious = 0（或可逐条解释）→ 进 Step 3；否则停，写清是 identity 不是瓶颈。

### Step 3：实现 patch（仅在 worktree）
- `iter/worktrees/identity/` = `v43cP2` 副本（含 assets 最小集）
- 只改身份比较路径；每处改动写注释说明"这是等价表示归一，不是放宽命中条件"
- 产出 `iter/rounds/r001/patch.diff` + 变更说明（文件:行号 + 理由）
- **不做任何部署**

### Step 4：全 298 验证
- 用 Stage 1 的 replay 基座（`iter/bin/replay.py`）对 worktree 代码跑全 298
- 逐题配对：g（unmatched/partial→strict）、l（strict→非 strict）、持平
- 核 J1–J5（预注册 §4，**含 l ≤ 6 绝对损失上限**），负控 P1–P4 / N1–N4 全跑
- 报附加项：v1 净增、hit@3/5、strict、rank>1；**v1 净增 <0 或 hit@3/5 掉 >5 题 → 停并解释**
- 输出 `iter/rounds/r001/{metrics,g_l,controls}.json` + 人类摘要

### Step 5：报告
`docs/L2_STAGE2_PILOT_RESULT_2026-10-26.md`（本地 + 回传）：
- Step 2 门结果（可回收上限、suspicious 清单）
- patch 说明与 diff 路径
- J1–J5 逐项判定
- g/l 明细（哪些 qid 变好、哪些变坏、为什么）
- 正负控结果
- 证明范围披露（照预注册 §7）
- 建议：合并 / 不合并 / 换试点

---

## 4. 排障

| 症状 | 处置 |
|---|---|
| Step 2 可回收 < 10 题 | 停，如实写"identity 不是瓶颈"，列下一个候选（element 7 / no_alignment 28）的入口 |
| canonical 口径产生大量 suspicious | 说明归一过宽，收缩白名单重测；仍不行则判"该试点不可做" |
| 负控在 raw 下就已违规 | 说明基线本身有判等 bug — 这是**重大发现**，单独报告，不要顺手修 |
| 另一窗口正在改 chemstate.py | 立即停实现，只做只读诊断；等代码稳定后重跑 Step 0 |
| notebook 实例被回收 | 进程死数据活：从 `iter/rounds/r001/` 的 journal 续跑；Stage 1 已证明可幂等 |
| 全链重放出现新的时间戳差异 | 按 Stage 1 的规矩：去时间戳语义比较 + artifact 级证明，不许直接判 FAIL |

---

## 5. 回传

1. Step 0 四个哈希 + 不撞车检查结果
2. Step 1 正负控表（每条的期望/实测）
3. **Step 2 门结果**：可回收上限题数、suspicious 题数、逐题归因摘要
4. 若进 Step 3：patch 路径 + 变更清单
5. Step 4：J1–J5 逐项 + g/l 明细
6. 报告路径 + 证据 SHA256SUMS
7. 偏离任务书的地方

---

## 6. 附录：路径与命令

```
notebook 工作根   /root/v43_migration/iter/
数据（只读）      /root/v43_migration/iter/data/r2/
生产代码（只读）  /root/v43_migration/v43cP2/
工作副本          /root/v43_migration/iter/worktrees/identity/
轮次目录          /root/v43_migration/iter/rounds/r001/
Stage 1 重放器    /root/v43_migration/iter/bin/replay.py
Stage 1 报告      docs/L2_STAGE1_FULL298_REPLAY_2026-10-26.md
Stage 1 证据      docs/review_evidence/l2_stage1_full298_2026-10-26/
预注册            docs/L2_STAGE2_PILOT_PREREG_2026-10-26.md
```

**L2 循环合同**（本任务书与后续轮次共同遵守，全文见预注册 §9）：
代理指标成对评估 + 闭卷预算 3 次只记录不选择 + 不拿 298 当选择信号；
±5pp 噪声带、一批多修复、配对判定；
大脑在本地、notebook 只当探针农场、agent 不读金标、代码改动须过审阅门；
每轮 record 落 `iter/rounds/rNNN/`，可断点续跑。