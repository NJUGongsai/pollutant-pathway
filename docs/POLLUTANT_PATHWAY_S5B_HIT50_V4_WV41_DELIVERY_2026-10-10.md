# PPV1 S5b HIT50 v4 W-V4.1 交付书 —— RHEA 主语料 recorded 直通接线
# (2026-10-10)

状态:`implementation_ready_for_review`。

任务依据:`docs/TASK_V43_PPV1_S5B_HIT50_V4_DRAFT_2026-10-10.md`
§10(用户六决策 ①②③④⑤⑥)+ §11(基线回填 + 实施授权)。本交付
= 该任务书 W-V4.1(接线主包 + 接线必需的最小编译支持),不含伴行包
①(编译墙深层再攻,列 v4b)、②(stereo 设计轮)、④(语料修复轮)。

- 实际开工 HEAD:`376ee0c`(v3 收口提交;任务书 §11 基线);
  实施期工作树:3 个已跟踪文件改动 + 1 个新测试文件
  (改动集与 G01 脚本强制披露一致,见 §八);
- 零真实模型调用、零花费、零网络;不 push;金标/题面/封存逐题 run
  零读取(语料消费沿 manifest/哈希审计,授权沿 §10 决策④确认);
- 判据零触碰:strict 身份/CN 含义、participant 集合语义、
  match_reference_edges、主 K 候选定义与 (created_at, event_id)
  顺序、分母 298、失败规则、S5B_PASS_LINES 全部未动;
  `compile_recorded_reaction`/`infer_reaction_mapping`/
  `compile_donor_template` 判据零改动(corpus 记录走同一入口)。

## 一、状态矩阵

| 项 | 状态 | 证据 |
|---|---|---|
| W-V4.1 corpus 装配入口 + sha 锚定回读 | 完成 | `recorded_source.load_corpus_index`;负控①(§五) |
| 组分级 + CN 宽检索 + strict/CN 分层(决策①②) | 完成 | `find_corpus_recorded_exact`;负控② + 分层正控 |
| 共底物声明(决策②) | 完成(spec 级) | 候选/spec `co_substrates` + `corpus` 元数据;参与物级属设计件(§十 R2-2) |
| 双向保留 + 通配拒因(决策③) | 完成 | RL/LR 双方向供给正控 + `unsupported_wildcard_atom` 行级拒 |
| builder 池接线(池策略升版) | 完成 | `s5b-pool-policy-2`;EAWAG 面/序零变化(单测) |
| 11 类负控 + 正控族 | 完成 | `tests/test_ppv1_s5b_hit50_v4_wv41.py` 18 个全绿 |
| 端到端合成批(builder→池→runflow→执行→事件) | 完成 | e2e 测试(scripted 首池模型,零真实网络) |
| 池深/空池率前后对照(298 底物) | 完成 | §六(零模型离线探针) |
| 定向 + 全量 + G01 + 父基线红绿 | 完成 | §七(四组数字) |
| mimo r30 采纳注记 | 完成 | §十(回应已落盘,逐条采纳/不采纳+理由) |
| corpus 记录编译成功率 | **unknown(如实)** | §六失败直方图为 298 检索面实测;全库编译率未测(任务书 §4.6 边界) |

## 二、开工语料事实独立复核(沿 §7 探针口径;只读)

命令:`~/miniconda3/envs/depending43/bin/python -B
/tmp/s5b_v4_wiring_probe/corpus_facts.py`(仓库根;脚本与输出留存
`/tmp/s5b_v4_wiring_probe/`;strict/CN 用仓内同源函数
`chemstate.strict_identity_of`/`domain.identity.cn_identity`;
只读 run_inputs 的 `substrate_smiles` 字段,金标零读取):

- corpus_v1 43,177 行 = RHEA 37,100 + enviPath 6,077;
  18,550 唯一 master × 恰两行(LR 18,550 / RL 18,550,逐对核验
  LR+RL 恰双行);sha256 `186a1dad…` = MANIFEST;donor_index
  95,782 行 sha `e2287aa2…` = MANIFEST;
- atom_mapping 全 null、mapping_status 全 'absent'(43,177/43,177);
  含 `*` 通配 8,502 行(donor 侧 47 / 产品侧 47 / 双侧 8,408);
- **新增披露(草案 §7 未列)**:①enviPath 5,497 带产物行的
  `provenance_sha256` 为 null(RHEA 全有;educt-only 580 行反而
  有)⇒ 负控⑨拒因面实测存在;②enviPath 303 个 record_id 跨行重复
  (最大 12 行同名)⇒ corpus 行唯一键必须行号化
  (`record_id@L<line_no>`);③donor_index 与 corpus
  (record_id,组分)对集不完全相等(95,782 vs 95,783,且组分多重性
  丢失)⇒ 装配入口直接读 corpus_v1 自建索引(单文件单 sha,无跨文件
  join 歧义)——理由见 §四;
- 298 题底物覆盖复算(题级):EAWAG 严格 147 / CN 182;corpus 整串
  严格 159 / 整串 CN 209 / 组分严格 231 / 组分 CN 273;
  147⊂159⊂231 复核 True —— 与任务书 §7 全部吻合。

## 三、共用入口矩阵(任务书 §3;每入口消费的身份/事实/版本/拒因)

| 入口 | 消费 | 本轮变化 |
|---|---|---|
| `env_asset_root.resolve_and_verify`(v3 冻结,只 import) | corpus_v1/donor_index/library 路径+SHA 身份块 | **零改动**;corpus 身份唯一来源 = identity_block 现有键 `corpus_v1_path/sha256`(无需新哈希机制,决策④授权链) |
| `recorded_source._corpus_identity / load_corpus_index`(新) | corpus 库身份 + sha 锚定逐行回读 | 新装配入口(同款 fail-closed):缺键 ⇒ `corpus_identity_missing`;实际 sha ≠ 身份记录 ⇒ `corpus_hash_mismatch`(负控①);进程内缓存;行键 `record_id@L<行号>` |
| `recorded_source.find_corpus_recorded_exact`(新) | 检索 + strict/CN 分层主入口 | CN 宽检索(决策①)+ 组分级(决策②)+ 双向保留/通配拒(决策③);身份比较同源调用 `strict_identity_of`/`cn_identity`,不另写比较器 |
| `recorded_source.find_recorded_exact`(EAWAG) | EAWAG 检索 + 分层 | **零改动**(字节级不动;EAWAG 面/序保持,单变量归因前提) |
| `recorded_source.infer_reaction_mapping / compile_recorded_reaction` | 推断映射 + 编译 + 产物多重集 gate | **判据零改动**(corpus 记录同入口;`mapping_origin=inferred` 强制;预算/歧义披露/有界键差沿用) |
| `s5b_builder.default_pool_provider` | recorded 池槽 | 通道 1b(corpus)追加在 EAWAG 候选后;`S5B_POOL_POLICY_VERSION` 升 `s5b-pool-policy-2`;`corpus_channel` 开关仅供消融(生产默认 True) |
| build 侧 `compile_failure_histogram` 聚合 | 编译失败直方图 | corpus 侧拒因类如实分层(通配/共底物链上诚实拒/charge/stereo/无产物/provenance/原生映射冒充),经 pool 诊断与批 manifest 落账 |
| worker/runflow 事件链 | plan.pools 消费 | **零改动**(worker 无感:池供给在 builder 层;spec 附带 `corpus` 元数据随 plan 冻结,prepare_hypothesis 忽略未知字段,e2e 走通) |

## 四、W-V4.1 实现要点(判据与身份语义全部沿用现行实现)

1. **检索语义冻结登记先于接线**(§1 硬条款):
   `CORPUS_RETRIEVAL_VERSION="s5b-corpus-retrieval-1"` +
   `CORPUS_RETRIEVAL_SEMANTICS` 常量块(CN 宽检索/strict 分层
   不升格/组分级+共底物声明/整串优先/通配行级拒/双向按行书写/
   全 inferred/records 级 provenance 存在性披露),冻结依据
   = §10 决策 ①②③,单测钉住(test_wv41_semantics_frozen)。
2. **装配入口**:`load_corpus_index` 单遍读 corpus_v1 自建
   (a) 适配记录(行号/record_id/record_key/source_type/master_id/
   direction/ec/donor_A_smiles/donor_components/products(完整净
   产物集合,`product_components` 优先、缺则按 `product_B_smiles`
   组分分离)/provenance/mapping_status/atom_mapping);
   (b) 组分 CN 索引(同源 `cn_identity`;通配组分不索引=天然
   不可检索)与多组分整串 CN 索引(单组分经组分索引承载整串语义)。
   不复用既有 `donor_index.jsonl` 的理由:corpus 记录必须整行回读
   (产物/方向/provenance 都在 corpus_v1),donor_index 是另一份
   派生文件——跨文件 join 键(record_id)在 enviPath 侧不唯一
   (303 重复),且 donor_index 丢组分多重性、缺 1 对、含 477 个
   `donor='*'` 需另过滤;单文件单 sha 自建索引 = 身份唯一、无
   join 歧义(决策⑤最小接线内的诚实选择)。
3. **检索/分层/适配**(决策 ①②③,§三入口矩阵):
   - CN 宽检索:底物 CN == 组分 CN 或整串 CN ⇒ 命中(strict ⊆ CN);
   - 分层:匹配侧严格身份==底物严格身份 ⇒ strict;CN 同 strict 异
     ⇒ cn_candidate 不升格(与 EAWAG 同源判据);
   - 匹配侧:单组分 donor/整串命中 ⇒ kind=whole(co_substrates 空,
     "整串语义下声明退化为空集");多组分 ⇒ kind=component,其余
     组分声明为共底物/条件参与物(不静默丢弃、不冒充单底物反应;
     声明携带组分 SMILES + 严格身份);
   - 行级拒因:通配(任一侧含 `*`)⇒ `unsupported_wildcard_atom`;
     原生映射冒充(mapping_status≠absent 或 atom_mapping 非空,
     corpus_v1 全库事实)⇒ `corpus_native_mapping_claimed`;
     provenance 缺 ⇒ `corpus_provenance_missing`;无产物 ⇒
     `record_missing_or_incomplete`(educt-only/no-structure 同款
     诚实拒);
   - 编译:匹配侧(整串或组分)→ 记录全量产物,走**同一**
     `compile_recorded_reaction`(完整净产物集合核 = 产物多重集
     gate;共底物来源组分无锚/失配 ⇒ 诚实拒——本轮未做"声明式
     拷贝进事件"的 gate 扩展,见 §十 R2-2);
   - 方向:按各自行书写编译(`donor_A→product_B`;direction 为
     记录声明,RL 行书写方向=生化反方向);master 双行均保留为
     候选(双方向分层引用);同一 master 双行命中仅诊断披露
     (`n_master_multirow`);同净反应双槽由池侧同签名去重防
     (W4 既有机制,单测证:master 重复双行 ⇒ 池单槽 + 合并
     provenance 留痕);
   - 候选序(确定性):(tier, 整串<组分, 行号, 组分序);
     max_reactions 候选数截断(与 EAWAG 同语义);行级拒因对检索面
     全量计数(不占候选名额)。
4. **池接线**(s5b-pool-policy-2):通道 1b 在 EAWAG 候选后追加
   corpus 候选(EAWAG 引擎 lookup 序零变化——单变量归因:corpus
   只增不删,同净反应签名合并不双槽);池诊断新增
   `corpus_diagnostics` + `n_corpus_strict_exact`/
   `n_corpus_cn_candidate`,随 build_question_batch 落批 manifest;
   corpus 身份缺失 ⇒ fail-closed 抛错(不静默降级为无 corpus 通道,
   决策④授权链纪律)。

## 五、合成正负控(11 类 + 正控族;`tests/test_ppv1_s5b_hit50_v4_wv41.py`,18 个)

夹具纪律:合成小分子(乙醇/丙醇/乙酸乙酯级,沿 W2 既有夹具纪律),
与真实 298 金标零重叠;真 corpus 实盘用例只读、资产缺席则 skip。

**正控族**:
- 整串严格(RHEA 同构):strict 分层 + 推断映射编译 + 公共链执行
  (`execute_atomtool_expansion` 中心/严格目标核对);
- **组分级 + 共底物声明**(决策②核心正控):底物=donor 组分 1
  (乙酸乙酯),水组分声明为共底物(strict 身份 `O`),编译按完整
  净产物集合核——执行组分 == {乙酸, 乙醇} == 记录全量产物;
  spec `corpus` 元数据携带声明(随池入 plan.pools 冻结);
- **RL 方向 + 双向保留**(决策③):master 90005 LR(裂解)/RL
  (缩合)双行各自供给——底物命中哪侧 donor 就按该行自身书写编译;
  RL 行 e2e(乙醇+共底物乙基声明 → CCOCC);酯水解 master 的 RL
  行(酸侧组分)检索面命中、按自身书写编译(不冒充 LR 侧);
- 授权语料实盘:真 corpus_v1(43,177 行)装配 + 真实 master 10000
  行(戊酰胺 + H₂O 共底物,ec 3.5.1.50,LR,strict 组分级)检索
  分层;水解记录电荷编辑不支持 ⇒ 诚实拒如实(非接线缺陷);
- 池接线:EAWAG 面序保持 + corpus 追加序 + corpus_channel=False
  消融形态(纯 EAWAG 面)+ corpus 全失败诚实空池。

**负控族(W2 七类全保留 + corpus 特有四类,合计十一类)**:

| # | 类 | 拒因/断言 | 测试 |
|---|---|---|---|
| ① | 源哈希篡改(corpus sha≠identity;缺 corpus 键) | `corpus_hash_mismatch` / `corpus_identity_missing` fail-closed | neg1 |
| ② | CN 同而 strict 异(立体) | `recorded_cn_candidate` 不升 strict;n_strict=0;编译层 `stereo_edit_unsupported` 如实 | neg2 |
| ③ | 方向反(RL 行不冒充另一侧书写) | RL 行按自身 donor→products 编译;断言匹配侧与方向字段 | rl 正控 |
| ④ | 另一底物/不可解析底物 | 检索面空(n_matched_rows=0 / substrate_unparseable) | neg3 |
| ⑤ | 过滤单产品卡冒完整 | `product_set_mismatch`(同 EAWAG 编译层判据) | neg5 |
| ⑥ | 缺产物(educt-only/no-structure) | `record_missing_or_incomplete` | neg6 |
| ⑦ | 映射枚举触顶 | `mapping_enumeration_truncated`(monkeypatch 预算,同 v3 wv2 口径) | neg7 |
| ⑧ | unmapped 冒原生映射来源 | `corpus_native_mapping_claimed`;全部 compiled spec `mapping_origin==inferred` | neg8 |
| ⑨ | provenance 缺失 | `corpus_provenance_missing`(实测 enviPath 5,497 行形态) | neg9 |
| ⑩ | 通配行 | `unsupported_wildcard_atom` 行级拒(donor 侧通配不进检索面=天然不供给,如实分层) | neg10 |
| ⑪ | master 双向重复/方向冒充 | 双行各成候选(分层引用)但池侧同签名去重单槽+合并 provenance;诊断 `n_master_multirow` | neg11 |

## 六、池深/空池率前后对照(298 题底物;零模型离线探针)

命令:`~/miniconda3/envs/depending43/bin/python -B
/tmp/s5b_v4_wiring_probe/pool_depth_v3v4.py`(仓库根;真引擎
`get_engine(resolve_config())`;v3 臂 = `corpus_channel=False` 单变量
对照;只读 run_inputs `substrate_smiles`;结果留存
`/tmp/s5b_v4_wiring_probe/pool_depth_result.json`)。

**池深/空池率前后(单变量对照:v3 臂 = corpus_channel=False)**:

| 口径 | v3 臂 | v4 臂 |
|---|---|---|
| 池深 mean / median / max | 0.477 / 0 / 4 | **0.570** / 0 / 4 |
| 空池率(空池题数) | 64.43%(192/298) | **61.41%(183/298)** |
| 池直方图 0/1/2/3/4 | 192/81/19/1/5 | 183/80/24/2/9 |
| 池槽净增题数 / 净失题数 | —(基线) | **+21 / 0**(只增不减,单变量兑现) |

**corpus 检索面 → 供给面(漏斗,298 题逐题;候选上限 raw_top=24)**:
- 检索面:匹配行 9,712(行级);**256/298 题**有 ≥1 corpus 候选;
  其中 **199/298 题**有 ≥1 strict 层候选;
- 候选面(行级拒因后进候选):1,421 个(strict 846 / cn 575);
- **供给面(编译入池):42 个 compiled corpus spec,分布于
  33/298 题**(tier:strict 38 / cn 4;整串 14 / 组分 28;
  方向 LR 17 / **RL 25**——RL 供给过半,mimo R2-3 的"反向书写
  不是方向性证据"警示句适用面大,如实披露);
- 池槽兑现:21 题池深净增(最大 +2;0 题池变小);9 题脱离空池;
- 同 master 双行命中:22 题(诊断披露;同净反应由签名去重防双槽)。

**corpus 侧失败直方图(全事件计数;诚实 unsupported 清单——
编译墙教训前置)**:unsupported_wildcard_atom 1,869(行级,最大类
——通配行经干净组分检索到即拒)、corpus_provenance_missing 371
(enviPath 5,497 行实测形态)、stereo_edit_unsupported 310、
mapping_enumeration_truncated 275、new_atom_placement_incomplete
236、no_alignment 170、new_atom_charge_unsupported 149、
record_missing_or_incomplete 143、charge_edit_unsupported 104、
no_structure_correspondence 73、transform_no_change 27、
product_set_mismatch 19、ambiguous_mapping 3、
aromatic_new_bond_unsupported 10。

**诚实结论(编译墙先验兑现)**:候选面编译通过率 42/1,421 ≈
**3.0%**——corpus 记录(多组分 donor、全量推断映射、通配行)的
编译失败面与 EAWAG 先验(54.4%)同向且更厚;**检索命中 256 题
≠ 供给 33 题 ≠ 命中数**;42 个供给 spec 中 38 个 strict 层、
覆盖 33 题——这是 v4 新批新增大供给面的**上界**,净命中以新批
同口径零 LLM 判分为准(任务书 §0.1 外推纪律);池深 0.477→0.570
(+0.093)与空池率 64.4%→61.4% 是供给侧中间指标,不冒充科学
达标。RHEA 全库编译成功率(不设 per-题 24 候选上限)仍未测,
按 unknown 登记(§一矩阵)。

**共底物构成谱(补充探针,mimo r30 G2 不确定项)**:
`cosubstrate_profile.py` —— 组分 CN 匹配面 273/298 题复算(与
任务书 §7 组分 CN 273 一致);行级拒因过滤后供给面记录题 267;
其中共底物**全部为零碳书写平衡项**(H⁺/H₂O/CO₂/O₂ 等)的题 63,
**含有机/辅因子样共底物**(NAD(P) 系 1138+245+111 次高频、谷氨酸、
铵、铁硫簇等)的题 204;组分级频次 balance_like 4,878 /
organic_like 11,052。**诚实结论:组分级供给面的 76%(204/267)
携带有机共底物——该子集在现行 P1 参与物集合语义下事件侧将判
partial(§十 R2-2/R2-4 采信注记),不是 strict 可达外推面**;
+84 是检索供给面数字,非命中数字(任务书 §0.1 边界重申)。

## 七、回归与隔离证据(四组)

| 组 | 命令 | 结果 |
|---|---|---|
| 定向(新文件) | `pytest tests/test_ppv1_s5b_hit50_v4_wv41.py -q` | **18 passed**(含真 corpus 实盘用例) |
| 定向(既有族) | `pytest tests/test_ppv1_s5b_hit50_{w23456,v3_wv1,v3_wv2,v3_wv3,v3_wv6}.py + s5b_runtime + v3r1/r2/r3 -q` | 43 + 144 passed(零回退;唯一改动 = w23456 版本字面量 s5b-pool-policy-1→-2) |
| 全量 | `pytest tests/ -q -m "not slow"` | **1976 passed / 0 failed / 16 deselected**(父基线 1958 + 18 新;≈5.4 分钟) |
| G01 隔离 | `/tmp/safe_g01_s5b_hit50_v4_wv41.py --repo … --out /tmp/g01_s5b_hit50_v4_wv41_r2` | **1965 passed / 10 skipped / 17 deselected, exit 0**(338.2s;= r3 基线 1947 + 18 新,精确兑现预期;328 输入 SHA 前后复验零失配;改动集脚本强制核对 = 预期 3 改 + 1 新与实测**逐项一致**;7 个游离 .pyc 如实记录;谱系 v3r1→r3→v4;禁写仓内/永久证据目录;_r2 = 交付字节终版复跑——一次诊断字段更名后重跑,首次运行输出 `/tmp/g01_s5b_hit50_v4_wv41/` 保留不删,两次均 1965/10/17) |
| 父基线红绿 | 新测试文件在父 HEAD `376ee0c` 隔离 worktree(`/tmp/s5b_v4_parent_wt`) | **红(18/18 收集失败)**:失败形态 = `ImportError: cannot import name 'CORPUS_RETRIEVAL_SEMANTICS'`(即旧缺陷本身:corpus 通道不存在);修改后的 w23456 版本字面量测试在父 HEAD 红(父为 pool-policy-1)、行为测试仍绿(池行为未变);import 前显式 sys.path.insert 指向 worktree src 并断言 `__file__`(防 pip 污染已验证) |

## 八、本轮改动清单(提交内容)

- `src/pathway_v43/pollutant/recorded_source.py`(+~460 行):
  模块 docstring 扩 W-V4.1 纪律段;`CORPUS_RETRIEVAL_VERSION/
  CORPUS_RETRIEVAL_SEMANTICS`(冻结登记);`_corpus_identity/
  load_corpus_index/reset_corpus_cache`(sha 锚定装配入口);
  `find_corpus_recorded_exact`(检索/分层/适配/拒因主入口)+
  `_corpus_candidate`;EAWAG 路径(find_recorded_exact/
  load_library_index/compile_recorded_reaction)字节级零改动;
- `src/pathway_v43/pollutant/s5b_builder.py`(+~40 行):
  `S5B_POOL_POLICY_VERSION` 升 `s5b-pool-policy-2`;通道 1b
  (corpus 直通,`corpus_channel` 消融开关);池诊断新增 corpus 计数;
- `tests/test_ppv1_s5b_hit50_w23456.py`(4 行):版本字面量
  s5b-pool-policy-1 → -2(池策略升版测试侧同步,父 HEAD 红即证);
- `tests/test_ppv1_s5b_hit50_v4_wv41.py`(新,~530 行):§五全部
  正负控 + 池接线 + 端到端;
- 本交付书 + mimo r30 请求/回应引用(回应原文 `docs/
  mimo_ppv1_chem_review_response_r30.md` 已由主会话落盘,本轮只读
  引用不改);
- 探针证据(语料复核/池深对照/共底物谱/G01)留存
  `/tmp/s5b_v4_wiring_probe/` 与 `/tmp/g01_s5b_hit50_v4_wv41/`
  (易失;关键数字已录本交付书,脚本可复跑)。

## 九、金标边界自查

- 预测侧零金标:corpus 通道与池深探针只消费 run_inputs 的
  `substrate_smiles` 字段;金标/products/旧答卷/封存逐题 run 零
  读取;判分零 LLM;合成夹具与真实 298 金标零重叠(夹具纪律);
- 语料消费沿授权资产包(manifest/哈希,§10 决策④);corpus
  消费入口 sha 锚定后回读,身份不一致 fail-closed;
- 参考图/题面承载物零触碰(本轮不重建批;builder 参考图路径零
  改动);e2e 合成批输出落 tmp(仓外);
- 冻结判据零触碰(§三入口矩阵);scorer 匹配排序/参与者集合语义/
  S5B_PASS_LINES 零改动;池策略升版是供给侧版本号,非判分尺子;
- 外推纪律:§六数字全部是检索/编译/池面聚合计数,非命中数;
  编译成功率未测面按 unknown 登记(§一矩阵);对外数字带题域标签
  (298 题域,不外推 dev)。

## 十、mimo r30 采纳注记(回应已落盘 `docs/mimo_ppv1_chem_review_response_r30.md`;采信到与程序证据互证为止)

评审通道 A 只读;回应按请求 G1–G4 逐条作答(其头部"三判断面"为
模板残留,其自披露已澄清,按请求原文采信)。逐条:

**G1(CN 检索 + strict 编译核;总评"有条件同意")**
- R1-1(CN 候选报告层警示标签):**采纳(文档层)**。本交付与后续
  报告凡出现 `recorded_cn_candidate` 计数处,配机读警示:
  "CN 同 = 电荷归一 + 立体盲同构,包含质子化态变体与全部立体异构体
  (含非对映体——化学上不同物质),不构成'同一化合物'声明,不得
  读作 strict 供给"。代码层 tier 字段已机读,无需改码。
- R1-2(`cn_identity` 电荷归一失败回退计数):**登记待复审(本轮
  不实施)**。理由:计数须在冻结口径模块 `domain/identity.py` 内
  埋点或复制其 try/except 语义(第二套实现,违反单一判据源纪律);
  风险有界(CN 候选不升 strict、终核走 strict 产物多重集 gate)。
  列 v4b 工程选项。
- R1-3(CN 增量不计 strict 外推):**采纳(文档层)**——§一矩阵与
  §六已按 unknown/非外推落字;任务书 §0.1 同款。
- G1 事实核(互证):"CN 永不升 strict 是代码事实"——与本轮
  负控②单测断言一致(成立);"互变异构不被 CN 合并、盐式大体不
  合并"——与 `domain/identity.py` 实现一致(Uncharger 无互变
  归一、不断反离子;成立)。**修正采信:CN 扩覆盖机理叙述限定
  "质子化态 + 立体"两类,不提互变异构**(本轮交付书全文遵守)。
- G1 风险 2(EAWAG 侧"索引键归一差异"同入 cn_candidate 类目):
  属 EAWAG 路径既有行为——**登记待复审**(拆分需改 EAWAG 路径,
  违反本轮 EAWAG 零字节改动纪律)。

**G2(组分级 + 共底物声明;总评"有条件同意",P1 级条件 R2-2)**
- R2-1(角色术语拆分:计量性共底物=cosubstrate、仅质子/水/CO₂
  可称条件参与物):**登记为设计轮条款(本轮不改码)**。理由:角色
  拆分需共底物分类判据(NAD/ATP/CoA/GSH 白名单级设计件)= 任务书
  §4.2 明文"共底物↔共产物对应判据属设计件,须交设计复审";本轮
  声明字段沿用用户决策②原词(共底物/条件参与物),不静默引入第二
  套角色判据。设计轮须按 R2-1 落字并拆分。
- R2-2(**P1 级**:共底物须显式进事件参与物、禁条件字段单处置、
  禁共底物原子经 add_atom 伪装新增、gate 扩展须同源带负控、partial
  子集占比按 unknown 登记):**登记为设计冻结前置条款(本轮不改
  码),程序证据如下**:(a) 本轮实现选择的是 mimo 列出的"诚实拒"
  分支——共底物专属产物组分(如 NADH)经 add_atom 无锚 ⇒
  `new_atom_unanchorable`/产物集失配 ⇒ 拒,不产生"A→P+NADH"
  型事件;gate 零扩展(判据零改动);(b) 共底物键合原子(如水解
  的酸 OH)经 add_atom 与 EAWAG 既有水解正控(W-V2,v3 交付 §五)
  同一机制,且本轮**额外**携带共底物声明(比 EAWAG 先例多一层
  provenance);该语义变化属设计轮裁定范围,不在工程轮静默改;
  (c) partial 子集占比已按 mimo 建议做了只读聚合计数(§六共底物
  构成谱:204/267 含有机共底物)——按 unknown/非外推登记;
  (d) "共底物只写条件字段则判据二 unknown 无守门"的闭环提醒
  **成立并采纳为设计轮第一优先问题**(§十一 #1)。
- R2-3(RL 行方向披露):**已实现(等价字段)**——候选/spec 携带
  `direction`(LR/RL)机读字段 + `master_id`;警示句采纳落字:
  "RHEA 行方向是书写声明,不是方向性/热力学有利方向证据;方向反
  候选不得表述为'该酶的主要方向'"。
- R2-4(T1′ 边界互引:辅因子恒不忽略、白名单仅无机小分子):
  **采纳(文档层)**——落字重申:组分级供给上线后 partial 桶膨胀
  是诚实后果;coproduct_ignore_tier 既有边界(r28 裁定)不得因
  "完整产物集语义"倒逼放宽;本条列入 §十一 #2 防滑坡。

**G3(双向行/通配行/推断映射守门;总评"三项全部有条件同意")**
- a) 双向行:判分侧别敏感、同净反应签名不同槽——与实现一致
  (互证成立)。`opposite_direction_no_alignment` 单列:**登记
  待复审(带程序更正)**:本轮检索按 donor 侧匹配,另一方向行
  通常**不进检索面**(底物不在其 donor),mimo 设想的"另一行
  no_alignment 灌水"形态只在同 master 双行均命中时出现
  (实测 `n_master_multirow` 见 §六);直方图语义已如实。
- R3-1(通配拒因三子类细分):**登记 v4b 选项**——用户决策③指定
  单一类目 `unsupported_wildcard_atom`(本轮已按行级拒 + 位置
  分层数字披露于 §二:47/47/8,408);三子类拆分属增量诊断。
- R3-2(记录自洽配平门 `record_self_unbalanced`):**登记 v4b
  选项**——新增源数据完整性门超出"接线必需最小编译支持"(决策⑤);
  现行链路下不平记录由推断映射/产物多重集 gate 诚实拒(非静默
  通过);门价值真实,单独立项。
- R3-3(底物组分必须变化门 `substrate_identity_no_change`):
  **登记 v4b 选项(带程序分析)**——本轮 lhs=匹配组分的结构下,
  "底物恒等、其余组分变化"的记录会以新增原子形态进入编译:共底物
  组分若与底物断连 ⇒ 无锚诚实拒;若键合 ⇒ 底物实际已变化(前提
  不成立);`transform_no_change` 拦整体恒等。专用类目属增量诊断。
- 推断映射立体盲由 strict 产物多重集 gate 终核 + `n_bond_diff`
  仅诊断禁作机制陈述:**采纳(文档层)**(源码注释既有同款声明,
  r29-F2"选首是工程事实非唯一性证明"措辞继续引用不重发明)。

**G4(总判定:与冻结判据一~五零冲突,放行判据冻结前文字收口)**
- 采信(与本轮程序证据互证:分层不改 strict 身份——单测钉住;
  供给面扩展不改判分尺子——scorer 零字节改动)。
- 两个误判模式("供给面数字=strict 收益"、"完整产物集倒逼忽略档
  放宽")采纳进 §九外推纪律与 §十一 #2。
- mimo 不确定项 4 条中 1 条(共底物类型分层占比)已由 §六探针
  补数;其余 3 条(corpus 方向性元数据有无/参考图剥除构建代码/
  CN 覆盖差的质子化-立体占比)维持未确认,可后续只读探针。

## 十一、待复审问题清单(给主会话)

1. **[P1,设计冻结前置] 共底物的事件参与物语义**(mimo R2-2):
   组分级候选的共底物是否/如何显式进事件参与物(角色拆分 R2-1
   cosubstrate vs 条件参与物、声明式拷贝 vs 现行诚实拒分支、
   产物多重集 gate 是否扩展为"执行 ∪ 声明拷贝"、以及"共底物藏
   条件字段则判据二 unknown 无守门"的闭环)——须独立设计轮裁定,
   涉及 partial 桶语义(204/267 供给面题携带有机共底物);本
   轮按"诚实拒 + spec 级声明"交付,不预支设计。
2. **[防滑坡] T1′ 边界重申**(mimo R2-4):组分级供给上线后
   partial 桶会显著膨胀;coproduct_ignore_tier 白名单(仅无机
   小分子、辅因子恒不忽略)不得因完整产物集语义放宽。
3. **[v4b 消融选项,工程级] 诊断细分族**:R1-2(CN 归一失败回退
   计数,须动冻结口径模块)、R3-1(通配拒因三子类)、R3-2(记录
   自洽配平门)、R3-3(底物变化门)、EAWAG 索引键归一差异拆分
   (G1 风险 2)——全部增量诊断/门,不涉判分;主会话取舍。
4. **[池预算实测披露] corpus 通道每题编译开销**:池深探针实测
   全程 ~2,090s / 298 题 × 双臂(v3 臂 + v4 臂)≈ **3.5s/题/臂**
   (v4 臂含 corpus 候选 ≤24/题逐候选推断映射编译);单臂另计
   corpus 索引一次性装配 ~45s(进程内缓存复用);真实批 build
   阶段时长按此增加(零模型调用、零费用,仅 build 墙钟);若成
   瓶颈可列 v4b 预算调优。
5. **[发车前置沿用任务书 §5]**:chain10 复测已回填基线(hit@1
   73);v4 新批发车仍须正链复审放行 + 新登记冻结(池策略身份
   s5b-pool-policy-2 + corpus_retrieval-1 随 run_identity 落账)+
   budget_guard 机器配置沿用;本交付不自行点火。

## 十二、成本与后续

- 本轮实施期真实模型费用:**0**(零调用、零网络、零花费);
- 检索命中数/编译通过数/池深增量**不冒充命中数**;v4 收益只由
  新批同口径零 LLM 判分判定(结果定位 seen298_post_hoc_repair_
  check / known_evidence_reconstruction,不外推 dev 题域);
- 下一步选项:① 主会话收口本交付 → 正链复审;② v4b 消融轮
  (§十一 #3 诊断细分族);③ 设计轮(共底物参与物语义,#1)。
