# 任务书 — 证据卡 P1 修复轮（Codex 复审回修，2026-10-15）

> 派单：主会话（评审-回修循环）。执行者：实施子代理（单人串行）。
> 依据：Codex 复审 `docs/EVIDENCE_CARD_CODEX_REVIEW_2026-10-15.md`
> （暂不通过：2×P1+1×P2 文档纠正；接线/边界/兼容已过——**只修列出的项，
> 不得顺手扩范围**）。
> 题域标签：**298=RHEA 通用酶学/已见题**。基线：当前工作树（证据卡实施
> 未提交改动之上）全量 not-slow **2154/0/16**。

## 一、修复项（最小面，评审已给到文件:行号）

### P1-1 未知系数渲染 `null` 违约

- 位置：`src/pathway_v43/pollutant/candidate_evidence.py:145`（系数缺失
  返回 `None` → 载荷 `coefficient: null`）。
- 根因链（评审已证）：`recorded_source.py:2275` 合法删除库记录无配平
  系数的 spec `coefficient`；`production.py:503/518-521` 合法装配未知系数
  （None/unknown）——**底层对象不是错，不许改底层**。
- 修法：**只在证据渲染层**把系数 `None` 转字面 `"unknown"`（评审写
  UNKNOWN），保留底层对象与 `coefficient_status` 原语义；已知系数维持
  原值不动。
- 新负控测试：真实 recorded 编译形状（评审用 `compile_recorded_reaction`
  编译 `CCO→CC=O` 复现）走公开 `start_ppv1_run(scripted=True)` +
  `ScriptedRealModelAdapter`，断言最终用户载荷参与物 `coefficient` 非
  `null` 而是 unknown 字面；默认副产物未知系数的负控同链断言。

### P1-2 Gasteiger 电荷非有限值（NaN）违约

- 位置：`candidate_evidence.py:317`（取电荷后直接 round/排序/极值）；
  `:337` 的异常降级捕不到「不抛异常但返回 NaN」。
- 复现（评审已证）：`C[SeH]`/`C[Se]C` 合法解析渲染，公开链零 monkeypatch，
  载荷电荷 min/max/mean/逐原子值均为 NaN。
- 修法：**逐电荷 `math.isfinite` 检查**；任一非有限 ⇒ **整个电荷描述符
  降为 unknown**（保留分子式/元素计数/官能团等其它事实）；不得全面拒绝
  含特殊元素的合法底物（同链 `CCO` 正控必须保留）；不得只设
  `allow_nan=False` 让整题失败（违反降级合同）。
- 新测试：Se 非有限负控（断言载荷无 NaN/Infinity、电荷字段=unknown、
  分子式/元素组成仍输出）+ 有限值正控（CCO 电荷数值在）。

### P2 文档纠正（非阻塞，一并做）

- 设计书 `docs/EVIDENCE_CARD_DESIGN_NOTE_2026-10-15.md` §四与交付书
  `EVIDENCE_CARD_IMPL_DELIVERY_2026-10-15.md`：放弃理由改为
  **「部分通道事实可得（corpus 路径写 spec.corpus 块、donor_match_kind
  whole/component 在），完整恢复尚未证明，v1 范围不纳入」**——原「通道
  事实完全不入 spec」说得过满。
- **禁止**为补字段透传整个 corpus 块（内含 EC，禁展示）。

## 二、红线

1. 只修证据渲染层与文档；**底层对象（Participant/production/recorded_source）
   零改动**；接线/池/判分/run_inputs 零改动。
2. 复核判据（评审 §五收口原话）：未知系数不得变数值、已知系数维持原值；
   不可用电荷不残留 NaN/Infinity、其它底物事实仍输出。**不追加科学性能门，
   不要求跑真实模型**。
3. 版本面：`candidate-evidence-1` schema 若语义变（null→unknown 编码变化）
  ⇒ 升版为 `candidate-evidence-2` 并同步测试断言与受控词表（按既有版本
  承载纪律；不升版则论证编码修复不属语义变化——二选一，交付书写明理由）。
4. 零金标零题面零模型零网络；不 commit 不 push；交付书增量节登记
   （不改评审报告原文）。
5. 全量 not-slow 回归：基线 2154/0/16 零翻转（新增测试另计）。

## 三、分步

1. 读评审报告全文（P1 证据与修法已在 §阻塞项；执行证据目录
   `docs/review_evidence/evidence_card_codex_2026-10-15/` 可参考其探针
   脚本复现手法）。
2. 实施两 P1 修复+P2 文档纠正+新负控/正控测试。
3. 跑新测试+受影响文件；跑全量 not-slow 回归。
4. 交付书追加「P1 修复轮」节：修了什么/行号/测试数字/复核判据自查
   （评审 §五收口三条逐条）。
5. 回传：①两 P1 修复点（文件:行号）；②新增测试清单与结果；③全量数字；
   ④复核判据自查三条；⑤版本决定（升版或论证）；⑥P2 文档纠正落点。

## 四、排障表

| 症状 | 处置 |
|---|---|
| Se 负控在 CI 环境行为不同 | 以本机 conda depending43 实测为准，如实记录 |
| 复现不了 P1 现象 | 停下报告（评审探针脚本在证据目录，照书复现） |
| 全量出现非新增测试红 | 定位；版本字面量/CI 合法更新按先例登记，行为红=修 |
