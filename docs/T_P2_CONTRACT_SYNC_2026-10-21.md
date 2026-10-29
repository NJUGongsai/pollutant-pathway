# P2 契约同步报告 — v2 prompt 新 SHA 落入 P2 文书（2026-10-21）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。**
> 本报告只做**文档同步**：未跑模型/网络/HPC、未读金标/题面/`reference_graphs`/`env`/key、
> 未改 `src/`/`tests/`、未改 chemfix/integration 证据目录、未对 `/private/tmp` 工作树做持久写操作
> （只读导入产生的 `__pycache__` 已即时清除，工作树内容零变化）、
> 未 push、未在主树 commit、**未签任何字**。
> 同步清单来源：`docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md` §6.2（15 行 + 1 条附加）。
> 主树 HEAD：`966bc5664a7daa30f24860d2b5594a9dddc6eee2`（分支 `v4.3`）；
> 集成树（**只读**核对）：`/private/tmp/dependingv43_p2_integration` @ `11aeeafded1b41185f24de49767933709aad49db`。

## 0. 最终身份（本次逐字使用）

| 项 | 值 |
|---|---|
| v2 prompt 最终 SHA-256 | `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598` |
| v2 prompt 旧链 | 原始 `89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37` → E 轮 `e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1ecd71be7d953a5a` → 最终 `c24bee42…7598` |
| v1 prompt（不变） | `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e` |
| chemfix patch | `90f0d83b3a63d69ecb151362828c5d2b807cd9d0e3c305ff7d13db66d12e00bc` |
| 集成组合补丁 | `608dec73f2060c78bbc891e134fb6ef16d6bebfa70e1de3e725f88c82c16a0a2` |
| 集成全量测试 | **2398 passed / 16 deselected**（`docs/review_evidence/p2_integration_2026-10-21/pytest_not_slow.log`） |

**核验方式：** 从集成树 `src/pathway_v43/pollutant/real_model.py` 以只读方式导入
`PROPOSALS_PROMPT_VERSION_V2` / `PROPOSALS_PROMPT_VERSION`（`PYTHONPATH=<集成树>/src`），
实测得 `c24bee42…7598` / `fe9eaf…b0f4e`；`_PROMPT_EVIDENCE_NOTES_V2` 由 AST 取出后
SHA-256 = `cd20b91cb260d1feccb1d98ea6189053d478a4ecdbace46e98907c56a639bf3b`。

## 1. 同步清单逐项（16 行）

| # | 文件 | 位置（当前行） | 旧值 | 新值 | 状态 |
|---|---|---|---|---|---|
| 1 | `docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md` | §二.1（L44–48） | 只写 `PROPOSALS_PROMPT_VERSION_V2` 一致 | 追加“chemfix 后新 SHA `c24bee42…7598`”+ 旧链 + v1 不变 | **已应用** |
| 2 | 同上 | §五 身份表 prompt 行（L144） | `PROPOSALS_PROMPT_VERSION_V2`（实现后记录实测 sha256） | `= c24bee42f651…7598`（chemfix 后实测；旧 `89311fdb…0f37` → E 轮 `e2aa2bbf…3a5a` → 本值） | **已应用** |
| 3 | 同上 | 附录 A（L250 起） | 旧 v2 notes 全文（2,391 字符；段 SHA `dd9d6929…04a9`） | 本轮 `_PROMPT_EVIDENCE_NOTES_V2` 新全文（4,477 字符；段 SHA `cd20b91c…bf3b`），逐字等于集成树源码；加身份登记 + “改一字=改版本哈希” | **已应用** |
| 4 | `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | §2.1 prompt 行（L110） | “实测 SHA 登记” | `PROPOSALS_PROMPT_VERSION_V2` = `c24bee42…7598`（chemfix 后实测；两臂同值） | **已应用** |
| 5 | 同上 | §2.2 `prompt_versions.proposals`（L123） | “v2 prompt SHA / 同左” | `c24bee42…7598`（v2 prompt，chemfix 后）/ 同左 | **已应用** |
| 6 | `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | §3.3 第 6 条（L198–200） | “v2 prompt 哈希不变” | “相对本任务书修订不变；chemfix 后以新 SHA `c24bee42…7598` 为准” | **已应用** |
| 7 | `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md` | L34 表行 + L39–46 addendum | 旧 v2 SHA（历史请求正文） | 正文保留不动；addendum 登记新 SHA + 旧链 + v1 不变 | **已应用（addendum）** |
| 8 | `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md` | L32 历史句 + L36–39 注 | 旧 v2 SHA（历史结论） | 历史句与结论保留；加注“旧 SHA 已被 chemfix 取代” | **已应用（加注）** |
| 9 | `docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md` | L37 表行 + L49–54 注 | “v1/v2 prompt 哈希不变” | 加注：只对格式压缩轮成立；chemfix 改了 v2 prompt，**token 离线门必须用新 prompt 重测**；明示“不表示 token 门已通过” | **已应用（加注）** |
| 10 | `docs/T_P2_V1CARD_IMPL_2026-10-21.md` | L57（4b 行） | 探针 `prompt_versions.proposals=89311fdb…0f37` | 保留历史探针值；加注“集成后 v1card 探针使用 `c24bee42…7598`” | **已应用（加注）** |
| 11 | `docs/review_evidence/p2_evidence_card_v2_2026-10-21/identity.json` | `prompt.v2_sha256`（L38） | `89311fdb…0f37` | 历史证据**不改**；本报告登记“历史值，新 identity 用新 SHA” | **未改（按设计）+ 已登记** |
| 12 | `tests/test_p2_v2_chemfix.py::NEW_V2_PROMPT_SHA256` | 集成树测试 L46–47 | — | 核对 = `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598` | **已核对，不改代码** |
| 13 | `tests/test_p2_evidence_card_v2.py` | L119–139 | — | 核对：只断言 v1 SHA + v2 自洽哈希，**未写死旧 v2 SHA**；无需改 | **已核对，无需改** |
| 14 | token 门证据 `token_measure_result_{standard,lean}_r2.json` | 全文件 | 旧 prompt 下测得 | 历史证据**不改**；本报告登记“**需用新 prompt 重测**”（本单未跑，不作为发车依据） | **未改（按设计）+ 已登记** |
| 15 | `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | §2.5（L183–190） | 只披露“prompt 描述 v2 字段、A 臂 v1 卡无这些字段” | 补披露：新 prompt 增加 `n_hits`/delta/unknown 原因语义 ⇒ 不匹配面扩大；B−A 是“同 prompt 下 v2 卡 vs v1 卡”，**不是纯卡版本效应**，不得写成纯重排/纯卡效应 | **已应用** |
| 16 | `docs/P2_FULL_V2_QWEN_REREVIEW_REQUEST_2026-10-21.md` | 历史表 + L28–36 addendum | 预注册 `0841201d…c868`、发车书 `276afde2…6caa` | 正文保留；addendum 登记同步后新 SHA：预注册 `86242516…3ce5`、发车书 `01b1896f…d092`；仍为草案 | **已应用（addendum）** |

## 2. 被改文档 SHA-256（改前 → 改后）

| 文件 | 改前 SHA-256 | 改后 SHA-256 |
|---|---|---|
| `docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md` | `0b69af58b5f0ca43bec87589f5efb03ed17df2b61dd3c545e498cc1b4af20373` | `59f3df908cace2601bf6294aeba485501cbea2d4857d24f38e1381da8202df74` |
| `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` | `0841201d50477c79128ca08f0257058ac56e36019d978cab3703548c8c366868` | `862425160f4bcaf3bafe933c39c02c45e1d44412b04ad6332d7d0b1647ca3ce5` |
| `docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md` | `276afde2057c2a6ac98c5f80e24ebe5ef44c885a3da5fd743bda7544ad576caa` | `01b1896f7b3312b1c05671123eec35020b96c4a579d8ef7ccaf858600de9d092` |
| `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md` | `326685f0bc310bd382f3d67563ad3563d116486a09cca00c4d9c7bdc70ac02d0` | `e70071eeed5eaba28a9fe2776975b10610298806addf86e54b72c448aeb63537` |
| `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md` | `3a513aea092a9b311bfdc2c4b65fc568abfc9fe25b28893b988fb4f0a0a70012` | `cffd4e0607b04a1d912c6c8ad9d8ede7f0c4e7638236ce959e05dd9cae1f467f` |
| `docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md` | `e3e72cd3ca131d093ad6f1201c4b7204fb0ffd1e651b2762f6a3c0f406c14779` | `c7aaadd381e22f16471016079e0254545fb4712cecdd581db3ce44dc4754dcef` |
| `docs/T_P2_V1CARD_IMPL_2026-10-21.md` | `5f4dcc7863c1039e1b3668fe857bdf2cba8fbcc56f592f1b0dbf586605142478` | `9790988527d5aa28caa559fce1aabfce685ba912b81bb59116ccd3f70b4ee431` |
| `docs/P2_FULL_V2_QWEN_REREVIEW_REQUEST_2026-10-21.md` | `3b38ecfaf73701c36dc451e9edac5871fad9ab715ec118a665e352d83685d27f` | `e615635a861aa2eee33374c9b9dd3b6e4d346cc79aa3f3c5ce833b08d92a488e` |

**未改文件（供对账）：**
`docs/review_evidence/p2_evidence_card_v2_2026-10-21/identity.json` =
`365122e3ed33bf9a3d5f27f393abf4ab4b60003490e79ce980b74744bf821655`（历史证据，原样）。

## 3. 未应用/未执行项及原因

| 项 | 原因 |
|---|---|
| #11 `identity.json`、#14 token 门双档 JSON | 按指令“历史证据不改”，只在报告登记；新 identity 属新证据目录/新 prompt 重测轮 |
| #12 `NEW_V2_PROMPT_SHA256` | 已核对为新值，属代码锁；本单“只改文档”，不改代码 |
| #13 `tests/test_p2_evidence_card_v2.py` | 已核对未写死旧 v2 SHA，无需改 |
| token 离线门重测 | 未执行：本单只做文档同步；重测属发车前硬门，需按预注册/任务书另行执行。**本报告不表示 token 门已通过** |
| 旧 v2 prompt 启动过的 run 的 resume 拒绝行为 | 未测：无真实 v2 run（chemfix 报告 §6.1 已说明“未发现/未启动任何真实 v2 run”），且属代码行为，不在文书同步范围 |
| 预注册 §2.5 第 6 条（L173）现有表述“v2 prompt 哈希不变” | 未改：不在 16 行清单内；该句限定在 `v1card` 实现合同的测试要求内（实现 v1card 不应改 v2 prompt），不构成现行身份声明；现行身份由 §2.1/§2.2 与 §2.5 新增披露覆盖。是否改写请 CC 定 |
| 教师进度报告、qwen 确认报告等旧 SHA | 未改：属历史快照/历史评审正文，按“不重写历史”原则保留（见 §5 标注） |

## 4. 附录 A 身份与替换核验

| 项 | 值 |
|---|---|
| 旧附录段（notes 正文） | 2,391 字符；SHA-256 `dd9d69297987c4d424911519b83064182e14c046916e9c4694eedfe7124004a9` |
| 新附录段（notes 正文） | 4,477 字符；SHA-256 `cd20b91cb260d1feccb1d98ea6189053d478a4ecdbace46e98907c56a639bf3b` |
| 与集成树源码一致性 | `附录 A` 代码块 == 集成树 `_PROMPT_EVIDENCE_NOTES_V2`（AST 取出原文，**逐字节相等**） |
| 整份 `PROPOSALS_PROMPT_VERSION_V2` | `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`（整 prompt 哈希，**不是**附录段哈希） |
| 新附录 A 整节 SHA-256 | `49a3c7cea83eb6c11dd3990f42e4ad70d58b77b62e82f7e72baf09be242ca0b9`（5,250 字节，从 `## 附录 A` 到 `## 附录 B` 前） |
| 源文件身份 | 集成树 `src/pathway_v43/pollutant/real_model.py` SHA-256 `6351e9b8b32f2bd12d46a1b08575e78a00ce1bc8d8229b404daf1f61cc8a1ed1` |

附录内已加“**改一字=改版本哈希**：改本段须重算 `PROPOSALS_PROMPT_VERSION_V2` 并重跑离线门”。

## 5. `grep -rn "89311fdb\|e2aa2bbf" docs/` 全量扫描（58 处）

扫描命令（仓库根）：`grep -rn "89311fdb\|e2aa2bbf" docs/`；下表**排除本报告自身**
（本报告 §0/§1/§5/§6 也引用旧 SHA，属自引用，不计入遗漏）。

- **遗漏（需修）= 0**：当前状态性文书（任务书/预注册/发车书/证据卡请求与复审请求）中的旧值
  均为历史正文或已加注；新身份值已在 §1 各行落入。
- 标注口径：**已加注** = 本轮加了说明且指向新 SHA；**历史** = 冻结报告/证据/旧快照，
  按“不重写历史”保留；**变更登记** = 文档本身记录旧→新，正确。

| 位置 | 内容摘要 | 标注 |
|---|---|---|
| docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md:45 | （旧链：原始 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50… | 已加注（本轮 provenance 旧链） |
| docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md:46 | → E 轮 e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1ecd71be7d953a5a | 已加注（本轮 provenance 旧链） |
| docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md:144 | ／ prompt ／ PROPOSALS_PROMPT_VERSION = fe9eaf…b0f4e ／ PROPOSALS_PROMP… | 已加注（本轮；新值为准，旧链并列） |
| docs/P2_FULL_V2_QWEN_CONFIRM_2026-10-21.md:67 | v2 prompt（89311fdb…0f37）——成本高且偏离已冻结面；预注册 §2.5 已把该出口留给 | 历史（chemfix 前 qwen 确认；非现行身份） |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md:32 | v2 prompt 实测 89311fdb…0f37；目标批 88 passed；全量 not-slow | 历史正文（保留）；邻接 L36–39 已加注 |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md:36 | > 注（2026-10-21 契约同步）： 上段 v2 prompt 实测 89311fdb…0f37 是本报告复现时的 | 已加注（本轮） |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md:37 | > 历史值；该旧 SHA 已被 chemfix 取代（89311fdb…0f37 → E 轮 e2aa2bbf…3a5a → 最终 | 已加注（本轮） |
| docs/T_P2_V2_CHEM_REVIEW_REQUEST_2026-10-21.md:45 | ／ v2 prompt SHA-256 ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c… | 历史（一轮化学评审请求快照） |
| docs/REPORT_TEACHER_LIU_PROGRESS_2026-10-21.md:148 | 注意： 修复改变了 v2 prompt 文本与 SHA（89311fdb… → e2aa2bbf…），token 门必须用新 | 历史（当日进度快照，E 轮值；下一版对外报告须登记新值） |
| docs/review_evidence/p2_integration_2026-10-21/sha_reconciliation.json:33 | "diff": "V2_PROMPT_SHA256 constant 89311fdb... -> c24bee42... (integ… | 历史证据（常量更新对账） |
| docs/review_evidence/p2_integration_2026-10-21/v1card_probe_integration.py:173 | # 89311fdb… → e2aa2bbf… → c24bee42…（N1/N2/N5 收口）； | 历史证据（旧链注释） |
| docs/review_evidence/p2_integration_2026-10-21/p2_integration_combined.patch:6012 | +# 取代 r2 的 89311fdb… 与上一版 e2aa2bbf…。两臂共用本常量。 | 历史证据（冻结 patch） |
| docs/review_evidence/p2_integration_2026-10-21/p2_integration_combined.patch:6429 | + "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37") | 历史证据（冻结 patch） |
| docs/review_evidence/p2_integration_2026-10-21/ORIGINAL_PATCHES.md:31 | ／ v2 prompt 89311fdb…（r2）/ e2aa2bbf…（E 轮） ／ 已被 c24bee42… 取代；历史值只保留在 … | 历史证据（已注明被 c24bee42 取代） |
| docs/review_evidence/p2_integration_2026-10-21/ORIGINAL_PATCHES.md:48 | 89311fdb… 更新为 N 轮 chemfix 后的 c24bee42…。 | 历史证据（说明常量更新） |
| docs/review_evidence/p2_integration_2026-10-21/environment.json:49 | "v2_e_round_old": "e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1… | 历史证据（旧值登记） |
| docs/review_evidence/p2_integration_2026-10-21/environment.json:51 | "v2_r2_old": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史证据（旧值登记） |
| docs/review_evidence/p2_integration_2026-10-21/environment.json:58 | "source_tree_note": "Integration tree was reset to clean 11aeeaf and… | 历史证据（常量更新说明） |
| docs/review_evidence/p2_v2_chem_review_2026-10-21/README.md:100 | ／ 提示词 v2 SHA-256 ／ 89311fdb...b50f37 ／ 同 ／ 通过 ／ | 历史证据（复审 README） |
| docs/review_evidence/p2_v2_chem_review_2026-10-21/probe_03_delta_v2.out:160 | v2_prompt_sha256 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c89721… | 历史证据（探针输出） |
| docs/review_evidence/p2_v1card_2026-10-21/impl.patch:1698 | + "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37") | 历史证据（冻结 patch） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe.py:174 | == "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37… | 历史证据（探针源码） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:13 | "prompt_v2_bytes_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad6… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:14 | "prompt_v2_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:109 | "proposals": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:143 | "system_prompt_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:152 | "proposals": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/v1card_probe_result.json:186 | "system_prompt_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616… | 历史证据（探针结果） |
| docs/review_evidence/p2_v1card_2026-10-21/patch2_v1card.patch:308 | + "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37") | 历史证据（冻结 patch） |
| docs/review_evidence/p2_evidence_card_v2_2026-10-21/identity.json:38 | "v2_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史证据（按设计不改；新 identity 用新 SHA） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/chemfix_19probe_before.out:345 | "prompt_v2_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8… | 历史证据（before 探针） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/chemfix_19probe_before.out:346 | "prompt_v2_text_sha256": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad61… | 历史证据（before 探针） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/RE_REVIEW_DELTA_2026-10-21.md:16 | ／ v2 prompt ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史证据（旧→新对照） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/before_after_matrix.json:715 | "prompt_v2_before": "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8… | 历史证据（before 值） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/RE_REVIEW_ROUND3_LIMITED_2026-10-21.md:95 | ／ 上一版（E1/E3） ／ e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b1ecd7… | 历史证据（上一版身份） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/RE_REVIEW_ROUND3_LIMITED_2026-10-21.md:96 | ／ 原始 impl.patch r2 ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8… | 历史证据（原始 r2 身份） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/chemfix.patch:286 | + "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37") | 历史证据（冻结 patch） |
| docs/review_evidence/p2_v2_chemfix_2026-10-21/IDENTITY_RECONCILIATION_2026-10-21.md:90 | - prompt SHA：c24bee42…7598（旧 e2aa2bbf…3a5a；更早 89311fdb…0f37）。 | 历史证据（旧链登记） |
| docs/T_P2_V1CARD_IMPL_2026-10-21.md:57 | ／ 4b ／ prediction.prompt_versions.proposals = v2 SHA ／ runflow.py:19… | 已加注（本轮；历史探针值保留） |
| docs/QWEN_P2_AB_REVIEW_2026-10-21.md:81 | ／ 4 ／ identity/resume ／ 通过 ／ _v1card_identity_fields（version/schema/… | 历史（v1card 程序复审快照） |
| docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md:21 | 89311fdb…0f37 → c24bee42…7598。任务书/预注册/token 门/旧证据里的 | 变更登记（旧→新，正确） |
| docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md:230 | ／ v2 prompt PROPOSALS_PROMPT_VERSION_V2 ／ 89311fdb5a85e6699f558d7b0a… | 变更登记（旧→新表，正确） |
| docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md:253 | ／ 10 ／ docs/T_P2_V1CARD_IMPL_2026-10-21.md ／ L57 ／ 探针 prompt_version… | 变更登记（同步清单第 10 项） |
| docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md:405 | 唯一要你拍板的是 v2 prompt SHA 变了（旧 89311fdb → 新 c24bee42）， | 变更登记（一句话摘要） |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md:34 | ／ v2 prompt ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史请求正文（保留）；L39–46 addendum 已加注 |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md:40 | > 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37 是… | 已加注（addendum） |
| docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md:43 | > （旧链：原始 89311fdb…0f37 → E 轮 e2aa2bbf61694c25f4607044f5f45a05c8e01c7… | 已加注（addendum） |
| docs/T_P2_INTEGRATION_2026-10-21.md:54 | ／ A 路测试 ／ tests/test_p2_v1card_mode.py ／ 与来源树有意不同：V2_PROMPT_SHA256 常… | 历史（已注明更新为 c24bee42） |
| docs/T_P2_INTEGRATION_2026-10-21.md:98 | ／ v2 prompt（r2 旧） ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c89… | 历史（§4 新旧表；L100 已列新值） |
| docs/T_P2_INTEGRATION_2026-10-21.md:99 | ／ v2 prompt（E 轮旧） ／ e2aa2bbf61694c25f4607044f5f45a05c8e01c76dad8e26b… | 历史（§4 新旧表；L100 已列新值） |
| docs/T_P2_INTEGRATION_2026-10-21.md:162 | 4. v1card 单独重放会红：patch2_v1card.patch 自带旧常量 89311fdb…；在 | 历史（旧 patch 常量说明） |
| docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md:37 | ／ 2.1 ／ 改动面=仅格式级 ／ 通过 ／ impl_r1.patch → impl.patch diff 仅：real_model… | 历史表格行（结论保留）；L49–54 已加注 |
| docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md:50 | > （fe9eaf77…/89311fdb…）”的结论只对格式压缩轮（r1→r2，仅 JSON 分隔符/空白）成立。 | 已加注（本轮） |
| docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md:51 | > chemfix 改了 v2 prompt 文本（89311fdb…0f37 → E 轮 e2aa2bbf…3a5a → 最终 | 已加注（本轮） |
| docs/T_P2_V2_CHEM_REVIEW_2026-10-21.md:151 | ／ v2 提示词 SHA-256 ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c897… | 历史（Stage B 化学复审，审旧 prompt） |
| docs/T_P2_V2_CHEM_REVIEW_ROUND2_2026-10-21.md:238 | 6. N6 token 门：v2 prompt SHA 由 89311fdb…0f37 变为 e2aa2bbf…3a5a（[P]，L27… | 历史（二轮复审 E 轮记录） |
| docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md:39 | ／ v2 prompt ／ 89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f… | 历史（r2 实施报告） |
| docs/T_P2_EVIDENCE_CARD_V2_IMPL_REPORT_2026-10-21.md:239 | ／ prompt ／ v1 fe9eaf…b0f4e、v2 89311fdb…0f37 均不变 ／ | 历史（r2 实施报告） |

## 6. 冲突与相邻不一致（登记，不改）

1. **16 行清单无冲突**：按内容逐项落地成功；§6.2 的行号有轻微过时（预注册 §2.1 现为 L110
   而清单写 L90；任务书 §五 prompt 行因本轮 §二.1 追加后移到 L144），均按内容定位，无歧义。
2. **预注册/发车书 SHA 已变**：同步后预注册 `86242516…3ce5`、发车书 `01b1896f…d092`；
   旧登记 `0841201d…`/`276afde2…` 只保留在历史件中。已在 §1 第 16 行 addendum 登记新值。
3. **仍带旧预注册/发车书 SHA 的相邻文书（不在 16 行清单，未改）**：
   - `docs/HANDOFF_MAIN_TO_P2_2026-10-21.md` L44–45、L59：属**现行交接文书**，建议下一轮
     交接刷新时更新为新 SHA（本单未授权改）；
   - `docs/T_P2_INTEGRATION_2026-10-21.md` L131–132：历史报告快照，保留；
   - `docs/review_evidence/closeout_2026-10-21/SHA256SUMS` L4–5 与
     `docs/review_evidence/p2_m1m3_fix_2026-10-21/after_sha256.txt`：冻结证据，不改。
4. **文档状态未被改动**：预注册仍 `approval_status: DRAFT_NOT_SIGNED`（`approved_at`/
   `approval_source` 仍为 `TBD`）；发车书仍 `DRAFT_NOT_EXECUTABLE`；未填任何签字字段。
5. **未改科学面**：未改任何 gate、判分、池、检索、科学参数；第 3 行是附录 A 原样替换为
   集成树新全文（未自行改写一字）。

## 7. 复核命令

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
shasum -a 256 \
  docs/TASK_P2_EVIDENCE_CARD_V2_IMPL_2026-10-21.md \
  docs/T_P2_PREREG_FULL_V2_2026-10-21.md \
  docs/TASK_P2_FULL_V2_LAUNCH_2026-10-21.md \
  docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md \
  docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_2026-10-21.md \
  docs/P2_EVIDENCE_CARD_V2_TOKEN_GATE_QWEN_DECISION_2026-10-21.md \
  docs/T_P2_V1CARD_IMPL_2026-10-21.md \
  docs/P2_FULL_V2_QWEN_REREVIEW_REQUEST_2026-10-21.md
grep -rn "89311fdb\|e2aa2bbf" docs/
grep -n "DRAFT_NOT_SIGNED\|approved_at\|approval_source" docs/T_P2_PREREG_FULL_V2_2026-10-21.md
```

**一句话：** 15+1 行同步全部落地（**12 行改文档（8 个文件）**、2 行核对代码不改、2 行历史登记；
token 门重测未执行、仅登记）；预注册/发车书仍是草案未签字；旧 SHA 只剩历史/已加注位置，
无当前状态性遗漏。