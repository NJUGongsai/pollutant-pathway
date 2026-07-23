# R3 Retrieval Toolkit 交付 Checklist（GitHub 上传 + Codex 自动执行）

> 接收人：执行 R3 toolkit 打包的学生（Codex 自动执行）
> 目的：把 R3 模型封装成本地纯 numpy 可调用的检索工具包，上传至 GitHub，供下游 agent prototyping 直接 import 使用
> 不做：不上线 API 服务、不做 LLM 集成、不重训、不收 OOD 数据
> 上游依据：v2 leak-fix 已通过（HO EC-3 MRR=0.619, ratio=0.663），R3 已冻结（SHA256 `f728455...c4c`）

---

## 0. 交付目标（一眼看明白）

```
07_r3_retrieval_toolkit_2026-06-17/
├── r3_retrieval/              # Python package（纯 numpy，无 torch）
│   ├── __init__.py
│   ├── loader.py              # 加载 embeddings_v3.npz / metadata_v3.json
│   ├── retrieval.py           # 4 个 retrieval primitive
│   ├── metadata.py            # lookup + EC index
│   └── version.py
├── tests/                     # pytest 单元测试
│   ├── test_loader.py
│   ├── test_retrieval.py
│   └── test_metadata.py
├── examples/                  # 6 个 runnable example
│   ├── 01_r2e_basic.py
│   ├── 02_e2m_candidate_set.py
│   ├── 03_s2m_candidate_set.py
│   ├── 04_metadata_lookup.py
│   ├── 05_unseen_ec4_abstain.py
│   └── 06_ec_classification.py
├── data/
│   ├── README.md              # 指向 HPC 上 .npz / .json 路径（文件不上 GitHub，太大）
│   ├── MODEL_ARCHITECTURE.md  # reaction(/substrate) encoder 网络结构说明（开域查询用）
│   └── r3_reaction_encoder.npz  # 从 model_v3.pt export 的 projection weights（几 MB，可上 GitHub）
├── requirements.txt           # numpy>=1.26 即可（runtime 纯 numpy）
├── README.md
└── CHECKLIST_EXEC_LOG.md      # Codex 执行后填这份，记录每步实际输出
```

---

## 1. 6 个 retrieval API 的契约（学生不需要改设计，照实现即可）

### 1.1 `r2e_retrieval(reaction_drfp, top_k=10) -> List[Candidate]`

```python
@dataclass
class Candidate:
    uniprot_id: str         # e.g. "P12345"
    ec_number: str          # e.g. "1.14.13.1"
    organism: str           # e.g. "Escherichia coli K-12"
    organism_taxonomy: str  # e.g. "Bacteria/Proteobacteria/..."
    annotation: str         # e.g. "Phenol 2-monooxygenase"
    score: float            # cosine similarity, [-1, 1]
    rank: int               # 1-indexed
    row_index: int          # 原 metadata_v3.json 中的 index
```

实现要点：
- L2-normalize reaction embedding 与 corpus（enzyme）embedding
- `score = reaction @ enzyme.T`，按 score 降序取 top-K
- metadata 字段从 `metadata_v3.json` 取，找不到就填 `"unknown"`，**不要抛异常**

### 1.2 `e2m_retrieval(enzyme_emb_or_uniprot, top_k=50) -> List[MicrobeCandidate]`

```python
@dataclass
class MicrobeCandidate:
    microbe: str
    assembly_accession: str
    score: float
    rank: int
    row_index: int
```

注意：top-1 实测 ≈ 0.006，**API doc 必须明确写 "do not consume top-1, use top_k as candidate set"**。

### 1.3 `s2m_retrieval(substrate_drfp, top_k=100) -> List[MicrobeCandidate]`

同 1.2，warning 同上。

### 1.4 `lookup_metadata(uniprot_id: str) -> dict`

```python
{
    "uniprot_id": "P12345",
    "ec_number": "1.14.13.1",
    "organism": "...",
    "annotation": "...",
    "sequence": "MSKLA..."  # 可选，若 metadata_v3.json 里有
}
```

`uniprot_id` 不存在时返回 `None`，**不要抛异常**。

### 1.5 `is_known_ec4(ec_str: str) -> bool`

判定该 EC-4 是否出现在训练集（即 metadata_v3.json 里至少有 1 row 的 EC-4 等于此值）。
返回 `False` 的 EC-4 在 agent 端必须走 abstain（cross-class transfer 仅 0.619，不到 0.80 阈值）。

### 1.6 `get_ec3_neighbors(ec_str: str) -> List[str]`

给定 EC-4，返回同 EC-3 的所有训练集 EC-4 邻居。供 agent 端 fallback 决策（v2 数字虽未到 0.80，仍可让 agent 自己用此函数构造 fallback set）。

### 1.7 开域 reaction query 支持（外置交付物，非 runtime API）

上面 6 个 API 都是 **closed-corpus retrieval**：query 必须来自 corpus 已有的 145607 行（直接用预计算 embedding）。但 agent 真实场景下大多数 target reaction **不在 corpus 中**，需要实时编码。

Toolkit **不内置 encoder**（避免 runtime 引入 torch / rdkit），改为额外交付两份文件，让下游消费方（我）自己在 agent 端用 numpy 复现 forward pass：

```
RxnSMILES → DRFP (rdkit, 我侧) → 加载 r3_reaction_encoder.npz 做投影 → L2-normalize → reaction_emb
                                                                              ↓
                                                          直接喂给 r2e_retrieval 的检索内核
```

学生侧**只需 export weights + 写清结构**，不实现 inference。torch 仅用于一次性 export（build-time 工具），**不进 requirements.txt**。

---

## 2. Codex 执行步骤（按 RULE-ID 顺序）

### RULE-1: 创建目录骨架

```bash
mkdir -p 07_r3_retrieval_toolkit_2026-06-17/{r3_retrieval,tests,examples,data}
cd 07_r3_retrieval_toolkit_2026-06-17
```

**验收**：tree 命令输出与 §0 目录结构一致。

### RULE-2: 实现 `r3_retrieval/loader.py`

```python
import json
import numpy as np
from pathlib import Path

def load_artifacts(output_dir: str | Path) -> dict:
    """Load R3 embeddings and metadata from output_dir.

    Returns dict with keys:
        reaction_emb, enzyme_emb, substrate_emb, microbe_emb (np.ndarray, L2-normalized)
        metadata (list of dict, length N)
    All embeddings are float32 and L2-normalized along last axis.
    """
    output_dir = Path(output_dir)
    npz = np.load(output_dir / "embeddings_v3.npz")
    with open(output_dir / "metadata_v3.json") as f:
        metadata = json.load(f)

    def l2(x):
        n = np.linalg.norm(x, axis=-1, keepdims=True)
        n = np.where(n == 0, 1.0, n)
        return (x / n).astype(np.float32)

    return {
        "reaction_emb": l2(npz["reaction"]),
        "enzyme_emb":   l2(npz["enzyme"]),
        "substrate_emb": l2(npz["substrate"]) if "substrate" in npz.files else None,
        "microbe_emb":   l2(npz["microbe"])   if "microbe"   in npz.files else None,
        "metadata":      metadata,
    }
```

**验收**：调用 `load_artifacts(...)` 不抛异常，返回 dict 含上述 key，shape 与 N=145607 对齐。

### RULE-3: 实现 `r3_retrieval/retrieval.py`

按 §1.1 – §1.3 实现 3 个 retrieval function。所有 function 必须：
- 仅依赖 numpy，不 import torch
- 输入 query 自动 L2-normalize（防调用方忘记）
- 返回结果按 score 降序排列，rank 从 1 开始
- 提供 `top_k` 参数，默认值见 §1

**关键实现细节（防再次出现 leak）**：
- `r2e_retrieval` 不需要 ban self（agent 调用时 query reaction 通常不在训练集中；如果在训练集中，让 agent 自己决定是否要 ban）
- 提供 `exclude_self_row_index: Optional[int] = None` 参数，agent 可选择性 ban 某个 corpus row
- 提供 `exclude_ec4_set: Optional[Set[str]] = None` 参数，agent 可选择性 ban 某些 EC-4 class

### RULE-4: 实现 `r3_retrieval/metadata.py`

按 §1.4 – §1.6 实现 3 个 API。EC index 从 metadata 一次性构建并缓存：

```python
def build_ec_index(metadata: list) -> dict:
    """One-pass scan, return {ec4_set, ec3_to_ec4s, uniprot_to_row_index, ...}"""
```

**验收**：`is_known_ec4("1.14.13.1")` 返回 `True`，`is_known_ec4("99.99.99.99")` 返回 `False`。

### RULE-5: 实现 6 个 example 脚本

每个 example 必须 self-contained，可直接 `python examples/0X_*.py` 运行。

| 文件 | 内容 | 预期输出 |
|---|---|---|
| `01_r2e_basic.py` | 取 metadata 第 0 行 reaction，调 r2e top-5 | top-1 score ≥ 0.9（自身 row）+ 5 个 candidate 列表 |
| `02_e2m_candidate_set.py` | 取一个 enzyme，调 e2m top-50 | 50 个 microbe candidate；显式 warn "top-1 ≈ 0.006, use as candidate set" |
| `03_s2m_candidate_set.py` | 取一个 substrate，调 s2m top-100 | 同上 warn |
| `04_metadata_lookup.py` | 给一个 UniProt ID 查 metadata | 字段完整或返回 None，不抛异常 |
| `05_unseen_ec4_abstain.py` | 构造 fake unseen EC-4 → 触发 is_known_ec4=False → abstain | 输出 "abstain due to unseen EC-4" |
| `06_ec_classification.py` | 用 r2e top-10 + majority vote 给反应分类 | 输出 predicted EC-4 + 投票分布 |

### RULE-6: 写 pytest 单元测试

```python
# tests/test_loader.py
def test_load_artifacts():
    art = load_artifacts(TEST_DIR)
    assert art["reaction_emb"].shape[0] == 145607
    assert np.allclose(np.linalg.norm(art["reaction_emb"], axis=-1), 1.0, atol=1e-5)

# tests/test_retrieval.py
def test_r2e_self_query_top1_score_high():
    """同一 row 的 reaction query 应该 top-1 retrieve 到自己 (score > 0.99)。"""

def test_r2e_returns_dataclass_with_metadata():
    """每个 Candidate 必须含 organism / annotation 字段（非 None / 非空）。"""

def test_unseen_ec4_returns_false():
    assert is_known_ec4("99.99.99.99") is False
```

**验收**：`pytest tests/ -v` 全 PASS。

### RULE-7: 写 `data/README.md`

明确指出：
- `embeddings_v3.npz`（~150MB）和 `metadata_v3.json`（~50MB）**不上传 GitHub**
- HPC 路径：`/public/home/acfbwjsi7s/bio_vector_full_run_2026-06-04/outputs/r3_ec4_balanced_stage3skip_2026-06-15/`
- 用户使用本 toolkit 时，需先把这两个文件复制到本地 `data/` 目录或通过 `--output_dir` 参数指向

### RULE-8: 写 `requirements.txt`

```
numpy>=1.26.0
pytest>=7.0.0
```

仅此。**不要加 torch / transformers / sklearn 任何深度学习依赖**——这是纯 numpy offline toolkit。

### RULE-9: 写 `README.md`

必须包含：
- 一句话定位（"R3 enzyme retrieval toolkit, pure numpy, offline, no API server"）
- 数据准备（指向 `data/README.md`）
- 6 个 API 的最小调用 example（每个 5–10 行）
- 性能数字一览表（EC-4 grouped 0.918 / cross-class EC-3 transfer 0.619 / row-level 不可达）
- Agent v1 调用 gating 模板（score ≥ 0.9 + is_known_ec4）

### RULE-10: 写 `data/MODEL_ARCHITECTURE.md`（开域 query 用）

详细描述 reaction encoder（及 substrate encoder，如结构不同）的网络结构。模板：

```yaml
reaction_encoder:
  input:
    name: DRFP fingerprint
    shape: [2048]
    dtype: float32        # 实际是 0/1 binary，export 后按 float32 处理
  layers:
    - {type: linear, in: 2048, out: 768, bias: true, activation: null}
    # 若为多层 MLP / 含 layernorm，按 forward 顺序逐层列出
  output:
    name: reaction embedding
    shape: [768]
    post_processing: L2-normalize
  weights_file: r3_reaction_encoder.npz
  weights_layout:
    W: [768, 2048]        # 与 numpy `emb = drfp @ W.T + b` 匹配；若转置另说明
    b: [768]
```

substrate encoder 如与 reaction encoder 共享结构/权重，写明；不同则单列。

**验收**：yaml 块可解析；layer 顺序与 `model_v3.pt` 的 state_dict 一致（学生打印 state_dict key 比对）。

### RULE-11: export `data/r3_reaction_encoder.npz`

从 `model_v3.pt` 中**只读 export** reaction projection 的 weights（不修改原文件）：

```python
import torch, numpy as np

ckpt = torch.load("model_v3.pt", map_location="cpu", weights_only=True)
# key 名按实际 model 命名调整，下面是示例
W = ckpt["reaction_proj.weight"].numpy().astype(np.float32)  # [768, 2048]
b = ckpt["reaction_proj.bias"].numpy().astype(np.float32)    # [768]
np.savez("data/r3_reaction_encoder.npz", W=W, b=b)
# 多层 MLP 则存 W1,b1,W2,b2,... 并在 MODEL_ARCHITECTURE.md 标明顺序
```

**验收（关键 sanity check）**：用 corpus 第 0 行的原始 DRFP 走 numpy forward（`emb = drfp @ W.T + b`，再 L2-normalize），与 `embeddings_v3.npz["reaction"][0]` 的 cosine similarity **≥ 0.9999**。这是证明 export 的 weights 与训练时 encoder 完全一致的硬验证。如果 < 0.9999，说明结构写漏了层（layernorm / activation / 多层 projection），回 RULE-10 补全。

### RULE-12: 写 `CHECKLIST_EXEC_LOG.md`

Codex 执行完上述 11 步后，**自己填**这份 log，记录：
- 每个 RULE 的实际输出 / 是否 PASS
- pytest 全部 case 的 pass/fail
- 6 个 example 的实际 stdout 截取
- 任何 deviation 与原因

---

## 3. 上传 GitHub

### RULE-13: Git 提交

```bash
cd /path/to/enzyme-cage-bio-vector-demo
git checkout main
git pull
# 把 07_r3_retrieval_toolkit_2026-06-17/ 整个目录加进去
# 注意：data/r3_reaction_encoder.npz（几 MB）要上传；embeddings_v3.npz / metadata_v3.json（百 MB 级）不上传
git add 07_r3_retrieval_toolkit_2026-06-17/
git status   # 确认 embeddings_v3.npz / metadata_v3.json 未被误加（但 r3_reaction_encoder.npz 应在）
git commit -m "R3 retrieval toolkit v1: numpy retrieval + reaction encoder weights for open-domain query"
git push origin main
```

**验收**：
- `https://github.com/bgruiiii/enzyme-cage-bio-vector-demo/tree/main/07_r3_retrieval_toolkit_2026-06-17/` 可访问
- 仓库 size 增加 < 10MB（reaction encoder npz 几 MB；确认百 MB 级 artifact 未误传）

---

## 4. Do-NOT 清单（防过度交付）

- ❌ 不要做 Flask / FastAPI server
- ❌ 不要集成 LLM（agent reranker 是下游消费方的事，不是 toolkit 的事）
- ❌ 不要做 GPU 加速（纯 numpy 即可，CPU 端 r2e 单 query < 100ms）
- ❌ 不要做 ANN 索引（faiss / hnswlib）—— 145k 全量 dot product 在 CPU 上 ~50ms，足够；引入 ANN 反而带来精度偏差
- ❌ 不要把 `embeddings_v3.npz` / `metadata_v3.json` 上传 GitHub —— 用 `data/README.md` 指路即可
- ❌ 不要重训、不要动 `train.py`；`model_v3.pt` **只读 export weights，不修改、不上传完整文件**
- ❌ 不要把 encoder export 用的 torch 写进 `requirements.txt`（它是 build-time 工具，runtime 仍纯 numpy）

---

## 5. 验收（学生 done 后我会检查）

| 检查项 | 通过条件 |
|---|---|
| GitHub `07_r3_retrieval_toolkit_2026-06-17/` 目录存在 | tree 与 §0 一致 |
| `pytest tests/ -v` | 全 PASS |
| 6 个 example 可独立运行 | 每个 stdout 与 RULE-5 表预期匹配 |
| `r2e_retrieval` 返回 Candidate dataclass | organism / annotation 非空 |
| `is_known_ec4("99.99.99.99") == False` | True |
| `requirements.txt` 不含 torch | True（torch 仅 export 时用）|
| `data/MODEL_ARCHITECTURE.md` 含 reaction encoder 完整结构 | yaml 可解析 + layer 顺序与 state_dict 一致 |
| `data/r3_reaction_encoder.npz` 数值复现度 | numpy forward 与 `embeddings_v3.npz["reaction"][0]` cosine ≥ 0.9999 |
| 仓库 size 增量 < 10MB | True（含 encoder npz）|
| `CHECKLIST_EXEC_LOG.md` 有 Codex 实际执行记录 | True |

---

## 6. 一句话给学生（Codex prompt suffix）

> 把 R3 封装成本地 numpy package：6 个 retrieval API + 6 个 example + pytest 全过 + README，再 export reaction encoder weights（`r3_reaction_encoder.npz` + `MODEL_ARCHITECTURE.md`）供开域查询。**不上线 API、不集成 LLM、runtime 不依赖 torch、不传百 MB 级大文件**。按 RULE-1 到 RULE-13 顺序执行，每步留 log。验收看 §5 表，全勾再 push。
>
> 关键验证：encoder export 后必须通过 cosine ≥ 0.9999 的复现度 sanity check（RULE-11），否则说明网络结构写漏了层。
