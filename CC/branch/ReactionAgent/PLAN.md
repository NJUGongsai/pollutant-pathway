# ReactionAgent Build Plan（v3 · 位点驱动）

参照设计文档：`CC/branch/ReactionAgent/DESIGN.md`（v3）。
工作目录：`CC/branch/ReactionAgent/`。原则：**P0 诚实评估先行** → 训练**唯一**的 site 模型 → 建 agent；其余 ML 能力（listwise ranker / episodic / template-free）仅留插槽。

## 摘要
1. **P0**：把 `verify_substrate_retrieval.py` 的条件排序升级为端到端诚实漏斗（去 oracle donor、不偷共反应物、全 X 进分母、canonical 去重、错误谱系、scaffold/family split、novelty 分桶），产出"覆盖 vs 排序"结论。
2. **site 模型（本期唯一训练）**：用现成 `reacting_center.pkl` 训练轻量原子/键级位点预测器，不依赖整分子相似度。
3. **核心引擎去 Morgan/DRFP 中心化**：检索主导交给反应中心子图 + 转化指纹 + EC/酶家族（Morgan 降为多样性视角）；生成受 site 约束的多尺度模板；打分改证据融合（DRFP 降为一特征）。
4. **Agent**：LangGraph 单 tool-calling agent（自由推理），LLM 归纳转化族 + listwise 择优 + 拒答，输出多步路径 + 证据卡。
5. **验证**：P0/site/工具单测/端到端 smoke/消融，所有对外指标走 P0 诚实协议。

## 阶段 0 · 工程骨架与数据同步
- 建 `ReactionAgent/` 目录结构（见 DESIGN §7），`pyproject.toml`/`.gitignore`（忽略 `data/`）。
- `sync_assets.sh`：从晨羽 HPC 拉 `rxn2fp.pkl`、`reacting_center.pkl`、反应→酶映射、底物 Morgan 索引到 `data/`；失败则记录退回 HPC FastAPI 方案。
- 移植 `chenyu_features/pipeline/reaction_scorer/enzyme_lookup` 到 `core/`，跑 import smoke 确认资产路径与 `ENZYMECAGE_DATA_ROOT` 生效。

## 阶段 1 · P0 诚实评估（先行交付物）
- `benchmark/canonical_identity.py`：RDKit canonicalize + 反应图编辑层去重/分组；同一 substrate→product 归一，多 UniProt 不跨拆分。
- `benchmark/splits.py`：random（sanity）、scaffold split、reaction-family split。
- `benchmark/honest_eval.py`：
  - donor 选择用**固定策略**（禁止依据"候选是否含 Y_true"挑 donor）。
  - 输入只含主底物 X，不注入 held-out 共反应物。
  - 所有 X 进分母；失败各记类型（替换 `except: pass`）。
  - 命中判定计入计量数，避免 `issubset` 误判。
  - 漏斗：可解析→有 donor→≥1 候选→generation recall@K→end-to-end top-1/3→高置信 selective；输出 confidence–coverage 曲线；novelty 分桶。
- 运行并写 `benchmark/RESULTS_P0.md`：端到端 top-1/3、逐阶段 recall、**覆盖 vs 排序主瓶颈**结论，作为后续优先级依据。**此协议后续复用于 site/agent 评估。**

## 阶段 2 · site-of-transformation 模型（本期唯一训练）
- `site_model/dataset.py`：`reacting_center.pkl`（全局连续原子索引）映射回各反应主底物的原子/键位点标签；用 P0 的 canonical 分组与 scaffold/family split，donor 库与标签只用训练折。
- `site_model/model.py`：先做指纹+MLP 基线，再上轻量 GNN（2–3 层 MPNN/GIN）；类别不平衡加权。
- `site_model/train.py`：训练 + 交叉验证；位点级 precision/recall/AUC 按 novelty 桶报告。
- `site_model/infer.py`：`predict_sites(smiles)` 推理封装，返回原子/键概率。
- 验收：位点预测在 held-out 上显著优于随机/官能团先验；不达标则退回规则位点先验（不阻塞阶段 3）。

## 阶段 3 · 核心引擎去中心化重构（training-free）
- `core/chenyu_features.py`：重构检索为**多路召回**——反应中心子图匹配 + 转化指纹(A→B 编辑指纹) + EC/酶家族；Morgan 降为"全局骨架"多样性视角；MMR 去近重复，返回多样化 support set。
- `core/pipeline.py`：模板抽取扩多尺度 radius∈{0,1,2}，并**受 site 概率约束**只在高概率位点迁移；保留 `_atom_query_smarts` 放宽 SMARTS 修复。
- `core/reaction_scorer.py`：重构为**证据融合**——site 概率 + support consensus（同位点同编辑独立 donor 数）+ 酶家族密度(top-m 聚合) + 适用域惩罚；DRFP 退为一特征。
- 新增 `check_conservation`（价键/质量/元素/电荷/碎裂硬门）与 `is_terminal`（矿化终点规则）。
- 每个重构点配单测：site 约束模板点火率、多路检索多样性、证据融合相对旧单 donor/单 max 的变化。

## 阶段 4 · Agent 组装
- `state.py`：`Evidence`（含 site/site_prob/support_consensus/enzyme_family_density/drfp_score/applicability/counter_evidence）/`Step`/`PathwayState`。
- `tools.py`：6 个确定性能力封装为 `@tool`（predict_sites / multi_view_retrieve / generate_candidates / collect_evidence / check_conservation / is_terminal）；预留桶3 空接口（learned_ranker_score / enzyme3d_compat / transformer_generate）。
- `prompts.py`：系统提示写清潜变量骨架、从 support set 归纳转化族、listwise 证据择优、**拒答**触发与话术。
- `agent.py`：LangGraph 单 agent（自由推理）+ 逐跳展开 + 停止条件（终点/无候选/max_depth=5/置信<0.3）+ 拒答分支。
- `run.py`：CLI，输入 X 输出路径 + 证据卡（JSON + 可读）。

## 测试计划
- **P0**：拆分上端到端 top-1/3、逐阶段 recall、confidence–coverage；瓶颈结论落 `RESULTS_P0.md`。
- **site 模型**：位点级 precision/recall/AUC 按 novelty 桶；train/test 泄漏隔离。
- **工具单测**：site 约束模板点火率、多路检索多样性、证据融合正确性、守恒门拦截碎裂候选。
- **端到端 smoke**：`CCCCCCCCO` 复现"借醇脱氢→辛醛"并多步展开（辛醛→辛酸）；构造库内无相近转化的 X 验证正确**拒答**。
- **诚实回归**：agent 端到端指标必须用 P0 协议报告，禁止回到 oracle donor / 偷共反应物。
- **消融**：单 donor vs 多 support；固定 radius=1 vs 多尺度；有无 site 约束；单 max vs top-m；Morgan 主导 vs 反应中心/转化主导；无拒答 vs 有拒答。

## 假设与风险
- 假设核心 pkl/映射可拷本地；否则退回 HPC FastAPI（文档记录）。
- site 标签仅 4541 条偏小 → 基线先行 + 交叉验证 + 不平衡加权；不达标退回规则位点先验，不阻塞主干。
- 若 P0 显示覆盖为主瓶颈且 site 约束多尺度模板仍不足 → 触发桶3 template-free 生成器（另立 plan）。
- 自由推理成本/发散由 max_depth + 流程提示 + 工具幂等 + 每跳候选上限收敛。
- 本期 `confidence` 用规则/证据加权近似；正式校准属桶3。
