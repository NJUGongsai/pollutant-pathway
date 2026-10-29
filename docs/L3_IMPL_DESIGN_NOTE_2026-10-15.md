# L3 声明面下放实施 — Phase A 设计书（2026-10-15）

> 任务书 `docs/TASK_L3_IMPL_2026-10-15.md`。题域标签 **298=RHEA 通用酶学/已见题**；**探针≠预注册≠成绩**；零金标零题面零模型零网络。证据：`reports/ppv1_s5b/l3_impl_2026-10-15/l3_face_estimate.{py,json}`。

## 一、结论先行：**前提失效，按任务书 §八停并回报，不进 Phase B**
前提「普通门 compiled ∧ 底层记录已声明共底物」约 55 题 —— **实测该集合为空（0 行 / 0 题）**。锁3「普通门 spec 无声明面」在当前实现里不成立：凡是底层记录真声明了反应物侧共底物的 compiled spec，**已全部在既有声明面路径上**。本轮未改任何 `src/` 代码、未跑 Phase B/C、未 commit。

## 二、入口枚举（`src` 全扫，5 个 spec 构建入口，无遗漏）
| # | 入口 | 通道 | 已发射声明面 | L3 适用 | 实测可声明面 |
|---|---|---|---|---|---|
| 1 | `s5b_builder.py:1173` analog 普通门 | analog | 否 | 是 | **0** |
| 2 | `s5b_builder.py:1111` analog C 线救援 | analog | **是**(:1127) | 否（已覆盖） | 24 行 |
| 3 | `recorded_source.py:1519` corpus D2 split | corpus | **是**(:1630) | 否（已覆盖） | 22 行 |
| 4 | `recorded_source.py:1708` corpus whole-string | corpus | 否 | 是 | **0** |
| 5 | `recorded_source.py:1251` recorded EAWAG | recorded | 否 | 是 | **0** |

**同一判据实现**：三条无声明面入口共用 `corpus_v1`/`library_full` 同源 resolve + §三 判据（禁各写各的）；两条已覆盖入口复用其**既有** attach helper，不重写。**三个「0」是按构造不可能（非未实现）**：

- **入口 1**——`compile_donor_template` 只在模板袋**单组分**时过前置门并编译。真实 run 69 条 analog compiled 行的（模板袋组分数, 记录 donor 组分数）交叉表 = `{1:1→43, 2:2→22, 3:3→4}`，**`bag=1 ∧ donor≥2` = 0 行** ⇒ 普通门按构造无可声明共底物。
- **入口 4**——代码自载不变式：`component+co_comps` 候选由 D2 三分支守门处理完毕、**不可达** whole 路径，「whole-string compiled specs carry **empty** co-substrate declaration」。
- **入口 5**——tier=strict 要求 `donor_strict == 底物严格身份`，tier=cn 要求 `donor CN == 底物 CN` ⇒ **donor 即底物**，无反应物侧额外组分。

## 三、精确资格判据（可断言伪码，替代探针族级代理）
```
qualified(spec) := spec 经普通门 compiled（不在 analog 救援 / corpus D2 声明面路径上）
  AND record := resolve(spec.record_key)                     # corpus_v1/library 同源
  AND cn_identity(substrate) ∈ {cn_identity(d) for d in record.反应物侧组分}
  AND extras := {d ∈ record.反应物侧组分 : cn_identity(d) ≠ cn_identity(substrate)}
  AND extras ≠ ∅  AND  ∀e∈extras: cn_identity(e) 成功  AND  primary_family ∈ FAM
```
- **额外组分界定**：对齐/多重集差——按 `cn_identity` 严格身份做集合差；底物**必须本身是记录反应物侧某组分**，否则该记录与本底物非对齐、判据不适用。
- **族界**：需要但**只作收窄闸、不引新化学规则**（判据本体=声明存在性）。复用 `FAMILY_PRIORITY` 去 其它/unknown 的 10 族，挡 ATP/NAD/FAD 等大辅因子面，避免把「记录顺带声明的能量载体」误当共底物供给面。

## 四、实测面数与锚偏差（**停的理由**）
真实 chain13 run 全部 **207 条 compiled 行**逐行跑 §三 判据：

| 分类 | analog | corpus | recorded |
|---|---:|---:|---:|
| A 反应物侧有额外组分 | 24 | 22 | 0 |
| └ 其中已在既有声明面（C 线救援 / D2） | 24 | 22 | 0 |
| └ **其中普通门（真 L3 候选）** | **0** | **0** | **0** |
| C 底物已对齐但无额外组分（无可声明） | 11 | 12 | 104 |
| D 底物未出现在记录反应物侧（非对齐记录） | 34 | 0 | 0 |

**真 L3 候选 = 0 行 / 0 题；锚（≤55 题并尽量贴近）偏差 = −55。** **锚为何虚高**：探针口径 B（55 题/60 行）= A 46（**已在既有声明面**）+ C 23（无可声明）+ D 中非对齐行；且探针族扫描是**方向无关的供体∪产物并集**（探针自载口径），例 `rhea:14570` donor=`['CC(O)CO']`（单组分）、product=`['CCC=O','O']` —— 水在**产物侧**却被计成「已声明共底物」。**探针口径 B ≠ L3 目标集。**

## 五、发射字段清单（前提修复后重启时按此实现）
与 C 线同源：`participants`/`participant_list_status`/`co_substrate_states`/`declared_copy_components`/`cosubstrate_event_contract`/`record_equation`+`_ref`。**`execution_input_smiles` 不适用于普通门**：普通门 edits 只对底物编译，执行输入=底物本身；发 `底物⊕B` 是虚假执行声明，发 `底物` 则与声明供给多重集不等而触发 `_verify_execution_input` 结构化拒 —— 故**不发此键**（run 期键控，不发=不触发核验，合法——任务书 §四.3 已预判）。`pool-policy-7→8` 的理由在当前结论下不成立（无可升版的行为面），待前提修复后再登记并同步 T11 受控词。

## 六、请 CC 拍板的三条出路
1. **口径放宽到产物侧**：普通门 spec 的记录常在**产物侧**多出组分（水等）。可复用既有 `declared_copy_components`（`execution_status=declared_not_executed`）声明为「记录声明未执行」拷贝组分，NC-10 轴2 满足、NC-9 不破 —— **但这不是任务书所写的判据，属改口径。**
2. **锁1/锁2 转向**：锁3 已闭，真正没解锁的是锁1（前置门资格）、锁2（救援件编不过），建议按 P1/P2 重新立项。
3. **换受益面**：若目标是扩大 v2 豁免受益面，可评估 corpus D2 / C 线**已发射声明面但事件仍 partial** 的 spec（判分侧零改动前提下属另一杠杆，需重新预注册）。

## 七、CC 拍板记录（2026-10-15，结论已冻结）

| 事项 | 拍板 | 后果 |
|---|---|---|
| 判据口径 | **维持「反应物侧额外组分」**，不放宽到产物侧 | 本任务**无代码可写**；产物侧口径作为**备选路线留档**，不实施 |
| 下轮方向 | **转向锁1/锁2**（前置门资格 / 救援件编译） | 下一轮按 R0 探针 P1/P2 底数（族合格 186/93 件、覆盖 12/13 题）重新立项 |
| 本任务收尾 | **按现状结项** | 零 `src/` 改动、不 commit、工作树干净；Phase A 设计书 + 面数证据为本任务全部交付 |

**冻结声明**：锁3「普通门 spec 无声明面」经实测判定为**已关闭**（面 = 0 行 / 0 题，锚偏差 −55）；
后续任何以「普通门存在未声明共底物面」为前提的方案，**须先重跑本文件所附面数实测证伪**，
不得直接沿用预注册/探针的族级代理数字。