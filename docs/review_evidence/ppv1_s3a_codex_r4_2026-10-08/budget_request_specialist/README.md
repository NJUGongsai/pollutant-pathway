# S3a-r4 独立预算 / 请求 / stop 专项证据

本次正式Codex链子专项，实际HEAD `b7f2bba02ca49edd0a45a13bc9b8434909d99175`，父 `41d0cd55f3def050a62325f00235cf22da302d2e`，2026-10-08(Asia/Shanghai)。执行根 `/private/tmp/ppv1_s3a_r4_budget_etb34fix`。**03/04关闭，05保持关闭**；报告见`SPECIALIST_REVIEW.md`。

只执行本地合成工程夹具，不访问金标/题面/封存run/dependingv4，不调用provider/外部模型，不改主仓或旧永久证据，不commit/push。Python depending43 -B / PYTHONDONTWRITEBYTECODE=1，无pytestcache。源码含vendor与pyproject，所有实验建库只在仓外新tmp；包内只收JSON/文本完整输入输出，无DB/cache/link。

## 实际执行与不执行的区分

1. `scripts/contract_probe.py`：R3永久证据原字节脚本，raw115，exit0；旧5recover期待和1错误priority原样保留。当前effective114/114由只读`adjudicate_r4.py`登记，不复跑不改原输出。
2. `scripts/supplement.py`：原字节，exit0/13记录，correct63priority、10policy消费、exact旧claimed控制/runtime。冻结坏块现在在expected比对前拒，历史kind-only期待两案已只读纠正。
3. `scripts/extra_probe.py`：原字节，exit1/31完整case；18坏policy状态口修复、3合法状态、5unknown状态消费/披露、5foreign-run边界。最后2合法装配控制误删version的旧准备错误仍存在且未执行；stderr完整保留，不把早停后的控制报通过。
4. `scripts/legal_assembly.py`：原正确version输入两案完整补控，exit0。`scripts/sent_failed_control.py`原合法sent→failed控制，exit0。
5. `scripts/full_table_status_probe.py`：本审新增35完整case（非expand decide十八policy、五unknown、三real登记账正控、九terminal拒），15张表前后快照。实际provider调用0；账内network计数与实际网络明确区分。
6. `scripts/runtime.py`：一次环境/schema记录，exit0。
7. `scripts/adjudicate_r4.py`：只读上述已完成日志验证，exit0；保存`evidence/adjudicated_summary_r4.json`，不运行生产代码。

`old_root/old_search/old_stop_input`与原`adjudicate.py`/`reproduce_r2_original.py`只作历史输入保全，本轮没有运行这些额外旧脚本，不借其旧stdout/硬编码HEAD报当前执行。实际每个run的argv/cwd/env/exit/elapsed/scriptSHA/stdout/stderr在`evidence/<run>/`；源输入SHA及actualHEAD见input_snapshot，保全见final_integrity。

`reproduce.py`为本轮便携复现控制器，**仅语法核对**；将冻结包复制到另外新tmp运行一次全部同输入原脚本。勿在永久目录原地执行会建库的脚本。原R3复现控制器保留`reproduce_r3_original.py`，适配diff只改控制路径与运行清单，不改反例输入/expectations。

`manifest.json`为附件相对路径/bytes/SHA-256映射，排除自身/SHA256SUMS/manifest.sha256；`SHA256SUMS`逐附件+manifest；`manifest.sha256`单列manifestSHA。所有数字为合成工程控制，不认证污染物降解的科学性能。
