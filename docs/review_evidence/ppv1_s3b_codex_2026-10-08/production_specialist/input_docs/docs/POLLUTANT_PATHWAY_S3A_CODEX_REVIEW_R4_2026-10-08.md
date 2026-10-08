# pollutant_pathway_v1：S3a 回修 r4 独立复审

日期：**2026-10-08（Asia/Shanghai）**。仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

**结论：S3a 通过，P1 清零，S3b 可以启动。** R3 的 S3A-02／03／04 三组残余已经按原最低验收闭合，S3A-01／05 保持关闭。缓存命中与“检索引用及行同时删掉”无法在当前账表区分，按固定范围接受为 P2，并明确保留限制；本结论不认证全部检索历史真实性。

实际 HEAD：`b7f2bba02ca49edd0a45a13bc9b8434909d99175`；直接父提交：`41d0cd55f3def050a62325f00235cf22da302d2e`。本报告行号对应当前 r4。永久证据入口：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r4_2026-10-08/README.md`。

从污染物降解路径预测的目标看，本批已能在限定持久搜索模型内拒绝缺必要额度证明的完成、损坏策略授权的请求状态变化、损坏生命周期的正常化。下一步才是把这些守卫接到实际搜索与化学审核链。**S3a 通过不等于整个 S3 完成、科学性能通过、判据冻结或 S4／S5 启动。**

## 1. 固定验收与独立执行纪律

验收基准为 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R3_2026-10-08.md` §4 三组最低收口、§5 已裁定边界和 §7 放行条件；继承原 S3 任务书的 S3a 范围，不追加下一阶段或整库抗一致重造门。主文件为本轮交付书 `POLLUTANT_PATHWAY_S3A_DELIVERY_R4_2026-10-08.md`、mimo v12 回应 `mimo_ppv1_chem_review_response_r12.md`；同时核对当前 v12 请求、仓内 AGENTS.md 和审核协议书。

工程全量／化学精度、搜索权威、预算／请求／停止三个专项分别在新 `/private/tmp` 隔离副本执行。复制完整源码含 vendor、必要 metadata 和 R3 永久证据中的合成反例；不在旧证据原地建库。使用 depending43、Python `-B`、禁字节码与 pytest cache。没有访问真实金标、题面、封存逐题 run、dependingv4，没有调用外部模型或实际 provider，判分零 LLM、实际网络 0。`provider_kind=real` 的账接口夹具只验证登记行为，不表示发生网络请求。

PPV1、父基线新回归、安全 G01 各执行一次；专项探针完成后只读核对输入输出和正确合同断言，归档不再跑测试。本轮没有账号额度中断事件，r3 报告中的中断是历史事件，不冒充本轮续跑。旧脚本早停、旧期待与夹具错误完整保留，未执行内部段不报通过，见 §3 和各专项说明。

评审只新增本报告与新证据目录，无源码／测试／既有文档／AGENTS.md 修改，无提交或 push。原授权 AGENTS.md 差异及旧未跟踪评审材料保持；发布前后核对 **1002 个既存输入文件**的 SHA、HEAD／父、tracked diff 与工作树，见 `input_snapshot.json`、`workspace_integrity.json`。证据包含完整命令、输入输出、返回码、分案账表、脚本及 SHA-256；合成数据库二进制不入永久目录，必要消费事实已转存 JSON，并登记被省略文件哈希。必要集合／新分段权威案核14表，预算补充核15表；旧crash／observed沿原6表快照加完整日志／schema，不把所有历史案都说成14表全库重算。

## 2. 独立执行数字与红绿精度

| 执行 | 本审结果 | 范围 |
| --- | --- | --- |
| PPV1 全量，26 文件 | **787 passed／0 skipped／0 failed**，exit 0 | 697 存量＋90 新回归，工程合成 |
| 父 41d0cd5 detached worktree，同字节 r4 新回归 | **78 failed／12 passed／0 collection error**，exit 1 | 未改输入、import 或期待来适配父版本 |
| 安全隔离 G01 | **1389 passed／8 skipped／17 deselected**，exit 0 | **277** 白名单输入，原件与隔离副本 SHA 前后一致 |

78 红必须分开写：**77 个行为红＝58 未发生预期 SearchIntegrityError＋18 未发生预期 SearchRecoveryError＋1 未发生预期 SearchContractError；另 1 个是恢复报告缺 `unknown_status_requests` 键的 KeyError 形态红。** 该例键访问之后的内部断言没有在父版本执行，不能说 78 个全部检验完拒绝行为。没有 collection 红、返回形态 TypeError 或其他值断言红。

12 父绿是 **11 个合法行为控制＋1 个已关闭的坏输入拒绝控制**：9 clean 入口、1 合法策略状态控制、1 合法失败生命周期，以及 1 sent／response 已拒未知状态的保持控制。交付书 §3 的逐项明细正确；§5 写“9 合法＋3 既有坏输入”应更正为 **11＋1**，属 P2 文档精度。90 当前通过来自787全量 JUnit 的子集，不重复相加；本审未另跑交付方的90、23或版本断言矩阵，不把其数字当本审多执行一次。

G01 277 输入＝当前仓 **217**＋普通 dependingv3/src **42**＋本仓明确非题面普通资产镜像 **18**；隔离引擎／资产路径固定，外部数据根空。实际缺席／排除逐项登记如下，完整 nodeid 见工程专项 JUnit 和 deselected 清单。

| 缺席／排除 | 本审披露 |
| --- | --- |
| 5 skip，真实评价依赖 | `test_batch_runner:52`；`test_score_report:110／163／172／184` |
| 1 skip，v4 对照 | `test_analog_assets:95`；没有访问 dependingv4 |
| 2 skip，phase_d 派生 metadata | `test_analog_v2_corpus:62／153` |
| 16 deselect，slow | 逐 nodeid 留证，测试体未执行 |
| 1 显式 deselect | `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden` |

G01 pytest **197.70s**、内部 pytest 子进程 **199.226s**、控制器 **199.841615s** 是不同计时层，不混用。Python3.11.16／RDKit2026.03.6／SQLite3.53.4；profile-12／search-4／store-9／limits-3。历史 R7 1110、R8 1138、S3a首批1196、r2 1250、r3 1299 分开登记，均不混计或外推 dev（B1 环境中间步骤）与298（RHEA 通用酶学）的科学性能。

## 3. 三组残余逐案收口与继承状态

| 原组 | 当前公开链实证 | 裁定 |
| --- | --- | --- |
| S3A-02 必要预约集合 | R3 原9入口×3必要资源×2模式：**54 坏案全部先拒**，逐案14表前后完全一致；27只删ref为 `necessary_reservation_ref_missing`、27删ref＋row为 `reservation_row_missing`。9合法控制保持 | **关闭** |
| S3A-03 状态消费冻结块 | sent／response／failed × null／缺version／bool／越界／未知键／负数，**18 原坏案**全为 `search_policy_block_corrupt`、零状态与账变化；补非expand合法空attempt的同18案亦先拒 | **关闭** |
| S3A-04 未知来源生命周期 | `corrupt-status` 在failed／同键复用分别结构化拒，sent／response原拒保持；recover在 `unknown_status_requests` 披露，原坏status保全、零写、不当普通pending | **关闭** |

### 3.1 必要集合：同源创建、B3前置与额度反例

`search.py:572` 的 `_reservation_id` 同源用于 `_reserve` 与必要集合派生；保留原逐行内容守卫，并在`:2020–2081`追加适用集合核验，二者均在写账前。总action必需；transition加transitions；expand按attempt加alternatives／attempts及适用reopens。共享alternative不因跨action重复使用被强加新额度，合法cache不强加检索预约。

first complete／B4／B1／defer／B3事件前／done四复用共9入口原反例全部收口；**B3 六坏案 event0→0、commit0→0，artifact保全**。done拒绝零新成功确认，坏action无新commit或consume。上限1双链已翻转：干净首链完成后第二claim预算拒；删首链总ref＋row后首complete拒，第二不同hypothesis的合法链仍可完成，最终只有 **1 commit／总used1**。

该坏双链最终仍有 **2 events／1 commit**：第一次普通 `submit_action_event` 已合法保存event，随后坏complete拒；第二合法链保存另一个event并完成。不能把B3“提交前零新增”扩大为所有独立首提必须零event，也不能把2events误报为2次成功搜索完成。原 R3 的 used0／commits2 漏洞已关闭。

### 3.2 请求状态：写前消费与真实调用边界

`:1481／1513／1565` 的sent／response／failed在新状态写入之前消费同一 `_limits`→`validate_frozen_search_limits`，不补默认、不依赖expected或调用方预验。`:1287` 同键复用核stored枚举，`:1547` 未知值拒、`:1555–1556` 失败来源限registered／sent；`:2767–2774／2803` recover实际披露未知状态。recover返回报告不是未知行被授执行权。

原 R3 补充脚本前31案完整捕获：18坏policy、3合法状态、5未知状态口、5foreign作用域控制均符合既有契约。末段两个合法装配夹具误删version后脚本exit1，未执行部分不计通过；合法带version的装配两控制已另行执行一次。新全表补充 **35 案**完整：18非expand坏policy、5未知状态、3real账接口控制、9终态拒绝，逐案15表快照。real样例sent账内 `network_request_count=1` 是主动调用记账接口的记录，**实际网络0**。

### 3.3 已关闭项与早停登记

- S3A-01 四异身份event普通submit／write／B3拒且artifact保全；合法B3同output一次提交、重复恢复零新增。R2原27及分段120输入重新复制执行，坏预约／attempt／commit行、投影／plan附随内容同源核验保持，无自比较授权。合法done返回真实完成event，foreign公开有效event明确冲突。
- S3A-05 claimed／open披露及有余不exhausted保持。原预算／请求／停止矩阵按既有合同有效 **114／114**，正确六原因优先级 **63／63**；10坏冻结块读取／claim／recover（含无expected）消费前拒。历史raw115的6个旧期待偏差保留，不能直接说原raw全部通过。
- 四独立子进程实际硬杀B1–B4、双独立进程ready／GO barrier、H07／H08保全及记录控制保持。runner对PPV1 start／resume双入口仍fail-closed；legacy code_identity不变。
- 化学五核心 chemstate／audit／path_context／hypothesis／events 与父全字节相同，R8已认可的R6五组、R7两项保持关闭；依靠当前全量、原权威分段反例和窄化学控制核必要继承，**不冒称重跑全部历史R8脚本**。

旧观察断言本来钉住漏洞，修复后按设计失败。复合 `probe_original.py` 在首异run正确拒绝后，后续内部段未运行；历史 `assert_observed.py` 在首坏state拒绝后化学后段未运行，不能由顶层继续推断后段通过。上限1旧assert仍期待commits2；done旧assert误期待异常类，两案完整输出已先保存，只读正确合同断言exit0，无重跑或改原输出。R3旧集合assert在首已拒坏案的旧returned形态期待处失败。原日志、退出码和适配diff全部留证。

## 4. P1 清单与验收收口

**本轮 P1=[]。** R3 三组最低收口、合法正控、继承项均满足；没有以全面拒绝换通过，没有依靠mimo读码或实施自报数字代替执行。已证修复保持关闭，后续只有同合同内新的具体公共链证据才重开。§5是限制披露，§8是S3b接线注意事项，不构造新一轮S3a返工。

## 5. cache_hit 同构边界及已接受限制

本轮执行 **7 个公共链缓存控制**：合法cache、正常非cache、仅删两检索ref、仅删两检索row、ref＋row同删，以及合法cache／非cache在检索预算0下的对照。

合法 `claim_action(cache_hit=True)` 只建总action预约；非cache两检索ref＋row同删后，在忽略**仅时间戳列**时，两者消费前 **14表逐值相同**，run／policy／action／task／frozen_pool_digest及payload也相同；此处比较同payload内digest，不认证完整冻结池。当前权威账和claim收据不持久化cache分支事实，guard不能从同一形态重建原历史。实测同删形态recover／非事件complete／done复用成功、retrieval used0；只删ref或只删row均先拒，零写。合法cache检索预算0仍可claim，非cache0预算拒且事务回滚。

**裁定：接受为固定S3a范围内的P2限制。** 理由不是“改schema麻烦”，而是条件历史事实无独立持久来源，两引用与两行同时移除后成为另一合法当前存储形态。R3最低收口明确保留合法cache、不要求认证所有历史真实性或抵抗整库一致重造；54个无条件expand必要集合和可区分检索缺项已经闭合。直接将所有缺检索行判坏会破坏已定合法cache正控。与此同时，**不得宣称检索消费历史、全部检索额度完整性已认证**。

S3b实际缓存caller若承诺恢复后区分cache与实际检索，应持久记录缓存来源／认领分支事实或给unknown，并按身份／version规范登记待审。这是实际接线时要确定的保证范围，本轮不强制额外历史签名或回填旧账。

其他已接受边界继续保留：两事务之间没有全程持锁，当前不保证外部并发SQL改库安全；不能安全归因event的defer保守不退，不证明一定执行；foreign-run行不在本run恢复清单反向披露，不能声称跨run完整诊断；claim幂等收据／停止报告不当完整行级ledger证书。readonly流程不等于整个任意并发系统已认证。

## 6. mimo v12 与程序证据互证

回应provenance为免费模型只读通道，自标读码／待执行；本审未调用该模型。其意见只采信到当前源码与本审执行互证的程度。化学判据仍未冻结，以下落字项是下一请求／实际caller的精度要求，不作为新S3a化学代码门。

| 受审条目 | 本审互证与落字要求 |
| --- | --- |
| 0b／0c测试执行标签 | 本审787、父78／12、G01 1389／8／17与277输入独立证成；回应中“待执行”归属于它自己的只读权限，不能改写成模型执行 |
| 判据一，错误层次／CX | 15窄控制＋7实际CX写出／别名控制完整；factory／strict读顶层 `detail.kind`，restore外ChemicalStateError内 `detail.reason.kind`。writer canonical外Ppv1StateContractError带reason.kind；writer raw+r外kind为 `raw_structure_unparseable` 且没有reason，不能统一成所有入口都读reason或restore的 `raw_structure_rejected`。真实token为a:／&N:／oN:／^N:；英文and／or／rad不当token。RDKit锁定2026.03.6，不认证样品／来源 |
| 判据二，元素账／覆盖 | 未知系数使元素／电荷账亦unknown；coefficient_binding_mismatch不比较结构重推导值，但completion_surplus／deficit确有结构差额核算。verified仅覆盖调用方声明清单的数值闭合；omission_pattern_matches不证明实际缺物质、不含电子／质子计量，不能认证机制 |
| 判据三，R1／R2b／R6与ID | 额外7控制：factory／strict各两坏结构早抛、audit直接空／坏canonical两案早抛且未调用admission、合法公开audit一案。仅证这些公共链不落R1，不声称R1全称不可达或防御行应删。R2b需caller映射构造detail，不传并非化学已核；表示违约不是化学不可能。audit_id按输入内部生成，外给ID核验须指明state／hypothesis／context。expand是本层许可，不等于反应可行 |
| 判据三，v9 scope归属 | scope字面与规则／许可注释各归属已纠正、保持关闭；许可恒入字段不等于实际适用，需full、uncovered非空、unlicensed空。无需再要求将非字面句塞入scope |
| 判据四，条件入口与事实 | from_dict／derive父对象／audit直接对象强制validate；assess_conditions／assess_candidate_conditions／route_assessment自身仍靠上游纪律，S3b真实caller接守卫。满足／冲突是给定事实集相容性，不核事实真实性；某场景conflict不变永久不可行 |
| 判据五，失败diagnostic与异常 | 三None、空center_evidence不通过；converter仍有版本／来源元数据与center_match=None。下游缺scope／proof给中心UNKNOWN，其他轴可verified；必需中心unknown不能R6 expand，最终也可能由更早行拒绝，不保证固定R5或retain。源内10处raise AuditContractError全在audit，零specific except；没有实际生产caller，静态不等于运行期不吞异常通用证明 |

65个src与83个明确白名单测试文件的静态检索互证，10抛点与相关调用祖先见工程专项。重点行号如 `store.py:475–496` 的 `_verify_state_payload_facts`、`store.py:2013–2021` 的附随入口、audit／context守卫与回应一致；`14643→1643` 是回应明示修正的笔误，不据此虚造代码差异。跨轮行号须重读，不能将行号命中当运行结果。

“待执行验证”逐项裁定：①RDKit CX已执行；②RegistrationHash对照本轮未另启全套，使用已审／已登记限定子集的历史证据、核心字节不变及现有回归，**不声称新扩对照范围或已正式冻结**；③测试计数已执行；④空／坏isomeric公开audit链已执行到前置异常，只覆盖上述具体对象；⑤跨RDKit版本state_id稳定性**未执行**，留未来冻结前专门取证，当前不作保证、不新增S3a门；⑥cache同删反例已执行，按§5有限裁定。执行器／preview输出仍应经state工厂／首消费守卫后采纳，不能整块诊断充当结构或ledger证明。

## 7. 交付一致性与放行

交付数字及主要行为证成；§5对r3“未知status不会写新状态”的更正属实，r4修的是合法来源行为，专用reason不替代拒绝。r3红分类旧误记已纠正，本轮78红仍区分77行为＋1形态。交付§5的父绿分组应按§2改成11合法＋1既有拒绝控制。

profile由11→12、search由3→4；store-9与limits-3保持，消费语义升版已登记待审。runner未触碰，legacy code_identity仍为 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`；化学五核心与父一致。必要集合、请求状态守卫及同键/未知状态披露均符合最低收口；S3b未交付清单诚实，不用其缺席阻塞本批。

**S3a通过，S3b可按原任务书启动；无本轮P1返工清单。** 科学性能pending、判据未冻结、S4／S5未启动继续保持。以后若改变语义、保证范围或身份版本，照既有规范登记待审，不拿本报告替代冻结裁定。

## 8. S3b启动注意事项（有限范围交接）

实施先读绝对路径：

- `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md`，特别是S3b边界、继承合同及分任务验收矩阵。
- `/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_ARCHITECTURE_UPGRADE_SPEC_2026-10-05.md` §17及既定S3任务。
- 本报告§3／§5／§6／§7、永久证据README、mimo v12回应及当前请求。S3b基线为上述r4完整HEAD。

1. **先列生产消费入口再接链。** 队列与条件依赖调度、两类deferred激活、场景转换、proposals[]及有界反馈、PPV1独立runner按原S3b矩阵实施。首消费state／context／hypothesis／ledger守卫继续消费；put_state返回不当ledger证书，恢复不能洗掉坏权威。只读收据不代替完整证明。
2. **化学中心接真实调用链并测异常。** 冻结AtomTool→donor诊断→converter→audit→admission→submit；三个None与缺proof保持unknown。对实际caller补宽捕获负控和合法正控，AuditContractError不得吞成verified／R6／成功提交；R2b映射与构造拒绝分别落字。不改冻结legacy／G2／AtomTool，不借化学评审增加完整机制库。
3. **保留真实预算与恢复语义。** 合成夹具验证预算预约／consume／release不重扣、悬空不默发、身份幂等与并发认领；双独立进程barrier及实际硬杀继续采用执行证据。cache来源／认领分支是否持久化须与实际caller承诺一致；扩大历史保证时登记版本待审。不得宣称外部provider exactly-once或任意SQL并发安全。
4. **runner放开须以接线验收为条件。** 本轮双入口仍fail-closed；S3b接到真实守卫与正负控制后再按任务书开放PPV1路径，legacy行为与identity变化逐项披露。G01继续安全隔离、逐项披露缺席依赖，不套用原环境数字或科学性能。
5. **交付同步P2落字。** 更新11＋1父绿精度、各入口kind／reason层次、未知系数账、omission及声明清单边界、R2b／R1对象范围、条件事实真实性与异常不当R行。未来mimo请求自包含无金标、版本／行号重读、执行类标待验证，不继续追问已关闭scope字面项。新行为对直接基线如实分行为红／字段红／collection红／保持控制，完整输出与SHA归入新批次。

S3b由主会话按任务书派实施agent，本评审未实施。继续不访问真实金标／题面／封存run、判分零LLM、不含S4／S5；本地提交显式git add、不push，完成后再走实施→mimo→Codex独立复审。
