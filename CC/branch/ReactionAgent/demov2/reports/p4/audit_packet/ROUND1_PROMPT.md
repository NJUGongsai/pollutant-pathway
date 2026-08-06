# Round 1 — 请你输出"疑点清单"

你是独立审核者。这是对你的**第一轮质询**：请通读以下全部材料，然后输出你的**疑点清单**——即：提交材料中哪些声称需要独立验证、哪些地方可能存在绕过路径、哪些上轮 finding 的关闭状态存疑。

**本轮不要输出最终裁决**，只输出疑点清单（编号列出，每条附：疑点内容 + 你要验证什么 + 你怀疑的等级 P0/P1/P2）。

---

## 一、被审对象

- **阶段**：P4（Evidence / Ranking / Applicability / Abstention）
- **提交**：Round 4 — origin/authority boundary 重构（Round 3 audit FAIL 后的整改）
- **状态声明**：`P4_ROUND_4_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT` / `P5_BLOCKED`

## 二、Round 4 提交材料（核心）

### 0. Verdict request（提交者自述）

> Round 4 以 origin/authority boundary 取代 Round 3 的 self-attested digests：production/fixture 类型拆分、execution-authority registry、owning P1/P2 receipt verifiers、in-P4 feature derivation from verified evidence、mandatory repeated hashing、integrator-owned pin read-only。Round 3 audit 的 12 个 synchronized-recomputation probes 现在全部被 reject。真实 P1/P2/P3 生产 authority 仍然缺失，真实 Gate 诚实 BLOCKED。

### 1. 提交的验证矩阵

| Check | 提交声称结果 |
|---|---|
| `pytest tests/p4` | 248 passed（205 Round 3 + 43 new RED） |
| `pytest tests/contracts` | 290 passed |
| `run_p4_gate` | exit 2 — machinery 11/11 PASS, real-input 3/3 BLOCKED |
| `run_p4_mutations` | 14/14 CAUGHT |
| `run_p4_round4_probes` | 12/12 rejected（每个 synchronized re-seal/re-hash/re-label 尝试） |
| P1/P2/P3 suites | P2/P3 在此 worktree 缺失 — integration BLOCKED |

### 2. Round 4 关键实现主张

1. **Type split**：`VerifiedProductionP3Bundle` / `SyntheticP3FixtureBundle` 是两个独立 public type，生产与 fixture 管线不可互换。
2. **`apply_pin=False` 移除**：生产 consumer 无 bypass。
3. **Execution-authority registry**：`P4AuthorityRegistry`/`PRODUCTION_REGISTRY` process-local；verified production consumer 是唯一 producer，注册 **exact object**（identity + canonical content hash）；复制/重建/重标/重封对象即使是 byte-identical 也被 reject。
4. **Pin 发布在 P4 之外**：从 `reports/p3/p3_p4_interface_pin.json` 只读引用（integrator-owned）。
5. **Owning P1/P2 verifiers**：`P1ReceiptVerifier`/`P2ReceiptVerifier` 按 owning frozen Gate authority 验证。
6. **真实 authority 缺失时**：`resolve_bundle()` 返回 typed BLOCKED。

## 三、任务书 checklist（final_plan §7，审核依据）

- P4-T1 Independent evidence identity（每条 evidence 独立身份 + 内容 hash）
- P4-T2 Support aggregation（evidence-bound，非概率）
- P4-T3 Counterevidence（仅允许型，缺席永不负面）
- P4-T4 Baseline ranker（strict-only、确定性）
- P4-T5 Applicability（结构性）
- P4-T6 Typed abstention（优先级冻结）
- P4-T7 PredictionResult（不变量 + 系统失败分离）
- P4-T8 Immutable run/trace/manifest（freeze 原子、child 校验）
- Gate P4：G01-G14（machinery G01-G11 PASS-capable on synthetic；G12-G14 real-input authority）

## 四、上一轮（Round 3 audit）mandatory findings（本轮必须逐条核对关闭状态）

### P4-R3-A — bundle/receipt/pin self-attested 而非 upstream-authoritative（P0）
- 要求：receipt 必须由 owning Gate authority 产生，不能是 caller 自洽 hash；pin 必须 integrator-owned 不能 P4 自设 accepted；不得有 public bypass（apply_pin=False）。

### P4-R3-B — candidate/feature/evidence 内容仍 caller-recomputable（P0）
- 要求：生产管线不得接受 caller 提供的 evidence_records/feature_observations/counterevidence_contexts；feature 应由 P4 内从 verified evidence 派生；evidence_content_hashes 必须与真实 evidence 记录核对；candidate/evidence 必须绑定真实 P3/P1 authority；ordinal 0..3、frozen key、去重。

### P4-R3-C — upstream hash 与 interface validation 仍 optional/self-declared（P1）
- 要求：决定相关 hash/ID 必须 mandatory（缺失即 BLOCKED）；pin 必须集成 canonical path/file hash/content hash/schema hash/producer commit/accepted-evidence-kind 一起验证；fixture 永远不能满足 production pin。

### P4-R3-D — Round 3 audit receipts 与 changed-file counts 不一致（P1）
- 要求：路径归一化、separate counts、one parent session nonce 贯穿 Gate/mutation、报告记录真实命令与 cwd。

## 五、独立重放结果（审计者已客观重跑，与提交一致）

| Check | 独立重放 |
|---|---|
| `pytest tests/p4` | **248 passed**（与提交一致） |
| `pytest tests/contracts` | **290 passed**（pytest 9.1.1 环境） |
| `run_p4_gate` | **11/11 PASS + 3/3 BLOCKED**（安装 pytest-json-report 后） |
| `run_p4_mutations` | **14/14 CAUGHT** |
| `run_p4_round4_probes` | **12/12 rejected** |

**环境备注**：G11 依赖 `pytest-json-report`（pyproject dev 已声明，默认环境未装时 G11 FAIL）；contracts 依赖 pytest>=8.0（lock 9.1.1）。均非代码缺陷，属环境复现前提。

## 六、现有代码结构（供你判断绕过面）

- `reaction_agent/authority/registry.py`：`verify()` = `is not` identity + content_hash 对比；`_RegistrationCapability` 门控注册；PRODUCTION_REGISTRY 单例。
- `reaction_agent/authority/receipts.py`：`P2ReceiptVerifier`/`P1ReceiptVerifier` — shape 检查 6 字段、hash 自洽、status/gate_version 精确匹配、`_cross_bind` 双方都声明才对比。
- `reaction_agent/adapters/p3_consumer.py`：`load()`（manifest+pin+artifact 验证）、`load_p2/p1_receipt()`（从 P1/P2 Gate 报告文件提取 receipt）、`resolve_bundle()`（注册 exact object）。
- `reaction_agent/adapters/p3_interface_pin.py`：`verify_interface_pin` — 对 manifest 做 file/content/schema hash + canonical path + status 验证。
- `reaction_agent/schemas/p4/bundle.py`：`_seal_preimage` 覆盖全部决策字段；`compute_seal()` 公开；`verify_receipts()` 构造 expected（namespace + current_run_artifact_hash）后调 owning verifiers。

---

## 请输出

编号疑点清单，每条含：**疑点** / **要验证什么** / **怀疑等级**。至少覆盖但不限于：receipt 可伪造性、artifact 与 pin 的绑定、registry 的 exact-object 语义、跨进程/跨会话语义、上轮 P4-R3-A/B/C/D 各自的关闭状态。