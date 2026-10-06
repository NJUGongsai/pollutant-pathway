# PPV1 R3 回修:红验证与 G01 证据

- 日期:2026-10-06;对应交付书 `docs/POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R3_2026-10-06.md`。
- 回修基线 0002f71(= R2 复审 HEAD);交付 HEAD 见交付书 §1。

| 文件 | 内容 |
|---|---|
| red_behavior_probe.py | 行为级红验证:对**基线 0002f71** 断言 v3 预期,8/8 失败(v2 缺陷仍在)。需先 `git archive 0002f71 | tar -x -C <dir>` 并把脚本内 sys.path 指向该目录 src |
| g01_full.log | G01 legacy 全量回归(not slow):837 passed, 16 deselected, 0 failed |

探针复跑(修复后行为翻转)用 R2 复审附件原样脚本:
`docs/review_evidence/ppv1_r2_2026-10-06/*.py`(chemistry/admission exit 0 且反例翻转;conditions/storage 在首个旧反例段 fail-closed = 修复后行为)。全部反例的**正本回归**在仓库测试
`tests/test_ppv1_r2_{chem,conditions,storage}.py`(226 项),不依赖 /tmp。
