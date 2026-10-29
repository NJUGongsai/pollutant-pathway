# 证据卡 v2 设计备用通道复审（2026-10-18）

> **Provenance：**本报告由备用审核通道 `tokeasy/gpt-6-sol` 产出，不替代正链 ChatGPT Codex 最终裁定权。设计冻结类重要轮次可在正链额度恢复后复核确认。

## 结论

**P1-A：闭合。P1-B：闭合。P1-C：未闭合。总裁定：再回修，本轮不放行设计冻结。** 未发现 P0；没有新增独立缺陷。未闭合项是上一轮 P1-C 原收口清单中已经列出的测量定义和发车门，不是新加性能要求。

最小补齐：在任务书中写明后续预注册必须冻结 token 统计对反馈轮、传输重试及失败请求的计量口径；并冻结 novel 首位占比的统计分母及无首位样本处理。明确这些项未填不得发车。具体口径可留给预注册选定，本轮不要求真实模型、完整预注册或代码实施。

## 范围与证据

审核对象为修订版[设计任务书](/Volumes/CC/Enzyme_Agent/dependingv43/docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md:1)，按上一轮[收口报告](/Volumes/CC/Enzyme_Agent/dependingv43/docs/EVIDENCE_CARD_V2_DESIGN_CODEX_REVIEW_2026-10-18.md:75)复核。任务书 SHA-256：`d6db9358301a7616e212a97c49cf9b537eca827ef44946685dc0c9aa2eda6fbb`；实际 HEAD：`f222096087031543eb4d0b7ac98dbb24306dffed`。精确源码哈希、隔离执行参数与结果见[快照元数据](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_channelC_2026-10-18/snapshot_metadata.json)。

本轮仅核对任务书、上一轮报告、相关源码和许可的归因汇总报告。未访问金标、题面、封存逐题 run 或 `reports/`；未调用网络、模型或 pytest；未修改 `src/`、`tests/`、既有文档或仓库配置。将完整 `src/`（含 vendor）及 `pyproject.toml` 归档到新建隔离目录后，以 Python 3.11.16、RDKit 2026.03.6、`PYTHONDONTWRITEBYTECODE=1` 和 `-B` 执行合成 parser/载荷 helper 探针；98 个归档源码文件执行前后哈希相同，退出码 0、stderr 为空。探针与输出保存在[本轮证据目录](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_channelC_2026-10-18/c_probe.py)。

该探针验证现有协议行为，不认证 v2 尚未实施的字段、化学结果或收益，也没有运行 tokenizer；UTF-8 字节长度不能当作 token 增量。

## P1 逐项复核

| 项目 | 裁定 | 证据与边界 |
|---|---|---|
| **P1-A：source 方案、可见面、兼容及因果边界** | **闭合** | 任务书 §一第17行选择 S1，明确卡内 source 四字段删除、顶层 `transformation_ref` 保留并称“非盲臂”，S2 不纳入本轮；§二第27行限定 A 兼容为用户 JSON 字节路径、两臂共用同一新版 prompt；任务书第7行及归因报告 §七限制 15:2 等数字的解释范围。源码 `candidate_evidence.py` 第182–187行列出卡内四字段，`real_model.py` 第259–268行显示顶层引用仍单独装载。**P2 非阻塞措辞：**“检验卡内重复呈现来源的挤位贡献”容易被理解为识别 source 单字段因果；但本轮 A/B 同时改变整包证据，最多估计整包方案差异。建议改称“本设计针对卡内重复呈现来源的挤位假设；A/B 不识别单字段贡献”。同样，S2 对 A 路径兼容的影响属于本轮方案选择，不宜写成技术必然。 |
| **P1-B：字段事实、unknown、delta scope、锚点与版本** | **闭合** | 任务书 §一第18、20–22行及 §四第45–47行已明确：参与物保真且已知系数照实、删除完整度提示、不隐藏/伪补行；required FG 暂缓且不消费负证据；delta 限编译器主产物、类集合语义，部分参与物/未知系数时降为图级差值或 unknown；编辑落点用完整内部匹配；列出有限确定性锚。源码 `candidate_evidence.py` 第147–159行支持已知系数事实，第312–322行显示展示匹配最多 8 条；`s5b_compiler.py` 第1107–1115行定义主产物选择范围；`path_context.py` 第438–440行将 Requirement 定义为环境/供给要求。任务书 §二第28行规定 prompt 哈希、schema、descriptor 与 RDKit 身份承载。关闭的是设计合同，不是未实施实现的通过认证。氧化度的具体可复算表达可在实施单定为图级口径或暂缓，不扩大为整反应氧化态证明。 |
| **P1-C：测量参数、旧停点、四象限、novel 指标** | **未闭合** | 已闭合部分：任务书 §一第23行规定同输入 A 基线、system+user、逐题及批合计、固定 tokenizer 版本、离线 ≤+13% 门与实际费用账分列；§二第27–30行规定冻结面、共享 prompt、novel 指标方向和冲突优先级、旧 strict ≤−3 停点最高优先及事前变更；§三第32–41行完整列四象限。剩余项仍是上一轮原清单：没有指定 token 统计对格式反馈、传输重试、失败请求的口径，也没有冻结 novel 占比的统计分母及无首位样本处理；第49行“§二合同全量”无法指向未写入 §二的内容。 |

## P1-C 程序互证

当前 `model_protocol.py` 第223–225行规定 rank 字段缺席时补为提案顺序；第230–242行允许显式空 rank 与非空提案并将其标为非弃权。因此“模型声明首位 novel 占比”在合法输出中可能遇到没有首位的非弃权样本；若不冻结分母及该样本的处理，指标仍不能唯一复算。

本轮隔离合成探针覆盖显式 novel 首位、rank 缺席、显式空 rank 但有提案、合法弃权及非法 rank 引用：行为与上述代码相符。它还核对格式反馈只给 user JSON 增加 `format_feedback` 内容；无法从这些字节数推得 token 数。故 token 门必须预先写出反馈、重试、失败的计数规则，避免不同执行人各自选择口径。完整输出见[探针结果](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ec_v2_design_channelC_2026-10-18/c_probe_output.json)。

## 收口

1. **P1-A：是，闭合。** 建议把“检验……挤位贡献”改为设计假设表述，不影响 P1 关闭。
2. **P1-B：是，闭合。** 关闭范围限于设计合同；后续实施仍须按任务书锚点验收。
3. **P1-C：否，未闭合。** 仅补 token 反馈/重试/失败统计口径、novel 分母/无首位处理，并声明未填不得发车；不要求本轮填具体数字或跑真实批。
4. **新问题：无新增 P0/P1。** 上述措辞建议为 P2，非冻结阻塞项。

**总裁定：再回修。** 完成第3项最小补充后，可按原范围申请复审；本报告不替代正链 Codex 对设计冻结的最终裁定。
