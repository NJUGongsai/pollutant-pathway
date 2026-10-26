# -*- coding: utf-8 -*-
"""bible_checks 第二批 B 组自测:stop-loss-gate / dual-caliber / review-loop。

跑法: ~/miniconda3/envs/depending43/bin/python -m pytest tests/test_bible_checks_batch2b.py -q

只造临时目录正/反例 + 本仓真实资产冒烟(只读),不碰金标/封存/公共文件。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "bible_checks"))

import check_dual_caliber as cdc  # noqa: E402
import check_review_loop as crl  # noqa: E402
import check_stop_loss_gate as cslg  # noqa: E402


def _write(base, name, text):
    p = base / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------- check_stop_loss_gate ----------

def _mk_batch_metrics(base, hit=89, rate=0.2987, pass_lines=None, denom=298):
    m = {"main_caliber": {"hit@1": hit, "hit@1_rate": rate}, "denominator": denom}
    if pass_lines:
        m["main_caliber"]["pass_lines"] = pass_lines
    return _write(base, "metrics.json", json.dumps(m))


def test_stoploss_batch_unmet_with_recheck_in_docs_passes(tmp_path):
    """批根模式:metrics 未达 pass_lines,批根无回查,docs/ 结果报告有回查 → pass。"""
    batch = tmp_path / "reports" / "t_x_20261026r2"
    batch.mkdir(parents=True)
    _mk_batch_metrics(batch, hit=89, pass_lines={"hit@1": 116})
    _write(tmp_path / "docs", "T_X_RESULT_2026-10-26.md",
           "# T-X 结果\n批:`t_x_20261026r2`\n"
           "## 回查\n逐桶配对:净 +2(18 改善/16 退化),与噪声同量级。\n")
    r = cslg.run_check(tmp_path, batch=batch)
    assert r["status"] == "pass", r["findings"]
    assert any("T_X_RESULT" in n for n in r["notes"])  # 回查在 docs/ 找到
    assert any("未达线" in n for n in r["notes"])


def test_stoploss_batch_unmet_without_recheck_fails(tmp_path):
    """批根模式:未达线且批根与 docs/ 均无回查记录 → fail。"""
    batch = tmp_path / "reports" / "t_y_20261026"
    batch.mkdir(parents=True)
    _mk_batch_metrics(batch, hit=50, pass_lines={"hit@1": 116})
    (tmp_path / "docs").mkdir()
    r = cslg.run_check(tmp_path, batch=batch)
    assert r["status"] == "fail"
    assert any("未发现回查记录" in f["msg"] for f in r["findings"])


def test_stoploss_batch_met_needs_no_recheck(tmp_path):
    """批根模式:实测过线(达标)→ 不要求回查,pass。"""
    batch = tmp_path / "reports" / "t_z_20261026"
    batch.mkdir(parents=True)
    _mk_batch_metrics(batch, hit=120, rate=0.4027, pass_lines={"hit@1": 116})
    (tmp_path / "docs").mkdir()
    r = cslg.run_check(tmp_path, batch=batch)
    assert r["status"] == "pass" and not r["findings"]


def test_stoploss_batch_not_found_is_error(tmp_path):
    r = cslg.run_check(tmp_path, batch=tmp_path / "nope")
    assert r["status"] == "error"


def test_stoploss_degraded_unmet_no_recheck_fails(tmp_path):
    """降级模式:结果报告未达线且无回查 → fail;MODE=degraded 进 notes。"""
    _write(tmp_path / "docs", "T_A_RESULT_2026-10-26.md",
           "# 结果\n预注册线:hit@1 ≥ 50%。\n实测:本批 60/298。\n结论:本批显著低于线。\n")
    r = cslg.run_check(tmp_path, batch=None)
    assert r["status"] == "fail"
    assert any(n.startswith("MODE=degraded") for n in r["notes"])
    assert any("未发现回查记录" in f["msg"] for f in r["findings"])


def test_stoploss_degraded_unmet_with_recheck_passes(tmp_path):
    _write(tmp_path / "docs", "T_B_RESULT_2026-10-26.md",
           "# 结果\n判定线:hit@1 ≥ 50%。\n实测 hit@1 60/298。\n"
           "回查:逐桶配对净 -3,不再续跑。\n")
    r = cslg.run_check(tmp_path, batch=None)
    assert r["status"] == "pass", r["findings"]


def test_stoploss_claim_without_negation_fails(tmp_path):
    """未达线 + 未加否定的宣称句 → fail,finding 带「需人工复核」。"""
    _write(tmp_path / "docs", "T_C_RESULT_2026-10-26.md",
           "# 结果\n判定线:hit@1 ≥ 50%。\n实测 hit@1 60/298。\n"
           "回查:配对完成。\n修复有效,带来了 10 题的提升。\n")
    r = cslg.run_check(tmp_path, batch=None)
    assert r["status"] == "fail"
    hit = [f for f in r["findings"] if "需人工复核" in f["msg"]]
    assert hit and "宣称" in hit[0]["msg"]


def test_stoploss_claim_negated_is_clean(tmp_path):
    """未达线 + 否定式表述(不能宣称)→ 不算宣称违规。"""
    _write(tmp_path / "docs", "T_D_RESULT_2026-10-26.md",
           "# 结果\n判定线:hit@1 ≥ 50%。\n实测 hit@1 60/298。\n"
           "回查:配对完成。\n净增益与噪声同量级,不能宣称修复有效。\n")
    r = cslg.run_check(tmp_path, batch=None)
    assert r["status"] == "pass", r["findings"]


def test_stoploss_unparseable_line_fails_and_le_form_partial(tmp_path):
    """强判定线措辞但无数值 → fail;净失型停点(≤−N)→ 识别不误判。"""
    r1_docs = tmp_path / "r1" / "docs"
    _write(r1_docs, "T_E_RESULT_2026-10-26.md",
           "# 结果\n判定线见预注册(原文引用略)。\n实测感觉不错。\n")
    r = cslg.run_check(tmp_path / "r1", batch=None)
    assert r["status"] == "fail"
    assert any("判定线数值不可解析" in f["msg"] for f in r["findings"])
    r2_docs = tmp_path / "r2" / "docs"
    _write(r2_docs, "T_F_RESULT_2026-10-26.md",
           "# 结果\n停点纪律:任一分族 strict 净失 ≤−3 停点复盘。\n")
    r2 = cslg.run_check(tmp_path / "r2", batch=None)
    assert r2["status"] == "pass"
    assert any("净失/上限型停点" in n for n in r2["notes"])


def test_stoploss_real_repo_smoke():
    """本仓真实资产冒烟:降级跑通,状态合法,关键附注在。"""
    r = cslg.run_check(REPO, batch=None)
    assert r["status"] in ("pass", "fail")
    assert any(n.startswith("MODE=degraded") for n in r["notes"])


# ---------- check_dual_caliber ----------

def test_dualcaliber_batch_manifest_ok_pass(tmp_path):
    """批根模式:双口径 .vN 留存 + SHA256SUMS 全对 → pass。"""
    batch = tmp_path / "b1"
    batch.mkdir()
    _write(batch, "metrics.json", '{"main_caliber": {"hit@1": 89}}')
    _write(batch, "metrics.json.v1", '{"main_caliber": {"hit@1": 84}}')
    _write(batch, "report.md", "## 主口径\n89\n## 老口径敏感性\n141\n")
    lines = []
    for name in ["metrics.json", "metrics.json.v1", "report.md"]:
        h = hashlib.sha256((batch / name).read_bytes()).hexdigest()
        lines.append(f"{h}  ./{name}")
    _write(batch, "SHA256SUMS", "\n".join(lines) + "\n")
    r = cdc.run_check(tmp_path, batch=batch)
    assert r["status"] == "pass", r["findings"]
    assert any("双口径留存" in n for n in r["notes"])


def test_dualcaliber_batch_overwrite_fails(tmp_path):
    """批根模式:封存清单哈希不符 = 疑似原地覆写 → fail。"""
    batch = tmp_path / "b2"
    batch.mkdir()
    _write(batch, "metrics.json", '{"v": 2}')
    _write(batch, "metrics.json.v1", '{"v": 1}')
    h = hashlib.sha256(b'{"v": 0}')  # 与磁盘实际不符的声称哈希
    _write(batch, "SHA256SUMS", f"{h.hexdigest()}  ./metrics.json.v1\n")
    r = cdc.run_check(tmp_path, batch=batch)
    assert r["status"] == "fail"
    assert any("覆写" in f["msg"] or "哈希不符" in f["msg"] for f in r["findings"])


def test_dualcaliber_batch_change_without_retention_fails(tmp_path):
    """批根模式:声明口径变更(criteria_v2)但无任何 .vN 留存 → fail。"""
    batch = tmp_path / "b3"
    batch.mkdir()
    _write(batch, "metrics.json", json.dumps({"criteria_v2": {"exemption_enabled": True}}))
    r = cdc.run_check(tmp_path, batch=batch)
    assert r["status"] == "fail"
    assert any("留存" in f["msg"] for f in r["findings"])


def test_dualcaliber_degraded_label_check(tmp_path):
    """降级模式:数字带口径标签 → pass;远离标签的裸读数 → fail(带行号)。

    (口径标签窗口 ±3 行:裸读数要放得比窗口远,才构成本检查语义下的违规。)
    """
    _write(tmp_path / "docs", "T_G_RESULT_2026-10-26.md",
           "# 结果\n"
           "- 主口径 hit@1 87/298(v2)。\n"
           "- 老口径敏感性 141(47.32%)。\n"
           "\n\n\n\n"
           "- 裸读数 12.5% 无任何计量标记。\n")
    r = cdc.run_check(tmp_path, file_specs=["docs/T_G_RESULT_2026-10-26.md"])
    assert r["status"] == "fail"
    fd = [f for f in r["findings"] if "口径标签" in f["msg"]]
    assert fd and fd[0]["line"] == 8 and "12.5%" in fd[0]["msg"]


def test_dualcaliber_degraded_cross_caliber_sentence(tmp_path):
    """降级模式:无守卫的跨口径比较 → fail;带守卫(不能/分账)→ pass。"""
    _write(tmp_path / "docs", "T_H_RESULT_2026-10-26.md",
           "# 结果\n老口径 145 比主口径只差 4,可以兑换。\n")
    r = cdc.run_check(tmp_path, file_specs=["docs/T_H_RESULT_2026-10-26.md"])
    assert any("跨口径" in f["msg"] for f in r["findings"])
    _write(tmp_path / "docs", "T_I_RESULT_2026-10-26.md",
           "# 结果\n老口径 145 与主口径不能直接比,差额不构成还差 4 题;两口径并列披露。\n")
    r2 = cdc.run_check(tmp_path, file_specs=["docs/T_I_RESULT_2026-10-26.md"])
    assert not [f for f in r2["findings"] if "跨口径" in f["msg"]]


def test_dualcaliber_real_batch_and_repo():
    """真实资产:T-H r2 批根应 pass(26 件清单全对 + 三版本留存);降级跑通。"""
    r = cdc.run_check(REPO, batch=REPO / "reports/ppv1_s5b/t_h_2026-10-20/r2")
    assert r["status"] == "pass", r["findings"]
    r2 = cdc.run_check(REPO, batch=None)
    assert r2["status"] in ("pass", "fail")
    assert any(n.startswith("MODE=degraded") for n in r2["notes"])


# ---------- check_review_loop ----------

GOOD_QWEN = """# X 复审(qwen3.8max 代 Codex,2026-10-26)

> provenance:qwen3.8max 代 Codex 复审,按 CC 2026-10-26 指示执行;
> 不冒充 Codex 本人,不替代正链最终复核权,CC 后置复核项见 §7。
> 实际 HEAD `11aeeafded1b41185f24de49767933709aad49db`。

结论:放行(附条件)。采信到与程序证据互证为止。
"""

UNMARKED_QWEN = """# X 设计复审(2026-10-26)

结论:放行。理由略。
"""


def test_reviewloop_good_substitute_passes(tmp_path):
    _write(tmp_path / "docs", "T_X_QWEN_REVIEW_2026-10-26.md", GOOD_QWEN)
    r = crl.run_check(tmp_path)
    assert r["status"] == "pass", r["findings"]
    assert r["n_pass"] == 3  # provenance + 代审三要素 + 互证


def test_reviewloop_unmarked_substitute_fails(tmp_path):
    _write(tmp_path / "docs", "T_Y_QWEN_REVIEW_2026-10-26.md", UNMARKED_QWEN)
    r = crl.run_check(tmp_path)
    assert r["status"] == "fail"
    assert any("代审未标注" in f["msg"] for f in r["findings"])


def test_reviewloop_missing_provenance_fails(tmp_path):
    _write(tmp_path / "docs", "T_Z_REVIEW_2026-10-26.md",
           "# 某评审\n结论:不放行,发现 2 项 P1。互证后采信。\n")
    r = crl.run_check(tmp_path)
    assert any("通道/模型标识" in f["msg"] for f in r["findings"])


def test_reviewloop_requests_excluded(tmp_path):
    """评审请求(*REQUEST*)与任务书不入评审报告集。"""
    _write(tmp_path / "docs", "T_W_CODEX_REVIEW_REQUEST_2026-10-26.md",
           "# 请求\n禁金标、只读边界。\n")
    _write(tmp_path / "docs", "TASK_SOMETHING_REVIEW_2026-10-26.md", "# 任务书\n")
    files = crl.discover_reports(tmp_path)
    assert files == []


def test_reviewloop_mutual_missing_fails(tmp_path):
    _write(tmp_path / "docs", "T_V_QWEN_REVIEW_2026-10-26.md",
           "# 复审(qwen3.8max 代 Codex)\n> 按 CC 2026-10-26 指示;后置复核见 §7。\n"
           "结论:放行。\n")
    r = crl.run_check(tmp_path)
    assert any("互证" in f["msg"] for f in r["findings"])


def test_reviewloop_real_repo_exemplars_pass():
    """真实正控:bible 点名的代审范本三项全过;mimo 通道件过 provenance+互证
    (代 Codex 三要素不适用通道 A,不加分也不 finding)。"""
    np_, fd = crl.check_report(REPO / "docs" / "T_I_C8_STOP_QWEN_DECISION_2026-10-21.md")
    assert fd == [] and np_ == 3
    np2, fd2 = crl.check_report(REPO / "docs" / "mimo_ppv1_chem_review_response_r36.md")
    assert fd2 == [] and np2 == 2


def test_reviewloop_real_repo_smoke():
    """真实仓全量:跑通、状态合法、扫描数量在预期量级(>100 份)。"""
    r = crl.run_check(REPO)
    assert r["status"] in ("pass", "fail")
    assert len(r["findings"]) >= 1  # 历史欠账真实存在(见回传报告)
    assert any("评审报告" in n for n in r["notes"])


# ---------- main() 契约集成(首行 MODE + 末行 JSON + 退出码) ----------

def test_main_contract_last_json_and_mode(capsys):
    assert cslg.main(["--repo", str(tmp_repo(cslg, "sl"))]) in (0, 1, 2)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("MODE=")
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["check"] == "stop-loss-gate"
    assert set(payload) == {"check", "status", "n_pass", "n_fail", "findings"}


def tmp_repo(mod, tag):
    """main 集成用最小仓:docs/ 只放一份无判定线报告,保证可确定性跑完。"""
    import tempfile
    base = Path(tempfile.mkdtemp(prefix=f"bible_{tag}_"))
    _write(base / "docs", "R_RESULT.md", "# R\n普通结论文档。\n")
    _write(base / "docs", "REVIEW_R_2026-10-26.md",
           "# 评审\n> qwen3.8max 代 Codex,按 CC 2026-10-26 指示;后置复核见 §7。\n"
           "采信到与程序证据互证为止。\n")
    return base
