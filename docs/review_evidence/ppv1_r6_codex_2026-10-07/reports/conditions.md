# PPV1 R6 条件/快照/循环分轴独立复审

日期 2026-10-07；repo `/Volumes/CC/Enzyme_Agent/dependingv43`；锁定 HEAD `6d9020130a481866ce2f3b79933907a33d8cfc9e`。源码及原 docs 只读；已读 AGENTS、R6 delivery、mimo R6 全文、R5 Codex 审核。全部执行使用合成结构/条件/来源和新 `/private/tmp`，`python -B`、`PYTHONDONTWRITEBYTECODE=1`；未读 gold/题面/封存 run/真实资产，未调用模型。未重复全量测试。

**结论：R5-03、R5-04 原反例和循环分轴 P2 已修；但派生子上下文可给损坏父对象重新生成身份，配合“已存在签名不对应实际评估行”的漏校验，让历史必要未知消失并进入 R6。此一项 P1 阻塞 S3。** 不撤销直接 audit/from_dict 的身份门修复。

## 证据及重跑

- `r5_replay/probe.py/results.json`：R5 新 7 案例，6 个完整结果、1 个预期快照结构化拒绝；拒绝后后续顶层案例继续。
- `r4_replay/probe.py/results.json`：旧 19 案例，10 个完整结果、9 个预期冻结/构造/版本/内容身份拒绝；内部旧 R3 分段还捕获 4 处已修拒绝。
- 旧 7 案例中快照篡改函数在第一条拒绝处停止，旧 19 的孤儿函数在“删快照保 ID”处停止；**未声称这些内部后半段通过**。新 `probe.py/results.json` 的 10 个分开案例补足 summary/flag × from_dict/直接 audit、合法往返、具体签名成员拒绝及残余，`assert_observed.py` 核实实际输出。
- 新探针只复用已归档 R5 脚本的合成夹具初始化；不运行其主体。中心证据来自真实 AtomTool 乙醇 C–O single→double 的真实诊断记录；H2 仅闭合数值账，不证明机制/路径科学性能。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python -B /private/tmp/ppv1_r6_conditions_6d90201/r5_replay/probe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python -B /private/tmp/ppv1_r6_conditions_6d90201/r4_replay/probe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src /Users/cc/miniconda3/envs/depending43/bin/python -B /private/tmp/ppv1_r6_conditions_6d90201/probe.py
/Users/cc/miniconda3/envs/depending43/bin/python -B /private/tmp/ppv1_r6_conditions_6d90201/assert_observed.py
```

## 已修与正负控制

| 核查 | 独立实际结果 |
| --- | --- |
| 非物种 absent | oxygen aerobic、matrix soil 同词 absent：conflict/violated/defer；温度 25/C absent：unknown/retain；NADH 物种 absent 保持 conflict |
| 单位 | 来源温度空单位 unknown/retain；C、°C 和无量纲 pH 正常；显式 K unknown |
| 旧快照矛盾 | 仅改 summary=compatible 或 has_gate=False：from_dict 和直接 audit 均拒绝 context_snapshot_inconsistent；事实变更保 ID 直接 audit 拒 context_content_identity_mismatch |
| 合法历史 | 冲突历史合法往返同 ID/同 payload，audit defer；合法历史满足仍 expand；同 phase 跨 scenario 原反例仍 expand |
| 签名子集 | 凭空签名拒绝 signature_not_in_requirements，与 mimo 条件⑤的当前行为一致 |
| 循环分轴 P2 | initial supported/reaction contradicted：启动无未知、关系未支持；initial contradicted/regeneration supported：启动未知、关系无污染；双支持与同轴恢复正例正确 |
| 更早控制 | 普通冻结修改、外来绑定、malformed requirements、缺/未知版本结构化拒绝保持；排序幂等/调用方原字典隔离及 matrix unknown 保持 |

关系轴“任一被反驳则关系不支持”的保守门已登记，当前只影响 S2 诊断披露；不要求环自动 reject/defer，不要求本轮实现 S3 调度或数值否定/单位换算。

## 唯一残余 [P1] 子上下文派生未验父身份，已有要求签名可掩盖被删掉的必要评估

准确源码锚点：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:2250`、`:2272`：derive_child_context 入口不调用父对象的身份/快照校验，直接继承内容。
- 同文件 `:2361`：从被改父内容计算新的合法 child.context_id。
- 同文件 `:1408`、`:1420`：必要键/旗标只从现存 per_requirement 派生；`:1443` 只验证覆盖签名属于累积要求，未证明对应评估行实际存在。
- 同文件 `:929`：签名成员存在就承认历史覆盖；`:1220` 排除 has_gate=False 的快照；`:1230` 凭签名让旧必要要求不成为孤儿。
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:410`：audit 确实调用直接对象校验，但在重新派生的子对象上两道现有校验都通过。

合成公开链：p0/s 旧必要 pH 6–8 有来源、未给 pH 事实，正常是 unknown；显式转 p1/s，当前有氧必要条件满足。合法 derive 得到旧 pH unknown 快照，audit retain。随后只对父的普通 phase_history 字段做以下改动，保留 pH 的原具体签名：

```python
snap = c.phase_history[0]
snap['per_requirement'] = []
snap['requirement_coverage'] = {key: [] for key in snap['requirement_coverage']}
snap['has_gate_requirements'] = False
# snap.environment_fit 仍 unknown；covered_requirement_signatures 仍有 pH

audit_hypothesis(..., context=c)       # 正确拒绝：原 context_id 与内容不符
c2 = derive_child_context(c)          # 公开 API；不传新事实/要求/转场
audit_hypothesis(..., context=c2)      # 实际 verified/R6
```

预期：已被直接 audit 拒绝的父对象不能由派生入口静默认证成新合法子对象；且一个 essential 的“已覆盖签名”不能没有相应记录评估行。应在派生入口拒绝损坏父，快照签名/必要评估对应关系同源校验；合法旧未知必须保留 unknown。

实际：直接审计父报 `context_content_identity_mismatch`，但 public derive 重算新 ID；c2 的历史快照“无门禁/无评估行”，签名却仍声明覆盖现存 pH 要求，现有校验接受。候选 `essential_keys=['oxygen_regime']`，旧 pH 从 coverage 消失；condition verified，admission expand/R6。c2.to_dict→PathContext.from_dict 再 audit 也 R6。完整结果键 `derive_launders_empty_evaluation_with_existing_signature`；未改历史的 `genuine_unknown_historical_requirement_retained` 正对照仍 retain。

最小验收：派生与恢复/审核共用父输入契约；快照的具体要求覆盖必须对应其记录评估，不能只证明要求在累积集合中。保留合法 scope 空但历史 unknown 的单向判定、正常阶段转换和所有已修控制。**不要求以当前事实重评旧边，不认证用户事实真实性，不讨论攻击者完整重造自洽历史；本例是公开 API 接受已经可检测为损坏的父对象并漏掉仍存在的必要要求。** 新 child ID/input_hash 随内容变化，不能误称同 hash 漏项。

## mimo 采信边界

mimo 对 absent 三分、原 summary/flag 拒绝、身份重算与循环轴原控制的判断得到独立确认。其条件⑤“凭空签名拒绝”当前行为正确，正式回归可补；但签名子集仅证明要求存在，不能证明评估存在。本残余使用的是合法现存签名，所以不被条件⑤覆盖。mimo 整体同意不能代替此实际公开链核查。未引入 S3 或无限边角要求。
