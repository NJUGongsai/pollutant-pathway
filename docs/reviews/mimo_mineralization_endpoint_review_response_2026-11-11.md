# 通道复审回应：微生物降解路径「完全矿化终点标志（ppv1-mineralization-sink-v1）」化学判据审查

- **审查时间**：2026-11-11
- **审查通道**：通道 B（Codex CLI / gpt-6.1-sol 只读沙箱模式，因 opencode free 额度受限按 AGENTS.md 规程自动切入）
- **题域与金标状态**：零金标、零测试集题面 SMILES、纯规则级化学拓扑审查
- **采信原则**：结论采信到与源码及公开复现互证的程度为止

---

CC，结论：**R1 小修；R2、R3 存在阻塞项，当前规则不宜冻结。** 本次只核对规则和公开资料，未执行代码；程序是否落实这些规则，均**待执行验证**。

1. **[R1 化学审查]：`MINOR_SUGGESTION`**

   一碳拦截方向正确，但应明确写成：**除精确命中 A 的 CO₂、碳酸及其去质子化态外，其他含碳物种默认继续追踪。** 这样，光气、二硫化碳、羰基硫、异氰酸酯、甲酰胺都会被拦住，不必靠不断补长黑名单。这里真正兜底的是 A/B 精确白名单；甲酰胺等物种并不一定命中 R2 的毒害基团表。

   两处结构示例需要更正：`N=C=O` 表示中性的异氰酸，`N#CS` 表示中性的硫氰酸；对应阴离子可写作 `N#C[O-]`、`N#C[S-]`。酸、阴离子及允许的共振写法都应覆盖。[ChEBI：氰酸根](https://www.ebi.ac.uk/chebi/CHEBI:29195)、[硫氰酸根](https://www.ebi.ac.uk/chebi/CHEBI:18022)

   A 必须比较**完整分子身份**，不能仅因分子含碳酸酯片段就放行；A0 也只表示没有碳分支，不表示已经无害。

2. **[R2 化学审查]：`BLOCKER`**

   **确定漏洞是立体身份丢失。** `InChIKey-14` 不编码顺反和手性，追加分子式也补不回来。[InChI 官方说明](https://www.inchi-trust.org/technical-faq/)

   | 核对对象 | 审查结论 |
   |---|---|
   | cis-/trans-aconitate | 两者均为 `GTZCVFVGUGFEME`、`C6H6O6`；现匹配规则会把未列入的反式与指定顺式混同。[顺式](https://www.ebi.ac.uk/chebi/CHEBI:32805)、[反式](https://www.ebi.ac.uk/chebi/CHEBI:32806) |
   | fumarate / maleate | 前 14 位和分子式相同。“排除显式 Z”仍不足以处理未标顺反者；应要求已确认的 E 构型。[富马酸](https://www.ebi.ac.uk/chebi/CHEBI:18012)、[马来酸](https://pubchem.ncbi.nlm.nih.gov/compound/444266) |
   | succinate / methylmalonate | 同分子式、不同连通性，现方法能够区分，**不是误放行反例**。[琥珀酸](https://pubchem.ncbi.nlm.nih.gov/compound/1110)、[甲基丙二酸](https://www.ebi.ac.uk/chebi/CHEBI:30860) |
   | malate、isocitrate 等手性物 | 必须登记允许的构型；不能把同连通性的全部立体异构体自动视为同一个宿主中心池。 |

   还须修正“maleate 水合为 malate 即可”的表述：maleate hydratase 对应 **D/(R)-malate**，TCA 的 fumarase 对应 **L/(S)-malate**。前者能否作为该宿主的汇入口，需要另有依据。[IUBMB：maleate hydratase](https://iubmb.qmul.ac.uk/enzyme/EC4/2/1/31.html)、[fumarase](https://iubmb.qmul.ac.uk/enzyme/EC4/2/1/2.html)

   最小修订是：保留酸碱归一，增加完整结构及许可立体匹配；必需构型缺失时给 `unknown` 或继续追踪。丙酮酸、乙酸、乙酰乙酸等的**不同连通性异构体**，不能仅因分子式相同就视为上述风险。

   `succinate semialdehyde`、`3-hydroxybutyryl-CoA`、`crotonyl-CoA`、`malonyl-CoA` 保持继续追踪是合理的保守选择，**不构成必须扩表的遗漏**；已知后续反应可以进入现有白名单，但是否具备相应宿主通路不能仅凭名称保证。[半醛→琥珀酸](https://iubmb.qmul.ac.uk/enzyme/EC1/2/1/24.html)、[malonyl-CoA→acetyl-CoA](https://iubmb.qmul.ac.uk/enzyme/EC4/1/1/9.html)

   **结论范围也须写清：到达 B 只证明进入指定中心代谢池，不能证明已经完全矿化。** 含 B 的闭合应明确标注为“中心代谢汇入代理指标”，并与全部进入 A 的无机碳闭合区分。[OECD 有氧矿化定义](https://www.oecd.org/content/dam/oecd/en/publications/reports/2004/11/test-no-309-aerobic-mineralisation-in-surface-water-simulation-biodegradation-test_g1gh4b4a/9789264070547-en.pdf)

3. **[R3 化学审查]：`BLOCKER`**

   全分支追踪方向正确，但**`coproduct` 标签不能证明碳来自内源**。一个可核查的规则反例是：外源腺嘌呤可经核苷酸补救反应进入 AMP；若 AMP 被标成副产物便直接排除，就可能漏掉污染物来源碳。这说明规则存在缺口，尚不代表程序已发生该误判。[IUBMB：腺嘌呤磷酸核糖转移酶](https://iubmb.qmul.ac.uk/enzyme/EC2/4/2/7.html)

   建议辅因子排除必须同时满足：**完整结构精确命中；反应物端有已登记的内源辅因子及相符的转化、计量关系；碳来源记录证明该产物实例不含污染物碳。** 输入污染物本身就是核苷酸或辅因子时，以及上游污染物碳已进入这些分子时，均不得因改标副产物而豁免。来源无法证明就保留分支，给 `unknown/partial`。

   腺嘌呤、尿嘧啶本身不在精确名单中，不能声称它们会被该名单直接排除。同样，载碳 THF、GSH 结合物和酰基-CoA 不等于游离 THF、GSH、CoA-SH；禁止按辅因子名称或局部骨架扩大豁免。