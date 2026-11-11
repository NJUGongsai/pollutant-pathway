# 任务书：`[biosysmodb121]` 全卷 121 条路径「禁祖先倒车零束宽（Non-Backtracking `B=1`）」重放与增量补跑验证

- **文档编号**：`TASK_B121_NON_BACKTRACKING_B1_EVAL_2026-11-11`
- **立项与拍板日期**：2026-11-11（CC 拍板锁定）
- **题域标签**：**`[biosysmodb121]`**（B1 环境微生物多步降解路径，与 `[dev-298]` 双向不外推）
- **模型与管线锚点**：
  - 基座模型固定：**`deepseek-v4.1-flash-1017`**
  - 生产管线固定：**`v44-Next v1.2`**（`/Volumes/CC/Enzyme_Agent/v44` @ `d40eec7`：`S1d + S5-env ∪ S5-rr` 12 大类均衡 Top-16 建池 + 去 `v1card` + 双路 `novel` 编译 + 智能门控回填 + C-C/C-O/C1 裂解共产物补全 + 五层级候选排序器校准）
  - 终点分类器固定：**`mineralization_sink.py`**（`ppv1-mineralization-sink-v1`，A0/A/B 档确定性终点）

---

## 一、 核心背景与现状表

### 1.1 `Naive B=1` 评测基线复盘与瓶颈诊断

在上一轮 `biosysmodb121` 全卷 121 条路径的零束宽（`Naive B=1`，每步盲取单步排名第 1 的 `Event #1`）端到端完全矿化评测中：
- **完全矿化闭合率较低**：`MINERALIZED_CLOSED` 为 **`21 / 121 (17.36%)`**（其中 `Tuning 16/76 (21.05%)`，`Holdout 5/43 (11.63%)`，`Non-417 0/2`）；
- **极度严重的父子一步可逆倒车**：高达 **`89 / 121 (73.55%)`** 的路径死于 `CYCLE_ABORTED`；深入排查发现，在全部 96 个环路分支中，**`93 / 96 (96.88%)` 的环路是 `lag = 2` 的父子一步可逆倒车（`A -> B -> A`）**；
- **候选事件库储备极其充沛**：单步底层执行在 **`99.46%`（`551 / 554`）** 的底物上已经产出了 $\ge 2$ 个合规反应事件（其中 539 个底物产满 5 个事件），真正的正向降解（如 `B -> C`）往往就在同一步的 `Event #2` 或 `#3`，却被 `Naive B=1` 的 Top-1 盲取机制完全掩盖。

### 1.2 CC 拍板决议：Non-Backtracking `B=1`（禁祖先倒车零束宽）

| 规则维度 | 锁定结论 | 形式化执行契约 |
| :--- | :--- | :--- |
| **束宽维持** | **严格维持零束宽 $B=1$** | 每步依然只选用 **1** 个反应事件推进，绝不发散多条反应束，计算复杂度严格为 $O(D)$。 |
| **禁祖先倒车顺延** | **禁止变回祖先分子，按序顺延** | 当分支处于底物 $X$（其从根到 $X$ 的祖先分子集合为 $\mathcal{A}$）选择当步反应时：<br>1. 按单步校准排名顺序依次检查已通过编译与守恒审计的合规候选事件 $E_1, E_2, \dots, E_K$；<br>2. 对候选事件 $E_k$，提取其全部非终点含碳碎片（排除 $A0$ 无机物、内源货币辅因子及 $A/B$ 档已矿化终点）；<br>3. 若任一非终点含碳碎片命中祖先集合 $\mathcal{A}$（分子严格身份 `strict_identity_of` 碰撞），则判定该事件发生倒车，记录 `backtracking_skipped`，顺延检查 $E_{k+1}$；<br>4. 选用第一个无祖先碰撞的合规事件；若所有候选事件均倒车回祖先，则该分支诚实判为 `CYCLE_ABORTED`（子原因 `all_candidates_backtrack`）。 |
| **独立工作区与零覆盖** | **原结果绝对只读保护** | 严禁覆盖或修改原 `full121` 的推演树与汇总文件！新建独立子目录 `reports/ppv1_s5b/b121_e2e_mineralization_20261111/full121_non_backtracking_b1/`。 |
| **缓存零 LLM 复用** | **554 底物完整候选补齐** | 离线解析原 `waves/` 中已落盘的 554 个唯一底物 `native_result.json`，提取完整 Top-1..#5 事件补齐至新缓存目录，确保已跑底物 100% 零重复在线调用。 |
| **增量并发补跑** | **36 路并发在线执行** | 顺延后解锁出的全新下游中间体，自动调用 `deepseek-v4.1-flash-1017` 并发补跑并落盘新缓存。 |

---

## 二、 铁律与红线约束

1. **留出集单向盲测**：
   - 评测涵盖 `Tuning (76)` 与 `Holdout (43)`，Holdout 集一镜到底，严禁人工挑题或回调管线参数；
   - 规则与算法仅基于拓扑环路避免机制，零金标渗透。
2. **公开产物零金标 / 零题面 / 零私有 ID**：
   - 公开报告（`docs/reports/B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md`）与公开证据 JSON（`docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/non_backtracking_b1_summary.json`）严禁出现 `BIOPATH150_` 题号、测试集化合物名称或私有 SMILES；
   - 详细推演树与逐步私有记录仅存放在 gitignored 的 `reports/` 目录下。
3. **禁止自动 Git Commit / Push**：
   - 严格遵守仓内工作纪律，一切代码与报告修改均不自动执行 `git commit` 或 `git push`。
4. **分母闭合与三道红线门禁**：
   - 严格保障 $76 + 43 + 2 = 121$ 分母完备闭合；跑通三道红线扫描脚本。

---

## 三、 形式化规则与算法定义

### 3.1 祖先集合与倒车碰撞检测

设分支当前历史严格身份序列为 $H = (s_0, s_1, \dots, s_d)$，其中 $s_d$ 为当前底物 $X$ 的 strict_id，$s_0$ 为根污染物 strict_id。
祖先集合定义为：
$$\mathcal{A} = \{s_0, s_1, \dots, s_d\}$$

对候选反应事件 $E$，其产物集合为 $\mathcal{P}(E)$。对每个产物 $p \in \mathcal{P}(E)$：
1. 运行 `sink = classify_mineralization_sink(p.smiles, role=p.role)`；
2. 若 `sink.sink_tier in ("ENDOGENOUS_CURRENCY_COFACTOR", "A0_noncarbon_inorganic")` 或 `sink.is_terminal_sink`，则忽略；
3. 否则 $p$ 为非终点含碳碎片，计算其严格身份 $id(p) = \text{strict\_identity\_of}(p.\text{smiles})$；
4. 若 $id(p) \in \mathcal{A}$，则发生倒车碰撞，其倒车距离定义为：
   $$\text{lag} = |H| - \text{index}_H(id(p))$$
   - 若 $id(p) = s_d$，$\text{lag} = 1$（自身环路）；
   - 若 $id(p) = s_{d-1}$，$\text{lag} = 2$（父子逆反应，如 $A \to B \to A$）；
   - 若 $id(p) = s_{d-k+1}$，$\text{lag} = k$。

### 3.2 Non-Backtracking 事件选择器算法

```python
def select_event_non_backtracking(
    candidate_events: list[dict],
    history_strict_ids: tuple[str, ...],
) -> EventSelectionResult:
  skipped = []
  for ev in candidate_events:
    collisions = check_ancestor_collisions(ev, history_strict_ids)
    if collisions:
      skipped.append({'rank': ev['rank'], 'collisions': collisions})
    else:
      return EventSelectionResult(
          status='SELECTED', selected_event=ev, skipped_events=skipped
      )
  return EventSelectionResult(
      status='ALL_CANDIDATES_BACKTRACK',
      selected_event=None,
      skipped_events=skipped,
  )
```

---

## 四、 执行命令与验收标准

1. **缓存补齐**：从既有 `waves/` 解析 554 底物完整候选事件并落盘到 `full121_non_backtracking_b1/substrate_step_cache/`。
2. **单测覆盖**：在 `test_mineralization_sink.py` 中新增正控、负控与裂解碰撞测试，100% 绿灯。
3. **全卷推演**：执行 `--policy non_backtracking_b1 --workers 36 --max-depth 15`。
4. **报告与双仓同步**：生成对比表，同步更新公开报告与证据目录，并镜像至 `dependingv43`。
5. **门禁核验**：确保零泄露、分母闭合、单测全绿。
