# T-I C8 停点后重试路径代决报告（2026-10-21）

> **provenance：qwen3.8max 代 Codex 复审/代决，按 CC 2026-10-21 指示**（「需要我/师姐裁决的由
> Codex 代决，Codex 裁决即最终裁决」；本轮 Codex 无额度，由 qwen3.8max 代 Codex 执行，
> 不冒充 CC 本人，不替代正链 Codex 的最终复核权——CC 后置复核项见 §7）。
>
> **题域标签：[298域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本文件是操作路径裁决，
> 不含科学成绩；一切数字与 dev 双向不外推。
>
> 审阅环境：本机只读（macOS，仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，
> 实际 HEAD `11aeeafded1b41185f24de49767933709aad49db`）。本轮**未连接 HPC、未跑作业、
> 未调用模型、未读 key/金标/题面/封存 run、未改 stop.json/代码/证据/批准件**。
> 新增文件仅本报告。C8 网络证据本地核验：
> `docs/review_evidence/ti_c0_c5_2026-10-21/c8_SHA256SUMS` 4/4 OK
> （netprobe 脚本 + 计算节点 47014884 输出 + 登录节点经代理 + 登录直连对照）。

## 1. 总裁定

**选 B2：代理稳定门槛（§3）达标后，开新批根/新 batch_tag/新协调目录重走发车链；
旧批 100% 原样保全（stop.json 不清、4 个失败 case 不移、run history 不动）。**

- 这是对既有预注册 `prereg-t-i-298-2026-10-20` 的**继续执行**，不是新付费批、
  不产生新批准；no-cap 拍板继续有效；金额 unknown（§5）。
- 允许在 §3 门槛绿后**自动执行** §4 步骤，硬停点见 §6；任一停点触发即停、回 CC/代决，
  不自动绕过。
- B1 仅作为 CC 明确推翻本裁决时的后备（§4.4 给了最小合规步骤），默认不采用。

## 2. 三路径比较（代码与证据均已实核）

| 维度 | B1 同批 --resume | **B2 新批/新窗（选定）** | C 等待/换站/中止 |
|---|---|---|---|
| 停点纪律 | 需手工清 `stop.json`（代码无 clear 命令，grep 实核；`write_stop` 明写「首写生效、现场不删改」，ti_operations.py:943）+ 移走 4 个终态 case——两处都是对已停现场的手工记录变更 | 旧协调目录与 stop.json 原样保留；新 tag 用新协调目录，`require_no_stop` 天然绿 | 不触碰；但等待无期限，换站需重做 C2/C3+批准 |
| 门逻辑 | `_terminal_case`（s5b_orchestrator.py:830-837）跳过终态 case ⇒ 不移 case 则 smoke10 门 `n_completed_run_errors>0`（ti_operations.py:756-758）恒红；移 case 则 GLM 先付费补跑最多 9 题才到门 | 全新 case 集，门按原语义跑，无绕过 | n/a |
| 重试预算 | 用掉唯一一次同参重投（history 上限 2，ti_operations.py:2019-2020「同参重投已用一次，连续失败停报 CC」）；若代理再抖，新批也停且 history=2 封死第三次 ⇒ 被迫仍走 B2，双重浪费 | 新批 history 从 0 起，保留一次应急同参重投 | 保留 |
| 记录完整性 | run history/case 发生变更，结果报告背负「批中人工移件」披露债 | 旧批=基础设施停跑证据快照；新批=科学运行；两批身份清晰可审计 | 完整但无产出 |
| 单变量 | 旧 completed 题与新补跑题跨时间窗混合 | 两臂同一新窗、同新 build，唯一变量=模型，最干净 | n/a |
| 费用 | 省约 1 题（GLM 已 completed 的 qid）+ 省 build 机时 | 多付约 1 题 smoke 调用 + 两臂 build 约 1h/臂（**零模型费**）；no-cap 下差异可忽略，金额均 unknown | 零新增 |
| 时间 | 快约 2-3h（免 build/免身份重锁） | 多 2-3h（build+verify-identity+重锁确认） | 不可控 |
| 身份链 | 指纹不变（5014fa13…d330a，C7 实测两臂同值），无需 C6 重锁 | 新 batch_tag 进 run_id ⇒ `build_identity_fingerprint` 必变 ⇒ C6 重锁 + qwen/Codex 对实测读数的确认（§4 步骤 4；D6 门只要求**两臂逐字相同**+代码身份期望 `1aac04da…`不变，`verify_identity` 实核无旧指纹硬编码） | n/a |

**裁定理由（一句话）**：根因是站点代理间歇 TCP 不可达（计算节点 1/3 失败、登录经代理 1/1
失败、直连 401/0.167s，与 C3 同源、非模型特定），修复未证实；在未被证实稳定的基础设施上
花掉唯一一次同参重投、并以手工删改停跑现场为代价，换 2-3 小时与约 1 题的调用费——不值。
B2 多花的只是零费机时与一次机械的身份重锁，买到的是记录零污染、重试预算保留与最干净的
单变量叙事。TI-F1 监控本次正确触发并保全现场，本裁决不放松任何停点阈值。

## 3. 代理稳定门槛（付费步骤前必须全绿并落证据）

失败签名（已实测）：`curl_rc=28 / http_code=000 / connect≈7.01s 超时`；
成功签名：`curl_rc=0 / HTTP 401（无 key 探测的预期 API 层响应）/ connect≈3.0s / total<5s`。

| # | 门 | 判据 |
|---|---|---|
| G1 | 计算节点 soak（wzhcnormal，经站点代理，探 dashscope 端点，**不带 key**，沿 `c8_netprobe.sh` 同法） | **连续 12/12 次成功**（401 + connect<3.5s + total<15s），间隔 60s±10s，soak ≥12 分钟；出现任一次失败签名即整轮作废 |
| G2 | 登录节点对照（经代理） | 同窗 **3/3** 成功，间隔 60s |
| G3 | 登录直连对照（--noproxy，1 次） | 401 且 total<5s（证明 API 层活着，隔离「代理坏」vs「API 坏」） |
| G4 | 官方 C3 netcheck 作业 | G1-G3 绿后 **30 分钟内**提交，`COMPLETED 0:0` + `NETCHECK-PASS`；若距 soak 结束 >2h，先补做 G2(3/3)+计算节点 6/6 快检 |

- 概率依据：实测失败率约 1/4-1/3；若真实失败率仍为 25%，12/12 假绿概率 ≈ 0.75^12 ≈ 3.2%。
- soak 失败 ⇒ 等 ≥2h 重做整套 G1-G3；**连续两轮 soak 失败 ⇒ 停，报 CC**（换站点需重做
  C2/C3 与批准、中止归 CC，均属 C 路径，不在本裁决内自动执行）。
- 探针脚本/输出/时间戳落 `docs/review_evidence/ti_b2_soak_<日期>/` + SHA256SUMS；
  不打印任何 key（401 探测本身不带 key）。

## 4. B2 最小步骤（新批身份重锁）

命名提案（执行时以实际发车日登记，两臂必须同 tag，build 前落字）：
`batch_tag=t-i-298-<发车日>r1`（如 `t-i-298-20261021r1`）、批根/运行根
`t_i_298_<发车日>r1_{glm,deepseek}`、协调目录 `t_i_coordination_t-i-298-<发车日>r1`。

1. **soak 门**：§3 G1-G3 绿，证据落盘。
2. **config 唯一件修改**（`scripts/hpc/ti_arm_config.json`）：仅改 `batch_tag`、
   `date_stamp`、两臂 `batch_name`/`runs_name`、`paths.coordination_dir` 字面量
   （现硬编码 `t_i_coordination_t-i-298-20261020`，实核）、`immutable_batch_names`
   **追加旧两根** `t_i_298_20261020_{glm,deepseek}`（`mutable()` 即拒写旧批，实核
   ti_operations.py:494）。**不改**：题卷 SHA、`identity_expectations`（代码聚合
   `1aac04da…` 不变）、科学源码两 SHA、no_cap 块、approval 块、模型 ID、env 文件名、
   token_plan、`record_dir`（批准包与 tag 无关，验证只绑四文书 SHA + 字段，实核）。
3. **脚本锁重算 + 部署核对**：14 件重算（预期 13 件逐字不变、仅 config 变，沿 C6 重锁
   先例）；部署 HPC 树后逐文件 SHA 核对；orchestrator 停派发补丁 SHA
   `a95bb8be…5d62` 不变（已部署，不回退不重打）。
4. **C2-C5 在新窗重跑**（顺序照任务书 §5）：C2 作业能力/净环境 → C3 netcheck（G4）→
   C4 两臂 env/有效请求核对（不打印值）→ C5 每臂 1 次付费预检 +
   `preflight_calls.json`（新窗的代理/账号状态必须重证，不吃旧窗读数）。
5. **C6 重锁（build + 身份门 + 代审确认）**：两臂 build（零模型费，约 1h/臂）→
   build-gate → `verify-identity`：判据不变——两臂 `batch_tag`/manifest SHA/
   `build_identity_fingerprint`/298 条逐题 `(qid, run_input_sha256)` 逐字相同；
   指纹为**新值**（≠5014fa13…d330a 属预期，因 run_id 含 batch_tag）；实测读数落证据后
   **需 qwen/Codex 身份确认件**（沿 `T_I_C6_IDENTITY_QWEN_ACK` 先例；正链 Codex 恢复后
   可复核）。确认件落盘前不得 prepare/付费 run。
6. **C7 prepare**：两臂 prepare（自动重验批准包）+ P2 探针，期望计数与旧批一致：
   `specs_total=531 / remap_applied=242 / ge1=205 / ge2=78 / questions_remap=151 /
   with_add=134 / multi_add=65 / files=298`；不符即停。
7. **C8 发车**：两臂 run（smoke2→smoke10→barrier→full）+ `monitor --submit`；
   TI-F1 停点/barrier/15 分钟巡检全部照旧，**阈值零改动**。
8. **旧批零写入**：不清 stop.json、不移 case、不重命名；旧批作为停跑事件证据整体保留
   （含远端 `operations/c8_diag_20261021/`、monitor 作业记录）；结果报告按 §8 限制节
   披露第一次停跑与新批身份。

### 4.4 若 CC 推翻改走 B1（后备，默认不采用）——最小合规步骤与登记义务

先答问题：**B1 无法避免 case/run 记录变更**（门逻辑决定），本代决**不接受**其作为默认；
若 CC 明确拍板 B1，则必须：① `stop.json` + 4 个失败 case + 对应 run 目录先整体复制到
证据隔离目录并登 SHA256（远端+本地镜像），再清原位；② 只移这 4 个 qid 的 case 文件
（run 根保留；同参 identity 核对可容忍多余 run 目录），使 `_terminal_case` 判非终态、
同 qid 同参重派发；③ 变更逐件登记到 operations 记录 + 结果报告披露「批中人工移件与
清停点」；④ 重投前同样过 §3 soak 门；⑤ 明示 history 到 2 封顶——再停即无路径，只能
另批（回到 B2）。用掉唯一重投预算的风险由拍板人承担并落字。

## 5. 费用口径

- **重试不产生新批准，只是执行已有预注册**：`prereg-t-i-298-2026-10-20` +
  `preregistration_approval.json`（SHA `190e42a5…a50ae7`）+ `budget_no_cap.json`
  （`no_cap_ack=true`、`cost_cap_cny=null`）全部继续有效；批准验证绑四文书 SHA，与
  batch_tag 无关（实核），B2 不触碰批准件本体。
- 新增付费面 = C5 预检 2 次 + smoke2/10 两臂各 10 题 + full 两臂各 298 题（原计划内），
  外加 build 为零模型费。**金额 unknown**（无账单/单价快照；不估算、不编单价；
  事后账单回填，`cost_status=no_snapshot` 照旧）。gate_max_calls=4470/臂、RPM/TPM/并发
  守卫照旧生效。

## 6. 自动执行授权与停点

**允许**在 §3 门槛绿后由实施代理自动执行 §4 步骤 2-8（沿常设自动循环纪律），条件与硬停点：

| 停点（触发即停，不自动处置，回 CC/代决） |
|---|
| soak 连续两轮失败（G1-G3 任一） |
| C2/C3/C4/C5 任一红；预检 ok=false 或非 200 |
| verify-identity 任一不同值；身份确认件未落盘即想进 prepare/付费 run |
| P2 探针计数与期望不符 |
| 运行中任一 fatal / `consecutive_outage>=2` / barrier 不过 ⇒ TI-F1 自动停两臂后：**保全现场，不自动 resume**（第二次基础设施停跑=站点级决策，归 CC：换站重做 C2/C3+批准，或中止） |
| 任何需要写旧批根/旧协调目录/stop.json 的动作 |
| 任何冻结面（模型/题卷/代码/判分/profile/gate/超时重试）改动需求 ⇒ 一律停，另立预注册 |

不自动做的事：不清旧 stop.json、不封存任何批、不 push、不宣布成绩、不改停点阈值。

## 7. 需 CC 后置复核项

1. **批名 deviations 追认**：任务书 §1「批名发车前一次写死」；本裁决以新批名/新 tag
   开新批（旧批不改名不续跑），属操作面 deviation，依授权链（CC 2026-10-20/21 →
   Codex 代决 → 本轮 qwen3.8max 代 Codex）先行生效，请 CC 追认；正链 Codex 恢复后可复核。
2. **config-only 锁重算 diff**：确认仅 `ti_arm_config.json` 变、其余 13 件逐字不变。
3. **旧批保全状态**：确认 stop.json/4 失败 case/history=1 原样、两根已入
   `immutable_batch_names`。
4. **披露义务**：结果报告须并列披露第一次停跑（基础设施传输故障）与重试批身份。
5. **费用**：no-cap 下金额 unknown，账单出来后回填复核。
6. 若 §3 连续两轮 soak 失败：换站点（重做 C2/C3+批准）或中止，均归 CC/师姐，不在本
   裁决内。

## 8. unknown / 未核清单（诚实登记，不冒充已核）

| 项 | 状态 |
|---|---|
| 远端 HPC 读数：stop.json 内容/SHA、monitor 作业 47013128 COMPLETED、4 个 `completed_run_error` case 原文、`operations/c8_diag_20261021/` | **本轮未重核**（未连 HPC）；按协调者报告采信，与本地 netprobe 证据（4/4 SHA OK）方向一致 |
| 4 次失败的精确 failure_kind 文本（timeout vs connect） | 按请求文本采信，未读 case 原文 |
| 2026-10-20T21:22Z 之后代理是否已稳 | unknown（soak 门负责回答） |
| 站点代理根因/修复 ETA | unknown（站点运维侧） |
| 计算节点是否具备直连（--noproxy）出口 | unknown（登录节点直连已证 401/0.167s；计算节点未测；改网络路径不在本裁决范围） |
| 新窗两模型账号级限流状态 | unknown（C4/C5/smoke 负责重证） |
| 金额 | unknown（无快照，不估算） |
| 新指纹具体值 | 待 build 实测；只锁「两臂逐字相同 + 代码身份期望不变」判据 |

## 9. 证据与路径

- 本报告：`docs/T_I_C8_STOP_QWEN_DECISION_2026-10-21.md`
- 网络证据（本地已验 SHA）：`docs/review_evidence/ti_c0_c5_2026-10-21/c8_netprobe*`
- 停点/门代码依据：`scripts/hpc/ti_operations.py`（launch history 上限 :2017-2020、
  smoke10 completed_run_error 门 :756-758、write_stop「现场不删改」:943、
  mutable/immutable :494、verify_identity 无旧指纹硬编码）、
  `src/pathway_v43/pollutant/s5b_orchestrator.py`（`_terminal_case` :830-837）、
  `scripts/hpc/sbatch_ti_run.sh`（smoke2→smoke10→barrier→full :92-101）
- 冻结面/判据来源：`docs/TASK_T_I_LAUNCH_2026-10-20.md` §2/§3/§5/§7、
  `docs/T_I_PREREG_2026-10-20.md`、`docs/T_I_C7_PREPARE_2026-10-21.md`（旧指纹
  5014fa13…d330a 两臂同值）、`docs/T_I_TI_F1_FATAL_FIX_REPORT_2026-10-21.md`
- 本轮实际 HEAD：`11aeeaf`；未改任何 src/tests/scripts/既有 docs/证据/批准件；未 push。
