# pollutant_pathway_v1 S4b 备用通道独立终审

日期：2026-10-08（Asia/Shanghai）  
结论：**建议 S4b 通过；S4 完成交接点到达；P1=[]**

> 备用通道 `tokeasy/gpt-6-sol` 依协议经 opencode 执行；本裁定为放行级，正链恢复后建议 Codex 正链复核确认。未取得 opencode 会话标识或可独立读取的运行元数据；通道身份按派单声明记录，不冒充正链 Codex 最终裁定。

## 1. 身份、范围与边界

- 阶段／批次／轮次：S4 / S4b / S4 终审（放行级）。
- 实际 HEAD：`8735601b75825388fe9f4a177a1131ef264054a1`；直接父：`fc40605819201ae4a7101fc500b19083d78383b0`。与派单相符。
- 输入：备用通道复审协议、根 `AGENTS.md`、S4 实施任务书（仓内实际文件名为 `POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md`，派单日期名不存在）、S4b 交付书、S4a 复审报告及证据 README、mimo r17 回应、S4b 实施证据 README 与其 G01/父基线/legacy 专项材料、冻结判据正文及本批源码/测试。
- 起始工作树：只有既有 `.zcodeignore`、S4a 复审报告、mimo r16/r17 回复及既有证据目录未跟踪；本轮未改动。审查期间 HEAD 未漂移。
- 审查边界：未访问金标、题面、封存逐题 run、dependingv4；零外部模型、零真实 provider、零 LLM 判分；未 push/commit。测试与探针运行在全新仓外隔离目录，不在永久证据目录执行写库程序。
- 科学性能仍 pending。本文数字只证明合成规则级工程契约，不外推 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）。

## 2. 固定验收矩阵与执行数字

| 验收项 | 独立复核结果 | 证据范围 |
| --- | --- | --- |
| S4b 焦点 | **18 passed，exit 0** | 从 HEAD 复制 `src`（含 vendor）、`pyproject.toml` 与 PPV1 测试到新隔离树，`-B`、禁 pytest cache |
| PPV1 全量 | **932 passed，exit 0** | 34 个 `test_ppv1*.py` 文件；工程契约结果，不是科学性能 |
| 直接父同字节新增回归 | 新文件 **collection/import 红**：父上缺 `native_export.py`；profile 测试 **2 个预期版本/阶段字面量红 + 21 passed** | 父 HEAD 已核为 fc40605；S4a 依赖测试同字节复制；新测试 SHA 与 HEAD 文件相同；没有行为红 |
| G01 安全隔离 | **1534 passed / 8 skipped / 17 deselected，exit 0** | 独立运行指定控制器副本，294 输入白名单，空数据根，无敏感目录 |
| 冻结判据 | **正文零差异** | 冻结稿相对冻结提交 `0e345e8` 与本 HEAD 的 diff 为空 |
| legacy/冻结共享核心 | **与父提交逐字节无差异** | production/store/audit/export_v3/AtomTool/runner/chemstate/path_context/events/search/queue/model_protocol 等保护文件 diff 为空 |

父基线有两次无效准备尝试：初次遗漏 S4a 依赖测试；第二次 `--no-checkout` worktree 未完成 checkout，曾误测到当前树来源。两次均不采信并保留日志。随后新建 detached 父 worktree，按“先 no-checkout、稀疏限定 src/vendor、再 checkout”完成，核 HEAD、`native_export.py` 缺席和同字节测试 SHA 后执行，结果如上。父新增测试在 collection 阶段即因 `ModuleNotFoundError: pathway_v43.pollutant.native_export` 停止；不能把它报告成 18 项行为失败。

G01 的 8 个 skip：真实冻结评价 5、缺失 v4 对照 1、phase-d 派生材料 2；17 个 deselect：slow 16、明确排除 export 用例 1。未补敏感依赖，不为匹配数字改测试选择。G01 首次启动因预建输出目录被控制器拒绝；这是预期安全保护，随后以全新目录完成正式执行。

## 3. S4b 十一项验收矩阵

| 项 | 裁定 | 核对摘要 |
| --- | --- | --- |
| 正式原生文件导出 | 通过 | `native_export.py` 将原生完整 payload 与 manifest 写入 run 目录；目录名取 digest 前 24 字符，manifest 保留完整 digest；同 digest 不同字节拒绝覆盖 |
| 文件级确定性 | 通过 | 18 项焦点回归全绿；交付方 G02 包含同进程、独立子进程和恢复后逐字节稳定测试，本审重新执行焦点套件 |
| stale/integrity 八 kind | 通过 | 读取入口按文件、内容、版本、权威引用、策略、事实摘要顺序 fail-closed；endpoint 首消费先行，endpoint/stop 问题可能先以 endpoint kind 暴露。payload 解析错误可在字节 hash 后或版本门后出现，报告不把它误述为唯一线性位置 |
| 全量事实导出 | 通过 | payload 直接序列化已构建 native result；manifest 覆盖 15 张事实表、artifact 引用与 endpoint/stop/native-result 权威锚 |
| v3 有损投影 | 通过 | 固定 12 条损失轴、原生引用、摘要、lossy 标记与空事件说明具备；不生成终点/矿化/解毒结论、不合并 CO₂；多 reactant collapse 代码披露，但本轮没有夹具实际触发该分支 |
| 双向引用边界 | 通过 | 正向引用核对原生 manifest；反向仅只读列举；契约标记禁止反向消费，投影不写原生 DB |
| legacy/export_v3 字节专项 | 通过（依交付方证据） | 四个 legacy 产物当前/父 SHA 相同；52 份 legacy code_identity 聚合一致。本审读取专项比较记录，未再次执行 legacy 专项探针 |
| 完整公共链 | 通过 | 回归覆盖公共 start/resume、endpoint、导出、投影、读取与 replay；新增代码接线在既有派生链末端，无化学判定入口 |
| G02 七测 | 通过 | 新增测试文件 18 用例独立全绿，覆盖七项 G02 及投影、引用和 replay 控制 |
| S4 全量回归/G01 | 通过 | PPV1 独立 932 passed；G01 独立 1534/8/17 |
| 冻结判据与 S4a 聚合缺口 | 通过 | 冻结稿零 diff；新增模块不解析结构、不构造 `state_id`；`native_result.py` 同时枚举 `action.task_key` 与 `stable_id("soutc", action_id)` 并缺键跳过 |

## 4. 冻结面与继承关闭项

独立检查新增导出/投影模块：`native_export.py` 序列化现有 native result 和 DB/artifact 权威；`v3_projection.py` 读取已有 `state_id` 与 `smiles_isomeric` 字符串，仅作格式映射，不调用化学解析器或身份工厂。`runflow.py` 新接线位于派生完成后的导出/投影区，profile/runflow 版本注册变化不触碰 `ppv1-criteria-v1` 正文。保护文件与直接父逐字节相同。

S4a 已关闭的 P1 与 S3 已关闭组保持关闭；未发现新公共链反例证明 unknown/partial/deferred/失败被升成成功或 verified。S4a 的 `soutc:<action_id>` 聚合缺口修复方向正确：调度结论由第二种真实写入键读取，既有 `action.task_key` 仍保留，缺键自然跳过。此修复是补全失败/unknown 事实，不是化学判据变更。

## 5. 已接受边界与 P2

无阻塞 P1。保留以下明示边界，不作为本轮额外阶段门：

- stop 视图含会话成分；相邻 resume 可合法更新 stop/endpoint 并产生新 digest。旧文件保全，事件/预算零新增是硬边界。
- 不防持有数据库、artifact 与导出文件写权限者进行全库协同改写；不宣称签名级防篡改。
- digest 目录名使用 24 字符前缀，完整 digest 在 manifest/载荷中核对。
- v3 多 reactant collapse 分支本轮未由公共链夹具触发；其规则为读码披露，不声称动态覆盖。
- 行号锚定随 runflow/profile 漂移，待下一判据版本统一重锚；不影响本轮冻结正文零差异结论。
- mimo r17 提出的目录名写法、endpoint 拒绝优先级文字和“914 存量零改动”精度建议，属于请求/交付描述修整。请求与实施测试版本变更的说法不作为代码阻塞；交付书已披露两处 profile 字面量更新。放行不替代后续文档精度整理。

## 6. mimo 与交付声明互证

mimo 对判据一至五及 0g 的结论为同意级；所有执行类声明均按“待执行验证”处理。本审独立执行了 PPV1 焦点、全量、父基线分类和 G01；legacy 四产物专项与 52 文件聚合采用交付证据记录并核对其明确比较值，未冒充本会话执行。mimo 提醒的 24 字符目录名、endpoint 首消费优先与多 reactant 未覆盖均与源码/交付披露相符。mimo 的程序执行声明不作为独立执行证据。

## 7. 结论与 S5 前置交接清单

**建议 S4b 通过，P1=[]；按任务书达到完整 S4 工程完成交接点。** 备用通道建议，不替代正链 Codex 最终裁定；正链恢复后建议复核确认。判据仍为 `ppv1-criteria-v1`，未由本审冻结或改变。

S5 前置条件与交接状态：

- S4 endpoint 分账、原生导出、v3 有损投影、完整公共链与 G02 工程交付通过本轮备用通道审查。
- S5 科学评测器、数据规范、留出实验、真实 provider/付费实验与统计预注册均未启动；金标、题面、封存逐题 run 未访问。
- 判据冻结状态、终点阈值与统计方案仍属用户裁定，不由本报告自动宣布。
- 科学性能 pending；所有工程数字仅属合成规则级结果，不外推 dev 或 298 题域。
- 遗留 P2 见 §5；无待修 P1。

通过时没有回修提示词。交接仅覆盖 S4 完成事实，不授权自动启动 S5。

## 8. 下一轮提示

本轮无 P1 回修项。若启动 S5，必须另有用户授权、S5 任务书与预注册方案；不得把 S4 合成工程结果当科学性能或金标证据，不得自动冻结/改写化学判据。S4 本批本地审查证据位于 `docs/review_evidence/ppv1_s4b_codex_2026-10-08/`。
