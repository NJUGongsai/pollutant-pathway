# S3a 继承与化学/mimo专项永久附件

HEAD `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`；R8 parent `00e509a974b40a7c9779fcd35e53b16637a13d60`。结论与有限回修见 INHERITANCE_REVIEW.md；本专项 P1 是 **B4/done恢复消费坏ledger，只验索引身份**。

- inheritance_v2.stdout.jsonl：26 authority案（两阶段各clean+12坏）+1直submit raw guard；24坏恢复被接受，公共writer重放拒，clean保持。authority_cases/ 每案完整输入与14表前后载荷。
- chemistry_v2.stdout.jsonl：15case+assertionfooter，canonical/raw r与真坏解析、9往返小控、failure三None/diag{}→converter→audit中心unknown、runner双入口拒、全src AST。cx_controls.stdout.jsonl：原R8 literal retained6/removed3分段当前独立执行9case+footer。
- metadata.json：实际HEAD/parent/schema/env/argv/退出码及工具wall时间。input_hashes.json：仓内读取/复制源与文档78输入hash。inherited_chemical_source_hashes.json：五化学源与R8逐字一致。全部原日志/stderr保留；两次审核脚本准备错误与畸形DAT夹具如实登记。
- assert_observed.py exit0 固定当前错误观察；assert_contract.py exit1 是正确契约在当前HEAD的预期红，停在首坏state_charge，后续assert未运行。24逐案不是由它声称“后续通过”。

仅合成public底座，不含真实金標/题面/封存、源树、资产、DB、pycache；未外模/网络/推送，不把工程数字说成科学性能。本专项不执行PPV1全量/基线/G01/并发预算，归主审其他专项；不得拿交付自报填入本专项执行。

复现必须新tmp，禁止本永久目录原地执行会写库/日志的原脚本：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  <本附件目录>/reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/<尚不存在的新目录> \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

控制器固定当前历史HEAD/必要源hash，拒已有out/仓内out/证据内out，复制完整src/vendor、project metadata和s3a_worker到隔离源。它是**归档阶段新写，syntax/path检查而未运行**，实际运行证据来自上述原probe/log，不冒称控制器独立执行。固定hash不应被当下轮实际HEAD；下轮要复跑旧probe则明确绑定下轮新隔离源与命令，别修改永久材料。

first inheritance原脚本和first chemistry原脚本从本轮已知编辑历史重构字节存档，metadata明确原执行命令是同名脚本修改前，不冒称错误版本执行前已哈希。第一次inheritance序列化错零JSONL；第一次chem14cases后AST literal_eval错，修正完整窄probe重跑，不是源码失败。SHA256SUMS覆盖所有附件，只有根manifest.json/SHA256SUMS不自hash。
