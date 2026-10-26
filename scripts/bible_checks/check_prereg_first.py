#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prereg-first 机器检查:预注册先于付费 —— 判定线/哈希/发车登记先写死。

调用:
    python3 scripts/bible_checks/check_prereg_first.py --repo <repo根> [--batch <批根>]

- 给了 --batch:在批根(及其 docs 常规位置)找预注册 md 与 approval package,
  逐项核(存在/判定线/哈希可核/发车登记),缺任一 → fail;
- 没给 --batch:对 docs/ 里全部 *PREREG* 文档跑降级检查,摘要明确标注
  「降级模式(无批根)」;approval package 若在 docs/P2_APPROVAL_PACKAGE_*/
  下能找到,仍做真实哈希互核;找不到 approval 记 unknown,不直接 fail。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, find_files, finding, load_text, sha256_file  # noqa: E402

CHECK = "prereg-first"

# 判定线字段的写法(按本仓预注册实际用词校准):判定线/阈值/停点/净增/净失/hit@N/≥N
_JUDGE_PAT = re.compile(r"判定线|阈值|停点|净增|净失|hit@\d|≥\s*\d|≤\s*-?\d")
# 显式弃权写法:探索性口径声明不设判定线(如实声明,不算违规)
_WAIVER_PAT = re.compile(r"不设判定线|探索性口径")
# 发车登记行:发车/launch/登记(大小写不敏感)
_LAUNCH_PAT = re.compile(r"发车|launch|登记", re.I)
# 草稿态标记:设计稿还没发车,缺发车登记属正常,记 n/a 而非违规
_DRAFT_PAT = re.compile(r"draft|草案|待评审|待拍板|未发车", re.I)

PREREG_PATTERNS = ("**/*PREREG*.md", "**/*prereg*.md",
                   "**/*preregistration*.md", "**/*PREREGISTRATION*.md")


def _iter_prereg_docs(repo: Path, batch: Path | None):
    """收集预注册 md:批根优先,其次 docs/(递归,含 approval package 子目录);去重保序。"""
    roots = []
    if batch is not None:
        roots.append(batch)
    roots.append(repo / "docs")
    seen, out = set(), []
    for root in roots:
        if not root.is_dir():
            continue
        for p in find_files(root, PREREG_PATTERNS):
            if p.resolve() not in seen:
                seen.add(p.resolve())
                out.append(p)
    return out


def _check_doc(doc: Path):
    """对单份预注册 md 核「判定线」与「发车登记」两个子检查。

    返回 (n_pass, findings, notes):判定线缺失 → 违规;显式弃权/草稿态 → 附注放行。
    """
    n_pass, findings, notes = 0, [], []
    text = load_text(doc)
    lines = text.splitlines()

    # 子检查:判定线字段
    judge_hits = [(i + 1, l) for i, l in enumerate(lines) if _JUDGE_PAT.search(l)]
    if judge_hits:
        n_pass += 1
    elif _WAIVER_PAT.search(text):
        n_pass += 1
        notes.append(f"{doc.name}: 显式声明不设判定线(探索性口径),放行")
    else:
        findings.append(finding(doc, 0, "预注册缺判定线字段(判定线/阈值/停点/hit@/≥N 均未出现)"))

    # 子检查:发车登记行
    if _LAUNCH_PAT.search(text):
        n_pass += 1
    elif _DRAFT_PAT.search(text[:4000]):
        n_pass += 1
        notes.append(f"{doc.name}: 草稿态(draft/待评审),尚未发车,发车登记不适用")
    else:
        first = next((i + 1 for i, l in enumerate(lines) if l.strip()), 0)
        findings.append(finding(doc, first, "已生效预注册但未见发车/登记行(发车|launch|登记)"))
    return n_pass, findings, notes


def _collect_declared_pairs(obj, pairs):
    """递归收集 approval JSON 里所有同时带 path+sha256 的声明(路径, 哈希)对。"""
    if isinstance(obj, dict):
        path, sha = obj.get("path"), obj.get("sha256")
        if isinstance(path, str) and isinstance(sha, str) and len(sha) == 64:
            pairs.append((path, sha))
        for v in obj.values():
            _collect_declared_pairs(v, pairs)
    elif isinstance(obj, list):
        for v in obj:
            _collect_declared_pairs(v, pairs)


def _verify_approval(repo: Path, batch: Path | None):
    """核 approval package 与其声称的文件哈希(真实 sha256 互核),三层:

    1. JSON 内声明的 (path, sha256) 对 → 按路径定位磁盘文件实核;
    2. 顶层 <字段>_sha256 → 对 approval 包目录内文件按哈希成员核;
    3. approval 自哈希(canonical JSON,排除自身与算法说明两个键)。
    找不到 approval → unknown(不算 fail)。
    """
    notes = []
    # 找 preregistration_approval.json:批根 → docs/P2_APPROVAL_PACKAGE_*/
    candidates = []
    if batch is not None:
        candidates += [batch / "preregistration_approval.json",
                       batch / "approval" / "preregistration_approval.json"]
    candidates += sorted((repo / "docs").glob("P2_APPROVAL_PACKAGE_*/preregistration_approval.json"))
    approval_path = next((c for c in candidates if c.is_file()), None)
    if approval_path is None:
        return 0, 0, [], ["approval package 未找到(preregistration_approval.json),记 unknown 不判 fail"]

    n_pass, n_fail, findings = 0, 0, []
    try:
        approval = json.loads(load_text(approval_path))
    except (ValueError, OSError) as e:
        return 0, 1, [finding(approval_path, 0, f"approval JSON 解析失败: {e}")], notes

    # 层 1:声明的 (path, sha) 对逐条实核
    pairs = []
    _collect_declared_pairs(approval, pairs)
    known_shas = set()
    for rel, want in pairs:
        target = repo / rel
        if not target.is_file():  # 声明路径也可能相对包目录
            alt = approval_path.parent / Path(rel).name
            target = alt if alt.is_file() else target
        if not target.is_file():
            notes.append(f"声明文件不存在,记 unknown: {rel}")
            continue
        actual = sha256_file(target)
        known_shas.add(actual)
        if actual == want:
            n_pass += 1
        else:
            n_fail += 1
            findings.append(finding(target, 0,
                             f"哈希不符: approval 声称 {want[:12]}…, 磁盘实际 {actual[:12]}…"))

    # 层 2:顶层 <字段>_sha256 ↔ 包目录文件哈希成员(包目录小,全量哈希成本可忽略)
    pkg_files = [p for p in approval_path.parent.iterdir()
                 if p.is_file() and p != approval_path]
    pkg_by_hash = {sha256_file(p): p.name for p in pkg_files}
    known_shas.update(pkg_by_hash)
    skip = ("approval_sha256", "approval_sha256_algorithm")
    for key, val in approval.items():
        if key in skip or not key.endswith("_sha256"):
            continue
        if not isinstance(val, str) or len(val) != 64:
            continue
        if val in known_shas:
            n_pass += 1
        else:
            n_fail += 1
            findings.append(finding(approval_path, 0,
                             f"{key} 对不上任何可定位文件的实测哈希(声称 {val[:12]}…)"))

    # 层 3:approval 自哈希(canonical JSON)
    want_self = approval.get("approval_sha256")
    algo = approval.get("approval_sha256_algorithm", "")
    if isinstance(want_self, str) and "canonical_json" in algo:
        stripped = {k: v for k, v in approval.items()
                    if k not in ("approval_sha256", "approval_sha256_algorithm")}
        canon = json.dumps(stripped, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(canon).hexdigest()
        if actual == want_self:
            n_pass += 1
        else:
            n_fail += 1
            findings.append(finding(approval_path, 0,
                             f"approval 自哈希不符: 声称 {str(want_self)[:12]}…, 实算 {actual[:12]}…"))
    elif want_self is None:
        notes.append("approval 无 approval_sha256 字段,自哈希核验记 unknown")
    return n_pass, n_fail, findings, notes


def run_check(repo: Path, batch: Path | None):
    """主检查:返回 emit 所需参数 dict。"""
    findings, notes = [], []
    if batch is not None and not batch.is_dir():
        return {"status": "error", "findings": [finding(batch, 0, "批根目录不存在")],
                "notes": [], "n_pass": 0, "n_fail": 0}

    docs = _iter_prereg_docs(repo, batch)
    if batch is None:
        notes.append("降级模式(无批根):对 docs/ 下预注册文档逐份检查")
    if not docs:
        findings.append(finding(repo / "docs", 0, "未找到任何预注册文档(*PREREG*/*preregistration*)"))
        return {"status": "fail", "findings": findings, "notes": notes, "n_pass": 0, "n_fail": 1}

    # 子检查 1+2+4:存在性(隐含)、判定线、发车登记 —— 逐份文档
    n_pass = 1  # 存在性:能走到这里即预注册 md 存在
    for doc in docs[:50]:  # 上限保护:最多核 50 份
        p, f, nn = _check_doc(doc)
        n_pass += p
        findings += f
        notes += nn

    # 子检查 3:approval 哈希互核(找不到 → unknown,不计 fail)
    ap, af, aff, an = _verify_approval(repo, batch)
    n_pass += ap
    findings += aff
    notes += an
    if ap == 0 and af == 0:
        notes.append("哈希互核: unknown(无 approval package 可核)")

    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="prereg-first 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--batch", default=None, help="批根目录(缺省则对 docs/ 降级检查)")
    args = ap.parse_args(argv)
    repo, batch = Path(args.repo), (Path(args.batch) if args.batch else None)
    r = run_check(repo, batch)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
