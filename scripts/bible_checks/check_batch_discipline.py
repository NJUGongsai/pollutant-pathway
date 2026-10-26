#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch-discipline 机器检查:单变量成臂、同批对照、事后标签。

调用:
    python3 scripts/bible_checks/check_batch_discipline.py --repo <repo根> \
        [--batch <批根目录>] [--strict] [--files <md> ...]

- --batch:批根=含 metrics.json/orchestration.json 的臂目录(自动找同前缀兄弟臂)
  或含多个臂子目录的父目录。真核三件事:
  ①对照臂:≥2 臂才成立,单臂 → finding(T-H r2 教训);
  ②两臂参数 diff:对 orchestration.json 顶层键做归一化 diff(剔除时间戳键、
  把臂名变体替换为占位符),剩余差分键须恰为 1 个(单变量);>1 → finding;
  =0 → 附注(变量不在批根参数面,如模型/env,人工核对发车书);
  ③批量声明:metrics.json denominator 与 per_qid 行数互核;seed 声明:批根任一
  JSON 带 seed 键 → pass,缺失 → 附注(付费批采样无 seed 属现状,--strict 才判)。
- 缺省 --batch:降级扫 docs/ 发车书/批次报告(文件名含 launch|rebatch|双臂|_ab_|result),
  核:单变量/对照声明、多变量须配「不可归因」声明、跨批效应句 ±2 行内须有
  置信区间/换手/降级声明之一(bible §6)、批量(298/分母/denominator)声明、
  post-hoc 标签(result 类文档;历史件缺失只附注,--strict 才判)。
  摘要首行打印 MODE=degraded。

首行恒打印 MODE 行(real-batch / repo+local-roots / degraded)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "batch-discipline"
CONTEXT_LINES = 2

# 时间戳类键:两臂必然不同但非实验变量
_TS_KEY_PAT = re.compile(r"_at$|timestamp|_time$", re.I)
# 臂名后缀 token(成臂命名约定:<prefix>_<arm>)
_ARM_SUFFIX_PAT = re.compile(r"^(?P<prefix>.+)_(?P<arm>[A-Za-z0-9]+)$")

# ---- 降级模式(docs 发车书/批次报告)----
VAR_DECL_PAT = re.compile(
    r"单变量|唯一变量|唯一差分|唯一差异|单差分|差分变量|对照臂|同批对照|双臂|两臂|"
    r"A\s*/\s*B|[AB]\s*臂|单臂", re.I)
MULTI_VAR_PAT = re.compile(r"多变量|一起变|变量叠加|四变量|混批|多变量混批", re.I)
NOATTRIB_PAT = re.compile(
    r"不可归因|不得称单变量|不能称单变量|不得单变量归因|无法归因|不宣称单变量|"
    r"不作因果|不做因果|不作归因|只作参照|非因果", re.I)
# 跨批效应句(「净」前是 干/洁 时是「干净 N」子串,非净变化;其余 CJK 前字放行)
EFFECT_PAT = re.compile(
    r"(?<![干洁])净\s*[-+±−]?\d|(?:高|低)出\s*\d|提升\s*\d+|净增|净失|净回收|净差")
# 门/停点声明与判线句不是效应主张(预注册里写死的推进/止损线、未达线判词)
GATE_LINE_PAT = re.compile(r"停点|止损|推进线|判定线|预注册线|未达|不设门|[≤≥]")
SUPPORT_PAT = re.compile(
    r"置信区间|bootstrap|\bCI\b|换手|改善|退化|持平|配对|不可归因|噪声区间|"
    r"不能宣称|无法归因|不宣称|不能证明|没有同批|无同批|同量级", re.I)
BATCHSIZE_PAT = re.compile(
    r"298\s*[题条分/]|298\s*=|分母|denominator|n_total|批量|题集|full 段|full 298", re.I)
SEED_PAT = re.compile(r"\bseed\b|种子", re.I)
POSTHOC_PAT = re.compile(r"post-hoc|posthoc|事后", re.I)
RESULT_NAME_PAT = re.compile(r"result|结果", re.I)
DOC_SCAN_PAT = re.compile(r"launch|relaunch|rebatch|发车|双臂|两臂|_ab_|result", re.I)
# 评审/请求/交接件不是发车书或批次报告,纪律声明在正件里(不在本检查范围)
OUTOFSCOPE_NAME_PAT = re.compile(r"_REVIEW|REQUEST|CODEX|HANDOFF|SCOUT", re.I)
# 纯运营执行记录(部署/环境检查/正负控)不产生成绩,无需批次设计声明
OPS_EXEMPT_PAT = re.compile(r"不产生真实题成绩|只做部署|合成正负控")
# 成臂/批次对比语境(单变量/批量检查只对这类文档生效)
BATCHNESS_PAT = re.compile(r"臂|A/B|batch_tag|批根|成臂")


def _load_json(path: Path):
    try:
        return json.loads(load_text(path))
    except (ValueError, OSError):
        return None


def _norm_arm_strings(obj, variants: list[str]):
    """递归把字符串里的臂名变体替换为 «arm» 占位(runs_root 等身份路径非变量)。"""
    if isinstance(obj, str):
        s = obj
        for v in variants:
            s = s.replace(v, "«arm»")
        return s
    if isinstance(obj, dict):
        return {k: _norm_arm_strings(v, variants) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_norm_arm_strings(v, variants) for v in obj]
    return obj


def _arm_variants(arm: Path) -> list[str]:
    """臂目录名的身份变体:chain14_a → [chain14_a, chain14a]。"""
    name = arm.name
    out = {name, name.replace("_", "")}
    m = _ARM_SUFFIX_PAT.match(name)
    if m:  # 共同前缀+单臂字母:chain14a / chain14b 这类无下划线写法
        pre, arm = m.group("prefix"), m.group("arm")
        if len(arm) <= 8:
            out.add(f"{pre}{arm}")
    return sorted(out)


def discover_arms(batch: Path) -> list[Path]:
    """臂目录:batch 自身含 metrics/orchestration → [batch + 同前缀兄弟臂];
    否则取含 metrics.json 或 orchestration.json 的子目录。"""
    def has_markers(d: Path) -> bool:
        return (d / "metrics.json").is_file() or (d / "orchestration.json").is_file()
    if has_markers(batch):
        arms = [batch]
        m = _ARM_SUFFIX_PAT.match(batch.name)
        if m and batch.parent.is_dir():  # 同前缀兄弟臂(chain14_a → chain14_b)
            prefix = m.group("prefix")
            for d in sorted(batch.parent.iterdir()):
                if not d.is_dir() or d == batch or not has_markers(d):
                    continue
                dm = _ARM_SUFFIX_PAT.match(d.name)
                if dm and dm.group("prefix") == prefix:
                    arms.append(d)
        return arms
    if batch.is_dir():
        arms = [d for d in sorted(batch.iterdir()) if d.is_dir() and has_markers(d)]
        if arms:
            return arms
    return []


def check_param_diff(arms: list[Path]):
    """两臂 orchestration.json 归一化 diff。返回 (n_pass, n_fail, findings, notes, var_keys)。"""
    findings, notes = [], []
    orchs = {}
    for a in arms:
        o = _load_json(a / "orchestration.json")
        if o is not None:
            orchs[a.name] = o
    if len(orchs) < 2:
        notes.append("参数 diff: orchestration.json 不足两臂,无法实核(记 unknown)")
        return 0, 0, findings, notes, []
    names = sorted(orchs)
    by_name = {a.name: a for a in arms}
    variants = []
    for n in names:
        variants += _arm_variants(by_name[n])
    keys = set(orchs[names[0]]) | set(orchs[names[1]])
    diff = []
    for k in sorted(keys):
        if _TS_KEY_PAT.search(k):
            continue
        v0 = _norm_arm_strings(orchs[names[0]].get(k), variants)
        v1 = _norm_arm_strings(orchs[names[1]].get(k), variants)
        if v0 != v1:
            diff.append(k)
    if len(diff) == 1:
        notes.append(f"两臂参数 diff 恰 1 个变量: {diff[0]}(单变量实核通过)")
        return 1, 0, findings, notes, diff
    if not diff:
        notes.append("两臂参数面零差分:变量不在批根参数内(如模型/env),须人工核对发车书")
        return 0, 0, findings, notes, diff
    findings.append(finding(arms[0] / "orchestration.json", 0,
                     f"两臂参数 diff 含 {len(diff)} 个字段,超出单变量: {', '.join(diff)}"))
    return 0, 1, findings, notes, diff


def check_batch_root(repo: Path, batch: Path, strict: bool):
    """--batch 真核。返回 emit 参数 dict。"""
    print(f"MODE=real-batch (batch={batch})")
    findings, notes, n_pass = [], [], 0
    if not batch.is_dir():
        return {"status": "error", "findings": [finding(batch, 0, "批根目录不存在")],
                "notes": [], "n_pass": 0, "n_fail": 0}
    arms = discover_arms(batch)
    if not arms:
        return {"status": "error", "findings": [finding(batch, 0,
                "批根内未发现臂目录(需 metrics.json 或 orchestration.json)")],
                "notes": [], "n_pass": 0, "n_fail": 0}
    notes.append(f"发现 {len(arms)} 臂: {', '.join(a.name for a in arms)}")

    # ①对照臂
    if len(arms) >= 2:
        n_pass += 1
    else:
        findings.append(finding(batch, 0, "批根只见 1 臂,无同批对照臂"
                                "(效应与批次噪声不可分;T-H r2 教训)"))

    # ②两臂参数 diff 单变量实核
    p, _nf, f, nn, _vk = check_param_diff(arms)
    n_pass += p
    findings += f
    notes += nn

    # ③批量声明 + seed
    den_seen, seed_seen = False, False
    for a in arms:
        m = _load_json(a / "metrics.json")
        if isinstance(m, dict):
            den = m.get("denominator")
            per = m.get("per_qid")
            if isinstance(den, int):
                den_seen = True
                if isinstance(per, list) and len(per) != den:
                    findings.append(finding(a / "metrics.json", 0,
                                     f"per_qid 行数 {len(per)} ≠ denominator {den}(未评题疑似被丢出分母)"))
            if "seed" in m:
                seed_seen = True
        o = _load_json(a / "orchestration.json") or {}
        br = _load_json(a / "batch_report.json") or {}
        if "seed" in o or "seed" in br:
            seed_seen = True
        if isinstance(br, dict) and isinstance(br.get("n_total"), int):
            den_seen = True
    if den_seen:
        n_pass += 1
    else:
        findings.append(finding(batch, 0, "批根未见批量声明(metrics denominator / batch n_total 均缺)"))
    if seed_seen:
        n_pass += 1
    elif strict:
        findings.append(finding(batch, 0, "批根未见 seed 声明(--strict)"))
    else:
        notes.append("seed: 批根未见 seed 键(付费批采样无 seed 属现状;登记待补纪律,不判 fail)")

    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def check_doc(repo: Path, doc: Path, strict: bool):
    """降级:核单份发车书/批次报告。返回 (n_pass, findings, notes)。"""
    n_pass, findings, notes = 0, [], []
    text = load_text(doc)
    lines = text.splitlines()

    if OPS_EXEMPT_PAT.search(text[:2000]):
        notes.append(f"{doc.name}: 纯运营执行记录(不产生真实题成绩),批次设计面不适用")
        return n_pass, findings, notes
    batchy = bool(BATCHNESS_PAT.search(text))
    is_task = doc.name.upper().startswith("TASK_")

    # ①单变量/对照声明(仅成臂/批次对比语境;非批次文档跳过不判)
    if not batchy:
        notes.append(f"{doc.name}: 非成臂/批次对比文档,单变量/批量面不适用")
    elif VAR_DECL_PAT.search(text):
        n_pass += 1
    else:
        findings.append(finding(doc, 0, "未见单变量/对照臂声明"
                                "(单变量|唯一差异|对照臂|双臂|两臂|单臂 均未出现)"))
    # ②多变量须配不可归因/不作因果声明
    if MULTI_VAR_PAT.search(text) and not NOATTRIB_PAT.search(text):
        findings.append(finding(doc, 0, "声明了多变量合并但无「不可归因/不作因果」降级声明"))

    # ③跨批效应句须有支撑(置信区间/换手/配对/降级之一,±2 行);
    #   门/停点声明与判线句不是效应主张,豁免
    for i, line in enumerate(lines):
        if not EFFECT_PAT.search(line) or GATE_LINE_PAT.search(line):
            continue
        ctx = "\n".join(lines[max(0, i - CONTEXT_LINES): i + CONTEXT_LINES + 1])
        if not SUPPORT_PAT.search(ctx):
            findings.append(finding(doc, i + 1,
                             f"跨批效应句无区间/换手/降级声明支撑: {line.strip()[:60]}"))

    # ④批量声明(任务书缺省附注——批量冻结在预注册,由 prereg-first 核)
    if batchy:
        if BATCHSIZE_PAT.search(text):
            n_pass += 1
        elif is_task and not strict:
            notes.append(f"{doc.name}: 任务书未见批量声明(批量冻结在预注册,不判 fail)")
        else:
            findings.append(finding(doc, 0, "未见批量/分母声明(298 题/条/分母|denominator|n_total|批量|题集)"))

    # ⑤seed:缺省附注,--strict 判违规
    if SEED_PAT.search(text):
        n_pass += 1
    elif strict:
        findings.append(finding(doc, 0, "未见 seed/种子声明(--strict)"))
    else:
        notes.append(f"{doc.name}: 未见 seed 声明(登记待补,不判 fail)")

    # ⑥post-hoc 标签:仅 result/结果 类文档;历史件缺省附注,--strict 判违规
    if RESULT_NAME_PAT.search(doc.name):
        if POSTHOC_PAT.search(text):
            n_pass += 1
        elif strict:
            findings.append(finding(doc, 0, "结果报告缺 post-hoc/事后标签(--strict)"))
        else:
            notes.append(f"{doc.name}: 缺 post-hoc/事后标签(历史件待补,不判 fail)")
    return n_pass, findings, notes


def dedupe_docs(docs: list[Path]) -> list[Path]:
    """范围过滤与去重,返回保留列表:
    - 评审/请求/交接件(CODEX/REVIEW/REQUEST/HANDOFF/SCOUT)不在范围,纪律在正件;
    - _PLAIN 副本(后缀或中缀式)在主报告并存时跳过。"""
    keep = []
    for d in docs:
        if OUTOFSCOPE_NAME_PAT.search(d.name):
            continue
        m = re.search(r"_plain(?=_|$|_\d)", d.stem.lower())
        if m:
            main_stem = d.stem[: m.start()] + d.stem[m.end():]
            if any(q.stem == main_stem for q in docs):
                continue  # 主报告并存,PLAIN 副本不重复判
        keep.append(d)
    return keep


def discover_local_roots(repo: Path) -> list[Path]:
    """本地批根自动发现:reports/**/orchestration.json 所在目录(深度有限)。"""
    roots = []
    reports = repo / "reports"
    if reports.is_dir():
        for p in sorted(reports.glob(f"{'*/' * 3}orchestration.json")):
            if p.is_file():
                roots.append(p.parent)
    return roots


def run_check(repo: Path, batch: Path | None, strict=False, file_specs=None):
    """主检查。返回 emit 所需参数 dict。"""
    findings, notes, n_pass = [], [], 0

    if batch is not None:
        r = check_batch_root(repo, batch, strict)
        findings += r["findings"]
        notes += r["notes"]
        n_pass += r["n_pass"]
        return {"status": "fail" if findings else "pass", "findings": findings,
                "notes": notes, "n_pass": n_pass, "n_fail": len(findings)}

    # 缺省:本地批根实核(能找到就真核) + docs 发车书降级面
    local_roots = discover_local_roots(repo)
    docs = [p for p in sorted((repo / "docs").glob("*.md"))
            if DOC_SCAN_PAT.search(p.name)] if (repo / "docs").is_dir() else []
    if file_specs:
        extra = []
        for spec in file_specs:
            p = Path(spec) if Path(spec).is_absolute() else repo / spec
            if p.is_file():
                extra.append(p)
            else:
                extra += [q for q in repo.glob(spec) if q.is_file()]
        docs += [d for d in extra if d not in docs]
    docs = dedupe_docs(docs)

    if not local_roots:
        print("MODE=degraded (无本地批根,扫 docs/ 发车书/批次报告)")
        notes.insert(0, "MODE=degraded: 无本地批根,仅 docs 结构检查;真核请传 --batch <批根>")
    else:
        print(f"MODE=repo+local-roots ({len(local_roots)} 本地批根 + {len(docs)} docs)")
        notes.insert(0, f"MODE=repo+local-roots: 本地批根 {len(local_roots)} 个实核 + docs {len(docs)} 份")

    seen_groups = set()
    for root in local_roots[:12]:  # 上限保护
        arms = discover_arms(root)
        if len(arms) < 2:
            continue  # 单文件批根留给 --batch;缺省只核成臂组,避免误伤孤件
        m = _ARM_SUFFIX_PAT.match(root.name)
        gkey = m.group("prefix") if m else root.name
        if gkey in seen_groups:
            continue
        seen_groups.add(gkey)
        p, _nf, f, nn, _vk = check_param_diff(arms)
        n_pass += p
        findings += f
        notes += nn
        for a in arms:  # 批量互核:per_qid 行数 == denominator(未评题留在分母)
            mm = _load_json(a / "metrics.json")
            if isinstance(mm, dict) and isinstance(mm.get("denominator"), int):
                n_pass += 1
                per = mm.get("per_qid")
                if isinstance(per, list) and len(per) != mm["denominator"]:
                    findings.append(finding(a / "metrics.json", 0,
                                     f"per_qid 行数 {len(per)} ≠ denominator {mm['denominator']}(未评题疑似被丢出分母)"))

    if not docs:
        notes.append("docs/ 未发现发车书/批次报告(launch|rebatch|双臂|_ab_|result)")
    for d in docs[:40]:  # 上限保护
        p, f, nn = check_doc(repo, d, strict)
        n_pass += p
        findings += f
        notes += nn

    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="batch-discipline 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--batch", default=None, help="批根目录(臂目录或含臂子目录的父目录)")
    ap.add_argument("--strict", action="store_true",
                    help="seed/post-hoc 缺失也判违规(缺省历史件只附注)")
    ap.add_argument("--files", nargs="*", default=None, help="追加要核的 docs md")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), Path(args.batch) if args.batch else None,
                  args.strict, args.files)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
