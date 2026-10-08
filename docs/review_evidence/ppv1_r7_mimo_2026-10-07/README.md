# R7 mimo 评审运行证据（opencode 免费模型通道）

- 日期：2026-10-07；用户外出时授权主会话（ZCode）代为转交。
- 通道：opencode 内置免费模型 `opencode/mimo-v2.6-flash-free`
  （opencode v2.0.23，无认证集成，`opencode models` 列表确认）。
  用户确认该即其所指 mimo-2.6-flash；与手机 mimo 应用是否同一实例未证实。
- 评审对象：`docs/mimo_ppv1_chem_review_request.md`（v7，自包含、无金标）。
- 会话：`ses_eeb722c54ffe4HM0j4CAKsnhU0`（标题 "mimo ppv1 v7 chem review"）。
- 评审模式：**只读**——模型用读取类工具核对源码/文档（其自述另用过一次
  `wc -l`），无测试/探针执行权限；全部执行类声明在其回应中标注
  "待执行验证"，回应明示不以交付自报数字背书。
  其中 PPV1 508 / G01 1119 已由主会话本机独立复跑证实（R7 交付核对）。

## 文件与 SHA-256

| 文件 | 内容 | SHA-256 |
| --- | --- | --- |
| `prompt.md` | 发送的完整提示词（边界说明头 + v7 请求原文） | `8b381155b42d8259aa5b37a89968fc30024848192f526ebdc5ce728a4401b545` |
| `raw_run1_aborted.txt` | 首轮运行原始输出：模型读码核对过程 + 免费网关断流（`OpenAI Chat stream ended without finish_reason`，exit 1） | `b41b1f5643670ac27aa35ebea1f1a519241a2f9b545ee19b812b25e859553dd6` |
| `raw_run2_final.txt` | 续会话后的完整回应原始输出（exit 0） | `6a2d06fede6fc6dc42c0e8bcac0d892cad288bd522a104288f0767f0e14a1900` |

回应落盘（清理终端控制字符后原文）：`docs/mimo_ppv1_chem_review_response_r7.md`
（SHA-256 `04d7beac8c618e72e2f2442da4bfd14002b91f4eb3f7af6a8a150d4d482be3fc`，
含主会话 provenance 头 + mimo 回应正文）。

## 复现方式

```sh
# 组装提示词（头 + 请求原文）后从仓库根目录运行：
cd /Volumes/CC/Enzyme_Agent/dependingv43
opencode run -m opencode/mimo-v2.6-flash-free --title "mimo ppv1 v7 chem review" "$(cat prompt.md)"
# 网关断流时续会话（会话 ID 见 opencode session list）：
opencode run -m opencode/mimo-v2.6-flash-free -s <session-id> "继续输出完整回应"
```

注意：免费网关会话不可确定性复现（模型行为非确定）；本目录为本次运行的
原始存档。不在此目录内执行会写库/覆盖输出的脚本。

## 结论摘要（详见回应原文）

判据二/四/五同意；判据一/三有条件同意（条件 C1～C6）；附 8 项
"待执行验证"清单。C1 为本轮读码新发现（`ChemicalState.from_dict`
恢复路径不跑输入守卫，可达性窄、按读码不可达 verified/R6，待执行验证）。
