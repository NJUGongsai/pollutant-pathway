# D1/D2 闭环确认 & D3 Wrapper 接口契约（正式版）

日期：2026-07-15  
状态：D1 ✓ / D2 ✓ / D3 发出 / D4 待启动

---

## 一、D1/D2 确认

D1（v1 冻结包制作 + 完整性审计）和 D2（交付说明 + 边界披露）确认通过，闭环。

做到位的几件事：
1. 3B 五 seed ensemble 主线 + 600M 五 seed ensemble AUC 参照，定位清晰
2. pocket 处理不对称、P1 欠训练假设否定、P3 关闭——全部主动披露，没藏
3. 12 个训练运行本地备份 + SHA256 校验 + 长期保留，证据链完整

不需要返工，直接进 D3/D4。

---

## 二、D3：EnzymeCAGE v1 Wrapper 接口契约

以下是**正式版**契约。拿到即可启动 D4 实现。

### 2.1 输入 Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple

class EnzymeCAGERequest(BaseModel):
    reaction_smiles: str = Field(
        ..., description="目标反应的 SMILES 字符串"
    )
    enzyme_pool_uids: List[str] = Field(
        ..., min_length=1, description="候选酶 UID 列表（来源由上游 Agent 提供）"
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="返回排序前 K 个结果"
    )
    return_ci: bool = Field(
        default=True, description="是否返回 5-seed ensemble 置信区间"
    )
```

### 2.2 输出 Schema

```python
class RankedEnzyme(BaseModel):
    uid: str
    score: float = Field(..., description="5-seed ensemble 平均分")
    rank: int = Field(..., ge=1, description="从 1 开始连续编号")
    ensemble_ci: Optional[Tuple[float, float]] = Field(
        default=None,
        description="5-seed 打分的 [lower, upper] 95% 分位 CI；return_ci=False 时为 None"
    )

class EnzymeCAGEResponse(BaseModel):
    ranked_enzymes: List[RankedEnzyme] = Field(
        ..., description="按 score 降序排列，长度 = min(top_k, 有效候选数)"
    )
    model_version: str = Field(default="v1_20260714")
    evidence_hash: str = Field(
        ..., description="本次推理输入的 SHA256 摘要，用于复现追溯"
    )
```

### 2.3 行为约束

| 约束项 | 要求 |
|---|---|
| 排序键 | `score` 降序，`rank` 从 1 开始连续 |
| ensemble 逻辑 | 5 个 seed checkpoint 各自前向推理 → 取 mean 作 `score`，取 2.5%-97.5% 分位作 `ensemble_ci` |
| 无效 UID 处理 | `enzyme_pool_uids` 中含不存在的 UID → 跳过该 UID，不抛异常，不计入 rank |
| `evidence_hash` 算法 | `SHA256(reaction_smiles + "\n" + "\n".join(sorted(enzyme_pool_uids)) + "\n" + model_version)` |
| 超时约束 | 单次调用 ≤ 60s（100 个候选酶，单卡 4090D 48GB） |
| 幂等性 | 同输入 → 同输出（推理时 eval 模式，不做 dropout） |
| 返回长度 | `len(ranked_enzymes) = min(top_k, 有效候选酶数量)` |

### 2.4 不做的事（边界明确）

- **不负责** `enzyme_pool_uids` 的来源——pool 由上游 Agent 提供，wrapper 只做排序
- **不负责** 后续"酶 → 菌"映射——那是下游 `Enzyme2OrganismTool` 的事
- **不嵌入** 任何 HTTP 框架——D4 阶段先做 Python 函数级 wrapper，M3 联调时再考虑 FastAPI 包装
- **不做** 输入的化学合法性校验——reaction_smiles 的合法性由上游 Agent 保证

---

## 三、D4 实现要求

### 3.1 目标

一个可直接调用的 Python 函数：

```python
def predict(request: EnzymeCAGERequest) -> EnzymeCAGEResponse:
    ...
```

### 3.2 代码结构

```
enzymecage_wrapper/
├── __init__.py
├── schema.py          # EnzymeCAGERequest / RankedEnzyme / EnzymeCAGEResponse
├── predictor.py       # predict() 函数：加载 5 checkpoint → 推理 → 聚合
├── utils.py           # compute_evidence_hash()
└── tests/
    └── test_smoke.py  # smoke test 脚本
```

### 3.3 Smoke Test 验收标准

从 P0 test set 中任取 **3 个 reaction**，每个配 **50 个候选酶**（含正确酶 + 随机负例），跑 `predict()`。

验收 checklist：

| # | 检验项 | 通过条件 |
|---|---|---|
| 1 | 正确酶 rank 一致性 | 与冻结 test 结果完全一致（幂等保证） |
| 2 | evidence_hash 可复现 | 同输入跑两次，hash 相同 |
| 3 | ensemble_ci 合理性 | CI 宽度 > 0 且 < 1（不全是 [0,0] 也不全是 [0,1]） |
| 4 | 耗时 | ≤ 60s / 50 enzyme |
| 5 | 输出长度 | `len(ranked_enzymes) == min(top_k, 有效候选数)` |
| 6 | 无效 UID 容错 | 插入 3 个不存在的 UID，不报错，不出现在结果中 |

### 3.4 交付物

完成 D4 后提交：
1. `enzymecage_wrapper/` 目录（代码）
2. `d4_smoke_test_report.md`：3 个 case 的输入/输出/耗时 + 6 项 checklist 通过状态

---

## 四、时间预期

| 任务 | 预计耗时 |
|---|---|
| D4 wrapper 实现（predictor.py 核心） | 2 天 |
| D4 smoke test + report | 0.5 天 |
| 完成后进入 M3（端到端 3 case 联调） | - |

---

## 五、注意事项

1. **checkpoint 加载**：5 个 seed 的 checkpoint 路径从冻结包里读，不要硬编码绝对路径。建议用一个 `config.yaml` 或环境变量指定冻结包根目录
2. **依赖隔离**：wrapper 只依赖 PyTorch + Pydantic + 标准库，不引入 CrewAI / LangChain 等框架（那些是上层 Agent 的事）
3. **eval 模式**：推理时所有模型必须 `.eval()` + `torch.no_grad()`，确保幂等
4. **不要自作主张加东西**：契约里没写的字段不要加、没写的行为不要做。有疑问先问，不要"觉得应该有"就加进去

有问题随时问，没问题就开始。
