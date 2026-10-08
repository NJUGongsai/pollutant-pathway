# ppv1 S3b 回修 r3 实施证据(s3b_r3)

日期:2026-10-08(Asia/Shanghai)。范围:Codex S3b-r2 复审
`docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R2_2026-10-08.md` 唯一残余
P1 **S3B-01 后段锚定**(冻结计划与独立既存 run/root/task 原绑定的内容
身份核对)的一次性有限回修。不重开 S3B-02~06/已过 S3a,不实现
S4/S5/分布式锁/新机制库;科学 pending,判据未冻结。

实施时点实际 HEAD:`2bedfc060a9b19019ba44aa2a56dcacb88450c3b`
(= r2 交付提交,即本批直接父);本批变更在其工作树上未提交实施
(见 `metadata/working_tree_status.txt`):源码
`src/pathway_v43/pollutant/runflow.py`(新增
`_verify_frozen_plan_binding`,resume 入口锚核对;RUNFLOW_VERSION
ppv1-runflow-2 → **ppv1-runflow-3**)、`src/pathway_v43/pollutant/
profile.py`(契约注册注释登记 runflow-3;版本值不动 -14)、新测试
`tests/test_ppv1_s3b_r3.py`。用户既存 AGENTS.md 差异与旧未跟踪评审
材料不纳入本批提交。**production.py/store.py/search.py/queue.py/
model_protocol.py/workflow-runner.py 与父字节一致**(见
`metadata/legacy_identity_check.json`:52 份 legacy code_identity 文件
与九份生产/化学共享核心父↔当前逐字节一致;legacy 聚合保持 r2 复审
核验值 `18007e6a…f1374d6`,本批无相关文件变化)。

## 1. 目录与独立数字

| 位置 | 内容 |
| --- | --- |
| `current/` | 当前工作树 PPV1 全量(`pytest tests/ -q -k ppv1`):**879 passed / 0 skipped / 0 failed,exit 0**(871 r2 存量 + 8 新 r3;32 文件);junit + stdout/stderr;另有 r3 焦点跑(8 passed) |
| `baseline/` | 直接父 2bedfc0 detached worktree 同字节对照(新 r3 文件,cmp 逐字节相同):**5 行为红 + 3 合法正控绿 / 0 collection errors**(exit 1);junit + stdout/stderr + 逐案分类 JSON + worktree 建立日志 |
| `probe/` | S3B-01 反例翻转取证(公开入口真子进程):**15/15 观察符合** —— r2 复审两原反例(B3/B4 自洽重封装 frozen_plan artifact)均结构化拒 `frozen_plan_binding_mismatch` 且十五表逻辑快照零变化、被改文件保全、转换 action 0;同计划/省略 plan/显式换 plan 拒/四崩溃合法恢复/合法原计划转换(phase-1)/三产物 2/3→3/3/重复 resume 无新增/novel/弃权/零深度复合披露全保持;observations.json + inputs/ + logs/ + tables/ + sqlite 二进制 SHA 清单(二进制不入档,可读全表快照在 tables/) |
| `g01/` | 安全隔离 G01:**1481 passed / 8 skipped / 17 deselected,exit 0**(1473 r2 + 8 新 r3;pytest 213.90s/外层 215.43s);288 输入(287 r2 + 1 新增 `tests/test_ppv1_s3b_r3.py`)前后 SHA 一致;preparation/execution/junit/stdout |
| `scripts/safe_g01_s3b_r3.py` | G01 控制器(沿 s3b_r2 控制器谱系回到 R7 评审 safe_g01_reproduce;白名单路径不变、当前字节新 SHA;新增 r3 输入) |
| `metadata/` | env(Python 3.11.16/RDKit 2026.03.6/SQLite 3.53.4)、契约版本族(runflow-3/profile-14/search-6/store-9/search-limits-3/format-feedback-1/model-proposals-2/frozen-plan-1)、实际 HEAD/父/脏状态、legacy 一致性核对 |
| `manifest.json`、`SHA256SUMS` | 全部附件 SHA(外层 manifest 不自哈希;只读核验命令见 §5) |

红绿分类(父 2bedfc0 同字节,详见 `baseline/parent_r3_classification.json`):

- **5 行为红,全部为"未结构化拒"型**(`DID NOT RAISE PPV1RunError`,
  父上 public resume 完整执行并写入——省略 plan 的 B3/B4 自洽重封装
  各新增 1 条 phase-injected 转换、重封装+显式新 plan 完成注入转换、
  缺锚/坏锚不构成拒绝):`test_s3b01r3_b3_self_consistent_replaced_
  plan_rejected`、`…_b4_…`、`…_replaced_artifact_with_matching_new_
  plan_rejected`、`…_anchor_missing_rejected`、`…_anchor_corrupt_
  digest_edited_rejected`。父上这些用例的内部到达段 = **完整 public
  resume 执行**(事件提交/转换消费发生),失败点在"拒绝未发生"
  断言,不是早停在某个内部段;
- **3 真父绿(合法正控)**:`b3_omitted_plan_legal_resume_positive_
  control`(1 event/4 commit,重复 resume 无新增)、`same_plan_
  explicit_resume_positive_control`、`b4_legal_transition_new_context_
  positive_control`(转换 done、followup phase-1);
- **0 collection/版本字面量/字段形态红**:本批不更新任何既有测试
  文件(RUNFLOW_VERSION 无测试断言其字面量),父基线集合 = 新 r3
  文件本身。

两原反例翻转数字(与 r2 复审 recovery_specialist 的原值逐项一致,
`probe/observations.json`):
root 原锚摘要 `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe
256e8dd08babdeb94`;重封装 artifact 新摘要 `7164d4f966b107f19544e
5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04`;plan_version 保持
`ppv1-frozen-plan-1`;B3/B4 拒后转换 action 均 0(父行为为各 1
phase-injected);十五表逻辑快照改前/拒后逐表相等;被改 artifact
逐字节保全。

## 2. S3B-01 后段锚定实现与入口矩阵

共享规则:`src/pathway_v43/pollutant/runflow.py` 新增
`_verify_frozen_plan_binding`(file:line 见交付书 §1.2;单一来源
`decision_task_key` 重算,不另造第二套派生),在
`resume_ppv1_run` 的 `_load_frozen_plan` + 传入计划比对之后、
`ledger.recover_run`(B4 补账/B3 bundle 消费)与任何驱动调度/
事件提交/预算 consume **之前**调用:

1. 扫描本 run 全部 retrieve 行;载荷不可解析/非 dict ⇒ 坏锚
   (`frozen_plan_anchor_corrupt`)先拒;
2. 携带非空 `plan_digest` 的行 = 锚(start 落账的根 retrieve 行;
   followup retrieve 不绑定计划摘要)。无任何锚 ⇒ 缺锚
   (`frozen_plan_anchor_missing`)先拒;
3. 逐锚两查:①按行内冻结身份字段 + 行内 plan_digest 用
   `decision_task_key` **单一来源重算** task_key,与行内落账
   task_key(列与载荷)比对,不符 ⇒ `frozen_plan_anchor_corrupt`
   (锚行自身不再同源);②锚 plan_digest 与当前读取的冻结计划
   摘要比对,不符 ⇒ `frozen_plan_binding_mismatch`;
4. 任何拒绝均为结构化 `PPV1RunError`,发生在 recover/补账/调度/
   consume 之前 ⇒ 业务表/event/commit/consume 零新增,原
   artifact/DB 行保全;正常同计划、省略 plan、显式同计划、合法
   原计划转换恢复全保持(探针 + 879 全量证成)。

不提供密码学签名服务、不抵抗全库协同改写(复审 §4 明示范围外);
执行层第二核(`_run_retrieve` plan_digest/`_run_decide`
pool_digest)保留为纵深防御。

## 3. 复现命令(depending43 Python 3.11.16 / RDKit 2026.03.6 / SQLite 3.53.4)

```sh
PY=/Users/cc/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
EV=$REPO/docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r3

# 当前 PPV1 全量(仓库根)
cd $REPO && PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest tests/ \
  -p no:cacheprovider -q -k ppv1

# 父 2bedfc0 同字节红绿对照(输出到新 tmp,不在本目录执行)
git -C $REPO worktree add --detach /private/tmp/ppv1_s3b_r3_base_2bedfc 2bedfc0
cp $REPO/tests/test_ppv1_s3b_r3.py /private/tmp/ppv1_s3b_r3_base_2bedfc/tests/
cd /private/tmp/ppv1_s3b_r3_base_2bedfc && \
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest tests/test_ppv1_s3b_r3.py \
  -q -p no:cacheprovider

# S3B-01 反例翻转探针(公开入口真子进程;输出到新 tmp)
rm -rf /private/tmp/ppv1_s3b_r3_probe_rep && \
PYTHONDONTWRITEBYTECODE=1 $PY -B $EV/probe/probe_s3b_r3.py \
  --repo $REPO --out /private/tmp/ppv1_s3b_r3_probe_rep

# 安全隔离 G01(输出到新 tmp;不在本目录执行)
rm -rf /private/tmp/ppv1_s3b_r3_g01_rep && \
PYTHONDONTWRITEBYTECODE=1 $PY -B $EV/scripts/safe_g01_s3b_r3.py \
  --repo $REPO --out /private/tmp/ppv1_s3b_r3_g01_rep \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

探针与 G01 控制器均**拒绝已存在的输出目录**(fresh tmp only),
不写输入仓与本证据目录;本目录内的一切执行产物均产生于仓外
/private/tmp 后复制归档。旧 r1/r2/历史证据目录与旧评审脚本未在本
目录原地执行或改写。

## 4. G01 缺席依赖逐项披露(与 r2 相同口径)

8 skipped = 5 真实冻结评价(`test_batch_runner.py:52`;
`test_score_report.py:110/163/172/184`)+ 1 旧 v4 对照
(`test_analog_assets.py:95`)+ 2 phase_d 派生 provenance/summary
metadata(`test_analog_v2_corpus.py:62/153`)。17 deselected = 16
`-m "not slow"` + 1 显式排除
`test_export_v3::test_charge_fixture_cn_hits_raw_sb_misses_
neutralization_forbidden`。未进入缺席路径补数,未将 skip 改
pass。288 输入 = 227 r2 本仓白名单 + 1 新增
(`tests/test_ppv1_s3b_r3.py`)+ 42 普通 dependingv3/src + 18 非题面
资产镜像;runflow/profile 为既有白名单路径的更新副本(新 SHA,
见 `g01/input_sha256.json`),前后 SHA 一致;零金标/题面/封存
run/dependingv4/真实 provider,网络 0,判分零 LLM。历史
1110/1138/1196/1250/1299/1389/1453/1473 各自单列不混计。

## 5. 只读核验(不导入项目、不开 SQLite、不运行行为)

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B - <<'EOF'
import hashlib, json, pathlib
ev = pathlib.Path('/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3_impl_2026-10-08/s3b_r3')
sums = {}
for line in (ev/'SHA256SUMS').read_text().splitlines():
    h, p = line.split('  ', 1)
    sums[p] = h
bad = []
for p, h in sums.items():
    f = ev/p
    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
        bad.append(p)
man = json.loads((ev/'manifest.json').read_text())
print('files checked:', len(sums), 'bad:', bad,
      'manifest_files:', len(man['files']))
EOF
```

## 6. 执行异常与限制(如实)

- 本批无环境纠错事件:PPV1 全量、父基线、探针、G01 均一次完整
  执行,无中途额度/中断/续跑;
- 探针 worker 与 pytest 子进程同仓测试口径(`resolve_config()`
  默认、cwd=repo);G01 用控制器钉死的隔离 env(两处口径不同,
  数字分开登记,不互相冒充);
- 探针三产物夹具沿用 r2 证据的预算放宽(total_search_actions 30,
  默认 10),未宣称与旧反例输入逐字节相同(注入转换意图/计划内容
  与 r2 复审原反例语义一致,摘要逐项吻合);
- probe 的合成 SQLite 二进制不入档(`probe/
  synthetic_runs_binary_inventory.json` 记 SHA);可读十五表快照
  在 `probe/tables/`;
- `driver.lock` 披露文件在拒绝路径上会被会话锁持有方重写
  (pid/时间),这是已接受的 P2 口径("零写"指业务账);
  探针的零变化断言只覆盖业务表与被改 artifact 文件。

全部数字为工程合成规则级契约结果,不外推 dev(B1 环境路径中间
步骤)或 298(RHEA 通用酶学)科学性能;判据未冻结;S4/S5 未启动。
