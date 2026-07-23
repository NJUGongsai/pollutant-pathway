# D4 前置审计回复 & D3 契约 v1.1 补丁

日期：2026-07-16  
回复对象：`ENZYMECAGE_D4_PREIMPLEMENTATION_TEACHER_CLARIFICATION_REQUEST_2026-07-16.md`  
状态：D4A2 前置审计通过 / Q1-Q8 全部裁定 / D3 契约打 v1.1 补丁 / D4B 授权启动

---

## 一、整体判断

前置审计做得到位，两件事表扬：

1. **在正式实施前把 batch-context sensitivity 找出来**——`to_dense_batch` padding 长度动态 + attention mask 用 `-1e9` 而非 `-inf` + padding query 输出未 mask + `.mean(1)` 未 mask，这四条叠加导致同一候选在不同 batch 上下文里分数漂移 max abs diff = 0.62。这不是 wrapper 的问题，是 v1 模型自身固有属性，属于**已知边界**，正确的处理是披露不是修复
2. **对"复现"的边界定义克制**——25/25 对照 PASS 只写成"抽查 5 候选在原始 batch context 下复现"，没有夸成"1024 行全部复现"；`ensemble_ci` 只描述为"5 seed 分数分位范围"，不冒充"统计置信区间"。这种表述纪律要保持

Q1-Q8 逐条裁定如下，**全部采纳本地建议**，个别加约束。

---

## 二、Q1-Q8 逐条裁定

### Q1 → **A**（以 wrapper 请求本身作为推理上下文）

**裁定**：正式 D4 推理上下文 = 调用方实际提交的候选集本身。历史 `reference_rank` 18/27/17 只作 provenance 对照，不作跨 batch-context 的强制相等门控。

**理由**：
- 选 B 会强制 wrapper 内部注入"请求外候选"来重建历史 256 行上下文，违反 D3"只对提交的 pool 排序"的核心契约
- 选 C 是重训 v1，不在冻结范畴
- v1 的 batch-context sensitivity 是**模型层**的已知属性，wrapper 无义务掩盖

**修订 smoke test 第 1 项 checklist**（原"正确酶 rank 与冻结 test 完全一致"作废）：

> **新第 1 项**：正确酶被推荐到 Top-K（K=50） 且 rank 值在同输入重复调用下**幂等**（同输入 → 同 rank）。历史冻结 rank 18/27/17 作为 provenance 记录，不作强制相等断言。

**Smoke test 调用参数确认**（按学生方案）：

```text
base request：50 个有效候选，top_k=50，return_ci=True
无效 UID 子测试：50 有效 + 3 无效 = 53 UIDs，top_k=50，输出 50 条有效
```

**报告必须披露**：
- 25 个 seed/candidate 对照的 max abs diff = 0.62（batch-context sensitivity 证据）
- 三个 case 的 wrapper 上下文下正确酶实测 rank vs 历史 18/27/17（差值可能非零，如实报）

### Q2 → **限定预计算资产域 + 分类处理**

**裁定**：D4 v1 正式运行域限定为"冻结资产索引中可解析的 reaction + UID"。

**分类处理规则**：

| 情境 | 处理 |
|---|---|
| `reaction_smiles` 合法但无 DRFP/分子构象资产 | 抛 `MissingReactionAssetError`（自定义异常），异常消息列出缺失资产名 |
| UID 存在但缺 GVP / pocket ESM / sequence ESM 任一 | **静默跳过**，跟"不存在的 UID"同样处理，不进入 rank |
| UID 全部无资产 | 返回空 `ranked_enzymes` 列表，`evidence_hash` 照常计算（基于原始输入） |

**架构级补充**（这条是我的加码，请学生实现）：

新增 `PrecomputedAssetIndex` 类（无状态查询），放在 `enzymecage_wrapper/asset_index.py`：

```python
class PrecomputedAssetIndex:
    def has_reaction(self, reaction_smiles: str) -> bool: ...
    def has_enzyme(self, uid: str) -> bool: ...
    def missing_assets(self, reaction_smiles: str) -> List[str]: ...
```

`predict()` 内部先用它做资产可用性预检，把"缺资产"这个失败路径从**推理层**上移到**契约层**，避免深层堆栈里抛陌生异常。

### Q3 → **A**（wrapper 代码层轻量，运行时继承 v1 科学依赖）

**裁定**：原 D3 契约里"只依赖 PyTorch + Pydantic + 标准库"的措辞需要修订，我表述不严谨，学生指出得对。

**修订**：

> **wrapper 代码层**（`enzymecage_wrapper/*.py` 中新写的代码）只 import PyTorch / Pydantic / 标准库，不引入 CrewAI / LangChain / FastAPI 等 Agent/Web 框架。
>
> **wrapper 运行时环境**继承 v1 冻结包的科学依赖：PyG、`torch-cluster`、`torch-scatter`、RDKit、pandas、NumPy、scikit-learn、ASE、PyYAML、tqdm。这些是 v1 模型推理路径的既有依赖，不是新增。

**交付要求补充**：`enzymecage_wrapper/` 目录里加一个 `requirements.txt`，分两栏：

```text
# wrapper layer (new)
pydantic>=2.0

# scientific runtime (inherited from v1 frozen package)
torch>=2.7
torch-geometric
torch-cluster
torch-scatter
rdkit
pandas
numpy
scikit-learn
ase
pyyaml
tqdm
```

版本号按 v1 冻结时的实测环境写死（Python 3.12.3 / PyTorch 2.7.1+cu126）。

### Q4 → **A**（60s 门控只针对 warm predict()）

**裁定**：60s 门控只覆盖模型和资产完成一次性初始化后的 `predict()` 调用。

**理由**：wrapper 后续在 EnzymeCAGE Agent 里是常驻服务，冷启动只发生一次，用 60s 卡冷启动没意义。

**报告要求**（必须分三行披露，不合并）：

```text
initialization_time_sec:       <一次性加载 5 checkpoint + 特征资产索引的耗时>
first_predict_time_sec:        <第一次 predict() 调用耗时>
warm_predict_time_sec:         <连续调用第 2 次以后的耗时>
```

**门控判定**：`warm_predict_time_sec ≤ 60s`（50 候选）+ `warm_predict_time_sec_100_candidates ≤ 60s`（100 候选，如果 smoke test 覆盖到）。

冷启动耗时**不做门控**，但**必须披露**——后续 M3 联调时决定是否需要预加载策略要用到这个数。

### Q5 → **B**（rank/UID/hash 完全一致，score/CI 允许容差）

**裁定**：

| 字段 | 幂等标准 |
|---|---|
| `evidence_hash` | 逐字节完全一致 |
| `ranked_enzymes[*].uid` 顺序 | 完全一致 |
| `ranked_enzymes[*].rank` | 完全一致 |
| `ranked_enzymes[*].score` | 允许 `abs_tol=1e-5` 容差 |
| `ranked_enzymes[*].ensemble_ci` | 允许 `abs_tol=1e-5` 容差（每个端点分别比较） |

**理由**：
- 学生实测重复前向 max diff = 1.043e-6，1e-5 有 10× buffer
- GPU CUDA nondeterminism 是 PyTorch 已知行为，除非全局 `torch.use_deterministic_algorithms(True)`，否则压不到 0（且开启后显著降速）
- rank / UID / hash 三个"公开语义字段"必须严格一致，这是契约核心；score/CI 是浮点，允许微小漂移

**不选 A** 的原因：逐字节一致要求会强制 wrapper 内做强制舍入或 deterministic mode，前者引入数值噪声，后者影响性能，都是过度约束。

**不选 C** 的原因：固定小数位是 presentation 层的事，contract 层不该管。

### Q6 → **完全采纳**

**裁定**：

```text
每 seed score       : post-sigmoid probability (与冻结 test `pred` 一致)
ensemble score      : mean of 5 seed scores, dtype=float64
ensemble_ci         : torch.quantile(seeds, [0.025, 0.975], interpolation="linear"), dtype=float64
```

**表述纪律**（这条要写进 d4_smoke_test_report.md）：

> `ensemble_ci` 描述为"5 个 seed 输出分数在 2.5% 和 97.5% 分位处的经验分数范围"，**不**描述为"95% 置信区间"或"统计显著性区间"。5 seed 是采样噪声的极小样本，无法支撑总体参数意义上的 CI 断言。

学生原文已经做到了这条，正式记入契约。

### Q7 → **去重 + 同分 UID 升序**

**裁定**：

| 情境 | 处理 |
|---|---|
| 输入 UID 含重复 | 推理前**去重**（保留首次出现顺序做 log），只对唯一 UID 前向 |
| 完全相同的 ensemble score | 按 UID 升序作为第二排序键 |
| `evidence_hash` 计算 | **严格按原始输入 UID 列表**排序后 hash，**保留重复项**（不先去重） |

**关键分离**：`evidence_hash` 记录"用户原始提交意图"，去重是**内部推理优化**。两者不能耦合。

**举例**：
- 输入 UIDs = `["E1", "E2", "E1"]`
- `evidence_hash` 输入串 = `smi + "\n" + "E1\nE1\nE2" + "\n" + model_version`（sorted 后含重复）
- 实际推理只跑 `E1` 和 `E2`（去重后）
- 输出 `ranked_enzymes` 只有 2 条

### Q8 → **完全采纳**

**裁定**：

```text
待哈希字符串 → UTF-8 encode → hashlib.sha256() → hexdigest() (小写, 64 chars)
换行符严格 "\n" (0x0A)，不用 "\r\n"，不用 os.linesep
```

补一条测试向量到 `test_smoke.py`：

```python
def test_evidence_hash_canonical():
    smi = "CC(=O)O"
    uids = ["E002", "E001"]  # 未排序
    version = "v1_20260714"
    expected = "<学生跑一次得到值，写进测试锁定>"
    assert compute_evidence_hash(smi, uids, version) == expected
```

这个测试锁定 hash 算法本身，之后任何 encoding/换行/排序改动都会立刻暴露。

---

## 三、D3 契约 v1.1 补丁总结

相对 2026-07-15 发布的 v1.0 契约，本次修订：

| # | 项 | v1.0 | v1.1 |
|---|---|---|---|
| 1 | Smoke test 第 1 项 | "正确酶 rank 与冻结 test 完全一致" | "正确酶被推荐到 Top-K 且同输入幂等"（rank 数值不做强制相等） |
| 2 | 依赖边界表述 | "只依赖 PyTorch + Pydantic + 标准库" | 分层：wrapper 代码层轻量 / 运行时环境继承 v1 科学依赖 |
| 3 | 60s 门控 | 未明确冷启动 | 只对 warm predict()，冷启动分别披露不做门控 |
| 4 | 幂等标准 | "同输入 → 同输出" | rank/UID/hash 严格一致，score/CI 容差 abs_tol=1e-5 |
| 5 | 运行域 | 未定义 | 限定预计算资产索引域，缺 reaction 抛异常、缺 UID 静默跳过 |
| 6 | 重复 UID | 未定义 | 推理前去重，evidence_hash 保留原始 |
| 7 | 编码 | 未定义 | UTF-8 + `\n` + hexdigest 小写 |
| 8 | 新增交付物 | `wrapper/` + `report.md` | +`requirements.txt` +`asset_index.py`（架构级补充） |

v1.1 是 v1.0 的**严格超集**，没有破坏性变更，只补充定义。

---

## 四、修订后的 D4 Smoke Test Checklist（正式版）

| # | 检验项 | 通过条件 |
|---|---|---|
| 1 | 正确酶 Top-K 可见性 + 幂等 | 3 case 的正确酶都出现在 top_k=50 结果中；同输入重复调用 rank 完全一致 |
| 2 | evidence_hash 可复现 | 同输入跑两次 hash 完全一致；测试向量锁定通过 |
| 3 | ensemble_ci 合理性 | CI 宽度 > 0 且 < 1；报告中明确表述为"分位范围"不冒充"统计 CI" |
| 4 | warm predict 耗时 | 50 候选 ≤ 60s；同时分别披露 init / first / warm 三段耗时 |
| 5 | 输出长度 | `len(ranked_enzymes) == min(top_k, 有效候选数)` |
| 6 | 无效 UID 容错 | 50 有效 + 3 无效 = 53 输入，输出 50 条有效，不报错，不进入 rank |
| 7 | 重复 UID 去重 | 输入含重复 UID，推理层去重，evidence_hash 保留原始 |
| 8 | 缺资产异常路径 | 构造一个 reaction 缺 DRFP 资产的 case，验证抛 `MissingReactionAssetError` |
| 9 | Batch-context sensitivity 披露 | report 中明确记录 25 个对照 max abs diff = 0.62 作为已知边界 |

---

## 五、D4B 授权启动

前置审计通过，D3 契约 v1.1 定稿，D4B 授权启动。

**实施边界**：
- 严格实现 v1.1 契约 + Q1-Q8 全部裁定
- 不加未经批准的字段 / 行为 / 依赖
- 遇到 v1.1 未定义的边缘 case，停下来问，不自作主张
- 目标交付物（三项）：

```text
enzymecage_wrapper/
├── __init__.py
├── schema.py
├── predictor.py
├── asset_index.py           # 新增（Q2 架构级补充）
├── utils.py
├── requirements.txt         # 新增（Q3 依赖分层）
└── tests/
    └── test_smoke.py
d4_smoke_test_report.md      # 9 项 checklist + 三段耗时 + batch-context 披露
```

**时间预期**：wrapper 实现 2 天 + smoke test/report 1 天（加了 asset_index 和多披露项，比原来多 0.5 天）。

**结束语**：这次前置审计的方式值得沿用——在 D5/D6/D7 之前都可以先做一轮"运行时前置审计 + 待确认清单"，把架构层不确定性提前暴露。这比事后返工便宜得多。
