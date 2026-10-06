# PPV1 R5 实施方证据(ppv1-r5-impl)

日期 2026-10-07;仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`;实施
基线 e80f459(R4 审核 HEAD),实施完成后以本目录证据留档。

本目录是**实施方**自证材料,与审核方目录 `ppv1_r4_codex_2026-10-07/`
分开保存。全部为 R4 审核探针的**原样脚本复制到新临时目录后在 v5
源码上的复跑输出**;未在审核方证据目录写任何 SQLite/覆盖任何日志
(复审 §6/§8 纪律)。

| 文件 | 内容 |
| --- | --- |
| admission.jsonl / admission.err | 主审核探针前 5 行(meta/真实诊断正控制/绑定控制/两串/六字段),在第 6 行 `genuine_evidence_mutated_edits_signature` 处以 AuditContractError(integrity) 结构化拒绝退出——**退出非 0 即修复行为**(观察脚本无捕获;篡改证据在 v5 不可继续) |
| chemistry_boundary_probe.jsonl | 17 行:新编辑协议(先增后引/错 from_order)、E/Z 轴、非四面体、DATA SGroup、联合映射门、scope 控制;真实 executor/接口合成各行如实标注 |
| conditions_probe.results.json | 19 个顶层案例完整结果:R4 反例(source_unit/same_local_phase/orphan/axis_contradiction/frozen_ior/hypothesis_mutation)全部翻转,旧控制保持;旧 R3 探针按 AST 分段复跑(4 个 catch 块为 R4 已记录的 fail-closed 拒绝,不算通过) |
| storage_boundary_probe.jsonl | 21 行:R4-09/10/02/11 场景——十类 put 拒绝、submit 拒、假设身份三入口拒绝、重放 manifest/三类 state 篡改损坏、旧导入关系/矛盾;`same_graph_alternate_raw`/`replay_normal` 为接受控制 |
| r3_chemistry_probe.jsonl | R3 原样 40 行在 v5 复跑:零异常(旧控制保持) |
| r3_storage_probe.jsonl | R3 原样 29 行:结构与拒绝逐项捕获(预期 fail-closed 行为,与 R4 审核记录同族) |
| *.err | 各探针 stderr(空即无隐藏错误;admission.err 为结构化拒绝的 traceback) |

环境 Python 3.11.16、RDKit 2026.03.6,解释器
`/Users/cc/miniconda3/envs/depending43/bin/python`。记录数含控制
与环境记录,不是失败数;脚本 exit 0 不表示问题已修——缺陷断言
的仓库化回归在 `tests/test_ppv1_r5_*.py`(基线红 58/69,11 个为
正控制)。合成计量闭合不证明机理、生物可行性或酶选择性;接口合成
例不冒称冻结执行器行为。

## 重跑方法

```bash
repo=/Volumes/CC/Enzyme_Agent/dependingv43
tmp=$(mktemp -d /private/tmp/ppv1-r5-repro.XXXXXX)
cp "$repo"/docs/review_evidence/ppv1_r4_codex_2026-10-07/*.py "$tmp/"
cd "$tmp"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$repo/src" \
  /Users/cc/miniconda3/envs/depending43/bin/python -B chemistry_boundary_probe.py
# 其余脚本同法;admission_probe.py 预期在篡改用例处 exit 1
# conditions_probe 完整结果为本目录 results.json(写自身目录)
```
