# PPV1 S5b HIT50 复测发车登记（2026-10-09）

状态：`ready_for_real_retest / launched`（任务书
`docs/TASK_V43_PPV1_S5B_HIT50_UPGRADE_AND_RETEST_2026-10-09.md`
§3 预授权路径：实施完成 → 主会话复审通过 → 新登记 → 同模型真实 298）。

## 一、复审结论（主会话，2026-10-09 22:0x）

- 实施提交 `35727eb2b5f548d07755430ad6d5f59fbb429b5c`（父 `0d86c48`；
  24 文件 +4682/−341；未 push）。
- 复核证据：提交构成与树干净 ✓；交付书证据链（定向/全量/G01/十二组
  覆盖/金标边界自查）✓；关键抽查 R1 白名单 / W3 created_at 忠实性 /
  W3 effective_rank / W5 逐条容错 / W4 池策略常量与补位 ✓；
  本机全量复跑 `1813 passed / 0 failed / 16 deselected`（264.5s）与
  交付一致 ✓；父基线红绿：两个新测试文件在 `0d86c48` 收集即错
  （依赖新模块）+ 行为级红 `preregistration_approved({'rejected'})`
  父=True（误放行）→ 现=False ✓（复测探针首次被已安装包污染，
  显式 sys.path 插入 + `__file__` 断言后重测，两臂同源错误已排除）。
- 待复审 5 项处置：①W3 去重按任务书原文执行，S4a 三夹具改造保留原
  意图，契约差异随 mimo r27+ 与 Codex 复审披露，不阻塞；②R5 默认值
  变更为 §3 首批冻结数值的实施，发车价按当日快照定稿（见 §三）；
  ③scripted 桩 blob 跳过为测试语义，真实路径必配 account path，
  不阻塞；④W2 source-only 0 模型独立路径任务书措辞为"可"非"必须"，
  本轮不做，recorded 池经确定性 fallback 仍可 0 模型入候选；
  ⑤历史 G01 未含 s5b runtime 为已披露历史缺口，本轮已补，历史轮
  封存证据不改不重跑。
- 结论：`implementation_ready_for_review → ready_for_real_retest`。

## 二、冻结身份（首次真实调用前冻结；任何变化即停批另立新登记）

- 代码：本地 `35727eb`；Chenyu 部署 = 15 个变更 src 文件按 SHA
  逐一校验字节一致（部署清单=git diff `0d86c48..35727eb -- src/`）。
- 协议版本：`s5b-compiler-1`（W1 共同编译器）、
  `s5b-recorded-source-1`（W2 exact recorded 源）、
  `s5b-pool-policy-1`（W4：raw24/pool8/阈值 0.45→不足 3 独特候选
  条件降 0.40/编译失败补位/exact+analog 融合序）、
  `s5b-rank-policy-1`（W3：显式模型位次先于 fallback、novel 位次
  补回、净反应签名去重合并 provenance）、`s5b-real-model-1`。
- 提示词：`PROPOSALS_PROMPT_VERSION` 内容哈希
  `e28b5342b0036a6a…`（中性"酶促单步转化"任务、≤8 净反应、
  弃权合法；内容变更自动升版）。
- 模型：GLM-5.3-Flash，现有授权 provider（env `V43_LLM_*`，
  凭证只 env 内存）；不换模型、不多模型、不多次成功采样。
- 检索/池：`--recorded-source` 开（W2 exact 通道）；类比模板池
  `s5b-pool-policy-1` 参数如上；池 provider 只消费 substrate，
  不按 qid 查答案、不接金标/参考图/旧正确 source ID。
- profile（首批冻结）：depth=1、最多 8 备选尝试、产品展开 width=2、
  **每 qid 1 次逻辑 proposal**、格式反馈轮 0、HTTP retries=4
  （初次+4=5 总尝试）、HTTP timeout 沿现值、workers/max_in_flight=40、
  RPM 180、TPM 2.7M、**gate max_calls=1490**（298×1×5 理论上限）。
- 评分：零 LLM；主口径 hit@5 ≥150/298=50.34% 判
  `target_met_seen298`；配对 §9-4 硬门（bases 全 qid_strict）；
  U/H5/L 聚合诊断一并披露；失败/unknown/无候选/预算漏答留 298 分母。
- 题源：`ec298_gold_readonly/questions.jsonl`，SHA
  `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`
  （发车日两端实核）。

## 三、预算与停止策略

- 价格快照（发车当日，沿今晨已落值）：input 0.8 / output 2.8
  CNY/Mtok；费用字段分 input/visible content/billed output/
  reasoning/usage unknown 与延迟记账。
- 安全硬帽估算 **60 CNY**（任务书 §3 估算值；按 1490 次调用
  上限与历批 token 均值推算，充裕）；预算硬帽与 gate cap 先于
  send 生效；预算耗尽早停仍留 298 分母，不自行升预算。
- 单协调者（flock）+ run 锁；断点续跑仅同批同身份（prompt/池/
  模型/retry/profile 变化即停批、如实披露、另立新登记新批）。
- 冒烟：冻结注册序前 10 题作为**正式新批前缀**（同一 298 分母，
  不另批）；只看运行完整性/费用，不看 gold、不做中期命中调参；
  0 题完成=链路断，停批修复（冒烟段答案保留，不重采样）。
- 停批条件：401/403/402 停新付费；预算/HTTP/输出上限触顶；
  凭证或模型权限异常；其余按 gate/超时纪律保守失败留分母。

## 四、批与执行

- 新批根：`/usrdata/EnzymeCAGE_data/workspaces/s5b_298_hit50_20261009`
  （batch_root/runs_root/gate/cases/ledger 全新；旧批
  `s5b_298_20261009_batch2` 封存只读）。
- 执行链：chain9（SHA 门 → envcheck → build --recorded-source →
  approve → price → 冒烟 10 → 闸(≥1 完成) → 全量 298 → 零 LLM
  判分 → §9-4 配对硬门 → U/H5/L → 报告）。
- 结果定位：`seen298_post_hoc_repair_check / known_evidence_
  reconstruction`（适应性评测，不称独立盲测、不外推 dev 题域）；
  对外数字带 298 题域标签与口径名。
- 预注册历史线 `S5B_PASS_LINES`（116/128/130）为历史参照线不改；
  本批目标线 150 为新登记独立字段。

## 五、诚实边界

- 298 已被观察并用于目标驱动迭代（适应性）；参数选择未用独立
  未见开发集（W4 阈值比较无授权开发集，本轮仅冻结参数+合成正负控）。
- charge-only/stereo-only 编辑与芳香新成键首版 unsupported；
  recorded CN candidate 不升 strict——供给损失如实披露。
- 本登记与发车由主会话按任务书预授权执行；mimo r27 请求
  （`docs/S5B_HIT50_W7_MIMO_CHEM_REVIEW_REQUEST_2026-10-09.md`）
  由用户送审，回复按"与程序证据互证"采信，不阻塞本批。
