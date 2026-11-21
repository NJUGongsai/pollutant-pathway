# 预注册草案：多参考披露口径 `ppv1-multi-ref-disclosure-v1`（计算前写死，不回写主成绩）

```text
preregistration_status = pending_teacher_confirmation
disclosure_metric_id = ppv1-multi-ref-disclosure-v1
allow_writeback_to_primary = false
primary_frozen_caliber = ppv1-criteria-v6
holdout_touched = false
created_on = 2026-11-21
author = 弓赛（反应预测 / 降解路径分支）
```

> - **定位**：回应《给弓赛：降解路径分支判分口径与指标分工的批复》（`TEACHER_REPLY_GONGSAI_V6_CALIBER_2026-11-18(1).md`）§2.2 与 §4 第 3 项要求：在任何多参考 Hit@k 计算执行之前，先在本预注册文件中**书面锁定**参考集来源库与版本、是否包含未审核文献路线、分母与题集是否变化、与单一参考 Hit@k 的并列方式，以及**绝不回写冻结主成绩**的硬约束。
> - **红线**：本预注册文件获老师确认前，**不得对外发布任何多参考 Hit@k 数字**；即使日后计算并披露，也**仅作为替代路线覆盖面的伴随披露表**，冻结单金标主表与 `ppv1-criteria-v6` 主口径永不被回写或覆盖。

---

## 1. 参考集来源库、冻结版本与资产 SHA256 锁定

本口径明确区分**「Tier-1 已审核生化学多参考集」**与**明确排除项**：

### 1.1 Tier-1 纳入范围（已审核环境微生物代谢与酶学反应参考库）

| 来源层级 | 来源库 / 数据包 | 仓内固定路径 / 来源说明 | 冻结版本与校验指纹（`assets/MANIFEST.json`） | 纳入边界 |
| :--- | :--- | :--- | :--- | :--- |
| **T1-A** | `BIOSYSMOdb121` 同底物兄弟 curated 路径 | 仅限同一底层公开基准内与当前题拥有**相同 `v6` 标准化起始底物**、但属于不同文献通路编号（`pathway_id != target_pathway_id`）的 curated 生物降解反应边 | 随题目元数据版本锁定；与单步 `holdout` 隔离规则对齐（禁止用留出集参考边污染调参集） | **纳入**：用于识别“同一污染物有多条公认生物降解途径”引发的单一参考假阴性 |
| **T1-B** | `EAWAG-BBD / enviPath` 环境降解反应库 | `assets/v3_reactions/eawag/donor_product.jsonl`<br>`assets/v3_reactions/library/library_full.jsonl`<br>`assets/v3_reactions/corpus_env/corpus_v1.jsonl` | `dependingv3 v3.5 frozen assets (2026-09-18)`：<br>• `donor_product.jsonl`: `9f9fba542e1247e1afe09b509706268b3efd18c20f01b6224bf5442d22e21bbb`<br>• `library_full.jsonl`: `042e9e2c2afccdd83088eb0b50d75619261fb096728a17ab108da06cb54667f3`<br>• `corpus_v1.jsonl`: `186a1dad17e9c92ac5beb0415f1b806146ac804206fc53c6e5dd941b0044b58c` | **有条件纳入（剔除已确认非生物反应）**：按 [`V44_ASSETS_ABIOTIC_CHEMICAL_AUDIT_2026-11-16.md`](V44_ASSETS_ABIOTIC_CHEMICAL_AUDIT_2026-11-16.md) 显式剔除已实锤纯化学自由基 `[OH]` 反应（`4` 条）等非生物条目 |
| **T1-C** | `Rhea` 与 `MetaNetX` 酶促反应参考库 | `assets/v3_reactions/corpus_env/corpus_v1.jsonl`<br>`assets/analog/corpus_templates_v2.jsonl` | • `corpus_v1.jsonl` (`v3.5`, SHA 见上)<br>• `corpus_templates_v2.jsonl` (`dependingv43 Phase D D2`, SHA: `fabe4e24fa37eecc3dd544b0f31a72d46d9557c941943b1a2c4a9883a6b3d6db`) | **有条件纳入（剔除纯自发/无 EC/UV 条目）**：按上述非生物审计剔除 Rhea 无 EC 纯自发/UV 光照条目（`640` 条，含 `20` 条 UV）及对应派生模板，仅保留已核酶促反应 |

### 1.2 明确排除项（不进入 Tier-1 多参考 Hit@k）

| 排除类别 | 对应资产 / 来源 | 排除原因 |
| :--- | :--- | :--- |
| **未审核文献路线与大模型生成路线** | 任何未经数据库人工 curation 或未经师姐/专家复核的文献摘录、LLM 自动抽提或自生成替代路线 | **Tier-1 明确不包含任何未审核文献路线**。若未来确需评估未审核文献补充，须单独增设独立 `Tier-2-Unreviewed` 口径并另立预注册，且必须经领域专家复核后才允许引用 |
| **纯有机合成模板库 (`USPTO`)** | `assets/analog/uspto_relaxed_index_v1.jsonl` (`28fdf6bf...`)<br>`assets/v3_reactions/templates/uspto_templates.json` (`65a5ad25...`) | 源自有机合成专利而非环境微生物酶学，不可充当“生物降解替代路线参考” |
| **非生物/光解/高级氧化纯化学条目** | `audit_abiotic_chemical_assets.py` 检出的 `CONFIRMED_ABIOTIC` 与无 EC 自发/UV 条目 | 避免把纯化学降解（臭氧/羟基自由基/UV）混作生物酶促替代路线 |

> **对来信第 2 条的直接回答**：Tier-1 多参考 Hit@k **不包含任何未审核文献路线**（仅使用上述冻结且完成非生物清洗的 `BIOSYSMOdb121`、`EAWAG-BBD/enviPath`、`Rhea/MetaNetX` 酶促 curated 参考边）。

---

## 2. 分母固定与题集一致性规则

1. **分母完全不变、100% 同一题集**：
   - 多参考 Hit@k 必须与冻结单参考 `ppv1-criteria-v6` 主口径运行在**完全相同的题集与分母**上，不允许增删题目、不允许剔除“多参考无匹配题”、也不允许改变工程失败题的留分母保守规则：
     - `[biosysmodb121·调参集 N=261]`（主单步分母 `261`）；
     - `[biosysmodb121·调参干净集 N=220]`（去噪切片 `220`）；
     - `[dev-298·调参集 N=196]`（对照域分母 `196`）；
     - `[biosysmodb121·Tuning-76]`（多步步级/路径对比固定 `76` 条通路）。
   - 两个单步 30% 留出集（`[biosysmodb121 N=156]`、`[dev-298 N=102]`）在冻结前与本预注册获批前**均严禁触碰**。
2. **身份函数与排位规则与 `v6` 逐字节同源**：
   - 多参考匹配复用 `scripts/eval/score_disclosure_v4cn.py`（SHA256 `0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f`）的同一 `ppv1-criteria-v6` 质子化不变身份、6 条不变量护栏与小分子排除清单（碳酸体系、NH₃/NH₄⁺、CN⁻/HCN、SCN⁻、H⁺/H₃O⁺），以及**同事件底物+主产物同时命中**（禁止跨事件拼答案）和同一提交序 `Hit@1 / @3 / @5` 定义。
   - **重要单调性保障**：同一系统输出下，`Multi-Ref Tier-1 命中集合 ⊇ Single-Ref v6 命中集合`；单参考已命中的题目不重新判定，仅对单参考未命中事件核查是否命中同底物的 Tier-1 已审核替代参考边。
3. **零 LLM 调用**：多参考重判全程离线、纯确定性图/字符串比对，不发起任何模型推理调用。

---

## 3. 并列列报格式与禁止回写规则

1. **标准并列列报格式（所有对外/对内报告必须成对出现，严禁单列多参考指标）**：

| 题域·分集（同一分母） | 系统 / 模型 | 冻结主成绩：`Single-Ref v6` Hit@1 / @3 / @5 *(参考命中率)* | 伴随披露：`Multi-Ref Tier-1 v6` Hit@1 / @3 / @5 *(已审核替代参考)* | 净差 `Δ = Multi − Single` | Tier-1 增量来源拆解 (`BIOSYSMOdb兄弟 / EAWAG-enviPath / Rhea-MNX`) | 未核未中 (`UNRESOLVED`, 记 NE) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| *待计算（预注册批准后填入）* | — | *冻结锚定值* | *待算* | *待算* | *待算* | *待算* |

2. **硬性禁止回写主成绩（`allow_writeback_to_primary = false`）**：
   - 多参考 Hit@k **永不回写、不修改、不替代**冻结 `ppv1-criteria-v6` 单一参考 Hit@k 主成绩表；
   - 若多参考结果改变了两个模型/系统之间的排序结论，**不得用多参考结论涂改冻结主表**，必须按照批复要求**另立披露表**，将“单参考主表结论（撞上考卷指定路线能力）”与“多参考披露表结论（撞上多库公认替代路线能力）”并列解释。
   - 对于开放路线对照任务（如未来全量 6 基模 de-leak 重测），单参考 `v6` Hit@k 与 Tier-1 多参考 `v6` Hit@k 及五态 `route_status` 分布三者分栏并报、互不混算。
