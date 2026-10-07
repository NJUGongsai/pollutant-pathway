# R7 回修实施证据(合成公开入口)

实施日期 2026-10-07;审核基线 HEAD `6d9020130a481866ce2f3b79933907a33d8cfc9e`(R6
交付提交);本目录为 R7 实施方证据,与 R6 审核方证据目录
`docs/review_evidence/ppv1_r6_codex_2026-10-07/`(只读快照)分开。完整裁定文档:
`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md`;
R7 交付书:`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R7_2026-10-07.md`。

这份证据只核查表示、证明覆盖、条件及账本契约,不证明污染物真实降解路线、生物可行性、机制或泛化性能。全部结构、条件、来源和 SQLite 为合成。SQL 只在新建合成库准备损坏并记录零写入,接受/拒绝由公开 put/submit 观察。没有金标、真实题面、封存逐题 run 或模型请求。执行身份以 `manifest.json` 为准(实施时 HEAD 仍为 6d90201、工作树含未提交 v7 修改——v7 交付提交在证据生成之后)。

| 文件/目录 | 证据 |
| --- | --- |
| `pytest_full_output.txt` | v7 全量 ppv1 回归:19 文件 **508 passed / 0 skipped**(451 存量 + 57 新增 R7) |
| `g01_full_run.txt` | G01 全量 not slow:**1119 passed / 16 deselected**(611 legacy + 508 ppv1;legacy 零改动) |
| `baseline_red_output.txt` | 57 项 R7 新测试对基线 6d90201 源码:**33 failed / 24 passed**;r7_chem 对缺失常量 COMPLETION_LICENSE 仅做 import 同值字面量替换(不改断言语义,R6 同口径) |
| `admission_completion_probe.*` | R6 审核方探针在 v7 隔离复跑(R6 reproduce.py --allow-head-change):3 个复杂共底物 unknown/partial/retain;genuine/自由基氢当量正控 verified/full/expand |
| `chem/` | R6 CX 边界探针复跑:登记头后并列未知项拒(带 item 原文);RDKit 写出器含空格登记内容接受(P2);donor current/mapped/plain/target 加 \|r\| ⇒ AuditContractError(raw_input_cx_class_unregistered,带字段名);clean 输入 R6 expand;R3/R4/R5 化学探针复跑 exit 0 |
| `conditions/` | R6 条件探针复跑:`derive_launders_empty_evaluation_with_existing_signature` ⇒ ConditionContractError(context_snapshot_inconsistent/signature_row_correspondence);其余分段案例 completed |
| `storage/` | R6 存储探针复跑:四例既存行损坏首提即 Ppv1LedgerCorrupt 零写入;清单删 A 留 B / 连行删 ⇒ event_appearance_manifest_link_corrupt;只删行(留清单)⇒ entry_missing(既有控制);正常/valid 首提与重放控制保持;R3/R4/R5 存储探针复跑 exit 0 |
| `manifest.json` | 实际 HEAD/版本/命令/基线红分类(26 行为翻转 + 7 字段/表缺失)/探针翻转摘要/全部附件 SHA-256 |

复跑说明:

```sh
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
# R6 审核方探针对当前(v7)源复跑:复制源码+探针到新临时目录,不在永久目录执行
PYTHONDONTWRITEBYTECODE=1 $PY -B $REPO/docs/review_evidence/ppv1_r6_codex_2026-10-07/reproduce.py \
  --repo $REPO --out /private/tmp/ppv1_r7_verify_NEW --allow-head-change --skip-pytest
# (12 份探针入口 exit 0;assert_observed.py 按设计失败——它钉住 R6 修前缺口,
#  非修后期望;R6 README 明示该用途)
```

基线红验证:`git worktree add --detach <tmp> 6d90201`,复制 3 个 r7 测试文件
(r7_chem 的 COMPLETION_LICENSE import 换同值字面量,仅影响 import 不影响断言),
运行 ⇒ 33 failed / 24 passed(字段缺失与行为红分类见 manifest.json;24 绿全部
为正控制/基线已拒形状)。

**不要在本目录运行会写数据库/覆盖输出的脚本**;探针复跑一律复制到新临时目录
(上方命令即此模式)。记录数含对照,不当漏洞数。
