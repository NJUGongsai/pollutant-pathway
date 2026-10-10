# PPV1 S5b HIT50 v4 复测发车登记（2026-10-10）

状态：`ready_for_real_retest / launched`。正链 Codex v4-R1 复审
（docs/POLLUTANT_PATHWAY_S5B_HIT50_V4_R1_CODEX_REVIEW_2026-10-10.md）
：**S5B-V4-01 关闭、P1=[]、chain11 工程有条件放行**；mimo r31
（docs/mimo_ppv1_chem_review_response_r31.md）：**同意——诚实拒满足
r30 R2-2 最低要求（corpus 组分级通道断供闭合）、与冻结判据零冲突**。
本登记=放行条件的执行（新登记冻结+读回封包）。

## 一、评审链

- v4 实施轮 3725379（W-V4.1 RHEA 接线，用户六决策）→ Codex v4 复审
  P1=S5B-V4-01（共底物 add_atom 伪装通道，配平反例实证）→ 回修 R1
  bd6e836（候选装配层编译前结构化 unsupported）→ Codex R1 复审
  关闭清零放行 → mimo r30（身份判据 G1-G4）+ r31（诚实拒范围 H1-H3）
  两轮化学评审。
- 主会话独立核验：v4 全量 1976/0/16、R1 全量 1978/0/16（均复跑一致），
  许可规则/分层判据/正控抽查合格。

## 二、冻结身份（首次真实调用前冻结；任何变化即停批另立新登记）

- 代码：本地 `bd6e83674a8d5d39b6ef70a72514add966a53a34`（父链
  376ee0c←3725379←bd6e836）；Chenyu 部署 = 自 d240045 起 2 个变更
  src 文件（recorded_source.py、s5b_builder.py）SHA 逐一字节一致。
- 协议版本：**s5b-corpus-retrieval-2**（cosubstrate_permission 键）、
  **s5b-pool-policy-3**、s5b-compiler-1、s5b-recorded-source-1、
  s5b-rank-policy-1、s5b-submit-order-1、s5b-budget-guard-1、
  s5b-orchestrator-2、s5b-real-model-1。
- 提示词：PROPOSALS_PROMPT_VERSION `e28b5342b0036a6a…`（与 v2/v3 批
  相同）；模型 GLM-5.3-Flash 现有授权 provider。
- profile：depth=1、8 备选、width=2、1 logical/题、format0、
  HTTP retries4、workers/max_in_flight=40、RPM180/TPM2.7M、
  HTTP cap 1490。
- 金额守卫：budget_guard.json cap 60 CNY、0.8/2.8 元/Mtok（沿用值
  如实披露）、input bound 30000、max_output_tokens 98304
  （v2 实测分布定界）；发送前原子预留；429/缺轴/自矛盾/未知保守
  保留；存储冻结块同源校验；结算幂等。
- 供给：EAWAG recorded 直通（原样）+ **corpus_v1 整串子集直通**
  （组分级共底物候选一律 corpus_cosubstrate_participants_unsupported
  编译前拒）；类比模板池同 v3。
- 评分：零 LLM；主列 hit@1≥119/298；hit@5 150 参考；§9-4 程序门
  （含空集/缺键/foreign 形态拒）；U/H5/L 披露。
- 题源：ec298_gold_readonly/questions.jsonl SHA 9f5955d4…（发车日
  两端实核）。

## 三、mimo r31 措辞护栏（P1 级，随登记冻结）

1. "共底物原子经 add_atom 伪装新增"禁令范围 = **记录已声明的共底物**
   （corpus 组分级通道）；记录未声明的隐式来源（水/受体/氧）不在
   禁令内、仍合法经 add_atom 产生（EAWAG 水解正控即此），元素账按
   判据二 unknown 登记。任何"本轮后事件不再出现无声明来源原子"的
   表述 = 错误。
2. G2-c 闭合定性 = **通道级断供闭合（corpus 组分级）**，非机制级/
   全局闭合；判据二 unknown=无守门是冻结判据既定性质，本轮不触碰
   也不宣称修复。

## 四、期望登记（诚实，非承诺）

- corpus 通道净供给 = 14 整串 spec/13 题（组分级 1,323 候选编译前拒，
  留待"显式共底物参与物语义"独立设计轮解锁）。
- 预期 U 106→**110±**、hit@1 大概率 73→**76±**：**hit@1≥119 本轮
  如实不达**；本批目的=干净兑现 RHEA 整串供给 + 为 v4b（编译墙）与
  共底物设计轮提供批级证据。
- 反事实/离线漏斗数字不构成命中承诺；298 题域标签、适应性评测
  诚实标注（seen298_post_hoc_repair_check / known_evidence_
  reconstruction）。

## 五、批与执行

- 新批根：`/usrdata/EnzymeCAGE_data/workspaces/s5b_298_v4_20261010`
  （旧批封存只读）。
- 执行链：chain11（SHA 门→envcheck→build --recorded-source→approve
  →budget→冒烟 10 前缀→闸→全量 298→零 LLM 判分→§9-4 门+U/H5/L→
  hit@1 119 判定）。
- 停批条件沿 v3 登记（401/403/402 停新付费、金额/HTTP/输出上限、
  身份变化即停）。
