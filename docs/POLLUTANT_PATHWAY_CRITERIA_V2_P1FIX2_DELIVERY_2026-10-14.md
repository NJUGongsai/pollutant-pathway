# 交付书 — criteria-v2 终裁余项 P1fix2：appearance 首次消费完整集合校验（2026-10-14）

> 任务书：`docs/TASK_CRITERIA_V2_P1FIX2_2026-10-14.md`；终判报告：
> `docs/POLLUTANT_PATHWAY_CRITERIA_V2_FINAL_DECISION_2026-10-14.md`（唯一阻塞
> 余项 P1 + 有限验收）。执行：实施子代理。

## 一句话结论

**修完了，全绿。** 官方链第一次"拆包"持久状态出现记录时，现在对**完整出现集合**
逐行验三件事——载荷是对象、state_id 绑对、内容哈希对得上（哈希判据与写入/重放
共用同一个函数，没有另立标准）——坏记录在构建处就被结构化拒绝，后面 persist/
export/reader/evaluator 一步都不走；合法数据一个字节都没变（同库双树构建全等 +
同一 run 缺省 v1 评估/判分字节全等），全量 not-slow 父树 2121/0/16 精确复现基线、
修复树 2125/0/16（= 基线 + 本轮 4 件新测试），零翻转。

## 改了哪些文件（改动面恰为 3 文件，均未提交）

| 文件 | 改动 | +/- 行 | 说什么 |
|---|---|---|---|
| `src/pathway_v43/pollutant/store.py` | 抽单一验证源 | +49/−30 | 新增模块级 `_verify_appearance_content_hash()`（内容⇄哈希判据唯一出处）；收集阶段复用核（R7-02/R8）、重放 `_verify_stored_appearances`、`_verify_event_appearance_manifest` 三处改为调用它，**消息原文 AST 级逐字保持（3/3）**，detail 键集不变（event_id 键移至末尾） |
| `src/pathway_v43/pollutant/native_result.py` | 完整集合核验 | +78/−17 | `_validate_native_state_rows` 从"只索引 dict 载荷"扩为**逐行核 ①对象形状 ②appearance_hash 内容绑定（经 store 单一验证源）③state_id 绑定（与行键/语义块一致）**；结构化 kind=`native_result_appearance_corrupt`，reason 三分（payload_not_object / appearance_hash_mismatch / state_id_binding_mismatch），底层 kind/detail 原样保全；原 (语义， 出现) 逐对 from_dict 事实重算保持不变 |
| `tests/test_ppv1_s4b_export.py` | 新增 4 测试 | +156/−0 | 合法正控+重放幂等 / 形状拒（[] 主反例同构）/ 哈希拒（错绑旁证同构）/ 绑定拒（重签腐蚀） |

不碰判分侧（evaluation/s5b_scoring 零改动）；金标/题面零触碰（全合成 run）；
零模型零网络；**未 git add / 未 git commit**（并发 C 轮同树，主窗口统一收口）。

## 终判"有限验收"逐条对照

| 终判验收要求 | 结果 | 证据 |
|---|---|---|
| 对被消费的完整 appearance 集合核验形状/state_id 绑定/既存 appearance_hash 内容绑定；与写入/重放共用验证来源，不另立判据 | ✅ 三查全落；哈希判据经 `_verify_appearance_content_hash` 单一函数（写入收集/重放/首消费共用） | `store.py:464-491`、`native_result.py:93-217` |
| 不静默丢弃坏行、不重算新哈希洗损坏 | ✅ 坏行当场结构化拒绝；哈希永远与 `appearance_hash` 列比，不重写 | 探针+测试 |
| `[]` 主反例在首次消费结构化拒绝、后续 persist/export/reader/evaluator 不执行、底层损坏可追溯 | ✅ build 拒绝（reason=payload_not_object，appearance_hash_matches=false 底层附入）；六步链只走第 1 步 | `postfix_participant_appearance_output.json` |
| 错绑 state_id 旁证同上 | ✅ build 拒绝（reason=appearance_hash_mismatch，底层 kind=appearance_hash_corrupt 与同库重放同一结论） | 同上 |
| 合法多出现正控完整导出、公共 submit_event 重放幂等 | ✅ 3 条出现完整导出、digest 可复现、重放 created=false | 同上 + `test_native_build_multi_appearance_legal_export_and_replay` |
| 原 cn 负控、零出现负控、合法结构/CN-only 边界、P2 闭合继续保持 | ✅ 11 文件受影响子集 211 passed（207 既有 + 4 新）双树全绿 | `pytest_full_*` |
| 缺省 v1 字节不变（双树对照） | ✅ 同库双树 build 载荷 SHA 全等 + 同一 run 三探针 stdout 字节全等 | `v1_byte_identity/` |
| 新增测试 + 全量 not-slow 零翻转（基线 2121/0/16） | ✅ 父树 2121/0/16 精确复现；修复树 2125/0/16（+4 恰为新测试） | `pytest_full_parent_tree.stdout`、`pytest_full_fixed_tree.stdout` |

## 两反例拒绝输出（结构化错误原文）

**[] 主反例**（终判同构；修复后）：

```
type: NativeResultContractError
detail: {
  "kind": "native_result_appearance_corrupt",
  "state_id": "cs_a41af84d453ceaadda96",
  "reason": "payload_not_object",
  "payload_kind": "list",
  "appearance_hash": "963a61ccf86fdcfe1b3783bf22af5d967e14e3eccad87aeda44e3ca1ef90b024",
  "appearance_hash_matches": false
}
after_step: "read_endpoint"（六步链 steps_executed=1，persist/export/reader/evaluator 未执行）
```

**错绑 state_id 旁证**（终判同构；修复后）：

```
type: NativeResultContractError
detail: {
  "kind": "native_result_appearance_corrupt",
  "state_id": "cs_a41af84d453ceaadda96",
  "reason": "appearance_hash_mismatch",
  "appearance_error_kind": "appearance_hash_corrupt",
  "appearance_error_detail": {"table": "state_appearances",
    "kind": "appearance_hash_corrupt", "state_id": "cs_a41af84d453ceaadda96",
    "appearance_hash": "963a61ccf86fdcfe1b3783bf22af5d967e14e3eccad87aeda44e3ca1ef90b024"}
}
after_step: "read_endpoint"（steps_executed=1）
```

合法正控：六步全过（read_endpoint→build→persist→export→reader→evaluator v2），
`public_submit_event_replay.accepted=true, created=false`；两反例同库公共重放侧
同判据拒 `Ppv1LedgerCorrupt(appearance_hash_corrupt)`（首消费与重放已无分裂）。

## 字节不变四对照（parent=纯 HEAD，fixed=HEAD+本轮 3 文件；diff -rq 确认无其他差异）

| 对照 | parent | fixed | 相等 |
|---|---|---|---|
| 同库双树 build 载荷 SHA256（合法数据零行为差） | `01ca528d…` | `01ca528d…` | ✅ |
| 同一 run 缺省 v1 公共 evaluate/score stdout | `b9a82c98…` | `b9a82c98…` | ✅ |
| direct17 直连接口 stdout | `988b9e26…` | `988b9e26…` | ✅ |
| true-default（真省略 vs 显式 v1）stdout | `16055b0a…` | `16055b0a…` | ✅ |

## 全量红绿

| 树 | 结果 | exit |
|---|---|---|
| parent（纯 HEAD，同环境同法） | **2121 passed / 0 failed / 16 deselected** | 0 |
| fixed（HEAD+本轮 3 文件） | **2125 passed / 0 failed / 16 deselected** | 0 |

## 如实登记的偏差与方法学说明

1. **双树各自生成 run 的哈希不等是方法学假象**：首轮我让两树各自生成合成 run
   再比对，导出 digest 不同——diff 定位为全部来自行内 `created_at` 时间戳与 tmp
   路径（终裁轮协议是"同一 run 双树评估"）。已按终裁协议重做：共享一次生成 +
   同库 build 差分，四对照全等；首轮原始输出保全于
   `v1_byte_identity/pytest_full_first_attempt_collection_errors.stdout` 旁的
   `v1_comparison_summary` 前身与 progress 记录。
2. **全量跑了两轮半**：隔离树首次全量 2 failed（batch_dev 两测）+ 16 skipped，
   纯 HEAD 同环境对照复现同 2+16 → 定位为隔离树缺同级 dependingv3/dependingv4
   根（skip 原因原文"v3 代码根不可用：/private/tmp/.../dependingv3"）；补 symlink
   后双树全绿如上。全部四份 stdout 保全（`*_before_v3link` 与终值）。
3. **store.py detail 键序**：event_id 从 detail 首位移至末尾（键集与取值不变）；
   三处消息文本 AST 级逐字一致（`store_refactor_equiv/`）。既有 R7/R8 测试全绿。
4. **自建杂物已清**：最初 `py_compile` 语法检查落了两枚 gitignored .pyc，已删。
5. **工作树里有并发 C 轮的进行中改动**（production.py / s5b_builder.py /
   s5b 系列测试 / prereg 文档）：本轮零触碰、零依赖；提交收口时请把两轮改动
   分开看（本轮 = 上表 3 文件）。
6. 语义拿不准点未遇到：哈希校验共用方式按"判据抽成 store 模块级单函数、四入口
   共用、消息原文保持"落地，未扩范围（未加孤儿 appearance 行的语义闭合检查——
   终判有限验收只要求形状/绑定/哈希三查）。

## 证据索引（docs/review_evidence/criteria_v2_p1fix2_2026-10-14/）

| 文件 | 内容 |
|---|---|
| `START_MARKER.md` / `progress.md` | 开工标记 + 全程阶段记录 |
| `prefix_repro_participant_appearance_output.json` | 修复前缺陷复现（终判探针原样复跑：两反例官方链全接纳+重放拒） |
| `p1fix2_participant_appearance_probe.py`（+`appearance_probe.py`） | 修复后验证探针（构造同终判、期望翻转；可复跑同构） |
| `postfix_participant_appearance_output.json` | 修复后全链输出（两反例拒绝原文+链截断+正控幂等） |
| `store_refactor_equiv/` | 单一验证源重构消息逐字 parity 检查脚本+输出 |
| `v1_byte_identity/` | 四组字节对照探针/脚本/输出（同库 build 差分 + 同 run v1/direct17/true-default） |
| `pytest_full_parent_tree.stdout` / `pytest_full_fixed_tree.stdout` | 全量终值 2121/0/16 与 2125/0/16 |
| `pytest_full_*_before_v3link.stdout` | 隔离树环境假象轮原始输出（2+16） |
| `SHA256SUMS.txt` | 本目录全部文件 SHA256 |
