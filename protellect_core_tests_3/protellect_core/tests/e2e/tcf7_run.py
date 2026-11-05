import sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/claude/work/core/protellect_core/tests/stubs"); sys.path.insert(0, "/home/claude/work/core")
import pandas as pd, numpy as np
from streamlit.testing.v1 import AppTest
rng = np.random.default_rng(0)
df = pd.DataFrame({"gene": [f"G{i}" for i in range(400)] + ["TP53", "GPR151"], "log2FoldChange": list(rng.normal(0, 0.4, 400)) + [3.12, 1.5], "padj": list(rng.uniform(0.05, 1, 400)) + [1e-9, 1e-5]})
at = AppTest.from_file("/home/claude/work/app.py", default_timeout=600).run()
next(b for b in at.button if "Continue as Guest" in b.label).click().run()
at.session_state["csv_df"] = df; at.session_state["csv_type"] = "expression"; at.session_state["csv_triage_active"] = True; at.session_state["csv_filename"] = "sade_feldman_like.csv"
at.run()
at.text_input(key="protein_query_box").set_value("TP53")
next(b for b in at.button if "Analyse Protein" in b.label).click().run()
print("exceptions:", len(at.exception), [str(e.value)[:120] for e in at.exception])
md = " ".join(m.value for m in at.markdown)
import re
for k in ("DEPRIORITIZE", "PRIORITIZE", "strong role in your experiment", "As a drug target", "Role in your experiment", "low as a drug target"):
    print(f"{k!r}:", k in md)
m = re.search(r"letter-spacing:\.08em'>([A-Z ]+)</div><div[^>]*>([^<]+)</div>", md)
print("BANNER:", m.groups() if m else None)
