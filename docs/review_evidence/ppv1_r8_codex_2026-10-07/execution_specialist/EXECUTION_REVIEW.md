# R8 工程执行与新增回归专项独立复核

执行身份：仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `00e509a974b40a7c9779fcd35e53b16637a13d60`；父提交 `858dd94c7c6c8fc387940242403d67b6b36b5313`。Python `/Users/cc/miniconda3/envs/depending43/bin/python`（depending43，3.11）。当前 schema 族 v8；基线 v7，完整常量在 execution_metadata.json。全部只在 `/private/tmp/ppv1_r8_execution_khvopiqv` 下新隔离目录执行；未改仓内源代码、测试、已有文档或 AGENTS，未访问真实金标、题面、evaluation、封存 run 或旧 dependingv4，未调用模型或 push。

## 独立执行结论

| 对象 | 实际结果 | 证据 |
|---|---|---|
| PPV1 全量 21 文件 | **536 passed / 0 skipped / 0 failed**；1 warning，4.73s | ppv1_baseline/ppv1_full.stdout.txt 与 junit |
| R8 新增当前版本 | **28 passed / 0 skipped**；1 warning，0.69s | ppv1_baseline/current_28.stdout.txt 与 junit |
| 父提交相同原字节 28 项 | **14 failed / 14 passed / 0 skipped**；全部 14 红是行为红，0 字段或缺表红；1 warning，0.69s | ppv1_baseline/baseline_28.stdout.txt、junit、baseline_classification.json |
| G01 安全隔离 | **1138 passed / 8 skipped / 17 deselected / 0 failed**；1 warning，192.46s | g01_safe/g01_safe.stdout.txt 与 execution_result.json |
| slow 名单只收集 | **16/1163 tests collected (1147 deselected)**；未执行 slow 案例 | slow_collection.stdout.txt、metadata、slow_deselected_cases.json |

所有 PPV1/new 当前 pytest 出口 0；基线 pytest 出口 1。父版本由独立 detached worktree 取得，再在完整源码隔离副本执行。两个新增测试文件完整复制且 SHA 一致，**无需 import 或预期适配**。finally 已移除 worktree；记录中的路径已不存在。源码包含 vendor 和 pyproject metadata；无 Python 字节码或 pytest 缓存。完整命令、源码输入哈希与实际版本在 ppv1_baseline/execution_metadata.json。

## 红绿有效性与证明范围

1. 化学 12 红均是 `DID NOT RAISE ChemicalStateError`：raw 未登记 3 参数化、raw 跨分子、formal_charge、origin、恢复+直传组合 2、直接对象 raw/跨分子/formal_charge 3、手性复合 1。不是 KeyError 或缺表导致。合法 7 控制均保持，覆盖干净往返/公共 R6、OCC 同图异拼写、含空格 atomProp、指定手性正常链、CN-only 诚实 unknown、archive fidelity unknown、writer 已拒正控。
2. 存储 2 红明确观察 `created=True`，而目标是同 hash 损坏行首次复用必须 `Ppv1LedgerCorrupt/appearance_hash_corrupt`。当前两例均立即该码并零写入。9 存储例中剩余 7 基线亦绿：none supply 已拒、带载荷 replay 已拒、合法 none/prod-only/all、fresh 首提、semantic conflict 零写入；不以全拒换通过。
3. 组合化学测试在基线首个 `pytest.raises` 因未抛异常即停止，**其后内部绕路不能登记为基线已执行**；当前全绿执行了这些内部部分。独立 direct dataclass 3 例另行覆盖直接对象路径；旧公开 R7 探针对该路径的行为证据归主审另列。14 是测试案例数，不是 14 个独立漏洞。
4. direct formal_charge 例的 docstring“基线用假电荷(verified)”**不准确**。主审要求的两次公开链补跑已确认：clean 为全 verified/R6；只改产物 formal_charge=99，基线元素/身份/center 仍 verified、coverage full，但电荷轴 **violated**，charge_delta=`-99`（reactant-product），admission **retain_conditional/R5d**。本项红证明对象新拒绝行为，不是旧错误 R6。完整输入状态/hyp/context/原 proof 与 audit/admission 在 baseline_charge_doc_probe.stdout.jsonl；不改测试、不重跑套件、不新增 P1。本轮已有最低验收要求结构事实重推导，不需新增机制/性能要求。
5. R7 conditions 的末段现按正确顺序 `_audit(hyp, states, child2, evidence)` 并核 `gate_flag_mismatch`，原误测参数类型已更正。from_dict 基线说明承认旧 ID 载荷原已拒，原反例红在 derive 洗出新 ID。其余 6 存量测试 9 处为 -7→-8 机械版本断言；未降格已有验收。

新增测试对两个既有 P1 的恢复/直传与 supplied occurrence 首提入口有实质检验，合法对照足够。不能单凭 536 测试数证明所有契约或科学性能；本专项不裁定主审另外执行的 put_state 边界和 mimo 条件。

## G01 安全边界及缺席依赖

执行前独立读完 R8 实施方安全控制器和 R7 同源控制器；本次将脚本及两路径白名单复制到新 tmp 后运行。复制 **270** 个输入：本仓 210（R7 208 + R8 新测试 2）、普通 dependingv3/src 42、本仓非题面 v3 reaction 资产镜像 18。所有输入实时 SHA-256 留档。原 dependingv3 assets 不读，v3 evaluation 不复制；旧 dependingv4 不访问。各禁止目录在隔离树均不存在。明确 pinned 环境 PYTHONPATH、BBD_DATA_ROOT（空/不存在的隔离数据根）、V3_CODE_ROOT、V43_ASSET_ROOT、DEPENDING_V3_ROOT；无 .git/reports/data/evaluation/benchmark/gold/封存目录复制。

实际 8 skip，原输出逐项列明：

- test_analog_assets.py:95：无 dependingv4 对照源码 1。
- test_analog_v2_corpus.py:62 与 :153：未复制 provenance 与 summary 各 1。
- test_batch_runner.py:52：无真实 v3 冻结评价基准 1。
- test_score_report.py:110、:163、:172、:184：无同一评价基准共 4。

实际 17 deselect = `-m 'not slow'` 的 16 项（全部名称另存 JSON）+ 显式排除 `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` 1。后者依赖未复制的 evaluation 导出纯函数源文件；没有为凑数字复制它。慢例仅在隔离树做 collect-only 取得名称，不执行。

本次数与实施方 **1138/8/17** 一致；与 R7 独立 **1110/8/17** 分开登记，增加 28 来自 R8 两测试。**不是完整原环境 1119/16**，不是污染物或 RHEA 题域科学性能。保留 skip/deselect，不改成 pass。

G01 原始执行脚本是本轮复制的 safe_g01_r8.py，依路径白名单重新记录当前哈希。为永久可复跑性，另提供 **safe_g01_reproduce.py**：从 R7 审核方固定哈希控制器派生，仅更新 R8 HEAD、期望摘要和独立本次输入哈希两 JSON；`--prepare-only` 已成功，完整 270 输入核一致，未重跑整套 G01。实际执行仍以原始日志对应脚本为准，不把 prepare-only 当第二次完整运行。

## 可重复执行及控制器出口限制

原独立 PPV1 控制器 intentionally 收集 pytest 出口，基线红时不停止并执行 finally，最后总出口 0；**不可单凭总出口 0 认定测试成功**。已另运行 assert_ppv1_results.py，核 full 536 出口 0、current 28 出口 0、baseline 14/14 出口 1、无字段红、无 error/skip、测试文件不变、worktree 移除成功。提供 reproduce_ppv1.py wrapper，未来运行原控制器后必须执行该观察断言，失败即总出口非 0；不重复本次完整测试。

`independent_execution_as_executed.py` 对应本次控制器运行体；`independent_execution.py` 是随后仅补入 schema/cache metadata 的版本（未改测试/复制/红绿逻辑）。execution_metadata.json 的 schema/cache 信息本次是在执行结束后从已经隔离且哈希固定的源码补充，未冒充新的测试执行。

主审归档只需脚本、原测试、日志、junit、JSON metadata/hash/分类及本说明；**不要复制 src/assets/临时数据库或缓存**。assert_execution_evidence.py 是执行现场附加核验（270 输入实际副本 SHA 与 16 slow 验证），已执行出口 0；永久证据不含这些资产副本，不能在永久目录原地跑此脚本。
