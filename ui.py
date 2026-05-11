"""ui.py — CSS injection + domain UI helpers. Proper module, no exec()."""
import streamlit as st
import requests

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{font-family:'Inter',sans-serif!important}
html,body,[data-testid="stAppViewContainer"]{background:#010306!important}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden;height:0}
.block-container{padding:.5rem 1.2rem!important;max-width:100%}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-thumb{background:#0d1a2a;border-radius:2px}
[data-testid="stSidebar"]{background:#020609!important;border-right:1px solid #0a1520!important;min-width:240px!important;max-width:265px!important}
[data-testid="stSidebar"] .block-container{padding:.5rem .7rem!important}
[data-testid="stSidebar"] .stButton>button{font-size:.72rem!important;padding:3px 8px!important;min-height:26px!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#020609;border-radius:5px;padding:2px;gap:1px;border:1px solid #0a1520}
[data-testid="stTabs"] [data-baseweb="tab"]{border-radius:4px;color:#2a5070;font-size:.74rem;font-weight:500;padding:4px 10px;min-height:26px}
[data-testid="stTabs"] [aria-selected="true"]{background:rgba(0,229,255,0.1)!important;color:#00e5ff!important;border:1px solid rgba(0,229,255,0.2)!important}
[data-testid="stMetric"]{background:#020609;border:1px solid #0a1520;border-radius:6px;padding:7px 10px}
[data-testid="stMetricValue"]{color:#00e5ff!important;font-size:.95rem!important;font-weight:700!important}
[data-testid="stMetricLabel"]{color:#2a5070!important;font-size:.62rem!important;text-transform:uppercase;letter-spacing:.04em}
[data-testid="stExpander"]{background:#020609;border:1px solid #0a1520!important;border-radius:5px;margin:2px 0}
[data-testid="stExpander"] summary{color:#4a7090!important;font-size:.73rem!important;padding:4px 8px!important}
[data-testid="stTextInput"] input{background:#020609!important;border:1px solid #0d1a2a!important;color:#d0e8ff!important;border-radius:4px!important;font-size:.78rem!important;padding:4px 8px!important}
[data-testid="stTextInput"] input:focus{border-color:rgba(0,229,255,0.35)!important}
[data-testid="stTextArea"] textarea{background:#020609!important;border:1px solid #0d1a2a!important;color:#d0e8ff!important;border-radius:4px!important;font-size:.74rem!important;padding:4px 8px!important}
[data-testid="stSelectbox"] div[data-baseweb="select"]>div{background:#020609!important;border-color:#0d1a2a!important;font-size:.75rem!important;min-height:26px!important}
[data-testid="stFileUploader"]{border:1px dashed #0d1a2a!important;border-radius:4px!important;padding:4px!important;background:#020609!important}
[data-testid="stFileUploader"] *{font-size:.71rem!important;color:#4a7090!important}
.stButton>button{background:#020609;border:1px solid #0d1a2a;color:#8baabf;border-radius:4px;font-size:.74rem;padding:3px 10px;min-height:28px;transition:all .12s}
.stButton>button:hover{background:#0a1520;border-color:rgba(0,229,255,0.2);color:#00e5ff}
.stButton>button[kind="primary"]{background:rgba(0,229,255,0.07)!important;border-color:rgba(0,229,255,0.25)!important;color:#00e5ff!important}
[data-testid="stDataFrame"] *{font-size:.72rem!important}
[data-testid="stSlider"] *{font-size:.72rem!important}
[data-testid="stAlert"]{padding:5px 9px!important;font-size:.74rem!important;border-radius:4px!important}
.p-lbl{font-size:.62rem;color:#1e3a5f;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:7px 0 2px;padding:0;display:block}
.sec{font-size:.78rem;font-weight:600;color:#00e5ff;border-bottom:1px solid #0a1520;padding-bottom:4px;margin:10px 0 6px;letter-spacing:.02em}
.card{background:#020609;border:1px solid #0a1520;border-radius:5px;padding:8px 12px;margin:4px 0;font-size:.76rem}
.row{display:flex;align-items:flex-start;gap:5px;padding:4px 7px;border-radius:4px;margin:2px 0;background:#020609;border-left:2px solid #1e3a5f;font-size:.74rem}
.row.crit{border-left-color:#ff2d55}.row.hi{border-left-color:#ff8c42}.row.mod{border-left-color:#ffd60a}
.pill{display:inline-block;background:rgba(0,229,255,0.06);color:#00e5ff;border:1px solid rgba(0,229,255,0.15);border-radius:10px;padding:1px 7px;font-size:.66rem;margin:1px;text-decoration:none}
.src{display:inline-block;background:#020609;color:#1e3a5f;border:1px solid #0a1520;border-radius:2px;padding:0 4px;font-size:.63rem;margin:1px}
.bdc{border-radius:3px;padding:1px 6px;font-size:.65rem;font-weight:600;display:inline-block}
.bdc-crit{background:rgba(255,45,85,0.1);color:#ff2d55;border:1px solid rgba(255,45,85,0.25)}
.bdc-hi{background:rgba(255,140,66,0.1);color:#ff8c42;border:1px solid rgba(255,140,66,0.25)}
.bdc-mod{background:rgba(255,214,10,0.07);color:#ffd60a;border:1px solid rgba(255,214,10,0.2)}
.bdc-lo{background:rgba(100,116,139,0.1);color:#4a7090;border:1px solid #1e3a5f}
.bdc-dep{background:rgba(239,68,68,0.08);color:#ef4444;border:1px solid rgba(239,68,68,0.3)}
.bdc-ok{background:rgba(74,222,128,0.07);color:#4ade80;border:1px solid rgba(74,222,128,0.2)}
.mono{font-family:'JetBrains Mono',monospace!important;font-size:.78rem}
.dim{color:#2a5070;font-size:.7rem}
.exp-dof{border-color:rgba(0,229,255,0.25)!important;background:rgba(0,229,255,0.02)!important}
.exp-av{border-color:rgba(239,68,68,0.25)!important;background:rgba(239,68,68,0.02)!important}
</style>""", unsafe_allow_html=True)

def lbl(t): return f'<div class="p-lbl">{t}</div>'
def section(t): st.markdown(f'<div class="sec">{t}</div>', unsafe_allow_html=True)
def badge(cls, t):
    m={"critical":"crit","high":"hi","moderate":"mod","low":"lo","neutral":"lo",
       "deprioritise":"dep","ok":"ok","CRITICAL":"crit","HIGH":"hi","MODERATE":"mod",
       "DISEASE-CRITICAL":"crit","DISEASE-ASSOCIATED":"hi","VERY LOW":"lo",
       "DEPRIORITISE":"dep","NO DISEASE VARIANTS":"lo"}
    c=m.get(cls,cls); return f'<span class="bdc bdc-{c}">{t}</span>'
def src(label, url=""):
    if url: return f'<a class="src" href="{url}" target="_blank">{label}</a>'
    return f'<span class="src">{label}</span>'

def show_domain_landing():
    from databases import DOMAIN_EXAMPLES
    ICONS={"Neuroscience":"🧠","Cancer Biology":"🎗","Pharmaceuticals":"💊","Microbiome":"🦠","Molecular Biology":"⚛️"}
    DESC={"Neuroscience":"Neurodegeneration · ALS/AD/PD · BBB penetrance · Brain expression",
          "Cancer Biology":"Oncogene/TSG · Somatic hotspots · Founder mutations · cfDNA",
          "Pharmaceuticals":"GPCR targets · Filamin Ser2152-P IP assay · Drug tractability",
          "Microbiome":"LLM gene annotation · BGC · Taxonomy · Host–microbe pathways",
          "Molecular Biology":"Protein structure · Phosphorylation codes · Kinase signalling"}
    st.markdown("""<style>
    @keyframes fadeInUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
    .dlanding{animation:fadeInUp .35s ease forwards;opacity:0;animation-delay:var(--d,0s)}
    </style>
    <div style='text-align:center;padding:48px 0 28px'>
      <div style='font-size:1.6rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#7c3aed);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px'>Protellect</div>
      <div style='color:#1e3a5f;font-size:.7rem;letter-spacing:.12em;margin-top:2px'>GENETICS-FIRST PROTEIN INTELLIGENCE</div>
      <div style='color:#2a5070;font-size:.78rem;margin-top:10px'>Select a domain to begin</div>
    </div>""", unsafe_allow_html=True)
    _, mc, _ = st.columns([1,2.5,1])
    with mc:
        for i,(d,desc) in enumerate(DESC.items()):
            delay=f"{i*0.08:.2f}s"
            st.markdown(f'<div class="dlanding" style="--d:{delay}"></div>', unsafe_allow_html=True)
            if st.button(f"{ICONS[d]}  {d}  ·  {desc}", key=f"dl_{d}", use_container_width=True):
                st.session_state.domain=d; st.rerun()
    st.markdown('<div style="text-align:center;margin-top:28px;color:#0d1a2a;font-size:.68rem;font-style:italic">The only platform that tells you which proteins to abandon before you spend the money.</div>', unsafe_allow_html=True)

def show_domain_workspace(domain):
    from databases import DOMAIN_EXAMPLES
    ICONS={"Neuroscience":"🧠","Cancer Biology":"🎗","Pharmaceuticals":"💊","Microbiome":"🦠","Molecular Biology":"⚛️"}
    examples=DOMAIN_EXAMPLES.get(domain,[])
    st.markdown(f"""<div style='border:1px solid #0a1520;border-radius:6px;padding:20px;text-align:center;margin:8px 0'>
      <div style='font-size:1rem;margin-bottom:6px'>{ICONS.get(domain,"🔬")}</div>
      <div style='font-size:.85rem;font-weight:600;color:#d0e8ff'>{domain}</div>
      <div style='color:#2a5070;font-size:.73rem;margin-top:3px'>Enter a gene symbol in the sidebar or click an example below.</div>
    </div>""", unsafe_allow_html=True)
    if examples:
        st.markdown('<div style="color:#1e3a5f;font-size:.64rem;text-align:center;margin-bottom:4px;letter-spacing:.06em">QUICK EXAMPLES</div>', unsafe_allow_html=True)
        ec=st.columns(min(7,len(examples)))
        for i,ex in enumerate(examples):
            with ec[i]:
                if st.button(ex, key=f"dex_{ex}_{domain}", use_container_width=True):
                    st.session_state._qval=ex; st.rerun()

def show_disease_link_inline(q):
    from databases import MICRO_ORGANISMS
    from fetchers import HEADERS
    section(f"Disease: {q}")
    q_l=q.lower()
    for org_name,org in MICRO_ORGANISMS.items():
        if org_name.lower() in q_l or org.get("disease","").lower() in q_l:
            st.markdown(f'<div class="card"><span class="mono">{org["organism"]}</span> <span class="bdc bdc-dep">{org["type"]}</span><br><span class="dim">Disease: {org["disease"]}</span><br><span class="dim">{org.get("mechanism","")[:150]}</span></div>', unsafe_allow_html=True)
            section("Host Receptors — Analyse")
            rc=st.columns(min(4,len(org.get("host_receptors",[])) or 1))
            for i,rec in enumerate(org.get("host_receptors",[])):
                with rc[i]:
                    if st.button(rec, key=f"rec_{rec}"): st.session_state._qval=rec; st.rerun()
            return
    try:
        r=requests.get("https://rest.uniprot.org/uniprotkb/search",
                       params={"query":f"cc_disease:{q} AND organism_id:9606 AND reviewed:true","format":"json","size":8,"fields":"accession,gene_names,protein_name"},
                       headers=HEADERS, timeout=12)
        for hit in r.json().get("results",[]):
            gs=[g.get("geneName",{}).get("value","") for g in hit.get("genes",[])]
            g=gs[0] if gs else hit.get("primaryAccession","")
            pn=hit.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
            c1,c2=st.columns([4,1])
            with c1: st.markdown(f'<span class="mono">{g}</span> <span class="dim">{pn[:55]}</span>',unsafe_allow_html=True)
            with c2:
                if st.button(f"↗{g}",key=f"dis_{g}"): st.session_state._qval=g; st.rerun()
    except: pass
