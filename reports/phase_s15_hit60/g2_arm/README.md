# g2_arm/ — T8 G2 novel 守恒过滤 + 自排序(实施全链条产物;v2 修订轮)

> 2026-09-30 v1 实施 / 2026-10-05 **v2 修订**(mimo 终版评审 9 必改,
> `docs/mimo_g2_rules_final_review_response.md`),T8 G2 代理,零 LLM
> 零 API(¥0)。判据终版与判定线见
> [PREREGISTRATION_G2.md](PREREGISTRATION_G2.md)(v2 DRAFT,§0 修订记录
> 逐条对 9 必改;待 mimo delta 确认 + 用户冻结)。设计报告:
> `docs/HIT60_T8_G2_DESIGN_REPORT.md` §9(+_PLAIN.md v2 节)。

| 文件 | 内容 |
|---|---|
| `PREREGISTRATION_G2.md` | 预注册 v2:§0 修订记录(9 必改逐条落法)、四步冻结判据终版(机器可读附录 A v2)、臂定义(单变量开关)、判定线(cn@1 净赢 ≥3 + spurious 净降 ≥3)、离线重放定位声明(in-sample 非确证) |
| `offline_replay.py` | 离线重放驱动(判据 v43-cons-2):六批封存答卷 → 同一判据函数过滤+自排序 → 口径 v3 重算(分母 51;答案 SHA 与封存锚定 fail-closed;hold 分账;v1 副本在场时自动生成 v1/v2 对照;`--check` 复算) |
| `replay_summary.json` | v2 臂级汇总:逐批 @1/@3/@5/spurious/空答/hold/降位、判定对净赢题、健全性预检(金标落剔除档 = 0) |
| `replay_per_question.tsv` | v2 逐题表(qid、原位次→新位次、降位/剔除/hold 标记;**零 SMILES**) |
| `replay_candidate_details.json` | v2 逐候选守恒判定明细(档位/规则/变换类/dC_main/碎片重构证据;零 SMILES) |
| `replay_summary_v1.json` 等 `*_v1.*` | v1 判据(v43-cons-1)重放产物副本(2026-09-30),与 v2 对照用 |
| `replay_v1_v2_comparison.json` | v1→v2 逐批对照 + 救回题清单(092-S03/101-S05:v1 rank 1→3/4,v2 rank 1→1) |
| `ARM_CONFIG_DIFFS_DRAFT.md` | G2 臂配置差异表草稿(唯一实验变量 `novel_conservation_filter=on`;与 C0 逐字段 diff) |

代码落点:`src/pathway_v43/validation/conservation.py`(判据 v2,纯函数,
版本三元组 v43-cons-2/norm-2/selfrank-2/g3b-catalog-2/kw-2/registry-2/
frag-1)、`domain/policy.py`(开关,默认 off)、`workflow/nodes.py`(挂接
`_apply_novel`/`_apply_analogy`);夹具 `tests/test_conservation_filter.py`
(50 用例:9 必改逐条 + v1 风险清单 11 条 + off 逐字节等价 + e2e)。

复现:

```bash
PYTHONPATH=src python -m pytest tests/test_conservation_filter.py -q   # 50 用例
PYTHONPATH=src python -m pytest tests/ -q                              # 全仓 627
OMP_NUM_THREADS=1 PYTHONPATH=src python reports/phase_s15_hit60/g2_arm/offline_replay.py
OMP_NUM_THREADS=1 PYTHONPATH=src python reports/phase_s15_hit60/g2_arm/offline_replay.py --check
```

红线:金标只在本进程(gitignored dev_gold 只读);仓内产物零 SMILES
(qid+旗标+计数);封存件只读;付费跑不发生(等 mimo delta 确认 + 冻结 +
授权)。题域标签:全部数字仅 dev(B1 环境路径中间步骤),不外推 298。
