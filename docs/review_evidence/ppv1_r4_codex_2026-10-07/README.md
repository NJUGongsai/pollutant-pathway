# PPV1 R4 Codex 独立复审证据

审核日期2026-10-07；仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`；实际审核 HEAD `e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae`。

结论见[正式报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R4_2026-10-07.md)。该目录是独立复审材料，与实施方 `ppv1_r4_impl_2026-10-06` 分开保存。全部使用合成分子/条件/来源与临时SQLite，不读gold、题目资产或封存逐题run，不调用模型、不改实现。

## 文件与采信限度

| 脚本/结果 | 内容 |
| --- | --- |
| [admission_probe.py](admission_probe.py) / [23条输出](admission_probe.output.jsonl) | 主审真实诊断正控制、可自造/改输入证据、strict类型、finite_rule hash、scope标签、真实断裂多产品绑定及额外转化覆盖 |
| [chemistry_boundary_probe.py](chemistry_boundary_probe.py) / [17条输出](chemistry_boundary_probe.output.jsonl) | 新编辑协议、非四面体/EZ轴、DATA注记及支持范围控制，主审再次执行；真实executor/接口合成分别标明 |
| [r3_chemistry_probe.py](r3_chemistry_probe.py) / [40条输出](r3_chemistry_probe.output.jsonl) | R3原样脚本在R4实际源码复跑，主审再次执行；脚本meta中的af14fb2是来源标签，实际库为本目录锁定e80f459，输出诊断版本为-4 |
| [conditions_probe.py](conditions_probe.py) / [19个顶层案例](conditions_probe.results.json) | 主审复制并再次执行的完整结果；旧R3按AST块复跑含4处拒绝，拒绝块不算通过；新增全链用真实v4诊断 |
| [storage_boundary_probe.py](storage_boundary_probe.py) / [21条输出](storage_boundary_probe.output.jsonl) | 新writer/replay/旧来源边界，主审再次执行；仅临时合成库 |
| [r3_storage_probe.py](r3_storage_probe.py) / [29条输出](r3_storage_probe.output.jsonl) | R3原样存储脚本在R4复跑，主审再次执行；控制和预期结构化拒绝逐项捕获 |
| [pytest_output.txt](pytest_output.txt) | 存储专项隔离复制src和10个ppv1测试，312 passed in 1.95s，0 skipped，主审核查；未独立复跑923全量 |
| [manifest.json](manifest.json) | 附件、正式报告、审核输入及源码/测试SHA-256；不含manifest自身 |

记录数包含环境/正控制，不是失败数；脚本exit 0不表示问题已修。合成计量闭合不证明机理、生物可行性或酶选择性。非四面体联合控制strict=False现在被消费，不声称直接R6；E/Z变更是接口合成，不声称冻结执行器会生成该反转。DATA注记不类推所有SGroup/SRU非化学。

环境Python3.11.16，RDKit2026.03.6；解释器 `/Users/cc/miniconda3/envs/depending43/bin/python`。旧脚本来源HEAD与实际运行HEAD分列，判断依据实际源码及输出版本。输出中临时SQLite绝对路径只作运行轨迹，不是永久数据依赖。

## 重跑方法

**全部脚本先复制到新临时目录。**条件脚本写自身目录 `results.json`；存储脚本在自身目录创建SQLite。不得在本证据目录执行或覆盖审核输出。条件旧脚本依赖本仓永久R3附件，AST执行时其__file__基目录已重定向临时目录，避免向原证据目录写库。

复现原结果应使用上述审核HEAD；若源码已更新，另记新HEAD并用于前后比较，不回退用户工作。下面只写临时目录：

```bash
review_repo=/Volumes/CC/Enzyme_Agent/dependingv43
review_evidence="$review_repo/docs/review_evidence/ppv1_r4_codex_2026-10-07"
review_tmp=$(mktemp -d /private/tmp/ppv1-r4-review-XXXXXX)
review_python=/Users/cc/miniconda3/envs/depending43/bin/python
cp "$review_evidence"/*.py "$review_tmp/"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/admission_probe.py" > "$review_tmp/admission.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/chemistry_boundary_probe.py" > "$review_tmp/chemistry_boundary.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/r3_chemistry_probe.py" > "$review_tmp/r3_chemistry.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/conditions_probe.py" > "$review_tmp/conditions_summary.json"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/storage_boundary_probe.py" > "$review_tmp/storage_boundary.jsonl"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_repo/src" "$review_python" -B "$review_tmp/r3_storage_probe.py" > "$review_tmp/r3_storage.jsonl"
```

条件完整结果是新临时目录的 `results.json`，stdout仅摘要。原审核完整结果是本目录 `conditions_probe.results.json`。

隔离套件复跑：

```bash
cp -R "$review_repo/src" "$review_tmp/src"
mkdir "$review_tmp/tests"
cp "$review_repo"/tests/test_ppv1*.py "$review_tmp/tests/"
cd "$review_tmp"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$review_tmp/src" "$review_python" -B -m pytest -p no:cacheprovider -q -rs tests > "$review_tmp/pytest_rerun.txt"
```

实施方把报告反例转成正确断言的公共边界回归，保存正/负控制。不要把观察脚本自身异常被捕获后的exit0、字段存在/注册名称/机械升版当成验收，不改本证据或原审核报告。
