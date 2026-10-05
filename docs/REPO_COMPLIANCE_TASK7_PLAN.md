# 仓库合规整改方案（teacher 任务七）——数据出库 / enzyme_cage_v1 与编排主线恢复 / commit 粒度

- 日期：2026-09-30
- 性质：**方案级送审**（teacher 2026-09-30 批复 §三.③：下次主线交付前方案必须送审，不要求完成整改）。
  本文档只定方案，不含任何已执行的整改动作。
- 取证方式：全程 git 只读（`count-objects`/`ls-tree`/`rev-list --objects`/`cat-file --batch-check`/`log`）+ 仓内文档核对 + 本机兄弟仓磁盘核验，**零 LLM、零 API**。文中所有数字均为实测值，无法实测的标 [待确认]。
- 三项任务来源：`docs/REPLY_TEACHER_HUANG_EC298_2026-09-28.md` §9（144.2MB 数据入库、`enzyme_cage_v1`/编排主线删除、commit 粒度）；teacher 侧最新表述 `docs/TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md` §7 与 `docs/TASK_V43_HIT60_INDEX.md` T5 行。

---

## 0. 现状与三项事实（取证结果）

### 0.1 三个"仓库体积"口径与 144.2 / 192MB 勘误对账

先分清三个口径（实测，2026-09-30，HEAD=bf1ac38）：

| 口径 | 实测值 | 含义 |
|---|---|---|
| git 跟踪文件总量 | **198.6 MiB / 416 个文件** | `git ls-tree -r -l HEAD` 逐 blob 求和，即"入了库的文件"体积 |
| .git 对象库 | 28 MiB（松散 10.98 + pack 17.19） | `git count-objects -vH`，clone 实际下载量 |
| 工作区总占用（含 gitignored） | 531 MB | `du -sh`，含 runs/、金标隔离目录等不入库内容 |

**144.2 / 192MB 勘误对账**（两个数字都是真值，只是测量时点不同，均对应"跟踪文件总量"口径）：

| 引用值 | 实测对上的时点 | 出处 |
|---|---|---|
| 144.2MB | ecac176（2026-09-25 建仓首提交）跟踪文件总量 = **144.2 MiB / 114 文件** | 最早可考引用 = 本仓 `REPLY_TEACHER_HUANG_EC298_2026-09-28.md` §9（teacher 2026-09-27 原始任务书未入仓，其原文口径 [待确认]） |
| 192MB | 9509985（2026-09-28 23:08 Phase D 提交）= **192.0 MiB / 291 文件** | teacher `TEACHER_PLAN_V43_HIT60_MASTERPLAN_2026-09-29.md` §7 |
| 当前 | bf1ac38（2026-09-29）= **198.6 MiB / 416 文件**，仍在增长 | 本方案实测 |

体积演进：144.2（09-25 建仓）→ 148.1（09-27 Phase A 收口）→ 192.0（09-28 Phase D）→ 198.6（09-29）。**结论：无须"更正"任何一个数，须统一口径表述**——对外一律说"git 跟踪文件总量"，引用时带时点；当前值 198.6 MiB 为最新实测。注意 198.6 MiB ≠ clone 体积（.git 仅 28 MiB，文本 jsonl 压缩率高）。

### 0.2 事实一：大文件入库

- 跟踪文件 198.6 MiB 中：**assets/ 占 159.13 MiB（24 个文件）**，reports/ 占 37.18 MiB（201 个文件），代码+文档+测试+脚本合计约 2.2 MiB。
- 历史 >1MiB 的 blob 共 **11 个，全部当前仍在跟踪**（无"只留历史"的死重量）；最大 7 个合计约 179 MiB：

| 文件 | 大小 | 入库提交 |
|---|---|---|
| assets/analog/uspto_relaxed_index_v1.jsonl | 48.70 MiB | ecac176（建仓即入） |
| assets/v3_reactions/corpus_env/corpus_v1.jsonl | 48.57 MiB | ecac176 |
| reports/phase_d/v2_remap_provenance.jsonl | 24.22 MiB | 9509985（Phase D） |
| assets/analog/corpus_templates_v2.jsonl | 16.57 MiB | 9509985 |
| assets/analog/corpus_templates_v1.jsonl | 16.13 MiB | ecac176 |
| assets/v3_reactions/corpus_env/donor_index.jsonl | 14.25 MiB | ecac176 |
| assets/v3_reactions/templates/uspto_templates.json | 10.70 MiB | ecac176 |

- 数据不是"后来混入"的：**建仓首提交 ecac176 一次性进了 114 个文件、408,261 行插入**，144.2MiB 数据在仓库出生时就随仓入库（assets/ 迁移记录见 ASSETS.md：2026-09-24 从 dependingv3/dependingv4 逐字节复制并建 manifest）。
- 资产完整性现状：`assets/MANIFEST.sha256` 22 项覆盖全部跟踪资产，**实测 22/22 校验通过**（`shasum -a 256 -c`，2026-09-30）——出库方案可直接复用该清单作验收锚。

### 0.3 事实二：enzyme_cage_v1 与"编排主线"不在本仓

- 本仓 13 个提交的**全部历史对象中不存在任何含 cage 的路径**（`git rev-list --all --objects | grep -i cage` 零命中）；**全历史零删除提交**（`git log --all --diff-filter=D` 为空）。
- 即：所谓"`enzyme_cage_v1`/编排主线删除"**不是发生在本仓 git 历史内的删除，而是 v3 起新建仓时整条 v2 线资产未随迁**。v4.3 建仓只从 dependingv3/dependingv4 迁了环境降解检索资产（ASSETS.md 记载），EnzymeCAGE 线被留在旧仓。
- 本体去向（实测）：`assets/enzyme_cage_v1` = **EnzymeCAGE v1 模型定义代码（GVP+SchNet+attention 几何检索底座），17 个文件 / 3,341 行 / 164 KB，含 CC-BY-NC 4.0 LICENSE**。现存于本机三个旧仓，三份**逐字节一致**（目录级 SHA256 = `07f42a083dbd…f382`）：
  - `/Volumes/CC/Enzyme_Agent/dependingv2/assets/enzyme_cage_v1`（git 在案：`c67fc6b` 2026-09-15 "feat: 纳入 EnzymeCAGE v1 模型定义代码" + `0a2d894` 2026-09-15 13:59 补 CC-BY-NC 4.0 LICENSE；remotes 指向 org 仓 github.com/Water-Quality-Risk-Control-Engineering/depending）
  - `/Volumes/CC/Enzyme_Agent/depending/assets/enzyme_cage_v1`（同一 git 远端的工作仓）
  - `/Volumes/CC/Enzyme_Agent/depending-main/assets/enzyme_cage_v1`（非 git 的目录副本，对应 depending-main.zip）
- "编排主线"（按仓内文档与旧仓结构推断）：= dependingv2 的多节点编排线——`src/graph.py` + `src/state.py` + `src/nodes/`（13 个节点：orchestrator_node、enzymecage_node、enzyme_pool_node、substrate_node、reaction_node、reaction_prediction_node、llm_reranking_node、evidence_synthesis_node、multi_step_bridge_node、microbe_selection_node、organism_selection_node、trait_filter_node 等）+ `src/tools/enzymecage_client.py` 等。它以 `assets/enzyme_cage_v1` 为几何检索底座，是 v4.3 之前的整条 EnzymeCAGE 编排主线。**此解释为推断，teacher 原文口径 [待确认]**（2026-09-27 原始任务书未入仓）。
- 不可恢复处（实测排除）：封存镜像 `ec298_phase_a_seal/` 只含 runs（ec298_v43r1、exam298_agent、exam298_engine），无 cage 资产；Chenyu 远端 workspaces（CHENYU_ACCESS.md §2）只有 v3/v4 线四仓，无 v2 线。
- v4.3 设计约束：REPO_DESIGN.md §1 钦定"LangGraph StateGraph 是唯一的工作流编排层……不把旧洪水调度直接搬来"——**恢复的定位是资产保全（可溯源、可复用），不是把 v2 编排放回 v4.3 运行时**，除非用户另行拍板。

### 0.4 事实三：commit 粒度

- 全仓仅 **13 个提交**（09-25 至 09-29）。单提交触及文件数/行数 top：

| 提交 | 文件数 | 行数 | 内容性质 |
|---|---|---|---|
| ecac176 建仓 | 114 | +408,261 | 代码+配置+**144.2MiB 数据**+文档混于一个提交 |
| 9509985 Phase D | 160 | +77,189 | 任务实施+新资产 33MiB+产物混提 |
| 45cbb8d Phase D retest | 44 | +73,061 | 多份产物表 |
| e6543f1 Phase A R1 修复 | 34 | +25,388 | 修复+产物 |
| 6e572e0 raw-run audit | 51 | +20,996 | 报告+脱敏表+审计代码 |
| ea6de25 retest v2 | 22 | +56,921 | 修复+审计 |

- 当前工作树另有 **85 项未提交改动**（19 个 src/tests 修改 + 66 个新增：reports/phase_s15_hit60 等），正沿同一"大混提"模式累积；本地 v4.3 领先 origin/v4.3 **4 个提交**未推。
- 判定：问题不是提交太少也不是太多，是**单提交多主题**（任务书/实施代码/数据资产/判分产物四类不分开），以及**数据与产物无入仓门槛**（与事实一同源）。

### 0.5 选型硬约束（取证）

1. **历史 SHA 引用密度**：docs/ 及根文档中共 **30 处** commit SHA 引用（分布于 26 行；5c8f284×11、eb3ba7f×6、bf1ac38×3、ea6de25×2、e6543f1×2、a66ceae×2、27829ad×2、e51675e×1、9509985×1；不含本方案文档自身新增的引用），另 09-28 回信 §10 的送审锚"a66ceae…5c8f284"等引用在 git 之外。**任何历史重写都会打断这批引用——这是方案选型的一票否决级约束。**
2. **并发会话共享 worktree**：本仓为多会话/子代理共享工作树（AGENTS.md 工作约定；2026-09-30 当日即有并发会话在写 deep_recall_gate1/iteration2 与 T8 报告）。**活跃写盘期禁止动 git index/分支**——整改执行必须留协调静默窗口。
3. git 操作纪律：本方案起草全程 git 只读；执行期所有 git 写操作（rm --cached、commit、push）由用户在静默窗口内亲自或授权执行。
4. 仓内既有隔离先例：.gitignore 已排除 runs/ 全目录、153MB Phase B 离线产物、全部金标/评审隔离目录——**"数据不入 git"的纪律在仓内已是既定惯例**，甲案是把它补齐到 assets/ 与大表产物。

---

## 1. 整改方案一：数据出库

### 1.1 范围界定

出库对象 = 事实一表列的运行数据与大表产物：
- **A 类（运行数据，159.1 MiB/24 文件）**：assets/ 下 jsonl/json/txt 数据本体。保留 `assets/MANIFEST.sha256`、`MANIFEST.json`、README 等小文件在仓（它们是校验锚与来源账本，各自 <0.01 MiB）。
- **B 类（产物大表，约 27 MiB）**：reports/ 下 >1MiB 的派生表（v2_remap_provenance.jsonl 24.22 MiB、phase_a_v2 input_manifest.json 1.13×2、phase_d deepdiff_298.json 0.91 等）。**逐件裁定**：默认 >1MiB 的明细表出库外置，仓内保留 ≤1MiB 的摘要/汇总件与全部脚本。
- **C 类（不动）**：src/tests/docs/scripts/configs（合计约 2.2 MiB）与一切小文件。

### 1.2 甲案：前向清理（推荐起步）

**动作**（数据文件保留磁盘原位，只解除 git 跟踪，历史一个字节不改）：

1. [协调] 取得并发会话静默窗口（见 §4.2）；
2. `git rm --cached` A 类+B 类文件（**只清索引，绝不删盘上文件**——运行时读路径零变化，ReactionFinder 照常直读 assets/）；
3. .gitignore 增补对应路径（assets 数据本体、B 类大表），沿用仓内 Phase B 精例的注释格式写明"本地留存/外置位置见 xx"；
4. 更新 ASSETS.md：登记外置位置约定与校验命令（`shasum -a 256 -c MANIFEST.sha256` 流程不变，只是 manifest 在 git 内、数据在 git 外）；
5. 外置/备份存储三选一（[待用户确认]，汇总见 §6 通俗版末段与 S15 批次信 §5）：(a) 本机 gitignored 原位（零迁移成本，单机风险）；(b) Chenyu `/usrdata/EnzymeCAGE_data/` 副本（跨机备份，上行用 cy_scp，先校验 SHA）；(c) 归档 tgz + SHA256 清单存封存目录（冷备）。可组合，默认 (a)+(c)；
6. 用户 commit（单主题："chore: 数据出库，数据文件转 gitignored 外置，历史不重写"）。

**效果**：跟踪文件总量 198.6 MiB → 约 2~3 MiB（代码+文档+小表+manifest）；今后数据增量不再进 git。**不变**：.git 对象库 28 MiB（历史 blob 全保留）、全部 13 个 commit SHA、clone 行为。

**代价**：clone 后需先按 manifest 恢复数据才能跑引擎（新增一个"拉数据"步骤，可写成脚本）；仓库磁盘体积不变（这是诚实代价，见两案对比）。

**先例**：dependingv2 `67298c0`（2026-09-15）"BBD_DATA_ROOT resolver + v5 rankers committed + **230MB data out of git**"——同门同法已演练过一次，含 `bbd_data_root.py`（39 行环境变量解析器）可作外移时的读取层范本。

### 1.3 乙案：历史重写（可选后期，默认不做）

**动作**：`git filter-repo --strip-blobs-bigger-than 1M` 类操作，把 11 个大 blob 从全部历史抹除。

**收益**：.git 28 MiB → 估算 2~3 MiB（估算值非实测，实际取决于剩余小对象）；clone 真正瘦身。

**代价（一票否决项为主）**：
- 全部 13 个 commit SHA 重写 → docs 内 30 处 SHA 引用、09-28 回信等 git 外送审锚全部断链，需逐处人工改写并重新对账；
- origin/v4.3 需 force push + 远端协调（本地尚有 4 个未推提交要先收口）；
- 需全员静默窗口（所有本机/远端 clone 同步重置），并发会话全部停摆；
- 与仓内"历史读数不覆写"文化正面冲突（勘误都以"另立新档"处理，从无改写先例）。

### 1.4 两案对比与推荐

| 维度 | 甲案 前向清理 | 乙案 历史重写 |
|---|---|---|
| 防新增量 | 是 | 是 |
| clone 瘦身 | 否（.git 仍 28 MiB） | 是（→约 2~3 MiB，估算） |
| SHA 引用 | **零破坏** | 30 处+全断 |
| 静默窗口 | 短（index 操作数分钟） | 长（全员同步） |
| 可逆性 | 高（数据全在盘上） | 低（历史不可逆改写） |
| 远端协调 | 常规 push | force push 全员 |
| 仓内先例 | Phase B 精例 + v2 仓 230MB 先例 | 无 |

**推荐：甲案起步，乙案列为可选后期。**理由：teacher 的诉求是"数据出库"（止血增量），甲案即达成；乙案的唯一增量收益是 28 MiB 的 clone 体积，代价却是打断全部文档锚与全员协调——收益/风险比不成立。若将来 teacher 明确要求 clone 体积指标，再议乙案，且须连同 30 处 SHA 引用的改写清单一并送审。

---

## 2. 整改方案二：恢复 enzyme_cage_v1 与 v2 编排主线

### 2.1 恢复来源（按可信度排序）

1. **dependingv2 git 历史**（首选）：`c67fc6b`（17 文件/3,341 行）+ `0a2d894`（LICENSE），可 `git ls-tree -r --name-only 0a2d894 -- assets/enzyme_cage_v1/` 精确取清单与逐文件 SHA；
2. depending / depending-main 工作副本：与 v2 逐字节一致（目录哈希 07f42a08…），可作交叉校验；
3. org 远端 github.com/Water-Quality-Risk-Control-Engineering/depending：depending/dependingv2 的 origin，网路可达时可 clone 复核（[待确认] 是否走远端）。
- 封存镜像 ec298_phase_a_seal/ 与 Chenyu workspaces **均无此资产**（已实测排除），不是恢复来源。

### 2.2 恢复落位（默认案）

- `assets/enzyme_cage_v1/` **整目录入仓**（164 KB，体积可忽略）：17 文件 + LICENSE 原样，`assets/MANIFEST.sha256` 增列 17 行；ASSETS.md 增记来源（dependingv2 `c67fc6b`/`0a2d894`）、**许可 CC-BY-NC 4.0**（非商用条款须显式标注）与"模型权重未迁（如需运行时接线另议）"。
- v2 编排主线（src/graph.py + 13 nodes + tools）：按"参考存档"落位，两选一（[待用户确认]）：
  - (a) 入仓 `reference/v2_orchestration/`（新设参考目录；旧 dependingv4 系仓的惯例是 vendor/，本仓暂无此目录，落位名 [待确认]），只读存档+来源 commit 锚；
  - (b) 不入仓，外置档案（tgz+SHA 清单）+ docs 登记去向。
  - 默认 (a)：体积小（dependingv2 src/nodes 等约百余 KB 级），入仓才能满足"资产可溯源"的 teacher 验收口径。
- **运行时不接线**：v4.3 按 REPO_DESIGN 维持 LangGraph 唯一编排层。若用户/teacher 要求 enzyme_cage 功能回接 v4.3，属新功能立项（另立任务书），不混入本合规整改。

### 2.3 验收方式

- 文件清单：`git ls-tree -r 0a2d894 -- assets/enzyme_cage_v1/` 的 17 路径，逐文件 SHA256 与入仓版比对 **17/17 一致**；
- 编排主线：文件清单 + 逐文件 SHA（源自 dependingv2 相应提交树）落 docs 对照表；
- 许可与来源：ASSETS.md 记录来源 commit、LICENSE 原文在位、CC-BY-NC 4.0 标注可见。

---

## 3. 整改方案三：commit 粒度

### 3.1 向前纪律（整改本体）

自下一个提交起执行，写入 AGENTS.md 工作约定（一行纪律 + 指向本节）：

1. **单主题单 commit**：一个提交只做一件事（任务书 / 实施代码 / 数据资产 / 判分与产物四类分开，混提不再出现）；
2. **入仓门槛**：新文件 >1MiB 默认不入仓（走 §1.1 的 gitignored/外置约定，例外须在 commit message 里写明理由）；
3. **提交说明锚**：commit message 带产物 manifest/报告路径（如 `reports/…/output_manifest.sha256`），让每个提交可独立复核；
4. **交付前清树**：每次主线交付前，工作树未提交项收敛到"只留当批主题"（当前积压的 85 项按主题拆分提交，作为纪律的首轮执行样本——拆分方案由用户在静默窗口内执行）。

### 3.2 历史整理：默认不做

13 个历史提交被 30 处文档 SHA 引用锚定（§0.5），rebase/squash 同样改写 SHA，代价与乙案同源。**不做。**替代动作（零风险满足可读性）：新增 `docs/COMMIT_INDEX.md`（或并入本仓既有索引），把 13 个提交逐条列"SHA / 主题 / 涉及任务书 / 产物锚"，teacher 可一眼读历史而无须动历史。

---

## 4. 时序与协调

### 4.1 三项先后（互锁关系）

1. **本方案送审**（=随 S15 批次信发出，死线已满足）；
2. 用户拍板 [待用户确认] 项（汇总见 §6 通俗版末段与 S15 批次信 §5）；
3. **恢复 enzyme_cage_v1 + 编排主线存档**（最小动作、零风险、不依赖静默窗口的深度协调——只新增文件，不动既有跟踪文件，可最先执行）；
4. **commit 粒度向前纪律生效**（从 3 的提交起即按新纪律示范执行）；
5. **数据出库甲案**（最重、需静默窗口：涉及 index 清理、.gitignore、ASSETS.md、manifest 账本更新与外置备份）；
6. （可选后期）乙案历史重写：仅在 teacher 明确要求 clone 体积指标时再议，另案送审。

### 4.2 并发会话静默窗口（执行期纪律）

- 约定：**谁在活跃写盘就等谁收尾**。执行日先 `git status --short` 盘点并发未提交项，与在写会话（当例：deep_recall_gate1/iteration2、T8 报告代理）确认收尾或书面确认其改动不受影响后，才进入 git 写操作窗口；
- git 写操作（rm --cached / add / commit / push）一律由用户执行或明确授权后执行；本地 4 个未推提交的推送顺序由用户定；
- 窗口内一次做完一类动作（出库/恢复/拆分提交各自独立窗口），窗口外零 git 写操作；
- 若窗口被新会话打断，停止于最近一致点，登记进 docs 后择日续。

### 4.3 死线建议（自拟，供用户改）

| 里程碑 | 建议死线 |
|---|---|
| 方案送审 | 2026-09-30（随本批次信，已达成于发出时） |
| enzyme_cage_v1 恢复 + 编排主线存档 + 粒度纪律生效 | 2026-10-03 |
| 数据出库甲案完成（含外置备份与验收报告） | 2026-10-07 |
| 三项整改全部完成并向 teacher 报验收 | 2026-10-10 |

teacher 仅要求"下次主线交付前方案送审"；上表为整改本体的自拟排期，用户可整体改。乙案无死线（默认不排）。

---

## 5. 风险与验收（teacher 可复核口径）

| 项 | 风险 | 缓解 | 验收口径（全部程序可复核） |
|---|---|---|---|
| 数据出库-甲 | 误删盘上文件（rm --cached 误作 rm）；并发会话读 assets 断供；manifest 与数据失配 | 只用 `git rm --cached`；数据原位零迁移（默认）；manifest 在仓作锚 | ① `git ls-tree -r -l HEAD` 求和 <5 MiB；② `cd assets && shasum -a 256 -c MANIFEST.sha256` 全过；③ 引擎冒烟（checkenv 或小批判分）不依赖 git 状态跑通；④ 大表外置件有 SHA 清单 |
| 数据出库-乙 | SHA 断链 30 处+、force push、全员静默 | **默认不做**；若做须先交 SHA 引用改写清单 | （若启用）clone 后 `count-objects` 达标 + 全仓测试绿 |
| 资产恢复 | 来源不唯一/错版；CC-BY-NC 4.0 许可遗漏；与 v4.3 设计冲突（误接线） | 三副本已核字节一致；LICENSE 随目录入仓；默认不接运行时 | 17/17 文件 SHA 对 `0a2d894` 树一致；编排主线清单+SHA 落 docs；ASSETS.md 载明来源与许可 |
| commit 粒度 | 无技术风险；纪律执行走样 | 纪律写入 AGENTS.md；交付信附 commit 索引 | 自整改起新 commit 逐条可归单主题（`git log --stat` 复核）；`docs/COMMIT_INDEX.md` 覆盖全历史 |
| 全局 | 静默窗口协调失败；数据外置单点 | 窗口纪律 §4.2；外置默认 (a)+(c) 双份 | 整改完成报告列逐项验收结果，命令可复制重跑 |

**验收三句话**：仓库"入了库的文件"降到 <5 MiB 且数据仍可一键校验；enzyme_cage_v1 十七文件哈希对上 2026-09-15 的入库树；新提交单主题可读、历史一个 SHA 都没动。

---

## 6. 通俗版（大白话）

**三项体检结果**：第一，"144.2 还是 192MB"——都对，只是称重的日子不同：9 月 25 日建仓时 144.2，Phase D 干完 192，现在 198.6 还在涨；真正压秤的是 7 个数据文件（约 179MB），从建仓第一天就在库里。第二，enzyme_cage_v1（一套 164KB 的模型代码）和老的编排主线**不是在这个仓里被删的——是 v3 换新仓时压根没搬过来**，原件还好好躺在三个旧仓里，一字不差。第三，提交粒度：13 个提交里建仓那一笔就塞了 114 个文件 40 万行，后面几笔也是任务书、代码、产物一锅炖，现在桌上还堆着 85 件没提交的。

**打算怎么改**：数据出库走"前向清理"——文件留在磁盘原处、只是不让 git 再跟踪它们（一小时的活，什么引用都不会断）；真把历史里的旧数据抠掉那种"动大手术"方案先不干，因为仓里 30 处文档引用都指着旧提交编号说话，一动全断。旧资产直接从旧仓按哈希搬回来，164KB 顺手就入仓，但**不**把它接回 v4.3 的运行电路（新仓的设计就是不走老编排）。提交纪律从下笔开始改：一个提交只说一件事。历史提交不动，另写一张"提交索引表"让老师看得清。

**什么时候干**：本信先把方案送出去（死线要求的就是这个）；旧资产 3 天内恢复、粒度纪律立即生效、数据出库一周内做完，10 月 10 日前三项全交。动 git 前先跟正在写盘的会话打招呼，等人家收尾。

**要用户拍板的**：① "编排主线"是不是就指旧仓那 13 个编排节点（teacher 原话没存档，对不了原文）；② 恢复的代码放仓里还是放外置档案、要不要接回运行时（建议不接）；③ 出库的数据备份放哪（建议本机+归档包双份）。

---

## 附：本文档引用的取证命令（可复制重跑）

```bash
# 体积三口径
git count-objects -vH
git ls-tree -r -l HEAD | awk '{s+=$4} END {print s/1048576 " MiB"}'
du -sh . .git
# 各时点跟踪体积（勘误对账）
for c in ecac176 e51675e 5c8f284 9509985 eb3ba7f 2b1c39e bf1ac38; do \
  git ls-tree -r -l $c | awk -v c=$c '{s+=$4; n++} END {print c, s/1048576 " MiB", n " files"}'; done
# 历史 >1MiB blob 及路径
git cat-file --batch-all-objects --batch-check='%(objecttype) %(objectsize) %(objectname)' \
  | awk '$1=="blob" && $2>1048576'
git rev-list --objects --all
# 本仓无 cage 历史 / 无删除
git rev-list --all --objects | grep -i cage            # 零输出
git log --all --diff-filter=D --name-status            # 零输出
# 资产校验（22/22）
cd assets && shasum -a 256 -c MANIFEST.sha256
# 旧仓恢复源
cd ../dependingv2 && git ls-tree -r --name-only 0a2d894 -- assets/enzyme_cage_v1/
# SHA 引用密度 / 粒度
grep -roh "<13 个短SHA>" docs/ *.md | sort | uniq -c
git log --oneline | wc -l && git status --short | wc -l
```
