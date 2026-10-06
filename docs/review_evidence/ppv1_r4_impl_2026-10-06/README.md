# PPV1 R4 回修:红验证与 G01 证据(实施侧)

- 日期:2026-10-06;对应交付书 `POLLUTANT_PATHWAY_S0_S2_REWORK_DELIVERY_R4_2026-10-06.md`。
- 回修基线 af14fb2(= R3 复审 HEAD);交付 HEAD 见交付书 §1。

| 文件 | 内容 |
|---|---|
| red4_behavior_probe.py | 化学线行为级红验证:对**基线 af14fb2** 断言 v4 预期,8/8 失败(v3 缺陷仍在)。运行需 `git archive af14fb2 | tar -x -C <dir>` 并把脚本内 sys.path 指向该目录 src |
| g01_full.log | G01 legacy 全量回归(not slow):923 passed, 16 deselected, 0 failed(611 legacy + 312 ppv1) |

探针复跑(修复后行为翻转)用 R3 复审附件原样脚本
`docs/review_evidence/ppv1_r3_codex_2026-10-06/*.py`(admission_binding/chemistry
反例翻转;conditions 在外来绑定反例处 fail-closed;storage 分段对照见存储线
交付内部报告)。全部反例的**正本回归**在仓库测试
`tests/test_ppv1_r4_{chem,conditions,storage}.py`+修订的 r2_*(312 项),
不依赖 /tmp。本目录不含金标/封存材料;合成夹具只检验程序口径。
