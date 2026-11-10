#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe-before-build 机器检查:零 LLM 探针先行 —— 过门才立项。

调用:
    python3 scripts/bible_checks/check_probe_before_build.py --repo <repo根> \
        [--files <方案md/探针md> ...]

两种用法(可叠加):
1. 缺省(--repo):在 docs/ 下发现探针文档(文件名含 probe/探针,排除 docs/BIBLE/),
   按三类分别核:
   - 报告类(非 TASK/INPUT/INITIATION 名,非 review_evidence 附件):
     ①零模型调用声明 ②门结论(过/不过/成立/不成立/未过线/结项/撤销)
     ③引用了真实存在的证据文件(reports|docs|scripts|src 路径且磁盘可定位)。
     缺报告 → fail;报告缺门结论 → fail;零 LLM 声明缺失 → fail;
     「探针≠预注册≠成绩」标签缺失 → 附注(历史报告不回写,不判 fail)。
   - 任务书/立项输入类(TASK_*/*INITIATION*/*INPUT*/*PLAN*):核①,
     门结论只附注(尚未执行属正常)。
   - review_evidence/ 附件:只附注,不判 fail(证据附件非报告正文)。
   - *_PLAIN.md 与同干主报告并存时跳过(副本不重复判)。
2. --files 给方案/立项 md:扫「新增/解锁/召回/救回」类增面数字,±2 行内须有
   探针出处(探针|probe|review_evidence|面数实测);无出处 → fail(bible §6)。

首行打印 MODE 行(repo=docs 探针报告面,files=方案 md 面)。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "probe-before-build"
CONTEXT_LINES = 2

# ①零模型调用声明(按本仓探针报告实际用词:零模型零 API 零判分重算零网络零付费)
ZERO_LLM_PAT = re.compile(
    r"零\s*模型|零\s*LLM|零LLM|零\s*API|零网络|零付费|零判分|只读探针|零调用", re.I)
# ②门结论(过/不过及其本仓变体)
GATE_CONCL_PAT = re.compile(
    r"过/不过|不通过|未过线|未达线|未达|达标|不达标|结项|立项|撤销|"
    r"成立|不成立|通过门|过门|未过|不再推进|放行")
# 「探针≠预注册≠成绩」标签(细则5;历史件缺失只附注)
LABEL_PAT = re.compile(r"探针\s*≠\s*预注册|探针≠预注册|探针≠成绩", re.I)
# ③证据引用:reports|docs|scripts|src 下带扩展名的路径
EVID_PATH_PAT = re.compile(
    r"\b(?:reports|docs|scripts|src)/[A-Za-z0-9_\-./]+\.(?:py|json|md|txt|sh|csv)")
# 任务书/立项输入类文件名
BRIEF_NAME_PAT = re.compile(r"^TASK_|INITIATION|_INPUT|PLAN|任务书|_设计", re.I)
# 副本后缀(与同干主报告并存时不重复判)
_PLAIN_SUFFIX = "_plain"

# 增面数字(方案 md 用):新增/解锁/召回/救回 + 数字
CLAIM_NUM_PAT = re.compile(
    r"(?:新增|解锁|召回|救回|面数)\s*(?:约|≈|~)?\s*\d+"
    r"|\d+\s*(?:题|行)\s*(?:新增|增量|潜力)")
# 探针出处(±2 行内)
PROBE_SRC_PAT = re.compile(r"探针|probe|review_evidence|面数实测|面数探针", re.I)


def _classify(doc: Path) -> str:
    """报告/任务书/附件三分类(_PLAIN 副本归入其主报告类)。"""
    pos = str(doc).lower()
    if "review_evidence" in pos:
        return "aux"
    if BRIEF_NAME_PAT.search(doc.name):
        return "brief"
    return "report"


def _evidence_exists(repo: Path, text: str) -> bool:
    """报告里引用的路径至少一个在磁盘可定位(相对 repo 根)。"""
    for m in EVID_PATH_PAT.finditer(text):
        p = m.group().rstrip(".,;，。;)")
        if (repo / p).exists():
            return True
    return False


def check_probe_doc(repo: Path, doc: Path):
    """核单份探针文档。返回 (n_pass, findings, notes)。"""
    n_pass, findings, notes = 0, [], []
    kind = _classify(doc)
    text = load_text(doc)

    if kind == "aux":
        notes.append(f"{doc.name}: review_evidence 附件,只登记不判")
        return n_pass, findings, notes

    # ①零模型调用声明
    if ZERO_LLM_PAT.search(text):
        n_pass += 1
    else:
        findings.append(finding(doc, 0, "探针文档未见零模型调用声明"
                                "(零模型/零LLM/零API/零网络/零判分/只读探针)"))

    # ②门结论:报告类必须给出过/不过;任务书类尚未执行只附注
    if GATE_CONCL_PAT.search(text):
        n_pass += 1
    elif kind == "report":
        findings.append(finding(doc, 0, "探针报告存在但无通过门结论"
                                "(过/不过/成立/不成立/未过线/结项/撤销 均未出现)"))
    else:
        notes.append(f"{doc.name}: 任务书/立项输入,未见门结论(尚未执行属正常,不判)")

    # ③证据文件引用(报告类必须;任务书类不强制——它引用的是上游而非产物)
    if kind == "report":
        if _evidence_exists(repo, text):
            n_pass += 1
        else:
            findings.append(finding(doc, 0, "探针报告未引用任何磁盘可定位的证据文件"
                                    "(reports|docs|scripts|src 路径)"))

    # 标签(细则5):缺失只附注——历史报告按「原文件不回写」红线不补标
    if kind == "report" and not LABEL_PAT.search(text):
        notes.append(f"{doc.name}: 无「探针≠预注册≠成绩」标签(bible 细则5;"
                     f"历史件不回写,新报告须带)")
    return n_pass, findings, notes


def discover_probe_docs(repo: Path) -> list[Path]:
    """docs/ 下文件名含 probe/探针 的 md(排除 docs/BIBLE/);_PLAIN 副本去重。"""
    out, seen_plain_stems = [], set()
    cands = []
    for p in (repo / "docs").rglob("*.md"):
        if not p.is_file() or "bible" in p.parent.name.lower():
            continue
        if re.search(r"probe|探针", p.name, re.I):
            cands.append(p)
    for p in sorted(cands):
        stem = p.stem
        if stem.lower().endswith(_PLAIN_SUFFIX):
            main_stem = stem[: -len(_PLAIN_SUFFIX)]
            if any(q.stem == main_stem for q in cands):
                seen_plain_stems.add(main_stem)
                continue  # 主报告并存时跳过 PLAIN 副本
        out.append(p)
    return out


def check_plan_files(repo: Path, files: list[Path]):
    """--files 方案 md:增面数字必须带探针出处(±2 行)。"""
    n_pass, findings, notes = 0, [], []
    for f in files:
        lines = load_text(f).splitlines()
        for i, line in enumerate(lines):
            if not CLAIM_NUM_PAT.search(line):
                continue
            ctx = "\n".join(lines[max(0, i - CONTEXT_LINES): i + CONTEXT_LINES + 1])
            if PROBE_SRC_PAT.search(ctx):
                n_pass += 1
            else:
                m = CLAIM_NUM_PAT.search(line)
                findings.append(finding(f, i + 1,
                                 f"增面数字无探针出处(±2 行无 探针/probe/review_evidence/面数实测): {m.group()}"))
        if not any(CLAIM_NUM_PAT.search(l) for l in lines):
            notes.append(f"{f.name}: 无增面数字声明,方案数字检查不适用")
    return n_pass, findings, notes


def run_check(repo: Path, file_specs=None):
    """主检查。返回 emit 所需参数 dict。"""
    print(f"MODE=repo (probe 报告面=docs/, 方案面=--files 或缺省不查)")
    findings, notes = [], []
    files = []
    for spec in file_specs or []:
        p = Path(spec)
        if not p.is_absolute():
            p = repo / p
        if p.is_dir():
            files += sorted(p.rglob("*.md"))
        elif p.is_file():
            files.append(p)
        else:
            files += sorted(repo.glob(spec))
    n_pass = 0

    docs = discover_probe_docs(repo)
    if not docs and not files:
        findings.append(finding(repo / "docs", 0,
                         "未找到任何探针文档(docs/**/*probe*/*探针*)——立项/发车前缺零 LLM 探针报告"))
        return {"status": "fail", "findings": findings,
                "notes": ["MODE=repo", "发现 0 份探针文档"], "n_pass": 0, "n_fail": 1}
    notes.append(f"探针文档 {len(docs)} 份(报告/任务书/附件三分类核)")
    for d in docs[:30]:  # 上限保护
        p, f, nn = check_probe_doc(repo, d)
        n_pass += p
        findings += f
        notes += nn

    if files:
        notes.append(f"--files 方案面: {len(files)} 份,核增面数字探针出处")
        p, f, nn = check_plan_files(repo, files)
        n_pass += p
        findings += f
        notes += nn

    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="probe-before-build 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--files", nargs="*", default=None,
                    help="方案/立项 md(增面数字须带探针出处;可与缺省探针报告检查叠加)")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), args.files)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
