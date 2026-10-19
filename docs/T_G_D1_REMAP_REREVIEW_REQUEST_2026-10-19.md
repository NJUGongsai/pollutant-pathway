# 复审请求（二轮）— T-G Step D1.2 P1-D 回修 + P1-E 闭合（2026-10-19）

> 请求类型：**回修同范围复核**（依据首轮报告 `docs/T_G_D1_REMAP_CODEX_REVIEW_2026-10-19.md`
> §四 P1-D/P1-E 的「最小收口」与 §五 收口条款）。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩。
> 通道：Codex 正常通道额度断流期 ⇒ **CC 手动发送或代审**（provenance 如实标注；放行类结论
> 正链恢复后可复核）。
> **工作树状态**：D1.2 改动仍**未提交**；工作树同时含 E1a/E1b 未提交改动。**本轮复审范围只限
> D1.2 面**：`src/pathway_v43/pollutant/s5b_compiler.py`（未再改动，sha 仍 `4cf61a8a…`）、
> `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_remap/` 下回修产物。其它工作流改动不在范围。

## 1. 请评什么（按序，全部只读）

1. **首轮报告（回修任务书）**：`docs/T_G_D1_REMAP_CODEX_REVIEW_2026-10-19.md` §四 P1-D/P1-E、
   §三.2/三.3、§五.3；重点核「最小收口」逐项；
2. **回修产物（本轮对象）**，均在 `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_remap/`：
   - `d1_remap_c2probe_diff.py`（重写版，sha256 `9eacda70800d8b60…`；helper 改
     `align_ordered_subsequence` 记真实命中索引；六类分类；全量落盘；因果字段）；
     产物 `d1_remap_c2probe_diff.json`（**1.2MB**，全量 298×2 分类行 + 201×2 诊断逐键 +
     unlock 454 行全量表）+ `.log`；
   - `d1_remap_replay.py/.json/.log`（post 改指单变量树；新增 `frame_rows` 1886 +
     `migrated_tnc_rows` 616 全量行级）；
   - `p3_chem_diagnostic_pack.md/json` + `d1_remap_p3chem_pack.py`（P3-CHEM 机械诊断包）；
   - `d1_remap_summary.md`（§2 已改重账读数、新增 §6 P1-D 对照）；
   - `oldaccount_v1_20261019/`（旧账归档，对照用）；
   - `p1e_closure_evidence.md` + `p1e_idempotence_x12.log` + `p1e_novel_failure_x4.log`（P1-E）。
3. **单变量口径核验**：reproduce 提示——pre=`git archive HEAD src`（compiler-4
   `aa6806b8…`）；post=`HEAD(src)+仅工作树 s5b_compiler.py`（compiler-5 `4cf61a8a…`）；
   脚本 meta 记录 `trees_identical_except_compiler=true`；如需复跑约 2.5 分钟
   （/tmp 快照易失，复跑=重建两树+两探针+diff；命令在脚本 docstring）。

## 2. 评审要求（逐项给结论）

- **P1-D 四缺陷逐项**：①前插/中插吞噬（helper 修法是否真闭合：未匹配新 spec 全保留+逐件
  remap 披露核验；复审举证件 `RXNG_0faafc6` 臂B added 0→1）；②等长 version-only 拆分
  （逐路径差 100% = `compile.compiler_version`？有无例外）；③明细截断（全量落盘面是否齐：
  298×2/201×2/454/1886/616；有无仍截断处）；④other_diff 因果（**12 件 removed 类的机读解释
  是否充分**：同 key spec 仍在 post 池、差仅 `compiler_version`+`merged_source_keys`
  （W4 同签名合并 provenance 重组）、候选层全在——**判「池层可观测变化」口径是否可接受**，
  含对 `merged_source_keys` 重组本身的机制核）。
- **新增件披露全量核**：臂A 278/278、臂B 266/266 `applied=true`+`n_new_maps` 逐件——抽查复算；
- **replay 面零差确认**：A/B/C/D 与旧账逐项零差（17/17；732→116；33 件 2 翻转；1154 行零漂移；
  锚 mismatch 0）；1886/616 行级落盘齐否；
- **unlock 行级**：4 结局变化全点名（15143/15407→compiled；42649→center_empty:removed_only；
  49530→ambiguous_alignment）是否与你的 overlay 复核一致；
- **P1-E 闭合证据判定**：干净树全量 **2293 passed / 0 failed / 16 deselected**（含 E1a/E1b 在树
  ——按回修范围应说明：D1.2 单变量面=算法本体已在首轮通过；本证据满足「收口后干净树全量绿」
  还是需要**仅 HEAD+D1.2 的 overlay 全量绿**？请给裁定口径与（若需要）复现要求）；
  幂等件 ×12 变 seed 全绿 + novel_failure ×4 全绿是否满足「专项 ≥10 次」；
- **P3-CHEM 诊断包**：完整性（首轮 §三.1 要求的字段：原 judgement_basis+mapping_anchor、原模板/
  底物、补映射前后模板+完整 transform、最终 execution product、字段来源与哈希）齐否；
- **新问题**：脚本重写是否引入新缺陷（分类互斥/完备性、行账闭合恒等式）。
- 终判定=「放行 / 需修正 / 退回」（P0/P1/P2 制式）。

## 3. 输出（写到文件）

`docs/T_G_D1_REMAP_CODEX_REREVIEW_2026-10-19.md`：
1. 头部：终判定 + 一句话理由 + 读时 sha256（脚本+产物）+ provenance + 读件清单；
2. P1-D/P1-E 逐项闭合判定表（项 | 判定 | 依据（行号/产物字段）| 要求动作）；
3. 新问题（若有）；4. 「随轮交付书可直接消费的验收结论」汇总（**含提交放行明确措辞**）。

**纪律（写死）**：只读评审+只新增本报告与你的证据文件（`docs/review_evidence/t_g_d12_rereview_2026-10-19/`）；
**不动 src/tests/既有 docs（并行工作流在编辑，禁止触碰）**；不访问金标/题面/封存逐题 run；
探针如需复跑一律新 tmp、`PYTHONDONTWRITEBYTECODE=1`、`-B`、`pytest -p no:cacheprovider`；
不 git add/commit/push；不调用外部模型/网络。