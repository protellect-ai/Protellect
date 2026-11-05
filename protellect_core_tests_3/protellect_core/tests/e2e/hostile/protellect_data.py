"""Hostile stand-in: the realistic stub, but every number in every response becomes text (what a sloppy API can return)."""
import functools, pathlib
_src = pathlib.Path("/home/claude/work/core/protellect_core/tests/stubs/protellect_data.py").read_text(encoding="utf-8")
exec(compile(_src, "stub", "exec"), globals())

def _s(x):
    if isinstance(x, bool) or x is None: return x
    if isinstance(x, (int, float)): return str(x)
    if isinstance(x, dict): return {k: _s(v) for k, v in x.items()}
    if isinstance(x, list): return [_s(v) for v in x]
    if isinstance(x, tuple): return tuple(_s(v) for v in x)
    return x

def _wrap(f):
    @functools.wraps(f)
    def g(*a, **k): return _s(f(*a, **k))
    g.clear = getattr(f, "clear", lambda *a, **k: None)
    return g

for _n in [n for n, v in list(globals().items()) if n.startswith("fetch_") and callable(v)]:
    globals()[_n] = _wrap(globals()[_n])
