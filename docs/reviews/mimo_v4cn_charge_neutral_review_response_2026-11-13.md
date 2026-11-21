# mimo 化学评审回复：v4-cn 电荷中和披露口径（2026-11-13）

> 通道 A：`opencode run -m opencode/mimo-v2.6-flash-free`（只读评审，无执行权限；回复中"待执行验证"项均未经执行验证）。
> 请求：`docs/mimo_v4cn_charge_neutral_review_request_2026-11-13.md`。原始输出：`docs/review_evidence/v4cn_mimo_20261113/raw_output.txt`（已清理终端控制字符）。
> 采信原则：与程序证据互证为止。

---


> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/scripts/eval/score_disclosure_v4cn.py 
✱ Glob "<REPO_ROOT>/scripts/eval/*.py" 0 matches
> build · mimo-v2.6-flash-free
✱ Glob "<REPO_ROOT>/src/pathway_v43/domain/*.py" 0 matches
✱ Grep "def normalize_charge_smiles|def cn_identity|Uncharger" in <REPO_ROOT>/src · 28 matches
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [offset=900, limit=200]
→ Read <REPO_ROOT>/src/pathway_v43/domain/identity.py 
> build · mimo-v2.6-flash-free
✱ Grep "def strict_identity_of|strict_identity_of =|matched_product_hit|def _matched_product" in <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py · 27 matches
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [offset=1189, limit=120]
✱ Grep "strict_identity_of" in <REPO_ROOT>/src · 86 matches
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/chemstate.py [offset=860, limit=120]
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [limit=150, offset=1400]
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/recorded_source.py [limit=180, offset=400]
> build · mimo-v2.6-flash-free
✱ Grep "def _identity_key|def _guard_input_cx_classes|state_id =|def _derive_state_id|smiles_isomeric" in <REPO_ROOT>/src/pathway_v43/pollutant/chemstate.py · 23 matches
✱ Grep "rederivation|rederive" in <REPO_ROOT>/src/pathway_v43/pollutant · 0 matches
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/chemstate.py [limit=70, offset=690]
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/chemstate.py [limit=70, offset=175]
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [limit=70, offset=2355]
✱ Grep "def _product_hit_row|def _paired_payload|def _batch_export_reader" in <REPO_ROOT>/src/pathway_v43/pollutant/s5b_scoring.py · 3 matches
> build · mimo-v2.6-flash-free
✱ Grep "def _export_states|def _hypothesis_payloads|smiles_isomeric|product_smiles" in <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py · 15 matches
> build · mimo-v2.6-flash-free
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [limit=50, offset=2284]
→ Read <REPO_ROOT>/src/pathway_v43/pollutant/evaluation.py [limit=45, offset=2440]
> build · mimo-v2.6-flash-free
✗ Read <REPO_ROOT>/.git/HEAD failed
Error: File not found: <REPO_ROOT>/.git/HEAD
> build · mimo-v2.6-flash-free
**通道**：OpenCode `mimo-v2.6-flash-free`（通道 A）｜**性质**：只读化学评审，无执行权限，**未运行任何代码、无任何执行结果**
**已读源码**：`scripts/eval/score_disclosure_v4cn.py`、`src/pathway_v43/domain/identity.py`、`pollutant/chemstate.py`（`_identity_key` / `build_chemical_state`）、`pollutant/evaluation.py`（v2/v3/v4 判据段、B-6 碳酸闭集、`_export_states`、v4 事件判定）、`pollutant/recorded_source.py`（记录侧形式归一）、`validation/conservation.py`（F-2 注释）
**未核**：实际分支/HEAD（无执行权限，`.git/HEAD` 读不到）。凡"算子实际跑出来是什么"一律标 **待执行验证**。

**一句话结论**：方向是对的——质子化写法差异不是化合物身份差异，做披露口径站得住；但当前实现是"整分子裸跑 `Uncharger()` + 纯 SMILES 往返"，缺三道护栏（形式电荷位点被改写、CX 事实丢失、盐/反离子没处理），补齐前只宜当内部披露数用。

| 题 | 结论 |
|---|---|
| 1 化学合理性 | 有条件同意 |
| 2.1 季铵/吡啶鎓 | 有条件同意 |
| 2.2 两性离子（氨基酸） | 同意 |
| 2.3 硝基/N-氧化物/偶氮鎓 | 有条件同意 |
| 2.4 磷酸/硫酸单酯与二酯 | 同意 |
| 2.5 磺酸根 | 同意 |
| 2.6 辅酶 A 硫酯 | 同意 |
| 2.7 金属/卤素阴离子盐 | **不同意**（应排除或单列） |
| 2.8 烯醇负离子与羰基 | 有条件同意 |
| 3 会不会合并不同物种 | 有条件同意 |
| 4 护栏建议 | 有条件同意（11 条） |

---

## 3.1 化学合理性

**结论**：有条件同意

**理由**：质子化状态由 pH 和数据库书写习惯决定，不改变化合物身份，用严格结构身份去罚"写法"等于把记录习惯记成预测错误；作为**只披露、不替换主成绩**的口径，方向安全。但"只差质子即同物"只在共价骨架、取代基、氧化态、自由基数完全一致时成立——水合（CO₂→H₂CO₃）、成盐（多一个反离子）、脱酰基（硫酯→游离酸）都不是质子化，不能并。

**建议**：
- 维持"双口径并列 + 题域标签 + 主成绩仍严格 v4"（现状已满足，不要放松）；
- 把可中和面写成显式判据：**仅当两侧重原子图/键级/同位素/立体/自由基/组分数一致，差异只在形式电荷与相应位点 H 数时**，才允许判同一产物；
- NH₄⁺/NH₃、CN⁻/HCN、H⁺/H₃O⁺ 这类既是质子化对、又被本仓 `CRITERIA_V2_NEVER_EXEMPT_FAMILIES` 点名的族，是否并入由 CC 裁定，不由算子静默决定。

---

## 3.2 Uncharger 边界情况（逐子项）

### 2.1 季铵 / 吡啶鎓类永久正电荷
**结论**：有条件同意
**理由**：四取代 N 没有可移走的质子，算子中和不了，两侧同形照样相等，不会因中和产生误合并——`validation/conservation.py` 已注明"季铵/甜菜碱 N（百草枯/敌草快/胆碱型），Uncharger 中和不了，F-2 残电荷"。真正的风险是**改写**而非合并：若其配对阴离子被算子处理，会多出或改掉一个组分。
**建议**：对含永久正电荷的结构做夹具实测；中和后若净电荷非 0 或组分数变化，回退原串并记 `permanent_charge_retained`。
**待执行验证**：Uncharger 对季铵盐配对阴离子（Cl⁻/Br⁻/对阴离子）的实际处理。

### 2.2 两性离子（氨基酸）
**结论**：同意
**理由**：N⁺ 去质子、COO⁻ 加质子后回到中性氨基酸，与数据库写成中性的同物相等，正是本口径想要的；甘氨酸/GABA 在酸式、碱式、两性三种写法下应收敛同一形。唯一要盯的是**带永久 N⁺ 的甜菜碱型**：COO⁻ 被质子化而 N⁺ 留着，输出会变成净 +1 的"内盐酸式"，名叫"中和"却带电。
**建议**：净电荷在中和前后发生变化（0→+1 之类）的结构单列一档 `net_charge_changed`，不与正常命中混算。
**待执行验证**：甜菜碱/内盐经 Uncharger 后的净电荷与形态。

### 2.3 硝基、N-氧化物、偶氮鎓等形式电荷结构
**结论**：有条件同意（**这是最需要实测的一类**）
**理由**：它们都是"形式电荷分离但整体中性"的分子；若算子给阴离子 O 加质子而阳离子中心无质子可去，会把**中性分子改写成阳离子**（硝基→硝酸型阳离子、N-氧化物→N-羟基鎓），既改净电荷也可能造成后续误比。若算子识别形式电荷对并整体跳过，则无影响——两种结局都不是"质子化归一"的本意。
**建议**：把硝基 / N-氧化物 / 偶氮鎓 / 叠氮 / 亚铵做成固定夹具，实测并登记成机读"算子行为表"（对齐 `recorded_source.py` 的 param spec 登记纪律）；出现净电荷符号变化即回退原串。
**待执行验证**：Uncharger 对 `[N+](=O)[O-]`、`[O-][N+]`（N-氧化物）、`[N-]=[N+]` 类的实际输出与净电荷。

### 2.4 磷酸 / 硫酸单酯与二酯
**结论**：同意
**理由**：单酯与二酯差的是酰基/烷基取代基，重原子图不同，只做电荷中和不会互相合并；同一酯的 −2/−1/0 质子化态收敛到同一中性形才是本意——本仓 v2 对 Pi/PPi 的质子化变体已按"收敛单一 cn 键"在导入期断言，先例一致。真正的遗漏是**成盐写法**（带 Na⁺/K⁺ 反离子）消不掉。
**建议**：把"磷酸/硫酸酯质子化变体收敛"作正控夹具钉死；把"带碱金属反离子的酯"登记为已知不覆盖（under-normalization），在披露数里单列。

### 2.5 磺酸根
**结论**：同意（附实测条件）
**理由**：R-SO₃⁻ → R-SO₃H 只是质子化，R 不变就不会误合并，磺酸与磺酸根在化合物意义上是同一物。前提是算子对高价 S 的磺酸根确实加质子、且不动 S=O 键。
**建议**：夹具覆盖芳环磺酸、牛磺酸型、长链烷烃磺酸三种；若算子不动磺酸根，在披露里注明"磺酸类未覆盖"，不要默认已覆盖。
**待执行验证**：Uncharger 对 `S(=O)(=O)[O-]` 的处理。

### 2.6 辅酶 A 硫酯
**结论**：同意（风险低）
**理由**：硫酯与游离 CoA-SH 差的是酰基，重原子图不同，不会被合并；中和只动 CoA 骨架上的磷酸/质子位点，不触硫酯键。遗留问题仍是**反离子/成盐写法**，以及大分子多位点中和经纯 SMILES 往返的表示稳定性。
**建议**：乙酰-CoA / 游离 CoA / CoA 二硫化物做正负控夹具；大分子中和前后额外核对重原子数与同位素不变。
**待执行验证**：CoA 类大分子经 `MolFromSmiles→MolToSmiles` 往返是否丢 CX 注记。

### 2.7 含金属或卤素阴离子的盐
**结论**：**不同意**（该类不能直接吃进 v4-cn）
**理由**：算子删不掉 Na⁺/K⁺/金属阳离子，多半只造成"该合没合"的漏判；而卤素阴离子若被质子化成 HX，属于**错误改写**（给卤素加了质子、多出一个组分），既不是中和也不是去盐。盐的正确处理是**去反离子**，那是另一个口径，不能混在"电荷中和"里静默做。
**建议**：识别"多组分 + 存在独立单价离子/金属离子"的结构，标 `salt_not_normalized`，从 v4-cn 增量中单列（不静默计命中、也不静默计不命中）；如确需去盐，另立口径单独评审。
**待执行验证**：Uncharger 对 `Cl-` / `Br-` / `[Na+]` / `[Zn+2]` 的实际输出。

### 2.8 烯醇负离子与羰基
**结论**：有条件同意（不会误合并，但结果随数据库写阴离子的习惯漂移）
**理由**：C⁻ 质子化回到酮、O⁻ 质子化回到烯醇，两者都只差一个质子，方向上都不算误合并。但 v4 不做互变异构归一（v3 档 B 仍锁着，`tautomer_promoted_nodes` 恒空），于是同一个"烯盐"按写法不同会分别并到酮或烯醇，判分结果随书写习惯漂移。这是**不一致**，不是误合并，但会让披露数的可解释性打折。
**建议**：把酮-烯醇-烯盐体系列为已知不稳定面单独出桶表；若要消除漂移，另开一条**互变异构披露臂**与 v4-cn 分列，不要顺手塞进电荷中和。

---

## 3.3 会不会合并本来不同的物种

**结论**：有条件同意

**理由**：只做电荷中和时，两侧必须先有相同重原子图才可能相等，氧化态不同（O/原子数不同）与骨架不同的物种基本不可能被误合并，互变异构也不被并（v4-cn 没跑 TautomerEnumerator）。真正的误合并面有三处：跨本仓常量点名的无机质子化对（NH₄⁺/NH₃、CN⁻/HCN、H⁺/H₃O⁺→H₂O）、**纯 SMILES 往返丢 CX 事实**（自由基层 `^n:`、增强立体 `&N:`）后与闭壳层/单构型写法相等、以及盐反离子处理不对称。互变异构 + 质子化叠加造成的是结果漂移（同一烯盐按写法不同并到酮或烯醇），不是误合并，但需单列。

**建议**：
- 中和前后强制不变量比对：**原子数 / 元素序列 / 键级 / 同位素 / 立体（含增强立体）/ 自由基电子数 / 组分数**，任一变化即回退原串并记机读原因；
- 只对**真带电**结构做往返，净电荷 0 且无带电原子 → 直通原串（避免无谓改写）；
- 幂等自检：中和两次 == 一次；
- 互变异构保持不做（范围窄是对的），但把受酮-烯醇影响的题单独分桶披露。
**待执行验证**：自由基/增强立体经 `MolFromSmiles→MolToSmiles` 往返是否丢失；`MolFromSmiles` 是否解析 CX 段（丢→假新命中，拒→静默回退）。

---

## 3.4 护栏建议

**结论**：有条件同意（下列护栏补齐后，可正式用作披露口径）

**理由**：现有 `--self-check` 只验证"不中和"路径复现官方 `metrics_v4.json`，**中和路径本身没有任何不变量或一致性检查**。仓内已有可直接对齐的先例——`recorded_source.py` 的记录侧形式归一（逐组分、实跑短路、逐原子对应、all-or-nothing 回退）与 v3 B-6 碳酸闭集排除。不补齐就报数，翻转题里会混进"往返伪影"和"底物侧被改写"两类非电荷归因的假增量。

**建议**（按优先级）：

1. **中和不变量 + 短路**（镜像 record-side 纪律）：重原子图/键级/同位素/立体/增强立体/自由基/映射号全不变，仅允许形式电荷与被中和位点 H 数变化；不变量破坏 ⇒ 回退原串 + 逐原子差异行。
2. **CX 事实保全或排除**：`_neutralize` 走纯 `MolToSmiles`，而 v4 参考侧身份是 `strict_identity_of` → `_identity_key` 的 **CXSMILES**（保留 `^n:`/`&N:`），事件侧则**直接拿 `smiles_isomeric` 当身份串**（`evaluation.py` 2463/2467 行）。两者不同源，含自由基/增强立体的结构必须要么改走同一身份机器，要么排除。
3. **形式电荷保护**：中和前后净电荷符号或非零状态改变 ⇒ 回退原串 + `net_charge_changed`（覆盖季铵/甜菜碱/N-氧化物/硝基/偶氮鎓）。
4. **盐/反离子单列**：`salt_not_normalized`，既不静默计命中也不静默计不命中；不要在本口径里引入"去反离子"。
5. **排除清单**（与既有常量对齐）：碳酸体系闭集 CO₂/HCO₃⁻/CO₃²⁻（对齐 v3 B-6 逐对象排除）；`CRITERIA_V2_NEVER_EXEMPT_FAMILIES` 中受质子化影响的 NH₃/NH₄⁺、CN⁻、SCN⁻、H⁺/H₃O⁺（由 CC 裁定）；盐与金属配合物；CX 自由基无法保全时的自由基结构。
6. **逐侧归一状态留痕**：`flips_*.jsonl` 每题记 reference / prediction 各自 `normalization_status`（applied / not_applicable / failed）+ 是否真的改写了字符串 + 中和前后净电荷 + 组分数，否则一次 `new_hit` 分不清是"写法差异被消掉"还是"往返伪影"。
7. **归因到侧**：v4 的 `CRITERIA_V4_HIT_MODE_SCOPE` 含底物身份（`declared_principal_products_and_substrate_identity`），中和同时作用于底物节点与产物节点——翻转必须标 product-side / substrate-side。
8. **派生事实一致性**（实现面）：`_neutral_payload` 只改 `smiles_isomeric` 与 `cn_identity`，`state_id` / `formal_charge` / `structure_smiles_raw` 仍是旧值，而 `state_id = stable_id("cs", identity)`、身份即 `smiles_isomeric`——身份变了 id 没变。要么同步重算，要么明确披露"仅身份轴被改写"。
9. **自检扩展**：现有 self-check 不覆盖中和路径；补 (a) 中和幂等，(b) 中和路径零异常（无 `ChemicalStateError`、无静默回退），(c) 中和后 `reference_graph_sha256` 与 manifest 声明一致。
10. **固定夹具探针 + 机读算子行为表**：2.1–2.8 每个子项做成 fixture 跑一遍落 `docs/`（哪些被改写、净电荷变化、骨架变化、组分数变化），作为该口径的算子登记；探针在隔离 tmp 跑，禁写仓库（AGENTS 审核证据条款）。
11. **数字资格**：披露数属自报内部数，对外引用前按 AGENTS 做一次独立复核；若将来要转正进主成绩，按自迭代闸门走 ±15% 判据。

**待执行验证**：第 8 条的下游是否真的走到状态重推导（走到即 `state_fact_rederivation_mismatch`）；第 2、9 条的 CX 往返与中和幂等实测结果。
