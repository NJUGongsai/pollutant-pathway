# R8 mimo 评审运行证据（opencode 免费模型通道）

- 日期：2026-10-07；按 AGENTS.md「评审-回修自动循环」轮内第③步自动送审
  （用户已拍板开 R8）。
- 通道：opencode 内置免费模型 `opencode/mimo-v2.6-flash-free`（opencode
  v2.0.23）；与手机 mimo 应用是否同一实例未证实。
- 评审对象：`docs/mimo_ppv1_chem_review_request.md`（v8，自包含、无金标）。
- 会话：`ses_eeb143e1cffeFDe4prKTG10UCJ`（标题 "mimo ppv1 v8 chem review"）。
- 评审模式：**只读**——模型自述未执行任何测试/探针（读取类工具核对源码/
  测试/请求），执行类声明一律标"待执行验证"。本轮耗时长于 v7（模型对
  R8 修复代码与测试做了逐处读码核对）。
- 运行事件：中途一次 `ECONNRESET` 断流，opencode 侧自动恢复后完整输出；
  续会话（raw_run2）确认回应无遗漏（按请求 §7 不设总评段）。

## 文件与 SHA-256

| 文件 | 内容 | SHA-256 |
| --- | --- | --- |
| `prompt.md` | 发送的完整提示词（边界头 + v8 请求原文） | `35d030617c2f4c66f3f470c812324d5e5a3c539a95a1bb7fc1cf745058cfad5d` |
| `raw_run1_with_recovery.txt` | 主运行原始输出（读码过程 + ECONNRESET + 恢复后完整回应；回应正文从第 325 行起） | `197de03a9196cfae6a397ca5c8bd05af6dd8d40acba1429027036c1cc40c04a2` |
| `raw_run2_continuation_confirm.txt` | 续会话确认收尾完整性的原始输出 | `7cc30d9c6f446b557d24aa63978a386fd22a693f995cd081c75c4a49e6d2393e` |

回应落盘（清理终端控制字符后原文 + 主会话 provenance 头）：
`docs/mimo_ppv1_chem_review_response_r8.md`
（SHA-256 `dc004e603ef9634dc023d833b5485bbda729595fb9b8a9845a6e7c732879cb8e`）。

## 复现方式

```sh
cd /Volumes/CC/Enzyme_Agent/dependingv43
opencode run -m opencode/mimo-v2.6-flash-free --title "mimo ppv1 v8 chem review" "$(cat prompt.md)"
# 断流时续会话（会话 ID 见 opencode session list）
```

免费网关会话非确定性；本目录为本次运行原始存档，不在其内执行写库/覆
输出脚本。

## 结论摘要（详见回应原文）

判据一/二/四/五**同意**；判据三**有条件同意**。8 条条件均落字性质
（判据一 ①(d) 句升格+②同源括注、判据二 ③入口限定、判据三 ④scope
字面/归属对齐[请求文本与代码字面不一致的直接修正，建议优先]+⑤恒入
≠已适用、判据四 ⑥frozen/内容哈希分写、判据五 ⑦None≠通过+⑧异常
承担方写明），无一要求新增化学机制。
