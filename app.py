# app.py
from __future__ import annotations

import streamlit as st
from modules.auth import auth_init, login_page, check_search_limit, decrement_search, save_to_workspace
from modules.config import LOGO_B64, _logo_src, STRIPE_LINKS, PLAN_LIMITS, GOAL_OPTIONS, CSV_GUIDE
from modules.utils import sh, mc, badge, src_link, render_citations
from modules.api import (
    fetch_uniprot, fetch_clinvar, fetch_pdb, fetch_papers, fetch_disease_proteins,
    fetch_ncbi_gene, fetch_pubmed_abstracts, fetch_string_interactions, fetch_gnomad,
    fetch_clinical_trials, fetch_dgidb, fetch_alphamissense, fetch_opentargets, fetch_isoforms
)
from modules.data_processing import (
    ml_score_variants, compute_gi, g_gene, g_name, g_seq, g_diseases, g_func, g_sub, g_tissue,
    g_xref, g_gpcr, g_ptype, classify_entity, g_gpcr_class, assess_gpcr_piggybacking,
    classify_organism, analyse_csv_standalone, detect_csv_type, compute_hotspot_clusters,
    compute_experiment_roi, estimate_patient_population, find_drugged_analogs, regulatory_pathway_map
)
from modules.visualization import (
    viewer_html, mutation_cascade_html, build_mutation_dynamics_html,
    build_disease_timeline_html, build_druggability_map_html, variant_landscape_fig,
    render_domain_expansion_cards, render_chemical_backbone, kyte_doolittle, calc_pI, aa_composition
)
from modules.domain_workspaces import (
    render_oncology_workspace, render_neuroscience_workspace, render_microbiome_workspace,
    render_pharma_workspace, render_molbio_workspace, render_rare_disease_workspace,
    render_oncology_panel
)
from modules.ai_synthesis import ai_synthesize
from modules.excel_export import generate_excel
from modules.tutorial import show_tutorial_dialog
from modules.sidebar import render_sidebar
from modules.domain_landing import handle_domain_landing
from modules.search_handler import handle_search
from modules.csv_handler import handle_csv_mode
from modules.disease_panel import render_disease_panel
from modules.tabs_renderer import render_all_tabs

st.set_page_config(page_title="Protellect", page_icon="🧬",
                   layout="wide", initial_sidebar_state="expanded")

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;font-size:15px;}
.stApp{background:#000205;}
[data-testid="stSidebar"]{background:#010408!important;border-right:1px solid #071828;}
.ph{background:linear-gradient(135deg,#010306,#030d1a);border:1px solid #0c2040;border-radius:14px;
  padding:1rem 1.8rem .7rem;margin-bottom:.5rem;position:relative;overflow:hidden;}
.ph::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,#00e5ff44,transparent);}
.pt{font-size:2rem;font-weight:800;letter-spacing:-.5px;margin:0;
  background:linear-gradient(90deg,#00e5ff,#6478ff,#00e5ff);background-size:200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:sh 4s linear infinite;}
.ps{color:#1e4060;font-size:1rem;margin:.2rem 0 0;}
@keyframes sh{0%{background-position:0%}100%{background-position:200%}}
.pursue-yes{background:linear-gradient(135deg,#080103,#0e0308);border:2px solid #ff2d55;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.pursue-no{background:linear-gradient(135deg,#020505,#030c16);border:2px dashed #3a6080;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.pursue-caution{background:linear-gradient(135deg,#0a0900,#120e00);border:2px solid #ffd60a;
  border-radius:12px;padding:.9rem 1.4rem;margin-bottom:.8rem;display:flex;gap:12px;align-items:center;}
.mc{background:linear-gradient(145deg,#03090f,#020810);border:1px solid #0c2040;
  border-radius:12px;padding:.9rem 1rem;text-align:center;position:relative;overflow:hidden;transition:transform .2s;}
.mc:hover{transform:translateY(-2px);}
.mc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--acc);}
.mv{font-size:1.9rem;font-weight:800;line-height:1;color:var(--clr,#00e5ff);}
.ml2{font-size:.81rem;color:#1e4060;margin-top:3px;text-transform:uppercase;letter-spacing:.7px;}
.card{background:#010508;border:1px solid #071828;border-radius:12px;padding:1rem 1.3rem;margin-bottom:.7rem;}
.card h4{color:#00e5ff;font-size:.98rem;font-weight:700;margin:0 0 .4rem;}
.card p{color:#3a6080;font-size:1.02rem;line-height:1.6;margin:0;}
.badge{display:inline-block;padding:2px 9px;border-radius:16px;font-size:.81rem;font-weight:800;}
.bC{background:rgba(255,45,85,.12);color:#ff2d55;border:1px solid #ff2d5540;}
.bH{background:rgba(255,140,66,.12);color:#ff8c42;border:1px solid #ff8c4240;}
.bM{background:rgba(255,214,10,.1);color:#ffd60a;border:1px solid #ffd60a35;}
.bN{background:rgba(58,90,122,.2);color:#3a6080;border:1px solid #1e404050;}
.stTabs{position:sticky;top:0;z-index:100;background:#000308;padding-top:3px;}
.stTabs [data-baseweb="tab-list"]{background:#000308!important;gap:3px;border-bottom:1px solid #071828;overflow:hidden!important;user-select:none!important;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px 8px 0 0;
  padding:6px 14px;color:#0d2a40!important;font-weight:600;font-size:1.02rem;}
.stTabs [aria-selected="true"]{background:#06111e!important;color:#00e5ff!important;border-bottom:2px solid #00e5ff!important;}
.sh2{display:flex;align-items:center;gap:8px;margin:0 0 .7rem;padding-bottom:5px;border-bottom:1px solid #0c2040;}
.sh2 h3{color:#a0c8e8;font-size:1rem;font-weight:700;margin:0;}
.dv{border:none;border-top:1px solid #091830;margin:1.1rem 0;}
.cite{border-left:2px solid #00e5ff22;padding:6px 10px;margin:3px 0;background:#040e1c;border-radius:0 8px 8px 0;}
.cite a{color:#2a80a4;text-decoration:none;font-size:.96rem;}
.cite a:hover{color:#00e5ff;}
.cm{color:#4a7090;font-size:.96rem;margin-top:1px;}
.src-badge{display:inline-block;background:#04080f;border:1px solid #1e4060;color:#2a6080;
  padding:1px 8px;border-radius:6px;font-size:1.02rem;margin-left:5px;text-decoration:none;}
.src-badge:hover{border-color:#00e5ff44;color:#4a90c0;}
.pt2{width:100%;border-collapse:collapse;font-size:.79rem;}
.pt2 thead tr{background:#020810;}
.pt2 th{color:#00e5ff;padding:8px 12px;text-align:left;font-size:.78rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #0c2040;}
.pt2 td{padding:8px 12px;border-bottom:1px solid #040c18;color:#7ab0cc;vertical-align:middle;}
.pt2 tr:hover td{background:#05101e;}
.sb-t{font-size:.73rem;font-weight:700;color:#5a9ab0;text-transform:uppercase;
  letter-spacing:1px;margin:.8rem 0 .3rem;padding-bottom:3px;border-bottom:1px solid #0c2040;}
.stButton>button{background:linear-gradient(135deg,#003d55,#002868)!important;
  color:#00e5ff!important;border:1px solid #00e5ff22!important;border-radius:8px!important;font-weight:700!important;}
.stButton>button:hover{border-color:#00e5ff55!important;box-shadow:0 4px 18px rgba(0,229,255,.15)!important;}
.stTextInput input,.stTextArea textarea{background:#040d18!important;border:1px solid #0c2040!important;color:#c0d8f8!important;border-radius:8px!important;}
details{border:1px solid #0c2040!important;border-radius:10px!important;background:#050f1d!important;}
.gi-critical{background:#0d020a;border:2px solid #ff2d55;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-moderate{background:#0a0900;border:2px solid #ffd60a;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-redundant{background:#04080f;border:2px dashed #3a6080;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.gi-unknown{background:#04080f;border:1px solid #1e4060;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.7rem;}
.dis-row{display:flex;align-items:flex-start;gap:10px;background:#050e1c;border:1px solid #0c2040;
  border-radius:9px;padding:10px 12px;margin:4px 0;}
.dis-name{color:#c0dff0;font-size:.83rem;font-weight:600;}
.dis-desc{color:#5a8090;font-size:1.02rem;margin-top:2px;line-height:1.5;}
.gpcr-box{background:linear-gradient(135deg,#030f1e,#04101c);border:1px solid #00e5ff33;border-radius:12px;padding:1.1rem 1.4rem;color:#7ab8d0;}

/* Domain selection cards */
[data-testid="stHorizontalBlock"] .stButton>button {
    white-space: pre-line !important;
    min-height: 80px !important;
    height: auto !important;
    text-align: left !important;
    padding: 14px 16px !important;
    background: linear-gradient(135deg, #020810, #03101e) !important;
    border: 1px solid #0d2545 !important;
    border-radius: 12px !important;
    font-size: .82rem !important;
    line-height: 1.55 !important;
    font-weight: 600 !important;
    transition: all .22s ease !important;
    width: 100% !important;
}
[data-testid="stHorizontalBlock"] .stButton>button:hover {
    border-color: rgba(0,229,255,.3) !important;
    background: linear-gradient(135deg, #030d1a, #04121f) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(0,229,255,.08) !important;
}

@keyframes fadeInUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideInLeft{from{opacity:0;transform:translateX(-18px)}to{opacity:1;transform:translateX(0)}}
@keyframes pulseGlow{0%,100%{box-shadow:0 0 0 rgba(0,229,255,0)}50%{box-shadow:0 0 20px rgba(0,229,255,.22)}}
@keyframes barFill{from{width:0!important}to{width:var(--bar-w,100%)}}
@keyframes borderPulse{0%,100%{border-color:#0c2040}50%{border-color:#00e5ff44}}

.mc{animation:fadeInUp .55s ease both;}
.sum-card{animation:slideInLeft .45s ease both;}
.dis-row{animation:fadeInUp .3s ease both;}
.pursue-yes,.pursue-no,.pursue-caution{animation:fadeInUp .4s ease both;}
.card{animation:fadeInUp .4s ease both;}
.badge{transition:transform .2s;}.badge:hover{transform:scale(1.1);}
.sh2{animation:fadeInUp .35s ease both;}
.stDownloadButton>button{background:linear-gradient(135deg,#004428,#002d18)!important;
  color:#00c896!important;border:1px solid #00c89644!important;font-weight:700!important;border-radius:8px!important;}
.stDownloadButton>button:hover{box-shadow:0 4px 20px rgba(0,200,150,.25)!important;transform:translateY(-1px);}
</style>
""", unsafe_allow_html=True)

def main():
    auth_init()
    if not st.session_state.get('auth_user'):
        login_page()

    # Initialize session state defaults
    defaults = {
        "pdata": None, "cv": None, "pdb": "", "papers": [], "scored": [], "gene": "", "uid": "",
        "assay": "", "last": "", "csv_df": None, "csv_type": "", "goal_label": GOAL_OPTIONS[0],
        "goal_custom": "", "sensitivity": 50, "gi": None, "partner_query": "",
        "partner_cv": None, "partner_gi": None, "disease_search": "", "disease_proteins": [],
        "csv_triage_active": False, "show_tutorial": True, "gnomad": {}, "string": [],
        "trials": [], "drugs": [], "abstracts": [], "org": {}, "ai_result": {},
        "ot": {}, "am": {}, "isoforms": [], "hotspots": [], "patients": {},
        "excel_bytes": None, "research_domain": None, "domain_expanded": None,
        "_last_domain": None, "protein_query_val": "", "_trigger_search": None, 
        "_search_clicked": False, "gpcr_assessment": {}, "roi_data": [], "reg_paths": {}, "analogs": []
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Handle domain switching - clear protein data when domain changes
    _cur_domain = st.session_state.get("research_domain")
    _last_domain = st.session_state.get("_last_domain")
    if _cur_domain != _last_domain and _cur_domain is not None:
        for key in ["pdata", "cv", "pdb", "scored", "gene", "uid", "assay", "last",
                    "gi", "gnomad", "string", "trials", "drugs", "abstracts", "org",
                    "ai_result", "ot", "am", "isoforms", "hotspots", "patients",
                    "partner_query", "partner_cv", "partner_gi", "excel_bytes"]:
            st.session_state[key] = defaults[key]
        st.session_state["_last_domain"] = _cur_domain

    # Header
    st.markdown(
        "<div class='ph'>"
        "<div style='display:flex;align-items:center;gap:14px;'>"
        f"<img src='{_logo_src}' style='width:52px;height:52px;object-fit:contain;filter:drop-shadow(0 0 14px #00e5ff66);'>"
        "<div>"
        "<div class='pt'>Protellect</div>"
        "<div class='ps'>AI-powered protein triage · Genetics-first · Eliminate wasted experiments</div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    # Tutorial - show on first visit or when requested
    if st.session_state.get("show_tutorial", True):
        show_tutorial_dialog()

    # Persistent tutorial button
    with st.container():
        _, btn_col = st.columns([10, 1])
        with btn_col:
            if st.button("📖 Tutorial", key="tut_btn", help="Open the tutorial"):
                st.session_state["show_tutorial"] = True
                st.rerun()

    # Handle click-to-analyse from workspace buttons
    if st.session_state.get("_trigger_search"):
        _tq = st.session_state.pop("_trigger_search")
        if _tq and _tq != st.session_state.get("last", ""):
            st.session_state["last"] = ""
            st.session_state["protein_query_val"] = _tq

    # Render sidebar
    render_sidebar()

    # Get domain and search state
    _rd = st.session_state.get("research_domain", "")
    _pdata = st.session_state.get("pdata", {})
    _search_trigger = st.session_state.get("protein_query_box", "") and st.session_state.get("_search_clicked", False)

    # Handle domain landing page (no protein loaded yet)
    handle_domain_landing(_rd, _pdata, _search_trigger)

    # Main search logic
    handle_search()

    # CSV-only mode (when CSV uploaded but no protein)
    handle_csv_mode()

    # Disease-to-proteins panel
    render_disease_panel()

    # Render all main tabs if protein data is loaded
    if st.session_state.get("pdata"):
        render_all_tabs()

    # Footer
    st.markdown(
        f"<hr style='border-color:#040c18;margin:.8rem 0;'>"
        f"<div style='text-align:center;margin-bottom:6px;'>"
        f"<img src='data:image/svg+xml;base64,{LOGO_B64}' style='width:22px;height:22px;object-fit:contain;opacity:.4;vertical-align:middle;margin-right:6px;'>"
        f"<span style='color:#0a1e30;font-size:.8rem;font-weight:600;'>Protellect</span></div>"
        f"<p style='text-align:center;color:#060f1c;font-size:.75rem;'>"
        f"Protellect · Not a substitute for expert clinical judgment.</p>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()