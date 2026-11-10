"""EAWAG-BBD raw HTML parser (RA-S8).

Turns the frozen raw archive under data/bbd_expand/raw/{lists,rules,reactions,
compounds} into structured JSON.  Deterministic (sorted iteration, no network),
fail-closed (missing / malformed fields are recorded verbatim or as null, never
invented).

entity model
  rules     : btid -> {pattern_id, description, example_reacs[], aerobic}
  compounds : compID -> {name, smiles, formula}
  reactions : reacID -> {donor_compids[], product_compids[], donor_names[],
                         product_names[], rules[], ec[]}
"""
import html
import json
import os
import re

RE_IMG_PATTERN = re.compile(r"patterns/(\d+)\.png")
RE_REAC = re.compile(r"reacID=r(\d+)")
RE_RULE = re.compile(r"rule\.jsp\?rule=(bt\d+)")
RE_COMP_HREF = re.compile(r'href="[^"]*compID=c(\d+)"[^>]*>([^<]*)<')
RE_EC = re.compile(r"enzymeID=e\d+\"[^>]*>([\d.]+)\s*<")


def _deent(t):
    if t is None:
        return None
    return html.unescape(t).strip()


def _first(pat, text):
    m = re.search(pat, text)
    return m.group(1) if m else None


def parse_rule_page(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    out = {
        "pattern_id": _first(RE_IMG_PATTERN, t),
        "description": None,
        "example_reacs": sorted(set(RE_REAC.findall(t))),
        "aerobic": _aerobic(t),
    }
    for line in t.split("\n"):
        if "->" in line and "<br>" in line and "href" not in line and "rule.jsp" not in line:
            desc = re.sub(r"<[^>]+>", "", line).strip()
            if "->" in desc:
                lhs, rhs = desc.split("->", 1)
                out["description"] = f"{_deent(lhs)} -> {_deent(rhs)}"
            break
    return out


def _aerobic(t):
    if "Neutral" in t:
        return "neutral"
    if "Unlikely" in t or "Very unlikely" in t:
        return "unlikely"
    if "Very likely" in t or "Likely" in t:
        return "likely"
    return None


def parse_compound_page(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    # ignore "Malformed URL" error pages / no-content
    if "Malformed URL" in t and "SMILES" not in t:
        return None
    name = _first(r"<h1>\s*([^<]+?)\s*</h1>", t)
    smiles = _first(r"SMILES String:\s*([^<\n]+)", t)
    formula = _first(r"Formula:\s*(.*?)<p>", t)
    if formula is not None:
        formula = re.sub(r"<[^>]+>", "", formula).strip()
    if smiles is None:
        return {"name": _deent(name), "smiles": None, "formula": _deent(formula)}
    return {"name": _deent(name), "smiles": _deent(smiles), "formula": _deent(formula)}


def parse_reaction_page(path):
    """First compID link = donor; remaining = products. h1 gives names/direction.

    Multi-substrate ("From X and Y to Z") is detected and donor list split 2-way.
    """
    t = open(path, encoding="utf-8", errors="replace").read()
    if "Malformed URL" in t and "reacID" not in t and "compID" not in t:
        return None
    h1 = _first(r"<h1>\s*([^<]+?)\s*</h1>", t)
    comps = [(c, _deent(n)) for c, n in RE_COMP_HREF.findall(t)]
    rules = sorted(set(RE_RULE.findall(t)))
    ecs = sorted(set(RE_EC.findall(t)))
    # split donor / product(s)
    # count donors from h1 "From A (and B) to C (and D)"
    donor_names, product_names = [], []
    if h1 and h1.startswith("From ") and " to " in h1:
        head = h1[len("From "):]
        lhs, rhs = head.split(" to ", 1)
        donor_names = [x.strip() for x in _split_names(lhs)]
        product_names = [x.strip() for x in _split_names(rhs)]
    n_donor = max(1, len(donor_names))
    if n_donor > 1:
        donor_comps = [c for c, _n in comps[:n_donor]]
        product_comps = [c for c, _n in comps[n_donor:]]
    elif len(comps) >= 2:
        donor_comps = [comps[0][0]]
        product_comps = [c for c, _n in comps[1:]]
    elif len(comps) == 1:
        donor_comps = [comps[0][0]]
        product_comps = []
    else:
        donor_comps = []
        product_comps = []
    return {
        "h1": _deent(h1),
        "donor_compids": donor_comps,
        "product_compids": product_comps,
        "donor_names": donor_names,
        "product_names": product_names,
        "rules": rules,
        "ec": ecs,
    }


def _split_names(s):
    # split "X and Y" -> [X, Y] (last 'and' only, to keep names with inner 'and')
    parts = re.split(r"\s+and\s+(?=[^)]*$)", s)
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# full-archive parse drives
# ---------------------------------------------------------------------------

def parse_archive(raw_dir):
    rules = {}
    rules_dir = os.path.join(raw_dir, "rules")
    for fn in sorted(os.listdir(rules_dir)):
        if not fn.endswith(".html"):
            continue
        btid = fn[:-5]
        p = parse_rule_page(os.path.join(rules_dir, fn))
        if p is None:
            p = {"pattern_id": None, "description": None, "example_reacs": [], "aerobic": None}
        rules[btid] = p

    compounds = {}
    comps_dir = os.path.join(raw_dir, "compounds")
    if os.path.isdir(comps_dir):
        for fn in sorted(os.listdir(comps_dir)):
            if not fn.endswith(".html"):
                continue
            cid = fn[:-5]
            p = parse_compound_page(os.path.join(comps_dir, fn))
            compounds[cid] = p if p else {"name": None, "smiles": None, "formula": None}

    reactions = {}
    reacs_dir = os.path.join(raw_dir, "reactions")
    if os.path.isdir(reacs_dir):
        for fn in sorted(os.listdir(reacs_dir)):
            if not fn.endswith(".html"):
                continue
            rid = fn[:-5]
            p = parse_reaction_page(os.path.join(reacs_dir, fn))
            reactions[rid] = p if p else {
                "donor_compids": [], "product_compids": [], "donor_names": [],
                "product_names": [], "rules": [], "ec": [],
            }
    return {"rules": rules, "compounds": compounds, "reactions": reactions}


def write_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
    return path