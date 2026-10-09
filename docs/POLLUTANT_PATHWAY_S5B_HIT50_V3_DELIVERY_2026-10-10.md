# PPV1 S5b HIT50 v3 实施交付书(W-V0→V1→V2→V3→V6;V4 草稿)

状态:`implementation_ready_for_review`(交回主会话复审;不自行
点火 298)。任务书:`docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md`
(唯一权威);红线继承链:AGENTS.md + v2 任务书 §1。

- 开工基线:HEAD = `35727eb2b5f548d07755430ad6d5f59fbb429b5c`
  (v2 轮实施提交),工作树跟踪文件干净(56 个评审侧未跟踪文件
  保持不动、未读、未提交);本轮改动 = 7 个源文件 + 4 个新测试
  文件 + 本交付书 + W-V4 mimo 请求草稿(见 §十提交清单)。
- 实施期:**零真实模型调用、零花费、不 push、不改封存批**;远端
  Chenyu 通道只读(v2/v1 批根与授权 corpus,探针零远端落盘)。
- 验收主列(用户指定):主口径 hit@1 ≥ 119/298(40% 档);
  hit@5 ≥ 150/298 参考线。**本轮为工程修复交付,科学目标由
  复审后新批零 LLM 判分判定;本交付书所有恢复/外推数字均为
  反事实/编译面测量,不构成性能承诺**(缺口是净新增,编译通过
  数不冒充命中数)。

## 一、状态矩阵

| 工作包 | 状态 | 关键产物与证据 |
|---|---|---|
| W-V0 尸检证据复核 | ✅ 完整复现 | 两探针全部数字与尸检一致(§二);不带着错误前提实施 |
| W-V1 提交序贯彻调度序 | ✅ 完成(方案 A) | `search.py` 单调微秒 created_at;4 测试绿;父基线红绿对照红(§四) |
| W-V2 recorded 编译墙 | ✅ 完成(有界键差) | 116 全量分类(复现直方图逐项一致)+ fallback + 产物多重集全映射评估(§五);v2 失败面恢复 4 条(如实) |
| W-V3 池深审计 | ✅ 完成(审计+前置门) | 298 题检索面零模型审计(§六);对齐必要条件前置门;结论:编译门非主要供给杀手 |
| W-V4 partial 口径 | ✅ 草稿交付 | mimo 请求草稿(§七);不实施 |
| W-V5 消融批 | 未做(任务书明示不做) | — |
| W-V6 r27 条款项 | ✅ 完成 | §9-4 程序门 + 配对入口锁 + 触发等价性写死(§八) |

## 二、W-V0 尸检证据复核(前置必做;命令/输入/输出/哈希)

方法:独立起草探针(不引用尸检数字开工),远端只读执行
(`echo <b64> | base64 -d | python3 -`,零远端落盘、零写、零模型),
数据源 = v2 批根 `s5b_298_hit50_20261009` 的 `metrics.json`
(封存判分聚合,只取 rank/桶/n_candidate_events 标志,金标内容零
读取)+ `runs/*/pollutant.sqlite`(答卷侧聚合:事件/动作的
身份/时序/rank 字段)。判分隔离:strict 匹配事实只取已封存
metrics 的聚合输出;反事实 = 纯位次索引置换(零新调用)。

**探针 1(提交序一致性)**:298 题逐 run 重算 (created_at,event_id)
提交序 vs action_id 哈希序 vs effective_rank 序:

- 提交序 == 哈希序:**295/298**(多事件题 282/285)—— 尸检预期
  295/298 ✓;
- 提交序 == eff_rank 升序:**30/298**(多事件题 17/285)—— 预期
  30/298 ✓;
- 3 个例外为跨秒提交(机制相同,与尸检附录 C.3 一致)。

**探针 2(离线重排反事实)**:候选序换 effective_rank 序重算主口径
hit@K(n_matched_events==1/题,100/100,反事实精确):

- 实际(提交序)hit@1/3/5 = **29/67/89**(复现本批评分)✓;
- 反事实(eff_rank 序)hit@1/3/5 = **73/98/100**(预期 73/98/100)✓;
- 命中事件 eff_rank 分布 {1:73, 2:20, 3:5, 4:1, 5:1} —— 与尸检
  §2.1 逐项一致 ✓;候选数与 metrics n_candidate_events 一致
  100/100 ✓。

**正控**:合成批调度序=提交序用例 = W-V1 正控测试(见 §四);
**负控**:v2 批本身即哈希序反例(只读取证,295/298)。

复核记录(脚本/输出/哈希,证据留 /tmp 易失目录,关键数字如上):

- 脚本:`/tmp/s5b_v3_impl/wv0_probe.py`
  (sha256 `5043f8b9aefe1720e6a910debba00300cc748da326b1781ecfb2594fd676451c`);
- 输出:6 个分块 JSON(0-50/50-100/…/250-298)+ 聚合
  `/tmp/s5b_v3_impl/wv0_all_rows.json`
  (sha256 `18147ba8e62c40364aa4b2d378851b655f6e928699d79f3f2336620d172b9cd4`);
  分块哈希 `cbb1e91e…/f15a1b96…/c892df8f…/312e8e93…/6a4d9d6a…/9b5014db…`
  (完整值见 `/tmp/s5b_v3_impl/wv0_hashes.txt`);
- 命令形态:`/tmp/cy_ssh.sh "echo <b64> | base64 -d | python3 -
  <start> <end>"`(连接不稳按 5 次重试/12s 间隔纪律)。

**结论:两决定性结论全部复现,开工前提闭合。**

## 三、共用入口矩阵(任务书 §2)

本轮新增/改动的消费入口(全部复用同源 helper,无第二套判据):

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `search.SearchLedger.enqueue_action / record_blocked_hypothesis` | search_actions 行(created_at 装配) | W-V1:单调微秒 created_at(`_next_action_created_at`,事务内 MAX+1µs 递推);幂等 unchanged 分支不触碰已落账时间 |
| `runflow._inflight_action_ids / drive` | ORDER BY created_at, action_id 取任务序 | **判据一字不动**;W-V1 后自然返回调度序(docstring 更新) |
| `store.submit_event` | 事件首提微秒 created_at | **不改**(W3 既有忠实记录) |
| `recorded_source.infer_reaction_mapping` | donor↔产物并集结构对应 | W-V2:标准(零键差)枚举无解 ⇒ 有界键差 fallback(删 donor ≤2 键的不连通 any-bond 查询;预算 `_INFER_MATCH_LIMIT=200`/`_INFER_BOND_DIFF_CALL_LIMIT=512` 触顶拒) |
| `recorded_source.compile_recorded_reaction` | 库记录 → 池 spec(推断映射) | W-V2:产物多重集 gate 在全部候选映射上评估择可复现者;无可复现保持原 ambiguous/product_set_mismatch 判据 |
| `s5b_compiler._place_new_atoms/_emit_new_bonds` | rhs 新键落位 | W-V2:保留原子间新成键在无新增原子时同样 form_bond 落位(旧实现静默丢弃,已证缺口) |
| `s5b_builder.default_pool_provider` | analog 检索面 → 编译 → 池 | W-V3:对齐必要条件前置(`template_elements_fit`,同源必要条件;省编译预算,池成员/失败口径零变化) |
| `s5b_scoring.score_s5b_batch` | 判分聚合 | W-V6.1:§9-4 程序门(real ∧ 非 qid_strict ⇒ S5bScoringError,先于聚合/落盘) |
| `evaluation.evaluate_scientific`(L01 守卫) | real 首消费配对守卫 | W-V6.3:触发等价性写死(detail.trigger_equivalence);守卫行为不变 |
| `evaluation._pair_exports_to_samples` | 样本↔导出配对 | W-V6.2:入口矩阵登记(docstring)+ 锁调用点回归测试(全仓唯一活动调用) |

## 四、W-V1 提交序贯彻调度序(本轮最高优先)

**选定方案 A**(调度入队按 effective_rank 序装配本 run 内严格
单调递增的微秒 created_at),理由:

- 取任务序判据 `ORDER BY created_at, action_id` 与原 scorer
  `(created_at, event_id)` **一字不动**(防改尺子嫌疑的直接兑现);
  `schedule_hypotheses` 本就按 effective_rank 升序入队,单调时序使
  既有判据自然按调度序取任务;
- 无 schema/身份升版(方案 B 需取任务序显式带 effective_rank 排序
  键 + schema 升版;created_at 不参与 action_id 派生,方案 A 零身份
  影响);
- 通用机制(所有入队入口获得 FIFO 语义);崩溃中途重放保持相对
  次序(幂等 unchanged 不触碰;新入队时间戳 ≥ 本 run 已落账最大值);
- 并发安全:MAX 读取在 enqueue 的 BEGIN IMMEDIATE 写事务内
  (单写者纪律下跨进程串行);极限并发退化为 action_id tie-break
  旧语义,不损坏。

**执行语义保持**:rank1 展开失败不阻塞 rank2(drive 逐条容错
不变);同秒 tie 形态消除(微秒互异);重放/resume 幂等不回退
(unchanged 分支不触碰 created_at;B1 恢复 floor 语义有单测)。
**负担披露**:单驱动串行下严格按 rank 序提交,先失败重试下一条
的墙钟略增(毫秒级,零模型调用,不构成费用风险)。

**测试**(tests/test_ppv1_s5b_hit50_v3_wv1.py,4 个,全绿):

- 正控①(8 池 + 首位 novel,budget8):action 层 (created_at,
  action_id) 序 = effective_rank 严格升序、created_at 互异;事件层
  提交序 = 调度序、首事件 = novel;**穿 store→native_export→
  原 score**:`evaluate_scientific`(qid_strict 配对)+
  `_main_caliber_row`(原 scorer 主口径行,判据零改动)⇒ matched_
  strict **rank1**、命中事件 = 首个提交事件;
- 正控②(recorded 池候选模型显式首位,47 题反例形态合成版):
  rec- 候选首提交且原 scorer rank1;
- 负控:v2 形态(哈希序重排)在同一检测函数下必须 False +
  pytest.raises 断言红(检测器敏感性证明);
- 单元:同 run 严格单调微秒、幂等 unchanged 不触碰、B1 恢复新实例
  floor 续在已落账最大值之上。

**父基线红绿对照**(上一轮漏做、本轮补齐的纪律):新测试文件在
父 HEAD `35727eb` 隔离 worktree 上 4/4 红,失败形态即旧缺陷本身:
6 次入队共享同一秒级时间戳(1 个互异值)、取任务序 eff_rank =
[3,2,4,5,9,8,…](哈希序)、提交序 ≠ 调度序(recorded 首位被洗后)。
import 前显式 sys.path.insert 指向 worktree src 并断言 `__file__`
(pip editable .pth 污染已验证不生效)。

## 五、W-V2 recorded 编译墙(先分类后修)

### 5.1 分类探针(全量 298,复现闭合)

复跑 v2 批 recorded 编译(远端只读,v2 批同源代码快照 —— 84/84
文件哈希与 run_identity code_identity 一致;engine =
`V43Engine` 只读包装,python =
`/usrdata/EnzymeCAGE_envs/enzymecage_three_module_t2b_v32_…`):
**复跑失败直方图与 v2 批 manifest 逐项一致**(no_structure_
correspondence 116、stereo 38、product_set 28、new_atom_charge 14、
charge 12、no_alignment 9、ambiguous 4、aromatic_new_bond 3、
execution 3、placement 1)。

116 次 no_structure_correspondence 分支级分类(90 strict 层 +
26 cn 层):

| 类 | 数量 | 处置 |
|---|---|---|
| 加成分支/donor 侧 1 键差可解 | 23 | **本轮修**(fallback) |
| 裂解分支/组分侧 1 键差可解 | 20 | **本轮修**(donor 侧删键 ≤2 覆盖) |
| 裂解分支/组分侧 2 键差可解 | 7 | 同上 |
| 水解型(跨组分断裂+新原子;union ⊇ donor 元素) | 15 | **本轮修**(fallback 的不连通查询天然覆盖) |
| 加成分支/union 缺 donor 元素 | 9 | 语料真实无对应(诚实拒) |
| 裂解分支/组分元素不在 donor | 29 | 语料真实无对应(诚实拒) |
| 裂解分支/组分侧键差 >2 或不可松 | 6 | 超有界(诚实拒) |
| 加成分支/其他 | 7 | 诚实拒 |

### 5.2 修复(S5b-recorded-bonddiff-1;三件)

1. `infer_reaction_mapping` 有界键差 fallback:标准(零键差)枚举
   无解时,删 donor ≤2 条键的**允许不连通** any-bond 查询在产物
   并集上匹配(全部 donor 原子映射、元素对应、片段内连通保持;
   被删键 = 允许键差;未覆盖 union 原子 = 新原子,锚定由编译器
   W1 #6 规则约束)。预算/歧义披露不变(匹配数 ≤200、组合调用
   ≤512,触顶 truncated 拒;等价映射同目标合并、异目标歧义拒)。
   标准枚举成功时零行为变化(既有 W2 测试全绿)。
2. `compile_recorded_reaction` 产物多重集 gate 全映射评估:候选
   映射中恰一 executed 组分多重集 == 库记录产物多重集者被选中
   (W-V2.3"择产物集可复现者");无可复现者保持原判据(多目标
   ⇒ ambiguous;单目标 ⇒ product_set_mismatch 诚实拒,过滤缺失
   不冒充完整 record)。
3. `s5b_compiler` 保留原子间新成键落位:纯重排对应(断键+成键,
   无新增原子)的 rhs 新键同样经 form_bond 落位(旧实现
   `if not added: return {}` 静默丢弃该键 —— 已证缺口)。

spec 披露新增 `n_bond_diff`(选中映射删键数;0 = 标准零键差;
推断映射非机制证据的既有标注不变)。

### 5.3 v2 失败面恢复测量(如实,不冒充命中)

以 v2 批 322 条候选级失败记录 + 真实底物(与批 manifest 底物
join)用新代码重编译:**4/228 恢复编译**(no_structure_
correspondence 4,均 n_bond_diff=1,strict 层;涉及 2 条唯一
record、4 个 qid-record 出现)。映射层恢复 47/116,其余被更深层
门拦截:charge 24(W5 保留边界,stereo/charge 维持 unsupported)、
no_alignment 8(cn 层 donor ⊄ 底物)、枚举触顶 6、部分去芳香 3、
歧义 1、产物集 1。**product_set_mismatch 28:全映射评估后 0 条
恢复**(28/28 均"全部候选映射无一复现记录产物集,distinct
targets=1" —— 缺行/过滤缺失的诚实拒,与 v2 门语义一致)。
编译失败面修复合计 4 条;语料真实无对应与 W5 保留边界如实分层
(见上表)。零 LLM、零金标。

测试:tests/test_ppv1_s5b_hit50_v3_wv2.py,9 个全绿 —— 断键重排
正控(CCO→COC:break+form,产物多重集核对一致)、水解型正控
(酯→酸+甲醇:断键+新原子锚定)、标准路径零变化、compiler 直测
(纯重排 form_bond)、负控族(元素缺席 no_structure_correspondence
保持、触顶 truncated 拒、多目标无可复现 ambiguous 拒、filtered 单
产品卡 product_set_mismatch 保持)、产物多重集 gate 全映射正/负控。

## 六、W-V3 池深恢复与适用性门协同(零模型审计先跑)

### 6.1 审计探针(298 题检索面同 corpus 只读重编译)

对每题复跑 analog 检索面(`AnalogSourceResolver.templates_
similar_to`,阈值/降档与批 pool_diagnostics 逐题一致;本地 corpus
sha256 与批 asset identity 一致 `8f3f2c1a…`)+ 逐模板编译;
v1 侧交叉(run_inputs 池模板 + run 事件经 expand 动作
`hypothesis_key` join;v1 run_id 取自 **v1** manifest —— 修正了
探针初版误用 v2 run_id 的 join bug,修正后 v1 池模板执行数 93
与尸检"93/353≈26%"精确一致):

- v2 analog 面 3821 模板:compiled 84(2.2%);no_alignment 1946
  (元素缺席 1829 + 连通性不可松 117)、transform_no_change 1660、
  stereo 93、其他 44;
- **no_alignment ≈ 94% 元素缺席 = 检索噪声**(相似度检索面给出的
  模板 lhs 原子根本不在底物里)—— 编译门未杀供给,失败也不占槽
  (W4 失败补位语义不变,合成负控覆盖);
- **真供给损失(v1 曾执行 ∧ v2 拒)= 47 条**:transform_no_change
  39 + stereo 8。根因定位:corpus v1 模板的**反应原子未映射**
  (如 `Cl[c:6]…` → `O[c:6]…`,Cl/O 为无 map 的上下文原子 ⇒
  map 联结后零净变化 ⇒ transform_no_change;仓内 corpus v2 对部分
  record 已重映射);
- v1 的 24 个 analog 命中题:16 题的已执行模板在 v2 全部编译保留;
  ~7 题的唯一已执行模板被 v2 拒(5×transform_no_change +
  2×stereo;含 1 题混合)—— **被杀的 v1 analog 命中面 ≤ 7/24,
  且不属 no_alignment 大头**;
- **语料 v2 换装测量(本地全量 298)**:compiled 76 < 84(净更差),
  新失败 center_map_not_in_donor 59(v2 语料 center 数据缺陷),
  被杀 v1 命中模板 0/6 恢复 ⇒ **不换语料**(诚实结论)。

### 6.2 实施(S5b-pool-pregate-1)

- **对齐必要条件前置门**:`template_elements_fit`(模板 lhs 元素
  多重集 ⊆ 底物;不满足 ⇒ 编译必 no_alignment —— 判据单一来源,
  编译层 no_alignment 的必要条件,非第二套判据)在检索层拒、省
  编译预算;失败仍按 no_alignment 同口径计数(诊断另计
  `analog_pregate_skipped`);**池成员/失败语义零变化**(单测用
  编译调用计数证明前置拒不进编译)。
- 池宽/降阈值参数:零授权开发集 ⇒ 冻结参数不动(沿用 v2 纪律);
  语料换装审计结论如上(不换,待语料修复后另轮)。
- stereo 消解型(手性 sp3 → sp2,如 bt0002#r0032 二级醇氧化成酮)
  = W5 保留边界,维持 unsupported(**升级须先交设计复审**,
  设计草案见 §九待复审问题 3)。

测试:tests/test_ppv1_s5b_hit50_v3_wv3.py,4 个全绿 —— 前置门
单元(元素多重集/解析失败 fail-open)、池不变 + 诊断(编译调用
恰 1 次)、全链正控(v1 命中模板类合成同构用例:corpus 形状模板
→ provider 编译入池 → 公共链执行成事件,产物组分完整)、边界
冻结负控(授权语料实 record bt0002#r0032 维持 stereo_edit_
unsupported;资产缺席则 skip)。

## 七、W-V4 partial 40 题参与物语义(只交 mimo 请求草稿)

草稿:`docs/MIMO_PPV1_S5B_HIT50_V4_COPRODUCT_IGNORE_TIER_REVIEW_
REQUEST_2026-10-10.md`(规则级、自包含、零金标/零题面;含
T0–T3 裁定选项清单、聚合计数(38/40 超集迹象计数代理、25/40 老口径
rank≤5、v1→v2 流向)、A/B/C 三组逐条评审问题、预注册落地路径
`coproduct_ignore_tier` 独立字段 + 旧批只读 + 不与本轮工程包混批)。
送审与否及通道 A 边界由主会话按 AGENTS.md 现行条款决定;涉金标
外发须用户逐次拍板(本请求零金标内容)。

## 八、W-V6 mimo r27 判断面一附条件工程落地(三件)

1. **§9-④ 程序门**(`s5b_scoring.score_s5b_batch`):评分聚合前
   程序检查 —— `data_scope=real ∧ 任一 pairing basis 非 qid_strict
   ⇒ S5bScoringError`(`kind=s5b_real_pairing_not_all_qid_strict`,
   结构化 detail 含 non_qid_strict_bases;先于聚合/落盘;与
   evaluation-5 首消费守卫双保险 —— 判分入口独立复核,覆盖守卫
   未及的任何非 strict 值;synthetic 档不受影响)。正控:合成档
   fallback basis 聚合照旧;负控:real + fallback/未来混合档值 ⇒ 拒。
2. **配对唯一消费入口锁**:`_pair_exports_to_samples` 全仓唯一
   活动调用 = `evaluate_scientific`(evaluation.py 模块 docstring
   W-V6.2 入口矩阵登记:消费的图清单/导出条目/payload 身份);
   锁调用点回归测试源码扫描断言唯一活动调用(def/注释行除外;
   新增第二调用 ⇒ 红,须显式扩登记)。
3. **触发条件等价性写死**:L01 守卫 detail 新增机读
   `trigger_equivalence`("触发 ⇔ 两个 qid 映射皆空;整批二档;
   配对档若改逐图混合须同步改逐图判定");守卫行为不变(合成
   反例轴照旧拒,断言 detail 字段)。

测试:tests/test_ppv1_s5b_hit50_v3_wv6.py,4 个全绿。

## 九、回归与隔离证据(四组)

| 组 | 命令 | 结果 |
|---|---|---|
| 定向 | s5b 全家(w1/w23456/runtime/pairing/rework_l01 + v3 四新文件)+ s3b 全家 + atomtool/donor/analog/edit/conservation | 全绿(本报告各节记录;如 183+124+81+44 等分组全过) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1834 passed / 0 failed / 16 deselected**(4:22;基线 1813 + 本轮 21 新测试) |
| G01 隔离 | `/tmp/safe_g01_s5b_hit50_v3.py`(沿 s5b_hit50 G01 血统:路径 allowlist、SHA 前后核验、变更集精确披露、`python -B`、`-p no:cacheprovider`) | **exit 0;1823 passed / 10 skipped / 17 deselected**(4:19;相对 v2 G01 1802 = +21 新测试;输入 SHA 失配 = [];pyc 7(子进程缓存例外,同前两轮模式);expected_changed == observed_changed = 恰本轮 7 源文件;4 新输入 vs v2;实际 HEAD 35727eb + dirty=true 记录于 preparation.json) |
| 父基线红绿 | 4 个新测试文件在父 HEAD 35727eb 隔离 worktree(删除后重建亦可) | **17 红 / 4 绿 / 21**:红 = 全部新行为断言(wv1 4/4:wv2 7:wv3 4(ImportError=前置门函数缺席);wv6 2);绿 = 保持控制(wv2 元素缺席/filtered 负控 2 + wv6 合成档聚合/入口锁 2 —— 断言的是新旧一致的不变量) |

## 十、本轮改动清单(提交内容)

- 源码(7):`pollutant/{search, runflow, s5b_compiler,
  recorded_source, s5b_builder, evaluation, s5b_scoring}.py`
  (+413/−100 行);
- 新测试(4):`tests/test_ppv1_s5b_hit50_v3_{wv1, wv2, wv3,
  wv6}.py`(21 测试);
- 新文档(2):本交付书 + W-V4 mimo 请求草稿;
- 证据(未跟踪,按 AGENTS.md 默认留 /tmp 易失):
  `/tmp/s5b_v3_impl/`(W-V0/W-V2/W-V3 探针脚本与输出、哈希清单)、
  `/tmp/g01_s5b_hit50_v3/`(G01 完整产物)、
  `/tmp/safe_g01_s5b_hit50_v3.py`(sha256 `bdfe56569d1231ed…`)。

## 十一、金标边界自查声明

- 实施期零真实模型调用、零花费、不 push、不部署真实批、不改
  封存/冻结产物;scorer 排序规则 (created_at,event_id) 与全部冻结
  判据零触碰(反事实重算不改判据;W-V1 只改入队时序装配);
- 未读 298 题卷/金标/旧答卷/封存逐题 run;允许例外仅按任务书 §1:
  v2/v1 批根 metrics/manifest 池诊断/runs 答卷侧**聚合**(W-V0
  探针的 rank/桶/n_candidate_events 标志、W-V3 的池模板/事件
  身份/时序字段、底物串来自 manifest 预测侧输入);**逐题金标
  内容一律未读**(W-V2 分类探针的 donor/products 为授权语料库
  记录 = 预测侧,非金标);
- 远端只读、零落盘、零写;探针经 v2 批同源代码快照(身份核验
  84/84 文件一致)执行;
- 合成测试分子与真实 298 金标零重叠(乙醇/氯酚级合成小分子)。

## 十二、待复审问题清单(给主会话)

1. **W-V1 方案 A 的极限并发语义**:单写者纪律下事务内 MAX 串行;
   极限并发退化为 action_id tie-break 旧语义(不损坏)。是否需要
   更强保证(如跨进程锁)由复审裁定(当前批为单协调者,不构成
   阻塞)。
2. **W-V2 恢复面如实偏小**(4/228 记录级):映射层 47/116 恢复但
   深层门(charge 24/stereo/触顶)拦截 —— 这些属 W5 保留边界与
   预算纪律,不在本轮授权内;编译通过数不冒充命中数,真实 U 增益
   以新批复测为准。
3. **stereo 消解型设计草案(不实施,供复审)**:手性中心随 sp3→sp2
   键级变化消解(如二级醇氧化成酮)现被 stereo_changed 拒;设计
   方向 = "立体变化若发生在键级变化原子上,则手性为键级变化的
   派生属性(执行器 sanitize 自然结算),非独立立体 op"——
   升级须按 W-V2.4 条款先交设计复审;v1 命中面约 2-3 题在此类。
4. **语料 v2 不换装**:审计显示净更差(76<84)+ center 数据缺陷
   59;若下轮修语料(center_atoms 与 mapped_lhs 一致性 + 剩余
   unmapped 反应原子),预期恢复面 = transform_no_change 主部
   (v1 命中面 ~5 题)—— 属语料资产轮,须新身份。
5. **W-V4 送审**:mimo 请求草稿是否按通道 A 自动送审(规则级零
   金标)或留用户逐次拍板,由主会话按 AGENTS.md 评审-回修循环
   条款决定。
6. **父基线红绿的 4 个绿项**为保持控制(新旧一致的不变量),
   非行为翻转 —— 与 L01 轮"三个正控在父上同为绿"同模式,如实
   披露。

## 十三、成本与后续

- 实施期真实模型费用:**0 CNY / 0 次调用**(全轮零网络模型、
  零判分 LLM)。
- 后续(任务书 §3):主会话复审 → 有阻塞回修 / 通过转
  `ready_for_real_retest` → 新预注册冻结(代码/资产/protocol/
  prompt/池/融合/排序/profile/模型身份;W-V1 时序装配与 W-V2/V3
  变化全部进入新批身份)→ 首批 profile 沿 v2 冻结值 → 冒烟前缀
  10 题 → 同模型真实 298 → 零 LLM 判分(§9-4 配对硬门 + 本轮
  §9-④ 程序门双保险)。
