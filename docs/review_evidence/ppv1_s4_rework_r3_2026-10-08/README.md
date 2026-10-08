# S4 回修 r3(PPV1-ISO-01)实施证据

实施代理一次性证据包。开工/直接父 HEAD
`2ff919fa6ef127d4a477b1b1bb52beb685365a9d`;修复 = 方案 A(冻结判据
五 §5 现义兑现:isotope diff 并入实际净变化/changed atoms/属性披露/
公开重算)。所有执行在 fresh /private/tmp 副本,旧永久证据(含评审
R3 `ppv1_s4_codex_r3_2026-10-08/`)只读零触碰。不访问金标/题面/
封存逐题 run/dependingv4/原 v3 评价资产;判分零 LLM;不调用外部
模型;不 push。

## 结论

- **混合中心外同位素反例(评审 R3 §4.2 核心案)不再过度授信**:
  诊断 center True→**False**、audit 中心 verified→**violated**、
  准入 R6→**R5v retain_conditional**;探针层不提交;production caller
  按已登记 retain 策略提交但轴结论如实 violated/R5v(事件
  `ppev_0819a581aaf3ab0e7c91` 与评审同 ID,内容由 expand/R6 变为
  retain/R5v)。**不再 verified/full/R6。**
- 纯同位素案走真实轴(center False,extra_changes isotope 0→13),
  不再误标"仅立体";非四面体 stereo-only 控制仍走立体码+公开
  unsupported 清单。
- 正常控制全部保持:正常键变/原 13C 保持/中心内 isotope/全中心
  范围控制仍 verified/R6(事件 ID 与评审逐字相同);strict False→
  violated 保持;带标签结构不一概拒绝。

## 数字(合成规则级工程回归;不外推 dev/298;工程数不是漏洞数)

| 验证 | 结果 | 出处 |
| --- | --- | --- |
| PPV1 全量(仓内树) | 976 passed / 0 skipped,exit 0(36+1 文件) | logs/ppv1/(JUnit+stdout/stderr) |
| 父 2ff919f 同字节 | 15 failed / 961 passed,**0 collection 红**;5 行为+2 字段+8 版本 | logs/parent_redgreen/ + redgreen/baseline_classification.json |
| 8 分案复现 | 8/8 完成无异常;混合中心外 violated/R5v/不提交 | results/ + logs/isotope_probe/ |
| 3 production caller | 3/3 完成无异常;混合案 retain/R5v/violated,两正控 expand/R6 | production_results/ + logs/production_probe/ |
| G01 安全隔离 | **1578 passed / 8 skipped / 17 deselected,exit 0**(1564+14);297 输入前后 SHA-256 全同 | g01/ |
| 确定性 | 8 分案与 3 caller 正式复跑 summary.json 与首跑**逐字节相同** | logs/*/ + commands.json |

父基线构造:`git archive 2ff919f` 解包至 fresh tmp,7 个本批触改
测试文件以仓内工作树同字节覆入(逐文件 SHA 相等,见 redgreen/
same_byte_sha256.json)。红绿分类逐用例(首失败行+basis)见
redgreen/baseline_classification.json;首失败以后的断言不报已验证。

## 目录

- commands.json:实际命令/退出码/env/执行脚本 SHA/边界声明。
- logs/:ppv1(仓内全量)、parent_redgreen(父同字节)、isotope_
  probe、production_probe(完整 stdout+stderr+EXIT 行);JUnit 两份。
- results/:8 分案完整输入、proof、诊断/audit/admission/事件/
  重放/17 表前后(逐案 JSON);summary.json。
- production_results/:3 案生产完整输入、工具原输出与合成输出
  (controlled_tool_calls 内 actual_atomtool_result vs consumer_
  result)、全表、生产报告、artifact JSON;summary.json。
- controlled_result_diff.json:工具 raw vs 消费返回确定性 JSON
  diff —— 混合案仅 product_smiles/product_mapped_smiles 变,两正控
  零差异。
- before_after_comparison.json:对评审 R3 isotope_contract 逐案
  改前/改后(诊断 center/audit 中心/admission/提交布尔)。
- g01/:preparation.json(白名单谱系+297 输入含本批新增
  tests/test_ppv1_s4_rework_r3.py;触改文件当前字节新鲜 SHA)、
  input_sha256.json/after、g01_sha_verification.json(297/297 不变)、
  execution_result.json(命令/exit/229.8s)、JUnit、stdout/stderr。
- redgreen/:baseline_classification.json + same_byte_sha256.json。
- source_snapshot.json:9 个触改/新增文件 SHA+父字节比较;
  production.py/store.py/native_export.py/v3_projection.py/
  endpoint.py/atom_tool.py/冻结正文/冻结记录 8 文件**与父逐字节
  相同**(不改 legacy/G2/AtomTool、判据冻结零触碰的证明)。
- sqlite_inventory.json:7 个临时库 SHA/schema/计数(二进制不入
  包;逐案全表内容已在 JSON)。
- scripts/:probe.py、production_probe.py(评审 R3 原件逐字复制)、
  safe_g01_r3.py(评审 safe_g01_supplied.py 谱系副本,仅登记本批
  r3 新输入/预期数,白名单边界不变)。
- manifest.json + SHA256SUMS:覆盖本包全部附件 48 件(含 production_
  results 内嵌业务 artifact JSON;根 manifest.json/SHA256SUMS/
  manifest.sha256 三个控制文件自排除)。注:production_results/
  <案>/runs/ 下 6 个嵌套业务 artifact JSON 因仓级 .gitignore `runs/`
  规则以显式路径强制登记(证据交付意图明确;其全文同时收录于各案
  JSON 的 artifact_json_text)。

## 复现

不可在永久目录原地执行。复制 scripts/ 至新 tmp;探针用隔离源码
副本(`PYTHONPATH=<隔离>/src`,当前 HEAD 同源树 + 本批修复);
probe.py/production_probe.py 唯一参数为新结果目录(必须不存在,
mkdir exist_ok=False);safe_g01_r3.py 参数 --repo/--out/--python,
out 必须为 fresh 目录。禁 pyc(`-B` + PYTHONDONTWRITEBYTECODE=1)、
pytest no:cacheprovider。G01 白名单沿 R7→s3a_r4→s3b r1/r2/r3→
s4a_r1→s4b_r1→s4_rework_r1/r2→r3 谱系;8 skip 逐项与 17 deselect
nodeid 与评审 R3 相同(v4 对照根 1、v2 provenance/summary 2、冻结
v3 真实评价依赖 5;16 slow+1 charge/evaluation fixture);缺席不是
通过。本包数字与仓内树非隔离数字不混计。

## 诚实边界

- 不宣称原 AtomTool 会编辑同位素(冻结 v43-editproto-2 无该 op;
  13C 是合成工具返回 —— patch 只改 execute_edits 输出通道,内部先
  真实执行);不认证实验/机制/同位素计量/科学性能。
- self_contained_recompute 证明自包含输入集重算自洽,不证明
  "编辑曾被执行"。
- network:未调用网络工具;脚本未仪器化 socket 计数(沿评审 R3
  口径如实披露,不引用为 socket=0 实测)。
- production retain_conditional 仍按 S3b 起已登记策略提交事件;
  本批不改动该策略。
