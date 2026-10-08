# S3b queue / public recovery independent evidence

实际日期 2026-10-08（Asia/Shanghai）。实际代码提交与输入 SHA 见 `input_manifest.json`、`execution_metadata.json`。本专项只在新 tmp 合成运行，不写主仓；Python depending43 `-B`、禁 bytecode，无 pytest/provider/network。结果按 `SPECIALIST_REVIEW.md`、`adjudicated_summary.json` 裁定；`observed_check=true` 也可能是“缺口被实证”，不能计为通过测试。

- `scripts/probe_public.py`：公共 workflow.runner 两入口，E01/C06/H04/分支/零资源、四硬杀、冻 plan 恢复、novel、显式转换、H07/H08、双 start barrier。
- `scripts/probe_supplemental.py`：只补未完成/失效 fault 片段及计划内 deferred/格式反馈/双 resume 执行 barrier；不复跑已完成正控。
- `inputs/`：每个 child 的完整 JSON 输入；`logs/`：cmd/env/returncode/完整 stdout/stderr；`tables/`：每个明确边界全部 15 张 SQLite 表和可读 artifact/身份。`artifacts_final/`：合成 run 的最终身份与结果原始 bytes（包括故意坏 JSON）。SQLite 二进制与 barrier 临时文件不归档；完整 omission inventory SHA 与逐表结果不变。
- `observations.json`：第一批 34 顶层观察；`supplemental_observations.json`：6 观察。不代表 40 passed。
- `zero_depth_existing_extraction.json`：仅从原已执行 zero_depth 输出提取预算、实际 outcome、停止报告，未新执行。
- `source_review_lines.txt`：所用代码链定位；`src/` + `pyproject.toml`：执行源快照（含 vendor），本地完整依赖版本见 metadata。
- `omitted_binary_inventory.json`：未归档的合成库/WAL/barrier文件大小和 SHA；无题面、真实数据、封存 run。

本轮非账号额度中断。原脚本在 low-level distinct-worker barrier 输出捕获处空 stdout 引发 IndexError，之前所有输出保留；这条只按持久行+一方拒绝有限采信。原多产品 injector 没触发已明示；补脚本采用 fresh 新 run/新标签作有效注入。两个 H07 `observed_check=false` 是生产恢复绕过失败的证据，不能更改原观察。

## 复现纪律

**不要在永久证据目录原地执行会写库的脚本。** 全包复制到新 tmp，源快照、pyproject 与 scripts 保持相对布局；运行命令：

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<新tmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <新tmp>/scripts/probe_public.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<新tmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <新tmp>/scripts/probe_supplemental.py
```

脚本 ROOT 从复制位置派生，controller 会新建自己的输入和合成运行；first controller 的已登记 capture error 预期 exit1，不是所有观察未执行。单案 worker 可消费 `inputs/<case>.json`，但该文件记录的是历史绝对 runs_root；复现前生成新 JSON 并将 runs_root 改到新临时目录，不回写历史输入/数据库。

外层 `manifest.json` 采用 `files` **list**，每项 `path/bytes/sha256`；只不自包括三份外层控制文件 manifest/SHA256SUMS/manifest.sha256。`SHA256SUMS` 同时钉 manifest bytes；`manifest.sha256` 给 manifest SHA。任何归档后新增/改写文件需报告，不在原目录重建清单。
