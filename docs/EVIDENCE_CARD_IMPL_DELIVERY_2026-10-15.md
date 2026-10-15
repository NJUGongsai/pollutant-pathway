# 交付书 — 候选证据卡实施（Plan v1 P0 落地，2026-10-15）

> 任务书 `docs/TASK_EVIDENCE_CARD_IMPL_2026-10-15.md`；设计书
> `docs/EVIDENCE_CARD_DESIGN_NOTE_2026-10-15.md`（字段清单/入口枚举/
> 矛盾停点全量引彼处，本交付书不重复）。题域标签：**298**（RHEA 通用
> 酶学/已见题；实施+验证，不含发车）。HEAD `461844e` 工作树交付，
> **未 commit 未 push**（提交与否 CC 拍板）。

## 一、改动面（git diff 实测）

| 文件 | 改动 | 行数 |
|---|---|---|
| `src/pathway_v43/pollutant/candidate_evidence.py` | **新增**：candidate_evidence_payload + substrate_evidence_payload 纯函数 | 356 |
| `src/pathway_v43/pollutant/real_model.py` | 载荷渲染（evidence/substrate_evidence/schema_version 三键，未接线零变化）+提示词证据规则段 | +39/-4 |
| `src/pathway_v43/pollutant/runflow.py` | `_call_real_fetch`/`_model_proposals` 证据接线 + substrate_profile 穿参（decide 与格式反馈轮同入口） | +38/-8 |
| `tests/test_ppv1_s5b_candidate_evidence.py` | **新增**：正/负/不变量 14 测 | 463 |
| `tests/test_controlled_vocab_ci.py` | T1 基线哈希钉新值+升版断言（no-cap 先例）；T11 登记 candidate_evidence.py unknown 字面量 | +38/-18 |

判分侧（s5b_scoring.py 等）/池构建/检索/排序文件 **零 diff**；
PROPOSALS_PROMPT_VERSION `e28b5342…(8da11cb7 基线)→13698065db70…`
（4360→5380 字节）= 新批身份，resume 拒旧批为预期行为。

## 二、测试数字（全绿）

- 本轮新增：候选证据卡 14 测（正控 7：字段值/确定性双跑/提示词哈希
  升版断言/反馈轮一致性/底物档案/profile 直读；负控 2：缺失→字面
  unknown 零空串零 None、EC 编号/编造条件/记录状态/指派位点禁词扫描；
  不变量 5：spec 只读、未接线载荷逐字节向后兼容、run_inputs 零证据键、
  端到端池条目数与顺序不变、载荷键面恰五键）；
- CI 词表：18 测全绿（T1 新基线钉值+显式升版断言、T2-T8 检测器对
  新提示词全过、T11 登记面含新文件）;
- **全量 not-slow：2154 passed / 0 failed / 16 deselected**（333s；
  基线 2139+14 证据卡+1 CI 升版断言=2154，账目闭合零翻转）。

## 三、探针数字（reports/ppv1_s5b/evidence_card_probe_2026-10-15/
probe_report.{json,md}；gitignored；零模型零网络）

- 样本：20 题 = 4 个真实同底物歧义组 8 题（p0_ambiguity_2026-10-15
  按 substrate_sha256 连接）+ 非空池 6 + 空池 6，全部来自本地真实
  冻结批 s5b_298_local run_inputs；池条目 12 条（prepared 装配全成）；
- **确定性：20 题双跑载荷字节全等 = True；证据 dict 双跑全等 = True**；
- 覆盖率（真实批 spec，旧池形状）：编辑摘要/参与物/来源/对齐状态/
  供体映射数/参与物与步进范围 = 100%；compile 派生五字段（mapping_
  origin/n_alignments/truncated/立体消解）= 0%（该批无 compile 块，
  如实 unknown）；
- 覆盖率（现行形状合成 supplement）：compile 派生字段 83.3%
  （无 compile 块合成条目如实 0）、立体消解 16.7%（仅声明者）、
  requirements 0%（现行池供给不产 requirements，字段已接线待供给面
  携带）；
- 底物级覆盖率（20 题）：官能团/参考电荷/元素组成/分子式/表示保真/
  条件键 = 全部 100%（条件键为 unknown 占位值亦计入渲染成功）。

## 四、已知限制与预期管理

1. **32 题选错面上限**：证据卡只改信息表达，不动池/判分；选错面
   32 题（模型第一名已是首事件但不命中）是收益上限面，转化率未证；
2. **歧义 108 题转化未证**：底物层歧义长在题面，证据卡供给对齐质量
   信号但不清除歧义本身；
3. **A/B 批另走预注册**：提示词哈希已变=新批身份；发车前 CC 拍板
   预注册（A/B 双臂脚本不在本任务范围）；
4. **真实条目形状限制**：chain13 synced 无 run_inputs/plan.pools，
   本地 s5b_298_local 为旧池形状（无 compile 块）⇒ 探针以真实旧形状
   +现行形状合成 supplement 双表如实计量（探针报告 limitations 节）；
5. requirements 字段：现行池供给不携带 ⇒ 100% unknown（字段按契约
   接线，供给面携带后自动生效）。

## 六、P1 修复轮（2026-10-15；Codex 复审回修，未 commit 未 push）

> 依据 `docs/EVIDENCE_CARD_CODEX_REVIEW_2026-10-15.md`（2×P1+1×P2）；
> 任务书 `docs/TASK_EVIDENCE_CARD_P1FIX_2026-10-15.md`。最小面：只修
> 证据渲染层与文档；底层对象（Participant/production/recorded_source）、
> 接线/池/判分/run_inputs 零改动。两 P1 现象修复前本机复现与评审一致
> （`[null, null]` 系数 / Se 电荷 NaN），修复后同探针翻绿。

### 修复点（文件:行号，修复后工作树实测）

| 项 | 位置 | 修法 |
|---|---|---|
| P1-1 | `src/pathway_v43/pollutant/candidate_evidence.py:155`（`_participants_evidence` 系数渲染；常量 :45） | 系数 `None`（recorded 库记录合法删键 / 默认副产物缺省装配）渲染层转**字面 `unknown`**；底层对象与 `coefficient_status` 原语义零改动；已知系数维持原值（原 str 化口径不变，正控 `"1"` 实测不变） |
| P1-2 | `src/pathway_v43/pollutant/candidate_evidence.py:330-346`（Gasteiger 块） | 逐电荷 `math.isfinite` 核验；任一非有限 ⇒ **整个电荷描述符降字面 unknown**（不再依赖只捕异常的降级）；分子式/元素组成/官能团照常输出；CCO 同链正控数值保留 |

### 版本决定：升版 `candidate-evidence-1` → `candidate-evidence-2`

按任务书 §二.3 二选一取**升版**。理由：修复前后同输入载荷编码变化
（未知系数 `null`→`"unknown"`、非有限电荷 `NaN`→`"unknown"`）属载荷
编码语义变化——schema 版本字段的用途即向载荷消费方披露编码合同，
编码变即应显式升版（模块 docstring 同步;T11 登记注释同步;测试断言
`tests/test_ppv1_s5b_candidate_evidence.py:218` 同步）。附注：底物
描述符表版本 `candidate-evidence-descr-1` **不升**——SMARTS 表/极值
窗口/有限值计算口径零变化，变化仅在不可用输出的编码，由 schema 版本
承载。提示词零改动 ⇒ PROPOSALS_PROMPT_VERSION 不变（批身份由代码
哈希承载变化）。

### 新增测试（4 测；`tests/test_ppv1_s5b_candidate_evidence.py:472-601`）

| 测试 | 面 | 断言 |
|---|---|---|
| `test_full_chain_recorded_compiled_unknown_coefficient_payload` | P1-1 全链负控 | 真实 `compile_recorded_reaction` 编译 CCO→CC=O（spec 合法无 coefficient 键）→ 公开 `start_ppv1_run(scripted=True)` 零 monkeypatch → 最终用户载荷参与物 `coefficient=="unknown"`（非 null）、status 原语义、载荷零 null/NaN/Infinity 字面 |
| `test_full_chain_default_coproduct_unknown_coefficient_payload` | P1-1 默认副产物负控 | 主系数已知（`"1"`/known 不变）+ 默认副产物 → 载荷副产物 `coefficient=="unknown"` |
| `test_substrate_evidence_nonfinite_gasteiger_degrades_unknown` | P1-2 单元负控 | `C[SeH]`/`C[Se]C` 电荷=unknown、零 NaN/Infinity、分子式（CH4Se/C2H6Se）与元素组成（含 Se）仍输出 |
| `test_full_chain_gasteiger_nonfinite_negative_and_finite_positive` | P1-2 全链负控+正控 | Se 最终用户载荷零 NaN/Infinity、电荷=unknown、事实保留；同链 CCO 有限参考电荷数值在（min<0<max） |

执行结果：`test_ppv1_s5b_candidate_evidence.py` 18 测 + `test_
controlled_vocab_ci.py` 18 测 = **36 passed**（本机 conda depending43，
PYTHONDONTWRITEBYTECODE=1）。修复前基线探针（`null, null` / NaN）与
修复后翻绿均实测记录。

### 复核判据自查（评审 §五收口三条逐条）

1. **未知系数不得变数值**：`unknown` 字面非数值;全链负控断言
   `coefficient=="unknown"` ✓（且载荷零 `null` 字面）。
2. **已知系数维持原值**：正控 spec coefficient=1 → 载荷 `"1"`/known
   逐位不变（默认副产物负控同测覆盖）✓。
3. **不可用电荷不残留 NaN/Infinity、其它底物事实仍输出**：Se 负控
   断言电荷=unknown + `json.dumps(allow_nan=False)` 通过 + 原文零
   NaN/Infinity 字面;分子式/元素组成（含 Se:1）/官能团表仍输出;
   CCO 正控电荷数值保留 ✓。

### P2 文档纠正落点（非阻塞，一并完成）

- 设计书 `docs/EVIDENCE_CARD_DESIGN_NOTE_2026-10-15.md`：§四改写为
  「部分事实可得但完整恢复未证明 ⇒ v1 范围不纳入」（corpus 路径写
  spec.corpus 块、`donor_match_kind` whole/component 在为可得事实;
  strict_exact/cn 层级完整恢复未证明）+ 页头结论行同步 + §三版本
  字面量同步 -2;**未**为补字段透传 corpus 块（内含 EC，禁展示），
  证据面 corpus 细分仍不做;
- 本交付书：本节即登记;模块 docstring 与 `_source_evidence` docstring
  的同源过满措辞同步纠正（`src/pathway_v43/pollutant/candidate_
  evidence.py:20-24,164-169`）;
- 评审报告原文零改动（本节为增量登记）。

### 全量回归

**2158 passed / 0 failed / 16 deselected（334.91s）**——基线 2154 + 本轮
新增 4 测 = 2158，账目闭合**零翻转**（本机 conda depending43，
PYTHONDONTWRITEBYTECODE=1，pytest `-m "not slow"`）。

## 五、红线对账

零金标零题面（证据只读 spec/prepared/RDKit/substrate_profile 在线值；
缺失=字面 unknown）；候选集冻结（池/检索/排序/去重/run_inputs 零
diff，唯一行为面=decide 载荷+提示词规则段）；描述符纪律（Gasteiger
字段名自带 _reference+提示词"not assigned reaction sites"声明+负控
断言）；单次 decide 纪律/判分侧零改动/硬拒绝表未动；版本承载
（哈希变化被测试断言+schema 版本字段+CI 词表登记）；零模型零网络、
不 push、PYTHONDONTWRITEBYTECODE=1、对外数字带 298 标签。
**与红线/预期面偏差：零。**
