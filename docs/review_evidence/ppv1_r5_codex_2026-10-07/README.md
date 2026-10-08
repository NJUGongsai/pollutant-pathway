# R5 Codex 独立审核证据（2026-10-07）

实际审核 HEAD：`293bc627f57b1f778aa433750f7f61d00b4a9d18`。审核方只读实现，以合成结构/条件/SQLite取证；不使用 gold、真实题目、封存 run 或模型。报告：
`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R5_2026-10-07.md`。

## 证据清单与含义

| 文件组 | 实际记录 | 执行方/范围 |
| --- | --- | --- |
| admission_coverage | 9 JSONL | 主审；meta、真实双向编辑、5个audit控制/反例和观察摘要 |
| r4_admission recheck | 23 JSONL | 主审；AST逐调用捕获契约拒绝，完整继续；原fixture同时留存 |
| chemistry_boundary | 6 JSONL | 化学专项+主审复跑；meta、8输入CX矩阵、4真实执行器案例 |
| r4/r3 chemistry | 17 / 40 JSONL | 化学专项及主审完整复跑，旧脚本HEAD标题是原来源，并非实际R5版本 |
| conditions | 7 顶层案例 | 条件专项+主审复跑；内部含多个控制，结果JSON |
| r4 conditions | 19 顶层案例 | 条件专项及主审完整复跑；嵌入旧R3 AST块逐块捕获拒绝 |
| storage_boundary | 9 JSONL，无meta | 存储专项+主审复跑；首提/重放、manifest、hypothesis及旧兄弟来源 |
| r4/r3 storage | 21 / 29 JSONL | 存储专项及主审完整复跑；写SQLite只在临时脚本所在目录 |
| pytest_output | 381 passed，0 skipped | 主审复跑器3.61s；pytest_subagent_output为专项3.16s，均1条docstring warning |

记录数含环境与控制，不是失败测试数。探针 exit 0 意味案例跑完，不意味着实现符合期望。
`assert_observed.py`验证本轮观测及正控制；在修复后运行应出现相应断言失败，不能把其旧“观测值”直接当新测试期待。
SQL UPDATE/DELETE 只模拟临时数据库损坏；旧库字节比对在负例准备完成之后、只读导入之前采集。
虚拟输入集重算不是历史执行证明；数值配平不是机制/生物可行性/路径性能证明。

## 复跑

永久证据目录只读。以下命令只在新的临时目录复制源、脚本及13测试，再执行；每个脚本单独子目录，避免`results.json`和SQLite互相覆盖：

```sh
review_repo=/Volumes/CC/Enzyme_Agent/dependingv43
review_python=/Users/cc/miniconda3/envs/depending43/bin/python
review_tmp=$(mktemp -d /private/tmp/ppv1-r5-review-reproduce.XXXXXX)
PYTHONDONTWRITEBYTECODE=1 "$review_python" -B "$review_repo/docs/review_evidence/ppv1_r5_codex_2026-10-07/reproduce.py" --repo "$review_repo" --out "$review_tmp"
```

复跑器记录实际HEAD及Python/RDKit，不把原脚本旧HEAD字面值当实际源码版本。无需联网/模型；不跑全量legacy或题目实验。
环境Python3.11.16/RDKit2026.03.6，依赖沿用depending43。
旧条件fixture只读依赖 `docs/review_evidence/ppv1_r3_codex_2026-10-06/conditions_probe.py`，其哈希列入manifest；运行时重定向其`__file__`到新临时目录。
源码与测试哈希是本轮锚点；未来HEAD执行结果用于对照，不能冒充本轮锁定版本结果。

## 完整性

`manifest.json`登记所有附件、报告、审核依据、源码和测试的SHA-256。附件不含临时SQLite或真实资产。日志中临时路径仅是轨迹，不是必要永久数据依赖。
