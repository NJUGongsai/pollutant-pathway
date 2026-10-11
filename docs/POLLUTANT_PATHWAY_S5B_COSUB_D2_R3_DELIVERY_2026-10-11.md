# PPV1 S5b D2-R3 交付书（第二产物声明在位损坏，2026-10-11）

状态：`implementation_ready_for_review`。

Provenance：本交付由 R3 实施子代理**单人全程完成**（实现、测试、独立公开
探针、父红绿、全量、G01、等价面均由本代理执行；无进程死亡、无主会话接管
或代笔）。代码父 = `02a4b272e7f9ac481f67c2df7fba1974e095748c`（R2 收口
提交）；本轮实施期间主会话在其上另提交了 b728fdb7（仅 AGENTS.md 工作模式
节，src/tests 零字节变化、不属本验收面），故本 commit 的实际直接父为
b728fdb7——父红绿/探针/G01/全量均以 02a4b272 源码口径执行，对直接父具有
同等源码对照意义（沿 D2-R2 复审 §1 同情形先例）。actual HEAD = 本轮新
commit（见 git log）。版本身份：corpus-retrieval
**5→6**（本轮差异的登记面），recorded-source-3 / pool-policy-5 /
compiler-3 / search-production-2 维持。

## 修法（Codex D2-R2 复审 §4.2/§4.3/§8 为权威）

S5B-D2-01 最后残余：第二产物声明（corpus.record_products）的**存在性/格式
消费**——分开"字段确未声明"（corpus 块不带该键 ⇒ 单来源合法默认路径，
两处单来源正控保持可提交完整事件）与"字段在位但损坏"（null/string/dict/
bool 等非 list ⇒ 坏声明**首次消费结构化拒**，kind=
`cosubstrate_corpus_record_products_corrupt`，detail 披露 field/
declared_value_type/reason 并**保全原始坏值**，不清洗不重算新身份）。

- 实现位置（production 单一消费源，池 decide/novel/expand/公开 resume
  共用，不在 builder 单口补过滤）：
  - `src/pathway_v43/pollutant/production.py`
    `_check_cosubstrate_event_invariant` 轴 0：存在性改 **键在位**判定
    （`"record_products" in corpus_block`），在位而非 list ⇒ 结构化拒；
    有效 list 继续走既有 strict 身份多重集同源核验（空 list 是有效声明按
    既有多重集比较，不当缺省；contract 侧既有 list 门
    cosubstrate_contract_missing 不退回）；披露 invariant/trigger 措辞同
    步为"checked 只覆盖实际消费来源"。
  - 同文件 `_cosubstrate_record_declaration`（同根规则的**声明入口**）：
    corpus 产物声明在位性 = 键在位（空 list/坏形状都构成记录侧声明；在位
    而缺 contract ⇒ 缺契约拒，不回落 plain A→P 缺省装配）。whole/EAWAG
    的 corpus 块不带该键 ⇒ 行为零变化。
  - `src/pathway_v43/pollutant/recorded_source.py`：corpus-retrieval-5→6
    + 语义块/invariant_note/每 spec co_substrate_semantics 残句同步。
- 测试：`tests/test_ppv1_s5b_cosub_d2.py` 新增 11 项——四坏形状直连拒
  ×4（含 detail 逐项断言与坏 spec 保全）、声明入口控制（无 contract+无 B+
  键在位坏形状 ⇒ 缺契约拒 sources=[corpus]；空 list ⇒ divergent 非缺省；
  键不在位 ⇒ 单来源正控）、公开 start/resume ×4（0 坏 event/0
  event_committed、先行合法账逐表如实、resume 同拒零增行）、公开 novel
  同根（坏 spec 拒 + 同入口合法 spec 仍提交 1 event）、expand 共享守卫
  防御注入（如实标明：注入在 prepare 边界，不拆后续身份门；修后共享
  prepare 即拒早于身份门）；wv41/v4b 版本字面量。

## 验证（全部本代理独立执行；证据
docs/review_evidence/ppv1_s5b_d2_r3_impl_2026-10-11/，留未跟踪）

- 定向三文件：cosub_d2 **49 passed**（38 + 11 新）、wv41+v4b **42
  passed**。
- 全量 not slow（真实仓）：**2049 passed / 0 failed / 16 deselected**
  （= R2 基线 2038 + 11），单次完成，无中间失败，无删日志。
- G01 隔离（沿最新谱系，D2-R2 输入集基线，5 换/0 新/0 缸脚本强制核对）：
  **2038 passed / 10 skipped / 17 deselected，exit 0**（= 2027 + 11），
  输入 SHA 跑后复核零失配（易失目录 /private/tmp/g01_s5b_cosub_d2_r3）。
- 父红绿（02a4b272 源码 + 当前三测试文件字节）：**14 failed / 77 passed /
  0 collection**——11 行为红（四坏形状在父上被接受：直连无拒、公开提交
  1 event、novel 接受、expand 共享 prepare 接受——复审 §4.2 残余在父上
  复现）+ 3 版本字面量红（如实分类）；逐 nodeid 分类
  parent_red_green/classification.json。
- 独立公开探针（fresh tmp，R2 复审 §8 要求复制本轮证据脚本+合成输入执行，
  旧永久证据未动）：33 案公开链 + 7 入口控制 + EAWAG 正控。
  - 修前（父源码）：四坏形状案全部接受、各提交 **1 缺 copy event**（
    events=1、event_committed=1、search_actions=4、budget_reservations=7，
    与复审 §4.2 数字一致；事件产品仅 CC=O 缺 C1CCNCC1；生产报告
    record_products_sources 单来源 + NC-10 "checked"）——如实记录，不
    夸为 strict/R6（实际 R5/partial）。
  - 修后：四案共享 prepare/公开 start/同模型 resume 全拒（同 kind）、
    **0 坏 event/0 相关 event_committed**、坏 spec 保全（detail 原始坏值）、
    resume 17 表零增行、先行 root 检索等合法账逐表如实（不报 start 全零）；
    novel 同根拒（合法 spec 同入口仍提交）；expand 防御注入在共享 prepare
    即拒（早于身份门；注入形态如实标明）；其余 29 案（三原案/四双删/缺/
    重复/冲突 list/非法引用/无 corpus/corpus 缺键单来源/合法 copy/旁观 B
    零 copy/多 B 多 copy/whole ×2/两源同义反序）行为与父**逐项一致**；
    EAWAG 1 event matched_strict 前后一致。socket 禁用，网络尝试 0。
- 检索/编译面父-当前等价（已批准普通反应资产，8 底物）：
  find_recorded_exact + whole 检索输出**逐字节一致**（5453 字节 JSON）。

## 版本登记

corpus-retrieval-5 → **6**（第二产物声明存在性/格式消费语义；spec 装配/
检索/编译行为零变化）；recorded-source-3 / pool-policy-5 / compiler-3 /
search-production-2 维持（compile 判据/池成员/生产链身份零触碰）。

## 金标边界自查

零模型零花费零真实批不 push；金标/题面/封存逐题 run 零读取；三冻结
SHA/scorer/evaluation/AtomTool/金额链零触碰；探针全合成分子与真实 298
金标零重叠（W2 纪律）；等价面仅用已批准普通反应资产。

## 待复审

S5B-D2-01 最后残余是否按 D2-R2 复审 §4.3/§8 收口（四坏形状首消费结构化
拒 + 坏声明保全 + 两种单来源正控保持 + novel/expand 共享守卫 + 恢复同拒）；
声明入口（_cosubstrate_record_declaration 键在位即声明）为同根规则的其他
消费入口覆盖（AGENTS 返工教训 #1），是否采信由复审裁定——该入口只影响
"corpus 块带 record_products 键但既无 contract 又无 B 声明"的形态（真实
装配不可达：whole/EAWAG 不带键、component 分支必有 B+contract）。
