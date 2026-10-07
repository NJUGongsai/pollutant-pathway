# S3a-r4 回修实施证据(Codex 复审 R3 残余三组 S3A-02/03/04)

日期:2026-10-08(Asia/Shanghai)。实际 HEAD(交付时):见
`meta/head_status.txt`(工作树含本轮未提交交付物;提交哈希见交付书
§8)。直接父:`41d0cd55f3def050a62325f00235cf22da302d2e`。

范围:只修三组残余(S3A-02 必要预约集合完整性 / S3A-03 请求状态口
接冻结策略 / S3A-04 非法来源状态不能改记合法 failed);S3A-01/05
与已证行级旧反例保持关闭;不实施 S3b。交付书:
`docs/POLLUTANT_PATHWAY_S3A_DELIVERY_R4_2026-10-08.md`;复审报告:
`docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R3_2026-10-08.md`(其永久
证据只读,本轮反例输入同构复现于本目录探针)。

## 数字与执行入口(全部 depending43 Python 3.11.16 / RDKit
2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、-B、
pytest -p no:cacheprovider;执行全部在仓外新 tmp)

| 执行 | 结果 | 证据 |
| --- | --- | --- |
| PPV1 全量(26 文件) | 787 passed / 0 skipped / 0 failed(697 r3 存量 + 90 r4),exit 0 | `current/ppv1_full/` |
| r4 新回归(当前源) | 90 passed,exit 0 | `current/rework_r4/` |
| 四崩溃/H06 barrier/H07 H08/零预算/悬空请求矩阵 | 23 passed,exit 0 | `current/crash_barrier_budget/` |
| r4 有限探针(复审反例矩阵同构 + 前后完整 14 表) | 89/89 contract_passed(63 S3A-02 + 21 S3A-03 + 5 S3A-04),exit 0 | `current/probe/`、`current/probe_stdout.jsonl` |
| 父 41d0cd5 detached worktree 同字节 r4 新回归 | 78 failed / 12 passed / 0 collection error(77"未发生指定异常"+ 1 形态缺报告键) | `baseline/rework_r4/`(JUnit + failed_nodeids + 逐案分类) |
| 同基线更新既有测试(profile 副本) | 1 failed(版本字面量)/ 22 passed | `baseline/updated_existing/` |
| 安全隔离 G01(r4 控制器,277 输入) | 1389 passed / 8 skipped / 17 deselected,exit 0(= r3 1299 + 90) | `g01/` |

G01:R7 路径白名单 216 + 普通 dependingv3/src 42 + 本仓普通资产
镜像 18 + r4 新测试文件 1;8 skip = 5 真实评价 + 1 v4 对照 + 2
phase_d;17 deselect = 16 slow + 1 显式排除(逐 nodeid 见
`g01/deselected_nodeids.txt`);零金标/题面/封存 run/v4/真实
provider,网络 0;数字不外推 dev/298 科学性能。

## 目录结构

- `current/`:当前源执行(ppv1_full、rework_r4、crash_barrier_
  budget、probe + probe_stdout.jsonl;各含 stdout/stderr/JUnit/
  run_meta,argv/env/exit/耗时实记);
- `baseline/`:父 41d0cd5 detached worktree 同字节执行(rework_r4
  含逐案分类与 failed_nodeids;updated_existing;test_input_hashes
  双向 SHA);
- `g01/`:安全隔离 G01(preparation/input_sha256/execution_result/
  junit/stdout/stderr/deselected_nodeids/run_meta);
- `scripts/`:`safe_g01_s3a_r4.py`(r3 控制器适配 r4 输入)、
  `s3a_r4_probe.py`(复审反例矩阵同构探针,前后完整表);
- `mimo/`:v11 送审快照(字节同仓内 v11 请求);
- `meta/`:worktree add/remove、head_status、runtime(实际版本 +
  legacy code_identity 聚合不变)。

## 完整性

`manifest.json`(全附件清单,不含自身与根 SHA256SUMS)+
`SHA256SUMS`(覆盖全部附件含 manifest 本身;嵌套 g01/input_sha256
等也覆盖)+ `manifest.sha256`(manifest 自身哈希)。探针数据库
留在仓外 tmp(逐案 SHA/大小见 `current/probe/omitted_databases.
json`),不入永久证据。所有执行不在永久目录原地跑会写库的脚本;
不改历史证据/manifest。

不访问真实金标/题面/封存逐题 run/dependingv4,不真实 provider/
网络/外部模型,判分零 LLM;不宣布判据冻结、科学性能或 S4/S5
完成;S3b 未交付清单见交付书 §6。诚实残留(含 cache_hit 检索
ref+row 同删与合法 cache_hit 同构、并发窗口、foreign-run 扫描
作用域)见交付书 §7。
