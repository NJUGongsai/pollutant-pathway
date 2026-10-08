# R7 条件与基线冻结附件

HEAD 858dd94c7c6c8fc387940242403d67b6b36b5313；父/基线6d9020130a481866ce2f3b79933907a33d8cfc9e。

本目录仅保存脚本、原始/适配测试、元数据、分类、输入输出日志与专项报告；不收源码副本或SQLite，不在此原地运行写日志的复现。

- 条件结论和回归瑕疵见 conditions_findings.md。
- 基线正式执行：baseline_pytest_full.log，33failed/24passed；R7隔离执行 current_57_pytest_full.log，57passed。
- baseline_red_classification.json 明确26行为红、6字段/表缺失红、1新增violation披露红。
- conditions_public_probe.py 通过 --source 指定一份含src/vendor、tests/test_ppv1_r7_conditions.py、pyproject的R7隔离副本；16独立顶层case及期望assertions全部完成，观察结果见jsonl与空stderr。
- baseline_reproduce.py 先复制本目录到新tmp，再用 --repo /Volumes/CC/Enzyme_Agent/dependingv43 --out 一个不存在的tmp子目录执行；它创建6d90201 detached worktree，复制同目录original_tests三文件，仅在临时test移除新COMPLETION_LICENSE导入并提供同字面量，不改断言，运行33/24后finally移除worktree。此脚本已另建临时目录实际复现验证。
- metadata.json 保存实际HEAD、两源码树各文件SHA、命令/结果与worktree移除证据；永久包不携带源码，按git HEAD重建。
- 原脚本/测试属于规则级合成夹具；无金标/题面/封存逐题run/外部模型调用。

SHA256SUMS 是此附件冻结时除清单本身外所有文件的SHA-256。
