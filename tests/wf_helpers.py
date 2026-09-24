"""工作流测试共享夹具:脚本证据构造器与常见剧本。

规范分子身份统一用 domain.identity.cn_identity(与引擎同口径),
所以夹具在真实与合成检索之间可复用。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.services.reaction_finder import (  # noqa: E402
    ScriptedReactionFinder,
)
from pathway_v43.workflow import start_run  # noqa: E402

CATECHOL = "Oc1ccccc1O"


def evidence(
    rid: str,
    kind: str,
    reactant_identity: str,
    products: list[str],
    *,
    rank: int = 1,
    match_type: str = "exact_donor_cn_match",
    condition_fit: str = "unknown",
    query_identity: str | None = None,
    score: float = 0.9,
    extra: dict | None = None,
) -> dict:
    """构造一张证据卡(字段与真实 EngineReactionFinder 输出同构)。

    extra:附加字段(donor_refs/mapping_status 等 v2 字段)逐键覆盖。"""
    card = {
        "evidence_id": f"E-{rid}",
        "source_id": rid,
        "kind": kind,
        "query_identity": query_identity or reactant_identity,
        "match_type": match_type,
        "reactant_smiles": reactant_identity,
        "reactant_identity": reactant_identity,
        "products": [
            {"position": i, "product_smiles": s, "product_smiles_full": s,
             "product_identity": cn_identity(s), "score": score,
             "score_semantics": "fixture"}
            for i, s in enumerate(products)
        ],
        "atom_mapping": "unavailable",
        "condition_fit": condition_fit,
        "retrieval_rank": rank,
        "score": score,
        "score_semantics": "fixture",
        "source_record": {
            "donor_exact_match": kind == "recorded_reaction",
            "btid": rid.split("#")[0],
        },
        "asset_file": "fixtures://scripted",
        "asset_sha256": "0" * 64,
    }
    card.update(extra or {})
    return card


def run_scripted(
    run_id: str,
    scripted: dict[str, list[dict]],
    *,
    smiles: str = CATECHOL,
    max_depth: int = 2,
    max_expansions: int = 10,
    max_frontier_width: int = 3,
    runs_root: Path | None = None,
    model=None,
    crash_after: str | None = None,
    max_llm_calls: int = 0,
    max_proposals: int = 0,
) -> tuple[dict, Path]:
    """在临时目录跑一个 scripted run,返回 (summary, runs_root)。

    model:ModelSetup(fake 等);None = 纯确定性(第一阶段语义)。
    """
    if runs_root is None:
        runs_root = Path(tempfile.mkdtemp()) / "runs"
    summary = start_run(
        config=resolve_config(), runs_root=runs_root, run_id=run_id,
        smiles=smiles, max_depth=max_depth, max_expansions=max_expansions,
        max_frontier_width=max_frontier_width,
        finder=ScriptedReactionFinder(scripted), scripted=True,
        model=model, crash_after=crash_after,
        max_llm_calls=max_llm_calls, max_proposals=max_proposals,
    )
    return summary, runs_root


def fake_model(script: dict[str, list[str]] | None = None,
               counter_path: str | Path | None = None,
               default_by_mode: dict[str, str] | None = None):
    """构造 fake ModelSetup(剧本响应 + 跨进程计数)。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup

    return resolve_model_setup(
        "fake", fake_script=script or {},
        fake_counter_path=counter_path,
        fake_default_by_mode=default_by_mode or {},
    )


def rank_response(evidence_id: str, reasons: dict | None = None,
                  reason: str = "选中检索首位的已记录反应") -> str:
    import json

    return json.dumps({
        "decision": "select", "evidence_id": evidence_id,
        "order": [evidence_id], "reasons": reasons or {},
        "reason": reason,
    }, ensure_ascii=False)


def novel_response(products: list[dict],
                   uncertainty: str = "high",
                   reason: str = "无可用证据,受约束提案") -> str:
    import json

    return json.dumps({
        "decision": "propose", "products": products,
        "uncertainty": uncertainty, "reason": reason,
    }, ensure_ascii=False)


def load_report(runs_root: Path, run_id: str) -> dict:
    import json

    path = runs_root / run_id / "report" / "pathway.json"
    return json.loads(path.read_text(encoding="utf-8"))
