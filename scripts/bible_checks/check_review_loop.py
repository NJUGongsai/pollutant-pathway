#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review-loop 机器检查:评审交付的 provenance、代审标注与互证采信。

调用:
    python3 scripts/bible_checks/check_review_loop.py --repo <repo根> [--files ...]

评审报告来源(docs/ 顶层,按本仓真实命名形态识别):
- 收:名字含 review/response/reaudit,或含 decision 且带通道词(codex/qwen/gpt/
  claude/tokeasy/mimo/channelc);
- 不收:评审请求(*REQUEST*)与任务书/交接/协议/登记类(HANDOFF/PROTOCOL/PROMPT/
  REGISTER/ADOPTION/PACKAGE/MEMO/PACK/TUNING/FOR_REVIEW/TASK_ 前缀)。

检查项(每份报告):
1. provenance:头部(默认前 40 行)须有 通道/模型 标识(文件名通道词或正文
   codex/qwen/mimo/gpt/claude/tokeasy/opencode/独立评审人/子代理/本地预审…)
   且有 日期或 HEAD/commit 锚;缺任一 → fail;
2. 代审标注:名字或正文呈代审形态(qwen/channelc/tokeasy/local/deputy/
   substitute/代审/代 Codex/代决/替 Codex/备用通道/代师姐/代位)的文件,
   头部须有 ①代审者身份 ②授权链(按 CC 指示/指派/授权) ③后置复核或
   最终裁定权说明(bible §5 三要素口径),缺任一 → fail(纯名字暗示而
   正文全无自标识 → 「代审未标注」;mimo 通道自有 provenance 义务,
   不套代 Codex 三要素);
3. 互证采信:全文须含 互证/采信/互核/不做背书/独立性 等采信限度表述,
   缺 → fail。
评审报告一份都没有 → error。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "review-loop"
HEADER_LINES = 40  # provenance 检查的头部行数窗口(本仓报告头部 provenance 块均在此内)
MAX_DOCS = 200

# 通道/模型身份词(正文或文件名)
CHANNEL_PAT = re.compile(
    r"codex|qwen|mimo|chatgpt|gpt-|tokeasy|opencode|claude|opus|fable|glm|"
    r"独立评审人|本地预审|子代理|备用通道|代审|代 Codex|代决|代师姐", re.I)
# 日期或 HEAD/commit 锚
TIME_ANCHOR_PAT = re.compile(
    r"\d{4}-\d{2}-\d{2}|(?<![0-9a-fA-F])[0-9a-fA-F]{7,40}(?![0-9a-fA-F])")
# 代审形态:文件名提示
SUB_NAME_PAT = re.compile(
    r"qwen|channelc|channel_c|tokeasy|local|deputy|substitute", re.I)
# 代审形态:正文自标识(分类用;不冒充/不替代是三要素之一,不作分类信号——
# 正链复审的表格行也会出现「不冒充」字样,见 S5A 反例)
SUB_TEXT_PAT = re.compile(
    r"代审|代\s*Codex|代决|替\s*Codex|备用通道|代师姐|代位", re.I)
# 代审三要素(bible §5 清单口径:身份 / 授权链 / 后置复核项)
SUB_ID_PAT = re.compile(r"代审|代\s*Codex|代决|替\s*Codex|代替\s*Codex|备用通道|代师姐|代位", re.I)
SUB_AUTH_PAT = re.compile(
    r"按\s*CC|CC\s*指示|CC\s*指派|指派|授权|委托|拍板|代师姐|代\s*CC", re.I)
SUB_POSTREVIEW_PAT = re.compile(
    r"后置复核|复核项|复核确认|复核权|最终裁定|最终复核|CC 复核|正审|正链|通道\s*B|"
    r"由\s*CC\s*(决定|裁决|拍板|复核)|采信顺序", re.I)
# 代位 mimo 的识别(mimo 通道自有 provenance 义务,三要素按代 Codex 纪律不作硬要求)
SUB_MIMO_PAT = re.compile(r"代位\s*mimo|mimo\s*场景[^。\n]{0,12}代位|代 mimo", re.I)
# 互证采信
MUTUAL_PAT = re.compile(
    r"互证|采信|互核|不做背书|独立性背书|不构成独立性|独立执行|与程序证据|与源码", re.I)

INCLUDE_PAT = re.compile(r"review|response|reaudit", re.I)
EXCLUDE_PAT = re.compile(
    r"request|_req\b|handoff|review_protocol|prompt|register|adoption|package|"
    r"for_review|memo|_pack_|tuning|conclusions", re.I)
EXCLUDE_PREFIX = ("task_",)


def _channel_in_name(name: str) -> bool:
    return bool(re.search(r"codex|qwen|mimo|gpt|claude|tokeasy|channelc|fable", name, re.I))


def discover_reports(repo: Path):
    """按本仓命名形态收集评审报告(排除请求与任务书/协议/登记类)。"""
    docs = repo / "docs"
    if not docs.is_dir():
        return []
    out = []
    for p in sorted(docs.glob("*.md")):
        low = p.name.lower()
        if low.startswith(EXCLUDE_PREFIX) or EXCLUDE_PAT.search(low):
            continue
        is_decision = "decision" in low and _channel_in_name(low)
        if INCLUDE_PAT.search(low) or is_decision:
            out.append(p)
    return out[:MAX_DOCS]


def _expand(repo: Path, specs):
    out = {}
    for spec in specs:
        p = Path(spec)
        if not p.is_absolute():
            p = repo / p
        if p.is_dir():
            matches = sorted(p.glob("*.md"))
        elif p.is_file():
            matches = [p]
        else:
            matches = sorted(repo.glob(spec))
        for m in matches:
            if m.is_file():
                out.setdefault(m.resolve(), m)
    return list(out.values())


def check_report(path: Path, header_lines: int = HEADER_LINES):
    """对单份评审报告跑三项检查。返回 (n_pass, findings)。"""
    findings = []
    text = load_text(path)
    header = "\n".join(text.splitlines()[:header_lines])
    n_pass = 0

    # 检查 1:provenance(通道/模型 + 日期/HEAD)
    identity = bool(CHANNEL_PAT.search(header)) or _channel_in_name(path.name)
    anchor = bool(TIME_ANCHOR_PAT.search(header))
    if identity and anchor:
        n_pass += 1
    elif not identity:
        findings.append(finding(path, 0,
                         "缺 provenance:头部未见通道/模型标识(codex/qwen/mimo/gpt/"
                         "claude/tokeasy/opencode/独立评审人/子代理 等)"))
    else:
        findings.append(finding(path, 0, "缺 provenance:头部未见日期或 HEAD/commit 锚"))

    # 检查 2:代审标注三要素(bible §5:身份/授权链/后置复核项)
    is_substitute = bool(SUB_NAME_PAT.search(path.name)) or bool(SUB_TEXT_PAT.search(header))
    if is_substitute:
        is_mimo_channel = ("mimo" in path.name.lower() or SUB_MIMO_PAT.search(header)) \
            and not re.search(r"代\s*Codex|代决|备用通道", header, re.I)
        if is_mimo_channel:
            n_pass += 1  # 通道 A 自有 provenance 义务,由检查 1 覆盖
        else:
            elems = [
                ("代审者身份(代审/代 Codex/代决/替 Codex/备用通道/代位)", SUB_ID_PAT),
                ("授权链(按 CC 指示/指派/授权/委托)", SUB_AUTH_PAT),
                ("后置复核/最终裁定权说明", SUB_POSTREVIEW_PAT),
            ]
            missing = [label for label, pat in elems if not pat.search(header)]
            if not missing:
                n_pass += 1
            elif not SUB_ID_PAT.search(header) and not SUB_ID_PAT.search(text[:4000]):
                findings.append(finding(path, 0, "代审未标注:全文未见「代 Codex/代审/代决」"
                                       "类身份自标识(仅文件名暗示)"))
            else:
                findings.append(finding(path, 0,
                                 "代审 provenance 三要素缺: " + "、".join(missing)))

    # 检查 3:互证采信结论
    if MUTUAL_PAT.search(text):
        n_pass += 1
    else:
        findings.append(finding(path, 0,
                         "缺互证采信结论(互证/采信/互核/不做背书/与程序证据 均未出现)"))
    return n_pass, findings


def run_check(repo: Path, file_specs=None, header_lines: int = HEADER_LINES,
              max_findings: int = 200):
    """主检查。返回 emit 所需参数 dict。"""
    notes = ["MODE=repo(评审交付在 docs/,本检查无批根形态;--files 可指定范围)"]
    files = _expand(repo, file_specs) if file_specs else discover_reports(repo)
    if not files:
        return {"status": "error",
                "findings": [finding(repo / "docs", 0, "未发现任何评审报告(命名形态见脚本头)")],
                "notes": notes, "n_pass": 0, "n_fail": 0}
    notes.append(f"扫 docs/ 评审报告 {len(files)} 份(provenance/代审标注/互证采信,上限 {MAX_DOCS})")

    n_pass = 0
    findings = []
    for p in files:
        np_, fd = check_report(p, header_lines)
        n_pass += np_
        findings += fd
    n_sub = sum(1 for p in files
                if SUB_NAME_PAT.search(p.name))
    notes.append(f"其中文件名呈代审形态 {n_sub} 份(qwen/通道C/本地预审/代审等),"
                 f"须过代审三要素")
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings[:max_findings], "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="review-loop 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--files", nargs="*", default=None, help="要扫的 glob/文件(缺省=docs/ 自动识别)")
    ap.add_argument("--header-lines", type=int, default=HEADER_LINES,
                    help="provenance 检查的头部行数窗口(缺省 40)")
    ap.add_argument("--max-findings", type=int, default=200, help="finding 上限")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), args.files, args.header_lines, args.max_findings)
    print("MODE=repo")  # 契约:摘要首行标注模式
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
