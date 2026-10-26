# -*- coding: utf-8 -*-
"""bible_checks 第二批 A 组自测:probe-before-build / batch-discipline / loss-attribution。

临时目录造正/反例,断言 status、findings、MODE 行与 JSON 契约。
跑法: ~/miniconda3/envs/depending43/bin/python -m pytest tests/test_bible_checks_batch2a.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "bible_checks"))

import check_batch_discipline as cbd  # noqa: E402
import check_loss_attribution as cla  # noqa: E402
import check_probe_before_build as cpb  # noqa: E402


def _write(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ---------- check_probe_before_build ----------

GOOD_PROBE = """# X 面数探针（2026-10-26）
- 性质：零模型零网络只读探针；探针≠预注册≠成绩。
- 产物：reports/ev/attr_probe.py（自包含可复现）。
- 判定：新增 12 题 > 0，过门，成立 → 立项。
"""

PROBE_NO_GATE = """# Y 面数探针
- 零模型零 API 只读探针。
- 产物见 reports/ev/attr_probe.py。
- 出数：新增 12 题。
"""

PROBE_NO_ZEROLLM = """# Z 面数探针
- 产物见 reports/ev/attr_probe.py。
- 判定：不成立，结项。
"""


def test_probe_report_pass(tmp_path):
    """零 LLM 声明 + 门结论 + 真实证据文件 → pass。"""
    _write(tmp_path, "reports/ev/attr_probe.py", "print('probe')")
    _write(tmp_path, "docs/PROBE_X_RESULT_2026-10-26.md", GOOD_PROBE)
    r = cpb.run_check(tmp_path)
    assert r["status"] == "pass" and r["n_fail"] == 0
    assert r["n_pass"] >= 3  # 声明/门结论/证据引用三个子检查


def test_probe_report_missing_gate_fails(tmp_path):
    """报告存在但无通过门结论 → fail(CC 拍板规则)。"""
    _write(tmp_path, "reports/ev/attr_probe.py", "print('probe')")
    _write(tmp_path, "docs/PROBE_Y_RESULT.md", PROBE_NO_GATE)
    r = cpb.run_check(tmp_path)
    assert r["status"] == "fail"
    assert any("无通过门结论" in f["msg"] for f in r["findings"])


def test_probe_report_missing_zero_llm_fails(tmp_path):
    """报告无零模型调用声明 → fail。"""
    _write(tmp_path, "reports/ev/attr_probe.py", "print('probe')")
    _write(tmp_path, "docs/PROBE_Z_RESULT.md", PROBE_NO_ZEROLLM)
    r = cpb.run_check(tmp_path)
    assert r["status"] == "fail"
    assert any("零模型调用声明" in f["msg"] for f in r["findings"])


def test_probe_evidence_path_must_exist(tmp_path):
    """引用的证据文件磁盘上不存在 → fail(不许编造出处)。"""
    _write(tmp_path, "docs/PROBE_W_RESULT.md",
           "零模型只读探针。\n产物 reports/ev/missing.py。\n判定:成立。")
    r = cpb.run_check(tmp_path)
    assert r["status"] == "fail"
    assert any("未引用任何磁盘可定位的证据文件" in f["msg"] for f in r["findings"])


def test_probe_no_docs_at_all_fails(tmp_path):
    """仓里没有任何探针文档 → fail(缺报告)。"""
    (tmp_path / "docs").mkdir()
    r = cpb.run_check(tmp_path)
    assert r["status"] == "fail"
    assert any("未找到任何探针文档" in f["msg"] for f in r["findings"])


def test_probe_task_brief_without_gate_is_note_only(tmp_path):
    """TASK_ 任务书无门结论只附注不判 fail(尚未执行属正常)。"""
    _write(tmp_path, "docs/TASK_P_PROBE.md", "零模型只读探针任务书,先证面数非空。")
    r = cpb.run_check(tmp_path)
    assert r["status"] == "pass"
    assert any("尚未执行属正常" in n for n in r["notes"])


def test_probe_plan_files_claim_needs_probe_source(tmp_path):
    """--files 方案 md:增面数字 ±2 行无探针出处 → fail;有出处 → pass。"""
    _write(tmp_path, "reports/ev/attr_probe.py", "p")
    _write(tmp_path, "docs/PROBE_OK.md", GOOD_PROBE)  # 避免「缺报告」干扰
    _write(tmp_path, "docs/plan_bad.md", "预期给普通门候选补声明,新增 55 题收益。")
    _write(tmp_path, "docs/plan_good.md", "探针实测新增 55 题(逐行清单见 evidence)。")
    r = cpb.run_check(tmp_path, file_specs=["docs/plan_bad.md", "docs/plan_good.md"])
    assert r["status"] == "fail"
    bad = [f for f in r["findings"] if "plan_bad" in f["path"]]
    good = [f for f in r["findings"] if "plan_good" in f["path"]]
    assert len(bad) == 1 and bad[0]["line"] == 1 and not good


# ---------- check_batch_discipline ----------

def _arm(tmp_path: Path, name: str, orch: dict, den: int = 10, n_per: int = 10):
    d = tmp_path / "batch" / name
    d.mkdir(parents=True)
    (d / "orchestration.json").write_text(json.dumps(orch), encoding="utf-8")
    (d / "metrics.json").write_text(json.dumps({
        "denominator": den,
        "per_qid": [{"qid": f"q{i}", "main": {"rank": 1}} for i in range(n_per)],
    }), encoding="utf-8")
    return d


def test_batch_two_arms_single_variable_pass(tmp_path):
    """两臂 orchestration 归一化 diff 恰 1 字段 → pass,附注点名单变量。"""
    common = {"workers": 8, "gate_rpm": 200}
    _arm(tmp_path, "chain14_a", {**common, "evidence_card_enabled": False,
                                 "frozen_at": "2026-10-16T03:17:41+00:00",
                                 "runs_root": "/hpc/runs/chain14a_s5b"})
    _arm(tmp_path, "chain14_b", {**common, "evidence_card_enabled": True,
                                 "frozen_at": "2026-10-16T03:17:44+00:00",
                                 "runs_root": "/hpc/runs/chain14b_s5b"})
    r = cbd.run_check(tmp_path, tmp_path / "batch")
    assert r["status"] == "pass" and r["n_fail"] == 0
    assert any("恰 1 个变量: evidence_card_enabled" in n for n in r["notes"])


def test_batch_two_arms_multi_variable_fails(tmp_path):
    """两臂差分 2 个字段 → fail(超单变量)。"""
    common = {"workers": 8}
    _arm(tmp_path, "ch_a", {**common, "evidence_card_enabled": False, "gate_rpm": 200,
                            "runs_root": "/hpc/runs/cha_s5b"})
    _arm(tmp_path, "ch_b", {**common, "evidence_card_enabled": True, "gate_rpm": 300,
                            "runs_root": "/hpc/runs/chb_s5b"})
    r = cbd.run_check(tmp_path, tmp_path / "batch")
    assert r["status"] == "fail"
    assert any("超出单变量" in f["msg"] and "gate_rpm" in f["msg"] for f in r["findings"])


def test_batch_single_arm_fails(tmp_path):
    """单臂无同批对照 → fail(T-H r2 教训)。"""
    _arm(tmp_path, "th_r2", {"workers": 8, "runs_root": "/hpc/runs/thr2"})
    r = cbd.run_check(tmp_path, tmp_path / "batch")
    assert r["status"] == "fail"
    assert any("无同批对照臂" in f["msg"] for f in r["findings"])


def test_batch_denominator_drops_questions_fails(tmp_path):
    """per_qid 行数 ≠ denominator(未评题被丢出分母)→ fail。"""
    common = {"workers": 8, "runs_root": "/hpc/runs/x"}
    _arm(tmp_path, "p_a", dict(common), den=10, n_per=10)
    d = tmp_path / "batch" / "p_b"
    d.mkdir(parents=True)
    (d / "orchestration.json").write_text(json.dumps(dict(common)), encoding="utf-8")
    (d / "metrics.json").write_text(json.dumps({
        "denominator": 10,
        "per_qid": [{"qid": f"q{i}", "main": {"rank": 1}} for i in range(8)],
    }), encoding="utf-8")
    r = cbd.run_check(tmp_path, tmp_path / "batch")
    assert r["status"] == "fail"
    assert any("未评题疑似被丢出分母" in f["msg"] for f in r["findings"])


def test_degraded_doc_pass(tmp_path, capsys):
    """无批根 → MODE=degraded;合规发车书(双臂+唯一差分+298/298)→ pass。"""
    _write(tmp_path, "docs/TI_LAUNCH_2026-10-26.md",
           "# 发车\n双臂 A/B;唯一差分=模型 ID;两臂 298/298 零失败。\n")
    r = cbd.run_check(tmp_path, None)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("MODE=degraded")
    assert r["status"] == "pass" and r["n_fail"] == 0


def test_degraded_doc_effect_claim_without_support_fails(tmp_path, capsys):
    """跨批效应句 ±2 行无区间/换手/降级 → fail。"""
    _write(tmp_path, "docs/TT_RESULT_2026-10-26.md", "本批比基线净 +7 提升。\n下一行无关。\n")
    r = cbd.run_check(tmp_path, None)
    capsys.readouterr()
    assert r["status"] == "fail"
    assert any("无区间/换手/降级声明支撑" in f["msg"] for f in r["findings"])


def test_degraded_doc_multivar_without_disclaimer_fails(tmp_path, capsys):
    """多变量混批且无「不可归因/不作因果」声明 → fail(chain13 教训);有声明放行。"""
    bad = tmp_path / "c1"
    (bad / "docs").mkdir(parents=True)
    (bad / "docs" / "MV_LAUNCH_2026-10-26.md").write_text(
        "本批一起变:C 供给+判据 v2+调用上限 1→3,一次出数。\n", encoding="utf-8")
    r = cbd.run_check(bad, None)
    capsys.readouterr()
    assert r["status"] == "fail"
    assert any("「不可归因/不作因果」" in f["msg"] for f in r["findings"])
    good = tmp_path / "c2"
    (good / "docs").mkdir(parents=True)
    (good / "docs" / "MV2_LAUNCH_2026-10-26.md").write_text(
        "本批一起变:供给+判据+上限;跨批不得称单变量归因,不可归因。\n", encoding="utf-8")
    r2 = cbd.run_check(good, None)
    capsys.readouterr()
    assert not any("「不可归因/不作因果」" in f["msg"] for f in r2["findings"])


def test_degraded_kv_list_and_gate_lines_not_flagged(tmp_path, capsys):
    """降误报回归:kv 列表(净增≥5 进确认)与停点句不是效应主张。"""
    _write(tmp_path, "docs/G_LAUNCH_2026-10-26.md",
           "双臂 A/B;唯一差分=开关;298/298。\n"
           "推进/止损:净增 ≥5 题进确认;strict 净失 ≤−3 停点复盘。\n")
    r = cbd.run_check(tmp_path, None)
    capsys.readouterr()
    assert r["status"] == "pass" and r["n_fail"] == 0


# ---------- check_loss_attribution ----------

def _metrics_arm(tmp_path: Path, name: str, buckets: dict, den: int,
                 ranks: dict, hit1: int):
    d = tmp_path / "reports" / name
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({
        "denominator": den,
        "buckets": buckets,
        "main_caliber": {"hit@1": hit1},
        "per_qid": [{"qid": q, "main": {"rank": r}} for q, r in ranks.items()],
    }), encoding="utf-8")
    return d


def test_loss_closure_and_pairing_pass(tmp_path):
    """桶闭合 + 分母保持 + 两臂逐题配对 diff 真算 → pass。"""
    ranks_a = {"q1": 1, "q2": 2, "q3": 1}
    ranks_b = {"q1": 2, "q2": 1, "q3": 1}
    _metrics_arm(tmp_path, "ch_a", {"matched_strict": 2, "unmatched": 1}, 3, ranks_a, 2)
    _metrics_arm(tmp_path, "ch_b", {"matched_strict": 2, "unmatched": 1}, 3, ranks_b, 2)
    r = cla.run_check(tmp_path, tmp_path / "reports")
    assert r["status"] == "pass" and r["n_fail"] == 0
    assert any("配对 diff" in n and "改善 1 / 退化 1 / 持平 1" in n for n in r["notes"])
    assert any("桶闭合通过 3=2+1" in n for n in r["notes"])


def test_loss_closure_broken_fails(tmp_path):
    """桶合计 ≠ 分母 → fail。"""
    _metrics_arm(tmp_path, "solo", {"a": 5, "b": 6}, 10, {"q1": 1}, 1)
    r = cla.run_check(tmp_path, tmp_path / "reports")
    assert r["status"] == "fail"
    assert any("桶闭合失败" in f["msg"] and "11 ≠ 分母 10" in f["msg"] for f in r["findings"])


def test_loss_paired_diff_mismatch_fails(tmp_path):
    """配对 g−l 与两臂 hit@1 差值不符 → fail(口径不一致信号)。"""
    _metrics_arm(tmp_path, "m_a", {"s": 1, "u": 2}, 3, {"q1": 1, "q2": 2, "q3": 2}, 1)
    _metrics_arm(tmp_path, "m_b", {"s": 1, "u": 2}, 3, {"q1": 1, "q2": 1, "q3": 2}, 2)
    # per-qid 实际 g=1(B 改善 q2), g−l=1,但 hit@1 差=1 → 一致;改成不一致的 hit@1
    d = tmp_path / "reports" / "m_b"
    mm = json.loads((d / "metrics.json").read_text())
    mm["main_caliber"]["hit@1"] = 3  # 谎报
    (d / "metrics.json").write_text(json.dumps(mm), encoding="utf-8")
    r = cla.run_check(tmp_path, tmp_path / "reports")
    assert r["status"] == "fail"
    assert any("hit@1 差值" in f["msg"] for f in r["findings"])


def test_loss_doc_bad_equation_fails_good_passes(tmp_path, capsys):
    """docs 等式:算错 → fail;算对/kv 列表/区间号不误报。"""
    c1 = tmp_path / "c1"
    c2 = tmp_path / "c2"
    _write(c1, "docs/ATTR_BAD_RESULT.md",
           "分母 1585：1585 = 864 + 543 + 178。\n合计 100 = 50 + 40。\n")
    r = cla.run_check(c1, None)
    capsys.readouterr()
    assert r["status"] == "fail"
    assert any("100 ≠ 右侧合计 90" in f["msg"] for f in r["findings"])
    assert not any("1585" in f["msg"] for f in r["findings"])  # 正确等式不报
    _write(c2, "docs/ATTR_KV_RESULT.md",
           "逐题:hit@1 双臂同时命中 77;A 对 B 错 14、A 错 B 对 8。\n"
           "L=14、G=8、both=77。\n自洽:-5 = 13-18 区间读数。\n")
    r2 = cla.run_check(c2, None)
    capsys.readouterr()
    assert not any("算术不符" in f["msg"] for f in r2["findings"])


def test_loss_doc_counter_addition(tmp_path, capsys):
    """计数器(992)进加法 → fail;否定/警示语境豁免。"""
    c1 = tmp_path / "c1"
    c2 = tmp_path / "c2"
    _write(c1, "docs/COUNTER_BAD_RESULT.md", "供给缺口 = 864 + 992 条。\n")
    r = cla.run_check(c1, None)
    capsys.readouterr()
    assert any("计数器" in f["msg"] for f in r["findings"])
    _write(c2, "docs/COUNTER_OK_RESULT.md", "禁止把 864 + 992 相加(重叠 814)。\n")
    r2 = cla.run_check(c2, None)
    capsys.readouterr()
    assert not any("计数器" in f["msg"] for f in r2["findings"])


def test_loss_doc_net_claim_needs_gl(tmp_path, capsys):
    """「净 ±N」结论句无 g/l 三联数 → fail;±2 行有改善/退化 → pass。"""
    c1 = tmp_path / "c1"
    c2 = tmp_path / "c2"
    _write(c1, "docs/NET_BAD_RESULT.md", "strict 119→126,净回收 7 题,修复成功。\n")
    r = cla.run_check(c1, None)
    capsys.readouterr()
    assert r["status"] == "fail"
    assert any("无配套 改善/退化/持平/换手" in f["msg"] for f in r["findings"])
    _write(c2, "docs/NET_OK_RESULT.md",
           "strict 119→126。\n逐题看是 31 题改善、15 题退化(46 换手),净变化只有 +7。\n")
    r2 = cla.run_check(c2, None)
    capsys.readouterr()
    assert not any("无配套" in f["msg"] for f in r2["findings"])


def test_loss_degraded_mode_first_line(tmp_path, capsys):
    """无 metrics JSON → 首行 MODE=degraded,仍对 docs 做结构检查。"""
    _write(tmp_path, "docs/DEG_ATTR_RESULT.md", "桶表见附录,分母 298。\n")
    r = cla.run_check(tmp_path, None)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("MODE=degraded")
    assert any("表格型闭合" in n for n in r["notes"])


# ---------- CLI 契约(子进程级) ----------

def test_cli_contract_last_line_json_and_exit_code(tmp_path):
    """子进程调用:最后一行 JSON 符合契约 schema;fail → 退出码 1。"""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PROBE_BAD_RESULT.md").write_text("没有零模型声明也没有结论。\n", encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "bible_checks" / "check_probe_before_build.py"),
         "--repo", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
    )
    assert cp.returncode == 1
    last = cp.stdout.strip().splitlines()[-1]
    payload = json.loads(last)
    assert set(payload) == {"check", "status", "n_pass", "n_fail", "findings"}
    assert payload["check"] == "probe-before-build" and payload["status"] == "fail"
