"""Glue between the Protellect app and the hypothesis engine.

render_hypothesis_workspace() is what the new "Hypotheses" tab in app.py calls. It reuses what the app already
holds in st.session_state, so the engine behaves as part of the system, not a separate tool:

  * the CSV uploaded in the sidebar (csv_df)            -> analyzed directly, no second upload
  * the protein loaded by the sidebar search (gene/pdata) -> lookup mode, plus its UniProt tissue text as annotation
  * the disease field and research goal                  -> prefilled context
Everything is read defensively with .get(); if a key is missing the tab falls back to its own uploader.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from .registry import convert_iuphar_bytes, normalize_tissues
from .streamlit_tab import _guide, _run, get_engine


def uniprot_tissue_text(pdata: dict) -> str:
    """Tissue-specificity sentence from a UniProt entry, as stored by the main app (same logic as its g_tissue)."""
    for c in (pdata or {}).get("comments", []) or []:
        if c.get("commentType") == "TISSUE SPECIFICITY":
            texts = c.get("texts", [])
            if texts:
                return texts[0].get("value", "")
    return ""


def extra_annotations_from_app(gene: Optional[str], pdata: Optional[dict]) -> dict:
    if not gene or not pdata:
        return {}
    tissues = normalize_tissues([uniprot_tissue_text(pdata)])
    return {gene.upper(): {"tissues": tissues, "source": "UniProt tissue specificity (loaded in Protellect)"}} if tissues else {}


def _registry_panel(eng) -> None:
    n_orph = sum(v["status"] == "orphan" for v in eng.registry.values())
    n_all = len(eng.registry)
    with st.expander(f"Receptor registry: {n_orph} orphan GPCRs recognized ({n_all} receptors listed)", expanded=False):
        if n_orph < 50:
            st.warning("This is only the small seed list. Load the full list so the engine recognizes every orphan GPCR in your data.")
        st.markdown("Download the Guide to Pharmacology **targets and families** CSV from guidetopharmacology.org (Downloads page), "
                    "then upload it here. It is used for this session; download the converted file and add it to the repo as "
                    "`protellect_hypothesis/data/gpcr_registry.csv` to make it permanent.")
        up = st.file_uploader("Guide to Pharmacology targets-and-families CSV", type=["csv", "txt"], key="hyp_registry_upload")
        if up is not None:
            try:
                csv_text = convert_iuphar_bytes(up.getvalue())
            except ValueError as e:
                st.error(str(e))
            else:
                if st.session_state.get("hyp_registry_csv") != csv_text:
                    st.session_state["hyp_registry_csv"] = csv_text
                    st.rerun()
        if st.session_state.get("hyp_registry_csv"):
            st.success("Using the full registry you loaded this session. Spot-check a few receptors you know.")
            st.download_button("Download converted registry (CSV)", st.session_state["hyp_registry_csv"],
                               file_name="gpcr_registry.csv", mime="text/csv", key="hyp_registry_dl")


def render_hypothesis_workspace() -> None:
    eng = get_engine()
    st.markdown("### Hypotheses")
    st.caption("Turns the orphan GPCRs in your own data into ranked, testable hypotheses. Hypotheses, not answers: only a wet-lab "
               "experiment confirms them.")
    if not eng.library_verified:
        st.warning("The historical case library has not been expert-verified yet. Treat all rankings as illustrative.")
    st.caption(eng.calibration_note())

    ss = st.session_state
    csv_df, csv_name = ss.get("csv_df"), ss.get("csv_filename") or "your sidebar upload"
    gene, pdata = (ss.get("gene") or "").strip(), ss.get("pdata") or {}
    sources = []
    if csv_df is not None:
        sources.append("sidebar")
    if gene and pdata:
        sources.append("protein")
    sources.append("upload")
    labels = {"sidebar": f"Wet-lab data from the sidebar ({csv_name})", "protein": f"The protein I searched ({gene}), no experiment",
              "upload": "Upload a different file here"}

    guide_tab, run_tab = st.tabs(["Guide: what to upload and what you get", "Run an analysis"])
    with guide_tab:
        _guide(eng)
    with run_tab:
        mode = st.radio("What should the engine analyze?", sources, format_func=labels.get, horizontal=False, key="hyp_mode")
        disease = ss.get("disease_search")
        defaults = {"disease": disease if isinstance(disease, str) else ""}
        extra = extra_annotations_from_app(gene, pdata)
        if mode == "sidebar":
            _run(eng, source=csv_df, source_label=labels["sidebar"], defaults=defaults, extra_annotations=extra, kp="hypapp")
        elif mode == "protein":
            tissue_txt = uniprot_tissue_text(pdata)
            if tissue_txt:
                st.caption(f"UniProt tissue specificity for {gene}: {tissue_txt[:200]}")
            _run(eng, defaults=defaults, lookup_gene=gene, extra_annotations=extra, kp="hypapp")
        else:
            _run(eng, defaults=defaults, extra_annotations=extra, kp="hypapp")
        _registry_panel(eng)
