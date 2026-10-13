# S5b 表示层与形式归一实验轮交付书（A+B，2026-10-13）

> 上游：编译漏斗决策备忘（docs/S5B_COMPILE_FUNNEL_DECISION_MEMO_2026-10-13.md）候选行动 A/B，CC 拍板"开干，RR A/B 发车缓"。两单零模型零网络零 LLM，主会话核对（qid 交叉亲自复算）。题域标签：**298 / RHEA 通用酶学 / 已见题**。

## 0. 一页结论

两条便宜线的实验账（候选≠题≠命中三层口径如实分开）：

| 线 | 层位 | 结果 | 性质 |
|---|---|---|---|
| **A：cn_only 43 题表示层分类** | 提交后身份层 | **便宜赢面 20 题**（互变异构 14 + 质子化写法差 6）+ 立体差 21（stereo 线靶面）+ 真结构差 2（无救） | 前者属**判据口径级**变更（动 strict 身份预处理），须预注册+用户/teacher 裁定 |
| **B：形式归一实验** | 提交前对齐层 | 82 行 → Uncharger 归一后**对齐恢复 64 行（L1-pure 58/58=100%）** → 编译层再拦 54 → **compiled 10 行/7 题**（产物正确性待下一层验证） | 记录侧盐式 vs 题底物酸式**死因坐实**；实施属检索/编译侧预注册级 |
| 合账 | — | 两层 qid 交叉仅 1 题，**基本可加：毛上限 26 题**（20+7−1） | 全为上限口径，兑现需裁定+逐层验证 |

## 1. A 单详情（cnonly_repr_classification）

- 43 题全闭合（UNKNOWN 0）；配对忠实性复核：44 个 cn_only 节点全部复刻判分器逻辑配到产物 state、strict 命中 0、identity_scope_cap 全 False（确认真·同分子式不同构，非许可封顶）。
- 分类判据次序：TautomerEnumerator 归一 → 芳香往返 → Uncharger/ChargeParent → 立体盲差单列（stereo_only_difference）→ 真异构。
- 抽查 8/8 机器分类与人工读图一致（结构图仅存 /tmp/cnonly_probe/spotcheck/，未入仓）。
- **边界**：互变归一"可救"前提是身份预处理引入互变归一且范围与参考口径相容——采纳与否属下一轮预注册的用户裁定，本分析未改任何判定。

## 2. B 单详情（form_norm_experiment）

- 三层账：82 行（L1-pure 58+L1-candidate 24）→ ① 归一后对齐通过 64（L1-pure **58/58 全恢复**；L1-candidate 仅 6/24）→ ② 公开编译入口 compiled 10（corpus 6+recorded 4，全属 L1-pure）。
- ①过②拦的 54 行新拒因接管：transform_unmapped 19、stereo_edit 13、product_set_mismatch 6、截断/芳香/歧义等——编译墙既有拒因，非归一引入。
- 救不动的 18 行（全 analog·L1-candidate）：NAD(P)⁺ 阳离子型 10（Uncharger 中和反而失配，需净电荷对齐策略）、两侧本就中性 7（互变/连接差）、底物 q=−2 一条。
- 负控双干净：82/82 变体原始形式基线对齐 0 匹配；recorded/corpus 原始映射基线全>0。过程抓过一个真 bug（库行 products 字段名致 recorded 假拒）当场修正为 product_smiles。
- 抽查 6/6（3 compiled 逐字核验 + 2 编译拦截 + 1 NAD⁺ 救不动）。

## 3. 预注册裁定点清单（本实验轮产出，未动任何代码/判据）

| # | 裁定项 | 级别 | 上限面 |
|---|---|---|---|
| 1 | 互变异构归一进身份预处理 | **判据口径级**（动 strict 身份定义） | 14 题 |
| 2 | 质子化写法归一（酸↔盐） | **判据口径级** | 6 题 |
| 3 | 记录侧形式归一（检索/编译侧，不动判据） | 池策略级 | 7 题（compiled，产物待验） |
| 4 | NAD(P)⁺ 净电荷对齐策略 | 检索侧工单 | 10 行 |
| 5 | stereo 线立项与否 | 协议扩展级（此前已裁定兑现率存疑） | 21 题+13 行（首次量化靶面） |

建议打包走 mimo 场景 1（判据评审）+ 用户裁定；1/2 与 teacher T-1 类口径裁定同族，可随 T-1 裁定包一并送。

## 4. 产物索引

- A：analysis/cnonly_repr_classification{,_data.json,.md}；脚本 /tmp/cnonly_probe/
- B：analysis/form_norm_experiment{,_data.json,.md}（含快照 form_norm_replay_snapshot.py）；逐行账 /tmp/formnorm_probe/formnorm_rows.jsonl（易失）
- 交叉核对：主会话复算（cheap 20 ∩ compiled 7 = 1 题），机器数据 /tmp/ab_cross.json
