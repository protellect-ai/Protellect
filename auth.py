"""
Protellect — Genetics-First Protein Intelligence Platform
Streamlit Community Cloud deployment
"""
import streamlit as st
import os, re, math
import numpy as np, pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Protellect", page_icon="🔬", layout="wide",
                   initial_sidebar_state="expanded")

# ── Proper module imports (no exec hacks) ─────────────────────────────────
import ui
from auth import (is_authenticated, render_login, render_quota_banner,
                  logout, can_search, record_search, current_user)
import tabs as T
from fetchers import (fetch_uniprot, parse_uniprot, fetch_clinvar,
                      fetch_alphafold_pdb, parse_plddt, fetch_alphamissense,
                      fetch_pubmed, fetch_gnomad, fetch_string, fetch_opentargets,
                      fetch_dgidb, fetch_trials, fetch_gtex, fetch_kegg_pathways,
                      fetch_ai_report)
from engines import score_genomic_integrity, compute_experiment_roi
from databases import (ARRB_GENES, NON_HUMAN_TERMS, DOMAIN_EXAMPLES, MICRO_ORGANISMS,
                       VERDICT_COLORS)

ui.inject_css()

DOMAINS = ["Neuroscience","Cancer Biology","Pharmaceuticals","Microbiome","Molecular Biology"]
DOMAIN_ICONS = {"Neuroscience":"🧠","Cancer Biology":"🎗","Pharmaceuticals":"💊",
                "Microbiome":"🦠","Molecular Biology":"⚛️"}

# ── Session defaults ───────────────────────────────────────────────────────
for k,v in {"auth_user":None,"searches_used":0,"workspace":[],"current_protein":None,
            "protein_data_cache":{},"domain":None,"research_goal":"Drug target identification",
            "anthropic_key":"","sensitivity":0.70,"csv_data":None,"wet_lab_text":"",
            "_qval":"","_dval":"","_trigger_search":False,"_trigger_disease":False}.items():
    if k not in st.session_state: st.session_state[k]=v

# ── Auth gate ──────────────────────────────────────────────────────────────
if not is_authenticated():
    render_login()
    st.stop()

user = current_user()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""<div style="padding:10px 0 6px">
      <span style="font-size:1.1rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#7c3aed);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent">🔬 Protellect</span>
      <div style="font-size:.68rem;color:#2a5070;margin-top:1px;font-family:monospace">
        {user.get('name','')} · {user.get('tier','free').upper()}
      </div>
    </div>""", unsafe_allow_html=True)
    render_quota_banner()

    st.markdown(ui.lbl("RESEARCH GOAL"), unsafe_allow_html=True)
    st.selectbox("rg", ["Drug target identification","Disease mechanism","Variant pathogenicity",
                         "Therapeutic hypothesis","Protein function","Biomarker discovery","Academic research"],
                 label_visibility="collapsed", key="research_goal")

    st.markdown(ui.lbl("PROTEIN SEARCH"), unsafe_allow_html=True)
    domain = st.session_state.domain or "Molecular Biology"
    examples = DOMAIN_EXAMPLES.get(domain, ["TP53","BRCA1","EGFR"])
    _qinput = st.text_input("ps", value=st.session_state._qval,
                             placeholder=f"e.g. {' · '.join(examples[:3])}",
                             label_visibility="collapsed", key="_search_widget")
    st.session_state._qval = _qinput
    if st.button("⚡ Analyse Protein", type="primary", use_container_width=True, key="analyse_btn"):
        st.session_state._trigger_search = True

    st.markdown(ui.lbl("DISEASE → PROTEINS"), unsafe_allow_html=True)
    _dinput = st.text_input("dp", value=st.session_state._dval,
                             placeholder="e.g. Hantavirus · arrhythmia · BRCA",
                             label_visibility="collapsed", key="_disease_widget")
    st.session_state._dval = _dinput
    if st.button("🔗 Find Disease Proteins", use_container_width=True, key="disease_btn"):
        st.session_state._trigger_disease = True

    st.markdown(ui.lbl("WET-LAB DATA (CSV)"), unsafe_allow_html=True)
    with st.expander("▸ Accepted formats", expanded=False):
        st.markdown('<div style="color:#2a5070;font-size:.7rem">ClinVar export, VCF variants, AlphaMissense TSV, proteomics CSV (gene, fc, p-value). Max 50MB.</div>', unsafe_allow_html=True)
    csv_file = st.file_uploader("csv_up", type=["csv","txt","tsv"],
                                 label_visibility="collapsed", key="csv_uploader")
    if csv_file:
        try:
            sep = "\t" if csv_file.name.endswith((".txt",".tsv")) else ","
            df_csv = pd.read_csv(csv_file, sep=sep, nrows=5000)
            st.session_state.csv_data = df_csv
            st.markdown(f'<div style="background:rgba(0,229,255,0.06);border:1px solid rgba(0,229,255,0.15);border-radius:4px;padding:5px 9px;font-size:.71rem;color:#00e5ff">{csv_file.name} · {len(df_csv):,} rows</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Parse error: {e}")

    st.markdown(ui.lbl("SENSITIVITY"), unsafe_allow_html=True)
    sens = st.slider("sens", 0.0, 1.0, st.session_state.sensitivity, step=0.05,
                     label_visibility="collapsed", key="sensitivity",
                     help="AlphaMissense pathogenicity threshold. Default 0.70.")
    st.markdown(f'<div class="dim" style="margin:-4px 0 4px">{sens:.2f} · {"Strict" if sens>0.8 else "Balanced" if sens>0.5 else "Sensitive"}</div>', unsafe_allow_html=True)
    if st.button("▶ Run Triage", use_container_width=True, key="triage_btn"):
        st.session_state.protein_data_cache={}; st.toast(f"Re-running at sensitivity {sens:.2f}")

    st.markdown(ui.lbl("WET-LAB ASSAY"), unsafe_allow_html=True)
    wl = st.text_area("wl", value=st.session_state.wet_lab_text,
                       placeholder="Describe assay result — e.g. Ser2152-P detected at 10nM, abolished in R2149Q variant.",
                       label_visibility="collapsed", height=60, key="wet_lab_input")
    st.session_state.wet_lab_text = wl

    st.markdown(ui.lbl("AI REPORT KEY"), unsafe_allow_html=True)
    ak = st.text_input("aik", type="password", placeholder="sk-ant-...",
                        label_visibility="collapsed", key="_ak_widget")
    if ak: st.session_state.anthropic_key = ak
    if st.session_state.anthropic_key:
        st.markdown('<div style="font-size:.68rem;color:#4ade80">● AI enabled</div>', unsafe_allow_html=True)

    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Cache", use_container_width=True): st.cache_data.clear(); st.toast("✅")
    with c2:
        if st.button("Clear", use_container_width=True):
            st.session_state._qval=""; st.session_state.current_protein=None; st.rerun()
    with c3:
        if st.button("Logout", use_container_width=True): logout(); st.rerun()

# ── Domain landing ─────────────────────────────────────────────────────────
if not st.session_state.domain:
    ui.show_domain_landing()
    st.stop()

domain = st.session_state.domain

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;padding:2px 0;margin-bottom:4px">
  <span style="font-size:.85rem;font-weight:700;color:#00e5ff">🔬 Protellect</span>
  <span style="color:#1e3a5f;font-size:.75rem">—</span>
  <span style="color:#4a7090;font-size:.75rem">{DOMAIN_ICONS.get(domain,'')} {domain}</span>
  <span style="color:#1e3a5f;font-size:.7rem;margin-left:auto;font-family:monospace">{st.session_state.research_goal[:35]}</span>
</div>""", unsafe_allow_html=True)

# Domain switcher (compact)
dc = st.columns(len(DOMAINS))
for i,d in enumerate(DOMAINS):
    with dc[i]:
        if st.button(f"{DOMAIN_ICONS[d]} {d}", key=f"dtop_{d}", use_container_width=True,
                     type="primary" if d==domain else "secondary"):
            st.session_state.domain=d; st.session_state.current_protein=None; st.rerun()

# ── Disease trigger ────────────────────────────────────────────────────────
if st.session_state._trigger_disease and st.session_state._dval:
    st.session_state._trigger_disease = False
    ui.show_disease_link_inline(st.session_state._dval)
    st.stop()

# ── Microbiome ─────────────────────────────────────────────────────────────
if domain == "Microbiome":
    T.show_microbiome()
    st.stop()

# ── No query ───────────────────────────────────────────────────────────────
query = st.session_state._qval.strip()
if not query and not st.session_state._trigger_search:
    ui.show_domain_workspace(domain)
    st.stop()
st.session_state._trigger_search = False

# ── Validation ─────────────────────────────────────────────────────────────
if any(t in query.lower() for t in NON_HUMAN_TERMS):
    st.error(f"⛔ '{query}' is not a human protein. Protellect analyses human proteins only (taxon 9606).")
    st.stop()
if not can_search():
    st.error("Search quota exhausted.")
    st.stop()

# ── Load data ──────────────────────────────────────────────────────────────
cache_key = query.upper()
if cache_key not in st.session_state.protein_data_cache:
    prog = st.progress(0, text=f"Resolving {query}…")
    try:
        prog.progress(5,  "UniProt…");       uraw = fetch_uniprot(query)
        prog.progress(15, "Parsing…");       pdata = parse_uniprot(uraw)
        if not pdata or not pdata.get("accession"):
            st.error(f"⛔ '{query}' not found in UniProt Swiss-Prot. Use the official gene symbol."); st.stop()
        if not pdata.get("is_human", True):
            st.error(f"⛔ Not human (organism: {pdata.get('organism','?')})."); st.stop()
        gene=pdata["gene"] or query.upper(); acc=pdata["accession"]
        prog.progress(25, "AlphaFold…");    pdb=fetch_alphafold_pdb(acc); plddt=parse_plddt(pdb)
        prog.progress(35, "ClinVar…");      cv=fetch_clinvar(gene)
        prog.progress(50, "gnomAD + STRING…"); gnomad=fetch_gnomad(gene); string=fetch_string(gene)
        prog.progress(60, "OpenTargets…");  ot=fetch_opentargets(gene); dgidb=fetch_dgidb(gene)
        prog.progress(70, "AlphaMissense + PubMed…"); am=fetch_alphamissense(acc); papers=fetch_pubmed(gene)
        prog.progress(82, "GTEx + KEGG + Trials…"); gtex=fetch_gtex(gene); kegg=fetch_kegg_pathways(gene); trials=fetch_trials(gene)
        prog.progress(93, "Scoring…")
        gi   = score_genomic_integrity(gene, cv, pdata.get("seq_len",500))
        exps = compute_experiment_roi(gene, gi, pdata, cv, gnomad, string, ot, am)
        prog.progress(100, "Complete"); prog.empty()
        st.session_state.protein_data_cache[cache_key] = dict(
            pdata=pdata, pdb=pdb, plddt=plddt, cv=cv, gnomad=gnomad, string=string,
            ot=ot, am=am, papers=papers, gtex=gtex, dgidb=dgidb, trials=trials,
            kegg=kegg, gi=gi, exps=exps)
        record_search()
        ws = st.session_state.workspace
        if not any(w.get("gene")==gene for w in ws):
            ws.insert(0, {"gene":gene,"accession":acc,
                          "protein":pdata.get("protein_name","")[:50],
                          "verdict":gi["verdict"],"color":gi["color"],"domain":domain})
            st.session_state.workspace = ws[:50]
        st.session_state.current_protein = cache_key
    except Exception as e:
        import traceback
        st.error(f"Data loading error: {e}")
        with st.expander("Traceback"): st.code(traceback.format_exc())
        st.stop()
else:
    st.session_state.current_protein = cache_key

# ── Retrieve ───────────────────────────────────────────────────────────────
D     = st.session_state.protein_data_cache[cache_key]
pdata = D["pdata"]; pdb=D["pdb"]; plddt=D["plddt"]; cv=D["cv"]
gnomad= D["gnomad"]; string=D["string"]; ot=D["ot"]; am=D["am"]
papers= D["papers"]; gtex=D["gtex"]; dgidb=D["dgidb"]; trials=D["trials"]
kegg  = D["kegg"]; gi=D["gi"]; exps=D["exps"]
gene  = pdata["gene"] or query.upper(); acc=pdata["accession"]
is_arrb   = gene.upper() in ARRB_GENES
is_gpcr   = pdata.get("is_gpcr", False)
is_cardiac= gene.upper() in {"ADRB1","ADRB2","AGTR1","CHRM2"}
is_filamin= any(k in " ".join(pdata.get("functions",[])+pdata.get("keywords",[])).lower()
                for k in ["filamin","actin-binding protein 280"])

# ── Protein header (compact) ───────────────────────────────────────────────
vcolor=gi["color"]; verdict=gi["verdict"]
flags = ""
if is_gpcr:    flags += ' <span style="background:rgba(0,229,255,0.1);color:#00e5ff;border:1px solid rgba(0,229,255,0.3);border-radius:3px;padding:1px 6px;font-size:.65rem">GPCR</span>'
if is_filamin: flags += ' <span style="background:rgba(249,115,22,0.1);color:#f97316;border:1px solid rgba(249,115,22,0.3);border-radius:3px;padding:1px 6px;font-size:.65rem">FILAMIN</span>'
if is_cardiac: flags += ' <span style="background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.3);border-radius:3px;padding:1px 6px;font-size:.65rem">CARDIAC</span>'
st.markdown(f"""<div style="display:flex;align-items:flex-start;gap:8px;padding:5px 0;border-bottom:1px solid #0a1520;margin-bottom:6px">
  <div style="flex:1">
    <span style="font-size:1rem;font-weight:700;color:#d0e8ff;font-family:monospace">{gene}</span>
    <span style="background:{vcolor}18;color:{vcolor};border:1px solid {vcolor}40;border-radius:4px;padding:1px 7px;font-size:.66rem;font-weight:700;margin-left:5px">{verdict}</span>
    {flags}
    <br><span style="font-size:.7rem;color:#2a5070;font-family:monospace">{acc} · {pdata.get('protein_name','')[:70]}</span>
  </div>
  <div style="display:flex;gap:14px;text-align:right">
    <div><div style="font-size:.8rem;font-weight:700;color:#00e5ff;font-family:monospace">{pdata.get('seq_len',0):,} aa</div><div style="font-size:.6rem;color:#2a5070">length</div></div>
    <div><div style="font-size:.8rem;font-weight:700;color:#ff2d55;font-family:monospace">{gi.get('n_pathogenic',0)}</div><div style="font-size:.6rem;color:#2a5070">P/LP</div></div>
    <div><div style="font-size:.8rem;font-weight:700;color:#00e5ff;font-family:monospace">{f"{gnomad['pLI']:.2f}" if gnomad.get("pLI") else "—"}</div><div style="font-size:.6rem;color:#2a5070">pLI</div></div>
    <div><div style="font-size:.8rem;font-weight:700;color:#4ade80;font-family:monospace">{ot.get('known_drugs_count',0)}</div><div style="font-size:.6rem;color:#2a5070">drugs</div></div>
    <div><div style="font-size:.8rem;font-weight:700;color:#ffd60a;font-family:monospace">{len(trials)}</div><div style="font-size:.6rem;color:#2a5070">trials</div></div>
  </div>
</div>""", unsafe_allow_html=True)

# ── ARRB intercept ─────────────────────────────────────────────────────────
if is_arrb:
    T.show_arrb_analysis(gene, cv, pdata)
    st.stop()

# ── Tabs ───────────────────────────────────────────────────────────────────
t0,t1,t2,t3,t4,t5,t6,t7,t8 = st.tabs([
    "📊 Summary","🎯 Triage","🔬 Case Study","🧩 Explorer",
    "⚗️ Experiments","📋 CSV Analysis","🤖 AI Report","📁 Workspace","🦠 Disease Link"])

with t0: T.tab_summary(gene,pdata,gi,cv,gnomad,ot,dgidb,trials,papers,is_gpcr,is_filamin,is_cardiac,exps)
with t1: T.tab_triage(gene,pdata,pdb,plddt,cv,gnomad,ot,am,sens)
with t2: T.tab_case_study(gene,pdata,cv,gtex,papers,is_gpcr,is_cardiac,is_filamin,string)
with t3: T.tab_explorer(gene,pdata,pdb,plddt,cv,am,string)
with t4: T.tab_experiments(gene,exps,cv,gi,is_gpcr,is_arrb,kegg)
with t5: T.tab_csv_analysis(gene,pdata,gi)
with t6: T.tab_ai_report(gene,pdata,cv,gnomad,string,ot,papers)
with t7: T.tab_workspace()
with t8: T.tab_disease_link()
