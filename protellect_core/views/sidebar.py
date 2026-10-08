"""The microenvironment panel. One place that tailors the whole workspace."""
from __future__ import annotations

import streamlit as st

from ..context import FACTORS

MODELS = ["", "Human patient tissue", "Primary cells", "Cell line", "Organoid", "Mouse model", "Other"]


def render_context_sidebar() -> None:
    st.markdown("<div class='sb-t'>Microenvironment</div>", unsafe_allow_html=True)
    with st.expander("Tailor the workspace", expanded=False):
        st.caption("Everything you set here re-ranks and flags results in every tab. It never adds a claim that is not in the data.")
        ss = st.session_state
        ss["ctx_disease"] = st.text_input("Disease or condition", value=ss.get("ctx_disease", ""), key="ctx_disease_inp", placeholder="e.g. inflammatory bowel disease")
        ss["ctx_tissue"] = st.text_input("Tissue or cell type", value=ss.get("ctx_tissue", ""), key="ctx_tissue_inp", placeholder="e.g. colon biopsy")
        cur = ss.get("ctx_model", "")
        ss["ctx_model"] = st.selectbox("Experimental model", MODELS, index=MODELS.index(cur) if cur in MODELS else 0, key="ctx_model_inp")
        ss["ctx_comparison"] = st.text_input("What was compared", value=ss.get("ctx_comparison", ""), key="ctx_comp_inp", placeholder="e.g. inflamed vs healthy")
        ss["ctx_factors"] = st.multiselect("Microenvironment factors", list(FACTORS), default=[f for f in ss.get("ctx_factors", []) if f in FACTORS], key="ctx_factors_inp")
        st.markdown("**Patient context** (optional)")
        ss["pt_age"] = st.text_input("Age (years)", value=ss.get("pt_age", ""), key="pt_age_inp")
        sexes = ["", "Female", "Male", "Other"]
        cur = ss.get("pt_sex", "")
        ss["pt_sex"] = st.selectbox("Sex", sexes, index=sexes.index(cur) if cur in sexes else 0, key="pt_sex_inp")
        ss["pt_ethnicity"] = st.text_input("Ancestry", value=ss.get("pt_ethnicity", ""), key="pt_eth_inp")
        ss["pt_comorbid"] = st.text_area("Comorbidities (one per line)", value=ss.get("pt_comorbid", ""), key="pt_com_inp")
        ss["pt_meds"] = st.text_area("Current medications", value=ss.get("pt_meds", ""), key="pt_med_inp")
        ss["pt_family"] = st.text_input("Family history", value=ss.get("pt_family", ""), key="pt_fam_inp")
        ss["pt_envir"] = st.text_input("Environmental exposures", value=ss.get("pt_envir", ""), key="pt_env_inp")
