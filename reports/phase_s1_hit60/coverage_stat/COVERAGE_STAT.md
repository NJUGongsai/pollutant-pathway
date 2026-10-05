# COVERAGE_STAT — mimo 化学评审三个"未见证据"测量的补齐（只读统计）

- 执行日：2026-09-30；执行者：HIT60 只读统计代理
- 触发：`docs/mimo_e1_chem_review_comment.md`（gitignored）§B2/§C3/§D1/末尾三件事标注的三个"未见证据"
- 红线遵守：零 API、零 LLM、判分/统计全离线；金标只在本地 gitignored
  `dev_gold/` 内的离线进程打开；远端（Chenyu dependingv43_s1）只读拉取产物；
  不改任何评分代码（只调用 `exam_v2.first_hit_rank` 的 `component_mode` 既有开关）；
  不改 RUN_JOURNAL/ARMS；本文件与 TSV 不含任何 SMILES/金标内容。
- 环境：本地 conda `depending43`（python 3.11 + rdkit 2026.03.6），`PYTHONPATH=src`，
  `OMP_NUM_THREADS=1`。

## 0. 一行结论

**M1**：dev @1 未中 48 题里，"金标在答卷 2–5 位"=11 题且**全部走 novel 路由**
（E1 式证据卡重排承载面 = 0，复确认）；整串 miss 的 37 题 = 7 题**整串口径
假失分**（金标组分就在答卷里）+ 16 题**金标在检索证据池但漏斗丢弃**（其中 12 题
被路由送进 novel）+ 14 题**证据池也没有**（真·生成面）。
**M2**：E3（窗口 16）的 rank 任务实际只带 **2/2/4 张卡**——第 9–16 张卡
**不存在**，窗口 8→16 在 dev 载荷层是 no-op；按检索序放宽入围的假想"第 9–16 张卡"
（24 张）有 **79% 命中 mimo ①/③/④ 过滤器**（analog 通道 16/16 全违规）。
**M3**：mimo 手算"+6 上限（8/56→14/56）"**精确成立**，且六个批次全部 +6（@3/@5
均 +7）；救回题清单与 mimo 的 6 题逐一相同。

---

## 1. M1 — 金标在 5 候选池的覆盖率（决定"投生成 vs 投重排"）

### 1.1 口径

- 答卷 = 各批次 `merged/predictions.jsonl`（每题最多 5 个报告产物，跨 step 顺次拼接，
  与官方评分器 `agent_candidates` 同源；六批 SHA 与官方 `score.json` 的
  `answers_sha256` 逐一相核一致）。
- 金标 = `dev_gold/dev_gold.jsonl`，身份口径 = 整串 `cn_identity`（cn-v1，与
  `s1_dev_score`/exam_v2 完全同源）。整串 rank 复算与官方 `per_question.tsv`
  **逐题 0 差异**（六批全对拍）。
- 路由 = 远端各题 `decision.json` payload 的 `prediction_mode`（空 = recorded
  确定性通道）。六批路由分布完全相同：novel 42 / recorded 8 / rank 3 / analogy 3
  （= 48 次 LLM 调用中 42 novel，与 RUN_JOURNAL §10.4 一致）。
- 证据池 = 各题全部 `cardval.*.json` verdicts 的整串产物候选（cn 身份或精确串，
  与 FULL_SURFACE_LEAK_AUDIT §2 同判据）。

### 1.2 核心交叉表：路由 × 金标在答卷中的位置

桶定义（互斥，优先级自上而下）：
`at1`=整串 @1 命中；`2–5`=金标在答卷第 2–5 位（**重排可救**）；
`B`=整串 miss 但**金标组分已在答卷内**（组分级可救，见 M3）；
`C1`=答卷完全没有、但**金标在检索证据池**（漏斗/选择丢）；
`C2`=答卷与证据池都没有（**必须改生成**）。

| 路由 | at1 | 2–5 | B | C1 | C2 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| novel（C0-a） | 8 | **11** | 0 | 12 | 11 | 42 |
| recorded | 0 | 0 | 4 | 2 | 2 | 8 |
| rank | 0 | 0 | 3 | 0 | 0 | 3 |
| analogy | 0 | 0 | 0 | 2 | 1 | 3 |
| **合计** | **8** | **11** | **7** | **16** | **14** | 56 |

| 路由 | at1 | 2–5 | B | C1 | C2 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| novel（C0-b） | 9 | 11 | 0 | 11 | 11 | 42 |
| recorded | 0 | 0 | 4 | 2 | 2 | 8 |
| rank | 0 | 0 | 3 | 0 | 0 | 3 |
| analogy | 0 | 0 | 0 | 3 | 0 | 3 |
| **合计** | **9** | **11** | **7** | **16** | **13** | 56 |

| 路由 | at1 | 2–5 | B | C1 | C2 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| novel（E1） | 10 | 9 | 0 | 12 | 11 | 42 |
| recorded | 0 | 0 | 4 | 2 | 2 | 8 |
| rank | 0 | 0 | 3 | 0 | 0 | 3 |
| analogy | 0 | 0 | 0 | 2 | 1 | 3 |
| **合计** | **10** | **9** | **7** | **16** | **14** | 56 |

（E2-a/E2-b/E3 同结构表见 `qid_flags_*.tsv`；B 桶六批恒为 7（recorded/rank
确定性路由）；at1 8–10、2–5 带 7–12 题波动 = novel 采样方差，与 F_C0=7 同量级。）

### 1.3 关键读数（@1 未中 48 题，C0-a）

- **"金标在 2–5 位"（重排可救）= 11 题，100% novel 路由**。mimo §六.4 与
  RUN_JOURNAL §10.4 的"11 道 @2–5 全走 novel、rank 机制可及 = 0"**复确认**。
  注意：这 11 题的"重排"对象是 **novel 自产的 5 候选自排序**，不是 E1 式
  证据卡 listwise 重排（后者在 dev 触达 0 题）。
- **B（金标组分已在答卷、整串口径判 miss）= 7 题**：005-S01、008-S01、008-S03、
  010-S02、010-S03、010-S04、125-S02 —— 与 mimo C1 第 1 类的 7 题清单**完全一致**；
  全部走 recorded(4)/rank(3) **确定性路由**，不是 novel（见 §4 差异清单）。
- **C1（金标在证据池、答卷未含）= 16 题**：12 novel（C0-a；C0-b 11、E1 12）+
  2 recorded（025-S01、025-S02）+ 2 analogy（095-S05、124-S03）。novel 部分是
  **路由/漏斗丢**（检索到了答案分子，题目却被送进 novel 自由作答）。
- **C2（证据池也没有）= 14 题**：11 novel + 2 recorded（125-S05、135-S06）+
  1 analogy（067-S05）。含 mimo D3 的三道结构性不可答（067-S03、114-S01、
  028-S04）与退化题 149-S06；149-S01 在 C1（题面本身在池中）。
- 证据池含金标 = 36/37/36/36/37（C0a/C0b/E2a/E2b/E3，E1=36 为新读数）——
  与 FULL_SURFACE audit §2 **逐臂复现**。

### 1.4 与全证据面审计（FULL_SURFACE_LEAK_AUDIT §2）对账

C0-b 四格（审计原文口径：证据池 × top-5 整串命中）：

| 分解 | 审计 | 本复算 |
|---|---:|---:|
| 金标在产物候选 & top-5 命中 | 15 | 15 ✓ |
| 金标在产物候选 & top-5 未命中 | 22 | 22 ✓ |
| 金标不在候选 & top-5 命中 | 5 | 5 ✓ |
| 金标不在候选 & 未命中 | 14 | 14 ✓ |

**对账结论：完全复现，但"22 题候选含金被丢弃"的表述需修正**——22 = 6 题
（B 桶里 in-pool 的六题：005-S01、008-S01、008-S03、010-S02、010-S04、125-S02）
**并非被丢弃**，是答卷首位多组分串里就含金标、被整串口径判 miss（改判分即救）；
真丢弃 = 16 题（C1：12 题被路由送进 novel + 4 题 recorded/analogy 选择错）。
另 5 题"不在池却命中"全部 novel（模型参数知识直出金标分子：C0-a 的
053-S03、101-S08、102-S03、103-S03、132-S03）。

### 1.5 对资源投向的含义（M1）

改判分口径 > 改生成（novel 链路）> 改路由/重排承载面：
1. **判分口径**：B 桶 7 题（@1 +6、@3 再 +1），零模型成本、跨六批次稳定
   （确定性路由题）——先做，且须按 mimo 要求新臂预注册。
2. **生成链路（novel）**：dev 的质量大头在 novel——A(11)+C1-novel(12) ≈ 23 题
   可及面；修法是 mimo C2 的确定性守恒约束注入 novel 产出（③④过滤器已在
   M2 验证有 79% 的拦截率）。
3. **重排**：E1 式证据卡重排在 dev 承载面 0（复确认）；可投的重排只有两种
   形态——novel 自产 5 候选的守恒门控重排（救 A），或把 C1-novel 题改路由到
   证据卡重排（需先放宽 rank 入围，见 M2 的噪声警告）。

---

## 2. M2 — E3 第 9–16 张卡的成分（mimo §B2）

### 2.1 主发现：第 9–16 张卡不存在（窗口 8→16 在 dev 是 no-op）

E3 全批 48 个 prediction_task：novel 42（0 候选卡）、analogy 3（1 供体卡）、
rank 3（候选卡数 **2/2/4**：008-S01=4，010-S02=2，010-S04=2）。
rank 入围规则 = 合格 recorded 卡（`prediction.py`：`usable[:max_candidates_for_ranking]`），
三题的合格池本身就 ≤4 张 → **窗口 8 与 16 截断的都是同一个未满的池**。
实测：C0-a 与 C0-b 同三题候选**逐字节相同**（含 evidence_id）；C0-a 与 E3 候选
**产物逐一相同**（差异仅在 run_id/path_id 等运行侧字段）。E3 的 spurious 40、
@5 −3/−4 **不能归因于"多了卡"**，与 novel 采样噪声解释一致（E1 机制诊断同型）。

### 2.2 漏斗分解（E3 三道 rank 题）

| 题 | 检索证据总数 | recorded | rule_application | analog_transfer | 入围（=任务卡数） |
|---|---:|---:|---:|---:|---:|
| 008-S01 | 300 | 4 | 275 | 21 | 4 |
| 010-S02 | 502 | 2 | 8 | 492 | 2 |
| 010-S04 | 502 | 2 | 8 | 492 | 2 |

### 2.3 mimo ①–④ 过滤器占比（若放宽入围，按检索序取"第 9–16 张"）

对三题检索序第 9–16 位共 24 张卡（008-S01 为 enviPath 规则卡 ×8；
010-S02/S04 为 analog 迁移卡 ×16；操作化定义见 scripts/m2_filters.py）：

| 过滤器 | 命中 | 占比 | 说明 |
|---|---:|---:|---|
| ① 底物不同源且无 analog | 0/24 | 0% | 迁移卡的 reactant 即题面底物（cn 相同）；①在此口径无区分度 |
| ② 需 O₂/CoA/ATP/NAD | 0/24 | 0% | 代理判据：新增 P 或 ΔO≥+2，均未触发 |
| ③ ΔC ∉ {0,−1,−2} | **16/24** | **66.7%** | 全部来自 010-S02/S04 的 analog 卡（ΔC +1…+5）；008-S01 规则卡 0/8（ΔC∈{0,−1}） |
| ④ 杂原子增删超出 {O,H} | **19/24** | **79.2%** | analog 卡 16/16 全部新增 N 等杂原子；规则卡 3/8 |
| ①/③/④ 任一命中 | 19/24 | 79.2% | |
| 通过硬滤（③且④皆不违反） | 5/24 | 20.8% | 全部是 008-S01 的 enviPath 规则卡 |

对照：第 1–8 位 24 张卡（含 8 张实际入围的 recorded 卡）①/③/④ 任一命中 15/24
（62.5%）、过硬滤 9/24（37.5%）。⑤（被进攻位点取代基）**需人审**，未自动判。
实际入围的 8 张 recorded 卡：③ 2/8（ΔC=−3 与 −12，均"疑似指定裂解"需人审）、
④ 2/8、过硬滤 6/8。

### 2.4 对资源投向的含义（M2）

**窗口不是 dev 的杠杆**：eligible 漏斗上限 4 张，先改窗口什么都测不出。若真要
把规则/类比卡放进 rank，必须同时上 mimo ③④ 确定性过滤器——放宽后多出的卡
约 80% 会被这两条直接排除（analog 迁移通道 100% 违反），能活下来的主要是
enviPath 规则卡。这与 E3 实测"@5 反降、spurious 升"方向一致：无过滤的宽窗口
只会稀释。

---

## 3. M3 — component_mode 敏感性双轨复算（验证 mimo +6 上限）

用仓内既有实现（`exam_v2.first_hit_rank(..., component_mode=True)`，与
multicomponent_sensitivity 表同一代码路径），对六批答卷零 LLM 重算：

| 批次 | 整串 @1/@3/@5 | 组分 @1/@3/@5 | Δ@1 | Δ@3 | Δ@5 |
|---|---|---|---:|---:|---:|
| C0-a | 8/16/19 | **14/23/26** | +6 | +7 | +7 |
| C0-b | 9/16/20 | 15/23/27 | +6 | +7 | +7 |
| E1 | 10/16/19 | 16/23/26 | +6 | +7 | +7 |
| E2-a | 8/18/20 | 14/25/27 | +6 | +7 | +7 |
| E2-b | 8/16/19 | 14/23/26 | +6 | +7 | +7 |
| E3 | 9/15/16 | 15/22/23 | +6 | +7 | +7 |

**验证结论：mimo 的"+6 题（8/56→14/56）"精确成立**（C0-a 上逐数一致），
且在全部六个批次同为 +6；@3/@5 增益 +7。组分级救回的 @1 六题 =
005-S01、008-S01、008-S03、010-S02、010-S03、125-S02 —— 与 mimo
"第 1 件"列的 6 题**逐一相同**；第七题 010-S04 组分全覆盖、救在第 2 位
（贡献 @3 的 +1）。六批救回题单**完全相同**：这 7 题全走 recorded/rank
确定性路由（非采样题），故该收益对批次/温度/窗口/协议臂全部稳定。

附注（口径边界）：既有 `component_mode` 是"任一组分命中任一金标产物"（宽
any-of）；mimo D1 设想的"组分集合"口径（要求全覆盖）更严——在 dev 的 7 题
救回集上两者**等价**（六题 1/1 全覆盖、两道双金标题 008-S03 与 010-S04 均为
2/2 全覆盖），故 +6 不因口径宽严而变。

### 3.1 对资源投向的含义（M3）

组分级口径的 +6 是六批稳定、零模型成本、可预注册的确定性收益，支持 mimo
"第 1 件事"的优先级：先改判分（或双轨报告），否则所有臂读数被同向污染。

---

## 4. 与 mimo / 既有文档的差异清单（不静默取一）

1. **"+6 上限"：无差异**，精确复现（含 @3/@5 为 +7 的补充）。
2. **mimo C1 第 1 类 7 题清单：无差异**（含 008-S03 双组分全同的复算）。
3. **叙述澄清（非数字差异）**：mimo C2 把"多组分首位被整串判负"的根因记在
   "novel 模式卸掉约束"名下；实测这 7 题走 **recorded(4)/rank(3)** 确定性路由
   （多组分串来自库记录产物本身，如 010-S02 的记录产物即"甲醇.磷酸"两点串）。
   C2 对 novel 大盘（C 组其余 26 题）的诊断不受影响。
4. **FULL_SURFACE audit §2.3 "22 题候选含金被丢弃"**：数字复现，但其中 6 题
   答卷已含金标组分（口径型假丢弃），真丢弃 16 题；"瓶颈是排序/选择把金标丢了"
   的结论需加路由维度：12 题丢在**路由决策**（送进 novel），只有 4 题丢在
   非 novel 路由的选择上，0 题丢在 rank 协议内部排序上。
5. **mimo C3 "rank 可及上界 0"：复确认成立**；补充：若把"重排"理解为
   novel 5 候选自排序（A 桶 11 题）或 C1 路由改判，dev 上仍存在 ~11–16 题
   的"广义重排"可及面——但这不是 E1 协议的形态。

## 5. 数据源与 SHA256

| 数据源 | 说明 | SHA256（前 16） |
|---|---|---|
| dev_questions.jsonl | 冻结题卷 | 8869cd05cea1a442 |
| dev_gold.jsonl | 金标（gitignored，仅离线进程打开） | d285dc0b63546bef |
| answers_C0a/E2b | 拉回答卷 = 官方 answers_sha256 | 9d29ef4649483d9d / 1c6f18e2a8d82007 |
| answers_C0b/E2a | 同上 | ba678fd9b26588e8 / b20ab3f44f091505 |
| answers_E1/E3 | 同上 | 6057a4b192feb6a0 / 927a6e9679e85ec5 |
| pools_C0a/C0b/E1 等 | 逐题证据池身份集（cardval verdicts） | 0385c351d981002c / 8f0efe0aaeaa2038 / 95ca550c7244eee1 … |
| e3_rank_retrieval.json | E3 三道 rank 题全量检索证据 | 2a5d036a34d1b643 |
| meta_*（路由图） | decision.json prediction_mode | 4408cc3c2537c531 … |

远端产物根：`/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs/`
（六个批次根，只读；代码身份 C0/E2/E3 聚合 `fff3b417…4972c`、E1
`3fe38c86…39c3c`，见 ARMS §5/§10）。完整 SHA 清单与拉取脚本见
`scripts/` 与 gitignored `dev_gold/coverage_stat_work/`（m1_dump/ 原始拉取件）。

## 6. 复现命令

```bash
# ① 远端只读拉取（expect SSH；产物落 gitignored dev_gold/coverage_stat_work/）
bash reports/phase_s1_hit60/coverage_stat/scripts/remote_extract.py 的调用方式见
  dev_gold/coverage_stat_work/（base64 通道；本地解码后得 m1_dump/）

# ② M1+M3（金标仅在此离线进程打开；整串 rank 与官方 tsv 逐题对拍 0 差异）
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s1_hit60/coverage_stat/scripts/m1_m3.py

# ③ M1 分解表 / M2 过滤器
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s1_hit60/coverage_stat/scripts/m1_decompose.py
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s1_hit60/coverage_stat/scripts/m2_filters.py

# ④ qid 旗标 TSV（qid+布尔/位次，无任何 SMILES）
python reports/phase_s1_hit60/coverage_stat/scripts/make_tsv.py
```

依赖：conda `depending43`（rdkit 2026.03.6）；判分函数 = 仓内
`pathway_v43.exam_v2`（未改一行）。

## 7. 产物清单

- `COVERAGE_STAT.md`（本文件）
- `qid_flags_{C0a,C0b,E1,E2a,E2b,E3}.tsv`：qid / 路由 / n_pred / rank_whole /
  rank_comp / hit 旗标 / gold_in_pool / 桶旗标（无 SMILES）
- `scripts/`：remote_extract.py、m1_m3.py、m1_decompose.py、m2_filters.py、make_tsv.py
- gitignored 中间件：`dev_gold/coverage_stat_work/`（m1_dump/ 拉取原始件、
  m1_m3_detail.json、m2_detail.json——含运行侧候选身份，不入仓）
