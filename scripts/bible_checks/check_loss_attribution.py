#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loss-attribution 机器检查:失分桶闭合、逐题配对 diff、未评题留分母。

调用:
    python3 scripts/bible_checks/check_loss_attribution.py --repo <repo根> \
        [--batch <批根目录>] [--files <归因md> ...]

- 本地有 metrics/aggregate JSON(reports/**/metrics*.json)就真算:
  ①闭合等式:sum(buckets) == denominator;
  ②未评题留分母:len(per_qid) == denominator 且
    aggregate_diagnosis 单调 0<=H1<=H3<=H5<=U<=denominator;
  ③逐题配对 diff:同组 ≥2 臂(名字 <prefix>_<arm>)按 per_qid 配对,
    真算 改善g/退化l/持平 与换手率,与 main_caliber.hit@1 互核。
- --batch:只核指定批根(臂目录或含臂子目录的父目录)。
- 找不到任何 metrics JSON → 降级:扫 docs/ 归因类 md(文件名含
  diagnosis|recon|attr|triage|归因|对账|result),做结构检查:
  ①A = B + C 闭合等式算术验算(算错 → fail;解析不了跳过计数);
  ②已知计数器(analog_pregate_skipped/992 等)出现在加法 → fail,
  同行带否定/警示词(禁止/数两遍/重复计/负控/不是)豁免;
  ③「净 ±N」结论句 ±2 行内无 改善/退化/持平/换手 → fail。
  摘要首行打印 MODE=degraded;有 JSON 时打印 MODE=metrics-json / real-batch。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "loss-attribution"
CONTEXT_LINES = 2

_ARM_SUFFIX_PAT = re.compile(r"^(?P<prefix>.+)_(?P<arm>[A-Za-z0-9]+)$")
METRIC_NAMES = ("metrics.json", "metrics.v1.json", "metrics.json.v1")

# ---- 降级模式(docs 归因报告)----
# 「净变化」结论句:净 带符号数 / 净回收|净增|净失 N / 净变化|净差 N
# (「净 3 组」这类量词不匹配)
_NET_PAT = re.compile(
    r"净\s*[-+±−]\s*\d+|净(?:回收|增|失)\s*\d+|净(?:变化|差)\s*[-+±−]?\s*\d+")
_GL_PAT = re.compile(
    r"改善|退化|持平|换手|配对|g\s*/\s*l|不是已证|未证|未测|pending|"
    r"不可归因|噪声区间|不能宣称", re.I)
# 已知跨分支计数器(只能出现在闭合等式右侧,禁止与行数/题数相加)
COUNTER_ADD_PAT = re.compile(r"\d[\d,]*\s*[+＋]\s*(?:analog_pregate_skipped|992)\b"
                             r"|(?:analog_pregate_skipped|992)\b\s*[+＋]\s*\d[\d,]*")
_NEGATION_PAT = re.compile(
    r"禁止|不能|不许|不得|不要|勿|严禁|数两遍|重复计|负控|不是|≠|拒绝|自洽", re.I)
# 归因类文档名
DOC_SCAN_PAT = re.compile(r"diagnosis|recon|attr|triage|归因|对账|result", re.I)
OUTOFSCOPE_NAME_PAT = re.compile(r"^TASK_|_REVIEW|REQUEST|CODEX|HANDOFF|SCOUT", re.I)

# 闭合等式解析:
#   段分隔:；;。| 以及换行 —— 同行多等式互不串扰;
#   每段按 '=' 切片,相邻片组成 (L, R);
#   L:整个是算式(num op num…)或以「独立尾数」结尾(尾数前不能是字母/数字/@/./-/+);
#   R:必须是 num (op num)+ 链,且链外残留字符不得再含数字(排除 13-18 这类区间号);
#   op:+ ＋ 任意间距;- 仅带间距时算减号(排除 10-12 批、13-18 区间);−(U+2212)任意间距。
_SEG_SPLIT_PAT = re.compile(r"[；;。|\n]")
_EQ_SPLIT_PAT = re.compile(r"\s*=\s*")
_NUM_PAT = re.compile(r"\d[\d,]*")
# 右侧含加减链才算闭合等式(A = B + C);单个数字的右侧是 kv 赋值(L=14)
_RHAS_CHAIN_PAT = re.compile(r"\d[\d,]*\s*(?:[+＋]|−|\s-\s)\s*\d")
_LHS_TAIL_REJECT = tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@./-+＋−")


def _parse_sum(text: str):
    """把 text 解析为 num (op num)* 算式并求值(从首个数字起)。
    先剥全角括号注释(178（F3）+ 407 → 178 + 407)。
    返回 (value, ambiguous):ambiguous=True 表示链外残留字符仍含数字
    (如区间号 13-18),整条等式按歧义弃用;text 无数字 → (None, ...)。"""
    text = re.sub(r"（[^（）]*）", "", text)
    m = _NUM_PAT.search(text)
    if m is None:
        return None, bool(any(c.isdigit() for c in text))
    total = _n(m.group())
    pos = m.end()
    while True:
        k = pos
        while k < len(text) and text[k] in " \t":
            k += 1
        mop = re.match(r"[+＋]|−|-", text[k:])
        if not mop:
            break
        op = mop.group()
        j = k + 1
        if op == "-":
            left_ws = k > pos  # 数字与 '-' 之间有空白
            right_ws = j < len(text) and text[j] in " \t"
            if not (left_ws and right_ws):
                break  # 紧贴的 ASCII '-' 视为区间号(13-18、10-12 批),停止解析
        while j < len(text) and text[j] in " \t":
            j += 1
        n2 = _NUM_PAT.match(text, j)
        if not n2:
            break
        total += _n(n2.group()) if op in ("+", "＋") else -_n(n2.group())
        pos = n2.end()
    leftover = text[pos:]
    return total, bool(any(c.isdigit() for c in leftover))


def _lhs_value(left: str):
    """LHS 取值,两条路:
    1. 以数字/符号开头(可选负号)的完整算式 → _parse_sum 求值(残留含数字则弃用);
    2. 以「独立尾数」结尾(尾数前不能是字母/数字/@/./斜杠/运算符)→ 取尾数。
    否则 None(计 skipped)。"""
    left = left.strip()
    if not left:
        return None
    if re.match(r"[-−]?\d", left):
        v, amb = _parse_sum(left)
        if v is not None and not amb:
            return v
    m = re.search(r"(\d[\d,]*)$", left)
    if m and (m.start() == 0 or left[m.start() - 1] not in _LHS_TAIL_REJECT):
        return _n(m.group(1))
    return None


def _eval_equations(lines: list[str]):
    """抽闭合等式并验算(段级解析,同行多等式互不串扰)。
    只有「右侧含加减链」的对才当闭合等式验算;右侧单个数字的
    (L=14、G=8 这类 kv 列表)不是闭合等式,静默忽略。
    返回 (checked, bad[(line, msg)], skipped)。"""
    checked, bad, skipped = 0, [], 0
    for lineno, line in enumerate(lines, 1):
        for seg in _SEG_SPLIT_PAT.split(line):
            parts = _EQ_SPLIT_PAT.split(seg)
            if len(parts) < 2:
                continue
            for j in range(len(parts) - 1):
                rhs_raw = parts[j + 1]
                if not _RHAS_CHAIN_PAT.search(rhs_raw):
                    continue  # kv 赋值(L=14),非闭合等式
                lhs = _lhs_value(parts[j])
                if lhs is None:
                    skipped += 1
                    continue
                rhs, ambiguous = _parse_sum(rhs_raw)
                if rhs is None:
                    skipped += 1
                    continue
                if ambiguous:  # 右侧有未消费数字(区间号等),按歧义弃用
                    skipped += 1
                    continue
                checked += 1
                if lhs != rhs:
                    bad.append((lineno, f"{lhs} ≠ 右侧合计 {rhs}"))
    return checked, bad, skipped


def _load_json(path: Path):
    try:
        return json.loads(load_text(path))
    except (ValueError, OSError):
        return None


def _n(s: str) -> int:
    return int(s.replace(",", ""))


def _hit1(entry: dict) -> bool:
    """per_qid 条目的 hit@1:main.rank == 1(与判分口径一致)。"""
    main = entry.get("main") or {}
    return main.get("rank") == 1


def check_metrics_file(path: Path):
    """核单个 metrics JSON:闭合 + 分母保持 + 单调性。返回 (n_pass, findings, notes)。"""
    n_pass, findings, notes = 0, [], []
    d = _load_json(path)
    if not isinstance(d, dict):
        return 0, [finding(path, 0, "metrics JSON 解析失败")], notes
    den, buckets = d.get("denominator"), d.get("buckets")
    if isinstance(den, int) and isinstance(buckets, dict) and buckets:
        total = sum(v for v in buckets.values() if isinstance(v, (int, float)))
        if total == den:
            n_pass += 1
            notes.append(f"{path.parent.name}: 桶闭合通过 {total}={'+'.join(str(v) for v in buckets.values())}")
        else:
            findings.append(finding(path, 0,
                             f"桶闭合失败: 桶合计 {total} ≠ 分母 {den} "
                             f"(桶={ {k: v for k, v in buckets.items()} })"))
    else:
        notes.append(f"{path.parent.name}: 无 denominator+buckets,闭合核不适用")

    per = d.get("per_qid")
    if isinstance(den, int) and isinstance(per, list):
        if len(per) == den:
            n_pass += 1
        else:
            findings.append(finding(path, 0,
                             f"未评题疑似被丢出分母: per_qid 行数 {len(per)} ≠ denominator {den}"))
    # 聚合诊断单调性(0<=H1<=H3<=H5<=U<=denominator)
    agg = d.get("aggregate_diagnosis")
    if isinstance(agg, dict):
        chain = [agg.get(k) for k in ("H1", "H3", "H5", "U_strict_matched_questions")]
        nums = [v for v in chain if isinstance(v, (int, float))]
        if len(nums) == 4 and isinstance(den, int):
            seq = [0] + nums + [den]
            if all(a <= b for a, b in zip(seq, seq[1:])):
                n_pass += 1
            else:
                findings.append(finding(path, 0,
                                 f"聚合诊断单调性破坏: H1={chain[0]} H3={chain[1]} "
                                 f"H5={chain[2]} U={chain[3]} den={den}"))
    return n_pass, findings, notes


def paired_diff(arms: list[Path]):
    """同组 ≥2 臂按 qid 配对,真算 g/l/持平与换手率。返回 (n_pass, findings, notes)。"""
    notes = []
    if len(arms) < 2:
        return 0, [], notes
    tables = {}
    for a in arms[:2]:  # 主配对取排序前两臂
        d = _load_json(a / "metrics.json")
        per = d.get("per_qid") if isinstance(d, dict) else None
        if isinstance(per, list):
            tables[a.name] = {e.get("qid"): _hit1(e)
                              for e in per if isinstance(e, dict) and e.get("qid")}
    if len(tables) < 2:
        notes.append("配对 diff: 可用 per_qid 不足两臂,跳过(记 unknown)")
        return 0, [], notes
    (na, ta), (nb, tb) = list(tables.items())[0], list(tables.items())[1]
    common = set(ta) & set(tb)
    if not common:
        notes.append("配对 diff: 两臂无共同 qid,跳过(记 unknown)")
        return 0, [], notes
    g = sum(1 for q in common if tb[q] and not ta[q])   # B 对 A 改善
    l = sum(1 for q in common if ta[q] and not tb[q])   # A 对 B 改善 = B 退化
    tie = len(common) - g - l
    rate = (g + l) / len(common) * 100
    notes.append(f"配对 diff({na} vs {nb}, n={len(common)}): "
                 f"改善 {g} / 退化 {l} / 持平 {tie};换手 {g + l}({rate:.1f}%)")
    # 与 main_caliber.hit@1 差值互核(能核就算过)
    d0 = _load_json(arms[0] / "metrics.json") or {}
    d1 = _load_json(arms[1] / "metrics.json") or {}
    h0 = (d0.get("main_caliber") or {}).get("hit@1")
    h1 = (d1.get("main_caliber") or {}).get("hit@1")
    if isinstance(h0, int) and isinstance(h1, int) and h1 - h0 == g - l:
        return 1, [], notes
    if isinstance(h0, int) and isinstance(h1, int):
        return 0, [finding(arms[1] / "metrics.json", 0,
                   f"配对 diff(g-l={g - l})与 hit@1 差值({h1}-{h0}={h1 - h0})不符;"
                   f"两臂口径可能不一致")], notes
    return 0, [], notes


def group_arms(roots: list[Path]) -> dict:
    """按 <prefix>_<arm> 分组臂目录。"""
    groups = {}
    for r in roots:
        m = _ARM_SUFFIX_PAT.match(r.name)
        key = m.group("prefix") if m else r.name
        groups.setdefault(key, []).append(r)
    return groups


def check_batch(repo: Path, batch: Path):
    """--batch 真核:闭合+分母+配对。"""
    print(f"MODE=real-batch (batch={batch})")
    findings, notes, n_pass = [], [], 0
    if not batch.is_dir():
        return {"status": "error", "findings": [finding(batch, 0, "批根目录不存在")],
                "notes": [], "n_pass": 0, "n_fail": 0}

    def has_m(d: Path) -> bool:
        return any((d / n).is_file() for n in METRIC_NAMES)

    roots = [batch] if has_m(batch) else \
        [d for d in sorted(batch.iterdir()) if d.is_dir() and has_m(d)]
    if not roots:
        return {"status": "error",
                "findings": [finding(batch, 0, f"批根内未发现 metrics JSON({', '.join(METRIC_NAMES)})")],
                "notes": [], "n_pass": 0, "n_fail": 0}
    for r in roots:
        p, f, nn = check_metrics_file(r / "metrics.json")
        n_pass += p
        findings += f
        notes += nn
    p, f, nn = paired_diff(roots)
    n_pass += p
    findings += f
    notes += nn
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def discover_metric_dirs(repo: Path) -> list[Path]:
    """reports 下含 metrics JSON 的目录(两三层深,跳过 synced 细目)。"""
    out, seen = [], set()
    reports = repo / "reports"
    if not reports.is_dir():
        return out
    for depth in (1, 2, 3):
        for pat in METRIC_NAMES:
            for p in reports.glob(f"{'*/' * depth}{pat}"):
                if p.is_file() and p.parent.resolve() not in seen:
                    seen.add(p.parent.resolve())
                    out.append(p.parent)
    return sorted(out, key=lambda p: str(p))


# ---- 降级:docs 归因报告结构检查 ----
# (_eval_equations 的段级实现在上方常量区之后)

def check_doc(repo: Path, doc: Path):
    """降级:核单份归因报告结构。返回 (n_pass, findings, notes)。"""
    n_pass, findings, notes = 0, [], []
    text = load_text(doc)
    lines = text.splitlines()

    # ①闭合等式算术验算
    checked, bad, skipped = _eval_equations(lines)
    if checked:
        if bad:
            for ln, msg in bad[:8]:
                findings.append(finding(doc, ln, f"闭合等式算术不符: {msg}"))
        else:
            n_pass += 1
            notes.append(f"{doc.name}: {checked} 条闭合等式全部验算通过")
        if skipped:
            notes.append(f"{doc.name}: {skipped} 处等式无法解析/有歧义,跳过不计")
    elif re.search(r"分桶|失分桶|桶表|分母", text):
        # 表格型闭合(A→B 去向表)机器难普适解析,转人工清单项,附注不判 fail
        notes.append(f"{doc.name}: 谈分桶/分母但无可验算的 A = B + C 等式"
                     "(表格型闭合请人工走 bible §5 清单第 1 条)")

    # ②计数器进加法(992/analog_pregate_skipped),否定/警示语境豁免
    for i, line in enumerate(lines):
        if COUNTER_ADD_PAT.search(line) and not _NEGATION_PAT.search(line):
            findings.append(finding(doc, i + 1,
                             "跨分支计数器(992/analog_pregate_skipped)出现在加法里"
                             "(重叠计数;P3 O0 口径:禁止与候选行数相加)"))

    # ③净 ±N 结论句须配 g/l(±2 行),否定语境豁免
    for i, line in enumerate(lines):
        m = _NET_PAT.search(line)
        if not m:
            continue
        if _NEGATION_PAT.search(line):
            continue
        ctx = "\n".join(lines[max(0, i - CONTEXT_LINES): i + CONTEXT_LINES + 1])
        if not _GL_PAT.search(ctx):
            findings.append(finding(doc, i + 1,
                             f"「净变化」结论句无配套 改善/退化/持平/换手 数: {m.group()}"))
    return n_pass, findings, notes


def run_check(repo: Path, batch: Path | None, file_specs=None):
    """主检查。返回 emit 所需参数 dict。"""
    findings, notes, n_pass = [], [], 0

    if batch is not None:
        r = check_batch(repo, batch)
        return r

    roots = discover_metric_dirs(repo)
    if roots:
        print(f"MODE=metrics-json ({len(roots)} 个 metrics 目录真算闭合)")
        notes.insert(0, f"MODE=metrics-json: {len(roots)} 个 metrics 目录真算闭合/分母/配对")
        groups = group_arms(roots)
        paired_done = False
        for gname, arms in sorted(groups.items()):
            if len(arms) >= 2 and not paired_done:
                p, f, nn = paired_diff(sorted(arms, key=lambda x: x.name))
                n_pass += p
                findings += f
                notes += nn
                paired_done = True  # 每组代表配对一次即可;真核请用 --batch 指定组
        for r in roots:
            p, f, nn = check_metrics_file(r / "metrics.json")
            n_pass += p
            findings += f
            notes += nn
    else:
        print("MODE=degraded (本地无 metrics JSON,对 docs/ 归因报告做结构检查)")
        notes.insert(0, "MODE=degraded: 无本地 metrics JSON,仅 docs 结构检查;真算请等批根/传 --batch")

    # docs 归因报告结构检查(始终做;degraded 时是主检查)
    docs = [p for p in sorted((repo / "docs").glob("*.md"))
            if DOC_SCAN_PAT.search(p.name)] if (repo / "docs").is_dir() else []
    if file_specs:
        for spec in file_specs:
            p = Path(spec) if Path(spec).is_absolute() else repo / spec
            hits = [p] if p.is_file() else [q for q in repo.glob(spec) if q.is_file()]
            docs += [q for q in hits if q not in docs]
    # 范围过滤:任务书/评审/请求/交接件不是归因报告;_PLAIN 副本随主报告
    kept = []
    for d in docs:
        if OUTOFSCOPE_NAME_PAT.search(d.name):
            continue
        m = re.search(r"_plain(?=_|$|_\d)", d.stem.lower())
        if m:  # 中缀/后缀式 PLAIN 副本(CHAIN14_..._PLAIN / CHAIN13_..._PLAIN_2026-10-15)
            main_stem = d.stem[: m.start()] + d.stem[m.end():]
            if any(q.stem == main_stem for q in docs):
                continue
        kept.append(d)
    docs = kept
    if docs:
        notes.append(f"docs 归因报告结构检查 {len(docs)} 份")
    for d in docs[:40]:  # 上限保护
        p, f, nn = check_doc(repo, d)
        n_pass += p
        findings += f
        notes += nn

    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="loss-attribution 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--batch", default=None, help="批根目录(臂目录或含臂子目录的父目录)")
    ap.add_argument("--files", nargs="*", default=None, help="追加要核的归因 md")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), Path(args.batch) if args.batch else None, args.files)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
