# S3a-r3 权威专项独立复核（2026-10-08）

实际 HEAD `41d0cd55f3def050a62325f00235cf22da302d2e`；父 `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`。范围固定 R2 主审§4.1 S3A-02 最低验收、§5两个登记边界；不增加 S3b、科学机制/性能、外部 SQL 并发破坏门。全部 depending43 隔离源（包含 vendor/pyproject/worker），新 `/private/tmp`，`-B`+禁字节码；所有合成，无网络/provider/外模；不访问题面、金标、封存 run 或旧 v4 仓，主仓零修改。

**专项结论：S3A-02 原主要反例已关闭，但“必需预约集合”仍残余 P1。本轮不得把“已列出的每行正确”当作“必需集合完整”。S3A-01 既关四类身份与 H07/H08 正控继续保持。**

## 1. 已完成的旧输入分段复核

| 捕获 | 当前实际 | 边界 |
| --- | --- | --- |
| R2 原27 | 24坏权威均 SearchIntegrityError 拒、恢复/正确writer重放零写；2合法恢复/重放保持；raw首提交拒零写1 | 按原12×2输入完整捕获，不凭旧observed早停推断 |
| R2 原120 segmented | 111坏拒零写，9合法 | 原81被接受+2先写event后拒均消失；四run/parent/context/hypothesis write/direct/B3拒且artifact保全；8个H07/H08保全 |
| done 2 | 同event返回真实已完成event；有效异parent在独立普通store已证可首提，本action明确SearchContractError冲突，零写 | 两案原输入保持，仅捕获异常适配；当前拒绝kind `event_identity_not_frozen_to_action` |
| 附随正常首提3 | projection/plan非法产品ref、plan非法status同源正常首提均拒零写 | 不以只读函数名字当认证；实际对照与坏历史附随消费均拒 |
| 崩溃/并发5 | B1–B4四子进程实际硬退出、旧预约/attempt续跑；B2不默发/scripted网络0；B3同output只一次；B4幂等结算；两个独立进程ready/GO barrier仅一认领胜者 | 6 worker进程实际执行，不是线程测试 |
| defer行级守卫+合法13 | 9坏行 defer 均 SearchIntegrityError 零写；合法未执行defer释放、共享alternative、非expand空attempt非事件outcome、expand failedattempt合法done及再次幂等4 | 保留合法共享行由另一action创建；alternative used1/总action used2 |

`assert_r3_capture.py`仅对已捕获输出做正确合同断言，exit0。旧引用集合中的行单位/状态/scope、attempt状态/hyp/task、commit归属/attempt以及附随首提判据，确有实际进展。本专项不再重开这些具体已修案例。

旧observed行为纪律：`probe_original.py`仅合法B3正控完整输出，随后write异run在当前正确拒绝处早停，其后段未运行；分段120单独完整执行。旧`assert_observed.py`在首坏state_charge恢复拒绝处按设计失败，其化学后段未执行。R2 `assert_current_capture.py`在其“81接受+2late写”旧断言失败，后面的TOCTOU部分未运行。都不是当前回归失败数字。

夹具精度错误：done捕获adapter最后误期待 SearchIdentityConflict，实际明确SearchContractError；两案完整输入输出在末断言之前已保存。只读正确断言核其实际kind/零写/foreign普通首提合法，不重跑。原脚本、adapter diff、stdout/stderr、exit全部保留。

## 2. 保留的同合同 P1：必要引用集合可被缩短

原R2§4.1最低验收明确“必要预约/完整冻结引用”“B3先验全部必要引用”和done消费“必要结算证明”；首轮S3A-02也要求内容与引用完整性。这是原组剩余，不要求新签名/全历史真实性或任何S3b功能。

现 `_verify_action_references` search.py:1683–1698 仅要求预约引用非空、expand attempt引用非空，再于:1771开始逐个核**仍列在集合内的行**；没有核此action按现有claim规则必须包含的limit集合。`claim_action` :944–948恒创建总action预约；expand在 `_create_attempt` :1037起创建 alternatives/attempt 必需预约并并入引用。三行的完整引用集合本已有持久创建证据，不需要额外机制。

探针保留其余两条合法ref，只从 `search_actions.budget_reservation_ref` 删除某一必需limit项：

- 只删ref，原对应预约row留在库：首次complete/B3仍写done/commit，遗漏行留reserved，不做必要结算；done复用也接受。
- 删ref并删该row：首次complete/B4/B3/done四口/B1/defer仍普通成功。B3在event0库执行后变event1/commit1，artifact原字节保全；删总action项时预算显示used0/remaining10，且恢复说 `consumed_same_output_attempt`。
- 已done后同删，总action used0仍被恢复报告为 `done_commit_verified`；claim/complete/submit已完成复用也正常成功。

完整63案=9合法正控+54坏案（9口：firstcomplete/B4/B1/B3/done恢复/认领/完成/提交/defer × 3必要limit × 仅删ref或ref+row）。**54均正常接受、没有完整性错误**。数字是同规则入口分布，不能说54个漏洞。

实际公共链补证：`one_action_budget_chain_probe.py`配置总action上限1，两个不同hypothesis、两个不同event。合法正控第一次完成后第二claim正确 SearchBudgetExhausted（events1/commit1/used1）。坏案仅在第一次合法claim后移除总额度ref+row，第一次成功complete而used0；第二个action继而成功claim/submit/complete，最终 **events2/commits2/总used1，max1**。整个链零外部网络、不依赖竞态、不用未经验证化学结构。

证据入口：`necessary_reference_cases/`、`necessary_reference_observations.json`及`one_action_chain_cases/upper1_remove_total_ref_and_row/input_output.json`。每案输入、原合法14表、mutation后/消费后14表和预算完整保存。

最低修复：同源验证不仅核行内容，还核按action kind和持久claim/attempt证据应有的必要limit集合/各适用关联，零缺项/不重复错项。expand的total/alternatives/attempt三必要项及共享alternative按真实创建语义处理；reopen/其他动作资源只核真实适用证明，**不要给合法cache_hit retrieve强加并未消费的资源**。公共first complete/B4/defer/B1/B3前置/done四口共用；坏集合消费前结构化拒、零新event/commit/consume、artifact保全，不猜补/不重建预约洗坏。保留合法非expand空attempt/非事件outcome、failedattempt、主体共享、各预算0和旧已经修复控制。

## 3. 登记边界与附随同源

`verify_event_attachment_content` store.py:1988复用版本门、`_product_state_refs`、`_check_projection_scope`、`_check_expansion_plan`，现search在正常重放之前调用；原历史projection/plan坏产品ref/非法status均已执行级拒，零写，不再自比较洗坏记录。它认证现成协议语义，不证明来源或化学机制。

TOCTOU仍是预核验public replay事务退出、complete新写事务之间未持锁；按R2§5裁定的顺序单消费/不可变公共writer模型边界继续登记。本轮未重复主动并发坏SQL实验，不以同源函数新增调用声称跨并发外部改库安全，不新列P1。

未归因事件defer保守拒保持，可接受过拒边界，不当一定已执行证明，不升级组。

本专项不裁定预算块和请求生命周期（另两专项独立执行）、全量PPV1/G01或mimo化学事实；不给这些数字背书。所有合成工程case数不外推dev/298科学性能。
