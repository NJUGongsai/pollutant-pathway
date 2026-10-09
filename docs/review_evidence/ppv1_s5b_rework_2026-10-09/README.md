# S5b 启动批有限回修（S5B-L01/L02）实施证据

日期 2026-10-09，Asia/Shanghai。实施代理：S5b 回修批唯一实施会话。
基线（直接父）：`a399d6e665720f6e5f2f836bd6d6ef2e5448a0b2`（S5b 启动批）。
任务来源：复审 `docs/POLLUTANT_PATHWAY_S5B_CODEX_REVIEW_2026-10-09.md`
§8 回修提示词（P1=[S5B-L01, S5B-L02]）。

**结论**：L01 代码守卫 + 预注册发车核对落实；L02 预注册/交付/
r26 请求口径逐条订正。公开反例修前错误评分 → 修后结构化拒
（零样本评分/聚合/持久化）；各合法控制保持。

## 独立执行数字

| 项 | 数字 | 位置 |
|---|---|---|
| PPV1 全量（45 文件，快照树） | **1140 passed / 0 skipped / 0 failed，exit 0**（1133 存量 + 7 新） | `ppv1/` |
| 直接父基线同字节红绿（8 测试文件） | **8 failed / 148 passed / 0 collection / 0 skipped，exit 1**（156 nodeid；1 守卫红 + 7 版本字面量红，首失败分类见 commands.json） | `parent_baseline/` |
| G01 安全隔离（308 输入） | **1740 passed / 10 skipped / 17 deselected，exit 0**（launch 基线 1733 + 7 新精确吻合；输入 SHA 执行前后零不符；9 变更 + 1 新 vs launch 集精确闭合） | `g01/` |
| 公开反例复现 | 修前 PREFAULT_REPRODUCED（codex-a scored + 8 聚合、codex-b not_evaluated、两图 root_identity_fallback）→ 修后 GUARDED_STRUCTURED_REJECT（`real_data_root_identity_fallback_forbidden`，零样本评分/零聚合/零结果写入）；正控 3×2 保持 | `counterexample/` |

## 并行会话事件（如实登记，见 `parallel_session_event.json`）

回修实施中检测到**另一会话**对仓工作树的非本批改动：
`src/pathway_v43/pollutant/runflow.py`（provider 接线内容）与未跟踪
`src/pathway_v43/pollutant/real_model.py`。按 PPV1_REVIEW_PROTOCOL §2
处置：**并行改动结果不冠以本批身份、不回退他方改动**——全部验证
改用 detached 稀疏 worktree 快照（`/private/tmp/ppv1_s5b_rework_snap.
122808`，= a399d6e + 仅本回修 10 文件叠加，`input_snapshot.json`
SHA 核对全同）；他方文件不入任何验证树、不读正文、不提交。
仓内真实树的一轮 PPV1 全量（1140 绿，12:23）因该并行改动归属
不净，只作预备轮，不采信为交付数字（快照轮为准）。

## 目录导航

- `ppv1/`：快照树 PPV1 全量 junit/stdout/stderr/commands（含两份
  冻结正文准入使 r2/r3 守卫实际执行，沿复审先例）；
- `parent_baseline/`：父 a399d6e src 原字节 + 8 个当前字节测试文件
  （7 改 + 1 新）红绿；首失败逐 nodeid 分类（守卫红 =
  `test_real_label_noqid_structured_reject_before_scoring` DID NOT
  RAISE；版本字面量红 7 条；r2/r3 版本红后段冻结 SHA 断言未执行，
  不冒称冻结完整性翻转）；
- `g01/`：安全隔离全量（控制器副本 `scripts/safe_g01_s5b_rework.py`
  本身入包；谱系 R7→…→s5b_launch→**s5b_rework**；对比集 = launch
  G01 307 输入；attempt1 为一次准备失败——快照稀疏树缺 R7 白名单
  中的 5 个 `.DS_Store` 未跟踪杂项，从真实仓原字节补齐后 attempt2
  首跑即成；失败原始 console 保留不删；10 skip 逐 nodeid +
  17 deselect 见 `post_run_sha_result.json`/`preparation.json`；
  243MB 输入副本树留 tmp 不入包 `input_trees_note.json`）；
- `counterexample/`：公开反例修前/修后复现（脚本
  `scripts/repro_real_noqid.py`；tree_pre = a399d6e 归档 83 文件
  守卫 0 处；tree_post = 快照字节守卫 4 处；prefault/guarded 两组
  完整输入输出 JSON + stdout/stderr）；
- `scripts/`：两个执行脚本（控制器与复现脚本，均在 fresh
  /private/tmp 执行，永久证据不原地执行）；
- `parallel_session_event.json` / `input_snapshot.json` /
  `frozen_integrity.json`（criteria-v1 正文 7fd35aab… / FREEZE_RECORD
  6e046e29… 逐字节不变，PASS）。

## 环境与安全

解释器 `/Users/cc/miniconda3/envs/depending43/bin/python -B`，
`PYTHONDONTWRITEBYTECODE=1`、`pytest -p no:cacheprovider`、
`OMP_NUM_THREADS=1`；PPV1/父树零 pyc，G01 隔离子进程 7 个 pyc
如实登记（路径在 `post_run_sha_result.json`）。无真实题面/金标/
封存逐题 run/dependingv4/原 v3 评价资产访问；判分零 LLM；零网络
（反例中的 `data_scope=real`/`approval_status=approved` 是触发程序
门的合成接口标签，全部数据为合成夹具，不外推 dev/298）；不
commit 评审侧未跟踪材料；旧永久证据只读。反例复现沿复审口径：
`real_label_noqid_public` 场景在 fresh tmp 重建（公共 start_run 生成
两条同 CCO 根合成 run），非原地重跑评审脚本。

## 封包

`manifest.json` + `SHA256SUMS` 为本包唯二根控制文件（自排除），
其余全部附件（含 `g01/input_sha256.json` 等嵌套记录）纳入根哈希；
无 SQLite 二进制/pyc/缓存/逸出 symlink。只读校验：
`python3 -B scripts/verify_evidence.py <本目录>`（不导入产品、不写
库；verify 脚本随包）。业务复现须复制指定文件到新 /private/tmp，
按 commands.json 实际 argv/环境重放。
