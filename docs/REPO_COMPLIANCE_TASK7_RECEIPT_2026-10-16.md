# 仓库合规任务七回执——数据出库 / 资产恢复 / 提交粒度（截至 2026-10-16）

- 日期：2026-10-16
- 性质：**回执文档（未跟踪新增，仅本单产出）**。随下一主线交付包提交；入仓 commit 时机 = CC
  拍板，本单不 commit、不 push、不切分支。
- 口径来源：9-30 送审方案 `docs/REPO_COMPLIANCE_TASK7_PLAN.md`（下称「旧方案」）定义的三项
  任务（数据出库 / enzyme_cage_v1 与 v2 编排主线恢复 / commit 粒度）；主单拆分书 PRED-10。
- 核对方式：**全程只读**（git log/status/ls-tree/count-objects/cat-file、ls/find/cat/grep、
  shasum -a 256 -c 校验），零模型、零 API、零费用、零写入。文中数字均为 2026-10-16 实测值
  （HEAD=3440ca7，v4.3），可按文末附录命令重跑复核。
- 数字性质：本文全部数字为**仓库工程事实**（体积/文件数/提交数/未跟踪数），不带题域标签、
  亦不与 298 / dev 任何成绩混写。

## 0. 交接快照对账（先核对，再判三项）

| 项 | 任务书/交接快照口径 | 2026-10-16 本回执实测 | 判读 |
|---|---|---|---|
| HEAD | `3440ca7`（v4.3） | `3440ca760ab35d5949cb0947c3c72922575349dc`（v4.3） | 一致 |
| 未推提交 | 12 个，push 待 CC 拍板 | `git log --oneline origin/v4.3..HEAD` = **12**（正确原文见 §3.2） | 一致，push 仍未执行（未 push，时机=CC 拍板） |
| 总提交数 | （9-30 时 13 个） | **284**；其中 `bf1ac38..HEAD` = 94 个（9-30 方案基线后新增） | 期间新增 94 提交 |
| 未跟踪 | 217 条、全部 `??`、零已跟踪改动 | **226 条：225 条 `??` + 1 条已跟踪改动**（见下方按顶目录分解） | **多出 1 条 ` M AGENTS.md`**，环境注记（§4），非他人队列改动 |
| 跟踪文件总量 | （9-30 实测 198.6 MiB / 416 文件） | **624.157 MiB / 10738 文件**（`git ls-tree -r -l HEAD` 逐 blob 求和） | 9-30 后又增长约 3.1 倍，主因是 docs/review_evidence 评审证据入库（§3.2） |

未跟踪条目按顶目录分解（`git status --porcelain | sed 's/^...//' | sed 's|/.*||' | sort | uniq -c | sort -rn`）：
`docs` 218、`assets` 3（`METANETX.json`、`USPTO.json`、`rhea.json` 三个新数据件，未跟踪）、
`scripts` 1、`.zcodeignore` / `.opencode` / `.multica` 各 1；另有 1 条已跟踪改动 ` M AGENTS.md`。

---

## 1. 任务一：数据出库（旧方案甲案口径）——**未开始**

### 1.1 状态

**未开始（零动作落地）**，按旧方案 §1.2 甲案动作清单逐项判定，且验收指标反向恶化。

### 1.2 证据（可重跑，命令见附录）

| 甲案验收口径（旧方案 §5） | 2026-10-16 实测 | 判定 |
|---|---|---|
| ① `git ls-tree -r -l HEAD` 求和 < 5 MiB | **624.157 MiB / 10738 文件** | 不达标（较 9-30 的 198.6 MiB 不降反升） |
| ①a A 类运行数据出库 | `assets/` 跟踪仍为 **159.134 MiB / 24 文件**，与 9-30 实测**逐字节同一集合**（uspto_relaxed_index_v1.jsonl 48.70 MiB、corpus_v1.jsonl 48.57 MiB、corpus_templates_v1/v2 16.13/16.57 MiB、donor_index.jsonl 14.25 MiB、uspto_templates.json 10.70 MiB 等） | 未出库 |
| ①b B 类大表产物出库 | `reports/phase_d/v2_remap_provenance.jsonl`（24.22 MiB）、`reports/ec298/phase_a_v2*/input_manifest.json`（1.13 MiB ×2）等仍全部在跟踪；`reports/` 跟踪总量 **40.581 MiB / 353 文件** | 未出库 |
| ② `shasum -a 256 -c assets/MANIFEST.sha256` 全过 | **22/22 OK**（数据完整性仍可一键校验——出库验收锚完好，届时直接复用） | 在位 |
| ③ 引擎冒烟不依赖 git 状态 | 属甲案**执行期**验收项，甲案未执行，本轮不适用（不跑、不碰运行环境） | 不适用 |
| ④ 大表外置件有 SHA 清单 | 无任何外置/备份动作记录，外置件不存在 | 未达成 |
| .gitignore 对应增补（甲案动作 3） | 9-30 后 `.gitignore` 仅 +42 行（runs/、reports 隔离目录、金标手工复核目录、`.env` 反排除），**无任何 assets 数据出库条目** | 未增补 |
| `git rm --cached` / ASSETS.md 外置登记 | `git log bf1ac38..HEAD -- assets ASSETS.md` 仅早前既有提交，甲案专用提交不存在 | 未发生 |

### 1.3 未完成原因

1. 甲案全部 git 写操作（`rm --cached`、.gitignore/ASSETS.md 改动、外置备份、出库 commit）按旧方案
   §4.2 须在并发静默窗口内由用户执行或明确授权；自 9-30 送审后**未获得执行授权/CC 拍板**，
   回修循环与 chain13/14 各轮均未含此窗口。
2. 9-30 方案属「方案级送审」，不要求当日完成；其后主线优先级让位于 PPV1 评审-回修循环、
   chain13/14 双臂批与 P0 三件套（见 `docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` 主序列）。
3. 本回执轮次红线为只读核对，不执行出库动作本身。

### 1.4 与 9-30 状态差异（逐条）

| 项 | 9-30 | 2026-10-16 | 变化 |
|---|---|---|---|
| 跟踪总量 | 198.6 MiB / 416 文件 | 624.157 MiB / 10738 文件 | **恶化**（新增输入全是评审证据目录与大表，见任务三项 §3.2） |
| A 类 assets/ 数据 | 159.13 MiB / 24 文件在跟踪 | 159.134 MiB / 24 文件在跟踪 | **未动**（同一集合，零泄露零损失） |
| B 类大表 | 约 27 MiB 逐件裁定方案 | 原件未动，另有 task 三中新的 >1MiB 件入库 | 未动 |
| manifest 校验 | 22/22 过 | 22/22 过 | 持平（完好） |
| .gitignore 数据出库条目 | 无（待增） | 无 | 未动 |
| 血止增量（防新增数据入库） | 未实施 | **未实施，且期间以 review_evidence 形式新增约 414 MiB 跟踪内容** | 恶化 |

---

## 2. 任务二：enzyme_cage_v1 与 v2 编排主线恢复（旧方案默认案口径）——**未开始**

### 2.1 状态

**未开始**：仓内（HEAD 树与工作树）零 cage 痕迹、零 `reference/` 目录、`assets/MANIFEST.sha256`
未增列、`ASSETS.md`（27 行）无任何 cage/恢复条目。

### 2.2 证据（可重跑）

| 旧方案验收口径（§2.2/§5） | 2026-10-16 实测 | 判定 |
|---|---|---|
| `assets/enzyme_cage_v1/` 入仓（17 文件 + LICENSE，164 KB 级） | `git ls-tree -r HEAD --name-only | grep -i cage` **零命中**；工作树 `find -iname '*cage*'` **零命中** | 未入仓 |
| v2 编排主线按参考存档落位（默认 `reference/v2_orchestration/`） | 本仓无 `reference/` 也无 `vendor/` 目录 | 未落位 |
| `assets/MANIFEST.sha256` 增列 17 行 | manifest 仍为 22 项，无 cage 项 | 未增列 |
| ASSETS.md 记来源 commit + CC-BY-NC 4.0 许可标注 | `grep -i cage ASSETS.md` 零命中（全文 27 行） | 未登记 |
| 恢复来源可用性（前提仍成立） | 三份本地副本仍在且内容在位：`../dependingv2`、`../depending`、`../depending-main` 各有 `assets/enzyme_cage_v1`（磁盘 18 文件）；取文件清单权威源 `git -C ../dependingv2 cat-file -t c67fc6b` / `0a2d894` 均为可解析 `commit`，`git -C ../dependingv2 ls-tree -r --name-only 0a2d894 -- assets/enzyme_cage_v1/` = **18 个路径**（17 个代码/数据文件 + LICENSE），同一树 `src/graph.py + src/state.py + src/nodes/ + src/tools/enzymecage_client.py` = **16 个路径** | 恢复源完好，随时可执行 |

### 2.3 未完成原因

1. 旧方案 §6 拍板点②（落位两选一 + 是否接回运行时）**未拍板**：默认案（入仓
   `reference/v2_orchestration/` + 运行时不接线）已写明，但执行需用户确认；
2. 旧方案 §4.1 时序中恢复排第一顺位（最小动作、只需新增文件），但同样属 CC 授权的
   git 写窗口内动作（`git add` + commit），静默窗口未获得，零动作。

### 2.4 与 9-30 状态差异（逐条）

| 项 | 9-30 | 2026-10-16 | 变化 |
|---|---|---|---|
| 仓内 cage 资产 | 不在（v4.3 建仓未迁） | 仍不在（树+工作树双零命中） | 未动 |
| 编排主线存档 | 方案待拍板 | 方案未变、未落位 | 未动 |
| 恢复源三副本 | 实测逐字节一致（目录SHA 待复验） | 三副本目录均存在、主体文件均在（目录级复验采信 9-30 记录，本轮只验了 in-place 文件在位数 18 与 git 树可解析性，**未做目录级 SHA 重算**——如实标注 partial） | 来源侧无变化 |
| ASSETS.md 登记 | 待做 | 未做 | 未动 |

---

## 3. 任务三：commit 粒度（旧方案 §3 口径）——**未开始（纪律未成文），期间有局部向好迹象但无规则保障**

### 3.1 状态

**未开始**：旧方案 §3.1 四条前向纪律（单主题单 commit / >1MiB 入仓门槛 / 提交说明锚 /
交付前清树）无一成文、无一可核查落地；配套 `docs/COMMIT_INDEX.md` 不存在。

### 3.2 证据（可重跑）

| 旧方案 §3 落地项 | 2026-10-16 实测 | 判定 |
|---|---|---|
| 纪律写入 AGENTS.md（一行纪律+指向） | `grep -nE '单主题|粒度|COMMIT_INDEX|1 ?MiB' AGENTS.md` **零命中**（现行 400 行文本中无粒度纪律条） | **未写入** |
| `docs/COMMIT_INDEX.md` 全历史索引 | 文件不存在 | 未做 |
| 交付前清树（积压拆分提交） | 9-30 时未提交积压 85 项；现未跟踪已达 **225 条**（多含 docs 大宗：chain13 交付文档、chain14 结果报告、mimo 回应等） | 未做且恶化 |
| 单主题单 commit 实践 | 未推 12 提交中确有相当数量单主题提交（如 `5ade032` docs 预注册翻标签、`b6ba35f` docs 措辞落字、`dda852b` fix 单集合校验）；但**多主题混提仍在批量出现**——如 `0ba764f`（架构规划+评审综合+拍板记录+红线集合于一提交）、`0e345e8`（评审归档+判据冻结+三份任务书+AGENTS.md 条款于一提交）、`3440ca7`（证据卡 A/B 发车物+四轮回修于一提交） | 无规则保障，实践部分贴合、无约束 |
| >1MiB 入仓门槛（例外须写明理由） | 9-30 后经 `0e345e8` 一笔把 `docs/review_evidence/` 评审证据整目录入仓：现跟踪面 **414.352 MiB / 9823 文件**（含 6 个 ~29 MiB `g01_inputs.tar.gz`、多份 >1MiB observations JSON）——各 >1MiB 文件 commit message **未写例外理由**；跟踪总量因此由 198.6 MiB 升至 624.157 MiB | **违门槛且无例外声明** |
| push 状态（交包前提，非整改本体） | `git log --oneline origin/v4.3..HEAD` = **12 未推**；push 时机 = CC 拍板（任务书红线），本回执不执行、不宣布 | 如实挂账 |

### 3.3 未完成原因

1. 纪律写入 AGENTS.md 属已跟踪文件修改 + commit，与恢复/出库同一静默窗口纪律，未获授权；
2. `0e345e8` 一类的多主题大提交与 >1MiB 归档入库，是对旧方案 §3.1.2 门槛的直接反面；
   按旧方案「例外须在 commit message 写明理由」条款，该提交未声明——属纪律缺席下的
   自然行为，而非有意越规（诚实陈述，不升格为「故意违反」）；
3. 本回执红线明确不改已跟踪文件、不 commit，故「把纪律落字」也不在本单动作面内。

### 3.4 与 9-30 状态差异（逐条）

| 项 | 9-30 | 2026-10-16 | 变化 |
|---|---|---|---|
| 纪律成文 | 提出，未写入 AGENTS.md | 仍未写入 | 未动 |
| 粒度实践 | 建仓期四类混提典型（ecac176 建仓 114 文件 +40.8 万行） | 近 94 提交（bf1ac38..HEAD）中**单主题比例改善**（大量 docs/fix 粒度提交），但混提型与超门槛入库未绝迹；总量 13→284 提交 | **部分向好**（实践面），无规则固化 |
| review_evidence 入库 | 未见此类 >1MiB 证据目录入库 | **414.352 MiB / 9823 文件**已入跟踪面（0e345e8 起） | **恶化**（与 §1 数据出库目标同源冲突） |
| 积压未提交 | 85 项 | 未跟踪 225 条（另有 1 条环境注记已跟踪改动，§4） | 恶化 |
| COMMIT_INDEX.md | 待做 | 不存在 | 未动 |
| 未推提交 | 4 个 | **12 个**（push 待 CC 拍板） | 增长，挂账未清 |

---

## 4. 尾注与如实披露

1. **交付挂账**：本回执将随下一主线交付包提交（含收口 push、chain14 待补项披露与 T-F 验证
   状态一并交，见 `docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` 拍板点表）；入仓 commit 时机 =
   CC 拍板；push 本身亦为 CC 拍板项，任务三大项如实记「12 未推、push 待 CC 拍板」。
2. **汇总**：截至 2026-10-16，任务七三项均为**未开始**（零项动过）——数据出库（甲案零动作、
   验收面反向恶化）、资产恢复（恢复源完好在位、仓内零落地）、提交粒度（纪律未成文、
   实践局部向好但无规则保障且 review_evidence 大宗入库）。三项的执行路径均在旧方案文本内
   说明，无须新方案；唯一关口是旧方案已明列的**用户拍板/授权静默窗口**未曾开启。
3. **环境注记（非队列改动，未触碰）**：核对时工作树存在一条已跟踪改动
   ` M AGENTS.md`（+241 行，纯文件尾追加），内容为 Multica 运行平台在本仓 in-place 模式下
   注入的 auto-managed 运行环境护栏块（标注「do not edit」）。它晚于交接快照检查时点
   （彼时零已跟踪改动）出现，**不是任何代理或本单作者的人为改动**；本单按红线未回写、
   未提交、未还原该文件，留 CC 处置（保留随平台运行 / 提交前手动还原其一，两者取一即
   是拍板项）。
4. 本单全程零模型、零 API、零费用；除新添本回执文件与一个用于发评论的临时文件（发完即删）
   外，未创建、未修改、未删除任何文件，未触碰 `reports/`、`runs/`、金标、题面、封存 run。

## 附：本文核对命令清单（可复制重跑，全部只读）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
git rev-parse HEAD                                          # 3440ca760ab35d5949cb0947c3c72922575349dc
git log --oneline origin/v4.3..HEAD | wc -l                 # 12
git log --oneline | wc -l                                   # 284
git log --oneline bf1ac38..HEAD | wc -l                     # 94
git status --porcelain | wc -l                              # 226（225 ?? + 1 M AGENTS.md）
git status --porcelain | grep -v '^??'                      # " M AGENTS.md"
git ls-tree -r -l HEAD | awk '{s+=$4} END {print s/1048576 " MiB"}'   # 624.157 MiB
git ls-tree -r -l HEAD -- assets/ | awk '{s+=$4;n++} END {print s/1048576" MiB",n" files"}'  # 159.134 MiB / 24
git ls-tree -r -l HEAD -- docs/review_evidence/ | awk '{s+=$4;n++} END {print s/1048576" MiB",n" files"}'  # 414.352 MiB / 9823
git log --oneline --diff-filter=A -- 'docs/review_evidence/ppv1_s3a_codex_r2_2026-10-07/execution_specialist/g01_inputs.tar.gz'   # 0e345e8
git ls-tree -r -l HEAD | awk '$4>1048576 {printf "%.2f %s\n",$4/1048576,$5}'   # >1MiB 跟踪件清单
cd assets && shasum -a 256 -c MANIFEST.sha256 | grep -c ': OK$'    # 22
git ls-tree -r HEAD --name-only | grep -i cage              # 零输出（cage 未入仓）

# 资产恢复源（dependingv2）
git -C ../dependingv2 cat-file -t c67fc6b                   # commit
git -C ../dependingv2 ls-tree -r --name-only 0a2d894 -- assets/enzyme_cage_v1/ | wc -l   # 18
git -C ../dependingv2 ls-tree -r --name-only 0a2d894 -- src/graph.py src/state.py src/nodes/ src/tools/enzymecage_client.py | wc -l  # 16

# 粒度纪律是否成文
grep -nE '单主题|粒度|COMMIT_INDEX|1 ?MiB' AGENTS.md          # 零输出
ls docs/COMMIT_INDEX.md                                     # 不存在
```
