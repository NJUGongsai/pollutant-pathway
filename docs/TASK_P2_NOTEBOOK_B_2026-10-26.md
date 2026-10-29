# TASK_P2_NOTEBOOK_B_2026-10-26 — notebook 正式门禁跑 P2 B 臂（v2card）

> 口径：**正式批次-单臂**。A 臂（v1card）对照未跑，**不出 B−A、不写提升/有效**。
> 唯一执行者：本窗口（CC 2026-10-26 拍板）。另一个窗口只保留 P3，不得再碰 notebook 的 P2/v2card。
> 本任务书替代口头传话；执行偏离本文件必须先改本文件并留变更记录。

## 0. 拍板记录（CC 2026-10-26）

| # | 决策 | 结论 |
|---|---|---|
| 1 | 口径 | 正式 P2 批次（不是诊断口径） |
| 2 | 臂数 | 本轮只跑 B（v2card）；A（v1card）待 B 出数后自动补 |
| 3 | build | 复用 notebook 10-23 离线 build（`de19dc6e…`，298/298 与 HPC 逐字节同） |
| 4 | 执行归属 | 本窗口接管全部；另一窗口停 P2/v2card（CC 亲自通知） |
| 5 | 本地入口 | 补 notebook 本地 nohup 正式入口（无 sbatch） |
| 6 | 身份门 | 路径归一 + 披露附录，qwen3.8max 代 Codex 审后生效 |
| 7 | fatal 修复 | CC 那条线修；本窗口独立复现验收；**若触碰 `src/` 则停并补充披露，不自动发** |
| 8 | 发车时点 | 四件全绿自动发；任一门红停并报 CC |

### 0.1 执行期补充决定（2026-10-26 核代码后）

1. **batch_tag 沿用 `p2-298-20261021`**（与已签批准包一致），不重建。依据：run_id 在 build 期由 batch_tag 派生；新批根 `p2_298_20261023_*`、新 runs 根 `runs/p2_298_20261023_*`、新协调目录 `operations/p2_coordination_nb_20261023` 三者物理隔离，旧 10-21 产物零共享路径 ⇒ 换 tag 需重跑 build（约 50 分钟）并让已复审的身份归一包失效，代价大于收益。run_id 字符串与旧 P2 同形但不同根，报告披露。
   **条件失效并已改判**：fatal 修复触碰 `src/`（B 口径），`code_identity` 变化 ⇒ 原"不重建"作废。按交接书 `docs/HANDOFF_P2_FATAL_FIX_2026-10-26.md` §3.9 改用**新 batch_tag `p2-298-20261026`**：新 seed `p2_nb_seed_20261026`、新臂 `p2_298_20261026_{v1card,v2card}`、新协调目录 `p2_coordination_nb_20261026`；批准包重绑 `batch_tag`、`script_lock_sha256`、`code_identity_aggregate_sha256`、`approval_sha256`，`source_commit` 保持 `11aeeaf…`（不 commit）。
2. **A 臂不跑 full，但 barrier 要求两臂 smoke10 回执** ⇒ A 会跑 smoke2+smoke10（约 12 次真实调用），计入披露；B 跑 full 298。
3. **新入口与身份归一披露均走 qwen3.8max 代 Codex 复审**后生效。

## 1. 现状事实（2026-10-26 实测）

- notebook 实例重建过（主机名 `…-81040`），`/root/v43_migration` 数据完整（1.7G）。
- 两新臂批根 `batch/p2_298_20261023_{v1card,v2card}` 完整；**`runs/` 不存在、0 run、10-24 后零新文件、无 stop/lock**。
- build 10-23 10:37Z rc=0，`BUILD-GATE-OK n=298`，墙钟 2953s；prepare 两臂 P2-face 八项全中。
- 指纹 `de19dc6e…`（notebook）vs `76858eb4…`（HPC），仅 `assets_root`/`questions_source` 路径标签差异；298/298 run_inputs 与 reference_graphs 字节同。
- 正式 score 需 `p2_full_status.json`；当前缺，正式入口 `p2_operations.py score` 两臂 rc=1。
- notebook：Python 3.11.9，rdkit/pydantic/openai/httpx 等 10/10 import OK；`ppv1_hpc/env/llm_ds.env` 600、变量名 `V43_LLM_BASE_URL/V43_LLM_API_KEY/V43_LLM_MODEL`；无 sbatch/tmux；直连 DashScope 不通；**notebook 平台代理 `10.16.1.51:3128`（`/root/private_data/.ai_user_info/ai_proxy`，带认证）实测根路径 404、模型端点 401（通）**；HPC 自身代理 `10.15.2.115:3000` 在 notebook 不可达。
- 脚本在 notebook 的 `v43cP2/scripts/hpc/`（p2_operations.py / p2_run_wrapper.py / sbatch_p2_*.sh 全在）；`launch` 硬依赖 sbatch。
- 预注册 `docs/T_P2_PREREG_FULL_V2_2026-10-21.md` 已签（approval `ccdb9d14…`，签字文本 `86242516…`）；prompt `c24bee42…`；模型两臂同 `deepseek-v4.1-flash-1017`。
- 化学第三轮复审：`docs/T_P2_V2_CHEM_REVIEW_ROUND3_2026-10-21.md` = **PASS（限定范围内）**。

## 2. 红线

1. 金标/题面只允许在 notebook `/root/v43_migration`（700）内消费；不入仓、不外发、不打印。
2. 不修改已签预注册、批准包、判据/评分/池/排序/门阈值；新增件只能以披露附录形式登记。
3. 不触碰 10-21 旧批根与 `coordination` 旧 stop/lock；新臂新批根，不 resume 旧批。
4. 每次发车前必须确认 notebook 无并发 P2 作业；**同批根双发=事故**。
5. 模型密钥不打印、不入仓；代理串不外传。
6. fatal / pending>0 / 非模型内容失败>15 ⇒ 停批保全现场，不在无效批上判。
7. 任何 `src/` 变更必须停下报 CC，不得在未闭合代码身份上跑正式批。

## 3. 发车前四件（全绿才发）

| # | 交付件 | 验收标准 | 证据落点 |
|---|---|---|---|
| 1 | notebook 本地正式入口 | 只调用锁内 `p2_run_wrapper`，不改 `p2_operations.py`；支持 smoke2/smoke10/full、进度、`p2_full_status.json` 回执、§6.2 停点；合成小样本跑通 | `docs/review_evidence/p2_nb_entry_2026-10-26/` |
| 2 | 身份路径归一+披露 | 字段级 diff 仅路径标签；298/298 字节同；归一后指纹；预注册 §7 硬门偏离说明；qwen3.8max 代 Codex 审 | `docs/review_evidence/p2_nb_identity_2026-10-26/` |
| 3 | token 实测 | `p2_token_measure_298_arms.json`：逐题 tokens、批合计、B vs A、>13% 题集、tokenizer 文件 SHA；代理 tokenizer `87a7830d…` 并标注"代理口径" | `docs/review_evidence/p2_token_measure_2026-10-26/` |
| 4 | fatal 独立验收 | 隔离树复现 10-21 失败 case，确认 `state_fact_rederivation_mismatch` 不再触发；相关测试通过；记录 HEAD 与命令 | `docs/review_evidence/p2_fatal_reverify_2026-10-26/` |

发车序列（预注册 §6.2）：**smoke2 → smoke10 → full**。smoke 任一红停，不进 full。

**Gate 1 复审状态（2026-10-26）**：v1 = PASS_WITH_CONDITIONS（C1–C5）；**v2.1 增量复审 = PASS（工程面）**。C1–C5 + U7 + 双硬闸全部闭合：本地/notebook gate-probe 真 6/6、dryrun 20 步、plan 全绿、凭证扫描 137 文件零残留；`FULL_ARMS` 缺省/非 `v2card` 拒发（rc=9），U7 缺失/漂移/回执异常拒发（rc=10），正控放行。证据包 `docs/review_evidence/p2_nb_entry_2026-10-26-v2/`。
**发车规程（复审建议 P1/P4）**：真车**只经 `deploy_4_launch.sh start`**（`p2_nb_entry.sh start` 直启不过 U7 闸）；U7 回执必须是当次 `deploy_3` 的新鲜回执；发车带 `FULL_ARMS=v2card LAUNCH_CONFIRMED=CC-<当日> NOT_A_DRILL=yes`。
**2026-10-26 预检红灯（已修，v2.2）**：入口 v2.1 的 U7 默认配置硬编码旧 10-23、`deploy_3/4` 未转发 `P2_NB_CONFIG`、`deploy_4 start` 远端体未 export ⇒ 真发车会回落旧批根。v2.2 已修五处并复跑：U7 **默认调用 RC=0**（live=cfg=build=`c565cd56…`）、plan 六项 true/tag 26/22 步、gate-probe 6/6、dryrun 20/20、`deploy_4 check` 缺 FULL_ARMS=9 / `FULL_ARMS=v2card`=0 / 缺配置=11、远端 `P2_NB_CONFIG` 已设置且 0 处 UNSET。证据 `docs/review_evidence/p2_nb_entry_2026-10-26-v2-2/`；qwen 增量复审中。

## 4. 发车参数

- 臂：B = v2card（`candidate-evidence-3` / `descr-3`，紧凑 JSON 分隔符）。
- 题卷：298 固定；分母不剔题；`real` 数据面。
- workers 8 / max_in_flight 8；`max_real_model_requests=3`；`max_format_feedback_rounds=2`；gate 4470/RPM 200/TPM 3M；3600s；传输重试 1 次；429 有界退避。
- 温度与 max_tokens 都不发（no-cap）；金额帽无，usage 照记。
- **batch_tag 沿用 `p2-298-20261021`**（见 §0.1）；新批根/新 runs 根/新协调目录物理隔离，旧 10-21 产物零共享。
- 代理：`start`/`dryrun` 时 source notebook 平台 `/root/private_data/.ai_user_info/ai_proxy`（`10.16.1.51:3128`，带认证），逐进程导出 `http_proxy/https_proxy`；凭证不落仓、不打印、不进日志。

## 5. 评分与报告

- 完成后走正式 `score`（v1/v2 双口径），必须消费 `p2_full_status.json`。
- 报告标题与首段必须写：**"正式批次-单臂（B=v2card）；A=v1card 未跑，不出 B−A、不构成正式有效性结论"**。
- 只报：hit@1/@3/@5、strict(U)、rank>1、分族、novel 首选、失败/unknown/零调用、usage；token 只披露。
- B 验收通过后自动补 A；两臂齐后才出正式对照结论。

## 6. 依赖与停点

- **CC 亲自通知另一窗口停 P2/v2card**（本窗口无法控制其会话）。
- fatal 根因已定位（证据 `docs/review_evidence/p2_fatal_repro_2026-10-26/findings.md`）：`chemstate.py:703` 工厂按**原始串**算 `cn_identity`，`validate_state_object` 按**规范化串**重推；**驱动因素是原子映射号被 `_identity_key` 剥离**（`chemstate.py:209-210`），不是冗余括号/显式 H。**暴露面已按批级扫描更正**（`batch_scan/README.md`）：298 题冻结池/底物 1,475 条串 **0 分歧**；触发者是**模型自写的 novel SMILES**——已录制两臂 97 run/269 条 novel 规格中 2 条含映射号（同一题，即 fatal 题），静态不可枚举；full 298 按 2/238≈0.84% 外推约 1–3 题，另有 12 个 `budget_limit` 无响应 run 属未知面。修复口径 CC 2026-10-26 拍板 **B**（见下）。
- **映射号普查（2026-10-26，零模型）**：fatal 原始串 **19/21 原子带映射号**（19 个括号单元全是映射号；显式 H 17、电荷 0、同位素 0、立体 7）；raw CN 154 字符 → 去映射后 34 字符，**与 validator 的 CN(canonical) 逐字节相同**，分歧 100% 由映射号解释。269 条 novel 规格含映射号 **2 条**（v2card 2/134、v1card 0/135，均 `product_smiles`）；46 题回归集含映射号 **仅 1 题**（fatal 题）。**存量 117 run DB：646 states + 749 appearances + 333 含 CN 产物文件，带映射号 = 0**；fatal 态未落库（失败 run 的 state/appearance 均 0 行）；同一 `state_id` 在 3 个 run 已落库 8 行，CN 均 34 字符 `f6b6adde…`。⇒ **B 在存量上零 CN 变化（0/646）、零键冲突**；"无映射号存量 CN 不变"实测成立。
- **身份 v2 复审（2026-10-26）**：qwen3.8max 代 Codex = PASS_WITH_CONDITIONS；R1（两段时间线/引用）、R2（最终批准包 `c0b4c381…`/canonical `d950bf1d…` + rc=0 留档）、R3/R4（比较脚本、face 原件）、N1（新锁 `828c527b…` 归档到 `docs/T_P2_SCRIPT_LOCK_2026-10-26.json` 与批准包目录）全部闭合。仓库批准包已同步并保留 10-21 原始件 `ccdb9d14…`。**发车身份基准默认 = 批根存储值 `fcd84049…`**；`7be805d5…` 仅离线归一、不进入批根。§6.4 补绑效力按 CC 交接书+指令视为书面批准（CC 可另裁定）。
- **CC 补充事实（2026-10-26）**：fatal 原始串含 **19 个原子映射号**（1,2,3,4,7–21；5/6 缺失），不是纯冗余括号；该 state **写库前 fatal、未落库**，所以没有存量 CN 要改。B 只影响「带映射号**且已落库**」的输入；无映射号存量零漂移验收成立。若发现「无映射号但 B 会改 CN」的 case，修复线须明确标出，不得按零漂移过。
- **B 口径验收加码**：①无映射号**存量**（已落库）输入的 CN 必须与旧值**逐条相同**（硬零漂移）；②带映射号**且已落库**输入的 CN = 去映射号 canonical CN，并给出存量条数/qid 清单；③46 题回归 0 分歧、无新门；④旧录制态兼容性检查；⑤45 个非 fatal 回归题评分输出零漂移（若可离线复算）。
- **连锁后果（必须遵守）**：修复必动 `src/` ⇒ `code_identity` 变化 ⇒ 现有 10-23 build 的 `build_identity` 不再成立。因此修复落地后必须：①停，出补充披露（source_commit 从 `11aeeaf` 改为新 commit、code_identity 变化、重建说明）；②重跑 seed build + build-gate + build-copy + prepare（约 50 分钟离线）；③按新 build 重做身份路径归一并复审；④fatal 验收。**不得在未重建的旧 build 上跑正式批。**
- fatal 发车前验收必须含：①本 qid 零模型重放不再同款失败且无新门；②298 批 CN 分歧全量扫描清单上的所有 qid 离线重放不再触发；③writer/validator 同源性质测试；④源批根哈希不变。
- 若身份归一被代审判 NO-GO ⇒ 停，转 HPC 正式批或重开批准包，由 CC 拍板。
- **notebook 停点缺口（qwen 复审 A/B/C，默认保守处理，CC 可改判）**：①monitor 写的非 fatal 停（如 full 失败>15）不会中止相位内派发，余题跑完后由 phase 门拦 score——默认**接受费用暴露、不硬杀 wrapper**；②首 TERM 不调锁内 halt、不写 stop.json——默认**保持可复跑**，不写；③二次 TERM 仅硬退驱动、wrapper 成孤儿——已在文档披露，真硬停须 CC 明示授权。

## 6.1 执行记录（发车与结果）

- 2026-10-26 11:26Z：**B 臂 full 终态 `passed=true`**（294 completed + 2 模型结构失败 + 2 结构性零调用；0 failed/pending/fatal/内容失败），score rc=0；v2 hit@1 **68/298（22.82%）**、v1 64/298。报告 `docs/T_P2_B_ARM_RESULT_2026-10-26.md`，证据 `docs/review_evidence/p2_launch_2026-10-26/`（61 项）。
- 2026-10-26 13:11Z：**A 臂 full 发车**（pid **43617**，`FULL_ARMS=v1card` + `ALLOW_MULTI_ARM=CC-20261026`；`deploy_4 check` rc=0、`start` rc=0，三闸/配置/U7 全过；B 残留 `entry.pid` 39962 确认进程已死、归档为 `entry.pid.stale_b_full`）。子代理配额耗尽，发车与监控由主窗口执行；日志 `entry_20261026T131117Z.log`。两臂齐后出正式对照 B−A。
- 2026-10-26 14:03Z：**A 臂 full 终态 passed=true**（295 completed + 1 模型结构失败 + 2 结构性零调用；0 failed/pending/fatal），score rc=0；A v2 hit@1 **86/298（28.86%）**、v1 81/298。**两臂对照（headline v2）：B−A hit@1 −18、hit@3 −11、hit@5 −17、strict −17（配对 onlyA 22 / onlyB 4）、unmatched +15；v1 敏感性同构。§6.1 科学停点触发（strict 净失 −17 ≤ −3）⇒ 停点复盘，归 CC/老师，不自动改判。** 报告 `docs/T_P2_TWO_ARM_RESULT_2026-10-26.md`，证据 `docs/review_evidence/p2_launch_A_2026-10-26/`。

## 7. 证据与回传

每次动作落：命令、HEAD/代码 SHA、输入/输出 SHA、时间、执行人（窗口）、红绿结论。
证据目录统一 `docs/review_evidence/p2_nb_<route>_2026-10-26/` + `SHA256SUMS`。
主窗口汇报格式：结论先行 / 四件红绿表 / 停在哪个门 / 下一步选项。

## 8. 排障表

| 现象 | 先查 | 处置 |
|---|---|---|
| 代理下 API 仍 000/超时 | 代理环境变量是否进进程；`curl` 同环境复测 | 停，不盲跑；换显式 `https_proxy` 重试 1 次 |
| score 报缺 `p2_full_status.json` | 回执是否由本地入口写出、字段/路径是否符合 p2_operations 期望 | 停，修回执；不得手写伪造 |
| 同 qid 再现 `state_fact_rederivation_mismatch` | 复现记录、fix 是否在本批代码 | 停批保全现场，转 CC 线 |
| pending>0 超过 10 分钟 | run 日志、进程数、队列 | 停批，不剔题 |
| 非模型内容失败>15 | 分类计数 | 停批 |
| 批根出现并发写 | `ps`、锁文件、日志时间 | 立即停，报 CC |

## 9. 变更记录

- 2026-10-26：初版，按 CC 当日拍板写入。