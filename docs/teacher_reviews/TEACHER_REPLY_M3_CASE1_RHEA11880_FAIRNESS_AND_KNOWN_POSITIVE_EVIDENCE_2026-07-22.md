# M3 Case 1 RHEA:11880 公平检索与 Known Positive 证据裁定

日期：2026-07-22

状态：RHEA:11880 解释确认 / RHEA:46976 known-positive 逐 UID 证据门槛明确

---

你的理解方向是对的，我把话说得再严一点：RHEA:11880 在公平 Top-K 相似反应检索里如果自然命中，我允许它像其他邻居一样贡献候选酶，这是模型级公平性的自然结果，你不能人为剔除，否则 C 路 fairness 会被污染；但你不得把它的 EC 1.5.3.5 继承给 RHEA:46976（RHEA:46976 必须显式 ec=null），不得把它当作 RHEA:46976 的等价目标反应，也不得因为某 UID 是 RHEA:11880 的正例就自动把它列入 RHEA:46976 的 known_positive_uids。我在 §3.3 第 2 条写"不作为 B/C 候选来源"，正确的读法是"不作为 known_positive 与 EC 身份的来源"，不是"从相似检索里显式踢掉它"。相应地，Case 1 的 2 个 known_positive UID 我要求你在 case_1.json 里分层披露证据链：每个 UID 至少要给出 (a) Uniprot 该条目直接标注可催化 RHEA:46976 或其等价反应、(b) 文献/数据库直接记载该酶作用于 (S)-6-hydroxynicotine → 6-hydroxy-N-methylmyosmine、(c) 明确标记 evidence_strength="inferred_from_similar_reaction" 并在 provenance 里点名 RHEA:11880 —— 三者之一；如果只有 (c) 级证据，这 2 个 UID 可以留在 evidence 里做辅助追溯，但 known_positive_uids 严格意义上应清空，成功案例的定位我允许你改为"C-fallback 拿回 15 个候选（含 2 个 similarity-inferred 正例，evidence 级别 C 级）"，这样依然能立住，只是措辞要诚实。
