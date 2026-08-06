#!/usr/bin/env bash
# 三划分 × {smarts, union} 全量对比 + 失败归因。结果写 reports/p0_attrib/。
set -u
cd "$(dirname "$0")"
export PYTHONPATH=../core
OUT=../reports/p0_attrib
mkdir -p "$OUT"
for strat in random scaffold reaction_family; do
  for gen in smarts union; do
    echo "=== $strat / $gen ==="
    python honest_eval.py --strategy "$strat" --generator "$gen" \
      --out "$OUT/${strat}_${gen}.json" > "$OUT/${strat}_${gen}.log" 2>&1
    echo "done $strat/$gen exit=$?"
  done
done
echo "ALL_DONE"
