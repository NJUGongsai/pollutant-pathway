# 任务书：T-F 专项合成验证——首位候选被折叠后的位次传递（零模型，2026-10-17）

- 日期：2026-10-17
- 性质：**合成夹具验证**（老师任务书 P1-TF 口径：读码 + 合成夹具验证；
  证实即修〔排序免费收益〕、证伪则关闭）。零模型、零 API、零费用、零 git。
- 执行者：OCAgent；预计 0.5~1 天；到点未完成如实记录 unknown 并停。
- 依据（可读取核对）：`docs/TF_RANK_TRANSFER_VERIFICATION_2026-10-16.md`
  （前一轮证据链核查：本批 0/298 触发该分支、读码语义、§7 建议）+
  老师任务书 `docs/TEACHER_TASK_GONGSAI_LINE_EXECUTION_2026-10-15(1).md` §三.6。
- 本地 Python：`/Users/cc/miniconda3/envs/depending43/bin/python`，一律 `PYTHONDONTWRITEBYTECODE=1`。

## 一、现状（自包含）

chain13 本批 298 题实测：净反应签名去重折叠共 3 次（2 题），被折叠者**均非**
模型首位 ⇒「首位被折叠」分支在本批真实数据上 **0/298 触发**——真实批无法
检验该分支行为，故须合成夹具（这正是老师任务书要求的"合成夹具验证"一步，
前一轮只完成了读码与真实批证据链核查）。

读码语义（HEAD `3440ca7`，行号以此为准，若与实际不符以实际读码为准并登记差异）：

| 步 | 位置 | 逻辑 |
|---|---|---|
| 池装配 | `pollutant/runflow.py:871-879` | 池条目先入 `prepared_entries`（按 pools 声明序） |
| novel 追加 | `runflow.py:923-959` | 模型 novel 提案逐条预校验（不过⇒`novel_rejections`）→ 通过者**追加**到 `prepared_entries` 末尾（:958） |
| 签名去重 | `runflow.py:998-1014` | 净反应签名已见 ⇒ **后到者折叠**进 `dedup_rejections`，先出现者幸存 |
| 位次过滤 | `runflow.py:1015-1017` | `model_rank_by_key` 用**幸存键集合**过滤显式 rank：被折叠者声明位次在此丢弃，**无任何继承字段** |
| 密集重编号 | `runflow.py:1031-1039` | 幸存显式 rank 键按声明位次升序 → `effective_rank=1..n`，`rank_basis=model_selection` |
| fallback 殿后 | `runflow.py:1040-1045` | 无显式 rank 的条目 → `effective_rank` 接在全部显式位次之后，`rank_basis=deterministic_fallback` |
| 入队 | `runflow.py:1059, 1102-1111` | `rank=effective_rank` 入队；消费侧 `queue.py:211-295`（rank 升序取任务、超 cap ⇒ deferred） |

**待验证的风险形态**：模型把 novel-1 排第一位；novel-1 的净反应签名与
**更早出现的池条目**相同，且该池条目**没有模型声明位次** ⇒ novel-1 被折叠、
幸存池条目落 `deterministic_fallback` ⇒ 模型首选反应的展开位次退到
**全部显式位次候选之后**（若 cap 小还可能被挤成 deferred 备选）。
chain13 本批 3 次折叠的幸存者全部有显式位次，该组合从未出现。

## 二、任务（三段）

### Phase A 读码定方案（先做，产物=设计注记 ≤30 行）

读 `runflow.py:923-1111` + `queue.py:211-295` + 现有 scripted 模型协议链测试
（零 monkeypatch 公开链，见 tests/ 目录搜 scripted）——写明：夹具走哪条调用
路径（优先 scripted 协议链整链；若无现成路径直达 decide 装配层，允许直接
调用装配层函数构造输入=单元级夹具，须写明为何该层足以代表整链）；观察哪些
字段（`dedup_rejections`/`model_rank`/`effective_rank`/`rank_basis`/入队序/
deferred）。**读码发现与 §一 语义矛盾即停**，写报告不改。

### Phase B 构造三夹具并跑

执行纪律（AGENTS 返工教训 6）：探针复制到**全新临时目录**执行，仓库文件
只读，`PYTHONDONTWRITEBYTECODE=1`，不在仓库原地跑任何会写盘的东西。

- **夹具 1（风险形态）**：池含 ≥2 条候选（至少 1 条**无**模型声明位次），
  scripted 模型响应把 novel-1 排第一位，novel-1 净反应签名与该无位次池条目
  相同 → 观察：novel-1 是否折叠、幸存者 `rank_basis/effective_rank`、
  展开与提交次序、cap 小时幸存者是否被 deferred。
- **夹具 2（良性对照）**：同构但幸存池条目**有**声明位次（如 rank 2）→
  预期：幸存者保留自己的位次、下游整体上移一格、novel-1 折叠无痕
  （= 前一轮真实批 3 次折叠的形态）。
- **夹具 3（无折叠基线）**：同构但签名互异 → 预期：novel-1 生效位次 1。

合成输入纪律：结构串**纯构造**（可用简单分子如 CCO/CC=O 自造签名相同的
两条候选），**不得取自题卷/金标/语料**；零题面零金标零模型。

### Phase C 判读（判定线写死，老师口径）

- **夹具 1 证实**「模型首位反应的实际展开位次劣于全部显式位次候选
  （或被 cap 挤成 deferred）」⇒ **证实**（登记为排序免费收益修复项，
  **只给修复建议不动手修代码**）；
- 夹具 1 位次无劣化 ⇒ **证伪**（T-F 按老师口径关闭）；
- 夹具 2/3 必须与读码语义一致，否则夹具本身有问题，回炉重造。

## 三、红线（违反=立即停止并报告）

零模型零 API（scripted 响应不算模型调用）；零 git（不切分支/不 commit/
不 push/不改任何已跟踪文件）；仓库文件只读；产物**只新增**
`docs/review_evidence/tf_synth_fixture_2026-10-17/` 与本报告文件；
不在封存 run/批根上跑任何东西；合成输入零金标零题面。

## 四、产物与回传义务

- 证据目录 `docs/review_evidence/tf_synth_fixture_2026-10-17/`：夹具脚本、
  机读输出 JSON、README（实际 HEAD、命令、输入输出 hash）。
- 报告 `docs/TF_SYNTHETIC_VALIDATION_2026-10-17.md`（+同目录大白话版
  `_PLAIN_`）：判定=证实/证伪一句话 + 三夹具结果表
  （effective_rank/rank_basis/提交序/deferred）+ 与读码语义一致性核对 +
  若证实的修复建议一段（不动手）。
- 回传主会话：①判定一句话；②三夹具关键数字表；③夹具走的调用层级与
  理由；④任何与 §一 行号/语义的差异登记。

## 五、排障表

| 症状 | 处置 |
|---|---|
| scripted 整链路径不可达 | 降级单元级夹具（直接构造装配层输入），报告登记层级与代表性论证 |
| novel 构造触发预校验拒 | 读 `validate_edits` 规则调整构造使其通过，登记调整内容 |
| 与 §一 代码行号不符 | 以当前 HEAD 实际读码为准，登记差异后继续 |
| 夹具 2/3 结果与读码语义不符 | 夹具回炉，不改判读预期 |
| 到时未完成 | 如实记录 unknown 并停，不赶工 |
