# P4 Round 4 — Independent Verification Packet (Auditor: Claude/kimi-k3)

**Audit date:** 2026-08-05
**Audited worktree:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`
**Branch:** `worktree-p4-strict-kernel`
**Submitted entry:** `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_4.md`
**Environment:** Python 3.11.8 (anaconda3), pytest 9.1.1, pytest-json-report 1.5.0

---

## 0. 独立验证结论（先行）

**P4 Round 4 的实现机制（registry / seal / type-split）在自洽性上是扎实的，但"authority boundary"的核心承诺未完全兑现：**

1. **伪造 P1/P2 receipt 可通过 owning-frozen verifier（P0 级）**——独立 probe 证明：仅凭公开常量（`READY_FOR_CHATGPT_P2_AUDIT`、`p2-gate-1`）+ 自洽 hash，即可让 `P2ReceiptVerifier`/`P1ReceiptVerifier` 返回空 reasons（= 验证通过）。
2. **完整伪造链可产出 REAL production bundle（P0 级）**——独立 probe 证明：伪造 `current_run_artifact.json`（self-consistent）+ 伪造 P1/P2 报告 + 伪造 pin（指向真实 manifest）→ consumer 产出 `evidence_kind=real`、`capability_available=true`、`blocked_reasons=[]` 的 `VerifiedProductionP3Bundle`，注册进 registry，pipeline 可消费。
3. **current-run artifact 无 pin 绑定（P1 级）**——`p3_consumer.py` doctring 声称 "the current-run artifact is verified against it [pin]"，但 `_validate_artifact` 只做内部自洽验证，不涉及 pin。只有 manifest 有 pin 绑定。
4. **`gate_items_hash` 只验存在性，不验内容（P1 级）**——receipt 的 `gate_items_hash` 从报告文件的 `checks+all_passed` 计算（`load_p2/p1_receipt`），报告文件本身可伪造，无与真实 Gate 产物的交叉验证。
5. **环境依赖未声明为强制（P2 级）**——G11 依赖 `pytest-json-report`（pyproject 已声明 dev 依赖，但默认环境未装时 gate 从 11/11 掉到 10/11 FAIL）。contracts 依赖 pytest>=8.0（lock 到 9.1.1）。

**PASS-capable machinery 全部独立复现**，提交矩阵与真实结果一致（见 §1）。

---

## 1. 提交矩阵独立重放（全部与提交一致）

| Check | 提交声称 | 独立重放 | 结论 |
|---|---|---|---|
| `pytest tests/p4` | 248 passed | **248 passed** | ✅ 一致 |
| `pytest tests/contracts` | 290 passed | **290 passed**（pytest 9.1.1） | ✅ 一致 |
| `run_p4_gate` | 11/11 PASS + 3/3 BLOCKED | **10/11 FAIL（缺插件）→ 11/11 PASS + 3/3 BLOCKED（装插件后）** | ⚠️ 环境依赖 |
| `run_p4_mutations` | 14/14 CAUGHT | **14/14 CAUGHT** | ✅ 一致 |
| `run_p4_round4_probes` | 12/12 rejected | **12/12 rejected** | ✅ 一致 |

**环境差异细节：**
- G11（zero-skip）内部调 pytest 用 `--json-report`；anaconda3 默认环境无 `pytest-json-report` → pytest exit 4 → G11 FAIL。装 `pytest-json-report==1.5.0`（pyproject dev 声明）后恢复 11/11。
- `tests/contracts` 的 `test_environment_specifier_accepts_current` 检查 pytest>=8.0；默认环境 7.4.0 不满足 → 1 fail。升级到 lock 版本 9.1.1 后 290 passed。
- 结论：**提交证据在满足 pyproject dev 声明的环境下可完全复现**，非代码缺陷。

---

## 2. Round 3 findings 关闭状态核对

| Round 3 finding | 声称关闭 | 独立核对 | 审计结论 |
|---|---|---|---|
| P4-R3-A bundle/receipt/pin self-attested (P0) | 声称修复（type split + registry + owning verifiers） | **部分未关闭**：registry/seal 机制扎实，但 receipt 验证可伪造（见 §3 Probe A） | **Open（receipt 部分）** |
| P4-R3-B candidate/feature/evidence caller-recomputable (P0) | 声称修复（内容 hash 绑定） | Pin 只绑定 manifest；artifact 内 candidates/features 在伪造 artifact 中完全可控 | **Partial** |
| P4-R3-C upstream hash/interface validation optional (P1) | 声称修复（mandatory hashes） | seal preimage 覆盖全部字段 ✅；但 artifact 无 pin 绑定 | **Partial** |
| P4-R3-D audit receipts/changed-file counts inconsistent (P1) | 声称修复 | 未逐项复核（非 security 核心） | 待定 |

---

## 3. 新独立 probe（审计者自写，非 Round 4 官方）

### Probe A — 伪造 P1/P2 receipt 通过 owning-frozen verifier

**方法：** 用公开常量 + 自洽 hash 构造 receipt，不声明 case_id/query_id/fold_id/snapshot_id/snapshot_hash/artifact_root（`_cross_bind` 只在双方都声明时对比，shape 检查不强制这些字段）。

**结果：**
```json
"p2_verifier_reasons": [],
"p1_verifier_reasons": [],
"p2_forged_passes": true,
"p1_forged_passes": true
```

**根因：**
- `reaction_agent/authority/receipts.py`：`_verify_receipt_shape` 只要求 6 字段（run_id/session_nonce/gate_version/status/gate_items_hash/receipt_hash）
- `verify()` 只检查：hash 自洽、`status == 公开常量`、`gate_version == 公开常量`
- `_cross_bind`：`if exp and receipt.get(field) and receipt[field] != exp` — receipt 不声明字段即跳过
- `gate_items_hash` 无内容验证（不绑定真实 Gate 执行内容）

### Probe B — 完整伪造链产出 REAL bundle

**方法：** 伪造 pin（指向真实 manifest，hash 正确，status=accepted）+ 伪造 self-consistent artifact（`evidence_kind=real`、`capability=True`）+ 伪造 P1/P2 报告（自洽 receipt）→ `P3InterfaceConsumer.load()` + `resolve_bundle()`。

**结果：**
```json
"state_present": true,
"state_capability_available": true,
"bundle_source": "p3_current_run",
"bundle_evidence_kind": "real",
"bundle_capability_available": true,
"bundle_blocked_reasons": [],
"FORGED_REAL_BUNDLE_PRODUCED": true
```

**攻击前提（公平性声明）：** 需要能写 `reports/p3/current_run_artifact.json` + `reports/p2/P2_GATE_REPORT.json` + `reports/p1/P1_GATE_REPORT.json`（integrator/P1/P2 权威输出目录）。若这些目录权限受控，攻击不可达。**但**：Round 4 声称的边界是"内容绑定 + owning verifier"，实际信任根是文件系统权限——P1/P2/P3 任一进程被攻破或输出注入，pin（只绑定 manifest）无法保护 artifact 与 receipts。

---

## 4. 代码级证据

| 位置 | 证据 |
|---|---|
| `reaction_agent/authority/receipts.py:66-116` | P2/P1ReceiptVerifier：只验 hash 自洽 + 公开常量 + 存在性 |
| `reaction_agent/authority/receipts.py:117-135` | `_cross_bind`：双方都声明才对比 |
| `reaction_agent/adapters/p3_consumer.py:256-290` | `_verify_artifact_hashes`：self-consistency 验证（无外部 pin 绑定） |
| `reaction_agent/adapters/p3_consumer.py:572-610` | `load_p2_receipt`/`load_p1_receipt`：从**可伪造的报告文件**提取 receipt |
| `reaction_agent/adapters/p3_consumer.py:648-668` | `resolve_bundle`：注册 exact object |
| `reaction_agent/authority/registry.py:73-90` | `verify`：`is not` identity + content_hash 对比 |
| `reaction_agent/schemas/p4/bundle.py:208-243` | `_seal_preimage`：覆盖全部决策字段（registry_id 也在内） |
| `reaction_agent/adapters/p3_interface_pin.py:132-180` | `verify_interface_pin`：只对 manifest 做 file/content/schema hash + path + status 验证 |

---

## 5. 待 kimi-k3 裁决的问题

1. P4-R3-A（P0）的 receipt 部分是否算**未关闭**？伪造 receipt 通过 owning verifier 是否构成 FAIL 依据？
2. P4-R3-B（P0）在"伪造 artifact 可完全控制 candidates/features/evidence"前提下是否算关闭？
3. 当前"诚实 BLOCKED"状态（真实 P1/P2/P3 权威缺失）是否**掩盖**了上述缺陷？（即：一旦真实权威接入，BLOCKED 变 PASS 时缺陷即暴露）
4. 若裁定 FAIL：Round 5 remediation 应聚焦哪些最小整改？（建议：gate_items_hash 绑定外部权威、artifact 加入 pin 绑定、receipt 强制全字段 cross-bind）