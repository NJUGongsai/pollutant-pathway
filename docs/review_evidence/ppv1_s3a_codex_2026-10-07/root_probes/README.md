# 根探针的观测断言与安全复现

`assert_root_observed.py`只读两份既有JSONL，不导入生产模块、不打开SQLite、不复跑测试/探针。归档时独立执行一次，exit0：钉住11个request案例、首行metadata及5个policy案例，合法正控保持；**断言通过表示当前缺口确实存在，不表示已修复或批次通过**。原request脚本无footer，记录为metadata1/footer0。

完整本次只读执行材料：`assert_root_observed.stdout.jsonl`、`assert_root_observed.stderr.txt`、`assert_root_observed.run.json`。原两份观测日志、脚本及`input_snapshot.json`均未改写。账户/源码测试不存在本步骤新运行故障，不以归档断言冒称新增数据库执行。

`root_probe_reproduction.py`是新增的便携控制器。归档时**仅AST语法及静态安全检查，未实际运行**，因此不声称其执行已经验证。它要求显式仓库路径和不存在的新仓外目录；核实际HEAD/父与原snapshot中的完整src/vendor、pyproject、worker SHA后才复制，控制脚本本身也有固定SHA。输出必须在仓库及永久证据目录之外。只在新目录跑request、policy及观测断言；默认不执行任何suite，不读取金标题面/封存run，不调用模型provider，不进行真实网络发送。

```bash
PY=/Users/cc/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 "$PY" -B root_probe_reproduction.py \
  --repo "$REPO" --out /private/tmp/ppv1_s3a_root_probes_new \
  --python "$PY"
```

禁止在永久证据目录原地运行`request_probe.py`/`policy_probe.py`；它们会写合成SQLite，只能由上述控制器复制到新目录。修复后若HEAD或文件hash变化，控制器拒绝；应以新轮登记新输入/版本后独立验证，不能修改旧hash继续冒充原结果。新控制器静态检查证据在`root_probe_reproduction.static_check.json`，不是运行成功证书。
