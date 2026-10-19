# Codex 复审请求 — T-G Step C1 回修交付（2026-10-19）

> **【P3-LEDGER-01 账目修正（2026-10-19，提交前）】**：本请求书数字（+781/−65、2212、定向 20）取自追修轮落盘前——追修后实测=4 代码文件 **+1078/−67**、全量 **2215/0/16**、定向 **23**（见交付书 `docs/T_G_C1_IMPL_DELIVERY_2026-10-19.md` 与复审报告冻结事实表）；「与 docs 合计 +985/−148」把非本单的 P0-1 线 docs 4 件计入，提交时已分账。

> 上下文：C 线共底物供给 policy-7 已发货进 chain13/14 批，但 REAUDIT（`docs/C_COSUB_SUPPLY_IMPL_CODEX_REVIEW_2026-10-14_REAUDIT.md`）判「退回」的 2×P1+P2 至今未回修。T-G 任务书（`docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md` §3 Step C1）把该欠账列为第一刀。本单=该回修的交付复审（任务书合约原文：「回修后若 45/35 面发生位移，逐行披露并交 Codex 复审」）。
> 交付构成：工作树未提交改动 4 文件（`s5b_builder.py`/`search.py`/`production.py`/`tests/test_ppv1_s5b_cosub_supply.py`，+781/−65，与 docs 改动合计 +985/−148）；交付报告=实施子代理回报（主窗口已复验：定向 20 测复跑全绿、git diff 构成吻合）。

## 交付内容

1. **P1-BUILD-01**（s5b_builder.py）：供给主份扣除改按选定 `main_idx` 位置扣一份（其余 mapped lhs 组分原序保留），supply/spectator/声明装配同序贯通；保留正控（同结构双份供一份、双水 spectator）。
2. **P1-RUN-01**（search.py+production.py）：记录方程发射载荷随 `write_commit_bundle` 持久化；B3 恢复门=提交前先核验并幂等发射同源 provenance（形状/refs 绑定核+内容冲突门），冲突⇒结构化拒绝（H07 同形 disposition）；四控（正常/B3 未写/写异常/既定冲突）+合法恢复正控。
3. **P2-WILDCARD-01**：**恢复冻结边界**（含具体 dummy 组分如 `[H]*[H]` 的袋整袋 wildcard_blocked）——未收窄。
4. **P3-INPUT-01**：`execution_input_smiles` 键在位含 null/坏形状⇒首消费结构化拒；键不在位=兼容边界。

## 请逐条裁定（P0/P1/P2；总裁定=放行/回修）

- **Q1 实现正确性**：P1-BUILD-01 的 main_idx 位置扣除规则是否贯通三处装配且保正控；P1-RUN-01 的 provenance-first 门是否覆盖四控且幂等。
- **Q2 位移合法性**：对拍位移——unlock_face_replay 45→36 行（drifted 9，全 root=wildcard 袋整袋拦截）、byte_invariance 262+35+1→266+32+0（5 题位移，同 root）；逐行披露在 `reports/ppv1_s5b/t_g_fix_2026-10-19/c1_readback/face_shift_disclosure.json`——位移是否**全部**可归因 P2 冻结边界回修、无其他路径漂移；「35 行口径并轨为 75=35 裸+40 具体 dummy」的重述是否成立。
- **Q3 测试与零翻转**：全量 not-slow 2212/0/16、基线 2202+10 新增=零翻转——可复算性；PC-S4 两断言翻转（`[H]*[H]` supply→wildcard_blocked）是否属 REAUDIT 强制回退。
- **Q4 版本号**：policy-7/supply-1 未升号——「回修对齐冻结契约」定性是否成立，还是属语义变化需升号（交付方无权拍，交你裁）。
- **Q5 边界**：旧版无载荷历史 bundle 未加「缺载荷即拒」（有限回修边界登记）——是否可接受或需追加。

## 纪律（同前，违反=停止）

只读评审+全新临时目录跑只读核算脚本（PYTHONDONTWRITEBYTECODE=1）；不动 src/tests/既有 docs；新增仅限 `docs/review_evidence/t_g_c1_codex_2026-10-19/` 与你的报告 `docs/T_G_C1_CODEX_REVIEW_2026-10-19.md`；不访问金标/题面/封存逐题 run；不 push；不调用外部模型；结论须与程序证据互证；工作树含未提交回修改动（审查对象即该树，HEAD=ff0b534）。
