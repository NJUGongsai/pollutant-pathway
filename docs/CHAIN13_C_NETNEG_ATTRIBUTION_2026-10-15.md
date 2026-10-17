# chain13 C 供给净负贡献归因报告（技术版，2026-10-15）

> 题域标签：**298=RHEA 通用酶学/已见题**，与 dev 双向不外推。
> 性质：离线只读归因（零模型/零网络/零判分重算），探针≠预注册≠成绩。
> 任务书：`docs/TASK_CHAIN13_C_ATTRIBUTION_2026-10-15.md`；数据产物与主脚本：
> `reports/ppv1_s5b/chain13_glm/analysis/{attr_chain13_c.py,attr_chain13_c.json,attr_chain13_c_summary.md}`。
> 大白话版：`docs/CHAIN13_C_NETNEG_ATTRIBUTION_PLAIN_2026-10-15.md`。

## 一、结论先行（三句）

1. **C 线+v2 合并自效应净零**：C 门开的 35 题 strict 24（chain12）→ 19（chain13 v1）→
   **24（chain13 v2）**，回到 chain12 水平；v1 下行 5 题（S→P 4 + S→U 1）被 v2 豁免
   整体兜回（3 题 S→P→S + 2 题 U→P→S，后者为净赚路径）。
2. **v1 strict -16 的主损失在输入零变化的 263 题（-11，106→95）**，归因采样/服务端
   非确定性：18 个非 C 损失题中 **18/18 规范化扩展面（候选内容集）变化而 18/18 池
   compiled 计数两批相等**（输入零变化、供给面稳定、模型/扩展面全变）；
   **"非确定性无法逐题定责"——本报告不给单题因果断言**。
3. **13 题模拟豁免兑现 0/13 的根因=供给门未开（面不交集）**：13 题在 chain13 的
   297 个池候选中 289 件死编译门（no_alignment=141 为最大拒因），6 件 compiled
   也未触发 analog 前置门+Tanimoto 伴生救援（资格条件未罩住），rescued/declared
   全 0；事件面 13/13 连 role=cosubstrate 参与物都不存在（供给面差，非生成面差）。

## 二、C1 迁移矩阵×C 暴露复核（与任务书骨架逐格对照=零不一致）

v1 口径（chain12 `synced/metrics.json` ↔ chain13 `synced/metrics.json.v1`，逐题）：

| 迁移 | 全 298 | C 门开 35 题 | 输入零变化 263 题 |
|---|---:|---:|---:|
| S→P | 10 | 4 | 6 |
| S→U | 13 | 1 | 12 |
| P→S | 2 | 0 | 2 |
| U→S | 5 | 0 | 5 |
| P→U | 8 | 0 | 8 |
| U→P | 9 | 2 | 7 |
| **strict 净变化** | **130→114（-16）** | **24→19（-5）** | **106→95（-11）** |

- 同状态保持数（未列迁移的补全）：全 298 S→S=**107**、P→P=33、U→U=**111**。
  【2026-10-15 勘误（GPT hit50 诊断 §7 抓出，主会话核实）】：本行原写
  S→S=115、U→U=110，系自 JSON（`attr_chain13_c.json → C1.matrix.all`=
  107/33/111）转录错；闭合校验 107+10+13=130、111+5+9=125、251 保持+47
  迁移=298 全对。迁移矩阵本身（10/13/2/5/8/9）零错误，净结论不受影响。】
- C 门分布复核：open=35（==cexposed 清单），dist={0:263, 1:30, 2:4, 3:1}。
- **骨架对照：矩阵 6 格×3 列 + strict 净 3 组 + C 门分布，全部一致，零硬凑。**

### rank 面（两批都 strict 的 107 题，v1 rank 迁移）

| 类别 | 题数 | 类别 | 题数 |
|---|---:|---|---:|
| 1→1（不变） | 71 | 2→1 | 5 |
| 1→2 | 7 | 2→2（不变） | 6 |
| 1→4 | 1 | 2→3 | 4 |
| 3→1 | 3 | 2→5 | 1 |
| 3→3（不变） | 3 | 3→4 | 2 |
| 3→5 | 2 | 4→1 | 1 |
| 5→6 | 1 | | |

### hit@1 headline 分解（chain12 v1 92 → chain13 v2 87，-5）

chain12 v1 hit@1 载体（strict∧rank=1，92 题）→ chain13 v2 载体（87 题）：

| 分解 | 题数 |
|---|---:|
| kept（两批都是载体） | 74 |
| lost：掉出 strict（覆盖损失） | 10 |
| lost：仍 strict 但 rank>1（排名损失） | 8 |
| new（chain13 新载体） | 13 |

闭合自检：74+10+8=92 ✓；74+13=87 ✓；-5 = 13-18 ✓。逐题清单见
`attr_chain13_c.json → C1.hit1_v2_decomposition`。

## 三、C2 C 35 题 payload 级声明链追踪

35 行全表见 `attr_chain13_c.json → C2.rows`。汇总：

| 证据面 | 计数 |
|---|---:|
| C spec 动作存在（search_actions 内带 `cosubstrate_event_contract`） | 35/35 |
| C spec 选中并执行（action status=done） | 35/35 |
| 事件含 role=cosubstrate 参与物 | 35/35 |
| manifest 声明 spec>0（`n_cosubstrate_declared_specs`） | 35/35 |
| run_error（ProductionContractError） | **0/35** |

**C 线在 35 题内供给-执行-参与-声明四层全通，且零 fail-closed 拒题。**

### 重点 4 题

| 题 | 迁移 | 机制结论 |
|---|---|---|
| `RXNG_4a529de4…`（S→U 1 题） | S→U→U | **非 fail-closed**：无 run_error，C spec done、cosub 参与物 C#N 在场、声明链 1 条。事件面貌重组：chain12 的 strict 命中事件（产物 `CCC(C)N`+共产物丙酮+O）在 chain13 未再现；chain13 新出现 C#N cosub 事件但产物变为氰醇 `CCC(C)(O)C#N`，另一 `CCC(C)N` 事件丢失丙酮共产物——两批事件 participant 全表见 `C2.focus.S→U_1q_event_faces`。归因=采样/扩展面变化与 C 供给介入的叠加，**不能单因子定责**（诚实 unknown）。 |
| `RXNG_654cc41…`（S→P→P 1 题） | S→P→P | H₂O 家族（cosub=O 已声明在场、C spec done），**但 v2 未豁免**。【2026-10-15 mimo 场景 3 复核后更正】原稿的排除推理「未触发⇒缺口不在共底物参与物面上」**不成立**（反例：缺口=另一条无声明链事件上的 H₂O extra ⇒ pred1 unknown fail-closed ⇒ 同样不触发，但缺口恰在共底物面上；且机制身份 extra 与同事件非豁免 extra 共存也不触发）。正确降级表述：**缺口不是『superset 形态+豁免身份+已声明+三谓词全过』的可豁免形态；具体身份 unknown**（判分侧未披露逐 extra 明细，见 mimo 回应 Q2：`docs/mimo_chain13_scene3_review_response.md`）。旁证：本题 4 事件仅 1 个带 cosub 参与物/provenance，其余 3 事件大概率无链——「本事件带链」≠「判定键事件带链」。5 个 rescue 题同为 H₂O 家族皆救回，只证明家族充分性不成立，不证明逆命题。 |
| `RXNG_5e9b5672…`、`RXNG_8dce8a33…`（U→P→S 2 题，净赚） | U→P→S | C 供给把 uncovered 题抬到 partial（cosub 参与物入场+声明链），v2 豁免兑现 P→S。这是 C 线唯一正向增量（+2 strict）。 |

## 四、C3 损失题候选集差分（S→P 10 + S→U 13 = 23 题）

方法：对每题对比 chain12 vs chain13 payload 的 expand_hypothesis spec 集与池计数。
**主证据用规范化签名**（donor.center_atom_ids 排序 + edits 逐条排序 + expectation.target_smiles
+ product_smiles + coproducts 排序；刻意排除 run 专属引用 `cs_*`/`hyp_*` 与 alignment.ref
措辞，避免把"同化学不同顺序/措辞"算成面变化——首轮未规范化的 sha1 签名会高估，已废弃）。

| 证据面（非 C 18 题） | 结果 |
|---|---|
| 规范化扩展面（候选内容集）变化 | **18/18** |
| 池 compiled 计数两批相等 | **18/18** |
| chain13 扩展面零 spec（例外，如实列） | 2 |

- 2 个零 spec 例外：`RXNG_71774ffe…`（`real_model_transport_failure`，模型调用 failed，
  扩展面归零）与 `RXNG_aefef2f5…`（A 桶：池 compiled 双批皆 0，chain12 靠 novel 提案
  撑起 4 事件，chain13 novel 面=0 → no_local_candidate）——两者本身就是**服务端/采样
  面非确定性的直接样本**。
- 非 C 18 题分桶迁移：H→H 16、H→B 1（transport）、H→A 1（novel 塌缩）。
- C 暴露的 5 个损失题（S→P 4 + S→U 1）扩展面也全变（C 线新增候选叠加采样变化，
  不单独归 C）。
- **结论：输入零变化 + 供给面（池）稳定 + 模型/扩展面 18/18 全变 = 采样/服务端非
  确定性的面上证据成立；例外已如实列出；逐题"哪一次采样导致哪一题丢 strict"不可
  定责（无重复批可对拍）。**
  【2026-10-15 补注（回应 GPT hit50 诊断 §2.4 对「263 输入零变化」的保留，主会话实测闭合）：
  C 交付书 byte 探针的「1 题 W4 补位互动」= RXNG_9683627…，实测**在 C 门 35 题内**
  （rescued=3，P→P→P，非损失题）；探针纯新增面与实跑 C 门恰好差一题互换（探针面
  RXNG_0faafc67…/实跑面 W4），前者为 strict→strict 亦非损失题。⇒ **18 个非 C 损失题
  逐题确认全部输入字节不变**，本节结论无保留成立；「263 输入零变化」为 byte 探针
  262 全等+一题无计分影响的 build 口径互换的合并表述，如上精确化。】

## 五、C4 13 题模拟豁免面复核

| 证据面 | 结果 |
|---|---|
| chain12 rescore `in_cs2c_13`（13 题清单） | 与本地 sim13 清单一致 |
| chain13 v1 终态 | **8P / 4U / 1S**（与预期一致，逐题清单 `C4.terminal_state_qids`） |
| chain13 事件含 role=cosubstrate 参与物 | **0/13** → 全部「供给面差」（连参与物都没有），非「生成面差一口气」 |
| chain12 rescore events_reviewed 披露参与物 SMILES | **0/13**（字段仅 declaration_status/tiers/event_id_suffix/n_occurrences/all_exempt——如实记录，参与物判定降级为 role 代理，未对金标核实身份） |
| manifest rescued / declared | **0 / 0（13/13 全零）** |

### 供给门资格面（钥匙重设计方向的描述性证据，只描述不修）

13 题池候选 297 件的结局：

| 候选结局 | 件数 |
|---|---:|
| compile_rejected | 289 |
| compiled（但未触发救援） | 6 |
| merged_into | 2 |

编译拒因分布（候选行）：no_alignment=141、mapping_enumeration_truncated=76、
transform_no_change=31、cosubstrate_bonded_contribution_unsupported=25、
no_structure_correspondence=12、ambiguous_alignment=2、product_set_mismatch=1、
ambiguous_mapping=1。检索面 corpus_diagnostics 直方图合计：
**unsupported_wildcard_atom=1192**（最大宗）、mapping_enumeration_truncated=76、
cosubstrate_bonded_contribution_unsupported=25、corpus_provenance_missing=6 等。

**资格面没罩住 13 题的两层事实**：①绝大多数候选死在编译门之前/之中（对齐/映射
枚举/键贡献不支持），供给门根本没收到合格件；②6 件 compiled 存在但 rescued 仍
=0——analog 前置门拒绝+Tanimoto 伴生救援的资格条件未把它们判为可救。修复方向
（若拍板重设计）应在资格面：让 partial 面题的共底物进袋；本报告只描述，不修。

## 六、C5 采样参数与身份留痕

| 件 | 值 |
|---|---|
| run_identity（298 件） | code `aggregate_sha256` 去重=1：`37decacf1b8a94c3028f424bb45d67a2b1a163dce332b9c8b762881fcbbf9542`；asset identity 去重=1（analog_corpus v1） |
| s5b_real_calls.jsonl | 296/298 文件（缺 2 个=远端本无：两个 `cosubstrate_copy_in_expectation` run 零模型调用即终止）；调用行 596=issued 298 / responded 288 / **failed 10**（10 个失败=10 个 `real_model_transport_failure` case，账实相符） |
| 采样参数结论（主会话预核采信） | 调用未显式设置采样参数（provider_env 仅 *_set 布尔、request_params_set=false；记录无 temperature/model 值字段），温度由服务端默认决定；**非确定性按服务端行为处理** |
| budget_mode | chain13=`no_monetary_cap_user_decision`；chain12=字段不存在（no-cap 运营壳为 461844e 移植，chain12 批先行）——差异如实记录 |
| chain12 synced 结构差异 | 每 run 仅 manifest.json+payload.json（298+298），无 run_identity/ 无 calls 快照；对比参数面以 chain13 自身留痕为准，chain12 侧记缺 |

## 七、拍板材料：C 线三选一证据面

| 选项 | 证据面 | 本报告的读法 |
|---|---|---|
| 回滚 | C 35 题 v1 -5 但 v2 兜回 24（净零）；U→P→S 净赚 +2 依赖 C 线 | 回滚将同时丢掉净赚与豁免兑现面；**证据不支持回滚** |
| 收窄 | 收窄预设存在 fail-closed 误拒：C35 内 run_error=0/35；S→U 1 题非 fail-closed（C2）；2 个 NC-9 拷贝组分拒为双批同拒（chain12 亦有 2 例同 kind，U→U 不变），非 C 线回归 | **收窄当前没有修复对象**；若未来出现真实误拒样本再议 |
| 重设计 | 13 题钥匙资格面：289 件死编译门（no_alignment 主因）+6 件 compiled 未触发救援资格+检索面 wildcard_atom 1192 | **重设计方向=供给门资格面扩罩**（让 partial 面题的共底物进袋）；与「13 题兑现 0/13 根因在供给门」的骨架结论一致并给出候选级证据 |

### 方差治理参照（不冒充 CI）

同协议族参照：hpc2 RR A/B 两臂（v44 仓 `v44/reports/ppv1_s5b/hpc2_{a,b}/metrics.json`，
v1 口径，RR 开关单变量）：A=126/42/130、hit@1/3/5=94/121/124；B=129/43/126、
93/124/128；逐题状态翻转 **34/298**（S 损失 10：S→P 3+S→U 7；净 strict ±3）。

本批 chain12→chain13：翻转 47/298、S 损失 23、净 strict -16——**量级为 A/B 参照的
1.4~2.3 倍**。A/B 非纯重复批（RR 是真实干预），只作量级参照：本批下行超出同协议
波动参照，但 chain13 是多变量叠加批（C 供给+声明链+v2 判据+3 调用预算，3 调用
预算实测零消费），**不能把超额部分单归 C 线**；C 线可归因份额已由 §三/§四钉死：
C 35 题内净零、主损失在 263 题的非确定性面。

## 八、与任务书 §一骨架结论的不一致清单

**零不一致。** 矩阵 6 格×3 列、strict 净 3 组、C 门分布、35 题四层全通、S→U=非
fail-closed、S→P→P=H₂O 家族未豁免（缺口不是可豁免形态、身份 unknown——mimo Q2 更正后口径）、U→P→S 净赚 2 题、13 题终态
8P/4U/1S、13 题 rescued=0/declared=0——全部与骨架一致。唯一补充披露（非不一致）：
calls 文件 296/298（2 run 远端本无该文件，零模型调用 run，已核实）、chain12 synced
无 identity/calls 快照（结构差异如实记录）。

## 九、provenance 与红线声明

- 执行环境：本地 Mac，python3 stdlib；HPC 只读拉取（scp/rsync，wuzh02 节点）。
- 拉取命令与验收：批根 4 件 scp；cases rsync（298/298）；runs rsync 过滤
  `-f '+ */' -f '+ payload.json' -f '+ run_identity.json' -f '+ s5b_real_calls.jsonl' -f '- *'`
  （payload 298/identity 298/calls 296）；funnel 行数 298/298、mapping_issues=0。
- 输入哈希（sha256，见 `analysis/synced_top_sha256.txt` 与 `attr_chain13_c.json →
  provenance.inputs_sha256`）：chain13 metrics `f2e5003c…`、metrics.v1 `49eec917…`、
  batch_manifest `851a2d01…`、batch_report `a5f3db46…`；chain12 metrics `f435ad7a…`、
  rescore data `4a812f38…`；funnel chain13 `f14feed6…`、funnel chain12_r2 `cdbb37c1…`。
- 红线遵守：零 LLM/零模型调用/零判分重算（只消费既有判分产物）；HPC 批根与 runs
  根只读；金标/题面未读、未入仓；`src/`、`tests/`、既有 docs/AGENTS.md 未动；
  未 commit、未 push；分析输出全部落 gitignored `reports/ppv1_s5b/chain13_glm/analysis/`
  与本报告两份 docs 文件；对外数字均带题域标签 298。
- 本仓 HEAD：461844e（分支 v4.3）。
