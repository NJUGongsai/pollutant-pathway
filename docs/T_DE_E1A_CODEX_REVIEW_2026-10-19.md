# T-D/E E1a(T-E 记录侧形式归一 + build_identity)实施 — 代 Codex 复审报告(2026-10-19)

> **终判定:放行(P0=0,P1=0,P2=0,P3=4)。** 一句话理由:设计复审 §4.1/4.2/4.3 最终口径在
> 代码/单测/批内实测三层落实,全部验收数字经评审侧**独立全量复跑**逐项复现(双树 drift=0、
> P3/P4/幂等/N10/行 schema 全吻合),探针机具缺陷的披露与处置合格;§7.3 时序偏差与 §7.4 legacy
> 宽度两处待裁项均裁定可接受(附登记)。
> 通道 provenance:CC 指派 ZCode 主会话**代替 Codex**(额度断流期)。**交付链如实记录**:E1a 实施子
> 代理收尾被基础设施截断,主窗口接管补跑并如实披露探针机具缺陷(首版双臂均加载工作树,原「全 298
> 零漂移」读数作废,修复后重跑);本评审执行子代理亦中途因 token 配额阵亡,其盘面产物完整(35 件),
> 主会话据盘面重建——凡「复跑」结论均指子代理实际执行并落盘的独立复跑,非采信叙述。
> **题域标签:298=RHEA 通用酶学/已见题(post-hoc);探针 ≠ 预注册 ≠ 成绩;零金标。**

## 一、读时锁定(2026-10-19T16:05:41Z;HEAD `26ad119`)

`recorded_source.py` `ccce8f59…`、`s5b_builder.py` `463b42e2…`、`s5b_worker.py` `4856fb82…`、
`storage/build_identity.py`(新)`203e932e…`、`test_ppv1_s5b_t_e_formnorm.py` `24685075…`、
`test_ppv1_s5b_build_identity.py` `2104cb6f…`;同步既有测试面=git status 中 E1a 相关(cospool/d2、
v4b、w23456、v4_wv41、pool_lineage、controlled_vocab_ci、chain14_evidence_switch_retry)。
读件:请求书、任务书 v2 §1/§3.1/§4.1/§4.2/§5、设计复审二轮 §4/§5、FROZEN_V3 §5/§8/§9/§10、
E1a 验收报告全文(§7 十项自披露+§8 四关注)、四个 src 文件 diff(锚点级)、e1_te_impl 全部机读产物。

## 二、复审 §4.1/4.2/4.3 与 FROZEN_V3 §5 落实核验表

| 条 | 判定 | 证据 |
|---|---|---|
| §4.1 算子/事务(实跑短路/三值按事务/all-or-nothing/双遍固定点/applied 永久电荷/map 保留) | **通过** | 代码锚点(算子+同原子状态核+事务+`_formnorm_h_breakdown` D 分列);单测 33 绿(16+17 定向实测);批内实测:幂等 **158/158** 固定点、map 缺陷 **0**(复刻 checks map_defects_zero=true)、failed 域批内 0 行+单测两遍重现 |
| §4.1 注入点(recorded compile 入口/corpus 分类前视体贯穿+NC-10/analog for-ref+raw 不传编译/两 raw 例外/tier 召回底物零触) | **通过** | 代码锚点(`corpus_formnorm_view`/`_compile_at(lhs_view,rhs_view)`/`record_equation` 保 raw);NC-10 事件级不变量单测;机械 spy(raw 阴离子串零出现于编译入参) |
| §4.2 披露最小 schema(三值全形态/trace 逐字段含 source_ref·matched_side/H=includeNeighbors 分列含 D/matching_scope/实际 query 交集/risk 四值禁伪填/human_review/五标量键条件/trace_ref 内容 sha/未 applied 零字节) | **通过** | 双树复跑行账:**5304 行 100% 三值;applied 2723 行 100% trace 且 source_ref 完整、risk 域内(present 209/unknown 2294,无伪填);human_review 2503 行**;trace_ref=sha256(canonical trace)三通道单测 |
| §4.1 build_identity(旁块唯一权威/指纹排除恰 3 项/首消费核对/run 来源唯一不可覆盖/恢复同核/三类拒因) | **通过** | build_identity.py 函数面全覆盖;单测+worker 级(四拒例/输入字节/首启失败不建 run/O_EXCL/恢复同核/落盘失败不调用) |
| §4.3 嵌套事务(父 failed 子集不授益/固定 compiler) | **通过** | 单测(applied→二遍 no-op 不覆盖;父 failed 整回滚);旧树=compiler-5 固定(两树逐文件 sha 记录) |
| FROZEN_V3 §5(C-1 仅记录侧/C-3 三层分开/C-5 逐原子披露/C-6 正负控/底物侧覆盖限制) | **通过** | C-1/覆盖限制批级披露键在位;C-3:P3(①64/27+L1 58/58)与 P4(②20/9)分开报、③留 T-H;C-5 全形态行+交集风险+人工复核;C-6:P3/P4 复现+N8 原始 0 匹配+N9 全正+N10(见下) |
| 版本承载(pool-9/source-4/formnorm-1/指纹/路由注记) | **通过** | 三版本键+参数指纹+`_route_binding_note`(算法未改结果可变)批级在位;manifest 仅引用 |

## 三、验收逐项判定 + §7 自披露裁定 + 双树/N10 独立复核

| 项 | 判定 | 依据 |
|---|---|---|
| P3/L1/P4/幂等 | **通过(独立复现)** | 复刻 checks 全 true:P3 **64/27**(recorded 17/corpus 27/analog 20)=pre1 逐位;L1-pure **58/58**;发货口径 P4 **20/9**(recorded 3+corpus 6+analog 11;t2 复现 9/6+analog 丢号缺陷修复 11 行);幂等 **158/158**;t3 10/7 |
| 双树差分(§4.1) | **通过(独立全量复跑)** | 评审侧重建旧树(sha 全对齐)+298×2 复跑:unaffected **25** 逐字节+投影零漂移、affected **273**(run_inputs 98/投影 177,逐差异挂 applied record_key)、**drift_total=0**、closure all_pass;**归档臂与复跑臂双独立重算逐项同、旧树臂 formnorm 键 0 行**——主窗口重跑产物真实可复现 |
| 探针机具修复(交付说明 §0) | **处置合格** | 缺陷机读实锤(旧树产物带新版本键)→原读数作废→修复(module_file 自证)→小样双臂验证→全量重跑;修复有效性被本审复跑证实;无效叙述未混入验收 |
| N10 | **通过** | v1 臂 298 样本、bucket/rank mismatch 0、v1 无 criteria_v2 键;v2 臂 hits **92/126/130**、豁免边 0;cross_arm 逐题全同;与冻结探针双参考一致;closure all_pass(`n10_rescore/`) |
| 全量 not-slow | **通过(双记录)** | 主窗口最终树 **2293/0/16**;评审侧独立复跑(E1b 通道)二跑 **2293/0**(一跑 2292/1=prediction_recovery 家族负载 flake,单跑绿+复跑绿,详见 P3);基线 2243/0 |
| §7.3 ledger 时序偏差 | **裁定可接受** | 设计原文「…来源工件**或 ledger**」提供出口;批侧 ledger 语义目标全保(核对→唯一不可覆盖持久化→start/resume;首启拒不建 run;先于任何付费);结构性约束属实;**登记**:orphan-ledger 边界(ledger 在而 run 未建的遗留=恢复同核处置,无害)+建议 runflow 侧下轮开「run 创建后驱动前」回调点(不阻塞) |
| §7.4 legacy 宽度 | **裁定可接受** | 结构健全:builder 恒写旁块⇒新批必受控、无旁块必历史批;`legacy_absent_disclosed` 不冒充受控不写来源;**不要求**「缺旁块一律拒」(会锁死旧批合法恢复) |
| §7 其余(t1 归因/3 件口径/拒因迁移/受控词/并行树) | **逐条通过** | t1 18/8 归因 D1.2=**旧树行级同读数复现**(t1_rowdiff 双树在档);3 件口径差登记待 T-G 对账;拒因迁移 charge→tnc 语义化+测试同步保留作用面断言;受控词 3 字面量 CI 登记;并行树声明属实 |
| §8.4 intersection rhs(split 分支) | **满足** | 「坐标不可建立」计数披露与 §4.2「缺对应给原因不猜测」同精神;lhs 轴同源计算 |
| §8.3 三件口径 | **登记** | 56-pass 子集 3 件 vs frame 级 13/8:口径不同不硬凑,T-G 正式重放对账 |

## 四、P0/P1/P2 清单

**P0=0;P1=0;P2=0。** P3(登记):①三层口径账串联(冻结 C-3② 10/7 → pre1 t2 9/6(丢号缺陷)→ 实施 P4 20/9(修复后),建议交付书补一行对照,已在本报告表内);②**human_review 面 2503 行**(risk present 209+unknown 2294)的下游消费义务随 T-H/人工复核线登记(披露≠已复核);③探针复跑原始分片留 /tmp(易失),核算脚本与对照已归档证据目录,建议分片归档;④最终树全量绿的评审侧记录=E1b 通道二跑 2293/0,一跑出现 prediction_recovery 家族 flake(第三件实证)——并入 D1.2 二轮 P3-MONITOR(再现即留现场根因)。

## 五、随轮交付书可直接消费的验收结论

1. E1a(含 build_identity)按设计复审最终口径**验收通过**:算子/事务/幂等/注入点/披露 schema/build_identity 生命周期全落实,验收数字(P3 64/27、L1 58/58、P4 20/9、幂等 158/158、双树 drift 0+行 schema 全量、N10 92/126/130)全部独立复现;**可随轮提交**。
2. 探针机具缺陷的披露与处置作为**过程诚实正例**留档(原无效读数作废+修复自证+独立复现)。
3. §7.3/§7.4 按本报告裁定登记(orphan 边界+runflow 回调点建议;legacy 结构健全性说明)。
4. human_review 2503 行与「T-E 20/9 为上限口径非命中」纪律随 T-H 消费;三层口径对照见表。
5. 提交面与 D1.2/E1b 同树耦合(沿 D1.2 二轮 P3-COMMIT:同轮提交或拆分时按提交态补测)。

纪律:原仓写入仅证据目录与本报告;并行工作流文件零触碰;金标零接触;复跑全在 /tmp/证据目录;零外部模型。证据索引见同目录 `REVIEW_MANIFEST.json`(含执行子代理阵亡与重建说明)。
