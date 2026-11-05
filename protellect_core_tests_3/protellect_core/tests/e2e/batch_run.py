import sys, logging, re
logging.disable(logging.CRITICAL)
sys.path.insert(0, "/home/claude/work/core/protellect_core/tests/stubs"); sys.path.insert(0, "/home/claude/work/core")
import pandas as pd, numpy as np
from streamlit.testing.v1 import AppTest
rng = np.random.default_rng(1)
genes = [f"G{i}" for i in range(400)] + ["GPR56", "ADGRG1", "GPR171", "GPR18", "GPR65", "GPR35", "ADORA2A", "PTGER4", "PDCD1", "TCF7", "CCR7"]
lfc = list(rng.normal(0, .4, 400)) + [2.0, 3.0, 2.2, 1.9, 1.7, 1.5, 2.4, 1.8, 2.8, -3.12, -2.1]
padj = list(rng.uniform(.05, 1, 400)) + [1e-6, 1e-9, 1e-7, 1e-5, 1e-4, 1e-4, 1e-8, 1e-5, 1e-10, 1e-9, 1e-6]
df = pd.DataFrame({"gene": genes, "log2FoldChange": lfc, "padj": padj, "disease": "Hepatocellular carcinoma", "cell_type": "CD8+ T cells"})
reg = "gene,status,note,family,aliases\n" + "\n".join([
 "ADGRG1,orphan,,Adhesion receptors,GPR56|TM7XN1", "GPR171,orphan,,Class A Orphans,", "GPR18,orphan,,Class A Orphans,", "GPR65,orphan,,Class A Orphans,TDAG8",
 "GPR35,orphan,,Class A Orphans,", "ADORA2A,characterized,,Adenosine receptors,", "PTGER4,characterized,,Prostanoid receptors,"] + [f"GPRX{i},orphan,,Class A Orphans," for i in range(120)])
at = AppTest.from_file("/home/claude/work/app.py", default_timeout=600).run()
next(b for b in at.button if "Continue as Guest" in b.label).click().run()
at.session_state["hyp_registry_csv"] = reg
at.session_state["csv_df"] = df; at.session_state["csv_type"] = "expression"; at.session_state["csv_triage_active"] = True; at.session_state["csv_filename"] = "zheng_like.csv"
at.session_state["_meta_prefill"] = None
at.run()
print("exceptions:", len(at.exception), [str(e.value)[:150] for e in at.exception])
def dump(tag):
    md = " | ".join(m.value for m in at.markdown)
    infos = [i.value for i in at.info] + [c.value for c in at.caption]
    print(f"--- {tag}")
    print("alias notice:", [x for x in infos if "same gene" in x or "legacy name" in x][:2])
    print("selectbox opts:", [ (s.label, list(s.options)[:12]) for s in at.selectbox if "details" in s.label.lower()])
    for d in at.dataframe:
        v = d.value
        if hasattr(v, "columns") and ("Likely coupling" in list(v.columns) or "Protein" in list(v.columns)):
            print(v.to_string()[:1500])
    print("reported claims shown:", [m for m in re.findall(r"\*\*([^*]*(?:reported|family-level)[^*]*)\*\*", md)][:4])
dump("initial")
for s in at.selectbox:
    if "details" in s.label.lower() and "ADGRG1" in list(s.options):
        s.select("ADGRG1"); break
at.run()
print("exceptions after focus:", len(at.exception), [str(e.value)[:150] for e in at.exception])
dump("focus ADGRG1")
