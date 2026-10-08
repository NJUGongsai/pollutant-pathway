# R8 化学/state 专项证据

当前实际 HEAD/schema/源SHA见 metadata.json；结论见 chemical_review.md。只含规则级合成输入，不代表真实污染物路径性能。

必须在全新tmp执行，复制完整src（含vendor）及pyproject、tests/test_ppv1_r7_chem.py与test_ppv1_r8_chem.py、这些脚本及metadata.json；不在永久证据目录直接运行（原R7 probe和新matrix都会创建合成SQLite）。

命令（depending43，禁字节码）：

```text
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B chemical_boundary_probe.py
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B state_first_consumer_probe.py
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B static_contract_inventory.py
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B assert_r8_chemical_observed.py
```

分别完整重定向到同名日志（actual commands/output names见run_commands.json）。原R7 probe预期55 JSONL且exit1：最后未包capture的手性from_dict拒绝；新matrix补齐两尾案并覆盖恢复/直接对象。原assert_chemical_observed.py预期在57行计数处exit1，未执行其后缺口断言；修后观察验证用assert_r8_chemical_observed.py，预期exit0。历史probe硬编码858dd94不当当前真实HEAD。复跑时重新登记实际源哈希，不能用历史metadata认证新源。
