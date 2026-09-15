# EnzymeCrew 配置
# 环境变量从 .env 或系统环境读取，不硬编码

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# ---------- LLM ----------
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_CONFIG_PATH = PROJECT_ROOT / "config" / "llm_config.yaml"

# ---------- EnzymeCAGE 调用（M3I6-A：晨羽同环境 Python import） ----------
# 部署到晨羽后，以下三个路径必须由学生 onboarding 时提供稳定绝对路径。
# 本地开发时可留空（enzymecage_client 会走 mock/dry-run）。
D4_WRAPPER_ROOT = os.getenv("D4_WRAPPER_ROOT", "")
ENZYMECAGE_CODE_ROOT = os.getenv("ENZYMECAGE_CODE_ROOT", "")
ENZYMECAGE_V1_PACKAGE_ROOT = os.getenv("ENZYMECAGE_V1_PACKAGE_ROOT", "")

# 冻结底座权重单一事实源（Hugging Face）；未配 ENZYMECAGE_V1_PACKAGE_ROOT 时，
# enzymecage_client 会回退到 HF snapshot_download（首次下载，之后本地缓存复用）
ENZYMECAGE_HF_REPO = os.getenv("ENZYMECAGE_HF_REPO", "WQRCE/EnzymeCAGE-v1")

# 冻结模型版本（不改动）
ENZYMECAGE_MODEL_VERSION = "v1_20260714"

# EnzymeCAGE Python 契约参数
ENZYMECAGE_TOP_K = 10
ENZYMECAGE_RETURN_CI = True

# 本地 dry-run 开关：ENZYMECAGE_DRY_RUN=1 时不真正 import wrapper，
# 用 mock 返回，供不在晨羽环境的本地开发与 CI 使用
ENZYMECAGE_DRY_RUN = os.getenv("ENZYMECAGE_DRY_RUN", "0") == "1"

# ---------- 数据资产路径 ----------
# 学生 tar.gz 解压后的 assets/ 目录（学生原始层级）
# 晨羽稳定路径：
#   /root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/assets/
# 本地开发时通过环境变量指向解压后的 assets/ 目录
DATA_ASSETS_ROOT = Path(os.getenv(
    "M3_AGENT_DATA_ASSETS_ROOT",
    str(PROJECT_ROOT / "data" / "m3_agent_data_assets" / "assets"),
))

# #2 Rhea 140 四个 TSV（与学生 tar.gz 内 assets/rhea140/ 对齐）
RHEA_DIR = DATA_ASSETS_ROOT / "rhea140"
RHEA_DIRECTIONS_TSV = RHEA_DIR / "rhea-directions.tsv"
RHEA2EC_TSV = RHEA_DIR / "rhea2ec.tsv"
RHEA2UNIPROT_SPROT_TSV = RHEA_DIR / "rhea2uniprot_sprot.tsv"
RHEA_REACTION_SMILES_TSV = RHEA_DIR / "rhea-reaction-smiles.tsv"

# #3 route-C 参考反应索引 + Morgan radius=8 指纹（gz 直读）
ROUTE_C_DIR = DATA_ASSETS_ROOT / "route_c"
REFERENCE_REACTION_INDEX_PATH = ROUTE_C_DIR / "reference_reaction_index.csv.gz"
REFERENCE_MORGAN_RADIUS8_PATH = ROUTE_C_DIR / "reference_morgan_radius8.pkl"

# #4 D4 UID 资产可用性表（107,705 完整资产 UID）
D4_DIR = DATA_ASSETS_ROOT / "d4"
D4_UID_AVAILABILITY_PATH = D4_DIR / "uid_asset_availability.csv.gz"

# #5 公平 query-excluded EC → UID 表（route-B pool 来源）
ROUTE_B_DIR = DATA_ASSETS_ROOT / "route_b"
EC_TO_UID_QUERY_EXCLUDED_PATH = ROUTE_B_DIR / "ec_to_uid_query_excluded.csv.gz"

# ---------- Case 配置 ----------
# 学生 6.1 交付：三个正式 case YAML/JSON
CASES_DIR = PROJECT_ROOT / "cases"

# ---------- pool 约束 ----------
MAX_POOL_SIZE = 100               # pool >100 fail closed（M3D2 硬约束）

# ---------- Pipeline 模式 ----------
DEFAULT_PIPELINE_MODE = "m3"      # "m3" | "m5"

# ---------- M5: Enzyme2Organism 远程服务（M5 铺垫，M3 不使用） ----------
ENZYME2ORGANISM_API_URL = os.getenv("ENZYME2ORGANISM_API_URL", "http://localhost:8001/api/v1/enzyme2organism")
ENZYME2ORGANISM_TIMEOUT_SEC = 30

# ---------- M5: metaTraits ----------
METATRAITS_DATA_DIR = PROJECT_ROOT / "data" / "metatraits"
METATRAITS_DOWNLOAD_URL = "https://metatraits.de/download"
