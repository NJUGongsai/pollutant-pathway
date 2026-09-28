# Phase C 二轮修复复核：独立证据包任务书

## 0. 开工事实与目标

目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43`。本任务只收集可复算证据；队长独立裁决并写 `docs/REVIEW_PHASE_C_REPAIR.md`。

| 已有资产/代码 | 当前事实 |
|---|---|
| `.crew/PHASE_C_LATEST_REPAIR.md` | 声称 P1 三层防御、三个 P2 闭合，387 passed，审计计数不变；声明不是证据 |
| `docs/EC298_PHASE_C_REVIEW_R2.md` | 四项待核实问题和反例 |
| `src/pathway_v43/{services/{prediction,report_adjudication,atom_tool,donor_applicability}.py,workflow/nodes.py}` | 修复路径已存在，工作树未提交 |
| `scripts/phase_c_offline_audit.py`、`reports/ec298/phase_c/` | 审计脚本及既有输出；必须以新目录独立重跑 |
| `tests/test_{phase_b_workflow,phase_c_workflow,phase_c_audit_guards,edit_protocol,donor_applicability}.py` | 已有针对性夹具，须检查是否真正覆盖反例 |

完成定义：提交 `docs/PHASE_C_REPAIR_EVIDENCE.md`，每项声明有独立运行命令、退出码、关键输出与文件/SHA；未复现的项目明确标为未验证，不写 APPROVED。

## 1. 必读路径与陷阱

先读交接、R2 复核和上表代码及夹具，按实际调用链记录依赖。`prediction.py` 的 rank 可选集合、`nodes.py` 的验证/提交、`report_adjudication.py` 的占位是三道不同防线；原始检索卡与新提案卡不能混淆。`donor_applicability.py` 的 RDKit 枚举缺省会截断，存储截断和评估截断不是一回事。审计脚本导入当前工作树代码并默认写入既有报告目录，必须显式 `--out-dir`，否则会污染对照。金标仅能由离线审计读取，不能进预测或调参。代码/配置在运行身份中绑定；不要用旧 run 的成功记录推断新代码可 resume。

## 2. 交付物与排除项

只交 `docs/PHASE_C_REPAIR_EVIDENCE.md`：代码位置和状态、反例/正例测试输出、全仓回归、独立审计产物及 SHA、双方改动不冲突声明的可验证边界。允许附件式独立审计输出放在运行目录外的私有临时目录，报告写明确路径和哈希。不得修改实现、原测试、资产、封存 run、金标、既有 `reports/ec298/phase_c/` 或 R2 复核；不得写终审结论、启动 Phase D、commit。

## 3. 验收与对拍

| 核对项 | 可执行命令/判据 |
|---|---|
| P1 原始 analog/rule 选中被拒、recorded 正常 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/test_phase_b_workflow.py tests/test_phase_c_workflow.py -q`；列出覆盖“选中原始卡→无事件、无产物占位”及纯裁决的测试名、实际断言 |
| 金标缺题/空/重复失败 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/test_phase_c_audit_guards.py -q`；缺一题须非零、报告缺失 qid；成功夹具须覆盖全部 qid |
| 编辑未知字段/旧别名拒绝 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/test_edit_protocol.py -q`；列出 `unknown_field` / `unknown_op` 的断言位置 |
| 1001 匹配与 2000 上限 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/test_donor_applicability.py -q`；确认上限处 `alignment_limit_exceeded` 且不得推断唯一 applicable/inapplicable |
| 全仓回归 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests python -m pytest tests/ -q`；报告退出码和通过/失败/跳过数，不能只引用交接的 387 |
| 审计对拍 | `OMP_NUM_THREADS=1 python scripts/phase_c_offline_audit.py --seal-run-dir /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1 --gold /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl --out-dir <独立空目录>`；`shasum -a 256` 对比新旧五个产物，检查 summary 中 66/66、8/23、1/22、0/15、23/43；若封存不可读明确报阻断，禁止用既有报告冒充重跑 |

核验工作树：`git status --short`、`git rev-parse HEAD`、`shasum -a 256` 对关键代码/脚本/夹具；若共享树运行中变动，记录前后 SHA，不能声称同一快照测试通过。失败须定位命令、文件和拒因。

## 4. 实施纪律

`../dependingv3`、`../dependingv4` 和封存首跑只读；本次不能改实现或资产。MANIFEST/SHA 必须校验，失败不得回退旧路径。不可用空输出代替成功，不可将结构化失败吞掉。298 为已见卷，仅 `post_hoc_repair_check`；不根据其金标设阈值、预算或供体选择。若偏离上述命令或输入，报告写实际命令、原因、影响；不得授权自行 commit。

## 5. reviewer 材料与硬门槛

报告列文件清单、命令/退出码/摘要、HEAD 与关键 SHA、封存输入及新输出 identity、逐项通过/失败、偏离记录、不可验证项。硬门槛：四项反例钉住且正例不退化，全仓回归绿，审计独立重跑计数与哈希对拍，输入未改，工作树快照一致。任一项缺证据即不通过；终审由队长独立执行并另写 `docs/REVIEW_PHASE_C_REPAIR.md`。
