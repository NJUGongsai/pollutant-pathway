# PPV1 298 曙光 HPC 部署 runbook（乌镇 wuzh02.hpccube.com）

- 日期：2026-10-12（HPC 适配工程轮交付；脚本族与本文件同目录）
- 状态：**分区/机时权限申请中**（SCNet 门户，用户办理）。未开通前
  任何 `sbatch` 都会被拒（zzeshell 侦察实锤：账号不在分区
  AllowAccounts——**该事实来自 zzeshell 侦察，乌镇节点待同款核验**）。
  开通后按本文件 §6 起逐条执行即可发首批。
- 侦察基准：
  - `docs/HPC_SHUGUANG_SURVEY_2026-10-12.md`（zzeshell 站只读侦察，
    环境事实的主要来源——Python/pip/rdkit/存储/分区形态等凡标注
    "zzeshell 侦察事实"的条目都出自它，**乌镇按"待同款核验"处理**，
    §6 netcheck 首作业在计算节点逐项实测，不假设两站环境相同）；
  - `docs/HPC_WUZHEN_SURVEY_2026-10-12.md`（乌镇首勘：当时只有
    zzeshell 钥匙被拒、零实测——**历史快照已被新钥匙事件取代**：
    2026-10-12 乌镇专用钥匙到位并验证 login03 登录成功；环境清单
    仍按 zzeshell 模板待乌镇同款核验，环境事实以 §6 netcheck 实测为准）。
- 纪律：密钥值零落盘零打印（本文件只写路径与步骤）；题卷
  questions.jsonl 含金标，只放 HPC 工作区（仓外），不入仓不进部署包；
  判分零 LLM；金标只在判分进程进入；封存 run 只读。

---

## 1. 常量与布局

| 项 | 值 |
|---|---|
| SSH 主机 | `wuzh02.hpccube.com`，端口 `65091`，用户 `aclhl3hbth` |
| 密钥（Mac 本地路径） | `/Users/cc/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt`（乌镇专用已验证：2026-10-12 login03 登录成功；与 zzeshell 那把是**不同文件**；**有效期至 2026-11-30**，到期在 SCNet 门户换新） |
| SSH 一行式 | `ssh -i /Users/cc/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt -p 65091 aclhl3hbth@wuzh02.hpccube.com` |
| HPC 工作区 `WS` | `$HOME/ppv1_hpc`（家目录；zzeshell 侦察事实：$HOME 在 9.2PB Lustre /public、可写、余量 5.4P——乌镇待 `df -h $HOME` 核验） |
| 代码根 | `$WS/dependingv43`（解包后含 src/assets/scripts/pyproject） |
| 批根 | `$WS/batch/s5b_298_hpc`（3–4 GB 量级；zzeshell 家目录余量无压力） |
| run 根 | `$WS/runs/s5b_298_hpc` |
| 凭证 env | `$WS/env/llm.env`（chmod 600，见 §5） |
| 大暂存备选 | `/work2`（zzeshell 侦察事实：9.4P 全局可写——乌镇待核验；首批用不到） |

> 所有 sbatch 脚本可用环境变量覆盖缺省（提交 shell 的 env 会随
> `--export=ALL` 进作业）：`WS / BATCH_ROOT / RUNS_ROOT / ENV_FILE /
> WORKERS / GATE_MAX_CALLS / PY / QUESTIONS / BATCH_TAG / DATA_SCOPE`。
> 分区名写在脚本头 `#SBATCH --partition=hx1hdnormal`（**zzeshell 的
> 分区名；乌镇以 `sinfo -a` 实测为准**，提交时 `sbatch --partition=<实
> 际名>` 覆盖即可）。作业日志缺省落提交 cwd 的 `ppv1_*.out`，可提交时
> `sbatch -o $WS/slurm-logs/%x-%j.out` 归拢。

## 2. 本地打包（Mac，仓根 `/Volumes/CC/Enzyme_Agent/dependingv43`）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
mkdir -p /tmp/ppv1_hpc_deploy
tar --exclude='__pycache__' --exclude='.DS_Store' --exclude='*.pyc' \
    --exclude='assets/.DS_Store' \
    -czf /tmp/ppv1_hpc_deploy/ppv1_hpc_deploy.tgz \
    src \
    assets/analog assets/v3_reactions \
    assets/MANIFEST.json assets/MANIFEST.sha256 \
    pyproject.toml \
    scripts/hpc \
    docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md
shasum -a 256 /tmp/ppv1_hpc_deploy/ppv1_hpc_deploy.tgz   # 记下校验值
```

清单口径（精确到文件）：

- `src/`：全部运行代码（orchestrator/worker/CLI/判分/引擎适配）；
- `assets/analog` + `assets/v3_reactions` + 两份 `assets/MANIFEST.*`：
  build 的类比模板/语料通道资产（`verify_repo_manifest` 按内容哈希
  fail-closed 校验，tar 传输保字节 ⇒ 校验可过；注意不能用 symlink
  拼资产——边界校验会拒）；
- `pyproject.toml`：包布局元数据；
- `scripts/hpc/`：本脚本族；
- `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`：判分
  real 门的状态行兜底（approve 记录在批根，优先）。
- **不进包**：`assets/rhea.json / METANETX.json / USPTO.json` 三大件
  （约 750 MB）——只有 `--recorded-source` 引擎通道需要，冻结 298 配方
  （`--pool-mode template`，chenyu 首批同款）不消费；日后开该通道再
  另行传输。tests/ 也不进包（冒烟可选传，见 §4 注）。
- 包体约 160 MB（压缩后更小）。

## 3. 传输与解包（Mac → HPC）

```bash
KEY=/Users/cc/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
scp -i "$KEY" -P 65091 /tmp/ppv1_hpc_deploy/ppv1_hpc_deploy.tgz \
    aclhl3hbth@wuzh02.hpccube.com:/tmp/

ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com '
  mkdir -p $HOME/ppv1_hpc && cd $HOME/ppv1_hpc &&
  tar -xzf /tmp/ppv1_hpc_deploy.tgz &&
  shasum -a 256 /tmp/ppv1_hpc_deploy.tgz &&
  ls -l dependingv43/src dependingv43/assets'
```

解包后 `$WS/dependingv43/` 内应见 `src/ assets/ scripts/hpc/
pyproject.toml docs/…`（tar 的相对路径都在包根下）。核对 shasum 与
§2 记录一致。重复部署用 `rsync -az -e "ssh -i $KEY -p 65091"` 增量
（rsync 双端都有——zzeshell 侦察事实，乌镇待核验）。

## 4. Python 与依赖（登录节点，一次性）

zzeshell 侦察事实（**乌镇待 netcheck 核验**）：系统 Python
`/usr/local/python3.12/bin/python3`（3.12.6）、pip 25.1.1、numpy/
Pillow 已在系统 site-packages、PyPI 直连可达。据此：

```bash
# 登录节点解包后直接装(计算节点共享 $HOME 的 --user site-packages)
python3 -m pip install --user rdkit
```

- **包名必须是 `rdkit`**（`rdkit-pypi` 是废弃名，会报"No matching
  distribution found"——zzeshell 实测踩过）。
- `--user` 装进 $HOME（Lustre），计算节点同挂载可见。
- 验证：`python3 -c "import rdkit; print(rdkit.__version__)"`。
- 可选（远端冒烟用）：`python3 -m pip install --user pytest`，然后把
  本仓 `tests/` 也 scp 上去，在登录节点短跑
  `PYTHONPATH=dependingv43/src python3 -m pytest tests/test_ppv1_s5b_shard.py -q`
  （12 件分片正负控，秒级；登录节点只跑秒级测试，长跑仍上 sbatch——
  zzeshell MOTD"勿在登录节点直接运行程序"，乌镇同款待核验）。
- module 体系不需要（系统 python 即够；zzeshell 侦察事实，乌镇待核验）。

## 5. 题卷与凭证放置（两件敏感输入）

### 5a. questions.jsonl（含金标——只放 HPC 工作区，不入仓）

来源 A：从 chenyu 拉（Mac 中转）：

```bash
/tmp/cy_ssh.sh "cat /usrdata/EnzymeCAGE_data/workspaces/dependingv4_v41/runs/enzymecage298/questions.jsonl" \
  | grep -v "^spawn ssh\|password:" > /tmp/questions.jsonl
# 双端 sha 比对(不假设传输无损)
/tmp/cy_ssh.sh "sha256sum /usrdata/EnzymeCAGE_data/workspaces/dependingv4_v41/runs/enzymecage298/questions.jsonl" | grep -v "^spawn ssh\|password:"
shasum -a 256 /tmp/questions.jsonl
scp -i "$KEY" -P 65091 /tmp/questions.jsonl \
    aclhl3hbth@wuzh02.hpccube.com:ppv1_hpc/questions.jsonl
ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com \
    'sha256sum $HOME/ppv1_hpc/questions.jsonl && chmod 600 $HOME/ppv1_hpc/questions.jsonl'
```

来源 B：用户直接提供文件，同样 scp 到 `$WS/questions.jsonl`。
行数应为 298（build 作业会做"注册序=题卷行数"自检）。
**注意 chenyu 通道助手前两行是 expect 噪声，必须 grep -v 过滤**。

### 5b. 凭证 env 文件（密钥值零落盘零打印）

在 HPC 登录节点手工创建（值来自 chenyu worktree 的
`.dependingv43-dashscope.env`（DashScope 按量通道）或用户直接提供；
**抄值过程人工完成，不写进任何仓内文件/脚本/日志**）：

```bash
ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com
mkdir -p ~/ppv1_hpc/env && chmod 700 ~/ppv1_hpc/env
cat > ~/ppv1_hpc/env/llm.env <<'EOF'
V43_LLM_BASE_URL=<填 base url>
V43_LLM_API_KEY=<填 key>
V43_LLM_MODEL=<填 model 名>
# 可选:V43_LLM_TIMEOUT_S / V43_LLM_MAX_HTTP_RETRIES
EOF
chmod 600 ~/ppv1_hpc/env/llm.env
```

- 运行时只取 `V43_LLM_*` 键（`batch.load_env_file`）；密钥只进
  worker 子进程内存，不落盘不打印。
- 快速自检（不打印值）：`python3 -m pathway_v43.pollutant.s5b_cli
  envcheck --env-file ~/ppv1_hpc/env/llm.env`（PYTHONPATH 指 src；
  报 configured=true 才算就位）。

## 6. 首作业 netcheck（分区开通后的第一作业，硬门）

```bash
ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com
cd ~/ppv1_hpc/dependingv43
sinfo -a                      # 乌镇实际分区名/节点/核数,记下来
WS=$HOME/ppv1_hpc sbatch --partition=<实际分区> scripts/hpc/sbatch_hpc_298_netcheck.sh
# 看结果:
squeue -u $USER; cat ppv1_netcheck_*.out
```

**判定（全过才继续）**：退出码 0 且日志含 `NETCHECK-PASS`，其中逐项：

1. python 版本与路径（3.12.x）；
2. `rdkit` 导入 + 版本；
3. `pathway_v43` 导入（部署布局正确）；
4. 家目录可写（df 输出留档）；
5. **flock 互斥语义成立**（父持锁→子必拒；父放→子得。整条管线的
   qid 域协调锁/闸门锁/run 级 driver.lock 全依赖它）；
6. **计算节点到 dashscope 的端到端路由通**（不带 key 的 POST 收到
   API 层 JSON 应答即链路通——侦察的遗留风险项，本作业闭环）。

任一项不过 ⇒ 修（换分区/重装 rdkit/网络方案）再重投；**不过不发
第一真批**。注：计算节点出口若不通，备选方案是"登录节点跑本地反代/
队列进程，计算节点内网回连"（zzeshell 侦察 §7 提示登录/计算节点同
10.x 内网互通——乌镇待核验），属新工程，另行立轮。

## 7. build 作业（语料检索+编译，单作业）

```bash
cd ~/ppv1_hpc/dependingv43
WS=$HOME/ppv1_hpc sbatch --partition=<实际分区> scripts/hpc/sbatch_hpc_298_build.sh
# 或带依赖留档: BUILD_ID=$(sbatch --parsable ...同上...)
cat ppv1_build_*.out   # 应见 BUILD-OK: n_questions=298 … 与 BUILD-PASS
```

产物：`$WS/batch/s5b_298_hpc/`（batch_manifest.json 冻结注册序 +
run_inputs + 参考图；批身份/代码/资产哈希入账）。作业内自检
"注册序数=题卷行数"。

## 8. 发车三步（用户裁定步骤，登录节点秒级 CLI）

按仓纪律，approve/budget/price 是**用户拍板项**（新批新预注册档的
档位/授权措辞、当日价格、帽值均由用户定；下面命令只是落盘点）：

```bash
cd ~/ppv1_hpc/dependingv43 && export PYTHONPATH=$PWD/src
B=$HOME/ppv1_hpc/batch/s5b_298_hpc

# ① approve(发车硬门:授权记录,用户填当日授权标记)
python3 -B -m pathway_v43.pollutant.s5b_cli approve \
  --batch-root $B --preregistration-id prereg-s5b-hpc-2026-10-XX \
  --user-authorization launch-authorized-2026-10-XX

# ② budget(real 批硬门:60 CNY 帽默认;当日价用户定,示例 0.8/2.8 元/Mtok)
python3 -B -m pathway_v43.pollutant.s5b_cli budget \
  --batch-root $B --cap-cny 60 \
  --input-per-mtok 0.8 --output-per-mtok 2.8 \
  --input-tokens-bound 30000 --max-output-tokens 8192

# ③ price 由 ② 同步写(price_snapshot.json 单一价格来源),单独改价才用:
#    python3 -B -m pathway_v43.pollutant.s5b_cli price --batch-root $B \
#      --input-per-mtok 0.8 --output-per-mtok 2.8
```

- 金额守卫语义：发送前原子预留、余额不足先于传输拒、失败/未知 usage
  不释放、**不自动升帽**（帽到顶要加须用户落新值——改值会被拒，须
  新批根或用户重议）。
- 预注册纪律注记：HPC 新批根=新批身份；判分 real 门的批准走 ① 的
  批根记录优先、冻结稿状态行兜底（包里带了 prereg 文档）。冻结判据/
  口径零改动（本轮不碰 scorer）。

## 9. 分片发车（多作业分片核心步骤）

```bash
cd ~/ppv1_hpc/dependingv43
# 同节点约束(首批建议):sinfo -a -N -o '%N %P %C %m' 挑一个空闲节点
NODE=<挑好的节点名>

BUILD_ID=$(sbatch --parsable --partition=<实际分区> \
  scripts/hpc/sbatch_hpc_298_build.sh)

SHARD_ID=$(sbatch --parsable --partition=<实际分区> --nodelist=$NODE \
  --dependency=afterok:$BUILD_ID \
  --array=1-5 \
  scripts/hpc/sbatch_hpc_298_shard.sh)
# 分片数 5 只是建议:每分片缺省 20 workers + 4 核余量,
# 分片数×24 ≤ 单节点核数(zzeshell 计算节点 128 核——乌镇以 sinfo 实测为准)。
```

要点（脚本头注释同口径）：

- 数组作业 `--array=1-5`：每个数组元素=一个分片，白名单按冻结注册
  序连续切片（尾分片吃余量），`SHARD_INDEX/SHARD_TOTAL` 自动取
  `SLURM_ARRAY_TASK_ID/COUNT`；
- **所有分片同参**（workers=20、gate_max_calls=1490 等）：参数进
  orchestration.json 冻结副本，不同参后到者结构化拒（防误配）；
- 批级闸门跨分片共享：RPM/TPM/max_calls(1490=298×1×5 次尝试上
  限)/在途 40/金额帽全部落批根 gate 状态文件，flock 串行——分片只
  分摊 CPU/墙钟，不放大 API 配额；
- **首批建议 `--nodelist` 同节点**：跨节点时死亡占位回收按本机 pid
  判死会误回收他节点在途 worker（在途帽放松、金额侧保守不漏），且
  flock 跨节点语义未实测——首批先同节点，跨节点需求立新轮验证；
- 失败重启：分片红 ⇒ 看该分片 `ppv1_shard_<jobid>_<idx>.out` 与
  批根 case 文件，修因后**重投同参数**——已完成 qid SKIP（断点续跑），
  同 qid 双协调者会被 qid 域锁结构化拒（fail-fast 防重复跑题）。

## 10. 跑批监控

```bash
squeue -u $USER                          # 作业态
ls $HOME/ppv1_hpc/batch/s5b_298_hpc/cases | wc -l   # 终态题数(权威计数,到 298 收口)
cd ~/ppv1_hpc/dependingv43 && PYTHONPATH=$PWD/src \
  python3 -B -m pathway_v43.pollutant.s5b_cli summary \
    --batch-root $HOME/ppv1_hpc/batch/s5b_298_hpc   # 全批视角汇总
# 金额帽状态(只读):
python3 -c "import json;print(json.load(open('$HOME/ppv1_hpc/batch/s5b_298_hpc/gate/gate.json'))['cost'])"
```

- `progress.json`/`batch_report.json` 是**最后写盘分片的视角**
  （分片各自覆盖写，原子落盘不互踩）——全批视角以 `summary`/cases
  计数为准；
- 429 全局冷却是自动的（封顶 60s）；`gate.json` 的 `stopped` 非空
  = 401/403/402 付费类错误 ⇒ 停新发，查凭证（§5b）后重投续跑；
- 金额帽到顶：`cost.send_rejections` 增长、新发送被拒——**不自动升
  帽**，用户裁定。

## 11. score 作业（全分片终态后单次判分）

```bash
SCORE_ID=$(sbatch --parsable --partition=<实际分区> \
  --dependency=afterok:$SHARD_ID \
  scripts/hpc/sbatch_hpc_298_score.sh)
cat ppv1_score_*.out
```

- `--dependency=afterok:<数组作业ID>` = 等全部数组元素成功；
- 作业内还有第二道门：注册序全 qid 终态检查（有 pending/坏 case ⇒
  拒发判分，不把未跑完的题当未命中）；
- 产物：`$B/metrics.json` + `report.md/report_plain.md`（判分零
  LLM；数字带 298 题域标签，对外引用沿用"298=RHEA 通用酶学题域"
  口径，不与 dev 题域互推）。

## 12. 结果回收与对账

```bash
# 判分与批报告拉回 Mac(批根 ~3-4GB,按需全拉或只拉汇总件):
KEY=/Users/cc/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
mkdir -p ~/ppv1_hpc_results_298
scp -i "$KEY" -P 65091 \
  aclhl3hbth@wuzh02.hpccube.com:ppv1_hpc/batch/s5b_298_hpc/metrics.json \
  aclhl3hbth@wuzh02.hpccube.com:ppv1_hpc/batch/s5b_298_hpc/report.md \
  aclhl3hbth@wuzh02.hpccube.com:ppv1_hpc/batch/s5b_298_hpc/batch_report.json \
  ~/ppv1_hpc_results_298/
```

- 封存：跑完判分的批根/run 根按仓纪律**只读封存**（不回写、不复跑
  覆盖；重考须新批根）；
- 费用对账：`metrics/summary` 的 known-usage 小计（cost_known_cny）
  vs 闸门 `cost` 块 committed（settled+unsettled+reserved）；unsettled
  是"无 usage/部分缺轴的保守保留"（可能已付），以账单回填为准；
- 判分数字引用纪律：只引冻结判分链输出（metrics.json），不自算口径。

## 13. 故障处置速查

| 症状 | 处置 |
|---|---|
| sbatch 报 Invalid account/partition | 分区权限未生效或分区名不对：门户开通确认 + `sinfo -a` 实名 + `sbatch --partition=` 覆盖 |
| netcheck 不过 | 按 §6 逐项修；dashscope 不通走"登录节点代理"新轮；**不绕硬门** |
| 分片作业红 | 看分片日志 + 批根 case；断点续跑=同参重投本脚本（qid 域锁保证不重复跑题） |
| `s5b_coordinator_active` | 同 qid 已有活动协调者（重复投了重叠白名单）：确认无误后等前一个退出/杀掉再投；不相交白名单不受此限 |
| `s5b_orchestration_conflict` | 分片参数不一致（改 workers/gate 后没统一）：全部分片同参重投；改冻结参数须新批根 |
| `s5b_budget_guard_missing` | §8 ② 未做：real 批先落 budget_guard.json |
| gate `stopped`（401/403/402） | 凭证失效/额度：修 §5b env 文件，同参重投续跑 |
| 金额帽拒发（send_rejections 增） | 不自动升帽：用户裁定后新值落盘（改值拒 ⇒ 新批根重议） |
| 计算节点外网断（跑批中 429 全失败/超时） | 停批（依赖串会红），转"登录节点代理"方案（新轮） |

## 14. 红线自查（本 runbook 自带）

- 分区未开通 ⇒ 不提交任何作业（本文件全为就绪工程，执行从 §6 起）；
- 密钥值零落盘：§5b 是唯一放置点（HPC 仓外 env 文件，600 权限），
  本文件/脚本/部署包内无任何密钥片段；
- 金标承载物（questions.jsonl）只在 HPC 工作区与 gitignored 中转位，
  不入仓不进部署 tar；
- 判分零 LLM、金标只进判分进程；冻结判据/scorer/口径零改动；
- 封存 run 只读；对外数字带题域标签（298 ≠ dev）。
