# P2 完整 v2 预注册/发车书 M1–M3 修正 — qwen 复核请求（2026-10-21）

> **provenance：qwen3.8max 代 Codex 复核请求，按 CC 2026-10-21 指示。**
> 只读复核：不跑模型/HPC、不提交作业、不改代码、不改既有批/证据；不读金标/题面/
> `reference_graphs/`/`env`/key/私钥。**本请求与所审文书均零金标。**
> 不冒充 Codex/CC 本人；不替代 Codex 正链最终裁定权；不代签任何拍板。
>
> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本请求只审文书级修正，
> 不重开 token 门、不重审化学、不做科学判定、不决定付费发车。

## 1. 复核范围与对象

上一轮 qwen 确认（`docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md`）判定：两文书方向合格，
但有 **M1/M2/M3 三处文书级必须修正**，四选择中选择 1 附 provenance 条件。本文书已按
M1–M3 完成修正，**只请复核这三处与四选择落字**；不要求重审 token 数字、化学内容、
工程实现或科学判据。

| 文书 | 修前 SHA-256 | 修后 SHA-256（本次复核对象） |
|---|---|---|
| 预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | `8ad5473bfae748d90937af3b1efe399776d0d4112ad0c7d1c872b0d14c8c0528` | `0841201d50477c79128ca08f0257058ac56e36019d978cab3703548c8c366868` |
| 发车书 `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `d47dae5dda50aa8f3906138914c8174c1456c7d24350bc4afb053b0b6307067f` | `276afde2057c2a6ac98c5f80e24ebe5ef44c885a3da5fd743bda7544ad576caa` |
| qwen 确认报告（依据） | — | `51520236effd557032f25bff441542eef99aa464a247451eaae2d924fa2c09d9` |

> 修前/修后差异与 SHA 清单见 `docs/review_evidence/p2_m1m3_fix_2026-10-21/`。
> 两文书仍为**草案**：预注册 `approval_status=DRAFT_NOT_SIGNED`、发车书
> `DRAFT_NOT_EXECUTABLE`；付费批仍 **NO-GO**。

> **Addendum（2026-10-21，P2 契约同步后；不改写上方历史正文）：** 上表“修后 SHA-256”
> 是 M1–M3 修正轮的登记值（历史）。chemfix 后的契约同步
> （`docs/T_P2_CONTRACT_SYNC_2026-10-21.md`）改了预注册/发车书的 v2 prompt 身份行
> （v2 prompt 新 SHA `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`），
> 两文书现行 SHA-256 为：
>
> | 文书 | 同步后现行 SHA-256 |
> |---|---|
> | 预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | `862425160f4bcaf3bafe933c39c02c45e1d44412b04ad6332d7d0b1647ca3ce5` |
> | 发车书 `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `01b1896f7b3312b1c05671123eec35020b96c4a579d8ef7ccaf858600de9d092` |
>
> 两文书仍为草案（`DRAFT_NOT_SIGNED` / `DRAFT_NOT_EXECUTABLE`），本 addendum 不改变
> 历史请求正文、不代签、不构成放行。

## 2. M1 — 命令矛盾（task 附录 A G4）

**原问题：** 附录 A 的 G4 写 `sbatch_th_netcheck.sh`，而 §6.2 明确 P2 不得直接使用该脚本
（`CODE` 写死 `$HOME/EnzymeAgent/v43cTH`，会检查 T-I 树/环境），必须交付并使用
`scripts/hpc/sbatch_p2_netcheck.sh`。

**修正后（task §6.2 与附录 A 逐字一致）：**

```bash
# 附录 A G4
#    G4（官方 netcheck 是唯一允许直接 sbatch 的脚本；其余全走 p2_operations.py launch）：
WS="$P2_WS" sbatch --parsable scripts/hpc/sbatch_p2_netcheck.sh
```

§6.2 同时新增硬口径：

> **唯一直接 sbatch 的脚本：** 官方 netcheck 是 P2 唯一允许直接 `sbatch` 的脚本
> （共享脚本沿用 T-I 同一约定）；其余阶段一律经 `p2_operations.py launch`。本文件与
> 附录 A 的 G4 命令必须逐字一致，且**不得**出现 `sbatch_th_netcheck.sh`（该脚本属 T-I，
> 会检查 `v43cTH`）。

**请核：** ①两处命令是否逐字一致；②除“T-I 脚本说明/禁用句”外，两文书是否不再有把
`sbatch_th_netcheck.sh` 当 P2 命令使用的地方；③是否保留“netcheck 是唯一允许直接 sbatch
的脚本、其余走 `p2_operations.py launch`”这一约束。

## 3. M2 — A 臂 provenance 与四选择落字

**落字结论：`arm_a_definition = v1card`。** A 臂 = v2 prompt + v1 证据卡
（`candidate-evidence-2` / `candidate-evidence-descr-2`，默认 JSON 分隔符）。

**明确写成“设计修正/新增”，不是“回到冻结设计原意”：**

- 冻结设计 `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1 原文的 A 臂是
  **「用户 JSON 字节兼容回退」**（r2 实现为 **v2 prompt + 无证据**）；
- 该原文**保留为历史对照**，不适用于本批 A；
- `v1card` 是对冻结设计的变更/新增，须按预注册 §2.5 差异表由 CC 签字确认。

**provenance 原文（两文书一致）：**

> `qwen3.8max 代 Codex 代 CC 确认（CC 2026-10-21 指示，CC 后置复核）`

并明确：该确认**不是 CC 本人签字**、不替代 CC 拍板、不替代 Codex 正链最终裁定权；
归档的 `P2_CC_DECISION_FULL_V2_2026-10-21.md` 原文不含“A=v1 卡”字样，口径由 qwen 代确认
补链，**不伪填 CC 本人**。CC 签字文本必须显式落 `arm_a_definition = v1card`。

**落字位置：**

| 文书 | 位置 |
|---|---|
| 预注册 | §0.1（定义与 provenance）、§2.1（唯一变量）、§2.5（差异表）、§2.7（四选择）、§7.1/§7.2（签字字段）、§7.4 第 2 项、§10.10、§11（签字位） |
| 发车书 | §0.1（定义与 provenance）、§0.2（四选择）、§0 清单第 5 项、§3.3（最小实现合同前注）、附录 B `arm_a_definition` 及其注 |

**四选择已同步落字（两文书各一张表）：**

| # | 选择 | 落字结论 | 关键条件 |
|---|---|---|---|
| 1 | A 臂 | **A=v1card**（v2 prompt + v1 卡） | 设计修正/新增；provenance 如上；未实现/未复审不签字不发车 |
| 2 | prompt | **两臂共用 v2 prompt + 披露 prompt-卡语义不匹配** | 不分臂 prompt；严格中性共享 prompt 须另冻结/另哈希/复审/重测 token，默认不采用 |
| 3 | 操作入口 | **克隆 `p2_operations.py`，不改 `ti_operations.py`** | 阈值/fatal/恢复/barrier/monitor/stop/seal/评分逐字继承；差异仅 diff 白名单 |
| 4 | build | **seed build + 字节级复制**（默认） | 只复制 build 产物；**不复制** `orchestration.json`/`gate/`/cases/状态文件；**禁止一臂 seed、一臂独立 build**；复制后身份门 1–8 全跑 |

**请核：** ①`arm_a_definition = v1card` 是否在两文书显式出现；②provenance 是否逐字使用
上述字符串且未伪填 CC；③冻结设计原 A 定义是否作为历史对照保留；④四选择是否与 qwen
确认报告一致，且任务书/预注册互相对齐。

## 4. M3 — 分族时序矛盾

**原问题：** F2/F3 原写“发车前冻结”，但定义是“同底物 ≥2 题 **减去 F1**”；F1 只有在
A 臂评分后（发车后）才能确定，发车前无法完成减 F1。

**修正后（预注册 §5.3；任务书 §5.3/§9.3 同步）：**

1. **发车前（build/prepare 后、零题面）**：由 run_inputs 的 `substrate_smiles` 冻结
   **F2raw**（同底物 ≥2 题集合，**不减 F1**）+ 分族规则，写 `p2_family_f2raw.json` 并记 SHA；
2. **A 臂评分后、看 B 配对前**：冻结 **F1**（A 臂 strict 命中且首位 strict 位次 >1）；
3. F1 冻结后按已写死规则**确定性生成** `F2 = F2raw − F1`、`F3 = 298 − F1 − F2`，
   写 `p2_family_partition.json`（F1/F2/F3 qid 列表 + F2raw SHA + 生成规则 + 本文件 SHA）；
4. **冻结该件后**才读 B 的配对结果；不得事后改分组口径/阈值，不引入人工挑选。

**请核：** ①发车前只冻结 F2raw+规则、不再声称冻结最终 F2/F3；②F2/F3 由 F1 冻结后
确定性生成；③两文书的时序、文件名与 SHA 记录要求一致；④未把 F2raw 说成“已减 F1”。

## 5. 附核（不计入 M1–M3 判定）— 化学复审状态落字

CC 2026-10-21 追加纠正：**R4（P0b/D-6 规则级化学复审）= `PASS_WITH_CONDITIONS`，不是
已通过**。两文书已按此落字（预注册 §2.8；发车书 §0.3）：

- 未闭合条件：C1 `stereo_only` 粒度解释；C2 `isomeric_unspecified` 桶含同位素/CX 扩展差；
  C3 空参与物不读 `participant_list_status=partial`；C4 互变/质子化未归一写入
  `does_not_prove`；另 **58 条 `principal_stereo_only` / 146 条 `principal_absent` 的化学
  真伪仍 unknown**；
- **P2 侧仍需独立的 v2 证据卡化学复审（mimo 场景 1 口径），R4 不能充抵**；仓内 Stage B
  独立复审为 `PASS_WITH_CONDITIONS / 未放行`（P1–P7 未闭合，非 mimo 原始回应）；
- P2 付费批维持 **NO-GO**；D-2 离线实施书不得把化学复审写成“已过”而自动放行；
- **不改写 qwen 原文的 FAIL/条件事实为 PASS**；不把 `PASS_WITH_CONDITIONS` 写成 `PASS`。

**只请核：** 两文书是否如实写 `PASS_WITH_CONDITIONS`、是否保留“未放行/NO-GO/不能充抵/
58-146 unknown”，**不要求重审化学内容**。

## 6. 请按此格式回复

```
M1: PASS | FAIL | CLARIFY — 一句理由；引用 §/行
M2: PASS | FAIL | CLARIFY — 一句理由；引用 §/行
M3: PASS | FAIL | CLARIFY — 一句理由；引用 §/行
四选择: PASS | FAIL | CLARIFY — 逐项一句
化学状态附核: PASS | FAIL | CLARIFY — 只核写法，不重审化学
新增矛盾/回归: 无 | 列表（文书级）
总裁定: READY_FOR_OFFLINE_PREP | NEEDS_FIX
```

- `READY_FOR_OFFLINE_PREP` 的含义仅是：M1–M3 与四选择落字闭合，可进入离线准备段
  （v1card 实现/操作链/化学复审送审）；**不等于付费批放行**；
- 若判 `NEEDS_FIX`，请只指出文书级缺口与位置，不改写判据/科学结论。

## 7. 不做什么

- 不重开 token 门（CC 2026-10-21 已豁免；qwen FAIL 事实保留）；
- 不重审化学判据、不认证 58/146、不把 `PASS_WITH_CONDITIONS` 改写为 `PASS`；
- 不评价 v1card/操作链实现（尚不存在）；
- 不决定 T-I 模型、不签字、不批准付费/HPC；
- 不读金标/题面/env/key；不跑模型/HPC；不 push。