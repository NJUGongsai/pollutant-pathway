# pollutant_pathway_v1 S0–S2 第七轮回修交付书(R7)

- 日期:2026-10-07
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md`
  §3 五组 P1(R6-01～R6-05)+ §4 两项 P2 + §6/§8 有限范围
  (六份必读文档全部读取;R6 审核方证据目录只读,复跑走
  reproduce.py --allow-head-change 隔离复制,未在其内写任何
  SQLite/覆盖任何日志)
- 回修基线:6d9020130a481866ce2f3b79933907a33d8cfc9e(=R6 审核锁定
  HEAD);工作区原有未提交的 AGENTS.md 修改与 R5/R6 评审未跟踪文件
  原样保留,未回退未改动未纳入本次提交
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待 review + mimo 第七轮)
- 状态:五组 P1 全部处置(实现+回归+探针翻转,对照见 §5.3);
  全部 ppv1 测试 **508 通过**(451 存量 + 57 新增,0 skip);
  新增回归在基线 6d90201 **红 33/57**(26 真实反例翻转 + 7 个
  仅因 v7 新披露字段/新表缺失红,核心语义基线已绿)+ 24 基线绿
  正控制;G01 全量 **1119 passed/16 deselected**;mimo v7 评审请求
  已更新待用户转交
- 探针纪律:R6 审核方 12 份探针入口经其 reproduce.py 在 v7 隔离
  复跑全部 exit 0(五组 P1 逐案翻转、旧控制保持);assert_observed.py
  按设计在翻转点失败(钉住 R6 修前缺口,非修后期望)

## 0. 一句话结论

R6-01～R6-05 五组 P1 全部按"统一消费入口的验证契约"收口:补全
许可按严格结构身份注册(数值配平不再授未登记多原子共底物
full/R6)、原始 CX 输入按 RDKit 真实类边界逐项词法 + 供体诊断四
个原始字符串入口同源守卫、上下文派生先验父对象且覆盖签名必须
对应实际记录的评估行、首提复用既存行立即共用重放同源校验、
事件出现集合获得独立完整性表;契约族升 v7(无迁移);五组残余
反例翻转、全部既有正控保持;PPV1/G01 全绿;mimo v7 请求已备。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| (本次单提交) | R7 底座:六模块 v7(profile/chemstate/audit/path_context/store + 事件出现 links 表)+ 5 个存量测试文件版本串机械升位(-6→-7,8 处)+ 1 处被证伪披露断言语义修正(r6_chem violations 循环)+ 3 个新增 r7 测试文件(57 用例)+ R7 交付文档 + mimo v7 请求 + 实施证据目录 |

源码 diff(相对 6d90201,仅 src/ppv1):4 文件(audit/chemstate/
path_context/store)+ profile 版本族升位;测试 diff:5 文件修改 +
3 新文件。触碰面仅 `src/pathway_v43/pollutant/` 与 ppv1 测试
(+docs)。**legacy 路径零触碰**(services/atom_tool.py 冻结执行器
未改;storage/pathway_store.py 未改;G01 全量回归为证)。

## 2. 五组 P1 逐项处置表

### R6-01 补全许可按严格结构身份注册

| 项 | 内容 |
|---|---|
| 位置 | [audit.py:258-266](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:258)(COMPLETION_LICENSE/COMPLETION_LICENSED_IDENTITIES 常量);[audit.py:967-985](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:967)(_center_evidence_binding 内许可判定 + completion_license_unregistered_identity violation);[audit.py:988-997](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:988)(detail 披露 completion_license/scope/unlicensed_uncovered_identities) |
| 前行为 | 未覆盖参与物只贡献元素总数;两侧与 Δ 正负部分数值相等即授 product_coverage=full、中心 verified、R6 expand。真实 AtomTool C→CCCO(依次新增 C/C/O,不载入任何共底物初始图)的同一证明用于 C+CC=O / C+C1CO1 / C+C=CO → CCCO:三个 C2H4O 异构体(乙醛 C=O/环氧环键/乙烯醇 C=C)数值都恰好补足 Δ,全 verified/full/R6 |
| 后行为 | 补全规则 `atom_delta_stoichiometric_completion` 新增许可边界 `composition_only_hydrogen_equivalents`(登记严格结构身份 `[H][H]` 与 `[H] |^1:0|`——H2 对 2[H] 的 composition-only 作用域说明,不新增电子/自由基轴;不按名称/整类免审);未登记身份的未覆盖参与物**即使数值全配平** ⇒ violation(kind=completion_license_unregistered_identity)⇒ partial、中心 unknown、retain;detail 机器披露 completion_license/作用域说明/未登记身份清单。正控保持:乙醇氧化/乙醛氢化的 H2 补全、2[H] 原子氢当量、比例缩放、真实断裂分列/合并仍 full/verified/expand |
| 依据 | 数值配平只证明组成贡献,不证明初始分子图的键变化/连接贡献已核实(R6 §3 R6-01:三异构体同 Δ 数值不可区分);许可按"结构贡献完全由组成决定"论证登记(氢当量),其余身份须另提交可确定复算的初始图贡献证据后扩登记(不要求 S3 full_template/机制库,不要求共产物完整走 AtomTool) |
| 测试 | r7_chem 9 例(三异构体反例/披露/氢当量三正控/身份-不-类名边界);r6_chem 既有正控 12 例全绿 |

### R6-02 原始 CX 注册与解析统一(两处入口)

| 项 | 内容 |
|---|---|
| 位置 | [chemstate.py:257-466](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py:257)(_guard_input_cx_classes 按真实类边界逐项词法重写 + _cx_scan_field/_cx_scan_int_list/_cx_scan_atom_prop_item/_cx_scan_sgd_item/_cx_scan_sg_item + 结构化错误带违规项原文);[audit.py:2546-2576](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py:2546)(check_edit_against_donor 四原始字段入口守卫,kind=raw_input_cx_class_unregistered) |
| 前行为 | **A**:工厂/strict 按空格拆块、只查首头——`C[C@@H](N)C(=O)O \|atomProp:0.note.hello,r\|`、`SgD:…::::,r`、`Sg:n:…:::,r`、`atomProp:…,Ln:1`、`atomProp:…,w:1.0` 整块放行,RDKit 解析时静默丢 r 后与裸串同 state_id/as_written。**B**:donor checker 直接 MolFromSmiles 解析 current 与 mapped product(plain/target 走 strict_identity_of 已有守卫但仅 strict 轴)——干净乙醇→乙醛执行仅在 current 或 mapped 接口加 `\|r\|`,诊断 True/True、公共 audit→R6;指定手性底物远端编辑同样成立 |
| 后行为 | **A**:按 RDKit CXSmiles 解析器(Release_2026_03_6 源码取证:parse_it 主分派循环 + parse_atom_props/parse_data_sgroup/parse_polymer_sgroup 的字段分隔符)的**真实类边界**逐项词法:扩展段是项序列,项间 ','/空格分隔(逐字符跳过,含写出器 Sg 尾部 ':' 字段终止符);各登记类解析器自耗字段,字段内逗号/空格是内容(atomProp 值到 ':'/'|'/',' 止、SgD/Sg 冒号字段到 ':' 止——DAT 值内逗号受保护、`$…$` 标签到 '$' 止);未登记首头(含并列位置)⇒ ChemicalStateError(unregistered_cx_class,带违规项原文/段上下文/登记头)。**同修 P2**:RDKit 写出器生成的 `atomProp:0.note.hello world`、`SgD:…:hello world::::`、`$foo bar;$` 不再因空格拆块误拒。**B**:current/mapped/plain/target 四个原始字段在解析前统一过同一 _guard_input_cx_classes(与工厂/strict 同源);未登记项 ⇒ AuditContractError(kind=raw_input_cx_class_unregistered,带字段名,kind/detail 从守卫错误同源转译);审计复算链(_rerun_proof_record 重跑 proof_record)同守卫拒绝 |
| 依据 | R6 §3 R6-02 + RDBook CXSMILES(解析器对未知首字符逐字符静默跳过);词法边界与 C++ 实现逐条对照取证(逗号=项边界/字段内逗号=内容/尾随字段终止符),不是猜测;不解释新 CX 类、不改冻结执行器、未知默认拒绝(fail-closed) |
| 测试 | r7_chem 26 例(并列未知 7 反例/DAT 逗号+含空格 16 正控/裸未知 3 既有控制/donor 四入口+复算链+手性 6+2 正控);r6_chem 21 例既有 CX 控制全绿(裸 `\|r\|`/`\|Ln:1\|` 拒、SgD 逗号/SRU/增强组/自由基保持) |

### R6-03 derive 先验父对象 + 签名↔评估行对应

| 项 | 内容 |
|---|---|
| 位置 | [path_context.py:2320-2327](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:2320)(derive_child_context 入口调 validate_context_object);[path_context.py:1040-1049](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1040)(评估行携带 requirement_signature);[path_context.py:1487-1503](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/path_context.py:1487)(_validate_phase_history_snapshot 增 signature_row_correspondence 双向集合一致) |
| 前行为 | 合法 p0 必要 pH 6–8 事实缺失为 unknown;转 p1 当前有氧满足,旧 pH 快照使审核 retain。只将父快照 per_requirement=[]、coverage 清空、has_gate=False 而**保留真实 pH 签名**:直接 audit 拒(内容身份);但 public derive_child_context(parent) 不传新事实/要求/转换即重算合法子 ID——旧 pH 不再参与门禁(has_gate=False 使该边退出合取,签名在使孤儿检查放行),audit verified/R6;child→dict→from_dict 后再审也 R6 |
| 后行为 | ① derive 入口先调 validate_context_object(与 from_dict/audit 同源:版本门+快照一致性+内容身份)——篡改父 ⇒ ConditionContractError,不再产生"合法"子对象;② 每条评估行携带 requirement_signature(canonical JSON),快照 covered_requirement_signatures 集合必须**等于**逐条行签名集合(双向)——保留签名删行 ⇒ context_snapshot_inconsistent(signature_row_correspondence,机器披露"签名无评估行");③ 诚实方向:连签名一起删的自洽空快照(完全重造自洽历史,验收明示不要求防住)⇒ 旧 pH 变孤儿绑定,unknown/retain |
| 依据 | R6 §3 R6-03:签名只属累积要求集合不再充分,须对应**实际记录的评估**;derive/from_dict/audit 三入口共用同源契约;不用当前事实重评旧边,不认证用户事实真实性 |
| 测试 | r7_conditions 10 例(未篡改正控/直接 audit 拒/derive 拒/from_dict 拒/专用错误码/诚实孤儿方向/合法 conflict 往返/满足+正常转换+孙上下文/凭空签名/摘要与旗标篡改);r5/r6_conditions 既有控制全绿 |

### R6-04 首提复用既存行立即共用重放同源校验

| 项 | 内容 |
|---|---|
| 位置 | [store.py:1593-1607](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1593)(首提分支对 reuse_refs 调 _verify_stored_state_rows + _verify_stored_appearances,与重放同一复算源) |
| 前行为 | 首提只核本次事务 states(R3-09);不在本次载荷中的 derived_ref 只查**存在性**(SELECT 1)。先 public put 合法数据,再仅在合成 SQLite 损坏单字段(产物 CN 改 CCN/schema 未来版本/载荷内 state_id 与行键不符/appearance source_refs 改而 hash 不动),然后 states=[] 首提:created=True 写事件/投影/计划;紧接无输入重放才 LedgerCorrupt(state_row/state_schema/state_inner_id/appearance_hash_corrupt) |
| 后行为 | 首提对 reuse_refs(derived_refs − 本次事务提供)立即执行与重放同一 _verify_stored_state_rows(载荷内 ID=行键、schema 门、CN/立体/同位素事实结构重推导)与 _verify_stored_appearances(出现内容 hash 复算):四例损坏 ⇒ **首提即 Ppv1LedgerCorrupt、零新增事件/投影/计划**(校验区执行,事务回滚),不以"重放能发现"代替;合法全量/部分先存、显式状态、正常首提/重放保持(R5-05/R5-06 既有验证不动) |
| 依据 | R6 §3 R6-04:首次消费即闭合;认可既有 hypothesis 四项校验修复,不新增迁移,不自动补账 |
| 测试 | r7_storage 6 例(四损坏参数化/出现损坏/valid+partial 两正控);r6_storage 既有先存/歧义控制全绿 |

### R6-05 事件出现集合独立完整性表

| 项 | 内容 |
|---|---|
| 位置 | [store.py:219-225](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:219)(新表 event_appearance_links(event_id, state_id, appearance_hash) PRIMARY KEY 三元组);[store.py:1805-1811](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1805)(首提写入完整集合);[store.py:1297-1335](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1297)(_verify_event_appearance_links:payload 清单集合 == links 行集合,双向);[store.py:1502-1505](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1502)(重放接线);counts() 增 event_appearance_links |
| 前行为 | 重放只核清单的 state_id 集合 == derived_refs(清单是事件 payload 的一部分,而 event_semantics_hash 不含清单):合法首提 [底物, prod-A(CC=O/refs A), prod-B(O=CC/refs B)] 同 SID 不同 hash、manifest 三项;删清单 A 项留 B(或连实际 A 行也删)后,B 仍覆盖 product SID ⇒ 无输入重放 created=False 静默通过。只删 A 行留原清单(⇒ entry_missing)是有区分力的既有控制 |
| 后行为 | 首提把本事件**完整 (state_id, appearance_hash) 集合**同源双写进独立表 event_appearance_links;重放双向核验:删清单 A 留 B / 连行删 / 只删 links 行 ⇒ event_appearance_manifest_link_corrupt(Ppv1LedgerCorrupt,不静默 created=False,不补账);完整性依据独立于事件 payload(payload 单点编辑不再能洗掉某次出现);**保持**:原清单只删 A 行 ⇒ entry_missing(既有控制);同图多来源各自保留(不合并)、排序幂等(links/manifest 集合语义)、正常无输入重放 created=False;不要求抵抗重造整本账本(三处一致重写=外科手术式自造,超出验收) |
| 依据 | R6 §3 R6-05:完整出现集合须有独立可复核依据;event_semantics_hash 不含清单 ⇒ 单点持久不够 |
| 测试 | r7_storage 6 例(多来源+links 正控/删清单 A/删清单+行/删行留清单既有控制/只删 links 行/排序幂等);r6_storage 既有 R5-05 控制全绿 |

## 3. §4 两项 P2 文档同步

| 项 | 处置 |
|---|---|
| §4-1 登记类含空格过拒 | **同修**(与 R6-02A 词法重写一并):新词法按字段真分隔符读内容,`atomProp:0.note.hello world`、`SgD:…:hello world::::`、`$foo bar;$` 不再误拒(r7_chem 正控 3 例,基线红即此族);无空格与 DATA 内逗号正控保持 |
| §4-2 DATA 前提文本不一致 | **已修正**:R6 交付书 §3 曾声称"SgD 剥离前提已写入 mimo v6 请求判据一",实际 v6 请求只写了"内容不查/不按逗号拆整段"。本轮:(a) mimo **v7** 请求判据一第 2 条明确落字——"本仓把 DATA SGroup(SgD)视为纯出现/注记元数据,生成身份前分子级剥离;**化学事实不得只编码进将被视为注记的 DAT**(需要进身份的化学事实走结构串本身或登记保留类 Sg/SRU)";(b) 本交付书如实登记 R6 交付书该句为**夸大**(声明已落字而未落字),属文档修正非代码缺陷;(c) 不把 SRU/所有 SGroup 一概当注释(保留类语义不变) |
| (附)两条表述边界 | 已写入 mimo v7 请求判据五评审点 (d):原始 `r` 标记被拒绝**不**解释为"已证实验精确消旋";裸指定 SMILES **不**称实验纯品(身份层只声明表示事实) |
| §4-3 具体签名负控 | invented signature 独立回归已入库(r7_conditions `test_r6_03_invented_signature_still_rejected`) |

## 4. 实施约束遵守

只做 S0–S2;未实施 S3–S5(runner/搜索/队列/终点/评测零触碰);
未改冻结 legacy/G2/AtomTool(services/atom_tool.py、storage/
pathway_store.py 零 diff,G01 为证);未访问金标/题面/封存逐题
run;未调用任何外部模型(mimo 请求只是 md 文档,由用户转交);
所有新反例用合成夹具和公共消费链;SQL 只在新合成库准备损坏并
记录零写入;语义变动按既有 version 规范版本化(ppv1-*-7)并
明确待审;未发布 profile 拒旧版(v6 载荷按未知版本既有门拒绝,
无兼容迁移);允许诚实 unknown/partial(复杂共底物 partial/
retain、孤儿 unknown/retain、歧义零写入拒绝均保留),未全面
reject 破坏正控。

## 5. 测试证据与命令

~~~bash
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43

# 全量 ppv1(19 文件)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py tests/test_ppv1_s2.py \
  tests/test_ppv1_rework.py tests/test_ppv1_r2_conditions.py \
  tests/test_ppv1_r2_storage.py tests/test_ppv1_r2_chem.py \
  tests/test_ppv1_r4_conditions.py tests/test_ppv1_r4_storage.py \
  tests/test_ppv1_r4_chem.py tests/test_ppv1_r5_chem.py \
  tests/test_ppv1_r5_conditions.py tests/test_ppv1_r5_storage.py \
  tests/test_ppv1_r6_chem.py tests/test_ppv1_r6_conditions.py \
  tests/test_ppv1_r6_storage.py tests/test_ppv1_r7_chem.py \
  tests/test_ppv1_r7_conditions.py tests/test_ppv1_r7_storage.py
# => 508 passed, 0 skipped(451 存量 + 57 新增;日志 pytest_full_output.txt)

# G01 legacy 回归(全量 not slow)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  -m "not slow" tests/
# => 1119 passed, 16 deselected(611 legacy + 508 ppv1;0 failed;日志 g01_full_run.txt)

# R6 审核方探针在 v7 复跑(复制源码+探针到新临时目录,不在永久目录执行)
PYTHONDONTWRITEBYTECODE=1 $PY -B \
  $REPO/docs/review_evidence/ppv1_r6_codex_2026-10-07/reproduce.py \
  --repo $REPO --out /private/tmp/ppv1_r7_repro --allow-head-change --skip-pytest
# => 12 份探针入口全部 exit 0;assert_observed.py 按设计失败于首个
#    钉住的 R6 缺口断言(它钉修前观察,非修后期望)
# 复跑证据存 docs/review_evidence/ppv1_r7_impl_2026-10-07/
~~~

### 5.1 红验证(先红后绿)

- 基线:`git worktree add --detach <tmp> 6d90201`,复制 3 个 r7
  测试文件(r7_chem 对 v7 新常量 COMPLETION_LICENSE 做字面量替换,
  仅影响 import 不影响断言语义,R6 同口径),运行 ⇒
  **33 failed / 24 passed**(57 用例);
- **26 个红为复审反例的行为翻转**(断言形如 verified==unknown、
  created==LedgerCorrupt、DID NOT RAISE):
  - R6-01:复杂共底物 3(verified/full/expand → unknown/partial/retain);
  - R6-02A:登记头后并列未知项 6(接受 → 拒绝)+ 含空格登记内容
    3(误拒 → 放行,P2 假拒翻转);
  - R6-02B:donor 四原始入口 4 + audit 复算链 1 + 指定手性底物 1
    (True/True/R6 → AuditContractError);
  - R6-03:derive 洗白 1(产出子对象 → 拒)+ 签名↔行专用断言 1;
  - R6-04:首提既存行损坏 4(created=True → 首提 LedgerCorrupt);
  - R6-05:清单删项 2(created=False → link_corrupt);
- **7 个红是正控/披露语义基线已绿、仅因 v7 新披露字段或新表缺失**
  (KeyError: completion_license/unlicensed_uncovered_identities/
  requirement_signature;sqlite no-table: event_appearance_links):
  其核心语义断言(verified/full/expand、unknown/retain、manifest
  三项)在基线 6d90201 已通过;这 7 个是"披露/完整性新增"测试,
  非缺陷翻转;
- **24 个基线通过项全部为正控制或基线已拒形状**(合法先存首提/
  正常重放/多来源清单/删行留清单 entry_missing/from_dict id 未换
  拒/凭空签名拒/合法历史往返/裸未知 CX 拒/登记内容 13 例);
- v7(当前工作树)⇒ **57/57 全绿**;worktree 已清理。

### 5.2 修改的既有测试与理由

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_profile/s2/r2_chem/r2_conditions/r4_chem 版本断言(8 处) | -6 → -7 | 契约族升 v7(机械) |
| test_ppv1_r6_chem `test_r5_01_completion_rule_registered_and_disclosed` 的 violations 循环 | "每条 violation 带数值"改为分形:数值类(completion_surplus/deficit/coefficient_binding_mismatch)带 declared_total/required;许可类(completion_license_unregistered_identity)带 identities/completion_license | v6 断言覆盖数值类 violation 形状;v7 新增许可类 violation 的披露形状不同(身份清单而非数值),原循环会把许可类误判为缺数值;原控制意图(数值类带数值)保留并加许可类同级别披露断言 |
| test_ppv1_r4_chem 1 处、test_ppv1_r2_chem 2 处、test_ppv1_s2 2 处、test_ppv1_r2_conditions 2 处字面量 | -6 → -7 | 同版本族机械升位(donor-diagnostic/admission/pool-order/context/hypothesis) |

### 5.3 复审探针前后对照(关键行)

| 探针行 | v6(6d90201,R6 复审记录) | v7(本轮回跑) |
| --- | --- | --- |
| admission unmapped_organic_completion_{CC=O,C1CO1,C=CO} | verified/full/expand | unknown/partial_unchecked_transformation/retain_conditional |
| admission genuine_bound/genuine_hydrogenation/unmapped_radical_completion | verified/full/expand | verified/full/expand(保持) |
| cx 登记头后并列 r/Ln/w | accepted(与裸串同 id) | rejected(unregistered_cx_class,item 原文) |
| cx 写出器含空格登记内容 | 误报未登记(P2) | accepted(同 id) |
| cx donor current/mapped/plain/target 加 \|r\| | current/mapped True/True/R6;plain/target strict=None | AuditContractError(raw_input_cx_class_unregistered,带字段名) |
| conditions derive_launders_empty_evaluation_with_existing_signature | 产出子对象、after R6 expand | ConditionContractError(context_snapshot_inconsistent/signature_row_correspondence) |
| storage existing_state_first_{cn,inner_id,schema} 首提 | created=True(重放才 corrupt) | 首提 Ppv1LedgerCorrupt(state_row/state_inner_id/state_schema_corrupt)、零写入 |
| storage existing_appearance_bad_hash_first 首提 | created=True | 首提 appearance_hash_corrupt、零写入 |
| storage multi_occurrence remove_manifest_A_only / remove_manifest_and_row_A | created=False(静默) | Ppv1LedgerCorrupt(event_appearance_manifest_link_corrupt) |
| storage multi_occurrence remove_row_A_only | entry_missing 拒 | entry_missing 拒(保持) |
| storage existing_state_first_valid / multi_occurrence normal | created=True / 重放 created=False | 同(保持) |

## 6. schema/语义版本与兼容策略

| 契约 | v6 → v7 | 兼容声明 |
|---|---|---|
| profile/chemstate/hypothesis/event/store/context/dependency/ provenance/substrate_profile/audit/admission_policy/donor_diagnostic/pool_audit/pool_order/input_preview/condition_assessment | -6 → -7 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无迁移;v6 文件按未知版本拒绝(既有门) |
| gate_mapper | -3(不动) | 本轮未触碰 |
| run identity | v43-identity-2(不动) | 未触碰 run_identity.py |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

语义变化要点(v7):补全规则新增许可边界(数值配平不再授未登记
多原子共底物 full);原始 CX 输入守卫按真实类边界逐项词法(并列
未知项拒、登记内容含空格放行)+ 供体诊断四原始入口同源守卫;
条件评估行携带 requirement_signature,快照签名↔评估行双向对应,
派生先验父对象;首提复用既存行共用重放校验;存储新增
event_appearance_links 独立完整性表(表结构变更随 store-7 拒旧库)。

legacy_v43:零改动承诺继续成立——全部改动在 pollutant/ 包与
ppv1 测试(+docs);冻结执行器 services/atom_tool.py 未改;
storage/pathway_store.py 未改;G01 全量回归为证。

## 7. 剩余未知与边界(不宣称冻结)

1. 化学判据 v7 **未冻结**:mimo v7 评审请求已更新(§8),待用户
   转交;冻结以 review + mimo 回应与程序证据互证为准。
2. 契约 v7 未冻结;S3 入口 fail-closed 未解除(runner 未触碰);
   不实施搜索/队列/终点/评测。
3. **补全许可边界待审**:登记集当前只有氢当量([H][H]/[H]);
   O2/H2O/CO2 等是否可按"结构贡献完全由组成决定"的论证扩登记,
   留给 mimo v7 与下一轮 review 表态(扩登记须可机器判定判据,
   不按名称);未登记身份 partial 是诚实降级,不是化学不可能声明。
4. **输入侧词法登记表是类级白名单**:按 RDKit Release_2026_03_6
   解析器源码取证逐项实现;RDKit 新版本解析行为变化须重登记;
   未知 CX 类默认拒绝(不猜测解析)。
5. **R6-03 的诚实边界**:防住"现存签名+删评估行"的公开派生/恢复
   洗白与 id 未换篡改;完全重算 id 的自洽空快照走孤儿 unknown
   (诚实方向);不要求防完全重造自洽历史(验收明示)。
6. **R6-05 的完整性边界**:payload 清单与 links 表双写互证;三处
   (清单/links/出现行)一致重写的外科手术式自造超出本轮验收
   ("不要求抵抗重造整本账本")。
7. **R6-02 的范围**:四个原始入口闭合;`o:1`(无组号 OR)等
   边缘形态仍按未登记拒绝(与 v6 一致,保守);`a!:1` 形态基线
   起即 RDKit 不可解析(拒绝路径不同但同为拒绝)。
8. **S3 排期项(不冒充已实现)**:完整供体变换模板 checker
   (full_template scope)独立注册;执行流接 center_evidence;
   local_delta/edge_kind/scoring_key;互变/质子化等价类;被拒
   共同产物的展开计划消费。
9. 已知缺口(登记保留):增强组联合映射范围(unsupported);平面
   手性等非四面体构型比较(unsupported+公开);条件单位不换算
   (入口契约);matrix 同义/包含须注册;fidelity 的 radical 保真轴;
   cip_label_change_is_not_config_change 就地标注(mimo 建议,
   未实现);manifest 歧义显式引用参数。
10. 科学验收整体 pending(S5);508 项工程测试不构成任何路径
    科学性能声明;合成计量闭合不证明机制/生物可行性/酶选择性
    (探针与测试全部如实标注来源;自洽虚拟记录只证明输入集重算
    自洽,不证明历史执行)。

## 8. mimo v7 化学评审请求

已更新 `docs/mimo_ppv1_chem_review_request.md` 为 v7 文本(判据一
输入词法按真实类边界+全部原始 CX 入口清单+DAT 剥离适配器前提
明示;判据三补全许可 scope 及"数值配平≠结构贡献已核实"+登记
判据请求;判据四签名↔评估行双向对应+派生先验父对象;判据五
四原始入口同源守卫+镜像终态语义保持+消旋/纯品表述边界)。自
包含、规则级、无金标;**由用户转交**,回复原文落盘 docs/;
不自行外发。

## 9. 与原规格的冲突清单

无新增实质冲突。五处"规格未逐字规定、按 R6 复审验收收紧/具体化":
- §8 中心证据补全规则新增**许可边界**(R6-01 验收;规格只要求
  "可核验证据",未定许可 scope——氢当量登记判据留 mimo v7 表态);
- §5.1 身份键入口的输入词法具体化为真实 CX 类边界逐项检查
  (R6-02A 验收;词法依据为 RDKit 解析器源码取证,非规格条款);
- §7.1 供体诊断四个原始字段入口接线同源守卫(R6-02B 验收;
  规格无原始串入口清单条款);
- §6 快照一致性新增签名↔评估行对应与派生先验父对象(R6-03
  验收;规格无显式条款);
- §5.3/§9.2 事件持久格式新增 event_appearance_links 独立完整性
  表(R6-05 验收;表结构变更随 store-7 拒旧库,无迁移)。
