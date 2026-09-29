# v4.3 EC298 Phase D 复测原始 run 复核任务书（Chenyu）

> 状态：待执行。任务性质：**零 LLM、只读取证与独立重算**。本书要求到 Chenyu 直接复查 C0、D-3 两臂的原始 run；现有报告和仓内派生表仅作为待核对主张，不可充当唯一证据。通道、凭证纪律及路径变更处理见 [CHENYU_ACCESS.md](CHENYU_ACCESS.md)。

## 1. 目标与边界

复核 [Phase D 复测报告](EC298_PHASE_D_RETEST_REPORT.md) 的完成性、身份隔离、原始响应、产物来源、计分、并发与费用主张。尤其确认仓内派生表的错误是否仅限元数据，是否影响原始 run 或报告结论。输出逐项可回查的证据和差异清单，不能只写“脚本跑通”。

- 远端项目根：`/usrdata/EnzymeCAGE_data/workspaces/dependingv43`；原始臂：`runs/ec298_pd_retest_C0/`、`runs/ec298_pd_retest_D3/`；引擎：`runs/ec298_pd_retest_engine/`；烟测：`runs/ec298_pd_retest_smoke/`。
- 金标仅供**隔离的离线评分**：`/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl`。不得复制入两臂运行目录、任务载荷、prompt、日志或仓库交付物。
- 不重跑 agent、模型、引擎或烟测；不调用付费 API；不改原始 run、旧报告、旧派生表、封存清单、批次身份、远端金标。所有新输出写到独立目录，禁止把审计脚本的 `--out-dir` 指向原始 run 或现有 `scoring/`。
- 开工记录本地与远端 `HEAD`、工作树状态、审计时间、工具版本和实际读取路径；保护现有未提交文件。若 Chenyu 不可达或原始文件缺失，按证据缺口报告，不以本地副本冒充远端实核。

## 2. 基线主张与冻结锚

下表是**待验证值**，不是审计输入真值。远端逐文件重算 SHA；对照仓内副本和注册档，记录不一致项及其影响。

| 项 | 待验证值 |
|---|---|
| C0 / D-3 批次身份 SHA256 | `31549aab3db5fd2ef832996d5622d80ec8e17984e5b32e19a966455ac3b42df8` / `cfe1534a93d7fe1596f997272cb2e3260001f0861ecd4d66f286c6e99b2495b4` |
| 白名单输入 / 金标 SHA256 | `cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703` / `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` |
| 代码聚合 / 资产清单 SHA256 | `07fef84f0945bcba055a6424d37efcab2c60ebf47cd1d639d676dd00133764bc` / `ac9b97b872c9666eebbe32b42c626997aca34438ade17d7bbf36a8154b848e6c` |
| 引擎结果 SHA256 | `0e16268c375585f622f826a3649ef272f70154d22b2bae02c6e99b90537992cf` |
| C0 / D-3 merged 答卷 SHA256 | `48c84bd693636162ea157cd3c5ff4bdc068fdf2235cdcb88a01c0783f9426855` / `61386590f37146da6cb142a6b78ac6be9fc5d6c6cfed93e39590d220228e92bc` |
| C0 / D-3 seal 清单 SHA256 | `e83ad5333e0e28400ae8b93669a74f8f3c6dbec4d32b2dafc45fcddad42b9a62` / `ac1e0d2c10016184df33a0218f09806aeeb7e6e0fdcf2474de671fb0e1b7adeb` |

报告待验证数字：两臂各 298 合法终态、merged 各 298 唯一 qid；C0 286 success + 12 awaiting_prediction，D-3 285 + 13；各 187 次真实模型响应且 usage 187/187；hit@1/3/5 为 C0 `136/182/186`、D-3 `132/174/182`；@5 配对 both/C0-only/D3-only/neither 为 `178/8/4/108`；响应在途峰值 `33/32`；费用估算 `¥4.8911/¥5.2016`，另有烟测 `¥0.0761`。账单回填仍是独立费用门。

## 3. 执行顺序与证据要求

### A. 只读保护与身份

1. 从 [接入说明](CHENYU_ACCESS.md) 使用现有 SSH 通道；助手脚本缺失时按该说明恢复，不把密码、token、`.env` 值或原始金标内容写入命令输出/报告。长审计任务按该说明后台落盘并短连接检查。
2. 在任何解析或评分之前，为两臂关键目录建立**审计前**文件路径、大小、SHA256 清单；至少覆盖 `exam_inputs.jsonl`、`input_manifest.json`、`batch_identity.json`、`workers/`、`runs/`、`merged/`、`_arm_summary.json`、`_seal/`。完成后以同一规则再算清单，逐文件确认未改写；新输出不得落在被检查根内。文件太多时可保留逐文件 manifest 并汇总根摘要，不能仅比较目录 mtime。
3. 独立解析两臂配置及实机 `batch_identity`，逐键列差异：报告称配置 38 个扁平键、身份 58 个扁平键，均只差 `prediction_policy_overrides.reactant_similar_enabled`；C0 为 `false`，D-3 为 `true`。核对代码、资产、prompt、scorer、模型、预算、题卷及价格快照身份；若字段缺失，标证据缺口。
4. 核验 `exam_inputs` 是 298 个唯一且同序 qid，仅含 `qid/substrate_smiles/input_index`，与输入 manifest 对应，运行侧无答案字段。**先核封存与隔离，再单独打开金标做评分**。

### B. 298 题原始终态与答卷

1. 直接枚举 `workers/*.status.json`、`runs/<run_id>/` 的 checkpoint/results、`merged/` 和导出元数据；依据 manifest 的显式 qid/run_id 关系联结，不从目录名截取 qid。逐题列状态、停因、导出成功与否、身份引用、答卷路径、答卷 SHA、候选数。确认 298/臂一对一、无遗漏/重复/异常失败/导出失败/静默补空答。
2. 核对 `merged/export_metadata.json`、`merged/predictions.jsonl`（以实际文件名为准）和各题最终报告产物：非空数 286/285，空答 12/13，宽度不超过 5；`awaiting_prediction` 必须有可解释合法停因。独立判定配对完整性，之后再与 `pairing_gate.json:verdict=complete` 比较。
3. 核实引擎 298 条合法结果及上述引擎 SHA；两臂计分须引用同一引擎产物。引擎的原始结论和文件身份分开记录。

### C. 响应、重试、usage 与并发

1. 从每题原始任务/响应产物重建**每一次 issued 请求**，输出 qid、run_id、task_id、attempt、request_id、HTTP 状态、发出/完成时间、usage 各类 token、响应文件路径与 SHA。核对每臂 187 个唯一 request_id、187 个成功响应、无失败/429/孤儿，及“185 题各 1 次、1 题 2 次”；逐题核对 112 题无需模型的 recorded 直通。区分“请求尝试”与提供方内部 HTTP 重试，不把失败尝试漏出账本。
2. **重点复查两次尝试的题**：原始响应应能明确呈现 attempt 1、2。现有 `reports/phase_d/retest/{C0,D3}_inflight_events.tsv` 在重复 task 上把两行都标成 attempt 2；追查 `scripts/ec298_pd_retest_inflight.py` 的 `(run_id, task_id)` 映射覆盖。分别判定原始响应、API 调用表、在途表何者正确；记录受影响行及修复建议。不得因峰值碰巧一致而宣称逐请求表全对。
3. 独立用原始请求区间计算并发峰值：先核时钟顺序、负/零时长、唯一性与缺区间，再按明确的半开区间 `[sent_at_epoch, done_at_epoch)` 扫描事件；同一时刻先处理完成再处理发出。与闸门峰值和仓内逐请求表分别核对。`sent_at_epoch/done_at_epoch` 是 epoch 墙钟时间；若有 `elapsed_s`，检查其与区间时长差异并披露时钟异常。报告中的“单调时间戳”措辞须由原始字段和采集代码证明，否则提出勘误。
4. 从原始 usage 独立求和输入、输出、缓存、思考 token，按冻结价格快照重算两臂费用，并与 `{C0,D3}_api_calls.tsv`、arm summary 比对；核查烟测 2 次调用单独计账。估算费用与服务商账单分列，不把尚未回填的账单写成已核实。

### D. 产物来源、判分与隔离

1. 对每题最终 `predicted_products` 有序列表，重新读取 `results/T_*/report_adjudication.json` 的 `products[reportable=true]`，按 `report_rank` 排序后逐位比对完整 SMILES（含适用时的 `product_smiles_full`）、来源 `evidence_id/card_kind/report_rank` 和验证引用。至少完整覆盖 571 个非空答卷的首位，并对全部报告位做一致性统计；任何来源缺失或位次/字符串不符单列，不得只数填充率。
2. 在只读封存与无泄漏检查完成后，离线按冻结 `v43-ec298-scorer-2` 对原始 merged 答卷重算逐题 rank、hit@1/3/5、空答固定分母及配对四格。生产评分脚本可作第二对照，但主复核应独立读取原始答卷、显式 qid 联结并复算汇总，不能只重跑现有 pairing 脚本再引用它的输出。与 `score_v2_C0/D3.json`、`paired_scoring_298.json/tsv` 的 298×2 rank 逐项比较，列出全部差异。
3. 独立逐文件验证 `_seal/` manifest 的路径、大小与 SHA，并对运行侧输入、任务载荷、prompt、响应、裁决和导出做金标/凭证隔离审计。检查字段结构和泄漏路径，避免把一般化学词或引用文档当泄漏；报告只给脱敏证据路径、规则、计数，不回显密钥或金标答案。对照报告“309+309 seal 文件、601 扫描文件、0 违规”的口径及覆盖范围。

## 4. 交付物

新建 `reports/phase_d/retest/raw_run_audit/`，至少包含：审计环境与输入 SHA、前后文件清单及 diff、逐题终态表、逐调用表、来源逐位比对表、独立并发事件及峰值、usage/费用汇总、评分及配对差异表、隔离扫描摘要、输出 SHA 清单。原始响应、金标答案、prompt 全文和凭证不得入仓；表格只保留必要的脱敏字段与远端相对证据路径。

新建 `docs/EC298_PHASE_D_RETEST_RAW_RUN_AUDIT_REPORT.md`，逐门给 `pass | fail | evidence_gap`、差异的文件/行/题号/原始证据、影响面（主分数、来源、并发、费用、完成性）、复现命令和审计限制；总判定只可为 `verified_complete | contradictory | evidence_gap | not_accessed`。原始 run 的任何矛盾不得被既有报告的 `complete` 掩盖。若仅派生表元数据出错，明确“原始事实成立、派生表需修复”的边界，并提出具体补丁；本任务不擅自改旧报告或历史输出。

## 5. 验收门

只有在远端原始文件可读、前后 SHA 不变、两臂身份与 298 题终态完整、每次调用可追溯、报告产物来源逐位吻合、独立评分与配对数字一致、并发口径可由原始区间复算、费用 usage 完整且隔离无违规时，才可写 `verified_complete`。任何一门缺证据写 `evidence_gap`；任何真实矛盾写 `contradictory` 并给最小反例。结论仅限“已见 298 题、冻结配置下观察到的差异”；`reactant_similar_enabled` 默认继续保持 `false`。
