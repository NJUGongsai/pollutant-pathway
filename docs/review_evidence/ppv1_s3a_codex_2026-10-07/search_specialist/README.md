# S3a 独立搜索底座复核证据

实际提交 `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`，schema `ppv1-search-1 / ppv1-store-9`。合成工程证据，无金标、题面、封存run；网络请求0，不外推科学性能。

结论见 `SEARCH_REVIEW.md`。新行为复现16案、合法硬杀/并发控制5案、已执行defer额度绕过追加1案，共22个实际完成 case。首次观察脚本类型名断言准备错误（完成9案后早停）原文保留，不并入22；barrier父侧GO遗漏续接如实登记。未跑全量PPV1/G01/基线，由工程专项单列。

- `input_hashes.json`：隔离副本的逐输入SHA、实际HEAD，含vendor/pyproject/worker。
- `probe.py` / `observations.json` / `probe.stdout.jsonl` / `probe.stderr.txt`：16个独立行为，完整public args/ledger rows前后。
- `probe_attempt1.*`：原失败体与stdout9案+错误名断言stderr。
- `crash_concurrency_as_executed.py` / `crash_commands.json` / `crash_observations.json` / `crash.stdout.jsonl` / `crash.stderr.txt`：四独立子进程强制exit与两个barrier worker的完整argv/cwd/stdout/stderr/exit/前后。
- `barrier_external_release.json`：实际观察到双ready后续接GO记录；命令原文在 run_metadata 附件。
- `crash_concurrency.py`：把同一步GO释放内联的新复现控制器，源码语法核对通过，未另执行其全套四崩溃；不充当原执行体。
- `defer_budget_bypass.py` / `defer_bypass_observation.json` / 对应stdout/stderr：total/action与每父alternatives均限1，却实际提交保留3事件/3不同备选，然后全释放账面used=0。
- `run_commands.json` / `run_metadata.json`：实际执行、准备修正与复现未执行声明。
- SHA256SUMS/manifest.json覆盖脚本、日志与嵌套清单，外层两个清单除外；不归档数据库或完整源码。

安全复现命令（只合成，不跑全量pytest；脚本自行拒已有输出）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_s3a_search_replay_NEW \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

仅允许固定HEAD/逐输入hash相同的来源；复制完整白名单src/vendor与metadata到新tmp，不把永久目录当输出。`reproduce.py` 新归档安全包装已做语法/路径检查，未冒称该包装另跑22案；原分段执行日志为事实。永久证据目录中不得原地运行分段脚本（它们会建临时合成库）。
