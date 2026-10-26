#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anchored-numbers 机器检查:一切数字带锚(commit/口径标签/批次名)。

调用:
    python3 scripts/bible_checks/check_anchored_numbers.py --repo <repo根> \
        [--files <glob或文件> ...] [--max-findings N] [--ignore-pattern <regex>]...

文件来源三级缺省:
    1. --files 指定的 glob/文件(相对 --repo 解析);
    2. 缺省取 `git diff --name-only HEAD` 中改动的 .md;
    3. 再缺省扫 docs/BIBLE/*.md。

规则:形如 NN.N% / NN/NNN(如 89/298) / NN.Npp 的数字,同行或 ±2 行内
必须出现以下锚之一:7–40 位 hex(commit)、口径标签(v1/v2/v3/298/dev)、
批次名模式(p2[-_]298/chain1N/t-h/bN)。无锚 → finding(path, line, 数字原文)。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, git_head, load_text  # noqa: E402

CHECK = "anchored-numbers"
CONTEXT_LINES = 2  # 锚允许出现的相邻行窗口(±2)

# 数字形态(按本仓实际写法校准):
#   百分比 12.3%|86% ;分数 89/298(分子 1-3 位,分母 2-3 位,前后不能再是数字/斜杠,
#   借此排除日期 2026/10/21) ;百分点 5.03pp
NUM_PAT = re.compile(
    r"(?<![\d.])\d+(?:\.\d+)?%(?!\d)"
    r"|(?<![\d/.])\d{1,3}/\d{2,3}(?![\d/.])"
    r"|(?<![\w.])\d+(?:\.\d+)?pp(?![a-zA-Z0-9])"
)
# 锚:7–40 位 hex commit(前后不能再是 hex 字符)|口径标签 v1/v2/v3/298/dev|批次名
ANCHOR_PAT = re.compile(
    r"(?<![0-9a-fA-F])[0-9a-fA-F]{7,40}(?![0-9a-fA-F])"
    r"|\b(?:v[1-3]|298|dev)\b"
    r"|\bp2[-_]298\b|chain1\d|\bt-h\b|\bb\d\b",
    re.I,
)


def default_files(repo: Path) -> list[Path]:
    """三级缺省:git diff HEAD 的 .md → docs/BIBLE/*.md → 空。"""
    head = git_head(repo)
    if head:
        import subprocess
        r = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "HEAD"],
                           capture_output=True, text=True, timeout=15)
        mds = [repo / line for line in r.stdout.splitlines()
               if line.strip().endswith(".md") and (repo / line).is_file()]
        if mds:
            return sorted(set(mds))
    return sorted((repo / "docs" / "BIBLE").glob("*.md")) if (repo / "docs" / "BIBLE").is_dir() else []


def expand_files(repo: Path, specs: list[str]):
    """把 --files 的每个参数按 glob 展开(相对 --repo)。

    返回 (files, unmatched):unmatched = 一个文件都没展开出来的 spec,供摘要提示。
    """
    out, unmatched = {}, []
    for spec in specs:
        p = Path(spec)
        if not p.is_absolute():
            p = repo / p
        if p.is_dir():
            matches = sorted(p.rglob("*.md"))
        elif p.is_file():
            matches = [p]
        else:
            matches = sorted(repo.glob(spec))
        hits = [m for m in matches if m.is_file()]
        if not hits:
            unmatched.append(spec)
            continue
        for m in hits:
            out.setdefault(m.resolve(), m)
    return list(out.values()), unmatched


def scan_file(path: Path, ignore_res: list[re.Pattern], max_findings: int):
    """扫单文件:返回 (n_numbers, findings, truncated)。

    同行或 ±2 行内有锚 → 通过;无锚且未命中 ignore 正则 → finding。
    """
    lines = load_text(path).splitlines()
    n_numbers, findings = 0, []
    truncated = False
    for i, line in enumerate(lines):
        for m in NUM_PAT.finditer(line):
            n_numbers += 1
            if truncated:
                continue
            ctx = "\n".join(lines[max(0, i - CONTEXT_LINES): i + CONTEXT_LINES + 1])
            if ANCHOR_PAT.search(ctx):
                continue
            if any(rx.search(line) for rx in ignore_res):
                continue
            if len(findings) >= max_findings:
                truncated = True
                continue
            findings.append(finding(path, i + 1, f"数字无锚: {m.group()}"))
    return n_numbers, findings, truncated


def run_check(repo: Path, file_specs=None, max_findings=100, ignore_patterns=()):
    """主检查。返回 emit 所需参数 dict。"""
    ignore_res = []
    for pat in ignore_patterns:
        try:
            ignore_res.append(re.compile(pat))
        except re.error as e:
            return {"status": "error",
                    "findings": [finding(repo, 0, f"--ignore-pattern 非法正则 {pat}: {e}")],
                    "notes": [], "n_pass": 0, "n_fail": 0}

    if file_specs:
        files, unmatched = expand_files(repo, list(file_specs))
    else:
        files, unmatched = default_files(repo), []

    notes = []
    if not files:
        notes.append("无可扫文件(git diff 无改动 md,docs/BIBLE/ 也为空)——本轮 0 检查,不判 fail")
        return {"status": "pass", "findings": [], "notes": notes, "n_pass": 0, "n_fail": 0}
    notes.append(f"扫 {len(files)} 份 md" + (f"(--files 指定;零命中 spec: {unmatched})" if unmatched else ""))

    findings, n_numbers, truncated = [], 0, False
    for f in files:
        n, fd, tr = scan_file(f, ignore_res, max_findings - len(findings))
        n_numbers += n
        findings += fd
        truncated = truncated or tr
    if truncated:
        notes.append(f"finding 数达到 --max-findings={max_findings} 上限,其余截断")
    if n_numbers:
        notes.append(f"共识别 {n_numbers} 个带锚要求数字,无锚 {len(findings)} 个")
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_numbers - len(findings), "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="anchored-numbers 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--files", nargs="*", default=None, help="要扫的 glob/文件(缺省=git diff 的 md)")
    ap.add_argument("--max-findings", type=int, default=100, help="finding 上限(降误报截断)")
    ap.add_argument("--ignore-pattern", action="append", default=[],
                    help="命中该正则的行豁免(可多次)")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), args.files, args.max_findings, args.ignore_pattern)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
