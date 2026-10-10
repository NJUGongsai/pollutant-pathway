# PPV1 S5b HIT50 v3 复测发车登记（2026-10-10）

状态：`ready_for_real_retest / launched`。正链 Codex R3 复审
（docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_R3_CODEX_REVIEW_2026-10-10.md）：
**R3 通过、S5B-V3-02 清零、P1=[]，chain10 工程侧有条件放行**——条件=
受权协调者完成 §7 六条发车步骤并封包（本登记即该步骤的执行）。
任务链：任务书 docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md（用户
2026-10-10 凌晨授权"继续修复继续测"）→ 实施轮 0c6e45d（W-V0~V6）→
正链 Codex 复审两 P1 → 回修 R1 fecb0005 → 措辞微修 b502b75（mimo
r29-F2）→ 回修 R2 d08432c → 正链 R2 复审三残余 → 回修 R3 d240045 →
**正链 R3 复审放行（本登记 HEAD）**。评审事件：R2 复审曾撞额度
（9.47M tokens）切通道 C（tokeasy）亦差 $0.0013，正链 08:28 重置后
resume 出报告——全程如实记录于各复审报告。

## 一、评审链与放行依据

- 正链 Codex 链（01a11e94→01a12223→01a1226a→01a12299→01a12375）：
  首轮全量复审两 P1 → R1 回修后三残余 → R2 回修后两残余 → R3 回修后
  **清零放行**。挂账的 launch/runtime 事后补审已在首轮兑现。
- mimo：r28（三判断面）+ r29（采纳核对零化学阻塞）；R1/R2/R3 为纯
  程序语义回修，mimo 步按 AGENTS.md 既有职责登记实际跳过（各复审
  报告确认可接受，不冒称已做化学评审）。
- 主会话独立核验：每轮回修后全量复跑（1933/1958）与代理报告一致，
  关键修复点逐轮抽查。

## 二、冻结身份（首次真实调用前冻结；任何变化即停批另立新登记）

- 代码：本地 `d24004533e5e3a48f9c4a35049fed20f1d227afa`（父链
  35727eb←0c6e45d←fecb0005←b502b75←d08432c←d240045）；公开函数
  legacy52 实测聚合 `279d9bc19bad25e51b7c23ee276da95151a8f25cf
  598b9dc3642b508d817c4bb`；Chenyu 部署 = 13 个变更 src 文件按 SHA
  逐一校验字节一致（清单=git diff 35727eb..d240045 -- src/，含
  rate_gate.py；部署日志 /tmp/deploy_v3r3.log）。
- 协议版本：s5b-compiler-1 / s5b-recorded-source-1 / s5b-pool-policy-1
  / s5b-rank-policy-1 / s5b-submit-order-1 / s5b-budget-guard-1 /
  s5b-orchestrator-2 / s5b-real-model-1。
- 提示词：PROPOSALS_PROMPT_VERSION 内容哈希 `e28b5342b0036a6a…`
  （中性"酶促单步转化"，与 v2 批相同）。
- 模型：GLM-5.3-Flash 现有授权 provider（env V43_LLM_*，凭证只
  env 内存）。
- profile（首批冻结）：depth=1、8 备选、width=2、1 logical/题、
  format0、HTTP retries4、workers/max_in_flight=40、RPM180/TPM2.7M、
  HTTP cap 1490。
- **金额守卫（S5B-V3-02 机器生效，R3 复审后）**：budget_guard.json
  cap_cny=60、input 0.8 / output 2.8 元/Mtok（价格来源：2026-09-29
  价格记录沿用值，发车日未联网刷新——如实披露）、
  **input_tokens_bound=30000（v2 批实测最大输入 6,514，充裕）**、
  **max_output_tokens=98304**（v2 批实测输出均值 21,307/最大
  71,938 tokens，推理模型长思维链——CLI 缺省 8192 会截断全部回答，
  发车日按实测分布定界 98304≥72K 观测最大+余量；单次保守预留
  ≈0.299 CNY、40 在飞峰值预留 ≈12 CNY，60 帽内放得下全批）；发送
  前原子预留（settled+unsettled+reserved+bound≤60 才发）；429/部分
  usage/自矛盾 total/未知结局保守保留不退；存储冻结块同源校验；
  结算幂等；overrun 披露不回滚。
- 评分：零 LLM；验收主列 hit@1≥119/298（用户指定 40% 档）；
  hit@5≥150 参考列；§9-4 程序门（real∧非全 qid_strict ⇒ 拒，含
  空集/缺键/foreign 键形态拒）；U/H5/L 聚合诊断披露。
- 题源：ec298_gold_readonly/questions.jsonl SHA 9f5955d4…（发车日
  两端实核）。

## 三、§9-④ 同步句原文插入（r29-F4 义务，正链 R1 报告 §7 待插原文）

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的
> 守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图
> 集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，
> 任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与
> 覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档
> 改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判
> 定，不得沿用整批判。

读回核对：本段与 evaluation.py 整批二档守卫、s5b_scoring §9-4 门
的现行行为方向一致（合法全 strict 通过；空/缺/foreign/非 strict 拒）。
本登记全文 SHA 随发车证据封包（部署后回填）。

## 四、预算与停止策略

- 每题 1 次逻辑调用；HTTP cap 1490；金额帽 60 CNY 发送前机器生效
  （见 §二）；预算耗尽早停留 298 分母不升帽。
- 单协调者 flock + run 锁；断点续跑仅同批同身份。
- 冒烟：冻结注册序前 10 题为正式批前缀（同分母）；0 题完成=链路断
  停批；冒烟答案保留不重采样。
- 停批条件：401/403/402 停新付费；金额/HTTP/输出上限触顶；凭证或
  权限异常。

## 五、批与执行

- 新批根：`/usrdata/EnzymeCAGE_data/workspaces/s5b_298_hit50v3_20261010`
  （旧批 s5b_298_hit50_20261009 封存只读）。
- 执行链：chain10（SHA 门→envcheck→build --recorded-source→approve
  →budget 机器配置→冒烟 10→闸→全量 298→零 LLM 判分→§9-4 门+
  U/H5/L→hit@1 目标线判定）。
- 结果定位：seen298_post_hoc_repair_check / known_evidence_
  reconstruction（适应性评测，不称盲测不外推 dev）。
- 正链复核确认：Codex 额度 08:28 恢复后，本批放行依据与（若已出）
  结果一并交正链有限复核确认。

## 六、诚实边界

- 反事实 73/98/100 是旧候选固定集合的机器诊断，不是新批承诺；
  W-V2 实际恢复面小（4/228），U 增益主要靠排序修复兑现（预期
  H5→≈U≈100 量级），hit@1 119 本轮大概率不达——属"争取达成"型
  目标，未达交完整报告与下一版任务包。
- 通道 C 复审为备用通道意见；正链最终裁定权保留。
