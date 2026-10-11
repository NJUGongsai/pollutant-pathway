"""S5b recorded 精确源适配 —— 原生库记录 → PPV1 池候选(W2;契约登记
s5b-recorded-source-1;零模型、零网络)。

复用既有公共接口(不越层抓 engine 私有对象):
- ``V43Engine.expand_raw``(内含 eawag lookup:CN 键命中,单反应首产品行
  + ion/cofactor 过滤声明)—— 检索通道;
- ``engine.identity_block``(library_path/library_sha256:已授权且哈希
  校验的 corpus 身份)—— **源 hash 校验后**逐行回读原生记录;
- ``recorded_eligibility_reasons``(domain/policy,recorded 卡完整资格
  判据)—— 与 legacy 同一事实源;
- ``s5b_compiler.compile_donor_template``(W1 共同编译器,单一构建源)。

与旧卡口径的关键差异(任务书 W2 逐条):

- 旧 "exact" 卡是**电荷归一立体盲 CN** 查询命中且回填 current、
  mapping unavailable —— 卡名 "exact" ≠ PPV1 strict。本模块分层:
  * ``recorded_strict_exact``:原生记录 donor 的**严格结构身份**
    (canonical 含电荷/立体)== 当前底物严格身份,方向 donor→products,
    完整净产物集合(同 (btid, reac_id) 的**全部**库行,不是引擎 lookup
    去重后的首产品行),编译产物与记录逐组分 strict 核对一致;
  * ``recorded_cn_candidate``:CN 命中但严格身份不同(电荷/立体/拼写)
    —— 不升格 strict exact;按 analog 级候选入池(标注分层);
  * ``analog_transfer``:另一底物/相似通道(analog_source,不属本模块)。
- **一个原反应多产品构成同一事件**(候选事件);不同原反应是备选事件,
  不拼共同产物;
- 过滤声明(ion/cofactor filtered)如实透传;过滤过的单产品卡不冒充
  完整 record(完整集合按库回读);
- 无原生映射 ⇒ 确定性结构对应**推断映射**(枚举预算/歧义披露;标
  ``mapping_origin=inferred``,不是原生/机制证据);图差约束:元素
  对应、旧原子保全、离去组分、新原子来源、完整 target(不任意首
  MCS/补原子/删旁群 —— 对应 = 元素标记 any-bond 子结构同构枚举,
  多解同目标合并、异目标歧义拒);
- 无法编译留 ``unsupported`` + 源诊断(不假装 AtomTool 执行成功);
  所有获许可事件仍走共同公共链(prepare→AtomTool→donor→audit→
  admission→store),不直接插事件行。

负控(任务书 W2):源 hash 篡改(库文件 sha ≠ identity 记录)拒;
CN 同而电荷/手性不同 ⇒ recorded_cn_candidate(不 strict);方向反/另
一底物 ⇒ 不属 exact;filtered 单产品行冒完整 ⇒ 完整集合核对拒;
缺产品/来源 ⇒ 结构化拒;映射枚举触顶 ⇒ 歧义披露拒。

W-V4.1(S5b-corpus-retrieval-1,2026-10-10 用户六决策 ①②③):RHEA/
enviPath 主语料(corpus_v1.jsonl,43,177 行)接入 recorded 直通供给
——**判据与身份语义全部沿用本模块现行实现,不另写第二套**:

- 检索宽/判分严:**CN 口径检索**(cn_identity 同源函数),分层仍按
  严格身份(donor 侧匹配身份 == 底物严格身份 ⇒ strict;CN 同而
  strict 异 ⇒ cn_candidate 不升格);
- **组分级 donor 匹配 + 共底物声明**:底物 == donor 某一组分(CN
  检索口径),其余组分诚实声明为共底物/条件参与物(co_substrates,
  不静默丢弃、不冒充单底物反应);整串(单组分 donor 全串)语义下
  该声明退化为空集;
- **W-V4.1-R1(S5b-corpus-retrieval-2,2026-10-10,Codex v4 复审
  S5B-V4-01 回修)**:没有已经审定且**实际消费**的共底物参与物/
  原子来源语义时,**有共底物的 component 记录一律不送单组分 LHS
  编译**——编译前结构化 unsupported(``corpus_cosubstrate_
  participants_unsupported``,保留源行/方向/共底物声明/可追溯拒因),
  不产 spec、不产 event。该共用许可规则在本入口(``find_corpus_
  recorded_exact``)生效,消费方(builder 池/公开链)拿不到坏 spec;
  不按元素/角色/可锚性/方向/具体分子设例外(键合有机共底物原子经
  add_atom 折成"新增原子"的通道整体关闭;断连辅因子同样在编译前
  拒,不再依赖编译层 new_atom_placement_incomplete 兜底)。显式
  共底物参与物设计(声明式拷贝/gate 扩展)属后续独立设计轮,先
  规则级方案送化学评审,不借本轮放宽产物多重集 gate。
- **编译按完整净产物集合核**:donor 侧(整串)→ 记录全量
  product_components,走同一 ``compile_recorded_reaction`` 推断映射
  + 产物多重集 gate(共底物↔共产物对应判据属设计件,不本轮实现,
  交付书登记待复审);
- **双向保留**:RHEA master 的 LR/RL 双行按**各自行书写方向**作
  双方向候选分层引用(每行自己的 donor_A→product_B;方向=记录声明,
  不换向;同一 master 双行同净反应由池侧同签名去重防双槽);
- **通配行拒因**:含 ``*`` 的行 unsupported_wildcard_atom 行级结构化
  拒(不冒充可编译;donor 侧通配组分不可检索=天然不供给,产品侧
  通配检索到即拒并计数);
- **全库无原生映射**:mapping_status 必须 'absent'/atom_mapping null
  (corpus_v1 事实);冒充原生映射来源的记录 ⇒ 结构化拒
  (corpus_native_mapping_claimed),全部走推断映射(mapping_origin
  =inferred 强制);
- **provenance 披露**:记录级 provenance_sha256 存在性披露(构造期
  来源记录指纹,不冒充内容完整性证明);缺 ⇒ corpus_provenance_
  missing 结构化拒(实测 enviPath 带产物行 5,497 行缺该字段)。

corpus 身份唯一来源 = ``engine.identity_block`` 现有键
corpus_v1_path/corpus_v1_sha256(env_asset_root.resolve_and_verify
锚定,无需新哈希机制);sha 锚定后逐行回读,实际 sha ≠ 身份记录 ⇒
corpus_hash_mismatch fail-closed(源 hash 篡改负控同款)。

W-D2(S5b-corpus-retrieval-3 + S5b-recorded-source-3,2026-10-10,
共底物参与物显式语义 D2 编译实现轮;权威 = 设计书
S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md 全文
[含 §12 T-1~T-5 处置记录] + mimo r32 回应 16 条修改建议与
NC-8..12/PC-4/5 控件矩阵 + r31 措辞护栏):

- **事件表示(设计 §四 方案 a)**:component-with-cosubstrate 候选
  (现行被 s5b-corpus-retrieval-2 许可规则拦的面)按**原子归属三
  分类**(设计 §五.1:A-可溯/B-可溯/不可归属)重新供给——
  * **整组分拷贝子集**解锁:B 进事件反应物侧参与物(role=
    cosubstrate、系数 unknown),B 来源**整组分**产物声明式拷贝
    (不执行、中心 unknown、来源记录字段完整、身份 = 记录产物组
    分严格身份经 ``strict_identity_of`` 同源派生 state_id);
    ``expectation.target_smiles`` = 可执行子集(A 原子全部可溯);
    拷贝组分**不进** edits/alignment/expectation 通道;
  * **键合融合子集保守拒**(``cosubstrate_bonded_contribution_
    unsupported``;覆盖同根 LR/RL、可锚/不可锚、有机/辅因子、未
    知角色、配平/不配平,无例外——NC-1/NC-2;四轴子标签
    R32-CS2-3);
  * **不可归属原子保守拒**(``cosubstrate_atom_source_
    unattributable``;T-3 主会话默认档 + mimo r32 CS3 已裁
    R32-CS3-1——拒因子带 ``mapping_fallback: true|false`` 分列
    bond-diff 回退映射伪影 vs 源数据真缺);
  * 可执行子集为空 ⇒ ``cosubstrate_no_executable_product_subset``
    (R32-CS2-4/NC-8);B SMILES 不可解析 ⇒ ``cosubstrate_
    unparseable``(NC-6);
- **union gate 扩展**(设计 §五.3 落点子选项 i + R32-CS3-2):
  ``compile_recorded_reaction`` 新增可选参数 ``declared_copies``/
  ``record_products``(缺省 None ⇒ **EAWAG/整串路径行为字节等价**
  ——无拷贝分支零触碰);扩展语义 = 执行组分多重集 ∪ 声明拷贝
  组分多重集 == 记录产物多重集(严格身份、多重集、同源
  ``strict_identity_of`` 键空间统一 + 裸键/严格键一致性披露);
  拷贝身份 ≠ 记录产物组分 ⇒ ``declared_copy_mismatch``(NC-4);
  并集不齐 ⇒ ``product_set_mismatch`` 沿用;
- **add_atom 伪装机器断言**(设计 §五.2.5/NC-3):component 候选
  产出的 spec 其 edits 中出现任何 ``add_atom`` ⇒ 结构化拒
  (``cosubstrate_executable_add_atom_regression_guard``)——
  规则 2/3 已结构性排除 B 原子进编辑通道,该断言防未来实现漂移;
- **NC-12 批级熔断(钉死)**:本通道事件在现行 P1 参与物集合
  语义下**结构性无 strict 通路**(T-1 不立项 ⇒ 事件恒 partial;
  合成批 e2e 断言 matched_strict == 0,出数即红);
- **诚实预期(写入交付书)**:本通道对 hit@1 预期贡献 = 0;解锁
  的是诚实 partial 供给 + 审计链完整性 + T-1 立项后的机读基础;
- **EAWAG 面/整串面/公共编译判据零回退**:find_recorded_exact 与
  compile_recorded_reaction 缺省路径字节等价(负控断言回归);
  r31 措辞护栏(add_atom 伪装禁令范围 = 记录已声明的共底物;
  EAWAG 隐式书写不在禁令内)逐字保持。

W-V4b(S5b-recorded-infer-2,2026-10-10,编译墙深层修复轮):推断
映射公共判据链的**枚举预算与枚举面扩展**(判据零放宽——产物多重集
gate 不放宽、等价映射合并、触顶诚实拒、product_set_mismatch 0/28
维持缺行诚实拒不冒充):

- 有界键差 fallback 预算升档:``_INFER_BOND_DIFF_CALL_LIMIT``
  512→8192(删键组合调用预算;全 k≤2 枚举覆盖 donor ≤127 键,
  n(n+1)/2≤8192;实测触顶率前后披露);``_INFER_MATCH_LIMIT``
  200→800(候选映射歧义上限,触顶 ⇒ truncated 诚实拒不变);
- fallback 前置必要条件(fast-fail,零语义变化):donor 元素多重集
  ⊄ union 或 n_donor > n_union ⇒ 任意键差下查询必无解,直接空返回
  (省去无望记录的组合枚举预算,与 template_elements_fit 同纪律——
  编译层判据的必要条件前置,不新增第二套判据);
- 加成/生成分支全组分枚举:旧实现在首个可容纳 donor 的产物组分后
  break(丢后续组分的候选对应);现全部组分在预算内枚举,候选映射
  交由编译 + 产物多重集 gate + 落位纪律全映射评估(W-V2.3 同源);
- stereo 消解在公共编译器侧实施(s5b-compiler-3,2026-10-10 R1 收口
  S5B-V4B-01 后版本:消解元素域收窄为碳 + 执行后复核双轴;本模块
  零判据改动,通道产出的 stereo_edit_unsupported 事件面由消解谓词
  收敛)。
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from functools import lru_cache

from rdkit import Chem, RDLogger

from ..domain.identity import cn_identity
from .chemstate import build_chemical_state, strict_identity_of
from .s5b_compiler import S5bCompileError, compile_donor_template

RDLogger.DisableLog("rdApp.*")

RECORDED_SOURCE_VERSION = "s5b-recorded-source-3"

# ---- W-V4.1:corpus 直通检索语义冻结登记(§1 硬条款;开工先于接线)----
# 冻结依据:TASK_V43_PPV1_S5B_HIT50_V4_DRAFT_2026-10-10 §10 用户裁定
# ①(CN 检索 + strict 编译核)②(组分级 + 共底物声明)③(双向保留 +
# 通配拒因)。判据零新增:检索/分层/编译全部同源复用现行实现。
# W-V4.1-R1(2026-10-10,Codex v4 复审 S5B-V4-01 回修):版本升
# s5b-corpus-retrieval-2 ——共底物 component 许可变化(编译前结构化
# unsupported);分层/通配/映射/provenance 语义零变化。
# W-D2(2026-10-10,共底物参与物显式语义 D2 编译实现轮):版本升
# s5b-corpus-retrieval-3 ——component-with-cosubstrate 许可从
# "一律编译前拒"改为**三分类守门三分支**(整组分拷贝子集有条件
# 放行 / 键合融合保守拒 / 不可归属保守拒;原子归属 = 编译器内部
# 规则,不进事件协议)。检索宽/分层/通配/映射/provenance/双向
# 语义零变化;整串(whole)语义零变化。
# W-D2-R1(2026-10-11,Codex D2 复审 §4/§8 唯一 P1 S5B-D2-01 回修):
# 版本升 s5b-corpus-retrieval-4 ——**共底物事件契约消费语义变更**
# (spec 装配/检索/编译行为零变化):production.prepare_hypothesis
# 的 NC-10 触发条件改挂记录侧单一声明来源(cosubstrate_event_
# contract 为 dict 或 corpus 块声明 B/copy;装配数组缺失/null/空、
# participants 删减/省略不再能关闭守卫或默认降级 A→P——四反例
# strip_both_empty/missing/null、all_arrays_missing_participants_
# default 首消费结构化拒,零坏 event/相关提交);NC-12 熔断加
# 参考范围限定(仅当前剥除 B/copy 的 root-only 参考构建口径下
# matched_strict 恒 0;合法完整 B/copy 参考可 strict,不是漂移)。
CORPUS_RETRIEVAL_VERSION = "s5b-corpus-retrieval-4"
CORPUS_RETRIEVAL_SEMANTICS = {
    "version": CORPUS_RETRIEVAL_VERSION,
    "substrate_retrieval_scope": "cn_identity_wide",
    "tier_rule": (
        "matched_side_strict_identity == substrate_strict_identity "
        "-> recorded_strict_exact; cn_equal_strict_differs "
        "-> recorded_cn_candidate (no strict promotion)"),
    "donor_side_semantics": (
        "component_level_with_co_substrate_declaration;"
        " D2: component candidates with non-empty co_substrates "
        "pass the atomic-attribution three-way classification "
        "(A-traceable / B-traceable / unattributable) before "
        "compilation; whole-component-copy subset is re-supplied "
        "with explicit cosubstrate participants and declared-copy "
        "product components; bonded-fusion subset and "
        "unattributable-atom subset remain structured-rejected"),
    "cosubstrate_permission": (
        "D2 (s5b-corpus-retrieval-4 after W-D2-R1 rework of the "
        "Codex D2 review sole P1 S5B-D2-01; originally approved by "
        "mimo r32 conditional pass + design book DS-1 section 12 "
        "T-1..T-5 default dispositions): whole-component-copy events "
        "are CHEMICALLY HONEST partial supply under current P1 "
        "participant-set semantics (cosubstrate declared on the "
        "reactant side => superset => matched_participant_coverage"
        "_partial; structurally no strict path under the CURRENT "
        "ROOT-ONLY (B/copy-stripped) reference construction scope — "
        "NC-12 batch fuse asserts matched_strict == 0 for that scope "
        "only; a legal complete B/copy reference may legitimately "
        "match the same declared event strict, which is NOT drift "
        "and must NOT be masked by editing the evaluator); "
        "bonded-fusion contribution is conservatively rejected with "
        "no exceptions "
        "(cosubstrate_bonded_contribution_unsupported; NC-1/NC-2); "
        "unattributable atoms are conservatively rejected with "
        "mapping_fallback split disclosure "
        "(cosubstrate_atom_source_unattributable; mimo r32 "
        "R32-CS3-1); tier counts below are retrieval-candidate "
        "counts including precompile rejected, not compiled/supply "
        "counts"),
    "cosubstrate_event_semantics": (
        "W-D2-R1 (s5b-corpus-retrieval-4, S5B-D2-01): NC-10 "
        "applicability is decided by the RECORD-SIDE single "
        "declaration source (spec.cosubstrate_event_contract being "
        "a dict OR spec.corpus block declaring B/copy) inside "
        "production.prepare_hypothesis; the assembly arrays "
        "(co_substrate_states / declared_copy_components) being "
        "missing/null/empty, or participants being reduced/omitted, "
        "can NOT disable the guard nor default the spec to plain "
        "A->P assembly (first-consumption structured reject, zero "
        "bad events; legal bystander B with copy=[] is not "
        "rejected); the declared-B set for the subset axis is the "
        "contract UNION corpus merged declaration. participants: "
        "A (reactant, primary_substrate, coefficient unknown) + "
        "each declared B (reactant, cosubstrate, coefficient "
        "unknown) + executable products (principal/coproduct) + "
        "each B-derived whole product component "
        "(product, coproduct role; component_source="
        "record_declared_copy in the provenance layer, not the "
        "participant计量 layer); participant_list_status = "
        "declared_complete (T-2 main-session default); declared "
        "copies carry center=unknown (criterion 5: no mapping => "
        "unknown, R5 retain_conditional), never verified, never "
        "executed; expectation covers the executable subset only"),
    "union_gate_semantics": (
        "D2 (s5b-recorded-source-3, optional parameter on the "
        "shared compile_recorded_reaction; default None keeps the "
        "EAWAG/whole path byte-equivalent): executed component "
        "multiset UNION declared-copy component multiset == "
        "recorded product multiset, strict_identity_of key space "
        "unified on both sides (R32-CS3-2) with bare-key/strict-"
        "key consistency disclosure; copy identity != recorded "
        "product component => declared_copy_mismatch; union "
        "incomplete => product_set_mismatch; the gate is an "
        "identity-transcription check, NOT an element/charge "
        "balance verification (stoichiometry axis stays unknown "
        "per criterion 2; R32-CS1-2 wording)"),
    "whole_string_semantics": (
        "single_component_donor_or_exact_whole_string_cn_match;"
        " co_substrate declaration degenerates to empty set;"
        " whole records compile with the FULL donor string as lhs"),
    "wildcard_policy": "row_level_unsupported_wildcard_atom_reject",
    "master_direction_policy": (
        "both_direction_rows_retained_per_row_writing; "
        "identical net reaction deduped by pool signature"),
    "mapping_policy": (
        "all_inferred; native mapping claims rejected "
        "(corpus_v1 has no native atom mappings)"),
    "provenance_policy": (
        "record_level_existence_disclosure; missing -> "
        "corpus_provenance_missing structured reject"),
    "frozen_by": (
        "TASK_V43_PPV1_S5B_HIT50_V4 §10 decisions 1/2/3, 2026-10-10"
        "; W-V4.1-R1 rework: codex v4 review 2026-10-10 §4.3/§8; "
        "W-D2: S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_"
        "2026-10-10.md (DS-1 design_approved_with_conditions) + "
        "mimo r32 16-condition pass, 2026-10-10; W-D2-R1: codex D2 "
        "review 2026-10-11 §4/§8 sole P1 S5B-D2-01 rework (NC-10 "
        "record-side-declaration trigger), 2026-10-11"),
}

# 推断映射的子结构同构枚举上限(触顶 ⇒ 歧义披露拒绝,不静默取首解)
# W-V4b(S5b-recorded-infer-2):200→800——候选映射歧义上限升档
# (v3 分类中触顶类因预算截断被拒;升档后触顶率实测披露,触顶语义
# 不变:超上限仍 truncated 诚实拒)。
_INFER_MATCH_LIMIT = 800

# ---- W-V2(S5b-recorded-bonddiff-1):有界键差结构对应 ----
#
# 尸检(v2 批 L1):116 次 no_structure_correspondence 主因 = any-bond
# 子结构同构对"键连通性保持"的要求对断键/成键重排与水解型记录过紧
# (标准两分支:裂解=产物组分 ⊆ donor;加成=donor ⊆ 单一产物组分;
# 重排/跨组分断裂+新增原子两分支都无法表达)。fallback:删 donor
# ≤ _INFER_BOND_DIFF_LIMIT 条键后的**允许不连通**查询在产物并集上
# 匹配 —— 保留原子全覆盖、元素对应、片段内连通保持;被删键 = 允许
# 的键差(断键或像间重排成键,由 mapped_lhs/rhs 键差推导);未覆盖
# union 原子 = 新原子(锚定由编译器 W1 #6 规则约束)。预算/歧义披露
# 不变(枚举触顶 ⇒ truncated 拒;等价映射同目标合并、异目标歧义拒)。
# 标准(零键差)枚举成功时 fallback 不触发 —— 既有语义逐字节不变。
_INFER_BOND_DIFF_LIMIT = 2
# fallback 的查询调用预算(删键组合数上限;超 ⇒ truncated 拒,不静默
# 缩小枚举面)。原子级预算与 _INFER_MATCH_LIMIT(匹配数)互补。
# W-V4b(S5b-recorded-infer-2):512→8192——全 k≤2 枚举需
# n_bonds + C(n_bonds,2) = n(n+1)/2 次调用;8192 覆盖 donor ≤127 键
# (298 题面 EAWAG/corpus 整串 donor 键数实测上界见交付书;升档后
# 触顶率实测披露)。无望组合(fast-fail 前置必要条件)不再占用预算。
_INFER_BOND_DIFF_CALL_LIMIT = 8192

# 每进程库索引缓存(1.4MB 文本;hash 锚定后复用)
_LIBRARY_CACHE: dict = {}


class RecordedSourceError(RuntimeError):
    """recorded 源契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 库回读


def _library_identity(engine) -> dict:
    block = engine.identity_block or {}
    path = str(block.get("library_path") or "")
    sha = str(block.get("library_sha256") or "")
    if not path or not sha:
        raise RecordedSourceError(
            "引擎身份块缺 library 路径/哈希(recorded 源需要授权且哈希"
            "校验的 corpus 身份;不猜)", {
                "kind": "library_identity_missing"})
    return {"library_path": path, "library_sha256": sha}


def load_library_index(engine) -> dict:
    """逐行回读原生库(按 (btid, reac_id) 全产品分组;hash 校验)。

    返回 {reaction_key "btid#reac_id": {donor_smiles, package, products:
    [product_smiles 原样(库行序)]}};库文件实际 sha256 ≠ 引擎身份记录
    ⇒ 拒(源 hash 篡改负控)。进程内 lru 缓存(同一 engine 身份复用)。
    """
    identity = _library_identity(engine)
    cache_key = (identity["library_path"], identity["library_sha256"])
    if cache_key in _LIBRARY_CACHE:
        return _LIBRARY_CACHE[cache_key]
    actual = hashlib.sha256(
        open(identity["library_path"], "rb").read()).hexdigest()
    if actual != identity["library_sha256"]:
        raise RecordedSourceError(
            "库文件哈希与引擎身份记录不符(源 hash 篡改/漂移;授权 corpus"
            " 校验失败,fail-closed 不消费)", {
                "kind": "library_hash_mismatch",
                "library_path": identity["library_path"],
                "expected_sha256": identity["library_sha256"],
                "actual_sha256": actual})
    index: dict[str, dict] = {}
    with open(identity["library_path"], encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            rid = f"{record.get('btid', '')}#{record.get('reac_id', '')}"
            entry = index.setdefault(rid, {
                "donor_smiles": str(record.get("donor_smiles") or ""),
                "donor_id": str(record.get("donor_id") or ""),
                "package": str(record.get("package") or ""),
                "products": []})
            if not entry["donor_smiles"]:
                entry["donor_smiles"] = str(
                    record.get("donor_smiles") or "")
            product = str(record.get("product_smiles") or "")
            if product and product not in entry["products"]:
                entry["products"].append(product)
    _LIBRARY_CACHE[cache_key] = index
    return index


def reset_library_cache() -> None:
    """测试钩子:清库索引缓存。"""
    _LIBRARY_CACHE.clear()


# ---------------------------------------------------------------- W-V4.1 corpus 回读

# 每进程 corpus 索引缓存(hash 锚定后复用;43,177 行全文索引)
_CORPUS_CACHE: dict = {}


def _corpus_identity(engine) -> dict:
    """corpus_v1 身份(引擎 identity_block 现有键;fail-closed)。"""
    block = engine.identity_block or {}
    path = str(block.get("corpus_v1_path") or "")
    sha = str(block.get("corpus_v1_sha256") or "")
    if not path or not sha:
        raise RecordedSourceError(
            "引擎身份块缺 corpus_v1 路径/哈希(W-V4.1 corpus 直通需要"
            "授权且哈希校验的 corpus 身份;不猜,不静默降级为无 corpus"
            "通道)", {"kind": "corpus_identity_missing"})
    return {"corpus_v1_path": path, "corpus_v1_sha256": sha}


def _corpus_products(record: dict) -> list[str]:
    """完整净产物集合(product_components 优先,库行序承载;缺则按
    product_B_smiles 组分分离;均缺 ⇒ 空=record_missing_or_incomplete
    同款诚实拒)。"""
    comps = [str(c) for c in (record.get("product_components") or [])
             if str(c).strip()]
    if comps:
        return comps
    pb = str(record.get("product_B_smiles") or "")
    if not pb:
        return []
    mol = Chem.MolFromSmiles(pb)
    if mol is None:
        # 不可解析:原样透传给编译层结构化拒(不猜、不丢弃)
        return [pb]
    return [Chem.MolToSmiles(frag) for frag in Chem.GetMolFrags(
        mol, asMols=True, sanitizeFrags=True)]


def _corpus_donor_components(record: dict) -> list[str]:
    """donor 组分(donor_components 优先;缺/空 ⇒ 按 donor_A_smiles
    组分分离;均缺 ⇒ 空=不可检索)。"""
    comps = [str(c) for c in (record.get("donor_components") or [])
             if str(c).strip()]
    if comps:
        return comps
    da = str(record.get("donor_A_smiles") or "")
    if not da:
        return []
    mol = Chem.MolFromSmiles(da)
    if mol is None:
        return [da]  # 原样透传(CN 索引构建时会跳过不可解析项)
    return [Chem.MolToSmiles(frag) for frag in Chem.GetMolFrags(
        mol, asMols=True, sanitizeFrags=True)]


def load_corpus_index(engine) -> dict:
    """corpus_v1 逐行回读 + 组分级 CN 检索索引(sha 锚定;W-V4.1)。

    返回 {records: [适配记录], cn_component_index: {cn: [(i, comp_idx)]},
    cn_whole_index: {cn: [i]}, corpus_v1_sha256, n_rows}:
    - records[i]:{line_no, record_id, record_key(行唯一键,
      ``record_id@L<line_no>``;enviPath 303 个重复 record_id ⇒ 必须行
      定位), source_type, master_id, direction, ec, donor_A_smiles,
      donor_components, products(完整净产物集合,记录序), provenance_
      sha256, mapping_status, atom_mapping, parse_note};
    - 检索索引:donor 各组分的 CN(reusable 同源 ``cn_identity``;
      通配组分不索引=天然不可检索),多组分 donor 的整串 CN;
      单组分 donor 经组分索引承载整串语义(kind=whole);
    - 实际 sha256 ≠ 引擎身份记录 ⇒ 拒(源 hash 篡改负控,load_
      library_index 同款 fail-closed)。进程内缓存(同一身份复用)。
    """
    identity = _corpus_identity(engine)
    cache_key = (identity["corpus_v1_path"],
                 identity["corpus_v1_sha256"])
    if cache_key in _CORPUS_CACHE:
        return _CORPUS_CACHE[cache_key]
    actual = hashlib.sha256(
        open(identity["corpus_v1_path"], "rb").read()).hexdigest()
    if actual != identity["corpus_v1_sha256"]:
        raise RecordedSourceError(
            "corpus 文件哈希与引擎身份记录不符(源 hash 篡改/漂移;"
            "授权 corpus 校验失败,fail-closed 不消费)", {
                "kind": "corpus_hash_mismatch",
                "corpus_v1_path": identity["corpus_v1_path"],
                "expected_sha256": identity["corpus_v1_sha256"],
                "actual_sha256": actual})
    records: list[dict] = []
    cn_component_index: dict[str, list] = {}
    cn_whole_index: dict[str, list[int]] = {}
    with open(identity["corpus_v1_path"], encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            row = json.loads(text)
            record_id = str(row.get("record_id") or "")
            comps = _corpus_donor_components(row)
            record = {
                "line_no": line_no,
                "record_id": record_id,
                "record_key": f"{record_id}@L{line_no}",
                "source_type": str(row.get("source_type") or ""),
                "master_id": (str(row["master_id"])
                              if row.get("master_id") else None),
                "direction": (str(row["direction"])
                              if row.get("direction") else None),
                "ec": (str(row["ec"]) if row.get("ec") else None),
                "donor_A_smiles": str(row.get("donor_A_smiles") or ""),
                "donor_components": comps,
                "products": _corpus_products(row),
                "provenance_sha256": (
                    str(row["provenance_sha256"])
                    if row.get("provenance_sha256") else None),
                "mapping_status": str(row.get("mapping_status") or ""),
                "atom_mapping": row.get("atom_mapping"),
                "parse_note": str(row.get("parse_note") or ""),
            }
            i = len(records)
            records.append(record)
            # 检索索引:通配组分不索引(* 不可与真实底物 CN 相等);
            # 不可解析组分 CN=None 同样不索引
            for comp_idx, comp in enumerate(comps):
                if "*" in comp:
                    continue
                comp_cn = cn_identity(comp)
                if comp_cn is None:
                    continue
                cn_component_index.setdefault(comp_cn, []).append(
                    (i, comp_idx))
            if len(comps) > 1 and record["donor_A_smiles"]:
                # 多组分 donor 的整串 CN(单组分由组分索引承载)
                whole_cn = cn_identity(record["donor_A_smiles"])
                if whole_cn is not None:
                    cn_whole_index.setdefault(whole_cn, []).append(i)
    index = {
        "records": records,
        "cn_component_index": cn_component_index,
        "cn_whole_index": cn_whole_index,
        "corpus_v1_sha256": identity["corpus_v1_sha256"],
        "corpus_v1_path": identity["corpus_v1_path"],
        "n_rows": len(records),
    }
    _CORPUS_CACHE[cache_key] = index
    return index


def reset_corpus_cache() -> None:
    """测试钩子:清 corpus 索引缓存。"""
    _CORPUS_CACHE.clear()


# ---------------------------------------------------------------- 推断映射


def _any_bond_query(mol):
    """元素标记 + any-bond 查询(结构对应:元素对应约束,键级不约束)。"""
    params = Chem.AdjustQueryParameters.NoAdjustments()
    params.makeBondsGeneric = True
    return Chem.AdjustQueryProperties(Chem.Mol(mol), params)


def _mapped_copy(mol, map_of_idx: dict) -> str:
    """按 idx→map 号写原子映射号的 SMILES(确定性)。"""
    out = Chem.Mol(mol)
    for idx, map_no in map_of_idx.items():
        out.GetAtomWithIdx(idx).SetAtomMapNum(int(map_no))
    return Chem.MolToSmiles(out)


def _elements_contained(query_mol, target_mol) -> bool:
    """query 元素多重集 ⊆ target 元素多重集(子结构匹配必要条件)。

    子结构匹配要求全部 query 原子入 target ⇒ 元素计数必须被包含
    (键级任意/删键任意都不改变原子集)。fail 判定 = 任意键差下查询
    必无解 ⇒ 调用方可直接空返回(必要条件前置,非第二套判据)。"""
    q_counts: dict = {}
    for a in query_mol.GetAtoms():
        q_counts[a.GetSymbol()] = q_counts.get(a.GetSymbol(), 0) + 1
    t_counts: dict = {}
    for a in target_mol.GetAtoms():
        t_counts[a.GetSymbol()] = t_counts.get(a.GetSymbol(), 0) + 1
    return all(q_counts[e] <= t_counts.get(e, 0) for e in q_counts)


def _infer_bond_diff_fallback(donor, union) -> list[dict]:
    """有界键差对应 fallback(W-V2.2;标准枚举为空时才调用)。

    枚举:删 donor 的 1.._INFER_BOND_DIFF_LIMIT 条键(组合序:单键
    先于双键)⇒ 允许不连通的 any-bond 查询在 union 上匹配;每个
    match 是一个候选对应(全部 donor 原子均映射、元素对应、片段内
    连通保持)。被删键 = 允许键差(实际断键/重排由 mapped 双侧键差
    推导);未覆盖 union 原子 = 新原子。

    预算纪律(与标准分支同源):匹配数 ≤ _INFER_MATCH_LIMIT(每组合);
    组合调用数 ≤ _INFER_BOND_DIFF_CALL_LIMIT(超 ⇒ 剩余组合不枚举,
    truncated=True);像去重(不同删键组合可能给出同一像;先到先得,
    单键组合优先)。产出 mapping 携带 n_bond_diff(删键数,供诊断
    披露;非机制证据)。

    W-V4b fast-fail 前置必要条件(零语义变化):donor 元素多重集
    ⊄ union 或 n_donor > n_union ⇒ 任意删键组合的查询必无解,直接
    空返回(无望记录不再占用组合预算;与 template_elements_fit 同
    纪律——判据单一来源的必要条件前置)。
    """
    n_donor = donor.GetNumAtoms()
    n_union = union.GetNumAtoms()
    if n_donor > n_union or not _elements_contained(donor, union):
        return []
    bonds = list(donor.GetBonds())
    from itertools import combinations
    subsets: list[tuple] = []
    for k in range(1, _INFER_BOND_DIFF_LIMIT + 1):
        subsets.extend(combinations(range(len(bonds)), k))
    mappings: list[dict] = []
    seen_images: set[tuple] = set()
    truncated = False
    calls = 0
    for subset in subsets:
        if calls >= _INFER_BOND_DIFF_CALL_LIMIT or \
                len(mappings) >= _INFER_MATCH_LIMIT:
            truncated = True
            break
        calls += 1
        q = Chem.RWMol(donor)
        for b_idx in subset:
            b = bonds[b_idx]
            q.RemoveBond(b.GetBeginAtomIdx(), b.GetEndAtomIdx())
        try:
            query = _any_bond_query(q.GetMol())
        except Exception:
            continue
        ms = union.GetSubstructMatches(
            query, uniquify=False, useChirality=False,
            maxMatches=_INFER_MATCH_LIMIT)
        for m in ms:
            image = {d: int(m[d]) for d in range(n_donor)}
            key = tuple(sorted(image.items()))
            if key in seen_images:
                continue
            seen_images.add(key)
            covered = set(image.values())
            new_union = [u for u in range(n_union) if u not in covered]
            mappings.append({
                "donor_to_union": image,
                "new_union": new_union,
                "removed_donor": [],
                "truncated": truncated,
                "n_bond_diff": len(subset)})
            if len(mappings) >= _INFER_MATCH_LIMIT:
                truncated = True
                break
        if mappings:
            # 最小键差优先:首个产生像的删键组合已覆盖该键差面;
            # 更大键差组合仅在更小组合无解时继续(单组合序保证)
            continue
    for entry in mappings:
        entry["truncated"] = truncated or entry["truncated"]
    return mappings


def infer_reaction_mapping(
    donor_smiles: str, product_smiles: list[str],
) -> list[dict]:
    """确定性结构对应(元素标记 any-bond 子结构同构;W2)。

    两个互斥策略(按原子数;连通 donor 不能直接子结构匹配到断开的
    多组分产物并集 —— 产物并集按组分分离匹配):
    - ``n_union <= n_donor``(裂解/离去):逐产物组分在 donor 内枚举
      any-bond 同构,组分间 donor 原子不相交的组合为候选映射;
      未覆盖 donor 原子 = 离去组分;
    - ``n_donor < n_union``(加成/生成):donor(连通)在某单一产物
      组分内枚举同构;未覆盖 union 原子 = 新原子(新原子不可达锚点
      时由编译器诚实拒);
    每个候选 {donor_to_union: {donor_idx: union_idx}, new_union,
    removed_donor, truncated}。约束:元素对应(查询元素标记);不任意
    补原子/删旁群(仅同构像);枚举触顶 ⇒ truncated(调用方拒)。

    **W-V2.2(S5b-recorded-bonddiff-1)**:两个标准策略都无解 ⇒
    有界键差 fallback(删 donor ≤2 条键的不连通 any-bond 查询在
    产物并集上匹配;断键/成键重排与跨组分断裂+新增原子的记录恢复
    对应;预算/歧义披露不变;标准枚举成功时零行为变化)。

    **W-V4b(S5b-recorded-infer-2)**:预算升档(match 800 / 调用
    8192)与加成分支全组分枚举(见分支注释);fallback 前置必要
    条件 fast-fail(元素包含/原子数;零语义变化);触顶诚实拒、
    等价映射合并、异目标歧义拒全部维持。
    """
    donor = Chem.MolFromSmiles(donor_smiles or "")
    if donor is None:
        raise RecordedSourceError(
            f"库记录 donor 不可解析:{donor_smiles!r}",
            {"kind": "record_donor_unparseable"})
    union = Chem.MolFromSmiles(".".join(product_smiles))
    if union is None:
        raise RecordedSourceError(
            "库记录产物并集不可解析(fail-closed,不猜)",
            {"kind": "record_products_unparseable"})
    n_donor, n_union = donor.GetNumAtoms(), union.GetNumAtoms()
    mappings: list[dict] = []
    truncated = False
    if n_union <= n_donor:
        # ---- 裂解/离去:产物组分 ⊆ donor(组分分离不相交组合) ----
        comps = Chem.GetMolFrags(union, asMols=True, sanitizeFrags=True)
        offsets: list[int] = []
        offset = 0
        comp_matches: list[list[tuple]] = []
        for comp in comps:
            offsets.append(offset)
            offset += comp.GetNumAtoms()
            query = _any_bond_query(comp)
            ms = donor.GetSubstructMatches(
                query, uniquify=False, useChirality=False,
                maxMatches=_INFER_MATCH_LIMIT)
            if not ms:
                standard_empty = True
                break
            comp_matches.append([tuple(m) for m in ms])
        else:
            standard_empty = False
        if not standard_empty and comp_matches:
            combos: list[dict] = []

            def _combine(i: int, used: set[int], image: dict) -> None:
                if len(combos) >= _INFER_MATCH_LIMIT:
                    return
                if i == len(comps):
                    combos.append(dict(image))
                    return
                comp_global_offset = offsets[i]
                for m in comp_matches[i]:
                    if set(m) & used:
                        continue
                    for q_idx, d_idx in enumerate(m):
                        image[d_idx] = comp_global_offset + q_idx
                    _combine(i + 1, used | set(m), image)

            _combine(0, set(), {})
            truncated = len(combos) >= _INFER_MATCH_LIMIT
            for image in combos:
                removed = [d for d in range(n_donor) if d not in image]
                mappings.append({"donor_to_union": image, "new_union": [],
                                 "removed_donor": removed,
                                 "truncated": truncated})
    else:
        # ---- 加成:donor ⊆ 单一产物组分 ----
        # W-V4b(S5b-recorded-infer-2):全部组分在预算内枚举(旧实现
        # 在首个可容纳 donor 的组分后 break——丢后续组分的候选对应;
        # 不同组分承载的对应是不同的结构假设,交由编译 + 产物多重集
        # gate + 落位纪律全映射评估,W-V2.3 同源)。每组分枚举上限
        # _INFER_MATCH_LIMIT;总映射数超限 ⇒ truncated 诚实拒不变。
        comps = Chem.GetMolFrags(union, asMols=True, sanitizeFrags=True)
        offset = 0
        query = _any_bond_query(donor)
        for comp in comps:
            ms = comp.GetSubstructMatches(
                query, uniquify=False, useChirality=False,
                maxMatches=_INFER_MATCH_LIMIT)
            for m in ms:
                image = {d: offset + u for d, u in enumerate(m)}
                covered = {image[d] for d in image}
                new = [u for u in range(n_union) if u not in covered]
                mappings.append({
                    "donor_to_union": image, "new_union": new,
                    "removed_donor": [], "truncated": False})
            offset += comp.GetNumAtoms()
        truncated = len(mappings) >= _INFER_MATCH_LIMIT
        for entry in mappings:
            entry["truncated"] = truncated
    if not mappings:
        # ---- W-V2.2:标准枚举无解 ⇒ 有界键差 fallback ----
        return _infer_bond_diff_fallback(donor, union)
    return mappings


def _record_products_strict(products: list[str]) -> list:
    out = []
    for p in products:
        try:
            out.append(strict_identity_of(str(p)))
        except Exception:
            out.append(None)
    return out


def _executed_components_strict(target_smiles: str) -> list:
    mol = Chem.MolFromSmiles(target_smiles or "")
    if mol is None:
        return []
    out = []
    for frag in Chem.GetMolFrags(mol, asMols=True,
                                  sanitizeFrags=True):
        out.append(Chem.MolToSmiles(frag))
    return out


def _executed_components_strict_unified(target_smiles: str) -> list:
    """执行侧组件的**统一键空间**提取(R32-CS3-2;仅扩展 gate 用)。

    与 ``_record_products_strict`` 同一事实源(``strict_identity_of``
    = ``_identity_key`` CX 规范键);与现行裸 ``Chem.MolToSmiles``
    键空间的差异由调用方做一致性披露(裸键/严格键分歧计数,不静默
    吞)。缺省路径(无 declared_copies)不调用本函数——EAWAG/整串
    路径行为字节等价。
    """
    out: list = []
    try:
        mol = Chem.MolFromSmiles(target_smiles or "")
    except Exception:
        return [None]
    if mol is None:
        return [None]
    for frag in Chem.GetMolFrags(mol, asMols=True,
                                  sanitizeFrags=True):
        try:
            out.append(strict_identity_of(Chem.MolToSmiles(frag)))
        except Exception:
            out.append(None)
    return out


def _element_counts(mol) -> dict:
    """分子元素计数(不含隐式 H——归属判定是重原子图层面;隐式 H
    不进原子归属,读码推断按 RDKit 图语义,待执行核对已在设计书
    §五.1 落字)。"""
    counts: dict = {}
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        if sym == "H":
            continue
        counts[sym] = counts.get(sym, 0) + 1
    return counts


def _formula_counts_all(smiles: str) -> dict | None:
    """全元素计数(含隐式/显式 H;分子式配平代理口径,系数按 1 记
    且 unknown——非配平核验,诊断披露用)。不可解析 ⇒ None。"""
    mol = Chem.MolFromSmiles(str(smiles or ""))
    if mol is None:
        return None
    counts: dict = {}
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        if sym == "H":
            counts["H"] = counts.get("H", 0) + 1
        else:
            counts[sym] = counts.get(sym, 0) + 1
            h = atom.GetTotalNumHs()
            if h:
                counts["H"] = counts.get("H", 0) + h
    return counts


# B 类别代理标签(碳数零否;非化学生物角色规则——CO2 含碳归
# organic_like、铵无碳归 balance_like 的已知失真如实钉死;Codex v4
# 复审 §6 订正在案,只作诊断分栏不作判据)
def _cosubstrate_b_class(co_comps: list[str]) -> str:
    for comp in co_comps:
        mol = Chem.MolFromSmiles(str(comp))
        if mol is None:
            continue
        if any(a.GetSymbol() == "C" for a in mol.GetAtoms()):
            return "organic_like"
    return "balance_like"


def _classify_cosubstrate_candidate(
        *, matched_side: str, co_comps: list[str],
        products: list[str]) -> dict:
    """原子归属三分类守门(设计 §五.1/§五.2;编译器内部规则,**不进
    事件协议**——选项 b 已降级为守门基底层)。

    对 component 候选(LHS=A,记录产物 = 全量产物组分的并集)在
    推断映射(同源 ``infer_reaction_mapping``,判据单一来源)上把
    产物并集原子分为:
    - **A-可溯**:donor_to_union 映射覆盖的并集原子(new_union 补集);
    - **B-可溯**:new_union 中可归属某共底物组分 B 的原子(元素
      包含 + any-bond 子结构对应,预算沿用映射枚举纪律);
    - **不可归属**:new_union 中既不能归属 A 也不能归属任何 B 的
      原子(记录已声明 B 仍缺来源 ⇒ 源数据问题,R3-2 正交轴)。

    返回 {status, executable_products, copy_products, mapping_
    fallback, detail};status:
    - ``split``:存在候选映射使产物组分干净二分(可执行子集原子
      全部 A-可溯;拷贝组分断连且原子全部 B-可溯)——放行到
      ``compile_recorded_reaction`` 扩展分支;
    - ``bonded``:键合融合形态(同组分混 A-可溯与 B-可溯原子,或
      B 原子键合进 A 骨架/多 B 骨架并)⇒ 保守拒
      ``cosubstrate_bonded_contribution_unsupported``(拒因四轴
      子标签 R32-CS2-3 进 detail);
    - ``unattributable``:new_union 原子不可归属 ⇒ 保守拒
      ``cosubstrate_atom_source_unattributable``(T-3 主会话默认档
      子选项 i;mimo r32 R32-CS3-1 已裁;detail 带 mapping_
      fallback 分列);
    - ``no_mapping``/``truncated``/``unparseable``/
      ``no_executable_subset``:前置失败(与编译层同源理由)。

    确定性:按 ``infer_reaction_mapping`` 枚举序取**首个干净二分**
    映射;无可二分映射时按首映射证据定拒因(bonded 优先于
    unattributable——结构性拒因优先,子标签随 detail 披露)。
    """
    detail: dict = {}
    # NC-6:B SMILES 不可解析 ⇒ 候选级结构化拒(不猜不清洗)
    b_mols: list = []
    for comp in co_comps:
        mol = Chem.MolFromSmiles(str(comp))
        if mol is None:
            return {"status": "unparseable", "detail": {
                "co_substrate_smiles": str(comp)}}
        b_mols.append(mol)
    union = Chem.MolFromSmiles(".".join(str(p) for p in products))
    if union is None:
        return {"status": "no_mapping", "detail": {
            "note": "record products unparseable"}}
    frag_atom_sets = [
        set(f) for f in Chem.GetMolFrags(union, asMols=False)]
    try:
        mappings = infer_reaction_mapping(matched_side, products)
    except RecordedSourceError:
        return {"status": "no_mapping", "detail": {
            "note": "donor/products unparseable at mapping"}}
    if not mappings:
        return {"status": "no_mapping", "detail": {}}
    if mappings[0].get("truncated"):
        return {"status": "truncated", "detail": {}}

    def _attribute_to_single_b(product_smiles: str) -> str | None:
        """整组分归属:断连组分(原子全部 new)可整体对应到**单一** B
        (元素包含 + any-bond 子结构对应,预算沿用映射枚举纪律;多 B
        并合 ⇒ None 由调用方按骨架并拒)。组分串经展平后为单片段,
        直接解析(与 union 片段同图)。"""
        comp_mol = Chem.MolFromSmiles(str(product_smiles))
        if comp_mol is None:
            return None
        comp_elems = _element_counts(comp_mol)
        try:
            query = _any_bond_query(comp_mol)
        except Exception:
            query = None
        for b_mol in b_mols:
            b_elems = _element_counts(b_mol)
            if any(comp_elems.get(e, 0) > b_elems.get(e, 0)
                   for e in comp_elems):
                continue
            if query is not None and b_mol.HasSubstructMatch(
                    query, useChirality=False):
                return "copy"
        return None

    b_all_elems: dict = {}
    for b_mol in b_mols:
        for e, n in _element_counts(b_mol).items():
            b_all_elems[e] = b_all_elems.get(e, 0) + n

    for mapping in mappings:
        covered = set(mapping["donor_to_union"].values())
        new_atoms = set(mapping["new_union"])
        executable: list[str] = []
        copies: list[str] = []
        bonded_components: list[str] = []
        unattributable = False
        clean = True
        for frag_atoms, product in zip(frag_atom_sets, products):
            comp_new = frag_atoms & new_atoms
            if not comp_new:
                executable.append(str(product))
                continue
            comp_cov = frag_atoms - comp_new
            if comp_cov:
                # 同组分混 A-可溯与 new 原子 ⇒ 键合融合(设计 §五.2.3)
                clean = False
                bonded_components.append(str(product))
                continue
            # 全 new 原子的断连组分:归属单一 B ⇒ 拷贝;否则不可归属
            # (元素超出 A∪B)或多 B 骨架并(键合融合子形态)
            comp_mol = Chem.MolFromSmiles(str(product))
            comp_elems = (_element_counts(comp_mol)
                          if comp_mol is not None else {})
            if any(e not in b_all_elems for e in comp_elems):
                clean = False
                unattributable = True
                continue
            if _attribute_to_single_b(str(product)) == "copy":
                copies.append(str(product))
            else:
                # 元素可归 B 并集但非单一 B 对应 ⇒ 骨架并(B-B 融合)
                clean = False
                bonded_components.append(str(product))
        if clean:
            if not executable:
                # R32-CS2-4/NC-8:可执行子集为空(不得产空 expectation
                # 事件、不得把整产物集降级为拷贝绕行)
                return {"status": "no_executable_subset",
                        "executable_products": [],
                        "copy_products": copies,
                        "mapping_fallback":
                            "n_bond_diff" in mapping,
                        "detail": {
                            "copy_products": copies[:8],
                            "note": "no A-traceable executable product "
                                    "subset (pure record transcription "
                                    "must not impersonate prediction)"}}
            return {"status": "split",
                    "executable_products": executable,
                    "copy_products": copies,
                    "mapping_fallback": "n_bond_diff" in mapping,
                    "detail": {
                        "n_mappings": len(mappings),
                        "chosen_mapping_fallback":
                            "n_bond_diff" in mapping}}
    # ---- 无干净二分映射:按首映射证据定拒因(确定性) ----
    first = mappings[0]
    new_atoms = set(first["new_union"])
    bonded: list[str] = []
    unattr_products: list[str] = []
    # 每个键合组分的 (new 原子数, 是否混 A-可溯原子) —— bonded_kind
    # 子标签代理(R32-CS2-3):混 A 组分 new==1 ⇒ single_atom_
    # insertion;混 A 组分 new>1 ⇒ group_transfer;全 new 非单一 B
    # 对应 ⇒ skeleton_merge
    bonded_axes: list[dict] = []
    for frag_atoms, product in zip(frag_atom_sets, products):
        comp_new = frag_atoms & new_atoms
        if not comp_new:
            continue
        comp_cov = frag_atoms - comp_new
        if comp_cov:
            bonded.append(str(product))
            bonded_axes.append({
                "product": str(product)[:80],
                "n_new_atoms": len(comp_new),
                "mixed_with_a_traceable": True,
                "bonded_kind": ("single_atom_insertion"
                                if len(comp_new) == 1
                                else "group_transfer")})
            continue
        comp_mol = Chem.MolFromSmiles(str(product))
        comp_elems = (_element_counts(comp_mol)
                      if comp_mol is not None else {})
        if any(e not in b_all_elems for e in comp_elems):
            unattr_products.append(str(product))
        else:
            bonded.append(str(product))
            bonded_axes.append({
                "product": str(product)[:80],
                "n_new_atoms": len(comp_new),
                "mixed_with_a_traceable": False,
                "bonded_kind": "skeleton_merge"})
    # 分子式配平三态 + B 身份在产物 + B 类别(R32-CS2-3 四轴子标签)
    lhs_f: dict = {}
    rhs_f: dict = {}
    for s in [matched_side] + [str(c) for c in co_comps]:
        fc = _formula_counts_all(s)
        if fc is None:
            continue
        for e, n in fc.items():
            lhs_f[e] = lhs_f.get(e, 0) + n
    for s in [str(p) for p in products]:
        fc = _formula_counts_all(s)
        if fc is None:
            continue
        for e, n in fc.items():
            rhs_f[e] = rhs_f.get(e, 0) + n
    if lhs_f == rhs_f:
        balance_status = "balanced(coefficients=1,unknown)"
    elif any(rhs_f[e] > lhs_f.get(e, 0) for e in rhs_f):
        balance_status = "products_excess"
    else:
        balance_status = "reactants_excess"
    b_stricts = {_strict_of(str(c)) for c in co_comps}
    p_stricts = {_strict_of(str(p)) for p in products}
    detail.update({
        "bonded_products": bonded[:8],
        "unattributable_products": unattr_products[:8],
        "mapping_fallback": "n_bond_diff" in first,
        "bonded_kind_axes": {
            "per_component": bonded_axes[:8],
            "record_balance_status": balance_status,
            "b_class": _cosubstrate_b_class(co_comps),
            "b_identity_in_products": bool(b_stricts & p_stricts),
        },
        "note": (
            "bonded-fusion conservative reject: execution graph = "
            "render(substrate) (frozen 0d.1 chain), B is not in the "
            "execution graph; the only way to express B-bonded atoms "
            "in products is the add_atom channel, which r30 R2-2 "
            "forbids unconditionally (including declared sources; "
            "'disguise' strictly means the undeclared form per r31 "
            "R31-1 wording guard); known lost chemistry classes "
            "(mimo r32 R32-CS2-2): declared-water hydrolysis/"
            "hydration, declared-O2 bonded oxygen insertion "
            "(monooxygenase/hydroxylase-type), transferase-type "
            "group transfer into substrate products; oxidase-type "
            "(disconnected H2O2 product) and dehydrogenase-type "
            "(disconnected cofactor pair) are NOT in the loss face; "
            "no exceptions over LR/RL, anchorability, organic/"
            "cofactor, unknown role, balanced/unbalanced"),
    })
    if bonded:
        return {"status": "bonded", "executable_products": [],
                "copy_products": [], "mapping_fallback":
                    "n_bond_diff" in first, "detail": detail}
    return {"status": "unattributable", "executable_products": [],
            "copy_products": [], "mapping_fallback":
                "n_bond_diff" in first, "detail": detail}


def _flatten_product_entries(products: list[str]) -> list[str]:
    """产物条目展平到**组分**粒度(设计 §五.3:多重集比较的单位是
    组分;记录条目含 "." 的罕见形态(实测 186/43,177 行)统一展平,
    保证扩展 gate 两侧(执行片段/拷贝组分/记录组分)同粒度;不可
    解析条目原样透传——后续 union 解析失败 ⇒ 诚实拒,不猜)。"""
    flat: list[str] = []
    for p in products:
        s = str(p)
        mol = Chem.MolFromSmiles(s)
        if mol is None or "." not in s:
            flat.append(s)
            continue
        frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
        if not frags:
            flat.append(s)
            continue
        flat.extend(Chem.MolToSmiles(f) for f in frags)
    return flat


# ---------------------------------------------------------------- 主入口


def find_recorded_exact(
    *, substrate_smiles: str, engine,
    max_reactions: int = 24,
) -> dict:
    """当前底物的 recorded 精确源候选(W2 主入口)。

    返回 {candidates: [...], diagnostics: {...}}:
    - candidates(检索序,引擎 lookup 置顶序):每项 {record_id, tier
      (recorded_strict_exact|recorded_cn_candidate), donor_smiles,
      products(完整净产物集合,库行序), filter_flags, compile
      (compiled spec | None), compile_reason} —— compile 由
      ``compile_recorded_reaction`` 产生(推断映射,同一迁移结果);
    - diagnostics:n_lookup、n_reactions、strict/cn 计数、编译失败
      分层计数(unsupported 原因直方图)。

    严格分层:donor 严格身份 == 底物严格身份 ⇒ strict exact(编译产物
    逐组分 strict 核对一致才 spec);CN 同而 strict 异 ⇒ cn candidate
    (不升格,标 analog 级);方向 donor→products 由库行序承载。
    """
    raw = engine.expand_raw(str(substrate_smiles), case_id="recorded-source")
    if "error" in raw:
        return {"candidates": [], "diagnostics": {
            "kind": "engine_error", "error": str(raw.get("error"))}}
    index = load_library_index(engine)
    substrate_strict = _strict_of(substrate_smiles)
    substrate_cn = cn_identity(str(substrate_smiles))
    candidates: list[dict] = []
    seen_rids: set[str] = set()
    failure_hist: dict[str, int] = {}
    n_strict = n_cn = 0
    for row in raw.get("lookup") or []:
        for rid in row.get("eawag_reactions") or []:
            rid = str(rid)
            if rid in seen_rids or len(candidates) >= int(max_reactions):
                continue
            seen_rids.add(rid)
            record = index.get(rid)
            if record is None or not record.get("donor_smiles") \
                    or not record.get("products"):
                failure_hist["record_missing_or_incomplete"] = \
                    failure_hist.get("record_missing_or_incomplete", 0) + 1
                continue
            donor_strict = _strict_of(record["donor_smiles"])
            donor_cn = cn_identity(record["donor_smiles"])
            if donor_strict == substrate_strict:
                tier = "recorded_strict_exact"
                n_strict += 1
            elif donor_cn is not None and donor_cn == substrate_cn:
                tier = "recorded_cn_candidate"
                n_cn += 1
            else:
                # 引擎 lookup CN 键命中但库 donor CN 不同(索引键归一差
                # 异):按 analog 级披露,不升格
                tier = "recorded_cn_candidate"
                n_cn += 1
            compiled = compile_recorded_reaction(
                substrate_smiles=str(substrate_smiles),
                donor_smiles=record["donor_smiles"],
                products=list(record["products"]),
                record_id=rid)
            if compiled.get("status") != "compiled":
                reason = str(compiled.get("reason") or "unknown")
                failure_hist[reason] = failure_hist.get(reason, 0) + 1
            candidates.append({
                "record_id": rid,
                "tier": tier,
                "donor_smiles": record["donor_smiles"],
                "package": record.get("package", ""),
                "products": list(record["products"]),
                "filter_flags": {
                    "ion_filtered": bool(row.get("ion_filtered")),
                    "cofactor_filtered": bool(row.get("cofactor_filtered")),
                    "filtered": bool(row.get("filtered")),
                },
                "compile": compiled.get("spec"),
                "compile_status": str(compiled.get("status")),
                "compile_reason": str(compiled.get("reason") or ""),
                "compile_detail": dict(compiled.get("detail") or {}),
            })
    return {"candidates": candidates, "diagnostics": {
        "recorded_source_version": RECORDED_SOURCE_VERSION,
        "n_lookup_rows": len(raw.get("lookup") or []),
        "n_reactions": len(seen_rids),
        "n_strict_exact": n_strict,
        "n_cn_candidate": n_cn,
        "compile_failure_histogram": dict(sorted(failure_hist.items())),
    }}


def _strict_of(smiles: str) -> str | None:
    try:
        return strict_identity_of(str(smiles))
    except Exception:
        return None


# ---------------------------------------------------------------- W-V4.1 主入口


def find_corpus_recorded_exact(
    *, substrate_smiles: str, engine, max_reactions: int = 24,
) -> dict:
    """corpus_v1(RHEA/enviPath)recorded 直通候选(W-V4.1 主入口)。

    返回 {candidates: [...], diagnostics: {...}}(与 find_recorded_exact
    同构;corpus 特有字段见下):

    - 检索(W 决策①:**CN 宽**):底物 CN == 某记录 donor 组分 CN 或
      (多组分 donor)整串 CN ⇒ 该行入检索面;strict ⊆ CN,严格命中
      面天然包含;
    - 分层(同源判据,不另写比较器):匹配侧严格身份 == 底物严格身份
      ⇒ ``recorded_strict_exact``;CN 同而 strict 异 ⇒
      ``recorded_cn_candidate``(不升格);
    - 匹配侧语义(W 决策②):单组分 donor / 整串 CN 命中 ⇒ 整串
      (kind=whole,co_substrates 空);多组分 donor ⇒ 组分
      (kind=component,**其余组分声明为共底物/条件参与物**,
      co_substrates 携带组分 SMILES + 严格身份;不静默丢弃);
    - **W-V4.1-R1 共底物许可(S5B-V4-01 回修;corpus-retrieval-2
      历史行为)**:kind=component 且 co_substrates 非空 ⇒ 编译前
      结构化 unsupported(单一类目 ``corpus_cosubstrate_
      participants_unsupported``,298 题面实测 1,323)。
      **W-D2(s5b-corpus-retrieval-3,现行行为)**:该许可升级为
      **原子归属三分类守门三分支**——整组分拷贝子集放行(B 进
      事件反应物侧参与物 role=cosubstrate、系数 unknown;B 来源
      整组分产物声明式拷贝、中心 unknown、不执行;participants/
      states/event_contract 随 spec 装配,消费见 production.
      prepare_hypothesis)、键合融合子集保守拒(``cosubstrate_
      bonded_contribution_unsupported``,四轴子标签)、不可归属
      原子保守拒(``cosubstrate_atom_source_unattributable``,
      mapping_fallback 分列)、可执行子集空拒(NC-8)、B 不可解析
      拒(NC-6);守门在本入口生效——builder 池与公开链从源头拿
      不到坏 spec(不出现"builder 单口过滤而 find 仍返回可用坏
      spec"的分裂);拒因不按元素/角色/可锚性/方向/具体分子设
      例外(可锚有机/不可锚辅因子/未知角色/同根 LR/RL 全覆盖);
      add_atom 伪装机器断言(NC-3)随编译成功路径兜底;
    - 行级拒因(W 决策③+负控 ⑧⑨⑩):通配行 unsupported_wildcard_
      atom;原生映射冒充 corpus_native_mapping_claimed(corpus_v1 全
      库无原生映射,mapping_origin=inferred 强制);provenance 缺
      corpus_provenance_missing;无产物 record_missing_or_incomplete
      ——全部计数入 compile_failure_histogram(检索面统计仍全量);
    - 编译(**完整净产物集合核**):整串 donor → 记录全量产物,走
      同一 ``compile_recorded_reaction``(推断映射/产物多重集 gate/
      歧义披露,判据零改动);spec 附加 corpus 元数据(source_type/
      master_id/direction/ec/匹配语义/共底物声明=空集);
    - 方向(W 决策③):按**各自行书写**编译(donor_A→product_B;
      direction 为记录声明);master 双行均保留为候选(双方向分层
      引用);同一 master 多行命中仅诊断披露(同净反应双槽由池侧
      同签名去重防);
    - 候选序(确定性):(tier, whole<component, 行号, 组分序);
      max_reactions 以候选数截断(与 EAWAG 同语义)。
    """
    substrate = str(substrate_smiles)
    substrate_cn = cn_identity(substrate)
    if substrate_cn is None:
        return {"candidates": [], "diagnostics": {
            "corpus_retrieval_version": CORPUS_RETRIEVAL_VERSION,
            "kind": "substrate_unparseable",
            "note": "底物不可解析:corpus 检索面为空(诚实,不猜)"}}
    index = load_corpus_index(engine)
    records = index["records"]
    substrate_strict = _strict_of(substrate)
    # ---- 检索面(CN 宽;行级) ----
    whole_rows = set(index["cn_whole_index"].get(substrate_cn) or [])
    comp_entries = list(
        index["cn_component_index"].get(substrate_cn) or [])
    row_state: dict[int, dict] = {}
    for i in whole_rows:
        row_state.setdefault(i, {"whole": False, "sides": {}})
        row_state[i]["whole"] = True
    for i, comp_idx in comp_entries:
        record = records[i]
        state = row_state.setdefault(i, {"whole": False, "sides": {}})
        if state["whole"]:
            continue  # 整串命中优先:组分侧并入整串语义(不双计)
        comps = record["donor_components"]
        if len(comps) <= 1:
            # 单组分 donor:组分命中 = 整串语义(EAWAG 等价形态)
            state["whole"] = True
            continue
        side_strict = _strict_of(comps[comp_idx]) or comps[comp_idx]
        # 同一记录内同身份组分去重(重复组分不产双候选;
        # 不同身份组分各自成候选,分层引用)
        state["sides"].setdefault(side_strict, comp_idx)
    # ---- 行级适配拒因(负控 ⑧⑨⑩ + 无产物;检索面全量计数) ----
    failure_hist: dict[str, int] = {}
    n_master_rows: dict[str, set[int]] = {}
    ordered_matches: list[tuple] = []
    for i, state in row_state.items():
        record = records[i]
        if record["master_id"]:
            n_master_rows.setdefault(
                record["master_id"], set()).add(record["line_no"])
        donor_a = record["donor_A_smiles"]
        comps = record["donor_components"]
        products = record["products"]
        # ⑩ 通配行拒因(行级:donor/产物任一侧含 *;donor 侧通配组分
        # 不可检索=天然不供给,产品侧/共组分通配检索到即拒并计数)
        if "*" in donor_a or any("*" in c for c in comps) \
                or any("*" in p for p in products):
            failure_hist["unsupported_wildcard_atom"] = \
                failure_hist.get("unsupported_wildcard_atom", 0) + 1
            continue
        # ⑧ 原生映射冒充拒(corpus_v1 全库 absent/null;非此形态 ⇒ 拒)
        if str(record.get("mapping_status") or "") != "absent" \
                or record.get("atom_mapping") is not None:
            failure_hist["corpus_native_mapping_claimed"] = \
                failure_hist.get("corpus_native_mapping_claimed", 0) + 1
            continue
        # ⑨ provenance 缺失拒(存在性披露;实测 enviPath 5,497 行)
        if not record.get("provenance_sha256"):
            failure_hist["corpus_provenance_missing"] = \
                failure_hist.get("corpus_provenance_missing", 0) + 1
            continue
        # ⑥' 无产物(enviPath educt-only / no-structure)诚实拒
        if not products:
            failure_hist["record_missing_or_incomplete"] = \
                failure_hist.get("record_missing_or_incomplete", 0) + 1
            continue
        # ---- 候选侧装配(整串 / 组分) ----
        if state["whole"]:
            matched_side = donor_a
            side_strict = _strict_of(matched_side)
            tier = ("recorded_strict_exact"
                    if substrate_strict is not None
                    and side_strict == substrate_strict
                    else "recorded_cn_candidate")
            tier_rank = 0 if tier == "recorded_strict_exact" else 1
            ordered_matches.append((
                tier_rank, 0, record["line_no"], 0, i, "whole",
                matched_side, []))
            continue
        for side_key, rep_idx in state["sides"].items():
            matched_side = comps[rep_idx]
            tier = ("recorded_strict_exact"
                    if substrate_strict is not None
                    and side_key == substrate_strict
                    else "recorded_cn_candidate")
            tier_rank = 0 if tier == "recorded_strict_exact" else 1
            co_comps = [c for j, c in enumerate(comps) if j != rep_idx]
            ordered_matches.append((
                tier_rank, 1, record["line_no"], rep_idx, i,
                "component", matched_side, co_comps))
    ordered_matches.sort(key=lambda m: (m[0], m[1], m[2], m[3]))
    # ---- 逐候选编译(判据零改动;同 max_reactions 截断语义) ----
    candidates: list[dict] = []
    n_strict = n_cn = 0
    n_cosub_compiled = 0        # D2:三分支放行并编译成功的拷贝型 spec
    n_cosub_rejected = 0        # D2:三分支守门拒(component 面)
    cosub_b_class: Counter = Counter()  # D2 T-4:B 类别代理剖面
    for (tier_rank, _kind_rank, _line_no, _rep_idx, i, kind,
         matched_side, co_comps) in ordered_matches:
        if len(candidates) >= int(max_reactions):
            break
        record = records[i]
        tier = ("recorded_strict_exact" if tier_rank == 0
                else "recorded_cn_candidate")
        if tier == "recorded_strict_exact":
            n_strict += 1
        else:
            n_cn += 1
        # ---- W-V4.1-R1:共底物 component 编译前许可(S5B-V4-01) ----
        # 没有已审定且实际消费的共底物参与物/原子来源语义 ⇒ 有共底物
        # 的 component 记录不送单组分 LHS 编译:结构化 unsupported
        # (保留源行/方向/共底物声明/可追溯拒因),不产 spec、不产
        # event。共用许可规则在本入口生效(builder 池/公开链从源头
        # 拿不到坏 spec);不按元素/角色/可锚性/方向/具体分子设例外
        # ——可锚有机共底物(键合原子经 add_atom 折成"新增原子")与
        # 不可锚断连辅因子同根同拒,LR/RL 双方向全覆盖。唯一放行
        # 证明 = 显式共底物参与物语义经独立设计+化学评审落地并实际
        # 消费(mimo r30 R2-2 诚实拒分支;Codex v4 复审 §4.3 最低
        # 收口;不搭车放宽产物多重集 gate、不改 AtomTool/冻结判据)。
        if kind == "component" and co_comps:
            # ---- W-D2(s5b-corpus-retrieval-3):共底物 component 三分
            # 支守门(原子归属三分类 → 拷贝放行 / 键合拒 / 不可归属拒;
            # 设计书 §四 方案 a + §五 全部规则 + mimo r32 十六条)。
            # 拒因类目迁移:corpus_cosubstrate_participants_unsupported
            # (corpus-retrieval-2 单类,298 面实测 1,323)分裂为下列
            # 结构化子类——迁移是通道开放不是错误修复(R31-6 禁句
            # 沿用;编译成功子集从拒因直方图消失 = 放行不是消失,其
            # 计数由 n_cosubstrate_component_compiled 承接)。
            # T-4:B 类别代理剖面(碳数零否;非化学生物角色规则,
            # CO2 含碳归 organic_like、铵无碳归 balance_like 的已知
            # 失真钉死——Codex v4 复审 §6;只作诊断分栏不作判据)
            cosub_b_class[_cosubstrate_b_class(co_comps)] += 1
            flat_products = _flatten_product_entries(
                list(record["products"]))
            try:
                cls = _classify_cosubstrate_candidate(
                    matched_side=matched_side, co_comps=co_comps,
                    products=flat_products)
            except RecordedSourceError as exc:
                reason = str(exc.detail.get("kind")
                             or "record_unparseable")
                failure_hist[reason] = failure_hist.get(reason, 0) + 1
                n_cosub_rejected += 1
                candidates.append(_corpus_candidate(
                    record, tier, kind, matched_side, co_comps,
                    compile_spec=None, compile_status="unsupported",
                    compile_reason=reason, compile_detail={
                        "record_key": record["record_key"],
                        "line_no": record["line_no"],
                        "donor_A_smiles": record["donor_A_smiles"],
                        "direction": record["direction"],
                        "master_id": record["master_id"],
                        "matched_component": matched_side,
                        "co_substrates": [
                            {"smiles": str(c),
                             "strict_identity": _strict_of(str(c))}
                            for c in co_comps],
                        "products": list(record["products"]),
                        "permission_note": (
                            "D2 structured reject (classification "
                            "input failure); declared co-substrates "
                            "retained for traceability; REBUILDING a "
                            "usable pool spec from this detail "
                            "violates the permission boundary (r31 "
                            "R31-8)"),
                    }))
                continue
            status = str(cls.get("status"))
            if status == "split":
                compiled = None
                try:
                    compiled = compile_recorded_reaction(
                        substrate_smiles=substrate,
                        donor_smiles=matched_side,
                        products=list(cls["executable_products"]),
                        record_id=record["record_key"],
                        declared_copies=list(cls["copy_products"]),
                        record_products=flat_products)
                except RecordedSourceError as exc:
                    reason = str(exc.detail.get("kind")
                                 or "record_unparseable")
                    failure_hist[reason] = failure_hist.get(
                        reason, 0) + 1
                    n_cosub_rejected += 1
                    candidates.append(_corpus_candidate(
                        record, tier, kind, matched_side, co_comps,
                        compile_spec=None,
                        compile_status="unsupported",
                        compile_reason=reason, compile_detail={
                            "record_key": record["record_key"],
                            "line_no": record["line_no"],
                            "donor_A_smiles": record["donor_A_smiles"],
                            "direction": record["direction"],
                            "master_id": record["master_id"],
                            "matched_component": matched_side,
                            "co_substrates": [
                                {"smiles": str(c),
                                 "strict_identity": _strict_of(str(c))}
                                for c in co_comps],
                            "products": list(record["products"]),
                            "permission_note": (
                                "D2 structured reject (cosubstrate "
                                "component split branch); declared "
                                "co-substrates retained for "
                                "traceability; REBUILDING a usable "
                                "pool spec from this detail violates "
                                "the permission boundary (r31 R31-8)"),
                        }))
                    continue
                if compiled.get("status") != "compiled":
                    reason = str(compiled.get("reason") or "unknown")
                    failure_hist[reason] = failure_hist.get(
                        reason, 0) + 1
                    n_cosub_rejected += 1
                    reject_detail = dict(compiled.get("detail") or {})
                    reject_detail.update({
                        "record_key": record["record_key"],
                        "line_no": record["line_no"],
                        "donor_A_smiles": record["donor_A_smiles"],
                        "direction": record["direction"],
                        "master_id": record["master_id"],
                        "matched_component": matched_side,
                        "co_substrates": [
                            {"smiles": str(c),
                             "strict_identity": _strict_of(str(c))}
                            for c in co_comps],
                        "products": list(record["products"]),
                        "mapping_fallback": bool(
                            cls.get("mapping_fallback")),
                        "permission_note": (
                            "D2 structured reject (cosubstrate "
                            "component split branch; compile-layer "
                            "reason on the executable subset); "
                            "declared co-substrates retained for "
                            "traceability; REBUILDING a usable pool "
                            "spec from this detail violates the "
                            "permission boundary (r31 R31-8)"),
                    })
                    candidates.append(_corpus_candidate(
                        record, tier, kind, matched_side, co_comps,
                        compile_spec=None,
                        compile_status="unsupported",
                        compile_reason=reason,
                        compile_detail=reject_detail))
                    continue
                spec = compiled.get("spec")
                # ---- NC-3(设计 §五.2.5):add_atom 伪装机器断言 ——
                # 拷贝/键合已被结构性排除,component 候选产出的 spec
                # 的 edits 不得含任何 add_atom(防未来实现漂移,触发
                # 即结构化拒)。
                if any(str(e.get("op")) == "add_atom"
                       for e in spec.get("edits") or []):
                    reason = ("cosubstrate_executable_add_atom_"
                              "regression_guard")
                    failure_hist[reason] = failure_hist.get(
                        reason, 0) + 1
                    n_cosub_rejected += 1
                    candidates.append(_corpus_candidate(
                        record, tier, kind, matched_side, co_comps,
                        compile_spec=None,
                        compile_status="unsupported",
                        compile_reason=reason, compile_detail={
                            "record_key": record["record_key"],
                            "line_no": record["line_no"],
                            "donor_A_smiles": record["donor_A_smiles"],
                            "direction": record["direction"],
                            "master_id": record["master_id"],
                            "matched_component": matched_side,
                            "co_substrates": [
                                {"smiles": str(c),
                                 "strict_identity": _strict_of(str(c))}
                                for c in co_comps],
                            "products": list(record["products"]),
                            "note": ("executable-subset spec must not "
                                     "contain add_atom edits (B atoms "
                                     "must never enter products via "
                                     "the add_atom channel; r30 R2-2 "
                                     "unconditional)"),
                        }))
                    continue
                spec = dict(spec)
                try:
                    _attach_cosubstrate_spec_fields(
                        spec, substrate_smiles=substrate,
                        record=record, matched_side=matched_side,
                        co_comps=co_comps,
                        record_products_flat=flat_products,
                        copy_products=list(cls["copy_products"]))
                except _ChemStateBuildFailure as exc:
                    reason = str(exc.detail.get("kind"))
                    failure_hist[reason] = failure_hist.get(
                        reason, 0) + 1
                    n_cosub_rejected += 1
                    candidates.append(_corpus_candidate(
                        record, tier, kind, matched_side, co_comps,
                        compile_spec=None,
                        compile_status="unsupported",
                        compile_reason=reason,
                        compile_detail=dict(exc.detail)))
                    continue
                n_cosub_compiled += 1
                candidates.append(_corpus_candidate(
                    record, tier, kind, matched_side, co_comps,
                    compile_spec=spec,
                    compile_status=str(compiled.get("status")),
                    compile_reason="",
                    compile_detail=dict(compiled.get("detail") or {})))
                continue
            reason_map = {
                "bonded": "cosubstrate_bonded_contribution_unsupported",
                "unattributable":
                    "cosubstrate_atom_source_unattributable",
                "unparseable": "cosubstrate_unparseable",
                "no_mapping": "no_structure_correspondence",
                "truncated": "mapping_enumeration_truncated",
                "no_executable_subset":
                    "cosubstrate_no_executable_product_subset",
            }
            reason = reason_map.get(status, "cosubstrate_unsupported")
            failure_hist[reason] = failure_hist.get(reason, 0) + 1
            n_cosub_rejected += 1
            if reason == "cosubstrate_atom_source_unattributable":
                # R32-CS3-1:不可归属拒因子 mapping_fallback 分列
                # (bond-diff 回退映射伪影 vs 源记录真实缺原子,两类
                # 计数分列,不得合并为"源数据不配平"单一结论)
                fb_key = ("cosubstrate_unattributable_"
                          "mapping_fallback_"
                          + ("true" if cls.get("mapping_fallback")
                             else "false"))
                failure_hist[fb_key] = failure_hist.get(fb_key, 0) + 1
            detail = dict(cls.get("detail") or {})
            detail.update({
                "record_key": record["record_key"],
                "line_no": record["line_no"],
                "donor_A_smiles": record["donor_A_smiles"],
                "direction": record["direction"],
                "master_id": record["master_id"],
                "matched_component": matched_side,
                "co_substrates": [
                    {"smiles": str(c),
                     "strict_identity": _strict_of(str(c))}
                    for c in co_comps],
                "products": list(record["products"]),
                "mapping_fallback": bool(cls.get("mapping_fallback")),
                "permission_note": (
                    "D2 structured reject (s5b-corpus-retrieval-3): "
                    "the component record's co-substrate contribution "
                    "is NOT compilable under the current execution "
                    "contract; declared co-substrates and record "
                    "products are retained here for traceability; "
                    "REBUILDING a usable pool spec from this detail "
                    "violates the permission boundary (r31 R31-8)"),
            })
            candidates.append(_corpus_candidate(
                record, tier, kind, matched_side, co_comps,
                compile_spec=None, compile_status="unsupported",
                compile_reason=reason, compile_detail=detail))
            continue
        products = list(record["products"])
        try:
            compiled = compile_recorded_reaction(
                substrate_smiles=substrate,
                donor_smiles=matched_side,
                products=products,
                record_id=record["record_key"])
        except RecordedSourceError as exc:
            reason = str(exc.detail.get("kind") or "record_unparseable")
            failure_hist[reason] = failure_hist.get(reason, 0) + 1
            candidates.append(_corpus_candidate(
                record, tier, kind, matched_side, co_comps,
                compile_spec=None, compile_status="unsupported",
                compile_reason=reason, compile_detail={}))
            continue
        if compiled.get("status") != "compiled":
            reason = str(compiled.get("reason") or "unknown")
            failure_hist[reason] = failure_hist.get(reason, 0) + 1
        spec = compiled.get("spec")
        if spec is not None:
            spec = dict(spec)
            spec["corpus"] = {
                "corpus_retrieval_version": CORPUS_RETRIEVAL_VERSION,
                "source_type": record["source_type"],
                "record_key": record["record_key"],
                "master_id": record["master_id"],
                "direction": record["direction"],
                "ec": record["ec"],
                "donor_match_kind": kind,
                "matched_component": matched_side,
                "co_substrates": [
                    {"smiles": str(c),
                     "strict_identity": _strict_of(str(c))}
                    for c in co_comps],
                "co_substrate_semantics": (
                    # R31-5 死分支注记:component-with-cosubstrate 候选
                    # 在上方 D2 分支处理完毕(放行/守门拒),不再到达
                    # 本 whole 编译路径——本第一分支自 corpus-retrieval-3
                    # 起不可达,保留字符串防读码者据旧语义复活组分路径。
                    "declared_conditional_participants_not_consumed"
                    "_as_substrate(W-V4.1 决策②历史语义;UNREACHABLE "
                    "since corpus-retrieval-3: component-with-"
                    "co-substrate candidates are handled by the D2 "
                    "three-branch gate above and never reach the "
                    "whole-string compile path)"
                    if co_comps else
                    "empty_set_whole_string_semantics"
                    "(corpus-retrieval-3:component-with-co-substrate "
                    "candidates pass the D2 atomic-attribution gate "
                    "above; whole-string compiled specs carry empty "
                    "co-substrate declaration)"),
                "provenance_sha256": record["provenance_sha256"],
            }
        candidates.append(_corpus_candidate(
            record, tier, kind, matched_side, co_comps,
            compile_spec=spec,
            compile_status=str(compiled.get("status")),
            compile_reason=str(compiled.get("reason") or ""),
            compile_detail=dict(compiled.get("detail") or {})))
    multirow = {mid: sorted(rows) for mid, rows in n_master_rows.items()
                if len(rows) > 1}
    # ---- T-4 供给诊断分层(W-D2 机读;R31-4/R32-CS5-3 标签纪律)----
    # 拒因直方图迁移披露:corpus_cosubstrate_participants_unsupported
    # (corpus-retrieval-2 单类)分裂为 cosubstrate_bonded_contribution_
    # unsupported / cosubstrate_atom_source_unattributable(+mapping_
    # fallback 分列键)/ cosubstrate_unparseable / cosubstrate_no_
    # executable_product_subset / cosubstrate_executable_add_atom_
    # regression_guard + 可执行子集编译层拒因;编译成功子集从直方图
    # 消失 = 放行不是消失,其计数由 n_cosubstrate_component_compiled
    # 承接(R32-CS5-4 迁移承接句)。
    n_cosub_face = n_cosub_compiled + n_cosub_rejected
    cosub_reject_split = {
        k: v for k, v in sorted(failure_hist.items())
        if k.startswith("cosubstrate_")}
    return {"candidates": candidates, "diagnostics": {
        "corpus_retrieval_version": CORPUS_RETRIEVAL_VERSION,
        "corpus_retrieval_semantics": dict(CORPUS_RETRIEVAL_SEMANTICS),
        "corpus_v1_sha256": index["corpus_v1_sha256"],
        "corpus_n_rows": index["n_rows"],
        "n_matched_rows": len(row_state),
        "n_failure_events": sum(failure_hist.values()),
        "n_strict_exact": n_strict,
        "n_cn_candidate": n_cn,
        # R31-4 计数标签进数据(文档标签不替代机读标签)
        "tier_count_semantics": (
            "retrieval_candidates_including_precompile_rejected; "
            "not compiled/supply counts"),
        "n_cosubstrate_component_candidates": n_cosub_face,
        "n_cosubstrate_component_compiled": n_cosub_compiled,
        "n_cosubstrate_component_rejected": n_cosub_rejected,
        "cosubstrate_supply_labels": {
            "count_unit": "question_x_candidate_entries(raw_top 截断后)",
            "count_basis": "retrieval_face",
            "cosubstrate_reject_split": cosub_reject_split,
            "cosubstrate_class_profile": {
                "count_unit": "question_x_candidate_entries",
                "label": ("碳数零否代理,非化学生物角色规则"
                          "(CO2 含碳归 organic_like、铵无碳归 "
                          "balance_like 的已知失真;Codex v4 复审 "
                          "§6)——只作诊断分栏不作判据"),
                **{k: v for k, v in sorted(
                    cosub_b_class.items())}},
            "migration_note": (
                "corpus_cosubstrate_participants_unsupported (v2, "
                "298-face measured 1323) splits into the "
                "cosubstrate_* categories above; the split is a "
                "channel opening, not an error fix (R31-6 headline "
                "ban applies); compiled-successful candidates leave "
                "the reject histogram = released, not vanished; the "
                "successor count is n_cosubstrate_component_compiled"),
            "expected_match_semantics": (
                "n_cosubstrate_component_compiled counts compiled "
                "SPECS at the retrieval layer, not events; the event "
                "count is downstream and partial-matching under "
                "current P1 (structurally no strict path, NC-12)"),
        },
        "n_master_multirow": len(multirow),
        "master_multirow_examples": dict(list(multirow.items())[:8]),
        "compile_failure_histogram": dict(sorted(failure_hist.items())),
        "compile_failure_histogram_labels": {
            "includes_precompile_permission_rejects": True,
            "count_unit": "events(candidates;含编译前守门拒,非编译"
                          "尝试失败直方图的净面)",
        },
    }}


class _ChemStateBuildFailure(RuntimeError):
    """D2:B/拷贝组分状态构建失败(结构化;kind 进拒因)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _build_state_or_fail(smiles: str, *, record_key: str,
                         kind: str,
                         extra_refs: dict | None = None) -> dict:
    """同源 state 构建(严格身份内容寻址;失败 ⇒ 结构化拒不猜)。

    返回 {state_ref, smiles}——state_id = ``build_chemical_state``
    同源派生(结构内容寻址,与 production.prepare_hypothesis 重建
    同 ID;origin/source_refs 不进身份)。"""
    try:
        state = build_chemical_state(
            str(smiles), "source_product",
            [{"record": str(record_key), **(extra_refs or {})}])
    except Exception as exc:
        raise _ChemStateBuildFailure(
            f"cosubstrate spec state build failed:{kind}",
            {"kind": kind, "smiles": str(smiles)[:200],
             "record_key": str(record_key),
             "reason": f"{type(exc).__name__}:{str(exc)[:200]}"}) from exc
    return {"state_ref": state.state_id, "smiles": str(smiles)}


def _attach_cosubstrate_spec_fields(
        spec: dict, *, substrate_smiles: str, record: dict,
        matched_side: str, co_comps: list[str],
        record_products_flat: list[str],
        copy_products: list[str]) -> None:
    """W-D2:cosubstrate component spec 的参与物/状态/事件契约装配
    (设计 §四.3 事件形状细则;**协议层零新发明**——role 复用既有
    枚举,系数全 unknown,来源进 provenance 层不混入计量层)。

    - participants 显式列表(production.prepare_hypothesis 的
      ``spec["participants"]`` 覆盖路径;H02/H03 契约由构造层校验):
      A(reactant/primary_substrate)+ 逐个 B(reactant/cosubstrate)
      + 主产物(principal_product)+ 可执行其余组分(coproduct)
      + 逐个拷贝组分(product/coproduct;component_source 进
      declared_copy_components 披露,**不进 Participant 字段**);
    - ``participant_list_status=declared_complete``(T-2 主会话默认
      档:参与物清单完整度声明,不描述计量/配平完整性——R32-CS1-3
      措辞,stoichiometry 恒 unknown);
    - co_substrate_states(B 状态装配)+ declared_copy_components
      (拷贝组分机读披露:component_source=record_declared_copy +
      record_key/provenance_sha256 + execution_status=declared_
      not_executed;R32-CS1-1:身份轴 = 记录声明可核,生成轴 =
      未执行,两轴不得合并成"已生成/已核实");
    - cosubstrate_event_contract:NC-10 事件级端到端不变量的记录侧
      输入(production.prepare_hypothesis 消费并断言)。
    """
    record_key = str(record["record_key"])
    refs_meta = {"record": record_key,
                 "provenance_sha256": str(record["provenance_sha256"]
                                          or "")}
    substrate_entry = _build_state_or_fail(
        substrate_smiles, record_key=record_key,
        kind="cosubstrate_unparseable")
    # B 状态(声明共底物;NC-6 已在分类前置拒,此处构建失败 = CX
    # 守卫/工厂拒绝,同样结构化拒)
    b_entries: list[dict] = []
    for b in co_comps:
        entry = _build_state_or_fail(str(b), record_key=record_key,
                                     kind="cosubstrate_unparseable")
        b_entries.append({
            "smiles": str(b), "state_ref": entry["state_ref"],
            "source_ref": record_key,
            "strict_identity": _strict_of(str(b)),
        })
    # 拷贝组分状态(设计 §四.3.2:SMILES 不可解析 ⇒ 候选级结构化拒)
    copy_entries: list[dict] = []
    for c in copy_products:
        entry = _build_state_or_fail(
            str(c), record_key=record_key,
            kind="copy_component_unparseable",
            extra_refs={"component_source": "record_declared_copy"})
        copy_entries.append({
            "smiles": str(c), "state_ref": entry["state_ref"],
            "component_source": "record_declared_copy",
            "record_key": record_key,
            "provenance_sha256": str(
                record["provenance_sha256"] or ""),
            "execution_status": "declared_not_executed",
        })
    principal_entry = _build_state_or_fail(
        str(spec["product_smiles"]), record_key=record_key,
        kind="copy_component_unparseable")
    coproduct_entries = [
        _build_state_or_fail(str(c), record_key=record_key,
                             kind="copy_component_unparseable")
        for c in (spec.get("coproducts") or [])]

    def _participant(state_ref: str, side: str, role: str) -> dict:
        return {"state_ref": str(state_ref), "side": side,
                "role": role, "coefficient": None,
                "coefficient_status": "unknown"}

    participants: list[dict] = [
        _participant(substrate_entry["state_ref"], "reactant",
                     "primary_substrate")]
    participants.extend(
        _participant(e["state_ref"], "reactant", "cosubstrate")
        for e in b_entries)
    participants.append(_participant(
        principal_entry["state_ref"], "product", "principal_product"))
    participants.extend(
        _participant(e["state_ref"], "product", "coproduct")
        for e in coproduct_entries)
    participants.extend(
        _participant(e["state_ref"], "product", "coproduct")
        for e in copy_entries)
    spec["participants"] = participants
    spec["participant_list_status"] = "declared_complete"
    spec["co_substrate_states"] = b_entries
    spec["declared_copy_components"] = copy_entries
    spec["cosubstrate_event_contract"] = {
        "record_key": record_key,
        "co_substrates": [
            {"smiles": str(b), "strict_identity": _strict_of(str(b))}
            for b in co_comps],
        "record_products": list(record_products_flat),
        "copy_state_refs": [e["state_ref"] for e in copy_entries],
        "co_substrate_state_refs": [e["state_ref"] for e in b_entries],
        "invariant_note": (
            "NC-10 (r32 R32-CS3-3; W-D2-R1/s5b-corpus-retrieval-4): "
            "applicability is owned by the RECORD-SIDE single "
            "declaration source (this contract being a dict OR the "
            "spec corpus block declaring B/copy) — assembly arrays "
            "missing/null/empty or participants reduced/omitted can "
            "NOT disable the guard nor default to plain A->P "
            "assembly (first-consumption structured reject); record-"
            "declared co-substrate strict identities (contract "
            "UNION corpus merged) MUST be a subset of the event "
            "reactant-side cosubstrate state_refs AND the record "
            "product multiset MUST equal the event product-participant "
            "multiset (executed UNION declared-copy components); "
            "asserted at production.prepare_hypothesis before the "
            "event is submitted; spec-layer gate pass does NOT "
            "substitute the event-layer check"),
    }
    # corpus 元数据块(component 分支;whole 分支沿用下方主路径)
    spec["corpus"] = {
        "corpus_retrieval_version": CORPUS_RETRIEVAL_VERSION,
        "source_type": record["source_type"],
        "record_key": record_key,
        "master_id": record["master_id"],
        "direction": record["direction"],
        "ec": record["ec"],
        "donor_match_kind": "component",
        "matched_component": str(matched_side),
        "co_substrates": [
            {"smiles": str(b), "strict_identity": _strict_of(str(b))}
            for b in co_comps],
        "co_substrate_semantics": (
            "declared_explicit_participants(D2/corpus-retrieval-3:"
            "B 进事件反应物侧 role=cosubstrate;B 来源整组分产物"
            "声明式拷贝 record_declared_copy,中心 unknown,不执行;"
            "键合融合/不可归属子集结构化拒;事件在现行 P1 下判"
            "matched_participant_coverage_partial,结构性无 strict "
            "通路——NC-12 批级熔断)"),
        "record_products": list(record_products_flat),
        "provenance_sha256": record["provenance_sha256"],
    }


def _corpus_candidate(record: dict, tier: str, kind: str,
                      matched_side: str, co_comps: list[str],
                      *, compile_spec, compile_status: str,
                      compile_reason: str, compile_detail: dict) -> dict:
    """corpus 候选条目(find_recorded_exact 同构 + corpus 特有字段)。"""
    return {
        "record_id": record["record_id"],
        "record_key": record["record_key"],
        "tier": tier,
        "donor_smiles": matched_side,
        "donor_match_kind": kind,
        "matched_component": matched_side,
        "co_substrates": [
            {"smiles": str(c), "strict_identity": _strict_of(str(c))}
            for c in co_comps],
        "direction": record["direction"],
        "master_id": record["master_id"],
        "ec": record["ec"],
        "source_type": record["source_type"],
        "package": f"corpus:{record['source_type']}",
        "products": list(record["products"]),
        "provenance_sha256": record["provenance_sha256"],
        "filter_flags": {
            "ion_filtered": False,
            "cofactor_filtered": False,
            "filtered": False,
        },
        "compile": compile_spec,
        "compile_status": compile_status,
        "compile_reason": compile_reason,
        "compile_detail": compile_detail,
    }


def compile_recorded_reaction(
    *, substrate_smiles: str, donor_smiles: str,
    products: list[str], record_id: str,
    declared_copies: list[str] | None = None,
    record_products: list[str] | None = None,
) -> dict:
    """库记录(donor + 完整净产物集合)→ PPV1 池 spec(推断映射)。

    - 结构对应:元素标记 any-bond 同构枚举(有界;W2 约束);
    - 每个候选映射构建 mapped_lhs/mapped_rhs(map 号联结),走
      ``compile_donor_template``(W1 共同编译器,单一构建源);
    - 同目标映射合并;异目标 ⇒ ambiguous(歧义披露拒绝);
    - strict exact 校验(调用方 find_recorded_exact 之后的最终门):
      编译执行产物按组分 strict 身份多重集 == 库记录产物多重集;
      离去组分缺产物/过滤缺失 ⇒ product_set_mismatch(诚实拒)。
    - 中心 = 推断变换的变化原子(键变化端点 + 新增/离去;推断映射的
      反应中心,非机制证据);
    - mapping_origin=inferred(spec 与诊断如实标注)。

    **W-D2(S5b-recorded-source-3,可选参数;设计 §五.3 落点子选项
    i)**:``declared_copies`` + ``record_products``(corpus component
    共底物拷贝路径专用)⇒ 在既有最终门之上追加 **union gate**:
    执行组分多重集 ∪ 声明拷贝组分多重集 == 记录(全量)产物多重集
    (严格身份、多重集、``strict_identity_of`` 键空间两侧统一
    R32-CS3-2 + 裸键/严格键一致性披露);拷贝身份 ≠ 记录产物组分
    ⇒ declared_copy_mismatch(NC-4);并集不齐 ⇒ product_set_
    mismatch 语义沿用;拷贝不可解析 ⇒ copy_component_unparseable。
    **缺省 None ⇒ 扩展分支零触碰(EAWAG/整串路径行为字节等价,
    负控断言回归)**;gate 是组分身份完整转写核对,**不是**元素/
    电荷配平核验(配平轴状态恒为判据二 unknown,系数全 unknown;
    R32-CS1-2 措辞)。``products`` 参数在扩展模式下 = 可执行子集
    (A 原子全部可溯的产物组分);扩展模式在可复现 spec 中优先选
    无 add_atom 编辑者(可执行子集原子全部 A-可溯 ⇒ 结构上不应有
    新原子;防御性选择,不改变缺省路径行为)。
    """
    mappings = infer_reaction_mapping(donor_smiles, products)
    if not mappings:
        return {"status": "unsupported", "reason": "no_structure_correspondence",
                "detail": {"record_id": record_id}}
    if mappings[0].get("truncated"):
        return {"status": "unsupported",
                "reason": "mapping_enumeration_truncated",
                "detail": {"record_id": record_id,
                           "note": "结构同构枚举触顶(歧义不可闭合,拒绝)"}}
    compiled_specs: list[dict] = []
    reasons: set[str] = set()
    for mapping in mappings:
        donor_to_union = mapping["donor_to_union"]
        new_union = mapping["new_union"]
        removed_donor = mapping["removed_donor"]
        # map 号:donor idx → 1..N;union 新原子 → N+1..
        donor_map = {idx: i + 1 for i, idx in enumerate(
            sorted(donor_to_union) + sorted(removed_donor))}
        union_map = {donor_to_union[d]: donor_map[d] for d in donor_to_union}
        n_donor = donor_map and max(donor_map.values()) or 0
        for k, u_idx in enumerate(sorted(new_union)):
            union_map[u_idx] = n_donor + 1 + k
        donor_mol = Chem.MolFromSmiles(donor_smiles)
        union_mol = Chem.MolFromSmiles(".".join(products))
        if donor_mol is None or union_mol is None:
            return {"status": "unsupported", "reason":
                    "record_unparseable", "detail": {"record_id": record_id}}
        mapped_lhs = _mapped_copy(donor_mol, donor_map)
        mapped_rhs = _mapped_copy(union_mol, union_map)
        # 中心 = 变化原子(键变化端点 + 新增 + 离去)
        center = _changed_maps(mapped_lhs, mapped_rhs)
        out = compile_donor_template(
            mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
            center_atoms=center, substrate_smiles=substrate_smiles,
            record_id=record_id, mapping_origin="inferred",
            alignment_ref=f"recorded-inferred:{record_id}",
            key_prefix="rec")
        if out.get("status") == "compiled":
            out = dict(out)
            out["n_bond_diff"] = int(mapping.get("n_bond_diff") or 0)
            compiled_specs.append(out)
        else:
            reasons.add(str(out.get("reason")))
    if not compiled_specs:
        return {"status": "unsupported",
                "reason": (sorted(reasons)[0] if reasons
                           else "no_compilable_mapping"),
                "detail": {"record_id": record_id,
                           "all_reasons": sorted(reasons)[:8]}}
    targets = {spec["spec"]["expectation"]["target_smiles"]
               for spec in compiled_specs}
    recorded = sorted(x for x in
                      _record_products_strict(products) if x)
    # ---- W-V2.3:产物多重集 gate 在**全部候选映射**上评估,择产物集
    # 可复现者(存在至少一个映射使 executed 组分多重集 == 库记录产物
    # 多重集;等价映射同集合并、确定性选首 —— 选首是工程事实,不是
    # 映射唯一性证明,mimo r29-F2)。无可复现者:保留原判据 —— 多
    # distinct 目标 ⇒ ambiguous(歧义披露拒绝);单目标 ⇒
    # product_set_mismatch(过滤缺失/对应错误诚实拒,不冒充完整 record)。
    reproducible = [
        spec for spec in compiled_specs
        if sorted(_executed_components_strict(
            spec["spec"]["expectation"]["target_smiles"])) == recorded]
    if reproducible:
        chosen = reproducible[0]
        if declared_copies is not None:
            # W-D2 防御性选择:可执行子集原子全部 A-可溯 ⇒ 结构上
            # 不应出现 add_atom 编辑;等价可复现 spec 中优先选无
            # add_atom 者(缺省路径选首逻辑不动 ⇒ 字节等价)。
            no_add = [
                spec for spec in reproducible
                if not any(str(e.get("op")) == "add_atom"
                           for e in (spec["spec"].get("edits")
                                     or []))]
            if no_add:
                chosen = no_add[0]
    elif len(targets) > 1:
        return {"status": "unsupported", "reason": "ambiguous_mapping",
                "detail": {"record_id": record_id,
                           "competing_targets": sorted(targets)[:8],
                           "n_mappings": len(mappings),
                           "n_reproducible": 0,
                           "note": ("全部候选映射无一复现库记录净产物集合"
                                    "(歧义不可闭合,拒绝)")}}
    else:
        chosen = compiled_specs[0]
    spec = chosen["spec"]
    # ---- strict exact 最终门:执行产物组分 == 库记录产物(多重集) ----
    executed = sorted(_executed_components_strict(
        spec["expectation"]["target_smiles"]))
    if executed != recorded:
        return {"status": "unsupported",
                "reason": "product_set_mismatch",
                "detail": {"record_id": record_id,
                           "executed_components": executed[:8],
                           "recorded_components": recorded[:8],
                           "note": ("执行产物组分与库记录净产物集合不一致"
                                    "(离去组分缺行/过滤缺失/对应错误;"
                                    "不冒充完整 record)")}}
    declared_copy_info: dict = {}
    if declared_copies is not None:
        # ---- W-D2(s5b-recorded-source-3):union gate 扩展(设计 §五
        # .3;**收窄式扩展**——多一道拷贝核对,不是放宽)。缺省路径
        # 不进入本分支(EAWAG/整串行为字节等价)。
        copies_flat = _flatten_product_entries(list(declared_copies))
        record_flat = _flatten_product_entries(
            list(record_products or []))
        copies_strict = _record_products_strict(copies_flat)
        if any(x is None for x in copies_strict):
            return {"status": "unsupported",
                    "reason": "copy_component_unparseable",
                    "detail": {"record_id": record_id,
                               "declared_copies": copies_flat[:8]}}
        copies_sorted = sorted(x for x in copies_strict if x)
        recorded_full = sorted(
            x for x in _record_products_strict(record_flat) if x)
        # NC-4:拷贝身份必须是记录产物组分(多重集包含;身份 ≠ 记录
        # ⇒ declared_copy_mismatch,防"拷贝串被换")
        copies_counter = Counter(copies_sorted)
        record_counter = Counter(recorded_full)
        if copies_counter - record_counter:
            return {"status": "unsupported",
                    "reason": "declared_copy_mismatch",
                    "detail": {"record_id": record_id,
                               "declared_copy_components":
                                   copies_sorted[:8],
                               "recorded_components": recorded_full[:8],
                               "note": ("声明拷贝组分身份与库记录产物"
                                        "组分不一致(拷贝只认 strict "
                                        "identity;cn 派生/篡改串拒,"
                                        "NC-11)")}}
        # ---- union gate:执行 ∪ 声明拷贝 == 记录全量产物(多重集) ----
        # 两侧键空间统一到 strict_identity_of(R32-CS3-2;执行侧现行
        # 裸 MolToSmiles 键仅留作一致性披露对照,不再作比较键)
        executed_unified = _executed_components_strict_unified(
            spec["expectation"]["target_smiles"])
        union_sorted = sorted(
            x for x in executed_unified + copies_sorted
            if x is not None)
        if union_sorted != recorded_full:
            return {"status": "unsupported",
                    "reason": "product_set_mismatch",
                    "detail": {"record_id": record_id,
                               "executed_union_declared_components":
                                   union_sorted[:8],
                               "recorded_components": recorded_full[:8],
                               "note": ("执行组分 ∪ 声明拷贝组分 与库记录"
                                        "全量净产物集合不一致(拷贝缺失/"
                                        "对应错误;不冒充完整 record;"
                                        "W-D2 union gate)")}}
        # 键空间一致性披露(裸键 vs strict 键;分歧不吞、如实计数)
        bare_keys = sorted(_executed_components_strict(
            spec["expectation"]["target_smiles"]))
        strict_keys = sorted(
            x for x in executed_unified if x is not None)
        divergent = [f"{b}!={s}" for b, s in zip(bare_keys, strict_keys)
                     if b != s] if len(bare_keys) == len(strict_keys) \
            else ["length_mismatch"]
        declared_copy_info = {
            "n_declared_copies": len(copies_flat),
            "declared_copy_strict_identities": copies_sorted[:8],
            "execution_status": "declared_not_executed",
            "union_gate": ("executed_components_multiset UNION "
                           "declared_copy_components_multiset == "
                           "recorded_products_multiset (strict "
                           "identity, same-source strict_identity_of)"),
            "key_space_consistency": {
                "n_components": len(strict_keys),
                "n_divergent": len(divergent),
                "divergent_examples": divergent[:4],
                "note": ("bare MolToSmiles vs strict_identity_of key "
                         "agreement on executed components (R32-CS3-2 "
                         "consistency disclosure; divergence is "
                         "disclosed, never silently swallowed)"),
            },
            "verified_product_set_scope": (
                "executed_union_declared_copies(非元素/电荷配平核验;"
                "配平轴恒 unknown,判据二;R32-CS1-2)"),
        }
    spec = dict(spec)
    spec.pop("coefficient", None)  # 库记录无配平系数 ⇒ unknown
    spec["compile"] = dict(spec.get("compile") or {})
    spec["compile"].update({
        "mapping_origin": "inferred",
        "record_products": list(products),
        "verified_product_set": True,
        "n_mappings": len(mappings),
        "n_equivalent_mappings": len(compiled_specs),
        # W-V2:有界键差诊断披露(选中的候选映射删键数;0=标准零键差
        # 对应;非机制证据)
        "n_bond_diff": int(chosen.get("n_bond_diff") or 0),
    })
    if declared_copy_info:
        spec["compile"]["declared_copies"] = declared_copy_info
        spec["compile"]["record_products_full"] = (
            list(record_products or []))
    chosen = dict(chosen)
    chosen["spec"] = spec
    return chosen


def _changed_maps(mapped_lhs: str, mapped_rhs: str) -> list[int]:
    """推断变换的变化原子 map 号(**供体 lhs 侧**:键差端点 + 离去)。

    新增原子(rhs 独有 map)不在此列 —— 编译器自动把新增原子并入中心
    与对齐(W1);此处给 lhs 侧中心即可。"""
    from .s5b_compiler import extract_mapped_transform

    try:
        transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    except S5bCompileError:
        return []
    center: set[int] = set()
    for ch in transform["bond_changes"]:
        center.add(int(ch["map1"]))
        center.add(int(ch["map2"]))
    center |= set(transform["removed_maps"])
    # 只取 lhs(供体)侧 map;新增原子(rhs 独有)由编译器自动并入中心
    lhs_maps = set(transform["lhs"].maps)
    return sorted(center & lhs_maps)
