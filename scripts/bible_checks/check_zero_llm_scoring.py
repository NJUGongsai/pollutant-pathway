#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zero-llm-scoring 机器检查:判分零 LLM、锁哈希一致、金标只读。

调用:
    python3 scripts/bible_checks/check_zero_llm_scoring.py --repo <repo根>

检查项(全静态/字符串层,不运行判分代码、不读金标内容):
1. 判分链路源码不得 import LLM 客户端(openai/dashscope/anthropic/langchain*/litellm);
2. 判分器源码哈希须与脚本锁 docs/T_P2_SCRIPT_LOCK_2026-10-21.json 的 files 表一致
   (锁为 {相对路径: 文件sha256} 表;锁里没有的条目记 unknown 不判 fail);
3. 金标装载模块(reference_graph*.py)不得出现可写操作;判分链路内出现
   指向 reference/金标 的写操作即违规(判分产物落批根属正常,不算);
4. 金标装载路径须落在 gitignored 区域(只查 .gitignore 规则与源码内路径字符串,
   不读金标目录内容)。
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import REPO_DEFAULT, emit, finding, load_text, sha256_file  # noqa: E402

CHECK = "zero-llm-scoring"

# 判分链路入口:scoring*.py / score*.py / scoring/ 目录(契约指定),实测覆盖
# src/pathway_v43/pollutant/s5b_scoring.py 与 src/pathway_v43/output/score_report.py;
# 金标装载模块(reference_graph*/gold*)无条件入链——只读红线与是否被 import 无关。
ENTRY_GLOBS = ("src/**/scoring*.py", "src/**/score*.py", "src/scoring/**/*.py",
               "src/**/reference_graph*.py", "src/**/gold*.py")
# 判分链路相对包内导入的追踪深度上限(防止全仓传染)
_MAX_IMPORT_DEPTH = 3

# 禁止出现在判分链路的 LLM 客户端根包名
LLM_PACKAGES = ("openai", "dashscope", "anthropic", "litellm")
LLM_PREFIX = "langchain"  # langchain* 家族

# 金标相关名字(路径字符串/模块名层面判断,不读内容)
GOLD_NAME_PAT = re.compile(r"reference_graph|reference-graph|金标|gold", re.I)
GITIGNORE_GOLD_PAT = re.compile(r"reference_graph|reports/ppv1|gold", re.I)


def _module_to_path(repo: Path, mod: str) -> Path | None:
    """把第一方包名(如 pathway_v43.pollutant.evaluation)解析为 src/ 下文件。"""
    base = repo / "src"
    rel = mod.replace(".", "/")
    for cand in (base / f"{rel}.py", base / rel / "__init__.py"):
        if cand.is_file():
            return cand
    return None


def _resolve_import(repo: Path, node, cur_mod_parts: list[str]) -> str | None:
    """把一条 Import/ImportFrom 解析为第一方模块名;第三方返回 None。"""
    if isinstance(node, ast.Import):
        return None  # 绝对 import 的第三方在 LLM 包名检查里直接判,不做链路追踪
    if isinstance(node, ast.ImportFrom) and node.level > 0 and node.module:
        # 相对导入:按当前包向上回退 level 级
        base = cur_mod_parts[: len(cur_mod_parts) - node.level] if node.level <= len(cur_mod_parts) else []
        return ".".join(base + [node.module])
    if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "pathway_v43":
        return node.module
    return None


def discover_scoring_chain(repo: Path) -> list[Path]:
    """发现判分链路:入口 glob + 包内相对导入闭包(限深度)。"""
    entries = []
    for pat in ENTRY_GLOBS:
        entries += [p for p in repo.glob(pat) if p.is_file() and p.suffix == ".py"]
    seen, queue, out = set(), [], []
    for p in sorted(set(entries)):
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            queue.append((p, 0))
            out.append(p)
    while queue:
        path, depth = queue.pop(0)
        if depth >= _MAX_IMPORT_DEPTH:
            continue
        try:
            tree = ast.parse(load_text(path))
        except SyntaxError:
            continue
        parts = path.relative_to(repo / "src").with_suffix("").parts
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            mod = _resolve_import(repo, node, list(parts))
            if not mod:
                continue
            dep = _module_to_path(repo, mod)
            if dep is not None:
                key = dep.resolve()
                if key not in seen:
                    seen.add(key)
                    out.append(dep)
                    queue.append((dep, depth + 1))
    return sorted(out, key=lambda p: str(p))


def check_llm_imports(repo: Path, chain: list[Path]):
    """检查项 1:AST 层扫 LLM 客户端 import,命中记录 file:line。"""
    findings = []
    for path in chain:
        try:
            tree = ast.parse(load_text(path))
        except SyntaxError as e:
            findings.append(finding(path, 0, f"源码语法解析失败,无法静态核验: {e}"))
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                if root in LLM_PACKAGES or root.startswith(LLM_PREFIX):
                    findings.append(finding(path, node.lineno,
                                     f"判分链路 import LLM 客户端: {name}"))
    return findings


def check_lock_hashes(repo: Path, chain: list[Path], lock_path: Path):
    """检查项 2:判分链路文件哈希 ↔ 脚本锁 files 表({相对路径: sha256})。"""
    findings, notes = [], []
    n_pass = 0
    if not lock_path.is_file():
        return 0, [], [f"脚本锁不存在({lock_path}),哈希核验整体记 unknown"]
    try:
        lock = json.loads(load_text(lock_path))
    except ValueError as e:
        return 0, [finding(lock_path, 0, f"脚本锁 JSON 解析失败: {e}")], notes
    files_tab = lock.get("files")
    if not isinstance(files_tab, dict):
        return 0, [finding(lock_path, 0, "脚本锁缺 files 表,哈希核验记 unknown")], notes

    not_in_lock = []
    for path in chain:
        rel = str(path.relative_to(repo))
        actual = sha256_file(path)
        if rel not in files_tab:
            not_in_lock.append(rel)
            continue
        want = files_tab[rel]
        if actual == want:
            n_pass += 1
        else:
            findings.append(finding(path, 0,
                             f"判分器源码哈希与脚本锁不符: 锁 {str(want)[:12]}…, 实际 {actual[:12]}…"))
    if not_in_lock:
        notes.append(f"锁里没有的判分链路条目(记 unknown): {', '.join(not_in_lock)}")
    # 锁整体健康状况只作附注(锁在 HPC 部署树实测,本地树前进而产生差异属预期)
    match = sum(1 for rel, h in files_tab.items()
                if (repo / rel).is_file() and sha256_file(repo / rel) == h)
    notes.append(f"脚本锁整体: {len(files_tab)} 条, 本地可核 {match} 条一致, "
                 f"{len(files_tab) - match} 条不同/缺失(HPC 部署树快照,本地树前进属预期,不判违规)")
    return n_pass, findings, notes


def check_gold_writes(chain: list[Path]):
    """检查项 3:金标装载模块不得有写操作;判分链路不得写 reference/金标 目标。"""
    findings = []
    n_pass = 0
    write_attrs = {"write_text", "write_bytes", "unlink", "rmdir", "mkdir"}
    write_funcs = {"copy", "copytree", "move", "rmtree", "remove", "unlink", "makedirs"}
    for path in chain:
        is_gold_module = bool(GOLD_NAME_PAT.search(path.name))
        try:
            tree = ast.parse(load_text(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            mode_writes_gold = False
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                mode = None
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value
                if mode and any(c in str(mode) for c in "wax+"):
                    strs = [a.value for a in node.args if isinstance(a, ast.Constant)
                            and isinstance(a.value, str)]
                    if is_gold_module or any(GOLD_NAME_PAT.search(s) for s in strs):
                        mode_writes_gold = True
            elif isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if attr in write_attrs or (isinstance(node.func.value, ast.Name)
                                           and node.func.value.id == "shutil"
                                           and attr in write_funcs):
                    strs = [a.value for a in node.args if isinstance(a, ast.Constant)
                            and isinstance(a.value, str)]
                    if is_gold_module or any(GOLD_NAME_PAT.search(s) for s in strs):
                        mode_writes_gold = True
            if mode_writes_gold:
                findings.append(finding(path, node.lineno,
                                 f"金标装载/引用路径上的可写操作: {ast.unparse(node)[:80]}"))
    if not findings:
        n_pass = 1
    return n_pass, findings


def check_gold_paths_ignored(repo: Path, chain: list[Path]):
    """检查项 4(报告性质):金标路径字符串落点 + .gitignore 隔离规则核验。

    只做字符串/规则检查,不读金标目录内容。规则缺失 → unknown 附注,不判 fail。
    """
    notes, literals = [], []
    for path in chain:
        for i, line in enumerate(load_text(path).splitlines(), 1):
            if GOLD_NAME_PAT.search(line) and ("/" in line or "批根" in line or "dir" in line.lower()):
                literals.append(f"{path.name}:{i}")
    if literals:
        notes.append(f"金标路径相关字符串(装载声明,只读核验): {', '.join(literals[:6])}"
                     + ("…" if len(literals) > 6 else ""))
    gi = repo / ".gitignore"
    if gi.is_file() and GITIGNORE_GOLD_PAT.search(load_text(gi)):
        n_pass = 1
        notes.append(".gitignore 含金标区隔离规则(reference_graph/reports/ppv1/gold),金标不入仓可核")
    else:
        n_pass = 0
        notes.append("unknown: .gitignore 未发现金标区隔离规则,无法确认金标路径落在不可入仓位置")
    return n_pass, notes


def run_check(repo: Path, lock_path: Path | None = None):
    """主检查。任一违规 → fail;判分链路无法发现 → error。"""
    lock_path = lock_path or (repo / "docs" / "T_P2_SCRIPT_LOCK_2026-10-21.json")
    chain = discover_scoring_chain(repo)
    notes = [f"判分链路({len(chain)} 件): " + ", ".join(
        str(p.relative_to(repo)) for p in chain[:8]) + ("…" if len(chain) > 8 else "")]
    if not chain:
        return {"status": "error", "findings": [finding(repo / "src", 0, "未发现任何判分链路源码")],
                "notes": notes, "n_pass": 0, "n_fail": 0}

    findings = check_llm_imports(repo, chain)
    n_zero = 1 if not findings else 0

    np_lock, f_lock, n_lock = check_lock_hashes(repo, chain, lock_path)
    findings += f_lock
    notes += n_lock

    np_gold, f_gold = check_gold_writes(chain)
    findings += f_gold
    notes.append("金标只读写检查: " + ("通过(装载模块零写操作)" if not f_gold else f"{len(f_gold)} 处违规"))

    np_ign, n_ign = check_gold_paths_ignored(repo, chain)
    notes += n_ign

    n_pass = n_zero + np_lock + np_gold + np_ign
    status = "fail" if findings else "pass"
    return {"status": status, "findings": findings, "notes": notes,
            "n_pass": n_pass, "n_fail": len(findings)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="zero-llm-scoring 机器检查")
    ap.add_argument("--repo", default=str(REPO_DEFAULT), help="仓库根(缺省=本仓)")
    ap.add_argument("--lock", default=None, help="脚本锁 JSON 路径(缺省=docs/T_P2_SCRIPT_LOCK_*.json)")
    args = ap.parse_args(argv)
    r = run_check(Path(args.repo), Path(args.lock) if args.lock else None)
    return emit(CHECK, r["status"], r["findings"], r["notes"], r["n_pass"], r["n_fail"])


if __name__ == "__main__":
    sys.exit(main())
