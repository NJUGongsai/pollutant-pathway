"""S5A-04 反例复现探针(复制自评审 conditions/scripts/
write_boundary_probe.py,仅改 ROOT/sys.path 指向当前仓;fresh tmp 执行)。

五案全合成写边界(占位内容 synthetic-placeholder-not-gold,不接触真实
金标):显式 repo_root + 错 cwd 相对路径 / 绝对路径越界 / 相对路径经
symlink 逃根 / 绝对路径经 symlink 逃根 / 合法授权根正控。只观察并记录,
不修改产品行为;断言由 before/after 检查脚本分别执行。
"""
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/Volumes/CC/Enzyme_Agent/dependingv43")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    persist_evaluation_output,
)

WORK = ROOT / "work" / "write_boundary"
WORK.mkdir(parents=True, exist_ok=True)
declared = WORK / "declared_repo"
declared.mkdir()
elsewhere = WORK / "elsewhere"
elsewhere.mkdir()
external = WORK / "external_target"
external.mkdir()
relative = Path("reports/phase_s1_hit60/dev_gold/report.json")
normal_relative = Path("reports/phase_s1_hit60/dev_gold/good.json")
link = declared / "reports" / "phase_s1_hit60" / "dev_gold"
link.parent.mkdir(parents=True)
link.symlink_to(external, target_is_directory=True)
output = {"status": "interface_verified_only",
          "payload": "synthetic-placeholder-not-gold"}
cases = [
    ("explicit_root_relative_wrong_cwd", elsewhere, relative, declared),
    ("explicit_root_absolute_outside", elsewhere,
     elsewhere / "reports/phase_s1_hit60/dev_gold/abs.json", declared),
    ("explicit_root_relative_symlink_escape", declared, relative,
     declared),
    ("explicit_root_absolute_symlink_escape", declared,
     declared / "reports/phase_s1_hit60/dev_gold/abs_link.json",
     declared),
]
records = []
original = Path.cwd()
for name, cwd, target, root in cases:
    os.chdir(cwd)
    resolved = target.resolve()
    row = {
        "name": name, "target_literal": str(target), "cwd": str(cwd),
        "declared_repo_root": str(root),
        "resolved_target": str(resolved),
        "resolved_inside_declared_root":
            resolved.is_relative_to(root.resolve()),
        "input": output, "contains_gold": True,
        "target_exists_before": resolved.exists()}
    try:
        row["receipt"] = persist_evaluation_output(
            output, target, contains_gold=True, repo_root=root)
    except EvaluationContractError as ex:
        row["exception"] = {
            "type": type(ex).__name__, "message": str(ex),
            "detail": ex.detail}
    row["target_exists_after"] = resolved.exists()
    if resolved.is_file():
        row.update(
            written_text=resolved.read_text(),
            written_sha256=hashlib.sha256(
                resolved.read_bytes()).hexdigest())
    records.append(row)
    print(name, "accepted" if "receipt" in row else "refused",
          "outside=", not row["resolved_inside_declared_root"],
          "created=", row["target_exists_after"], flush=True)
# 合法正控:实际普通授权根内的相对路径(fresh 假仓)
normal = WORK / "normal_fake_repo"
normal.mkdir()
os.chdir(normal)
resolved = normal_relative.resolve()
receipt = persist_evaluation_output(
    output, normal_relative, contains_gold=True, repo_root=normal)
records.append({
    "name": "lawful_relative_inside_declared_root",
    "target_literal": str(normal_relative), "cwd": str(normal),
    "declared_repo_root": str(normal),
    "resolved_target": str(resolved),
    "resolved_inside_declared_root": True,
    "input": output, "contains_gold": True, "receipt": receipt,
    "written_text": resolved.read_text(),
    "written_sha256": hashlib.sha256(
        resolved.read_bytes()).hexdigest()})
os.chdir(original)
(ROOT / "probe" / "outputs" / "write_boundary.json").parent.mkdir(
    parents=True, exist_ok=True)
(ROOT / "probe" / "outputs" / "write_boundary.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2) + "\n")
print("write boundary probe complete:", len(records), "records")
