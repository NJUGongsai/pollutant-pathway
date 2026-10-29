# P2 `v1card` 模式离线实施收尾报告（2026-10-21）

> **题域：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只做离线实现核对、
> 定向测试与探针复跑；**未部署 HPC、未调用任何模型/网络、未跑付费批、未读金标/题面/
> reference_graphs/env/key、未改 T-I 锁定件、未 push**。合成样本/单一场景读数不外推为
> 真实 298 分布或科学收益。
>
> **Provenance：** P2 实施子代理收尾；任务书
> `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md`（SHA-256
> `d47dae5dda50aa8f3906138914c8174c1456c7d24350bc4afb053b0b6307067f`）§3.3；
> 预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` §2.2/§2.3/§2.5（`DRAFT_NOT_SIGNED`）；
> 基线 commit `11aeeafded1b41185f24de49767933709aad49db`；
> worktree `/private/tmp/dependingv43_p2_v1card`。
>
> **程序面复审状态（2026-10-21）：qwen3.8max 代 Codex 复审 A 路 `v1card` PASS**；
> 复审报告 `docs/QWEN_P2_AB_REVIEW_2026-10-21.md`（复审对象版本 SHA `3cf879e7…19c3`——
> **非持久化/逐轮易变**的复审时报告文本哈希；本 M2 补记后文件哈希已变）。
> 化学复审仍未做，正链 Codex 复核待额度；签字/发车门不变。

## 1. 一句话结论

**§3.3 第 1-6 条（代码/测试合同）逐条落地，未发现合同缺口；第 7 条程序面复审已 PASS，
化学复审为待办流程门。定向 28 passed、两个探针复跑与既有证据逐字节一致、off 路径
15 项零漂移全 true。具备送审条件，不具备签字/发车条件**
——程序面复审已由 qwen3.8max 代 Codex 完成（PASS），化学复审尚未执行、正链 Codex
复核待额度；操作链（§3.4，patch 3）未接，`v1card` 目前只能经
`start_ppv1_run`/`resume_ppv1_run` 直连入口使用。

| 项 | 结论 |
|---|---|
| §3.3 合同 7 条 | **第 1-6 条（代码/测试合同）全部满足，无缺口**；第 7 条程序面复审 **PASS**（qwen3.8max 代 Codex，`docs/QWEN_P2_AB_REVIEW_2026-10-21.md`），化学复审待办（逐条见 §2） |
| 代码改动 | patch1（v2 基线）4 文件 +1225/−45；patch2（v1card 增量）2 文件 +512/−29；合并 `impl.patch` 5 文件 +1713/−50（2061 行，99,570 字节） |
| 补丁可应用性 | 干净 `11aeeaf` 副本上 patch1→patch2 顺序 apply OK；`impl.patch` 单独 apply OK；应用后 5 文件 SHA-256 与 worktree 全等 |
| 定向测试 | **28 passed in 4.94s**（10 个 v1card + 18 个 v2） |
| 相关既有批（保存日志） | **174 passed in 88.23s** |
| 全量 not-slow（保存日志，本次未重跑） | **2362 passed, 16 deselected in 411.31s**（收集总数 2378） |
| off 路径零漂移 | **15/15 检查 true**；A/B 载荷 SHA 前后相同（`c2526a7f…799d` / `b8f66ed9…981e`） |
| v1card 探针 | 7/7 checks true；A 载荷与 v1 B 逐字节相同（`e00f3b40…ba0d`）；resume 同版本通过、换版本 `evidence_card_version_mismatch` |
| T-I 锁定件 | 14 件；`impl.patch` 路径交集为 **0** |
| 是否具备送审条件 | **具备**：代码/patch/测试/探针/证据齐 |
| 是否具备发车条件 | **不具备**：化学复审未做、正链 Codex 复核待额度、token（同 prompt 的 v1 卡 vs v2 卡）未实测、操作链未接 |

## 2. §3.3 七条合同逐条对照

行号均指 worktree `/private/tmp/dependingv43_p2_v1card` 当前文件；测试行号指
`tests/test_p2_v1card_mode.py`（除特别注明外）。

| # | 合同条目 | 实现位置（file:line） | 测试或证据 | 结论 |
|---|---|---|---|---|
| 1 | `runflow._resolve_evidence_card_version` 接受 `"v1card"`；其它值仍按原判据拒绝 | `src/pathway_v43/pollutant/runflow.py:1919-1931`：`None/"v1"→None`、`"v1card"/"v2"→原值`、其余 `evidence_card_version_invalid` | `tests/test_p2_v1card_mode.py:333-348` 覆盖 `V1CARD`/`v1-card`/`v1_card`/`v3`/`""`/`1`/`True`；非法值在创建 run 目录前拒（无空目录） | **满足** |
| 2a | `v1card` 下 system prompt = v2 prompt | `runflow.py:1464-1474`（`fetch_kwargs["system_prompt"]=proposals_system_prompt("v2")`）；`src/pathway_v43/pollutant/real_model.py:271-281`（v2 选择器）、`real_model.py:1020-1024`（实际发送） | `test_p2_v1card_mode.py:139-165`（A 的 prompt 等于 v2、v1 B 等于 v1）；探针 check `v1card_system_prompt_equals_v2` | **满足** |
| 2b | 候选证据 = v1 `candidate_evidence_payload`；底物证据 = v1 `substrate_evidence_payload` | `runflow.py:1442-1463`（`else` 分支复用 v1 纯函数；`v1card` 不再进入 v2 分支） | `test_p2_v1card_mode.py:167-181`（v1 独有 `source`/`coefficient_status`/Gasteiger 在位，v2 字段缺席）；探针 `v1_evidence_sha_unchanged`/`v1_substrate_sha_unchanged` | **满足** |
| 2c | schema=`candidate-evidence-2`；descriptor=`candidate-evidence-descr-2` | `runflow.py:1473` 传 `CANDIDATE_EVIDENCE_SCHEMA_VERSION`；`real_model.py:342-346` 写入载荷；`src/pathway_v43/pollutant/candidate_evidence.py:46-48`（常量）、`candidate_evidence.py:265-283`（v1 底物卡 descriptor） | `test_p2_v1card_mode.py:169-179`；探针 `v1card` 身份 strategy 字段（`candidate-evidence-2` / `descr-2`） | **满足** |
| 2d | JSON 分隔符 = 默认（与 v1 B 逐字节同），不得用 v2 B 紧凑分隔符 | `real_model.py:355-364`：紧凑分隔符仅在 `substrate_evidence` 在位且 `schema_version == candidate-evidence-3` 时触发；`v1card` 传 v1 schema ⇒ 走默认 | `test_p2_v1card_mode.py:182-185`（A 载荷等于默认 `json.dumps`，含 `", "`/`": "`）；`test_p2_v1card_mode.py:139-160` 与 v1 B 逐字节；探针 `v1card_payload_equals_v1_b_bytes` | **满足** |
| 3 | `evidence_card_enabled` 在 `v1card` 下必须为 true；false ⇒ 结构化拒 | `runflow.py:1934-1943`（`_require_v1card_evidence`，kind=`v1card_requires_evidence`）；start 在 `runflow.py:2000-2005`（建目录前）、resume 在 `runflow.py:2157-2160` 调用 | `test_p2_v1card_mode.py:314-330`：start 拒绝且不留空目录；v1card run 的 resume 传 false 同样拒 | **满足** |
| 4a | identity：`strategy.evidence_card_version="v1card"`；schema/descriptor=v1 | `runflow.py:1854-1872`（`_v1card_identity_fields`，含 `rdkit_version`）；`runflow.py:1897-1900`（仅 v1card 追加） | `test_p2_v1card_mode.py:240-256`；探针 `identity_strategy` | **满足** |
| 4b | `prediction.prompt_versions.proposals` = v2 SHA | `runflow.py:1946-1959`（v2/v1card 均替换为 `proposals_prompt_version("v2")`） | `test_p2_v1card_mode.py:255-256`、`263-265`（A/B 同为 v2 哈希）；探针两臂 `prompt_versions.proposals=89311fdb…0f37`（历史探针值，chemfix 前）；**集成后 v1card 探针使用 `c24bee42…7598`**（chemfix 改 v2 prompt；本行历史值不回写） | **满足** |
| 4c | resume 以同判据核对，缺失/不符 ⇒ `evidence_card_version_mismatch` | `runflow.py:2161-2182`：保存值合法性（非法 ⇒ `evidence_card_version_corrupt`）、`saved_version != current` ⇒ mismatch、按当前 schema/descriptor/RDKit 重算身份字段 | `test_p2_v1card_mode.py:351-400`：v1card run 用 None/v1/v2 resume 均 mismatch；v2 run 用 v1card resume mismatch；身份内坏值 corrupt；同版本正常续跑 | **满足** |
| 5 | off 路径（缺省/None/`v1`）零漂移：prompt/schema/descriptor/payload/identity/summary 不变 | `runflow.py:1889-1901`（strategy 无新键）、`2073-2076`/`2255-2258`（summary 仅 v2/v1card 加键）、`real_model.py:1020-1024`（缺省 v1 prompt）、`real_model.py:360-364`（off 不触发紧凑） | `test_p2_v1card_mode.py:275-308`；`off_path_compare.json` 15/15 true；本次复跑 `off_path_after.json` 与保存件逐字节同；A/B 载荷 SHA 与基线同 | **满足**（code identity 变化为预期，见 §6 注） |
| 6 | 测试覆盖：A 载荷与 v1 B 逐字节等价；v2 prompt 哈希不变；A/B 身份键；resume 拒错；双跑字节一致；v1 证据函数未被改 | 测试文件 `tests/test_p2_v1card_mode.py` 全文；v1 证据函数零删除（patch1 对 `candidate_evidence.py` 为 +397/−0） | 逐项对应：`139-185`、`210-218`、`240-272`、`351-400`、`406-423`、`219-234` + 探针 | **满足** |
| 7 | 复审：改变证据卡身份/载荷语义，必须 Codex/qwen 复审 + 化学复审引用；未复审不签字、不发车 | 本报告 §8 | 程序面复审 **PASS**（qwen3.8max 代 Codex，`docs/QWEN_P2_AB_REVIEW_2026-10-21.md`）；化学复审**未执行**；预注册 §2.5 已披露“v2 prompt 描述 v2 字段、A 臂 v1 卡无这些字段”是 treatment 的一部分 | **程序面闭合；化学复审待办（非代码缺口）** |

### 2.1 补充说明（合同解释边界）

- **“缺失”判据**：v1card run 的 resume 若不传版本参数（默认 `None`）⇒
  `evidence_card_version_mismatch`；历史 run（身份无该键）以 `None` resume 仍允许，
  这是为旧路径保留的兼容读取，不是 v1card 的放行口。
- **“其它非法值仍拒”**：`_resolve_evidence_card_version` 对 bool/非字符串/近似拼写
  一律 `evidence_card_version_invalid`；未新增任何静默回退。
- **第 3 条与第 4 条的关系**：`v1card` + `enabled=false` 在身份核对之前即拒，不会留下
  半初始化 run；resume 侧同样先拒，再读保存身份。

## 3. 设计变更 provenance（M2）

> 本节是 qwen3.8max 代 Codex 复审（`docs/QWEN_P2_AB_REVIEW_2026-10-21.md`）指出的
> **唯一文档缺口 M2** 的补记。**只改文档，不改代码/测试**；与复审对象版本
> `3cf879e7…19c3` 相比，代码/patch/证据零变化（该哈希是复审时报告文本哈希，
> **非持久化/逐轮易变**，本补记后文件哈希已变）。

| # | 事实/披露 | provenance |
|---|---|---|
| 1 | **冻结设计原文的 A 臂不是 `v1card`**：`docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1 写的是「A 臂=**用户 JSON 字节兼容回退**」（r2 实现为 v2 prompt + 无证据），不是「v2 prompt + v1 卡」。 | 冻结设计原文；`docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md` §2.1（M2） |
| 2 | **本次实现把 A 臂定为 `v1card`（v2 prompt + v1 证据卡），这是对冻结设计的变更**，不是「按原设计实现」、也不是「回到原意」。变更依据是 CC 2026-10-21 的决定与预注册 §2.3/§2.5；本报告按**变更路径**记录，不写成原设计实现。 | `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md`（CC 决定原文**不含**「A=v1 卡」字样）；`docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md` §2.1（M2）；任务书 `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` §3.3；预注册 §2.3/§2.5 |
| 3 | **披露：生产中从未存在过「v2 prompt + v1 卡」这个组合**（生产 v1 = v1 prompt + v1 卡）。因此本批读数是「**v2 prompt 语境下 v2 卡 vs v1 卡**」，**不是完整的生产替换效应**；不得在结果报告中丢失该限定。 | qwen confirm §2.1 披露条；预注册 §2.5/§10 |
| 4 | **provenance 链**：CC 决定 `docs/P2_CC_DECISION_FULL_V2_2026-10-21.md` → qwen3.8max 代 Codex 确认/条件 `docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md` §2.1（M2）→ 任务书 `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` §3.3 → 本实现/报告。**本报告不代签、不伪造 CC 签字**；CC 签字文本必须显式落「A 臂=v1card（v2 prompt + v1 卡）」，补齐授权链。 | 上述三件文书 |

## 4. 改动文件与补丁结构

### 4.1 基线与 worktree

| 项 | 值 |
|---|---|
| 基线 commit | `11aeeafded1b41185f24de49767933709aad49db` |
| worktree | `/private/tmp/dependingv43_p2_v1card`（detached at 基线） |
| 主树 | `/Volumes/CC/Enzyme_Agent/dependingv43` 仅新增本报告与 evidence；`src/`/`tests/` 未改 |
| 环境 | Python 3.11.16、RDKit 2026.03.6、pytest 9.1.1（`environment.json`） |

### 4.2 补丁结构与 apply 顺序

| 件 | 文件/行数 | SHA-256 | 说明 |
|---|---|---|---|
| `patch1_impl_r2.patch`（基线） | 4 文件 +1225/−45；1,546 行 | `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6` | v2 实施 r2（与任务书 §3.2 期望 SHA 一致）；`candidate_evidence.py` +397/−0、`real_model.py` +108/−10、`runflow.py` +163/−35、`test_p2_evidence_card_v2.py` +557/−0 |
| `patch2_v1card.patch`（增量） | 2 文件 +512/−29；671 行 | `09414e26af89b3c12a7d3a37a60ddfeef1f3c006049badd427743c948338269e` | v1card：`runflow.py` +89/−29（resolver/身份/拒错/接线）、`tests/test_p2_v1card_mode.py` +423/−0 |
| `impl.patch`（合并） | 5 文件 +1713/−50；2,061 行 / 99,570 字节 | `bb2485da5534a2af19fca2bb53fdac2243633a21845aff78e1a370988d503f42` | patch1+patch2 的最终树 diff（含两个测试文件） |

**apply 顺序与验证（本次复跑）**：

1. 从 `11aeeaf` 执行 `git archive` 取干净副本；
2. `git apply --check patch1` → apply → `git apply --check patch2` → apply：全部 OK；
3. 应用后 5 文件 SHA-256 与 worktree、`environment.json` 全等；
4. 另测 `impl.patch` 单独应用：`--check`/apply OK，产物哈希同上。

### 4.3 文件 SHA-256（与 environment.json 吻合）

| 文件 | SHA-256 |
|---|---|
| `src/pathway_v43/pollutant/candidate_evidence.py` | `6ce2772f716dfbefa3982cdf50992d01b5d0984afcc71751cbc5338ab0124560` |
| `src/pathway_v43/pollutant/real_model.py` | `4772e90a459ec43ab4e4fa41ff040851ed34efb3db7233c6e73f1153fce83c20` |
| `src/pathway_v43/pollutant/runflow.py` | `a26801f722825bf2ef666cf4f89e955feff5c102beb2eafc9aa8e9f8d0ec529c` |
| `tests/test_p2_evidence_card_v2.py` | `c102ceff6bd778b5c163ebf90fd5162b5194d786deb06bc1510dad0c3dadeb8d` |
| `tests/test_p2_v1card_mode.py` | `4300d5b815350ea98da2fcfe1baf431a320fdbe3435c5d6f3a60eb78b90857f9` |

### 4.4 边界确认

- `docs/T_I_SCRIPT_LOCK_2026-10-20.json` 的 14 件锁定文件中，`impl.patch` 路径交集为 0；
- T-I 树/`v43cTH`/封存 run/`src` 主树零改动；未 push；
- 本补丁不包含 schema-4/descr-4、`evidence_truncation`、帽表或截断等级（沿用任务书否决项）。

## 5. 测试数字与命令原文

### 5.1 本次自检实际执行（轻量复现）

```bash
cd /private/tmp/dependingv43_p2_v1card
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python -m pytest \
  tests/test_p2_v1card_mode.py tests/test_p2_evidence_card_v2.py \
  -q -p no:cacheprovider
# 28 passed in 4.94s
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_v1card_2026-10-21/v1card_probe.py \
  --src /private/tmp/dependingv43_p2_v1card/src --out <tmp>/v1card_probe_result.json
# 输出 JSON 与保存的 v1card_probe_result.json 逐字节相同（cmp OK）
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/p2_v1card_2026-10-21/off_path_probe.py \
  --src /private/tmp/dependingv43_p2_v1card/src --out <tmp>/off_path_after.json \
  --runs-root <tmp>/runs
# 输出 JSON 与保存的 off_path_after.json 逐字节相同（cmp OK）；
# 以 off_path_baseline.json 重算 15 项检查全 true
```

### 5.2 既有日志（随证据保全，本次未重跑全量）

| 日志 | 结果 | 说明 |
|---|---|---|
| `pytest_v1card_targeted.log` | `28 passed in 5.55s` | 实施期定向（v1card 10 + v2 18） |
| `pytest_related.log` | `174 passed in 88.23s` | 相关既有批 |
| `pytest_not_slow.log` | `2362 passed, 16 deselected in 411.31s` | 全量 not-slow（收集 2378） |

> 诚实说明：保存的三个日志文件未内嵌 shell 命令行；上表数字是日志原文。
> 本次自检只重跑定向与两个探针（任务要求不重跑 7 分钟全量），全量结论以保存日志为证。

### 5.3 测试覆盖对照（§3.3 第 6 条）

| 合同要求的测试 | 测试函数（行号） | 结果 |
|---|---|---|
| A 用户载荷与 v1 B 逐字节等价（system prompt 除外） | `test_v1card_user_payload_byte_identical_to_v1_b`（139-185） | pass |
| v2 prompt 哈希不变 | `test_v2_prompt_hash_unchanged_and_v1_evidence_frozen`（210-218） | pass |
| A/B 身份键 | `test_arms_identity_keys`（240-272） | pass |
| resume 拒错（缺失/换版本/坏值） | `test_v1card_resume_version_gate`（351-400） | pass |
| 双跑字节一致 | `test_v1card_double_run_byte_identical`（406-423） | pass |
| v1 证据函数未被改 | `test_v2_prompt_hash_unchanged_and_v1_evidence_frozen`（219-234，锚 `61cd96a9…8960`/`18a62e52…75d3`）+ `candidate_evidence.py` +397/−0 | pass |
| 附加：v1card + false 结构化拒 | `test_v1card_requires_evidence_enabled_true`（314-330） | pass |
| 附加：非法版本值仍拒 | `test_invalid_version_values_still_rejected`（333-348） | pass |
| 附加：off 身份/summary 无新键 | `test_off_path_identity_and_summary_have_no_v1card_keys`（275-289） | pass |
| 附加：off 载荷哈希锚 r2 基线 | `test_off_path_payload_hashes_match_r2_baseline`（292-308） | pass |
| 附加：v2 B 臂未被接线扰动 | `test_arms_share_v2_prompt_but_v2_arm_payload_unchanged`（188-204） | pass |

## 6. 零漂移证据摘要

### 6.1 off 路径 15 项检查（`off_path_compare.json` + 本次重算）

| # | 检查 | 结果 |
|---|---|---|
| 1-4 | A 臂 payload 字节/SHA、summary 键集、system prompt SHA | true |
| 5-8 | B 臂 payload 字节/SHA、summary 键集、system prompt SHA | true |
| 9-10 | v1 候选证据值/SHA 相同 | true |
| 11 | off 两侧均无 `evidence_card_version` summary 键 | true |
| 12-13 | v1 prompt 字节 SHA/字符串相同 | true |
| 14-15 | v1 底物证据值/SHA 相同 | true |

### 6.2 载荷 SHA 前后对照

| 口径 | 基线 | 实施 | 结论 |
|---|---|---|---|
| off A（v1 prompt，无证据） | `c2526a7fb47b43dc08ca5422d01787456581777ed4014087aece2c09bce1799d` | 同 | 逐字节一致 |
| off B（v1 prompt，v1 卡） | `b8f66ed9367c4325fc48ec07aec96ceb0d32c2fd215fd856deb2851a4621981e` | 同 | 逐字节一致 |
| v1 B（v1 prompt + v1 卡） | — | `e00f3b40b33f9c3eafdbf5c99e146afd159332060cf0a20d0524167c3092ba0d` | v1card A 同值 |
| v1card（v2 prompt + v1 卡） | — | `e00f3b40b33f9c3eafdbf5c99e146afd159332060cf0a20d0524167c3092ba0d` | 与 v1 B 逐字节同 |
| v2 B（v2 prompt + v2 卡） | — | `a973817925c9c8636ba1b24e1d901d8a6f1047efec6ac4a2a67c588efb0e7be4` | 紧凑分隔符，未受影响 |

### 6.3 identity 差异白名单（如实登记）

`off_path_compare.json` 的归一 diff 仅限：

1. `asset_identity.assets_root` 的 worktree 路径标签（环境差异，非语义）；
2. `code_identity` 的聚合哈希与 3 个白名单源文件（`candidate_evidence.py`、`real_model.py`、`runflow.py`）——
   这是任何代码补丁的必然结果，不是 off 行为漂移；
3. `strategy`/`prediction`/`summary` 键集零新增；off 路径无 v1card/v2 键。

**结论：off 路径 prompt/schema/descriptor/payload/identity 语义/summary 零漂移。**

## 7. unknown / 未覆盖项（诚实登记）

| # | 项 | 状态/影响 |
|---|---|---|
| 1 | Codex/qwen 程序面复审 | **已 PASS**（qwen3.8max 代 Codex，`docs/QWEN_P2_AB_REVIEW_2026-10-21.md`）：§3.3 第 1-6 条实核、28 定向 + 两探针 + off 15 项独立复现、v1 证据函数 +397/−0。**正链 Codex 复核待额度**；化学复审未做，未闭合前不签字、不发车（§3.3.7）。 |
| 2 | 化学复审 | **未执行**。`docs/TASK_P2_V2_CHEM_REVIEW_2026-10-21.md` 仍是“待执行”；v1card 作为独立臂（v2 prompt + v1 卡）必须被该复审显式覆盖，不能被 v2 字段评审替代。 |
| 3 | 操作链（§3.4，patch 3） | **未实现**。`s5b_worker.py`/`s5b_orchestrator.py` 当前不传 `evidence_card_version`；用既有 worker 跑 v1card 会**静默落回 off 路径**。本补丁只到 `runflow` 直连入口，发车前必须补 patch 3 并复审。 |
| 4 | `v1card` + `model=None` 边界 | 被接受：`_prediction_block(None, "v1card")` 返回 `enabled=false` 空 `prompt_versions`，不记录 v2 prompt 哈希；因无模型调用，不产生载荷。合同未定义该组合。qwen 复审 F5 已实测：不可经操作链到达，带模型 resume 被 `IdentityMismatch` 拒、不能洗成真实 run；建议下一轮补丁 fail-closed 或在脚本锁登记为「未定义组合，仅直连可达」，非阻塞。 |
| 5 | token 对照（同 prompt 的 v1 卡 vs v2 卡） | **未实测**。预注册 §2.5 明确要求重测；v2 B 的紧凑分隔符只作用于 B 臂，A 臂 v1 卡载荷更大，token 差可能大于 r2 的 v2 vs v2-A 读数。不得用 r2 的 token 数字代替本批 A/B。 |
| 6 | 真实池形状/真实模型 | **未覆盖**。载荷等价、off 漂移、身份/续跑均用 scripted 桩与单一合成池条目（与 r2 基线同一输入）；真实 298 池形状、反馈轮、超时/重试路径未在真实模型下演练。代码结构上 v1card 与 v1 B 共用同一载荷组装路径，但“所有真实池形状逐字节等价”仍是推断，不是实测。 |
| 7 | 格式反馈轮的 v1card 专项测试 | 未单列。反馈轮走同一 `_call_real_fetch`，`fetch_kwargs` 同样生效；v2 测试覆盖紧凑分隔符条件。建议复审时确认反馈轮沿用 v1 schema/默认分隔符。 |
| 8 | 全量 not-slow | 本次未重跑（按要求）；以 `pytest_not_slow.log` 的 2362 passed/16 deselected 为证。 |

## 8. 复审注意点

1. **这是改变证据卡身份/载荷语义的改动**：新增 `v1card` 版本值、v2 prompt 与 v1 卡的
   组合、身份字段与 resume 门。**程序面复审已 PASS**（qwen3.8max 代 Codex，
   `docs/QWEN_P2_AB_REVIEW_2026-10-21.md`）；化学复审仍未做、正链 Codex 复核待额度。
   复审结论须按预注册 §2.5 写进脚本锁；**化学复审/正链复核未闭合前不签字、不发车**。
2. **化学复审引用**：`docs/TASK_P2_V2_CHEM_REVIEW_2026-10-21.md`（待执行）必须把
   `v1card` 作为独立臂登记，核对“v2 prompt + v1 卡”的语义一致性（v2 notes 描述 v2 字段，
   A 臂 v1 卡没有这些字段且带 v1 独有字段）。预注册 §2.5 已把该“Prompt-卡语义不匹配”
   披露为 treatment 的一部分，**不是隐藏变量**；不得据此把 A/B 差异读成单字段因果。
3. **单变量口径**：两臂共享 v2 prompt、v2/v1 卡差异 + 默认/紧凑分隔符差异是设计的一部分；
   审稿时不要把分隔符差异误读为证据字段差异（预注册 §2.5 与 r2 报告 §10.1 已披露）。
4. **重点核对项**：
   - `_resolve_evidence_card_version` 的非法值 fail-closed（含 bool/近似拼写）；
   - `v1card` + `false` 在 start/resume 均结构化拒，且不留空 run 目录；
   - A 载荷与 v1 B 逐字节等价 + 默认分隔符；
   - identity 的 `v1card`/v1 schema/descr/v2 prompt/rdkit_version 五元组；
   - resume 缺失/换版本/坏值的三类结构化错误；
   - off 路径 15 项与 payload SHA 前后相同。
5. **发车前还需**：patch 3 操作链接线、脚本锁、token 重测（v1 卡 vs v2 卡，同 prompt）、
   化学复审结论、CC 付费/HPC 授权。本报告不代签任何一项。

## 9. 交付物

| 交付 | 路径 | SHA-256 |
|---|---|---|
| 本报告 | `docs/T_P2_V1CARD_IMPL_2026-10-21.md` | 报告在证据目录外，不纳入该目录 `SHA256SUMS`；证据件哈希见该文件 |
| v2 基线补丁 | `docs/review_evidence/p2_v1card_2026-10-21/patch1_impl_r2.patch` | `cd8c03e0a7ebc41e95ad7a1b9f323bda4a48caf3910373039c50f6ce6f9ebbd6` |
| v1card 增量补丁 | `docs/review_evidence/p2_v1card_2026-10-21/patch2_v1card.patch` | `09414e26af89b3c12a7d3a37a60ddfeef1f3c006049badd427743c948338269e` |
| 合并补丁 | `docs/review_evidence/p2_v1card_2026-10-21/impl.patch` | `bb2485da5534a2af19fca2bb53fdac2243633a21845aff78e1a370988d503f42` |
| v1card 探针/结果 | `.../v1card_probe.py` / `.../v1card_probe_result.json` | 见 `SHA256SUMS` |
| off 路径探针/前后件 | `.../off_path_probe.py` / `off_path_after.json` / `off_path_compare.json` | 见 `SHA256SUMS` |
| 测试日志 | `.../pytest_v1card_targeted.log` / `pytest_related.log` / `pytest_not_slow.log` | 见 `SHA256SUMS` |
| 环境/自检日志 | `.../environment.json` / `selfcheck_contract_2026-10-21.log` | 见 `SHA256SUMS` |

**一句话给 CC：** `v1card` 按 §3.3 第 1-6 条做完了、合同没缺口，定向 28 绿、探针复跑
逐字节一致、off 路径零漂移；程序面复审已 PASS（qwen3.8max 代 Codex），但化学复审
还没做、正链 Codex 复核待额度、操作链还没接、token 还没按“v1 卡 vs v2 卡”重测——
**可进入化学复审/发车前准备，仍不适合签字发车**。