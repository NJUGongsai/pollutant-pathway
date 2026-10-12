# PPV1 HPC 分片适配轮交付书（s5b-orchestrator-3 + scripts/hpc 部署族）

- 日期：2026-10-12（实施完成日；四组回归与 G01 证据当日全部落盘）
- 任务：298 全量测试迁曙光 HPC（乌镇 wuzh02.hpccube.com）跑 sbatch 多
  作业分片——本轮只做**本地工程与脚本**（账号分区权限申请中，不提交
  任何 sbatch/ssh 作业），分区开通后按 `scripts/hpc/deploy.md` 逐条
  执行即可发首批。
- 基线：开工实取 HEAD `8da11cb7`；实施期间兄弟轮 F3（受控词表同源 CI）
  落地为 commit `dbc71ca5`（改动 real_model.py、新增 controlled_vocab.py
  与其 17 件 CI 测试）——**本交付的实际父提交为 `dbc71ca5`**，本交付
  只新增/改动自己的面：`src/pathway_v43/pollutant/s5b_orchestrator.py`
  （唯一 src 改动）+ `tests/test_ppv1_s5b_shard.py`（新）+ `scripts/hpc/`
  （新，5 件）+ 本交付书。F3 的文件一字未碰（其在飞期间本轮开工时的
  dirty real_model.py 已由 F3 自行提交收口）。
- 零模型零网络零花费（0 CNY、0 次 LLM 调用、0 次 sbatch/ssh 提交）；
  不 push，树干净（提交后工作树无本交付的残留改动）。

---

## 一、分片协调工程（交付 1）

### 1.1 R4 锁核实结论（一句话）

v2 的"单协调者 flock"作用域是**整批根**（`batch_root/coord.lock` 一把
`LOCK_EX|LOCK_NB`，第二个协调者无论白名单是否相交都结构化拒
`s5b_coordinator_active`）——对"同根不相交 qid 白名单并发"是**拦**，
故按任务书适配为白名单域锁，版本 `s5b-orchestrator-2 → 3`。

### 1.2 改动明细（src/pathway_v43/pollutant/s5b_orchestrator.py，最小面）

1. **白名单域锁**（`_WhitelistCoordinatorLocks`，新增类）：
   `batch_root/coord/` 下逐 qid 一把 flock（文件名 = qid 消毒 + sha256
   前 8 位，单射：消毒碰撞由哈希区分、同 qid 必同名）；按 qid 排序序
   `LOCK_EX|LOCK_NB` 获取，撞已持 qid ⇒ 结构化拒（kind 沿用
   `s5b_coordinator_active`，detail 新增 `conflicting_qid`/
   `requested_qids`/`acquired_qids` 机读披露），**已获部分全部回滚**
   （不留半套锁）；不相交白名单多协调者并发放行；锁文件内容只写
   pid/qid/时间披露（写失败不影响锁，flock 是权威，崩溃 OS 自动释放）。
   同 qid 双发在**任何 worker 派发前** fail-fast（负控实测：拒时不新增
   run 目录与 case 文件）。
2. **并发写盘硬化**（伴随白名单放行的必然共享面）：
   - `orchestration.json` 的"读-比对-写"进 `orchestration.lock` 短
     flock 临界区串行（关闭分片同时首跑的静默双写窗口：后到者必读到
     先到者副本 ⇒ 参数不同恰好一方 `s5b_orchestration_conflict` 拒，
     负控实测确定性成立）；
   - `_write_json` 改原子 replace（tmp 名含 **pid+线程标识**——同进程
     多线程分片与跨进程分片都不互踩；首版只含 pid 被同进程双线程测试
     抓出真互踩，已修，见 §3.1）；progress.json/batch_report.json/
     orchestration.json/profile_policy.json 四个共享信息文件全覆盖。
3. **白名单去重**（保序 `dict.fromkeys`）：同 qid 重复项不再 flock 同
   文件二次打开自冲突；执行/报告按唯一 qid 集合（旧行为重复白名单会
   产生重复报告行，顺带消除——测试钉死 n_total 唯一计数）。
4. **fd 余量预检**（`_check_lock_fd_headroom`）：锁 fd + worker 管道
   估算超 `RLIMIT_NOFILE` 软限 ⇒ 结构化拒（kind=
   `s5b_lock_fd_headroom_insufficient`，提示 ulimit；fail-closed 不在
   获取中途裸抛 EMFILE）。Linux 缺省 1024 对 298 题 + 40 worker 足够；
   sbatch 脚本统一 `ulimit -n 4096`。
5. **版本与兼容**：`S5B_ORCHESTRATOR_VERSION = "s5b-orchestrator-3"`。
   `orchestration.json` 冻结副本含 `orchestrator_version` 比对 ⇒ **既有
   v2 批根（如 chenyu s5b_298_20261009_batch2）被 v3 协调者续跑时按
   `s5b_orchestration_conflict` 拒**（协调契约变化须新批根，预注册纪律；
   测试钉死）。HPC 首批本来就是新批根，不受影响。模块/入口 docstring
   同步 v3 语义与跨节点注意事项；批报告 `coordinator` 块披露改为
   `{pid, lock_domain, qids_n}`（旧字段 `lock` 随 v2 coord.lock 退场）。

### 1.3 FileRateGate 核实结论（零改动，写明即可）

任务书预判成立：**跨进程 flock 共享设计本来就在**，代码零改动。证据
（`src/pathway_v43/adapters/rate_gate.py` 实读）：

- RPM 滑窗/TPM 事后账/429 冷却/付费停止/max_calls 预算/**在途计数
  （in_flight + 占位 ID）/金额硬帽（预留-结算-超帽披露）**全部
  read-modify-write 都在 `_locked()` 的 `gate.lock` flock 独占临界区内；
- 状态文件临时文件 + `os.replace` 原子落盘（写入中途被杀只留完整
  旧/新 JSON）；
- 分片各自构造 FileRateGate 指向同一 `batch_root/gate/`（worker 经
  `V43_LLM_RATE_GATE` env 同门）；R2 参数首消费核对
  （`verify_config`）保证分片参数一致才可用——与 orchestration.json
  比对双保险；
- **跨节点风险（如实披露，不改代码）**：`reclaim_dead_placeholders`
  判死用本机 `os.kill(pid, 0)`——分片作业跨节点时他节点在途 worker
  会被误判死回收在途占位（在途帽放松；金额侧预留保守转未结算借记、
  committed 只增不减，硬帽不漏）。**处置写进 runbook：首批分片
  `--nodelist` 约束同一节点**；跨节点需求属新轮（连同跨节点 flock 语义
  实测，见 §六残留）。

### 1.4 判分（score）核实结论（零改动）

`score_s5b_batch`（`s5b_scoring.py`）按**冻结注册序全集**逐 qid 判分
（不感知分片）；调用时点约束（全分片终态后单次调用）由 runbook 的
依赖串接保证（`sbatch --dependency=afterok:$BUILD_ID` → 分片数组作业 →
`--dependency=afterok:$SHARD_ID` 的 score 作业；数组作业 ID 的 afterok
= 等全部数组元素）。score 作业脚本内再加**第二道门**：注册序全 qid
终态检查（有 pending/坏 case ⇒ 拒发判分，不把未跑完的题当未命中；
本地正负控实测：全终态批放行/零 case 批拒 `pending=3`）。判分代码、
冻结判据、评分口径、金额守卫族**零触碰**。

---

## 二、sbatch 脚本族 + 部署 runbook（交付 2，scripts/hpc/）

全部**本机可静态检查**（`bash -n` ×4 全过）+ 内嵌 python 逻辑本地实跑
验证（见 §3.2）；**本轮不提交任何作业**（分区权限未开通 + 侦察纪律）。
站点缺省全部乌镇（`wuzh02.hpccube.com:65091`，env 可覆盖）；环境事实
凡出自 zzeshell 侦察的都标注"乌镇待同款核验"，由 netcheck 首作业在
计算节点实测闭环，不假设两站环境相同。

| 文件 | 一句话 |
|---|---|
| `scripts/hpc/deploy.md` | 部署 runbook（自包含）：打包（清单精确到文件，src+assets/analog+v3_reactions+两 MANIFEST+pyproject+scripts/hpc+prereg 冻结稿，约 160MB；三大 json 不进包——recorded-source 通道件，冻结 298 配方不消费）→ scp（`-i` 乌镇专用已验证密钥 `/Users/cc/Downloads/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt`，2026-11-30 到期）→ 解包 → `pip3 install --user rdkit`（包名 rdkit 非 rdkit-pypi）→ 题卷（含金标，chenyu 拉取+双端 sha 比对+只放 HPC 工作区）与凭证 env 放置（chmod 600，值零落盘零打印）→ netcheck 硬门 → build → 用户三步（approve/budget/price）→ 分片数组发车（同节点约束+同参纪律）→ 监控 → score → 结果回收对账 → 故障速查表 + 红线自查 |
| `scripts/hpc/sbatch_hpc_298_netcheck.sh` | 首作业站点自证（硬门，1 分钟级）：计算节点实测 dashscope 端到端路由（侦察遗留风险项闭环）+ flock 互斥/释放语义（管线全部锁的基元）+ rdkit 导入 + python 版本 + 家目录可写；任一项不过非零退出不发首批 |
| `scripts/hpc/sbatch_hpc_298_build.sh` | build 作业（语料检索+编译单进程，4h 墙钟/8 核）：`s5b_cli build --pool-mode template`（冻结 298 配方，无 recorded-source）+ 作业内自检"注册序数=题卷行数" |
| `scripts/hpc/sbatch_hpc_298_shard.sh` | 分片跑题作业：建议 `sbatch --array=1-5` 一次提交全分片（SHARD_INDEX/TOTAL 自动取 SLURM_ARRAY_TASK_ID/COUNT；按冻结注册序连续切片、尾片吃余量、本地实测 5 片拼回=原序逐位一致）；缺省 workers=20/24 核/24h 墙钟；发车前硬检查（批根已 build、env 文件在、budget_guard.json 在——real 批金额门）；断点续跑=同参重投（已完成 qid SKIP；同 qid 双发被白名单域锁 fail-fast 拒） |
| `scripts/hpc/sbatch_hpc_298_score.sh` | score 作业（依赖全分片 afterok；1h/8 核）：终态预检门 + `s5b_cli score`（零 LLM；金标只进判分进程；产物 metrics.json/report.md） |

关键设计决策（与 §1 改动一一对应）：

- **同参纪律**：所有分片用同一脚本同缺省参数——orchestration.json
  比对（flock 串行化后无静默双写窗）保证不同参后到者结构化拒；
- **同节点建议**：首批 `--nodelist` 约束（跨节点 reclaim 误判 + flock
  跨节点语义未实测两项残留的规避；runbook 明示）；
- **fd**：脚本统一 `ulimit -n 4096`（298 把 qid 锁 + worker 管道）；
- **数组作业**：分片=数组元素（依赖串接只需两个 ID：build → 数组 →
  score；失败分片单独 `sbatch --array=N:N` 或整组重投均可断点续跑）。

---

## 三、本地回归（交付 3，四组 + 脚本验证）

### 3.1 四组回归数字

测试环境：`/Users/cc/miniconda3/envs/depending43/bin/python`（pytest
9.1.1）；测试解释器 python3.11（与既有各轮同款）。

| 组 | 命令面 | 数字 |
|---|---|---|
| ① 定向（orchestrator/gate/rate 族） | s5b_shard + s5b_runtime + rate_gate + hit50 cost×3/scope + w23456 + exam 共 9 文件 | **211 passed / 0 failed**（48.45s；= 父族 199 + 本轮 12） |
| ② 全量 not slow（工作树） | `tests/ -m "not slow"` | **2090 passed / 0 failed / 16 deselected**（369.39s；= hwall 全量基线 2061 + 本轮 12 + F3 CI 17，逐项对账精确） |
| ③ G01 隔离 | `/private/tmp/safe_g01_s5b_hpcshard.py`（血统 …cosub_d2_r3→hwall→**hpcshard**；路径 allowlist + 输入 SHA 前后全量复验 + 改动集 vs hwall G01 输入集脚本强制双向核对） | **exit 0 = 2062 passed / 10 skipped / 17 deselected（= hwall G01 实测 2050 + 本轮 12，精确）**，SHA 复验 0 失配、7 游离 .pyc 如实记录（同前轮模式）；实际输入 HEAD=dbc71ca5、dirty=仅本轮 s5b_orchestrator.py（记录 preparation.json）；强制核对：changed={real_model.py(兄弟 F3 轮 dbc71ca5), s5b_orchestrator.py(本轮)}、new={本轮 6 件 + controlled_vocab.py(F3 新模块，不复制则 dirty real_model.py 收集炸——披露为并行输入)}、missing=∅ |
| ④ 父红绿（真父 dbc71ca5 隔离 worktree） | 新测试文件 on 父 | **12 红 / 0 绿**：行为红 5（并发不相交分片被父全局 coord.lock 拒[正是本轮要改的行为]/续跑计数不符/并发参数分歧无 orchestration_conflict/v2 批根照跑不拒/白名单重复项不去重 n_total=3）+ 新面红 6（锁 API ImportError×5 + fd 预检 monkeypatch 目标不存在）+ 版本字面量红 1；父既有族同 worktree **199 passed / 0 failed**（未改测试零回退） |

期间还用 8da11cb7（F3 前祖提交）做过同款父红绿：同样 12 红/族 199
绿（orchestrator 面两提交间无差异，结论一致；真父以 dbc71ca5 为准
存档）。

### 3.2 脚本族静态与逻辑验证（不提交作业）

- `bash -n` ×4 全过；
- netcheck 的 **flock 探针**（父持锁⇒子进程必拒、父放⇒子得）本地实跑
  通过——即测试里验证同一语义（`test_lock_domain_*`）；
- shard 的**白名单切片**内嵌 python 本地实跑：298 qid 切 5 片
  （60/60/60/60/58），5 片拼回 = 冻结注册序逐位一致；
- score 的**终态预检门**本地正负控：全终态合成批放行（SCORE-GATE-OK）、
  零 case 批拒（`pending=3`）；
- 12 件新测试连跑 3 次全绿（并发时序零抖动；其中同进程双线程分片
  场景首版抓出 tmp 名 pid-only 互踩真 bug，修复后稳定）。

---

## 四、金标边界自查

- 零金标题面读取：本轮无离线漏斗/检索面探针；测试合成 qid/分子沿用
  `test_ppv1_s5b_runtime.py` 既有零重叠合成集（W2 纪律）；
- 题卷（questions.jsonl，金标承载物）只出现在 runbook 的**放置步骤**
  （chenyu 拉取/用户提供 → HPC 工作区/gitignored 中转；双端 sha 比对；
  不入仓不进部署 tar——tar 清单精确枚举不含它）；
- 判分零 LLM；scorer/冻结判据/评分口径/金额守卫族零改动（本轮唯一 src
  文件是 orchestrator 协调层）；
- 封存 run 零触碰（无任何 chenyu/封存目录读取——本轮全部本地）；
- 密钥值零落盘：交付物内只有路径（乌镇专用已验证那把的 Downloads
  路径）与放置步骤；env 文件模板只含 KEY 名。

---

## 五、成本与网络

零模型、零真实 HTTP（netcheck 的 curl 属 HPC 首作业执行项，不在本轮
跑）、零 sbatch/ssh 提交（分区权限未开通 + 侦察纪律）；0 CNY。

---

## 六、待复审残留（诚实清单）

1. **分区权限未开通**：全链路（netcheck→build→分片→score）只做了本地
   工程验证，未在真 HPC 上执行过任何一步——开通后从 runbook §6 起逐条
   执行；脚本头的分区名缺省沿用 zzeshell 侦察名，乌镇实名以 `sinfo -a`
   实测 + 提交时 `--partition=` 覆盖；
2. **跨节点语义两项未实测**：①flock 跨节点（netcheck 只实测单节点
   语义）；②`reclaim_dead_placeholders` 本机 pid 判死在跨节点分片下误
   回收他节点在途占位（在途帽放松、金额侧保守不漏）——首批已用
   `--nodelist` 同节点规避，跨节点需求立新轮（含两作业 flock 互斥探针）；
3. **分片视角的监控语义**：progress.json/batch_report.json 为最后写盘
   分片的视角（原子落盘不互踩），全批视角用 `s5b_cli summary`/cases
   计数——runbook 已写明，属知情披露而非缺陷；
4. **v2 批根不兼容**：既有 s5b-orchestrator-2 批根（chenyu
   s5b_298_20261009_batch2 等）不能被 v3 续跑（orchestration.json 版本
   比对拒，预注册纪律）——若日后要在旧批根上补跑须用户裁定（新批根
   重议或版本兼容轮）；
5. bash 脚本族的 SBATCH 头/参数自洽是静态+本地逻辑级验证，真调度器行
   为（数组展开、依赖图、`%A_%a` 日志名）以乌镇 Slurm 实跑为准；
   sbatch 头内不引用 shell 变量（Slurm 限制），可变参数走提交时 env/
   CLI 覆盖（runbook 有说明）；
6. G01 披露词生成时点写"并行在飞 F3 轮"，F3 随后落地为 dbc71ca5
   （preparation.json 的 actual_input_head 已如实记录为该提交，dirty
   面不含 real_model.py）——措辞与机器记录的时间线差在本文说明。

## 七、证据指针

- G01：`/private/tmp/g01_s5b_hpcshard/`（preparation.json /
  input_sha256.json / execution_result.json / post_run_sha_result.json /
  g01_junit.xml / 双日志）；G01 脚本 `/private/tmp/safe_g01_s5b_hpcshard.py`
  （血统：hwall G01 脚本派生，diff 基线 `/private/tmp/g01_s5b_hwall/
  input_sha256.json`）；
- 父红绿：`/private/tmp/hpcshard_parent_wt/`（dbc71ca5 worktree，新
  测试文件副本）；
- 侦察事实源：`docs/HPC_SHUGUANG_SURVEY_2026-10-12.md`（zzeshell，
  环境事实）+ `docs/HPC_WUZHEN_SURVEY_2026-10-12.md`（乌镇首勘失败
  快照，已被 2026-10-12 乌镇专用密钥到位并验证 login03 的事件取代）。
