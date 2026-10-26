# -*- coding: utf-8 -*-
"""bible_checks 自测:临时目录造正/反例,断言退出码、findings 与 JSON 契约。

跑法: python3 -m pytest tests/test_bible_checks.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "bible_checks"))

import _lib  # noqa: E402
import check_anchored_numbers as can  # noqa: E402
import check_prereg_first as cpf  # noqa: E402
import check_zero_llm_scoring as czl  # noqa: E402
import run_all  # noqa: E402


# ---------- _lib ----------

def test_emit_json_contract(capsys):
    """emit 最后一行 JSON 必须严格符合契约 schema,退出码 0/1/2 对应 pass/fail/error。"""
    fd = _lib.finding("docs/x.md", 12, "缺锚")
    assert _lib.emit("prereg-first", "pass", [], notes=["n1"], n_pass=3) == 0
    assert _lib.emit("prereg-first", "fail", [fd], n_pass=3) == 1
    assert _lib.emit("prereg-first", "error", [], n_pass=0) == 2
    out = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(out[-1])
    assert set(payload) == {"check", "status", "n_pass", "n_fail", "findings"}
    assert payload["status"] == "error"  # 最后一行覆盖
    assert payload["n_pass"] == 0 and payload["n_fail"] == 0
    # 再单验 fail 行
    assert _lib.emit("prereg-first", "fail", [fd], n_pass=3) == 1
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["status"] == "fail" and payload["n_fail"] == 1 and payload["n_pass"] == 3
    assert payload["findings"] == [{"path": "docs/x.md", "line": 12, "msg": "缺锚"}]


def test_load_text_crlf_and_sha256(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes(b"line1\r\nline2\r\n")
    assert _lib.load_text(p) == "line1\nline2\n"
    assert _lib.sha256_file(p) == hashlib.sha256(p.read_bytes()).hexdigest()


def test_git_head_real_repo():
    head = _lib.git_head(REPO)
    assert head is not None and 40 <= len(head) <= 64  # 全 hex 已由 git 保证


# ---------- check_anchored_numbers ----------

def _write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_anchored_pass_with_anchor(tmp_path):
    """带锚(口径标签+commit)的数字 → pass,退出码 0。"""
    _write(tmp_path, "docs/good.md",
           "主读数 hit@1 87/298（v2 口径）。\n复核 commit 966bc56 同池同判据。\n")
    r = can.run_check(tmp_path, file_specs=["docs/good.md"])
    assert r["status"] == "pass" and r["n_fail"] == 0 and r["n_pass"] >= 1


def test_anchored_fail_without_anchor(tmp_path):
    """裸数字(无 commit/口径/批次锚)→ fail,finding 带行号与数字原文。"""
    _write(tmp_path, "docs/bad.md", "第一行没什么。\n准确率提升了 12.5%，效果显著。\n")
    r = can.run_check(tmp_path, file_specs=["docs/bad.md"])
    assert r["status"] == "fail" and r["n_fail"] == 1
    fd = r["findings"][0]
    assert fd["line"] == 2 and "12.5%" in fd["msg"]


def test_anchored_adjacent_lines_anchor_counts(tmp_path):
    """锚在 ±2 行窗口内也算有锚(本仓注释/表格换行写法的现实情况)。"""
    _write(tmp_path, "docs/win.md",
           "对照参照 chain13 GLM（87/119/47，多变量批）\n"
           "下一行才是锚:\n"
           "口径 298。\n")
    r = can.run_check(tmp_path, file_specs=["docs/win.md"])
    assert r["status"] == "pass"


def test_anchored_ignore_and_max_findings(tmp_path):
    """--ignore-pattern 豁免命中行;--max-findings=1 截断多条违规。"""
    _write(tmp_path, "docs/multi.md", "涨了 3.2%。\n又涨了 4.5pp。\n")
    r = can.run_check(tmp_path, file_specs=["docs/multi.md"], ignore_patterns=["3.2%"])
    assert r["n_fail"] == 1 and "4.5" in r["findings"][0]["msg"]
    r2 = can.run_check(tmp_path, file_specs=["docs/multi.md"], max_findings=1)
    assert r2["n_fail"] == 1 and any("上限" in n for n in r2["notes"])


def test_anchored_dates_not_flagged(tmp_path):
    """日期 2026/10/21 与纯批次 tag 不应被当无锚数字。"""
    _write(tmp_path, "docs/date.md", "2026/10/21 发车,p2-298-20261021 批。\n")
    r = can.run_check(tmp_path, file_specs=["docs/date.md"])
    assert r["status"] == "pass"


def test_anchored_no_files_is_pass_with_note(tmp_path):
    """空仓(无 git、无 docs/BIBLE)→ 0 检查,pass + 附注,不算 error。"""
    r = can.run_check(tmp_path, file_specs=None)
    assert r["status"] == "pass" and r["n_pass"] == 0


def test_anchored_main_exit_codes(tmp_path, capsys):
    """main() 集成:正例退出 0,反例退出 1。"""
    _write(tmp_path, "docs/g.md", "87/298（298 口径）\n")
    _write(tmp_path, "docs/b.md", "裸 6.6% 数字\n")
    assert can.main(["--repo", str(tmp_path), "--files", "docs/g.md"]) == 0
    assert can.main(["--repo", str(tmp_path), "--files", "docs/b.md"]) == 1
    capsys.readouterr()


# ---------- check_prereg_first ----------

def _mk_prereg(base, name="T_X_PREREG_2026-10-26.md", judge=True, launch=True, draft=False):
    """在 base 目录(批根或 docs/)下写一份预注册 md。"""
    body = "# X 批预注册\n\n"
    if judge:
        body += "判定线: hit@1 净增 ≥15 题,strict 净失 ≤-3 即停点。\n"
    else:
        body += "本批为探索性口径,不设判定线。\n"
    if launch:
        body += "发车登记: 2026-10-26 22:00 登记发车,批次 p2_298_x。\n"
    if draft:
        body = body.replace("# X", "# X(draft 草案 待评审)")
    return _write(base, name, body)


def test_prereg_batch_mode_full_pass(tmp_path):
    """批根模式正例:预注册+判定线+发车登记齐全,approval 缺失记 unknown → 仍 pass。"""
    batch = tmp_path / "reports" / "b1"
    batch.mkdir(parents=True)
    _mk_prereg(batch, name="PREREG.md")
    r = cpf.run_check(tmp_path, batch=batch)
    assert r["status"] == "pass"
    assert any("unknown" in n for n in r["notes"])
    assert r["n_pass"] >= 3  # 存在 + 判定线 + 发车


def test_prereg_batch_mode_missing_judge_fails(tmp_path):
    """非草稿预注册缺判定线 → fail。"""
    batch = tmp_path / "reports" / "b1"
    batch.mkdir(parents=True)
    _mk_prereg(batch, name="PREREG.md", judge=False, launch=True, draft=False)
    # judge=False 时写的是显式弃权句,再补一份真缺判定线的
    (batch / "PREREG2.md").write_text("# Y 预注册\n发车登记:已登记。\n", encoding="utf-8")
    r = cpf.run_check(tmp_path, batch=batch)
    assert r["status"] == "fail"
    assert any("判定线" in f["msg"] for f in r["findings"])


def test_prereg_effective_doc_without_launch_fails(tmp_path):
    """已生效预注册(非 draft)整份无发车/登记行 → fail。"""
    batch = tmp_path / "reports" / "b1"
    batch.mkdir(parents=True)
    (batch / "PREREG.md").write_text("# Z 预注册\n判定线: ≥15。\n", encoding="utf-8")
    r = cpf.run_check(tmp_path, batch=batch)
    assert r["status"] == "fail"
    assert any("发车" in f["msg"] for f in r["findings"])


def test_prereg_draft_launch_na(tmp_path):
    """草稿态预注册缺发车登记 → n/a 放行(附注),不误报。"""
    batch = tmp_path / "reports" / "b1"
    batch.mkdir(parents=True)
    _mk_prereg(batch, name="PREREG.md", launch=False, draft=True)
    r = cpf.run_check(tmp_path, batch=batch)
    assert r["status"] == "pass"
    assert any("草稿" in n for n in r["notes"])


def test_prereg_degraded_mode_label(tmp_path):
    """无批根 → 降级模式,对 docs/ 的 PREREG 逐份检查,摘要带「降级模式」标注。"""
    _mk_prereg(tmp_path / "docs")
    r = cpf.run_check(tmp_path, batch=None)
    assert r["status"] == "pass"
    assert any("降级模式(无批根)" in n for n in r["notes"])


def test_prereg_approval_hash_verification(tmp_path):
    """approval 哈希互核:构造自洽 approval → pass;篡改一个哈希 → fail。"""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    pkg = docs / "P2_APPROVAL_PACKAGE_2026-10-26"
    pkg.mkdir()
    prereg = pkg / "T_X_PREREG_2026-10-26.md"
    prereg.write_text("# P 预注册\n判定线: hit@1 ≥15。\n发车登记:已登记发车。\n", encoding="utf-8")
    prereg_sha = hashlib.sha256(prereg.read_bytes()).hexdigest()
    approval = {
        "batch_tag": "p2-298-20261026",
        "preregistration_text_sha256": prereg_sha,
        "chem_review_doc_sha256": prereg_sha,  # 复用同一文件方便构造
    }
    stripped = {k: v for k, v in approval.items()}
    approval["approval_sha256_algorithm"] = ("sha256(canonical_json(approval minus keys "
                                             "['approval_sha256', 'approval_sha256_algorithm']))")
    approval["approval_sha256"] = hashlib.sha256(
        json.dumps(stripped, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    (pkg / "preregistration_approval.json").write_text(
        json.dumps(approval, ensure_ascii=False, indent=1), encoding="utf-8")
    r = cpf.run_check(tmp_path, batch=None)
    assert r["status"] == "pass", r
    # 篡改 prereg 哈希 → 顶层字段核失败
    bad = json.loads((pkg / "preregistration_approval.json").read_text(encoding="utf-8"))
    bad["preregistration_text_sha256"] = "0" * 64
    (pkg / "preregistration_approval.json").write_text(
        json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")
    r2 = cpf.run_check(tmp_path, batch=None)
    assert r2["status"] == "fail"
    assert any("对不上" in f["msg"] or "哈希不符" in f["msg"] for f in r2["findings"])


def test_prereg_batch_not_found_is_error(tmp_path):
    """--batch 指向不存在目录 → error(退出码对应 2)。"""
    r = cpf.run_check(tmp_path, batch=tmp_path / "nope")
    assert r["status"] == "error"


# ---------- check_zero_llm_scoring ----------

def _mk_repo_with_scoring(tmp_path, body: str, name="scoring_demo.py"):
    """造最小判分链路仓:src/pkg/scoring_demo.py(+包 __init__)。"""
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / name).write_text(body, encoding="utf-8")
    return pkg / name


def test_zero_llm_clean_pass_with_lock(tmp_path):
    """干净判分器 + 锁哈希一致 → pass。"""
    f = _mk_repo_with_scoring(tmp_path, "import json\n\ndef score(x):\n    return json.dumps(x)\n")
    lock = tmp_path / "docs" / "T_P2_SCRIPT_LOCK.json"
    lock.parent.mkdir(parents=True)
    rel = str(f.relative_to(tmp_path))
    lock.write_text(json.dumps({"files": {rel: _lib.sha256_file(f)}}), encoding="utf-8")
    r = czl.run_check(tmp_path, lock_path=lock)
    assert r["status"] == "pass", r
    assert r["n_pass"] >= 2  # 零LLM + 锁哈希(+金标忽略规则可能 unknown 不计)


def test_zero_llm_openai_import_fails(tmp_path):
    """判分器 import openai → fail,finding 带 import 行号。"""
    f = _mk_repo_with_scoring(tmp_path, "import json\nimport openai\n\ndef score(x):\n    return 1\n")
    r = czl.run_check(tmp_path, lock_path=tmp_path / "no_lock.json")
    assert r["status"] == "fail"
    hit = [x for x in r["findings"] if "openai" in x["msg"]]
    assert hit and hit[0]["line"] == 2


@pytest.mark.parametrize("mod", ["dashscope", "anthropic", "litellm", "langchain_community"])
def test_zero_llm_banned_packages(tmp_path, mod):
    """禁用客户端家族逐个命中(dashscope/anthropic/litellm/langchain*)。"""
    _mk_repo_with_scoring(tmp_path, f"import {mod}\n")
    r = czl.run_check(tmp_path, lock_path=tmp_path / "no_lock.json")
    assert r["status"] == "fail"
    assert any(mod in x["msg"] for x in r["findings"])


def test_zero_llm_lock_mismatch_fails_and_unknown_note(tmp_path):
    """锁哈希不符 → fail;锁里没有的链路条目 → unknown 附注不判 fail。"""
    f = _mk_repo_with_scoring(tmp_path, "def score(x):\n    return 1\n")
    lock = tmp_path / "docs" / "L.json"
    lock.parent.mkdir(parents=True)
    rel = str(f.relative_to(tmp_path))
    lock.write_text(json.dumps({"files": {rel: "0" * 64}}), encoding="utf-8")
    r = czl.run_check(tmp_path, lock_path=lock)
    assert r["status"] == "fail"
    assert any("哈希与脚本锁不符" in x["msg"] for x in r["findings"])
    # 另一份不在锁里的判分器 → unknown 附注
    _mk_repo_with_scoring(tmp_path, "def score2(x):\n    return 2\n", name="scoring_extra.py")
    r2 = czl.run_check(tmp_path, lock_path=lock)
    assert any("unknown" in n for n in r2["notes"])


def test_zero_llm_gold_loader_write_fails(tmp_path):
    """金标装载模块(reference_graph.py)出现写操作 → fail。"""
    _mk_repo_with_scoring(tmp_path, "def score(x):\n    return 1\n")
    pkg = tmp_path / "src" / "pkg"
    (pkg / "reference_graph.py").write_text(
        "from pathlib import Path\n"
        "def load(p):\n"
        "    return Path(p).read_text()\n"
        "def save(p, g):\n"
        "    Path(p).write_text(g)  # 违规:金标装载器不该有写\n",
        encoding="utf-8")
    r = czl.run_check(tmp_path, lock_path=tmp_path / "no_lock.json")
    assert r["status"] == "fail"
    assert any("可写操作" in x["msg"] and "reference_graph.py" in x["path"] for x in r["findings"])


def test_zero_llm_gold_loader_readonly_pass(tmp_path):
    """金标装载模块只有读操作 → 该项通过(正控)。"""
    pkg = tmp_path / "src" / "pkg"
    _mk_repo_with_scoring(tmp_path, "from .reference_graph import load\n")
    (pkg / "reference_graph.py").write_text(
        "from pathlib import Path\n"
        "def load(p):\n"
        "    return Path(p).read_text(encoding='utf-8')\n",
        encoding="utf-8")
    r = czl.run_check(tmp_path, lock_path=tmp_path / "no_lock.json")
    assert not [x for x in r["findings"] if "可写操作" in x["msg"]]


# ---------- run_all ----------

def test_run_all_discovery_and_last_json():
    """runner 能发现 ≥3 个子检查且不含自身;last_json_line 提取契约 JSON。"""
    scripts = run_all.discover_checks()
    assert len(scripts) >= 3
    assert all(s.name.startswith("check_") for s in scripts)
    out = '人类摘要行\n{"check":"x","status":"pass","n_pass":1,"n_fail":0,"findings":[]}\n'
    assert run_all.last_json_line(out)["check"] == "x"
    assert run_all.last_json_line("没有 json") is None


def test_run_all_aggregates_real_repo():
    """runner 对真实仓汇总:至少跑出 3 行,状态取值合法(不判 pass/fail,只验管道)。"""
    rows = [run_all.run_one(s, REPO) for s in run_all.discover_checks()]
    assert len(rows) >= 3
    assert all(r["status"] in ("pass", "fail", "error") for r in rows)


# ---------- 真实仓冒烟(只读,保证脚本对本仓资产可用) ----------

def test_real_repo_anchored_on_known_doc():
    """对本仓真实文档(chain14 预注册)跑锚检查:该文档数字全部带锚 → pass。"""
    r = can.run_check(REPO, file_specs=["docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md"])
    assert r["status"] == "pass", r["findings"][:5]
