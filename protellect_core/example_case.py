"""The built-in test case: a SYNTHETIC cancer-immune GPCRome (head and neck tumour microenvironment).

Why it exists: a tool like this needs something to be tested against. This dataset has known structure planted in invented numbers,
so you can check the tool finds what is there and stays silent where nothing is. It is a software test, not biology.
The questions it models are the ones a cancer-immune GPCR group asks: which uncharacterised GPCRs are active in tumour and immune
cells, which G-protein class dominates the receptors that change in a cell state (for example exhausted versus effector T cells), what each
receptor tracks (T-cell exhaustion, YAP/TAZ targets), and which ligand-producing cells could be talking to which receptor-bearing cells.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd

EX = pathlib.Path(__file__).parent / "example"
LABEL = "SYNTHETIC cancer-immune GPCRome (test case)"
CONTEXT = {"ctx_disease": "head and neck squamous cell carcinoma", "ctx_tissue": "tumor-infiltrating immune cells", "ctx_model": "Human patient tissue",
           "ctx_comparison": "exhausted versus effector CD8 T cells", "ctx_factors": ["Hypoxia", "Immune checkpoint"]}
WIDGET_KEYS = {"ctx_disease": "ctx_disease_inp", "ctx_tissue": "ctx_tissue_inp", "ctx_model": "ctx_model_inp", "ctx_comparison": "ctx_comp_inp", "ctx_factors": "ctx_factors_inp"}


def truth() -> dict:
    return json.loads((EX / "truth.json").read_text())


def load_into_session(ss) -> None:
    """Run as a button callback (before the page is drawn), so widget values can be set safely."""
    ss["csv_df"] = pd.read_csv(EX / "gpcrome_differential.csv")
    ss["csv_type"], ss["csv_filename"], ss["csv_triage_active"], ss["_csv_last_file"] = "expression", LABEL, True, LABEL
    ss["gpcrome_matrix"] = pd.read_csv(EX / "gpcrome_matrix.csv")
    ss["alterations"] = pd.read_csv(EX / "gpcrome_alterations.csv").rename(columns={"cancer_type": "cancer", "mutation_freq": "mut", "amp_freq": "amp", "del_freq": "del"})
    ss["hyp_registry_csv"] = (EX / "gpcrome_registry.csv").read_text()
    for k, v in CONTEXT.items():
        ss[k] = v
        ss[WIDGET_KEYS[k]] = v
    ss["example_loaded"] = True


def clear_session(ss) -> None:
    ss["csv_df"], ss["csv_triage_active"], ss["gpcrome_matrix"], ss["example_loaded"], ss["alterations"] = None, False, None, False, None
    for k in ("gp_fg", "coupling_table", "coupling_source", "_repurpose"):
        ss.pop(k, None)
    ss["hyp_registry_csv"] = ""
    for k, w in WIDGET_KEYS.items():
        ss[k] = [] if k == "ctx_factors" else ""
        ss[w] = [] if k == "ctx_factors" else ""
