# P2 完整 v2 预注册/发车书 + 四个工程选择 — qwen 确认报告（2026-10-21）

> **provenance 首行：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示。**
> 不冒充 Codex/CC 本人；不替代 Codex 正链最终裁定权；不代签任何拍板。
> 只读复审：未改 src/tests/scripts/既有 docs/证据原件/封存批；未跑 HPC/模型；
> 未读金标/题面正文/reference_graphs/llm.env/密钥；未 push。
> 复审环境：仓库 HEAD 实测 `966bc5664a7daa30f24860d2b5594a9dddc6eee2`（基线
> `11aeeaf` 为其祖先，其后唯一提交 `966bc56` 仅 docs/证据、src 零漂移）；darwin arm64，python3。
> 证据身份：`p2_evidence_card_v2_2026-10-21/SHA256SUMS` 18/18 OK（`impl.patch` 实测
> `cd8c03e0…ebbd6` = 登记值；r1 `f3735bb0…7f6d` 同）；`p2_token_298_2026-10-21/SHA256SUMS`
> 5/5 OK；冻结设计 `37d85958…c4f4`、设计终认 `48dfc599…56e7` 实测吻合。
> 独立复算：token 载重读数 21/21 通过
> （`docs/review_evidence/qwen_p2_full_v2_confirm_2026-10-21/recheck.{py,log}`）。
> 被审文书 SHA-256 实测：prereg `8ad5473b…0528`、task `d47dae5d…067f`、CC 决定
> `85010405…9219`、impl 报告 `525365fd…c8498`、298 预测量 `1c1d277a…d443`。

---

## 1. 总裁定

**需修正（修正后可进下一阶段=离线准备）；付费批维持 NO-GO。**

| 项 | 裁定 |
|---|---|
| 预注册 `T_P2_PREREG_FULL_V2` + 发车书 `TASK_P2_FULL_V2_LAUNCH` | **方向与内容合格**：完整 v2、无 token 门、无截断、全 298 配对、strict 净失 ≤−3 停点、no-cap/usage/金额 unknown、选臂规则、付费前缺项全部落实且与 CC 决定/上一轮 qwen 代决无静默取舍。3 处小修（M1–M3）须在**签字前**闭合 |
| 四个工程选择 | 1=v1card **确认（附 provenance 条件 M2）**；2=共用 v2 prompt+披露 **确认**；3=克隆 p2_operations **确认**；4=seed build+copy **确认（附条件）** |
| 付费发车 | **NO-GO**：T-I 无最终有效批（仓内无 `T_I_RESULT_*`，模型 TBD）、预注册 DRAFT_NOT_SIGNED、化学复审未取得、v1card/操作链未实现、脚本锁未生成、付费授权未落字、Codex 正链未复核——发车书 §12 十项前置**全部仍缺**，与文书自述一致，无夸大 |
| 与上轮 qwen C 截断代决的关系 | 无冲突需列：CC 决定文件明确豁免 token 门（优先级高于代决建议），预注册 §4.6 把「qwen 判 FAIL」保留为事实、未改写成 PASS，C 的 schema-4/帽表/截断件确认**不进入**本批；上轮与 token 门无关的前置全部保留（§7.4） |

一句话：文书把 CC「不考虑预算、完整 v2、效果优先」的决定翻译成了可执行且诚实的
预注册/发车书，token 数字全部独立复算吻合；修 3 个小口径问题、补 1 个签字
provenance 后即可进入离线准备段（v1card 实现/操作链/化学复审送审）；付费批在
T-I 出结果并十项前置闭合前不得启动。

---

## 2. 四个工程选择（最终建议）

### 2.1 选择 1 — A 臂：**确认 `v1card`（v2 prompt + v1 卡），附条件**

- **科学理由**：A=v1 卡直接回答「是否用 v2 卡**替换现行生产 v1 卡**」——这是 CC 的
  实际决策问题；冻结设计的「无证据 A」回答的是「v2 卡比不给卡好不好」，而 v1 卡
  on/off 的历史读数（chain14）已是负结果参照，决策相关性更低。预注册 §2.5 的对比表
  对此描述准确。
- **必须附带的 provenance 更正（M2，不静默取舍）**：
  1. 冻结设计原文（`TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` §二.1）写的是
     「A 臂=**用户 JSON 字节兼容回退**」，r2 实现为 v2 prompt+无证据——即
     **「冻结设计原意=v2 卡 vs v1 卡」这一转述与冻结设计原文不符**；预注册 §2.5
     的表述（冻结设计 A=无证据）才是对的。`v1card` 是**对冻结设计的变更**，不是
     「回到原意」，须按 §2.5 差异表走签字确认，本文按变更路径确认之。
  2. 归档的 CC 决定文件（`P2_CC_DECISION_FULL_V2`）原文**不含**「A=v1 卡」字样；
     该口径目前仅由预注册 §0 转述（「按 CC 2026-10-21 要求」）。CC 签字文本必须
     显式落「A 臂=v1card」字样，补齐授权链。
- **工程条件（已是文书硬前置，重申）**：v1card 模式当前**未实现**（r2 patch 只支持
  v2+无证据 / v2+v2）；预注册 §2.5 七条实现要求 + 任务书 §3.3 最小合同（A 用户载荷
  与 v1 B 逐字节等价、v1card∧enabled=false 结构化拒、resume 同判据、off 零漂移、
  六类测试）完成并经 Codex/qwen 复审前，不签字、不发车。
- **披露维持**：A 臂=v2 prompt+v1 卡是生产中从未存在过的组合（生产 v1=v1 prompt+v1 卡）；
  本批读数是「v2 prompt 语境下 v2 卡 vs v1 卡」，不是完整生产替换效应——预注册
  §2.5/§10 已如实写明，不得在结果报告中丢失该限定。

### 2.2 选择 2 — 两臂共用 v2 prompt：**确认共用 + 披露，不分臂 prompt**

- 分臂 prompt 引入第二变量（prompt 版本），破坏「唯一变量=证据卡版本」与配对归因，
  且冻结设计明文「两臂共用同一新版 prompt」；
- 「严格中性共享 prompt」备选需要新冻结+新哈希+化学复审+token 重测，并改动已冻结的
  v2 prompt（`89311fdb…0f37`）——成本高且偏离已冻结面；预注册 §2.5 已把该出口留给
  CC 显式选择，默认不采用，正确；
- prompt-卡语义不匹配（v2 notes 描述 v2 字段；A 臂 v1 卡带 source/Gasteiger 等未被
  notes 描述的字段）**作为 treatment 一部分披露**（§2.5/§10.3），偏向方向 unknown，
  不得据此读单字段因果——文书已写死，维持。

### 2.3 选择 3 — `p2_operations`：**确认克隆 `ti_operations`，不硬改**

- `ti_operations.py` 被 T-I 脚本锁/代码身份冻结，`REQUIRED_ARMS=("glm","deepseek")`、
  四文书键、prereg id、no-cap 日期、批名全部 T-I 写死；T-I 仍在待续跑（站点 B2 阻塞，
  仓内无结果报告），硬改会破坏 T-I 冻结身份、重开 TI-F1/F2 复审，触碰「T-I 树不动」
  红线；
- 克隆条件（任务书 §4.2 已写死，重申为验收面）：阈值/fatal 分类/恢复一次二败/
  barrier/monitor 15min/stop.json 首写/seal/评分版本**逐字继承零改动**；差异严格限
  diff 白名单表（config schema/臂名/臂差异字段/四文书键/prereg id/no-cap 日期
  2026-10-21/批名/默认 config）；交付时附 diff 对照件 + 正负控。

### 2.4 选择 4 — build 策略：**确认 seed build + 字节级复制（推荐案），附条件**

| 影响面 | seed+copy | 两臂独立 build |
|---|---|---|
| 身份 | manifest SHA/fingerprint/298 逐题 run_input SHA **by construction 字节相同**，再经 §5.2 门实测核验（构造相等不替代核验） | 依赖两次 build 的完全确定性；时间戳/环境路径任何非确定性都会让「指纹逐字相同」硬门变成事后赌注（T-I D6 先例是通过了，但风险更高） |
| 时间 | 省约一半 build 机时 | 双倍 build 机时 |
| 单变量 | build 非实验变量；copy 消除「build 非确定性成为隐藏第二变量」的风险 | 理论同值，实际把等同性押在确定性上 |

- 条件（任务书 §5.1 已写，重申）：只复制 build 产物；**不复制** `orchestration.json`/
  `gate/`/cases/状态文件；`assets_root` 等环境路径标签按 T-I off-path 先例仅归一后
  比较非路径事实，**不得改指纹字段**；不得一臂 seed、一臂独立；复制后 §5.2 身份门
  1–8 项全跑，任一不过即停不 prepare。

---

## 3. 逐项核（请求核点）

| # | 核点 | 裁定 | 证据 |
|---|---|---|---|
| 3.1 | 完整 v2、无 token 门、无截断 | **通过** | prereg §0/§4.1/§7.1（`token_gate_disposition=waived_by_cc_full_v2_disclosed`；无帽表/无 `evidence_truncation`/schema 仍 3）；task §2「token 门：无」、§3.2 注「补丁 1–4 不含 C 件」；CC 决定 §3.1–3.4 同口径 |
| 3.2 | qwen FAIL 事实保留、不写成 PASS | **通过** | prereg §4.2 注 + §4.6 冲突表 + §10.11；task 红线 10「不得写 token 门已过」；CC 决定 §5「不改变其他门结论」——三方一致，无静默取舍 |
| 3.3 | 全 298 配对、失败不剔题 | **通过** | prereg §5.1/§5.2（分母固定 298；失败/零调用/超时/空响应/解析失败计未命中；空池 60 留分母单列；NC-9 2 题计未中单列）；与 298 预测量实测（60 空池、`RXNG_7a88659`/`RXNG_ed3d707` prep 失败、真实批 model_calls=0 同源）吻合 |
| 3.4 | strict 净失 ≤−3 停点 | **通过** | prereg §6.1（Δstrict=c−b，全局或任一 F1/F2/F3，评分后算、禁中途 peek、触发即复盘不宣布收益）；冻结设计 §二.4 停点最高优先继承；task §9.3/§11.1 同值 |
| 3.5 | no-cap / usage / 金额 unknown | **通过** | prereg §2.1（金额帽=无）/§4.4/§7.1（`no_cap_ack` 现 false，CC 阅险后翻 true）；task §10 `budget_no_cap.json`（marker 2026-10-21、与 budget_guard 互斥、gate/速率/并发守卫照旧、金额无账单 `cost_status=no_snapshot`/`cost_known_cny=null`、禁 token×单价估算） |
| 3.6 | 选臂规则 | **通过** | prereg §3.1 与请求逐字一致：T-I 完整有效 ∧ B−A hit@1 净增 ≥15 ∧ M2 ⇒ B（DeepSeek）；有效但不满足 ⇒ A（GLM）；未完成/无效 ⇒ 不选模型、付费批不启动（仅离线准备）。与 `T_I_PREREG` §3.2（≥15=5.03pp）/§3.3（M2 四条件：两桶增 ≥15、strict 桶损 ≤5、strict 覆盖降 ≤5、c≥1.5b）交叉核对一致；§3.2「完整有效」操作定义四条件明确；仓内无 `T_I_RESULT_*` ⇒ 模型 TBD 属实 |
| 3.7 | token 披露读数 | **通过（21/21 独立复算）** | +8.2165%/104(298 与 296 口径)/+64.1263%(`RXNG_1eba3a0`,8 候选)/194 过/−20.8432%(298/298 更小,max −6.6396%)/+4.7733%/候选分布 60-92-57-53-24-8-1-3/531 候选/146≥2/19.9104% 增量比——全部与归档 JSON 逐位吻合；口径标注正确（v2 B vs **无证据** A，非本草案 A）；§4.3 明确 A(v1card)/B 同 prompt 对比**待测**、发车前出披露件、只披露不设门、tokenizer 不可得记 unknown——诚实 |
| 3.8 | 付费前缺项 | **通过** | prereg §7.4 十项 / task §12 十项，覆盖请求点名六项（T-I 模型、预注册签字、v2 化学复审、付费代决、Codex 正链复核、批级工程）+ v1card 实现、代码身份/RDKit、token 披露件、站点 soak；「本文件不执行任何动作」声明在两文书头部均在 |
| 3.9 | 四选择与文书一致性 | **通过（选择 1 附 M2）** | 选择 1=prereg §2.3/§2.5+task §3.3；选择 2=prereg §2.1/§2.5+task §2；选择 3=task §4.1–4.3；选择 4=task §5.1–5.2；互相一致、与 CC 决定一致 |
| 3.10 | 分族冻结时序 | **需修正（M3）** | prereg §5.3 定义 F2=「同底物≥2 题**减 F1**」、F3=补集，却把 F2/F3 冻结时点写成「build/prepare 后、**发车前**」；而 F1 在 A 臂评分后（发车后）才冻结——发车前无法完成减 F1。task §5.3「F2/F3 预生成」同病。规则本身无事后裁量空间，属措辞/时序修正 |
| 3.11 | task 附录 A G4 命令 | **需修正（M1）** | 附录 A 第 610 行仍写 `sbatch_th_netcheck.sh`，与 §6.2「P2 不得直接用（CODE 写死 v43cTH）、必须交付 `sbatch_p2_netcheck.sh`」自相矛盾；`scripts/hpc/` 现仅有 th/298 两版 netcheck，p2 版属待交付件（补丁清单 #4） |
| 3.12 | 身份/基线 | **通过** | 基线 `11aeeaf` 冻结正确（当前 HEAD `966bc56` 仅 docs 提交，src 零漂移；`source_commit` 登记如实）；task §3.5 要求 P2 树新代码聚合身份、**不得沿用 T-I `1aac04da…`**；新树 `v43cP2` 不复用 `v43cTH`——与 T-I 冻结身份保护一致 |
| 3.13 | 单变量叙述诚实性 | **通过** | JSON 空白差异（A 默认分隔符/B 紧凑）作为非语义差异披露（prereg §10.4、impl 报告 §10.1 同款口径）；非盲臂（顶层 `transformation_ref` 保留）披露（§2.6）；「整包证据呈现、不识别单字段、不称纯重排」在 prereg 头部/§1.3/task 头部三处一致 |

---

## 4. 最小回修清单（仅请求范围内；均为签字前文书级修正，不触碰判据）

| # | 级别 | 内容 |
|---|---|---|
| M1 | P2（签字前） | task 附录 A G4 命令改为 `sbatch_p2_netcheck.sh`（或参数化 `CODE`），与 §6.2 对齐 |
| M2 | P2（签字前，provenance） | ① CC 签字文本显式落「A 臂=v1card（v2 prompt+v1 卡）」——归档 CC 决定文件无此字样，现仅 prereg §0 转述；② 按 prereg §2.5 差异表签认「v1card 是相对冻结设计的变更」；③ 更正「冻结设计原意=v2 vs v1」转述（冻结设计原文 A=字节兼容回退/无证据） |
| M3 | P2（签字前） | 分族时序：发车前冻结 **F2raw**（同底物≥2 题集合）+分族规则并记 SHA；最终互斥分区（F2=F2raw−F1、F3=补集）在 F1 冻结后按已写死规则确定性生成，记 `p2_family_partition.json` SHA；prereg §5.3 与 task §5.3/§9.3 同步该措辞 |
| M4 | P3（发车日回填，已自注防漏） | `token_plan_high` 占位 12,000,000 按实际规划回填；RDKit 2026.03.6(实现)/2026.03.5(HPC venv) 对齐或在实际版本重跑 v2 确定性锚并登记（prereg §10.6 已列，保持） |

---

## 5. 仍需 CC/老师批准的事项（本确认不代签）

1. **预注册签字**：`approval_status=preregistration_confirmed` + `approved_at`/
   `approval_source`/四文书 SHA/`model_id`/T-I 结果 SHA 回填；签字 SHA 必须按签字后
   最终文本计算；
2. **A 臂=v1card 设计变更确认**（M2；字段面/treatment 类事项归 CC）；
3. **`no_cap_ack=true` + 付费/HPC 授权文字**（阅 prereg §4.4 风险段后落字）；
4. **mimo 场景 1 v2 化学复审送审范围确认**（v2 字段语义/质子化 SMARTS/碳氧化态约定；
   涉题面数据外发须逐次拍板）；
5. **Codex 正链额度恢复后的复核确认**（设计/实施/放行类结论；qwen 代审不替代正链
   最终裁定权）；
6. 若 CC 要「严格中性共享 prompt」或 3 seed 等多 seed 设计：另立新冻结/新预注册
   （prereg §2.5/§10.1 已留出口，默认不采用）。

---

## 6. unknown / 未核清单

- **T-I**：最终有效批、模型 ID、最终 tokenizer 全部 unknown（仓内无 `T_I_RESULT_*`）；
  选臂规则已写死但输入未到位。
- **A(v1card)/B 同 prompt token 对比**：未测；现有 +8.2165% 等读数是「v2 B vs 无证据 A」
  口径，不得挪用为本批 A/B 增量（prereg §4.2/§4.3 已正确隔离）。
- **未实现件的行为**：v1card 模式、orchestrator/worker 批级冻结、`p2_operations` 克隆、
  `sbatch_p2_*`、脚本锁、P2 树代码聚合身份——均不存在，本审只核了其**合同条款**
  与文书一致性，无法核行为。
- **化学正确性**：v2 字段语义/SMARTS/碳氧化态的化学判读归 mimo 场景 1 链，未取得；
  本确认不认证化学。
- **真实批 usage/反馈轮/重试/输出 token/金额**：unknown；金额无账单不估算。
- **HPC 现场**：批根是否干净、题卷 SHA、env 权限、站点 soak G1–G4 新窗结果——本审
  未连 HPC，全部未核（发车前清单 #10–#12 覆盖）。
- **prompt-卡语义不匹配的行为效应方向**：未测，按 treatment 一部分披露。
- **CC「v2 卡 vs v1 卡」指令原文**：未见于归档决定文件，按 unknown 处理，签字时
  补链（M2），不据转述当已证事实。
- **本审未重放**：pytest/off-path 探针/298 测量脚本全流程未重跑——采信归档日志与
  JSON（两证据目录 SHA256SUMS 全 OK），并对全部载重数字做了 21/21 独立重算。

---

## 7. 与上一轮结论的关系

无静默取舍。上一轮 qwen 代决（C uniform 13%）被 CC 2026-10-21 决定**显式否决并留档**
（CC 决定 §5、prereg §4.6 冲突表逐条对照）；本轮确认该冲突处理方式合规：FAIL 事实
保留、豁免只限「作为放行门」这一项、C 的工件不混入本批、上轮非 token 前置全部保留。
本轮新增内容仅为 M1–M4 四处文书级修正与四选择确认，不翻任何既有结论。
