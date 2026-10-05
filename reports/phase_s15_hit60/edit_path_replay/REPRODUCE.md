# T9 编辑路径重放 · 复现指南（零 LLM / 零 API / 确定性）

> 产物目录 `reports/phase_s15_hit60/edit_path_replay/`。
> 本文件只含命令与 SHA，不含任何金标/底物/产物 SMILES 原文。

## 0. 身份锚（重放时点 2026-09-30）

| 项 | 值 |
|---|---|
| git HEAD | `bf1ac3849e803097c9ae39f802bf774597f4f27d`（分支 v4.3） |
| 工作树 | 含 T4 门禁修复等大量未提交改动（未 reset 未提交，重放即该树行为） |
| `src/pathway_v43` 聚合 SHA256（51 文件按路径序拼接） | `0f0a4be5f50320de4b18238c13faab421d4a55b34e63b84e259b0f9a2c947e02` |
| `services/atom_tool.py` SHA256（T4 主战场） | `b20092dcf4d651a59a644ab7a8ba90aa83036958877918d3bd131901ec996f27` |
| python | `/Users/cc/miniconda3/envs/depending43/bin/python`（rdkit 齐） |

## 1. 输入（全部只读）

| 输入 | 位置 | SHA256 |
|---|---|---|
| 批1 原始编辑输入（298 首跑封存镜像） | `/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1`（agent_runs 只读扫描） | 由脚本现场读取 |
| 298 金标（只读，旗标比对用） | `/Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl` | `9f5955d4…9211c` |
| dev 金标（gitignored，只读） | `reports/phase_s1_hit60/dev_gold/dev_gold.jsonl` | `d285dc0b…2f2a` |
| 批2 原始编辑输入（远端只读抽取件） | `raw_inputs/remote_edit_inputs.jsonl`（gitignored） | `e5322075…11a1` |
| 修复前结论（批1） | `reports/ec298/phase_c/rejections_reclassified.tsv` | `efbef9ca…30b15` |
| 修复前结论（批2a 池标签） | `reports/phase_s0_hit60/boundary_pools.tsv` | `5ad32442…ce9b` |

## 2. 远端抽取（批2 输入的生产命令，只读零 API）

```bash
# 依赖 /tmp/cy_ssh.sh（expect 封装；stdout 前两行噪声用 grep 过滤）
B64=$(base64 -i reports/phase_s15_hit60/edit_path_replay/scripts/t9_remote_extract.py | tr -d '\n')
/tmp/cy_ssh.sh "echo $B64 | base64 -d > /tmp/t9_extract.py && python3 /tmp/t9_extract.py 2>/tmp/t9_stderr.txt && rm -f /tmp/t9_extract.py; cat /tmp/t9_stderr.txt 2>/dev/null" \
  2>/dev/null | grep -v "^spawn ssh\|password:" \
  > reports/phase_s15_hit60/edit_path_replay/raw_inputs/remote_edit_inputs.jsonl
# 远端只读对象：
#   /usrdata/EnzymeCAGE_data/workspaces/dependingv43/runs/ec298_pd_retest_C0/runs/
#     （Phase D 重测 C0 臂，12 道 edit_blocked qid 的 prediction_task/
#       prediction/decision/retrieval payload）
#   /usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs/s1_dev_*/
#     （S1 六批 dev analogy_edit 任务全扫，=18 条）
# 末行 stderr 摘要行（n_rows=…）需从 JSONL 中剔除。
```

## 3. 重放（确定性；PYTHONHASHSEED 钉住拒因列表序）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
OMP_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONPATH=src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  reports/phase_s15_hit60/edit_path_replay/scripts/t9_edit_replay.py
```

- 重放链 = `workflow/nodes.py _apply_analogy` 的确定性门禁序：
  ① donor 引用 → ② `validate_edits` → ③ `execute_edits` →
  ④ `check_target_consistency`（T4 修复主战场）→ ⑤ 空编辑 no-op 策略 →
  ⑥ `validate_event_products`（产物验证；ancestry=[底物]、siblings=空、
  check_elements=True 按 analog 提案卡口径）。
- 确定性实测：`PYTHONHASHSEED=0` 双跑逐字节一致；跨 seed（0 vs 1）
  38 行判定零差异（仅 2 行对称分子的拒因排列序不同——集合迭代序，
  与判定无关，见报告 §5）。

## 4. 产物

| 文件 | 层 | SHA256 |
|---|---|---|
| `replay_per_question.tsv`（38 行逐题表，无 SMILES） | 发布 | `6f4e2b3a…4383` |
| `replay_summary.json`（汇总+身份+计数） | 发布 | `7b2b069d…aedb` |
| `scripts/t9_edit_replay.py` | 发布 | `c76e91dc…3d0e07` |
| `scripts/t9_remote_extract.py` | 发布 | `8e7a90a7…a2a6` |
| `raw_inputs/remote_edit_inputs.jsonl`（含声明目标原文） | **gitignored** | `e5322075…11a1` |
| `raw_inputs/batch1_sealed_inputs.jsonl`（含声明目标原文） | **gitignored** | `0d76ecfa…c3f0` |
| `raw_inputs/replay_raw_results.jsonl`（全量含 SMILES） | **gitignored** | `c99f1155…523b` |

金标红线：金标只读；比对结论以旗标（`*_matches_gold`）呈现于发布层；
金标/产物/底物 SMILES 原文只存在于 `raw_inputs/`（已 gitignore，
`.gitignore:30`）。
