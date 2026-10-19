# T-G Step D1.2 确定性模板补映射 交付书（2026-10-19）

> 交付=`docs/TASK_T_G_D1_REMAP_IMPL_2026-10-19.md` 的实施；定刀依据=D1 交集探针
> （`docs/TASK_T_G_D1_PROBE_2026-10-19.md`；交集 0/17 ⇒ 不接线、走确定性重映射）。
> 复审：`docs/T_G_D1_REMAP_CODEX_REVIEW_2026-10-19.md`（**代 Codex 通道**：CC 指派 ZCode 主会话
> 代审，正链额度断流期处置；正链恢复后可复核）——**终判定「需修正」：P0=0、P1=2（P1-E 验收闭合、
> P1-D 对拍证据账）、P2=0、P3=4；编译器算法本体零缺陷面（规则保真/触发面/披露/A/B/C/F 全过且经
> 隔离复现）**。P1-E 已由主窗口闭合（`d1_remap/p1e_closure_evidence.md`：干净树全量
> 2293 passed/0 failed；幂等件 ×12 变 seed 全绿）；**P1-D 回修已完成并重账**（审计脚本重写
> sha `9eacda70…`：六类分类拆分 / 新增件披露 278/278+266/266 / 全量 298×2+201×2+454+1886+616
> 行落盘 / removed 12 件机读因果=同 key spec 仍在·差仅 `compiler_version`+`merged_source_keys`；
> 单变量树=HEAD(compiler-4) vs HEAD+仅 s5b_compiler.py(compiler-5)，
> `trees_identical_except_compiler=true`；replay 面与旧账逐项零差）。
> **二轮复核（P1-D 回修+P1-E 闭合同范围复核）：`docs/T_G_D1_REMAP_CODEX_REREVIEW_2026-10-19.md`
> ——终判定「放行」：P1-D 四缺陷逐项闭合（评审侧独立端到端复跑全数字复现）、P1-E 以
> 「收口干净树 2293/0/16 + 幂等件 ×12 变 seed 全绿」满足条款；新增 1 条前置登记
> P2-CHEM-FORWARD（T-H 前闭合，不阻塞本提交）。提交放行措辞：**可随轮提交**
> （编译器 1 件+测试 3 件+版本断言）；**建议 D1.2 与 E1a/E1b 同轮提交**，或拆提交时按提交态
> 补测后发货（P3-COMMIT）。**本交付的提交执行=待 E1a/E1b 复核回件后合议（同轮或拆提交）。**
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；全部数字为实施验收/探针口径
> （探针 ≠ 预注册 ≠ 成绩），非判分成绩、非预注册投影。

## 交付构成（实测，git numstat 为准）

| 文件 | 内容 |
|---|---|
| `src/pathway_v43/pollutant/s5b_compiler.py` | `complete_template_mapping`（v0 规则逐字移植）+ `_remap_unmapped_components`/`_remap_pair_components` + wrapper 层 **tnc 唯一触发点** + `template_remap` 披露 + `S5B_COMPILER_VERSION=s5b-compiler-5` + `S5B_TEMPLATE_REMAP_VERSION=template-remap-1`；F5 docstring 注（defer 语义保持） |
| `tests/test_ppv1_s5b_template_remap.py`（新） | 14 测：规则级 8（含幂等/确定性/新鲜号/签名巧合 fail-closed=P3-F）+ 编译级 3 + 回归 1 + 版本 1 + 首选负控 |
| `tests/test_ppv1_s5b_hit50_v4b.py` / `test_ppv1_s5b_hit50_w1.py` | 版本断言同步（compiler-4→5） |

## 验收（实测）

- **A（17 件）**：提取层迁移 17/17；**compiled 9** / no_alignment 7 / execution_failed 1。
- **B（全框 1,886）**：tnc **732→116**（保留=116 退化件全体）；迁移：no_alignment 368 /
  compiled 156 / ambiguous 58 / new_atom_placement 8 / execution_failed 4 / new_atom_charge 16 /
  aromatic_new_bond 6；env 608 全迁移、rhea 124（116 保留+8 迁移）；披露 applied 616/false 116/无 0。
- **C（负控）**：reject_correct 33 件；**reject→compiled 翻转 2 件逐名披露**
  （`a-2027e5910575bb3b`/`a-c6a1258f4db86523`，EAWAG-SOIL）——**复审处置（§三.1 链）**：维持
  「负控翻转、不计收益」；最小机械诊断包随 P1-D 回修组装（`p3_chem_diagnostic_pack.*`）；
  送既定化学复核链（v3.2 口径重判，代审即终审）按**补映射后面**材料重判；若 matched 规则后续
  变动 ⇒ A/B/C 迁移账全量重算（616/156 等数字不得沿用）。
- **D（非目标零漂移）**：全框非 tnc **1,154 行 drift 0**；unlock 48→50、pre-compiled 漂出 0、
  fail→compiled 2 行逐行披露；byte 臂A 76/216/4/**2**、臂B 72/212/4/**10**（other 全部同型
  阈值降载互动、逐行披露；**additive 全量明细未落盘=局限披露**）。
- **E（测试）**：定向 55 passed；全量 not-slow **2243 passed / 0 failed**（基线 2229+14 新测；
  零翻转）。
- **F（P3-TEST-01 专项负控）**：`test_signature_coincidence_fail_closed` 钉死（签名相同/拓扑
  不同 ⇒ no_gap 原样 + 编译层如实拒 tnc + applied=false 披露）。

## 口径与边界（如实）

- 补映射**只补 map 号**、零化学判断；补映射后一切判据=现行编译器原样；触发面只限 tnc；
- 116 退化件（rhea，无未映射缺口）不属本刀，维持原样；
- 产物 `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_remap/`（gitignored）；summary 为**主窗口**汇总
  （实施子代理终答环节被基础设施截断；脚本/json/log 为其落盘产物）；
- 机读 json 含机械编译产物串（非金标；gitignored 内）；报告 md 零结构串。

## P3 登记（复审 §四，非阻塞）

1. **P3-IDENT**：批级 diagnostics 无活 compiler 版本键（spec 级 `compile.compiler_version` 在位），
   policy-9 将横跨 compiler-4/5 两世代——**建议 T-H 付费批发车前补齐批级 `compiler_version` 键**
   （沿 C1 偏差窗口先例登记）；顺带更正 C2 轮报告「批产物无编译器版本」表述（spec 级实为在位）。
2. **P3-COMMIT**：`test_ppv1_s5b_hit50_v4b.py` 断言文件含 D1.2（compiler-5）与并行 T-E
   （policy-9/source-4）双工作流足迹——**提交时 D1.2 与 T-D/T-E 耦合提交或断言拆行**，避免
   单变量归因窗口（提交步骤执行时落实）。
3. **P3-LABEL**：`s5b_builder.py` policy8_route_note 静态文本嵌「compiler s5b-compiler-4」陈旧
   ——归 **E1a 回修轮**顺带更新（builder 属 E1a 文件面，E1a 复审未回件，不在本轮触碰）。
4. **P3-CHEM**：2 件翻转诊断包（§三.1）已组装（`p3_chem_diagnostic_pack.*`；二轮复核判为「完整」）
   ——送化学复核链（v3.2 口径，代审即终审）按补映射后面材料重判；**预期维持拒**（来源异议
   独立于对齐）；维持拒 ⇒ 登记「编译器-判读分歧面」2 件活例；若 matched 规则后续变动 ⇒ A/B/C
   迁移账全量重算（616/156 等数字不得沿用）。
5. **P2-CHEM-FORWARD（二轮新增，前置登记，T-H 前闭合，不阻塞本提交）**：两件=§8.1-5「有锚新增
   片段无来源」形状**首次实际进入机器编译面**（C2 轮「零暴露」结论仅适用其 150 面，本轮更正
   适用域）——判据对账条款（判读修订 2 来源校验 vs `_place_new_atoms` 不问来源）须在 T-H 付费批前
   闭合，或明示该类 spec 在 T-H 口径的排除/披露面。
6. **P3-MONITOR（二轮新增）**：幂等件 `test_crash_after_commit_resume_replays_prediction_idempotently`
   收口树 ×12 变 seed 不可复现原失败（按首轮条款「复现才根因」不阻塞）——**后续任何轮次该件
   再红，立即留现场根因，不得再按 flake 放行**。
7. **提交执行口径（二轮）**：建议 D1.2 与 E1a/E1b **同轮提交**；若拆提交，每个提交点须按该提交态
   补跑定向+版本断言件（建议全量）后方可发货。**T-H 付费批发车前**另有：P2-CHEM-FORWARD 对账闭合
   （或明示排除面）+ P3-IDENT 批级 compiler 版本键补齐。

## 下一步

- D1.2 放行后随轮提交（分账：D1.2 一提交）；
- 与 E1a/E1b 共同构成 T-G D1/E1 收口 → T-H 凑批前置（预注册+付费归 CC）。