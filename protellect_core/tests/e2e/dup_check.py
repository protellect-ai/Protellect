import sys, logging, collections
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/claude/work/core/protellect_core/tests/stubs"); sys.path.insert(0, "/home/claude/work/core")
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("/home/claude/work/app.py", default_timeout=600).run()
next(b for b in at.button if "Continue as Guest" in b.label).click().run()
at.text_input(key="protein_query_box").set_value(sys.argv[1] if len(sys.argv) > 1 else "FFAR1")
next(b for b in at.button if "Analyse Protein" in b.label).click().run()
assert not at.exception
c = collections.Counter()
for e in list(at.markdown) + list(at.caption) + list(at.info) + list(at.warning):
    v = str(e.value).strip()
    if len(v) > 60: c[v[:160]] += 1
rep = [(n, t) for t, n in c.items() if n > 1]
print("repeated blocks:", len(rep))
for n, t in sorted(rep, reverse=True)[:15]: print(n, "x", t[:110].replace("\n", " "))
