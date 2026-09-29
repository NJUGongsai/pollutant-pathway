# EC298 Phase D 修复后配对复测 — 发车前不可变实验登记

> 实验统一标签:`seen298_post_hoc_repair_check`。
> 任务书:[TASK_V43_EC298_PHASE_D_RETEST_298.md](TASK_V43_EC298_PHASE_D_RETEST_298.md)。
> **不可变性声明**:本登记在**首次付费 API 调用之前**写定并计算全文 SHA;此后
> 原文不得回写修改,只允许在文末「勘误记录」节**追加**新记录(每条勘误注明
> 时间与范围)。两臂 batch identity SHA 在身份文件落盘后、首次付费调用前以
> 勘误 #1 追加。
>
> 本登记不含任何密钥、金标内容(products_smiles/类别/原始反应)或 298 题
> 答案信息;金标 SHA 仅以摘要形式出现。

## 0. 研究问题与臂定义

同一冻结 298 题、同一修复版代码(HEAD `eb3ba7f`)、同一 scorer v2 下,两臂
配对比较(每父实际评估供体上限均为 3,v1 运行资产,不使用 v2 映射资产):

| 臂 | 批次根(Chenyu dependingv43) | `reactant_similar_enabled` | 其余配置 |
|---|---|---|---|
| C0 | `runs/ec298_pd_retest_C0/` | `false`(相似供体通道关闭) | 与 D-3 逐键一致 |
| D-3 | `runs/ec298_pd_retest_D3/` | `true`(D1 固定参数开启) | 与 C0 逐键一致 |

D-3 开启时所需固定 D1 参数(沿 [PHASE_D_D1_PARAM_CARD.md](PHASE_D_D1_PARAM_CARD.md)
与 `SIMILARITY_VERSION=v43-rsim-1`):Morgan r2/b2048、Tanimoto ≥ 0.45(含边界)、
检索 top-K 16;`max_analogy_donor_candidates=3`。两臂的
`reactant_similar_threshold=0.45`、`reactant_similar_top_k=16`、
`max_analogy_donor_candidates=3` **取值相同**:关闭时
`workflow/nodes.py` 强制 `threshold, top_k = 0.0, 0`(参数惰性),行为与 C0
旧检索配置一致;唯一行为差异即 `reactant_similar_enabled` 一个键。
**结构化配置 diff**(机器可读,38 个扁平键比较):见
`reports/phase_d/retest/config_diff.json`,value_differences 恰为
`prediction_policy_overrides.reactant_similar_enabled` 一项(false/true)。

不运行 D-5/D-10;不做超时/排序/预算/语料优化;两臂不使用 v2 映射资产。
本轮结论措辞限定为「在已见 298 题、这次冻结配置下观察到的差异」;
`reactant_similar_enabled` 发布默认保持 `false`。

## 1. 冻结输入(SHA 锚当日独立重算)

| 项 | 值(2026-09-29 实核) |
|---|---|
| 题卷源 CSV SHA256 | `a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a`(本地独立重算一致) |
| `questions.jsonl`(金标)SHA256 | `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`(本地/Chenyu `ec298_gold_readonly/` 双侧一致) |
| 运行白名单 `exam_inputs.jsonl` SHA256 | `cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703`(Chenyu 首轮冻结件拉回本地重算一致) |
| 白名单内容核验 | 298 行;qid 唯一;与 questions.jsonl qid 顺序逐一相同;逐题 substrate_smiles 相同(0 mismatch);`input_index` 0..297 顺序;字段恰为 `qid/substrate_smiles/input_index`(无金标字段) |
| 白名单分发 | 首轮冻结件路径失效时的处置 = 按首轮任务书冻结源重建并解释字节差异(本轮未触发,直接复用冻结件) |

金标隔离:金标 `products_smiles`/类别/原始反应/历史命中信息不进入
PredictionTask、检索、模型提示、batch/run identity 或运行日志;金标只在
两臂答卷与身份**封存后**由独立零 LLM 评分进程读取(§6)。

## 2. 代码与资产身份(与验收一致)

| 项 | 值 |
|---|---|
| Git HEAD(开工) | `eb3ba7f7dc52fdccad4956346bfd2c5cefe1e7f4`(分支 v4.3,提交 2026-09-29 00:51 +0800) |
| 开工 git status | 干净(工作树无未提交改动;本轮新增文件均为 untracked,旧产物零改写) |
| 代码身份 | aggregate `07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc`(50 文件;与 R1 修复验收一致) |
| Chenyu 部署 | `/usrdata/EnzymeCAGE_data/workspaces/dependingv43`;逐文件 SHA 与本地一致(124 文件 0 mismatch;本地多出的 2 个文件为与本轮无关的离线诊断脚本 `scripts/phase_b_offline_diagnostics.py`、`scripts/phase_d_asset_stats.py`,远端未部署)。**部署对齐动作**(2026-09-29,发车前、任何付费调用之前完成):(a) 远端 `src/pathway_v43/domain/policy.py` 与验收字节不一致(旧版默认 `reactant_similar_enabled=True`,验收版为 `False`)→ 以本地验收字节覆盖,同步后 SHA `89412eda…` 一致;(b) 远端 src 树含 75 个 macOS AppleDouble 垃圾文件(`._*`,macOS 打包产物,非代码,污染代码身份聚合)→ 全部删除,删除清单存远端 `runs/ec298_pd_retest_deploy_appledouble_removed.txt`;清理后远端代码身份 = `07fef84f…`(50 文件),与验收字节一致 |
| 资产双清单 | manifest `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c`,22 文件 / 166,849,006 字节;本地与 Chenyu 同值;运行资产为 v1;v2 映射资产不进运行时 |
| 策略/版本 | `STRATEGY_VERSION=v43-policy-5`、`APPLICABILITY_VERSION=v43-applicability-3`、`SIMILARITY_VERSION=v43-rsim-1`、`PREDICTION_POLICY_VERSION=v43-predpol-3` |
| Prompt 版本(SHA256) | rank_candidates `864a5f30…`、analogy_edit `6d228935…`、novel_proposal `1aa41393…`(`configs/prompts/`,随批次身份冻结) |
| 导出策略 | `products_per_parent_cap=5` 等(策略哈希 `a5bd77bba99328d8a3c64a3b0990dcf5d1af4a88b671de61744bb3d19f8571aa`),与首轮一致 |
| Scorer | 正式评分 `v43-ec298-scorer-2`(`src/pathway_v43/exam_v2.py`,SHA `b86a1f39…`);两臂同函数、同规则 |
| 完整身份快照 | `reports/phase_d/retest/local_identity_snapshot.json`(本地);远端环境 python 3.11.16 / rdkit 2026.03.6 / langgraph,与本地 conda env `depending43` 同版本系 |
| 逐文件树清单 | `reports/phase_d/retest/local_tree_manifest.txt`(本地 126 文件 SHA,与远端 124 文件全一致,见上) |

## 3. 模型、端点与当日价格快照

- 模型固定 DashScope 北京按量 `ZHIPU/GLM-5.3-Flash`(OpenAI 兼容入口);
  凭证只从 Chenyu 受限 env 文件
  `/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env`(仅
  `V43_LLM_BASE_URL/V43_LLM_API_KEY/V43_LLM_MODEL` 三键)注入;当日实核:
  env 模型 ID 与冻结要求一致、base URL 为 DashScope 域、key 存在
  (核验只输出布尔,不打印值)。密钥/完整 env 不进仓库、任务书、日志、报告。
- **当日价格快照(2026-09-29 刷新)**:input ¥0.8/M、output ¥2.8/M、
  cache read ¥0.23/M、RPM 200、TPM 3,000,000、区域 cn-beijing、按量计费;
  来源 help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu(WebFetch 官方
  文档逐字取数)。与 2026-09-25 旧快照同值(旧快照仅作历史记录)。
  快照文件:`reports/phase_d/retest/provider_price_snapshot_2026-09-29.json`。

## 4. 两臂运行配置与共同变更说明

配置文件(本仓,字节冻结):`reports/phase_d/retest/ec298_pd_retest_C0.json`
(SHA `78b4b168…`)、`ec298_pd_retest_D3.json`(SHA `20d83f74…`);
机器可读 diff:`config_diff.json`(SHA `005056e4…`)。

单步协议(与首轮 298 身份一致):`max_depth=1`、`max_expansions=1`、
`max_frontier_width=5`、`max_llm_calls=3/题`、`max_proposals=1/题`、
`max_http_retries=4`、`reasoning_effort=max`、每步最多五个已验证可报告
产物、40 worker、`max_in_flight=40`、RPM 180 / TPM 2.7M(对提供方
200/3M 的保守余量)。

**相对首轮 298 的共同变更(两臂同值,均在看到任何分数前冻结)**:

1. `llm_timeout_s` 900 → **3600**(2026-09-29 用户指令拆时间墙;首轮
   观察到思考链超过 900s 的调用被截断);
2. **不设费用上限**:`batch_cost_cap_cny=null`(首轮 40/臂;该键仅随身份
   记录,运行中无强制点)——2026-09-29 用户指令覆盖旧冻结;
3. **不设 issued 停止线**:`rate.max_calls=10,000,000`(首轮 900/臂;
   该值不可能在 298 题单步预算下触顶,语义即"无上限");
4. 资产清单由 21 文件(def94d82,首轮)变为 22 文件(ac9b97b8,Phase D
   加入 v2 类比语料但运行时不使用);引擎/类比 v1 运行资产不变。

除 `reactant_similar_enabled` 外,两臂其余 37 个扁平配置键逐一相同;
D-3 的 D1 固定参数(threshold 0.45 / top_k 16)在两臂配置中取值相同、
关闭臂惰性(见 §0)。

## 5. 运行顺序、停止与恢复规则

- **顺序**:先 C0 后 D-3,严格串行;不同时各开 40。每臂 40 个题目
  worker、全局 ≤40 个真实 API 请求同时在途(`max_in_flight=40` 持久闸门);
  `OMP_NUM_THREADS=1`;远端长任务 nohup 落盘保活,短连接查进度
  (progress.json / workers/*.status.json 计数)。
- **停止**:每题按冻结 qid 顺序补位至 298 个合法终态;`completed`、
  `awaiting_prediction`、按规则触顶的 `budget_exhausted`、`invalid_input`
  为合法停因(空答卷也是合法答卷);`failed`/导出失败/缺失/未终止不是。
- **恢复**:共享代码/配置不变的基础设施中断可按同一身份安全 resume
  (worker 按 task_id 幂等,已持久化响应不重复请求,悬空调用按孤儿与
  费用预留记账,旧不可变产物不覆盖)。若需改代码/配置才能继续:旧批次
  标 `incomplete` 封存,新版本用**新批次身份和新目录**重做两臂,不拼卷。
- **旧产物零改写**:`runs/ec298_v43r1/`(dependingv43_dev)、Phase A 封存件、
  Phase D r1 四臂(`runs/phase_d_*`)、r2 半途批次、`ec298_gold_readonly/`
  全部只读。
- 正式题卷前只做非 298 合成夹具的真实模型连通/计费烟测(见 §7),
  计独立烟测账;不得借 298 题看结果后调配置;不为凑并发数字让 recorded
  题调用模型、不发伪请求;并发实测峰值不足 40 时如实披露原因。

## 6. 费用记账规则(2026-09-29 用户指令:不设上限)

- 不设任何预算/费用上限、不设 issued 停止线;不得以费用或额度预估阻断
  发车、停止发新调用或中断运行;配额耗尽导致的调用失败按路线失败如实
  归档,不触发任何费用门。
- 诚实规则照旧:逐调用记 issued、响应/超时/传输失败/孤儿与 usage
  (worker 逐 attempt 落盘 `prediction_call/response/orphan`);缺 usage 的
  调用按保守预留登记(输入侧 = 已发出请求文本 //4 的 token 上界;输出侧
  无请求级上限记 `unprovable_no_request_output_cap`,不臆造);未知费用
  不得用已知 usage 小计填成总费用;运行结束后以服务商账单回填核对。
- 烟测调用单独立账,不计入任何臂的批次账本。

## 7. 烟测(正式题卷前,付费,独立账)

- 底物:`C\C=C\C=C(\O)C([O-])=O`(v3 基准 dev 路线 pb_0117 的 root_smiles,
  运行侧白名单字段;已核:其原串与 cn 身份均不在 298 题底物集合内)。
- 两个烟测 run,均在 Chenyu `runs/ec298_pd_retest_smoke/` 下,新 run_id:
  一个走 C0 语义(`reactant_similar_enabled=false` 覆盖)、一个走 D-3 语义
  (true 覆盖),各经真实 worker 路径(`run_worker` 计划注入 policy_overrides)
  发起真实付费调用;用途 = 连通/计费/修复回归(pb_0117 情形在 R1 修复后
  的真实重现)。费用与 usage 单独登记,不入两臂账本;烟测结果不用于调
  整任何臂配置(发现问题即停,按 §5 恢复规则处置)。

## 8. 主指标与逐题配对算法

- **评分**:正式 `v43-ec298-scorer-2`(零 LLM);两臂均从原始候选 SMILES
  现算 `cn_identity`(电荷归一化、立体盲);计分单位为**整条候选字符串**
  (多组分"任一组分命中"仅另表敏感性);主分母固定 **298**;空答、合法
  停待预测、预算终止均算未命中;不可解析候选占名次。两次评分传入
  **同一个**经 SHA 核实的引擎结果文件(引擎背景参照,见 §10)。
- **主结果**:hit@1/hit@3/hit@5;hit@10 对每步五位 agent 恒等于 @5,仅作
  宽度说明。另报题级配对赢/输/平、首个命中位次、空答数与合法停因分布。
- **配对算法**:按**显式 qid**(run_id 由批次身份短哈希与 qid 显式派生,
  不从目录名反推)联结两臂 298 行;每个 K(1/3/5)汇总
  `both / C0_only / D3_only / neither` 四格(**四格和必须为 298**);D-3
  题级赢/输/平(该题 @K 命中差 >0/<0/=0);命中数差与百分点差。逐题行
  列两臂 rank、@1/@3/@5 命中、首位产物及其来源(evidence_id/kind/
  report_rank/文件引用)、空答/停因、已验证候选数、调用/重试/孤儿、
  usage 与费用状态。
- **完整性门在评分之前**:两臂各自先过 `v43-pairing-gate-1`
  (`validate_arm`:冻结清单/身份自洽/逐路线 worker 终态/归并元数据/逐路线
  答卷 SHA/行唯一性)。任一臂不完整 → 配对结论只能标
  `diagnostic_incomplete`,失败题留在 298 分母,不做剔题命中率。
- 逐题差异分析分层:D1 新召回(similar_refs/budget_not_assessed)、实际
  供体评估(donor_evals)、资格/歧义(eligibility status/fallback)、
  类比/novel/recorded 路由(prediction_mode)、验证拒因(validation)、
  最终报告位次;附事件/卡/validation 文件引用。相似度增加、applicable
  增加或模型自述原因不能替代报告产物命中证据。

## 9. 异常路线处理规则

- 任何 `failed`/`export_failed`/`missing` 路线:该臂批次终态为
  `failed`/`incomplete`,阻断正式配对结论;分数只能标
  `diagnostic_incomplete`;失败题保留在 298 分母(空答卷行),不得以
  空行或部分行补成成功。
- 基础设施中断(SSH 掉线/进程被杀/机器重启):按同一身份安全 resume
  (§5);resume 前后逐路线核对已持久化产物 SHA 不变。
- 凭证失效/配额耗尽:如实归档(调用失败/闸门停止),不绕过、不换凭证
  源、不换模型;批次按实际终态封存并如实报告。
- 发现需改代码/配置才能继续:旧批次标 `incomplete` 封存,新身份新目录
  重做两臂(不拼卷);本轮出现该情形时报告状态为 `not_run`(未重做)或
  `diagnostic_incomplete`(部分完成),不得称 `complete`。

## 10. 引擎背景参照(不参与主配对)

首轮封存引擎臂的资产清单(21 文件 def94d82)与本轮部署(22 文件
ac9b97b8)不一致,按任务书 §5.3 **不直接复用**;本轮另跑零 API 引擎臂
(同一 `exam_inputs.jsonl`、当前冻结代码/资产,`runs/ec298_pd_retest_engine/`,
清楚标注版本),两臂评分传入**同一个**该引擎结果文件(SHA 核实)。
引擎臂零模型费用、零金标(只输出候选,不判分);它是背景参照,
**不参与 C0/D-3 主配对**;封存 `pool_identities` 只覆盖导出 Top-10,
不得称为完整候选池。

## 11. 发车前验证记录(2026-09-29)

- **本地全仓无凭证回归**:`OMP_NUM_THREADS=1 PYTHONPATH=src python -m
  pytest tests/ -q`(conda env depending43,python 3.11.16/rdkit
  2026.03.6)→ **456 passed / 0 failed,474.57s**;日志
  `reports/phase_d/retest/local_pytest.log`。覆盖 worker 子进程/崩溃注入/
  resume/批次终态/归并/配对门禁端到端(`tests/test_r1_end_to_end.py`)。
- **本地资产双清单**:verify_repo_manifest 通过(§2)。
- **本地无金标端到端夹具**:`pathway_v43 run --model off`(合成底物
  pb_0117 root_smiles,非 298 题)+ export → run completed、导出 verify ok、
  答卷 SHA `8e6ba1b860ca88aeb92823762df0965278d3512b9f27672deba087b85fefd3a6`;
  全程零凭证零 LLM 零金标。
- **Chenyu 同版独立回归/资产/夹具**:见勘误记录(完成后追加;
  预检已确认远端代码身份 = `07fef84f…`、资产清单 = `ac9b97b8…`)。

## 12. 勘误记录(只许追加)

### 勘误 #1(2026-09-29 01:26 +0800 之前;两臂身份落盘、首次付费调用之前)

1. **两臂 batch identity(Chenyu `dependingv43` 实机创建,driver `--phase
   identity`,零 API 调用)**:
   - C0:`batch_sha256 =
     31549aab3db5fd2ef832996d5622d80ec8e17984e5b32e19a966455ac3b42df8`
     (short `31549aab`);批次根 `runs/ec298_pd_retest_C0/`;
   - D-3:`batch_sha256 =
     cfe1534a93d7fe1596f997272cb2e3260001f0861ecd4d66f286c6e99b2495b4`
     (short `cfe1534a`);批次根 `runs/ec298_pd_retest_D3/`;
   - 两臂 `exam_inputs.jsonl` 副本 SHA 均为 `cb5996c9…`(driver 内嵌
     锚值 fail-closed 校验);身份文件分别位于各批次根
     `batch_identity.json`。
   - **跨机一致性**:两臂身份 SHA 与本地(conda env depending43)对同一
     配置/清单/代码/资产 dry-run 计算值**逐一相同**(31549aab /
     cfe1534a),证明本地与远端代码/资产/配置逐字节一致。
2. **Chenyu 同版独立回归完成**(补 §11 远端项):`OMP_NUM_THREADS=1
   PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`(python 3.11.16 /
   rdkit 2026.03.6)→ **456 passed / 0 failed,655.36s**;日志远端
   `/tmp/pd_retest_remote_pytest.log`(结论回传后留档于
   `reports/phase_d/retest/remote_pytest.log`)。
3. **远端无金标端到端夹具**:与本地同一合成底物(pb_0117 root_smiles,
   非 298 题)经 python 精确传串 `run --model off` + export → run
   completed、导出 verify ok、答卷 SHA
   `8e6ba1b860ca88aeb92823762df0965278d3512b9f27672deba087b85fefd3a6`,
   **与本地夹具逐字节一致**。(过程披露:第一次远端尝试因 shell 引号
   转义把底物串变成双反斜杠,产物 SHA 不同;发现后以 python 精确传串
   重跑,重跑结果与本地一致;错跑目录已删除,不影响任何共享产物。)

### 勘误 #2(2026-09-29 01:47 +0800 前后;发车烟测完成、臂运行开始之前)

1. **引擎背景臂(零 API)已完成**:`runs/ec298_pd_retest_engine/`,
   298/298 状态 ok、0 空答/失败,40 分片进程,`engine_results.jsonl`
   SHA256 `0e16268c375585f622f826a3649ef272f70154d22b2bae02c6e99b90537992cf`,
   白名单 SHA `cb5996c9…`;当前冻结代码/资产(§10 的"另跑零 API
   引擎臂"路线)。
2. **发车烟测(非 298 合成夹具,独立烟测账)**:
   - r1(pb_0117 底物,两臂语义各一 run):管线与 D1 修复路径验证——
     d3-like run 资格块 `applicable`、`selected=reactant_similar_channel`
     (record `rhea:32536`,donor_ref 路径无 TypeError),decision 写读
     稳定,run completed、导出 verify ok;两 run 均 0 模型调用(该底物
     在语料中有唯一可用 recorded 反应,确定性直通——因此 r1 不构成
     连通/计费烟测,如实记录)。
   - r2(pb_0002 底物 `C#CC(C)(C)NC(=O)C1=CC(=CC(=C1)Cl)Cl`,非 298,
     两臂语义各一 run):**真实付费模型调用 2 次,2 响应全部 ok
     (0 失败/0 孤儿/0 429),usage 2/2 齐全**(输入 4,451 tok、输出
     25,922 tok,其中思考 24,160);已知 usage 部分费用估算
     **¥0.0761**(2026-09-29 快照价,思考按输出计费);两 run 均
     completed + 导出 verify ok。连通与计费路径验证通过。
   - 烟测产物与账本:远端 `runs/ec298_pd_retest_smoke/`
     (`_smoke_summary.json`、`_smoke_summary_r2.json`、各 run 状态与
     产物);烟测费用不进任何臂批次账本。
   - 过程披露:烟测根内发现一个**非本会话创建**的
     `smoke_exam_inputs.jsonl`(内容为 SMOKE_pb_0002/SMOKE_pb_0117
     两行白名单,创建时间在本会话烟测之前);本会话未读取、未修改、
     未删除该文件,本会话烟测产物与其无交集。
3. 首次付费 API 调用时间:2026-09-28T17:35:12Z(烟测 r2 c0-like
   a1);本登记(含勘误 #1 的两臂身份 SHA,登记 SHA
   `603467accb06a34fab52a71881d04cb18e6a6653acff0d71764ccb1375324c44`)
   落盘时间早于该时刻。


### 勘误 #3(2026-09-29 运行后;R2 外部 review 的派生表修复,零 LLM 零付费调用)

R2 review 指出两张**运行后派生分析表**的 schema 读取缺陷(P1×2)与
仓内并发证据不足(P2)。修复事实登记如下:

1. **修复对象仅为运行后派生表与脚本,封存运行产物零改写**(全部
   只读重导;两臂 batch identity、merged 答卷、逐 run 原始产物、
   seal 清单均未触碰,远端旧 run 目录 mtime 早于本轮)。
2. **[P1] 首位产物来源**:r1 配对脚本读 merged 答卷不存在的
   `steps[].source` 字段,286/285 非空答卷来源列全空。修复后从
   `results/T_*/report_adjudication.json` 的
   `products[reportable=true]`(report_rank 排序)重建,与 merged
   `predicted_products[0]` 交叉核对:填充 286/286 与 285/285,
   **首位产物不匹配 0 题**。
3. **[P1] deepdiff 报告层**:r1 读不存在的 `report/entries` 键且
   `n_report_products` 计入全部裁决候选(max 505)。修复后按
   `products[reportable=true]` 口径:两臂 max 恰为 5、0 题越界;
   schema 升 `ec298-pd-retest-deepdiff-2`。
4. **[P2] 并发复核**:新增 `scripts/ec298_pd_retest_inflight.py`,
   从封存响应产物只读重导逐请求派生表(各 187 行,零凭证:
   request_id/sent_at_epoch/done_at_epoch 等),以与批次协调器同一
   函数(`pathway_v43.exam.inflight_evidence`)同口径重算峰值:
   **C0 33、D-3 32,与封存记录值一致**;driver 后处理同步改为落盘
   `_inflight_requests.json`。
5. **不变性**:重生成前后 score_v2 两臂 summary、hits、四格、
   赢/输/平、298×2 逐题 agent_rank 全部相同(旧表存档
   `scoring_r1_superseded/`);deepdiff 决策层指标(265/11/25/9)
   相同。主分数与配对结论不受影响。
6. 重生成命令与时间:2026-09-29 02:0xZ 前后于 Chenyu
   (pairing/deepdiff/inflight 三脚本,命令同报告 §11 复现节)。
   本勘误本身不含金标、密钥或答案内容。
