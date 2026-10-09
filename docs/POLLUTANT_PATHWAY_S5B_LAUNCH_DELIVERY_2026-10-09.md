# pollutant_pathway_v1 S5b 启动批交付书（POLLUTANT_PATHWAY_S5B_LAUNCH_DELIVERY_2026-10-09）

日期：2026-10-09。实施代理：本批唯一实施会话。仓库
`/Volumes/CC/Enzyme_Agent/dependingv43`，分支 v4.3，父提交
`4fe1e0a`（S5b 准备批，已审），本批在其上交付。

> **回修批订正注记（2026-10-09，S5B-L01/L02，复审
> `docs/POLLUTANT_PATHWAY_S5B_CODEX_REVIEW_2026-10-09.md`）**：本
> 交付书为启动批原始交付记录，下列声明已被回修批订正，读时以
> 回修交付书
> `docs/POLLUTANT_PATHWAY_S5B_REWORK_DELIVERY_2026-10-09.md` 与
> 预注册稿（已含 S5B-L02 订正）为准：
> ① §1.3/§1.4 契约登记 evaluation-4/profile-24 已升
> evaluation-5/profile-25（S5B-L01 real 档配对守卫）；
> ② §1.6 父基线红绿细分"6 新行为 + 3 新披露 + 4 新守卫 + 1 新
> 版本 + 5 旧版本"不准确——按首失败重分类为 **4 配对返回/效果
> 行为红 + 4 未发生指定 EvaluationContractError 守卫红 + 5
> KeyError('pairing') 缺字段红 + 6 版本字面量红**（总数 19 一致；
> multiple-export/order/deterministic 等父案先停在缺字段，后段
> 未执行，不得冒称行为已翻转）；
> ③ §2 核心发现 2/3 的"整串多报即不中/同向/宽向不存在"表述有
> 方向性事实错误（老侧需按展平分串/点串融合分形；见订正后预
> 注册 §5.1）；
> ④ §4/§7 的"r26 未送/Chenyu 未恢复"是本批提交时点快照，已被
> 最新用户来源推进（r26 已送已回、Chenyu 已恢复，发车当日实核
> 仍为硬门）。

**定位**：S5b 正式开跑前的**代码修复 + 预注册冻结稿汇编批**。
三任务：① evaluation-4 配对修复（mimo r25 ⚠️P1-9 G1 配对错位，
用户已裁定修评测器不回退 G2）；② superset-hit 与老 scorer 同构
核验（只读分析，不改码）；③ 预注册冻结稿汇编。

**本批不做**（硬边界，均遵守）：不执行任何真实模型调用、不花钱、
不启动正式 S5b 评测/冒烟、不访问 Chenyu（隧道不通）、不 push、
金标内容零入仓（提交前两层扫描在案，见证据 `gold_leak_scan.txt`）、
冻结判据正文/FREEZE_RECORD/path_context 逐字节不改（SHA 复核在案）、
评审侧未跟踪文件零触碰、封存 run 只读。

## 1. 任务一：evaluation-4 配对修复（代码批）

### 1.1 问题（mimo r25 ⚠️P1-9，主会话读码核实为真）

`_pair_exports_to_samples` 按根严格身份**首中即 break** +
`digests[0]` 取首位（digest 字典序）——53 个重复底物下同根的两个
export 全配给排序在前的图：该图可能拿**另一题的 run** 判自己的边
（判分张冠李戴），后图 `not_evaluated_export_missing` 大面积
pending。

### 1.2 修复设计（最小收口，仅配对语义变更）

- **图侧 qid**（权威声明点）：评测输入 `reference_graph_manifest`
  条目 `qid` 子字段；一致性核：必须出现在该图 `root_entity.source_refs`
  （转换规则 §2.2 图侧携带 qid），不符 ⇒ 结构化拒
  （`reference_graph_qid_not_in_source_refs`）；跨条目重复 qid ⇒
  拒（`evaluation_input_duplicate_qid`）。
- **导出侧 qid**（run↔qid 映射落点）：`native_path_exports` 条目
  `qid` 子字段；其 `run_id` 与 read_native_export 返回 payload 的
  权威 `run_id` 绑定核验，不符 ⇒ 结构化拒
  （`evaluation_export_run_binding_mismatch`）——qid↔run 映射与
  导出 run/identity 链断裂时不采信声明侧。
- **严格 qid 档**（任一侧声明 qid 即全局生效）：图只配同 qid 的
  可读导出；**qid 无匹配导出 ⇒ not_evaluated + reason 明示 qid
  未配到（`sample_qid_unpaired`，机读携带 qid 与"是否曾被导出条目
  声明"），不按根身份张冠李戴**；严格档下未声明 qid 的图不回退根
  身份（单独 reason `graph_qid_missing_in_strict_pairing`——回退
  即重新引入首中即 break 错位）；未声明 qid 的导出不配任何图
  （unmatched_exports 披露）。
- **回退档**（两侧均无 qid 声明 ⇒ 合成夹具路径）：沿用
  evaluation-3 根严格身份配对（首中即定、digest 字典序），机读披露
  `pairing_basis=root_identity_fallback`（样本级 + coverage_report
  级，不静默）。
- **同一 qid 多导出**：配对清单按输入 `native_path_exports` 清单序
  （显式清单序），消费 digest = 首位，`consumed_export_digest` +
  `digest_selection_rule` 机读披露（确定性，不随机）。
- 每导出至多配一个样本（两档同此约束）；coverage_report 新增
  `pairing` 块（bases/qids/paired digests/consumed digest/selection
  rule 逐图机读）。
- **新增消费的输入子字段仅两个**（S5-25 纪律如实登记）：manifest
  条目 `qid` 与导出条目 `qid`（见 evaluation.py 模块头与
  `consumed_field_policy`）。

### 1.3 契约登记与版本

- `ppv1-evaluation-3 → ppv1-evaluation-4`（配对语义变更升版，不偷换
  已登记契约；匹配/条件/指标/守卫判定零触碰）；
- `ppv1-profile-23 → ppv1-profile-24`（身份块携带 evaluation-4；
  profile.py 双处历史注释登记）；
- reference-graph-1 / split-manifest-1 字段形状零变化（qid 是输入
  条目级子字段与消费侧语义）；preregistration-template-3 不变。

### 1.4 改动文件（src 2 + tests 7）

- `src/pathway_v43/pollutant/evaluation.py`（模块头 evaluation-4
  说明 / qid 子字段校验 + 重复 qid 拒 / 图侧 source_refs 一致性核 /
  导出装载处 run 绑定核 / `_pair_exports_to_samples` 重写为 qid
  感知双档 / 样本级 pairing 披露 + qid 缺配 reason /
  coverage_report.pairing 块 / consumed_field_policy 更新）；
- `src/pathway_v43/pollutant/profile.py`（evaluation-4 + profile-24
  登记与历史注释）；
- `tests/test_ppv1_s5b_pairing.py`（**新**，14 条回归，见 1.5）；
- 版本字面量同步 6 文件：`tests/test_ppv1_profile.py`、
  `tests/test_ppv1_s4b_export.py`、`tests/test_ppv1_s5a_schema.py`
  （run_identity fixture 字面量，父上绿）、
  `tests/test_ppv1_s5a_rework_r1.py` / `r2` / `r3`。

### 1.5 新回归（14 条；公共链真实生成，判分不串可证）

夹具纪律：两题同底物 CCO、不同合成 qid（`RXNG-SYNTH-A/B`，与真实
RXNG_* 题面零重叠）、可区分计划（一题事件带 `[H][H]` 共同产物、
一题不带）——两导出按 e-alt-1/e-alt-2 覆盖结果互相区分；run 全部
走公共 `start_run` 真实生成，导出经 `read_native_export` 首消费
（多 run 分发 reader 按条目 run_id 取各自 ledger）。

1. **同底物两 qid 各配各的**（判分不串）：两题均 scored、各消费
   自己 run 的 digest、交叉反相覆盖模式（A：e-alt-1 严格/e-alt-2
   超集降档；B：e-alt-2 严格/e-alt-1 必要节点未覆盖）——配错即翻；
   零 unmatched；
2. **qid 缺配导出不张冠李戴**：排序在前的缺配图 not_evaluated +
   `sample_qid_unpaired`（qid 机读携带）+ 注明不回退根身份，持有
   导出的图正常判分（父基线：前者抢走导出、后者 pending）；
3. **qid 声明的导出条目读取失败**：仍 not_evaluated + reason +
   `qid_declared_by_export_entry=True` 披露；
4. **严格档无 qid 图不回退**：单独 reason，不抢有 qid 图的导出；
5. **孤儿导出（无人认领 qid）**：unmatched_exports 机读披露；
6. **无 qid 合成夹具回退 + 披露**：行为与 evaluation-3 一致
   （scored、consumed digest 同），`pairing_basis=
   root_identity_fallback` 样本级 + coverage_report 级机读披露；
7. **同 qid 多导出显式清单序**：消费清单首位、倒序输入消费另一端
   （双向可证）、paired 全清单与 consumed digest 披露；
8. **排序无关性**：倒排导出清单 ⇒ 各图消费 digest 不变；
9. **四个 fail-closed 契约守卫**：manifest qid 不在 source_refs
   拒 / 重复 qid 拒 / qid 条目 run 绑定不符拒（单 ledger 错接线
   场景）/ 空 qid 字符串拒（空值不静默当未声明）；
10. **确定性**：同输入重复评测 output_sha256 与 pairing 披露一致；
11. **契约登记**：evaluation-4/profile-24 + reference-graph-1/
    split-manifest-1 不变。

### 1.6 验证数字（三套）

| 验证 | 命令口径 | 结果 |
|---|---|---|
| PPV1 全量 | 44 个 `tests/test_ppv1_*.py`，`-B` + `-p no:cacheprovider`，仓内树 | **1133 passed / 0 skipped / 0 failed，exit 0**（1119 存量 + 14 新） |
| 父基线红绿 | 4fe1e0a detached 同字节 worktree（src/pyproject 与父同字节；6 测试文件以当前字节覆盖 + 1 新文件，已披露），7 文件 149 nodeid | **19 failed / 130 passed / 0 collection errors，exit 1**；红分类（S5B-L02 复审订正，按**首个实际失败**）：**4 配对返回/效果行为红 + 4 未发生指定 `EvaluationContractError` 守卫红 + 5 `KeyError('pairing')` 缺字段红 + 6 版本字面量红**——原报"6 新行为+3 新披露+4 新守卫+1 新版本+5 旧版本"细分不准确（总数一致）；multiple-export/order/deterministic 等父案先停在缺字段，后段未执行，不得冒称行为翻转 |
| G01 安全隔离 | 沿 R7→…→s5a_rework_r3→s5b_launch 谱系允许清单隔离副本（306 存量 + 1 新 = 307 输入），tmp 全量 `tests/` | **attempt1 首跑即成：1733 passed / 10 skipped / 17 deselected，exit 0**（r3 基线 1719 + 14 新，精确吻合）；输入 SHA 前后复验零不符；8 个合法变更输入 vs r3 集脚本强制披露；7 个隔离 pyc 如实登记 |

真实仓树未跑 `tests/` 全量（G01 纪律）；隔离副本 243MB 留 tmp 不入
包（`g01/attempt1/input_trees_note.json`）。

## 2. 任务二：superset-hit 与老 scorer 同构核验（只读分析，零改码）

**核验对象**：老 scorer v2（`v43-ec298-scorer-2`，
`src/pathway_v43/exam_v2.py`）+ Phase A 报告（`docs/
EC298_PHASE_A_REPORT.md` §1/§3）+ Phase D 复测报告（`docs/
EC298_PHASE_D_RETEST_REPORT.md` §4/§10）；对照 S5 评测器
（evaluation-3/4）边匹配语义（S5A-03 后必要节点覆盖严格匹配）。

**核心发现（三条）**：

1. **老 scorer v2 官方主口径**（产出首轮 116/128/130 与复测
   136/182/186）：cn 身份（电荷归一+立体盲）+ **整条候选字符串** +
   **任一金标产物相等即命中**（any-one；多产物金标报对一个即中）；
   多组分候选主口径不命中（只进"任一组分"敏感性另表）；分母 298
   固定，空答/失败全算未命中。
2. 模块内的 **caliber v3**（`first_full_coverage_rank`："G ⊆ S"、
   超集不破命中）是 HIT60 S1.5（dev 题域）判分勘误口径，**不是
   298 官方主分**——prep §2.3 把"全 principal"类比作"caliber v3
   同构"、mimo r25 据此把旧口径读成"候选 ⊇ 金标即命中"，经本轮
   实读代码**订正**：旧官方口径既非"超集不破"也非"全金标覆盖"
   （是 any-one）。**S5B-L02 再订正**：老侧"多报即不中"只对
   **点串融合**包装成立；**展平分串**下额外字符串不破 any-one
   命中（合成互证：候选 `['CCO','CO']` 对金标 {cn(CCO)} 老侧
   rank=1）——两侧行为须按包装分形叙述（订正后预注册 §5.1 表）。
3. **结论：新旧不同构，且新主口径系统性更严（S5B-L02 限定：
   命中存在性与指定报告映射层面）**（四轴：身份 cn→严格、金标
   覆盖 any-one→全金标集合相等、判定单元 字符串→事件双侧（反应
   物侧集合相等 + step_scope 一致）、排序源 报告序→提交时序）。
   **不再声明"宽向不存在/超集同向"的未限定版本**：展平分串下
   老侧容忍额外串（新对多报降档是新增更严约束）、点串融合下
   同向；K 单位/报告宽度/输入宇宙两轴使 hit@K 逐档数字可双向
   移动，不作逐 K 单调更严声明。逐情形差异清表（含订正）已
   冻结进预注册 §5.1。

**处置（预注册落字，冻结稿 §5）**：不宣称同构；通过线
116/128/130 冻结为"达到老系统首轮水平"**参照线锚**（S5B-L02：
该短语只与敏感性表数字绑定使用，四象限报告规则见预注册
§5.3）；主口径（hit@1/@3/@5，候选事件按提交时序报告序）+
**老口径敏感性表**（第二口径，复刻官方主口径判据：候选序列 =
导出事件报告序 × 事件内 report_rank 序展平的产物 SMILES、整串
cn any-one、`report_rank=None` 只纳非 None 位次并省略披露）双
口径并列报告，两口径差 = 口径差（非系统性能差）；superset 收口
（mimo r25 #6）：新主口径不含 superset 命中（一律 coverage
partial 披露桶），**与老官方主口径的关系按候选包装分形
（S5B-L02 订正：展平分串下新更严、点串融合下同向）**、与
HIT60 caliber v3 异向，三者关系写死。

## 3. 任务三：预注册冻结稿汇编（文档批）

交付 `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`
（**状态 `preregistration_pending_final_confirmation`**——用户未做
最终确认读前不算冻结完成）。汇编依据：prep §5 的 20+2 选择题
（**用户 2026-10-09 已圈"全按推荐档"**）+ mimo r25 收口清单全部
条件 + 任务二同构核验结论 + **用户 2026-10-09 并发改 40 指令**。
逐项写死冻结值：

- 主指标 = 参考边召回 hit@1/@3/@5（判定单元/候选事件报告序/rank/
  分母细则冻结）；**通过线 = hit@1≥116/298（38.93%）、
  hit@3≥128/298（42.95%）、hit@5≥130/298（43.62%）**（口径"达到
  老系统首轮水平"参照线锚，双口径并列报告，不宣称同构）；
- 分母固定 298 全算未命中（无覆盖不足剔题出口）；轨道 A
  `known_evidence_reconstruction` + 结论句式带题域标签；G1 一题一图
  + qid 感知配对（evaluation-4）；known_gaps 落字（mimo ⚠️P1-3）：
  "图级 known_gaps 仅为披露字段，不自动使该图 unmatched 边免计
  分母责任；真正不可判的边只经 not_evaluable_edge_ids 逐边登记"；
- 重复采样不允许；费用逐调用 + 缺 usage 保守预留 + 账单回填 +
  当日价格快照；**并发目标 40 在途**（2026-10-09 用户指令改 40，
  沿老复测口径：每批最多 40 个题目 worker、全局最多 40 个真实
  API 请求同时在途；原 80 方案作废；实测峰值如实披露、工程验收
  单列）；失败/超时/孤儿全占额度 + 全留分母 + 单独表；
- 独立性：重复底物 89 题标 `related`、其余 `unknown`（enzymemap
  5 ID 共享题 related；无题标 independent）；CI = bootstrap 按
  source group 聚类（主）+ Wilson 按题（敏感性）+ S2 按底物归并
  敏感性必报一档；
- mimo r25 四面条件全部落字：step_scope=net_reaction + 无守恒声明 +
  逐题例外规则 + 须存在净形事件披露 + 一致率不得当机理证据；全
  principal 入 to_node_ids + "口径选择不是化学认定"披露 + 禁
  启发式 + 同结构共同产物按集合匹配份数不在判分面；participant
  partial + 固定披露句（473 剥离/无计量声明）+
  source_complete/declared_complete 禁用 + coefficient unknown；
  严格为主 + CN 旁证封顶 + 电荷/立体/互变三类低估方向预披露 +
  互变等价轴本轮不加；reference_only + provenance 筛选事实
  （chemistry_audit + microbe-confirmed，不升 observed）；
- `key_intermediate_recall` 本题域恒空不可评（如实披露）；
- **冒烟后定型再冻结的项**（机制冻结、数值不预支）：①P1 请求
  计数上限（候选：每 run 3+2 反馈轮 / 批级 894+冒烟余量）；
  ②并发实测安全值（40 基准，若不可达如实报峰值）；③单题/全量
  费用与时长预估区间。冒烟属标定不属正式评测（如实写明；段 2 =
  40 路小批）；
- 发车前最终确认清单：①用户最终确认读（冻结稿全文过目后方可
  开始冒烟——预注册纪律）；②Chenyu 隧道恢复（用户同事在开）；
  ③题集三锚 SHA 发车前再核。

**冻结稿条目计数**：二十项选择题逐项冻结值（§6 表，每项一行）+
两项前置（P1/P2）+ 主指标判定细则 4 段（§5.2–5.4）+ 四面转换
规则 6 条（§3）+ known_gaps 处置（§4）+ 独立性/CI 5 条（§7）+
冒烟四段与三项冒烟后定型（§8）+ 发车三项硬门（§9）。

## 4. mimo 评审

- 本批送审 `docs/mimo_ppv1_chem_review_request_r26.md`（提交时点
  **写好未送**，由用户送 mimo；自包含、规则级+合成例、零金标）：
  两面——
  ①evaluation-4 qid 感知配对语义（qid 配对键合理性/回退边界/多
  导出选择/严格档 fail-closed 方向/冻结判据冲突检查）；②superset
  同构结论与双口径安排（差异清单漏轴复查/"系统性更严"方向声明/
  提交时序报告序可信度/敏感性表候选序列忠实性/通过线锚挂法）。
- 回复原文落盘 `docs/` 后采信到与程序证据互证为止；采信若有订正
  （如差异清单漏轴），走预注册确认读前修订——冻结稿尚在
  pending_final_confirmation，属合法修订窗口。

## 5. 证据

`docs/review_evidence/ppv1_s5b_launch_2026-10-09/`：

- `ppv1/`：PPV1 全量（44 文件 1133 过）junit/stdout/stderr/执行
  记录/文件清单；
- `parent_baseline/`：父 4fe1e0a detached 同字节 worktree 红绿
  （19 红/130 绿/0 收集错；`execution_record.json` 红分类
  observed==declared 精确闭合；src/pyproject 与父同字节、六测试
  文件当前字节覆盖 + 一新文件已披露）；
- `g01/`：G01 安全隔离 attempt1 首跑即成（1733/10/17，exit 0；
  307 输入 SHA 前后零不符；8 变更输入 vs r3 集披露；243MB 输入
  副本树留 tmp 不入包）；`incidents.json` 零事故（含一次准备阶段
  路径口径失败的如实披露，未跑任何测试）；
- `frozen_integrity.json`：criteria-v1 冻结正文 7fd35aab… /
  FREEZE_RECORD 6e046e29… / path_context 971ad00f… 与父及 r3 登记
  逐字节一致；
- `gold_leak_scan.txt`：提交前两层金标零泄漏扫描（整词精确匹配
  全零；子串层仅 'C=O' 短片段，系合成例 'CC=O' 内部片段非独立
  取值；提交前对交付书/README 复扫补录）；
- `scripts/safe_g01_s5b_launch.py`：G01 控制器（r3 谱系适配，本身
  纳 SHA）；
- `manifest.json` + `SHA256SUMS`：唯二控制文件，`shasum -c` 全绿。

## 6. 提交

- 本批提交（v4.3 本地，**不 push**）：src 2 文件 + tests 7 文件
  （1 新 6 改）+ docs 3 文件（冻结稿/r26 请求/本交付书）+ 证据目录
  （显式路径 git add）。
- 环境纪律：`~/miniconda3/envs/depending43/bin/python -B`、
  `PYTHONDONTWRITEBYTECODE=1`、`pytest -p no:cacheprovider`、
  `OMP_NUM_THREADS=1`、先 cd 仓库根。

## 7. 未完成项（如实）

1. **用户最终确认读**未做——冻结稿保持
   `preregistration_pending_final_confirmation`，冒烟与正式 S5b
   均未开始（本批零真实模型调用、零费用，硬边界遵守）；
2. **mimo r26 未送**（提交时点快照；**回修批同步：r26 已送、
   回复已落盘** `docs/mimo_ppv1_chem_review_response_r26.md`，其中
   两项事实判断经复审纠错——回退档硬门已按 L01 落码、老侧错格
   已按 L02 订正；r26 定位为**发车前规则/配对口径复核**，非
   AGENTS 三触发点之 3 的履行；r27 请求见回修交付书）；
3. **Chenyu 隧道未恢复**（提交时点快照；**回修批同步：用户
   2026-10-09 最新来源已恢复**——"已恢复"与发车当日实核分开，
   远端题集/金标权威 SHA 当日实核仍顺延至发车硬门 §9-②③）；
4. P1 请求计数上限数值与并发实测安全值：**冒烟后定型再冻结**
   （机制与候选值已冻结，数值未预支）；
5. 真实 298 参考图转换脚本/gitignore 变更：属 S5b 正式实施批
   （本批纯代码+文档）。
