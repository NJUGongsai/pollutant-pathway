# Hermes P4 Round 4 Read-Only Audit and Round 5 Remediation

**Audit date:** 2026-08-05
**Audit type:** implementation correctness, scientific provenance and integration-boundary review
**Audited worktree:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`
**Audited branch:** `worktree-p4-strict-kernel`
**Auditor:** kimi-k3（独立裁决，经 Hermes 运行）+ Claude（独立验证与 probe）
**Submitted entry:** `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_4.md`
**Independent verification:** `reports/p4/INDEPENDENT_VERIFICATION_PACKET.md`

---

## 0. Verdict

**P4 Round 4 不通过只读审核（FAIL）。Round 5 定向整改必须执行。P5 保持 BLOCKED。**

```text
HERMES_P4_ROUND_4_READ_ONLY_AUDIT_FAIL
P4_ROUND_5_REMEDIATION_REQUIRED
P5_BLOCKED
```

Round 4 的 machinery（registry / seal / type-split / pin 路径检查）相比 Round 3 有实质进步，提交矩阵全部可复现。但**独立 probe 证明 authority boundary 的核心承诺未兑现**：伪造 P1/P2 receipt 可通过 owning-frozen verifier，完整伪造链可产出 REAL production bundle。**提交矩阵全绿不具备开脱效力**——测试语料只覆盖"诚实证明者 + 对已有有效产物的变异"，从未覆盖"从公开常量凭空铸造"的攻击类别。

---

## 1. Independent verification matrix（审计者独立重放，与提交一致）

| Check | 提交声称 | 独立重放 | 结论 |
|---|---|---|---|
| `pytest tests/p4` | 248 passed | **248 passed** | ✅ |
| `pytest tests/contracts` | 290 passed | **290 passed**（pytest 9.1.1） | ✅ |
| `run_p4_gate` | 11/11 PASS + 3/3 BLOCKED | **11/11 PASS + 3/3 BLOCKED**（装 pytest-json-report 后） | ✅ |
| `run_p4_mutations` | 14/14 CAUGHT | **14/14 CAUGHT** | ✅ |
| `run_p4_round4_probes` | 12/12 rejected | **12/12 rejected** | ✅ |
| P2/P3 suites | worktree 缺失 | worktree 缺失 | BLOCKED |

**环境备注**：G11 依赖 `pytest-json-report`（pyproject dev 已声明，默认环境未装时 G11 FAIL）；contracts 依赖 pytest>=8.0（lock 9.1.1）。均非代码缺陷，属环境复现前提（见 P4-R4-05）。

---

## 2. Finding closure matrix（上轮 P4-R3-A/B/C/D 关闭状态）

| 上轮 finding | 提交声称 | 独立判定 | 依据 |
|---|---|---|---|
| **P4-R3-A** bundle/receipt/pin self-attested (P0) | 修复 | **Partial**（receipt 子项 Open） | Probe A 实测：伪造 receipt 通过 owning verifier（`p2_forged_passes=true`） |
| **P4-R3-B** candidate/feature/evidence caller-recomputable (P0) | 修复 | **Open** | Probe B 实测：伪造 artifact + P1/P2 报告产 REAL bundle，candidates/features/evidence 生成链攻击者可控 |
| **P4-R3-C** upstream hash/interface validation optional (P1) | 修复 | **Open** | Probe B 实测：artifact 无 pin 绑定（doctring 声称有，代码未实现） |
| **P4-R3-D** audit receipts/changed-file counts 不一致 (P1) | 修复 | **Open** | 本轮未复核；按 fail-closed 原则，无复核证据即不满足关闭条件 |

**结论：四个 finding 无一 Closed——1 Partial + 3 Open。**

---

## 3. Mandatory findings

### P4-R4-01 — 验证链无认证根，receipt 可伪造【Critical / 阻断】

**证据**：`reaction_agent/authority/receipts.py` — `P2ReceiptVerifier`/`P1ReceiptVerifier` 仅做内部一致性检查（hash 自洽、字段齐全、`status`/`gate_version` 与公开常量相等），无任何外部信任锚（无 HMAC/签名/密钥/台账）。`_cross_bind` 用 `if exp and receipt.get(field)` 只在双方都声明时对比；`gate_items_hash` 无内容验证。独立 Probe A 实测：仅用公开常量 + 自洽 hash 构造的 receipt 通过验证（`p2_verifier_reasons=[]`, `p1_verifier_reasons=[]`）。

**影响**：P4 的"通过"结论不可证伪。任何对 receipt 存储路径有写权限的主体可伪造"通过"回执。P5+ 所有下游阶段继承虚假前提。

**修复要求**：
1. 对 receipt canonical serialization 做 HMAC 或 Ed25519 签名；密钥存放于 artifact 目录之外。
2. fail-closed：密钥缺失/签名缺失/不匹配一律 FAIL，禁止"跳过验签"路径。
3. 签名范围覆盖 artifact digest 清单与 gate 定义版本（联动 R4-02/03）。

### P4-R4-02 — artifact 无 pin 绑定，验证后可调包【High】

**证据**：`reaction_agent/adapters/p3_consumer.py` — `_validate_artifact` 只做内部自洽验证（`_verify_artifact_hashes` 重算 artifact 自带 hash），**不涉及 pin / 外部锚**。doctring 声称 "the current-run artifact is verified against it [pin]"，代码未实现。`p3_interface_pin.py` 的 `verify_interface_pin` 只绑定 manifest 文件。独立 Probe B 实测：伪造 self-consistent artifact（`evidence_kind=real`, `capability=True`）可被消费。

**影响**：证据可在验证后被替换（TOCTOU）。"evidence-grounded" 立论失效——审核者无法证明当前 artifact 就是 gate 结果那份。

**修复要求**：
1. 内容寻址：SHA-256 digest 作为存储/引用主键，每个消费点重算比对，fail-closed。
2. artifact digest 钉入 bundle 并纳入 verifier 校验（写入 R4-01 签名范围）。
3. 存储侧 WORM/只读权限，验证流程内禁止原地改写。

### P4-R4-03 — gate_items_hash 只验一致性、不验内容【High】

**证据**：`p3_consumer.py` `load_p2_receipt`/`load_p1_receipt` — `gate_items_hash = canonical_hash({"checks": data.get("checks"), "all_passed": ...})`，checks 来自**可伪造的报告文件**。hash 只证明"列表在 hash 之后未变"，不证明"列表是正确的 gate 定义"。条目削弱/删减后重算 hash，校验照样通过。

**影响**：gate 可对着一份被削弱或错误的条目集"合法"通过；hash 检查提供虚假安全感。

**修复要求**：
1. canonical gate spec 纳入版本控制，期望 hash 钉在仓库或随 R4-01 签名分发。
2. 验证时重算 hash 且与 canonical 定义逐条 diff，未知/缺失/多余条目一律 FAIL。
3. hash 覆盖条目的全部参数与阈值，而非仅条目名。

### P4-R4-04 — registry 为 process-local，跨进程语义未定义【High】

**证据**：`reaction_agent/authority/registry.py` — `PRODUCTION_REGISTRY` 是模块级内存结构。注册与验证跨进程（pytest runner vs 校验器、xdist worker、多次 CLI 调用）时各进程持有独立实例；A 进程注册对 B 不可见。且 `resolve_bundle()` 每次调用注册新条目，`_entries` 无限增长（内存泄漏）。

**影响**：gate 结论依赖执行模型，不可复现；最坏情况"什么都没注册也判通过"（fail-open）。

**修复要求**：
1. registry 持久化：append-only JSONL（写后 fsync）或 SQLite，明确写者/读者/时序契约。
2. 验证端 fail-closed：期望条目缺失或 registry 为空时判 FAIL。
3. 增加跨进程 E2E 测试（生产者与验证者独立进程，覆盖 xdist）。

### P4-R4-05 — 验证依赖 pytest-json-report，环境约束未封闭【Medium】

**证据**：G11 内部调 pytest 用 `--json-report`；anaconda3 默认环境无该插件 → pytest exit 4 → G11 FAIL（实测）。contracts 依赖 pytest>=8.0（lock 9.1.1），默认 7.4.0 不满足。依赖虽在 pyproject dev 声明，但非"验证环境硬依赖"闭环。

**影响**：同一代码不同机器结论不同；环境错误与测试失败混为一谈。

**修复要求**：
1. 按仓库依赖政策钉版并 lock；验证前置检查插件存在且版本受支持。
2. fail-closed 分类：报告缺失/解析失败/schema 版本不符 → "环境错误"且总体 FAIL，分开报告。
3. receipt 记录插件版本与报告 hash；比对测试 node ID 集合与 canonical 测试清单。

---

## 4. Root cause 综述

五项 finding 同一根因：**把"自证一致"当成"外部可信"，且多处默认 fail-open**。内部一致性（hash 自洽、字段齐全）不构成真实性证明。Round 4 声称的 "origin/authority boundary" 实际信任根是**文件系统权限**（reports/ 目录写权限），而非内容绑定或密码学锚。

## 5. Remediation requirements（Round 5 最小整改）

1. **receipt 绑定信任根**：HMAC/Ed25519 签名，密钥外置；伪签/缺签一律 FAIL。（R4-01）
2. **artifact 内容寻址**：digest 钉入 bundle + 签名 manifest；验证端重算比对。（R4-02）
3. **pin 覆盖 artifact**：修 doctring 与实现差距，artifact 纳入 pin 验证。（R4-02）
4. **gate_items_hash 内容验证**：canonical gate spec 版本化 + 逐条 diff。（R4-03）
5. **registry 持久化 + 跨进程 fail-closed**。（R4-04）
6. **环境依赖闭环**：pytest-json-report 钉版 + 前置检查。（R4-05）

**R5 复审前提**：五项全部关闭，且每项附负向测试——伪造 receipt、调包 artifact、削弱 gate 条目、跨进程运行、卸载插件，五种攻击场景各至少一条 fail-closed 测试。复审时**先跑独立伪造 probe，再看提交矩阵**（顺序不可反）；关闭证据须附 Probe A/B 复测输出。

---

*Generated by Hermes (kimi-k3) 独立裁决 + Claude 独立验证。*