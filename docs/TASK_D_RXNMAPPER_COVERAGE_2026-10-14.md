# TASK — D 探针：rxnmapper 扩检索对 120 H 桶的覆盖摸底（2026-10-14）

> 派单：主窗口（grill 拍板：D 线=覆盖探针先行）。执行：子代理。
> 目的：回答一个数字——**rxnmapper 扩检索模板库能覆盖 120 H 桶
> （已提交不匹配）缺口的多大比例**，决定 D 全量立项值不值。

## 一、背景与数据源（先读这两个）

| 件 | 位置 |
|---|---|
| 决策备忘（rxnmapper 可行性验证配方 + ~26k 未映射行定义） | `/Volumes/CC/Enzyme_Agent/dependingv43/docs/S5B_COMPILE_FUNNEL_DECISION_MEMO_2026-10-13.md` §一 |
| RHEA 原始库 | v43 仓 `assets/rhea.json`（未跟踪大件 ~750MB，含 atom_mapping 字段；~26k 未映射行=备忘 §一 口径） |
| 120 H 桶题集 | T7 产物（H=120 已提交不匹配 qid 清单）：chain12 批分析目录一带 `analysis/`（先 find；批根 `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/`） |

已知事实（备忘 §一）：rxnmapper 独立 venv（wheel 自带 3.1MB 模型、
**零网络推理**）；RHEA 1,000 条成功率 96.7%（失败全为超长 >512 token）；
元素守恒/重原子覆盖 100%；全库 32 分钟单进程 CPU。

## 二、要做的事（三步）

1. **重建 rxnmapper 环境**：`/tmp/rxnmapper_env` 大概率已丢（/tmp 易失），
   按备忘 §一配方重建（pip wheel 自带模型，零网络推理；装不上停手报告）。
2. **建模板库**：对 ~26k 未映射 RHEA 行跑 rxnmapper 映射 → 按既有
   池供给的模板结构生成候选模板（结构对齐 analog/recorded 通道的
   模板字段；只建库不入仓——产物落 gitignored 分析目录）。
   超长 >512 token 的行按备忘口径走兜底（跳过并计数，如实报）。
3. **覆盖测量（判分进程内）**：对 120 H 桶逐题——用该题底物在
   新模板库做检索/编译模拟，测"能否产出该题缺失反应的候选"。
   判分进程内对照参考（金标只在本地进程消费，产物零外带，
   只出聚合计数）。输出：覆盖题数/120、按"可编译命中参考"分层
   （exact strict 命中形态 vs 仅产候选未过编译）。

## 三、红线

- 零模型零网络零 LLM（rxnmapper 本地模型=零网络推理，合规）；
- 金标/题面只在本地判分进程内消费，产物零外带，分析目录 gitignored；
- 不改 src/tests/既有 docs；不 push 不提交；模板库不入仓；
- 覆盖测量是探针级（如实标注"探针≠预注册≠成绩"）。

## 四、产物与回传义务

- 产物：`reports/ppv1_s5b/d_probe_rxnmapper_2026-10-14/`（自建，
  gitignored）：`rxn_coverage.json` + `rxn_probe_report.md`。
- 回传：模板库规模（行数/映射成功率/超长兜底数）、**120 H 桶覆盖率**
  （核心数字）、分层覆盖表、对 D 线立项的 3 条建议（值不值全量、
  需要什么前置）。
- 排障：rxnmapper 装不上/H 桶清单找不到/参考对照对不上 → 停下报告。
