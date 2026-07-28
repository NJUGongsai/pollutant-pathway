# ReactionAgent Build Plan

参照设计文档：`docs/superpowers/specs/2026-07-28-reactionagent-design.md`（v2，commit 744f1f8）。
工作目录：`CC/branch/ReactionAgent/`。原则：**P0 诚实评估先行**，结论驱动后续；不训练任何模型，桶3 仅留插槽。

## 摘要
1. **P0**：把 `verify_substrate_retrieval.py` 的条件排序指标升级为端到端诚实漏斗（去 oracle donor、不偷共反应物、全 X 进分母、canonical 去重、错误谱系、scaffold/family split），产出"覆盖 vs 排序"瓶颈结论。
2. **核心引擎增强**：移植 `extract_rea_trans_fea` 到 `core/`，加多视角检索、多尺度模板(0/1/2)、证据 top-m 聚合、守恒硬门。
3. **Agent**：LangGraph 单 tool-calling agent（自由推理），LLM 归纳转化族 + listwise 择优 + 拒答，输出多步路径 + 证据卡。
4. **验证**：工具单测 + 端到端 smoke + 消融，所有对外指标走 P0 诚实协议。

## 阶段 0 · 工程骨架与数据同步
- 建 `ReactionAgent/` 目录结构（见设计文档 §6），`pyproject.toml`/`.gitignore`（忽略 `data/`）。
- `sync_assets.sh`：从晨羽 HPC 拉 `rxn2fp.pkl`、`reacting_center.pkl`、反应→酶映射、底物 Morgan 索引到 `data/`；失败则文档记录退回 HPC FastAPI 方案。
- 移植 `chenyu_features.py`/`pipeline.py`/`reaction_scorer.py`/`enzyme_lookup` 到 `core/`，跑一次原样 import smoke 确认资产路径与 `ENZYMECAGE_DATA_ROOT` 生效。

## 阶段 1 · P0 诚实评估（先行交付物）
- `benchmark/canonical_identity.py`：RDKit canonicalize + 反应图编辑层去重/分组；同一 substrate→product 归一，多 UniProt 不跨拆分。
- `benchmark/splits.py`：random（sanity）、scaffold split、reaction-family split。
- `benchmark/honest_eval.py`：
  - donor 选择用**固定策略**（检索 top-1 或全 donor 展开），**禁止**依据"候选是否含 Y_true"挑 donor。
  - 输入只含主底物 X，共反应物按未知处理（不注入 held-out 共反应物）。
  - 所有 X 进分母；生成失败/无 donor/无候选各记失败类型（替换 `except: pass`）。
  - 命中判定计入计量数，避免 `issubset` 误判。
  - 产出漏斗：可解析→有 donor→≥1 候选→generation recall@K→end-to-end top-1/3→高置信 selective 准确率；输出 confidence–coverage 曲线。
- 运行并写 `benchmark/RESULTS_P0.md`：给出端到端 top-1/3、逐阶段 recall、**覆盖 vs 排序谁为主瓶颈**的明确结论。此结论作为后续增强优先级的依据。

## 阶段 2 · 核心引擎增强（training-free）
- `core/chenyu_features.py`：加**多视角检索**（全局 Morgan + 局部反应中心 motif 双通道）+ MMR 去近重复，返回多样化 support set。
- `core/pipeline.py`：模板抽取扩到**多尺度 radius∈{0,1,2}**，跨 support/尺度合并候选去重；保留既有 `_atom_query_smarts` 放宽 SMARTS 修复（避免显式 H 不点火）。
- `core/reaction_scorer.py`：DRFP-酶集相似度改 **top-m 聚合**（非单 max）+ 多 donor 共识计数。
- 新增 `check_conservation`（价键/质量/元素/电荷/碎裂硬门）与 `is_terminal`（矿化终点规则）。
- 每个增强点配单测：对已知案例验证点火率提升、多视角/聚合相对旧单 donor/单 max 的变化。

## 阶段 3 · Agent 组装
- `state.py`：`Evidence`/`Step`/`PathwayState`（含潜变量骨架字段 T/S/Δ、support_consensus、applicability、counter_evidence、confidence、funnel）。
- `tools.py`：把 5 个确定性能力封装为 `@tool`（multi_view_retrieve / generate_candidates / collect_evidence / check_conservation / is_terminal）；预留桶3 空接口（site_model_score / learned_ranker_score / enzyme3d_compat / transformer_generate）。
- `prompts.py`：系统提示写清潜变量推理骨架、从 support set 归纳转化族、listwise 证据择优、**拒答**触发条件与话术。
- `agent.py`：LangGraph 单 agent（自由推理 ReAct 循环）+ 逐跳展开 + 停止条件（终点/无候选/max_depth=5/置信<0.3）+ 拒答分支。
- `run.py`：CLI 入口，输入 X 输出路径 + 证据卡（JSON + 可读）。

## 测试计划
- **P0**：拆分上的端到端 top-1/3、逐阶段 recall、confidence–coverage；瓶颈结论落 `RESULTS_P0.md`。
- **工具单测**：多尺度模板点火率、多视角检索多样性、证据聚合正确性、守恒门拦截碎裂候选。
- **端到端 smoke**：`CCCCCCCCO` 复现"借醇脱氢→辛醛"并多步展开（辛醛→辛酸）；构造库内无相近转化的 X 验证正确**拒答**。
- **诚实回归**：agent 端到端指标必须用 P0 协议报告，禁止回到 oracle donor / 偷共反应物。
- **消融**：单 donor vs 多 support；固定 radius=1 vs 多尺度；单 max vs top-m；无拒答 vs 有拒答。

## 假设与风险
- 假设核心 pkl/映射可拷本地；否则退回 HPC FastAPI 服务（文档记录）。
- 若 P0 显示覆盖为主瓶颈且多尺度模板仍不足 → 触发桶3 template-free 生成器（另立 plan，不在本期）。
- 自由推理成本/发散由 max_depth + 流程提示 + 工具幂等 + 每跳候选上限收敛。
- 本期 `confidence` 用规则/证据加权近似；正式校准（conformal 等）属桶3。
