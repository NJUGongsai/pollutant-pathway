"""晨羽端：探 RHEA:46976 在 D4 pool / route_c index 里的存在情况，
决定 Case 1 官方 realrun 走 route B 还是 route C。"""
import gzip, csv, json, os

route_c_index = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/assets/route_c/reference_reaction_index.csv.gz"
route_b_dir = "/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/assets/route_b"

print("=== route_b 目录:")
for x in sorted(os.listdir(route_b_dir))[:20]:
    print(" ", x)

print()
print("=== 在 route_c index 里查 46976:")
with gzip.open(route_c_index, "rt", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    print("fields =", reader.fieldnames)
    hits = []
    for i, row in enumerate(reader):
        rmids = row.get("rhea_master_ids_json") or ""
        rids = row.get("rhea_ids_json") or ""
        if "46976" in rmids or "46976" in rids:
            uids_json = row.get("d4_valid_uids_json") or "[]"
            try:
                uids = json.loads(uids_json)
            except:
                uids = []
            hits.append({
                "line": i,
                "rxn_sha": (row.get("reaction_sha256") or "")[:16],
                "rxn_smiles": (row.get("CANO_RXN_SMILES") or "")[:120],
                "rhea_master_ids": rmids[:100],
                "rhea_ids": rids[:100],
                "d4_uids_count": len(uids),
                "first_uids": uids[:8],
            })
    print(f"命中 {len(hits)} 行:")
    for h in hits:
        print(json.dumps(h, ensure_ascii=False, indent=2))

# 并查 route_b 里对应 UID 的 embedding 是否已算过
print()
print("=== 查 route_b: 是否已包含 RHEA:46976 的 D4 UID embedding?")
d4_json_candidates = [f for f in os.listdir(route_b_dir) if f.endswith(".json") or "d4" in f.lower() or "reaction" in f.lower()]
for f in d4_json_candidates[:5]:
    print(" ", f)
