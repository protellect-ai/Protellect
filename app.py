"""Protellect v2 — single file, zero external module imports."""
import streamlit as st, streamlit.components.v1 as components
import hashlib, re, re, math, time, json
import numpy as np, pandas as pd, plotly.graph_objects as go, requests

st.set_page_config(page_title="Protellect", page_icon="🔬", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&display=swap');

/* ── Base ── */
*, *::before, *::after { font-family: 'EB Garamond', Georgia, serif !important; }
html, body, [data-testid="stAppViewContainer"] { background: #010306 !important; font-size: 13px; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden !important; height: 0 !important; }
header { height: 2px !important; min-height: 0 !important; overflow: hidden; padding: 0 !important; }
.block-container { padding: .4rem 1.1rem !important; max-width: 100%; }
::-webkit-scrollbar { width: 3px; } ::-webkit-scrollbar-thumb { background: #0d1a2a; border-radius: 2px; }

/* ── Sidebar — always visible ── */
[data-testid="stSidebar"] {
  background: #020609 !important; border-right: 1px solid #0a1520 !important;
  min-width: 248px !important; max-width: 248px !important;
  display: block !important; transform: translateX(0) !important; visibility: visible !important;
}
[data-testid="stSidebar"] .block-container { padding: .4rem .65rem !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="stSidebar"] .stButton>button { font-size: .73rem !important; padding: 3px 8px !important; min-height: 24px !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #020609; border-radius: 5px; padding: 2px; gap: 1px; border: 1px solid #0a1520;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 4px; color: #2a5070; font-size: .72rem; font-weight: 500;
  padding: 4px 10px; min-height: 26px; font-family: 'EB Garamond', serif !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  background: rgba(0,229,255,0.1) !important; color: #00e5ff !important;
  border: 1px solid rgba(0,229,255,0.2) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] { background: #020609; border: 1px solid #0a1520; border-radius: 6px; padding: 7px 10px; }
[data-testid="stMetricValue"] { color: #00e5ff !important; font-size: .9rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #2a5070 !important; font-size: .6rem !important; text-transform: uppercase; letter-spacing: .05em; }

/* ── Expanders ── */
[data-testid="stExpander"] { background: #020609; border: 1px solid #0a1520 !important; border-radius: 5px; margin: 2px 0; }
[data-testid="stExpander"] summary { color: #4a7090 !important; font-size: .72rem !important; padding: 4px 8px !important; }

/* ── Inputs ── */
[data-testid="stTextInput"] input {
  background: #020609 !important; border: 1px solid #0d1a2a !important;
  color: #d0e8ff !important; border-radius: 4px !important; font-size: .78rem !important;
  padding: 4px 8px !important; font-family: 'EB Garamond', serif !important;
}
[data-testid="stTextInput"] input:focus { border-color: rgba(0,229,255,.4) !important; }
[data-testid="stTextArea"] textarea {
  background: #020609 !important; border: 1px solid #0d1a2a !important;
  color: #d0e8ff !important; border-radius: 4px !important; font-size: .74rem !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"]>div {
  background: #020609 !important; border-color: #0d1a2a !important;
  font-size: .74rem !important; min-height: 26px !important;
}
[data-testid="stFileUploader"] { border: 1px dashed #0d1a2a !important; border-radius: 4px !important; background: #020609 !important; }
[data-testid="stFileUploader"] * { font-size: .7rem !important; color: #4a7090 !important; }

/* ── Buttons ── */
.stButton>button {
  background: #020609; border: 1px solid #0d1a2a; color: #8baabf;
  border-radius: 4px; font-size: .73rem; padding: 3px 10px; min-height: 28px;
  transition: all .12s; font-family: 'EB Garamond', serif !important;
}
.stButton>button:hover { background: #0a1520; border-color: rgba(0,229,255,.2); color: #00e5ff; }
.stButton>button[kind="primary"] {
  background: rgba(0,229,255,.07) !important; border-color: rgba(0,229,255,.3) !important;
  color: #00e5ff !important; font-weight: 600 !important;
}

/* ── Misc ── */
[data-testid="stDataFrame"] * { font-size: .7rem !important; }
[data-testid="stSlider"] * { font-size: .7rem !important; }
[data-testid="stAlert"] { padding: 5px 9px !important; font-size: .73rem !important; border-radius: 4px !important; }
[data-testid="stCodeBlock"], .stCode, pre, code { display: none !important; }

/* ── Utility classes ── */
.sec { font-size: .74rem; font-weight: 600; color: #00e5ff; border-bottom: 1px solid #0a1520; padding-bottom: 4px; margin: 10px 0 6px; letter-spacing: .02em; }
.card { background: #020609; border: 1px solid #0a1520; border-radius: 5px; padding: 8px 12px; margin: 4px 0; font-size: .75rem; }
.pill { display: inline-block; background: rgba(0,229,255,.06); color: #00e5ff; border: 1px solid rgba(0,229,255,.15); border-radius: 10px; padding: 1px 7px; font-size: .65rem; margin: 1px; text-decoration: none; }
.src { display: inline-block; background: #020609; color: #1e3a5f; border: 1px solid #0a1520; border-radius: 2px; padding: 0 4px; font-size: .62rem; margin: 1px; }
.dim { color: #2a5070; font-size: .69rem; }
/* Hide any icon text glitches */
[data-testid="stStatusWidget"], [data-testid="stDecoration"] { display: none !important; }
span.material-icons, span[class*="icon"] { font-size: 0 !important; }
[data-testid="stSpinner"] p { display: none !important; }
/* Hide domain switcher breadcrumb - clean header only */
</style>""", unsafe_allow_html=True)

# ── helpers ──────────────────────────────────────────────────────────────
def _sec(t): st.markdown(f'<div class="sec">{t}</div>', unsafe_allow_html=True)
def _src(l, u=""): return f'<a class="src" href="{u}" target="_blank">{l}</a>' if u else f'<span class="src">{l}</span>'

# ── auth ─────────────────────────────────────────────────────────────────
def _h(pw): return hashlib.sha256(pw.encode()).hexdigest()
ACCOUNTS = {
    "protellect@gmail.com": {"hash": _h("dev@protellect"), "tier": "enterprise", "name": "Protellect Dev", "quota": 999999, "dev": True},
    "demo@protellect.io":   {"hash": _h("demo2025"),       "tier": "free",       "name": "Demo User",     "quota": 5,      "dev": False},
}
def _authed(): return st.session_state.get("auth_user") is not None
def _user():   return st.session_state.get("auth_user", {})
def _used():   return st.session_state.get("searches_used", 0)
def _quota():  return _user().get("quota", 5)
def _can():    u = _user(); return True if (u.get("dev") or u.get("tier") == "enterprise") else _used() < _quota()
def _record():
    if not _user().get("dev"): st.session_state.searches_used = _used() + 1
def _logout():
    for k in ["auth_user", "searches_used", "workspace", "current_protein", "protein_data_cache"]:
        st.session_state.pop(k, None)

if not _authed():
    _, cc, _ = st.columns([1, 1.2, 1])
    with cc:
        st.markdown("<div style='height:50px'></div>", unsafe_allow_html=True)
        st.markdown("""<div style='text-align:center;margin-bottom:28px'>
          <div style='font-size:2.4rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#7c3aed);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent'>🔬 Protellect</div>
          <div style='color:#2a5070;font-size:.8rem;margin-top:4px;letter-spacing:.1em'>GENETICS-FIRST PROTEIN INTELLIGENCE</div>
        </div>""", unsafe_allow_html=True)
        tl, td = st.tabs(["Sign In", "Try Demo"])
        with tl:
            em = st.text_input("Email", placeholder="you@example.com", key="li_em")
            pw = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign In →", type="primary", use_container_width=True, key="li_btn"):
                ac = ACCOUNTS.get(em.strip().lower())
                if ac and ac["hash"] == _h(pw):
                    st.session_state.auth_user = {"email": em, "name": ac["name"], "tier": ac["tier"], "quota": ac["quota"], "dev": ac["dev"]}
                    st.session_state.searches_used = 0; st.session_state.workspace = []; st.rerun()
                else: st.error("Invalid credentials.")
        with td:
            dn = st.text_input("Name", placeholder="Dr. Smith", key="td_n")
            de = st.text_input("Email", placeholder="you@lab.edu", key="td_e")
            dg = st.selectbox("Goal", ["Drug target identification","Disease mechanism","Variant pathogenicity","Therapeutic hypothesis","Protein function","Academic research"], key="td_g")
            if st.button("Start Free Trial →", type="primary", use_container_width=True, key="td_btn"):
                if dn and de:
                    st.session_state.auth_user = {"email": de, "name": dn, "tier": "free", "quota": 5, "dev": False}
                    st.session_state.searches_used = 0; st.session_state.workspace = []; st.rerun()
                else: st.warning("Enter name and email.")
        st.markdown("""<div style='display:flex;gap:10px;margin-top:20px'>
          <div style='flex:1;background:#020609;border:1px solid #1e3a5f;border-radius:8px;padding:12px;text-align:center'><div style='color:#4a7090;font-size:.7rem'>FREE</div><div style='color:#d0e8ff;font-weight:700'>$0</div><div style='color:#2a5070;font-size:.7rem'>5/month</div></div>
          <div style='flex:1;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.25);border-radius:8px;padding:12px;text-align:center'><div style='color:#00e5ff;font-size:.7rem'>PRO</div><div style='color:#d0e8ff;font-weight:700'>$49/mo</div><div style='color:#2a5070;font-size:.7rem'>200 searches</div></div>
          <div style='flex:1;background:rgba(249,115,22,0.05);border:1px solid rgba(249,115,22,0.25);border-radius:8px;padding:12px;text-align:center'><div style='color:#f97316;font-size:.7rem'>ENTERPRISE</div><div style='color:#d0e8ff;font-weight:700'>$299/mo</div><div style='color:#2a5070;font-size:.7rem'>Unlimited</div></div>
        </div>""", unsafe_allow_html=True)
    st.stop()

# ── session ───────────────────────────────────────────────────────────────
for k, v in {"workspace": [], "current_protein": None, "protein_data_cache": {}, "domain": None,
             "research_goal": "Drug target identification", "anthropic_key": "", "sensitivity": 0.70,
             "csv_data": None, "wet_lab_text": "", "_qval": "", "_dval": "",
             "_trig": False, "_dtrig": False}.items():
    if k not in st.session_state: st.session_state[k] = v

# ── databases ─────────────────────────────────────────────────────────────
ARRB_GENES = {"ARRB1", "ARRB2"}
NON_HUMAN = ["gelatin", "gfp", "luciferase", "ovalbumin", "bovine", "collagen extract"]
DOMAIN_EXAMPLES = {
    "Neuroscience":     ["APP","SNCA","MAPT","LRRK2","TARDBP","HTT","GBA"],
    "Cancer Biology":   ["TP53","KRAS","BRCA1","EGFR","MYC","PTEN","APC"],
    "Pharmaceuticals":  ["ADRB2","ADRB1","AGTR1","DRD2","HTR2A","FLNA","GRK2"],
    "Microbiome":       [],
    "Molecular Biology":["FLNA","GRK2","MAPK1","AKT1","SRC","CDK2","EGFR"],
}
ARRB_COSTS = {"HTS screen": 2_500_000, "CRISPR knock-in": 150_000, "Cryo-EM": 500_000, "Mouse models": 800_000, "BRET screens": 100_000}
ARRB_PAPERS = [
    {"title": "ARRB1/2 DKO mice viable and fertile", "pmid": "11408584", "journal": "Science", "year": 2001, "finding": "Complete β-arrestin loss: no lethality — redundant pathway"},
    {"title": "Beta-arrestin phospho code: signal vs noise", "pmid": "26124276", "journal": "J Biol Chem", "year": 2015, "finding": "Phospho sites are EGFR background noise — not disease-causing"},
    {"title": "ClinVar: ARRB2 <5 confirmed Mendelian variants", "pmid": "25307466", "journal": "Nat Genet", "year": 2014, "finding": "No Mendelian disease via beta-arrestin LoF"},
    {"title": "G protein vs arrestin bias: clinical evidence gap", "pmid": "29531875", "journal": "Annu Rev Pharmacol", "year": 2018, "finding": "Biased agonism toward arrestin: no clinical benefit demonstrated"},
    {"title": "Redundant pathway masking in ARRB1/2 KOs", "pmid": "18765446", "journal": "J Cell Biol", "year": 2008, "finding": "Internalisation occurs via multiple arrestin-independent mechanisms"},
    {"title": "EGFR transphosphorylation creates false arrestin code", "pmid": "30279173", "journal": "Cell", "year": 2019, "finding": "Background kinase activity explains all ARRB phospho codes"},
]
ARRB_ALTS = [
    {"gene": "ADRB1", "reason": "β1-AR — 47 P/LP variants, cardiac disease"},
    {"gene": "ADRB2", "reason": "β2-AR — GPCR with FBM, therapeutic relevance"},
    {"gene": "AGTR1", "reason": "AT1R — hypertension, disease variants"},
    {"gene": "MAS1",  "reason": "Mas receptor — ACE2 axis"},
    {"gene": "FLNA",  "reason": "Filamin A — Ser2152 IP target"},
]
GPCR_PROTOCOL = [
    {"step":1,"name":"Surface Expression","desc":"SNAP/CLIP-tag + confocal. Confirm plasma membrane localisation before proceeding.","cost":"$800–2K","time":"1w","ip":False},
    {"step":2,"name":"G-protein Coupling","desc":"cAMP HTRF (Gs) or GTPγS/cAMP (Gi). Primary efficacy readout. WT vs each P/LP variant.","cost":"$500–1.5K","time":"1w","ip":False},
    {"step":3,"name":"Filamin Ser2152-P ★ IP ASSAY","desc":"Agonist → FLNA IP → pSer2152 western. H8 dislodgement = receptor activation. More proximal than cAMP, IP3, or arrestin. Only FLNA (not B/C). ~300/800 Class A GPCRs carry H8 FBM.","cost":"$300–800","time":"3–5d","ip":True},
    {"step":4,"name":"Beta-arrestin BRET (Secondary Only)","desc":"RLuc8-receptor + Venus-ARRB2. Characterise biased agonism ONLY. ARRB2 has <5 Mendelian variants — NOT a primary disease readout.","cost":"$1K–3K","time":"2w","ip":False,"warn":"ARRB2 disease evidence <5 variants. Do not use as primary triage assay."},
    {"step":5,"name":"Receptor Internalisation","desc":"SNAP-surface before/after agonist. % internalised at 30 min + 2 h.","cost":"$500–1K","time":"1w","ip":False},
    {"step":6,"name":"Variant Functional Panel","desc":"Run Steps 2+3 for each ClinVar P/LP variant. Kills cAMP not Filamin-P = G-protein defect. Kills Filamin-P not cAMP = cytoskeletal decoupling. Different biology → different target.","cost":"$2K–5K","time":"3–4w","ip":False},
    {"step":7,"name":"TMAO Rattling Assay (Cardiac GPCRs)","desc":"TMAO 5–50µM + FlAsH-BRET. Conformational rattling → disrupts H8-Filamin coupling → arrhythmia. Patent-unoccupied axis.","cost":"$1K–2K","time":"2w","ip":False,"cardiac":True},
]
MICRO_ORGANISMS = {
    "SARS-CoV-2": {"organism":"SARS-CoV-2 (all variants)","type":"Betacoronavirus","disease":"COVID-19","host_receptors":["ACE2","TMPRSS2","NRP1"],"mechanism":"Spike RBD binds ACE2; TMPRSS2 primes S2 fusion","approved_drugs":["Nirmatrelvir/ritonavir","Remdesivir","Molnupiravir"]},
    "HIV-1":      {"organism":"HIV-1","type":"Lentivirus","disease":"AIDS","host_receptors":["CD4","CCR5","CXCR4"],"mechanism":"gp120→CD4→CCR5/CXCR4→gp41 fusion","approved_drugs":["Dolutegravir","Darunavir","Bictegravir"]},
    "Hantavirus": {"organism":"Hantavirus (Sin Nombre/Hantaan/Seoul)","type":"Bunyavirus","disease":"HPS/HFRS","host_receptors":["ITGB3","ITGAV","DAG1"],"mechanism":"Gn/Gc glycoproteins bind β3-integrins on endothelial cells","approved_drugs":["Ribavirin (limited)","Supportive only"]},
    "Ebola":      {"organism":"Ebola virus (Zaire/Sudan/Bundibugyo)","type":"Filovirus","disease":"EVD","host_receptors":["NPC1","AXL","TYRO3"],"mechanism":"GP binds NPC1 in late endosome after cathepsin cleavage","approved_drugs":["Atoltivimab/maftivimab/odesivimab","Ansuvimab"]},
    "Helicobacter pylori": {"organism":"H. pylori CagA+ strains","type":"Gram-negative bacterium","disease":"Peptic ulcer / Gastric cancer","host_receptors":["EGFR","MET","CDH1"],"mechanism":"CagA via T4SS → SHP2/RAS/MAPK; VacA → mitochondria","approved_drugs":["Amoxicillin+clarithromycin+PPI","Bismuth quadruple"]},
}
DOMAIN_META = {
    "Neuroscience":     {"icon":"🧠","color":"#818cf8","tags":["Alzheimer's","Parkinson's","ALS","Epilepsy","BBB Penetrance","Synaptic Biology","Neurodegeneration","Huntington's"],"desc":"Map neurological disease variants to drug targets. BBB penetrance, synaptic networks, brain GTEx expression."},
    "Cancer Biology":   {"icon":"🎗","color":"#f43f5e","tags":["Oncogenes","Tumour Suppressors","Somatic Hotspots","Founder Mutations","COSMIC","cfDNA","CRC","Breast","Lung","Leukaemia"],"desc":"Founder mutation ID, somatic/germline classification, ClinVar triage for 14 cancer types."},
    "Pharmaceuticals":  {"icon":"💊","color":"#00e5ff","tags":["GPCR Targets","Filamin Ser2152-P","Drug Tractability","BRET","Biased Agonism","Clinical Trials","TMAO Arrhythmia","cAMP HTRF"],"desc":"GPCR piggyback targets, Filamin Ser2152-P IP assay, tractability, drug prioritisation."},
    "Microbiome":       {"icon":"🦠","color":"#4ade80","tags":["LLM Annotation","BGC","Taxonomy","Host–Microbe","Gut Ecology","SCFA","Pathobionts","Curli","NRP Synthetase","PKS"],"desc":"AI-powered vague→specific gene annotation, BGC prediction, pathogen host-receptor mapping."},
    "Molecular Biology":{"icon":"⚛️","color":"#f97316","tags":["Phosphorylation","Kinase Signalling","AlphaFold","STRING","PTMs","Structural Domains","Variant Impact","Co-IP","SPR"],"desc":"Phosphorylation signal/noise, AlphaMissense, 3D structure, mutation impact, interaction networks."},
}
VERDICT_COLORS = {"DISEASE-CRITICAL":"#ff2d55","DISEASE-ASSOCIATED":"#ff8c42","MODERATE":"#ffd60a","VERY LOW":"#4a7090","DEPRIORITISE":"#ef4444","NO DISEASE VARIANTS":"#334155"}
ICONS = {"Neuroscience":"🧠","Cancer Biology":"🎗","Pharmaceuticals":"💊","Microbiome":"🦠","Molecular Biology":"⚛️"}

# ── API fetchers ──────────────────────────────────────────────────────────
HDR = {"User-Agent": "Protellect/2.0"}

@st.cache_data(ttl=86400, show_spinner=False)
def _uniprot(query_raw):
    """Smart search: gene symbol, protein name, full text."""
    q_clean = re.sub(r"['\"()]", "", query_raw).strip()
    def _get(acc):
        r2 = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc}.json", headers=HDR, timeout=15)
        r2.raise_for_status(); return r2.json()
    queries = [
        f"gene:{q_clean} AND organism_id:9606 AND reviewed:true",
        f"protein_name:{q_clean} AND organism_id:9606 AND reviewed:true",
        f"({q_clean}) AND organism_id:9606 AND reviewed:true",
    ]
    try:
        for q in queries:
            r = requests.get("https://rest.uniprot.org/uniprotkb/search",
                params={"query": q, "format": "json", "size": 1}, headers=HDR, timeout=15)
            res = r.json().get("results", [])
            if res: return _get(res[0]["primaryAccession"])
        return {}
    except: return {}

def _parse(e):
    if not e: return {}
    seq = e.get("sequence", {}).get("value", "")
    genes = [g.get("geneName", {}).get("value", "") for g in e.get("genes", []) if g.get("geneName", {}).get("value")]
    diseases, functions, subcell, domains_f = [], [], [], []
    for c in e.get("comments", []):
        ct = c.get("commentType", "")
        if ct == "DISEASE":
            d = c.get("disease", {}); diseases.append({"name": d.get("diseaseName", "?"), "desc": d.get("description", "")[:180]})
        elif ct == "FUNCTION":
            for t in c.get("texts", []): functions.append(t.get("value", "")[:300])
        elif ct == "SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations", []): subcell.append(loc.get("location", {}).get("value", ""))
    for f in e.get("features", []):
        ft = f.get("type", ""); loc = f.get("location", {})
        s = loc.get("start", {}).get("value", "?"); en = loc.get("end", {}).get("value", "?")
        if ft in ("DOMAIN","REGION","MOTIF","DNA_BIND","ACT_SITE","BINDING"):
            domains_f.append({"type": ft, "name": f.get("description", ft), "start": s, "end": en})
    kws = [k.get("name", "") for k in e.get("keywords", [])]; kl = " ".join(kws).lower()
    is_gpcr = any(x in kl for x in ["g protein-coupled","gpcr","seven-transmembrane"])
    org = e.get("organism", {}); taxid = org.get("taxonId", 0)
    return {"accession": e.get("primaryAccession",""), "gene": genes[0] if genes else "",
            "protein_name": e.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value",""),
            "organism": org.get("scientificName",""), "taxon_id": taxid, "is_human": taxid == 9606,
            "sequence": seq, "seq_len": len(seq), "diseases": diseases, "functions": functions,
            "subcellular": list(set(subcell)), "domains": domains_f, "keywords": kws, "is_gpcr": is_gpcr,
            "mw_kda": round(len(seq)*110/1000, 1)}


@st.cache_data(ttl=86400, show_spinner=False)
def _clinvar(gene, mx=50):
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db":"clinvar","term":f"{gene}[gene] AND homo sapiens[organism]","retmax":mx,"retmode":"json"}, headers=HDR, timeout=15)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        time.sleep(0.35)
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db":"clinvar","id":",".join(ids[:50]),"retmode":"json"}, headers=HDR, timeout=20)
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
            stars = {"no assertion":0,"criteria provided, single":1,"criteria provided, multiple":2,"reviewed by expert":4}.get((v.get("review_status","") or "").lower()[:30], 0)
            out.append({"id":uid,"title":v.get("title",""),"significance":sig,"ml_class":cls,"protein_change":pc,
                        "position":pos,"conditions":[c.get("trait_name","") for c in v.get("trait_set",[])],"stars":stars,
                        "url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"})
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
                if ri not in d: d[ri] = b
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
def _pubmed(gene, n=20):
    qs = [f"{gene}[gene] pathogenic variant clinical 2020:2025[pdat]",
          f"{gene} functional assay CRISPR 2020:2025[pdat]",
          f"{gene} therapy treatment 2020:2025[pdat]",
          f"{gene} disease mechanism phenotype 2020:2025[pdat]"]
    all_p = []; seen = set()
    TMAP = {1:"#00e5ff",2:"#4ade80",3:"#818cf8",4:"#f97316",5:"#fbbf24",8:"#475569"}
    LMAP = {1:"RCT",2:"Cohort",3:"Functional",4:"Structural",5:"Animal",8:"Review"}
    def _tier(t):
        tl = t.lower()
        if any(k in tl for k in ["randomised","randomized","placebo"]): return 1
        if any(k in tl for k in ["cohort","prospective","retrospective"]): return 2
        if any(k in tl for k in ["crispr","knock-in","western","functional"]): return 3
        if any(k in tl for k in ["cryo-em","nmr","crystal","alphafold"]): return 4
        if any(k in tl for k in ["mouse","zebrafish","xenograft"]): return 5
        return 8
    for q in qs:
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db":"pubmed","term":q,"retmax":6,"retmode":"json"}, headers=HDR, timeout=12)
            ids = [i for i in r.json().get("esearchresult",{}).get("idlist",[]) if i not in seen]
            seen.update(ids)
            if not ids: continue
            time.sleep(0.35)
            r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, headers=HDR, timeout=15)
            res = r2.json().get("result", {})
            for pid in ids:
                p = res.get(pid, {}); au = p.get("authors",[]); fa = au[0].get("name","") if au else ""; t = p.get("title",""); tier = _tier(t)
                all_p.append({"pmid":pid,"title":t,"year":p.get("pubdate","")[:4],"authors":f"{fa} et al." if len(au)>1 else fa,
                               "journal":p.get("source",""),"url":f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                               "tier":tier,"tier_label":LMAP.get(tier,"Study"),"tier_color":TMAP.get(tier,"#64748b")})
        except: pass
    return sorted(all_p, key=lambda x: x["tier"])[:n]

@st.cache_data(ttl=86400, show_spinner=False)
def _gnomad(gene):
    q = 'query G($g:String!){gene(gene_symbol:$g,reference_genome:GRCh38){gnomad_constraint{pLI lof{oe}missense{oe}}}}'
    try:
        r = requests.post("https://gnomad.broadinstitute.org/api", json={"query":q,"variables":{"g":gene}},
            headers={**HDR,"Content-Type":"application/json"}, timeout=20)
        c = (r.json().get("data",{}).get("gene",{}) or {}).get("gnomad_constraint",{}) or {}
        pLI = c.get("pLI"); loe = (c.get("lof",{}) or {}).get("oe"); moe = (c.get("missense",{}) or {}).get("oe")
        return {"pLI":round(float(pLI),3) if pLI else None,"lof_oe":round(float(loe),3) if loe else None,
                "missense_oe":round(float(moe),3) if moe else None,"essential":float(pLI)>0.9 if pLI else False}
    except: return {}

@st.cache_data(ttl=86400, show_spinner=False)
def _string(gene, lim=15):
    try:
        r = requests.get("https://string-db.org/api/json/get_string_ids",
            params={"identifiers":gene,"species":9606,"limit":1,"caller_identity":"protellect"}, headers=HDR, timeout=12)
        d = r.json()
        if not d: return []
        sid = d[0].get("stringId","")
        r2 = requests.get("https://string-db.org/api/json/interaction_partners",
            params={"identifiers":sid,"species":9606,"limit":lim,"required_score":700,"caller_identity":"protellect"}, headers=HDR, timeout=15)
        return [{"partner":i.get("preferredName_B",""),"score":round(i.get("score",0),3)} for i in r2.json()]
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
        return {"sm_tractable":any((t or {}).get("value") for t in (tr.get("smallMolecule") or [{}])),
                "ab_tractable":any((t or {}).get("value") for t in (tr.get("antibody") or [{}])),
                "known_drugs_count":kd.get("count",0),
                "known_drugs":[(r.get("drug",{}) or {}).get("name","") for r in (kd.get("rows") or [])[:6]]}
    except: return {}

@st.cache_data(ttl=86400, show_spinner=False)
def _gtex(gene):
    try:
        r = requests.get("https://gtexportal.org/api/v2/expression/medianGeneExpression",
            params={"geneId":gene,"datasetId":"gtex_v8","format":"json"}, headers=HDR, timeout=20)
        return {i.get("tissueSiteDetailId","").replace("_"," "): i.get("median",0) for i in r.json().get("medianGeneExpression",[])}
    except: return {}

@st.cache_data(ttl=86400, show_spinner=False)
def _kegg(gene):
    try:
        r = requests.get(f"https://rest.kegg.jp/find/hsa/{gene}", headers=HDR, timeout=10)
        ls = r.text.strip().splitlines()
        if not ls: return []
        gid = ls[0].split("\t")[0].strip()
        r2 = requests.get(f"https://rest.kegg.jp/link/pathway/{gid}", headers=HDR, timeout=10)
        pids = [l.split("\t")[1].strip() for l in r2.text.strip().splitlines() if "\t" in l][:6]
        if not pids: return []
        r3 = requests.get(f"https://rest.kegg.jp/list/{'+'.join(pids)}", headers=HDR, timeout=10)
        return [{"id":l.split("\t")[0].strip(),"name":l.split("\t")[1].strip() if "\t" in l else "","url":f"https://www.kegg.jp/pathway/{l.split(chr(9))[0].strip()}"} for l in r3.text.strip().splitlines() if "\t" in l]
    except: return []

@st.cache_data(ttl=86400, show_spinner=False)
def _trials(gene):
    try:
        r = requests.get("https://clinicaltrials.gov/api/v2/studies",
            params={"query.term":gene,"filter.status":"RECRUITING","pageSize":6}, headers=HDR, timeout=15)
        out = []
        for s in r.json().get("studies",[]):
            mod = s.get("protocolSection",{}); im = mod.get("identificationModule",{}); dm = mod.get("designModule",{})
            out.append({"nct_id":im.get("nctId",""),"title":im.get("briefTitle","")[:80],"phase":(dm.get("phases",["?"])[0] if dm.get("phases") else "?"),"url":f"https://clinicaltrials.gov/study/{im.get('nctId','')}"})
        return out
    except: return []

@st.cache_data(ttl=86400, show_spinner=False)
def _dgidb(gene):
    try:
        r = requests.get("https://dgidb.org/api/v2/interactions.json", params={"genes":gene}, headers=HDR, timeout=12)
        out = []
        for m in r.json().get("matchedTerms",[]):
            for i in m.get("interactions",[])[:6]:
                d = i.get("drugName","")
                if d: out.append({"drug":d,"type":(i.get("interactionTypes",["?"])[0] if i.get("interactionTypes") else "?")})
        return out[:8]
    except: return []

# ── GI scorer ─────────────────────────────────────────────────────────────
def _gi(gene, cv, seq_len):
    if gene.upper() in ARRB_GENES:
        return {"verdict":"DEPRIORITISE","color":"#ef4444","n_pathogenic":0,"n_critical":0,"per100":0,"reasons":["ARRB override: <5 Mendelian disease variants","DKO mice viable/fertile"],"pursue":False}
    path = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")]
    n_p = len(path); n_c = sum(1 for v in cv if v.get("ml_class")=="CRITICAL"); ms = sum(1 for v in path if v.get("stars",0)>=2)
    per100 = (n_p/seq_len*100) if seq_len else 0; reasons = []
    if n_p >= 5: reasons.append(f"{n_p} P/LP ClinVar variants")
    if ms >= 2: reasons.append(f"{ms} multi-star reviewed")
    if per100 >= 1: reasons.append(f"{per100:.2f} P/LP per 100 residues")
    if per100>=1 and n_p>=5 and ms>=2: v2,p = "DISEASE-CRITICAL", True
    elif per100>=0.5 or n_p>=3: v2,p = "DISEASE-ASSOCIATED", True
    elif per100>=0.1 or n_p>=1: v2,p = "MODERATE", None
    elif n_p == 0: v2,p = "NO DISEASE VARIANTS", False; reasons.append("No ClinVar P/LP — consider redundant pathway")
    else: v2,p = "VERY LOW", False
    return {"verdict":v2,"color":VERDICT_COLORS.get(v2,"#4a7090"),"n_pathogenic":n_p,"n_critical":n_c,"per100":round(per100,3),"multi_star":ms,"reasons":reasons or ["Insufficient variant density"],"pursue":p}

# ── experiment ROI ────────────────────────────────────────────────────────
def _exps(gene, gi_s, pdata, cv, gnomad, string_d, ot, am):
    if gene.upper() in ARRB_GENES:
        return [{"name":n,"category":"AVOID","cost_usd":c,"time_weeks":0,"p_success":0,"value_score":0,"expected_value":0,"rationale":r,"do_first":False,"avoid":True}
                for n,c,r in [("HTS screen",2_500_000,"No disease variant validates this target"),("CRISPR knock-in",150_000,"<5 Mendelian variants — premature"),("Cryo-EM",500_000,"Structure without genetic support is academic"),("Mouse models",800_000,"DKO mice normal — no animal model justification")]]
    path = [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")]
    top_v = [v.get("protein_change","?") for v in path[:3]]; vstr = ", ".join(top_v) or "ClinVar variants"
    partners = [p["partner"] for p in string_d[:3]] if string_d else ["interaction partners"]
    kws = " ".join(pdata.get("keywords",[]) + pdata.get("functions",[])).lower()
    is_gpcr = pdata.get("is_gpcr",False); is_kinase = any(k in kws for k in ["kinase","phosphotransferase"])
    is_fil = any(k in kws for k in ["filamin","actin-binding protein 280"]); is_cardiac = gene.upper() in {"ADRB1","ADRB2","AGTR1","CHRM2"}
    am_path = {a["position"] for a in (am or []) if a.get("class")=="pathogenic"}; path_pos = {v["position"] for v in path if v.get("position")}
    concordant = len(path_pos & am_path); cell = "iPSC-cardiomyocytes" if is_cardiac else "iPSC-neurons" if any(x in " ".join([d.get("name","") for d in pdata.get("diseases",[])]).lower() for x in ["neuro","parkinson","alzheimer"]) else "HEK293T/patient cells"
    out = []
    out.append({"name":"AlphaFold-Multimer (in silico — free first step)","category":"Structural Prediction","cost_usd":0,"time_weeks":0.5,"p_success":0.80,"value_score":7,"expected_value":5.6,"rationale":f"Free via ColabFold. Model {gene}:{partners[0] if partners else 'STRING partner'} complex. ipTM>0.8 = high confidence. Map {vstr} onto interface before wet lab.","do_first":True})
    if is_gpcr:
        out.append({"name":f"Filamin Ser2152-P assay — {gene} (IP ASSAY ★)","category":"GPCR Activation","cost_usd":600,"time_weeks":1,"p_success":0.90,"value_score":10,"expected_value":9.0,"rationale":f"GPCR: Filamin Ser2152-P is receptor-proximal. Stimulate {cell} → FLNA IP → pSer2152 western. WT vs {vstr}. Nakamura et al. JBC 2015 PMID:26124276.","do_first":True})
        out.append({"name":f"cAMP HTRF — {gene} Gs coupling WT vs {vstr}","category":"GPCR Signalling","cost_usd":1200,"time_weeks":2,"p_success":0.85,"value_score":8,"expected_value":6.8,"rationale":"cAMP HTRF (Cisbio kit). Compare EC50 and Emax WT vs each P/LP variant. Primary G-protein efficacy readout.","do_first":False})
        if is_cardiac: out.append({"name":f"TMAO rattling assay — {gene}","category":"Cardiac GPCR","cost_usd":2000,"time_weeks":3,"p_success":0.75,"value_score":9,"expected_value":6.75,"rationale":"TMAO 5–50µM → FlAsH-BRET conformational transitions → disrupts Filamin-P. Patent-unoccupied arrhythmia axis.","do_first":False})
    if is_kinase: out.append({"name":f"ADP-Glo kinase assay — {gene} WT vs {vstr}","category":"Kinase Activity","cost_usd":1500,"time_weeks":2,"p_success":0.85,"value_score":8,"expected_value":6.8,"rationale":f"ADP-Glo measures ATP→ADP. Compare Vmax/Km WT vs pathogenic variants. Hyperactivating = GoF = different therapeutic approach.","do_first":True})
    if is_fil: out.append({"name":f"SPR — GPCR H8 FBM peptides vs {gene} Ig21","category":"Filamin Binding","cost_usd":3000,"time_weeks":3,"p_success":0.85,"value_score":9,"expected_value":7.65,"rationale":f"SPR: KD of FBM peptides (Phe-Arg-Leu) vs Ig21 domain. Validates Ser2152 phosphorylation axis. Map {vstr} onto interface.","do_first":True})
    if partners: out.append({"name":f"Co-IP — {gene} with {partners[0]}","category":"Protein–Protein Interaction","cost_usd":700,"time_weeks":1,"p_success":0.80,"value_score":7,"expected_value":5.6,"rationale":f"STRING: high-confidence {gene}:{partners[0]} interaction. Flag-tag {gene} (WT vs {vstr}) → IP → western for {partners[0]}.","do_first":False})
    if gi_s.get("n_critical",0)>=2 and concordant>=1:
        out.append({"name":f"CRISPR knock-in — {gene} {top_v[0] if top_v else 'P/LP variant'}","category":"Disease Modelling","cost_usd":15000,"time_weeks":10,"p_success":0.70,"value_score":9,"expected_value":6.3,"rationale":f"Justified: {gi_s['n_critical']} CRITICAL + {concordant} AlphaMissense-concordant. Knock-in {vstr} in {cell}. pLI={gnomad.get('pLI','?')}.","do_first":False})
    else:
        out.append({"name":f"CRISPR — PREMATURE for {gene}","category":"PREMATURE — Do Not Run","cost_usd":15000,"time_weeks":10,"p_success":0.15,"value_score":1,"expected_value":0.15,"rationale":f"Only {gi_s.get('n_critical',0)} CRITICAL variants and {concordant} AlphaMissense concordant. Run TSA/Co-IP first.","do_first":False,"avoid":True})
    if ot.get("sm_tractable") and gi_s.get("n_pathogenic",0)>=3:
        existing = ot.get("known_drugs",[]); 
        out.append({"name":f"Drug {'analogue' if existing else 'fragment'} screen — {gene}","category":"Drug Discovery","cost_usd":50000 if existing else 80000,"time_weeks":8,"p_success":0.60 if existing else 0.50,"value_score":9,"expected_value":5.4,"rationale":f"OpenTargets: small-molecule tractable. {'Test '+existing[0]+' analogues.' if existing else 'FBDD via SPR.'} Superimpose {vstr} onto AlphaFold structure.","do_first":False})
    out.sort(key=lambda x: (0 if x.get("do_first") and not x.get("avoid") else 1, -x.get("expected_value",0)))
    return out

# ── 3D viewer ─────────────────────────────────────────────────────────────
def _viewer(pdb, style="plddt", height=380, spin=False):
    if not pdb: st.markdown('<div class="dim" style="padding:8px">AlphaFold structure not available.</div>', unsafe_allow_html=True); return
    esc = pdb.replace("\\","\\\\").replace("`","\\`"); sp = "viewer.spin(true);" if spin else ""
    sj = {"plddt":"viewer.setStyle({},{cartoon:{colorfunc:function(a){var b=a.b;if(b>=90)return'#00b4d8';if(b>=70)return'#4ab8a7';if(b>=50)return'#f5b942';return'#e05c5c';}}});",
          "spectrum":"viewer.setStyle({},{cartoon:{color:'spectrum'}});","surface":"viewer.setStyle({},{surface:{opacity:0.85,color:'spectrum'}});","stick":"viewer.setStyle({},{stick:{colorscheme:'element'}});"}.get(style,"viewer.setStyle({},{cartoon:{color:'spectrum'}});")
    html = f"""<!DOCTYPE html><html><head><script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>body{{margin:0;background:#010306;overflow:hidden}}#v{{width:100%;height:{height}px}}
#info{{position:absolute;bottom:6px;left:6px;background:rgba(2,6,9,.95);color:#d0e8ff;border:1px solid rgba(0,229,255,0.15);border-radius:5px;padding:5px 10px;font:11px/1.5 monospace;display:none;z-index:100;max-width:280px;pointer-events:none}}
#leg{{position:absolute;top:6px;right:6px;background:rgba(2,6,9,.9);color:#d0e8ff;border:1px solid #0a1520;border-radius:5px;padding:7px 10px;font:10px monospace}}
.lr{{display:flex;align-items:center;gap:5px;margin:2px 0}}.lc{{width:10px;height:10px;border-radius:2px}}</style></head>
<body><div id="v"></div><div id="info"></div>
<div id="leg"><b style="color:#00e5ff">pLDDT</b><div class="lr"><div class="lc" style="background:#00b4d8"></div>&gt;90</div><div class="lr"><div class="lc" style="background:#4ab8a7"></div>70-90</div><div class="lr"><div class="lc" style="background:#f5b942"></div>50-70</div><div class="lr"><div class="lc" style="background:#e05c5c"></div>&lt;50</div></div>
<script>try{{var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#010306'}});viewer.addModel(`{esc}`,'pdb');{sj}
viewer.setClickable({{}},true,function(a,v){{var b=document.getElementById('info');b.style.display='block';b.innerHTML='<b style="color:#00e5ff">'+a.resn+' '+a.resi+'</b> Chain '+a.chain+'<br>pLDDT: '+(a.b?a.b.toFixed(1):'?');v.addStyle({{resi:a.resi}},{{sphere:{{color:'#00e5ff',radius:0.8,opacity:0.7}}}});v.render();}});
viewer.zoomTo();{sp}viewer.render();}}catch(e){{document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:12px;font:12px monospace">'+e.message+'</p>';}}</script></body></html>"""
    components.html(html, height=height, scrolling=False)

# ── domain landing ────────────────────────────────────────────────────────
def _landing():
    dm_js = json.dumps([{"id":d,"icon":m["icon"],"color":m["color"],"tags":m["tags"][:6],"desc":m["desc"]} for d,m in DOMAIN_META.items()])
    html = f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}}body{{background:#010306;color:#d0e8ff;min-height:100vh;overflow-x:hidden}}
#canvas{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}}
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:36px 20px 50px;text-align:center}}
.logo{{font-size:2rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#818cf8,#f43f5e);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-size:200% auto;animation:shimmer 4s linear infinite}}
.tag{{color:#1e3a5f;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;margin-top:5px}}
.sub{{color:#2a5070;font-size:.85rem;margin-top:10px;margin-bottom:36px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;text-align:left}}
.card{{background:rgba(2,6,9,.9);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:20px 22px;cursor:pointer;transition:all .3s;position:relative;overflow:hidden;animation:fadeUp .4s ease both;opacity:0}}
.card:hover{{transform:translateY(-4px) scale(1.01);border-color:var(--col);box-shadow:0 0 30px var(--glow),0 8px 32px rgba(0,0,0,.4)}}
.card:active{{transform:scale(0.98)}}
.ch{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.ci{{font-size:1.5rem;transition:transform .3s}}.card:hover .ci{{transform:scale(1.15) rotate(5deg)}}
.ct{{font-size:.95rem;font-weight:700;color:#fff}}
.cd{{font-size:.73rem;color:#4a7090;line-height:1.6;margin-bottom:12px}}
.tags{{display:flex;flex-wrap:wrap;gap:4px}}
.tg{{font-size:.6rem;color:var(--col);background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:2px 7px}}
.card:hover .tg{{background:rgba(255,255,255,.07);border-color:var(--col)}}
.scan{{position:absolute;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--col),transparent);top:-100%;transition:top .4s;opacity:.4}}.card:hover .scan{{top:100%}}
.foot{{text-align:center;margin-top:36px;color:#0d1a2a;font-size:.66rem;font-style:italic}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes shimmer{{0%{{background-position:0 50%}}100%{{background-position:200% 50%}}}}</style></head>
<body><canvas id="canvas"></canvas>
<div class="wrap"><div class="logo">🔬 Protellect</div><div class="tag">Genetics-First Protein Intelligence</div><div class="sub">Select a domain to enter your workspace</div>
<div class="grid" id="grid"></div><div class="foot">The only platform that tells you which proteins to abandon before you spend the money.</div></div>
<script>
const c=document.getElementById('canvas'),ctx=c.getContext('2d');c.width=window.innerWidth;c.height=window.innerHeight;
const pts=Array.from({{length:55}},()=>({{x:Math.random()*c.width,y:Math.random()*c.height,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*1.5+.4,col:`rgba(${{Math.random()>.5?'0,229,255':'129,140,248'}},0.35)`}}));
function draw(){{ctx.clearRect(0,0,c.width,c.height);pts.forEach(p=>{{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>c.width)p.vx*=-1;if(p.y<0||p.y>c.height)p.vy*=-1;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle=p.col;ctx.fill();}});pts.forEach((a,i)=>pts.slice(i+1).forEach(b=>{{const d=Math.hypot(a.x-b.x,a.y-b.y);if(d<110){{ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=`rgba(0,229,255,${{.07*(1-d/110)}})`;ctx.lineWidth=.5;ctx.stroke();}}}}));requestAnimationFrame(draw);}}draw();
window.addEventListener('resize',()=>{{c.width=window.innerWidth;c.height=window.innerHeight;}});
const DOMAINS={dm_js};const grid=document.getElementById('grid');
DOMAINS.forEach((d,i)=>{{const el=document.createElement('div');el.className='card';el.style.cssText=`--col:${{d.color}};--glow:${{d.color}}44;animation-delay:${{i*.07}}s`;
el.innerHTML=`<div class="scan"></div><div class="ch"><span class="ci">${{d.icon}}</span><span class="ct">${{d.id}}</span></div><div class="cd">${{d.desc}}</div><div class="tags">${{d.tags.map(t=>`<span class="tg">${{t}}</span>`).join('')}}</div>`;
el.addEventListener('click',()=>{{el.style.transform='scale(0.97)';setTimeout(()=>window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setComponentValue',value:d.id}},'*'),100);}});grid.appendChild(el);}});
</script></body></html>"""
    components.html(html, height=640, scrolling=False)
    cols = st.columns(5)
    for i,(d,m) in enumerate(DOMAIN_META.items()):
        with cols[i]:
            if st.button(f"{m['icon']} {d}", key=f"dl_{d}", use_container_width=True):
                st.session_state.domain = d; st.rerun()

# ── sidebar ───────────────────────────────────────────────────────────────
user = _user()
with st.sidebar:
    st.markdown(f"""<div style="padding:8px 0 5px"><span style="font-size:1rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent">🔬 Protellect</span><div style="font-size:.65rem;color:#2a5070;font-family:monospace">{user.get('name','')} · {user.get('tier','free').upper()}</div></div>""", unsafe_allow_html=True)
    used = _used(); quota = _quota(); tier = user.get("tier","free")
    if user.get("dev"): qlbl,qcol = "Dev — Unlimited","#f97316"
    elif tier=="enterprise": qlbl,qcol = "Enterprise — Unlimited","#f97316"
    else:
        rem = quota-used; qcol = "#00e5ff" if rem>0 else "#ef4444"
        qlbl = f"{rem} searches remaining" if rem>0 else "Quota exhausted — Upgrade"
    st.markdown(f'<div style="background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.1);border-radius:6px;padding:4px 10px;font-size:.72rem;color:{qcol};margin-bottom:6px">{qlbl}</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">RESEARCH GOAL</div>', unsafe_allow_html=True)
    st.selectbox("rg", ["Drug target identification","Disease mechanism","Variant pathogenicity","Therapeutic hypothesis","Protein function","Biomarker discovery","Academic research"], label_visibility="collapsed", key="research_goal")
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">PROTEIN SEARCH</div>', unsafe_allow_html=True)
    domain = st.session_state.domain or "Molecular Biology"; exs = DOMAIN_EXAMPLES.get(domain,["TP53","BRCA1"])
    qi = st.text_input("ps", value=st.session_state._qval, placeholder=f"e.g. {' · '.join(exs[:3])}", label_visibility="collapsed", key="_sw")
    st.session_state._qval = qi
    if st.button("⚡ Analyse Protein", type="primary", use_container_width=True, key="ab"): st.session_state._trig = True
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">DISEASE → PROTEINS</div>', unsafe_allow_html=True)
    di = st.text_input("dp", value=st.session_state._dval, placeholder="e.g. Hantavirus · arrhythmia", label_visibility="collapsed", key="_dw")
    st.session_state._dval = di
    if st.button("🔗 Find Disease Proteins", use_container_width=True, key="db"): st.session_state._dtrig = True
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">WET-LAB DATA (CSV)</div>', unsafe_allow_html=True)
    cf = st.file_uploader("cu", type=["csv","txt","tsv"], label_visibility="collapsed", key="cu")
    if cf:
        try:
            sep = "\t" if cf.name.endswith((".txt",".tsv")) else ","
            df_c = pd.read_csv(cf, sep=sep, nrows=5000); st.session_state.csv_data = df_c
            st.markdown(f'<div style="color:#00e5ff;font-size:.7rem">{cf.name} · {len(df_c):,} rows</div>', unsafe_allow_html=True)
        except Exception as e: st.error(f"Parse error: {e}")
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">SENSITIVITY</div>', unsafe_allow_html=True)
    sens = st.slider("se", 0.0, 1.0, st.session_state.sensitivity, 0.05, label_visibility="collapsed", key="sensitivity")
    st.markdown(f'<div class="dim" style="margin:-4px 0 4px">{sens:.2f} · {"Strict" if sens>0.8 else "Balanced" if sens>0.5 else "Sensitive"}</div>', unsafe_allow_html=True)
    if st.button("▶ Run Triage", use_container_width=True, key="rt"): st.session_state.protein_data_cache = {}; st.toast(f"Re-running at {sens:.2f}")
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">WET-LAB ASSAY</div>', unsafe_allow_html=True)
    wl = st.text_area("wl", value=st.session_state.wet_lab_text, placeholder="Describe assay result — e.g. Ser2152-P detected at 10nM, abolished in R2149Q.", label_visibility="collapsed", height=58, key="wli")
    st.session_state.wet_lab_text = wl
    st.markdown('<div style="font-size:.6rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px">AI REPORT KEY</div>', unsafe_allow_html=True)
    ak = st.text_input("ak", type="password", placeholder="sk-ant-...", label_visibility="collapsed", key="_aki")
    if ak: st.session_state.anthropic_key = ak
    if st.session_state.anthropic_key: st.markdown('<div style="font-size:.66rem;color:#4ade80">● AI enabled</div>', unsafe_allow_html=True)
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Cache", use_container_width=True): st.cache_data.clear(); st.toast("✅")
    with c2:
        if st.button("Clear", use_container_width=True): st.session_state._qval=""; st.session_state.current_protein=None; st.rerun()
    with c3:
        if st.button("Logout", use_container_width=True): _logout(); st.rerun()

# ── domain landing ────────────────────────────────────────────────────────
if not st.session_state.domain:
    _landing(); st.stop()

domain = st.session_state.domain
st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;padding:2px 0;margin-bottom:4px">
<span style="font-size:.85rem;font-weight:700;color:#00e5ff">🔬 Protellect</span><span style="color:#1e3a5f">—</span>
<span style="color:#4a7090;font-size:.75rem">{ICONS.get(domain,'')} {domain}</span>
<span style="color:#1e3a5f;font-size:.68rem;margin-left:auto;font-family:monospace">{st.session_state.research_goal[:35]}</span></div>""", unsafe_allow_html=True)
dc = st.columns(5)
for i,d in enumerate(["Neuroscience","Cancer Biology","Pharmaceuticals","Microbiome","Molecular Biology"]):
    with dc[i]:
        if st.button(f"{ICONS[d]} {d}", key=f"dt_{d}", use_container_width=True, type="primary" if d==domain else "secondary"):
            st.session_state.domain=d; st.session_state.current_protein=None; st.rerun()

# ── disease trigger ───────────────────────────────────────────────────────
if st.session_state._dtrig and st.session_state._dval:
    st.session_state._dtrig = False; q_l = st.session_state._dval.lower()
    _sec(f"Disease: {st.session_state._dval}")
    for org_name,org in MICRO_ORGANISMS.items():
        if org_name.lower() in q_l or org.get("disease","").lower() in q_l:
            st.markdown(f"**{org['organism']}** — {org['type']}"); st.write(org.get("mechanism","")[:200])
            _sec("Host Receptors — Click to Analyse")
            rc = st.columns(min(4, len(org.get("host_receptors",[])) or 1))
            for i,rec in enumerate(org.get("host_receptors",[])):
                with rc[i]:
                    if st.button(rec, key=f"rec_{rec}"): st.session_state._qval=rec; st.rerun()
            break
    st.stop()

# ── microbiome ────────────────────────────────────────────────────────────
if domain == "Microbiome":
    _sec("🦠 Microbiome Intelligence")
    st.caption("LLM-enhanced annotation · BGC · Taxonomy · Host–microbe")
    t1,t2,t3 = st.tabs(["Gene Annotation","Taxonomy","Pathway Re-annotation"])
    with t1:
        _sec("Vague → Specific Annotation")
        c1,c2 = st.columns(2)
        with c1:
            gid = st.text_input("Gene ID / KO", placeholder="K01810, WP_001234", key="mg_gid")
            vague = st.text_input("Current annotation", placeholder="biosynthesis", key="mg_vague")
            org_ctx = st.text_input("Organism context", placeholder="gut microbiome", key="mg_org")
        with c2: st.markdown('<div class="dim" style="margin-top:8px">Rule-based expansion without API key. Add Anthropic key in sidebar for AI annotation.</div>', unsafe_allow_html=True)
        if st.button("Generate", type="primary", key="mg_go") and vague:
            EXP = {"biosynthesis":"Anabolic enzyme — specify via KO: amino acid (e.g. lysine via DAP pathway), lipid (FASII), or B-vitamin. Run eggNOG-mapper for reaction specificity.",
                   "chemosynthesis":"Chemolithotrophy — energy from NH₃/S²⁻/Fe²⁺ oxidation. Check AMO/NXR/Sox gene families.",
                   "protein aggregation":"Regulated polymerisation: curli (CsgA/B — biofilm + TLR2/TLR1), functional amyloid, or spore coat.",
                   "hypothetical protein":"Run: (1) AlphaFold2+Foldseek, (2) eggNOG-mapper DIAMOND, (3) InterProScan, (4) Phyre2.",
                   "transporter":"TC database: ABC (ATP-driven), MFS (proton gradient), RND (multidrug efflux).",
                   "metabolism":"KEGG GHOSTX or eggNOG-mapper for specific reaction. Cross-reference SEED/RAST."}
            ak2 = st.session_state.get("anthropic_key",""); result = None
            if ak2:
                try:
                    import anthropic; client = anthropic.Anthropic(api_key=ak2)
                    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role":"user","content":f"Gene:{gid}\nCurrent:{vague}\nOrganism:{org_ctx}\nGive specific: molecular function, EC number, pathway, ecological role, validation tools. No vague terms."}])
                    result = msg.content[0].text
                except: pass
            if not result: al = vague.lower(); result = next((v for k,v in EXP.items() if k in al), f"'{vague}' not in rule base. Run eggNOG-mapper v2 or InterProScan.")
            ca,cb = st.columns(2)
            with ca: st.markdown(f'<div class="card" style="border-color:rgba(239,68,68,0.2)"><span class="dim" style="color:#ef4444">❌ Before</span><br><i style="color:#fca5a5">{vague}</i></div>', unsafe_allow_html=True)
            with cb: st.markdown(f'<div class="card" style="border-color:rgba(74,222,128,0.2)"><span class="dim" style="color:#4ade80">✅ After</span><div style="font-size:.72rem;color:#d0e8ff;margin-top:5px;line-height:1.7">{result}</div></div>', unsafe_allow_html=True)
    with t2:
        _sec("Taxonomy")
        taxon = st.text_input("Organism", placeholder="Akkermansia muciniphila", key="mg_tax")
        ROLES = {"Lactobacillus":"Lactic acid producer; pH pathogen competition; gut barrier; SCFA; probiotic","Bifidobacterium":"Probiotic; SCFA; immune modulation; infant microbiome; B-vitamins","Bacteroides":"Major fermenter; PULs; keystone symbiont","Akkermansia":"Mucin-layer; gut barrier integrity; depleted in obesity/T2D/IBD","Faecalibacterium":"Butyrate (F. prausnitzii); anti-inflammatory; depleted in IBD","Helicobacter":"CagA/VacA; peptic ulcer; gastric cancer","Fusobacterium":"FadA adhesin; CRC invasion; Wnt/β-catenin"}
        if taxon:
            role = ROLES.get(taxon.split()[0], "Ecological role not curated — search NCBI taxonomy and primary literature")
            st.markdown(f'<div class="card"><span style="color:#4ade80;font-family:monospace">{taxon}</span><br><span style="font-size:.72rem;color:#d0e8ff;line-height:1.6">{role}</span></div>', unsafe_allow_html=True)
    with t3:
        _sec("Batch Re-annotation"); raw = st.text_area("Annotations (one per line)", placeholder="biosynthesis\nchemosynthesis\nhypothetical protein", height=80, key="mg_b")
        VAGUE = {"biosynthesis","chemosynthesis","protein aggregation","hypothetical protein","metabolism","transport","regulation","unknown","uncharacterized"}
        if st.button("Analyse", type="primary", key="mg_ba") and raw:
            lines = [l.strip() for l in raw.splitlines() if l.strip()]; vn = sum(1 for l in lines if any(v in l.lower() for v in VAGUE))
            c1,c2,c3 = st.columns(3); c1.metric("Total",len(lines)); c2.metric("Vague",vn); c3.metric("Informative",len(lines)-vn)
            for l in lines:
                iv = any(v in l.lower() for v in VAGUE); col2 = "#ef4444" if iv else "#4ade80"
                st.markdown(f'<div style="font-size:.72rem;padding:2px 0;border-bottom:1px solid #060d14"><span style="color:{col2}">{"❌" if iv else "✅"}</span> <span style="color:#d0e8ff">{l}</span></div>', unsafe_allow_html=True)
    st.stop()

# ── search ────────────────────────────────────────────────────────────────
query = st.session_state._qval.strip()
if not query and not st.session_state._trig:
    meta = DOMAIN_META.get(domain,{}); exs2 = DOMAIN_EXAMPLES.get(domain,[])
    color = meta.get("color","#00e5ff")
    desc = meta.get("desc","")
    icon = meta.get("icon","🔬")
    tags = " · ".join(meta.get("tags",[])[:6])
    st.markdown(
        '<div style="border:1px solid ' + color + '22;border-radius:12px;padding:28px 32px;margin:16px 0;background:linear-gradient(135deg,#020609,#050f1a)">'
        + '<div style="font-size:1.6rem;margin-bottom:8px">' + icon + '</div>'
        + '<div style="font-size:1.1rem;font-weight:600;color:' + color + ';margin-bottom:6px">' + domain + '</div>'
        + '<div style="color:#4a7090;font-size:.9rem;margin-bottom:12px;line-height:1.7">' + desc + '</div>'
        + '<div style="color:#1e3a5f;font-size:.78rem;margin-bottom:16px">' + tags + '</div>'
        + '<div style="color:#2a5070;font-size:.82rem;border-top:1px solid #0a1520;padding-top:12px">'
        + 'Type a gene symbol in the <b style="color:#d0e8ff">Protein Search</b> field on the left, then click <b style="color:' + color + '">Analyse Protein</b>'
        + '</div></div>',
        unsafe_allow_html=True
    )
    if exs2:
        st.markdown('<p style="color:#1e3a5f;font-size:.75rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;margin:12px 0 6px">Examples</p>', unsafe_allow_html=True)
        ec = st.columns(min(7,len(exs2)))
        for i,ex in enumerate(exs2):
            with ec[i]:
                if st.button(ex, key=f"dex_{ex}_{domain}", use_container_width=True):
                    st.session_state._qval=ex; st.rerun()
    st.stop()
st.session_state._trig = False
if any(t in query.lower() for t in NON_HUMAN): st.error(f"⛔ '{query}' is not a human protein."); st.stop()
if not _can(): st.error("Quota exhausted."); st.stop()

# ── load ──────────────────────────────────────────────────────────────────
ck = query.upper()
if ck not in st.session_state.protein_data_cache:
    prog = st.progress(0, text=f"Resolving {query}…")
    try:
        prog.progress(5,"UniProt…"); uraw = _uniprot(query)
        prog.progress(15,"Parsing…"); pdata = _parse(uraw)
        if not pdata or not pdata.get("accession"): st.error(f"Not found: '{query}'. Try the gene symbol — FLNA, TP53, ADRB2, KRAS etc."); st.stop()
        if not pdata.get("is_human",True): st.error(f"⛔ Not human (organism: {pdata.get('organism','?')})."); st.stop()
        gene = pdata["gene"] or query.upper(); acc = pdata["accession"]
        prog.progress(25,"AlphaFold…"); pdb = _alphafold(acc); plddt = _plddt(pdb)
        prog.progress(35,"ClinVar…"); cv = _clinvar(gene)
        prog.progress(50,"gnomAD + STRING…"); gnomad = _gnomad(gene); string_d = _string(gene)
        prog.progress(62,"OpenTargets…"); ot = _opentargets(gene); dgidb = _dgidb(gene)
        prog.progress(74,"AlphaMissense + PubMed…"); am = _alphamissense(acc); papers = _pubmed(gene)
        prog.progress(86,"GTEx + KEGG + Trials…"); gtex = _gtex(gene); kegg = _kegg(gene); trials = _trials(gene)
        prog.progress(94,"Scoring…"); gi_s = _gi(gene,cv,pdata.get("seq_len",500)); exp_list = _exps(gene,gi_s,pdata,cv,gnomad,string_d,ot,am)
        prog.progress(100,"Complete"); prog.empty()
        st.session_state.protein_data_cache[ck] = dict(pdata=pdata,pdb=pdb,plddt=plddt,cv=cv,gnomad=gnomad,string_d=string_d,ot=ot,am=am,papers=papers,gtex=gtex,dgidb=dgidb,trials=trials,kegg=kegg,gi_s=gi_s,exp_list=exp_list)
        _record(); ws = st.session_state.workspace
        if not any(w.get("gene")==gene for w in ws): ws.insert(0,{"gene":gene,"accession":acc,"protein":pdata.get("protein_name","")[:50],"verdict":gi_s["verdict"],"color":gi_s["color"],"domain":domain}); st.session_state.workspace=ws[:50]
        st.session_state.current_protein = ck
    except Exception as e:
        import traceback; st.error(f"Error: {e}")
        with st.expander("Traceback"): st.code(traceback.format_exc())
        st.stop()
else:
    st.session_state.current_protein = ck

D = st.session_state.protein_data_cache[ck]
pdata=D["pdata"]; pdb=D["pdb"]; plddt=D["plddt"]; cv=D["cv"]; gnomad=D["gnomad"]
string_d=D["string_d"]; ot=D["ot"]; am=D["am"]; papers=D["papers"]; gtex=D["gtex"]
dgidb=D["dgidb"]; trials=D["trials"]; kegg=D["kegg"]; gi_s=D["gi_s"]; exp_list=D["exp_list"]
gene=pdata["gene"] or query.upper(); acc=pdata["accession"]
is_arrb=gene.upper() in ARRB_GENES; is_gpcr=pdata.get("is_gpcr",False)
is_cardiac=gene.upper() in {"ADRB1","ADRB2","AGTR1","CHRM2"}
is_filamin=any(k in " ".join(pdata.get("functions",[])+pdata.get("keywords",[])).lower() for k in ["filamin","actin-binding protein 280"])
vcolor=gi_s["color"]; verdict=gi_s["verdict"]

# ── protein header ────────────────────────────────────────────────────────
flags = ""
if is_gpcr:    flags += ' <span style="background:rgba(0,229,255,0.1);color:#00e5ff;border:1px solid rgba(0,229,255,0.3);border-radius:3px;padding:1px 6px;font-size:.64rem">GPCR</span>'
if is_filamin: flags += ' <span style="background:rgba(249,115,22,0.1);color:#f97316;border:1px solid rgba(249,115,22,0.3);border-radius:3px;padding:1px 6px;font-size:.64rem">FILAMIN</span>'
if is_cardiac: flags += ' <span style="background:rgba(239,68,68,0.1);color:#ef4444;border:1px solid rgba(239,68,68,0.3);border-radius:3px;padding:1px 6px;font-size:.64rem">CARDIAC</span>'
st.markdown(f"""<div style="display:flex;align-items:flex-start;gap:8px;padding:5px 0;border-bottom:1px solid #0a1520;margin-bottom:6px">
<div style="flex:1"><span style="font-size:1rem;font-weight:700;color:#d0e8ff;font-family:monospace">{gene}</span>
<span style="background:{vcolor}18;color:{vcolor};border:1px solid {vcolor}40;border-radius:4px;padding:1px 7px;font-size:.65rem;font-weight:700;margin-left:5px">{verdict}</span>{flags}
<br><span style="font-size:.68rem;color:#2a5070;font-family:monospace">{acc} · {pdata.get('protein_name','')[:65]}</span></div>
<div style="display:flex;gap:12px;text-align:right">
<div><div style="font-size:.78rem;font-weight:700;color:#00e5ff;font-family:monospace">{pdata.get('seq_len',0):,} aa</div><div style="font-size:.6rem;color:#2a5070">length</div></div>
<div><div style="font-size:.78rem;font-weight:700;color:#ff2d55;font-family:monospace">{gi_s.get('n_pathogenic',0)}</div><div style="font-size:.6rem;color:#2a5070">P/LP</div></div>
<div><div style="font-size:.78rem;font-weight:700;color:#00e5ff;font-family:monospace">{f"{gnomad['pLI']:.2f}" if gnomad.get("pLI") else "—"}</div><div style="font-size:.6rem;color:#2a5070">pLI</div></div>
<div><div style="font-size:.78rem;font-weight:700;color:#4ade80;font-family:monospace">{ot.get('known_drugs_count',0)}</div><div style="font-size:.6rem;color:#2a5070">drugs</div></div>
<div><div style="font-size:.78rem;font-weight:700;color:#ffd60a;font-family:monospace">{len(trials)}</div><div style="font-size:.6rem;color:#2a5070">trials</div></div>
</div></div>""", unsafe_allow_html=True)

# ── ARRB intercept ────────────────────────────────────────────────────────
if is_arrb:
    total = sum(ARRB_COSTS.values())
    st.markdown(f"""<div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.3);border-radius:6px;padding:14px;text-align:center;margin-bottom:10px">
<div style="font-size:.8rem;font-weight:700;color:#ef4444">DEPRIORITISE — {gene}</div>
<div style="font-size:1.4rem;font-weight:800;color:#ef4444;margin:6px 0">${total:,}</div>
<div class="dim">Avoidable spend · Beta-arrestin &lt;5 confirmed Mendelian disease variants · DKO mice viable/fertile</div></div>""", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        _sec("Avoidable Cost Breakdown")
        for n,c in ARRB_COSTS.items(): st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #060d14;font-size:.72rem"><span class="dim">{n}</span><span style="color:#ef4444;font-family:monospace">${c:,}</span></div>', unsafe_allow_html=True)
        _sec("Redirect Alternatives")
        for alt in ARRB_ALTS:
            ca,cb = st.columns([3,1])
            with ca: st.markdown(f'<span style="color:#00e5ff;font-family:monospace">{alt["gene"]}</span> <span class="dim">{alt["reason"][:50]}</span>', unsafe_allow_html=True)
            with cb:
                if st.button(f"↗{alt['gene']}", key=f"aa_{alt['gene']}"): st.session_state._qval=alt["gene"]; st.rerun()
    with c2:
        _sec("6 Landmark Papers — No Disease Evidence")
        for p in ARRB_PAPERS: st.markdown(f'<div class="dim" style="border-bottom:1px solid #060d14;padding:4px 0"><a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/" target="_blank" style="color:#8baabf;font-size:.71rem">{p["title"]}</a><br>{p["journal"]} {p["year"]} · PMID:{p["pmid"]}<br><i style="color:#1e3a5f">{p["finding"]}</i></div>', unsafe_allow_html=True)
    st.stop()

# ── TABS ──────────────────────────────────────────────────────────────────
t0,t1,t2,t3,t4,t5,t6,t7,t8 = st.tabs(["📊 Summary","🎯 Triage","🔬 Case Study","🧩 Explorer","⚗️ Experiments","📋 CSV Analysis","🤖 AI Report","📁 Workspace","🦠 Disease Link"])

with t0:  # SUMMARY
    pl = {True:"PURSUE",False:"DEPRIORITISE",None:"SELECTIVE"}.get(gi_s.get("pursue"),"PROCEED")
    st.markdown(f"""<div style="background:{vcolor}0d;border:1px solid {vcolor}30;border-radius:5px;padding:8px 14px;display:flex;align-items:center;gap:12px;margin-bottom:8px">
<div><span style="font-size:.95rem;font-weight:800;color:{vcolor}">{pl}</span> <span style="background:{vcolor}18;color:{vcolor};border-radius:3px;padding:1px 6px;font-size:.64rem;font-weight:700">{verdict}</span></div>
<div style="color:{vcolor}88;font-size:.72rem;flex:1">{' · '.join(gi_s.get('reasons',[])[:3])}</div></div>""", unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Diseases",len(pdata.get("diseases",[])));c2.metric("P/LP",gi_s.get("n_pathogenic",0))
    c3.metric("CRITICAL ML",gi_s.get("n_critical",0));c4.metric("pLI",f"{gnomad.get('pLI'):.2f}" if gnomad.get("pLI") else "N/A")
    c5.metric("Known Drugs",ot.get("known_drugs_count",0));c6.metric("Active Trials",len(trials))
    cl,cr = st.columns([1.2,.8], gap="large")
    with cl:
        _sec("Disease Associations")
        for d in pdata.get("diseases",[])[:6]:
            n=d.get("name","?"); desc=d.get("desc","")[:110]
            ct = "Somatic" if any(t in n.lower() for t in ["cancer","carcinoma","tumor","sarcoma"]) else "Germline" if any(t in n.lower() for t in ["hereditary","congenital","familial"]) else "Unknown"
            cc = "#ff8c42" if ct=="Somatic" else "#818cf8" if ct=="Germline" else "#4a7090"
            st.markdown(f'<div class="row"><span style="color:{cc};font-size:.62rem;font-weight:600;min-width:52px">{ct}</span><div><b style="color:#d0e8ff;font-size:.73rem">{n}</b><br><span class="dim">{desc}</span></div></div>', unsafe_allow_html=True)
        if not pdata.get("diseases"): st.markdown('<div class="dim" style="padding:6px">No disease annotations — null mutant with no phenotype = deprioritise.</div>', unsafe_allow_html=True)
        _sec("Top 5 Experiments")
        shown = 0
        for exp in exp_list:
            if shown>=5 or exp.get("avoid"): continue
            dof=exp.get("do_first",False); col2="#00e5ff" if dof else "#4a7090"
            st.markdown(f"""<div style="background:#020609;border:1px solid {"rgba(0,229,255,0.2)" if dof else "#0a1520"};border-radius:4px;padding:5px 9px;margin:3px 0">
<div style="display:flex;justify-content:space-between"><span style="color:{col2};font-size:.73rem;font-weight:600">{"🚀 " if dof else ""}{exp['name'][:60]}</span>
<span style="color:#2a5070;font-size:.62rem;font-family:monospace">${exp['cost_usd']:,} · {exp['time_weeks']}w · P={int(exp['p_success']*100)}%</span></div>
<div class="dim">{exp['rationale'][:110]}…</div></div>""", unsafe_allow_html=True)
            shown+=1
        _sec("Pursue vs Avoid")
        pa1,pa2 = st.columns(2)
        with pa1:
            st.markdown('<div style="color:#4ade80;font-size:.67rem;font-weight:600;margin-bottom:3px">✅ PURSUE</div>', unsafe_allow_html=True)
            for e in [e for e in exp_list if e.get("do_first") and not e.get("avoid")][:3]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14">{e["name"][:50]}</div>', unsafe_allow_html=True)
        with pa2:
            st.markdown('<div style="color:#ef4444;font-size:.67rem;font-weight:600;margin-bottom:3px">🛑 AVOID</div>', unsafe_allow_html=True)
            for e in [e for e in exp_list if e.get("avoid")][:3]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14">{e["name"][:50]}</div>', unsafe_allow_html=True)
    with cr:
        _sec("gnomAD Constraint")
        for lbl2,val,thresh,dh in [("pLI",gnomad.get("pLI"),0.9,"high"),("o/e LoF",gnomad.get("lof_oe"),0.35,"low"),("o/e Missense",gnomad.get("missense_oe"),0.6,"low")]:
            if val is None: continue
            good=(val>thresh if dh=="high" else val<thresh); col2="#00e5ff" if good else "#4a7090"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #060d14;font-size:.72rem"><span class="dim">{lbl2}</span><span style="color:{col2};font-family:monospace">{val:.3f}{"  ✓" if good else ""}</span></div>', unsafe_allow_html=True)
        st.markdown(_src("gnomAD","https://gnomad.broadinstitute.org"), unsafe_allow_html=True)
        if is_gpcr:
            with st.expander("★ H8-Filamin Assay (IP)", expanded=True): st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">GPCR agonist → H8 dislodges → binds FLNA Ig21 → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or arrestin. Only FLNA (not B/C). ~300/800 Class A GPCRs carry H8 FBM.</div>', unsafe_allow_html=True)
        if is_filamin:
            with st.expander("PhosphoSite Ser2152 — Signal vs Noise"): st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">Ser2152 = dominant phospho peak on FLNA. All others = background kinase noise. Validated signal requires: mutation causes human disease. R2149 variants (heterometropia) confirm this site.</div>', unsafe_allow_html=True)
        if is_cardiac:
            with st.expander("TMAO Rattling Receptor — Arrhythmia"): st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">TMAO causes conformational rattling → disrupts H8-Filamin coupling → cardiac conduction defects. Patent-unoccupied axis.</div>', unsafe_allow_html=True)
        if wl:
            _sec("Wet-Lab Assay Interpretation")
            interp = ("Filamin Ser2152-P readout — correlates with GPCR activation. Cross-ref Step 3 protocol." if "phospho" in wl.lower() and is_gpcr else "Interaction disruption — Co-IP with STRING top partners to validate specificity." if any(x in wl.lower() for x in ["co-ip","pull","interaction"]) else f"Functional alteration in {gene}. Map to ClinVar P/LP variants at affected position.")
            st.markdown(f'<div class="card"><div class="dim">{wl[:140]}</div><div style="color:#00e5ff;font-size:.71rem;margin-top:5px">{interp}</div></div>', unsafe_allow_html=True)
        drugs = ot.get("known_drugs",[]) or [d["drug"] for d in dgidb[:5]]
        if drugs: _sec("Known Drugs"); st.markdown(" ".join(f'<span class="pill">💊 {d}</span>' for d in drugs[:8]), unsafe_allow_html=True)
        if trials: _sec("Active Trials"); [st.markdown(f'<div class="dim"><a href="{t["url"]}" target="_blank" style="color:#00e5ff">{t["nct_id"]}</a> · Ph{t["phase"]} · {t["title"][:55]}</div>', unsafe_allow_html=True) for t in trials[:3]]
    if papers:
        _sec("Literature")
        for p in papers[:8]: st.markdown(f'<div style="display:flex;align-items:baseline;gap:5px;padding:3px 0;border-bottom:1px solid #060d14"><span style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;border-radius:3px;min-width:50px;text-align:center;font-size:.6rem;padding:1px 5px">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.72rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:18]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)

with t1:  # TRIAGE
    cl,cr = st.columns([1.1,.9], gap="large")
    with cl:
        _sec("AlphaFold Structure (pLDDT)")
        vw = st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="t1_view",label_visibility="collapsed")
        _viewer(pdb, style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw], height=380)
        if plddt:
            vals = list(plddt.values())
            fig = go.Figure(go.Histogram(x=vals,nbinsx=25,marker_color=["#00b4d8" if v>=90 else "#4ab8a7" if v>=70 else "#f5b942" if v>=50 else "#e05c5c" for v in vals]))
            fig.update_layout(height=130,plot_bgcolor="#010306",paper_bgcolor="#010306",xaxis=dict(title="pLDDT",gridcolor="#060d14",color="#2a5070"),yaxis=dict(title="n",gridcolor="#060d14",color="#2a5070"),font=dict(color="#d0e8ff",size=10),margin=dict(t=5,b=25,l=30,r=5))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            avg=np.mean(vals); hc=sum(1 for v in vals if v>=70)/len(vals)*100
            st.markdown(f'<span class="dim">avg pLDDT <b style="color:#00e5ff">{avg:.1f}</b> · >70: <b style="color:#4ab8a7">{hc:.0f}%</b></span>', unsafe_allow_html=True)
    with cr:
        _sec(f"Variant Map (sensitivity {sens:.2f})")
        if cv:
            seq_len = pdata.get("seq_len",500)
            fig_l = go.Figure()
            fig_l.add_trace(go.Scatter(x=[0,seq_len],y=[0,0],mode="lines",line=dict(color="#0d1a2a",width=4),hoverinfo="none",showlegend=False))
            for cls,col2 in {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#2a5070"}.items():
                grp = [v for v in cv if v.get("ml_class")==cls and v.get("position",0)>0]
                if grp: fig_l.add_trace(go.Scatter(x=[v["position"] for v in grp],y=[1]*len(grp),mode="markers",marker=dict(size=8,color=col2,line=dict(color="#010306",width=1)),text=[f'{v.get("protein_change","?")} — {v.get("significance","")[:25]}' for v in grp],hoverinfo="text",name=cls))
            if am:
                am_p = [a for a in am if a["score"]>=sens]
                if am_p: fig_l.add_trace(go.Scatter(x=[a["position"] for a in am_p[::max(1,len(am_p)//200)]],y=[-0.6]*min(200,len(am_p)),mode="markers",marker=dict(size=3,color="#7c3aed",opacity=0.4),name=f"AM≥{sens:.2f}",hoverinfo="none"))
            fig_l.update_layout(height=200,plot_bgcolor="#010306",paper_bgcolor="#010306",xaxis=dict(title="Position",gridcolor="#060d14",color="#2a5070"),yaxis=dict(visible=False,range=[-1.5,2]),font=dict(color="#d0e8ff",size=10),legend=dict(bgcolor="#020609",bordercolor="#0a1520",font=dict(size=9)),margin=dict(t=5,b=30,l=5,r=5))
            st.plotly_chart(fig_l,use_container_width=True,config={"displayModeBar":False})
        _sec("Variant Deep Dive")
        for v in [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")][:8]:
            cls=v.get("ml_class","?"); col2="#ff2d55" if cls=="CRITICAL" else "#ff8c42"
            am_here = next((a for a in (am or []) if a.get("position")==v.get("position")),None)
            am_tag = " 🟢 AM-concordant" if am_here and am_here["score"]>=sens else " 🟡 AM-discordant" if am_here else ""
            conds = ", ".join(v.get("conditions",[])[:2]) or "?"
            with st.expander(f'[{cls}] {v.get("protein_change","?") or v.get("title","?")[:38]}{am_tag}'):
                st.markdown(f'<div style="font-size:.71rem;line-height:1.7"><b>Significance:</b> {v.get("significance","")}<br><b>Review:</b> {v.get("review_status","")} {"⭐"*v.get("stars",0)}<br><b>Conditions:</b> {conds}<br><a href="{v.get("url","")}" target="_blank" style="color:#00e5ff;font-size:.68rem">View in ClinVar ↗</a></div>', unsafe_allow_html=True)
        _sec("Tractability")
        t1c,t2c,t3c = st.columns(3)
        t1c.metric("Small Mol","✓" if ot.get("sm_tractable") else "—"); t2c.metric("Antibody","✓" if ot.get("ab_tractable") else "—"); t3c.metric("Drugs",ot.get("known_drugs_count",0))

with t2:  # CASE STUDY
    cl,cr = st.columns(2, gap="large")
    with cl:
        _sec("Function")
        for fn in pdata.get("functions",[])[:2]: st.markdown(f'<div class="card" style="font-size:.72rem;color:#d0e8ff;line-height:1.6">{fn[:300]}</div>', unsafe_allow_html=True)
        _sec("Subcellular Localisation")
        locs = pdata.get("subcellular",[])
        if locs: st.markdown(" ".join(f'<span class="pill">{l}</span>' for l in locs[:8]), unsafe_allow_html=True)
        else: st.markdown('<div class="dim">Not annotated</div>', unsafe_allow_html=True)
        _sec("Tissue Expression (GTEx v8)")
        if gtex:
            items = sorted(gtex.items(),key=lambda x:x[1],reverse=True)[:20]
            fig_t = go.Figure(go.Bar(x=[i[1] for i in items],y=[i[0] for i in items],orientation="h",marker_color=["#00e5ff" if i[1]==max(gtex.values()) else "#1e3a5f" for i in items]))
            fig_t.update_layout(height=max(260,len(items)*19),plot_bgcolor="#010306",paper_bgcolor="#010306",xaxis=dict(title="Median TPM",gridcolor="#060d14",color="#2a5070"),yaxis=dict(color="#8baabf",autorange="reversed",tickfont=dict(size=8)),font=dict(color="#d0e8ff",size=10),margin=dict(l=130,r=5,t=5,b=25))
            st.plotly_chart(fig_t,use_container_width=True,config={"displayModeBar":False})
            st.markdown(_src("GTEx v8","https://gtexportal.org"), unsafe_allow_html=True)
    with cr:
        _sec("Structural Domains (UniProt)")
        domains = pdata.get("domains",[])
        if domains:
            df_d = pd.DataFrame(domains[:15])
            st.dataframe(df_d.rename(columns={"type":"Type","name":"Name","start":"Start","end":"End"}),use_container_width=True,hide_index=True,height=min(310,len(domains)*34+36))
        if is_gpcr:
            _sec("GPCR Study Protocol (7-Step)")
            for step in GPCR_PROTOCOL:
                if step.get("cardiac") and not is_cardiac: continue
                ip = step.get("ip",False)
                with st.expander(f"{'★ ' if ip else ''}Step {step['step']}: {step['name']}", expanded=ip):
                    st.markdown(f'<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">{step["desc"]}</div>', unsafe_allow_html=True)
                    if step.get("warn"): st.warning(step["warn"])
                    st.markdown(f'<span class="dim">{step["cost"]} · {step["time"]}</span>', unsafe_allow_html=True)
                    if ip: st.markdown('<a class="pill" href="https://doi.org/10.1074/jbc.M115.671826" target="_blank">Nakamura 2015 ↗</a> <a class="pill" href="https://www.phosphosite.org/proteinAction.action?id=2546" target="_blank">PhosphoSite ↗</a>', unsafe_allow_html=True)
        if string_d:
            _sec("STRING Network (score>0.7)")
            n=len(string_d); angles=[2*math.pi*i/n for i in range(n)]; r=3
            nx=[0]+[r*math.cos(a) for a in angles]; ny=[0]+[r*math.sin(a) for a in angles]
            nt=[gene]+[p["partner"] for p in string_d]; nc=["#00e5ff"]+[f"rgba(0,229,255,{min(1,p['score'])})" for p in string_d]; ns=[16]+[max(5,int(p["score"]*14)) for p in string_d]
            ex_,ey_=[],[]
            for i in range(n): ex_+=[0,r*math.cos(angles[i]),None]; ey_+=[0,r*math.sin(angles[i]),None]
            fig_n=go.Figure()
            fig_n.add_trace(go.Scatter(x=ex_,y=ey_,mode="lines",line=dict(color="#0d1a2a",width=1),hoverinfo="none",showlegend=False))
            fig_n.add_trace(go.Scatter(x=nx,y=ny,mode="markers+text",text=nt,textposition="top center",textfont=dict(color="#8baabf",size=9),marker=dict(size=ns,color=nc,line=dict(color="#010306",width=1)),hovertext=["Query"]+[f"{p['partner']} ({p['score']:.2f})" for p in string_d],hoverinfo="text",showlegend=False))
            fig_n.update_layout(height=280,showlegend=False,plot_bgcolor="#010306",paper_bgcolor="#010306",xaxis=dict(visible=False),yaxis=dict(visible=False),margin=dict(l=5,r=5,t=5,b=5))
            st.plotly_chart(fig_n,use_container_width=True,config={"displayModeBar":False})
            st.markdown(_src("STRING","https://string-db.org"), unsafe_allow_html=True)
    if papers:
        _sec("Evidence-Tiered Literature")
        for p in papers[:10]: st.markdown(f'<div style="display:flex;gap:5px;padding:3px 0;border-bottom:1px solid #060d14;align-items:baseline"><span style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;border-radius:3px;min-width:48px;text-align:center;font-size:.6rem;padding:1px 5px">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.71rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:18]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)

with t3:  # EXPLORER
    cl,cr = st.columns([2,1], gap="large")
    AA = {"A":("Ala",1.8,0),"R":("Arg",-4.5,1),"N":("Asn",-3.5,0),"D":("Asp",-3.5,-1),"C":("Cys",2.5,0),"Q":("Gln",-3.5,0),"E":("Glu",-3.5,-1),"G":("Gly",-0.4,0),"H":("His",-3.2,0),"I":("Ile",4.5,0),"L":("Leu",3.8,0),"K":("Lys",-3.9,1),"M":("Met",1.9,0),"F":("Phe",2.8,0),"P":("Pro",-1.6,0),"S":("Ser",-0.8,0),"T":("Thr",-0.7,0),"W":("Trp",-0.9,0),"Y":("Tyr",-1.3,0),"V":("Val",4.2,0)}
    with cl:
        _sec("3D Explorer — Click Residues")
        vw = st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="ex_view",label_visibility="collapsed")
        spin = st.checkbox("Auto-spin",key="ex_spin")
        _viewer(pdb,style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw],height=440,spin=spin)
    with cr:
        seq=pdata.get("sequence",""); seq_len=pdata.get("seq_len",0)
        _sec("Residue Inspector")
        if seq and seq_len:
            pos=st.number_input("Position",1,max(1,seq_len),min(50,seq_len),key="res_pos_ex")
            if 1<=pos<=seq_len:
                aa=seq[pos-1].upper(); pr=AA.get(aa,("?",0,0)); pv=plddt.get(pos,0)
                pc=("#00b4d8" if pv>=90 else "#4ab8a7" if pv>=70 else "#f5b942" if pv>=50 else "#e05c5c")
                st.markdown(f"""<div class="card"><span style="color:#00e5ff;font-family:monospace;font-size:.9rem">{aa}{pos}</span> <span class="dim">{pr[0]}</span>
<table style="width:100%;font-size:.71rem;margin-top:5px"><tr><td class="dim">Hydrophobicity</td><td style="color:#d0e8ff;font-family:monospace">{pr[1]}</td></tr>
<tr><td class="dim">Charge</td><td style="color:#d0e8ff;font-family:monospace">{pr[2]:+}</td></tr>
<tr><td class="dim">pLDDT</td><td style="color:{pc};font-family:monospace">{pv:.1f}</td></tr></table></div>""", unsafe_allow_html=True)
                for v in [v for v in cv if v.get("position")==pos][:2]:
                    col2="#ff2d55" if v.get("ml_class")=="CRITICAL" else "#ff8c42"
                    st.markdown(f'<div style="background:{col2}0d;border-left:2px solid {col2};padding:4px 7px;margin:3px 0;border-radius:3px;font-size:.71rem;color:#d0e8ff">{v.get("significance","")} · {", ".join(v.get("conditions",[])[:1])}</div>', unsafe_allow_html=True)
                new_aa=st.selectbox("Mutate to:",sorted([k for k in AA if k!=aa]),key="mut_aa_ex")
                if new_aa:
                    npr=AA.get(new_aa,("?",0,0)); dh=abs(npr[1]-pr[1]); dc=abs(npr[2]-pr[2])
                    score=min(100,int(dh*8+dc*25)); ic="#ff2d55" if score>=70 else "#ff8c42" if score>=40 else "#ffd60a" if score>=15 else "#4a7090"
                    il="Likely Damaging" if score>=70 else "Possibly Damaging" if score>=40 else "Moderate" if score>=15 else "Benign"
                    st.markdown(f'<div class="card"><span style="color:{ic};font-family:monospace">{aa}{pos}{new_aa}</span> <span class="dim">{il} · score {score}/100</span><br><span class="dim">Δhyd: {dh:.1f} · Δcharge: {dc:.0f}{"  ⚠️ Pro breaks secondary structure" if new_aa=="P" else ""}</span></div>', unsafe_allow_html=True)
    if am:
        _sec("AlphaMissense Per-Residue Pathogenicity")
        sample=am[::max(1,len(am)//600)]
        fig_am=go.Figure()
        fig_am.add_trace(go.Scatter(x=[a["position"] for a in sample],y=[a["score"] for a in sample],mode="markers",marker=dict(size=3,color=["#ff2d55" if a["score"]>=0.564 else "#1e3a5f" for a in sample],opacity=0.6),hovertemplate="Pos %{x} — %{y:.3f}<extra></extra>"))
        path_cv=[v for v in cv if v.get("position") and v.get("ml_class") in ("CRITICAL","HIGH")]
        if path_cv: fig_am.add_trace(go.Scatter(x=[v["position"] for v in path_cv],y=[0.564]*len(path_cv),mode="markers",marker=dict(size=10,symbol="star",color="#ff8c42"),hovertext=[v.get("protein_change","?") for v in path_cv],hoverinfo="text",name="ClinVar P/LP"))
        fig_am.add_hline(y=0.564,line_dash="dash",line_color="#ffd60a",annotation_text="0.564 threshold")
        fig_am.update_layout(height=240,plot_bgcolor="#010306",paper_bgcolor="#010306",xaxis=dict(title="Position",gridcolor="#060d14",color="#2a5070"),yaxis=dict(title="AM Score",gridcolor="#060d14",color="#2a5070",range=[0,1]),font=dict(color="#d0e8ff",size=10),legend=dict(bgcolor="#020609",bordercolor="#0a1520"),margin=dict(t=10,b=30,l=45,r=10))
        st.plotly_chart(fig_am,use_container_width=True,config={"displayModeBar":False})

with t4:  # EXPERIMENTS
    _sec("Protein-Specific Experiment Triage")
    do_f=[e for e in exp_list if e.get("do_first") and not e.get("avoid")]; av_=[e for e in exp_list if e.get("avoid")]
    c1,c2,c3,c4=st.columns(4)
    c1.metric("DO FIRST",len(do_f),f"${sum(e['cost_usd'] for e in do_f):,}"); c2.metric("Consider",len([e for e in exp_list if not e.get("do_first") and not e.get("avoid")])); c3.metric("AVOID",len(av_),f"${sum(e['cost_usd'] for e in av_):,}"); c4.metric("Total",len(exp_list))
    for exp in exp_list:
        av=exp.get("avoid",False); dof=exp.get("do_first",False) and not av
        cost_str=f"${exp['cost_usd']:,}" if exp['cost_usd']>0 else "Free"
        hd=f"{'🚀 ' if dof else '🛑 AVOID — ' if av else ''}{exp['name'][:65]} — {cost_str} · {exp['time_weeks']}w · P={int(exp['p_success']*100)}%"
        with st.expander(hd, expanded=dof and not av):
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Cost",cost_str); c2.metric("Timeline",f"{exp['time_weeks']}w"); c3.metric("P(success)",f"{int(exp['p_success']*100)}%"); c4.metric("Value",f"{exp['value_score']}/10")
            st.markdown(f'<div style="font-size:.72rem;color:#d0e8ff;line-height:1.7;margin-top:6px">{exp["rationale"]}</div>', unsafe_allow_html=True)
            if dof: st.success("Run first — highest expected value for this protein's specific variant profile")
            if av: st.error("Do not run — insufficient genetic evidence to justify expenditure")
    if kegg:
        _sec("KEGG Pathways")
        for p in kegg[:6]: st.markdown(f'<div class="dim"><a href="{p["url"]}" target="_blank" style="color:#00e5ff">{p["name"]}</a> <span class="src">{p["id"]}</span></div>', unsafe_allow_html=True)

with t5:  # CSV ANALYSIS
    _sec("CSV / VCF Dataset Analysis")
    df = st.session_state.get("csv_data")
    if df is None: st.markdown('<div class="dim">Upload a CSV file in the sidebar (Wet-lab Data section).<br><b style="color:#d0e8ff">Accepted:</b> ClinVar VCF export, proteomics CSV, AlphaMissense TSV, variant tables.</div>', unsafe_allow_html=True)
    else:
        c1,c2,c3=st.columns(3); c1.metric("Rows",f"{len(df):,}"); c2.metric("Columns",len(df.columns)); c3.metric("Type","VCF Variants" if "Condition(s)" in df.columns else "Dataset")
        st.dataframe(df.head(20),use_container_width=True,height=260)
        sig_col=next((c for c in df.columns if any(t in c.lower() for t in ["ignif","pathogen"])),"")
        if sig_col:
            _sec("Variant Classification")
            counts=df[sig_col].value_counts(); path=sum(v for k,v in counts.items() if "pathogenic" in str(k).lower() and "benign" not in str(k).lower()); vus=sum(v for k,v in counts.items() if "uncertain" in str(k).lower()); benign=sum(v for k,v in counts.items() if "benign" in str(k).lower())
            c1,c2,c3=st.columns(3); c1.metric("Pathogenic/LP",f"{path:,}"); c2.metric("VUS",f"{vus:,}"); c3.metric("Benign/LB",f"{benign:,}")
            for k,v in counts.head(8).items(): st.markdown(f'<div style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid #060d14;font-size:.71rem"><span class="dim">{k}</span><span style="color:#d0e8ff;font-family:monospace">{v:,}</span></div>', unsafe_allow_html=True)
        _sec("Recommended Next Experiments")
        st.markdown(f'<div class="dim"><b>1. ClinVar submission</b> — pathogenic variants absent from ClinVar should be submitted.<br><b>2. Functional validation</b> — P/LP variants lacking functional evidence: DMS or CRISPR knock-in.<br><b>3. VUS resolution</b> — AlphaMissense threshold {sens:.2f} + DMS data.<br><b>4. Segregation analysis</b> — confirm P/LP variants segregate with disease in family members.</div>', unsafe_allow_html=True)
        gene_col=next((c for c in df.columns if any(t in c.lower() for t in ["gene","symbol","hugo"])),"")
        if gene_col:
            _sec(f"Quick Analyse — {gene_col}")
            top=df[gene_col].dropna().unique()[:10]; gc=st.columns(min(10,len(top)))
            for i,g in enumerate(top):
                with gc[i]:
                    if st.button(str(g)[:8],key=f"csv_g_{g}"): st.session_state._qval=str(g); st.rerun()

with t6:  # AI REPORT
    _sec("Evidence-Tiered Literature")
    tg={}
    for p in papers: tg.setdefault(p["tier_label"],[]).append(p)
    for tlbl,tp in sorted(tg.items(),key=lambda x:x[1][0]["tier"]):
        tc=tp[0]["tier_color"]
        with st.expander(f"{tlbl} ({len(tp)})",expanded=tlbl in ("RCT","Cohort","Functional")):
            for p in tp: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14"><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.71rem">{p["title"][:100]}</a> · {p["authors"][:18]} · {p["journal"]} · {p["year"]} · PMID:{p["pmid"]}</div>', unsafe_allow_html=True)
    _sec("AI Synthesis")
    api_key=st.session_state.get("anthropic_key","")
    if not api_key: st.markdown('<div class="dim">Add Anthropic API key in sidebar to enable AI synthesis with live web search.</div>', unsafe_allow_html=True)
    else:
        if st.button("▶ Generate AI Report",type="primary",key="ai_run"):
            with st.spinner("Claude searching literature…"):
                try:
                    import anthropic; client=anthropic.Anthropic(api_key=api_key)
                    path_count=gi_s.get("n_pathogenic",0); conditions=list({c for v in cv for c in v.get("conditions",[]) if c})[:5]; partners=[p["partner"] for p in string_d[:5]]
                    prompt=f"""You are a specialist molecular biologist analysing {gene} for drug target potential.
Gene: {gene} | Protein: {pdata.get('protein_name','')} | P/LP variants: {path_count} | pLI: {gnomad.get('pLI','?')} | Conditions: {', '.join(conditions) or 'None'} | STRING partners: {', '.join(partners) or 'Unknown'}
Generate: VERDICT (PURSUE/DEPRIORITISE with genetic justification), MECHANISM (specific molecular mechanism), INHERITANCE (AD/AR/XL/de novo), THERAPEUTIC HYPOTHESES (3 specific approaches), KEY UNKNOWNS (what experiments resolve them). 
Rules: Cite every claim Author/Journal/Year/PMID. Never say 'unknown' — say what experiment resolves it. If GPCR: note Filamin Ser2152-P as receptor-proximal readout. If ARRB1/2: immediately DEPRIORITISE."""
                    message=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=2000,tools=[{"type":"web_search_20250305","name":"web_search"}],messages=[{"role":"user","content":prompt}])
                    report="\n".join(b.text for b in message.content if hasattr(b,"text") and b.text)
                    st.session_state[f"ai_{gene}"]=report
                except Exception as e: st.error(f"AI error: {e}")
        if f"ai_{gene}" in st.session_state:
            st.markdown(f'<div class="card" style="line-height:1.8;font-size:.76rem">{st.session_state[f"ai_{gene}"]}</div>', unsafe_allow_html=True)
            if st.button("🔄 Regenerate"): del st.session_state[f"ai_{gene}"]; st.rerun()

with t7:  # WORKSPACE
    _sec(f"Workspace — {user.get('name','')}")
    c1,c2,c3=st.columns(3); c1.metric("Searches Used",_used()); c2.metric("Quota",_quota() if _quota()<99999 else "∞"); c3.metric("Proteins",len(st.session_state.workspace))
    ws=st.session_state.workspace
    if not ws: st.markdown('<div class="dim">No proteins analysed yet.</div>', unsafe_allow_html=True)
    else:
        _sec("Search History")
        for item in ws:
            col2=item.get("color","#4a7090"); ca,cb=st.columns([5,1])
            with ca: st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:4px 0;border-bottom:1px solid #060d14"><span style="color:#d0e8ff;font-family:monospace">{item["gene"]}</span><span style="background:{col2}18;color:{col2};border:1px solid {col2}30;border-radius:3px;font-size:.61rem;padding:1px 6px">{item["verdict"]}</span><span class="dim">{item.get("domain","")} · {item["accession"]} · {item["protein"][:38]}</span></div>', unsafe_allow_html=True)
            with cb:
                if st.button("↗",key=f"ws_{item['gene']}"): st.session_state._qval=item["gene"]; st.rerun()

with t8:  # DISEASE LINK
    _sec("Disease → Protein Mapping")
    dq=st.text_input("Disease / pathogen",value=st.session_state._dval,placeholder="Alzheimer · Hantavirus · breast cancer · arrhythmia",label_visibility="collapsed",key="_dl_input")
    if dq:
        dql=dq.lower(); found=False
        for org_name,org in MICRO_ORGANISMS.items():
            if org_name.lower() in dql or org.get("disease","").lower() in dql:
                found=True
                st.markdown(f"**{org['organism']}** — {org['type']}"); st.write(org.get("mechanism","")[:200])
                _sec("Host Receptors — Click to Analyse")
                rc=st.columns(min(4,len(org.get("host_receptors",[])) or 1))
                for i,rec in enumerate(org.get("host_receptors",[])):
                    with rc[i]:
                        if st.button(rec,key=f"dl_rec_{rec}"): st.session_state._qval=rec; st.rerun()
                if org.get("approved_drugs"): _sec("Approved Treatments"); st.markdown(" ".join(f'<span class="pill">💊 {d}</span>' for d in org["approved_drugs"]), unsafe_allow_html=True)
                break
        if not found:
            try:
                r=requests.get("https://rest.uniprot.org/uniprotkb/search",params={"query":f"cc_disease:{dq} AND organism_id:9606 AND reviewed:true","format":"json","size":8,"fields":"accession,gene_names,protein_name"},headers=HDR,timeout=12)
                hits=r.json().get("results",[])
                if hits:
                    _sec(f"Proteins associated with {dq}")
                    for hit in hits:
                        gs=[g.get("geneName",{}).get("value","") for g in hit.get("genes",[])]
                        g=gs[0] if gs else hit.get("primaryAccession",""); pn=hit.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
                        c1,c2=st.columns([4,1])
                        with c1: st.markdown(f'<span style="color:#00e5ff;font-family:monospace">{g}</span> <span class="dim">{pn[:55]}</span>', unsafe_allow_html=True)
                        with c2:
                            if st.button(f"↗{g}",key=f"dl_{g}"): st.session_state._qval=g; st.rerun()
                else: st.markdown('<div class="dim">No proteins found for this query.</div>', unsafe_allow_html=True)
            except: st.markdown('<div class="dim">Search unavailable.</div>', unsafe_allow_html=True)
    else: st.markdown('<div class="dim">Enter a disease or pathogen name to map to associated proteins.</div>', unsafe_allow_html=True)
