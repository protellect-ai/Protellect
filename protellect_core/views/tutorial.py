"""First-run tutorial. Opens once per session (app.py clears the flag as it opens), reopenable from the sidebar."""
from __future__ import annotations

import streamlit as st

STEPS = [
    ("Tell it your microenvironment", "In the sidebar, set the disease, tissue, model and any patient context. Every tab re-ranks and flags results to match it."),
    ("Give it an experiment or a protein", "Upload a processed table (expression, variants or screen hits) or search a gene. Unknown receptors in your data are found automatically."),
    ("Read the banner", "The banner at the top tells you, from your data, what to prioritise, what to deprioritise, what is missing, and which tab to open next."),
    ("Overview", "A technical animation of your experiment, whether to pursue the target and how, its associated diseases, and a ranked list of what may happen, each with proof."),
    ("Triage", "The AlphaFold structure and the interaction network side by side. Pick any variant and it is shown on the structure, linked to disease and tissue, with a step-by-step plan."),
    ("Druggable hotspots", "Where the protein can be drugged, known drugs, pharmacokinetics and ADMET screens from real compound records, adverse-event reports, and ranked what-if scenarios."),
    ("Genetics", "The thresholds the gene meets or misses, the variant cascade (each stage tagged recorded, predicted, expected or untested), and its interactions."),
    ("Case Study", "Which diseases, tissues and organ systems the protein is tied to, with the source for each link."),
    ("Proof and ML validation", "Every statement shows its sources. Statements with no source are withheld. ML validation cross-examines each claim and shows its counter-arguments."),
]


@st.dialog("Welcome to Protellect", width="large")
def tutorial_dialog() -> None:
    st.markdown("**Evidence-first orphan-GPCR triage.** Nothing is shown as a finding unless it carries proof.")
    for i, (t, body) in enumerate(STEPS, 1):
        st.markdown(f"**{i}. {t}**  \n{body}")
    if st.button("Got it", type="primary", key="tut_ok"):
        st.rerun()
