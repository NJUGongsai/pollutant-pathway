# S3a 继承契约、化学文字与 mimo v9 专项复核

实际 HEAD：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`；父提交：`00e509a974b40a7c9779fcd35e53b16637a13d60`。仓库固定 dependingv43；全部合成执行在仓外新 tmp 的完整 src/vendor/metadata 副本，Python depending43、`-B`、`PYTHONDONTWRITEBYTECODE=1`，未访问真实金标/题面/封存逐题 run、dependingv4、外部模型或真实资产。

## 1. 结论与固定范围

**本专项发现一组既有契约内 P1：S3a B4 / done 恢复把坏权威事件账当作可用记录。不能通过本批。** 两条恢复路径只检查事件索引身份，绕开完整公共 writer 的既存重放校验；B4 还把搜索状态变 done、预约变 consumed、attempt 变 recorded。不是要求新化学机制或 S3b 调度，直接对应任务书 §3.2 及 §4.4 H08 / §7 R8 继承行。

正常提交仍调用公共 writer，raw `r` 输入拒绝，零写入。runner start/resume 对 PPV1 仍 fail-closed；legacy 共享文件文字改变身份哈希、运行分支 AST 不变，交付披露属实。S3b 无生产 audit caller 的未交付边界如实，不单凭未实现它增加 S3a 门。

主审另审预算/并发/B3跨action/request身份，及独立全量/基线/G01；本专项不重复这些工作，不将其交付声明数字当本专项执行。

## 2. P1：恢复完整性消费降为索引检查

位置：`search.py:1513–1537` B4 `find_event` 命中后直接 `complete_action`；`1484–1493` done / `1504–1512` existing commit 调 `_verify_commit_event`；`1595–1620` 只 `get_event` 看 run/hypothesis/parent/context 身份列。store `get_event/find_event` (`1964–1982`) 是无完整性认证的读视图，既有 `submit_event` 重放 (`1590–1710`) 才消费 state/appearance/hypothesis/event/payload/manifest/links/projection/plan 必要记录的契约。

公共链合成事件：`CCO → CC=O`、unknown 系数、partial participants（无机制或 R6 认证），经 factory → valid hypothesis/event → 注册 run → enqueue → claim → `submit_action_event` 落账。然后分别在“事件已提交记账未闭合”和“已 done 的首次恢复”修改已存权威记录，关闭库，新连接调用 `recover_run(policy_block=原块)`。

两阶段各 13 案：clean 正控 + 12 类损坏：产物 state charge=99 / schema未来值；appearance source_refs-only 改、底物 raw 加未登记 r；hypothesis origin 改；event occurrence manifest 清空；projection / plan / appearance links 删除；state / appearance / hypothesis 必要行删除。共 26 案：

- 2 clean 恢复正常，同事件 writer 重放 `created=False`，合法路径保留。
- **24 坏权威案 recover 均正常返回**。B4 的 12 案全部补账变 done/consumed/recorded；done 的 12 案返回 `done_commit_verified`（不写库，但错误宣称完整消费成功）。
- 同一库、同一个原有效 event/输入继续调用**公共 writer 重放全部拒绝**（state 显式供给的 semantic conflict / 其他 LedgerCorrupt），前后全表无写入。坏 authority 不被 repair。
- raw `r` 直接搜索提交额外 1 案：`Ppv1StateContractError`、全表零变化，首提正常路径没有退回。

`inheritance_v2.stdout.jsonl` 有 27 条，`authority_cases/<case>/input_output.json` 每案完整原输入、original/before/after/replay_after 14 表、异常 detail 和恢复报告，观察断言 exit0。`assert_contract.py` 按正确契约预期失败，首个 `B4_before_bookkeeping__state_charge` 即停；后续断言未执行，24 实证来自逐段捕获与独立观察断言，不能拿旧 assert 后半段当通过。

最低回修范围：恢复 / complete / 已完成幂等入口真正消费事件作为成功证明之前，沿现成同源完整 ledger 校验核全部必要权威记录；事件缺/坏立即结构化失败、保全且不写补账，不当前对象猜修旧账。保留合法 B4 一次补账、done 重复验证、正常 raw 拒绝正控。可提取可复用只读校验，不能仅把旧 `submit_event` 读视图替换成另一个索引检查，也不需要新增整库抗一致重造/真实来源认证。

## 3. 当前小探针：化学继承、错误层级与 None

`chemistry_v2.stdout.jsonl` 15 case + assertion footer exit0（其中静态 inventory 是 1 case）；锁定 RDKit `2026.03.6`。单独 `cx_controls.stdout.jsonl` 9 case + footer exit0，原 R8 固定输入 retained6/removed3 的分段复核；**不是整套 R8 重跑**。

- 原 raw `CCO |r|` 恢复为 `raw_structure_rejected`；canonical `CCO |r|` 恢复为上层 `state_structure_unparseable`，内层 `detail.reason.kind=unregistered_cx_class`；真坏 canonical 同上层、内层 `unparseable_smiles`。writer 同类拒绝、零状态写入。
- RDKit 直接解析 `CCO |r|` 返回 mol，写出 `CCO`。守卫拒绝是本仓登记政策，不能从拒绝推导实验事实。该单例直接执行证据不证明一切 CX 支持形或样品纯度。
- execution_ok=False 且四结构字符串不可解析/带 r：check_edit 早退三个判定字段 None、diagnostic.center_evidence={}；converter 有 checker_version/evidence_refs 等元数据、center_match=None，没有 checker_scope/proof_record。使用合法合成 hyp/state 进入公共 audit，`transformation_center=unknown`、`center_checker_scope_unknown`，未进入内部复算。None 不当通过。
- 9 新小往返控：atomProp 两形、DAT逗号/空格两形、label、坐标、AND、OR、radical。均 build→canonical reparse 同 state ID；另外 literal R8 retained6/removed3 经 build/from_dict/validate/canonical再parse/writer/read 回，同严格身份，removed3 与 bare ID 相同。没有宣称当前未知 SRU 形全部支持。
- chemstate/audit/path_context/hypothesis/events 五源与 R8 基线 bytes **完全相同**，逐 SHA 在 `inherited_chemical_source_hashes.json`。R8 其他分段/历史控制仅作旧证据引用；当前全量由主审独立执行，不冒称本专项复跑全部 R8。

## 4. runner / legacy 身份 / 静态捕获

公共 start_run 对 PPV1 即使传 model 对象也先 RunError，run 目录未创建；持久 PPV1 identity 的公共 resume 同拒，原 identity bytes 不变，未进入 legacy provider /预算派生/图。`runner_AST_except_refuse_function_equal=True`：排除唯一 PPV1 拒绝函数后全部 AST 与基线一致，模块 diff 仅该函数文字/detail。本专项未以这点替代主审 G01，但说明交付“legacy 行为未改”的范围。

legacy code identity 只共享 runner 受本提交影响；aggregate 当前 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`，按固定分集将唯一改动 runner 替回基线为 `5e8761c91d355f66ba81dfd80e6c3203b526d7ae4f2845baeaaa46b2246bf3a3`。交付“文字哈希使跨版本旧 run resume 身份拒绝”的披露属实；不是零身份变化。十上限除 version 外默认及全部范围 AST 比较相同，单位正文及新增计数由预算专项核。

全 src AST：10 个 AuditContractError 抛点无 enclosing broad catch try body；audit_hypothesis 生产 caller 0；check_edit_against_donor 唯一调用为 audit 复算，无 try 祖先；specific except AuditContractError 0。search 化学构造/解析调用 0、公共 submit_event 2（普通提交/B3）。这些是当前源码静态证据，grep空不是未来 caller动态安全证书；search/store 普通 rollback+raise catch 并不吞异常。新 S3b caller 义务仍 pending。

## 5. R8 P2 八条同步与 mimo v9 九条件

任务书 §8 的八项在 v9 request 与 delivery §9 均落字：①r拒不反推实验；②同源非独立双算；③经首消费入口限定；④scope归属更正；⑤恒入≠已适用、三条件；⑥frozen 与内容身份机制分写；⑦三个None及converter元数据；⑧无生产caller且义务未闭合待S3b。另外 canonical 层级、14红不是14旧R6、charge99旧R5d、旧化学55/57 early-stop/flag实参更正在新文本登记。历史文件不回写。测试R8旧错误charge注释未修改，本轮新交付正确说明；它仍是原P2精度项，不把旧文案重新升功能门。

mimo 九条件的有限裁定：

| 条件 | 本轮裁定 |
|---|---|
| ① 两处 state_structure_unparseable 包装、按reason.kind读 | 当前小公共恢复/writer执行证成，canonical+r与真不可解析应分例；新规则补读法P2 |
| ② r拒/受皆非分析认证 | 输入契约 + 小RDKit执行支持；正控接受不认证样品，适合文字补充P2 |
| ③ 同源确定性拒篡改/非独立核算 | v9已有“与工厂契约一致、不是独立双算”，可补“不跳过必要消费口”，无新门 |
| ④ 表示/账目验证≠来源/稳定性认证 | 化学表述可补；v9“搜索不存在绕过验证路径”全称被本轮B4/done证据反驳，须随P1修复改成实际验证边界 |
| **⑤ 键断裂/电子去向句字面落判据三正文** | **已落地**：v9§3 scope更正正文直接引用“本许可不区分该参与物的键断裂方式与电子去向”，并归属许可定义/规则而非代码scope。代码未改、无额外身份影响。当前草案未冻结；不要因mimo称“冻结正文”倒造本批freeze门 |
| ⑥ full/uncovered/许可的真值表 | 三条件及恒入≠适用正确（限定最终覆盖detail）；mimo所写值`partial`实际是`partial_unchecked_transformation`。有uncovered且partial可能含coefficient_binding_mismatch，不能概括成许可本身判负；须看coverage_violations；unknown_coefficients等早退亦非已使用许可。P2精度，不新机制 |
| ⑦ context新ID/parent链 | 与原继承契约方向相同；新S3b实际消费须保留该契约，当前source未改、既有验证不等于禁止合法新内容构建。P2文本，不要求底座新增调度 |
| ⑧ failedconverter缺scope/proof→中心unknown | 本轮执行证成，metadata仅追溯，可直接落字P2 |
| ⑨ S3b caller正常逃逸/宽捕获负控+未闭合 | 未闭合披露已在v9，当前无caller是S3a既定边界。S3b应有异常中止本次成功admission/submit的公共负控；不能把静态禁止所有except Exception扩大成新框架门 |

mimo对B3有一条明确“转Codex”静态预警：未见事件 run/parent/context 对 action 冻结身份比较；**仅读码提示，不是执行证据**。搜索专项执行四类跨身份来证成，不能把其测试数或本审新执行归为外模已验证。它的静态表“提交走公共writer”对正常/B3 fresh结构写入成立，不证明 B4/done完整权威消费，因而“搜索不绕过”需修正。

请求大量“同v7/v8、1–4同v8”的缩略引用使化学全文严格意义上不完全自包含；建议下一请求展开必要定义/判据而不是读者补历史，属本轮文档交付P2，不借它追加新的化学功能。判据冻结由用户裁定，本审未宣布冻结。

## 6. mimo 待执行清单与证据采信

①PPV1 594、②基线2行为+2collection/58未执行、③G01 1196/8/17、⑤四崩溃/H05-H08/预算：本专项不自行背书交付数，交主审/工程/搜索专项独立执行登记。④篡raw搜索提交拒：当前额外公共probe直接证成零全表变化。⑥锁RDKit词法/放行往返：本轮小矩阵、原retained6/removed3当前执行证成；不认证未登记所有形。⑦广捕获关系及0caller：全src AST证成。⑧三None/空diag有测试：旧test_f11仅断reaction/strict+reason；源码其它此类专门断言未在本专项作为现成覆盖背书，**本轮完整独立probe已钉住实际三个None、空diag、converter、audit未知**。可在实施新回归补完整断言，不构成独立新P1。

## 7. 自写探针准备错误如实登记

首个 inheritance脚本误以为 PathwayEvent有to_dict，第一clean案日志序列化AttributeError，未产case JSONL；改dataclasses.asdict，仅修记录，完整27案新目录重跑，前后原stderr保留。首个chem/static控制器14case完成后，AST literal_eval遇profile版本Name而失败；另两DAT输入为审核人自写多余字段尾f，被正确未登记拒。后用原登记语法修DAT、只在AST比较忽略version Name，完整窄probe新目录15case+footer通过；static-only一次也单列，不当额外完整化学运行。原错误脚本字节从本次编辑历史重构保存，未冒称执行时先存hash。未修改生产源码或验收行为来消失败。

只保存可读合成全部输入/前后账及原stdout/stderr；执行SQLite/source副本仅仓外scratch，归档包不含DB/源树/bytecode/cache。新archive reproduce控制器写于执行后，仅syntax/path检查、未运行；实际执行来源为原三探针及观察断言，README区分清楚。
