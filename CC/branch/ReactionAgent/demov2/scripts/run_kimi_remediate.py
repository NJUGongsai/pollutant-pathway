#!/usr/bin/env python3
"""修复执行器 — 审核闭环的修复段：无头调 claude 实施修复。

配套 run_kimi_audit.py（审核段）。审核段产出 KIMI_*_REMEDIATION_PROMPT.md
修复任务书后，本脚本解析任务书 → 构造短提示词 → claude -p 无头实施修复
（RED→GREEN→worklog）→ 验证测试全绿。

用法:
  python3 scripts/run_kimi_remediate.py \
      --prompt reports/p4/KIMI_P4_ROUND_5_REMEDIATION_PROMPT.md

风格（与审核段一致，两层式）:
  Layer 1: 完整修复任务书 → md（已由审核段生成）
  Layer 2: 提交给 claude 的只有 3-4 行短提示词（读 md + 目标 + 交付物）
  claude 通过 --permission-mode acceptEdits + 白名单在 worktree 内自主修复。

流程:
  1. 解析任务书 md：stage / round / worktree / findings
  2. 构造 3-4 行短提示词，调 claude -p 无头执行
  3. 验证 worklog 生成 + pytest tests/{stage} 全绿
"""
from __future__ import annotations

import argparse
import functools
import re
import subprocess
import sys
import time
from pathlib import Path

# 所有 print 实时 flush：配合 Monitor tail -f 实现修复进度实时透出
print = functools.partial(print, flush=True)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

CLAUDE = "claude"
CLAUDE_TIMEOUT = 900          # 修复任务长，给足时间

# 默认白名单：只给写文件 + 测试 + git 只读 + python 命令
DEFAULT_ALLOWED_TOOLS = (
    "Read,Glob,Grep,Write,Edit,"
    "Bash(python*),Bash(pytest*),Bash(git status*),Bash(git diff*),Bash(ls*),"
    "Bash(cd*),Bash(run_p4*),Bash(run_p1*),Bash(run_p2*),Bash(run_p3*),"
    "Bash(run_p5*)"
)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def run_cmd(cmd: str, cwd: str, timeout: int = 300,
            ok_exit_codes: tuple = (0,)) -> dict:
    """运行命令。gate 类命令 exit 2(BLOCKED) 视为预期。"""
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True,
            timeout=timeout)
        return {"ok": r.returncode in ok_exit_codes,
                "exit": r.returncode,
                "output": (r.stdout or "")[-600:] + (r.stderr or "")[-200:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit": -1, "output": f"[超时 {timeout}s]"}


def parse_prompt_meta(prompt_path: Path) -> dict:
    """从任务书文件名 + 内容解析 stage/round/worktree/findings。

    文件名约定: KIMI_<STAGE>_ROUND_<N>_REMEDIATION_PROMPT.md
    内容约定:  `## 2. 工作树、分支和环境` 代码块含 worktree 路径；
              `## 3. Mandatory findings` 下 `### P4-R4-XX` 或 `P4-R4-XX` 编号。
    """
    text = prompt_path.read_text(encoding="utf-8")
    name = prompt_path.stem  # KIMI_P4_ROUND_5_REMEDIATION_PROMPT

    m = re.search(r"KIMI_([A-Z0-9]+)_ROUND_(\d+)_REMEDIATION_PROMPT", name)
    stage_raw = m.group(1).lower() if m else "p4"
    round_ = m.group(2) if m else ""
    next_round = str(int(round_) + 1) if round_ else ""

    # worktree 路径：## 2. 工作树、分支和环境 段内代码块（首行非注释路径）
    wt = ""
    sec = re.search(r"##\s*2\.\s*工作树.*?```(.*?)```",
                    text, re.DOTALL)
    if sec:
        for line in sec.group(1).splitlines():
            s = line.strip()
            if s.startswith("/") and not s.startswith("//"):
                wt = s
                break
    if not wt:
        # 兜底：匹配任意绝对路径
        m2 = re.search(r"/(?:Volumes|Users|private)/[^\s`]+", text)
        wt = m2.group(0) if m2 else ""

    # findings：## 3. Mandatory findings 段内 P?-R?-XX 编号，去重保序
    # lookahead 排除同标题（标题可能带"（必须全部修复）"注释），用编号章节 4+ 分界
    sec3 = re.search(r"##\s*3\.\s*Mandatory findings(.*?)(?=\n##\s*[4-9]\.|\Z)",
                     text, re.DOTALL)
    findings = []
    if sec3:
        for fid in re.findall(r"\b(P\d+-R\d+-[A-Z\d]+)\b", sec3.group(1)):
            if fid not in findings:
                findings.append(fid)

    return {"stage": stage_raw, "round": round_, "next_round": next_round,
            "worktree": wt, "findings": findings}


def build_remediate_prompt(prompt_path: Path, meta: dict) -> str:
    """3-4 行短提示词：读任务书 md + 修复要求 + 交付物。"""
    return (
        f"你是 ReactionAgent 的修复执行者。完整读取并严格执行修复任务书：\n"
        f"{prompt_path}\n"
        f"要求：对每个 finding 先写 RED 负向测试（确认失败）再实施修复（GREEN）；\n"
        f"运行 {meta['stage'].upper()} 测试套件全绿；生成 worklog 到 "
        f"reports/{meta['stage']}/{meta['stage'].upper()}_ROUND_{meta['next_round']}_REMEDIATION_WORKLOG.md；\n"
        f"完成后输出修复摘要（每 finding 的 RED→GREEN 证据）。禁止事项见任务书，自行遵守。"
    )


def invoke_claude(prompt: str, worktree: str, allowed_tools: str) -> dict:
    """claude -p 无头执行修复（acceptEdits + 白名单，不越权）。"""
    cmd = [
        CLAUDE, "-p", prompt,
        "--permission-mode", "acceptEdits",
        "--allowedTools", allowed_tools,
    ]
    t0 = time.time()
    try:
        # Popen + 逐行转发：claude 无头输出实时透出（配合 Monitor 实时进度）
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=worktree, text=True, bufsize=1)
        out_lines: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            out_lines.append(line)
            if line.strip():
                print(f"[CLAUDE] {line[:200]}", flush=True)
        proc.wait(timeout=CLAUDE_TIMEOUT)
        return {"ok": proc.returncode == 0, "exit": proc.returncode,
                "output": "\n".join(out_lines)[-800:],
                "elapsed": time.time() - t0}
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"ok": False, "exit": -1,
                "output": f"[超时 {CLAUDE_TIMEOUT}s]",
                "elapsed": time.time() - t0}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="修复执行器（claude 无头修复）")
    ap.add_argument("--prompt", required=True,
                    help="KIMI_*_REMEDIATION_PROMPT.md 修复任务书路径")
    ap.add_argument("--worktree", default=None,
                    help="worktree 路径（默认从任务书解析）")
    ap.add_argument("--allowed-tools", default=DEFAULT_ALLOWED_TOOLS)
    ap.add_argument("--skip-verify", action="store_true",
                    help="跳过修复后 pytest 验证")
    args = ap.parse_args()

    prompt_path = Path(args.prompt).resolve()
    if not prompt_path.exists():
        print(f"❌ 任务书不存在: {prompt_path}")
        sys.exit(1)

    # 1. 解析任务书
    meta = parse_prompt_meta(prompt_path)
    print(f"=== 修复执行器: {meta['stage'].upper()} Round {meta['round']} ===")
    print(f"  · 任务书: {prompt_path}")
    print(f"  · 下一轮: Round {meta['next_round']}")
    print(f"  · worktree: {meta['worktree'] or '(未解析到)'}")
    print(f"  · findings ({len(meta['findings'])}): {', '.join(meta['findings']) if meta['findings'] else '(未解析到)'}")

    worktree = args.worktree or meta["worktree"]
    if not worktree or not Path(worktree).exists():
        print(f"❌ worktree 不存在或未解析: {worktree!r}")
        sys.exit(1)

    # 2. 构造短提示词 + claude 无头执行
    prompt = build_remediate_prompt(prompt_path, meta)
    print(f"\n  · 提交给 claude 的短提示词（3-4 行）：")
    for line in prompt.splitlines():
        print(f"    {line}")
    print(f"\n  · claude -p 执行中（acceptEdits + 白名单）...")
    r = invoke_claude(prompt, worktree, args.allowed_tools)
    print(f"    [{r['elapsed']:.0f}s] exit={r['exit']}")
    tail = " ".join(r["output"].split())[:300]
    print(f"    → {tail}")

    # 3. 验证 worklog 生成
    worklog_rel = (f"reports/{meta['stage']}/"
                   f"{meta['stage'].upper()}_ROUND_{meta['next_round']}_REMEDIATION_WORKLOG.md")
    worklog = Path(worktree) / worklog_rel
    worklog_ok = worklog.exists()
    print(f"\n  · worklog: {'✅ 已生成' if worklog_ok else '❌ 未生成'} {worklog_rel}"
          f" ({worklog.stat().st_size} bytes)" if worklog_ok else
          f"\n  · worklog: ❌ 未生成 {worklog_rel}")

    # 4. 验证测试全绿（可跳过）
    test_ok = "SKIPPED"
    if not args.skip_verify:
        print(f"\n  · pytest tests/{meta['stage']} 验证中...")
        tr = run_cmd(f"python3 -m pytest -q -p no:cacheprovider tests/{meta['stage']}",
                     worktree, timeout=600)
        test_ok = "✅" if tr["ok"] else f"❌ exit={tr['exit']}"
        print(f"    {test_ok} {tr['output'][-200:]}")
    else:
        print("\n  · pytest 验证跳过（--skip-verify）")

    summary_ok = worklog_ok and (test_ok == "SKIPPED" or tr["ok"])
    print(f"\n=== 修复执行{'✅ 完成' if summary_ok else '⚠️ 部分完成'} ===")
    print(f"  worklog: {worklog_rel}")
    print(f"  测试: {test_ok}")
    if not r["ok"]:
        print(f"  ⚠️ claude 无头退出码 {r['exit']}（可能部分修复未完成）")
    sys.exit(0 if summary_ok else 2)


if __name__ == "__main__":
    main()