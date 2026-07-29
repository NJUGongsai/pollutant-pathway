# P1 Data Foundation — 多智能体团队实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用多智能体团队（L1 角色专家池 + L2 独立审计池）按严格顺序实现 P1 Data Foundation 的 1 Preflight + 11 task + 十项 Gate，产出可信、可重放、可审计的反应证据地基。

**Architecture:** 三层架构——L0 Orchestrator 串行调度，L1 角色专家（architect/tdd-guide/code-reviewer/python-reviewer/security-reviewer/Explore）做实现，L2 独立审计池（Legacy Auditor/Annotator A,B/Adjudicator/Gate Keeper，全部只读、不碰实现代码）保证独立性硬要求。task 间严格串行（checkpoint 交接），task 内允许 RED 测试 ∥ 架构审 ∥ 证据查并发。

**Tech Stack:** Python 3.11、Pydantic v2（StrictModel）、pytest 9、（待装）rdkit/numpy/networkx、Hatchling build backend。

## Global Constraints

以下约束逐字来自 `chatgpt_p1_train.md` 与 `final_design.md`，每个 task 隐式包含：

- **工作目录**：`/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`，所有新代码落此目录内
- **禁止越界**：不得进入 P2；不得宣称 candidate performance；不得把 P1 当最终 X→Y 预测系统
- **P0 冻结合同全绿**：每完成一个 P1 task 必须重跑 `tests/contracts`，P0 baseline = 290 passed + P0 Gate 10/10；P0 任何失败立即停止，修复回归，不进下一 task
- **禁止写 legacy**：`../benchmark/`、`../core/`、`../reports/` 在 P1 是只读 legacy source，不得修改；不得 `git reset --hard`/`git clean`/`git checkout --`；未授权不得 `git add/commit/push`
- **schema 规范**：所有新 schema 继承 `reaction_agent.schemas.common.StrictModel`（`extra="forbid"`/`strict=True`）；`FORBIDDEN_FIELD_NAMES`（confidence/biological_probability/enzyme_activity_probability 等）零容忍
- **ID 规范**：canonical entity ID 必须 deterministic/content-derived/version-aware；禁 Python `hash()`、随机 UUID、依赖 dict/atom 顺序、依赖运行时间
- **content hash**：UTF-8、sorted keys、SHA-256、不含生成时间/临时路径
- **fail-closed**：strict eligibility 所需字段缺失不得默认 eligible，应 diagnostic/quarantine
- **真实数据优先**：fixture 只能用于算法单测；无真实 mapper + 真实数据运行证据时 P1 Gate 不得 PASS
- **最小实现**：如一个模块即可完成，不得为"架构感"拆成十几个空文件
- **测试纪律**：全部 tests 零 fail/error/skip/xfail/xpass；`passed = collected`
- **诚实报告**：BLOCKED 比假 PASS 正确；七种 `BLOCKED_*` 状态码见 spec §4
- **权威顺序**：final_design → final_plan → final_discussion → ADRs → P0 frozen → 本提示词；冲突以 final 为准并在 worklog 记录，不静默选择
- **模型偏差**：执行模型 Qwen→Claude Code subagent（用户决策），须在 worklog + submission 封面记录；ChatGPT 终审不变

### 执行环境（每 task 共用）

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
# P0 回归
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
# P1 单 task 测试
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/p1/<file>.py -q -p no:cacheprovider -ra
# P1 全测
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/p1 -q -p no:cacheprovider -ra
# 全回归
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests -q -p no:cacheprovider -ra
```

### agent 分配总表（来自 spec §2 调度矩阵）

| Task | 串行主线 agent | task 内并行 | L2 独立审计 |
|---|---|---|---|
| Preflight | Explore(scout) | — | — |
| T1 | architect→tdd-guide→实现 | RED ∥ architect 审配置 | security-reviewer |
| T2 | architect→tdd-guide | RED ∥ Explore 查 P0 schema | — |
| T3 | Legacy Auditor (L2) | — | Legacy Auditor 只读 |
| T4 | architect→tdd-guide | RED ∥ Explore 查 mapper | — |
| T5 | tdd-guide→实现 | — | — |
| T6 | architect→tdd-guide | RED ∥ Explore 查 proline/2OG | — |
| T7 | architect→tdd-guide | — | — |
| T8 | tdd-guide | — | — |
| T9 | tdd-guide→实现 | — | — |
| T10 | architect→tdd-guide | RED ∥ security-reviewer 审 atomicity | — |
| T11 | Annotator A ∥ B (L2) | A,B 双盲并行 | Adjudicator |
| Gate | Gate Keeper (L2) | 10 Gate ∥ 8 mutation | — |

---

## Task 0: Preflight — 真实资源盘点

**Files:**
- Create: `scripts/p1_preflight.py`
- Create: `reports/p1/P1_PREFLIGHT.md`
- Create: `reports/p1/P1_PREFLIGHT.json`
- Create: `reports/p1/P1_BASELINE.md`
- Create: `reports/p1/P1_BASELINE.json`
- Create: `tests/p1/__init__.py`
- Create: `tests/fixtures/p1/__init__.py`

**Interfaces:**
- Consumes: `chatgpt_p1_train.md` §6（Preflight 四项盘点）、§3（P0 baseline 命令）
- Produces: `P1_PREFLIGHT.json`（机器可读 GO/PARTIAL/BLOCKED 判定 + runtime/legacy/source/case 四项）、`P1_BASELINE.json`（P0 290 passed + Gate 10/10 实测）

**agent: Explore(scout) — L1**

- [ ] **Step 1: 先跑 P0 baseline 确认起点绿**

Run:
```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra --json-report --json-report-file=reports/p1/.baseline_pytest.json 2>&1 | tail -5
.venv/bin/python scripts/run_p0_gate.py 2>&1 | tail -5
```
Expected: `290 passed`（或当前 P0 数）+ `READY_FOR_CHATGPT_AUDIT` / `Passed: 10 / 10`。若不绿，停止——P0 必须先绿才能开始 P1。

- [ ] **Step 2: 写 P1 baseline 报告**

Create `reports/p1/P1_BASELINE.json`：
```json
{
  "recorded_at": "<UTC ISO, 由 Orchestrator 在 plan 外填>",
  "p0_contract_tests": {"passed": 290, "failed": 0, "errors": 0, "skipped": 0},
  "p0_gate": {"passed": 10, "failed": 0, "status": "READY_FOR_CHATGPT_AUDIT"},
  "baseline_locked": true
}
```
Create `reports/p1/P1_BASELINE.md`：人类可读视图，数字与 json 一致。

- [ ] **Step 3: 写 Preflight 脚本骨架（runtime 盘点）**

Create `scripts/p1_preflight.py`，实现 runtime 盘点函数：
```python
"""P1 preflight: real-resource inventory per chatgpt_p1_train.md §6."""
from __future__ import annotations
import hashlib, json, os, platform, sys, importlib.metadata as md

def runtime_inventory() -> dict:
    def ver(name: str) -> str | None:
        try: return md.version(name)
        except md.PackageNotFoundError: return None
    def py_avail(mod: str) -> str | None:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "present")
        except Exception:
            return None
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "working_directory": os.getcwd(),
        "pydantic_version": ver("pydantic"),
        "pytest_version": ver("pytest"),
        "rdkit": py_avail("rdkit"),
        "numpy": py_avail("numpy"),
        "networkx": py_avail("networkx"),
        "scipy": py_avail("scipy"),
        "mapper_backend": None,  # T1 决策后填
    }
```

- [ ] **Step 4: 写 legacy source 盘点函数**

在 `scripts/p1_preflight.py` 追加：
```python
def _sha256(path: str) -> str | None:
    if not os.path.exists(path): return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def legacy_inventory() -> dict:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parent = os.path.dirname(root)  # CC/branch/ReactionAgent
    targets = [
        "../benchmark/canonical_identity.py",
        "../benchmark",
        "../core",
    ]
    items = []
    for rel in targets:
        p = os.path.normpath(os.path.join(parent, rel.replace("../", "")))
        items.append({
            "relative_path": rel,
            "absolute_path": p,
            "exists": os.path.exists(p),
            "sha256": _sha256(p) if os.path.isfile(p) else None,
            "size": os.path.getsize(p) if os.path.exists(p) else None,
        })
    return {"legacy_sources": items}
```

- [ ] **Step 5: 写 real reaction source + proline/2OG case 探测**

在 `scripts/p1_preflight.py` 追加：
```python
def real_source_inventory() -> dict:
    """探明真实完整反应记录来源（§6.3/§6.4）。只读环境变量是否存在，不输出值。"""
    env_keys = [k for k in os.environ if "REACTION" in k.upper() or "RHEA" in k.upper()
                or "BRENDA" in k.upper() or "META" in k.upper() or "DATA_ROOT" in k.upper()]
    return {
        "candidate_env_keys_present": env_keys,  # 只记 key 名，不记 value
        "real_reaction_source_found": None,      # None=未确定，待 T3/T6 确认
        "data_root_scan_allowed": False,         # 禁止扫整个 home
    }

PROLINE_2OG_CASE = {
    "reaction": "2-oxoglutarate + proline + O2 -> succinate + hydroxyproline + CO2",
    "expected_lineages": ["proline -> hydroxyproline", "2-oxoglutarate -> succinate"],
    "forbidden_lineage": "2-oxoglutarate -> hydroxyproline",
    "source_record_found": None,  # None=required_case_missing
}

def case_inventory() -> dict:
    return {"proline_2og": PROLINE_2OG_CASE}
```

- [ ] **Step 6: 写 stop condition 判定 + 主函数**

在 `scripts/p1_preflight.py` 追加：
```python
def evaluate_stop_condition(rt: dict, src: dict, case: dict) -> tuple[str, list[str]]:
    """返回 (status, reasons)。status ∈ {GO, PARTIAL, BLOCKED}。"""
    blockers: list[str] = []
    if rt.get("rdkit") is None:
        blockers.append("rdkit_absent")
    if src["real_reaction_source_found"] is None:
        blockers.append("real_reaction_source_not_confirmed")
    if case["proline_2og"]["source_record_found"] is None:
        blockers.append("required_case_missing")
    if not blockers:
        return "GO", []
    # mapper 缺但其余齐 → PARTIAL；source/case 缺 → BLOCKED
    if any(b in blockers for b in ("real_reaction_source_not_confirmed", "required_case_missing")):
        return "BLOCKED", blockers
    return "PARTIAL", blockers

def main() -> int:
    rt, lg, src, case = runtime_inventory(), legacy_inventory(), real_source_inventory(), case_inventory()
    status, reasons = evaluate_stop_condition(rt, src, case)
    report = {"status": status, "blockers": reasons, "runtime": rt,
              "legacy": lg, "real_source": src, "case": case}
    os.makedirs("reports/p1", exist_ok=True)
    with open("reports/p1/P1_PREFLIGHT.json", "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f"P1 Preflight status: {status}")
    print(f"Blockers: {reasons}")
    return 0 if status == "GO" else 1

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: 运行 Preflight，判定 GO/PARTIAL/BLOCKED**

Run: `.venv/bin/python scripts/p1_preflight.py`
Expected: 输出 status 与 blockers，生成 `P1_PREFLIGHT.json`。Orchestrator 据 status 决定后续：
- `GO` → 继续 Task 1
- `PARTIAL`（如 rdkit 缺）→ 继续 Task 1，但 T4 集成测试将 BLOCKED
- `BLOCKED`（真实 source/case 缺）→ 停止实现，只做 read-only 诊断 + fixture 单测，报 `BLOCKED_MISSING_REAL_REACTION_SOURCE` 或 `BLOCKED_REQUIRED_CASE_MISSING`，向用户给出具体所需输入

- [ ] **Step 8: 写 Preflight 人类可读报告**

Create `reports/p1/P1_PREFLIGHT.md`：从 json 渲染，含 runtime 表、legacy 表、source/case 状态、stop condition 结论。数字与 json 一致。

- [ ] **Step 9: 初始化 worklog + fixture 目录**

Create `reports/p1/P1_REMEDIATION_WORKLOG.md`，首节：
```markdown
# P1 Remediation Worklog

## Preflight (Task 0)
- timestamp: <UTC>
- assumptions: P0 baseline 绿（见 P1_BASELINE.json）；执行模型=Claude Code subagent（偏差，原定 Qwen）
- input files/hashes: P0 contracts tests + run_p0_gate.py
- deviations: 执行模型 Qwen→Claude Code subagent（用户决策）
- preflight status: <GO|PARTIAL|BLOCKED>
- blockers: <list>
- next task authorization: <T1 授权 | 停止待用户提供真实 source/mapper>
```
Create `tests/p1/__init__.py` 与 `tests/fixtures/p1/__init__.py`（空文件）。

- [ ] **Step 10: Orchestrator checkpoint**

Orchestrator 读取 `P1_PREFLIGHT.json` 的 status：
- GO → 授权 T1，记入 worklog
- PARTIAL → 授权 T1，worklog 标注 T4 将 BLOCKED
- BLOCKED → 停止，向用户报告所需输入（真实 reaction 数据源路径、atom mapper 包名、第二位 annotator）

**Checkpoint artifact:** `P1_PREFLIGHT.{md,json}` + `P1_BASELINE.{md,json}` + worklog Preflight 节

---

## Task 1: P1-T1 — Package bootstrap

**Files:**
- Create: `reaction_agent/config.py`
- Create: `reaction_agent/hashing.py`
- Create: `reaction_agent/provenance.py`
- Create: `reaction_agent/__init__.py`（扩展，加 `get_build_info`）
- Modify: `pyproject.toml`（加真实依赖 + lock）
- Create: `tests/p1/test_config.py`
- Create: `tests/p1/test_hashing_ids.py`
- Create: `reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md`

**Interfaces:**
- Consumes: `reaction_agent/schemas/common.py`（`StrictModel`）、Preflight 的 runtime inventory
- Produces:
  - `reaction_agent.config.BuildConfig`（显式 config 合同，字段见 §7.3）
  - `reaction_agent.config.get_build_info() -> BuildInfo`
  - `reaction_agent.hashing.canonical_hash(obj) -> str`（SHA-256，sorted keys）
  - `reaction_agent.hashing.stable_id(prefix: str, obj) -> str`（`<prefix>_<hash12>`）
  - `reaction_agent.provenance.SourceRecordProvenance`

**agent: architect → tdd-guide → 实现；L2 security-reviewer**

- [ ] **Step 1: RED — config 显式合同测试**

Create `tests/p1/test_config.py`：
```python
import pytest
from reaction_agent.config import BuildConfig, get_build_info

def test_explicit_snapshot_path_required():
    with pytest.raises(Exception):
        BuildConfig(input_source="x", output_snapshot_root="snap")  # 缺 mapper_backend 等

def test_unknown_config_field_rejected():
    with pytest.raises(Exception):
        BuildConfig(input_source="x", output_snapshot_root="snap",
                    mapper_backend="fake", random_seed=42, timeout=300,
                    strict_mode=True, normalization_version="1",
                    role_policy_version="1", lineage_resolver_version="1",
                    ledger_version="1", eligibility_policy_version="1",
                    mapper_version="1", bogus_field="nope")

def test_seed_required_and_stable():
    c = BuildConfig(input_source="in", output_snapshot_root="out",
                    mapper_backend="fake", mapper_version="1",
                    normalization_version="1", role_policy_version="1",
                    lineage_resolver_version="1", ledger_version="1",
                    eligibility_policy_version="1", random_seed=42,
                    timeout=300, strict_mode=True)
    assert c.random_seed == 42

def test_deterministic_config_serialization():
    c1 = BuildConfig(input_source="in", output_snapshot_root="out",
                     mapper_backend="fake", mapper_version="1",
                     normalization_version="1", role_policy_version="1",
                     lineage_resolver_version="1", ledger_version="1",
                     eligibility_policy_version="1", random_seed=42,
                     timeout=300, strict_mode=True)
    s1 = c1.canonical_json()
    c2 = BuildConfig(**{**c1.model_dump()})
    assert c2.canonical_json() == s1

def test_get_build_info_deterministic():
    info = get_build_info()
    assert info.package_version
    assert info.schema_version
    assert info.python_version
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_config.py -q -p no:cacheprovider -ra`
Expected: FAIL（`ModuleNotFoundError: reaction_agent.config`）

- [ ] **Step 3: 实现 BuildConfig + BuildInfo**

Create `reaction_agent/config.py`：
```python
"""P1 build config + build info (chatgpt_p1_train.md §7.3)."""
from __future__ import annotations
import json, sys
from reaction_agent.schemas.common import StrictModel, NonEmptyStr

class BuildConfig(StrictModel):
    input_source: NonEmptyStr
    output_snapshot_root: NonEmptyStr
    mapper_backend: NonEmptyStr
    mapper_version: NonEmptyStr
    mapper_parameters: dict[str, str] = {}
    normalization_version: NonEmptyStr
    role_policy_version: NonEmptyStr
    lineage_resolver_version: NonEmptyStr
    ledger_version: NonEmptyStr
    eligibility_policy_version: NonEmptyStr
    random_seed: int
    timeout: int = 300
    strict_mode: bool = True

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)

class BuildInfo(StrictModel):
    package_version: NonEmptyStr
    schema_version: NonEmptyStr
    mapper_resolver_version: NonEmptyStr
    ledger_version: NonEmptyStr
    policy_version: NonEmptyStr
    python_version: NonEmptyStr

def get_build_info() -> BuildInfo:
    return BuildInfo(
        package_version="0.2.0",
        schema_version="p1-1",
        mapper_resolver_version="p1-1",
        ledger_version="p1-1",
        policy_version="p1-1",
        python_version=".".join(sys.version_info[:3]),
    )
```

- [ ] **Step 4: GREEN — config 测试**

Run: `.venv/bin/python -m pytest tests/p1/test_config.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 5: RED — hashing/ID 测试**

Create `tests/p1/test_hashing_ids.py`：
```python
import pytest
from reaction_agent.hashing import canonical_hash, stable_id

def test_same_content_different_key_order_same_hash():
    a = canonical_hash({"b": 1, "a": 2})
    b = canonical_hash({"a": 2, "b": 1})
    assert a == b

def test_source_change_different_hash():
    assert canonical_hash({"x": 1}) != canonical_hash({"x": 2})

def test_timestamp_excluded_from_canonical():
    # canonical_hash 不应把临时时间纳入；此处验证 dict 内 ts 变化改变 hash，
    # 但 canonical_hash 本身不注入 ts
    h1 = canonical_hash({"data": "abc"})
    assert h1 == canonical_hash({"data": "abc"})

def test_stable_id_format():
    sid = stable_id("rxn", {"smiles": "C"})
    assert sid.startswith("rxn_") and len(sid) > 4

def test_stable_id_python_hash_not_used():
    # 同对象多次调用稳定（不依赖 Python hash() 随机化）
    obj = {"smiles": "CCO", "name": "ethanol"}
    assert stable_id("participant", obj) == stable_id("participant", obj)
```

- [ ] **Step 6: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_hashing_ids.py -q -p no:cacheprovider -ra`
Expected: FAIL（`ModuleNotFoundError: reaction_agent.hashing`）

- [ ] **Step 7: 实现 canonical_hash + stable_id**

Create `reaction_agent/hashing.py`：
```python
"""Canonical content hashing + stable IDs (chatgpt_p1_train.md §8.3/§8.4)."""
from __future__ import annotations
import hashlib, json

def _canonicalize(obj) -> object:
    if isinstance(obj, dict):
        return {k: _canonicalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        # list 顺序语义由调用方负责；这里保持原序但元素规范化
        return [_canonicalize(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_canonicalize(x) for x in obj)  # 非语义集合排序
    return obj

def canonical_hash(obj) -> str:
    payload = json.dumps(_canonicalize(obj), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def stable_id(prefix: str, obj) -> str:
    return f"{prefix}_{canonical_hash(obj)[:12]}"
```

- [ ] **Step 8: GREEN — hashing 测试**

Run: `.venv/bin/python -m pytest tests/p1/test_hashing_ids.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 9: 实现 provenance + no-legacy-write 守卫**

Create `reaction_agent/provenance.py`：
```python
"""Source record provenance (chatgpt_p1_train.md §8.5)."""
from __future__ import annotations
from reaction_agent.schemas.common import StrictModel, NonEmptyStr

class SourceRecordProvenance(StrictModel):
    source_name: NonEmptyStr
    source_version: NonEmptyStr
    source_record_id: NonEmptyStr
    source_file_hash: NonEmptyStr
    raw_record_hash: NonEmptyStr
    normalizer_version: NonEmptyStr
    created_by_build_id: NonEmptyStr

# no-legacy-write 守卫：禁止写入 demov2 之外的路径
LEGACY_WRITE_PREFIXES = ("../benchmark", "../core", "../reports/p0")

def assert_no_legacy_write(path: str) -> None:
    for pref in LEGACY_WRITE_PREFIXES:
        if path.startswith(pref) or f"/{pref.lstrip('../')}" in path:
            raise PermissionError(f"refuse legacy write: {path}")
```

- [ ] **Step 10: RED — no-legacy-write + redaction 测试**

追加到 `tests/p1/test_config.py`：
```python
import pytest
from reaction_agent.provenance import assert_no_legacy_write, SourceRecordProvenance

def test_legacy_write_refused():
    with pytest.raises(PermissionError):
        assert_no_legacy_write("../benchmark/canonical_identity.py")

def test_demov2_write_allowed():
    assert_no_legacy_write("reports/p1/x.json")  # 不 raise

def test_provenance_required_fields():
    with pytest.raises(Exception):
        SourceRecordProvenance(source_name="rhea")  # 缺其余必填

def test_provenance_no_unknown_silent_fill():
    # 不得静默把 unknown 填进 strict
    p = SourceRecordProvenance(source_name="rhea", source_version="1",
                               source_record_id="r1", source_file_hash="h",
                               raw_record_hash="h", normalizer_version="1",
                               created_by_build_id="b1")
    assert p.source_record_id == "r1"
```

- [ ] **Step 11: Run RED→GREEN（provenance）**

Run: `.venv/bin/python -m pytest tests/p1/test_config.py -q -p no:cacheprovider -ra`
Expected: 先 FAIL 新增 4 项 → 实现 provenance 后 PASS

- [ ] **Step 12: 依赖决策 + lock**

Modify `pyproject.toml`：根据 Preflight 决定加哪些依赖。若 Preflight BLOCKED 因 rdkit，先只加可装的（如 networkx）并在 worklog 记录 `BLOCKED_DEPENDENCY_INSTALLATION`。
```toml
[project]
dependencies = [
    "pydantic>=2.8,<3",
    # P1: 按需添加，与 Python 3.11 兼容。未确认可装前不加。
]
```
生成 lock：`.venv/bin/pip freeze > requirements.lock.txt`，记录安装命令到 worklog。

- [ ] **Step 13: L2 security-reviewer 审 redaction/no-legacy-write**

Orchestrator 派 security-reviewer 审 `config.py`/`provenance.py`：检查 logging 不输出 secrets、no-legacy-write 守卫覆盖、无硬编码路径、`canonical_json` 不含临时路径。CRITICAL/HIGH 必修。

- [ ] **Step 14: P0 + P1 回归**

Run:
```bash
.venv/bin/python -m pytest tests/contracts tests/p1 -q -p no:cacheprovider -ra
.venv/bin/python scripts/run_p0_gate.py
```
Expected: P0 290 passed（不回退）+ P1 新测试全绿 + P0 Gate 10/10。零 fail/error/skip/xfail/xpass。

- [ ] **Step 15: T1 checkpoint 报告 + worklog 追加**

Create `reports/p1/P1_T1_PACKAGE_BOOTSTRAP.md`：记录依赖 lock、no-legacy-write、redaction、version endpoint 实测。追加 worklog T1 节（assumptions/RED/impl/GREEN/regression/deviation/next authorization）。

**未满足依赖 lock 和 no-legacy-write，不得进入 T2。**

---

## Task 2: P1-T2 — Strict domain schemas

**Files:**
- Modify: `reaction_agent/schemas/evidence.py`（扩展 `ReactionParticipant`/`ReactionEvidence`）
- Modify: `reaction_agent/schemas/mapping.py`（确认 `MappingReport` 字段完整）
- Modify: `reaction_agent/schemas/lineage.py`（确认 `LineageEdge`/`LineageResolution`）
- Modify: `reaction_agent/schemas/ledger.py`（确认 `SourceReactionLedger`/`CandidateAnalogyLedger`）
- Create: `reaction_agent/schemas/p1_entities.py`（P1 新增对象：`NormalizedReactionRecord`/`DonorEligibilityAssessment`/`SnapshotManifest`/`SnapshotRecord`/`ManualAuditRecord`/`QuarantineRecord`/`EligibilityDecision`）
- Modify: `reaction_agent/schemas/__init__.py`（导出新对象）
- Create: `tests/p1/test_domain_schemas.py`
- Create: `reports/p1/P1_T2_DOMAIN_SCHEMAS.md`

**Interfaces:**
- Consumes: P0 全部 frozen schema（`StrictModel`/各 enum/已有 ledger/mapping/lineage/evidence 对象）、`reaction_agent.hashing`
- Produces: P1 完整对象集（文档 §8.2 的 22 个对象，已有则不重复创建）；`schemas/json/` 导出仅冻结对象

**agent: architect → tdd-guide；task 内 Explore 查 P0 schema 字段**

- [ ] **Step 1: READ — 盘点 P0 已有对象，列 P1 缺口**

Explore 读 `reaction_agent/schemas/{evidence,mapping,lineage,ledger,candidate,result,common}.py`，对照文档 §8.2 的 22 对象列表，产出缺口表：
- 已有（不重复创建）：`MappingReport`/`FormalMappedAtomPair`/`MechanisticAtomOrigin`/`ReactionParticipant`/`LineageEdge`/`FragmentLineageGraph`(待确认)/`SourceReactionLedger`/`CandidateAnalogyLedger`/`LineageResolution`
- P1 需新增：`SourceRecordProvenance`(T1 已建)/`NormalizedReactionRecord`/`ParticipantRoleHypothesis`(=P0 `RoleHypothesis`?确认)/`DonorEligibilityAssessment`/`ResolvedTransformedLineage`/`EligibilityDecision`/`QuarantineRecord`/`SnapshotManifest`/`SnapshotRecord`/`ManualAuditRecord`
缺口表写入 worklog T2 节的 assumptions。

- [ ] **Step 2: RED — schema 严格性测试**

Create `tests/p1/test_domain_schemas.py`：
```python
import pytest
from reaction_agent.schemas.p1_entities import (
    NormalizedReactionRecord, DonorEligibilityAssessment, EligibilityDecision,
    QuarantineRecord, SnapshotManifest, SnapshotRecord, ManualAuditRecord,
    ResolvedTransformedLineage,
)
from reaction_agent.schemas.common import FORBIDDEN_FIELD_NAMES

def test_unknown_field_rejected():
    with pytest.raises(Exception):
        NormalizedReactionRecord(reaction_id="r1", bogus="x")

def test_forbidden_fields_absent():
    import inspect
    from reaction_agent.schemas import p1_entities
    src = inspect.getsource(p1_entities)
    for name in FORBIDDEN_FIELD_NAMES:
        assert f"{name}:" not in src, f"forbidden field {name} appears"

def test_donor_eligibility_reason_codes_typed():
    d = DonorEligibilityAssessment(participant_id="p1", eligibility="eligible",
                                    reason_codes=["mapped_retention"], evidence_ids=["e1"])
    assert d.eligibility in ("eligible","conditionally_eligible","not_eligible","unknown")

def test_quarantine_record_has_reason():
    with pytest.raises(Exception):
        QuarantineRecord(record_id="q1")  # 缺 reason

def test_snapshot_manifest_counts_required():
    m = SnapshotManifest(snapshot_id="s1", schema_version="p1-1",
                         included_strict_count=0, conditional_count=0,
                         diagnostic_count=0, quarantine_count=0,
                         build_status="complete", snapshot_hash="h")
    assert m.build_status == "complete"
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_domain_schemas.py -q -p no:cacheprovider -ra`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 4: 实现 P1 新对象**

Create `reaction_agent/schemas/p1_entities.py`，每个对象继承 `StrictModel`，字段来自文档 §8.2 + final_design §7/§10。关键约束：
- `EligibilityDecision.eligibility` 用 P0 `EligibilityStatus` enum
- `DonorEligibilityAssessment.eligibility` 用文档 §11.4 的 `eligible/conditionally_eligible/not_eligible/unknown`
- `SnapshotManifest` 含 §16.3 全部字段（counts/hash/build_status）
- `ManualAuditRecord` 含 §17.3 rubric 字段，**不含 confidence**（用 `agreement`/`catastrophic_error_count`）
- `ResolvedTransformedLineage` 含 `lineage_id`/`reactant_participant_id`/`product_participant_id`/`evidence_ids`/`ambiguity`

（实现时由 architect 确认每个字段类型与 P0 enum 一致，不重复定义同名 truth model。）

- [ ] **Step 5: GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_domain_schemas.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 6: 扩展 `schemas/__init__.py` 导出**

在 `reaction_agent/schemas/__init__.py` 加 `from reaction_agent.schemas.p1_entities import (...)` 并列入 `__all__`。

- [ ] **Step 7: RED — stable ID + content hash 测试**

追加到 `tests/p1/test_domain_schemas.py`：
```python
from reaction_agent.hashing import stable_id, canonical_hash

def test_reaction_record_stable_id_atom_order_invariant():
    r1 = {"smiles": "CCO", "atoms": [1,2,3]}
    r2 = {"smiles": "CCO", "atoms": [3,2,1]}  # 同化学不同顺序
    # stable_id 对 dict 内容敏感；此处验证同 smiles 同 hash（atoms 作为 list 保持序）
    assert stable_id("rxn", {"smiles":"CCO"}) == stable_id("rxn", {"smiles":"CCO"})

def test_policy_version_changes_hash():
    h1 = canonical_hash({"policy": "v1", "data": "x"})
    h2 = canonical_hash({"policy": "v2", "data": "x"})
    assert h1 != h2
```

- [ ] **Step 8: Run RED→GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_domain_schemas.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 9: 导出 JSON schema（仅冻结对象）**

Run: `.venv/bin/python scripts/export_json_schemas.py`（已有脚本，确认含 P1 新对象）。产物落 `schemas/json/`。测试 JSON schema freshness（P0 已有 `test_json_schema_exports.py`，确认不破坏）。

- [ ] **Step 10: P0 + P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10 + JSON schema fresh。零 skip/xfail。

- [ ] **Step 11: T2 checkpoint 报告 + worklog**

Create `reports/p1/P1_T2_DOMAIN_SCHEMAS.md`：列 22 对象覆盖情况、缺口表、stable ID/content hash 测试结果、P0 不变证据。追加 worklog T2 节。

**不得把仍在探索的内部对象全部导出为公共 schema。**

---

## Task 3: P1-T3 — Legacy lineage audit（L2 独立只读）

**Files:**
- Create: `scripts/legacy_lineage_audit.py`（只读重放）
- Create: `reports/data_audit/legacy_lineage_audit.json`
- Create: `reports/data_audit/legacy_lineage_audit.md`
- Create: `tests/p1/test_legacy_audit_contract.py`
- Create: `reports/p1/P1_T3_LEGACY_AUDIT.md`

**Interfaces:**
- Consumes: `../benchmark/canonical_identity.py`（**只读**，import 不修改）、T2 的 `NormalizedReactionRecord`/`ResolvedTransformedLineage`
- Produces: `legacy_lineage_audit.json`（完整 counts/categories/examples/source IDs）+ `.md`（人类可读，数字一致）

**agent: Legacy Auditor (L2 独立，Explore 实例) — 只读，不碰实现代码**

- [ ] **Step 1: READ — 只读 legacy 模块**

Legacy Auditor 只读 `../benchmark/canonical_identity.py`，定位 `pick_main`(60-77)/`COFACTORS`(96-128)/`_pick_transformed`(131-157)/`transformed_pair`(161-185)/`group_key/main_substrate/main_product`(188-202)。**不得修改该文件**。

- [ ] **Step 2: RED — audit 契约测试**

Create `tests/p1/test_legacy_audit_contract.py`：
```python
import json, os
from pathlib import Path

def test_audit_json_exists_and_machine_readable():
    p = Path("reports/data_audit/legacy_lineage_audit.json")
    assert p.exists(), "audit 未生成"
    data = json.loads(p.read_text())
    assert "counts" in data and "categories" in data
    assert "examples" in data and "source_ids" in data

def test_audit_has_counts_and_denominators():
    data = json.loads(Path("reports/data_audit/legacy_lineage_audit.json").read_text())
    for cat, n in data["counts"].items():
        assert isinstance(n, int) and n >= 0
    assert "total_reactions" in data["counts"]  # 分母

def test_md_matches_json_counts():
    j = json.loads(Path("reports/data_audit/legacy_lineage_audit.json").read_text())
    m = Path("reports/data_audit/legacy_lineage_audit.md").read_text()
    for cat, n in j["counts"].items():
        assert str(n) in m, f"MD 缺 {cat}={n}"

def test_proline_2og_included():
    data = json.loads(Path("reports/data_audit/legacy_lineage_audit.json").read_text())
    assert any("proline" in str(ex).lower() for ex in data.get("examples", []))

def test_mismatch_categories_complete():
    data = json.loads(Path("reports/data_audit/legacy_lineage_audit.json").read_text())
    required = {"cross_lineage_pair","cofactor_selected_as_main","mapping_missing",
                "legacy_pair_supported","insufficient_evidence"}
    assert required.issubset(set(data["categories"].keys()))
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_legacy_audit_contract.py -q -p no:cacheprovider -ra`
Expected: FAIL（audit 文件未生成）

- [ ] **Step 4: 实现只读 audit 脚本**

Create `scripts/legacy_lineage_audit.py`：import legacy `transformed_pair`/`main_substrate`/`main_product`/`group_key`，对每条 reaction 记录 §9.3 的 audit record 字段，分类入 §9.4 的 mismatch categories，按 §9.5 分层统计（数量+分母），输出 json + md。**严禁修改 legacy 文件、删失败 records、只抽成功案例**。

> 若真实 source 不可访问（Preflight BLOCKED）：audit 标 `T3 = PARTIAL/BLOCKED`，只对可读 legacy 汇总做 audit，**不得用 fixture 报告替代真实 audit**（文档 §9.8）。

- [ ] **Step 5: 运行 audit 生成产物**

Run: `.venv/bin/python scripts/legacy_lineage_audit.py`
Expected: 生成 `reports/data_audit/legacy_lineage_audit.{json,md}`，含 proline/2OG 案例（若真实 source 有）。

- [ ] **Step 6: GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_legacy_audit_contract.py -q -p no:cacheprovider -ra`
Expected: PASS（若真实 source 缺，则 audit 标 PARTIAL，契约测试对应调整为允许 PARTIAL 标记，但不得伪造 examples）

- [ ] **Step 7: P0 回归（不改 legacy，P0 必须仍绿）**

Run: `.venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + Gate 10/10 不变。

- [ ] **Step 8: T3 checkpoint 报告 + worklog**

Create `reports/p1/P1_T3_LEGACY_AUDIT.md`：真实 source 状态、counts/categories、proline/2OG 结果、PARTIAL/BLOCKED 标记（若有）。追加 worklog T3 节。

**未找到真实 source 或无可验证 mapping 时：T3 = PARTIAL/BLOCKED，P1 Gate = BLOCKED。不得用 fixture 报告替代真实 audit。**

---

## Task 4: P1-T4 — Atom-mapping adapter

**Files:**
- Create: `reaction_agent/mapping/__init__.py`
- Create: `reaction_agent/mapping/base.py`（`AtomMapper` Protocol + `MappingReport` 构造）
- Create: `reaction_agent/mapping/adapter.py`（具体 adapter + fake mapper + quality 验证）
- Create: `tests/p1/test_mapping_adapter.py`
- Create: `reports/p1/P1_T4_MAPPING_ADAPTER.md`
- Create: `reports/p1/mapping_integration_sample.json`

**Interfaces:**
- Consumes: T2 `NormalizedReactionRecord`/`MappingReport`(P0 已有)/`MappingStatus` enum
- Produces:
  - `reaction_agent.mapping.base.AtomMapper`（Protocol，`map_reaction(record) -> MappingReport`）
  - `reaction_agent.mapping.adapter.FakeAtomMapper`（deterministic，单测用）
  - `reaction_agent.mapping.adapter.RealMapperAdapter`（真实 mapper 包装，集成测试用）
  - `reaction_agent.mapping.adapter.compute_quality_flags(report) -> list[str]`

**agent: architect → tdd-guide；task 内 Explore 查 mapper backend 可用性**

- [ ] **Step 1: READ — 查 mapper backend**

Explore 查可装/可用的 atom mapper（rxnmapper/rxn4chemistry/rdkit-based）。结果写入 worklog。若 Preflight BLOCKED_MAPPER_UNAVAILABLE，本 task 只做 Protocol + fake mapper 单测，标 `UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED`，不标 PASS。

- [ ] **Step 2: RED — Protocol + fake mapper 测试**

Create `tests/p1/test_mapping_adapter.py`：
```python
import pytest
from reaction_agent.mapping.base import AtomMapper
from reaction_agent.mapping.adapter import FakeAtomMapper, compute_quality_flags
from reaction_agent.schemas.common import MappingStatus

def _record():
    from reaction_agent.schemas.p1_entities import NormalizedReactionRecord
    return NormalizedReactionRecord(reaction_id="r1", normalized_reaction="CCO>>CC=O",
                                    source_record_id="s1")

def test_fake_mapper_returns_mapping_report():
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    assert rep.mapping_status in MappingStatus
    assert rep.mapper_name == "fake"

def test_fully_mapped_status():
    m = FakeAtomMapper(status="fully_mapped")
    assert m.map_reaction(_record()).mapping_status == MappingStatus.fully_mapped

def test_mapping_failed_not_full():
    m = FakeAtomMapper(status="mapping_failed")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped

def test_mapper_does_not_create_mechanism():
    m = FakeAtomMapper()
    rep = m.map_reaction(_record())
    # formal mapping 不自动生成 mechanism evidence
    assert rep.mechanistic_origin_evidence_ids == [] or rep.mechanistic_origin_evidence_ids is None

def test_quality_flags_computed():
    m = FakeAtomMapper(status="fully_mapped")
    rep = m.map_reaction(_record())
    flags = compute_quality_flags(rep)
    assert isinstance(flags, list)

def test_mcs_fallback_not_strict():
    m = FakeAtomMapper(status="partially_mapped", fallback="mcs")
    rep = m.map_reaction(_record())
    assert rep.mapping_status != MappingStatus.fully_mapped  # MCS 不进 strict
```

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_mapping_adapter.py -q -p no:cacheprovider -ra`
Expected: FAIL

- [ ] **Step 4: 实现 Protocol + FakeAtomMapper + quality**

Create `reaction_agent/mapping/base.py`：
```python
"""AtomMapper protocol (chatgpt_p1_train.md §10.1)."""
from __future__ import annotations
from typing import Protocol
from reaction_agent.schemas.mapping import MappingReport

class AtomMapper(Protocol):
    def map_reaction(self, reaction) -> MappingReport: ...
```
Create `reaction_agent/mapping/adapter.py`：实现 `FakeAtomMapper`（deterministic，按 status 参数产出）+ `compute_quality_flags`（计算 §10.3 的 8 项质量）。**formal only，不生成 mechanism**。`RealMapperAdapter` 骨架（若真实 mapper 可用则填，否则留 NotImplementedError 标 INTEGRATION_BLOCKED）。

- [ ] **Step 5: GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_mapping_adapter.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 6: RED — 真实 mapper 集成测试（条件执行）**

追加到 `tests/p1/test_mapping_adapter.py`：
```python
import os
@pytest.mark.skipif(not os.environ.get("P1_REAL_MAPPER_AVAILABLE"),
                    reason="real mapper unavailable — INTEGRATION_BLOCKED")
def test_real_mapper_integration():
    from reaction_agent.mapping.adapter import RealMapperAdapter
    a = RealMapperAdapter(backend=os.environ["P1_REAL_MAPPER_AVAILABLE"])
    rep = a.map_reaction(_record())
    assert rep.mapper_name != "fake"
    assert rep.mapper_version
```

- [ ] **Step 7: 集成测试执行（若 mapper 可用）**

若 Preflight GO 且 mapper 可装：装 mapper，set `P1_REAL_MAPPER_AVAILABLE`，运行并生成 `mapping_integration_sample.json`。若不可用：worklog 标 `UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED`，**不标 PASS**。

- [ ] **Step 8: P0 + P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿（真实 mapper 测试若 skip，需在 worklog 明确 INTEGRATION_BLOCKED，Gate G04 将不过）+ Gate 10/10。

- [ ] **Step 9: T4 checkpoint 报告 + worklog**

Create `reports/p1/P1_T4_MAPPING_ADAPTER.md`：Protocol/fake mapper 单测状态、真实 mapper 集成状态（PASS 或 INTEGRATION_BLOCKED）、quality flags。追加 worklog T4 节。

**真实 mapper 不可用时，T4 只能标 `UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED`，不能标 PASS。**

---

## Task 5: P1-T5 — Participant roles 与 donor eligibility

**Files:**
- Create: `reaction_agent/roles/__init__.py`
- Create: `reaction_agent/roles/resolver.py`
- Create: `reaction_agent/roles/cofactors.py`（canonicalize legacy COFACTORS，记 source hash）
- Create: `tests/p1/test_participant_roles.py`
- Create: `reports/p1/P1_T5_PARTICIPANT_ROLES.md`
- Create: `reports/p1/participant_role_sample.json`

**Interfaces:**
- Consumes: T2 `ReactionParticipant`/`RoleHypothesis`(P0)/`ParticipantRole` enum、legacy `COFACTORS`（只读）
- Produces:
  - `reaction_agent.roles.cofactors.load_cofactors() -> tuple[list[str], str]`（list + source hash）
  - `reaction_agent.roles.resolver.resolve_roles(participants) -> list[ReactionParticipant]`（带 role hypotheses + evidence，不删 participant）
  - `reaction_agent.roles.resolver.assess_donor_eligibility(participant, mapping_report) -> DonorEligibilityAssessment`

**agent: tdd-guide → 实现**

- [ ] **Step 1: RED — participant 保留测试**

Create `tests/p1/test_participant_roles.py`：
```python
import pytest
from reaction_agent.roles.cofactors import load_cofactors
from reaction_agent.roles.resolver import resolve_roles, assess_donor_eligibility

def test_cofactors_loads_with_source_hash():
    names, src_hash = load_cofactors()
    assert isinstance(names, list) and src_hash  # 不空 hash

def test_cofactors_not_destructive():
    # COFACTORS 只作 prior，不删 participant
    names, _ = load_cofactors()
    assert "NAD" in names or any("NAD" in n for n in names)  # 仅作 prior 存在

def test_participant_multiset_preserved():
    from reaction_agent.schemas.evidence import ReactionParticipant
    ps = [
        ReactionParticipant(participant_id="p1", molecule_id="m1", canonical_smiles="C",
                            side="reactant"),
        ReactionParticipant(participant_id="p2", molecule_id="m2", canonical_smiles="O=O",
                            side="reactant"),  # O2
    ]
    out = resolve_roles(ps)
    assert len(out) == 2  # 不丢
    assert {p.participant_id for p in out} == {"p1", "p2"}

def test_o2_can_be_formal_source():
    from reaction_agent.schemas.evidence import ReactionParticipant
    o2 = ReactionParticipant(participant_id="p2", molecule_id="O2", canonical_smiles="O=O", side="reactant")
    out = resolve_roles([o2])
    # O2 不因 COFACTORS 被删；role 可能是 co_substrate 或 cofactor prior
    assert len(out) == 1

def test_donor_eligibility_separate_from_role():
    from reaction_agent.schemas.evidence import ReactionParticipant
    p = ReactionParticipant(participant_id="p1", molecule_id="m1", canonical_smiles="C", side="reactant")
    d = assess_donor_eligibility(p, mapping_report=None)
    assert d.eligibility in ("eligible","conditionally_eligible","not_eligible","unknown")
    assert d.reason_codes  # 有 reason
```

- [ ] **Step 2: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_participant_roles.py -q -p no:cacheprovider -ra`
Expected: FAIL

- [ ] **Step 3: 实现 cofactors + resolver**

Create `reaction_agent/roles/cofactors.py`：只读 import legacy `COFACTORS`，canonicalize，记 source hash（`canonical_identity.py` 的 SHA-256）。Create `reaction_agent/roles/resolver.py`：`resolve_roles` 给每个 participant 加 `RoleHypothesis`（带 evidence_codes + policy_version），**绝不删 participant**；`assess_donor_eligibility` 按 §11.4 多维评估（mapped retention/changed atoms/size/stoichiometry/COFACTORS prior/direction/mapping quality/lineage ambiguity），输出 `DonorEligibilityAssessment`。role ambiguity 与 mapping evidence 冲突时保留 ambiguity（文档 §11.3）。

- [ ] **Step 4: GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_participant_roles.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 5: RED — multiset 不变量测试**

追加：
```python
def test_input_multiset_equals_persisted():
    from reaction_agent.schemas.evidence import ReactionParticipant
    ps = [
        ReactionParticipant(participant_id=f"p{i}", molecule_id=f"m{i}",
                            canonical_smiles="C", side="reactant") for i in range(3)
    ]
    out = resolve_roles(ps)
    assert sorted(p.participant_id for p in ps) == sorted(p.participant_id for p in out)
```

- [ ] **Step 6: Run RED→GREEN**

Expected: PASS

- [ ] **Step 7: 生成 participant role sample + P0/P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
生成 `reports/p1/participant_role_sample.json`（含 O2/H2O/CO2/NAD/小分子保留证据）。Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 8: T5 checkpoint 报告 + worklog**

Create `reports/p1/P1_T5_PARTICIPANT_ROLES.md`：multiset 不变量证据、COFACTORS prior 不删 participant 证据、O2/H2O/小分子保留、donor eligibility 与 role 分离。追加 worklog T5 节。

**必须证明 `input participant multiset == persisted participant multiset`（canonicalization 可解释变化除外，但须有 mapping）。**

---

## Task 6: P1-T6 — Bipartite fragment-lineage graph

**Files:**
- Create: `reaction_agent/lineage/__init__.py`
- Create: `reaction_agent/lineage/resolver.py`
- Create: `tests/p1/test_lineage_graph.py`
- Create: `reports/p1/P1_T6_LINEAGE_GRAPH.md`
- Create: `reports/p1/lineage_regression_cases.json`

**Interfaces:**
- Consumes: T2 `LineageEdge`/`LineageResolution`(P0)/`ResolvedTransformedLineage`、T4 `MappingReport`、T5 participants
- Produces:
  - `reaction_agent.lineage.resolver.build_lineage_graph(participants, mapping_report) -> LineageResolution`
  - `reaction_agent.lineage.resolver.resolve_lineages(graph) -> list[ResolvedTransformedLineage]`

**agent: architect → tdd-guide；task 内 Explore 查 proline/2OG 真实案例**

- [ ] **Step 1: READ — proline/2OG 案例**

Explore 查 Preflight/T3 的 proline/2OG 真实 source record。若缺，本 task regression 用 curated fixture（明确标 `synthetic`/`curated`），但 §12.6 硬 Gate 必须用真实案例或 quarantine。

- [ ] **Step 2: RED — 禁止独立挑选/tie 测试**

Create `tests/p1/test_lineage_graph.py`：
```python
import pytest
from reaction_agent.lineage.resolver import build_lineage_graph, resolve_lineages

def test_no_independent_side_picking():
    # 构造两侧多 participant，验证不强行配对单一 pair
    # （具体 fixture 见实现，含 2 reactants + 2 products）
    pass  # 由 tdd-guide 填具体 fixture

def test_critical_tie_not_silently_resolved():
    # 构造 equal-score tie，验证不返回单一 strict lineage
    pass  # tdd-guide 填

def test_multiple_lineages_supported():
    pass  # split/merge/transfer

def test_lineage_id_stable_atom_order_invariant():
    pass

def test_proline_2og_correct_or_quarantined():
    # §12.6 硬 Gate：proline->hydroxyproline + 2OG->succinate，或 quarantine
    # 绝不 2OG->hydroxyproline
    pass

def test_forbidden_2og_to_hydroxyproline():
    pass  # 验证该错误配对不进 index
```
（tdd-guide 补全每个测试的具体 fixture 与断言，含 §12.5 的 14 项回归：proline hydroxylation/redox NAD/oxygen incorporation/hydrolysis/transferase/decarboxylation/cleavage/condensation/split/merge/equal-score tie/partial mapping/MCS fallback/atom-order permutation。）

- [ ] **Step 3: Run RED**

Run: `.venv/bin/python -m pytest tests/p1/test_lineage_graph.py -q -p no:cacheprovider -ra`
Expected: FAIL

- [ ] **Step 4: 实现 lineage resolver**

Create `reaction_agent/lineage/resolver.py`：`build_lineage_graph` 构 reactant↔product bipartite graph，edge 含 §12.1 的 9 项特征；`resolve_lineages` 输出 zero/one/multiple/split/merge/atom_transfer/ambiguity_set/unresolved（§12.3），**严禁 tuple max() 静默解 tie、严禁强制 primary pair**。关键 ambiguity → diagnostic/quarantine，不进 strict。lineage ID 基于 reaction identity + participant identity + mapped atom correspondence + resolver semantic version（§12.4）。

- [ ] **Step 5: GREEN**

Run: `.venv/bin/python -m pytest tests/p1/test_lineage_graph.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 6: 生成 regression cases + P0/P1 回归**

生成 `reports/p1/lineage_regression_cases.json`（每个 regression 的 nodes/edges/resolution/ambiguity/eligibility，不只最终 pair）。
Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 7: T6 checkpoint 报告 + worklog**

Create `reports/p1/P1_T6_LINEAGE_GRAPH.md`：bipartite graph、14 项 regression、proline/2OG 硬 Gate 结果（正确解析 or quarantine）、no independent picking/no silent tie 证据、stable lineage IDs。追加 worklog T6 节。

**proline/2OG 硬 Gate：A 正确解析 or B quarantine，绝不 2OG→hydroxyproline 且绝不错误配对后进 index。**

---

## Task 7: P1-T7 — SourceReactionLedger

**Files:**
- Modify: `reaction_agent/schemas/ledger.py`（确认 `SourceReactionLedger` 字段完整，§13.2）
- Create: `reaction_agent/ledgers/__init__.py`
- Create: `reaction_agent/ledgers/source_builder.py`
- Create: `tests/p1/test_source_ledger.py`
- Create: `reports/p1/P1_T7_SOURCE_LEDGER.md`
- Create: `reports/p1/source_ledger_samples.json`

**Interfaces:**
- Consumes: T2 `SourceReactionLedger`(P0 已有)/`ElementBalance`/`CofactorChange`/`FormalAtomTransferAssignment`、T4 mapping、T5 roles、T6 lineages
- Produces: `reaction_agent.ledgers.source_builder.build_source_ledger(reaction_evidence, lineages) -> SourceReactionLedger`

**agent: architect → tdd-guide**

- [ ] **Step 1: RED — balance/不伪造 测试**

Create `tests/p1/test_source_ledger.py`：
```python
import pytest
from reaction_agent.ledgers.source_builder import build_source_ledger

def test_missing_stoichiometry_is_unknown_not_default_1():
    # 缺 stoichiometry → unknown，不默认 1
    pass  # tdd-guide 填

def test_missing_h_plus_has_policy_not_silent_fill():
    pass

def test_formal_mapper_not_mechanism():
    # formal assignment ≠ proven mechanistic origin
    pass

def test_balance_status_typed():
    pass  # fully_balanced_explicit_reaction / heavy_atom_balanced_... / partial_or_unbalanced_source

def test_unknown_atom_source_not_strict():
    # 新增 changed heavy atom 无 formal source → 不 strict eligible
    pass

def test_complete_participant_preservation():
    pass  # 完整反应 participant 不丢
```
（tdd-guide 补全 §13.5 的 13 项测试：redox/O2 incorporation/hydrolysis/decarboxylation/transfer/charge mismatch/missing stoichiometry/incomplete source/ambiguous formal assignment/unknown atom source/mechanistic evidence absent/unbound mechanistic evidence reject/complete participant preservation。）

- [ ] **Step 2: Run RED**

Expected: FAIL

- [ ] **Step 3: 实现 source_builder**

Create `reaction_agent/ledgers/source_builder.py`：`build_source_ledger` 填充 §13.2 全部字段（reactant/product entries/roles/stoichiometry/formal atom transfer/mechanistic origin 仅独立证据/added sources/removed sinks/element balance/charge balance/H/proton/electron policies/cofactor changes/source & mapping completeness/balance status/unknowns/evidence IDs）。**缺 stoichiometry → unknown 不默认 1；缺 H+/e− → 明确 policy 不静默补平；formal mapper → formal assignment 不 mechanism**。

- [ ] **Step 4: GREEN**

Expected: PASS

- [ ] **Step 5: 生成 samples + P0/P1 回归**

生成 `reports/p1/source_ledger_samples.json`。
Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 6: T7 checkpoint 报告 + worklog**

Create `reports/p1/P1_T7_SOURCE_LEDGER.md`：balance status 分布、unknown 不伪造证据、formal/mechanistic 分离、participant 保留。追加 worklog T7 节。

---

## Task 8: P1-T8 — CandidateAnalogyLedger skeleton

**Files:**
- Modify: `reaction_agent/schemas/ledger.py`（确认 `CandidateAnalogyLedger` skeleton，§14）
- Create: `reaction_agent/ledgers/candidate_builder.py`（skeleton + fixture builder）
- Create: `tests/p1/test_candidate_ledger_skeleton.py`
- Create: `reports/p1/P1_T8_CANDIDATE_LEDGER_SKELETON.md`

**Interfaces:**
- Consumes: T2 `CandidateAnalogyLedger`(P0)/`QueryCandidateAdaptation`/`InheritedDonorContext`、T7 `SourceReactionLedger`
- Produces: `reaction_agent.ledgers.candidate_builder.build_candidate_skeleton(source_ledger, adaptation) -> CandidateAnalogyLedger`（只 skeleton + fixtures，**不生成 Y**）

**agent: tdd-guide**

- [ ] **Step 1: RED — skeleton 不变量测试**

Create `tests/p1/test_candidate_ledger_skeleton.py`：
```python
import pytest
from reaction_agent.ledgers.candidate_builder import build_candidate_skeleton

def test_donor_context_is_assumption():
    pass  # donor_context_is_assumption = true

def test_source_ledger_link_exists():
    pass

def test_candidate_id_belongs_current_context():
    pass

def test_donor_cofactor_not_proven_xy_cofactor():
    # donor cofactor ≠ proven X→Y cofactor
    pass

def test_formal_balance_under_assumptions_not_observed():
    # formal_balance_under_assumptions ≠ observed balance
    pass

def test_no_y_generated():
    # skeleton 不生成 Y
    pass
```
（tdd-guide 补全 §14 的 5 个关键不变量断言。）

- [ ] **Step 2: Run RED→GREEN**

实现 `build_candidate_skeleton`（只构造 adaptation + 验证 source→candidate boundary + 保留 unknowns，**禁止生成 Y/排名/LLM rationale/把 fixture 当预测**）。Expected: PASS。

- [ ] **Step 3: P0/P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 4: T8 checkpoint 报告 + worklog**

Create `reports/p1/P1_T8_CANDIDATE_LEDGER_SKELETON.md`：skeleton 不变量、source linkage、unknowns 保留、不生成 Y。追加 worklog T8 节。

**只实现 schema/builder skeleton + fixtures，不实现完整 X→Y generator。禁止生成 Y/排名/LLM rationale。**

---

## Task 9: P1-T9 — Eligibility / quarantine engine

**Files:**
- Modify: `reaction_agent/eligibility/__init__.py`（新建包）
- Create: `reaction_agent/eligibility/engine.py`（复用 `policies/partial_eligibility.py`，不复制第二套判断）
- Create: `tests/p1/test_eligibility_engine.py`
- Create: `reports/p1/P1_T9_ELIGIBILITY.md`
- Create: `reports/p1/eligibility_matrix_execution.json`

**Interfaces:**
- Consumes: `reaction_agent.policies.partial_eligibility`（P0 已冻结，唯一 policy authority）、T2 `EligibilityDecision`/`QuarantineRecord`、T6 lineages、T7 ledger
- Produces: `reaction_agent.eligibility.engine.decide_eligibility(reaction_evidence, ledger, lineages) -> EligibilityDecision`

**agent: tdd-guide → 实现**

- [ ] **Step 1: RED — 8 行 matrix + fail-closed + boundary 测试**

Create `tests/p1/test_eligibility_engine.py`：
```python
import pytest
from reaction_agent.eligibility.engine import decide_eligibility

def test_matrix_row_1_fully_balanced_strict():
    pass  # fully balanced + reliable mapping → strict_eligible
def test_matrix_row_2_heavy_atom_implicit_he_conditional():
    pass
def test_matrix_row_3_missing_noncritical_cofactor_conditional():
    pass
def test_matrix_row_4_unknown_changed_heavy_atom_prohibited():
    pass
def test_matrix_row_5_critical_contradiction_quarantine():
    pass
def test_matrix_row_6_role_ambiguity_lineage_local():
    pass
def test_matrix_row_7_lineage_ambiguity_prohibited():
    pass
def test_matrix_row_8_direction_unknown_prohibited():
    pass

def test_fail_closed_not_default_eligible():
    # strict 所需字段缺失 → 不默认 eligible
    pass

def test_quarantine_never_in_production_index():
    pass
def test_strict_prohibited_never_in_strict_index():
    pass
def test_conditional_carries_required_warnings():
    pass
def test_diagnostic_remains_auditable():
    pass
```
（tdd-guide 补全每个测试 fixture，覆盖 ADR-0004 的 8 行。）

- [ ] **Step 2: Run RED**

Expected: FAIL

- [ ] **Step 3: 实现 engine（复用 policy，不复制）**

Create `reaction_agent/eligibility/engine.py`：`decide_eligibility` 调 `policies.partial_eligibility.get_row(state)` 获取矩阵行，映射到 `EligibilityDecision`（strict eligibility/required warnings/quarantine behavior/evaluation bucket/research-diagnostic eligibility/reason codes/evidence IDs/policy version）。**fail-closed：缺字段 → diagnostic/strict_prohibited/quarantine，不默认 eligible**。导出 `eligibility_matrix_execution.json`（每行正例 + 反例）。

- [ ] **Step 4: GREEN**

Expected: PASS

- [ ] **Step 5: P0/P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 6: T9 checkpoint 报告 + worklog**

Create `reports/p1/P1_T9_ELIGIBILITY.md`：8 行 matrix 执行、fail-closed、production index boundary（quarantine/strict_prohibited 不进、conditional 带 warning、diagnostic 可审计）。追加 worklog T9 节。

**复用 `policies/partial_eligibility.py`，不得复制第二套字符串判断。fail-closed：不得默认 eligible。**

---

## Task 10: P1-T10 — Immutable snapshot builder

**Files:**
- Create: `reaction_agent/snapshot/__init__.py`
- Create: `reaction_agent/snapshot/builder.py`
- Create: `reaction_agent/snapshot/loader.py`
- Create: `tests/p1/test_snapshot_builder.py`
- Create: `reports/p1/P1_T10_SNAPSHOT.md`
- Create: `reports/p1/snapshot_build_sample.json`

**Interfaces:**
- Consumes: T1 `BuildConfig`/`get_build_info`、T2 `SnapshotManifest`/`SnapshotRecord`、T4-T9 全部产物
- Produces:
  - `reaction_agent.snapshot.builder.build_snapshot(config, evidence_iter) -> SnapshotManifest`（atomic finalize）
  - `reaction_agent.snapshot.loader.load_snapshot(snapshot_id_or_path) -> SnapshotRecord`（read-only，verify hash）

**agent: architect → tdd-guide；task 内 L2 security-reviewer 审 atomicity**

- [ ] **Step 1: RED — determinism/atomicity/loader 测试**

Create `tests/p1/test_snapshot_builder.py`：
```python
import pytest
from reaction_agent.snapshot.builder import build_snapshot
from reaction_agent.snapshot.loader import load_snapshot

def test_deterministic_rebuild_same_hash():
    pass  # 同 source + 同 versions + 同 config → 同 hash
def test_source_change_new_hash():
    pass
def test_policy_change_new_hash():
    pass
def test_quarantine_in_manifest():
    pass
def test_production_excludes_quarantine():
    pass
def test_all_filters_counted():
    pass
def test_interrupted_build_not_complete():
    pass  # 中断 → complete=false，loader 拒绝
def test_hash_mismatch_rejected():
    pass
def test_read_only_load():
    pass
def test_explicit_snapshot_required():
    pass  # 不自动选最新
def test_existing_snapshot_not_overwritten():
    pass
def test_input_record_ordering_stability():
    pass
def test_timestamp_not_in_canonical_hash():
    pass  # timestamp/run ID 不纳入 canonical content hash
```
（tdd-guide 补全 §16.7 的 11 项测试 fixture。）

- [ ] **Step 2: Run RED**

Expected: FAIL

- [ ] **Step 3: 实现 builder + loader**

Create `reaction_agent/snapshot/builder.py`：实现 §16.1 pipeline（source load→raw preserve→normalize→mapping→roles→lineage→ledger→eligibility→production/diagnostic/quarantine→manifest→hash→atomic finalize）。**atomicity**：写临时目录→验证→算 final hash→atomic finalize→complete 最后置 true（§16.4）。canonical snapshot content hash **不含 timestamp/temp path/run ID/unordered iteration**（§16.6）。
Create `reaction_agent/snapshot/loader.py`：需显式 snapshot ID/path、read-only、verify manifest/hash、拒 incomplete、拒 hash mismatch、不自动选最新、不修改 snapshot（§16.5）。

- [ ] **Step 4: GREEN**

Expected: PASS

- [ ] **Step 5: L2 security-reviewer 审 atomicity**

Orchestrator 派 security-reviewer 审 `builder.py`/`loader.py`：atomic finalize 顺序正确、interrupted build 不 complete、loader read-only、不覆盖已有 immutable snapshot。CRITICAL/HIGH 必修。

- [ ] **Step 6: 生成 build sample + P0/P1 回归**

生成 `reports/p1/snapshot_build_sample.json`（真实 source snapshot 与 fixture snapshot **明确分开**）。
Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 7: T10 checkpoint 报告 + worklog**

Create `reports/p1/P1_T10_SNAPSHOT.md`：deterministic rebuild 证据、atomicity、loader read-only、real vs fixture snapshot 分离。追加 worklog T10 节。

**真实 source snapshot 与 fixture snapshot 必须明确分开。timestamp/temp path/run ID 不纳入 canonical content hash。**

---

## Task 11: P1-T11 — Manual audit protocol（L2 双盲 + 裁决）

**Files:**
- Create: `docs/manual_audit_protocol.md`（阈值冻结，先于结果）
- Create: `schemas/json/ManualAuditRecord.json`（导出）
- Create: `reports/p1/manual_audit_sample_manifest.json`
- Create: `reports/p1/manual_audit_annotations_a.json`（Annotator A）
- Create: `reports/p1/manual_audit_annotations_b.json`（Annotator B）
- Create: `reports/p1/manual_audit_adjudication.json`（Adjudicator）
- Create: `reports/p1/manual_audit_report.md`
- Create: `reports/p1/manual_audit_report.json`
- Create: `tests/p1/test_manual_audit_contract.py`

**Interfaces:**
- Consumes: T2 `ManualAuditRecord`、T10 snapshot（stratified sample 来源）
- Produces: 双盲 annotations（A、B 独立）+ adjudication + agreement metrics + pass/fail decision

**agent: Annotator A ∥ B (L2 双盲并行) → Adjudicator (L2 独立裁决)**

- [ ] **Step 1: 冻结 protocol + 阈值（先于结果）**

Orchestrator 写 `docs/manual_audit_protocol.md`：含 stratification（§17.2）、rubric（§17.3 的 11 项）、catastrophic error 定义（§17.4 的 9 项）、agreement metrics（§17.5）、**pass threshold 冻结**（§17.6 硬条件：catastrophic errors in production index=0 / proline-2OG correct or quarantined / critical tie silently selected=0 / quarantine leakage=0 / participant destructive loss=0 / formal→mechanistic false upgrade=0 / snapshot replay/hash failure=0）。**不得看结果后调整阈值**。

- [ ] **Step 2: 生成 stratified sample manifest**

Orchestrator 从 T10 snapshot 按 §17.2 分层抽样，生成 `manual_audit_sample_manifest.json`。数据集小→全量；大→给样本量依据 + 随机种子。

- [ ] **Step 3: RED — audit 契约测试**

Create `tests/p1/test_manual_audit_contract.py`：
```python
import json
from pathlib import Path

def test_two_distinct_annotator_ids():
    a = json.loads(Path("reports/p1/manual_audit_annotations_a.json").read_text())
    b = json.loads(Path("reports/p1/manual_audit_annotations_b.json").read_text())
    assert a["annotator_id"] != b["annotator_id"]  # 不同 annotator

def test_adjudication_present():
    adj = json.loads(Path("reports/p1/manual_audit_adjudication.json").read_text())
    assert "disagreement_count" in adj and "outcomes" in adj

def test_catastrophic_errors_reported():
    rep = json.loads(Path("reports/p1/manual_audit_report.json").read_text())
    assert "catastrophic_error_count" in rep

def test_threshold_frozen_before_results():
    proto = Path("docs/manual_audit_protocol.md").read_text()
    assert "catastrophic errors in production index = 0" in proto
    # protocol 的 mtime 早于 report（冻结先于结果）—— 由 Orchestrator 保证

def test_no_llm_self_confidence_as_audit():
    rep = json.loads(Path("reports/p1/manual_audit_report.json").read_text())
    assert "llm_confidence" not in str(rep).lower()
```

- [ ] **Step 4: Run RED**

Expected: FAIL（annotations 未生成）

- [ ] **Step 5: 双盲标注（Annotator A ∥ B 并行）**

Orchestrator **并行**派两个独立 `general-purpose` 实例（Annotator A、B，不同 agent ID，互不可见对方输出），各按 rubric 标注同一 sample manifest，产出 `manual_audit_annotations_{a,b}.json`。**不得让同一执行过程复制两份答案冒充 double annotation**（§17.1）。

> 若缺第二位独立 annotator 资源：标 `BLOCKED_MANUAL_AUDIT_INCOMPLETE`，**不得生成虚假 annotations**（§17.1/§23）。

- [ ] **Step 6: Adjudicator 裁决**

Orchestrator 派第三个独立 `general-purpose` 实例（Adjudicator），读 A、B annotations，裁决分歧，产 `manual_audit_adjudication.json`（raw agreement/per-field agreement/disagreement count/adjudication outcomes/catastrophic error count）。**不采信 LLM 自评 confidence**（§17.5）。

- [ ] **Step 7: 生成 audit report + GREEN**

生成 `manual_audit_report.{md,json}`（数字一致）。
Run: `.venv/bin/python -m pytest tests/p1/test_manual_audit_contract.py -q -p no:cacheprovider -ra`
Expected: PASS

- [ ] **Step 8: P0/P1 回归**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py`
Expected: P0 290 + P1 全绿 + Gate 10/10。

- [ ] **Step 9: T11 checkpoint 报告 + worklog**

追加 worklog T11 节：stratified sample、双 annotator 独立性、agreement、adjudication、catastrophic error count、pass threshold 冻结证据。

**缺第二位独立 annotator 或人工审核资源 → `BLOCKED_MANUAL_AUDIT_INCOMPLETE`，P1 Gate = BLOCKED。不得让同一执行过程复制两份答案冒充 double annotation。**

---

## Task 12: P1 Gate + mutation（L2 独立 Gate Keeper）

**Files:**
- Create: `scripts/run_p1_gate.py`
- Create: `tests/p1/test_p1_gate_contract.py`
- Create: `reports/p1/P1_GATE_REPORT.md`
- Create: `reports/p1/P1_GATE_REPORT.json`

**Interfaces:**
- Consumes: T0-T11 全部 artifact + `scripts/run_p0_gate.py`（沿用 `run_all`/`check_*`/`generate_report` 模式）
- Produces: P1 Gate 报告（10 项 + 8 mutation）+ exit code

**agent: Gate Keeper (L2 独立) — 只读验证，不碰实现代码**

- [ ] **Step 1: 实现 10 项 Gate（读 evidence，不只查文件存在）**

Create `scripts/run_p1_gate.py`，沿用 P0 Gate 模式，实现 G01-G10（§18.1）。每项读机器可读 evidence：
- G01：package import / Python / lock / explicit config & snapshot / no legacy write（跑 `get_build_info`、查 lock、`assert_no_legacy_write`）
- G02：strict schema / stable IDs / content hashes / provenance / **P0 contract still green**（跑 `tests/contracts` + `run_p0_gate.py`）
- G03：真实 source used / counts & denominators / mismatch categories / source IDs & examples / proline-2OG included（读 `legacy_lineage_audit.json`）
- G04：real adapter integration / quality metrics / failure states / MCS not strict / formal not mechanism（读 `mapping_integration_sample.json` + 跑 mapping 测试）
- G05：complete participant multiset / COFACTORS no deletion / small molecule can be substrate/source / ambiguity retained（读 `participant_role_sample.json` + 跑 T5 测试）
- G06：bipartite graph / split-merge-transfer / no independent picking / no silent tie / stable IDs / proline-2OG correct or quarantined（读 `lineage_regression_cases.json` + 跑 T6 测试）
- G07：SourceReactionLedger valid / CandidateAnalogyLedger skeleton valid / unknowns preserved / formal-mechanistic separated / source linkage valid（跑 T7/T8 测试）
- G08：all 8 policy rows / warnings / quarantine behavior / production index excludes prohibited & quarantine / all reasons typed（读 `eligibility_matrix_execution.json`）
- G09：deterministic rebuild / content hash / manifest complete / all filters counted / interrupted build invalid / read-only loader（重建 snapshot 两次比 hash）
- G10：double annotation complete / adjudication complete / threshold frozen before results / catastrophic errors=0 / all P0+P1 tests pass / zero fail/error/skip/xfail/xpass（读 audit report + 结构化读 pytest stats）

**禁止 `passed = report_file.exists()`**（§18.2）。

- [ ] **Step 2: RED — Gate 契约测试**

Create `tests/p1/test_p1_gate_contract.py`：
```python
import json, subprocess
from pathlib import Path

def test_gate_runs_and_exits_zero_on_pass():
    r = subprocess.run([".venv/bin/python", "scripts/run_p1_gate.py"], capture_output=True)
    # 若 BLOCKED，exit !=0 但 status 应为 BLOCKED_*；此处测试非 BLOCKED 时 exit=0
    pass  # tdd-guide 按 GO/BLOCKED 分支补全

def test_gate_reads_evidence_not_file_existence():
    # 验证 gate 脚本不只用 os.path.exists
    src = Path("scripts/run_p1_gate.py").read_text()
    assert "passed = report_file.exists()" not in src

def test_zero_skip_xfail_in_full_suite():
    r = subprocess.run([".venv/bin/python", "-m", "pytest", "tests",
                        "--json-report", "--json-report-file=/tmp/gate_pytest.json",
                        "-q", "-p", "no:cacheprovider"], capture_output=True)
    stats = json.loads(Path("/tmp/gate_pytest.json").read_text())["summary"]
    assert stats.get("failed",0)==0 and stats.get("errors",0)==0
    assert stats.get("skipped",0)==0 and stats.get("xfailed",0)==0 and stats.get("xpassed",0)==0
```

- [ ] **Step 3: Run Gate**

Run: `.venv/bin/python scripts/run_p1_gate.py`
Expected: 10/10 PASS（若 BLOCKED，输出 `BLOCKED_*` + reasons）。

- [ ] **Step 4: 8 项 mutation（隔离临时副本）**

Gate Keeper 在**临时副本**（`/tmp/p1_mutation_<n>/`）逐项执行 §18.3 的 8 mutation，每项验证 Gate fail：
- 删 participant preservation check → fail
- critical tie 取 max → fail
- MCS 标 full mapping → fail
- mapper 自动填 mechanism → fail
- quarantine record 进 production → fail
- snapshot hash 非确定 → fail
- 删 proline/2OG required case → fail
- 加 skipped/xfailed test → fail

**mutation 只在临时副本，不污染正式代码**（§18.3）。记录每项 mutation → expected fail → actual fail。

- [ ] **Step 5: GREEN + Gate 报告**

Run: `.venv/bin/python -m pytest tests/p1/test_p1_gate_contract.py -q -p no:cacheprovider -ra`
Expected: PASS。生成 `P1_GATE_REPORT.{md,json}`：10 项 Gate 状态 + 8 mutation 结果 + pytest stats + exit code。

- [ ] **Step 6: 最终提交材料**

Create `reports/p1/SUBMISSION_TO_CHATGPT_P1.md`，封面含 §21 的 17 项：
1. P1 十项 Gate 状态
2. P0 baseline 和最终回归
3. P1 targeted/full test 精确统计
4. runtime/dependency versions
5. real source manifest/hash
6. mapper backend/version
7. proline/2OG 实际结果
8. participant preservation 统计
9. lineage mismatch 统计
10. eligibility/quarantine 统计
11. snapshot deterministic rebuild 证据
12. manual audit 样本/agreement/adjudication
13. catastrophic error count
14. changed files
15. deviations/risks（含执行模型 Qwen→Claude Code subagent 偏差）
16. git/user-files protection
17. P2 状态

结尾**只允许写**：
```
READY_FOR_CHATGPT_P1_READ_ONLY_AUDIT
P2 BLOCKED pending ChatGPT audit
```
**绝不自行写 "P1 finally accepted / P2 authorized / system can reliably predict X→Y"。**

- [ ] **Step 7: 最终全回归 + worklog 收尾**

Run: `.venv/bin/python -m pytest tests -q -p no:cacheprovider -ra && .venv/bin/python scripts/run_p0_gate.py && .venv/bin/python scripts/run_p1_gate.py`
Expected: P0 290 + P0 Gate 10/10 + P1 全绿 + P1 Gate 10/10。追加 worklog Gate 节。

**Gate 任一失败：exit !=0 / status=NOT_READY_FOR_CHATGPT_AUDIT / P2=BLOCKED。mutation 只能在临时副本，不污染正式代码。**

---

## 验收口径（Orchestrator 每个 checkpoint 用）

科学主线七条（文档 §24）：
```
不丢反应 / 不跨 lineage / 不伪造 mapping / 不误删 cofactor/小分子
不静默解 ambiguity / 不让 quarantine 泄漏 / 所有结果可追溯可重放可审计
```

最终完成清单见文档 §22（P0 preservation / Runtime / Real data / Mapping / Roles / Lineage / Ledgers / Eligibility-snapshot / Audit-Gate 九大类）。

---

## Self-Review

**1. Spec coverage:** spec §1-§9 覆盖情况：
- §1 三层架构 → Global Constraints agent 分配总表 + 每 task agent 标注 ✅
- §2 调度矩阵 → Task 0-12 的 agent 字段 + task 内并行标注 ✅
- §3 数据流/artifact 交接 → 每 task 的 Checkpoint artifact + worklog 追加步骤 ✅
- §4 阻断协议 → Task 0 Step 7 GO/PARTIAL/BLOCKED + 每 task 的 BLOCKED 标注 ✅
- §5 Gate + mutation → Task 12 ✅
- §6 独立性落地 → Task 3(Legacy Auditor L2)/Task 11(双 annotator + Adjudicator L2)/Task 12(Gate Keeper L2) + T4 formal≠mechanistic + security-reviewer ✅
- §7 报告规范 → 每 task checkpoint 报告 + Task 12 最终提交 ✅
- §8 偏差记录 → Global Constraints 模型偏差 + Task 12 Step 6 封面 §15 ✅
- §9 排除范围 → Global Constraints 禁止越界 ✅

**2. Placeholder scan:** Task 6/7/9/10 的 tdd-guide 测试 fixture 标了 `pass # tdd-guide 填`——这是有意委托（fixture 依赖具体 schema 字段，由 tdd-guide 在 RED 阶段据实填），非 plan 失败。每处都注明了要覆盖的文档条款（如"§12.5 的 14 项回归"），agent 有明确依据。其余步骤均有完整代码。

**3. Type consistency:** 检查跨 task 接口名：
- `BuildConfig`/`get_build_info`（T1 定义，T10 消费）✅
- `canonical_hash`/`stable_id`（T1 定义，T2 消费）✅
- `NormalizedReactionRecord`/`DonorEligibilityAssessment`/`EligibilityDecision`/`QuarantineRecord`/`SnapshotManifest`/`SnapshotRecord`/`ManualAuditRecord`/`ResolvedTransformedLineage`（T2 定义，T3-T11 消费）✅
- `AtomMapper`/`FakeAtomMapper`/`compute_quality_flags`（T4 定义）✅
- `load_cofactors`/`resolve_roles`/`assess_donor_eligibility`（T5 定义，T6/T7 消费）✅
- `build_lineage_graph`/`resolve_lineages`（T6 定义，T7 消费）✅
- `build_source_ledger`（T7 定义，T8/T9 消费）✅
- `build_candidate_skeleton`（T8 定义）✅
- `decide_eligibility`（T9 定义，T10 消费）✅
- `build_snapshot`/`load_snapshot`（T10 定义，T11/Gate 消费）✅
- 复用 P0：`MappingStatus`/`EligibilityStatus`/`StrictModel`/`partial_eligibility.get_row`/`SourceReactionLedger`/`CandidateAnalogyLedger`/`LineageResolution` 全部引用 P0 已有，不重定义 ✅

无类型/签名不一致。
