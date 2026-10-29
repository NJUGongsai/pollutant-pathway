# T-G Step D1.2 P1 回修 — 代 Codex 同范围复审(二轮)报告(2026-10-19)

> **终判定:放行。** 一句话理由:首轮 P1-D 四缺陷全部经修正+**评审侧独立端到端复跑**逐项闭合、
> P1-E 以「收口干净树 2293/0/16 + 幂等件 ×12 变 seed 全绿」满足首轮条款,编译器算法本体未再动
> (sha 与首轮锁定逐字节同);新增 1 条前置登记(P2-CHEM-FORWARD,T-H 前闭合,不阻塞本提交)。
> 通道 provenance:CC 指派 ZCode 主会话**代替 Codex**(额度断流期);评审独立性不做背书,
> 结论采信到程序证据互证为止;正链 Codex 恢复后可复核确认。放行类结论按请求书自注执行。
> **题域标签:298=RHEA 通用酶学/已见题(post-hoc);探针 ≠ 预注册 ≠ 成绩;compiled ≠ 化学有效。**

## 一、读时 sha256 与读件清单

HEAD=`26ad119`;`s5b_compiler.py`=`4cf61a8a…`(与首轮锁定**逐字节同,算法本体未再动**)。

| 对象(读时锁定) | sha256 |
|---|---|
| `d1_remap_c2probe_diff.py`(重写版) | `9eacda70800d8b60…`(与请求书声称一致) |
| `d1_remap_c2probe_diff.json`(1.2MB 重账) | `f905927ecd1acf50…` |
| `d1_remap_replay.py` / `.json`(单变量树+行级全量) | `bf4859781288…` / `f749bc3ef539…` |
| `d1_remap_summary.md`(重账版) | `a877326503012…` |
| `p3_chem_diagnostic_pack.json` | `f869c08388a0…` |
| `p1e_closure_evidence.md` / `p1e_idempotence_x12.log` | `ade2edc19e65…` / `a2d2ea443606…` |

读件:请求书、首轮报告(回修任务书)、上述全部回修产物+重写脚本源码(helper/分类/因果段)、`oldaccount_v1_20261019/` 旧账对照、诊断包 md+json 全量、builder W4 合并语义段(`merged_source_keys` 机制核)。

## 二、P1-D / P1-E 逐项闭合判定表

| 项 | 判定 | 依据(行号/产物字段/实验) | 要求动作 |
|---|---|---|---|
| **P1-D① helper 吞前插/中插** | **闭合** | `align_ordered_subsequence`(重写版 :~181-206):贪心最早匹配+`matched_positions` 记真实命中索引+未匹配新 spec 全保留;举证件 `RXNG_0faafc6` 臂B added **0→1** 且披露在档;**新增件披露全量核**:臂A **278/278**、臂B **266/266** 逐件 `remap_applied=true`+`n_new_maps`(臂B 另 2 件共底物声明面)——本审逐行复算通过 | 无 |
| **P1-D② version-only 混入 additive** | **闭合** | 六类拆分:`version_only` A 62/B 66,行内 `raw_diff_paths` 全量落盘,**150 条路径 100% 以 `compile/compiler_version` 结尾、零例外**(本审逐行核);旧账 additive 216/212 = 62+154 / 66+146 **精确拆分保持**;本审首轮实证件 RXNG_0410354 正落 version_only 类 | 无 |
| **P1-D③ 明细截断** | **闭合** | 全量落盘核数:298×2 分类行(每行 class 唯一,六类和=298 互斥完备,`unresolved=0` 兜底在码)+201×2 诊断逐键行+unlock `all_rows` 454 行(pre/post outcome+changed)+replay `frame_rows` **1886**+`migrated_tnc_rows` **616**(逐行 applied=true);旧账完整归档 `oldaccount_v1_20261019/` | 无 |
| **P1-D④ other_diff 因果+unlock 点名** | **闭合** | removed 12 行(2+10,与旧 other_diff **同 id 集**,fallback 4+4 亦同 id 集)全部 `removed_kind=spec_bytes_changed_same_key`;`causal.missing_old[]` 逐件:缺位旧 spec 身份+**双侧候选层状态全等**(in_candidates/outcome=compiled/pool_rank/route/f5 逐字段同)+`key_reappears_as_changed_spec=true`+`spec_diff_paths_vs_same_key` 恰 2 条(compiler_version 值差+merged_source_keys only-in-pre);unlock 4 行结局变化**全点名**(15143/15407→compiled、42649→`center_empty:removed_only`、49530→`ambiguous_alignment`)且与本审独立复跑逐行一致。**「池层可观测变化」口径成立**(机制核见 §三.2) | 无 |
| **P1-E 全量绿** | **闭合(裁定口径见下)** | 收口干净树(D1.2+E1a+E1b 在树、无写入者)全量 not-slow **2293/0/16** = 基线 2243+E1a 33+E1b 17 **精确闭合**;幂等件 **×12 PYTHONHASHSEED 逐次随机全绿**(满足「≥10 次含变 seed」);novel_failure ×4 全绿 | P3-MONITOR 登记 |
| **单变量口径** | **通过** | meta:`trees_identical_except_compiler=true`、pre/post sha=首轮复审锁定两 sha(`aa6806b8`/`4cf61a8a`)逐字节同;本审**独立端到端复跑**(全新重建两树+4 探针全跑,非 diff-only)全数字复现,复跑 JSON 与交付版除 meta volatile 字段外**全等** | 无 |
| **replay 面零差** | **通过** | A/B/C/D 四 section 与旧账逐项零差(task_b_frame 仅**新增** frame_rows/migrated_tnc_rows/n_tnc_migrated 三键,旧键值全同——本审程序化对照);锚 pre==D1 基线逐行 mismatch 0 | 无 |
| **P3-CHEM 诊断包** | **通过(完整)** | 首轮 §三.1② 清单全齐:原判读记录**逐条原文**(件1=7 条:6 reject_correct+1 v2 期 pass_expected 含 mapping_anchor;件2=3 条:2 reject+1 uncertain)+原/补映射后模板串+extract 前后状态+execution product/target/coproducts+来源文件清单与逐件 sha256(spec/remap/material/transform_after) | 消费见 §三.1 |
| **新问题(重写引入?)** | **未发现** | 分类互斥/完备(单 class 赋值+unresolved 兜底)、行账恒等式(76+62+154+4+2+0=298;72+66+146+4+10+0=298)、旧 rest_ok 只扫旧键缺陷同步修复(`extra_top_keys`/`extra_plan_keys` 双侧核) | 无 |

**P1-E 裁定口径**(请求书问):「收口后干净树全量绿」**满足**首轮条款,不要求另做「仅 HEAD+D1.2 overlay 全量绿」——理由:①首轮条款原文=「并行施工收口后,在干净树重跑」,被测树即发货树,**测试面=提交面**是正确同一性;②overlay-only 绿客观不可达且无意义(首轮已证:batch_dev 2 件纯 HEAD 同失败=既有 flake 族;v4b 断言文件天然耦合 T-E 版本面);③附加条件:**D1.2 与 E1a/E1b 同轮提交则本证据直接消费;若拆提交,每个提交点须按该提交态补跑定向+版本断言件(建议全量)后方可发货**(P3-COMMIT 沿首轮)。幂等件原失败根因未定位(收口树变 seed ×12 不可复现)——按首轮条款「复现才根因」不阻塞,登记 P3-MONITOR:**后续任何轮次该件再红,立即留现场根因,不得再按 flake 放行**。

## 三、重点项独立复核

### 1. 两件翻转的化学有效性判定与处置(P1-D 遗留重点)

诊断包证据显示**两件的判读层化学异议均仍然成立且未被补映射回答**:
- **a-2027e5910575bb3b**(n_new_maps=21):模板=氯乙酰胺→**谷胱甘肽结合物**(EAWAG-SOIL);补映射编号的 21 原子=整段 GSH 片段(S/C/N/O);7 条判读记录中 6 条 reject_correct 的理由**同族**:「多原子新片段无声明来源,donor 集仅氯乙酰胺,水/质子不能补齐」(仲裁/主判/二读×3 一致);唯一 pass_expected 为 v2 期旧读(其 anchor 称 GSH 取自 product 配平——正是修订 2 否决的读法)。
- **a-c6a1258f4db86523**(n_new_maps=1):酚 O-甲基化,新增甲基碳无供体声明;GLM v3 reject(「净 +CH₂ 无来源,拒因面独立成立——不论对齐可否」)、mimo v2 reject(砜/硝基底物前提不符)、mimo v1 uncertain。

**判定**:翻转=**机器面变化(映射完整性修复使提取层可见),非化学收益**;两件 compiled 与判读层 reject 的冲突属「机器可表达面 ≠ 化学可行面」的已知边界(负锚判例同向)。交付处置合格(列名、不静默、不计收益、维持披露未定态)。
**处置链**(沿首轮 §三.1,诊断包已就绪):①化学复核链(v3.2 口径,codex 代审即终审)消费诊断包重判——**预期维持拒**(来源异议独立于对齐);②维持拒⇒登记「编译器-判读分歧面」2 件活例;翻过⇒判读史更正;③**P2-CHEM-FORWARD(新,前置登记)**:两件=§8.1-5「有锚新增片段无来源」形状**首次实际进入机器编译面**(C2 轮 H「零暴露」结论仅适用 C2 的 150 面,本轮更正其适用域)——**判据对账条款(判读修订 2 来源校验 vs `_place_new_atoms` 不问来源)须在 T-H 付费批前闭合,或明示该类 spec 在 T-H 口径的排除/披露面**;不阻塞 D1.2 提交。

### 2. other_diff(removed 12 行)归因充分性 + merged_source_keys 机制核

**判定:充分。** 除行内因果字段外,本审做了**单题双版本机械重构**(RXNG_13a2ae2,臂B 真实供给,compiler-4/5 两隔离树):pre=触 W4 阈值降载(候选 24、unique 净反应 1、池 1 个代表 spec 携 `merged_source_keys=[bt0001#r0176, bt0001#r0267]`);post=补映射抬升首轮 unique 1→…→5、**降载不触**(候选 13)⇒二轮检索伙伴不在场⇒合并组解散⇒同 key spec 失 `merged_source_keys`、池 2→5(新增 3 件全 remap applied、原被并伙伴各自成 spec)。**零模板消失**(缺位旧 spec 双侧候选层状态逐字段全等、仍在 post 池 rank1),差异=「够则不降载」既有语义+合并 provenance 重组——与 interaction_fallback 同族同根的 spec 字节面形态,机读因果链闭合,不再依赖散文归因。

### 3. additive 抽样局限(首轮 §三.3)

已消除:六类全量行级落盘+新增件 278/266 逐件披露核验+version_only 逐路径证明,首轮「216/212 语义混淆」拆清且合计守恒。**本审独立复跑同数**(端到端,非复用快照)。

## 四、随轮交付书可直接消费的验收结论(含提交放行措辞)

1. **D1.2(s5b-compiler-5 / template-remap-1)验收 A-F 全项闭合**:A 17/17 迁移+9 compiled;B 732→116(616 迁移 8 类去向、退化 116 id 级保持、行级全量在档);C 33 逐件+2 翻转列名;D 非 tnc 1154 行零漂移+对拍六类全量账(unlock 4 行全点名、byte 298×2 互斥完备、removed 12 行因果链闭合);E 2293/0/16(收口树)+幂等件 ×12 变 seed 全绿;F 签名巧合负控钉死。
2. **提交放行措辞**:本交付**可随轮提交**(编译器 1 件+测试 3 件+版本断言;提交面与 E 测试面耦合条件见 P3-COMMIT——**建议 D1.2 与 E1a/E1b 同轮提交**,或拆提交时按提交态补测后发货);提交信息建议引用本报告与首轮报告编号。**T-H 付费批发车前另需**:P2-CHEM-FORWARD 判据对账闭合(或明示排除面)+P3-IDENT 批级 compiler 版本键补齐。
3. **两件翻转维持「披露未定、不计收益」**,化学复核链按诊断包重判;结果回写判读史,不改本轮验收数字。
4. 数字消费口径:全部读数为 298 post-hoc 探针/验收面;`compiled ≠ 化学有效`;616/156 等迁移数字在 matched 规则未动前提下有效(若动,全量重算)。

## 五、纪律与证据索引

只读评审:原仓写入仅 `docs/review_evidence/t_g_d12_rereview_2026-10-19/` 与本报告;src/tests/既有 docs/交付产物零触碰(复跑 OUT_DIR/PROBE_ROOT 改指证据目录与新 /tmp,交付 JSON 未被覆盖);金标/题面/封存逐题 run 零接触(诊断包结构串=材料包/语料资产级,gitignored 内,首轮授权口径);未执行真实批脚本;零外部模型/网络;git 只读;不 push。隔离:复跑两树全新重建+逐文件核验;机制重构用首轮双副本(headonly/overlay,存在性与 compiler sha 核过);`PYTHONDONTWRITEBYTECODE=1`+`-B`+`-p no:cacheprovider`;python 3.11.16(depending43)。

证据:`REVIEW_MANIFEST.json`(冻结哈希/实验/合规总账)、`unified_verification.py/.json`(32 项统一核算;4 项初报 not-true 均系本审字段名/前缀/新增键口径问题,逐一复核为实质通过,过程注记)、`merged_keys_mechanism.py/.json`(单题双版本机制重构)、`rerun/`(独立端到端复跑:重建两树+4 探针+diff,1.21MB JSON 与交付版 volatile 外全等,stdout 日志含快照核验行)。

本报告与证据按惯例留未跟踪,由 CC 定期自决。
