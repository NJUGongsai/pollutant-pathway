# P0-1 判读争议件师姐裁定包（12 件 = A 组 7 + B 组 5，2026-10-18）

> **背景一句话**：机器编译器机械拒绝了一批候选反应，我们在测「误拒率」（其中多少其实本应通过编译；题域标签：298/RHEA 通用酶学/已见题）。两位机器判读者（mimo 主判 / Codex 独立二读，B 组另有 mimo 手动通道一读）在下列 12 件上判定不一致。按测量设计，**化学实质判断以师姐逐件裁定为准**，裁定结果同时用作下一轮判读规则的校准样例。

> **本包自包含、零金标**：全部材料在文内（题底物 + 语料证据记录），不含标准答案、不含判分参考，无需访问任何仓库。

> **请按此格式回复**（12 行，一行一裁定）：
> `case_id | pass_expected 或 reject_correct 或 uncertain | 一句话化学理由`

> 三值含义：**pass_expected** = 该件本应通过编译——存在化学上成立的原子映射使净反应可编译（原子/键级守恒可配平；水/质子增减按现行豁免口径）；**reject_correct** = 机械拒绝正确（无可行映射，或存在独立成立的拒因——产物原子无来源、中心对不上、产物集不匹配等）；**uncertain** = 证据确实不足无法判。判读只从文内给定证据出发（题底物 + donor/product/模板），化学直觉用于判断可行性与中心归属，不引外部文献补证据。

---

## A 组 7 件（analog|no_alignment 通道，**回炉校准用——请优先**）

（A 通道机械拒因 = 「找不到对齐」。判读要点：模板与题底物的结构差异，是**反应中心对不上**，还是**旁观位取代基差异**；产物原子是否都有来源。）

### A-1 `a-2027e5910575bb3b`

**材料**
- 题底物（substrate_smiles）：`CCc1cccc(CC)c1N(COC)C(=O)CCl`
- 证据记录：record_key `tpl-env:EAWAG-SOIL:43729396-9ce4-4b94-a83a-83daed303795`（channel=analog，family=转氨族(PLP/氨基酸)）
- 证据 donor：`CCC1=C(C(=CC=C1)C)N(COC(C)C)C(=O)CCl`
- 证据 product：`CCC1=C(C(=CC=C1)C)N(COC(C)C)C(=O)CSC[C@@H](C(=O)NCC(=O)O)NC(=O)CC[C@@H](C(=O)O)N`
- 模板[0] mapped_lhs：`Cl[CH2:18][C:16]([N:10]([c:4]1[c:3]([CH2:2][CH3:1])[cH:8][cH:7][cH:6][c:5]1[CH3:9])[CH2:11][O:12][CH:13]([CH3:14])[CH3:15])=[O:17]`
- 模板[0] mapped_rhs：`N[C@@H](CCC(=O)N[C@@H](CS[CH2:18][C:16]([N:10]([c:4]1[c:3]([CH2:2][CH3:1])[cH:8][cH:7][cH:6][c:5]1[CH3:9])[CH2:11][O:12][CH:13]([CH3:14])[CH3:15])=[O:17])C(=O)NCC(=O)O)C(=O)O`

**机器判定分歧**
- mimo 主判：**pass_expected** —— ③ 模板断 [CH2:18]–Cl、mapped_rhs 成 S–[CH2:18] 键（谷胱甘肽取代氯，S_N2）；题底物 acetochlor 的 ClCH2C(=O)N 反应中心相同，N-CH2OCH3 与 2,6-二乙基↔模板 N-CH2OCH(CH3)2 与 2-乙基-6-甲基为旁观位差异，GSH 结构取自 product/template rhs 配平。
  （锚：断 [CH2:18]–Cl 键、成 [CH2:18]–S 键（mapped_rhs …CS[CH2:18]…，S 来自 product 谷胱甘肽硫；Cl 以 Cl⁻/HCl 离去配平）；题底物 acetochlor 与模板底物仅 N-CH2OR 与芳环烷基旁观位不同）
- Codex 二读：**reject_correct** —— ①题底物氯乙酰胺中心可对应，外围取代差异按旁观位处理；命中②：record_content.donor 只有含一个 N 且无 S 的氯乙酰胺，product 与 mapped_rhs 却增加谷胱甘肽片段的 S/C/N 等原子，材料无其来源，不能由水/质子豁免补齐。

分歧焦点：产物比 donor 多出谷胱甘肽片段（S/C/N 无来源）——是证据集配不出净反应（拒），还是模板图式可作为依据（过）？

### A-2 `a-9014ac66da35eb39`

**材料**
- 题底物（substrate_smiles）：`CC1(C)[C@@H](C=C(Cl)Cl)[C@@H]1C(=O)OCc1cccc(Oc2ccccc2)c1`
- 证据记录：record_key `tpl-env:EAWAG-SEDIMENT:f20c9b33-d836-45d0-9b86-6bb26936cc1f`（channel=analog，family=其它）
- 证据 donor：`CC1=C(C=CC=C1COC(=O)C2C(/C=C(/C(F)(F)F)\Cl)C2(C)C)C3=CC=CC=C3`
- 证据 product：`CC1(C)C(/C=C(/C(F)(F)F)\Cl)C1C(=O)O`
- 模板[0] mapped_lhs：`Cc1c(C[O:8][C:6]([CH:5]2[C:2]([CH3:1])([CH3:3])[CH:4]2/[CH:9]=[C:10](/[C:11]([F:12])([F:13])[F:14])[Cl:15])=[O:7])cccc1-c1ccccc1`
- 模板[0] mapped_rhs：`[CH3:1][C:2]1([CH3:3])[CH:4](/[CH:9]=[C:10](/[C:11]([F:12])([F:13])[F:14])[Cl:15])[CH:5]1[C:6](=[O:7])[OH:8]`
- 模板[1] mapped_lhs：`[CH3:1][c:2]1[c:3](-[c:24]2[cH:25][cH:26][cH:27][cH:28][cH:29]2)[cH:4][cH:5][cH:6][c:7]1[CH2:8][O:9][C:10](=[O:11])[CH:12]1[CH:13](/[CH:17]=[C:18](/[C:19]([F:20])([F:21])[F:22])[Cl:23])[C:14]1([CH3:15])[CH3:16]`
- 模板[1] mapped_rhs：`O[c:27]1[cH:26][cH:25][c:24](-[c:3]2[c:2]([CH3:1])[c:7]([CH2:8][O:9][C:10](=[O:11])[CH:12]3[CH:13](/[CH:17]=[C:18](/[C:19]([F:20])([F:21])[F:22])[Cl:23])[C:14]3([CH3:15])[CH3:16])[cH:6][cH:5][cH:4]2)[cH:29][cH:28]1`
- 模板[2] mapped_lhs：`CC1(C)C(/C=C(\Cl)C(F)(F)F)C1C(=O)[O:9][CH2:8][c:7]1[c:2]([CH3:1])[c:3](-[c:10]2[cH:11][cH:12][cH:13][cH:14][cH:15]2)[cH:4][cH:5][cH:6]1`
- 模板[2] mapped_rhs：`[CH3:1][c:2]1[c:3](-[c:10]2[cH:11][cH:12][cH:13][cH:14][cH:15]2)[cH:4][cH:5][cH:6][c:7]1[CH2:8][OH:9]`

**机器判定分歧**
- mimo 主判：**reject_correct** —— 命中①：酯醇侧骨架不同——donor 为联苯基甲基（C–C 直连），底物为苯氧基苄基（多一个醚氧且连接方式不同），该区正落在模板反应中心（酯键与芳环羟基化位），非旁观位差异。
- Codex 二读：**pass_expected** —— ①题底物酯中心可对应 templates[0]，②该模板羧酸产物与 record_content.product 相符，未见独立拒因；命中③：仅裂解酯氧的苄基侧键，CF3/Cl 与芳基的中心外差异按旁观位豁免。
  （锚：选 templates[0]：断未编号苄基 C—O8，O8 得 H，C6=O7 及 C6—O8 两侧均保留；题底物酯羰基/羰基氧/酯氧对应 6/7/8，释放对应二氯乙烯基环丙烷羧酸，绝非断酰基 C6—O8，CF3/Cl 及芳基差异在该裂解中心外。）

分歧焦点：donor 骨架（联苯甲基 C-C）与题底物（苯氧基苄基，多一个醚氧）——是反应中心对不上（拒）还是仅裂酯氧苄基键、外围差异属旁观位（过）？

### A-3 `a-0120308e05d147c6`

**材料**
- 题底物（substrate_smiles）：`O=C([O-])c1ccc(Cl)cc1`
- 证据记录：record_key `tpl-env:EAWAG-BBD:bt0051#r0321`（channel=analog，family=其它）
- 证据 donor：`[O-]C(=O)c1ccc(cc1)C([O-])=O`
- 证据 product：`[O-]C(=O)c1ccccc1`
- 模板[0] mapped_lhs：`O=C([O-])[c:7]1[cH:6][cH:5][c:4]([C:2]([O-:1])=[O:3])[cH:9][cH:8]1`
- 模板[0] mapped_rhs：`[O-:1][C:2](=[O:3])[c:4]1[cH:5][cH:6][cH:7][cH:8][cH:9]1`

**机器判定分歧**
- mimo 主判：**reject_correct** —— ①donor [O-]C(=O)c1ccc(cc1)C([O-])=O（邻苯二甲酸根，两个 COO-）与题底物 O=C([O-])c1ccc(Cl)cc1（4-氯苯甲酸根）不同物质：模板 [C:2]([O-:1])=[O:3] 位在题底物上是 Cl，同底物前提不成立。
- Codex 二读：**pass_expected** —— ①题底物现有羧基可映到 templates[0] 的离去羧基，②未见独立拒因；命中③：实际脱除位是 c7，另一保留位的羧基/Cl 差异属于旁观位，羧酸与羧酸根的质子差异按豁免处理。
  （锚：templates[0]：断 c7—lhs 开头未编号羧基碳的键，c7 得 H，c4—C2 及 C2(=O3)—O1 两侧保留；把题底物现有羧基放到 c7 的离去位，para 位 Cl 对应 c4 的旁观取代位，环骨架及 Cl 保留，脱羧得到氯苯，不把保留的 c4—C2 误报为断键。）

分歧焦点：donor 为邻苯二甲酸根（两个 COO-）、题底物为 4-氯苯甲酸根——第二个羧基缺失落在模板映射位（拒）还是脱除位可对应、保留位差异属旁观（过）？

### A-4 `a-079a94f836d4f12f`

**材料**
- 题底物（substrate_smiles）：`O=C(O)c1ccc(O)cc1O`
- 证据记录：record_key `tpl-env:EAWAG-BBD:bt0349#r0152`（channel=analog，family=其它）
- 证据 donor：`Oc1ccc(C([O-])=O)c(c1)C([O-])=O`
- 证据 product：`Oc1cccc(c1)C([O-])=O`
- 模板[0] mapped_lhs：`O=C([O-])[c:5]1[cH:4][cH:3][c:2]([OH:1])[cH:7][c:6]1[C:8]([O-:9])=[O:10]`
- 模板[0] mapped_rhs：`[OH:1][c:2]1[cH:3][cH:4][cH:5][c:6]([C:8]([O-:9])=[O:10])[cH:7]1`

**机器判定分歧**
- mimo 主判：**reject_correct** —— 独立拒因②：模板受体为尿嘧啶（4-羰基），证据底物为胞嘧啶（4-氨基），产物集不匹配
- Codex 二读：**pass_expected** —— ①题底物羧基可对应 templates[0] 的离去位，②未见独立拒因；命中③：脱除连接 c5 的未编号羧基，c6 保留位的羧基/OH 差异属于旁观位，质子差异按豁免处理。
  （锚：templates[0]：断 c5—lhs 开头未编号羧基碳的键，c5 得 H，c6—C8 羧基键及 c2—OH1 两侧保留；题底物羧基所连芳碳对应 c5，para-OH 对应 c2—OH1，ortho-OH 对应 c6 旁观位，脱羧得间苯二酚，不声称断保留的 c6—C8。）

分歧焦点：模板受体尿嘧啶（4-羰基）vs 证据底物胞嘧啶（4-氨基）——产物集不匹配（拒）还是脱羧位可对应、其余属旁观位（过）？

### A-5 `a-c2b2e9e6aa3bf0d6`

**材料**
- 题底物（substrate_smiles）：`Cc1cc(O)ccc1[N+](=O)[O-]`
- 证据记录：record_key `tpl-env:EAWAG-BBD:bt0080#r0476`（channel=analog，family=其它）
- 证据 donor：`Cc1c(cc(cc1[N+]([O-])=O)[N+]([O-])=O)[N+]([O-])=O`
- 证据 product：`Cc1c(N)cc(cc1[N+]([O-])=O)[N+]([O-])=O`
- 模板[0] mapped_lhs：`O=[N+:4]([O-])[c:3]1[c:2]([CH3:1])[c:8]([N+:9]([O-:10])=[O:11])[cH:7][c:6]([N+:12]([O-:13])=[O:14])[cH:5]1`
- 模板[0] mapped_rhs：`[CH3:1][c:2]1[c:3]([NH2:4])[cH:5][c:6]([N+:12]([O-:13])=[O:14])[cH:7][c:8]1[N+:9]([O-:10])=[O:11]`

**机器判定分歧**
- mimo 主判：**pass_expected** —— 同底物前提成立（模板另两个NO2为旁观位差异）；可行映射：[N+:4]→[NH2:4]，硝基→氨基还原，守恒可配平
  （锚：[N+:4]→[NH2:4]；模板另两NO2 vs 底物H旁观）
- Codex 二读：**uncertain** —— ①题底物硝基可对应 templates[0] 的 N4 中心，旁观位差异按豁免处理；④：mapped_lhs 的 N4 为 +1、mapped_rhs 为中性 NH2，材料只证明电荷变化，未提供该编辑不可行或可编译的依据，不能确认②或③。

分歧焦点：硝基→胺还原（N+ 变中性 NH2、脱 2O 成水、加 2H）——守恒可配平属豁免（过）还是材料证明不了电荷编辑可行性（存疑）？

### A-6 `a-6e423f4c33a45b6a`

**材料**
- 题底物（substrate_smiles）：`C[C@H](O)CO`
- 证据记录：record_key `tpl-rhea:17494`（channel=analog，family=其它）
- 证据 donor：`*`；`OCC(O)CO`
- 证据 product：`O=C(CO)CO`；`[H]*[H]`
- 模板[0] mapped_lhs：`[*:8].[OH:1][CH:2]([CH2:3][OH:4])[CH2:5][OH:6]`
- 模板[0] mapped_rhs：`[O:1]=[C:2]([CH2:3][OH:4])[CH2:5][OH:6].[H:7][*:8][H:9]`

**机器判定分歧**
- mimo 主判：**pass_expected** —— ③ 模板 [OH:1][CH:2]…→[O:1]=[C:2]… 仲醇氧化为酮、[*:8] 承氢成 [H:7][*:8][H:9]；题底物 C[C@H](O)CO 的仲醇碳映射 [CH:2]，模板 [CH2:5][OH:6]↔题底物 CH3 为旁观位差异，净反应可配平。
  （锚：断 C2–H 与 O1–H、成 C2=O1 双键（mapped_lhs [OH:1][CH:2]([CH2:3][OH:4])[CH2:5][OH:6] → mapped_rhs [O:1]=[C:2]…），H2 经 [H:7][*:8][H:9] 离去；模板 [CH2:5][OH:6] 对应题底物 CH3 为旁观位取代基差异）
- Codex 二读：**uncertain** —— ①题底物仲醇可对应 templates[0] 的 O1—C2 氧化中心；④：另一产物 [H]*[H] 与 donor 的 * 共用映射 *8 且增加 H，但材料未说明抽象受氢体的产物对应及氢豁免如何适用，无法证实②独立拒因或③可编译。

分歧焦点：仲醇氧化成酮 + 抽象受氢位 [*:8] 得两个 H——模板映射成立（过）还是受氢体产物对应无从证实（存疑）？

### A-7 `a-ae58d9d71c2d7bf4`

**材料**
- 题底物（substrate_smiles）：`CC(=O)C(C)O`
- 证据记录：record_key `tpl-rhea:10962`（channel=analog，family=其它）
- 证据 donor：`C[C@@H](O)C(=O)[O-]`
- 证据 product：`C[C@H](O)C(=O)[O-]`
- 模板[0] mapped_lhs：`[CH3:1][C@@H:2]([OH:3])[C:4](=[O:5])[O-:6]`
- 模板[0] mapped_rhs：`[CH3:1][C@H:2]([OH:3])[C:4](=[O:5])[O-:6]`

**机器判定分歧**
- mimo 主判：**reject_correct** —— 命中①：模板反应中心是乳酸 [C@@H:2] 立体反转，donor 为乳酸盐；底物为 3-羟基-2-丁酮 CC(=O)C(C)O，羧酸根与酮/醇排布均不同，非旁观位差异。
- Codex 二读：**uncertain** —— ④：templates[0] 的唯一变化是 C2 从 @@H 到 @H，而 substrate_smiles=CC(=O)C(C)O 未指定手性；材料没有题底物起始构型或该立体编辑支持信息，无法证实②不可行，也无法给出③所需的确定立体映射。

分歧焦点：模板中心是乳酸 C2 立体反转（连 OH/COO-/CH3），题底物对应碳连 O/C(=O)CH3/CH3 且未标注手性——中心邻域连接不同（拒）还是手性信息缺失（存疑）？

---

## B 组 5 件（corpus|mapping_enumeration_truncated 通道，确认轨道——可稍后回）

（B 通道机械拒因 = 「映射枚举达上限被截断」。判读要点：被截断丢掉的组合里有没有**本可编译的候选**（pass_expected=误拒）；还是这些件本就有独立拒因——组分混源（产物原子来自多组件混合映射）、产物集不可拷贝对应（如 [H+]/O=O 无对应）——与截断无关（reject_correct）。）

### B-1 `b-ea54732f4a13843a`

**材料**
- 题底物（substrate_smiles）：`CC1=C([N+](=O)[O-])C[C-]([N+](=O)[O-])C=C1[N+](=O)[O-]`
- 证据记录：record_key `rhea:80176@L34449`（channel=corpus，family=糖基）
- 证据 donor：`CC1=C([N+](=O)[O-])C[C-]([N+](=O)[O-])C=C1[N+](=O)[O-]`；`NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1`；`[H+]`
- 证据 product：`CC1=C([N+](=O)[O-])CC([N+](=O)[O-])C[C-]1[N+](=O)[O-]`；`NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)c1`
- 模板：（空，本通道该件无模板证据）

**机器判定分歧**
- mimo 主判（免费线）：**pass_expected** —— 命中③：TNT-Meisenheimer donor[0] C7H6N3O6- 得 2 隐式 H(1 来自 NADH 质子氢+1 来自 donor[2] H+)还原为产物[0] C7H8N3O6-，重原子全 A 可溯(仅 H/键级变)；donor[1] NADH(C21H26…-4)失 1 隐式 H 成产物[1] NAD+(C21H25…-3)，B 可溯拷贝。三底物组合空间大，该还原映射在截断面外、被上限截断丢弃(RDKit 骨架匹配两产物均单源=干净二分)。
  （锚：Meisenheimer donor[0]→产物[0](A 加氢) 与 NADH→NAD+(B 拷贝) 均单源；该可行组合映射数多、位于截断面之外）
- mimo 手动通道：**reject_correct** —— 手动通道①无可行映射：donor 含 [H+] 而 product[0] 仍带 [C-]，产物侧净电荷多一负，形式电荷/键级无法同时守恒
- Codex 二读：（该件未抽入其二读样本，无判定）

分歧焦点：Meisenheimer 中间体加氢还原（donor 含 [H+]，product 仍带 [C-]）——电荷/键级守恒成立可配平（过）还是净电荷差一负无法守恒（拒）？

### B-2 `b-63bce3c84d43f18c`

**材料**
- 题底物（substrate_smiles）：`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O`
- 证据记录：record_key `rhea:10277@L719`（channel=corpus，family=其它）
- 证据 donor：`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=P([O-])([O-])O[C@H]1[C@@H](OP(=O)([O-])[O-])[C@H](OP(=O)([O-])[O-])[C@@H](OP(=O)([O-])OP(=O)([O-])[O-])[C@H](OP(=O)([O-])[O-])[C@H]1OP(=O)([O-])[O-]`；`[H+]`
- 证据 product：`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=P([O-])([O-])O[C@@H]1[C@@H](OP(=O)([O-])[O-])[C@H](OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](OP(=O)([O-])[O-])[C@H](OP(=O)([O-])OP(=O)([O-])O)[C@@H]1OP(=O)([O-])[O-]`
- 模板：（空，本通道该件无模板证据）

**机器判定分歧**
- mimo 主判（免费线）：**reject_correct** —— 命中②组分混源：IP7(产物[1] 带 POP 的肌醇焦磷酸) 由 ATP(donor[0] γ-磷酸) 与 肌醇六磷酸(donor[1]) 两组分键连(P-O-P 焦磷酸键连到肌醇环 O)，无法单源对应(RDKit 任意键骨架匹配判跨组分融合)；截断与否不改判。
- mimo 手动通道：**pass_expected** —— ③可行且无独立拒因、多中心/跨组分深部组合位于截断面外（手动通道 md §三）
  （锚：ATP γ-P(3 个非桥氧)转移形成新焦磷酸末端 + 受体 C4 焦磷酸末端 P(+3O) 分子内重排至 C3/C5；6 个 OP 位点多可断 P-O 键使组合数远超 64，位于枚举序尾部）
- Codex 二读：（该件未抽入其二读样本，无判定）

分歧焦点：ATP+七磷酸肌醇→ADP+八磷酸肌醇的焦磷酸重排——可行组合位于枚举截断面外（过=误拒）还是组分混源/无独立拒因不成立（拒）？

### B-3 `b-44694dd9f777aa13`

**材料**
- 题底物（substrate_smiles）：`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O`
- 证据记录：record_key `rhea:10829@L977`（channel=corpus，family=酰基族(CoA)）
- 证据 donor：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCS`；`Nc1ccccc1C(=O)[O-]`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O`
- 证据 product：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)c1ccccc1N`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=P([O-])([O-])OP(=O)([O-])O`
- 模板：（空，本通道该件无模板证据）

**机器判定分歧**
- mimo 主判（免费线）：**reject_correct** —— 命中②组分混源：邻氨基苯甲酰-CoA(产物[0] NCCSC(=O)c1ccccc1N) 由 CoA(donor[0] NCCS 阉iol) 与 邻氨基苯甲酸(donor[1] 羧基) 两组分键连(C-S 酯键把邻氨基苯甲酰连到 CoA S)，无法单源对应(RDKit 任意键骨架匹配判跨组分融合)；截断与否不改判。
- mimo 手动通道：**pass_expected** —— ③可行且无独立拒因、多中心/跨组分深部组合位于截断面外（手动通道 md §三）
  （锚：跨 3 组分 3 断 2 成（断 S-H、断 C-O、断 Pα-O 桥；成 C-S、成 Pα-O 羧酸氧），羧酸一个 O 转入 AMP 磷酸；CoA/ATP 大量候选键空间中位于截断面外）
- Codex 二读：（该件未抽入其二读样本，无判定）

分歧焦点：邻氨基苯甲酸+CoA+ATP 三组分连接（3 断 2 成）——组合在枚举序深部被截断埋掉（过=误拒）还是跨组分成键属混源拒因（拒）？

### B-4 `b-886394e1b7442ec9`

**材料**
- 题底物（substrate_smiles）：`O=C([O-])Cc1ccccc1`
- 证据记录：record_key `rhea:20957@L5791`（channel=corpus，family=酰基族(CoA)）
- 证据 donor：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCS`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=C([O-])Cc1ccccc1`
- 证据 product：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)Cc1ccccc1`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=P([O-])([O-])OP(=O)([O-])O`
- 模板：（空，本通道该件无模板证据）

**机器判定分歧**
- mimo 主判（免费线）：**reject_correct** —— 命中②组分混源：苯乙酰-CoA(产物[0] NCCSC(=O)Cc1ccccc1) 由 CoA(donor[0] NCCS) 与 苯乙酸(donor[2] 羧基) 两组分键连(C-S 酯键把苯乙酰连到 CoA S)，无法单源对应(RDKit 任意键骨架匹配判跨组分融合)；截断与否不改判。
- mimo 手动通道：**pass_expected** —— ③可行且无独立拒因、多中心/跨组分深部组合位于截断面外（手动通道 md §三）
  （锚：腺苷酸化模式：羧酸氧跨组分转入 AMP 磷酸，多键组合在枚举序深部）
- Codex 二读：**reject_correct** —— ①可将 donor[2] 苯乙酸酰基接到 donor[0] CoA 的 S，并将 ATP 对应 AMP 与焦磷酸；命中②：product[0] 的 CoA 骨架与苯乙酰基来自不同 donor，不能单源对应。

分歧焦点：苯乙酸+CoA+ATP 腺苷酸化连接（codex 二读也判拒、与主判一致；手动通道判过）——三判读者两票拒一票过，请裁定。

### B-5 `b-35b8404e4837331b`

**材料**
- 题底物（substrate_smiles）：`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)c1ccc(Cl)cc1`
- 证据记录：record_key `rhea:23222@L6874`（channel=corpus，family=酰基族(CoA)）
- 证据 donor：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)c1ccc(Cl)cc1`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=P([O-])([O-])OP(=O)([O-])O`
- 证据 product：`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCS`；`Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O`；`O=C([O-])c1ccc(Cl)cc1`
- 模板：（空，本通道该件无模板证据）

**机器判定分歧**
- mimo 主判（免费线）：**reject_correct** —— 命中②组分混源：ATP(产物[1] COP OP OP) 由 AMP(donor[1]) 与 焦磷酸 PPi(donor[2]) 两组分键连(AMP 与 PPi 缩合成三磷酸)，无法单源对应(RDKit 任意键骨架匹配判跨组分融合)；截断与否不改判。
- mimo 手动通道：**pass_expected** —— ③可行且无独立拒因、多中心/跨组分深部组合位于截断面外（手动通道 md §三）
  （锚：连接酶逆向：断 C-S、断/重排 AMP Pα-O，成 C-O(H)、成 Pα-O-Pβ 桥；跨三组分键组合被 64 上限截断）
- Codex 二读：（该件未抽入其二读样本，无判定）

分歧焦点：连接酶逆反应（4-氯苯甲酰-CoA→CoA+ATP+酸）——跨三组分键组合被截断（过=误拒）还是混源（拒）？

---

## 回传方式

12 行裁定（格式同上）原文交回即可——主会话落盘存证，并作为：①A 通道判读规则 v3 的校准样例；②师姐确认记录（pass_expected 件的最终分子以师姐确认为准）。本包全部材料零金标零题面，可外发。
