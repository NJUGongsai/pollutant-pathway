# R8 独立存储专项复审

2026-10-07。实际仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`；HEAD
`00e509a974b40a7c9779fcd35e53b16637a13d60`；父提交
`858dd94c7c6c8fc387940242403d67b6b36b5313`。Python 为 depending43；
具体 Python/RDKit/schema 与全源码 SHA 见 metadata.json。

**裁定：R7-02 最低验收关闭，本存储专项无剩余 P1。R6-04 原反例与已关闭 R6-05 保持关闭。**
put_state 幂等入口没有复算既存同 hash 行是实际边界，如交付 §8.4 登记；本轮只登记为非阻塞
完善项，不能把 put_state 的 None 返回解释成账本出现记录已通过验证。

## 1. 固定验收与执行纪律

只验 R7 主审 §4 R7-02、§7、§8 的有限首提范围，以及旧 R6-04/05 回退。
读本仓 AGENTS、R7 报告、R6 原最低验收、R8 交付/源码差异/新存储测试和 mimo v8
读码意见。没有添加新机制、真实性认证、完整库抗一致重造或无关功能门。

源码（含 vendor）与 pyproject.toml 复制到新 tmp；所有探针也先复制，DB 均在 tmp
中由合成分子新建。`PYTHONDONTWRITEBYTECODE=1`、Python `-B`；没有 pytest 缓存。
没有改 src/tests/AGENTS/既有 docs、没有在旧证据内执行、没有访问真实金标/题面/封存 run、
没有外部模型或 push，没有读取或修改 dependingv4。

## 2. 旧公共链独立复跑

R7 永久证据 `storage_current/storage_contract_probe.py` 原样复制、用当前完整源码执行。
实际 **15 个 case + 1 metadata，exit 0**，stderr 空。新版观察断言另写
`assert_storage_r8_observed.py`，按修后期望检查全部 15 case，exit 0。
旧钉住 R7 缺口的断言不被当作修后通过线。

| 固定案例 | 当前行为 |
| --- | --- |
| 损坏产物 appearance.source_refs，hash 不动，供给 none / prod_only / all | 三条首提均 Ppv1LedgerCorrupt、appearance_hash_corrupt；counts 完全不变，event/projection/plan/links 零新增 |
| 对应无损坏 none / prod_only / all | 首提 created=True；无输入重放 created=False、零写入 |
| 无 supplied 状态，既存 CN / schema / innerID 损坏 | 原 state_row_corrupt / state_schema_corrupt / state_inner_id_corrupt 零写入拒保持 |
| 同图来源 A/B，正常/manifest 反序 | 三项 distinct occurrence 绑定保持；重放 created=False |
| 只删 A manifest / 连 A row 一并删 / 只删 A link | event_appearance_manifest_link_corrupt，零写入 |
| 只删 A row，manifest 保持 | event_appearance_manifest_entry_missing，零写入 |

这证明两个 supplied 首提反例确实翻转，合法与来源集合控制保持，不能用进程 exit 0
替代逐案结果。源 schema 升位产生 appearance/event hash 变化，不将历史 hash 字面当作
当前身份；判断按内容与行为轴，而不是要求不同版本结果逐字相同。

## 3. 独立扩展公共矩阵（同一规则适用入口）

`storage_r8_public_matrix.py` 新鲜合成公开 put/submit/replay 链，**17 case + metadata +
结尾断言，共 19 JSONL，exit 0**，stderr 空：

- 底物同 hash appearance 损坏，在 none/sub_only/prod_only/all 四供给路径首提：
  appearance_hash_corrupt、零新增。避免只修原产物例。
- 产物 semantic CN/schema/innerID 损坏，在 prod_only/all 六条供给路径：
  保持 Ppv1EventConflict/state_semantic_conflict、零新增；按既定要求不为改错误类型返工。
- 合法无先存/只先存底物/只先存产物/全先存四条：提供缺席载荷首提成功、无输入重放幂等，
  反序重给全部 payload 重放也幂等。旧 15 case 已独立覆盖多来源/manifest 排序。
- put_state 相同有效 payload 对 source_refs-only/hash 不动、raw 跨分子/hash 不动两种已存
  appearance 损坏，及 clean 同 hash 幂等正控：详见下一节。

初次自写脚本误把 `get_state` 的 `appearances` envelope 顶层键直接交给
`ChemicalState.from_dict`，触发 TypeError；这不是源码回归。前 14 case 已执行，后 3 未完成，
不能算首次 17 全过。已按 get_state 文档取首出现镜像、去 envelope 键，再完整重跑 17 case；
前一轮的完整 stdout/stderr/returncode 保留 `initial_envelope_fixture_error_*`，不隐藏错误。

## 4. put_state 幂等边界的有限裁定

位置：store.py:673–724 公共 put_state；:715–720 的 INSERT OR IGNORE 没有对同
(SID,hash) 的旧 payload 再复算。source_refs-only 与 raw 跨分子两例均执行级确认：

1. public put 建合法两状态，合成 SQL 只改产物出现行一个字段、hash 不动。
2. public put_state 再给原有效产物 payload 返回 None，counts 不变、坏 payload 原样留存。
   因此交付 §8.4 如实；**该返回不证明既存出现行完好，也没有自行修库。**
3. get_state 只是读回语义+appearances/首出现镜像。source_refs-only 镜像可恢复为
   ChemicalState，是对象内部结构契约自洽，不是来源真伪或 ledger hash 的认证；
   raw 跨分子镜像经 from_dict 立即 raw_identity_mismatch 拒。
4. 继续 public submit_event 显式重给有效产物，当前共用收集校验马上
   appearance_hash_corrupt / Ppv1LedgerCorrupt，counts 不变、无 event；没有损坏行被事件
   manifest/plan 作为可信引用落账。clean 同 hash put 则幂等且合法首提/重放通过。

R6-04 和 R7-02 的明确最低验收均是**首提实际引用/复用权威记录**，不是所有读写 API 的
无条件全账本检查。这里没有坏出现获事件准入、verified/R6 或扩展计划的具体公共证据；
不能只因一个幂等函数未加同形检查就追加 P1。该边界为后续 API 完善项，S3 消费方仍必须
走账本绑定/submit 校验，不能把 put_state 无异常当作 hash 完好证明；这不是新增阶段门。

## 5. 实现与新增回归有效性

store.py:1013–1054 的 `_collect_state_writes` 在数据收集阶段（事务提交之前）对每个
supplied payload 先核自身版本/事实与既存 semantic，再计算本次 appearance_hash，精确读取
已存同 (SID,hash) 行，content_hash(json.loads(payload)) 不等则 LedgerCorrupt。首提/带载荷
重放共用该函数；supplied 不再凭输入有效豁免实际复用旧行。

无 supplied 的 `reuse_refs` 路径仍走已有 `_verify_stored_state_rows` +
`_verify_stored_appearances`；多来源完整集合与 links 校验没被删改。
R8 9 个新存储 pytest case 使用公开提交结果、counts 和错误 kind 检查；两 P1 基线红点
为 prod_only/all 的错误接受行为，不是缺字段/缺表。其合法、语义冲突、无输入及 supplied
重放控制有效；本专项未重复跑全 pytest 或基线 28（由其它独立专项负责），不重复计数。

## 6. 证据与复跑

命令的精确 argv/cwd/returncode 见 `*.run.json`；输入源码 SHA、版本见 metadata.json；
完整输入由已冻结脚本中的规则级 fixture、公开调用参数和 JSONL 记录共同定义。
SHA256SUMS 对本纯脚本/日志包内容校验。永久目录不要原地执行；复制三个 .py 到新 tmp，
给 argv[1] 一个当前完整源码/vendor/pyproject.toml 隔离副本，再执行两个探针与观察断言。
DB 不进入永久证据，本包没有源码快照、真实评价数据或 SQLite。
