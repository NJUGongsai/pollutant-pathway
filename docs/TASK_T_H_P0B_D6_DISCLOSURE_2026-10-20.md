# 任务书 — T-H P0b/D-6 旁路披露与零漂移门（2026-10-20）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 全部读数只在该题域成立。
>
> **授权链**：
> 1. CC 2026-10-20：「开始做，然后直接推进到 P2；需要我/师姐裁决的由 Codex 代为裁决，
>    Codex 的裁决即为最终裁决」；
> 2. Codex 审核报告 `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md`：本轮唯一最高优先=
>    **P0b/D-6 旁路披露**；**不加对账硬门**；D-2 选为第一个选择层实验方向但需本门通过后才动；
> 3. 本任务书把上述决定落成可执行范围。**Codex 对本任务的实施审结论为最终裁决**（代 CC/师姐）。
>
> **性质**：代码改动（诊断字段）+ 合成正负控 + 正式零漂移回放门。
> **禁止**：对账硬门、候选/池/检索/排序改变、评分改变、v3 promotion、D-3/D-7 修复、付费批。
> **成本**：零模型调用、零 HPC 作业、零付费；仍需工程时间。

## 0. 一句话

在**独立 checkout** 里给已提交事件加一组**旁路诊断字段**（声明产物 vs 执行碎片、主产物归属、
copy 来源、proof_scope、四态），用合成正负控证明不误伤合法多碎片/合法 copy/立体差/unknown，
再用**冻结历史输入与响应**做回放：**剔掉新字段后，候选成员、事件身份/内容/顺序、位次、
评分语义零漂移**，并复现 **hit@1=89、strict=126、partial=53、unmatched=119**。
本任务**不改提交、不改判分、不加硬门**。

## 1. 起点与输入

| 项 | 值 |
|---|---|
| 基线 commit | `c9c6c7a7ae02b46769add09fbc2536323ce8a985`（HEAD；科学 src 与 T-H 相同） |
| 基线结果 | v2 headline 89/298；hit@3 118、hit@5 125；strict 126；partial 53；unmatched 119 |
| 批根（只读，555/444） | `~/ppv1_hpc/batch/t_h_s5b_298_20261020r2` |
| runs 根（可读） | `~/ppv1_hpc/runs/t_h_s5b_298_20261020r2` |
| 本地镜像 | `reports/ppv1_s5b/t_h_2026-10-20/r2/` |
| P0 证据 | `docs/review_evidence/t_h_p0_2026-10-20/`（22 件，SHA256SUMS） |
| Codex 审核 | `docs/T_H_P0_DECISION_CODEX_REVIEW_2026-10-20.md`（必读） |
| 代码位置 | `src/pathway_v43/pollutant/{native_result,native_export}.py`、`s5b_builder.py`、`s5b_compiler.py`、`production.py`（及实际字段消费链） |

## 2. 非目标（写死，不做）

- **不做**一致性硬门；不拒绝候选；不改变 admission/排序/评分。
- **不做**候选/池/检索/编译准入改动；不修 D-3 delta、不修 D-7 route。
- **不做** v3 归一 promotion；不重判、不回写旧成绩。
- **不做**原始模型响应考古；旧 rank 原始来源无法恢复就写 unknown。
- **不跑** HPC 作业、不调模型、不 push、不读金标/题面/reference_graphs/llm.env。

## 3. Phase A：先冻结合同（实施前）

产出一份 `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md`，冻结以下字段与语义（只写字段、状态、边界，
不写化学结构正文）：

| 合同项 | 必须写清 |
|---|---|
| origin | 事件来源（recorded/template/novel 等），与既有字段同源 |
| 结构身份版本 | 使用哪一版严格身份/规范化；不得新造第二套 |
| 主产物 | 如何认定 principal product；多主产物/无主产物如何记 |
| 实际生成组分 | 执行碎片的多重集；与声明组分的对应关系 |
| copy 来源 | copy 组分是否经执行通道；合法 copy 如何不判为不一致 |
| 执行/装配边界 | 哪些组分由 edits 生成、哪些由装配/记录侧声明；边界不明记 unknown |
| 适用性 | `applicable / not_applicable` 的判定；空声明、解析失败、未核执行范围 |
| proof_scope | 本次对账能证明什么、不能证明什么（不扩成机制/生物可行性） |
| 四态 | `consistent / inconsistent / unknown / not_applicable` 的互斥定义 |
| unknown_reason | 缺字段、解析失败、边界不明、未核范围等枚举 |

**合同门**：合同必须能被 Codex 按 §7 审核；未过合同门不得进入 Phase B 的实现合并。

## 4. Phase B：独立 checkout 实现诊断字段

### 4.1 工作方式

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
git worktree add /tmp/dependingv43_p0b c9c6c7a7ae02b46769add09fbc2536323ce8a985
# 所有代码改动只在 /tmp/dependingv43_p0b；主树不动
```

- 只新增**本任务必要**的诊断字段与 schema/版本承载；按既有五处及实际消费链列允许字段对照。
- 诊断字段默认**旁路**：不得改变候选成员、事件提交、排序、admission、评分。
  若必须改 schema，提供**开关**（默认关闭）与版本号；开关关闭时行为逐字节等价。
- 共用既有来源，不新造第二套身份/规范化；不扩成新阶段机制证明或全面重构。
- 测试：新增/修改测试只覆盖本任务字段与开关；不得改既有断言口径。
- 交付形式：**patch + 测试证据 + 合同**；主树在 Codex 审核通过前不合并。

### 4.2 允许改动的文件（白名单）

- `src/pathway_v43/pollutant/native_result.py`
- `src/pathway_v43/pollutant/native_export.py`
- `src/pathway_v43/pollutant/s5b_builder.py`
- `src/pathway_v43/pollutant/s5b_compiler.py`
- `src/pathway_v43/pollutant/production.py`
- 对应 tests（只新增本任务测试）
- 若实际消费链还需要一处，先在合同里列出并说明理由；**不得扩到评分/检索/池策略**。

## 5. Phase C：合成正负控（本地，零模型）

至少覆盖：

| 控制 | 期望 |
|---|---|
| 合法主产物 + 多碎片 | `consistent` 或 `unknown`，不得误判 `inconsistent` |
| 合法 copy（21 条正控类型） | `consistent`/`not_applicable`，不得因 copy 判不一致 |
| 仅立体差 | 按合同归 `inconsistent` 的立体子类；不得与“结构不同”混为一类 |
| 明确声明矛盾 | `inconsistent`，reason 指向具体字段 |
| 解析失败 | `unknown`，不得洗成 `consistent` |
| 空声明 | `not_applicable`/`unknown`，按合同 |
| 未核执行范围 | `unknown`，保留 proof_scope |
| 开关关闭 | 与基线逐字节等价 |

**负控不得全面拒绝换通过**：合法正控必须保留；unknown 必须保留。

## 6. Phase D：正式零漂移回放门（本任务完成门）

用**固定历史输入/已保存响应/批内环境**（优先 `venv_v44run`，RDKit 2026.03.5）做诊断开关回放：

1. **剔掉新字段后**逐项比较：
   - 候选成员（池/spec 身份与顺序）；
   - 事件身份/内容/顺序（1586 条）；
   - 位次（strict rank 126 条逐条）；
   - 评分语义（桶、hit@1/@3/@5、strict/partial/unmatched）。
2. **复现锚点**：`hit@1=89`、`strict=126`、`partial=53`、`unmatched=119`；
   hit@1 是 strict 子集，不可混算。
3. 开关关闭 vs 开启：除新增字段外，上述四项**零漂移**。
4. 产出 `p0b_replay_evidence/`：逐项 diff 表、rank 对照、事件集合对照、SHA256SUMS。

**未过此门 ⇒ 不合并、不启动 P1/P2。**

## 7. 审核与裁决（Codex 代 CC/师姐，最终）

1. 提交合同 + patch + Phase C/D 证据给 Codex 审核；
2. Codex 的结论（放行/需修正）为**最终裁决**；
3. 放行后才允许：主树合并（单独 commit）、进入 P2 的离线实施书；
4. 若 Codex 要求修正，按它的清单回修；**不得自行降级门或扩大范围**。

## 8. 红线

1. 不改主树（除审核通过后的合并提交）；不在 `/tmp/dependingv43_p0b` 之外改代码。
2. 不碰封存批根；不写 runs 根；不 push。
3. 不读金标/`reference_graphs`/`questions.jsonl`/`llm.env`/私钥；不输出化学结构正文。
4. 不把“声明≠执行”写成“化学错误”；不把 unknown 洗成通过；不承诺收益。
5. 任何超出白名单的改动 ⇒ 停报，不自行扩权。

## 9. 交付物

| 件 | 路径 |
|---|---|
| 合同 | `docs/T_H_P0B_D6_CONTRACT_2026-10-20.md` |
| 实施报告 | `docs/T_H_P0B_D6_IMPL_2026-10-20.md` |
| patch | `docs/review_evidence/t_h_p0b_2026-10-20/*.patch` |
| 合成正负控 | 证据目录，含 8 项控制与输出 |
| 零漂移回放 | 证据目录，含逐项 diff/rank/事件对照 + SHA256SUMS |
| 审核请求 | `docs/T_H_P0B_D6_CODEX_REVIEW_REQUEST_2026-10-20.md` |

## 10. 验收（主窗口/Codex）

- 合同完整、四态互斥、proof_scope 明确；
- 白名单内改动；开关关闭与基线零漂移；
- 8 项合成控制通过，合法正控保留、unknown 保留；
- 正式门复现 89/126/53/119，逐项对照齐全；
- 未做硬门/未改判分/未扩范围；
- Codex 审核结论为最终裁决。

## 11. 与后续的关系

- 本任务通过后：按 Codex 决定进入 **D-2 证据卡 v2 离线实施书**（只按冻结 S1 字段实施，
  不塞 D-1/D-3/D-7/对账硬门）。
- P2 付费配对批仍需：独立预注册 + token 门 + 全部 298 题配对统计 + CC/Codex 的代决签字。
- T-I 先于 P2；本任务与 T-I 并行不冲突（零模型、零付费、独立 checkout）。