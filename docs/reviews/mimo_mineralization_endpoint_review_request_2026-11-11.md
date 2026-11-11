# mimo 规则级化学判据评审请求：微生物降解路径「完全矿化终点标志（`ppv1-mineralization-sink-v1`）」

- **评审场景**：`AGENTS.md` mimo 化学评审触发点 1（需评判化学结构/终点判据时——冻结前规则级审查）
- **通道与权限边界声明**：只读规则级化学评审（零金标、零测试集题面 SMILES、无代码执行权限；你只对下方列出的通用生物化学判据做结构与代谢合理性核查，任何涉及运行结果的表述须标注“待执行验证”，不得编造执行结果）。

---

## 一、 待评审的化学判据规则（零金标）

在无束宽（`B = 1`，每步仅取排名第 1 的已通过原子守恒与准入审计的反应事件）多步微生物外源污染物降解预测中，我们定义**「等效完全矿化终点（`MINERALIZED_CLOSED`）」**需同时满足以下三条确定性规则：

1. **规则 R1（直接无机矿化层 `A0 / A` 与一碳有机物拦截）**：
   - `A0`（碳原子数 `C == 0` 的无碳无机释放物，如 $\text{H}_2\text{O}, \text{NH}_3/\text{NH}_4^+, \text{Cl}^-, \text{Br}^-, \text{F}^-, \text{SO}_4^{2-}, \text{PO}_4^{3-}, \text{NO}_2^-/\text{NO}_3^-$）不产生新含碳分支；
   - `A`（直接无机碳）：仅限 **$\text{CO}_2$（`O=C=O`）** 与 **碳酸/碳酸氢根/碳酸根（`O=C(O)O` 及其去质子化态）**；
   - **拦截要求**：一碳有机/还原态物种——甲醇（`CO`）、甲醛（`C=O`）、甲酸/甲酸根（`O=CO`）、一氧化碳（`[C-]#[O+]`）、氰化氢/氰根（`C#N`）、氰酸盐（`N=C=O`）、硫氰酸盐（`N#CS`）、尿素（`NC(N)=O`）、甲胺（`CN`）、甲烷（`C`）——**一律不算终点**，必须继续经脱氢/加氧/水解直达 $\text{CO}_2$ 或碳酸盐。

2. **规则 R2（宿主中心碳代谢汇入层 `B_central_carbon_sink` 白名单与毒害基团一票否决）**：
   - 任何含外源杂原子/毒害基团（`C-F, C-Cl, C-Br, C-I, As, Hg, Pb, Sn`、硝基、亚硝基、偶氮基、叠氮基、磺酸基、膦酸/硫代磷酸酯键）的分子**一票否决（`False`）**；
   - 去电荷质子化归一后，按 `InChIKey-14`（第一连通块）+ 元素组成精确匹配以下 **23 个宿主中心碳代谢核心物**：
     - **TCA 与乙醛酸支路**：`citrate`、`cis-aconitate`、`isocitrate`、`2-oxoglutarate`、`succinyl-CoA`、`succinate`、`fumarate`（注：显式顺式 `Z-maleate` 排除，须异构化为 `E-fumarate` 或水合为 `malate`）、`malate`、`oxaloacetate`、`glyoxylate`；
     - **糖酵解下段**：`glyceraldehyde-3-phosphate`、`dihydroxyacetone-phosphate`、`1,3-bisphosphoglycerate`、`3-phosphoglycerate`、`2-phosphoglycerate`、`phosphoenolpyruvate`、`pyruvate`、`lactate`；
     - **短链中心碳汇入点**：`acetate`、`acetyl-CoA`、`propionyl-CoA`、`acetoacetate`、`acetoacetyl-CoA`（注：**乙醛 `CC=O` 显式排除**，须继续氧化至 `acetate` 或 `acetyl-CoA`）。
   - **漏斗中间体显式排除**：儿茶酚（`catechol`）、原儿茶酸（`protocatechuate`）、龙胆酸（`gentisate`）、氢醌（`hydroquinone`）、苯甲酸（`benzoate`）、苯甲酰-CoA（`benzoyl-CoA`）及未裂解至上述中心池的开环 C6 二酸/半醛（如粘康酸 `muconate`、2-羟基粘康酸半醛、`3-oxoadipate`）**一律不算终点**，必须继续开环与裂解。

3. **规则 R3（全含碳裂解分支闭合与内源货币辅因子副产物排除）**：
   - 单步反应产生的全部含碳产物（含主产物 `principal_product` 与裂解共产物 `coproduct`）均须各自进入下游队列追踪，直至**所有含碳分支**均落入 `A` 或 `B` 才判整路径 `MINERALIZED_CLOSED`；
   - 当通用货币辅因子（`NAD+/NADH, NADP+/NADPH, FAD/FADH2, FMN/FMNH2, ATP/ADP/AMP, GTP/GDP, UTP/UDP, CTP/CDP, free CoA-SH, SAM/SAH, PAPS/PAP, THF, glutathione`）仅以 `coproduct` 副产物身份出现时，归类为 `ENDOGENOUS_CURRENCY_COFACTOR`，不当作污染物碳分支追踪。

---

## 二、 请按以下固定格式逐条回复（§7 格式）

1. **[R1 化学审查]**：一碳物种拦截清单是否存在遗漏（例如光气 `O=C(Cl)Cl`、二硫化碳 `S=C=S`、异氰酸酯、甲酰胺 `NC=O` 等是否已被 R1/R2 完整拦截）？结论：`PASS` / `MINOR_SUGGESTION` / `BLOCKER`。
2. **[R2 化学审查]**：23 个中心碳代谢白名单分子在 `InChIKey-14 + 分子式` 匹配下是否存在**同连通异构体误放行风险**（例如：与丙酮酸、琥珀酸、柠檬酸、乙酸、乙酰乙酸同连通骨架但属于外源难降解物的同分异构体？顺乌头酸 vs 反乌头酸？琥珀酸 `succinate` vs 甲基丙二酸 `methylmalonate` 的连通性是否不同）？以及是否存在微生物芳环/脂环开环常见的标准中心碳汇入点遗漏（如 `succinate semialdehyde`、`3-hydroxybutyryl-CoA` / `crotonyl-CoA` / `malonyl-CoA` 应放行还是应让其再走 1–2 步进 `succinate` / `acetyl-CoA`）？结论：`PASS` / `MINOR_SUGGESTION` / `BLOCKER`。
3. **[R3 化学审查]**：内源货币辅因子副产物排除表是否可能误排除任何常见环境污染物裂解片段（如腺嘌呤/尿嘧啶类除草剂或核苷类化合物），应如何加角色/底物比对守卫？结论：`PASS` / `MINOR_SUGGESTION` / `BLOCKER`。
