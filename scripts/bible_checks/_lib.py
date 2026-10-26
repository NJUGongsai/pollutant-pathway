# -*- coding: utf-8 -*-
"""bible_checks 公共库 —— 机器检查契约(docs/BIBLE/_CONTRACT.md 第三节)的公共件。

约定:
- 输出: stdout 人类可读摘要(≤20 行) + 最后一行严格 JSON;
- 退出码: 0=pass, 1=fail(发现违规), 2=error(无法检查);
- 只用标准库,不引第三方依赖。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# 缺省仓库根: scripts/bible_checks/_lib.py → 上两级
REPO_DEFAULT = Path(__file__).resolve().parents[2]

# 遍历时跳过的目录(.git/缓存类);review_evidence/ 里的大 JSON 只在扫 JSON 时跳,
# 本框架默认只读 .md 与指定源码,不盲扫大文件。
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv"}

# 退出码映射
_EXIT = {"pass": 0, "fail": 1, "error": 2}


def load_text(path) -> str:
    """读文本: UTF-8、坏字节替换、统一换行(Windows CRLF → LF)。"""
    raw = Path(path).read_bytes()
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def iter_md(repo, pattern="**/*.md"):
    """按 glob 遍历仓内 .md,跳过 .git 等目录;返回排序去重后的 Path 列表。"""
    repo = Path(repo)
    seen = set()
    for p in sorted(repo.glob(pattern)):
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            yield p


def find_files(root, patterns):
    """在 root 下按多个 glob 找文件(大小写不敏感后缀交给 pattern 本身),去重排序。"""
    root = Path(root)
    out = {}
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                out.setdefault(p.resolve(), p)
    return sorted(out.values(), key=lambda p: str(p))


def sha256_file(path) -> str:
    """文件字节级 SHA256(流式,不整读入内存)。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo) -> str | None:
    """返回仓库 HEAD 全 hex;非 git 仓/无提交时返回 None(不抛异常)。"""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    head = r.stdout.strip()
    return head or None


def finding(path, line, msg) -> dict:
    """构造契约格式的 finding;line 未知时用 0。"""
    return {"path": str(path), "line": int(line or 0), "msg": str(msg)}


def emit(check, status, findings, notes=(), n_pass=0, n_fail=None, out=None) -> int:
    """打印人类摘要 + 最后一行契约 JSON;返回退出码。

    - status: "pass" | "fail" | "error";
    - findings: 违规列表(契约 schema: path/line/msg);
    - notes: 附注行(如 unknown 项、降级模式声明),只进人类摘要,不进 JSON;
    - n_fail 缺省 = len(findings);n_pass 由调用方按子检查计数;
    - out 缺省在调用时取当前 sys.stdout(便于测试捕获)。
    """
    if out is None:
        out = sys.stdout
    if status not in _EXIT:
        status = "error"
    if n_fail is None:
        n_fail = len(findings)

    print(f"[bible] {check}: {status.upper()} (pass={n_pass} fail={n_fail})", file=out)
    for note in notes:
        print(f"  · {note}", file=out)
    show = list(findings)
    for fd in show[:12]:
        loc = f"{fd['path']}:{fd['line']}" if fd.get("line") else str(fd["path"])
        print(f"  ✗ {loc} {fd['msg']}", file=out)
    if len(show) > 12:
        print(f"  …另有 {len(show) - 12} 条 finding 略,见末行 JSON", file=out)

    payload = {
        "check": check,
        "status": status,
        "n_pass": int(n_pass),
        "n_fail": int(n_fail),
        "findings": [
            {"path": fd["path"], "line": int(fd.get("line") or 0), "msg": str(fd["msg"])}
            for fd in show
        ],
    }
    print(json.dumps(payload, ensure_ascii=False), file=out)
    return _EXIT[status]
