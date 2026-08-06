"""P0 全量运行入口：三种划分各跑一遍，JSON 落盘 reports/ 下。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.insert(0, os.path.dirname(__file__))

import honest_eval as he

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(OUT_DIR, exist_ok=True)


def main():
    max_cases = int(os.environ.get("P0_MAX_CASES", "0")) or None
    all_agg = {}
    for strat in ("random", "scaffold", "reaction_family"):
        t0 = time.time()
        agg = he.run(strat, max_cases=max_cases)
        agg["elapsed_sec"] = round(time.time() - t0, 1)
        all_agg[strat] = agg
        with open(os.path.join(OUT_DIR, f"p0_{strat}.json"), "w") as f:
            json.dump(agg, f, ensure_ascii=False, indent=2)
        print(f"[DONE] {strat}  {agg['elapsed_sec']}s -> reports/p0_{strat}.json", flush=True)
    with open(os.path.join(OUT_DIR, "p0_all.json"), "w") as f:
        json.dump(all_agg, f, ensure_ascii=False, indent=2)
    print("[ALL DONE] -> reports/p0_all.json", flush=True)


if __name__ == "__main__":
    main()
