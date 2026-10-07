# S3a 批次(持久搜索底座)实施证据(2026-10-07,r1 轮)

交付书:[S3a 交付](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_DELIVERY_2026-10-07.md)。任务书:[S3 实施任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md)(未跟踪评审侧产物,只读)。实际 HEAD `00e509a974b40a7cf35e53b16637a13d60`(=开工基线;实施期间工作树含本批未提交变更,G01 记录 dirty 状态)。

**范围:S3a 持久搜索底座(身份/预算/认领/恢复/停止原因);S3b 未交付;`workflow.runner` 对 PPV1 双入口继续 fail-closed。** 本目录为实施方证据(非复审方独立执行);复审按 AGENTS 自动循环另行独立核。

## 结果摘要(工程契约,合成规则级夹具,不外推任何题域科学性能)

- PPV1 全量 23 文件:**594 passed / 0 skipped**(536 存量 + 58 S3a 新增;`ppv1_current/pytest_full_output.txt`)。
- 基线 00e509a detached worktree 同字节红:**2 行为红**(test_ppv1_profile.py 的 profile-9/search-limits-3/delivered_stages 断言)+ **2 文件 collection 红**(pollutant.search 缺失,58 用例未执行)—— 缺实现红与行为红分类分开,不以 collection 红冒充行为翻转(`baseline_red/` + `red_green_worktree_log.md`)。
- G01 安全隔离(新控制器 `safe_g01_s3a.py`,R7 路径白名单 + R8/S3a 新输入,fresh hash + 实际 HEAD + dirty 记录):**1196 passed / 8 skipped / 17 deselected,exit 0,194.8s**(`g01_safe_isolation/`)。8 skip = 5 真实评价依赖 + 1 v4 对照源 + 2 phase_d 派生 metadata(逐 nodeid 见执行结果);17 deselect = 16 slow + 1 明确排除 export 用例。R7 历史 1110/8/17、R8 历史 1138/8/17 单列不混计。
- 修后全绿对照:同批文件当前树 594 绿(见上)。

## 文件布局

- `safe_g01_s3a.py`:本批新 G01 安全隔离控制器(沿 R7/R8 白名单纪律:普通 src/tests/configs/scripts/assets + 普通 dependingv3/src 42 文件 + 本仓 18 非题面反应资产镜像;不复制 .git/reports/data/evaluation/benchmark/gold/封存/v4;固定 PYTHONPATH/空 BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT)。`--out` 必须是仓外新目录;禁字节码/pytest cache;只在 tmp 执行,不在本永久目录跑会写库/日志的探针。
- `g01_safe_isolation/`:preparation.json(实际 HEAD/dirty/命令/env/白名单来源)、input_sha256.json(全部输入 fresh SHA-256)、execution_result.json(exit/耗时/skip 行/summary 行/stdout+stderr hash)、g01_safe.stdout.txt / g01_safe.stderr.txt(完整输出)、controller_stdout.json / controller_stderr.txt(控制器自身输出)。
- `baseline_red/`:基线红两份完整日志(collection 红 + profile 行为红)。
- `ppv1_current/`:修后全量绿完整日志。
- `red_green_worktree_log.md`:worktree 创建/清理命令、红分类(行为红 2/缺实现红 58/基线绿 21)、环境(python 3.11.16 / rdkit 2026.03.6)。
- `mimo/`:v8 请求快照(替换前原文)与 v9 送审快照(送审轮序由主会话执行;旧回应 r5–r8 原样在 docs/ 不覆盖)。
- `manifest.json`、`SHA256SUMS`:本目录全部附件 hash(外层两份清单不自 hash)。

## 复现(安全口径;每个 --out 用全新 tmp,禁止在永久目录原地执行)

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_impl_2026-10-07/s3a_r1/safe_g01_s3a.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_s3a_g01_new_replay \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

PPV1 全量与基线红的命令见交付书 §10;基线 worktree 用后即清(记录在 red_green_worktree_log.md)。本控制器记录的是 fresh hash + 当前 HEAD(00e509a + 本批工作树 dirty 状态)—— S3a 提交后 HEAD 变化时,需按实际 HEAD 重跑或显式登记漂移,不以本日志冒充提交后执行。

无金标/题面/封存逐题 run/外部模型调用/真实付费请求;合成 SQLite 与 artifact 只写新 tmp;判分零 LLM。
