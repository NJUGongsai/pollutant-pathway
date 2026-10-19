# T-D/E E1 交付书（T-E + T-D-A/B，2026-10-19）

> 交付=`docs/TASK_T_DE_E1_IMPL_2026-10-19.md`（v2）的实施；生效口径=FROZEN_V3 +
> Codex 两轮设计复审终口径（`docs/T_E_RUN_IDENTITY_DESIGN_CODEX_{REVIEW,REREVIEW}_2026-10-19.md`）。
> 复审状态：**E1a / E1b 实施复审均已回件=放行（P0/P1/P2=0；E1a P3×4、E1b P3×3；代 Codex 通道）**
> ——报告 `docs/T_DE_E1A_CODEX_REVIEW_2026-10-19.md`、`docs/T_DE_E1B_CODEX_REVIEW_2026-10-19.md`
> （证据各在其 `docs/review_evidence/` 目录，REVIEW_MANIFEST 索引；按惯例未跟踪）。**已随轮提交
> （提交面与 D1.2 耦合，沿 P3-COMMIT；提交 `d758845`）**。⚠ 提交后 T-H 前置 delta（P3-IDENT/
> P3-LABEL）另随提交，postdates E1a 锁定（builder `463b42e2`→新值），零判据变化、T-H 门确认。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩。

## 1. 交付构成

**E1a（T-E 记录侧形式归一 + build_identity）**：
- `src/pathway_v43/pollutant/recorded_source.py`：算子（`record-side-formnorm-1`；默认
  `Uncharger()` 实跑+同原子状态核短路；map 保留；整候选消费视体 all-or-nothing；成功域双遍固定点）
  + 三通道注入（recorded compile 入口 / corpus 分类前统一视体贯穿 NC-10 / analog for-ref 视体）
  + 全形态审计（三值 + trace + spec 条件五键）+ 常量/指纹；
- `src/pathway_v43/pollutant/s5b_builder.py`：analog 视体接线 + 审计两键 + 批级四键
  （版本/指纹/路由注记/覆盖限制）+ `build_identity.json` 旁块；
- `src/pathway_v43/pollutant/s5b_worker.py` + `src/pathway_v43/storage/build_identity.py`（新）：
  首消费核对（四拒例+输入字节）+ run 来源 ledger（O_EXCL 唯一不可覆盖）+ 恢复同核；
- 新测试 33（`test_ppv1_s5b_t_e_formnorm.py` 16 + `test_ppv1_s5b_build_identity.py` 17）
  + 版本/契约断言同步 8 件；
- 版本：`s5b-pool-policy-8→9`、`s5b-recorded-source-3→4`；route 不升+机读绑定注记。

**E1b（T-D-A/B，ppv1-criteria-v3 披露轴）**：
- `evaluation.py` +865：`PPV1_CRITERIA_V3` 常量/白名单/resolve（fail-closed 门）+ 双臂注册表与
  指纹（四臂 param_sha256）+ 配对披露（A 双臂布尔/臂名/分臂指纹；B 启用臂+敏感性臂；B-6 碳酸
  闭集 tri-state；B-5 双布尔+单归属 A→B+双满足）+ 节点披露（`criteria_v3_normalized_identity`；
  **match_status/S5A-01 封顶零改动**）+ 批级块（分列计数/恒空 promoted/档 A 措辞/芳香与单批句）；
- `s5b_scoring.py` +18：批级透传（v1/v2 零新键）；版本断言同步 1 件；
- 新测试 17（`test_ppv1_criteria_v3.py`）；**档 A：只披露、不授 strict、不进 hit@1**。

## 2. 验收数字（摘要；详见各自验收产物）

### E1a（`reports/ppv1_s5b/t_de_e1_2026-10-19/e1_te_impl/REPORT_e1a_acceptance.md`）

- P3 **64/27**（L1-pure 58/58）复现；**发货口径 P4 = 20 行/9 题**（recorded 3 + corpus 6 +
  analog 11——**analog 11 不再因归一丢号**；对照前置 1 t2=9/6 系缺陷下读数）；幂等 158/158 固定点；
  map 丢号缺陷 0 回归；N8 零、N9 全正；N10 冻结事实逐事件全等（v1 per_qid 298/298、桶对齐
  298/298；v2 臂 hits=92/126/130 与冻结探针一致）；
- **双树差分（修复后重跑，298×2）**：unaffected 25 零漂移；affected 273 逐差异归因
  （**run_inputs 变化 98 题 / 诊断旧投影变化 177 题 / drift=0 / 闭包 all_pass**）；
  审计 schema：candidates 5,304 行全带三值；applied 2,723 行 trace+source_ref 全；
  risk present 209 / unknown 2,294（human_review 2,503）；
- ⚠ **机具修复披露**：首版双树探针 `sys.path` 次序 + `--tree` 目标双层缺陷使两臂均加载工作树代码
  （旧树产物机读实锤）；主窗口修复（次序翻转+`--tree …*/src`+meta `module_file` 自证）后重跑，
  修复后产物为唯一有效证据（报告 §4/复审请求 §0 已如实披露）；
- 自披露风险（待复审裁定）：worker ledger 时序口径（核对后、start/resume 前；「run 创建后 driver
  前」字面插入点不存在）、legacy 边界宽度（无旁块且 manifest 未声明 ⇒ disclosed 模式）、
  t1 读数差（18/8 vs 9/6 归因 D1.2 compiler-5 映射补全）、带电荷夹具拒因迁移（charge→tnc，仍拒
  不入池）、「3 件质子化/形式差」登记差（56-pass 子集 vs frame 机械计数 13/8）；
- 全量 not-slow：**见 §4（主窗口最终树复跑记录）**；E1b 侧记录的实施中同树读数（2259/1）中唯一
  失败件 `test_ppv1_s5b_hit50_w23456.py::test_w4_pool_provider_backfill_and_order` 已随 E1a
  拒因迁移同步更新（charge→tnc 语义变更，作用面断言保留）。

### E1b（`reports/ppv1_s5b/t_de_e1_2026-10-19/e1_td_impl/e1b_acceptance_summary.md`）

- P1 默认臂 **14/14**、立体保留臂 **13/14**（唯一对 `RXNG_50891a38435` 逐对披露）；P2 两臂各
  **6/7**（差 1 对为 composite 题 TAUTOMER 节点对——**与前置 1 的 6/6 口径差已披露，待复审裁定**）；
  N1 0/23 相等（两臂）PASS；N2 0；N3/N7 同 payload 逐位一致；N4 合成单测钉死（批级真空已披露）；
  N5/N6 PASS；B-5 四布尔与前置 1 逐格一致、**双满足 0 对**、单归属 {tautomer 15, protonation 6,
  none 23}；四臂指纹与前置 1 **4/4 一致**；`tautomer_promoted_nodes` 恒空；
  **v1 字节不变 / v2 行为不变 / v3 显式启用**（三断言 + 批级 sha 对照）；旧批零回写；
- v3⊇v2 承载选择（单一改动点）与 45/44 配对口径差：**待复审裁定**。

## 3. P3 登记项

- 前置 1 登记（供 C1 处置）：立体保留臂 13/14 相等——FROZEN_V3 §4.4 C1 所引「擦除唯一机制」未获
  重算支持（唯一依赖擦除对 `RXNG_50891a38435`）；**不改变档 A 语义**，逐对原子级溯源仍为待补化学
  门槛；
- E1b 登记：N4 批级真空（合成面证据）；N2 沿前置 1；P2 6/7 口径差；单批零读数不可外推句。

## 4. 全量回归（主窗口，最终树）

- 命令：`~/miniconda3/envs/depending43/bin/python -m pytest -p no:cacheprovider -q -m "not slow"`
  （`PYTHONDONTWRITEBYTECODE=1`）；
- 基线（开工时树，D1.2 后）：**2243 passed / 0 failed / 16 deselected**；
- **最终树（D1.2+E1a+E1b 全在树，主窗口复跑）：2293 passed / 0 failed / 16 deselected（353.2s）**
  = 基线 + 50 新测（E1a 33 + E1b 17），**零翻转零失败**。

## 5. 下一步

- E1a/E1b 复审回件 → 回修（若有）→ 放行 → **分账提交**（E1a/E1b 各一提交；D1.2 独立一提交）；
- 交付随 CC 消费（T-H 凑批前置：D1/E1 收口 → 预注册+付费=CC）。