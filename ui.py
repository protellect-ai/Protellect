"""ui.py — Protellect UI. Animated landing via components.html, CSS via st.markdown."""
import streamlit as st
import streamlit.components.v1 as components
import requests

def inject_css():
    st.markdown("""<style>
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
</style>""", unsafe_allow_html=True)

def lbl(t): return f'<div class="p-lbl">{t}</div>'
def section(t): st.markdown(f'<div class="sec">{t}</div>', unsafe_allow_html=True)
def badge(cls, t):
    m={"critical":"crit","high":"hi","moderate":"mod","low":"lo","neutral":"lo","deprioritise":"dep","ok":"ok",
       "CRITICAL":"crit","HIGH":"hi","MODERATE":"mod","DISEASE-CRITICAL":"crit","DISEASE-ASSOCIATED":"hi",
       "VERY LOW":"lo","DEPRIORITISE":"dep","NO DISEASE VARIANTS":"lo"}
    return f'<span class="bdc bdc-{m.get(cls,cls)}">{t}</span>'
def src(label, url=""):
    if url: return f'<a class="src" href="{url}" target="_blank">{label}</a>'
    return f'<span class="src">{label}</span>'

# ─────────────────────────────────────────────────────────────────────────
# DOMAIN LANDING — full animated HTML via components.html()
# ─────────────────────────────────────────────────────────────────────────
DOMAIN_META = {
    "Neuroscience": {
        "icon":"🧠","color":"#818cf8","glow":"rgba(129,140,248,0.3)",
        "tags":["Alzheimer's","Parkinson's","ALS","Epilepsy","Neurodegeneration","BBB Penetrance","Synaptic Biology","Brain Expression","Huntington's","MS"],
        "desc":"Map neurological disease variants to drug targets. BBB penetrance scoring, synaptic interaction networks, brain-specific expression from GTEx.",
    },
    "Cancer Biology": {
        "icon":"🎗","color":"#f43f5e","glow":"rgba(244,63,94,0.3)",
        "tags":["Oncogenes","Tumour Suppressors","Somatic Hotspots","Founder Mutations","COSMIC","cfDNA","CRC","Breast","Lung","Leukaemia"],
        "desc":"Founder mutation identification, somatic vs germline classification, tumour-type breakdown, ClinVar P/LP variant triage for 14 cancer types.",
    },
    "Pharmaceuticals": {
        "icon":"💊","color":"#00e5ff","glow":"rgba(0,229,255,0.3)",
        "tags":["GPCR Targets","Filamin Ser2152-P","Drug Tractability","BRET Assays","Biased Agonism","Clinical Trials","TMAO Arrhythmia","cAMP HTRF","HTS","Phase III"],
        "desc":"GPCR piggyback targets, Filamin Ser2152-P IP assay (receptor-proximal), tractability scoring, drug analogue prioritisation.",
    },
    "Microbiome": {
        "icon":"🦠","color":"#4ade80","glow":"rgba(74,222,128,0.3)",
        "tags":["LLM Annotation","BGC Detection","Taxonomy","Host–Microbe","Gut Ecology","SCFA","Pathobionts","Curli","NRP Synthetase","PKS"],
        "desc":"AI-powered vague→specific gene annotation, biosynthetic gene cluster prediction, pathogen host-receptor mapping, taxonomy intelligence.",
    },
    "Molecular Biology": {
        "icon":"⚛️","color":"#f97316","glow":"rgba(249,115,22,0.3)",
        "tags":["Phosphorylation","Kinase Signalling","Protein Structure","AlphaFold","STRING Networks","Post-translational Mods","Structural Domains","Variant Impact","Co-IP","SPR"],
        "desc":"Phosphorylation signal vs noise analysis, per-residue AlphaMissense, 3D structure exploration, mutation impact scoring, interaction networks.",
    },
}

def show_domain_landing():
    """Animated domain selection page — rendered in iframe via components.html."""
    domains_js = str([{
        "id": d, "icon": m["icon"], "color": m["color"], "glow": m["glow"],
        "tags": m["tags"][:6], "desc": m["desc"]
    } for d, m in DOMAIN_META.items()]).replace("True","true").replace("False","false").replace("None","null")

    html = f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}}
body{{background:#010306;color:#d0e8ff;min-height:100vh;overflow-x:hidden}}

/* ─ Canvas particles ─ */
#canvas{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}}

/* ─ Layout ─ */
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:40px 24px 60px}}

/* ─ Header ─ */
.hero{{text-align:center;margin-bottom:48px}}
.logo{{display:inline-flex;align-items:center;gap:10px;margin-bottom:16px;
  animation:fadeDown .6s ease both}}
.logo-icon{{font-size:2rem;animation:pulse 3s ease infinite}}
.logo-text{{font-size:2.2rem;font-weight:800;letter-spacing:-1px;
  background:linear-gradient(90deg,#00e5ff,#818cf8,#f43f5e);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-size:200% auto;animation:shimmer 4s linear infinite}}
.tagline{{font-size:.78rem;color:#1e3a5f;letter-spacing:.14em;text-transform:uppercase;
  animation:fadeUp .6s .2s ease both;opacity:0}}
.subtitle{{font-size:.9rem;color:#2a5070;margin-top:10px;
  animation:fadeUp .6s .35s ease both;opacity:0}}

/* ─ Domain grid ─ */
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px;
  animation:fadeUp .5s .4s ease both;opacity:0}}
.card{{background:rgba(2,6,9,.85);border:1px solid rgba(255,255,255,0.06);border-radius:14px;
  padding:22px 24px;cursor:pointer;transition:all .3s ease;position:relative;overflow:hidden;
  backdrop-filter:blur(10px)}}
.card::before{{content:'';position:absolute;inset:0;border-radius:14px;opacity:0;
  transition:opacity .3s;pointer-events:none}}
.card:hover{{transform:translateY(-4px) scale(1.01);border-color:var(--col);
  box-shadow:0 0 30px var(--glow),0 8px 32px rgba(0,0,0,.4)}}
.card:hover::before{{opacity:1;background:radial-gradient(circle at 50% 0%,var(--glow),transparent 60%)}}
.card:active{{transform:translateY(-2px) scale(1.005)}}

.card-head{{display:flex;align-items:center;gap:12px;margin-bottom:12px}}
.card-icon{{font-size:1.6rem;transition:transform .3s}}
.card:hover .card-icon{{transform:scale(1.15) rotate(5deg)}}
.card-title{{font-size:1rem;font-weight:700;color:#fff}}
.card-desc{{font-size:.75rem;color:#4a7090;line-height:1.6;margin-bottom:14px}}
.tags{{display:flex;flex-wrap:wrap;gap:4px}}
.tag{{font-size:.62rem;background:rgba(255,255,255,0.04);color:var(--col);
  border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:2px 8px;
  transition:all .2s}}
.card:hover .tag{{background:rgba(255,255,255,0.07);border-color:var(--col)}}

/* ─ Scan line on hover ─ */
.scan{{position:absolute;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--col),transparent);
  top:-100%;transition:top .4s ease;opacity:.5}}
.card:hover .scan{{top:100%}}

/* ─ Footer ─ */
.footer{{text-align:center;margin-top:40px;color:#0d1a2a;font-size:.68rem;font-style:italic;
  animation:fadeUp .5s .6s ease both;opacity:0}}

/* ─ Keyframes ─ */
@keyframes fadeDown{{from{{opacity:0;transform:translateY(-20px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes shimmer{{0%{{background-position:0% 50%}}100%{{background-position:200% 50%}}}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.05)}}}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
</style>
</head><body>
<canvas id="canvas"></canvas>
<div class="wrap">
  <div class="hero">
    <div class="logo">
      <span class="logo-icon">🔬</span>
      <span class="logo-text">Protellect</span>
    </div>
    <div class="tagline">Genetics-First Protein Intelligence</div>
    <div class="subtitle">Select a research domain to enter your workspace</div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="footer">The only platform that tells you which proteins to abandon before you spend the money.</div>
</div>

<script>
// ─ Particle canvas ────────────────────────────────────────────────────────
const canvas=document.getElementById('canvas');
const ctx=canvas.getContext('2d');
canvas.width=window.innerWidth;canvas.height=window.innerHeight;
const pts=Array.from({{length:60}},()=>({{
  x:Math.random()*canvas.width,y:Math.random()*canvas.height,
  vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,
  r:Math.random()*1.5+.5,
  col:`rgba(${{Math.random()>.5?'0,229,255':'129,140,248'}},0.4)`
}}));
function drawPts(){{
  ctx.clearRect(0,0,canvas.width,canvas.height);
  pts.forEach(p=>{{
    p.x+=p.vx;p.y+=p.vy;
    if(p.x<0||p.x>canvas.width)p.vx*=-1;
    if(p.y<0||p.y>canvas.height)p.vy*=-1;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
    ctx.fillStyle=p.col;ctx.fill();
  }});
  pts.forEach((a,i)=>pts.slice(i+1).forEach(b=>{{
    const d=Math.hypot(a.x-b.x,a.y-b.y);
    if(d<120){{ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.strokeStyle=`rgba(0,229,255,${{.08*(1-d/120)}})`;ctx.lineWidth=.5;ctx.stroke()}}
  }}));
  requestAnimationFrame(drawPts);
}}
drawPts();
window.addEventListener('resize',()=>{{canvas.width=window.innerWidth;canvas.height=window.innerHeight;}});

// ─ Render domain cards ─────────────────────────────────────────────────────
const DOMAINS={domains_js};
const grid=document.getElementById('grid');
DOMAINS.forEach((d,i)=>{{
  const el=document.createElement('div');
  el.className='card';
  el.style.cssText=`--col:${{d.color}};--glow:${{d.glow}};animation:fadeUp .4s ${{i*.07}}s ease both;opacity:0`;
  el.innerHTML=`
    <div class="scan"></div>
    <div class="card-head">
      <span class="card-icon">${{d.icon}}</span>
      <span class="card-title">${{d.id}}</span>
    </div>
    <div class="card-desc">${{d.desc}}</div>
    <div class="tags">${{d.tags.map(t=>`<span class="tag">${{t}}</span>`).join('')}}</div>
  `;
  el.addEventListener('click',()=>{{
    el.style.transform='scale(0.97)';
    setTimeout(()=>window.parent.postMessage({{type:'domain_select',domain:d.id}},'*'),120);
  }});
  grid.appendChild(el);
}});

// ─ Listen for Streamlit to receive click ──────────────────────────────────
window.addEventListener('message',e=>{{
  if(e.data&&e.data.type==='domain_select'){{
    window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setComponentValue',value:e.data.domain}},'*');
  }}
}});
</script>
</body></html>"""

    # Render the animated landing and capture click via component value
    result = components.html(html, height=680, scrolling=False)
    
    # Button row below for Streamlit to actually catch domain selection
    st.markdown('<div style="margin-top:-12px">', unsafe_allow_html=True)
    cols = st.columns(5)
    ICONS = {"Neuroscience":"🧠","Cancer Biology":"🎗","Pharmaceuticals":"💊","Microbiome":"🦠","Molecular Biology":"⚛️"}
    for i, (d, m) in enumerate(DOMAIN_META.items()):
        with cols[i]:
            if st.button(f"{m['icon']} {d}", key=f"dl_{d}", use_container_width=True):
                st.session_state.domain = d
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────
# DOMAIN WORKSPACE — tailored per domain + research goal
# ─────────────────────────────────────────────────────────────────────────
WORKSPACE_CONFIG = {
    "Neuroscience": {
        "color":"#818cf8","examples":["APP","SNCA","MAPT","LRRK2","TARDBP","HTT","GBA","PINK1","PRKN","FUS"],
        "goal_prompts":{
            "Drug target identification": "Search a gene to identify neurological disease variants, BBB penetrance, and druggable pockets. Start with LRRK2 or GBA.",
            "Disease mechanism": "Analyse APP or MAPT to map amyloid/tau pathways and identify upstream targets.",
            "Variant pathogenicity": "Enter a gene to score ClinVar variants with AlphaMissense concordance for disease causality.",
            "default": "Enter a neurological gene to begin genetics-first analysis.",
        },
        "key_concepts":["pLI >0.9 = essential neurodevelopmental gene","Heterozygous LoF = dominant neurodegeneration","Digenic interactions in low-diversity populations","Somatic mosaicism in epilepsy"],
        "featured":{"LRRK2":"PD kinase target · 6 P/LP variants · LRRK2i in Phase III","APP":"AD amyloid precursor · GWAS anchor","GBA":"PD lysosomal target · 300+ ClinVar variants"},
    },
    "Cancer Biology": {
        "color":"#f43f5e","examples":["TP53","KRAS","BRCA1","EGFR","MYC","PTEN","APC","BRAF","RB1","CDH1"],
        "goal_prompts":{
            "Drug target identification": "Search an oncogene to identify somatic hotspots, founder mutations, and approved drug overlaps.",
            "Disease mechanism": "Analyse TP53 or KRAS to map cancer hallmarks and downstream pathway dependency.",
            "default": "Enter a cancer gene to triage somatic vs germline variants and identify druggable interfaces.",
        },
        "key_concepts":["Founder mutations = earliest cancer event = primary target","Superimpose variants onto drug crystal structures","LoF + LOH = classic tumour suppressor","Oncogene: gain-of-function at hotspot residues"],
        "featured":{"TP53":"TSG · 1800+ ClinVar variants · p53 reactivators","KRAS":"RAS oncogene · G12C/D hotspots · AMG-510","BRCA1":"Hereditary breast/ovarian · PARP inhibitors"},
    },
    "Pharmaceuticals": {
        "color":"#00e5ff","examples":["ADRB2","ADRB1","AGTR1","DRD2","HTR2A","OPRM1","FLNA","GRK2","ARRB2","MAS1"],
        "goal_prompts":{
            "Drug target identification": "Search a GPCR or drug target to get the 7-step study protocol and Filamin Ser2152-P assay plan.",
            "Therapeutic hypothesis": "Enter a receptor to generate biased agonism hypotheses and TMAO arrhythmia axis analysis.",
            "default": "Enter a GPCR or pharmacological target to begin tractability and assay analysis.",
        },
        "key_concepts":["Filamin Ser2152-P = receptor-proximal GPCR readout (IP)","ARRB1/2: DEPRIORITISE — <5 Mendelian variants","TMAO: cardiac GPCR conformational rattling → arrhythmia","~300/800 Class A GPCRs carry H8 FBM"],
        "featured":{"ADRB2":"β2-AR · GPCR with FBM · cardiac disease variants","FLNA":"Filamin A · Ser2152 IP target · actin cytoskeleton","AGTR1":"AT1R · hypertension · 47 P/LP variants"},
    },
    "Microbiome": {
        "color":"#4ade80","examples":[],
        "goal_prompts":{
            "default": "Use the Annotation tool to convert vague functional annotations into specific mechanistic descriptions.",
        },
        "key_concepts":["'Biosynthesis' is not an annotation — it is the absence of one","LLM reasoning over KO IDs > BLAST-only annotation","BGC clusters predict secondary metabolite output","Host receptor blockade = microbiome-driven therapeutic hypothesis"],
        "featured":{"LLM Annotation":"Vague → specific in seconds","BGC Prediction":"NRPS · PKS · RiPP · Siderophore · Terpene","Taxonomy":"Gut ecology + pathobiont identification"},
    },
    "Molecular Biology": {
        "color":"#f97316","examples":["FLNA","GRK2","PKA","MAPK1","AKT1","SRC","CDK2","EGFR","JAK2","STAT3"],
        "goal_prompts":{
            "Drug target identification": "Enter a kinase or signalling protein to score variant density, tractability, and experiment ROI.",
            "Protein function": "Analyse FLNA or GRK2 to map structural domains, phosphorylation sites, and interaction partners.",
            "default": "Enter a signalling protein to explore structure, phosphorylation codes, and variant impact.",
        },
        "key_concepts":["Phosphorylation site = validated ONLY if mutation causes disease","Background kinase noise ≠ functional phospho code","pLI >0.9 = essential — lethal to disrupt","AlphaMissense score ≥0.564 = pathogenic prediction"],
        "featured":{"FLNA":"Filamin A · Ser2152 PKA substrate · GPCR scaffold","MAPK1":"ERK2 · RAS/MAPK · many somatic variants","AKT1":"PI3K/AKT · E17K hotspot · drug target"},
    },
}

def show_domain_workspace(domain):
    """Animated workspace tailored to domain and research goal."""
    meta  = DOMAIN_META.get(domain, {})
    cfg   = WORKSPACE_CONFIG.get(domain, {})
    goal  = st.session_state.get("research_goal","Drug target identification")
    color = meta.get("color","#00e5ff")
    icon  = meta.get("icon","🔬")
    tags  = meta.get("tags",[])
    examples = cfg.get("examples",[])
    key_concepts = cfg.get("key_concepts",[])
    featured = cfg.get("featured",{})
    prompt_map = cfg.get("goal_prompts",{})
    prompt = prompt_map.get(goal, prompt_map.get("default","Enter a gene to begin."))

    # Animated domain workspace header via components.html
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags[:8])
    concepts_html = "".join(f'<div class="concept">▸ {c}</div>' for c in key_concepts)
    featured_html = "".join(
        f'<div class="feat-item"><span class="feat-gene">{g}</span><span class="feat-desc">{d}</span></div>'
        for g,d in featured.items()
    )
    ex_btns = "".join(f'<button class="ex-btn" onclick="pick(\'{e}\')">{e}</button>' for e in examples[:8])

    ws_html = f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}}
body{{background:#010306;color:#d0e8ff;padding:20px 24px}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes glow{{0%,100%{{box-shadow:0 0 15px {color}33}}50%{{box-shadow:0 0 30px {color}66}}}}
@keyframes scanline{{0%{{top:-2px}}100%{{top:102%}}}}

.header{{display:flex;align-items:center;gap:12px;margin-bottom:18px;animation:fadeIn .4s ease}}
.icon{{font-size:1.8rem;animation:glow 3s ease infinite;border-radius:10px;padding:4px 8px;
  background:rgba(255,255,255,.04);border:1px solid {color}33}}
.title{{font-size:1.3rem;font-weight:800;color:{color}}}
.goal-badge{{font-size:.65rem;background:{color}18;color:{color};border:1px solid {color}44;
  border-radius:12px;padding:2px 10px;font-weight:600;margin-left:8px;letter-spacing:.04em}}

.prompt{{background:{color}08;border:1px solid {color}22;border-left:3px solid {color};
  border-radius:6px;padding:10px 14px;font-size:.8rem;color:#8baabf;margin-bottom:16px;
  animation:fadeIn .4s .1s ease both;opacity:0}}

.tags{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:18px;animation:fadeIn .4s .15s ease both;opacity:0}}
.tag{{font-size:.62rem;color:{color};background:{color}10;border:1px solid {color}25;
  border-radius:12px;padding:2px 9px}}

.section{{font-size:.7rem;color:#1e3a5f;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  margin-bottom:8px;margin-top:14px}}

.concepts{{animation:fadeIn .4s .2s ease both;opacity:0}}
.concept{{font-size:.74rem;color:#4a7090;padding:4px 0;border-bottom:1px solid #060d14;line-height:1.5}}

.featured{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px;
  animation:fadeIn .4s .25s ease both;opacity:0}}
.feat-item{{background:#020609;border:1px solid #0a1520;border-radius:6px;padding:8px 10px;
  transition:border-color .2s}}
.feat-item:hover{{border-color:{color}44}}
.feat-gene{{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:{color};display:block;font-weight:600}}
.feat-desc{{font-size:.67rem;color:#2a5070;margin-top:2px;display:block;line-height:1.4}}

.ex-row{{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;animation:fadeIn .4s .3s ease both;opacity:0}}
.ex-btn{{font-family:'JetBrains Mono',monospace;font-size:.72rem;background:#020609;
  border:1px solid #0d1a2a;color:#4a7090;border-radius:4px;padding:3px 10px;cursor:pointer;
  transition:all .15s}}
.ex-btn:hover{{background:{color}10;border-color:{color};color:{color};transform:translateY(-1px)}}
</style></head><body>
<div class="header">
  <span class="icon">{icon}</span>
  <div>
    <span class="title">{domain}</span>
    <span class="goal-badge">{goal}</span>
  </div>
</div>
<div class="prompt">{prompt}</div>
<div class="tags">{tags_html}</div>
{"<div class='section'>Key Concepts</div><div class='concepts'>" + concepts_html + "</div>" if key_concepts else ""}
{"<div class='section'>Featured Proteins</div><div class='featured'>" + featured_html + "</div>" if featured_html else ""}
{"<div class='section'>Quick Examples</div><div class='ex-row'>" + ex_btns + "</div>" if ex_btns else ""}
<script>
function pick(gene){{
  window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setComponentValue',value:'pick:'+gene}},'*');
}}
</script>
</body></html>"""

    components.html(ws_html, height=340, scrolling=False)

    if examples:
        ec = st.columns(min(8, len(examples)))
        for i, ex in enumerate(examples[:8]):
            with ec[i]:
                if st.button(ex, key=f"dex_{ex}_{domain}", use_container_width=True):
                    st.session_state._qval = ex
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────
# DISEASE LINK INLINE
# ─────────────────────────────────────────────────────────────────────────
def show_disease_link_inline(q):
    from databases import MICRO_ORGANISMS
    from fetchers import HEADERS
    section(f"Disease: {q}")
    q_l = q.lower()
    for org_name, org in MICRO_ORGANISMS.items():
        if org_name.lower() in q_l or org.get("disease","").lower() in q_l:
            st.markdown(f"**{org['organism']}**")
            st.caption(f"{org['type']} · Disease: {org['disease']}")
            st.write(org.get("mechanism","")[:200])
            section("Host Receptors — Click to Analyse")
            rc = st.columns(min(4, len(org.get("host_receptors",[])) or 1))
            for i, rec in enumerate(org.get("host_receptors",[])):
                with rc[i]:
                    if st.button(rec, key=f"rec_{rec}"):
                        st.session_state._qval = rec; st.rerun()
            return
    try:
        r = requests.get("https://rest.uniprot.org/uniprotkb/search",
            params={"query":f"cc_disease:{q} AND organism_id:9606 AND reviewed:true",
                    "format":"json","size":8,"fields":"accession,gene_names,protein_name"},
            headers=HEADERS, timeout=12)
        for hit in r.json().get("results",[]):
            gs = [g.get("geneName",{}).get("value","") for g in hit.get("genes",[])]
            g  = gs[0] if gs else hit.get("primaryAccession","")
            pn = hit.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value","")
            c1, c2 = st.columns([4,1])
            with c1: st.markdown(f"**`{g}`** — {pn[:55]}")
            with c2:
                if st.button(f"↗ {g}", key=f"dis_{g}"):
                    st.session_state._qval = g; st.rerun()
    except: pass
