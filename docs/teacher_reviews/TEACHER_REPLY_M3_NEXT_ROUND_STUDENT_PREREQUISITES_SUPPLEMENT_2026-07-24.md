# M3 下一轮实装前置输入清单（07-23 裁定补充）

日期：2026-07-24
定位：本文是 `TEACHER_REPLY_M3_TASKS_1_7_ACCEPTANCE_AND_TASK7_SCOPE_AND_SNAPSHOT_MTTQ02_2026-07-23.md` 的**补充件**，
不改动上一轮任何裁定结论，只把"下一轮 Agent 侧实装所需的学生前置输入"一次性列清并催办。
依据：
- `TEACHER_REPLY_M3_TASKS_1_7_ACCEPTANCE_AND_TASK7_SCOPE_AND_SNAPSHOT_MTTQ02_2026-07-23.md`（上一轮裁定）
- `ENZYMECAGE_METATRAITS_INTEGRATION_TECHNICAL_FRAMEWORK_2026-07-14.md`（§三 数据契约 / §八 决策点 D1–D8）
- `ENZYMECREW_M3_DEVELOPMENT_PLAN_LANGGRAPH_2026-07-17.md`

状态：上一轮学生尚未回复；我在此把欠项与新增前置输入合并成一份催办清单。**其中 D5 是所有下游动作的前提，我要求最优先交付。**

---

## 零、终极目标复述

我们要交付的完整业务链条是 **底物 → 反应（相似性 OK 检索 / 不 OK 预测）→ 酶（EnzymeCAGE 排序）→ 菌（酶→宿主菌→性状过滤→LLM 选菌）**。
当前 Agent 侧现状：**酶推荐主干（底物→反应检索→酶排序→LLM 重排→证据合成）已全实装且经晨羽真跑三案例全绿**；
缺口集中在**下半链（菌层）与反应预测 fallback**。本文列的就是补齐这两块所必需的学生输入。

---

## 一、上一轮（07-23）尚未回复的三项

我在上一轮已列，此处重申，仍然有效：

```text
[ ] ①（硬需）回传 07-22 原件 —— SHA256 应为 80a3be0c8507a6cbf4f318de0c4735aa04d7c5106c2cc759fb5af7ee9ea356c0
        用途：导师侧以原件字节替换重建稿，两侧审计链字节对齐（不影响 Task 1 PASS）
[ ] ② Task 7 按 (a)：TraitValue schema 修订契约 + not_applicable 示例（契约层交付，不落 M4b 活代码）
[ ] ③（并行，不阻塞）M3-EXT 候选二次裁定所需补充材料，待我另行安排
```

---

## 二、下一轮"可立刻动"的实装所需输入（不碰 M4b 锁定）

以下三块实装不触发 M4b 锁定门，是可以马上推进的部分。我据此要求学生提供：

### 2.1 反应预测器（打通"相似性不 OK → 预测"分支）—— **必需**

当前 `reaction_prediction_node` 是空占位（fail-closed 语义已就绪，底层预测器未接）。
我们的业务链条明确要求：相似性检索失败（不 OK）时，调用**独立的反应预测工具**生成候选反应，与检索结果合并后统一交 EnzymeCAGE。

我要求学生提供其一，并附最小契约：

```text
选项 A：逆合成/正向反应预测工具（AiZynthFinder 类）—— 给可调用入口 + 环境依赖
选项 B：LLM 生成候选反应 SMILES + 有效性校验规则
选项 C：规则库/已知降解路径模板匹配

统一契约（无论选哪个）:
  Input : substrate_smiles: str
  Output: predicted_reactions: List[{reaction_smiles, confidence, provenance}]
  约束  : 输出 SMILES 必须可被 RDKit 解析；confidence 归一化 0–1；标注预测来源
```

### 2.2 酶→菌映射的 confidence 来源确认（OrganismAggregator 前置）

聚合层（`OrganismAggregator`，无状态函数）由我方实现，但聚合排序主键
`cumulative_score = sum(enzyme_score × organism_confidence)` 依赖"酶→菌"的置信度分档。
当前我方用 UniProt REST 直连只能拿到 `organism_name + tax_id`，**缺 `evidence_level`（reviewed/unreviewed/predicted）与归一化 confidence**。

我要求学生二选一确认（对应框架 D1/D2）：

```text
路线甲：学生上线 Enzyme2OrganismTool 服务（settings.ENZYME2ORGANISM_API_URL），
        按框架 §3.2 OrganismHit 出全字段（organism_uid 用 NCBI Taxonomy/GTDB ID、
        source∈{UniProt,KEGG,both}、evidence_level、confidence）
路线乙：确认"由我方从 UniProt entry 类型（SwissProt=reviewed / TrEMBL=unreviewed）
        自行推导 evidence_level 并按 D2 硬映射 confidence"这一简化方案可接受
```

### 2.3 MicrobeSelectionAgent（LLM 选菌）—— 半装说明

LLM 后端已就绪，我方可先做到"按 `cumulative_score` 排序 + 生成理由"的半装形态。
**完整形态需要 `trait_score`，而 `trait_score` 来自 M4b 的 TraitFilterLayer**，故其完整版依赖第三节。此项不额外要学生输入，但需知悉其上限受 M4b 制约。

---

## 三、"完全实现菌层"所需输入（M4b 前置，当前堵点）

以下均为 M4b 前置。**MT-TQ-02 未闭不给 M4b 立项**（上一轮已定），故这些是打通菌层的真正堵点。

```text
[ ] ④（最优先）D5 metaTraits 预调研报告 metatraits_probe_report.md
        - 用 P0 test set Top MRR 酶反查 5–10 个宿主菌
        - 验证：接口稳定性 / 污水相关性状覆盖度 / no_robust_majority 比例 / rate limit
        - 附 5 个 sample 菌的原始 JSON（原始数据优先，不允许只交坍塌结论）
        - 成本约 0.5 天，是所有下游动作的前提 —— 我要求最优先交付
[ ] ⑤ metaTraits 数据面接入方式确认（已知 API v1 返回 404、download 面可用）
        - 明确走 bulk download 还是稳定 query 接口
        - 给出 organism_uid → traits 的数据或接口
[ ] ⑥ organism ID 体系对齐：确认酶→菌拿到的 tax_id 能否直接查 metaTraits
        （框架要 organism_uid = NCBI Taxonomy / GTDB ID），随 D5 顺带验证
[ ] ⑦ 污水 Trait 硬约束清单（好氧/厌氧、盐度、温度、pH 分级标准，框架 D4）
        - 确认污水领域有无现成分级标准；无则由我方先出草案供 review
```

---

## 四、总闸：框架 D1–D8 决策点定稿

框架 §八的 D1–D8 至今未师生 review 定稿，是 M4a/M4b/M4c 全部实装的总闸。与下一轮直接相关的：

```text
D1 宿主定义（UniProt reviewed / +KEGG / +TrEMBL）—— 我倾向 B（reviewed+KEGG）
D2 酶→菌 confidence 归一化 —— 需学生确认 UniProt 有无稳定 confidence 字段
D3 聚合排序主键 —— 我倾向 A（cumulative_score）
D4 Trait 硬约束清单谁定 —— 要问学生污水领域标准（见 ⑦）
D5 metaTraits 预调研 —— 学生本周 0.5 天（见 ④）
D6 LLM 决策层 prompt 硬约束 —— 我倾向都要（禁绕硬约束 + 每条推荐引用 ≥2 evidence）
```

我要求学生下轮 review 时对 D1–D8 逐条给出立场，我据此定稿后出实施细节文档。

---

## 五、优先级与交付渠道

**优先级（我的排序）**：

```text
P0  ④ D5 预调研（0.5 天，解锁整个菌层）
P0  ① 07-22 原件回传（硬需，审计对齐）
P1  ① 反应预测器契约（2.1）+ ② 酶→菌 confidence 确认（2.2）
P1  D1–D8 立场定稿（第四节）
P2  ⑤⑥⑦ metaTraits 数据面 / ID 对齐 / Trait 清单（随 D5 结论推进）
P2  ② Task 7 TraitValue 契约修订、③ M3-EXT 材料
```

**交付渠道**（沿用上一轮判定原则）：

```text
要"留痕/被审计"的（文档、契约、schema、JSON、原始探测 JSON、SHA256 清单）→ GitHub teacher-deliverables，
    git 天然保字节且提交历史即审计
要"被跑"的（route_b/c、d4 白名单等数据资产、4090D 上执行的代码）→ 晨羽
本文所列除反应预测器可能含可执行工具外，其余均走 GitHub；07-22 原件必须字节对齐。
```

---

本补充件不构成对 EnzymeCAGE v1、任一 case 排序结果、MetaTraits 真实世界生物学有效性的背书。
