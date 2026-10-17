# T-F 专项合成验证报告——首位候选被折叠后的位次传递（2026-10-17）

- 判定：**证实**。模型首位 novel 被折叠进【无模型声明位次】的池条目时，该反应的展开位次
  劣化为 `deterministic_fallback` 殿后（劣于全部显式位次候选）；被折叠者的声明位次
  无继承、无痕丢失。与读码语义逐项一致（`docs/TF_RANK_TRANSFER_VERIFICATION_2026-10-16.md` §2.1）。
- 性质：合成夹具验证（老师任务书 P1-TF 口径：读码+合成夹具验证；**证实即修〔排序免费
  收益〕、证伪关闭**）。零模型（scripted 协议）、零金标零题面（纯构造输入）、零 git。
- 执行者：主会话（CC 2026-10-17 拍板「不派单、自己干」；当日 opencode 免费网关故障
  亦使执行器通道不可用，详见报告尾注）。
- 证据：`docs/review_evidence/tf_synth_fixture_2026-10-17/`（脚本+机读输出+README 含
  HEAD `3440ca7` 与复现命令）；实际 HEAD 与读码版一致，仓库零写入。

## 一、验证对象与前提

- 真实批证据链（前一轮）：chain13 本批 298 题「首位被折叠」**0/298 触发** ⇒ 真实数据
  无法检验该分支行为，须合成夹具（老师任务书要求的收口一步）。
- 读码风险形态：模型排 novel-1 第一位；novel-1 的净反应签名与**更早出现的池条目**相同
  且该池条目**无模型声明位次** ⇒ novel-1 折叠（`runflow.py:998-1014`，后到者折叠）、
  幸存池条目落 `deterministic_fallback`（`1040-1045`，排在全部显式位次之后）。

## 二、夹具设计与结果（四趟，观察面=search_actions 载荷）

公共池（纯构造，底物 CCO）：条目 A（产物 CC=O，change_bond_order 模板）+ 条目 B
（产物 CCOO，add_atom O 模板）；novel:1（产物与 B 同 ⇒ 同净反应签名，代码级前置核验
`B_eq_novelO=true`；fx3 变体产物 CCCO ⇒ 签名互异）。模型响应（scripted 协议，
`rank_hypotheses` 首位一律 novel:1）：

| 夹具 | 模型排名 | width | 结果（logical → model_rank / effective_rank / basis / status） |
|---|---|---|---|
| **fx1 风险形态** | novel:1 第1、A 第2、**B 不排名** | 2 | A→2/**1**/model_selection/done；**B→None/2/deterministic_fallback/done**；novel:1 无展开条目（被折叠，n_actions 比不折叠少 1） |
| fx1b 同 fx1 | 同上 | 1 | 同 fx1（宽度=1 未产生 deferred，见 §五注记） |
| fx2 良性对照 | novel:1 第1、**B 第2**、A 不排名 | 2 | B→2/**1**/model_selection/done（幸存者保留自己的声明位次）；A→None/2/fallback/done；模型第一选择的反应经 B 生效位次 1 |
| fx3 基线 | novel:1 第1、A 第2、B 不排名（novel 签名互异） | 2 | **novel:1→1/1/model_selection/done**；A→2/2/model_selection/done；B→None/3/fallback/**deferred**（cap 演示） |

## 三、判定（对照判定线写死）

- fx1 证实「**模型首位反应的实际展开位次（2，fallback）劣于全部显式位次候选（A 位次 1）**」
  ⇒ **证实**。模型的第一选择（novel:1 的反应，折叠后由 B 承载）从位次 1 劣化为位次 2
  殿后；模型的**第二**选择 A 反而先执行。位次不继承（B 的 model_rank=None，novel 的
  rank 1 消失无痕）。
- 对照链自洽：fx2（幸存者有位次）模型第一选择仍位次 1；fx3（不折叠）novel 位次 1 直达。
  即位次劣化**仅在「首位被折叠 ∧ 幸存者无声明位次」组合下发生**——与读码条件语义一致。
- fx3 的 B 顺带演示 fallback 殿后被 cap 挤成 `deferred`（备选不保证执行）——被折叠首位
  在更小 cap 下的进一步后果形态。

## 四、修复建议（按任务书只登记不动手）

- **缺陷**：`runflow.py:1015-1017` 幸存键过滤直接丢弃被折叠者的声明位次，无继承字段。
- **建议修法（排序免费收益档）**：去重折叠时，若被折叠者的 model_rank 优于幸存者的
  （或幸存者无声明位次），将该位次**继承给幸存者**并在 `dedup_rejections` 记录原位次
  与继承事实（披露优先）；生效位次仍走既有密集重编号。单变量小改 + 正负控（本报告四
  夹具可直接翻成回归测试：fx1 修复后 B 应得 effective_rank 1）。
- **真实批影响披露（诚实边界）**：chain13/chain14 真实批该组合 **0/298 触发** ⇒ 该缺陷
  在已跑批分布下未造成已知失分；修复属低成本加固，**没有真实批同口径前后对照可给**
  （无触发例）。是否修、何时修（可随 T-H 修复批捎带）= CC 拍板。

## 五、诚实边界与注记

1. fx1b（width=1）两候选均获展开（未见 deferred）：宽度参数对该形状的 cap 语义未由本
   夹具完全钉死，如实注记；deferred 后果已由 fx3 演示，不影响本判定。
2. 本验证覆盖 decide 装配+调度序（rank/effective_rank/rank_basis/状态）；「提交序=调度序」
   的端到端问题沿前一轮 unknown（未核范围不扩大）。
3. 合成输入纯构造（CCO/CC=O/CCOO/CCCO），零金标零题面零语料；scripted 协议零模型调用。
4. 池装配（build）侧折叠 41 题/50 次（前一轮发现）不在本验证范围（该层无 rank 语义）。

## 六、收尾核验

- 实际 HEAD `3440ca760ab35d5949cb0947c3c72922575349dc`（v4.3）；未切分支、未 commit、
  未 push、未改任何已跟踪文件；新增文件仅本报告两件+证据目录三件；运行数据在 /tmp
  （易失，脚本可复现）。
- 尾注（执行环境）：2026-10-17 下午本机代理（XQNetwork，127.0.0.1:7890）一度故障致
  opencode 免费网关 ConnectionRefused（mimo 与 OCAgent 通道同断）；后代理自恢复、
  mimo 通道回线。该事件与 T-F 验证内容无关，仅作执行环境 provenance 记录。
