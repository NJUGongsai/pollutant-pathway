#!/usr/bin/env python3
"""R8 independent PPV1 and baseline red/green; no evaluation inputs."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time
from pathlib import Path
from xml.etree import ElementTree as ET

CURRENT = "00e509a974b40a7c9779fcd35e53b16637a13d60"
BASELINE = "858dd94c7c6c8fc387940242403d67b6b36b5313"
NEW_TESTS = ["test_ppv1_r8_chem.py", "test_ppv1_r8_storage.py"]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def versions(root):
    text=(root/"src/pathway_v43/pollutant/profile.py").read_text()
    return {key:value for key,value in re.findall(r'^(PPV1_[A-Z_]+VERSION)\s*=\s*"([^"]+)"',text,re.M)}

def command(args, cwd, out, name, env=None):
    started = time.monotonic()
    with (out / (name + ".stdout.txt")).open("w") as stdout, (out / (name + ".stderr.txt")).open("w") as stderr:
        completed = subprocess.run(args, cwd=cwd, env=env, stdout=stdout, stderr=stderr)
    return {"command": args, "cwd": str(cwd), "exit_code": completed.returncode,
            "elapsed_wall_seconds": round(time.monotonic()-started,3),
            "stdout": name + ".stdout.txt", "stderr": name + ".stderr.txt"}

def prepare(source, target, test_names):
    target.mkdir()
    shutil.copytree(source / "src", target / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    shutil.copy2(source / "pyproject.toml", target / "pyproject.toml")
    (target / "tests").mkdir()
    shutil.copy2(source / "tests/conftest.py", target / "tests/conftest.py")
    for name in test_names:
        shutil.copy2(source / "tests" / name, target / "tests" / name)
    return {str(p.relative_to(target)): sha(p) for p in sorted(target.rglob("*")) if p.is_file()}

def pytest(python, target, out, name, tests):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(target / "src"), TMPDIR=str(out / "synthetic_tmp"))
    (out / "synthetic_tmp").mkdir(exist_ok=True)
    cmd = [python,"-B","-m","pytest","-p","no:cacheprovider","-q","-rs","--junitxml",str(out / (name+".junit.xml"))] + ["tests/"+n for n in tests]
    return command(cmd,target,out,name,env)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--python",required=True)
    args=parser.parse_args()
    repo=args.repo.resolve(); out=args.out.resolve()
    if out.exists(): raise RuntimeError("Require fresh output")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
    if actual!=CURRENT: raise RuntimeError(("Unexpected HEAD",actual))
    if repo in out.parents or out in repo.parents: raise RuntimeError("Output must be separate")
    out.mkdir()
    alltests=sorted(p.name for p in (repo/"tests").glob("test_ppv1_*.py"))
    metadata={"actual_head":actual,"baseline_head":BASELINE,"python":args.python,
              "no_real_evaluation_gold_question_sealed_inputs":True,"commands":{}}
    current=out/"current"
    metadata["current_input_hashes"]=prepare(repo,current,alltests)
    metadata["current_schema_versions"]=versions(current)
    metadata["commands"]["ppv1_full"]=pytest(args.python,current,out,"ppv1_full",alltests)
    metadata["commands"]["current_28"]=pytest(args.python,current,out,"current_28",NEW_TESTS)
    originals=out/"original_tests"; originals.mkdir()
    for n in NEW_TESTS: shutil.copy2(repo/"tests"/n,originals/n)
    wt=out/"baseline_worktree"
    added=False
    try:
        result=command(["git","worktree","add","--detach",str(wt),BASELINE],repo,out,"worktree_add")
        metadata["commands"]["worktree_add"]=result
        if result["exit_code"]: raise RuntimeError("worktree add failed")
        added=True
        baseline_actual=subprocess.check_output(["git","rev-parse","HEAD"],cwd=wt,text=True).strip()
        metadata["actual_baseline_head"]=baseline_actual
        # Only these synthetic tests are copied to this private detached checkout.
        for n in NEW_TESTS: shutil.copy2(originals/n,wt/"tests"/n)
        baseline=out/"baseline"
        metadata["baseline_input_hashes"]=prepare(wt,baseline,NEW_TESTS)
        metadata["baseline_schema_versions"]=versions(baseline)
        metadata["new_tests_unmodified_no_adapter"]={n:sha(originals/n)==sha(baseline/"tests"/n)==sha(current/"tests"/n) for n in NEW_TESTS}
        metadata["commands"]["baseline_28"]=pytest(args.python,baseline,out,"baseline_28",NEW_TESTS)
        rows=[]
        for case in ET.parse(out/"baseline_28.junit.xml").iter("testcase"):
            failure=case.find("failure")
            msg="" if failure is None else failure.attrib.get("message","")
            text="" if failure is None else failure.text or ""
            category="baseline_positive_or_already_rejected" if failure is None else "behavior_flip"
            if failure is not None and any(x in msg+text for x in ("KeyError", "no such table", "AttributeError", "ImportError")):
                category="needs_manual_disclosure_review"
            rows.append({"name":case.attrib["name"],"classname":case.attrib["classname"],"passed":failure is None,"category":category,"failure_message":msg})
        (out/"baseline_classification.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n")
        metadata["baseline_summary"]={"failed":sum(not r["passed"] for r in rows),"passed":sum(r["passed"] for r in rows),"field_missing_red":sum(r["category"]=="needs_manual_disclosure_review" for r in rows),"behavior_red":sum(r["category"]=="behavior_flip" for r in rows)}
    finally:
        if added:
            metadata["commands"]["worktree_remove"]=command(["git","worktree","remove","--force",str(wt)],repo,out,"worktree_remove")
        metadata["worktree_still_exists"]=wt.exists()
        metadata["no_bytecode_or_pytest_cache_in_source"]=not any(p.name in ("__pycache__",".pytest_cache") or p.suffix==".pyc" for lane in ("current","baseline") for p in (out/lane).rglob("*"))
        metadata["worktree_list_after"]=subprocess.check_output(["git","worktree","list","--porcelain"],cwd=repo,text=True)
        (out/"execution_metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"full":metadata["commands"]["ppv1_full"],"current_28":metadata["commands"]["current_28"],"baseline":metadata.get("baseline_summary"),"removed":not wt.exists()},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
