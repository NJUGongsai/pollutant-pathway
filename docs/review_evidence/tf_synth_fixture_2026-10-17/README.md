# T-F 合成验证证据目录（2026-10-17，主会话自干）

- 实际 HEAD：`3440ca760ab35d5949cb0947c3c72922575349dc`（v4.3）；执行时工作树零已跟踪改动（git diff 为空，仅未跟踪新增）。
- 执行方式：脚本在全新临时目录 `/tmp/tf_synth_fixture_2026-10-17/` 运行（PYTHONPATH=仓库 src、PYTHONDONTWRITEBYTECODE=1、cwd=仓库根仅为 resolve_config；runs_root 指向临时目录，仓库零写入）。
- 复现命令：
```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python \
  /tmp/tf_synth_fixture_2026-10-17/tf_synth_fixture.py
```
（脚本自包含：池/novel 构造、prepared id 镜像算法、四趟运行、结果 JSON 落盘）
- 文件：
  - `tf_synth_fixture.py` —— 夹具脚本（scripted 协议零模型；纯构造输入零金标零题面）
  - `tf_fixture_output.json` —— 机读输出（四夹具全量结果+签名前置核验）
- 运行数据（sqlite/events）留在 /tmp 临时目录（易失，脚本可复现）。
