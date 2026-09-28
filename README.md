# dependingv43 — v4.3 确定性路径工作流(资产接线 + LangGraph 主干 + 预测接线)

本仓提供 v4.3 的反应检索资产(本仓 `assets/`)与 v3 冻结引擎代码之间的只读接线
(清单校验、引擎适配器、类比索引装载与 v4 对拍),以及确定性核心工作流:
从底物出发,ReactionFinder 给出分级证据,LangGraph 选择路径、检索、分类、
校验并提交可接受的已记录反应,支持持久化与断点恢复。设计依据见
ARCHITECTURE.md、REPO_DESIGN.md、ASSETS.md;任务边界见 TASK_ASSET_WIRING.md、
TASK_V43_CORE_WORKFLOW.md 与 TASK_V43_PREDICTION_ATOMTOOL.md;实施见
docs/CORE_WORKFLOW_REPORT.md 与 docs/PREDICTION_ATOMTOOL_REPORT.md。

## 安装与环境

需要 Python ≥3.10、RDKit、LightGBM、numpy。本机对拍环境(记录于
docs/ASSET_WIRING_REPORT.md):

```sh
conda create -y -p /Users/cc/miniconda3/envs/depending43 python=3.11
/Users/cc/miniconda3/envs/depending43/bin/python -m pip install "rdkit==2026.3.6" "lightgbm==4.7.0" "numpy==2.4.6" pytest
/Users/cc/miniconda3/bin/conda install -y -p /Users/cc/miniconda3/envs/depending43 -c conda-forge llvm-openmp
```

无需安装即可运行(源码布局):

```sh
export PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src
```

或 `pip install -e .`。

## CLI

配置优先级:CLI 参数 > 环境变量(`V3_CODE_ROOT`、`V43_ASSET_ROOT`)> 默认值
(代码根 `../dependingv3`,资产根本仓 `assets/`)。

```sh
# 资产环境检查:本仓 21 文件清单校验 + v3 原版 resolve_and_verify + 类比索引哈希
python -m pathway_v43 checkenv --v3-code-root ../dependingv3 --assets-root assets

# 完整装载两份类比索引并报告行数(慢,约 +10s)
python -m pathway_v43 checkenv --v3-code-root ../dependingv3 --assets-root assets --analog-rows

# 引擎冒烟:输出候选摘要 + asset_identity(--out 缺省 stdout)
python -m pathway_v43 probe --smiles "Oc1ccccc1O" --v3-code-root ../dependingv3 --assets-root assets --top-k 10
```

`checkenv` 从任意工作目录启动都会定位并校验同一批资产;失败输出结构化 JSON
并返回退出码 2。

## 核心工作流(run / resume / inspect)

```sh
# 从底物出发运行确定性主干(已记录反应→提交;竞争/仅规则类比→awaiting_prediction;无证据→dead_end)
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-smoke --max-depth 2 --max-expansions 3

# 查看 run:status 区分 completed / budget_exhausted / awaiting_prediction / abnormal_stop
python -m pathway_v43 inspect --run-id v43-smoke

# 从 LangGraph SQLite 检查点恢复(先核对代码/资产/策略身份与 graph_revision)
python -m pathway_v43 resume --run-id v43-smoke
```

可选参数:`--max-frontier-width N`(一个事件提交后继续展开的产物路径数,默认 3,
其余合法候选标 deferred)、`--runs-root PATH`(默认 `<repo>/runs`)。

运行产物布局 `runs/<run_id>/`:

| 文件 | 内容 |
|---|---|
| `checkpoint.sqlite` | LangGraph 检查点(thread_id=run_id;执行恢复点) |
| `pathway.sqlite` | 化学路径账本(compounds / reaction_events / event_products / path_instances / graph_revision) |
| `results/<task_id>/{retrieval,decision,validation}.json` | 不可变证据/裁决/校验产物(task_id 幂等;同键异内容报冲突) |
| `run_identity.json` | 代码/资产/策略/依赖身份(resume 核对门槛) |
| `report/pathway.json` | 研究报告:路径、反应事件、证据/拒因、stop_reason、top-5 与展开分离 |

输出约定:run/resume/inspect 的 **stdout 为纯净 JSON**(v3 引擎装载横幅已改道
stderr);失败输出结构化 JSON 并返回退出码 2。无模型配置时遇到待预测路径以
`awaiting_prediction` 明确结束,不谎称预测完成。

冒烟实测(2026-09-24,catechol):run 停在 awaiting_prediction——根路径检索得
3 条竞争已记录反应 + 规则/类比证据,不按引擎分数自动淘汰;详见
docs/CORE_WORKFLOW_REPORT.md。示例报告:`runs/v43-smoke/report/pathway.json`。

## 预测接线:三种模型模式(第三阶段)

在 `classify_evidence` 之后,若路由需要预测(竞争已记录反应 / 类比编辑 /
无证据提案),按 `--model` 三种模式工作;**唯一可用已记录反应永远确定性直通,
不调用模型**。

### 模式一:`--model off`(默认,无模型,零配置)

```sh
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-predict-off --max-depth 1
```

既有确定性流程原样运行;待预测路径以 `stop_reason=awaiting_prediction` 明确
结束(不谎称预测完成)。示例产物:`runs/v43-predict-off/report/pathway.json`。

### 模式二:`--model fake`(剧本假模型,无凭证可跑)

```sh
# 剧本 JSON:{"rank_candidates"|"analogy_edit"|"novel_proposal": ["响应文本", ...]}
cat > /tmp/fake.json <<'JSON'
{"novel_proposal": ["{\"decision\":\"propose\",\"products\":[{\"smiles\":\"O=CCC=CO\",\"note\":\"氧化\"}],\"uncertainty\":\"high\",\"reason\":\"演示\"}"]}
JSON
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-demo-fake \
    --max-depth 1 --model fake --fake-script /tmp/fake.json
```

假模型输出与真实响应走**同一**确定性解析器与校验门禁;调用计数落盘可审计。
仅用于测试与演示,不冒充在线模型验证(验收以 `tests/test_prediction_real.py`
的真实资产口径为准)。

### 模式三:`--model real`(OpenAI 兼容真实提供者,凭证只从环境变量读取)

```sh
export V43_LLM_BASE_URL="https://api.example.com/v1"   # OpenAI 兼容根
export V43_LLM_API_KEY="..."                           # 密钥不落盘、不入日志
export V43_LLM_MODEL="..."                             # 模型名
python -m pathway_v43 run --smiles 'Oc1ccccc1O' --run-id v43-demo-real \
    --max-depth 2 --model real
# 可选:V43_LLM_TIMEOUT_S(默认 60);请求自动携带 Idempotency-Key
```

⚠️ 截至本报告(2026-09-24)本机无凭证,`real` 模式**在线调用未实测**;
缺任一环境变量时启动即结构化报错(`ModelNotConfigured`,不打印密钥值),
不会静默降级为无模型。

### 预测模式的产物位置

`runs/<run_id>/` 在第一阶段布局之上新增(全部不可变,task_id 幂等):

| 文件 | 内容 |
|---|---|
| `results/<task_id>/prediction_task.json` | 预测任务书(完整祖先链+证据+预算+纪律块) |
| `results/<task_id>/prediction_call.aN.json` | 调用记录(status=issued + request_hash + 幂等键) |
| `results/<task_id>/prediction_response.aN.json` | 模型响应(传输层+确定性解析结果) |
| `results/<task_id>/prediction_orphan.aN.json` | 悬空请求审计卡(请求已发出未响应;恢复时重试并留痕,不声称恰好一次) |
| `results/<task_id>/prediction.json` | 最终预测结果(选中卡/提案卡/停留原因) |

报告 `report/pathway.json` 新增路径级 `prediction` 视图与 `llm_calls` 统计;
事件带 `model_ref`。预测身份(模型/提示词/MoleCode 实现/策略)写入
`run_identity.json` 的 `prediction` 与 `molecode` 块,resume 逐字段核对;
改用新代码 resume 第一阶段旧 run 会被身份门槛拒绝,显式迁移用:

```sh
python -m pathway_v43 run --run-id v43-migrated --migrate-from v43-smoke
```

(`--migrate-from` 只读旧 run 身份的输入/策略,旧目录零改动;LLM/提案预算
可用 `--max-llm-calls/--max-proposals` 显式设定,缺省随 `--max-expansions` 派生。)

## dev 批跑、冻结导出与判分(第四阶段)

```sh
# ① 一次性白名单提取 dev 20 路输入(只含 route_id + root_smiles + 哈希)
python -m pathway_v43 batch plan --split dev --batch-root batch_dev_v1 \
    --v3-code-root ../dependingv3
# ② 资源预检(20 路并行容量;不足 → CapacityBlocked,不暗改串行)
python -m pathway_v43 batch precheck --batch-root batch_dev_v1
# ③ 发车(real=DashScope 按量;凭证经 --env-file 读入环境,不落盘不打印)
nohup python -m pathway_v43 batch run --split dev --batch-root batch_dev_v1 \
    --model real --env-file /path/to/.dependingv43-dashscope.env \
    --batch-config configs/dev_batch.json > batch.log 2>&1 &
#    监控:短连接轮询 batch_dev_v1/progress.json 与 batch status
python -m pathway_v43 batch status --batch-root batch_dev_v1
# ④ 单 run 导出 v3 冻结格式(零 LLM;verify 核对新鲜度)
python -m pathway_v43 export --run-id <run_id> --route-id pb_0002
python -m pathway_v43 export --run-id <run_id> --verify
# ⑤ 归并 20 行答卷(冻结 route_id 顺序;失败路线补显式空行)
python -m pathway_v43 batch merge --batch-root batch_dev_v1
# ⑥ 只读调用 v3 冻结评测器 --split dev 判分
python -m pathway_v43 score --predictions batch_dev_v1/merged/predictions.jsonl \
    --out-dir report --label v43 --v3-code-root ../dependingv3
```

- 批次身份(`batch_dev_v1/batch_identity.json`):代码/资产/提示词/模型/
  请求参数/预算/限流/输入清单 SHA 全部冻结;run_id 含批次短哈希与
  route_id;同批次根不同身份 → 结构化冲突。
- 20 个 worker 为独立 OS 进程,各自只写自己的 run 目录/SQLite;共享
  闸门(`V43_LLM_RATE_GATE`)跨进程管理 RPM/TPM/批次调用预算,429 有界
  退避、403/配额错误全局停止新付费请求。
- 对失败/预算耗尽/awaiting 路线仍生成显式空或部分答卷,保持 20 行且
  每个 route_id 恰一次。
- DashScope 烟测(一次真实低额度调用,与正式批次分开记录):
  `python scripts/dashscope_smoke.py --out smoke/dashscope_smoke.json`
- 对照报告:`python scripts/build_dev_report.py --batch-root ... \
  --v3-root ../dependingv3 --baseline <label>=<历史dev目录> --out-dir ...`
  然后 `python scripts/render_export_dev_report.py --report ... --out docs/EXPORT_DEV_REPORT.md`

## v4 / v4.3 对拍

```sh
python scripts/compare_asset_roots.py
# 结果:reports/asset_wiring_parity/{arm_old,arm_new,comparison}.json
```

两臂在同一解释器、同一 v3 代码提交、字节一致的 13 个 v3 运行数据文件上,
于独立子进程运行:`old` = v4 `V3Engine` + 原 v3/assets;`new` = v4.3 适配器 +
本仓 `assets/v3_reactions`。比较规范产物身份、候选数、候选顺序、source/layer、
engine_rank、共同 score 字段与 score_semantics;v4.3 新增透传的来源字段单独检查。

## 测试

```sh
cd /Volumes/CC/Enzyme_Agent/dependingv43
OMP_NUM_THREADS=1 /Users/cc/miniconda3/envs/depending43/bin/python -m pytest tests/ -v
# 只跑快速用例:
... -m "not slow"
```

共 161 项:资产接线 37 项 + 核心工作流 68 项 + 预测接线/AtomTool 56 项
(其中 2 项 slow 真实资产烟测)。slow 用例会真实加载 v3 引擎(约 25s)、
重跑双臂对拍、以子进程实测崩溃恢复与 CLI 真实烟测。
(包已 editable 安装时可直接 `python -m pytest`;未安装则加 `PYTHONPATH=src`。)

## Python 接口(LangGraph 后续调用)

```python
from pathway_v43.config import resolve_config
from pathway_v43.adapters.v3_engine import get_engine, EngineBootstrapError
from pathway_v43.adapters.analog_index import AnalogAssets, AnalogAssetError

config = resolve_config()          # 或 resolve_config(v3_code_root=..., assets_root=...)
engine = get_engine(config)        # 进程内单例;第二套资产身份会被拒绝
candidates = engine.predict("Oc1ccccc1O", case_id="case-1", top_k=10)
identity = engine.asset_identity() # 检索资产身份 + 引擎代码身份

analog = AnalogAssets(config.assets_root)   # 启用类比桥:缺任一索引即抛错
status = analog.status()                    # available / rows / sha256
```

注意:同进程内 v3 模块存在导入时路径绑定与全局模型对象,加载过一套资产身份后
再请求另一套会 fail-closed;多套身份请用隔离子进程(对拍脚本即如此实现)。

## 许可说明

本仓 assets/ 内的 EAWAG/enviPath/USPTO 衍生数据与混合检索语料未附带可独立
确认的公开再分发许可文本,仅限项目工作区内部使用;公开分发前需另行核实各
上游条款(详见 ASSETS.md)。
