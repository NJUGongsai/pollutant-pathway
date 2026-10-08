# R7 化学专项永久附件

来源 HEAD 858dd94c7c6c8fc387940242403d67b6b36b5313；日期2026-10-07。完整裁定见chemical_review.md，57条顶层记录（含metadata/工厂与writer对照/早退），观察断言通过，仍有raw恢复P1；观察断言不是修后通过线。

不要在永久目录原地执行。复制本目录到新空tmp，再复制完整src（含vendor与metadata；忽略__pycache__/pyc）到tmp/src。helper fixture在tests/test_ppv1_r7_chem.py，已包含；脚本会使用其公开API夹具函数，完整输入、diagnostic/proof、audit/admission、结构化拒绝和写前后counts都在JSONL。新SQLite只会生成在脚本所在的新tmp。

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B chemical_boundary_probe.py > chemical_boundary_output.jsonl 2> chemical_boundary_stderr.txt
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B assert_chemical_observed.py > assert_chemical_output.txt 2> assert_chemical_stderr.txt
```

expected_source_HEAD只是原始执行来源锁定说明；实际HEAD和完整源码hash由主审manifest记录。源码校验摘要在JSONL metadata；此目录不含整个src副本，也不含SQLite二进制（合成库由脚本重建）。原始atom-indexed RDKit快照可能因规范写出重排不同，不等于事实丢失，查看canonical writer稳定、严格身份往返和原子属性多集合。
