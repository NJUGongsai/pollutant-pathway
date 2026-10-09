# S5b 启动批永久证据（ppv1_s5b_launch_2026-10-09）

待审 HEAD：工作树（4fe1e0a 之上的本批改动，提交身份以 git 为准；
G01 运行时实际输入 HEAD=4fe1e0a、工作树含本轮未提交改动，见
`g01/attempt1/preparation.json` 的 `actual_input_head` 与
`working_tree_dirty_at_run`）。本轮范围：mimo r25 ⚠️P1-9 G1 配对
错位修复（契约 ppv1-evaluation-4 / profile-24，仅样本↔导出配对
语义变更）+ 老 scorer 同构核验（只读）+ 预注册冻结稿汇编
（`preregistration_pending_final_confirmation`）。**零真实模型
调用、零费用、零网络、S5b 评测/冒烟未启动、不 push。**

## 1. 目录

- `ppv1/`：PPV1 全量（44 文件，**1133 passed / 0 skipped / 0
  failed，exit 0**）——junit/stdout/stderr/执行记录（argv/cwd/
  env/exit）/文件清单。
- `parent_baseline/`：直接父 4fe1e0a detached 同字节 worktree
  红绿（7 个当前新增/更新测试文件、149 nodeid：**19 failed /
  130 passed / 0 collection errors / exit 1**；
  `execution_record.json` 的 `red_classification` 给出
  6 新配对行为 + 3 新配对披露 + 4 新契约守卫 + 1 新版本字面量 +
  5 存量版本字面量的逐 nodeid 分类，observed==declared 精确闭合；
  src/pyproject 与父同字节（git diff 为空），六测试文件以当前
  字节覆盖父测试字节、一新文件加入，均已披露）。
- `g01/`：G01 安全隔离（工程口径）。**attempt1/ 首跑即成**：
  1733 passed / 10 skipped / 17 deselected，exit 0（r3 基线
  1719 + 14 新，精确吻合）；307 白名单输入（306 r3 谱系 +
  1 新 `tests/test_ppv1_s5b_pairing.py`），前后 SHA 复验零不符；
  8 个合法变更输入 vs r3 G01 集脚本强制披露（2 src + 6 tests）；
  10 skip（8 旧类 + r2/r3 两代冻结文档守卫，docs/ 不入隔离树）
  与 17 deselect 逐 nodeid/命令级披露；7 个隔离树子进程 pyc 如实
  登记。243MB 输入副本树留 tmp 不入包
  （`attempt1/input_trees_note.json`）。`incidents.json`：零事故；
  含一次准备阶段控制器默认路径口径失败（r3 输入 SHA 路径少了
  attempt1/ 一层，修正后未跑任何测试即重试成功——如实披露，
  不计入测试尝试）。
- `frozen_integrity.json`：criteria-v1 冻结正文
  `7fd35aab…` / FREEZE_RECORD `6e046e29…` / path_context 冻结判决
  `971ad00f…` 与父及 r3 登记逐字节一致（配对语义在 evaluation
  消费侧，冻结侧零触碰）。
- `gold_leak_scan.txt`：提交前两层金标零泄漏扫描（整词精确匹配
  全零；子串层仅 'C=O' 短片段 = 合成例 'CC=O' 内部片段，非独立
  金标取值；含交付书/README 落盘后的提交前复扫补录）。
- `scripts/safe_g01_s5b_launch.py`：本轮 G01 控制器（r3 谱系适配
  ——新增输入与变更集披露；本身纳 SHA）。

## 2. 口径

- 全部合成规则级输入（CCO/CC=O/[H][H]/aerobic 等，合成 qid
  RXNG-SYNTH-* 与真实题面零重叠），零金标/题面/封存逐题 run/
  dependingv4/原 v3 评价资产访问；判分零 LLM；无外部模型调用；
  无网络；无 push。
- 业务脚本一律复制/执行于 fresh `/private/tmp`（G01 隔离树、父
  worktree、泄漏扫描对照只读件 0444 权限直接读取）；永久证据
  目录只读不建库；评审方/先前批次证据目录只读未改（本目录为
  新建）。
- 命令统一 `~/miniconda3/envs/depending43/bin/python -B`、
  `PYTHONDONTWRITEBYTECODE=1`、`OMP_NUM_THREADS=1`、pytest
  `-p no:cacheprovider`。
- `manifest.json` 与 `SHA256SUMS` 是本根唯二控制文件（不纳自身
  SHA）；其余全部实际文件（含嵌套控制件与 G01 控制器）纳
  SHA-256；`shasum -c` 全绿。

## 3. 复现

复制本包 + 相同版本 src/vendor/pyproject/assets 与 r3 谱系 G01
输入集至新 tmp，按 `ppv1/execution_record.json`、
`parent_baseline/execution_record.json`、
`g01/attempt1/preparation.json` 的 argv/env 逐条重放；不在永久
证据原地建库、不读红线资产。
