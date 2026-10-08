# R7 独立存储专项证据

锁定 R7 `858dd94c7c6c8fc387940242403d67b6b36b5313`，R6 对照 `6d9020130a481866ce2f3b79933907a33d8cfc9e`。详见 storage_review.md；所有结构、来源、条件及 SQLite 是脚本内合成，探针无模型、无金标、无真实题面或封存逐题 run。

- `storage_contract_probe.py`：自包含 public build/put/submit/replay；SQL 只在新建合成库准备损坏。R7 15cases+1metadata；v6 9首提case+2metadata（无links表说明），不计metadata为案例。
- `storage_contract_probe.output.jsonl` / `.baseline.output.jsonl`：完整参数输入、事件/假设、计数、错误及逐案输出。
- `storage_assert_observed.py`：逐条钉住本次15观察，**包含当前两个显式states首提错误成功**，因此不是修后验收。修复后应在这些当前缺口断言失败。
- `ppv1_full.stdout.txt/.stderr.txt`：隔离全PPV1 508 passed/0skip。
- `g01_safe_isolated.stdout.txt/.stderr.txt`：第一遍不放真实v3/v4/evaluation，1099passed/2依赖缺席failed/18skip/16slow deselected；合成worker状态在 g01_synthetic_worker_failures/。
- `g01_safe_with_v3_source.*`：第二遍仅补普通v3源码，临时v3/assets由已隔离非题面反应资产镜像；evaluation仍无，export纯函数一case显式deselect。最终 **1110 passed /8 skipped /17 deselected**（16slow+1额外evaluator纯函数），222.45s，exit0。8skip是5真实评价+1v4+2未复制phase_d派生metadata。完整1119结果需读取真实金标，因此本证据不声称独立1119全通过。
- `execution_identity.json` / `runtime_identity.json` / `commands.json` / `input_hashes.json` / `g01_v3_source_addition*.json`：实际源码/版本/命令/执行及复制输入哈希；不包含反应索引内容。
- `initial_fixture_error_*`：首次夹具输出误用没有to_dict的方法后停止日志，已改dataclasses.asdict；最终脚本全部15case完整执行，旧停止后控制不算通过。

仅在新 tmp 执行，不在永久证据目录运行会创建SQLite或覆盖输出的脚本。示例：

```sh
TASK_TMP=$(mktemp -d /private/tmp/ppv1_r7_storage_replay_XXXXXX)
# 将本目录storage_contract_probe.py与storage_assert_observed.py复制到TASK_TMP；
# 使用fresh隔离源码（含vendor与metadata）作为REPO_TMP，不修改主仓或封存证据。
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B "$TASK_TMP/storage_contract_probe.py" "$REPO_TMP" > "$TASK_TMP/output.jsonl" 2> "$TASK_TMP/stderr.txt"
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B "$TASK_TMP/storage_assert_observed.py" "$TASK_TMP/output.jsonl"
```

这些是工程契约复算，不认证真实来源、不证明化学机制或科学性能。G01未访问真实evaluation，缺席/排除项如实列明，不当架构P1。
