#!/usr/bin/env python3
"""recompute_ablation_anchors.py — v44 论文消融核心锚点零 LLM 独立复算与锁状态验收器。

用途（回应 Axl 2026-11-22 审阅门槛）
--------------------------------------
在完全脱离原始采样与未入仓大脚本的前提下，基于冻结的 ``ppv1-criteria-v6`` 判分器与
归档重放产物（`batch/` + `runs/` + `run_inputs/`），零 LLM 调用独立复算并硬门断言：

1. ``T1-6`` 完整系统（11 路共识 + ``trace_protected`` 裁决）：
   - ``[Tuning-261]`` ``v6 all = 118 / 133 / 141 (45.21%)``，``Clean-220 = 113 / 127 / 134 (51.36%)``
   - ``v4 all = 80 / 96 / 102 (30.65%)``，``Clean-220 v4 = 76 / 91 / 96``
   - ``v6 ex_rec_only = 72``，``v6 ex-self = 57 / 63 / 72``（``Clean-220 = 56``）
2. ``T1-6 NoSelf_11p`` 输入端清零自记录全系统（11 路 ``db2_pa..pk`` + 共识 + 裁决）：
   - ``[Tuning-261]`` ``v6 all = 94 / 127 / 134 (36.02%)``，``Clean-220 = 90 / 120 / 126 (40.91%)``
   - ``v4 all = 61 / 87 / 93 (23.37%)``，``Clean-220 v4 = 58 / 82 / 87``
   - ``v6 ex_rec_only = 94 / 127 / 134``（``== all``，输入端 ``rec`` 自记录零残留）
   - ``v6 ex-self = 70 / 97 / 103 (26.82%)``（``Clean-220 = 66``）
3. ``self_61`` 逐题交叉与 261 题 Venn：
   - ``T1-6 all (118) -> ex-self (57)`` 扣分 ``61`` 题（``46 rec_only + 15 tpl_only``）；
   - ``T1-6 NoSelf_11p`` 在该 ``61`` 题上实测夺回 ``43/61 Hit@1``（``Top-5 = 56/61``，严格剔模板 ``20/61``）；
   - ``T1-6 NoSelf_11p`` 自身 ``94 -> 70`` 的 ``24`` 题扣分 ``100%`` 来自 ``tpl_only``（``rec_only = 0``）。

红线纪律
--------
- 100% 零 LLM / 零网络 / 零触碰留出集；
- 运行前后双重校验三份冻结判分器 SHA256；
- 自动直接调用冻结 ``scripts/eval/score_disclosure_v4cn.py --self-check`` 做端到端核验；
- 产出的回执 JSON **严禁含任何 SMILES、InChI、私有题号或本机绝对路径**。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
EVAL_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

FROZEN_SCORER_SHA256: dict[str, str] = {
    "scripts/eval/score_disclosure_v4cn.py": (
        "0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f"
    ),
    "src/pathway_v43/pollutant/evaluation.py": (
        "ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41"
    ),
    "src/pathway_v43/pollutant/s5b_scoring.py": (
        "5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d"
    ),
}

# 220 道 4 层去噪干净子集的单向 SHA256 前 16 位指纹（零原始题号、261 题内零碰撞）
CLEAN_220_SHA16: frozenset[str] = frozenset({
    "013eba591dc62813", "01936821aad1be81", "01d62bc54aa7743a", "03c5d404431a4916",
    "0483f2c547e663e9", "04de80a528455175", "0599cd4cc9375175", "0628a390e77ffc35",
    "06d6932574a503c9", "0718a1e09000ab69", "08a1d72d9a940feb", "09c2a87f115f6cc0",
    "09e18dea438a0ce5", "0af0d4dce8544084", "0bba93c1cef5a693", "0bbbff2ad83afcb5",
    "0bd71293a15d5866", "0c677998671b4ad1", "0d1cac887cc1040e", "0e4c07c12e0624fc",
    "0ef5d1230d3fa4d0", "115434da8c65da92", "12d9ca70595a405e", "171bf546eb0158ed",
    "17306e0ab8fa20a7", "198fa8bd4463cc30", "214aa12eed4798e9", "23edd7af67985d15",
    "2438d92d8dca8ad6", "24bfd8131634053e", "252df0372d66965e", "2556c040e1784625",
    "291e839e4e460a24", "2a49afe16caa9a23", "2aea29c98aea281e", "2b9da8e94f182bfd",
    "2bc47b6106596e31", "2d4e1d4b1ec2b116", "2dd083223da0f203", "2f5d939561957292",
    "2f95304e7ba3cf7e", "30114dc6d4a5d102", "324bd46d49dffc16", "325561bebc59e7c6",
    "32ced7fcb2de9a04", "35828b03f6368b3a", "388d84d0961becc3", "38a00b41f34a1370",
    "3a82e7bec71db316", "3abac6cddfdfe5a1", "3c7da3442225ae95", "3e1ceb8c64ebc866",
    "3fee1224f7de6d01", "407f63e01e2adf70", "41b7493eef24e5aa", "44b0e8037dbd3d28",
    "4ef69063d3f8654d", "4f6c1ad90b9c74dd", "51d3498907a70362", "55567af68d3d467c",
    "55e655be929d29ad", "5691e1f291e1b028", "5b1a14291a23785a", "5b3e2501431fbb13",
    "5b4d6d4fac437c41", "5bec22eec495b57a", "5e073274fc6d23fa", "5e1386acf1997736",
    "5ee2e4794deaa1a0", "60a27a45de5e7c0e", "62c5556313dff974", "63a83769d7241c90",
    "64caded6382c9ba5", "64ef8add1147d6c0", "65ddca3ef73c4e90", "668536a2e10d4be5",
    "6a80cfdbc6ed83ab", "6a83e4f70060feac", "6b13f1f88e488614", "6b7d1ab86d281d5f",
    "6b94c5ed17dedc69", "6c03630f6d1ca07c", "6e5c2bfc759287a4", "6ef72e29d0bfdcac",
    "6f7b8425d0df9d9a", "6facc93659c8db94", "7000fa1a6e47a1a4", "71a10e7f4067cd1a",
    "71dc61568c5abfd7", "71e119a5ad2fac9a", "73f644336262bca7", "763febff0f810258",
    "7640f0daa7120cca", "7843aca37d83c736", "7967128177b8ccc2", "7a22cae891b6b002",
    "7c2d030b83de0f8c", "7c952b66f044b48d", "7cf6d2222b6593cd", "7dba8ea07dc06686",
    "7ef39a2917068af6", "7f4577e69c934922", "7f66de096fd1a1be", "81a3a763a28f8708",
    "81efd25c157363f7", "822628f0c1936203", "83646963cedc11a4", "83a83c532b22b9fd",
    "83e868b83262110a", "8579a7535fbe9c91", "8581d041c0759dac", "87a62d4641ef8bc2",
    "880f94a9d50d6c91", "88a0b1e6ad05dd83", "898419fb4b83da66", "8ba6effd9da096fa",
    "8c00254bd2a408e6", "8c85597d6f8379a7", "8d7f4ae00920dc38", "8e9e899c282d5f93",
    "8f05e154259c10ae", "8fc4c18a64e36849", "90db365c2f7571df", "90efc492449dfc21",
    "94b7e725453d2493", "94be5fd2f59e0054", "94f9ec6f43487ccc", "963c10f5b37887a7",
    "969f154ba45b51c3", "96e9666da2a201a2", "98c6c041cbd561f9", "99094e30aa464cd8",
    "9b3c95a093099485", "9bc99a1a933b74f4", "9bcb6d416bf8b6e0", "9bec9bac70131bbd",
    "9bf0d9b290251979", "9bfbbe9eca718e35", "9de7f47b60990079", "9ee30d290b6b8da0",
    "9fb43d4e6270d79a", "a39c2886942b917c", "a3ffc1f4b8266567", "a5746a12f0d0d038",
    "a588f0cff34bcaa9", "a93eb8e07b86e013", "aab137a7871f62c2", "aab684cc641cccaa",
    "aac1581eefec6367", "ab5384279e508a56", "ac6103d9f334e356", "ada92ca97bd1fc8c",
    "ade81cc35b6d3f17", "afc4fb3aaa132840", "b0fff263bb9b6a4b", "b226e1adcde1e2be",
    "b3128a6179fea499", "b34e9b9569e9bfcf", "b38948aa86a1b2da", "b49f9ecc002b3715",
    "b6988d71eb582b93", "b7cfe18de47ac314", "b9a4754a90564eca", "bb493d9c6378cef6",
    "bbbff9e991c23f6c", "bbdc2b67bce223c6", "bd701c8f0366422c", "be20553a0151d8bc",
    "be2e225d6782627f", "be432a29836943a1", "be92728c0906e3d9", "bed9c4e517621b8e",
    "c1f9f283d9d87fd4", "c2f092543da7af6c", "c30edc0f496d0605", "c3e9ef0a27e2f682",
    "c5e910866cf19b77", "c610ba38c68a33db", "c7549ccd3a0a5a7e", "c79e871d9c923d32",
    "c8cf1402f7478e25", "c91514f7ab494a6c", "c9b61812c9c6531e", "cb14ad497a8a36f1",
    "cb6d2ba9cde9d994", "cc38d7e48bdcc6be", "ceddf617b01a6a73", "d08157527f9016dd",
    "d20afd70f08977fd", "d21f9b25b5ae6595", "d27a7239f3a1fb16", "d40f629a9f579fa2",
    "d44e9edb7dc95e05", "d5d71a64bfbe0896", "d6b2149bb92ef9eb", "d6deb629eb8b3ab8",
    "d97525066b16224e", "da59c3bb3dcb5200", "dfa3d1a8e4be6b3d", "e150497b9c1c27ef",
    "e2a4da96c5037c9e", "e2f3a8f1595eaa38", "e547be308ffcb76d", "e5abcf102f553d99",
    "e69e0f18c54e2d4c", "ea9a1fc2dd1b1b89", "ed0346b026047e08", "ed500972ca40cc1b",
    "ed93e7c778afc23f", "ede5ba16953486c8", "efcecdc81e4c2676", "f0f81afb87f945ea",
    "f2bf394ca3f22f81", "f2e396eb6ba9f487", "f2fee67cc6bfcf57", "f42deb3d4442c2ea",
    "f528843c19ea7c56", "f6c42392a137ee42", "f73b1d0bd43ca665", "fe086baf5264b28b",
})


def sha16(qid: str) -> str:
    return hashlib.sha256(str(qid).encode("utf-8")).hexdigest()[:16]


def verify_frozen_scorers(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """前/后校验三份冻结判分器 SHA256，不一致则 fail-closed 退出码 2。"""
    files: dict[str, dict[str, Any]] = {}
    all_ok = True
    for rel, expected in sorted(FROZEN_SCORER_SHA256.items()):
        path = repo_root / rel
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
        ok = actual == expected
        all_ok = all_ok and ok
        files[rel] = {"expected": expected, "actual": actual, "ok": ok}
    if not all_ok:
        raise RuntimeError(f"冻结判分器 SHA256 校验失败: {json.dumps(files, ensure_ascii=False)}")
    return {"all_ok": True, "files": files}


def classify_key_prefix(key: str, tref: str) -> str:
    """将候选 key / transformation_ref 映射为通道家族类别（零 SMILES）。"""
    for src in (str(key or ""), str(tref or "")):
        if src.startswith("rec-") or "rec-source:" in src:
            return "rec"
        if src.startswith("tpl-recorded"):
            return "tpl-recorded"
        if src.startswith("tpl-rr_mnx") or src.startswith("rr_mnx"):
            return "tpl-rr_mnx"
        if src.startswith("tpl-rr_rhea") or src.startswith("rr_rhea"):
            return "tpl-rr_rhea"
        if src.startswith("tpl-eawag"):
            return "tpl-eawag"
        if src.startswith("tpl-envipath"):
            return "tpl-envipath"
        if src.startswith("tpl-analog"):
            return "tpl-analog"
        if src.startswith("tpl-uspto"):
            return "tpl-uspto"
        if src.startswith("tpl-"):
            return "tpl-other"
        if "novel" in src:
            return "novel"
    return "other"


def _expand_action_payload(action: dict) -> dict:
    raw = action.get("payload")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def provenance_from_payload(payload: dict) -> dict[str, dict[str, str]]:
    """从导出 payload.json 提取 event_id -> hypothesis_key / transformation_ref。"""
    if not isinstance(payload, dict):
        return {"hypothesis_key_by_event": {}, "transformation_ref_by_event": {}}
    hyp_by_event: dict[str, str] = {}
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id") or "")
        hypothesis_id = str(event.get("hypothesis_id") or "")
        if event_id and hypothesis_id:
            hyp_by_event[event_id] = hypothesis_id

    key_by_prepared: dict[str, str] = {}
    tref_by_prepared: dict[str, str] = {}
    for action in payload.get("search_actions") or []:
        if not isinstance(action, dict):
            continue
        if str(action.get("action_kind") or "") != "expand_hypothesis":
            continue
        body = _expand_action_payload(action)
        prepared_id = str(body.get("prepared_hypothesis_id") or action.get("subject_ref") or "")
        if not prepared_id:
            continue
        key = str(body.get("logical_proposal_id") or body.get("hypothesis_key") or "")
        if key:
            key_by_prepared.setdefault(prepared_id, key)
        spec = body.get("spec")
        tref = str(spec.get("transformation_ref") or "") if isinstance(spec, dict) else ""
        if tref:
            tref_by_prepared.setdefault(prepared_id, tref)

    return {
        "hypothesis_key_by_event": {
            ev: key_by_prepared[hid]
            for ev, hid in hyp_by_event.items()
            if hid in key_by_prepared
        },
        "transformation_ref_by_event": {
            ev: tref_by_prepared[hid]
            for ev, hid in hyp_by_event.items()
            if hid in tref_by_prepared
        },
    }


def _match_refs(text: str, refs: set[str]) -> list[str]:
    if not text or not refs:
        return []
    return [ref for ref in refs if ref and (text == ref or text.endswith(ref) or ref in text)]


def _identity_keys(smiles: str, v4cn_mod: Any = None) -> set[str]:
    from pathway_v43.pollutant.chemstate import strict_identity_of

    out: set[str] = set()
    raw = str(smiles or "").strip()
    if not raw:
        return out
    try:
        key = str(strict_identity_of(raw) or "")
        if key:
            out.add(key)
    except Exception:  # noqa: BLE001
        pass
    if v4cn_mod is not None:
        try:
            neutral = str(v4cn_mod._neutralize_smiles(raw) or "")
            if neutral and neutral != raw:
                nkey = str(strict_identity_of(neutral) or "")
                if nkey:
                    out.add(nkey)
        except Exception:  # noqa: BLE001
            pass
    return out


def build_detailed_self_index(
    v4cn_mod: Any,
    batch_root: Path,
    qids: list[str],
) -> dict[str, dict[str, Any]]:
    """按 Stage P4/P5 同源逻辑构建每题 ``rec_refs``（直接记录）与 ``tpl_refs``（同底物-主产物模板对）。"""
    manifest_path = batch_root / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    entry_by_qid = {str(e.get("qid")): e for e in manifest.get("entries") or []}
    out: dict[str, dict[str, Any]] = {}
    for qid in qids:
        run_input_path = batch_root / "run_inputs" / f"{qid}.json"
        if not run_input_path.is_file():
            out[qid] = {"rec_refs": set(), "tpl_refs": set(), "all_refs": set(), "tpl_family": {}}
            continue
        run_input = json.loads(run_input_path.read_text(encoding="utf-8"))
        pools = (run_input.get("plan") or {}).get("pools") or {}
        rec_pairs: list[tuple[str, str, str]] = []
        tpl_pairs: list[tuple[str, str, str]] = []
        for cands in pools.values():
            for cand in cands or []:
                tref = str(cand.get("transformation_ref") or "")
                key = str(cand.get("key") or "")
                product = str(cand.get("product_smiles") or "")
                fam = classify_key_prefix(key, tref)
                if key.startswith("rec-") or str(cand.get("origin_group_key") or "").startswith("rec-source:"):
                    if tref:
                        rec_pairs.append((tref, product, fam))
                elif key.startswith("tpl-"):
                    if tref:
                        tpl_pairs.append((tref, product, fam))

        gold_keys: set[str] = set()
        entry = entry_by_qid.get(qid) or {}
        graph_rel = str(entry.get("graph_rel") or "")
        if graph_rel:
            graph = v4cn_mod.load_reference_graph(batch_root / graph_rel)
            for node in graph.get("nodes") or []:
                role = str(node.get("role") or "")
                if role and role != "principal_product":
                    continue
                gold_keys |= _identity_keys(str(node.get("structure_smiles") or ""), v4cn_mod)

        def _is_gold(product: str) -> bool:
            return bool(gold_keys and product and (_identity_keys(product, v4cn_mod) & gold_keys))

        rec_refs: set[str] = set()
        tpl_refs: set[str] = set()
        tpl_family: dict[str, str] = {}
        for tref, product, _fam in rec_pairs:
            if not gold_keys or _is_gold(product):
                rec_refs.add(tref)
        for tref, product, fam in tpl_pairs:
            if gold_keys and _is_gold(product):
                tpl_refs.add(tref)
                tpl_family[tref] = fam
        out[qid] = {
            "rec_refs": rec_refs,
            "tpl_refs": tpl_refs,
            "all_refs": rec_refs | tpl_refs,
            "tpl_family": tpl_family,
        }
    return out


def compute_ex_self_ranks(
    *,
    candidates: list[dict],
    hit_events: set[str],
    tref_by_event: dict[str, str],
    key_by_event: dict[str, str],
    rec_refs: set[str],
    tpl_refs: set[str],
    tpl_family: dict[str, str] | None = None,
) -> dict[str, Any]:
    """在已提交候选列表中重算剔除 ``rec_refs`` / ``tpl_refs`` 后的首位命中位次与首名来源标签。"""
    first_ex_rec: int | None = None
    first_ex_all: int | None = None
    rank1_prefix: str | None = None
    rank1_rec_flag = False
    rank1_tpl_flag = False
    rank1_tpl_fam: str | None = None
    tpl_family = tpl_family or {}

    for pos, cand in enumerate(candidates, 1):
        ev_id = str(cand.get("event_id") or "")
        if ev_id not in hit_events:
            continue
        tref = str(tref_by_event.get(ev_id) or "")
        key = str(key_by_event.get(ev_id) or "")
        rec_hits = _match_refs(tref, rec_refs) or _match_refs(key, rec_refs)
        tpl_hits = _match_refs(tref, tpl_refs) or _match_refs(key, tpl_refs)
        is_rec = bool(rec_hits)
        is_tpl = bool(tpl_hits)
        if pos == 1:
            rank1_prefix = classify_key_prefix(key, tref)
            rank1_rec_flag = is_rec
            rank1_tpl_flag = is_tpl
            if tpl_hits:
                rank1_tpl_fam = tpl_family.get(tpl_hits[0]) or classify_key_prefix(key, tref)
        if not is_rec and first_ex_rec is None:
            first_ex_rec = pos
        if not (is_rec or is_tpl) and first_ex_all is None:
            first_ex_all = pos
    return {
        "ex_self_rank": first_ex_all,
        "ex_rec_rank": first_ex_rec,
        "rank1_prefix": rank1_prefix,
        "rank1_rec_flag": rank1_rec_flag,
        "rank1_tpl_flag": rank1_tpl_flag,
        "rank1_tpl_fam": rank1_tpl_fam,
    }


def _run_score_disclosure_subprocess(
    *,
    arm_dir: Path,
    out_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_dir = arm_dir / "batch"
    runs_dir = arm_dir / "runs"
    strict_metrics = batch_dir / "metrics_v4.json"
    if not strict_metrics.is_file():
        strict_metrics = arm_dir / "metrics_v4_replay.json"
    cmd = [
        sys.executable,
        "-B",
        str(repo_root / "scripts" / "eval" / "score_disclosure_v4cn.py"),
        "--batch-root",
        str(batch_dir),
        "--runs-root",
        str(runs_dir),
        "--out-dir",
        str(out_dir),
        "--domain-tag",
        "biosysmodb121",
        "--strict-metrics",
        str(strict_metrics),
        "--self-check",
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(repo_root / "src")
    proc = subprocess.run(cmd, cwd=str(repo_root), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"score_disclosure_v4cn.py --self-check 失败 rc={proc.returncode}:\n{proc.stderr[-1000:]}"
        )
    disclosure = json.loads((out_dir / "disclosure_v4cn_biosysmodb121.json").read_text(encoding="utf-8"))
    self_check = json.loads((out_dir / "self_check_biosysmodb121.json").read_text(encoding="utf-8"))
    return {"disclosure": disclosure, "self_check": self_check}


def _evaluate_arm_breakdown(arm_dir: Path) -> dict[str, Any]:
    import score_disclosure_v4cn as v4cn
    from pathway_v43.pollutant import s5b_scoring as s5b

    batch_dir = arm_dir / "batch"
    runs_dir = arm_dir / "runs"
    _, v4_rows = v4cn._build_inputs(batch_dir, runs_dir, neutralize=False, domain_tag="biosysmodb121")
    _, v6_rows = v4cn._build_inputs(batch_dir, runs_dir, neutralize=True, domain_tag="biosysmodb121")

    self_idx = build_detailed_self_index(v4cn, batch_dir, [str(r["qid"]) for r in v6_rows])

    def _summarize(rows: list[dict], *, collect_per_q: bool = False) -> tuple[dict[str, Any], dict[str, dict]]:
        n261 = {b: {"hit@1": 0, "hit@3": 0, "hit@5": 0} for b in ("all", "ex_rec_only", "ex_self")}
        n220 = {b: {"hit@1": 0, "hit@3": 0, "hit@5": 0} for b in ("all", "ex_rec_only", "ex_self")}
        per_q: dict[str, dict[str, Any]] = {}
        n_clean = 0
        for row in rows:
            qid = str(row["qid"])
            h16 = sha16(qid)
            is_clean = h16 in CLEAN_220_SHA16
            if is_clean:
                n_clean += 1
            hit = row.get("product_hit") or {}
            rank_all = hit.get("rank")
            hit_events = set(hit.get("product_hit_events") or [])
            payload = row.get("payload") or {}
            graph = row.get("graph") or {}
            roots = s5b._root_strict_states(row.get("sample") or {}, graph)
            candidates = s5b._candidate_events(payload, roots)
            prov = provenance_from_payload(payload)
            qidx = self_idx.get(qid) or {"rec_refs": set(), "tpl_refs": set(), "tpl_family": {}}
            ex_meta = compute_ex_self_ranks(
                candidates=candidates,
                hit_events=hit_events,
                tref_by_event=prov["transformation_ref_by_event"],
                key_by_event=prov["hypothesis_key_by_event"],
                rec_refs=qidx["rec_refs"],
                tpl_refs=qidx["tpl_refs"],
                tpl_family=qidx["tpl_family"],
            )
            ranks_by_bucket = {
                "all": rank_all,
                "ex_rec_only": ex_meta["ex_rec_rank"],
                "ex_self": ex_meta["ex_self_rank"],
            }
            for bucket, rk in ranks_by_bucket.items():
                if isinstance(rk, int):
                    for k in (1, 3, 5):
                        if rk <= k:
                            n261[bucket][f"hit@{k}"] += 1
                            if is_clean:
                                n220[bucket][f"hit@{k}"] += 1
            if collect_per_q:
                per_q[h16] = {
                    "rank": rank_all,
                    "ex_rec_rank": ex_meta["ex_rec_rank"],
                    "ex_self_rank": ex_meta["ex_self_rank"],
                    "rank1_rec_flag": ex_meta["rank1_rec_flag"],
                    "rank1_tpl_flag": ex_meta["rank1_tpl_flag"],
                    "is_clean": is_clean,
                }
        return {
            "N261": {"denominator": len(rows), **n261},
            "N220": {"denominator": n_clean, **n220},
        }, per_q

    v4_sum, _ = _summarize(v4_rows, collect_per_q=False)
    v6_sum, v6_per_q = _summarize(v6_rows, collect_per_q=True)
    return {"v6": v6_sum, "v4": v4_sum, "per_q": v6_per_q}


def _compute_cross_dissection(pq_t16: dict[str, dict], pq_noself: dict[str, dict]) -> dict[str, Any]:
    all_h16 = sorted(set(pq_t16) & set(pq_noself))
    self_61 = [h for h in all_h16 if pq_t16[h]["rank"] == 1 and pq_t16[h]["ex_self_rank"] != 1]

    t16_trig = Counter()
    ns_on_61 = Counter()
    for h in self_61:
        m = pq_t16[h]
        trig = (
            "both_rec_and_tpl" if (m["rank1_rec_flag"] and m["rank1_tpl_flag"])
            else ("rec_only" if m["rank1_rec_flag"] else ("tpl_only" if m["rank1_tpl_flag"] else "unknown"))
        )
        t16_trig[trig] += 1
        rk = pq_noself[h]["rank"]
        if rk == 1:
            ns_on_61["hit1_all"] += 1
        elif isinstance(rk, int) and rk <= 5:
            ns_on_61["hit2_5_all"] += 1
        else:
            ns_on_61["miss_top5"] += 1
        if pq_noself[h]["ex_self_rank"] == 1:
            ns_on_61["hit1_strict_ex_tpl"] += 1

    ns_drops = [h for h in all_h16 if pq_noself[h]["rank"] == 1 and pq_noself[h]["ex_self_rank"] != 1]
    ns_trig = Counter()
    for h in ns_drops:
        m = pq_noself[h]
        trig = (
            "both_rec_and_tpl" if (m["rank1_rec_flag"] and m["rank1_tpl_flag"])
            else ("rec_only" if m["rank1_rec_flag"] else ("tpl_only" if m["rank1_tpl_flag"] else "unknown"))
        )
        ns_trig[trig] += 1

    venn_all = Counter()
    venn_ex = Counter()
    for h in all_h16:
        a1 = int(pq_t16[h]["rank"] == 1)
        ax = int(pq_t16[h]["ex_self_rank"] == 1)
        n1 = int(pq_noself[h]["rank"] == 1)
        nx = int(pq_noself[h]["ex_self_rank"] == 1)
        venn_all[f"t16all_{a1}_ns11all_{n1}"] += 1
        venn_ex[f"t16ex_{ax}_ns11ex_{nx}"] += 1

    return {
        "n_common_questions": len(all_h16),
        "n_t16_all_self_61": len(self_61),
        "t16_self_61_trigger_breakdown": dict(sorted(t16_trig.items())),
        "t16_noself_11p_on_self_61": {
            "hit1_all": ns_on_61["hit1_all"],
            "hit2_5_all": ns_on_61["hit2_5_all"],
            "top5_all": ns_on_61["hit1_all"] + ns_on_61["hit2_5_all"],
            "miss_top5": ns_on_61["miss_top5"],
            "hit1_strict_ex_tpl": ns_on_61["hit1_strict_ex_tpl"],
        },
        "t16_noself_11p_own_drop_count": len(ns_drops),
        "t16_noself_11p_own_trigger_breakdown": dict(sorted(ns_trig.items())),
        "venn_261_t16all_vs_noself11p_all": dict(sorted(venn_all.items())),
        "venn_261_t16exself_vs_noself11p_exself": dict(sorted(venn_ex.items())),
    }


def _assert_anchor_values(receipt: dict[str, Any]) -> None:
    t16 = receipt["arms"]["T1-6"]
    ns = receipt["arms"]["T1-6_NoSelf_11p"]
    cross = receipt["cross_dissection"]

    checks = [
        ("T1-6 self_check.n_diffs == 0", t16["score_disclosure_self_check"]["n_diffs"], 0),
        ("T1-6 self_check.neutralization.ok", t16["score_disclosure_self_check"]["neutralization_ok"], True),
        ("T1-6 subprocess v6 all", t16["subprocess_v6_matched_product_hit"], {"hit@1": 118, "hit@3": 133, "hit@5": 141}),
        ("T1-6 subprocess v4 all", t16["subprocess_v4_matched_product_hit"], {"hit@1": 80, "hit@3": 96, "hit@5": 102}),
        ("T1-6 N261 v6 all", t16["breakdown"]["v6"]["N261"]["all"], {"hit@1": 118, "hit@3": 133, "hit@5": 141}),
        ("T1-6 Clean-220 v6 all", t16["breakdown"]["v6"]["N220"]["all"], {"hit@1": 113, "hit@3": 127, "hit@5": 134}),
        ("T1-6 N261 v4 all", t16["breakdown"]["v4"]["N261"]["all"], {"hit@1": 80, "hit@3": 96, "hit@5": 102}),
        ("T1-6 Clean-220 v4 all hit@1", t16["breakdown"]["v4"]["N220"]["all"]["hit@1"], 76),
        ("T1-6 N261 v6 ex_rec_only hit@1", t16["breakdown"]["v6"]["N261"]["ex_rec_only"]["hit@1"], 72),
        ("T1-6 N261 v6 ex_self", t16["breakdown"]["v6"]["N261"]["ex_self"], {"hit@1": 57, "hit@3": 63, "hit@5": 72}),
        ("T1-6 Clean-220 v6 ex_self hit@1", t16["breakdown"]["v6"]["N220"]["ex_self"]["hit@1"], 56),
        ("NoSelf_11p self_check.n_diffs == 0", ns["score_disclosure_self_check"]["n_diffs"], 0),
        ("NoSelf_11p self_check.neutralization.ok", ns["score_disclosure_self_check"]["neutralization_ok"], True),
        ("NoSelf_11p subprocess v6 all", ns["subprocess_v6_matched_product_hit"], {"hit@1": 94, "hit@3": 127, "hit@5": 134}),
        ("NoSelf_11p subprocess v4 all", ns["subprocess_v4_matched_product_hit"], {"hit@1": 61, "hit@3": 87, "hit@5": 93}),
        ("NoSelf_11p N261 v6 all", ns["breakdown"]["v6"]["N261"]["all"], {"hit@1": 94, "hit@3": 127, "hit@5": 134}),
        ("NoSelf_11p Clean-220 v6 all", ns["breakdown"]["v6"]["N220"]["all"], {"hit@1": 90, "hit@3": 120, "hit@5": 126}),
        ("NoSelf_11p N261 v4 all", ns["breakdown"]["v4"]["N261"]["all"], {"hit@1": 61, "hit@3": 87, "hit@5": 93}),
        ("NoSelf_11p Clean-220 v4 all hit@1", ns["breakdown"]["v4"]["N220"]["all"]["hit@1"], 58),
        ("NoSelf_11p N261 v6 ex_rec_only == all", ns["breakdown"]["v6"]["N261"]["ex_rec_only"], {"hit@1": 94, "hit@3": 127, "hit@5": 134}),
        ("NoSelf_11p N261 v6 ex_self", ns["breakdown"]["v6"]["N261"]["ex_self"], {"hit@1": 70, "hit@3": 97, "hit@5": 103}),
        ("NoSelf_11p Clean-220 v6 ex_self hit@1", ns["breakdown"]["v6"]["N220"]["ex_self"]["hit@1"], 66),
        ("cross n_t16_all_self_61", cross["n_t16_all_self_61"], 61),
        ("cross t16_self_61_trigger_breakdown", cross["t16_self_61_trigger_breakdown"], {"rec_only": 46, "tpl_only": 15}),
        ("cross noself hit1 on 61", cross["t16_noself_11p_on_self_61"]["hit1_all"], 43),
        ("cross noself top5 on 61", cross["t16_noself_11p_on_self_61"]["top5_all"], 56),
        ("cross noself strict ex_tpl on 61", cross["t16_noself_11p_on_self_61"]["hit1_strict_ex_tpl"], 20),
        ("cross noself own drop", cross["t16_noself_11p_own_drop_count"], 24),
        ("cross noself own drop breakdown", cross["t16_noself_11p_own_trigger_breakdown"], {"tpl_only": 24}),
    ]
    failures = [
        f"{name}: expected {expected!r}, got {actual!r}"
        for name, actual, expected in checks
        if actual != expected
    ]
    if failures:
        raise AssertionError("Anchor verification failed:\n  - " + "\n  - ".join(failures))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", default="", help="解压后的复算包根目录（含 arms/t1_6_full_118 与 arms/t1_6_noself_11p_94）")
    parser.add_argument("--t16-dir", default="", help="显式指定 T1-6 (118/261) 重放目录")
    parser.add_argument("--noself-dir", default="", help="显式指定 T1-6 NoSelf_11p (94/261) 重放目录")
    parser.add_argument("--work-dir", default="", help="score_disclosure_v4cn 临时输出目录（默认临时目录，用后不入仓）")
    parser.add_argument("--out-receipt", default="", help="输出纯脱敏机读回执 JSON 路径（零 SMILES、零私有题号）")
    parser.add_argument("--assert-anchors", action="store_true", help="对 118/261、94/261 与 self_61 做 fail-closed 硬断言")
    args = parser.parse_args(argv)

    if args.bundle_root:
        bundle = Path(args.bundle_root).resolve()
        t16_dir = Path(args.t16_dir).resolve() if args.t16_dir else bundle / "arms" / "t1_6_full_118"
        noself_dir = Path(args.noself_dir).resolve() if args.noself_dir else bundle / "arms" / "t1_6_noself_11p_94"
    else:
        if not args.t16_dir or not args.noself_dir:
            parser.error("必须提供 --bundle-root，或同时提供 --t16-dir 与 --noself-dir")
        t16_dir = Path(args.t16_dir).resolve()
        noself_dir = Path(args.noself_dir).resolve()

    scorers_before = verify_frozen_scorers(REPO_ROOT)

    tmp_ctx = None
    if args.work_dir:
        work_root = Path(args.work_dir).resolve()
        work_root.mkdir(parents=True, exist_ok=True)
    else:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="recompute_anchors_")
        work_root = Path(tmp_ctx.name)

    try:
        arm_specs = (("T1-6", t16_dir), ("T1-6_NoSelf_11p", noself_dir))
        arms_out: dict[str, Any] = {}
        per_q_by_arm: dict[str, dict[str, dict]] = {}
        for label, arm_dir in arm_specs:
            sub = _run_score_disclosure_subprocess(
                arm_dir=arm_dir,
                out_dir=work_root / label,
                repo_root=REPO_ROOT,
            )
            disc = sub["disclosure"]
            sc = sub["self_check"]
            breakdown = _evaluate_arm_breakdown(arm_dir)
            per_q_by_arm[label] = breakdown.pop("per_q")
            assert breakdown["v6"]["N261"]["all"] == disc["v4cn"]["matched_product_hit"], (
                f"{label} 进程内 v6 与子进程 score_disclosure_v4cn 不一致"
            )
            arms_out[label] = {
                "score_disclosure_self_check": {
                    "n_compared": sc["n_compared"],
                    "n_diffs": sc["n_diffs"],
                    "neutralization_ok": bool((sc.get("neutralization") or {}).get("ok")),
                    "idempotence_violations": int(
                        (sc.get("neutralization") or {}).get("n_idempotence_violations", -1)
                    ),
                },
                "subprocess_v4_matched_product_hit": disc["strict_v4"]["matched_product_hit"],
                "subprocess_v6_matched_product_hit": disc["v4cn"]["matched_product_hit"],
                "breakdown": breakdown,
            }

        cross = _compute_cross_dissection(per_q_by_arm["T1-6"], per_q_by_arm["T1-6_NoSelf_11p"])
        scorers_after = verify_frozen_scorers(REPO_ROOT)

        receipt: dict[str, Any] = {
            "schema": "v44-ablation-anchor-recompute-receipt-v1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "domain_tag": "biosysmodb121",
            "zero_llm_calls": True,
            "holdout_touched": False,
            "scorers_before": scorers_before,
            "scorers_after": scorers_after,
            "arms": arms_out,
            "cross_dissection": cross,
            "anchors_asserted": bool(args.assert_anchors),
        }

        if args.assert_anchors:
            _assert_anchor_values(receipt)

        if args.out_receipt:
            out_path = Path(args.out_receipt)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
