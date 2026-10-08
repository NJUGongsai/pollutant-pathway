# S3a-r3：工程专项与 mimo v11 互证

只审本轮三组及继承，不把文字冻结条件增成 S3a 放行新门。实际源 HEAD=41d0cd55f3def050a62325f00235cf22da302d2e，直接父=dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03。五个化学核心 chemstate/audit/path_context/hypothesis/events 对父逐字节相同；本轮 profile11/search3/store9/limits3，RDKit2026.03.6。静态扫描全 src65 Python 文件及安全 G01 白名单82测试文件；不声称扫描所有未列 scripts/tools 或证明未来动态调用。

## 执行证据

PPV1 697 passed/0 skipped/0 failed（25文件）；其中 r3 新文件49全通过，不与全量相加。父同字节 r3 49项40失败9通过，无collection/TypeError/旧kind先停；40分类=28未发生预期SearchIntegrityError+3未发生SearchContractError+2未发生SearchRecoveryError+2未发生SearchIdentityConflict+5行为值断言。DID NOT RAISE 案已进入公共行为且错误接受；这些函数后面的零写入断言未执行，不冒充完整分段。9绿细分5既有坏输入拒绝控制、4合法控制，不当9个独立合法化学正控。具体分案见 baseline_case_classification.json。

G01安全隔离1299 passed/8 skipped/17 deselected，276输入=repo216+普通 dependingv3/src42+普通本仓资产镜像18；原v3 assets/evaluation及v4不读。详见g01_exclusions_detail.json（8skip逐项理由/17nodeid）。测试体没有修改，被动观察插件仅记录实际skip/deselect。当前/父runtime记录完整新库schema、契约、Python/SQLite、legacy逐文件hash。runner.py父/当前全字节相同，legacy聚合4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae相同。

公共store.submit_event合成缺产物案零全表变化、trace含BEGIN IMMEDIATE/ROLLBACK；合法首提一次、重放created=False且全表相同。runner.start_run/resume_run的合成PPV1身份均RunError拒，无执行/身份文件变化。store本轮增加只读附随校验，不能由store字节变化推出legacy行为变化；上述public controls是真实执行证据。

## v11 八条条件

| 汇总项 | 互证与裁定（文字精度/后续S3b接口纪律） |
| --- | --- |
| 1 实际CX token | mimo指正成立。额外7例真实RDKit执行：ABS写a:1,3；AND写&1:1,3；OR写o1:1,3；自由基写^1:0，4案public构造身份往返一致。and:/or:/rad:三个字面别名均unregistered_cx_class拒。旧窄探针9个登记元数据/立体往返控制也完成。本请求139行a/o/and/or/rad不宜当实际token登记表。 |
| 2 系数句 | parse_coefficient(hypothesis.py136–173)拒非法值；store._verify_state_payload_facts（定义475、重推主体578–643）比结构事实而非系数；audit927–933 coefficient_binding_mismatch为覆盖轴并由admission首中顺序处置。这些机制不能合写“结构重推导发现系数不符在构造边界拒”；无现有明确该句所指独立检查。改写表示值非法拒、证明绑定违例unknown/partial并按决策表，不要求新机制。 |
| 3 恒入/R2b | full/partial覆盖完成分支1009–1013带license/scope，unknown_coefficients893–897及unverifiable早退不带，字段出现非证明本次使用。1664–1667 representation_contract_failure取调用方输入，R2b以映射detail为前提。mimo此项建议成立，正式冻结仍用户裁定。 |
| 4 裸partial/成功路径 | donor部分映射理由码2746与alignment_…center_unknown2707，不能与product_coverage枚举混写。execution_ok=False2553早退在2572四原始串守卫之前；失败不解析串、三个diagnostic轴None，执行成功路径再消费串。 |
| 5 入口划界 | writer同源核验体及search本体无MolFromSmiles/strict_identity_of/validate_state_object调用均属实。search首消费的结构权威由公共writer/replay等同源状态事实核验承接；verify_event_attachment_content1988只核projection/plan附随语义，绝不是单独状态身份证书。substrate_profile71–107（91直解析、不验证state）源内无生产调用方，属P2前置纪律：只档案输出且调用方须传已验证状态；不重开旧阶段或要求本批S3b生产接线。 |
| 6 known_absent归属 | 这是path_context条件评估而非元素/电荷账：706–733实体缺席conflict、826–831非数值同值缺席conflict、832–837异值unknown、819–825数值/区间缺席numeric_absence_semantics_undefined unknown。表述不能跨轴或把同值规则泛化到数值。 |
| 7 异常类 | 请求176–178括注将“CX守卫拒vs真解析失败”称不同异常类，mimo更正这一具体括注成立：restore两案同ChemicalStateError，writer两案同Ppv1StateContractError，区别是detail.reason.kind。跨入口外层类型确不同，需两维分写；raw writer raw_structure_unparseable不透reason，不能声称所有外层均有reason。窄化学日志完整捕获原外层/内因。 |
| 8 执行数字/旧commit | 本审697、40/9、1299/8/17独立证实；mimo只读意见不替代这些执行。实际父是dcb7ed6，未跑655c7e8或交付1版本红/22绿，不冒充其验证。4实际CXwriter/9旧往返均单列工程合成，不认证实验样品或科学性能，不给冻结背书。 |

## 其他读码及行号互证

static_precision_inventory.json留逐范围带原行号源码摘录及AST；mimo列主要chem/audit/path_context位置与当前源码相符。store._verify_state_payload_facts函数起点是475，595–643是其内部体；verify_event_attachment_content定义1988。其行为是调用_check_projection_scope/_check_expansion_plan同源校验，非独立化学证明。substrate_profile定义71/解析91、frozen validator337、装配validator297位置均对齐。source excerpts的行号相符不等于每个文字推论都获证。

AST实际10个AuditContractError抛点全audit.py（464/739/1076/1110/1589/1596/1603/1607/2547/2584）；没有包覆raise体的广捕获，无src/白名单测试specific except；唯一src check_edit_against_donor调用audit746不在try body。src无audit_hypothesis或center_evidence_from_donor_diagnostic生产调用，mimo已对此限定静态非动态证明，正确。assess_conditions1117/assess_candidate_conditions1172/route_assessment2112体均无validate_context_object，from_dict/derive/audit消费前校验是不同入口；未强制assess输出不授R6，本批不把没有caller当新P1。

mimo v10虚构donor_present/donor_consistency/_walk_conversions/same_cid/conversion_warnings及registered_missing/documented_absent/unrecorded均在完整src零命中。mimo v11不采信这些名字正确；checker_scope未知1064–1071是CHECK_UNKNOWN非raise。

失败diagnostic到converter的真实执行保留三个None、diagnostic.center_evidence={}，converter仍带checker_version/evidence_refs/center_match=None而无checker_scope/proof_record；实际audit中心unknown/center_checker_scope_unknown，但同一audit其他结构/身份/来源等轴仍可verified。mimo判据五建议“失败不产生任何轴结论，也不产生R行”只能限诊断自身；不能说下游audit不执行其他轴/decide永不有R行。本探针调用audit，不调用decide；其admission_disposition为空不充作下游不可能有R行证明。

两事务间竞态/defer/foreign-run pending/unknown request status的边界由权威与请求专项公共链判定，本专项不重复故障注入，不借mimo文本更改固定验收。
