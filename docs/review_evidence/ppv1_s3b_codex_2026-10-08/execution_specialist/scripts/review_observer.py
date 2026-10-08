import json,os
from pathlib import Path
result={'selected_nodeids':[],'deselected_nodeids':[],'skip_reports':[]}
def pytest_collection_modifyitems(session,config,items):
    result['selected_nodeids']=[i.nodeid for i in items]
def pytest_deselected(items):
    result['deselected_nodeids'].extend(i.nodeid for i in items)
def pytest_runtest_logreport(report):
    if report.skipped:result['skip_reports'].append({'nodeid':report.nodeid,'when':report.when,'reason':str(report.longrepr)})
def pytest_sessionfinish(session,exitstatus):
    result['exitstatus']=int(exitstatus)
    Path(os.environ['REVIEW_OBSERVATION']).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
