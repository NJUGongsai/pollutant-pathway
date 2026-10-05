# deep_recall_gate1 — HIT60 T8 门 1:深位召回器纯检索能力测量(零 LLM)

- 执行:2026-09-30,T8 门 1 实施代理。依据:`docs/TASK_V43_HIT60_S1R2_GENERATION_ARMS.md` §1、
  teacher 批复 §四建议 1 先决 1;口径 v3(T6 封存)。
- 红线:零 LLM 零 API;远端 runs 只读;金标仅在 `gate1_measure.py` 离线进程只读;
  封存件零 SMILES(grep 审计过);不碰 298;不改 src;未 commit。
- **题域标签(强制)**:dev = B1 环境路径中间步骤;数字不外推 298(RHEA 题域)。

## 一行结论

引擎原序在 K=16/24/32 已捞出 22 题候选含金中的 **6/10/14 题**(最深 166 位,rank75 案例复核一致);
四种独立信号在 K=16 最多 +5 题(11/22),**K=32 无一超过引擎原序**(符号检验全部 p≥0.125);
按本报告提议的判定线草案(K=32 单一信号 ≥18/22 且显著)→ **门 1 预判不过**,走失败分支(纯检索优化)。
判定线为草案,待用户/teacher 确认后冻结(见 docs/HIT60_T8_GATE1_RECALL_REPORT.md §5)。

## 产物

| 文件 | 内容 |
|---|---|
| `gate1_remote_extract.py` | 远端只读抽取脚本(六批 retrieval.json+cardval → 紧凑 dump) |
| `gate1_measure.py` | 主测量脚本(A 基线/B 信号/符号检验;`--check` 复算) |
| `sealed/gate1_summary.json` | 全部汇总数字(召回表/增益/分布/符号检验/对账) |
| `sealed/gate1_measurements.json` | 逐题表(qid/位次/旗标/信号位次,零 SMILES) |
| `sealed/gold_depth_22.tsv` | 22 题候选含金逐题金标深度(引擎+各信号位次) |
| `sealed/SEAL_MANIFEST.sha256` | 封存 SHA(含输入/金标锚 SHA 与 --check 记录) |
| `raw_dumps/`(gitignored) | 六批检索 dump(含候选分子,金标红线不入仓) |

## 复现

```bash
# 测量(本地 conda depending43;金标只在此进程只读)
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/deep_recall_gate1/gate1_measure.py
# --check 复算(2026-09-30 实测 PASS 2/2)
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/deep_recall_gate1/gate1_measure.py --check
# 重拉原始 dump(远端只读,expect 通道见 docs/CHENYU_ACCESS.md)
python reports/phase_s15_hit60/deep_recall_gate1/gate1_remote_extract.py  # 远端执行
```

## 数据源对账(全部逐数一致)

- in-pool(cardval 审计口径):36/37/36/36/36/37 vs FULL_SURFACE §2 逐臂一致;
  rank75 案例(005-S01,C0-b,uspto 模板卡)复现一致。
- 22 题清单 = qid_flags_C0b.tsv `gold_in_pool & !hit5_whole` = 22,与审计 2x2(15/22/5/14)同源。
- 金标/题卷 SHA 与 COVERAGE_STAT §5、T6 SEAL_MANIFEST 逐一相核。
- 批间稳定性:53/56 题六批检索骨架全同;3 题深位采样抖动(067-S05/135-S06/143-S04),
  金标位次六批全部一致 → 测量结论批不变。
