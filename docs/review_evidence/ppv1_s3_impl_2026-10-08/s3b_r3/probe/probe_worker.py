
import json, os, sys
from pathlib import Path
sys.path.insert(0, '/Volumes/CC/Enzyme_Agent/dependingv43/src')
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run, resume_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from pathway_v43.pollutant.search import SearchCrashInjection, SearchLedger

inp = json.loads(Path(sys.argv[1]).read_text())
run_id = inp["run_id"]
runs_root = Path(inp["runs_root"])

def hard(tag, detail=None):
    print(json.dumps({"hard_kill": tag, "detail": detail or {},
                      "pid": os.getpid()}, ensure_ascii=False), flush=True)
    sys.stderr.flush()
    os._exit(77)

if inp.get("injection") == "after_two_followups":
    orig = SearchLedger.enqueue_action
    count = [0]
    def enqueue(self, *a, **k):
        r = orig(self, *a, **k)
        if k.get("action_kind") == "retrieve" and (k.get("payload") or {}).get("source_event_id"):
            count[0] += 1
            if count[0] == 2:
                hard(inp["injection"], {"count": count[0], "result": dict(r)})
        return r
    SearchLedger.enqueue_action = enqueue

try:
    if inp["mode"] == "start":
        out = start_run(config=resolve_config(), runs_root=runs_root,
                        run_id=run_id, smiles=inp.get("smiles", "CCO"),
                        max_depth=3, max_expansions=10,
                        max_frontier_width=2, finder=object(),
                        scripted=True,
                        profile=PROFILE_POLLUTANT_PATHWAY_V1,
                        ppv1_plan=inp.get("plan"),
                        profile_policy=inp.get("policy"),
                        crash_after=inp.get("crash_after"))
    else:
        out = resume_run(config=resolve_config(), runs_root=runs_root,
                         run_id=run_id, finder=object(),
                         ppv1_plan=inp.get("plan"),
                         crash_after=inp.get("crash_after"))
    print(json.dumps({"result": out, "pid": os.getpid()},
                     ensure_ascii=False), flush=True)
except SearchCrashInjection as exc:
    hard(inp.get("crash_after"), exc.detail)
except Exception as exc:
    print(json.dumps({"exception": type(exc).__name__,
                      "detail": getattr(exc, "detail", {}),
                      "message": str(exc)[:300], "pid": os.getpid()},
                     ensure_ascii=False), flush=True)
    sys.exit(3)
