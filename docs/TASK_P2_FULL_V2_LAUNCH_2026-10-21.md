# 任务书 — P2 完整证据卡 v2 发车物（298 post-hoc，2026-10-21，草案）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本批全部数字只在该题域内成立，
> 与 dev 双向不外推。
>
> **文档状态：DRAFT_NOT_EXECUTABLE。** 本文件是发车任务书草案，**不是发车指令**。
> 执行前必须同时满足：①T-I 完整有效且模型已按 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md`
> §3.1 选定；②P2 预注册已签字并回填四文书 SHA；③v2 化学复审已取得且**条件闭合**
> （当前 PASS_WITH_CONDITIONS，P1–P7 未闭合）；④`v1card` 模式与 P2 操作链已实现并复审；
> ⑤CC/代决已落字付费/HPC 授权；
> ⑥§0 发车前清单全绿。**缺一不发。**
>
> **性质：证据呈现整包实验，不是纯重排因果。** 两臂同模型、同池/检索输入、同判据/配置/
> 预算语义、同 v2 prompt；唯一变量=证据卡版本（A=v1 卡，B=完整 v2 卡）。模型提案与排名
> 都可能改变；不识别单字段贡献。
>
> 上游：`docs/T_P2_PREREG_FULL_V2_2026-10-21.md`、`docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`、
> `docs/P2_TOKEN_REVISION_QWEN_DECISION_2026-10-21.md`（qwen 建议 C，CC 已否决）、
> `docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md`（M1–M3 修正与四选择依据）、
> `docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md`、
> `docs/T_P2_TOKEN_PREMEASURE_298_2026-10-21.md`、
> `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md`、
> `docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md`、
> `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` §4 P2、
> `docs/T_I_PREREG_2026-10-20.md`、`docs/TASK_T_I_LAUNCH_2026-10-20.md`。
>
> **本文件不执行任何动作：** 不连 HPC、不提交 sbatch、不调用模型、不跑付费批、不改代码、
> 不读金标/题面/reference_graphs/env/key、不 push。

## 0. 一句话与发车前清单

一次批跑两臂：A=`v1-card`（v2 prompt + v1 证据卡）、B=`v2-card`（v2 prompt + 完整 v2 证据卡）；
同 298 题卷、同模型、同池、同 profile/gate/超时/重试；判分 v2 headline + v1 敏感性；
预算模式 no-cap（CC 2026-10-21），无金额停点，usage 照记、金额 unknown；
token 只披露、不设门；strict 净失 ≤−3 为科学停点。

> **token 决定（2026-10-21）：** qwen3.8max 代 Codex 建议 C uniform 13% 截断
> （`docs/P2_TOKEN_REVISION_QWEN_DECISION_2026-10-21.md`），但 CC 直接否决 C：
> **完整 v2、不截断、无帽表、schema 仍为 3**；token 只披露（+8.2165%/104/298/+64.13%），
> 不设门。本任务书不包含 C 的 schema-4/descr-4、`evidence_truncation`、帽表或截断步骤；
> 不得写“token 门已过”。

发车前清单（全绿才可发）：

| # | 检查 | 判定 |
|---|---|---|
| 1 | T-I 有效性与模型 | T-I 最终有效批结果报告落盘；按预注册 §3.1 选定模型；T-I 无效 ⇒ 不发 |
| 2 | P2 预注册 | `approval_status=preregistration_confirmed`；四文书 SHA 相符；`no_cap_ack=true` |
| 3 | 付费/HPC 授权 | CC/代决落字：预注册定稿 + 付费/HPC 指令 + no-cap；来源链记录 |
| 4 | v2 化学复审 | **未放行**：Stage B 独立复审为 **PASS_WITH_CONDITIONS**（`T_P2_V2_CHEM_REVIEW_2026-10-21.md` §2 P1–P7 未闭合）；须独立复审/条件闭合；R4 不能充抵（§0.3） |
| 5 | `v1card` 模式 | **`arm_a_definition=v1card`（M2 设计修正/新增，provenance 见 §0.1）**；已实现、测试全绿、复审通过；A 载荷与 v1 B 逐字节等价；off 零漂移 |
| 6 | P2 操作链 | `p2_operations.py`/`p2_run_wrapper.py`/`sbatch_p2_*` 已交付、合成正负控通过、复审通过 |
| 7 | 脚本锁 | `docs/T_P2_SCRIPT_LOCK_<date>.json` 逐文件 SHA 与部署树一致 |
| 8 | 代码身份 | P2 树代码聚合身份实测登记；两臂同值；不沿用 T-I 的旧聚合 |
| 9 | RDKit | 部署环境实际 RDKit 版本登记；v2 确定性锚在该版本下复跑通过 |
| 10 | 题卷/env | 298 行题卷 SHA 实核；模型 env 在位、权限 600、模型 ID 与配置一致 |
| 11 | 批根 | 两个 P2 批根不存在或为空；旧批（T-H/chain13/chain14/T-I）只读 |
| 12 | 站点 | C8 G1–G4 soak + 官方 netcheck 在新窗全绿 |
| 13 | 披露件 | 同 prompt A/B token 披露件、分族 `p2_family_f2raw.json`（F2raw+规则，发车前冻结）、`p2_face_measure` 已生成 |
| 14 | 监控 | 单协调者 flock；monitor 15 分钟巡检；stop/halt/scancel 路径明确 |

### 0.1 A 臂定义与 provenance（M2 落字）

**`arm_a_definition = v1card`**：A 臂 = v2 prompt + v1 证据卡（`candidate-evidence-2` /
`candidate-evidence-descr-2`，默认 JSON 分隔符），即 §3.3 的最小实现合同、预注册 §2.3/§2.5。

- **这是相对冻结设计的设计修正/新增，不是“回到冻结设计原意”。** 冻结设计
  `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1 原文的 A 臂是
  「用户 JSON 字节兼容回退」（r2 实现为 v2 prompt + 无证据）；该原文保留为历史对照，
  **不适用于本批 A**。
- **provenance：`qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）`。**
  该确认不是 CC 本人签字、不替代 CC 拍板，也不替代 Codex 正链最终裁定权；CC 签字文本
  必须显式落 `arm_a_definition = v1card`（设计修正/新增）。
- 归档的 CC 决定 `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md` 原文不含“A=v1 卡”字样；
  本口径由 qwen 代确认补链，**不伪填 CC 本人**。
- `v1card` 当前未实现；未按 §3.3 实现并复审前，A 臂不是 v1 卡，不得签字/发车。

### 0.2 四个工程选择（qwen 2026-10-21 确认，已落字）

| # | 选择 | 落字结论 | 本任务书锚点 | 预注册锚点 |
|---|---|---|---|---|
| 1 | A 臂 | **`arm_a_definition = v1card`**（v2 prompt + v1 卡） | §0.1、§3.3 | §0.1、§2.3、§2.5 |
| 2 | prompt | **两臂共用 v2 prompt + 披露 prompt-卡语义不匹配**；不分臂 prompt | §2 冻结面 | §2.1、§2.5、§10.3 |
| 3 | 操作入口 | **克隆 `p2_operations.py`，不改 `ti_operations.py`** | §4.1–4.3 | §3.3、§7.4 |
| 4 | build | **seed build + 字节级复制**（默认） | §5.1–5.2 | §7.4 |

- 选择 1 附 provenance 条件（§0.1）；选择 2 的严格中性共享 prompt 出口保留但不默认采用；
  选择 3 的差异只限 §4.2 diff 白名单、阈值/fatal/恢复/barrier/monitor/stop/seal/评分逐字
  继承；选择 4 只复制 build 产物，**不复制** `orchestration.json`/`gate/`/cases/状态文件，
  **禁止一臂 seed、一臂独立 build**，复制后 §5.2 身份门 1–8 全跑。

### 0.3 化学复审状态（PASS_WITH_CONDITIONS；不是已通过）

两条复审线**不得互相充抵**：

| 复审线 | 文档 | 状态 | 未闭合条件/限度 |
|---|---|---|---|
| **R4：P0b/D-6 规则级化学评审** | `docs/T_H_P0B_D6_CHEM_REVIEW_2026-10-21.md`（qwen3.8max 代 Codex；SHA-256 `fba74ea6fe11cdb4efa45e2193f90d3b914b2d20f83aeff1a5f9e5d675416b62`） | **PASS_WITH_CONDITIONS**（CC 2026-10-21 纠正；原文“规则级语义可接受（可冻结）”，**不改写成 PASS**） | C1 `stereo_only` 粒度解释（立体粒度/注记差，不得读作已证构型错误）；C2 `isomeric_unspecified` 桶必含同位素/CX 扩展差；C3 空参与物不读 `participant_list_status=partial`；C4 互变/质子化未归一写入 `does_not_prove`；另 **58/146 化学真伪 unknown**，需真实结构复核 |
| **P2 v2 证据卡化学复审**（mimo 场景 1 口径） | `docs/T_P2_V2_CHEM_REVIEW_2026-10-21.md`（Stage B 独立复审，代位 mimo 场景 1；**非 mimo 原始回应**；SHA-256 `537047cc3abaf65124b50998fa6bf602755780fad97a17bc5fa9e55881d96b8a`） | **PASS_WITH_CONDITIONS / 未放行**（§2 P1–P7 未闭合；不构成化学放行） | P1 碳酸盐/氨基甲酸酯不得计羧酸；P2 硫代酰胺/脒/胍/硫脲不得计胺；P3 定义 `n_hits`；P4 未列出的类≠不存在；P5 formula/C_ox delta 非配平净反应；P6 O–O/高价卤素 C_ox unknown 或正确；P7 开放壳层 C_ox unknown 或正确处理 |

- **R4 不能充抵 P2 v2 证据卡化学复审**；P2 侧仍需独立的 v2 化学复审/条件闭合；
- **不得把 `PASS_WITH_CONDITIONS` 写成 `PASS`/“化学已过”**，也不改 qwen 的 FAIL/条件事实；
- P2 付费批维持 **NO-GO**；§12 十项前置（含 v2 化学复审闭合）全部闭合前不发车；
- D-2 离线实施书不得把化学复审写成“已过”而自动放行；先闭合上述条件。

## 1. 批根、两臂命名与记录

| 项 | 值 |
|---|---|
| 站点 | 乌镇 wuzh02，分区 `wzhcnormal` |
| SSH | `ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com`；`KEY` 在 `/Volumes/CC/Enzyme_Agent/`，权限 600 |
| 代码树 | **`~/EnzymeAgent/v43cP2`（新树；不得复用 T-I 的 `v43cTH`）** |
| Python | `~/ppv1_hpc/venv_v44run/bin/python`（实际 RDKit 版本以部署树实测登记） |
| 题卷 | `~/ppv1_hpc/questions.jsonl`（298 行；SHA 发车日实核） |
| env 目录 | `~/ppv1_hpc/env/`；两臂**同一个** env 文件（模型相同；不打印内容） |
| 两臂批根 | `~/ppv1_hpc/batch/p2_298_<YYYYMMDD>_v1card` / `..._v2card` |
| 两臂运行根 | `~/ppv1_hpc/runs/p2_298_<YYYYMMDD>_v1card` / `..._v2card` |
| 操作状态 | `~/ppv1_hpc/operations/p2_298_<YYYYMMDD>_v1card.json` / `..._v2card.json` |
| 批准记录 | `~/ppv1_hpc/operations/p2_approved_record_<YYYYMMDD>/` |
| 协调目录 | `~/ppv1_hpc/operations/p2_coordination_p2-298-<YYYYMMDD>/` |
| 本地镜像 | `reports/ppv1_s5b/p2_<YYYY-MM-DD>/{v1card,v2card}/`（gitignored；只拉指标/身份件） |
| 封存标记 | 批根 `p2_sealed.json`（`mutable()` 识别；chmod 555/444） |

**命名规则：**

- 展示名：`v1-card` / `v2-card`；文件系统/配置臂名：`v1card` / `v2card`（无连字符，避免
  shell/路径歧义）；
- `batch_tag = p2-298-<YYYYMMDD>`，**两臂同值**（build 身份指纹门需要）；发车日一次写死，
  批中不改；
- job 前缀：`p2-v1card` / `p2-v2card`；job 名 `p2-{arm}-{phase}`；
- 两臂批名/运行根/状态文件/协调目录全部按臂隔离；**不得共用 runs 根**。

> 命名冲突提示：本文件的“P2”指**证据卡 v2 实验**；`p2_face_measure.json` 是 T-H 延续的
> **输入形态探针**（池/remap 计数），不是本实验的 treatment。两者不得混写。

## 2. 冻结面（两臂同值；唯一差异=证据卡版本）

| 项 | 值 |
|---|---|
| 模型 | **TBD（T-I 规则选定后写死）**；两臂同一模型 ID、同一 env 文件、同一请求参数 |
| 唯一差异 | `evidence_card_version`：A=`v1card`，B=`v2`；以及对应证据载荷/schema/descriptor |
| 题卷 | 298 行；SHA 发车日实核并登记 |
| 代码 commit | **`11aeeafded1b41185f24de49767933709aad49db` + P2 patch 组合**（见 §3） |
| prompt | 两臂共用 `PROPOSALS_PROMPT_VERSION_V2`（SHA 登记；不得一臂用 v1 prompt） |
| 证据卡 | A：`candidate-evidence-2` / `descr-2`；B：`candidate-evidence-3` / `descr-3` |
| 编译/池/来源/归一/路由/检索/排序 | `s5b-compiler-6` / `s5b-pool-policy-9` / `s5b-recorded-source-4` / `record-side-formnorm-1` / `s5b-analog-route-f1f4-1` / `s5b-corpus-retrieval-6` / `s5b-rank-policy-2`（零改动） |
| 判分 | v2 headline + v1 敏感性；v3 纯披露默认关；零 LLM |
| profile_policy | `max_real_model_requests=3`；`max_format_feedback_rounds=2`；其余沿 `CHAIN13_PROFILE` |
| gate | RPM 200 / TPM 3,000,000 / max_calls 4,470；每臂独立 |
| workers | 8 / max_in_flight 8 |
| 超时/重试 | 3600s/调用，timeout 不重试；传输失败自动重试 1 次；429 有界退避 |
| 温度 / 最大 token | 都不发 temperature；都不发 `max_tokens`（no-cap 语义；两臂一致） |
| 金额帽 | 无（`no_monetary_cap_user_decision`，2026-10-21）；gate/速率/并发守卫照旧 |
| token 门 | **无**（CC 2026-10-21 豁免；完整 v2、不截断、无帽表；qwen 的 FAIL 事实保留为披露，不改写成 PASS） |
| 数据面/分母 | `real`；298 固定；失败/空池/弃权不剔题 |

## 3. 代码基线、补丁与部署

### 3.1 基线

- 基线 commit：`11aeeafded1b41185f24de49767933709aad49db`（主树 P0b 已合并、诊断块默认关闭；
  P2 不消费/不修改 P0b）。
- 禁止直接改主树 `dependingv43` 的 `src/`/`tests/`；所有 P2 代码在独立 worktree/部署树完成。
- **部署树必须是新树 `~/EnzymeAgent/v43cP2`**：T-I 的 `v43cTH` 绑定 T-I 的代码身份/脚本锁，
  在里面打 P2 补丁会破坏 T-I 的冻结身份与待续跑。

### 3.2 补丁清单（发车前全部要落 SHA）

| # | 件 | 内容 | 状态 |
|---|---|---|---|
| 1 | `impl.patch`（r2） | 4 文件：`candidate_evidence.py`、`real_model.py`、`runflow.py`、`tests/test_p2_evidence_card_v2.py`；SHA `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6`；在 `11aeeaf` 干净克隆上 `git apply --check` 通过 | 已有 |
| 2 | `v1card` 模式补丁（新） | `runflow.py`：`evidence_card_version="v1card"`（v2 prompt + v1 证据卡）；身份/resume/测试；A 用户载荷与 v1 B 逐字节等价 | **待实现/复审** |
| 3 | P2 操作链接线补丁（新） | `s5b_orchestrator.py` + `s5b_worker.py`：批级冻结 `evidence_card_version`、worker 透传、case 披露、resume/汇总校验；旧路径零新键 | **待实现/复审** |
| 4 | P2 操作脚本（新） | `scripts/hpc/p2_operations.py`、`p2_run_wrapper.py`、`sbatch_p2_build/run/score/monitor/netcheck.sh`、`p2_arm_config.json` | **待交付/复审** |
| 5 | 脚本锁（新） | `docs/T_P2_SCRIPT_LOCK_<date>.json`：上述 1–4 逐文件 SHA + 部署树 SHA | **待生成** |

> 补丁 1–4 **不包含** C 的 schema-4/descr-4、`evidence_truncation`、帽表或截断等级。
> CC 已否决 C；本批完整 v2 卡按 `candidate-evidence-3` / `descr-3` 发车。若未来 CC 改变
> 决定，另立预注册与新补丁，不在本任务书内追加。

### 3.3 `v1card` 模式的最小实现合同

> **A 臂身份（M2）：** 本节实现 `arm_a_definition = v1card`（v2 prompt + v1 证据卡）。
> 这是相对冻结设计 §二.1「A=用户 JSON 字节兼容回退/无证据」的**设计修正/新增**，不是回到
> 原意；冻结设计原文仅作历史对照。provenance 见 §0.1；未按本节实现并复审前，A 臂不是
> v1 卡，不得签字/发车。

1. `runflow._resolve_evidence_card_version` 接受 `"v1card"`；其它值仍按原判据拒绝；
2. `_Driver` 在 `v1card` 下设：
   - system prompt = v2 prompt（`PROPOSALS_PROMPT_VERSION_V2`）；
   - 候选证据 = `candidate_evidence_payload`（v1）；底物证据 = `substrate_evidence_payload`（v1）；
   - schema=`candidate-evidence-2`；descriptor=`candidate-evidence-descr-2`；
   - JSON 分隔符 = 默认（与 v1 B 逐字节同），不得用 v2 B 的紧凑分隔符；
3. `evidence_card_enabled` 在 `v1card` 下必须为 `true`；`false` ⇒ 结构化拒；
4. run identity：`strategy.evidence_card_version="v1card"`；`prediction.prompt_versions.proposals`
   = v2 SHA；schema/descriptor=v1；resume 以同判据核对，缺失/不符 ⇒ `evidence_card_version_mismatch`；
5. off 路径（缺省/None/`v1`）零漂移：prompt/schema/descriptor/payload/identity/summary 不变；
6. 测试：A 用户载荷与 v1 B 逐字节等价（system prompt 除外）；v2 prompt 哈希相对本任务书修订不变；
   chemfix 后以新 SHA `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598` 为准；
   A/B 身份键；resume 拒错；双跑字节一致；v1 证据函数未被改；
7. 复审：该模式改变证据卡身份/载荷语义，**必须走 Codex/qwen 复审 + 化学复审引用**；
   未复审不签字、不发车。

### 3.4 P2 操作链接线的最小实现合同

`s5b_orchestrator.py`：

- `run_s5b_batch(..., evidence_card_version: str | None = None)`；合法值 `None`/`"v1card"`/`"v2"`；
  非 None 时要求 `evidence_card_enabled=true`，否则结构化拒；
- 冻结副本增加 `evidence_card_version`：**仅当非 None 时写键**；None 时不得新增键（旧批零漂移）；
- worker argv 增加 `--evidence-card-version`；`_run_batch_loop`/`summarize_batch` 按臂期望值
  核对 case 披露；缺失/不符/非布尔/非字符串 ⇒ 拒；
- 批终态报告写入 `evidence_card_version`（非 None 时）。

`s5b_worker.py`：

- CLI `--evidence-card-version`；从 `orchestration.json` 读冻结值并同判据核对；
- 传递给 `start_ppv1_run`/`resume_ppv1_run` 的 `evidence_card_version`；
- case 写 `evidence_card_version`；失败路径同样披露；
- 任何缺失/不符/非法值 ⇒ fail-closed，零模型调用。

验收：旧批（无 `evidence_card_version` 键）resume/汇总**零新键、逐字节零漂移**；
A/B 交叉错配拒；v1card/v2 身份/resume 测试；全量 not-slow 绿。

### 3.5 部署与脚本锁

1. 新 worktree/克隆到 `11aeeaf`；`git apply --check` + `git apply` 补丁 1→2→3；
2. 运行全量 not-slow + v2 18 项 + 新 `v1card` 测试 + 操作链正负控；
3. off 路径零漂移对比（v1 prompt/证据/载荷/identity/summary 全等）；
4. 用**部署环境实际 RDKit** 重跑 v2 确定性锚（FG SMARTS/质子化容忍/碳氧化态/公式）；
5. 生成 `code_identity_aggregate_sha256`（P2 树实测；两臂同值；**不得沿用 T-I 的
   `1aac04da…`**）；写入 `p2_arm_config.json` 的 `identity_expectations`；
6. 生成脚本锁 JSON（补丁 1–4 + 部署树逐文件 SHA）；部署到 HPC `~/EnzymeAgent/v43cP2`
   （tar 后 `find . -name "._*" -delete`）；HPC 上逐文件 `sha256sum -c` 核对；
7. 不合并主树、不 push。

## 4. 操作入口：复用 `ti_operations` 还是新建 `p2_operations`

### 4.1 建议：**新建冻结克隆 `p2_operations.py`，复用同一套参数化语义；不改 `ti_operations.py`**

理由：

1. `ti_operations.py` 的 `REQUIRED_ARMS` 写死 `("glm","deepseek")`，approval 四文书键、
   prereg id、no-cap 日期、批名/协调目录均按 T-I 写死；不改无法跑 `v1card/v2card`；
2. 改 `ti_operations.py` 会使 T-I 的脚本锁/代码身份失效，并重开 TI-F1/F2 复审；
   T-I 仍在待续跑（C8 B2），不能为 P2 动它的正链操作件；
3. 克隆可做到“语义完全同、只换操作面”：gate 阈值、smoke2/smoke10/full、barrier、monitor、
   halt、seal、approval 校验逻辑逐字保留；diff 白名单可审计；
4. 用户要求“优先复用参数化”：这里复用的是**参数化代码语义**，不是同一个文件；若 CC
   坚持单文件复用，则必须同步重开 T-I 脚本锁与 TI-F1/F2 复审，属另一项拍板。

### 4.2 克隆必须改的面（diff 白名单）

| 面 | T-I 值 | P2 值 |
|---|---|---|
| config schema | `ti-arm-config-2` | `p2-arm-config-1` |
| 臂 | `glm` / `deepseek` | `v1card` / `v2card` |
| 臂差异 | 模型/env | **证据卡版本**（模型/env 相同） |
| 每臂新增字段 | — | `evidence_card_enabled=true`、`evidence_card_version=v1card 或 v2` |
| approval 四文书键 | `prereg/task/final_review/script_lock` | `prereg/task/chem_review/script_lock` |
| prereg id | `prereg-t-i-298-2026-10-20` | `prereg-p2-298-2026-10-21` |
| no-cap marker 日期 | 2026-10-20 | **2026-10-21** |
| 批名/job/协调目录 | `t_i_*` / `ti-*` | `p2_298_*` / `p2-*` |
| 默认 config | `ti_arm_config.json` | `p2_arm_config.json` |

**不得改**：smoke2/smoke10/full 阈值、fatal 分类、恢复一次/二败、barrier 语义、monitor 15
分钟、stop.json 首写生效、seal 语义、评分版本/headline、gate 默认值。克隆需附
`diff` 对照件与正负控，证明差异只在上表白名单。

### 4.3 配置模板

见附录 B。关键：两臂 `expected_model_id`、`env_file_basename`、`identity_expectations` 相同；
`evidence_card_version` 分别 `v1card`/`v2`；`role` 分别为 `control`/`treatment`。

## 5. build 与 prepare

### 5.1 build 策略（建议：seed build + 字节级复制）

- **建议默认**：build 一次到 seed 根（零模型、零网络），过 build-gate 后，把 build 产物
  字节级复制到两个臂根；复制后核对 `batch_manifest.json` SHA、`build_identity_fingerprint`、
  298 条逐题 `(qid, run_input_sha256)` 全等；不复制 `orchestration.json`/`gate/`/cases/状态文件。
- 理由：build 不是本实验变量；两臂必须拿到**完全 identical** 的池/输入；seed+copy 消除
  两次 build 的非确定性，省约一半机时。
- 复制后若 `build_identity.json` 记录 `assets_root` 等环境路径，按 T-I off-path 先例只把
  路径标签归一后比较非路径事实；**不得用路径差异冒充身份差异，也不得改指纹字段**。
- 备选（CC 可改）：两臂独立 build + 同一 `batch_tag`，指纹逐字相同硬门（T-I D6 先例）。
  两种方案都必须满足 §5.2 身份门；不得一臂 seed、一臂独立 build。

### 5.2 身份门（任一不过即停）

1. 两臂 `batch_tag` 相同；
2. `batch_manifest.json` 字节级 SHA 相同；
3. `build_identity_fingerprint` 相同且为 64 位小写 hex；
4. `build_identity.run_inputs` 的 298 条 `(qid, run_input_sha256)` 完全相同；
5. manifest 的 `build_identity_ref` 与 `build_identity.json` 一致；
6. 代码聚合身份 = P2 树实测值（两臂同值）；compiler/pool/retrieval/rank 版本与 §2 同值；
7. RDKit 版本与部署环境实测一致，且 v2 确定性锚已在该版本下通过；
8. 缺指纹、空 sha、旧 T-I 聚合混入 ⇒ 直接停，不 prepare。

### 5.3 prepare（每臂）

- 预放批准包 `p2_approved_record_<date>/`：`preregistration_approval.json`、
  `budget_no_cap.json`、四份文本快照（prereg/task/chem_review/script_lock）、`SHA256SUMS`；
- `p2_operations.py prepare --arm v1card|v2card ...` 逐臂执行；核对批准文本 SHA、
  `approval_status`、build 身份、no-cap schema/marker、四文书、模型/env、脚本锁；
- 写 `record/p2_operations.json`、`arm_config.json`（含 evidence 版本/开关）；
- 跑输入形态探针（沿用 `p2_face_measure`）：期望 `specs_total=531`、`remap_applied=242`、
  `remap_add_atom_ge1=205`、`remap_add_atom_ge2=78`、`questions_remap=151`、
  `questions_with_add=134`、`questions_with_multi_add=65`、`files=298`；
  不符 ⇒ 停，查 build/资产；**不得改探针口径**；
- **P2 载荷/token 披露件**（离线、零模型）：
  - 对 298 输入构造 A（v1card）与 B（v2）的 system+user 固定载荷；
  - 记录逐题/批合计 tokens、B vs A 增量、分布、>13% 题集（**只披露**）、tokenizer SHA；
  - 抽样核对实际 payload SHA 与代码路径一致；不写题面/候选 SMILES 正文；
  - 生成 `p2_token_measure_298_arms.json` 入批根 record；
- **分族件（M3 时序）**：发车前（build/prepare 后、零题面）由 run_inputs 底物 SMILES 冻结
  `p2_family_f2raw.json`（同底物 ≥2 题集合，**不减 F1**）+ 分族规则并记 SHA；F1 在 A 臂
  评分后冻结；最终互斥分区（F2=F2raw−F1、F3=补集）在 F1 冻结后按已写死规则确定性生成，
  写 `p2_family_partition.json` 并记 SHA（见 §9.3）；
- 检查 `orchestration.json` 首跑冻结：A `evidence_card_enabled=true`/`version=v1card`；
  B true/`v2`；其余冻结参数逐字相同。

## 6. 前置 C2–C5 与站点 soak（新窗重证，不吃 T-I 旧读数）

### 6.1 C2 作业能力/净环境

- 计算节点可提交、python/rdkit 可导入、盘空间/flock/句柄充足；
- 登录节点不跑重活；所有重活 sbatch。

### 6.2 C3 官方 netcheck

T-I 的 `scripts/hpc/sbatch_th_netcheck.sh` 把 `CODE` 写死为 `$HOME/EnzymeAgent/v43cTH`；
P2 **不得**直接用它（会检查 T-I 树/环境）。发车前必须交付 `scripts/hpc/sbatch_p2_netcheck.sh`
（或参数化 `CODE`），指向 `v43cP2`，其余只读/判据与 T-I 版一致。

**唯一直接 sbatch 的脚本：** 官方 netcheck 是 P2 唯一允许直接 `sbatch` 的脚本（共享脚本
沿用 T-I 同一约定）；其余阶段一律经 `p2_operations.py launch`。本文件与附录 A 的 G4 命令
必须逐字一致，且**不得**出现 `sbatch_th_netcheck.sh`（该脚本属 T-I，会检查 `v43cTH`）。

```bash
WS="$P2_WS" sbatch --parsable scripts/hpc/sbatch_p2_netcheck.sh
```

判据：`COMPLETED 0:0` 且日志含 `NETCHECK-PASS`。该脚本只探 DashScope 端点，不检查模型级
开通；模型开通由 C5 预检负责。

### 6.3 C8 代理 soak（G1–G4，付费前必须全绿）

| 门 | 判据 |
|---|---|
| G1 计算节点 soak | 连续 **12/12** 成功（HTTP 401 + connect<3.5s + total<15s），间隔 60s±10s，≥12 分钟；一次失败签名即整轮作废 |
| G2 登录经代理 | 同窗 **3/3** 成功，间隔 60s |
| G3 登录直连对照 | 1 次：401 且 total<5s |
| G4 官方 netcheck | G1–G3 绿后 30 分钟内提交，`COMPLETED 0:0` + `NETCHECK-PASS` |

- 失败签名：`curl_rc=28 / http_code=000 / connect≈7.01s`；
- soak 失败 ⇒ 等 ≥2h 重做；**连续两轮失败 ⇒ 停，报 CC**；不自动换站/改端点；
- 探针脚本/输出/时间戳落证据目录 + `SHA256SUMS`；不打印任何 key。

### 6.4 C4 env/模型只读核对

- 两臂共用同一 env 文件；权限 600；`V43_LLM_MODEL` 与 `p2_arm_config.json` 逐字一致；
  `V43_LLM_BASE_URL`/`V43_LLM_REQUEST_PARAMS` 两臂同值（只核布尔/同值，不打印值/key）；
- 任何 temperature/思考键混入 ⇒ 停（政策不发 temperature）；
- `reasoning_effort` 是否被接受未知；不兼容 ⇒ 停，交 CC，不静默增删。

### 6.5 C5 付费预检

- 两臂同模型/env ⇒ **一次共享最小调用**即可（也可每臂各一次，但必须都计入 usage 账）；
- 核对 HTTP 200、非空 content、usage 可解析、模型 ID 与预期一致、无 400/401/402/403；
- 预检可用较短超时（如 300s，仅预检）；超时即停、不重试；
- 写入 `operations/preflight_calls.json`（臂/共享、模型、tokens、时间、金额或 unknown），
  计入 usage 账；金额无快照记 unknown，不估算。

## 7. run（每臂 smoke2→smoke10→barrier→full）

### 7.1 发车顺序

```bash
for arm in v1card v2card; do
  "$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" launch --phase run \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    --config "$P2_CODE/scripts/hpc/p2_arm_config.json" \
    || { echo "STOP: run $arm"; exit 1; }
done
```

- 两臂 run 作业**都提交后**，任一臂才可能在 barrier 等到对侧 smoke10；禁止先跑完 A 整臂
  再提交 B（A 会卡 barrier 至超时停臂）；
- 默认并行（同时间窗）；若账号级 429/TPM 挤兑，可错峰提交，但两臂仍须都提交、各自
  smoke10 都过才准 full；顺序会引入时间窗差异，结果披露；
- 每臂独立 gate（4470 调用/臂，RPM 200/TPM 3M，workers 8/8）。

### 7.2 smoke2 判据（每臂；机器强制）

1. 至少 1 题 completed 且 `model_calls>0`；
2. 所检 2 题均终态（pending=0）；
3. `run_identity.prediction.model_id` 与 `p2_arm_config.json` 一致；两臂模型 ID 相同；
4. `run_identity.strategy.evidence_card_version` 与臂一致（A=`v1card`，B=`v2`）；
   `prompt_versions.proposals` 两臂均为 v2 SHA；schema/descriptor 与臂一致；
5. usage 可解析（completed 且有调用的题必须 `usage.present=true`，input/output/total 为整数）；
6. 无 fatal 信号（auth/quota/402/403/401/identity/integrity/no-cap marker/
   evidence-card-version/`unregistered_cx_class`）。

任一项不满足 ⇒ 停两臂，不进入下一阶段。

### 7.3 smoke10 判据（每臂）

1. 10 题全部终态（仍有 pending ⇒ 停）；
2. 非豁免 `failed>0` ⇒ 停该臂并停另一臂（终态 failed 必须先处置，不得口头豁免）；
3. 未登记结构性原因的零调用 >0 ⇒ 停两臂；已登记 NC-9
   （`ProductionContractError / cosubstrate_copy_in_expectation`，`counts.events=0`）
   按未中登记、豁免；
4. 按“实测每调用 token × 预期 298 次调用”外推该臂 total tokens，写入运行记录并与
   §11 的 token 披露并列；**不设 token/金额硬停**；
5. 任何 429 风暴、连续 2 个不同 qid 未按冻结策略恢复 ⇒ 停报。

两臂 smoke10 都通过并写入 barrier 放行件后，才准任一臂 full；不单独让一臂跑 full。

### 7.4 monitor / halt

```bash
"$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" monitor --submit \
  --ws "$P2_WS" --code "$P2_CODE" --config "$P2_CODE/scripts/hpc/p2_arm_config.json"

"$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" monitor --ws "$P2_WS" --checks 1
"$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" halt --ws "$P2_WS" \
  --reason "manual coordinator halt" --cancel
```

- 单协调者 flock；15 分钟巡检；任一停点写 `coordination_dir/stop.json`（首写生效），
  并（可执行时）`scancel` 两臂 run 作业；另一臂每阶段前查停点；
- 运行中 fatal 停派发：沿用已部署的 `orchestrator_stop_dispatch` 补丁（T-I C6 已部署，
  同一行为）；P2 树若未带该补丁，必须在 §3 的 P2 操作链补丁中一并带上，否则不满足
  “收割 fatal 后立即停派发”。

## 8. score（每臂）

```bash
for arm in v1card v2card; do
  "$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" launch --phase score \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    --config "$P2_CODE/scripts/hpc/p2_arm_config.json" \
    || { echo "STOP: score $arm"; exit 1; }
done
```

- 默认判分顺序 v1→v2；根 headline=v2；输出 `metrics.json{,.v1,.v2}`、`report*.md*`、
  `p2_score_complete.json`；
- v3 默认关；若 CC 明确要 v3 纯披露，用 `--include-v3`，顺序 v1→v3→v2，追加 `.v3` 与
  `criteria_v3_disclosure.json`，并做 v3/v2 稳定字段对账；差异即停交付；
- 判分零 LLM；两臂都 score 完成后才拉回。

## 9. 对账与出数

### 9.1 身份对账（逐项硬门）

| 项 | A=v1card | B=v2 | 判据 |
|---|---|---|---|
| 模型 ID | 同值 | 同值 | 逐字相同 |
| env 文件 | 同值 | 同值 | 同一 basename |
| build fingerprint | 同值 | 同值 | 逐字相同 |
| 298 逐题 run_input SHA | 同值 | 同值 | 298/298 |
| prompt SHA | v2 | v2 | 同值 |
| evidence_card_version | `v1card` | `v2` | 与臂一致 |
| evidence_card_enabled | true | true | 同值 |
| schema/descriptor | v1 | v2 | 与臂一致 |
| RDKit 版本 | 同值 | 同值 | 实际版本 |
| 判分版本/headline | v2 | v2 | 同值 |

任何一项不符 ⇒ 批无效，停；不得用“改一臂旁件/重算新 ID”洗掉差异。

### 9.2 配对统计

- 逐题合并两臂 `metrics.json.v2` 的 `per_qid`；核对 298/298、无重复/无缺；
- 分别对 hit@1、strict(U) 报告 `b/c/net/n_disc`；精确 McNemar 双侧 p 描述性；
- hit@1/@3/@5、strict(U)、rank>1、三桶计数、rank 分布；
- v1 敏感性同表并列；v1 与 v2 不混比；
- 失败/零调用/超时/空响应/解析失败/usage_missing 单列；分母仍 298。

### 9.3 分族与停点

1. 两臂评分完成后，先只用 **A 臂** 计算 F1（strict-rank>1）；
2. F1 冻结（qid 列表）后，按发车前已冻结的 `p2_family_f2raw.json` 与分族规则
   **确定性生成** F2=F2raw−F1、F3=298−F1−F2，写 `p2_family_partition.json`
   （F1/F2/F3 qid 列表 + F2raw SHA + 生成规则 + 本文件 SHA）；**冻结该件后**才读 B 的配对结果；
3. F2raw 由 run_inputs 底物 SMILES 分组（同底物 ≥2 题，**不减 F1**），发车前已冻结；
   评分后不得改分组口径/阈值；
4. 对全局与 F1/F2/F3 分别计算 `Δstrict = c − b`；
5. **任一 `Δstrict ≤ −3` ⇒ 科学停点复盘**：不宣布收益、不进入下一轮、不据此改设计；
   报 CC/代决裁定；
6. 同时报告四象限（hit@1 B−A × rank>1 B−A）允许读法；不得越象限写结论。

### 9.4 novel 首选、失败、usage、token

- novel 首选：分母 298；协议规范化首位为 novel 的题数；无首位/弃权留分母不入分子；
  A/B 并列；v2 不劣于 A 为工程防退化线，但不单独停批；
- 失败/零调用：逐题原因、是否结构性、是否影响分母；NC-9 单列；
- usage：每臂 input/output/total、调用数、重试、零调用、`usage_missing_calls`；格式反馈轮/
  传输重试单列；金额 unknown 或账单实数；
- token 披露：A/B 同 prompt 固定载荷逐题/批合计、B vs A 增量、分布、>13% 题集（仅披露）、
  tokenizer SHA；最终 tokenizer 读数（若可得）并列；**不写成门**。

### 9.5 拉回白名单

只拉：`metrics.json{,.v1,.v2}`、`report*.md*`、`batch_report.json`、`orchestration.json`、
`profile_policy.json`、`build_identity.json`、`p2_face_measure.json`、`arm_config.json`、
`p2_score_complete.json`、批准记录副本、usage/费用摘要、失败登记、token 披露件、
`p2_family_partition.json`、stop/阶段回执。

不拉：题卷、`reference_graphs/`、逐题 case/state/run 正文、含模型自由文本的大件、env/key。

### 9.6 结果报告

产出 `docs/T_P2_RESULT_<date>.md`（技术版）+ `_PLAIN.md`（大白话版），至少含：

1. 身份表（模型、env basename、代码 commit、代码聚合、build fingerprint、题卷 SHA、
   prompt/schema/descriptor/RDKit、判分版本、profile/gate/超时/重试、两臂证据卡版本）；
2. 两臂主表（v2 headline；v1 敏感性并列）：hit@1/@3/@5、strict(U)、三桶、rank>1、分母 298；
3. 配对表：hit@1/strict 的 `b/c/net/n_disc`、McNemar p（描述性）；
4. 分族 F1/F2/F3 的配对与停点判定；F2raw 冻结 SHA、F1 冻结 SHA、
   `p2_family_partition.json` SHA（F1 评分后生成）；
5. novel 首选占比 A/B；
6. 四象限判读与“整包/非盲臂/不识别单字段”措辞；
7. 失败/零调用/unknown；
8. token 披露（含 +8.2165%/104/298/+64.13% 的既有读数，注明其口径是 v2 B vs 无证据 A；
   P2 同 prompt A/B 实测另列）；最终 tokenizer（若可得）；
9. usage 与金额（实数或 unknown）；
10. 限制（单批、单模型、prompt-卡语义不匹配、JSON 空白、代理 tokenizer、RDKit、NC-9、
    空池、站点时间窗、no-cap）；
11. 封存/证据路径、作业号、SHA 清单；
12. 每张表带 **[298 域]** 标签；不写通用能力、不写单字段因果。

## 10. 费用口径

- CC 2026-10-21：**不考虑预算，只要效果**；两臂 no-cap；
- 每臂批根 `budget_no_cap.json`：

```json
{
  "budget_mode": "no_monetary_cap_user_decision",
  "marker": "no_monetary_cap_user_decision_2026-10-21",
  "note": "CC 2026-10-21 决定 P2 完整 v2 无预算帽;金额检查跳过;调用数门(gate_max_calls=4470)/速率门(RPM 200/TPM 3M)/并发门(max_in_flight=8)照常;usage 照记;金额无快照记 unknown;与 budget_guard.json 互斥",
  "recorded_at": "<生成时真实 UTC>",
  "schema": "v44-budget-no-cap-1",
  "user_decision_date": "2026-10-21",
  "user_decision_record": "CC 2026-10-21: 我不考虑预算啊 我真不考虑预算 我只要效果好"
}
```

- 无金额停点；不设 80%/90%/100% 告警；token/usage 只记录；
- 用量记录点：预检、smoke2、smoke10、full、格式反馈、传输重试、失败无 usage；
- 金额：有账单/价格快照才写实数；否则 `cost_status=no_snapshot`、`cost_known_cny=null`；
  **不得 token×单价估算、不得编造单价**；
- 规划参考（仅沟通，不是承诺）：v2 B 298 题首发固定载荷约 96.3 万 input token（代理
  tokenizer 读数）；A v1card 待测；输出/反馈/重试未知；实际 usage 以批报告为准；
- **不采用 C**：不生成帽表、不做截断、不升 schema-4/descr-4；qwen 的 FAIL 事实保留为
  披露，CC 豁免该门作为放行门；**不得写“token 门已过”**。
- 若事后账单异常，按事故口径单独报 CC，不自动改批/加帽。

## 11. 停点/失败处置/回滚/封存

### 11.1 停点表

| 阶段/信号 | 阈值 | 处置 |
|---|---|---|
| 预注册/批准 | 缺签字、四文书 SHA 不符、`no_cap_ack!=true`、来源链不明 | 不发车；不预检付费 |
| 模型 | T-I 无效/未完成；模型 ID 与配置不符 | 不选模型；不发车 |
| 代码 | v1card/操作链补丁未复审；off 零漂移失败；脚本锁不符 | 不发车；回修/复审 |
| RDKit | 版本未登记；v2 锚在该版本下失败 | 不发车；对齐/复跑 |
| 站点 | G1–G4 任一失败；连续两轮 soak 失败 | 停；等/报 CC；不自动换站 |
| 预检 | 401/402/403/400、模型 ID 不符、env 缺失、参数不兼容 | 停全部；不 build/run |
| build/身份 | 作业非零、无 BUILD-PASS、fingerprint/manifest/逐题 SHA 不符 | 停；不 prepare/run |
| prepare | 批准包缺件、SHA 不符、探针计数异常、orchestration 冻结不符 | 停；不改审批/不猜 |
| smoke2 | 无真实调用可核、pending、身份/usage/fatal | 停两臂 |
| smoke10 | 非豁免 failed>0、未登记零调用>0、pending | 停该臂并停另一臂 |
| full | 非模型内容失败>15、pending>0、fatal | 停两臂、保全现场 |
| 科学停点 | 全局或任一分族 `Δstrict≤−3` | **评分后**停点复盘；不宣布收益 |
| token/金额 | 无硬停；usage 只记录 | 超规划带只告警登记 |
| score | 全 qid 未终态、回执 schema/digest 不符、v3 稳定字段差异 | 停；不交付 |
| 范围外 | 新参数/新 prompt/新判据/换模型/改分母 | 一律停；另立预注册 |

### 11.2 失败处置

- 任一停点写 `coordination_dir/stop.json`（首写生效，不覆盖），并（可执行时）`scancel`
  两臂 run 作业；另一臂每阶段前查停点；
- 保留现场：批根/runs 根/case/日志/usage/SHA 全只读；不清 stop、不移 case、不删证据；
- 不自动重跑、不自动换模型、不自动加帽、不自动改参；
- 新尝试须新批标签/新批根 + 新预注册或 CC 书面偏离批准；
- 恢复只走既有 `prediction_recovery` 白名单、同题同参一次、先保全；二败停。

### 11.3 回滚

- 预检/build/prepare 失败：不产生付费批；回修仅限发车前窗口，修后重跑全部门/重锁；
- run 中途停：批根封存为“停跑证据”，不复用、不续跑换参；新批重新 build；
- score 失败：只用同一输入重跑冻结 scorer；不得手改 metrics；仍失败则停交付；
- 任何回滚不得写旧批（T-H/chain13/chain14/T-I）。

### 11.4 封存

```bash
for arm in v1card v2card; do
  "$P2_PY" -B "$P2_CODE/scripts/hpc/p2_operations.py" seal \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    || { echo "STOP: seal $arm"; exit 1; }
done
```

- 校验 `p2_score_complete.json` 与全部产物 SHA，写 `p2_sealed.json`，目录 555/文件 444；
- runs 根不封；封存后只读，不再补评分、不再写；
- 封存前确认两臂 score 完成、SHA 清单一致。

## 12. 不执行声明与剩余前置

**本任务书不执行。** 它只是发车物草案；在下列前置全部闭合前，不得产生任何付费调用：

1. **T-I 模型选择**：T-I 当前被站点代理阻塞，尚无最终有效批；模型 TBD；
2. **P2 预注册签字**：`approval_status=preregistration_confirmed` + 四文书 SHA + 模型 ID +
   T-I 结果 SHA + `no_cap_ack=true`；
3. **v2 化学复审**：当前 Stage B 独立复审为 **PASS_WITH_CONDITIONS / 未放行**
   （`T_P2_V2_CHEM_REVIEW_2026-10-21.md` §2 P1–P7 未闭合，不构成化学放行）；须独立
   v2 化学复审/条件闭合；R4（P0b/D-6，同为 **PASS_WITH_CONDITIONS**，C1–C4 未闭合 +
   58/146 unknown）**不能充抵**（§0.3）；
4. **`v1card` 模式**：当前 r2 实现不支持；需实现/复审；否则 A 臂不是 v1 卡；
5. **P2 操作链**：orchestrator/worker 的 `evidence_card_version` 批级冻结与透传未接；
   `p2_operations`/`p2_run_wrapper`/`sbatch_p2_*` 待交付/复审；
6. **代码身份/RDKit**：P2 树新聚合未测；HPC RDKit 2026.03.5 与实现环境 2026.03.6 未对齐；
7. **token 披露件**：同 prompt A/B 298 实测未做；最终 tokenizer 待模型选定；
8. **付费/HPC 授权**：CC/代决未落字；
9. **站点**：C8 soak/netcheck 未在新窗重证；
10. **Codex 正链复核确认**：qwen 代决不替代正链最终裁定权；设计/实施/放行类结论待正链
    额度恢复后复核。

## 13. 红线

1. 预注册先于付费；无签字不发车、不预检付费调用。
2. 判分/评测零 LLM；模型只出 proposals。
3. 金标隔离：题卷/参考图/逐题 case 只留 HPC；本地只拉指标/身份件。
4. 一批跑完、禁止修一点跑一点；批中零代码/配置/prompt/模型改动。
5. 封存旧批只读；P2 新批根独立；旧批零回写。
6. 不 push；push 时机归 CC。
7. 题域标签处处带；298 与 dev 双向不外推。
8. 单变量=证据卡版本；模型/env/pool/prompt/判据/配置必须同值；任何额外差异=停报 CC。
9. 失败/零调用不剔题；不换题、不补跑换题。
10. token 只披露、不设门、不截断、不采用 C 帽表；不因 token 成本改 treatment；
    不写“token 门已过”（qwen 的 FAIL 事实保留，CC 豁免作为放行门）。
11. 不把探针/单批配对写成成绩；不把 mixed/weak 写成“有效”。
12. 不改判据/池/检索/排序/评分/硬拒绝表/调用次数/分母。

## 14. 回传义务

- 每步完成回报“做了什么/读数/下一步”：预检、build、身份门、prepare、每臂 smoke2、
  每臂 smoke10、每臂 full、每臂 score、拉回封存；
- 预检失败/用量异常/429 风暴/CX/身份错误/连续失败/科学停点 ⇒ 立即停并报 CC，
  不自动处置；
- 出数后按 §9.6 出技术版 + 大白话版；每张表带 298 标签；
- 不 push；不新增付费批；不把本批结果写进老师既定目标的达成声明；
- 金额 unknown 不阻塞，账单异常单独报。

## 附录 A — 命令模板（待 `p2_operations.py` 交付后启用）

```bash
# 0) 一次设定（登录节点）
P2_WS="$HOME/ppv1_hpc"
P2_CODE="$HOME/EnzymeAgent/v43cP2"
P2_PY="$P2_WS/venv_v44run/bin/python"
export P2_WS P2_CODE P2_PY
export PYTHONPATH="$P2_CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$P2_CODE"

# 1) 站点 soak/netcheck（G1–G4；按 C8 探针脚本）
#    G1/G2/G3 输出落 docs/review_evidence/p2_soak_<date>/ + SHA256SUMS
#    G4（官方 netcheck 是唯一允许直接 sbatch 的脚本；其余全走 p2_operations.py launch）：
WS="$P2_WS" sbatch --parsable scripts/hpc/sbatch_p2_netcheck.sh

# 2) build（seed + copy 或两臂独立；按 §5）
"$P2_PY" -B scripts/hpc/p2_operations.py launch --phase build \
  --arm v1card --ws "$P2_WS" --code "$P2_CODE" --config scripts/hpc/p2_arm_config.json
"$P2_PY" -B scripts/hpc/p2_operations.py launch --phase build \
  --arm v2card --ws "$P2_WS" --code "$P2_CODE" --config scripts/hpc/p2_arm_config.json
"$P2_PY" -B scripts/hpc/p2_operations.py verify-identity --ws "$P2_WS" \
  --config scripts/hpc/p2_arm_config.json

# 3) prepare
for arm in v1card v2card; do
  "$P2_PY" -B scripts/hpc/p2_operations.py prepare \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    --config scripts/hpc/p2_arm_config.json \
    || { echo "STOP: prepare $arm"; exit 1; }
done

# 4) run
for arm in v1card v2card; do
  "$P2_PY" -B scripts/hpc/p2_operations.py launch --phase run \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    --config scripts/hpc/p2_arm_config.json \
    || { echo "STOP: run $arm"; exit 1; }
done
"$P2_PY" -B scripts/hpc/p2_operations.py monitor --submit \
  --ws "$P2_WS" --code "$P2_CODE" --config scripts/hpc/p2_arm_config.json

# 5) score
for arm in v1card v2card; do
  "$P2_PY" -B scripts/hpc/p2_operations.py launch --phase score \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    --config scripts/hpc/p2_arm_config.json \
    || { echo "STOP: score $arm"; exit 1; }
done

# 6) seal
for arm in v1card v2card; do
  "$P2_PY" -B scripts/hpc/p2_operations.py seal \
    --arm "$arm" --ws "$P2_WS" --code "$P2_CODE" \
    || { echo "STOP: seal $arm"; exit 1; }
done
```

## 附录 B — `p2_arm_config.json` 模板（草案；SHA/模型/日期发车日回填）

```json
{
  "schema": "p2-arm-config-1",
  "batch_tag": "p2-298-<YYYYMMDD>",
  "date_stamp": "<YYYYMMDD>",
  "source_commit": "11aeeafded1b41185f24de49767933709aad49db",
  "arm_a_definition": "v1card",
  "immutable_batch_names": [
    "t_h_s5b_298_20261020",
    "t_i_298_20261020_glm",
    "t_i_298_20261020_deepseek"
  ],
  "ws_default": "~/ppv1_hpc",
  "code_default": "~/EnzymeAgent/v43cP2",
  "python_default": "~/ppv1_hpc/venv_v44run/bin/python",
  "paths": {
    "batch_root": "{ws}/batch/{batch_name}",
    "runs_root": "{ws}/runs/{runs_name}",
    "env_file": "{ws}/env/{env_file_basename}",
    "operations_state": "{ws}/operations/{batch_name}.json",
    "record_dir": "{ws}/operations/p2_approved_record_<YYYYMMDD>",
    "coordination_dir": "{ws}/operations/p2_coordination_p2-298-<YYYYMMDD>"
  },
  "sealed_marker": "p2_sealed.json",
  "questions": {
    "path": "{ws}/questions.jsonl",
    "sha256": "<发车日实核>",
    "n_questions": 298
  },
  "identity_expectations": {
    "code_identity_aggregate_sha256": "<P2 树实测>",
    "compiler_version": "s5b-compiler-6",
    "pool_policy_version": "s5b-pool-policy-9",
    "recorded_source_version": "s5b-recorded-source-4",
    "corpus_retrieval_version": "s5b-corpus-retrieval-6",
    "formnorm_version": "record-side-formnorm-1",
    "route_version": "s5b-analog-route-f1f4-1",
    "rdkit_version": "<部署环境实测>"
  },
  "scientific_source_sha256": {
    "src/pathway_v43/pollutant/s5b_compiler.py": "<实测>",
    "src/pathway_v43/pollutant/evaluation.py": "<实测>"
  },
  "build": {
    "mode": "seed_copy_or_per_arm_independent",
    "identity_gate": "literal_fingerprint_requires_shared_batch_tag"
  },
  "scoring": {
    "default_versions": ["v1", "v2"],
    "headline": "v2",
    "v3_default": false
  },
  "no_cap": {
    "schema": "v44-budget-no-cap-1",
    "budget_mode": "no_monetary_cap_user_decision",
    "marker": "no_monetary_cap_user_decision_2026-10-21",
    "user_decision_date": "2026-10-21",
    "user_decision_record": "CC 2026-10-21: 我不考虑预算啊 我真不考虑预算 我只要效果好"
  },
  "approval": {
    "preregistration_id": "prereg-p2-298-2026-10-21",
    "source_kind": "<cc_personal|codex_delegated_cc_shijie|qwen_delegated_codex>",
    "required_docs": {
      "prereg": "docs/T_P2_PREREG_FULL_V2_2026-10-21.md",
      "task": "docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md",
      "chem_review": "docs/T_P2_V2_CHEM_REVIEW_<date>.md",
      "script_lock": "docs/T_P2_SCRIPT_LOCK_<date>.json"
    },
    "no_cap_ack": true
  },
  "arms": {
    "v1card": {
      "batch_name": "p2_298_<YYYYMMDD>_v1card",
      "runs_name": "p2_298_<YYYYMMDD>_v1card",
      "job_prefix": "p2-v1card",
      "env_file_basename": "<T-I 选定模型的 env>",
      "expected_model_id": "<T-I 选定模型>",
      "role": "control",
      "evidence_card_enabled": true,
      "evidence_card_version": "v1card",
      "token_plan_high": 12000000
    },
    "v2card": {
      "batch_name": "p2_298_<YYYYMMDD>_v2card",
      "runs_name": "p2_298_<YYYYMMDD>_v2card",
      "job_prefix": "p2-v2card",
      "env_file_basename": "<同 v1card>",
      "expected_model_id": "<同 v1card>",
      "role": "treatment",
      "evidence_card_enabled": true,
      "evidence_card_version": "v2",
      "token_plan_high": 12000000
    }
  }
}
```

> `token_plan_high` 在 no-cap 下只作沟通/告警，不设硬停；上表 12,000,000 是草案占位，
> 发车前按实际规划回填（两臂可同值；不是金额、不是预算帽）。
> `env_file_basename`/`expected_model_id` 两臂必须逐字相同；不同 ⇒ 停（本批不是模型对比）。
> `arm_a_definition` 必须为 `v1card`（M2；设计修正/新增，provenance 见 §0.1）；
> 与 `arms.v1card.evidence_card_version` 必须一致，不一致 ⇒ 停。

## 附录 C — 发车前验收矩阵（建议）

| # | 面 | 正控 | 负控 | 通过判据 |
|---|---|---|---|---|
| 1 | v1card 载荷 | A 用户载荷 == v1 B 逐字节 | 非法版本值拒 | 字节相等 + 结构化拒 |
| 2 | v2 载荷 | B 载荷含 v2 字段/紧凑分隔符 | 缺字段/多字段/旧 schema 混入拒 | 字段面/schema 全等 |
| 3 | 身份 | A=v1card/v1 schema；B=v2/v3 schema；prompt 同 v2 | 缺失/错臂/错 schema 拒 | run_identity/resume 全等 |
| 4 | 批级冻结 | orchestration 两臂版本正确 | 改参/换臂/缺键拒 | 冻结副本比对 |
| 5 | off 零漂移 | None/v1 路径字节全等 | v2 键泄漏到旧路径拒 | 15 项对比全 true |
| 6 | 旧批兼容 | 无 version 键的旧批 resume/汇总 | 新键写入旧批拒 | 零新键、字节不变 |
| 7 | 操作链 | 两臂 smoke2/smoke10/barrier/full 正控 | fatal/零调用/超限负控 | 阈值/停点全等 |
| 8 | 判分 | v1/v2 双版本 | 回执/schema 篡改负控 | 冻结 scorer 全等 |
| 9 | RDKit | 部署版本 v2 锚通过 | 版本漂移/身份不符拒 | 实测版本登记 |
| 10 | 封存 | score 完成后 seal | 未完成/封存后写拒 | SHA/权限正确 |