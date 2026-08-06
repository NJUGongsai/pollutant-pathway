# Round 1 — 请你输出"疑点清单"（精简版）

你是独立审核者。请通读以下材料，输出**疑点清单**：材料中哪些声称需要独立验证、可能存在什么绕过路径、上轮 finding 关闭状态存疑点。

**本轮不要输出最终裁决**，只输出编号疑点清单，每条含：**疑点** / **要验证什么** / **怀疑等级 P0/P1/P2**。

---

## 被审对象

- **阶段**：P4（Evidence / Ranking / Applicability / Abstention）
- **提交**：Round 4 — origin/authority boundary 重构（Round 3 FAIL 后的整改）
- **状态声明**：`P4_ROUND_4_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT` / `P5_BLOCKED`

## 提交的验证矩阵（声称）

| Check | 声称结果 |
|---|---|
| pytest tests/p4 | 248 passed |
| pytest tests/contracts | 290 passed |
| run_p4_gate | 11/11 PASS + 3/3 BLOCKED（exit 2） |
| run_p4_mutations | 14/14 CAUGHT |
| run_p4_round4_probes | 12/12 rejected |
| P2/P3 suites | worktree 缺失 — integration BLOCKED |

## Round 4 关键实现主张

1. **Type split**：`VerifiedProductionP3Bundle` / `SyntheticP3FixtureBundle` 独立 public type，生产与 fixture 管线不可互换。
2. **`apply_pin=False` 移除**：生产 consumer 无 bypass。
3. **Execution-authority registry**：process-local；verified consumer 是唯一 producer，注册 exact object（identity + hash）；复制/重建/重标对象即使 byte-identical 也 reject。
4. **Pin 发布在 P4 之外**：`reports/p3/p3_p4_interface_pin.json` integrator-owned，只读引用。
5. **Owning P1/P2 verifiers**：按 owning frozen Gate authority 验证 receipts。
6. **真实 authority 缺失时**：`resolve_bundle()` 返回 typed BLOCKED。

## 本文件未包含的完整材料（若有需要可指出应核验）

完整提交：`reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_4.md`；结构化证据：`reports/p4/P4_ROUND_4_AUDIT_EVIDENCE.json`；上轮 audit：`reports/p4/CHATGPT_P4_ROUND_3_READ_ONLY_AUDIT_AND_REMEDIATION.md`。

## 代码结构速览（供判断绕过面）

- `reaction_agent/authority/registry.py`：`verify()` = `is not` identity + content_hash；capability 门控注册；PRODUCTION_REGISTRY 单例。
- `reaction_agent/authority/receipts.py`：`P2/P1ReceiptVerifier` — shape 检查 6 字段、hash 自洽、status/gate_version 精确匹配、`_cross_bind` 双方都声明才对比。
- `reaction_agent/adapters/p3_consumer.py`：`load()`（manifest+pin+artifact 验证）、`load_p2/p1_receipt()`（从 P1/P2 Gate 报告文件提取 receipt）、`resolve_bundle()` 注册 exact object。
- `reaction_agent/adapters/p3_interface_pin.py`：仅对 manifest 做 hash+path+status 验证。
- `reaction_agent/schemas/p4/bundle.py`：`_seal_preimage` 覆盖全部决策字段；`compute_seal()` 公开；`verify_receipts()` 构造 expected 后调 owning verifiers。

## 上轮 mandatory findings（须核对关闭状态）

- **P4-R3-A (P0)**：bundle/receipt/pin self-attested 而非 upstream-authoritative。要求：receipt 必须由 owning Gate authority 产生，不能是 caller 自洽 hash；pin 必须 integrator-owned；不得有 public bypass。
- **P4-R3-B (P0)**：candidate/feature/evidence 内容 caller-recomputable。要求：生产管线不得接受 caller 提供的 evidence/observations/contexts；feature 由 P4 内从 verified evidence 派生；evidence_content_hashes 必须与真实记录核对；ordinal 0..3。
- **P4-R3-C (P1)**：upstream hash/interface validation optional。要求：决定相关 hash mandatory（缺失即 BLOCKED）；pin 必须验证 canonical path/file hash/content hash/schema hash/producer commit。
- **P4-R3-D (P1)**：audit receipts 与 changed-file counts 不一致。要求：one parent session nonce 贯穿、报告记录真实命令。

## 独立重放结果（客观，与提交一致）

| Check | 重放 |
|---|---|
| tests/p4 | **248 passed** |
| tests/contracts | **290 passed**（pytest 9.1.1） |
| run_p4_gate | **11/11 PASS + 3/3 BLOCKED**（安装 pytest-json-report 后） |
| run_p4_mutations | **14/14 CAUGHT** |
| run_p4_round4_probes | **12/12 rejected** |

环境备注：G11 依赖 pytest-json-report（pyproject dev 已声明）；contracts 依赖 pytest>=8.0（lock 9.1.1）。均非代码缺陷。

---

请输出编号疑点清单（至少 5 条），覆盖：receipt 可伪造性、artifact 与 pin 绑定、registry exact-object 语义、跨进程/跨会话语义、P4-R3-A/B/C/D 各自关闭状态。