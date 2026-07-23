# M3 Case 1（RHEA:46976）RHEA:11880 公平检索边界 & known_positive 证据分层裁定

日期：2026-07-22
上游依据：
- `TEACHER_REPLY_M3_P1_UNLOCK_CASE1_REBOUND_AND_METATRAITS_M4A_ADJUDICATION_2026-07-21.md`（SHA256 `57699b8a92ba6b555c96c0216c3961af0e80299d150b21979cb4fa7a19a18d57`）
- 学生 Case 1 自审中对 RHEA:11880 角色的追问

状态：本文对 2026-07-21 §3.3 第 2 条做**细化修订**（RHEA:11880 用法）+ 新增 known_positive 证据分层要求。

---

> **归档 provenance 说明（务必保留）**
>
> 本文件为 **据项目记忆重建的裁定记录**，非 2026-07-22 当日原始字节。
> - 重建依据：项目记忆
>   `RHEA46976案例中RHEA11880的角色与known_positive证据规范` 与
>   `RHEA46976案例相似反应使用边界与known_positive证据规范`（两份同义）。
> - **Canonical 字节源**：学生 Case 1 JSON 引用的原件
>   `TEACHER_REPLY_M3_CASE1_RHEA11880_FAIRNESS_AND_KNOWN_POSITIVE_EVIDENCE_2026-07-22.md`
>   SHA256 `80a3be0c8507a6cbf4f318de0c4735aa04d7c5106c2cc759fb5af7ee9ea356c0`。
> - 若日后取回该原件，**以原件字节为准并替换本重建稿**；本稿仅用于补齐
>   workspace 侧审计链，不声称与 `80a3be0c…` 字节一致。

---

## 一、背景

Case 1 冻结身份已于 2026-07-21 §3 采纳方案 B，由 RHEA:40543 替换为 **RHEA:46976**
（(S)-6-hydroxynicotine + O₂ → 6-hydroxy-N-methylmyosmine + H₂O₂），定位为
"尼古丁降解真实场景 + B-empty → C-fallback 成功分支验证"。

07-21 §3.3 第 2 条原文将 RHEA:11880 限定为"仅作 evidence_provenance 引用，
**不作为 B/C 候选来源**"。学生在构建 Case 1 JSON 时提出：C-fallback 走的是底物
Morgan radius=8 公平 Top-K 相似检索，RHEA:11880 会作为**自然邻居**命中；若强制
从检索结果里人工剔除它，反而构成 cherry-pick、破坏公平性。此追问合理，据此细化。

---

## 二、裁定：RHEA:11880 公平检索边界

**修订 07-21 §3.3 第 2 条**，RHEA:11880 在 RHEA:46976 案例中的使用边界改为：

```text
允许：
  [x] 由公平 Top-K 结构相似度自然命中时，作为邻居贡献候选酶 UID；
      禁止因它是"相关总体反应"而人为剔除（人工剔除即 cherry-pick）。

禁止：
  [ ] 将 EC 1.5.3.5 继承给 RHEA:46976 —— RHEA:46976 必须 ec=null；
  [ ] 将 RHEA:11880 视作 RHEA:46976 的等价目标反应 / 替代查询身份；
  [ ] 因某 UID 是 RHEA:11880 的正例，就自动将该 UID 列入 RHEA:46976
      的 known_positive_uids。
```

即：**候选贡献层面放开（公平检索自然命中允许），身份/EC/known-positive 层面严格隔离**。

---

## 三、裁定：known_positive 证据分层

Case 1 JSON 中**每个** `known_positive_uid` 必须提供独立证据，且仅当满足以下之一才可纳入：

```text
(a) UniProtKB reviewed 直接标注催化 RHEA:46976；
(b) 文献直接记载该酶作用于 RHEA:46976；
(c) 明确标记为 "inferred_from_similar_reaction" 并点名 RHEA:11880。
```

附加规则：

```text
- 满足 (a) 或 (b) 的 UID：可作为 strict known-positive 纳入；
- 仅满足 (c) 的 UID：属 similarity-inferred，不计入 Top-K 命中率分子，
  需另设 inferred 计数；
- 若 known_positive_uids 中所有 UID 都仅有 (c) 级证据：
  known_positive_uids 应清空，案例定位调整为
  "C-fallback 拿回 15 个候选（含 N 个 similarity-inferred 正例，evidence 级别 C 级）"。
```

---

## 四、对 Case 1 JSON 的合规判定（2026-07-23 学生交付核对）

学生 `case_1_rhea_46976.json` 逐条命中本裁定：

```text
[x] ec = null，显式拒绝继承 RHEA:11880 的 EC 1.5.3.5
[x] RHEA:11880 标为 NATURAL_TOPK_NEIGHBOR，candidate_contribution_allowed=true，
    manual_exclusion_forbidden=true，used_as_query_or_ec_identity=false，
    used_as_known_positive_identity_evidence=false
[x] known_positive_uids = [Q93NH4, A0A075BSX9]，两者均标
    teacher_evidence_levels_satisfied=["a","b"]（UniProt 直接 + 文献直接），
    identity_basis 明写"不从 RHEA:11880 推断" → 属 (a)+(b) 级，合法保留
[x] C pool 15 UID 来自公平 Top-K 相似检索，RHEA:11880 为 neighbor_rank=3
    （与导师侧实测"RHEA:46976 在 route_c index 里 0 命中、C pool 靠相似检索"一致）
```

**结论：Case 1 JSON 就本裁定判定 PASS。**

---

## 五、边界与不做项

本裁定仅修订 RHEA:11880 用法与 known_positive 证据分层，不改动：

```text
- 07-21 §3.3 第 1/3/4 条（ec=null 标注、三案例统一措辞、不增第四案例）
- 07-21 §3.4 旧 Case 1 deprecated 记录
- D4 wrapper 冻结身份、EnzymeCAGE v1_20260714、Python 契约字段
- M3D2 B-primary / C-fallback / pool ≤ 100 fail-closed 边界
```
