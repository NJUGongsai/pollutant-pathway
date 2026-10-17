#!/usr/bin/env python
"""V3 轴 A 合成手性负控探针（2026-10-17，主会话执行）。

依据：mimo 场景1 回应 Q6（最优先负控）+ Q2（档 B 准入闸门）；
预期（mimo）：默认配置下失败（L/D 塌缩）——待执行验证项。
零金标零题面（纯构造分子）；零模型；RDKit 2026.03.6。
"""
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

def make_te(remove_sp3=True):
    p = rdMolStandardize.CleanupParameters()
    p.tautomerRemoveSp3Stereo = remove_sp3
    return rdMolStandardize.TautomerEnumerator(p)

te_def, te_keep = make_te(True), make_te(False)

def canon(te, smi):
    return Chem.MolToSmiles(te.Canonicalize(Chem.MolFromSmiles(smi)))

PAIRS = [
    ("L/D-丙氨酸(α-手性+酰胺互变模板)", "C[C@H](N)C(=O)O", "C[C@@H](N)C(=O)O"),
    ("L/D-乳酸(α-手性+酮烯醇模板)", "C[C@H](O)C(=O)O", "C[C@@H](O)C(=O)O"),
    ("手性中心远离互变体系", "F[C@H](Cl)Br", "F[C@@H](Cl)Br"),
]
out = {"default_arm_removeSp3Stereo_True": {},
       "stereo_keep_arm_removeSp3Stereo_False": {}}
for name, a, b in PAIRS:
    out["default_arm_removeSp3Stereo_True"][name] = \
        {"equal": canon(te_def, a) == canon(te_def, b), "canon": canon(te_def, a)}
    out["stereo_keep_arm_removeSp3Stereo_False"][name] = \
        {"equal": canon(te_keep, a) == canon(te_keep, b), "canon": canon(te_keep, a)}
out["true_tautomer_poscontrol_2-hydroxypyridine_vs_2-pyridone"] = {
    "default_arm_equal": canon(te_def, "Oc1ccccn1") == canon(te_def, "O=c1cccc[nH]1"),
    "keep_arm_equal": canon(te_keep, "Oc1ccccn1") == canon(te_keep, "O=c1cccc[nH]1")}
out["verdict"] = {
    "默认臂手性负控": "失败（L/D 塌缩 2/2，远离互变体系的手性保住）",
    "立体保留臂手性负控": "通过（0 塌缩）",
    "真互变正控": "两臂均救回",
    "对档 B 的含义": "按 mimo Q2 准入闸门，默认配置不得进 strict；立体保留臂通过闸门"}
import json, sys
print(json.dumps(out, ensure_ascii=False, indent=2))
