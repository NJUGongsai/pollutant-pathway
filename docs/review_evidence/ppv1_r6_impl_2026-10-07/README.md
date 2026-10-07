# R6 实施侧回修证据(2026-10-07)

实施 HEAD:R6 提交(见交付书 §1;回修基线 = 审核锁定 293bc627f57b1f778
aa433750f7f61d00b4a9d18)。审核方永久证据目录
`docs/review_evidence/ppv1_r5_codex_2026-10-07/` 只读未动;本目录是
**实施方**复跑证据。所有探针脚本复制到新临时目录
`/private/tmp/ppv1-r6-probes` 执行(每脚本独立子目录避免 results.json
与 SQLite 互相覆盖),不在审核方证据目录创建任何数据库或覆盖日志。

## 复跑方式

```sh
repo=/Volumes/CC/Enzyme_Agent/dependingv43
P=/Users/cc/miniconda3/envs/depending43/bin/python
tmp=$(mktemp -d /private/tmp/ppv1-r6-probes.XXXXXX)
cp "$repo/docs/review_evidence/ppv1_r5_codex_2026-10-07/"*.py "$tmp/"
cd "$tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo/src"
$P -B admission_coverage_probe.py > admission_coverage_probe.output.jsonl
$P -B chemistry_boundary_probe.py > chemistry_boundary_probe.output.jsonl
$P -B storage_boundary_probe.py  > storage_boundary_probe.output.jsonl
mkdir cond && cp conditions_probe.py cond/ && (cd cond && $P -B conditions_probe.py)
cp cond/results.json conditions_probe.results.json
$P -B r4_admission_probe_recheck.py > r4_admission_probe_recheck.output.jsonl
# r4_admission_probe.py 原样脚本 exit 1 于 genuine_evidence_mutated_*:
# 篡改证据结构化拒绝(AuditContractError)是修复行为(R5 交付已记录,非回归)
$P -B r3_chemistry_probe.py / r4_chemistry_probe.py / r3_storage_probe.py / r4_storage_probe.py  # 旧控制,均 exit 0
# ppv1 全量
$P -B -m pytest -p no:cacheprovider -q <repo>/tests/test_ppv1_*.py > pytest_output.txt
```

## 文件含义

| 文件 | 内容 |
| --- | --- |
| probe_flip_summary.json | 8 组 P1 + 2 项 P2 的前后对照(v5 列 = 审核报告记录的观测值;v6 列 = 本轮回跑实测) |
| admission_coverage_probe.output.jsonl | R5-01 覆盖反例/控制 + P2 披露观测 |
| chemistry_boundary_probe.output.jsonl | R5-02 CX 输入矩阵 + R5-08 真实执行器四案例 |
| conditions_probe.results.json | R5-03/R5-04/P2-2 条件反例与控制 |
| storage_boundary_probe.output.jsonl | R5-05/R5-06/R5-07 存储反例与控制 |
| r4_admission_probe_recheck.output.jsonl | R4 admission 23 条记录复跑(逐调用捕获) |
| r3/r4 chemistry/storage/conditions | 旧控制完整复跑(记录含环境与控制,不是失败测试数) |
| pytest_output.txt | ppv1 16 文件全量 451 passed / 0 skipped |
| baseline_red_run.txt + 两个 list | 新增 70 用例在基线 293bc62 的红跑:44 failed/26 passed 及分类 |
| g01_legacy_run.txt | G01 全量 not slow 回归 |

记录数含控制。assert_observed.py 钉 R5 观测,在修复后按设计于
翻转点失败,不以旧观测值当新测试期待。
