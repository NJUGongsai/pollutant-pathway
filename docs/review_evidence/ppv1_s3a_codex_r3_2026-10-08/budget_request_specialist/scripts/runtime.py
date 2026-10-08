from pathlib import Path
import json,sqlite3,sys
import rdkit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source/src'))
from pathway_v43.pollutant.profile import PPV1_SEARCH_SCHEMA_VERSION,PPV1_PROFILE_SCHEMA_VERSION,SEARCH_LIMITS_VERSION
from pathway_v43.pollutant.store import PPV1_STORE_SCHEMA_VERSION
print(json.dumps({'python':sys.version,'rdkit':rdkit.__version__,'sqlite':sqlite3.sqlite_version,'schema':{'search':PPV1_SEARCH_SCHEMA_VERSION,'profile':PPV1_PROFILE_SCHEMA_VERSION,'limits':SEARCH_LIMITS_VERSION,'store':PPV1_STORE_SCHEMA_VERSION},'network_requests':0,'external_model_calls':0},sort_keys=True))
