# Phase C 三审补强终审（2026-09-28）

复核对象：CCLA-16 的 Phase C 二轮修复及金标行重复补强。复核快照 `HEAD=5c8f284423716137af24053f067ffdc7489066f2`，实现仍有未提交改动；本结论绑定本轮实测文件内容，不把工作树状态归于 HEAD。审计脚本 SHA256 为 `52c2443c212a7ae78a7c501033b5876dc6e74c1b9c4515a02cd62990c33d8b2b`，金标守卫夹具 SHA256 为 `536a431ee6b5316abe7b3bcb6f0d191c329e50893cfb5c27d0a9129c93557eb9`。

## 逐项验收

| 门槛 | 结果 | 独立证据 |
|---|---|---|
| P1 候选层仅合格 recorded | 【属实】 | rule/analog 原始卡端到端反例均在本轮 74 项定向回归内通过；`prediction.py` 候选集合限合格 recorded |
| P1 验证层拒绝非 recorded | 【属实】 | `nodes.py` 的 `rank_selected_non_recorded` 守卫与对应工作流夹具通过 |
| P1 裁决层零占位 | 【属实】 | rule/analog 裁决层反例通过；原始卡不可报告，合格 recorded 不连坐 |
| 金标覆盖 fail-closed | 【属实】 | 守卫夹具 5/5；同 qid 两行金标的独立端到端反例返回码 2、stderr 为 `FAIL: 金标行重复…`、无 `summary.json`；空金标、缺题、任务题号重复夹具也通过 |
| 编辑协议严格化 | 【属实】 | 未声明字段与旧操作别名拒绝夹具在定向回归内通过 |
| 对齐枚举上限 fail-closed | 【属实】 | 2000 上限与触顶 ambiguous/unavailable 夹具在定向回归内通过 |
| 定向回归 | 【属实】 | 五个相关测试文件 `74 passed in 10.08s`，退出码 0 |
| 全仓回归 | 【属实】 | `OMP_NUM_THREADS=1 PYTHONPATH=src:tests /Users/cc/miniconda3/envs/depending43/bin/python -m pytest tests/ -q`：`388 passed in 484.45s`，退出码 0 |
| 独立审计 | 【属实】 | 新目录重跑退出码 0；金标 298 行 / 298 唯一、任务覆盖 66/66；拒绝目标文本匹配金标 8/23、旧接纳 0/15、再分类 1/22、路由 23/43 |
| 审计 SHA 对拍 | 【属实】 | 独立目录的四个 TSV 和新 `summary.json` 与 `reports/ec298/phase_c/` 五项逐字节一致；SHA 见证据包 |

## 上轮阻断与边界

上轮独立反例证明金标文件自身的重复 qid 会被字典覆盖，故当时的 `APPROVED` 不成立。本轮 `_gold_index` 检出规范化后的重复金标 qid，主流程在写审计产物前以退出码 2 拒绝；新增夹具覆盖该反例。真实封存金标 SHA256 仍为 `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c`，四个 TSV 的哈希不变；新增汇总字段使 `summary.json` 哈希更新为 `96ee62a60e926e4f31bb5c006b3ae295e9491649f4b16f1ce97da1feeca529e0`。

本次审计是已见 298 题的离线事后修复检查，不是新版预测成绩或 dev 三臂验证。复核未修改实现、资产、封存 run 或金标，也未提交。详细命令、输出和哈希见 [`PHASE_C_REPAIR_EVIDENCE.md`](PHASE_C_REPAIR_EVIDENCE.md)。

## Verdict

✅ **APPROVED**（限本轮 Phase C 修复门禁及离线审计验收）
