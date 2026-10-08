#!/usr/bin/env python3
"""Exit nonzero if the independent controller's observed tests differ."""
import json,sys
from pathlib import Path
from xml.etree import ElementTree as ET
out=Path(sys.argv[1]).resolve()
m=json.loads((out/'execution_metadata.json').read_text())
assert m['actual_head']=='00e509a974b40a7c9779fcd35e53b16637a13d60'
assert m['actual_baseline_head']=='858dd94c7c6c8fc387940242403d67b6b36b5313'
for name,count,red,rc in [('ppv1_full',536,0,0),('current_28',28,0,0),('baseline_28',28,14,1)]:
    assert m['commands'][name]['exit_code']==rc,(name,m['commands'][name])
    cases=list(ET.parse(out/(name+'.junit.xml')).iter('testcase'))
    assert len(cases)==count,(name,len(cases))
    assert sum(c.find('failure') is not None for c in cases)==red,name
    assert not any(c.find('error') is not None or c.find('skipped') is not None for c in cases),name
assert m['baseline_summary']=={'failed':14,'passed':14,'field_missing_red':0,'behavior_red':14}
assert all(m['new_tests_unmodified_no_adapter'].values())
assert m['commands']['worktree_remove']['exit_code']==0
assert not m['worktree_still_exists']
assert not Path(m['commands']['worktree_add']['command'][4]).exists()
print('PPV1 public observations verified: full 536/0 skip, current 28/0 skip, baseline 14 behavior red + 14 green / 0 missing-field red; return codes and worktree cleanup match.')
