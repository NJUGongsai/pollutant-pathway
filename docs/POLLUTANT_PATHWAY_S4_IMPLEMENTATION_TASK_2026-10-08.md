> 生成通道：本任务书由 opencode tokeasy/gpt-6-sol 于 2026-10-08 撰写（用户裁定交给 tokeasy 的 gpt 写），基于仓内规格 §10/§11/§17、S3B-R3 终审 §7.2 与 S3 任务书范本生成；主会话落盘。开工前由用户/主会话复核。

# pollutant_pathway_v1：S4 工程实施任务书

日期：2026-10-08。  
仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。  
建议文件名：`docs/POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md`。  
直接父基线：`adf0287abef0c4803962fee0df0065d8e6f3793d`。

**授权边界：本任务书用于用户另行启动 S4。S3 已完成工程交接，但 S3 通过不等于污染物路径已科学确证，也不自动启动 S4/S5 或判据冻结。实施 agent 只读本任务书与当前 `AGENTS.md` 即可开工；本文列出的绝对路径用于核对来源、既有契约和交接证据。**

S4 的目标是把 S3 已经持久化、可恢复、可审计的有限搜索结果，转换为：

1. 独立的执行状态、搜索停止原因、化学终点判断和账目闭合状态；
2. 保留完整信息的路径原生正式导出；
3. 明确标注信息损失的 v3 兼容适配；
4. 通过 scripted/off 规则级场景验证从搜索到终点判断、原生导出和适配导出的完整公共链路。

本阶段不实现科学性能评测，不访问真实 provider，不使用金标、题面或封存逐题 run，也不宣布化学判据冻结。

## 1. 必读材料与基线核对

实施前必须读取并在交付书中登记实际版本、实际 HEAD 和工作区状态：

1. `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`  
   仓库纪律、入口矩阵要求、隔离证据、mimo 通道、自动回修循环和提交边界。

2. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md`  
   重点：
   - §10：搜索停止、化学终点、账目闭合、路径原生导出和 v3 适配；
   - §11：阶段归属、review 交付和阶段边界；
   - §12：A01–G02 最小工程验收矩阵；
   - §17：阶段裁定、G2 审计边界、终点证据边界和负面场景归属。

3. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`  
   重点：
   - §5：残留 P2、当前许可范围和不可扩大的边界；
   - §7.2：S4 逐条交接约束；
   - §7.4：恢复、ledger、`put_state`、失败状态、旧 run 和新实验根目录等交接义务。

4. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md`  
   作为 S4 任务书的结构、入口矩阵、回归、G01、证据和交付格式范本。S4 不复制 S3 的功能范围。

5. `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_DELIVERY_R3_2026-10-08.md`  
   作为当前入口矩阵、独立权威、首消费守卫、公共入口验证和证据披露的先例。

6. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/profile.py`  
   查看 PPV1 profile、版本注册和当前契约身份。

7. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py`  
   查看 `ChemicalState` 构造、解析、严格身份和首消费验证。

8. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py`  
   查看路径上下文、条件、依赖、场景转换和历史快照边界。

9. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/hypothesis.py`、`events.py`、`store.py`  
   查看假设、事件、报告投影、展开计划、首提和 replay 契约。

10. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py`、`pool_audit.py`、`substrate_profile.py`、`provenance.py`  
    查看 audit、来源、底物档案、支持来源和 proof scope。

11. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py`、`search.py`、`queue.py`、`model_protocol.py`  
    查看 S3 公共搜索链、停止原因、action/attempt、预算、恢复和 scripted 模型边界。

12. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/workflow/runner.py`  
    查看 `start_run`/`resume_run` 的 PPV1 分流和 legacy 保护，不得把 S4 接回 legacy 流程。

13. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/output/export_v3.py`  
    这是冻结的旧 v3 导出入口，只读核对，禁止修改。

14. `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/services/atom_tool.py`  
    冻结工具，只能调用，不能修改。

开工第一步必须记录：

- 实际 `HEAD`；
- 工作区已存在的修改和未跟踪文件；
- 当前直接父基线是否为 `adf0287abef0c4803962fee0df0065d8e6f3793d`；
- 当前 PPV1 profile、runflow、search、store、export 相关版本；
- 预计本批修改文件和不修改文件。

不得删除、覆盖、stash、reset 或顺手暂存用户已有修改、AGENTS 差异、历史 review、mimo 回复和证据目录。

## 2. S4 范围

### 2.1 必须实现

S4 必须覆盖以下四组工程任务。

#### A. endpoint 分账

在公共 PPV1 链路中分别保存并输出：

- `execution_status`
- `search_stop_reason`
- `chemical_endpoint_assessment`
- `bookkeeping_status`

四者不得互相代替。

`search_stop_reason` 至少支持：

- `budget_limit`
- `depth_limit`
- `no_local_candidate`
- `awaiting_prediction`
- `exhausted_search`
- `user_stop`

如仍有 deferred、未展开对象、知识缺口或必要依赖未知，不能把状态写成“所有路线已搜索完毕”。

`chemical_endpoint_assessment` 至少区分：

- `unknown`
- `metabolic_handoff`
- `supported_terminal_transformation_product`
- `supported_mineralization`

终点判断必须同时保留：

- `evidence_basis`，例如：
  - `direct_observation`
  - `inferred_from_pathway`
  - `model_prediction`
  - `no_evidence`
- 来源引用；
- 来源支持范围；
- 条件和环境；
- 观察时间或观察窗口；
- 检测范围；
- 必要依赖；
- 根碳去向核查范围；
- 未核实轴和 proof scope。

没有独立终点证据时，必须是 `unknown`。  
模型预测或路径推断不能单独产生 `supported_terminal_transformation_product` 或 `supported_mineralization`。

`bookkeeping_status` 只表达参与物、系数、根碳账或映射是否在声明范围内闭合。账目闭合不等于发生矿化，也不等于生物可行。

#### B. 路径原生正式导出

新增 PPV1 原生导出，必须保留完整的路径事实和不确定性，包括：

- `ChemicalState`
- `PathInstance`
- 根路径和子路径身份
- 全部反应假设和事件
- 不同来路和 parent/context
- 共同产物
- 备选反应和备选路径关系
- 产品角色
- 条件和依赖
- source/provenance
- audit 结果
- proof scope
- 已展开状态
- 仅报告状态
- deferred/暂缓集合
- 未解决 continuation
- 预算预约和实际消耗
- 搜索停止原因
- endpoint 分账结果
- 账目闭合状态
- 失败、unknown、partial 和 violated 的原因
- 版本、身份、内容 hash 和生成依据。

导出不能按 CN 父节点首现合并成一条“唯一真实路线”。路径相同但来路、上下文、假设、证据或来源不同，必须继续分别表示。

原生导出必须是确定性的：相同版本、相同图修订、相同权威输入和相同策略身份，应产生相同的规范化字节或等价稳定序列。

导出必须能够识别过期结果。至少要能发现：

- 源路径版本变化；
- graph revision 变化；
- endpoint/导出策略版本变化；
- 依赖对象内容变化；
- 产出结果与当前权威输入不匹配；
- 导出 manifest 或引用的内容 hash 不一致。

过期结果必须结构化标记或拒绝消费，不能静默当作当前结果。

#### C. v3 有损适配

如提供旧 v3 适配，必须是显式的有损投影：

- 标注 `lossy_projection`；
- 标注原生结果引用；
- 标注信息损失项；
- 标注适配版本；
- 标注原生图修订和来源 identity；
- 保留不可投影字段的摘要或引用；
- 不把 v3 报告位置约束反向写成 PPV1 事件事实；
- 不把 v3 的单一路径、CN 合并或旧报告字段解释为原生完整语义。

旧 `export_v3.py` 和 legacy 导出行为冻结，不得修改。适配器只能位于 PPV1 新模式的明确边界内。

当一个原生结果无法无损映射到 v3 时，应保留原生引用并明确丢失：

- 来路；
- 共同产物；
- 备选关系；
- 条件/依赖；
- audit/proof scope；
- deferred/未展开集合；
- endpoint 证据等级；
- 预算停止原因；
- unknown/partial 的具体轴。

不得为填满旧字段而编造终点、矿化、解毒或来源支持。

#### D. scripted 端到端验收

必须从公共 PPV1 入口验证完整链路，而不是只测导出函数：

```text
scripted 输入
→ start_run/resume_run
→ action/attempt/ledger 消费
→ 搜索结果和停止原因
→ endpoint 分账
→ 原生导出
→ 过期识别
→ v3 有损适配
→ 再次读取/消费/重放
```

必须使用规则级自包含夹具、scripted/off provider 和合成来源。网络请求必须为 0。

端到端场景至少覆盖：

- 正常路径；
- 多个备选反应；
- 共同产物；
- 首选下游受阻而备选可继续；
- deferred 未激活；
- 预算停止；
- 深度停止；
- 空候选停止；
- 上游模型假设、下游 recorded；
- unknown 必要依赖；
- 不同来路的同 CN；
- 重复来源引用；
- 终点无证据；
- 账目闭合但无矿化证据；
- 原生导出重复生成；
- 原生导出过期；
- v3 投影信息损失；
- endpoint 和搜索状态不一致的拒绝或修正；
- resume/replay 不重复写事件或预算。

## 3. 明确不做

本批不得实施：

1. S5 科学性能评测器、数据集、真实路径命中率、留出规则、阈值冻结、统计预注册执行。
2. 真实 provider、真实模型请求、付费实验或检索质量实验。
3. 金标、题面、封存逐题 run、真实评测结果或任何需要访问敏感资料的验证。
4. 新机制库、完整机制证明、酶活性认证、电子转移硬门、样品纯度认证。
5. 新的隐含 G2 过滤、排序或 hard gate。
6. 修改冻结 legacy profile、legacy budget、legacy report、冻结 G2、`AtomTool` 或 `/src/pathway_v43/output/export_v3.py`。
7. 把 S4 工程夹具通过写成 dev 或 298 科学性能通过。
8. 自动冻结化学判据、proof scope、终点阈值或矿化定义。
9. 将不同备选路线的 CO₂ 或来源证据合并为单一路径证据。
10. 将 endpoint 结果反向改写 S3 已提交事件、历史 run 或封存资料。
11. 为了“让导出完整”而把 unknown、partial、deferred、unresolved 或预算停止改成成功。
12. 为了使 v3 适配通过而丢弃或伪造原生结果事实。

如果必须修改冻结判据正文、既有 hard gate、legacy 行为或评分含义，必须停下并报告：

- 触碰的具体文件和字段；
- 当前判据版本；
- 为什么 S4 无法在不改判据的情况下完成；
- 可选方案及其影响；
- 需要用户/teacher 另行裁定和新的化学 review 的范围。

## 4. S4 硬约束

以下约束逐条来自 S3B R3 交接，实施和验收均必须覆盖。

### 4.1 F01：停止不是终点

以下任何情况只能产生搜索停止状态，不能自动产生化学终点：

- 无候选；
- 深度达到上限；
- 预算达到上限；
- 模型弃权；
- 等待预测；
- 搜索队列耗尽；
- 用户停止。

若缺少独立终点证据，`chemical_endpoint_assessment` 必须为 `unknown`。

停止时仍必须保留：

- 已有有效事件；
- 未展开对象；
- deferred 集合；
- unresolved continuation；
- 未解决依赖；
- 预算和停止原因；
- 已有 endpoint 证据及其范围。

不得用“搜索停止”覆盖已有有效终点证据，也不得用“账目闭合”提升为矿化。

### 4.2 F02：未知依赖不能被 recorded 洗白

如果上游假设依赖未知、条件未知、供体未知、必要共底物供应未知或环境事实未闭合，下游即使来源标记为 `recorded`，也必须继承未解决依赖。

`recorded` 只表示该边或该观察在来源层被记录，不表示：

- 当前场景已满足条件；
- 上游假设已被观察证实；
- 整条路线已成为观测路线；
- 终点已获得支持；
- 根碳账已闭合；
- 解毒或矿化已经发生。

必须在原生导出中同时保留：

- recorded 状态；
- inherited unknown/unresolved；
- 依赖来源；
- 条件评估；
- proof scope；
- 最终 endpoint 限制。

### 4.3 F03：不同来路和重复来源不增加独立支持

以下内容不得重复增加独立路径支持：

- 同一来源的多个引用；
- 同一观察的多个包装；
- 相同来源引用的重复记录；
- 相同 CN 但不同来路被错误合并；
- 同一模型多次采样；
- 同一个 artifact 的不同投影；
- 原生结果和 v3 适配结果同时计为两条路径。

原生导出必须保留不同来路，但支持计数必须使用去重后的来源/观察身份。

“保留不同来路”和“避免重复支持”必须同时成立：

- 来路不能被 CN 合并抹掉；
- 重复来源不能被计数器当成独立证据；
- 不同 parent/context 不得被当成同一个全局 hypothesis；
- 同一 semantic attempt 的恢复不能新增支持。

### 4.4 G02：导出确定性与过期可识别

相同有效输入必须重复生成相同原生导出。需要固定：

- 字段顺序；
- 列表排序；
- ID 表示；
- 数值和空值编码；
- 版本和策略字段；
- hash 输入；
- manifest 组成；
- endpoint 和 stop reason 的序列化格式。

必须测试：

1. 同一 run、同一 graph revision 重复导出；
2. 恢复后重复导出；
3. 原生导出再读取；
4. 改变源图 revision 后旧结果被识别为过期；
5. 改变 endpoint/export policy 后旧结果被识别为过期；
6. 内容 hash 或引用不一致时结构化失败；
7. 旧结果不能通过重新计算新 ID 被“洗成”当前结果。

### 4.5 终点、矿化、CO₂ 和解毒边界

必须明确执行以下规则：

- 停止不当终点；
- 账平不当矿化；
- 不把不同备选反应生成的 CO₂ 相加；
- 不把单项 CO₂ 产物自动解释为根污染物已矿化；
- 缺根碳去向、来源终点证据或必要条件时保持 unknown；
- 不自动推导解毒；
- `metabolic_handoff` 不等于矿化；
- `supported_terminal_transformation_product` 不等于永久去除；
- 来源报告的矿化比例必须保留计量基础、条件、时间范围和证据引用；
- root carbon accounting coverage 只能表示核查范围，不表示所有根碳已经转化。

## 5. 继承契约

S4 必须继续消费 S3 已建立的守卫，不得因为新增 endpoint 或 export 层而绕过它们。

### 5.1 恢复和 ledger 首消费守卫继续生效

所有以下入口都必须继续先验证版本、身份、内容 hash、事实和来源范围：

- restore；
- direct dataclass；
- `from_dict`；
- context derive；
- state 组装；
- hypothesis 消费；
- audit；
- 首次 `submit_event`；
- replay；
- endpoint 计算；
- 原生导出；
- v3 适配；
- resume；
- 过期结果读取。

导出层不能把未经验证的 raw 对象包装成“正式结果”。  
派生前必须先验证父对象。  
历史覆盖签名必须对应实际记录评估，不能用当前事实重新评估旧边。

### 5.2 `put_state` 返回值不是证书

`put_state` 返回成功、`None` 或无异常，都不能作为：

- 旧行完整性证书；
- appearance hash 证书；
- 来源真实性证书；
- endpoint 证书；
- replay 正确性证书；
- 导出可用证书。

实际复用 state、appearance、hypothesis、event、ledger 或导出缓存前，必须消费对应的独立权威记录并完成验证。

### 5.3 失败状态必须保留

以下状态不得转成成功：

- `None`
- `unknown`
- `partial`
- `deferred`
- `unresolved`
- `blocked`
- `violated`
- `method_failed`
- `pending`
- `not_run`
- `prerequisite_failed_not_run`

`execution_ok=False` 时，不能把诊断字段的 `None` 当作通过。  
普通缺证据、缺映射、覆盖不足应继续保留 unknown/partial；契约异常必须中止本次 admission/submit/export 消费，不能吞异常继续生成成功终点。

### 5.4 版本和 run 根目录

- 旧 run 不跨版本续跑。
- 语义变化必须升级对应版本并进入身份。
- 不原地切换旧 run 的 profile、endpoint schema、export policy 或策略身份。
- 新批实验、新 scripted scenario、新证据批次使用新根目录。
- 旧 run 只能按既有版本规则读取和报告。
- 不通过重新计算新 ID 掩盖旧资料损坏或版本不匹配。

## 6. 入口矩阵要求

开工后必须先建立 S4 入口矩阵，至少包含以下入口：

| 入口 | 必须登记的事实 | 必须验证的身份/版本 | S4 行为 |
| --- | --- | --- | --- |
| `start_run` / PPV1 start | root state、context、search actions、attempts、预算 | profile、runflow、search、policy、endpoint、export | 创建新 run 的 endpoint/export 绑定 |
| `resume_run` | 已提交事件、预算、deferred、endpoint 状态 | run/root/task、artifact、graph revision | 恢复同一事实，不重复事件或预算 |
| state restore | state、appearance、source、conditions | state/version/content identity | 失败则拒绝，不进入 endpoint |
| hypothesis/event 首提 | 反应假设、参与物、来源、条件、依赖 | hypothesis/event/context identity | 保留不同来路和共同产物 |
| replay | 事件、展开计划、attempt | event/action/attempt identity | 幂等，结果不增加 |
| endpoint derive | 搜索状态、事件、依赖、来源 | graph revision、endpoint policy | 分账，不从停止直接推终点 |
| endpoint consume | endpoint record、证据、账目 | endpoint identity、proof scope | 过期或缺证据时拒绝/unknown |
| native export | 全部原生事实 | export schema、graph revision、policy、输入 hash | 确定性完整导出 |
| native export read | manifest、payload、引用 | hash、schema、source identity | 识别 stale/corrupt |
| v3 adapter | 原生结果和映射策略 | adapter version、legacy boundary | 只产生明确 `lossy_projection` |
| deferred activation | deferred 类型、触发条件、parent revision | action、trigger、budget | 共同产物和备选反应分账激活 |
| audit/admission | proof、scope、conditions、来源 | audit/version、hypothesis identity | 不扩大证明范围 |
| report projection | endpoint、停止、账目、未展开集合 | report/export version | 不丢掉原生事实 |

矩阵中每一行必须说明：

- 入口实际消费什么事实；
- 事实的独立权威在哪里；
- 身份和版本如何绑定；
- proof scope 到哪里；
- 失败、unknown、partial、stale 如何表示；
- 对应哪个验收场景；
- 使用什么正控和负控。

不得只在一个导出函数上补判断。相同规则适用的入口必须共享验证来源和判据。

## 7. 建议分批

建议分为 S4a 和 S4b。每批都可以独立走完整的：

```text
实施
→ 主会话核对
→ mimo 化学请求
→ Codex 复审
```

### S4a：endpoint 分账和原生结果底座

建议内容：

1. endpoint record/schema 和版本注册；
2. `execution_status`、`search_stop_reason`、`chemical_endpoint_assessment`、`bookkeeping_status` 分账；
3. endpoint evidence、source conditions、proof scope、root carbon accounting coverage；
4. F01/F02/F03 规则；
5. stop reason 和 endpoint 的独立持久化；
6. endpoint 读取、首消费和 stale/integrity 校验；
7. 原生结果对象的完整字段和确定性规范化；
8. endpoint-only scripted 端到端公共链；
9. endpoint 相关的正控、unknown 控、partial 控、停止控和重复来源控；
10. 不接 v3 正式适配，或只建立不改变 legacy 的明确边界。

S4a 完成时可以证明 endpoint 分账和原生结果底座已覆盖，但不能称完整 S4，除非 S4b 的适配和端到端矩阵也完成。

### S4b：正式导出、v3 有损适配和完整端到端链

建议内容：

1. 路径原生正式导出；
2. 确定性重复生成；
3. stale/integrity 识别；
4. 共同产物、备选、不同来路、条件、依赖、audit、未展开集合和预算原因的全量导出；
5. v3 `lossy_projection` 适配；
6. 原生结果与 v3 投影的双向引用边界；
7. legacy/export_v3 冻结回归；
8. scripted 从 start/resume 到 endpoint、native export、v3 adapter、replay 的完整公共链；
9. G02 重复生成和过期场景；
10. S4 全量回归、G01 隔离、交付书和 mimo v16 请求。

不得因为 S4a 通过就提前修改冻结 legacy 导出或宣称完整 S4。

## 8. 逐任务验收矩阵

每一行必须有“入口 → 行为 → 可执行断言 → 证据”。  
复合探针遇到预期拒绝后，未执行的后续内部部分必须标记为未执行，不能报整条链通过。

| 任务 | 入口 | 必须行为 | 证据 |
| --- | --- | --- | --- |
| endpoint 四分账 | 公共 start/resume→endpoint derive | execution、stop、chemical endpoint、bookkeeping 四者独立存在；停止不覆盖终点 | scripted 输出、数据库/ledger、字段断言 |
| F01 停止非终点 | no candidate/depth/budget/prediction/user stop | endpoint 无独立证据时为 unknown；保留 deferred、未展开、预算原因 | 零预算、零深度、空池、等待预测四类夹具 |
| F02 unknown 依赖 | 上游假设→下游 recorded→endpoint | 未知依赖沿途保留；recorded 不升级观测路线或终点 | 上下游链、导出字段、endpoint 断言 |
| F03 来源去重 | 同来源多引用、同 CN 不同来路、重复 replay | 来路保留；独立支持不重复增加；同一采样不计多条路径 | 来源身份和支持计数账目 |
| 根碳账 | 共同产物/CO₂/缺映射/缺供碳 | 账平只表示核查范围；不自动矿化；不同备选 CO₂ 不相加 | 正控、缺口控、备选分支控 |
| 终点证据 | direct/inferred/model/no evidence | 证据类型、条件、时间、范围和引用分开；模型/推断不能单独授 supported endpoint | 四类 evidence fixture |
| 终点条件 | 必要条件 unknown/conflict/recorded | 条件/依赖不被来源标签洗白；保留 unresolved | context/condition fixture |
| 原生结果完整性 | native export | 导出包含 state、path、events、alternatives、products、conditions、dependencies、audit、deferred、budget、stop、endpoint | 完整合成图及字段 hash |
| 共同产物 | 一个事件产生 B+C | 一个事件保留 B+C；产品宽度不截断事件事实 | A02/A03 公共链 |
| 备选路径 | A→B 与 A→C | 两个假设/事件独立；不合并为单反应；B 受阻时 C 可在预算内继续 | A01/E01 公共链 |
| 不同来路 | 同 CN、多 parent/context | 来路、context、source origin 保留；不按 CN 全局合并 | 两个 parent/context 正控 |
| deferred 分类 | 共同产物 deferred、备选 reaction deferred | 两类分别记录、分别激活、分别记录原因 | E02 公共链 |
| 搜索停止账 | action/attempt/budget/reason | 主因按既定优先级；其他原因和未探索集合保留 | stop ledger、预算复算 |
| 导出确定性 | 同一结果重复 export | 字节或规范化等价结果相同；排序和空值稳定 | 两次独立进程导出 hash |
| 导出过期 | 改 graph revision/policy/source hash | 旧结果 stale 或拒绝；不能静默消费 | 正常、stale、corrupt 三案 |
| 导出完整性 | 破坏 manifest/payload/reference | 明确 integrity failure，保全原文件，不重写覆盖 | hash 错、schema 错、缺引用 |
| v3 有损适配 | native result→v3 | 标注 `lossy_projection`、原生引用、适配版本、信息损失 | v3 适配 JSON/报告 |
| v3 反向污染 | 读取 v3 适配→原生 state/event | v3 旧字段不能改写原生事实；不能从旧报告位置推出新事件 | 反向消费负控 |
| legacy 回归 | legacy profile/export_v3 | 旧输入、报告、预算和冻结导出字节/行为不变 | legacy 测试和字节比较 |
| resume/replay | crash/restart/replay | endpoint/export 不重复写 event、attempt、request、budget；旧 run 不跨版本续跑 | 四崩溃边界和重复恢复 |
| 失败状态 | audit/admission/export | None/unknown/partial/deferred/failed 不被转成功；契约异常中止本次消费 | 分段负控 |
| scripted E2E | start/resume→native→v3→replay | 所有公共入口实际到达；网络请求为 0；未到达段单列 | 完整 argv/stdout/stderr/断言 |
| G01 | 安全隔离源 | 只运行允许工程输入；skip/deselect/缺依赖逐项披露 | G01 README、清单、日志 |

## 9. 回归、红绿和基线口径

### 9.1 直接父基线

直接父基线固定为：

```text
adf0287abef0c4803962fee0df0065d8e6f3793d
```

新增测试必须在父基线的 detached worktree 中以**同字节文件**运行。不得为让父基线收集测试而：

- 修改 import；
- 修改返回值；
- 修改测试期望；
- 添加兼容补丁；
- 复制当前实现；
- 将缺接口伪装为行为失败。

父基线对新增 S4 测试的结果必须分类如实：

- `collection/import/schema/field/table missing`
- `implementation missing`
- `behavior failure`
- `expected behavior difference`
- `legal positive control`
- `unknown/partial positive control`
- `not reached after expected rejection`

“父基线出现红”不自动等于旧错误。  
“当前测试全绿”也不等于科学性能或化学终点正确。

### 9.2 当前树回归

每批至少运行：

1. S4 新增焦点测试；
2. S3 PPV1 全量测试；
3. 受影响模块的既有测试；
4. legacy/export_v3 相关回归；
5. 端到端 scripted 场景；
6. G01 安全隔离工程回归。

记录实际测试数量，不锁死历史数字。必须区分：

- 测试收集失败；
- 字段/表/导入缺失；
- 真实行为失败；
- 正控通过；
- unknown/partial 合法保留；
- 预期拒绝后未执行的内部段；
- 网络请求数；
- provider 类型；
- 真实模型调用数。

不得用测试总数、exit 0、字段存在或顶层继续替代逐场景断言。

### 9.3 既有 legacy 保护

以下文件和行为默认冻结：

- `src/pathway_v43/output/export_v3.py`
- legacy profile 和 legacy runner 分支；
- 冻结 G2 逻辑；
- `src/pathway_v43/services/atom_tool.py`
- 既有 legacy budget、报告位置、排序、输入和输出约束。

如果确需共享文件增加 PPV1 分流，只能增加明确 PPV1 分支，必须证明 legacy 分支逐字节或行为保持，并在交付书列出：

- 修改文件；
- 旧/新 SHA；
- legacy 运行结果；
- profile/identity 影响；
- 未触碰的冻结模块。

## 10. G01 安全隔离口径

G01 只证明工程安全隔离和既有工程回归，不证明科学性能。

必须：

- 从当前源码复制到新 tmp 或新 worktree；
- 复制完整 vendor 和必要 project metadata；
- 使用当前实际 HEAD 和当前源清单；
- 禁止 Python 字节码和 pytest cache；
- 使用空的 `BBD_DATA_ROOT`、`V3_CODE_ROOT`、`V43_ASSET_ROOT`、`DEPENDING_V3_ROOT`；
- 不在永久证据目录原地运行会写数据库、日志或输出的探针；
- 不读取真实评价、金标、题面、reports/data/evaluation/benchmark、封存逐题材料、dependingv4 或冻结 v3 资产；
- 当前 S4 新增文件和依赖逐项加入白名单并记录理由和 SHA；
- 记录 skip、deselect、缺依赖和显式排除；
- 记录网络请求为 0；
- 记录 scripted/fake provider 与真实 provider 的区别；
- 不能把历史 G01 数字直接称为当前 S4 数字；
- 不能把 G01 数字外推到 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）科学性能。

G01 控制器必须新建或明确更新，不能直接用硬编码旧 HEAD、旧测试数或旧输入 hash 的脚本声称当前 S4 已验证。

## 11. 证据目录规范

本批证据根目录固定为：

```text
/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_impl_<实际日期>/
```

建议子目录：

```text
s4a_<轮次>/
s4b_<轮次>/
```

每个批次使用新的合成批次根和新的 tmp/worktree。回修新建新的子目录，不覆盖旧证据，不回写旧报告或旧 manifest。

每个批次至少包含：

- `README.md`
- `manifest.json`
- `SHA256SUMS`
- 原始执行脚本；
- 合成输入；
- 完整输出；
- stdout/stderr；
- junit 或等价断言结果；
- 实际 argv、cwd、关键环境变量；
- 退出码和耗时；
- 实际 HEAD、父基线、dirty 状态；
- Python、RDKit、SQLite 和相关依赖版本；
- schema、策略、endpoint、export、adapter、tool identity；
- 每个输入和输出 hash；
- endpoint ledger；
- stop reason ledger；
- bookkeeping ledger；
- 来源去重账；
- native export 和重复导出比较；
- stale/corrupt 负控；
- v3 projection 及 loss manifest；
- replay/resume 和四崩溃边界日志；
- scripted provider 类型、请求登记数、网络数；
- 当前树与父基线的分类结果；
- G01 源清单、白名单、排除项和运行日志；
- 早停、准备错误和未执行内部段的解释。

永久证据目录不得直接运行会写库、日志或结果的程序。README 复现命令必须复制到新 tmp，或明确拒绝已存在输出目录。

证据必须能回答：

- 哪个版本的代码运行；
- 哪个输入运行；
- 哪个入口被调用；
- 哪个权威记录被消费；
- 哪个断言观察到了什么；
- 哪些段未执行；
- 哪些结果是 scripted 合成；
- 哪些结论仍是 unknown/pending；
- 哪些数字不能外推到 dev/298；
- 哪些内容没有访问。

## 12. mimo v16 请求更新

本批必须更新：

```text
docs/mimo_ppv1_chem_review_request.md
```

建议版本标题：

```text
v16（PPV1 S4 endpoint/native export/v3 lossy projection）
```

v16 必须是自包含请求，至少说明：

1. 本批新增或消费的 endpoint 分账字段；
2. `execution_status`、`search_stop_reason`、`chemical_endpoint_assessment`、`bookkeeping_status` 的区分；
3. `unknown`、`metabolic_handoff`、`supported_terminal_transformation_product`、`supported_mineralization` 的边界；
4. evidence basis、source conditions、observation window、root carbon accounting coverage；
5. F01 停止非终点；
6. F02 未知依赖不被 recorded 洗白；
7. F03 重复来源不增加独立支持、不同来路仍保留；
8. 不把账平当矿化；
9. 不把备选 CO₂ 相加；
10. 不自动推解毒；
11. 原生导出的完整性、不同来路、共同产物、备选、条件、依赖、audit、deferred、预算和停止原因；
12. G02 确定性和过期识别；
13. v3 `lossy_projection`、原生引用和信息损失；
14. 旧 legacy/export_v3 冻结；
15. 本批 scripted/off 规则级边界；
16. 未实施的科学性能、真实 provider、金标、题面和封存 run 边界；
17. 本批哪些内容需要只读化学评审，哪些是程序/存储事实，哪些待执行验证；
18. 判据仍未冻结，不能由 mimo、Codex 或本批实施自动宣布冻结。

更新请求时：

- 不覆盖 v15 或更早请求；
- 在本批证据目录保存送审快照；
- 旧回应原样保留；
- 只读模型不能声称执行了测试；
- mimo 只评化学判据部分；
- 程序、存储、版本、测试和证据事实由主会话/Codex独立核对；
- 如果 v16 修改了判据正文、终点含义或新增 hard gate，不能只当文案同步，必须停下按版本规范另行评审；
- 如果只是描述本批实际新增的消费入口且不改变已冻结判据含义，必须明确写出“语义未改变”。

实施 agent 不自行调用外部模型。mimo 请求由主会话按 `AGENTS.md` 规定通道送审。

## 13. 交付书要求

每批必须产出交付书，建议：

```text
docs/POLLUTANT_PATHWAY_S4A_DELIVERY_<日期>.md
docs/POLLUTANT_PATHWAY_S4B_DELIVERY_<日期>.md
```

交付书至少包含：

1. 本批完成项；
2. 未完成项；
3. 与 spec §10/§11/§17 的逐项映射；
4. 与 S3B R3 §7.2、§7.4 的逐项映射；
5. 入口矩阵；
6. endpoint/schema/export/adapter 版本；
7. 实际源码 diff 和提交引用；
8. 实际测试命令和结果；
9. 当前树与直接父 `adf0287` 的红绿分类；
10. G01 隔离范围和结果；
11. 证据目录和 manifest hash；
12. scripted 输入、输出和断言；
13. 预算、事件、attempt、来源和 endpoint 账；
14. unknown/partial/deferred/stale/未执行段；
15. legacy 未改动和回归证明；
16. v3 信息损失清单；
17. mimo v16 请求和送审状态；
18. 判据未冻结、科学性能 pending 和未访问敏感资料声明；
19. 残留 P2；
20. S4b 或 S5 不在本批范围内的事项。

交付书不能把“实现了字段”写成“终点正确”，不能把 scripted 通过写成科学通过，不能把导出成功写成矿化证据。

## 14. 提交纪律

只允许在：

```text
/Volumes/CC/Enzyme_Agent/dependingv43
```

内做 v4.3 本地提交。

必须：

- 使用显式路径执行 `git add`；
- 提交前检查 `git status`、`git diff`、`git diff --cached`；
- 检查提交只包含本批源码、测试、交付书、mimo 请求及按既定规则允许提交的材料；
- 不使用 `git add .`；
- 不使用 `git add -A`；
- 不 push；
- 不带入 AGENTS.md 的既有用户修改；
- 不带入旧的未跟踪 review、mimo 回复或证据；
- 不删除别人的文件；
- 不回写旧报告、旧证据、封存 run 或旧 manifest；
- 只清理本批自建 tmp/worktree；
- 在交付书登记工作区原差异和提交构成。

S4 实施 agent 可以修改必要的 PPV1 源码、测试、交付书和 v16 请求，但不得修改冻结 legacy/G2/AtomTool/export_v3。若共享文件必须修改，必须在交付书中逐项披露 legacy 影响和 identity 影响。

## 15. 实施顺序

建议按以下顺序执行：

1. 记录实际 HEAD、直接父基线和工作区差异；
2. 列完整 S4 入口矩阵；
3. 列现有 endpoint、stop、bookkeeping、native export、legacy adapter 的代码入口；
4. 固定 endpoint、export、adapter 版本和身份字段；
5. 先实现 endpoint 四分账和 F01/F02/F03 共用验证；
6. 编写最小正控、unknown、partial、deferred、停止和重复来源夹具；
7. 接入原生导出，确保全量保真；
8. 加入 deterministic serialization 和 stale detection；
9. 接入 v3 有损适配，不修改 legacy exporter；
10. 接入公共 start/resume/replay 端到端链；
11. 补 resume、首消费、ledger、过期和损坏控制；
12. 运行当前树回归；
13. 在同字节父基线运行新增测试并完成红绿分类；
14. 在新隔离源运行 G01；
15. 生成证据目录、README、manifest 和 SHA256；
16. 更新 mimo v16 和本批交付书；
17. 做一次完整自审；
18. 交主会话进入“实施→mimo→Codex 复审”循环。

## 16. 完成定义

S4a 只有在 endpoint 分账、F01/F02/F03、停止和公共 endpoint 链完成，并有入口矩阵、正负控、回归、G01 和证据时，才可作为 S4a 交付。

完整 S4 只有同时满足以下条件，才可提交复审：

- endpoint 分账独立且可恢复；
- 搜索停止不冒充终点；
- 未知依赖不被 recorded 洗白；
- 重复来源不增加独立支持；
- 不同来路、共同产物和备选关系保留；
- 账目闭合不被解释为矿化；
- 备选 CO₂ 不被相加；
- 不自动推导解毒；
- 原生导出完整、确定性且可识别过期；
- v3 适配明确标注有损并保留原生引用；
- legacy/export_v3/G2/AtomTool 冻结行为不变；
- 公共 start/resume/replay scripted 端到端链真实执行；
- 恢复、ledger 首消费和 `put_state` 契约继续生效；
- 失败、None、unknown、partial、deferred 和未展开集合没有被抹掉；
- 旧 run 没有跨版本续跑；
- 新批实验使用新根；
- 当前树与直接父 `adf0287` 的红绿已如实分类；
- G01 在安全隔离源完成，敏感资料未访问；
- 判分仍为零 LLM；
- 真实 provider 请求为 0；
- S5 科学性能仍明确 pending；
- 判据冻结状态没有因本批改动而改变；
- mimo v16、交付书、证据目录和提交纪律完整；
- 经 mimo 与程序证据互证后，再交 Codex 复审裁定。

本任务书不授权实施 S5，不授权访问金标/题面/封存逐题 run，不授权修改冻结判据，也不授权把工程端到端通过写成污染物路径科学确证。
