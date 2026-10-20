# T-H r2 阶段 1 执行报告（build 收尾 → 批根三件套 → 发 run 前置）

> 执行窗口 2026-10-20 10:31–11:05（北京时间）。依据 `docs/T_H_R2_OPERATIONS_2026-10-20.md`
> 与任务书；只读操作＋批根写入（prepare），未改 src/tests/scripts，未 push，旧事故批只读。
> 题域：298＝RHEA 通用酶学／已见题（post-hoc）。

## 0. 结论

**STAGE1 = STOP（执行窗口按容差停报）；主窗口裁定 = 放行发 run（见 §10）。**

build、build-gate、批级诊断、prepare 全部通过；但 P2 实测与“门后预期”在
`remap_add_atom_ge1`（+4）与 `remap_add_atom_ge2`（+3）两项超出 ±2 容差。
按任务书“差异>2 ⇒ 停报，不自行解释为正常”，**未发 run**，交 CC/主窗口裁定。

差异已用只读诊断闭环解释（见 §6）：compiler-6 身份门在**最终 r2 池上零漏**
（531 个池 spec 全部可经 chemstate 表示，0 invalid），但门对 21 题的处置并非
“每题删 1 个 remap+multi-add spec”，而是 **19 题删 1 spec＋2 题替换 1 spec**，
另有 1 个幸存 spec 的 add_atom 计数由 multi 降为 single。因此“529/240/201/75”
的预测前提与实际门行为不符，实际 531/242/205/78 自洽。

## 1. 时间线

| 时刻（北京） | 事件 |
|---|---|
| 09:51:34 | build 作业 46954982 开始（wzhcnormal / f02r3n02） |
| 10:53:20 | build 完成，Elapsed 01:01:46；298/298 题，`TH-BUILD-PASS` |
| 10:54 | `chain13_gate.py build-gate` → `BUILD-GATE-OK`，RC=0 |
| 10:54:54 | `th_operations.py prepare` 发起，RC=0；自动 probe 产出 `p2_face_measure.json` |
| 10:55–11:05 | 批级诊断、P2 对账、spec 级差异与身份门复检（只读） |
| — | **run 未发**（P2 容差停点） |

## 2. build 终态

- `sacct -X`：`46954982 th-r2-bui+ COMPLETED 0:0 2026-10-20T09:51:34 → 10:53:20`。
- `$TH_CODE/th_build_46954982.out` 含：
  - `BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298`
  - `TH-BUILD-PASS (batch_root=…/t_h_s5b_298_20261020r2)`
- 产物：`batch_manifest.json`、`build_identity.json`、`split_manifest.json`、
  `run_inputs/`（298 件）、`reference_graphs/`（298 件）。

## 3. build gate

`chain13_gate.py build-gate --batch-root "$TH_BATCH"` → `BUILD-GATE-OK`，RC=0。

## 4. 批级诊断（只读版本键）

| 键 | 值 |
|---|---|
| `build_identity.compiler_version` | `s5b-compiler-6` |
| `build_identity.pool_policy_version` | `s5b-pool-policy-9` |
| `build_identity.corpus_retrieval_version` | `s5b-corpus-retrieval-6` |
| `build_identity.formnorm_version` | `record-side-formnorm-1` |
| `build_identity.rdkit_version` | `2026.03.5` |
| `build_identity.build_identity_fingerprint` | `ecf4b6bc…c40` |
| manifest `build_identity_ref` 同指纹 | 一致（MATCH） |
| `questions_source_sha256` | `9f5955d4…1c`（与旧批同题卷 SHA） |

`build_identity.json` 在位且可读；`batch_manifest.n_questions=298`。

## 5. prepare 产物

RC=0；批根新增/更新：`preregistration_approval.json`、`budget_no_cap.json`、
`record/approved_text/{T_H_LAUNCH_TASK,T_H_LAUNCH_PREP}_2026-10-20.md`、
`record/r2_operations.json`、`p2_face_measure.json`。
核对：`approval_status=preregistration_confirmed`；`budget_mode=no_monetary_cap_user_decision`
且 marker 在位；`r2_operations.source_commit=c360e74…`。原审批文本 SHA 由 prepare
校验通过（否则会非零退出）。

## 6. P2 对账（实测 vs 预期）

| 指标 | 旧根基线 | 门后预期 | r2 实测 | 实测−预期 | 实测−旧基 | 判定 |
|---|---:|---:|---:|---:|---:|---|
| `specs_total` | 550 | 529 | **531** | +2 | −19 | 容差内 |
| `remap_applied` | 261 | 240 | **242** | +2 | −19 | 容差内 |
| `remap_add_atom_ge1` | 222 | 201 | **205** | **+4** | −17 | **超容差** |
| `remap_add_atom_ge2` | 96 | 75 | **78** | **+3** | −18 | **超容差** |

其余实测量：`files=298`、`questions_remap=151`、`questions_with_add=134`、
`questions_with_multi_add=65`；by_channel：`tpl-env` remap240/add204/add_multi77、
`tpl-rhea` remap2/add1/add_multi1。

### 6.1 差异根因（只读、零模型、零金标）

1. **旧批 550 个池 spec 中恰有 21 个过不了 compiler-6 身份门**（21 题，正是
   `degenerate_fragment_face_v2.json` 的 cop 名单；在最终新池上复跑门：旧批
   `invalid_specs=21/invalid_qids=21`，**新批 `invalid_specs=0/invalid_qids=0`**）。
2. 逐题新旧对比：20 题指标有变化，全部落在上述 21 题内；**17 题各删 1 个
   remap+add≥2 spec，2 题各删 1 个 remap-only spec（add=0）**，共删 19 个 spec
   → `specs_total/remap` 只降 19，不是 21。
3. 另有 **2 题是“替换”而非删除**（各 1 个旧 spec 离池、1 个新 spec 入池，
   池大小不变）：`RXNG_103c8400…`（P2 计数不变）与 `RXNG_b978fd0b…`
   （multi-add 由 1 降为 0）。
4. 因此 add 计数降幅（ge1 −17、ge2 −18）小于预期 −21：被删的 21 个候选里
   有 2 个本来就不含 add_atom，且 b978 的替换 spec 少一个 multi-add。
5. 7 题因唯一 spec 被拒变为空池；旧批本来就有 53 个空池题，新批 60 个——
   空池是该批既有可处理状态（runflow 明确“空池仍组装”），非新增异常形态。

**结论：数字差异可完全由“门按 spec 拒绝/替换”的粒度解释，最终池身份门零漏；
但实测偏离预注册预期，按规则不由执行窗口自行放行。**

## 7. run 状态

**未发起。** opsstate（`operations/t_h_s5b_298_20261020r2.json`）中只有
`build.job_id=46954982`，无 run 作业。未调用 `launch --phase run`。

## 8. 异常与处置

| # | 事项 | 处置 |
|---|---|---|
| 1 | P2 两项超 ±2 容差 | 停报；未发 run；等待 CC/主窗口裁定 |
| 2 | 7 题空池（旧批 53→新批 60） | 记录；沿既有空池路径，未改代码 |
| 3 | 其它 | 无；build/gate/prepare 均一次通过，无重试 |

红线遵守：未读题卷/金标/`llm.env`/私钥；未拉逐题 case；未改 src/tests/scripts；
未 push；未覆盖旧批根；未启动 score。

## 9. 证据目录

`docs/review_evidence/t_h_r2_stage1_2026-10-20/`

| 文件 | 内容 |
|---|---|
| `01_build_job_terminal.txt` | squeue 空 + sacct COMPLETED 0:0 |
| `02_build_log_tail.txt` | build 日志全文与 SHA256 |
| `03_build_gate.txt` | build-gate 输出与 RC |
| `04_diagnostics_versions.txt` | 版本键、指纹与一致性 |
| `05_prepare.txt` | prepare 命令/输出/RC、旁件清单 |
| `06_p2_actual_vs_expected.txt` | P2 四数对比与容差判定 |
| `07_spec_diff_old_vs_new.txt` | 新旧逐题/逐 spec 差异汇总 |
| `08_gate_recheck_pool.txt` | 身份门在旧/新最终池上的复检（21→0） |

## 10. 主窗口裁定（2026-10-20 11:10，发 run）

1. **性质认定**：P2 四个数是**披露分母**，不是发车硬门——`T_H_LAUNCH_PREP` §1-8 与
   `T_H_P2_CHEM_FORWARD_DRAFT` 均写「A=披露、判据不动/池不动、批报告披露实测分母」；
   移交书 §3.4 亦写「以 r2 实测为准披露」。故实测偏离预期不构成预注册变更。
2. **安全性**：compiler-6 身份门在最终 r2 池复检 **0 invalid / 531 spec**（旧池 21→0），
   smoke 期 CX 杀题的根因面已封闭。
3. **算术闭环**：550−19=531、261−19=242、222−17=205、96−17−1=78，与 19 删+2 换、
   2 件 remap-only、1 件 multi→single 的逐题归因逐项吻合，无未解释残差。
4. **裁定**：放行发 run；交付时按 **531/242/205/78** 披露（并注明与旧基/预案的差异及
   §6.1 归因）；7 题新增空池（53→60）沿既有空池形态登记，不视为新异常。
5. 本裁定为**执行操作裁定**，不改预注册文本、不新增科学变量、不改判据与池。