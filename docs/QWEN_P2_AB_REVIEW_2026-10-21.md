# qwen3.8max 代 Codex 复审（不替代正链 Codex 最终裁定权），按 CC 2026-10-21 指示 — P2 A/B 两路交付独立复审（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只评程序/合同面，
> 不评化学机制、不评科学性能；合成探针读数不外推为真实 298 分布或任何收益。
>
> **Provenance：** 复审人 = qwen3.8max（Codex 无额度期间代 Codex 执行程序面复审；
> 放行/冻结类结论待正链 Codex 额度恢复后复核确认）。复审对象与身份：
>
> | 件 | SHA-256 |
> |---|---|
> | 任务书 `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `d47dae5dda50aa8f3906138914c8174c1456c7d24350bc4afb053b0b6307067f`（与 A 报告/environment.json 记录一致） |
> | A 路报告 `docs/T_P2_V1CARD_IMPL_2026-10-21.md` | `3cf879e7a205f1a10c2c25c5e29d83cc641b8604d6d844571db0546d787f19c3` |
> | B 路报告 `docs/T_P2_OPS_CHAIN_IMPL_2026-10-21.md` | `9d38ae655c003adf0c43a0ad668dcb29bc3bde3db4098cd5558caf6ec3ebfbf0` |
>
> 复审环境：主树 HEAD 实测 `11aeeafded1b41185f24de49767933709aad49db`（=声称基线）；
> Python 3.11.16 / RDKit 2026.03.6 / pytest 9.1.1（`/Users/cc/miniconda3/envs/depending43`，
> 与两路 environment.json 一致）；隔离 worktree `/private/tmp/qwen_review_p2`
> （`git worktree add --detach … 11aeeaf` 新建）；复审产物 `/private/tmp/qwen_review_p2_evidence/`。
> 本复审零模型调用、零网络、零 HPC、零金标/题面/reference_graphs/env/key 读取、不 push；
> 主树与两路证据原件、两路工作树均未改动（对 A/B 工作树只读；探针只写 tmp）。
> 按任务红线「唯一允许写入的是报告文件」，本文件是仓内唯一新增件；复审复跑证据留在
> `/private/tmp/qwen_review_p2_evidence/`（§9 给归档命令，是否入仓归 CC）。

## 1. 总裁定

| 路 | 裁定 | 一句话 |
|---|---|---|
| **A：`v1card` 模式（patch1+patch2 / impl.patch）** | **PASS**（§3.3 第 1–6 条合同面） | 七条合同逐条实核成立；我在隔离树独立复现全部关键证据且逐字节一致；未发现合同缺口。第 7 条（复审+化学复审引用）中程序面复审=本报告，化学复审仍未做，签字/发车门不变。 |
| **B：P2 操作链（patch_ops_chain + 8 个操作文件）** | **CONDITIONAL PASS** | 代码/配置/正负控全部实核成立（77/77 在隔离树独立复现、W0=0 经我逐 hunk 人工复核、T-I 14 件锁定文件四树全未动）；但 **B 报告有 2 处 SHA 数字与保存证据不符（must-fix，文档级）**，且部署序列（任务书 §3.5「补丁 1→2→3」）与交付补丁形态（单一全量组合补丁）不一致，须在脚本锁/部署文书写明后再进入部署。 |

两裁定都**不等于放行发车**：任务书 §0 清单（模型选定、预注册签字、化学复审、脚本锁、
soak、付费授权等）与 §3.3.7 复审门全部仍然有效，本报告只闭合其中「程序面复审」一格，
且待正链 Codex 复核确认。

## 2. 验收面（固定，不扩边）

按 CC 指令固定为：①补丁序列可应用性与产物 SHA；②A 路 §3.3 七条合同；③B 路 §3.4
操作链合同 + §4.2 克隆白名单（W0=0）+ 77 项正负控抽查复现；④两路互不污染；⑤红线
（金标/题面/env/key/HPC/T-I 锁定件/主树）；⑥报告数字与证据逐项对账。科学性能、化学
语义、token/费用、部署与 HPC 侧检查**不在本验收面内**，其 pending 状态如实转记（§7）。

## 3. 我独立复现了什么（区别于「只看了日志」）

全部在 `/private/tmp/qwen_review_p2`（基线 11aeeaf 干净 worktree）+ tmp 输出目录执行：

| # | 复现项 | 结果 |
|---|---|---|
| R1 | `patch1 → patch2` 顺序 apply | OK；应用后 5 文件 SHA 与 A 证据 environment.json 全等 |
| R2 | `impl.patch`（patch1+2 合并）单独 apply 于干净 11aeeaf 归档 | OK；5 产物 SHA 全等（`6ce2772f…`/`4772e90a…`/`a26801f7…`/`c102ceff…`/`4300d5b8…`） |
| R3 | `patch_ops_chain_2026-10-21.patch` 单独 apply 于干净 11aeeaf | OK；15 产物（5 src + 8 scripts + 2 tests）SHA 与 B 报告 §1/environment.json **逐一全等** |
| R4 | ops 补丁叠加在 patch1+patch2 之上 | **FAIL（does not apply）** —— 它是全量组合补丁（含 patch1+2 内容），不是增量 patch3；见发现 F2 |
| R5 | 定向测试 `test_p2_v1card_mode.py + test_p2_evidence_card_v2.py` | **28 passed（5.20s）**，与报告一致（10 v1card + 18 v2，函数计数核实） |
| R6 | **全量 not-slow**（组合树） | **2362 passed, 16 deselected, 1 warning（387.33s），EXIT=0** —— 与 A 日志（411.31s）/B 日志（401.32s）数字一致 |
| R7 | `v1card_probe.py`（--src 指 A 工作树） | 输出与保存件**逐字节同**（SHA `41d5f2c3…` 双侧一致）；7/7 checks true；A 载荷=v1 B 载荷=`e00f3b40…ba0d`；resume 同版本过、换 v2 拒 `evidence_card_version_mismatch` |
| R8 | `off_path_probe.py`（--src 指 A 工作树） | 输出与保存 `off_path_after.json` **逐字节同**（SHA `abcea2a4…`）；另**手工重算**基线（r2 证据 `off_path_baseline.json`，在位）vs 我的 after：A/B payload SHA、system prompt SHA、summary 键集、v1 prompt/证据/底物卡值+SHA、归一 identity 哈希全等；两侧 summary 均无 `evidence_card_version` 键 —— off 15 项的底层事实全部独立成立 |
| R9 | `probe_ops_controls.py` 隔离副本（重定向到我的树 + T-I 锁一致的 ti_operations 参考副本） | **77/77 全过、exit 0、stderr 空**；与保存结果逐 check 对比：名称集一致、ok 值零差异；7 处 detail 差异全部只是随机 tmp 路径及其派生哈希；C1 旧批汇总 SHA **精确复现 `b2ccb10d…490`**（与主树未打补丁 summarize 逐字节同）；C3 全部 14 项拒错 + 桩件模型调用 0；C4 假 sbatch 下 marker 全程不存在（干跑不 sbatch、不写状态、squeue 幂等、结束需 --resume、二败停、pending_submission 禁盲重投、flock 单发车锁生效）；C5 stop.json 首写生效且第二写不改字节；C7 11 常量 + 20 冻结函数归一后逐字同 |
| R10 | ti→p2 diff 独立重算 | 75 hunk；我的 diff 与保存 `diff_ti_vs_p2_operations.diff` **正文逐字节同**（仅文件标签路径不同）；`diff_whitelist_hunks.json` primary 计数 = W1 29 / W2 10 / W3 11 / W4 17 / W5 1 / W6 7 / **W0 0**，与审计表一致；**75 个 hunk 我全部人工过目**（含最大的 hunk 51 verify_identity/build-copy +234 行、hunk 24 approval 语义、hunk 52–58 launch），归类无异议；冻结面（阈值/fatal 分类/恢复一次二败/barrier/monitor/stop 首写/seal/评分版本/gate 默认）未见任何改动，`phase_guard`（不在 C7 冻结函数清单内）体变更仅为命名 + 证据卡参数透传 |
| R11 | T-I 锁定 14 件 | 主树/A 树/B 树/我的树四处逐件对锁 SHA：tracked 件全 OK；worktree 缺失件（3 docs + 7 ti 脚本，11aeeaf 未跟踪）在 B 树的参考副本与锁 SHA 全等；唯一「不符」= `s5b_compiler.py`（锁值 `f917762b…` 定在 c9c6c7a，四树实测 `58cf3dc9…` = 11aeeaf 含 P0b +21 行）——见 F7，属基线演进非篡改 |
| R12 | `v1card + model=None` 实测 | start 被接受：strategy 记 `v1card`+v1 schema/descr，但 `prediction.enabled=false`、`prompt_versions={}`（无 v2 哈希）；带模型 resume ⇒ **IdentityMismatch 拒**（不可洗成真实模型 run）；`model=None` 同版本 resume ⇒ 接受。与 A 报告待决点 #4 描述一致 |
| R13 | 我自设的额外负控（非交付方提供） | `n_questions=297` 拒；`v3_default=true` 拒；臂 batch_name 非 `p2_298_*` 拒（顺带挡住 immutable 名冲突）；`mutable()` 对 immutable 批名与已封存批根拒；批级 `normalize_evidence_card_version` 对 `"v1"`/`"V1CARD"`/`""`/`1`/`True` 全部结构化拒（批级不接受 `"v1"` 别名，比 runflow 更严，防错臂——设计如此且有注释） |
| R14 | A/B 互染检查 | A 树（patch1+2）与 B 树（ops 补丁）与我的 R3 重建，5 个共享文件（runflow/real_model/candidate_evidence + 2 测试）**逐字节一致**；A 树无 orchestrator/worker/p2 脚本改动；B 树 src/tests 与我的重建 diff 为空；两证据目录 SHA256SUMS `shasum -c` 全 OK |

**只核对日志、未独立复跑：** A 的 `pytest_related.log`（174 passed/88.23s）；A 树自身的
not-slow（我在**组合树**复跑了 R6，A 树是其子集，未单独再跑一遍）；A 的
`pytest_v1card_targeted.log`（28 passed/5.55s，与我 R5 数字一致）；B 的
`pytest_p2_targeted.log`（28 passed/9.54s）与 `pytest_not_slow.log`（数字与 R6 一致）；
A 的 selfcheck 日志（内容与我 R1/R5/R7/R8 复现逐项吻合）。

**无法核实（unknown）：** HPC 部署树/真实 slurm/真实 sbatch 行为；部署 RDKit 2026.03.5
对齐与 v2 确定性锚；真实 298 build/池形状下的 build-copy/verify_identity 实跑；真实模型
载荷与 token；化学复审、预注册签字、正链 Codex 复核（均未发生）；B 报告中两个陈旧 SHA
的原始出处（见 F1，推测为实施期早一轮探针输出，未保存，无法核对）。

## 4. A 路 §3.3 七条合同逐项核验

| # | 合同 | 裁定 | 关键证据（我实核） |
|---|---|---|---|
| 1 | resolver 接受 `"v1card"`，其它值拒 | **通过** | `runflow.py:1919-1931` 实读；测试覆盖 `V1CARD/v1-card/v1_card/v3/""/1/True` 全拒且建目录前拒；R5 全绿 |
| 2 | v2 prompt + v1 卡 + v1 schema/descr + 默认分隔符 | **通过** | `runflow.py:1440-1474` else 分支复用 v1 纯函数、仅换 system prompt 与传 v1 schema 常量；`real_model.py:355-364` 紧凑分隔符条件要求 schema==v2 常量，v1card 不触发；R7 探针 `v1card_payload_equals_v1_b_bytes=true`，载荷 SHA `e00f3b40…ba0d` 双侧同；测试断言原始字符串相等 + `", "`/`": "` 在位 |
| 3 | `v1card`+false 结构化拒 | **通过** | `_require_v1card_evidence`（kind=`v1card_requires_evidence`）在 start `runflow.py:2000-2005`（建 run 目录前）与 resume `2157-2160` 均先于身份核对调用；测试双向覆盖 |
| 4 | identity/resume | **通过** | `_v1card_identity_fields`（version/schema/descr/rdkit 五元组）只在 v1card 追加；`_prediction_block` 对 v2/v1card 替换 proposals=v2 哈希（`89311fdb…0f37` 两臂同值，R7 核实）；resume 三态拒错（缺失/换版 mismatch、身份内坏值 corrupt）实测成立（测试甚至篡改身份文件证 corrupt 路径）；**重算身份不能洗版本**：saved≠current 先拒，带模型跨身份 resume 实测 IdentityMismatch（R12） |
| 5 | off 路径零漂移 | **通过** | R8：payload/prompt/证据/summary 键集/归一 identity 与 r2 基线全等；identity 白名单差异仅 assets_root 路径标签 + code_identity 聚合/3 个被改源文件（任何补丁的必然结果，如实登记）；`_strategy_block` None 时无新键 |
| 6 | 测试覆盖 | **通过** | 10+18=28 函数计数核实；六项合同要求测试逐一对应到函数并在我环境全绿；v1 证据函数「未被改」有硬证据：patch1 对 `candidate_evidence.py` numstat **+397/−0（零删除=纯新增）**，且 v1 输出锚（`61cd96a9…`/`18a62e52…`）测试通过 |
| 7 | 复审门 | **部分闭合** | 程序面复审=本报告（PASS）；**化学复审未做**（`T_P2_V2_CHEM_REVIEW_2026-10-21.md` 未落盘），且须显式覆盖「v2 prompt + v1 卡」独立臂；正链 Codex 复核待额度。未闭合前不签字不发车 |

A 报告行号引用抽查（resolver/require/identity/prediction/start/resume/summary/real_model
各处）与实测行号一致；补丁行数/字节数/numstat（1546 行、671 行、2061 行/99,570 字节、
+1225/−45、+512/−29、+1713/−50）全部对账吻合。

## 5. B 路 §3.4/§4.2 验收核验

| 验收 | 裁定 | 证据 |
|---|---|---|
| orchestrator：版本参数/合法值/非 None 要求 enabled | 通过 | `normalize_evidence_card_version` + `require_evidence_card_version_enabled` 实读；R13 负控全拒 |
| 冻结副本仅非 None 写键；旧批零新键 | 通过 | 条件写键实读；C1 旧批汇总与主树逐字节同（`b2ccb10d…` 我精确复现）；「键的在场/缺席本身是批身份」双向锁死（旧批不得升级、版本批不得被 None 洗掉）——`s5b_orchestration_conflict` |
| worker argv/case 披露/失败路径披露/fail-closed 零调用 | 通过 | worker diff 全读：可信上下文缺冻结键拒（`frozen_copy_missing`）、换臂拒（`mismatch`）、非法值拒（`invalid`）、版本+false 拒（`disabled`）；全部失败 case 带版本字段；C3 桩件计数 0 |
| 批终态报告非 None 写版本、写前对冻结副本复核 | 通过 | `reported_version != evidence_card_version ⇒ fail-closed 不写错账报告` 实读 |
| summarize/validate 对旧批拒绝意外版本键 | 通过 | `validate_case`：expected None 时 case 出现该键 ⇒ `evidence_card_version_unexpected` 拒（防跨臂污染） |
| §7.4 停派发（T-I C6 语义） | 通过 | orchestrator 新增 `stop_check` 回调（默认 None 完全不变、报告零新键）；`p2_run_wrapper.py` 的 `dispatch_stop_check` 收割 fatal ⇒ write_stop(cancel=True) ⇒ 停新派发；部署 orchestrator 不支持版本参数时 wrapper **fail-closed**（消除 A 报告待决 #3 的「静默落回 off 路径」风险） |
| §4.2 克隆白名单 W0=0 | 通过 | R10：75 hunk 全人工过目 + 机读分档复核 + C7 常量/冻结函数门（我复跑） |
| stop.json 不可覆盖 | 通过 | 全文件唯一写点在 `write_stop` 的 `.stop.lock` 内且 exists 即不写；C5 复现 |
| 双发车防护 | 通过（有一处继承性暴露，见 F3） | flock 单发车 + squeue 活跃幂等 + history 二败停 + pending_submission 禁盲重投，C4 复现 |
| 配置负控 | 通过 | C6 13 项复现 + 我 R13 加测 5 项 |
| 红线 | 通过 | 交付文件 grep 无 reference_graphs/gold/ssh/hpccube/65091；`require_env` 只核权限 600/布尔/模型 ID 同值，不打印内容；探针假 sbatch marker 全程未落（无真调度器接触）；主树 src/tests/scripts 零 tracked 改动；ti_* 14 件未动（R11） |

## 6. 逐项发现（编号/严重度/位置/证据/最小修复）

| # | 严重度 | 发现 | 证据 | 最小修复 |
|---|---|---|---|---|
| **F1** | **P2（must-fix，文档级）** | B 报告引用的 2 个 SHA 与保存证据不符：§0/§4 写 stop.json「SHA 不变 `416926da…`」、§3.2 写旧 run identity「前后同为 `c5ca0640…`」；但证据 `probe_ops_controls_result.json` 里对应值是 `5aa8ddc3…` 与 `bad7ed6a…`，且 `416926da`/`c5ca0640` 在整个 B 证据目录 grep 无命中。这两个哈希含时间戳/路径，**逐轮必变**，报告引用了未保存轮次的数字。语义主张本身（首写不覆盖、identity 前后不变）我已独立复现为真，故只是报告-证据对账缺陷，不是代码缺陷 | 我的 grep + R9 复跑 detail 对比 | 改 B 报告两处：要么引用保存证据中的值并注明「逐轮运行值，以证据文件为准」，要么删具体 SHA 改写不变量（first_sha==second_sha / before==after）。不动代码不动证据原件 |
| **F2** | **P2（must-fix，部署文书级）** | 补丁应用序列不一致：任务书 §3.5 与 A 报告口径是「补丁 1→2→3 顺序 apply」，但交付的 `patch_ops_chain_2026-10-21.patch` 是**对 11aeeaf 的全量组合 diff**（含 patch1+patch2 全部内容），我实测它无法叠加在 patch1+patch2 之上（apply 失败），单独 apply 则产物 15 件 SHA 全对。部署执行人若照任务书顺序操作会当场卡死 | 我的 R4/R3 实测 | 在 P2 脚本锁/部署文书（及对任务书 §3.5 的勘误或下一版修订）写明：**部署 = 11aeeaf 上单次 `git apply patch_ops_chain…patch`**（或另行拆出独立 patch3）；A 侧 impl.patch 仅用于 A 路审计口径。归 CC 认可文书口径 |
| F3 | P3（建议） | 「直投 sbatch 绕过 launch 记账」的暴露面存在：`sbatch_p2_run.sh`/wrapper 不消费 launch 状态文件，prepare 完成后人工直接 `sbatch` 可跑批而不留 jobs/history/pending_submission 记账。这正是 T-I B3 rebatch 的事故形态（锁文件 note 原文：unauthorized direct sbatch bypassing launch）。属**继承自 T-I 的同构暴露**，不违反 §4.2 克隆白名单（克隆语义要求与 T-I 相同）；科学门（stop-check/mutable/no-cap/arm_config/env/barrier/阶段门）直投时仍全部生效 | T-I 锁 relock_b3 note；我对 sbatch_p2_run.sh/wrapper/launch 的实读 | 建议（不代拍）：launch 落一次性「发车票据」文件、wrapper 启动时核销；或 wrapper 核 state["jobs"] 中 SLURM_JOB_ID 匹配。属操作链契约变更，归 CC/正链裁定；若采纳需同步评估是否破坏「冻结克隆」口径 |
| F4 | P3（建议） | approval `source_kind` 从 T-I 单一 `codex_delegated_cc_shijie` 放宽为三类（含 `cc_personal`/`qwen_delegated_codex`）有任务书附录 B 授权，但 T-I 的文案反伪校验（须含"Codex/代"、不得伪填 CC 本人）只在 `codex_delegated_cc_shijie` 分支保留；`cc_personal` 下任何非空 `approval_source/user_authorization` 文本都过机检。机器本来就验不了签字真伪，最终防线是人 | hunk 9/24 实读；B 报告 §8.1 已自报待 CC 确认 | 建议批准包生成时把 CC 书面决定**原文**写入 source_text 并随四文书快照留 SHA；`source_kind=cc_personal` 的真实性由 CC 在签字环节确认（B 报告 §8.1 已列，维持） |
| F5 | P3（建议） | `v1card/v2 + model=None` 在 runflow 直连入口被接受（identity 记版本但 `prompt_versions={}` 无 v2 哈希）。不可经操作链到达（wrapper require_env/require_model、worker 模型装配失败即 fail-closed），且带模型 resume 被 IdentityMismatch 拒、不可洗成真实 run（R12 实测）。v2 分支同病，系 r2 继承而非 v1card 新增 | R12 实测输出 | 建议下一轮补丁在 start/resume 入口对 `version 非 None 且 model None` 结构化拒（fail-closed 加固），或在脚本锁登记为「未定义组合，仅直连可达」。契约解释归 CC/正链，本轮不阻塞 |
| F6 | P3（证据完整性） | `off_path_compare.json` 的**生成脚本未保存**在 A 证据目录（目录里只有 off_path_probe.py），对比逻辑不可原样复跑 | A 证据目录清单 | 我已手工重算全部 15 项底层事实（R8）替代；建议今后对比脚本随证据落盘 |
| F7 | P3（登记，防误判） | `p2_arm_config.json` 的 `scientific_source_sha256.s5b_compiler=58cf3dc9…` 与 T-I 锁的 `f917762b…` 不同：**合法基线演进**——T-I 锁定在 c9c6c7a，P2 基线 11aeeaf 含 P0b 提交对该文件 +21 行（纯新增诊断常量 `P0B_D6_COMPILED_DECLARATION_BOUNDARY` + 一个返回副本的函数；`S5B_COMPILER_VERSION="s5b-compiler-6"` 未变，编译判据未动），与任务书 §3.1「P0b 已合并、P2 不消费/不修改 P0b」一致 | `git diff c9c6c7a..11aeeaf` 实核 | 在 P2 脚本锁/结果报告身份表里登记一句「compiler SHA 与 T-I 锁差异=基线 c9c6c7a→11aeeaf 的 P0b 演进」，防后续审计误判为篡改 |
| F8 | P3（提示） | 两路证据的 not-slow 日志数字同为 2362/16 但时长不同（411.31s vs 401.32s）、targeted 时长不同（4.94/5.55/9.54s）——是不同树不同轮的正常波动，非矛盾；我的复跑 387.33s 同数字。登记以免被误读为「同一份日志复制两处」 | 三份日志 + R5/R6 | 无需修复 |

**未发现**：off 路径新键、身份洗白通道、双发车通道（launch 路径内）、stop.json 覆盖通道、
金标/题面/env/key 读取、真 sbatch/HPC 接触、T-I 锁定件改动、主树污染、A/B 互染、
C 方案残留（schema-4/descr-4/`evidence_truncation`/帽表——补丁内 grep 无命中）、
「token 门已过」类违规表述。

## 7. 报告数字 vs 证据对账总表

| 主张 | 对账 |
|---|---|
| A：28/174/2362+16 三档测试数 | 28 我复现✓；2362+16 我在组合树复现✓；174 仅日志核对 |
| A：off 15/15 true、探针 7/7 true、payload/prompt/证据锚 SHA | 全部我独立复现或手工重算✓ |
| A：补丁 SHA/行数/字节/numstat/文件 SHA/T-I 交集 0 | 全部吻合✓ |
| B：77/77、C1–C7 分组 2/3/14/10/4/13/31 | 我隔离复现✓（分组计数一致） |
| B：75 hunk、W1-W6=29/10/11/17/1/7、W0=0、20 函数/10 常量 | 我重算+人工全量过目✓ |
| B：`b2ccb10d…`（旧批汇总） | 我精确复现✓ |
| B：`416926da…`（stop）、`c5ca0640…`（identity） | **证据无此二值 ⇒ F1 must-fix** |
| B：8 操作文件 + 7 源文件 SHA、补丁 SHA `9169cd30…`、T-I 锁审计 | 全部吻合✓（15 件在我 R3 重建中逐一验证） |
| B：2362+16+1 warning/401.32s、28/9.54s | 日志吻合，且 2362/16 被我复现✓ |

## 8. 最小回修清单（仅请求范围内）

1. **F1**：修正 B 报告两处 SHA 引用（对齐保存证据或改写为不变量表述）。文档级，一行×2。
2. **F2**：部署序列口径写清（脚本锁/部署文书/任务书勘误任选其一，归 CC 认可）。
3. （可选，F6）把 off-path compare 生成脚本补入 A 证据目录或在报告中注明「对比由
   基线/after 两 JSON 直接重算」。
以上均不动代码、不动证据原件、不重开已证修复。F3/F5/F7 是建议/登记项，不列为回修门槛。

## 9. 三个待决点的意见（不代 CC 拍契约变更）

1. **`v1card + model=None`**：实测行为如 A 报告所述（接受、无载荷、无 v2 prompt 哈希、
   带模型 resume 被拒、不可洗白）。操作链不可达 ⇒ **不构成发车阻塞**。倾向 F5 的
   fail-closed 加固（成本一行），但是否改 runflow 入口语义属契约变更，归 CC/正链。
2. **token 重测口径**：同意 A 报告待决 #5——r2 的 +8.2165%/104/298/+64.13% 口径是
   「v2 B vs 无证据 A」，**不能**代替 P2 的「同 v2 prompt 下 v1 卡 vs v2 卡」；且 A 臂
   v1 卡默认分隔符 vs B 臂 v2 卡紧凑分隔符方向相反，差值必须实测。按任务书 §5.3 在
   prepare 阶段产出 298 题固定载荷披露件，只披露不设门，不得写「token 门已过」。
3. **送审顺序**：本报告闭合程序面（qwen 代 Codex）。剩余两门可并行：①mimo 化学评审
   （场景 1，须显式覆盖 v1card 独立臂的「v2 prompt + v1 卡」语义）；②正链 Codex 对本
   报告的复核确认（额度恢复后）。**脚本锁与签字必须在两门闭合之后**；F1/F2 回修应在
   送正链复核前完成，避免正链对着一份数字不一致的报告复核。

我的复审复跑证据（未入仓，留 `/private/tmp/qwen_review_p2_evidence/`；CC 若要归档：
`mkdir -p docs/review_evidence/qwen_p2_ab_2026-10-21 && cp /private/tmp/qwen_review_p2_evidence/* docs/review_evidence/qwen_p2_ab_2026-10-21/` 并生成 SHA256SUMS）：

| 文件 | SHA-256 | 说明 |
|---|---|---|
| `v1card_probe_result_qwen.json` | `41d5f2c380348fca62d92652cb408f902b9a8590fc17637d1c315688ecaddb3e` | 与 A 保存件逐字节同 |
| `off_path_after_qwen.json` | `abcea2a4704df09d5048e1d401e2547ee43e7b3ae37e85e17832f1effd34c4bf` | 与 A 保存件逐字节同 |
| `probe_rerun_result.json` | `dd7a718eb8b8051258ebb2f7832868444b1c8f1503edc2875993d201bcc4b248` | 77/77，n_failed=0 |
| `probe_ops_controls_qwen.py` | `5930d03bb0293ee2b51c612ffb809c7495db8a222bd2571ce2df6ab70901cf40` | 隔离副本（仅改 WORKTREE/TI_OPS 两路径） |
| `probe_ops_controls_stdout.log` | `41b01c58df996f8407f9d60f4b4a7ed307e8448e10711da16ca59a4085a7f96d` | 我的复跑干跑输出 |
| `pytest_not_slow_qwen.log` | `e39f17f8bac3a4e940953ec53026a6345afe58d92eaadb476a6ef5d434734d28` | 2362 passed/16 deselected/EXIT=0 |
| `my_diff.diff` | `471e273aba093a8619d094e5a0d0a3135c13197961c2cc6df9200acea769be1c` | 我重算的 ti→p2 diff（75 hunk） |
| `ti_operations_ref.py` | `931966a8122ce094cb2b55c3d0a95072c314a6ef43927411f7236d7cffefdfa7` | 与 T-I 锁一致的参考副本 |

## 10. unknown / 未核清单（诚实登记）

1. 全量 not-slow 在 **A 树（仅 patch1+2）** 未单独复跑（在组合树复跑，见 §3）；A 树日志已核对。
2. `pytest_related.log` 174 passed 仅日志核对，未复跑。
3. HPC 侧一切（部署树、RDKit 2026.03.5、v2 确定性锚、真实 build、soak/netcheck、
   slurm 行为）未核——本轮禁止且不可达。
4. 真实模型/真实 298 池形状下的载荷与 token：未测（A 报告同口径登记）。
5. B 报告两个陈旧 SHA 的出处：无法核实（对应轮次输出未保存）。
6. 化学语义（v2 字段/质子化 SMARTS/碳氧化态/v1card 臂 prompt-卡匹配性）：不在本验收面，
   待 mimo 场景 1。
7. 我的 tmp 证据目录在重启后可能丢失（/private/tmp）；归档与否归 CC（§9 给命令）。

## 11. 红线自检

本复审：未改 src/tests/scripts/既有 docs/封存批/两路证据原件/两路工作树；未 push；
未跑 HPC 作业、未连任何远端；未调外部/付费模型；未读金标/题面/reference_graphs/
llm.env/私钥（env 相关只核了 require_env 的代码逻辑与布尔口径）；未输出结构正文；
仓内唯一写入 = 本报告文件。判据（v3/T1′）、新付费批、真实题面外发均未触碰。
