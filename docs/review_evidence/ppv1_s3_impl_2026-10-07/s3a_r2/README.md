# S3a 回修 r2 实施证据(ppv1_s3_impl_2026-10-07/s3a_r2)

日期:2026-10-07,Asia/Shanghai。固定仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`,
实施前 HEAD(直接父基线)`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`(v4.3 分支)。
本目录为 **S3a 回修轮(r2)实施方证据**:Codex S3a 复审五组 P1(S3A-01~05)
的修复、回归与红绿对照。复审报告:`docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md`
(只读;详细反例输入在其永久证据 `ppv1_s3a_codex_2026-10-07/`,本轮回修
未在旧证据原地执行任何探针)。

## 1. 范围与完成/未完成

- **已完成**:S3A-01(B3/write_bundle 与全部输出消费入口共用 action+attempt+
  task+event 完整绑定)、S3A-02(首次 complete/B4/done/已有提交结果复用经
  公共 `store.submit_event` 重放同源的完整事件账权威核验 + attempt/预约
  引用行核验)、S3A-03(defer 先核未执行事实;注册/读取/恢复共用 profile
  `validate_search_limits` 十键单一校验)、S3A-04(请求同键异身份内容冲突 +
  登记/发送/响应/失败执行引用闭合)、S3A-05(停止报告披露 claimed/open
  attempt,执行未完成不报 exhausted_search)。
- **未做(不冒充)**:S3b 全部(队列化学集成/两类 deferred 调度/条件依赖/
  场景转换/模型协议与格式反馈/冻结 AtomTool 中心证据生产链/PPV1 runner
  公开分流);runner 双入口对 PPV1 继续 fail-closed;外部 exactly-once;
  机制库;科学性能门;判据冻结。
- **契约影响**:search ppv1-search-1 → ppv1-search-2(消费协议闭合);profile
  -9 → -10(contracts 登记);store 保持 -9(表结构/writer 行为未改,权威
  核验从 search 层调用公共 submit_event);search-limits 保持 -3(计数语义
  未动,注册/读取/恢复改同源单一校验实现)。workflow/runner.py 未改,
  legacy code_identity 聚合不受本批影响。

## 2. 实际执行与数字(全部 depending43 Python 3.11.16 / RDKit 2026.03.6 /
SQLite 3.53.4,`-B` + `PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider`)

| 执行 | 数字 | 证据 |
| --- | --- | --- |
| 当前源 PPV1 全量(24 文件) | **648 passed / 0 skipped / 0 failed**,exit 0,pytest 8.36s | `current/ppv1_full/`(junit+stdout+stderr) |
| r2 新回归(1 文件 54 项) | **54 passed**,exit 0 | `current/rework_r2/` |
| 四崩溃/H06 双进程/零预算/悬空请求矩阵(自审复跑) | **23 passed**,exit 0,2.15s | `current/crash_barrier_budget/` |
| 直接父基线 9b78f42 detached worktree 同字节新回归 | **52 failed / 2 passed**,exit 1(行为红=修前缺口;2 正控绿:合法未执行 defer 释放、非 expand 空 attempt 请求) | `baseline/rework_r2/`(junit+stdout+failed_nodeids) |
| 同基线更新的既有测试(s3a_search/s3a_recover/profile) | **2 failed / 79 passed**(1 行为红:提交记录 event_id 篡改在基线仅报事件缺失,r2 先在记录哈希层拒;1 版本红:profile-10 断言) | `baseline/updated_existing/` |
| G01 安全隔离(R7 白名单 + R8/S3a/r2 输入,275 显式输入) | **1250 passed / 8 skipped / 17 deselected**,exit 0,pytest 195.43s,控制器 197.262s | `g01/`(preparation/execution_result/junit/stdout/stderr) |

基线无 collection 红(新回归只用公开 API,`tests/test_ppv1_s3a_rework_r2.py`
在 9b78f42 可正常收集)——与首批 S3a 的 00e509a collection 红历史分开;
00e509a 对照保留在 `ppv1_s3a_impl_2026-10-07/s3a_r1/`,不用它替代本轮行为红。

G01 8 项 skip 逐项:`test_analog_assets.py:95`(v4 对照源)、
`test_analog_v2_corpus.py:62/153`(phase_d 派生 metadata)、
`test_batch_runner.py:52`、`test_score_report.py:110/163/172/184`(真实评价
依赖);17 deselect = 16 slow(`-m "not slow"`)+ 1 明确排除
`tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`。
R7 历史 1110/8/17、R8 历史 1138/8/17、S3a 首批 1196/8/17 单列,不混计;
工程数字不代表 dev/298 科学性能。G01 只在仓外新 tmp 执行,275 项输入
SHA 前后一致(`g01/input_sha256.json`);不读取 evaluation/金标/题面/
封存逐题 run/dependingv4;无 provider 调用、无判分 LLM、无网络请求
(scripted network_request_count 恒 0)。

## 3. mimo

- v9 请求快照:`mimo/mimo_ppv1_chem_review_request_v9_snapshot.md`(替换前
  原文;旧回应 r5–r9 在 `docs/` 原样保留);
- v10 送审快照:`mimo/mimo_ppv1_chem_review_request_v10_sent.md`(自包含
  展开必要规则;复审 §5 mimo⑥ 精度更正落入判据三;mimo⑤确认后不再
  要求改代码 scope);**由主会话送审,实施 agent 未调用任何外部模型**。

## 4. 输入与完整性

- 基线同字节输入 5 份哈希:`baseline/test_input_hashes.txt`(worktree 副本
  与仓内字节一致,shasum 双向核对);
- 实际 HEAD/父/dirty:`meta/head_status.txt`;运行时版本与契约:
  `meta/runtime.txt`;基线 worktree 建立/清理:`meta/worktree_*.txt`
  (清理用 --force 仅因副本为未跟踪的同字节测试输入,主仓未动);
- 本目录不含任何运行 SQLite/pytest cache/字节码/真实敏感数据;全部合成
  输入(CCO → CC=O 规则级夹具);
- manifest.json 与 SHA256SUMS 覆盖全部附件(README/manifest 本身不自我
  hash)。

## 5. 异常/准备修正

无:全部执行第一遍完成,无超时重试、无源码/断言修补;基线 52 红全部为
预期行为红(坏案在修前基线被错误接受),2 绿为合法正控;G01 输出目录为
全新 tmp,控制器拒绝已有输出目录。

## 6. 安全复现(只在新仓外 tmp;禁止在永久证据目录原地执行)

```bash
PY=/Users/cc/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
# 当前源 PPV1 全量 + r2 新回归 + 崩溃/并发/预算矩阵
PYTHONDONTWRITEBYTECODE=1 "$PY" -B -m pytest "$REPO/tests" \
  -k "ppv1" -p no:cacheprovider -q
# G01(白名单同 r1/r2;输出须为不存在的新目录)
PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$REPO/docs/review_evidence/\
ppv1_s3_impl_2026-10-07/s3a_r2/scripts/safe_g01_s3a_r2.py" \
  --repo "$REPO" --out /private/tmp/ppv1_s3a_r2_g01_NEW --python "$PY" \
  --r7-path-manifests "$REPO/docs/review_evidence/ppv1_r7_codex_2026-10-07/\
storage_specialist"
# 基线红绿(自行建 detached worktree 并复制同字节测试输入)
```
