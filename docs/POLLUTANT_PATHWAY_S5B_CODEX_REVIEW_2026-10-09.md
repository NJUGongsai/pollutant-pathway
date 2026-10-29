# pollutant_pathway_v1 S5b 启动批正链复审

日期：2026-10-09，Asia/Shanghai。身份：正链 Codex 主审，三项隔离专项并行取证；最终裁定由主审合并核验，不以子代理/mimo 的自报背书。

**结论：启动批不通过。P1=[S5B-L01, S5B-L02]。** evaluation-4 的有 qid 配对修复有效；真实数据双侧全漏 qid 的消费入口仍能回退错配。预注册冻结稿的老侧超集描述有方向性事实错误，敏感性候选序列还有未定义项，暂不能按“已收口稿”交用户最终确认读。S5a 的 `interface_verified_only` 交接保持，S4/S3/ISO-01 不重开；本结论不涉及真实科学性能。正式 S5b、冒烟和真实模型调用均未启动。

## 1. 固定验收、实际身份与边界

- 待审 HEAD：`a399d6e665720f6e5f2f836bd6d6ef2e5448a0b2`；直接父：`4fe1e0a459772861d1f90b6cd1e37ac469a5b0cd`。实际 git 身份、输入 SHA、初始工作树在证据 `root_audit/initial_snapshot.json`。
- 验收面仅为本次派单三件：evaluation-4 的 G1/qid 配对；旧 scorer 源码口径核验；预注册稿是否可交最终确认读。mimo r26 的事实须源码和合成执行互证。新增 P1 分别对应既定“不张冠李戴”和“差异清单在冻结前如实落字”，不追加科学性能门。
- 本审必读来源：本批交付书/预注册稿、prep、mimo r25/r26 请求与回应、S5 任务书、S5a R4 交接、AGENTS/审核协议。旧 scorer 只读 `src/pathway_v43/exam_v2.py` 和身份源码；未读取 Phase A/D 逐题报告、真实题面/金标/封存逐题 run、dependingv4 或原 v3 评价资产。116/128/130 等历史数字按用户派单与规则文档登记，**没有独立重算历史卷成绩或真实产物分布**。
- 当前用户已圈定：题源 298、费用不限、20+2 推荐档、116/128/130 历史锚+双口径、G1、40 在途。Chenyu 已恢复是最新用户/主会话来源，本审未远端访问；发车当日三锚 SHA 核验仍须实际执行。旧文“隧道未恢复”应同步。
- 业务全在 fresh `/private/tmp`：完整 src/vendor/metadata，conda depending43，主命令 `-B`、禁 pyc/pytest 缓存。G01 仅白名单隔离树全量，父 detached 稀疏 worktree；父子普通 v3 镜像同根。只新增本报告与本证据根，不 commit/push，不修改现有 src/tests/docs/AGENTS/旧永久证据。
- 中断—续跑：用户在本轮续跑消息确认此前因 ChatGPT 账号额度中断、约4270行输出，额度现已恢复；该描述按用户来源登记，不编造具体触发时刻/配额错误stdout。此前三套独立套件及两个专项已完成的结果和已建隔离树复用，本恢复段只读核对证据、补README/终稿与SHA封包，未重跑业务套件。准备/观察器错误及接续另列，不当账号故障。

证据根：[ppv1_s5b_codex_2026-10-09](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5b_codex_2026-10-09/README.md)。下文相对路径均指这个新证据根。

## 2. 独立执行数字与红绿精度

| 项 | 本审实际 | 证据与范围 |
|---|---|---|
| PPV1 全量 | **1133 passed / 0 skipped，exit 0** | 44 文件，1119 存量+14 新；`execution/logs/ppv1/` 完整 stdout/stderr/JUnit/command |
| 直接父、当前 7 文件同字节 | **19 failed / 130 passed / 0 collection / 0 skipped，exit 1** | 149 nodeid；`execution/logs/parent_changed/`、`execution/baseline_classification.json`；原断言不改 |
| G01 安全隔离 | **1733 passed / 10 skipped / 17 deselected，exit 0** | `execution/logs/g01/`；307 输入 source/copy/执行前后 SHA 全同 |
| G01 谱系 | **306+1 新、8 合法变更、零移除** | 新 `tests/test_ppv1_s5b_pairing.py`；`execution/g01_lineage.json` 逐路径登记 |
| 配对专项 | **26/26 观测确认** | 两条实际公共 start/resume 合成 run；包括已复现缺口，**不是 26 项产品验收通过**；`pairing/outputs/summary.json` |
| scorer/投影/匹配合成专项 | **27/27 完成** | purefunction/最小原生形态输入；不冒称全部经 audit/submit；`caliber/caliber_probe_results.json`、`caliber/reportability_probe_results.json` |
| legacy 继承 | **52 文件聚合不变；4 合成产物父子逐字节同** | `execution/legacy_identity_comparison.json`、`execution/legacy_current/`、`execution/legacy_parent/`及 README |

父 19 红必须按**首个实际失败**重新分类：4 配对返回/效果行为红 + 4 未发生指定 `EvaluationContractError` 守卫红 + 5 `KeyError('pairing')` 缺字段红 + 6 版本字面量红。交付“6 行为+3 披露+4 守卫+1 新版本+5 旧版本”的细分不准确；总数正确。尤其 multiple-export/order/deterministic 等父案先停在缺字段，不能凭父日志宣称后段行为已翻转。当前完整 14 条绿与额外公开链分别证明当前行为；不把字段红、版本红当漏洞数。

G01 的 10 个 skip 为：真实冻结评测依赖 5、v4 对照 1、phase_d provenance/summary 2、白名单不含冻结 docs 的契约守卫 2。最后两项在窄 PPV1/父树准入两份普通冻结文档并实际执行；G01 不扩边补依赖凑数。逐 nodeid、原因和缺席路径见 [execution/README.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5b_codex_2026-10-09/execution/README.md) 与 `execution/g01_exclusions_detail.json`。17 deselect 为 16 slow + 1 明确原评价脚本依赖，同文件逐项列齐；缺席不当通过。G01 隔离子进程产生 7 pyc，路径/bytes/SHA 在 `execution/runtime_omissions.json`，源输入不变，缓存未归档；主 PPV1/父为零 pyc。

三套独立 suite 首跑均完整保留。实施 attempt1 日志/JUnit/SHA 完整一致；其提前一次默认路径准备失败没有执行测试，按准备事故接受，不伪报为套件失败或删掉。业务库二进制省略，以 JSON 表快照/必要 schema、重建脚本及省略 SHA 披露，不泛称每案全库原始快照。

## 3. 已收口部分与继承

| 入口/规则 | 公开合成/源码互证 | 裁定 |
|---|---|---|
| 同底物两题，manifest/export 都带 qid | 两公共 run 反相覆盖，各消费本题导出；交换不同 qid 的输入列表顺序仍一致 | 原“根结构首中”缺口在严格档关闭 |
| qid 缺配 / 严格档图缺 qid | `sample_qid_unpaired` / `graph_qid_missing_in_strict_pairing`，not_evaluated；不借另一同根导出 | 保守拒配保持；正式 298 分母规则留未命中 |
| 四个输入守卫 | source_refs 不含声明 qid、重复 qid、run_id 与真实导出不符、空 qid 均拒 | 有效；qid 是外部声明映射，run 绑定只证明声明 run=原生 run，不替代未来注册表题目来源证明 |
| 两侧全无 qid，合成档 | root_identity_fallback 机读披露 | 合法旧合成兼容保持；real 档残余见 §4.1 |
| 同 qid 多导出 | 首个**可读**条目按输入清单序消费；其他已认领导出在 paired 列表披露、不入 unmatched_exports | 消费者相同输入确定性有效；构建器列表来源序未交付，不能冒称首注册闭环已验 |
| 新消费字段 | manifest.qid / native_path_exports.qid 只用于配对，consumed_field_policy 登记；化学匹配函数不消费 qid | evaluation-4/profile-24 登记方向正确，未触碰身份判据正文 |
| 公共 resume 的事件创建序 | 两 run 六表逐行保持；数据库与**新可读导出** event `(created_at,event_id)` 保持 | `pairing/outputs/created_at_event_id_stability.json`；不能扩大为 export digest 永不改变 |

resume 实际刷新 endpoint/export digest，旧导出首读按 `authority_reference_mismatch` 合法拒绝，新导出可读、边桶语义保持。这是既有 stale 契约控制，不当新 P1，也不称“全链产物幂等不变”。创建时序来源是首次提交的数据库行；store 幂等分支不重写。未来排序实现还须真实消费该受保护字段，当前没有 hit@K 实现。

冻结正文 SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`、FREEZE_RECORD `6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`、path_context `971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286b40d588d` 均与父逐字节同。7 个评分/条件/写口函数 AST、12 个已关生产/恢复/导出关键文件与父不变，见 `root_audit/inheritance_readonly.json`；legacy 52 聚合 `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` 保持。全量+有限出口控制收口继承，未声称复跑所有旧永久探针；没有以字节继承豁免本轮新漏洞。

## 4. 两组阻塞 P1 与最低收口

### 4.1 S5B-L01：real 双无 qid 仍走根身份回退

原验收：本次任务一 G1 一题一图/qid 配对、不张冠李戴；任务二 real/synthetic 支持范围如实、首消费 fail-closed。

源码：`evaluation.py:1813–1885` 配对函数仅看两侧声明是否存在；`:2059–2068` real 门仅检查 prereg approved；`:2170–2172` 调配对没有 real 禁回退门；后续照常评分/聚合。

本审公开复现：两个自行生成的同 CCO 根合成 run、两图，省略 manifest/export 条目所有 qid；输入 `data_scope='real'`，fake approved prereg **仅用于触发程序门的形状**。实际轴仍是 dev/development 合成样例，不是 298 题、真实金标或真实用户授权评测。本程序没有按题域消除此分支。`evaluate_scientific` 未拒：两图 basis 都为 root_identity_fallback；codex-a 配走两个导出并消费 digest 首位，状态 scored，进入聚合；codex-b 零配对、`not_evaluated_export_missing`。顶层 pending 状态不能抹去错误样本评分。输入/完整输出：[real_label_noqid_public_input.json](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5b_codex_2026-10-09/pairing/outputs/real_label_noqid_public_input.json)、同目录 `real_label_noqid_public_output.json` / `summary.json`。

**最低收口：代码守卫+预注册发车核对都做。** real 在配对首次消费前禁止 root_identity_fallback，结构化 `EvaluationContractError`，先于任何样本评分/聚合/持久化结果；不静默退成某题低分。保留 synthetic_rule_level 的双无 qid 合法控制、real 严格 qid 正控、缺配 not_evaluated。预注册增加真实批输出 basis 全 qid_strict 的发车/判分检查，不能看分后才发现错配。该门是既定样本身份边界兑现，不是 criteria-v2 新化学门；消费语义变化按 evaluation/profile 既有 version 规范登记。

### 4.2 S5B-L02：冻结稿口径事实与序列定义尚未闭合

原验收：任务二官方老 scorer 同构独立核验、逐情形差异如实；任务三最终确认读前冻结定义齐备、mimo 条件互证落字。

**方向性事实错误成立。** `exam_v2.py:122–157` 判每个独立候选整串 cn 身份是否属于任一参考产物 cn 集合。合成输入参考 CCO：候选 `['CCO','CO']` 首中 rank=1；候选 `['CCO.CO']` 官方主口径不中。所以预注册 §5.1 第4行“事件超集老侧不中/同向”、§5.1 第3条以及交付书核心发现3的统一“同向”描述不真；它们还与 §5.4 自己的**展平分串**规则矛盾。新严格档事件产品超集落 partial、不计 strict；在分串包装下是新增更严约束，不是旧官方也惩罚多报。不改已选 strict-only 主口径。

必须在交最终确认读前完成以下定义/事实同步：

1. 分开“展平分串”与“点串融合”的旧侧结果；老 any-one 额外字符串不破命中，融合整体只在身份本身等于参考整串时才中。订正表格、结论、交付/mimo 请求转述，保留 HIT60 dev caliber-v3 与 298 官方 scorer-2 的区别。
2. 补两个轴：**K 一个槽=产物字符串 vs 事件**；**报告可见性/宽度**（新主为所有已提交候选事件，老为答卷串，敏感性为报告投影；生产 cap=`max(1,min(width if width>0 else 1,4))`，旧≤5/步）。反应物侧细化为两侧集合**相等**，非仅含根；多产物分散到不同事件不能拼成一条严格边。
3. `report_rank=None` 处理必须明确。合成投影 [extra,target] cap1：排除 None ⇒ 老敏感表 miss；把 None 尾随 ⇒ rank2。建议按“可报告候选”只消费非 None 位次并披露宽度外产物，最终确认读前写定，不能交给得分后实现临选。不是本审替用户定 width/预算值。
4. “更严/宽向不存在”限定结构命中**存在性与指定报告映射**；同 K 的 rank/数字因单位、顺序和候选集合不同可双向移动，不能宣称每档必低或“更难达到同数字”。§5.3 表头改历史参照锚，不仅脚注补口径；四种“主通过/旧敏感表达历史锚”组合分别陈述，不拿 CN 表升 strict/化学正确，不把两次不同批历史锚彼此当可比性能差。
5. §7 统计事实如实：S1 `source_group_id=qid` 是单题簇，related 标签不会归并跨 qid 的同底物/共享记录，不能宣称主 bootstrap 已因此消除跨题相关。保留已授权 S1 主/S2 敏感性/Wilson 安排，解释实际范围；若要改变主聚类键，只登记用户/teacher 决策项，不在有限代码回修里代选。

具体执行与源码行锚：[caliber/README.md](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5b_codex_2026-10-09/caliber/README.md)。这是一组冻结前定义收口，不是五个新化学门，不要求本批实现未来真实 hit@K/敏感表判分。

## 5. 预注册保持项、P2 与发车前必办

- 20 行选择+2 前置已写入；题域298、轨道A已知证据重建、G1、严格主/CN封顶、所有共同产物 principal 但不作化学认定、net_reaction 非机制/守恒证明、participant partial、reference_only、例外规则、无重复采样、固定298分母等方向一致。known_gaps 保留为披露，不能免分母；逐边 not_evaluable 也仍按本卷298分母留未命中。当前接口覆盖桶不替代未来 hit@K 分母实现，须实施时实测。key_intermediate_recall 本题域不可评，不称测得0。
- `hit@K` 与旧敏感表消费者尚未实现，源码互证 mimo 判断属实；属于后续 S5b 判分实施批，**本审没有借未实现另立当前 P1**。四象限报告、298分母、None规则、提交序、已选阈值均须后来以合成正负控实现验收，再谈真实评测。
- 真实输入构建器尚未交付：run注册表→qid 的单一来源、图 source_refs 与 manifest 一致、清单按冻结注册序稳定生成、禁止目录遍历偶然序/内容择优，必须在构建器实施时单独验收。消费者确定性不代表构建器确定性。unmatched_exports 是完全无人认领导出，不是所有未消费者；同 qid 其他导出需单独披露。旧 stale 导出须按既有读取契约处理，不能拿“首清单序”绕过来源守卫。P2/后续入口交接，不偷变为本批未交付构建器代码门。
- cap≥3 不是旧 any-one 命中存在性的必要新门，见 §6；完整报告性可作为用户选择/披露项。报告宽度最终值与请求计数上限、并发安全值/费用时长候选不由本审替定。
- 冒烟后定型三项：per-run/batch 请求计数上限、40目标的实测安全并发、费用/时长区间。收费无上限不撤调用次数门。非298合成段0≤10次为计划值，本审没有执行；真实题的试运行计正式批并沿原身份续跑，不能看分后调配置。段1/2要区分性能信息与安全/连通性标定，涉及正式配置变更走用户既有冻结纪律。
- 用户最终确认读、Chenyu 恢复、发车当日三 SHA 硬门仍必办；加 §4.1 qid gate。审批“已恢复”与实际当日SHA核验分开。发车当日 RPM/TPM/价格快照、usage 缺失保守记账及账单回填由实施阶段执行，本审未查外部行情或密钥。
- §6 第19项称 r26 为“出题后答题结果复核”应改正为发车前规则/配对评审；真实评测后仍须 AGENTS 三触发点之3，不能预先当已履行。P2 落字搭车即可，非当前新代码门。
- 研究级独立性 unknown，89题/共享记录 related 的来源按给定元数据登记；本审未核真实卷行。统计键/CI解释改变、尚需用户/teacher 的正式结果状态，不因工程验收自动裁定。不得把已拍板题源/费用/参照线/分母重列 TBD。

## 6. mimo r26 与交付声明互证、纠错

| 主张 | 本审裁定 |
|---|---|
| 与 criteria-v1 零冲突；qid 不进化学匹配 | 采信到源码差分/AST、冻结SHA和实际输入许可一致为止；不是自动冻结/机制正确认证 |
| qid 严格档修复、四守卫、14测试 | 互证有效；当前完整14绿。父红细分须按§2改报 |
| real fallback P1 | **确认 S5B-L01**，公共合成链实测；代码守卫+发车检查都做 |
| superset错格与清单漏轴 | **确认 S5B-L02**；27案+源码；排序/K/宽度不应泛称逐K更严 |
| 清单序是首注册锚、构建器确定性 | 当前只能证明消费清单序；实际注册来源须后续构建器验证。不得以同输入绿冒称生成序已验 |
| resume created_at 未确认 | 本审两公开run事件六表、DB/新原生导出时间序保持；旧导出stale拒和新digest如实登记 |
| hit@K/敏感表尚无实现 | 读码成立；属后续评分实施，不当科学数字已验 |
| **投影“先去重再排名”会有固定乐观偏差** | **mimo 事实纠错**：`build_report_projection(['a','a','b'])` 实际给1/2/3；`prepare_hypothesis`重复共产物也保留重复refs。docstring是调用方输入前提，不是函数自动去重。纯helper/准备测试不冒称重复hypothesis可成功audit/submit；尚无真实敏感表消费者，不能把固定偏差写成已实现事实 |
| **cap≥金标最大产物数3才能保证旧any-one存在命中** | **不采信为必要P1门**：exact三产品+cap1 实测新matched_strict、旧any-one rank1。any-one只需报告至少一个相等产物；全产物可报告与旧any-one不同。None处理必须定义，但不据此新增强制cap3科学门 |
| CN表防升格、结论四象限、非模型置信序 | 文档防护，纳§4.2最低落字；不改 strict 判据、不设新阈值 |

老官方 scorer 口径“CN + 逐整串任一金标即中”核验成立；caliber v3 超集全集是另一口径，不得继续混用。第一/复测历史锚本审未独立重算。mimo 的建议逐条互证，有错误就更正，不因“零冲突”照收全部P1建议。

交付书截至提交时写“r26未送/Chenyu未恢复”是时间快照，被最新用户来源推进；后续文档同步，不当欺诈或新增代码缺陷。旧侧错格与父红分类则是实质事实精度问题，须更正。实施原封包25文件/23附件SHA完整核验；mimo包是README SHA表而非manifest，prompt/raw/response三SHA独立相同。本审未触碰金标漏扫输入或重做含真实答案的扫描，仅验已给证据字节完整性。

观察器/准备记录：配对专项第一次在已做完配对后误用表名 commit_records，接续只读正确 search_commit_records；两run resume已完成后读取旧stale导出停，仅读新导出续证，不再resume。scorer主脚本24案后缺origin TypeError，保留exit1，续仅末案，另补2案；27案不重复相加。根通用验证器对README式mimo包寻找不存在manifest失败，按原README SHA表核，不修改旧包；无产品业务重跑。详细日志/argv/env/exit和省略项在三子包与root_audit。不能称全过程零错误，也不把观察器错误计成产品P1。

## 7. 正链最终裁定与交接

**启动批不通过，P1=[S5B-L01, S5B-L02]；冻结稿暂不作为收口件交最终确认读。** qid正确声明下的配对修复通过，S5a工程接口交接保持；同构结论“确实不同构”成立，当前差异表“已齐且同向/逐K更难”不成立。先按 §8 两组有限回修，再复审最终确认读可交付性；不撤用户已有选择、不启动正式S5b。

科学性能pending。后续必须分别完成预注册最终确认、构建器/provider/判分实现及合成验收、当日权威SHA/并发/调用预算/账单措施后才谈正式跑分。用户/teacher的最终状态/真实卷裁定不由本审代选；工程测试数字不外推dev或298成绩。

## 8. 下一轮有限回修提示词（实施代理可直接使用）

你负责 pollutant_pathway_v1 **S5b启动批有限回修**，不是正式S5b。仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，基线 `a399d6e665720f6e5f2f836bd6d6ef2e5448a0b2`；先核HEAD/工作树，保留用户已有未跟踪评审材料。只修本报告 **S5B-L01/L02**，已关S5a-01~05/S4/S3/ISO-01及legacy保持。

必读绝对路径：

- `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_CODEX_REVIEW_2026-10-09.md`（本报告§4最低收口/§5边界/§6mimo纠错）
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s5b_codex_2026-10-09/README.md`，其 pairing/caliber/execution 三包脚本/原输入/首失败分类
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_LAUNCH_DELIVERY_2026-10-09.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5B_PREP_2026-10-09.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r26.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/PPV1_REVIEW_PROTOCOL_2026-10-08.md`
- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/exam_v2.py`（只读源码，不读其真实评价资产）

先列入口矩阵，再实施：

**L01**：公开 `evaluate_scientific` 的 real 首消费禁止双无qid/root_identity_fallback，结构化拒，先于样本评分/聚合/结果写入。代码+预注册发车核对都落实。机读保留原因/data_scope/缺qid范围，正控保留合成fallback、合法real严格qid、缺配not_evaluated及四原守卫。契约语义升 evaluation/profile 版本并同步现有登记测试；不动冻结正文/FREEZE_RECORD/path_context，qid不进化学结构判据。

**L02**：按本报告§4.2逐条修预注册/交付/mimo请求口径。必须分开旧分串/融合超集结果，补K单位与报告可见性，reactant set equality与跨事件产品规则如实，写定None消费规则（建议只纳非None位次+省略披露），更严限定存在性和报告映射条件，逐K无单调声明，§5.3用历史锚、四象限+CN不升格。CI保留已授权S1/S2/Wilson，修“单题簇自动纠跨题相关”夸大句；改主聚类键只列用户/teacher决策项。明确cap3不是本审强制门，不能照抄mimo投影自动去重断言。顺带同步mimo已回/Chenyu最新来源、r26是前置规则复核而非已履行结果后触发3、未消费导出与未认领导出差别；未来真实构建器按冻结注册序生成清单且不按结果择优写成交接义务。

不改变用户题源298/费用不限/20+2/116-128-130历史锚/固定298分母/strict-only/40在途；不代定width、请求上限、冒烟后并发/费用时长，不新增强制cap3门，不改统计聚类策略、不认证机制，不实现真实图转换/provider/正式hit@K判分、不执行冒烟或模型调用、不碰题面金标封存run/v4/原v3评价资产。新mimo请求自包含规则+合成，显式含本报告两项对mimo事实纠错，不冒称已有真实科学数字。

验收：复制本证据公开real标签双无qid反例到fresh tmp，修前错误评分→修后结构化拒且零样本评分/聚合/持久化结果；严格qid、synthetic fallback及各合法控制保持。L02复用27案逐条订正文案，其中纯函数/prepare测试不冒称完整audited链。新增必要回归在**直接父a399d6e同字节**红绿分类，行为/字段/静态文案/版本/collection分列，不把后段未执行算翻转；PPV1全量、G01沿307白名单谱系首跑/缺席nodeid/输入SHA前后完整登记（缺依赖不补红线资产）。`depending43`、`-B`、禁pyc/cache，脚本fresh /private/tmp，永久证据不原地执行。

交付：新回修交付书+新证据目录README/脚本/输入输出/argv env exit/SHA，嵌套manifest纳hash只排根controls，准备失败原日志不删；本轮和继承分开。实施可按本范围改代码/测试/相关交付文档，在v4.3显式路径git add、本地提交，不push；别覆盖评审报告/旧永久证据，不批量add未跟踪材料。交主会话按既有流程mimo→Codex复审。不要在这个回修任务中发车。
