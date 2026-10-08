# S3a Codex 独立复审永久证据

日期：2026-10-07，Asia/Shanghai。固定仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`，父提交 `00e509a974b40a7c9779fcd35e53b16637a13d60`。

**S3a 不通过，五组 P1；S3b 暂不可启动。** 报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md`，§4 逐项证据、§8 有限回修提示词。通过的工程测试不能替代损坏/错绑/预算公共链反例。

## 1. 目录与实际执行

| 目录 | 内容/本轮实际 |
| --- | --- |
| `execution_specialist/` | 独立 PPV1 594/0；当前新回归58；父基线2 collection（58未执行）及 profile 单跑2 failed/21 passed；安全 G01 1196/8/17；完整 stdout/stderr/JUnit/命令/白名单/哈希/legacy 身份/基线 worktree 建立清理 |
| `search_specialist/` | 16 个分案公共链探针 + B1–B4硬杀/H06 barrier共5案 + 上限1实际3事件used0的加强预算1案，共22；前后账/完整输入/artifact/返回、子进程日志与准备修正 |
| `inheritance_specialist/` | B4/done各clean+12坏共26案、raw首提1案，共27；24坏权威恢复接受而正常writer重放拒；每案14表及原载荷；三None/converter/audit未知、runner、AST、CX当前分段控制 |
| `root_probes/` | 主审11请求案例+首行metadata（无footer）；5策略消费案例；原脚本/完整JSONL/前后账/命令及只读观察断言、固定输入snapshot、安全复现模板 |

三专项原件与复制件182附件及6份内层清单全部逐SHA核对，原路径/数量见 `package_assembly.json`。外层清单还覆盖这些内层 `manifest.json`/`SHA256SUMS`，只排除本目录根部的两个自清单。不归档运行SQLite、完整src/vendor树、资产、pycache或pytest cache；用固定提交与输入SHA复现。

原 R8 化学源字节一致及必要合法控制保持；本次没有复跑全部R6/R7/R8永久探针，不冒称旧整套新执行。R7历史1110/8/17、R8历史1138/8/17分开。本轮工程数据不代表dev或298题域科学性能，化学判据尚未冻结。S3b生产caller/调度/中心链/公开runner继续未交付。

## 2. 完整性及安全边界

`run_metadata.json` 记录实际HEAD/父、分段执行来源、schema/环境、计数、初始输入与已知取证限制；`workspace_integrity.json` 核对425个明确既存输入、tracked diff与HEAD、预期旧差异及新增路径；`report.sha256` 绑定独立报告。原G01脚本仅增加JUnit观测，未改变筛选；274安全输入前后一致。

全执行仓外新tmp、depending43 Python、`-B`/无bytecode/pytest cache；完整vendor与metadata。只合成，无金标/题面/封存逐题run/dependingv4；没有provider调用、模型送审、真实网络发送、判分LLM或push。真实请求种类只作账表登记，network始终0。主仓仅新增报告和本目录，用户原AGENTS修改、`.zcodeignore`、旧未跟踪材料保留。

审核阶段已完成的套件/探针不再重跑。新增归档复现控制器仅语法/路径检查，未实际运行；原分段脚本与原日志才是执行证据。根两原探针的命令/exit已捕获，但当时未单独登记墙钟耗时，不能补造；其余专项耗时与实际argv见各包metadata。正确契约断言在当前坏案上预期失败，观察断言通过只表示确实存在缺口，不是验收通过。

## 3. 准备修正/早停不得忽略

- 搜索第一次异常名字断言写LedgerCorrupt，实际Ppv1LedgerCorrupt，9行后早停；新tmp修记录断言后完整16。原attempt1脚本/输出保留。
- 四硬杀已完成后，父控制器遗漏GO写入而两barrier进程ready等待；实际双ready后父侧续接GO完成并发控制。原体、真实续接、新便携内联体区分，没重新跑四硬杀。
- 继承第一次用不存在的PathwayEvent.to_dict序列化，零case；新tmp用asdict完整27。化学第一次14case后AST版本Name求值失败，两自写畸形DAT正确拒；修审核输入/静态比较后新tmp完整15。原失败体由编辑历史重构，明确没有执行前冻结hash。
- `inheritance_specialist/assert_contract.py` exit1首坏state_charge停，后续断言未执行；24坏案来自逐案capture及observed断言，不是那个早停体“全验过”。

## 4. 安全复现

**禁止在永久证据目录原地运行会写库/结果的底层探针。** 所有控制器必须显式选择不存在的新仓外out、保持金标/题面/封存边界；核固定HEAD/白名单hash后复制到新tmp。修复后的HEAD/hash变化应新轮登记，不能改旧永久清单冒充同次执行。

各专项README包含完整命令。根请求/策略最小复现（只是两个合成探针，不跑套件/不外模）：

```bash
PY=/Users/cc/miniconda3/envs/depending43/bin/python
REPO=/Volumes/CC/Enzyme_Agent/dependingv43
E=$REPO/docs/review_evidence/ppv1_s3a_codex_2026-10-07
PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$E/root_probes/root_probe_reproduction.py" \
  --repo "$REPO" --out /private/tmp/ppv1_s3a_root_replay_NEW --python "$PY"
```

搜索及继承控制器分别为 `search_specialist/reproduce.py`、`inheritance_specialist/reproduce.py`，同样 `--repo/--out/--python`。工程回归入口 `execution_specialist/reproduce_engineering.py`；G01参数详其README。新包装未运行，不应把复现命令当本审又一次执行结果。

只读归档核验（不会运行探针/创建库）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_2026-10-07/verify_evidence.py
```

完整附件逐SHA见 `manifest.json`/`SHA256SUMS`。复制证据时保留全部内层清单和原日志；对原来错误输出不删不覆盖。
