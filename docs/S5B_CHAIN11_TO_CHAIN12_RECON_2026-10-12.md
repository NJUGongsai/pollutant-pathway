# chain11 → chain12 逐题迁移对账（2026-10-12）

> 题域标签：**298 / RHEA 通用酶学 / 已见题**。对外引用一律带此标签，不外推 dev 题域。
> Provenance：数据 = 本地已同步判分产物（`reports/ppv1_s5b/chain11_s5b_298_v4_20261010/metrics.json` md5 `7c59edd5ac9ccea5421b203883c9483a`；`chain12_s5b_298_v4b_20261012/metrics.json` md5 `1f826b932e109fc688e004bcbdaf7c21`）；逐题明细 = 两批 `synced/`（cases + native_export payload，远端 md5 抽查一致）；脚本 `/tmp/recon_c11_c12/{reconcile,scan_attr,attr_map2,spot}.py`（零模型、零网络、只读；未读取金标/题面内容）。对账代理执行，主会话核对落盘。

## 0. 一句话结论

聚合数字全部复核无误；净增主要由 uncovered 大规模流出驱动（→strict 32、→partial 11）；归因抽查发现 **hwall（显式氢墙）是新 strict 主力指纹（20/35），D2 直接指纹零道进 strict 且有 3 道旧 strict 被拉成 partial（诚实 coproduct 参与物 vs root-only 参考的 superset 判 partial 机制）**；chain11→chain12 实为多因子批次（compiler s5b-compiler-1→3，含 v4b 立体消解/推断映射深层门/诚实计量线 + D2-R1/R2/R3 + hwall + F3 词表），增益归因混有独立调模型的采样方差，以下所有"归因"均带此上界。

## 1. 聚合复核（全部对上）

| 指标 | chain11 | chain12 | Δ |
|---|---:|---:|---:|
| hit@1（严格口径） | 76 | 92 | +16 |
| hit@3 | 101 | 126 | +25 |
| hit@5 | 103 | 130 | +27 |
| U（strict 覆盖） | 106 | 130 | +24 |
| L = U−H5 | 3 | 0 | −3 |
| partial | 37 | 43 | +6 |
| uncovered | 155 | 125 | −30 |
| 老口径敏感性 @1/@3/@5 | 123/179/187 | 143/208/220 | — |

W0 诊断：U=130 < 150 ⇒ 方向指示仍为"优先供给/生成"。

## 2. 桶迁移矩阵（行=chain11，列=chain12）

| | strict | partial | uncovered | 行和 |
|---|---:|---:|---:|---:|
| **strict**(106) | 95 保留 | 4 | 7 | 106 |
| **partial**(37) | 3 | 28 保留 | 6 | 37 |
| **uncovered**(155) | 32 | 11 | 112 保留 | 155 |
| **列和** | 130 | 43 | 125 | 298 |

净变化：strict +24 = +32+3−4−7；partial +6 = +11+4−3−6；uncovered −30 = −32−11+7+6。

## 3. hit@1 迁移与退步题

2×2：保留 62 / **退步 14** / 新成功 30 / 双未 192（闭合 298）。hit@3 保留 89/退步 12/新增 37；hit@5 保留 93/退步 10/新增 37。

14 道 hit@1 退步题：7 道 strict→strict 掉位（rank1→rank2 ×5、→rank4 ×1，其中 2 道带 D2 指纹）、3 道 strict→partial（2 道带 D2 指纹）、4 道 strict→uncovered（1 道 c12 出现 valence 异常）。完整 qid 清单见附录 A。

## 4. 后位答案 rank 直方图（strict−hit@1=38）

rank2=23、rank3=11、rank4=1、rank5=3（和=38）。**L=U−H5=0：全部 strict 答案都在前 5 位内。**

## 5. 归因抽查（35 道新 strict：32 U→S + 3 P→S）

| 指纹 | 全量扫描（35 题） | 说明 |
|---|---:|---|
| hwall 间接指纹（c11 同题 AtomValenceException、c12 消失） | **20/35** | 全库该异常 52→16 题 |
| D2 直接指纹（declared_copy_components） | **0/35** | c12 全库 13 题、c11 全库 0 题 |
| 两者皆无 | ~15/35 | 多为模型候选差异（两链独立调模型） |

深查 6 题：090cdd（苯甲醇氧化→酮，c11 同通道 sanitize_failed、c12 编译成功排 rank1）**hwall 强证据**；439a1 方向一致未确证；e5bcf（P→S）为共底物参与物呈现差异所致、源头 unknown；22901/1629f 不可归因（候选差异）。

**D2 双刃发现**：13 道 D2 指纹题零道 strict；机制 = 事件诚实保留 coproduct 参与物 + 声明式拷贝产物后，参考为 root-only 视图时参与物覆盖变 superset ⇒ 按冻结判分规则判 partial。14 道退步中 4 道带此指纹。该现象与 GPT 分析 §3.3、D2 设计书"诚实拷贝型候选主要贡献 partial"的预期一致，量化首次落地。

## 6. partial 37→43 构成

旧 partial 保留 28；uncovered→partial 11；strict→partial 4。旧 37 道：→strict 3 / 保留 28 / →uncovered 6。

## 7. 对下游任务的含义

- **T3（partial 细分）**：43 partial 中 superset（多参与物）类预计占比可观（D2 双刃 + 共底物呈现差异），细分需区分 superset/partial_subset/身份差异，口径不变。
- **T6（重排摸底）**：对象更新为 chain12；38 题后位答案（rank2=23 大头）+ 14 道退步题的排序稳定性一起看。
- **供给方向**：U=130<150，W0 指示仍以供给/生成为主；125 uncovered 的漏斗账（T1b/T2）是主战场。

## 附录 A：14 道 hit@1 退步题 qid

（rank 掉位 7）RXNG_082f4c1a…caad、RXNG_18a3c06e…2737、RXNG_44411841…ad9de*、RXNG_45d8d90f…d182、RXNG_4c2cd0c3…af16、RXNG_9becc12f…5f81、RXNG_b978fd0b…d9b3*；（→partial 3）RXNG_0eda0ec3…1d7a*、RXNG_21ed83a6…bfc0*、RXNG_5d15fc19…31ff；（→uncovered 4）RXNG_341b958e…e969、RXNG_365fb0be…55c8、RXNG_5e9b5672…5de、RXNG_65536b46…749e。（*=带 D2 指纹）

## 勘误（2026-10-12 当日，T3 程序复现触发，主会话独立复核裁定）

§0"D2 直接指纹零道进 strict"行文口径松，需按两个口径分开读：

| 口径 | 正确表述 | 状态 |
|---|---|---|
| 事件级（本意，§5 表 0/35） | 35 道**新** strict 的命中事件 0 道来自 D2 拷贝候选 | ✅ 成立，NC-12 熔断（D2 拷贝候选事件恒 partial）不受影响 |
| 题级（字面误读） | "13 道指纹题零道 strict"**错误**：题桶实为 **8 strict / 4 partial / 1 uncovered**（多数为 D2 候选陪跑+他通道候选命中） | ❌ 原行文勿再引用 |

验证：主会话独立复现 13 题桶分布（metrics+payload 直查）；抽查 strict 指纹题 RXNG_0faafc67f…（rank1）命中事件 `coproduct_participants=[]`、非 D2 事件；T3 全量数据（analysis/partial_breakdown）证 4 道 partial 指纹题 4/4 落 superset 类。mimo r35 回应原文沿用了本报告原表述，其 M3/M5 结论不受影响（论证依据是 NC-12/T1′ 设计线与事件级数字），采信时以本勘误为准。40/43 partial 为 superset 的 T3 新数字见 analysis/partial_breakdown.md。

## 附录 B：35 道新 strict qid

见 `/tmp/recon_c11_c12/`（attr_marks.json）；U→S 32：0567e10c(rank3)/090cdd3b(1)/1629feef(1)/1de92ec1(1)/22901c4d(1)/248f2d71(1)/28cc9c75(5)/36c4cbdc(1)/3f134aaa(1)/439a1e93(1)/4609b23a(1)/4e05a0b8(3)/5048373e(1)/57e0d032(2)/582fbbca(1)/5975a922(1)/66ce382c(1)/6b806f47(1)/7265b8c5(1)/8bb56f09(1)/9c0a2d02(2)/a685d0ed(1)/b139babc(1)/b6f489e0(1)/bed2884c(1)/d30a28d0(3)/e11a1cac(2)/e47fbe85(2)/ebe7683e(1)/f8ce36a0(1)/fb86653f(3)/fea48338(1)；P→S 3：bcf26fbe(1)/ddbcc56d(2)/e5bcfa56(1)。
