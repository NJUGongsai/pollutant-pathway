# 证据卡 v2 设计冻结正链终认（2026-10-18）

**P1-A、P1-B、P1-C 闭合：均为是。未发现新增 P0/P1/P2。总裁定：放行设计冻结。** 本结论限于原收口清单的设计合同，不认证未实施程序、实际 token 开销或科学收益。

## 对象与证据身份

复核当前第三版[设计任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md)，按首轮正链报告75–83行收口，不重开已放行的 T-F 修复及既有边界。实际 HEAD 为 `4eede032d2815dd20f3a532b44a41afde8289aa4`；任务书 SHA-256 为 `37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4`，与通道 C 第二份报告所审文本相同。通道 C 报告记录的旧 HEAD `f222096087031543eb4d0b7ac98dbb24306dffed` 不冒充本轮源码身份。输入哈希见[快照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_final_2026-10-18/snapshot_metadata.json)。

通道 C 第一份报告7–9行实际裁定为 **P1-C 未闭合、回修**；第二份7行才放行设计冻结。第二份18行如实记录缺少 RDKit、导入失败，未执行断言。本轮不将其说成“两轮都放行”或“探针均通过”，也不以通道独立性替代源码和执行证据。

## 原 P1 收口逐项终认

| 原项 | 闭合 | 当前设计与源码证据 |
|---|---|---|
| **P1-A：方案身份** | **是** | 任务书17行选定 S1，卡内 source 四字段全删、顶层 transformation_ref 保留，明确非盲臂；27行限定 A 为用户 JSON 字节兼容，两臂共用新版 prompt。现有 `candidate_evidence.py:182–187` 与 `real_model.py:259–267` 支持两层来源确实分开存在。S2 另轮编号预注册，不留实施者临场择优。 |
| **P1-B：字段事实合同** | **是** | 18行保留已知系数和真实参与物，不伪造 unknown 或行数；21行暂缓 required FG，不把环境条件当必需官能团依据；20–22行把 delta 限定为编译器主产物、类集合与图级事实，信息不足给 unknown。14/47行明确完整内部匹配及有限确定性锚；28行承载 prompt/schema/descriptor 与 RDKit 身份。现有 `candidate_evidence.py:145–158、215–228、312–321`、`path_context.py:438–440`、`s5b_compiler.py:1111–1150` 支持这些事实边界。它们是后续实施要求，不能声称 v3 已实现。 |
| **P1-C：验收判读合同** | **是** | 23行补齐反馈、重试及失败计量：固定载荷离线门与实际费用分列，全部真实网络尝试进入费用账，无 usage 记 unknown 并计数，不拿字节当 token，预注册冻结且未填不得发车。29行固定全部注册题数298为分母，规范化首位 novel 为分子，无首位/弃权留分母不入分子；hit/strict 优先、禁来源配额过线。30行保留旧 strict ≤−3 停点最高优先，32–41行四象限齐全。`model_protocol.py:223–242` 及本轮合成执行支持规范化口径可复算。 |

两条原 P2 措辞已采纳：任务书17行明确 S1 是挤位假设、整包 A/B 不识别单字段贡献；S2 不选属于方案取舍而非技术必然。7行保留上游证据强度和题域限制，不据汇总数字宣布单字段因果。

## 本轮实际执行与限度

在新 tmp 归档当前 HEAD 的完整 src（含 vendor）及 metadata，以 Python 3.11.16、RDKit 2026.03.6、`-B`、`PYTHONDONTWRITEBYTECODE=1` 执行纯合成 parser/payload helper：**退出0，9例均达预期**。覆盖显式 novel 首位、缺席/null rank 默认、显式空 rank、合法弃权、非法引用及三种非法 rank 类型。前五例解析成立，后四例按协议拒绝；输入未改。

反馈 helper 确认仅追加 format_feedback；282→502 是 UTF-8 字节数，**不是 token 或 +13% 门通过证据**。未计算真实批分子/分母；298 分母属于冻结的设计定义。90个归档文件前后哈希不变，隔离源码及运行目录无 pyc/pytest 缓存；工作树与归档清单的整体差异仅为两个额外 .DS_Store，共享源码哈希一致，详见[执行证据](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_final_2026-10-18/EXECUTION_RESULT.md)。

未访问金标、题面、封存逐题 run 或真实 reports 数据，未调用外部模型或网络，未运行全量测试、真实 tokenizer、判分或旧 FG/source 探针。仅新增本报告与本轮证据目录，不修改轮前文件，不做 git 写操作。来源结论与本轮执行范围均不外推为 v2 实施通过或收益证明。

**新问题分级：无新增 P0/P1/P2。总体裁定：放行设计冻结。** 后续按任务书48–49行进入实施审、mimo 场景1、预注册与 CC 确认；本裁定不替代实施验收、预注册批准或费用放行，不追加新门。
