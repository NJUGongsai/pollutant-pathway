# Codex 同范围复核请求 — 证据卡 P1 修复轮（2026-10-15）

> 对象：上一轮评审 `docs/EVIDENCE_CARD_CODEX_REVIEW_2026-10-15.md` 列出的
> 2×P1+1×P2 的修复（工作树未提交增量，其上）。**同范围复核**：只核两 P1
> 修复与 P2 纠正是否闭合+是否引入新问题；不扩评审面（接线/边界/兼容上轮
> 已过，除非发现修复越界）。
> 题域标签：**298=RHEA 通用酶学/已见题**；修复全部合成输入验证。

## 一、修复声明（供核对）

| 项 | 修法（文件:行号） | 声明效果 |
|---|---|---|
| P1-1 未知系数 null | `candidate_evidence.py:150-158`：渲染层 `None→"unknown"`，`coefficient_status` 原语义保留、已知系数原 str 化口径不变；底层对象零改动 | 合法装配（recorded 删键/默认副产物）最终载荷 `coefficient` 非 null；已知系数维持原值 |
| P1-2 电荷非有限 | `candidate_evidence.py:328-347`：逐电荷 `math.isfinite`，任一非有限 ⇒ 整个电荷描述符降 `"unknown"`（未用 allow_nan=False 全面拒绝）；分子式/元素/官能团照常 | Se 类合法底物载荷零 NaN/Infinity、电荷=unknown、其它事实保留；CCO 有限电荷正控 |
| P2 文档纠正 | 设计书 §三/§四+页头、交付书 §六、模块 docstring：放弃理由改「部分通道事实可得（spec.corpus 块/donor_match_kind 在），完整恢复未证明，v1 不纳入；禁透传 corpus 块（含 EC）」 | 措辞与事实对齐，无字段透传 |
| 版本承载 | schema 升 `candidate-evidence-1→candidate-evidence-2`（编码语义变化由版本披露；测试断言+docstring+T11 注释同步）；descr 版本不升（计算口径零变化）；提示词零改动 ⇒ PROPOSALS_PROMPT_VERSION 不变 | 编码合同变化有版本承载 |

## 二、修复轮新增测试（4 件，全绿；证据卡 18+CI 18=36 复跑过）

- `test_full_chain_recorded_compiled_unknown_coefficient_payload`：真实
  `compile_recorded_reaction` CCO→CC=O → 公开 `start_ppv1_run(scripted=True)`
  零 monkeypatch → 最终用户载荷 coefficient=="unknown"、零 null/NaN/Infinity；
- `test_full_chain_default_coproduct_unknown_coefficient_payload`：主系数
  "1" 不变+默认副产物 unknown；
- `test_substrate_evidence_nonfinite_gasteiger_degrades_unknown`：
  C[SeH]/C[Se]C 电荷 unknown、CH4Se/C2H6Se+Se 元素保留；
- `test_full_chain_gasteiger_nonfinite_negative_and_finite_positive`：
  Se 全链负控+CCO 有限正控。

## 三、基线数字（全链条）

| 项 | 值 |
|---|---|
| 修复前（实施轮，主会话独立复跑过） | 2154/0/16（=2139+14+1） |
| 修复后（实施方） | **2158/0/16**（=2154+4 新测，零翻转） |
| 主会话独立复跑 | **2158 passed / 16 deselected（333.3s）——与实施方数字逐字相同** |
| 主会话独立 P1 探针 | 系数渲染 `['unknown','1']`（无 null、known 保留）；Se 电荷=unknown、payload 零 NaN/Infinity、CH4Se+Se 保留；CCO 数值电荷 dict；Se 双跑确定性 True |

## 四、请复核的问题

1. **P1-1/P1-2 闭合**：按你上轮 §五收口三条判据复核——未知系数不得变
   数值、已知系数维持原值；不可用电荷不残留 NaN/Infinity 且其它事实仍
   输出。修复是否只在证据渲染层（底层 Participant/production/
   recorded_source 零改动）？
2. **新测试对漏口的覆盖**：4 件新测是否覆盖你指出的两漏口（真实编译
   形状/默认副产物/Se 非有限/有限正控）？仍有绕过面吗？
3. **修复无越界**：接线/池/判分/run_inputs 是否仍零 diff（git 范围=
   上轮 5 文件之内增量）？
4. **版本裁定**：schema 升 2 不升 descr、提示词零改动的版本决定是否
   合理？
5. **P2 文档**：措辞纠正是否到位、有无顺带透传 corpus 块？

## 五、回复格式

逐条 1–5：闭合/未闭合+证据（文件:行号或探针结果）；发现新 P1/P0 明示
级别。最后总体读法 ≤3 行（收口或仍不通过+理由）。不追加科学性能门、
不要求跑真实模型（沿你上轮收口口径）。
