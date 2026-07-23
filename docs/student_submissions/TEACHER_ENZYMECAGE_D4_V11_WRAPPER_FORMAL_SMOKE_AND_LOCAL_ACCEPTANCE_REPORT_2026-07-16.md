# EnzymeCAGE D4 v1.1 Wrapper Formal Smoke 与本地验收报告

日期：2026-07-16

状态：D4 v1.1 实现与 formal smoke 已完成，本地独立审计通过，提交老师审阅；M3 尚未启动。

## 一、依据与范围

本次 D4 严格依据以下两份老师文件执行：

```text
00_Authority_Teacher_Plan/
TEACHER_REPLY_D1D2_CLOSURE_AND_D3_CONTRACT_2026-07-15.md

00_Authority_Teacher_Plan/
TEACHER_REPLY_D4_PREIMPLEMENTATION_CLARIFICATION_2026-07-16.md
```

实施范围仅包括老师批准的 Python 函数级 wrapper、资产索引和 formal smoke；未加入 HTTP/FastAPI、CrewAI、LangChain 或未经批准的字段与行为，未进入 M3 端到端联调。

## 二、老师要求的交付物

最终包内已包含：

```text
enzymecage_wrapper/
├── __init__.py
├── schema.py
├── predictor.py
├── asset_index.py
├── utils.py
├── requirements.txt
└── tests/
    └── test_smoke.py

d4_smoke_test_report.md
```

同时保留 formal smoke 原始输出、逐 seed 证据、验证器结果、环境记录、checkpoint 身份和完整性清单，供复核使用。

## 三、D3 v1.1 裁定落实情况

| 裁定 | 落实结果 | 状态 |
|---|---|---|
| 正式推理上下文为调用方实际提交的候选集 | 三个 case 均将各自 50 个候选作为一个完整请求批次，不混入历史 256 行上下文 | 完成 |
| D4 v1 运行域限于冻结资产索引可解析的 reaction 和 UID | `asset_index.py` 负责解析；无效 UID 静默跳过；reaction 缺资产时抛 `MissingReactionAssetError` | 完成 |
| wrapper 层依赖与冻结科学运行时分层 | `requirements.txt` 分栏记录；未新增 Agent/Web 框架依赖 | 完成 |
| init、first、warm 分段计时 | 三段分别记录；50 和 100 候选 warm 调用均单独实测 | 完成 |
| rank/UID/hash 严格幂等，score/分位范围容差 `1e-5` | 三个重复请求的 rank、UID、hash 完全一致；最大浮点差低于 `1e-5` | 完成 |
| 五 seed 使用 linear 2.5%/97.5% quantile | 已由逐 seed 原始分数独立重算；报告明确其为经验分位范围，不冒充统计置信区间 | 完成 |
| `evidence_hash` 使用原始 UID 列表并保留重复项 | 使用 UTF-8、LF、排序后保留重复项；canonical test vector 通过 | 完成 |
| 推理层按首次出现顺序去重 UID | 53 条重复输入对应 50 条唯一 forward/output 行，hash 仍保留原始输入 | 完成 |

## 四、正式 3 x 50 结果

使用冻结 v1 的 corrected-pocket ESM-2 3B 五模型 ensemble（seeds 40--44）。三个 case 的正确酶均在 `top_k=50` 返回结果中，重复调用排名一致：

| Case | 正确 UID | Wrapper rank | Repeat rank | 历史 rank（仅 provenance） |
|---:|---|---:|---:|---:|
| 0 | `O29953` | 22 | 22 | 18 |
| 1 | `O33289` | 27 | 27 | 27 |
| 2 | `Q47317` | 17 | 17 | 17 |

上述结果只证明三个正确酶在 Top-50 内可见和重复调用排名稳定。三个正确酶均未进入 Top-10，因此本次结果不表述为 Top-10 检索成功，也不据此宣称候选酶排序效果优秀。

历史 rank 只用于来源对照。按照老师 2026-07-16 的裁定，它不是跨 batch-context 的强制相等门控。

## 五、修订后 9 项 Smoke Test Checklist

| # | 老师要求 | 实测结果 | 状态 |
|---:|---|---|---|
| 1 | 三个正确酶 Top-50 可见且重复 rank 一致 | `22/22`、`27/27`、`17/17` | PASS |
| 2 | `evidence_hash` 可复现且测试向量锁定 | 三个重复 hash 完全一致；canonical SHA256 为 `bd19fd6441b5baa26079185628160d51f46fc47e28743210fd96ede359202120` | PASS |
| 3 | ensemble 分位范围合理并如实命名 | 所有宽度有限且位于 `(0,1)`；逐 seed linear quantile 重算一致 | PASS |
| 4 | warm-50 不超过 60 秒并披露三段耗时 | init `67.8527023291s`；first `0.6169522110s`；warm-50 `0.3273567309s` | PASS |
| 5 | 输出长度等于 `min(top_k, 有效唯一 UID 数)` | 正式请求均为 50；另测 top_k=10、return_ci=False 和 100 候选，长度均正确 | PASS |
| 6 | 50 有效 UID + 3 无效 UID 容错 | 三次请求均返回 50 条有效结果，无效 UID 不进入输出 | PASS |
| 7 | 重复 UID 推理去重、hash 保留原始输入 | 53 条原始输入、50 条唯一 forward、50 条唯一输出 | PASS |
| 8 | reaction 缺资产时抛指定异常 | 缺 DRFP 和 molecule-conformation graph 的 case 在 forward 前抛 `MissingReactionAssetError` | PASS |
| 9 | 披露 batch-context sensitivity | 25 个 seed/candidate 对照的精确最大差为 `0.6218325197696686` | PASS |

100 候选 warm 调用为 `0.5588800320s`，同样低于 60 秒。最大重复调用 score/lower/upper 差分别为：

```text
4.648783942240442e-07
1.8030405044000553e-07
7.521361112261538e-07
```

均低于老师规定的绝对容差 `1e-5`。

## 六、已知边界

1. D4 v1 只支持冻结资产索引中可解析的 reaction 和 UID，不支持任意新 reaction 或新 enzyme 的在线特征生成。
2. 模型存在已确认的 batch-context sensitivity。`0.6218325197696686` 是 D4A2 五候选诊断中 25 个 seed/candidate 对照的最大绝对差，不是 150 行 formal-smoke 的汇总值。
3. `ensemble_ci` 是五个 seed 输出的 2.5%/97.5% 经验分位范围，不是统计学 95% 置信区间或显著性区间。
4. 初始化耗时 `67.8527s` 不计入老师裁定的 warm gate；first、warm-50 和 warm-100 已分别披露。
5. 三个正确酶只达到 Top-50 可见，未达到 Top-10。

## 七、本地独立审计与包完整性

本地未直接接受执行端自报 PASS，而是独立复核目录、manifest、tar、identity、解包内容和权限。结果如下：

```text
final validator exit                         0
raw per-seed evidence rows                4000
teacher checklist rows                       9
mandatory requirement IDs                   22
package regular files                        71
manifest entries                             70
manifest failures                             0
tar members                                  79
fresh-extraction body/mode mismatches         0
```

```text
manifest SHA256
944fe2d22b6b43808a1d6a6250ad62e652a4b52e7e7b36d91a58a012fecd326d

tar SHA256
12df378964793561c2d193d92c16276739b14df1761ff34c0e46f426e5cad0f7
```

tar 只有一个顶层目录；成员顺序、`mtime=0`、`uid=gid=0`、空 owner/group、脚本权限和解包后逐文件内容均通过检查。

本地审计结论：

```text
D4_FULL_LOCAL_ACCEPTANCE_PASS
```

## 八、当前结论与下一步

D4 v1.1 wrapper 实现、三案例 formal smoke、9 项 checklist、老师 Q1--Q8 裁定落实和完整性审计均已完成。当前结论是“本地通过并提交老师审阅”，不写成“老师已经验收”。

请老师审阅 D4 交付物和上述结果。收到老师对 D4 的确认或后续指示后，再进入 M3 端到端三案例联调；本次未提前实施 M3。
