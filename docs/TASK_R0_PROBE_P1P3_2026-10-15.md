<!--
provenance: 本任务书由 catjam-coder 代理 2026-10-15 从主会话派单原文整理落盘
（/tmp/catjam-r0-probe-p1p3.md，易失件已备份）；经主会话核对**取代**同日主会话
自写的 docs/TASK_R0_PROBE_P1P3_2026-10-15.md 初稿——catjam 版修正了两处实质问题：
①本机 rdkit 解释器=conda depending43（初稿误写 HPC 侧 v44 venv）；②P1 通道口径
歧义拆双口径 A/B（初稿单口径会漏 3/4 锚点题）。CC 拍板：执行按本文件派单。
-->

# 任务书：C 资格面重设计 R0 离线探针 P1–P3（零模型/零网络/零金标）

## 0. 你是谁、在哪干

- 仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`（分支已备好，直接在上面干）。
- 解释器（唯一可用，带 RDKit 2026.03.6）：`/Users/cc/miniconda3/envs/depending43/bin/python`
  （派单原文写"v44 venv"，该 venv 只存在于 HPC 侧，本机不可得；本机唯一带 rdkit 的
  解释器就是它，仓库 docs/TASK_V44_SYNC_T4_2026-10-12.md 有"否则 conda depending43"先例。
  这是一条已登记的口径假设，不是你的失误。）
- 纪律：零模型、零网络（不 pip install、不 curl）、零金标零题面（不读 questions.jsonl
  、参考图、任何 gold 产物）、不动 src/ tests/ docs/ AGENTS.md、**不 commit 不 push**
  （产物全在 gitignored 分析目录，改完跑验证即收工）。工作树不得出现 tracked 改动。

## 1. 背景与现状（已由队长验证，直接信）

预注册书：`docs/C_COSUB_SUPPLY_REDESIGN_PREREG_2026-10-15.md` §四探针矩阵（只做 P1–P3，P4 不做）。
本轮输出全部带「族级代理面」标注：精确声明面资格 record_products 语义属 L3 实施期判，本轮不装。

| 数据源 | 路径（相对仓库根） | 已验事实 |
|---|---|---|
| 逐候选谱系 | reports/ppv1_s5b/chain13_glm/synced/batch_manifest.json | entries 298，其中 293 题有 entries[].pool_diagnostics.candidates，共 5540 行：compile_rejected 5266 / compiled 207 / merged_into 65 / pool_truncated 2；通道 analog 3797 / corpus 1421 / recorded 322 |
| sim13 清单 | reports/ppv1_s5b/chain13_glm/analysis/sim13_qids.json | 13 个 qid 的 JSON 数组 |
| cexposed 清单 | reports/ppv1_s5b/chain13_glm/analysis/cexposed_qids.json | 35 个 qid（chain13 C 门已开题） |
| 语料-环境 | assets/v3_reactions/corpus_env/corpus_v1.jsonl | record_id → donor_components/product_components |
| 语料-模板 | assets/analog/corpus_templates_v1.jsonl | record_id → mapped_lhs/rhs |
| 语料-库 | assets/v3_reactions/library/library_full.jsonl | btid#reac_id → donor_smiles/products |
| 判分 chain13 v1 | reports/ppv1_s5b/chain13_glm/synced/metrics.json.v1 | per_qid 为 list，每项 main.match_status；matched_strict=114 |
| 判分 chain13 v2 | reports/ppv1_s5b/chain13_glm/synced/metrics.json | matched_strict=119（仅参考，本任务不用） |
| 判分 chain12 | reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/metrics.json | matched_strict=130 |
| **模板脚本（必须复用）** | reports/ppv1_s5b/chain13_glm/analysis/c_redesign_base_tables.py | 族判定/解析/自检全套 |
| 模板既有产物 | reports/ppv1_s5b/chain13_glm/analysis/c_redesign_base_tables.json | rows_all_297（13 题 297 行，已含 primary_family/outcome/reason） |

## 2. 复用要求（硬性）

新脚本与模板脚本同目录，用 **import 复用，禁止复制粘贴改写**（防口径漂移）：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c_redesign_base_tables as base
```

复用：`base.FamilyMarker`、`base.build_indexes`、`base.resolve`、`base.FAMILY_PRIORITY`、
`base.sha256_of`、`base.load_jsonl`、`base.split_components`、`base.REASON_BONDED`、
`base.REPO/MAN/SIM13/CORPUS/TEMPLATES/LIBRARY` 路径常量。
族判定函数不许重写；record_key 解析（rhea:ID@L行号→corpus_v1；tpl-→templates；
<uuid>#<uuid>→library_full）一律走 `base.resolve`。

模板 main() 里的 SMARTS 自检块（正控 plp/coa_sh/benzoyl_coa/folate_dhf/udp_galnac/
adp_glucose，负控 nad/amp/h2o2/ribose1p/glucosamine + water 必须命中 H2O）——把同款
自检搬进新脚本（这段允许照抄，逐 assert 保留），结果落 JSON meta.self_test。

## 3. 精确口径定义（照此实现，遇含糊按保守假设并记录）

### 3.0 通用定义
- **族资格集合 FAM** = `FAMILY_PRIORITY` 去掉 `"其它"` 和 `"unknown"`（即 H2O/H+、O2、
  NH3、C1转移族(SAM/THF)、酰基族(CoA)、转氨族(PLP/氨基酸)、糖基、PPi、Pi、CN-）。
  primary_family 为 其它/unknown 的行一律不算资格；unknown 件数与 unresolved 件数
  单独披露，不硬猜。
- **strict 两口径**（从 metrics 的 per_qid list 取 `main.match_status == 'matched_strict'`）：
  - strict_wide（宽面）= chain13v1 strict ∪ chain12 strict（任一批 strict）
  - strict_stable（最稳面）= chain13v1 strict ∩ chain12 strict（两批都 strict）
  - 脚本内 assert len(c13v1_strict)==114、len(c12_strict)==130。
- 全批 5540 行 = batch_manifest 全部 entries 的 pool_diagnostics.candidates 逐行
  （含 outcome 为 pool_truncated/merged_into 的），脚本 assert 总数 5540 与 outcome
  计数 {compile_rejected:5266, compiled:207, merged_into:65, pool_truncated:2}。
- 全批每行都要 resolve+判族（缓存 (channel, record_key) 与组分 SMILES，参考模板做法）。

### 3.1 P1：L3 声明面下放解锁面（对 compiled 候选）

筛选基 = 全批 outcome == "compiled" 的行（207 件）。**双口径都实现、都出数**（这是
已上报的口径歧义，两个口径都是正式产物，不许只留一个、不许合并成一个）：

- **口径 A（主口径，派单正文字面）channel-face**：行.channel ∈ {"corpus","recorded"}
  且 primary_family ∈ FAM。
- **口径 B（辅口径，锚点反推）record-face**：不限通道（analog 的 tpl- 记录经
  base.resolve 解析回 corpus 记录后同样判族），primary_family ∈ FAM。
  语义：候选引用的底层记录在语料中已声明共底物。

出数（两口径各自完整一套）：
- **a** 含资格 spec 的题数 + 逐题资格行数（JSON 放逐题明细 qid→count；md 放
  族×通道聚合件数表 + 题数）；
- **b** 与 sim13 13 题的交集（题数 + qid 清单）；
- **c** 与 strict 两口径的交集（stable/wide 各一个数 + qid 清单）；同时各附
  「相对 cexposed 的新增」（(P1题集 − cexposed) ∩ strict）；
- **d** 与 cexposed 35 题的交集（题数 + qid 清单）。

### 3.2 P2：L1 前置门扩罩资格面（对 sim13 compile_rejected）

- 基线：读模板产物 c_redesign_base_tables.json 的 rows_all_297，取
  outcome=="compile_rejected" 的 289 件（assert len(rows_all_297)==297 且其 outcome
  分布为 compile_rejected 289 / compiled 6 / merged_into 2——若实际不同，停下在结论
  里报告，不许硬凑）。
- 资格 = compile_rejected ∧ primary_family ∈ FAM。
- 出数：族×reason 交叉表（件数）+ 分族小计 + reason 小计；**另附限
  channel∈{corpus,recorded} 的分栏**（P3 的 L1 全批口径与它对齐）。
- 附一行：13 题内含资格件的题数（对比预注册 §三 L1 现行"9/13 题获得救援尝试资格"）。
- 必须在 JSON meta 与 md 明确标注：**存活率上界不可算（编译能力属 L2），只出资格件数**。

### 3.3 P3：暴露面聚合

- L3 题集 = P1a 的题集（口径 A 与口径 B 各一套）。
- L1 题集（全批推及）= {qid | 存在行: outcome==compile_rejected ∧ primary_family∈FAM
  ∧ channel∈{"corpus","recorded"}}（对全批 5540 行聚合；通道限制是派单明文，无歧义）。
- 对每个面（L3-A、L3-B、L1、L3-A∪L1、L3-B∪L1）出：
  1. 题集大小；
  2. C 门打开题数 = |cexposed ∪ 面|（现行对照 |cexposed|=35；同时给裸 |面|）；
  3. ∩ strict_stable、∩ strict_wide（含 qid 清单）；
  4. 新增暴露 strict 题 = (面 − cexposed) ∩ strict（两 strict 口径各一，qid 清单）——
     这是 mimo Q4-1 硬门数字，单列表述。
- 现行基线行：cexposed 自身的 ∩strict_stable/∩strict_wide 也算出来放表首作对照。

## 4. 产物（全部落 reports/ppv1_s5b/chain13_glm/analysis/，gitignored 区）

1. `r0_probe_p1p3.py` —— 新脚本（含 §2 的 import 复用与 SMARTS 自检）。
2. `r0_probe_p1p3_data.json` —— 全量数据：meta（每个数据源 path+sha256、git HEAD/branch、
   generated_at、offline_note、**族级代理面声明**（精确 record_products 语义属 L3 实施
   期判，本轮不装）、探针≠预注册≠成绩、§3 口径定义全文、歧义登记——尤其写明口径 A/B
   并存的原因：派单正文限 corpus/recorded 通道，而锚点"4 题已知 compiled H2O spec"里
   3/4 题的 compiled H2O 只走 analog 通道、底层记录同一对 RHEA（14570/56586）；self_test）
   + P1/P2/P3 全部计数表与 qid 清单 + 全批行级明细（5540 行：qid/channel/record_key/
   outcome/reason/primary_family/family_set）。
3. `r0_probe_p1p3_summary.md` —— 大白话 + 表格；**每张表头带题域标签
   「298=RHEA 通用酶学/已见题」**，文档显著位置写 **「探针≠预注册≠成绩」** 与
   「族级代理面」标注；口径 A/B 并列呈现；自检锚点核对清单（§5 逐项，注明对上/对不上）。

## 5. 自检锚点（对不上 = 停下，在结论与 md 里如实报告，不许硬凑）

| # | 锚点 | 口径归属 |
|---|---|---|
| 1 | sim13 297 件族分布：其它103/糖基64/Pi36/H2O28/O222/PPi16/NH3、C1转移、CoA 各8/转氨4 | rows_all_297 |
| 2 | sim13 compiled 6 件全 H2O/H+（4 题）；bonded 25 件=11 distinct 记录 | rows_all_297 |
| 3 | chain13 v1 strict=114、chain12 strict=130、cexposed=35、sim13=13 | metrics/清单 |
| 4 | P1b ∩sim13 ≥ 4 题 | **仅口径 B（record-face）**；口径 A 预期只有 1 题（qid 前缀 RXNG_08d3…，其 corpus 通道 compiled H2O 2 件）——口径 A 对不上 ≥4 不是故障，是口径差异，如实披露 |
| 5 | 全批 5540 行 outcome/channel 计数 = §1 表 | batch_manifest |

锚点 1–3、5 由脚本 assert；锚点 4 在 md 里按口径 A/B 分别报告，不 assert。

## 6. 实施步骤建议

1. 先写脚本骨架：import base → SMARTS 自检（照抄模板 assert）→ 读清单与 metrics，
   assert 锚点 3/5。
2. 全批 5540 行 resolve+判族（缓存），assert 无 outcome/channel 计数偏差。
3. P1（双口径）→ P2（基线 JSON）→ P3（聚合）。
4. 写 JSON → 写 md（表格用 markdown，数字与 JSON 同源）。
5. 跑验收命令（§7），全绿后在结论里给锚点核对清单。

## 7. 验收命令（跑给你自己看，全绿才算交活）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python \
  reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3.py   # 退出码 0
python3 -m json.tool reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_data.json > /dev/null && echo JSON-OK
python3 -c "import pathlib; [print(p, p.stat().st_size) for p in map(pathlib.Path, ['reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3.py','reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_data.json','reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_summary.md'])]"
git status --porcelain | grep -v '^??' && echo TRACKED-DIRTY || echo WORKTREE-CLEAN
```

预期：脚本退出 0；JSON-OK；三产物存在且非空（md ≥ 60 行）；WORKTREE-CLEAN。

## 8. 排障提示

- `from rdkit import Chem` 失败 → 用错解释器，回到 §0 的 conda python。
- 全批判族慢 → 正常（5540 行去重后 distinct record 约 1–3k，组分判族有缓存），
  预计几分钟内；超过 15 分钟再排查。
- rows_all_297 的 outcome 分布与 §3.2 预期不符 → 停下报告，不硬凑。
- 遇本文未覆盖的口径含糊 → 按保守假设（更窄的资格面）执行，并把假设写进结论。

## 9. 回传（你的最终汇报，≤40 行）

1. 三产物路径 + 字节数；
2. P1 a/b/c/d 两口径各一行数字；P2 资格件数（全通道/限通道）一行；P3 表的关键数
   （各面题数、C门打开数、新增暴露 strict 两口径）；
3. §5 锚点核对清单逐项 对上/对不上；
4. 你做过的保守假设与发现的异常（含 unknown/unresolved 件数）。
