# 回复：chain12 → 三模型批回退归因材料清单（2026-10-15）

> 回复对象：teacher huang（材料索取清单 2026-10-14）。
> 题域标签：**298=RHEA 通用酶学/已见题**——本文所有数字均属该题域，与 dev
> 双向不外推。判分零 LLM；探针≠预注册≠成绩；金标内容零出正文。
> 提交方式按清单要求：仓内文档给路径，大件给远端路径 + SHA256（前 16 位）。

## 一、总览：核心归因已完成（零成本离线，2026-10-15）

清单所求的核心分析——「−9 的逐题分解：判据效应 / 修复回退 / 采样噪声
各占多少题」——**已经做完**，报告在仓：

- 技术版 `docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md`（sha256
  `f0a4eeb3d3f35e8e`）+ 大白话版 `…_PLAIN_…`（`6fcc4147b495da15`）；
- 三模型对照表 `docs/CHAIN13_MODEL_CMP_TABLE_2026-10-15.md`（`9b2d7b3a2d8431dd`）；
- 全部数据产物与逐题 qid 清单见 §三映射表（gitignored 报告区，可整体拷送）。

**结论先行（v1 口径 92→83，逐题闭合 71+13+8=92、71+12=83）**：

| 分解 | 题数 | 机制归因 |
|---|---:|---|
| kept（两批都命中 rank1） | 71 | — |
| 掉出 strict（覆盖损失） | 13 | 其中仅 5 题与 C 线供给面相关（见下），其余在 C 线未触碰题 |
| 仍 strict 但 rank>1（排名损失） | 8 | 同上 |
| new（本批新命中） | 12 | 含 C 线供给带来的净赚 2 题（uncovered→strict） |

**机制归因三句话**（证据链见报告 §三/§四）：

1. **C 线+v2 合并自效应净零**：C 门开的 35 题 strict 24→19(v1)→24(v2)；
   生成侧唯一行为变化（C 线 commit 873c323）名下账已查清。
2. **主损失在 C 线未触碰、输入字节零变化的 263 题（strict −11）**：
   18 个损失题候选池供给两批**完全相等**而模型扩展面 18/18 全变；
   另有 10 题 run 级 `real_model_transport_failure`（模型调用传输失败、
   零事件）；逐题翻转 47/298 vs 同协议族参照批 34/298。判「采样/服务端
   非确定性」（面上证据，不逐题定责——无重复批可对拍）。
3. **豁免档兑现 5/13**：v2 实测豁免 5 事件（全 H₂O，hit@1 +4：83→87）；
   模拟 N1''=13 兑现 0/13 的根因=供给门资格面未罩住（后续离线重放测到头：
   精确谓词下扩罩面为**空集**，编译主死因=元素适配 704/1192——见
   `docs/LOCK12_REPLAY_VERDICT_2026-10-15.md`）。

三模型排序口径：同协议同卷下 **GLM > deepseek-v4.1-flash > qwen3.8-flash**
（GLM v2 hit@1=87 / 83；tokens：ds 最省 4.84M vs GLM 6.30M）；本批为
多变量叠加批（C 供给+声明链+v2+3 调用预算），模型间排序对该协议稳健，
**绝对数不与旧协议批直比**。

## 二、P0 材料逐项映射

| 清单项 | 状态 | 位置与哈希 |
|---|---|---|
| 1.1 三模型批身份 | ✅ | 部署=**v43@461844e**（乌镇 wuzh02 树 `~/EnzymeAgent/v43c13`）；run 级 `code_identity.aggregate_sha256` = `37decacf1b8a94c3028f424bb45d67a2b1a163dce332b9c8b762881fcbbf9542`（**298 run 去重=1**）；模型 ID：GLM-5.3-Flash / qwen3.8-flash / deepseek-v4.1-flash（三臂 env 文件）；冻结配置 `orchestration.json`（rpm 200 / tpm 3M / max_calls 4470 / workers 8 / 每题 ≤3 调用）；判据版本常量 `ppv1-criteria-v2`。**诚实缺口**：调用未显式记录采样参数（provider_env 仅布尔位、request_params_set=false；源码亦不设温度）——已列为下轮卫生件 |
| 1.2 chain12 身份 | ⚠️ 部分 | synced `batch_manifest.json` 在（batch_tag `s5b-298-v4b`；题源 sha256 `9f5955…` 与三模型批**逐字一致**）；**chain12 无 run_identity / calls 快照**（历史批结构限制，归因报告 §六如实登记） |
| 1.3 代码 diff 范围 | ✅（含修正） | **hwall(5006493) / F3 词表(dbc71ca) / D2-R3(59db0da) 均在 chain12 基线内，不在 diff 里**（chain12=10-12 批，含 T1a 池诊断 0e46333）。chain12→chain13 的 src 行为面差异=①C 线 `873c323`（**生成侧唯一**）②判分侧 v2 族 `84a9eb4`/`7e7855c`/`dda852b`（自证零生成改动）③no-cap 运营壳 `461844e`（发车门/预算标记，不改生成语义） |
| 1.4 部署对拍 | ✅（口径修正） | 本批走乌镇 wuzh02（**非 Chenyu 通道**）；部署一致性以 run_identity 聚合哈希（298/298 去重=1）+ 本地 HEAD 461844e 对拍为据；Chenyu policy.py 前科不适用本批 |
| 2.1 三模型批逐题表 | ✅ | `metrics.json(.v1)` per_qid：qid × match_status / rank / run_id / run_status / stop_reason（本地 synced + 远端批根）；本地 v2=`f2e5003c4bc2de08`、v1=`49eec91756de2f7e` |
| 2.2 chain12 逐题表 | ✅ | 同结构；本地 `f435ad7aaf2905d2` |
| 2.3 逐题配对 diff 表 | ✅ | `attr_chain13_c.json`（`738e8d0c72d0304c`）C1 块：迁移矩阵（S→P 10 / S→U 13 / …×C 暴露分列）+ rank 迁移表 + hit@1 分解（v1/v2 双套）+ 全部 qid 清单 |
| 3.1 双口径判分输出 | ✅ | 三臂各两套（metrics.json=v2 headline / metrics.json.v1=敏感性；GLM 哈希见 2.1） |
| 3.2 豁免逐题落点 | ✅（口径说明） | 实测豁免 5 题=由 v1/v2 状态差分精确重建（qid 清单在 attr JSON）；聚合披露在 metrics `criteria_v2` 块（5 事件全 H2O/tier 计数）；**逐边参与物明细未按题落盘**（判分器披露粒度限制，如实登记；5 题清单+参与物 SMILES 可从 attr JSON C2 焦点块复核）。N1''=13 模拟面 qid 清单在 chain12 分析目录（`criteria_v2_rescore_data.json`） |
| 3.3 判据版本与冻结 | ✅ | 常量 `ppv1-criteria-v2`；预注册 `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`；生效登记 commit `5ade032` |

## 三、P1 材料逐项映射

| 清单项 | 状态 | 位置与哈希 |
|---|---|---|
| 4.1 失分结构对比 | ✅ | v1 口径 partial 52 vs chain12 43（+9）：迁移矩阵给构成（S→P 10 等）；后位损失=rank 迁移表（1→2 共 7 题等）；桶级 A–I 在 funnel |
| 4.2 执行期拒因普查 | ✅（超出清单粒度） | `funnel_chain13_glm.json`（`f14feed652330f72`：扩展 outcome 分布）；**新增**编译侧拒因普查 `l1_replay_data.json`（`cf93cb3444f425b9`：template_elements_no_fit 704 / no_alignment 168 / charge 133 / stereo 42…，族×拒因交叉表）——比 S5b 期漏斗更细一层 |
| 4.3 池层数据 | ✅ | funnel `supply_view`（specs/compiled/池深/去重分布）+ manifest `pool_diagnostics`（逐候选谱系 5540 行：通道×结局×拒因）；C 门新增 35 题 45 行（交付书字节探针：262 题全等+35 纯新增+1 补位） |
| 5.1 调用账本 | ✅ | 三臂 `s5b_real_calls.jsonl`（296/298 文件，缺 2=零调用即终止的 run）；GLM 臂 596 行：issued 298 / responded 288 / failed 10；逐请求 tokens/elapsed/finish 状态 |
| 5.2 终态与空答 | ✅ | 298/298 零失败；run_error 普查 286 干净 / 10 传输失败 / 2 拷贝组分拒（结构化） |
| 5.3 并行闸门证据 | ✅ | 三臂 gate.json（批根，远端只读）：**429=0 / forbidden=0 / peak_in_flight=8**（=max）；三臂独立批根独立配额池，互不挤兑 |
| 5.4 usage 分布 | ✅ | GLM 6.30M / ds 4.84M / qwen 6.49M tokens；逐请求输入/输出 tokens 在 calls 账本（thinking 字段无——同 1.1 缺口） |

## 四、P2 与承诺部分

| 清单项 | 状态 | 说明 |
|---|---|---|
| 6.1 预注册/发车登记 | ✅ | `docs/CHAIN13_S5B_298_PREREG_2026-10-14.md` + 三模型增补 `…_MODEL_CMP_PREREG_…` + 批根 `preregistration_approval.json`（配置冻结） |
| 6.2 修复触点离线重放 | ✅ | C 线交付书字节不变探针（262 全等/35 纯新增/1 补位，`docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`）；10-15 追加零模型重放探针（Harness 逐题复现救援结果零偏差后测编译容量） |
| 6.3 warning 级异常汇总 | ✅ | run_error 普查（见 5.2）即异常面主体；无 warning 级未登记项 |

**关于贵方「材料到齐后我们产出归因报告」的承诺**：归因报告我方已产出
（§一两版+数据全链），贵方可直接消费/复核/质疑——逐题 qid 清单全部在
attr JSON，可独立重算。若贵方复核后仍需补充导出（如逐边豁免明细重建、
gate 明细整理），列出件名即可，全部零成本只读。

## 五、大文件远端路径（只读封存，SHA256 可按需补算）

| 件 | 远端路径（wuzh02） |
|---|---|
| 三臂批根（判分产物/gate/approve/budget 标记齐） | `~/ppv1_hpc/batch/chain13{,q,d}_s5b_20261014` |
| 三臂 runs 根（全量 186M×3 量级） | `~/ppv1_hpc/runs/chain13{,q,d}_s5b_20261014` |
| 部署代码树 / 仓外引擎 | `~/EnzymeAgent/v43c13` / `~/EnzymeAgent/dependingv3` |
| 三臂 env / venv | `~/ppv1_hpc/env/llm{,_qwen,_ds}.env` / `~/ppv1_hpc/venv_v44run` |

本地镜像：`reports/ppv1_s5b/chain13_{glm,qwen,ds}/`（判分汇总）+
`chain13_glm/synced/`（298 cases+payloads+identity+calls 子集，53M）。
