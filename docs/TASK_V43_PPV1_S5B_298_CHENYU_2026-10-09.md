# TASK_V43_PPV1_S5B_298_CHENYU_2026-10-09 — S5b 298 全量评测 Chenyu 执行任务书

> **执行者注意**：本任务书自包含。唯一预注册依据 =
> `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`
> （状态 `preregistration_confirmed`，commit cf64624）。**首跑不可因
> 分数改写；禁重复采样**；§9-②③④ 是发车当日实核项——本文就是
> 实核清单+执行程序。凭证纪律：本文件**永不包含**密码/密钥。
> 通道总述见 `docs/CHENYU_ACCESS.md`（隧道限流/短命令纪律同源）。

---

## 0. 一句话（大白话）

把新架构（PPV1 污染物路径）在 298 题酶学考卷上正式跑一遍、出分。
远端东西已备齐约 95%，剩下三件事：

1. **把 API 钥匙填进远端 env 文件**（一条无回显命令，上次被打断）；
2. **点火**（一条短命令；脚本自动走：建题库→40 路并行答题→判分→
   过守卫，全链自带）；
3. **收三份报告回传本地**（判分明细含金标，只进 gitignored 目录）。

全程有自动守卫，哪步不对脚本自己停、打 `CHAIN5_ABORT_*` 标记，按
§6 排障表处置。花钱不设上限（用户已批），逐调用记账。

## 1. 依据与版本

| 项 | 值 |
|---|---|
| 预注册 | `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`，`preregistration_confirmed`（cf64624 三处状态已翻） |
| 运行时代码 | commit efefb20（real_model / s5b_builder / s5b_orchestrator / s5b_worker / s5b_cli / s5b_scoring；1159 PPV1 测试绿） |
| 远端代码快照 | `git archive v4.3` @ cf64624；245774025 字节；SHA256 `76ed8f08702afed7ccdb4336940ab973b8f21431bf60d8615bd94b7cb9081562` |
| 分母 | 298 固定；失败/超时/空答题照算 miss（预注册冻结） |
| 判分 | 零 LLM、零网络（链内 score 步骤本身如此） |
| 数字口径 | 对外一律带题域标签 **298（RHEA 通用酶学）**，与 dev 题域双向不外推 |
| 旧架构首跑锚（及格线） | hit@1 ≥ 116/298、hit@3 ≥ 128、hit@5 ≥ 130（首跑口径） |

## 2. 远端现状（截至 2026-10-09 ~16:00；新链接若仍是同一台机器，全部有效）

`WS = /usrdata/EnzymeCAGE_data/workspaces`

| 件 | 远端路径 | 状态 |
|---|---|---|
| 源码包 | `/tmp/s5b_code.tar.gz` | ✓ 已传已核（245774025B，SHA 见 §1） |
| 解包代码 | `$WS/s5b_298_20261009`（下称 `D`） | ✓ `src/` 就位 |
| 链路脚本 | `/tmp/s5b_chain5.sh` | ✓ 已上传且 Q 行已修正（本地 `/tmp/s5b_chain5.sh` 同版可重传；全文见附录 A） |
| 题卷（金标） | `$WS/ec298_gold_readonly/questions.jsonl` | ✓ SHA 已核 = `9f5955d4…`（远端第二副本 `$WS/dependingv4/runs/enzymecage298/questions.jsonl` 同 SHA） |
| env 文件 | `$WS/.dependingv43-dashscope.env` | ⚠ `V43_LLM_BASE_URL`/`V43_LLM_MODEL` 已填；`V43_LLM_API_KEY` **空**（上次填钥匙被中断，先 envcheck 确认） |
| 批次根 | `$WS/s5b_298_20261009_batch` | 空，待脚本创建（**仓外合法根**——金标守卫只放行仓外或仓内 `reports/ppv1_s5b/`） |
| python | `$WS/dependingv43_dev/.venv/bin/python` | ✓ dev venv |
| 已花钱 | — | **零元、零次真实调用、预注册未消费**（两次点火均被守卫拦在花钱前：①批次根误放仓内；②题卷路径笔误；③钥匙空） |

> ⚠️ **若新链接不是同一台机器**（Step 0 找不到上述路径）→ 停，回报
> 用户。远端没有 venv/依赖引导程序，不要自行重建全套环境。

## 3. 红线（违反=事故）

1. **金标永不入仓**：远端产物只在仓外批次根；回传本地的判分件只进
   gitignored `reports/ppv1_s5b/`；
2. 判分零 LLM、零网络；
3. **预注册禁重复采样**：本地备胎批 `reports/ppv1_s5b/s5b_298_local`
   （已建已批未跑）绝不能与远端批并行/先后开跑；启用须用户明示
   （仅当远端链宣告死亡时）；
4. 凭证/密码不打印、不入仓、不入日志：填钥匙只用 §5 Step 3 的
   无回显命令；expect 包装脚本只住 `/tmp`；
5. 失败题留分母；封存 run 只读；main 分支禁动（只 push v4.3）；
6. **单一协调者**：点火前 `pgrep` 确认没有别的 chain5 在跑；不要双点火。

## 4. 凭证接线（用户当次重发新链接后做一次）

把 ssh 链接拆成 host/port/user/pass，写两个 `/tmp` 助手脚本
（凭证只进这两个文件；两文件丢了找用户按原样重建）：

`/tmp/cy_ssh.sh`：

```tcl
#!/usr/bin/expect -f
# 用法: /tmp/cy_ssh.sh "<远端短命令>"
set timeout 7200
set host __HOST__
set port __PORT__
set user __USER__
set pass __PASS__
spawn ssh -o StrictHostKeyChecking=accept-new -p $port $user@$host {*}$argv
expect "assword:"
send "$pass\r"
expect eof
```

`/tmp/cy_scp.sh`：

```tcl
#!/usr/bin/expect -f
# 用法: /tmp/cy_scp.sh <本地文件> <远端路径>
set timeout 7200
set host __HOST__
set port __PORT__
set user __USER__
set pass __PASS__
set local [lindex $argv 0]
set dest [lindex $argv 1]
spawn scp -P $port $local $user@$host:$dest
expect "assword:"
send "$pass\r"
expect eof
```

（两个脚本 `chmod +x`。）

- **连通验证**：`/tmp/cy_ssh.sh "ls /usrdata/EnzymeCAGE_data/workspaces/ | head"`；
- **限流纪律**：约 1 连接/3 分钟；连接被掐等 60–90s 再试；长任务一律
  `nohup … > 日志 2>&1 &` 落盘+短连接轮询；**命令必须短**（单行）——
  多 KB 长命令会被隧道掐掉且**回显 DISPATCHED 但从未执行**（本窗口
  实测两次）；
- expect 前两行是噪声（`spawn ssh…`+密码提示），拉数据要
  `grep -v "^spawn ssh\|password:"`；
- 单流 scp >20MB 会被中转掐断（大件分块纪律见附录 B）。

## 5. 执行步骤（命令可整段复制；每步有通过条件）

### Step 0 核远端状态（新链接接好后第一件事）

```bash
/tmp/cy_ssh.sh "ls -d /usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009/src /tmp/s5b_code.tar.gz /tmp/s5b_chain5.sh /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env 2>&1; ls /usrdata/EnzymeCAGE_data/workspaces/ | head -12"
```

四个路径都在 → Step 1。缺 `/tmp` 件 → 附录 B + §6；连 `$WS` 都不对
（新机器）→ 停，报用户。

### Step 1 发车硬门 §9-③：三锚重算（预注册冻结项）

**本地**（执行机=本 Mac；以下为 2026-10-09 已重算值，跨日须重跑）：

```bash
shasum -a 256 \
  /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl \
  /Volumes/CC/Enzyme_Agent/ENZYMECAGE_POLLUTANT_REACTION_TEST_298_FINAL_V6_PAYLOAD_2026-09-21/ENZYMECAGE_POLLUTANT_REACTION_TEST_298_FINAL_V6_PROVISIONAL_2026-09-21.csv \
  /Volumes/CC/Enzyme_Agent/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1/exam_inputs.jsonl
# 须依次 = 9f5955d4… / a3cb7955… / cb5996c9…（全 SHA 见 §1 与下表）
```

**远端（权威）**：

```bash
/tmp/cy_ssh.sh "sha256sum /usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl /usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev/runs/ec298_v43r1/exam_inputs.jsonl 2>/dev/null"
```

| 锚 | 全 SHA256 | 角色 | 规则 |
|---|---|---|---|
| questions.jsonl | `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` | **链路实际消费件** | 远端不符 ⇒ **停**（chain5 内置同款硬门，双保险）；不许换文件凑数 |
| exam_inputs.jsonl | `cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703` | 运行侧锚 | 不符/找不到 ⇒ 如实记录+报用户，不静默 |
| V6 题卷 CSV | `a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a` | 题源溯源锚 | 本地权威副本已核；链路不消费；远端无副本不阻断但发车记录写明 |

### Step 2 确认没有旧链在跑（单一协调者）

```bash
/tmp/cy_ssh.sh "pgrep -af 's5b_chain5|s5b_cli' | head; echo PGREP_DONE"
```

有 `s5b_chain5.sh` 进程 → **别点火**，直接跳 Step 6 监控。只有残留
`s5b_cli` 孤儿 → 报用户处置（确认其父链已死前不要 kill）。

### Step 3 填 API 钥匙（无回显；钥匙值不落日志）

先 envcheck：

```bash
/tmp/cy_ssh.sh "cd /usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009 && PYTHONPATH=src /usrdata/EnzymeCAGE_data/workspaces/dependingv43_dev/.venv/bin/python -B -m pathway_v43.pollutant.s5b_cli envcheck --env-file /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env 2>&1 | tail -3"
```

`"ok": true` → 跳过填钥匙。`"ok": false` 缺 `V43_LLM_API_KEY` →
从 v41 `.env` 无回显拷入（那把钥匙就是 9 月底 298 考试用的 DashScope
按量钥匙，已知可用）：

```bash
/tmp/cy_ssh.sh "F=/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env; V=/usrdata/EnzymeCAGE_data/workspaces/dependingv4_v41/.env; K=\$(grep '^LLM_API_KEY=' \$V | cut -d= -f2- | tr -d '\r'); if [ -n \"\$K\" ]; then sed -i '/^V43_LLM_API_KEY=/d' \$F; printf 'V43_LLM_API_KEY=%s\n' \"\$K\" >> \$F; chmod 600 \$F; echo KEY_FILLED; else echo KEY_EMPTY_IN_V41_STOP; fi"
```

`KEY_EMPTY_IN_V41_STOP` → 停，报用户。填完再跑一遍 envcheck 确认
`"ok": true`。顺手把非敏感两行记进发车记录（模型名/端点不是密钥）：

```bash
/tmp/cy_ssh.sh "grep '^V43_LLM_MODEL=\|^V43_LLM_BASE_URL=' /usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env"
```

### Step 4（条件）重传链路脚本

仅当 `/tmp/s5b_chain5.sh` 缺失/被清：

```bash
/tmp/cy_scp.sh /tmp/s5b_chain5.sh /tmp/s5b_chain5.sh
```

（本地 `/tmp/s5b_chain5.sh` 为修正版，Q 行已指 `ec298_gold_readonly`；
全文见附录 A。本地 /tmp 也丢了 → 从附录 A 原文重建。）

### Step 5 点火（一条短命令；以回显为准）

```bash
/tmp/cy_ssh.sh "nohup bash /tmp/s5b_chain5.sh > /tmp/s5b_chain5.log 2>&1 & sleep 3; head -8 /tmp/s5b_chain5.log; echo FIRE_DONE"
```

通过条件：输出含 `FIRE_DONE`，且 head 里出现
`CHAIN5_QSHA=9f5955d4…`（SHA 硬门过）。head 显示任何
`CHAIN5_ABORT_*` → §6。若连接被掐没有 `FIRE_DONE` 回显 → 等 90s
重试（**expect 封装连接失败也退 0，以回显文字为准，不信 exit code**；
本窗口实测教训）。

### Step 6 监控（限流：~3 分钟一拍，短命令）

```bash
/tmp/cy_ssh.sh "tail -10 /tmp/s5b_chain5.log; echo ---; cat /usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009_batch/progress.json 2>/dev/null | head -c 400"
```

标记语义（脚本自打）：

- `CHAIN5_PREP_OK` → build/approve/price 完成（构建 298 张参考图，
  预计十几分钟到一小时）；
- `CHAIN5_FULL_START` → 40 路开跑；`progress.json` 看完成数/298；
  中途调用账看 `$B/gate/gate.json`（调用上限 894）；
- `CHAIN5_FULL_EXIT=0` → 跑完；非 0 → 看其上方日志定位；
- `CHAIN5_SCORE_START` / `CHAIN5_SCORE_EXIT=0` → 判分中/判分完
  （零 LLM，纯 CPU）；
- `CHAIN5_BASIS_OK` → 预注册硬门④通过（全部题目-答卷按 qid 严格
  配对，无一 fallback）；
- `CHAIN5_SCORED` → 全链完成 → §7。

**时长预期（如实）**：构建 ~15–60min；40 路跑题 ~1–2.5h（不确定项：
每题最多 3+2 次调用、单调用数分钟、gate 894 上限）；判分 ~10–30min。
断连不影响（链是 nohup 的）——重连继续本步轮询。

## 6. 排障表（标记 → 原因 → 处置）

| 标记/现象 | 原因 | 处置 |
|---|---|---|
| `CHAIN5_ABORT_QSHA` | 远端题卷 SHA ≠ `9f5955d4…` | **停**，报用户；不许换文件凑数 |
| `CHAIN5_ABORT_ENV` | `V43_LLM_*` 缺（多半钥匙空） | Step 3 填钥匙后回 Step 5 重点火 |
| `CHAIN5_ABORT_CD` / `CHAIN5_ABORT_TAR` | 代码目录/源码包缺失 | `/tmp` 被清：附录 B 重传 tar + Step 4 重传脚本 + 重点火 |
| `CHAIN5_ABORT_BUILD` | 构建错（log 尾有栈） | 栈尾巴报主窗口/用户；批次根若半建，整目录删掉再重试（幂等键 = `batch_manifest.json`） |
| `CHAIN5_ABORT_APPROVE` / `CHAIN5_ABORT_PRICE` | 批准/价格快照写失败 | 同上，报错尾巴 |
| `CHAIN5_BASIS_FAIL` | 判分后配对 basis 有非 `qid_strict` | **分数不可采信**；原文回传 metrics.json 该字段，报用户（代码侧本应结构化拒，出现即异常） |
| 无 `FIRE_DONE` 回显 | 点火命令没打进（连接掐） | 等 90s 重试 Step 5 |
| 连续 `Connection closed` | 隧道限流 | 拉长到每 4–5 分钟一拍；别连环重试 |
| `progress.json` 长时间不动 | 限流下正常慢，或 worker 卡 | 先看 `gate/gate.json` 调用数与 `tail` 日志；仍不动 30min+ → 报用户（worker 断点续跑设计支持 kill 后重发同命令恢复） |

## 7. 完成后回传与义务

**回传三件套**（远端 → 本地 gitignored
`reports/ppv1_s5b/s5b_298_remote/`，先 `mkdir -p`）：

```bash
B=/usrdata/EnzymeCAGE_data/workspaces/s5b_298_20261009_batch
for f in report.md report_plain.md metrics.json; do
  /tmp/cy_scp.sh $B/$f reports/ppv1_s5b/s5b_298_remote/$f
done
```

- `report.md`（技术版）/ `report_plain.md`（大白话版）/
  `metrics.json`（明细，含判分明细 ⇒ **只进 gitignored**）；
- 判分明细与参考图（含金标）留远端不动；封存后只读；
- 摘要数字（总命中/分桶）可进 docs，全部带「298 题域」标签；
- 填 `docs/S5B_298_INTERIM_BRIEF_2026-10-09.md` 的槽位（给老板的版本）。

**记账义务（预注册冻结）**：逐调用账 =
`$WS/s5b_298_20261009_batch/runs/<run_id>/s5b_real_calls.jsonl`
（每 run 一份，零密钥）+ `gate/gate.json` 调用数 + 实际并发峰值，
如实记进发车记录；费用 = 调用数 × 价格快照（0.8 / 2.8 元/Mtok），
日后账单回填核对。

**后置（不阻塞跑）**：Codex 补审（launch/runtime 批）、mimo r27
评审随下一轮交付走；`docs/CHENYU_ACCESS.md`「最后核验」日期顺带更新。

## 8. 完成报告模板（给用户的大白话版）

- 跑完没有：Y/298 题完成，失败 Z 题照算 miss（分母 298 不变）；
- 主口径：hit@1 = x/298（x.x%），hit@3、hit@5 同款；
- 旧口径敏感性（松口径参照，不对外当成绩）；
- 对照旧架构首跑锚（hit@1 116 / hit@3 128 / hit@5 130）：过线/未过线；
- 花了多少钱（调用数 × 单价）；
- known_gaps 披露照预注册 §3.3 原文。

---

## 附录 A：chain5 全文（修正版；本地 `/tmp/s5b_chain5.sh` 同款）

```bash
#!/bin/bash
exec 2>&1
WS=/usrdata/EnzymeCAGE_data/workspaces
PY=$WS/dependingv43_dev/.venv/bin/python
D=$WS/s5b_298_20261009
Q=$WS/ec298_gold_readonly/questions.jsonl
B=$WS/s5b_298_20261009_batch
R=$B/runs
QSHA=9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c

# ① 发车硬门(预注册 §9-③):远端权威题卷 SHA 实核,不符即停
SHA=$(sha256sum $Q 2>/dev/null | awk '{print $1}')
echo CHAIN5_QSHA=$SHA
if [ "$SHA" != "$QSHA" ]; then echo CHAIN5_ABORT_QSHA; exit 1; fi

# ② 凭证存在性(密钥值不打印),不配置即停
cd $D || { echo CHAIN5_ABORT_CD; exit 1; }
export PYTHONPATH=$D/src
$PY -B -m pathway_v43.pollutant.s5b_cli envcheck --env-file $WS/.dependingv43-dashscope.env || { echo CHAIN5_ABORT_ENV; exit 1; }

# ③ 仓代码就位(chain4 已解包,幂等);清掉 chain4 误建的仓内根
if [ ! -d $D/src ]; then
  rm -rf $D; mkdir -p $D
  tar -xzf /tmp/s5b_code.tar.gz -C $D || { echo CHAIN5_ABORT_TAR; exit 1; }
fi
rm -rf $D/local 2>/dev/null

# ④ 幂等 prep:build(仓外批次根)/approve/price
if [ ! -f $B/batch_manifest.json ]; then
  $PY -B -m pathway_v43.pollutant.s5b_cli build --questions $Q --batch-root $B --batch-tag s5b-298 --pool-mode template || { echo CHAIN5_ABORT_BUILD; exit 1; }
fi
if [ ! -f $B/preregistration_approval.json ]; then
  $PY -B -m pathway_v43.pollutant.s5b_cli approve --batch-root $B --user-authorization launch-authorized-2026-10-09 || { echo CHAIN5_ABORT_APPROVE; exit 1; }
fi
if [ ! -f $B/price_snapshot.json ]; then
  $PY -B -m pathway_v43.pollutant.s5b_cli price --batch-root $B --input-per-mtok 0.8 --output-per-mtok 2.8 || { echo CHAIN5_ABORT_PRICE; exit 1; }
fi
echo CHAIN5_PREP_OK $(date +%H:%M:%S)

# ⑤ 40 路全量(断点续跑;批级 gate 894)
echo CHAIN5_FULL_START $(date +%H:%M:%S)
$PY -B -m pathway_v43.pollutant.s5b_cli run --batch-root $B --runs-root $R --workers 40 --gate-max-calls 894 --python-bin $PY --env-file $WS/.dependingv43-dashscope.env
echo CHAIN5_FULL_EXIT=$?
cat $B/progress.json 2>/dev/null

# ⑥ 判分(零 LLM)
echo CHAIN5_SCORE_START $(date +%H:%M:%S)
$PY -B -m pathway_v43.pollutant.s5b_cli score --batch-root $B --runs-root $R
echo CHAIN5_SCORE_EXIT=$?

# ⑦ 预注册硬门 §9-④:配对 basis 全 qid_strict 才可采信分数
$PY -B -c "
import json, pathlib
m = json.loads(pathlib.Path('$B/metrics.json').read_text(encoding='utf-8'))
b = m.get('evaluator_pairing_bases') or {}
bad = {k: v for k, v in b.items() if v != 'qid_strict'}
print('CHAIN5_BASIS_FAIL ' + json.dumps(bad, ensure_ascii=False) if bad else 'CHAIN5_BASIS_OK graphs=%d' % len(b))
"
echo CHAIN5_SCORED $(date +%H:%M:%S)
ls -la $B/report.md $B/report_plain.md $B/metrics.json 2>/dev/null
```

## 附录 B：大件重传纪律（仅源码包缺失时）

本地 `/tmp/s5b_code.tar.gz`（245774025B，SHA `76ed8f08…`）还在就直接
传（>20MB 单流会被掐，须分块）；没了先重建：

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43 && git archive v4.3 | gzip > /tmp/s5b_code.tar.gz
```

分块传输（每块后核远端字节数，失败重试 2 次）：

```bash
split -b 20m /tmp/s5b_code.tar.gz /tmp/s5b_part_
for f in /tmp/s5b_part_*; do /tmp/cy_scp.sh $f /tmp/$(basename $f); done
```

远端拼回+核验：

```bash
/tmp/cy_ssh.sh "cat /tmp/s5b_part_* > /tmp/s5b_code.tar.gz && sha256sum /tmp/s5b_code.tar.gz"
# 必须等于 76ed8f08702afed7ccdb4336940ab973b8f21431bf60d8615bd94b7cb9081562
```

然后：远端 `rm -rf $D` 重解包（`tar -xzf /tmp/s5b_code.tar.gz -C $D`
，先 `mkdir -p $D`）→ Step 4 重传脚本 → Step 5 点火。远端分块件
`rm /tmp/s5b_part_*` 清理。
