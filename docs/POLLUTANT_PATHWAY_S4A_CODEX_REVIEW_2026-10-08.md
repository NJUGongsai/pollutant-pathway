# pollutant_pathway_v1 S4a 备用通道独立复审

日期：2026-10-08（Asia/Shanghai）  
结论：**建议 S4a 通过，可启动 S4b；P1=[]**

> 本报告由备用通道 `tokeasy/gpt-6-sol` 经 opencode 依
> `docs/PPV1_REVIEW_PROTOCOL_2026-10-08.md` 独立执行。它不是 ChatGPT
> 账号 Codex 链式评审，不替代正链最终裁定；正链恢复后可复核。

## 1. Provenance 与范围

- 阶段／批次／轮次：S4 / S4a / 首轮复审。
- 实际通道／模型：opencode agent，派单指定 `tokeasy/gpt-6-sol`。
- opencode 会话标识：未取得运行元数据。
- 实际 HEAD：`fc40605819201ae4a7101fc500b19083d78383b0`。
- 直接父：`0e345e83de27e7369334fe092da7a6ccbc8afd6c`；S4a 源码基线为
  `adf0287abef0c4803962fee0df0065d8e6f3793d`，父提交在 `src/` 与
  `tests/` 面同字节。
- 环境：`/Users/cc/miniconda3/envs/depending43/bin/python`，Python
  3.11.16，RDKit 2026.03.6，SQLite 3.53.4，macOS arm64。
- 输入：协议、S4a 交付书、S3b-r3 终审与证据 README、S4 任务书、AGENTS、
  mimo r16，均按派单绝对路径读取。
- 工作树既有差异：`.zcodeignore`、mimo r16 回复及其证据目录未跟踪；本审未改动。
- 执行中断：首轮 PPV1 全量因多文件参数错误未执行，未采信；首轮 G01 超过
  120 秒被工具超时，未采信。两者均在 HEAD 与输入未漂移时按原命令重试并完成。

未访问金标、题面、封存逐题 run、dependingv4；未调用外部模型、真实 provider 或
LLM 判分；未 push、commit，也未在永久证据目录运行写库程序。

## 2. 固定验收矩阵与独立数字

| 验收面 | 本审结果 | 证据范围 |
| --- | --- | --- |
| S4a 新焦点 | **35 passed / 0 failed，exit 0** | 四分账、F01/F02/F03、根碳账、首消费、native result、公共 start/resume 链 |
| PPV1 全量 | **914 passed / 0 skipped / 0 failed，exit 0** | 33 个 `tests/test_ppv1*.py` 文件；工程规则级，不是科学性能 |
| 直接父新增测试 | endpoint 文件 **35 collection/import 红**；profile **2 预期字面量红 + 21 绿** | 同字节测试，无 stub、无弱化断言 |
| G01 安全隔离 | **1516 passed / 8 skipped / 17 deselected，exit 0** | 291 个当前输入，白名单复制到新 tmp，网络 0 |

G01 的 8 skip 为 5 个真实冻结评价、1 个 v4 对照、2 个 phase-d 产物缺失；17
deselect 为 16 个 slow 与 1 个明确 export 用例。没有为补数字复制敏感依赖。

## 3. S4a 逐项裁定

| 项目 | 裁定 | 核对结果 |
| --- | --- | --- |
| 四分账与独立持久化 | 通过 | execution、stop、endpoint、bookkeeping 独立存在；两张派生表；停止不覆盖有效 endpoint 证据 |
| F01 停止非终点 | 通过 | 六值停止枚举；预算、深度、空池等无独立证据时保持 unknown；deferred/unexplored 保留 |
| F02 依赖不洗白 | 通过 | 被引用上下文中非 supported 依赖继承为 unknown；recorded 边不升级终点；有正控 |
| F03 三态去重 | 通过 | 同观察多包装、同来源多声明、不同来源及 model/inferred 贡献均有断言；原始条目保留 |
| 根碳账 | 通过 | closed 只表示声明范围内闭合；未知系数／悬空引用保留 unknown/not-closed；CO2 备选不相加 |
| 终点证据与条件 | 通过 | direct/inferred/model/no-evidence 分开；缺字段逐项披露；条件冲突不提交；proof scope 保留 |
| endpoint 首消费 | 通过 | 版本、载荷 hash、stop 交叉引用、四摘要 staleness 与五类拒绝控制具备；原行保全 |
| 原生结果对象 | 通过（S4a 范围） | 字段聚合、不同来路、deferred/blocked、对象级确定性 digest、读回完整性具备 |
| 公共 endpoint-only 链 | 通过 | start/resume 均为驱动→停止→四分账→首消费→原生对象；无新 event/attempt/request/budget 写入 |
| v3/legacy 边界 | 通过 | S4a 明确未实施 v3 适配；`production.py`、`export_v3.py`、AtomTool 与共享核心未改 |
| 冻结判据一致性 | 通过 | `POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md` 与 HEAD 零差异；新增入口不产生化学身份或 verified 证据 |

## 4. P1 与边界

没有发现既有 S4a 契约内的 P1 阻塞，也没有证据表明 unknown、partial、deferred、
失败或必要依赖被升格为 verified/R6。S3 已关闭组保持关闭，未发现新的同契约反例。

以下保留为已披露的 P2／文字精度注意事项，不阻塞 S4b：

1. endpoint 载荷包含 stop 摘要副本，权威仍是 `stop_reason_records`；交付书的
   “不复制其语义”应理解为不以副本替代权威，而不是字面上的零复制。
2. payload 与 hash 同步自洽改写、且不改变四摘要和引用的协同写权者，不在本轮
   检出面内；这与 S3B-01 的协同改写边界相同，不应对外表述成签名级防篡改。
3. `native_result.py` 读取 H07 信封完整性；上下文内容身份的 `from_dict` 首消费
   由 endpoint 派生侧承担，原生对象侧不重复做同一核验。
4. S4a 的对象级确定性和 endpoint 记录级 stale 不等于 S4b 文件级导出/G02 完成。
   S4b 的正式导出、v3 有损适配、文件级过期矩阵和完整公共链仍未做。

这些边界已在交付书 §19–§20 或实现注释中披露；它们不是冻结判据正文冲突，也不是
本批新增 P1。

## 5. 交付与 mimo 互证

mimo r16 对判据一至五及 0c/0d/0e/0f 的化学意见为只读输入，执行类均标为待验证。
本审独立确认：冻结判据正文未改；S4a 新入口主要是持久化、聚合和消费边界；测试和
G01 数字由本审实际执行取得。mimo 指出的 A 级文字精度项中，未发现会把本批实现
变成冻结判据 P1 的项目；本报告保留上述可核查边界，未把交付方数字冒充科学证据。

所有数字仅为合成规则级工程证据，不外推 dev（B1 环境路径中间步骤）或 298（RHEA
通用酶学）科学性能；科学性能、真实来源真实性和判据冻结权仍 pending／属用户裁定。

## 6. 结论与交接

**建议通过 S4a，P1=[]，S4b 可启动。** 这只表示 endpoint 分账、S4a 首消费和原生
结果底座满足本轮工程验收；不得写成完整 S4、污染物路径科学确证、矿化确证或文件级
导出已完成。S4b 开工时应继续保留本报告列出的协同改写、H07/内容身份分层和对象级／
文件级确定性边界，并按任务书新增正式导出、v3 projection、G02 和完整 start→replay
链验收。

## 7. 下一轮有限提示词

本轮通过，无 P1 回修项。若进入 S4b：基于 HEAD
`fc40605819201ae4a7101fc500b19083d78383b0`，先读取本报告、S4 任务书 §7–§8、
S4a 交付书 §19–§20 和本证据 README；只实施 S4b 正式文件导出、v3 有损投影、
文件级 G02/stale/integrity、完整公共链及相应回归。保留 S4a 的 stop/endpoint 独立
权威、unknown/partial/deferred/失败、不同来路与 CO2 不相加控制；不得改冻结判据、
legacy/export_v3、AtomTool、金标/题面/封存 run 或 dependingv4。新批次使用新 tmp、
新证据根和新 manifest，父子同字节分类、G01 白名单、零网络／零 LLM 判分规则不变。
