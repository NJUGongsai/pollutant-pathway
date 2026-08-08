# M3 2026-07-23 / 07-24 老师任务单最终逐项回应

日期：2026-07-27  
回应对象：

1. `TEACHER_REPLY_M3_TASKS_1_7_ACCEPTANCE_AND_TASK7_SCOPE_AND_SNAPSHOT_MTTQ02_2026-07-23(1).md`
2. `TEACHER_REPLY_M3_NEXT_ROUND_STUDENT_PREREQUISITES_SUPPLEMENT_2026-07-24(1).md`

本轮新增输入：2026-07-27 生物学侧会议对 D4 soft 策略和反应预测研究路线的决定。  
状态：**逐项回应完成 / 两项生物学策略已记录 / 待验收、待授权和外部阻塞未冒充完成**

## 一、先给老师看的结论

### 1.1 本轮完成到什么程度

```text
2026-07-23 已由老师验收:
  Tasks 1-6
  SNAPSHOT_CONTRACT_DRAFT 草案

学生已经交付、等待老师确认收到或按新合同验收:
  07-22 RHEA:11880 裁定原件
  Task 7 contract-only 交付
  D5 07-24 新合同重审版

2026-07-27 生物学侧已确定:
  D4 = T1，全 soft，只作参考/建议/解释，不自动删除候选菌
  reaction prediction = A-first 三工具比较；
    弓师兄模型 + BioTransformer 3.0-ENVMICRO + enviFormer；
    三者均不满足时再考虑 C 路线

已经完成探测但结论为负:
  production MetaTraits data plane
  direct NCBI tax-ID -> MetaTraits traits 精确路径

仍未完成且没有包装成完成:
  三工具正式统一 benchmark
  enviFormer 项目 benchmark
  弓师兄模型交接和 benchmark
  新 external unseen set
  production reaction_prediction_node
  official versioned MetaTraits snapshot
  production organism_uid -> traits
  M3-EXT Stage 2
  M4b / M4c
```

### 1.2 两项生物学决定的准确含义

第一项不是删除 soft traits，而是保留它们给用户作参考、建议、解释和不确定性提示；禁止
自动 hard rejection。

第二项不是宣布 BioTransformer、enviFormer 或弓师兄模型已经胜出，而是先统一比较三者。
enviFormer 当前仍在技术验证；弓师兄模型尚待交接；BioTransformer 只有既有 product-only
小试。三个 A 路工具均不能满足最低合同时，才触发 C 路线的数据库/规则资产预研。

## 二、交付仓库与本轮入口

### 2.1 酶侧仓库

仓库：

[`EnzymeCAGE-Teacher-Deliverables`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables)

本轮更新前已核对基线：

```text
main:
  e6ee1cf22ed2b014c37af88a9880278b48f5f63c
```

本轮新增入口（与本文件同批提交）：

- [`反应预测 A-first 三工具评测决定记录`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-27_M3_P1_2_1_Reaction_Predictor_A_First_Three_Tool_Benchmark_Decision/M3_P1_2_1_REACTION_PREDICTOR_A_FIRST_THREE_TOOL_BENCHMARK_BIOLOGICAL_DECISION_RECORD_2026-07-27.md)
- [`本最终逐项回应`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_2026_07_23_24_TEACHER_TASK_LIST_FINAL_RESPONSE_2026-07-27.md)
- [`黄老师确认与最小授权请求`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_NEXT_ROUND_HUANG_TEACHER_ADJUDICATION_REQUEST_AFTER_BIOLOGICAL_DECISIONS_2026-07-27.md)

### 2.2 微生物侧仓库

仓库：

[`EnzymeCAGE-MetaTraits-Teacher-Deliverables`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables)

本轮更新前已核对基线：

```text
main:
  74013a1b10362925dea8b7bae55566b221c1169b
```

本轮新增入口（与本文件同批提交）：

- [`D4 全 soft 生物学决定记录`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-27_M3_D4_Wastewater_Trait_Soft_Policy_Decision/M3_D4_WASTEWATER_TRAIT_SOFT_POLICY_BIOLOGICAL_DECISION_RECORD_2026-07-27.md)
- [`本最终逐项回应`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/M3_2026_07_23_24_TEACHER_TASK_LIST_FINAL_RESPONSE_2026-07-27.md)
- [`黄老师确认与最小授权请求`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/M3_NEXT_ROUND_HUANG_TEACHER_ADJUDICATION_REQUEST_AFTER_BIOLOGICAL_DECISIONS_2026-07-27.md)

主回应和授权请求在两仓根目录保留同字节副本，只作为跨侧证据定位入口；酶侧和微生物侧
实际资产仍分仓存放，不互相混入。

## 三、对 2026-07-23 文档逐项回应

### 3.1 Task 1：RHEA:46976 新 Case 1

```text
状态:
  ACCEPTED_COMPLETE

完成/验收:
  2026-07-23

commit:
  694faff9b9364fb4d9c134e74deb13c62b49e935

结果:
  rhea_master_id = 46976
  ec = null
  B_pool = 0
  C_pool = 15
  known_positive = 2
  RHEA:11880 只作为公平 Top-K 自然邻居；
  不继承其 EC，不把它当等价目标反应，不借它定义 known-positive 身份
```

证据：

- [`case_1_rhea_46976.json`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/case_1_rhea_46976.json)
- [`Tasks 1/2/3/5 总交付`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/ENZYME_TASKS_1_2_3_5_FINAL_TEACHER_DELIVERY_2026-07-23.md)
- [`Task 1 审计`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-23_Enzyme_Tasks_1_2_3_5_Submission/audits/ENZYMECAGE_M3_TASK1_RHEA46976_CASE_JSON_LOCAL_AUDIT_2026-07-22.md)

本轮动作：不重做，只重新给老师定位。

### 3.2 Task 2：三案例首页角色

```text
状态:
  ACCEPTED_COMPLETE

结果:
  Case 1 = C-fallback 成功分支演示
  Case 2 = B-primary 排序统计意义
  Case 3 = 上游召回失败 fail-closed
```

证据：

- [`THREE_CASE_HOMEPAGE.md`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/THREE_CASE_HOMEPAGE.md)
- [`Task 2 审计`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-23_Enzyme_Tasks_1_2_3_5_Submission/audits/ENZYMECAGE_M3_TASK2_THREE_CASE_HOMEPAGE_ROLE_LOCAL_AUDIT_2026-07-22.md)

### 3.3 Task 3：旧 Case 1 deprecated 与 registry

```text
状态:
  ACCEPTED_COMPLETE

结果:
  RHEA:40543 原文件保留
  deprecated = true
  superseded_by = RHEA:46976
```

证据：

- [`case_1_rhea_40543.json`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/case_1_rhea_40543.json)
- [`M3_CASE_REGISTRY.json`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_CASE_REGISTRY.json)
- [`Task 3 审计`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-23_Enzyme_Tasks_1_2_3_5_Submission/audits/ENZYMECAGE_M3_TASK3_OLD_CASE1_DEPRECATION_REGISTRY_LOCAL_AUDIT_2026-07-22.md)

### 3.4 Task 5：M3-EXT shortlist

```text
状态:
  ACCEPTED_WITHIN_SCREENING_BOUNDARY

结果:
  shortlist 和外部证据筛选已完成
  未补 D4/Rhea/B/C 资产
  未跑模型
  未升级官方案例
```

证据：

- [`M3_EXT_CANDIDATE_SHORTLIST_v0.md`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_EXT_CANDIDATE_SHORTLIST_v0.md)
- [`Task 5 审计`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-23_Enzyme_Tasks_1_2_3_5_Submission/audits/ENZYMECAGE_M3_TASK5_M3_EXT_CANDIDATE_SHORTLIST_LOCAL_AUDIT_2026-07-22.md)

下一动作：等待黄老师在 MX1/MX2/MX3 中裁定；未授权前不进入 Stage 2。

### 3.5 Task 4：SNAPSHOT_CONTRACT_DRAFT

```text
状态:
  ACCEPTED_COMPLETE_AS_DRAFT

首次交付:
  2026-07-21

根目录重交/验收:
  2026-07-23

commit:
  624d62c87044a49ed0c4b60245df2eca4bc66128

覆盖:
  upstream version
  update cadence
  license
  local storage
  SHA256 and validation
  online fallback
```

证据：

- [`SNAPSHOT_CONTRACT_DRAFT.md`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/SNAPSHOT_CONTRACT_DRAFT.md)
- [`Task 4 审计`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-23_MetaTraits_Tasks_4_6_and_Task7_Decision_Request/audits/ENZYMECAGE_METATRAITS_TASK4_SNAPSHOT_CONTRACT_DRAFT_LOCAL_AUDIT_2026-07-22.md)

边界：草案已完成；official upstream version 尚未取得；M4b 未因此自动解锁。

### 3.6 Task 6：去项目名的维护方询问信

```text
状态:
  ACCEPTED_COMPLETE_AS_UNSENT_DRAFT

结果:
  对外身份已改为通用学术酶-微生物映射研究
  项目名已删除
  邮件未发送
```

证据：

- [`METATRAITS_API_INQUIRY_EMAIL_DRAFT.md`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/METATRAITS_API_INQUIRY_EMAIL_DRAFT.md)
- [`Task 6 审计`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-23_MetaTraits_Tasks_4_6_and_Task7_Decision_Request/audits/ENZYMECAGE_METATRAITS_TASK6_PROJECT_NAME_DISCLOSURE_REMOVAL_LOCAL_AUDIT_2026-07-23.md)

下一动作：只有黄老师选择 MQ1，才补真实收件人/落款并发送。

### 3.7 Task 7：TraitValue not_applicable 契约

```text
状态:
  DELIVERED_PENDING_ACCEPTANCE

完成:
  2026-07-24

commit:
  20f55d0c4769d85b7f90caaeb7e76d1a596b1ff7

结果:
  trait_name / value / reason / note 合同齐全
  not_applicable 示例齐全
  unknown、species/strain 不继承和 exact-ID 边界齐全
  无 Pydantic 活代码、字段测试、M4b 或 M4c
```

证据：

- [`TRAIT_VALUE_NOT_APPLICABLE_SCHEMA_CONTRACT.md`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/TRAIT_VALUE_NOT_APPLICABLE_SCHEMA_CONTRACT.md)
- [`Task 7 自包含包和审计`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/tree/main/2026-07-24_Task7_TraitValue_Not_Applicable_Contract)

本轮请求：请老师确认验收 contract-only 交付；不申请以 Task 7 名义直接启动 M4b。

### 3.8 07-22 RHEA:11880 裁定原件

```text
状态:
  DELIVERED_PENDING_TEACHER_ARCHIVE_ALIGNMENT

回传:
  2026-07-24

commit:
  cf06bf6e63b19c1d7cb486ba954e9a42d151da27

SHA256:
  80a3be0c8507a6cbf4f318de0c4735aa04d7c5106c2cc759fb5af7ee9ea356c0
```

证据：

- [`07-22 原件`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/TEACHER_REPLY_M3_CASE1_RHEA11880_FAIRNESS_AND_KNOWN_POSITIVE_EVIDENCE_2026-07-22.md)
- [`原字节回传包和审计`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/tree/main/2026-07-24_M3_RHEA11880_Clarification_Original_Byte_Resubmission)

本轮请求：请老师确认已用该原字节替换重建稿。

### 3.9 三案例 end-to-end 真跑

```text
责任方:
  导师侧

状态:
  TEACHER_SIDE_COMPLETE

结果:
  Case 1 PASS 9/9
  Case 2 PASS 9/9
  Case 3 PASS 3/3
```

这是 07-23 文档告知的导师侧完成结果，不是学生欠项，不重复发起 HPC。

## 四、对 2026-07-24 补充清单逐项回应

### 4.1 ① 07-22 原件

状态：学生侧已完成，见 §3.8。  
剩余动作：老师侧确认字节归档。

### 4.2 ② Task 7

状态：学生侧 contract-only 交付已完成，见 §3.7。  
剩余动作：老师验收；活代码仍等待单独 M4b 授权。

### 4.3 ③ M3-EXT

状态：v0 shortlist 已完成且符合边界，见 §3.4。  
剩余动作：黄老师 MX 裁定，不由学生自行扩线。

### 4.4 §2.1 反应预测器

#### 4.4.1 已完成的统一 A/B/C 探测

```text
状态:
  PRIOR PILOT COMPLETE

完成:
  2026-07-26

commit:
  601d0d384825e4e0fca1e2790de37db7a664c96a

answer unlock:
  25/25 PASS

independent recomputation:
  43/43 PASS

negative tests:
  6/6 PASS

BioTransformer:
  25/26 products RDKit parseable
  无满足旧合同的完整反应、合法 rank、可用 confidence

LLM best labelled model:
  product Top-1/3/5 = 4/6, 5/6, 5/6
  product-only

C-exact:
  directed Rhea Top-1/3/5 = 4/6, 5/6, 6/6
  full reaction Top-5 = 6/6
  仅为已知 Rhea 查回，不是未知反应泛化
```

证据：

- [`旧三路线裁定请求`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_P1_2_1_REACTION_PREDICTOR_ROUTE_ADJUDICATION_REQUEST_2026-07-26.md)
- [`旧三路线自包含证据包`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/tree/main/2026-07-26_M3_P1_2_1_Reaction_Predictor_Route_Adjudication)
- [`详细 A/B/C 选择材料`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/tree/main/2026-07-27_M3_P1_2_1_Reaction_Predictor_Biological_Route_Selection_Pending)

#### 4.4.2 2026-07-27 生物学侧决定

```text
状态:
  A-FIRST STRATEGY SELECTED
  THREE-TOOL FORMAL BENCHMARK NOT YET COMPLETE

工具:
  弓师兄模型
  BioTransformer 3.0-ENVMICRO
  enviFormer

测试:
  同一冻结测试和评分合同
  现有集作回归/兼容性测试
  新 external set 单独报告训练暴露状态

选择:
  比较后在 A 路线内部择优

后备:
  三个工具均不满足最低合同时，才考虑 C 路线自建数据库/规则
```

enviFormer 文献身份：

```text
Predictive modeling of biodegradation pathways using transformer architectures
Journal of Cheminformatics, 2025, 17:21
DOI 10.1186/s13321-025-00969-7
```

论文元数据已核对，但项目工具验证和 benchmark 尚未完成。弓师兄模型尚待交接。

证据：

- [`A-first 三工具决定记录`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/2026-07-27_M3_P1_2_1_Reaction_Predictor_A_First_Three_Tool_Benchmark_Decision/M3_P1_2_1_REACTION_PREDICTOR_A_FIRST_THREE_TOOL_BENCHMARK_BIOLOGICAL_DECISION_RECORD_2026-07-27.md)

本轮请求：请黄老师选择 RP1/RP2。RP1 只授权统一 benchmark，不授权 production 接入。

### 4.5 §2.2 酶→菌 confidence

该项此前已经由 MT-D2 裁定，不是学生漏做：

```text
状态:
  DECIDED_AND_IMPLEMENTED FOR V1

裁定:
  v1 不输出 organism_confidence float

保留:
  reviewed status
  annotation score
  protein existence
  KEGG multiplicity

禁止:
  LLM 创造数值
  擅自把 Swiss-Prot/TrEMBL 映射为 0-1 confidence

aggregator:
  supporting-enzyme count 降序
  NCBI taxon ID 数字升序 tie-break

tests:
  15 passed
```

证据：

- [`MT-D1-D8 权威裁定`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/authority_reference/TEACHER_REPLY_MTD5_ACCEPTED_AND_MTD1_D8_DECISIONS_2026-07-18.md)
- [`Enzyme2OrganismTool`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/implementation/microbe_crew/tools/enzyme2organism_tool.py)
- [`OrganismAggregator`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/implementation/microbe_crew/tools/organism_aggregator.py)
- [`M4A smoke report`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/implementation/microbe_crew/M4A_SMOKE_REPORT.md)
- [`既有裁定状态闭合`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/M3_P1_MICROBE_PREREQUISITES_EXISTING_DECISIONS_AND_STATUS_CLOSURE_2026-07-26.md)

本轮请求：确认继续沿用 MT-D2 C 修订版，不重新选择甲/乙。

### 4.6 §2.3 MicrobeSelectionAgent

```text
老师原文:
  本项不额外要学生输入

当前:
  可按既有聚合主键排序并生成有界理由

完整形态:
  依赖 M4b TraitFilterLayer / trait_score

M4b:
  NOT AUTHORIZED

M4c:
  NOT AUTHORIZED
```

结论：不是学生欠项。选择全 soft 也不自动启动完整 MicrobeSelectionAgent。

### 4.7 ④ D5 MetaTraits 新合同预调研

```text
状态:
  COMPLETE_AND_INDEPENDENTLY_REAUDITED

旧合同:
  07-16/07-18 已验收

07-24 新合同重审:
  已完成，等待本次验收

commit:
  48c6e80be60cca285540c65acc5dd337762ede94

补充澄清:
  324a19e820a7780bbb929ab025f90eccaac4eb5f

P0 source:
  10 个 frozen Label=1、positive_rank=1 酶

reviewed hosts:
  10 个

raw JSON:
  5 份

documented API:
  16/16 HTTP 404

website summaries:
  5/5 HTTP 200

coverage:
  oxygen 5/5
  temperature 5/5
  pH 5/5
  salinity 5/5
  wastewater metabolism 4/5
  safety/pathogenicity 4/5
  biofilm 0/5

No robust majority:
  43/597 = 7.202680%

rate limit:
  0 observed HTTP 429
  published numeric limit UNKNOWN
```

证据：

- [`D5 新合同报告`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/metatraits_probe_report.md)
- [`10 酶—宿主—MetaTraits crosswalk`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/P0_TOP_MRR_ENZYME_TO_HOST_METATRAITS_CROSSWALK.csv)
- [`D5 新合同独立审计`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/audits/METATRAITS_D5_NEW_CONTRACT_INDEPENDENT_REAUDIT_2026-07-24.md)
- [`5 份原始 JSON`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/tree/main/2026-07-24_MT_D5_Accepted_Evidence_Resubmission/raw/metatraits/samples)

结论：足够支持有界 soft-trait 预研，不足以支持 production、exact strain attribution 或
hard filtering。请老师按 07-24 新合同验收，不以旧验收代替新验收。

### 4.8 ⑤ MetaTraits 数据面

```text
学生调研和合同:
  COMPLETE

老师既有路线:
  official versioned snapshot = production primary
  maintainer inquiry = 审阅后发送
  website endpoint = experimental fallback only

当前:
  upstream_version 未取得
  documented API 16/16 HTTP 404
  website download 有界可用
  stable production organism_uid -> traits 不存在

production data plane:
  BLOCKED_EXTERNAL_OR_TEACHER
```

证据：

- [`SNAPSHOT_CONTRACT_DRAFT.md`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/SNAPSHOT_CONTRACT_DRAFT.md)
- [`D5 数据面实测`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/metatraits_probe_report.md)
- [`维护方询问信`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/METATRAITS_API_INQUIRY_EMAIL_DRAFT.md)

下一动作：请老师选择 DP1/DP2 和 MQ1/MQ2。学生不声称已提供生产接口。

### 4.9 ⑥ organism ID 对齐

```text
状态:
  COMPLETE_NEGATIVE_FINDING

NCBI TaxID direct calls:
  10/10 HTTP 404

summary tax_id:
  absent

explicit classes:
  exact_strain = 0
  exact_species = 0
  no_exact_match_established = 10

contextual:
  species-name summary only = 5
  no delivered summary = 5

production organism_uid -> traits:
  unresolved
```

证据：

- [`D5 crosswalk`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/P0_TOP_MRR_ENZYME_TO_HOST_METATRAITS_CROSSWALK.csv)
- [`显式三分类补充`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/ORGANISM_ID_ALIGNMENT_EXPLICIT_TRISTATE_SUPPLEMENT_2026-07-26.md)
- [`三分类独立审计`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-24_MT_D5_New_Contract_Reaudit_and_Resubmission/audits/METATRAITS_ORGANISM_ID_ALIGNMENT_EXPLICIT_TRISTATE_SUPPLEMENT_INDEPENDENT_AUDIT_2026-07-26.md)

这是完成后的负结果，不是“没检查”。`no_exact_match_established` 只表示现有证据未建立
精确匹配，不等于声明数据库里绝对不存在记录。

下一动作：请老师选择 ID1/ID2。

### 4.10 ⑦ 污水 Trait 策略

```text
状态:
  BIOLOGICAL POLICY SELECTED

选择:
  T1 = all soft

用途:
  reference / advice / explanation / uncertainty

禁止:
  automatic deletion
  hard rejection
  species-strain inheritance
```

具体处理：

```text
oxygen / temperature / pH / salinity:
  soft

wastewater metabolism:
  contextual soft

safety/pathogenicity:
  soft warning + manual review

biofilm:
  unknown / unused
```

证据：

- [`D4 全 soft 生物学决定记录`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-27_M3_D4_Wastewater_Trait_Soft_Policy_Decision/M3_D4_WASTEWATER_TRAIT_SOFT_POLICY_BIOLOGICAL_DECISION_RECORD_2026-07-27.md)
- [`此前 T1/T2/T3 完整证据卡`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/tree/main/2026-07-27_M3_D4_Wastewater_Trait_Biological_Selection_Pending)

边界：这是生物学政策冻结，不是 M4b/M4c 实装授权。

## 五、D1-D8 正式逐项立场

### D1 宿主定义

```text
状态:
  DECIDED_AND_IMPLEMENTED

立场:
  reviewed UniProt primary
  KEGG independent supplement
  TrEMBL v1 excluded
```

证据：§4.5 的权威裁定、工具源码和 smoke report。

### D2 酶→菌 confidence

```text
状态:
  DECIDED_AND_IMPLEMENTED

立场:
  v1 不输出 organism_confidence float
  原始证据维度分别保留
```

证据：§4.5。

### D3 聚合排序

```text
状态:
  DECIDED_AND_IMPLEMENTED

立场:
  supporting-enzyme count descending
  NCBI taxon ID numeric ascending tie-break
```

证据：[`OrganismAggregator`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/implementation/microbe_crew/tools/organism_aggregator.py)。

### D4 Trait hard/soft

```text
状态:
  BIOLOGICALLY CONFIRMED

立场:
  T1 all soft
  reference/advice/explanation only
  no automatic deletion
```

证据：§4.10。

### D5 MetaTraits 预调研

```text
状态:
  OLD CONTRACT ACCEPTED
  07-24 NEW CONTRACT REAUDITED_PENDING_ACCEPTANCE
```

证据：§4.7。

### D6 LLM prompt 约束

```text
状态:
  CONTRACT_DECIDED / M4C NOT AUTHORIZED

立场:
  禁止绕过确定性约束
  每个正向推荐至少 2 条可追溯 evidence
  证据不足返回 insufficient_evidence/unknown
  No robust majority 和冲突进入 uncertainty_flags
```

全 soft 决定不允许 LLM 把 soft evidence 改写成 hard exclusion。

### D7 crew 边界

```text
状态:
  DECIDED

立场:
  独立 MicrobeCrew
```

M4a 工具已在独立 `microbe_crew/` 交付；M4b/M4c 仍锁定。

### D8 checkpoint 预加载

```text
状态:
  DECIDED

立场:
  A = 启动时预加载
```

证据：

- [`M4a teacher review package`](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/tree/main/2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request)

结论：D1-D8 均已有正式立场；D4 已由本轮生物学会议确认继续 T1。活代码范围仍受
M4b/M4c 授权门限制。

## 六、老师本轮需要确认或裁定什么

完整勾选卡：

- [`M3_NEXT_ROUND_HUANG_TEACHER_ADJUDICATION_REQUEST_AFTER_BIOLOGICAL_DECISIONS_2026-07-27.md`](https://github.com/bgruiiii/EnzymeCAGE-Teacher-Deliverables/blob/main/M3_NEXT_ROUND_HUANG_TEACHER_ADJUDICATION_REQUEST_AFTER_BIOLOGICAL_DECISIONS_2026-07-27.md)
- [微生物侧同字节入口](https://github.com/bgruiiii/EnzymeCAGE-MetaTraits-Teacher-Deliverables/blob/main/M3_NEXT_ROUND_HUANG_TEACHER_ADJUDICATION_REQUEST_AFTER_BIOLOGICAL_DECISIONS_2026-07-27.md)

### 6.1 只需确认收到/验收

```text
[ ] 07-22 原件已完成老师侧字节归档
[ ] Task 7 contract-only 交付验收
[ ] D5 07-24 新合同重审版验收
[ ] MT-D2 和 D1-D8 既有裁定继续有效，D4 采用本轮 T1
```

### 6.2 只需在冻结选项中裁定

```text
DP:
  是否允许 unversioned candidate 仅作 offline_nonproduction 工程准备

ID:
  species summary 是否只作 contextual soft evidence

MQ:
  是否发送已验收维护方询问信

RP:
  是否授权一次 A-first 三工具统一 benchmark

MX:
  M3-EXT 是否继续锁定或开放有界预研

IM:
  M4b/M4c 是否继续锁定，或只开放 M4b 最小 soft-only 启动包
```

这些选择不要求老师现场设计接口、提示词、阈值或数据库。每个选项的允许范围和禁止范围
已在勾选卡中写清。

## 七、尚未完成和不得越界的内容

```text
三工具正式统一 benchmark:
  未完成

enviFormer project benchmark:
  未完成，技术验证进行中

弓师兄模型:
  未完成交接和测试

external unseen set:
  未冻结

FULL_FORMAL vs MAJOR_PAIR:
  HPC 探索实验仍在继续，不作为本轮已完成结论

production reaction_prediction_node:
  未修改

C database/rule asset:
  未建设

official versioned MetaTraits snapshot:
  未取得

production organism_uid -> traits:
  未闭合

M3-EXT Stage 2:
  未启动

MicrobeTraitTool / TraitFilterLayer:
  未启动

完整 MicrobeSelectionAgent:
  未启动

M4b / M4c:
  未授权
```

## 八、提交完整性声明

```text
07-23 条目:
  全覆盖

07-24 原始响应行:
  ①②③ + 2.1/2.2/2.3 + ④⑤⑥⑦ + D1-D8
  18/18 均已回应

此前已做:
  重新给出日期、commit 和 GitHub 路径

新决定:
  单独留痕，不覆盖 07-26 pending 选择材料

负结果:
  不写成未做，也不写成成功生产链路

待验收:
  不写成老师已接受

待授权:
  不自动执行

酶/微生物资产:
  分仓保存
```

本回应只用于逐项定位结果、记录生物学选择并请求最小裁定，不构成黄老师已经验收本轮
新增材料，也不构成对任一工具、MetaTraits production、M3-EXT、M4b 或 M4c 的执行授权。

