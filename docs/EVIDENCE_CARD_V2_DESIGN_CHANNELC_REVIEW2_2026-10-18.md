# 证据卡 v2 设计备用通道第三轮复核（2026-10-18）

> **Provenance：**备用通道 `tokeasy/gpt-6-sol` 产出，不替代正链 Codex 最终裁定权；设计冻结类重要轮次可由正链恢复后复核。

## 结论

**P1-A：闭合。P1-B：闭合。P1-C：闭合。新问题：无新增 P0/P1；P2 无阻塞项。总裁定：按本轮同范围设计审查，设计冻结放行。** 这只是设计合同收口，不代表 v2 已实施、token 增量已实测、模型收益已验证或科学性能已认证。正链 Codex 保留最终裁定权。

## 范围与执行证据

对象为 [设计任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md)。审核按上一轮收口清单复核 P1-A/B/C 和本轮新增口径，仅读相关源码及既有审核材料；未访问金标、题面、封存逐题 run 或 `reports/`，未调用网络、模型或 pytest，未修改源码、测试或既有文档。

- 实际 HEAD：`f222096087031543eb4d0b7ac98dbb24306dffed`
- 任务书 SHA-256：`37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4`
- 解析器源码：`src/pathway_v43/pollutant/model_protocol.py:223-242`
- 旧停点：`docs/CHAIN14_EVIDENCE_AB_PREREG_2026-10-15.md:37-38`

本轮尝试运行合成解析探针，但当前 Python 环境缺少 `rdkit`，在导入阶段以 `ModuleNotFoundError` 退出，未执行探针断言。没有把该尝试计作通过。逐项程序互证因此基于源码静态检查；原始执行限制记录见[证据文件](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_channelC_r2_2026-10-18/probe_attempt.txt)。

## P1 逐项复核

| 项目 | 裁定 | 依据与边界 |
|---|---|---|
| **P1-A：source 方案、可见面、兼容及因果边界** | **是，闭合** | 任务书 §一已选 S1，删除卡内 source 四字段并保留顶层 `transformation_ref`，明示非盲臂；§二冻结 A 用户 JSON 字节兼容、两臂同 prompt，并明确 A/B 是整包方案差异、不识别单字段贡献。S2 明确属于本轮方案取舍，如需比较另行编号预注册。实现中顶层引用仍在 `real_model.py:259-268` 组装，和文档边界一致。 |
| **P1-B：事实合同、unknown、scope、锚点与版本** | **是，闭合** | 第三版保留已知参与物系数、不伪造 unknown；required FG 暂缓；delta 限编译器主产物与类集合语义，部分信息不足时限定图级差值或 unknown；编辑落点用完整内部匹配；实施前确定性锚及 prompt/schema/descriptor/RDKit 版本承载均有列明。关闭范围仍仅是设计合同，后续实施须按锚验收。 |
| **P1-C：token、novel 指标、停点与判读** | **是，闭合** | token 条款区分固定载荷离线门与发车后账单口径：格式反馈不计离线门，decide 首发、反馈轮及传输重试均计实际费用；失败请求无 usage 记 unknown 并披露；禁止用 UTF-8 字节代 token；预注册逐字冻结且未填不得发车。novel 指标分母固定为全部注册题数 298；分子按规范化后的 `rank_hypotheses` 首位为 novel 计题，无首位/弃权留分母不入分子；同样预注册冻结、未填不得发车。既有 strict 净失 ≤−3 停点仍优先，四象限判读完整，hit/strict 冲突时优先。 |

## 程序互证与限制

`model_protocol.py:223-225` 显示 `rank_hypotheses` 字段缺席（以及解析后值为 `None`）会按 proposals 顺序补齐；`230-242` 按 rank 列表保留顺序，并允许显式空 rank 与非空 proposals，因此任务书区分了“缺席按补后首位”和“显式空 rank 无首位”。空 proposals 被解析为 `abstained=True`，支持弃权留在注册题分母的定义。非法 rank 引用在 `233-238` 拒绝。源码证据支持该统计定义可复算；由于依赖缺失，本轮没有运行行为探针。

旧预注册明确全局或任一分族 v2 strict 净失 ≤−3 停点。任务书将其列为最高优先，并把 novel 与 token 联合方向门定位为附加读数，未用新读数替换旧停点。

**新问题分级：**无新增 P0/P1。无新增 P2。探针未执行是审核证据限制，不是设计书缺陷；它也不构成实现通过证据。

## 总裁定

1. **P1-A：是，闭合。**
2. **P1-B：是，闭合。**
3. **P1-C：是，闭合。** 上轮列出的两项缺口及“未填不得发车”均已明确补齐，且与解析器源码定义相容。
4. **设计冻结：放行（备用通道意见）。** 本结论不替代正链 Codex 最终裁定；也不授权付费发车。实施、预注册、CC 确认及费用红线仍按任务书执行。
