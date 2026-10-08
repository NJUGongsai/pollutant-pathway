# S5a 回修 r2 证据封包（ppv1_s5a_rework_r2_2026-10-09）

实施 HEAD 基线 `1ef9e4840ff1be233dedcb543b967447cd591276`（直接
父 `2e1e7af`）。范围：评审 R2
`docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R2_2026-10-09.md` §4 唯一
残余 P1 S5A-02（要求侧显式非规范/键量纲不支持单位在映射首消费处
收口）+ B2 文案纠错；契约登记 evaluation-2→3 /
preregistration-template-2→3 / profile-21→22（reference-graph-1 /
split-manifest-1 不变）；criteria-v1 冻结正文与 FREEZE_RECORD
逐字节不改（`frozen_integrity.json`）。

## 执行环境与红线遵守

全部业务执行 fresh `/private/tmp`：条件探针两棵完整树（src 含
vendor/tests/pyproject/assets）+ dependingv3 普通镜像（两树共用、
只读）+ 隔离 `BBD_DATA_ROOT`/`V3_CODE_ROOT`/`DEPENDING_V3_ROOT`/
`V43_ASSET_ROOT`（固定相关环境记录于各 logs/command.json/
execution_record.json，非全部 ambient 环境）。主命令
`~/miniconda3/envs/depending43/bin/python -B`、
`PYTHONDONTWRITEBYTECODE=1`、pytest `-p no:cacheprovider`。未访问
金标/题面/封存逐题 run/dependingv4/原 v3 评价资产；真实仓 tests/
未跑全量（G01 走白名单隔离树）；零外部模型调用（mimo 请求只写
文档未发送）；判分零 LLM；无 commit/push 本目录之外的动作。

## 目录结构

- `conditions_before/`：评审方 `mimo_conditions_probe.py` +
  `assert_B1_contract.py` **逐字节复制**（SHA 与评审包
  `ppv1_s5a_codex_r2_2026-10-09/conditions/scripts/` 一致：
  `a60df6ae…` / `994e2d6a…`）在 fresh tmp、HEAD 父字节树上复跑
  ——17 个真实公开条件案（B1 六/B2 十/B3 一）完整输入输出 +
  B1 契约断言（4 FAIL/2 PASS，exit1，与评审 §4.1 一致）+ logs
  （argv/cwd/env/exit/elapsed/stdout/stderr SHA）。
- `conditions_after/`：同一对脚本、同一构造，在 r2 字节树上复跑
  ——B1 契约 **6/6 PASS exit0**（四不支持单位案降
  condition_unknown、两合法正控保持 compatible）；17 案桶 diff
  恰好 4 变 13 保持（B2/B3 零影响）。
- `flip_check.json`：B1 六案 before/after 断言行 + 17 案桶 diff
  汇总（4 changed/13 kept + 逐案 before/after 桶）。
- `frozen_integrity.json`：冻结正文（`7fd35aab…`）与 FREEZE_
  RECORD（`6e046e29…`）shasum 核验一致（r2 单元守卫在仓内树同核
  ；隔离树内 skipif 由本记录承担）。
- `ppv1/`：PPV1 全量（42 文件，r2 字节，仓内树）完整执行封包：
  argv/env/exit/elapsed/stdout/stderr SHA/junit/execution_record
  （HEAD+dirty 如实记录）——**1105 passed / 0 skipped / 0 failed，
  exit 0**（r1 1087 + 18 新）。
- `parent_baseline/`：直接父 `1ef9e48` detached worktree（父字节
  + r2 的 5 个新/更新测试文件覆盖）跑同一命令集——**15 failed /
  106 passed / 0 collection errors，exit 1**；`baseline_
  classification.json` 逐 nodeid 红绿分类：行为 10（六 B1 分类器
  四案 + 端到端四案 + 判别案 + preference 轴案）+ 字段缺失 1
  （父披露缺机读 `reason` 键 KeyError；分类 compatible 本身在父
  已正确）+ 版本字面量 4；106 绿含 B1 两正控/B2 守门/r1 20 案
  保持/事实侧三态。
- `g01/`：G01 安全隔离（R7→…→s5a→r1 谱系 +1 新输入=305 白名单
  树）：**复跑 1706 passed / 9 skipped / 17 deselected，exit 0**
  （r1 实测 1689 + 18 新 − 1 守卫隔离树内 skipif；8 旧 skip +
  1 新 skip 类别逐 nodeid 披露）；305 输入 SHA 拷贝时/运行后零
  变化；与 r1 G01 304 输入 diff：+1 新、7 个既有输入字节合法变化
  （evaluation/preregistration/profile + 4 测试文件，脚本强制集合
  一致）；7 个隔离 pyc 如实登记（`post_run_sha_result.json`）；
  `incidents.json` 登记首跑 1 failed（本交付测试守卫读 docs/ 的
  设计缺陷，改 skipif 复跑；首跑完整 stdout 未保留已注明，不计
  产品红）。
- `scripts/`：评审方两脚本逐字节副本 + 本轮 runner/分类器/G01/
  flip-check/封包脚本（全部纳哈希）。

## 封包口径

`manifest.json` + `SHA256SUMS` 覆盖本目录**全部文件**（含各子包
内嵌的 manifest/junit/stdout/stderr/controls），**只排根两个自
控制文件**（根 `manifest.json` 与 `SHA256SUMS` 本身——它们哈希
其余文件，不自哈希）；封包脚本 `scripts/seal_package.py` 本身
**纳哈希**。`shasum -c SHA256SUMS` 全过。SQLite/pyc/pytest cache/
symlink 不封包（G01 树内 7 个 pyc 只登记路径不复制度）。

## 执行事件与未执行内段（不凑全绿）

- 条件探针一次成功执行 17 案 ×2 树，无调度失败；
- r1 的 identity/必要节点/写边界专项与 40 检查本轮未复跑（已关
  项，行为由 1105/1706 里的 r1 用例守门）；
- B2 四个直接 dataclass 低层对照未复跑（P2 保持登记）；
- A1/C1 晨报 P2 未构造新夹具；
- 网络口径：探针无 socket 仪表，不宣称全局网络计数实测为零；
  本轮无网络/模型调用代码。

程序数字均为合成工程口径，不外推 dev/298；对外数字必须带题域
标签。
