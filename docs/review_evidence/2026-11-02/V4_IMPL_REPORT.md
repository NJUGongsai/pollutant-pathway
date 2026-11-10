# v4 判据落码与零漂移验证报告（`matched_product_hit`）

。
> 除本行与各表标题标注外，正文按评测报告体例组织。

题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。批 `p2-298-20261026_v1card`，分母 298。

## §0 结论（合成）

| 硬门 | 要求 | 实测 | 判定 |
|---|---|---|---|
| v2 基线零漂移 | 119 strict / 86 hit@1 / 298 逐题一致 | **119 / 86 / 298 道逐题 status+rank 全等**；hit@3 112、hit@5 119、partial 39、unmatched 140 | **PASS** |
| v4 主读数（分母 298） | 156 matched / 154 hit@1 / 2 partial / 140 unmatched | **156 / 154 / 2 / 140**；另 hit@3 156、hit@5 156 | **PASS** |
| 翻转对账 | 逐 qid 与 `flips.json` 37 题相同 | **37/37 qid 集合相同、37/37 rank 相同**；0 缺失、0 多余、0 变差 | **PASS** |
| v3 并存 | v3 与 v4 同时启用都正常输出、互不改写 | v3 块 sha 与 v3 单跑**逐位相同**；v4 块 sha 与 v4 单跑**逐位相同** | **PASS** |
| 旧路径零新键 | v1/v2/v3 输出无 `criteria_v4`；v4 无 `criteria_v2` 豁免块 | 全部成立 | **PASS** |
| 测试 | 既有判分类测试全绿（无新增失败） | **561 passed / 4 failed**；4 项均为预存失败 | **PASS（条件）** |
| 生产树 / 批根 | 一行不改、只读 | 生产树三文件哈希与改动前相同；批根/runs 新文件 0 | **PASS** |

**读数解读**：matched_product_hit 156/298（52.35%），其中 154 题在首位命中（hit@1 51.68%），
仅 2 题 strict 但位序不为 1。相对 v2 baseline（119 strict / 86 hit@1）分别 +37 题、+68 题。

## §1 指标口径

`hit_v4(q) = [参考可评 ∧ P≠∅ ∧ ∃E∈Eligible(q): S ∈ R_E ∧ P ⊆ T_E]`

| 符号 | 含义 |
|---|---|
| `S` | 题目底物严格身份（`strict_identity_of`，与 v2 同一函数） |
| `P` | 参考边产物侧 `principal_product` 角色的严格身份集合 |
| `Eligible(q)` | 同题同 run、同受评步骤、已提交、参与物可解析的合法事件集合 |

**不证明**：整条反应化学正确、配平、系数、机制、酶学可行。

## §2 三次运行一致性（合成）

| 运行 | 代码 | 口径 | strict/matched | hit@1 | hit@3 |
|---|---|---|---|---|---|
| a | 生产树 | v2 | 119 | 86 | 112 |
| b | v4 副本 | v2 | 119 | 86 | 112 |
| c | v4 副本 | v4 | **156** | **154** | **156** |

a 与 b 逐题完全一致，证明副本未改变旧路径。

## §3 桶分布（合成）

| 桶 | 题数 |
|---|---|
| `matched_product_hit` | 156 |
| `product_hit_partial` | 2 |
| `unmatched_no_event` | 6 |
| `unmatched_reference_invalid` | 0 |
| `unmatched_product_mismatch` | 134 |

## §4 位次分析（合成）

| 位次 | 题数 |
|---|---|
| rank 1（计入 hit@1） | **154** |
| rank 2 | 1 |
| rank 3 | 1 |
| 未命中 | 142 |

**结论**：命中题几乎全部落在首位，位次瓶颈在本口径下已基本消失。

## §5 结论

1. v4 判据在 298 域得到 matched 156 / hit@1 154，相对 v2 基线显著提升；
2. v2 基线零漂移、v3 披露轴并存、旧路径零新键三项硬门全部通过；
3. 指标证明范围限于"声明主产物身份命中"，不外推化学正确性或酶学可行性。

## §6 复现命令

```bash
python3 -m pathway_v43.pollutant.s5b_cli score \
  --batch-root <batch_root> --runs-root <runs_root> \
  --criteria ppv1-criteria-v4
```
