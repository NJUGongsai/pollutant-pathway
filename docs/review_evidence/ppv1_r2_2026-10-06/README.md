# PPV1 S0–S2 第二轮复审：合成复现附件

- 审核日期：2026-10-06。
- 目标仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。
- 对应 HEAD：`0002f71af23a2d00db7734e15bf1142c64c85145`。
- 对应报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R2_2026-10-06.md`。
- 所有分子、条件、研究 ID 和 SQLite 都是合成夹具；不含 gold、真实逐题运行或模型输出。

## 文件与证据含义

| 文件 | 内容 |
|---|---|
| chemistry_probe.py / chemistry_probe.output.jsonl | 38 条化学、身份、审计和真实编辑协议对照；部分刻意不一致的 result 属公开接口合成输入，脚本注明 |
| conditions_probe.py / conditions_probe.results.json | 条件、阶段、依赖、分支隔离、假设身份、来源计数正反例 |
| storage_probe.py / storage_probe.output.jsonl | 17 条实际提交、重放、schema、旧导入、门禁和处理池合成探针 |
| admission_probe.py / admission_probe.json | 主审核补做缺 context、窄 scope 和提供 context 的对照 |
| pytest_output.txt | 隔离复制 src 与四个 ppv1 测试文件后实跑：129 passed，1 skipped |
| focused_pytest.txt | 条件专项子集：28 passed，48 deselected；不可与 129 相加 |
| skip_control.json | 错 S_O_3 断键失败与同环境有效 S_O_1 断键成功的对照 |
| manifest.json | 附件及主报告的 SHA256，便于核对审核材料 |

输出中的异常是探针捕获的审核证据。退出成功不表示被测契约通过；第三轮回修时应将所列预期转成明确回归断言。hypothesis/状态 ID 和临时路径会随实现版本变化；不应只断言旧 ID 字面值。

## 复跑

先将脚本复制到新 `/private/tmp` 目录再执行，避免探针的合成数据库写入文档目录。`storage_probe.py` 每次新建 synthetic 目录；`conditions_probe.py` 创建临时合成库；admission 补充脚本另写自己的固定 `/private/tmp` JSON，同时打印输出。以下命令不调用模型或真实数据。

```bash
task_review_scratch="$(mktemp -d /private/tmp/ppv1-r2-replay.XXXXXX)"
cp /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r2_2026-10-06/*.py "$task_review_scratch/"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python "$task_review_scratch/chemistry_probe.py" > "$task_review_scratch/chemistry_probe.output.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python "$task_review_scratch/conditions_probe.py" > "$task_review_scratch/conditions_probe.results.json"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python "$task_review_scratch/storage_probe.py" > "$task_review_scratch/storage_probe.output.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python "$task_review_scratch/admission_probe.py" > "$task_review_scratch/admission_probe.json"
```

隔离 ppv1 测试的原命令：在仅复制 src 与以下测试文件的临时目录，以本项目 Python 执行 `python -m pytest -q -rs -p no:cacheprovider`，并设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=<临时目录>/src`。

- `tests/test_ppv1_profile.py`
- `tests/test_ppv1_domain.py`
- `tests/test_ppv1_s2.py`
- `tests/test_ppv1_rework.py`

本附件不含实施方“740 passed”的独立复跑记录，该数量应按交付书原日志引用。
