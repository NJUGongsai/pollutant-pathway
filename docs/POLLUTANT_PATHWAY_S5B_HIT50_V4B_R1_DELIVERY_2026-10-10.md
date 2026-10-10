# PPV1 S5b v4b-R1 交付书 —— S5B-V4B-01 消解许可收口
# （Codex v4b 复审 §4 唯一 P1 + mimo r33 S1/S2 采纳条件；2026-10-10）

状态：`implementation_ready_for_review`（交回主会话复审；不自行点火
298、不发 chain12）。任务依据：Codex v4b 复审 §4/§8 有限回修提示词
（权威）+ mimo r33 回应（S1-a/b/c、S2-a/b/c、S3-a/b/c、S6 采纳条件）
+ 本轮任务书。红线继承：AGENTS.md + v4b 交付链。

- 开工基线：HEAD = `9a0a60ea`（v4b 收口提交；开工时实际 HEAD 与
  基线一致，工作树跟踪文件干净）；
- 本轮改动 = 3 个源文件（其中 2 个纯注释/docstring 级）+ 2 个测试
  文件（1 改测试字节含 8 个新测试 + 1 版本字面量）+ 本交付书；
- 实施期**零真实模型调用、零花费、零网络、不 push**；金标/题面/
  封存逐题 run 零读取（证据探针只用规则级合成反例与授权语料资产，
  只读；探针全部在 fresh `/tmp`/`/var/folders` tmp 执行，不动永久
  证据目录）；
- **不碰红线逐条兑现**：三冻结 SHA 逐项核对一致（criteria-v1
  `7fd35aab…`、FREEZE_RECORD `6e046e29…`、path_context `971ad00f…`，
  与 Codex 复审 §9 封包值相同）；scorer/evaluation/chemstate/AtomTool
  **字节零改动**（`git diff 9a0a60ea` 仅 5 个披露文件）；共底物许可/
  金额守卫/提交序/v1–v3 供给/推断枚举已验收面（V4B-C02）零重开；
  不重开旧同标签 SN2 残留（§十.3 登记维持）。

## 一、修法一句话 + 理由

**组合修法（mimo r33 S2-b ②+①）**：谓词新增条件 0 **元素域守卫
（限 C）**拦入口——非碳四面体中心（P/S/Si 等）的"标签消失"直接落
`stereo_changed` ⇒ `stereo_edit_unsupported`；执行后同源复核扩展为
**双轴**（已指派四面体标签轴 + 潜在立体中心清单轴：该原子不得出现
在执行产物 RDKit `FindPotentialStereo` 清单，含未指派、仅原子轴类型）
作纵深防御。

理由：② 是唯一能在**入口**挡住 Codex 反例族（2P+1S 真实公共链
反例：执行产物 P 仍为潜在四面体中心、S 为潜在三角双锥）的窄化，
且碳型是唯一有正控证据的放行面（合成二级醇→酮、bt0002#r0032、
价态墙 5 例全部为碳）——复审 §4.3 明示"可保守只支持已有证据的
碳型"；① 把 r28 E2 原文口径（"执行+sanitize 后该原子**非立体
中心**"）在复核层兑现，"无已指派标签 ≠ 非立体中心"的空窗闭合，
对碳面预期零行为变化（sp2 碳不在潜在清单，实测）而成为执行器/
序列化行为漂移的防御轴。只做①不做②会让 P/S 反例在真实公共链上
依赖 RDKit `FindPotentialStereo` 的每一步行为（含性能与版本漂移）；
只做②不①则复核仍停留在标签轴、r33 S2-a 指出的"验证强度高于实际"
印象不闭合。**N 不入域**：无正控证据且其四面体形态的解析/价态
行为需独立证据，放开属扩大放行面，留待有证据另轮预注册。

## 二、入口矩阵（共用入口；同根反例覆盖所有适用入口）

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `s5b_compiler.extract_mapped_transform` | 模板双侧 map 联结变换表 | 谓词条件 0（元素域 C）：非碳消解候选落 `stereo_changed_maps` ⇒ `stereo_edit_unsupported`；`stereo_dissolved_maps` 仅碳 |
| `s5b_compiler._is_stereo_dissolution` | 消解谓词 | + 条件 0（`_DISSOLUTION_ELEMENTS = ("C",)`）；条件 1–4 原文不动 |
| `s5b_compiler._executed_stereo_state` / `_stereo_dissolution_mismatch` | 执行后同源复核 | 双轴：标签轴（原 `_executed_chiral_tag` 语义原样）+ 潜在立体中心轴（`FindPotentialStereo`，**仅原子轴类型**——键轴 E/Z 条目 centeredOn 是键索引，与原子索引数值可碰撞，合成探针实测后过滤）；fail-closed 语义维持（映射缺失/不可解析/轴检查异常均失配） |
| `s5b_compiler._compile_donor_template_impl` | 编译主入口（对齐/编辑/执行/复核/spec） | 复核调用点不变（helper 扩双轴）；spec 语义串更新（S2-c 元素域/双轴限定）；版本 `s5b-compiler-3` |
| `recorded_source.compile_recorded_reaction` → `compile_donor_template` | 推断映射编译（EAWAG/corpus/analog 共用） | 同一编译器，自动继承；本模块**零判据改动**（仅 docstring 版本引用更新） |
| `recorded_source._changed_maps` → `extract_mapped_transform` | 推断中心 map | 只消费 `bond_changes`/`removed_maps`/`lhs.maps`，不消费 stereo 字段——谓词分类变化对其零影响（消费面核对） |
| `s5b_builder.default_pool_provider` → `compile_donor_template` | 池供给 | 同一编译器，自动继承；池成员零变化（§五）⇒ `s5b-pool-policy-4` 维持 |
| `real_model.execution_graph_payload` | 模型侧执行图 capability | **纯 docstring/注释级** S6 scope 注记（模型侧 novel 编辑协议面 vs 编译侧消解披露两属）；payload 字节零变化 |
| worker/runflow 事件链 | plan.pools specs | 零改动（spec 新语义串仍是 compile 诊断字段，prepare_hypothesis 忽略未知字段） |

## 三、r28 E2 / r33 采纳条件逐条落地

| 条款 | 落地 |
|---|---|
| r28 E2"执行+sanitize 后该原子非立体中心"（复审 P1 缺口） | 双兑现：入口（条件 0 元素域）+ 复核（潜在立体中心轴，含未指派、任何原子轴类型——S 案 Atom_TrigonalBipyramidal 同拒） |
| r33 S1-a 反例族限定"标签变化形态" | 模块 docstring 落字：标签变化形态反例族全拒（stereo_created/标签变化∧断成键/非四面体标签/纯翻转/非碳中心）；同标签（及模板无声明-底物有声明）断/成键落底物手性中心为**已登记残留**，守门扩展列下轮 |
| r33 S1-b E/Z 无声明对无声明 | 模块 docstring 落字："参考亦无 E/Z 声明时 strict 相等成立，该相等是无声明对无声明，非 E/Z 已核一致" |
| r33 S1-c 测试归因改正 + 条件 2/3 隔离负控 | SN2/非四面体夹具 docstring 归因更正（实为条件 1 拒）；新增条件 3 隔离负控（rhs 无声明 ∧ 断/成键落该原子：Cl 离去 + Br 到达不翻转书写）；条件 2 隔离负控用亚砜（真四面体 S 标签 + S=O 双键；**碳的该形态进不了判定环——RDKit 解析即清 sp2 碳标签，该事实实测后写入测试**）；碳条件 2 不可构造性如实登记 |
| r33 S2-a 复核轴落字 | 模块 docstring + helper docstring：复核 = 两轴合取，"已指派标签轴 ≠ 潜在立体中心感知"；非碳残差披露改写为**已消除**（条件 0 拒 + 双轴兜底；"残留改写"而非"原样保留"） |
| r33 S2-b 二选一/组合 | 组合（§一）；①的范围只限该原子、仅原子轴类型，碳面实测零行为变化（CC(=O)Cl / CC(=O)c1ccccc1 均不在清单） |
| r33 S2-c 诊断字符串限定 | `stereo_dissolution_semantics` 追加：`element domain: C only (non-carbon tetrahedral centers such as P/S/Si are NOT dissolvable…)` + 双轴描述 + `FindPotentialStereo`；旧前缀 `chiral_sp3_center_dissolved_by_bond_order_change_sp3_to_sp2` 保留（既有断言兼容，语义仍真） |
| r33 S3-a/b 分解口径（EAWAG 口径 + analog/corpus 行 + 5 vs 6 统一） | 本交付 §五按统一口径落字：EAWAG 通道 38 例 = 1 编译（cn 层）+ **5 显式氢价态墙**（strict 层；谓词通过 = 6 = 1+5）+ 24 stereo_created + 8 翻转/保留；analog 另有 1 编译 + 9 价态墙（跨通道价态墙 5+9=14 例事件）；corpus 18 全非消解型 0 恢复；全部为检索/编译面聚合计数，非命中数 |
| r33 S3-c 价态墙类归类 | §十.1 登记维持并升为下轮优先项（执行器记账假阴性，非化学不可修面；修复条件：只动 numExplicitHs 记账、负控含真实超价仍拒 + novel 通道全量重跑、规则文字补"键级升高伴随显式氢消耗 = 脱氢记账语义"） |
| r33 S6 capability scope 注记 | `real_model.execution_graph_payload` docstring + capability 处内联注释（§二；payload 字节零变化） |

## 四、正负控结果（修后；前后对照）

**负控（Codex 反例族，修后全拒；证据
`/tmp/s5b_v4b_r1_impl/public_probe_{before,after}.json`，fresh tmp
真实公共链 compile→production→runflow→store）**：

| 案 | 修前（父 9a0a60ea worktree 同探针） | 修后 |
|---|---|---|
| phosphorus_three（P3） | compiled、dissolution=[1]、**真实提交事件 1** | unsupported / `stereo_edit_unsupported` / stereo_changed_maps=[1] / 零事件 |
| phosphorus_four（P4） | compiled、dissolution=[1]、真实事件 1 | 同上全拒 |
| sulfur_four（S4） | compiled、dissolution=[1]、真实事件 1 | 同上全拒 |
| carbon_control（碳正控） | compiled、dissolution=[2]、事件 1（matched） | **逐项不变**（compiled、dissolution=[2]、production center/strict match True、事件 1、反应物={CC(O)Cl} 产物={CC(=O)Cl}） |
| bt0002#r0032（授权语料实盘） | compiled、target=苯乙酮、dissolution=[2] | **逐项不变** |

防御纵深（不依赖元素守卫的①轴证明）：对 P3/S4 的**真实执行产物**
直接跑复核 helper——P 案 `potential:Atom_Tetrahedral`、S 案
`potential:Atom_TrigonalBipyramidal` 均失配（即使模拟谓词放行，①轴
也能拒；父上该轴不存在 ⇒ 红）。键轴碰撞防御：产物含未指派 E/Z
双键（Bond_Double 键轴条目）而该原子无原子轴条目 ⇒ 不误失配。

测试面（`tests/test_ppv1_s5b_hit50_v4b.py`，8 个新测试）：三反例
parametrized 拒、条件 2/3 隔离负控、复核双轴负控（monkeypatch 无
标签但潜在四面体中心产物 ⇒ `stereo_derived_mismatch` + 
`potential:Atom_Tetrahedral` 机读）、helper 双轴直测 + 碰撞防御 +
fail-closed 维持。既有 14 测试全部保持（含归因改正后行为断言零
变化）；既有 SN2/纯翻转/stereo_created/价态墙/recorded 通道负控
族逐项绿。

## 五、两通道 298 面影响（诚实计量；不重跑漏斗/池深，按复审裁定）

- **本修只收窄放行面**。修前 71→72 的 +1 题（bt0002#r0032 碳消解）
  不在收缩面（碳域保留，实盘正控证据 §四）；非碳消解候选在 298
  两通道语料为 **0**（v4b 漏斗 38 例 stereo 面全部为碳化学：1 编译
  + 5 价态墙 + 24 stereo_created + 8 翻转，Codex 复审 §6 独立采信；
  corpus 18 全非消解型；analog 1+9 全碳）——**P/S 收紧影响面 =
  反例案零**（复审 §4.2 三案均为规则级合成，非 298 题面）。
- **池成员零变化 ⇒ `s5b-pool-policy-4` 维持**（唯一 298 消解槽
  bt0002#r0032 保留）；`s5b-recorded-source-2` / 
  `s5b-corpus-retrieval-2` 维持（recorded 侧零判据改动、检索语义
  零改动）。编译判据链行为变化由 **`s5b-compiler-3`** 承载
  （`S5B_COMPILER_VERSION` 升版；spec.compile.compiler_version 随
  新批落账，code_identity 文件哈希机制自动入新身份）。
- 口径统一（r33 S3-a/b）：**EAWAG 通道** 38 = 1 编译（cn 层）+
  5 显式氢价态墙（strict 层；"谓词通过" = 6 = 1+5，旧交付正文
  "价态墙（6"字面摇摆以 6=谓词通过总数、墙=5 统一）+ 24
  stereo_created + 8 翻转/保留；**analog 另有 1 编译（同净反应
  合槽）+ 9 价态墙，corpus 18 全非消解型**；跨通道价态墙 = 
  5+9=14 例事件（执行器记账假阴性，非化学边界，§十.1 下轮优先）。
  全部数字为 v4b 轮检索/编译面聚合自报（本轮零重跑、零独立复算），
  不冒充命中数；298 题域不外推 dev。

## 六、四组回归（全绿）

| 组 | 命令/口径 | 结果 |
|---|---|---|
| 定向 s5b 家族（14 文件：w1/w23456/v3_wv1-wv3/wv6/v4_wv41/v4b/runtime/pairing/rework_l01/v3r1 scope+cost/v3r2/v3r3 cost） | `pytest -q`（未筛 slow） | **250 passed / 0 failed** |
| 定向邻接族（8 文件：atom_tool/donor_applicability/analog×3/edit_protocol/conservation_filter/s3b_production） | 同上 | **149 passed / 0 failed** |
| 全量 | `pytest tests/ -q -m "not slow"`（`-B`、no cacheprovider） | **2000 passed / 0 failed / 16 deselected**（基线 1992 + 本轮 8 新测试，308s） |
| G01 隔离（329 输入谱系，沿 v4b 血统 +1 轮：路径 allowlist、fresh SHA、改动集 vs v4b G01 输入集脚本强制双向核对、`python -B`、`-p no:cacheprovider`） | `/private/tmp/safe_g01_s5b_hit50_v4b_r1.py` | **exit 0；1989 passed / 10 skipped / 17 deselected**（= v4b 1981 + 8 新测试；输入 SHA 复验零失配；改动集强制核对通过：5 换字节 + 0 新增 + 0 缺失；实际 HEAD + dirty 状态如实记录） |

父基线红绿（新/改测试字节覆盖到父 `9a0a60ea` 隔离 worktree
`/tmp/s5b_v4b_r1_parent_wt`，`git worktree add` + 测试文件字节
覆盖，import 前显式 sys.path 指向 worktree src）：

- **9 红 / 14 绿**。红 = 6 行为/轴（三反例 P/S 拒 ×3 param 实例、
  潜在中心复核轴（monkeypatch 形态父上编译放行）、防御轴直测
  （父上 helper 无潜在轴 → 空窗）、helper 双轴直测（父上
  `potential:Atom_Tetrahedral` 断言不存在））+ 2 版本字面量
  （v4b/w1 `s5b-compiler-2` ≠ 3）+ 1 语义串字面（碳正控测试新增
  S2-c 断言 `element domain: C only` 父上不存在；行为断言部分
  父上同绿）。
- 绿 = 全部既有负控/正控不变量（纯翻转/stereo_created/SN2/价态
  墙/recorded 通道/P2 预算族/e2e 链）+ 新增条件 2/3 隔离负控
  （父上同拒——不变量，非翻转）。

## 七、金标边界自查

- 预测侧零金标：本轮零漏斗/池深重跑（任务书口径），证据探针只
  用规则级合成 P/S 反例（与真实 298 金标零重叠）+ 授权语料资产
  （bt0002#r0032，仓内 sha 锚定回读，只读）；金标/products/旧答卷/
  封存逐题 run 零读取；判分零 LLM；
- 冻结判据/scorer/评测尺子/AtomTool/金额链/共底物许可零触碰（§开
  头逐项核对）；`real_model.py` 改动为纯 docstring/注释（payload
  产出字节零变化）；
- 合成反例不外推科学性能（不称 298 已发生同错，也不称本轮修复
  提升 298 命中）；对外数字带题域标签（298 检索/编译/池面聚合，
  不外推 dev）。

## 八、待复审残留（不预支批准）

1. **AtomTool 显式氢价态墙**（v4b §十.1 登记，r33 S3-c 升为下轮
   优先项）：修复条件与影响面登记照旧，本轮不实施（红线）；
2. **同标签断/成键落底物手性中心**（r28 E1-2 残留，S1-a 落字）：
   守门 = 执行后同源复核扩展到全部手性保留原子，属判据扩展，列
   下轮选项；
3. **E/Z 检测面**维持既有披露（原子四面体标签检测面；r33 S1-b
   落字已加"无声明对无声明"限定）；完整键轴立体支持另轮；
4. **N（及其他元素）消解域扩展**：须规则级设计 + 该元素真实执行
   后中心非立体的证据 + 化学评审，不凭标签空预支（§一）；
5. mimo r33 不确定清单中"待执行验证"项本轮已执行验证的：RDKit
   sp2 碳标签解析即清除（条件 2 碳形态不可构造，写入测试）、
   `FindPotentialStereo` 对酮产物零条目（碳面零行为变化）、键轴
   条目索引与原子索引碰撞（实测后过滤+测试）；未执行验证维持：
   漏斗/池深/G01 之外的 298 逐题形态（金标纪律零访问）。
6. 发车前置（chain12）：正链复审放行 + r33 采信互证 + 新登记
   冻结（compiler-3 随 code_identity 落账）+ 冒烟前缀；本轮不
   自行点火。

## 九、本轮改动清单（提交内容）

- 源码（3）：`pollutant/s5b_compiler.py`（谓词条件 0 + 复核双轴 +
  语义串 + docstring r33 落字 + `s5b-compiler-3`）、
  `pollutant/recorded_source.py`（**纯 docstring** 版本引用）、
  `pollutant/real_model.py`（**纯 docstring/注释** S6 scope 注记）；
- 测试（2）：`tests/test_ppv1_s5b_hit50_v4b.py`（8 新测试 + 归因
  改正 + 版本字面量 + 语义串断言）、`tests/test_ppv1_s5b_hit50_w1.py`
  （版本字面量）；
- 本交付书；
- 证据（未跟踪，易失 /tmp）：`/tmp/s5b_v4b_r1_impl/`（公开链前后
  对照探针脚本与 JSON：修前三反例各 1 真实事件 → 修后零；碳正控
  逐项不变）、G01 输出目录 `/private/tmp/g01_s5b_hit50_v4b_r1/`、
  父红绿 worktree `/tmp/s5b_v4b_r1_parent_wt/`。

## 十、成本

本轮实施期真实模型费用：**0 CNY / 0 次调用**（全轮零网络、零判分
LLM；探针/回归/G01/父红绿全部离线）。
