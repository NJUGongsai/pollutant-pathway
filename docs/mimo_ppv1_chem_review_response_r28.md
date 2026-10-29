# mimo 化学评审回应 r28（2026-10-10）

- 通道：opencode run -m opencode/mimo-v2.6-flash-free（免费档，通道 A；本回应经主会话转发落盘）
- 请求：docs/mimo_ppv1_chem_review_request_r28.md（三判断面：V4 coproduct_ignore_tier 裁定选项 / r27 条款项采纳核对 / stereo 消解型设计复审）
- 只读 provenance：评审员以读取工具核对源码/文档，无 shell 执行权限；其执行类断言均自带"待执行验证"标注
- 原始流：docs/review_evidence/ppv1_r28_mimo_2026-10-10/raw.txt（终端控制字符已清理；证据目录含 header/请求/原始流）
- 采信原则：与程序证据互证为准，通道独立性不做背书

---


我先核对仓库源码（只读），再按 A/B/C/D/E 逐条作答。
✱ Glob "src/pathway_v43/pollutant/*.py" 32 matches
✱ Glob "tests/test_ppv1_s5b_hit50_v3_*.py" 4 matches
→ Read src/pathway_v43/pollutant/s5b_scoring.py 
✱ Grep "_pair_exports_to_samples|trigger_equivalence|root_identity_fallback|bases_by_graph" in . · 100 matches
→ Read src/pathway_v43/pollutant/evaluation.py [offset=1840, limit=140]
→ Read src/pathway_v43/pollutant/evaluation.py [offset=100, limit=200]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=140, offset=2390]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=130, offset=2185]
→ Read tests/test_ppv1_s5b_hit50_v3_wv6.py 
✱ Grep "stereo_edit_unsupported|stereo" in src/pathway_v43/pollutant · 80 matches
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=260, offset=150]
✱ Grep "coproduct" in src/pathway_v43 · 60 matches
✱ Grep "def execute_edits|def strict_identity_of" in src · 2 matches
→ Read src/pathway_v43/services/atom_tool.py [limit=120, offset=402]
✱ Grep "matched_participant_coverage_partial|multiset|participant" in src/pathway_v43/pollutant/evaluation.py · 18 matches
→ Read src/pathway_v43/pollutant/evaluation.py [limit=300, offset=730]
✱ Grep "含碳|carbon|无机|inorganic|碳" in src/pathway_v43/pollutant/reference_graph.py · 2 matches
✱ Grep "coproduct_ignore_tier" in docs · 11 matches
→ Read docs/mimo_ppv1_chem_review_response_r27.md 
→ Read src/pathway_v43/pollutant/s5b_compiler.py [limit=190, offset=695]
→ Read src/pathway_v43/pollutant/chemstate.py [limit=60, offset=905]
✱ Grep "def cn_identity|RemoveStereochemistry|isomeric" in src/pathway_v43/domain/identity.py · 2 matches
→ Read src/pathway_v43/domain/identity.py [limit=70, offset=20]
✱ Grep "def _identity_key" in src/pathway_v43/pollutant/chemstate.py · 1 match
✱ Grep "def validate_reference_graph|participants|edges" in src/pathway_v43/pollutant/reference_graph.py · 17 matches
✱ Grep "含碳组分|无机.{0,6}被剥|剥离" in . · 30 matches
✱ Grep "dedup|去重|seen_identities|identity_seen" in src/pathway_v43/pollutant · 30 matches
→ Read src/pathway_v43/pollutant/real_model.py [limit=80, offset=205]
→ Read src/pathway_v43/pollutant/evaluation.py [limit=75, offset=2110]
✱ Grep "def _manifest_qid_map|def _export_qid_map" in src/pathway_v43/pollutant/evaluation.py · 2 matches
→ Read src/pathway_v43/pollutant/evaluation.py [limit=40, offset=1805]
✱ Grep "state_id\s*=|def build_chemical_state" in src/pathway_v43/pollutant/chemstate.py · 4 matches
# mimo r28 化学评审回应（直接输出稿，未改任何文件）

**执行边界声明（先行）**：本轮只用读取类工具（glob/grep/read）核对了 `src/pathway_v43/pollutant/{evaluation,s5b_scoring,s5b_compiler,real_model,chemstate,reference_graph,production}.py`、`src/pathway_v43/services/atom_tool.py`、`src/pathway_v43/domain/identity.py`、`tests/test_ppv1_s5b_hit50_v3_wv6.py`、`docs/mimo_ppv1_chem_review_response_r27.md`；**未运行任何测试/脚本**，行为类断言一律标"待执行验证"；引用行号均为本轮实读；未访问金标/题面/gitignored 目录。聚合数字（partial 40、38/40、25/40 等）按请求声明采信，无法逐题核验（金标纪律），凡依赖逐题形态的估计均标"聚合级推断"。

---

## A. 判据含义

**A1：结论——这是"参考图声明语义 vs 判分比较语义"的口径错配，不是模型错，但 partial 桶本身的归类是诚实正确的。**
机理：参考边按提取口径系统性剥除无机/辅因子（P3；`docs/S5B_HIT50_V2_POSTMORTEM_2026-10-09.md:136` 亦记此观察），事件协议却要求完整产物集（`s5b_compiler.py:830-848` 主产物+coproducts 全入参与物；`reference_graph.py:403-409` 参考边 participants 也声明为非空完整清单——**两边都自称"完整集合"，含义却不同**）。判分侧严格身份（`chemstate.py:913-929`）+ 集合相等（`evaluation.py:975-981` exact/superset/partial_subset 三分类，:992-993 落 partial）在这种错配下把"按自己协议写全"判成 partial——**保守方向正确**（partial 名字本身如实说的是"覆盖不精确"，不是"化学错"），错的是把 partial 读成模型错误、并用它当主口径非命中。
可落文字：规则文字补一句——"`matched_participant_coverage_partial` 语义 = 候选与参考声明的**集合比较**结果，非化学正确性判定；其成因含参考提取口径（剥除无机/辅因子）与事件完整产物集语义的**声明口径差**，解读与报告不得单义归因模型。"
误导风险：若忽略档不上，主口径 hit@K 实际测的是"模型对提取口径的服从度"而非净反应预测力——程序上诚实，化学上误导（报告层）。

**A2：结论——白名单内部分子的"真实共产物 vs 活性组分"边界必须按方向和元素可追溯性划，不能按名单一锅端。**
逐类：
- **H₂O**：水解/水合是**反应物**，脱水/缩合/单加氧酶旁产物才是**产物**——同一名单项方向语义相反。模型如实写"底物 + H₂O → 产物"（本域最主流化学）会落**反应物侧超集** → partial。若忽略档只管产物侧，水解类永久 partial（忽略档修了一半错配）。建议：**反应物侧仅特例 H₂O**（溶剂活度 ≈1，净反应簿记噪音），其余反应物侧无机（O₂/NADH/NH₃/Pi）一律不豁免（共底物=机制主张）。
- **CO₂/HCO₃⁻/CO₃²⁻**：脱羧真实产物，白名单（名单缺 CO₃²⁻，补）；碳可追溯前提（底物须含碳——必要非充分）。
- **Cl⁻/Br⁻/F⁻**：脱卤真实离去基团，白名单+卤素可追溯；**补 I⁻**（碘代污染物如碘帕醇/泛影酸是本域经典难降解类，碘离子释放是其标志性转化，名单漏了）。含氟有机磷（沙林类/DEF）水解也放 F⁻。
- **NH₃/NH₄⁺**：脱氨/腈酶真实产物，白名单+N 可追溯；作**反应物**（转氨/同化）不豁免。
- **Pi/PPi**：磷酸酶/磷酸三酯酶真实产物，白名单+P 可追溯；作反应物（激酶）不豁免。**P 可追溯前提在此有强判别力**（见 A6 的 PPi 例）。
- **SO₄²⁻/HS⁻**：硫酸酯酶/含硫污染物真实产物，白名单+S 可追溯。
- **O₂**：**建议移出"产物侧"白名单**——O₂ 作产物（释氧）在本域几乎必是方向错（氧化酶/加氧酶里 O₂ 是共底物，在反应物侧）。产物侧白名单放 O₂ = 白送方向错一条豁免。
可落文字：白名单逐项带**元素可追溯前提**（该杂原子须出现在该事件声明的反应物侧），且白名单**只作用于产物侧**（反应物侧仅 H₂O 特例）。
误导风险：无追溯前提时，"无 Cl 底物写 Cl⁻ 产物"这类**元素不守恒的假共产物**会被洗成 strict——判据二（计量）本就不比较（`evaluation.py:884-887` 系数仅披露），忽略档就成了这类错误唯一藏身处。

**A3：结论——F⁻ 有条件进（带追溯）；CN⁻、SCN⁻ 一律出白名单；NO₂⁻/NO₃⁻ 带 N 追溯进、但须单列披露。**
理由：CN⁻/SCN⁻ **含碳**——它们的释放是有机骨架 C–N/C–S 键断裂的实质性主张，不是簿记噪音，忽略它们等于抹掉一类真化学（且 CN⁻ 是共底物/抑制剂语义高发项，写在产物侧本身就是可疑信号）；F⁻ 是正常离去基团（有 C–F 才放行）。NO₂⁻/NO₃⁻ 承载 N 的**氧化态信息**（亚硝化/硝化/厌氧氨氧化路径分叉点），可豁免但必须在机读披露里单列该题曾被豁免的无机种类，保住路径可读性。

**A4：结论——T2 元素级档我会否决：存在必须计分的"不含碳组分"，且 T2 会系统性抹掉机制信息。**
反例（元素级规则"仅含 O/N/P/S/卤素/H、不带碳"全部命中）：**H₂O₂**（氧化酶 vs 加氧酶的分叉信号）、**NH₂OH**（硝化/羟胺路径）、**N₂H₄**、**NO**（请求自己提到的活性边界）。这些是**机制上可区分路径的产物**，超集方向放过它们 = 掩盖"模型把氧化酶写成加氧酶"这类类型错。超集方向的"掩盖共底物当产物"具体形态就是 O₂（见 A2）。T2 比 T1 宽出的部分没有换来覆盖率上的必要性（T1 已覆盖真实高发项），换来的是误放面——不值。

**A5：结论——不对称在化学上站得住，支持保持（子集仍 partial）；但规则文字须把"多重集"改成与实现一致的"集合"。**
机理：参考声明的产物是**必须出现**的（少写=净反应不完整，真错误）；多写白名单无机是"写全了"（口径差）。本批 2/40 子集迹象恰好证明 partial 桶里混着真模型错误（见 B3），更支持方向特异的豁免。**事实订正（P2 级）**：请求 P1 写"参与物**多重集**严格相等"，实现是**集合**相等（`evaluation.py:975-981` `reactants == from_states and products == to_states`，两侧均为 state_ref/state_id 集合；状态 ID 按严格身份内容寻址 `chemstate.py:705`，重复组分天然塌缩）。两口径在"同组分写两次"上行为不同，规则文字必须二选一写死。

**A6：结论——辅因子（AMP/ADP/ATP/NAD(P)(H)/FAD/FMN/CoA/THF）不入任何忽略档，正确，维持 partial；会被误伤的"辅因子片段"情形存在，且追溯前提恰好能救。**
机理：辅因子书写是**机制主张**（哪个供体/受体、ATP 还是 GTP），参考剥除它们是提取口径差（同 A1），但它们含碳/有机骨架，任何"无碳"规则都碰不到它们——留在 partial 是对的，它们是目前判分里少数还有效的机制信息压力。误伤例：**酰基-CoA 合成酶型**（底物+CoA+ATP → 酰基-CoA+**AMP+PPi**）——忠实写全者 partial（正确）；但"半套簿记"（丢掉 ATP/CoA 只留 PPi 产物）在**裸 T1** 下 PPi 被豁免 → 洗成 strict（假命中）；加了 P 可追溯前提（反应物侧无 P ⇒ PPi 不豁免）则恒 partial（正确）。泛醌→泛醇这类**整体辅基氧化还原**是有机组分，白名单碰不到，不会被误伤；真正要防的是 PPi/AMP 这类片段。**T3（计量级）我不同意现在采纳**：它要求判分消费参考图并未可靠声明的系数事实（`evaluation.py:884-887` 明示"系数仅披露不比较"），与"库记录无系数 ⇒ unknown"现状正面冲突；追溯前提就是 T3 的可实现最小子集。

---

## B. 风险

**B1：结论——最大单点风险 = "元素不可追溯的白名单无机"把化学上不可能的计量洗成 strict；裸 T1 下我估计 flip 20–35/40、其中假命中 0–5 题量级（聚合级推断，待执行验证）。**
理由：partial 桶定义保证了 40 题全部已让参考声明节点严格命中（`evaluation.py:911-937` 必要节点缺口不进 partial 分支），主形态"参考 1 产物 vs 事件 2 产物"正是裸 T1 的可豁免形；38 超集迹象里扣掉反应物侧也有无机/有机多写者即为上界来源。假命中集中在三类：①产物侧白名单无机无元素来源（判据二不查守恒，见 A2/A4）；②O₂ 在产物侧被豁免（方向错）；③若忽略档被做成两侧对称，共底物误置。加追溯前提+产物侧限定+O₂ 移出后，flip 区间收窄（我预期 15–30），假命中面基本封死。缺的证据：40 题逐题"多出组分的元素 vs 底物元素"计数（聚合计数代理不含此轴）。

**B2：结论——T0 的激励是坏的但不是灾难：它教会"少写共产物"，同时把主口径变成对提取口径的服从度测试。**
若判分数字回流供给侧（提示词/选型），T0 下最便宜的提分动作就是不写共产物——恰好迎合参考口径，**指标改善与化学改善脱钩**；更实质的损失是事件完整产物集是后续机制评审、守恒核查、端点判定的输入（`native_result.py:22` coproduct 角色、`runflow.py:597` coproduct followup 都消费它），把它教薄了整条审计链变脆。所以 T0 只能当默认兜底，不能当终态；长线解法在参考侧（见 C1 的替代方案）。

**B3：结论——2/40 子集迹象是"partial=口径错配"论点的反例素材，支持方向特异豁免，反对任何把 partial 整体读成错配的叙述。**
子集（少写声明产物）在此协议下就是真错误，它的存在证明模型不是一律"写全党"，38 超集的错配论点不被推翻但也拿不到"全体豁免"的授权。

**B4：结论——同题双形态（1 产物/2 产物事件并存）在 T0 下已是"看排序中"，T1 会把命中从"存在性"稳定推向"位次"敏感：hit@5 存在性更稳，hit@1 更依赖两事件的提交时序。**
`evaluation.py:942-953` 逐事件比较、`s5b_scoring.py:521-543` 按 `(created_at, event_id)` 定序——T1 后 2 产物事件也变 strict，若它排在 1 产物事件前面，rank 前移、**hit@1 增量可能主要来自冗余事件的位次前移而非新覆盖能力**。可落文字：首个生效批必须**单列"因忽略档新增的 strict 命中里、同题原本已有 strict 事件"的题数**（纯位次效应 vs 新覆盖效应分离披露）。

---

## C. 预注册路径

**C1：结论——落地形态成立，但字段粒度必须从"档位枚举"升到"档位+白名单 cn 身份版本哈希+方向策略+追溯开关"四元组，否则档位定义漂移不可避免。**
要点：
1. **白名单匹配必须走 cn 身份层**（`identity.py:41-55` 已有电荷归一+stereo 盲化，可直接覆盖"及其质子化变体"），而不是裸 SMILES 枚举；无机离子在 Uncharger 下的往返稳定性须逐条验证（**待执行验证**）。
2. **豁免只作用于"事件超出声明的差集"**（extras = 事件组分 − 该边声明组分，再对 extras 按白名单过滤），天然对参考图未来版本（若某边补声明了水/卤离子）中性——不回写、不反向要求。
3. **角色不可作为豁免依据**（`production.py:229-231` coproduct 角色是模型可写的）；豁免判据只能是化学身份，好在有机组分永不豁免已封死角色洗分通道。
4. **事后选择防线**：该档是在看过 partial 40 形态后提出的，属教科书式 post-hoc——首个生效批的数字必须以"敏感性表 + post-hoc 标签"并列披露，**不得回填/覆盖 T0 主口径 headline**（与 P4 旧线只读一致）。
5. 长线替代方案（更干净，建议并行登记）：让参考图提取对每边显式声明 `omitted_coproduct_scope`（剥了什么），判分只豁免**参考自己声明剥掉的**那类——根治 A1 错配，白名单漂移风险整个消失。

**C2：结论——同意 T0 兜底；"未裁定期双口径并列"我不同意作为默认。**
理由：未裁定就并报两个数字等于把选择权转嫁给读者（结论句可挑数），违背本仓"结论句式冻结+双尺并列须带口径声明"的既有纪律。允许的更弱默认：可出**聚合级 flip 计数诊断**（每档会翻多少题，零逐题内容）供决策，标签写"decision-support, not caliber"；headline 恒为 T0 直到裁定。

**C3：结论——必须解耦的理由比请求给的更硬：这条提示词改动不只混淆归因，它在化学上就是错的指令，建议不做。**
"仅声明转化所必需的共产物"里的"必需"**化学上无定义**——水解的水"必需"吗？加氧酶的 O2"必需"吗？这等于让模型自己发明净反应口径约定，而协议已经定了（完整产物集）。它会把 B2 的"少写"固化成生成侧常态、削薄审计面，且模型侧口径一旦改变，与忽略档裁定的归因就永久不可分（时间上分开一轮也救不了"生成协议变了"这一层）。若目标是减少无谓共产物，压力应加在**判分侧**（档位），生成协议保持跨批稳定可比。

---

## D. 判断面 D（r27 条款项采纳核对）

**D1：结论——采纳忠实，满足 r27 第 4 点附条件（二选一取了程序门）；但双保险有一个"空集放行"的口子要堵。**
核对：程序门落在 `s5b_scoring.py:292-308`，位于 `evaluate_scientific` 产出之后、逐题聚合（:309-344）与 metrics/report 落盘（:437-444）**之前**，位置正确；detail 携带 `non_qid_strict_bases`/`n_graphs`/note，结构化 ✓；合成档不受影响（正控 `wv6:150-161`）、"未来混合档"非 strict 值同拒（负控 `wv6:139-143`）✓。**口子（建议 P1 级补）**：门读 `coverage_report.pairing.bases_by_graph`（:293-294），若未来评测器版本改键名/该键缺失，读到 `{}` ⇒ `non_strict` 空 ⇒ 门**空真放行**——"全部 qid_strict"的断言在零 basis 时 vacuously true。建议：real 档下 bases_by_graph 缺失或为空一律按不合规拒，并加一条键缺失负控回归（**测试行为待执行验证**）。另两条小项：① r27 建议 D（"本门核档位不核映射"）未在门 note 落字（:306-308 未见该 caveat），建议补，防止"双保险"被读成"映射已核"；② `score_s5b_batch` 未校验 `data_scope ∈ {real, synthetic_rule_level}`（:209/:292 均按字符串相等分支），拼写变体（如 "Real"）会同时绕过两道 real 门——建议入口处白名单校验（**是否由评测器兜底未确认**）。

**D2：结论——已达到 r27 排序的最优档（入口矩阵+调用点测试 > 函数内嵌），锁面有两处可绕过的小口子。**
核对：入口矩阵登记在 `evaluation.py:153-165`（含"新消费方须经 evaluate_scientific 产物消费，不得直调"的显式义务）✓；调用点锁测试扫 `src/**/*.py` 断言唯一活动调用+唯一 def（`wv6:166-196`）✓。口子：①豁免规则是**行模式**（`wv6:182-184`：evaluation.py 内含 `pairing = _pair_exports_to_samples(` 的行一律跳过）——在 evaluation.py 别处再写一个同前缀调用不会红；建议改为"evaluation.py 内该调用模式**计数 == 1**"的断言而非整行豁免。②扫描范围只到 `src/`——src 外的可执行入口（scripts/工具脚本）新增直调不会红；建议在 W-V6.2 登记里写死"活动调用"定义域，或把扫描扩到仓内可执行入口。（动态 getattr 绕过属残余理论面，可接受，不必处理。）

**D3：结论——措辞达到条款要求，且等价性我读码核实为真。**
`evaluation.py:2245-2248` 的 `trigger_equivalence` 写死了"real ∧ 两个 qid 映射皆空 ⇔ 触发 + 整批二档 + 改逐图混合须同步改逐图判"；等价性核对：回退档触发条件是 `not (manifest_qids or export_qids)`（:1887），严格档全图改写 qid_strict（:1913-1926），守卫触发条件是 real ∧ 任一 basis==fallback（:2230-2232），两个映射由 :2151-2152 构建——当前实现下 ⇔ 成立 ✓；测试断言了内容子串（`wv6:239-244`）✓。建议补一处：把同一句等价性搬进预注册 §9-④ 文字，使文档门与代码守卫引用同一表述（目前只在代码 detail 里）。

---

## E. 判断面 E（stereo 消解型编辑设计复审）

**E1：结论——有条件成立：只对"执行+sanitize 后该原子确实不再是立体中心"这一子情形成立；"键级变化所涉原子"作为谓词太宽，存在四类反例。**
成立部分：C–OH→C=O（二级醇→酮）类 sp3→sp2，手性确实随杂化消失，执行器 `Chem.SanitizeMol`（`atom_tool.py:503`）的 cleanup 会摘掉无意义四面体标签，产物 canonical 无该中心立体——机理上是派生属性 ✓。反例：
1. **stereo_created（sp2→sp3 新增立体中心，如对 C=C/C=O 的加成）**：手性是**新信息**，sanitize 无法从键级编辑派生它，产物该中心必为 unspecified——若设计笼统放行"键级变化原子上的立体变化"，此类会静默产出未指定中心。**这是"派生属性"论断最干净的反例**，必须排除在放行外。
2. **仍保持 sp3 的中心上的断键/成键**（SN2 型配体交换、**有机磷水解**——P 中心保持四面体、立体结局由机理定；毒死蜱/对氧磷类是本域核心底物，这类模板一旦放行）：RDKit 四面体标签的 CW/CCW 语义锚定在该原子的**键表顺序**上，`RemoveBond`/`AddBond`（`atom_tool.py:441/:450`）会移动邻居序 → 标签保留但解读翻转 = **静默对映体翻转**。"sanitize 自然结算"在此不是化学，是键序副作用。
3. **E/Z（键立体）**：`_chiral_token` 只比原子标签（`s5b_compiler.py:270-275`），双键 E/Z 差异根本不在 `stereo_changed` 检测面内——sp3→sp2 通常新建双键，其 E/Z 在执行产物里必然未指定；参考若声明 E/Z 则 miss，未声明则被静默断言为"无 E/Z"。这是既有检测盲区，设计复审必须一并披露。
4. **非四面体/累积烯**：RDKit 把丙二烯轴手性存在中央原子的 chiral tag 上（:272-274 注释自己承认非四面体也走同一 token）——"该原子有键级变化 ⇒ 手性消解"在此不必然成立（**具体可行反例我未构造出单步现实反应，标不确定**；缺证据：本题域是否存在此类供体模板）。

**E2：结论——边界必须重钉：放行谓词从"原子上有键级变化"改为"执行+sanitize 后该原子非立体中心 ∧ rhs 模板该 map 无手性声明"，并加执行后 rhs 立体核对 + 机读诊断。**
具体条款建议：① 仅 `change_bond_order` 型变化可进入放行评估（键表顺序不变、无标签重解读风险）；`form_bond`/`break_bond` 落在现存立体中心上一律维持 unsupported（反例 2）；② stereo_created（lhs 无手性→rhs 有手性）维持 unsupported（反例 1）；③ 放行的每例**执行后必须核对**：执行产物在该 map 的立体状态 == rhs 模板声明（不等 ⇒ 结构化 `stereo_derived_mismatch` 拒，而不是靠"派生"假设放行）——没有这一步，编译器是在为它没验证过的声明背书；④ 放行例落机读诊断字段（如 `stereo_dissolution_applied: maps`），供下游统计"多少 strict 命中依赖消解"；⑤ 键立体（E/Z）盲区如实写进边界文字（不在本设计放行面内、当前也不在拒面内——两头都要写）；⑥ 一旦实现，`real_model.py:280-284` 的 capability `unsupported: [charge_edits, stereo_edits, aromatic_bond_tokens]` 与提示词同步改版并版本化——否则模型不会提这些模板，供给面变化测不到（这本身是供给侧变更，须独立批归因，同 C 的纪律）。

**E3：结论——与冻结判据 P1 零冲突，且 strict 口径天然封住该设计的假阳性面。**
严格身份含立体（`chemstate.py:913-929` → `_identity_key`；执行产物 SMILES 为 isomeric 默认 `atom_tool.py:521`）：参考声明了该中心立体而执行产物被消解 ⇒ 严格身份不等 ⇒ 落 `cn_only`（`identity.py:46-55` cn 是立体盲）⇒ 不授 strict、不升格（`evaluation.py:829-831`）——消解只在参考真的无该中心立体时才转化为命中，方向诚实。参考节点 scope 封顶（S5A-01）同样不受影响。残余风险不在判分而在**事件记录层**（反例 2 的静默翻转会把一个无证据的绝对构型写进事件与 provenance，判据一"不伪造特异性"精神层面的失真）——靠 E2 的②③封。v1 命中面 2–3 题属供给侧可生产性变化，建议同样按独立批+消解诊断计数披露。

---

## 总裁定

- **主面（coproduct_ignore_tier）：有条件同意 T1′**——条件清单：①白名单只作用于**产物侧差集**（extras = 事件组分 − 该边声明组分）；②反应物侧**仅 H₂O 特例**豁免，其余反应物侧无机不豁免；③逐项**元素可追溯前提**（杂原子须见于该事件声明的反应物侧）；④O₂ 移出产物侧白名单；⑤补 I⁻、CO₃²⁻；⑥CN⁻/SCN⁻/H₂O₂/NH₂OH/NO 恒不忽略；⑦白名单以 cn 身份层定义并版本化哈希，落地为预注册四元组（档位+哈希+方向策略+追溯开关）；⑧首个生效批以 post-hoc 敏感性表并列披露，单列"纯位次效应"与"新覆盖效应"分离计数；⑨T2 否决，T3 暂不采纳（其可实现子集已并入③）。判据一~五、0d/0e 与本设计零冲突，无 P1。
- **附面一（D1–D3）：同意采纳成立**；补三处：门空集放行堵漏（建议 P1）、"核档位不核映射"落字、入口 data_scope 白名单校验；D2 两处锁面小口子按上文收紧。
- **附面二（E1–E3）：有条件同意（窄化后）**——放行谓词改为"执行后非立体中心 ∧ rhs 无手性声明"+ 执行后 rhs 立体核对 + 机读诊断；stereo_created、断/成键落现存中心、非四面体一律维持 unsupported；E/Z 盲区如实披露。与冻结判据零冲突。

**最值得警惕的两个误判模式**：①**不可追溯白名单洗分**——主产物碰对 + 元素上不可能的白名单无机（无卤底物写 Cl⁻、无磷来源写 PPi、O₂ 写上产物侧）被忽略档洗成 strict，而判据二不查守恒，这是忽略档引入后唯一能藏住这类错误的地方（追溯前提即为此设）；②**"手性=键级变化派生属性"过度泛化**——对仍为四面体的中心（尤其有机磷/硫中心、SN2 型配体交换）靠 RDKit 键序副作用静默翻转绝对构型、对立体创建情形静默产出 unspecified，两者都是"程序诚实、化学误导"，且在立体盲参考下会转化为假严格命中。

（所有执行类断言——测试红绿、sanitize 具体行为、Uncharger 无机往返——维持"待执行验证"。）
