# ppv1 S5a 实施侧证据(评测接口工程侧先行批)

日期:2026-10-08。实施方:pollutant_pathway_v1 S5a 批次唯一实施代理。
任务书:`docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`(§15 S5a
交付 + §14 工程侧先行 + §16 验收矩阵);R4 交接:
`docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R4_2026-10-08.md`(§5 P2/§8
授权搭车)。

## 执行数字

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量 | **1045 passed / 0 skipped,exit 0**(976 既有 + 69 新增) | `ppv1/`(junit + stdout/stderr) |
| G01 安全隔离 | **1647 passed / 8 skipped / 17 deselected,exit 0**(1578 r3 谱系 + 69 新) | `g01/`(完整 junit/preparation/输入 SHA 前后) |
| G01 输入身份 | **303 输入前后 SHA-256 全同**(297 r3 谱系 + 6 S5a 新输入) | `g01/input_sha256*.json` |
| 父基线红绿(同字节测试) | **12 failed + 2 collection errors / 981 passed,exit 1** | `parent_baseline/` |

父基线红分类(父 = a19960f,当前测试文件同字节完整复制):

- **2 collection 红**:`test_ppv1_s5a_schema.py` / `test_ppv1_s5a_
  evaluator.py` 在父上 import `pollutant.evaluation` /
  `reference_graph` 失败(S5a 模块不存在于父 —— 接口批真咬合);
- **3 isotope 搭车 P2 行为/字段红**:`test_presence_records_carry_
  isotope_disclosure`(P2-2)、`test_axis_detail_carries_recomputed_
  disclosures`(P2-3)、`test_donor_diagnostic_version_registered`
  (donor-diagnostic-10 登记);
- **9 版本字面量红**:profile-20 / donor-diagnostic-10(7 个修改
  测试文件中的版本断言)。

G01 缺席披露(逐项,与 r3 谱系一致;缺席不算通过):
v4 parser 对照根缺席 1(v4 不复制,红线);v2 provenance/summary 未
生成 2;v3 冻结真实评价基准缺席 5。17 deselect = 16 slow + 1 显式
排除的 charge/evaluation fixture 节点(`test_charge_fixture_cn_hits_
raw_sb_misses_neutralization_forbidden`,沿 R7→S5a 谱系)。
工程回归不外推 dev(B1 环境路径中间步骤)或 298(RHEA 通用酶学)
科学性能;合成规则级数字不当化学证据。

## 目录

- `ppv1/`:当前 PPV1 全量(37+3=40 文件,junit + stdout/stderr);
- `g01/`:安全隔离执行(完整 junit、argv/env/exit、preparation
  (HEAD/脏树/白名单谱系/期望数字)、输入 SHA-256 前后、stdout/stderr);
- `parent_baseline/`:父 a19960f 同字节测试红绿(junit + stdout/stderr);
- `scripts/`:G01 隔离脚本(与实际执行逐字节相同,fresh /private/tmp
  执行)、changed_inputs.json(6 新 + 9 改文件 SHA-256 + 环境);
- 根 `manifest.json` / `SHA256SUMS`:覆盖全部实际附件与嵌套子包
  controls,仅排根两个控制文件(manifest.json / SHA256SUMS)。

## 红线执行声明

无金标/题面/封存逐题 run/dependingv4/原 v3 评价资产访问;无外部
模型/LLM 判分;网络请求 0、费用 0(评测器模块无任何网络代码;G01
内个别测试子进程历史已知 pyc 例外沿 R4 §6 口径不声称绝对);真实
仓树内未执行 `tests/` 全量(G01 在隔离副本);所有探针在 fresh
/private/tmp 执行,不改任何旧永久证据目录(含 R4 的
ppv1_s4_codex_r4_2026-10-08/——只读取口径);criteria-v1 冻结正文
与 FREEZE_RECORD 逐字节不改;legacy/G2/AtomTool/export_v3 零触碰;
不实施 S5b。
