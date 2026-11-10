# BIBLE 契约（第一批）

> 用途：把弓赛线验证过的评测工程纪律沉淀成九条可执行 skill。
> 本文件是**派工契约**，三个子代理各自按本文件交付，互不改对方的文件。
> CC 2026-10-26 拍板：先做 L1（方法论资产），L2/L3 后续。

---

## 一、九条 skill（slug 固定，不许改名）

| # | slug | 一句话规则 |
|---|---|---|
| 1 | `prereg-first` | 预注册先于付费：判定线、身份、发车登记先写死，再花钱 |
| 2 | `zero-llm-scoring` | 判分零 LLM、金标隔离、封存只读、泄漏扫描 |
| 3 | `probe-before-build` | 零 LLM 探针先行：召回/误拒实测过门才立项 |
| 4 | `batch-discipline` | 单变量成臂、凑批、同批对照、事后标签 |
| 5 | `loss-attribution` | 失分桶闭合：桶合计 = 分母，逐题配对 diff，换手分析 |
| 6 | `stop-loss-gate` | 未达线强制回查，净增益不足不宣称有效 |
| 7 | `dual-caliber` | 口径变更走新版本流程，双口径并列，历史不覆写 |
| 8 | `review-loop` | 多 AI 评审环：正链复审 + 化学评审 + 互证注记 + 代审标注 |
| 9 | `anchored-numbers` | 一切数字带锚：commit + 口径 + 批次 SHA，缺一不写 |

---

## 二、文档模板（每份 `docs/BIBLE/<slug>.md`）

固定七节，不许增删（可加附录）：

1. **一句话规则**（≤40 字，能贴在墙上）
2. **为什么**（一句人话，说清不这么做会出什么事）
3. **细则**（3–6 条，每条一句话 + 必要解释）
4. **反例**（≥2 个，**每个必须带真实 `docs/xxx.md:行号`**，不许编造；找不到就写"待补"）
5. **检查清单**（可勾选，开工前/发车前/交付前三段各若干条）
6. **机器检查**（指向 `scripts/bible_checks/check_<slug>.py`，写清怎么调用、通过/失败长什么样）
7. **模板**（可选：一段可复制的 md 骨架，如预注册头、发车登记行）

写作红线：
- 反例必须能在仓里定位到；数字必须带口径标签；
- 不许把"应该"写成"已经"；不确定的事实写"待核"；
- 每条 ≤250 行，宁短勿空。

---

## 三、机器检查契约

**位置**：`scripts/bible_checks/`

**调用**：
```bash
python3 scripts/bible_checks/check_<slug_underscore>.py --repo /Volumes/CC/Enzyme_Agent/dependingv43 [--files <glob>]
```

**输出**：stdout 人类可读摘要（≤20 行）+ 最后一行 JSON：
```json
{"check":"prereg-first","status":"pass|fail|error","n_pass":3,"n_fail":1,"findings":[{"path":"...","line":12,"msg":"..."}]}
```

**退出码**：0 = pass，1 = fail（发现违规），2 = error（无法检查）

**公共库** `scripts/bible_checks/_lib.py`：
- `load_text(path)` / `iter_md(repo, glob)` / `emit(check, status, findings)` / `git_head(repo)`
- 统一处理 Windows/UTF-8、跳过 `.git` 与 `review_evidence/` 里的大 JSON

**runner** `scripts/bible_checks/run_all.py`：跑全部已存在的 check 脚本，汇总一张表。

### 第一批只实现这三个脚本

| 脚本 | 检查什么 | 判定 |
|---|---|---|
| `check_prereg_first.py` | 给一个批次根目录（`--batch <path>`），校验：预注册 md 存在、含判定线字段、approval package 哈希可核、发车登记行存在 | 缺任一 → fail |
| `check_zero_llm_scoring.py` | 扫 `src/**/scoring*.py` 与 `scoring/` 目录：不得 import LLM 客户端（`openai`/`dashscope`/`requests` 调模型域）、判分器源码哈希须与 `docs/T_P2_SCRIPT_LOCK_2026-10-21.json` 或同类锁文件一致、金标路径不得出现在可写路径清单 | 违规 → fail |
| `check_anchored_numbers.py` | 扫 `--files` 指定的 md（默认：`git diff --name-only HEAD` 中的新增 md）：形如 `NN.N%` 或 `NNN/298` 的数字，同一行/相邻 2 行内须有 commit(7-40 hex)、口径标签（v1/v2/v3/dev/298）、批次名之一 | 无锚 → fail（每条 finding 带行号） |

**质量要求**：三个脚本必须在本仓**真实跑出结果**（不许空壳、不许全 pass 了事、不许靠模拟数据）。若某脚本对现有资产必然 fail，就在报告里写清是资产真违规还是检查太严，并给出降误报的参数化方案。

---

## 四、交付边界（红线）

- 只**新建**文件，不改任何既有 `docs/*.md`、`src/**`、`AGENTS.md`；
- 不 commit、不 push；
- 不读 `reference_graphs/`、`env/`、任何密钥；不打印 token；
- 数字不编：仓里查不到就写"待核"；
- 完成后回传：改了哪些文件（路径+行数）、跑了什么命令、结果如何、遗留问题。

## 五、待补（第二批）

其余六个 check 脚本（probe-before-build / batch-discipline / loss-attribution / stop-loss-gate / dual-caliber / review-loop）在第一批验收后按同一契约补齐。