# pollutant_pathway_v1 S4 回修 r2 证据（2026-10-08）

本包为 S4 回修 r2 轮（复审 R2 `POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_2026-10-08.md`
§4 剩余两组 P1 = S4-C02 必要集合不由文件存在决定 / S4-C04 无 ledger 投影首读核父
来源版本；§5 P2 精度同步）的实施侧证据。实施者：主会话按 AGENTS.md 评审-回修
自动循环派出的一次性 S4 r2 实施 agent（本会话）。执行全部在仓外新
`/private/tmp`（s4r2_run / s4r2_g01 / s4r2_parent_wt / s4r2_review /
s4r2_legacy_*）；本永久目录只保存结果文件，未在本目录运行任何写库程序。

- 实际 HEAD（开工）：`0dd35d14d6539fbf134be18565f6709e852fc076`（S4 回修 r1；
  本批修复以工作树修改交付，本地提交在证据归档后创建，哈希见交付书
  `POLLUTANT_PATHWAY_S4_REWORK_DELIVERY_R2_2026-10-08.md`）。
- 新增回归的直接父基线 = 0dd35d1（同 HEAD；R2 两组反例即出自该树）。
- 本批源改动（`git diff 0dd35d1 --stat -- src/ tests/`）：
  pollutant/native_export.py（C02 必要集合闭合读+写两侧 + payload 版本门）、
  v3_projection.py（C04 无 ledger 父来源版本门）、profile.py（版本登记）＋
  tests/test_ppv1_s4b_export.py、test_ppv1_profile.py（8 处版本字面量行，其中
  1 处 future-policy 字面量按语义取 -4；3 个失败用例覆盖 7 断言行，future 用例
  父上仍绿）＋ 新文件 tests/test_ppv1_s4_rework_r2.py（11 用例）。
  legacy/export_v3/G2/AtomTool/production.py 零触碰（52 非 pollutant src 文件
  code_identity 聚合两树一致 2b32c86e…；两树四产物 legacy 字节专项 4/4 一致）。
- 环境：conda depending43、`-B`、`PYTHONDONTWRITEBYTECODE=1`、
  `pytest -p no:cacheprovider` 全程；隔离源 = src（含 vendor）+ tests + configs +
  scripts + assets + pyproject，普通 dependingv3（src+assets，无 evaluation）同级
  副本；父/子同 V3_CODE_ROOT。准备事故 2 起（缺 assets 的 7 失败、复跑目录预建
  冲突），均如实登记于 metadata/preparation_incidents.json，单次修正重跑，
  不改产品/断言。

## 结论性数字（工程规则级；不外推 dev/298 科学性能）

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| 当前 PPV1 全量（隔离源） | **962 passed / 0 skipped / 0 failed, exit 0**（951 r1 存量 + 11 新；36 文件） | current/ppv1_full_* |
| 当前 S4 焦点（r2 11 + r1 19 + s4a 35 + s4b 18） | **83 passed, exit 0** | current/s4_focus_* |
| 当前全量非 slow（隔离源，G01 同口径 deselect） | **1564 passed / 8 skipped / 17 deselected, exit 0**（1553 r1 + 11 新；首次 7 失败为准备事故 prep-1，修正后单次重跑） | current/full_nonslow_deselect_*（含 first_failed_*） |
| 仓内树全量非 slow（不 deselect） | 1573 passed / 16 deselected | 交付书（同命令重跑） |
| 直接父 0dd35d1（detached 稀疏 worktree，同字节 3 份测试文件） | 新/更新文件 **11 红 = 7 拒绝缺失行为红 + 1 字段红 + 3 版本字面量红，0 collection**；41 合法绿（含 r2 文件 3 正控） | baseline/ |
| G01 安全隔离（296 输入 = 295 r1 + 1 新，新控制器谱系） | **1564 passed / 8 skipped / 17 deselected, exit 0**；执行后对仓源逐文件 SHA 复核 0 失配；8 skip/17 deselect 逐 nodeid 披露 | g01/ |
| legacy 字节专项（两树各 2 run × 2 产物） | **4/4 逐字节一致**；52 非 pollutant src 文件聚合一致 | legacy/ |
| R2 反例逐字复跑（independent_cases.py，fresh tmp） | **C02 single_ref_missing 自洽重封读取 ACCEPTED→REFUSED；C04 unknown_export_schema / unknown_contract_profile / unknown_native_result 无 ledger 首读 ACCEPTED→REFUSED**；no_ledger_h07 / no_ledger_resealed_source 按 R2 登记的文件级边界保持 ACCEPTED（不加 DB 新鲜度门）；逐案零 DB 写、还原正控 | review_rerun/flip_comparison.json + independent/ |
| 公开正控（public_controls.py 逐字复跑） | start/resume 三次恢复/确定性重导出/六类业务计数零重复/网络 0 全过 | review_rerun/public_controls/ |
| 旧确认探针（export_confirmation/supplemental 逐字复跑） | 按 r1 已闭合缺口预期早停（fake-native build 拒 / StopIteration），未执行段单列；不把早停当通过 | review_rerun/old_probes/early_stop_registration.json |

## 目录

- `current/`：隔离源三组套件 junit+stdout+stderr（含 prep-1 首败输出
  first_failed_*）。
- `baseline/`：父 0dd35d1 detached 稀疏 worktree（src+tests）同字节运行 3 份
  测试文件；worktree_setup.log（同字节 SHA 记录）、junit、stdout、stderr、
  parent_r2_classification.json（11 红逐条分类：C02 文件+引用同删案、写入侧
  守卫案、C04 四个未知/缺失版本案与版本组案为拒绝缺失行为红；intact 变体为
  字段红（父上 r1 闭合已拒，缺 r2 新增 detail 字段）；3 版本字面量红；
  0 collection——r2 新文件在父上可收集，属行为红）。
- `g01/`：新控制器 safe_g01_s4_rework_r2.py（沿 R7→…→s4_rework_r1 白名单谱系
  + 1 新输入 = 296 输入）、preparation.json、input_sha256.json（执行后复核
  0 失配）、g01_junit.xml、g01_safe.stdout/stderr、execution_result.json、
  g01_dependency_disclosure.json（8 skip 逐 nodeid：5 真实冻结评价 + 1 缺 v4 +
  2 phase_d；16 slow + 1 显式 deselect）。
- `legacy/`：legacy_export_byte_probe（s4b_r1 脚本逐字复本，SHA 记录）在当前
  隔离树与父 worktree 两树执行；comparison.json（4 产物两两字节一致）+
  legacy_code_identity.json（52 非 pollutant src 文件聚合，两树一致；聚合方法
  为本探针自有定义：逐文件 sha256 → content_hash，与 r1 登记值 18007e6a… 的
  计法不同不互比，同一探针两树一致 + `git diff 0dd35d1 -- src` 仅 3 个
  pollutant 文件为旁证）+ commands 类记录于 metadata/commands.json。
- `review_rerun/`：R2 复审永久证据脚本逐字复本（old_script_identity.json 记
  SHA 逐字一致）到 fresh tmp 执行——independent/（逐案输入/输出/results.json/
  run_snapshots JSON，无 DB 二进制）、public_controls/、old_probes/（早停登记
  与部分输出）、independent_cases.{stdout,stderr}.txt、
  public_controls.{stdout,stderr}.txt、flip_comparison.json（修前/修后对照）。
- `scripts/`：safe_g01_s4_rework_r2.py、legacy_code_identity.py、
  seal_package.py。
- `metadata/`：git_state.json（实际 HEAD/父/dirty 全列/diff stat）、
  environment.json、commands.json（11 条执行记录：argv/cwd/exit/结果）、
  preparation_incidents.json（2 起，如实保留）。
- `mimo/`：v19 请求送审快照（字节同仓内 docs/mimo_ppv1_chem_review_request.md
  的新增节；主会话按 AGENTS.md 通道送审，回应原文落盘 docs/）。
- `manifest.json`＋`SHA256SUMS`：全部附件相对路径 SHA-256（manifest/
  SHA256SUMS 自排除）。

## 边界声明

- 全部输入为合成规则级夹具（scripted/off provider；model_requests 0；
  public_controls 记录 network_requests 0）；不证明污染物路径、矿化比例、
  酶活性或 dev/298 科学性能。
- 未访问金标、题面、封存逐题 run、reports/data/evaluation/benchmark、
  dependingv4、冻结 v3 评价资产（G01 白名单同 r1 谱系；dependingv3 隔离副本
  只含普通 src+assets；评审脚本复跑的 V3_CODE_ROOT 指向空目录）。
- 未调用外部模型、未 LLM 判分、未 push；旧报告/旧证据/旧 manifest 只读未回写
  （R2 复审 export_chain 只读引用作修前对照）。
- 冻结判据 ppv1-criteria-v1 正文零触碰（判据一–五、0d/0e 范围不动；本批为
  工程契约升级：native-export-3 / native-export-policy-3 / v3-projection-3 /
  profile-18；endpoint/native-result/runflow-5/store-10 沿 r1 不变），旧 run
  不跨版本续跑（版本门拒）。
- 复现：脚本需复制到全新 tmp、按 metadata/environment.json 重建隔离源
  （src+tests+configs+scripts+assets+pyproject＋普通 dependingv3 src+assets
  同级副本）后运行；禁止在本永久目录运行任何写库程序。
