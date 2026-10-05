# HIT60 S1.5 判分口径 v3（component-aware）+ 金标体检 — 实施报告

- 执行：HIT60 T6 实施代理；2026-09-30；全程零 LLM API。
- 任务书：[TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md](TASK_V43_HIT60_S15_DETERMINISTIC_FIX.md)
  （teacher 批复 [TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md](TEACHER_REPLY_V43_HIT60_S0S1_VERDICT_2026-09-30.md)
  §五，批复 SHA256 `3e804e88…`）。
- 预注册（先于任何重刷落盘）：[reports/phase_s15_hit60/PREREGISTRATION_V3.md](../reports/phase_s15_hit60/PREREGISTRATION_V3.md)。
- 封存读数与 SHA 清单：[reports/phase_s15_hit60/dual_track_rescore/](../reports/phase_s15_hit60/dual_track_rescore/)
  （[RESUMARY.md](../reports/phase_s15_hit60/dual_track_rescore/RESUMARY.md)
  / [SEAL_MANIFEST.sha256](../reports/phase_s15_hit60/dual_track_rescore/sealed/SEAL_MANIFEST.sha256)，
  `--check` 复算 8/8 件逐字节一致）。
- 通俗版：[HIT60_S15_CALIBER_V3_REPORT_PLAIN.md](HIT60_S15_CALIBER_V3_REPORT_PLAIN.md)。
- **题域标签（teacher §八.2，强制）**：dev = B1 环境路径中间步骤；
  298 = RHEA 通用酶学；两题域所有数字**双向不外推**。

---

## 0. 一页结论

1. **口径 v3 已按预注册落盘并重刷封存**（主分 = 全 56 分母，口径 v3 单
   变量）：dev C0-a = **14/56 = 25.0%**（teacher 参照 14/56 **精确命中**）；
   C0-b 15/56、C0 均值 14.5/56 = 25.9%。组分救回题单六批完全一致
   （7 题，全走 recorded/rank 确定性路由）。
2. **298 侧 v3 与 teacher 参照 149/298 不符（如实登记，以实测为准）**：
   v3 @1 与整串持平（C0 136=136、D3 132=132）——组分救回 11 题 ↔
   多产物金标「只答对一个也算对」的单产物部分命中降级 11 题**恰好相抵**
   （两臂同型）。v3 在 298 不是单向救分而是再分布：45 道多产物金标题
   v3 miss 33。any-of 参照 149/195/199 我方同代码路径复现无误——
   参照与 v3 的差 = any-of（teacher 明令禁止）与全主产物命中的语义差。
3. **实现核对结论**：既有 `component_mode` 是 any-of（任一组分命中即
   对），**与 v3 细则不一致，已修正**——新增 `gold_main_component_ids` +
   `first_full_coverage_rank`（全主产物命中 + partial 指标）为 v3 主分唯
   一路径；any-of 旧路径原样保留仅作历史敏感性表复现、任何主分禁用。
   同时修正了 v1/v2 整串模式在多产物金标上的隐性 any-of（单组分答对
   其中之一即判中）——149-S04 型按细则移入 partial（E1 @1 +5、E2-b
   @1 +4 的差异源，预注册 §1.2 先期登记，实测吻合）。
4. **注入测试（teacher 条件②）PASS**：合成夹具 22 例（四类错配 +
   已注册超集边界）+ 真实六批答卷注入审计（四类 × 6 批 × 56 题）
   **0 违规、0 洗白**。
5. **金标体检**：dev 56 打标 5 题（与 teacher「3 结构性不可答 + 2 退化」
   逐题吻合：067-S03/114-S01 R1 不可达、028-S04 R3 碳数 4→5、
   149-S01/S06 R4 退化）；quarantine 提案 5 题（分母 56→51，**待人审 +
   mimo 评审后生效**，本轮不生效）；298 全卷只诊断打标 26 题（R1 3 /
   R3 25 / R4 1，不动分数不动金标）。
6. quarantine 变体（待人审）：C0-a 14/51 = 27.5%、C0 均值 14.5/51 =
   28.4%（teacher 路径预算 26–27% 同量级）。

## 1. 口径 v3 的语义（预注册 §0 的操作化）

- 判定单位不变：候选（`steps[].predicted_products` 跨 step 拼接，
  不可解析占名次，空答留分母）；
- 金标主产物组分集合 G = 产物条目按 `.` 拆分逐组分 cn 身份（两卷条目
  内均无点串，与 v2 `gold_ids` 同集；点串拆分为前瞻泛化）；
- **命中 = 某候选的组分集合 ⊇ G**（「全部主产物组分命中」）；
- **partial（单列不进主分）**= 主分未中但答卷覆盖 ≥1 金标组分；
  子旗标 scattered_full = 组分全被覆盖但分散在不同候选（any-of 残影）；
- **any-of 两处禁止**：多组分候选任一组分命中即对（旧 component_mode）
  与多产物金标单产物命中即对（v1/v2 整串隐性 any-of）；
- 超集不破命中（包含语义）：5/批 v3 命中的触发候选含金标外共产物
  组分（金标只收主产物那一半的题面结构所必需，见预注册 §1.2；
  配套 hit_with_extra_components 披露列）。

## 2. 重刷封存值与参照对账

### 2.1 dev 六批（全 56 分母；B1 题域）

| 批次 | 整串（官方锚点复现一致） | **v3 主封存** | Δ@1/Δ@3/Δ@5 |
|---|---|---|---|
| C0-a | 8/16/19 | **14/22/25** | +6/+6/+6 |
| C0-b | 9/16/20 | **15/22/26** | +6/+6/+6 |
| E1 | 10/16/19 | **15/22/25** | +5/+6/+6 |
| E2-a | 8/18/20 | **14/24/26** | +6/+6/+6 |
| E2-b | 8/16/19 | **12/21/24** | +4/+5/+5 |
| E3 | 9/15/16 | **15/21/22** | +6/+6/+6 |

- 参照对账：teacher「dev ≈ 14/56 ≈ 25%」→ C0-a 实测 **精确一致**。
- 与 M3「六批全部 +6@1/+7@3/+7@5」（any-of）的差异：@3/@5 为 +6；
  E1 @1 +5、E2-b @1 +4。差异源 = 149-S04（E1）/149-S04+058-S01（E2-b）
  的整串 any-of 假阳性被 v3 剔除入 partial——**细则禁止方向的另一侧
  生效**，非口径失效；该差异在预注册 §1.2 **先期登记**（发车前已知
  149-S04 型存在及其批间分布），实测与登记吻合。
- 救回/降级题单：救回 @1 六题（005-S01、008-S01、008-S03、010-S02、
  010-S03、125-S02）+ @2 一题（010-S04）六批恒定，全走 recorded/rank；
  降级仅 E1（149-S04）与 E2-b（149-S04、058-S01），均为 novel 路由题。

### 2.2 298 复测两臂（分母 298；RHEA 题域；只读观测 I1）

| 臂 | 整串（官方锚点复现一致） | **v3** | Δ@1/Δ@3/Δ@5 |
|---|---|---|---|
| ec298_pd_retest_C0 | 136/182/186（45.6%） | **136/176/180** | 0/−6/−6 |
| ec298_pd_retest_D3 | 132/174/182（44.3%） | **132/170/176** | 0/−4/−6 |

- 参照对账：teacher「298 post-hoc ≈ 149/298 ≈ 50%」**不成立**（以重刷
  实测为准）。结构：救回@1 = 11、降级@1 = 11（两臂同数），@3 救 11 /
  降 17（C0）与 11/15（D3）。@1 持平的机理 = v1/v2 的「任一产物命中
  即算」在 298 的 45 道多产物金标题上放行了单产物命中，v3 依细则收回
  ——净效应与组分救回相抵。**含义**：覆盖轨道基线（post-hoc 参照）
  在 v3 下 @1 不动（45.6%），@3/@5 收窄；any-of 读数（149/195/199）
  保留为 v2 时代探索性参照、不得混入 v3 主分。
- 298 重算只作口径参照上报，未用于任何调参/择优。

### 2.3 quarantine 变体（另算一版，标「待人审+mimo 评审后生效」）

提案 5 题六批均非命中（模型从未复读题面）→ 分母 56→51：
C0-a 14/51 = 27.5%、C0-b 15/51 = 29.4%、E1/E3 15/51、E2-a 14/51、
E2-b 12/51；C0 均值 14.5/51 = 28.4%。不替代主封存（主封存 = 全 56
分母，口径 v3 单变量）。

## 3. 实现核对与修正（teacher 条件①）

| 项 | 核对结论 | 处置 |
|---|---|---|
| `exam_v2.first_hit_rank(component_mode=True)` | any-of（任一组分命中任一金标产物）——**明令禁止** | 保留原样（历史敏感性表复现用）；v3 主分禁用，新增 `first_full_coverage_rank` |
| v1/v2 整串模式 × 多产物金标 | 隐性 any-of（gold_ids 集合，单产物命中即中）——**同一禁令** | v3 语义下自动降级为 partial（149-S04/058-S01 型） |
| partial 指标 | 缺失 | 新增 `component_coverage_profile`（partial/scattered_full/超集披露列） |
| 空金标防护 | 无 | `gold_main_component_ids` 空集合 fail-closed |

代码落点：`src/pathway_v43/exam_v2.py`（v3 函数 + 版本常量
`v43-exam-caliber-3`，any-of 路径加 deprecated-v3 说明）；测试
`tests/test_exam_v3_caliber.py`；全仓回归 **563 passed / 0 failed**
（基线 541 + 新增 22）。

## 4. 注入测试（teacher 条件②）

- **合成夹具**（`tests/test_exam_v3_caliber.py`，零真实金标，长期钉住）：
  四类（完全命中/缺一组分/部分命中 scattered/多一错误组分）+ 已注册
  超集边界 + 辅助语义（点串条目、不可解析占名次、电荷/立体同 cn、
  重复与乱序）。22 例全绿；其中缺一组分用例**同时钉住 v1/v2 的 any-of
  假阳性被 v3 修复**（旧口径 rank=1，v3 miss）。
- **真实六批注入审计**（`dual_track_rescore/injection_audit.json`）：
  缺一组分（22–26 注入/批，全部命中消失或降位）、多一错误组分
  （miss 题全部仍 miss；命中题追加 = 注册超集边界且旗标 100% 亮起）、
  scattered 对照（4 多金标题/批全部 miss+partial）、完全命中对照
  （56/56 rank=1）。**total_violations = 0**。

## 5. 金标体检与 quarantine 提案（teacher 条件②/§五.2 处置口径）

规则实现 `src/pathway_v43/gold_health.py`（判据**待 mimo 评审冻结**，
`docs/mimo_gold_rules_review_request.md` 在用户手上待送）；产物
[reports/phase_s15_hit60/gold_health_check/](../reports/phase_s15_hit60/gold_health_check/)。

### 5.1 dev 56（提案可处置；题卷金标冻结不改）

| qid | 旗标 | 细节 |
|---|---|---|
| 067-S03 | R1+R3 | 题面缺 CoA 来源（新元素 P/S/核糖骨架；碳 9→30） |
| 114-S01 | R1+R3 | 同上（2-萘甲酰-CoA；碳 11→32） |
| 028-S04 | R3 | 碳数不守恒（肌酸酐 4C → 金标 5C，无碳供物解释） |
| 149-S01 | R4 | 退化（金标=题面 L-canavanine） |
| 149-S06 | R4 | 退化（金标=题面羟胍） |

- R2 保留 1 题（124-S03：新 O，O₂ 环氧化诚实属性）；未列观察 2 题
  （新 N，067/114 的 CoA 氮——判据开放项交 mimo）。
- 提案 = 5 题剔出分母（56→51）；**待人审 + mimo 评审后生效，本轮只出
  提案**；金标翻转纪律（双人确认）仅在人审推翻规则打标时触发。
- 与 teacher §二.5 预期（3 不可答 + 2 退化，5/56 ≈ 9%）**逐题吻合**。

### 5.2 298 全卷（只诊断打标，不动分数不动金标）

26/298 打标（8.7%）：R1 3（S 引入 1、P+核糖 2）、R3 25（碳数 +1…+16，
其中 22 题纯碳增无新元素）、R4 1（退化）；R2 保留 49（新 O）；
未列新元素 3（新 N）。题卷旗标交叉：ambiguous_substrate 4 题**全部**
打标；nucleotide_fallback 5 题 0 打标。池级数字入仓，随下轮汇报。

## 6. mimo 评审（AGENTS.md 三触发点，本任务两处）

1. 规则判据评审请求（触发点 1）：`docs/mimo_gold_rules_review_request.md`
   —— 已在用户手上待送；
2. 结果复核请求（触发点 3，重刷 + quarantine 落盘后产出）：
   `docs/mimo_v3_rescore_review_request.md`（gitignored，含 dev 救回
   7 题 / quarantine 5 题 / 降级 2 题的金标与答卷内容；298 只给池级
   统计）——**待送**。后置不改已冻结判定；评审独立性不做背书，采信
   到与程序证据互证为止。

## 7. 差异与待办登记

1. **298 @1 持平（非 149）**：teacher 参照未复现，已如实登记并以重刷
   封存值为准；覆盖轨道（60% 挂靠轨）的 post-hoc 基线在 v3 下为
   45.6%（@1 不动、@3/@5 收窄）——建议随下轮汇报向 teacher 侧披露
   再分布结构（救 11 ↔ 降 11）。
2. dev @3/@5 增益 +6（非 M3 的 +7）：同因（any-of 剔除侧），先期登记
   且实测吻合。
3. quarantine 5 题处置、R1/R2/R3/R4 判据细化（N/卤素白名单边界、
   核糖 SMARTS 代理、R3 多条目总和语义）：待人审 + mimo 评审。
4. E3 判定改写（rejected → 无效应、不可判）已另行处理，本报告不重复。
5. 后续每一臂（T8 深位召回、守恒过滤等）的对照组 = 重刷后的 C0
   v3 主封存（C0-a 14/56；变体 14/51 待生效后另行引用）。
6. RUN_JOURNAL/ARMS 未动（他代理维护）；历史读数零覆写；本任务全部
   产物新增于 reports/phase_s15_hit60/ 与 docs/（两份报告）；未 git
   commit。

---

## 附录 A：判分口径变迁对齐表（v1 → v2 → v3，历史数字不覆写）

| 轨 | 定义 | 批次数（代表读数） | 参照值 | 变更理由 | 批复出处 |
|---|---|---|---|---|---|
| **v1**（scorer-1，`exam.score_exam`） | 整条候选字符串 cn 比对；agent 现算身份、引擎臂用封存缓存 `product_identity`（可能保留电荷）；多产物金标=任一命中 | EC298 首跑（298 题） | 首跑 39.6% @1（留档不覆盖） | 首跑判分件，身份口径两臂不一致 | EC298 Phase A 任务书 |
| **v2**（scorer-2，`exam_v2`） | 整条候选字符串 cn 比对；**两臂统一从原始 SMILES 现算**（忽略缓存身份）；多产物金标=任一命中（隐性 any-of）；含 `.` 候选只进 any-of 敏感性表 | EC298 复测两臂 + dev 六批 | 298 复测 C0 136/298 = 45.6%（post-hoc 参照）；dev C0-a 8/56 = 14.3%（闭卷基线） | 身份函数勘误（电荷归一两臂统一）；v2 身份勘误属判分定义修正 | teacher 2026-09-28/09-30 回执（EC298 Phase A 验收 + S0/S1 §二） |
| **v3**（caliber-3，本报告） | **组分集合包含判定**：候选组分集合 ⊇ 金标主产物组分集合=命中；partial 单列；any-of 禁止（候选侧+金标侧）；超集不破命中 | dev 六批 + 298 复测两臂（同批重刷，输入 SHA 逐一相同） | dev C0-a **14/56 = 25.0%**（与 teacher 参照精确一致）；298 C0 **136/298 = 45.6%**（@1 持平，参照 149 未复现，如实登记） | 断裂/水解多主产物被整串比对判负 = 判分定义缺陷（dev 7 题实证）；any-of 两处禁止 | teacher 2026-09-30 §五.4（口径 v3 勘误立项批复，SHA `3e804e88…`） |

读数导航：v2 整串官方件 = `reports/phase_s1_hit60/artifacts_remote/*/scoring/`、
`reports/phase_d/retest/scoring/score_v2_{C0,D3}.json`；any-of 敏感性
（v2 时代探索性）= `reports/phase_d/retest/scoring/multicomponent_sensitivity_*.json`
（149/195/199）与 COVERAGE_STAT M3（+6/+7/+7）；v3 封存件 =
`reports/phase_s15_hit60/dual_track_rescore/sealed/`。

## 附录 B：产物清单

- `reports/phase_s15_hit60/PREREGISTRATION_V3.md`（预注册，四条件逐条）
- `reports/phase_s15_hit60/dual_track_rescore/`：`rescore_v3.py`（评分
  driver，锚点 fail-closed + `--check`）、`injection_audit.py`、
  `quarantine_variant.py`、`RESUMARY.md`、`sealed/`（8 件 readings +
  注入审计 + 变体 + `SEAL_MANIFEST.sha256`）、`work/`（gitignored：
  298 金标只读副本）
- `reports/phase_s15_hit60/gold_health_check/`：`gold_health_check.py`、
  打标 TSV（dev/298）、quarantine 提案 TSV、汇总 JSON
- `src/pathway_v43/exam_v2.py`（v3 函数）、`src/pathway_v43/gold_health.py`
  （R1–R4）
- `tests/test_exam_v3_caliber.py`、`tests/test_gold_health_rules.py`
- `docs/mimo_v3_rescore_review_request.md`（gitignored，待送）
- 本报告 + 通俗版
