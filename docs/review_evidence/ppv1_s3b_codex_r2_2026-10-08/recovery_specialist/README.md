# S3b-r2 public recovery / concurrency independent evidence

实际日期 2026-10-08，代码 HEAD `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`，直接父 `c1211183c0874b12c5b5461845d3c61f0a84719c`。这是主评审的恢复/并发专项，非全量pytest。新 tmp 隔离当前 src（含vendor）、pyproject metadata，Python depending43 `-B` 禁字节码/pytest缓存；无外部模型、网络、真实金标/题面/封存run，主仓源码/测试/既有文档零修改。

## 裁定

`observations_r2.json` 21 个顶层观察 + `additional_observations.json` 4 个：**23 项符合既定契约，2 项具体反例同属 S3B-01 残余**，不称25 passed、不称两个新漏洞。所有观察内部是否完整执行看逐项日志。两控制器 exit0，未发生原脚本已登记的低层 distinct-worker 捕获错误，本轮只使用其公开 worker/helpers，未调用过时 raw control_run 的旧缺口 oracle。

- S3B-01 普通 changed/decide_changed 输入 ⇒ frozen_plan_mismatch 且15表不变；same/omitted 沿冻结原计划提交合法事件；冻结artifact missing/unparseable/普通payload改坏 ⇒执行前拒、零工具、15表不变。**残余**：B3/B4 后只替换 frozen_plan artifact 加 scenario_transitions 并重算局部包装 payload_hash/plan_digest（plan_version保持 ppv1-frozen-plan-1）；原 run_identity、root retrieve payload.plan_digest、task/ledger/event不改，resume不传plan成功，新增 injected scenario transition。不是抗整库协同重写要求；新输入被原身份真实公共链消费。
- S3B-02 两旧坏 bundle 对应 action blocked，events0/commits2不增、attempt/预约与坏文件保全。缺reservation或坏 event context 权威均公开恢复先拒且15表不变。追加独立 C 控制：真实工具trace恰1，为合法独立hyp；坏hyp零工具/零event，合法hyp event1；repeat不重数。
- S3B-03 三产物普通/all及2/3硬杀恢复补足3/3；转换 normal/事件已提交零入队/转换创建后硬杀/转换后followups尚未complete，各恢复到同一phase-1后续、重复无新增。旧事件context与phase_history保持冻结。三产物本专项 total_search_actions=30，旧反例20，仅留预算余量；化学/产物/硬杀输入同旧规则，**不冒称该项完整输入字节与旧20相同**。
- S3B-04 两真实 workflow.runner.resume_run 进程。winner在expansion barrier持flock，peer在GO释放前返回 driver_session_active；真 AtomTool tool_entered恰1；原attempt ID及预约ID保持、单进程接管可完成，重复resume无新增。不是仅最终event去重断言，也不是分布式/external provider exactly-once认证。
- 四硬杀 after_claim/request_registered/bundle_written/event_submitted 均真公共 start_run/resume_run 控制；合法B1/B3/B4各event1/commit4，B2 request1/scripted network0且不默重发，重复计数保持。

## 文件与复现

- `scripts/review_recovery.py`：四硬杀、旧01/02/03/04公开输入规则、两个自洽重包反例、真实双resume。`scripts/review_additional.py`：独立C继续+真实工具trace、冻结计划missing/invalid。
- `scripts/probe_public.py`、`probe_supplemental.py`：复制首轮旧脚本，`raw_old_scripts/`保留原bytes；只用公共worker/helper，不把其中硬编码旧oracle当本轮裁定。
- `original_inputs/`：复制首轮39份相关输入供核对，历史绝对runs_root保留；**不得直接对历史路径执行**。本轮`inputs/`由新controller生成，run_id/runs_root一律新tmp；其余细节逐JSON为准。
- `inputs/`完整每child输入及两反例before/new envelope；`logs/`完整cmd/env/exit/stdout/stderr；`tables/`全部15表/可读artifact前后快照；`artifacts_final/`原始artifact与identity字节（含坏JSON、driver.lock披露文本）；二进制合成库/WAL/barrier不归档，SHA在omitted_binary_inventory.json。
- `adjudicated_summary.json`绑定每项结果；两个计划反例数据库逻辑前后由15表JSON canonical SHA记录：artifact突变前与突变后表完全一致，resume后实际变更。**执行前二进制DB SHA未记录，不能倒补**，只有最终二进制SHA与完整前后逻辑快照。
- `input_manifest.json`当前source输入SHA，`execution_metadata.json`真实版本/命令/源不变核验，`source_review_lines.txt`代码锚点。manifest含SHA-256。

不要在永久目录原地跑会建库/日志的脚本。需复现时整包复制新tmp后运行：

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<新tmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <新tmp>/scripts/review_recovery.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<新tmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <新tmp>/scripts/review_additional.py
```

控制器会重新创建自己的输入/运行，勿从original_inputs拿绝对历史路径直接跑。外层manifest不自包括manifest.json/SHA256SUMS/manifest.sha256三控制文件；SHA256SUMS钉manifest bytes。
