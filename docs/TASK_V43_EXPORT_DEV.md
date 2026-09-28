# v4.3 第四阶段实现任务书：评测导出、dev 批跑与对照分析

> 交给独立执行模型实现并在 Chenyu 执行；本会话负责 review。目标仓：`/Volumes/CC/Enzyme_Agent/dependingv43/`，远端通道与布局见 `docs/CHENYU_ACCESS.md`。起点是已验收的 PredictionAgent/AtomTool 阶段（168 项测试、资产 21/21、MoleCode vendor 7/7）。先读本仓 `ARCHITECTURE.md`、`REPO_DESIGN.md`、`docs/PREDICTION_ATOMTOOL_REPORT.md`，以及 v3 `evaluation/pathway_benchmark/PROTOCOL.md`、`eval_pathway_benchmark.py`、`split_manifest.json`。v4 的 `src/pathway_agent/export.py` 只作旧实现参考。

## 0. 本轮目标与红线

交付从 v4.3 的**已校验可报告候选与已提交 PathwayStore 化学事实**到 v3 冻结预测格式的确定性导出器、可恢复的 dev 批跑入口，以及只读调用 v3 冻结评测器的对照报告。在 Chenyu **同时启动 dev 20 条路线的 20 个独立作业**，用其 DashScope **按量付费** OpenAI 兼容 API 的 **`ZHIPU/GLM-5.3-Flash`** 完成真实预测、导出与判分。官方模型 ID 的大小写固定如上；`ZHIPU/GLM-5.3-FlashX`、`glm-5.3` 等均不是本轮模型。用户本轮已明确授权这次 dev 按量调用；不要把 `docs/CHENYU_ACCESS.md` 中针对旧任务的再次批准流程当作阻塞。模型 ID、请求参数、用量和账单口径必须冻结在批次身份中。

本轮**不运行 100 条 eval、298 外考或任何冻结外考切片**，不修改 v3 金标、评测器、split 或资产，不用 dev 金标来构造模型提示词、检索查询或逐题选择策略。v3 的路径基准是 EAWAG 语料图拼接，且库根与检索语料高度重合；dev 指标是此基准上的路径/排序表现，不能宣称是环境泛化能力。真实模型不可用时，不把 fake 模型的数字写成真实模型效果。

## 1. 确定性导出契约

新增 `output/export_v3.py`（可调整文件名），从持久化的**已校验可报告候选**和 PathwayStore 的已提交事件构造一行一路线的 JSONL：

```json
{"route_id":"pb_0001","root_smiles":"...","steps":[{"parent_smiles":"...","predicted_products":["...","..."]}]}
```

- `route_id` 来自输入任务映射，`root_smiles` 保留该路线的原始输入；不得用 `path_id`、显示名或规范身份字符串冒充原始 SMILES。`steps.predicted_products` 取**已通过确定性门禁、被策略接纳为可报告**的有序候选，最多五个；其中只有被选入 frontier 的产物才继续展开。检索原始卡、模型原文和被拒产品不能因为“在前五名”就进入答卷。需要新增不可变的候选裁决产物/账本字段，记录每个候选的 `evidence_id`、验证引用、`report_rank`、`reportable` 与 `expand_selected`；它是预测声明，不冒充已提交 ReactionEvent。一个已提交多产物事件的有效产品可同时进入可报告列表；暂缓展开不等于被拒报告。
- 现有报告的 `top5_candidates` 是**检索卡**视图，不能直接拿来当 v3 答卷。实现需另给 `top5_reportable_products` 视图，明确它与检索前五、已提交事件和 frontier 的关系；同一父路径的可报告候选若少于五个，不用未验证检索结果补齐。若另算“检索池候选命中率”，必须单独命名为诊断指标，不混入路径答卷的正式分数。
- 一个 ReactionEvent 的多个有效产物按保存的 `position` 排列；多张可报告证据卡按冻结的候选裁决顺序排列。相同父分子从不同来路到达，保留 PathInstance 供研究报告使用；导出到 v3 平面格式时按评测器的“同 parent 首现合并”语义投影，并记录这一信息损失。相同规范产物只保留首次出现的排名；不得让 SQLite 无序查询决定 rank。
- 产物的 `product_smiles_full` 与 `product_smiles` 的选择要写成固定规则，经过 v3 `cn` 与 `raw_sb` 两口径夹具验证；不可把 `cn` 身份值当作 raw 产物。导出前校验根、父、产物 SMILES 可解析，遇账本损坏给结构化失败，不静默删边。
- 导出排序、去重及每个 parent 的 top-5 上限要明确并写入导出 schema/配置；排序依据是**已验证的报告位次**，不是检索证据排名。导出结果可从同一持久账本/候选裁决产物重复生成，哈希一致；不能调用 LLM 或重跑 ReactionFinder。
- `export --run-id ... --route-id ...` 读现有 run，产出 `runs/<run_id>/predictions.jsonl` 和导出元数据（run identity 哈希、账本 revision、导出 schema/策略哈希、行数、文件 SHA256）。导出是可重建的派生结果；若账本 revision 或导出策略变化，旧产物必须显式失效/重生成，不让过期文件通过判分。

## 2. dev 批跑与隔离

新增 `batch --split dev` 或等价入口。只从 v3 冻结 `split_manifest.json` 取得 dev 的 20 个 `route_id`；运行侧输入清单只含 `route_id`、`root_smiles` 与输入/来源哈希，不含 gold `edges`、`gold_leaves`、provenance 或逐题答案。若从 `gold_routes.jsonl` 提取输入，提取动作须隔离为一次性只读取白名单字段的工具；把生成的输入清单随报告保存并核查恰为 20 条、与 eval ID 不相交。PredictionTask 与模型请求中不得出现 gold 字段或 dev/eval 金标。

- 每条路线使用稳定 run_id（含批次身份和 route_id），单条失败不使整批结果不可复核；批次配置、资产/代码/提示词/模型身份、预算和输入清单 SHA 写入 batch identity。重复执行已完成项只读复用，未完成项走既有 `resume`，同 ID 不同配置报冲突。**固定 20 路并行**：一个协调进程一次性分配 20 个 route_id，启动 20 个独立 OS 进程；每个子进程只写自己的 run 目录和 SQLite 文件。共享的仅为只读代码/资产与协调器的进度、API 额度账。禁止多进程共写同一个 `pathway.sqlite`/checkpoint，禁止在已装载 RDKit/LightGBM/OpenMP 的进程里用 `fork` 复制引擎。`OMP_NUM_THREADS=1` 随每个进程设置；输出按冻结的 dev route_id 顺序归并，不按先完成顺序。远端内存/CPU/磁盘预检须证明 20 个进程可同时承载；达不到时明确报容量阻塞，不暗改为串行。
- 协调器记录 20 个 worker 的 PID/route_id/启动时间/心跳或完成标记/退出码，并保留各自日志；远端用 `nohup` 或等价守护方式启动协调器，短 SSH 连接只做状态查询，避免长连接超时。启动、重连、重复命令或单 worker 崩溃时只恢复未完成路线，不再发已持久化的模型请求；最终 20 个 route 都应有唯一终态。日志进度以持久状态/目录计数为准，不把 stdout 暂无输出判成卡死。
- 对失败、预算耗尽、`awaiting_prediction`、模型不可用、无效输入等路线仍生成**显式空或部分答卷**，保持 20 行且每个 route_id 恰出现一次；另列每条状态与未完成原因。不能因困难题被跳过而抬高总体分数。
- `off` 模式可作为 20 路确定性对照；`fake` 仅用于协议/恢复测试，不进入模型效果表。主臂必须是 Chenyu DashScope 按量 API 的真实响应；若远端凭证/权限不可用，明确 `not_run:no_credentials_or_access`，不以 fake 代跑。记录逐条模型调用、孤儿请求、输入/输出/缓存 token（响应提供时）、费用（账单可核对时）、耗时和展开节点；未知费用标 `unknown`，不可估算后当实测。

## 3. Chenyu 部署、DashScope 接线与费用约束

- 按 `docs/CHENYU_ACCESS.md` 找到远端通道和独立工作区；先核查该文档中的 SSH helper、工作区和 Python 环境当日仍可用。为 v4.3 建**独立远端目录/环境**，不覆盖 `dependingv4_v41`、`dependingv4_v42fix` 或任何旧 `runs/`。本地 v4.3 可能不是 Git 仓，不可假设 `git bundle` 一定适用；若无 Git 历史，用可复核的文件同步并记录本地/远端代码文件清单 SHA。v4.3 `assets/` 必须是本仓实际文件，不以指向旧仓的 symlink 绕过资产根边界。远端装 Python 3.11 及项目锁定依赖，核对 21/21 资产、7/7 vendor 和旧 168 项测试；v3 冻结代码/评测器用只读路径。
- Chenyu 已预置 `/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env`（权限 `0600`，在代码目录外），含 `V43_LLM_BASE_URL`、`V43_LLM_API_KEY`、`V43_LLM_MODEL`；正式作业从该文件读取，不复制到本地仓库、打印变量值或在报告中给出密钥。部署代码时保留此文件，不用同步命令覆盖/删除它。用户给出的 `https://dashscope.aliyuncs.com/apps/anthropic` 是 **Anthropic 兼容**入口；本仓现有 `OpenAICompatibleClient` 调 `/chat/completions`，故 `.env` 使用同一北京按量服务的 **OpenAI 兼容**入口 `https://dashscope.aliyuncs.com/compatible-mode/v1`。若以后改用 Anthropic 协议，须另写并验证适配器，不能只替换 base URL。此模型官方仅列**华北2（北京）**：核查该地域 Key、模型权限与端点一致，不误接 token-plan 端点。批次模型 ID 必须精确为 `ZHIPU/GLM-5.3-Flash`，20 路完全相同，不在 429 或失败时私自换模型。
- 当前 `OpenAICompatibleClient.complete()` 无条件发送 `temperature=0.0`、默认 60 秒超时，且把 HTTP 429 混入普通传输失败。GLM-5.3-Flash **仅支持思考模式**；首版请求省略 `temperature`、采用官方默认 1.0，并显式锁定 `reasoning_effort`（首次 dev 用官方默认 `max`，如烟测证明需调整则在正式发车前定版）。不能发送关闭思考的参数。配置适配思考模型的超时、输出 token 上限和三协议请求参数，检验 `choices[].message.content` 与独立 `reasoning_content` 的处理：解析候选只取最终 content，usage 含思考输出 token。以**一次真实、低额度的远端 API 烟测**确认模型在此工作区已开通、参数可用、最终 content 与 usage 能解析，再同时启动 20 路。烟测与正式批次的调用和用量分开记录，正式批次不混用测试响应。
- 20 个路线作业必须并行，但 API 额度是**主账号/模型共享**的。协调器使用跨进程共享的请求闸门，按实际模型的 RPM/TPM 与响应状态管理发起速率；对 HTTP 429 记录 status、可用的 `Retry-After`/请求 ID，做有上限的指数退避和抖动，不能把 429 当化学失败，也不能无界重试。403/余额或权限错误停止新付费请求并保留已完成事实。提供者是否兑现 `Idempotency-Key` 不可假设；沿用本仓 issued/response/orphan 审计，悬空调用计入额度，重试可能重复计费要如实报告。真实 HTTP 请求只由 LLM adapter 发出。
- 启动前固化每路线 `max_expansions/max_depth/max_frontier_width/max_llm_calls/max_proposals`、每次输出 token 上限和**整个批次的最大 API 调用数/估算 token 及费用上限**；协调器以持久原子预留管理全局调用预算，达到上限时停止新请求，保留 20 路部分答卷和原因。官方模型页当前列北京原价：输入 **¥0.8/百万 token**、输出 **¥2.8/百万 token**、缓存命中输入 **¥0.23/百万 token**，限流 **200 RPM / 3,000,000 TPM**；思考 token 按输出计费。发车前仍要用当日控制台价格/限流复核并把快照/时间写入 batch identity；账上费用与返回 usage、估算值分列。若正式批次有多次尝试，保留每次 attempt 的状态与用量，不覆盖历史。

## 4. 冻结评测器与对照报告

只读调用 v3 `evaluation/pathway_benchmark/eval_pathway_benchmark.py --split dev --predictions ... --out ... --per-route`；先核对 v3 benchmark 清单/协议和评测器身份，禁止在 v4.3 另写一套“等价判分”替代它。评测全过程零 LLM。保留评测器原始 JSON，再生成便于比较的研究报告。

报告至少并列 `cn` 主口径与 `raw_sb` 对照口径：step hit@1/3/5（按金标边 micro）、route recall、gold-leaf reached、spurious rate（后三者按路线 macro）；v3 原生的 S/M/D 分层照原样报告。来源（已记录/规则/类比/新提案）、路径深度和停止原因按 v4.3 账本另做**描述性诊断**，注明归属规则、样本量与分母，不能冒充冻结评测器原生切片；无样本写 N/A。不能把引擎跨来源 score 当校准概率。报告同时列已报告 top-5 与实际展开数量、LLM 调用数、成本和耗时。

对照只用**同一 dev 20 路、同一冻结评测器与相同口径**的历史 v4.1/v4.2 答卷；若历史答卷缺失或其输入/配置口径不同，先标明不可直接比较，不补造基线。优先给逐路线差异与失分类型（候选未生成、候选在第 6 位以后、被门禁拒绝、未展开、模型弃权、预算停止），再汇总总分。任何 dev 调参都记录配置版本、运行先后和选择依据；在进入下一阶段前只选一套冻结候选，不用 eval 选配置。

报告必须保留 v3 协议的两项限定：整条金标路线由语料图拼接，未作为整体实验验证；公开 EAWAG/enviPath 可能进入模型预训练，且本仓检索资产与 dev 金标同源。外部 298 单步结果与本路径基准指标不同，若引用历史数字须分表标注，不能直接作提升百分比。

## 5. 必须覆盖的验收用例

1. 合成账本：单反应多产物、两个事件竞争、同一分子经两来路汇合、路径内循环、有效/无效产物混合、仅检索未校验、已校验但未展开、`awaiting_prediction`、deferred 子路径；逐字比较导出 JSONL 的 parent、顺序、去重和 rank。尤其证明**可报告未展开产品进入该步答卷，但不会凭空产生下一步**；未经接纳的检索前五绝不进入答卷。
2. `cn` 与 `raw_sb` 电荷形态夹具：中性/阴离子同身份在主口径命中，保电荷口径按原始形判；导出不得提前中和原始字符串。一个父分子重复出现时结果与 v3 评测器首现合并语义一致。
3. 同一 run 重复导出字节/哈希相同；事件新增或 revision 改变后旧导出被识别为过期；数据损坏或同一 route_id 多行时失败并保留拒因。
4. dev 批次恰含 20 条且与 eval 100 条不相交；以屏障夹具证明 **20 个 worker 在同一时间处于运行态**，并证明每个 worker 的 SQLite 与结果目录隔离、API 闸门跨进程共享、最终归并顺序固定。故意杀掉 1 个 worker 后恢复，最终仍 20 行无重复，失败项按空/部分答卷计入；运行侧和模型请求不含 gold 字段。
5. 模拟 DashScope 429、403、超时、悬空请求与重复启动：429 退避后继续且不产生重复事件，403 停止新请求，账单/调用预算不漏记；GLM-5.3-Flash 的模型 ID、仅思考参数、最终 content 与 reasoning_content 分离、usage 解析及凭证脱敏均有回归夹具。无网络测试不得代替正式远端 API 烟测。
6. v3 冻结评测器 CLI 对 v4.3 导出真正执行 `--split dev`，产出 `cn/raw_sb`、分层和逐路线结果；脚本/日志证明未调用 `--split eval`。全部新增测试可在无模型凭证环境运行。
7. 既有 168 项回归不退化，远端资产 21/21 与 MoleCode vendor 7/7 清单通过。正式批次须有 20 路真实模型身份一致的运行产物；报告完整命令（凭证脱敏）、20 worker 启停时间、远端依赖和资源峰值、API/费用统计、产物 SHA 及实际失败与恢复记录。

## 6. 交付与 review 门槛

交付 `docs/EXPORT_DEV_REPORT.md`、README 命令、导出 schema/策略、20 路输入清单、batch identity、逐路线状态、20 worker 的进程与时间证据、API request/usage/费用账、v3 原始评分 JSON、汇总和逐题诊断。说明历史基线是否真可比、实际使用的地域/端点/模型是否按量、最终拟冻结配置及其 dev 选择依据。不要改旧仓或冻结 benchmark 文件。

review 重点：**答卷只由已校验且明确接纳的可报告候选形成，并与实际展开分离；路径图到平面格式的排序与汇合无歧义；20 个路线作业真实同时运行且各自隔离；DashScope 按量调用与额度可审计；20 条路线完整计分；gold 不进入预测；判分确实调用冻结评测器；恢复无重复；所有比较标明同口径与数据限制。** 本轮通过后，再单独写冻结配置与独立验收任务书；那时才讨论 eval/run-once 的实际执行。

## 7. 外部接口依据（实施前复核当日版本）

- [阿里云百炼地域与 OpenAI 兼容 base URL](https://help.aliyun.com/zh/model-studio/regions/)：地域、Key 和模型需匹配。
- [阿里云百炼 Base URL 总览](https://help.aliyun.com/en/model-studio/base-url)：同一地域的 Anthropic `/apps/anthropic` 与 OpenAI `/compatible-mode/v1` 是不同协议入口。
- [阿里云百炼限流](https://help.aliyun.com/zh/model-studio/rate-limit)：RPM/TPM 按主账号与模型计，超限 429；按量充值不提高限流。
- [阿里云百炼 OpenAI 兼容 Chat API](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)：请求参数与返回 usage 口径。
- [ZHIPU/GLM-5.3-Flash 官方模型页](https://help.aliyun.com/zh/model-studio/glm-5-3-flash-by-zhipu)与[智谱直供接入说明](https://help.aliyun.com/zh/model-studio/glm-zhipu)：精确模型 ID、北京地域、思考模式、价格和限流；正式发车前复核当日控制台值。
