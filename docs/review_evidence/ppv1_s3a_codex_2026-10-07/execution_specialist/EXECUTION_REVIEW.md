# S3a 工程执行专项结论

范围：任务书§2.3 S3a、§3继承、§9安全G01和红绿；仅工程执行及legacy共享文案身份影响。本报告不能代替其他专项对预算/首次消费/恢复完整性的反例审核。

## 独立执行

实际源HEAD9b78f4279cc6fa50b3b51c31a5c8e07abbeda207，父00e509a974b40a7c9779fcd35e53b16637a13d60。depending43 Python3.11.16、RDKit2026.03.6、SQLite3.53.4。源码隔离完整vendor+必要metadata、无字节码/pytest缓存，全部输出仓外新tmp。初末274显式工程输入SHA相同，主仓不改动。

|执行|实际|分类|
|---|---|---|
|PPV1全量23文件|594通过，0跳过，0失败，1历史警告|536存量+58新项；不代表性能|
|两新文件当前|58通过|search45/recover13|
|两新文件+profile父基线|2 collection error，exit2|新search模块缺失；58未执行；此组合profile也未执行|
|profile父基线单跑|2失败/21通过，exit1|纯版本行为断言，没有缺字段/表/适配；后续delivered_stages分支不算已红|
|安全G01|1196通过/8跳过/17排除，exit0|274白名单；pytest194.01s；历史1110、1138不混算|
|slow collect-only|16 nodeid|没有测试体执行；另排一条export|

profile失败1=`test_ppv1_identity_block_contract_versions`:父profile-8≠期待profile-9，第一断言失败；失败2=`test_ppv1_identity_block_default_switches`:父search-limits-2-proposed≠期待3，后面的delivered_stages比较未执行。四输入（两新文件、profile、worker）current/baseline/仓源SHA逐一相同，无import适配。

G01逐项缺席：真实评价5（batch_runner52；score_report110/163/172/184）、v4对照1（analog_assets95）、phase_d metadata2（analog_v2_corpus62/153）。8条原始SKIPPED保留；16slow实际收集及1条`tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`明确排除。没有把skip改为pass，没有补读禁区依赖。

## legacy身份与实际拒绝

独立合成probe：父legacy aggregate=`5e8761c91d355f66ba81dfd80e6c3203b526d7ae4f2845baeaaa46b2246bf3a3`；当前=`4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`，逐文件差异仅workflow/runner.py。去除`_refuse_undelivered_profile`后全module AST相同；两版`legacy_v43`调用该函数均返回None；PPV1均RunError。新PPV1detail准确声明S0-S2,S3a-base / 缺S3b-S5。synthetic old/current identity输入导致既有check_resume_identity仅在code_identity拒绝；不读取历史真实run。这是共享文件文案带来的既有身份变化，交付已如实登记，不能写成跨提交legacy恢复仍兼容。G01绿支持同版本legacy行为未改，证明限度分开。

## 非阻塞落字更正

交付§1把recover写12，当前JUnit为13，总58正确。交付基线括写版本/阶段三项，实际两项首失败为profile与search-limits；delivered_stages后续未运行不得独立计为红。以上为记录精度修正，单凭它们不升级P1。

## 安全与证据

全部脚本与输入/输出、JUnit、argv/cwd/env/依赖、schema、输入SHA、worktree日志、可复现控制器附于本包。仅G01脚本新增JUnit观测参数，零选测和语义修改；全部独立套件只单次，另新文件子集为同字节红绿对照；slow仅collect。没有source/test/既有docs/AGENTS修改，没有push/外模/真实判分。初末主仓HEAD相同、旧工作区差异保留。此专项未提出P1；最终阶段裁定由主审合并其他专项具体证据。
