# PPV1 R6 独立存储复审（2026-10-07）

对象：`/Volumes/CC/Enzyme_Agent/dependingv43`，固定 HEAD `6d9020130a481866ce2f3b79933907a33d8cfc9e`。阅读 AGENTS、R6 delivery / mimo 全文及 R5 Codex review；原仓只读。源码与 16 个 `test_ppv1*.py` 独立复制到 `/private/tmp/ppv1_r6_storage_ql26mzaz`。未读 gold、真实题目资产或封存 run，未调用模型、未跑真实路径实验或全量 1062 套件。

结论：**原 R5-05 的全量 / 部分预存、单 appearance 清单缩短反例，R5-06 的已有假设首次使用，以及 R5-07 的同父兄弟来源，均已按原反例修复。** 新核查仍有两个当前 S0–S2 账本边界缺口：首次引用已存 state / appearance 没有使用重放的事实与 hash 校验；同一 state 的多个不同 occurrence 可以在清单中删去一项而不被检测。没有要求提前实现新的 S3 功能。

## 1. 独立执行与文件

| 执行 | 实际结果 | 证据 |
|---|---|---|
| 16 个 PPV1 文件隔离回归 | **451 passed，0 skipped，1 warning，3.91s** | `pytest_output.txt` |
| R3 旧存储脚本 | 29 条 JSONL，stderr 空 | `r3_storage_probe.py` / `r3_storage_output.jsonl` |
| R4 旧存储脚本 | 21 条 JSONL，stderr 空 | `r4_storage_probe.py` / `r4_storage_output.jsonl` |
| R5 原新边界脚本 | 9 条 JSONL，正确拒绝捕获后继续，stderr 空 | `storage_boundary_probe.py` / `r5_storage_output.jsonl` |
| R6 独立边界 / 正控 | **17 个 case + 1 条 metadata**，stderr 空 | `r6_storage_boundary_probe.py` / `r6_storage_boundary_output.jsonl` |

唯一 warning 为 `chemstate.py:1` 文档字符串的无效转义 `\_`。没有 skipped；不需要 skip 原因。交付和 mimo 的 1062 passed / 16 deselected、44 failed / 26 passed 基线红绿是实施 / 外部评审声明，本线未重新运行。

所有输出和脚本都在以上隔离目录。`metadata.json` 保存 HEAD、原工作区 status 与复制测试文件列表；新脚本也在执行前核查固定 HEAD 并输出审核模块 SHA256。SQL UPDATE / DELETE **只在通过公共 API 新建的合成 SQLite 上模拟损坏**，随后记录公共 submit API 实际行为；不声称公开 put 可以直接写入这些错误值。旧库导入的 before 字节在合成损坏准备完成后采集，import 前后比较确认未写回。

复跑命令（cwd 为隔离目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/ppv1_r6_storage_ql26mzaz/src /Users/cc/miniconda3/envs/depending43/bin/python -B -m pytest -p no:cacheprovider -q -rs tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/ppv1_r6_storage_ql26mzaz/src /Users/cc/miniconda3/envs/depending43/bin/python -B r6_storage_boundary_probe.py
```

## 2. ST-1（P1）：首次引用已存 state / appearance 漏核内容，先成功提交再报损坏

定位：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1505` 首提 `_collect_state_writes` 只复核本次提供的 states；`:1507` 对未提供的参与 state 只查询行存在。
- 同文件 `:1532` 预存 appearance 绑定只读取 `appearance_hash`；`:1554` 唯一出现直接入 manifest，不复算该行内容 hash。
- 同文件 `:1424` / `:1425` 是重放时才执行的已存 state 事实与 appearance hash 验证。
- 具体已实现的重放检查：`:1078` 版本、`:1085` inner ID、`:1129` CN、`:1167` appearance payload hash。

最小反例：先通过 public `put_state` 存有效 CCO 底物及 CC=O 产物；仅在合成 SQLite 中修改一个既存字段；随后 public `submit_event(..., states=[], hypothesis_dict=valid)`。

| 合成损坏 | 首次公共 submit 实际 | 紧接同事件 empty-input replay | probe |
|---|---|---|---|
| 产物 semantic.cn_identity = CCN，结构仍 CC=O | created=True，event/projection/plan 已新增 | LedgerCorrupt(state_row_corrupt)，CN 重推 CC=O | `existing_state_first_cn_identity` |
| 产物 semantic.schema_version = ppv1-chemstate-99 | created=True | LedgerCorrupt(state_schema_corrupt) | `existing_state_first_schema_version` |
| 产物 semantic.state_id 与行键不等 | created=True | LedgerCorrupt(state_inner_id_corrupt) | `existing_state_first_state_id` |
| 原 appearance.source_refs 改动，但 hash 未改 | created=True | LedgerCorrupt(appearance_hash_corrupt) | `existing_appearance_bad_hash_first` |

所有四例首提 `event_present=True`、counts 已增加；重放拒绝时 counts 保全。有效预存行的正控首提 created=True、重放 created=False（`existing_state_first_valid`）。所以不是取消合法先存，也不是不认可 R5-06 已有 hypothesis 的修复；是同一 submit 首提复用 **state / appearance** 仍没有复用已实现的重放校验。

预期：首次引用既存 state / appearance 时即校验版本、内容身份与科学事实、必要 appearance 的内容 hash；错误行首提零新增事件 / 投影 / 计划。不能把“下一次重放会报错”当作首提验证。该问题落在当前支持的先 put 后 submit 入口，不是 S3 调度或真实来源真实性认证。

最小验收：上述四种损坏首提即 LedgerCorrupt、counts 不变、event 不存在；全量 / 部分合法预存及明确提供状态的正常首提和重放保持。阻塞 S0–S2 账本同源验收及据此开放 S3。

## 3. ST-2（P1）：manifest 只保证 state 集合覆盖，同 state 多来源删项仍重放成功

定位：

- `/Volumes/CC/Enzyme_Agent/dependingv43/src/pathway_v43/pollutant/store.py:1254` manifest 完整性只取 state_id 集合，与 derived_refs 比较；不能区分同一 state 的多个不同 appearance。
- 同文件 `:1001` event semantics hash 只复算 participants / catalytic_support / hypothesis_id，没有覆盖 manifest 原始出现集合。
- 同文件 `:1557` 首提按 (state_id, appearance_hash) 去重，正确保存同图不同来源的多个 occurrence；`:1711` 持久清单。因此这类首提是当前明确接受的公开路径。

最小合法首提：CCO → CC=O 的公共 submit 提供 `[substrate, prod-A, prod-B]`。A raw 为 CC=O、refs 为 prod-A；B raw 为 O=CC、refs 为 prod-B。两个 product 的严格 state_id 相同、appearance hash 不同。首提 created=True，manifest 有 3 项（底物一项、同一产物 state 两个不同来源项）；正常无重复 states 重放 created=False。

| 后续合成损坏 | 当前 empty-input replay | probe |
|---|---|---|
| 仅从 event payload manifest 删除 A 项，B 项仍覆盖 product state | **created=False** | `multi_occurrence_manifest_remove_manifest_A_only` |
| 删除 A appearance 行，保持原 manifest | 正确 LedgerCorrupt(event_appearance_manifest_entry_missing) | `multi_occurrence_manifest_remove_row_A_only` |
| 从 manifest 删除 A 项，且删除实际 A appearance 行，B 保留 | **created=False**；A 来源已丢仍认为重放成功 | `multi_occurrence_manifest_remove_manifest_and_row_A` |

变更没有重新计算 event 身份、语义 hash、hypothesis 或其他附件，只模拟一个原始必要 occurrence 被从权威清单移除 / 丢失。该证据不声称防住恶意重建整本账本；它证明当前哈希与覆盖检查没有保存完整 (state_id, appearance_hash) 集合的独立核对依据。同一个 state 还有 B 不能证明 A 从未属于首提清单。

R5 原“删除唯一 product 清单项”现在因缺 state coverage 正确拒绝，应认可修复；但原验收要求是出现集合完整性，不能降为每物种至少一项。也不要求把去除同一 hash 的重复输入当作损坏：这里删的是不同 raw / source_refs / hash 的真实独立 occurrence。

预期 / 最小验收：正常同图多来源首提 / 重放保持；原绑定 distinct occurrence 的删项或丢失必须由独立记录的完整集合或同源完整性摘要检测，即使该 state 尚有另一来源。不得把不同 occurrence 合并为一个 state 来绕过校验；不补账、无 caller 重复输入也能检测。阻塞 S0–S2 完整来源账本验收及据此开放 S3。

## 4. 已修项的独立确认

| 项 | 实际证据 | 源码 |
|---|---|---|
| R5-05 全先存首提空 manifest、正常立刻不可重放 | 原9条：manifest 现在绑定两 ref；正常 replay created=False | store.py:1531 / 1554 |
| R5-05 部分先存删原 A 留无关 B | 原9条：现在 event_appearance_manifest_entry_missing，counts 保全 | store.py:1233 |
| R5-05 sole product manifest 缩短 | 原9条：现在 event_appearance_manifest_coverage_corrupt | store.py:1254 |
| 多既存 occurrence 不猜来源 | 新17条：缺显式 product state 首提 appearance_source_ambiguous，counts 不变；明确提供 A 的控制首提 / 重放成功 | store.py:1543 |
| R5-06 已有假设内容 ID | assumptions 损坏首提 hypothesis_payload_id_corrupt；counts 不变、无 event | store.py:1590 / 1607 |
| R5-06 已有假设 inner ID | ID 与行键错首提 hypothesis_id_corrupt；counts 不变 | store.py:1619 |
| R5-06 已有假设 schema | 未来版本首提 hypothesis_schema_corrupt；counts 不变 | store.py:1628 |
| R5-06 已有假设参与物契约 | 单独的同源四项控制：合成 invalid entry_id 的 payload，其内容重推 ID / inner ID / 行键三者相等、schema 正确，仍首提 hypothesis_participants_corrupt(entry_id_mismatch)，counts 不变、无 event | store.py:1639 |
| R5-06 合法先存假设及排序幂等 | 新17条合法先存首次 created=True、replay created=False；451 套件排序控制通过 | store.py:1648 |
| R5-07 同父同 CN 兄弟错 source pointer | 原9条现在 CN-only + substrate_source_event_relation_mismatch；不导入 B 相反立体 raw；import 旧库字节不变 | legacy_reader.py:299 / 308 |
| R5-07 正确兄弟、合法多位置来源 | 原9条正确 raw 保持；451 套件多位置控制通过 | legacy_reader.py:299 |
| 原 R4 writer raw / CN / 立体 / 同位素 / fidelity / CN-only | 21 条原探针的错误输入仍结构化拒绝；同图异拼写控制保持 | r4_storage_output.jsonl |
| 原 R3 版本门、必要表 / 内容损坏、空计划 / 跳阶段 | 29 条原探针保持拒绝 / 披露；不补账 | r3_storage_output.jsonl |

同源参与物专项控制 `existing_hypothesis_self_consistent_bad_participant` 用合法公开 event 构造链引用已损坏的合成假设行，只用于验证“ID 相等后仍检查参与物契约”；不是一个新增缺陷。mimo R6 明确将存储三项排除在化学抽查范围，其化学意见不替代这里的程序验收。

本线不提出兼容已发布 v5 PPV1 run 的新要求：交付明确这些 profile 从未放行，v6 升版、无迁移符合既有审核口径；未来 / 不支持 schema 应由入口明确拒绝。独立发现 ST-1 的未来已存 state 首提接受是现有版本门路径遗漏，与要求新兼容或迁移不同。
