"""
Protellect — The Most Powerful Protein Triage Tool in Biology
Genetics-first. Reduces cost, time, and saves lives.
v5 — Complete fresh build.
"""
import streamlit as st
import streamlit.components.v1 as components
import hashlib, re, math, time, json, io
import numpy as np, pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="Protellect",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════
# GLOBAL STYLES  —  Inter font, safe selectors, no * rule
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body { background: #020609 !important; }
[data-testid="stAppViewContainer"] { background: #020609 !important; }
.block-container { padding: .3rem .8rem !important; max-width: 100%; }

/* Font — safe, targeted, never touch span (breaks icons) */
p, li, h1, h2, h3, h4, label,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] *,
[data-testid="stAlert"] *,
[data-testid="stExpander"] summary,
[data-testid="stTabs"] [data-baseweb="tab"],
.stButton > button,
[data-testid="stMarkdownContainer"] p {
    font-family: 'Inter', sans-serif !important;
}

/* Hide chrome */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"], header {
    display: none !important; visibility: hidden !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-thumb { background: #0f1e2d; border-radius: 2px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #040c14 !important;
    border-right: 1px solid #0f1e2d !important;
    min-width: 255px !important; max-width: 255px !important;
    display: block !important; transform: translateX(0) !important;
    visibility: visible !important;
}
[data-testid="stSidebar"] .block-container { padding: .35rem .55rem !important; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #040c14; border-radius: 7px; padding: 3px;
    gap: 2px; border: 1px solid #0f1e2d;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 5px; color: #2a4060; font-size: .68rem;
    font-weight: 500; padding: 4px 9px; min-height: 25px;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(0,212,255,.1) !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0,212,255,.2) !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #040c14; border: 1px solid #0f1e2d;
    border-radius: 6px; padding: 7px 10px;
}
[data-testid="stMetricValue"] {
    color: #00d4ff !important; font-size: .82rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #2a4060 !important; font-size: .56rem !important;
    text-transform: uppercase; letter-spacing: .05em;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #040c14 !important; border: 1px solid #0f1e2d !important;
    border-radius: 6px; margin: 2px 0;
}
[data-testid="stExpander"] summary {
    color: #3a5570 !important; font-size: .7rem !important;
}
[data-testid="stExpander"] summary:hover { color: #00d4ff !important; }

/* Inputs */
[data-testid="stTextInput"] input {
    background: #040c14 !important; border: 1px solid #0f1e2d !important;
    color: #b8d4e8 !important; border-radius: 4px !important;
    font-size: .74rem !important; padding: 4px 8px !important;
}
[data-testid="stTextInput"] input:focus { border-color: rgba(0,212,255,.4) !important; }
[data-testid="stTextArea"] textarea {
    background: #040c14 !important; border: 1px solid #0f1e2d !important;
    color: #b8d4e8 !important; border-radius: 4px !important; font-size: .7rem !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #040c14 !important; border-color: #0f1e2d !important;
    font-size: .7rem !important; color: #b8d4e8 !important;
}
[data-testid="stFileUploader"] {
    border: 1px dashed #0f1e2d !important; border-radius: 4px !important;
    background: #040c14 !important;
}

/* Default buttons */
.stButton > button {
    background: #040c14; border: 1px solid #0f1e2d; color: #5a7590;
    border-radius: 4px; padding: 4px 10px; min-height: 28px;
    transition: all .15s; font-size: .7rem; font-family: 'Inter', sans-serif !important;
}
.stButton > button:hover {
    background: #0a1a28; border-color: rgba(0,212,255,.25); color: #00d4ff;
}
.stButton > button[kind="primary"] {
    background: rgba(0,212,255,.08) !important;
    border-color: rgba(0,212,255,.35) !important;
    color: #00d4ff !important; font-weight: 600 !important;
}

/* DOMAIN CARD BUTTONS — the critical part */
[data-testid="stHorizontalBlock"] .stButton > button {
    white-space: pre-line !important;
    height: auto !important;
    min-height: 100px !important;
    text-align: left !important;
    background: #040c14 !important;
    border: 1px solid #0f2035 !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    font-size: .82rem !important;
    line-height: 1.55 !important;
    color: #8ab0c8 !important;
    font-family: 'Inter', sans-serif !important;
    width: 100% !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
    border-color: rgba(0,212,255,.35) !important;
    background: rgba(0,212,255,.04) !important;
    color: #00d4ff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(0,212,255,.08) !important;
}

/* Utility classes */
.sec {
    font-size: .7rem; font-weight: 600; color: #00d4ff;
    border-bottom: 1px solid #0f1e2d; padding-bottom: 4px; margin: 10px 0 7px;
    font-family: 'Inter', sans-serif;
}
.card {
    background: #040c14; border: 1px solid #0f1e2d;
    border-radius: 6px; padding: 9px 12px; margin: 3px 0;
}
.pill {
    display: inline-block; background: rgba(0,212,255,.06); color: #00d4ff;
    border: 1px solid rgba(0,212,255,.15); border-radius: 9px;
    padding: 1px 7px; font-size: .61rem; margin: 2px; text-decoration: none;
    font-family: 'Inter', sans-serif;
}
.dim { color: #2a4060; font-size: .66rem; font-family: 'Inter', sans-serif; }
.mono { font-family: 'JetBrains Mono', monospace !important; }
.badge-c { background: rgba(255,45,85,.12); color: #ff2d55; border: 1px solid rgba(255,45,85,.3); border-radius: 3px; padding: 1px 6px; font-size: .6rem; font-weight: 700; white-space: nowrap; }
.badge-h { background: rgba(255,140,66,.1); color: #ff8c42; border: 1px solid rgba(255,140,66,.3); border-radius: 3px; padding: 1px 6px; font-size: .6rem; font-weight: 700; white-space: nowrap; }
.badge-m { background: rgba(255,210,10,.07); color: #ffd20a; border: 1px solid rgba(255,210,10,.25); border-radius: 3px; padding: 1px 6px; font-size: .6rem; font-weight: 700; white-space: nowrap; }
.badge-n { background: rgba(42,64,96,.2); color: #3a5570; border: 1px solid #0f1e2d; border-radius: 3px; padding: 1px 6px; font-size: .6rem; font-weight: 700; white-space: nowrap; }
</style>
""", unsafe_allow_html=True)


def _sec(t, c="#00d4ff"):
    st.markdown(f'<div class="sec" style="color:{c}">{t}</div>', unsafe_allow_html=True)

def _h(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _badge(cls):
    m = {"CRITICAL": '<span class="badge-c">CRITICAL</span>',
         "HIGH": '<span class="badge-h">HIGH</span>',
         "MODERATE": '<span class="badge-m">MODERATE</span>',
         "LOW": '<span class="badge-n">NEUTRAL</span>'}
    return m.get(cls, '<span class="badge-n">NEUTRAL</span>')


# ══════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════
ACCOUNTS = {
    "protellect@gmail.com": {"hash": _h("dev@protellect"), "tier": "enterprise", "name": "Dr Smith", "quota": 999999, "dev": True},
    "demo@protellect.io":   {"hash": _h("demo2025"),       "tier": "free",       "name": "Demo User", "quota": 5,      "dev": False},
}

if not st.session_state.get("auth_user"):
    # Login page
    components.html("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter',sans-serif; }
    body { background:#020609; display:flex; align-items:center; justify-content:center; min-height:98vh; overflow:hidden; }
    #cv { position:fixed; inset:0; z-index:0; pointer-events:none; }
    .hero { position:relative; z-index:1; text-align:center; }
    .logo { font-size:2rem; font-weight:700;
        background:linear-gradient(90deg,#00d4ff,#6366f1,#f43f5e);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-size:200%; animation:sh 5s linear infinite; }
    .sub { color:#0f2035; font-size:.68rem; letter-spacing:.14em; text-transform:uppercase; margin:6px 0 4px; }
    .tag { color:#1a3040; font-size:.78rem; max-width:340px; line-height:1.6; }
    @keyframes sh { 0%{background-position:0 50%} 100%{background-position:200% 50%} }
    </style>
    <canvas id="cv"></canvas>
    <div class="hero">
      <div class="logo">🔬 Protellect</div>
      <div class="sub">Genetics-First Protein Intelligence</div>
      <div class="tag">The most powerful triage tool in biology.<br>Reduce cost. Save time. Improve outcomes.</div>
    </div>
    <script>
    const c=document.getElementById('cv'),x=c.getContext('2d');
    c.width=innerWidth;c.height=innerHeight;
    const p=Array.from({length:55},()=>({
      x:Math.random()*c.width,y:Math.random()*c.height,
      vx:(Math.random()-.5)*.25,vy:(Math.random()-.5)*.25,
      r:Math.random()*1.2+.4,
      col:`rgba(${Math.random()>.5?'0,212,255':'99,102,241'},.2)`
    }));
    function dr(){
      x.clearRect(0,0,c.width,c.height);
      p.forEach(o=>{o.x+=o.vx;o.y+=o.vy;
        if(o.x<0||o.x>c.width)o.vx*=-1;
        if(o.y<0||o.y>c.height)o.vy*=-1;
        x.beginPath();x.arc(o.x,o.y,o.r,0,Math.PI*2);
        x.fillStyle=o.col;x.fill();
      });
      p.forEach((a,i)=>p.slice(i+1).forEach(b=>{
        const d=Math.hypot(a.x-b.x,a.y-b.y);
        if(d<100){x.beginPath();x.moveTo(a.x,a.y);x.lineTo(b.x,b.y);
          x.strokeStyle=`rgba(0,212,255,${.04*(1-d/100)})`;x.lineWidth=.5;x.stroke();}
      }));
      requestAnimationFrame(dr);
    }
    dr();
    </script>
    """, height=240)

    _, cc, _ = st.columns([1, 1.2, 1])
    with cc:
        tl, td = st.tabs(["Sign In", "Try Demo"])
        with tl:
            em = st.text_input("Email", placeholder="you@example.com", key="li_em")
            pw = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign In →", type="primary", use_container_width=True, key="li_btn"):
                ac = ACCOUNTS.get(em.strip().lower())
                if ac and ac["hash"] == _h(pw):
                    st.session_state.auth_user = {"email": em, "name": ac["name"], "tier": ac["tier"], "quota": ac["quota"], "dev": ac["dev"]}
                    st.session_state.searches_used = 0
                    st.session_state.workspace = []
                    st.session_state.onboarded = False
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        with td:
            dn = st.text_input("Name", placeholder="Dr. Smith", key="td_n")
            de = st.text_input("Email", placeholder="you@lab.edu", key="td_e")
            if st.button("Start Free Trial →", type="primary", use_container_width=True, key="td_btn"):
                if dn and de:
                    st.session_state.auth_user = {"email": de, "name": dn, "tier": "free", "quota": 5, "dev": False}
                    st.session_state.searches_used = 0
                    st.session_state.workspace = []
                    st.session_state.onboarded = False
                    st.rerun()
                else:
                    st.warning("Please enter your name and email.")
        st.markdown("""
        <div style='display:flex;gap:6px;margin-top:14px'>
          <div style='flex:1;background:#040c14;border:1px solid #0f1e2d;border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#2a4060;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif'>FREE</div>
            <div style='color:#b8d4e8;font-size:.95rem;font-weight:700;font-family:Inter,sans-serif'>$0</div>
            <div style='color:#2a4060;font-size:.62rem;font-family:Inter,sans-serif'>5 searches</div>
          </div>
          <div style='flex:1;background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#00d4ff;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif'>PRO</div>
            <div style='color:#b8d4e8;font-size:.95rem;font-weight:700;font-family:Inter,sans-serif'>$49/mo</div>
            <div style='color:#2a4060;font-size:.62rem;font-family:Inter,sans-serif'>200 searches</div>
          </div>
          <div style='flex:1;background:rgba(99,102,241,.04);border:1px solid rgba(99,102,241,.15);border-radius:8px;padding:10px;text-align:center'>
            <div style='color:#6366f1;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif'>ENTERPRISE</div>
            <div style='color:#b8d4e8;font-size:.95rem;font-weight:700;font-family:Inter,sans-serif'>$299/mo</div>
            <div style='color:#2a4060;font-size:.62rem;font-family:Inter,sans-serif'>Unlimited</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════
user = st.session_state.auth_user
for k, v in {
    "searches_used": 0, "workspace": [], "protein_data_cache": {},
    "current_protein": None, "domain": None, "onboarded": False,
    "lab_profile": {}, "research_goal": "Drug target identification",
    "anthropic_key": "", "sensitivity": 0.70,
    "csv_data": None, "wet_lab_text": "",
    "_qval": "", "_dval": "", "_trig": False, "_dtrig": False,
    "show_tutorial": True,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════
HDR = {"User-Agent": "Protellect/5.0 (protellect@gmail.com)"}

DOMAIN_META = {
    "Neuroscience": {
        "icon": "🧠", "color": "#6366f1",
        "tags": "Alzheimer's · Parkinson's · ALS · Epilepsy · BBB · Neurodegeneration",
        "desc": "Neural receptor biology, synaptopathies, BBB penetrance scoring, neurodegeneration pathway analysis.",
    },
    "Cancer Biology": {
        "icon": "🎗", "color": "#f43f5e",
        "tags": "Oncogenes · Tumour Suppressors · Somatic Hotspots · Founder Mutations · cfDNA",
        "desc": "Somatic mutation triage, cancer driver vs passenger, metastasis, founder mutation analysis.",
    },
    "Pharmaceuticals": {
        "icon": "💊", "color": "#00d4ff",
        "tags": "GPCR Targets · Filamin Ser2152-P · Tractability · HTS · Clinical Trials",
        "desc": "GPCR piggyback analysis, Filamin IP assay, druggability scoring, clinical pipeline context.",
    },
    "Microbiome": {
        "icon": "🦠", "color": "#22c55e",
        "tags": "Taxonomy · BGC · Pathobionts · Host-Microbe · SCFA · Curli",
        "desc": "Taxonomic intelligence, biosynthetic gene clusters, host-receptor mapping, pathway annotation.",
    },
    "Molecular Biology": {
        "icon": "⚛️", "color": "#f97316",
        "tags": "Phosphorylation · Kinase · AlphaFold · STRING · PTMs · Structural Domains",
        "desc": "Phosphorylation biology, AlphaMissense per-residue, 3D structure, interaction networks.",
    },
}

DOMAIN_EXAMPLES = {
    "Neuroscience": ["APP", "SNCA", "MAPT", "LRRK2", "TARDBP", "HTT", "GBA", "SOD1"],
    "Cancer Biology": ["TP53", "KRAS", "BRCA1", "EGFR", "MYC", "PTEN", "BRAF", "RB1"],
    "Pharmaceuticals": ["ADRB2", "ADRB1", "AGTR1", "DRD2", "FLNA", "GRK2", "OPRM1", "CHRM2"],
    "Microbiome": [],
    "Molecular Biology": ["FLNA", "MAPK1", "AKT1", "SRC", "CDK2", "EGFR", "JAK2", "PIK3CA"],
}

VERDICT_COLORS = {
    "DISEASE-CRITICAL": "#ff2d55",
    "DISEASE-ASSOCIATED": "#ff8c42",
    "MODERATE": "#ffd20a",
    "VERY LOW": "#2a4060",
    "NO DISEASE VARIANTS": "#1a2d3a",
}

NAME_MAP = {
    "filamin a": "FLNA", "filamin-a": "FLNA", "filamin": "FLNA",
    "filamin b": "FLNB", "filamin c": "FLNC",
    "beta arrestin 2": "ARRB2", "beta-arrestin-2": "ARRB2", "arrestin 2": "ARRB2",
    "beta arrestin 1": "ARRB1",
    "p53": "TP53", "alpha synuclein": "SNCA", "alpha-synuclein": "SNCA",
    "synuclein": "SNCA", "tau": "MAPT", "tau protein": "MAPT",
    "amyloid precursor": "APP", "beta 2 adrenergic": "ADRB2", "b2ar": "ADRB2",
    "trpc": "TRPC3", "trpc3": "TRPC3", "trpc6": "TRPC6",
    "grk2": "GRK2", "akt": "AKT1", "brca": "BRCA1",
    "egfr": "EGFR", "huntingtin": "HTT", "sod1": "SOD1", "tdp-43": "TARDBP",
}


# ══════════════════════════════════════════════════════════
# ONBOARDING QUESTIONNAIRE
# ══════════════════════════════════════════════════════════
if not st.session_state.onboarded:
    st.markdown(f"""
    <div style="max-width:580px;margin:28px auto;text-align:center">
      <div style="font-size:1.5rem;font-weight:700;color:#00d4ff;font-family:Inter,sans-serif;margin-bottom:4px">
        Welcome, {user.get('name','').split()[0]} 👋
      </div>
      <div style="color:#2a4060;font-size:.78rem;font-family:Inter,sans-serif;line-height:1.6">
        Tell us about your lab so Protellect can tailor every analysis to your needs.
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, qc, _ = st.columns([1, 2, 1])
    with qc:
        lab_type = st.selectbox("What type of lab do you run?",
            ["Academic Research", "Pharmaceutical / Biotech", "Clinical / Hospital",
             "CRO / Consultancy", "Startup", "Other"])
        org_name = st.text_input("Organisation", placeholder="UCSD, Pfizer, your startup")
        focus = st.multiselect("Primary research focus",
            ["Drug target ID", "Disease mechanism", "Cancer biology", "Neuroscience",
             "GPCR biology", "Structural biology", "Genomics", "Microbiome",
             "Biochemistry", "Clinical translation"])
        models = st.multiselect("Model systems",
            ["Cell lines (HEK293, HeLa)", "iPSC-derived", "Primary cells",
             "Mouse models", "Zebrafish", "Patient samples", "Organoids", "In silico"])
        budget = st.selectbox("Typical experiment budget",
            ["< $10K", "$10K–$100K", "$100K–$500K", "> $500K", "Variable"])
        goal = st.selectbox("Primary goal",
            ["Drug target identification", "Disease mechanism", "Variant pathogenicity",
             "Therapeutic hypothesis", "Biomarker discovery", "Academic research"])
        st.session_state.research_goal = goal
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Enter Protellect →", type="primary", use_container_width=True):
            st.session_state.lab_profile = {
                "lab_type": lab_type, "org": org_name,
                "focus": focus, "models": models,
                "budget": budget, "goal": goal,
            }
            st.session_state.onboarded = True
            st.rerun()
    st.stop()


# ══════════════════════════════════════════════════════════
# DOMAIN SELECTION  —  pure Streamlit buttons + CSS
# ══════════════════════════════════════════════════════════
if not st.session_state.domain:
    # Animated hero (decoration only)
    components.html("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter',sans-serif; }
    body { background:#020609; display:flex; align-items:center; justify-content:center;
           height:100vh; overflow:hidden; }
    #cv { position:fixed; inset:0; z-index:0; pointer-events:none; }
    .hero { position:relative; z-index:1; text-align:center; }
    .logo { font-size:2rem; font-weight:700;
        background:linear-gradient(90deg,#00d4ff,#6366f1,#f43f5e);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-size:200%; animation:sh 5s linear infinite; }
    .sub { color:#0f2035; font-size:.68rem; letter-spacing:.14em; text-transform:uppercase; margin:5px 0 3px; }
    .tag { color:#1a3040; font-size:.76rem; margin-bottom:0; }
    @keyframes sh { 0%{background-position:0 50%} 100%{background-position:200% 50%} }
    </style>
    <canvas id="cv"></canvas>
    <div class="hero">
      <div class="logo">🔬 Protellect</div>
      <div class="sub">Genetics-First Protein Intelligence</div>
      <div class="tag">Select your research domain</div>
    </div>
    <script>
    const c=document.getElementById('cv'),x=c.getContext('2d');
    c.width=innerWidth; c.height=innerHeight;
    const p=Array.from({length:50},()=>({
      x:Math.random()*c.width, y:Math.random()*c.height,
      vx:(Math.random()-.5)*.22, vy:(Math.random()-.5)*.22,
      r:Math.random()*1.3+.4,
      col:`rgba(${Math.random()>.5?'0,212,255':'99,102,241'},.18)`
    }));
    function dr(){
      x.clearRect(0,0,c.width,c.height);
      p.forEach(o=>{o.x+=o.vx;o.y+=o.vy;
        if(o.x<0||o.x>c.width)o.vx*=-1;
        if(o.y<0||o.y>c.height)o.vy*=-1;
        x.beginPath();x.arc(o.x,o.y,o.r,0,Math.PI*2);
        x.fillStyle=o.col;x.fill();});
      p.forEach((a,i)=>p.slice(i+1).forEach(b=>{
        const d=Math.hypot(a.x-b.x,a.y-b.y);
        if(d<90){x.beginPath();x.moveTo(a.x,a.y);x.lineTo(b.x,b.y);
          x.strokeStyle=`rgba(0,212,255,${.04*(1-d/90)})`;x.lineWidth=.5;x.stroke();}
      }));
      requestAnimationFrame(dr);
    }
    dr();
    </script>
    """, height=185, scrolling=False)

    # Domain cards as pure Streamlit buttons (3 + 2 layout)
    r1c1, r1c2, r1c3 = st.columns(3)
    dom_list = list(DOMAIN_META.items())

    def _dom_btn_text(d, m):
        return f"{m['icon']}  {d}\n{m['tags']}"

    with r1c1:
        if st.button(_dom_btn_text(*dom_list[0]), key="dl_0", use_container_width=True):
            st.session_state.domain = dom_list[0][0]; st.rerun()
    with r1c2:
        if st.button(_dom_btn_text(*dom_list[1]), key="dl_1", use_container_width=True):
            st.session_state.domain = dom_list[1][0]; st.rerun()
    with r1c3:
        if st.button(_dom_btn_text(*dom_list[2]), key="dl_2", use_container_width=True):
            st.session_state.domain = dom_list[2][0]; st.rerun()

    _, r2c1, r2c2, _ = st.columns([.5, 1, 1, .5])
    with r2c1:
        if st.button(_dom_btn_text(*dom_list[3]), key="dl_3", use_container_width=True):
            st.session_state.domain = dom_list[3][0]; st.rerun()
    with r2c2:
        if st.button(_dom_btn_text(*dom_list[4]), key="dl_4", use_container_width=True):
            st.session_state.domain = dom_list[4][0]; st.rerun()

    st.markdown(
        '<div style="text-align:center;color:#0d1a24;font-size:.61rem;font-style:italic;'
        'margin-top:10px;font-family:Inter,sans-serif">'
        'The only platform that tells you which proteins to abandon before you spend the money.</div>',
        unsafe_allow_html=True
    )
    st.stop()


# ══════════════════════════════════════════════════════════
# TUTORIAL POPUP  —  rendered as a Streamlit container
# ══════════════════════════════════════════════════════════
domain = st.session_state.domain
meta = DOMAIN_META.get(domain, {})

if st.session_state.show_tutorial:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#040c14,#071220);border:1.5px solid rgba(0,212,255,.3);
         border-radius:12px;padding:22px 26px;margin-bottom:12px;position:relative">
      <div style="font-size:.9rem;font-weight:700;color:#00d4ff;font-family:Inter,sans-serif;margin-bottom:12px">
        🔬 Welcome to Protellect — Quick Start Guide
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
        <div style="background:#020609;border:1px solid #0f1e2d;border-radius:7px;padding:11px">
          <div style="color:#00d4ff;font-size:.68rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">① Search a protein</div>
          <div style="color:#2a4060;font-size:.67rem;line-height:1.65;font-family:Inter,sans-serif">Type any gene symbol (FLNA, TP53) or common name (filamin A, p53) in the sidebar. Hit Analyse Protein.</div>
        </div>
        <div style="background:#020609;border:1px solid #0f1e2d;border-radius:7px;padding:11px">
          <div style="color:#00d4ff;font-size:.68rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">② Read the verdict bar</div>
          <div style="color:#2a4060;font-size:.67rem;line-height:1.65;font-family:Inter,sans-serif">DISEASE-CRITICAL (red) = pursue. NO DISEASE VARIANTS (grey) = deprioritise. Driven by ClinVar human genetic data.</div>
        </div>
        <div style="background:#020609;border:1px solid #0f1e2d;border-radius:7px;padding:11px">
          <div style="color:#00d4ff;font-size:.68rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">③ Seven tabs</div>
          <div style="color:#2a4060;font-size:.67rem;line-height:1.65;font-family:Inter,sans-serif">Overview → Triage → Protein Explorer → Experiments → Therapeutic Targets → AI Report → Workspace (Excel download).</div>
        </div>
        <div style="background:#020609;border:1px solid #0f1e2d;border-radius:7px;padding:11px">
          <div style="color:#00d4ff;font-size:.68rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">④ Try these first</div>
          <div style="color:#2a4060;font-size:.67rem;line-height:1.65;font-family:Inter,sans-serif"><b style="color:#ff2d55">FLNA</b> — DISEASE-CRITICAL, 1000+ variants. <b style="color:#ff8c42">TP53</b> — Cancer archetype. <b style="color:#00d4ff">ADRB2</b> — GPCR Filamin IP target.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("✕  Got it — enter the workspace", key="close_tut"):
        st.session_state.show_tutorial = False
        st.rerun()
    st.stop()


# ══════════════════════════════════════════════════════════
# API FETCHERS
# ══════════════════════════════════════════════════════════
@st.cache_data(ttl=86400, show_spinner=False)
def _uniprot(raw_q):
    q = re.sub(r"['\"\(\)]", "", raw_q).strip()
    def _get(acc):
        r = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc}.json", headers=HDR, timeout=20)
        r.raise_for_status(); return r.json()
    try:
        for qs in [
            f"gene:{q} AND organism_id:9606 AND reviewed:true",
            f"protein_name:{q} AND organism_id:9606 AND reviewed:true",
            f"({q}) AND organism_id:9606 AND reviewed:true",
        ]:
            r = requests.get("https://rest.uniprot.org/uniprotkb/search",
                params={"query": qs, "format": "json", "size": 1}, headers=HDR, timeout=15)
            res = r.json().get("results", [])
            if res: return _get(res[0]["primaryAccession"])
        return {}
    except: return {}


def _parse(e):
    if not e: return {}
    seq = e.get("sequence", {}).get("value", "")
    genes = [g.get("geneName", {}).get("value", "") for g in e.get("genes", []) if g.get("geneName", {}).get("value")]
    diseases, functions, subcell, doms, ptms, tissues, binding, phospho, uni_v = [], [], [], [], [], [], [], [], []
    for f in e.get("features", []):
        ft = f.get("type", ""); loc = f.get("location", {})
        pos = loc.get("start", {}).get("value", 0)
        orig = f.get("alternativeSequence", {}).get("originalSequence", "")
        alts = f.get("alternativeSequence", {}).get("alternativeSequences", [])
        alt = alts[0] if alts else "?"
        desc = f.get("description", "")
        if ft == "NATURAL_VARIANT" and pos:
            is_d = any(k in desc.lower() for k in ["disease", "in patient", "pathogenic", "associated", "syndrome"])
            if is_d:
                cls = "CRITICAL" if any(k in desc.lower() for k in ["disease", "pathogenic"]) else "HIGH"
                uni_v.append({"id": f.get("ftId", f"U{pos}"), "title": f"{orig}{pos}{alt} — {desc[:60]}", "significance": "Pathogenic" if cls == "CRITICAL" else "Likely pathogenic", "ml_class": cls, "protein_change": f"{orig}{pos}{alt}", "position": pos, "conditions": [desc[:60]], "stars": 2, "source": "UniProt", "url": f"https://www.uniprot.org/uniprotkb/{e.get('primaryAccession','')}/entry"})
        elif ft in ("DOMAIN", "REGION", "MOTIF", "DNA_BIND", "ACT_SITE", "BINDING", "METAL", "CARBOHYD"):
            en = loc.get("end", {}).get("value", "?")
            s_p = loc.get("start", {}).get("value", "?")
            doms.append({"type": ft, "name": desc or ft, "start": s_p, "end": en})
            if ft in ("BINDING", "ACT_SITE", "METAL", "DNA_BIND"):
                binding.append({"type": ft, "name": desc or ft, "start": s_p, "end": en})
        elif ft == "MOD_RES" and "phospho" in desc.lower():
            phospho.append({"position": pos, "name": desc})
    for c in e.get("comments", []):
        ct = c.get("commentType", "")
        if ct == "DISEASE":
            d = c.get("disease", {})
            nm = d.get("name") or d.get("diseaseName") or "Unnamed disease"
            desc_t = d.get("description", "")[:220]
            txt = (nm + desc_t).lower()
            som = any(k in txt for k in ["cancer", "tumor", "tumour", "carcinoma", "sarcoma", "lymphoma", "leukemia", "leukaemia", "somatic"])
            diseases.append({"name": nm, "desc": desc_t, "inheritance": "Somatic" if som else "Germline", "omim": d.get("diseaseAccession", "")})
        elif ct == "FUNCTION":
            for t in c.get("texts", []): functions.append(t.get("value", "")[:400])
        elif ct == "SUBCELLULAR LOCATION":
            for l in c.get("subcellularLocations", []): subcell.append(l.get("location", {}).get("value", ""))
        elif ct == "PTM":
            for t in c.get("texts", []): ptms.append(t.get("value", "")[:200])
        elif ct == "TISSUE SPECIFICITY":
            for t in c.get("texts", []): tissues.append(t.get("value", "")[:200])
    kws = [k.get("name", "") for k in e.get("keywords", [])]; kl = " ".join(kws).lower()
    org = e.get("organism", {}); taxid = org.get("taxonId", 0)
    return {
        "accession": e.get("primaryAccession", ""), "gene": genes[0] if genes else "",
        "protein_name": e.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
        "organism": org.get("scientificName", ""), "taxon_id": taxid, "is_human": taxid == 9606,
        "sequence": seq, "seq_len": len(seq), "diseases": diseases, "functions": functions,
        "subcellular": list(set(subcell)), "domains": doms, "ptms": ptms, "tissues": tissues,
        "keywords": kws, "is_gpcr": any(x in kl for x in ["g protein-coupled", "gpcr", "seven-transmembrane"]),
        "is_kinase": any(x in kl for x in ["kinase", "phosphotransferase"]),
        "is_phosphatase": "phosphatase" in kl,
        "mw_kda": round(len(seq) * 110 / 1000, 1),
        "uni_variants": uni_v, "binding_sites": binding, "phospho_sites": phospho,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _clinvar(gene, mx=100):
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "clinvar", "term": f"{gene}[gene] AND homo sapiens[organism]", "retmax": mx, "retmode": "json"},
            headers=HDR, timeout=20)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        time.sleep(0.4)
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "clinvar", "id": ",".join(ids[:mx]), "retmode": "json"}, headers=HDR, timeout=25)
        res = r2.json().get("result", {}); out = []
        for uid in res.get("uids", []):
            v = res.get(uid, {}); sig = v.get("clinical_significance", {}).get("description", "Unknown"); sl = sig.lower()
            cls = ("CRITICAL" if ("pathogenic" in sl and "likely" not in sl)
                   else "HIGH" if "likely pathogenic" in sl
                   else "MODERATE" if "uncertain" in sl else "LOW")
            pc = v.get("protein_change", ""); pos = 0
            m = re.search(r'(\d+)', pc)
            if m: pos = int(m.group(1))
            stars = {"no assertion": 0, "criteria provided, single": 1, "criteria provided, multiple": 2, "reviewed by expert": 4}.get((v.get("review_status", "") or "").lower()[:30], 0)
            out.append({"id": uid, "title": v.get("title", ""), "significance": sig, "ml_class": cls, "protein_change": pc, "position": pos, "conditions": [c.get("trait_name", "") for c in v.get("trait_set", [])], "stars": stars, "source": "ClinVar", "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"})
        return sorted(out, key=lambda x: x["ml_class"] == "CRITICAL", reverse=True)
    except: return []


@st.cache_data(ttl=604800, show_spinner=False)
def _alphafold(acc):
    acc_u = acc.upper()
    for url in [
        f"https://alphafold.ebi.ac.uk/files/AF-{acc_u}-F1-model_v4.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc_u}-F1-model_v3.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc_u}-F2-model_v4.pdb",
    ]:
        try:
            r = requests.get(url, headers=HDR, timeout=25)
            if r.status_code == 200 and "ATOM" in r.text[:100]:
                return r.text
        except: continue
    return ""


def _plddt(pdb):
    d = {}
    for line in (pdb or "").splitlines():
        if line.startswith("ATOM"):
            try: ri = int(line[22:26].strip()); b = float(line[60:66].strip()); d.setdefault(ri, b)
            except: pass
    return d


@st.cache_data(ttl=604800, show_spinner=False)
def _alphamissense(acc):
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{acc.upper()}-F1-aa-substitutions.csv", headers=HDR, timeout=25)
        if r.status_code != 200: return []
        out = []
        for line in r.text.strip().splitlines()[1:]:
            p = line.split(",")
            if len(p) >= 4:
                try: out.append({"position": int(p[0]), "ref": p[1], "alt": p[2], "score": float(p[3]), "class": "pathogenic" if float(p[3]) >= 0.564 else "benign"})
                except: pass
        return out
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _gnomad(gene):
    q = 'query G($g:String!){gene(gene_symbol:$g,reference_genome:GRCh38){gnomad_constraint{pLI lof{oe}missense{oe}}}}'
    try:
        r = requests.post("https://gnomad.broadinstitute.org/api",
            json={"query": q, "variables": {"g": gene}},
            headers={**HDR, "Content-Type": "application/json"}, timeout=20)
        c = (r.json().get("data", {}).get("gene", {}) or {}).get("gnomad_constraint", {}) or {}
        pLI = c.get("pLI"); loe = (c.get("lof", {}) or {}).get("oe"); moe = (c.get("missense", {}) or {}).get("oe")
        return {"pLI": round(float(pLI), 3) if pLI else None, "lof_oe": round(float(loe), 3) if loe else None, "missense_oe": round(float(moe), 3) if moe else None, "essential": float(pLI) > 0.9 if pLI else False}
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _string(gene, lim=20):
    try:
        r = requests.get("https://string-db.org/api/json/get_string_ids",
            params={"identifiers": gene, "species": 9606, "limit": 1, "caller_identity": "protellect"},
            headers=HDR, timeout=12)
        d = r.json()
        if not d: return []
        sid = d[0].get("stringId", "")
        r2 = requests.get("https://string-db.org/api/json/interaction_partners",
            params={"identifiers": sid, "species": 9606, "limit": lim, "required_score": 700, "caller_identity": "protellect"},
            headers=HDR, timeout=15)
        return [{"partner": i.get("preferredName_B", ""), "score": round(i.get("score", 0), 3), "experimental": round(i.get("escore", 0), 3)} for i in r2.json()]
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _opentargets(gene):
    try:
        r = requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene", headers=HDR, timeout=10)
        hits = r.json().get("hits", [])
        eid = (hits[0].get("ensembl", {}).get("gene", "") if hits else "")
        if isinstance(eid, list): eid = eid[0]
        if not eid: return {}
        q = 'query O($id:String!){target(ensemblId:$id){tractability{smallMolecule{value}antibody{value}}knownDrugs{count rows{drug{name}phase status}}}}'
        r2 = requests.post("https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": q, "variables": {"id": eid}},
            headers={**HDR, "Content-Type": "application/json"}, timeout=20)
        tgt = (r2.json().get("data", {}).get("target", {}) or {})
        tr = tgt.get("tractability", {}) or {}; kd = tgt.get("knownDrugs", {}) or {}
        return {
            "sm_tractable": any((t or {}).get("value") for t in (tr.get("smallMolecule") or [{}])),
            "ab_tractable": any((t or {}).get("value") for t in (tr.get("antibody") or [{}])),
            "known_drugs_count": kd.get("count", 0),
            "known_drugs": [(r.get("drug", {}) or {}).get("name", "") for r in (kd.get("rows") or [])[:8]],
        }
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _gtex(gene):
    try:
        r = requests.get("https://gtexportal.org/api/v2/expression/medianGeneExpression",
            params={"geneId": gene, "datasetId": "gtex_v8", "format": "json"}, headers=HDR, timeout=20)
        return {i.get("tissueSiteDetailId", "").replace("_", " "): i.get("median", 0) for i in r.json().get("medianGeneExpression", [])}
    except: return {}


@st.cache_data(ttl=86400, show_spinner=False)
def _pubmed(gene, n=30):
    qs = [
        f"{gene}[gene] pathogenic variant 2020:2025[pdat]",
        f"{gene} functional assay CRISPR 2019:2025[pdat]",
        f"{gene} therapy drug 2020:2025[pdat]",
        f"{gene} structure cryo-em alphafold 2018:2025[pdat]",
        f"{gene} disease mechanism 2018:2025[pdat]",
    ]
    all_p = []; seen = set()
    TMAP = {1: "#00d4ff", 2: "#22c55e", 3: "#6366f1", 4: "#f97316", 5: "#fbbf24", 6: "#64748b", 8: "#475569"}
    LMAP = {1: "RCT", 2: "Cohort", 3: "Functional", 4: "Structural", 5: "Animal", 6: "Computational", 8: "Review"}
    def _tier(t):
        tl = t.lower()
        if any(k in tl for k in ["randomis", "randomiz", "phase iii"]): return 1
        if any(k in tl for k in ["cohort", "prospective"]): return 2
        if any(k in tl for k in ["crispr", "knock-in", "functional", "assay"]): return 3
        if any(k in tl for k in ["cryo-em", "crystal", "alphafold", "structure"]): return 4
        if any(k in tl for k in ["mouse", "zebrafish", "xenograft"]): return 5
        if any(k in tl for k in ["computational", "in silico"]): return 6
        return 8
    for q in qs:
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db": "pubmed", "term": q, "retmax": 7, "retmode": "json", "sort": "relevance"},
                headers=HDR, timeout=12)
            ids = [i for i in r.json().get("esearchresult", {}).get("idlist", []) if i not in seen]
            seen.update(ids)
            if not ids: continue
            time.sleep(0.35)
            r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"}, headers=HDR, timeout=15)
            res = r2.json().get("result", {})
            for pid in ids:
                p = res.get(pid, {}); au = p.get("authors", []); fa = au[0].get("name", "") if au else ""
                t = p.get("title", ""); tier = _tier(t)
                all_p.append({"pmid": pid, "title": t, "year": p.get("pubdate", "")[:4], "authors": f"{fa} et al." if len(au) > 1 else fa, "journal": p.get("source", ""), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/", "tier": tier, "tier_label": LMAP.get(tier, "Study"), "tier_color": TMAP.get(tier, "#475569")})
        except: pass
    return sorted(all_p, key=lambda x: x["tier"])[:n]


@st.cache_data(ttl=86400, show_spinner=False)
def _trials(gene):
    try:
        r = requests.get("https://clinicaltrials.gov/api/v2/studies",
            params={"query.term": gene, "filter.status": "RECRUITING", "pageSize": 8}, headers=HDR, timeout=15)
        out = []
        for s in r.json().get("studies", []):
            mod = s.get("protocolSection", {}); im = mod.get("identificationModule", {}); dm = mod.get("designModule", {})
            out.append({"nct_id": im.get("nctId", ""), "title": im.get("briefTitle", "")[:80], "phase": (dm.get("phases", ["?"])[0] if dm.get("phases") else "?"), "url": f"https://clinicaltrials.gov/study/{im.get('nctId', '')}"})
        return out
    except: return []


@st.cache_data(ttl=86400, show_spinner=False)
def _dgidb(gene):
    try:
        r = requests.get("https://dgidb.org/api/v2/interactions.json", params={"genes": gene}, headers=HDR, timeout=12)
        out = []
        for m in r.json().get("matchedTerms", []):
            for i in m.get("interactions", [])[:8]:
                d = i.get("drugName", "")
                if d: out.append({"drug": d, "type": (i.get("interactionTypes", ["?"])[0] if i.get("interactionTypes") else "?")})
        return out[:10]
    except: return []


def _gi(gene, cv, seq_len):
    path = [v for v in cv if v.get("ml_class") in ("CRITICAL", "HIGH")]
    n_p = len(path); n_c = sum(1 for v in cv if v.get("ml_class") == "CRITICAL")
    ms = sum(1 for v in path if v.get("stars", 0) >= 2)
    per100 = (n_p / seq_len * 100) if seq_len else 0
    reasons = []
    if n_p >= 5: reasons.append(f"{n_p} pathogenic/LP variants in ClinVar")
    if ms >= 2: reasons.append(f"{ms} expert-reviewed")
    if per100 >= 1: reasons.append(f"{per100:.2f} P/LP per 100 aa")
    if per100 >= 1 and n_p >= 5 and ms >= 2: v2, p = "DISEASE-CRITICAL", True
    elif per100 >= 0.5 or n_p >= 3: v2, p = "DISEASE-ASSOCIATED", True
    elif per100 >= 0.1 or n_p >= 1: v2, p = "MODERATE", None
    elif n_p == 0: v2, p = "NO DISEASE VARIANTS", False; reasons.append("No ClinVar P/LP — null mutant or understudied")
    else: v2, p = "VERY LOW", False
    return {"verdict": v2, "color": VERDICT_COLORS.get(v2, "#2a4060"), "n_pathogenic": n_p, "n_critical": n_c, "per100": round(per100, 3), "multi_star": ms, "reasons": reasons or ["Insufficient genetic evidence"], "pursue": p}


# ══════════════════════════════════════════════════════════
# 3D VIEWER
# ══════════════════════════════════════════════════════════
def _viewer3d(pdb, cv=None, style="plddt", height=400, spin=False, show_v=True, binding=None):
    if not pdb:
        st.markdown("""
        <div style="background:#040c14;border:1px solid #0f1e2d;border-radius:8px;padding:14px;margin:4px 0">
          <div style="color:#ffd20a;font-size:.7rem;font-weight:600;margin-bottom:5px;font-family:Inter,sans-serif">
            ⚠ AlphaFold structure not available for this protein
          </div>
          <div style="color:#2a4060;font-size:.67rem;line-height:1.7;font-family:Inter,sans-serif">
            May be a large membrane protein (&gt;2700 aa), recently characterised, or accession mismatch.
            Check <a href="https://alphafold.ebi.ac.uk" target="_blank" style="color:#00d4ff">alphafold.ebi.ac.uk</a> directly.
            All variant and disease data remain fully valid — structure is not required for triage decisions.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    esc = pdb.replace("\\", "\\\\").replace("`", "\\`")
    sp = "viewer.spin(true);" if spin else ""
    var_js = ""
    if show_v and cv:
        for v in [v for v in cv if v.get("ml_class") in ("CRITICAL", "HIGH") and v.get("position", 0) > 0][:50]:
            col = "#ff2d55" if v["ml_class"] == "CRITICAL" else "#ff8c42"
            var_js += f"viewer.addStyle({{resi:{v['position']}}},{{sphere:{{color:'{col}',radius:1.2,opacity:0.88}}}});"
    bind_js = ""
    if binding:
        for bs in binding[:15]:
            try:
                p = int(bs.get("start", "0"))
                if p: bind_js += f"viewer.addStyle({{resi:{p}}},{{sphere:{{color:'#ffd20a',radius:1.0,opacity:0.8}}}});"
            except: pass
    sj = {"plddt": "viewer.setStyle({},{cartoon:{colorfunc:function(a){var b=a.b;if(b>=90)return'#00b8d9';if(b>=70)return'#22d3a0';if(b>=50)return'#f5c842';return'#e05c5c';}}});", "spectrum": "viewer.setStyle({},{cartoon:{color:'spectrum'}});", "surface": "viewer.addSurface($3Dmol.SurfaceType.VDW,{opacity:0.72,colorscheme:'spectrum'});viewer.setStyle({},{cartoon:{color:'spectrum',opacity:0.25}});", "stick": "viewer.setStyle({},{stick:{colorscheme:'element'}});"}.get(style, "viewer.setStyle({},{cartoon:{color:'spectrum'}});")

    html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>body{{margin:0;background:#020609;overflow:hidden}}#v{{width:100%;height:{height}px}}
#info{{position:absolute;bottom:7px;left:7px;background:rgba(2,6,9,.96);color:#b8d4e8;
  border:1px solid rgba(0,212,255,.2);border-radius:5px;padding:6px 10px;font:11px/1.6 'JetBrains Mono',monospace;
  display:none;z-index:100;max-width:270px;pointer-events:none}}
#leg{{position:absolute;top:7px;right:7px;background:rgba(4,12,20,.92);color:#b8d4e8;
  border:1px solid #0f1e2d;border-radius:5px;padding:7px 10px;font:9px 'JetBrains Mono',monospace}}
.lr{{display:flex;align-items:center;gap:5px;margin:2px 0}}.lc{{width:9px;height:9px;border-radius:2px;flex-shrink:0}}
</style></head><body>
<div id="v"></div><div id="info"></div>
<div id="leg">
<b style="color:#00d4ff;font-size:9px">pLDDT</b>
<div class="lr"><div class="lc" style="background:#00b8d9"></div>&gt;90 Very High</div>
<div class="lr"><div class="lc" style="background:#22d3a0"></div>70–90 Confident</div>
<div class="lr"><div class="lc" style="background:#f5c842"></div>50–70 Low</div>
<div class="lr"><div class="lc" style="background:#e05c5c"></div>&lt;50 Very Low</div>
{"<div class='lr'><div class='lc' style='background:#ff2d55'></div>Critical variant</div><div class='lr'><div class='lc' style='background:#ff8c42'></div>High variant</div>" if show_v and cv else ""}
{"<div class='lr'><div class='lc' style='background:#ffd20a'></div>Binding site</div>" if binding else ""}
</div>
<script>
try{{
var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#020609'}});
viewer.addModel(`{esc}`,'pdb');
{sj}{var_js}{bind_js}
viewer.setClickable({{}},true,function(a,v){{
  var b=document.getElementById('info');b.style.display='block';
  var cl=a.b>=90?'Very High':a.b>=70?'Confident':a.b>=50?'Low':'Very Low';
  b.innerHTML='<b style="color:#00d4ff">'+a.resn+' '+a.resi+'</b> Chain '+a.chain+'<br>pLDDT: '+a.b.toFixed(1)+' ('+cl+')<br>Atom: '+a.atom;
  v.addStyle({{resi:a.resi}},{{sphere:{{color:'#ffffff',radius:0.7,opacity:0.4}}}});v.render();
}});
viewer.zoomTo();{sp}viewer.render();
}}catch(e){{document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:14px;font:11px monospace">Structure error: '+e.message+'</p>';}}
</script></body></html>"""
    components.html(html, height=height, scrolling=False)


# ══════════════════════════════════════════════════════════
# EXCEL EXPORT
# ══════════════════════════════════════════════════════════
def _make_excel(gene, pdata, cv, gnomad, gi_s, ot_d, string_d, papers, trials, dgidb, gtex, am_d):
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment
        wb = openpyxl.Workbook()
        def mk(nm, data, headers):
            ws = wb.create_sheet(nm[:31])
            ws.append(headers)
            for row in ws.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="0f1e2d")
                    cell.alignment = Alignment(horizontal="center")
            for d in data: ws.append(d)
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(12, min(50, max(len(str(c.value or "")) for c in col)))
            return ws
        mk("Summary", [["Gene", gene], ["Protein", pdata.get("protein_name", "")], ["Accession", pdata.get("accession", "")], ["Verdict", gi_s.get("verdict", "")], ["P/LP Variants", gi_s.get("n_pathogenic", 0)], ["Critical ML", gi_s.get("n_critical", 0)], ["pLI", gnomad.get("pLI", "N/A")], ["Essential", str(gnomad.get("essential", False))], ["Known Drugs", ot_d.get("known_drugs_count", 0)], ["Active Trials", len(trials)], ["Domain", domain], ["Research Goal", st.session_state.research_goal]], ["Field", "Value"])
        mk("ClinVar Variants", [[v.get("protein_change", ""), v.get("ml_class", ""), v.get("significance", ""), v.get("stars", 0), ", ".join(v.get("conditions", [])[:2]), v.get("source", "ClinVar"), v.get("url", "")] for v in cv[:200]], ["Protein Change", "ML Class", "Significance", "Stars", "Conditions", "Source", "URL"])
        mk("Diseases", [[d.get("name", ""), d.get("inheritance", ""), d.get("desc", "")[:200], d.get("omim", "")] for d in pdata.get("diseases", [])], ["Disease", "Inheritance", "Description", "OMIM"])
        mk("AlphaMissense", [[a["position"], a["ref"], a["alt"], a["score"], a["class"]] for a in (am_d or [])[:500]], ["Position", "Ref", "Alt", "AM Score", "Class"])
        mk("STRING Network", [[p["partner"], p["score"], p.get("experimental", 0)] for p in string_d[:50]], ["Partner", "STRING Score", "Experimental Score"])
        mk("Literature", [[p["title"], p["authors"], p["journal"], p["year"], p["tier_label"], p["pmid"], p["url"]] for p in papers], ["Title", "Authors", "Journal", "Year", "Tier", "PMID", "URL"])
        mk("Clinical Trials", [[t["nct_id"], t["title"], t["phase"], t["url"]] for t in trials], ["NCT ID", "Title", "Phase", "URL"])
        mk("Drugs", [[d.get("drug", ""), d.get("type", ""), "DGIdb"] for d in dgidb] + [[d, "", "OpenTargets"] for d in ot_d.get("known_drugs", [])], ["Drug", "Interaction Type", "Source"])
        mk("GTEx Expression", [[tissue, round(tpm, 2)] for tissue, tpm in sorted(gtex.items(), key=lambda x: x[1], reverse=True)[:50]], ["Tissue", "Median TPM"])
        if wb.worksheets: del wb["Sheet"]
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return buf.getvalue()
    except Exception as ex:
        return None


# ══════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="padding:8px 0 7px;border-bottom:1px solid #0f1e2d;margin-bottom:7px">
      <div style="font-size:.95rem;font-weight:700;background:linear-gradient(90deg,#00d4ff,#6366f1);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:Inter,sans-serif">
        🔬 Protellect
      </div>
      <div style="font-size:.6rem;color:#2a4060;margin-top:1px;font-family:Inter,sans-serif">
        {user.get('name', '')} · {user.get('tier', 'free').upper()} · {meta.get('icon','')} {domain}
      </div>
    </div>
    """, unsafe_allow_html=True)

    used = st.session_state.searches_used; quota = user.get("quota", 5)
    if user.get("dev"): qlbl, qcol = "Dev — Unlimited", "#f97316"
    elif user.get("tier") == "enterprise": qlbl, qcol = "Enterprise — Unlimited", "#f97316"
    else:
        rem = quota - used; qcol = "#00d4ff" if rem > 1 else "#ffd20a" if rem == 1 else "#ef4444"
        qlbl = f"{rem} searches remaining" if rem > 0 else "Quota exhausted"
    st.markdown(f'<div style="background:{qcol}0d;border:1px solid {qcol}22;border-radius:4px;padding:3px 8px;font-size:.66rem;color:{qcol};margin-bottom:7px;text-align:center;font-family:Inter,sans-serif">{qlbl}</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:6px 0 2px;font-family:Inter,sans-serif">RESEARCH GOAL</div>', unsafe_allow_html=True)
    st.selectbox("rg", ["Drug target identification", "Disease mechanism", "Variant pathogenicity", "Therapeutic hypothesis", "Biomarker discovery", "Academic research"], label_visibility="collapsed", key="research_goal")

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">PROTEIN SEARCH</div>', unsafe_allow_html=True)
    exs = DOMAIN_EXAMPLES.get(domain, [])[:3]
    qi = st.text_input("ps", value=st.session_state._qval, placeholder=f"e.g. {' · '.join(exs) if exs else 'FLNA · TP53'}", label_visibility="collapsed", key="_sw")
    st.session_state._qval = qi
    if st.button("⚡  Analyse Protein", type="primary", use_container_width=True, key="ab"):
        st.session_state._trig = True

    # Sidebar disease breakdown when protein loaded
    ck_sb = st.session_state._qval.upper().strip()
    cached_sb = st.session_state.protein_data_cache.get(ck_sb, {})
    if cached_sb:
        pdata_sb = cached_sb.get("pdata", {})
        cv_sb = cached_sb.get("cv", [])
        dis_sb = pdata_sb.get("diseases", [])
        if dis_sb:
            st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:8px 0 3px;font-family:Inter,sans-serif">DISEASE BREAKDOWN</div>', unsafe_allow_html=True)
            for d in dis_sb[:6]:
                inh = d.get("inheritance", "?"); cc = "#ff8c42" if inh == "Somatic" else "#6366f1"
                st.markdown(f'<div style="display:flex;gap:4px;padding:2px 0;border-bottom:1px solid #070d14;font-size:.65rem;font-family:Inter,sans-serif"><span style="color:{cc};min-width:52px">{inh}</span><span style="color:#7090a0">{d.get("name","?")[:32]}</span></div>', unsafe_allow_html=True)
        path_sb = [v for v in cv_sb if v.get("ml_class") in ("CRITICAL", "HIGH")]
        if path_sb:
            st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 3px;font-family:Inter,sans-serif">TOP VARIANTS</div>', unsafe_allow_html=True)
            for v in path_sb[:5]:
                st.markdown(f'<div style="display:flex;gap:4px;padding:2px 0;border-bottom:1px solid #070d14;align-items:center">{_badge(v.get("ml_class","LOW"))}<span style="color:#5a7590;font-family:JetBrains Mono,monospace;font-size:.62rem">{v.get("protein_change","?")[:16]}</span></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">DISEASE → PROTEINS</div>', unsafe_allow_html=True)
    di = st.text_input("dp", value=st.session_state._dval, placeholder="e.g. arrhythmia · epilepsy", label_visibility="collapsed", key="_dw")
    st.session_state._dval = di
    if st.button("🔗 Find Disease Proteins", use_container_width=True, key="db"):
        st.session_state._dtrig = True

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">WET-LAB ASSAY RESULT</div>', unsafe_allow_html=True)
    wl = st.text_area("wl", value=st.session_state.wet_lab_text, placeholder="Describe result — e.g. Ser2152-P detected at 10nM, abolished in R2149Q variant.", label_visibility="collapsed", height=55, key="wli")
    st.session_state.wet_lab_text = wl
    if wl and cached_sb:
        pdata_sb2 = cached_sb.get("pdata", {}); is_gpcr_sb = pdata_sb2.get("is_gpcr", False)
        interp = ("Filamin Ser2152-P — direct GPCR activation signal. PMID:26124276." if "phospho" in wl.lower() and is_gpcr_sb else "PPI disruption — validate by Co-IP." if any(x in wl.lower() for x in ["co-ip", "pull"]) else "Functional signal — cross-reference ClinVar pathogenic residues.")
        st.markdown(f'<div style="background:#020609;border:1px solid #0f1e2d;border-radius:4px;padding:5px 8px;font-size:.64rem;color:#3a5570;line-height:1.6;font-family:Inter,sans-serif">{interp}</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">CSV DATA</div>', unsafe_allow_html=True)
    cf = st.file_uploader("cu", type=["csv", "txt", "tsv"], label_visibility="collapsed", key="cu")
    if cf:
        try:
            sep = "\t" if cf.name.endswith((".txt", ".tsv")) else ","
            df_c = pd.read_csv(cf, sep=sep, nrows=100000); st.session_state.csv_data = df_c
            st.markdown(f'<div style="color:#00d4ff;font-size:.64rem;margin-top:2px;font-family:Inter,sans-serif">✓ {cf.name} · {len(df_c):,} rows · {len(df_c.columns)} cols</div>', unsafe_allow_html=True)
        except Exception as ex: st.error(f"Parse error: {ex}")

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">SENSITIVITY</div>', unsafe_allow_html=True)
    sens = st.slider("se", 0.0, 1.0, st.session_state.sensitivity, 0.05, label_visibility="collapsed", key="sensitivity")
    st.markdown(f'<div class="dim" style="margin-top:-4px;margin-bottom:3px">AM threshold: {sens:.2f}</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:.56rem;color:#0f2035;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;font-family:Inter,sans-serif">AI REPORT KEY</div>', unsafe_allow_html=True)
    ak = st.text_input("ak", type="password", placeholder="sk-ant-...", label_visibility="collapsed", key="_aki")
    if ak: st.session_state.anthropic_key = ak
    if st.session_state.anthropic_key:
        st.markdown('<div style="font-size:.62rem;color:#22c55e;margin-top:1px;font-family:Inter,sans-serif">● AI enabled</div>', unsafe_allow_html=True)

    st.divider()
    ca, cb, cc_btn = st.columns(3)
    with ca:
        if st.button("📖", use_container_width=True, help="Tutorial"):
            st.session_state.show_tutorial = True; st.rerun()
    with cb:
        if st.button("🔄", use_container_width=True, help="Clear cache"):
            st.cache_data.clear(); st.toast("Cache cleared")
    with cc_btn:
        if st.button("↪", use_container_width=True, help="Logout"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
    if st.button("← Back to Domains", use_container_width=True, key="back_dom"):
        st.session_state.domain = None; st.session_state.current_protein = None; st.rerun()


# ══════════════════════════════════════════════════════════
# DISEASE TRIGGER
# ══════════════════════════════════════════════════════════
if st.session_state._dtrig and st.session_state._dval:
    st.session_state._dtrig = False
    dq = st.session_state._dval
    _sec(f"Disease → Proteins: {dq}")
    try:
        r = requests.get("https://rest.uniprot.org/uniprotkb/search",
            params={"query": f"cc_disease:{dq} AND organism_id:9606 AND reviewed:true", "format": "json", "size": 10, "fields": "accession,gene_names,protein_name"},
            headers=HDR, timeout=12)
        hits = r.json().get("results", [])
        if hits:
            for hit in hits:
                gs = [g.get("geneName", {}).get("value", "") for g in hit.get("genes", [])]
                g = gs[0] if gs else hit.get("primaryAccession", "")
                pn = hit.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
                c1, c2 = st.columns([4, 1])
                with c1: st.markdown(f'<span style="color:#00d4ff;font-family:JetBrains Mono,monospace;font-weight:600">{g}</span> <span class="dim">{pn[:60]}</span>', unsafe_allow_html=True)
                with c2:
                    if st.button("Analyse", key=f"dis_{g}"): st.session_state._qval = g; st.rerun()
        else: st.info(f"No proteins found for '{dq}'.")
    except: st.warning("Search unavailable.")
    st.stop()


# ══════════════════════════════════════════════════════════
# MICROBIOME DOMAIN
# ══════════════════════════════════════════════════════════
if domain == "Microbiome":
    st.markdown(f'<div style="color:#22c55e;font-size:.88rem;font-weight:700;font-family:Inter,sans-serif;margin-bottom:8px">🦠 Microbiome Intelligence</div>', unsafe_allow_html=True)
    mt1, mt2, mt3 = st.tabs(["Annotation", "Taxonomy", "Batch Analysis"])
    with mt1:
        _sec("Vague → Specific Gene Annotation")
        c1, c2 = st.columns(2)
        with c1:
            gid = st.text_input("Gene ID / KO", placeholder="K01810, WP_001234", key="mg_gid")
            vague = st.text_input("Current annotation", placeholder="biosynthesis", key="mg_vague")
            org_ctx = st.text_input("Organism context", placeholder="gut microbiome", key="mg_org")
            run_ann = st.button("Annotate", type="primary", key="mg_go")
        with c2:
            st.markdown('<div class="dim" style="margin-top:8px;line-height:1.8">Expands vague metabolic annotations into specific EC-numbered pathways with ecological context. Add Anthropic API key for AI-powered annotation.</div>', unsafe_allow_html=True)
        if run_ann and vague:
            EXP = {"biosynthesis": "Anabolic enzyme — specify via KO: amino acid (DAP pathway for lysine), lipid (FASII), or B-vitamin. Run eggNOG-mapper v2 for EC number.", "chemosynthesis": "Chemolithotrophy — inorganic oxidation (NH₃, S²⁻, Fe²⁺). AMO/NXR/Sox gene families.", "protein aggregation": "Curli (CsgA/B → biofilm + TLR2/TLR1) or functional amyloid. Check N-terminal signal.", "hypothetical protein": "(1) AlphaFold+Foldseek → (2) eggNOG-mapper DIAMOND → (3) InterProScan → (4) Phyre2.", "transporter": "TC database: ABC (ATP), MFS (proton gradient), RND (multidrug efflux).", "metabolism": "KEGG GHOSTX or eggNOG for specific reaction. SEED/RAST pathway assignment."}
            ak2 = st.session_state.get("anthropic_key", ""); result = None
            if ak2:
                try:
                    import anthropic; client = anthropic.Anthropic(api_key=ak2)
                    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role": "user", "content": f"Gene:{gid}\nCurrent:{vague}\nOrganism:{org_ctx}\nSpecific: molecular function, EC number, pathway, ecological role, clinical relevance, validation tools. No vague terms."}])
                    result = msg.content[0].text
                except: pass
            if not result:
                al = vague.lower(); result = next((v for k, v in EXP.items() if k in al), f"'{vague}' not in rule base. Run eggNOG-mapper v2.")
            ca, cb = st.columns(2)
            with ca: st.markdown(f'<div class="card" style="border-color:rgba(239,68,68,.2)"><span class="dim" style="color:#ef4444">❌ Before</span><br><i style="color:#fca5a5">{vague}</i></div>', unsafe_allow_html=True)
            with cb: st.markdown(f'<div class="card" style="border-color:rgba(34,197,94,.2)"><span class="dim" style="color:#22c55e">✅ After</span><div style="font-size:.7rem;color:#b8d4e8;margin-top:5px;line-height:1.7">{result}</div></div>', unsafe_allow_html=True)
    with mt2:
        _sec("Taxonomy Intelligence")
        taxon = st.text_input("Organism", placeholder="Akkermansia muciniphila", key="mg_tax")
        ROLES = {"Lactobacillus": "Lactic acid producer; pH pathogen competition; gut barrier; SCFA; probiotic.", "Bifidobacterium": "Probiotic; B-vitamin synthesis; infant microbiome; immune modulation.", "Bacteroides": "Major fermenter; PULs; keystone coloniser; propionate/acetate.", "Akkermansia": "Mucin-layer coloniser; gut barrier; depleted in obesity/T2D/IBD; next-gen probiotic.", "Faecalibacterium": "Butyrate (F. prausnitzii); anti-inflammatory; depleted in IBD.", "Helicobacter": "CagA/VacA; peptic ulcer; gastric cancer; MALT lymphoma.", "Fusobacterium": "FadA adhesin; CRC invasion; Wnt/β-catenin; oral pathobiont."}
        if taxon:
            g2 = taxon.split()[0]; role = ROLES.get(g2, "Not curated — check NCBI taxonomy and primary literature.")
            st.markdown(f'<div class="card"><span style="color:#22c55e;font-family:JetBrains Mono,monospace">{taxon}</span><br><span style="font-size:.7rem;color:#b8d4e8;line-height:1.6">{role}</span></div>', unsafe_allow_html=True)
    with mt3:
        _sec("Batch Annotation Quality")
        raw = st.text_area("Annotations (one per line)", height=100, key="mg_b")
        VAGUE = {"biosynthesis", "chemosynthesis", "protein aggregation", "hypothetical protein", "metabolism", "transport", "regulation", "unknown", "uncharacterized", "putative"}
        if st.button("Analyse", type="primary", key="mg_ba") and raw:
            lines_b = [l.strip() for l in raw.splitlines() if l.strip()]
            vn = sum(1 for l in lines_b if any(v in l.lower() for v in VAGUE))
            c1, c2, c3 = st.columns(3); c1.metric("Total", len(lines_b)); c2.metric("Vague", vn); c3.metric("Informative", len(lines_b) - vn)
            for l in lines_b:
                iv = any(v in l.lower() for v in VAGUE)
                st.markdown(f'<div style="font-size:.68rem;padding:2px 0;border-bottom:1px solid #070d14;font-family:Inter,sans-serif"><span style="color:{"#ef4444" if iv else "#22c55e"}">{"❌" if iv else "✅"}</span> <span style="color:#b8d4e8">{l}</span></div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════
# EMPTY STATE (no query entered)
# ══════════════════════════════════════════════════════════
query = st.session_state._qval.strip()
if not query and not st.session_state._trig:
    color = meta.get("color", "#00d4ff")
    st.markdown(f"""
    <div class="card" style="border-color:{color}18;padding:22px 26px">
      <div style="font-size:1.6rem;margin-bottom:8px">{meta.get('icon','🔬')}</div>
      <div style="font-size:.92rem;font-weight:600;color:{color};margin-bottom:5px;font-family:Inter,sans-serif">{domain}</div>
      <div style="font-size:.72rem;color:#2a4060;margin-bottom:10px;line-height:1.7;font-family:Inter,sans-serif">{meta.get('desc','')}</div>
      <div style="margin-bottom:12px">{' '.join(f'<span class="pill">{t.strip()}</span>' for t in meta.get('tags','').split('·') if t.strip())}</div>
      <div style="font-size:.68rem;color:#0f2035;border-top:1px solid #0f1e2d;padding-top:9px;font-family:Inter,sans-serif">
        Type any gene symbol or protein name in the <b style="color:#b8d4e8">Protein Search</b> sidebar, then click <b style="color:{color}">⚡ Analyse Protein</b>
      </div>
    </div>
    """, unsafe_allow_html=True)
    exs = DOMAIN_EXAMPLES.get(domain, [])
    if exs:
        st.markdown('<div style="color:#0f2035;font-size:.58rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin:12px 0 6px;font-family:Inter,sans-serif">QUICK EXAMPLES</div>', unsafe_allow_html=True)
        n = min(7, len(exs))
        ec = st.columns(n)
        for i, ex in enumerate(exs[:n]):
            with ec[i]:
                if st.button(ex, key=f"dex_{ex}", use_container_width=True):
                    st.session_state._qval = ex; st.rerun()
    st.stop()


# ══════════════════════════════════════════════════════════
# SEARCH & LOAD DATA
# ══════════════════════════════════════════════════════════
st.session_state._trig = False
query = NAME_MAP.get(query.strip().lower(), query)
st.session_state._qval = query

NON_HUMAN = ["gelatin", "gfp", "luciferase", "ovalbumin", "bovine", "beta keratin", "algae"]
if any(t in query.lower() for t in NON_HUMAN):
    st.error(f"'{query}' appears to be non-human. Protellect analyses human proteins only."); st.stop()

can_search = user.get("dev") or user.get("tier") == "enterprise" or st.session_state.searches_used < user.get("quota", 5)
if not can_search:
    st.error("Search quota exhausted. Upgrade at protellect.io."); st.stop()

ck = query.upper()
if ck not in st.session_state.protein_data_cache:
    prog = st.progress(0, text=f"Fetching {query} from UniProt…")
    try:
        prog.progress(5, "UniProt search…"); uraw = _uniprot(query)
        prog.progress(14, "Parsing…"); pdata = _parse(uraw)
        if not pdata or not pdata.get("accession"):
            st.error(f"Could not find '{query}'. Try gene symbol (FLNA, TP53) or protein name (filamin A, p53)."); st.stop()
        if not pdata.get("is_human", True):
            st.error(f"'{pdata.get('gene', query)}' is not human. Protellect requires human proteins only."); st.stop()
        gene = pdata["gene"] or query.upper(); acc = pdata["accession"]
        prog.progress(24, "AlphaFold structure…"); pdb = _alphafold(acc); pld = _plddt(pdb)
        prog.progress(36, "ClinVar variants…"); cv = _clinvar(gene)
        uni_v = pdata.get("uni_variants", [])
        if len(cv) < 5 and uni_v:
            existing = {v.get("position", 0) for v in cv}
            for uv in uni_v:
                if uv.get("position", 0) not in existing: cv.append(uv)
            cv = sorted(cv, key=lambda x: x.get("ml_class", "LOW") == "CRITICAL", reverse=True)
        prog.progress(48, "gnomAD + STRING…"); gnomad = _gnomad(gene); string_d = _string(gene)
        prog.progress(60, "OpenTargets + DGIdb…"); ot_d = _opentargets(gene); dgidb = _dgidb(gene)
        prog.progress(72, "AlphaMissense + PubMed…"); am_d = _alphamissense(acc); papers = _pubmed(gene)
        prog.progress(84, "GTEx + Trials…"); gtex = _gtex(gene); trials = _trials(gene)
        prog.progress(95, "Scoring…"); gi_s = _gi(gene, cv, pdata.get("seq_len", 500))
        prog.progress(100, "Complete ✓"); prog.empty()
        st.session_state.protein_data_cache[ck] = dict(
            pdata=pdata, pdb=pdb, pld=pld, cv=cv, gnomad=gnomad, string_d=string_d,
            ot_d=ot_d, am_d=am_d, papers=papers, gtex=gtex, dgidb=dgidb, trials=trials, gi_s=gi_s)
        if not user.get("dev"): st.session_state.searches_used += 1
        ws = st.session_state.workspace
        if not any(w.get("gene") == (pdata["gene"] or query.upper()) for w in ws):
            ws.insert(0, {"gene": pdata["gene"] or query.upper(), "accession": acc, "protein": pdata.get("protein_name", "")[:50], "verdict": gi_s["verdict"], "color": gi_s["color"], "domain": domain})
            st.session_state.workspace = ws[:50]
        st.session_state.current_protein = ck
    except Exception as ex:
        import traceback; st.error(f"Loading error: {ex}")
        with st.expander("Traceback"): st.code(traceback.format_exc())
        st.stop()
else:
    st.session_state.current_protein = ck

D = st.session_state.protein_data_cache[ck]
pdata = D["pdata"]; pdb = D["pdb"]; pld = D["pld"]; cv = D["cv"]
gnomad = D["gnomad"]; string_d = D["string_d"]; ot_d = D["ot_d"]
am_d = D["am_d"]; papers = D["papers"]; gtex = D["gtex"]
dgidb = D["dgidb"]; trials = D["trials"]; gi_s = D["gi_s"]
gene = pdata["gene"] or query.upper(); acc = pdata["accession"]
is_gpcr = pdata.get("is_gpcr", False); is_kinase = pdata.get("is_kinase", False)
is_pase = pdata.get("is_phosphatase", False)
is_cardiac = gene.upper() in {"ADRB1", "ADRB2", "AGTR1", "CHRM2"}
is_filamin = any(k in " ".join(pdata.get("functions", []) + pdata.get("keywords", [])).lower() for k in ["filamin", "actin-binding protein 280"])
verdict = gi_s["verdict"]; vcolor = gi_s["color"]; pursue = gi_s.get("pursue")
path_v = [v for v in cv if v.get("ml_class") in ("CRITICAL", "HIGH")]
n_path = gi_s.get("n_pathogenic", 0); n_crit = gi_s.get("n_critical", 0)
sens = st.session_state.sensitivity
druggable = ot_d.get("sm_tractable") or ot_d.get("ab_tractable") or ot_d.get("known_drugs_count", 0) > 0


# ══════════════════════════════════════════════════════════
# VERDICT BANNER
# ══════════════════════════════════════════════════════════
if verdict == "DISEASE-CRITICAL":
    bl, bb, bbc, btc = "🔴 DISEASE-CRITICAL — PURSUE IMMEDIATELY", "rgba(255,45,85,.1)", "rgba(255,45,85,.4)", "#ff2d55"
elif verdict == "DISEASE-ASSOCIATED":
    bl, bb, bbc, btc = "🟠 DISEASE-ASSOCIATED — SELECTIVE PURSUIT", "rgba(255,140,66,.07)", "rgba(255,140,66,.35)", "#ff8c42"
elif verdict == "MODERATE":
    bl, bb, bbc, btc = "🟡 MODERATE EVIDENCE — VALIDATE FURTHER", "rgba(255,210,10,.05)", "rgba(255,210,10,.3)", "#ffd20a"
elif verdict == "NO DISEASE VARIANTS":
    bl, bb, bbc, btc = "⬜ NO DISEASE VARIANTS — DEPRIORITISE", "rgba(42,64,96,.08)", "rgba(42,64,96,.3)", "#3a5570"
else:
    bl, bb, bbc, btc = "⚪ VERY LOW EVIDENCE — APPROACH WITH CAUTION", "rgba(42,64,96,.05)", "rgba(42,64,96,.2)", "#2a4060"

flags = ""
if druggable: flags += f' <span style="background:rgba(34,197,94,.1);color:#22c55e;border:1px solid rgba(34,197,94,.25);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">DRUGGABLE</span>'
if n_crit >= 3: flags += f' <span style="background:rgba(255,45,85,.1);color:#ff2d55;border:1px solid rgba(255,45,85,.25);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">YIELDS TRUE RESULTS</span>'
if verdict == "NO DISEASE VARIANTS": flags += f' <span style="background:rgba(239,68,68,.08);color:#ef4444;border:1px solid rgba(239,68,68,.2);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">DEPRIORITISE ENTIRELY</span>'
if n_path > 0 and n_crit == 0: flags += f' <span style="background:rgba(255,210,10,.07);color:#ffd20a;border:1px solid rgba(255,210,10,.2);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">INVISIBLE ASSOCIATION</span>'
if is_gpcr: flags += f' <span style="background:rgba(0,212,255,.08);color:#00d4ff;border:1px solid rgba(0,212,255,.25);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">GPCR</span>'
if is_kinase: flags += f' <span style="background:rgba(34,197,94,.08);color:#22c55e;border:1px solid rgba(34,197,94,.2);border-radius:3px;padding:0 6px;font-size:.59rem;font-weight:700;font-family:Inter,sans-serif">KINASE</span>'

st.markdown(f"""
<div style="background:{bb};border:1.5px solid {bbc};border-radius:8px;padding:9px 16px;display:flex;align-items:center;gap:12px;margin-bottom:7px">
  <div style="flex:1">
    <span style="font-size:.82rem;font-weight:700;color:{btc};font-family:Inter,sans-serif">{bl}</span>
    <span style="color:{btc}80;font-size:.65rem;margin-left:8px;font-family:Inter,sans-serif">{' · '.join(gi_s.get('reasons', [])[:2])}</span>
    <div style="margin-top:3px">{flags}</div>
  </div>
  <div style="display:flex;gap:10px;text-align:center;flex-shrink:0">
    <div><div style="font-size:.74rem;font-weight:700;color:#00d4ff;font-family:JetBrains Mono,monospace">{pdata.get('seq_len',0):,}</div><div style="font-size:.54rem;color:#2a4060;font-family:Inter,sans-serif">AA</div></div>
    <div><div style="font-size:.74rem;font-weight:700;color:#ff2d55;font-family:JetBrains Mono,monospace">{n_path}</div><div style="font-size:.54rem;color:#2a4060;font-family:Inter,sans-serif">P/LP</div></div>
    <div><div style="font-size:.74rem;font-weight:700;color:#00d4ff;font-family:JetBrains Mono,monospace">{f"{gnomad['pLI']:.2f}" if gnomad.get('pLI') else '—'}</div><div style="font-size:.54rem;color:#2a4060;font-family:Inter,sans-serif">pLI</div></div>
    <div><div style="font-size:.74rem;font-weight:700;color:#22c55e;font-family:JetBrains Mono,monospace">{ot_d.get('known_drugs_count',0)}</div><div style="font-size:.54rem;color:#2a4060;font-family:Inter,sans-serif">DRUGS</div></div>
    <div><div style="font-size:.74rem;font-weight:700;color:#ffd20a;font-family:JetBrains Mono,monospace">{len(trials)}</div><div style="font-size:.54rem;color:#2a4060;font-family:Inter,sans-serif">TRIALS</div></div>
  </div>
</div>
<div style="font-size:.65rem;color:#2a4060;margin-bottom:7px;font-family:JetBrains Mono,monospace">
  {gene} · {acc} · {pdata.get('protein_name','')[:62]} · {pdata.get('organism','')}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════
t0, t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Overview", "🎯 Triage", "🧩 Protein Explorer",
    "⚗️ Experiments", "💊 Therapeutic Targets", "🤖 AI Report", "📁 Workspace"
])

AA = {"A": ("Ala", 1.8, 0), "R": ("Arg", -4.5, 1), "N": ("Asn", -3.5, 0), "D": ("Asp", -3.5, -1), "C": ("Cys", 2.5, 0), "Q": ("Gln", -3.5, 0), "E": ("Glu", -3.5, -1), "G": ("Gly", -0.4, 0), "H": ("His", -3.2, 0), "I": ("Ile", 4.5, 0), "L": ("Leu", 3.8, 0), "K": ("Lys", -3.9, 1), "M": ("Met", 1.9, 0), "F": ("Phe", 2.8, 0), "P": ("Pro", -1.6, 0), "S": ("Ser", -0.8, 0), "T": ("Thr", -0.7, 0), "W": ("Trp", -0.9, 0), "Y": ("Tyr", -1.3, 0), "V": ("Val", 4.2, 0)}
top_v = [v.get("protein_change", "?") for v in path_v[:3]]
vstr = ", ".join(top_v) or "no P/LP variants identified"
partners = [p["partner"] for p in string_d[:3]] if string_d else ["STRING partner"]
diseases = pdata.get("diseases", [])
cell_type = "iPSC-cardiomyocytes" if is_cardiac else "iPSC-neurons (NGN2)" if any(x in " ".join([d.get("name", "") for d in diseases]).lower() for x in ["neuro", "parkinson", "alzheimer", "epilep"]) else "HEK293T"


# ─── TAB 0: OVERVIEW ──────────────────────────────────────
with t0:
    cl, cr = st.columns([1.15, .85], gap="large")
    with cl:
        _sec("AlphaFold 3D Structure")
        vw = st.radio("t0v", ["pLDDT", "Spectrum", "Surface"], horizontal=True, label_visibility="collapsed", key="t0_vw")
        _viewer3d(pdb, cv=cv, style={"pLDDT": "plddt", "Spectrum": "spectrum", "Surface": "surface"}[vw], height=360, show_v=True, binding=pdata.get("binding_sites", []))
        if pld:
            vals = list(pld.values()); avg = np.mean(vals)
            fig = go.Figure(go.Histogram(x=vals, nbinsx=20, marker_color=["#00b8d9" if v >= 90 else "#22d3a0" if v >= 70 else "#f5c842" if v >= 50 else "#e05c5c" for v in vals]))
            fig.update_layout(height=105, plot_bgcolor="#020609", paper_bgcolor="#020609", xaxis=dict(title="pLDDT", gridcolor="#070d14", color="#2a4060", tickfont=dict(size=8, family="JetBrains Mono")), yaxis=dict(gridcolor="#070d14", color="#2a4060", tickfont=dict(size=8)), font=dict(color="#b8d4e8", size=9, family="Inter"), margin=dict(t=4, b=22, l=28, r=4), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<span class="dim">Avg pLDDT {avg:.1f} · {sum(1 for v in vals if v>=70)/len(vals)*100:.0f}% confident · 🔴 Critical · 🟠 High · 🟡 Binding</span>', unsafe_allow_html=True)

        _sec("Disease Associations — What, How, and Why")
        if diseases:
            for d in diseases[:8]:
                nm = d.get("name", "?"); inh = d.get("inheritance", "?"); desc = d.get("desc", "")[:200]
                cc = "#ff8c42" if inh == "Somatic" else "#6366f1"
                n_cv_dis = [v for v in cv if any(nm[:15].lower() in c.lower() for c in v.get("conditions", []))]
                strength = "Strong" if len(n_cv_dis) > 3 else "Moderate" if len(n_cv_dis) > 0 else "UniProt annotation"
                with st.expander(f"[{inh}] {nm[:50]}  —  {strength}"):
                    st.markdown(f'<div style="font-size:.7rem;color:#b8d4e8;line-height:1.75;margin-bottom:8px;font-family:Inter,sans-serif">{desc or "No description available."}</div>', unsafe_allow_html=True)
                    mech = ""
                    if is_gpcr: mech = "GPCR-mediated: pathogenic variants disrupt G-protein coupling, receptor internalisation, or Filamin cytoskeletal anchoring via H8-FBM. Validated readout: Filamin Ser2152-P IP assay (Nakamura JBC 2015, PMID:26124276)."
                    elif is_kinase: mech = "Kinase-mediated: GoF variants hyperactivate substrate phosphorylation; LoF variants abolish catalytic activity. Check DFG motif and activation loop variants first."
                    elif is_filamin: mech = "Filamin-mediated: pathogenic variants at Ig21 domain disrupt GPCR-cytoskeleton coupling. Ser2152 phosphorylation is the mechanistic readout. R2149Q → periventricular nodular heterotopia validates this site."
                    elif inh == "Somatic": mech = "Somatic gain-of-function or tumour suppressor loss. Clonal expansion driven by proliferative advantage. Check COSMIC for hotspot co-occurrence."
                    else: mech = f"Germline loss-of-function. Haploinsufficiency or biallelic loss. pLI={gnomad.get('pLI','N/A')} — {'essential gene; handle carefully' if gnomad.get('essential') else 'not highly constrained'}."
                    if mech: st.markdown(f'<div class="card" style="border-color:rgba(0,212,255,.12)"><div style="color:#00d4ff;font-size:.62rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">MECHANISM</div><div style="font-size:.69rem;color:#8ab0c8;line-height:1.7;font-family:Inter,sans-serif">{mech}</div></div>', unsafe_allow_html=True)
                    if d.get("omim"): st.markdown(f'<a class="pill" href="https://omim.org/entry/{d["omim"]}" target="_blank">OMIM {d["omim"]} ↗</a>', unsafe_allow_html=True)
                    if n_cv_dis:
                        st.markdown(f'<div class="dim" style="margin:5px 0">ClinVar variants for this disease: {len(n_cv_dis)}</div>', unsafe_allow_html=True)
                        for v in n_cv_dis[:3]: st.markdown(f'<div style="font-size:.66rem;padding:2px 0;border-bottom:1px solid #070d14;font-family:Inter,sans-serif">{_badge(v.get("ml_class","LOW"))} <span style="color:#5a7590;font-family:JetBrains Mono,monospace">{v.get("protein_change","?")[:18]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card"><div style="color:#ffd20a;font-size:.7rem;font-weight:600;margin-bottom:5px;font-family:Inter,sans-serif">No Confirmed Disease Associations</div><div class="dim" style="line-height:1.7">ClinVar has no P/LP variants for <b style="color:#b8d4e8">{gene}</b> and UniProt lists no disease annotations. This may mean: (1) understudied gene, (2) embryonic lethal LoF — pLI={gnomad.get("pLI","N/A")}, (3) genuinely redundant in vivo. Review gnomAD, STRING partners, and GTEx before deprioritising.</div></div>', unsafe_allow_html=True)

        _sec("Top 5 Recommended Experiments")
        am_path_s = {a["position"] for a in (am_d or []) if a.get("class") == "pathogenic"}
        path_pos_s = {v["position"] for v in path_v if v.get("position")}
        concordant = len(path_pos_s & am_path_s)
        exps_top = [
            {"n": 1, "name": "AlphaFold-Multimer (ColabFold) — FREE", "cost": "Free", "time": "3–5 days", "p": 80, "d": f"Model {gene}:{partners[0] if partners else 'partner'} complex. ipTM>0.8 = confident interface. Map {vstr} onto predicted binding site before committing wet-lab budget. Identifies druggable pockets and PPI interfaces."},
            {"n": 2, "name": f"Filamin Ser2152-P IP Assay{'  ★ PRIMARY READOUT' if is_gpcr else ''}" if is_gpcr or is_filamin else f"ADP-Glo Kinase Assay — WT vs variants" if is_kinase else f"Co-IP — {gene} + {partners[0] if partners else 'TOP PARTNER'}", "cost": "$400–800" if (is_gpcr or is_filamin) else "$1,200–2,000" if is_kinase else "$500–900", "time": "1 week", "p": 90 if (is_gpcr or is_filamin) else 85 if is_kinase else 78, "d": (f"Agonist EC80 → 10 min → lyse → anti-FLNA IP → pSer2152 western. WT vs {vstr}. Cell: {cell_type}. More receptor-proximal than cAMP/arrestin. PMID:26124276." if (is_gpcr or is_filamin) else f"ADP-Glo luminescent kinase assay. Compare Vmax/Km WT vs {vstr}. Determines GoF vs LoF — dictates drug strategy." if is_kinase else f"FLAG-{gene} WT and {vstr}. Immunoprecipitate. Western for {partners[0] if partners else 'partner'}. Variant that abolishes co-IP = interface = drug target zone.")},
            {"n": 3, "name": "Thermal Stability Assay (DSF/TSA)", "cost": "$800–1,500", "time": "1–2 weeks", "p": 75, "d": f"Differential scanning fluorimetry. WT vs {vstr}. ΔTm>3°C = structurally destabilising. Cross-reference AM score ≥{sens:.2f}. Also screens compounds — thermal shift = engagement confirmed."},
            {"n": 4, "name": f"CRISPR Knock-in {top_v[0] if top_v else 'P/LP'} in {cell_type}", "cost": "$12,000–20,000", "time": "10–14 weeks", "p": 65 if n_crit >= 2 and concordant >= 1 else 20, "d": f"{'JUSTIFIED: '+str(n_crit)+' CRITICAL ClinVar + '+str(concordant)+' AM-concordant positions.' if n_crit>=2 and concordant>=1 else 'PREMATURE: run Co-IP, TSA, and functional assays first.'} pLI={gnomad.get('pLI','?')}."},
            {"n": 5, "name": f"Drug Analogue Screen {'(SM tractable)' if ot_d.get('sm_tractable') else '(Fragment-based)'}", "cost": f"${'40,000–80,000' if ot_d.get('sm_tractable') else '60,000–100,000'}", "time": "8–12 weeks", "p": 65 if druggable and n_path >= 3 else 30, "d": f"{'OpenTargets: small-molecule tractable. Test '+str(ot_d.get('known_drugs',[''])[0] or 'analogue scaffold')+' panel (200–500 compounds).' if ot_d.get('sm_tractable') else 'No confirmed tractability. FBDD: fragments <300 Da, LE>0.3, SPR primary assay.'} Map {vstr} onto AlphaFold binding pocket first."},
        ]
        for exp in exps_top:
            pc = exp["p"]; pc_col = "#22c55e" if pc >= 75 else "#ffd20a" if pc >= 50 else "#ef4444"
            st.markdown(f"""
            <div class="card" style="border-color:rgba(0,212,255,.1)">
              <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px">
                <span style="color:#00d4ff;font-size:.6rem;font-weight:700;font-family:Inter,sans-serif;min-width:16px">#{exp['n']}</span>
                <span style="color:#b8d4e8;font-size:.72rem;font-weight:600;font-family:Inter,sans-serif">{exp['name']}</span>
                <span style="margin-left:auto;color:#2a4060;font-size:.6rem;white-space:nowrap;font-family:Inter,sans-serif">
                  {exp['cost']} · {exp['time']} · <span style="color:{pc_col}">P={pc}%</span>
                </span>
              </div>
              <div class="dim" style="margin-left:24px;line-height:1.65">{exp['d']}</div>
            </div>
            """, unsafe_allow_html=True)

    with cr:
        fns = pdata.get("functions", [])
        if fns: st.markdown(f'<div class="card" style="font-size:.7rem;color:#b8d4e8;line-height:1.75;margin-bottom:8px;font-family:Inter,sans-serif">{fns[0][:340]}</div>', unsafe_allow_html=True)
        locs = pdata.get("subcellular", [])
        if locs: st.markdown('<div style="margin-bottom:8px">' + " ".join(f'<span class="pill">{l}</span>' for l in locs[:6]) + '</div>', unsafe_allow_html=True)

        _sec("gnomAD Constraint")
        if gnomad:
            for lbl2, val, thresh, dh, ex in [("pLI (LoF intolerance)", gnomad.get("pLI"), 0.9, "high", "pLI>0.9 = essential gene"), ("o/e LoF", gnomad.get("lof_oe"), 0.35, "low", "o/e<0.35 = constrained"), ("o/e Missense", gnomad.get("missense_oe"), 0.6, "low", "o/e<0.6 = intolerant")]:
                if val is None: continue
                good = (val > thresh if dh == "high" else val < thresh)
                col2 = "#00d4ff" if good else "#2a4060"
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #070d14"><div><span style="font-size:.69rem;color:#5a7590;font-family:Inter,sans-serif">{lbl2}</span><br><span class="dim">{ex}</span></div><span style="color:{col2};font-family:JetBrains Mono,monospace;font-size:.76rem;font-weight:600">{val:.3f}{"✓" if good else ""}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<a class="pill" href="https://gnomad.broadinstitute.org/gene/{gene}" target="_blank">gnomAD ↗</a>', unsafe_allow_html=True)
        else: st.markdown('<div class="dim">gnomAD not available.</div>', unsafe_allow_html=True)

        _sec("Binding Sites & Chemistry")
        binding_s = pdata.get("binding_sites", []); phospho_s = pdata.get("phospho_sites", [])
        if binding_s:
            for bs in binding_s[:6]:
                tc = {"ACT_SITE": "#ffd20a", "BINDING": "#22c55e", "METAL": "#ffd20a", "DNA_BIND": "#6366f1"}.get(bs["type"], "#3a5570")
                st.markdown(f'<div style="display:flex;gap:5px;padding:3px 0;border-bottom:1px solid #070d14"><span style="color:{tc};font-size:.59rem;min-width:66px;font-weight:600;font-family:Inter,sans-serif">{bs["type"]}</span><span style="color:#8ab0c8;font-size:.68rem;font-family:Inter,sans-serif">{bs.get("name","")[:35]}</span><span class="dim" style="margin-left:auto">Pos {bs.get("start","?")}–{bs.get("end","?")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<a class="pill" href="https://www.uniprot.org/uniprotkb/{acc}/entry#function" target="_blank">UniProt ↗</a>', unsafe_allow_html=True)
        if phospho_s:
            st.markdown(f'<div style="color:#f97316;font-size:.64rem;margin:5px 0;font-family:Inter,sans-serif">{len(phospho_s)} phosphorylation sites annotated</div>', unsafe_allow_html=True)
            for ps in phospho_s[:4]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #070d14"><span style="color:#f97316">Pos {ps["position"]}</span> — {ps["name"][:40]}</div>', unsafe_allow_html=True)
        if not binding_s and not phospho_s: st.markdown('<div class="dim">No binding site annotations in UniProt.</div>', unsafe_allow_html=True)

        drugs = ot_d.get("known_drugs", []) or [d["drug"] for d in dgidb[:5]]
        if drugs:
            _sec("Known Drugs")
            st.markdown(" ".join(f'<span class="pill">💊 {d}</span>' for d in drugs[:8]), unsafe_allow_html=True)
        if trials:
            _sec("Active Clinical Trials")
            for t in trials[:3]: st.markdown(f'<div class="dim" style="padding:3px 0;border-bottom:1px solid #070d14"><a href="{t["url"]}" target="_blank" style="color:#00d4ff">{t["nct_id"]}</a> · Phase {t["phase"]} · {t["title"][:55]}</div>', unsafe_allow_html=True)
        if string_d:
            _sec("Interaction Partners")
            for p in string_d[:6]: st.markdown(f'<div style="display:flex;gap:5px;padding:3px 0;border-bottom:1px solid #070d14;font-family:Inter,sans-serif"><span style="color:#00d4ff;font-family:JetBrains Mono,monospace;font-size:.69rem;min-width:60px">{p["partner"]}</span><span class="dim">score {p["score"]:.2f}{" · exp" if p.get("experimental",0)>0.3 else ""}</span></div>', unsafe_allow_html=True)

        # Domain-specific panel
        if domain == "Neuroscience":
            _sec("Neuroscience Context", "#6366f1")
            neuro_kws = ["synap", "neurot", "dopamin", "seroton", "glutam", "gaba", "acetylcholin", "receptor", "ion channel"]
            hit = [k for k in neuro_kws if k in " ".join(pdata.get("functions", []) + pdata.get("keywords", [])).lower()]
            st.markdown(f'<div class="card" style="border-color:rgba(99,102,241,.2)"><div style="color:#6366f1;font-size:.66rem;font-weight:600;margin-bottom:4px;font-family:Inter,sans-serif">NEURAL RELEVANCE</div><div class="dim" style="line-height:1.7">{"Neural signatures: <b style=\'color:#6366f1\'>" + ", ".join(hit[:4]) + "</b>. CNS drug requirements: cLogP 1–3, MW<450, HBD<3, PSA<90Å², CNS MPO score ≥4. Check BBB penetrance and neuronal subtype expression (Allen Brain Atlas)." if hit else "No direct neural annotation. Verify brain GTEx expression and synaptic proteome databases."}</div></div>', unsafe_allow_html=True)
        elif domain == "Cancer Biology":
            _sec("Oncology Context", "#f43f5e")
            som = [d for d in diseases if d.get("inheritance") == "Somatic"]; germ = [d for d in diseases if d.get("inheritance") != "Somatic"]
            st.markdown(f'<div class="card" style="border-color:rgba(244,63,94,.2)"><div style="font-size:.69rem;color:#b8d4e8;font-family:Inter,sans-serif"><b style="color:#f43f5e">Somatic:</b> {len(som)} · <b style="color:#6366f1">Germline:</b> {len(germ)}<br>CRITICAL ClinVar variants with ≥2 stars: {n_crit}.<br>{"Potential companion diagnostic: ctDNA panel for " + vstr if top_v else "Insufficient variant density for companion diagnostic."}</div></div>', unsafe_allow_html=True)
        elif domain == "Pharmaceuticals":
            _sec("Drug Development Context", "#00d4ff")
            st.markdown(f'<div class="card" style="border-color:rgba(0,212,255,.12)"><div class="dim" style="line-height:1.7">SM tractable: <b style="color:{"#22c55e" if ot_d.get("sm_tractable") else "#3a5570"}">{"Yes" if ot_d.get("sm_tractable") else "No"}</b> · Antibody: <b style="color:{"#22c55e" if ot_d.get("ab_tractable") else "#3a5570"}">{"Yes" if ot_d.get("ab_tractable") else "No"}</b><br>{"GPCR: Full H8-Filamin coupling protocol. Ser2152-P IP is the receptor-proximal readout (PMID:26124276). ~300/800 Class A GPCRs carry H8 FBM." if is_gpcr else "Non-GPCR: PPI inhibitor or kinase/allosteric strategy."}</div></div>', unsafe_allow_html=True)

    # Papers at bottom
    if papers:
        _sec("Evidence-Tiered Literature")
        for p in papers[:10]: st.markdown(f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #070d14;align-items:baseline"><span style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;border-radius:3px;min-width:52px;text-align:center;font-size:.58rem;padding:1px 5px;white-space:nowrap;font-family:Inter,sans-serif">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#5a7590;font-size:.68rem;flex:1;font-family:Inter,sans-serif">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:16]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)


# ─── TAB 1: TRIAGE ────────────────────────────────────────
with t1:
    cl, cr = st.columns([1.1, .9], gap="large")
    with cl:
        _sec("AlphaFold Structure — Pathogenic Variant Spheres")
        vw2 = st.radio("t1v", ["pLDDT", "Spectrum", "Surface", "Stick"], horizontal=True, label_visibility="collapsed", key="t1_vw")
        sp2 = st.checkbox("Spin", key="t1_sp")
        _viewer3d(pdb, cv=cv, style={"pLDDT": "plddt", "Spectrum": "spectrum", "Surface": "surface", "Stick": "stick"}[vw2], height=400, spin=sp2, show_v=True)

        _sec("Mutation Dynamics — All Variants by Position")
        if cv:
            sl = pdata.get("seq_len", 500)
            fig_m = go.Figure()
            fig_m.add_trace(go.Scatter(x=[0, sl], y=[0, 0], mode="lines", line=dict(color="#0f1e2d", width=7), hoverinfo="none", showlegend=False))
            for dom_f in pdata.get("domains", [])[:8]:
                try:
                    s = int(dom_f.get("start", "0")); en = int(dom_f.get("end", "0"))
                    if s and en:
                        fig_m.add_shape(type="rect", x0=s, x1=en, y0=-0.3, y1=0.3, fillcolor="rgba(0,212,255,.05)", line=dict(color="rgba(0,212,255,.15)", width=1))
                        fig_m.add_annotation(x=(s + en) / 2, y=0.5, text=dom_f.get("name", "")[:10], showarrow=False, font=dict(size=7, color="#2a4060", family="Inter"))
                except: pass
            for cls, col, yp, sz in [("CRITICAL", "#ff2d55", 1.0, 11), ("HIGH", "#ff8c42", 0.6, 8), ("MODERATE", "#ffd20a", -0.5, 6), ("LOW", "#2a4060", -0.85, 4)]:
                grp = [v for v in cv if v.get("ml_class") == cls and v.get("position", 0) > 0]
                if grp:
                    fig_m.add_trace(go.Scatter(x=[v["position"] for v in grp], y=[yp] * len(grp), mode="markers", marker=dict(size=sz, color=col, line=dict(color="#020609", width=1), opacity=0.9), text=[f"{v.get('protein_change','?')}<br>{', '.join(v.get('conditions',[])[:1])[:40]}<br>Source: {v.get('source','ClinVar')}" for v in grp], hoverinfo="text", name=cls))
            fig_m.update_layout(height=195, plot_bgcolor="#020609", paper_bgcolor="#020609", xaxis=dict(title="Residue Position", gridcolor="#070d14", color="#2a4060", range=[0, sl], tickfont=dict(size=8, family="JetBrains Mono")), yaxis=dict(tickvals=[1, .6, -.5, -.85], ticktext=["CRIT", "HIGH", "MOD", "LOW"], color="#2a4060", gridcolor="#070d14", range=[-1.3, 1.3], tickfont=dict(size=8, family="Inter")), font=dict(color="#b8d4e8", size=9, family="Inter"), legend=dict(bgcolor="#040c14", bordercolor="#0f1e2d", font=dict(size=8)), margin=dict(t=8, b=32, l=50, r=8))
            st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<span class="dim">P/LP: {n_path} · VUS: {sum(1 for v in cv if v.get("ml_class")=="MODERATE")} · Total: {len(cv)} variants · ClinVar + UniProt</span>', unsafe_allow_html=True)

    with cr:
        _sec("Disease Associations — Full Detail")
        if diseases:
            st.markdown(f'<div class="card" style="border-color:rgba(0,212,255,.12);margin-bottom:8px"><b style="color:#00d4ff;font-size:.73rem;font-family:Inter,sans-serif">{len(diseases)} disease associations</b> · <span style="color:#ff8c42">{sum(1 for d in diseases if d.get("inheritance")=="Somatic")} Somatic</span> · <span style="color:#6366f1">{sum(1 for d in diseases if d.get("inheritance")!="Somatic")} Germline</span></div>', unsafe_allow_html=True)
            for d in diseases[:10]:
                nm = d.get("name", "?"); inh = d.get("inheritance", "?"); desc = d.get("desc", "")[:180]
                cc = "#ff8c42" if inh == "Somatic" else "#6366f1"
                with st.expander(f"[{inh}] {nm[:50]}"):
                    st.markdown(f'<div style="font-size:.69rem;color:#b8d4e8;line-height:1.7;font-family:Inter,sans-serif">{desc or "No description."}</div>', unsafe_allow_html=True)
                    pathotype = ("Somatic GoF/LoF drives clonal expansion. Target: restore tumour suppression or inhibit oncogenic gain." if inh == "Somatic" else "Germline LoF. Consider: gene supplementation, read-through therapy for nonsense, ASO for dominant-negative.")
                    st.markdown(f'<div class="dim" style="margin-top:4px">{pathotype}</div>', unsafe_allow_html=True)
                    if d.get("omim"): st.markdown(f'<a class="pill" href="https://omim.org/entry/{d["omim"]}" target="_blank">OMIM ↗</a>', unsafe_allow_html=True)
        else: st.markdown('<div class="dim" style="padding:8px">No disease associations. Check gnomAD pLI and STRING partners before deprioritising.</div>', unsafe_allow_html=True)

        _sec("Tissue Distribution (GTEx v8)")
        if gtex:
            items = sorted(gtex.items(), key=lambda x: x[1], reverse=True)[:18]
            fig_g = go.Figure(go.Bar(x=[i[1] for i in items], y=[i[0] for i in items], orientation="h", marker_color=["#00d4ff" if i[1] == max(gtex.values()) else "#0f2035" for i in items], hovertemplate="<b>%{y}</b>: %{x:.1f} TPM<extra></extra>"))
            fig_g.update_layout(height=max(280, len(items) * 19), plot_bgcolor="#020609", paper_bgcolor="#020609", xaxis=dict(title="Median TPM", gridcolor="#070d14", color="#2a4060", tickfont=dict(size=8, family="JetBrains Mono")), yaxis=dict(color="#7090a0", autorange="reversed", tickfont=dict(size=9, family="Inter")), font=dict(color="#b8d4e8", size=9), margin=dict(l=140, r=5, t=4, b=26))
            st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        else: st.markdown('<div class="dim">GTEx data not available.</div>', unsafe_allow_html=True)

        _sec("Variant Sphere Triage — Ranked by Severity")
        if path_v:
            for v in path_v[:15]:
                am_h = next((a for a in (am_d or []) if a.get("position") == v.get("position")), None)
                am_tag = " 🟢" if am_h and am_h["score"] >= sens else " 🟡" if am_h else ""
                with st.expander(f'{_badge(v.get("ml_class","LOW"))} {v.get("protein_change","?")[:20]}{am_tag}   {", ".join(v.get("conditions",[])[:1])[:35]}'):
                    st.markdown(f'<div style="font-size:.69rem;line-height:1.7;font-family:Inter,sans-serif"><b style="color:#7090a0">Significance:</b> {v.get("significance","")}<br><b style="color:#7090a0">Stars:</b> {"⭐"*v.get("stars",0) or "Unrated"}<br><b style="color:#7090a0">Conditions:</b> {", ".join(v.get("conditions",[])[:2]) or "Not specified"}<br><b style="color:#7090a0">Source:</b> {v.get("source","ClinVar")}<br>{"<b style=\'color:#7090a0\'>AlphaMissense:</b> "+str(round(am_h["score"],3))+" ("+am_h["class"]+")" if am_h else ""}<br><a href="{v.get("url","#")}" target="_blank" style="color:#00d4ff">View in ClinVar ↗</a></div>', unsafe_allow_html=True)
        else:
            # Domain map when no variants
            sl2 = pdata.get("seq_len", 500); doms2 = pdata.get("domains", [])
            if doms2:
                fig_lin = go.Figure()
                fig_lin.add_trace(go.Scatter(x=[0, sl2], y=[0, 0], mode="lines", line=dict(color="#0f1e2d", width=9), hoverinfo="none", showlegend=False))
                cols_d = ["#00d4ff", "#6366f1", "#f97316", "#22c55e", "#fbbf24", "#f43f5e"]
                for i2, d in enumerate(doms2[:10]):
                    try:
                        s = int(d.get("start", "0")); en = int(d.get("end", "0"))
                        if s and en:
                            fig_lin.add_shape(type="rect", x0=s, x1=en, y0=-0.5, y1=0.5, fillcolor=cols_d[i2 % 6] + "22", line=dict(color=cols_d[i2 % 6], width=1.5))
                            fig_lin.add_annotation(x=(s + en) / 2, y=0.8, text=d.get("name", "")[:12], showarrow=False, font=dict(size=7, color=cols_d[i2 % 6], family="Inter"))
                    except: pass
                fig_lin.update_layout(height=130, plot_bgcolor="#020609", paper_bgcolor="#020609", xaxis=dict(title="Position", gridcolor="#070d14", color="#2a4060", range=[0, sl2], tickfont=dict(size=8)), yaxis=dict(visible=False, range=[-1, 1.2]), font=dict(color="#b8d4e8", size=8), margin=dict(t=28, b=30, l=5, r=5))
                st.plotly_chart(fig_lin, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="dim" style="padding:6px">No pathogenic variants found. Domain map shown. May reflect limited clinical ascertainment — cross-reference OMIM.</div>', unsafe_allow_html=True)


# ─── TAB 2: PROTEIN EXPLORER ─────────────────────────────
with t2:
    cl, cr = st.columns([1.3, .7], gap="large")
    with cl:
        _sec("Protein Backbone — Click Residue for Full Analysis")
        vw3 = st.radio("t2v", ["pLDDT", "Spectrum", "Surface", "Stick"], horizontal=True, label_visibility="collapsed", key="t2_vw")
        sp3 = st.checkbox("Spin", key="t2_sp")
        _viewer3d(pdb, cv=cv, style={"pLDDT": "plddt", "Spectrum": "spectrum", "Surface": "surface", "Stick": "stick"}[vw3], height=430, spin=sp3, show_v=True, binding=pdata.get("binding_sites", []))

        _sec("Genetic Skeleton — Domain Architecture")
        doms = pdata.get("domains", [])
        if doms:
            st.markdown(f'<div class="dim" style="margin-bottom:5px">{pdata.get("seq_len",0):,} amino acids · {pdata.get("mw_kda",0):.1f} kDa · {len(doms)} annotated features</div>', unsafe_allow_html=True)
            for dom in doms[:14]:
                tc = {"DOMAIN": "#00d4ff", "ACT_SITE": "#ffd20a", "BINDING": "#22c55e", "METAL": "#ffd20a", "DNA_BIND": "#6366f1", "REGION": "#f97316", "MOTIF": "#64748b"}.get(dom["type"], "#3a5570")
                st.markdown(f'<div style="display:flex;gap:6px;padding:3px 0;border-bottom:1px solid #070d14"><span style="color:{tc};font-size:.59rem;font-weight:600;min-width:72px;font-family:Inter,sans-serif">{dom["type"]}</span><div><span style="color:#8ab0c8;font-size:.68rem;font-family:Inter,sans-serif">{dom.get("name","")[:45]}</span><span class="dim" style="margin-left:5px">Pos {dom.get("start","?")}–{dom.get("end","?")}</span></div></div>', unsafe_allow_html=True)

        _sec("Phosphorylation & Kinase/Phosphatase Biology")
        phospho_t = pdata.get("phospho_sites", []); ptms_t = pdata.get("ptms", [])
        if is_filamin:
            st.markdown('<div class="card" style="border-color:rgba(249,115,22,.2)"><b style="color:#f97316;font-family:Inter,sans-serif">FILAMIN A — Ser2152 Phosphorylation Hub</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">Ser2152 is the functionally dominant phosphorylation site on FLNA (PhosphoSite DB). PKA phosphorylates Ser2152 upon GPCR activation. This is more receptor-proximal than cAMP, IP3, or beta-arrestin. Pathogenic variant R2149Q (periventricular nodular heterotopia) directly validates this Ig21 domain site. Only FLNA (not FLNB/C) carries this site. PMID:26124276.</div></div>', unsafe_allow_html=True)
        elif is_kinase:
            st.markdown('<div class="card" style="border-color:rgba(34,197,94,.2)"><b style="color:#22c55e;font-family:Inter,sans-serif">KINASE — Catalytic Phosphotransferase</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">Phosphorylates substrates on Ser/Thr or Tyr. Pathogenic GoF variants hyperactivate substrate phosphorylation; LoF variants abolish catalytic activity. Drug strategy: ATP-competitive (DFG-in), allosteric/Type II (DFG-out), or covalent Cys-targeting inhibitor. Check activation loop variants first.</div></div>', unsafe_allow_html=True)
        elif is_pase:
            st.markdown('<div class="card" style="border-color:rgba(251,191,36,.2)"><b style="color:#fbbf24;font-family:Inter,sans-serif">PHOSPHATASE — Dephosphorylation Activity</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">Removes phosphate from substrates. LoF variants lead to substrate hyperphosphorylation and pathway overactivation. Drug strategy: phosphatase activator or upstream kinase inhibitor to reduce substrate burden.</div></div>', unsafe_allow_html=True)
        if phospho_t:
            st.markdown(f'<div style="color:#f97316;font-size:.64rem;margin:5px 0;font-family:Inter,sans-serif">{len(phospho_t)} UniProt-annotated phosphorylation sites:</div>', unsafe_allow_html=True)
            for ps in phospho_t[:8]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #070d14"><span style="color:#f97316">Pos {ps["position"]}</span> — {ps["name"][:45]}</div>', unsafe_allow_html=True)
        for pt in ptms_t[:2]: st.markdown(f'<div class="dim" style="padding:2px 0;line-height:1.6">{pt[:100]}</div>', unsafe_allow_html=True)
        if not phospho_t and not ptms_t and not is_filamin and not is_kinase and not is_pase: st.markdown('<div class="dim">No phosphorylation annotations in UniProt.</div>', unsafe_allow_html=True)

        _sec("Interaction Partners — What Each Means")
        if string_d:
            for p in string_d[:10]:
                ec = p.get("experimental", 0); col_p = "#00d4ff" if ec > 0.5 else "#22c55e" if p["score"] > 0.8 else "#3a5570"
                with st.expander(f'{p["partner"]}  ·  score {p["score"]:.2f}{"  · experimentally confirmed" if ec > 0.3 else ""}'):
                    st.markdown(f'<div class="dim" style="line-height:1.7">Combined STRING score: <b style="color:{col_p}">{p["score"]:.3f}</b>. {"Experimental evidence (co-IP/affinity/reconstitution): score " + str(ec) + ". High-confidence physical interaction." if ec > 0.3 else "Co-expression and text-mining prediction."}<br><br>Implication: perturbation of {gene} may alter {p["partner"]} activity. Check: (1) shared disease phenotypes in OMIM, (2) whether {p["partner"]} has independent P/LP variants overlapping {gene} phenotypes, (3) AlphaFold-Multimer interface prediction for drug target zone.</div>', unsafe_allow_html=True)
        else: st.markdown('<div class="dim">STRING network not available.</div>', unsafe_allow_html=True)

        if is_gpcr:
            _sec("GPCR Coupling Animation", "#00d4ff")
            components.html(f"""<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>body{{margin:0;background:#020609;display:flex;align-items:center;justify-content:center;height:220px;overflow:hidden;font-family:Inter,sans-serif}}</style>
<canvas id="cv" width="500" height="210"></canvas>
<script>
const c=document.getElementById('cv'),x=c.getContext('2d');
let t=0;
const parts=[
  {{x:80,y:105,r:38,label:'{gene[:6]}\\nGPCR',color:'#00d4ff',freq:1,amp:5}},
  {{x:200,y:85,r:26,label:'H8\\ndislodges',color:'#6366f1',freq:1.4,amp:8}},
  {{x:300,y:105,r:30,label:'FLNA\\nIg21',color:'#f97316',freq:.9,amp:7}},
  {{x:400,y:100,r:22,label:'PKA→\\nSer2152-P',color:'#22c55e',freq:1.2,amp:5}},
];
const agonist={{x:30,y:105,r:8,color:'#ffd20a'}};
function dr(){{
  x.clearRect(0,0,500,210);
  // Draw agonist moving
  const ax=agonist.x+Math.min(t*40,55);
  x.beginPath();x.arc(ax,agonist.y,agonist.r,0,Math.PI*2);
  x.fillStyle='#ffd20a44';x.fill();x.strokeStyle='#ffd20a';x.lineWidth=1.5;x.stroke();
  x.fillStyle='#ffd20a';x.font='7px Inter';x.textAlign='center';x.fillText('Agonist',ax,agonist.y+16);
  // Connections
  parts.forEach((a,i)=>{{if(i<parts.length-1){{
    const bx=parts[i+1].x+Math.sin(t*parts[i+1].freq+i+1)*parts[i+1].amp;
    const by=parts[i+1].y+Math.cos(t*parts[i+1].freq)*parts[i+1].amp*.5;
    const ax2=a.x+Math.sin(t*a.freq+i)*a.amp,ay=a.y+Math.cos(t*a.freq)*a.amp*.5;
    x.beginPath();x.moveTo(ax2,ay);x.lineTo(bx,by);
    x.strokeStyle='rgba(0,212,255,.2)';x.lineWidth=2;x.stroke();
    // Signal pulse
    const prog=(Math.sin(t*2+i)*.5+.5);
    const px2=ax2+(bx-ax2)*prog,py=ay+(by-ay)*prog;
    x.beginPath();x.arc(px2,py,3.5,0,Math.PI*2);x.fillStyle='#00d4ff88';x.fill();
  }}}});
  // Draw domains
  parts.forEach((d,i)=>{{
    const dx=d.x+Math.sin(t*d.freq+i)*d.amp,dy=d.y+Math.cos(t*d.freq)*d.amp*.5;
    x.beginPath();x.arc(dx,dy,d.r,0,Math.PI*2);
    x.fillStyle=d.color+'18';x.fill();x.strokeStyle=d.color;x.lineWidth=1.5;x.stroke();
    x.fillStyle=d.color;x.font='bold 8px Inter';x.textAlign='center';
    d.label.split('\\n').forEach((ln,li)=>x.fillText(ln,dx,dy-5+li*11));
  }});
  // Labels
  x.fillStyle='#2a4060';x.font='7px Inter';x.textAlign='center';
  x.fillText('Agonist activates → H8 dislodges → FLNA Ig21 binds → PKA phosphorylates Ser2152 | PMID:26124276',250,200);
  t+=0.022;requestAnimationFrame(dr);
}}
dr();
</script>""", height=220, scrolling=False)

        if am_d:
            _sec("AlphaMissense Pathogenicity Landscape")
            sample = am_d[::max(1, len(am_d) // 500)]
            fig_am = go.Figure()
            fig_am.add_trace(go.Scatter(x=[a["position"] for a in sample], y=[a["score"] for a in sample], mode="markers", marker=dict(size=2.5, color=["#ff2d55" if a["score"] >= 0.564 else "#0f2035" for a in sample], opacity=0.7), hovertemplate="Pos %{x}: %{y:.3f}<extra></extra>"))
            pcv = [v for v in cv if v.get("position") and v.get("ml_class") in ("CRITICAL", "HIGH")]
            if pcv: fig_am.add_trace(go.Scatter(x=[v["position"] for v in pcv], y=[0.564] * len(pcv), mode="markers", marker=dict(size=9, symbol="star", color="#ff8c42"), hovertext=[v.get("protein_change", "?") for v in pcv], hoverinfo="text", name="ClinVar P/LP"))
            fig_am.add_hline(y=0.564, line_dash="dash", line_color="#ffd20a", annotation_text="0.564 (pathogenic threshold)", annotation_font=dict(size=9, color="#ffd20a"))
            fig_am.update_layout(height=220, plot_bgcolor="#020609", paper_bgcolor="#020609", xaxis=dict(title="Residue Position", gridcolor="#070d14", color="#2a4060", tickfont=dict(size=8, family="JetBrains Mono")), yaxis=dict(title="AM Score", gridcolor="#070d14", color="#2a4060", range=[0, 1], tickfont=dict(size=8)), font=dict(color="#b8d4e8", size=9, family="Inter"), legend=dict(bgcolor="#040c14", bordercolor="#0f1e2d", font=dict(size=8)), margin=dict(t=10, b=32, l=45, r=8))
            st.plotly_chart(fig_am, use_container_width=True, config={"displayModeBar": False})
            n_am_p = sum(1 for a in am_d if a["score"] >= 0.564)
            st.markdown(f'<span class="dim">Pathogenic positions (≥0.564): <b style="color:#ff2d55">{n_am_p}</b> / {len(am_d)} · ClinVar-AM concordant: {concordant}</span>', unsafe_allow_html=True)

    with cr:
        _sec("Residue Inspector")
        seq_x = pdata.get("sequence", ""); sl_x = pdata.get("seq_len", 0)
        if seq_x and sl_x:
            pos = st.number_input("Residue position", 1, max(1, sl_x), min(50, sl_x), key="res_pos")
            if 1 <= pos <= sl_x:
                aa = seq_x[pos - 1].upper(); pr = AA.get(aa, ("?", 0, 0)); pv = pld.get(pos, 0)
                pc2 = "#00b8d9" if pv >= 90 else "#22d3a0" if pv >= 70 else "#f5c842" if pv >= 50 else "#e05c5c"
                st.markdown(f"""
                <div class="card">
                  <span style="color:#00d4ff;font-family:JetBrains Mono,monospace;font-size:.92rem;font-weight:700">{aa}{pos}</span>
                  <span class="dim"> — {pr[0]}</span>
                  <table style="width:100%;font-size:.69rem;margin-top:6px">
                    <tr><td class="dim">Hydrophobicity</td><td style="color:#b8d4e8;font-family:JetBrains Mono,monospace">{pr[1]}</td></tr>
                    <tr><td class="dim">Charge</td><td style="color:#b8d4e8;font-family:JetBrains Mono,monospace">{pr[2]:+}</td></tr>
                    <tr><td class="dim">pLDDT</td><td style="color:{pc2};font-family:JetBrains Mono,monospace">{pv:.1f}</td></tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)
                for v in [v for v in cv if v.get("position") == pos][:2]:
                    bc = "#ff2d55" if v.get("ml_class") == "CRITICAL" else "#ff8c42"
                    st.markdown(f'<div style="background:{bc}0a;border-left:2px solid {bc};padding:5px 8px;margin:3px 0;border-radius:4px;font-size:.69rem;color:#b8d4e8;font-family:Inter,sans-serif">{v.get("significance","")} · {", ".join(v.get("conditions",[])[:1])[:40]}</div>', unsafe_allow_html=True)

                _sec("If Mutated — Structural & Genomic Impact")
                new_aa = st.selectbox("Substitute to:", sorted([k for k in AA if k != aa]), key="mut_aa")
                if new_aa:
                    npr = AA.get(new_aa, ("?", 0, 0)); dh = abs(npr[1] - pr[1]); dc = abs(npr[2] - pr[2])
                    score = min(100, int(dh * 8 + dc * 25))
                    ic = "#ff2d55" if score >= 70 else "#ff8c42" if score >= 40 else "#ffd20a" if score >= 15 else "#3a5570"
                    il = "Likely Damaging" if score >= 70 else "Possibly Damaging" if score >= 40 else "Moderate" if score >= 15 else "Likely Benign"
                    imps = []
                    if dc > 0: imps.append("Charge change — disrupts salt bridges and electrostatic protein-protein interfaces")
                    if dh > 3: imps.append("Major hydrophobicity shift — affects core packing or membrane insertion")
                    if new_aa == "P": imps.append("Proline introduces backbone rigidity — breaks α-helix or β-sheet")
                    if aa == "C" or new_aa == "C": imps.append("Cysteine involved — disulfide bond disruption or aberrant Cys creation")
                    if aa == "G" or new_aa == "G": imps.append("Glycine flexibility changed — alters local backbone dynamics")
                    am_mut = [a for a in (am_d or []) if a.get("position") == pos and a.get("alt") == new_aa]
                    st.markdown(f"""
                    <div class="card" style="border-color:{ic}30">
                      <span style="color:{ic};font-family:JetBrains Mono,monospace;font-size:.88rem;font-weight:700">{aa}{pos}{new_aa}</span>
                      <span class="dim" style="margin-left:7px">{il} · {score}/100</span>
                      <div style="margin-top:6px;font-size:.68rem;color:#5a7590;font-family:Inter,sans-serif">Δhydrophobicity {dh:.1f} · Δcharge {dc:+.0f}</div>
                      {"".join(f'<div class="dim" style="margin-top:2px;font-family:Inter,sans-serif">▸ {i}</div>' for i in imps)}
                      {"<div style='color:#ff2d55;font-size:.65rem;margin-top:4px;font-family:Inter,sans-serif'>AlphaMissense: " + str(round(am_mut[0]['score'],3)) + " (" + am_mut[0]['class'] + ")</div>" if am_mut else ""}
                    </div>
                    """, unsafe_allow_html=True)
        else: st.markdown('<div class="dim">Sequence data not available.</div>', unsafe_allow_html=True)


# ─── TAB 3: EXPERIMENTS ───────────────────────────────────
with t3:
    _sec("Experiment Triage — Color-Coded Priority")
    st.markdown('<div style="display:flex;gap:7px;margin-bottom:10px"><span style="background:rgba(34,197,94,.12);color:#22c55e;border:1px solid rgba(34,197,94,.3);border-radius:4px;padding:2px 9px;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif">🟢 PURSUE</span><span style="background:rgba(255,210,10,.07);color:#ffd20a;border:1px solid rgba(255,210,10,.25);border-radius:4px;padding:2px 9px;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif">🟡 CAUTION</span><span style="background:rgba(239,68,68,.08);color:#ef4444;border:1px solid rgba(239,68,68,.2);border-radius:4px;padding:2px 9px;font-size:.62rem;font-weight:600;font-family:Inter,sans-serif">🔴 AVOID</span></div>', unsafe_allow_html=True)

    EXPS = [
        {"name": "AlphaFold-Multimer (ColabFold)", "cost": "Free", "time": "0.5w", "p": 80, "pr": "PURSUE",
         "details": f"Model {gene}:{partners[0] if partners else 'STRING partner'} complex. ipTM>0.8 = high-confidence interface. Map {vstr} onto predicted binding site before any wet-lab expenditure. Identifies druggable pockets. Also run FoldDock for protein-protein docking.",
         "focus": f"CRITICAL variants {top_v[0] if top_v else 'all P/LP'} at interface residues.",
         "neglect": "Benign polymorphisms. Variants >15 Å from predicted interface.",
         "hypo": "If ipTM>0.8 → Co-IP + TSA justified. If ipTM<0.5 → interaction likely indirect → modify hypothesis.",
         "cite": "Jumper et al. Nature 2021 PMID:34265844; Evans et al. Science 2022 PMID:36265909"},
        {"name": f"Filamin Ser2152-P IP Assay {'★ GPCR Primary Readout' if is_gpcr else '(GPCR only)'}", "cost": "$400–800", "time": "1w", "p": 90 if (is_gpcr or is_filamin) else 20, "pr": "PURSUE" if (is_gpcr or is_filamin) else "AVOID",
         "details": f"{'GPCR confirmed. Agonist (EC80) → 10 min → lyse → anti-FLNA IP → pSer2152 western. WT vs '+vstr+'. Cell: '+cell_type+'. More receptor-proximal than cAMP/IP3/arrestin. Cardiac GPCRs only for TMAO rattling assay.' if (is_gpcr or is_filamin) else gene+' is not a GPCR — this assay is not applicable.'}",
         "focus": "Pathogenic variants in TM helices and H8 domain. R2149Q-equivalent positions." if (is_gpcr or is_filamin) else "N/A",
         "neglect": "ARRB2 co-IP as primary disease evidence — DKO mice have no phenotype.",
         "hypo": f"If WT Ser2152-P+ and {top_v[0] if top_v else 'variant'} Ser2152-P− → receptor coupling disrupted → therapeutic target confirmed → advance to cAMP HTRF + HTS.",
         "cite": "Nakamura et al. JBC 2015 PMID:26124276"},
        {"name": "ADP-Glo Kinase Activity Assay", "cost": "$1,200–2,000", "time": "2w", "p": 88 if is_kinase else 20, "pr": "PURSUE" if is_kinase else "AVOID",
         "details": f"{'Kinase confirmed. ADP-Glo luminescent assay. Compare Vmax and Km WT vs '+vstr+'. Determines GoF (hyperactivating) vs LoF (kinase-dead) — critical: different mechanisms require completely different drug strategies.' if is_kinase else gene+' is not a kinase — this assay is not appropriate.'}",
         "focus": "DFG motif variants, activation loop, ATP-binding pocket variants.",
         "neglect": "Regulatory domain variants unless studying autoinhibition release.",
         "hypo": "GoF kinase → ATP-competitive or allosteric inhibitor (>70 FDA-approved precedents). LoF kinase → restore function or target downstream effector.",
         "cite": "Anastassiadis et al. Nat Biotechnol 2011 PMID:22037378"},
        {"name": f"Thermal Stability Assay (DSF/TSA) — WT vs {top_v[0] if top_v else 'variants'}", "cost": "$800–1,500", "time": "1–2w", "p": 75, "pr": "PURSUE",
         "details": f"Differential scanning fluorimetry (SYPRO Orange). WT vs {vstr}. ΔTm>3°C = structurally destabilising. Correlate with AlphaMissense score ≥{sens:.2f}. Use as primary screen for compound engagement (thermal shift = binding confirmed). Plate-based, 384-well capable.",
         "focus": f"CRITICAL/HIGH variants. AM-concordant positions (score ≥{sens:.2f}).",
         "neglect": "VUS without structural evidence. Benign variants.",
         "hypo": f"WT Tm − variant Tm = ΔTm. If ΔTm>3°C → structural destabilisation → structural drug strategy. If ΔTm<1°C → functional mechanism elsewhere → PPI or allosteric assay next.",
         "cite": "Niesen et al. Nat Protocols 2007 PMID:17853878"},
        {"name": f"Co-IP — {gene} + {partners[0] if partners else 'TOP PARTNER'}", "cost": "$500–900", "time": "1w", "p": 78, "pr": "PURSUE",
         "details": f"FLAG-{gene} WT and {vstr}. Anti-FLAG immunoprecipitation. Western blot for {partners[0] if partners else 'STRING partner'}. STRING combined score {partners[0] if string_d else 'N/A'} (score={string_d[0]['score']:.2f} if string_d else '?'). Variant that abolishes co-IP identifies therapeutic interface.",
         "focus": f"Variants at AlphaFold-Multimer predicted interface. {vstr}.",
         "neglect": "Variants outside interaction domain. Single-residue substitutions far from interface.",
         "hypo": f"If co-IP lost in {top_v[0] if top_v else 'variant'} → PPI interface confirmed → design inhibitor. If co-IP preserved → variant acts through other mechanism → functional/enzymatic assay next.",
         "cite": f"STRING-DB Szklarczyk et al. 2023 PMID:36370105"},
        {"name": f"CRISPR Knock-in {top_v[0] if top_v else 'P/LP variant'} in {cell_type}", "cost": "$12,000–20,000", "time": "10–14w", "p": 65 if n_crit >= 2 and concordant >= 1 else 20, "pr": "PURSUE" if n_crit >= 2 and concordant >= 1 else "AVOID",
         "details": f"{'JUSTIFIED: '+str(n_crit)+' CRITICAL ClinVar variants + '+str(concordant)+' AlphaMissense-concordant positions. Knock-in '+vstr+' into '+cell_type+'. pLI='+str(gnomad.get('pLI','?'))+' — '+('handle carefully, essential gene.' if gnomad.get('essential') else 'not highly constrained.')  if n_crit>=2 and concordant>=1 else 'PREMATURE: only '+str(n_crit)+' CRITICAL variants and '+str(concordant)+' AM-concordant. Run experiments 1–5 first to build evidence base.'}",
         "focus": "CRITICAL variants with ≥2 ClinVar review stars. AM-concordant positions.",
         "neglect": "VUS variants. Single-submitter pathogenic variants without functional validation.",
         "hypo": "If CRISPR cells show disease phenotype → causal validation complete → advance to drug discovery. Rescue with WT construct → confirms mechanism → HTS justified.",
         "cite": "Anzalone et al. Nature 2019 (prime editing) PMID:31634902; Richardson et al. Nat Biotechnol 2016 PMID:26780180"},
        {"name": f"Drug Analogue Screen / Fragment-Based HTS", "cost": "$40,000–100,000", "time": "8–12w", "p": 65 if druggable and n_path >= 3 else 30, "pr": "PURSUE" if druggable and n_path >= 3 else "CAUTION",
         "details": f"{'OpenTargets confirms tractability. '+('Test '+str(ot_d.get('known_drugs',[''])[0] or 'compound')+'analogue panel (200–500 cpds) at AlphaFold binding pocket.' if ot_d.get('known_drugs') else 'FBDD: fragments <300 Da, LE>0.3, SPR primary assay.')+' Map '+vstr+' onto AlphaFold structure to confirm target engagement at variant sites.' if druggable else 'No confirmed tractability. Establish target mechanism via assays 1–5 first, then fragment screen at AlphaFold pocket.'}",
         "focus": f"Druggable pockets near pathogenic variant clusters. {vstr} positions.",
         "neglect": "Diffuse variant distribution with no pocket. Variants outside predicted binding sites.",
         "hypo": "Fragment hit (KD<1mM, LE>0.3) → SAR campaign → lead (IC50<1µM) → clinical candidate. Selectivity vs off-targets → IND filing ~5–8y.",
         "cite": "OpenTargets Ochoa et al. 2021 PMID:32516411; Freshour et al. 2021 PMID:33237278"},
    ]

    for exp in EXPS:
        pr = exp["pr"]; pc = exp["p"]
        border_col = "rgba(34,197,94,.3)" if pr == "PURSUE" else "rgba(255,210,10,.25)" if pr == "CAUTION" else "rgba(239,68,68,.2)"
        em = "🟢" if pr == "PURSUE" else "🟡" if pr == "CAUTION" else "🔴"
        pc_col = "#22c55e" if pc >= 70 else "#ffd20a" if pc >= 45 else "#ef4444"
        with st.expander(f"{em} {exp['name']}  —  {exp['cost']}  ·  {exp['time']}  ·  P={pc}%"):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Cost", exp["cost"][:12]); m2.metric("Timeline", exp["time"]); m3.metric("P(success)", f"{pc}%"); m4.metric("Priority", pr)
            st.markdown(f'<div style="font-size:.7rem;color:#b8d4e8;line-height:1.75;margin:7px 0;font-family:Inter,sans-serif">{exp["details"]}</div>', unsafe_allow_html=True)
            c1e, c2e = st.columns(2)
            with c1e: st.markdown(f'<div style="background:rgba(34,197,94,.05);border:1px solid rgba(34,197,94,.2);border-radius:5px;padding:7px 10px"><div style="color:#22c55e;font-size:.6rem;font-weight:600;margin-bottom:3px;font-family:Inter,sans-serif">✅ FOCUS ON</div><div class="dim" style="line-height:1.6">{exp["focus"]}</div></div>', unsafe_allow_html=True)
            with c2e: st.markdown(f'<div style="background:rgba(239,68,68,.04);border:1px solid rgba(239,68,68,.15);border-radius:5px;padding:7px 10px"><div style="color:#ef4444;font-size:.6rem;font-weight:600;margin-bottom:3px;font-family:Inter,sans-serif">🛑 NEGLECT</div><div class="dim" style="line-height:1.6">{exp["neglect"]}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.15);border-radius:5px;padding:7px 10px;margin-top:5px"><div style="color:#00d4ff;font-size:.6rem;font-weight:600;margin-bottom:3px;font-family:Inter,sans-serif">🔄 HYPOTHESIS TREE — If X → Then Y</div><div class="dim" style="line-height:1.65">{exp["hypo"]}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dim" style="margin-top:4px">📖 {exp["cite"]}</div>', unsafe_allow_html=True)
            if pr == "PURSUE": st.success("High priority — run this experiment.")
            elif pr == "AVOID": st.error("Premature or not applicable — insufficient evidence at this stage.")

    if papers:
        _sec("Literature by Experiment Type")
        tg = {}
        for p in papers: tg.setdefault(p["tier_label"], []).append(p)
        for tlbl, tp in sorted(tg.items(), key=lambda x: x[1][0]["tier"]):
            with st.expander(f"{tlbl} ({len(tp)} papers)", expanded=tlbl in ("RCT", "Functional")):
                for p in tp: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #070d14"><a href="{p["url"]}" target="_blank" style="color:#5a7590;font-size:.68rem;font-family:Inter,sans-serif">{p["title"][:100]}</a> · {p["authors"][:16]} · {p["journal"]} {p["year"]} · PMID:{p["pmid"]}</div>', unsafe_allow_html=True)

    if trials:
        _sec("Active Clinical Trials")
        for t in trials: st.markdown(f'<div class="dim" style="padding:3px 0;border-bottom:1px solid #070d14"><a href="{t["url"]}" target="_blank" style="color:#00d4ff;font-family:Inter,sans-serif">{t["nct_id"]}</a> · Phase {t["phase"]} · {t["title"][:65]}</div>', unsafe_allow_html=True)


# ─── TAB 4: THERAPEUTIC TARGETS ──────────────────────────
with t4:
    _sec("Druggability & Therapeutic Strategy")
    cl, cr = st.columns([1, .85], gap="large")
    with cl:
        _sec("3D Structure — Druggable Pockets & Binding Sites")
        _viewer3d(pdb, cv=cv, style="surface", height=380, spin=False, show_v=True, binding=pdata.get("binding_sites", []))
        st.markdown('<div class="dim" style="margin-top:3px">🟡 Binding sites  🔴 CRITICAL variants  🟠 HIGH — overlap = primary drug target zone</div>', unsafe_allow_html=True)

        _sec("Druggability Score")
        sm = ot_d.get("sm_tractable", False); ab = ot_d.get("ab_tractable", False); nd = ot_d.get("known_drugs_count", 0)
        ds = sum([sm * 4, ab * 2, min(nd, 5), min(n_path, 5) * 2, int(is_gpcr) * 3, int(is_kinase) * 3])
        dc = "#22c55e" if ds >= 10 else "#ffd20a" if ds >= 5 else "#ef4444"
        st.markdown(f'<div class="card" style="border-color:{dc}30"><div style="display:flex;justify-content:space-between;margin-bottom:7px"><b style="color:{dc};font-family:Inter,sans-serif">Score: {ds}/20</b><span class="dim">{"Highly Druggable" if ds>=10 else "Moderate" if ds>=5 else "Challenging"}</span></div>', unsafe_allow_html=True)
        for lbl2, val2, cc2 in [("Small Molecule Tractable", sm, "#22c55e"), ("Antibody Tractable", ab, "#6366f1"), ("GPCR (34% FDA drugs)", is_gpcr, "#00d4ff"), ("Kinase (>70 FDA drugs)", is_kinase, "#22c55e"), ("Known Drugs in DB", nd > 0, "#ffd20a"), ("Genetic Validation (P/LP≥3)", n_path >= 3, "#ff8c42")]:
            icon2 = "✓" if val2 else "✕"; col2 = cc2 if val2 else "#2a4060"
            st.markdown(f'<div style="display:flex;gap:6px;padding:2px 0;border-bottom:1px solid #070d14;font-size:.68rem;font-family:Inter,sans-serif"><span style="color:{col2};min-width:14px">{icon2}</span><span style="color:#8ab0c8">{lbl2}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        _sec("Protein Dynamics — Conformational Animation")
        components.html(f"""<style>body{{margin:0;background:#020609;display:flex;align-items:center;justify-content:center;height:195px;overflow:hidden}}</style>
<canvas id="cv" width="480" height="185"></canvas>
<script>
const c=document.getElementById('cv'),x=c.getContext('2d');let t=0;
const dm=[{{x:-120,y:0,r:26,col:'#00d4ff',lbl:'{gene[:5]}\\nCore',f:1,a:8}},{{x:-35,y:28,r:18,col:'#6366f1',lbl:'Dom\\n2',f:1.5,a:11}},{{x:45,y:-18,r:22,col:'#f97316',lbl:'Bind\\nSite',f:.8,a:9}},{{x:125,y:8,r:16,col:'#22c55e',lbl:'C-term',f:1.2,a:6}}];
function dr(){{x.clearRect(0,0,480,185);
for(let i=0;i<dm.length-1;i++){{const a=dm[i],b=dm[i+1];const ax=240+a.x+Math.sin(t*a.f+i)*a.a,ay=90+a.y+Math.cos(t*a.f)*a.a*.5;const bx=240+b.x+Math.sin(t*b.f+i+1)*b.a,by=90+b.y+Math.cos(t*b.f)*b.a*.5;x.beginPath();x.moveTo(ax,ay);x.lineTo(bx,by);x.strokeStyle='rgba(0,212,255,.2)';x.lineWidth=2;x.stroke();}}
dm.forEach((d,i)=>{{const dx=240+d.x+Math.sin(t*d.f+i)*d.a,dy=90+d.y+Math.cos(t*d.f)*d.a*.5;x.beginPath();x.arc(dx,dy,d.r,0,Math.PI*2);x.fillStyle=d.col+'18';x.fill();x.strokeStyle=d.col;x.lineWidth=1.5;x.stroke();x.fillStyle=d.col;x.font='bold 8px Inter,sans-serif';x.textAlign='center';d.lbl.split('\\n').forEach((l,li)=>x.fillText(l,dx,dy-5+li*10));}});
x.fillStyle='#0f2035';x.font='7px Inter,sans-serif';x.textAlign='center';x.fillText('Domain dynamics — fluctuation around equilibrium · Drug binding stabilises specific conformations',240,178);
t+=0.025;requestAnimationFrame(dr);}}
dr();
</script>""", height=195, scrolling=False)

    with cr:
        _sec("Drug Strategy by Protein Class")
        if is_gpcr:
            st.markdown(f'<div class="card" style="border-color:rgba(0,212,255,.2)"><b style="color:#00d4ff;font-family:Inter,sans-serif">GPCR Drug Strategy</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">1. <b>Orthosteric:</b> bind endogenous ligand pocket. Blocks or modulates receptor activation.<br>2. <b>PAM:</b> positive allosteric modulator — remote site, enhances agonist affinity, fewer side effects.<br>3. <b>Biased agonist:</b> selective G-protein coupling without arrestin — reduces desensitisation.<br>4. <b>H8-Filamin disruption:</b> peptide mimetic of FBM — novel, patent-unoccupied axis.<br><br>Timeline: Hit ID 1–2y → Lead opt 2–3y → IND 4–6y → Approval 10–14y.</div></div>', unsafe_allow_html=True)
        elif is_kinase:
            st.markdown(f'<div class="card" style="border-color:rgba(34,197,94,.2)"><b style="color:#22c55e;font-family:Inter,sans-serif">Kinase Drug Strategy</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">1. <b>ATP-competitive (Type I):</b> DFG-in conformation. Most kinase drugs but selectivity issues.<br>2. <b>Allosteric (Type II):</b> DFG-out hydrophobic pocket. More selective. Imatinib model.<br>3. <b>Covalent irreversible:</b> Cys near ATP pocket. EGFR afatinib/osimertinib model.<br>4. <b>PROTAC:</b> degrade kinase entirely — GoF variants unresponsive to inhibition.<br><br>Start with {top_v[0] if top_v else "P/LP variant"} at ATP pocket structure. >70 FDA-approved precedents.</div></div>', unsafe_allow_html=True)
        elif is_pase:
            st.markdown(f'<div class="card" style="border-color:rgba(251,191,36,.2)"><b style="color:#fbbf24;font-family:Inter,sans-serif">Phosphatase Drug Strategy</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">1. <b>Active site inhibitor:</b> bind catalytic pocket — historically challenging (charged site).<br>2. <b>Substrate competitor:</b> block substrate docking — requires substrate structure.<br>3. <b>Allosteric activator:</b> restore LoF activity — underexplored, high opportunity.<br>4. <b>Upstream kinase inhibitor:</b> reduce substrate burden — indirect but precedented.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card" style="border-color:rgba(99,102,241,.2)"><b style="color:#6366f1;font-family:Inter,sans-serif">PPI / Structural Drug Strategy</b><div style="font-size:.69rem;color:#8ab0c8;margin-top:5px;line-height:1.75;font-family:Inter,sans-serif">1. <b>PPI inhibitor:</b> target protein-protein interface (AlphaFold-Multimer + Co-IP validated).<br>2. <b>Stapled peptide:</b> α-helix mimetic — MDM2-p53 model.<br>3. <b>ASO/siRNA:</b> reduce protein level — LoF disease mechanism.<br>4. <b>AAV gene therapy:</b> germline Mendelian disease with known causative variant.<br><br>Evaluate {gene}:{partners[0] if partners else "STRING partner"} interface as primary PPI target.</div></div>', unsafe_allow_html=True)

        if ot_d.get("known_drugs"):
            _sec("Known Drugs")
            for d in ot_d.get("known_drugs", [])[:6]: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #070d14;font-family:Inter,sans-serif">💊 <span style="color:#b8d4e8">{d}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<a class="pill" href="https://platform.opentargets.org/target/{gene}" target="_blank">OpenTargets ↗</a> <a class="pill" href="https://dgidb.org/genes/{gene}" target="_blank">DGIdb ↗</a>', unsafe_allow_html=True)

        _sec("Timeline to Clinic")
        for phase_n, yr, col_p in [("Target ID & Validation", "0–2y", "#00d4ff"), ("Hit Discovery", "1–3y", "#6366f1"), ("Lead Optimisation", "2–4y", "#f97316"), ("Preclinical ADME/Tox", "3–5y", "#ffd20a"), ("Phase I Safety", "5–7y", "#22c55e"), ("Phase II Efficacy", "6–9y", "#22c55e"), ("Phase III Pivotal", "8–12y", "#ff8c42"), ("FDA Review & Approval", "10–14y", "#ff2d55")]:
            st.markdown(f'<div style="display:flex;gap:7px;padding:3px 0;border-bottom:1px solid #070d14;font-family:Inter,sans-serif"><span style="color:{col_p};min-width:62px;font-size:.62rem;font-family:JetBrains Mono,monospace">{yr}</span><span style="color:#8ab0c8;font-size:.68rem">{phase_n}</span></div>', unsafe_allow_html=True)

        # Domain-specific therapeutic notes
        if domain == "Neuroscience":
            _sec("BBB Penetrance Requirements", "#6366f1")
            st.markdown('<div class="card" style="border-color:rgba(99,102,241,.2)"><div class="dim" style="line-height:1.7">CNS drug requirements: cLogP 1–3 · MW<450 · HBD<3 · PSA<90Å² · CNS MPO score ≥4 · Not P-gp substrate. Check Allen Brain Atlas for neuronal subtype expression. BBB permeability via PAMPA-BBB assay.</div></div>', unsafe_allow_html=True)
        elif domain == "Cancer Biology":
            _sec("Oncology Drug Strategy", "#f43f5e")
            st.markdown(f'<div class="card" style="border-color:rgba(244,63,94,.2)"><div class="dim" style="line-height:1.7">Somatic hotspot drug: GoF at {vstr if top_v else "pathogenic variant"} (KRAS G12C/osimertinib model). Consider PARP inhibitor synthetic lethality for germline LoF. Companion diagnostic: ctDNA panel for {vstr if top_v else "target variant"}. FDA Breakthrough designation if rare variant (&lt;200K US patients).</div></div>', unsafe_allow_html=True)
        elif domain == "Pharmaceuticals":
            _sec("Biotech / GPCR Protocol", "#00d4ff")
            st.markdown(f'<div class="card" style="border-color:rgba(0,212,255,.15)"><div class="dim" style="line-height:1.7">{"Full GPCR characterisation protocol: Surface expression (ELISA) → Gα coupling (cAMP HTRF/BRET) → Filamin Ser2152-P IP (primary readout) → β-arrestin (Tango/NanoBiT) → Internalisation (confocal) → WT vs pathogenic variant panel → HTS campaign. PMID:26124276." if is_gpcr else "Non-GPCR biotech target. Evaluate tractability via OpenTargets. Consider bispecific antibody or PROTAC approach for undruggable targets."}</div></div>', unsafe_allow_html=True)


# ─── TAB 5: AI REPORT ─────────────────────────────────────
with t5:
    _sec("Evidence-Tiered Literature")
    tg2 = {}
    for p in papers: tg2.setdefault(p["tier_label"], []).append(p)
    for tlbl, tp in sorted(tg2.items(), key=lambda x: x[1][0]["tier"]):
        with st.expander(f"{tlbl} ({len(tp)} papers)", expanded=tlbl in ("RCT", "Functional")):
            for p in tp: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #070d14"><a href="{p["url"]}" target="_blank" style="color:#5a7590;font-size:.68rem;font-family:Inter,sans-serif">{p["title"][:100]}</a> · {p["authors"][:16]} · {p["journal"]} {p["year"]} · PMID:{p["pmid"]}</div>', unsafe_allow_html=True)

    _sec("AI Synthesis with Live Web Search")
    api_key = st.session_state.get("anthropic_key", "")
    if not api_key:
        st.info("Add your Anthropic API key in the sidebar to enable AI synthesis with live literature search.")
        st.markdown('<div class="card"><div style="color:#b8d4e8;font-size:.72rem;font-weight:600;margin-bottom:6px;font-family:Inter,sans-serif">The AI Report includes:</div><div class="dim" style="line-height:1.8">• VERDICT with confidence and genetic justification · MOLECULAR MECHANISM · INHERITANCE PATTERN<br>• 3 specific therapeutic hypotheses · ACTIVE RESEARCH (live web search 2024–2025) · KEY UNKNOWNS<br>• Every claim cited: Author / Journal / Year / PMID</div></div>', unsafe_allow_html=True)
    else:
        if st.button("▶ Generate AI Report", type="primary", key="ai_run"):
            with st.spinner("Searching live literature and synthesising…"):
                try:
                    import anthropic; client = anthropic.Anthropic(api_key=api_key)
                    wl_txt = st.session_state.wet_lab_text
                    prompt = f"""You are a specialist molecular biologist analysing {gene} for drug target potential.

PROTEIN: {gene} / {pdata.get('protein_name','')} / {acc}
ClinVar P/LP: {n_path} | Critical: {n_crit} | gnomAD pLI: {gnomad.get('pLI','?')} | Verdict: {verdict}
Diseases: {', '.join([d.get('name','') for d in diseases[:5]]) or 'None confirmed'}
STRING partners: {', '.join([p['partner'] for p in string_d[:5]]) or 'Unknown'}
Is GPCR: {is_gpcr} | Is Kinase: {is_kinase} | Is Filamin: {is_filamin}
Domain: {domain} | Research goal: {st.session_state.research_goal}
{"Wet-lab assay: " + wl_txt if wl_txt else ""}

Write these sections with full citations:

## VERDICT
State PURSUE/DEPRIORITISE with confidence level and genetic justification.

## MOLECULAR MECHANISM
Specific mechanism by which variants cause disease. Cite the original papers.

## INHERITANCE PATTERN
AD/AR/XL/de novo — infer from variant data and pLI. Cite clinical genetics papers.

## THERAPEUTIC HYPOTHESES
3 specific, actionable strategies with variant positions. Include estimated timelines.

## ACTIVE RESEARCH LANDSCAPE
Use web search for 2024–2025 preprints, clinical trials, drug approvals, breakthroughs.

## KEY UNKNOWNS AND RESOLVING EXPERIMENTS
3 experiments that would resolve critical gaps. What result would confirm vs refute.

RULES:
- Every claim must cite: Author, Journal, Year, PMID or DOI
- Never say "unknown" — say what experiment resolves it
- {"Mention Filamin Ser2152-P IP assay (PMID:26124276) where relevant" if is_gpcr else ""}
- Specify exact variant positions (p.Arg175His not just "missense variant")
- Tailor to {domain} domain context"""
                    message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=3000, tools=[{"type": "web_search_20250305", "name": "web_search"}], messages=[{"role": "user", "content": prompt}])
                    report = "\n".join(b.text for b in message.content if hasattr(b, "text") and b.text)
                    st.session_state[f"ai_{gene}"] = report
                except Exception as ex: st.error(f"AI error: {ex}")
        if f"ai_{gene}" in st.session_state:
            st.markdown(f'<div class="card" style="line-height:1.85;font-size:.72rem;font-family:Inter,sans-serif">{st.session_state[f"ai_{gene}"]}</div>', unsafe_allow_html=True)
            if st.button("🔄 Regenerate"):
                del st.session_state[f"ai_{gene}"]; st.rerun()


# ─── TAB 6: WORKSPACE ─────────────────────────────────────
with t6:
    _sec(f"Research Workspace — {user.get('name', '')}")
    c1w, c2w, c3w, c4w = st.columns(4)
    c1w.metric("Searches Used", st.session_state.searches_used)
    c2w.metric("Quota", user.get("quota", 5) if user.get("quota", 5) < 99999 else "∞")
    c3w.metric("Proteins Analysed", len(st.session_state.workspace))
    c4w.metric("Domain", domain)

    _sec("Download Full Analysis — 9-Sheet Excel")
    excel_data = _make_excel(gene, pdata, cv, gnomad, gi_s, ot_d, string_d, papers, trials, dgidb, gtex, am_d)
    if excel_data:
        st.download_button(
            f"⬇ Download {gene} Complete Analysis (.xlsx)",
            data=excel_data,
            file_name=f"Protellect_{gene}_{domain.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary", use_container_width=True
        )
        st.markdown('<div class="dim" style="margin-top:3px">9 sheets: Summary · ClinVar Variants · Diseases · AlphaMissense · STRING Network · Literature · Clinical Trials · Drugs · GTEx Expression</div>', unsafe_allow_html=True)
    else:
        st.warning("Excel export requires openpyxl: pip install openpyxl")

    _sec("Search History")
    ws_data = st.session_state.workspace
    if not ws_data:
        st.markdown('<div class="dim" style="padding:8px">No proteins analysed yet.</div>', unsafe_allow_html=True)
    else:
        for item in ws_data:
            col2 = item.get("color", "#2a4060"); ca, cb = st.columns([5, 1])
            with ca: st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:4px 0;border-bottom:1px solid #070d14"><span style="color:#b8d4e8;font-family:JetBrains Mono,monospace;font-size:.76rem;font-weight:600">{item["gene"]}</span><span style="background:{col2}18;color:{col2};border:1px solid {col2}35;border-radius:3px;padding:0 6px;font-size:.6rem;font-weight:600;font-family:Inter,sans-serif">{item["verdict"]}</span><span class="dim">{item.get("domain","")} · {item["accession"]} · {item["protein"][:35]}</span></div>', unsafe_allow_html=True)
            with cb:
                if st.button("↗", key=f"ws_{item['gene']}", help=f"Re-analyse {item['gene']}"):
                    st.session_state._qval = item["gene"]; st.rerun()

    lab = st.session_state.lab_profile
    if lab:
        _sec("Lab Profile")
        st.markdown(f'<div class="dim" style="line-height:1.8;font-family:Inter,sans-serif"><b style="color:#b8d4e8">Organisation:</b> {lab.get("org","Not provided")}<br><b style="color:#b8d4e8">Lab type:</b> {lab.get("lab_type","")}<br><b style="color:#b8d4e8">Research focus:</b> {", ".join(lab.get("focus",[]) or ["Not specified"])}<br><b style="color:#b8d4e8">Model systems:</b> {", ".join(lab.get("models",[]) or ["Not specified"])}<br><b style="color:#b8d4e8">Budget:</b> {lab.get("budget","")}</div>', unsafe_allow_html=True)
