"""P1 build config + build info (chatgpt_p1_train.md §7.3)."""
from __future__ import annotations
import importlib.metadata
import json, sys
from reaction_agent.schemas.common import StrictModel, NonEmptyStr

class BuildConfig(StrictModel):
    input_source: NonEmptyStr
    output_snapshot_root: NonEmptyStr
    mapper_backend: NonEmptyStr
    mapper_version: NonEmptyStr
    mapper_parameters: dict[str, str] = {}
    normalization_version: NonEmptyStr
    role_policy_version: NonEmptyStr
    lineage_resolver_version: NonEmptyStr
    ledger_version: NonEmptyStr
    eligibility_policy_version: NonEmptyStr
    random_seed: int
    timeout: int = 300
    strict_mode: bool = True

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)

class BuildInfo(StrictModel):
    package_version: NonEmptyStr
    schema_version: NonEmptyStr
    mapper_resolver_version: NonEmptyStr
    ledger_version: NonEmptyStr
    policy_version: NonEmptyStr
    python_version: NonEmptyStr

def _package_version() -> str:
    """单源化 package_version 取自 importlib.metadata (MINOR-2)。

    pyproject.toml 是唯一版本源；metadata 缺失（未 ``pip install``）时
    fallback "0.0.0"，避免硬编码与 pyproject 漂移。
    """
    try:
        return importlib.metadata.version("reaction-analogy-agent")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"

def get_build_info() -> BuildInfo:
    return BuildInfo(
        package_version=_package_version(),
        schema_version="p1-1",
        mapper_resolver_version="p1-1",
        ledger_version="p1-1",
        policy_version="p1-1",
        python_version=".".join(str(x) for x in sys.version_info[:3]),
    )
