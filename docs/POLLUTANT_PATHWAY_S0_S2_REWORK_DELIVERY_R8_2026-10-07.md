# pollutant_pathway_v1 S0–S2 第八轮回修交付书(R8)

- 日期:2026-10-07
- 回修依据:`docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R7_2026-10-07.md`
  §4 两项 P1(R7-01/R7-02)+ §7 有限范围 + §8 R8 提示词(五份
  必读文档全部读取;R7 审核方证据目录只读,探针复制到新临时
  目录复跑,未在其内写任何 SQLite/覆盖任何日志)
- 回修基线:858dd94c7c6c8fc387940242403d67b6b36b5313(=R7 交付
  提交);工作区原有未提交的 AGENTS.md 两章节(2026-10-07「返工
  教训与实施/审核约定」与「评审-回修自动循环与外部通道」)按主
  会话既定默认随本轮入仓(内容未改写);R5–R7 评审侧未跟踪文件
  原样保留、不入库
- 回修范围:**仅 S0–S2 底座回修**;S3 入口继续 fail-closed(未解除);
  契约与化学判据**不宣称冻结**(待 review + mimo 第八轮)
- 状态:两项 P1 全部处置(实现+回归+公共探针翻转,对照见 §5.3);
  全部 ppv1 测试 **536 通过**(508 存量 + 28 新增,0 skip);
  新增回归在基线 858dd94 **红 14/28**(全部 14 红为两项 P1 反例
  行为翻转)+ 14 基线绿正控制;G01 按 R7 复审 §2 新口径为**安全
  隔离工程回归**(隔离源码副本、不含 evaluation/金标/题面,逐项
  报告实际数字与缺席依赖,见 §5);mimo v8 评审请求已更新待用户
  转交
- 探针纪律:R7 审核方化学/存储公共链探针复制到新临时目录复跑
  (chem 55 条 + 补全 3 条;storage 15 案全);`storage_assert_
  observed.py` 与 `assert_chemical_observed.py` 按设计在翻转点
  失败(它们钉住 R7 修前缺口,非修后期望)

## 0. 一句话结论

R7 两项 P1 按"首次消费共用同源验证"收口:状态恢复
(ChemicalState.from_dict)与 audit 直接 states 对象在首次授信前
共用与公共 writer 同源的纯状态验证(raw 登记守卫 + raw→strict
身份一致 + 规范身份/结构事实重推导 + CN-only 专用契约——不只补
from_dict 留 dataclass 绕路、不静默清洗信息再授 full);首提对
supplied SID 的既存同 (SID,hash) 出现行的复用校验统一到收集阶段
(_collect_state_writes,首提/重放共用),实际复用的坏 appearance
立即 LedgerCorrupt 零新增;契约族升 v8(无迁移);两项公共反例在
858dd94 先红、修后翻转,全部既有正控保持;PPV1 全绿;G01 安全
隔离数字如实;mimo v8 请求已备。

## 1. 提交与 diff

| commit | 内容 |
|---|---|
| (本次单提交) | R8 底座:4 个源码文件(chemstate validate_state_object + from_dict 接线、audit states 入口接线、store _collect_state_writes 同 hash 出现校验、profile 版本族升位)+ 6 个存量测试文件机械升位(9 处 -7→-8)+ 1 处 r7_conditions P2 修正(参数顺序 + 基线说明更正)+ 2 个新增 r8 测试文件(28 用例)+ R8 交付文档 + mimo v8 请求 + 实施证据目录 + AGENTS.md 流程章节随本轮入仓 |

源码 diff(相对 858dd94,仅 src/ppv1):4 文件(profile/chemstate/
audit/store)。测试 diff:6 文件机械升位 + 1 处语义修正 +
2 新文件。触碰面仅 `src/pathway_v43/pollutant/` 与 ppv1 测试
(+docs+AGENTS.md)。**legacy 路径零触碰**(services/atom_tool.py
冻结执行器未改;storage/pathway_store.py 未改;G01 安全隔离
回归为证)。

## 2. 入口矩阵(实施先列,共用验证源)

**R7-01:ChemicalState 的全部消费入口**

| # | 入口 | 消费事实 | v7 校验 | v8 |
|---|---|---|---|---|
| 1 | build_chemical_state(chemstate) | 原始结构串 | 输入 CX 守卫+解析+派生 | 不变 |
| 2 | strict_identity_of(chemstate) | 原始结构串 | 输入 CX 守卫+解析 | 不变 |
| 3 | build_chemical_state_from_cn_only | CN 串 | 专用命名空间+未知事实 | 不变 |
| 4 | **ChemicalState.from_dict** | 序列化载荷(恢复) | 仅版本+fidelity 枚举 | **+validate_state_object** |
| 5 | **audit_hypothesis(states=…)** | 直接 dataclass 对象 | 无 | **+validate_state_object(逐个)** |
| 6 | audit_hypothesis(raw_structures=…) | 原始结构串 | 工厂构建(#1)+state_ref 身份 | 不变(再经 #5) |
| 7 | store put_state/_collect_state_writes | state 载荷 | _verify_state_payload_facts(writer 同源) | 不变(**验证源**) |
| 8 | store._verify_stored_state_rows | 已存行 | 重推导 | 不变 |
| 9 | 供体诊断四原始字段 | 原始串 | _guard_input_cx_classes | 不变 |
| 10 | 池 preview conservation/冻结执行器 | 原始串 | 诊断 only/冻结 | 范围外(C2 划界) |

**R7-02:submit_event 的出现行复用入口**

| # | 入口 | v7 校验 | v8 |
|---|---|---|---|
| 1 | 首提 states=[](复用路径) | _verify_stored_state_rows + _verify_stored_appearances(R6-04 修复) | 不变 |
| 2 | **首提 supplied states(INSERT OR IGNORE 复用同 hash 行)** | 载荷事实已验;**既存同 hash 行未验** | **+收集阶段同 hash 行内容复算** |
| 3 | 重放 states=[] | 全链校验 | 不变 |
| 4 | 重放 supplied states | _collect_state_writes + 全链 | 新校验同源生效(同码) |
| 5 | 绑定(unsupplied 唯一出现) | 存在性/计数+hash | 不变 |

## 3. 两项 P1 逐项处置表

### R7-01 恢复/直接对象首次消费同源验证

| 项 | 内容 |
|---|---|
| 位置 | [chemstate.py:validate_state_object](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py)(新函数,与 store._verify_state_payload_facts 同源:版本门/fidelity 分轴/origin 合法/CN-only 专用契约/结构态 canonical 重推导+raw 登记守卫+raw→strict 身份一致);[chemstate.py:from_dict](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/chemstate.py)(恢复入口接线);[audit.py:audit_hypothesis](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/audit.py)(直接 states 逐个接线,raw_structures 构建后统一过) |
| 前行为 | 正常工厂建 CCO/CC=O/H2、真实 AtomTool 乙醇氧化证明不动,只改序列化 payload 的 `structure_smiles_raw="CCO \|r\|"`(state_id/规范串/版本/四轴 as_written 保留):from_dict 接受,恢复对象经 audit_hypothesis→decide_admission 全 verified/full/**R6 expand**;H2 raw 改 `CC=O`(跨分子)同根全 R6;直接 dataclass 对象(不经 from_dict)同样绕过;指定手性 `F[C@H](Cl)CCO` 远端氧化同根 |
| 后行为 | 恢复入口与 audit 直接对象在首次授信前共用纯状态验证:raw 含未登记 CX 项 ⇒ ChemicalStateError(kind=raw_structure_rejected,reason=unregistered_cx_class 带违规项原文——不静默清洗信息再授 full);raw 解析到另一身份 ⇒ raw_identity_mismatch(同图异拼写 OCC 接受);规范身份/结构事实(state_id/formal_charge/cn_identity/立体/同位素)重推导不一致 ⇒ state_fact_rederivation_mismatch;origin 未知 ⇒ invalid_structure_origin;空结构非 CN-only ⇒ structured_state_missing_isomeric;CN-only 走专用契约。非法对象结构化拒绝或诚实身份 unknown、**不 R6**;只核对象内部可确定一致性,不认证来源真伪/历史执行/机制 |
| 依据 | R7 §4 R7-01 最低验收:writer 同源的既有验证用于恢复和直接对象首审;store.put_state 对相同载荷已有同源规则拒(测试 test_r7_01_validation_source_discloses_not_writer_only 互证) |
| 测试 | r8_chem 19 例(反例 12:from_dict 恢复 6[3 参数化 raw+跨分子+电荷+origin+组合]、直接对象 3、指定手性 1[恢复+绕路+直接三路]、恢复组合 2;正控 7:clean 往返/同图异拼写 OCC/登记 atomProp 含空格/指定手性正常链/CN-only 诚实 unknown/存档 fidelity 边界/writer 同源互证) |

### R7-02 首提 supplied SID 的既存同 hash 出现行校验

| 项 | 内容 |
|---|---|
| 位置 | [store.py:_collect_state_writes](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py)(收集阶段:每个提供 state 的既存同 (state_id,appearance_hash) 行立即复算 content_hash(payload)==appearance_hash,不一致 ⇒ Ppv1LedgerCorrupt(kind=appearance_hash_corrupt)零写入);首提/重放两分支共用该收集函数(重放行为不变:同一错误码,拒绝只是提前);首提 reuse 注释同步说明 supplied 不再豁免 |
| 前行为 | 先 public put 合法 sub/prod,仅在合成 SQLite 改产物 appearance.source_refs 而 hash 不动,再首提:states=[] 已拒(R6-04 修复);**重新提供有效 prod-only 或全量 states ⇒ created=True**,新增 event/projection/plan 各 1、links 2(重放才 appearance_hash_corrupt)—— 有效输入不能证明被 INSERT OR IGNORE 复用的行有效 |
| 后行为 | 实际复用的坏 appearance 在**各 supply 路径首提立即 Ppv1LedgerCorrupt、零新增**(校验区执行,事务回滚),不延后、不自动覆盖修库;supplied/unsupplied 不两套授信(unsupplied 复用路径既有校验保持,states 表语义冲突零写入拒绝保持——不为改错误类型返工);合法 none/partial/all 先存、同图多来源、排序幂等与无输入重放保持;链接集合 R6-05 已关,不新增整本账本抗一致重造要求 |
| 依据 | R7 §4 R7-02 最低验收:首提校验实际引用/复用的既存 state 与 appearance,包括 supplied SID 的已存同 hash 行;"可将纯验证统一到收集/绑定阶段" |
| 测试 | r8_storage 9 例(反例 2:prod_only/all 重给有效载荷首提 → LedgerCorrupt 零写入;共享规则 1:落账后损坏+带载荷重放同码拒绝[基线亦拒,保持];既有保持 1:states=[] 首提拒;正控 5:none/prod_only/all 参数化+全新库首提+语义冲突零写入保持) |

## 4. P2 同步项处置清单(R7 §7 允许项)

| 项 | 处置 |
|---|---|
| r7_conditions 最后 flag 测试参数顺序 | **已修**:[test_ppv1_r7_conditions.py](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_r7_conditions.py) `test_r6_03_snapshot_row_tampering_still_rejected` 末段原 `_audit(*_oxygen_hyp(), child2)` 实参顺序写反(evidence 被当 context,实际断 context_object_invalid_type);修正后按真实链路断 `gate_flag_mismatch`(R7 §6.3 所指) |
| from_dict 基线说明 | **已更正**:同文件 `test_r6_03_from_dict_rejects_signature_without_rows` docstring 原称"基线红(恢复接受且 R6)"——事实为 id 未换的载荷基线已由内容身份层拒绝(基线绿),R6-03 原反例红点在 derive 洗出新 ID;按 R7 §6.4 更正,v7 新增的是 signature_row_correspondence 层 |
| 7 披露红准确分类 | **本交付如实登记**:R7 基线 33 红的正确窄分类是 **6 字段/缺表 + 1 新增 violation kind 披露红**(R7 交付原称"7 项全因 KeyError/缺表"不精确);本轮基线 14 红全部为行为红(无字段/缺表红——r8 新测试顶层只用基线已存在符号,无需 import 适配) |
| 复合控制未执行部分如实报告 | **如实登记**:R7 的旧条件复合探针在预期拒绝处停止后内部后半段未执行不算通过(R7 复审已用 16 分段案例补足);本轮无复合探针新增;R7 化学探针 v8 复跑在 from_dict 翻转点停止(55/57 条),尾部 2 案由补全脚本覆盖(见 §5.3),如实分开登记 |
| v7 规则整理(full 两根据/拒绝早退口径/DATA 前提) | **已落字 mimo v8 请求**:判据三 4)"覆盖 full 的两个互不替代根据"(mimo C4);判据五 8b 拒绝⇒无 disposition + execution_ok=False 早退边界、8c 两句表述边界与 strict 语义(mimo C6/C5[d]);判据一 2b 恢复/直传入口 + C2 划界 + (d) 拒绝不反推含义;判据四"要求评估后不可变"前提;DATA/SgD 剥离适配器前提保持;C3 冻结前往返无损执行验证句入 §6 |
| scope 顶层/同屏展示 | **列后续(P2,不变新增阶段门)**:completion_license/scope 已在 center detail 机器披露(R6 原门满足);顶层别名/license_applied/渲染同屏列为后续 API/展示层事项,已写入 mimo v8 请求判据三供表态;SRU 含空格保守过拒 4 形状维持 R7 复审判定(P2 限制,未证静默丢失) |

## 5. 测试证据与命令

~~~bash
PY=~/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43

# 全量 ppv1(21 文件)
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -p no:cacheprovider -q \
  tests/test_ppv1_profile.py tests/test_ppv1_domain.py \
  tests/test_ppv1_s2.py tests/test_ppv1_rework.py \
  tests/test_ppv1_r2_conditions.py tests/test_ppv1_r2_storage.py \
  tests/test_ppv1_r2_chem.py tests/test_ppv1_r4_conditions.py \
  tests/test_ppv1_r4_storage.py tests/test_ppv1_r4_chem.py \
  tests/test_ppv1_r5_chem.py tests/test_ppv1_r5_conditions.py \
  tests/test_ppv1_r5_storage.py tests/test_ppv1_r6_chem.py \
  tests/test_ppv1_r6_conditions.py tests/test_ppv1_r6_storage.py \
  tests/test_ppv1_r7_chem.py tests/test_ppv1_r7_conditions.py \
  tests/test_ppv1_r7_storage.py tests/test_ppv1_r8_chem.py \
  tests/test_ppv1_r8_storage.py
# => 536 passed, 0 skipped(508 存量 + 28 新增;日志 pytest_full_output.txt)

# G01 安全隔离工程回归(R7 复审 §2 新口径;不含 evaluation/金标/题面)
PYTHONDONTWRITEBYTECODE=1 $PY -B \
  $REPO/docs/review_evidence/ppv1_r8_impl_2026-10-07/safe_g01_r8.py \
  --repo $REPO --out /private/tmp/ppv1_r8_g01_safe \
  --python ~/miniconda3/envs/depending43/bin/python
# => 实际数字见 g01_safe_isolation/(执行结果/缺席依赖逐项在 README);
#    不是原环境 1119/16 数字,不外推科学性能

# 基线红(先红后绿)
git worktree add --detach <tmp> 858dd94
cp tests/test_ppv1_r8_chem.py tests/test_ppv1_r8_storage.py <tmp>/tests/
# (无 import 适配——新测试顶层只用基线已存在符号)
# => 14 failed / 14 passed(日志 baseline_red_output.txt)
~~~

### 5.1 红验证(先红后绿)

- 基线:`git worktree add --detach /private/tmp/ppv1_r8_baseline_wt
  858dd94`,复制 2 个 r8 测试文件(与 R7 同口径;**本轮无需
  import 适配**),运行 ⇒ **14 failed / 14 passed**(28 用例);
- **14 个红全部为两项 P1 反例的行为翻转**(断言形如
  DID NOT RAISE、created==LedgerCorrupt):
  - R7-01(12):from_dict raw 未登记 CX 3(参数化 CCO/CC=O/H2)、
    H2 raw 跨分子 1、结构事实(电荷)1、未知 origin 1、恢复+dataclass
    绕路组合 2、直接对象 raw/跨分子/电荷 3、指定手性恢复+绕路+
    直接 1(三路断言合并单测);
  - R7-02(2):prod-only / 全量重给有效 payload 首提
    created=True → 首提 Ppv1LedgerCorrupt 零写入;
- **14 个基线绿全部为正控制或基线已拒形状**:clean 往返+公共链
  R6(1)、同图异拼写 OCC(1)、登记 atomProp 含空格(1)、指定手性
  正常链(1)、CN-only 诚实 unknown(1)、存档 fidelity 边界(1)、
  writer 同源互证 put_state 拒(1)、states=[] 首提拒保持(1)、
  合法 none/partial/all 先存首提+重放(3 参数化)、全新库首提(1)、
  带载荷重放共享规则(1,基线亦拒)、语义冲突零写入(1);
- v8(当前工作树)⇒ **28/28 全绿**;worktree 已清理(创建/移除
  记录在 manifest.json)。

### 5.2 修改的既有测试与理由

| 测试 | 改动 | 理由 |
|---|---|---|
| test_ppv1_profile/s2/r2_chem/r2_conditions/r4_chem/r7_chem 版本断言(9 处) | -7 → -8 | 契约族升 v8(机械) |
| test_ppv1_r7_conditions `test_r6_03_snapshot_row_tampering_still_rejected` 末段 | 实参顺序修正+新断言 gate_flag_mismatch | R7 §6.3:原参数顺序实际断 context_object_invalid_type,不验旗标矛盾;修正后断言真实链路(控制意图落到位) |
| test_ppv1_r7_conditions `test_r6_03_from_dict_rejects_signature_without_rows` | docstring 基线说明更正 | R7 §6.4:基线事实不符(该项基线绿);原反例红点在 derive 洗新 ID |

### 5.3 复审公共探针前后对照(R7 审核方探针在 v8 隔离复跑)

| 探针行 | v7(858dd94,R7 复审记录) | v8(本轮回跑) |
| --- | --- | --- |
| C1_raw_{substrate,product,H2}_unknown_flag(C1 类 raw 加 \|r\|) | ok:true,恢复→audit→admission expand/R6 | ChemicalStateError(raw_structure_rejected/unregistered_cx_class) |
| C1_raw_uncovered_H2_different_molecule(H2 raw=CC=O) | ok:true,R6 | ChemicalStateError(raw_identity_mismatch) |
| C1_chiral_raw_unknown_flag(手性 raw 加 \|r\|) | ok:true,R6 | ChemicalStateError(补全脚本同码;原探针在 from_dict 处停止,见下) |
| C1_canonical_*_unknown_flag(canonical 加 r) | retain(R7 已认可窄判断) | ChemicalStateError(state_structure_unparseable——canonical 串不可解析,同为拒绝;方向不回退) |
| C1_restore_control_{clean,same_graph_spelling,registered_metadata} | R6 expand | R6 expand(保持) |
| C1_chiral_clean_control / C1_CN_only_honest_unknown_control | expand / retain | expand / retain(保持) |
| storage first_existing_appearance_{prod_only,all}_corrupt 首提 | created=True(+event/projection/plan/links) | Ppv1LedgerCorrupt(appearance_hash_corrupt)、零写入 |
| storage first_existing_appearance_none_corrupt 首提 | 首提拒(R6-04 修复) | 同(保持) |
| storage first_existing_appearance_*_valid | 首提 created=True / 重放 created=False | 同(保持) |
| storage first_reused_semantic_{cn,schema,inner_id} | 首提 state_*_corrupt 零写入 | 同(保持) |
| storage multi_occurrence 全 6 案 | 见 R7 §3(关闭) | 同(保持:link_corrupt×3/entry_missing/none+reverse 幂等) |

探针复跑说明:R7 化学探针(chemical_boundary_probe.py)第 123 行
在 capture 外直接用 `ChemicalState.from_dict(pay)` 构造篡改对象——
v8 恢复入口即拒,探针在该行停止(55/57 条;stderr 的拒绝 traceback
即修复本身;探针未修改、保持原样);尾部 chiral raw 与 CN-only 两
案由 `chem/r8_probe_completion.py` 以同 capture 语义补跑(3 条,
含 dataclass 绕路直传 audit 一条)。R7 存储探针(storage_contract_
probe.py)15 案全部完整复跑(exit 0)。两个观察断言脚本
(assert_chemical_observed.py / storage_assert_observed.py)按设计
在首个翻转断言失败(它们钉住 R7 缺口,不是修后验收线;复跑输出
留证据)。

## 6. G01 安全隔离工程回归(R7 复审 §2 新口径)

按主会话操作约定,本轮**不在原环境跑 `tests/ -m "not slow"` 并把
结果当验证数字**(该口径含真实 gold_routes 读取路径——
test_score_report.py:115/189、batch.py:198/225、score_report.py:
69/117,与零金标访问冲突)。改用 R7 审核方安全隔离方法的本轮
适配(`safe_g01_r8.py`):路径白名单沿用 R7 清单(208 仓内输入
+ 42 普通 dependingv3/src 源文件 + 18 本仓非题面 v3 反应资产
镜像)+ 2 个 r8 新测试文件;hash 记录当前工作树新鲜值(实施方
证据;R7 审核方脚本的 HEAD/hash 钉死是其独立复核要求,必然拒
v8 工作树);pinned env(PYTHONPATH/BBD_DATA_ROOT 空目录/
V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT)与显式排除用例
同 R7;不复制 .git/reports/data/evaluation/benchmark/gold/封存/v4。

实际数字与缺席依赖见 `g01_safe_isolation/`(执行结果 JSON +
完整 stdout/stderr + preparation.json + input_sha256.json):
预期 **1138 passed(1110 + 28 R8)/ 8 skipped / 17 deselected**
(8 skip = 5 真实评价依赖 + 1 缺 v4 对照源 + 2 未复制 phase_d
provenance summary;17 deselect = 16 slow + 1 显式排除的
export 用例);逐项以实际输出为准,不凑数字、不把 skip/deselect
改成 pass。两轮隔离数字(R7 审核方 1110/8/17 与本轮)如实分开,
不冒充完整 1119;工程回归不代表任何题域科学性能。

## 7. schema/语义版本与兼容策略

| 契约 | v7 → v8 | 兼容声明 |
|---|---|---|
| profile/chemstate/hypothesis/event/store/context/dependency/provenance/substrate_profile/audit/admission_policy/donor_diagnostic/pool_audit/pool_order/input_preview/condition_assessment | -7 → -8 | profile 从未放行执行流(入口 fail-closed),无已发布 run/产物;升版即生效,无迁移;v7 载荷按未知版本既有门拒绝 |
| gate_mapper | -3(不动) | 本轮未触碰 |
| run identity | v43-identity-2(不动) | 未触碰 run_identity.py |
| search_limits | -2-proposed(不动) | proposed 草案,S3 落地 |

语义变化要点(v8):ChemicalState.from_dict 恢复与 audit 直接
states 首次消费共用公共 writer 同源的纯状态验证(raw 登记守卫/
raw→strict 身份一致/规范身份与结构事实重推导/CN-only 契约——
非法对象拒绝,不静默清洗再授 full);首提对 supplied SID 既存同
hash 出现行收集阶段即校验(损坏 ⇒ LedgerCorrupt 零新增);store
schema 语义随 store-8(无表结构变更,行为校验收紧)。

legacy_v43:零改动承诺继续成立——全部改动在 pollutant/ 包与
ppv1 测试(+docs+AGENTS.md);冻结执行器 services/atom_tool.py
未改;storage/pathway_store.py 未改;G01 安全隔离回归为证。

## 8. 剩余未知与边界(不宣称冻结)

1. 化学判据 v8 **未冻结**:mimo v8 评审请求已更新(判据一 2b
   恢复/直传入口+C2 划界、判据三 full 两根据、判据四不可变前提、
   判据五拒绝/早退口径),待用户转交;冻结以 review + mimo 回应
   与程序证据互证为准。
2. 契约 v8 未冻结;S3 入口 fail-closed 未解除(runner 未触碰);
   不实施搜索/队列/终点/评测。
3. **R7-01 的范围边界**:只核对象内部可确定一致性(字段与结构
   重算互证),不认证来源真伪/历史执行/机制;C1 canonical 串
   加 r 的三例在 v8 走"结构不可解析"拒绝(方向不回退);顶层
   scope/同屏展示与 license_applied 标志列后续 API/展示层(P2);
   SRU 含空格保守过拒 4 形状维持 R7 判定(P2,登记限制)。
4. **R7-02 的范围边界**:校验实际引用/复用的既存行(supplied
   同 hash 行+unsupplied 绑定行),不新增整本账本抗一致重造要求;
   put_state 幂等追加入口未加同 hash 行复算(其 INSERT OR IGNORE
   后 submit/重放仍会闭合同 hash 行;本轮范围以 R8 提示词首提
   入口为准,如实登记)。
5. 已证修复保持关闭:R6-01/03/05 及 R6-02/04 原反例本轮全部
   复跑保持(R7 §3 裁定不重开)。
6. S3 排期项(不冒充已实现):完整供体变换模板 checker
   (full_template scope)独立注册;执行流接 center_evidence;
   local_delta/edge_kind/scoring_key;互变/质子化等价类;被拒
   共同产物的展开计划消费。
7. 已知缺口(登记保留):增强组联合映射范围(unsupported);
   平面手性等非四面体构型比较(unsupported+公开);条件单位
   不换算(入口契约);matrix 同义/包含须注册;fidelity 的
   radical 保真轴;manifest 歧义显式引用参数。
8. 科学验收整体 pending(S5);536 项工程测试不构成任何路径
   科学性能声明;合成计量闭合不证明机制/生物可行性/酶选择性
   (探针与测试全部如实标注来源;自洽虚拟记录只证明输入集重算
   自洽,不证明历史执行)。

## 9. 与原规格/R7 复审的冲突清单

无新增实质冲突。两处"R7 复审未逐字规定、按其最低验收收紧":
- §5.1/§7.1 身份键入口的**恢复/直接对象首次消费验证**(R7-01
  验收"把既有规范身份/结构事实、raw 登记与 raw strict 一致性
  校验用于恢复和直接对象首次审核"——具体函数化落
  chemstate.validate_state_object,与 store writer 同源);
- §5.3/§9.2 首提校验 supplied SID 的既存同 hash 出现行(R7-02
  验收"共享收集/绑定/重放规则"——统一落 _collect_state_writes
  收集阶段,首提/重放同码)。
