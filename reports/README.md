# reports/ —— 跑批证据（不进版本库）

这里放**运行证据快照**：每个 case 一次运行一个目录，内含
`console.log` / `result.json` / `evidence.json` / `verdict.json`。

**自 2026-09-21 起 `reports/**` 不再提交进 git**（历史里的 60 个文件已从跟踪移除）。
原因：这些是产物不是代码，按时间戳堆积（曾出现同一 case 的 `..._PASS` 与未 PASS 并存、
三个只差几分钟的 dryrun 目录），而且没有任何代码引用它们。

保留在仓内的只有：
- `chenyu_smoke/LAYER2_SMOKE_REPORT_2026-07-22.md`（一份**结论文档**，不是快照）

## 产物现在放哪

- 本地/陈宇 HPC：`$ENZYMECAGE_RUN_REPORTS_ROOT`（默认仍在仓库工作区的 `reports/`，仅本地）；
- 需要长期归档的：按 `assets_manifest.json` 的同一套托管方式（HF dataset / 陈宇 HPC）。

## 命名约定（沿用）

```
reports/<runner>/<case>_<UTC时间戳>[_<tag>]/
    console.log  result.json  evidence.json  verdict.json
```
`<runner>` 用流程名而不是人名（`dryrun` / `hpc` / `local`），`<tag>` 用 `PASS` / `warm` 这类语义标签。
