# 评审请求 — T-D/E E1a（T-E 记录侧形式归一 + build_identity）实施复审（2026-10-19）

> 请求类型：**实施评审**（评审-回修循环；任务书 `docs/TASK_T_DE_E1_IMPL_2026-10-19.md` v2
> §1/§3.1/§4.1/§4.2；最终口径=Codex 二轮设计复审
> `docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REREVIEW_2026-10-19.md` §4/§5）。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩；零金标。
> 通道：Codex 正常通道额度断流期 → **由 CC 手动发送或代审**（provenance 如实标注；放行类结论
> 正链恢复后可复核）。
> **工作树状态**：E1a 改动**未提交**；工作树同时承载 E1b（`evaluation.py`/`s5b_scoring.py`）与
> D1.2（`s5b_compiler.py`）的未提交改动。**你的评审范围只限 E1a 文件面**：
> `src/pathway_v43/pollutant/recorded_source.py`、`src/pathway_v43/pollutant/s5b_builder.py`、
> `src/pathway_v43/pollutant/s5b_worker.py`、`src/pathway_v43/storage/build_identity.py`、
> `tests/test_ppv1_s5b_t_e_formnorm.py`、`tests/test_ppv1_s5b_build_identity.py`，
> 及被同步的既有测试（`git status` 中 E1a 相关的 `tests/test_*` 改动）——读时记录 sha256 并锁定；
> 其它文件改动不在范围、不得据此判 E1a 对错。

## 0. 交付说明（provenance，如实披露，评审必读）

- E1a 实施子代理在**收尾阶段被基础设施截断**（双树探针分片被中断、报告两节留占位、终答丢失）。
  主窗口接管完成并**发现/修复一处探针机具缺陷**：
  1. **双树探针原始形态无效（机读实锤）**：`te_two_tree_probe.py` 的 `measure` 原为
     `sys.path.insert(0, tree)` 后 `sys.path.insert(0, REPO/src)` ⇒ REPO/src 恒在 `sys.path[0]`
     压过 tree/src；且旧树快照实际布局为 `/tmp/e1a_old_tree/src/pathway_v43`（tree 参数须指
     到 `*/src`）。**两处叠加 ⇒ 原分片运行的两臂实际都加载工作树代码**（旧树产物带
     `pool_policy_version=s5b-pool-policy-9`、`recorded_source_version=s5b-recorded-source-4`、
     applied 事件与 formnorm 键——本应仅新树有）。**因此 E1a 报告 §0 的「全 298 双树差分
     零漂移」声明与任何基于该分片产物的读数均无效**，以主窗口修复后的重跑为准。
  2. **修复**：路径插入次序翻转（REPO/src 先、tree 后，tree 胜出）+ `--tree` 指到 `*/src` +
     meta 增记 `module_file`（每片自证加载树）。小样验证：旧树 `module_file=…/e1a_old_tree/src/
     pathway_v43/__init__.py`、applied_events=0；新树=工作树、applied_events>0。
  3. **重跑**：修复后完整重跑 298 题 × 两树（8 分片）并跑 compare；**该批产物
     （`/tmp/e1a_tt_{old,new}/`、`/tmp/e1a_tt_compare_full.json`）为 §4 验收的唯一有效证据**；
     主窗口已将其数字填入报告 §4/§6 并加注来源。全量 not-slow 亦由主窗口在最终树上重跑。
- 上述补跑产物/脚本在 `reports/ppv1_s5b/t_de_e1_2026-10-19/e1_te_impl/` 与 /tmp（运行时目录）；
  评审如需复核以产物 json/log 为准并**自行独立复跑**（复跑命令见报告 §4 与本文档尾部提示）。

**复跑命令（评审可用，隔离执行）**：
```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43 && export PYTHONDONTWRITEBYTECODE=1
PY=~/miniconda3/envs/depending43/bin/python; P=reports/ppv1_s5b/t_de_e1_2026-10-19/e1_te_impl/te_two_tree_probe.py
# 单题小样（先证两臂加载树）：
$PY "$P" measure --tree /tmp/e1a_old_tree/src --tag old --out /tmp/chk/old --limit 2
$PY "$P" measure --tree /Volumes/CC/Enzyme_Agent/dependingv43/src --tag new --out /tmp/chk/new --limit 2
# 全量：8 分片（old/new × shard 0..3，--shards 4），再 compare --old … --new … --out …
```

## 1. 你要评什么（按序，全部只读）

1. 任务书 v2 §1/§3.1/§4.1/§4.2/§5（最终口径与红线）；
2. 设计复审最终口径：`docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REREVIEW_2026-10-19.md` §4.1（build_identity
   生命周期与三类拒因）、§4.2（审计最小 schema：五键 + trace 逐字段 + H 口径 + risk_status 四值 +
   matching_scope）、§4.3（嵌套事务/A 臂）；
3. FROZEN_V3 §5 全节（语义权威：C-1 仅记录侧/底物侧不施加、C-3 三层分开、C-5 披露补齐、C-6 控、§5.3）；
4. E1a 验收报告：`reports/ppv1_s5b/t_de_e1_2026-10-19/e1_te_impl/REPORT_e1a_acceptance.md`
   （主窗口已补 §4/§6 占位）+ 同目录机读产物（`te_p3p4_batch_measure.json`、`te_replay_arms_*.json`、
   `n10_rescore/`、`old_tree_src_sha256.txt`、pytest 日志）；
5. 代码 diff（锁版本）：`git diff -- src/pathway_v43/pollutant/recorded_source.py
   src/pathway_v43/pollutant/s5b_builder.py src/pathway_v43/pollutant/s5b_worker.py` +
   `git diff --no-index` 或直接读 `src/pathway_v43/storage/build_identity.py`（新文件）+ 新测试两件。

## 2. 评审要求（P0/P1/P2 制式）

- **算子/事务**（复审 §4.1/§4.3）：默认 `Uncharger()` 实测三参数登记；**实跑+同原子状态核**短路
  （非「电荷向量」强断言）；applied/not_applicable/failed 按提交事务；**整候选消费视体
  all-or-nothing**（保 None/空/顺序/重数）；成功域双遍字节固定点 + failed 域确定性重现；
  applied 允许永久电荷；**map 号保留**（不得回归前置 1 的丢号缺陷）。
- **注入点**（P1-2 最终口径）：recorded=compile 入口；corpus=**分类前统一视体**贯穿分类/编译/
  装配/NC-10 两处声明；analog=for-ref 视体、**raw ref 不得再传编译**；raw 例外只限
  `record_equation`/`matched_component`；tier/召回/底物串零触碰。
- **披露**（复审 §4.2 逐字段）：全形态行三值标量 + trace（source_ref 含 matched_side_or_component、
  changes 源坐标、atom_correspondence、H=GetTotalNumHs(includeNeighbors=True) 且显式/隐式/邻接分列
  含 D 身份、matching_scope、intersection 用实际消费 query、risk_status 四值含 unknown 禁伪填、
  风险/unknown 行 human_review 义务）；applied spec **五标量键**条件性、trace_ref 可回指；
  未 applied 零字节；旧 diag 投影 vs 新 audit 分开验。
- **build_identity**（复审 §4.1）：旁块唯一权威、指纹排除仅 3 项；首消费核对（创建 run/调用前）；
  run 来源唯一不可覆盖持久化；恢复同核；三类拒因；**E1a §7.3 自披露的 ledger 时序偏差**（worker
  无「run 创建后、driver 前」插入点，ledger 落在全部核对后、start/resume 前）——判是否可接受或
  要求改法；**§7.4 legacy 边界**（无旁块且 manifest 未声明 ⇒ legacy_absent_disclosed）——判宽度。
- **验收**（§3.1 与 §4.1/§4.2）：P3 64/27、L1-pure 58/58、**发货口径 P4=20/9**（对照前置 1 t2=9/6
  与丢号缺陷说明）；幂等 158/158 固定点；**双树差分（298/298）**：未 affected 题 run_inputs 逐字节
  + 旧字段投影全等、affected 题逐差异挂 applied record_key 归因、drift=0；审计 schema 统计
  （applied 行 trace 完整率等）；N10 冻结事实逐事件（v1 每事件全等；v2 臂 hits=92/126/130 双探针
  一致）；全量 not-slow 零翻转；**§7 各项自披露**（t1 18/8 归因 D1.2、3 件口径差、拒因迁移、
  受控词登记、并行树声明）逐条裁定。
- 终判定=「放行 / 需修正（列 P0/P1）/ 退回」。

## 3. 输出（写到文件）

`docs/T_DE_E1A_CODEX_REVIEW_2026-10-19.md`：
1. 头部：终判定 + 一句话理由 + E1a 文件面读时 sha256 + provenance（并**如实记录「E1a 子代理被截断、
   主窗口补跑」的交付链**）+ 读件清单；
2. 复审 §4.1/§4.2/§4.3 与 FROZEN_V3 §5 逐条落实核验表（条 | 判定 | 证据（行号/产物字段）| 要求动作）；
3. 验收逐项判定表 + §7 自披露逐条裁定 + 双树探针与 N10 的独立复核结论；
4. P0/P1/P2 清单；
5. 「随轮交付书可直接消费的验收结论」汇总。

**纪律（写死）**：只读评审+只新增本报告与你的证据文件（`docs/review_evidence/t_de_e1a_codex_2026-10-19/`）；
**不动 src/tests/既有 docs**；不访问金标/题面/封存逐题 run；探针如需复跑一律新 tmp、
`PYTHONDONTWRITEBYTECODE=1`、`-B`、pytest `-p no:cacheprovider`；不 git add/commit/push；
不调用外部模型/网络；不得把主窗口补跑叙述当已执行事实——以产物为准独立复核。