# E1_DESIGN — rank_candidates 选择协议修复臂(HIT60 S1 E1)

- 设计代理:E1 设计代理 E;登记时间 2026-09-29;**只设计不实施**:本目录
  两个 diff(`ranker.diff`、`prediction_task.diff`)不 apply 到 src,留待
  跑分代理在发车前实施(实施后须按 PREREGISTRATION §8 把 diff 补进批次登记)。
- 上游依据:[PREREGISTRATION.md](../PREREGISTRATION.md) §2.3(E1 预注册)、
  §0 红线(I1/I2/I4)、§4 采用判据;[pool_summary.md](../../phase_s0_hit60/pool_summary.md)
  (池级结论,S0 边界表);teacher 指导书 §4 S1 E1 三抓手(候选呈现 /
  证据卡密度 / 放弃理由约束)。
- 已在临时副本上通过:py_compile、v2 载荷形状冒烟、v2 解析器 fail-closed
  冒烟、v1 路径字节不变对照、`git apply --check`(对当前工作树副本)。

## 0. I1 合规声明

本文只用 pool_summary.md 的**池级**事实:L1 排序池 50 题(金标已在最终
答卷 2–5 位;novel 27 / rank 23;其中引擎也排 2–5 的 27 题、引擎 Top-10
没有的 15 题里 7 题是模型自生成金标排后位)、L2 的 rank 子池 13 题(有含
金标的合格 recorded 候选、模型选了别的卡)、多维监控要求(@3/@5 不牺牲、
空答率/spurious 率不升)。不引用任何 qid、分子、逐题答案,或从 298 逐题
表推出的规则。放弃理由枚举的维度取自任务书自身呈现的四层信号(来源/
条件/验证/引擎),与题目无关、与题库无关。

## 1. 设计动机(逐条挂池级事实)

| # | 机制 | 挂到的池级事实 |
|---|---|---|
| M1 | **候选分层呈现**(engine/source/condition/verification 四层 + 决策字段白名单重组) | L2 rank 子池 13 题 = 含金标的合格 recorded 候选**在卡间比输了**。现状候选卡是平铺字段:与裁决强相关的信号(文献行数 `n_evidence`、行级过滤标记、full SMILES、验证红标)不在任务书里,而每卡重复的 64 位资产 SHA / 恒真字段(kind/match_type/mapping_status/donor_refs)反而在 —— 模型看到的"差异"多数是噪声,真差异看不见。 |
| M2 | **完整 order 契约**(select 必须给任务书全部候选的排列;漏卡 = 解析失败) | L1 排序池 50 题 = 金标已在答卷 2–5 位(排序不优)。答卷 2–5 位由模型 `order` 尾部直接决定(adjudicate_parent:order 内的卡才被背书进报告);现状 order 可省略、可部分,漏卡 = 静默不背书,位次事实上回退为引擎序回声。强制显式排满,把"尾部位次"从隐式变成模型必须做的决定。 |
| M3 | **结构化放弃理由**(hold 必须给 `hold={kind∈枚举, note}`;fail-closed;诚实弃权不惩罚) | 多维监控红线(空答率不升)+ teacher §4 三抓手之三。现状 hold 只要自由文本,弃权不可归因;结构化后 hold 按 kind 聚合 = 机制读出(哪一层信号不足),且把"被迫选卡"与"诚实弃权"在协议层分开。 |
| M4 | **有界证据卡密度**(密度预算 + 确定性截断留痕) | 支撑 M1:密度提升的目标是**卡间可区分性**,不是堆料。同时把 M1 的 token 增幅钉在硬上限内(PREREGISTRATION §2.3 费用上限 ¥6/批)。 |

E1 只动 rank_candidates 协议;L1 的 novel 27 题走 novel_proposal 协议
(该模式任务书 candidates=[] 为既有事实),**不在本臂机制内**(见负面清单
N8),本臂的直接杠杆对象是 L1-rank 23 + L2-rank 13 的机制类型。

## 2. 改动清单(文件:函数)

补丁 = `ranker.diff`(新增 `configs/prompts/ranker_v2.md`,新文件全文)
+ `prediction_task.diff`(4 个文件,unified diff,基于当前工作树——已含
agentC 的 E2/E3 开关,`git apply --check` 通过)。

| 文件:函数 | 改动 |
|---|---|
| `src/pathway_v43/domain/policy.py`:`PREDICTION_POLICY_DEFAULTS` / 新 `_normalize_rank_presentation` / `prediction_policy` | 新增开关 `rank_candidate_presentation`,默认 `"v1"`(C0/E2/E3 请求体逐字节不变);值域 {v1,v2} 装配期 fail-closed;随 policy 块进 run/batch identity(跨配置 resume 拒绝,同 E2/E3 开关链路)。**不 bump PREDICTION_POLICY_VERSION**(沿用 agentC 加开关不动版本号的先例;身份差异由 policy 块携带)。 |
| `src/pathway_v43/adapters/llm_client.py`:`prompt_versions` | 新增常驻键 `"rank_candidates_v2" → ranker_v2.md` 的 SHA256。两版 prompt 的 SHA 恒在身份里;**prompt SHA 自动进身份**:该 dict 经 `ModelSetup.identity_block()` 进 run identity、经 `content_hash(prompt_versions)` 进 `prediction_task_id`、经 `build_batch_identity` 的 policy/prompt 链进批次身份(既有链路,零新代码)。 |
| `src/pathway_v43/services/prediction.py`:新 `_rank_v2_candidate_card` / `_apply_density_cap` / `_rank_v2_candidate_set` / `_apply_rank_presentation_v2`;`build_prediction_task`(尾部挂钩);`parse_model_response`(v2 契约);`ParsedPrediction`(+`hold_kind`/`hold_note`) | 见 §3 三抓手与 §5 解析契约。v1 路径零改动(挂钩不触发;v1 解析分支逐字节等价,已冒烟对照)。 |
| `src/pathway_v43/workflow/nodes.py`:`call_model` / `_prompt_for` | 按 policy 开关选 ranker_v2.md(v2 时)并把 `rank_presentation` 传给解析器;prompt 选择与解析契约**同一开关**,不可能错配。 |
| `configs/prompts/ranker_v2.md`(新) | 协议 v2 提示词全文(候选集事实、四层信号说明、去锚定声明、order/hold 契约、诚实弃权条款、铁律不变)。 |

发车侧(不由本补丁携带,登记于此):E1 臂配置 = 复制
`configs/s1_dev_C0.json` → `s1_dev_E1.json`,唯一差异
`prediction_policy_overrides.rank_candidate_presentation = "v2"`;
ARM_CONFIG_DIFFS.md §1 差异表届时由跑分代理补一行(与 E2/E3 同格式)。

## 3. 三抓手怎么落

### 3.1 候选呈现结构(v2 卡:四层 + 集级事实上提)

v2 任务书(v2 任务 schema 升 `v43-prediction-task-4`;v1 任务保持
`v43-prediction-task-3` 逐字节不变):

```json
"candidates": [
  {
    "evidence_id": "E…",
    "engine":       {"reference_rank": 3, "score": 0.71, "score_semantics": "eawag_lookup_tanimoto"},
    "source":       {"source_id": "BT…#r…", "n_evidence": 4},
    "condition":    "unknown",
    "verification": {
      "products": [
        {"position": 0, "product_smiles": "…", "product_smiles_full": "…",
         "product_identity": "cn…", "parse_ok": true, "identity_match": true,
         "in_path_cycle": true, "ion_filtered": false, "cofactor_filtered": true}
      ],
      "all_products_parse_ok": true, "all_identity_match": true, "any_in_path_cycle": false
    },
    "density": {"per_candidate_char_cap": 1600, "truncated": []}
  }
],
"candidate_set": {
  "presentation": "v2", "n_candidates": 8, "selection_rule": "eligible_recorded_only",
  "uniform_facts":  {"kind": "recorded_reaction", "match_type": "exact_donor_cn_match",
                     "mapping_status": "unavailable", "donor_refs": []},
  "provenance":     {"recorded": {"asset_file": "…", "asset_sha256": "…"}},
  "answer_semantics": {"answer_width": 5, "within_card_product_order": "fixed_by_position",
                       "selected_card_products_fill_answer": "in_card_position_order"},
  "density_budget": {"per_candidate_char_cap": 1600, "product_smiles_full_char_cap": 300,
                     "drop_order": […], "truncated": […]}
}
```

- **字段白名单只用运行时已有字段**:上表全部来自检索证据卡(`retrieval_rank`
  `score` `score_semantics` `source_id` `source_record.n_evidence`、产物行
  `product_smiles` `product_smiles_full` `product_identity` `ion_filtered`
  `cofactor_filtered`)与祖先链。`verification` 是**确定性预览**:用与裁决层
  逐卡验证同源同函数(`gate_smiles` / `cn_identity` / `is_in_path_cycle`)
  对已在卡上的数据重算,不引入任何需要回查金标的信息;仅呈现、不门禁
  (门禁语义原封不动在裁决层,红标产物仍由裁决层拒)。
- **恒真字段上提**:kind/match_type/mapping_status/donor_refs 由入围资格
  保证恒真(组装时点逐字段核对,不恒真不上提),连同每卡重复的资产
  SHA/path(≈110 字符/卡,零区分度)上提 `candidate_set` 单份 —— 去掉的
  都是"假差异",省出的预算给真差异(见 3.2)。
- **去锚定**:`engine.reference_rank` 显式改名并声明"引擎参照位次,不是
  裁决结论";`answer_semantics` 把(不可变的)答卷语义告诉模型:选中卡
  产物按卡内 position 顺序占答卷前几位、宽度上限 —— 模型第一次能把自己
  的 order 决策与最终答卷位次对上。
- 模型无关:呈现只重排/上提/预览既有 JSON 字段,任何模型同一任务书
  直接复用(E4 换模型时协议零改动)。

### 3.2 证据卡密度(有界)

- **硬上限**(常量、版本化,进 `candidate_set.density_budget` 让模型与
  审计都知道):单条 full SMILES ≤300 字符;单卡序列化 ≤1600 字符
  (不含 density 留痕块)。现状合格 recorded 卡实测约 600–800 字符/卡
  (runs/v43-predict-smoke 实测),上限留约 2× 余量,正常路径不触发;
  E3 窗口 16 时同一规则适用(规则与窗口无关)。
- **截断规则(确定性、可重放)**:超预算按固定降级次序裁
  `DENSITY_DROP_ORDER = ①逐产物过滤标记 → ②full SMILES(保留短形+规范
  身份)→ ③n_evidence`;`evidence_id`/`engine`/`condition`/
  `verification` 聚合与 `product_identity` **永不裁** —— 卡间可区分性
  不因预算受损。每次截断逐项记入 `density.truncated` 与
  `candidate_set.density_budget.truncated`;prompt 明示"被裁 ≠ 不存在",
  不得把裁剪当缺失证据引用。
- 密度是**换仓**不是堆料:删每卡重复 SHA/恒真字段(≈200 字符/卡),加
  full SMILES、验证预览、行级标记(净增约 150–350 字符/卡,见 §4)。

### 3.3 放弃理由约束(结构化 + fail-closed + 不惩罚)

- 输出契约:decision=hold 时必须给
  `hold={"kind": <枚举>, "note": <说明>}`;枚举(代码 `HOLD_KINDS` 单一
  事实源,prompt 镜像,测试锁一致):`condition_conflict` /
  `direction_or_substrate_doubt` / `product_validity_doubt` /
  `insufficient_discrimination` / `engine_rank_disagreement` / `other`
  (`other` 时 note 必填)。维度 = v2 呈现的四层信号 + 密度充分性 + 兜底,
  无逐题语义(I1)。
- **解析 fail-closed**(仅 v2):缺 hold 块 / kind 不在枚举 / other 无
  note / hold 携带 order → `error_kind=hold_reason_invalid|order_with_hold`
  → 走既有有界重试(1+max_parse_retries=3 次)。note 超 500 字符确定性
  截断,不因长度失败。
- **诚实弃权不被惩罚**:hold 的下游处置一字不改(nodes.py 既有分支:
  path 停 awaiting_prediction、reason 记录),不设任何"hold 计数惩罚"、
  不把 hold 改写为被迫选卡;`ParsedPrediction.hold_kind/hold_note` 随
  parsed dict 自动落 prediction.json 产物,供批后按 kind 聚合读出。
  空答率不升由 §6 判定标准守住(见风险 R1)。

### 3.4 完整 order 契约(M2,v2 解析侧)

select 时 `order` 必须是任务书**全部候选各出现一次**的排列(缺 →
`order_missing`/`order_incomplete`,fail-closed 重试);既有的
unknown-id / 重复 / 选中卡必在首位契约不变;hold 时不得携带 order。
理由:裁决层的背书规则(order 内的卡才进报告)意味着部分 order = 静默
弃权 —— 要弃就显式 hold(3.3),这是 3.3 与 M2 成一对的原因。**裁决层
零改动**:完整 order 本就是 adjudicate_parent 既有输入的合法超集。

## 4. token 预算(估计口径 + 硬账)

- 现状实测(v43-predict-smoke,8 候选,rank 任务):任务书 11,091 字符,
  其中候选块 9,614 字符;单卡 598–836 字符(该样本为旧 schema 混入规则
  卡;现行合格-recorded-only 口径更小)。
- v2 逐卡变化:−asset_sources/恒真字段(≈−200) + full SMILES/验证预览/
  行级标记/density 块(≈+150–350)→ 净 +150–350 字符/卡;候选块净
  +1.2–2.8k 字符;candidate_set ≈ +500 字符。**用户载荷净增 ≈ +8–20%**。
- 系统提示词:ranker.md 1,078 字符 → ranker_v2.md ≈2,300 字符,
  +1.2k 字符(中文为主,约 +0.8–1.2k tokens/次调用)。
- 输出增项:完整 order 尾部 + reasons 结构化 ≈ +0.4–0.8k 字符/次;
  hold 块仅在 hold 时发生。
- **合计:rank 路由题的 rank 调用 input +≈0.6–1.3k tokens、output
  +≈0.1–0.3k;每题 ≤3 次 LLM 调用中只占 1 次 → 每题整体 +5–15%**。
  以 C0 单臂 ¥2–4 为基数,E1 单批预计 ¥3–5,PREREGISTRATION §2.3 上限
  ¥6 内有余量;每批 usage 全记账,超上限停机(§2.1 停机规则沿用)。

## 5. 配套测试计划(实施代理执行;全部离线零 API)

1. **payload 形状**(test_prediction_task.py 增):
   - v2 开:task schema=v4、candidates 为四层卡、candidate_set 存在;
     uniform_facts 只在跨候选恒真时上提(构造一张 condition_fit 不同的卡
     → condition 留逐卡层);provenance 去重单份;
   - **v1 关(黄金测试)**:开关缺省/显式 v1 时 `task_user_payload(task)`
     与打补丁前 HEAD 输出逐字节相等(冻结期望 JSON);
   - policy 开关:v2 override 生效;非法值(v3/null/数字)装配期 ValueError;
     开关进 `ModelSetup.identity_block()["policy"]`。
2. **解析器 fail-closed**(test_prediction_task.py 增,已冒烟通过的同款
   用例):select 无 order→`order_missing`;漏一卡→`order_incomplete`;
   hold 缺块/坏枚举/other 无 note→`hold_reason_invalid`;hold 带 order→
   `order_with_hold`;合法 hold(kind=insufficient_discrimination,超长
   note)通过且 note 截 500;reasons 字符串旧形规约为 {verdict:"",note}
   不失败;**v1 回归:全部既有 parse 测试不改一行通过**(order 可省略、
   hold 自由文本)。
3. **密度截断**(新):>300 字符 full SMILES → 丢字段+留痕;构造超 1600
   字符卡 → 按 DENSITY_DROP_ORDER 逐级裁、never-drop 字段存活、
   density.truncated 完整;同输入重放同输出(确定性)。
4. **枚举/提示词一致性**(新):ranker_v2.md 含 HOLD_KINDS 每个值与
   order 契约文本;`prompt_versions()` 返回 4 键(含 rank_candidates_v2);
   `_prompt_for(v2)` 装载 ranker_v2.md、v1/analogy/novel 不变。
5. **端到端**(test_prediction_workflow.py 增):ScriptedFinder+假 client
   走 v2 rank → 调用产物 `system_prompt_sha256` = ranker_v2.md 的 SHA、
   prediction.json 含 hold_kind(造一次合法 hold)、
   adjudicate_parent 消费完整 order 全绿(裁决层零改动的行为证明)。

## 6. 判定标准引用(全部继承 PREREGISTRATION,不改一字)

- 主终点:dev cn@1 净赢 vs 登记对照 ≥3 题(§2.3/§4);辅报 L1 型敏感
  读出(金标在候选 2–5 位的题内位次提升)仅机制印证不作判据。
- 回退上限(§2.3):cn@5 不降;空答率不升;spurious 率不升;费用 ≤¥6/批。
- 结论三态与止损门(§4):dev_candidate / rejected / inconclusive;
  累计 <+8pp 停止冲刺。小样本纪律:56 题逐题四格 + 不确定性一起报。
- 配对结构(§3):E1 对照在发车前登记(E2 落地则对 E2 配置批,否则 C0),
  看分后不得换对照;与 E3 不叠加(单变量成臂)。

## 7. 风险与回退

| # | 风险 | 缓解 |
|---|---|---|
| R1(**最大**) | 完整 order + hold 枚举的解析严格度抬高解析失败率;重试耗尽(≤3 次)→ prediction failed → 空答率上升,击穿监控红线 | 严格度只加在两个有界小字段(order/hold),不动大字段 reasons;失败走既有有界重试且任务书不变(重试只是再采样);批后按 error_kind 聚合,`order_*`/`hold_*` 占比异常即归因上报;**回退 = 配置开关改回 v1(一行,不改代码),批次重跑新根**。 |
| R2 | 完整 order 让答卷尾部更长,非金标卡挤占宽度 → cn@5/spurious 恶化 | 同一 order 也让金标卡必进背文集;由 §6 回退上限直接判定,击穿即 rejected,不带病采用。 |
| R3 | 密度截断规则在极端卡(多产物超长 SMILES)上裁掉区分度 | never-drop 清单保住决策字段;截断全留痕可审计;上限留 2× 余量,正常路径不触发。 |
| R4 | prompt 枚举与代码 HOLD_KINDS 漂移 | 单一事实源在代码,测试 #4 锁一致;prompt 内容变更 = SHA 变更 = 新身份,不可能静默混批。 |
| R5 | v2 呈现引入的验证预览与裁决层判据出现第二事实源 | 预览直接 import 裁决层同函数(gate_smiles/cn_identity/is_in_path_cycle);预览仅呈现不门禁,裁决层复验照旧;测试 #5 端到端证明裁决输出不因预览改变。 |

回退路径(全部一行配置,不动代码):E1 批任何红线击穿 → 弃用该批结论,
开关回 v1;v1 行为已被黄金测试钉死与 HEAD 逐字节一致。

## 8. 负面清单(不做什么)

- **N1 不动窗口**:`max_candidates_for_ranking` 缺省 8 不碰(E3 臂的 16
  与本臂不叠加;单变量成臂)。v2 呈现对 8/16 同一规则。
- **N2 不动裁决层**:`adjudicate_parent` / tie-break / 后备键
  `(retrieval_rank, evidence_id, position)` / 去重 / 报告宽度 5 / 逐卡
  验证门禁,一行不改;验证预览只是呈现,不放宽不收紧任何门禁。
- **N3 不动模型与传输**:模型选择、temperature(E2 开关)、重试上限、
  request body 结构不动;E4 换模型时本协议原样复用。
- **N4 不做首位重排类手段**:不改 selected 卡产物的卡内位次语义
  (answer_semantics 只是"告知"既有语义,不是新排序权);
  PREREGISTRATION §2.3 对首位重排的 @5/多重集合约束自然满足。
- **N5 不用任何 298 逐题信息**:无 qid/分子/答案;枚举与呈现维度全部
  来自协议自身的信息层(I1)。
- **N6 不动 hold 下游语义**:不惩罚、不改写、不强制选卡;空答率红线靠
  判定标准守,不靠协议逼模型选卡。
- **N7 不改金标接触面**:任务组装仍只读运行时素材;金标只在独立评分
  进程读取(PREREGISTRATION §0)。
- **N8 不动 novel/analogy 协议**:novel 任务 candidates=[] 是既有事实,
  本臂不往 novel 任务书里加证据卡(那是另一机制、另一臂的预注册);
  analogy_edit 编辑协议不动。
- **N9 不实施、不部署、不跑分、零 LLM 调用**:本目录只有设计 + diff
  草案;apply 由跑分代理发车前执行并按 §8 补登记。
