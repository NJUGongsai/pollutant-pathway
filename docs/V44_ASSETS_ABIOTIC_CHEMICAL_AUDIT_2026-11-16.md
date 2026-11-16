# `v44` 路径预测在用资产「非生物 / 纯化学反应」只读筛查报告（2026-11-16）

- **执行环境**：32 核 HPC Slurm 节点（作业号 `49201715`，耗时 `65.62s`）+ 公开上游数据库（Rhea SPARQL / MetaNetX 4.5）在线交叉核验
- **脚本**：`scripts/eval/audit_abiotic_chemical_assets.py` / `scripts/hpc/sbatch_asset_abiotic_audit.sh`
- **原始产物**：`audit_summary.json`、`confirmed_abiotic_hits.jsonl`、`suspect_needs_upstream.jsonl`、`upstream_rhea_mnx_verification.json`、`eawag_high_suspect_for_envipath_lookup.jsonl`
- **资产完整性**：全程**只读**扫描，未修改任何 `assets/` 文件及 SHA256 清单锁

---

## 1. 一句话总结

1. **在 `v44`（`v44-next`）当前默认路径预测真正进候选池的 5 组资产（合计约 55.4 万条记录/模板）里，本地反应式直接写明了强非生物试剂的「实锤纯化学反应」一共只抓出 `8` 条命中（实质是 `EAWAG-SOIL` 同一条路径下的 `4` 个羟基自由基 `[OH]` 反应在 `library_full` 和 `corpus_v1` 中各存一份）**；**臭氧（`O3`）、过硫酸盐（`S2O8^2-`/`HSO5-`）、高锰酸盐（`MnO4-`）、铁酸盐（`FeO4^2-`）以及 Pd/Pt/Rh/Ru/Ir/Os 等纯化学合成催化剂在本轮均未检出（`0` 条）**。
2. **上游元数据回查抓出一批“本地无文字看不出来、但上游标为纯自发/非酶/UV 光照”的反应**：通过查询 Rhea 官方 SPARQL 与 MetaNetX 4.5 全库，在 `corpus_v1.jsonl`（37,100 条 Rhea）中进一步揪出 **`640` 条（`1.73%`）纯自发/非酶促反应（无 EC 号）**（其中含 **`20` 条显式 UV 光照反应**），以及对应派生进 `corpus_templates_v2.jsonl` 的 **`467` 条（`2.72%`）**、派生进 `rhea.json`（`S5-rr` Rhea）的 **`2,300` 条模板（`S5` 活跃半径 `2/4/6` 内占 `926` 条）**、派生进 `METANETX.json`（`S5-rr` MNX）的 **`1,866` 条模板（`S5` 活跃半径 `2/4/6` 内占 `766` 条）**。
3. **enviPath 隐式非生物盲区与待查包**：`library_full.jsonl` 中的 `EAWAG-SOIL / SEDIMENT / SLUDGE` 共 `3,452` 条记录本地**只存有机底物 → 有机产物 SMILES**，既未把 `O3`/`•OH`/`hv` 写进反应式，也无“光解/臭氧/高级氧化”文字标签；因 `envipath.org` 目前对未登录访问拦截为登录与人机验证，已将其中最可疑的 **`101` 条高优先级 UUID** 单独导出为 `eawag_high_suspect_for_envipath_lookup.jsonl`，待授权环境补查文字条件。
4. **真酶反应安全保住（零误杀）**：`H2O2` / `O2`（过氧化物酶与加氧酶共用）、`rhea` 中 `EC 1.16.3.3` 锰氧化酶的 `O=[Mn]=[O]`、`rhea:32820` 铬酸根膜转运（`CrO4^2- >> CrO4^2-`）与 `rhea:44369` 细菌铬酸还原酶，以及 `EAWAG-SOIL` 中有机锡杀螨剂自身降解（`Fenbutatin oxide >> CO2`）均已精准区分，未误判为纯化学反应。

---

## 2. 筛查范围与本地结构扫描总表

> 说明：默认未进入 `v44-next` 候选池的 USPTO 家族（`uspto_relaxed_index_v1.jsonl`、`retrorules/raw/USPTO.json`、`uspto_templates.json`）未纳入本轮扫描。

| 资产组 | 作用通道 | 扫描记录数 | 本地实锤明确非生物 (`CONFIRMED_ABIOTIC`) | 需回查上游高疑点 (`SUSPECT_NEEDS_UPSTREAM`) | 本地实锤占比 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `library_full.jsonl` | `recorded` 精确查表 | `4,454` | **`4`** | `3,454`（含 `3,452` 条无标准 `bt` 规则的 SOIL/SEDIMENT/SLUDGE） | `0.09%` |
| `corpus_v1.jsonl` | `corpus` 同底物直通 | `43,177`（Rhea `37,100` + enviPath `6,077`） | **`4`** | `561` | `0.009%` |
| `corpus_templates_v1.jsonl` / `v2.jsonl` | `analog` 模板类比 | `17,183` × 2 | **`0`** | 各 `5` | `0%` |
| `S5-env`（`envipath/templates_implicitH.jsonl` + `eawag/rules_new_clean.jsonl`） | `S5-env` 规则补池 | `286` + `49` | **`0`** | `0` | `0%` |
| `S5-rr`：`rhea_retro_index.meta.json` | `S5-rr` Rhea 规则 | `134,738`（`S5` 活跃半径 `2/4/6` 占 `47,872`） | **`0`** | `1,720`（`S5` 活跃半径内 `435`） | `0%` |
| `S5-rr`：`mnx_retro_index.meta.json` | `S5-rr` MetaNetX 规则 | `336,966`（`S5` 活跃半径 `2/4/6` 占 `122,455`） | **`0`** | `3,072`（`S5` 活跃半径内 `913`） | `0%` |

---

## 3. 本地实锤非生物反应明细（共 8 条记录 / 4 个独立反应）

全部 8 条实锤命中均来自 **`EAWAG-SOIL` 同一条吡唑酰胺类杀菌剂路径 `b11b1c77-1c0e-4b3a-86f4-a450f7941c9b`**（在 `library_full.jsonl` 和 `corpus_v1.jsonl` 各存 4 条），反应式里明确写入了 **羟基自由基 `[OH]`**：

| 序号 | 反应 ID | `library_full` 行号 | `corpus_v1` 行号 | 命中特征 | 反应式摘要 |
| :---: | :--- | :---: | :---: | :--- | :--- |
| 1 | `015bda2e-a78c-46a9-85ca-33a617698028` | `2490` | `39643` | 消耗 `[OH]` 自由基 | `...吡唑酰胺底物.[OH] >> ...吡唑甲酸` |
| 2 | `5768be02-5548-4680-8356-a02432b7c4d8` | `3141` | `40449` | 消耗 `[OH]` 自由基 | `...N-甲基吡唑酰胺.[OH] >> ...吡唑甲酰胺` |
| 3 | `c8550f07-7e1d-4701-b08a-eb3cc07052e5` | `4031` | `41565` | 生成 `[OH]` 自由基 | `...N-甲基吡唑酰胺 >> 同分子.[OH]` |
| 4 | `e3f963a6-ab70-4c5d-bf08-48c24fa723d6` | `4243` | `41840` | 生成 `[OH]` 自由基 | `...吡唑酰胺 >> 同分子.[OH]` |

> 注：同一路径 `b11b1c77-1c0e-4b3a-86f4-a450f7941c9b` 在 `library_full.jsonl` 中共有 `9` 条反应，其余 `5` 条未显式写 `[OH]`；极可能整条路径来自土壤光解/自由基文献。

---

## 4. 「需回查上游文本确认」的高疑点分层清单（本地统计）

### 4.1 高优先级小撮疑点（合计 101 条 EAWAG + 5 条 MNX）

| 资产 | 疑点类型 | 数量 | 典型代表 / 化学说明 |
| :--- | :--- | :---: | :--- |
| `library_full` / `corpus_v1` | **非 `bt` 规则且「脱卤 + 多步加氧（`ΔO>=2`）」** | `58` | 仅发生在 `EAWAG-SOIL/SEDIMENT/SLUDGE`，可能是土壤光解/高级氧化或多步合并记录 |
| `library_full` / `corpus_v1` | **净加氧 `ΔO=3` 或 `4`（`ΔC=0`）** | `26` | `multi_oxygenation_deltaO=3`（23）、`deltaO=4`（3），臭氧/AOP 氧化或跳步合并常见特征 |
| `library_full` / `corpus_v1` | **EAWAG 环境包里的有机自由基 SMILES** | `18` | 逐条抽看多为 enviPath 导出时缺氢写法瑕疵（如 `[N]`、`[C]`、`[O]` 少写 `H`），个别如 `SEDIMENT:12f4cf31` 值得顺手核对 |
| `library_full` / `corpus_v1` | **氯酸盐 / 亚氯酸盐无机转化** | `2`（镜像各 2） | `EAWAG-SOIL:eb5c80c9`（`ClO3-.Na+ >> ClO2-`）、`3b69b846`（`ClO2- >> Cl-`） |
| `corpus_v1` / `analog` | **过氧酸 / 有机过氧化物（`envipath` 缺 EC）** | `3` | `EAWAG-SOIL:65d3d2d5`（羧酸→过氧酸 `C(=O)O >> C(=O)OO`）、`EAWAG-SEDIMENT:542fc3a5`、`bt0077#r0684` |
| `library_full` / `corpus_v1` | **无机磷化锌 / 有机锡杀螨剂** | `2` | `EAWAG-SOIL:f0f3a6c2`（磷化锌 `P(=[Zn])[Zn]P=[Zn]>>[Zn-]`）；`EAWAG-SOIL:645cc434`（苯丁锡 `Fenbutatin oxide >> CO2`） |
| `retro_mnx` | **缺少 EC 的含氯氧化/亚硝酰氯水解模板** | `5`（`S5` 活跃半径内 `2`） | 均出自 `MNXR103688`（`O=NOCl + H2O <-> HNO2 + HOCl`） |

### 4.2 低优先级背景疑点（主要源于数据库缺少 EC 标注）

- **`library_full` 无 `bt` 规则元数据缺失（`3,452` 条）**：`EAWAG-SOIL`（`1,977`）、`EAWAG-SEDIMENT`（`931`）、`EAWAG-SLUDGE`（`544`）全量使用 UUID 作为 `btid`/`reac_id`，本地没有反应条件文本。
- **`retro_rhea`（`1,720` 条）与 `retro_mnx`（`3,067` 条）缺 EC 的有机过氧化物模板**：主要是脂质氢过氧化物 / 前列腺素内过氧化物等正常生物氧化脂类反应，仅缺少 EC 标注。
- **`corpus_v1` Rhea 缺 EC 自由基反应（`organic_radical_no_ec: 53`、`bio_known_radical_no_ec: 44`）**：经上游核查主要是抗坏血酸自由基、NO/N2O 等真实酶促反应缺失 EC 标签。

---

## 5. 上游元数据回查追加结论（Rhea SPARQL + MetaNetX 4.5 + enviPath）

### 5.1 Rhea 与 MetaNetX 上游已全量查清（100% 在线验证）

> 数据源：`https://sparql.rhea-db.org/sparql`（Rhea 官方 SPARQL）与 MetaNetX/MNXref 4.5 `reac_prop.tsv`（84,185 条）。

| 资产 | 上游实锤「纯自发 / 非酶促（无 EC）」 | 其中显式 UV 光照反应 | 上游实锤「跨膜转运反应（`isTransport`）」 |
| :--- | :--- | :--- | :--- |
| `corpus_v1.jsonl`（37,100 Rhea） | **`640` 条**（`1.73%`） | `20` 条（如 7-脱氢胆固醇/麦角固醇光照开环） | **`3,194` 条**（`8.61%`，如 `CrO4^2- >> CrO4^2-`） |
| `corpus_templates_v2.jsonl`（17,183） | **`467` 条**（`2.72%`） | — | — |
| `rhea.json` / `S5-rr` Rhea（134,738） | **`2,300` 条**（`S5` 活跃半径 `2/4/6` 内 **`926` 条**） | `154` 条（`S5` 内 `52` 条） | — |
| `METANETX.json` / `S5-rr` MNX（336,966） | **`1,866` 条**（`S5` 活跃半径 `2/4/6` 内 **`766` 条**） | `22` 条（`S5` 内 `6` 条） | **`1,089` 条** |

- **本地 721 个 Rhea 疑点 + 249 个 MNX 疑点复核结果**：
  - `249 / 249` 个疑点 `MNXR` 全部来自生信代谢库（`rh:118 / vmhR:51 / biggR:47 / metacycR:16 / seedR:14 / keggR:3`），**没有任何一条来自化学合成或 AOP 数据库**。
  - Rhea 721 个疑点中，绝大多数是缺 EC 标注的真酶（如脂质过氧化物还原、抗坏血酸酶、细菌铬酸还原酶 `RHEA:44369`、细菌锰氧化酶 `RHEA:52248`），但通过 Rhea `rdfs:comment` 顺藤摸瓜，**反查出了上述 `640` 条纯自发/非酶/UV 反应**（本地无文字时无法识别，例如 `RHEA:15666` 美拉德糖化、`RHEA:65977` UV 光照、`RHEA:30268` 自发自由基歧化、`RHEA:15650` 氨基甲酸自发分解）。

### 5.2 enviPath 上游核查边界与导出清单

- **受阻情况**：`https://envipath.org/package/...` 与 `https://envipath.org/api/legacy/package` 目前对未登录访问拦截为 Sign-In + `@cap.js` 人机验证（`/api/legacy/package` 返回 `{"detail": "Unauthorized"}`），遵循安全规范不绕过登录或人机验证，因此该批 UUID 的包内文字条件暂未在线拉取。
- **已就绪待查包**：已将最可疑的 **`101` 条 EAWAG 高疑点**单独抽成 `eawag_high_suspect_for_envipath_lookup.jsonl`，后续在已登录账号环境下仅回查这 101 条即可收口。

---

## 6. 下一步可选动作（未改动任何资产）

1. **高确定性过滤清单已具备**：如后续在 `v44` 运行时（不改 `assets/` SHA256）加一道「非生物 / 非酶过滤」开关，可直接覆盖三块：
   - `EAWAG-SOIL` 的 `4` 条 `[OH]` 自由基反应（含同路径共 `9` 条）；
   - Rhea/MNX 上游实锤的 **`640` 条 `corpus_v1` 纯自发/UV/非酶反应**（以及对应 `467` 条类比模板、`926` + `766` 条 `S5-rr` 纯自发模板）；
   - `corpus_v1` 中的 `3,194` 条 `isTransport=true` 跨膜转运空反应。
2. **enviPath 101 条补充核查**：在已登录 enviPath 的环境对 `101` 条高疑点 `reac_id` 核对包内反应描述字段，即可完成最后一环闭环。
