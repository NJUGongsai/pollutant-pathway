# 交付书：S5b 池层逐候选谱系诊断 T1a（2026-10-12）

> 实施子代理照任务书 `docs/TASK_S5B_POOL_LINEAGE_T1A_2026-10-12.md` 执行完毕。
> 实际 HEAD 基准 = `dbc71ca5`（本任务改动全部留在工作树，**未 commit 未 push**，
> 待主会话核对）。工作树另有一份**先前任务**的未提交改动
> `src/pathway_v43/pollutant/s5b_orchestrator.py`（s5b-orchestrator-3 HPC
> 分片，非本任务产物，本任务零触碰）——主会话核对提交构成时请区分。

## 一、改动清单（5 文件）

| 文件 | 性质 |
|---|---|
| `src/pathway_v43/pollutant/s5b_builder.py` | 唯一源码改动（净 +92 行）：①`S5B_POOL_POLICY_VERSION` s5b-pool-policy-5→6（版本注释按 house style 登记升版理由）；②provider 内加逐候选行基础设施（`candidate_rows`/`row_by_spec`/`_diag_row`/`_signature_head`；行不进 spec 本体，经 spec 对象 id 关联，池载荷零污染）；③三通道候选产出点各插一行记录（recorded :545 附近 / corpus :575 附近 / analog 含 pregate 与编译失败点）；④去重循环回填 `merged_into`+`merged_into` key（与幸存者 `merged_source_keys` 同点留痕）；⑤截断段回填 `pool_rank`（1 基）与 `pool_truncated`；⑥`diagnostics` 追加 `candidates` 键（空池路径补 `candidates: []`）；⑦docstring 登记。**排序/去重判据/截断位置/失败补位/控制流零变化** |
| `tests/test_ppv1_s5b_pool_lineage.py` | 新测试 8 件（任务书 §6 矩阵全覆盖，见 §三） |
| `tests/test_ppv1_s5b_hit50_v4b.py` | 版本字面量断言 policy-5→6（1 处，随轮披露，非静默：断言上方附 T1a 注释） |
| `tests/test_ppv1_s5b_hit50_v4_wv41.py` | 同上（2 处：`test_wv41_semantics_frozen_and_versions_registered`、`test_wv41_pool_corpus_appended_after_eawag`） |
| `tests/test_ppv1_s5b_cosub_d2.py` | 同上（1 处 `test_d2_versions_registered`；docstring 同步登记升版链） |
| `tests/test_ppv1_s5b_hit50_w23456.py` | 同上（1 处 `test_versions_registered`） |
| `tests/test_controlled_vocab_ci.py` | F3 词表 CI 契约收口：`REGISTERED_LITERAL_SINKS` 登记 `("s5b_builder.py", "recorded")`（candidates 行 channel 自变量新写入 src 的受控词字面量；corpus/analog 非受控词；同词先例 native_export/provenance/search 等已登记） |

未触碰（零 diff）：runflow / production / queue / store / 判分侧
（s5b_scoring.py / evaluation.py）/ `EDIT_PROTOCOL_VERSION` /
`ATOMTOOL_VERSION` / `CORPUS_RETRIEVAL_VERSION` / `S5B_BUILDER_VERSION`
（维持 s5b-builder-1）/ run_inputs 生成逻辑。

## 二、行 schema（实现与定稿 §3.1 逐字段一致）

```json
{"channel": "recorded|corpus|analog",
 "record_key": "<EAWAG/corpus 行级定位键；analog=tpl key>",
 "outcome": "compiled|compile_rejected|merged_into|pool_truncated",
 "reason": "<仅 compile_rejected 非空：拒因短码>",
 "merged_into": "<仅 merged_into 非空：幸存 spec key>",
 "pool_rank": "<compiled/pool_truncated 有：截断前排序位，1 基>",
 "signature_head": "<仅 compiled 非空：净反应签名前 4 token>"}
```

- 定位键：recorded=候选 `record_id`（spec key=`rec-<rid>`）；corpus=候选
  `record_key` 行级键（spec key=`rec-<record_key>`）；analog=tpl key。
  全部与幸存者 `merged_source_keys` 的 key 规则可互定位（闭合 join）。
- null 位次严格按 outcome（schema 字面执行：`signature_head` 仅 compiled
  非空，merged/truncated 行置 null）。
- 与聚合计数天然闭合（设计性质，非附加逻辑）：`compile_failure_histogram`
  每 reason 计数 = 同 reason 行数；`merged_source_keys` 总条数 =
  merged_into 行数；`n_unique_net_reactions` = compiled+pool_truncated；
  `n_pool_returned` = compiled。

## 三、测试（三层实际数字）

解释器：conda env depending43（仓内无 `.venv`，沿任务书排障指引）。

| 层 | 数字 |
|---|---|
| 定向 `tests/test_ppv1_s5b_pool_lineage.py` | **8 passed / 0 failed**（正控 4：三通道 compiled 行、compile_rejected+直方图闭合、merged_into+merged_source_keys 闭合（含跨通道合并）、pool_truncated+计数闭合；不变量 3：manifest 白名单消费（worker `manifest_provider_kind` + 判分 `score_s5b_batch` 合成 scope 实际跑通）、run_inputs 字节等价+诊断不进 run_inputs、版本 =s5b-pool-policy-6；负控 1：聚合键集零变化+行 schema 七键精确+四态 null 位次+聚合闭合） |
| 相关既有（w23456/runtime/score_report/v4b/wv41/cosub_d2/v3_wv3） | **141 passed / 0 failed** |
| 全量 `tests/ -m "not slow"` | **2098 passed / 0 failed / 16 deselected**（406s） |

全量 2098 对基线 2061 的 +37 构成：本任务新测试 8 + `dbc71ca5`（F3 词表
CI，2026-10-11）引入 17 + 既有未跟踪 `tests/test_ppv1_s5b_shard.py` 12。
（第一遍全量曾 1 红：F3 词表 CI 发现新字面量 `"recorded"` 未登记，按其
自身契约登记后全绿——见 §一最后一行，随轮披露。）conftest 仓外依赖
skip 面与基线一致（16 deselected）。

## 四、字节等价探针（红线 3：全部新 tmp，零写入封存目录）

**Probe B（全 build 路径；合成 2 题×真引擎，before=父 HEAD 隔离
worktree `dbc71ca5` / after=工作树，双根资产同源只读）**：

- `run_inputs/*.json` **逐字节一致**（2/2 sha256 相同；目录字节
  27909 = 27909）；
- 两批根全部产物中**唯一差异文件 = `batch_manifest.json`**；
  差异面 = `entries[].pool_diagnostics.candidates`（新键追加）+
  `pool_diagnostics.pool_policy_version` 值（-5→-6）；其余键
  （reference_graphs / split_manifest / manifest 其余字段）逐字节相同。

**Probe A（真实 298 题；provider 级，底物只读封存批根
`reports/ppv1_s5b/s5b_298_local/run_inputs/` 的 `substrate_smiles`
批准字段，沿 v4b §五先例；before/after 同脚本双跑）**：

- **298/298 逐 qid 池 spec 序列 sha256 一致**（= run_inputs
  plan.pools 冻结面字节不变）；
- **298/298 既有聚合诊断字段逐键全等**（shared keys 0 差异）；
- after 独有诊断键 = `{"candidates": 298}`（恰一键、每题在位）；
- 版本对 = (s5b-pool-policy-5, s5b-pool-policy-6)，恰为预期。

## 五、父 HEAD 红绿对照（隔离 worktree `dbc71ca5`）

| 组 | 结果 |
|---|---|
| 新测试 8 件 | **7 红 / 1 绿**。红因分类：5×`KeyError: 'candidates'`（行为红：新字段父上不存在；compiled/rejected/merged/truncated/manifest 兼容四件+负控键集红 1）+1×版本字面量红（`'s5b-pool-policy-5' != 's5b-pool-policy-6'`）。绿 1 = run_inputs 字节等价（父上本无诊断字段，等价平凡成立） |
| 既有 6 文件（含 4 个被改断言文件+runtime+score_report） | **恰 5 红 = 5 处版本字面量断言**（v4b_versions_registered / wv41_semantics_frozen_and_versions_registered / wv41_pool_corpus_appended_after_eawag / d2_versions_registered / w23456_versions_registered），128 passed / 4 skipped，**零行为翻转** |

## 六、candidates 行数分布与 manifest 增量（真实 298 实测）

| 项 | 实测 |
|---|---|
| 每题行数 | min **0** / median **17** / p90 35 / max **52**（总计 5551 行） |
| 行四态 | compile_rejected 5316 / compiled 182 / merged_into 53 / **pool_truncated 0**（真实 298 池深 max 4 < 池宽 8，截断态仅合成测试覆盖；min=0 = 空池题如实 `[]`） |
| 诊断面增量 | canonical JSON 字节 2,942,340 → 4,023,280 = **1.367×** |
| 全 manifest 增量（Probe B 合成 2 题样本） | 22,923 → 34,805 字节 = **1.518×** |
| 墙钟 | 双探针检查点逐点相同（200/298=1013s、250/298=1155s 两侧一致）——附加开销低于该粒度计时分辨率 |
| 结论 | 均 **≪ 5×**，未触发任务书 §3.1 规模裁定点，无需截断规则 |

## 七、已知限制（如实披露，不修）

1. **decide 层 prepare 失败仍整 run 级失败**（`runflow.py:870` 无逐条
   容错）：池 spec 在 decide 侧 prepare 失败只有 case 级
   failure_kind 可见，该丢失点无逐条记录——任务书 §3.5.5 指定披露，
   本任务不改该行为；
2. `signature_head` 仅 outcome=compiled 行非空（定稿 schema 字面执行）；
   merged/truncated 行凭 `record_key`+`pool_rank` 定位；
3. `row_by_spec` 以 spec 对象 id 关联（行不进 spec 本体=池载荷字节零
   污染的代价；编译成功行与 spec 一一对应由同点插入保证，取行是
   防御性 get）；
4. 真实 298 数据不含 pool_truncated 态（见 §六），该态正确性由合成
   测试（max_pool=2 夹具）覆盖；
5. 判分兼容性证据 = 白名单消费机制确认（scoring 只取
   registration_order/entries 白名单字段）+ 合成 scope 判分实际跑通
   （专项测试 + Probe B）；`data_scope=real` 全量判分未点火（零模型
   边界，与本轮无关）。

## 八、红线自查

| 红线 | 结果 |
|---|---|
| 判分侧零污染 | s5b_scoring.py / evaluation.py 零 diff；新 manifest 经 worker+判分实测正常消费（§三定向不变量件） |
| 金标/题面零触碰 | 未读 `reference_graphs/` 内容与金标 tsv；真实探针只读封存 run_inputs 的 substrate_smiles 批准字段（v4b §五先例）；build 产物（reference_graphs 等）只写 /tmp 新批根 |
| 封存 run 只读 | 零写入封存目录；全部探针/证据在 `/tmp/s5b_t1a_lineage/` |
| export_digest 零影响 | 未动 facts 表/artifact payload；诊断只进 batch_manifest entries（builder 面不进 store） |
| 不 push / 零模型 / 零网络 | 全程本地零调用零花费；改动留工作树未 commit |

## 九、证据路径（`/tmp/s5b_t1a_lineage/`）

| 文件 | 内容 |
|---|---|
| `probe_smoke_lineage.py` | 三通道合并驱动冒烟（行 schema/闭合/判分消费首证） |
| `probe_real_build_ab.py` | 真实 298 before/after provider 探针（src_root 参数化） |
| `probe_full_build_ab.py` | 合成题全 build before/after 字节探针 |
| `join_ab.py` / `join_report.json` | 298 逐 qid join 比对与结论 |
| `real_before.json` / `real_after.json` | 双侧全量逐 qid（池 sha+全诊断；含 5551 行 candidates） |
| `fullbuild_before/` `fullbuild_after/` | 全 build 双侧批根+`*_summary.json`（文件级 sha256 清单） |
| `before_stderr.log` / `after_stderr.log` | 探针运行日志（版本、进度、墙钟检查点） |
| `wt_before/` | 父 HEAD 隔离 worktree（`git worktree`，红绿对照执行地；内含按轮拷入的新测试与被改测试文件副本） |

## 十、回传义务对照（任务书 §8）

1. 改动清单 → §一；2. 三层测试数字 → §三；3. 字节等价 → §四；
4. 父 HEAD 红绿 → §五；5. 行数分布+manifest 增量 → §六；
6. 本交付书（含 §七已知限制）；7. 证据路径 → §九。
