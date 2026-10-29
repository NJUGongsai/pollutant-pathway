# T-G Step C1 回修交付 — 代 Codex 复审报告(2026-10-19)

> **终判定:放行。P0=0,P1=0,P2=0,P3=2(非阻塞,登记处置)。**
> 通道 provenance:CC 指派 ZCode 主会话**代替 Codex** 执行本复审(请求书
> `docs/T_G_C1_CODEX_REVIEW_REQUEST_2026-10-19.md`);执行=主会话读码级审 +
> 隔离副本子代理复跑 + 主会话独立核算脚本;评审独立性不做背书,结论采信到
> 与程序证据互证为止;正链 Codex 额度恢复后可复核确认。
> **题域标签:以下 454 面/298 题/371 行等数字均为实施验收与探针口径
> (298=RHEA 已见题,chain12 批),非判分成绩、非预注册投影,与 dev 双向不外推。**

## 一、审查对象与冻结事实

| 项目 | 事实 |
|---|---|
| 审查对象 | HEAD `ff0b534` + 工作树未提交回修改动(4 代码文件) |
| 冻结 blob(sha1) | s5b_builder `074a5429`、search `7f0a64c7`、production `58500e7b`、tests `54c2b998`(审查起点与终点复核一致,无并发漂移;完整 sha256 见证据清单) |
| 树内时间线 | search.py/tests 最后写盘 09:59:37/10:00:02 =「追修轮」(恢复门载荷内容兜底 + 3 兜底测)落盘,**晚于请求书取数时点**——请求书数字陈旧由此解释(见 P3-LEDGER-01);本审对象=追修后终态 |
| git numstat 实测 | 4 代码文件 **+1078/−67**(production 33/18、s5b 67/34、search 199/5、tests 779/10);请求书称 +781/−65,不符 |
| 工作树 docs 4 件 | HANDOFF_P01/P0_1_ERR_RATE/V3_DRAFT/TASK_GONGSAI(+204/−83)为 P0-1/判据线内容,**非 C1 交付产物**;请求书「与 docs 合计 +985/−148」将其计入本单构成,口径混乱一并登记 P3-LEDGER-01 |
| 隔离执行 | 副本 `/Volumes/CC/tmp_tg_c1_review_27133a49`(保留);主会话脚本 cwd `/tmp/tg_c1_review_run_23062`;python 3.11.16(depending43)、pytest 9.1.1、`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider` |

## 二、逐条裁定

### Q1 实现正确性 — **通过(P1=0)**

**P1-BUILD-01(main_idx 位置扣除)**:供给循环改为 `index == main_idx` 位置扣除、其余组分原序原样保留,`main_copies` 如实计数——与 REAUDIT「有限回修」条款逐字对应。**三处贯通实证**:池消费(`sub_supplied` 拼接)、spectator(`_cosub_supply_spectators` 参数)、声明装配(`_attach_analog_cosub_supply_fields` 参数)均消费 `analog_cosub_supply` **同一次返回**的 `supply["supply"]`,无第二套份数判据。正控保留:同结构双份恰供一份(新测断言)+ 双水 spectator 存量测未动。**独立对拍**(自证脚本 v2):454 面行中 371 供给行按新旧规则逐行重演扣除,**370 行供给序列逐字节相同,唯一差异行 = tpl-rhea:49530/RXNG_93161cb**(两份同构苯甲酸副本,main_idx=2,多重集相同=仅顺序级,编译结局不变)——交付说明「唯一影响行」声明独立证实,且证明 P1 修复在真实面上零内容级位移。REAUDIT 手性反例(同 CN 相反立体双份+并列取后位)在单元/编译/池三级复现为新增测试,负控(旧错袋反事实 compiled=具体误救)在案。

**P1-RUN-01(B3 恢复门)**:采用 REAUDIT 允许的第二形态——发射载荷随 `write_commit_bundle` 持久化(键仅在位时写,非 C bundle 字节零变化),恢复首消费 `_emit_bundle_record_equation` 五层核验(假设形状/载荷形状/record_id∈refs 绑定/refs 覆盖/判分侧 `_criteria_declaration_sides` **同源判据**内容解析)→ 核验全过才 `put_provenance` 幂等发射 → 再 `submit_event`。**拒绝先于发射**(不带病写入),冲突 `Ppv1EventConflict` 原样上抛拒绝提交;disposition 与既有 H07 分支同形(error/kind/note),`continue` 隔离不中断其余 action 恢复。发射参数 `(str(record_id), run_id or "", dict(payload))` 与正常路径逐参数同源(已对源核验),`put_provenance` 幂等/冲突语义按 content_hash(store.py:970-1002)——同内容重写不误触冲突。四控(正常/B3 未写/写异常/既定冲突)+ 合法恢复正控 + 追修三兜底控(missing/unparseable/unbound/uncovered/hypothesis_invalid 五形态)+「合法载荷不误拒」正控全部在案且断言完整(零事件/零提交/零消费含 hypotheses/provenance 行零条、bundle 字节原样保全、冲突旧行不覆盖)。正常路径顺序不变(bundle→put_provenance→submit),B4/done 路径未触碰。

### Q2 位移合法性 — **通过(位移全部归因 P2 冻结边界回修,无其他路径漂移)**

- **unlock 面 45/35→36/32,drifted 9**:九行逐行在案(`face_shift_disclosure.json` shift_rows),`supply_status` 全为 `wildcard_blocked`、根因全为供给袋含具体 dummy 组分 `[H]*[H]`(模板 tpl-rhea:33573/48078/49809/16359);闭合算术自洽(437 matched+9 drifted+8 skipped=454;45−9=36)。
- **「75=35 裸+40 具体 dummy」重述成立**:本审独立扫描(自证脚本 v1)对 454 面行逐行复算 wildcard_blocked 桶拆分,**精确得 bare 35 + concrete_dummy 40 = 75**;`bare_wildcard_blocked=3`(探针侧 cofactor 恰为 `*` 且 probe 编译行的实现必拦截核)两面均过,口径不冲突(3 ⊂ 35)。
- **byte 面 262+35+1→266+32+0(5 题分类位移)**:4 题 additive→identical + 1 题 fallback_interaction→additive,逐题归因同一根因(wildcard 袋臂 B 供给件消失);closure 全过、drift_total=0;分类内内容变化(fd4e0ba rescued 2→1 等)由 l1 探针 5 处 mismatch 补充披露——三面(unlock/byte/l1)互证同根,无未披露路径。
- **P1 无位移的独立证据**:见 Q1 对拍(370/371 逐字节同、唯一行仅顺序级);byte 面 drift 0 佐证。
- **l1 Stage 0 锚不复现**(chain13 manifest rescued 5 处消失)= 封存 manifest 为回修前实现产物,同根位移的诚实附带披露,非 C1 验收项,处置(全停 Stage 1-4、登记另行重放)恰当。

### Q3 测试与零翻转 — **通过(可复算性成立;请求书数字为追修前旧账)**

隔离副本实测:**定向 23 passed/0 failed/0 skipped**(请求书称 20);**全量 not-slow 2215 passed/0 failed/0 skipped/16 deselected,376s**(请求书称 2212/0/16)。零翻转成立的精确闭合:**基线 2202(HEAD 提交口径)+ 本单新增 13 个测试函数 = 2215**,failed=0,文件内零 skip 标记;请求书「2202+10」的 10 与「定向 20」均为追修轮(+3 兜底测)之前取数,failed=0 的实质结论不受影响。三对拍探针副本复跑输出与交付 JSON **逐字节一致**(sha256 对照在案);unlock 探针 exit 2 = 披露位移下对锚闭合门按设计失败(交付版 all_pass=false 同态,非新缺陷)。**PC-S4 两断言翻转**(`[H]*[H]` 袋 `supply`→`wildcard_blocked`)= REAUDIT P2「恢复冻结边界」强制回退,且同测新增无 dummy 对照袋照常供给断言(证明非全拒替代),翻转合法。

### Q4 版本号 — **裁定:定性成立,policy-7/supply-1 不升号**

理由:①P2 回修是**回到冻结契约**(冻结设计 44-45/105 行本就规定 wildcard 袋本轮不供给、定义另行拍板;收窄才是偏差),升号反而把契约内行为标成新语义;②P1 是契约内缺陷修复(设计书始终要求选定主份保真),非语义变化;③判分侧零改动,消费契约(criteria-v2 §二.1)未动。REAUDIT 自身亦以「恢复冻结边界」而非「新版本」表述处置。
**附带登记义务(P3-DISCLOSE-01)**:chain13/14 已发货批次的 policy-7 池系**偏差实现**所建(含 ≤5 件 wildcard 供给件、49530 供给顺序差),同 tag 两态并存——跨批比较/离线重判一律以**批次内容哈希/manifest** 为身份,不得以版本 tag 等同池内容;l1 Stage 0 锚不复现披露已在案,建议随 C1 提交在交付书补一条「policy-7 偏差窗口」登记。

### Q5 边界 — **裁定:可接受,无需追加**

「旧版无载荷历史 bundle 未加缺载荷即拒」实为**写入侧兼容边界**(公开 writer 不强制新参数,旧调用方形态不破坏),而恢复侧已有兜底:refs 非空而载荷缺/坏/不符 ⇒ `emission_missing` 等五形态同形拒(有专项反例测试,首写经公开接口构造)——即「先提交后留悬空链」在恢复入口被关死,安全方向 fail-closed。非 C bundle(无 refs 无载荷)零调用零变化由既有 S3A 族恢复测+全量覆盖。历史 C 线 bundle 若真被恢复将拒绝提交=保全而非放行,sealed 批只读不触发恢复,无实际暴露面。写入侧强制会破坏合法旧调用方且无安全增益,不要求追加。

## 三、P3(非阻塞,登记处置)

| 分级/ID | 事实与处置 |
|---|---|
| **P3-LEDGER-01** | 请求书/交付账数字与 git 及实测不符:①4 文件 +781/−65 vs 实测 **+1078/−67**(`-w` 口径同);②全量 2212/定向 20 vs 实测 **2215/23**;③「与 docs 合计」把非本单的 P0-1 线 docs 4 件(+204/−83)计入交付构成。根因一致=请求书数字取自追修轮(09:59-10:00 落盘)之前,「主窗口已复验 git diff 构成吻合」在线号层面不成立。按 REAUDIT 先例(以 git 为准、笔误不升阻塞)判 P3;**处置:提交前更新请求书/交付书数字为追修后实测,提交时 C1 代码 4 件与非本单 docs 4 件分账** |
| **P3-DISCLOSE-01** | Q4 附带:policy-7 版本 tag 偏差窗口(chain13/14 批池=偏差实现产物)登记义务,见 Q4 处置 |

## 四、纪律遵守与证据

只读评审:原仓新增仅本目录与本报告;子代理 find 实证副本运行期原仓写入仅 `rerun/`;未访问金标/题面/封存逐题 run 内容(manual_review 未打开;chain12 manifest 仅按探针同口径取底物字段,输出零底物原文外带);未 push、未调用外部模型、未动 src/tests/既有 docs/AGENTS.md。

证据索引(`docs/review_evidence/t_g_c1_codex_2026-10-19/`):
- `REVIEW_MANIFEST.json`(冻结哈希、命令、环境、合规声明);
- 自证脚本+输出:`dupcn_wildcard_scan.py/.json`(75=35+40、同 CN 袋扫描、语料库 15 个立体异构重复份模板=P1 未来面受益清单)、`p1_rule_diff_scan.py/.json`(371 行新旧规则对拍);
- `rerun/`:三探针复跑 JSON(与交付版 sha256 全等,`sha256sums.txt` 对照)、定向/全量 pytest 摘要、README(副本路径/版本/命令/起止时间/探针 REPO 常量适配披露)。

## 五、收口

**放行 C1 回修交付。** P1 清零、P2 清零,REAUDIT 三判(2×P1+P2)与 P3-INPUT-01 全部闭合且有正反控;两处对拍位移全部归因 P2 冻结边界回修并逐行披露,符合任务书 §3-C1「位移逐行披露并交复审」合约。放行附带两条 P3 登记(账目更新+偏差窗口披露),随 C1 提交一并处置;版本 tag 不升号(本报告 Q4 为代审判定,正链 Codex 恢复后可复核确认)。本报告与证据按惯例留未跟踪,由 CC 定期自决。
