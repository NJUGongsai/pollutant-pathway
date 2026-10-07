# R8 回修实施证据(合成公开入口)

实施日期 2026-10-07;回修基线 HEAD `858dd94c7c6c8fc387940242403d67b6b36b5313`(R7 交付
提交);本目录为 R8 实施方证据,与 R7 审核方证据目录
`docs/review_evidence/ppv1_r7_codex_2026-10-07/`(只读快照)分开。完整裁定文档:
`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R7_2026-10-07.md`;
R8 交付书:`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R8_2026-10-07.md`。

这份证据只核查状态恢复/直传首次消费与账本出现复用的工程契约,不证明污染物真实
降解路线、生物可行性、机制或泛化性能。全部结构、来源和 SQLite 为合成。SQL 只在新
建合成库准备损坏并记录零写入,接受/拒绝由公开 put/submit/from_dict/audit 观察。没有
金标、真实题面、封存逐题 run 或模型调用;G01 按安全隔离口径(见下)。执行身份以
`manifest.json` 为准(实施时 HEAD 仍为 858dd94、工作树含未提交 v8 修改——与 R7 impl
同口径,v8 交付提交在证据生成之后)。

| 文件/目录 | 证据 |
| --- | --- |
| `pytest_full_output.txt` | v8 全量 ppv1 回归:21 文件 **536 passed / 0 skipped**(508 存量 + 28 新增 R8) |
| `baseline_red_output.txt` | 28 项 R8 新测试对基线 858dd94(父提交,detached worktree):**14 failed / 14 passed**;无 import 适配——新测试顶层只用基线已存在符号;14 红全部为两项 P1 反例行为翻转(DID NOT RAISE / created→LedgerCorrupt),0 字段/缺表红;14 绿全部为正控制/基线已拒形状(分类见 manifest.json) |
| `chem/r7_chemistry_probe_replay.jsonl(+stderr)` | R7 审核方化学公共链探针在 v8 隔离复跑(脚本+src+tests 复制到 /private/tmp 新目录):55/57 条——C1_raw_*(substrate/product/H2 加 r、H2 挂 CC=O)全部由 ok/R6 翻转为 ChemicalStateError;clean/same_graph/registered_metadata/chiral_clean/C3/CX_boundary/R6_01/C6 控制保持;第 123 行 `ChemicalState.from_dict` 在 capture 外直接调用,v8 恢复入口即拒、探针在该行停止(stderr 的拒绝 traceback 即修复本身;探针脚本未修改) |
| `chem/r8_probe_completion.py(+output)` | 尾部 2 案补跑(同 capture 语义,合成夹具):C1_chiral_raw_unknown_flag → 拒;C1_chiral_raw_direct_dataclass(audit 直传绕路)→ 拒;C1_CN_only_honest_unknown_control → retain(控制保持) |
| `chem/r7_chemical_observed_assert_rerun.txt` | R7 观察断言(assert_chemical_observed.py)在 v8 输出上按设计失败(len(rows)==57——复跑 55 条);它钉住 R7 修前缺口,非修后验收线 |
| `storage/r7_storage_probe_replay.jsonl(+stderr)` | R7 审核方存储公共链探针在 v8 复跑(同 tmp,SQLite 只写 tmp):15 案完整 exit 0——first_existing_appearance_{prod_only,all}_corrupt 首提由 created=True 翻转为 Ppv1LedgerCorrupt(appearance_hash_corrupt)零写入;none_corrupt 首提拒、valid 三形状、first_reused_semantic_*、multi_occurrence 全 6 案保持 |
| `storage/r7_storage_observed_assert_rerun.txt` | R7 观察断言(storage_assert_observed.py)按设计在翻转点失败(断言 first=created=True 的钉住观察) |
| `g01_safe_isolation/` | **G01 安全隔离工程回归(R7 复审 §2 新口径)**:`safe_g01_r8.py` 以 R7 审核方同边界(路径白名单 208 仓内输入 + 2 个 r8 新测试 + 42 普通 dependingv3/src + 18 本仓非题面 v3 资产镜像;不复制 .git/reports/data/evaluation/benchmark/gold/封存/v4;pinned env;显式排除 1 export 用例)执行 => **1138 passed / 8 skipped / 17 deselected,0 failed**(195.5s);8 skip = 5 真实评价依赖 + 1 缺 v4 对照源 + 2 未复制 phase_d provenance;17 deselect = 16 slow + 1 显式排除;execution_result/preparation/input_sha256/完整 stdout/stderr 均在 |
| `safe_g01_r8.py` | 本轮安全隔离控制器(hash 记当前工作树新鲜值——实施方证据口径;R7 审核方脚本的 HEAD/hash 钉死是其独立复核要求,必然拒 v8 工作树,故本轮适配) |
| `manifest.json` | 实际 HEAD/版本/命令/基线红分类(14 行为红 + 0 字段红)/探针翻转摘要/G01 缺席依赖分类/全部附件 SHA-256 |

复跑说明:

```sh
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
# G01 安全隔离(约 3.5 分钟;输出到新 tmp,不在本目录/仓库内写任何东西)
PYTHONDONTWRITEBYTECODE=1 $PY -B $REPO/docs/review_evidence/ppv1_r8_impl_2026-10-07/safe_g01_r8.py \
  --repo $REPO --out /private/tmp/ppv1_r8_g01_NEW --python ~/miniconda3/envs/depending43/bin/python
```

探针复跑必须先把脚本复制到新临时目录(上方化学/存储探针即此模式执行,
SQLite 只写 tmp);不要在永久证据目录运行会写数据库或覆盖输出的脚本。
两个观察断言脚本(assert_*_observed)钉住 **R7 修前缺口**,在修后输出上
按设计失败,不能当回归线使用。记录数含对照,不当漏洞数。

基线红验证:`git worktree add --detach <tmp> 858dd94`,复制 2 个 r8
测试文件(无 import 适配),运行 ⇒ 14 failed / 14 passed(完整日志与
分类见 `baseline_red_output.txt` 与 `manifest.json`)。

G01 数字口径:本轮安全隔离 1138/8/17 与 R7 审核方隔离 1110/8/17 如实
分开登记;**不是**原环境 `tests/ -m "not slow"` 的 1119/16 数字(该
口径含真实 gold_routes 读取路径,与本仓零金标纪律冲突,本轮未执行);
不把 skip/deselect 改成 pass,不为凑数字读取评价基准或伪造 fixture。
