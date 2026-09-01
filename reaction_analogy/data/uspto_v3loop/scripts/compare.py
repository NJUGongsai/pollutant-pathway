import json, sys
def cmp(orig_path, new_path):
    a = json.load(open(orig_path)); b = json.load(open(new_path))
    assert len(a['dump']) == len(b['dump']), 'dump length mismatch'
    n_c = n_match = n_mis = n_o0r = n_n0o = 0
    maxd = 0.0; other_diff = 0
    for ca, cb in zip(a['dump'], b['dump']):
        assert ca['lhs'] == cb['lhs']
        for xa, xb in zip(ca['cands'], cb['cands']):
            assert xa['s'] == xb['s']
            ya = dict(xa); yb = dict(xb)
            ma, mb = ya.pop('mpnn'), yb.pop('mpnn')
            if ya != yb: other_diff += 1
            n_c += 1
            if abs(ma - mb) < 1e-9: n_match += 1
            else:
                n_mis += 1; maxd = max(maxd, abs(ma - mb))
                if ma == 0.0 and mb > 0: n_o0r += 1
                if mb == 0.0 and ma > 0: n_n0o += 1
    print(f'{new_path}: cands={n_c} mpnn_exact_match={n_match} mismatch={n_mis} maxdiff={maxd:.2e} orig0_newpos={n_o0r} new0_origpos={n_n0o} other_fields_diff={other_diff}')
    return n_mis
tot_mis = 0
for orig, new in [(sys.argv[1] + '/' + f, sys.argv[2] + '/' + f) for f in sys.argv[3].split(',')]:
    tot_mis += cmp(orig, new)
print('TOTAL_MISMATCH', tot_mis)
