# RESUMARY — 口径 v3 双轨重算读数（封存件导航 + 差异登记 + 复现命令）

- 执行：HIT60 T6 实施代理，2026-09-30；零 LLM API；判分全程离线。
- 预注册（先于重刷）：[../PREREGISTRATION_V3.md](../PREREGISTRATION_V3.md)。
- 封存清单与 SHA：[sealed/SEAL_MANIFEST.sha256](sealed/SEAL_MANIFEST.sha256)。
- **题域标签（强制）**：dev = B1 环境路径中间步骤；298 = RHEA 通用酶学；
  两题域数字**双向不外推**。
- 历史读数不覆写：本目录只新增；phase_s1 / phase_d 既有官方评分件未动
  （readings 里的整串轨是同输入同代码的锚点复现，非覆写）。

## 1. 封存读数总表（主分 = component v3，全 56/全 298 分母）

### 1.1 dev 六批（B1 题域；整串 v2 → 组分 v3）

| 批次 | 整串 @1/@3/@5（官方锚点，复现一致） | **v3 @1/@3/@5（主封存）** | Δ@1/Δ@3/Δ@5 | partial | scattered |
|---|---|---|---|---:|---:|
| C0-a | 8/16/19 | **14/22/25**（25.0%/39.3%/44.6%） | +6/+6/+6 | 1 | 1 |
| C0-b | 9/16/20 | **15/22/26**（26.8%） | +6/+6/+6 | 1 | 0 |
| E1 | 10/16/19 | **15/22/25**（26.8%） | +5/+6/+6 | 1 | 1 |
| E2-a | 8/18/20 | **14/24/26**（25.0%） | +6/+6/+6 | 1 | 0 |
| E2-b | 8/16/19 | **12/21/24**（21.4%） | +4/+5/+5 | 2 | 1 |
| E3 | 9/15/16 | **15/21/22**（26.8%） | +6/+6/+6 | 1 | 0 |

- **C0 基线封存（v3）**：样本 a = **14/56 = 25.0%**（与 teacher 参照
  14/56 **精确一致**）；样本 b = 15/56 = 26.8%；两样本均值 14.5/56 = 25.9%。
- 组分级救回题单**六批完全一致**：@1 六题 = 005-S01、008-S01、008-S03、
  010-S02、010-S03、125-S02（+第 7 题 010-S04 救在 @2，贡献 @3/@5）；
  全部走 recorded/rank **确定性路由**（novel_proposal 路由零涉及）——
  与 COVERAGE_STAT M3 的救回题单逐一相同。
- **与参照的登记差异**：M3/teacher 的「六批全部 +6@1/+7@3/+7@5」是
  any-of 敏感性口径；v3 全主产物命中语义下 @3/@5 为 **+6**（非 +7），
  且 E1 @1 为 +5、E2-b @1 为 +4。差异源（预注册 §1.2 已先期登记）：
  v1/v2 整串在**多产物金标**上事实是 any-of——E1 整串 @1 含 149-S04
  （单组分命中双金标之一）、E2-b 另含 058-S01，v3 依细则将其移入
  partial（救回集不变，纯剔除侧差异）。**这正是 any-of 禁令的另一侧
  生效，非口径失效。**
- 超集披露列：hit_with_extra_components = 5/批（触发候选含金标之外
  共产物组分的题，含语义已注册边界）。

### 1.2 298 复测两臂（RHEA 题域；只读观测，I1：只作口径参照）

| 臂 | 整串 @1/@3/@5（官方锚点，复现一致） | **v3 @1/@3/@5** | Δ@1/Δ@3/Δ@5 | partial | scattered |
|---|---|---|---|---:|---:|
| ec298_pd_retest_C0 | 136/182/186（45.6%） | **136/176/180**（45.6%） | 0/−6/−6 | 19 | 5 |
| ec298_pd_retest_D3 | 132/174/182（44.3%） | **132/170/176**（44.3%） | 0/−4/−6 | 19 | 3 |

- **与参照的登记差异（重要）**：teacher 参照「298 post-hoc ≈ 149/298 ≈
  50%」来自 any-of 敏感性读数（136→149）。v3 全主产物命中语义下 **@1
  与整串持平（136=136）**：组分救回 11 题 ↔ 单产物部分命中降级 11 题
  恰好相抵（两臂同型；any-of 读数 149/195/199 我方代码路径同源复现
  无误）。即：**298 侧 v3 不是单向救分，而是再分布**——多组分答卷
  救回的同时，多产物金标的「只答对一个也算对」按细则降级为 partial。
  45 道多产物金标题中 v3 miss 33。
- 累计覆盖敏感性辅读（不进主分）：C0 136/179/185；D3 132/172/179。

### 1.3 quarantine 变体（不替代主封存；**待人审 + mimo 评审后生效**）

[sealed/quarantine_variant_dev.json](sealed/quarantine_variant_dev.json)：
分母 56→51（提案 5 题剔出；五题在六批均非命中，模型从未复读题面）：

| 批次 | v3 @1（/51） | 率 |
|---|---|---|
| C0-a | 14 | 27.5% |
| C0-b | 15 | 29.4% |
| E1 | 15 | 29.4% |
| E2-a | 14 | 27.5% |
| E2-b | 12 | 23.5% |
| E3 | 15 | 29.4% |

C0 变体均值 14.5/51 = 28.4%（teacher 路径预算「14/51–53 ≈ 26–27%」
同量级、以实测为准）。

## 2. 注入审计（条件②，真实六批答卷）

[sealed/injection_audit.json](sealed/injection_audit.json)：四类错配
注入 × 六批 × 56 题，**total_violations = 0，verdict = PASS**。
- 缺一组分：22–26 注入/批，全部命中消失或降位；
- 多一错误组分（miss 题追加错误组分）：全部仍 miss（0 洗白）；
  命中题追加错误组分 = 已注册超集边界，hit_with_extra 旗标 100% 亮起；
- 部分命中（scattered 对照组）：4 多金标题/批全部 miss+partial；
- 完全命中对照组：56/56 批全 rank=1。
合成样例版（长期钉住）：`tests/test_exam_v3_caliber.py`（22 例全绿）。

## 3. 金标体检导航

[../gold_health_check/](../gold_health_check/)：dev 56 打标 5 题
（R1 2 / R3 3 / R4 2，独立 R3 1；R2 保留 1）；298 全卷只诊断打标
26 题（R1 3 / R3 25 / R4 1，R2 保留 49；不动分数不动金标）。
quarantine 提案表 [../gold_health_check/quarantine_proposal_dev.tsv
](../gold_health_check/quarantine_proposal_dev.tsv)（处置建议=剔出分母，
**待人审生效**）。规则合成夹具：`tests/test_gold_health_rules.py`。

## 4. 复现命令（本地 conda depending43，零 LLM）

```bash
# dev 六批（示例 C0-a；其余五批换 answers/meta/锚点，见 SEAL_MANIFEST 各件 answers_sha256）
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/dual_track_rescore/rescore_v3.py \
  --answers reports/phase_s1_hit60/dev_gold/coverage_stat_work/m1_dump/answers_C0a.jsonl \
  --gold reports/phase_s1_hit60/dev_gold/dev_gold.jsonl \
  --label s15_dev_C0a --out-dir /tmp/rv3_out \
  --routes-json reports/phase_s1_hit60/dev_gold/coverage_stat_work/m1_dump/meta_C0a.json \
  --anchor-whole 8,16,19 \
  --expect-answers-sha 9d29ef4649483d9daa76a78adc28fafa3d9f9a9da43c2f9d368c26b2050a75e5 \
  --expect-gold-sha d285dc0b63546bef3799f71a6065feeaa60bf202a97597b7431b4e4265262f2a

# 298 两臂（金标 = gitignored 只读副本，SHA 9f5955d4…；answers = reports/phase_d/retest/*/merged_predictions.jsonl）
#   --anchor-whole 136,182,186（C0）/ 132,174,182（D3）

# --check 复算（封存件逐字节一致；8/8 PASS 已验）
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/dual_track_rescore/rescore_v3.py \
  --check reports/phase_s15_hit60/dual_track_rescore/sealed/readings_s15_dev_C0a.json \
  --answers … --gold … --label s15_dev_C0a [--routes-json …]

# 注入审计 / quarantine 变体 / 金标体检
python reports/phase_s15_hit60/dual_track_rescore/injection_audit.py
python reports/phase_s15_hit60/dual_track_rescore/quarantine_variant.py
python reports/phase_s15_hit60/gold_health_check/gold_health_check.py

# 测试（注入四类 + 规则夹具 + 全仓回归）
OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest tests/test_exam_v3_caliber.py tests/test_gold_health_rules.py -q
```

输入金标红线：dev_gold/ 与 dual_track_rescore/work/（298 金标副本）
均 gitignored；封存件只含 qid/计数/位次/旗标，零 SMILES。
