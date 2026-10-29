# pollutant_pathway_v1 S4 回修 r3 正链复审（报告 R4）

日期：2026-10-08，Asia/Shanghai。正链 Codex 主审及三个协作子代理独立执行；不调用外部模型。此文发布前已完成全部必做项，不以主会话或实施方数字代替本审执行。

**最终裁定：S4 通过。PPV1-ISO-01 关闭，P1=[]；C01–C04、S3 已关项保持关闭，S4 完成交接点正式成立。**本次兑现冻结现义；`ppv1-criteria-v1` 正文及 FREEZE_RECORD 不改，不自动宣布新判据版本或启动 S5。

## 1. 固定验收、身份与执行边界

- 实际 HEAD：`a19960f9012ceb326a1c40d5906861f223124946`；直接父：`2ff919fa6ef127d4a477b1b1bb52beb685365a9d`。
- 验收：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R3_2026-10-08.md` §4.4、§7、§8。仅收 PPV1-ISO-01，按实施方已获授权的方案 A 实现既有同位素净变化轴，不追加机制、真实科学性能或 S5 门。
- 主材料：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_REWORK_DELIVERY_R3_2026-10-08.md`；`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_request_r20.md`；`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r20.md`。
- 初始守卫：2026-10-08 23:03:38+08:00，125 项源/测试/文档输入及三个旧永久目录 **2009 文件 SHA**。本轮没有账号额度中断或继承旧轮未完成日志；上一轮中断事实仍留在历史报告，不能冒充本轮执行。
- 子代理分别承担执行全量/父/G01，8+3 同位素及真实对称分支，出口继承与材料互证；均 fresh `/private/tmp` 源码、vendor、metadata 副本，conda `depending43`（Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4），主命令 `-B`、禁 pyc 和 pytest 缓存，子进程缓存例外见 §6。父为 detached 隔离树，同字节测试和父子同根 v3 安全镜像；真实仓树不执行 `tests/` 全量。
- 无金标/题面/封存逐题 run、dependingv4、原 v3 评价资产访问；无外部模型/LLM 判分、push、commit；仅新增本报告及证据目录。

## 2. 独立执行数字与红绿分类

| 项目 | 本审结果 | 口径 |
| --- | --- | --- |
| 当前 PPV1 全量 | **976 passed / 0 skipped，exit 0** | 37 文件，962 既有＋14 新；完整 JUnit、stdout/stderr/argv/env/exit |
| 直接父同字节完整 PPV1 | **15 failed / 961 passed，exit 1，0 collection 红** | 当前测试完整复制，非只挑新增文件；15 红不是 15 个漏洞 |
| 父失败根因 | **5 同位素行为＋2 披露字段/形态＋8 版本相关** | 两披露红仅一条 `KeyError('isotope')`，另一条是缺键断言；8 版本相关是 5 字面量＋3 旧 checker 注册不匹配的间接失败，不能写成 8 字面量或 8 行为翻转 |
| G01 安全隔离 | **1578 passed / 8 skipped / 17 deselected，exit 0** | 235.17 秒；297 输入＝上一轮 296＋新 r3 测试；隔离执行前后与当前批准来源 SHA 全同，8 skip/17 deselect 单列 |
| 旧同位素输入 | **8/8 分案＋3/3 production caller 完整执行** | 原脚本逐字复制 fresh tmp；观察退出 0 不等于所有案被产品接受，逐案裁定见 §3 |
| 对称专项与公开 proof 重算 | **4 对称控制＋4 标签方向控制＋1 篡改拒绝完整执行** | 原8+3合计20条行为输入，raw matcher另记，不是20个漏洞；未执行事件阶段不称通过 |
| 旧出口继承有限复跑 | **两脚本 exit 0** | C02、C04、写前守卫、B4 合法边界的完整 JSON；不虚报旧复合脚本未执行后段 |
| legacy 专项 | **两树四产物逐字节相同；标准52聚合不变** | `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6`，不混用实施方其它序列化聚合 |

G01 缺席披露：v4 parser 对照根缺席 1；v2 provenance/summary 未生成 2；冻结 v3 真实评价依赖缺席 5。17 deselect 为 16 slow 节点＋1 显式排除的 charge/evaluation fixture 节点。逐 nodeid 与理由见 `execution/`；这些依赖未访问，缺席不算通过。输入 SHA 比较针对实际安全白名单，不采用仓内原环境数字替代。工程回归不外推 dev 或 298 科学性能；8+3 探针不与 suite 用例数相加。

## 3. PPV1-ISO-01 逐案收口

公开链仍为真实 AtomTool→供体诊断→converter→audit proof 复算→admission→submit/replay 或真实 production caller。旧输入完全保留，仅加载本轮源码。合成混合例只一致修改工具输出 plain/mapped 产物上的中心外 `S_C_1` 标签；真实 AtomTool 内部先执行正常 C–O 键变，不替换审核结论。

| 旧分案 | 本审观察 | 裁定 |
| --- | --- | --- |
| 纯同位素，中心不覆盖 | `S_C_1` isotope 0→13 进入变化集；center=False、audit violated、R5v；不再落“仅立体”码，探针不提交 | 原归因缺口关闭 |
| 正常键变 | center=True、verified/R6，真实提交/幂等重放保持 | 合法正控保持 |
| 原有 13C 保持的键变 | isotope [13,13] 如实披露，不作为变化；verified/R6、提交保持 | 带标签不一概拒绝 |
| 混合中心外 isotope | changed atoms 含 `S_C_1`，extra_changes 明示 isotope before/after；center=False、violated/R5v，探针不提交 | 原错误 verified/full/R6 关闭 |
| 中心内 isotope | 中心属性含 isotope，范围覆盖时 verified/R6、提交保持 | 许可范围正控保持 |
| 全中心范围控制 | 全部变化已列入中心，direct/verified/R6 保持 | 不新增科学硬门 |
| strict 目标错误 | strict=False，中心 violated/R5v，探针不提交 | 原优先级保持 |
| 非四面体 stereo-only | unknown/R5、原立体理由码和 unsupported 清单保持 | 真立体残差不被吞并 |

三 production 案完整消费真实 donor/converter/audit/admission/writer/complete。正常键变、13C 保持两案仍 submitted/expand/R6。混合中心外案仍可 submitted，但 **admission=retain_conditional/R5v，中心=violated**；事件与生产报告如实记载，不能解读成成功核实，也不能把产品覆盖字段 `full` 的局部覆盖解释成整条证据已全部 verified。该提交是 S3b 已登记的 retain 策略，不为本轮加“所有 violated 禁止留存”的新门。

`_atom_property_diffs` 的 isotope `!=` 比较进入 delta、records、changed atoms；中心内属性和中心外摘要同源披露。公开 audit 的 `_rerun_proof_record` 重跑同一 checker，不只信自报；本轮额外篡改“center=True”证明被结构化拒绝。完整原始工具输出与消费输出、states/context/proof/audit/admission、全业务表前后、schema/产物文本均封存。

### 3.1 对称像同位素敏感性独立裁定

原始 RDKit 自同构：无标 `FCCF` 两个（恒等＋镜像）；单标 `F[13CH2]CF` 仅恒等；双标 `F[13CH2][13CH2]F` 恢复两个。四原子带标 query 对同骨架四原子无标 target 无匹配。

真实 `check_edit_against_donor` 的四分案：无标对称断键、双13C对称断键均 `True/symmetric_equivalent`；单13C破缺对称后的镜像断键为 False，不能借图镜像放行；单13C背景上中心外新 isotope 差异也 False，并公开 isotope extra_changes。具有标签而仍合法对称的正控保留，不能以一概拒绝所有对称分支来换安全。

额外有限公开审核控制：纯同位素且中心覆盖该原子为 verified/R6；13→0 中心外为 violated/R5v；合法 `[2H]OC→[3H]OC` 相同映射 D/T 差异，中心外 violated/R5v、中心内 verified/R6。篡改混合案自报 center=True 时，公开 audit 抛 `AuditContractError/center_evidence_integrity_mismatch`，detail 明示 claimed=True/recomputed=False。该追加篡改控制到审核拒绝即止，未进入事件阶段，不声称其后提交/库操作已执行。

**mimo §5 疑似 P1 按其预设撤回条件撤回。**本裁定依据当前 depending43/RDKit 实测与真实 checker 正负控，不把 raw matcher 局部结论泛化成任意对称算法/未来 RDKit 版本的保证。

主会话旧探针有一处取证精度问题：`[13CH3]CO` query 对 `CO` target 是 3 对 2 原子，负匹配受骨架大小混杂，不能单独证明同位素约束。本审用同骨架、同原子数补证，并用真实对称消费链互证；旧 self-match 正负控制有效，撤回结论仍成立。旧文件不回写，此问题列 P2 取证措辞更正。

## 4. 继承与身份契约

只改 `audit.py` 的诊断实现/披露及 `profile.py` 的注册身份；production/store/search/runflow/endpoint/native_result/native_export/v3_projection/runner 等本批字节不变。全量既有回归及以下有限独立出口控制互证，不以字节不变掩盖同契约新证问题：

- **C02**：删真实已被 payload 消费的 production_report，删 manifest 同 ref，再自洽新 digest，保持 DB/native 不动：先拒、零业务表写、缺席和坏形态保全。其它必要 ref 删除分案也拒；写前删必要 soutc 时零新导出目录。
- **C04**：无 ledger 首消费对未知来源 schema/profile/native_result、缺 native_result 版本/缺 contract_versions、投影自记版本冲突均拒；正常对照可读。
- **B4**：公开 start 注入事件已提交硬停→公开 resume；合法 done expand 无 production_report，有一事件；native 与带/不带 ledger 投影都可读。不能反向补新门要求 done 必有该报告。
- C01/C03、S3 已关组、首消费/恢复、四崩溃/barrier、E01/E02/C06/H04、八 kind、确定性/幂等等沿全量对应回归保持；冻结正文/记录、legacy/AtomTool/G2 不变。

诊断 `ppv1-donor-diagnostic-8→9`、profile `18→19`，审核/准入码表 `-8` 不改。含诊断身份的注册来源块如实变更，旧 checker 不静默当新证据。该登记承载实现语义变化，不能误称行为零变化。父失败的注册相关测试也显示新旧证据不互相冒充。

冻结正文 SHA：`7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`；FREEZE_RECORD SHA：`6e046e2970a102c63e693cebb81f2564b5d79fea1b6e7a776b0fc00c09662610`。本修复落实正文已经承诺的同位素轴，不改变判据定义，因此**不单独触发 criteria-v2**。必要条件 endpoint 阻断的前轮正式裁定不变，本轮没有再次更改它。

## 5. 交付/mimo 互证、P2 与支持范围

交付的 976/1578/297、15 红/961 绿、8+3 前后转向与本审执行互证；红类精度按 §2 更正。实施归档 **48 附件＋3 根控制文件**完整哈希相符；嵌套 runs 的六个 artifact JSON 均实际存在并已显式 force-add 入提交，不是缺席证据。嵌套业务 manifest 均纳哈希，仅排包根控制文件。实施和主会话材料仍按来源标注，不换署成本审执行。

mimo 问题 1–6 的规则判断与代码、公开观察互证到本轮覆盖范围为止；正文问题 5 实为有条件同意，不能把 provenance 的“问题 1~6 全同意”转述成全部无条件。其程序声明“待执行验证”由本审证据补齐本轮固定面；没有代 mimo 宣称执行过，也不采用其独立性背书。代码行号抽查与名称一致，具体区间/片段见 `inheritance/`。

以下归 **P2 后续披露/测试/文字项，不延后 S4、不新增评审门**：

1. 四处 docstring/属性注释补 isotope，同新头注/实际字段一致；profile 新注释“仍未放行执行流，无历史产物需迁移”沿旧文，S3b 后公开 PPV1 start/resume 已开放，应改为旧版本依既有门拒绝，迁移另议。
2. 被增/删标签原子 records 补 isotope，改善原子 presence 摘要可见性。目前 presence 已进 changed atoms，中心外照样拒；不是漏变化后 verified。
3. audit center 检查 `axis_detail` 可携带复算 `extra_changes/center_property_deltas`，便于读者第一眼看到标签轴。完整 diagnostic/proof/production 产物已有，不能说证据不存在。
4. 四个规则级合成例作为后续常驻回归建议；本审已独立补对称与若干方向控制，详见专项，不能把未执行的删标签片段或模型示例都报已验证。D/T 建议串 `[CH3]OH`/`[2H3]COH` 应改合法输入后再做例，不照抄为可执行证据。
5. 主会话方向性 matcher 控制骨架混杂见 §3.1；版本/字段红分类按 §2 落字，非新增程序缺陷。

**交接常驻披露**：isotope 表示的是结构标签整数差异，0=未标；0↔13 不断言样品实测同位素组成或核过程。violated 表示实际变化与声明中心范围不符，不裁定反应化学不可能。中心内可 verified 只认证表示层范围，不能读成酶反应机制已核实。D/T 元素账计 H、身份/同位素轴区分，两个结论不互推。固定 AtomTool 没有 isotope op；合成输出防御验证不证明正常工具会改标签。`self_contained_recompute` 证明输入自洽重算，不认证编辑曾执行、来源真实性、生物可行性或污染物降解性能。

## 6. 永久证据、完整性与如实执行

目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_codex_r4_2026-10-08/`。

- `execution/`：当前 PPV1、父完整红绿、G01 安全白名单/297 SHA 前后/8+17 nodeid、argv/env/exit、schema/runtime、两树 legacy 产物及标准52身份。
- `isotope_contract/`：逐字复制的8+3脚本，全部输入/proof/诊断/audit/admission/提交或不提交/真实 production 留存、前后业务表、对称 raw 与公开 checker 及额外 proof 控制。
- `inheritance/`：旧出口脚本复制及两项完整新执行、C02/C04/B4/写前守卫、材料和行号互证、实施归档 SHA 与 P2 裁定。
- `root_audit/`：125 输入、旧永久2009文件初始/发布前后守卫、来源材料、脚本与只读验证、发布收据及工作树新增两路径核对。
- 根 `manifest.json`/`SHA256SUMS`：覆盖所有实际附件和嵌套 manifest/子包 controls，仅排**根**两个控制文件；子包有独立清单。`report.sha256` 绑定本报告。

执行和证据准备若有修正如实保留：ISO 最初 setup 因仓根没有 vendor 目录退出，尚未执行业务；随后包含 src 内 vendor 的隔离树准备成功，8+3 仅执行一次。继承准备尝试缺席的可选 worker 后纠正、一次辅助 stdin 元数据生成因编码失败后改用正确编码，均未因此重跑产品探针。观察脚本的旧字段/旧 HEAD/历史续跑标志不作为当前 HEAD 或本轮事实；实际身份由本轮运行记录钉住。对称第一次工具调用采用合并输出转录，完整输入/诊断 JSON 和实际命令/exit 保留，不伪造独立 stderr，也不为分流日志重跑。网络口径保持收窄：旧 production 输出 `network_calls=0` 未仪器化，不能当 socket 实测；本审没有宣称全部 G01 子进程网络测量零。

主命令缓存禁用均设置；G01 内个别测试子进程仍留下 **7 个临时 pyc**，当前/父 PPV1 树为0。观察已归档，pyc 不入永久包，297 受控输入及真实仓未改；不写成“全部子进程绝对无 pyc”。

所有写库均在新 tmp；不归档二进制 SQLite/pyc/cache，专项保存全表 JSON/schema/SHA，suite 库的 schema/count/hash 不冒充全行证据。归档后只读核验，不在永久证据原地运行业务脚本。源/旧永久 SHA 与 tracked diff 守卫均不变，仓内只新增两处授权产物。

## 7. 正链最终裁定与 S5 前置交接

**PPV1-ISO-01 关闭，P1=[]；S4 完成交接点正式成立。**先前 C01–C04 与 S3 已关组不重开。方案 A 兑现冻结现义、版本登记及公开重算闭合；对称疑点也由真实分支执行排除，不靠文字中性化或单点字段补丁替代收口。

S5 前置条件维持：另行任务书及用户对题域/留出、统计预注册、阈值/费用、provider、敏感资料外发、teacher裁定等的授权；真实评估继续金标隔离、封存只读、零 LLM 判分、题域数字不外推。当前放行是工程交接，不是污染物降解科学性能通过。S5 交接包应携带 §5 支持范围与遗留 P2；本轮不实施 S5、不自动修改冻结正文或宣告下一判据版本。

## 8. 下一步有限范围

没有 P1 回修提示词，也无需仅为本轮 P2 再追加化学评审轮次。后续 agent 可同步 §5 的非冻结文档/注释、将已执行合成控制转常驻回归，并保留当前 profile/donor 版本门和 retain 策略披露；如要改变冻结语义、生产准入或科学评价条件，另行用户裁定与版本登记。P2 不冒充本轮未闭合的放行条件。
