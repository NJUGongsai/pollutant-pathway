# ppv1 S3b 回修 r2 实施证据(s3b_r2)

日期:2026-10-08(Asia/Shanghai)。范围:Codex S3b 复审
`docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md` §4 六组 P1
(S3B-01~06)的有限回修 —— 冻结输入恢复消费、坏 artifact 恢复隔离、
后续/转换集合完整性、公开恢复执行会话互斥、novel 独立假设消费者、
blocked 原因/对象持久接公开 stop。

实施时点实际 HEAD:`c1211183c0874b12c5b5461845d3c61f0a84719c`
(= 复审报告 HEAD;r2 变更在其工作树上未提交实施);父提交:
`b7f2bba02ca49edd0a45a13bc9b8434909d99175`。脏状态含本批 10 个
修改文件(6 源码 + 4 测试/worker)+ 1 新测试文件,及用户既存
AGENTS.md 差异与旧未跟踪评审材料(不纳入本批提交)。

## 1. 目录与数字

| 位置 | 内容 |
| --- | --- |
| `baseline/` | 直接父 c121 detached worktree 同字节红绿对照:新 r2 文件 + 更新的 3 既有文件 + 更新 worker;**18 failed / 57 passed / 0 collection errors**;junit + stdout/stderr + 分类 JSON |
| `current/` | 当前工作树 PPV1 全量:**871 passed / 0 skipped / 0 failed,exit 0**(851 存量 + 20 新 r2;含 4 个更新的既有文件全绿) |
| `g01/` | 安全隔离 G01:**1473 passed / 8 skipped / 17 deselected,exit 0,208.51s pytest / 210.25s wall**;287 输入(286 r1 + 1 新 r2 测试文件),前后 SHA 一致,preparation/execution/junit/stdout |
| `scripts/safe_g01_s3b_r2.py` | G01 控制器(沿 s3b_r1 控制器谱系;白名单路径不变,当前字节新 SHA;新增 `tests/test_ppv1_s3b_r2.py`) |
| `manifest.json`、`SHA256SUMS` | 全部附件 SHA(外层 manifest 不自哈希) |

红绿分类(父 c121 同字节,详见 `baseline/baseline_classification.json`):

- **新 r2 文件:15 行为红 + 5 合法正控绿**(父上模块已存在,无
  collection 红;合法正控 = B3 同 output 恢复、B4 0-followup 窗口、
  三产物正常、合法非零、空池 no_local_candidate —— 父亦绿);
- **更新的 3 既有文件:3 红** = 1 profile 版本字面量有意翻转
  (profile-13→14/search-5→6,沿前批登记口径)+ 1 字段形态红
  (父 blocked 条目缺 action_id 键;底层行为红 = 父不持久 blocked 行)
  + 1 行为红(父接受无 reaction_spec 的 novel,DID NOT RAISE);
- 失败均在首个修复目标断言处如实失败;早停内部段不报通过。

## 2. 六组 P1 的入口→消费权威→同源守卫(代码位置)

| P1 | 入口 | 消费权威 | 守卫(同源) |
| --- | --- | --- | --- |
| 01 冻结输入 | `runflow.start_ppv1_run/resume_ppv1_run`、`_Driver._pool_for/_run_retrieve/_run_decide/_model_proposals/_match_transition` | start 持久化的冻结计划 artifact(`run-plan/frozen_plan`,plan_digest 内容绑定,H07 包装读取) | resume 无 plan ⇒ 沿冻结;传入计划 digest 不符 ⇒ `frozen_plan_mismatch` 结构化拒(零写入);冻结计划损坏 ⇒ 完整性失败;retrieve 任务 plan_digest 与 decide 冻结 pool_digest 同源核验(`runflow.py:_run_retrieve/_run_decide`) |
| 02 恢复裁定接执行门 | `resume_ppv1_run` → `SearchLedger.recover_run` → `isolate_recovered_failure` → `_Driver._inflight_action_ids` | recover 报告的坏 artifact 处置(disposition 携带 error) | 坏 hash/不可解析 ⇒ claimed→blocked(`recovery_failure:<kind>`);零重执行/零坏任务 event/成功 commit;claim/激活对 blocked 均拒;证据(坏文件/attempt/预约行)保全;合法 B1–B4 与独立任务继续 |
| 03 后续集合完整性 | `_Driver.reconcile_followups`(+`_ensure_transition_followup`)、`_run_expand`(转换一次冻结)、`_run_transition` | 提交记录 event_id → 事件行 + 展开计划附件 + 冻结计划 scenario_transitions | 期望集合 = 事件产物全集 × 展开计划;逐对象幂等补齐(enqueue 同键同内容 unchanged);转换带 pending_followup 一次写入(无两写窗口);不重发事件/不重复扣额;旧边冻结 |
| 04 执行会话互斥 | `start_ppv1_run/resume_ppv1_run` 的 `_DriverSession` | run 目录 `driver.lock` 的 flock(LOCK_EX\|LOCK_NB;OS 权威) | 竞争方在任何恢复/认领/请求/工具执行前 `driver_session_active` 结构化拒;崩溃 OS 自动释放 ⇒ 新进程沿原 attempt/预约接管;胜者退出后幂等复用;不宣称分布式锁/外部 exactly-once |
| 05 novel 消费者 | `model_protocol.parse_model_proposals`(novel 须 reaction_spec)、`runflow._run_decide`(prepare_hypothesis 单一构建源 + schedule + 固定生产链)、`_run_retrieve`(空池+模型仍进 decide)、`build_substrate_profile`(底物档案) | 既有结构身份/参与物/系数/共同产物/条件/依赖契约;proposal_context 来源入冻结任务输入 | 缺 reaction_spec ⇒ json_field 格式错误(反馈有界);spec 内容非法 ⇒ 构造侧结构化拒(run_error);弃权合法(proposals=[];响应耗尽=弃权);不启 chemical_reposal、不付费;网络恒 0 |
| 06 blocked 持久 | `queue.schedule_hypotheses` → `SearchLedger.record_blocked_hypothesis` → `stop_report` | search_actions blocked 行(status/defer_reason/冻结 payload) | stop 从持久行派生 depth_limit 原因 + blocked_objects 对象清单(有界 100);主因优先级不动(budget > depth);恢复/重放幂等不重数;blocked 不可执行(reactivate/claim 拒) |

## 3. 复现命令(depending43 Python 3.11.16 / RDKit 2026.03.6 / SQLite 3.53.4)

```sh
# 当前 PPV1 全量(仓库根)
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  -m pytest tests/ -p no:cacheprovider -q -k ppv1

# 父 c121 同字节红绿对照
git worktree add --detach /private/tmp/ppv1_s3b_r2_base_c121 c1211183
cp tests/test_ppv1_s3b_r2.py tests/s3b_worker.py tests/test_ppv1_profile.py \
   tests/test_ppv1_s3b_queue.py tests/test_ppv1_s3b_model.py \
   /private/tmp/ppv1_s3b_r2_base_c121/tests/
cd /private/tmp/ppv1_s3b_r2_base_c121 && \
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest tests/test_ppv1_s3b_r2.py \
  tests/test_ppv1_profile.py tests/test_ppv1_s3b_queue.py \
  tests/test_ppv1_s3b_model.py -q -p no:cacheprovider

# 安全隔离 G01(输出到新 tmp;不在本目录执行)
rm -rf /private/tmp/ppv1_s3b_r2_g01 && \
PYTHONDONTWRITEBYTECODE=1 $PY -B \
  <本目录>/scripts/safe_g01_s3b_r2.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_s3b_r2_g01 \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

## 4. G01 缺席依赖逐项披露(与 r1 相同口径)

| 缺席/排除 | 位置 |
| --- | --- |
| 5 skip,真实评价依赖 | `tests/test_batch_runner.py:52`;`tests/test_score_report.py:110/163/172/184` |
| 1 skip,v4 对照 | `tests/test_analog_assets.py:95`(未访问 dependingv4) |
| 2 skip,phase_d 派生 metadata | `tests/test_analog_v2_corpus.py:62/153` |
| 16 deselect,slow | 逐 nodeid 见 junit(测试体未执行) |
| 1 显式 deselect | `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` |

历史数字(1110/1138/1196/1250/1299/1389/1453)保留历史标签;
1473 = 1453(r1)+ 20(r2),工程合成,不外推 dev(B1 中间步骤)或
298(RHEA 通用酶学)科学性能。

## 5. 边界与诚实披露

- 全部规则级合成(CCO→CC=O 等),无真实金标/题面/封存逐题 run/
  dependingv4/真实评价资产;scripted 网络 0;真实 provider 默认
  off(额度 0 登记即拒);判分零 LLM;无外部模型调用。
- 执行会话互斥为**同机文件锁**(flock);跨机/分布式锁与外部
  provider exactly-once 不在范围(沿复审裁定)。
- cache_hit 同构、两事务间外部 SQL 并发窗口、foreign-run 反向诊断
  等沿 S3a R4 §5 / 复审 §5 既定 P2 边界保持,未扩大历史保证。
- `_run_decide` 的 pool_digest / `_run_retrieve` 的 plan_digest 同源
  核验是第二层守卫(第一层为冻结计划绑定);正常流不可达,防御
  DB 侧输入漂移。
- 本目录封存后只读;复现先复制到新 tmp(见 §3)。
