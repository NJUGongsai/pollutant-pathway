# TEACHER_REPLY：T6-R3 六项合同裁定与收口

- 回复对象：陈浩然《T6-R3 真实执行审计与裁定请求》（2026-09-11）
- 裁定日期：2026-09-11
- 裁定性质：一次性定案。你方只按批准的最小契约做新版本验证，不改写我未授权拓扑。

---

## 一、总体判定

我已收到并核实 T6-R3 真实运行审计证据包，返回包校验一致。本轮暴露的问题分两类：

1. 我侧固定合同尚未下发/收口的部分（第 1、3、4、6 项），现逐项裁定并已落定；
2. 你方证据口径需纠正的部分（见第三节），属证据工具修正，不触发科学重跑。

---

## 二、六项裁定

### 1. enviPath known-route lookup 与 HIT/MISS edge —— 不入本轮固定图

我判定：本轮 T6 固定图只做**冻结参考反应库的相似度检索（Route C 相似检索）**，这是已授权的确定性路径，**不再声称 enviPath lookup-first**。enviPath known-route lookup 作为可选增强另行立项，不阻塞 T6 收尾。

你方证据测试应以「相似度检索」为唯一检索语义判 PASS/FAIL，不得再按 enviPath known-route HIT/MISS 语义判 FAIL。

### 2. MISS 后正式 predictor —— BioTransformer ENVMICRO

我确认：lookup MISS 后的正式 predictor 为 **BioTransformer ENVMICRO**（确定性规则引擎，无概率；产物按环境细菌酶标注，不作为酶唯一标识直接下发）。**depending v3.2 仅作离线评价候选（evaluation candidate），不进入正式图路径。**

你方不得把 depending v3.2 当作图内正式 predictor 来判 PASS/FAIL。

### 3. 来源标签 / 来源工具强制保留 —— 已收口

我判定并已落定：候选反应的**来源标签与来源工具字段强制非空**；检索来源显式标注；**未知来源必须显式写 unknown/unavailable，禁止默认 enviPath**；多步路径输入的来源工具同样改为必填。

此项属我方职责，你方只需按新契约消费字段，无需自行补写来源。

### 4. 统一公共 ID 合同 —— RT-{16hex}

我判定：统一公共 ID 合同为 **RT-{16hex}**（前缀 `RT-` + 16 位十六进制）。**图内单步与多步桥接统一由我侧生成 RT-\***；T5 维持只接受 `RT-{16hex}` 不变。跨组件对应关系由我侧持久化。

你方不再需要手工 reattach，也不需要同时兼容两种 typed ID。

### 5. 无 LLM 时选菌层是否降级 —— 不允许

我确认：**选菌层对外判断能力是硬依赖，无凭证/超时/限流/断网必须显式终止（fail-closed），不允许确定性降级直通 trait/synthesis**。这是既定约束，不是缺陷。

因此本轮「图运行到选菌层显式终止 + 图外组件可调用性测试」的组合证据，我接受，状态命名为：

- 图内：闭环至选菌层；
- 选菌层及以下组件：图外可调用。

若你方要验证完整闭环，正式运行需提供受控 LLM 配置。

### 6. canonical lowercase aromatic SMILES —— 入口直接接受

我判定：生产入口**直接接受 canonical lowercase aromatic SMILES，不要求上游统一转 Kekulé**。入口已加不依赖 LLM 的 RDKit 解析硬门，并保留「原输入」与「规范化输入」两个字段。

你方测试应以「直接输入 lowercase aromatic SMILES 可通过」为预期，不得再要求上游转 Kekulé 才能跑通。

---

## 三、你方证据口径需纠正处（零模型，不重跑）

1. TEST-03 → `NOT_ESTABLISHED_REAL_GRAPH`（不计入 PASS）。
2. TEST-04 → `FAIL_SOURCE_PROVENANCE_NULL_AND_FALSE_ENVIPATH_DEFAULT`。
3. TEST-11 → 分母混用需拆分报告：branch occurrence / unique upstream task / 每条 route 的 step denominator 三类分别统计。
4. TEST-12/16 → `C8_AND_T5_PRODUCTION_CALLABLE_PASS_AFTER_REATTACH`，且 `GRAPH_CONTINUOUS=NOT_ESTABLISHED`；不得把图外 typed reattach 写成图内 C8→T5 连续通过。
5. TEST-17 → `PASS_REAL_GRAPH_EXECUTION_WITH_TERMINAL_FAIL_CLOSED_LIMITATION`。
6. mutation 补齐原科学合同（非只 13 项环境/运输门）；access 判「仅授权 UniProtKB/KEGG，unauthorized=0」；rxn2fp.pkl 正确身份 6500 bytes，必须纳入总布尔门。

以上均为证据工具修正，不触发科学重跑。

---

## 四、你方下一步配合行动项

1. 停止重跑模型与当前老师 graph（不必要，避免再耗十几小时）。
2. 做一次零模型证据纠正，并冻结修正后的 finalizer/validator。
3. 收到我下发的 base/patch 后，复用本轮固定 Python、LightGBM overlay、资产 registry、GPU worker 与 runner；先跑 ≤2 分钟 Python/import/schema/runner smoke，任何 runner 类型错误在此暴露。

---

## 五、红线约束

- 不改写我未授权拓扑。
- 不把图外 reattach 写成图内连续通过。
- 不把来源空（null）视为来源保留。
- 不混用 occurrence 与 unique task 分母。

---

## 六、附录：入口 SMILES 硬门行为验收样例（裁定 6 配套）

为便于你方做零模型证据纠正时对齐 PASS/FAIL 判定，我给出入口硬门的行为样例：

| 输入示例 | 预期结果 |
| --- | --- |
| `c1ccccc1`（lowercase aromatic 苯环） | 接受；规范化后即为 `c1ccccc1` |
| `C1=CC=CC=C1`（Kekulé 苯环） | 接受；「原输入」为 `C1=CC=CC=C1`，「规范化输入」为 `c1ccccc1` |
| `Clc1ccccc1`（lowercase aromatic 氯苯） | 接受 |
| `degrade benzene using enzyme`（自然语言，非 SMILES） | 拒绝（不被误识别为 SMILES） |
| 无法被分子解析器解析的任何字符串 | 拒绝（不得作为候选底物进图） |

判定口径：接受/拒绝均以不依赖 LLM 的分子解析硬门为准；凡解析失败的输入一律拒绝进图。你方测试以「直接输入 lowercase aromatic SMILES 可通过」为唯一预期，不得再要求上游转 Kekulé 才能跑通。