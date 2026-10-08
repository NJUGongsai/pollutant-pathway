# mimo 化学评审请求 r22:pollutant_pathway_v1 S5a 回修 r1 四组修复后的化学判断面

日期 2026-10-09。本请求**自包含、只含规则级表述与合成例**(如
CCO/CC=O/[H][H]/C/F[C@H](Cl)Br/温度与氧标签),不含金标/题面/
封存逐题 run 数据,不含任何真实 dev/298 指标数值;由用户送 mimo,
回复原文落盘。触发点:AGENTS.md 化学评审三类之 1(需评判化学
结构/条件口径——S5a 回修 r1 改动了评测器 proposed 匹配/分类/写入
规则,冻结前需化学复核)。**评审独立性不做背书;结论采信到与
程序证据互证的程度为止;本请求只问规则级判据,不请求任何执行
声明。所有"已执行"字样的程序事实均标注〔待执行验证〕,mimo 不
复跑代码。**

---

## 0. 背景(一段)

S5a 批次的评测器接口(`ppv1-evaluation-1`)经 Codex 正链复审
(2026-10-09)判为不通过,四组 P1:参考身份 scope 未消费许可
(旁证可升格严格)、条件评测另写简化规则(与冻结判据四冲突)、
必要参考参与节点漏核(空命中被 union 吞)、输出写守卫用未解析
路径名授权(越界写)。本轮回修 r1 按"最小收口"修复,登记为
`ppv1-evaluation-2`(匹配/分类/写侧语义变更不偷换同一已登记
契约;criteria-v1 冻结正文零改动)。请评审以下四个修复面是否
把口径收对了——是否存在"收得过紧导致漏报"或"收得不彻底仍有
化学误导"的结构性缺陷。每面给出修复后规则与合成例;例为合成
规则级(公共链真实生成 run,无金标)。

## 1. 判断面一(修复 S5A-01):参考身份 scope 先消费许可,再授严格档

**修复后规则**:参考节点声明
`structure_identity_scope ∈ {cn_only, partial, unknown}` ⇒
**许可范围封顶**——即使预测侧结构与参考声明内容严格相等
(同源 canonical strict identity 相等),也只计 **CN 旁证桶
(`cn_only`)**,不授 `strict_structure` 严格命中、不进边严格
匹配候选与严格指标;机读披露 `identity_scope_cap`(记录哪些
预测 state 内容严格相等)。scope=`strict_structure` 才允许严格
档。真实严格差异(对映体/同位素/电荷)仍只进旁证;带标签或
有限图不全面拒绝(样本照常评估,条目保留)。

**合成例**:
- 例 1(封顶):参考节点 structure_smiles=`CC=O`、
  structure_identity_scope=`cn_only`(参考来源只声明了 CN 级身份);
  预测 state `CC=O` 内容严格相等 ⇒ 计 `cn_only`(旁证),机读披露
  "内容严格相等被封顶";该节点参与的参考边不再产生严格候选
  ⇒ 落"必要节点未覆盖"分桶,聚合严格边召回归零。
- 例 2(许可差):同一节点若声明 scope=`strict_structure` ⇒
  内容严格相等计 `strict_structure` 严格命中。
- 例 3(正控):全部节点 strict_structure 的合法完整图(根 CCO →
  CC=O 两条备选边)⇒ 两条边严格命中保持,不因本规则收紧而误伤。

**问 1**:①"参考自己声明只够旁证 ⇒ 内容相等也封顶旁证"是否
正确的许可语义?有没有应当**升格**的例外(例如参考声明
`partial` 但缺失的恰是预测侧也不携带的维度)?②封顶后该节点
参与的边落"必要节点未覆盖"桶而非 unmatched——把"参考声明有限
身份"与"预测未命中"分开计数,读数上是否还有误导?③内容严格
相等的旁证是否应该与 CN 级旁证在旁证桶内**再分子桶**(现在同
为 cn_only,仅机读披露区分)?

## 2. 判断面二(修复 S5A-02):条件分类沿冻结同源规则 + 登记映射

**修复后规则**:评测器不再另写字符串首条/`or ""`/字符串区间
解析的简化分类,而是**登记 ConditionScope → 冻结 Requirement/
事实的合法映射**后,调用生产侧同一实现(`path_context` 冻结
判据四的代码)裁决:

- **单位三态**:带量纲键(temperature_C)事实无单位 ⇒ unknown
  (source_unit_unknown);非规范单位(K/F)⇒ unknown(unit_mismatch,
  首版无换算);规范单位才数值比较。
- **absence 保守语义**:同值字符串 known_absent(必需值被同词
  否定)⇒ conflict;**异值字符串/异实体 known_absent ⇒ unknown**
  ("anaerobic 缺席"不证明 aerobic 在场;NO3 缺席不证明 O2 状态);
  **数值/区间 known_absent ⇒ unknown**(单点缺席不推出区间缺席)。
- **多事实保守 unknown**:同键多条相反事实 ⇒ unknown(不首条
  说了算,与顺序无关)。
- **necessity 来源**:essential 无 source_refs ⇒ unknown
  (necessity_unsourced_not_gating)。
- **value_basis 由映射声明**:区间键 "lo-hi" 字符串规范为 {lo,hi}
  区间(range)、单数值为点值(point)、其余字符串按定性标签
  (label;注册表为空 ⇒ unknown);物种/枚举/matrix 键字符串按
  entity。**缺表示能力 ⇒ unknown/unsupported 族 + 机读披露**
  (冻结键集外的键、无法表示的要求值/事实条目),不判冲突/相容。
- **要求侧 status=known_absent**(负要求):冻结 Requirement 无该
  表示 ⇒ **单列 `requirement_status_not_representable`,不伪称
  冻结矛盾、不推断负要求**(语义待用户/teacher 裁定)。

**合成例**(全部 20 案已程序核验与冻结同源一致〔待执行验证〕):
- 温度:要求 20–30°C;事实 25°C ⇒ compatible;事实 25 无单位 ⇒
  unknown;事实 30 K ⇒ unknown(不换算直比)。
- 氧:要求 aerobic;事实 aerobic present ⇒ compatible;事实
  anaerobic present ⇒ essential_conflict;事实 aerobic known_absent
  ⇒ essential_conflict(同词否定);事实 anaerobic known_absent ⇒
  unknown(异值缺席不判定)。
- 多事实:[anaerobic present, aerobic present] ⇒ unknown(两序
  同判)。
- 数值:要求点值 0°C、事实 0°C ⇒ compatible;要求 -5–10°C、
  事实 0°C ⇒ compatible;要求 20–30°C、事实区间 22–26°C ⇒
  compatible。
- matrix:要求 soil、事实 activated_sludge ⇒ unknown(未注册标签,
  文本不等不证明不相容)。

**问 2**:①修复后评测侧与生产侧用**同一实现**裁决条件(不再有
第二套规则)——该同源闭合是否足以消除"同名 essential_conflict
两义"?②负要求单列 not_representable(不判冲突/相容)是否正确,
还是应该按对称语义(要求 absent + 事实 absent ⇒ 相容;要求
absent + 事实同值 present ⇒ 冲突)定义?若定义,是否属于 teacher
裁定而非评测侧自行发明?③区间键要求字符串规范为 {lo,hi}、单
数值为点值——该映射限定是否引入了"把声明者意图 point 写成
range"的错配风险?④缺表示能力(键集外/无法表示条目)按
unknown 族披露是否足够,还是应有专门的"不可评估"分母口径?

## 3. 判断面三(修复 S5A-03):必要参考节点空命中不被 union 吞

**修复后规则**:每个**声明的必要 from/to 参考节点**都必须有
许可的严格命中,该参考边才可产生严格候选;任一必要节点空命中
⇒ 候选不生成(空集合不并入整侧 union、不被删除),边落
**未覆盖分桶**并逐节点机读披露缺口(节点/侧/节点档位)。参与
物覆盖比较因此消费**完整声明节点集合**——不能只证明缩小后
子集精确。仅 participants 列表新增而 from/to 未列的节点**不进门禁**
(该 schema 歧义评审单列 P2 待裁定);不新增角色/系数/计量门。

**合成例**:
- 例 1(核心反例已翻转):原合法 declared_complete 边 A(根
  CCO)→ C(CC=O)新增**必需反应物**节点(结构 C,预测侧无命中);
  预测真实事件 CCO→CC=O 与其余节点严格匹配——修复前该边仍
  `matched_strict`(必需节点空命中被整侧 union 吞、缩小集合标
  exact);修复后该边落"必要节点未覆盖",另一条未受影响的边
  严格命中保持。
- 例 2(product 侧同构):新增**必需共同产物**节点(结构 C)于
  to_node_ids ⇒ 同样不 strict。
- 例 3(联动):必需节点同结构但声明 scope=cn_only ⇒ 经判断面一
  封顶后同样不 strict。
- 例 4(正控):事件侧多带溶剂/缺共同产物 ⇒ 覆盖失配披露桶
  (partial_subset/superset)保持,不被新规则吞掉。

**问 3**:①"每个声明必要节点须严格命中才可完整 strict"是否
正确口径?预测事件包含参考未声明的额外参与物(超集)仍不进
严格——对 declared_complete 参考这是否过严(参考作者漏画 H₂O
之类)?②participants-only 节点不进门禁(P2 待裁定)是否留下
可钻的表示漏洞(把必需参与物只写进 participants 就绕过核验)?
③必要节点未覆盖桶与参考覆盖不足桶、预算未展开桶三分——读数
是否会混淆"模型没做到"与"参考没画全"?

## 4. 判断面四(修复 S5A-04):写边界根规则(工程,无化学判据,仅完整性)

**修复后规则**:含金标评测产物落盘时,核验与写入使用**同一
解析后实际规范路径**(resolve 一次;授权判定/建目录/写文件三处
同一路径):relative target 基准 = 相对 cwd 解析,解析后逃出声明
repo_root(错 cwd/绝对越界/任意层 symlink 逃根)⇒ 先拒、零新
文件;根内再核授权 gitignored 根;未声明 repo_root ⇒ 含金标一律
拒绝(授权判定必须有一个可核验的根);普通非敏感写入不受限。
回执 path = 实际写入路径。

**合成例**:显式 repo_root=A、cwd=B、相对授权名路径(解析落
B)⇒ 拒零新文件(修复前真实写 B 并返回回执);A 内授权名目录为
symlink 指向 A 外 ⇒ 拒零新文件;合法 A 内相对授权路径 ⇒ 接受
(合成占位内容 synthetic-placeholder-not-gold)。

**问 4**:〔工程面,请只作完整性检查〕该根规则是否有残留漏洞
(如相对基准选择、并发 symlink race、无 root 一律拒)会导致
金标内容泄漏到普通目录?不要求新增 DLP/沙箱。

## 5. 请求汇总

| 面 | 修复 | 关键问 | 程序事实 |
|---|---|---|---|
| 一 | identity scope 许可封顶(节点→边→聚合) | 封顶语义/例外/旁证子桶 | 六 scope 合成案翻转、合法 strict 正控保持〔待执行验证〕 |
| 二 | 条件沿冻结同源 + 登记映射 | 同源闭合/负要求/映射限定/不可评估口径 | 20 合成条件案与冻结同源逐案一致〔待执行验证〕 |
| 三 | 必要节点闭合(空命中不被 union 吞) | 过严风险/participants-only 漏洞/三桶读数 | 两核心反例 + 联动变体翻转、覆盖失配正控保持〔待执行验证〕 |
| 四 | persist 同一实际路径根规则 | 完整性残留 | 五合成写边界案 2 翻转 2 保持 1 正控〔待执行验证〕 |

请逐面回答:该修复是否把口径收对了?哪里收得过紧/不彻底?
有没有应单列的化学误导风险?以上为完整评审请求;mimo 回应原文
将落盘 `docs/`,结论按"采信到与程序证据互证为止"处理。
