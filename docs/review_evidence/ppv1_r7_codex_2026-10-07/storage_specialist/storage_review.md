# R7 独立存储复审与隔离回归记录

日期 2026-10-07；锁定 HEAD `858dd94c7c6c8fc387940242403d67b6b36b5313`；父/对照 `6d9020130a481866ce2f3b79933907a33d8cfc9e`。限 R6 报告 §3 R6-04/05、§6/§7；不新增跨阶段门。主仓只读，文件均新 tmp；无外部模型、真实金标、题面、封存逐题 run 或 dependingv4 访问。

**裁定：R6-05 关闭；R6-04 原 `states=[]` 四反例修复，但同契约的“显式再次提供有效状态载荷，复用已损坏的同 hash 出现行”仍 P1。** 不把该入口再拆成新的两组问题。

## 1. 首提入口矩阵及实证

全部先 public `put_state` 合法 CCO（sub-A）和 CC=O（prod-A），损坏只在新建合成 SQLite：改 prod 出现载荷 `source_refs`，原 `(state_id, appearance_hash)` 和语义状态行不动；调用者持有的原有效状态载荷不动。首提 public submit，成功则紧接 `states=[] / hypothesis_dict=None` public replay。

| 首提提供的 states | 未损坏正控 | 同 hash 出现行已损坏 | 即刻无输入重放 |
| --- | --- | --- | --- |
| 空 | created=True；重放 created=False | 首提 appearance_hash_corrupt、零写入 | 不进入重放 |
| 只明确提供 prod 原有效载荷 | created=True；重放 created=False | **首提 created=True** | appearance_hash_corrupt；不补账 |
| 明确提供 sub/prod 全有效载荷 | created=True；重放 created=False | **首提 created=True** | appearance_hash_corrupt；不补账 |

两个错误首提都实际增加 events=1、report_projections=1、expansion_plans=1、event_appearance_links=2；状态/出现旧损坏未修复。这里不是“传入错载荷”、不是要求全库防伪，而是首提选中并链接已有相同 `(sid, hash)` 的损坏权威记录，随后重放明确诊断同一记录损坏。R6 对状态 CN/schema/inner ID 的 states=[] 三反例也都首提拒绝且零新增。

在 R6 源码对照上，空/只 prod/全状态三种损坏首提均 created=True；三个合法正控均正常。故 R7 的空输入修复应认可，同时显式提供路径未闭合应继续列原 R6-04。

**源码根因：**

- `src/pathway_v43/pollutant/store.py:1602–1607` 以 `reuse_refs = derived_refs - supplied_sids` 排除本次明确提供的 SID，已存 appearance 校验仅执行于剩余引用。
- `store.py:993–1012` `_collect_state_writes` 验证输入状态及已有 semantic 一致，不验证已有同 hash 出现载荷。
- `store.py:1768–1774` `INSERT OR IGNORE state_appearances` 碰到相同键就保留原坏行，后续 event/links 仍持久化该 hash。
- `store.py:1492–1494` 重放无论 caller 是否重复提供，仍 `_verify_stored_appearances`，因此第一次和第二次消费判据不一致。

**有限补修：**首提在任何写入之前，对将实际复用的已有 state/appearance 行统一校验；“本次带了有效载荷”不能免除同键已有权威出现行的内容/hash 校验。损坏应 Ppv1LedgerCorrupt、事件/投影/计划/links 零新增，不自动修行；保留全新载荷、合法先存、部分先存、同图多来源、排序/重放幂等。无迁移、来源真实认证或完整机制要求。

## 2. 完整出现集合

新表 `store.py:219–225`，首提同源持久 `:1805–1811`，重放双向集合校验 `:1297–1335/:1502–1505`。

独立 6 控制：正常三项（底物+同 SID 的 A/B）重放 False；删 manifest A 留 B、删 manifest+实际 A、仅删 link A 均 link_corrupt；保持 manifest 只删实际 A 仍 entry_missing；只倒序 manifest 仍合法幂等，三 links 保留。所有拒绝重放都零写入。完整 distinct occurrence 集合通过独立持久源核验；不要求抵抗一致重造整本账本。R6-05 可关闭。

## 3. 回归有效性与交付说法

R7 storage 新 12 项有效检验 R6-04 的四个空 states 首提反例，以及 R6-05 多来源与各单点删除形状。`tests/test_ppv1_r7_storage.py:133–154` 出现损坏首提只测 `states=[]`；`:176–188` 的“部分先存/显式 states”正控先存的是 sub、prod 全新，并没有触发“同 SID/同出现 hash 已存并损坏，再明确提供 prod”分支。该缺失不是因测试数少而制造阻塞，而是独立公共链已实际确认错误首提。

已有 5 文件版本串 -6→-7 为机械升位；r6_chem violation 断言改为数值类与许可类分形，同时保留数值披露并加入许可身份断言，未见用改预期抹平存储故障。PPV1 508 passed 不代表入口矩阵闭合。

交付 §2 R6-04 “四例损坏首提即拒”针对原空输入成立；“五组全部按统一入口收口”的总体表述对显式复用同 hash 出现不成立。G01计数与数据访问纪律另见下一节，不能用测试数量背书无金标访问。

## 4. 独立 PPV1 与 G01 安全隔离执行

使用 depending43 Python、`-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest `-p no:cacheprovider`。复制源码含 vendor/必要 metadata、tests、pyproject、configs/scripts及明确非题面非金标的反应模板/索引/ranker/manifest；不复制 reports、data、evaluation、dependingv3/dependingv4、真实评价基准。不运行模型。

- PPV1：**508 passed /0 skipped**，3.97s，1 文档转义 warning，exit 0；完整 stdout/stderr 已保存。
- G01 原命令 `pytest -m "not slow" tests/` 在上述安全副本：**2 failed /1099 passed /18 skipped /16 deselected**，87.34s，1 warning，exit 1。两 fail 是未标 slow 的 `test_batch_dev` 并行屏障/崩溃控制，worker status 明确 `EngineBootstrapError: v3 引擎目录缺失`，属隔离依赖缺席，不能当 PPV1 源码回归。

18 skipped 精确原因（完整原文在 stdout）：v3 源码夹具 10（asset_manifest 1、asset_root_isolation 7、cli 1、export_v3 纯函数 1）；v4 parser 对照 1；未复制 phase_d provenance/summary 2；真实评价基准 5（batch_runner 1、score_report 4）。总计 1099+2+18=1119 选中项，另16 slow deselected。不能称为独立复跑 1119 全通过。

**G01与本次纪律冲突的具体链：** `tests/test_score_report.py:33–36` 唯一 module skip 条件是原 v3 evaluator 文件缺席；`:115–119/:189–193` 未标 slow 的测试直接读 `dependingv3/evaluation/pathway_benchmark/gold_routes.jsonl`，`:145` 调冻结评测器。`tests/test_batch_runner.py:52–58` 唯一 skip 条件是 split_manifest 缺席，调用 `batch.build_input_manifest`，`src/pathway_v43/batch.py:176/:198/:225–226` hash/读取真实金标原文件。不得为凑完整数字恢复这些目录。

第二遍消除已知源码环境缺席：仅只读复制 `dependingv3/src`；临时 `dependingv3/assets` 物理镜像已隔离的 `v43/assets/v3_reactions`，不读原 v3/assets，`BBD_DATA_ROOT` 固定新 tmp 阻断外部数据缓存。仍不复制/读取 evaluation、题面、金标或 dependingv4。由于 `test_export_v3.py:435` 只以 v3/src 存在作 skip 条件，源码补齐后其 `:426` 会加载未复制的 evaluator 脚本，本审明确 `--deselect tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`，不补评价目录。

最终安全 G01：**1110 passed /8 skipped /17 deselected**，222.45s，1 文档 warning，exit 0、stderr 空；原两项 batch 失败及 v3 源码夹具均已通过。8 skipped 精确为真实评价5（batch_runner1 + score_report4）、v4 parser对照1、未复制 phase_d provenance/summary2；17 deselected=16slow+额外的上述纯 evaluator 函数1。总选中口径 1110+8+1=1119；这是具有明确数据边界差异的独立执行，不能冒称1119全通过。

R7 交付的 1119 passed/16 deselected 为外部声明（用户转发已由主会话证实），本复核未按其环境重复金标读取。交付 §4 的“未访问金标/题面”与该套当前测试全 1119 passed/0 skip 按现有源码不能同时成立；本审不替外部执行背书该纪律声明，不据此另加架构 P1。

## 5. 永久证据候选

scratch `/private/tmp/ppv1_r7_storage_e5U2uF/`：`storage_contract_probe.py` 为自包含公共链合成输入；当前 JSONL 15 cases+1 metadata；R6 对照 9首提cases+2 metadata（v6无links表的显式说明）；`storage_assert_observed.py` 对当前15观察逐条验收，含当前残余“首次成功、重放报坏”的断言，**不是修后验收**。stdout/stderr完整；commands/identity/input_hashes/runtime/SHA将与主审核证据收录。最初仅一处夹具输出调用错用 event.to_dict 导致脚本停止，已改 dataclasses.asdict；初次 stderr 单独保留，最终 15 cases 完整执行 exit 0，不把停止后的控制算通过。
