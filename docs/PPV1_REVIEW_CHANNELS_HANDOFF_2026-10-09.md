# PPV1_REVIEW_CHANNELS_HANDOFF_2026-10-09 — 评审通道迁移交接（Codex+mimo 流程活状态）

> **用途**：把「评审-回修自动循环」从本窗口迁移到新窗口用。
> 流程**规则**已固化在 `AGENTS.md`「评审-回修自动循环与外部通道」节
> （任何在本仓打开的窗口自动加载，无须搬运）；本文只补**不会随仓库
> 自动过去的活状态**：Codex fork 链头、mimo 边界头与 opencode 服务
> 修法、额度节律、挂账中的评审义务、/tmp 易失件清单。

---

## 1. 流程规则的权威位置（在仓里，自动生效）

| 件 | 位置 | 内容 |
|---|---|---|
| 循环 spec | `AGENTS.md`「评审-回修自动循环与外部通道（2026-10-07）」节 | 范围/停点/轮内四段接力（实施子代理→主会话核对→mimo→Codex fork）/失败重试/自动续轮与急停 |
| 通道 A（mimo） | 同节「通道 A」 | 命令、只读边界、断流续跑、落盘与 provenance 规则 |
| 通道 B（Codex fork） | 同节「通道 B」 | App 内置二进制路径、链式 fork 命令、cwd 纪律、无沙箱配套提示词纪律 |
| 通道 C（备用 tokeasy） | 同节「通道 C」+ `docs/PPV1_REVIEW_PROTOCOL_2026-10-08.md` | 撞额度时的同规格替代，不替代正链最终裁定权 |
| mimo 三触发点 | `AGENTS.md` 上方「仓库红线」节 | 判据评审/出题前抽审/出题后复核；涉金标外发逐次拍板 |
| 先例件 | `docs/mimo_ppv1_chem_review_request_r1..r27.md` + `docs/mimo_ppv1_chem_review_response_r1..r27.md` | 请求/回应命名与头部 provenance 格式 |

## 2. Codex fork 链——当前链头（最关键的单件）

```
01a11e94-5ef4-7442-9e4e-db5ab6280c33
```

- 这是 **S5b 启动批评审**的会话（其后 L01/L02 回修后 resume 过，同 id）；
- 下一轮复审从这里 fork（命令模板见 AGENTS.md 通道 B；**必须在
  `/Volumes/CC/Enzyme_Agent/dependingv43` 下发起**——fork 以发起时
  shell cwd 为工作目录）；
- 输出头部的 `session id:` 行即下一轮 fork 父，**每轮记下来**；
- 验证链头存活：`/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex exec resume 01a11e94-5ef4-7442-9e4e-db5ab6280c33 "<极短提示>"`，
  或直接看 App 会话列表（主评审对话运行期被 App 写锁占用是常态，
  所以才用 fork 链）。

## 3. mimo 通道活状态

- **模型**：`opencode/mimo-v2.6-flash-free`（免费档，固定）；
- **命令形态**（仓库根发起）：
  `opencode run -m opencode/mimo-v2.6-flash-free "$(cat <边界头> <请求md>)"`；
- **边界头**：每轮一个，历史件在 `/tmp/mimo_rN_header.md`（易失；
  最新 `/tmp/mimo_r27_header.md`，含只读声明/无执行权限/禁金标/
  行号漂移警示/冻结口径状态——**新窗口写新轮时按最新版改轮号与
  变更文件清单**，其余骨架照抄）；请求 md 进 `docs/`（入库）；
- **回应落盘**：清终端控制字符后存
  `docs/mimo_ppv1_chem_review_response_rN.md`，头部注明通道与只读
  provenance；运行证据（raw/body/header）归
  `docs/review_evidence/ppv1_rN_mimo_<日期>/`；
- **opencode 服务必须带代理环境跑**（否则免费网关被系统代理拦、
  `DEPTH_ZERO_SELF_SIGNED_CERT` 三连）：服务挂了就重启——
  ```bash
  pkill -f "opencode serve --service"
  env http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 \
    nohup opencode serve --service >/tmp/opencode_serve.log 2>&1 &
  ```
  （会话持久在 DB，重启不丢历史会话。）
- **断流续跑**：`OpenAI Chat stream ended without finish_reason` ⇒
  `opencode session list` 找回会话，`opencode run -s <id> "继续输出完整回应"`。

## 4. 额度节律（两通道）

- **Codex（ChatGPT 账号）**：一轮全量评审约 7–8.5M tokens；额度约
  5 小时一复位（撞线报错信息里带精确恢复时刻）。恢复前选项：定时
  `sleep N; codex exec resume <id>`，或**用户说"额度恢复了"就立即
  resume**；撞额度默认切通道 C（AGENTS.md 通道 C 节），不再干等。
- **mimo**：免费档无额度问题，主要是偶发断流（见上）。

## 5. 交接时点挂账中的评审义务（新窗口接走）

1. **Codex 补审（后置，用户已批延后）**：S5b launch+runtime 批的
   事后复审——从 `01a11e94` fork，输入=交付书+当轮 mimo 回应；
   **时点**：298 正式跑出分之后随下一轮交付一起送（不阻塞跑）；
2. **mimo r27 条款项**：r27 回应中"条件随下轮交付"的采纳核对
   （response 文件在 docs/，先读再决定下一轮请求要不要带上）；
3. **mimo v6→r27 之外的独立线**：`docs/mimo_ppv1_chem_review_request.md`
   （早期主线版）已被 r 系列取代，勿混用；
4. **评审侧文档归宿**：Codex 报告/mimo 回应/证据目录默认留未跟踪，
   用户定期自决入库——新窗口不要擅自批量 add。

## 6. /tmp 易失件清单（本窗口布局；新窗口可按需重建）

| 件 | 用途 | 重建来源 |
|---|---|---|
| `/tmp/codex_*_last.txt / _output.txt` | Codex 每轮输出（含 `session id:` 行） | 撞线后新轮输出重新生成；链头见 §2 |
| `/tmp/mimo_rN_{header,body,raw}.*` | mimo 每轮边界头/回应体/原始流 | header 骨架照抄 r27；body 已落 docs/response |
| `/tmp/cy_ssh.sh` `/tmp/cy_scp.sh` | Chenyu expect 封装（含凭证，不入仓） | 任务书 §4 配方+用户新链接 |
| `/tmp/s5b_code.tar.gz` `/tmp/s5b_chain5.sh` | 298 远端执行件 | 任务书附录 A/B |

## 7. 一句话总结

规则看 `AGENTS.md`（自动加载）；活状态三件套=**Codex 链头
`01a11e94-…`、mimo 边界头照抄 `/tmp/mimo_r27_header.md`、
opencode 服务带代理重启**；挂账义务见 §5，按"互证采信"原则不变。
