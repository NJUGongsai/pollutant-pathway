# 教师裁定回复：T6-Full F2-R1 无 LLM 凭据下 organism_selection fail-closed 的定性

**结论**：你方将"无 LLM 凭据时真实 LangGraph 于 organism_selection fail-closed"定性为 production 拓扑问题、并要求我修复连续路径 + 提交新 commit，**我不认可，予以驳回**。这是选菌层 LLM 硬依赖不可降级的设定内正确行为，不是缺陷。本次**无代码改动、无新 commit**，现有 00574c8 即最新基线，无需且不应改造我方 production 拓扑。

## 一、fail-closed 是刻意裁定，不是缺陷

M5 后端里，调用 LLM 的节点有两处，但在我方裁定下待遇不同：

| 节点 | 角色 | 无 LLM 凭据时的行为 | 裁定依据 |
| --- | --- | --- | --- |
| reranking | 增强项 | 诚实回退原排序 passthrough，继续走图 | 可降级 |
| organism_selection | 核心价值 | 显式 fail_closed，图终止 | 硬依赖不可降级 |

其余后端组件（microbe 的酶→菌映射 + MT-D3 聚合、trait 的 M4b 锁定 soft-passthrough、synthesis 确定性拼接、reaction_prediction 的 BioTransformer 规则引擎）全部确定性、不调 LLM。

同一个无凭据环境里，reranking 降级通过、organism_selection 截断终止，正是两者在我裁定下"刻意的差别待遇"——**选菌层的多因素综合判断是不可替代的核心价值，LLM 不可用即显式 fail_closed，绝不静默按聚合分直通透传（禁止"无面试录取"）**。这一红线在 T6-R3 裁定 5 及更早已多次落定，此处不是 bug，无可修之处。

## 二、选菌层只存在两种合法结果，没有"既 fail_closed 又继续"的第三态

1. 无候选菌（上游未产出 reviewed 宿主）→ 优雅跳过，图继续（代码已支持）。
2. 有候选菌但 LLM 不可用 / 响应不合法 → 显式 fail_closed，图终止（代码已支持）。

你方场景是有候选菌 + 无凭据，落入第 2 种，必须终止。你方所提"使无 LLM 凭据的合法确定性路径进入 trait 与 T5"，本质是把第 2 种降级成"确定直通"，等同"无面试录取"，撞我方红线，不能成立。

## 三、graph_continuous=false 是诚实且正确的标记，不影响 T6/G7 验收

T6-R3 裁定 5 已明确接受"图内至选菌层 + trait/T5 图外确定性组件测试"的组合证据模式。graph_continuous=false 是如实标记，不是扣分项，也不需"修复"成 true。

trait 与 synthesis 均为确定性组件、不依赖选菌 LLM 输出，图外调用与图内调用的结果是等价的；因此你方图外验证 + 图内至选菌层，已构成完整的组合证据。T6/G7 的验收点是六个 production 能力的真实证据 + trait/T5 确定性组件的验证，这两点你方均已具备，保持现有诚实标记即可。

## 四、图内端到端证据的唯一合法路径，是有凭据方真跑

graph_continuous=true 只能由持有 LLM 凭据的一方在真实凭据下跑通 organism_selection 获得，这属我方（或 CI 注入凭据）能力范围，不在无凭据学生侧的自证范围内。你方无需、也不应为达到 graph_continuous=true 而改造我方 production 拓扑。

## 五、你方后续动作

1. 保持现状：不改我方 production 代码，维持现有诚实标记与组合证据。
2. 无新 commit 可复核；如需针对 00574c8 重跑最小 CPU smoke 以留痕，可自行安排，我方此处不改代码。
3. 若你方认定"图内端到端"是某项外部验收的硬性要求，请把该验收标准原文给我，我方将评估是否由凭据侧补一次全链路真跑，而不是改造拓扑。