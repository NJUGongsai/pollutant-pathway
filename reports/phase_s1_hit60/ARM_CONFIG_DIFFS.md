# ARM_CONFIG_DIFFS — S1 dev 四配置预登记差异表(HIT60 S1,机读登记)

登记时间:2026-09-29(施工代理C,S1 变更集施工;先于任何付费调用;
E1 行由 E1 跑分代理于 E1 发车前补登记,见 §4.4)。
性质:**预注册差异**(PREREGISTRATION.md §1.3 的落地件)。跑分配对判定时,
两臂身份/配置的合法差异**只认本文件列出的字段**;出现本表之外的差异 =
预注册被破坏,该批不得进判定(须新批次根重跑)。

- 基线(对照臂):`configs/s1_dev_C0.json`(= 当前行为:不发送 temperature、
  rank 窗口 8、rank 候选呈现 v1)。
- 实验臂:`configs/s1_dev_E2.json`(唯一实验差异 `temperature=0.0`)、
  `configs/s1_dev_E3.json`(唯一实验差异 `max_candidates_for_ranking=16`)、
  `configs/s1_dev_E1.json`(唯一实验差异
  `rank_candidate_presentation="v2"`,2026-09-29 E1 发车前补登记)。
- 判定规则、配对结构、费用上限:见 [PREREGISTRATION.md](PREREGISTRATION.md)。

## 1. 逐字段差异表(相对基线 C0;全量扫描,未列字段 = 四配置完全相等)

| # | 字段路径 | C0(基线) | E2 | E3 | E1 | 类别 |
|---|---|---|---|---|---|---|
| 1 | `arm` | `s1_dev_C0` | `s1_dev_E2` | `s1_dev_E3` | `s1_dev_E1` | 基建标识(臂名,非行为) |
| 2 | `batch_root` | `s1_dev_C0` | `s1_dev_E2` | `s1_dev_E3` | `s1_dev_E1` | 基建(批次根基名;部署代理加时间戳后缀;一律新批次根) |
| 3 | `prediction_policy_overrides.temperature` | (未写 = null = 不发送) | `0.0` | (未写 = null) | (未写 = null) | **实验变量:E2 唯一差异** |
| 4 | `prediction_policy_overrides.max_candidates_for_ranking` | (未写 = 默认 8) | (未写 = 默认 8) | `16` | (未写 = 默认 8) | **实验变量:E3 唯一差异** |
| 5 | `prediction_policy_overrides.rank_candidate_presentation` | (未写 = 默认 v1) | (未写 = 默认 v1) | (未写 = 默认 v1) | `"v2"` | **实验变量:E1 唯一差异**(§4.4 补登记) |

未列出的一切字段(budgets / model_request_params / llm_timeout_s /
max_http_retries / rate / batch_cost_cap_cny / provider_price_snapshot /
export_policy_overrides / capacity / worker_wall_clock_cap_s /
max_worker_respawns / poll_interval_s / max_parallel / exam_inputs /
config_notes / 其余 prediction_policy_overrides 键)四配置逐字节相等。

## 2. 差异的运行侧语义(进身份什么、发什么请求)

| 开关 | 默认(C0/E3/E1) | 实验臂 | 进 run identity | 进 batch identity | 进模型请求体 |
|---|---|---|---|---|---|
| `temperature`(E2) | null → 请求体**不含** temperature 键(与 HEAD 逐字节一致) | 0.0 → 每次请求显式 `"temperature": 0.0` | 是(`prediction.policy.temperature`) | 是(`model.prediction_policy.temperature`,经 `_policy_block_for_identity`) | 是(E2 臂) |
| `max_candidates_for_ranking`(E3) | 8(rank 任务最多携带 8 张合格 recorded 卡) | 16 | 是(同上,`…max_candidates_for_ranking`) | 是(同上) | 间接(只改 rank_candidates 任务书候选数;**报告宽度 5 不动**;入围规则不变,仍只合格 recorded 卡) |
| `rank_candidate_presentation`(E1) | v1(rank 任务 = ranker.md + 平铺候选卡,任务书与 HEAD 逐字节一致) | v2 → rank 任务的候选分层四层卡(engine/source/condition/verification)+ candidate_set 集级事实 + 密度预算;提示词换 ranker_v2.md;解析契约 v2(select 须完整 order,hold 须结构化 {kind,note}) | 是(同上,`…rank_candidate_presentation`) | 是(同上;prompt SHA 另经 prompt_versions 以 `rank_candidates_v2` 键恒在身份) | 是(E1 臂 rank 调用的 system prompt 与任务书候选块;对 analogy/novel 无任何作用) |

身份冻结链:`prediction_policy_overrides` → `prediction_policy()` 合并块 →
`ModelSetup.identity_block()["policy"]`(run identity,resume 逐字段核对)
+ `build_batch_identity(..., prediction_policy_block=...)`(批次身份短哈希)。
跨配置 resume(如 E2 身份的 run 用 C0 配置恢复)在 `check_resume_identity`
的 `prediction` 块上被拒(IdentityMismatch),不静默继续。

E2 附加约束(fail-closed,装配期):远端 `.env` 模型若不支持 temperature
(已知 **kimi-k3**,API 400 `Parameter 'temperature' is not supported`,见
docs/CHENYU_ACCESS.md 坑清单),`resolve_model_setup` 直接报
"该模型不支持温度臂"并拒绝装配(结构化 `ModelNotConfigured`,
detail 带 model_id/temperature),不静默忽略。E2 发车前部署代理须确认
`V43_LLM_MODEL` 非 kimi-k3 系。

## 3. 部署回填契约(JSON 无注释,故在此登记;三份配置内 `config_notes` 同文)

| 字段 | 施工时值 | 发车前动作 | diff 纪律 |
|---|---|---|---|
| `batch_cost_cap_cny` | `null` | 部署代理按 ¥50 总预算与 PREREGISTRATION §2/§5 分摊回填(参考:单臂 ¥2–4,E2 批 ≤¥5,E3 批 ≤¥6) | 回填值若三臂不同,属**费用治理字段**,须在本文件补登记后才算合法差异 |
| `provider_price_snapshot` | `null` | 部署代理按实际 `V43_LLM_MODEL` 回填价格快照 | **三臂必须同值回填**(同模型同价);不回填 = 无费用账,批不得进判定 |
| `batch_root` | 基名 | 部署代理加时间戳后缀、新建目录 | 一律新批次根,禁跨身份 resume |
| `exam_inputs` | `workspaces/dependingv43_s1/exam/dev_questions.jsonl`(远端部署位占位) | 部署代理把冻结 dev 题卷放到该位 | 三臂同值;SHA 必须等于 8869cd05cea1a44220f3001f0b6415c6bf97eb5f0122ebc4609aa1c77ab0360c |

注意:回填会改变配置文件字节与批次身份;回填后本文件的 SHA 行(§4)须同步
补登记(追加,不覆盖施工时值)。

## 4. 施工时配置指纹(sha256;部署回填后追加新行,勿改本行)

```
configs/s1_dev_C0.json  89c9d3c94af8884aae2f71a0b69620e908876758b6276053f719275e293e9e23
configs/s1_dev_E2.json  cd16f498b5df5329be2381bf0dd57a9f2ac045d5ced5fcb92d489de8f3342a5e
configs/s1_dev_E3.json  1bf85ae46af66e7c7a717e50ca8d245e52532e24e11d1a534aae611b82214d79
```

### 4.1 部署回填后指纹(2026-09-29,跑分代理D;发车前、任何付费调用之前)

回填内容 = §3 契约的两项:`batch_cost_cap_cny`(C0=8.0 / E2=5.0 / E3=6.0,
按 PREREGISTRATION §2/§5 与跑分任务段预算 ¥22 分摊;**三臂不同属费用治理
字段,本节即为 §3 要求的补登记**)与 `provider_price_snapshot`(**三臂同值**,
自 reports/phase_d/retest/provider_price_snapshot_2026-09-29.json 抄录,当日
2026-09-29 由部署代理重取官方页核对一致:input ¥0.8/M、output ¥2.8/M、
cache read ¥0.23/M、RPM 200、TPM 3,000,000、max_in 1,048,576、max_out
131,072)。除该两字段外配置语义与其余字段与施工时值逐键相等。

```
configs/s1_dev_C0.json  b1480fa0d358362447f3c409f839ba619a49eabeb52dc86004496062a05b406c
configs/s1_dev_E2.json  7a05ea5921e5279254a81c3c9740422702df685d1074bc2717983013a459d8de
configs/s1_dev_E3.json  74cbf5eb4f4f5d20ec7581a23ea8417e1e4322f929795181614b6a430ba620b0
```

**E3 对照接力预登记(依 PREREGISTRATION §3.2,条件式,先于任何跑分登记)**:
若 E2 按预注册判 `dev_candidate`(方差显著下降),E3 发车前在其配置补
`prediction_policy_overrides.temperature=0.0`(即 E3 = E2 配置 + 窗口 16 单一
差异),对照臂 = E2 配置批(两次采样之一为基准,登记先于看 E3 分数);若 E2
`rejected`/`inconclusive`,E3 按本表原样(仅窗口差异)对 C0 配对。两种情形
的 E3 实际发车指纹在发车前追加于 §4.3。

### 4.2 基础设施修正:llm_timeout_s 300→3600(2026-09-29,三臂同值;任何判定之前)

C0 首批(runs/s1_dev_C0_20260929T175041Z,身份 f9769daf)在**进入任何判定之前**
按 §2.1 停机规则作废:56/56 合法终态、pairing gate 过,但 90 发 58 超时
(llm_timeout_s=300:usage-ok 调用中位 192s/最大 292s,紧贴 300s 墙),
**58/90 缺 usage → 费用账不完整(§1.4 不得进判定)**,且超时属 §2.1
"单批超时>10% → 修基础设施后新批次根重跑"的登记处置。修正 =
`llm_timeout_s` 300→**3600**(Phase D 登记的同款拆墙值,2026-09-29 用户
指令先例;三臂同值,diff 纪律不破坏),旧批根封存不进判定,新批根重跑。
本修正在看到任何臂间对比或分数趋势之前由超时账目触发,不改任何判定规则。

```
configs/s1_dev_C0.json  313af38b3d0fd34b4eab868998c31fbcfae9ea227706ff6e57fb53ba6ba82b18
configs/s1_dev_E2.json  8ba59742425c22939fd6bc74bd20f6a74356cec3bc372293186107bb44fb8c6f
configs/s1_dev_E3.json  6770f3c332b0a3dae8e44c7871caf54721e027b99fde4ed20381bb762064a0fe
```

### 4.3 E3 发车登记(2026-09-29 20:45Z,先于任何 E3 分数)

E2 已按 PREREGISTRATION §2.1 判 **rejected**(F_E2=6 vs F_C0=7;符号检验
不一致对 n=7 双侧 p=1.0;F_E2=6 > max(0,F_C0−3)=4 → 方差未显著减少;
次级指标全守:@5 均值 19.5=19.5、空答 +0.5、spurious 35.5<36)。**接力不
触发** → 依 §3.2,E3 直接对 C0 配对(温度行为与 C0 一致,E3 配置按本表原样,
仅窗口差异,指纹 = §4.2 的 6770f3c3…)。E3 批:`runs/s1_dev_E3_20260929T204506Z`,
身份 `f77b2991`。判定口径(发车前登记):净赢 = E3 cn@1 − C0 两样本逐样本
净赢,**须对两样本均 ≥3 才算过门(保守侧)**;回退:@5 对两样本净降取较大
侧,降 0 为底线(≤2 需逐题归因);空答 ≤1(C0 样本 1/0);spurious ≤36;
费用 ≤ 对照批 2.5× 且 ≤ ¥6。

### 4.4 E1 发车登记(2026-09-29,先于任何 E1 付费调用与分数)

- **实验差异**:`configs/s1_dev_E1.json` = s1_dev_C0.json + 唯一差异
  `prediction_policy_overrides.rank_candidate_presentation = "v2"`
  (E1_DESIGN §2;呈现/prompt/解析契约同一开关)。发车指纹:

```
configs/s1_dev_E1.json  975c6e3a8d6464ce180100a577ff1babcfcf0ebbbcaec2e9e0fb4a4523cf7d06
```

  其余字段与 C0(§4.2 指纹 313af38b…)逐字节相等,除 `arm`/`batch_root`
  (基建标识)与 `batch_cost_cap_cny=6.0`(费用治理字段,PREREG §2.3
  单批上限 ¥6);`llm_timeout_s=3600`、价格快照、并发策略与 C0 同值。
  E1 代码增量 = E1_DESIGN 的两个 diff(已 apply,prompts 新增
  ranker_v2.md,SHA 经 `rank_candidates_v2` 键进身份)+ 一处最小手工适配
  (非恒真 uniform 候选字段留逐卡层,与 E1_DESIGN §3.1 文本一致;登记于
  RUN_JOURNAL E1 节)。
- **对照(依 PREREGISTRATION §3.2,E2 非 dev_candidate → 直接对 C0 配对)**:
  C0 两次采样 `s1_dev_C0_20260929T182619Z`(C0-a)与
  `s1_dev_C0_20260929T190054Z`(C0-b),看分后不得换对照。
- **判定口径(发车前登记,照 §4.3 保守先例)**:净赢 = E1 cn@1 − C0
  逐样本净赢,须对 **C0-a 与 C0-b 两样本均 ≥3** 才算过门;回退上限:
  @5 对两样本净降 0 为底线(≤2 需逐题归因);空答率不升(>5 题空答即
  停机,E1 最大风险 = 解析变严);spurious 不升;费用 ≤ ¥6。
- **批根**:`runs/s1_dev_E1_<UTC时间戳>/`(一律新批次根;跨身份 resume
  由既有 IdentityMismatch 链路拒绝,呈现开关已入 policy 块)。
- **发车与判定回执(2026-09-30 补记)**:实际批根
  `runs/s1_dev_E1_20260930T023702Z`,批次身份 `f6a6e18b`(02:37Z 发车,
  20 worker 与三臂同值,~29 分钟完成;56/56 合法终态、pairing gate ok、
  48 发/0 缺 usage/0 孤儿,费用 ¥2.2841 ≤ ¥6)。判定 = **rejected**:
  净赢 vs C0-a +2 / vs C0-b +1(均 < 3);@5 净 0/−1(−1 在 ≤2 归因带内);
  空答 1 ≤ 1;spurious 36 = 36。机制诊断:rank 路由仅 3/56 题(三臂同分布)、
  3 题在三臂全 miss → 净赢属 novel 模式采样噪声;解析面 48/48 干净
  (0 hold、0 解析失败,完整 order 全数达成)。详见
  [ARMS_C0_E2_E3_RESULT.md](ARMS_C0_E2_E3_RESULT.md) §3b 与
  [RUN_JOURNAL.md](RUN_JOURNAL.md) §10。

## 5. 机读块(判定脚本直接消费)

```json
{
  "schema_version": "v43-s1-arm-diffs-1",
  "registered_at": "2026-09-29",
  "baseline_arm": "s1_dev_C0",
  "baseline_config": "configs/s1_dev_C0.json",
  "baseline_config_sha256": "89c9d3c94af8884aae2f71a0b69620e908876758b6276053f719275e293e9e23",
  "allowed_infra_fields": ["arm", "batch_root"],
  "deployment_fill_fields": ["batch_cost_cap_cny", "provider_price_snapshot"],
  "deployment_fill_rule": "provider_price_snapshot 必须三臂同值;batch_cost_cap_cny 按 PREREGISTRATION §2/§5 分摊并回填后在本文件补登记",
  "arms": {
    "s1_dev_E2": {
      "config": "configs/s1_dev_E2.json",
      "config_sha256": "cd16f498b5df5329be2381bf0dd57a9f2ac045d5ced5fcb92d489de8f3342a5e",
      "single_variable": "prediction_policy_overrides.temperature",
      "diffs_vs_baseline": {
        "arm": {"baseline": "s1_dev_C0", "arm": "s1_dev_E2", "class": "infra_label"},
        "batch_root": {"baseline": "s1_dev_C0", "arm": "s1_dev_E2", "class": "infra_batch_root"},
        "prediction_policy_overrides.temperature": {
          "baseline": null, "arm": 0.0, "class": "experimental",
          "identity_paths": ["prediction.policy.temperature",
                             "model.prediction_policy.temperature"],
          "request_body_effect": "每个 /chat/completions 请求显式携带 temperature=0.0;基线臂请求体不含该键",
          "fail_closed_note": "kimi-k3 系模型装配期拒绝(该模型不支持温度臂)"
        }
      },
      "predecessor": "PREREGISTRATION.md §2.1(E2 温度臂)"
    },
    "s1_dev_E3": {
      "config": "configs/s1_dev_E3.json",
      "config_sha256": "1bf85ae46af66e7c7a717e50ca8d245e52532e24e11d1a534aae611b82214d79",
      "single_variable": "prediction_policy_overrides.max_candidates_for_ranking",
      "diffs_vs_baseline": {
        "arm": {"baseline": "s1_dev_C0", "arm": "s1_dev_E3", "class": "infra_label"},
        "batch_root": {"baseline": "s1_dev_C0", "arm": "s1_dev_E3", "class": "infra_batch_root"},
        "prediction_policy_overrides.max_candidates_for_ranking": {
          "baseline": 8, "arm": 16, "class": "experimental",
          "identity_paths": ["prediction.policy.max_candidates_for_ranking",
                             "model.prediction_policy.max_candidates_for_ranking"],
          "request_body_effect": "rank_candidates 任务书候选上限 8->16(仅合格 recorded 卡入围,规则不变);报告宽度 5 不动",
          "cost_note": "候选翻倍的 token/费用增幅按 PREREGISTRATION §2.2 监控"
        }
      },
      "predecessor": "PREREGISTRATION.md §2.2(E3 窗口臂)"
    },
    "s1_dev_E1": {
      "config": "configs/s1_dev_E1.json",
      "config_sha256": "975c6e3a8d6464ce180100a577ff1babcfcf0ebbbcaec2e9e0fb4a4523cf7d06",
      "single_variable": "prediction_policy_overrides.rank_candidate_presentation",
      "diffs_vs_baseline": {
        "arm": {"baseline": "s1_dev_C0", "arm": "s1_dev_E1", "class": "infra_label"},
        "batch_root": {"baseline": "s1_dev_C0", "arm": "s1_dev_E1", "class": "infra_batch_root"},
        "batch_cost_cap_cny": {"baseline": 8.0, "arm": 6.0, "class": "cost_governance"},
        "prediction_policy_overrides.rank_candidate_presentation": {
          "baseline": "v1", "arm": "v2", "class": "experimental",
          "identity_paths": ["prediction.policy.rank_candidate_presentation",
                             "model.prediction_policy.rank_candidate_presentation"],
          "request_body_effect": "仅 rank_candidates 任务:候选分层四层卡 + candidate_set 集级事实 + 密度预算(1600/卡,300/full SMILES);system prompt 换 ranker_v2.md;解析契约 v2(select 须任务书全部候选完整 order,hold 须结构化 {kind∈枚举,note});v1 臂任务书与请求体逐字节不变",
          "fail_closed_note": "值域 {v1,v2} 装配期 fail-closed;v2 解析失败走既有有界重试(1+max_parse_retries=3)",
          "registered_in": "§4.4(2026-09-29,E1 发车前)"
        }
      },
      "predecessor": "PREREGISTRATION.md §2.3(E1 协议臂)"
    }
  }
}
```

## 6. 判定脚本用法约定

任何跑分判定前的身份核对:取两臂 `batch_identity.json`,按 §5 的
`diffs_vs_baseline` 逐字段比对 `identity.config`(及
`identity.model.prediction_policy`);差异字段集合 ⊄ 本文件所列 =
预注册破坏,判定终止。E2 臂另须核对每条 `prediction_call.aN` 产物带
`"temperature": 0.0`(温度臂实际发送的逐调用留痕;基线/E3 臂该键不存在)。
