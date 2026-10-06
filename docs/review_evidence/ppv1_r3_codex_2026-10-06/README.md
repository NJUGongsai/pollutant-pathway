# PPV1 R3 Codex 独立复审证据

审核仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。锁定 HEAD：`af14fb2bb66e8afbbbbecd38722a9cacbd0699c3`。日期：2026-10-06。

结论见[正式复审报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R3_2026-10-06.md)。该目录属于独立复审，与实施方的 `ppv1_r3_2026-10-06` 交付证据分开保存。

## 内容与证据限度

| 文件 | 来源及内容 |
| --- | --- |
| [chemistry_probe.py](chemistry_probe.py) / [输出](chemistry_probe.output.jsonl) | 化学专项脚本，主审再次执行的 40 条 JSONL，含 meta/正控制；真实 executor 与接口合成分别标记 |
| [conditions_probe.py](conditions_probe.py) / [输出](conditions_probe.results.json) | 条件专项脚本，主审再次执行的 36 个顶层案例；已登记 checker 的合成 True 载荷只隔离条件/依赖逻辑，不证明真实生物反应 |
| [storage_probe.py](storage_probe.py) / [输出](storage_probe.output.jsonl) | 存储专项最新版脚本，主审再次执行的 29 条 JSONL；仅临时合成 SQLite，含合法/损坏控制 |
| [admission_binding_probe.py](admission_binding_probe.py) / [输出](admission_binding_probe.json) | 主审真实乙醇→乙醛诊断的跨反应复用、注册名字-only、门禁 on/off 对照 |
| [pytest_output.txt](pytest_output.txt) | 存储专项独立复制 src/七个 ppv1 测试后执行，226 passed in 1.91s，0 skipped；主审核查日志 |
| [manifest.json](manifest.json) | 本附件、正式报告及审核输入/源码 SHA-256；不包含 manifest 自身 |

40/36/29 是结果记录或案例数量，不是失败测试数。全部使用合成输入，不读 gold、真实题目资产或封存逐题 run，不调用模型，不更改实现。合成数值闭合不证明机理、生物可行性或酶选择性。全量 837 passed / 16 deselected 仅是实施方交付声明，本证据包没有独立复跑全量的日志。

环境：`/Users/cc/miniconda3/envs/depending43/bin/python`；Python 3.11.16，RDKit 2026.03.6。审计与探针使用审核 HEAD 源码；临时测试复制目录和 SQLite 的绝对路径已原样保留在输出中，属于运行轨迹，不能当永久数据依赖。

## 安全重跑

**先复制脚本到新的临时目录。** conditions/storage 脚本会在自身目录创建临时 SQLite；不能在本证据目录执行，也不能覆盖原审核日志。原脚本为观察型探针，不是“exit 0 即问题修复”的验收器；实施 agent 应把关键反例转成有正确断言的公共边界回归。

下面命令只写新临时目录。要复现当前结果，源码应处于上述审核 HEAD；在更新 HEAD 上运行用于前后比较，须另记实际版本。

```bash
review_repo=/Volumes/CC/Enzyme_Agent/dependingv43
review_evidence="$review_repo/docs/review_evidence/ppv1_r3_codex_2026-10-06"
review_tmp=$(mktemp -d /private/tmp/ppv1-r3-review-XXXXXX)
review_python=/Users/cc/miniconda3/envs/depending43/bin/python
cp "$review_evidence"/*.py "$review_tmp/"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/chemistry_probe.py" > "$review_tmp/chemistry.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/conditions_probe.py" > "$review_tmp/conditions.json"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/storage_probe.py" > "$review_tmp/storage.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/admission_binding_probe.py" > "$review_tmp/admission_binding.json"
```

独立 ppv1 测试复跑方式：

```bash
cp -R "$review_repo/src" "$review_tmp/src"
mkdir "$review_tmp/tests"
cp "$review_repo"/tests/test_ppv1*.py "$review_tmp/tests/"
cd "$review_tmp"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_tmp/src" "$review_python" -B -m pytest -p no:cacheprovider -q -rs tests > "$review_tmp/pytest_rerun.txt"
```

实施方应保留错误输入被拒/未知、合法控制被接受两类结果，并按正式报告验收真实消费者；不要改附件、改判据为“测试绿”或把 checker 注册名称作为反应证明。
