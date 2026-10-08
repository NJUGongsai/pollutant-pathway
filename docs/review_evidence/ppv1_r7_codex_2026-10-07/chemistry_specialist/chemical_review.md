# R7 独立化学专项复审

日期 2026-10-07；仓库只读输入 HEAD `858dd94c7c6c8fc387940242403d67b6b36b5313`，父 `6d9020130a481866ce2f3b79933907a33d8cfc9e`。范围固定 R6 §3 R6-01/02 及 mimo v7 C1–C6 的化学部分；不追加机制库、科学性能或电子/自由基轴。

执行位于 `/private/tmp/ppv1_r7_chem_858dd94_4roj2m9l`，完整 `src/`（含 vendor 与其 metadata）和单一 R7 化学 fixture 测试复制后执行。命令 `PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B chemical_boundary_probe.py`，stdout `chemical_boundary_output.jsonl`，stderr `chemical_boundary_stderr.txt`。输出 57 条顶层记录（含 metadata、factory/store 对照和失败早退，不等于漏洞数）。`assert_chemical_observed.py` 全部断言通过；其钉住 R7 实际观察含未修 raw 恢复缺口，不能作修后通过线。未运行全量套件或旧 12 探针，主审/其他线负责。没有金标、真实题面、封存 run、外部模型；SQLite 仅本隔离目录内新合成库。

## 1. 化学结论

R6-01 三个复杂共底物原例已关闭；R6-02 工厂/strict 并列未知与 donor 四原始入口原例已关闭，但同契约还有 **一项 P1 残余：恢复/直接对象进 audit 没有验证原始串与规范身份的一致性**。mimo C1 仅在规范字段加 r 的三个例子确实止于 retain，应认可其窄判断；不能把它说成所有状态恢复路径都不可达 R6。

## 2. [P1] raw 原始串恢复后可授 as_written/全部 verified/R6

公开最小链：

1. 用正常工厂建立 `CCO`、`CC=O`、`[H][H]`，真实 AtomTool 把乙醇 C–O single→double 执行并通过正常 donor checker，取得未改写 proof。
2. 仅复制 `CCO.to_dict()` 并改 `structure_smiles_raw = "CCO |r|"`；state_id、规范串 `CCO`、四轴 as_written、版本均保留。
3. `ChemicalState.from_dict(payload)` 接受；把恢复对象直传 `audit_hypothesis`，公共 `decide_admission` 返回 `expand`、`R6:all_verified_no_conflict`。parse、identity_fidelity、元素、电荷、中心及条件均 verified。

日志 `C1_raw_substrate_unknown_flag` 是最小反例。同根 `C1_raw_product_unknown_flag`、`C1_raw_uncovered_H2_unknown_flag` 也 expand。`C1_chiral_raw_unknown_flag` 在指定手性表示 `F[C@H](Cl)CCO` 的远端氧化中重复成立（不借 achiral 输入推定实验含义）。辅助 `C1_raw_uncovered_H2_different_molecule` 仅把 H2 状态 raw 改成 `CC=O`，恢复/审核仍 expand，说明原始身份一致性验证本身缺失；不将此另立新 P1。

**代码与同源判据：**

- `src/pathway_v43/pollutant/chemstate.py:618–631` 恢复只做版本及 fidelity 枚举校验。
- `src/pathway_v43/pollutant/audit.py:448–457` 直传 `states` 不经过 build/守卫；`raw_structures` 只补缺项。
- 同文件 `:493–519` parse 项检查规范字段为空与 CN-only，没有重推导原始串；`:537–559` identity_fidelity 只查调用方四轴枚举是否 as_written。
- 现有 store 已有适用的同源判据：`store.py:463–504` 规范身份/科学事实重推导；`:507–530` raw→`strict_identity_of`，并与规范身份比较。7 个本次不一致载荷经公开 `put_state` 全部首用拒绝且 counts 不变，故不是指控 store 可写这些假状态。

**对应原验收：**R6-02 的原始表示不能经未核恢复路径获得 as_written/verified/R6，及 AGENTS §返工教训 1/3/4 的恢复／审核入口与首消费完整性闭合；也是原规格 §5.1 原始串与解析图同时保留、S1/S2 信息保真。此次没有认证调用方数据是否真实或实验样品是否纯，仅验证对象自身已有字段可确定检查的一致性。

**最低修复：**把已有纯状态 payload 规则抽成 ChemicalState 恢复、audit 直接对象和 store writer 同源的校验：规范表示登记/重推导、raw 登记守卫、raw strict identity 与规范身份相符，以及既有身份/结构事实。canonical-only 守卫不够。不得将非法 raw 静默剥掉或重写成干净串再授 full；明确拒绝或保留未核身份 unknown、不 R6。恢复与直接对象均覆盖，避免只补 from_dict 后又被 dataclass 绕过。保留 CN-only/存档形已有降级及 fidelity 来源边界，不以全面拒绝代替校验，不额外认证实验真实性。

**合法正控：**`C1_restore_control_clean`、`C1_restore_control_same_graph_spelling`（raw `OCC`、canonical `CCO`）、`C1_restore_control_registered_metadata`（合法 atomProp 含空格按登记注记去除）全部 expand；`C1_chiral_clean_control` expand；`C1_CN_only_honest_unknown_control` 恢复成功，保真与结构为 unknown、retain，未变成 reject 或 expand。

## 3. C1 规范字段窄反例与 mimo 判断的采信范围

`C1_canonical_substrate_unknown_flag`、`C1_canonical_product_unknown_flag`、`C1_canonical_uncovered_H2_unknown_flag` 分别在 `smiles_isomeric` 里加 `|r|`，当前均 retain：底物精确绑定、产品集匹配或补全许可失配，center unknown；mimo 读码对此三例的判断成立。它们的 parse/fidelity 和元素/电荷仍 verified，是同一恢复首消费问题的局部表现；不夸大为这三个 canonical 例本身到 R6。

## 4. R6-01 与 C4/C5

`R6_01_CC=O`、`R6_01_C1CO1`、`R6_01_C=CO` 均有真实新增原子证据，元素/电荷数值闭合，但许可身份未登记，center unknown、`partial_unchecked_transformation`、retain。机器 detail 明示 `completion_license`、scope 与未登记身份；原复杂图只靠配平升 full 的例已关闭。H2/[H] 精确登记两键的 composition-only 本轮许可可保持；本审不新增电子/自由基/均裂机理要求，不接受 mimo 关于未来扩登记的同分异构唯一性建议作为本轮必修门。

C4：v7 请求没有逐字“full 两根据”一句，src 注释也没有这句，但源码 `audit.py:951–1018` 实際分开无未覆盖参与物与有未覆盖参与物：后一分支既精确双侧数值又要求许可身份集合。请求判据三现有条目亦写了无未覆盖→full、许可内正控 full 与未登记→partial。**缺一句整理说明属 P2，不是缺实现或新 P1。**建议下一次 docs 文本明确两根据和互不替代，不强制改已封存 R6 文档。

C5：scope 在 `ChemicalAudit.to_dict()` 的中心 detail 内机器保留（`audit.py:992–997`），`decide_admission` tuple 本身仅返回处置与 R6 原因，不复制 scope。本轮 R6 原验收要求机器披露已满足，未找到 scope 缺少顶层别名造成错误结构声明的实际消费链；“顶层披露/渲染同屏”和 `license_applied` 是后续展示/API 的 P2，不能凭其缺失阻塞 S3。别把 full 读成 H2 活化机理、历史真实执行或所有氢键命运已经核实。

## 5. C3：放行侧往返执行核查

锁定本机 RDKit 版本记录在 metadata。保留类合成 10 形状：正常 SRU，4 个 SRU 字段含空格/逗号/转义/双组，以及增强组/自由基项间空格与逗号 5 形状。

- `C3_retained_0` 与 `5–9` 六个放行形状经 RDKit MolToCXSmiles→MolFromSmiles→MolToCXSmiles 规范写出稳定；严格状态往返同 id，且与裸串不同 id。增强组与自由基事实未静默消失。自由基原子索引因 canonical 写出重排可交换，不能把 raw atom-indexed 数组不同误算事实丢失；日志同时保存原始/重解析快照、规范 writer 稳定和 radical 多集合控制。
- `C3_retained_1–4` 四个带空格/逗号 SRU 字段，RDKit 本身能往返且 writer 稳定，输入守卫放行后旧输出守卫按空格/逗号误拒（`chemstate.py:484–497`），最终未构造状态。**保守过拒 P2，未见静默丢事实/R6，不能另升级 P1。**R7 声称修复的含空格三正控是移除类，并未宣称所有 SRU 内容支持；报告应准确登记此剩余限制。
- 三个移除类 atomProp 含空格、DAT 含逗号+空格、标签含空格，实际 RDKit writer 往返稳定；身份按规则去除元数据，与裸结构相同 id，身份再构建同 id。不能只凭原测试“没抛异常”称保留类全保真，现有专项补足上述允许形状的执行证据。

## 6. C2/C6 与 R7 回归有效性

C2 非 admission 消费入口应准确划界：pool preview 是 diagnostic_only/pool_unchanged；冻结 AtomTool 与外围服务的内部解析不能当额外独立 verified，供体四字段随后统一守卫。缺范围说明是 P2；不改冻结执行器。

C6 `C6_execution_success_current/mapped/plain/target` 四例均 `AuditContractError(kind=raw_input_cx_class_unregistered)`，没有返回 diagnostic/evidence/disposition。本脚本捕获异常仅记录观察；不把异常当 retain/verified 行。`C6_execution_failure_*` 四例 `ok=False` 早退，center/strict/legacy 三轴 None、`center_evidence={}`，有 `execution_failed` 原因，不消费 tainted 原始四字段，安全。未执行生产级未知异常吞噬的假设，不凭这种猜测立 P1；建议文本补清此早退与拒绝语义。

R7 新化学回归真正检查复杂共底物 partial、未知并列 build/strict 拒绝、donor 四入口拒绝、proof 复算拒绝、正常氢当量；不是只检查退出状态。不过 `test_r6_02a_registered_content_passes` 仅验证构造/strict 不抛异常，不核 RDKit 原始保留事实与写出往返；本文 C3 是独立补证。R7 化学回归没有覆盖 `ChemicalState.from_dict`/直接 `states` raw 一致性，故 508 绿不能关闭上述残余。

## 7. 附件与复跑

复制 `chemical_boundary_probe.py`、`assert_chemical_observed.py`、`tests/test_ppv1_r7_chem.py` 到新的空 tmp，完整源码含 vendor 置于同级 src，再在 tmp 运行上述 Python 命令（随后运行 assert 脚本）。脚本会在它自己的目录写合成 SQLite 与日志输入由 shell 重定向，**不要在永久证据原地执行**。57 JSONL 条记录含完整状态 payload、hypothesis、真实 proof、audit、admission、RDKit 快照或结构化错误及 store 写前后 counts。stderr 中若有 RDKit 关于独立氢的通常警告应留原文，不作失败或 skip。

SHA-256 清单 `chemical_manifest.json` 是本专项脚本/输入 fixture/输出/报告的快照；metadata 的 expected_source_HEAD 是来源锁定说明，实际 HEAD 与附件源码完整性以主审 manifest 为准。此报告中的临时绝对路径是原始执行来源，主审汇总永久附件提供可复跑入口。
