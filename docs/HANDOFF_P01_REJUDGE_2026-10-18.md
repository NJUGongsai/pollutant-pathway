# HANDOFF — P0-1 判读回炉后半程 + goal 剩余（2026-10-18 午，交新窗口零上下文接手）

> 写给：下一个窗口。当前窗口按 CC 指令收手（上下文过长）。
> 读法：§1 活状态 → §2 剩余步骤（按序） → §3 机器参数（防再踩坑） → §5 goal 大盘。

## 1. 一句话状态

P0-1 误拒率判读**回炉重判已完成 221/252**（A 通道 155/155 全、B 通道 66/97）；**B 批 3（最后 31 件）未派**——新窗口第一件事就是派它。之后二读门 → 能力负锚 → 重出表 → Codex 复审 → 师姐件打包。

## 2. 活状态（精确到批，2026-10-18 12:00 止）

### 回炉重判（细化规则版，`judgement_mimo_v2_*` 系列；本轮产物全在 `reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/`）

| 通道 | 进度 | 三值分布 | 备注 |
|---|---|---|---|
| A（analog·no_alignment） | **155/155 ✅**（batch1-5） | 109 拒 / 45 过 / 1 存疑 | 回炉读数 err_rate_raw = 45/154 = **29.2%** Wilson95[22.6%, 36.8%]（uncertain 从 21 塌到 1——是否过度自信由二读门检验） |
| B（corpus·截断拒） | **66/97 ✅**（batch1-2 各 33 件） | **66 件全 reject_correct（0 过）** | 细化规则（Biii 强制子查）下维持零误拒形态 |
| B 批 3 | ❌**未派** | — | `sampled_B.json[66:97]` 31 件 |

### 相关既有产物（勿动）

- 第一轮判读（被一致性门拦下、已降级）：`judgement_mimo_A_{pilot,batch2..5}.json` + `judgement_mimo_B_{batch1..3}.json`（252 件）；
- 二读门第一轮（**未过**）：`judgement_second_read_gptsol.json`（30 件：A 15 件 80%/κ0.505、B 15 件 0%/κ0 系统性相反——根源=B 通道 Biii 排除条款两位判读者执行不一致，故回炉）；
- 意外一致性样本：`judgement_mimo_v2_A_batch1_recheck.json`（同 34 件 mimo 跨会话自一致 **94%**，≥90% 线）；
- P1-1 返工件：`judgement_mimo_A_case_rework.json`（a-075c0a3e10c5426f 维持 pass_expected、锚已修正——回炉模板里的校准样例）；
- 结果表（已降级）：`docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`（含二读失败记录+回炉条款）；
- 抽样/材料包/汇总：`sampled_{A,B}.json`、`material_packs_{A,B}.json`、`frame_{A,B}.json`、`p0_1_output.json`（seed=20261016）；
- 二读样本与能力样本：`second_read_sample.json`（A15+B15 已抽）、`capability_sample.json`（15 件编译通过件已抽，**材料包未生成**）。

## 3. 剩余步骤（按序；全零费用 mimo 免费线+Codex）

1. **派 B 回炉批 3**（31 件）：模板 `reports/.../mimo_rejudge_B_template.md`（占位符 `CASE_IDS_PLACEHOLDER`）——sed 换清单（`sampled_B.json[66:97]` 带 `b-` 前缀）+ 输出文件名改 `judgement_mimo_v2_B_batch3.json` + 「回炉批 3」；跑法 `opencode run -m opencode/mimo-v2.6-flash-free "$(cat 提示词)"`（仓库根发起；断流→`opencode session list` 找会话→`opencode run -m opencode/mimo-v2.6-flash-free -s <id> "继续"`）。
2. **二读门复算**（30 件=second_read_sample.json）：第二判读者=通道 C `opencode run -m tokeasy/gpt-6-sol`，**用回炉细化规则版**（从 A/B 模板改写出二读版：禁读任何 judgement 文件+同规则+30 件清单）→ 输出 `judgement_second_read2_gptsol.json` → 算 agreement+κ（**门=各通道 ≥90% 且 κ≥0.6**；门过→结果表恢复可消费；不过→按设计稿再回炉或升级 CC 裁定）。
3. **能力负锚**（15 件编译通过件盲判）：先给 `capability_sample.json` 15 件生成材料包（仿 `p0_1_materialize.py` 材料包段：底物+语料 donor/product/templates+规则引用；这 15 件是编译**通过**件——盲判提示词用 A 通道规则但**不告知**它们通过）；期望多数 pass_expected；>20% 误判 reject ⇒ 判读流程不采率（设计稿 §五负锚）。
4. **重出表**：更新 `docs/P0_1_ERR_RATE_RESULT_2026-10-18.md`（回炉终读数+门结果+条件读法+能力负锚记录）。
5. **Codex 复审**：fork 链父=`01a14ba1-d84b-7343-b7c8-72d0c782dc16`（判读审会话，ChatGPT.app 二进制 `--dangerously-bypass-approvals-and-sandbox`，仓库 cwd）；请求格式仿 `docs/P0_1_JUDGEMENT_CODEX_REVIEW_REQUEST_2026-10-18.md`（五问制式+纪律头）。
6. **师姐件打包**（挂 CC）：A 45 件+B（批 3 出数后定）pass_expected 件+材料包+锚——供师姐逐件确认（设计稿 §四：确认后才是最终分子）。

## 4. 机器参数（防再踩坑——本窗口踩过的都在这）

- **提示词生成必须用模板占位符**（`CASE_IDS_PLACEHOLDER`）+ sed 换清单——手拼 id 串匹配**两次翻车**（替换串不在模板里=静默无操作→整批重复判读前一批；事故已止损+文件已改名存证）。
- **mimo 断流续跑必须带 `-m`**：漏了会用 opencode 默认模型（GLM）续跑走偏。
- **验收三件套**：行数=预期、case_id 集合==清单（带 `a-`/`b-` 前缀、材料包 B 面 case_id 是 `c-`/`b-` 双射注意）、pass_expected 全带 mapping_anchor。
- **新派单规矩（CC 2026-10-18 拍板）**：执行类子代理**不走 opencode 免费通道**（OCAgent 停用）→ 用 ZCode 本身子代理；**mimo 例外**（化学评审/判读继续免费线）。Codex（通道 B fork 链）与 tokeasy（通道 C）审核线不变。
- 免费网关夜间慢+断流：白天较稳；批均 10-40 分钟。

## 5. goal 大盘（新窗口全景）

| Goal | 状态 | 下一件 |
|---|---|---|
| G1 P0-1 判读 | 回炉 221/252 | §3 步骤 1-6 |
| G2 证据卡 v2 | **设计已冻结**（通道 C 两轮+正链终认双确认；任务书 `docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md` v2 修订版） | **实施单**（SMARTS 质子化容忍先行+冻结字段面+确定性锚；实施派 ZCode 本身子代理——新规矩） |
| G3 审核循环 | T-F 三轮✅放行；v2 设计三轮✅放行；判读审✅（2×P1 抓实→回炉中） | fork 链 01a14ba1 |
| G4 T-H 修复批 | blocked（等师姐 V3 冻结+误拒率定稿） | — |
| 挂 CC | 师姐确认/发车费用（no-cap）/金标红线 | — |

已完成大件（全部已推 origin/v4.3，HEAD `4eede03..7c262b2`）：T-F 位次继承三轮循环放行（`0facf85`/`f222096`）、V3 草案 v2+mimo 场景1（`b21fff4`）、chain13/chain14 交付包+任务七回执+老师任务书（`52ae0e8`..`04f2482`）、归因探针、判读审降级（`7c262b2`）。

## 6. 回传义务（新窗口）

- 每完成 §3 一步：更新本文件状态+主 TODO（`docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md`）；
- 二读门/能力负锚**任一未过**：停下汇报 CC（附分歧样本），不自行处置；
- 全部完成：出最终两通道误拒率表（judger+师姐双门后）交 CC 消费 T-G 立项线。
