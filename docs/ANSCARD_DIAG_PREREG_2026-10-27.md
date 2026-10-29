# 预注册：答案卡诊断批（金标入卡 · 独立诊断）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）；本批另加 [答案卡诊断] 标签——
> 结果是诊断读数，不得作为 hit@1 成绩引用、不得对外发布。**
> CC 2026-10-27 拍板（对话原文："给产物 我们不后面评价是看是否写对了完整反应吗"）。
> **金标外发确认：CC 已明确拍板**——参考反应内容（产物 SMILES/参与物/官能团变化）随 API
> 载荷发给 DeepSeek 服务端，仅限本批、仅限此用途。

---

## 1. 要回答的问题

给模型**唯一一条"答案卡"**（正常证据卡 schema，内容 = 该题正确反应：反应类型 + 官能团变化
+ 参考产物 SMILES + 参与物描述），模型能否写出**通过 strict 判定的完整反应**？

- 写对率高 ⇒ 失分在"没给对信息"（选择/供给层）；
- 写不对 ⇒ 失分在转录/组装层（模型看到答案也转写不出合规事件）——新修复面。

## 2. 设计

| 项 | 定案 |
|---|---|
| 范围 | **172 道失分题**（P2 A 臂 `p2-298-20261026` v2 口径：119 unmatched + 53 partial） |
| 唯一变量 | 证据卡内容 = 单条答案卡（池只留这一条候选）；prompt 模板 `c24bee42…`、模型 `deepseek-v4.1-flash-1017`、判分 v2、卡格式 schema 全部不变 |
| 答案卡构造 | 从 `reference_graphs` 反构造单条 spec：`product_smiles`/`coproducts` 取参考值；`transformation_ref` 用合成标记 `oracle-diagnostic:<ref>`；`evidence`（edit_summary/participants/conditions 等五字段）用仓内同一纯函数从反构造 spec 计算；底物级 `substrate_evidence` 照常（零金标） |
| 判分 | 照常 v2；指标名 **"答案卡转录命中率"**（172 题内 strict 通过数），与 P2 A 臂同题逐题配对 |
| 对照 | P2 A 臂同 172 题基线（全为失分：unmatched/partial） |
| batch_tag | `anscard-diag-20261027`（新批根，不撞任何既有批） |

## 3. 流程门

1. 构造脚本（零 LLM）产出 172 张答案卡 → **人工核对卡格式与正常运行逐字段一致**（仅内容为答案）
2. smoke 5-10 题：零管线失败、判分链跑通，卡内容抽查
3. full 172 → score（v1+v2）→ 配对与逐题归因报告

## 4. 红线

- 判分器两哈希冻结不变（`evaluation.py=37c09231…`、`s5b_scoring.py=4af3ed2d…`）
- 不碰 P2 批根/封存批/金标目录（只读消费 reference_graphs 构造卡）
- 本批所有数字带 [答案卡诊断] 标签；金标内容不得写入任何报告正文（报告只写 qid 级结果）
- 解读：跑完看数据（CC 拍板不预写阈值）
- 不 commit/push；费用 ~2.3M tokens 逐批记账

## 5. 产出

- `docs/ANSCARD_DIAG_RESULT_2026-10-27.md`（转录命中率 + 逐题配对 + 写错样本的四层归因）
- 证据目录 + SHA256SUMS；notebook `iter/anscard/`
