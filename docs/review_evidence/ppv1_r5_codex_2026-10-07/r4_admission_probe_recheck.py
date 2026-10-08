"""Run copied R4 admission fixture with per-call contract capture on R5.

Expected integrity/type rejection must not abort remaining controls. A changed
True diagnostic to False/None is tampering, not a genuine negative axis case.
The R5 suite tests genuine negative diagnostics separately.
"""
import ast
import pathlib

source = pathlib.Path(__file__).with_name('r4_admission_probe.py')
tree = ast.parse(source.read_text())
out = []
wrapper = ast.parse('''
def audit_case(name, h, states, ev, **kw):
    try:
        return _original_audit_case(name, h, states, ev, **kw)
    except Exception as exc:
        emit(name, exception=type(exc).__name__, detail=getattr(exc, 'detail', None), message=str(exc))
        return None
''').body[0]
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'HEAD' for t in node.targets):
        node.value = ast.Constant('293bc627f57b1f778aa433750f7f61d00b4a9d18')
    if isinstance(node, ast.FunctionDef) and node.name == 'audit_case':
        node.name = '_original_audit_case'
        out.extend([node, wrapper])
    else:
        out.append(node)
tree.body = out
namespace = {'__file__':str(source),'__name__':'__main__'}
exec(compile(ast.fix_missing_locations(tree), str(source), 'exec'), namespace)
