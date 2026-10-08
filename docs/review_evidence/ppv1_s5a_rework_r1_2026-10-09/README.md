# S5a 回修 r1 证据封包（ppv1_s5a_rework_r1_2026-10-09）

基线 HEAD `2e1e7af3c4bef9e98db9481167a835cabd3c088e`（评审
`docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_2026-10-09.md` §4 四组 P1
S5A-01/02/03/04 的有限回修）。全部在 fresh `/private/tmp`
（`ppv1_s5a_rework_r1/`）执行：评审探针脚本只复制 tmp 跑，真实仓
不跑 tests/ 全量、不写库；零金标/题面/封存 run/v4/原 v3 评价资产
访问，零 LLM 判分，零网络，零费用，不 push。

## 目录

- `scripts/`：探针与控制器（identity/conditions/write_boundary 探针
  —— 复制自评审 `ppv1_s5a_codex_2026-10-09/identity|conditions/
  scripts/`，仅改 ROOT/sys.path 指向本仓并在 fresh tmp 落 outputs；
  `probe_flip_check.py` before/after 翻转核对；G01 控制器沿
  `safe_g01_s5a.py` 谱系 +1 新输入；`post_run_sha_verify.py` 运行后
  输入 SHA 复核；`run_with_capture.py` argv/env/exit 捕获）。
- `probe_before/`：修复前（父行为）探针完整输出——六 scope 分案、
  必要节点六案、20 条件案（含冻结同源对照）、5 写边界案；每案含
  完整参考图/评测输入/评测输出/DB 全表快照（`known_public_run.json`
  等含 `database_after_start` 快照与 SHA）。
- `probe_after/`：修复后同案复跑输出（同构 45 文件）。
- `probe_flip_result.json`：40 项翻转/保持核对全过（六 scope 封顶、
  两相对路径越界写翻转为拒、两绝对路径案父已拒保持、合法正控
  保持、20 条件案与冻结同源一致、participants-only P2 案不进门禁
  保持）。
- `ppv1/`：PPV1 全量（41 文件，1087 passed / 0 skipped / 0 failed，
  exit0；junit + stdout/stderr + argv/env/exit/SHA 记录）。
- `parent_baseline/`：直接父 `2e1e7af` detached worktree 同字节
  （新+更新测试文件逐字节复制）5 文件执行：41 failed / 94 passed /
  0 collection errors；逐 nodeid 分类见
  `parent_classification.json`（S5A-01 行为 7 / S5A-03 行为 4 +
  披露字段 3 / S5A-02 行为 19 + 详细分类器实现缺失 1 / S5A-04 行为
  3 + 拒绝 kind 1 / 版本字面量 3）；5 条件同义正控与
  preference/scenario 轴在父基线保持绿。
- `g01/`：G01 安全隔离（沿 R7→s5a 控制器谱系 +1 新输入，304 输入
  白名单边界拷贝）：1689 passed / 8 skipped / 17 deselected，exit0
  （期望 1647 评审实测 + 42 新，recorded not enforced）；输入 SHA
  复核 `post_run_sha_result.json`（304 输入前后零变化，含源树
  244 项）；8 skip 逐项缺席披露（v4 对照根 1、v2 provenance/
  summary 2、冻结 v3 真实评价 5——与评审 §2 类别一致；17
  deselect = 16 slow + 1 显式 export 排除）。

## 边界与纪律

- 探针/评测全部合成规则级：无金标、无题面、无封存 run、无 v4、
  无原 v3 评价资产；`synthetic-placeholder-not-gold` 字面占位。
- 判分零 LLM；网络/费用为零；provider 默认关。
- G01 隔离副本白名单输入 + 逐项 skip/deselect 披露，数字不与仓内
  树数字混计；仓内仅跑 PPV1 单元/合成套件。
- 冻结正文 `POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md`
  SHA `7fd35aab…` 与 FREEZE_RECORD `6e046e29…` 逐字节未动。
- 临时 SQLite run 树不入包（`probe_before/after` 已含全表 JSON 快照
  与 SHA；fresh tmp 目录保留供复核：`/private/tmp/
  ppv1_s5a_rework_r1/`）。
- 本包与 `manifest.json`/`SHA256SUMS` 覆盖全部附件（含嵌套业务
  manifest 与子包 controls；仅排根自控制文件 manifest.json /
  SHA256SUMS 本身）。
