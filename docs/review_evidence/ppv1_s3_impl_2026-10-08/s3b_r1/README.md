# S3b 批次(s3b_r1)实施证据 — 2026-10-08

- 仓库:`/Volumes/CC/Enzyme_Agent/dependingv43`;实施时实际
  HEAD(=直接父,本批变更待本地提交):`b7f2bba02ca49edd0a45a13bc9b8434909d99175`
  (S3a 回修 r4,S3a 复审 R4 放行基线)。
- 批次:S3b(S3 第二批 = 完整 S3 收尾批)—— 队列选择/两类
  deferred 激活/条件依赖与显式场景转换进调度、`proposals[]` 模型
  协议与有界格式反馈、固定 AtomTool→供体诊断→converter→audit→
  admission→事件提交生产调用链、PPV1 独立 runner start/resume 分流。
- 判据未冻结;本目录全部为**工程合成规则级**契约证据(CCO →
  CC=O 编辑协议夹具),不代表 dev(B1 环境中间步骤)或 298(RHEA
  通用酶学)科学性能;判分零 LLM;零金标/题面/封存 run/dependingv4
  访问;真实 provider 网络发送恒 0(max_real_model_requests 默认 0,
  scripted/fake 恒 network_request_count=0)。

## 目录

- `current/ppv1_full/`:当前源 PPV1 全量(31 文件=26 存量+5 新;
  junit+summary)。**851 passed / 0 skipped / 0 failed**,exit 0,
  pytest 16.04s(787 存量 + 64 新 S3b)。
- `current/s3b_new/`:仅 4 个新 S3b 测试文件(64 passed;junit)。
- `baseline/`:直接父 b7f2bba detached worktree 同字节红绿对照
  (worktree 建立/清理日志、junit、summary、
  `failure_classification.json`):
  - 同字节更新的 2 个既有文件(`test_ppv1_profile.py`、
    `test_ppv1_s3a_search.py`):**4 failed / 64 passed** —— 2 个
    版本字面量行为红(profile-12→13/search-4→5 断言)+ 2 个 runner
    分流翻转行为红(基线旧代码对 PPV1 拒绝 ⇒ "未发生预期分流"
    红;S3b 有意行为翻转,非旧错误行为);
  - 4 个新 S3b 测试文件:**4 collection errors**(`pathway_v43.
    pollutant.queue/model_protocol/production/runflow` 模块缺失;
    新 API 缺失造成的 collection 红,不称旧行为红,无逐测试结果);
  - 正控绿 = 未改动断言 64 passed(r4 交付的 787 全量在其原文件,
    本对照只跑同字节更新的 2 文件)。
- `g01/`:安全隔离 G01(controller = s3a_r4 控制器适配 S3b 输入)。
  **286 输入**(277 r4 输入 + 9 个新增:4 新 src 模块(queue/
  model_protocol/production/runflow)+ 4 新测试 + s3b_worker.py;
  runner.py/profile.py 为 277 内已有路径的更新副本,非新增;原件与
  隔离副本 SHA 一致;
  fresh hash,实际 HEAD+脏状态记录)。**1453 passed / 8 skipped /
  17 deselected**,exit 0,pytest 202.40s(1389 r4 基线 + 64 新
  S3b)。缺席/排除逐项:
  - 8 skip = 5 真实评价依赖(test_batch_runner:52;
    test_score_report:110/163/172/184)+ 1 v4 对照
    (test_analog_assets:95;dependingv4 未复制)+ 2 phase_d 派生
    metadata(test_analog_v2_corpus:62/153);
  - 17 deselect = 16 slow + 1 显式排除
    `test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_\
    neutralization_forbidden`;
  - 历史 R7 1110 / R8 1138 / S3a 首批 1196 / r2 1250 / r3 1299 /
    r4 1389 各自单列,不混计。
- `scripts/`:`safe_g01_s3b_r1.py`(G01 控制器;复制到新 tmp 执行,
  永不在本目录原地跑)。
- `mimo/`:v12 请求送审快照(字节同仓内 v12;本批将其升级 v13,
  回应由主会话按通道落盘,不入本批)。
- `code_identity_after.txt` / `runner_py_hashes.txt`:共享
  `workflow/runner.py` 变更的身份影响披露 —— legacy code_identity
  聚合由 r4 的 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591be
  ccbff2507c29ae` 变为 `18007e6a7cc239606eb30921f91045540446a7d7298
  108be30d47fce2f1374d6`(旧 run 跨此代码变更的 resume 按既有身份
  门槛拒绝,是设计行为;legacy 运行时行为零改变——legacy 全量回归
  于 G01 内保持绿)。
- `run_meta.txt`:实际 HEAD/父、Python 3.11.16 / RDKit 2026.03.6 /
  SQLite 3.53.4、契约版本(profile-13/search-5/store-9/
  search-limits-3/format-feedback-1)、本批脏文件清单(AGENTS.md
  用户差异不纳入提交,单列保留)。

## 复现(安全命令;均在新 tmp,不在本目录原地执行)

- PPV1 全量:`PYTHONDONTWRITEBYTECODE=1 <depending43 python> -B -m
  pytest -p no:cacheprovider -q tests/test_ppv1_*.py
  tests/test_ppv1_s3b_*.py`(仓库根)。
- 基线对照:`git worktree add --detach <tmp> b7f2bba` 后复制同字节
  测试文件再跑(本目录 worktree_add.txt 记录建立/清理)。
- G01:`python -B scripts/safe_g01_s3b_r1.py --repo <仓库> --out <新
  tmp> --python <depending43 python>`。

## 异常/早停说明

- 首次 G01 运行因控制器输入清单拼接缺陷(新 S3b 输入未进复制
  清单)得到 2 failed(runflow 缺失的 ModuleNotFoundError),已修
  清单后完整重跑为 1453 绿;首次输出目录已删除,不以失败运行充当
  证据(本条如实登记)。
- PPV1 套件内 0 skip(s3b runner 四崩溃参数化中 B2 子进程用
  `--with-model` 实跑,不 skip)。

## 清单

- `manifest.json` + `SHA256SUMS`:覆盖全部附件;只有外层清单不自
  我 hash。合成 SQLite 数据库二进制不入永久目录(执行事实以 junit/
  stdout/JSON 转存)。
