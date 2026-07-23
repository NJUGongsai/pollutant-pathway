# MT-D5 验收通过 & MT-D1–D8 逐项裁定

日期：2026-07-16  
上游：`metatraits-d5-probe-evidence-2026` 仓库（学生交付）  
状态：MT-D5 验收通过 / MT-D1–D8 裁定完成 / M4a 授权启动

---

## 一、MT-D5 验收结论

**通过。** 三个质量点值得肯定：

1. **证据链完整**：5 份原始 JSON 逐字节保存 + SHA256SUMS + 独立审计 + tar 确定性重建（rebuilt SHA256 与 returned SHA256 一致），R01–R16 闭环
2. **边界披露自觉**："5 样本不能外推全库"、"0 个 429 不等于 unlimited"、"species 查询不证明 strain preservation"、"trait 存在不等于适合污水处理"——全部主动标注，没有越界表述
3. **发现两个合同级问题**（见第二节），这两个发现直接改变了 M4 实现合同，是本次调研最有价值的产出

---

## 二、两个合同问题的裁定

### 2.1 文档 API 不可用 → 数据路径裁定

**事实**：`/api/v1` 16/16 HTTP 404；网站 `/taxon/download` + observation 页面 5/5 + 2/2 可用；三次重复字节一致但有一次 TLS 超时；rate limit UNKNOWN。

**裁定**：采纳学生建议的三层路径，但补充具体要求：

| 层级 | 角色 | 要求 |
|---|---|---|
| **A. 官方 versioned snapshot** | **生产主路径** | 学生在 M4a 期间出一份 `SNAPSHOT_CONTRACT_DRAFT.md`，明确：版本字段、更新频率、许可展示、本地存储路径、hash 校验方式、与在线 fallback 的切换条件 |
| **B. 联系维护方确认 API** | **并行动作** | 学生起草英文询问邮件（问 `/api/v1` 是否下线、是否有替代入口、是否有官方 bulk download），老师审阅后由老师发出 |
| **C. 网站 endpoint experimental fallback** | **仅标注 fallback** | 必须带：TTL cache（建议 24h）、请求间隔 ≥ 2s、完整 provenance 记录、熔断器（连续 3 次失败切换 snapshot）、adapter 接口可替换 |

**明确禁止**：不得把网站 endpoint 写成唯一生产依赖；不得在无 snapshot 的情况下上线 M4b。

### 2.2 三状态 evidence 字段 → schema v1.1 补丁

**事实**：`is_ai`、`majority_label`、`database_record`、`record_url`、`value` 是独立维度；`No robust majority` 是聚合共识状态，可与 AI/非 AI 来源同时存在。

**裁定**：学生判断正确。我原框架 3.4 节的 `evidence: Literal["experimental", "predicted", "no_robust_majority"]` 是错误设计，废止。schema v1.1 补丁如下：

```python
class TraitRecord(BaseModel):
    trait_name: str                          # 如 "oxygen_preference"
    value: Any                               # 来源观测原始值
    is_ai: bool                              # 独立布尔：是否 AI 预测
    majority_label: Optional[str]            # 独立聚合标签：如 "aerobic" / "No robust majority"
    source_database: Optional[str]           # database_record
    source_url: Optional[str]                # record_url
    tax_id: Optional[int]                    # NCBI taxon ID
    # 不再有 evidence 三状态字段
    # 不再有 confidence float（见 MT-D2 裁定）
```

`TraitFilterLayer` 和 `MicrobeSelectionAgent` 消费时必须分别判断 `is_ai` 和 `majority_label`，不得合并。

---

## 三、MT-D1–D8 逐项裁定

### MT-D1：宿主定义 → **采纳 B+**

```text
UniProt reviewed organism/taxon ID：主证据
KEGG Organism：独立补充/交叉证据，保留 0/1/N multiplicity
TrEMBL unreviewed：v1 默认不纳入；后续单独授权并明确降级标志
```

依据：D5 实测 UniProt 10/10 精确，KEGG 7/1/2。KEGG 多命中不得折叠为单一宿主。

### MT-D2：confidence 归一化 → **采纳 C 修订版**

v1 **不输出** `organism_confidence` float。确定性代码透传原始证据维度（reviewed 状态、annotation score、protein existence、KEGG multiplicity），LLM 只能解释已存在的档位，不得创造数值。

**补充**：若后续 schema 必须保留 confidence 字段（如前端展示需要），学生需先出一份 `CONFIDENCE_MAPPING_PROPOSAL.md`，给出确定性映射表 + 映射依据 + 校准计划，老师审阅后才可实现。当前 v1 不需要。

### MT-D3：OrganismAggregator 排序主键 → **延后，v1 先锁 B**

M4a smoke 同时报告 A/B/C 三种排序的差异，但 v1 默认实现锁 **B（supporting-enzyme 数量降序 + UID 升序 tie-break）**，理由：

- B 最简单、无未校准乘积、可复现
- A 依赖 MT-D2 的 confidence（已裁定不输出 float）
- C 的加权公式需要标注验证集，当前没有

M4a 报告里附上 A/B/C 排序差异表，供后续升级参考。

### MT-D4：Trait 硬约束清单 → **采纳 C，v1 最小保守 allowlist**

权限拆分确认：

```text
专家清单：定义允许成为 hard constraint 的 trait、方向和阈值
LLM：只从用户场景提取温度、pH、盐度、好氧/厌氧等值，并对齐专家清单
确定性 TraitFilterLayer：执行最终 hard/soft 规则
```

**v1 最小保守 allowlist**（老师侧暂定，待生物侧专家确认后升级）：

| Trait | v1 角色 | 依据 |
|---|---|---|
| temperature | **soft** | D5 覆盖 5/5，但污水工艺分级标准未验证 |
| pH | **soft** | 同上 |
| salinity | **soft** | 同上 |
| oxygen_preference | **soft** | 同上 |
| biofilm | **不使用** | D5 覆盖 0/5，数据不足，标 unknown |
| safety/pathogenicity | **soft + 人工复核标记** | D5 覆盖 4/5，但安全性判断责任重大，v1 不做自动剔除 |

**关键**：v1 所有 trait 都走 soft + uncertainty_flag，**不执行不可逆剔除**。等生物侧专家确认 allowlist 和阈值后，再升级为 hard。

### MT-D5：接口稳定性调研 → **已闭环**

无需进一步动作。结论边界已确认。

### MT-D6：LLM prompt 硬约束 → **采纳学生增强版**

```text
1. 明确禁止绕过 TraitFilterLayer hard constraints
2. 每个正向推荐至少引用 2 条可定位 evidence
3. 不足 2 条时返回 insufficient_evidence/unknown，不得补写理由
4. 每条关键 trait 引用必须能回到 source、record URL 或 summary identity
5. No robust majority 和来源冲突必须进入 uncertainty_flags
```

**补充**：第 2 条的"2 条 evidence"指**可追溯证据**（有 source_database + source_url），不是两句 LLM 文本。M4c 实现时在 prompt 里明确这一区分。

### MT-D7：独立 crew 还是并入 AdsorptionCrew → **采纳 A**

独立 `MicrobeCrew`，与 `AdsorptionCrew` 并列。上层 orchestrator 只负责意图路由和最终结果组合。与老师原框架一致。

### MT-D8：checkpoint 加载策略 → **延后到 M4a 联调后**

学生给的三段耗时（init 67.85s / first 0.62s / warm-50 0.33s / warm-100 0.56s）与 D4 smoke test 一致，但 QPS/并发/显存竞争确实无数据。

**裁定**：M4a 联调时学生补测以下数据，再裁定 A/B/C：

- 单进程连续 100 次 warm predict 的 P50/P95/P99 延迟
- 2 并发 / 4 并发下的延迟退化
- 显存占用峰值（与 ADRMATS 其他模型共存时）

数据到齐前，M4a 默认用 **A（启动时预加载）**，因为当前是单进程开发环境。

---

## 四、taxonomy 口径确认

采纳学生补充：

```text
生产主键：NCBI taxon ID
GTDB：必须通过带版本的官方 crosswalk，不得与 NCBI ID 静默混用
species 查询：不承诺 strain preservation；observation 中多个 tax_id 时全部保留
```

---

## 五、补充要求

### 5.1 残余非阻塞边界记录

学生审计发现的"30 秒 socket read timeout ≠ 30 秒端到端 wall-clock deadline"（4 个大 taxon 页面请求超过 30s），在生产 client 设计时必须明确：

- 连接超时、socket read 超时、端到端 wall-clock 超时是三个独立参数
- M4b 实现时分别配置，不得混用

### 5.2 biofilm 处理

D5 实测 biofilm 0/5 覆盖。v1 不得把 biofilm 作为任何过滤条件，所有菌的 biofilm 性状统一标 `unknown`。若用户场景明确提到生物膜，LLM 返回 `insufficient_evidence` 并建议人工查阅文献。

### 5.3 Debaryomyces hansenii 稀疏样本

该菌仅 9 条记录，无 safety/pathogenicity 和 wastewater metabolism 匹配。这是**数据稀疏的真实案例**，M4a smoke 应保留此样本作为"稀疏菌处理路径"的测试用例，不得剔除。

---

## 六、M4a 授权启动

**授权范围**：`Enzyme2OrganismTool` + `OrganismAggregator`

**交付物**：

```text
microbe_crew/
├── tools/
│   ├── enzyme2organism_tool.py      # UniProt reviewed 为主，KEGG 独立补充
│   └── organism_aggregator.py       # v1 锁 B 排序，同时报告 A/C 差异
├── tests/
│   └── test_enzyme2organism.py      # 10 个 P0 UID + 稀疏样本
├── M4A_SMOKE_REPORT.md              # 含 A/B/C 排序差异表
└── SNAPSHOT_CONTRACT_DRAFT.md       # 见 2.1 节 A 层要求
```

**边界**：

- 不启动 M4b（MicrobeTraitTool + TraitFilterLayer）——等 snapshot 合同草案 + 专家 allowlist
- 不启动 M4c（MicrobeSelectionAgent）——等 M4b 完成
- 不执行 porTraits、bulk observation 抓取、模型训练
- 所有 trait 走 soft + uncertainty_flag，不执行不可逆剔除

**时间预期**：M4a 约 3-4 天（含 snapshot 合同草案 + 联调补测数据）。

---

## 七、给学生的话

1. MT-D5 通过，质量很高。两个合同问题的发现直接改变了 M4 实现路径，这是本次调研最有价值的产出
2. MT-D1–D8 裁定已全部给出，没有悬置项。MT-D3 和 MT-D8 虽然"延后"，但都给了 v1 默认值和后续触发条件，不阻塞开工
3. M4a 授权启动。snapshot 合同草案和联调补测数据是 M4a 的必交付项，不是可选项
4. 三条治理纪律继续沿用：边界如实披露 / 表述不越界 / 权限自觉
5. 联系 metaTraits 维护方的邮件草稿写好发我，我审阅后发出

有问题随时问，没问题就开工。
