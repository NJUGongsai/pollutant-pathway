# 候选证据卡 P1 修复轮同范围复核（2026-10-15）

**结论：有限范围通过；上轮两项 P1 已闭合，P2 文档纠正到位，未发现修复引入的新 P0/P1。** 本轮仅检查上轮已定的缺失值编码、不可用电荷降级及修复越界；不追加科学性能门，不授权发车或判据冻结。

审核对象为 HEAD `461844eef6c3d0c464b12db0d89fc34e9971e825` 上的未提交工作树。比较基线采用[上轮安全源码快照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_2026-10-15/execution_probe/inputs)，并与当前源码及本轮合成执行互证；没有把实施方或请求方的全量测试声明当成本次独立复跑。

## 1. 两项 P1 是否闭合：闭合

**P1-1 已关闭。** [candidate_evidence.py:147](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:147) 取参与物序列化副本的 coefficient，第 155–157 行仅将 None 分支改为字面 `unknown`；已知值仍按原 `str()` 口径输出，coefficient_status 不变。没有写回 Participant、prepared 或 spec。底层未知系数仍合法使用 None/unknown，未改成虚构数值；[production.py:503](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/production.py:503) 的缺省装配和默认副产物规则保持原样。实际公开链得到真实编译两系数 `unknown/unknown`；默认副产物为 unknown，已知主系数仍为字符串 `1`、状态 known。

**P1-2 已关闭。** [candidate_evidence.py:328](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:328) 计算电荷后逐个调用 `math.isfinite`，在四舍五入和排序前拦截 NaN、正负 Infinity；任一不可用，第 346–347 行将整个电荷描述符降为 unknown。原异常分支同样只降级该字段。官能团已于第 323 行保存，元素和分子式仍在第 362–376 行继续计算，没有全面拒绝合法底物。

上轮同一公共链脚本在当前源码原样退出 0：Se 的严格 JSON 检查由失败变通过、原载荷 NaN 由有变无；CH4Se、Se 元素及表示档案保留。CCO 仍返回有限电荷 dict（min=-0.3967、mean=-0.1328、max=0.0402）。[前后结果对照](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/execution/old_current_probe_comparison.json) 与[静态证据](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/static/findings.md) 相互支持。

## 2. 四项新测试覆盖是否充分：本轮漏口已覆盖

[新增测试:481](/Volumes/CC/Enzyme_Agent/dependingv43/tests/test_ppv1_s5b_candidate_evidence.py:481) 真调用 compile_recorded_reaction 生成缺 coefficient 的合法 spec，再走公开 `start_ppv1_run(scripted=True)`，核最终载荷；第 517 行覆盖默认副产物与已知系数正控；第 549 行覆盖 C[SeH]/C[Se]C 的非有限降级及其它事实；第 568 行覆盖 Se 与 CCO 的同链负控/正控。四项原样执行 **4 passed、零 monkeypatch**，均运行到目标断言。

首提和格式反馈分别经 [runflow.py:1162](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/runflow.py:1162)、第 1213 行调用同一 `_call_real_fetch`，第 1296、1307 行共用修复函数。未发现修复另建绕过过滤的输出路径。测试不穷举所有分子，但对应上轮两个具体漏口与合法能力均已闭合，不以缺少无关单例扩阻塞。

本轮两测试文件在纠正临时目录后原样 **34 passed / 2 failed**：两个旧集成测试默认 scripted=False，在隔离副本缺 assets 的身份核验处先失败，内部断言未执行，不记通过。仅受控替换资产身份函数后 **36 passed**；不能称原样 36 全绿，也不证明真实资产核验。首次误将 TMPDIR 放在源码副本内多触发一道输出根门禁，已纠正并完整保留记录；属于执行环境问题，非产品反例。详见[执行摘要](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/execution/execution_summary.md)。

## 3. 修复是否越界：未越界

与上轮五文件安全快照相比，real_model.py、runflow.py 逐字节相同；本轮执行代码变化仅在 candidate_evidence.py 的两项修复、math 导入与 schema 常量。测试增加四项和版本断言，词表 CI 仅改版本注释。不能把“本修复增量接线零改动”误写成“初版接线相对 HEAD 零 diff”。

production.py、recorded_source.py、s5b_builder.py、s5b_scoring.py、model_protocol.py 与 HEAD 相同；候选池、检索、判分和 run_inputs 没有本轮新改动。证据是[保护面哈希核对](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/protected_scope_check.json) 与[范围复核](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/scope/findings.md)。算法未改不表示模型选择或真实成绩必然相同。

## 4. 版本决定是否合理：合理

[candidate_evidence.py:45](/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/candidate_evidence.py:45) 将 schema 升为 `candidate-evidence-2`，足以披露 null/NaN 改 unknown 的编码合同变化；最终 builder 在 real_model.py 第 242–245 行从该常量输出版本。

descr-1 保持合理：SMARTS、原子编号、有限输入的计算公式、精度和极值窗口均未改，本次新增不可用值降级。real_model.py 与上轮逐字节相同，提示词内容与哈希来源未变，PROPOSALS_PROMPT_VERSION 不变合理。源码仍由 storage/run_identity.py 第 76–100 行整体纳入身份，修复代码变化不会静默复用旧批。

## 5. P2 文档是否纠正、是否透传 corpus：闭合，无新增透传

[设计书:4](/Volumes/CC/Enzyme_Agent/dependingv43/docs/EVIDENCE_CARD_DESIGN_NOTE_2026-10-15.md:4)、第 60–74 行，[交付书:119](/Volumes/CC/Enzyme_Agent/dependingv43/docs/EVIDENCE_CARD_IMPL_DELIVERY_2026-10-15.md:119)，以及模块第 20–23、164–168 行，均已改为“部分通道事实可得，完整恢复尚未证明，v1 范围不纳入”。设计第 74 行、交付第 125 行明确禁止直接透传含 EC 的 corpus 块。

candidate_evidence.py 第 170–187 行来源白名单未改，执行增量没有读取或复制 corpus，装配与 builder 亦与上轮相同；没有为纠正文案顺带加入禁用事实。

执行使用 Python 3.11.16、RDKit 2026.03.6、pytest 9.1.1，在新 tmp 复制含 vendor 的源码后运行，禁用 pyc 与 pytest 缓存；结束时原仓相关源码、测试哈希前后一致，pyc/cache 均为 0。[快照身份](/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/evidence_card_codex_rereview_2026-10-15/review_snapshot.json) 与 execution 中命令、输出、postcheck 可复查。本次未重跑全量 2158，未读取金标、真实题面或封存逐题 run，未联网或调用模型，未改任何已有文件，未 commit/push。

## 总体读法（≤3 行）

同范围复核通过：两项 P1 关闭，P2 纠正完成，未发现修复引入的新 P0/P1。
结论限于编码、局部降级与修复边界；不认证 298（RHEA 通用酶学/已见题）的 hit@1 收益，不构成发车或冻结裁定。
