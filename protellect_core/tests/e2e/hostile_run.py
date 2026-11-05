import sys, os, re, logging
logging.disable(logging.CRITICAL)
mode = sys.argv[1]; genes = sys.argv[2:] or ["FFAR1", "GPR-40", "TP53"]
sys.path.insert(0, "/home/claude/work/core/protellect_core/tests/stubs")
if mode == "hostile": sys.path.insert(0, "/home/claude/work/hostile")
sys.path.insert(0, "/home/claude/work/core")
from streamlit.testing.v1 import AppTest
def start():
    at = AppTest.from_file("/home/claude/work/app.py", default_timeout=600).run()
    next(b for b in at.button if "Continue as Guest" in b.label).click().run(); return at
bad = 0
for g in genes:
    at = start(); at.text_input(key="protein_query_box").set_value(g)
    next(b for b in at.button if "Analyse Protein" in b.label).click().run()
    err = [e for e in at.markdown if "Search error" in e.value]
    print(f"== {mode} {g}: search-error box: {bool(err)} | exceptions: {len(at.exception)}")
    if err or at.exception: bad += 1
    for e in at.exception: print("  EXC:", str(e.value)[:140])
    tb = at.session_state["_last_search_tb"] if "_last_search_tb" in at.session_state else None
    if tb: print("  TRACEBACK:\n", tb[-900:])
    se = at.session_state["_step_errors"] if "_step_errors" in at.session_state else {}
    for k, v in (se or {}).items(): print("  step failed:", k, "->", v[:220])
print("FAILING SEARCHES:", bad)
