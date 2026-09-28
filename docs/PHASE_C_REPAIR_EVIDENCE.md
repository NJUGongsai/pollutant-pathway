# Phase C 三审补强独立证据包（2026-09-28）

## 结论

上轮未通过的“金标文件自身重复 qid”门禁现已独立复核通过。代码、测试夹具、全仓回归与离线审计符合本轮交接声明；复核未修改实现、资产、封存输入或金标，未提交。

## 证据

| 项目 | 实际结果 |
|---|---|
| 定向测试 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests /Users/cc/miniconda3/envs/depending43/bin/python -m pytest tests/test_phase_b_workflow.py tests/test_phase_c_workflow.py tests/test_phase_c_audit_guards.py tests/test_edit_protocol.py tests/test_donor_applicability.py -q`：退出码 0，`74 passed in 10.08s` |
| 全仓回归 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests /Users/cc/miniconda3/envs/depending43/bin/python -m pytest tests/ -q`：退出码 0，`388 passed in 484.45s` |
| 金标覆盖反例 | `tests/test_phase_c_audit_guards.py`：退出码 0，`5 passed in 0.94s`；覆盖缺一题、空金标、任务 qid 重复、金标文件同 qid 多行；失败输入审计返回码 2 且不产出 summary |
| 编辑协议反例 | `tests/test_edit_protocol.py::test_validate_rejects_undeclared_fields_and_legacy_aliases` 覆盖 `unknown_field`、`unknown_op`；合法四操作仍通过 |
| 对齐上限 | `tests/test_donor_applicability.py` 覆盖 2000 上限、触顶 ambiguous、全败 unavailable 与 `alignment_limit_exceeded` |
| P1 rule/analog | `test_rule_card_selected_via_rank_zero_commit`、`test_analog_card_selected_via_rank_zero_commit` 覆盖候选层；对应 adjudication guard 覆盖裁决层零报告、零占位；`nodes.py` 验证层拒 `rank_selected_non_recorded` |
| 独立审计 | 输出至新建空目录 `/tmp/phase-c-rereview.h4g72w`，exit 0；金标 298 行 / 298 唯一、任务 `66/66`，再分类 `1/22`，接纳 `0/15`，消融 `23/43`，拒绝目标文本金标诊断 `8/23` |

## 独立失败反例与审计命令

用 `tests/test_phase_c_audit_guards.py` 的假封存构造函数生成一条任务和同 qid 的两条金标行，再直接运行审计子进程，得到 `exit_code=2`、`summary_exists=False`、stderr 包含 `FAIL: 金标行重复(same qid multiple rows)`。新增 `test_audit_fails_on_duplicate_gold_rows` 钉住此反例；先前所谓“重复夹具”只覆盖任务 qid 重复，本轮已补金标行重复。

独立封存审计的实际命令（显式指定新建空目录，避免覆盖对照产物）：

```bash
OMP_NUM_THREADS=1 /Users/cc/miniconda3/envs/depending43/bin/python scripts/phase_c_offline_audit.py \
  --seal-run-dir /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1 \
  --gold /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl \
  --out-dir /tmp/phase-c-rereview.h4g72w
```

独立 TSV 逐行复算：23 条旧拒绝中目标文本可解析 22、匹配金标 8、再分类 1 可执行 / 22 不可执行；15 条旧接纳匹配金标 0；新门禁路由 23 条类比 / 43 条分流。8/23 是被拒目标**文本**的诊断，不是报告产物命中数。

## 审计对拍

独立五项产物与 `reports/ec298/phase_c/` 分别执行 `cmp`，均逐字节一致：

```text
analogy_route_audit.tsv       da2eae84f916f0879eade5e6d340db7a4b3e593199190ad21398727ec436e39e
rejections_reclassified.tsv  efbef9ca3b006f0dd4abe997a9a48d2b00f9778d2d308d6d665e814b72d30b15
accepted_gate_check.tsv       7b347f8a3e5ba1a995ea59161b7e32ddb8ed05a46372ee453bc8c1ab612850cf
routing_ablation_offline.tsv 949e8014ca0fbfa949f5ebce69b7b845ee2df4816e250482897457e442df7f58
summary.json                  96ee62a60e926e4f31bb5c006b3ae295e9491649f4b16f1ce97da1feeca529e0
```

金标输入 SHA256：`9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`。

## 快照与偏离

复核时 `HEAD=5c8f284423716137af24053f067ffdc7489066f2`；工作树有既有未提交改动，按要求未清理、未提交。本次审计脚本 SHA256 为 `52c2443c212a7ae78a7c501033b5876dc6e74c1b9c4515a02cd62990c33d8b2b`，金标守卫夹具为 `536a431ee6b5316abe7b3bcb6f0d191c329e50893cfb5c27d0a9129c93557eb9`。其他关键实现文件 SHA 与 `docs/EC298_PHASE_C_REPORT.md` §10 所记前缀一致。真实金标 298 行 / 298 个唯一规范化 qid；金标输入 SHA 如上。

上轮记录的 base `python` 缺 pytest 与外层 zsh 只读变量名冲突不适用于本轮命令；本轮统一使用 `depending43` 环境，全仓与审计命令均以退出码 0 完成。四个 TSV 与上轮哈希相同；`summary.json` 因新增 `n_gold_unique_qids=298`、`n_gold_duplicate_qids=0` 并更名覆盖门禁字段而产生新哈希。

## 终审

逐项复核结果：P1 三层防御【属实】；双卡反例【属实】；金标覆盖与金标行唯一门禁【属实】；编辑协议严格化【属实】；对齐枚举上限 fail-closed【属实】；全仓回归【属实】；独立审计及五项 SHA 对拍【属实】；工作树未清理、未提交【属实】。

verdict：✅ APPROVED
