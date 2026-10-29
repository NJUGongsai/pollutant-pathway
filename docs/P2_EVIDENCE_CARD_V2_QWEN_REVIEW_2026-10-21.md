# qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示

> **性质：** P2 证据卡 v2 离线实施复审（代 Codex 正链执行；**不冒充 Codex，
> 不替代 Codex 正链最终裁定权**）。复审请求：
> `docs/P2_EVIDENCE_CARD_V2_QWEN_REVIEW_REQUEST_2026-10-21.md`（Q1–Q7）。
> **题域：[298域] = RHEA 通用酶学 / 已见题（post-hoc）**；本卡全部数字为
> 合成样本/代理 tokenizer 离线读数，不外推真实 298 分布或科学收益。
> **纪律执行：** 只读主树（src/tests/既有 docs/证据原件零改动）；全部校验在
> 隔离克隆 `/tmp/qwen_p2_review_20261021/repo` 执行；未 push、未调模型/网络、
> 未跑 HPC/付费批、未读金标/题面/reference_graphs 内容/封存逐题 run/llm.env/
> 密钥。本复审新增证据：`docs/review_evidence/qwen_p2_evidence_card_v2_2026-10-21/`
> （含 REPRO_NOTES.txt、SHA256SUMS）。**本报告不构成付费批准。**

## 1. 总裁定

| 项 | 裁定 |
|---|---|
| 设计冻结是否仍成立 | **成立**。冻结设计 SHA-256 实测 `37d85958…c4f4`、设计终认 `48dfc599…56e7`，与请求/identity.json 一致；实施未触判据/池/检索/排序/评分/硬拒绝面 |
| 实施是否放行 | **放行（附条件 M1–M5，见 §4）**。代码忠实于冻结字段面；默认关闭；off 路径零漂移经本审独立复现成立；放行 ≠ 发车 |
| token 门 | **未通过（实测失败，停有效）**。标准 +16.62%、lean +15.62% > 13%；逐题 24/30 超限；**不接受按锚缩放投影（+12.35～12.73%）代替实测**。裁定理由与后续义务见 §3 |
| 是否具备交复审条件 | **具备**（证据可独立复现：token JSON 逐字节等值、off 探针值全等、2351 passed 复现） |
| 是否具备发车条件 | **不具备**。缺项见 §6；维持任务书「>13% ⇒ 停」停点在付费批之前 |
| 代码级 blocking 缺陷 | **无**。唯一 blocking 事项是 token 门本身（B1） |

**独立复现摘要**（全部在隔离克隆，`PYTHONPATH=<克隆>/src`；细节
`REPRO_NOTES.txt`）：patch `f3735bb0…17f6d` 只改 4 个白名单文件
（1180+/44−，`git apply --check` 通过）；patch 后 4 文件 SHA ==
identity.json == 实施树 `/tmp/dependingv43_p2`；off 探针基线 vs patch 后：
v1 prompt `fe9eaf…b0f4e`、v1 证据 `61cd96a9…8960`、底物卡 `18a62e52…75d3`、
A 载荷 `c2526a7f…799d`、B 载荷 `b8f66ed9…981e`、system prompt、summary 键集
**全等**，identity 归一 diff 仅 code_identity 聚合 + 3 个白名单源文件；
v2 prompt 实测 `89311fdb…0f37`；目标批 88 passed；全量 not-slow
**2351 passed / 16 deselected**（与实施方 r2 一致）；token 双档 JSON 与实施方
证据**逐字节等值**（SHA 相同）。

> **注（2026-10-21 契约同步）：** 上段 `v2 prompt 实测 89311fdb…0f37` 是本报告复现时的
> **历史值**；该旧 SHA 已被 chemfix 取代（`89311fdb…0f37` → E 轮 `e2aa2bbf…3a5a` → 最终
> `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`）。本报告的历史结论、
> 数字与证据原样保留，不因新 prompt 回写；新 prompt 下需另行复核（不在本报告范围）。

## 2. Q1–Q7 逐项

### Q1 字段裁剪忠实性 — **sound**

逐项对照设计 §一表与任务书 §三（证据：impl.patch `candidate_evidence.py`
追加段 + `test_v2_candidate_fields_exact` / `test_v2_forbidden_content_absent`
/ `test_v2_participants_preserve_known_and_unknown_coefficients` /
`test_v2_payload_keeps_top_level_ref_and_omits_card_source`）：

- 删：Gasteiger、`molecular_formula`/`element_counts`、FG `smarts`/`matches`、
  `coefficient_status`、`alignment_quality` 非 status 六键、卡内 `source` 四件
  （禁词断言覆盖 `source_kind`/`origin_group_key`/`alignment_ref`，且卡文本
  不含 transformation_ref 值）。未见偷删真实事实、未见偷留被裁字段。
- 留：`participants` 保真紧凑——遍历全部参与物、行不隐藏、不补假条目；
  已知系数如实 `str(coefficient)`、缺失才 `unknown`（测试断言 primary/
  principal `=="1"`、coproduct `=="unknown"` 且行在位）；
  `requirements` 缺席=字面 `unknown`、在位=直读完整列表（v1 helper
  `_conditions_and_scope` 原样复用，键面恰为三键）；`participant_list_status`
  必留（缺省 `partial`）、`step_scope` 合并一行（缺省 `net_reaction`）；
  顶层 `transformation_ref` 保留（非盲臂，与 S1 裁定一致）。
- 加：`functional_group_delta` / `product_delta` 均 `scope=principal_product`
  （常量 `PARTICIPANT_ROLE_PRINCIPAL_PRODUCT="principal_product"`，hypothesis.py:84）。
- v1 函数/常量/表零修改：candidate_evidence.py 仅加一行 import + 文件尾追加；
  off 路径逐字节等价由探针独立证实（见 Q2）。

### Q2 实现正确性与 off 零漂移 — **sound**

- **独立复现成立**（本审自跑基线/patch 后双侧探针）：A/B 用户载荷 SHA、
  v1 证据/底物卡 SHA、system prompt SHA、summary 键集、`has_v2_summary_key`
  全等；identity 归一 diff 仅 code_identity 聚合 + 3 个白名单源文件哈希
  （本审同树对比连 `assets_root` 差异都没有，比实施方跨树对比更紧）。
  无 v2 键泄漏到旧 summary/strategy/payload/prediction。
- v2 A 臂用户 JSON 与 v1 无证据路径同字节：`test_v2_arm_a_user_json_byte_
  compatible_with_v1`（含不传 schema_version 的旧调用形态）。
- 两臂共享 v2 prompt：`test_v2_both_arms_share_prompt_and_identity` 断言
  A/B 两 run 的 `seen_system_prompts == [proposals_system_prompt("v2")]`。
- v2 identity 登记 schema/descriptor/RDKit/版本（`_v2_identity_fields`）；
  resume 三重 fail-closed：saved 版本非法 → `evidence_card_version_corrupt`；
  版本不符 → `evidence_card_version_mismatch`（有测试）；schema/descriptor/
  RDKit 漂移 → 当前值重算后 `check_resume_identity` 拒。
- 开关语义与任务书 §四表一致；非法版本值 fail-closed（`_resolve_evidence_
  card_version` 抛结构化 PPV1RunError，不静默落回 v1）；
  `proposals_system_prompt` 同样 fail-closed。
- v1 prompt 构造性不变：`_PROMPT_STATIC_4_PREFIX + _PROMPT_EVIDENCE_NOTES_V1
  == _PROMPT_STATIC_4`（本审实测 True），v2 仅替换证据 notes 段。

### Q3 确定性锚覆盖 — **clarify**（一处缺测试，行为已验证正确）

设计 §四.3 / 任务书 §六 九锚对照：锚1 质子化对（羧酸/羧酸根、伯仲叔胺/铵、
酰胺不误标、且断言 v1 路径行为不变）✓；锚2 无变化/单得失/多命中（甘油
n_hits=3）/跨类重叠 ✓；锚3 主副产物次序置换不改 delta ✓；锚4 prepared=None
⇒ participants=unknown 且图级 delta 仍可算、未知系数不伪造 ✓；锚5 **前半**
（add_atom spec 照常算 delta）✓、**后半（participant 缺 `state_ref` ⇒ 该行
smiles=`unknown`）无 committed 测试**——本审 ad-hoc 探针
（`anchor5_adhoc_probe.py`）验证行为正确，属覆盖缺口非行为缺陷（→M1）；
锚6 解析失败（render_ok=false、delta=unknown）vs 真实零命中（甲烷：空集合
非 unknown）✓；锚7 10 片段 n_hits=10、无 matches/smarts 键 ✓；锚8 双跑字节
一致 + spec deepcopy 不变 ✓；锚9 v1/v2 身份、off 无新键 ✓。

### Q4 化学语义（规则级） — **sound**（规则级限度内）

- 质子化容忍 SMARTS：`[OX2H1,OX1-]` 把羧酸/羧酸根归同类；胺类
  `[$([NX3;Hn]),$([NX4+;Hn+1])]` 双表示把中性胺/铵归同类；`!$(NC=[OX1])`
  酰胺排除沿用（测试：`CC(=O)N` 不标 amine_primary、`CC(=O)NCC` 不标
  amine_secondary）。合成探针验证正确。
- FG delta 类集合语义与「主产物 scope」自洽：gained/lost=类集合差（非命中数
  变化）、跨类重叠独立（乙酰乙酸 ketone+carboxylic_acid 并存）、只读
  `spec["product_smiles"]`（编译器指定主产物，不重选）、多组分 `.` ⇒ 整字段
  unknown（保守）；prompt v2 段明示「not the complete product set, coproducts,
  stoichiometry, mechanism, or oxidation proof」——无夸大。
- 部分参与物/未知系数时仍给图级 delta：与冻结设计「限定图级差值或 unknown」
  一致，可接受。
- `unknown` 语义：prompt 明示「not negative evidence … not by itself a reason
  to abstain」；负证据（requirement_missing）未实施 ✓。
- 限度声明：以上为**规则级**判断；v2 字段在真实结构上的化学正确性复审
  **未取得**（实施报告 §7 已如实登记），类标签不得当化学结论（沿 R4 纪律）。

### Q5 碳氧化态定义与许可范围 — **sound**

- 定义 `C_ox=(q−H+2O+X)/C` 是标准甲酰基式平均碳氧化态；数值锚独立复核：
  乙醇→乙醛 Δ=+1.0、乙醇→乙酸 Δ=+2.0、乙酸根→乙酸根 Δ=0.0（电荷入式）、
  含 N 变换 ⇒ unknown 但 formula 差仍如实给（测试断言与本审手算一致）。
- 许可范围诚实：仅两侧含 C 且元素 ⊆ {C,H,O,F,Cl,Br,I} 才计算，N/S/P/金属
  一律 unknown（不猜）；prompt 与字段注释均声明非逐原子/机制/氧化还原配平
  证明。应收窄处已收窄，无应放宽而未放宽之处。
- 非阻断注：过氧化物/O–O 键在「O=−2 约定」下按约定值计（甲酰基式约定的
  固有属性），prompt 已用「under the convention H=+1, O=-2, halogen=-1」如实
  描述该度量；建议冻结文本可加一句 peroxide 脚注（§5-C3，措辞级）。

### Q6 token 离线门 — **blocking（对发车）；门未通过，停有效**

详见 §3 专项裁定。要点：实测标准 +16.62%、lean +15.62% > 13%（本审逐字节
复现）；按任务书 §8.1「逐题与批合计 ≤13%」双口径，逐题 24/30 超限（全部
非空池题，最小 13.4772%）；投影不是实测；样本校准方法部分可辩护但有三处
缺陷（§3.1）。**具备交复审条件：是。具备发车条件：否。**

### Q7 剩余前置是否列全 — **sound（两条措辞级补充）**

报告 §7 八行覆盖请求所列全部前置（T-I 模型选择、最终 tokenizer 复测、真实
池形状复测、P2 预注册、CC 付费签字、化学评审、批级冻结/worker/orchestrator/
HPC、实施审）。补充建议：C1 把「token 门以最终 tokenizer + 真实池形状**实测
通过**（非投影）」单列为发车硬前置行（现分散在两行的说明列）；C2 注明
Codex 正链额度恢复后对本代审的复核确认（请求头部已声明，报告宜呼应）。

## 3. token 门专项裁定（CC 必核 3/4）

### 3.1 裁定：**门未通过（要求停）**；不接受按锚缩放投影

1. **实测失败是硬事实**：批合计 +16.6216%（standard）/ +15.6213%（lean），
   门限 13%（本审逐字节复现，两档 `pass=false`、exit 3）。按 §8.1 逐题口径
   同样失败：24/30 题 >13%（凡有 ≥1 候选的题全部超限，最小 13.4772%；压力题
   +201.55% 另计）。设计 §五红线「token 离线门硬约束」、任务书 §七「任一
   超 13% ⇒ 停」——无裁量空间。
2. **投影不可采信的三条理由**：
   - **锚差不可分解**：样本 v1 锚 +33.95%（Qwen3.5-2B 代理 tokenizer）vs
     已公布 +26%（chain14 真实批，GLM-5.3-Flash tokenizer）。差值混合了
     「样本形状」与「tokenizer 家族」两种效应，现有数据无法归因分解；按
     26/33.95 等比缩放隐含「tokenizer 效应对 v1/v2 增量同比例」的未证假设。
   - **投影本身就在门线上**（12.35–12.73% vs 13%），落在样本构造噪声内，
     即便假设成立也不构成稳健通过。
   - **纪律**：实施报告 §6.3.4 自判「不得用投影代替实测」，本审维持；
     合成绿不得写成真实可发车，投影同理。
3. **失败性质判定**：这是「**实测未过、归因未分解**」——既不能据此宣布
   「设计门（13% 目标）不可达」（最终 tokenizer 下可能不同），也不能接受为
   「样本校准伪失败」（逐题口径下任何非空池题都超线，与批合计形状无关）。
   是否设计门失败，**留待最终 tokenizer + 真实池形状实测后判定**；在此之前
   unknown 保持 unknown。
4. **样本校准方法（Q6a）部分可辩护**：空池占比对齐已公布锚（6/30≈20.1%）、
   压力题分离且明示不混入批门、lean/standard 双档敏感性、构造全披露——方法
   透明。但三处缺陷须登记（→M4）：
   - 任务书 §七样本规格写明「**每题 8–30 个候选**」，实际代表样本为
     0–3 候选/题（平均 1.07）；偏差方向偏松（候选越少增量越低），报告 §8
     未把此偏差登记为偏差。注意：**即便如此门仍未过**——若按任务书原文
     样本规格计量，批合计将处于压力题量级（+201%），失败更重。该偏差未
     翻转任何结论，属披露完备性问题。
   - 「非空池以 1 候选为主」无已公布出处：已发表数据只支持 60 空池（20.1%）
     与 rank 2–5/>5 分布（`T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` §3），
     完整池大小分布未见公布 ⇒ 真实池形状 unknown。
   - gate JSON 的 `max_delta_pct` 实为批合计而非逐题最大值，命名易误读
     （→M3）。
5. **停点与复测义务（若 CC 决定继续推进）**：
   - **硬前置（不可豁免，Q6d）**：T-I 模型选定后，用最终模型 tokenizer 按
     同口径（system+user、首发固定载荷、tokenizer 文件 SHA 登记）复测；
     并以真实池形状复测——后者需离线装配冻结池输入做 tokenization（零模型
     调用、零判分、零金标），其数据处置属「读题面输入」层面，**执行方式须
     CC 另行授权**，不由本卡红线自动豁免。
   - 复测仍 >13% ⇒ 判「设计门失败」，回到 CC：重开设计（裁字段）或调整
     token 预算/门限（判据变更权在 CC/老师，不在实施/审核侧）。
   - 复测 ≤13% ⇒ 门过，仍须 §6 其余前置齐备才可议发车。
6. **最小压缩方向（Q6c，不删真实事实、不改判据/池/排序/评分）**：
   - **格式级（实施侧可做，改后必须重测+重登记 v2 载荷身份）**：仅 v2 B 臂
     证据渲染改紧凑 JSON 分隔符（`,`/`:` 去空格）。不删任何事实；v1 与 A 臂
     字节兼容约束不受影响。压缩幅度 unknown，**不承诺过门**。
   - **语义级（超出实施裁量，归 CC/设计方）**：requirements 行压缩（现保留
     完整列表，报告 §8.5 已披露）、字段名/枚举值缩短——均触碰冻结字段表，
     须设计方裁定，不属本审可批。
   - 明确不可用手段：删参与物行/系数/真实事实（任务书排障表明令禁止）。

### 3.2 30 候选压力题（CC 必核 4）

不影响「实施放行」判断；对发车是**风险披露项**：(i) 大池题增量 +201.55%
（v2 B vs v2 A）说明门对池形状高度敏感，真实池若大池占比高，门恶化，压力题
读数是下界不是上界；(ii) 相对 v1 B −20.34% 只说明「同池下 v2 卡比 v1 卡省」，
是事实陈述，**不得当收益、不得当过门理由**（门口径是 v2 B vs v2 A，冻结于
任务书 §七）；(iii) 压力题与批门分离符合样本设计披露，但见 §3.1.4——任务书
原文样本规格本就含大池题，分离口径不能反向论证门可过。

## 4. 必须修正项与最小回修清单（仅请求范围内）

**Blocking（B 级，对发车/冻结）**：

- **B1** token 门未通过：维持「停在付费批之前」；任何发车路径先满足 §3.1.5
  复测义务或 CC 设计变更裁定。此为门裁定，非代码缺陷；代码侧无 blocking。

**最小回修（M 级，冻结文本/预注册前完成；全部不改行为判据）**：

| # | 内容 | 依据 |
|---|---|---|
| M1 | 补锚 5 第二分支 committed 测试：participant 缺 `state_ref` ⇒ 该行 smiles=`unknown`（行为已由本审 ad-hoc 验证正确，只缺测试） | 任务书 §六「必须逐项有测试」 |
| M2 | 实施方归档 `off_path_baseline.json`/`off_path_after.json` 原件（请求 §4 引用但未入证据目录；本审复跑件 `off_path_*_qwen.json` 已作等价证据入 qwen 目录） | 证据保存完整性 |
| M3 | 报告 §6 明示逐题超限（24/30 题 >13%，最小非空 13.4772%）；`token_measure.py` gate 字段 `max_delta_pct` 改名或注明为批合计 | 任务书 §8.1 双口径披露 |
| M4 | 报告 §8 登记样本形状对任务书 §七「每题 8–30 候选」规格的偏差及校准理由（本审已代为披露于 §3.1.4，实施方报告应自登记） | 偏差登记纪律 |
| M5 | `tests/test_p2_evidence_card_v2.py` 文件尾补换行符 | cosmetic |

**非阻断澄清（C 级，可随冻结文本落）**：C1/C2 见 Q7；C3 碳氧化态约定的
peroxide 脚注（Q5）；C4 run1 失败日志（controlled-vocab `principal_product`
字面量）与 r2 全绿的修复链条已由本审核实（最终 patch 用常量
`PARTICIPANT_ROLE_PRINCIPAL_PRODUCT`，未新增词表登记，未改
`test_controlled_vocab_ci.py`），建议在报告 §4 注明两日志对应不同 patch 中间态。

## 5. grep 意外预览披露裁定（CC 必核 5）

**接受该披露，无需追加处置（登记已完成）**。核验：环己烷 SMILES
（`C1CCCCC1`）在 `token_measure.py`、`off_path_probe.py`、`impl.patch` 中出现
次数为 **0**，即未污染任何样本/实现/数字；实施方声明未继续使用、未读该文件
其余内容，且已双处登记（报告 §8.8、请求头部）。环己烷为常见简单分子，单条
substrate SMILES 不构成金标/答案级信息。建议（非阻断）：后续在 reports/ 等
敏感目录检索时用 `grep -l`/计数模式避免内容预览；是否在污染台账补一条由 CC 定。

## 6. P2「交付费批」前置裁定（CC 必核 6）

**不具备交付费批条件。** 本审放行的是离线实施质量，不是发车，更不是付费
批准。缺项（全部为硬前置）：

1. token 门实测通过（最终 tokenizer + 真实池形状；B1/§3.1.5）；
2. T-I 模型选择（P2 单变量要求同模型；T-I 暂停中）；
3. P2 独立预注册（298 配对、hit@1/strict/rank>1/分族、novel 首选占比口径、
   strict 净失 ≤−3 停点继承、费用账含反馈轮/重试/失败 unknown 计数）——
   设计 §二.3「未填不得发车」；
4. v2 字段语义/质子化容忍 SMARTS/碳氧化态约定的化学复审（mimo 场景 1 随
   冻结；R4 是 P0b 链，不覆盖 P2）；
5. 批级冻结/worker/orchestrator/HPC 发车工具（本卡明确未接）；
6. CC 付费签字（no-cap 费用=CC 拍板，不代签）；
7. Codex 正链复核确认（本代审不替代正链最终裁定权）。

## 7. unknown / 本审核未覆盖

- 真实 298 池形状分布（「非空池以 1 候选为主」无已公布出处）——unknown；
- T-I 最终模型 tokenizer 行为——未定，无法测；
- v1 锚差（+33.95% vs +26%）的样本/tokenizer 归因分解——不可得；
- v2 字段在真实结构上的化学正确性——属化学评审链，本卡未覆盖（规则级为限）；
- chain14 +26% 锚：仅核对 `CHAIN14_EVIDENCE_AB_RESULT_2026-10-16.md` 原文
  行，未复核该批原始 usage 账；
- 实施方 pytest/token 调用的确切命令行（日志无头部命令）——以文件哈希与
  结果逐字节吻合替代验证；
- 本审首轮全量的 2 个 batch 并发时序失败（`test_batch_dev`）单独重跑通过
  （122s），归为负载抖动；未做并发敏感性穷尽排查（同哈希代码在实施方与本审
  环境对齐后均全绿）；
- 环境注记：conda env 存在 editable 安装指向主树 src
  （`__editable__.pathway_v43-0.1.0.pth`），任何隔离复跑必须
  `PYTHONPATH=<隔离树>/src`，否则静默导入主树（本审首轮即因此收集失败；
  该失败同时反证主树 src 无 v2 常量、未被改动）。

## 8. 新问题分级

- **P0：无。**
- **P1：M3、M4**（披露完备性：逐题超限未在报告正文显式；样本规格偏差未
  登记为偏差）——不改变「停」结论，但影响 CC 决策信息面，应在下一轮文本
  修正中闭合。
- **P2：M1、M2、M5、C1–C4**（验收覆盖缺口一件、证据归档缺口一件、措辞/
  cosmetic 若干）。

## 9. Provenance 与环境

- 审核人：qwen3.8max（代 Codex 复审，按 CC 2026-10-21 指示；不冒充 Codex/CC；
  结论采信到与源码/程序证据互证为止；Codex 正链最终裁定权不变）。
- 主树 HEAD（实测）：`11aeeafded1b41185f24de49767933709aad49db`（=基线，
  工作树中 `docs/T_H_P0B_D6_IMPL_2026-10-20.md` 有一处非本审产生的未提交
  修改，本审未触碰）。
- 身份实测：设计 `37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4`；
  终认 `48dfc59931c383e640c9753eb4998ec0b25c41648c79b9c489bf835f754f56e7`；
  patch `f3735bb07f24143150369db76d02fe2c45ff3958461d20ed4453758bfbd17f6d`；
  tokenizer 文件 `87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4`。
- 环境：macOS arm64；Python 3.11.16（`/Users/cc/miniconda3/envs/depending43`）；
  tokenizers 0.22.2；RDKit 2026.03.6。隔离克隆 `/tmp/qwen_p2_review_20261021/repo`
  （用后可弃）；本审新增文件仅本报告与
  `docs/review_evidence/qwen_p2_evidence_card_v2_2026-10-21/`（11 件，含
  SHA256SUMS）。
- 未做：push/合并、模型/网络调用、HPC/付费批、金标/题面/reference_graphs/
  封存 run/llm.env/密钥读取、主树 src/tests/既有 docs/证据原件修改。
