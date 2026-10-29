# T-G Step D1.2 确定性模板补映射 — 代 Codex 实施评审报告(2026-10-19)

> **终判定:需修正(P0=0,P1=2,P2=0,P3=4)。** 一句话理由:**编译器算法本体零缺陷面**
> (规则保真/触发面/披露版本/A/B/C/F 全部通过且经隔离复现),但两项验收未闭合——
> **E 全量绿未达成且恢复幂等件归因未闭合(P1-E)**、**D 对拍证据账存在实证缺陷(P1-D)**,
> 两者均在验收/证据层,修正不动编译算法。
> 通道 provenance:CC 指派 ZCode 主会话代替 Codex;评审独立性不做背书,采信到程序证据
> 互证为止;正链 Codex 恢复后可复核确认。
> **题域标签:298=RHEA 通用酶学/已见题(post-hoc)。全部数字为实施验收/探针口径,
> 探针 ≠ 预注册 ≠ 成绩,不外推;compiled ≠ 化学有效(负锚判例)。**

## 一、头部:锁定版本与读件清单

**D1.2 四文件读时 sha256(2026-10-19T11:54:07Z 主会话锁定)**:

| 文件 | sha256 |
|---|---|
| `src/pathway_v43/pollutant/s5b_compiler.py` | `4cf61a8a0a6e19214e39b36879e6c1bf2526b8a8731dbc541ea70afb7ae3fbb3` |
| `tests/test_ppv1_s5b_template_remap.py` | `4d868f8d784d1a0da6df52443c6f5be9c2073eb30ccb38a1efd4de711fbd14f2` |
| `tests/test_ppv1_s5b_hit50_v4b.py` | `55067d007b92d727bd9464c01684a889848ca21ee9c941a4e42e7272124b1ed2` |
| `tests/test_ppv1_s5b_hit50_w1.py` | `54d449e4e5c1e34c831a7de23db6c3c091d4559b3050a7c25e7bf82d7a47d876` |

HEAD=`26ad119`;基线对照快照=d9cee97 不适用,本轮基线=`26ad119`(compiler-4 `aa6806b8…`)。**并发注记**:v4b 在本审窗口内被并行 T-E 工作流再次修改(另一评审实例 19:15 锁定 `aa095ef8…`,主会话 19:54 锁定 `55067d00…`,差异=recorded-source-4/policy-9 两断言行,属 T-E 足迹;D1.2 在 v4b 的自身足迹仅 compiler-5 断言,单变量干净)——见 P3-COMMIT。

**读过的文件**:请求书、任务书 `TASK_T_G_D1_REMAP_IMPL_2026-10-19.md`(验收 A-F 合约)、`TASK_T_G_D1_PROBE_2026-10-19.md`(v0 规则源+17 件权威清单+锚订正)、`d1_probe.py:201-275,391-447`(v0 规则本体)、compiler diff 全量(+270/−4)、新测试文件全量(14 测)、两版本断言 diff、`d1_remap_summary.md`、`d1_remap_replay.{json,py}`、`d1_remap_c2probe_diff.{json,py}`(helper 与分类段源码亲证)、`c2probe_{unlock,byte}_{pre,post}.json`、同证据目录另一评审实例静态审计(`diff_findings.md`/`replay_findings.md`,交叉引用、仅采本审独立实证部分)。

## 二、逐项判定表

| 项 | 判定 | 依据(行号/产物字段) | 要求动作 |
|---|---|---|---|
| **规则保真** | **通过** | `_remap_unmapped_components`/`_remap_pair_components` 与探针 `unmapped_components`/`pair_components` 逐字同(union-find/签名=(元素多重集,边界排序元组)/计数配对/`key=repr` 序);`complete_template_mapping` 与 `patch_v0` 规则逐项同(新号 max+1 起按原子索引递增/removed→lhs、added→rhs/MolToSmiles canonical/异常 fail_closed);差异仅任务书 §1.1 契约扩展(返回字段、no_gap 早返、提取复跑移调用方——docstring 注明来源与版本);幂等+确定性专测在位;工业化命名零语义差 | 无 |
| **触发面** | **通过** | wrapper 层 pre-flight 唯一触发点(compiler:1404-1460),仅 `transform_no_change`;非 tnc 异常立即重抛且 remap=None⇒detail 零新键(回归测三态钉死);`_compile_donor_template_impl` 零改动;「两次解析不改输出」=extract 纯函数,成立;no_gap/fail_closed⇒原 exc 对象原样抛;「补映射后仍 tnc」结构化不可达(tnc 判据=六变化集全空,remapped 态新号必落 added/removed 集——compiler:384 判据亲证);F5 三位置/defer 语义零改动+双层 docstring 注在位;F1-F4/builder 零触碰 | 无 |
| **披露与版本** | **通过** | `spec["template_remap"]`/detail 同形(applied=true 触发未果/false 未应用);非 tnc 零新键;compiler-5+`template-remap-1` 登记;版本断言 2 件同步;全仓 `s5b-compiler-4` 引用仅历史注释/静态标签(无 live 断言;builder:1740 静态标签陈旧=P3-LABEL,T-E 侧) | 无 |
| **验收 A(17 件)** | **通过(独立复现)** | 17 件=探针任务书 §0.2 权威清单逐件同;提取层迁移 17/17;compiled 9/no_alignment 7/execution_failed 1;9 件 applied=true、n_new_maps>0、带披露;隔离子代理复跑 vs 归档 **n_diffs=0**(volatile 4 键除外);锚校验 pre==baseline 逐行 mismatch 0 | 无 |
| **验收 B(全框)** | **通过(独立复现)** | 1886 行闭合;tnc 732→116;迁移去向 368/156/58/8/4/16/6 逐项吻合;退化件 116=id 级同集保持;applied 616/116/0;env 608 全迁移、rhea 124=116 保留+8 迁移;直方图总和闭合 | 无(行级明细落盘归 P1-D③) |
| **验收 C(负控 33)** | **通过(独立复现)** | 33 件逐件结局(2/16/13/1/1);still-tnc⊆B116、compiled2⊆B156 交叉闭合;2 件翻转列名不静默不计收益;化学有效性判定见 §三.1 | P3-CHEM 诊断包 |
| **验收 D(零漂移+对拍)** | **P1-D 需修正** | 非 tnc 1154 行四字段行级零漂移=通过(任务书 D 行口径=「逐行结局」,四字段即行级结局;完整 spec 字节不变性由触发面结构+非 tnc 零新键测试支撑);unlock 48→50/broken 0/f2c 2 行点名=通过(复跑逐字节同);**byte 面证据账四缺陷见 §四 P1-D** | 修审计脚本+重账 |
| **验收 E(全量)** | **P1-E 未闭合** | 交付记录被截断无数字;overlay 实测 5F/2222P(总账 2243=2229+14 吻合);差分归因见 §四 P1-E | 干净树重跑+专项复测 |
| **验收 F(签名巧合)** | **通过** | `test_signature_coincidence_fail_closed`:机械前置证明(签名同+去 map canonical 不同)+规则级(no_gap/零新号/串原样)+编译级(原 tnc 如实拒+applied=false)三层钉死;matched 不处理=护栏本体 | 无 |
| **负控纪律** | **通过** | 翻转不静默/不当收益;退化 116 保持;replay json 逐行在档 | 无 |

## 三、重点项独立复核

### 1. 两件 reject→compiled 翻转(C 项重点)— 化学有效性风险判定与处置建议

**事实**:a-2027e5910575bb3b(tpl-env:EAWAG-SOIL:43729396-…, **n_new_maps=21** 大补映射)与 a-c6a1258f4db86523(tpl-env:EAWAG-SOIL:edcfad65-…, n_new_maps=1);均 pre=tnc、post=compiled、applied=true。二者属 P0-1 判读层 **reject_correct** 面——机器翻转与判读标签冲突。

**风险判定**:(a) 现有归档产物**不足以判定化学有效性**——replay 行只含 case_id/record_key/n_new_maps/结局,缺产物串、补映射前后模板、transform、原判读理由(replay.py:390-405 字段面亲证);(b) 两个方向的标签都不得当真值:历史 reject_correct 可能基于 tnc 伪影面判读(判读者看到的是「无净变化」材料),compiled 也不证明化学可行(负锚判例「编译通过不单独证明闭合净反应」);(c) n_new_maps=21 意味着 21 个原子按**签名配对假设**获得编号——签名只证「元素多重集+附着点」同,不证化学对应(F 项测试钉死的正是该风险类),大件优先复核。

**处置建议**(按序):①维持「负控翻转、未计收益」状态(交付已如此,合格);②实施方回传**最小机械诊断包**(两件:原 judgement_basis+mapping_anchor、原模板/底物串、补映射前后模板+完整 transform、最终 execution product、字段来源与哈希)——零金标零题面即可组装;③送既定化学复核链(v3.2 判读口径重判,codex 代审即终审)按**补映射后面**材料重判;④复核维持拒⇒登记「编译器-判读分歧面」(判据是否加化学校验=另轮+CC,沿 §8.1-5 对账条款先例);复核翻过⇒登记判读史更正;⑤**若后续修复触及 matched 规则,A/B/C 迁移账必须重算(616/156 等数字不得沿用)**。

### 2. other_diff 2/10(D 项)— 归因充分性判定:**不充分,并入 P1-D**

12 行(臂A 2+臂B 10)字段级同型属实(pre_threshold_dropped=true/post=false、rest_ok/plan_rest_ok=true、post_candidates⊆pre、missing_not_in_post_candidates=false=缺旧 spec 仍在候选未丢编译面),机制叙事(补映射抬高首轮编译数⇒W4 阈值降载未触发⇒池组成重排)与 C2/RR 轮先例一致、方向诚实;但**四条件不齐备形态按现有字段无法排除竞争因**(去重/截断/排序均可产同型字段),缺逐件因果链(缺位旧 spec 身份、替代它的新 spec 是否 remap 件、候选层状态)。逐行披露在档合格,归因闭合不合格——修正动作并入 P1-D(补因果字段后重账,不得静默并入 fallback_interaction 类)。

### 3. additive 抽样局限(D 项)— **实证坐实为分类混淆,并入 P1-D**

本审自证实验(`equal_len_additive_diff.py`):RXNG_0410354(归档等长 additive 行代表)双版本池构建,**spec 级唯一差异=3 个 `compile.compiler_version` 字符串(compiler-4→5),诊断零差**——即「等长 additive」行实为版本-only 字节差;叠加 helper 吞前插/中插(实证 RXNG_0faafc6 臂B old2/new3/added=0,真新增 1 件逃逸 remap 披露核验;同题臂A 尾插 added=1 正常捕获)——**「additive 216/212」不是真新增计数,「新增件逐样本带 template_remap 披露」未被全量核验**。前 20 行截断(196/192 行无明细)使上述两缺陷不可从归档自查。

## 四、P0/P1/P2 清单

**P0=0。P2=0。**

| 级别/ID | 事实 | 最小收口 |
|---|---|---|
| **P1-E** | 任务书 E 硬验收(全量 not-slow 全绿)无落盘记录(交付终答被截断);本审 overlay(HEAD+仅 D1.2 四文件)实测 **5 failed/2222 passed/16 skipped/16 deselected**(总账 2243=基线 2229+14 ✓)。差分归因:①`test_v4b_versions_registered`=锁定文件内含并行 T-E 断言而 overlay 还原其模块所致(归因并行合编,非 D1.2);②③`test_batch_dev`×2=**纯 HEAD 对照同失败**(既有 flake 族,非 D1.2);④`test_crash_after_prediction_recorded_novel_failure…`=仅全量重载失败、两次隔离均过(负载 flake,不坐实);⑤`test_crash_after_commit_resume_replays_prediction_idempotently`=**overlay 全量 FAIL+批量隔离 FAIL(ArtifactConflict validation.json `e8c5cdda`≠`e959c7ba`)、单测复核 PASS(2.46s)、HEAD 对照 PASS——归因未闭合,疑似 D1.2 与进程对非确定性交互**(驱动子进程走副本源码已证,排除并行代码泄漏;失败窗口与并行施工/784s 异常负载重叠如实登记) | 并行施工收口后,在干净树(提交后 HEAD+D1.2)重跑全量并落盘数字;该幂等件专项 ≥10 次复测(含 PYTHONHASHSEED 变化)须全绿;若复现⇒定位 validation.json 首写 vs resume 重算的差异字段(疑点面:恢复重放路径对 remapped 串/披露字段的再导出稳定性)修复后放行。**此项闭合前不得提交发货** |
| **P1-D** | byte/unlock 对拍**证据账**四缺陷(编译算法不动):①`_is_ordered_subsequence`(c2probe_diff.py:181-194)把扫描过的新索引全部记入 consumed⇒**前插/中插新增被吞**(归档实证 0faafc6 臂B added=0/真差 1;臂A 尾插正常)⇒「新增件带 remap 披露」核验不完备;②**等长字节差行归入 additive 未拆版本-only**(实证 0410354 唯一差异=compiler_version×3)⇒216/212 计数语义混淆;③**明细截断**(additive 仅前 20/216+20/212、diag 前 30/201;B 面 1886 原始行与 616 迁移行级未落盘)——C2 轮「漂移面全披露」先例不适用截断替代;④other_diff 2/10 缺逐件因果链字段+unlock `all_rows` 无最终拒因字段(tnc→ambiguous/center_empty 的 2 行迁移无法逐行点名,仅直方图可见) | 修审计脚本(helper 记录实际匹配位置、未匹配新 spec 全保留并逐件核 remap 披露;分类拆 raw-identical/version-only/真 additive/interaction/unresolved;全量 298×2 分类行+201 诊断差行+616 迁移行落盘;other_diff 补旧 spec 身份/候选状态/替代因/remap 身份;unlock 行级落最终 outcome)→**新隔离链复跑重账(不得静默用并行工作树作单变量归因,沿本审 overlay 法)**;重账后 A/B/C 若受 helper 修正影响一并复核(预期不影响——A/B/C 走 replay 脚本非本 diff 脚本) |

**P3(登记,非阻塞)**:P3-IDENT(spec 级 `compile.compiler_version` 自证在位=批内容可判世代;manifest/diagnostics 无批级活 compiler 版本键,policy-9 将横跨 compiler-4/5 两世代——建议下轮 diagnostics 加 `compiler_version` 键+沿 C1 偏差窗口先例登记;本审顺带更正 C2 轮报告「批产物无编译器版本」表述);P3-COMMIT(v4b 断言文件双工作流合编且评审窗口内仍被并行修改——D1.2 与 T-D/T-E 提交须耦合或断言拆行,避免单变量归因窗口);P3-LABEL(builder:1740 policy8_route_note 静态文本嵌「compiler s5b-compiler-4」陈旧,T-E/下轮侧顺带改动态或更新);P3-CHEM(2 件翻转最小诊断包回传,§三.1 处置链)。

## 五、随轮交付书可直接消费的验收结论

1. **规则保真/触发面/披露版本/F 签名巧合负控:通过**——compiler-5 实现=探针 v0 规则逐字移植+任务书契约扩展,触发面单变量封闭(仅 tnc、非 tnc 逐字节零触碰有结构+测试双证),「补映射后仍 tnc」结构化不可达有证。
2. **A/B/C 三面:通过且经隔离复现**(复跑 vs 归档 n_diffs=0;锚 pre==D1 基线逐行 0 mismatch;全部声称数字逐项吻合):17/17 迁移+9 compiled;732→116(616 迁移 8 类去向+116 退化 id 级保持);负控 33 逐件+2 翻转列名。
3. **D 面:行级账通过、byte 证据账需修正**(P1-D,修审计脚本不动算法);unlock 48→50/broken 0/迁移 4 行(2 行已点名,2 行待 all_rows 补最终拒因字段)。
4. **E 面:未闭合**(P1-E)——干净树全量绿+幂等件专项复测通过后方可提交发货。
5. **2 件翻转:维持「披露未定」态**,按 §三.1 诊断包→化学复核链处置;不计收益、不入任何分子;matched 规则若动,迁移账全量重算。
6. 版本身份:spec 级 compiler_version 自证在位;批级键与 policy-9 世代窗口按 P3-IDENT 登记,**T-H 付费批发车前建议补齐批级 compiler 版本键**。

## 六、纪律与证据索引

只读评审:原仓写入仅本证据目录与本报告;src/tests/既有 docs 零触碰(并行施工禁触遵守);未执行真实批脚本;金标/题面/封存逐题 run 零接触(材料面=授权判读产物+冻结底物+语料资产级信息);零外部模型;git 只读;不 push。隔离执行:overlay `/Volumes/CC/tmp_tg_d12_review_8857fe`(四锁核验 ok)+headonly 对照 `/Volumes/CC/tmp_tg_d12_headonly_25644`;探针脚本 REPO/OUT 适配 patch 在档;`PYTHONDONTWRITEBYTECODE=1`+`-B`+`-p no:cacheprovider`;python 3.11.16(depending43)。

**异常如实登记**:①执行子代理终答被基础设施截断(暴毙),其 36 件产物完整落盘,本报告据盘面重建并由主会话补做关键差分实验(headonly 对照、单测复核、等长 additive 探针);②同证据目录存在另一评审实例(19:15-19:18 静态审计,rule_/replay_/diff_ 系列)——本审仅采其发现中经独立实证者(helper 缺陷经源码亲证+归档行亲证;版本-only 混入经本审双版本探针实证;截断经交付自白+脚本源码核;unlock all_rows 局限采其读码结论并注出处),其结论不构成本审背书;③本审 C2 轮报告中「批产物无活 compiler 版本键」表述经本轮实证**更正**(spec 级在位,manifest 级缺)。

证据(`docs/review_evidence/t_g_d12_codex_2026-10-19/`):`REVIEW_MANIFEST.json`(冻结哈希/实验/合规总账)、`equal_len_additive_diff.py/.json`(本审自证)、`overlay_exec/`(01-10 系列:overlay 构建与四锁、定向 54+1F、全量 5F/2222P、探针适配、replay 复跑 n_diffs=0 对照、c2probe 复跑、隔离归因实验)、另一实例静态审计系列(交叉引用)。

本报告与证据按惯例留未跟踪,由 CC 定期自决。
