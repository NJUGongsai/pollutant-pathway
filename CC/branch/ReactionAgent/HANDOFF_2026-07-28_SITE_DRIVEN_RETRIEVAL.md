# HANDOFF · 位点驱动检索(解法C) · 2026-07-28

> 交给下一个窗口。本文自包含,读完即可接手。**任务:实现"位点驱动检索"以治病A(检索带不回对的变法)。**
> 上一个窗口已完成:诊断证明"改检索值得做",并选定解法C。本窗口只讨论到"决定上C + 写此 handoff"为止,**尚未开始 C 的实现**。

---

## 0. 一句话任务

把 benchmark 检索层从 **"按底物 Morgan 全分子指纹找 top-5 相似 donor"** 升级为 **"按反应位点局部环境检索——枚举 X 的候选位点,找在类似位点上发生过变法的 donor"**,目标把"对的变法被检索到"的天花板从 **41.5% 抬向 ~79.5%**。

---

## 1. 为什么做这个(决策依据,已用数据拍板)

主线是"照葫芦画瓢":给未知污染物 X → 找相似底物 → 搬来它们的变法全试一遍 → DRFP 打分排序 → 推降解产物,拼多步路径。**我们不判断 X"该"发生什么,而是把相似分子会发生的事全搬来再排序。**

benchmark(`honest_eval.py`,防作弊闭卷考试)暴露:漏斗**唯一卡点是"造出真产物"这一层**(random 692 例只有 ~28% 造得出),前面解析/检索不卡,后面打分不卡(造出来→top5 命中 ~94%)。

"造不出"拆成两种病:
- **病A · 没检索到对的变法**(占造不出的 ~72%)→ 病根在检索。
- 病B · 检索到了却施加不上(~28%)→ 病根在施加器(union 已能救一部分)。
- 病C · 测试反应自身抽不出编辑(~0.4%)→ 忽略。

**关键诊断(`diagnose_selection.py` 全量跑,本窗口完成)**——把病A 再切成 A1(库里有、排到 top-5 外,改检索能救)vs A2(全库都没有,真 novel,检索无解):

| 划分 | 检索已带回 | A1 可救 | A2 真缺失 | A1 占失败 |
|---|---|---|---|---|
| random (692) | 287 (41.5%) | **263** | 138 | **65.6%** |
| scaffold (702) | 264 (37.6%) | **276** | 154 | **64.2%** |
| reaction_family (742) | 144 (19.4%) | **325** | 266 | **55.0%** |

**结论**:检索不到的案例里 ~2/3 是"库里有、只是排到外面了"。若检索能把库存变法都捞回,random 的检索天花板可从 41.5% → **~79.5%**(287+263)/692。A2 ~20% 是硬顶,检索救不了(留给未来的泛化模型)。→ **改检索值得做,且位点驱动(对准"谁带对变法")是正解。**

结果文件:`reports/p0_attrib/selection_diagnosis.json`。

---

## 2. 系统现状:保留 / 改 / 缓(别推倒重来)

架构是模块化的三段,**只需动检索一处**:

```
① 检索  →  ② 生成候选  →  ③ 打分排序
🔧改这     (受益)          🟢保留(没卡)
```

- 🟢 **保留**:6 步框架、检索→生成→打分结构、**DRFP 打分器**(验证过 top1 77.8% vs 随机 29%,不是卡点)。
- 🔧 **改(本次唯一)**:检索——位点驱动。
- 🧹 **缓**(不急,等检索收敛再做):打分器参照去酶化——现在用"某酶的反应族"当参照,只是图个"可信参照反应集合",可换成"通用已知反应库",换数据源即可,是替换不是重写。(demov1 的酶/EC 逻辑上上个窗口已摘除,但打分器仍叫"DRFP-酶集",这是遗留矛盾,缓做。)
- ⛔ **别做**:推倒重来。

一页纸现状图:`STATUS_OVERVIEW.html`(浏览器打开)。

---

## 3. 解法C 设计意图 + 可复用积木

**核心思想**:检索的钥匙从"整个分子长得像"换成"**反应位点周围长得像**"。Morgan 全分子指纹被骨架主导、压低了反应位点权重,导致"相似分子发生的是别的反应"。位点驱动直接匹配"谁在类似的局部环境里发生过变法"。

**建议组件(待下一个窗口细化并经 brainstorming 定稿)**:

1. **donor 位点索引(离线建一次)**:对每条 train donor,取其**反应中心原子**(优先用晨羽真值 `chenyu_features.reaction_center_from_chenyu(rxn)`,回退 MCS `pipeline.extract_reaction_center`),用 `pipeline._get_env_atoms(mol, center, radius)` 抽中心周围 radius 环境,编码成**位点环境指纹**(可用以中心原子为根的 Morgan/ECFP,或 `pipeline._atom_query_smarts` 的原子不变量)。索引项:`(donor_rxn, 位点环境指纹, 该 donor 的编辑签名 edit_key)`。
2. **X 位点枚举(在线)**:枚举 X 上的候选反应位点(原子中心 / 官能团中心),各自抽同口径的位点环境指纹。
3. **位点级检索**:对 X 每个位点,在 donor 位点索引里找环境最相似的 donor 位点 → 召回其 donor + 变法。天然产出"在哪反应(WHERE)"=X 的那个位点 → 顺带缓解病B(WHERE/WHAT 解耦)。
4. **接入 benchmark**:作为 `honest_eval.GENERATOR`/检索模式的新选项(如 `site`),复用同一诚实漏斗与归因,可直接和 `smarts`/`union` 对比。

**可复用的现成积木**(都在 `core/pipeline.py` 与 `core/chenyu_features.py`):
- `reaction_center_from_chenyu(rxn)` → 真值反应中心(demo 格式,逐片段局部索引)。
- `pipeline._get_env_atoms(mol, center:Set[int], radius)` → 中心邻域原子集。
- `pipeline._atom_query_smarts(atom)` → 原子不变量 SMARTS。
- `canonical_identity.transformed_pair(rxn)` → 辅酶剥离 + 反应中心锚定后的干净 (X,Y) 对。
- `edit_script.extract_edit(x,y)` + `.key()` → 变法签名(元素×键级变化)。
- `align_transfer.transfer(donor_rxn, query_x)` → 模糊位点对齐+编辑回放(病B 的 A 生成器,位点驱动可与之衔接施加)。

---

## 4. 下一个窗口要先经 brainstorming 拍板的设计问题

上个窗口在 `/brainstorming` 流程中,选项1(先测量再对症)已完成测量。**下一步应继续 brainstorming 把解法C 设计定稿,再转 writing-plans 实现**。待定:

1. **位点粒度**:原子中心枚举?还是官能团/子结构中心?(影响候选位点数量与召回)
2. **环境编码**:半径取多少?用中心根 Morgan 还是原子不变量序列?是否含键级/芳香性?
3. **donor 中心来源**:全用晨羽真值中心?真值未命中的 donor 怎么回退(MCS / transformed_pair 锚定)?
4. **位点匹配度量**:Tanimoto?还是环境指纹 + 编辑签名联合打分?
5. **召回与 K**:每个 X 位点取几个 donor?全 X 汇总后如何去重/截断(按 edit_key 去重)?
6. **施加衔接**:位点检索命中后,施加走 SMARTS 模板还是 `align_transfer`(既然已知 WHERE,align 更自然)?

---

## 5. 如何测量(必须与现有口径一致,否则数不可信)

**同一把尺子**:实现后用 `honest_eval.py` 三划分跑,重点看 **`retrieval.edit_retrieved`(检索天花板)** 有没有从 41.5% 往 ~79.5% 抬;再用 `diagnose_selection.py` 看 **A1 被回收了多少**(A1 → retrieved)。

复现命令(工作目录 `benchmark/`,**务必** `PYTHONPATH=../core`):
```bash
cd CC/branch/ReactionAgent/benchmark
# 诊断 A1/A2(只读, 三划分, ~1s/划分)
PYTHONPATH=../core python diagnose_selection.py --out ../reports/p0_attrib/selection_diagnosis.json
# 全量诚实评估(单划分, 单生成器)
PYTHONPATH=../core python honest_eval.py --strategy random --generator smarts --out ../reports/p0_attrib/random_smarts.json
```
成功判据:位点驱动模式下 `edit_retrieved/scope` 显著高于 41.5%(random),且 `attribution.selection_failure` 明显下降、真产物命中(top5)上升。

---

## 6. 文件地图

**benchmark/**(诚实评估与诊断,均在此目录下运行,依赖 `../core`):
- `honest_eval.py` — 主评估。检索 `retrieve_donors`/`build_donor_index`(← 位点驱动要在此加新模式)、生成 `generate_candidates`(GENERATOR: smarts/align/union)、归因 `_reaction_edit_key`、漏斗+attribution+retrieval 聚合。
- `diagnose_selection.py` — 本窗口新增。A1/A2 切分诊断(只读,复用 honest_eval 口径)。
- `canonical_identity.py` — `transformed_pair`(辅酶剥离 COFACTORS + 反应中心锚定)、`main_substrate`/`main_product`/`group_key`/`canon_frags`。
- `edit_script.py` — `extract_edit` + `EditScript.key()`(变法签名)。
- `align_transfer.py` — `transfer`(A 生成器:模糊位点对齐 + 编辑回放)。
- `splits.py` — `make_split(random|scaffold|reaction_family)`,按 group_key 去重防泄漏。
- `diagnosis_a.py` — 上个窗口早期诊断脚本(参考,非本次主线)。
- `run_p0.py` — P0 批量入口。

**core/**(生产特征与工具,`PYTHONPATH=../core` 注入):
- `chenyu_features.py` — DRFP 加载/检索、`reaction_center_from_chenyu`(真值中心)、`retrieve_by_substrate`。
- `pipeline.py` — `mcs_atom_mapping`/`extract_reaction_center`/`extract_template`/`apply_template_to_molecule`/`_get_env_atoms`/`_atom_query_smarts`。
- `reaction_scorer.py` — DRFP-酶集打分(`score_candidates`/`rank_candidates`)。
- `enzyme_lookup.py` — `enzymes_for_reaction`/`reactions_for_enzyme`(打分参照族来源;去酶化时改这里的数据源)。

**demov1/**(LLM 单 agent,酶/EC 已摘除,4 个确定性工具)。**docs/visualizations/**、根目录 `STATUS_OVERVIEW.html`(现状图)。

---

## 7. 运行与环境注意

- 从 `benchmark/` 跑任何脚本都要 `PYTHONPATH=../core`(否则 `ModuleNotFoundError: chenyu_features`)。
- 数据根:`ENZYMECAGE_DATA_ROOT` 默认 `/Volumes/CC/Enzyme_Agent/depending/data`;用到 `feature/reaction/reacting_center/reacting_center.pkl` 与 `feature/reaction/drfp/rxn2fp.pkl`。
- `reacting_center.pkl` 原子索引是"整条底物串一次解析"的**全局连续编号**,`reaction_center_from_chenyu` 已用 `_global_to_per_fragment` 拆回逐片段局部索引——位点编码时注意用哪套索引。
- DRFP 打分对库外新反应现算(`reaction_scorer._drfp` 调 `drfp` 库),晨羽 enzymecage_py312 已装 0.3.7。

---

## 8. 冻结清单(本次别碰)

打分器、6步框架、demov1、splits 防泄漏逻辑、honest_eval 的四类防作弊与归因口径——**全部冻结**。本次只在检索层加"位点驱动"新模式,并用既有漏斗/诊断度量收益。A2(~20% 真 novel)不在本次射程,留给未来泛化模型。

---

### 交接状态
- ✅ 诊断完成,A1/A2 比例已切出(见 §1 表 + `selection_diagnosis.json`)。
- ✅ 决策:上解法C(位点驱动检索)。
- ⬜ 下一窗口:续 `/brainstorming` 定稿 C 设计(§4 六问)→ writing-plans → 实现 → 用 §5 口径测收益。
