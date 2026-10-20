# -*- coding: utf-8 -*-
"""T-H 部署轮(s5b-compiler-6)产物侧身份自洽门单测。

动机(2026-10-20 实测):D1.2 补映射使产物侧含游离退化片段(如 ``[N+]``,
RDKit 产出裸 ``|0|`` 未登记 CX 块)的记录首次编译入池;worker decide 段在
模型调用前对全部池 spec 构建产物态,chemstate 身份守卫 fail-closed ⇒
整题 0 调用失败(21/298 题)。门=编译包装层对 compiled spec 的
product_smiles/coproducts 经 ``build_chemical_state`` 逐一核验,不过 ⇒
结构化拒 ``product_component_identity_invalid``(判据单一来源,不引入
化学判断;``_compile_donor_template_impl`` 内判据零改动)。
"""
from __future__ import annotations

from rdkit import Chem, RDLogger  # noqa: F401

from pathway_v43.pollutant.s5b_compiler import (
    S5B_COMPILER_VERSION,
    S5B_PRODUCT_IDENTITY_GATE_VERSION,
    _product_components_identity_problem,
    compile_donor_template,
)

RDLogger.DisableLog("rdApp.*")

# 合成退化件:[N+] 游离片段经 RDKit 产出 |0|(未登记 CX 类)
_DEGEN_TEMPLATE = {
    "mapped_lhs": "[CH3:1][N+:2]([CH3:3])[CH3:4]",
    "mapped_rhs": "[CH3:1][CH3:3].[CH3:4].[N+:2]",
    "substrate": "C[N+](C)C",
}
_CLEAN_TEMPLATE = {
    "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
    "mapped_rhs": "[CH3:1][CH:2]=[O:3]",
    "substrate": "CCO",
}


def test_helper_flags_degenerate_coproduct() -> None:
    spec = {"product_smiles": "C", "coproducts": ["CC", "[N+]"]}
    problem = _product_components_identity_problem(spec)
    assert problem is not None
    bad = problem["invalid_components"]
    assert len(bad) == 1
    assert bad[0]["component"] == "[N+]"
    assert bad[0]["kind"] == "unregistered_cx_class"


def test_helper_passes_clean_spec() -> None:
    spec = {"product_smiles": "CCO", "coproducts": ["O", "[H+]"]}
    assert _product_components_identity_problem(spec) is None


def test_helper_flags_degenerate_product_component() -> None:
    spec = {"product_smiles": "[N+]", "coproducts": []}
    problem = _product_components_identity_problem(spec)
    assert problem is not None


def test_compile_rejects_degenerate_products() -> None:
    """合成退化模板:冒烟证明篇——无门时该模板可编译并产 [N+] 组分
    (2026-10-20 REPL 实证),门上后 ⇒ product_component_identity_invalid。"""
    out = compile_donor_template(
        mapped_lhs=_DEGEN_TEMPLATE["mapped_lhs"],
        mapped_rhs=_DEGEN_TEMPLATE["mapped_rhs"],
        center_atoms=[], substrate_smiles=_DEGEN_TEMPLATE["substrate"],
        record_id="syn-degen")
    assert out["status"] == "unsupported"
    assert out["reason"] == "product_component_identity_invalid"
    assert out["detail"]["invalid_components"][0]["component"] == "[N+]"


def test_compile_still_passes_clean_template() -> None:
    """合法正控:干净模板照常编译(门不全面拒绝)。"""
    out = compile_donor_template(
        mapped_lhs=_CLEAN_TEMPLATE["mapped_lhs"],
        mapped_rhs=_CLEAN_TEMPLATE["mapped_rhs"],
        center_atoms=[], substrate_smiles=_CLEAN_TEMPLATE["substrate"],
        record_id="syn-clean")
    assert out["status"] == "compiled"
    assert out["spec"]["compile"]["compiler_version"] == "s5b-compiler-6"
    # 非退化产物:门未加任何键
    assert "invalid_components" not in out["spec"]


def test_versions_registered() -> None:
    assert S5B_COMPILER_VERSION == "s5b-compiler-6"
    assert S5B_PRODUCT_IDENTITY_GATE_VERSION == "product-identity-gate-1"
