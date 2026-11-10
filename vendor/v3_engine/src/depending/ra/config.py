"""Read-only source paths (never modified) + output conventions."""
import os

DEPENDING = "/Volumes/CC/Enzyme_Agent/depending"

RHEA_RXN_DIR = os.path.join(DEPENDING, "demov3/data/rhea/rxn_subset/rxn")
RHEA_SMILES_TSV = os.path.join(DEPENDING, "demov3/data/rhea/rhea-reaction-smiles.tsv")
RHEA2EC_TSV = os.path.join(DEPENDING, "demov3/data/rhea/rhea2ec.tsv")
RHEA_DIRECTIONS_TSV = os.path.join(DEPENDING, "demov3/data/rhea/rhea-directions.tsv")
ENVIPATH_JSON = os.path.join(DEPENDING, "reaction_v3/data/lib_envipath/source_substrates.json")
PARENTS_CSV = os.path.join(
    DEPENDING,
    "demov3/data/bbd83_blind_inputs/KNOWN_PATHWAY_POLLUTANT_BLIND_PARENT_INPUTS_V0_2.csv",
)

# output (inside this repo only)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CORPUS_DIR = os.path.join(DATA_DIR, "corpus_v1")
RETRIEVAL_DIR = os.path.join(DATA_DIR, "retrieval_v1")
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")

# retrieval defaults
RETRIEVAL_K = 20
FP_RADIUS = 2
FP_BITS = 2048