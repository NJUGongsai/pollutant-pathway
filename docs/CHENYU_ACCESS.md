# CHENYU_ACCESS — chenyu 接入与 dev/298 测试路径(常青)

> **维护规则**:路径/环境变了就改对应节。最后核验:**2026-09-24**(全路径当日在 chenyu 实核)。
> **凭证纪律**:本文件**永不包含**密码/令牌/API key。链接凭证在本地 dependingv4 `.env.chenyu`(gitignored)与 /tmp 助手脚本里;丢了找主窗口/用户按原样重建。任务书引用方式:「通道与路径见 docs/CHENYU_ACCESS.md」。
> 总入口=docs/REPO_GUIDE.md;298 考试原始任务书=evaluation/enzymecage_v6/TASK_298.md。

---

## 1. 链接方式

- **SSH**:`/tmp/cy_ssh.sh "<远端命令>"`(本地执行;expect 封装,单命令 300s 硬超时)。脚本含凭证,**不入仓**;/tmp 易失,丢失时找主窗口重建(配方凭证来自 `.env.chenyu` 的 CHENYU_HOST/PORT/USER/PASS)。
- **文件上行**:`/tmp/cy_scp.sh <本地文件> <远端路径>`(同款封装)。
- **stdout 噪声(必踩)**:两个助手的前两行是 expect 噪声(`spawn ssh…`+密码提示行),拉数据必须 `| grep -v "^spawn ssh\|password:"`。
- **长任务纪律**:chenyu 上 `nohup … > 日志 2>&1 &` 落盘 + 短连接轮询(直连长命令会被代理掐);hybrid 进程 stdout 块缓冲,**日志冻结≠进度冻结,进度看 case 目录计数**;单一协调者,多作业共存时不碰别人目录。
- **引擎/评测一律 `OMP_NUM_THREADS=1`**(96 核共享机线程超额反而慢,且避开 libomp×fork 死锁)。

## 2. 布局速查(根 = `/usrdata/EnzymeCAGE_data/workspaces/`)

| 目录 | 内容 | 关键路径 |
|---|---|---|
| `dependingv3` | 引擎+资产+基准(v3 部署位,冻结) | `evaluation/pathway_benchmark/{gold_routes.jsonl, split_manifest.json, eval_pathway_benchmark.py}`;`assets/corpus_env/`(引擎语料);`training/mpnn/gnn_model_v3_repro/model.pt` |
| `dependingv4`(主仓) | main 仓 + **判分用 venv**(py3.12,rdkit 2026.03.6) | `.venv/bin/python`;`.env` = **token-plan 端点**(26 模型:glm/kimi-k2 系/deepseek 系,无 kimi-k3) |
| `dependingv4_v41` | feat/v41-pipeline @ fa58596 = 298 考试代码 | **`runs/exam298_agent|engine/`(run-once 只读!)**、`runs/exam298_agent/per_question_scoring.jsonl`(判分件)、`runs/enzymecage298/questions.jsonl`(298 题金标)、`runs/298chunks/`(40 分片);`.env` = **DashScope 按量**(261 模型,`deepseek-v4.1-flash` 与 `kimi-k3` 都在) |
| `dependingv4_v42fix` | feat/v42-fix worktree(v4.2 修复轮) | `runs/dev_hybrid_v42fix/`(S3 处理臂);`.env` = DashScope 按量 |

参考目录(v41):`runs/dev_hybrid_v41/` = S3 对照臂(v4.1 hybrid)。

## 3. dev 测试路径与流程(可反复跑;LLM 花钱项须用户批)

- **金标与 split**:`dependingv3/evaluation/pathway_benchmark/`——120 条路线,`split_manifest.json` 切 **dev 20**(pb_0002…,207 金标步)/ **eval 100**(865 步);判分器 = 同目录 `eval_pathway_benchmark.py`(cn 主口径,零 LLM)。
- **发车**(标准流程,详见 §5 新 worktree 三步):
  ```bash
  cd <你的worktree> && set -a && . ./.env && set +a   # DEPENDING_V3_ROOT 已指 chenyu v3 位
  OMP_NUM_THREADS=1 python -m pathway_agent checkenv
  OMP_NUM_THREADS=1 nohup python -m pathway_agent batch --split dev --mode hybrid \
      --representation molecode --config configs/pathway_agent.yaml --tag <任务名> \
      > /tmp/<任务名>.log 2>&1 &
  ```
  断点续跑:同命令重人,已完成的 qid 自动 SKIP。**--tag 必须用任务专名**,产物在 `runs/<tag>*/`。
- **判分**:单臂数字用 v3 evaluator;双臂对照+不劣化门用 `scripts/s3_dev_gate.py`(拷到你的 worktree 跑,判分零 LLM)。已有双臂参考:`dev_hybrid_v41`(对照)/`dev_hybrid_v42fix`(处理)。
- **红线**:eval split 的 run-once 产物只读;dev 可重跑但 tag 分开;LLM 消融发车前过硬闸门(用户明确指令)。

## 4. 298 测试路径与流程(**按 v4.2 重考写;未拍板前禁跑**)

### 4.1 现有冻结产物(任何 agent 只读)
- 考试产物:`dependingv4_v41/runs/exam298_agent/`(298 case,每 case 含 decision_log/steps/state/run_identity)+ `runs/exam298_engine/`;
- 判分件:`runs/exam298_agent/per_question_scoring.jsonl`(298 行:`qid/category/vacuum/agent_rank/baseline_rank`;rank=金标有机产物在有序 predicted_products 中的 1-based 名次,null=不在);
- 题目金标:`runs/enzymecage298/questions.jsonl`(qid/substrate_smiles/products_smiles);题卷 CSV SHA256=`a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a`。

### 4.2 重考前置(硬闸门,缺一不发)
1. **用户拍板** v4.2 重考 + **新预注册档**(v4.1 首跑 39.6% 留档不覆盖,新档记录配置/预期/回退规则);
2. **单步预算钦定**:max_depth=1、max_expands=1(首跑按多步超支跑是已记录事故,重考必须按 TASK_298 §S4 原文);
3. 新 worktree + **新 run 目录**(绝不写旧目录);跑前重算题卷 SHA 对 4.1 锚。

### 4.3 重考流程(按 TASK_298 §7 编制)
① 引擎基线臂先行(纯 CPU,40 分片并行,`runs/298chunks/chunk_XX.csv` 已备);② agent 臂:前 10 题冒烟核对 run_identity(config/prompt hash)→ 一键续跑余量(nohup 分片+断点续跑);③ 判分(确定性代码,零 LLM)→ per-question jsonl;④ 报告(三档切片:池顶10/排序余量/真空 39 + 三条披露)。LLM 端点用 worktree `.env`(DashScope 按量)。

## 5. 新 worktree 标准三步(Q3 钦定:新任务新 worktree,禁互踩)

```bash
# ① 本地打包(git 历史已推到 org 仓,也可从 org 仓 clone/fetch)
git bundle create /tmp/x.bundle <branch> --not <双方共有的基线hash>
/tmp/cy_scp.sh /tmp/x.bundle /tmp/x.bundle
# ② chenyu 主仓收包建 worktree
ssh: cd /usrdata/EnzymeCAGE_data/workspaces/dependingv4 \
  && git fetch /tmp/x.bundle <branch>:refs/heads/<branch> \
  && git worktree add ../<新目录名> <branch>
# ③ 环境:.env 从 dependingv4_v41/.env 拷贝(含 LLM 凭证,gitignored,不外传不打印)→ checkenv 全绿才算就位
```

## 6. 坑清单(全部实踩)

- expect 助手 stdout 前两行是噪声——拉数据必过滤;
- hybrid stdout 块缓冲:日志不动≠进程死了,看 case 目录计数;
- macOS libomp×fork 死锁 + chenyu 96 核线程超额:`OMP_NUM_THREADS=1` 全程带;
- 判分器 qid 含下划线致 rsplit 误切→**「整齐的全零」症状=先查解析层再看数字**;
- rdkit/判分只信 `dependingv4/.venv`(py3.12);各 worktree 自带 .venv 不一定有引擎依赖;
- /tmp 易失:助手脚本/bundle/payload 丢了就重建;
- `kimi-k3` 不接受 temperature 参数(API 400:`Parameter 'temperature' is not supported`);
- 细粒度 PAT 访问本组织私有仓会 403(`Write access to repository not granted`),经典 `ghp_` 令牌可用;
- git 拉分支到 worktree:`git fetch <bundle> <branch>:refs/heads/<branch>`(对未检出分支可用 refspec;已检出的分支会被拒)。

## 7. 文档关系

总入口=REPO_GUIDE;考试原始任务书=evaluation/enzymecage_v6/TASK_298.md(§7 晨羽执行附录=编制与纪律原文);修复轮=TASK_V42_FIX.md;本文件取代各任务书里散落的通道段落(旧任务书里的路径若与本文件冲突,以本文件+当日实核为准)。
