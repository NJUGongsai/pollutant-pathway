# T-G Step C2 R2' 实施交付 — 代 Codex 复审报告(2026-10-19)

> **终判定:放行 C2 交付。P0=0,P1=0,P2=0,P3=2(非阻塞,登记处置)。**
> 通道 provenance:CC 指派 ZCode 主会话**代替 Codex**(额度断流期)执行本复审;
> 执行=主会话读码级审(冻结设计合约/diff/矩阵测试/探针方法学)+隔离副本子代理
> (测试复跑/七探针复现/F1-F4 逐字对照/负控与形状交叉核验);评审独立性不做背书,
> 结论采信到文件与程序证据互证范围;正链 Codex 恢复后可复核确认。
> **题域标签:298=RHEA 通用酶学/已见题。以下 647/1192/3797 面、44/26、150/54、
> 6/42 等全部数字为实施验收与探针口径,非判分成绩、非预注册投影,不外推;
> 探针 ≠ 预注册 ≠ 成绩。**

## 一、审查对象与冻结事实

| 项目 | 事实 |
|---|---|
| 审查对象 | HEAD `a31e227` + 工作树未提交实施改动:src 2 件 +728/−150、tests 7 件修改 +71/−23、新增 `tests/test_ppv1_s5b_c2_center_anchor.py`(14 测)——**合计与请求书 +799/−173 吻合(账实相符)**;探针产物 `reports/ppv1_s5b/t_g_fix_2026-10-19/c2_impl/`(gitignored 新批根) |
| 冻结哈希 | builder `e07b29de…`、compiler `aa6806b8…`、新测试 `d9dcbc5b…`、四件关键探针 JSON(完整 sha256 见证据清单);**审查期间被审 10 件 T0(08:48Z)/T1(09:16Z)双时点 sha256/mtime 零变化,无并发干扰** |
| 对照基线 | F1-F4 与跨版本对照的基线=`d9cee97`(C1 收口)git archive 只读快照;compiler-3/policy-7 → **compiler-4/policy-8/新增 route-f1f4-1**(diagnostics `analog_route_truth_version` 承载) |
| 隔离执行 | 副本 `/Volumes/CC/tmp_tg_c1_review_27133a49`(增量 rsync 后关键件 sha 核对启用);python 3.11.16(depending43)、pytest 9.1.1、`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`;探针脚本 REPO/OUT 常量适配逐处记录 |

## 二、逐条裁定

### Q1 解耦接线 — **通过(P1=0)**

- **F1-F4 一字不改(对照 d9cee97 逐字核验)**:F1 `template_elements_fit` 可执行代码逐字符零差异(仅 docstring 按设计 §3.2 要求改写双角色:路由真源+判据原样);F2 `analog_cosub_supply` 全函数 77 行**逐字节相同**;F3 wildcard 拦截条件式+计数表达式逐字符一致(缩进因提前 continue 重构浅一层,结局与基线 fall-through 等价:no_alignment+pregate_skipped+不供给不编译);F4 加袋串构造 `substrate+"."+".".join(...)` 逐字符一致、直编/no_supply 均 raw、F5 只读 f4 无反写。
- **F5 只对 F4 冻结输入判准入、三位置**:`_f5_gate` 定义 1 处、调用恰 3 处(直编 raw/供给后二次门 supplied/no_supply 编译前);`center_anchor_probe` 仅经 `_f5_gate` 消费;与编译层中心枚举**共用同一实现**(`build_center_query`/`enumerate_center_alignments`,判据单一来源)。
- **无绕过路径**:F1/F2/wildcard 判据在全 src 均唯一消费位;直编分支进入条件=F1 过(未用中心命中);F3 先于本路径任何 F5 调用(route 行 `f5=not_evaluated`、编译调用 0)——§6.2 矩阵 #2 的 `[*:4]` 反例(复审 v3 门替换合成反证)由 r2_2 单测关闭:probe_calls==[]、compile_calls==[]、记数 1。
- **版本键与 docstring 如实升位**:三键升位/新增属实;policy-8 注释块写明 F1-F4 冻结+F5 语义+池策略配置零变化;`template_elements_fit` docstring 写明「旧元素门=路由真源」角色(D-8 要求)。

### Q2 歧义硬拒 — **通过(P1=0)**

实现:`order` = 度全等子集 G 优先 + **M 全量**枚举(`[ok]+[not ok]` 覆盖全部命中),被 prefer 排序靠后的非全等候选**不跳过**;逐候选执行冻结编辑段,按净产物目标归并 `seen_targets`;**>1 目标 ⇒ 结构化 `ambiguous_alignment`**(机读 `competing_targets`/`n_targets`/`all_matches_verified=True`,披露只补充不替代拒);单目标 ⇒ 取 prefer 序首个(G 优先消歧、G 空回退全体=`fallback_all_presence` 容忍保留);预算截断 ⇒ `alignment_limit_exceeded`+`truncation_axis`+`n_matches_at_limit`+`unverified_matches`(不得称唯一目标已证)。§6.1 矩阵 1-5 全部固化为单测**且经 builder 公共入口触发**(同根消费入口要求):m2_1 即设计级 P1 反例 `OCCC(O)C`(competing_targets ⊇ {CC(=O)CCO, CC(O)CC=O})、m2_2 证伪「非全等一律拒」、m2_3/m2_4 正负控、m2_5 以 65×CCO 触 64 上限并断言 `f5=defer` 行字段(截断在公共入口的 defer 语义同测)。

### Q3 验收数字 — **通过;F5 defer 口径裁定=合规,无需回修**

**可复算性(子代理隔离复跑)**:定向 14 新件全过+7 修改文件 163 passed;全量 not-slow **2229/0/16 deselected**(基线 2215+14 零翻转,366s);七探针复现(03 unlock/05 byte_invariance/07 replay **逐字节一致**;01/02/04/06 canonical 相同,仅 elapsed_s 与路径回显差)。核心读数逐项复现:**负控 0/72**(72/76 双口径与 150 行新编译面交集=0)、**材料 6/7**(与设计 §2.3 兑现 7 件=6 maintain+1 env 精确对齐;wildcard 件 a-5f12 直编在 6 内、生产 F3 拦截 ⇒ 生产口径 5/42 自洽)、**D-6 存疑件 a-21c2 单独分账**(不在负控集、在 new_rows、归档行在案)、**128/128 保持、lost 0**、**647 面 44/26、1192 面 56/29、全面 150/54**。

**F5 defer 口径(实施方自报的设计未钉死处)— 裁定合规**,依据四条:
1. **结构保证**:F5 `absent`(中心查询零命中)是唯一可短路面——builder 直接记 no_alignment、编译调用 0(省预算);此面拒因与编译层同源必拒,**「省预算不改结果口径」不变量由代码结构成立**,拒因迁移不可能混入 absent 行。
2. **defer 发编译是「同源拒因、不冒名」的唯一诚实实现**:空中心(`center_empty:*`)、截断(`alignment_limit_exceeded`)、变换提取异常在编译层各有稳定拒因;若在前门位冒名 no_alignment,反而违反真源表 F5「与编译层同源拒因」并破坏 §8.1-6 的机读区分义务。
3. **设计自证**:§8.1-6 明令拒因码机读区分(`center_empty:*`/`charge_edit_unsupported`/`no_alignment`)「实现轮保证落地」——拒因迁移正是该条款的直接后果;主验收行本身要求「拒因迁移+flipped 清单+drift 逐行披露」。
4. **披露完备**:迁移 14 桶全机读(`reason_drift_hist`,含 1042 行 no_alignment→transform_no_change 主桶)+150 行新编译明细+逐行 route/f5/execution_input_sha256 字段;m2_5 单测把 defer 语义固化在公共入口。

### Q4 对拍与挤位 — **通过;跨版本对照处理成立**

- **前提失效处理成立**:旧双臂 byte 探针的「arm A monkeypatch=policy-6 基线等价」前提在 compiler-4 下确实失效(编译器本体变了,arm A 不再等价)——交付**如实保留**旧探针 all_pass=False+drift 185 读数(不销毁不利证据),另建**跨版本对照**:基线=`git archive d9cee97` 真实源码、独立进程双臂、同题卷同 provider 配置——方法学**强于**原前提(真实基线 vs monkeypatch 等价论证)。
- **数字闭合**:identical **181** + pool_delta **37** + spec_internal_change **80** + run_id_only 0 = 298;非目标题 run_inputs **零字节位移**成立;基线/变体 meta 版本键如实(compiler-3/policy-7 vs compiler-4/policy-8)。
- **挤位披露完整**:37 题逐题 added/removed spec 键清单(真挤出 removed>0 仅 7 题,其余纯新增);80 题逐题 changed_spec_keys;行 schema 新增键(route/execution_input_source/execution_input_sha256/f5/light_gap)单列不混入漂移计数。
- **诊断漂移如实披露**:字节全等 181 题中 **150 题诊断旧键漂移**(拒因迁移在非目标题的投影)逐题清单在档(`diag_drift_on_identical_questions`)——见 P3-DOC-02 措辞登记。
- **unlock 面**:48 行/35 题(36+12=48 算术闭合);**drift 21 行=12 新可达(compiler-4 中心锚定)+9 继承 C1 wildcard 边界,零第三类**(与 C1 复审的 9 行同批,两面互证)。
- **l1 Stage0 halt 13 题**:同根(chain13 封存 manifest 为旧实现产物)如实披露、全停不硬凑,处置恰当。

### Q5 红线 — **通过,无越界**

diff 边界=builder/compiler/8 测试文件(**判分侧 evaluation/s5b_scoring/recorded_source 零触碰**);池配置常量(RAW_TOP 24/池宽 8/阈值 0.45/对齐预算 64/排序/融合/截断)零变化;轻刀 A=纯读归因字段(F1 判据零改动,`_light_gap_coverable_by_bag` 只写诊断行);`git status` ahead 4 **未 push**;新批根 c2_impl(gitignored);探针零模型零网络零 LLM、金标/题面/封存逐题 run 零接触(run_inputs 只含题面底物+池 spec 口径);**金标输出根守卫 fail-closed 正向实证**(子代理探针 05 首跑被 `check_output_root` 拒绝=守卫在隔离场景照常起效,适配后走合法根)。

### §8.1-5 放行条件(负控扩面「多原子新片段无来源」)— **实证闭合;专项合成测留 P3 补强**

- **无锚子类**(全新组分无保留锚):L1 定义「限 lhs 侧存在原子+新增原子经保留锚入 L1」⇒ 结构上中心为空 ⇒ `center_empty:added_without_anchor` 结构化拒——`tests/test_ppv1_s5b_hit50_v4b.py` 既有测扩展固化(结局不变:仍拒、零入池)。
- **有锚子类实证**:150 行新编译面 **added_maps 全部=0**(该形状在 298 面新编译零暴露);「raw+多原子新增+compiled」P1 形状 **0 行**;3 行 `template_elements_no_fit→execution_failed` 全为 tpl-rhea:49462(supplied 路由、added=0、执行校验如实拒)。**结论:该形状 0 翻过成立**(结构守卫=执行校验原子账+center_empty,实证=零暴露)。

## 三、P3(非阻塞,登记处置)

| 级别/ID | 事实与处置 |
|---|---|
| **P3-TEST-01** | 有锚多原子新增(无来源)形状无专项合成负控单测(现闭合依据=实证零暴露+执行校验结构守卫+无锚子类固化)。实证面强于合成面,但 298 面零暴露不等于未来批零暴露——建议下一测试轮补一条合成负控(模板加 2 原子锚定片段、无袋源 ⇒ 执行校验拒/如实出因),固化该形状类 |
| **P3-DOC-02** | 设计 §6「非目标字节不变:run_inputs 逐字节+**诊断逐键**,drift≠0 即停」与主验收「**拒因迁移**逐行披露」在 C2 变量下必然张力(迁移改的就是诊断面值):本轮 181 字节全等题中 150 题诊断旧键漂移,交付按「字节面守线+漂移面全披露」处置(逐题清单在档),裁定成立;但两条验收行措辞应在下轮预注册修订时统一(何为非目标题的诊断豁免面),避免下刀再解释。修订归 CC/预注册轮,不归本交付 |

## 四、收口

**放行 C2 交付(s5b-compiler-4 / s5b-pool-policy-8 / s5b-analog-route-f1f4-1)。** 冻结设计(FROZEN_R2P)的两大硬验收矩阵(§6.1 歧义硬拒 1-5、§6.2 解耦接线 1-4)全部固化为公共入口单测并经隔离复跑;负控 0/72、D-6 分账、128/128 保持、可达重算三面、42 件重放 6/42(B+C 拍板的 C 探针兑现:0/42→6/42,生产口径 5/42)全部机读复现;F1-F4 同输入承诺逐字核验成立;红线零越界。两条 P3 随下轮处置(补强建议+预注册措辞统一),不阻塞本交付提交。R2' 后重放按处置 C 作为 T-G C2 修复验收探针的预期已兑现方向(compiled 0→6>0);正式发车(T-H 付费批)仍归预注册与 CC 拍板,本报告不操作任何开关。

## 五、纪律与证据索引

只读评审:原仓写入仅 `docs/review_evidence/t_g_c2_impl_codex_2026-10-19/`(41 件+本清单)与本报告;未动 src/tests/既有 docs/AGENTS.md;未 push、零外部模型;git 只读(archive/GIT_OPTIONAL_LOCKS=0);子代理自查更正两处(F 交集键长笔误重算覆盖、H 粗筛误报以执行校验+added_maps 网格为准)如实登记,交付=修正版。

证据(`docs/review_evidence/t_g_c2_impl_codex_2026-10-19/`,MANIFEST.sha256.txt 41/41 校验过):`README.txt`(命令全文/时间线/环境/适配逐处)、`stdout/`(全量+定向+七探针)、`comparisons/`(F1-F4 逐字 diff、F_VERIFICATION_SUMMARY、probe_compare_01-07、F3_fixed_intersection、F4b_direct_production_semantics、F_G_analysis、H_added_atom_shape 等)、`scripts/`(9 个核算脚本)、`REVIEW_MANIFEST.json`(冻结哈希与结论)。

本报告与证据按惯例留未跟踪,由 CC 定期自决。
