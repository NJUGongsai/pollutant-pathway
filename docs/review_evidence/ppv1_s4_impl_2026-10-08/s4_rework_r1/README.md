# pollutant_pathway_v1 S4 回修 r1 证据（2026-10-08）

本包为 S4 回修轮（确认复核 `POLLUTANT_PATHWAY_S4_CODEX_CONFIRM_REVIEW_2026-10-08.md`
§4 四组 P1 = S4-C01/S4-C02/S4-C03/S4-C04）的实施侧证据。实施者：主会话派出的
S4 回修一次性实施 agent（本会话）。执行全部在仓外新 `/private/tmp`；本永久目录
只保存结果文件，未在本目录运行任何写库程序。

- 实际 HEAD（开工/提交前）：`8735601b75825388fe9f4a177a1131ef264054a1`（S4b 批次；
  本批修复以工作树修改交付，本地提交在证据归档后创建，哈希见交付书）。
- 新增回归的直接父基线 = 8735601（同 HEAD；四组反例即出自该树）。
- 本批源改动（`git diff 8735601 --stat -- src/ tests/`）：
  pollutant/endpoint.py、native_result.py、native_export.py、v3_projection.py、
  profile.py、runflow.py（1 行接线）＋ tests/test_ppv1_profile.py、
  test_ppv1_s4a_endpoint.py、test_ppv1_s4b_export.py（版本字面量登记更新，逐项披露）
  ＋ 新文件 tests/test_ppv1_s4_rework_r1.py（19 用例）。
  legacy/export_v3/G2/AtomTool/production.py 零触碰（legacy code_identity 52 文件
  聚合 `18007e6a…` 与父一致；两树四产物 legacy 字节专项一致，见 legacy/）。
- 环境：depending43（Python 3.11.16 / RDKit 2026.03.6 / SQLite 3.53.4）；
  `PYTHONDONTWRITEBYTECODE=1`、`-B`、`pytest -p no:cacheprovider` 全程；
  隔离源含 src（含 vendor/molecode）＋ tests ＋ pyproject ＋ configs/scripts/assets，
  普通dependingv3（src+assets，无 evaluation）副本为隔离同级根，
  父/子进程同一 V3_CODE_ROOT（准备错误与更正见
  metadata/preparation_incidents.json，如实保留）。

## 结论性数字（工程规则级；不外推 dev/298 科学性能）

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| 当前 PPV1 全量（隔离源，正式唯一有效） | **951 passed / 0 skipped / 0 failed, exit 0**（932 存量 + 19 新；34 文件） | current/ppv1_full_* |
| 当前 S4 焦点（rework 19 + s4a 35 + s4b 18） | **72 passed, exit 0** | current/s4_focus_* |
| 当前全量非 slow（隔离源，G01 同口径 deselect） | **1553 passed / 8 skipped / 17 deselected, exit 0** | current/full_nonslow_deselect_* |
| 当前全量非 slow（仓内树，不 deselect） | 1562 passed / 16 deselected（含 export charge-fixture 用例在仓内通过） | 交付书 §数字（同命令重跑） |
| 直接父 8735601（detached 稀疏 worktree，同字节 4 份测试文件） | 新文件 **19 红全部为缺拒绝/缺字段/缺签名类**；更新文件 4 版本字面量红＋72 合法绿 | baseline/ |
| G01 安全隔离（295 输入，新控制器） | **1553 passed / 8 skipped / 17 deselected, exit 0**；逐 nodeid 缺席披露 | g01/ |
| legacy 字节专项（两树各 2 run×2 产物） | 4/4 逐字节一致；52 文件聚合一致 | legacy/ |
| 确认复核 oracle（本审 7 案新库只读重捕获后） | **5 passed**（修前同一 oracle 对修前捕获数据 = 2 failed / 3 passed，历史缺口钉住不改期待） | confirm_rerun/logs/ |
| 确认复核边界控制 5 案复跑 | 5/5 断言通过 | confirm_rerun/logs/boundary_controls.stdout |
| 确认复核导出观察脚本（逐字复跑） | export_confirmation_probe.py 在 projection-binding 段 exit 1（S4-C04 修后假 native 构建拒 ⇒ 脚本钉住缺口、按修后预期失败登记）；export_supplemental_probe.py StopIteration（S4-C03 修后无可漏聚候选 ⇒ 同登记） | confirm_rerun/logs/* |
| 确认复核导出观察脚本（忠实微调复跑） | 全部反例改拒：manifest 四例 mutation 拒（manifest_core_digest）；必要引用自洽重封拒（集合闭合）；漏聚/坏 soutc 拒（build+read）；假 native 构建拒；projection-only 改内容读取拒；public_resume 正控全过 | confirm_rerun/export_*_r1_out/results.json |

## 目录

- `current/`：隔离源正式全量/焦点 junit+stdout+stderr（含两次准备失败重试记录于
  metadata，不改源码/期待，唯一有效重试）。
- `baseline/`：父 8735601 detached 稀疏 worktree（src+tests）同字节运行 4 份
  测试文件；worktree_setup.log、junit、stdout、stderr、parent_r1_classification.json
  （19 新用例逐条分类：11 行为红（缺拒绝）、5 断言红（修前输出仍
  supported/漏聚）、2 签名红（read_v3_projection 无 ledger 参数）、1 字段红
  （summary 无必要条件键）；4 版本字面量红；0 collection 红——本批新文件在
  父上可收集（模块均在 8735601 存在），属行为红，非模块缺失）。
- `confirm_rerun/`：确认复核各案复制到新 tmp 的复跑——
  scripts/（评审脚本逐字副本＋两个 *_r1.py 忠实微调版：projection-binding
  构建调用包 call() 记录拒绝；missing-outcome 狩猎改为全聚合断言＋坏 soutc 拒绝
  观察；唯一差异点在文件头注明）、logs/（全部 stdout/stderr/命令记录）、
  endpoint_probe_out/（7 案完整输入/输出/全表快照）、endpoint_contract/
  （新库 readback＋oracle 5/5 junit）、endpoint_contract_prefetch/（修前捕获
  数据副本上的 oracle 2F/3P junit——期待未改）、boundary_out/、
  export_confirm_out/（逐字脚本部分输出）、export_confirm_r1_out/、
  export_supp_out/（逐字脚本部分输出）、export_supp_r1_out/。
  各 ws 运行工作区（含 SQLite）留在 /private/tmp/s4r1_evidence（复审可查，
  二进制不封包）。
- `g01/`：新控制器 safe_g01_s4_rework_r1.py（沿 R7→…→s4b_r1 白名单谱系＋1 新
  输入 tests/test_ppv1_s4_rework_r1.py = 295 输入）、preparation.json（实际
  HEAD/dirty/固定 env/命令）、input_sha256.json（295 项，前后一致由控制器
  记录）、g01_junit.xml、g01_safe.stdout/stderr（实际 pytest 原始输出，非控制器
  JSON 替代）、g01_dependency_disclosure.json（8 skip 逐 nodeid：5 真实冻结
  评价＋1 缺 v4＋2 phase_d；16 slow＋1 显式 deselect）。运行树内出现的
  `__pycache__` 为全套件既有非 PPV1 子进程用例写入的字节码（与本批无关，
  如实登记；输入 SHA 只覆盖 .py 源，源字节一致）。
- `legacy/`：legacy_export_byte_probe（s4b_r1 脚本复用）在当前树与父 worktree
  两树执行：legA/legB 的 predictions.jsonl 与 export_metadata.json 4/4
  逐字节一致（cmp 记录于交付书）＋ probe_result sha 记录。
- `mimo/`：v18 请求送审快照（字节同仓内 docs/mimo_ppv1_chem_review_request.md
  的新增节；主会话按 AGENTS.md 通道送审，回应原文落盘 docs/）。
- `metadata/`：git_state（实际 HEAD/父/dirty 全列）、environment.json、
  preparation_incidents.json。
- `manifest.json`＋`SHA256SUMS`：全部附件相对路径哈希（manifest 自排除
  manifest.json/SHA256SUMS）。

## 边界声明

- 全部输入为合成规则级夹具（scripted/off provider；socket connect 0；
  model_requests 0）；不证明污染物路径、矿化比例、酶活性或 dev/298 科学性能。
- 未访问金标、题面、封存逐题 run、reports/data/evaluation/benchmark、
  dependingv4、冻结 v3 资产（G01 仅普通源码/准入资产白名单；dependingv3
  隔离副本只含普通 src＋assets）。
- 未调用外部模型、未 LLM 判分、未 push；旧报告/旧证据/旧 manifest 只读未回写。
- 冻结判据 ppv1-criteria-v1 正文零触碰；本批为工程契约升级（endpoint-2/
  endpoint-policy-2/native-result-2/native-export-2/native-export-policy-2/
  v3-projection-2/profile-17，runflow-5/store-10 不变），旧 run 不跨版本续跑
  （版本门拒）。
- 复现：脚本需复制到全新 tmp、按 metadata/preparation_incidents.json 的环境
  说明重建隔离源（src+vendor/tests/pyproject/configs/scripts/assets＋普通
  dependingv3 同级副本）后再运行；禁止在本永久目录运行任何写库程序。
