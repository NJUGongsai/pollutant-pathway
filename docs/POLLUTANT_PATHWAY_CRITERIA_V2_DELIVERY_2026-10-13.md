# ppv1-criteria-v2 判分面 T-1 豁免实施交付书（2026-10-13）

> 任务书：docs/TASK_CRITERIA_V2_EXEMPTION_IMPL_2026-10-13.md（§4.5/§4.6/§6 回传义务全项）。
> 预注册：docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md（**状态 preregistration_pending_final_confirmation**，交 CC 最终确认读；与代码同轮交付）。
> 题域标签：**298/RHEA 通用酶学/已见题**；一切重算数字为对照/敏感性披露，**非新成绩、非任何已判批次回写**；headline 恒为现行 v1 口径直到新批次按预注册以 v2 出数。
> 纪律：不 commit 不 push（交主会话核对后提交）；生成侧判据与行为零改动；判分零 LLM 零网络。

## 一、改动面（git 工作树，未提交）

| 文件 | 性质 |
|---|---|
| `src/pathway_v43/pollutant/evaluation.py` | **判分侧豁免实施**：①判据版本常量（`PPV1_CRITERIA_V1`/`PPV1_CRITERIA_V2`/`resolve_criteria_version` 严格门）；②方向限定豁免身份集（四类变体组导入期收敛断言 + sha256 前 16 位版本化哈希 + **零碳构造断言** + **与 COMPLETION_LICENSED_IDENTITIES 交集=∅ 断言** + 辅因子硬拒绝表常量）；③`_criteria_declaration_sides`（pred1 执法链：event→hypothesis→provenance_refs→provenance_records.record_equation，判不了=unknown）；④`evaluate_participant_exemption`（三谓词 + 事件级 P/O 元素账照抄补证脚本口径 + 完备二分单归属 tier）；⑤`match_reference_edges`/`evaluate_scientific` 新增 keyword-only `criteria_version`（**缺省 v1 = 豁免关**，非法值结构化拒）；⑥v2 批级 `criteria_v2` 汇总块（豁免计数 + 参考侧 v1 身份监控/退出信号）。**v1 缺省路径零新键零行为差** |
| `src/pathway_v43/pollutant/s5b_scoring.py` | 版本承载：`score_s5b_batch` 新增 keyword-only `criteria_version`（缺省 v1，与评测器同一 `resolve_criteria_version` 判据），透传 `evaluate_scientific`；v2 时聚合透传 `criteria_v2` 块（v1 metrics 零新键） |
| `src/pathway_v43/pollutant/recorded_source.py` | **仅模块 docstring** NC-12 前提域重写注记（"未获豁免披露的 matched_strict 恒 0" + v2 依据；旧文字保留）。**同文件两处运行时字符串（`cosubstrate_permission`/`co_substrate_semantics`，进 pool_diagnostics/spec 产物）未动**——它们是运行时常量不是注释，改动即破生成侧字节零改动红线；实施中发现后已回退 |
| `tests/test_ppv1_criteria_v2_exemption.py` | **新增 16 件**（正负控矩阵，§三） |
| `tests/test_ppv1_s5b_cosub_d2.py` | NC-12 断言注记 + docstring 前提域重写（四处措辞，断言本体不变——缺省 v1 口径恒 0 断言保持；旧文字保留） |
| `tests/test_controlled_vocab_ci.py` | 按 T11 自身契约登记 `("evaluation.py","resolved")`（criteria-v2 声明链状态字面量；与对齐状态词表同词形不同语义域） |
| `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md` | 预注册（新增） |
| `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/criteria_v2_rescore_{summary.md,data.json}` | 重算对照产物（gitignored 批目录新名文件，未覆盖任何既有产物；生成器 `/tmp/criteria_v2_probe/criteria_v2_rescore.py` 易失） |

## 二、测试数字

| 层 | 结果 |
|---|---|
| 新文件定向 | **16 passed / 0 failed** |
| 受影响面定向（cosub_d2 + s5a 全家 + pairing + rework_l01） | **182 passed / 0 failed** |
| 全量 `tests/ -m "not slow"`（工作树） | **2117 passed / 0 failed / 16 deselected**（380s） |
| G01 隔离副本（配对对照设计） | 见下 |

- 基线核对：任务书基线 2098 为 T1A 轮数字；HEAD `cced0db`（T7 轮）登记全量 **2101 绿**（+3 新测试）。本轮 +16 = **2117**，与工作树全量实测一致，**零翻转**；16 deselected（仓外依赖 skip 面不变）。
- 唯一红及处置：首轮全量 1 红 = F3 词表 CI `test_t11_literal_sinks_registered_and_current`（新字面量 `"resolved"` 未登记）——按该 CI 自身维护规则显式登记后全绿（先例：T1A 轮 `"recorded"` 登记同款）。

### G01 隔离跑（配对对照归因）

- 设置：`/private/tmp/g01_criteria_v2/repo`（边界副本：排除 .git/reports/缓存；`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`、`BBD_DATA_ROOT` 指空）；**真树改动面 6 文件 SHA 前后复验一致（隔离跑零触碰真树）**。
- 结果：本单工作树副本 **2079 passed / 20 failed / 18 skipped / 16 deselected**；**HEAD 干净副本（同环境同条件、本单 6 文件回退到 cced0db 版本）全量对照 = 2063 passed / 同样 20 failed / 18 skipped，失败清单逐条相同**（diff 为空）。
- 归因：两副本 delta = **恰 +16 passed（本单新测试）、零翻转**；20 红为隔离配方固有（F3 谱系 G01 脚本的 sibling dependingv3/V3_CODE_ROOT/V43_ASSET_ROOT 边界复制未复刻；失败面 = s3b/r1/cli resume 完整性测试，与本单触碰面零交集；配对单跑 4 文件时两副本同为 1 红亦互相一致）。另注：首轮 G01 与工作树全量并行执行（负载干扰），HEAD 对照单跑复现同 20 红，排除负载因素。

## 三、测试矩阵（16 件；合成夹具零金标零真实 qid）

1. `test_criteria_constants_and_membership_guards` —— 版本常量/四类 cn 收敛/版本化哈希/零碳挡板/豁免∩许可集=∅/硬拒绝表代表身份/完备二分恰两 tier/T1′ 明字；
2. `test_hplus_atomic_h_h2_three_way_distinct_no_merge` —— H⁺/[H]/[H][H] 三分无合流 + strict(H⁺) ∉ 许可集；
3. `test_declared_water_exemption_unlocks_strict_with_disclosure` —— 已声明水豁免 strict + 逐边披露形态（身份哈希/族/侧/角色/tier/谓词三布尔）+ v1 零新键；
4. `test_hplus_product_side_exemption_not_applicable_counts_pass` —— H⁺ 无 O/P ⇒ not_applicable 记过；
5. `test_ppi_product_side_traceable_exemption` —— PPi 带 P/O 追溯正控（r28 A6 合法面）；
6. `test_denovo_water_blocked_by_element_account` —— 无中生水拦截（O 供给 0 < 需求）；
7. `test_pi_reactant_side_not_exempt` —— Pi 反应物侧不豁（方向限定）；
8. `test_ppi_without_p_source_half_bookkeeping_blocked` —— 半套簿记拦截（P 追溯防线负控）；
9. `test_cofactor_and_mechanism_families_not_washed` —— NAD 挂名不洗 + NH₃/O₂ 不豁（即使来源声明）；
10. `test_undeclared_extra_maintains_partial_t1p_note` —— 未声明多余产物维持 partial（T1′ 未实施明字）；
11. `test_declaration_chain_missing_dangling_unparseable_fail_closed` —— 声明链缺席/悬空/无方程/不可解析四形态全 unknown=fail-closed；
12. `test_side_flip_and_role_mismatch_not_exempt` —— 身份+侧+角色绑定（侧别翻转/角色不符都不豁）；
13. `test_single_attribution_mixed_extras_event_stays_partial` —— 混合 extras 单归属（键唯一/恰一 tier/事件不升 exact/未豁免不披露）；
14. `test_evaluate_scientific_v2_summary_and_reference_side_signal` —— v2 批级汇总 + 参考侧 v1 身份监控（干净图 ok / 参考声明水 ⇒ EXIT_CONDITION_SIGNAL_nonzero）+ v1 零 criteria_v2 键；
15. `test_criteria_version_rejected_everywhere` —— 非法 criteria_version 三门同拒（评测器/边匹配/判分入口）；
16. `test_scoring_side_carries_criteria_version_default_v1` —— 判分侧版本承载（keyword-only 缺省 v1）。

## 四、字节不变探针（任务书 §4.5，红线 2）

**探针 = 实施后用仓内真实 `evaluate_scientific`（v1 缺省）对 chain12 全 298 题离线重算，对照 T3 冻结基线（analysis/rescore_detail.json + 批根 metrics.json）**；读取链照抄 `scripts/s5b_offline_rescore` 离线校验段（1–5b/7 步；6/8 步 DB 权威跳过并披露）；参考图 sha 对账 298/298。

| 核 | 结果 |
|---|---|
| 桶（match_status）不一致 | **0 / 298** |
| rank 不一致（桶一致题内） | **0** |
| 逐题 edge_matches 结构全等 | **298 / 298** |
| 节点 status/scope_cap 不一致 | **0** |
| v1 输出含 `criteria_v2` 键 | **False（零新键）** |
| hit@1/@3/@5 | **92 / 126 / 130（= 冻结基线，零漂移）** |

**判定：PASS —— 豁免关闭（v1 缺省）路径对已落盘基线字节级零漂移。**（另有实施中即时核：`recorded_source.py` 两处运行时字符串误改发现即回退，最终 diff 仅 docstring。）

## 五、v2 重算对照（任务书 §4.6；逐题 diff 归因）

**实现 v2 解锁 0 题 vs CS2c 模拟 N1''=13 题；集合不相等 —— 差额全部归因于 pred1 数据源差，属任务书预期的"合法性发现"，非硬凑对齐对象：**

| 证据 | 数字 |
|---|---|
| 43 partial 的 41 个 superset 事件声明链状态 | **全部 `no_chain`**（payload 内 hypothesis.provenance_refs 全空 + provenance_records 0 行 + transformation_ref 仅为 RHEA 引用号非方程——预注册 §八实测） |
| pred1 判定 | 全部 **unknown** ⇒ fail-closed ⇒ 零豁免 ⇒ 事件维持 superset/partial |
| 逐实例谓词对账（16 实例次 = 12 H₂O + 4 PPi） | **pred2 16/16、pred3 16/16 与 CS2c 探针布尔完全一致**；pred1 形态 = 实现 `unknown` vs 探针 `true`（16/16） |
| 差额机制 | CS2c 探针的 pred1 数据源 = **sha256 绑定题卷 `raw_reaction`**（金标，判分面不可消费）；实现 pred1 数据源 = **payload 内 provenance 声明链**（本批为空）——即 mimo r36 M3.5 要求的执法对象；链空时 fail-closed（unknown=不豁免，**不退化为纯身份豁免**，恰是 r32 CS4a"文本封死+未装配机器"警告的兑现面） |
| hit 参照（对照非成绩） | v2 = v1 = 92/126/130（零变化 = fail-closed 兑现） |
| v2 批级块 | edges_with_exemption=0 / events_exempted_strict=0 / exempted_occurrences=0；参考侧 v1 身份 = 0（signal ok，无退出信号） |

**13 的兑现路径（如实登记）**：豁免机器已装配且按设计惰性；兑现需生成侧/批装配按预注册 §二.1 消费契约填充声明链（hypothesis.provenance_refs → provenance_records 行携 `record_equation`；仓内 `store.put_provenance` 现无调用方）——生成侧零改动红线内本任务不填充，属后续独立轮。

## 六、mimo r36 九条件落字对照（预注册附表，摘）

| # | 条件 | 实施落点 |
|---|---|---|
| 1 | 方向限定写死 | 清单常量 `CRITERIA_V2_EXEMPT_FAMILIES_PRODUCT/REACTANT`（产物侧四类/反应物侧仅 H₂O/H⁺）+ 测试 7 |
| 2 | 侧别+追溯证据 | CS2c 补证（上游）；实现按侧过滤+逐侧豁免 |
| 3 | 三谓词进预注册（执法对象/追溯开关在四元组内/cn 版本化） | 预注册 §二 + `_criteria_declaration_sides`/元素账/`sha256_16_by_cn` |
| 4 | 逐侧过滤+参考侧 v1 计数监控 | `evaluate_participant_exemption` 逐侧 + `reference_side_v1_identity_*` 批级字段 + 测试 14 |
| 5 | 完备二分+单归属 | 两 tier 常量+显式断言+T1′ 明字+测试 10/12/13 |
| 6 | NC-12 前提域重写 | 测试 docstring/注记 + recorded_source docstring（运行时字符串不动，§一备案） |
| 7 | H⁺/[H] 无合流 | 导入期交集断言 + 测试 2 |
| 8 | 含碳非法断言+CO₂ 冲突登记 | 导入期零碳断言 + 预注册 §十.1 known gap |
| 9 | 双口径/post-hoc/位次分离/下界 | v1 headline+v2 敏感性并列、`dual_caliber_note`、预注册 §七 |

## 七、Known limits

1. **v2 在本批数据上惰性（fail-closed 兑现）**：解锁 0 vs 模拟 13，差额 = pred1 声明链空（§五）；豁免激活依赖未来声明链发射（生成侧独立轮，`put_provenance` 现零调用方）。
2. **NC-12 措辞同步范围**：仅测试注记/docstring；recorded_source 两处运行时字符串为 pool_diagnostics/spec 产物载荷，按生成侧零改动红线未动（任务书"注释措辞同步"按注释语义执行，已备案）。
3. **H⁺ pred2 语义差**：实现按任务书"豁免实例涉及的 O/P"语义将 H⁺ 记 `not_applicable`（过），与补证脚本 inst_pass 字面（恰 `pass`）不同；本批 H⁺ 实例 0，对 13 零影响（预注册 §十.3）。
4. **元素账为计数级追溯**（P/O 供给≥需求），不证明键级机制来源；判据二口径不变。
5. 探针/对照仅覆盖 43 道 partial 桶 ⇒ 一切投影为下界（mimo M4-5）；已有 strict 题位次效应未模拟。
6. CO₂/HCO₃⁻ 为登记的 v2 冲突点（含碳禁入挡板），不静默重开。
7. 判分入口 `score_s5b_batch` 的 v2 聚合透传以签名/单测+评测输出块验证；未在封存批根上跑 `score_s5b_batch`（会覆写冻结 metrics.json，封存只读红线）——新批启用走正常判分链。
8. 预注册状态 = preregistration_pending_final_confirmation；判据级变更按约定须过 Codex 正链复审才生效（本任务不含发车）。
