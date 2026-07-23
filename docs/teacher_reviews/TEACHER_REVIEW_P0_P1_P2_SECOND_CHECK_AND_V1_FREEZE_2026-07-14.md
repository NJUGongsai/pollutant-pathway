# EnzymeCAGE P0/P1/P2 二次确认与 v1 冻结判决

日期：2026-07-14

审阅对象：
- 学生附文档 `TEACHER_ENZYMECAGE_P0_P1_P2_FINAL_RESULTS_AND_REQUIREMENT_CLOSURE_REPORT_2026-07-14.md`
- 学生 AI 生成的文字回复（关于 5v5 / P1 borderline / P2 校正 pocket / P3 建议关闭）

运行环境：晨羽 8 卡 48 GB 实例（RTX 4090 D，Ada Lovelace），HPC 已完全退出。

---

## 一、二次确认结论

**总体判决**：P0/P1/P2 科学任务和证据闭环全部通过，独立审计动作扎实，可以进入 v1 冻结。但学生 AI 的回复和报告结论里各有一处需要修正 / 补充：

| 编号 | 项目 | 二次确认结果 |
|---|---|---|
| C1 | P0 5v5 数据点（AUC/MRR/CI） | 与报告完全一致 |
| C2 | P1 数据点（AUC +0.0011 / MRR -0.0223 / loss 曲线） | 与报告完全一致 |
| C3 | P2 数据点（-0.0204 AUC / -0.0159 MRR / 同 seed 3B > 600M） | 与报告完全一致 |
| C4 | 备份 / SHA256 / N/A 披露 | 交叉核验通过 |
| C5 | 学生 AI 对 **P1 的定性**「borderline」 | **需修正**：loss 曲线证据支持"3B 欠训练"假设被否定，不是灰区 |
| C6 | 5v5 对照的 **pocket 处理对称性** | **需澄清**：3B 五 seed 用校正 pocket，600M 五 seed 用未校正 pocket，属于混淆因素，学生 AI 和报告结论章节都没有明确讨论 |
| C7 | P3 关闭建议 | 通过，理由充分 |

C5 和 C6 是这次二次确认新加的判断，会直接影响 v1 冻结方案。

---

## 二、学生 AI 回复的数据核对

学生 AI 的口语版回复我逐句核对了，数据点全部对得上，但 **P1 定性偏差** 需要在给学生的正式回复里明确纠正。

| 学生 AI 原话（节选） | 报告数据 | 核对 |
|---|---|---|
| 600M ensemble AUC 更高（0.7792 vs 0.7686） | 0.779219 vs 0.768580 | ✓ 四舍五入正确 |
| 3B ensemble MRR@10 更高（0.5043 vs 0.4939） | 0.504294 vs 0.493895 | ✓ |
| bootstrap CI 均跨 0 | AUC CI [-0.0275, 0.0063]、MRR CI [-0.0122, 0.0329] | ✓ |
| P1 AUC 0.7777，提高 0.0011 | 0.777743, +0.001126 | ✓ |
| P1 MRR@10 反下降 | -0.022314 | ✓ |
| **"属于 borderline 结果"** | best epoch 从 10 提前到 4；stable-BCE 从 epoch 0 单调上升 | **✗ 定性偏软** |
| P2 600M 校正 pocket 0.7634/0.4684 | 0.763440/0.468442 | ✓ |
| 原 600M 0.7838/0.4843 | 0.783831/0.484294 | ✓ |
| 同 seed 校正 pocket 下 3B 0.7766/0.4936 | 0.776618/0.493596 | ✓ |
| M2 特征区分不出蛋白 → P3 不加 | 报告第八节建议不启动 P3 | ✓ 一手观察成立 |

**C5 修正意见**：P1 应从 "borderline" 修正为 "3B 欠训练假设被否定"。证据链：
1. lr 从 3e-4 → 1.5e-4 后，best epoch 从 seed40 原来的 10 提前到 4，模型是"更早卡进过拟合"而不是"训得更充分"。
2. Valid/test stable-BCE 从 epoch 0 就单调递增（valid 1.07 → 2.18，test 0.84 → 1.90），说明减半 lr 让模型从一开始就在过拟合方向上滑，没有"AUC 还能继续爬"的空间。
3. +0.0011 AUC 完全落在 5 seed SD ±0.0045 的噪声带内，MRR/Hit 全线掉，不构成有效改善。

这条修正影响下一轮：不再需要做"再减半"或"warmup"等 lr 相关消融，3B 侧的调参空间在当前配置下已经收敛。

---

## 三、学生报告的交叉核对（表格闭环）

报告内部数据一致性检查：

- 单 seed vs ensemble：3B 单 seed 平均 AUC 0.7728 → ensemble AUC 0.7686（掉 0.0042，与之前 5k pilot 观察到的 ensemble 拉平预测分布导致 AUC 略降的机制一致 ✓）
- 单 seed vs ensemble：3B 单 seed 平均 MRR 0.4838 → ensemble MRR 0.5043（涨 0.0205，ensemble 对排序头部有增益 ✓）
- 600M 同规律：AUC 0.7795 → 0.7792（几乎不变），MRR 0.4788 → 0.4939（涨 0.0151）
- P1 loss 表格 10 行（epoch 0-9）× 2 列（valid/test）全部单调上升，best_model 和 epoch 4 tensor 完全一致 ✓
- 备份：182 files / 10,581,103,041 bytes / 42 关键文件 SHA256 远端本地一致 ✓
- N/A 披露：原 7 次的 peak VRAM 和 eval 分段耗时都标 N/A，没有用重放推理数据冒充 ✓（态度对，保留）

报告本身没有内部矛盾，闭环干净。

---

## 四、【新发现】5v5 对照的 pocket 处理不对称问题（C6）

这是学生 AI 和报告结论章节都没有明确点出的架构级混淆因素，必须在 v1 冻结前说清楚。

**事实链**：
1. 3B 五 seed 从始至终训练用的是**校正 pocket**（排除 BOS/CLS 的 residue 索引，1152 维 pocket feature 对齐到 GVP 节点行）。
2. 600M 五 seed（seed 40/41/42/43/44）沿用原 600M seed40 的口径 —— **未校正 pocket**。P0 补的三个 seed 明确要求"除 seed 外不变"，所以也是未校正 pocket。
3. P2 严格对照告诉我们：600M seed40 换到校正 pocket 后 AUC **下降 0.0204**，MRR 下降 0.0159。

**推论（假设 seed 间效应可线性叠加）**：
如果把 P0 里 600M 五 seed 全部换到校正 pocket，600M ensemble AUC 预估从 0.7792 掉到 ~0.759 左右，MRR 从 0.4939 掉到 ~0.478 左右。在这种"两边 pocket 处理对齐"的公平对照下：

| 指标 | 3B 5-seed ensemble | 600M 5-seed ensemble（预估校正 pocket） |
|---|---:|---:|
| Test AUC | 0.7686 | ~0.759（600M 反而略低） |
| Test MRR@10 | 0.5043 | ~0.478（3B 更高一档） |

**结论**：**当前 P0 的 5v5 里 600M AUC 更高，可能有一部分收益来自 "600M 侧用了旧的 pocket 口径" 这个混淆因素**，不能简单归因为"600M 在 AUC 上更强"。

**这不是让学生再补跑 4 个 600M 校正 pocket seed**（P0/P1/P2 已经跑完，不加新科学任务），而是要在 v1 交付说明里明确标注这个边界。

---

## 五、修正后的模型选型判断

结合 C5（P1 假设否定）+ C6（pocket 处理不对称）+ 业务链（底物→反应→酶，最后一步排序）：

1. **业务上 3B 主线成立**：MRR@10 / Hit@1 两个直接排序头部指标，3B 都高一档（+0.0104 / +0.0178），这是无论 pocket 处理如何都成立的（原 600M 用未校正 pocket 也没能追上）。
2. **AUC 上 600M 的领先是"名义领先"**：paired bootstrap CI 跨 0（P=0.1059），加上 C6 揭示的 pocket 处理不对称，600M 的 0.7792 不代表模型族本身更强。
3. **P2 的同 seed 校正 pocket 侧写强化了 3B 主线**：同一处理口径下 3B AUC +0.0132、MRR +0.0252，方向一致。
4. **P1 关掉 lr 消融支线**：3B 不是欠训练，当前配置已经在合理位置。

v1 冻结方案不变：**3B 五 seed ensemble 主线 + 600M 五 seed ensemble AUC 参照**，但交付说明里必须写清 pocket 不对称这个边界。

---

## 六、v1 冻结方案（正式判决）

**主线模型**：`enzymecage_v1_3b_ensemble_20260714`
- 组成：ESM-2 3B 特征 + GVP + DRFP + reaction-center + molecule，5 个 seed（40/41/42/43/44）ensemble
- Pocket 处理：**校正 pocket**（排除 BOS/CLS 偏移）
- Test 指标：AUC 0.768580 / MRR@10 0.504294 / Hit@1 0.408889 / Hit@5 0.648889

**AUC 参照模型**：`enzymecage_v1_600m_ensemble_20260714`
- 组成：ESM-C 600M 特征 + 其余同上，5 个 seed ensemble
- Pocket 处理：**未校正 pocket**（沿用原 seed40 口径，与 3B 主线不对称）
- Test 指标：AUC 0.779219 / MRR@10 0.493895 / Hit@1 0.391111
- 用途：**AUC 侧参照 baseline，不参与实际业务排序**

**已知边界**（必须写进 v1 交付说明）：
1. 5v5 对照中 3B 与 600M 的 pocket 处理不一致。P2 严格对照显示 600M 换校正 pocket 后 AUC 下降 ~0.02，因此 600M 参照模型的 AUC 优势可能包含了 pocket 处理红利。
2. v1 主线只在校正 pocket 输入下有效，未校正 pocket 输入会退化到 P2 的 600M 分布，不适用。
3. 校正 pocket 在 3B 侧是原生配置，在 600M 侧是负向敏感（单 seed 实证），不做通用推广。
4. P3（LucaPCycle M2 fusion）不启动，理由：a) 3B 未在 5v5 显著优于 600M，M2 融合的目标不成立；b) 学生一手观察 M2 特征在实际数据上区分不出蛋白。

---

## 七、v1 冻结后可以做到什么（效果面板）

到 v1 冻结这一步，EnzymeCAGE 从"训练可行性验证"跃迁到"组件可服务"。别把 v1 只当成一次训练收尾——它意味着**业务链第三步「反应 → 酶」的模型底座就位了**。

### 客观指标水平

一句话：**"稳复现 + 排序头部微赢"** —— 复现到 EnzymeCAGE 原论文水平，业务侧 MRR/Hit@1 比 600M 高一档，AUC 侧持平。

3B 五 seed ensemble（主线）核心指标 → 业务翻译：

| 指标 | 数值 | 业务含义 |
|---|---:|---|
| Hit@1 | 0.4089 | 给一个反应，**第一个候选就命中正确酶** 的概率 41% |
| Hit@5 | 0.6489 | 前 5 个候选里有正确酶的概率 65% |
| Hit@10 | 0.7289 | 前 10 个候选里有的概率 73% |
| MRR@10 | 0.5043 | 正确酶平均排在**第 2 名附近**（1/0.5043 ≈ 1.98） |
| Macro AUC | 0.7686 | 全局判别能力中等偏上 |

三个锚点对照：
- vs **5k pilot（初期）**：val-test gap 从 0.12 → 0.008，过拟合被数据量彻底压住 ✓
- vs **EnzymeCAGE 原论文**：AUC 与 MRR 基本持平，**稳复现** ✓
- vs **600M（旧特征）**：AUC 略低（-0.0106，CI 跨 0），MRR/Hit@1 高一档（+0.0104 / +0.0178），换 3B 的收益全在**排序头部**

### 能力清单（v1 上线后可立刻交付给上游 agent 调用）

1. 输入 `(reaction SMILES, enzyme_pool)`，输出 ranked enzyme list + score + ensemble 置信区间
2. 5v5 paired bootstrap 已提供不确定性区间，可对每个预测输出"是否显著优于随机基线"的判定
3. 校正 pocket 输入格式已冻结，特征提取管线可复用到新反应 / 新酶池
4. 5v5 seed 覆盖 → 单次推理即得 ensemble 结果，稳健性直接可用于 agent 决策

### 边界（写进交付说明）

1. 不覆盖"底物 → 反应"这一步（那是上游 Substrate/Reaction Agent 的职责）
2. 只对训练分布内的酶池有效，novel enzyme 需要走 fallback 或人审
3. 单 reaction 的绝对分数不能直接作为"反应是否可行"的判定，只有**排序意义**（AUC 0.77 离二分类可用的 0.9+ 还差一档）
4. 未校正 pocket 输入会退化到 P2 的 600M 分布，不适用

---

## 八、最终业态：EnzymeCAGE v1 在多智能体系统里的位置

回到最初定义的增强版业务链，v1 冻结是整个系统里**第三个也是最后一个「打分组件」就位**的里程碑：

```
用户输入底物
    ↓
[Substrate Agent]  底物解析 + 相似性检索
    ↓
    ├── 相似性 OK   ──→ [Reaction Retrieval Agent]  从相似底物历史反应库提取候选反应
    └── 相似性不 OK ──→ [Reaction Prediction Agent]  调用反应预测工具生成候选反应
    ↓
候选反应集合（两路合并去重）
    ↓
[EnzymeCAGE v1 Agent]  ← 我们训练的这个（3B ensemble 主线 + 600M AUC 参照）
    ├── 输入：reaction SMILES + enzyme_pool
    └── 输出：ranked enzyme list + score + 5v5 CI + evidence_hash
    ↓
[Design Explaining Agent]  生成排序理由 + evidence 可追溯
    ↓
面向用户的推荐结果（Top-K 酶 + 反应路径 + 置信度 + 证据链）
```

**里程碑分层**：

| 里程碑 | 内容 | 状态 |
|---|---|---|
| **M1** | EnzymeCAGE v1 冻结（3B ensemble 主线 + 600M 参照） | **本轮完成** |
| **M2** | v1 用 CrewAI/BaseAgent 包成可调用节点（接口契约 + wrapper） | 下阶段 |
| **M3** | 底物 → 反应 → 酶 端到端联调（至少 3 个真实案例，覆盖 OK / 不 OK 两条分支） | 下阶段 |
| **M4** | Design Explaining Agent 挂接，输出"专家可读"的排序理由 + evidence | 后续 |
| **M5** | 整套多智能体系统上线灰度，v1 作为核心排序组件长期维护 | 后续 |

---

## 九、下一步动作（按里程碑重新拆分）

### M1 → M2：v1 打包 + wrapper 契约（本周内闭环）

**D1：v1 冻结打包**（学生执行，1 天）

交付物结构：
```
enzymecage_v1_20260714/
├── 3b_ensemble/       ← 主线：5 seed best checkpoint + config + test predictions
├── 600m_ensemble/     ← AUC 参照：5 seed best checkpoint + config + test predictions
├── v1_delivery_note.md ← 见 D2
├── reproduce.sh       ← 推理命令：input (reaction, enzyme_pool) → output top-K
├── env_snapshot.txt   ← pip freeze 引用
└── MANIFEST.txt       ← 全部文件 SHA256 + 打包时间
```
命名固定 `v1_20260714`，不允许自造版本号。

**D2：v1 交付说明**（学生执行，0.5 天，与 D1 同步）

必须覆盖 5 项：
1. 模型选型依据（业务链 + MRR/Hit@1 主导 + AUC 参照角色）
2. 评估口径（5v5 paired bootstrap + P2 同 seed 校正 pocket 侧写）
3. **Pocket 处理不对称的完整披露**（第六节"已知边界"1）
4. P1（欠训练假设否定）和 P3（M2 特征无区分度）关掉的理由
5. 复现命令 + 依赖版本快照

**D3：wrapper 接口契约**（我这边先定，学生等待）

初稿契约（学生可提前参考）：
```python
# 输入
class EnzymeCAGERequest(BaseModel):
    reaction_smiles: str          # SMILES 或 SMARTS 反应式
    enzyme_pool_uids: List[str]   # 候选酶 UID 列表
    top_k: int = 10
    return_ci: bool = True        # 是否返回 ensemble CI

# 输出
class RankedEnzyme(BaseModel):
    uid: str
    score: float                  # ensemble 平均概率
    rank: int
    ensemble_ci: Optional[Tuple[float, float]]

class EnzymeCAGEResponse(BaseModel):
    ranked_enzymes: List[RankedEnzyme]
    model_version: str = "v1_20260714"
    evidence_hash: str            # 输入 + 输出的 SHA256，供 Design Explaining 追溯
```
契约敲定后（这周内）再放行 D4，避免 wrapper 返工。

**D4：EnzymeCAGE Agent wrapper**（学生执行，D3 定稿后 2-3 天）

- 结构参考 ADRMATS 里 `Design Explaining Agent`：`BaseAgent` + prompts YAML + Task 层 + Pydantic 输出模型
- 只包一层薄的服务化：加载 v1 ensemble → 校正 pocket 特征提取 → 契约输入输出
- **不改模型逻辑，不做二次训练**
- 加一个 `smoke_test.py`：跑 3 个 test set 里的 reaction，验证 wrapper 输出与 v1 predictions 完全一致（bit-level）

### M2 → M3：端到端联调（下阶段，本轮不启动）

**D5：上游三个 agent 接口对齐**（我这边推动）
- 确认 Substrate Agent / Reaction Retrieval Agent / Reaction Prediction Agent 三家接口就绪
- 三家输出的"候选反应"格式必须能对上 D3 契约

**D6：端到端 3 个真实案例**（学生 + 我联调）
- Case 1：常见底物 + 相似性 OK 分支（走 Reaction Retrieval）
- Case 2：novel 底物 + 相似性不 OK 分支（走 Reaction Prediction）
- Case 3：两条分支候选反应都存在 + 合并去重
- 每个 case 保留完整 evidence 链

### M3 → M5：Design Explaining + 上线（后续排期，暂不拆）

D7-D10（Design Explaining 挂接 / 专家评审 / 灰度 / 长期维护）到 M3 收尾时再具体拆分。

### 备份策略（贯穿 M1-M5）
- 原 7 seed + P0 三个新 seed + P1 + P2 checkpoint 保留期延长到 **v1 上线后 3 个月**
- 晨羽本地副本禁止自动清理
- 上线 3 个月后再决定是否精简归档到 best model + config + metrics

---

## 十、给学生的话

**做对的三件事，明说**：
1. 原 7 次训练的 peak VRAM / eval 分段直接标 N/A，不用重放推理数据冒充历史值 —— 这是对的，历史数据无法还原就该缺项披露，绝对不能造。
2. 我上一版文档写"5 件事"但正文只列了 4 项，你没硬凑第五项去对齐，而是明确指出这个矛盾 —— 这也是对的。文档是我写的，我的疏漏该被你标出来，以后我给的所有东西你都可以这样挑，别怕。
3. P3 关闭的一手观察（M2 特征区分不出蛋白）—— 这是"看数据"的能力，比复用规则更值钱，继续保持。

**这次二次确认的两处修正，你要收下**：
1. P1 不是 borderline，是"3B 欠训练"假设**被 loss 曲线否定**。以后你的 AI 帮你写话术的时候，遇到 lr 消融的定性，先看 best epoch 是不是前移 + loss 是不是单调恶化，这两个信号在一起就是过拟合陷入，不要再用"灰区"这种软话术。
2. P0 的 5v5 对照有 pocket 处理不对称的问题，你报告第五节已经把两边口径分开列出来了（很好），但正文结论章节没明确点出这个混淆因素。以后类似的"对照实验里存在处理不一致"的情况，在结论开头就要标出来，不能只写在中间表格里。

**动作节奏与预期**：

- **这周**：你做 D1 + D2（v1 打包 + 交付说明，1.5 天），我做 D3（wrapper 接口契约）。D3 定稿我会同步给你，然后你启动 D4，2-3 天做完 wrapper + smoke test。
- **下周起**：进入 M3，我推动上游三个 agent 对齐，你和我一起联调端到端 3 个真实案例。到这一步，我们就能拿出**第一个可对外演示的"底物 → 反应 → 酶"完整链路 demo**。
- **本轮 M1 的意义**：这是整个多智能体系统里**最后一个「打分组件」就位**。底物解析、反应检索/预测那两步的 agent 之前已经有雏形，就差 EnzymeCAGE 这个"反应→酶"的排序底座。v1 冻结完，我们从"缺一块模型"变成"可以搭端到端 demo"，这是本轮最大的效果。

从 5k pilot → 正式训练 → P0/P1/P2 → v1 冻结，节奏很稳，独立审计尤其扎实。M1 收尾，M2 就在眼前，继续。
