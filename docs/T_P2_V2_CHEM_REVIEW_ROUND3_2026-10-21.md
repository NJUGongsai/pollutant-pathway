# qwen3.8max 代 Codex 复审（第三轮限定）——P2 v2 chemfix

> **Provenance**：qwen3.8max 代 Codex 复审，按 CC 2026-10-21 指示（Codex 无额度，
> 不冒充 Codex 本人；Codex 正链最终裁定权保留）。日期 2026-10-21。
> 复审材料 `docs/review_evidence/p2_v2_chemfix_2026-10-21/RE_REVIEW_ROUND3_LIMITED_2026-10-21.md`
> （SHA-256 `12244115822fbc2cbc1e8ebf6e6c8707b1706daf6642441b2f1d65ef88788743`，与
> SHA256SUMS 一致）。限定范围：① E1–E3 身份账 ② N1/N2/N5 提示词措辞 ③ 新 prompt SHA。
> 零模型/网络/费用；未读金标/题面/reports 封存 run/env/key；主仓只读，唯一写入为本文件。

## 0. 总裁定

**PASS（限定范围内）**。

三项限定验收全部由本会话在隔离树独立复现通过；两处历史中间值
（`ba58b940`、`f7597230→63d2d91a` EOF 关系）本机无副本、不可复算，如实登记为
unknown——与材料自身 §7 的诚实声明一致，不构成身份链缺口（最终态全链实测闭合）。

## 1. 逐项判定表

| 项 | 判定 | 证据（实测 vs 声称） |
|---|---|---|
| E1 身份账 | **PASS** | SHA256SUMS 21/21 OK；§1 表 6 个 SHA 实测全等；impl.patch=`cd8c03e0…ebbd6`、chemfix.patch=`90f0d83b…00bc` 实测一致；隔离树 `11aeeaf`+两 patch 干净应用后 `candidate_evidence.py`=`82b9b7cf3dcc…098d17`（=声称）、`real_model.py`=`6351e9b8b32f…a1ed1`（=材料 §3.5 N 轮最终值）、测试=`c560977a…dd73d`（=声称）；before 树源码 `4772e90a…c83c20`/`6ce2772f…4560` 与 off_path_compare before 值全等；旧中间态 `67584037/3ca6130e/f8cc3fda/70ffc05b/eebca5/ab66ad4d/24b024be` 经哈希前缀搜索均未在盘 →「已被取代」声明成立 |
| E2 全量日志 | **PASS** | 当前 `pytest_not_slow.log` 实测 3194 B、结尾 `2388 passed, 16 deselected, 1 warning in 357.69s`、SHA `4c03e223…ebcb15` 全等声称；且本会话隔离树独立重跑 `-m "not slow"` 得 **2388 passed / 16 deselected**（361.37s），非仅日志核对 |
| E3 测试 SHA | **PASS**（历史值 unknown） | N 轮最终 `c560977a2928…dd73d` 实测一致（隔离树 apply 产物 + 本机 4 份 tmp 副本全同），文件以 `0x0a` 结尾；`f7597230`/`63d2d91a` 及 EOF 换行复算关系：本机无任何副本（E1 patch `70ffc05b` 已不存在），**unknown**——材料 §4.2 声称为其当时实测，与其 §7「旧副本已不在本机、不伪造旧字节」自洽 |
| N1 措辞 | **PASS** | `Functional-group class labels are protonation-tolerant (a protonation change alone is not a class gain or loss), and classes are computed on the substrate and on the entry's designated principal product.` 在 `_PROMPT_EVIDENCE_NOTES_V2` 中逐字命中（程序比对 True） |
| N2 措辞 | **PASS** | `n_hits is the number of distinct matched atom tuples (match sites) for that class on the substrate and may exceed the number of functional groups:` 逐字命中（True）；`test_p3_n_hits_definition_in_prompt` 已断言 `may exceed` |
| N5 措辞 | **PASS** | `substrate_render_ok is false when the substrate structure could not be rendered; … substrate_render_ok true with an empty table means the structure parsed and no class pattern matched.` 全句逐字命中（True） |
| N1/N2/N5 测试与探针一致性 | **PASS** | `tests/test_p2_v2_chemfix.py::test_n1_n2_n5_prompt_wording` 存在，断言与 §5 三句关键词一一对应；19 探针独立复跑 **19/19 PASS**，`N1_N2_N5` 段 6 关键词（protonation_tolerant / protonation_change_not_class_delta / computed_both_sides / may_exceed_groups / substrate_render_ok / render_failure_vs_zero_hit）**全 true** |
| prompt SHA v2 新值 | **PASS** | 隔离树实测 `hashlib.sha256(proposals_system_prompt('v2'))` = `c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598`，常量 `PROPOSALS_PROMPT_VERSION_V2` 同值，测试写死锁 `NEW_V2_PROMPT_SHA256` 同值，探针 `prompt_v2_sha256` 同值——四路一致 |
| prompt SHA v1 不变 | **PASS** | 实测 `proposals_system_prompt('v1')` = `fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e`，与声称一致；`off_path_compare.json` 读取核验 **20/20 all_ok**（prompt_v1_bytes_equal / evidence_v1 / substrate_v1 / A、B 载荷字节全等 true；identity 差异仅路径标签+聚合哈希+本次有意修改的 2 个源文件） |

## 2. 独立执行记录（声称 vs 本会话实测）

- **环境**：主仓 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD
  `966bc5664a7daa30f24860d2b5594a9dddc6eee2`（材料基线 `11aeeaf` 为其祖先 commit，
  `git cat-file` 确认存在）；隔离树 `git worktree add --detach /private/tmp/p2r3_review
  11aeeafded1b41185f24de49767933709aad49db`（HEAD 实测 `11aeeaf…49db`）；
  Python `/Users/cc/miniconda3/envs/depending43/bin/python` 3.11.16、
  rdkit 2026.03.6、pytest 9.1.1；全程 `PYTHONDONTWRITEBYTECODE=1 -B`、
  pytest `-p no:cacheprovider`。主树 src/ 状态未信任，全部结论出自隔离树。
- **patch 应用**：`git apply --check` + `git apply`（impl.patch→chemfix.patch，
  主仓绝对路径引用）均干净通过；改动面 = 3 源文件修改 + 2 测试新增，与声称一致。
- **哈希**：SHA256SUMS `shasum -a 256 -c` 21/21 OK；§1 表 6 项、E3 测试、
  源码修后值、before 树值全部实测（数值见 §1 表）。
- **prompt SHA**：本会话重算 v2/v1（命令同材料 §6 口径），声称=实测。
- **探针**：`chemfix_19probe.py --src /private/tmp/p2r3_review/src` →
  19/19 PASS、exit 0（声称 19/19，实测同）。
- **测试**：`test_p2_v2_chemfix.py` **36 passed**；+`test_p2_evidence_card_v2.py`
  **54 passed**（=36+18，声称同）；全量 not-slow **2388 passed / 16 deselected**
  （声称 2388/16，实测同；耗时 361.37s vs 日志 357.69s 属正常波动）；
  `pytest_targeted.log` 结尾实测 `125 passed`（定向 5 文件，声称同，日志核对）。
- **v1 零漂移**：采用「读文件核数」路径——`off_path_compare.json` n_checks=20、
  n_ok=20、all_ok=true（该文件及其 before/after 输入 json 均在 SHA256SUMS 校验内）；
  未在隔离树重跑 off_path_compare.py，如实注明。

## 3. 不符项 / 条件项 / 最小回修建议

**不符项：无（限定范围内）。** 两条登记事项：

1. **指令预期与材料的口径差（非缺陷）**：派单指令写「apply 后 real_model.py 应为
   `ba58b940…`」；材料 §2/§3.5 明确 `ba58b940` 是 **E1 时值**，N 轮 prompt 修订后
   最终值为 `6351e9b8…a1ed1`。本会话实测 = `6351e9b8…a1ed1`，**与材料一致**；
   `ba58b940` 属历史中间值，其载体 patch `70ffc05b` 本机无副本 → 该历史值
   **unknown**（不可复算），不影响最终身份链闭合。
2. **文档小疵（不要求回修既有证据）**：`IDENTITY_RECONCILIATION_2026-10-21.md` §6
   的「EOF 差异复算」命令指向
   `/private/tmp/dependingv43_p2_integration/tests/test_p2_v2_chemfix.py`，该文件
   N 轮后已是 `c560977a`（mtime 18:13），命令对 `f7597230→63d2d91a` 复算已过时。
   该文件属封存证据不得改动；建议在下一轮新报告/新证据目录中澄清一句即可。

## 4. 仍需 CC / 老师批准的事项

- 本复审**不批准发车、不代签预注册**；token 门数值需以新 prompt（`c24bee42…`）
  重测，归后续拍板。
- 旧 prompt SHA（`e2aa2bbf`、`89311fdb`）出现在任务书/预注册等下游文档的同步
  更新（材料 §6 备注），由 CC 决定何时改哪些文档。
- Codex 正链额度恢复后对本轮 PASS 的复核确认权保留。

## 5. unknown / 未核清单

| 项 | 状态 | 原因 |
|---|---|---|
| `real_model.py` E1 历史值 `ba58b940…4a73` | unknown | 载体 patch `70ffc05b` 已被 `90f0d83b` 取代且本机无副本 |
| 测试文件 `f7597230` / `63d2d91a` 及 EOF 换行复算关系 | unknown | 本机 4 份 tmp 副本均为 `c560977a`；E1 版无副本。材料声明（§4.2 当时实测）内部自洽 |
| 17:20 报告 `ab66ad4d` / patch `eebca5`、17:25 报告 `3ca6130e`、delta `f8cc3fda`、中间态 patch `67584037`、E1 全量日志 `24b024be`、86 B 截断日志 | unknown（不存在性已核） | 均不在盘（文件名+哈希前缀双重搜索无果），「已被取代/无副本」声明成立 |
| off_path_compare.py 隔离树重跑 | 未执行 | 采用读文件核数路径（20/20），已注明 |
| P1–P7 化学结论、真实 298 分布、token 门、R4、判分/池/检索/存储/resume | 不在范围 | 材料 §9 边界；二轮化学 PASS 见 `docs/T_P2_V2_CHEM_REVIEW_ROUND2_2026-10-21.md` |

## 6. 边界重申

不重做 P1–P7 化学；不批准发车；不代签预注册；不评真实 298 分布与 token 门数值；
Codex 正链最终裁定权保留。本会话未改 src/tests/既有 docs/AGENTS.md/既有证据目录，
未 commit、未 push；自建隔离树 `/private/tmp/p2r3_review` 审毕以
`git worktree remove --force` 清理。
