# pollutant_pathway_v1 S5b 运行时实施批交付书(真模型接线/题卷构建器/40 路编排/判分与报告)

日期:2026-10-09。实施代理:S5b 紧急实施批唯一实施会话。仓库
`/Volumes/CC/Enzyme_Agent/dependingv43`,分支 v4.3,基线 `b636f43`
(S5b 启动批回修——evaluation-5 L01 守卫/L02 口径订正;本批改动在其
之上,文件面与回修代理严格不相交:回修只碰 evaluation.py/profile.py
与 7 个存量测试字面量,本批只新增 pollutant 新模块 + runflow.py 最小
钩子 + .gitignore 一行 + 本交付书)。

**定位**:S5b 真实模型集成的**运行时四件套**落地——真实模型客户端、
298 题卷构建器、40 路编排器、判分与双口径报告。**本批不执行任何真实
模型调用、不花钱、不启动正式 298 评测**(真调用由主会话按 §3 runbook
在 Chenyu 部署后发车)。判分零 LLM 不变;金标内容零入仓。

## 1. 四块交付映射

| 块 | 文件(全部新建,除注明) | 契约 | 关键事实 |
|---|---|---|---|
| 1 真模型客户端 | `src/pathway_v43/pollutant/real_model.py` | s5b-real-model-1 | 复用 legacy `OpenAICompatibleClient`(只读 import,不重写):DashScope OpenAI 兼容 /chat/completions、429 有界退避、401/403/402 付费停止、`Idempotency-Key`、usage 归一、FileRateGate 批级闸门;凭证只从 env(主名 `V43_LLM_BASE_URL/API_KEY/MODEL`,v41 老名 `LLM_API_BASE_URL/LLM_API_KEY/LLM_MODEL` 只读回退;部署定案 2026-10-09);缺省 timeout 3600s / HTTP 重试 4;逐调用账本 `<run_dir>/s5b_real_calls.jsonl`(issued/responded/failed/orphan + usage,零密钥零凭证);`ScriptedRealModelAdapter` 为同接口测试/冒烟桩(不冒充在线模型验证) |
| 2 题卷构建器 | `src/pathway_v43/pollutant/s5b_builder.py` | s5b-builder-1 | questions.jsonl → 每题一条 PPV1 run 输入(根底物=substrate、无人工条件注入、池=底物侧确定性检索零金标消费)+ 298 张 G1 参考图(预注册 §2/§3 全规则:qid 进 source_refs、全 principal、partial+固定披露、net_reaction 无守恒声明、reference_only、known_gaps 仅披露、S1 一题一组、related/unknown 永不 independent)+ split 清单 + 批清单(冻结注册序=行序);输出根守卫 `check_output_root`:仓内只许 gitignored `reports/ppv1_s5b/`,仓外合法,其余拒(零写入) |
| 3 40 路编排器 | `src/pathway_v43/pollutant/s5b_orchestrator.py` + `s5b_worker.py` + `s5b_cli.py` | s5b-orchestrator-1 / s5b-worker-1 | 逐 qid 一进程 worker(`OMP_NUM_THREADS=1`;最多 40 并发);批级 FileRateGate(RPM/TPM 滑窗、429 冷却、付费停止、max_calls 预算、`max_in_flight=40` + `peak_in_flight` 原子记账);断点续跑(终态 case SKIP;run 存在 ⇒ resume 幂等);发车参数冻结(同批根改参 ⇒ 拒);逐题 case 落盘 stop_reason/endpoint/export_digest/调用/usage;失败题失败补位留分母;CLI:`build/approve/price/run/score/envcheck/summary` |
| 4 判分与报告 | `src/pathway_v43/pollutant/s5b_scoring.py` | s5b-scoring-1 | 封存答卷后零 LLM:逐 qid `evaluate_scientific`(real 门按当前签名接线:批根 `preregistration_approval.json` / 显式参数 / 冻结稿状态行三通道,`preregistration_confirmed` 兼容非 pending 即已批准,归一为评测器契约的 "approved");主口径 hit@1/3/5(参考边 matched_strict;候选事件按 `(created_at, event_id)` 提交时序;分母固定=注册 qid 全集);老口径敏感性表(v43-ec298-scorer-2 官方整串 any-one 复刻:`exam_v2.first_hit_rank` 只读复用,候选=报告投影产物展平成串,`report_rank=None` 宽度外不进序列——L02 订正口径,`caliber_policy` 字段可调);多组分 any-of 第三表;失败/unknown/预算漏展开分桶单列;CI 三档(S1 bootstrap/S2 按底物/Wilson,固定种子可重放);报告技术版+大白话版(数字带题域标签 298;不外推 dev);metrics 零金标 SMILES 取值 |

**runflow.py 最小接线钩子(唯一小改文件)**:`_Driver.__init__` 增
`model=None` 参数;`_model_proposals` 的"取响应"一步与格式反馈轮
重试在注入对象实现 `ppv1_real_fetch` 时改走真实取响应
(登记→sent→complete→responded/failed→同一确定性解析器
`parse_model_proposals`);登记 `provider_kind` 沿 plan(real 占
`max_real_model_requests` 额度、network=1;scripted 桩网络 0 不占
真实额度);无对象/无方法 ⇒ 旧行为逐字节不变(存量 1133 全量绿证
明)。崩溃恢复:B2 悬空请求记 failed(占额)+ 显式新 request
(`retry_of` 记来源,不默发第二请求);B1 续跑经公共 resume。

`.gitignore` 新增一行:`reports/ppv1_s5b/`(金标承载物根;预注册
§2 转换中间产物纪律由本批登记)。

## 2. 测试与验证数字(全部实跑,零网络)

- **新测试 `tests/test_ppv1_s5b_runtime.py`:19 通过 / 0 失败**:
  客户端 8(env 缺失 fail-closed/v41 回退/身份块/载荷形状/桩全链/
  传输失败记账/额度 0 阻断/钩子旧行为回归)+ 构建器 3(合成端到端/
  输出根守卫/题卷校验)+ 编排器 3(3 题 2 路子进程 + resume SKIP +
  失败题留分母 + qid/参数拒)+ 判分 5(合成端到端双口径/real 门三态/
  预注册 helper/通过线语义/合成 qid 严格配对);
- **全量 `pytest tests/`:1786 通过 / 0 失败 / 0 跳过**(约 9 分钟,
  含回修批 b636f43 的 `test_ppv1_s5b_rework_l01.py` 7 条 + 启动批
  `test_ppv1_s5b_pairing.py` 14 条;PPV1 存量 1133 无回归);
- **合成端到端演示(scripted 桩,3 题夹具)**:构建 → 2 路编排
  (每题 1 次模型调用、model_requests scripted/responded/network=0、
  调用账本零密钥)→ resume(3 题全 SKIP,case 文件不改写)→ 判分
  (denominator=3;主口径 hit@3=hit@5=2,老口径 hit@3=2;分桶
  matched_strict=2 / unmatched_required_node_uncovered=1;
  real 档配对全 `qid_strict`;状态 `pending_user_teacher_decision`;
  report.md/report_plain.md/metrics.json 产出;metrics 零金标取值)。
  合成分子(CCO/CC=O/CC(O)C/CCOCC)经与真实 298 金标集合只读零重叠
  核验后选用(核验不落盘)。
- **未验证(如实声明)**:真实网络调用、真实 DashScope 响应解析率、
  真实题卷(298)构建、40 路真实并发峰值、真实费用记账、Chenyu 远端
  全链——全部留给主会话按 §3 runbook 发车后验证。

## 3. Chenyu 部署 runbook(主会话执行;部署环境定案 2026-10-09)

### 3.0 前置硬门(发车前)

1. 用户最终确认读:冻结稿状态行已是
   `preregistration_confirmed`(2026-10-09 用户确认;本批 score 侧
   按状态行兜底兼容);
2. Chenyu 通道当日可用(短连接);
3. 三锚 SHA 当日实核(a3cb7955/9f5955d4/cb5996c9;远端权威
   `/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/
   questions.jsonl`);
4. 发车当日 RPM/TPM/价格快照刷新(§3.3 price 步骤)。

### 3.1 部署(git bundle + scp + worktree;远端拉不了私库)

```bash
# 本地(仓根)
git bundle create /tmp/s5b.bundle v4.3        # 孤儿根 53 提交全量,约 125MB
scp /tmp/s5b.bundle <chenyu>:/usrdata/EnzymeCAGE_data/workspaces/s5b.bundle
# 远端短连接(root 与仓属主不一致 ⇒ safe.directory 注入,预置代理已验证)
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory \
       GIT_CONFIG_VALUE_0=/usrdata/EnzymeCAGE_data/workspaces/dependingv4
cd /usrdata/EnzymeCAGE_data/workspaces/dependingv4
git fetch /usrdata/EnzymeCAGE_data/workspaces/s5b.bundle v4.3:refs/heads/v4.3_s5b
git worktree add ../s5b_298_20261009 v4.3_s5b
```

注:bundle 应基于包含本批提交后的 v4.3(先完成 §4 本地提交再打
bundle);本批提交哈希见 §5。

### 3.2 环境与凭证(dev venv + 受限专用 env 文件)

```bash
PY=/usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev/.venv/bin/python
# py3.12.3 + rdkit 2026.3.6 + v4.3 全套(Phase-D 批次同款)
cd /usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009
export PYTHONPATH=$PWD/src
# 凭证(键名已核:V43_LLM_BASE_URL / V43_LLM_API_KEY / V43_LLM_MODEL;
# 备选回退 v41 老名;密钥不落日志不落盘)
set -a; . /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env; set +a
# checkenv(资产/引擎自检;再跑本批凭证存在性检查,密钥值不打印)
$PY -B -m pathway_v43 checkenv --analog-rows
$PY -B -m pathway_v43.pollutant.s5b_cli envcheck
```

### 3.3 批根准备(run 根沿 ec298_pd_retest_pre 先例 configs/ + local/)

```bash
B=/usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009/local/s5b_298
R=$B/runs
Q=/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl
$PY -B -m pathway_v43.pollutant.s5b_cli build \
    --questions $Q --batch-root $B --batch-tag s5b-298 \
    --pool-mode template            # 模板池;冒烟后可换 --pool-mode empty 对照
# 预注册批准记录(冻结稿已 confirmed;显式落记录=发车留痕)
$PY -B -m pathway_v43.pollutant.s5b_cli approve \
    --batch-root $B --user-authorization launch-authorized-2026-10-09
# 当日价格快照(示例值;以发车当日刷新值为准)
$PY -B -m pathway_v43.pollutant.s5b_cli price \
    --batch-root $B --input-per-mtok 0.8 --output-per-mtok 2.8
```

构建输出(参考图/run 输入/清单,含金标承载物)全在远端批根(仓
外路径,合法);**不得拷回仓内非 gitignored 路径**。

### 3.4 段 0 烟测(非 298 合成夹具,≤10 次调用,独立烟测账)

```bash
# 合成题卷(自带合成夹具;零 298 题面)走完整 real 链:登记→发送→
# usage 记账→解析→导出;验收:网络计数=1/请求、usage 回填、账本零密钥
$PY -B - <<'EOF'
import json, os
from pathlib import Path
import sys; sys.path.insert(0, "src")
from pathway_v43.config import resolve_config
from pathway_v43.pollutant.s5b_builder import build_question_batch
from pathway_v43.pollutant.real_model import RealModelAdapter
from pathway_v43.pollutant.runflow import start_ppv1_run
B = Path("local/s5b_smoke0"); B.mkdir(parents=True, exist_ok=True)
q = [{"qid": "SMOKE-Q001", "substrate_smiles": "CCO",   # 与 298 集零重叠
      "products_smiles": ["CC=O"]}]
(B/"questions.jsonl").write_text(json.dumps(q[0])+"\n")
build_question_batch(B/"questions.jsonl", B/"batch", batch_tag="smoke0",
                     pool_provider=lambda s: [], provider_kind="real")
ri = json.loads((B/"batch/run_inputs/SMOKE-Q001.json").read_text())
out = start_ppv1_run(config=resolve_config(), runs_root=B/"runs",
    run_id=ri["run_id"], smiles=ri["substrate_smiles"], plan=ri["plan"],
    model=RealModelAdapter.from_env(
        call_account_path=B/"runs"/ri["run_id"]/"s5b_real_calls.jsonl"),
    profile_policy={"search_limits": {"max_real_model_requests": 3},
                    "format_feedback_policy": {"max_format_feedback_rounds": 2}})
print(json.dumps({"stop": out["stop_reason"],
                  "export": out["native_export"]["export_digest"][:16]}))
EOF
cat $B/runs/*/s5b_real_calls.jsonl | head -5   # 核 usage/零密钥
```

### 3.5 冒烟段 1/2 并入正式批(前 10 题串行核对 → 一键续跑)

```bash
# 段 1:冻结注册序前 10 题串行(计入正式批,同批根同身份续跑;
# 不得借 298 看结果后调配置——预注册纪律)
$PY -B -m pathway_v43.pollutant.s5b_cli run \
    --batch-root $B --runs-root $R --workers 1 --limit 10 \
    --gate-max-calls 894 --python-bin $PY
# 核对前 10 题:run_identity 的 prediction 块(prompt 版本/model_id/
# request_params/timeout)、case 文件的 model_calls/usage、
# s5b_real_calls.jsonl 的 usage 与错误率;异常 ⇒ 停,回报,不硬闯
$PY -B -m pathway_v43.pollutant.s5b_cli summary --batch-root $B
# 段 2+全量:一键续跑(前 10 题 SKIP;40 在途;断点续跑随时可中断重启)
nohup $PY -B -m pathway_v43.pollutant.s5b_cli run \
    --batch-root $B --runs-root $R --workers 40 --gate-max-calls 894 \
    --python-bin $PY > $B/nohup_run.log 2>&1 &
```

### 3.6 进度轮询(短连接;不看结果只看进度)

```bash
$PY -B -m pathway_v43.pollutant.s5b_cli summary --batch-root $B
# 或直接 cat $B/progress.json(总数/终态/在途/待跑/峰值);
# 闸门状态 cat $B/gate/gate.json(total_requests/429/peak_in_flight/stopped)
```

### 3.7 判分与回传(封存答卷后;金标只在此时进判分进程)

```bash
$PY -B -m pathway_v43.pollutant.s5b_cli score \
    --batch-root $B --runs-root $R            # data_scope=real(缺省)
# 产物:$B/metrics.json、$B/report.md、$B/report_plain.md
# 回传(短连接):report.md / report_plain.md / metrics.json /
# batch_report.json / progress.json(判分明细与参考图含金标信息,
# 留远端批根,不回传仓内;回传件只进 gitignored 根或 docs 摘要)
```

## 4. 诚实风险清单(首次真模型集成的未知风险)

1. **首次真模型集成**:PPV1 全链此前从未接过真模型——proposals
   协议的真实响应解析率(JSON 形状率)、格式反馈轮触发率、单题墙钟、
   单题真实调用数全部未实测;段 0/段 1 冒烟是唯一实证来源,若解析率
   异常低,如实回报,不硬闯全量;
2. **模板池派生正确性未经真实题卷验证**:`default_pool_provider`
   的模板→spec 派生(键差→编辑/对齐/中心)只有合成夹具正控;真实
   语料上派生 spec 可能大量在 audit/admission 拒(如实计未命中);
   段 1 核对池命中率后可切换 `--pool-mode empty`(模型 novel 提案)
   对照——**切换=配置变化,预注册纪律下属冒烟标定范畴(段 1/2 允许
   定型,全量前冻结),不属借结果改配置**;
3. **老口径敏感性表的候选序列语义**按冻结稿 §5.4 + L02 订正稿实现
   (`report_rank=None` 不进序列;`caliber_policy` 留可调);若回修
   代理订正稿后续再改字段,按新稿调 policy,不改判分内核;
4. **预注册 P1 数值未冻结**:每 run `max_real_model_requests=5`、
   批级 `gate_max_calls`(缺省 600,runbook 示例 894)是候选值,冒烟
   后须按实测定型补冻结;40 在途目标未经实测(Phase-D 实测峰值 33/32
   作参照,429 冷却自动降并发,如实记 `peak_in_flight`);
5. **评审后置声明**:本批未执行 mimo 化学评审三触发点之 3(出题后
   结果复核)——跑分后由用户按 AGENTS 送 r27/后续请求;评审独立性
   不做背书;
6. worker 超时/进程死亡走"失败补位留分母 + resume 续跑"路径,无
   语义级自动重试(预注册 #18 拒绝"重试后再算";传输层 429 有界
   重试除外);
7. CLI envcheck/approve/price 的输出与批根产物均不含密钥;真实
   questions.jsonl 只在远端被读取,任何仓内路径写入受
   `check_output_root` 守卫。

## 5. 提交与证据

- 本批提交(v4.3 本地,不 push,显式路径):`real_model.py` /
  `s5b_builder.py` / `s5b_orchestrator.py` / `s5b_worker.py` /
  `s5b_scoring.py` / `s5b_cli.py`(六个新模块)+
  `runflow.py`(最小钩子)+ `tests/test_ppv1_s5b_runtime.py` +
  `.gitignore`(一行)+ 本交付书;提交哈希见 git log
  (标题含 "ppv1 S5b runtime");
- 不触碰:evaluation.py / profile.py / path_context.py / production.py /
  search.py / store.py / audit.py / chemstate.py / queue.py / native_*.py /
  v3_projection.py / exam.py / batch.py / exam_v2.py /
  adapters/llm_client.py(全部只读复用);冻结判据正文/FREEZE_RECORD/
  path_context 逐字节不动;评审侧未跟踪文件零触碰;主会话对冻结稿
  状态行的未提交修改不并入本批提交;
- 金标零入仓:仓内新增文件零金标取值(合成分子经零重叠核验;
  参考图/run 输入只落 gitignored 或仓外根);判分产物 metrics 零
  金标 SMILES;
- 测试命令:`~/miniconda3/envs/depending43/bin/python -B -m pytest
  tests/ -q -p no:cacheprovider`(1786 passed)。
