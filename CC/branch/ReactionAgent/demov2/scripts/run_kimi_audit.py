#!/usr/bin/env python3
"""Kimi 审核流水线 v2 — 完整材料落 md + 3-4 行短提示词（用户协作风格）。

用法:
  python3 scripts/run_kimi_audit.py --stage p4 --round 4 \
      --worktree /path/to/worktree \
      --submission reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_4.md \
      --prior-audit /abs/path/CHATGPT_P4_ROUND_3_READ_ONLY_AUDIT_AND_REMEDIATION.md \
      --output reports/p4/HERMES_P4_ROUND_4_READ_ONLY_AUDIT_AND_REMEDIATION.md

风格（两层式）:
  Layer 1: 完整审核任务书 → 详细 Md（证据、任务书、约束、交付物格式）
  Layer 2: 提交给 kimi 的只有 3-4 行短提示词（读 md + 目标 + 约束 + 交付物）
  kimi 通过 Hermes（工具已可用）读 md 后自主执行审核。

流程:
  1. 独立重放验证矩阵（可 --skip-verify）
  2. 生成自包含审核任务书 md（audit_packet/HANDOFF_<stage>_R<round>.md）
  3. 生成 3-4 行短提示词，调 hermes -z（kimi 读 md 执行审核）
  4. 检查报告落盘
"""
from __future__ import annotations

import argparse
import functools
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

# 所有 print 实时 flush：配合 Monitor tail -f 实现流水线实时进度透出
print = functools.partial(print, flush=True)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

HERMES = "hermes"
HERMES_ARGS = ["--cli", "--no-restore-cwd", "--yolo"]
HERMES_TIMEOUT = 900          # 审核任务长，给足时间

STAGE_VERIFY_CMDS = {
    "p0": [("pytest tests/p0 -q -p no:cacheprovider", "p0 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts")],
    "p1": [("pytest tests/p1 -q -p no:cacheprovider", "p1 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts"),
           ("python3 -m scripts.run_p1_gate", "p1 gate"),
           ("python3 -m scripts.run_p1_mutations", "p1 mutations")],
    "p2": [("pytest tests/p2 -q -p no:cacheprovider", "p2 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts")],
    "p3": [("pytest tests/p3 -q -p no:cacheprovider", "p3 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts")],
    "p4": [("pytest tests/p4 -q -p no:cacheprovider", "p4 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts"),
           ("python3 -m scripts.run_p4_gate", "p4 gate"),
           ("python3 -m scripts.run_p4_mutations", "p4 mutations"),
           ("python3 -m scripts.run_p4_round4_probes", "p4 probes")],
    "p5": [("pytest tests/p5 -q -p no:cacheprovider", "p5 测试"),
           ("pytest tests/contracts -q -p no:cacheprovider", "contracts")],
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def resolve_path(p: str, wt: Path) -> Path:
    """绝对路径直接用；相对路径拼 worktree。"""
    path = Path(p)
    if path.is_absolute():
        return path
    return wt / p


def run_cmd(cmd: str, cwd: str, timeout: int = 300,
            ok_exit_codes: tuple = (0,), full_output: bool = False) -> dict:
    """运行命令。gate 类命令 exit 2(BLOCKED) 视为预期。

    ``full_output=True``（gate 类）保留完整 stdout，避免审核重放证据被截断
    （R7-02：kimi 要求 G12-G14 的完整 reason 可复核）。

    用 shell ``cd`` 而非 subprocess ``cwd=`` 参数：外置卷（/Volumes）在后台
    任务里 ``cwd=`` 可能不稳定（FileNotFoundError），shell 内建 cd 更可靠。
    """
    try:
        cmd = f"cd {shlex.quote(cwd)} && {cmd}"
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout)
        if full_output:
            out = (r.stdout or "") + (r.stderr or "")
        else:
            out = (r.stdout or "")[-600:] + (r.stderr or "")[-200:]
        return {"ok": r.returncode in ok_exit_codes,
                "exit": r.returncode,
                "output": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit": -1, "output": f"[超时 {timeout}s]"}


def extract_submission_matrix(submission: Path) -> str:
    if not submission.exists():
        return "(submission 不存在)"
    text = submission.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and ("passed" in s or "PASS" in s or
                                  "CAUGHT" in s or "rejected" in s or
                                  "BLOCKED" in s):
            lines.append(s)
    return "\n".join(lines[:12]) or "(未找到矩阵)"


def extract_prior_findings(prior: Path) -> str:
    if not prior.exists():
        return "(prior audit 不存在)"
    text = prior.read_text(encoding="utf-8")
    # 兼容两种格式：`### P4-R4-01 标题`（kimi 自动报告）和 `P4-R4-01  标题`（纯文本行）
    findings = re.findall(r"^#{0,3}\s*(P\d-R\d+-\w[^\n#|]*)", text,
                          re.MULTILINE)
    return "\n".join(findings[:10]) if findings else "(未找到 findings 标题)"


def extract_probes(packet: Path) -> str:
    """从独立验证包提取 Probe A/B 章节。"""
    if not packet.exists():
        return "(verification packet 不存在)"
    full = packet.read_text(encoding="utf-8")
    m = re.search(r"(#{2,3} Probe A[^\n]*\n(?:.*\n){0,14}?)(?=#{2,3} Probe B|## |\Z)",
                  full, re.DOTALL)
    m2 = re.search(r"(#{2,3} Probe B[^\n]*\n(?:.*\n){0,14}?)(?=#+ [A-Z]|\Z)",
                   full, re.DOTALL)
    return ((m.group(1) if m else "") + (m2.group(1) if m2 else ""))[:1500]


# ---------------------------------------------------------------------------
# Layer 1: 生成完整审核任务书 md
# ---------------------------------------------------------------------------


def build_handoff_md(args, claimed, prior_findings, probes, verified) -> str:
    stage = args.stage.upper()
    next_round = str(int(args.round) + 1)
    wt = args.worktree
    return f"""# {stage} Round {args.round} 独立只读审核任务书（kimi-k3）

> 你是独立只读审核者。按本任务书完成 {stage} Round {args.round} 的只读审核。
> 全部证据已在本文件内，无需访问外部资料。

## 一、任务目标

对 {stage} Round {args.round} 提交做严格、fail-closed 的独立只读审核，判定 PASS / FAIL / BLOCKED。
若 FAIL 则输出下一轮（Round {next_round}）remediation 要求。审核报告写到本任务书指定的路径。

## 二、被审对象与环境

- **项目根（worktree）**：`{wt}`
- **提交入口**：`{args.submission}`
- **上一轮 audit**：`{args.prior_audit}`
- **环境**：Python 3.11（anaconda3），pytest 9.1.1，pytest-json-report 1.5.0 已装
- **状态声明**：提交方声称 `{stage}_ROUND_{args.round}_IMPLEMENTATION_COMPLETE_..._READY_FOR_AUDIT`

## 三、提交声称的验证矩阵

{claimed}

## 四、独立重放结果（审计者已实测，无需你重跑）

{verified}

## 五、独立 probe 发现（审计者自写，关键证据）

{probes}

## 六、上一轮 mandatory findings（必须逐条核对关闭状态）

{prior_findings}

## 七、审核行为规范（硬性）

1. **Fail-closed**：任何绕过路径/概念缺陷 → FAIL。宁可错杀，不可放过。
2. **不信任自述**：以独立验证证据为准，提交方声称的 PASS 不作数。
3. **证据导向**：每个 finding 带 file:line 或可复现证据引用。
4. **逐项核对**：任务书 checklist 逐项判定 PASS/FAIL/BLOCKED。
5. **诚实**：无法验证 → BLOCKED，禁止编造 PASS。
6. **分级**：P0=科学/安全命门，P1=重要，P2=次要。

## 八、审核流程（必须完成）

1. 通读本任务书全部证据。
2. 逐条核对第三~六节的矩阵与 findings，判定各 finding 关闭状态（Closed/Partial/Open）。
3. 若发现证据矛盾或你认为需要额外验证的点，可用命令行工具验证（只读，不改源码）。
4. 输出最终审核报告。

## 九、交付物（审核报告）

写到：`{args.output}`（绝对路径）

格式（严格遵循）：
```markdown
# {stage} Round {args.round} Read-Only Audit and Round {next_round} Remediation

## 0. Verdict
一句话判定 + 状态码：
{stage}_ROUND_{args.round}_READ_ONLY_AUDIT_PASS   # 或 FAIL / BLOCKED
{stage}_ROUND_{next_round}_REMEDIATION_REQUIRED   # FAIL 时
P{int(args.stage[1]) + 1}_BLOCKED                 # 直到 PASS

## 1. Independent verification matrix
（提交声称 vs 独立重放，逐项）

## 2. Finding closure matrix
（上一轮 findings 关闭状态，逐条 Closed/Partial/Open + 依据）

## 3. Mandatory findings
### {stage}-R{args.round}-XX — 标题（等级）
#### 证据 / #### 影响 / #### 修复要求

## 4. Remediation requirements
（FAIL 时给下一轮最小整改清单，按优先级；每项附关闭条件与负向测试）
```

## 十、禁止事项

- 不得修改 repo 源码/测试/合同（只读审核）
- 不得 commit / push / merge
- 不得伪造 real / Gate PASS
- 完成审核报告后停止，不得做额外工作
"""


# ---------------------------------------------------------------------------
# Layer 2: 3-4 行短提示词（提交给 kimi）
# ---------------------------------------------------------------------------


def build_short_prompt(args, handoff_path: Path, section: str) -> str:
    """3-4 行短提示词：读任务书 md + 输出指定章节（分块，kimi 不做多轮工具）。"""
    stage = args.stage.upper()
    return (
        f"你是独立只读审核者。完整读取审核任务书：\n"
        f"{handoff_path}\n"
        f"基于任务书中的证据，输出第 {section} 部分（只输出该部分，不要执行其他工具/命令）。\n"
        f"fail-closed；不得编造证据。"
    )


# 审核输出章节（分块征询）
AUDIT_SECTIONS = [
    ("verdict", "0.Verdict（状态码 + 一句理由）"),
    ("closure", "2.Finding closure matrix（上一轮 findings 关闭状态表格）"),
    ("findings", "3.Mandatory findings（编号 + 等级 + 证据 + 影响 + 修复要求）"),
    ("remediation", "4.Remediation requirements（下一轮最小整改清单，按优先级）"),
]


# ---------------------------------------------------------------------------
# Layer 2b: 从审核报告生成修复提示词 md（Round N+1 Remediation Prompt）
# ---------------------------------------------------------------------------


_SECTION_HEADERS = (
    "Verdict|Finding closure matrix|Mandatory findings|Remediation requirements"
)


def _strip_section_title(text: str) -> str:
    """剥掉 kimi 输出自带的章节标题（如 `## 0. Verdict`），避免与报告模板标题重复。"""
    if not text or text == "(无)":
        return text
    return re.sub(rf"^#+\s*\d*\.?\s*({_SECTION_HEADERS})\s*\n+",
                  "", text, count=1, flags=re.MULTILINE | re.IGNORECASE).strip()


def call_kimi(prompt: str, retries: int = 4, base_delay: float = 30.0) -> str:
    """调 hermes 单次征询，429/超时自动退避重试；耗尽后抛 RuntimeError。"""
    cmd = [HERMES, "-z", prompt, *HERMES_ARGS]
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=HERMES_TIMEOUT)
            out = (r.stdout or "").strip()
            combined = out + "\n" + (r.stderr or "")
            if ("Throttling" in combined or "EngineOverloaded" in combined
                    or "429" in combined):
                last_err = " ".join(combined.split())[:200]
                if attempt < retries:
                    wait = base_delay * attempt
                    print(f"    ⚠️ 限流（第{attempt}次），{wait:.0f}s 后重试...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"429 限流重试 {retries} 次仍失败: {last_err}")
            return out or "(无输出)"
        except subprocess.TimeoutExpired:
            last_err = f"{HERMES_TIMEOUT}s 超时"
            if attempt < retries:
                wait = base_delay * attempt
                print(f"    ⚠️ 超时（第{attempt}次），{wait:.0f}s 后重试...")
                time.sleep(wait)
    raise RuntimeError(f"API call failed after {retries} retries: {last_err}")


def build_report_md(args, claimed, prior_findings, probes, verified,
                    results: dict, wt: Path) -> str:
    """把 4 块 kimi 输出组装成标准审核报告。"""
    stage = args.stage.upper()
    next_round = str(int(args.round) + 1)
    return f"""# {stage} Round {args.round} Read-Only Audit and Round {next_round} Remediation

**Audit date:** 2026-08-05
**Audited worktree:** `{wt}`
**Auditor:** kimi-k3（独立裁决，经 Hermes）+ 独立验证
**Submitted entry:** `{args.submission}`

---

## 0. Verdict

{_strip_section_title(results.get('verdict', '(无)'))}

---

## 1. Independent verification matrix

提交声称：

{claimed}

独立重放：

{verified}

## 2. Finding closure matrix

{_strip_section_title(results.get('closure', '(无)'))}

---

## 3. Mandatory findings

{_strip_section_title(results.get('findings', '(无)'))}

---

## 4. Remediation requirements

{_strip_section_title(results.get('remediation', '(无)'))}

---

*Generated by run_kimi_audit.py (kimi-k3 via Hermes).*
"""


def generate_remediation_prompt(stage: str, round_: str, next_round: str,
                                report_path: Path, wt: Path,
                                repo_root: Path | None = None) -> Path:
    """从审核报告提取 findings，生成下一轮修复任务书 md。

    报告章节约定：`## 3. Mandatory findings` 与 `## 4. Remediation requirements`。
    若报告内无该章节，则嵌入报告全文作为 findings 依据。
    """
    report = report_path.read_text(encoding="utf-8")
    m = re.search(r"## 3\. Mandatory findings(.*?)(?=\n## 4\.|## 0\.|\Z)",
                  report, re.DOTALL)
    findings = (m.group(1).strip() if m else
                report[:1500] + "\n...（未提取到 findings 章节，见审核报告全文）")
    vm = re.search(
        r"([A-Z0-9]+_ROUND_[0-9]+_READ_ONLY_AUDIT_(?:PASS|FAIL|BLOCKED))", report)
    verdict_code = vm.group(1) if vm else \
        f"{stage.upper()}_ROUND_{round_}_READ_ONLY_AUDIT_FAIL"

    # 落盘位置：主目录（与 ChatGPT remediation prompt 并列），否则 worktree
    if repo_root is not None:
        out_dir = Path(repo_root) / "reports" / stage
    else:
        out_dir = wt / "reports" / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"KIMI_{stage.upper()}_ROUND_{next_round}_REMEDIATION_PROMPT.md"

    content = f"""# Kimi {stage.upper()} Round {next_round} Remediation Instructions

## 1. 任务与正式审计状态

你正在修复 ReactionAgent 的 {stage.upper()}。kimi-k3 已完成 Round {round_} 只读审核（独立裁决）+ 独立验证。

正式状态为：

```text
{verdict_code}
{stage.upper()}_IMPLEMENTATION_COMPLETE = NOT_ACCEPTED
P5_INTEGRATION = BLOCKED
```

本轮是 **{stage.upper()} Round {next_round} 定向修复**。目标是建立真正的信任根与上游权威绑定，而不是继续给调用方自填字段增加更多自签名 hash。这不是架构重写，不是下一阶段开发，也不是修改冻结合同来适配代码。真实上游权威缺失可以继续诚实标记 `BLOCKED`，但任何 machinery / boundary 缺陷必须使审计状态为 `FAIL`，不能被 BLOCKED 掩盖。

## 2. 工作树、分支和环境

只在以下工作树中实施修复：

```text
{wt}
```

工作树分支：见 `git branch --show-current`。

Python / 测试环境（已就绪，勿重装）：

```text
/opt/anaconda3/bin/python3   (Python 3.11+, pytest 9.1.1+, pytest-json-report 1.5.0)
```

开始前必须运行并记录起始状态（写入 `reports/{stage}/{stage.upper()}_ROUND_{next_round}_STARTING_WORKTREE_STATE.md`）：

```bash
cd {wt}
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

## 3. Mandatory findings（必须全部修复）

{findings}

## 4. RED→GREEN 测试要求（强制）

1. **先写 RED tests**：为每个 finding 写负向测试（攻击场景），运行确认失败（RED）。
2. 再实施修复（GREEN）。
3. 全部验证命令必须实际运行并记录输出（见审核报告 §1 的验证命令）。

## 5. 复审准入条件（全部满足方可申请重测）

1. 每个 finding 的修复要求全部落实，负向测试覆盖对应攻击场景。
2. 负向测试 + 正向对照已提交且全绿；变异自检通过（抽查任一用例被注释后 pytest 必须红）。
3. 重跑独立 probe（若审核报告有）：伪造路径必须被拒绝。
4. 不得伪造 PASS；BLOCKED 项保持诚实 BLOCKED。

## 6. 禁止事项

- 不得修改上游合同 / frozen 文件 / P0 ADRs / final_design / final_plan
- 不得伪造 real / Gate PASS；machinery 缺陷不得被 BLOCKED 掩盖
- 不得 commit / push / merge / 安装依赖（环境已就绪）
- 不得修改其他阶段（P1/P2/P3）的冻结产物

## 7. 交付物（完成标准）

1. `reports/{stage}/{stage.upper()}_ROUND_{next_round}_REMEDIATION_WORKLOG.md`（逐 finding 记录：RED 证据 → 修复 → GREEN 证据）
2. `reports/{stage}/{stage.upper()}_ROUND_{next_round}_STARTING_WORKTREE_STATE.md`（§2 起始状态）
3. 新增/修改的测试与实现代码（含负向测试）
4. `reports/{stage}/SUBMISSION_TO_CHATGPT_{stage.upper()}_ROUND_{next_round}.md`（提交封面，含验证矩阵 + probe 重跑结果）

完成后停止，保持 P5 BLOCKED，等待 Round {next_round} 复审。

---

*Generated by run_kimi_audit.py（kimi-k3 裁决 + 独立验证）。*
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Kimi 审核流水线 v2（材料落 md + 短提示词）")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--round", required=True)
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--submission", required=True)
    ap.add_argument("--prior-audit", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--verification-packet", default=None)
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--auto-remediate", action="store_true",
                    help="审核完成后自动触发修复执行器")
    ap.add_argument("--repo-root", default=None,
                    help="主仓库根（remediation prompt 落盘处，默认 worktree）")
    args = ap.parse_args()

    wt = Path(args.worktree)
    stage = args.stage.lower()
    print(f"=== {stage.upper()} Round {args.round} Kimi 审核流水线 v2 ===")

    # 1. 独立重放验证矩阵
    verified_lines = []
    if not args.skip_verify:
        print("[1/4] 独立重放验证矩阵...")
        for cmd, label in STAGE_VERIFY_CMDS.get(stage, []):
            ok_codes = (0, 2) if "gate" in cmd else (0,)
            full = "gate" in cmd
            r = run_cmd(cmd, str(wt), ok_exit_codes=ok_codes,
                        full_output=full)
            mark = "✅" if r["ok"] else "❌"
            print(f"[PROGRESS] 验证 {label}: {mark} (exit {r.get('exit')})")
            if full:
                # R7-02: gate 输出保留完整关键行（逐 G 项 status + reason + Status）
                keep = [ln for ln in r["output"].splitlines()
                        if ln.strip().startswith("[") or "Status:" in ln]
                tail = "\n".join(keep)[:1500] or r["output"][-600:]
            else:
                # Strip ANSI colour codes and show the pytest summary line
                # verbatim ("83 passed in 0.88s") instead of a dot run — a
                # dot run trimmed to 150 chars never matches the total and
                # broke cross-round verification (R2-02/R3-02).
                clean = re.sub(r"\x1b\[[0-9;]*m", "", r["output"])
                summary_parts = []
                m_pass = re.search(r"\d+ passed[^\n]*", clean)
                m_fail = re.search(r"\d+ failed", clean)
                m_err = re.search(r"\d+ error", clean)
                if m_pass:
                    summary_parts.append(m_pass.group(0))
                if m_fail:
                    summary_parts.append(m_fail.group(0))
                if m_err:
                    summary_parts.append(m_err.group(0))
                tail = " | ".join(summary_parts) if summary_parts else \
                    " ".join(clean.split())[:150]
            verified_lines.append(
                f"- {label}: {'OK（exit ' + str(r.get('exit')) + '）' if r['ok'] else 'FAIL'} `{cmd}`\n  → {tail}")
    else:
        print("[1/4] 跳过验证重放")
    verified = "\n".join(verified_lines) or "(验证重放已跳过)"[:200]

    # 2. 读取材料
    print("[2/4] 读取提交材料与证据...")
    submission = resolve_path(args.submission, wt)
    prior = resolve_path(args.prior_audit, wt)
    claimed = extract_submission_matrix(submission)
    prior_findings = extract_prior_findings(prior)
    probes = ""
    if args.verification_packet:
        probes = extract_probes(resolve_path(args.verification_packet, wt))
    print(f"  · submission ✅ / prior ✅ / probes {len(probes)} chars")

    # 3. 生成任务书 md + 短提示词
    print("[3/4] 生成审核任务书 md...")
    next_round = str(int(args.round) + 1)
    handoff_rel = f"reports/{stage}/audit_packet/HANDOFF_{stage}_R{args.round}.md"
    handoff_path = wt / handoff_rel
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        build_handoff_md(args, claimed, prior_findings, probes, verified),
        encoding="utf-8")
    print(f"[PROGRESS] 任务书落盘: {handoff_path} ({handoff_path.stat().st_size} bytes)")

    short_prompt = build_short_prompt(args, handoff_path, "0.Verdict")
    print("\n  · 提交给 kimi 的短提示词风格（每块 3-4 行）：")
    for line in short_prompt.splitlines():
        print(f"    {line}")

    # 4. 分块调用 kimi（读 md + 输出指定章节）
    print("\n[4/4] 分块调用 kimi-k3（读任务书 md，输出各章节）...")
    results: dict[str, str] = {}
    for key, section in AUDIT_SECTIONS:
        prompt = build_short_prompt(args, handoff_path, section)
        print(f"[PROGRESS] kimi 征询 {key} 开始...")
        t0 = time.time()
        try:
            out = call_kimi(prompt)
            print(f"[PROGRESS] kimi 征询 {key} 完成 [{time.time()-t0:.0f}s] {out[:80]}...")
            results[key] = out
        except RuntimeError as e:
            print(f"[PROGRESS] kimi 征询 {key} ❌ 失败: {str(e)[:100]}")
            results[key] = f"(调用失败: {e})"

    # 5. 组装审核报告并落盘
    print("\n[5/5] 组装审核报告落盘...")
    out_path = resolve_path(args.output, wt)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    next_round = str(int(args.round) + 1)
    report = build_report_md(args, claimed, prior_findings, probes,
                             verified, results, wt)
    out_path.write_text(report, encoding="utf-8")
    print(f"[PROGRESS] 审核报告落盘: {out_path} ({out_path.stat().st_size} bytes)")

    # 6. 生成下一轮修复提示词 md
    print("[6/6] 生成修复提示词 md（Round N+1 Remediation Prompt）...")
    remed_path = generate_remediation_prompt(
        stage, args.round, next_round, out_path, wt,
        repo_root=args.repo_root)
    print(f"[PROGRESS] 修复提示词落盘: {remed_path} ({remed_path.stat().st_size} bytes)")

    # 7. 可选：自动触发修复执行器（审核闭环）
    if args.auto_remediate:
        print("\n[7/7] 自动触发修复执行器（--auto-remediate）...")
        remed_cmd = ([sys.executable, "-m", "scripts.run_kimi_remediate",
                      "--prompt", str(remed_path)] +
                     (["--skip-verify"] if args.skip_verify else []))
        try:
            rr = subprocess.run(remed_cmd, capture_output=True, text=True,
                                cwd=wt, timeout=1200)
            print(rr.stdout[-800:] if rr.stdout else "")
            if rr.stderr:
                print(f"  ⚠️ stderr: {rr.stderr[-300:]}")
            if rr.returncode != 0:
                print(f"  ⚠️ 修复执行器退出码 {rr.returncode}（见上方输出）")
        except subprocess.TimeoutExpired:
            print("  ⚠️ 修复执行器超时（1200s）")
    else:
        print(f"\n  💡 修复提示词已生成: {remed_path}")
        print(f"    自动实施修复: python3 -m scripts.run_kimi_remediate "
              f"--prompt {remed_path}")

    print(f"\n✅ 流水线完成：审核报告 + 修复提示词均已落盘。")


if __name__ == "__main__":
    main()