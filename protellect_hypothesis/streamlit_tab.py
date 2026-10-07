"""Streamlit UI for the hypothesis engine. Call render_hypothesis_tab() from any page or tab."""
from __future__ import annotations

import pathlib

import pandas as pd
import streamlit as st

from .engine import HypothesisEngine
from .io_parsers import InputError, parse_experiment

EXAMPLE = pathlib.Path(__file__).parent / "example_data" / "example_expression.csv"


@st.cache_resource(show_spinner=False)
def _engine() -> HypothesisEngine:
    return HypothesisEngine()


def render_hypothesis_tab() -> None:
    st.header("Hypothesis Engine (beta)")
    st.info("Hypotheses, not answers. Every card shows its reasoning, and only a wet-lab experiment can confirm it. "
            "Structural similarity is not included in this version.")
    eng = _engine()
    if not eng.library_verified:
        st.warning("The historical case library has not been expert-verified yet. Treat all rankings as illustrative.")
    st.caption(eng.calibration_note())

    c1, c2 = st.columns(2)
    disease = c1.text_input("Disease or condition", placeholder="e.g. inflammatory bowel disease")
    tissue = c2.text_input("Tissue or cell type", placeholder="e.g. colon biopsy")
    comparison = st.text_input("What was compared", placeholder="e.g. inflamed vs adjacent healthy tissue")
    shape = st.selectbox("Data shape", ["auto-detect", "expression", "variant", "screen"])
    max_p = st.number_input("Keep only rows with p/adjusted p up to (0 = no filter)", 0.0, 1.0, 0.05, 0.01)

    up = st.file_uploader("Upload your processed experiment (CSV or TSV)", type=["csv", "tsv", "txt"])
    use_example = st.button("Use example data")
    src = None
    if up is not None:
        src = pd.read_csv(up, sep=None, engine="python")
    elif use_example or st.session_state.get("_hyp_use_example"):
        st.session_state["_hyp_use_example"] = True
        src = pd.read_csv(EXAMPLE)
        st.caption("Showing the bundled example (fictional values).")
    if src is None:
        return

    try:
        parsed = parse_experiment(src, None if shape == "auto-detect" else shape, max_p or None)
    except InputError as e:
        st.error(f"Could not read your file: {e}")
        return

    summary = eng.run(parsed, {"disease": disease, "tissue": tissue, "comparison": comparison})
    m1, m2, m3 = st.columns(3)
    m1.metric("Genes read", summary.n_input_genes)
    m2.metric("GPCRs found", summary.n_gpcr)
    m3.metric("Orphan GPCRs", summary.n_orphan)
    if summary.characterized:
        st.caption("Already-characterized GPCRs in your data (no hypotheses needed): " + ", ".join(summary.characterized))
    if summary.n_orphan == 0:
        st.success("No orphan GPCRs from the current registry were found in this data.")
        return

    for r in summary.results:
        sig = "" if r.significance is None else f", p = {r.significance:.3g}"
        with st.expander(f"{r.gene}  ({r.effect_type}: {r.effect:.2f}{sig})", expanded=True):
            if r.status != "hypotheses":
                st.warning(r.message)
                continue
            if r.message:
                st.caption(r.message)
            for h in r.hypotheses:
                st.markdown(f"**{h.category.replace('-', ' ').title()}: {h.statement}**")
                st.progress(min(max(h.support, 0.0), 1.0), text=f"Relative support {h.support:.2f} (a ranking, not a probability)")
                st.markdown("**Why:** " + " | ".join(h.rationale))
                st.markdown("**Test it:** " + h.test_experiment)
                with st.popover("Evidence, flags and caveats"):
                    for k, v in h.evidence_axes.items():
                        st.markdown(f"- **{k.replace('_', ' ')}:** {v}")
                    for k, v in h.flags.items():
                        st.markdown(f"- **{k.replace('_', ' ')}:** {v}")
                    for cv in h.caveats:
                        st.markdown(f"- _{cv}_")
                st.divider()
