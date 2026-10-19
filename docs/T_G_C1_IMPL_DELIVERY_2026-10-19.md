# T-G Step C1 交付书（含追修，2026-10-19）

> 交付=REAUDIT 2×P1+P2+P3 回修 + B3 载荷校验追修（复审额度耗尽前抓到的追加 P1）；Codex 复审（代审：ZCode 主会话代执行，正链可复核）**终判定放行**（P0/P1/P2=0，P3×2 登记处置见下）。复审报告 `docs/T_G_C1_CODEX_REVIEW_2026-10-19.md`（留未跟踪按惯例）。
> 题域标签：全部数字为实施验收与探针口径（298=RHEA 已见题，chain12 批），非判分成绩、非预注册投影。

## 交付构成（追修后实测，git numstat 为准）

| 文件 | +/− |
|---|---|
| `src/pathway_v43/pollutant/s5b_builder.py` | +67/−34 |
| `src/pathway_v43/pollutant/search.py` | +199/−5 |
| `src/pathway_v43/pollutant/production.py` | +33/−18 |
| `tests/test_ppv1_s5b_cosub_supply.py` | +779/−10 |
| **合计** | **+1078/−67** |

（请求书原记 +781/−65/2212/20 为追修轮落盘前取数，已按 P3-LEDGER-01 修正；本单与非 C1 的 P0-1 线 docs 4 件分账提交。）

## 内容

1. **P1-BUILD-01**：供给主份扣除按选定 `main_idx` 位置扣一份，supply/spectator/声明装配同源贯通；独立对拍 371 供给行 370 逐字节相同、唯一差异行（tpl-rhea:49530）仅顺序级零结局变化。
2. **P1-RUN-01**：记录方程发射载荷随 `write_commit_bundle` 持久化；B3 恢复门五层核验（假设形状/载荷形状/record_id∈refs/refs 覆盖/**判分侧同源判据**内容解析）→ 拒绝先于发射 → 幂等发射 → 提交；**追修**：载荷缺失/损坏/悬空 refs/hypothesis_dict 坏形五形态结构化拒（H07 同形 disposition，反例先复现后修复）。
3. **P2-WILDCARD-01**：恢复冻结边界（含具体 dummy 组分袋整袋 wildcard_blocked）。
4. **P3-INPUT-01**：`execution_input_smiles` 键在位含 null/坏形状⇒首消费结构化拒。

## 验收（追修后实测）

- 定向 23 passed（存量 20+追修 3）；全量 not-slow **2215/0/16**（基线 2202+新增 13=零翻转）。
- 对拍位移（全 root=P2 回修，逐行披露 `reports/ppv1_s5b/t_g_fix_2026-10-19/c1_readback/face_shift_disclosure.json`）：unlock 45→36 行（drifted 9=wildcard 袋）、byte 262+35+1→266+32+0（5 题）、l1 Stage 0 附带披露（263→266/28/4/0，同根）。
- 「75=35 裸+40 具体 dummy」口径经复审独立扫描证实。

## P3 登记处置（复审附带）

1. **P3-LEDGER-01**：请求书/交付账数字已修正为追修后实测（上文）；分账提交。
2. **P3-DISCLOSE-01（policy-7 偏差窗口）**：chain13/14 已发货批次的 policy-7 池系偏差实现所建（含 ≤5 件 wildcard 供给件、49530 供给顺序差），同 tag 两态并存——**跨批比较/离线重判一律以批次内容哈希/manifest 为身份，不得以版本 tag 等同池内容**；版本 tag 不升号（Q4 裁定：回修=回到冻结契约，非新语义；正链 Codex 恢复后可复核）。

## 下一步

C2 设计轮（元素适配/中心锚定——预注册级，先死因细分探针+暴露面前置数字，无数字不发货）。
