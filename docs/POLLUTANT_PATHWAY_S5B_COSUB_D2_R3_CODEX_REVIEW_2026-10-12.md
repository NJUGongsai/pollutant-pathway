# PPV1 S5b 共底物 D2-R3 正链有限复审（含追加显式氢修复）

日期：2026-10-12，Asia/Shanghai。原被审 HEAD=`59db0dac0b2bd950aa7350e32f7aaab84a62d5b7`，代码父=`02a4b272e7f9ac481f67c2df7fba1974e095748c`，实际直接父=`b728fdb7150e8a0a611950882a9ab1b730df1123`。两个父之间只有 AGENTS.md，src/tests 字节相同，父红绿的源码对照意义相同。

用户续跑时明确追加显式氢修复 `50064933cb17e9b74e243e17b2cc785353301a39`，直接父为59db。因此本报告分两层留证：D2语义及原红线按59db固定副本复核；追加执行器及组合继承按50064933固定副本复核。已完成结果复用，不把旧HEAD数字冒称新HEAD全量。派单开头的“S5B-V3-02产物侧”按内容更正为 **S5B-D2-01**，金额守卫族不重开。

## 1. 编号裁定

| 编号 | 正链最终裁定 |
|---|---|
| D2R3-C01 | **D2-R3通过，S5B-D2-01清零，P1=[]。** contract/corpus 双声明首次消费核对及“键在位但损坏”拒绝成立；R1两池反例与novel同根关闭，原双删修复和合法族保持。 |
| D2R3-C02 | 声明入口“键在位即声明”自洽。空list是有效声明参与比较；在位而缺contract拒；没有第二来源的合法旧/默认路径保持，未以全面拒绝换通过。 |
| D2R3-C03 | **追加50064933显式氢修复工程通过。** 仅键级升高时消费变化端点的括号氢计数；独立H/[2H]图原子及真实超价边界保持。它是执行器语义变更，不是零行为注释改动；AtomTool-2明确登记。 |
| D2R3-C04 | **D1–D3设计线工程收口。** 本轮独立公开链及r34互证共同闭环，不能倒填r34原D3“无旁路”读码结论为当时已经成立；没有批准teacher豁免档或科学性能。 |
| D2R3-C05 | **chain12工程侧有条件放行。** 已通过D2+v4b/compiler-3+追加显式氢可组成新批；须受权协调者完成§7新登记、身份/金额/qid硬门及读回SHA封包。本评审不启动真实批，不保证298题域119/298达标。 |
| D2R3-C06 | 三冻结SHA、scorer/evaluation/金额链不变。D2层AtomTool不变；追加氢层AtomTool有意改变，不能把组合HEAD仍写成“AtomTool/legacy零字节、零行为变化”。 |

这是有限工程复审，不是298或dev的科学性能验收，不重开已经关闭的提交序、金额守卫、S3/S4及历史launch。

## 2. 固定验收、执行边界与中断续跑

基准：本人的D2-R1报告§4.2三反例、§4.3同源权威消费、§7组合批条件；本轮R3交付书及实际代码。r34评的是原始2e679b31，历史行号及“同意”不能替代当前源码和执行证据。追加氢验收来自用户本次明确授权、v4b交付§十.1/新增§十三、r33显式氢三条件。

只新增本报告与本轮永久证据目录。全部项目执行在fresh `/private/tmp`隔离副本，复制必要source/vendor/metadata及安全白名单依赖；父子同一安全v3根。depending43、`-B`、`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`；公共链socket封禁，模型为scripted合成响应。真实仓tests/全量没有执行，安全G01统计单独登记。

未读取真实题面、金标、封存逐题run、dependingv4或原v3评价资产；没有外部模型、commit、push或真实批。交付的1323/984/317/22、真实8底物等价与真实EAWAG5例恢复只核聚合/算术，未读取逐qid输入输出复跑。另作独立合成控制，不能冒称真实题域证据。

**中断续跑如实登记：** 用户报告账号额度中断；本轮执行代理确认原59db三个controller会话已不可恢复、无存活进程，只留下部分stdout，没有完整JUnit/命令完成收据。原日志完整保留，不把点号或脚本启动当全量通过。已完成源码/等价证据保留；59db不再补跑完整G01/定向。组合HEAD发生了实质执行器语义变化，故在50064933独立执行一次所需组合回归和G01，这是追加改动的必要验证。父红绿以同字节collector固定顺序复用可确证的40个通过前缀，补跑51案取得完整红trace，合并91案；没有将未完成进度冒称已完成，见execution日志与恢复计划。

## 3. 独立执行和缺席口径

| 独立验证 | 实际结果 | 证据限定 |
|---|---|---|
| 50064933四组定向 | **476 passed / 3 skipped / 0 failed**（25文件） | s5b族、AtomTool/donor/analog/edit/conservation及S3b生产回归，逐文件与命令见execution_hwall |
| 50064933安全G01 | **2050 passed / 10 skipped / 17 deselected，exit0** | 完整stdout/stderr/JUnit、逐nodeid缺席及输入SHA |
| G01中安全PPV1子集 | **1447 passed / 2 skipped** | 不冒称真实仓2061/0/16；文档守卫缺席另由本轮冻结字节核对 |
| D2父02a4同字节三文件 | **14 failed / 77 passed / 0 collection** | 11行为红＋3版本字面量红，40前缀复用＋51完整补证，逐nodeid分类 |
| 氢父59db同字节三文件 | **9 failed / 29 passed / 0 skipped / 0 collection**：6新行为红＋2既有授权翻转＋1版本红 | 行为/版本/原负控授权翻转分开，不能当漏洞数 |
| 安全输入谱系 | 59db 330→50064933 331；3换＋1新＋0缺 | 三换为atom_tool/wv3/v4b，新增hwall；D2的330相对封包R1为5换/0新/0缺；前后SHA 失配0 |
| D2公开链 | **46个distinct公开start：38主案＋7入口＋1合成EAWAG；12合法事件、0坏事件**；另9直接prepare控制 | 原R1输入逐字节复制，新增坏形态及合法控制；坏event/commit和合法账分开 |
| 默认EAWAG/whole合成等价 | 8/8 compile字节相同；4成功prepare同内容 | ea→59db；另4原unsupported未执行prepare，不称其内部验收通过；不是全域/真实8底物证明 |
| 氢独立合成控制 | 17底层边界（7放宽正控＋7仍sanitize拒＋3neutral）＋5人工模板父0→当前5 compiled/5执行成功；pool/novel当前各1事件、父各0 | 除现有测试外的边界、公共链和规则级夹具；不是5真实题的复跑 |

10个skip逐nodeid如下；同一前三项也是25文件定向的3个skip。

| nodeid | 缺席依赖/原因 |
|---|---|
| `tests/test_analog_assets.py::test_row_counts_match_v4_parser` | v4对照根未复制 |
| `tests/test_analog_v2_corpus.py::test_v2_selected_and_remapped_rows_decidable` | v2 provenance未生成 |
| `tests/test_analog_v2_corpus.py::test_v2_line_level_one_to_one_and_duplicate_ids_recorded` | v2 summary未生成 |
| `tests/test_batch_runner.py::test_input_manifest_whitelist_from_frozen_v3` | 原v3冻结评价基准不复制 |
| `tests/test_ppv1_s5a_rework_r2.py::test_s5a_r2_contract_version_registration_and_frozen_integrity` | 冻结判据文档不在G01白名单；独立SHA核验覆盖 |
| `tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_contract_version_registration_and_frozen_integrity` | 冻结判据文档不在G01白名单；独立SHA核验覆盖 |
| `tests/test_score_report.py::test_frozen_evaluator_cli_really_runs_dev` | 原v3冻结评价基准不复制 |
| `tests/test_score_report.py::test_evaluator_refusal_on_wrong_split` | 原v3冻结评价基准不复制 |
| `tests/test_score_report.py::test_evaluator_refusal_on_missing_lines` | 原v3冻结评价基准不复制 |
| `tests/test_score_report.py::test_diagnose_route_buckets` | 原v3冻结评价基准不复制 |

17个deselect=16 slow＋1禁止复制评价夹具的export_v3条目，逐nodeid完整记录于 `execution_hwall/logs/g01_absences.json`；清单：

```text
tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden
tests/test_asset_root_isolation.py::test_engine_load_isolation_and_reinit
tests/test_cli_workflow.py::test_real_run_inspect_resume_smoke
tests/test_domain_identity.py::test_identity_parity_with_frozen_engine
tests/test_engine_asset_parity.py::test_all_fixtures_parity
tests/test_engine_asset_parity.py::test_parity_covers_required_categories
tests/test_engine_asset_parity.py::test_arms_ran_on_expected_roots
tests/test_engine_asset_parity.py::test_same_runtime_failure_on_valid_fixture_fails
tests/test_engine_asset_parity.py::test_runtime_failure_in_one_arm_only_fails
tests/test_engine_asset_parity.py::test_unparseable_passes_only_with_expected_error
tests/test_engine_asset_parity.py::test_category_and_count_expectations_enforced_against_actual_candidates
tests/test_engine_asset_parity.py::test_missing_fixtures_in_both_arms_fail
tests/test_engine_asset_parity.py::test_duplicate_and_unexpected_result_names_fail
tests/test_engine_asset_parity.py::test_real_comparison_reports_found_categories
tests/test_finder_real.py::test_real_engine_catechol_recorded_evidences
tests/test_prediction_real.py::test_real_catechol_rank_candidates_smoke
tests/test_prediction_real.py::test_real_donor_recovery_attempt_recorded
```

组合定向/G01并行使用同一隔离树；主进程禁pyc/pytest缓存，实际观察隔离子进程7个pyc，pytest缓存0。数量和路径见execution_hwall/run_metadata.json，不能独归因G01；封包排除所有pyc/缓存。语义和scope各自缓存情况另列其日志。未将隔离例外隐去或归到真实仓。

原交付 `2049/0/16`、追加交付 `2061/0/16` 仍是来源声明，不以安全G01的通过数认证未复制依赖或真实题域。没有把交付自身dirty准备HEAD误当本次固定50064933的执行身份。原父14红不是14漏洞；氢父红体现获授权语义翻转，不意味着父版本错误授信。

## 4. S5B-D2-01最低收口核验

### 4.1 同源权威已经实际消费

当前 `production.py:291`统一取记录声明，`:293–300`先核contract和record_products合法list；`:415–418`共享调用NC-10。`_record_products_multiset_keys`在`:498–515`走既有strict_identity_of身份键，排序保留重复意义，不用集合并集掩盖分歧。

轴0 `:579–627`先按两处声明同源比较，分歧给 `cosubstrate_record_products_divergent`；之后`:628`才消费核验后的contract清单，并在`:669–687`与事件产物参与物多重集再对账。完整corpus不再被忽略，也不拿收缩后的contract自比较当全量证明。

| 本人R1原反例 | 当前prepare/公开消费 | 裁定 |
|---|---|---|
| contract_products_shrink_keep_copyrefs | 同源分歧拒，坏event/相关event_committed为0 | 关闭；原compile/行键/完整corpus保留，未重写权威洗输入 |
| contract_products_shrink_keep_corpus | 同源分歧拒，坏event/相关event_committed为0 | 同一P1关闭 |
| novel_contract_products_shrink | novel_rejections登记同源拒，坏event0 | 同一共享规则关闭，不要求run级一律异常 |

原坏事件在R1是R5/partial，报告没有夸为strict/R6；如今拒的理由是同源记录完整性，不是调低匹配分数掩盖坏提交。

### 4.2 键在位而损坏：四形态翻拒

`production.py:581–585`以“键在位”认第二产物来源；`:587–608`对非list值结构化拒，detail保留field/type/reason/raw原值。键在位的null/string/dict/bool不再被解释为“没有第二来源”，也不会到NC-10 checked披露。

| 原始坏值 | 父02a4公开链 | 当前prepare/start/resume | 恢复 |
|---|---|---|---|
| NoneType | 缺copy事件1、event commit1；R5/partial | cosubstrate_corpus_record_products_corrupt；事件0/事件commit0；raw值保全 | 17表增行0；本次内容也相同 |
| str | 缺copy事件1、event commit1；R5/partial | cosubstrate_corpus_record_products_corrupt；事件0/事件commit0；raw值保全 | 17表增行0；本次内容也相同 |
| dict | 缺copy事件1、event commit1；R5/partial | cosubstrate_corpus_record_products_corrupt；事件0/事件commit0；raw值保全 | 17表增行0；仅endpoint/stop的updated_at更新 |
| bool | 缺copy事件1、event commit1；R5/partial | cosubstrate_corpus_record_products_corrupt；事件0/事件commit0；raw值保全 | 17表增行0；本次内容也相同 |

四案当前先行合法账各为search_actions=2、budget_reservations=4、outcome_recorded=1，事件提交0；其余17表完整文本在证据。父各actions=4/reservations=7/event commit=1，与原缺口一致。先行合法root检索/认领/预算等账逐表保留；拒绝不报start全表零写。坏spec/声明原值保全，未覆盖、未迁移、未发新身份。resume17表零增行只证明恢复未新增行，不冒称全部表内容由此得到认证。

### 4.3 声明入口与合法回退

`_cosubstrate_record_declaration`的`:467–495`只取记录侧来源；`:478–479`把record_products键在位计作声明，不依赖装配数组。于是“有该键、无contract、无B”的坏形态在`:293–300`给 `cosubstrate_contract_missing`，不降为plain A→P。空list是有效声明，与非空另一侧不一致时仍给divergent；不是缺省。

corpus块不存在、或块存在但record_products键确未声明的两种单来源正控保持完整事件，并披露实际只消费contract；两个合法来源的同义/反序保持相同strict身份键及多重集。已知缺/重复产物、参与物引用、原双删族保持拒绝；合法copy、旁观B零copy、多B/多copy、whole/多组分whole及默认EAWAG保持。

上述9直接prepare的声明/坏成员控制单独计数，未冒称其distinct输入都已跑公开链。

这是既有双来源同源核验的兑现，不认证语料机制/原子来源，也不声称能识别两个来源及历史证据同步改写后的所有形态。合法缺来源与没有历史证据的协同改写边界按原最低收口处理，未另加全库防篡改门。

### 4.4 入口和检查时点

runflow池decide/novel/expand沿`:870`/`:933`/`:1324`调用同一prepare；run级异常经`:740–749`结构化结算，novel经`:941–951`逐条登记rejections。公开恢复再次消费同一共享源。

内存 `build_hypothesis` 在 `production.py:389`，NC-10在`:415`，早于实际工具/事件提交；不写成“假设构造前”。expand坏spec为明确登记的prepare边界防御注入，修后共享守卫先拒；没有拆后续身份门，也不冒称持久任务被自然篡改后的完整执行都已通过。

## 5. 追加显式氢修复裁定

### 5.1 边界及正负控制

`atom_tool.py:63`升AtomTool-2，`:87–89`列single/double/triple序数；`:496–503`只在 `to_n>have_n` 时，针对变化键两端点消费 `GetNumExplicitHs()`，按级差减且最低0。`:413–418`明确脱氢记账，图中独立H/同位素H不在此面。form/break/add路径未套该放宽，键不存在/键级前提不符/未知键级仍拒，最终sanitize继续裁真正超价。

独立17底层控制中，括号显式H的合成变键正控与级差记账共7项成功；clamp不足、季碳无H、醚O真实超价、form_bond非法、add_atom边界、独立[2H]和[3H]共7项仍sanitize拒；另外3项降级/同级/断键neutral保持。独立5人工规则模板父0 compiled→当前5 compiled，生产执行5/5成功，不是5真实题复跑。公共pool和novel当前各提交1事件、各matched_strict，父各0事件；两条当前诊断reaction_center_match/strict_target_match均True，**admission实际为R5/retain_conditional（计量/条件unknown），不是R6**。恢复同一模型/策略后各17表零增行；第一次novel恢复因探针错用first_pool策略被合法IdentityMismatch拒，纠正夹具只补resume，完整日志保留，未重复当前start/底层/模板/pool。第一次driver因恢复异常未保存novel start返回，事件成功以既存合成DB+artifact及同策略恢复互证，不伪补start返回值。

碳域stereo消解及执行后potentialStereo守卫仍在compiler-3；P/S/Si及纯翻转/stereo_created等已关负控没有因氢记账获许可。新执行器的可解析输出仍须走原diagnostic→audit→admission→submit，不把sanitize成功当中心/机制证明。

### 5.2 EAWAG五例、版本与池策略

交付§十三称298题域EAWAG编译成功72→77、execution_failed8→3，新增5中strict检索层3、cn层2，其余拒因不变。算术闭合；“compiled”不是hit@1/严格判分命中。本轮不读取真实5题输入或逐记录漏斗，只独立验证合成同构恢复和负控，故**五真实例恢复保持来源声明，未确认其逐题join或全漏斗相同**；不将+5外推科学成绩，不把“墙钟+1%”认证为本会话实测。

AtomTool-2承载本次执行器语义；editproto-2线协议维持，compiler-3/recorded-source-3/pool-policy-5/retrieval-6函数策略没有借此改比较/选池规则。池成员可随执行器编译成功面变化；**本轮不强制无关pool-policy升版**，但组合新登记必须冻结实际AtomTool版本、部署HEAD/code_identity、语料SHA、最终pool digest及开关，不能沿用旧候选池身份。没有把“策略不改”说成“池成员不变”。

legacy52源聚合有意从 `279d9bc19bad25e51b7c23ee276da95151a8f25cf598b9dc3642b508d817c4bb` 变为 `943571b59ad07dc7b0837930136c4508ebd673d51c4794a6d554e23c689c3b14`，唯一source变化为 services/atom_tool.py；PPV184源聚合当前为 `c56454a4a6ad79001c535a49e9c25b6cf5de85db9761fea61ac8255d4c698ec2`。历史“legacy零改动”只对D2层成立，本次执行器语义允许影响所有调用路径（含novel/legacy），由四组边界回归限定，不宣称全域科学等价。

## 6. r34互证与遗留P2

| 面/条件 | 本轮采信及处置 |
|---|---|
| D1三分类/CS2c记账 | 已关分类函数不重开。984+317+22=1323来源漏斗；CS2c代理不可归属22不等于守门实拒22。独立未跑真实面，子拒因/H重原子归属盲区继续披露。 |
| D2两轴诚实性 | 生产报告实际披露 `declared_not_executed`、center unknown、expectation_covered_state_refs及consumer_discipline；旁观B的consumption/catalysis/coefficient unknown已机读。coproduct角色不证明执行生成，消费者必须联读同批生产报告；禁止“copy已生成/全部原子有来源”。 |
| D3原“无旁路”结论 | 原读码结论已被D2及R1公开证据否定；本轮新执行证据关闭双删和产物来源残余，只据当前代码确认，不追溯采信原错误。异常并非必然逃出进程，时点是内存假设后、工具/提交前。 |
| D4union/EAWAG等价 | 既有strict键空间保持；8合成抽样、4成功prepare及函数字节核验限定报告。扩展中间裸键过拒、zip示例近似继续P2，不放宽终门，也不将8例扩大为全域。 |
| D5 NC-12/T1′ | 当前root-only/剥除参考且无豁免档，合法共底物事件partial保持；完整合法B/copy参考在criteria-v1内可strict。本轮不采r34“所有strict回路必须criteria-v2”泛化，不批准真实参考转换或豁免。 |
| D6设计闭环 | 关键条件经当前机读与公共链互证兑现，D3工程责任闭环。r32实际24唯一编号归并16行，未把休眠teacher事项冒称24个机器功能全部实施。 |

可随下一小修/文稿同步的P2，非新的代码阻塞：

| 项 | 处置责任 |
|---|---|
| 消费者证明范围 | 同批联读报告、记录身份/形成未核/计量unknown分栏，保持本轮禁句；后续协议扩字段另走版本流程。 |
| CS2c/teacher旧文句 | 真实面来源摘要已出与旧“探针未跑”文句须在下次送teacher前同步；旧mimo/封包原文不回写。teacher头仍awaiting_teacher_decision，不能替teacher批准。 |
| 后续诊断 | bonded/fallback子拆、近似键差示例、额外B计数等增强保持P2；不由缺字段追加新阶段门。 |
| hwall授权措辞 | atom_tool.py:486–487将mimo r33建议称“批准”应改为用户/任务书授权链；mimo不是授权人。本次用户明确追加工程复审，不用mimo文字代批准。 |
| 合成与金标交集 | 未读取金标，不能认证“合成与真实金标分子集合零交集”；应写人工合成、未从真实题面/金标取输入，不冒称已做真实集合对照。 |
| NC-12登记 | 每spec的retrieval-6、root-only前提与checked范围已同步；未来teacher许可/真实参考口径变化须重新登记批级检查，不静默拆旧钉子。 |

既有partial/unsupported与生成unknown不是P1；本轮没有为成绩压力开放辅因子豁免或放宽冻结判据。

## 7. 设计线收口及chain12终版条件

**D1–D3工程线收口；S5B-D2-01清零。chain12工程侧有条件放行，尚不是“旧登记立即可点火”或“真实批已完成”。** 用户本次明确纳入氢修复，原“氢墙待实施复审”项的工程验收已完成；实际组合批授权、新登记和题源/金额发车核对仍由受权主会话完成。已有授权若覆盖该组合，引用授权链即可，不要求重复拍板。

| 六项既定条件 | 必须落到新登记/执行证据 |
|---|---|
| 1 新批与身份 | 新batch、不复用封存根；实际50064933或字节相同的最终部署HEAD，corpus-retrieval-6 / pool-policy-5 / recorded-source-3 / compiler-3 / AtomTool-2 / editproto-2；code_identity、语料SHA、pool digest/开关。不得把单59db验证当组合完整部署身份。 |
| 2 298目标与范围 | hit@1≥119/298为主列，hit@5=150参考；主/老敏感性/seen/U-H5-L及共底物partial分栏；真实+5供给仍来源声明，合成通过不等于科学达线，零dev外推。 |
| 3 机器金额/数量 | 40在途、1logical/题、HTTP1490、60CNY机器帽；同日价或可核保守价界、输入/计费输出界、budget_guard SHA入run身份；原子预约/未知usage保留/429保守保留不变，失败留分母。 |
| 4 qid与§9-④ | 当日授权题源/SHA/298唯一qid由受权数据通道核；expected graphIds非空、精确键集、全qid_strict；下文原文插新登记→读回→正负控→登记全文SHA，与配置/部署身份封包。本审不访问真实资产完成这一项。 |
| 5 组合授权及冒烟 | 读回实际用户组合授权、teacher T-1默认不立项/待裁状态，T-5不暗中落地；现行无豁免档执行。相同身份固定前10冒烟后按既定授权继续，不代定真实费用/时长。 |
| 6 完整终态/封存 | 全298保留分母，usage/未结算/账单对账，封包后零LLM评分；NC-12按现行参考scope执行，异常停止保全。组合为多变量探索，不将增益独占归因D2或氢；因果归因另作固定其余项的配对消融。 |

**§9-④沿v3-R3正链报告的待插原文：**

> 现行真实批配对采用整批二档；`data_scope=real` 时禁止根身份回退的守卫触发 ⇔ `manifest_qids` 与 `export_qids` 皆空。判分前须核注册图集合非空、`bases_by_graph` 键集精确覆盖注册图且值全为 `qid_strict`，任一缺失、额外键、坏类型或非 strict 即阻断。本门只核配对档位与覆盖，不核 qid↔图映射正确性，映射由评测器权威链负责。若配对档改为逐图混合，§9-④、evaluation-5 守卫与判分门须同步改为逐图判定，不得沿用整批判。

本报告不代新登记，不代用户/teacher改阈值、金标/转换/豁免口径，不自行冒烟或开批。不存在新的工程回修P1；发车条件是既定执行义务，不是新增代码阻塞。

## 8. 红线与永久证据

| 冻结项 | D2父/59db/50064933/工作树一致的SHA-256 |
|---|---|
| criteria-v1 | 7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4 |
| FREEZE_RECORD | 6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610 |
| path_context | 971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d |

scorer匹配/排序、evaluation、runflow/endpoint、金额client/gate/worker/orchestrator及compiler字节未改；EAWAG检索/compile函数在D2阶段等价，组合新增AtomTool执行器导致部分编译结果有意翻转，不能再声称组合所有EAWAG输出与旧父字节相同。金额旧72控制由新组合回归保持，三冻结面没有因此重开。

根快照先固定169输入/24,888旧证据文件；用户追加提交只变更三个已固定源/测试，新增hwall测试和追加交付输入后固定171输入，授权过渡原文及差异保存。发布前后核已有输入与旧永久证据的集合/SHA，以及工作树只增加指定两处；不回写旧封包。发布前后守卫结果及完整清单见root_audit/workspace_integrity.json与assembly_receipt.json。

永久入口：`docs/review_evidence/ppv1_d2r3_codex_2026-10-12/README.md`。含execution中断/恢复分类、execution_hwall组合完整回归、semantics双相输入/17表/event/native/生产报告、scope的r34/默认合成等价、hwall边界/父红绿/公共链及root_audit纯读回/输入守卫/授权过渡/发布收据。脚本全文、argv/env/cwd/exit、stdout/stderr/JUnit和文本数据库转储齐备；只在tmp执行，永久包无运行数据库、pyc、pytest缓存、symlink。嵌套manifest/SHA控制全部纳根哈希，根仅排自己的manifest.json与SHA256SUMS。

根纯读回曾将scope事实文件猜为facts.json而非实际scope_facts.json，、氢纯读回初次错用status而非match_status，及追加快照初次把未在旧固定清单的交付文档当作旧变化输入，导致只读FileNotFound/AssertionError；按实际文件/清单修正，保留事件，不重跑项目、不隐去失败。账号中断、子进程/launcher失联及各包准备事件以原日志和README为准，不把取证脚本exit0当被测产品对所有输入通过。
