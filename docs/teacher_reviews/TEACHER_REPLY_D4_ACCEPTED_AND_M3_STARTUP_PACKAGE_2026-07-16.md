# D4 通过确认 & M3 端到端联调启动包

日期：2026-07-16  
回复对象：`TEACHER_ENZYMECAGE_D4_V11_WRAPPER_FORMAL_SMOKE_AND_LOCAL_ACCEPTANCE_REPORT_2026-07-16.md`  
状态：D4 v1.1 通过 / M2 里程碑收官 / M3 启动包发布 / M3 前置澄清待学生响应

---

## 一、D4 v1.1 正式验收

**结论**：D4 v1.1 通过。M2 里程碑（wrapper 契约 + 实现 + smoke test）正式收官。

**采纳依据**：
- 9 项 checklist 全 PASS，实测数据全部披露
- 三个 case 重复调用 rank 幂等一致（22/22、27/27、17/17）
- 幂等性 score 最大漂移 4.65e-7，远低于 `abs_tol=1e-5` 契约门控
- warm-50 = 0.33s / warm-100 = 0.56s，远低于 60s 门控
- 完整性审计双 SHA256（manifest + tar）+ 独立验证器 exit 0

**特别肯定的三条治理纪律**（要写进 M3 及之后的规范）：

| 纪律 | 学生这次的做法 | 为什么值得沿用 |
|---|---|---|
| 边界如实披露 | Case 0 rank 从历史 18→wrapper 22，直接列表，归因到已披露的 batch-context sensitivity | 不美化数据，保留复现价值 |
| 表述不越界 | "Top-50 可见"绝不包装成"检索成功"；`ensemble_ci` 绝不说成"统计置信区间" | 保护后续 Agent 层不被误导性数值污染 |
| 收尾权限自觉 | "本地通过 + 提交审阅，不写成老师已经验收" | 治理边界清晰，等外部审计后才升级为验收 |

这三条从 M3 起纳入交付规范，每一份 report 尾部必须自觉遵守。

---

## 二、当前效果水平的定性（面向学生的坦诚判断）

三个 case 的 wrapper rank 22/27/17，正确酶**都没进 Top-10**。这个结果的解读要分层：

**别过度悲观的三点**：
1. Top-50 可见 + 幂等稳定，说明 wrapper 层是干净的，问题不在 wrapper
2. Case 1 (27) 和 Case 2 (17) 跟历史 rank 完全一致，只有 Case 0 有 batch-context 漂移。这是**采样效应**，不是系统性退化
3. P0 全集统计（450 reaction）里 Hit@10=0.73 / MRR@10=0.50，抽这 3 个 case 恰好都是**冻结 test 里排 rank 20 附近的中等难度样本**（provenance rank 18/27/17 都在 Top-30 边缘）。用这三个做 smoke 是**为了压 wrapper 幂等性**，不是为了展示模型峰值能力。所以 rank 落在 17-27 属于**符合预期**，不是模型退化。

**别过度乐观的一点**：
三个 case 都不在 Top-10，意味着**下游"酶→菌"链路里，用户看到的 Top-K 菌很可能不包含"最正确的酶"对应的菌**。这条要在 M3 端到端 report 里给用户明确警示，不能让用户以为"排第一的推荐就是最优解"。

**M3 挑 case 的原则要变**（见第四节）——不能只挑 provenance rank 20 附近的中等样本，得覆盖高/中/低三档难度。

---

## 三、M3 里程碑定义

**M3 目标**：把 EnzymeCAGE v1 wrapper 挂进多智能体系统，跑通"底物 → 反应 → 酶"的完整链路，输出 3 个端到端 case 的 report。

**M3 不做的事**（边界前置明确）：
- 不接入 metaTraits（那是 M3.5-M4 的事）
- 不接入"酶→菌"反查（那是 M4a 的事）
- 不做 Design Explaining Agent 挂接（那是 M5 的事）
- 不做 FastAPI 服务化（M3 仍保持 Python 函数级调用）

**M3 交付物**：

```text
enzymecage_crew/
├── agents/
│   ├── substrate_agent.py
│   ├── reaction_agent.py
│   ├── enzyme_pool_agent.py      # 新增，见架构决策
│   └── enzymecage_agent.py       # 调用 v1 wrapper
├── config/
│   ├── agents.yaml               # backstory / goal
│   └── tasks.yaml                # 输出 schema 约束
├── orchestrator.py               # 意图路由 + stage 编排
├── tools/
│   ├── reaction_search_tool.py   # KEGG/Rhea 相似性检索
│   └── ec_lookup_tool.py         # EC → enzyme UID 索引
└── tests/
    └── test_e2e_3cases.py

m3_e2e_report.md                  # 3 case 端到端结果
```

---

## 四、M3 启动包：4 个待学生确认的架构决策

沿用 D4 前置澄清的模式，**在正式实施 M3 之前**，先把这 4 个架构级决策确认下来。学生本地给建议，我裁定后开工。

### 决策 1：3 个端到端 case 的选择原则

**候选方案**：

- **A. 覆盖难度分层**：从 P0 test set 按 provenance rank 挑 3 个——1 个 Top-5 内（模型强项）、1 个 Top-30 内（中等）、1 个 Top-100 外（模型弱项）
- **B. 覆盖业务场景**：挑 3 个跟污水处理有真实业务相关性的反应（比如芳香族降解、卤代物脱卤、氮循环）
- **C. 兼顾 A+B**：3 个 case 各取一种（污染物场景 × 难度分层交叉）

**我倾向 C**。理由：M3 是给用户看的"端到端 demo"，需要业务代入感（B 侧），也需要暴露模型的能力上限和下限（A 侧）。

**待学生调研**：能不能从 P0 test set 里筛出既有 known enzyme（有 provenance rank）又有污水处理相关性的反应？如果 test set 里没有，是不是要走 D4 的 `MissingReactionAssetError` 路径（缺资产就走反应预测 fallback）？

### 决策 2：`enzyme_pool_uids` 的来源（架构级）

**这条最关键**。D3 契约里说"pool 由上游 Agent 提供"，但没定义**上游具体怎么造这个 pool**。三种做法：

- **A. 全局 pool**：EnzymeCAGE Agent 每次都对冻结数据集里**所有** enzyme UID 排序
  - 优点：不漏酶
  - 缺点：单次调用规模巨大（v1 冻结数据集大概 ~1000+ 酶），Top-K 效果会被稀释
  
- **B. EC number 索引**：Reaction Agent 输出反应时同时输出候选 EC number（1-3 个），EnzymeCAGE Agent 用 EC 反查该 EC class 下所有 enzyme UID 作为 pool
  - 优点：pool 规模合理（每个 EC 下 ~50-200 酶），Top-K 有意义
  - 缺点：依赖反应→EC 的映射准确度
  
- **C. 结构相似性检索**：从冻结数据集里检索与目标反应 SMILES 相似的已知反应，取这些反应的对应 enzyme UID 作为 pool
  - 优点：不依赖 EC 分类
  - 缺点：检索质量本身是个大问题

**我倾向 B**。理由：
- 反应→EC 是标准问题，KEGG/Rhea/BRENDA 都提供，成熟工具链存在
- EC 下的酶数量适中，跟 wrapper 的 50-100 候选设计匹配
- 架构上把"pool 构造"和"pool 内排序"清晰分离——`EnzymePoolAgent` 负责前者，`EnzymeCAGEAgent` 负责后者

**新增 `EnzymePoolAgent` 的必要性**：这是**架构级新增**，不是拍脑袋。理由：
- 让 EnzymeCAGE Agent 保持"排序器"单一职责
- 后续 M4 加"酶→菌"反查时，EnzymePoolAgent 可以复用做"菌→酶反查"，架构对称
- Pool 构造有独立的置信度评估（EC 匹配置信度），不能混进 wrapper 排序分数

**待学生调研**：Rhea / KEGG Reaction 有没有稳定的 reaction_smiles → EC number 的 API？如果 API 覆盖不全，需要备一个 fallback（比如用 RXN Mapper 或 Retro* 之类的工具做反应分类）。

### 决策 3：Substrate Agent 和 Reaction Agent 的接口契约

按用户偏好的增强版业务链（含相似性判断 + fallback），两个 Agent 的输入输出契约初稿：

```python
class SubstrateAgentOutput(BaseModel):
    substrate_smiles: List[str]           # 解析后的底物 SMILES 列表
    substrate_metadata: Dict[str, Any]    # 来源污水描述、CAS、别名等

class ReactionAgentOutput(BaseModel):
    candidate_reactions: List[CandidateReaction]
    fallback_used: bool                   # 是否走了预测分支
    similarity_hit_score: Optional[float] # OK 分支的相似性最高分

class CandidateReaction(BaseModel):
    reaction_smiles: str
    source: Literal["retrieved", "predicted"]
    confidence: float                     # 相似性分数或预测置信度
    ec_hint: Optional[List[str]]          # EC number 提示（供 EnzymePoolAgent 用）
```

**待学生确认**：这两个 Agent 目前是"雏形"状态，M3 之前需要把 backstory / goal / 工具挂载都补齐。**具体做到什么程度**：
- 最小可用（能跑通就行）？
- 还是要做 prompt 迭代 + 3 case 验证？

我倾向**最小可用**——M3 目标是跑通链路，不是把每个 Agent 都调到最优。上游 Agent 的迭代放到 M3 之后。

### 决策 4：M3 验收标准

**候选方案**：

- **A. 链路跑通即通过**：3 个 case 都能从"污水描述"跑到"Top-K 酶推荐"，无异常，即通过
- **B. 链路通 + 合理性人工审核**：跑通之外，还要人工判断推荐的酶是否"业务上合理"（EC class 匹配、机理合理）
- **C. 链路通 + 定量指标**：3 个 case 里至少 2 个的正确酶进入 Top-K（K 待定）

**我倾向 B**。理由：
- A 太松，只测了 pipeline 不测语义
- C 太严，端到端有 Substrate/Reaction/EnzymePool 三层不确定性叠加，用"正确酶 rank"做定量门控会把上游噪声都算进 EnzymeCAGE 头上，不公平
- B 是"pipeline 正确 + 语义可接受"的折中，符合 M3 是"demo 版"而不是"生产版"的定位

**待学生确认**：B 方案里的"业务合理性"由谁审核？是学生自审、我复核，还是拉外部专家？我倾向前两者组合。

---

## 五、时间预期与推进节奏

| 阶段 | 内容 | 预计耗时 |
|---|---|---|
| **M3-P0（本周内）** | 学生响应决策 1-4 的本地建议，出一份 `M3_PREIMPLEMENTATION_CLARIFICATION` | 1-2 天 |
| **M3-P0 裁定** | 我逐条裁定，发布 M3 正式启动包 | 1 天 |
| **M3-P1** | Substrate Agent + Reaction Agent 最小可用版 | 2-3 天 |
| **M3-P2** | EnzymePoolAgent（新增）+ Reaction/EC 索引工具 | 2 天 |
| **M3-P3** | EnzymeCAGEAgent（wrapper 调用层）+ orchestrator | 2 天 |
| **M3-P4** | 3 case 端到端跑 + `m3_e2e_report.md` + 本地审计 | 2-3 天 |
| **M3 收官** | 提交老师审阅 → 进 M3.5 metaTraits 预调研 | - |

**总计约 2 周**。这个节奏不激进，把 M3-P0 前置澄清做扎实是关键——D4 就是靠前置澄清省了大量返工。

---

## 六、给学生的话

1. D4 通过。M2 收官。**这次的三条治理纪律**（边界披露 / 表述不越界 / 收尾权限自觉）从 M3 起写进规范
2. 现在的模型效果"Top-50 可见但 Top-10 不进"是采样效应 + smoke case 选择偏差，不是模型退化，别焦虑
3. 下一步是 M3 前置澄清——**先别写代码**，把决策 1-4 的本地建议出成一份 `M3_PREIMPLEMENTATION_CLARIFICATION_2026-07-XX.md`，我裁定后开工
4. M3 前置澄清预计 1-2 天。这一步做好了，M3 主体实施能省一半时间

有问题随时问，没问题就开始出 M3 前置澄清。
