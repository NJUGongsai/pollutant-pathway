# M3-P0 逐项裁定 & M3 正式实施合同

日期：2026-07-17  
上游：`ENZYMECAGE_M3_P0_PREIMPLEMENTATION_CLARIFICATION_AND_ROUTE_ADJUDICATION_REQUEST_2026-07-17.md`（学生交付）  
状态：M3-P0 四项决策裁定完成 / M3-P1 授权启动

---

## 一、总体评价

**M3-P0 前置澄清通过。** 三个质量点：

1. **查询泄漏自觉修正**：M3-P0B 发现 B 索引包含查询反应自身正例行，主动拒绝并重新构建 M3-P0B1 公平基准。这是方法论自觉，不是形式合规
2. **B/C 互补性数据扎实**：公平排除后 BOTH=77 / B_ONLY=14 / C_ONLY=169 / NEITHER=190，完整呈现了"两路都不能单独保证正确酶入池"的真实图景
3. **三层分离治理建议**：`biological_candidate_universe` / `d4_computable_asset_pool` / `asset_completion_queue` 的提出超越了当前 M3 任务范围，是有价值的架构级思考，后续 M4/M5 可参考

---

## 二、逐项裁定

### M3D1：case 选择 → **采纳 A（受限 C*）**

```text
1 个 strong 污水 plausible case
+ 1 个 medium 污水 plausible case
+ 1 个 weak P0 技术边界 case（不宣称污水相关）
```

**补充裁定**：9 个候选的 B/C pool 召回数据必须作为 case 选择的硬约束。具体指导见第三节。

### M3D2：pool 来源 → **采纳 A（B-primary / C-fallback，pool >100 fail closed）**

**数据验证**：严格 B-primary/C-fallback 与 B+C 并集的效果差距极小（最多差 2 个 query），因为 B 非空时命中率已达 97.8%（91/93）。学生建议的实现复杂度更低、pool 更小，合理。

**补充裁定**：
- pool >100 fail closed 是 M3 v1 的硬约束，不静默截断
- 每个 case 必须同时保存 B、C 的独立候选结果和 provenance，即使只用了一路
- `B_ONLY=14` 和 `C_ONLY=169` 证明互补性存在，M3 v1 不做并集但不否定后续混合路线

### M3D2E：域外候选资产 → **采纳 A（保持 D4 冻结资产域）**

M3 是 demo，不是生产系统。域外候选保留 provenance 并标记未评分，不在 M3 内生成新资产。

**后续路径明确**：学生提出的三层分离（候选全集 / 可计算资产池 / 资产补齐队列）是 M4/M5 的参考架构，但 M3 不启动。若 M4 阶段需要资产补齐，另行立项并提交完整合同（来源、成本、失败率、兼容性验证）。

### M3D3：Agent 实现深度 → **采纳 A（retrieved-only、资产域内、最小可用版）**

确认运行域：

```text
Substrate Agent：只完成 3 个已裁定 case 的确定性底物解析与 provenance 输出
Reaction Agent：只返回固定库中 retrieved、可追溯、具有 D4 资产的反应
CandidateReaction.source：M3 v1 实际只产生 "retrieved"
fallback_used：M3 v1 正常路径固定为 false
无匹配或缺资产：明确 fail closed，不伪装成 predicted fallback
```

不修改 schema，不增加 "unsupported" 字段，不把异常写成成功输出。

### M3D4：验收标准 → **采纳 A（B：链路跑通 + 人工审核，学生自审 + 老师复核）**

确认三层审核顺序：

```text
学生基于证据逐 case 自审
→ 老师最终复核
→ 外部专家可选/延后，不作为 M3 demo 收官硬门槛
```

定量结果必须逐 case 披露，不因采用 B 而省略。学生列出的 8 项记录要求全部保留。

---

## 三、case 选择具体指导

9 个污水候选的 B/C pool 召回数据是 case 选择的硬约束。当前数据：

| 候选反应 | 难度/rank | EC | B pool/recover | C pool/recover | 适合做 case？ |
|---|---|---|---|---|---|
| 10-deoxymethymycin hydroxylation | strong/1 | 1.14.15.33 | 1/1 | 5/1 | ✅ **strong 首选**：B/C 都召回，pool 小 |
| (S)-6-hydroxynicotine oxidation | strong/2 | 无 | 0/0 | 15/2 | ✅ **strong 备选**：C 召回 2 个正确 UID，pool 可控 |
| spectinomycin adenylylation | strong/4 | 无 | 0/0 | 1472/5 | ⚠️ pool 太大（1472），>100 fail closed |
| streptomycin phosphorylation | strong/3 | 2.7.1.87 | 0/0 | 51/0 | ❌ 正确 UID 未入池 |
| 10-deoxymethynolide glycosylation | strong/4 | 2.4.1.277 | 0/0 | 11/0 | ❌ 正确 UID 未入池 |
| ribostamycin-related glycosylation | strong/5 | 2.4.1.285 | 0/0 | 84/0 | ❌ 正确 UID 未入池 |
| rifampicin phosphorylation | strong/1 | 2.7.9.6 | 0/0 | 291/0 | ❌ 正确 UID 未入池 |
| 4'-demethylrebeccamycin hydrolysis | medium/8 | 4.3.3.5 | 0/0 | 119/0 | ❌ 正确 UID 未入池 |
| tetracenomycin F2 conversion | medium/10 | 4.2.1.154 | 0/0 | 17/0 | ❌ 正确 UID 未入池 |

**关键问题**：两个 medium 候选的正确 UID 都没入池，不能直接做 medium case。

**裁定方案**：

```text
case 1（strong 污水）：10-deoxymethymycin hydroxylation
  → B/C 都召回正确 UID，pool 小（B=1, C=5），最适合做 demo

case 2（medium 污水）：从 strong 候选中降档选 (S)-6-hydroxynicotine oxidation
  → C 召回 2 个正确 UID，pool=15 可控
  → 难度标签按实际 provenance rank 标，不人为降档；若 rank ≤5 则标 strong，
    medium case 改从 P0 非污水候选中选（见 case 3 逻辑）

case 3（weak 技术边界）：从 P0 WEAK_OVER_100 档选 1 个，不宣称污水相关
  → 目的是展示模型在弱档的真实表现，不是展示污水业务
```

**若 strong 候选不足 2 个可用**：medium case 允许从 P0 非污水的 MEDIUM_6_TO_30 档中选 1 个 B 或 C 召回正确 UID 的反应，不虚构污水关联。这比硬凑一个 pool 里没有正确酶的"污水 medium"更诚实。

**case 冻结流程**：学生按上述指导选出 3 个 case 的 reaction SHA256 + 机理证据自审 → 提交老师确认 → 老师确认后冻结，进入 M3-P1。

---

## 四、补充要求

### 4.1 pool ≤100 验证

C 的 pool 中位数 61.5，但 P95 约 1267。学生在冻结 case 前必须验证：所选 3 个 case 的 B pool 和 C pool 均 ≤100。若 C pool >100，该 case 不可用（fail closed），需换候选。

### 4.2 B/C 独立结果保存

即使 M3 v1 采用 B-primary/C-fallback，每个 case 必须同时保存：
- B pool 的完整 UID 列表（若有）
- C pool 的完整 UID 列表（若有）
- 实际使用的是哪一路、为什么
- 正确 UID 在哪一路的 pool 中、rank 多少

这是后续评估混合路线价值的基础数据。

### 4.3 三层分离概念的后续引用

学生提出的 `biological_candidate_universe` / `d4_computable_asset_pool` / `asset_completion_queue` 三层分离，M3 不实现，但 M3 报告中应引用这个概念框架，说明当前 demo 只覆盖 `d4_computable_asset_pool` 的子集。这为 M4/M5 的资产扩充讨论预留接口。

---

## 五、M3-P1 授权启动

**裁定组合**：M3D1-A + M3D2-A + M3D2E-A + M3D3-A + M3D4-A

**授权范围**：M3-P1（Substrate Agent + Reaction Agent 最小可用版）

**前置条件**：3 个 case 的 reaction SHA256 + 机理证据自审经老师确认冻结后，才能写代码。

**交付物**（沿用 M3 启动包）：

```text
enzymecage_crew/
├── agents/
│   ├── substrate_agent.py
│   └── reaction_agent.py
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
├── tools/
│   ├── reaction_search_tool.py
│   └── ec_lookup_tool.py
└── tests/
    └── test_substrate_reaction.py
```

**边界**：
- 不启动 M3-P2（EnzymePoolAgent）——等 M3-P1 验收
- 不启动 M3-P3/P4——等 M3-P2 验收
- 不做 prompt 迭代——等 3 case 基线完成后再做
- 不做资产补齐——M3 全程不做
- 不做 metaTraits 接入——M3 全程不做

**时间预期**：M3-P1 约 2-3 天（含 case 冻结确认）。

---

## 五点五、智能体搭建数据资产需求（学生需提供）

M3 智能体搭建由导师侧负责，使用 LangGraph 编排。以下 6 项数据资产是开发前置依赖，请学生按格式提供：

| # | 依赖项 | 格式 | 用途 | 阻塞阶段 |
|---|---|---|---|---|
| 1 | 3 个已裁定 case 的 reaction SHA256 + SMILES + 机理自审结论 | YAML/JSON | case 配置文件 | 端到端测试 |
| 2 | Rhea 140 本地文件（rhea-directions.tsv / rhea2ec.tsv / rhea2uniprot_sprot.tsv / rhea-reaction-smiles.tsv） | TSV 文件 | B 路线 EC 索引构建 | **工具开发** |
| 3 | 参考反应指纹数据库（4,051 个排除 query 后的 Label=1 反应的 Morgan radius-8 指纹预计算） | pickle/numpy | C 路线相似反应检索 | **工具开发** |
| 4 | D4 冻结资产索引（UID → 资产可用性映射，即 PrecomputedAssetIndex 的导出） | JSON/CSV | pool 过滤：只保留有完整资产的 UID | **工具开发** |
| 5 | EC → UID 映射表（从正式 train/valid/test Label=1 行构建，排除 451 个 P0 query 反应） | CSV/JSON | B 路线 pool 构造 | **工具开发** |
| 6 | EnzymeCAGE 远程服务 HTTP 接口文档（晨羽智云部署的 wrapper API 端点、请求/响应格式、认证方式） | OpenAPI/README | 远程调用客户端开发 | 集成联调 |

**交付方式**：
- 文件类（#2/#3/#4/#5）：打包为 `m3_agent_data_assets.tar.gz`，附 SHA256 校验和，放到 HPC 共享路径或发送给老师
- 文档类（#1/#6）：直接发 Markdown 或 YAML 文件
- #3 参考反应指纹如未预计算，可从 M3-P0B1 的公平基准代码中导出
- #6 如果晨羽智云上的 wrapper 服务尚未部署 HTTP 接口，请先确认是否可以用 SSH 端口转发或直接 Python import 方式调用

**时间要求**：#2/#3/#4/#5 请尽快提供（阻塞工具开发）；#1 等 case 冻结后提供；#6 在集成联调前提供。

---

## 六、给学生的话

1. M3-P0 前置澄清通过，质量很高。查询泄漏的自觉修正和 B/C 互补性数据的完整呈现是本次交付最有价值的部分
2. 四项决策裁定已全部给出，与你的本地建议完全一致。没有悬置项
3. case 选择有具体指导（第三节），两个 medium 候选正确 UID 未入池的问题必须正视，不能硬凑
4. M3-P1 授权启动，但前置条件是 case 冻结经我确认。先交 case 选择 + 机理自审，再写代码
5. **智能体搭建由导师侧负责（LangGraph 编排），但需要你提供 6 项数据资产**——清单见第五节半，#2/#3/#4/#5 请尽快提供，这是开发前置依赖
6. 三条治理纪律继续沿用：边界如实披露 / 表述不越界 / 权限自觉

有问题随时问，没问题就先出 case 选择方案 + 准备数据资产。
