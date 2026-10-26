#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stop-loss-gate 机器检查:未达线强制回查、不虚宣有效。

调用:
    python3 scripts/bible_checks/check_stop_loss_gate.py --repo <repo根> [--batch <批根>]

- 给了 --batch(MODE=batch):批根真核。判定线/实测优先读 metrics.json
  (main_caliber.hit@K 与 pass_lines),其次解析批根 report md 的
  <N%/<N题/≥N/N–M% 阈值与 hit@K/分数/实测读数;未达线时先在批根 md 找
  回查记录,找不到再按批 tag(orchestration.json runs_root basename 等)
  去 docs/ 结果报告里找(回查/配对/逐桶/净增/换手);未达线且无回查 →
  fail;未达线且出现未加否定的「修复有效/达标」类宣称句 → fail
  (finding 带「需人工复核」标注)。
- 没给 --batch(MODE=degraded):扫 docs/ 里 RESULT/REPORT 类结果报告,
  含判定线关键词的才进入判定,同一套解析与判定逻辑。

检查项(每份有判定线的结果报告):
1. 判定线数值可解析;2. 实测值可解析;3. 未达线时有回查记录;
4. 未达线时无未加否定的宣称句(命中即标「需人工复核」)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text  # noqa: E402

CHECK = "stop-loss-gate"
MAX_DOCS = 60  # 降级模式扫描文档数上限

# 文档"有判定线"的资格关键词(命中才进入阈值/实测解析)
GATE_MARK_PAT = re.compile(
    r"判定线|达标线|回查线|推进线|停点|强制回查|通过线|pass_line|预注册线")
# 阈值形态:<32% / <96 题(回查触发线);≥5 题 / ≥32% / ≥ 116(目标线,含表格 ≥ N)
THRESH_LT_PAT = re.compile(r"[<＜]\s*(\d+(?:\.\d+)?)\s*(%|题)")
THRESH_GE_PAT = re.compile(r"[≥≧]\s*(\d+(?:\.\d+)?)(%|题)?")
# 目标区间:35–40%(达标需 ≥ 下沿)
THRESH_RANGE_PAT = re.compile(
    r"(?<![\d.])(\d{1,3}(?:\.\d+)?)\s*[-–—~]\s*(\d{1,3}(?:\.\d+)?)\s*%(?!\d)")
# 净失/上限型停点:净失 ≤−3(可识别但读数不做自动比对,转人工复核;
# 只认同行带 净失/净增/上限/池 语境的 ≤N,避免把普通「≤0 failed」当判定线)
THRESH_LE_PAT = re.compile(r"[≤≦]\s*[−-]?\s*(\d+(?:\.\d+)?)\s*(?:%|题)?")
LE_CONTEXT_PAT = re.compile(r"净失|净增|上限|毛空间|池")
# 判定线资格的强措辞(「判定线数值不可解析」finding 只由这些触发;
# 泛词「停点/通过线」单独出现不算,避免实现报告误入)
GATE_MARK_STRICT_PAT = re.compile(r"判定线|达标线|回查线|强制回查|预注册线")
# 实测读数(逐行打分取最优,避免把 298/298 完成率或判定线行数字当成读数):
MEAS_HIT_PAT = re.compile(r"hit@1([^0-9\n]{0,24}?)(\d{1,3})(?![\d/])")
MEAS_FRAC_PAT = re.compile(r"(?<![\d/.])(\d{1,3})/(\d{2,3})(?![\d/.])")
MEAS_EQ_PAT = re.compile(r"(?:v[12]|实测|headline)([^0-9\n]{0,12})[=＝]([^0-9\n]{0,6})(\d{1,3})(?!\d)")
MEAS_PCT_PAT = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d+)?)%(?!\d)")
MEAS_KEYWORD_PAT = re.compile(r"hit@1|命中|headline|实测|本批|v1|v2", re.I)
_THRESH_BEFORE = re.compile(r"[<＜≥≧>＞]\s*$")


def _not_threshold_context(line: str, pos: int) -> bool:
    """数字前的紧邻文本不含比较符(≥/<),即非判定线数字。"""
    return _THRESH_BEFORE.search(line[:pos]) is None
# 回查记录关键词(配对 diff / 净增益 / 换手;含「净 +N」「5 进 4 出」实况写法)
RECHECK_PAT = re.compile(
    r"回查|配对|逐桶|净增|净失|净负|换手|净\s*[+±−-]\s*\d|进\s*\d+\s*出|"
    r"改善.{0,6}退化|paired", re.I)
# 宣称有效关键词(未达线时出现需人工复核)
CLAIM_PAT = re.compile(
    r"修复有效|宣称有效|有效兑现|成功回收|有效回收|已达标|已达成|效果显著|显著提升"
    r"|带来了?.{0,16}(?:提升|增益|收益)"
    r"|(?:净增|增益|收益)[^0-9\n]{0,6}\d+[^0-9\n]{0,6}(?:显著|明显|有效)")
# 否定/降级守卫(当前行或上一行命中即不算宣称)
NEG_PAT = re.compile(
    r"不能|未能|没[有得]|无法|不宣称|不得|并非|不是|未兑现|没兑现|未达|低于|不代表|"
    r"不构成|不外推|不归因|不单独|unknown|待核|未证|尚不|难以|噪声同量级", re.I)
# 降级模式的文件名门槛:结果/报告类,排除预注册/请求/PLAIN 副本等
DEGRADED_NAME_PAT = re.compile(r"RESULT|REPORT|RECON", re.I)
DEGRADED_NAME_SKIP_PAT = re.compile(r"PREREG|REQUEST|_PLAIN|HANDOFF|TASK_|REVIEW", re.I)


def _parse_thresholds(text: str):
    """解析判定线阈值,返回 (lt_pcts, lt_counts, ge_pcts, ge_counts, range_lows)。

    `<X%`/`<X 题` 是回查触发线(实测低于即未达);`≥X`/`≥X%` 与 `A–B%` 是
    目标线(实测低于下沿即未达)。
    """
    lt_pct, lt_cnt, ge_pct, ge_cnt, rng = [], [], [], [], []
    for m in THRESH_LT_PAT.finditer(text):
        (lt_pct if m.group(2) == "%" else lt_cnt).append(float(m.group(1)))
    for m in THRESH_GE_PAT.finditer(text):
        if m.group(2) == "%":
            ge_pct.append(float(m.group(1)))
        else:  # ≥5 题 与表格 ≥ 116 形态都按题数比较
            ge_cnt.append(float(m.group(1)))
    for m in THRESH_RANGE_PAT.finditer(text):
        rng.append(float(m.group(1)))
    return lt_pct, lt_cnt, ge_pct, ge_cnt, rng


def _parse_measured(text: str, metrics=None):
    """解析实测读数,返回 (count, pct) 或 None。

    metrics.json(main_caliber.hit@1)机读优先;否则逐行扫描打分:
    hit@1/=读数 行 +2,分数(NN/分母,分子≠分母)+1,同行百分数补全 pct,
    行含 hit@1/命中/实测/本批 关键词再 +1;取最高分行(并列取先出现)。
    """
    if isinstance(metrics, dict):
        main = metrics.get("main_caliber")
        if isinstance(main, dict) and isinstance(main.get("hit@1"), (int, float)):
            rate = main.get("hit@1_rate")
            denom = metrics.get("denominator")
            pct = float(rate) * 100 if isinstance(rate, (int, float)) else (
                float(main["hit@1"]) / float(denom) * 100.0 if denom else None)
            return float(main["hit@1"]), pct
    best = None  # (score, count, pct)
    for line in text.splitlines():
        cnt = pct = None
        score = 0.0
        for m in MEAS_HIT_PAT.finditer(line):
            if _THRESH_BEFORE.search(m.group(1)):  # gap 里有 ≥/< → 是判定线数字
                continue
            if _not_threshold_context(line, m.start(2)):
                cnt = float(m.group(2))
                score += 2
                break
        if cnt is None:
            m = MEAS_EQ_PAT.search(line)
            if m and not _THRESH_BEFORE.search(m.group(2)):
                cnt = float(m.group(3))
                score += 2
        if cnt is None:
            fm = MEAS_FRAC_PAT.search(line)
            if fm and fm.group(1) != fm.group(2) \
                    and _not_threshold_context(line, fm.start()):
                # 298/298 是完成率,不是读数
                cnt = float(fm.group(1))
                pct = cnt / float(fm.group(2)) * 100.0
                score += 1
        if cnt is not None:
            for pm in MEAS_PCT_PAT.finditer(line):
                if _not_threshold_context(line, pm.start()):
                    pct = float(pm.group(1))
                    break
        else:
            for pm in MEAS_PCT_PAT.finditer(line):
                if _not_threshold_context(line, pm.start()):
                    pct = float(pm.group(1))
                    score += 0.5
                    break
        if pct is not None and pct > 100.0:  # 分数分子>分母是计数比,不是率
            pct = None
        if MEAS_KEYWORD_PAT.search(line):
            score += 1
        if cnt is None and pct is None:
            continue
        if best is None or score > best[0]:
            best = (score, cnt, pct)
    if best is None:
        return None
    return best[1], best[2]


def _judge(text: str, metrics=None, path=""):
    """对单份(或批根合并)文本判 定。返回 (n_pass, findings, notes, judged)。

    judged: "met" | "unmet" | None(无判定线或无法比较)。
    """
    findings, notes = [], []
    lt_pct, lt_cnt, ge_pct, ge_cnt, rng = _parse_thresholds(text)
    # 机读判定线:metrics.json main_caliber.pass_lines(达标线,语义 ≥)
    if isinstance(metrics, dict):
        main = metrics.get("main_caliber")
        if isinstance(main, dict) and isinstance(main.get("pass_lines"), dict):
            for v in main["pass_lines"].values():
                if isinstance(v, (int, float)):
                    ge_cnt.append(float(v))
    le_hits = []
    for line in text.splitlines():
        if LE_CONTEXT_PAT.search(line):
            le_hits += THRESH_LE_PAT.findall(line)
    measurable = bool(lt_pct or lt_cnt or ge_pct or ge_cnt or rng)

    # 检查项 1:判定线数值可解析
    if not measurable:
        if le_hits:  # 净失/上限型停点(≤−N):识别但不做自动比对
            notes.append(f"判定线为净失/上限型停点(≤−N 命中 {len(le_hits)} 处),"
                         f"读数未自动比对,需人工复核")
            return 1, findings, notes, None
        if GATE_MARK_STRICT_PAT.search(text):
            findings.append(finding(path, 0,
                             "有判定线措辞但判定线数值不可解析(<N%/<N题/≥N/N–M% 均未命中)"))
            return 0, findings, notes, None
        return 0, [], ["无判定线,止损门不适用"], None

    # 检查项 2:实测值可解析
    meas = _parse_measured(text, metrics)
    if meas is None or (meas[0] is None and meas[1] is None):
        findings.append(finding(path, 0,
                         "有判定线但实测值不可解析(hit@K/NN/分母/vN=/实测/% 均未命中)"))
        return 1, findings, notes, None
    count, pct = meas
    notes.append(f"实测解析: count={count:g}" if count is not None else "实测解析: count 未知")
    if pct is not None:
        notes[-1] += f", pct={pct:.2f}%"
    n_pass = 2  # 判定线解析 + 实测解析

    # 未达线判定:任一可比阈值低于线 → unmet(保守取向,止损门宁严勿松)
    unmet = []
    if pct is not None:
        unmet += [f"<{x:g}%" for x in lt_pct if pct < x]
        unmet += [f"≥{x:g}%" for x in ge_pct if pct < x]
        unmet += [f"区间{x:g}–%下沿" for x in rng if pct < x]
    if count is not None:
        unmet += [f"<{x:g}题" for x in lt_cnt if count < x]
        unmet += [f"≥{x:g}题" for x in ge_cnt if count < x]
    judged = "unmet" if unmet else "met"
    if judged == "unmet":
        notes.append("未达线判定依据: " + ", ".join(unmet[:6]))
    return n_pass, findings, notes, judged


def _find_recheck_line(text: str):
    """文本中找回查记录,返回首个命中行号(无则 0)。"""
    for i, line in enumerate(text.splitlines(), 1):
        if RECHECK_PAT.search(line):
            return i
    return 0


def _check_claims(path, text: str):
    """未达线文本扫宣称句:当前行(含上一行语境)无否定守卫的宣称 → finding。"""
    findings = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not CLAIM_PAT.search(line):
            continue
        ctx = ((lines[i - 1] if i else "") + "\n" + line)
        if NEG_PAT.search(ctx):
            continue
        findings.append(finding(path, i + 1,
                         f"未达线但出现未加否定的宣称句(需人工复核): {line.strip()[:60]}"))
    return findings


def _batch_metrics(batch: Path):
    """读批根 metrics.json(存在则返回 dict,否则 None)。"""
    p = batch / "metrics.json"
    if not p.is_file():
        return None
    try:
        return json.loads(load_text(p))
    except (ValueError, OSError):
        return None


def _batch_tags(batch: Path, metrics=None):
    """提取批 tag 候选:orchestration.json runs_root basename + metrics.batch_tag + 目录名。"""
    tags = set()
    orch = batch / "orchestration.json"
    if orch.is_file():
        try:
            rr = json.loads(load_text(orch)).get("runs_root")
            if isinstance(rr, str) and rr.strip():
                tags.add(Path(rr.strip().rstrip("/")).name)
        except (ValueError, OSError):
            pass
    if isinstance(metrics, dict) and isinstance(metrics.get("batch_tag"), str):
        tags.add(metrics["batch_tag"])
    tags.add(batch.name)
    return {t for t in tags if len(t) >= 6}  # 过滤 r2 这类过短目录名


def _recheck_in_docs(repo: Path, tags):
    """在 docs/ 里找提及任一批 tag 且含回查记录的结果报告,返回 (path, line) 或 None。

    命中多个时按文件名优先级取:RESULT/RECON/DELIVERY 结果报告 > 其他
    (回查结论按契约回写在结果报告,不是任务书/选项表)。
    """
    docs = repo / "docs"
    if not tags or not docs.is_dir():
        return None
    tag_res = [re.compile(re.escape(t)) for t in tags]
    hits = []
    for p in sorted(docs.glob("*.md")):
        if DEGRADED_NAME_SKIP_PAT.search(p.name) and "RESULT" not in p.name.upper():
            continue
        text = load_text(p)
        if not any(r.search(text) for r in tag_res):
            continue
        line = _find_recheck_line(text)
        if line:
            pri = 0 if re.search(r"RESULT|RECON|DELIVERY", p.name, re.I) else 1
            hits.append((pri, p, line))
    if not hits:
        return None
    hits.sort(key=lambda x: x[0])
    return hits[0][1], hits[0][2]


def run_check(repo: Path, batch: Path | None = None, max_findings: int = 100):
    """主检查。返回 emit 所需参数 dict。"""
    findings, notes = [], []
    if batch is not None and not batch.is_dir():
        return {"status": "error", "findings": [finding(batch, 0, "批根目录不存在")],
                "notes": ["MODE=batch"], "n_pass": 0, "n_fail": 0}
    mode = "batch" if batch is not None else "degraded"
    notes.append(f"MODE={mode}")

    if batch is not None:
        metrics = _batch_metrics(batch)
        texts = [(p, load_text(p)) for p in sorted(batch.glob("*.md"))]
        if not texts and metrics is None:
            notes.append("批根内无 md 也无 metrics.json,0 检查,不判 fail")
            return {"status": "pass", "findings": [], "notes": notes, "n_pass": 0, "n_fail": 0}
        src = texts[0][0] if texts else batch
        combined = "\n".join(t for _, t in texts)
        n_pass, fd, nn, judged = _judge(combined, metrics, path=str(src))
        findings += fd
        notes += nn
        if judged == "unmet":
            n_pass += 1  # 未达线识别本身成立
            line = _find_recheck_line(combined)
            hit = (src, line) if line else None
            if hit is None:  # 批根无回查 → 按批 tag 去 docs/ 找(回查结论回写结果报告)
                hit = _recheck_in_docs(repo, _batch_tags(batch, metrics))
                if hit:
                    notes.append(f"批根无回查记录,于 docs/ 按批 tag 找到: "
                                 f"{hit[0].name}:{hit[1]}")
            if hit is not None:
                n_pass += 1
                notes.append(f"回查记录: {hit[0].name}:{hit[1]}")
            else:
                findings.append(finding(src, 0,
                                 "未达线但未发现回查记录(回查/配对/逐桶/净增/换手均未命中,"
                                 "批根与 docs/ 按批 tag 均未找到)"))
            for p, t in texts:  # 宣称句逐文件核(行号对应原文件)
                findings += _check_claims(p, t)
        status = "fail" if findings else "pass"
        return {"status": status, "findings": findings[:max_findings], "notes": notes,
                "n_pass": n_pass, "n_fail": len(findings)}

    # ---- 降级模式:扫 docs/ 结果报告 ----
    docs = repo / "docs"
    files = []
    if docs.is_dir():
        for p in sorted(docs.glob("*.md")):
            if DEGRADED_NAME_PAT.search(p.name) and not DEGRADED_NAME_SKIP_PAT.search(p.name):
                files.append(p)
    files = files[:MAX_DOCS]
    if not files:
        notes.append("docs/ 下未找到 RESULT/REPORT 类结果报告,0 检查,不判 fail")
        return {"status": "pass", "findings": [], "notes": notes, "n_pass": 0, "n_fail": 0}
    notes.append(f"降级模式(无批根):扫 docs/ {len(files)} 份结果报告"
                 f"(判定线+实测+回查+宣称,上限 {MAX_DOCS} 份)")

    n_pass = n_gated = 0
    for p in files:
        text = load_text(p)
        if not GATE_MARK_PAT.search(text):
            continue  # 无判定线的报告不适用止损门(不计 pass 也不计 fail)
        # 降级模式加一道门槛:须有强判定线措辞(判定线/达标线/回查线/强制回查/
        # 预注册线)或净失型停点(≤−N),仅泛词「停点」的实现报告不进入判定
        if not (GATE_MARK_STRICT_PAT.search(text) or THRESH_LE_PAT.search(text)):
            continue
        n_gated += 1
        np_, fd, nn, judged = _judge(text, None, path=str(p))
        n_pass += np_
        findings += fd
        notes += [f"{p.name}: {x}" for x in nn]
        if judged == "unmet":
            line = _find_recheck_line(text)
            if line:
                n_pass += 1
            else:
                findings.append(finding(p, 0, "未达线但本文未发现回查记录(回查/配对/逐桶/净增/换手)"))
            findings += _check_claims(p, text)
    notes.append(f"进入判定的报告 {n_gated} 份(其余无判定线措辞,不适用)")
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings[:max_findings], "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="stop-loss-gate 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--batch", default=None, help="批根目录(缺省则降级扫 docs/)")
    ap.add_argument("--max-findings", type=int, default=100, help="finding 上限")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), Path(args.batch) if args.batch else None,
                  args.max_findings)
    print(f"MODE={'batch' if args.batch else 'degraded'}")  # 契约:摘要首行标注模式
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
