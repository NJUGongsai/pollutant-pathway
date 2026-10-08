#!/usr/bin/env python3
"""Launch the original controller, then enforce independent result checks."""
import subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent
args=sys.argv[1:]
if '--out' not in args:
    raise SystemExit('Use --repo <repo> --out <fresh tmp> --python <depending43 python>')
out=args[args.index('--out')+1]
completed=subprocess.run([sys.executable,'-B',str(here/'independent_execution_as_executed.py')]+args)
if completed.returncode:
    raise SystemExit(completed.returncode)
checked=subprocess.run([sys.executable,'-B',str(here/'assert_ppv1_results.py'),out])
raise SystemExit(checked.returncode)
