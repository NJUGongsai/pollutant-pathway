import httpx, time
for name in ["(S)-6-hydroxynicotine", "hexane", "tartaric acid"]:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/SMILES,InChIKey/JSON"
    t0 = time.time()
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True)
        dt = time.time() - t0
        print(f"[{dt:5.2f}s] [{r.status_code}] {name}")
        if r.status_code == 200:
            p = r.json()["PropertyTable"]["Properties"][0]
            print(f"    SMILES={p.get('SMILES')}  InChIKey={p.get('InChIKey')}")
    except Exception as e:
        print(f"ERR {name}: {type(e).__name__}: {e}")
