# T-H 冒烟事故档案 + 修复记录（2026-10-20 凌晨，主窗口自记）

> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；探针 ≠ 预注册 ≠ 成绩。
> 性质：**发车冒烟期事故**（正式满批未开始、无数据消费）——诊断、停批、修复、验证全程
> 机读在案；修复（compiler-6 身份自洽门）**待 CC 复核**（请求稿
> `docs/T_H_DEPLOY_FIX2_REVIEW_REQUEST_2026-10-20.md`）。
> 费用：事故全程 **10 次模型请求**（smoke 期即停）；旧批根原封留档。

## 1. 时间线（HPC 作业号实录）

| 步 | 作业/动作 | 结果 |
|---|---|---|
| netcheck | 46930509 | **PASS**（venv python 3.11.15 / rdkit 2026.03.5 / flock / dashscope 出口全过） |
| build | 46930529 | **PASS**（~66 分钟；298/298；build_identity.json 在位；policy-9/compiler-5/formnorm 键全在；P2 面探针 261/222/96 落批根） |
| run 第一次 | 46936622 | 快速失败：`budget_no_cap.json` 缺 `budget_mode` 字段（fail-closed，零花费） |
| run 第二次 | 46937422 | smoke2→smoke10 推进中抓到 **CX 身份守卫杀题**（见 §2）⇒ **scancel 主动停批**；终态 6 件（5 completed + 1 failed-CX），10 次请求 |

## 2. 事故机理（全链机读可复现）

1. **现象**：smoke2 的 `RXNG_103c8400…` 在 **0 模型调用**下失败：
   `unregistered_cx_class: CX 扩展段含未登记旗标块:'0'`。
2. **本地复现**（同错误、本地 rdkit 2026.03.6 亦触发 ⇒ 非引擎差）：栈=
   `runflow._run_decide → production.prepare_hypothesis → build_product_state →
   chemstate.build_chemical_state → _identity_key → _guard_registered_cx_classes`。
   **decide 段在模型调用前对全部池 spec 构建产物态**——任一 spec 产物组分身份不可表示 ⇒ 整题死。
3. **根因**：D1.2 补映射（compiler-5）使产物侧含**游离退化片段**的记录首次编译入池。
   实测：`[N+]` 游离片段经 `MolToCXSmiles` 产出**裸 `|0|` 未登记 CX 块** ⇒ 守卫拒；
   `[O-]` → `|^1:0|`（**登记**注记类，放行——所以带 `[O-]` 的题不死）。
4. **波及面（真守卫精确扫描，批根 `degenerate_fragment_face_v2.json`）**：**21/298 题**
   （21 件 spec、100% remap-applied、每题 1 件）；chain14 同题池为**空**（旧编译器下这些模板
   死于 transform_no_change 未入池）⇒ 旧批无此病，纯新变量暴露。

## 3. 停批决定

21 题=7% 假 miss 会淹没 T-H 的判定线（35–40% vs 基线差只有几个点）⇒ 按「批次失去回答力」
主动 scancel；已花仅 10 次请求；「一批跑完」纪律未破（修复发生在正式满批前）。

## 4. 修复（CC 拍板 A=编译层自洽门；待复核）

- **实现**：`compile_donor_template` **包装层** gate（`_compile_donor_template_impl` 判据零改动）：
  compiled 后对 `product_smiles`+全部 `coproducts` 逐一 `build_chemical_state`（origin=
  `source_product`，**判据单一来源=chemstate**）；任一组分不可表示 ⇒ 结构化拒
  `product_component_identity_invalid`（detail 带 `invalid_components[{component,kind,error}]`；
  remap 路径同形披露）。不引入化学判断。
- **版本**：`S5B_COMPILER_VERSION` 5→**6**；新常量 `S5B_PRODUCT_IDENTITY_GATE_VERSION=
  "product-identity-gate-1"`；pool policy 不升（R1 compiler-3 先例）；5 处断言同步。
- **sha**：`s5b_compiler.py` 已审锁定 `4cf61a8a…` → 修复后 `f917762b…`（+72 行）；
  同批还有另一处部署 delta：`evaluation.py` v3 transforms 指纹平台化（`a7e5ecfd…`→`37c09231…`，
  HPC v3 判据已实测 `available=True`）——两处一并送复核（同一请求稿）。
- **验证**：新测试文件 `tests/test_ppv1_s5b_product_identity_gate.py` 6 测；定向 69 全绿；
  **对真面分判：550 spec 恰 21 拒（逐题吻合）/ 529 过（零误伤）**；池效应=14 题余池+7 题
  池清空（→novel-only，chain14 同形态）；全量 not-slow **2299/0/16**（基线 2293+6，零翻转）。

## 5. 复核与重启

- **复核**：`docs/T_H_DEPLOY_FIX2_REVIEW_REQUEST_2026-10-20.md`（两 delta 打包；CC 亲验或转代审；
  放行落 `docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md`）。
- **重启**：见放行 ⇒ 按移交书 `docs/HANDOFF_T_H_RELAUNCH_2026-10-20.md` 续跑
  （提交 delta → 重部署 → 重建批根 **r2** → 批准件/探针 → run → score → 对账）。
- **登记项**：本事故面=「机器可表示性」层（与 P2-CHEM-FORWARD「化学来源」层不同层）；
  21 件被拒 spec 的 P2 面占比变化（222→201 含新增原子）随 r2 批根探针复测披露。