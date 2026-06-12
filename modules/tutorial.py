# modules/tutorial.py
from __future__ import annotations
import streamlit as st
from modules.config import LOGO_B64

@st.dialog("🧬 Welcome to Protellect", width="large")
def show_tutorial_dialog():
    st.markdown(
        f"<div style='text-align:center;margin-bottom:1.2rem;'>"
        f"<img src='data:image/svg+xml;base64,{LOGO_B64}' style='width:68px;height:68px;object-fit:contain;filter:drop-shadow(0 0 16px #2a8a5066);'>"
        f"<div style='color:#00e5ff;font-size:1.4rem;font-weight:800;margin-top:6px;'>Protellect</div>"
        f"<div style='color:#2a5070;font-size:.88rem;'>Genetics-first protein triage</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    steps = [
        ("🎯", "Set Your Research Goal", "Choose your objective in the sidebar (therapeutic targets, drug discovery, biomarker, etc). All findings will be tailored to this goal."),
        ("🔍", "Search a Human Protein", "Type a gene symbol (TP53, BRCA1, FLNC) or UniProt accession (P04637). Human proteins only — the app rejects non-human proteins like Ovalbumin."),
        ("🏥", "Disease → Proteins Search", "Enter a disease name to find ALL proteins whose mutations cause it, ranked by confirmed ClinVar variant count."),
        ("📂", "Upload Wet-Lab CSV", "Upload any CSV (expression, variants, proteomics). Click 'Run Wet-Lab Triage' for standalone analysis — no protein needed."),
        ("🎚️", "Sensitivity Slider", "Controls how strictly variants are ranked. High = more flagged. Low = only the most certain disease variants elevated."),
        ("🔴", "Read the Pursue Banner First", "The banner (red/grey) appears immediately: PURSUE / PROCEED / BE SELECTIVE / DEPRIORITISE. Based entirely on ClinVar disease genetics."),
        ("📊", "Tab 1 — Triage", "3D structure (click residues!), variant landscape chart, ranked hotspot table. Red dots = disease-causing sites."),
        ("📋", "Tab 2 — Case Study", "Tissue associations, GPCR signal breakdown, genomic map, somatic vs germline classification."),
        ("🔬", "Tab 3 — Explorer", "Full 3D viewer + mutation simulator. Pick any residue, choose a substitute, see structural disruption."),
        ("🧪", "Tab 4 — Experiments", "Mutation cascade animation (drag the slider!), full protocol cards with cost tiers, decision funnel."),
        ("⚠️", "The Core Principle", "Protein structures are NOT a validation of biology. DNA sequences are. A protein with zero Mendelian disease variants — however famous — should be deprioritised."),
    ]
    for i, (icon, title, body) in enumerate(steps, 1):
        st.markdown(
            f"<div style='display:flex;gap:12px;background:#020810;border:1px solid #0d2545;border-radius:10px;padding:.8rem 1rem;margin:.4rem 0;align-items:flex-start;'>"
            f"<div style='display:flex;align-items:center;gap:7px;flex-shrink:0;'>"
            f"<span style='background:#00e5ff;color:#000;border-radius:50%;width:20px;height:20px;text-align:center;line-height:20px;font-weight:800;font-size:.75rem;flex-shrink:0;display:inline-block;'>{i}</span>"
            f"<span style='font-size:1rem;'>{icon}</span></div>"
            f"<div><div style='color:#00e5ff;font-weight:700;font-size:.92rem;margin-bottom:2px;'>{title}</div>"
            f"<div style='color:#3a6080;font-size:.85rem;line-height:1.5;'>{body}</div></div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("<div style='color:#6a9ab0;font-size:.88rem;'>💡 Try <b style='color:#3a8090;'>FLNC</b> (disease-critical) vs <b style='color:#3a8090;'>ARRB2</b> (no disease variants) to see the triage system in action.</div>", unsafe_allow_html=True)
    with c2:
        if st.button("Got it ✓", use_container_width=True, type="primary"):
            st.session_state["show_tutorial"] = False
            st.rerun()
