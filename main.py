# main.py
# EnzymeCrew 入口：底物 → 反应 → 酶 Pool → EnzymeCAGE 排序

import sys
import json
import logging
from pathlib import Path

# 确保项目根在 sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph import compile_graph
from src.state import EnzymeCrewState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enzymecrew")


def run(query: str, mode: str = "m3") -> dict:
    """运行 EnzymeCrew pipeline"""
    logger.info(f"{'='*60}")
    logger.info(f"EnzymeCrew Pipeline Start (mode={mode})")
    logger.info(f"Query: {query}")
    logger.info(f"{'='*60}")

    graph = compile_graph()

    initial_state = EnzymeCrewState(user_query=query, pipeline_mode=mode)
    final_state = graph.invoke(initial_state.model_dump())

    # 输出结果
    if final_state.get("fail_closed") or final_state.get("error"):
        logger.error(f"Pipeline FAILED: {final_state.get('error')}")
        return {
            "status": "failed",
            "error": final_state.get("error"),
            "evidence_chain": [e.model_dump() if hasattr(e, 'model_dump') else e for e in final_state.get("evidence_chain", [])],
        }

    ranked = final_state.get("ranked_enzymes", [])
    logger.info(f"Pipeline SUCCESS: {len(ranked)} enzymes ranked")

    return {
        "status": "success",
        "query": query,
        "substrate_smiles": final_state.get("substrate_info", {}).get("substrate_smiles") if isinstance(final_state.get("substrate_info"), dict) else getattr(final_state.get("substrate_info"), "substrate_smiles", None),
        "pool_route": final_state.get("pool_route_used"),
        "pool_size": final_state.get("pool_size"),
        "ranked_enzymes": [
            {"uid": e.uid, "score": e.score, "rank": e.rank}
            if hasattr(e, "uid") else e
            for e in ranked
        ],
        "evidence_chain": [
            e.model_dump() if hasattr(e, 'model_dump') else e
            for e in final_state.get("evidence_chain", [])
        ],
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py '<query>' [--mode m3|m5]")
        print("Example: python main.py '帮我找能降解己烷(CCCCCC)的酶'")
        print("         python main.py '帮我找能降解己烷(CCCCCC)的酶' --mode m5")
        sys.exit(1)

    query = sys.argv[1]
    mode = "m3"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    result = run(query, mode=mode)
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
