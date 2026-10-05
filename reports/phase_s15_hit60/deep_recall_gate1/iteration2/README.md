# iteration2 — HIT60 T8 门 1 失败分支:纯检索信号升级复测(零 LLM)

- 执行:2026-09-30,T8 失败分支执行代理(teacher 预声明:门 1 不过 → 退纯检索
  优化,指纹/模板分调优,全程零 LLM,不升级付费臂)。
- 依据:`docs/TASK_V43_HIT60_S1R2_GENERATION_ARMS.md` §4 失败分支、
  teacher 批复 §四先决 2(独立排序信号,禁按引擎原序扩窗);门 1 基线见
  `docs/HIT60_T8_GATE1_RECALL_REPORT.md` 与上级目录 `sealed/`。
- 口径:与门 1 完全同口径(C0-b 参照批、22 题清单、金标卡判据、K=16/24/32
  三档、符号检验、全 56 护栏);基线复现对拍 PASS(逐题 engine 位次与
  基线 S3 位次与门 1 封存件逐数相等,测量内 assert)。
- 红线:零 LLM 零 API;不改 src/ 与 configs/(信号函数全部在本目录);
  raw_dumps 只读复用;金标仅在 `gate1_iter2_measure.py` 离线进程只读,
  封存件零 SMILES 零身份串;门 1 `sealed/` 只读不覆写(本迭代写
  `iteration2/sealed/` 新目录);不碰 298;未 git commit。
- **题域标签(强制)**:dev = B1 环境路径中间步骤;数字不外推 298(RHEA 题域)。

## 一行结论

33 个新信号配置(全局重排 19 + hybrid 形态 14)复测:**无任何配置达到
门 1 草案主判据(K=32 ≥18/22 且 p<0.05)**;单信号天花板 14→15
(hybrid_s3_taut,+1 题且护栏 +3,但 p=1.0);紧预算档 K=16 最优升至
12/22(+6,p=0.0703,数字线过、显著性仍不达);2 题盲区题 1 题被够到
(023-S03:148→8,MACCS/互变规范指纹),另 1 题 166→41(002-S03,
同分异构簇内选择问题)。**三分支判定落"明显不过"支:宽窗判据下纯检索
优化不足以救深位**,按 teacher 失败分支第 3 档预填 30% 里程碑重估素材,
不自行加臂。详见 `docs/HIT60_T8_GATE1_ITERATION2_REPORT.md`。

## 产物

| 文件 | 内容 |
|---|---|
| `signals2.py` | 新信号函数库(特征层/守恒罚分/通道/校准/排序构造;零金标) |
| `gate1_iter2_measure.py` | 主测量脚本(复用 gate1_measure.py 加载与判定;`--check` 复算) |
| `sealed/iter2_summary.json` | 全部汇总(召回表/符号检验/护栏/基线对照/多重性声明) |
| `sealed/iter2_measurements.json` | 逐题表(qid/位次/守恒特征值/各信号位次,零 SMILES) |
| `sealed/iter2_gold_depth_22.tsv` | 22 题逐题位次表(引擎/基线 S3/新信号主口径) |
| `sealed/SEAL_MANIFEST.sha256` | 本迭代封存 SHA(含门 1 锚引用与 --check 记录) |

## 复现

```bash
# 测量(本地 conda depending43;互变规范化指纹为瓶颈,全程约 10 分钟)
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/deep_recall_gate1/iteration2/gate1_iter2_measure.py
# --check 复算(结果见 sealed/SEAL_MANIFEST.sha256 记录)
OMP_NUM_THREADS=1 PYTHONPATH=src python \
  reports/phase_s15_hit60/deep_recall_gate1/iteration2/gate1_iter2_measure.py --check
```

## 数据源对账

- 输入 dump:与门 1 同一封存 raw_dumps(SHA 见上级 `raw_dumps/DUMP_SHA256.txt`
  与门 1 `sealed/SEAL_MANIFEST.sha256`),只读复用,零重拉。
- 基线复现:测量内 assert 逐题核对 engine 金标位次与基线 S3 位次,与
  门 1 `sealed/gate1_measurements.json` 逐数相等(PASS)。
- 门 1 封存件(`../sealed/`)全程只读;本迭代输出全部写入本目录。
