#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dual-caliber 机器检查:口径变更走新版本、双口径并列、历史不覆写。

调用:
    python3 scripts/bible_checks/check_dual_caliber.py --repo <repo根> [--batch <批根>] [--files ...]

- 给了 --batch(MODE=batch):批根真核。
  1. 双口径留存:metrics/report 是否保留 ≥2 个口径版本(.vN 变体或 criteria_vN 键);
  2. 历史覆写:核对批根 *SHA256SUMS* 封存清单(逐文件实测 SHA256),哈希不符或
     文件缺失 = 疑似原地覆写 → fail;无清单时以 .vN 文件 mtime 晚于当前文件做
     人工复核提示(mtime 证据弱,不判 fail);
  3. 新版本流程:声明了口径变更(criteria_v2/v3、老口径敏感性表)却无任何 .vN
     留存 → fail;报告 md 同时含主口径+老口径并列披露 → pass。
- 没给 --batch(MODE=degraded):扫 docs/ 结果/口径文档:
  1. 成绩数字(NN/分母、NN.N%、NNpp)同行或 ±2 行须有口径标签(criteria-vN/
     v1/v2/v3/主口径/老口径/口径),无标签 → fail(逐条带行号);
  2. 跨口径比较句式(v1/老口径 与 v2/主口径 同句且带比较词,无「不能比/分账/
     测量修正」类守卫)→ fail;
  3. 冻结类口径文档(CALIBER/CRITERIA 命名且含冻结/封存/历史件标记)在 git 里
     冻结后仍有改写记录(M)→ fail(疑似原地改写历史口径)。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "dual-caliber"
MAX_DOCS = 60
CONTEXT_LINES = 3  # 口径标签允许的相邻行窗口(±3;本仓规范写法是节标题带口径、表格随其后)

# 成绩数字形态(与 anchored-numbers 同款):百分比/分数(2-3 位分母)/百分点
NUM_PAT = re.compile(
    r"(?<![\d.])\d+(?:\.\d+)?%(?!\d)"
    r"|(?<![\d/.])\d{1,3}/\d{2,3}(?![\d/.])"
    r"|(?<![\w.])\d+(?:\.\d+)?pp(?![a-zA-Z0-9])")
# 口径标签锚(strict/hit@ 是本仓口径定义的主族词:主口径=matched_strict 参考边召回,
# 老口径=产物串 anyof;行内带 metric 族词视为已在口径语境里)
CALIBER_ANCHOR_PAT = re.compile(
    r"criteria[-_ ]?v[1-9]|\bv[1-3]\b|主口径|老口径|旧口径|新口径|main_caliber|anyof|口径"
    r"|strict|hit@|matched", re.I)
# 跨口径比较句式与守卫
CROSS_COMPARE_PAT = re.compile(
    r"(?:v1|老口径|anyof)[^。\n]{0,60}(?:v[23]|主口径|新口径)[^。\n]{0,40}"
    r"(?:比|差|提升|退化|还差|多出|高出|低于|高于|兑换|换算)")
CROSS_GUARD_PAT = re.compile(
    r"不能|不得|不是|禁止|无法|不构成|不外推|测量修正|分账|口径差|混算|不比|不直接|"
    r"并列|各自|分别|单独|非工程|双向不外推|不是同一把尺|回查|触发|预注册")
# 冻结/历史件标记(判定"历史口径文档"用)
FREEZE_MARK_PAT = re.compile(r"冻结|freeze|sealed|封存|只读|历史件|不作回写|不改写", re.I)
DEGRADED_NAME_PAT = re.compile(r"RESULT|RESULTS|CALIBER|CRITERIA|RECON", re.I)
DEGRADED_NAME_SKIP_PAT = re.compile(r"PREREG|REQUEST|_PLAIN|HANDOFF|TASK_|REVIEW_R", re.I)
VERSIONED_SUFFIX = re.compile(r"\.v(\d+)$")


def _versioned_variants(batch: Path):
    """批根内带 .vN 后缀的口径版本件,按基名分组: {base_name: [version,...]}。

    匹配文件全名(如 metrics.json.v1 → 基名 metrics.json,版本 1)。
    """
    groups = {}
    for p in sorted(batch.iterdir()):
        if not p.is_file():
            continue
        m = VERSIONED_SUFFIX.search(p.name)
        if m:
            groups.setdefault(p.name[: m.start()], []).append(int(m.group(1)))
    return groups


def _verify_manifests(batch: Path):
    """核对批根内 *SHA256SUMS* 清单。返回 (n_ok, findings, notes)。"""
    n_ok, findings, notes = 0, [], []
    manifests = [p for p in sorted(batch.rglob("*SHA256SUMS*")) if p.is_file()][:5]
    if not manifests:
        return 0, [], ["批根无 SHA256SUMS 封存清单,覆写核验记 unknown(不判 fail)"]
    for man in manifests:
        base = man.parent
        for raw in load_text(man).splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                continue
            want, rel = parts[0], parts[1].strip()
            target = base / rel.removeprefix("./")
            if not target.is_file():
                findings.append(finding(man, 0, f"封存清单文件缺失(疑似被删/改名): {rel}"))
                continue
            h = hashlib.sha256(target.read_bytes()).hexdigest()
            if h == want:
                n_ok += 1
            else:
                findings.append(finding(target, 0,
                                 f"封存清单哈希不符,历史件疑似被原地覆写: "
                                 f"清单 {want[:12]}… vs 实测 {h[:12]}…"))
        notes.append(f"{man.name}: 核 {n_ok} 项一致" if not findings else f"{man.name}: 有异常项")
    return n_ok, findings, notes


def _mtime_sanity(batch: Path, groups):
    """无清单时的 mtime 提示:.vN 历史件mtime 晚于当前件 → 需人工复核(不判 fail)。"""
    notes = []
    for base_stem, vers in groups.items():
        cur = batch / f"{base_stem}"
        if not cur.is_file():
            continue
        for v in vers:
            hist = batch / f"{base_stem}.v{v}"
            if hist.is_file() and hist.stat().st_mtime > cur.stat().st_mtime:
                notes.append(f"需人工复核: 历史件 {hist.name} mtime 晚于当前件 "
                             f"{cur.name}(无封存清单,mtime 证据弱,不判 fail)")
    return notes


def run_batch(batch: Path):
    """批根模式。返回 emit 参数 dict。"""
    findings, notes = [], []
    notes.append("MODE=batch")
    if not batch.is_dir():
        return {"status": "error", "findings": [finding(batch, 0, "批根目录不存在")],
                "notes": notes, "n_pass": 0, "n_fail": 0}

    metrics = batch / "metrics.json"
    groups = _versioned_variants(batch)
    has_versions = any(len(v) >= 1 for v in groups.values())
    declared = False
    if metrics.is_file():
        try:
            m = _safe_json(metrics)
            declared = bool(m.get("criteria_v2") or m.get("criteria_v3")
                            or (isinstance(m.get("caliber_policy"), dict)
                                and m["caliber_policy"].get("old_caliber")))
        except ValueError:
            findings.append(finding(metrics, 0, "metrics.json 解析失败"))
    declared = declared or has_versions
    if not declared:
        notes.append("未见口径变更声明(无 .vN 变体、无 criteria_vN/old_caliber 键),"
                     "双口径留存检查不适用;封存清单覆写核验照做")
        n_ok, f_man, n_man = _verify_manifests(batch)
        notes += n_man
        return _finish(notes, f_man, n_pass=n_ok)

    # 检查项 1:双口径留存(声明了变更就要有 ≥2 版本结果)
    n_pass = 1
    retained = {k: sorted(set(v)) for k, v in groups.items() if len(set(v)) >= 1}
    multi = [k for k, v in groups.items() if len(set(v)) >= 1 and (batch / k).is_file()]
    if multi:
        n_pass += 1
        notes.append("双口径留存: " + ", ".join(
            f"{k}(v{','.join(str(x) for x in sorted(set(groups[k])))})" for k in multi[:6]))
    else:
        findings.append(finding(batch, 0,
                         "口径变更已声明但未见任何旧口径版本件(.vN)留存,双口径并列不成立"))

    # 检查项 2:新版本流程(有 v3 类披露却连 v1 都不留 → 原地改)
    max_v = max((max(v) for v in groups.values()), default=0)
    if max_v >= 2 and not any(min(groups[k]) == 1 for k in groups):
        findings.append(finding(batch, 0,
                         f"口径已演进到 v{max_v} 但无 v1 版本件留存,疑似原地改写历史口径"))

    # 检查项 3:报告双口径并列披露
    report = batch / "report.md"
    if report.is_file():
        text = load_text(report)
        if "主口径" in text and ("老口径" in text or "敏感性" in text):
            n_pass += 1
            notes.append("报告含主口径+老口径(敏感性)并列披露")
        else:
            notes.append("unknown: report.md 未检出主口径+老口径并列披露措辞(不判 fail)")

    # 检查项 4:封存清单核覆写
    n_ok, f_man, n_man = _verify_manifests(batch)
    n_pass += n_ok
    findings += f_man
    notes += n_man
    if not f_man:
        notes += _mtime_sanity(batch, groups)
    return _finish(notes, findings, n_pass)


def _finish(notes, findings, n_pass):
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def _safe_json(p: Path):
    return json.loads(load_text(p))


def _default_files(repo: Path):
    docs = repo / "docs"
    if not docs.is_dir():
        return []
    out = [p for p in sorted(docs.glob("*.md"))
           if DEGRADED_NAME_PAT.search(p.name) and not DEGRADED_NAME_SKIP_PAT.search(p.name)]
    return out[:MAX_DOCS]


def _git_modifications(repo: Path, rel: str):
    """git 里该文件的改写(M)提交数;非 git/出错返回 None。"""
    try:
        r = subprocess.run(["git", "-C", str(repo), "log", "--format=%h",
                            "--diff-filter=M", "--", rel],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return len([l for l in r.stdout.splitlines() if l.strip()])


def run_repo(repo: Path, file_specs=None, max_findings: int = 100):
    """降级模式:口径标签、跨口径比较、冻结口径文档 git 改写。"""
    findings, notes = [], []
    notes.append("MODE=degraded")
    if file_specs:
        files, _ = _expand(repo, file_specs)
    else:
        files = _default_files(repo)
    if not files:
        notes.append("无可扫文档,0 检查,不判 fail")
        return _finish(notes, findings, 0)
    notes.append(f"降级模式(无批根):扫 docs/ {len(files)} 份结果/口径文档"
                 f"(口径标签 + 跨口径比较,上限 {MAX_DOCS} 份)")

    n_numbers = 0
    for p in files:
        text = load_text(p)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for m in NUM_PAT.finditer(line):
                tok = m.group()
                # 跳过完成率(298/298)与阈值/比较符邻接的数字(<32%、≥116 不是读数)
                if "/" in tok:
                    num, den = tok.split("/", 1)
                    if num == den:
                        continue
                before = line[: m.start()].rstrip()
                if before and before[-1] in "<≤≥≧>＞<":
                    continue
                n_numbers += 1
                if len(findings) >= max_findings:
                    continue
                ctx = "\n".join(lines[max(0, i - CONTEXT_LINES): i + CONTEXT_LINES + 1])
                if not CALIBER_ANCHOR_PAT.search(ctx):
                    findings.append(finding(p, i + 1, f"成绩数字无口径标签: {tok}"))
            # 跨口径比较句式(无守卫)
            if CROSS_COMPARE_PAT.search(line) and not CROSS_GUARD_PAT.search(line):
                findings.append(finding(p, i + 1,
                                 f"疑似跨口径比较句式(需人工复核): {line.strip()[:60]}"))

    # 冻结类口径文档的 git 改写检查(草案 DRAFT 是活文档,不在此列)
    n_hist_checked = 0
    for p in files:
        name = p.name.upper()
        if "CALIBER" not in name and "CRITERIA" not in name:
            continue
        if "DRAFT" in name or "PREREG" in name:
            continue
        text = load_text(p)
        if not FREEZE_MARK_PAT.search(text):
            continue
        n_hist_checked += 1
        rel = str(p.relative_to(repo))
        mods = _git_modifications(repo, rel)
        if mods is None:
            notes.append(f"unknown: 非 git 仓或 git 不可用,无法核 {p.name} 的改写历史")
        elif mods > 0:
            findings.append(finding(p, 0,
                             f"冻结/历史类口径文档在 git 中有 {mods} 次改写记录(M),"
                             f"疑似原地改写历史口径(需人工核对是否为冻结前修订)"))
        else:
            notes.append(f"历史口径件 {p.name}: git 零改写(M=0),历史不覆写可核")

    notes.append(f"共识别 {n_numbers} 个成绩数字,无口径标签 {sum(1 for f in findings if '口径标签' in f['msg'])} 个;"
                 f" 冻结类口径文档 git 改写核查 {n_hist_checked} 份")
    n_pass = n_numbers - sum(1 for f in findings if "口径标签" in f["msg"])
    return _finish(notes, findings, max(n_pass, 0))


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
    return list(out.values()), []


def run_check(repo: Path, batch: Path | None = None, file_specs=None, max_findings: int = 100):
    if batch is not None:
        return run_batch(batch)
    return run_repo(repo, file_specs, max_findings)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="dual-caliber 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--batch", default=None, help="批根目录(缺省则降级扫 docs/)")
    ap.add_argument("--files", nargs="*", default=None, help="降级模式要扫的 glob/文件")
    ap.add_argument("--max-findings", type=int, default=100, help="finding 上限")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), Path(args.batch) if args.batch else None,
                  args.files, args.max_findings)
    print(f"MODE={'batch' if args.batch else 'degraded'}")  # 契约:摘要首行标注模式
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
