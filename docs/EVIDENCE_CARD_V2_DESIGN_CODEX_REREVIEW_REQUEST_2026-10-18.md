# Codex 同范围设计复审请求二 — v2 设计任务书修订版（P1-A/B/C 补齐确认，2026-10-18）

> 授权链同前；fork 父=你上轮设计审会话（01a14aa6）。审核对象：`docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` **v2 修订版**（整体重写，2026-10-18）。
> 你的上轮报告：`docs/EVIDENCE_CARD_V2_DESIGN_CODEX_REVIEW_2026-10-18.md`（三组 P1 收口清单）。另：归因探针报告已按你的 P2 追加 §七 用语收窄注记（数字不变）。

## 修订摘要（对照你的收口清单）

- **P1-A 方案身份**：设计轮已选定 **S1=卡内来源去重呈现**（卡内 source 对象四件全删；顶层 transformation_ref 原样保留并**如实命名「非盲臂」**——检验卡内重复呈现的挤位贡献）；S2（顶层中性化）明记不选理由（破坏单差分与 A 字节兼容），如要比较=另轮分别预注册；§一表列完整删/留裁定。
- **P1-B 字段事实合同**：participants **保真**（已知系数如实呈现、不做「一律 unknown」；删 coefficient_status；不隐藏行数差不补假条目）；required FG **暂缓**（无权威来源不消费负证据、一律 unknown）；FG delta scope=编译器主产物+类集合语义+部分参与物限 unknown；编辑落点用**完整内部匹配**（非渲染前 8 条）；alignment 仅留 status；requirements 缺席语义保留；三类版本承载+RDKit 入指纹。
- **P1-C 验收合同**：token 计量合同（同输入 A 基线/system+user/逐题批合计/tokenizer 版本固定/离线门≤+13%/发车后费用账另列）；novel 首选指标=**模型 rank_hypotheses 首位 novel 占比**（声明偏好口径，不受折叠继承影响；行为指标非化学正控；冲突时 hit/strict 优先）；**既有 strict ≤−3 停点保持最高优先**（联合门=附加读数不取代）；**四象限判读表**全文照收。
- **P2**：证据强度用语收窄已入设计书头部+归因报告 §七。

## 请裁定（P1-A/B/C 闭合=是/否+证据；新问题分级；总裁定=设计冻结放行/再回修）

按你上轮收口清单逐项复核：P1-A（一个明确方案/可见面表/兼容与共享 prompt 关系/因果表述有限）；P1-B（participants 保真格式/requiredFG 暂缓处置/delta 落点 scope/确定性锚清单/版本承载）；P1-C（必备测量参数/停点优先或事前变更/四象限/novel 行为指标及冲突顺序）。

## 纪律（同前，违反=停止）

只读评审+可在全新临时目录跑只读探针；不动 src/tests/既有 docs/AGENTS.md；新增仅限 `docs/review_evidence/ec_v2_design_codex_rereview_2026-10-18/` 与你的报告 `docs/EVIDENCE_CARD_V2_DESIGN_CODEX_REREVIEW_2026-10-18.md`；不访问金标/题面/封存逐题 run；不 push；不调用外部模型；结论须与程序证据互证。
