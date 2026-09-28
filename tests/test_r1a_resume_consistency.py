"""R1-a 冷跑 vs 合法 resume 一致性(任务书 §2.3;无凭证无网络)。

对未受历史污染的新 run 做完整 检索→资格→decision→恢复→导出 路径:

- 冷跑与合法 resume(中途硬杀后恢复)的资格块、事件与导出 SHA 一致;
  硬杀经独立子进程注入(os._exit 不杀 pytest 本体);
- 哈希已不匹配的旧 run(int 键事故现场)不能靠新代码 resume 当作
  已修好 —— 完整性守卫必须拒绝,不改旧信封哈希。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

DRIVER = Path(__file__).parent / "recovery_driver.py"


def _driver(mode: str, runs_root: Path, run_id: str, smiles: str,
            scripted: Path, *,
            crash_after: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    cmd = [sys.executable, str(DRIVER), mode,
           "--runs-root", str(runs_root), "--run-id", run_id,
           "--smiles", smiles, "--scripted", str(scripted),
           "--model", "off", "--max-depth", "1",
           "--max-expansions", "2", "--max-frontier-width", "3"]
    if crash_after:
        cmd += ["--crash-after", crash_after]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                          env=env)


def _summary(proc) -> dict:
    for line in proc.stdout.splitlines():
        if line.startswith("SUMMARY "):
            return json.loads(line[len("SUMMARY "):])
    raise AssertionError(f"驱动无 SUMMARY 输出:{proc.stdout[-2000:]} "
                         f"{proc.stderr[-2000:]}")


def _scripted_fixture(tmp_path: Path) -> Path:
    """带 donor_refs 的类比卡(走资格块/decision 落盘路径)。"""
    from tests.test_reactant_similar import _fx
    from pathway_v43.domain.identity import cn_identity

    fx = _fx("F1_full_donor_exact")
    ident = cn_identity(fx["substrate_smiles"])
    card = {
        "evidence_id": "E-analog", "kind": "analog_reaction",
        "substrate_identity": ident,
        "products": [{"product_identity": "CCCO"}],
        "donor_refs": [dict(fx["donor"])],
        "mapping_status": "resolved",
    }
    p = tmp_path / "scripted.json"
    p.write_text(json.dumps({ident: [card]}), encoding="utf-8")
    return p


def _events_snapshot(run_dir: Path) -> dict:
    report = json.loads((run_dir / "report" / "pathway.json").read_text(
        encoding="utf-8"))
    return {e["event_id"]: {k: e[k] for k in (
        "evidence_id", "evidence_kind", "path_id")}
        for e in report.get("reaction_events", [])}


def _eligibility_snapshot(run_dir: Path) -> list:
    """资格块内容快照(task_id 键含 run_id,跨 run 不可比;按内容排序)。"""
    from pathway_v43.domain.models import canonical_json

    blocks = []
    for f in sorted((run_dir / "results").glob("*/decision.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))["payload"]
        if "analogy_eligibility" in payload:
            blocks.append(canonical_json(
                payload["analogy_eligibility"]))
    return sorted(blocks)


def _export_sha(runs_root: Path, run_id: str) -> str:
    from pathway_v43.output.export_v3 import export_run_v3

    result = export_run_v3(runs_root, run_id, route_id="pb-test", policy={})
    return result["predictions_sha256"]


def test_cold_run_and_crash_resume_produce_same_facts(tmp_path):
    """冷跑完整落盘;同身份硬杀后 resume → 事件/资格块/导出 SHA 一致。"""
    from tests.test_reactant_similar import _fx

    fx = _fx("F1_full_donor_exact")
    substrate = fx["substrate_smiles"]
    scripted = _scripted_fixture(tmp_path)

    # ---- 冷跑 ----
    cold_root = tmp_path / "cold" / "runs"
    proc = _driver("run", cold_root, "r1a-cold", substrate, scripted)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = _summary(proc)
    assert summary["stop_reason"] in ("completed", "awaiting_prediction",
                                      "budget_exhausted")
    cold_dir = cold_root / "r1a-cold"
    ev_cold = _events_snapshot(cold_dir)
    el_cold = _eligibility_snapshot(cold_dir)
    sha_cold = _export_sha(cold_root, "r1a-cold")

    # ---- 崩溃恢复:同身份跑到 decision 落盘后硬杀,再 resume ----
    warm_root = tmp_path / "warm" / "runs"
    killed = _driver("run", warm_root, "r1a-warm", substrate, scripted,
                     crash_after="classify_evidence")
    assert killed.returncode == 70, "硬杀注入应 os._exit(70)"
    assert (warm_root / "r1a-warm" / "run_identity.json").is_file()
    proc2 = _driver("resume", warm_root, "r1a-warm", substrate, scripted)
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    assert _summary(proc2)["resumed"] is True
    warm_dir = warm_root / "r1a-warm"

    # 事实一致:事件、资格块、导出 SHA(任务书 §2.3 一致性口径)
    assert _events_snapshot(warm_dir) == ev_cold
    assert _eligibility_snapshot(warm_dir) == el_cold
    assert _export_sha(warm_root, "r1a-warm") == sha_cold

    # ---- 合法 resume 幂等:已完成的 run 再 resume 不改产物 ----
    before = {p.name: p.read_bytes()
              for p in (cold_dir / "results").glob("*/decision.json")}
    proc3 = _driver("resume", cold_root, "r1a-cold", substrate, scripted)
    assert proc3.returncode == 0, proc3.stdout + proc3.stderr
    after = {p.name: p.read_bytes()
             for p in (cold_dir / "results").glob("*/decision.json")}
    assert after == before, "合法 resume 不得重写已落盘产物"
    assert _export_sha(cold_root, "r1a-cold") == sha_cold


def test_corrupted_old_run_cannot_resume_as_fixed(tmp_path):
    """哈希已不匹配的旧 run(事故现场):resume 必须失败,不修旧信封。"""
    from tests.test_reactant_similar import _fx

    fx = _fx("F1_full_donor_exact")
    substrate = fx["substrate_smiles"]
    scripted = _scripted_fixture(tmp_path)
    runs_root = tmp_path / "runs"
    # 中途硬杀(r1 时序:decision 已落盘、checkpoint 未推进、run 未完成)
    killed = _driver("run", runs_root, "r1a-broken", substrate, scripted,
                     crash_after="classify_evidence")
    assert killed.returncode == 70

    # 把已落盘 decision 的 payload 改成 int 键事故形状(重读必炸)
    decision = next((runs_root / "r1a-broken" / "results").glob(
        "*/decision.json"))
    env = json.loads(decision.read_text(encoding="utf-8"))
    env["payload"]["analogy_eligibility"] = {
        "cards": [], "results_int_key": [{"alignment": {2: 0, 11: 8}}],
    }
    from pathway_v43.domain.models import canonical_json

    tampered = canonical_json(env) + "\n"
    decision.write_text(tampered, encoding="utf-8")

    # resume 必须失败:驱动以非零返回码显式报完整性错误
    proc2 = _driver("resume", runs_root, "r1a-broken", substrate, scripted)
    assert proc2.returncode != 0, "损坏 run 的 resume 不得静默成功"
    combined = proc2.stdout + proc2.stderr
    assert ("完整性校验失败" in combined
            or "ArtifactIntegrityError" in combined), combined[-1000:]

    # 旧信封未被修复代码改写:损坏文件字节原样保留(审计事实不动;
    # int 键经 JSON 序列化在盘上本就是字符串,信封哈希按原 payload 算)
    assert decision.read_text(encoding="utf-8") == tampered
    env_now = json.loads(decision.read_text(encoding="utf-8"))
    assert "results_int_key" in env_now["payload"][
        "analogy_eligibility"], "损坏形状不得被静默修复"
