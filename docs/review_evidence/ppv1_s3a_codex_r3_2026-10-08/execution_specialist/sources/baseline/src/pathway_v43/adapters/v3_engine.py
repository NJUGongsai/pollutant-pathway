"""v3 冻结引擎只读适配器 — 资产根导入前注入 + 进程内资产身份守卫。

桥接配方逐字镜像 v4 ``pathway_agent/engine.py`` 的 init / expand / serialize
逻辑(同一引擎实现是对拍一致的前提),唯一结构性差异:

1. 任何 v3 引擎模块导入之前,先把 ``dp_paths.ASSETS`` 重绑到
   ``V43_ASSET_ROOT/v3_reactions`` —— v3 的 expand_bbd_routes 在导入时通过
   dp.asset 绑定 TEMPLATES / ENVIPATH_RULES / ENVIPATH_TSV / CORPUS_DIR /
   MODEL_DIR,dp_paths.asset() 在调用时动态读模块级 ASSETS,因此这一处重绑
   即让全部实际读取落在本仓资产下(不修改 v3 源文件,不改旧仓资产目录)。
2. ``DEPENDING_V3_ROOT`` 指向 v3 代码根(与 v4 同语义,仅用于 REPO_ROOT,
   不参与资产解析);资产根由本适配器显式传给原版
   ``env_asset_root.resolve_and_verify`` —— 代码根与资产根解耦。
3. 进程内资产身份守卫:dp_paths/引擎模块的导入时绑定与 LightGBM 等进程全局
   模型对象不可卸载,本进程一旦加载过某套资产身份,再请求不同身份即拒绝
   (结构化错误,提示用隔离子进程);同身份重复初始化返回同一实例。
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
from pathlib import Path

from pathway_v43.adapters.asset_manifest import (
    ANALOG_INDEX_FILES,
    EXTENSION_FILES,
    AssetManifestError,
    analog_index_shas,
    extension_file_shas,
    sha256_file,
    verify_repo_manifest,
)

_LOCK = threading.Lock()
_BINDING: dict | None = None  # 进程当前绑定的资产身份与引擎实例
_LAST_KEY: tuple | None = None  # 最近一次绑定的身份(reset 后用于同身份重初始化)

# v3 引擎链上会在导入时绑定资产路径/模型对象的模块(出现任何一个都说明本进程
# 已有 v3 状态;env_asset_root 是纯函数模块不缓存路径,靠加载后 __file__ 溯源把关)
_ENGINE_CHAIN_MODULES = (
    "dp_paths",
    "bbd_v33_fusion",
    "eawag_lookup",
    "expand_bbd_routes",
    "single_smiles_v32",
    "eawag_rules_engine",
    "single_smiles_hybrid",
)

# v4 序列化省略、但 v4.3 按任务书保留的来源字段(单独检查,不计入对拍差异)
EXTRA_SOURCE_FIELDS = (
    "donor_exact_match",
    "n_evidence",
    "cofactor_filtered",
    "filtered",
    "product_smiles_full",
    "tanimoto",
)


class EngineBootstrapError(RuntimeError):
    """引擎加载/身份守卫失败(fail-closed)。detail 携带结构化信息。"""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def _sb(smi: str) -> str | None:
    """立体盲 canonical(镜像 v4 engine._sb / v3 predict_env_batch_v35.sb_)。"""
    from rdkit import Chem

    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m else None


def _realpath(p: str | Path) -> str:
    return os.path.realpath(str(p))


def _require_under(root: str | Path, path: str | Path, what: str) -> None:
    rp, pp = Path(_realpath(root)), Path(_realpath(path))
    if pp != rp and rp not in pp.parents:
        raise EngineBootstrapError(
            f"{what} 路径逃逸:{path} 不在 {root} 下",
            {"root": str(rp), "path": str(pp), "what": what},
        )


def v3_code_identity(v3_code_root: str | Path) -> dict:
    """v3 引擎代码身份(git 提交/分支/脏标记;只读探查,失败如实降级为 unknown)。"""
    root = Path(v3_code_root)
    info: dict = {"v3_code_root": str(root.resolve())}

    def _git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
        except Exception:
            return None
        return out.stdout.strip() or None

    commit = _git("rev-parse", "HEAD")
    if commit is None:
        info.update({"git_commit": None, "git_available": False})
        return info
    dirty = _git("status", "--porcelain")
    info.update(
        {
            "git_commit": commit,
            "git_branch": _git("branch", "--show-current"),
            "git_dirty": bool(dirty),
            "git_available": True,
        }
    )
    return info


def _identity_key(config) -> tuple:
    """资产身份键(检索资产 + 引擎代码);不含模拟环境差异。"""
    manifest = verify_repo_manifest(config.assets_root)
    code = v3_code_identity(config.v3_code_root)
    return (
        _realpath(config.assets_root),
        manifest["manifest_sha256"],
        _realpath(config.v3_code_root),
        code.get("git_commit"),
    )


def _no_v3_modules_loaded(requested_key: tuple) -> None:
    """进程内已加载 v3 模块时的身份守卫。

    - 请求身份 == 最近一次绑定的身份:允许重初始化(同一资产根重新走
      完整校验与装载,确定性安全);
    - 请求身份不同或未知:拒绝 —— 导入时路径绑定与 LightGBM 等进程全局
      模型不可卸载,跨身份必须用隔离子进程。
    """
    loaded = [name for name in _ENGINE_CHAIN_MODULES if name in sys.modules]
    if not loaded:
        return
    if _LAST_KEY is not None and requested_key == _LAST_KEY:
        return
    if _LAST_KEY is not None:
        raise EngineBootstrapError(
            "本进程已加载 v3 引擎模块且请求了另一套资产身份,无法保证资产根"
            f"注入失效与全局模型不复用:{loaded}。请对第二套资产身份使用"
            "隔离子进程(scripts/compare_asset_roots.py 即按此运行)。",
            {"loaded_modules": loaded, "requested_key": requested_key[:2]},
        )
    raise EngineBootstrapError(
        "本进程已加载 v3 引擎模块但身份未知(绑定已被丢弃),拒绝盲目重载:"
        f"{loaded}。请使用隔离子进程。",
        {"loaded_modules": loaded},
    )


class _StdoutToStderr:
    """v3 冻结模块装载期 print() 的横幅改道 stderr,保持 stdout 只有 CLI JSON。"""

    def write(self, s: str) -> int:
        return sys.stderr.write(s)

    def flush(self) -> None:
        sys.stderr.flush()


class V43Engine:
    """v3.5 冻结引擎的进程内只读包装。通过 get_engine() 获取(身份守卫)。"""

    def __init__(self, config) -> None:
        from pathway_v43.config import V43Config

        if not isinstance(config, V43Config):  # 防误传字符串路径
            raise EngineBootstrapError(
                "V43Engine 需要 V43Config(用 resolve_config 构造)",
                {"got": type(config).__name__},
            )
        self.config = config
        run_root = config.v3_run_root

        # ---- 0. 本仓清单校验先于一切 v3 导入(fail-closed,无回退) ----
        self.manifest_identity = verify_repo_manifest(config.assets_root)

        # ---- 1. 进程交叉守卫:请求身份与已加载 v3 模块的一致性 ----
        _no_v3_modules_loaded(_identity_key(config))

        # ---- 2. 导入前注入:env(sys.path 在 import dp_paths 前就位) ----
        os.environ["DEPENDING_V3_ROOT"] = str(config.v3_code_root)
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        depending_dir = config.v3_depending_dir
        if not depending_dir.is_dir():
            raise EngineBootstrapError(
                f"v3 引擎目录缺失:{depending_dir}",
                {"v3_code_root": str(config.v3_code_root.resolve())},
            )
        if str(depending_dir) not in sys.path:
            sys.path.insert(0, str(depending_dir))

        import dp_paths as dp  # v3 冻结模块,只 import 不改

        if _realpath(dp.REPO_ROOT) != _realpath(config.v3_code_root):
            raise EngineBootstrapError(
                "dp_paths.REPO_ROOT 与 v3 代码根错位(可能被抢先导入):"
                f"{dp.REPO_ROOT} != {config.v3_code_root}",
                {"repo_root": dp.REPO_ROOT},
            )
        # ← 唯一接线点:此后 dp.asset(...) 全部落在本仓 v3_reactions 下
        dp.ASSETS = str(run_root)

        import env_asset_root as EAR  # v3 冻结模块,只 import 不改

        # 原版校验,显式传本仓运行根;其返回的每个 *_path 必须位于配置的
        # assets 根(物理边界)下 —— run_root 若是 symlink 指向旧仓,这里会以
        # 物理路径不符拒绝
        try:
            identity_block = EAR.resolve_and_verify(str(run_root))
        except Exception as exc:
            raise EngineBootstrapError(
                f"v3 资产校验失败(fail-closed, run_root={run_root}):{exc}",
                {"run_root": str(run_root.resolve())},
            ) from exc
        physical_boundary = str(config.assets_root.resolve())
        for key, value in sorted(identity_block.items()):
            if key.endswith("_path"):
                _require_under(physical_boundary, value, f"v3 核心资产 {key}")

        import bbd_v33_fusion as V33  # noqa: F401 — expand_raw 合并段使用
        import eawag_lookup as EGD  # noqa: F401
        import expand_bbd_routes as X  # noqa: F401
        import single_smiles_v32 as S  # noqa: F401

        # 导入溯源:链上模块必须来自本 v3 代码根(防同名模块被其它副本抢先占用)
        expected_dir = _realpath(depending_dir) + os.sep
        for mod_name, mod in (
            ("dp_paths", dp), ("env_asset_root", EAR),
            ("bbd_v33_fusion", V33), ("eawag_lookup", EGD),
            ("expand_bbd_routes", X), ("single_smiles_v32", S),
        ):
            mod_file = _realpath(getattr(mod, "__file__", ""))
            if not mod_file.startswith(expected_dir):
                raise EngineBootstrapError(
                    f"v3 模块 {mod_name} 来自其它位置:{mod_file}"
                    f"(期望 {expected_dir})",
                    {"module": mod_name, "file": mod_file},
                )

        # ---- 3. init 段(镜像 v4 engine.py:63-74 的顺序与取值) ----
        # v3 装载期会向 stdout print 横幅;改道 stderr,保证 stdout 只有 CLI JSON
        with contextlib.redirect_stdout(_StdoutToStderr()):
            corpus_dir = os.path.dirname(identity_block["corpus_v1_path"])
            library = identity_block["library_path"]
            X.MODEL_DIR = os.path.dirname(identity_block["ranker_uspto_path"])
            X.set_calibrator_path(EAR.calibrator_path(identity_block, "v35"), "v35")
            X.CORPUS_DIR = corpus_dir
            self.load_stats = S.load_engines()
            X._G_SCORING = "v35"
            S.setup_v34(no_policy=False)
            self.lookup_index = EGD.build_index(library)
        self.lookup_index.pop("__parse_fail__", None)
        self._EAR, self._V33, self._EGD, self._X, self._S = EAR, V33, EGD, X, S
        self.identity_block = identity_block

        # ---- 4. 装载后路径断言(纵深防御:X.* 与导入时绑定都须在本仓根下) ----
        self._assert_loaded_paths()

    # ------------------------------------------------------------ 校验

    def _assert_loaded_paths(self) -> None:
        # 物理边界 = 配置的 assets_root(resolve 后);run_root 是其子目录。
        # run_root 本身若是 symlink,resolve 后的旧仓路径会落在边界外 → 拒绝。
        boundary = self.config.assets_root.resolve()
        X = self._X
        loaded = {
            "X.TEMPLATES": X.TEMPLATES,
            "X.ENVIPATH_RULES": X.ENVIPATH_RULES,
            "X.ENVIPATH_TSV": X.ENVIPATH_TSV,
            "X.CORPUS_DIR": X.CORPUS_DIR,
            "X.MODEL_DIR": X.MODEL_DIR,
            "X._G_V34_CALIB_PATH": X._G_V34_CALIB_PATH or "",
            "identity.library_path": self.identity_block["library_path"],
            "identity.corpus_v1_path": self.identity_block["corpus_v1_path"],
            "identity.calibrator_v35_path": self.identity_block["calibrator_v35_path"],
        }
        for name, path in sorted(loaded.items()):
            if not path:
                raise EngineBootstrapError(f"引擎装载路径为空:{name}", {"path": path})
            _require_under(boundary, path, f"引擎装载路径 {name}")

    def asset_identity(self) -> dict:
        """检索资产身份与引擎代码身份的完整块(checkenv/probe/run_identity 素材)。"""
        config = self.config
        core = {}
        for key, value in sorted(self.identity_block.items()):
            if key.endswith("_path"):
                stem = key[: -len("_path")]
                core[stem] = {
                    "path": str(Path(value).resolve()),
                    "sha256": self.identity_block.get(f"{stem}_sha256"),
                    "bytes": self.identity_block.get(f"{stem}_bytes"),
                }
        return {
            "retrieval_assets": {
                "assets_root": str(config.assets_root.resolve()),
                "manifest_sha256": self.manifest_identity["manifest_sha256"],
                "n_manifest_files": self.manifest_identity["n_files"],
                "v3_run_root": str(config.v3_run_root.resolve()),
                "core_files": core,
                "extension_files": extension_file_shas(self.manifest_identity),
                "analog_index_files": analog_index_shas(self.manifest_identity),
            },
            "engine_code": v3_code_identity(config.v3_code_root),
        }

    # ------------------------------------------------------------ 桥接口(镜像 v4)

    def cn_identity(self, smiles: str) -> str:
        """电荷归一化立体盲 canonical(v3 引擎口径;解析失败原样返回)。"""
        return self._X._identity(smiles) or smiles  # noqa: SLF001 — 桥接层例外

    def serialize_edge(self, e: dict, rank: int) -> dict:
        """镜像 v4 V3Engine.serialize_edge(冻结链兼容字段),另透传来源字段。"""
        out = {
            "rank": rank,
            "layer": e.get("layer", "prediction"),
            "product_smiles": e["product_smiles"],
            "product_identity": e.get("product_identity", e["product_smiles"]),
            "source": e.get("source", ""),
            "score": e.get("edge_score", e.get("tanimoto", 0.0)),
            "score_semantics": e.get(
                "score_semantics",
                "eawag_lookup_tanimoto" if e.get("layer") == "lookup" else "",
            ),
            "v34_regime": e.get("v34_regime", ""),
            "eawag_reactions": e.get("eawag_reactions", []),
            "p_uspto": e.get("p_uspto", 0.0),
            "p_envipath": e.get("p_envipath", 0.0),
            "p_retrieval": e.get("p_retrieval", 0.0),
            "ion_filtered": e.get("ion_filtered", False),
            "wildcard_filtered": e.get("wildcard_filtered", False),
            "charge_variants": e.get("charge_variants", []),
        }
        for field in EXTRA_SOURCE_FIELDS:  # v4.3 新增透传(对拍单独检查)
            if field in e:
                out[field] = e[field]
        return out

    def expand_raw(self, smiles: str, case_id: str = "case") -> dict:
        """单底物原始展开(engine edges + eawag lookup,未合并)。镜像 v4。"""
        from rdkit import Chem

        if Chem.MolFromSmiles(smiles) is None:
            return {"error": "unparseable_parent", "smiles": smiles}
        X, S, EGD, V33 = self._X, self._S, self._EGD, self._V33
        root_identity = X._identity(smiles) or smiles  # noqa: SLF001
        node = {
            "node_id": X._node_id(case_id, 0, root_identity),  # noqa: SLF001
            "case_id": case_id,
            "depth": 0,
            "smiles": smiles,
            "canonical_smiles": root_identity,
            "is_root": True,
            "ancestor_canons": set(),
            "path_score": 1.0,
        }
        S.attach_retrieval([node])
        res = S.expand_node(node)
        pred = list(res["edges"])
        look = EGD.lookup(self.lookup_index, smiles)
        # 合并段(镜像 v4 / predict_env_batch_v35:lookup 置顶 + 预测去重)
        look_canons = {
            _sb(V33.normalize_charge_smiles(c["product_smiles"]) or c["product_smiles"])
            for c in look
        }
        pred_dedup = [
            e
            for e in pred
            if _sb(
                V33.normalize_charge_smiles(e["product_smiles"]) or e["product_smiles"]
            )
            not in look_canons
        ]
        merged = list(look) + pred_dedup if look else pred
        return {
            "smiles": smiles,
            "canonical_smiles": root_identity,
            "lookup": look,
            "pred_edges": pred,
            "merged_edges": merged,
            "n_pred_candidates": len(pred),
            "n_lookup": len(look),
            "budget_cut": bool(res.get("budget_cut")),
            "pool_capped": bool(res.get("pool_capped")),
        }

    def expand_merged(self, smiles: str, case_id: str = "case") -> dict:
        """单底物 hybrid 候选池(合并、1 起始排名、冻结链兼容序列化)。镜像 v4。"""
        raw = self.expand_raw(smiles, case_id)
        if "error" in raw:
            return raw
        candidates = [
            self.serialize_edge(e, rank)
            for rank, e in enumerate(raw["merged_edges"], start=1)
        ]
        return {
            "smiles": raw["smiles"],
            "canonical_smiles": raw["canonical_smiles"],
            "n_pred_candidates": raw["n_pred_candidates"],
            "n_lookup": raw["n_lookup"],
            "lookup_hit": raw["n_lookup"] > 0,
            "budget_cut": raw["budget_cut"],
            "candidates": candidates,
        }

    def predict(
        self, smiles: str, case_id: str = "case", top_k: int | None = None
    ) -> list[dict]:
        """契约入口:hybrid 池 → 候选列表(cand_id/engine_rank 1 起始)。

        不可解析输入 fail-closed 抛错,不返回半空池(镜像 v4 语义)。
        """
        exp = self.expand_merged(smiles, case_id)
        if "error" in exp:
            raise EngineBootstrapError(
                f"predict 失败:{exp['error']}({smiles!r})", {"smiles": smiles}
            )
        out: list[dict] = []
        for i, cand in enumerate(exp["candidates"], start=1):
            row = dict(cand)
            row["cand_id"] = f"e{i}"
            row["engine_rank"] = i
            out.append(row)
            if top_k is not None and i >= top_k:
                break
        return out


def get_engine(config) -> V43Engine:
    """进程内引擎单例(同资产身份复用;不同身份拒绝,须用隔离子进程)。"""
    global _BINDING, _LAST_KEY
    with _LOCK:
        key = _identity_key(config)
        if _BINDING is not None:
            if _BINDING["key"] == key:
                return _BINDING["engine"]
            raise EngineBootstrapError(
                "本进程已绑定另一套资产身份,拒绝复用导入时绑定的路径与全局模型:"
                f"已绑定 assets={_BINDING['key'][0]} "
                f"manifest={_BINDING['key'][1]};"
                f"请求 assets={key[0]} manifest={key[1]}。"
                "请用隔离子进程(scripts/compare_asset_roots.py 的双臂即如此)。",
                {
                    "bound": {
                        "assets_root": _BINDING["key"][0],
                        "manifest_sha256": _BINDING["key"][1],
                    },
                    "requested": {
                        "assets_root": key[0],
                        "manifest_sha256": key[1],
                    },
                },
            )
        engine = V43Engine(config)
        _BINDING = {"key": key, "engine": engine}
        _LAST_KEY = key
        return engine


def reset_engine() -> None:
    """测试钩子:丢弃绑定(不卸载已 import 的 v3 模块)。

    reset 后同身份可重新初始化(V43Engine 全程重新校验与装载,确定性
    安全);跨身份仍被守卫拒绝。
    """
    global _BINDING
    with _LOCK:
        _BINDING = None
