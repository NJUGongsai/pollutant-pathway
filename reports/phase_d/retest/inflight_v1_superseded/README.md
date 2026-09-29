# inflight v1 派生表（已作废，仅留作 F1 证据链）

本目录 4 个文件是 F1 修复前的旧版并发逐请求派生表：重复 task 的两行
attempt 均被标成 `2`（`scripts/ec298_pd_retest_inflight.py` 旧版以
`(run_id, task_id)` 字典覆盖所致；C0 `RXNG_16560019…`、D3 `RXNG_7701b699…`
的 a1 行应为 `1`）。

现行版本在原路径（`reports/phase_d/retest/{C0,D3}_inflight_events.tsv` +
`{C0,D3}_inflight_summary.json`，schema `ec298-pd-retest-inflight-2`）：
逐文件 `payload.attempt` + 文件名 `aN` + request_id 三方交叉核对，
与旧版逐格比对仅各改 1 格（a1 行 attempt 2→1），峰值仍 33/32。
详见复测报告 §12 v3 修订记录与综合 review F1。
