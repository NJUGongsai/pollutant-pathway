# EnzymeCAGE D4 正式实现前合同澄清申请

日期：2026-07-16  
依据文件：

```text
00_Authority_Teacher_Plan/
TEACHER_REPLY_D1D2_CLOSURE_AND_D3_CONTRACT_2026-07-15.md
```

当前状态：D4A2 运行时前置审计已在本地完整通过；尚未启动正式 D4B
wrapper 实现。模型代码、5 个 checkpoint、特征资产、冻结结果和老师发布的
D3 合同均未修改。

本文件只询问会直接改变 D4 实现或验收结论的未定义事项。老师已经明确规定的
schema、字段、hash 公式、5-seed ensemble、无效 UID 跳过、边界和正式交付物
不会擅自更改。

---

## 一、已经确认且不会再改动的 D3 要求

1. 输入和输出严格使用老师给出的 Pydantic schema，不增加字段。
2. `model_version` 固定为 `v1_20260714`。
3. 使用冻结包内 ESM-2 3B seeds 40--44 的 5 个 checkpoint；每个 seed
   独立前向，`score` 为 5-seed 均值。
4. `ensemble_ci` 使用 5 个 seed 分数的 2.5% 和 97.5% 分位；
   `return_ci=False` 时返回 `None`。
5. 按 `score` 降序，`rank` 从 1 开始连续编号。
6. 不存在的 UID 静默跳过，不抛异常，也不进入 rank。
7. 输出长度严格为 `min(top_k, 有效候选数)`。
8. `evidence_hash` 的字符串内容严格使用老师给出的公式：

```text
SHA256(
  reaction_smiles + "\n" +
  "\n".join(sorted(enzyme_pool_uids)) + "\n" +
  model_version
)
```

9. 所有模型使用 `.eval()` 和 `torch.no_grad()`。
10. 不加入 HTTP、FastAPI、CrewAI、LangChain、酶到菌映射或化学合法性校验。
11. checkpoint 根目录通过冻结包配置或环境变量指定，不硬编码机器绝对路径。
12. 老师正式要求的交付物保持为且仅为：

```text
enzymecage_wrapper/
d4_smoke_test_report.md
```

---

## 二、D4A2 已验证事实及证据边界

### 2.1 冻结 checkpoint 和原批次复现

- seeds 40--44 的 5 个 3B checkpoint SHA256 均与已接受 v1 冻结包一致。
- D4A2 为 case 0 的正确酶和前 4 个负例定位了原始 test 行。这 5 行分别来自
  历史 batch 35、241、242、243。
- 为保持历史推理上下文，D4A2 实际构建并前向了上述 4 个完整的 256 行批次，
  共 1,024 行。
- 数值一致性门控只比较这 5 个指定候选在 5 个 seed 下的 25 个
  live/frozen 对照，不是对 1,024 行全部做冻结分数逐行比较。
- 25 个对照的最大绝对差为：

```text
4.198866272453472e-07 <= 1e-6，PASS
```

因此可以确认：checkpoint 和当前运行时在保持原始 256 行 batch context 时能够
复现所抽查的冻结分数。这里不扩大解释为“1,024 行全部逐值复现”。

### 2.2 已证实批次上下文会改变分数，但尚未证实正式 3 x 50 rank 改变

将上述同 5 个候选改为一个独立 5 行请求批次后，与各自原始 256 行上下文相比，
25 个 seed/candidate 分数中的最大绝对差为：

```text
0.6218325197696686
```

源码检查与该现象一致：`to_dense_batch` 的 padding 长度取决于当前批次；attention
在 softmax 前以有限的 `-1e9` 处理 mask；padding query 的输出没有在 softmax 后
清零；interaction 对 dense 长度执行未加 mask 的 `.mean(1)`。D4A2 没有修改该
行为。

重要边界：这 5 个候选在两种上下文中的 ensemble 排名顺序仍然相同。因此目前
只能确认“分数具有 batch-context sensitivity”，不能声称正式 3 x 50 中正确酶
rank 已经发生变化。正式 3 x 50 尚未执行，rank 是否一致仍待 D4 验证。

### 2.3 正式 3 x 50 冻结参考的来源

D4A 已固定 3 个 smoke case，每个 case 为 1 个正确酶加 49 个负例，共 150 个
唯一候选。将 150 个 `example_id` 独立映射回 seed-40 冻结 test 表得到：

| Case | 候选数 | 历史来源 batch 数 | 来源 batch | 冻结表正确酶 `reference_rank` |
|---|---:|---:|---|---:|
| 0 | 50 | 5 | 35, 240, 241, 242, 243 | 18 |
| 1 | 50 | 8 | 5, 72, 73, 74, 75, 76, 77, 78 | 27 |
| 2 | 50 | 2 | 6, 78 | 17 |

即每个 50-candidate 冻结参考都由多个历史 256 行推理上下文中的单行分数重新排序
形成，而正式 wrapper 会把同一 case 的 50 个候选作为一个新的请求上下文。

### 2.4 重复前向和幂等性证据

同一已加载模型、同一 5 行请求批次连续前向两次：

```text
5 candidates x 5 seeds 的最大未舍入 post-sigmoid 分数差：1.043081283569336e-06
各 seed 重复 rank：一致
5-seed ensemble 重复 rank：一致
```

这只是底层前向诊断。D4A2 尚未生成公开 wrapper response，因此不能把“rank
一致”写成老师要求的“同输入 -> 同输出”已经 PASS。

### 2.5 计时证据的适用范围

```text
加载特征资产并构建四个 256 行来源批次：63.921241 s
构建并加载 5 个模型：                   0.893498 s
5 个模型完成一次 5 行请求前向：          0.103714 s
同一请求 warm repeat：                   0.098020 s
```

其中 63.92 秒包含 1,024 行诊断数据构建，不是正式 50 或 100 候选 wrapper
冷调用耗时，不能据此判定老师的 60 秒门控通过或失败。

### 2.6 当前科学运行域和实际依赖

当前冻结运行时能够直接消费已有预计算资产，但不会为任意新 reaction/UID 自动
生成缺失的 GVP、pocket ESM、sequence ESM、DRFP 或分子构象资产。

除 PyTorch、Pydantic 和标准库外，现有科学代码实际还会使用 PyG、
`torch-cluster`、`torch-scatter`、RDKit、pandas、NumPy、scikit-learn、ASE、
PyYAML 和 tqdm。这些是现有模型数据构建/推理路径的运行依赖，不是拟新增的
Agent 框架。

---

## 三、需要老师确认的实施口径

### Q1. 3 x 50 smoke test 的“正确酶 rank 与冻结 test 完全一致”以哪个上下文为准？

请确认以下哪一种口径控制 D4 验收：

```text
A. 以每个 50-candidate wrapper 请求本身作为正式 D4 推理上下文。
   在该上下文中产生并验收输出；历史 reference_rank 18/27/17 只作为
   provenance 对照，不作为跨 batch-context 的强制相等门控。

B. 仍强制正确酶 rank 分别精确等于历史冻结值 18/27/17。
   若选 B，请同时确认是否允许 wrapper 在内部引入请求之外的历史 256 行
   候选以重建各行原始上下文，或请指定其他合法复现方法。

C. 修改 padding/masking/aggregation 行为，建立新模型版本并重新生成冻结参考。
```

本地建议：**A**。理由是它只排序调用者实际提交的 50 个候选，不修改冻结 v1
checkpoint，也不把请求外候选隐式带入推理。batch-context sensitivity 会在 D4
报告中作为已知边界披露。

另外，三个冻结正确酶 rank 18、27、17 均超过请求 schema 的默认
`top_k=10`。为保证 smoke test 能观察正确酶 rank，请确认正式测试调用方式为：

```text
base request：50 个有效候选，top_k=50，return_ci=True；
无效 UID 子测试：在相同 50 个有效候选之外再加入 3 个不存在的 UID，
                 即输入共 53 个 UID，top_k=50，输出仍为 50 个有效候选。
```

无效 UID 会进入老师规定的原始输入 `evidence_hash`，但不会进入模型推理、输出或
rank。若老师希望“用 3 个无效 UID 替换 3 个负例”或采用其他调用参数，请明确
指定。

### Q2. D4 v1 的有效运行域，以及缺失预计算资产时如何处理？

D3 输入允许上游提供合法的 `reaction_smiles` 和 UID，但当前科学运行时只支持
已有完整预计算资产的 reaction/UID。请分别确认：

```text
1. D4 v1 是否正式限定为“冻结资产索引中可解析的 reaction + UID”？

2. reaction_smiles 合法但没有所需 DRFP/分子资产时：
   抛出指定异常 / 返回空 ranked_enzymes / 另行规定？

3. UID 字符串存在但缺少任一 GVP、pocket ESM 或 sequence ESM 资产时：
   是否按“不存在的 UID”同样静默跳过？
```

本地建议：D4 v1 先明确限定在预计算资产域；缺失候选酶资产的 UID 静默跳过；
缺失 reaction 资产时抛出老师指定的明确异常。这样不虚构在线特征生成能力，也
不增加 response schema 字段。

### Q3. “wrapper 只依赖 PyTorch + Pydantic + 标准库”的边界如何解释？

请确认：

```text
A. wrapper 层不新增 CrewAI/LangChain/FastAPI 等依赖，但允许调用冻结
   EnzymeCAGE 科学运行时已经需要的 PyG、RDKit、NumPy 等依赖；

B. 整个可运行交付环境必须严格只有 PyTorch、Pydantic 和标准库。
   若选 B，则现有科学推理路径无法直接运行，需要先单独授权依赖消除或
   运行时重构，不能直接进入当前 D4 实现。
```

本地建议：**A**。wrapper 本身保持轻量，不额外引入 Agent/Web 框架；现有科学
运行依赖作为冻结模型运行时的一部分如实列出。

### Q4. 60 秒门控是否包含冷启动？

D3 同时规定单次 100 候选调用不超过 60 秒，以及 smoke test 的 50 候选不超过
60 秒。D4 将分别记录并检查 50 和 100 候选；这里只需确认计时边界：

```text
A. 只计模型和资产完成一次性初始化后的 predict() 调用；
B. 首次 cold predict()，包含全部模型/资产初始化；
C. cold 和 warm 两种调用都必须 <=60 秒。
```

本地建议：**A**，同时在报告中分别披露初始化耗时、首次请求耗时和 warm repeat
耗时。这符合常驻模型服务的运行方式，也不会隐藏 cold-start 成本。

### Q5. “同输入 -> 同输出”的精确判定标准是什么？

重复底层前向的 rank 相同，但 25 个分数的最大差为约 `1.043e-6`。请确认公开
response 的幂等性标准：

```text
A. 完整序列化 response 必须逐字节完全一致，包括 score 和 ensemble_ci；

B. rank、UID 顺序和 evidence_hash 必须完全一致，score/CI 允许在指定容差内；

C. 老师批准固定小数位后再返回 score/CI，并要求舍入后的完整 response
   完全一致。
```

如选 **B** 或 **C**，请给出容差或保留小数位。确认前不会自行加入 rounding、
caching 或宽松容差。

### Q6. `score` 和 5-seed 分位区间的精确数值口径

请确认采用以下实现：

```text
每个 seed score：沿用冻结 test `pred` 的 post-sigmoid 概率
ensemble score：5 个 seed score 的 float64 算术均值
ensemble_ci：torch.float64 quantile([0.025, 0.975]), interpolation="linear"
```

D4A2 中 torch 与独立标准库 linear quantile 的最大差为
`1.1102230246251565e-16`。报告中会把该区间准确描述为 5 个 seed 输出分数的
分位范围，不把它解释为统计显著性或总体参数的置信区间。

### Q7. 重复 UID 和并列分数如何确定唯一输出？

```text
重复 UID：保留重复项 / 去重 / 拒绝请求？

完全相同的 ensemble score：
  保持输入顺序 / UID 字典序作为第二排序键 / 其他规则？
```

本地建议：候选输出按 UID 去重；同分时按 UID 升序作为第二排序键。这样 UID
重排不会在同分情况下改变输出顺序，也与 evidence_hash 对 UID 列表先排序的
设计一致。

无论选择哪种输出规则，`evidence_hash` 都将严格基于原始请求中的完整 UID
列表计算；除非老师明确修改公式，否则排序时保留重复字符串，不先去重。

### Q8. `evidence_hash` 的字节编码和文本形式

老师已固定待哈希字符串内容。为保证跨机器结果唯一，请确认：

```text
将完整字符串按 UTF-8 编码后计算 SHA256，返回 64 位小写十六进制 hexdigest。
```

换行符严格使用公式中的 `\n`，不使用平台相关换行。D4A 已按该口径验证已有
hash 测试向量。

---

## 四、等待确认期间的边界

在收到上述实施口径前，不启动 D4B，不修改模型行为，也不把 D4A2 的诊断结果
写成正式 D4 PASS。

收到确认后，D4B 只实现：

```text
老师已经发布的 D3 正式合同
+ 老师对 Q1--Q8 的明确选择
```

正式交付仍严格保持：

```text
enzymecage_wrapper/
d4_smoke_test_report.md
```

不会增加 HTTP、Web/Agent 框架、酶到菌逻辑、化学合法性校验、新公开字段或
未经批准的模型修复。
