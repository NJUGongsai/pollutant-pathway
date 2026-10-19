# TASK — T-G 编译漏斗分通道修复（设计任务书，2026-10-19）

> **状态**：设计任务书（draft_v1，供新窗口零上下文接手；未冻结、未派工）。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**。本文件全部数字挂该标签，
> **不向 dev（B1 环境路径）外推**；探针/侦察数字一律「**探针 ≠ 预注册 ≠ 成绩**」。
> **上游**：老师任务书 `docs/TEACHER_TASK_GONGSAI_LINE_EXECUTION_2026-10-15(1).md`
> Phase 2 #7（T-G「编译漏斗分通道修复：analog 的 no_alignment 与 recorded 的映射枚举截断
> 分开治，各带正负控；立项规模以 Phase 0 漏斗的误拒率实测为准——低于 10% 降维护」）；
> #8（T-H：T-D/E/F/G 全齐后**一批跑完**，预注册 hit@1 35–40%，<32% 回查）。
> **立项依据（CC 已拍板开干）**：P0-1 误拒率 v3.2 读数 A 通道 56/131 = **42.7%**
> [34.6%, 51.3%] 稳过 10% 线（判读可用性门处置按 CC 2026-10-19 拍板②执行中，
> 两分歧件代审终审回件后门复算；出表序列见 `docs/HANDOFF_P01_REJUDGE_2026-10-18.md` §3）。
> **写单窗口**：2026-10-18/19 ZCode 侦察子代理（GLM）；**本单为只读侦察+起草产物，
> 未改任何既有文件**，未跑批、未调外部模型、零费用。

---

## 0. 现状（新窗口零上下文可接）

### 0.0 一分钟机制速览（先读这段，后面全用得上）

- **管线**：三通道检索（corpus / recorded / analog）→ **池编译站**（对齐→编辑编译）→
  去重/截断/成池（policy 版本承载）→ 模型 decide（唯一调用）→ 执行 → 准入/提交 → 判分
  （v1 缺省 + v2 豁免双口径；零 LLM）。
- **analog 通道**：模板库 `assets/analog/corpus_templates_v{1,2}.jsonl`（RHEA+enviPath 记录，
  含 mapped_lhs/mapped_rhs/center_atoms）；检索 → `resolver.templates_similar_to(substrate)`；
  候选 = 模板映射反应。编译 = `s5b_compiler.compile_donor_template`：
  `extract_mapped_transform`（取变换；双侧 map 号联结无净变化 → 拒 **transform_no_change**）
  → `enumerate_template_alignments`（**全供体匹配**：整条 mapped_lhs 子结构匹配底物，
  `useChirality=False`、`maxMatches=64`；零匹配 → **no_alignment**）→ 编辑编译。
- **前置门**：`s5b_builder` 在编译前先跑 `template_elements_fit(mapped_lhs, substrate)`
  （元素多重集 ⊄ 底物 ⇒ 必 no_alignment，只省预算不改口径）；**C 线 policy-7 救援**：
  前置门拒时 `analog_cosub_supply` 把模板袋共底物按伴生参与物补给底物后重过门再编译。
- **词表**：`no_alignment`=找不到对齐；`transform_no_change`=模板 map 联结后无净变化
  （改动原子没带 map 号/半映射键时最常见）；`no_supply`=无共底物袋可补给；
  `wildcard_blocked`=裸通配袋（`*`）拦截；L1/L2/L3=判读 v3.2 中心三层（L1 变键边、
  L2 变键原子其他重边、L3 其余=旁观豁免）；旁观差异=L3 差异。

### 0.1 四修复面现状表（设计 / 实施 / 复审 / 入口）

| 修复面 | 设计状态 | 实施状态 | 复审与尾巴 | 入口代码路径（行号为工作树实测） |
|---|---|---|---|---|
| **C 线共底物供给** | v1 冻结设计 `C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`（语义 a 伴生供给）；重设计预注册 `C_COSUB_SUPPLY_REDESIGN_PREREG_2026-10-15.md`（L1 资格面**已实测证伪关闭**、L3 声明面下放**证伪关闭**、**L2 编译容量在案不排期**、L4 键合缓行） | **已落地并进批**：commit `873c323`（policy-7）+ `b6ba35f`（P2-1 落字）；chain13/14 批含之 | 两轮 Codex：首轮有条件通过；**REAUDIT（`C_COSUB_SUPPLY_IMPL_CODEX_REVIEW_2026-10-14_REAUDIT.md`）判定「退回」——2×P1+P2+P3 至今未回修**（工作树核实：`s5b_builder.py:598-616` 主份扣除仍按 CN 首位删、非选定 `main_idx`；`search.py:3331-3370` B3 恢复仍先 `submit_event` 无 provenance 发射核验）；设计面 mimo 场景 1 已过 | `src/pathway_v43/pollutant/s5b_builder.py`：`analog_cosub_supply`(559-624)、`_cosub_supply_spectators`(628-709)、`analog_record_equation`(712-728)、`_attach_analog_cosub_supply_fields`(731-862)、`_compile_analog_refs` 救援接线(1061-1171)；`production.py`：`_verify_execution_input`(194-244)、`expand_hypothesis_production` 发射(1232-1238)；`search.py` B3 恢复(3331-3370)；测试 `tests/test_ppv1_s5b_cosub_supply.py` |
| **D 线 rxnmapper 扩检索** | 设计书 `D_RXNMAPPER_SCALEUP_DESIGN_PREREG_2026-10-14.md`（draft_v2，**未冻结**；含「86 题缺口=收录范围外」证伪改写与三件套） | **零实现**：`src/`、`tests/`、`scripts/`、`configs/` 无 rxnmapper 引用；模板资产 **32,832 条**在 gitignored 探针目录 `reports/ppv1_s5b/d_probe_rxnmapper_2026-10-14/rxnmapper_templates_v1.jsonl`（61.8MB，字段对齐 corpus_templates_v1） | D 探针：120 H 桶覆盖 **0/120**（三重闸门串联：86/120 缺书 + 在库 33/34 死共底物元素门 + 1 电荷）；D 对齐侦察：原「RHEA 版本/表示差异」前提**证伪**（收录范围外 100%）；LOCK12 裁定建议「转向 D 线」但 D 未冻结 | 无 src 入口；接线点 = `s5b_builder.py:1198 resolver.templates_similar_to`（模板源）；现有模板资产 `assets/analog/corpus_templates_v{1,2}.jsonl` |
| **表示层（T-D/E，FROZEN_V3）** | **已冻结**：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`（CC 2026-10-19「冻结开关开干」；代审即终审 D01–D07 + R01–R07 已落实）；关键参数：**双臂**（默认臂=互变中心立体容忍、手性负控 FAIL 实测 2/2、**敏感性披露臂不具 strict 准入**；候选主臂=sp3 立体保留、档 B 唯一候选但**本轮未解锁**）、**档 A 披露**（三轴本轮一律 `cn_only_normalized` 披露、不授 strict、不进 hit@1）、**23 题**（ISOMER-TRUE=21 纯立体差+2 其他真差，题组 14 互变/6 质子化/7 形式归一、并集 26 毛上限） | **零实现**（V3 常量未加：`evaluation.py` 现仅 `PPV1_CRITERIA_V1/V2` 白名单） | 评审链已收口（mimo 场景 1 + Codex 代审终审）；**实施前置缺口 5/6 待完成**（来源批次逐行只读重算持久证据；记录侧归一与 run 身份/缓存 key 闭合设计）；T-E 的逐行原始账在 /tmp 属易失件 | 判分侧：`src/pathway_v43/pollutant/evaluation.py:842-844`（V1/V2 常量+白名单）、`:956`（resolve）、`:1369`（`match_reference_nodes`）、`:1414-1416`（S5A-01 许可门）；`src/pathway_v43/domain/identity.py:46`（`cn_identity`）；`s5b_scoring.py:203/541`（批级透传）。检索/编译侧（T-E）：`recorded_source.py:2060-2130`（`compile_recorded_reaction` 构建 mapped_lhs/rhs）、`s5b_compiler.py:487-505`（对齐枚举） |
| **stereo / 协议扩展（末位）** | 散见于立项候选（stereo 表示审计在 P4 登记；本批 0 立项） | 零 | — | `s5b_compiler.py` `stereo_edit_unsupported` 分支；`ATOMTOOL_VERSION`/`EDIT_PROTOCOL_VERSION` 承载面 |

### 0.2 P0-1 立项输入（读数、抽样框、判读状态）

- **A 通道（analog | no_alignment）**：原始 2,818 行 → 按 (record_key, 底物-产物对) 去重
  **1,886** → 分层比例抽样 **155**（seed=20261016）→ v3.2 子代理判读
  **56 过 / 75 拒 / 24 存疑**，分母 131 ⇒ **err_rate = 42.7% [34.6%, 51.3%]**。
- **B 通道（corpus | mapping_enumeration_truncated）**：224 → 去重 97 全查（census）：
  judger 层 2/97 = 2.1%；终审翻转层 6/97 = 6.2%（上界 12.8% 触线披露）⇒ **未过线，降维护**
  （但 recorded/corpus 小项面 218 件按同框架可另立测量面，见 P0-1 设计稿 §〇）。
- **判读规则**：v3.2 = `docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md`（中心三层 L1/L2/L3、
  来源闭合、当量、手性、材料保真）；判读产物
  `reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/judgement_glmsub_v3_A_batch{1..5}.json`
  （155 行，judged_by=`ZCode-subagent(GLM)`）；二读 `judgement_second_read3_codex.json`；
  终审 `judgement_arbitration_codex.json`（代审即终审）。
- **注意**：A 通道判读的「过」= 判读口径下**化学上成立且中心落位**（L3 旁观豁免），
  **≠** 现行编译规则的机械可编译（见 §0.4 侦察发现——两者存在系统性缺口，T-G 正是修这个缺口）。

### 0.3 漏斗底数与 A 通道 2,818 行的构成

来源：`reports/ppv1_s5b/p0_funnel_2026-10-15/`（chain13 GLM 臂，policy-7）+
chain12 no_alignment 分层归因（`S5B_COMPILE_FUNNEL_DECISION_MEMO_2026-10-13.md`，唯一可参考的逐类拆账）。

| 层 | 行数（chain12 3,113 口径） | 占比 | 读法 | 对策指向 |
|---|---:|---:|---|---|
| ELEM-REJECT（元素不可入） | 2,497 | 80.2% | 聚合层判定「该拒」——**但 P0-1 实测该层混入 42.7% 误拒**（P0-1 推翻聚合读法） | 救只能扩检索/修对齐 |
| **COSUB-GATE（模板辅因子袋被元素门拦）** | **454**（167 题） | 14.6% | 最大可修单项；语义 a 实心解锁 **45 行/35 题**（扣 3 行 wildcard 伪影）；其中 11/11 纯 H₂O/H⁺/Pi/PPi 袋=教师豁免面 v1 直接受益，34/28 机制类=诚实 partial | **C 线靶面（已落地）**；残余转锁 2 |
| L1-pure + L1-candidate（底物=记录主反应物同身份仍对齐失败） | 58 + 24 | 2.6% | 抽查 6/6=酸式底物 vs 盐式记录 | **表示层 T-E（记录侧形式归一）** |
| L2-mid/low（松散类比） | 80 | 2.6% | 该拒 | — |

- chain13 全链漏斗：A=analog|no_alignment **2,818 件/249 题**（本单修复靶）；S2 池编译站全通道
  拒 5,266 件/292 题；S8 判分站 uncovered 132（119 已交卷不匹配）/partial 47/strict 119。
- **全 298 题 analog 候选宇宙（L1 重放 harness 实测，chain13 复现 0 偏差）**：候选 3,797 行、
  前置门拒 2,935；供给状态分布 `{no_supply: 2575, supply: 1136, wildcard_blocked: 86}`
  （`reports/ppv1_s5b/l1_replay_2026-10-15/`）。
- **锁 2 工单底数**（`docs/LOCK12_REPLAY_VERDICT_2026-10-15.md`）：重放 1,192 件存活 41
  （全部=现行 C 基线）；主死因 **`template_elements_no_fit` 704 件（59%）**；sim13 钥匙面
  81 行全拒=元素适配 62+对齐 17。

### 0.4 56 件 pass 侦察归类（本次侦察探针；离线零模型零 LLM）

> 方法（复现口径见附录 B）：把 `material_packs_A.json` 的 155 件逐件喂
> `template_elements_fit` + `analog_cosub_supply` + `compile_donor_template`（中心缺省=
> 全部 lhs map），复刻 policy-7 救援链的机械结局，并与 56 件 pass 判定交叉。
> **性质=侦察探针**（单模板/件、未带 ref.center_atoms——不影响对齐判定），正式实施前须
> 用正式重放脚本（沿 `unlock_face_replay.py` 先例）复算入证据目录。

| 子面（机械死点实测） | 件数 | 说明 | 预期修复面 |
|---|---:|---|---|
| **模板映射不完整（transform_no_change）** | **17** | 编译在「变换提取」层即拒：改动原子未带 map 号/半映射键（典型：EAWAG 记录 RHS 新增 O 未映射；CoA 硫酯模板酰基链未映射）。**15 件 EAWAG/enviPath + 2 件 RHEA** | **D 线工具族（重映射/映射完整性）**——注意 rxnmapper 库只覆盖「未映射 RHEA 行」，与 EAWAG 15 件无交集，须探针定交集后再定刀 |
| **中心锚定/全匹配口径缺口** | **≈27** | 中心（L1/L2）落位，但「全供体匹配」或元素多重集被 L3 旁观差异挡死（典型：模板对位 OH vs 底物对位 NO₂；2-位 Cl vs NH₂；CoA 棕榈酰 vs 环二烯）。其中 **7 件袋已供、元素门全过、仍死在全匹配** | **锁 2 编译容量（C 重设计 L2 工单）**——预注册级重工程，含对齐能力（与判读 v3.2 中心三层同构）与元素适配 |
| **元素账缺口（主合袋短）** | **6** | 袋供了但模板整侧元素多重集仍短（主组分元素账/多份/质子账） | 同上（元素适配第一刀） |
| **wildcard 面** | **6** | `[*:n]` 占位/裸 `*` 袋——冻结设计本轮**不供给**、定义另行拍板 | CC 定义轮（登记不排期） |
| （交叉单列）**质子化/形式差** | 3 | 质子化态差异挡对齐（ATP 类、羧酸 [O-]↔COOH 类） | **表示层 T-E** |

**两个关键侦察发现**（任务书设计的直接依据，须在正式实施前复算确认）：

1. **56 件中，绕过前置门直编仍是 0 件编译通过**——单修前置门/单上线袋供给解决不了
   A 通道误拒；机械缺口的真身是「全匹配/全模板元素账」的口径（≈33 件）与模板映射不完整（17 件）。
2. **transform_no_change 面是全场性现象**：155 件中 66 件（42.6%）直编死于 transform_no_change
   （56 pass 中 17、75 reject 中 35、24 uncertain 中 14）——即「模板改动原子未映射」不是误拒特有，
   而是模板资产质量面；修复该面**只改变拒因、不自动产生净收益**，负控同在（不会把该拒件变通过，
   因为其化学本来不成立或仍死在别层）。

### 0.5 修复面 × 子面映射（谁能吃掉什么，本样本口径）

| 修复面 | 本样本可吃面 | 量级（56 件口径） | 备注 |
|---|---|---:|---|
| C 线（袋供给增强+**锁 2 元素适配/对齐容量**） | 中心锚定 ≈27 + 元素账 6（重叠计入） | **≈30+** | 最大且最重；「袋已供仍死 7 件」坐实残余不在袋语义 |
| D 线（映射完整性/扩检索） | 模板映射不完整 17 | 17 | 先做交集探针；EAWAG 15 件不在 rxnmapper RHEA 库覆盖面 |
| 表示层 T-E（记录侧形式/质子化归一） | 质子化/形式差 3（+全 298 面 82 行/31 题上限） | 3 | 判分侧 T-D-A/B 轴**不修编译拒绝面**（只修判分测量），勿混预算 |
| wildcard 定义 | 6 | 6 | 须 CC/评审定义，默认维持拦截 |
| stereo/协议 | ≈0–1 | 0–1 | 末位 |

---

## 1. 目标与验收

### 1.1 目标

把 **A 通道（analog | no_alignment）误拒率从 42.7% 打下来**，路径=按 §0.5 表逐面收口；
修复动作只许落在**生成/检索/编译侧**（判分侧互变归一禁改，见 §2）。

### 1.2 验收口径（T-G 不发付费批；付费批归 T-H）

| 层 | 口径 | 方法（零模型 / 零 LLM 程序侧） |
|---|---|---|
| 步级 | 每步自包含单测 + 既有全量 not-slow 零翻转 | `~/miniconda3/envs/depending43/bin/python -m pytest -p no:cacheprovider`；定向子集 + 全量两档 |
| **修复兑现（主验收）** | **重放对拍**：对 P0-1 抽样框（去重 1,886；至少 155 样本 + 56 件 pass 全覆盖）跑修复前后**确定性重放**（正式脚本沿 `unlock_face_replay.py` 先例入新批次根），报告逐件机械结局对照表（拒因迁移 + flipped 清单），drift 必须可解释 | 修复前基线=本单 §0.4 侦察探针（复算校准）；修复后=同一 harness 原样重跑 |
| 残差面重测（量化跟踪） | 修复后残差 A 面**新抽样框重测 err_rate**：新漏斗物化（新批次根）→ 去重 → 分层抽样（新 seed，登记）→ **v3.2 同口径判读 + 二读门** | 判读纪律同 P0-1（程序侧零 LLM；判读派 ZCode 子代理，按 2026-10-18 新派单规矩） |
| 批跑对拍 | T-H 一次性付费批（预注册 hit@1 35–40%）；T-G 只交「同口径前后对照」材料 | 见老师任务书 #8；**本单不发起** |
| 红线探针 | 非目标题字节不变（沿 `byte_invariance_probe.py` 先例：run_inputs 逐字节 + 诊断逐键，版本键/计数键除外披露） | 每步随附 |

**建议验收线（供 CC 拍板/预注册消费，非既成）**：
- 修复兑现率：56 件 pass 中**机械翻过 ≥ 1/3（≥19 件）**且正负控全过；
- 残差面 err_rate 点估计 **≤ 20%**（对照 42.7%；Wilson CI 分开报）为 T-G 放行建议线；
  重测 **< 10%** 可按既定额度宣布该通道降维护；
- 若 <19 件或残差 >20%：停点复盘（方向/范围回 CC 拍板，不自动续刀）。

### 1.3 题域标签纪律

- 全部数字带 **298=RHEA 通用酶学/已见题**；修复类表述=「**工程损耗回收**」，
  须附修复前后同口径对照；禁止表述为系统能力提升；探针/重放数字标「探针 ≠ 预注册 ≠ 成绩」。

---

## 2. 红线（全程，逐条给检查动作）

1. **判分/评测零 LLM**：程序侧（编译/漏斗/判分/重放）不调用任何模型；判读类工作
   （误拒率判读）按 P0-1 已验收模板走、judged_by 如实标通道；调用账（若有）逐笔落盘。
2. **新实验一律新批次根**：本任务全部产物入新目录
   `reports/ppv1_s5b/t_g_fix_2026-10-19/`（gitignored 沿 `.gitignore:57`）或其后缀批根；
   封存 run 只读；**不原地改产**；不动 chain13/14 既有产物。
3. **「一批跑完禁止修一点跑一点」**：T-G 内只做离线重放/单测/探针，**不得**发起中间付费批；
   所有修复变量在 T-H 一次成批出数（预注册登记）。
4. **判分侧互变归一禁改——只动生成/检索/编译侧**：
   - 禁：改 strict 身份比较语义、把互变/质子化归一提升进 hit@1（档 B 未解锁）；
   - 许：T-E 记录侧归一（检索/编译侧，池策略级）；T-D-A/B 披露字段按 **FROZEN_V3 档 A**
     （`cn_only_normalized` 披露、不授 strict）——接入时以 FROZEN_V3 文本为唯一权威；
   - **FROZEN_V3 判据按冻结版执行**（双臂分列、23 题口径、参数指纹含 RDKit 版本、
     V2 正交断言 N3/N7、N1/N4 负控不放松）。
5. **金标/题面零外带**；封存逐题 run 不读；含金标产物只放 gitignored 目录。
6. **池宽 8 / 阈值 0.45 / fallback 0.40 / 排序 / 截断 / 融合序不动**（C 线单变量纪律先例；
   确需动=预注册级拍板）。
7. **单变量纪律**：同批不叠加未登记变量；分族记账可拆（沿 chain13 教训）。
8. 提交按仓规（随轮本地 commit、**不 push** 除 CC 拍板）；主窗口只留「派了什么/结论/下一步」。

---

## 3. 分步实施计划（C → D → 表示层 → stereo 末位）

> 每步=自包含子任务（执行者照单可干）；标 ⚑=依赖拍板/裁定；标 ⚙=已就绪可直接派。

### Step 0（前置，零成本，先做）底数与基线固化

- **干什么**：把 §0.4 侦察探针**脚本化入正式证据目录**（新批次根），产：
  ① 155 件机械结局对照表（修复前基线）；② 56 件子面分桶；③ **全抽样框 1,886 件的
  `transform_no_change` / 元素账 / wildcard 分桶**（把本单 §0.4 从 155 扩到全框）。
- **入口**：`reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/{material_packs_A.json,
  judgement_glmsub_v3_A_batch*.json}` + `src/pathway_v43/pollutant/{s5b_compiler,s5b_builder}.py`。
- **验收**：对照表行数=1,886（或去重口径明示）；与 §0.4 数字逐项对账（155 件口径）；
  脚本 shard/取证纪律沿「审核证据在隔离目录执行」（tmp 副本、`PYTHONDONTWRITEBYTECODE=1`、
  `-p no:cacheprovider`、记录实际 HEAD `ff0b534`/分支 `v4.3`）。
- ⚙ 无依赖。

### Step C1 ⚙ C 线收口（REAUDIT 回修，工程闭合，零化学风险）

- **干什么**（限定范围=REAUDIT 已列的 2×P1+P2，不加新面）：
  1. **P1-BUILD-01**（`s5b_builder.py:593-624`）：供给主份扣除改为**按选定 `main_idx` 位置**
     扣一份（其余 mapped lhs 组分按原序原样保留），同一规则贯通 supply/spectator/声明装配；
     保留合法正控（两份完全同结构仍供一份、双水 spectator=[False,True]）。
  2. **P1-RUN-01**（`search.py:3331-3370` + `production.py:1212-1238`）：B3 恢复路径
     **先幂等发射/核验记录方程 provenance（含内容冲突门）再提交**（或 bundle 存完整发射载荷、
     恢复首消费时核验+幂等发射后提交）；验收覆盖正常/B3 未写/写异常/既定冲突四控 + 合法恢复正控。
  3. **P2-WILDCARD-01**（`s5b_builder.py:620-623`）：恢复冻结边界（整袋不供给）**或**按
     CC 另行定义；默认=恢复边界，`[H]*[H]`/`*C=O` 类收窄须有授权词。
  4. P3-INPUT-01（`production.py:205-207`）：`execution_input_smiles=null` 首消费结构化拒/披露。
- **单测验收**：`tests/test_ppv1_s5b_cosub_supply.py` 补 P1 反例（同 CN 相反手性双份+选定后位
  的供给袋保真；B3 四控）+ 存量 10 件全绿；全量 not-slow 零翻转。
- **对拍**：复跑 `reports/ppv1_s5b/c_impl_2026-10-14/unlock_face_replay.py`（锚 45 行/35 题、
  行级 drift 0）与 `byte_invariance_probe.py`（262 全等 + 35 纯新增 + 1 补位互动；**回修后
  若 45/35 面发生位移，逐行披露并交 Codex 复审**）。
- ⚑ 依赖：无 teacher 裁定；wildcard 若选「另行定义」→ CC 拍板。
- **为什么第一刀**：已发货管线（policy-7 在批）带「退回未回修」欠账，T-H 发车前必须闭合；
  纯工程、零化学、对拍脚本现成。

### Step C2 ⚑ 锁 2：元素适配 / 对齐容量（重工程，预注册级）

- **现状**：`template_elements_no_fit` 704 件（1192 重放口径 59%）、sim13 钥匙面 81 行
  （元素适配 62+对齐 17）、本样本中心锚定 ≈27+元素账 6。**这是 A 通道误拒的最大剩余面**。
- **必须走设计轮（本步先产设计稿+预注册，再实施）**：
  1. 死因细分（零成本探针）：704 件按 主/袋、单元素/多元素、多份/质子账、rhea/EAWAG 分桶；
  2. 候选解形态（二选一或分级）：
     - **元素账口径修**（轻）：前门与编译层的元素多重集改为**主组分锚定 + 袋并入**口径
       （主组分元素 ⊆ 底物⊕袋；整侧多重集仅作披露）——直接覆盖「主合袋短 6 件 + 部分 704」；
     - **中心锚定对齐**（重）：对齐从「全供体匹配」放宽为**中心/邻域锚定匹配**（与判读 v3.2
       L1/L2 同构；L3 差异=披露不拒）——覆盖本样本 ≈27 件；**属编译判据语义变化**，
       须 mimo 场景 1 + Codex 复审 + **暴露面测量**（新开编译行、池变化、现有 strict 题挤位）
       + 保留全匹配合法正控与「歧义即拒」。
  3. **暴露面前置**：放宽前先出「新开编译候选行数/涉及题数/∩现有 strict 题数」（沿 R0/P1-P3
     探针先例，零成本）；无该数字不发货。
- **入口**：`s5b_compiler.py:120-175`（`template_elements_fit`）、`:487-505`
  （`enumerate_template_alignments`）、`:884-1010`（`_compile_donor_template_impl` 对齐段）；
  `s5b_builder.py:1073-1090`（前门调用点）。
- **单测/对拍**：分档重放存活率（704 件 + sim13 81 件）；对拍=298 题全量池重放前后对照 +
  非目标题字节不变探针 + 负控（该拒件不翻过）。
- ⚑ **teacher 豁免族裁定依赖**：本步解锁的事件若带机制类共底物（O₂/NH₃/HCN/金属/有机）
  参与物，按冻结设计**维持诚实 partial**（封顶，不洗白）；**若要这些事件可进 strict，
  需 teacher 扩大豁免族（预注册级拍板，默认不做）**。纯 H₂O/H⁺/Pi/PPi 袋走既有 v1 豁免面。
- ⚑ 排期与范围（轻刀/重刀）按设计稿数字交 CC 拍板（沿 C 重设计「单杠杆先行」纪律）。

### Step D1 ⚙ D 线交集探针 + 模板映射完整性刀（先探针，后定刀）

- **现状修正（侦察发现）**：D 现设计书主体（扩检索三件套）对本靶面**不直接对症**——对 A 通道，
  真对口的子面是「模板映射不完整（transform_no_change）」17 件（EAWAG 15 + RHEA 2），
  其修复机制=**给模板改动原子补 map 号/补全半映射键**（确定性重映射），而非往检索宇宙加新模板。
- **D1.1 探针（零成本）**：全抽样框 1,886 件中 transform_no_change 类占比与来源分桶
  （rhea/enviPath/EAWAG 各自量）；对 17 件查 `rxnmapper_templates_v1.jsonl` 是否有同 record 模板、
  其变换提取/对齐/编译结局如何（**交集≈0 时如实宣布 D 库不覆盖 EAWAG 面**）。
- **D1.2 决策与刀**：若交集有料 → 接线（模板资产入库定位=gitignored 大件、analog 检索接线
  `s5b_builder.py:1198`、池策略版本升号、单变量预注册）；若交集≈0 → 转「**确定性重映射工单**」：
  对 EAWAG/enviPath 侧模板补映射（规则级、零化学判断），试点 17 件 + 分档重放。
- **验收**：17 件 transform 层不再拒（拒因迁移表）；负控=该拒件仍拒（35 件 reject 同面样本不翻过）；
  既有 unlock/byte 探针零漂移。
- ⚑ 若启用 D 设计书主干「袋化语义」→ 化学评审+mimo + 预注册（与 C 面分开记账，禁混变量）。
- ⚑ teacher 裁定依赖：无新裁定；袋化措辞若涉及豁免族口径同 Step C2 注。

### Step E1 ⚑ 表示层接入（FROZEN_V3 执行：T-E 主刀 + T-D 披露轴）

- **前置子任务（FROZEN_V3 §11 缺口，必须先闭）**：
  1. **来源批次逐行只读重算**（缺口 5）：T-E 82 行/31 题 的对齐恢复账、T-D 14/6 题的
     分臂重算——持久证据入仓（新批次根）；校准样例（P3/P4 正控、N8/N9 负控）复现；
  2. **run 身份/缓存 key 闭合设计**（缺口 6，§5.3）：记录侧归一改变记录字符串 ⇒ 缓存/复现
     key 处置（AGENTS「身份与完整性在首次消费时闭合」）——设计稿+Codex 复审后再动码。
- **T-E 实施（检索/编译侧，本刀主菜）**：
  - 入口：`recorded_source.py:2060-2130`（记录侧 donor 归一后构建 mapped_lhs/rhs）+
    analog 模板侧对齐前归一 + `s5b_compiler.py:487-505` 消费点；
  - 改动要点：仅记录侧 `Uncharger()` 默认配置（逐组分→点号重接，**底物侧不施加**但披露
    覆盖限制）；analog 行原子映射号保留；逐行机读标签
    `record_side_form_norm ∈ {applied, not_applicable, failed}`；**逐行原子级披露**（被改原子
    电荷/氢变化分开列、模板匹配原子∩被改原子=「过度对齐风险」信号行**交人工复核**）；
    fail-closed 同公共约定；三层口径**分开报**（对齐行→compiled 行→strict 命中，第三层本轮 unknown）。
- **T-D-A/B 实施（判分侧披露轴，若同批）**：`evaluation.py:842-844/956` 加
  `PPV1_CRITERIA_V3` 常量+白名单+resolve；**缺省 v1 字节不变、显式 v2 行为不变、V3 显式启用**；
  双臂字段分列（默认臂=敏感性披露臂、不具 strict 准入；候选主臂 sp3 立体保留=档 B 唯一候选、
  **本轮未解锁**）；B-6 碳酸体系闭集机读排除；FROZEN_V3 §4/§5 判据逐条落实（不得改写文本）。
- **单测**：正控 P1/P2（分臂待验值就地重算）/P3/P4；负控 N1（ISOMER-TRUE 23 题不相等）/
  N3·N7（V2 正交）/N4（S5A-01 许可门）/N8/N9/N10；参数指纹含 RDKit 版本。
- **对拍**：V3 与 v1/v2 **同批只读重算并列披露**（rescore 先例）；本样本 3 件质子化件
  经 T-E 后进入修复兑现表；旧批零回写。
- ⚑ 依赖：无新化学裁定（D01–D07 已终审）；**档 B 未解锁**（若要解锁=CC 拍板+门槛①②③④全过）。

### Step S1 ⚑ stereo / 协议扩展（末位，登记不排期）

- 本样本仅 0–1 件触及（a-32875…立体翻转件）；**只登记**，范围与是否并入本批由 CC 拍板。
- 入口备查：`s5b_compiler.py` `stereo_edit_unsupported` 分支、`ATOMTOOL_VERSION` 承载面。

---

## 4. 排障表与回传义务

### 4.1 排障表（前车之鉴，遇症查表）

| 症状 | 原因（已踩实例） | 处置 |
|---|---|---|
| 子代理产物 qid/case_id 截短 | GLM 子代理写盘截 64 字符（2026-10-19 批 4 实例） | 验收三件套**必须含 qid 逐件对账**，按材料包权威源回填（机械替换，判定不动） |
| 提示词替换静默无操作 | sed 替换串不在模板（两次翻车） | 占位符规矩 `CASE_IDS_PLACEHOLDER`；替换后校验行数+清单集合 |
| 探针污染证据目录 | 原地跑写库/日志 | 隔离 tmp 副本执行；`PYTHONDONTWRITEBYTECODE=1`、pytest `-p no:cacheprovider`；不改封存资料 |
| 旧脚本硬编码 HEAD 误认 | 记录链断 | 记录**实际** HEAD/分支/schema/命令/输入输出哈希；本单基线 HEAD `ff0b534`（v4.3） |
| 免费网关断流/诈尸 | opencode 线 | **已退役**——判读/审阅派 ZCode 子代理；Codex 走 ChatGPT.app 二进制；断流续跑必须带 `-m` |
| CLI 退出码 1 ≠ 活没干完 | 日志尾部有完结回报 | 判活以日志尾部+产物验收（行数/集合/锚）为准，先验收再定重跑 |
| 全量 pytest 红绿归因混乱 | 并行工作树 | 定向子集+提交边界隔离；全量数字如实附注基线 |
| 字节不变探针 drift | 目标外行为漂移 | 逐键比对（版本键/计数键除外披露）；drift≠0 即停 |
| 对拍 45/35 面位移 | C 回修副作用 | 逐行披露 + Codex 复审，不得静默接受 |
| 判读门不达线（≥90% 且 κ≥0.6） | 规则边界分歧 | **停下报 CC**，不自行处置（处置选项报「回炉/代审/口径变更」三档） |

### 4.2 回传义务

1. 每步完成：更新本文件状态表 + `docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` 对应行；
   向主会话回报「派了什么/结论/下一步选项」三件。
2. 每步产物：新批次根 + 脚本 + 机读 json + 说明 md；**回传三件套=行数/清单集合/哈希**。
3. **停下报 CC 的触发**：判读门/负控不过；红不翻绿（同任务自动重试 1 次仍败）；范围外要求；
   金标/题面/封存触碰风险；费用异常（本单预期零费用）；连续两轮无实质进展。
4. 修复兑现表与残差重测数字**逐项带题域标签**；对外表述遵循「工程损耗回收+同口径对照」纪律。
5. 争议处理：任一方（实施/审核）发现事实错误须明确更正；外部意见只采信到与程序证据互证为止。

### 4.3 产物归宿与提交纪律

- 新批次根：`reports/ppv1_s5b/t_g_fix_2026-10-19/`（gitignored，沿 `.gitignore:57`）；
  评审报告/证据按「评审侧文档归宿」惯例留未跟踪由 CC 定期自决。
- 随轮本地 commit、**不 push**（除 CC 拍板）；只加本任务文件（先例：C 线 §四红线自查）。

---

## 附录 A：关键路径清单（新窗口速查）

- 现状与依据：`docs/P0_1_ERR_RATE_RESULT_V3_DRAFT_2026-10-18.md`（v3.2 读数）、
  `docs/P0_1_A_RULES_V3_DRAFT_2026-10-18.md`（判读规则 v3.2）、
  `docs/P0_1_PROBE_INITIATION_INPUT_2026-10-16.md`（测量设计稿）、
  `docs/HANDOFF_P01_REJUDGE_2026-10-18.md`（活状态与机器参数）、
  `docs/P0_TRIO_VERDICT_2026-10-15.md`（三件套裁决）、
  `docs/S5B_COMPILE_FUNNEL_DECISION_MEMO_2026-10-13.md`（2818 构成）、
  `docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md`（C 归因）、
  `docs/LOCK12_REPLAY_VERDICT_2026-10-15.md`（锁 1/锁 2 裁定）、
  `docs/CHAIN14_LEVER_DECISION_2026-10-15.md`（L3 勘误+杠杆拍板材料）。
- C 线：`docs/C_COSUB_SUPPLY_{DESIGN_PREREG_2026-10-14,REDESIGN_PREREG_2026-10-15,
  IMPL_DELIVERY_2026-10-14,IMPL_CODEX_REVIEW_2026-10-14,IMPL_CODEX_REVIEW_2026-10-14_REAUDIT,
  IMPL_LOCAL_REVIEW_2026-10-14}.md`。
- D 线：`docs/D_RXNMAPPER_SCALEUP_DESIGN_PREREG_2026-10-14.md`、探针
  `reports/ppv1_s5b/d_probe_rxnmapper_2026-10-14/`、对齐侦察 `reports/ppv1_s5b/d_align_recon_2026-10-14/`。
- 表示层：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md`（生效口径）、
  `docs/TDE_CRITERIA_V3_FREEZE_DEPUTY_REVIEW_2026-10-18.md`（代审终审）。
- 代码入口：见 §0.1 表；探针先例 `reports/ppv1_s5b/c_impl_2026-10-14/{unlock_face_replay.py,
  byte_invariance_probe.py}`、`reports/ppv1_s5b/l1_replay_2026-10-15/l1_replay_probe.py`。
- 环境：`cwd=/Volumes/CC/Enzyme_Agent/dependingv43`；
  python=`~/miniconda3/envs/depending43/bin/python`（RDKit 2026.03.6）；HEAD `ff0b534`（v4.3）。

## 附录 B：侦察探针复现口径（§0.4 底数，可第三方复跑）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 ~/miniconda3/envs/depending43/bin/python - <<'PY'
import json, sys
sys.path.insert(0, 'src')
from pathway_v43.pollutant.s5b_compiler import template_elements_fit, compile_donor_template
from pathway_v43.pollutant.s5b_builder import analog_cosub_supply
base='reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/'
mp=json.load(open(base+'material_packs_A.json'))
rows=[]
for f in ['judgement_glmsub_v3_A_batch%d.json'%i for i in range(1,6)]:
    rows += [json.loads(l) for l in open(base+f) if l.strip()]
jud={r['case_id']:r for r in rows}
for e in mp:                       # 逐件：复刻 policy-7 救援链机械结局
    t=e['record_content']['templates'][0]
    lhs,rhs,sub=t['mapped_lhs'],t['mapped_rhs'],e['substrate_smiles']
    sup=analog_cosub_supply(mapped_lhs=lhs,mapped_rhs=rhs,substrate_smiles=sub)
    sub2=sub+'.'+'.'.join(sc for _mc,sc in sup['supply']) \
         if (sup['status']=='supply' and sup['supply']) else sub
    gate=template_elements_fit(lhs,sub2)
    out=compile_donor_template(mapped_lhs=lhs,mapped_rhs=rhs,center_atoms=[],
        substrate_smiles=sub2,record_id=str(t.get('record_id','tpl')))
    print(e['case_id'], jud[e['case_id']]['judgement'], sup['status'],
          'gate2=%s'%gate, out.get('status'), out.get('reason'))
PY
```

- 口径：单模板/件（material pack 首模板）；`center_atoms=[]`（对齐判定不受其影响）；
  直编分支=绕过前置门以区分「前门拒」与「编译层拒」；**≠ 正式重放**（正式件须带
  ref.center_atoms 与真实检索序，入新批次根复算）。
- 与 §0.4 对账锚：56 件 pass 分桶 17/≈27/6/6/3；155 件直编结局
  `pass: 39 no_alignment + 17 transform_no_change`、
  `reject: 39 + 35`、`uncertain: 11 + 14`。

---

*本任务书为设计侦察产物：不含金标、不含题面结构串外带（材料包内结构串只在本机进程内消费）；
未冻结、未派工；下一步=CC 过目后按 Step 0→C1 派首个实施子代理。*