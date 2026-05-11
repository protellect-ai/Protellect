"""
Protellect v3 — Genetics-First Protein Intelligence Platform
Complete rewrite per workflow specification.
"""
import streamlit as st
import streamlit.components.v1 as components
import hashlib, re, math, time, json
import numpy as np, pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="Protellect",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
# CSS — DM Sans font, safe selectors only, never touch icon spans
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

/* Apply font ONLY to content — never to span (breaks icons) */
.stMarkdown, .stMarkdown *, .stText, .stCaption,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stMetricLabel"], [data-testid="stMetricValue"],
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stAlert"] *, [data-testid="stExpander"] summary,
[data-testid="stTabs"] [data-baseweb="tab"],
.stButton > button, p, h1, h2, h3, h4 {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px;
}

/* Hide ALL Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"] *,
header { display: none !important; visibility: hidden !important; }

html, body, [data-testid="stAppViewContainer"] { background: #060b14 !important; }
.block-container { padding: .4rem 1rem !important; max-width: 100%; }
::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-thumb { background: #1a2a3a; border-radius: 2px; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #080f1a !important;
  border-right: 1px solid #1a2a3a !important;
  min-width: 270px !important; max-width: 270px !important;
  display: block !important; transform: translateX(0) !important; visibility: visible !important;
}
[data-testid="stSidebar"] .block-container { padding: .5rem .7rem !important; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #080f1a; border-radius: 8px; padding: 3px; gap: 2px; border: 1px solid #1a2a3a;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 6px; color: #3a5570; font-size: .72rem; font-weight: 500; padding: 5px 12px; min-height: 28px;
}
[data-testid="stTabs"] [aria-selected="true"] {
  background: rgba(0,229,255,.1) !important; color: #00e5ff !important; border: 1px solid rgba(0,229,255,.2) !important;
}

/* Metrics */
[data-testid="stMetric"] { background: #080f1a; border: 1px solid #1a2a3a; border-radius: 8px; padding: 8px 12px; }
[data-testid="stMetricValue"] { color: #00e5ff !important; font-size: .9rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #3a5570 !important; font-size: .6rem !important; text-transform: uppercase; letter-spacing: .06em; }

/* Expanders */
[data-testid="stExpander"] { background: #080f1a !important; border: 1px solid #1a2a3a !important; border-radius: 6px; margin: 3px 0; }
[data-testid="stExpander"] summary { color: #5a7590 !important; font-size: .72rem !important; }
[data-testid="stExpander"] summary:hover { color: #00e5ff !important; }

/* Inputs */
[data-testid="stTextInput"] input {
  background: #080f1a !important; border: 1px solid #1a2a3a !important;
  color: #d0e8ff !important; border-radius: 5px !important; font-size: .78rem !important; padding: 5px 9px !important;
}
[data-testid="stTextInput"] input:focus { border-color: rgba(0,229,255,.4) !important; }
[data-testid="stTextArea"] textarea {
  background: #080f1a !important; border: 1px solid #1a2a3a !important; color: #d0e8ff !important;
  border-radius: 5px !important; font-size: .74rem !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #080f1a !important; border-color: #1a2a3a !important; font-size: .74rem !important;
}
[data-testid="stFileUploader"] { border: 1px dashed #1a2a3a !important; border-radius: 5px !important; background: #080f1a !important; }

/* Buttons */
.stButton > button {
  background: #080f1a; border: 1px solid #1a2a3a; color: #7a9aaa;
  border-radius: 5px; padding: 4px 12px; min-height: 30px; transition: all .15s;
  font-size: .73rem;
}
.stButton > button:hover { background: #0f1f2f; border-color: rgba(0,229,255,.25); color: #00e5ff; }
.stButton > button[kind="primary"] {
  background: rgba(0,229,255,.08) !important; border-color: rgba(0,229,255,.35) !important;
  color: #00e5ff !important; font-weight: 600 !important;
}

/* Utility */
.sec { font-size: .74rem; font-weight: 600; color: #00e5ff; border-bottom: 1px solid #1a2a3a; padding-bottom: 5px; margin: 12px 0 8px; }
.card { background: #080f1a; border: 1px solid #1a2a3a; border-radius: 6px; padding: 10px 14px; margin: 4px 0; }
.pill { display: inline-block; background: rgba(0,229,255,.06); color: #00e5ff; border: 1px solid rgba(0,229,255,.15); border-radius: 10px; padding: 1px 8px; font-size: .65rem; margin: 2px; text-decoration: none; }
.dim { color: #3a5570; font-size: .69rem; }
.badge-crit { background: rgba(255,45,85,.12); color: #ff2d55; border: 1px solid rgba(255,45,85,.3); border-radius: 4px; padding: 1px 7px; font-size: .63rem; font-weight: 700; }
.badge-high { background: rgba(255,140,66,.1); color: #ff8c42; border: 1px solid rgba(255,140,66,.3); border-radius: 4px; padding: 1px 7px; font-size: .63rem; font-weight: 700; }
.badge-mod  { background: rgba(255,214,10,.07); color: #ffd60a; border: 1px solid rgba(255,214,10,.25); border-radius: 4px; padding: 1px 7px; font-size: .63rem; font-weight: 700; }
.badge-neu  { background: rgba(58,85,112,.15); color: #5a7590; border: 1px solid #1a2a3a; border-radius: 4px; padding: 1px 7px; font-size: .63rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


def _sec(t): st.markdown(f'<div class="sec">{t}</div>', unsafe_allow_html=True)
def _h(pw): return hashlib.sha256(pw.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════
ACCOUNTS = {
    "protellect@gmail.com": {"hash": _h("dev@protellect"), "tier": "enterprise", "name": "Dr Smith", "quota": 999999, "dev": True},
    "demo@protellect.io":   {"hash": _h("demo2025"),       "tier": "free",       "name": "Demo User", "quota": 5,      "dev": False},
}
def _authed(): return bool(st.session_state.get("auth_user"))
def _user():   return st.session_state.get("auth_user", {})
def _used():   return st.session_state.get("searches_used", 0)
def _quota():  return _user().get("quota", 5)
def _can():    u = _user(); return True if (u.get("dev") or u.get("tier") == "enterprise") else _used() < _quota()
def _record():
    if not _user().get("dev"): st.session_state.searches_used = _used() + 1
def _logout():
    for k in ["auth_user","searches_used","workspace","current_protein","protein_data_cache","domain"]:
        st.session_state.pop(k, None)

if not _authed():
    _, cc, _ = st.columns([1, 1.3, 1])
    with cc:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        st.markdown("""<div style='text-align:center;margin-bottom:24px'>
          <div style='font-size:2.2rem;font-weight:700;background:linear-gradient(90deg,#00e5ff,#7c3aed);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px'>🔬 Protellect</div>
          <div style='color:#3a5570;font-size:.75rem;margin-top:4px;letter-spacing:.12em'>GENETICS-FIRST PROTEIN INTELLIGENCE</div>
        </div>""", unsafe_allow_html=True)
        tl, td = st.tabs(["Sign In", "Try Demo"])
        with tl:
            em = st.text_input("Email", placeholder="you@example.com", key="li_em")
            pw = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign In →", type="primary", use_container_width=True, key="li_btn"):
                ac = ACCOUNTS.get(em.strip().lower())
                if ac and ac["hash"] == _h(pw):
                    st.session_state.auth_user = {"email": em, "name": ac["name"], "tier": ac["tier"], "quota": ac["quota"], "dev": ac["dev"]}
                    st.session_state.searches_used = 0; st.session_state.workspace = []
                    st.session_state.show_tutorial = True; st.rerun()
                else: st.error("Invalid credentials.")
        with td:
            dn = st.text_input("Name", placeholder="Dr. Smith", key="td_n")
            de = st.text_input("Email", placeholder="you@lab.edu", key="td_e")
            if st.button("Start Free Trial →", type="primary", use_container_width=True, key="td_btn"):
                if dn and de:
                    st.session_state.auth_user = {"email": de, "name": dn, "tier": "free", "quota": 5, "dev": False}
                    st.session_state.searches_used = 0; st.session_state.workspace = []
                    st.session_state.show_tutorial = True; st.rerun()
                else: st.warning("Enter name and email.")
        st.markdown("""<div style='display:flex;gap:8px;margin-top:16px'>
          <div style='flex:1;background:#080f1a;border:1px solid #1a2a3a;border-radius:8px;padding:12px;text-align:center'>
            <div style='color:#3a5570;font-size:.68rem;font-weight:600'>FREE</div>
            <div style='color:#d0e8ff;font-size:1.1rem;font-weight:700;margin:2px 0'>$0</div>
            <div style='color:#3a5570;font-size:.68rem'>5 searches/month</div></div>
          <div style='flex:1;background:rgba(0,229,255,.04);border:1px solid rgba(0,229,255,.2);border-radius:8px;padding:12px;text-align:center'>
            <div style='color:#00e5ff;font-size:.68rem;font-weight:600'>PRO</div>
            <div style='color:#d0e8ff;font-size:1.1rem;font-weight:700;margin:2px 0'>$49/mo</div>
            <div style='color:#3a5570;font-size:.68rem'>200 searches</div></div>
          <div style='flex:1;background:rgba(249,115,22,.04);border:1px solid rgba(249,115,22,.2);border-radius:8px;padding:12px;text-align:center'>
            <div style='color:#f97316;font-size:.68rem;font-weight:600'>ENTERPRISE</div>
            <div style='color:#d0e8ff;font-size:1.1rem;font-weight:700;margin:2px 0'>$299/mo</div>
            <div style='color:#3a5570;font-size:.68rem'>Unlimited</div></div>
        </div>""", unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════
for k, v in {
    "workspace": [], "current_protein": None, "protein_data_cache": {},
    "domain": None, "research_goal": "Drug target identification",
    "anthropic_key": "", "sensitivity": 0.70, "csv_data": None,
    "wet_lab_text": "", "_qval": "", "_dval": "",
    "_trig": False, "_dtrig": False, "show_tutorial": False,
}.items():
    if k not in st.session_state: st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════
# DATABASES
# ═══════════════════════════════════════════════════════════════════
NON_HUMAN = ["gelatin","gfp","luciferase","ovalbumin","bovine","collagen extract","beta keratin","algae"]
DOMAIN_EXAMPLES = {
    "Neuroscience":     ["APP","SNCA","MAPT","LRRK2","TARDBP","HTT","GBA","FUS","SOD1","PINK1"],
    "Cancer Biology":   ["TP53","KRAS","BRCA1","EGFR","MYC","PTEN","APC","BRAF","CDKN2A","RB1"],
    "Pharmaceuticals":  ["ADRB2","ADRB1","AGTR1","DRD2","HTR2A","FLNA","GRK2","OPRM1","CHRM2","MAS1"],
    "Microbiome":       [],
    "Molecular Biology":["FLNA","GRK2","MAPK1","AKT1","SRC","CDK2","EGFR","JAK2","STAT3","PIK3CA"],
}
DOMAIN_META = {
    "Neuroscience":    {"icon":"🧠","color":"#818cf8","glow":"rgba(129,140,248,0.2)","tags":["Alzheimer's","Parkinson's","ALS","Epilepsy","BBB Penetrance","Synaptic Biology","Neurodegeneration","Huntington's","MS","Dementia"],"desc":"Neurological disease genetics, BBB penetrance, brain expression, synaptic networks."},
    "Cancer Biology":  {"icon":"🎗","color":"#f43f5e","glow":"rgba(244,63,94,0.2)","tags":["Oncogenes","Tumour Suppressors","Somatic Hotspots","Founder Mutations","COSMIC","cfDNA","CRC","Breast","Lung","Leukaemia"],"desc":"Founder mutation identification, somatic/germline triage, 14 cancer type breakdown."},
    "Pharmaceuticals": {"icon":"💊","color":"#00e5ff","glow":"rgba(0,229,255,0.2)","tags":["GPCR Targets","Filamin Ser2152-P","Drug Tractability","BRET Assays","Biased Agonism","Clinical Trials","TMAO Arrhythmia","cAMP HTRF","HTS","Phase III"],"desc":"GPCR piggyback analysis, Filamin Ser2152-P IP assay, drug tractability, clinical trials."},
    "Microbiome":      {"icon":"🦠","color":"#4ade80","glow":"rgba(74,222,128,0.2)","tags":["LLM Annotation","BGC","Taxonomy","Host–Microbe","Gut Ecology","SCFA","Pathobionts","Curli","NRP Synthetase","PKS"],"desc":"AI gene annotation, biosynthetic gene clusters, pathogen host-receptor mapping."},
    "Molecular Biology":{"icon":"⚛️","color":"#f97316","glow":"rgba(249,115,22,0.2)","tags":["Phosphorylation","Kinase Signalling","AlphaFold","STRING","PTMs","Structural Domains","Variant Impact","Co-IP","SPR","Proteomics"],"desc":"Phosphorylation signal/noise, AlphaMissense, 3D structure, interaction networks."},
}
VERDICT_COLORS = {
    "DISEASE-CRITICAL":"#ff2d55","DISEASE-ASSOCIATED":"#ff8c42",
    "MODERATE":"#ffd60a","VERY LOW":"#3a5570",
    "DEPRIORITISE":"#ef4444","NO DISEASE VARIANTS":"#334155",
}
ICONS = {d: DOMAIN_META[d]["icon"] for d in DOMAIN_META}

# Common name → gene symbol map
NAME_MAP = {
    "filamin a":"FLNA","filamin-a":"FLNA","filamin":"FLNA","filamin b":"FLNB","filamin c":"FLNC",
    "beta arrestin 2":"ARRB2","beta-arrestin-2":"ARRB2","arrestin 2":"ARRB2","beta arrestin2":"ARRB2",
    "beta arrestin 1":"ARRB1","arrestin 1":"ARRB1",
    "p53":"TP53","tumor protein p53":"TP53","p21":"CDKN1A",
    "alpha synuclein":"SNCA","alpha-synuclein":"SNCA","synuclein":"SNCA",
    "tau":"MAPT","tau protein":"MAPT","microtubule-associated protein tau":"MAPT",
    "amyloid precursor":"APP","amyloid":"APP","amyloid beta precursor":"APP",
    "beta 2 adrenergic":"ADRB2","beta-2 adrenergic":"ADRB2","b2ar":"ADRB2","beta2ar":"ADRB2",
    "beta 1 adrenergic":"ADRB1","b1ar":"ADRB1",
    "angiotensin":"AGTR1","at1r":"AGTR1","angiotensin ii type 1":"AGTR1",
    "dopamine d2":"DRD2","d2 receptor":"DRD2",
    "grk2":"GRK2","g protein-coupled receptor kinase 2":"GRK2",
    "akt":"AKT1","akt1":"AKT1","pkb":"AKT1",
    "brca":"BRCA1","kras":"KRAS","nras":"NRAS","hras":"HRAS",
    "egfr":"EGFR","her1":"EGFR","epidermal growth factor receptor":"EGFR",
    "huntingtin":"HTT","htt":"HTT",
    "lrrk2 kinase":"LRRK2","leucine rich repeat kinase 2":"LRRK2",
    "superoxide dismutase":"SOD1","sod1":"SOD1",
    "fus protein":"FUS","tdp-43":"TARDBP","tdp43":"TARDBP",
}

HDR = {"User-Agent": "Protellect/3.0 (protellect@gmail.com)"}


# ═══════════════════════════════════════════════════════════════════
# API FETCHERS
# ═══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400, show_spinner=False)
def _uniprot(raw_query):
    """Search UniProt: gene symbol → protein name → full text."""
    q = re.sub(r"['\"\(\)]", "", raw_query).strip()
    def _get(acc):
        r = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc}.json", headers=HDR, timeout=20)
        r.raise_for_status(); return r.json()
    try:
        for query_str in [
            f"gene:{q} AND organism_id:9606 AND reviewed:true",
            f"protein_name:{q} AND organism_id:9606 AND reviewed:true",
            f"({q}) AND organism_id:9606 AND reviewed:true",
        ]:
            r = requests.get("https://rest.uniprot.org/uniprotkb/search",
                params={"query": query_str, "format": "json", "size": 1}, headers=HDR, timeout=15)
            res = r.json().get("results", [])
            if res: return _get(res[0]["primaryAccession"])
        return {}
    except: return {}


def _parse(e):
    """Parse UniProt JSON entry. Uses 'name' field (new API) with 'diseaseName' fallback."""
    if not e: return {}
    seq = e.get("sequence", {}).get("value", "")
    genes = [g.get("geneName", {}).get("value", "") for g in e.get("genes", []) if g.get("geneName", {}).get("value")]
    diseases, functions, subcell, domains_f, ptms, tissues = [], [], [], [], [], []
    
    # Extract UniProt natural variants (primary disease variant source, more reliable than ClinVar on cloud)
    uni_variants = []
    for f in e.get("features", []):
        if f.get("type") == "NATURAL_VARIANT":
            desc = f.get("description", "")
            loc = f.get("location", {}); pos = loc.get("start", {}).get("value", 0)
            orig = f.get("alternativeSequence", {}).get("originalSequence", "")
            alts = f.get("alternativeSequence", {}).get("alternativeSequences", [])
            alt = alts[0] if alts else "?"
            is_disease = any(k in desc.lower() for k in ["disease", "in patient", "pathogenic", "associated with", "syndrome"])
            if is_disease and pos:
                cls = "CRITICAL" if "disease" in desc.lower() else "HIGH"
                uni_variants.append({
                    "id": f.get("ftId", f"UNI{pos}"),
                    "title": f"{orig}{pos}{alt} — {desc[:60]}",
                    "significance": "Pathogenic" if cls == "CRITICAL" else "Likely pathogenic",
                    "ml_class": cls, "protein_change": f"{orig}{pos}{alt}",
                    "position": pos, "conditions": [desc[:60]] if desc else [],
                    "stars": 2, "source": "UniProt",
                    "url": f"https://www.uniprot.org/uniprotkb/{e.get('primaryAccession','')}/entry",
                })
        elif f.get("type") in ("DOMAIN", "REGION", "MOTIF", "DNA_BIND", "ACT_SITE", "BINDING", "METAL", "CARBOHYD"):
            loc = f.get("location", {}); s = loc.get("start", {}).get("value", "?"); en = loc.get("end", {}).get("value", "?")
            domains_f.append({"type": f["type"], "name": f.get("description", f["type"]), "start": s, "end": en})
    
    for c in e.get("comments", []):
        ct = c.get("commentType", "")
        if ct == "DISEASE":
            d = c.get("disease", {})
            # UniProt API 2024: field is "name" not "diseaseName"
            name = d.get("name") or d.get("diseaseName") or d.get("acronym") or "Unnamed disease"
            desc_txt = d.get("description", "")[:200]
            # Classify somatic vs germline from disease name and description
            somatic = any(k in (name + desc_txt).lower() for k in ["cancer","tumor","tumour","carcinoma","sarcoma","lymphoma","leukaemia","leukemia","somatic"])
            inheritance = "Somatic" if somatic else "Germline"
            diseases.append({"name": name, "desc": desc_txt, "inheritance": inheritance, "omim": d.get("diseaseAccession", "")})
        elif ct == "FUNCTION":
            for t in c.get("texts", []): functions.append(t.get("value", "")[:400])
        elif ct == "SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations", []): subcell.append(loc.get("location", {}).get("value", ""))
        elif ct == "PTM":
            for t in c.get("texts", []): ptms.append(t.get("value", "")[:200])
        elif ct == "TISSUE SPECIFICITY":
            for t in c.get("texts", []): tissues.append(t.get("value", "")[:200])
    
    kws = [k.get("name", "") for k in e.get("keywords", [])]; kl = " ".join(kws).lower()
    is_gpcr = any(x in kl for x in ["g protein-coupled", "gpcr", "seven-transmembrane"])
    is_kinase = any(x in kl for x in ["kinase", "phosphotransferase"])
    is_phosphatase = any(x in kl for x in ["phosphatase"])
    org = e.get("organism", {}); taxid = org.get("taxonId", 0)
    
    # Binding sites from features
    binding_sites = [f for f in domains_f if f["type"] in ("BINDING", "ACT_SITE", "METAL", "DNA_BIND")]
    phospho_sites = []
    for f in e.get("features", []):
        if f.get("type") in ("MOD_RES",) and "phospho" in f.get("description", "").lower():
            pos = f.get("location", {}).get("start", {}).get("value", 0)
            phospho_sites.append({"position": pos, "name": f.get("description", "Phosphoserine")})
    
    return {
        "accession": e.get("primaryAccession", ""), "gene": genes[0] if genes else "",
        "protein_name": e.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
        "organism": org.get("scientificName", ""), "taxon_id": taxid, "is_human": taxid == 9606,
        "sequence": seq, "seq_len": len(seq), "diseases": diseases, "functions": functions,
        "subcellular": list(set(subcell)), "domains": domains_f, "ptms": ptms, "tissues": tissues,
        "keywords": kws, "is_gpcr": is_gpcr, "is_kinase": is_kinase, "is_phosphatase": is_phosphatase,
        "mw_kda": round(len(seq) * 110 / 1000, 1), "uni_variants": uni_variants,
        "binding_sites": binding_sites, "phospho_sites": phospho_sites,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _clinvar(gene, mx=80):
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "clinvar", "term": f"{gene}[gene] AND homo sapiens[organism]",
                    "retmax": mx, "retmode": "json"}, headers=HDR, timeout=20)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        time.sleep(0.4)
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(ids[:mx]), "retmode": "json"}, headers=HDR, timeout=25)
        res = r2.json().get("result", {}); out = []
        for uid in res.get("uids", []):
            v = res.get(uid, {}); sig = v.get("clinical_significance", {}).get("description", "Unknown"); sl = sig.lower()
            if "pathogenic" in sl and "likely" not in sl: cls = "CRITICAL"
            elif "likely pathogenic" in sl: cls = "HIGH"
            elif "uncertain" in sl: cls = "MODERATE"
            else: cls = "LOW"
            pc = v.get("protein_change", ""); pos = 0
            m = re.search(r'(\d+)', pc)
            if m: pos = int(m.group(1))
            stars = {"no assertion":0,"criteria provided, single":1,"criteria provided, multiple":2,"reviewed by expert":4}.get(
                (v.get("review_status","") or "").lower()[:30], 0)
            out.append({
                "id": uid, "title": v.get("title", ""), "significance": sig, "ml_class": cls,
                "protein_change": pc, "position": pos,
                "conditions": [c.get("trait_name", "") for c in v.get("trait_set", [])],
                "stars": stars, "source": "ClinVar",
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
            })
        return sorted(out, key=lambda x: x["ml_class"] == "CRITICAL", reverse=True)
    except: return []


@st.cache_data(ttl=604800, show_spinner=False)
def _alphafold(acc):
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{acc.upper()}-F1-model_v4.pdb", headers=HDR, timeout=30)
        r.raise_for_status(); return r.text
    except: return ""


def _plddt(pdb):
    d = {}
    for line in (pdb or "").splitlines():
        if line.startswith("ATOM"):
            try:
                ri = int(line[22:26].strip()); b = float(line[60:66].strip())
                d.setdefault(ri, b)
            except: pass
    return d


@st.cache_data(ttl=604800, show_spinner=False)
def _alphamissense(acc):
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{acc.upper()}-F1-aa-substitutions.csv", headers=HDR, timeout=30)
        if r.status_code != 200: return []
        out = []
        for line in r.text.strip().splitlines()[1:]:
            p = line.split(",")
            if len(p) >= 4:
                try: out.append({"position":int(p[0]),"ref":p[1],"alt":p[2],"score":float(p[3]),"class":"pathogenic" if float(p[3])>=0.564 else "benign"})
                except: pass
        return out
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _pubmed(gene, n=25):
    """Fetch highly cited papers with evidence tier classification."""
    qs = [
        f"{gene}[gene] pathogenic variant clinical 2020:2025[pdat]",
        f"{gene} functional assay CRISPR 2019:2025[pdat]",
        f"{gene} therapy treatment drug 2020:2025[pdat]",
        f"{gene} disease mechanism phenotype 2018:2025[pdat]",
        f"{gene} structure crystal cryo-em alphafold 2018:2025[pdat]",
    ]
    all_p = []; seen = set()
    TMAP = {1:"#00e5ff",2:"#4ade80",3:"#818cf8",4:"#f97316",5:"#fbbf24",6:"#94a3b8",8:"#475569"}
    LMAP = {1:"RCT",2:"Cohort",3:"Functional",4:"Structural",5:"Animal",6:"Computational",8:"Review"}
    def _tier(t):
        tl = t.lower()
        if any(k in tl for k in ["randomised","randomized","phase iii","placebo"]): return 1
        if any(k in tl for k in ["cohort","prospective","retrospective","population"]): return 2
        if any(k in tl for k in ["crispr","knock-in","western","functional","assay"]): return 3
        if any(k in tl for k in ["cryo-em","nmr","crystal","x-ray","alphafold","structure"]): return 4
        if any(k in tl for k in ["mouse","zebrafish","xenograft","animal"]): return 5
        if any(k in tl for k in ["in silico","computational","machine learning","model"]): return 6
        return 8
    for q in qs:
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db":"pubmed","term":q,"retmax":6,"retmode":"json","sort":"relevance"}, headers=HDR, timeout=12)
            ids = [i for i in r.json().get("esearchresult",{}).get("idlist",[]) if i not in seen]
            seen.update(ids)
            if not ids: continue
            time.sleep(0.4)
            r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, headers=HDR, timeout=15)
            res = r2.json().get("result",{})
            for pid in ids:
                p = res.get(pid,{}); au = p.get("authors",[]); fa = au[0].get("name","") if au else ""; t = p.get("title",""); tier = _tier(t)
                all_p.append({"pmid":pid,"title":t,"year":p.get("pubdate","")[:4],
                    "authors":f"{fa} et al." if len(au)>1 else fa,
                    "journal":p.get("source",""),"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    "tier":tier,"tier_label":LMAP.get(tier,"Study"),"tier_color":TMAP.get(tier,"#475569")})
        except: pass
    return sorted(all_p, key=lambda x: x["tier"])[:n]


@st.cache_data(ttl=86400, show_spinner=False)
def _gnomad(gene):
    q = 'query G($g:String!){gene(gene_symbol:$g,reference_genome:GRCh38){gnomad_constraint{pLI lof{oe}missense{oe}}}}'
    try:
        r = requests.post("https://gnomad.broadinstitute.org/api",
            json={"query":q,"variables":{"g":gene}},
            headers={**HDR,"Content-Type":"application/json"}, timeout=20)
        c = (r.json().get("data",{}).get("gene",{}) or {}).get("gnomad_constraint",{}) or {}
        pLI = c.get("pLI"); loe = (c.get("lof",{}) or {}).get("oe"); moe = (c.get("missense",{}) or {}).get("oe")
        return {"pLI":round(float(pLI),3) if pLI else None,"lof_oe":round(float(loe),3) if loe else None,
                "missense_oe":round(float(moe),3) if moe else None,"essential":float(pLI)>0.9 if pLI else False}
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _string(gene, lim=20):
    try:
        r = requests.get("https://string-db.org/api/json/get_string_ids",
            params={"identifiers":gene,"species":9606,"limit":1,"caller_identity":"protellect"}, headers=HDR, timeout=12)
        d = r.json()
        if not d: return []
        sid = d[0].get("stringId","")
        r2 = requests.get("https://string-db.org/api/json/interaction_partners",
            params={"identifiers":sid,"species":9606,"limit":lim,"required_score":700,"caller_identity":"protellect"}, headers=HDR, timeout=15)
        return [{"partner":i.get("preferredName_B",""),"score":round(i.get("score",0),3),
                 "experimental":round(i.get("escore",0),3)} for i in r2.json()]
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _opentargets(gene):
    try:
        r = requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene", headers=HDR, timeout=10)
        hits = r.json().get("hits",[]); eid = (hits[0].get("ensembl",{}).get("gene","") if hits else "")
        if isinstance(eid, list): eid = eid[0]
        if not eid: return {}
        q = 'query O($id:String!){target(ensemblId:$id){tractability{smallMolecule{value}antibody{value}}knownDrugs{count rows{drug{name}phase status}}}}'
        r2 = requests.post("https://api.platform.opentargets.org/api/v4/graphql",
            json={"query":q,"variables":{"id":eid}}, headers={**HDR,"Content-Type":"application/json"}, timeout=20)
        tgt = (r2.json().get("data",{}).get("target",{}) or {})
        tr = tgt.get("tractability",{}) or {}; kd = tgt.get("knownDrugs",{}) or {}
        return {
            "sm_tractable":any((t or {}).get("value") for t in (tr.get("smallMolecule") or [{}])),
            "ab_tractable":any((t or {}).get("value") for t in (tr.get("antibody") or [{}])),
            "known_drugs_count":kd.get("count",0),
            "known_drugs":[(r.get("drug",{}) or {}).get("name","") for r in (kd.get("rows") or [])[:8]],
        }
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _gtex(gene):
    try:
        r = requests.get("https://gtexportal.org/api/v2/expression/medianGeneExpression",
            params={"geneId":gene,"datasetId":"gtex_v8","format":"json"}, headers=HDR, timeout=20)
        return {i.get("tissueSiteDetailId","").replace("_"," "): i.get("median",0) for i in r.json().get("medianGeneExpression",[])}
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _trials(gene):
    try:
        r = requests.get("https://clinicaltrials.gov/api/v2/studies",
            params={"query.term":gene,"filter.status":"RECRUITING","pageSize":8}, headers=HDR, timeout=15)
        out = []
        for s in r.json().get("studies",[]):
            mod = s.get("protocolSection",{}); im = mod.get("identificationModule",{}); dm = mod.get("designModule",{})
            out.append({"nct_id":im.get("nctId",""),"title":im.get("briefTitle","")[:80],
                "phase":(dm.get("phases",["?"])[0] if dm.get("phases") else "?"),
                "url":f"https://clinicaltrials.gov/study/{im.get('nctId','')}"})
        return out
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _dgidb(gene):
    try:
        r = requests.get("https://dgidb.org/api/v2/interactions.json", params={"genes":gene}, headers=HDR, timeout=12)
        out = []
        for m in r.json().get("matchedTerms",[]):
            for i in m.get("interactions",[])[:8]:
                d = i.get("drugName","")
                if d: out.append({"drug":d,"type":(i.get("interactionTypes",["?"])[0] if i.get("interactionTypes") else "?")})
        return out[:10]
    except: return []


# ═══════════════════════════════════════════════════════════════════
# GI SCORER (no mandatory ARRB deprioritize — only if asked)
# ═══════════════════════════════════════════════════════════════════
def _gi(gene, cv, seq_len):
    path = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")]
    n_p = len(path); n_c = sum(1 for v in cv if v.get("ml_class")=="CRITICAL")
    ms = sum(1 for v in path if v.get("stars",0)>=2)
    per100 = (n_p / seq_len * 100) if seq_len else 0
    reasons = []
    if n_p >= 5: reasons.append(f"{n_p} P/LP variants")
    if ms >= 2: reasons.append(f"{ms} multi-star expert reviewed")
    if per100 >= 1: reasons.append(f"{per100:.2f} P/LP per 100 aa")
    if per100 >= 1 and n_p >= 5 and ms >= 2: v2, p = "DISEASE-CRITICAL", True
    elif per100 >= 0.5 or n_p >= 3: v2, p = "DISEASE-ASSOCIATED", True
    elif per100 >= 0.1 or n_p >= 1: v2, p = "MODERATE", None
    elif n_p == 0: v2, p = "NO DISEASE VARIANTS", False; reasons.append("No ClinVar P/LP — null mutant with no phenotype")
    else: v2, p = "VERY LOW", False
    return {"verdict":v2,"color":VERDICT_COLORS.get(v2,"#3a5570"),"n_pathogenic":n_p,"n_critical":n_c,
            "per100":round(per100,3),"multi_star":ms,"reasons":reasons or ["Insufficient variant density"],"pursue":p}


def _classify_severity(v):
    """Classify individual variant as Critical/High/Medium/Neutral for sidebar."""
    cls = v.get("ml_class","LOW")
    if cls == "CRITICAL": return "Critical", "#ff2d55", "badge-crit"
    elif cls == "HIGH": return "High", "#ff8c42", "badge-high"
    elif cls == "MODERATE": return "Medium", "#ffd60a", "badge-mod"
    else: return "Neutral", "#3a5570", "badge-neu"


# ═══════════════════════════════════════════════════════════════════
# 3D VIEWER (AlphaFold + variant spheres)
# ═══════════════════════════════════════════════════════════════════
def _viewer3d(pdb, cv=None, style="plddt", height=420, spin=False, show_variants=True):
    if not pdb:
        st.markdown('<div class="dim" style="padding:12px">AlphaFold structure not available.</div>', unsafe_allow_html=True)
        return
    esc = pdb.replace("\\","\\\\").replace("`","\\`")
    sp = "viewer.spin(true);" if spin else ""
    # Build variant sphere JS
    var_js = ""
    if show_variants and cv:
        path_vars = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH") and v.get("position",0) > 0]
        for v in path_vars[:50]:
            pos = v["position"]; col = "#ff2d55" if v["ml_class"]=="CRITICAL" else "#ff8c42"
            label = (v.get("protein_change","") or "")[:20]
            var_js += f"viewer.addStyle({{resi:{pos}}},{{sphere:{{color:'{col}',radius:1.2,opacity:0.85}}}});"
    style_js = {
        "plddt": "viewer.setStyle({},{cartoon:{colorfunc:function(a){var b=a.b;if(b>=90)return'#00c4e0';if(b>=70)return'#35c7a3';if(b>=50)return'#f5c842';return'#e05c5c';}}});",
        "spectrum": "viewer.setStyle({},{cartoon:{color:'spectrum'}});",
        "surface": "viewer.addSurface($3Dmol.SurfaceType.VDW,{opacity:0.75,colorscheme:'spectrum'});viewer.setStyle({},{cartoon:{color:'spectrum',opacity:0.3}});",
        "stick": "viewer.setStyle({},{stick:{colorscheme:'element'}});",
    }.get(style, "viewer.setStyle({},{cartoon:{color:'spectrum'}});")
    
    html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>
body{{margin:0;background:#060b14;overflow:hidden}}
#v{{width:100%;height:{height}px}}
#info{{position:absolute;bottom:8px;left:8px;background:rgba(6,11,20,.96);color:#d0e8ff;
  border:1px solid rgba(0,229,255,.2);border-radius:6px;padding:7px 12px;font:11px/1.6 monospace;
  display:none;z-index:100;max-width:300px;pointer-events:none}}
#legend{{position:absolute;top:8px;right:8px;background:rgba(8,15,26,.92);color:#d0e8ff;
  border:1px solid #1a2a3a;border-radius:6px;padding:8px 12px;font:10px monospace}}
.lr{{display:flex;align-items:center;gap:6px;margin:2px 0}}
.lc{{width:11px;height:11px;border-radius:3px;flex-shrink:0}}
#variant-legend{{position:absolute;bottom:8px;right:8px;background:rgba(8,15,26,.92);
  color:#d0e8ff;border:1px solid #1a2a3a;border-radius:6px;padding:7px 10px;font:10px monospace}}
</style></head><body>
<div id="v"></div>
<div id="info"></div>
<div id="legend">
  <b style="color:#00e5ff;font-size:10px">pLDDT</b>
  <div class="lr"><div class="lc" style="background:#00c4e0"></div>&gt;90 Very High</div>
  <div class="lr"><div class="lc" style="background:#35c7a3"></div>70–90 Confident</div>
  <div class="lr"><div class="lc" style="background:#f5c842"></div>50–70 Low</div>
  <div class="lr"><div class="lc" style="background:#e05c5c"></div>&lt;50 Very Low</div>
</div>
{"<div id='variant-legend'><b style='color:#ff2d55;font-size:10px'>● Critical variants</b><br><b style='color:#ff8c42;font-size:10px'>● High variants</b></div>" if show_variants and cv else ""}
<script>
try{{
  var viewer = $3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#060b14'}});
  viewer.addModel(`{esc}`,'pdb');
  {style_js}
  {var_js}
  viewer.setClickable({{}},true,function(a,v){{
    var b=document.getElementById('info');b.style.display='block';
    var conf=a.b?a.b.toFixed(1):'N/A';
    var confLabel=a.b>=90?'Very High':a.b>=70?'Confident':a.b>=50?'Low':'Very Low';
    b.innerHTML='<b style="color:#00e5ff">'+a.resn+' '+a.resi+'</b>  Chain '+a.chain+
      '<br>pLDDT: <b style="color:#35c7a3">'+conf+'</b> ('+confLabel+')'+
      '<br>Atom: '+a.atom;
    v.addStyle({{resi:a.resi}},{{sphere:{{color:'#00e5ff',radius:0.9,opacity:0.7}}}});
    v.render();
  }});
  viewer.zoomTo();{sp}
  viewer.render();
}}catch(e){{
  document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:14px;font:12px monospace">Viewer error: '+e.message+'</p>';
}}
</script></body></html>"""
    components.html(html, height=height, scrolling=False)


# ═══════════════════════════════════════════════════════════════════
# TUTORIAL
# ═══════════════════════════════════════════════════════════════════
def _tutorial():
    if not st.session_state.get("show_tutorial"): return
    st.markdown("""
    <div style="background:linear-gradient(135deg,#080f1a,#0d1a2d);border:1.5px solid rgba(0,229,255,.3);
         border-radius:14px;padding:22px 26px;margin-bottom:14px">
      <div style="font-size:.95rem;font-weight:700;color:#00e5ff;margin-bottom:12px">Welcome to Protellect v3</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
        <div style="background:#060b14;border:1px solid #1a2a3a;border-radius:8px;padding:11px">
          <div style="color:#00e5ff;font-size:.73rem;font-weight:600;margin-bottom:4px">1 · Enter a Gene</div>
          <div style="color:#3a5570;font-size:.7rem;line-height:1.6">Type any gene symbol (FLNA, TP53) or protein name (filamin A, p53) in the Protein Search sidebar. Hit Analyse Protein.</div></div>
        <div style="background:#060b14;border:1px solid #1a2a3a;border-radius:8px;padding:11px">
          <div style="color:#00e5ff;font-size:.73rem;font-weight:600;margin-bottom:4px">2 · Read the Verdict</div>
          <div style="color:#3a5570;font-size:.7rem;line-height:1.6">DISEASE-CRITICAL = pursue. NO DISEASE VARIANTS = deprioritise. The verdict is driven entirely by human genetic data from ClinVar and UniProt.</div></div>
        <div style="background:#060b14;border:1px solid #1a2a3a;border-radius:8px;padding:11px">
          <div style="color:#00e5ff;font-size:.73rem;font-weight:600;margin-bottom:4px">3 · Explore Tabs</div>
          <div style="color:#3a5570;font-size:.7rem;line-height:1.6">Triage → 3D structure with variant spheres. Case Study → tissue/GPCR/disease. Protein Explorer → residue analysis. Chemistry → binding sites. Experiments → full ROI ranking.</div></div>
        <div style="background:#060b14;border:1px solid #1a2a3a;border-radius:8px;padding:11px">
          <div style="color:#00e5ff;font-size:.73rem;font-weight:600;margin-bottom:4px">4 · AI Report</div>
          <div style="color:#3a5570;font-size:.7rem;line-height:1.6">Add your Anthropic API key in the sidebar to get a Claude-synthesised report with next-experiment recommendations and highly cited literature.</div></div>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <div style="background:#060b14;border:1px solid rgba(255,45,85,.25);border-radius:6px;padding:8px 10px;flex:1"><span style="color:#ff2d55;font-size:.68rem;font-weight:600">Try ARRB2</span><br><span style="color:#3a5570;font-size:.65rem">No mandatory deprioritise — see the actual data</span></div>
        <div style="background:#060b14;border:1px solid rgba(0,229,255,.2);border-radius:6px;padding:8px 10px;flex:1"><span style="color:#00e5ff;font-size:.68rem;font-weight:600">Try FLNA or filamin A</span><br><span style="color:#3a5570;font-size:.65rem">Full variant analysis with 3D spheres</span></div>
        <div style="background:#060b14;border:1px solid rgba(255,140,66,.2);border-radius:6px;padding:8px 10px;flex:1"><span style="color:#ff8c42;font-size:.68rem;font-weight:600">Try TP53</span><br><span style="color:#3a5570;font-size:.65rem">Cancer DISEASE-CRITICAL with 1800+ variants</span></div>
      </div>
    </div>""", unsafe_allow_html=True)
    if st.button("Got it — Enter Protellect", type="primary", key="dismiss_tut"):
        st.session_state.show_tutorial = False; st.rerun()


# ═══════════════════════════════════════════════════════════════════
# DOMAIN LANDING
# ═══════════════════════════════════════════════════════════════════
def _landing():
    """Domain landing — pure Streamlit styled cards, no iframe, fully accessible."""
    # Animated header via small component
    components.html("""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'DM Sans',sans-serif}
body{background:#060b14;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;overflow:hidden}
#canvas{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
.hero{position:relative;z-index:1;text-align:center}
.logo{font-size:2rem;font-weight:700;background:linear-gradient(90deg,#00e5ff,#818cf8,#f43f5e);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-size:200%;animation:shimmer 4s linear infinite}
.sub{color:#1a3a5a;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;margin:6px 0 5px}
.tagline{color:#3a5570;font-size:.8rem}
@keyframes shimmer{0%{background-position:0 50%}100%{background-position:200% 50%}}
</style></head><body>
<canvas id="canvas"></canvas>
<div class="hero">
  <div class="logo">🔬 Protellect</div>
  <div class="sub">Genetics-First Protein Intelligence</div>
  <div class="tagline">Select a domain below to enter your workspace</div>
</div>
<script>
const c=document.getElementById('canvas'),ctx=c.getContext('2d');c.width=window.innerWidth;c.height=window.innerHeight;
const pts=Array.from({length:45},()=>({x:Math.random()*c.width,y:Math.random()*c.height,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*1.3+.4,col:`rgba(${Math.random()>.5?'0,229,255':'129,140,248'},0.25)`}));
function draw(){ctx.clearRect(0,0,c.width,c.height);pts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>c.width)p.vx*=-1;if(p.y<0||p.y>c.height)p.vy*=-1;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle=p.col;ctx.fill();});pts.forEach((a,i)=>pts.slice(i+1).forEach(b=>{const d=Math.hypot(a.x-b.x,a.y-b.y);if(d<100){ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=`rgba(0,229,255,${.05*(1-d/100)})`;ctx.lineWidth=.5;ctx.stroke();}}));requestAnimationFrame(draw);}
draw();
</script></body></html>""", height=180, scrolling=False)

    # Pure Streamlit domain cards — 2 rows of buttons, styled beautifully
    st.markdown("""
    <style>
    .domain-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 10px; }
    .domain-grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 24px; max-width: 66%; margin-left: auto; margin-right: auto; }
    </style>
    """, unsafe_allow_html=True)

    # Row 1: Neuroscience, Cancer Biology, Pharmaceuticals
    c1, c2, c3 = st.columns(3)
    with c1:
        col = DOMAIN_META["Neuroscience"]["color"]
        tags = " · ".join(DOMAIN_META["Neuroscience"]["tags"][:4])
        st.markdown(f'''<style>#dn0>div>button{{
          background:{col}0d!important;border:1px solid {col}35!important;color:{col}!important;
          font-weight:600!important;border-radius:10px!important;height:auto!important;
          padding:14px 16px!important;font-size:.82rem!important;text-align:left!important;
          white-space:normal!important;line-height:1.5!important;transition:all .2s!important}}
        #dn0>div>button:hover{{background:{col}1c!important;border-color:{col}70!important;transform:translateY(-2px)!important;box-shadow:0 0 20px {col}22!important}}
        </style>
        <div id="dn0">''', unsafe_allow_html=True)
        if st.button(f"🧠  Neuroscience\n{tags}", key="dl_Neuroscience", use_container_width=True):
            st.session_state.domain = "Neuroscience"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        col = DOMAIN_META["Cancer Biology"]["color"]
        tags = " · ".join(DOMAIN_META["Cancer Biology"]["tags"][:4])
        st.markdown(f'''<style>#dn1>div>button{{
          background:{col}0d!important;border:1px solid {col}35!important;color:{col}!important;
          font-weight:600!important;border-radius:10px!important;height:auto!important;
          padding:14px 16px!important;font-size:.82rem!important;text-align:left!important;
          white-space:normal!important;line-height:1.5!important;transition:all .2s!important}}
        #dn1>div>button:hover{{background:{col}1c!important;border-color:{col}70!important;transform:translateY(-2px)!important;box-shadow:0 0 20px {col}22!important}}
        </style>
        <div id="dn1">''', unsafe_allow_html=True)
        if st.button(f"🎗  Cancer Biology\n{tags}", key="dl_Cancer Biology", use_container_width=True):
            st.session_state.domain = "Cancer Biology"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        col = DOMAIN_META["Pharmaceuticals"]["color"]
        tags = " · ".join(DOMAIN_META["Pharmaceuticals"]["tags"][:4])
        st.markdown(f'''<style>#dn2>div>button{{
          background:{col}0d!important;border:1px solid {col}35!important;color:{col}!important;
          font-weight:600!important;border-radius:10px!important;height:auto!important;
          padding:14px 16px!important;font-size:.82rem!important;text-align:left!important;
          white-space:normal!important;line-height:1.5!important;transition:all .2s!important}}
        #dn2>div>button:hover{{background:{col}1c!important;border-color:{col}70!important;transform:translateY(-2px)!important;box-shadow:0 0 20px {col}22!important}}
        </style>
        <div id="dn2">''', unsafe_allow_html=True)
        if st.button(f"💊  Pharmaceuticals\n{tags}", key="dl_Pharmaceuticals", use_container_width=True):
            st.session_state.domain = "Pharmaceuticals"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Row 2: Microbiome, Molecular Biology — centred
    _, c4, c5, _ = st.columns([0.5, 1, 1, 0.5])
    with c4:
        col = DOMAIN_META["Microbiome"]["color"]
        tags = " · ".join(DOMAIN_META["Microbiome"]["tags"][:4])
        st.markdown(f'''<style>#dn3>div>button{{
          background:{col}0d!important;border:1px solid {col}35!important;color:{col}!important;
          font-weight:600!important;border-radius:10px!important;height:auto!important;
          padding:14px 16px!important;font-size:.82rem!important;text-align:left!important;
          white-space:normal!important;line-height:1.5!important;transition:all .2s!important}}
        #dn3>div>button:hover{{background:{col}1c!important;border-color:{col}70!important;transform:translateY(-2px)!important;box-shadow:0 0 20px {col}22!important}}
        </style>
        <div id="dn3">''', unsafe_allow_html=True)
        if st.button(f"🦠  Microbiome\n{tags}", key="dl_Microbiome", use_container_width=True):
            st.session_state.domain = "Microbiome"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c5:
        col = DOMAIN_META["Molecular Biology"]["color"]
        tags = " · ".join(DOMAIN_META["Molecular Biology"]["tags"][:4])
        st.markdown(f'''<style>#dn4>div>button{{
          background:{col}0d!important;border:1px solid {col}35!important;color:{col}!important;
          font-weight:600!important;border-radius:10px!important;height:auto!important;
          padding:14px 16px!important;font-size:.82rem!important;text-align:left!important;
          white-space:normal!important;line-height:1.5!important;transition:all .2s!important}}
        #dn4>div>button:hover{{background:{col}1c!important;border-color:{col}70!important;transform:translateY(-2px)!important;box-shadow:0 0 20px {col}22!important}}
        </style>
        <div id="dn4">''', unsafe_allow_html=True)
        if st.button(f"⚛️  Molecular Biology\n{tags}", key="dl_Molecular Biology", use_container_width=True):
            st.session_state.domain = "Molecular Biology"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;color:#0d1a2a;font-size:.63rem;font-style:italic;margin-top:8px">The only platform that tells you which proteins to abandon before you spend the money.</div>', unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
user = _user()
with st.sidebar:
    st.markdown(f"""<div style="padding:10px 0 8px;border-bottom:1px solid #1a2a3a;margin-bottom:8px">
      <div style="font-size:1rem;font-weight:700;background:linear-gradient(90deg,#00e5ff,#7c3aed);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent">🔬 Protellect</div>
      <div style="font-size:.65rem;color:#3a5570;margin-top:1px">{user.get('name','')} · {user.get('tier','free').upper()}</div>
    </div>""", unsafe_allow_html=True)
    
    # Quota
    used = _used(); quota = _quota(); tier = user.get("tier","free")
    if user.get("dev"): qlbl,qcol = "Dev — Unlimited","#f97316"
    elif tier=="enterprise": qlbl,qcol = "Enterprise — Unlimited","#f97316"
    else:
        rem = quota-used; qcol = "#00e5ff" if rem>1 else "#ffd60a" if rem==1 else "#ef4444"
        qlbl = f"{rem} searches remaining" if rem>0 else "Quota exhausted"
    st.markdown(f'<div style="background:{qcol}0d;border:1px solid {qcol}25;border-radius:6px;padding:4px 10px;font-size:.7rem;color:{qcol};margin-bottom:8px;text-align:center">{qlbl}</div>', unsafe_allow_html=True)
    
    # Research goal
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">RESEARCH GOAL</div>', unsafe_allow_html=True)
    st.selectbox("rg",["Drug target identification","Disease mechanism","Variant pathogenicity","Therapeutic hypothesis","Protein function","Biomarker discovery","Academic research"],label_visibility="collapsed",key="research_goal")
    
    # Protein search
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">PROTEIN SEARCH</div>', unsafe_allow_html=True)
    domain = st.session_state.domain or "Molecular Biology"
    exs = DOMAIN_EXAMPLES.get(domain, ["TP53","BRCA1"])
    qi = st.text_input("ps", value=st.session_state._qval, placeholder=f"e.g. {' · '.join(exs[:3])}", label_visibility="collapsed", key="_sw")
    st.session_state._qval = qi
    if st.button("⚡  Analyse Protein", type="primary", use_container_width=True, key="ab"):
        st.session_state._trig = True
    
    # Disease in sidebar — show after protein loaded
    cached = st.session_state.protein_data_cache.get(st.session_state._qval.upper().strip(), {})
    if cached:
        pdata_sb = cached.get("pdata",{}); cv_sb = cached.get("cv",[]); gi_sb = cached.get("gi_s",{})
        diseases_sb = pdata_sb.get("diseases",[])
        if diseases_sb:
            st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:10px 0 4px">DISEASE BREAKDOWN</div>', unsafe_allow_html=True)
            for d in diseases_sb[:6]:
                inh = d.get("inheritance","Unknown"); col = "#ff8c42" if inh=="Somatic" else "#818cf8"
                st.markdown(f'<div style="display:flex;align-items:baseline;gap:5px;padding:3px 0;border-bottom:1px solid #0d1a2a"><span style="color:{col};font-size:.6rem;min-width:50px">{inh}</span><span style="color:#b0c8d8;font-size:.68rem">{d.get("name","?")}</span></div>', unsafe_allow_html=True)
        # Variant severity breakdown
        path_vars = [v for v in cv_sb if v.get("ml_class") in ("CRITICAL","HIGH")]
        if path_vars:
            st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 4px">VARIANT SEVERITY</div>', unsafe_allow_html=True)
            for v in path_vars[:5]:
                sev_label, sev_col, badge_cls = _classify_severity(v)
                st.markdown(f'<div style="display:flex;align-items:center;gap:5px;padding:2px 0;border-bottom:1px solid #0d1a2a"><span class="{badge_cls}">{sev_label}</span><span style="color:#7a9aaa;font-size:.65rem;font-family:monospace">{v.get("protein_change","?")[:18]}</span></div>', unsafe_allow_html=True)
    
    # Disease → proteins
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">DISEASE → PROTEINS</div>', unsafe_allow_html=True)
    di = st.text_input("dp", value=st.session_state._dval, placeholder="e.g. Hantavirus · arrhythmia", label_visibility="collapsed", key="_dw")
    st.session_state._dval = di
    if st.button("🔗  Find Disease Proteins", use_container_width=True, key="db"):
        st.session_state._dtrig = True
    
    # Wet-lab CSV
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">WET-LAB DATA (CSV)</div>', unsafe_allow_html=True)
    cf = st.file_uploader("cu", type=["csv","txt","tsv"], label_visibility="collapsed", key="cu", help="Any size. Auto-detects: DMS, RNA-seq, VCF, proteomics, binding assay, GWAS.")
    if cf:
        try:
            sep = "\t" if cf.name.endswith((".txt",".tsv")) else ","
            df_c = pd.read_csv(cf, sep=sep, nrows=100000); st.session_state.csv_data = df_c
            st.markdown(f'<div style="color:#00e5ff;font-size:.68rem;margin-top:2px">✓ {cf.name} · {len(df_c):,} rows · {len(df_c.columns)} cols</div>', unsafe_allow_html=True)
        except Exception as e: st.error(f"Parse error: {e}")
    
    # Wet-lab assay interpretation
    if cached and st.session_state.wet_lab_text:
        wl = st.session_state.wet_lab_text
        pdata_sb2 = cached.get("pdata",{})
        is_gpcr = pdata_sb2.get("is_gpcr",False)
        interp = ("Filamin Ser2152-P readout — correlates with GPCR activation state. Cross-reference the Filamin IP assay." if "phospho" in wl.lower() and is_gpcr
            else "Protein-protein interaction disruption — validate by Co-IP with STRING top partners." if any(x in wl.lower() for x in ["co-ip","pull","interaction"])
            else f"Functional signal detected. Cross-reference with ClinVar pathogenic variants at affected residue.")
        st.markdown(f'<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">ASSAY INTERPRETATION</div><div style="background:#060b14;border:1px solid #1a2a3a;border-radius:5px;padding:6px 8px;font-size:.68rem;color:#5a8aaa;line-height:1.6">{interp}</div>', unsafe_allow_html=True)
    
    # Wet-lab assay text
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">WET-LAB ASSAY</div>', unsafe_allow_html=True)
    wl = st.text_area("wl", value=st.session_state.wet_lab_text, placeholder="Describe result — e.g. Ser2152-P detected at 10nM, abolished in R2149Q variant.", label_visibility="collapsed", height=55, key="wli")
    st.session_state.wet_lab_text = wl
    
    # Sensitivity
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">SENSITIVITY</div>', unsafe_allow_html=True)
    sens = st.slider("se",0.0,1.0,st.session_state.sensitivity,0.05,label_visibility="collapsed",key="sensitivity")
    st.markdown(f'<div class="dim" style="margin-top:-4px;margin-bottom:4px">{sens:.2f} · {"Strict" if sens>0.8 else "Balanced" if sens>0.5 else "Sensitive"}</div>', unsafe_allow_html=True)
    if st.button("▶ Run Triage", use_container_width=True, key="rt"):
        st.session_state.protein_data_cache = {}; st.toast(f"Re-running at {sens:.2f}")
    
    # AI key
    st.markdown('<div style="font-size:.6rem;color:#1a3a5a;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 2px">AI REPORT KEY</div>', unsafe_allow_html=True)
    ak = st.text_input("ak", type="password", placeholder="sk-ant-...", label_visibility="collapsed", key="_aki")
    if ak: st.session_state.anthropic_key = ak
    if st.session_state.anthropic_key: st.markdown('<div style="font-size:.65rem;color:#4ade80;margin-top:1px">● AI enabled</div>', unsafe_allow_html=True)
    
    st.divider()
    if st.button("📖 Tutorial", use_container_width=True, key="tut_btn"):
        st.session_state.show_tutorial = True; st.rerun()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("🔄",use_container_width=True,help="Clear cache"): st.cache_data.clear(); st.toast("Cache cleared")
    with c2:
        if st.button("✕",use_container_width=True,help="Clear search"): st.session_state._qval=""; st.session_state.current_protein=None; st.rerun()
    with c3:
        if st.button("↪",use_container_width=True,help="Logout"): _logout(); st.rerun()


# ═══════════════════════════════════════════════════════════════════
# DOMAIN LANDING
# ═══════════════════════════════════════════════════════════════════
if not st.session_state.domain:
    _tutorial()
    _landing()
    st.stop()

domain = st.session_state.domain
_tutorial()

# Back button + breadcrumb
col_back, col_info = st.columns([1,6])
with col_back:
    if st.button("← Domains", key="back_domains"):
        st.session_state.domain = None; st.session_state.current_protein = None; st.rerun()
with col_info:
    meta = DOMAIN_META.get(domain,{})
    st.markdown(f'<div style="padding:4px 0;color:#3a5570;font-size:.76rem">{meta.get("icon","")} <b style="color:{meta.get("color","#00e5ff")}">{domain}</b> · {st.session_state.research_goal}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# DISEASE TRIGGER
# ═══════════════════════════════════════════════════════════════════
if st.session_state._dtrig and st.session_state._dval:
    st.session_state._dtrig = False
    dq = st.session_state._dval
    _sec(f"Disease → Proteins: {dq}")
    try:
        r = requests.get("https://rest.uniprot.org/uniprotkb/search",
            params={"query":f"cc_disease:{dq} AND organism_id:9606 AND reviewed:true","format":"json","size":10,"fields":"accession,gene_names,protein_name"},
            headers=HDR, timeout=12)
        hits = r.json().get("results",[])
        if hits:
            for hit in hits:
                gs = [g.get("geneName",{}).get("value","") for g in hit.get("genes",[])]
                g = gs[0] if gs else hit.get("primaryAccession","")
                pn = hit.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
                c1,c2 = st.columns([4,1])
                with c1: st.markdown(f'<span style="color:#00e5ff;font-family:monospace;font-weight:600">{g}</span> <span class="dim">{pn[:60]}</span>', unsafe_allow_html=True)
                with c2:
                    if st.button(f"Analyse →", key=f"dis_{g}"): st.session_state._qval=g; st.rerun()
        else: st.info(f"No proteins found for '{dq}'.")
    except: st.warning("Search unavailable.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════
# MICROBIOME DOMAIN
# ═══════════════════════════════════════════════════════════════════
if domain == "Microbiome":
    _sec("🦠 Microbiome Intelligence")
    t1,t2,t3 = st.tabs(["Gene Annotation","Taxonomy","Batch Analysis"])
    with t1:
        _sec("Vague → Specific Annotation")
        c1,c2 = st.columns(2)
        with c1:
            gid = st.text_input("Gene ID / KO", placeholder="K01810, WP_001234", key="mg_gid")
            vague = st.text_input("Current annotation", placeholder="biosynthesis", key="mg_vague")
            org_ctx = st.text_input("Organism context", placeholder="gut microbiome", key="mg_org")
        with c2: st.markdown('<div class="dim" style="margin-top:8px;line-height:1.8">Add Anthropic API key for AI-powered annotation with EC numbers and pathway specificity. Rule-based expansion works without key.</div>', unsafe_allow_html=True)
        if st.button("Generate", type="primary", key="mg_go") and vague:
            EXP = {"biosynthesis":"Anabolic enzyme — specify via KO: amino acid (DAP pathway for lysine), lipid (FASII), or B-vitamin. Run eggNOG-mapper for reaction specificity and EC number.",
                   "chemosynthesis":"Chemolithotrophy — energy from inorganic oxidation (NH₃, S²⁻, Fe²⁺). Check AMO/NXR/Sox gene families.",
                   "protein aggregation":"Regulated polymerisation: curli (CsgA/B → biofilm + TLR2/TLR1 host activation), functional amyloid, or spore coat.",
                   "hypothetical protein":"Run: (1) AlphaFold2+Foldseek, (2) eggNOG-mapper DIAMOND, (3) InterProScan, (4) Phyre2.",
                   "transporter":"TC database: ABC (ATP-driven), MFS (proton gradient), RND (multidrug efflux). Check antibiotic resistance relevance.",
                   "metabolism":"KEGG GHOSTX or eggNOG-mapper for specific reaction. Cross-reference SEED/RAST reconstruction."}
            ak2 = st.session_state.get("anthropic_key",""); result = None
            if ak2:
                try:
                    import anthropic; client = anthropic.Anthropic(api_key=ak2)
                    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role":"user","content":f"Gene:{gid}\nCurrent:{vague}\nOrganism:{org_ctx}\nGive specific: molecular function, EC number, pathway, ecological role, validation tools. No vague terms."}])
                    result = msg.content[0].text
                except: pass
            if not result: al = vague.lower(); result = next((v for k,v in EXP.items() if k in al),f"'{vague}' not in rule base. Run eggNOG-mapper v2.")
            ca,cb = st.columns(2)
            with ca: st.markdown(f'<div class="card" style="border-color:rgba(239,68,68,.2)"><span class="dim" style="color:#ef4444">❌ Before</span><br><i style="color:#fca5a5">{vague}</i></div>', unsafe_allow_html=True)
            with cb: st.markdown(f'<div class="card" style="border-color:rgba(74,222,128,.2)"><span class="dim" style="color:#4ade80">✅ After</span><div style="font-size:.72rem;color:#d0e8ff;margin-top:5px;line-height:1.7">{result}</div></div>', unsafe_allow_html=True)
    with t2:
        _sec("Taxonomy"); taxon = st.text_input("Organism", placeholder="Akkermansia muciniphila", key="mg_tax")
        ROLES = {"Lactobacillus":"Lactic acid producer; pH pathogen competition; gut barrier; SCFA; probiotic candidate","Bifidobacterium":"Probiotic; SCFA; immune modulation; infant microbiome","Bacteroides":"Major fermenter; PULs; keystone coloniser","Akkermansia":"Mucin-layer; gut barrier; depleted in obesity/T2D/IBD","Faecalibacterium":"Butyrate (F. prausnitzii); anti-inflammatory; depleted in IBD","Helicobacter":"CagA/VacA; peptic ulcer; gastric cancer","Fusobacterium":"FadA adhesin; CRC invasion; Wnt/β-catenin"}
        if taxon:
            role = ROLES.get(taxon.split()[0],"Ecological role not curated — search NCBI taxonomy.")
            st.markdown(f'<div class="card"><span style="color:#4ade80;font-family:monospace">{taxon}</span><br><span style="font-size:.72rem;color:#d0e8ff;line-height:1.6">{role}</span></div>', unsafe_allow_html=True)
    with t3:
        _sec("Batch Annotation Quality"); raw = st.text_area("Annotations (one per line)", height=100, key="mg_b")
        VAGUE = {"biosynthesis","chemosynthesis","protein aggregation","hypothetical protein","metabolism","transport","regulation","unknown","uncharacterized","putative"}
        if st.button("Analyse", type="primary", key="mg_ba") and raw:
            lines_b = [l.strip() for l in raw.splitlines() if l.strip()]; vn = sum(1 for l in lines_b if any(v in l.lower() for v in VAGUE))
            c1,c2,c3 = st.columns(3); c1.metric("Total",len(lines_b)); c2.metric("Vague",vn); c3.metric("Informative",len(lines_b)-vn)
            for l in lines_b:
                iv = any(v in l.lower() for v in VAGUE); col2 = "#ef4444" if iv else "#4ade80"
                st.markdown(f'<div style="font-size:.7rem;padding:2px 0;border-bottom:1px solid #0d1a2a"><span style="color:{col2}">{"❌" if iv else "✅"}</span> <span style="color:#d0e8ff">{l}</span></div>', unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════════════════
# SEARCH & LOAD
# ═══════════════════════════════════════════════════════════════════
query = st.session_state._qval.strip()
if not query and not st.session_state._trig:
    meta2 = DOMAIN_META.get(domain,{}); exs2 = DOMAIN_EXAMPLES.get(domain,[])
    color2 = meta2.get("color","#00e5ff"); desc2 = meta2.get("desc","")
    tags2 = " ".join(f'<span class="pill">{t}</span>' for t in meta2.get("tags",[])[:8])
    st.markdown(
        f'<div class="card" style="border-color:{color2}22;padding:22px 26px">'
        f'<div style="font-size:1.8rem;margin-bottom:8px">{meta2.get("icon","🔬")}</div>'
        f'<div style="font-size:1rem;font-weight:600;color:{color2};margin-bottom:5px">{domain}</div>'
        f'<div style="font-size:.76rem;color:#3a5570;margin-bottom:12px;line-height:1.7">{desc2}</div>'
        f'<div style="margin-bottom:14px">{tags2}</div>'
        f'<div style="font-size:.72rem;color:#2a4060;border-top:1px solid #1a2a3a;padding-top:10px">'
        f'Type a gene symbol or protein name in the <b style="color:#d0e8ff">Protein Search</b> sidebar, then click <b style="color:{color2}">⚡ Analyse Protein</b></div></div>',
        unsafe_allow_html=True
    )
    if exs2:
        st.markdown('<div style="color:#1a3a5a;font-size:.6rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin:12px 0 5px">QUICK EXAMPLES</div>', unsafe_allow_html=True)
        n_cols = max(1, min(7, len(exs2)))
        ec = st.columns(n_cols)
        for i,ex in enumerate(exs2[:n_cols]):
            with ec[i]:
                if st.button(ex, key=f"dex_{ex}_{domain}", use_container_width=True): st.session_state._qval=ex; st.rerun()
    st.stop()

st.session_state._trig = False

# Normalise query
query = NAME_MAP.get(query.strip().lower(), query)
st.session_state._qval = query

if any(t in query.lower() for t in NON_HUMAN): st.error(f"'{query}' appears to be non-human. Protellect requires human proteins only."); st.stop()
if not _can(): st.error("Search quota exhausted. Upgrade to continue."); st.stop()

ck = query.upper()
if ck not in st.session_state.protein_data_cache:
    prog = st.progress(0, text=f"Fetching {query} from UniProt…")
    try:
        prog.progress(6,"UniProt search…"); uraw = _uniprot(query)
        prog.progress(16,"Parsing protein data…"); pdata = _parse(uraw)
        if not pdata or not pdata.get("accession"):
            st.error(f"Could not find '{query}'. Try the official gene symbol (FLNA, TP53, ADRB2) or a protein name (filamin A, p53, beta-2 adrenergic receptor)."); st.stop()
        if not pdata.get("is_human",True):
            st.error(f"'{pdata.get('gene',query)}' is not a human protein (organism: {pdata.get('organism','?')}). Protellect analyses human proteins only."); st.stop()
        gene = pdata["gene"] or query.upper(); acc = pdata["accession"]
        prog.progress(26,"AlphaFold structure…"); pdb = _alphafold(acc); plddt = _plddt(pdb)
        prog.progress(37,"ClinVar variants…"); cv = _clinvar(gene)
        # Merge UniProt natural variants if ClinVar returns few
        uni_v = pdata.get("uni_variants",[])
        if len(cv) < 5 and uni_v:
            existing_pos = {v.get("position",0) for v in cv}
            for uv in uni_v:
                if uv.get("position",0) not in existing_pos: cv.append(uv)
            cv = sorted(cv, key=lambda x: x.get("ml_class","LOW")=="CRITICAL", reverse=True)
        prog.progress(50,"gnomAD + STRING…"); gnomad = _gnomad(gene); string_d = _string(gene)
        prog.progress(62,"OpenTargets + DGIdb…"); ot_d = _opentargets(gene); dgidb = _dgidb(gene)
        prog.progress(74,"AlphaMissense + PubMed…"); am_d = _alphamissense(acc); papers = _pubmed(gene)
        prog.progress(86,"GTEx + Trials…"); gtex = _gtex(gene); trials = _trials(gene)
        prog.progress(94,"Computing GI score…"); gi_s = _gi(gene, cv, pdata.get("seq_len",500))
        prog.progress(100,"Complete ✓"); prog.empty()
        
        st.session_state.protein_data_cache[ck] = dict(
            pdata=pdata,pdb=pdb,plddt=plddt,cv=cv,gnomad=gnomad,string_d=string_d,
            ot_d=ot_d,am_d=am_d,papers=papers,gtex=gtex,dgidb=dgidb,trials=trials,gi_s=gi_s)
        _record()
        ws = st.session_state.workspace
        if not any(w.get("gene")==gene for w in ws):
            ws.insert(0,{"gene":gene,"accession":acc,"protein":pdata.get("protein_name","")[:50],"verdict":gi_s["verdict"],"color":gi_s["color"],"domain":domain})
            st.session_state.workspace = ws[:50]
        st.session_state.current_protein = ck
    except Exception as ex:
        import traceback; st.error(f"Loading error: {ex}")
        with st.expander("Traceback"): st.code(traceback.format_exc())
        st.stop()
else:
    st.session_state.current_protein = ck

D = st.session_state.protein_data_cache[ck]
pdata=D["pdata"]; pdb=D["pdb"]; plddt=D["plddt"]; cv=D["cv"]; gnomad=D["gnomad"]
string_d=D["string_d"]; ot_d=D["ot_d"]; am_d=D["am_d"]; papers=D["papers"]
gtex=D["gtex"]; dgidb=D["dgidb"]; trials=D["trials"]; gi_s=D["gi_s"]
gene=pdata["gene"] or query.upper(); acc=pdata["accession"]
is_gpcr=pdata.get("is_gpcr",False); is_kinase=pdata.get("is_kinase",False)
is_pase=pdata.get("is_phosphatase",False)
is_cardiac=gene.upper() in {"ADRB1","ADRB2","AGTR1","CHRM2","MAS1"}
is_filamin=any(k in " ".join(pdata.get("functions",[])+pdata.get("keywords",[])).lower() for k in ["filamin","actin-binding protein 280"])
vcolor=gi_s["color"]; verdict=gi_s["verdict"]


# ═══════════════════════════════════════════════════════════════════
# PROTEIN HEADER
# ═══════════════════════════════════════════════════════════════════
flags = ""
if is_gpcr:    flags += f' <span style="background:rgba(0,229,255,.1);color:#00e5ff;border:1px solid rgba(0,229,255,.3);border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">GPCR</span>'
if is_filamin: flags += f' <span style="background:rgba(249,115,22,.1);color:#f97316;border:1px solid rgba(249,115,22,.3);border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">FILAMIN</span>'
if is_cardiac: flags += f' <span style="background:rgba(239,68,68,.1);color:#ef4444;border:1px solid rgba(239,68,68,.3);border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">CARDIAC</span>'
if is_kinase:  flags += f' <span style="background:rgba(74,222,128,.08);color:#4ade80;border:1px solid rgba(74,222,128,.25);border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">KINASE</span>'
if is_pase:    flags += f' <span style="background:rgba(251,191,36,.08);color:#fbbf24;border:1px solid rgba(251,191,36,.25);border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">PHOSPHATASE</span>'

st.markdown(f"""<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #1a2a3a;margin-bottom:8px">
<div style="flex:1">
  <span style="font-size:1.1rem;font-weight:700;color:#d0e8ff;font-family:monospace">{gene}</span>
  <span style="background:{vcolor}18;color:{vcolor};border:1px solid {vcolor}45;border-radius:5px;padding:2px 9px;font-size:.67rem;font-weight:700;margin-left:6px">{verdict}</span>
  {flags}
  <br><span style="font-size:.69rem;color:#3a5570;font-family:monospace">{acc} · {pdata.get('protein_name','')[:65]} · {pdata.get('organism','')}</span>
</div>
<div style="display:flex;gap:12px;text-align:center;align-items:flex-start;flex-shrink:0">
  <div><div style="font-size:.8rem;font-weight:700;color:#00e5ff;font-family:monospace">{pdata.get('seq_len',0):,}</div><div style="font-size:.58rem;color:#3a5570">AA</div></div>
  <div><div style="font-size:.8rem;font-weight:700;color:#ff2d55;font-family:monospace">{gi_s.get('n_pathogenic',0)}</div><div style="font-size:.58rem;color:#3a5570">P/LP</div></div>
  <div><div style="font-size:.8rem;font-weight:700;color:#00e5ff;font-family:monospace">{f"{gnomad['pLI']:.2f}" if gnomad.get("pLI") else "—"}</div><div style="font-size:.58rem;color:#3a5570">pLI</div></div>
  <div><div style="font-size:.8rem;font-weight:700;color:#4ade80;font-family:monospace">{ot_d.get('known_drugs_count',0)}</div><div style="font-size:.58rem;color:#3a5570">DRUGS</div></div>
  <div><div style="font-size:.8rem;font-weight:700;color:#ffd60a;font-family:monospace">{len(trials)}</div><div style="font-size:.58rem;color:#3a5570">TRIALS</div></div>
</div></div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════
t0,t1,t2,t3,t4,t5,t6,t7 = st.tabs([
    "📊 Summary", "🎯 Triage", "🔬 Case Study", "🧩 Protein Explorer",
    "⚗️ Experiments & Therapy", "⚗ Chemistry", "🤖 AI Report", "📁 Workspace"
])


# ─── TAB 0: SUMMARY ─────────────────────────────────────────────
with t0:
    pl = {True:"PURSUE",False:"DEPRIORITISE",None:"SELECTIVE"}.get(gi_s.get("pursue"),"PROCEED")
    st.markdown(f"""<div style="background:{vcolor}0a;border:1px solid {vcolor}30;border-radius:7px;padding:10px 16px;display:flex;align-items:center;gap:14px;margin-bottom:10px">
<div><span style="font-size:.95rem;font-weight:800;color:{vcolor}">{pl}</span> <span style="background:{vcolor}18;color:{vcolor};border-radius:4px;padding:1px 7px;font-size:.67rem;font-weight:700">{verdict}</span></div>
<div style="color:{vcolor}88;font-size:.72rem;flex:1">{' · '.join(gi_s.get('reasons',[])[:3])}</div></div>""", unsafe_allow_html=True)
    
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Diseases",len(pdata.get("diseases",[])))
    c2.metric("P/LP Variants",gi_s.get("n_pathogenic",0))
    c3.metric("Critical",gi_s.get("n_critical",0))
    c4.metric("pLI",f"{gnomad.get('pLI'):.2f}" if gnomad.get("pLI") else "N/A")
    c5.metric("Known Drugs",ot_d.get("known_drugs_count",0))
    c6.metric("Active Trials",len(trials))
    
    cl,cr = st.columns([1.2,.8], gap="large")
    with cl:
        _sec("Disease Associations")
        for d in pdata.get("diseases",[])[:7]:
            n=d.get("name","?"); desc=d.get("desc","")[:120]; inh=d.get("inheritance","Unknown")
            cc="#ff8c42" if inh=="Somatic" else "#818cf8" if inh=="Germline" else "#3a5570"
            st.markdown(f'<div style="display:flex;gap:6px;padding:5px 0;border-bottom:1px solid #0d1a2a"><span style="color:{cc};font-size:.62rem;font-weight:600;min-width:58px">{inh}</span><div><b style="color:#d0e8ff;font-size:.73rem">{n}</b><br><span class="dim">{desc}</span></div></div>', unsafe_allow_html=True)
        if not pdata.get("diseases"): st.markdown('<div class="dim" style="padding:8px">No disease annotations — null mutant with no phenotype. Consider deprioritising.</div>', unsafe_allow_html=True)
        
        _sec("Highest-Priority Variants")
        path_v = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")][:8]
        for v in path_v:
            sev,svc,sbc = _classify_severity(v); conds = ", ".join(v.get("conditions",[])[:1])
            am_here = next((a for a in (am_d or []) if a.get("position")==v.get("position")),None)
            am_tag = " 🟢" if am_here and am_here["score"]>=sens else ""
            st.markdown(f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid #0d1a2a"><span class="{sbc}">{sev}</span><a href="{v.get("url","")}" target="_blank" style="color:#7a9aaa;font-family:monospace;font-size:.71rem">{v.get("protein_change","?")[:18]}{am_tag}</a><span class="dim">{conds[:35]}</span></div>', unsafe_allow_html=True)
        if not path_v: st.markdown('<div class="dim" style="padding:6px">No pathogenic/likely pathogenic variants in ClinVar or UniProt.</div>', unsafe_allow_html=True)
    
    with cr:
        _sec("gnomAD Constraint")
        for lbl2,val,thresh,dh in [("pLI",gnomad.get("pLI"),0.9,"high"),("o/e LoF",gnomad.get("lof_oe"),0.35,"low"),("o/e Missense",gnomad.get("missense_oe"),0.6,"low")]:
            if val is None: continue
            good=(val>thresh if dh=="high" else val<thresh); col2="#00e5ff" if good else "#3a5570"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #0d1a2a;font-size:.72rem"><span class="dim">{lbl2}</span><span style="color:{col2};font-family:monospace">{val:.3f}{"  ✓" if good else ""}</span></div>', unsafe_allow_html=True)
        if gnomad.get("essential"):
            st.markdown('<div style="color:#4ade80;font-size:.68rem;margin-top:4px">Essential gene (pLI>0.9) — LoF lethal. Handle CRISPR with care.</div>', unsafe_allow_html=True)
        
        if is_gpcr:
            with st.expander("★ Filamin Ser2152-P IP Assay", expanded=True):
                st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.7">GPCR agonist → H8 dislodges → binds FLNA Ig21 → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or arrestin. Only FLNA (not B/C). ~300/800 Class A GPCRs carry H8 FBM.<br><br><a href="https://pubmed.ncbi.nlm.nih.gov/26124276/" target="_blank" class="pill">Nakamura JBC 2015 PMID:26124276</a></div>', unsafe_allow_html=True)
        
        drugs = ot_d.get("known_drugs",[]) or [d["drug"] for d in dgidb[:5]]
        if drugs:
            _sec("Known Drug Interactions")
            st.markdown(" ".join(f'<span class="pill">💊 {d}</span>' for d in drugs[:8]), unsafe_allow_html=True)
        if trials:
            _sec("Active Clinical Trials")
            for t in trials[:3]:
                st.markdown(f'<div class="dim"><a href="{t["url"]}" target="_blank" style="color:#00e5ff">{t["nct_id"]}</a> · Phase {t["phase"]} · {t["title"][:55]}</div>', unsafe_allow_html=True)
    
    # ── Mutation Timeline (variant positions by severity) ──────────
    if cv:
        _sec("Mutation Dynamics — Variant Positions Across Protein")
        path_all = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH","MODERATE","LOW")]
        fig_mut = go.Figure()
        seq_len2 = pdata.get("seq_len", 500)
        # Backbone
        fig_mut.add_trace(go.Scatter(x=[0, seq_len2], y=[0,0], mode="lines",
            line=dict(color="#1a2a3a", width=6), hoverinfo="none", showlegend=False))
        # Domain bands
        for dom_f in pdata.get("domains",[])[:8]:
            try:
                s_pos = int(dom_f.get("start","0")); e_pos = int(dom_f.get("end","0"))
                if s_pos and e_pos:
                    fig_mut.add_shape(type="rect", x0=s_pos, x1=e_pos, y0=-0.3, y1=0.3,
                        fillcolor="rgba(0,229,255,0.08)", line=dict(color="rgba(0,229,255,0.2)",width=1))
                    fig_mut.add_annotation(x=(s_pos+e_pos)/2, y=0.45, text=dom_f.get("name","")[:12],
                        showarrow=False, font=dict(size=8, color="#3a5570"))
            except: pass
        # Variants
        for cls, col, y_pos, size in [("CRITICAL","#ff2d55",1.0,12),("HIGH","#ff8c42",0.6,9),("MODERATE","#ffd60a",-0.5,6),("LOW","#3a5570",-0.9,5)]:
            grp = [v for v in path_all if v.get("ml_class")==cls and v.get("position",0)>0]
            if grp:
                fig_mut.add_trace(go.Scatter(
                    x=[v["position"] for v in grp], y=[y_pos]*len(grp), mode="markers",
                    marker=dict(size=size, color=col, line=dict(color="#060b14",width=1), opacity=0.9),
                    text=[f"{v.get('protein_change','?')}<br>{', '.join(v.get('conditions',[])[:1])[:40]}" for v in grp],
                    hoverinfo="text", name=cls,
                ))
        fig_mut.update_layout(height=200, plot_bgcolor="#060b14", paper_bgcolor="#060b14",
            xaxis=dict(title="Residue Position", gridcolor="#0d1a2a", color="#3a5570", range=[0, seq_len2]),
            yaxis=dict(title="Severity", tickvals=[1.0,0.6,-0.5,-0.9], ticktext=["CRITICAL","HIGH","MODERATE","LOW"],
                color="#3a5570", gridcolor="#0d1a2a", range=[-1.4,1.4]),
            font=dict(color="#d0e8ff",size=10),
            legend=dict(bgcolor="#080f1a",bordercolor="#1a2a3a",font=dict(size=9)),
            margin=dict(t=10,b=35,l=75,r=10))
        st.plotly_chart(fig_mut, use_container_width=True, config={"displayModeBar":False})
        n_path2 = sum(1 for v in cv if v.get("ml_class") in ("CRITICAL","HIGH"))
        n_mod2 = sum(1 for v in cv if v.get("ml_class")=="MODERATE")
        st.markdown(f'<span class="dim">Pathogenic/LP: <b style="color:#ff2d55">{n_path2}</b> · Moderate (VUS): <b style="color:#ffd60a">{n_mod2}</b> · Total: {len(cv)} · Source: ClinVar + UniProt</span>', unsafe_allow_html=True)

    # ── Disease Progression Timeline ──────────────────────────────
    diseases_all2 = pdata.get("diseases",[])
    if diseases_all2:
        _sec("Disease Associations — Progression & Classification")
        ONSET = {"periventricular nodular heterotopia":"Congenital","cancer":"Adult onset","carcinoma":"Adult onset","syndrome":"Variable","congenital":"Congenital","infant":"Infantile","childhood":"Childhood","juvenile":"Juvenile","adult":"Adult onset","late-onset":"Late onset","early-onset":"Early onset","progressive":"Progressive"}
        fig_dis = go.Figure()
        categories = {"Somatic (Cancer)":[], "Germline (Congenital)":[], "Germline (Variable)":[]}
        for d in diseases_all2[:12]:
            n2 = d.get("name","?"); inh = d.get("inheritance","Unknown")
            if inh=="Somatic": categories["Somatic (Cancer)"].append(n2)
            elif "congenital" in n2.lower() or "hereditary" in n2.lower(): categories["Germline (Congenital)"].append(n2)
            else: categories["Germline (Variable)"].append(n2)
        y_pos = 0; colors = {"Somatic (Cancer)":"#ff8c42","Germline (Congenital)":"#818cf8","Germline (Variable)":"#4ade80"}
        for cat, items in categories.items():
            for item in items:
                fig_dis.add_trace(go.Bar(x=[1], y=[item[:40]], orientation="h",
                    marker_color=colors[cat], name=cat, showlegend=y_pos==0,
                    hovertext=cat, hoverinfo="text"))
                y_pos += 1
        fig_dis.update_layout(height=max(180, len(diseases_all2)*30+40), plot_bgcolor="#060b14", paper_bgcolor="#060b14",
            xaxis=dict(visible=False), yaxis=dict(color="#7a9aaa",tickfont=dict(size=10)),
            font=dict(color="#d0e8ff",size=10), barmode="stack",
            legend=dict(bgcolor="#080f1a",bordercolor="#1a2a3a",font=dict(size=9),orientation="h",yanchor="bottom",y=1.02),
            margin=dict(t=30,b=5,l=5,r=5))
        st.plotly_chart(fig_dis, use_container_width=True, config={"displayModeBar":False})

    if papers:
        _sec("Evidence-Tiered Literature — Cited Sources")
        for p in papers[:10]:
            st.markdown(f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #0d1a2a;align-items:baseline"><span style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;border-radius:3px;min-width:52px;text-align:center;font-size:.6rem;padding:1px 5px;white-space:nowrap">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#7a9aaa;font-size:.71rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:18]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)


# ─── TAB 1: TRIAGE ─────────────────────────────────────────────
with t1:
    cl,cr = st.columns([1.1,.9], gap="large")
    with cl:
        _sec("AlphaFold Structure — Pathogenic Variant Sites Shown as Spheres")
        vw = st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="t1_view",label_visibility="collapsed")
        spin_t1 = st.checkbox("Auto-spin",key="t1_spin")
        _viewer3d(pdb, cv=cv, style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw], height=420, spin=spin_t1, show_variants=True)
        if plddt:
            vals=list(plddt.values()); avg=np.mean(vals); hc=sum(1 for v in vals if v>=70)/len(vals)*100
            fig=go.Figure(go.Histogram(x=vals,nbinsx=25,marker_color=["#00c4e0" if v>=90 else "#35c7a3" if v>=70 else "#f5c842" if v>=50 else "#e05c5c" for v in vals]))
            fig.update_layout(height=130,plot_bgcolor="#060b14",paper_bgcolor="#060b14",xaxis=dict(title="pLDDT",gridcolor="#0d1a2a",color="#3a5570"),yaxis=dict(title="n",gridcolor="#0d1a2a",color="#3a5570"),font=dict(color="#d0e8ff",size=10),margin=dict(t=5,b=25,l=30,r=5))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            st.markdown(f'<span class="dim">Avg pLDDT: <b style="color:#00e5ff">{avg:.1f}</b> · Residues >70: <b style="color:#35c7a3">{hc:.0f}%</b></span>', unsafe_allow_html=True)
        st.markdown(f'<div class="dim" style="margin-top:4px">🔴 CRITICAL variants  🟠 HIGH variants  — click any residue for details</div>', unsafe_allow_html=True)
    
    with cr:
        _sec("Is This Protein Associated With Disease?")
        diseases = pdata.get("diseases",[])
        if diseases:
            st.markdown(f'<div style="background:rgba(0,229,255,.06);border:1px solid rgba(0,229,255,.2);border-radius:8px;padding:10px 14px;margin-bottom:10px"><b style="color:#00e5ff">Yes — {len(diseases)} disease associations confirmed in UniProt</b><br><span class="dim">ClinVar P/LP variants: {gi_s.get("n_pathogenic",0)} · Verdict: {verdict}</span></div>', unsafe_allow_html=True)
            for d in diseases[:8]:
                inh=d.get("inheritance","Unknown"); cc="#ff8c42" if inh=="Somatic" else "#818cf8"
                st.markdown(f'<div style="padding:4px 0;border-bottom:1px solid #0d1a2a"><span style="color:{cc};font-size:.62rem">{inh}</span> — <b style="color:#d0e8ff;font-size:.72rem">{d.get("name","?")}</b><br><span class="dim">{d.get("desc","")[:80]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.2);border-radius:8px;padding:10px 14px"><b style="color:#ef4444">No UniProt disease associations</b><br><span class="dim">A null mutant with no phenotype should be deprioritised unless disease ascertainment is incomplete.</span></div>', unsafe_allow_html=True)
        
        _sec("Variant Sphere Triage — Ranked by Severity")
        path_vars = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH","MODERATE")][:20]
        if path_vars:
            for v in path_vars:
                sev,svc,sbc = _classify_severity(v)
                conds = ", ".join(v.get("conditions",[])[:1]) or "Unspecified"
                am_here = next((a for a in (am_d or []) if a.get("position")==v.get("position")),None)
                concordance = "🟢 AM-concordant" if am_here and am_here["score"]>=sens else "🟡 check AM" if am_here else ""
                source = v.get("source","ClinVar")
                st.markdown(f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #0d1a2a"><span class="{sbc}">{sev}</span><div style="flex:1"><a href="{v.get("url","#")}" target="_blank" style="color:#7a9aaa;font-family:monospace;font-size:.71rem">{v.get("protein_change","?")[:18]}</a> <span class="dim">{concordance}</span><br><span class="dim">{conds[:45]} · {source}</span></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="dim" style="padding:8px">No disease-associated variants found in ClinVar or UniProt.</div>', unsafe_allow_html=True)
        
        _sec("Tractability")
        t1c,t2c,t3c = st.columns(3)
        t1c.metric("Small Mol","✓" if ot_d.get("sm_tractable") else "—")
        t2c.metric("Antibody","✓" if ot_d.get("ab_tractable") else "—")
        t3c.metric("Known Drugs",ot_d.get("known_drugs_count",0))


# ─── TAB 2: CASE STUDY ─────────────────────────────────────────
with t2:
    cl,cr = st.columns(2, gap="large")
    with cl:
        _sec("Tissue Associations — GTEx v8")
        if gtex:
            items = sorted(gtex.items(),key=lambda x:x[1],reverse=True)[:22]
            fig_t = go.Figure(go.Bar(x=[i[1] for i in items],y=[i[0] for i in items],orientation="h",
                marker_color=["#00e5ff" if i[1]==max(gtex.values()) else "#1a3a5a" for i in items],
                hovertemplate="<b>%{y}</b><br>%{x:.2f} TPM<extra></extra>"))
            fig_t.update_layout(height=max(300,len(items)*20),plot_bgcolor="#060b14",paper_bgcolor="#060b14",
                xaxis=dict(title="Median TPM",gridcolor="#0d1a2a",color="#3a5570"),
                yaxis=dict(color="#7a9aaa",autorange="reversed",tickfont=dict(size=9)),
                font=dict(color="#d0e8ff",size=10),margin=dict(l=140,r=5,t=5,b=28))
            st.plotly_chart(fig_t,use_container_width=True,config={"displayModeBar":False})
        else:
            st.markdown('<div class="dim" style="padding:8px">GTEx expression data not available.</div>', unsafe_allow_html=True)
        
        _sec("Genomic Framework")
        st.markdown(f"""<div class="card">
<table style="width:100%;font-size:.72rem;border-collapse:collapse">
<tr><td class="dim">Gene</td><td style="color:#d0e8ff;font-family:monospace">{gene}</td><td class="dim">UniProt</td><td style="color:#d0e8ff;font-family:monospace">{acc}</td></tr>
<tr><td class="dim">Length</td><td style="color:#d0e8ff">{pdata.get('seq_len',0):,} aa · {pdata.get('mw_kda',0):.1f} kDa</td><td class="dim">pLI</td><td style="color:{"#00e5ff" if gnomad.get("essential") else "#3a5570"}">{gnomad.get("pLI","N/A")}</td></tr>
<tr><td class="dim">Organism</td><td style="color:#d0e8ff">{pdata.get('organism','')}</td><td class="dim">P/LP</td><td style="color:#ff2d55">{gi_s.get("n_pathogenic",0)}</td></tr>
<tr><td class="dim">LoF o/e</td><td style="color:#d0e8ff">{gnomad.get("lof_oe","N/A")}</td><td class="dim">Miss o/e</td><td style="color:#d0e8ff">{gnomad.get("missense_oe","N/A")}</td></tr>
</table></div>""", unsafe_allow_html=True)
        
        _sec("Disease Classification — Somatic vs Germline (UniProt)")
        germline_d = [d for d in pdata.get("diseases",[]) if d.get("inheritance")!="Somatic"]
        somatic_d  = [d for d in pdata.get("diseases",[]) if d.get("inheritance")=="Somatic"]
        gca,gcb = st.columns(2)
        with gca:
            st.markdown(f'<div style="color:#818cf8;font-size:.67rem;font-weight:600;margin-bottom:4px">GERMLINE ({len(germline_d)})</div>', unsafe_allow_html=True)
            for d in germline_d[:5]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a">{d.get("name","?")[:40]}</div>', unsafe_allow_html=True)
        with gcb:
            st.markdown(f'<div style="color:#ff8c42;font-size:.67rem;font-weight:600;margin-bottom:4px">SOMATIC ({len(somatic_d)})</div>', unsafe_allow_html=True)
            for d in somatic_d[:5]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a">{d.get("name","?")[:40]}</div>', unsafe_allow_html=True)
    
    with cr:
        _sec("Function")
        for fn in pdata.get("functions",[])[:2]:
            st.markdown(f'<div class="card" style="font-size:.73rem;color:#d0e8ff;line-height:1.7">{fn[:350]}</div>', unsafe_allow_html=True)
        
        _sec("Subcellular Localisation")
        locs = pdata.get("subcellular",[])
        if locs: st.markdown(" ".join(f'<span class="pill">{l}</span>' for l in locs[:10]), unsafe_allow_html=True)
        else: st.markdown('<div class="dim">Not annotated.</div>', unsafe_allow_html=True)
        
        _sec("GPCR Classification")
        if is_gpcr:
            kws_txt = " ".join(pdata.get("keywords",[]))
            is_orphan = "orphan" in kws_txt.lower()
            st.markdown(f'<div style="background:rgba(0,229,255,.06);border:1px solid rgba(0,229,255,.2);border-radius:8px;padding:12px;margin-bottom:8px"><b style="color:#00e5ff">DIRECT GPCR</b><br><span class="dim">Seven-transmembrane receptor. {"Orphan receptor — no confirmed endogenous ligand." if is_orphan else "Endogenous ligand identified."} H8 Filamin binding motif present if FBM detected.</span></div>', unsafe_allow_html=True)
        else:
            kws_lower = " ".join(pdata.get("keywords",[])).lower()
            is_piggyback = any(k in kws_lower for k in ["arrestin","rgs","grk","regulator of g"])
            tag = "PIGGYBACK PROTEIN" if is_piggyback else "NON-GPCR TARGET"
            col3 = "#ffd60a" if is_piggyback else "#3a5570"
            desc3 = "Co-associates with GPCRs but may not independently cause Mendelian disease. Verify germline variant evidence before primary drug targeting." if is_piggyback else "No GPCR annotation. Analyse via primary disease variant evidence."
            st.markdown(f'<div style="background:{col3}0a;border:1px solid {col3}30;border-radius:8px;padding:12px"><b style="color:{col3}">{tag}</b><br><span class="dim">{desc3}</span></div>', unsafe_allow_html=True)
        
        _sec("Post-Translational Modifications")
        phospho = pdata.get("phospho_sites",[])
        ptms = pdata.get("ptms",[])
        if phospho:
            st.markdown(f'<div class="dim" style="margin-bottom:4px">Phosphorylation sites: {len(phospho)} annotated</div>', unsafe_allow_html=True)
            for ps in phospho[:6]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a"><span style="color:#fbbf24">Ser/Thr/Tyr {ps["position"]}</span> — {ps["name"]}</div>', unsafe_allow_html=True)
        for pt in ptms[:3]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a">{pt[:100]}</div>', unsafe_allow_html=True)
        if not phospho and not ptms: st.markdown('<div class="dim">No PTM annotations.</div>', unsafe_allow_html=True)
        
        if string_d:
            _sec("STRING Interaction Network")
            n=len(string_d); angles=[2*math.pi*i/n for i in range(n)]; r=3
            nx=[0]+[r*math.cos(a) for a in angles]; ny=[0]+[r*math.sin(a) for a in angles]
            nt=[gene]+[p["partner"] for p in string_d]; ns=[18]+[max(5,int(p["score"]*15)) for p in string_d]
            ex_,ey_=[],[]
            for i in range(n): ex_+=[0,r*math.cos(angles[i]),None]; ey_+=[0,r*math.sin(angles[i]),None]
            fig_n=go.Figure()
            fig_n.add_trace(go.Scatter(x=ex_,y=ey_,mode="lines",line=dict(color="#1a2a3a",width=1.5),hoverinfo="none",showlegend=False))
            fig_n.add_trace(go.Scatter(x=nx,y=ny,mode="markers+text",text=nt,textposition="top center",textfont=dict(color="#7a9aaa",size=9),marker=dict(size=ns,color=["#00e5ff"]+["rgba(0,229,255,"+str(min(1,p['score']))+')' for p in string_d],line=dict(color="#060b14",width=2)),hovertext=["Query"]+[f"{p['partner']} ({p['score']:.2f})" for p in string_d],hoverinfo="text",showlegend=False))
            fig_n.update_layout(height=280,showlegend=False,plot_bgcolor="#060b14",paper_bgcolor="#060b14",xaxis=dict(visible=False),yaxis=dict(visible=False),margin=dict(l=5,r=5,t=5,b=5))
            st.plotly_chart(fig_n,use_container_width=True,config={"displayModeBar":False})
    
    if papers:
        _sec("Evidence-Tiered Literature")
        for p in papers[:8]: st.markdown(f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #0d1a2a;align-items:baseline"><span style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;border-radius:3px;min-width:52px;text-align:center;font-size:.6rem;padding:1px 5px;white-space:nowrap">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#7a9aaa;font-size:.71rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:16]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)


# ─── TAB 3: PROTEIN EXPLORER ────────────────────────────────────
with t3:
    cl,cr = st.columns([2,1], gap="large")
    AA = {"A":("Ala",1.8,0),"R":("Arg",-4.5,1),"N":("Asn",-3.5,0),"D":("Asp",-3.5,-1),"C":("Cys",2.5,0),"Q":("Gln",-3.5,0),"E":("Glu",-3.5,-1),"G":("Gly",-0.4,0),"H":("His",-3.2,0),"I":("Ile",4.5,0),"L":("Leu",3.8,0),"K":("Lys",-3.9,1),"M":("Met",1.9,0),"F":("Phe",2.8,0),"P":("Pro",-1.6,0),"S":("Ser",-0.8,0),"T":("Thr",-0.7,0),"W":("Trp",-0.9,0),"Y":("Tyr",-1.3,0),"V":("Val",4.2,0)}
    with cl:
        _sec("Protein Backbone Explorer — Click Any Residue for Details")
        vw = st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="ex_view",label_visibility="collapsed")
        spin_ex = st.checkbox("Auto-spin",key="ex_spin")
        _viewer3d(pdb,cv=cv,style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw],height=460,spin=spin_ex,show_variants=True)
        
        # Disease → mutation → genomic implication table
        _sec("Disease Caused → Mutation → Genomic Implication")
        diseases_all = pdata.get("diseases",[])
        path_all = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")]
        if diseases_all:
            for d in diseases_all[:8]:
                dn = d.get("name","?"); inh = d.get("inheritance","Unknown")
                # Find matching variants for this disease
                matching = [v for v in path_all if any(dn[:20].lower() in c.lower() for c in v.get("conditions",[])) or any(v.get("protein_change","") for v in path_all)][:2]
                inh_col = "#ff8c42" if inh=="Somatic" else "#818cf8"
                
                with st.expander(f"{dn[:50]}  [{inh}]"):
                    st.markdown(f'<div style="font-size:.72rem;color:#d0e8ff;line-height:1.7;margin-bottom:8px">{d.get("desc","No description available.")[:250]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="display:flex;gap:10px;margin-bottom:8px"><span style="color:{inh_col};font-size:.68rem;font-weight:600">{inh}</span><span class="dim">Inheritance: {inh}</span></div>', unsafe_allow_html=True)
                    
                    # Genomic implication based on disease type and variant type
                    if "cancer" in dn.lower() or "carcinoma" in dn.lower():
                        impl = "Somatic gain/loss-of-function drives clonal expansion. Loss of tumour suppression or oncogenic activation. Target: restore wild-type function or inhibit mutant gain-of-function."
                    elif "syndrom" in dn.lower() or "congenital" in dn.lower():
                        impl = "Germline loss-of-function. Haploinsufficiency or recessive homozygosity. Consider: gene supplementation, read-through therapy for nonsense variants, or antisense oligonucleotides."
                    else:
                        impl = "Germline variant alters protein structure/function. Phenotype depends on inheritance mode, penetrance, and modifier genes. Functional assay required to confirm pathogenesis."
                    st.markdown(f'<div style="background:#080f1a;border:1px solid #1a2a3a;border-radius:5px;padding:8px 10px;font-size:.71rem;color:#b0c8d8;line-height:1.7">{impl}</div>', unsafe_allow_html=True)
                    
                    if path_all:
                        st.markdown('<div style="color:#3a5570;font-size:.62rem;font-weight:600;margin:6px 0 3px">KEY MUTATIONS</div>', unsafe_allow_html=True)
                        for v in path_all[:3]:
                            sev,svc,sbc = _classify_severity(v)
                            st.markdown(f'<div style="display:flex;gap:5px;padding:2px 0"><span class="{sbc}">{sev}</span><span style="color:#7a9aaa;font-family:monospace;font-size:.68rem">{v.get("protein_change","?")}</span></div>', unsafe_allow_html=True)
    
    with cr:
        seq = pdata.get("sequence",""); seq_len = pdata.get("seq_len",0)
        _sec("Residue Inspector")
        if seq and seq_len:
            pos = st.number_input("Residue position",1,max(1,seq_len),min(50,seq_len),key="res_pos_ex")
            if 1<=pos<=seq_len:
                aa = seq[pos-1].upper(); pr = AA.get(aa,("?",0,0)); pv = plddt.get(pos,0)
                pc = "#00c4e0" if pv>=90 else "#35c7a3" if pv>=70 else "#f5c842" if pv>=50 else "#e05c5c"
                pl_lbl = "Very High" if pv>=90 else "Confident" if pv>=70 else "Low" if pv>=50 else "Very Low"
                st.markdown(f"""<div class="card"><span style="color:#00e5ff;font-family:monospace;font-size:1rem;font-weight:700">{aa}{pos}</span> <span class="dim">— {pr[0]}</span>
<table style="width:100%;font-size:.71rem;margin-top:7px">
<tr><td class="dim">Hydrophobicity</td><td style="color:#d0e8ff">{pr[1]}</td></tr>
<tr><td class="dim">Charge</td><td style="color:#d0e8ff">{pr[2]:+}</td></tr>
<tr><td class="dim">pLDDT</td><td style="color:{pc}">{pv:.1f} — {pl_lbl}</td></tr>
</table></div>""", unsafe_allow_html=True)
                
                for v in [v for v in cv if v.get("position")==pos][:2]:
                    col2 = "#ff2d55" if v.get("ml_class")=="CRITICAL" else "#ff8c42"
                    st.markdown(f'<div style="background:{col2}0a;border-left:2px solid {col2};padding:5px 8px;margin:4px 0;border-radius:4px;font-size:.71rem;color:#d0e8ff">{v.get("significance","")} · {", ".join(v.get("conditions",[])[:1])[:40]}</div>', unsafe_allow_html=True)
                
                _sec("If Mutated")
                new_aa = st.selectbox("Substitute to:",sorted([k for k in AA if k!=aa]),key="mut_aa_ex")
                if new_aa:
                    npr = AA.get(new_aa,("?",0,0)); dh = abs(npr[1]-pr[1]); dc = abs(npr[2]-pr[2])
                    score = min(100,int(dh*8+dc*25))
                    ic = "#ff2d55" if score>=70 else "#ff8c42" if score>=40 else "#ffd60a" if score>=15 else "#3a5570"
                    il = "Likely Damaging" if score>=70 else "Possibly Damaging" if score>=40 else "Moderate" if score>=15 else "Likely Benign"
                    implications = []
                    if dc > 0: implications.append(f"Charge reversal/loss — may disrupt salt bridges and protein-protein interfaces")
                    if dh > 3: implications.append(f"Major hydrophobicity shift — likely affects core packing or membrane insertion")
                    if new_aa == "P": implications.append("Proline disrupts α-helix and β-sheet — structural break certain")
                    if aa == "C" or new_aa == "C": implications.append("Cysteine involved — disulfide bond disruption possible")
                    if aa == "G" or new_aa == "G": implications.append("Glycine flexibility lost/gained — affects local backbone dynamics")
                    st.markdown(f"""<div class="card" style="border-color:{ic}30">
<span style="color:{ic};font-family:monospace;font-size:.9rem;font-weight:700">{aa}{pos}{new_aa}</span>
<span class="dim" style="margin-left:8px">{il} · impact score {score}/100</span>
<div style="margin-top:8px;font-size:.71rem;color:#b0c8d8;line-height:1.7">Δhydrophobicity: {dh:.1f} · Δcharge: {dc:+.0f}</div>
{"".join(f'<div class="dim" style="margin-top:3px">▸ {i}</div>' for i in implications)}
</div>""", unsafe_allow_html=True)
                    
                    # AM score at this position
                    am_at_pos = [a for a in (am_d or []) if a.get("position")==pos and a.get("alt")==new_aa]
                    if am_at_pos:
                        ams = am_at_pos[0]["score"]; amc = "#ff2d55" if ams>=0.564 else "#4ade80"
                        st.markdown(f'<div style="color:{amc};font-size:.7rem;margin-top:4px">AlphaMissense: {ams:.3f} ({"pathogenic" if ams>=0.564 else "benign"})</div>', unsafe_allow_html=True)
    
    # AlphaMissense landscape
    if am_d:
        _sec("AlphaMissense Per-Residue Pathogenicity")
        sample = am_d[::max(1,len(am_d)//600)]
        fig_am = go.Figure()
        fig_am.add_trace(go.Scatter(x=[a["position"] for a in sample],y=[a["score"] for a in sample],mode="markers",marker=dict(size=3,color=["#ff2d55" if a["score"]>=0.564 else "#1a3a5a" for a in sample],opacity=0.65),hovertemplate="Pos %{x} — Score %{y:.3f}<extra></extra>"))
        path_cv = [v for v in cv if v.get("position") and v.get("ml_class") in ("CRITICAL","HIGH")]
        if path_cv: fig_am.add_trace(go.Scatter(x=[v["position"] for v in path_cv],y=[0.564]*len(path_cv),mode="markers",marker=dict(size=11,symbol="star",color="#ff8c42"),hovertext=[v.get("protein_change","?") for v in path_cv],hoverinfo="text",name="ClinVar P/LP"))
        fig_am.add_hline(y=0.564,line_dash="dash",line_color="#ffd60a",annotation_text="Pathogenic threshold (0.564)")
        fig_am.update_layout(height=250,plot_bgcolor="#060b14",paper_bgcolor="#060b14",xaxis=dict(title="Residue Position",gridcolor="#0d1a2a",color="#3a5570"),yaxis=dict(title="AM Score",gridcolor="#0d1a2a",color="#3a5570",range=[0,1]),font=dict(color="#d0e8ff",size=10),legend=dict(bgcolor="#080f1a",bordercolor="#1a2a3a"),margin=dict(t=12,b=35,l=50,r=12))
        st.plotly_chart(fig_am,use_container_width=True,config={"displayModeBar":False})


# ─── TAB 4: EXPERIMENTS & THERAPY ──────────────────────────────
with t4:
    _sec("Experiment ROI Triage — Ranked by Expected Value")
    path_v = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")]
    top_vars = [v.get("protein_change","?") for v in path_v[:3]]
    vstr = ", ".join(top_vars) or "P/LP variants"
    partners = [p["partner"] for p in string_d[:3]] if string_d else ["top STRING partner"]
    cell_type = "iPSC-cardiomyocytes" if is_cardiac else "iPSC-neurons" if any(x in " ".join([d.get("name","") for d in pdata.get("diseases",[])]).lower() for x in ["neuro","parkinson","alzheimer"]) else "HEK293T / disease-relevant cell line"
    
    def _exp_card(name, category, cost, time_w, p_success, rationale, mutations_to_focus, mutations_to_neglect, expected_outcome, is_priority=False, is_avoid=False):
        border_col = "#00e5ff" if is_priority else "#ef4444" if is_avoid else "#1a2a3a"
        label = "🚀 DO FIRST" if is_priority else "🛑 PREMATURE" if is_avoid else "Consider"
        label_col = "#00e5ff" if is_priority else "#ef4444" if is_avoid else "#3a5570"
        cost_str = f"${cost:,}" if cost > 0 else "Free"
        with st.expander(f"{'🚀 ' if is_priority else '🛑 ' if is_avoid else ''}{name}  —  {cost_str}  ·  {time_w}w  ·  P(success)={p_success}%", expanded=is_priority and not is_avoid):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Cost",cost_str); c2.metric("Timeline",f"{time_w}w"); c3.metric("P(success)",f"{p_success}%"); c4.metric("Category",category[:12])
            st.markdown(f"""<div style="margin-top:8px;font-size:.73rem;color:#d0e8ff;line-height:1.75">{rationale}</div>
            <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <div style="background:#060b14;border:1px solid rgba(74,222,128,.2);border-radius:5px;padding:8px 10px">
                <div style="color:#4ade80;font-size:.63rem;font-weight:600;margin-bottom:4px">✅ FOCUS ON</div>
                <div style="font-size:.7rem;color:#b0c8d8;line-height:1.6">{mutations_to_focus}</div></div>
              <div style="background:#060b14;border:1px solid rgba(239,68,68,.15);border-radius:5px;padding:8px 10px">
                <div style="color:#ef4444;font-size:.63rem;font-weight:600;margin-bottom:4px">🛑 NEGLECT</div>
                <div style="font-size:.7rem;color:#b0c8d8;line-height:1.6">{mutations_to_neglect}</div></div>
            </div>
            <div style="margin-top:8px;background:rgba(0,229,255,.04);border:1px solid rgba(0,229,255,.15);border-radius:5px;padding:8px 10px">
              <div style="color:#00e5ff;font-size:.63rem;font-weight:600;margin-bottom:3px">EXPECTED OUTCOME</div>
              <div style="font-size:.7rem;color:#b0c8d8;line-height:1.6">{expected_outcome}</div></div>""", unsafe_allow_html=True)
            if is_priority: st.success("Run this experiment first — highest expected value for this protein's variant and interaction profile")
            if is_avoid: st.error("Do not run yet — insufficient genetic evidence at this stage")
    
    # Always show in silico first
    _exp_card("AlphaFold-Multimer — in silico (free, run first)",
        "Structural", 0, 0.5, 80,
        f"Free via ColabFold. Model {gene}:{partners[0] if partners else 'STRING partner'} complex. ipTM>0.8 = high confidence. Map {vstr} onto predicted interface before committing any wet-lab budget.",
        f"All CRITICAL and HIGH variants ({vstr}). Map positions onto predicted interaction interface.",
        "VUS and benign variants — only disease-confirmed positions.",
        "If ipTM>0.8 and variants cluster at interface → wet-lab justified. If ipTM<0.6 or variants off-interface → reconsider experiment design.",
        is_priority=True)
    
    if is_gpcr:
        _exp_card("Filamin Ser2152-P IP Assay (GPCR Activation — Step 3)",
            "GPCR", 600, 1, 90,
            f"GPCR agonist → 10 min at EC80 → lyse cells → anti-FLNA immunoprecipitation → pSer2152 western blot. More receptor-proximal than cAMP, IP3, or arrestin. Validated by Nakamura et al. JBC 2015 (PMID:26124276). Cell type: {cell_type}.",
            f"Variants {vstr} — compare WT vs each pathogenic variant. CRITICAL variants that abolish Ser2152-P are direct therapeutic targets.",
            "VUS variants and non-GPCR-domain variants. ARRB2 readout alone — insufficient as primary disease evidence.",
            "Variants that abolish Filamin-P = loss of receptor coupling = mechanistic drug target. Variants that preserve Filamin-P but alter cAMP = G-protein selectivity change.",
            is_priority=True)
        _exp_card("cAMP HTRF — Gs Coupling WT vs Variants",
            "GPCR", 1200, 2, 85,
            f"Cisbio HTRF kit. EC50 and Emax comparison WT vs {vstr}. Confirms G-protein efficacy downstream of receptor activation.",
            f"Pathogenic variants in transmembrane helices and ligand-binding pocket.",
            "Intracellular C-tail variants unless targeting phosphorylation code. Benign polymorphisms.",
            "Right-shifted EC50 = variant reduces agonist affinity. Reduced Emax = partial agonism or constitutive G-protein uncoupling.",
            is_priority=False)
        if is_cardiac:
            _exp_card("TMAO Rattling Assay (Cardiac GPCRs — Patent-Unoccupied)",
                "Cardiac", 2000, 3, 75,
                f"TMAO 5–50µM + FlAsH-BRET conformational tracking. TMAO increases receptor conformational sampling → disrupts H8-Filamin coupling → arrhythmia mechanism. Patent-unoccupied axis.",
                "Cardiac GPCR variants associated with arrhythmia. R2149Q-equivalent positions.",
                "Non-cardiac domain variants. Variants without arrhythmia phenotype in patients.",
                "TMAO-induced BRET signal change = conformational rattling confirmed. Correlate with Filamin-P reduction to validate mechanistic link.",
                is_priority=False)
    
    if is_kinase:
        _exp_card("ADP-Glo Kinase Activity Assay",
            "Kinase", 1500, 2, 85,
            f"ADP-Glo luminescent kinase assay. Compare Vmax and Km for WT vs {vstr}. Determines if pathogenic variants are gain-of-function (hyperactivating) or loss-of-function (kinase-dead). Different mechanisms require different drugs.",
            f"Variants in kinase domain ({vstr}). Activation loop variants (DFG motif).",
            "Regulatory domain variants unless studying autoinhibition. Signal peptide variants.",
            "GoF → kinase inhibitor strategy. LoF → activator or downstream supplementation strategy.",
            is_priority=True)
    
    if partners:
        _exp_card(f"Co-IP — {gene} with {partners[0]}",
            "PPI", 700, 1, 80,
            f"FLAG-tag {gene} (WT vs {vstr}). Immunoprecipitate with anti-FLAG. Western blot for {partners[0]}. STRING predicts high-confidence interaction (score>0.7). Variant that disrupts {partners[0]} binding identifies the therapeutic interface.",
            f"Variants at predicted interaction interface from AlphaFold-Multimer. {vstr}.",
            "Signal peptide variants. Post-translational modification sites unless studying PTM-dependent interaction.",
            f"Loss of {partners[0]} co-IP = interface disrupted = drug target validated. Preserved co-IP = interaction domain elsewhere.",
            is_priority=False)
    
    n_critical = gi_s.get("n_critical",0)
    am_path = {a["position"] for a in (am_d or []) if a.get("class")=="pathogenic"}
    path_pos = {v["position"] for v in path_v if v.get("position")}
    concordant = len(path_pos & am_path)
    
    if n_critical >= 2 and concordant >= 1:
        _exp_card(f"CRISPR Knock-in — {top_vars[0] if top_vars else 'P/LP variant'}",
            "Disease Model", 15000, 10, 70,
            f"Justified: {n_critical} CRITICAL ClinVar variants + {concordant} AlphaMissense-concordant positions. Knock-in {vstr} into {cell_type}. pLI={gnomad.get('pLI','?')} — {'proceed carefully (essential gene)' if gnomad.get('essential') else 'not highly constrained'}.",
            f"CRITICAL variants with starred ClinVar review. Variants concordant with AlphaMissense pathogenic prediction.",
            "VUS variants. Variants with only one submitter. Benign polymorphisms.",
            "Disease phenotype in knock-in cells = causal validation. Rescuable with WT construct = drug opportunity confirmed.",
            is_priority=False)
    else:
        _exp_card("CRISPR Knock-in — PREMATURE",
            "Disease Model", 15000, 10, 15,
            f"Only {n_critical} CRITICAL variants and {concordant} AlphaMissense-concordant. Genetic evidence insufficient. Run Co-IP, ADP-Glo, and TSA first to build evidence base.",
            "N/A — run earlier experiments first.",
            "All variants at this stage.",
            "Not applicable — return when you have >2 CRITICAL variants with functional assay data.",
            is_priority=False, is_avoid=True)
    
    if ot_d.get("sm_tractable") and gi_s.get("n_pathogenic",0)>=3:
        existing = ot_d.get("known_drugs",[])
        cost = 50000 if existing else 80000
        _exp_card(f"Drug Screen — {existing[0] if existing else 'Fragment-Based'}",
            "Drug Discovery", cost, 8, 60 if existing else 50,
            f"OpenTargets: small-molecule tractable. {'Test '+existing[0]+' analogues (200–500 compound library) — fastest path to hit.' if existing else 'Fragment-based screen via SPR — no existing scaffold.'} Superimpose {vstr} onto AlphaFold structure to confirm target engagement at variant sites.",
            f"Pathogenic variant positions ({vstr}). Hotspot clusters from AlphaMissense.",
            "Off-target positions. Sites without disease variant evidence.",
            f"IC50 < 10µM in primary assay → SAR campaign. Selectivity confirmed vs off-targets → candidate. {'Start with '+existing[0]+' structure as pharmacophore.' if existing else 'FBDD: fragments <300 Da, LE>0.3.'}",
            is_priority=False)
    
    if papers:
        _sec("Experiment Types from Literature")
        tg_map = {}
        for p in papers: tg_map.setdefault(p["tier_label"],[]).append(p)
        for tlbl,tp in sorted(tg_map.items(), key=lambda x:x[1][0]["tier"]):
            with st.expander(f"{tlbl} ({len(tp)} papers)"):
                for p in tp: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a"><a href="{p["url"]}" target="_blank" style="color:#7a9aaa;font-size:.71rem">{p["title"][:100]}</a> · {p["authors"][:18]} · {p["year"]} PMID:{p["pmid"]}</div>', unsafe_allow_html=True)


# ─── TAB 5: CHEMISTRY ───────────────────────────────────────────
with t5:
    _sec("Chemical Structure & Molecular Interactions")
    cl,cr = st.columns([1.3,.7], gap="large")
    with cl:
        _sec("3D Chemical Structure — Binding Sites & Interaction Points")
        # Surface view with binding sites highlighted
        if pdb:
            binding_sites = pdata.get("binding_sites",[])
            phospho_sites = pdata.get("phospho_sites",[])
            
            # Build sphere JS for binding sites and phospho sites
            chem_js = ""
            for bs in binding_sites[:20]:
                if bs.get("start") != "?":
                    try:
                        pos = int(bs["start"])
                        col = "#ffd60a" if bs["type"] in ("ACT_SITE","METAL") else "#4ade80" if bs["type"]=="BINDING" else "#818cf8"
                        chem_js += f"viewer.addStyle({{resi:{pos}}},{{sphere:{{color:'{col}',radius:1.4,opacity:0.8}}}});"
                    except: pass
            for ps in phospho_sites[:15]:
                try:
                    pos = int(ps["position"])
                    chem_js += f"viewer.addStyle({{resi:{pos}}},{{sphere:{{color:'#f97316',radius:1.3,opacity:0.85}}}});"
                except: pass
            
            esc = pdb.replace("\\","\\\\").replace("`","\\`")
            chem_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>
body{{margin:0;background:#060b14;overflow:hidden}}
#v{{width:100%;height:460px}}
#leg{{position:absolute;top:8px;right:8px;background:rgba(8,15,26,.92);color:#d0e8ff;border:1px solid #1a2a3a;border-radius:6px;padding:8px 12px;font:10px monospace}}
.lr{{display:flex;align-items:center;gap:6px;margin:2px 0}}.lc{{width:10px;height:10px;border-radius:2px}}
#info{{position:absolute;bottom:8px;left:8px;background:rgba(8,15,26,.96);color:#d0e8ff;border:1px solid rgba(0,229,255,.2);border-radius:6px;padding:7px 12px;font:11px/1.6 monospace;display:none;z-index:100;max-width:300px}}
</style></head><body>
<div id="v"></div><div id="info"></div>
<div id="leg">
  <b style="color:#00e5ff;font-size:10px">Sites</b>
  <div class="lr"><div class="lc" style="background:#ffd60a"></div>Active/Metal site</div>
  <div class="lr"><div class="lc" style="background:#4ade80"></div>Binding site</div>
  <div class="lr"><div class="lc" style="background:#818cf8"></div>DNA binding</div>
  <div class="lr"><div class="lc" style="background:#f97316"></div>Phosphorylation</div>
  <div class="lr"><div class="lc" style="background:#35c7a3"></div>Other domain</div>
</div>
<script>
try{{
  var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#060b14'}});
  viewer.addModel(`{esc}`,'pdb');
  viewer.setStyle({{}},{{cartoon:{{colorfunc:function(a){{var b=a.b;if(b>=90)return'#00c4e0';if(b>=70)return'#35c7a3';if(b>=50)return'#f5c842';return'#e05c5c';}}}}}});
  viewer.addSurface($3Dmol.SurfaceType.VDW,{{opacity:0.12,color:'#00e5ff'}});
  {chem_js}
  viewer.setClickable({{}},true,function(a,v){{
    var b=document.getElementById('info');b.style.display='block';
    b.innerHTML='<b style="color:#00e5ff">'+a.resn+' '+a.resi+'</b><br>pLDDT: '+(a.b?a.b.toFixed(1):'?')+'<br>Atom: '+a.atom;
    v.addStyle({{resi:a.resi}},{{sphere:{{color:'#ffffff',radius:0.9,opacity:0.5}}}});v.render();
  }});
  viewer.zoomTo();
  viewer.render();
}}catch(e){{document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:14px;font:12px monospace">Error: '+e.message+'</p>';}}
</script></body></html>"""
            components.html(chem_html, height=460, scrolling=False)
        else:
            st.markdown('<div class="dim" style="padding:12px">Structure not available from AlphaFold.</div>', unsafe_allow_html=True)
    
    with cr:
        _sec("Binding Sites & Active Sites")
        binding = pdata.get("binding_sites",[])
        if binding:
            for bs in binding[:12]:
                type_col = {"ACT_SITE":"#ffd60a","BINDING":"#4ade80","METAL":"#ffd60a","DNA_BIND":"#818cf8","CARBOHYD":"#f97316"}.get(bs["type"],"#3a5570")
                st.markdown(f'<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid #0d1a2a"><span style="color:{type_col};font-size:.62rem;min-width:70px;font-weight:600">{bs["type"]}</span><div><span style="color:#d0e8ff;font-size:.71rem">{bs.get("name","?")[:40]}</span><br><span class="dim">Residues {bs.get("start","?")}–{bs.get("end","?")}</span></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="dim">No binding site annotations in UniProt.</div>', unsafe_allow_html=True)
        
        _sec("Phosphorylation Sites")
        phospho = pdata.get("phospho_sites",[])
        if phospho:
            for ps in phospho[:10]:
                st.markdown(f'<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid #0d1a2a"><span style="color:#f97316;font-family:monospace;font-size:.71rem">Pos {ps["position"]}</span><span style="color:#d0e8ff;font-size:.7rem">{ps["name"][:40]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="dim">No phosphorylation annotations in UniProt for this protein.</div>', unsafe_allow_html=True)
        
        _sec("Interaction Partners — Possible Disease Pathways")
        if string_d:
            for p in string_d[:8]:
                exp_score = p.get("experimental",0); col = "#00e5ff" if exp_score>0.5 else "#4ade80" if p["score"]>0.8 else "#3a5570"
                st.markdown(f'<div style="display:flex;gap:6px;padding:4px 0;border-bottom:1px solid #0d1a2a"><span style="color:{col};font-family:monospace;font-size:.71rem;min-width:60px">{p["partner"]}</span><div><span class="dim">Score: {p["score"]:.2f}</span> {" · <span style=&quot;color:#4ade80;font-size:.62rem&quot;>exp</span>" if exp_score>0.3 else ""}</div></div>', unsafe_allow_html=True)
        
        _sec("Phosphatase & Kinase Context")
        if is_kinase:
            st.markdown('<div class="card" style="border-color:rgba(74,222,128,.2)"><span style="color:#4ade80;font-size:.72rem;font-weight:600">KINASE</span><div class="dim" style="margin-top:4px;line-height:1.6">Phosphorylates downstream substrates. Pathogenic variants often alter substrate specificity or autoinhibition. Drug strategy: ATP-competitive inhibitor or allosteric inhibitor targeting regulatory domain.</div></div>', unsafe_allow_html=True)
        if is_pase:
            st.markdown('<div class="card" style="border-color:rgba(251,191,36,.2)"><span style="color:#fbbf24;font-size:.72rem;font-weight:600">PHOSPHATASE</span><div class="dim" style="margin-top:4px;line-height:1.6">Dephosphorylates substrates. LoF variants lead to substrate hyperphosphorylation. Drug strategy: phosphatase activator or substrate-targeted inhibitor.</div></div>', unsafe_allow_html=True)
        if is_filamin:
            st.markdown('<div class="card" style="border-color:rgba(249,115,22,.2)"><span style="color:#f97316;font-size:.72rem;font-weight:600">FILAMIN — Ser2152 IP TARGET</span><div class="dim" style="margin-top:4px;line-height:1.6">Ser2152 is the functionally dominant phosphorylation peak. PKA phosphorylates Ser2152 upon GPCR activation. Only FLNA (not FLNB/C) carries this site. Validated by pathogenic R2149 variants causing periventricular nodular heterotopia.</div></div>', unsafe_allow_html=True)
        
        _sec("PTM Summary")
        ptms = pdata.get("ptms",[])
        if ptms:
            for pt in ptms[:4]: st.markdown(f'<div class="dim" style="padding:3px 0;border-bottom:1px solid #0d1a2a;line-height:1.6">{pt[:100]}</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="dim">No PTM annotations available.</div>', unsafe_allow_html=True)


# ─── TAB 6: AI REPORT ───────────────────────────────────────────
with t6:
    _sec("Evidence-Tiered Literature")
    tg = {}
    for p in papers: tg.setdefault(p["tier_label"],[]).append(p)
    for tlbl,tp in sorted(tg.items(), key=lambda x: x[1][0]["tier"]):
        with st.expander(f"{tlbl} ({len(tp)} papers)", expanded=tlbl in ("RCT","Cohort","Functional")):
            for p in tp: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #0d1a2a"><a href="{p["url"]}" target="_blank" style="color:#7a9aaa;font-size:.71rem">{p["title"][:105]}</a> · {p["authors"][:18]} · {p["journal"]} · {p["year"]} · PMID:{p["pmid"]}</div>', unsafe_allow_html=True)
    
    _sec("AI Synthesis with Live Web Search")
    api_key = st.session_state.get("anthropic_key","")
    if not api_key:
        st.info("Add your Anthropic API key in the sidebar (AI Report Key) to enable Claude synthesis with live literature search.")
        st.markdown("""<div class="card"><div style="color:#d0e8ff;font-size:.76rem;font-weight:600;margin-bottom:6px">The AI Report provides:</div>
<div class="dim" style="line-height:1.8">• VERDICT with full genetic justification and confidence level<br>• MECHANISM — specific molecular mechanism from the variant data<br>• INHERITANCE PATTERN — AD/AR/XL/de novo inference<br>• THERAPEUTIC HYPOTHESES — 3 specific, actionable drug strategies<br>• ACTIVE RESEARCH — current clinical trial and drug pipeline context (live search)<br>• KEY UNKNOWNS — what experiments would resolve critical gaps<br>• Every claim cited: Author / Journal / Year / PMID</div></div>""", unsafe_allow_html=True)
    else:
        if st.button("▶ Generate AI Report", type="primary", key="ai_run"):
            with st.spinner("Searching literature and synthesising analysis…"):
                try:
                    import anthropic; client = anthropic.Anthropic(api_key=api_key)
                    conditions = list({c for v in cv for c in v.get("conditions",[]) if c})[:5]
                    partners_ai = [p["partner"] for p in string_d[:5]]
                    prompt = f"""You are a specialist molecular biologist analysing {gene} for drug target potential.

PROTEIN: {gene} / {pdata.get('protein_name','')} / {acc}
ClinVar P/LP variants: {gi_s.get('n_pathogenic',0)} | gnomAD pLI: {gnomad.get('pLI','Unknown')} | Verdict: {verdict}
Disease conditions: {', '.join(conditions) or 'None confirmed'} | STRING partners: {', '.join(partners_ai) or 'Unknown'}
UniProt diseases: {len(pdata.get('diseases',[]))} | GPCR: {is_gpcr} | Kinase: {is_kinase} | Filamin: {is_filamin}

Generate these sections:
## VERDICT
State PURSUE / DEPRIORITISE with genetic justification and confidence.

## MOLECULAR MECHANISM  
Specific mechanism by which pathogenic variants cause disease.

## INHERITANCE PATTERN
AD / AR / XL / de novo — infer from variant data and pLI.

## THERAPEUTIC HYPOTHESES
3 specific, actionable strategies with rationale. Include variant positions.

## ACTIVE RESEARCH LANDSCAPE
Use web search to find 2024–2025 developments. Drug trials, preprints, breakthroughs.

## KEY UNKNOWNS AND RESOLVING EXPERIMENTS
What 3 experiments would provide the most critical missing information.

RULES:
- Every claim must cite: Author, Journal, Year, PMID or DOI
- Never say "unknown" — specify what experiment resolves it
- If GPCR: mention Filamin Ser2152-P IP assay (PMID:26124276) where relevant
- Be specific about variant positions (p.Arg175His not just "missense variant")"""
                    message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=2500, tools=[{"type":"web_search_20250305","name":"web_search"}], messages=[{"role":"user","content":prompt}])
                    report = "\n".join(b.text for b in message.content if hasattr(b,"text") and b.text)
                    st.session_state[f"ai_{gene}"] = report
                except Exception as e: st.error(f"AI error: {e}")
        if f"ai_{gene}" in st.session_state:
            st.markdown(f'<div class="card" style="line-height:1.85;font-size:.75rem">{st.session_state[f"ai_{gene}"]}</div>', unsafe_allow_html=True)
            if st.button("🔄 Regenerate"): del st.session_state[f"ai_{gene}"]; st.rerun()


# ─── TAB 7: WORKSPACE ───────────────────────────────────────────
with t7:
    _sec(f"Research Workspace — {user.get('name','')}")
    c1,c2,c3 = st.columns(3)
    c1.metric("Searches Used",_used()); c2.metric("Quota",_quota() if _quota()<99999 else "∞"); c3.metric("Proteins Analysed",len(st.session_state.workspace))
    ws_data = st.session_state.workspace
    if not ws_data:
        st.markdown('<div class="dim" style="padding:10px">No proteins analysed yet. Search for a gene in the sidebar to begin.</div>', unsafe_allow_html=True)
    else:
        _sec("Search History")
        for item in ws_data:
            col2 = item.get("color","#3a5570"); ca,cb = st.columns([5,1])
            with ca: st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #0d1a2a"><span style="color:#d0e8ff;font-family:monospace;font-size:.8rem;font-weight:600">{item["gene"]}</span><span style="background:{col2}18;color:{col2};border:1px solid {col2}35;border-radius:4px;padding:1px 7px;font-size:.63rem;font-weight:600">{item["verdict"]}</span><span class="dim">{item.get("domain","")} · {item["accession"]} · {item["protein"][:38]}</span></div>', unsafe_allow_html=True)
            with cb:
                if st.button("↗",key=f"ws_{item['gene']}",help=f"Re-analyse {item['gene']}"): st.session_state._qval=item["gene"]; st.rerun()
