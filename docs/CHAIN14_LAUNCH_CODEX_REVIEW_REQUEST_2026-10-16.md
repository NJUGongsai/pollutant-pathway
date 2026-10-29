# Codex 代审请求 — chain14 发车物+修正案整体放行审核（2026-10-16，代 CC）

> 代审依据：CC 2026-10-16 指令「有需要我审核的都发给 Codex 让他替我审核」。
> 你（Codex）的结论**作为 CC 的审核裁定**执行：放行=进入 HPC 发车流水；
> 不放行=按你的意见回修。红线类（金标外发/费用异常）仍由人拍板，不适用代审。
> 对象：HEAD `b4b89dc` 之上的**未提交工作树**（发车物实施+mimo 修正案增量）。
> 题域标签：**298=RHEA 通用酶学/已见题**。

## 一、被审改动全景（两轮增量）

**轮 1：发车物实施**（子代理，交付书 `docs/CHAIN14_LAUNCH_IMPL_DELIVERY_2026-10-15.md` §一至§六）：

| 件 | 文件 | 声明 |
|---|---|---|
| 证据卡批级开关 | s5b_orchestrator.py(+71)/s5b_worker.py(+45)/runflow.py(+64/-8) | 发车参数冻结 orchestration.json+单一验证源+批报告披露；worker 同判据核对；_call_real_fetch 消费+resume 换臂拒；**A 臂 off 载荷与实施前四字段形状逐字节相等**（断言） |
| 传输重试 | real_model.py(+132/-9)/model_protocol.py(+7/-3) | _send_and_settle/_transport_retry；首败 transport_error→重试 1 次；两连败现行失败语义；timeout/forbidden_permanent 不重试；每题 3 请求语义不变；反馈轮计数排除 retry_of |
| chain14 发车族 | scripts/hpc/ 新 4 文件（260 行） | sbatch_{build,run,score} ARM 参数化+chain14_run_wrapper.py（EVIDENCE_CARD_BY_ARM={a:False,b:True}）+no-cap/approve 门沿 chain13 |

实施方自报 4 条偏差（交付书 §五）：①发车参数 None⇒冻结 True（缺席即拒会翻 20 处既有调用；对冲=两臂脚本显式传值）；②worker 侧副本缺席（手动路径）回退 on 而非拒（沿 no-cap 先例）；③重试族={transport_error, empty_response}（timeout 双计费排除）；④gate_max_calls 维持 4470。

**轮 2：mimo 修正案增量**（主会话直改，交付书 §七，全部披露）：

| 项 | 位置 | 声明 |
|---|---|---|
| SMARTS 口径修×3 | candidate_evidence.py:63/65/66 | 羧酸 OH 排除/胺类补酰胺排除（同 tertiary 先例）——RDKit 实测分子核过 |
| descriptor 升版 | :47 | candidate-evidence-descr-1→-2（schema 不变仍 candidate-evidence-2） |
| 提示词四句补丁 | real_model.py 证据注记段 | 记账非机制/role unknown 语义/系数 unknown 语义/电荷按所绘算+unknown≠弃权理由（并入既有行）；一处去引号合规修正（T2-T8 检测器） |
| T1 基线换钉 | tests/test_controlled_vocab_ci.py | 哈希→fe9eaf77…、字节→6123（注释留链条） |
| 新增正负控×2 | tests/test_ppv1_s5b_candidate_evidence.py | 酰胺≠胺/羧酸 OH≠羟（n_hits 断言） |

## 二、测试与回归账

| 项 | 值 |
|---|---|
| 发车物新测 | 15 件（开关正负控/字节兼容/重试 6 件/发车物冒烟）全绿 |
| mimo 增量新测 | 2 件正负控全绿；受影响三文件 53 passed |
| 全量 not-slow | 实施方 2173/0/16（=2158+15）；**主会话独立复跑在飞**（含增量，预期 2175；结果以你自跑/复跑为准） |
| 判分/池/检索/排序 | 零触碰（两轮均声明，git 范围可核） |

## 三、请代审的问题（P1 优先）

1. **A 臂字节兼容**：off 路径载荷是否与证据卡实施前逐字节一致（含 JSON
   键序）？开关消费是否覆盖全部 decide 入口（含反馈轮/resume；换臂拒语义）？
2. **重试语义**：重试族选择（transport_error/empty_response 进，timeout/
   forbidden 排除）是否合理？计费诚实性（每 HTTP 尝试=issued，每题 3 请求
   上限语义）有无漏洞？两连败后失败语义与 chain13 可比性？
3. **实施方 4 条偏差**：逐条裁定可接受/需改（尤其①None⇒True 缺省与②
   worker 副本回退 on——与「两臂显式传值+冻结后改参即拒」对冲是否足够）。
4. **mimo 增量**：三处 SMARTS 修正的化学口径（你的 RDKit 自验）；四句
   补丁的纪律合规（T2-T8 过=词表不教内部载荷词）；版本承载链（schema
   candidate-evidence-2+descr-2+提示词 fe9eaf77+T1 钉）是否闭合无静默漂移。
5. **发车族脚本**：ARM 参数化/no-cap+approve 门/wrapper 的
   EVIDENCE_CARD_BY_ARM 是否按预注册（A 臂 false/B 臂 true、两臂同构）？
6. **发车放行判定**（总问题）：以上全过 ⇒ **放行 HPC 发车**（部署 v43c14
   →双批根 chain14{a,b}→build→approve+no-cap→run→score 双口径）；有任何
   P0/P1 ⇒ 列明回修项。

## 四、回复格式

逐条 1–6：结论+证据（文件:行号/探针）；最后「总体裁定」一行：**放行发车/
不放行（附回修清单）**。沿你上两轮口径：不认证科学收益、不追加性能门、
不要求跑真实模型；发现金标泄漏类标 P0。

## 五、纪律（无沙箱全权配套）

只允许：读仓库核对、跑受控探针（tmp 隔离、禁 pyc/cache）、新增你的审核
报告与证据目录（docs/review_evidence/ 下）。禁止：改 src/tests/既有 docs/
AGENTS.md、访问金标/题面/封存逐题 run、git push/commit、调用外部模型。
