"""pollutant_pathway_v1 — 污染物路径探索新 profile 的领域契约与固定诊断。

本包是**显式启用**的新模式(实施书 §3.1):legacy_v43 的冻结行为、门禁、
预算与评测口径不经过本包任何代码;legacy 路径不 import 本包(storage.
run_identity 仅在 profile=pollutant_pathway_v1 时延迟取 profile 块)。

S0–S2 交付范围(实施书 §11,首阶段):
- S0 profile 注册/版本清单/新旧身份分开(本包 profile.py);
- S1 ChemicalState / ReactionHypothesis / 参与物 / 事件-报告-展开分离
  (chemstate.py / hypothesis.py / events.py / store.py / legacy_reader.py);
- S2 PathContext / 底物档案 / 来源细分 / 依赖 / 条件评估 / ChemicalAudit
  与 admission_policy / 候选池审计(path_context.py / provenance.py /
  substrate_profile.py / audit.py / pool_audit.py)。

S3a 批次交付(任务书 §2.3):pollutant/search.py 的**持久搜索底座**
(搜索/任务/attempt/request 身份、实际计数预算、认领事务、四崩溃恢复
协议、停止原因);用公开底座接口与 scripted/fake driver 验证。S3b
(队列化学集成/两类 deferred 调度、条件依赖/场景转换、新模型假设协议
与格式反馈、固定工具中心证据生产链、PPV1 独立 runner 分流)**未交付**;
执行流入口 workflow.runner.start_run 对本 profile 仍显式 fail-closed
(不进图、不建 run 目录),直到 S3b 集成交付后解除。S4/S5 不在本批。
"""
