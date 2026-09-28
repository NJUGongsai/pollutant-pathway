# EC298 Phase D 报告:供体检索、映射资产与预算验证

> 结论状态(任务书 §6 预注册):****no_release**(保留 C0:旧检索 + v1 + 预算 3;v2 亦未过发布门)**
> 选中配置:C0(v1 资产 + 旧检索 + 预算 3)—— Phase B/C 现状原样保留;未选臂与原因见 §6;限制见 §8。
>
> 实施会话:ZCode(GLM-5.3);任务书 `docs/TASK_V43_EC298_PHASE_D.md`
> (2026-09-28 发车,"/goal 完成这份任务书")。外部 review 未做 —— 本报告
> 交付后由用户按既有节奏发起。

## 0. 摘要

Phase D 在**不放宽 Phase C 确定性门禁**的前提下交付了三个杠杆并完成
冻结 dev 20 的对照验证:

1. **D1 供体反应物相似度检索**(`reactant_similar` 通道,`v43-rsim-1`):
   检索键从"产物身份"扩展到"底物-反应物结构相似"(Morgan r2 b2048
   Tanimoto ≥ 0.45,top-K 16);相似度只决定召回次序,资格仍走全部门禁。
2. **D2 映射资产 v2**(`v43-analogmap-1` 确定性 MCS 映射器):17183 行中
   2828 行 v1 变换不可判定,重映射成功 **767 行**(其余 2059 行为无结构
   变化模板/2 行 MCS 超时,如实 rejected 保留 v1 语义);机器门禁全过,
   分层抽样 100 条经实施模型复核 0 错(复核中发现并修复 1162 条
   L==R 伪映射缺陷);**独立人工复核未执行 → v2 不进运行时默认**。
3. **D3 配对实验**:零 API 四配置消融(applicable 11→14/19/22)+
   真实模型 dev 20 四臂(C0 / D-3 / D-5 / D-10,Chenyu,顺序执行)。
   **真实四臂(20/20 全完成,合计 ¥2.75,0 限流,0 孤儿调用):
   cn@1 = 0.208(C0)/ 0.193(D-3)/ 0.169(D-5)/ 0.126(D-10);配对 vs C0:
   D-3 净赢 **-2 题**(0 win / 2 lose,pb_0459 与 pb_0471)且 @5 下降
   (步 -6);预算 5/10 单调更差(D-10 spurious 升至 0.078)。
   **预注册规则判定:D-3 不满足"@1 净赢 ≥2 且 @5 不降",不满足
   "@1 净赢 0 且 @5 净赢 ≥2 的候选标记",其余情况保留 C0 —— 全部
   D 臂不采用,v2 不发布。**离线消融的 applicable 增加(+3/+8/+11)
   未转化为命中:相似供体让更多父节点走类比编辑,其中一部分编辑
   失败或产物偏离,挤占了原本 novel/recorded 可用的路径 —— 这正是
   任务书要求"最终看报告产物命中,不能仅以 applicable 数增加宣布
   成功"的实证。**

红线全程遵守:金标只在运行结束后的独立评分进程读取;参数卡只用资产
无标签分布(dev 20 输入未参与定标);已见 298/Phase A 归因未用于任何
参数选择;v1 与封存产物零改动;原始 rule/analog 卡无报告位;跨版本
resume 被身份检查拒绝(端到端反例钉住)。

## 1. 基线与协议(D0)

- 起点 commit `5c8f284`(branch v4.3),工作树含 Phase B/C 未提交改动
  (全部保留,未清理未重置);并发会话无活跃写盘(开工前核对)。
- 全仓无凭证回归:**388 passed**(466s,depending43 env,2026-09-28)。
- 关键 SHA(开工时):`dev_batch.json 7fe556cd…`、`policy.py b63a8da2…`(旧)、
  `corpus_templates_v1.jsonl 8f3f2c1a…`、`assets/MANIFEST.sha256 def94d82…`(21 条)、
  Phase C 报告 `02feca36…`;金标(封存 questions.jsonl)SHA 单独登记,
  运行进程零接触。
- 基线定义 = **Phase B+C 可复核代码 + v1 资产 + 预算 3**(非 EC298 首跑)。
- dev 20 输入:`reports/export_dev/input_manifest.json`(20 路 root_smiles,
  `gold_fields_excluded=true`),四臂共用同一冻结清单(Chenyu 重建后逐字节
  一致);金标路径只传给终评 scorer。

## 2. D1:按反应物相似度找回供体

### 2.1 实现与语义

- `services/analog_source.py`:`templates_similar_to(substrate, *,
  threshold, top_k)` + 反应物指纹索引(键含资产 SHA 与算法版本
  `v43-rsim-1`,跨版本缓存不串用);无效 SMILES 如实返回空/跳行。
- 三通道合并:`product_producing`(既有)/ `reactant_similar`(新)/
  `corpus_trace`(溯源)。同一 `(asset_sha256, line_no, record_id)` 只评估
  一次,`find_channels` 多通道标签双向完整(含相似度分数/版本/召回位次,
  沿 `assess_donor` 结果透传,答卷→资格块→供体→通道可回查)。
- 评估序(冻结进策略身份):**resolved 卡优先 → reactant_similar 通道
  (相似度降序)→ 其余卡 (rank, evidence_id)**。新通道不得挤掉 resolved;
  被挤掉的供体逐条记 `displaced_by_similar_channel`。
- 预算语义:检索 top-K(16)与每父评估数 `max_analogy_donor_candidates`
  (3/5/10 按臂)分别计数;预算外供体标 `budget_not_assessed`,不冒充
  `inapplicable`。
- 版本:`STRATEGY_VERSION v43-policy-4`(单一事实源移回 models.py,修复
  policy.py 死定义)、`PREDICTION_POLICY_VERSION v43-predpol-3`、
  `APPLICABILITY_VERSION v43-applicability-2` —— 三者进 run identity,
  变更拒绝旧 run resume。
- 接线一致性:CLI run / resume `_finder_for` / batch worker 三路恒注入
  `AnalogSourceResolver`(修复 resume 路径缺 resolver 的潜在分叉);
  batch 身份冻结 `prediction_policy`(预算臂身份自动区分)。

### 2.2 参数卡(评分前提交,无 dev/298 接触)

`docs/PHASE_D_D1_PARAM_CARD.md`:指纹 Morgan r2 b2048 立体盲、Tanimoto、
阈值 **0.45**(边界 ≥)、top-K **16**。依据 = 资产无标签分布
(`reports/phase_d/asset_similarity_stats.json`,seed 20260928):17183 行
反应物全可解析、13003 唯一、2504 组同 SMILES 多记录(去重键证据);阈值
0.45 时中位召回 10 / p90 102 / 零召回率 6%,与 top-K 16、预算档 3/5/10
匹配(0.40 召回过多、0.50+ 零召回抬升)。性能:索引 1.24s、单查 3.1ms。

### 2.3 测试与审计

`tests/test_reactant_similar.py` **19 例**全绿:旧通道漏召回/新通道找回、
阈值含边界、同 SMILES 52 记录不误合并、双通道去重单评估、resolved 不被
饥饿、高相似仍被化学门禁拒、竞争弃权、budget_not_assessed、displaced
留痕、C0 无 similar_refs 行为与 Phase C 一致、兄弟路径不串线、索引键
SHA+版本、真实资产 ref SHA/行号回查、workflow 节点级接线、同配置重放
字节一致 + resume 不改判资格块。

## 3. D2:映射资产 v2 与来源审核

### 3.1 管线与漏斗

`scripts/build_analog_v2.py`(零网络零金标,只读 v1):重映射条件 = 纯结构
条件(v1 `extract_donor_transform` 不可判定;实测 2828 行全部为
`transform_no_change` —— 映射号两侧一致、真实反应在未映射区)。映射工具
`v43-analogmap-1`:RDKit 2026.03 `MCSParameters`(AtomCompare=Elements/
BondCompare=Order/Timeout=10s),公共骨架按确定性字典序最小匹配编号、
两侧独有原子续编;center_atoms = 变化键端点 ∪ 增删/氢/电荷变化映射号。
配置与 "weights: none" 随 provenance 记录。

| 漏斗 | 数量 |
|---|---:|
| v1 总行 | 17183 |
| unchanged(v1 可判定,字节原样) | 14355 |
| 重映射候选 | 2828 |
| **remapped(过全部机器门禁)** | **767** |
| rejected:no_structural_change | 2059 |
| rejected:mcs_timeout | 2 |

v2 = 完整替代版 17183 行,行级一一对应;96 个重复 record_id 是 v1 事实
(template_id 行级唯一),登记于 summary,不删行("未通过重映射的行保留
v1 语义,不删除"红线优先)。v2 SHA `fabe4e24…3d6db`。

### 3.2 机器门禁与复核

机器门禁(§3.3 八项,767/767 全过):双侧可解析、映射号各侧唯一、保留
原子元素一致、**去映射两侧与原记录一致**(映射不改化学)、变化非空、
center 与变化一致、提取器可判定、`assess_donor` 不抛异常。

分层抽样(seed 20260928)100/767,覆盖原子增删 100、芳香变化 33、立体
26、氢变化 6。**复核发现系统性缺陷并已修复**:初版 1929 条 remapped 中
1162 条为 L==R 伪映射(电子转移/离子对/转运类模板,MCS 单连通分量限制
把其余组分伪造成 add/rem)—— 加 `no_structural_change` 门禁后重跑,
该类全部正确落入 rejected(897 旧 no_change + 1162 伪映射 = 2059 守恒)。
复核结论 100/100 ok,保守性注记两类(化学计量模板、剧烈重排大块
add/rem —— 评估趋向拒绝,fail-closed 方向)。

**诚实声明**:复核者 = 实施模型 GLM-5.3(非独立人工;记录见
`reports/phase_d/v2_review_verdicts.json`)。按任务书 §3.3"无人做化学
复核则未过发布门槛"的严格读法,**v2 不满足运行时发布门**:
- v2 已入双清单(`assets/MANIFEST.sha256|json`,22 条,装载校验+物理边界
  全过)并支持显式装载(`V43_ANALOG_CORPUS=v2`,缺失/不在清单 fail-closed
  不回退 v1;所选 SHA 进卡/资格块/run identity,跨语料 resume 被拒,
  `tests/test_analog_v2_corpus.py` 5 例);
- v2 仅用于零 API 消融诊断(D3.1);**真实模型臂不使用 v2**(§4.2 fallback:
  以 D1+v1 替代三条 D 臂,全部文件与表头明示);
- 独立人工复核(或外部 review 会话复核)通过前,v2 不得成为任何默认。

### 3.3 v1→v2 逐条差异

`reports/phase_d/v2_remap_provenance.jsonl`(17183 行:原/新行号与行 SHA、
record_id、原/新映射与 center、状态、拒因、工具/配置/权重、RDKit 版本)
+ `v2_remap_summary.json` 漏斗 + `v2_review_sample.jsonl` 复核工作表。
"实际从 unavailable 变可判定"的量以 dev 实测为准(§5 消融),不以恢复
行数冒充成绩。

## 4. D3.1:零 API 四配置消融

输入 = 冻结 dev 20(只 root_smiles,不读金标);审计对象 = 每条路线从根
出发沿**唯一 recorded 确定性直通**可达的全部父节点(零 API 的诚实边界:
类比/novel 无模型即停,完整树由真实臂产生)。四配置 × 52 父节点
(`reports/phase_d/ablation/`):

| 臂 | 语料 | 相似通道 | applicable | ambiguous | inapplicable | 相似召回 | 被挤掉 |
|---|---|---|---:|---:|---:|---:|---:|
| C0 | v1 | off | 11 | 17 | 24 | 0 | 0 |
| D1-only | v1 | 0.45/16 | 14 | 16 | 22 | 493 | 42 |
| D2-only | v2 | off | 19 | 19 | 14 | 0 | 0 |
| D1+D2 | v2 | 0.45/16 | 22 | 18 | 12 | 493 | 37 |

机制读数(不是命中率):D1 +3 applicable / D2 +8 / 联合 +11;ambiguous
同步上升(更多供体进入竞争裁决,弃权语义不变);`budget_not_assessed`
2233→2537(相似召回涌入预算竞争,如实记账)。

## 5. D3.2:真实模型 dev 20 四臂

**配置**:同一冻结 dev 20、`ZHIPU/GLM-5.3-Flash`、prompt/请求参数
(reasoning_effort=max,timeout 300s,重试 4)与 `configs/dev_batch.json`
口径;四臂 = C0(v1+旧检索+预算3)/ D-3 / D-5 / D-10(**D1+v1**,预算
3/5/10 —— v2 未过人工门,按任务书 §4.2 fallback,表头全部明示
"D1+v1",不写 D1+D2)。每臂 20 worker 上限、顺序执行(无 80 并发);
凭证只在 Chenyu env;价格快照刷新存档(输入 0.8 / 输出 2.7-2.8 元/百万
token,2026-09-28 复核与冻结一致);计费烟测 4.12s/58in/131out 计入账。

| 臂 | 配置 | cn@1 | cn@3 | cn@5 | route_recall | leaf | spurious | 调用 | 费用 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 | v1+旧检索+预算3 | 0.2077 | 0.2609 | 0.2802 | 0.4504 | 0.3596 | 0.0446 | 28 | ¥0.52 |
| D-3 | **D1+v1**+预算3 | 0.1932 | 0.2367 | 0.2512 | 0.4052 | 0.3013 | 0.0473 | 45 | ¥0.83 |
| D-5 | **D1+v1**+预算5 | 0.1691 | 0.2126 | 0.2271 | 0.3752 | 0.3013 | 0.0423 | 35 | ¥0.64 |
| D-10 | **D1+v1**+预算10 | 0.1256 | 0.1643 | 0.1739 | 0.3420 | 0.3283 | 0.0776 | 43 | ¥0.76 |

(20/20 全臂完成;D 臂 = D1+v1,v2 未过人工门未参与;逐题配对表见
`reports/phase_d/scoring/paired_scoring.json`。)

- 逐题配对:D-3 相对 C0 **0 题 win / 2 题 lose**(pb_0459:@1 5→3;
  pb_0471:@1 1→0);其余 18 题完全一致 —— 相似通道只在少数父节点
  改变了路由走向,且全部是负向。D-5 在此之上再掉 pb_0324(6→2)与
  pb_0065(3→2);D-10 掉 pb_0316/pb_0324(6→0)且 spurious 翻倍。
- 调用账:C0 28 → D-3 45(相似通道增加类比路径 → 更多模型调用与
  展开);费用合计 ¥2.7514(上限 ¥120,四臂各自 30 元硬门未触及)。
- 烟测 4.12s(58in/131out)计入 C0 臂账。

## 6. 预注册规则判定(§4.3)

硬门清单:§2/§3 QA(19+5 例全绿)、全仓回归(§7)、恢复/身份(重放
一致+resume 拒改)、资产清单(22 条双向一致)、费用账(四臂合计
¥2.7514 元 ≤ 120 元上限)、四臂 20/20 完成且评分口径一致 ——
**全部通过**(四臂 20/20、口径一致、QA/回归/恢复/清单/费用全绿)。

以 cn@1 为主、cn@5 为保护指标:
- D-3 vs C0:@1 配对净赢 -2(<2),@5 下降 → **不采用**;
- "@1 净赢 0 且 @5 净赢 ≥2 的 @5 改善候选"分支:不适用(@1 为负);
- 预算升级链(D-5/D-10 对已选最低臂继续满足净赢 ≥2 且 @5 不降):
  D-5/D-10 相对 C0 均为净负 → **不升级**;
- **最终裁定:`no_release` —— C0 保持运行默认(旧检索 + v1 + 预算 3),
  reactant_similar 通道不启用(v43-predpol-3 默认值改为关闭,见 §7),
  v2 资产不发布;D1/D2 全部交付物保留为可复核的诊断与候选资产。**
- 已见 EC298 的 budget10 诊断未被用于覆盖本规则(本实验即真实对照)。

## 7. 全仓回归与恢复

- 终回归:**412 passed**(无凭证;D0 基线 388 → Phase D
  净增 24 例,另有 4 处版本/清单计数断言随身份升级同步)。
- 硬杀恢复:Phase B/C 四个注入点回归全绿;D1 新增"同配置两次运行资格块
  字节一致 + resume 不改判已落盘资格块"端到端钉子。
- 身份:策略/预测策略/适用性三版本、语料版本+SHA、相似参数全部进 run
  identity;跨版本 resume 端到端拒绝(测试钉住);批次身份含
  prediction_policy(预算臂不混)。
- **no_release 落地**:`reactant_similar_enabled` 默认值已改为 `false`
  (保留 C0 语义;显式开启需新对照);四臂配置文件与产物原样保留。

## 8. 限定与已知边界

1. **D2 发布门**:v2 机器门禁全过 + 实施模型复核 0 错,但独立人工复核
   未执行 → v2 保守地排除在运行时与真实臂之外;复核工作表已备
   (`v2_review_sample.jsonl`),外部 review 或用户复核通过后可重跑
   D1+D2 真实对照。
2. 零 API 消融只覆盖"recorded 直通可达父节点"(52/臂),不代表模型完整
   展开树;applicable 增加不等于命中(§5 才是裁决)。
3. dev 20 是小样本:±1 题波动不作结论;预注册门槛是工程门槛,不证明
   统计显著性或机理。
4. 相似度检索立体盲(对映异构体相似度 1);立体区分由下游门禁与
   canonical SMILES 承担。
5. MCS 映射对多组分化学计量模板(2A→A 类)与剧烈重排产生大块 add/rem,
   评估趋向拒绝(fail-closed);已在复核注记,不构成错误化学路径。
6. 陈述一致性:897+1162=2059 的 rejected 守恒;96 重复 record_id 不删行;
   相似通道挤掉的原供体逐条可查(displaced 留痕)。

## 9. 复现命令与产物 SHA

```bash
# 全仓回归(无凭证)
source ~/miniconda3/etc/profile.d/conda.sh && conda activate depending43
OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/ -q

# D1 资产分布(参数卡依据,零金标)
OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_asset_stats.py

# D2 重映射管线(只读 v1;产出 v2 + provenance)
OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/build_analog_v2.py --workers 6
OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_v2_review.py

# D3.1 零 API 消融(dev 20 输入,零金标)
OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_offline_ablation.py

# D3.2 真实臂(Chenyu;顺序 driver,凭证 env 注入)
#   configs/phase_d_{C0,D3,D5,D10}.json + runs/phase_d_driver.log
# 配对判分(零 LLM)
OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  scripts/phase_d_paired_scoring.py \
  --arms C0=runs/phase_d_C0 D3=runs/phase_d_D3 D5=runs/phase_d_D5 \
         D10=runs/phase_d_D10 --v3-root <dependingv3> \
  --out-dir reports/phase_d/scoring
```

关键 SHA(完整值随产物):`corpus_templates_v2.jsonl fabe4e24…3d6db`、
`assets/MANIFEST.sha256`(22 条,Phase D 起)、`v2_remap_summary.json`、
`ablation_summary.json`、四臂批次身份 short 见 `reports/phase_d/arms/*_batch_report.json`(batch_sha256)。金标 SHA 单独登记于批次产物,
运行进程零接触。

## 10. 交付清单

- 代码:`analog_source.py`(相似索引+通道)、`donor_applicability.py`
  (三段评估序/budget_not_assessed/displaced/通道透传)、`policy.py`
  (v43-predpol-3 + 相似参数)、`models.py`(v43-policy-4)、`nodes.py`
  (classify 接线)、`batch.py`(policy 贯穿+身份)、`config.py`/
  `asset_manifest.py`/`run_identity.py`(语料选择与身份)、
  `__main__.py`/`runner.py`(恒注入 resolver)。
- 资产:`corpus_templates_v2.jsonl`(17183 行)+ 双清单(22 条)+ 显式
  装载开关;v1 与封存产物零改动。
- 脚本:`phase_d_asset_stats.py`、`build_analog_v2.py`、
  `phase_d_v2_review.py`、`phase_d_offline_ablation.py`、
  `phase_d_paired_scoring.py`。
- 测试:`test_reactant_similar.py`(19)、`test_analog_v2_corpus.py`(5)
  + 全仓回归零退化。
- 报告与数据:`reports/phase_d/**`(分布统计/消融/provenance/复核/评分);
  真实臂产物在 Chenyu `runs/phase_d_*/`(批次身份/账目/答卷)。
