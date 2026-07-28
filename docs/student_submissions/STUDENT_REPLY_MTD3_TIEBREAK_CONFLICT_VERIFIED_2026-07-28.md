# Student reply: MT-D3 OrganismAggregator tie-break conflict, verified version

日期：2026-07-28

回应对象：

```text
TEACHER_QUERY_MTD3_TIEBREAK_CONFLICT_2026-07-28(1).md
```

## 1. 可直接发送给黄老师的回复

黄老师，MT-D3 这个冲突我重新核对了一下。

07-27 交付版 `OrganismAggregator` 当前确实实现为：

```text
supporting_enzyme_count 降序，随后按 NCBI taxon ID 数字升序进行 tie-break。
```

关于 A1，这个实现本身不是无意产生的随机偏差，而是按照聚合后的 organism/taxon candidate 层做出的有意识工程选择；但我们没有在最终文档中把该实现与早先裁定文中的“UID 升序”完成正式消差，因此形成了当前的文档—代码口径分歧。这个文档消差遗漏由我们承担。

我又核对到 07-21 的后续裁定文 `TEACHER_REPLY_M3_P1_UNLOCK_CASE1_REBOUND_AND_METATRAITS_M4A_ADJUDICATION_2026-07-21.md` §MT-TQ-01 中已经写明：

```text
MT-D3 UID tie-break 歧义 → 采纳当前 NCBI taxon ID 数字升序实现
```

因此我的理解是：07-16/07-18 原始 MT-D3 裁定文中的 UID 升序表述没有被回写更新，但 07-21 后续裁定已经把该歧义裁定为保留当前 NCBI taxon ID 数字升序实现。

采用 NCBI taxon ID 的主要原因是：聚合单位是 taxon group，聚合后候选菌的生产主键是唯一的 `ncbi_taxon_id`；而一个 taxon group 可能由多条 enzyme UID 支撑。如果采用 enzyme UID 作为候选菌之间的 tie-break，还必须额外规定使用组内最小 UID、最高排名酶 UID，还是其他代表 UID，否则比较对象存在二义性。相比之下，直接比较聚合候选自身的 `ncbi_taxon_id`，比较对象唯一，能够保证同一输入得到完全确定且可复现的顺序。

当前代码中的实际排序为：

```python
candidates.sort(key=lambda candidate: (-candidate.supporting_enzyme_count, candidate.ncbi_taxon_id))
```

也就是先比较 `supporting_enzyme_count`，count 相同时直接比较聚合记录自身的 `ncbi_taxon_id` 整数值。

现有 15 个通过测试中有覆盖同分 tie-break 的用例：

```text
test_aggregator_grouping_default_order_dedup_and_name_variants
```

该用例中 taxon 3 与 taxon 11 的 `supporting_enzyme_count` 均为 1，测试断言最终顺序为 `[20, 3, 11]`：taxon 20 因 supporting count 更高排在前面，taxon 3 和 taxon 11 同分后按数字 taxon ID 升序排列。

关于真实酶池中的打平频率，目前我们尚未对全量真实聚合结果做专门统计。根据聚合机制推断，若大量 taxon 仅由 1 条 supporting enzyme 支撑，count=1 的同分组可能比较常见；但具体频率和 Top-K 边界受影响的比例仍应以真实聚合结果审计为准。

这处 tie-break 不会改变完整候选池、各 taxon 的 supporting-enzyme count、supporting UID、score、rank、CI 或 provenance；但如果 Top-K 截断边界落在同 count 候选组内部，它可能改变同分候选的内部顺序，以及哪些同分候选进入 Top-K。

基于以上原因，并结合 07-21 后续裁定，我建议将最终文档口径统一为：

```text
supporting-enzyme count descending + numeric NCBI taxon ID ascending tie-break
```

并同步更新仍保留旧表述的早期裁定/汇总文档，使文档与代码口径一致。

附一个与本次 MT-D3 不冲突、但和后续 MetaTraits data plane 有关的小提示：我们内部讨论到，既然此前 D5 里 documented API 路由出现 16/16 HTTP 404，而网页 summary/search 在 5 个样本上可以返回 HTTP 200，后续如果转向 official versioned snapshot 作为生产主数据面，可以补一个很小的只读探测：在 snapshot 内同时测试 `NCBI taxon_id exact lookup`、`species name lookup` 和 `strain name lookup` 三种入口，尤其看 UniProt 返回的菌株名能否比物种名更好地命中 MetaTraits 记录。

但这个只能作为候选发现/人工核查入口，不能替代老师前面要求的 ID 对齐规则。最终 trait 继承仍应区分：

```text
exact strain；
exact species；
no exact match established。
```

也就是说，如果 strain name 搜索能命中，它可以帮助我们发现 snapshot 中可能存在的菌株级记录；但不能因为名字模糊相似，就把 species trait 继承给 strain，或把 strain trait 继承给 species。这个建议目前只是后续小试，不是已验证结论，也不改变当前 M4a/MT-D3 实装。

## 2. 本地复核结论

```text
SENDABLE_STATUS=PASS
OVERCLAIM_CHECK=PASS_WITH_DISCLOSURE
TEACHER_ORIGINAL_FILE_MODIFIED=FALSE
SCORING_OR_CODE_CHANGE=FALSE
METATRAITS_STRAIN_NAME_LOOKUP_NOTE=ADDED_AS_PROPOSAL_NOT_RESULT
```

说明：

1. 上面回复没有说“全量真实酶池已经统计过 tie 频率”；只说“尚未专门统计”，并把常见性表述为基于机制的推断。
2. 上面回复没有说“07-16/07-18 原始裁定文已经更新”；事实是原始裁定文仍保留 UID 升序表述。
3. 上面回复补充了 07-21 后续老师裁定，避免遗漏已有权威文本。
4. MetaTraits strain-name lookup 只写成“后续小试建议”，没有写成已经验证或生产可用。
5. 本轮没有改代码、没有改老师原始文档、没有跑新实验。

## 3. 依据位置

### 3.1 早期裁定仍保留 UID 升序表述

本地文件：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/00_Authority_Teacher_Plan/TEACHER_REPLY_MTD5_ACCEPTED_AND_MTD1_D8_DECISIONS_2026-07-18.md
```

相关段落：

```text
MT-D3：OrganismAggregator 排序主键 → 延后，v1 先锁 B
v1 默认实现锁 B（supporting-enzyme 数量降序 + UID 升序 tie-break）
```

备注：老师本次 query 中写的是 `TEACHER_REPLY_MTD5_ACCEPTED_AND_MTD1_D8_DECISIONS_2026-07-16.md`，本地实际可见文件名为 `...2026-07-18.md`，内容与 query 引用的 MT-D3 表述一致。

### 3.2 07-21 后续裁定已经采纳 NCBI taxon ID 数字升序

本地文件：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/00_Authority_Teacher_Plan/TEACHER_REPLY_M3_P1_UNLOCK_CASE1_REBOUND_AND_METATRAITS_M4A_ADJUDICATION_2026-07-21.md
```

相关段落：

```text
MT-TQ-01：MT-D3 UID tie-break 歧义 → 采纳当前 NCBI taxon ID 数字升序实现
裁定：保留学生当前实现（NCBI taxon ID 数字升序做 tie-break），不切换为 enzyme UID 字符串升序。
```

### 3.3 当前实现

本地文件：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_m4a3a_portable_validator_transport_final_correction_20260720/source/microbe_crew/tools/organism_aggregator.py
```

关键实现：

```python
candidates.sort(key=lambda candidate: (-candidate.supporting_enzyme_count, candidate.ncbi_taxon_id))
```

### 3.4 测试证据

测试文件：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_m4a3a_portable_validator_transport_final_correction_20260720/source/microbe_crew/tests/test_enzyme2organism.py
```

用例：

```text
test_aggregator_grouping_default_order_dedup_and_name_variants
```

测试日志：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_m4a3a_portable_validator_transport_final_correction_20260720/logs/m4a3a_pytest.stdout.txt
```

测试结果：

```text
15 passed in 9.54s
```

### 3.5 Smoke report

本地文件：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_m4a3a_portable_validator_transport_final_correction_20260720/source/microbe_crew/M4A_SMOKE_REPORT.md
```

相关段落：

```text
Default v1 sorting: supporting-enzyme count descending, numeric NCBI taxon ID ascending.
```

### 3.6 MetaTraits data-plane 小提示的依据

D5/D5A2 evidence：

```text
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_mt_d5_interface_coverage_probe_20260716/metatraits_probe_report.md
/home/a/EnzymeCAGE/custom/docs/enzyme_feature_expansion/ENZYMECAGE_LUCAPCYCLE_MODEL_TRAINING_RUN_2026-07-01/03_HPC_Returned_Result_Summaries/metatraits_mt_d5a2_https_handler_and_required_evidence_final_correction_20260716/MT_D5A2_CORRECTION_REPORT.md
```

依据点：

```text
documented API probes: 16/16 HTTP 404 in D5；
D5A2 current summary evidence: 5/5 selected sample summary.json HTTP 200；
species-query collapse observed, so strain preservation is not claimed；
no observed 429 in bounded probe does not establish unlimited API；
production-wide coverage and production readiness remain unresolved。
```

因此，strain-name lookup 只能作为 snapshot/data-plane 后续只读探测建议，不是当前结论。
