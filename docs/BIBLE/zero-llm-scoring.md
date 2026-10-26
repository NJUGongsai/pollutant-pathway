# zero-llm-scoring — 判分零 LLM、金标隔离

> 状态：L1 已完成（2026-10-26）。检查脚本第一批已实现。

## 1. 一句话规则

指标计算只用确定性代码读封存产物；模型、金标正文、可写路径三者永不进判分链。

## 2. 为什么

判分一旦掺进 LLM 或读金标的自由逻辑，「分数」就变成了「生成物」：
既没法复算，也没法向老师/评审证明同一批产物换个人跑会得同一个数。
零 LLM + 金标隔离 + 封存只读三件事合起来，才让 89/298 这种数字
有一个可以被任何人机械重放的来源。

## 3. 细则

1. **判分器只做确定性计算**：scoring 源码不得 import 任何模型客户端
   或网络栈（现源码 `src/pathway_v43/pollutant/s5b_scoring.py` 的
   import 面只有 json/math/random/pathlib 与仓内 evaluation/profile/
   reference_graph 模块——这就是合格形态）。
2. **金标（reference_graphs）只在 scorer 进程内被消费**：金标产物不
   入仓、不外发、不打印内容；诊断/评审只允许「只读计数/哈希」，逐题
   对错明细留在受保护 scorer 内部（`s5b_scoring.py` 的保护边界注释
   即此规则）。
3. **封存只读**：批根出分后整体封存（`th_sealed.json` + 目录 555/
   文件 444，runs 根不封）；封存后任何人只读消费，不重跑不重判。
4. **正式分数必须过正式入口**：阶段门回执（如 `p2_full_status.json`）
   缺失时正式 score 入口必须拒判；绕门评分只能标注「诊断口径」，
   不得写入正式结论或伪造 receipt。
5. **程序不自行宣布评测结论**：评测器状态只发
   `pending_user_teacher_decision` 族，最终状态归用户/teacher 裁定。
6. **LLM 可以做化学判读，但那是另一条有门的线**：误拒率判读之类
   LLM 参与的工作必须走一致性二读门 + 终审 + provenance，产物永不
   与零 LLM 指标混在同一口径里。

## 4. 反例

反例：正式 score 入口被阶段门拦下，诊断评分被迫明确降级为「不构成
放行」（`docs/NOTEBOOK_MIGRATION_2026-10-23.md:21`、`:199`、`:201`）
发生什么 → P2 批在 r2 fatal 停点，批根缺 `p2_full_status.json`，
正式入口 `p2_operations.py score` 两臂均 rc=1，报
`score 前缺 full 阶段门回执`。
→ 后果：本轮只能复制批根到诊断目录直接调 `s5b_scoring.score_s5b_batch`
跑 v1/v2 口径，且报告明写「不改迁移批根、不写正式 receipt、不构成
P2 放行」；54/55 题覆盖面上的 3.69% 这类数字永远不能被引用为 P2 成绩。
→ 正确做法：门挡住时承认「这不是正式分」，诊断产物带诊断标签；
不绕门、不补造回执。

反例：LLM 判读不加门会被一致性检查当场抓住——P0-1 二读门 A 通道
53.3% 未过（`docs/HANDOFF_P01_REJUDGE_2026-10-18.md:35`，终态见 `:3`）
发生什么 → 误拒率判读（LLM 判「拒得对不对」）做二读一致性复算，
A 通道 agreement 8/15=53.3%、κ=0.222 未过门；B 通道因双方同常数
全拒而 κ 未定义，也如实报告。
→ 后果：按回传义务停下报 CC，A 方案回炉、规则升 v3.2 全量重判，
最后由代审终审收口（A 42/118=35.6% 过线）。
→ 正确做法：LLM 判读线必须自带一致性门、分歧样本披露与终审位；
门未过就回炉，不把第一轮读数直接消费。

反例：金标与密钥的隔离边界写进每一次迁移与核查（正面纪律的实况）
（`docs/NOTEBOOK_MIGRATION_2026-10-23.md:36`、`:55`、`:246`）
发生什么 → 跨站迁移 4,675 个文件时，金标只落 700 权限的专用根、
只做「只读计数/哈希」；`llm_ds.env` 只搬不改、600、未打印内容。
→ 后果：迁移报告可以自证「零泄漏面」，评审无需信任只看边界声明
即可复核。
→ 正确做法：任何涉及金标/env 的操作，报告里写清「读了什么元数据、
没读什么正文」；这条边界比便利优先。

## 5. 检查清单

开工前：
- [ ] 本轮工作是否触碰判分链？触碰则确认零 LLM、零网络、零金标正文。
- [ ] 诊断/探针需要读封存批吗？只在隔离副本读，且不写回封存目录。
- [ ] LLM 判读类工作已单独立线（一致性门 + provenance + 终审）？

发车前：
- [ ] score 入口的阶段门回执要求没有 bypass 开关？
- [ ] 判分器源码哈希已进脚本锁（如 `docs/T_P2_SCRIPT_LOCK_2026-10-21.json`）？
- [ ] 金标/env 的路径、权限、是否打印已列入报告边界声明模板？

交付前：
- [ ] 分数只从封存 metrics/report 消费，未重跑未重判？
- [ ] 诊断口径数字没混进正式结论？
- [ ] 评测器状态仍是 pending 族，未替用户/teacher 宣布结论？
- [ ] 泄漏面自查：金标正文、题面、env 值、key 是否零出现在交付物？

## 6. 机器检查

脚本：`scripts/bible_checks/check_zero_llm_scoring.py`（第一批已实现）。

```bash
python3 scripts/bible_checks/check_zero_llm_scoring.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43
```

扫 `src/**/scoring*.py` 与 scoring 目录：① 不得 import 模型客户端
（`openai`/`dashscope`/`requests` 调模型域）；② 判分器源码哈希与
`docs/T_P2_SCRIPT_LOCK_2026-10-21.json` 或同类锁文件比对；③ 金标路径
不得出现在可写路径清单。违规 → fail（findings 带文件与行号）；锁文件
缺失 → error。当前源码 import 面干净，此检查应 pass。

## 7. 模板（score 交付边界声明）

```markdown
> 判分零 LLM；分母固定 <N>（失败/unknown/空候选均不剔题）。
> 本文件只消费已冻结的本地 metrics/report/批旁件，未重跑、未重判、
> 未读金标/题卷/llm.env/逐题 case 正文。
> 评测器状态：pending_user_teacher_decision（程序只发 pending 族）。
> [诊断口径时另加] 本节数字为诊断口径，<原因>，不构成 <正式批> 放行。
```
