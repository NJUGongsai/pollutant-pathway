> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# CLAUDE_PLAN — LLM 潜变量分阶段类比推理引擎 · 实施计划（demov2）

> 日期：2026-07-29
> 配套设计：`CLAUDE_DESIGN_LLM_LATENT_STAGE_REASONING_2026-07-29.md`
> 工作根目录：`CC/branch/ReactionAgent/demov2/`
> 运行约定：脚本从 `benchmark/` 跑时 `PYTHONPATH=../../core`；数据根 `ENZYMECAGE_DATA_ROOT` 默认 `/Volumes/CC/Enzyme_Agent/depending/data`。

---

## 0. 计划总览

按设计的三里程碑推进，**每个里程碑独立可验收、可回退**。核心原则：先用最小闭环证明"LLM+MCP 类比推理"可行（M0），再拆完整潜变量链接上诚实漏斗（M1），最后做校准与对拍（M2）。

冻结项（本轮不动）：DRFP 打分器、`splits.py` 防泄漏、`honest_eval` 四类防作弊口径。

---

## 1. 目录结构（新建于 demov2/）

```
demov2/
├── plan/                         # 本设计与计划（已建）
├── tools/                        # MCP 工具封装层（包装 core/ 现有资产）
│   ├── retrieve.py               # retrieve_support_reactions
│   ├── site.py                   # check_reaction_center
│   ├── validate.py               # validate_smiles (RDKit)
│   ├── score.py                  # score_candidate (DRFP-酶集)
│   └── edit_sig.py               # edit_signature (变换签名)
├── reasoner/                     # LLM 推理核心
│   ├── prompts/                  # 各阶段 prompt 模板
│   ├── stages.py                 # 六跳阶段函数 + 拒答闸
│   └── engine.py                 # 编排：推理链 + 工具调用循环
├── schemas.py                    # 输出契约（product/T/S/Δ/evidence/confidence）
├── run_predict.py                # 单 X 预测入口
└── eval/
    └── run_honest_eval.py        # 接入 honest_eval 三划分 + selective/abstention
```

---

## 2. 里程碑 M0 · MVP 单环（LLM+MCP 闭环）

**目标**：证明 LLM 握着 MCP 工具能对 X 端到端类比推理出 Y、并会拒答。链路 ①→④→⑥（暂不拆 ②③⑤）。

### 任务
- [ ] **M0-T1 工具封装（最小三件）**
  - `tools/retrieve.py`：包装 `chenyu_features.retrieve_by_substrate`（Morgan r=2,2048bit），入参 `X, k`，出参 `[{donor_rxn, A, B, similarity}]`。
  - `tools/validate.py`：包装 RDKit，入参 `Y_smiles`，出参 `{valid: bool, reason}`。
  - `tools/score.py`：包装 `reaction_scorer.score_candidates`，入参 `X>>Y`，出参 `{score}`。
  - 统一为无状态函数式接口 + JSON schema（供 function-calling）。
- [ ] **M0-T2 输出契约 `schemas.py`**：定义成功输出（product_smiles / support_evidence / confidence / reasoning_chain）与拒答输出（abstain / abstain_stage / reason）。
- [ ] **M0-T3 推理引擎 `reasoner/engine.py`**：单 ReAct 环——检索证据 → LLM 读 A→B 类比写候选 Y → validate 校验（非法有限次重写）→ score 打分 → LLM 给置信/拒答。LLM 后端沿用现有 `call_dashscope`（kimi）。
  - 工具接口先走**进程内 function-calling**（不急着起 MCP server 进程），跑通后 M1/M2 再抽 MCP server。
- [ ] **M0-T4 入口 `run_predict.py`**：输入单个 X SMILES，打印产物 + 推理链 + 是否拒答。
- [ ] **M0-T5 冒烟**：取 3–5 个已知 case（含 1 个应拒答的 novel）手工验证闭环。

### 验收
- 能对样例 X 端到端产出 Y + 可回溯 support_evidence + 人类可读 reasoning_chain。
- 对无类比依据的 case 能触发拒答闸①/④，输出 abstain。
- LLM 亲自写 SMILES（非模板算法生成），工具仅做检索/校验/打分。

---

## 3. 里程碑 M1 · 完整潜变量链 + 诚实漏斗

**目标**：拆出 ②判T ③定S ⑤评E 三跳，接 honest_eval 三划分，产出逐阶段漏斗归因。

### 任务
- [ ] **M1-T1 补齐工具**
  - `tools/site.py`：包装 `reaction_center_from_chenyu` / MCS `extract_reaction_center`，出 X 候选位点。
  - `tools/edit_sig.py`：包装 `edit_script.extract_edit + key()`，做 support set 转化一致性校验。
- [ ] **M1-T2 阶段化 `reasoner/stages.py`**：把引擎拆成六跳，每跳独立函数 + 对应拒答闸（①检索②判T③定S④写Δ⑤评E⑥置信）。每跳产出结构化中间态（T/S/Δ 假设）。
- [ ] **M1-T3 检索升级（复用解法C）**：`retrieve_support_reactions` 增加位点驱动模式 + 多样性采样（MMR / 分层：高全局相似 + 高局部位点相似 + 远程同族类比），避免 top-k 全是近重复。
- [ ] **M1-T4 接入 honest_eval `eval/run_honest_eval.py`**：作为 honest_eval 的新 generator/mode，复用同一诚实漏斗；报端到端 top-1/top-3（分母=全部测试 X，去 oracle donor、不偷共反应物）。
- [ ] **M1-T5 漏斗归因**：输出六道闸的逐阶段分母与损失归因，对齐 `unparsable/no_donor/no_candidate/not_generated/hit`。
- [ ] **M1-T6 三划分跑全量**：random / scaffold / reaction_family 各跑一遍，产出漏斗报告。

### 验收
- 三划分端到端 top-1/top-3 数字 + 逐阶段漏斗报告落盘（`reports/`）。
- 错误可定位到具体阶段（T错/S错/Δ错/Y非法/未命中）。
- 防作弊口径与 honest_eval 一致（可复现）。

---

## 4. 里程碑 M2 · 置信校准与对拍

**目标**：置信度可用、拒答有价值，并量化相对旧管线的收益。

### 任务
- [ ] **M2-T1 置信校准**：产出 selective accuracy vs coverage 曲线；标定置信阈值。
- [ ] **M2-T2 指标补齐**：`selective_accuracy`、`abstention_rate` 纳入评估报告。
- [ ] **M2-T3 与旧管线对拍**：同数据同划分，跑旧确定性管线（Morgan+模板+DRFP，honest_eval smarts/union generator）作基线，对比端到端 top-k 与高置信段准确率。
- [ ] **M2-T4 抽 MCP server（可选）**：若确认需要跨进程 MCP，把 `tools/` 抽成独立 MCP server 进程；否则保留进程内接口。
- [ ] **M2-T5 结论文档**：写对拍结论与建议（LLM 推理核心相对机械迁移强多少、拒答换来多少可靠性）。

### 验收
- 校准曲线 + selective/abstention 指标落盘。
- 对拍结论：random 划分端到端 top-3 ≥ 旧管线，高置信段 selective accuracy 显著高于旧管线整体准确率。
- 结论文档写入 `demov2/plan/`（沿用 CLAUDE_ 前缀）。

---

## 5. 复用清单（现成积木，勿重写）

| 能力 | 现有位置 | 用途 |
|---|---|---|
| Morgan 底物检索 | `core/chenyu_features.retrieve_by_substrate` | retrieve 工具 |
| 位点驱动检索 | 解法C（`benchmark/honest_eval` 检索层新模式） | retrieve 升级 |
| 真值/MCS 反应中心 | `core/chenyu_features.reaction_center_from_chenyu`、`core/pipeline.extract_reaction_center` | site 工具 |
| DRFP-酶集打分 | `core/reaction_scorer.score_candidates` | score 工具 |
| 变换签名 | `benchmark/edit_script.extract_edit + key()` | edit_sig 工具 |
| 辅酶剥离/反应中心锚定 | `benchmark/canonical_identity.transformed_pair` | 数据清洗 |
| 三划分防泄漏 | `benchmark/splits.make_split` | 评估划分 |
| 诚实漏斗主评估 | `benchmark/honest_eval.py` | eval 接入 |
| LLM 调用入口 | `src/utils/llm.call_dashscope`（kimi 网关） | 推理核心后端 |

---

## 6. 风险与对策

| 风险 | 对策 |
|---|---|
| LLM 写出化学非法/幻觉 SMILES | `validate_smiles` 强制校验 + 有限次重写；仍非法则拒答 |
| LLM 靠语言直觉而非证据推理 | reasoning_chain 强制回溯到具体 A→B；对拍机械迁移对照组 |
| token 成本 / 延迟 | M0 单环控制工具调用轮数上限；M1 阶段化后可缓存中间态 |
| 检索带不回对的变法（病A） | M1-T3 位点驱动 + 多样性采样；带不回则走拒答（不硬造） |
| 评估口径漂移导致数不可信 | 严格复用 honest_eval 四类防作弊 + 三划分，去 oracle |

---

## 7. 开放项（M0 不阻塞，需用户择机确认）

1. 环境上下文 C 是否建模（M0 先忽略）。
2. 多步路径 X→Y→Z 是否本轮必须（建议 M1 后，单步引擎递归）。
3. LLM 后端是否需可切换（默认沿用 kimi 网关）。
4. 是否需真正跨进程 MCP server（建议 M0 先进程内 function-calling，M2 再抽）。

---

## 8. 交接状态

- ✅ 一致性审阅完成（现状 vs 目标偏差已定位）。
- ✅ brainstorming 完成，方案 B（潜变量分阶段）获批准。
- ✅ 设计文档 + 实施计划落盘 `demov2/plan/`（CLAUDE_ 前缀）。
- ⬜ 下一步：按 M0 任务清单开始实现（需用户确认开工，或先答第 7 节开放项）。
