# S5a 回修 r3 永久证据（ppv1_s5a_rework_r3_2026-10-09）

待审 HEAD：工作树（39d739d 之上的 r3 改动，提交身份以 git 为准；
封包时 HEAD=39d739d、工作树含本轮改动，见 `g01/attempt1/
preparation.json` 的 `actual_input_head` 与 `working_tree_dirty_
at_run`）。本轮范围：评审 R3
`docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R3_2026-10-09.md` §4 唯一
P1 [S5A-05]（生产上下文首消费引用绑定）+ §5 五处 P2 文案搭车。
S5A-01/02/03/04、S4/S3、ISO-01 保持关闭不重开；S5b 未启动。

## 1. 目录

- `ppv1/`：PPV1 全量（43 文件，1119 passed / 0 skipped / 0 failed，
  exit 0）——argv/cwd/固定 env/exit/stdout/stderr/JUnit/执行记录。
- `parent_baseline/`：直接父 39d739d detached 同字节 worktree 红绿
  （6 个当前新增/更新文件、135 nodeid：**12 failed / 123 passed /
  0 collection / exit 1**；`execution_record.json` 的
  `red_classification` 给出 5 行为 + 2 字段 + 5 版本字面量的逐
  nodeid 分类，observed==declared 精确闭合；src/tests/pyproject
  与父同字节，六测试文件以当前字节覆盖父测试字节）。
- `mimo_cases/`：五案裁定与原输入复跑。
  - `scripts/probe.py`：评审 R3 mimo 专项脚本**字节忠实副本**
    （SHA256 `4e0000f2ca8cc22ef870d991421a55d43c3b1e6c5f301241f
    2dae2b0c07db9f2`，与
    `docs/review_evidence/ppv1_s5a_codex_r3_2026-10-09/mimo/
    scripts/probe.py` 一致）；`scripts/r3_cases45.py`：本轮自构造
    案 4/5 脚本（OBSERVE=1 支持观察模式；**不冒称复审已执行**：
    复审 4 号补控未执行、5 号须构造）。
  - `after/`：r3 树结果（1/2 保持、3 翻转 binding mismatch、
    4 拒+新地址合法、5 正控保持）；`before/`：父字节树结果
    （3/4 接受、events 1）。
  - `five_case_adjudication.json`：五案 before/after 裁定与逐表
    计数；`source_guard.json`：两树源码对账（after 对仓工作树、
    before 对父树逐文件 SHA）+ v3 镜像说明（source-only 副本，
    不含评价资产，git 不可用 ⇒ git_available=False，start/resume
    同根一致）；`run_meta.json`：逐 run argv/env/exit。
  - SQLite 二进制与 run 目录不入包（tmp scratch 保留；输入以
    SHA 与 JSON 结果固化）。
- `g01/`：G01 安全隔离（工程口径）。**attempt1/ 首跑即成**：
  1719 passed / 10 skipped / 17 deselected，exit 0；306 白名单输入
  （305 r2 谱系 + 1 新 `tests/test_ppv1_s5a_rework_r3.py`），前后
  SHA 复验零不符；9 个合法变更输入 vs r2 G01 集脚本强制披露；
  10 skip（8 旧类 + r2/r3 两代冻结文档守卫）与 17 deselect 逐
  nodeid/命令级披露；7 个隔离树子进程 pyc 如实登记。243MB 输入
  副本树留 tmp 不入包（`attempt1/input_trees_note.json`）。
  `incidents.json`：本轮零事故；r2 首跑日志丢失的历史登记只读
  保留在 r2 证据内，不重裁定。r2 教训已应用：每次尝试独立输出
  根、封包前不删日志。
- `frozen_integrity.json`：criteria-v1 冻结正文
  `7fd35aab…` / FREEZE_RECORD `6e046e29…` / path_context 冻结判决
  `971ad00f…` 与父及评审登记逐字节一致（S5A-05 守卫在
  production 消费侧，冻结侧零触碰）。
- `scripts/`：本轮全部执行脚本（G01 控制器、裁定/记录/收集/
  封包）——本身纳 SHA。

## 2. 口径

- 全部合成规则级输入（CCO/CC=O/[H][H]/O2/aerobic 等），零金标/
  题面/封存逐题 run/dependingv4/原 v3 评价资产访问；判分零 LLM；
  无外部模型调用；无网络；无 push。
- 业务脚本一律复制到 fresh `/private/tmp` 执行（两棵 mimo 树、
  G01 隔离树、父 worktree）；永久证据目录只读不建库；评审方
  证据目录只读未改。
- 命令统一 `~/miniconda3/envs/depending43/bin/python -B`、
  `PYTHONDONTWRITEBYTECODE=1`、pytest `-p no:cacheprovider`。
- `manifest.json` 与 `SHA256SUMS` 是本根唯二控制文件（不纳自身
  SHA）；其余全部实际文件（含嵌套控制件与封包脚本）纳
  SHA-256；`shasum -c` 全绿。

## 3. 复现

复制本包 + 相同版本 src/vendor/pyproject/assets 与 source-only
dependingv3 镜像至新 tmp，按 `run_meta.json`/`execution_record.json`
的 argv/env 逐条重放；不在永久证据原地建库、不读红线资产。
