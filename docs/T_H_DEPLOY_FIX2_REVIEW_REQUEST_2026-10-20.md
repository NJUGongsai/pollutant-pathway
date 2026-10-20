# 复核请求 — T-H 部署轮两处 delta（2026-10-20，CC 亲验或代审）

> 请求类型：**发车面 delta 复核**（两处修复均 postdate 三单复审的文件锁定，属发车面前置件；
> 沿 P3-IDENT「T-H 门确认」先例——由 CC/指定评审确认后随 T-H 发车）。
> 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；零金标。
> 工作树：未提交（HEAD `abbfa39`）；三单已提交内容不受影响，本请求只覆盖下述两处 delta。
> 工作树另有一处与本 delta 无关的未提交改动：`docs/HANDOFF_P01_REJUDGE_2026-10-18.md`
> （2026-10-19 终态状态刷新，纯文档改动），不在本请求评审范围。

## delta-1：v3 transforms 指纹平台化（`evaluation.py`；已在 HPC 生效验证）

- **事实**：HPC 发车冒烟时发现 v3 判据注册表 `available=False / transforms_fingerprint_unavailable`——
  原实现只查 macOS 布局（`pkg/.dylibs/libRDKitMolStandardize.1.dylib`），Linux（conda/pip）取不到
  ⇒ v3 判据被 fail-closed 关闭（T-H 预注册含「V3 档 A 披露块随批输出」，缺失即缺口）。
- **修复**：候选路径平台化——macOS 原路径（首选项，mac 行为逐字节不变）+ `$prefix/lib` +
  `purelib`/`rdkit.libs` + conda 锚（`pkg.parents[2]`/`[3]/lib`）依次 glob；**environment 字段集未增删**
  （刻意不加 path 键——environment 进四臂指纹，新键会改写指纹并破坏前置 1/评审锚）。
  找不到仍 fail-closed（`transforms_fingerprint_unavailable`，语义保留）。
- **验证**：本地 35 测（v3+v2 套件）全绿且**四臂指纹与常量逐字同**（`fa4c6a42…/56e41340…/
  b059fe22…/7e88e613…`）；HPC 实测 `available=True`、四臂指纹可算、`resolve v3` 通过
  （lib sha `06cbe785…` = `anaconda3/envs/rxn/lib/libRDKitMolStandardize.so.1`）。
- **sha**：`evaluation.py` 已审锁定 `a7e5ecfd…` → 本 delta 后 `37c09231…`（diff：+31/−2，numstat 口径）。
  附注：候选命中路径记入局部变量 `dylib_path` 但未被消费（诊断用死变量，无指纹/行为影响）。
- **评审要点**：候选顺序/回退语义（mac 首选、Linux 兜底、全失败仍 fail-closed）；
  environment 零增删的指纹保护是否认同；`sys.prefix` 在 venv/conda 组合下的兜底覆盖。

## delta-2：产物侧身份自洽门（`s5b_compiler.py`；s5b-compiler-5→6）

- **事实（T-H 冒烟事故）**：D1.2 补映射使产物侧含**游离退化片段**（如 `[N+]`，RDKit 产出裸
  `|0|` 未登记 CX 块）的记录首次编译入池；worker 的 decide 段在模型调用前对**全部池 spec**
  构建产物态，chemstate 身份守卫 fail-closed ⇒ **整题 0 调用失败**。全批实测面：**21/298 题**
  （21 件 spec，100% remap-applied；每题 1 件）。
- **修复（CC 拍板 A=编译层自洽门）**：`compile_donor_template` **包装层**（`_compile_donor_template_impl`
  内判据零改动，沿 D1.2 tnc gate 同模式）在 compiled 后对 `product_smiles`+全部 `coproducts`
  逐一跑 `build_chemical_state`（origin=`source_product`，**判据单一来源**）；任一组分不可表示 ⇒
  结构化拒 `product_component_identity_invalid`（detail 带 `invalid_components[{component, kind, error}]`）。
  不引入化学判断：只要求「编译器产物必可被管线消费」自洽。
- **版本**：`S5B_COMPILER_VERSION` 5→**6** + 新常量 `S5B_PRODUCT_IDENTITY_GATE_VERSION="product-identity-gate-1"`;
  5 处断言同步（v4b/w1/pool_lineage/template_remap×2）。**pool policy 不升**（R1 compiler-3 先例：
  compiler-only 变化只升 compiler）。
- **验证**：定向 69 测全绿（新文件 `tests/test_ppv1_s5b_product_identity_gate.py` 6 测：
  helper 退化/干净/产物面 + 合成退化模板集成拒 + 干净模板正控编译 + 版本）；
  **对真面分判**：全批 550 spec 过门 ⇒ 恰 21 件拒（= face_v2 的 21 题逐题吻合）、529 件过（零误伤）；
  被拒 21 件 100% remap-applied；池效应：14 题余池、7 题池清空（→novel-only，与 chain14 同形态）
  ——分判读数来自实施会话扫描，**扫描脚本/产物未落盘存档**；复核侧重放 = 对批重建面
  550 spec 逐件调 `_product_components_identity_problem` 计数（`s5b_compiler.py` 内 helper，
  判据单一来源同源），发车后以 HPC 批根复测为准（任务书 §3 步 5）；
  全量 not-slow：**2299 passed / 0 failed / 16 deselected**（基线 2293+6 新测，零翻转）。
- **sha**：`s5b_compiler.py` 已审锁定 `4cf61a8a…` → 本 delta 后 `f917762b…`（diff：+71/−1，numstat 口径）。
- **评审要点**：门判据只依赖 chemstate 构建（无新化学判据）；包装层放置与 `_impl` 零改动；
  拒因分类（`product_component_identity_invalid` 新拒因）与披露（含 remap 路径同形披露）；
  分判零误伤（529 过）与池效应披露（14/7）。

## 附带（同批发车面，已由 CC 亲验过，供复核确认）

- P3-IDENT/P3-LABEL delta（`616dad8` 已提交）：批级 `compiler_version` 键+注记动态化——本次
  compiler-6 后批级键将自动随值更新（设计如此）。

## 复核输出

`docs/T_H_DEPLOY_FIX2_REVIEW_2026-10-20.md`：两 delta 逐项判定（放行/需修正），
含 sha 复验、HPC 侧实测复现建议（ssh 命令：`venv_v44run/bin/python` 跑注册表/门扫描）。

**纪律**：只读复核；不动 src/tests；HPC 侧只读。