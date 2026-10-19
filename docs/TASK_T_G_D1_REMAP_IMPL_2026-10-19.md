# TASK — T-G Step D1.2 确定性模板补映射（实施任务书，2026-10-19）

> **状态**：实施任务书（自包含；派实施子代理）。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；不外推 dev。
> **性质**：规则级、零化学判断的**映射完整性修复**（编号补全，不改任何结构内容）；
> 全部数字为实施验收/探针口径（探针 ≠ 预注册 ≠ 成绩）。
> **上游**：`docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md` §3 Step D1（D1.2 定刀）+
> **D1 探针结果** `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_probe/`（交集 0/17 已坐实，
> 干跑 17/17、全框 616/732 提取层救回，0 件需要对应规则）+ 本任务书。
> **基线**：HEAD `26ad119`（v4.3）；s5b-compiler-4 / pool-policy-8。

## 0. 定刀依据（D1 探针结论，一句话）

rxnmapper 资产与 17 件交集 **0/17**（15 env 无覆盖 + 2 rhea 被 QC 拒）⇒ 不接线，
转**确定性补映射**：`transform_no_change` 的成因=模板改动基团未带 map 号（半映射键不进键差表
⇒ 提取层判「无净变化」）。规则级补全这些 map 号后，D1 干跑实测：17 件 **17/17** 恢复变换提取，
全框 732 件 tnc 面 **616/732** 恢复（116 件不动 = rhea 退化空模板「无未映射缺口」，属数据面，
**不是本刀对象**）。

## 1. 改动面（单变量：只改 `transform_no_change` 触发路径）

### 1.1 新函数（`src/pathway_v43/pollutant/s5b_compiler.py`）

`complete_template_mapping(mapped_lhs, mapped_rhs) -> dict`——**逐字移植 D1 探针
`patch_v0`/`unmapped_components`/`pair_components` 的 v0 规则**（探针脚本
`reports/ppv1_s5b/t_g_fix_2026-10-19/d1_probe/d1_probe.py:201-275,391-447`；
移植时在 docstring 注明来源与版本）：

1. 双侧解析失败 ⇒ `{"status": "fail_closed", "reason": ...}`（不改串）；
2. 未映射原子（map==0）按「仅经未映射原子相连」求连通分量；分量签名 =
   （元素多重集，边界原子元素及其映射邻居 map 号集合的排序元组）；
3. 按签名跨侧配对（计数配对，签名相同先配；余下在 lhs 侧 ⇒ removed、rhs 侧 ⇒ added；
   matched **不处理**——v0 无对应规则，D1 探针实测 0 件需要）；
4. removed 分量原子 → 新 map 号写回 **lhs 侧**；added 对称写回 **rhs 侧**；
   新号从 `max(双侧现有 map 号 ∪ {0}) + 1` 起，按原子索引排序确定性递增；
   写回用 `Chem.MolToSmiles`（canonical；确定性与 RDKit 版本绑定，已登记）；
5. 返回 `{"status": "remapped"|"no_gap"|"fail_closed", "mapped_lhs", "mapped_rhs",
   "n_new_maps", "rule_version": S5B_TEMPLATE_REMAP_VERSION}`；
6. **幂等**（对已补串再调用 = 无操作原样返回）与**确定性**（同输入两次调用逐字节同）
   各写单测钉死。

### 1.2 接线（唯一触发点）

`_compile_donor_template_impl`（或 `compile_donor_template` 包装层，实现时择一，
以「调用点最少、后续 F5 不感知」为准——**推荐包装层**）：

```
try: transform = extract_mapped_transform(lhs, rhs)
except S5bCompileError as e:
    if e.reason != "transform_no_change": raise          # 其它拒因零触碰
    remap = complete_template_mapping(lhs, rhs)
    if remap.status != "remapped": raise e               # 原拒因原样
    try: transform = extract_mapped_transform(remapped)
    except S5bCompileError as e2:
        if e2.reason != "transform_no_change": raise e2  # 如实迁移
        raise e  # 仍无净变化 ⇒ 原样 tnc（116 退化件走这）
```

后续全部逻辑（中心/对齐/编辑）**用 remapped 串原样跑**，一字不改。
**F5（builder `center_anchor_probe`）不改**：tnc 件 F5=defer（照常发编译），
「defer ⇒ 由编译层如实出因」语义保持；为消歧在 F5 docstring 与 compile 层 docstring
各加一句注（defer 件可能经补映射编译成功——出因以编译层为准）。**F1-F4 接线零改动**
（本刀不改 builder 路由函数；`template_elements_fit` 对补映射不变量=元素多重集不变）。

### 1.3 版本与披露

- `S5B_COMPILER_VERSION`：`s5b-compiler-4` → **`s5b-compiler-5`**；新常量
  `S5B_TEMPLATE_REMAP_VERSION = "template-remap-1"`（升位时同步既有版本断言测试，
  沿 C2 轮「7 件版本断言同步」先例）；
- **机读披露**：compiled spec 追加 `spec["template_remap"] = {"applied": true,
  "rule_version": ..., "n_new_maps": N}`；拒因 detail 同形（若补映射后仍拒，
  detail 附 `template_remap={applied:true/false, ...}` 区分「未触发/触发未果」）；
  **非 tnc 路径输出逐字节不变**（无新增键）。

## 2. 单测（新文件 `tests/test_ppv1_s5b_template_remap.py` + 存量跟改）

1. 规则级合成：removed-only / added-only / 两边都有 / matched 不处理 / no_gap（零缺口原样）/
   解析失败 fail_closed / 新鲜号>max / 决定性与幂等（各 1 测）；
2. 编译级合成：**tnc 合成模板**（自造半映射键模板；离场基团未映射——不复用任何真实记录串）
   补映射后 `compile_donor_template` 跨过提取层（compiled 或后续层稳定拒，**不得再是
   transform_no_change**）；负控=no_gap 退化模板保持 tnc；负控=补映射后仍然失败的形状
   返回**原** tnc；
3. 回归：非 tnc 合成模板输入输出与改前逐字节同（smoke）；全量 not-slow 零翻转。

## 3. 验收（分档重放 + 对拍；新批次根）

产物入 `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_remap/`（gitignored；脚本+json+md+log）：

| # | 项 | 口径 |
|---|---|---|
| A | **17 件迁移表** | 155 材料包 17 件：改前 tnc → 改后结局（compiled / 新拒因）逐件；**≥1 件 compiled 或 ≥17 件提取层迁移**（D1 验收「不再拒」+ 如实报 compiled 数） |
| B | **全框 1,886 重放** | 新直方图 vs 基线（`{tnc 732, no_align 718, compiled 124, ...}`）；tnc 迁移去向逐类计数；116 退化件保持原样 |
| C | **负控-失败面** | 155 中 reject_correct 的 tnc 件（33 件）改后**逐件报结局**；任何 reject→compiled 翻转**逐件列名披露**（不静默、不当作收益） |
| D | **非目标零漂移** | 全框非 tnc 件（1,154 件）改前后逐行结局逐字节同；unlock/byte 探针（`r2p_unlock_face_replay.py`、`r2p_byte_invariance_probe.py` 同源复跑）非 tnc 行零漂移，受影响行逐行披露（沿 C2 轮「字节面守线+漂移面全披露」处置） |
| E | 全量测试 | `~/miniconda3/envs/depending43/bin/python -m pytest -p no:cacheprovider` not-slow 全绿（基线 2229/0/16 零翻转；新增测试计入） |
| F | P3 登记项 | 沿 C2 轮 P3-TEST-01 口径补一条专项合成负控（补映射后 **错误映射不得伪装新变化**：构造「签名巧合」反例——两侧未映射分量签名相同但化学对应不同——要求 fail-closed 或如实拒，测试钉死） |

## 4. 红线与纪律

1. **只改 `s5b_compiler.py` + 测试**（新函数+触发点+版本键/披露）；不动 builder/search/
   production/recorded_source/evaluation；不动资产与封存批次；
2. 触发面**只限 tnc**：其它拒因路径逐字节不变（对拍 D 证）；
3. **零化学判断**：只补 map 号，不改结构/不改元素/不改立体；补映射后一切照现行编译器判据；
4. 产物新批次根；`PYTHONDONTWRITEBYTECODE=1`、pytest `-p no:cacheprovider`；
   记录实际 HEAD/命令/输入 sha256；金标/题面零接触（探针用的记录串=gitignored 既有产物）；
5. 提交纪律：实施完成**先不提交**——交主窗口核对+送复审（评审-回修循环），放行后才随轮提交；
6. 复数失败/超时：同任务重试 1 次仍败即停报。

## 5. 回传三件套

1. 改动构成：`git diff --stat`（文件+行数）+ 新函数/接线/版本键/披露字段清单；
2. 验收数字：A-E 逐项（17 件迁移表、全框新直方图、负控逐件、零漂移读数、pytest 数字）；
3. 风险与披露清单：任何非预期漂移、reject→compiled 翻转、与探针干跑数字的差异（逐项机械归因）；
   交主窗口送复审。**不 push。**