# pollutant_pathway_v1 S5b 启动批有限回修交付书（POLLUTANT_PATHWAY_S5B_REWORK_DELIVERY_2026-10-09）

日期：2026-10-09。实施代理：S5b 回修批唯一实施会话。仓库
`/Volumes/CC/Enzyme_Agent/dependingv43`，分支 v4.3，直接父/基线
`a399d6e`（S5b 启动批，已复审）。任务来源：复审
`docs/POLLUTANT_PATHWAY_S5B_CODEX_REVIEW_2026-10-09.md` §8 回修
提示词；**只修 S5B-L01/S5B-L02**，S5a-01~05/S4/S3/ISO-01 及 legacy
保持关闭。

**本批不做**（硬边界，均遵守）：不启动正式 S5b、不冒烟、不调用
任何模型（零网络零费用）；不代定 width/请求上限/并发/费用时长；
不新增强制 cap3 门；不改统计聚类策略（S1/S2/Wilson 保留）；不
实现真实图转换/provider/hit@K 判分（属后续批）；不碰题面/金标/
封存 run/dependingv4/原 v3 评价资产（`exam_v2.py` 只读源码）；冻结
判据正文/FREEZE_RECORD/path_context 逐字节不改（SHA 复核在案，
证据 `frozen_integrity.json`）；不 push；不覆盖评审报告与旧永久
证据；不提交任何评审侧未跟踪材料。

## 0. 并行会话事件披露（先读）

实施中（12:24–12:25 CST）检测到**另一会话**对仓工作树的非本批
改动：`src/pathway_v43/pollutant/runflow.py`（provider 接线内容）与
未跟踪 `src/pathway_v43/pollutant/real_model.py`。按
`PPV1_REVIEW_PROTOCOL` §2（并行改动结果不冠以本批身份、不回退
他方改动）处置：**全部验证改用 detached 稀疏 worktree 快照**
（`/private/tmp/ppv1_s5b_rework_snap.122808` = a399d6e 检出 + 仅
本回修 10 文件叠加，`input_snapshot.json` 前后 SHA 核对全同）；
他方文件不读正文、不入任何验证树、不提交。仓内真实树曾跑一轮
PPV1 全量 1140 绿（12:23），因并行改动归属不净**不采信**为交付
数字（下文数字均为快照树数字）。事件完整登记：证据
`parallel_session_event.json`。

## 1. L01：real 首消费禁双无 qid / root_identity_fallback

### 1.1 入口矩阵（入口 → 行为 → 正负控 → 证据）

| 入口 | 修后行为 | 正控/负控 | 证据 |
|---|---|---|---|
| `evaluate_scientific`（public 主入口，`evaluation.py`）：`data_scope=real` 且配对档 `root_identity_fallback`（评测输入 `reference_graph_manifest` 条目与 `native_path_exports` 条目两侧全部未声明 qid） | 配对计算后、**样本评分/聚合/结果写入前**抛 `EvaluationContractError`，`kind=real_data_root_identity_fallback_forbidden`；机读 detail 携带 `data_scope`/`pairing_basis`/`graphs_without_declared_qid`/`export_entries_without_declared_qid`（缺 qid 范围）+ note（发车核对指引） | 负控=复审公开反例（real 标签 + fake approved 形状 + 双无 qid）：修前 codex-a scored 进 8 项聚合、codex-b not_evaluated → 修后整评结构化拒，**零样本评分/零聚合/零结果写入** | `counterexample/`（prefault/guarded 两轮 + 正控 3×2）；`tests/test_ppv1_s5b_rework_l01.py::test_real_label_noqid_structured_reject_before_scoring` |
| 门次序：real + 双无 qid + 预注册未批准 | 既有 `real_data_requires_approved_preregistration` 先拒（授权前置不取消） | 正控保持（两树同绿） | `test_real_noqid_prereg_gate_precedes_pairing_guard` |
| 门次序：real 标签下既有输入守卫（qid 不在 source_refs 等） | 输入校验先于配对守卫（四原守卫不动） | 正控保持 | `test_real_noqid_input_guard_precedes_pairing_guard`；启动批 4 守卫测试全绿 |
| `synthetic_rule_level` 双无 qid（合成夹具） | 回退根身份配对照常 + `pairing_basis` 机读披露（合成正控保持） | 正控保持（两树同绿） | `test_fallback_root_identity_pairing_disclosed`；`test_synthetic_noqid_fallback_positive_control_kept` |
| real + 双侧 qid 声明（严格档） | qid_strict 正常评分（不全面拒绝合法 real 档） | 正控保持 | `test_real_label_strict_qid_positive_control_kept` |
| qid 声明缺配导出 | `not_evaluated` + `sample_qid_unpaired`（fail-closed 留分母不张冠李戴） | 正控保持 | `test_qid_unpaired_not_mispaired_by_root`；`test_real_qid_unpaired_not_evaluated_kept` |
| 契约登记 | `ppv1-evaluation-4 → -5`、`ppv1-profile-24 → -25`（real 档配对守卫语义升版，不偷换已登记契约）；reference-graph-1/split-manifest-1/preregistration-template-3 不变；qid 不进化学结构判据（守卫在消费侧，匹配/条件/指标判定零触碰） | 版本字面量同步 7 存量测试文件 + 契约登记测试 | `test_l01_contract_version_registration` + 6 文件字面量；`profile.py` -25/-5 注释块 |
| 预注册发车核对（L01 的文档侧） | 预注册 §9 新增第 ④ 项：判分聚合前核对 `coverage_report.pairing.bases_by_graph` 全 `qid_strict`，任一 fallback ⇒ 阻断不出分；§2 配对段落同步代码守卫语义 | 与代码守卫双保险 | `POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §2/§9-④/状态行 |

### 1.2 代码改动（src 2 文件）

- `src/pathway_v43/pollutant/evaluation.py`：模块头 evaluation-5
  说明段；`evaluate_scientific` 配对消费处新增 real 档守卫（约
  2193–2224 行区域，结构化拒 + 机读 detail）；
  `PAIRING_BASIS_NOTE`/`consumed_field_policy`/`_pair_exports_
  to_samples` docstring 同步守卫语义（守卫在消费侧，配对函数
  本身不接收 data_scope）。
- `src/pathway_v43/pollutant/profile.py`：`PPV1_PROFILE_SCHEMA_
  VERSION` → `ppv1-profile-25`、`PPV1_EVALUATION_VERSION` →
  `ppv1-evaluation-5`，各带注释块登记（仅此一处语义变更；
  criteria-v1 冻结正文/FREEZE_RECORD/path_context 不动）。

### 1.3 新增回归（7 条，`tests/test_ppv1_s5b_rework_l01.py`）

反例翻转 1（real+双无 qid+fake approved ⇒ 结构化拒 + detail 断言）
+ 门次序 2（prereg 门先/输入守卫先）+ 正控 3（synthetic 回退/real
严格 qid/缺配 not_evaluated）+ 契约登记 1。夹具纪律沿启动批：公共
`start_run` 真实生成、合成 qid 与真实 RXNG_* 零重叠；
`data_scope='real'`/`approval_status='approved'` 均为合成接口形状
标签（复审反例同款），不代表真实数据/用户或 teacher 审批。

## 2. L02：预注册/交付/mimo 请求口径逐条订正（27 条对照）

修订对象：`docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`
（确认读前合法修订窗口）、`docs/POLLUTANT_PATHWAY_S5B_LAUNCH_
DELIVERY_2026-10-09.md`（顶部回修注记 + 错处订正）、`docs/mimo_
ppv1_chem_review_request_r26.md`（顶部订正注记，已送正文不改写）。
下表每条注复审出处 → 订正落点 → 合成/码级互证锚（锚=复审 caliber
专项 27 案编号或源码事实；**该 27 案为纯函数/最小原生形态匹配
输入，不冒称经公共 audit/submit 链**）：

| # | 订正条目 | 落点 | 互证锚 |
|---|---|---|---|
| 1 | 老侧判定单元按**展平分串/点串融合**分形；表第 4 行"整串≠金标"错格订正（分串下额外串不破 any-one 命中、融合下才不中） | 预注册 §5.1 判定单元 + 差异表第 4 行；交付书 §2 发现 2/处置；r26 注记① | 案 1/2（分串多报 rank1/rank2）、案 3（融合 miss）、案 4（融合组分敏感性中）、案 5 |
| 2 | superset 与老官方口径关系**按包装分形**（分串下新更严、融合下同向）；"新对多报降档是新增更严约束，不是旧官方也惩罚多报" | 预注册 §5.1 结论 3；交付书处置段 | 案 13（HIT60 caliber v3 是另一口径）、15/16（新侧 superset ⇒ partial） |
| 3 | 补 **K 单位轴**（rank 槽=事件 vs 字符串；敏感性表展平后同单位是锚对齐前提；主口径 hit@K 与老不可逐档对读） | 预注册 §5.1 表新行 + §5.2 rank 注 | 案 11（展平非全局去重）、14–18（事件判分单元）；单位差为定义级 |
| 4 | 补**报告可见性/宽度轴**（主口径=全部已提交事件无过滤；老=答卷 ≤5/步；敏感性表=投影可报告，cap=`max(1,min(width,4))`） | 预注册 §5.1 表新行 + §5.4 宽度披露 | 案 21/22/23（cap 投影 rank）、26 |
| 5 | 反应物侧细化：**两侧集合相等**（非仅"含根"；reactant 超集 ⇒ partial 不中） | 预注册 §5.1 表行；交付书发现 3 | `evaluation.py` 集合相等判分（复审 2.1 码级） |
| 6 | 多产物金标行补**跨事件分散**细化（分散不能拼成一条严格边） | 预注册 §5.1 表行 | 案 17（同事件 exact）/18（分散 partial） |
| 7 | "更严/宽向不存在"限定**命中存在性与指定报告映射**；逐档数字可双向移动，**无逐 K 单调声明** | 预注册 §5.1 结论 + §5.3 语义限定；交付书发现 3 | K 单位/排序源/输入宇宙（定义级） |
| 8 | §5.3 表口径列改**历史参照锚**；"达到老系统首轮水平"只与敏感性表数字绑定 | 预注册 §5.3 | 历史数字来源（用户/文档 provenance，未独立重算——如实） |
| 9 | **四象限报告规则**（主口径过/不过 × 敏感性表达锚/未达锚，如实报告不单边取用；两类差不混解释） | 预注册 §5.3 | 定义级（复审 §4.2-4） |
| 10 | 两锚（首轮/复测）**互相不可比**、各自只与同口径敏感性表比 | 预注册 §5.3 来源 bullet | Phase D §10 自述（复审转引） |
| 11 | `report_rank=None` 消费规则**写死**：只纳非 None 位次 + 宽度外产物计数级披露（不尾随、不留给得分后临选） | 预注册 §5.4 | 案 26/27（cap1 `[extra,target]`：排除 None ⇒ miss、尾随 ⇒ rank2——两选一冻结取**排除**） |
| 12 | **mimo 纠错一**：投影 helper 不自动去重；不采纳"先去重再排名 ⇒ 固定乐观偏差"断言；去重只在判分处沿老 `seen` 规则 | 预注册 §5.4 判据 bullet + §5.1 排序 bullet | 案 24（`['a','a','b']`→1/2/3）、25（prepare 保留重复 refs） |
| 13 | **mimo 纠错二**：**cap≥3 不是本审强制门**（不新增强制 cap3 科学门）；cap<3 时作可报告性角落披露 + 用户可选披露项 | 预注册 §5.4 宽度/cap 披露 | 案 26（exact 三产品+cap1：新侧 matched_strict、可报告金标产物给老 any-one rank1） |
| 14 | "重复身份跳过"明示为**判分处规则**（复刻表沿老 scorer 语义执行，非投影层行为） | 预注册 §5.1/§5.4 | 案 7（重复非命中身份占名次） |
| 15 | 不可解析候选机制注（老=占名次不中；新=参考侧 `invalid_input`、候选侧经状态契约不存在，复刻表内不触发） | 预注册 §5.1 表行 | 案 6 |
| 16 | CN 旁证防护句（敏感性表 cn 数字=历史锚对齐独立指标，不进身份判定、不与 strict 合并、不得读成"CN 命中即化学正确"） | 预注册 §5.4 | mimo r26 §0 建议 + 冻结判据五精神 |
| 17 | 份数轴=**共享盲区**披露（两口径同向不看份数），不进差异表 | 预注册 §5.1 表注 | 案 12（gold 集合坍缩）/19（一份 state 严中两 occurrence） |
| 18 | **S1 单题簇统计事实**：`source_group_id=qid` 每簇一题、related 不归并跨 qid ⇒ 主 bootstrap 不因此消除跨题相关；S1/S2/Wilson 保留；改主聚类键只列**用户/teacher 决策项**（不代选） | 预注册 §7 | S1 定义级 + 复审 caliber 专项第 8 条 |
| 19 | r26 定位订正：**发车前规则/配对口径复核**（已送已回，采信到互证为止），不是 AGENTS 三触发点之 3 的履行；真实评测后仍须另执行；r27 排程 | 预注册 §6 表 #19 | 复审 §5 第 19 项 |
| 20 | Chenyu **已恢复**同步（用户 2026-10-09 最新来源；"已恢复"与发车当日实核分开） | 预注册 §9-②；交付书 §7 | 复审 §1（最新用户来源） |
| 21 | r26 **已送已回**同步 + 两项 mimo 事实纠错的处置登记（回退档硬门已按 L01 落码、老侧错格已按 L02 订正） | 交付书 §4/§7；r26 顶部注记 | 复审 §6 裁定表 |
| 22 | `unmatched_exports` = **完全无人认领**的导出（非全部未消费）；同 qid 被配对但未消费的其他导出单独披露 | 预注册 §2 构建器义务段 | 复审 §5 + 启动批正向测试（零 unmatched 而两导出同 qid） |
| 23 | 未来真实构建器**交接义务**：run 注册表→qid 单一来源、按冻结注册序确定性生成清单、禁目录遍历偶然序/内容择优/按结果择优；消费者确定性≠构建器确定性 | 预注册 §2 构建器义务段 | 复审 §5 + r26 1.2-3（构建器侧验收属后续批） |
| 24 | hit@K/敏感性表**尚无实现**如实披露（预注册为规则文本，实现属 S5b 判分实施批） | 预注册 §5.2 末 bullet | 复审 §5 + r26 判断面（仓内无消费码） |
| 25 | 报告序披露"**非模型自报置信排序**"（提交序=系统展开/调度序；hit@1 语义限定）+ resume `created_at` 保持为实现验收项 | 预注册 §5.2 报告序 bullet | 复审 pairing 专项（两公共 run DB/新导出 `(created_at,event_id)` 序保持，合成级） |
| 26 | 启动批交付书**父红分类订正**（按首个实际失败：4 行为+4 守卫+5 缺字段+6 版本，原"6+3+4+1+5"细分不准确；后段未执行不冒称翻转） | 交付书 §1.6 + 顶部注记② | 复审 §2 baseline_classification |
| 27 | 预注册汇编依据/§6 表 #8 契约版本同步 evaluation-5/profile-25（配对段写明守卫语义与"14+7 条回归在案"） | 预注册 依据 5/§2/§6 表 | 本批 L01（契约登记测试） |

订正纪律：全部为**确认读前合法修订窗口**（状态保持
`preregistration_pending_final_confirmation`）内的口径订正；**不改
变任何已圈定冻结值**——题源 298、费用不限、20+2、116/128/130
历史锚、固定 298 分母、strict-only 主口径、40 在途、K 档位、
S1/S2/Wilson 安排全部原值保留。

## 3. 验证数字（全部快照树 = a399d6e + 仅本回修 10 文件）

| 项 | 数字 | 备注 |
|---|---|---|
| PPV1 全量（45 文件） | **1140 passed / 0 skipped / 0 failed，exit 0** | 1133 存量 + 7 新；两份冻结正文准入使 r2/r3 守卫实际执行 |
| 直接父基线同字节红绿（8 测试文件：7 改 + 1 新） | **8 failed / 148 passed / 0 collection / 0 skipped，exit 1**（156 nodeid） | 首失败分类：**1 未发生指定守卫红**（反例翻转：父上 `DID NOT RAISE EvaluationContractError`，evaluate 返回错误评分输出）+ **7 版本字面量红**（profile/s4b/r1/r2/r3/pairing/rework_l01 契约登记）；0 行为值红、0 缺字段红；r2/r3 版本红后段冻结 SHA 断言未执行，不冒称冻结完整性翻转；`test_ppv1_s5a_schema.py` 当前字节父上绿（仅夹具字面量） |
| G01 安全隔离 | **1740 passed / 10 skipped / 17 deselected，exit 0** | launch 基线 1733 + 7 新精确吻合；308 输入（307 谱系 + 1 新）复制/执行后 SHA 零不符；9 变更 + 1 新 vs launch 集脚本强制精确闭合；10 skip 逐 nodeid（真实评测 5/v4 1/phase_d 2/冻结 docs 2）+ 17 deselect（16 slow + 1 显式）全披露；7 个隔离子进程 pyc 如实登记；attempt1 一次准备失败（稀疏快照缺 5 个 R7 白名单 `.DS_Store` 未跟踪杂项）原日志保留不删，attempt2 首跑即成 |
| 公开反例复现（fresh tmp） | 修前 PREFAULT_REPRODUCED → 修后 GUARDED_STRUCTURED_REJECT | 复制复审 `real_label_noqid_public` 场景重建（公共 start_run 两同根合成 run）；修前 codex-a scored + 8 聚合 + 两图 fallback；修后结构化拒 + **零样本评分/零聚合/零结果写入**；正控 3×2（synthetic 回退/real 严格 qid/real+pending prereg 拒）两侧保持 |

真实仓 `tests/` 从未全量（G01 纪律）；G01 用白名单隔离副本；
所有业务脚本在 fresh `/private/tmp` 执行，永久证据不原地执行。

## 4. 改动文件清单

- **src（2）**：`src/pathway_v43/pollutant/evaluation.py`（L01 守卫 +
  文字登记）、`src/pathway_v43/pollutant/profile.py`（evaluation-5/
  profile-25 升版）；
- **tests（8）**：`tests/test_ppv1_s5b_rework_l01.py`（**新**，7 回归）；
  字面量同步 7 文件：`test_ppv1_profile.py`、`test_ppv1_s4b_export.py`、
  `test_ppv1_s5a_rework_r1.py`/`r2`/`r3`、`test_ppv1_s5a_schema.py`
  （run_identity 夹具字面量）、`test_ppv1_s5b_pairing.py`（契约登记
  断言 + docstring）；
- **docs（5）**：预注册稿（L01+L02 订正）、启动批交付书（回修注记
  + 错处订正）、r26 请求（订正注记）、本交付书、mimo r27 请求
  `docs/mimo_ppv1_chem_review_request_r27.md`（写好未送，由用户送
  mimo）；
- **证据（1 目录）**：`docs/review_evidence/ppv1_s5b_rework_
2026-10-09/`（README/脚本/输入输出/argv/env/exit/SHA 封包，嵌套
  manifest 纳哈希只排根 controls，准备失败原日志不删）。

## 5. mimo 评审

r27 请求已写好**未送**（由用户送 mimo；判分零 LLM、不外发任何
题面/金标）：自包含规则级 + 合成例，覆盖 ①L01 守卫语义（real 档
禁回退、正控边界、门次序、与冻结判据零冲突复查）；②L02 订正后
判断面（分串/融合分形、两新轴、None 规则、cap3 非门、S1 事实、
四象限）；**显式含复审对 mimo r26 的两项事实纠错**（投影不自动
去重、cap≥3 非必要门），供 mimo 复核其 r26 结论的修订面；程序
事实全部标"待执行验证"。

## 6. 未完成项（如实）

1. 用户最终确认读未做——预注册保持
   `preregistration_pending_final_confirmation`（§9 由三项增为四项
   硬门）；
2. mimo r27 未送（请求已备）；r26 两项纠错已按复审裁定落实，mimo
   侧修订意见待 r27 回复；
3. 冒烟/正式 S5b/provider/真实转换/hit@K 判分实现均未启动（属
   S5b 实施批；本轮并行会话的 provider 接线改动**非本批交付**，
   状态登记于 §0）；
4. P1 请求计数上限数值/并发实测安全值/费用时长区间：冒烟后定型
   再冻结（不预支）；
5. Chenyu 发车当日三锚 SHA 实核：仍为发车硬门（"已恢复"≠已核）。

## 7. 提交

v4.3 本地提交（**不 push**），显式路径 git add：src 2 + tests 8 +
docs 5 + 证据目录。环境纪律：`~/miniconda3/envs/depending43/bin/
python -B`、`PYTHONDONTWRITEBYTECODE=1`、`pytest -p
no:cacheprovider`、`OMP_NUM_THREADS=1`、先 cd 仓库根。评审侧
未跟踪材料（复审报告/mimo 回应/旧证据目录/.zcodeignore 等）零
触碰零提交。
