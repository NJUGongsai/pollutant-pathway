"""enviPath donor parsing — source_substrates.json (read-only)."""
import json
import logging

from ra.chem import ChemParseError, canonical_smiles

logger = logging.getLogger(__name__)


def load_envipath_donors(json_path: str) -> tuple:
    """Load the enviPath donor-substrate file.

    Entry: {substrates: [smiles,...], verified: bool}. Each substrate is one
    donor record (canonicalised, deduped per template). Fail-closed: unparseable
    substrates are reported through the second element of the returned tuple.
    """
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    records: list = []
    parse_failed: list = []
    for key in sorted(data):
        entry = data[key]
        if not isinstance(entry, dict):
            continue
        substrates = entry.get("substrates") or []
        seen = set()
        for s in substrates:
            try:
                canon = canonical_smiles(s)
            except ChemParseError as exc:
                parse_failed.append({"source_id": key, "smiles": s, "error": str(exc)})
                continue
            if canon in seen:
                continue
            seen.add(canon)
            records.append({"source_id": key, "educt": canon, "verified": bool(entry.get("verified"))})
    return records, parse_failed