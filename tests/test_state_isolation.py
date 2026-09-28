"""State 迭代隔离回归测试。

真实事故(2026-09-25 dev 批跑 pb_0065 首跑暴露):select_frontier 不清理
上一路径的 ``predicted_evidence_id`` 等引用 → 下一路径的 validate/commit
读到陈旧 ID,在当前路径检索集找不到,误入提案卡分支 KeyError
('proposed_card');若陈旧 ID 恰好也在新检索集里则会**静默提交错误证据卡**。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from wf_helpers import (  # noqa: E402
    CATECHOL,
    evidence,
    fake_model,
    rank_response,
    run_scripted,
)


def test_predicted_evidence_id_does_not_leak_across_iterations(tmp_path):
    """路径 A(模型 rank 选卡提交)→ 子路径 B(唯一 recorded 确定性提交):
    B 的事件必须用 B 自己的证据卡,不得受 A 的选中 ID 影响。"""
    A = CATECHOL
    B1, B2 = "CC=O", "C=CO"           # A 的两个候选产物(两条 recorded 卡竞争)
    C = "CC(O)C"                      # B1 的唯一 recorded 产物
    cards_a1 = evidence("recA1", "recorded_reaction", cn_identity(A), [B1],
                        rank=1)
    cards_a2 = evidence("recA2", "recorded_reaction", cn_identity(A), [B2],
                        rank=2)
    cards_b = evidence("recB1", "recorded_reaction", cn_identity(B1), [C],
                       rank=1)
    scripted = {
        cn_identity(A): [cards_a1, cards_a2],
        cn_identity(B1): [cards_b],
    }
    model = fake_model(script={
        "rank_candidates": [rank_response("E-recA1")],
    })
    summary, runs_root = run_scripted(
        "r-leak", scripted, smiles=A, max_depth=2, max_expansions=4,
        max_frontier_width=3, runs_root=tmp_path, model=model,
        max_llm_calls=4, max_proposals=4)
    assert summary["stop_reason"] in ("completed", "awaiting_prediction")
    # A 经模型选卡提交 B1;B1 的确定性提交必须用 recB1,而非 A 的 E-recA1
    rep_path = runs_root / "r-leak" / "report" / "pathway.json"
    rep = __import__("json").loads(rep_path.read_text(encoding="utf-8"))
    events_by_parent = {}
    for ev in rep["reaction_events"]:
        events_by_parent.setdefault(ev["parent_path_id"], []).append(ev)
    b1_events = [e for p, evs in events_by_parent.items()
                 for e in evs
                 if p in {pi["path_id"] for pi in rep["path_instances"]
                          if pi["depth"] == 1
                          and pi["substrate_identity"] == cn_identity(B1)}]
    assert b1_events, "B1 路径必须有已提交事件"
    assert all(e["evidence_id"] == "E-recB1" for e in b1_events), \
        "B1 事件证据卡必须是其自己的 recorded 卡(迭代泄漏会把 A 的选中卡带过来)"
    # A 路径事件 = 模型选中的 E-recA1
    a_events = [e for p, evs in events_by_parent.items()
                for e in evs
                if p in {pi["path_id"] for pi in rep["path_instances"]
                         if pi["depth"] == 0}]
    assert a_events and a_events[0]["evidence_id"] == "E-recA1"
