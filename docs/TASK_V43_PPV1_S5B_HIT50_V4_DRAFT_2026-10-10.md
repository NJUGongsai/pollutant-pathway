# PPV1 S5b HIT50 v4 任务包草案——RHEA 主语料接入 recorded 直通供给通道（2026-10-10）

状态：`draft_for_main_session_review`（**未授权实施**；主会话审定改定后生效，
生效时状态改 `implementation_authorized / scientific_target_pending`）。

撰稿：v4 草案撰稿子代理（2026-10-10）。本草案基于：v3 任务链全部已读材料
（任务书/尸检/交付书/正链复审/R1-R2 复审/复测发车登记）+ 撰稿方**独立复核
探针**（§7 证据：语料实盘与 298 题底物覆盖两口径复算，与主会话给的
147/159 全部吻合）。上游任务链：v3 实施轮 0c6e45d → R1/R2 回修 → 当前
HEAD `d08432c`；正链 R2 复审判 S5B-V3-02 两残余未清零、chain10 暂不放行
（复测登记已建，§5 顺序条款按"chain10 复测出分在前、v4 实施在后"排序）。

依据（全文已读，冲突处以本文明文为准）：
- `docs/TASK_V43_PPV1_S5B_HIT50_V3_2026-10-10.md`（体例模板；其 §0/§1/§3
  条款本草案全文继承）；
- `docs/S5B_HIT50_V2_POSTMORTEM_2026-10-09.md`（尸检：供给漏斗 L0-L4、
  U=100 主导死因=recorded 编译墙+语料覆盖墙）；
- `docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_DELIVERY_2026-10-10.md`（W-V2 编译
  墙攻坚实际恢复 4/228、stereo/charge unsupported 边界、语料不换装审计）；
- `docs/POLLUTANT_PATHWAY_S5B_HIT50_V3_CODEX_REVIEW_2026-10-10.md` 及
  R1/R2 复审（W2 哈希/许可/分层纪律；金额守卫 budget_guard 机器配置——
  v4 新批须沿用，见 §5）；
- `docs/S5B_HIT50V3_RETEST_REGISTRATION_2026-10-10.md`（chain10 冻结身份
  与预算机器配置现状）。

核心判断（一句话）：v2/v3 尸检证明供给墙是 U=100 的主导死因；主语料
43,177 条（RHEA 37,100 + enviPath 6,077，§7 实测）从未被 recorded 直通
通道消费——现通道只消费 4,454 条 EAWAG 环境库（经
`engine.identity_block["library_path"]`），而 298 题本是 RHEA 酶学题。
v4 的主杠杆 = 把 corpus_v1 主语料接入 recorded 直通，**判据与身份语义
全部沿用 recorded_source 现行实现，不另写第二套**；开工第一件事是冻结
底物匹配身份语义（§1 硬条款）。

## 0. 目标、基线与完成含义

- **验收目标（沿用用户指定，不变）：298 题域主口径 matched_strict
  hit@1 ≥119/298（39.93%，"40% 档）**；hit@5 ≥150/298 维持参考列
  （防降线换通过，S5B_PASS_LINES 历史线照旧只读）。
- **基线（回填条款）：以 chain10 复测批（v3 工程：提交序贯彻调度序 +
  有界键差 + 前置门 + 守卫）的终判分为 v4 基线，实施前回填**。当前
  U=100/H5=89/L=11 是 v2 批基线；v3 的 H1≈73/H5≈100 属反事实先验
  （旧候选固定集合诊断，非新批承诺）。
- 完成含义沿用 v3 任务书 §0：编译接受率、测试绿、复审放行均不等于
  科学达标；最终只由 v4 新批同口径零 LLM 判分判定；缺口是净新增，
  不把检索命中数、编译通过数相加作承诺；结果定位
  `seen298_post_hoc_repair_check / known_evidence_reconstruction`，
  不称独立盲测、不外推 dev 题域。

### 0.1 可达性测算（证据导向、互证区间，非承诺）

供给面（题级底物覆盖，本草案 §7 探针实测；编译/命中面为外推）：

| 供给口径 | 底物覆盖 | 严格净增（vs EAWAG 147） | 依据 |
|---|---|---|---|
| EAWAG 现状（唯一被消费库） | strict 147 / CN 182 | —（基线） | §7；147 与尸检 strict_exact 层三方一致 |
| corpus_v1 整串严格（donor_A 全串==底物） | **159/298** | **+12**（11 RHEA + 1 enviPath；1-4 条记录/题、零通配符、全有产物、方向 LR-only 4/RL-only 5/双向 2/无方向 1） | §7；147⊂159 复核 True |
| corpus_v1 组分严格（底物=donor 某组分） | 231/298 | +84（须 §1 donor 口径裁定+共底物声明设计） | §7；本探针新增口径 |
| corpus_v1 整串 CN / 组分 CN（电荷归一立体盲） | 209 / 273 | CN 增量 +50 / +42（对各自严格口径） | §7；cn_identity 同引擎口径 |
| 主会话简报"另一会话 201/298" | 未复现 | —（其 +54=201-147 引自未披露方法） | **方法未披露，不得引用为事实**；本探针三个 CN 口径 182/209/273 无一等于 201 |

**编译墙折扣（诚实外推，不承诺）**：EAWAG 先验=147 题底物 strict 命中
→ 80 题编译失败（54.4%）→ 67 题进池 → 41 题 strict 命中（在池 61%；
端到端 41/147≈28%）。RHEA 记录走同一编译器（`compile_recorded_
reaction`/推断映射/产物多重集 gate），其编译失败面**未测**，且额外
携带三重衰减面：通配符记录（RHEA 8,502 行含 `*`，本探针）、多组分
donor、全量无原生映射（mapping_status 全 absent）。按 EAWAG 端到端
先验的纯算术外推：+12 底物 ⇒ ~3 题净命中；+84 ⇒ ~24 题——**外推上界，
不承诺**。任何"RHEA 接线后 U 直达 150"的说法都不成立；真实增益以
v4 新批复测为准。

## 1. 底物匹配身份语义先行披露（本草案特有硬条款；开工第一件事）

**v4 开工第一件事 = 冻结底物匹配身份语义，先于任何接线代码。** 未冻结
前不得开工 W-V4.1 的检索/分层分支；不得默认采用最宽口径换覆盖数。

1. **两口径的定义与覆盖差（本探针实测，方法见 §7）**：
   - 严格口径（canonical 含电荷/立体，与仓内 `strict_identity_of`
     同一事实源）：EAWAG 147 / corpus 整串 159 / corpus 组分 231；
   - CN 口径（`domain.identity.cn_identity`，=引擎 `X._identity`
     电荷归一立体盲）：EAWAG 182 / corpus 整串 209 / corpus 组分 273；
   - 覆盖差 159 vs 209（整串）/ 231 vs 273（组分）＝ +50/+42 题——
     即"底物语料命中但电荷/立体异"的候选面。主会话简报引用的
     "201/298"方法未披露，**本探针未复现，不采信为事实**；采信须
     待其方法披露后与程序证据互证。
2. **对 strict 直通候选资格的影响（现行分层不动摇）**：CN 命中而
   严格身份不同 ⇒ 只进 `recorded_cn_candidate` 层（analog 级候选），
   **不得升 strict**——沿 `recorded_source.find_recorded_exact` 现行
   分层判据，一字不改。若要为 RHEA 侧增设中间档（如"CN 同且仅立体
   异"），属口径级裁定：走新预注册独立字段 + teacher/mimo 场景 1
   判据评审，不得在工程轮静默放宽。
3. **donor 侧口径（第三维，本探针新增披露）**：整串（donor_A_smiles
   全串==底物，与 EAWAG 现行语义一致——EAWAG 库内 89/4,454 行多组分
   donor 同样不匹配单底物，即现行通道事实上就是整串语义）vs 组分
   （底物==donor 某一组分，覆盖 231）。组分语义的严格资格**必须**
   附带共底物/辅因子角色判定与声明（H⁺/H₂O/O₂/NAD⁺/NADH/CO₂ 等高频
   共组分，§7 实测计数）——"出现为组分"本身不构成 strict 资格，
   否则会把底物是辅因子的题灌入无关反应记录。
4. **预登记与裁定路径**：三个口径维度（底物身份口径、donor 侧口径、
   层级资格）的选择权交主会话/teacher 裁定并预登记（如独立字段
   `corpus_donor_semantics` / `recorded_component_tier`）；旧批/旧线
   不回写；裁定前本草案 §0.1 只按已披露口径给数，不引用未核数字。

## 2. 开工基线、红线与不可改的尺子（继承 v3 任务书 §1 全文，要点重申）

- 开工前读 AGENTS.md；记录实际 HEAD/工作树/资产身份（本草案成稿时
  HEAD=`d08432c`，工作树含他人未跟踪文件保持不动）；沿返工教训 #1
  先列适用入口矩阵（§3）再修同一规则。
- **零金标入预测侧**：不读 298 题卷/金标/旧答卷/封存逐题 run；
  pool-provider 与语料检索实验**只允许消费 substrate_smiles 字段，
  禁读 products**（本草案 §7 探针即此口径，可复用）；金标只进答卷
  封存后的判分隔离进程。允许例外沿 v3：批根 metrics/manifest 池诊断/
  runs 答卷侧聚合。
- **冻结判据不可改**：strict 身份/CN 含义、participant 集合与
  step_scope、match_reference_edges、主 K 候选定义与 (created_at,
  event_id) 顺序、分母 298、失败规则、S5B_PASS_LINES 历史含义——
  全部零触碰。W-V4.1 只新增语料供给入口，不碰 scorer。
- 适应性评测诚实标注（`seen298_post_hoc_repair_check`）、每改动写
  通用机制理由、独立构造正负控、禁止 qid/本卷定制——v2 任务书 §1.1
  全文继承。
- **授权语料哈希审计先于消费（fail-closed）**：corpus_v1/donor_index/
  library 的 SHA 已在引擎身份块（`env_asset_root.resolve_and_verify`）
  与仓内 `MANIFEST.sha256` 双锚（本草案 §7 实测三文件 sha 与 manifest
  一致）；消费入口必须 sha 锚定后回读（`load_library_index` 同款），
  身份不一致 fail-closed 拒（源 hash 篡改负控）。
- **语料消费许可前置门（本轮新增，授权级）**：RHEA/enviPath 语料的
  recorded 直通消费是**新消费面**（此前 corpus 只供 analog 检索侧）。
  语料来源与授权状态沿资产包 README 与既有 manifest——**开工前由
  主会话/用户确认消费许可，未确认不消费**（AGENTS 红线"语料消费许可
  须先于本轮"的执行条款）。
- 不搬旧批答案/qid→答案表；不 push；实施期零真实模型调用、零花费、
  不部署真实批、不改封存批；评审侧证据在隔离 /tmp 副本执行
  （python -B、-p no:cacheprovider、输入 SHA 前后核验）。

## 3. 共用交付与入口矩阵（W-V4.1 适用入口先列清单）

沿 v3 §2 口径，本轮适用入口（每入口登记消费的身份/事实/版本/
proof_scope 与拒因，复用同源 helper，无第二套判据）：

| 入口 | 消费 | v4 角色 |
|---|---|---|
| `env_asset_root.resolve_and_verify`（v3 冻结模块，只 import 不改） | corpus_v1/donor_index/library 路径+SHA 身份块 | corpus 身份唯一来源（corpus_v1_path/sha256 **已在 identity_block**，无需新哈希机制） |
| `recorded_source._library_identity / load_library_index` | 库身份+sha 锚定回读 | 扩展为 corpus 消费入口（同款 fail-closed；单库→多库或新 index 装配） |
| `recorded_source.find_recorded_exact` | 检索+strict/CN 分层主入口 | RHEA 检索通道接入点（donor 检索实现可选用既有 `donor_index.jsonl`（组分级、95,782 行、SHA 在身份块）或新装配入口——实施方选一并写理由；**身份比较必须同源调用 strict/CN 函数，不另写比较器**） |
| `recorded_source.infer_reaction_mapping / compile_recorded_reaction` | 推断映射+编译+产物多重集 gate | **判据零改动**（corpus 记录同样走推断映射——其 atom_mapping 全 null，见 §7） |
| `adapters/v3_engine.py`（identity_block 装配） | 引擎身份 | 只读复用；不新建第二套 corpus 身份 |
| `s5b_builder.default_pool_provider` | recorded 池槽 | 消费新候选（分层/补位语义不变） |
| build 侧 `compile_failure_histogram` 聚合 | 编译失败直方图 | corpus 侧新增拒因类如实分层（通配符/共底物/无产物） |

## 4. W-V4.1 RHEA 主语料 recorded 直通接线（工程级；本轮主杠杆）

依据：尸检 L0（61 题无任何 EAWAG 记录=语料覆盖墙）+ 本草案 §7 实盘
（43,177 条主语料未被 recorded 直通消费；298 题是 RHEA 酶学题）。

**前置**：§1 身份语义冻结裁定 + §2 授权核实前置门闭合。两者任一未
闭合即停，不开工。

1. **授权与哈希（沿 W2 库 sha 校验纪律）**：corpus 消费入口 sha 锚定
   后逐行回读（`load_library_index` 同款：实际 sha ≠ 身份记录 ⇒
   `library_hash_mismatch` 同语义结构化拒）；记录级 `provenance_sha256`
   字段（逐行已有）作存在性/一致性披露（缺 ⇒ corpus 特有负控结构化拒；
   其语义=构造期来源记录指纹，**不冒充内容完整性证明**，如实登记）。
   装配形态二选一并写理由：identity_block 现有键扩展消费，或新装配
   入口（同源 MANIFEST/身份块校验）——不出现第二套哈希事实源。
2. **字段适配层（corpus_v1 → EAWAG library 结构等价物）**，逐条要求：
   - **完整净产物集合回读**：`product_components`/`product_B_smiles`
     全量组分（库行序承载），对齐 EAWAG 同 (btid,reac_id) 全产品行
     语义；enviPath educt-only 580 行（parse_note=envipath-educt、无
     product_B）与 RHEA no-structure 2 行 ⇒ `record_missing_or_
     incomplete` 同款诚实拒，**不冒充完整 record**（§7 实测：159 题
     的整串匹配记录全有产物，该拒因不影响 12 净增面）；
   - **角色与方向**：RHEA 每个 master_id 恰两行（LR/RL 两侧互换，
     18,550 唯一 master ×2 = 37,100，§7 实测）——适配层必须按
     master_id 去重语义 + 方向声明（RL 行的书写方向=生化反方向；
     "库行序承载方向"的既有语义延续）；同一 master 双行不得重复
     入池占双槽；**方向反负控按 corpus 形态重定义**（RL 行按反方向
     冒充正方向 ⇒ 拒）；
   - **过滤声明**：donor 多组分时共底物/辅因子组分**声明化**（对齐
     引擎 ion/cofactor_filtered 的如实透传纪律：不静默丢弃、不冒充
     新原子/净产物、不把共底物对应产物算进底物净转化）——组分语义
     的共底物↔共产物对应判据属设计件，须交设计复审（与 §1.3 裁定
     联动）；整串语义下该声明退化为空集；
   - **mapping_status 处理**：corpus_v1 全部 43,177 行 atom_mapping=
     null、mapping_status='absent'（§7 实测）⇒ **全部走
     `infer_reaction_mapping` 推断映射通道**（`mapping_origin=inferred`
     强制；预算/歧义披露/有界键差 fallback 全部沿用，零新判据）；
     负控=伪造原生映射来源的记录必须拒（corpus 侧不存在原生映射，
     不得出现 mapping_origin=native）；
   - **通配符**：RHEA 8,502 行含 `*`（R-基通配，§7 实测）⇒ 结构化拒
     （如 `wildcard_unsupported`），如实分层计数，不冒充可编译。
3. **strict/CN 分层沿用 recorded_source 同一判据**：分层比较函数同源
   调用（donor 严格身份==底物 ⇒ strict；CN 同而 strict 异 ⇒ cn
   candidate 不升格）；CN 候选按 analog 级入池标注，与 EAWAG 侧
   候选同池同规（补位/去重/预算语义不变）。
4. **负控族（沿 W2 七类 + corpus_v1 特有扩展，逐类构造）**：
   - W2 七类全保留：①源哈希篡改（库/corpus sha ≠ 身份记录）拒；
   ②CN 同而电荷/手性不同 ⇒ cn_candidate 不升 strict；③方向反；
   ④另一底物（donor≠底物不属 exact）；⑤filtered 单产品行冒完整 ⇒
   完整集合核对拒；⑥缺产物/来源 ⇒ 结构化拒；⑦映射枚举触顶 ⇒
   歧义披露拒；
   - corpus_v1 特有四类：⑧unmapped 形态（无原生映射记录冒充原生
   映射来源拒）；⑨provenance 缺失（记录缺 provenance_sha256 ⇒
   结构化拒）；⑩通配符记录（含 `*` ⇒ 结构化拒不冒充可编译）；
   ⑪master 双向重复（同一 master_id LR/RL 双行重复入池/方向冒充 ⇒
   拒）；
   - 合计 **11 类**；正控：RHEA 整串严格命中的合成同构用例编译入池
   并执行成事件（含一例 RL 方向、一例多组分 donor 声明）+ 合法
   EAWAG 正控全数保持（既有 W2 测试零回退）。
5. **mimo 场景 1 判据评审（随交付）**：W-V4.1 涉化学判据（底物匹配
   身份口径、共底物声明语义、strict 资格边界）——交付规则级、自
   包含、零金标/零题面的 mimo 请求 md（沿
   `docs/MIMO_PPV1_S5B_HIT50_V4_COPRODUCT_IGNORE_TIER_REVIEW_REQUEST_
   2026-10-10.md` 体例）；送审与否与通道按 AGENTS.md 现行条款（涉
   金标外发须用户逐次拍板；本请求零金标内容）。
6. **交付计数与诚实边界**：底物命中→编译→进池→提交→命中分层计数
   （新批复测后）；**检索命中数/编译通过数不冒充命中数**；corpus
   侧编译失败直方图如实分层（通配符/共底物/charge/stereo 各自拒因
   计数）；RHEA 记录的编译成功率是**未测量面**，交付书必须登记为
   unknown，不以 EAWAG 先验冒充。
7. **风险**：供给面放宽引入错误对应先验（共底物误配、RL 反方向、
   推断映射歧义）——产物多重集 gate（执行产物=库记录净产物多重集）
   与方向/角色声明是仅有的守门，必须在全部公共入口生效；池槽膨胀
   （RHEA 候选多）与 W4 补位语义联动的披露。

## 5. 复审后发车与顺序条款（继承 v3 任务书 §3 全文 + 本轮顺序）

**顺序条款（单变量纪律，本轮新增明示）**：

1. **v4 实施排在 chain10 复测兑现排序修复价值之后**：chain10 批=v3
   工程修复归因轮（提交序+编译墙+池深+守卫），v4 批=RHEA 接线轮，
   **两轮收益不混账**——各自独立预注册、同尺子零 LLM 判分、独立
   归因；不得把 v3 反事实/chain10 数字与 v4 供给数字相加作承诺。
2. chain10 现状（如实，本草案成稿时）：正链 R2 复审（`d08432c`）判
   S5B-V3-02 两残余（A 自矛盾 total 低额结清、C 已启用金额帽整块缺失
   降级 legacy）未清零、**暂不放行**；复测发车登记已建
   （`ready_for_real_retest`，通道 C 意见先放行、正链恢复后复核确认
   口径；正链 R2 §7.1 同时登记了当日价未刷新等发车条件缺口）。
   **v4 开工前置 = S5B-V3-02 清零 + 正链放行 + chain10 出分回填基线**；
   该前置的进度与裁定以主会话实际推进为准，本草案不预支。
3. 复审后新预注册与真实 298（继承 v3 §3 全文）：主会话复审有有限
   阻塞则回修再交付；通过转 `ready_for_real_retest`，新登记冻结
   （代码/资产/protocol/prompt/池/融合/排序/profile/模型身份/
   budget_guard 机器配置，任何变化即停批另立）；首批 profile 沿
   v2/v3 冻结值（depth=1、8 备选、width=2、1 logical/题、format0、
   HTTP retries4、workers/在途 40、RPM180/TPM2.7M、HTTP cap 1490）；
   冒烟前缀 10 题只看运行完整性/费用；零 LLM 判分、§9-4 双门
   （evaluation-5 + 程序门）、U/H5/L 一并披露；达标标
   `target_met_seen298`、未达标交完整报告与实质不同下一版。
4. **金额守卫 budget_guard 机器配置沿用（v4 新批须沿用，R1/R2 复审
   与复测登记 §二 的现行配置）**：`budget_guard.json` cap_cny=60、
   input 0.8/output 2.8 元/Mtok（2026-09-29 价格沿用值——发车日须
   核当日价或可证保守上界，R2 §5 义务）、input_tokens_bound=30000、
   max_output_tokens=8192；**每次付费发送尝试（含 retry）发送前原子
   预留**（settled+unsettled+reserved+bound≤60 才发）；429/部分
   usage/未知结局保守保留不退；结算幂等；overrun 披露不回滚；不自动
   升帽。S5B-V3-02 两残余的收口修复先于一切 v4 发车（同 §5.2 前置）。
5. 同模型 GLM-5.3-Flash、1 logical/题、正链复审放行；不自行点火。

## 6. 伴行包（不并入 W-V4.1 单变量归因；每包标注级别）

1. **①EAWAG 编译墙剩余分类再攻（工程级，列选项不默认做）**：116 次
   no_structure_correspondence 按主会话口径=44 真无对应 + 22 超界 +
   可修类 50；可修类中 bond-diff 1/2 已修但 v3 实际仅恢复 4/228
   （映射层 47/116 恢复被更深层门拦截：charge 24=W5 保留边界、
   触顶 6、去芳香 3 等；product_set_mismatch 28 全 0 恢复）。v4 是否
   再攻（深层门 charge 24 / 触顶预算 / product_set 28）列选项交主
   会话；若做，先补分类定义与互斥计数的算术闭合（正链复审对 v3
   交付 §5.1 分类的 P2 订正义务）再动代码。
2. **②stereo 消解设计（口径级/设计级，独立设计轮，不随 v4 搭车）**：
   mimo r28 E1-E3 已评审（手性中心随 sp3→sp2 键级变化消解——"立体
   变化发生在键级变化原子上则为派生属性"方向），**警告过度泛化**；
   命中面 ~2-3 题；须另批窄能力证明（执行后确实不再是立体中心、
   rhs 无手性声明、仍存中心/新建中心不放行、执行后 rhs 立体同源
   复核与机器诊断；E/Z、非四面体不支持范围明示）。升级须按 v3
   W-V2.4 条款先交设计复审，不因数量压力放行"乱加立体"。
3. **③67 题全语料无覆盖（teacher/来源决策，不属工程）**：组分严格
   口径下 298-231=67 题在全语料（RHEA+enviPath）无 donor 覆盖
   （§7；注意与尸检"61 题纯 novel"口径不同：61=EAWAG-CN 引擎检索层、
   67=全语料组分严格层）。这 67 题的出路在语料来源扩展（teacher/
   来源决策），v4 工程不覆盖、不承诺。
4. **④语料修复方向（授权级/语料资产轮，须新身份）**：v1 模板反应
   原子未映射（v3 审计"真供给损失 47 条=transform_no_change 39 +
   stereo 8"——39 是模板条数非题数）+ v2 语料 center 数据缺陷
   （center_map_not_in_donor 59，净更差 76<84 不换装）。修复属语料
   资产轮：新语料身份 + 沿 v3 交付书 §十二.4 待复审项 + 哈希/
   授权纪律同 §2；不与 W-V4.1 混轮（接线消费的是现版 corpus_v1，
   修语料=另一身份另一轮）。

## 7. 证据：撰稿方独立复核探针（方法与数字）

- **环境与纪律**：`/Users/cc/miniconda3/envs/depending43/bin/python -B`
  （rdkit 2026.03.6），仓库根目录执行，全只读；脚本与结果留存
  `/tmp/s5b_v4_draft_probe/`（易失；`probe_coverage.py`/
  `probe_detail.py`/`coverage_result.json`）。**只读
  `reports/ppv1_s5b/s5b_298_local/run_inputs/*.json` 的
  `substrate_smiles` 字段（预测侧输入）**，金标/products 零读取；
  语料两库逐行只读。
- **口径**：严格=rdkit isomeric canonical（`MolToSmiles` 默认；实现侧
  须用仓内 `strict_identity_of` 同源函数，本探针为覆盖估算）；
  CN=仓内 `domain.identity.cn_identity`（=引擎 `X._identity` 口径）。
- **语料实盘（与任务简报全部吻合）**：
  - `library_full.jsonl`：4,454 行=4,128 唯一 (btid,reac_id)、2,721
    唯一严格 donor（CN 唯一 2,678=README 口径）、packages
    BBD 1002/SEDIMENT 931/SLUDGE 544/SOIL 1977、89 行多组分 donor；
    sha256 实测 `042e9e2c…`=MANIFEST；
  - `corpus_v1.jsonl`：43,177 行=enviPath 6,077（master_id 全空；
    580 educt-only 无产物 + 5,497 带产物=README"5,497 environmental
    reaction records"）+ RHEA 37,100=18,550 唯一 master_id ×
    (LR,RL) 恰双行（两侧互换，逐例核验）；atom_mapping 全 null、
    mapping_status 全 'absent'、reaction_smiles 37,098 有/2 行
    no-structure；RHEA 含 `*` 通配符 8,502 行（enviPath 0）；
    sha256 实测 `186a1dad…`=MANIFEST；
  - `donor_index.jsonl`：95,782 行（rhea 90,026/envipath 5,756），
    组分级 donor 索引，477 行 donor='*'；analog 侧
    `uspto_relaxed_index_v1.jsonl` 188,725 行、
    `corpus_templates_v2.jsonl` 17,183 行（=简报数）。
- **298 题底物覆盖（题级；209 唯一严格底物）**：EAWAG 严格 **147** /
  CN 182；corpus 整串严格 **159** / 整串 CN 209；corpus 组分严格
  231 / 组分 CN 273；**147⊂159⊂231 复核 True**；整串严格净增 12
  （11 RHEA + 1 enviPath；1-4 条匹配记录/题、零通配符、全有产物、
  方向 LR-only 4/RL-only 5/双向 2/无方向 1）；组分严格净增 84（1 enviPath-only
  + 83 RHEA）；组分命中最高频共组分：H⁺ 179/H₂O 134/O₂ 114/
  NAD(P)⁺/NAD(P)H 系 218/CO₂ 47（组分命中记录中共组分出现次数）。
- **与主会话数字对照**：147/159/12 净增/147⊂159 **全部一致**；
  本探针新增披露口径：组分 231/273、CN 182/209/273——主会话未给
  这些口径的数字；"201/298"未复现（182/209/273 无一等于 201），
  方法未披露不采信。
- **三方互证**：EAWAG 147 与尸检 L1"147 题 strict 记录"一致；
  EAWAG CN 182 与尸检 L0"引擎 lookup 命中 182/298"一致。
- **诚实边界**：本探针为静态覆盖估算（canonical 等值语义），不含
  编译可行性；§0.1 的编译/命中外推非本探针结论；探针脚本属草案
  证据，实施方开工时按 v3 W-V0 纪律独立复跑并登记命令/输出/哈希。

## 8. 待主会话裁定的决策点清单（≥3；裁定后本草案改定生效）

1. **底物匹配身份口径**（§1.1）：严格 159 vs CN 209/273；CN 命中
   不升 strict 的现行分层是否维持（或增设中间档走裁定）；
   "201/298"是否要求该会话披露方法后互证。
2. **donor 侧口径**（§1.3）：整串 159（与 EAWAG 现行语义一致、
   工程量小、净增 12）vs 组分 231（须共底物声明与角色判定设计、
   净增 84）——或分两档先整串后组分。
3. **RHEA 记录处置语义**（§4.2）：master_id 双向去重、RL 方向声明、
   8,502 通配行的结构化拒类目。
4. **授权核实前置门**（§2）：RHEA/enviPath recorded 直通消费许可
   的用户/主会话确认。
5. **伴行包取舍**（§6）：EAWAG 编译墙 v4 是否再攻；stereo 消解
   独立设计轮是否排期；语料资产轮（④）是否立项。
6. **mimo 送审**（§4.5）：身份判据请求是否按通道 A 自动送审。

## 9. 最终 hand-off 清单（实施方交付书必含）

实际 HEAD/commit/dirty、有限 diff、§1 口径冻结登记与 §2 授权核实
记录、W-V4.1 入口矩阵与字段适配层设计（含角色/方向/过滤声明）、
11 类负控族与正控、定向回归 + required PPV1+G01 + 父基线红绿对照、
corpus 侧编译失败直方图与 unsupported/unknown 诚实清单（编译成功率
未测面登记）、每阶段真实模型费用（实施期 0）、待复审问题。状态区分
`implementation_ready_for_review / review_changes_required /
ready_for_real_retest`。

> 执行摘要：v4 主杠杆=RHEA 主语料（37,100 行、18,550 反应×双向）
> 接入 recorded 直通供给——判据、分层、推断映射、哈希纪律全部沿用
> recorded_source 现行实现，不另写第二套；开工第一件事=冻结底物匹配
> 身份语义（严格 159 vs CN 209/273、整串 vs 组分 231，"201"未复现
> 不采信）+ 授权核实前置门。收益只按互证区间披露（严格净增 12/84、
> CN +50/+42，叠加 EAWAG 编译墙 54.4% 失败先验后一切数字标外推上界
> 不承诺）。验收主列不变 hit@1≥119/298（hit@5≥150 参考）；基线以
> chain10 终判分回填（当前 U=100 为 v2 基线）。v4 排在 chain10 复测
> 之后，两轮收益不混账；新批沿用 budget_guard 机器配置（60 帽/价/
  界/发送前原子预留）与同模型 1 logical/题；零金标入预测侧（底物
  检索只许 substrate_smiles）、冻结判据零触碰、不 push。

---

## §10 主会话定稿记录（2026-10-10，用户逐一弹窗通过）

状态更新：`draft_for_main_session_review` → **`decided_pending_chain10_baseline`**
（六决策点全部裁定；实施排序仍按 §5 顺序条款——chain10 复测出数回填
基线后开工；mimo r30 送审先行）。

| 决策点 | 用户裁定（2026-10-10） |
|---|---|
| ① 底物身份口径 | **CN 检索 + strict 编译核**（检索宽、判分严；CN 命中不升 strict 沿现行分层） |
| ② donor 侧粒度 | **组分级 + 共底物声明**（净增 84 供给面；其余组分诚实声明为共底物/条件参与物，编译按完整净产物集合核） |
| ③ RHEA 记录处置 | **双向保留 + 通配拒因**（LR/RL 双行保留为双方向候选分层引用；8,502 条 * 通配行 unsupported_wildcard_atom 拒因类目化） |
| ④ 语料授权 | **确认授权**（既有授权资产包同源消费，沿 manifest/哈希审计纪律，无新外发） |
| ⑤ 伴行包取舍 | **只做接线必需的最小编译支持**（编译墙深层再攻列 v4b 消融可见）；**stereo 设计轮独立排队**（mimo 评审后续审）；语料修复轮不纳入本轮 |
| ⑥ 身份判据评审 | **送 mimo r30**（通道 A 自动送审；判据冻结前把关） |

---

## §11 基线回填与实施授权（2026-10-10，用户"开干"指令）

状态：`decided_pending_chain10_baseline` → **`implementation_authorized /
scientific_target_pending`**（mimo r30 身份判据评审并行进行，其结论在
新登记冻结前收口；实施不自行点火真实批）。

**chain10 基线回填（v3 复测终判分，批根 s5b_298_hit50v3_20261010，
§9-4 通过、零 LLM 判分）**：
- 主口径 hit@1/3/5 = **73 / 100 / 105**；老口径 123 / 180 / 195
- 聚合诊断：U=106、H5=105、**L=1**（排序损失归零——W-V1 提交序修复
  精确兑现尸检反事实预测 73）
- 分桶：matched_strict 106、participant_coverage_partial 43、
  uncovered 149；**零失败**、恰 298 调用、18.16 CNY、60 帽内
- 目标判定：hit@1 73 < 119 ⇒ 未达；U=106 ⇒ 供给墙仍是唯一主要矛盾
  （本任务包的靶子）
- 差口：hit@1 距 119 差 46 题，全部须由供给端（本包 RHEA 接线 +
  组分级检索）长出；排序侧已无增益空间（L=1）
