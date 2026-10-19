# TASK — T-D/E E1 表示层实施（实施任务书 **v2**，2026-10-19）

> **状态**：**可派工**。v2 依据 = Codex 二轮复审终判定「**放行，可进入实施**」
> （`docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REREVIEW_2026-10-19.md`——其 §4/§5 为**最终口径**，
> 优先于设计稿 v2 的简写）；v1 的 ⚑ 待钉项已全部按复审裁定落字（见文末清单）。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针/重算 ≠ 预注册 ≠ 成绩。
> **生效口径（唯一语义权威）**：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`
> ——本任务书只做落实，不得改写其文本。
> **前置件**：① 前置 1 重算（`docs/TASK_T_DE_E1_PRE1_RECOMPUTE_2026-10-19.md`，证据
> `reports/ppv1_s5b/t_de_e1_2026-10-19/pre1_recompute/`）；② 前置 2 设计稿 v2
> （`docs/T_E_RUN_IDENTITY_DESIGN_DRAFT_2026-10-19.md`）+ 两轮复审报告
> （`docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REVIEW_2026-10-19.md`、
> `docs/T_E_RUN_IDENTITY_DESIGN_CODEX_REREVIEW_2026-10-19.md`）。
> **基线**：HEAD `26ad119`（v4.3）；编译器以**实际工作树**为准（D1.2 与 E1 并行实施 ⇒
> 若 D1.2 先合入，实际树 = s5b-compiler-5；设计复审判定的固定件为 compiler-4，
> 其约束=「E1 不得改编译判据」——E1 对拍基线一律取「E1 开工时的实际树」并记录 sha256）。
> **实施拆单**：本任务书可拆两个实施子代理并行（**E1a=T-E**：§1+§3.1+§4.1/4.2；**E1b=T-D-A/B**：
> §2+§3.2+§4.3）——文件面不重叠（E1a：`recorded_source.py`/`s5b_builder.py`/`s5b_worker.py`/
> `runflow.py`；E1b：`evaluation.py`/`s5b_scoring.py`/`profile.py` 只读），测试各自新文件。

---

## 0. 一句话

按 FROZEN_V3 实施两条**同一轮、分层位**改动：**T-E 记录侧形式归一**（检索/编译侧主刀；
含 **build_identity 首消费绑定**新件）+ **T-D-A/B 判分侧披露轴**（V3 显式启用；三判据全走
**档 A 披露、不授 strict、不进 hit@1**）。判分侧互变归一禁改；底物侧不施加；单变量、
新批次根、零金标。

## 1. T-E 实施（E1a；检索/编译侧主刀）

### 1.1 归一算子（单一实现源；复审 §4.1/§5 最终口径）

- 新函数（落 `recorded_source.py`）：`normalize_record_side_smiles(smi) -> dict`：
  - **算子=默认 `rdMolStandardize.Uncharger()`**；**登记实测默认三参数
    `canonicalOrder=True, force=False, protonationOnly=False`**（复审 Q9：可读、必须登记；
    **`neutralize=True` 关键字被拒——不得出现在代码/文档**）；**逐组分**施加；
  - **短路=先实际运行算子**，再按**同一原子对应**核 q/H、重原子图、键、map、同位素、立体
    均未变，才认「成功无操作」并直通原串（**禁止**用「电荷向量不变便足矣」的强断言）；
  - **三值语义（按提交事务状态，非净电荷/非字符串比较）**：
    `applied`=事务成功提交的原子化学状态改变（**允许保留永久电荷**——内盐反例已实证）；
    `not_applicable`=成功无操作（原串直通）；`failed`=未提交并**完整回滚**（原串 + 机读原因）；
  - **事务单位=一次候选消费视体**（donor/lhs、rhs/products、copies、full_products、派生供给
    及装配字段全量原子化）：任一分量失败 ⇒ **全部回原始**；保 `None`/空列表/顺序/重数的既有
    区别；**all-or-nothing**；
  - **保留原子映射号**（analog）：⚠ 前置 1 实证来源快照的 verbatim 路径**有丢号缺陷**
    （`strip_map` 缓存污染；19 行受影响）——**不得照抄**；口径=`GetMolFrags(asMols=True)`
    逐组分在**独立新 Mol** 上 `uncharge` → 保留 map/立体的 canonical SMILES → 按**输入组分序**
    点号重接；单测钉死「归一前后 map 号集合逐行相等」；
  - 幂等：**成功域双遍字节固定点**（第二遍无新增改动）；**failed 域确定性重现 failed 且原串
    不变**（两域状态不同，不得改标签换通过）；
  - 嵌套消费（复审 §4.3）：**首次 source→view 事务持有原始 status/trace**；corpus 视体二次
    进入公共 compile 时局部 `not_applicable` **不得**覆盖首次 `applied`、不得移除证明域；
    完整视体 failed 时，子集 compile **不得**重新归一授益（实施矩阵覆盖两形态）。
- 常量与指纹（同模块）：
  `RECORD_SIDE_FORMNORM_VERSION = "record-side-formnorm-1"`；
  `RECORD_SIDE_FORMNORM_PARAM_SHA256`=sha256(canonical_json({operator；**实测三默认参数**；
  application=逐组分+序列化+组分序；noop_rule；事务策略；RDKit 版本串}))；不可自省面单列
  登记；批诊断同时输出版本+指纹（机读绑定）。

### 1.2 注入点（单一来源纪律；复审 §4.1/P1-2 最终口径）

| 通道 | 注入点 | 消费范围（全部同域） |
|---|---|---|
| recorded（EAWAG） | `compile_recorded_reaction` **函数入口**：全部记录侧入参（`donor_smiles`、`products`、`record_products`、`declared_copies` 及派生成分）过同一算子 | 映射推断（:2095）/`mapped_lhs,rhs` 构建/产物 strict 门/union gate |
| corpus（RHEA/env） | **候选识别后、分类前**建统一消费视体（`_classify_cosubstrate_candidate` :1483 之前），贯穿：分类（:1483）→ 编译（:1519/:1708）→ 装配（co_comps/flat_products/copy_products，:1630）→ **NC-10 两处声明（:1957/:2021）**；公共 compile 直呼共用同一算子（无旁路） | 同上 + 分类与声明 |
| analog（模板） | `_compile_analog_refs` 的 `for ref in refs` 起点（`s5b_builder.py:1273-1275`）生成「归一视体」（`lhs/rhs`） | 该循环**全部**记录侧消费者（F1/F2/F3/F5/编译/`record_equation`/spectators/light_gap）读视体；**raw ref 不得再传编译**；召回与阈值逻辑不变 |

- **tier/原始召回/底物串保持原始**（身份面零触碰，D06/C3 硬约束；S5A-01 门不变）；
- **raw 例外只限**：`record_equation`（保原始条目、侧和重数；消费视体另用）、corpus
  `matched_component`（保 raw；两装配分支另披露消费态；实际 copies/co_substrates/
  record_products 同域）；
- 通配预筛/T-4 碳类诊断：登记原始域、不变性（不改既有规则）。

### 1.3 披露（复审 §4.2 最小 schema——**优先于设计稿简写**）

- 诊断行（`pool_diagnostics.candidates`，**全形态**：compiled / compile_rejected /
  merged_into / pool_truncated 均保留归一事件）：
  - `record_side_form_norm` = **三值标量**；追加 `record_side_form_norm_trace`：
    - `source_ref`：`channel/asset_sha256/record_key/matched_side_or_component`
      （**不能只靠 record_key**——同记录可多匹配侧）；`source_fields` 标明 raw 来源例外；
    - `changes[]`：`side/entry_index/fragment_index/source_atom_index/original_map` +
      `charge_before/charge_after`、`hydrogen_before/hydrogen_after`（**源坐标**）；
    - `atom_correspondence[]`：同坐标绑定 `normalized_atom_index/generated_map`；
      changes 回指它；缺对应给原因（**不拿重排后 idx 猜测**）；
    - **H 口径**：总数=`GetTotalNumHs(includeNeighbors=True)`，并**分列**显式属性 H、隐式 H、
      邻接 H 原子及其同位素来源（保原子身份，**不把 D 当普通 H**），均存前后值；
    - `matching_scope ∈ {center_l1_l2, legacy_whole}`（后者仅作来源复现，**不得合并冒充同一
      消费范围**）；`intersection`=**实际消费 query/匹配原子** ∩ 同坐标 lhs 改动原子（rhs 另列）；
    - `risk_status ∈ {present, absent, unknown, not_applicable}` + 原因：可核交集非空=present、
      可核空集=absent、无法追溯/无匹配/截断**如实 unknown/not_applicable（禁伪填 absent）**；
      **风险行与 unknown 行保留人工复核义务**。
- applied 成功 spec 的 `compile` **仅条件追加五个标量键**（不采用嵌套对象）：
  `record_side_form_norm="applied"`、`record_side_form_norm_version`、
  `record_side_form_norm_param_sha256`、`record_side_form_norm_trace_ref`（=同候选 trace 规范
  内容的确定性 sha256，**必须能回到相应诊断行**）、`verification_domain="normalized_record_side"`；
  **未 applied spec 五键缺席、原字节不变**；
- `verified_product_set=True` 只证明**消费态归一记录域**产品集通过既有核验，**不授**原始资产
  完整离子身份；
- 批级：`record_side_form_norm_version` + `_param_sha256`（池诊断顶层）；
- **覆盖限制披露**：底物侧未处理=覆盖限制（逐批披露；不得宣称仅归一记录侧即免误判）。

### 1.4 版本与批次（复审 Q8 最终口径）

- `S5B_POOL_POLICY_VERSION`：`s5b-pool-policy-8` → **`-9`**；
- `RECORDED_SOURCE_VERSION`：`s5b-recorded-source-3` → **`-4`**（公共 compile 默认输入的
  核验域与 spec 改变；不得静默）;
- **`S5B_ANALOG_ROUTE_VERSION` 不升**但批诊断**机读绑定** formnorm 版本/指纹，
  并注明「route 表达 F1–F4 分支公式、算法未改，但**路由结果可变**」；
- **不动**：`S5B_COMPILER_VERSION`（E1 不改编译判据）、`PPV1_EVALUATION_VERSION`、
  `EDIT_PROTOCOL_VERSION`/`ATOMTOOL_VERSION`、criteria V1/V2 路径；
- 新 batch_tag + 新批次根；旧批零回写。

### 1.5 build_identity 首消费绑定（E1a 新件；复审 §4.1 直接指定）

- **批根唯一权威旁块 `build_identity.json`**（manifest 可放引用/摘要，不再另存可独立变更的
  同内容权威块）；字段集=设计稿 v2 §3.6:386-397（build 代码聚合 code_identity + pool/source/
  formnorm 版本与指纹 + route/compiler/RDKit + 源资产身份 + **逐 qid/run_id 输入原始字节 sha**）；
- `build_identity_fingerprint = sha256(canonical_json(payload))`；**只排除**顶层自身哈希键与
  展示项 `created_at`/`display_note`（排除清单随 schema 登记）；**代码/资产/版本/参数/RDKit/
  逐输入 sha 等实际身份事实不得排除**；
- **首消费核对**：worker/公共批在**创建 run 之前、driver 开始与任何付费调用之前**核对；
  通过后在**run 合法创建后**把 `{build_identity_fingerprint, run_input_sha256, qid, run_id}`
  **唯一、不可覆盖地持久化**到 run 内来源工件或 ledger（**case 只作摘要，不得为唯一权威**）；
  来源落盘失败 ⇒ **不得继续调用**；
- **恢复**：先读并核既存原来源，再与当前已验旁块/输入逐项同值；缺/坏/不符 ⇒ **拒并保全原
  记录**（不覆盖、不用当前新摘要补造旧出处）；
- **结构化拒因**（沿现有枚举风格定名，但三类可判定事实必须保留）：`build_identity_invalid`
  （detail 区分 missing/corrupt/version/content mismatch）、`run_input_bytes_mismatch`、
  `run_build_origin_mismatch`（detail 区分缺/坏/错）；**拒绝时失败题留分母、零发送**；
  首启核对失败**不建 run**；恢复失败**不改既存 run**；
- 范围：**不改** `run_identity.json`、**不改** native-export schema、不强改通用无批
  scripted start（可放批侧）。

## 2. T-D-A/B 实施（E1b；判分侧披露轴，档 A）

### 2.1 版本承载

- `evaluation.py`：`PPV1_CRITERIA_V3 = "ppv1-criteria-v3"` + `PPV1_CRITERIA_VERSIONS` 白名单
  （:842-844）+ `resolve_criteria_version`（:956）；非法值结构化拒；
- **缺省 v1 字节不变；显式 v2 行为不变；v3 显式启用**；`s5b_scoring.py` 批级透传（沿
  `criteria_v2` 块先例 :203/:541）；批诊断登记 V3 块（**不动** PPV1_EVALUATION_VERSION）。

### 2.2 A 轴（互变异构；双臂分列；档 A）

- 默认臂：`TautomerEnumerator(CleanupParameters(maxTransforms=1000, maxTautomers=1000,
  removeSp3Stereo=True, removeBondStereo=True))` → `Canonicalize()` → canonical isomeric
  SMILES；候选主臂=同参、`removeSp3Stereo=False`（`removeBondStereo` 保持默认 true=未核范围）；
  **双臂布尔独立保存、分开报数**；臂字段 `tautomer_arm ∈ {default, stereo_preserving}` +
  分臂 `tautomer_param_sha256`；
- **档 A：归一相等只产披露（`cn_only_normalized`），不授 strict、不进 hit@1**；
  `tautomer_promoted_nodes` **本轮恒无**；
- A-1 适用面：仅 `structure_identity_scope=="strict_structure"` 参考节点的 cn_only 配对；
  其余沿用 V1 封顶；**S5A-01 门不得越过**。

### 2.3 B 轴（质子化；单臂默认 + 并列敏感性）

- 默认单启用 **Uncharger 臂**（逐组分→点号重接→canonical isomeric SMILES **保留立体**相等；
  **不用** cn_identity 立体盲口径）；**ChargeParent 臂仅并列敏感性披露**（同批双跑分开报）；
- 归一后仍不等且净电荷不同 ⇒ 不授；禁「净电荷对齐」扩面；
- **B-6 碳酸体系闭集**（CO₂/HCO₃⁻/CO₃²⁻ 及仅质子化写法变异）：两侧均命中 ⇒ 逐对象排除 +
  机读原因 `carbonate_system_exclusion`；闭集+识别算子参数入批级指纹；增删=版本升号；
- **B-5 双轴布尔+单归属**：每配对保存 A/B 布尔+臂+参数来源；计数按 **A→B** 单归属，双满足
  **披露双满足计数**。

### 2.4 公共

- fail-closed：不可解析/异常 ⇒ 不授归一相等 + 逐对机读原因，**无第三态**（单归属断言）；
- 参数指纹（§3 条 3）：各臂实际生效参数（含未显式设置默认值 `tautomerRemoveIsotopicHs`/
  `tautomerReassignStereo`/`maxRestarts` **实测值**——前置 1 已实测登记）+ 双臂差异 diff +
  `transforms` 文件哈希（本 RDKit 构建无 `tautomerTransforms.in`，以原子库 sha256 替代登记
  并披露）+ RDKit 版本串 → sha256；
- 芳香 0 题固定句；单批不宣称稳定。

## 3. 单测与正负控（实施验收）

### 3.1 E1a（T-E）

| 类别 | 内容 |
|---|---|
| 算子 | 短路（实跑+同原子状态核）/ 幂等双遍（成功域固定点+failed 域重现）/ 失败直通 / all-or-nothing / 组分序 / **map 号保留逐行断言** / 实测三默认参数存在性断言 |
| 注入点 | recorded/corpus（含**分类前视体**贯穿与 NC-10 两处声明 1 测）/ analog（同 ref 全消费同域 1 测） |
| 披露 | 三值标量 / trace schema 逐字段（source_ref/changes/atom_correspondence/H 分列含 D 身份）/ matching_scope / intersection（实际 query 口径）/ risk_status 四值含 unknown 禁伪填 / applied 五键条件性 / 未 applied 零字节 |
| build_identity | 指纹口径（排除清单仅 3 项）；首消费核对四拒例（missing/corrupt/version/content mismatch）；输入字节不匹配拒；run 来源持久化（唯一不可覆盖）；恢复同核（缺/坏/不符拒+保全原记录）；来源落盘失败不调用 |
| 嵌套 | 首次 applied→二遍 no-op 不覆盖；父事务 failed→子集 compile 不得重新授权 |
| 正控 | P3/P4 复现（前置 1 实测账：P3 64/27、L1-pure 58/58、P4 现行口径 10/7 零位移）；⚠ **发货口径编译基线以实施后批内实测为准**（前置 1 t2=9/6 系来源快照丢号缺陷下读数；正确实现后重新实测：预期 recorded/corpus 侧 9 行复现 + analog 侧不再因归一丢号）+ 本样本 3 件质子化/形式差进修复兑现表 |
| 负控 | N8/N9 在实现上复现；**N10 按复审 §5**：固定同批不可变事件/产物/参考/导出/criteria，钉哈希，逐事件核 strict 布尔/身份参与物/原因，v1 与显式 v2 分开；**新池候选/事件变化另表归因**（不得以「池策略级」豁免 N10） |

### 3.2 E1b（T-D）

| 类别 | 内容 |
|---|---|
| 正控 | P1（**前置 1 实测：默认臂 14/14 对、立体保留臂 13/14 对**，唯一仅默认臂相等对 `RXNG_50891a38435` 逐对披露）；P2（**两单臂各 6/6**） |
| 负控 | N1（ISOMER-TRUE 23 题两臂全不相等——**前置 1 实测 PASS**）；N2（0）；N3/N7（v3 启用时 V2 tier 计数**同 payload** 与 v2 逐位一致——不要求不同新事件 v2 总计数恒等）；N4（S5A-01 封顶仍生效）；N5/N6；**B-5 双满足实测 0 对** |
| 指纹 | 分臂 param_sha256 断言（四臂指纹 + 实测默认值 + transforms 替代登记） |
| 披露 | 双臂字段分列 / 原状态 / 批级分列计数 / `tautomer_promoted_nodes` 恒空断言 / carbonate 机读排除原因 |

### 3.3 全量

not-slow 全绿零翻转；**基线=开工时实际树**（若 D1.2 已合入则为其后基线；记录 sha256 与
测试总数，翻转=0）。

## 4. 对拍（实施轮必交）

1. **T-E 差分双 build 字节探针**（复审 §4.3：**A 臂路线=直接旧树/新树对比**（推荐路线已选，
   须记录两棵树的源码与输入身份；否则不得称「旧基线」））：未受影响题 run_inputs 逐字节 +
   诊断**旧字段投影**逐键相等；受影响题每一差异挂实际 `applied` 事件归因；**全 298 题穷举**；
   **旧 diag 字段投影与新 audit 字段分开验**（不得当版本键整块排除、不得扩大排除键掩盖漂移）；
2. **三层口径分开报**（C-3）：①对齐行 ②compiled 行 ③strict 命中（**本轮 unknown 未验**）；
3. NC-10/池声明同域核（P1-2 面）；
4. **T-D**：V3 与 v1/v2 同批只读重算并列披露（rescore 先例）；旧批零回写；
5. N10 对照按 §3.1 口径；与前置 1 重算账逐行交集/差集归因。

## 5. 红线

1. **判分侧互变归一禁改**：不升 strict、档 B 未解锁（无静默路径）、不进 hit@1；
2. **底物侧不施加**；F4/路由事实不被归一改写；**E1 不改编译判据**（compiler 引擎零改动）；
3. C-4 邻接项不认领（NAD(P)⁺ 10 行 / 救不动 18 行 / 既有编译拒因 54 行）；
4. 单变量分账：E1a/E1b/D1.2 各自独立归因、可拆；
5. 金标/题面零外带；含金标产物仅 gitignored；新批次根；封存批零改写；
6. 提交纪律：实施完成→主窗口核对→送复审（Codex 正常通道；额度断流=代审）→回修→放行走一回
   一提交；**不 push**；
7. 子代理纪律：报告级产物零结构串；`PYTHONDONTWRITEBYTECODE=1`；`-p no:cacheprovider`。

## 6. 产物与回传

- 批次根：`reports/ppv1_s5b/t_de_e1_2026-10-19/e1_te_impl/`（E1a）与 `e1_td_impl/`（E1b）；
- 交付书：`docs/T_DE_E1_IMPL_DELIVERY_2026-10-19.md`（合并两单）；
- 回传三件套：改动构成（`git diff --stat`+清单）/ 验收数字逐项 / 风险与披露清单；
- 主 TODO 行 4/5/7 与移交书 §3 由主窗口刷新。

---

## ⚑ 前置 1 关键发现（回填，实施与评审必读）

1. **P4 零位移**：C2（compiler-4）未移动 64 恢复行编译结局；来源 10/7 与现行逐行 reason 全等。
2. **发货口径 vs uu 参考差 1 行**：仅记录侧归一（t2）=9/6；双侧（t3）=10/7；差额行
   `RXNG_36ff61dc588|bt0063#r0073`——按 FROZEN_V3 底物侧不施加，发货=9/6、差额逐行披露；
   ⚠ 且 t2 为**来源快照丢号缺陷下**读数，实施后以批内实测为准（见 §3.1 正控行）。
3. **analog 映射号保留=实现硬要求**（§1.1 已钉）。
4. **C1 文本差异（登记供处置，不改冻结文本）**：重算下**立体保留臂仍 13/14 相等**
   （唯一仅默认臂相等对 `RXNG_50891a38435`）——FROZEN_V3 §4.4 C1 所引「参考侧立体被消除是
   唯一机制」**未获重算支持**；逐对原子级溯源仍为待补化学门槛。不改变档 A 语义；随交付书报
   CC/评审。
5. **指纹口径**：`tautomerTransforms.in` 本构建不存在；以原子库 sha256 替代登记并披露。
6. **t1 基线注**：原样串下 analog 9 行可编译 vs 来源账 analog 0 compiled（来源走丢号路径）
   ——两口径入册，实施后对账以 §3.1 口径为准。

## ⚑ 待钉清单（v2 终态：全部已钉）

| # | 项 | 落点 |
|---|---|---|
| 1 | 短路口径 / applied 判据 | §1.1（复审 §4.1 改写版） |
| 2 | 版本三件 | §1.4（pool-9/source-4/route 绑定） |
| 3 | N10 口径 | §3.1 负控行（复审 §5） |
| 4 | Q3/Q4/Q5/Q6/Q7 | §1.2 raw 例外 + §1.1 事务（复审 §4.3） |
| 5 | Q9 指纹 / Q10 字段 | §1.1 指纹 + §1.3 五键（复审 §4.2） |
| 6 | 前置 1 数字 | §3.1/§3.2 正负控行 |
| 7 | 口径差汇总 | 前置发现 2/6 |
| 8 | build_identity 生命周期与拒因 | §1.5（复审 §4.1 直接指定） |
| 9 | A 臂路线 | §4.1（直接旧树/新树，已选） |