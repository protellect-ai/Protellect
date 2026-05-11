import streamlit as st
import requests, re, json, io, os, hashlib
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

try:
    import anthropic as _ant
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

def _ai_client():
    if not ANTHROPIC_OK: return None
    key = None
    try: key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
    except: pass
    if not key: key = os.environ.get("ANTHROPIC_API_KEY","")
    return _ant.Anthropic(api_key=key) if key else None

st.set_page_config(page_title="Protellect", page_icon=":microscope:", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{font-family:'Space Grotesk',sans-serif;box-sizing:border-box}
code,.mono{font-family:'JetBrains Mono',monospace}
#MainMenu,footer,header,[data-testid="stDeployButton"]{display:none!important}
[data-testid="stSidebar"]{background:#030810!important;border-right:1px solid #0d2545!important;min-width:230px!important}
.block-container{padding:0!important;max-width:100%!important}
[data-testid="stAppViewContainer"]{background:#010306}
div[data-testid="metric-container"]{background:#070d1a;border:1px solid #0d2545;border-radius:11px;padding:.7rem}
div[data-testid="metric-container"] label{color:#3a6080!important;font-size:.68rem!important;letter-spacing:.07em!important;text-transform:uppercase!important}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#00e5ff!important;font-size:1.3rem!important;font-weight:600!important}
.stTabs [data-baseweb="tab-list"]{gap:2px;background:#030810;border-radius:10px;padding:3px;border:1px solid #0d2545}
.stTabs [data-baseweb="tab"]{background:transparent;color:#3a6080;border-radius:7px;font-size:.74rem;padding:.27rem .72rem;font-weight:500}
.stTabs [aria-selected="true"]{background:#0d2545!important;color:#00e5ff!important}
.stButton>button{background:transparent;border:1px solid #0d2545;color:#d0e8ff;font-size:.78rem;border-radius:8px;font-weight:500;transition:all .2s;padding:.27rem .72rem}
.stButton>button:hover{border-color:#00e5ff44;color:#00e5ff;background:#00e5ff08}
.stButton>button[kind="primary"]{background:#00e5ff!important;color:#010306!important;border:none!important;font-weight:700!important}
.stTextInput>div>div>input,.stSelectbox>div>div,.stTextArea textarea{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important}
.stExpander{border:1px solid #0d2545!important;border-radius:10px!important;background:#040c14!important;margin-bottom:.25rem!important}
.stFileUploader>div{background:#030810;border:1px dashed #0d2545;border-radius:8px}
h1,h2,h3{color:#d0e8ff!important}
a{color:#00e5ff!important;text-decoration:none!important}
.stAlert{border-radius:9px!important}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:.4;transform:scale(.97)}50%{opacity:1;transform:scale(1.03)}}
@keyframes glow{0%,100%{box-shadow:0 0 18px #00e5ff22}50%{box-shadow:0 0 44px #00e5ff55}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

# ── session state ─────────────────────────────────────────────────────────────
for k,v in [("domain",None),("onboarded",False),("lab",{}),("user",None),("analysis_cache",{})]:
    if k not in st.session_state: st.session_state[k]=v

# ── helpers ───────────────────────────────────────────────────────────────────
def sh(icon,title,color="#00e5ff"):
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;margin:.75rem 0 .3rem'><span style='font-size:.9rem'>{icon}</span><span style='color:{color};font-weight:600;font-size:.87rem'>{title}</span></div>",unsafe_allow_html=True)
def badge(text,color="#00e5ff"):
    return f"<span style='background:{color}18;color:{color};font-size:.67rem;padding:2px 8px;border-radius:7px;border:1px solid {color}44;font-weight:600'>{text}</span>"
def warn_box(title,body):
    st.markdown(f"<div style='background:#0a0205;border:1px solid #ff2d5544;border-radius:9px;padding:.58rem .88rem;margin:.22rem 0'><div style='color:#ff2d55;font-weight:600;font-size:.75rem;margin-bottom:1px'>{title}</div><div style='color:#6a3040;font-size:.75rem;line-height:1.58'>{body}</div></div>",unsafe_allow_html=True)
def info_box(body,color="#00e5ff"):
    st.markdown(f"<div style='background:{color}0a;border:1px solid {color}33;border-radius:9px;padding:.58rem .88rem;margin:.22rem 0'><div style='color:{color};font-size:.8rem;line-height:1.68'>{body}</div></div>",unsafe_allow_html=True)
def src_link(label,url):
    return f"<a href='{url}' target='_blank' style='display:inline-flex;align-items:center;gap:3px;font-size:.68rem;color:#00e5ff;background:#00e5ff0d;border:1px solid #00e5ff33;border-radius:6px;padding:2px 7px;margin:2px'>{label} &#8599;</a>"

TIER_MAP={"Tier 1 RCT":{"c":"#00c896","w":10},"Tier 2 Cohort":{"c":"#4a90d9","w":8},"Tier 3 Functional":{"c":"#ff8c42","w":7},"Tier 4 Structural":{"c":"#a855f7","w":6},"Tier 5 Animal":{"c":"#ffd60a","w":5},"Tier 6 Computational":{"c":"#5a8090","w":4},"Tier 7 Case report":{"c":"#3a5a7a","w":3},"Tier 8 Review":{"c":"#2a4060","w":2},"Tier 9 Preprint":{"c":"#ff2d55","w":1}}
def tier_badge(t): c=TIER_MAP.get(t,{"c":"#3a5a7a"})["c"]; return badge(t,c)
def classify_tier(title):
    t=title.lower()
    if any(x in t for x in ["randomised","randomized","rct","placebo-controlled","double-blind"]): return "Tier 1 RCT"
    if any(x in t for x in ["cohort","prospective","retrospective","patients with","case-control"]): return "Tier 2 Cohort"
    if any(x in t for x in ["crispr","knock-in","knock-out","functional assay","western blot","immunoprecip"]): return "Tier 3 Functional"
    if any(x in t for x in ["crystal structure","cryo-em","nmr structure","x-ray","alphafold","spr","itc"]): return "Tier 4 Structural"
    if any(x in t for x in ["mouse model","zebrafish","xenograft","in vivo","murine"]): return "Tier 5 Animal"
    if any(x in t for x in ["computational","in silico","machine learning","deep learning"]): return "Tier 6 Computational"
    if any(x in t for x in ["case report","case series"]): return "Tier 7 Case report"
    if any(x in t for x in ["review","meta-analysis","systematic review"]): return "Tier 8 Review"
    return "Tier 9 Preprint"
def detect_weaknesses(title):
    w=[]; t=title.lower()
    if any(x in t for x in ["beta-arrestin","arrestin"]): w.append(("No ARRB disease variant evidence","Uses arrestin as readout/target. ARRB1/ARRB2 KO mice viable. Zero Mendelian disease variants. Kinase noise."))
    if any(x in t for x in ["hek293","hek 293","cos-7","cos7"]): w.append(("Transformed cell line artefact risk","HEK293/COS hyperactivated signalling -- not primary cell biology."))
    if any(x in t for x in ["overexpressed","overexpression","ectopic"]): w.append(("Overexpression artefact","Non-physiological concentrations cause artefactual interactions. Use CRISPR endogenous tagging."))
    if "n=3" in t or "n = 3" in t: w.append(("Very small sample (n=3)","Insufficient statistical power. Effect sizes overestimated."))
    if any(x in t for x in ["g93a","sod1 g93a"]): w.append(("SOD1 G93A -- poor translational record","100+ drugs worked in this model, zero translated to ALS."))
    return w

# ── APIs ──────────────────────────────────────────────────────────────────────
ESEARCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_uniprot(gene):
    try:
        r=requests.get("https://rest.uniprot.org/uniprotkb/search",params={"query":f"gene:{gene} AND organism_id:9606 AND reviewed:true","format":"json","size":1},timeout=12)
        res=r.json().get("results",[])
        if not res: return {}
        p=res[0]; uid=p.get("primaryAccession","")
        name=(p.get("proteinDescription",{}).get("recommendedName",{}).get("fullName",{}).get("value",""))
        gene_sym=p.get("genes",[{}])[0].get("geneName",{}).get("value",gene)
        func=""; diseases=[]; tissues=[]; ptms=[]
        for c in p.get("comments",[]):
            ct=c.get("commentType","")
            if ct=="FUNCTION" and not func: func=" ".join(x.get("value","") for x in c.get("texts",[]))[:500]
            if ct=="DISEASE":
                d=c.get("disease",{}); diseases.append({"name":d.get("diseaseId",d.get("diseaseName","")),"desc":" ".join(x.get("value","") for x in c.get("texts",[]))[:200]})
            if ct=="TISSUE SPECIFICITY": tissues.append(" ".join(x.get("value","") for x in c.get("texts",[]))[:200])
            if ct=="PTM": ptms.append(" ".join(x.get("value","") for x in c.get("texts",[]))[:200])
        keywords=[kw.get("name","") for kw in p.get("keywords",[])[:12]]
        return{"uid":uid,"name":name,"gene":gene_sym,"function":func,"diseases":diseases[:6],"tissues":tissues[:3],"ptms":ptms[:3],"keywords":keywords,"length":p.get("sequence",{}).get("length",0),"human":p.get("organism",{}).get("taxonId",0)==9606}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_clinvar(gene):
    try:
        r=requests.get(ESEARCH,params={"db":"clinvar","term":f"{gene}[gene] AND (pathogenic[clinsig] OR likely_pathogenic[clinsig])","retmax":50,"retmode":"json"},timeout=12)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(EFETCH,params={"db":"clinvar","id":",".join(ids[:35]),"rettype":"vcv","retmode":"json"},timeout=15)
        variants=[]
        for uid,entry in r2.json().get("result",{}).items():
            if uid=="uids": continue
            title=entry.get("title",""); cs=entry.get("clinical_significance",{}).get("description","")
            stars=entry.get("review_status",{}).get("stars",0)
            cond="; ".join((entry.get("trait_set",[{}])[0].get("trait_name",[""]) if entry.get("trait_set") else [""]))
            score=(5 if "pathogenic" in cs.lower() and "likely" not in cs.lower() else 4 if "likely pathogenic" in cs.lower() else 0)+min(stars,2)
            rank="CRITICAL" if score>=6 else "HIGH" if score>=5 else "MODERATE" if score>=4 else "LOW"
            variants.append({"uid":uid,"title":title,"cs":cs,"stars":stars,"condition":cond,"score":score,"ml_rank":rank,"url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"})
        return sorted(variants,key=lambda x:-x["score"])
    except: return []

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_gnomad(gene):
    try:
        q='{ gene(gene_symbol: "%s", reference_genome: GRCh38) { gnomad_constraint { pli oe_lof oe_mis } } }' % gene
        r=requests.post("https://gnomad.broadinstitute.org/api",json={"query":q},timeout=12)
        c=r.json().get("data",{}).get("gene",{}).get("gnomad_constraint",{})
        return{"pLI":round(c.get("pli",0),3),"oe_lof":round(c.get("oe_lof",1),3),"oe_mis":round(c.get("oe_mis",1),3)}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_string(gene):
    try:
        r=requests.get("https://string-db.org/api/json/network",params={"identifiers":gene,"species":9606,"required_score":700,"limit":10},timeout=12)
        seen=set(); partners=[]
        for item in r.json():
            a,b=item.get("preferredName_A",""),item.get("preferredName_B","")
            partner=b if a.upper()==gene.upper() else a
            if partner and partner.upper()!=gene.upper() and partner not in seen:
                seen.add(partner); partners.append({"partner":partner,"score":round(item.get("score",0),3)})
        return partners[:8]
    except: return []

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_opentargets(gene):
    try:
        r0=requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene",timeout=8)
        hits=r0.json().get("hits",[])
        if not hits: return {}
        ensembl=hits[0].get("ensembl",{})
        if isinstance(ensembl,list): ensembl=ensembl[0]
        eid=ensembl.get("gene","")
        if not eid: return {}
        q='query($id:String!){ target(ensemblId:$id){ knownDrugs{ rows{ drug{ name } phase approvedIndications } } tractability{ label modality value } associatedDiseases(page:{size:6}){ rows{ disease{ name } score } } } }'
        r=requests.post("https://api.platform.opentargets.org/api/v4/graphql",json={"query":q,"variables":{"id":eid}},timeout=12)
        t=r.json().get("data",{}).get("target",{})
        drugs=[{"name":row.get("drug",{}).get("name",""),"phase":row.get("phase",0)} for row in (t.get("knownDrugs") or {}).get("rows",[])[:8]]
        tract=[x.get("label","") for x in (t.get("tractability") or []) if x.get("value")]
        dis_assoc=[{"name":row.get("disease",{}).get("name",""),"score":round(row.get("score",0),3)} for row in (t.get("associatedDiseases") or {}).get("rows",[])[:6]]
        return{"drugs":drugs,"tractability":tract,"disease_assoc":dis_assoc,"ensembl":eid}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_clinicaltrials(gene):
    try:
        r=requests.get("https://clinicaltrials.gov/api/v2/studies",params={"query.term":gene,"filter.status":"RECRUITING","pageSize":8,"format":"json"},timeout=12)
        studies=[]
        for s in r.json().get("studies",[])[:6]:
            proto=s.get("protocolSection",{}); ident=proto.get("identificationModule",{})
            design=proto.get("designModule",{}); status=proto.get("statusModule",{})
            studies.append({"nct":ident.get("nctId",""),"title":ident.get("briefTitle","")[:85],"phase":", ".join(design.get("phases",[])),"sponsor":proto.get("sponsorCollaboratorsModule",{}).get("leadSponsor",{}).get("name","")[:45],"url":f"https://clinicaltrials.gov/study/{ident.get('nctId','')}"})
        return studies
    except: return []

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_pubmed(query,n=10):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":query,"retmax":n,"retmode":"json","sort":"relevance"},timeout=12)
        ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=12)
        result=r2.json().get("result",{}); papers=[]
        for uid in result.get("uids",[]):
            e=result.get(uid,{}); auth=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: auth+=" et al."
            title=e.get("title",""); doi=e.get("elocationid","").replace("doi: ","")
            papers.append({"pmid":uid,"title":title,"authors":auth,"journal":e.get("source",""),"year":e.get("pubdate","")[:4],"doi":doi,"tier":classify_tier(title),"url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"})
        return papers
    except: return []

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_alphafold(uid):
    try:
        r=requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{uid}",timeout=10)
        d=r.json()
        if not d: return {}
        return{"af_url":f"https://alphafold.ebi.ac.uk/entry/{uid}","pdb_url":d[0].get("pdbUrl",""),"am_url":d[0].get("amAnnotationsUrl","")}
    except: return {}

# AlphaMissense cached separately with lower entry count
@st.cache_data(ttl=7200,show_spinner=False,max_entries=10)
def api_alphamissense(uid):
    try:
        af=api_alphafold(uid)
        am_url=af.get("am_url","")
        if not am_url: return {}
        r=requests.get(am_url,timeout=20)
        lines=r.text.strip().split("\n"); scores=[]; path=0; benign=0; amb=0
        for line in lines[1:]:
            parts=line.split(",")
            if len(parts)>=4:
                try:
                    pos=int(parts[1]); score=float(parts[3])
                    scores.append({"pos":pos,"score":score})
                    if score>=0.564: path+=1
                    elif score<=0.34: benign+=1
                    else: amb+=1
                except: pass
        pos_max={}
        for s in scores:
            p=s["pos"]
            if p not in pos_max or s["score"]>pos_max[p]: pos_max[p]=s["score"]
        mean=round(sum(s["score"] for s in scores)/len(scores),3) if scores else 0
        return{"pathogenic_count":path,"benign_count":benign,"ambiguous_count":amb,"mean_score":mean,"pos_max_scores":pos_max,"total":len(scores)}
    except: return {}

@st.cache_data(ttl=3600,show_spinner=False,max_entries=50)
def api_pubchem(compound):
    try:
        r=requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(compound)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,XLogP/JSON",timeout=10)
        props=r.json().get("PropertyTable",{}).get("Properties",[{}])[0]
        cid=str(props.get("CID",""))
        return{"cid":cid,"formula":props.get("MolecularFormula",""),"mw":props.get("MolecularWeight",""),"smiles":props.get("CanonicalSMILES",""),"logp":props.get("XLogP",""),"img_url":f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG" if cid else ""}
    except: return {}

def gi_score(cv,length):
    n=len(cv); per100=n/(length/100) if length else 0
    n_crit=sum(1 for v in cv if v.get("ml_rank")=="CRITICAL")
    n_lof=sum(1 for v in cv if any(k in v.get("title","").lower() for k in ["frameshift","nonsense","stop gained","del"]))
    if not cv: return{"verdict":"NO DISEASE VARIANTS","color":"#1e3a5a","pursue":"deprioritise","n":0,"per100":0,"n_crit":0,"n_lof":0,"icon":"o","explanation":"Zero pathogenic variants. Cannot classify as disease driver."}
    if per100>=1.0 and n>=5 and n_crit>=1: return{"verdict":"DISEASE-CRITICAL","color":"#ff2d55","pursue":"prioritise","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"[R]","explanation":f"{n} confirmed P/LP variants * {n_crit} CRITICAL * Strong genetic validation."}
    if per100>=0.5 or n>=15: return{"verdict":"DISEASE-ASSOCIATED","color":"#ff8c42","pursue":"proceed","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"[O]","explanation":f"{n} pathogenic variants. Work from confirmed P/LP variants only."}
    if n>=3: return{"verdict":"MODERATE","color":"#ffd60a","pursue":"selective","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"[Y]","explanation":f"{n} variants. Be selective."}
    return{"verdict":"VERY LOW","color":"#3a5a7a","pursue":"caution","n":n,"per100":round(per100,2),"n_crit":n_crit,"n_lof":n_lof,"icon":"[B]","explanation":f"Only {n} variants. Possible redundancy."}

# ── DOMAIN METADATA ───────────────────────────────────────────────────────────
DOMAINS = {
    "neuro": {
        "label":"Neuroscience & Pharma","icon":"brain","color":"#a855f7",
        "tagline":"Alzheimer's * Parkinson's * Epilepsy * ALS * Psychiatry * BBB",
        "key_genes":["APP","PSEN1","SNCA","LRRK2","GBA","SCN1A","DRD2","SOD1","C9ORF72","MAPT","TREM2","KCNQ2","GRIN2B","TSC1","PRNP"],
        "quick_searches":["Alzheimer disease amyloid tau 2024[pdat]","Parkinson LRRK2 GBA drug 2024[pdat]","epilepsy channelopathy gene therapy 2024[pdat]","ALS TDP-43 C9ORF72 antisense 2024[pdat]"],
        "databases":[("AlzForum","https://www.alzforum.org","AD mutations and failed drugs"),("PDGene","https://pdgene.org","PD GWAS loci"),("DisGeNET","https://www.disgenet.org","Gene-disease associations"),("Allen Brain Atlas","https://portal.brain-map.org","Brain region expression"),("OMIM","https://www.omim.org","Mendelian disease catalogue")],
        "domain_facts":[
            "LRRK2 G2019S: most common dominant PD mutation. >40% of Ashkenazi Jewish and North African Arab PD patients. LRRK2 kinase activity increased 3x -- target for LRRK2 inhibitors (DNL151 Phase 2).",
            "GBA N370S/L444P: heterozygous carriers 5-10x increased PD risk. Homozygous = Gaucher disease. GBA-PD converges on lysosomal dysfunction -- substrate reduction therapy approach.",
            "Tau phosphorylation: 85+ phospho-sites on PhosphoSite. Only disease-causing mutations (R406W FTLD, P301L/S) and NFT-forming sites (Ser202/Thr205 AT8 epitope) are validated signals. All others are kinase noise.",
            "BBB penetration rules: MW <500 Da, logP 1-3, H-bond donors <5, H-bond acceptors <10. P-gp efflux substrate status = CNS failure predictor.",
            "DRD2 occupancy: 65% threshold = therapeutic effect. >80% = extrapyramidal symptoms. This is why clozapine (lower D2, higher 5-HT2A) has different side effect profile.",
            "SCN1A gain vs loss of function: same gene, opposite drug choice. SCN1A LOF (Dravet) -- Na+ channel blockers WORSEN disease. SCN1A GOF (GEFS+) -- Na+ channel blockers TREAT disease.",
            "C9ORF72 GGGGCC repeat >30 copies = ALS/FTD. Causes RNA foci toxicity AND dipeptide repeat proteins AND haploinsufficiency. Most common genetic ALS cause (40% familial).",
            "SOD1 G93A mouse warning: 100+ drugs worked in this model. Zero translated to clinical ALS benefit. Does not model C9ORF72 or TDP-43 pathology (>90% of ALS cases).",
        ],
        "arrb_note":True,"gpcr_protocol":False,
    },
    "onco": {
        "label":"Oncology","icon":"ribbon","color":"#ff2d55",
        "tagline":"Somatic mutations * Immunotherapy * ADCs * Liquid biopsy * Resistance mechanisms",
        "key_genes":["TP53","KRAS","BRCA1","BRCA2","EGFR","HER2","ALK","BRAF","PIK3CA","CDK4","RB1","MYC","BCR-ABL1","JAK2","FLT3"],
        "quick_searches":["KRAS G12C inhibitor resistance 2024[pdat]","tumour mutational burden immunotherapy 2024[pdat]","antibody drug conjugate ADC solid tumour 2024[pdat]","ctDNA liquid biopsy early detection 2024[pdat]"],
        "databases":[("cBioPortal","https://www.cbioportal.org","Cancer genomics cohorts"),("OncoKB","https://www.oncokb.org","Actionable variants 4-level evidence"),("COSMIC","https://cancer.sanger.ac.uk/cosmic","Somatic mutations catalogue"),("DepMap","https://depmap.org","CRISPR dependency 900+ lines"),("TCGA","https://www.cancer.gov/tcga","33 cancer types")],
        "domain_facts":[
            "KRAS G12C: covalently targetable in GDP-bound state (sotorasib, adagrasib approved). KRAS G12D and G12V lack approved inhibitors -- different chemistry required. G12C is ~13% of NSCLC adenocarcinoma.",
            "TP53: mutated >50% all cancers. Hotspot mutations R175H, R248W, R248Q, G245S cause DIFFERENT gain-of-function phenotypes -- not all TP53 mutations are equivalent.",
            "Founder mutation principle: earliest somatic mutation in tumour evolution = primary therapeutic target. Late-arising mutations during drug treatment are passengers -- targeting them causes rapid acquired resistance.",
            "TMB threshold: >=10 mut/Mb predicts pembrolizumab response (FDA pan-tumour 2020). POLE/POLD1 mutations = ultra-high TMB >100 mut/Mb = exceptional IO response even in typically IO-resistant histologies.",
            "HER2-low: IHC 1+ or 2+/ISH- was previously HER2-negative. T-DXd (Enhertu) achieves 57% ORR -- redefined a new targetable population of 50% of all breast cancers.",
            "Biomarker-unselected trial failure: EGFR inhibitors failed in unselected NSCLC until EGFR mutation testing was mandated. Never run a targeted therapy trial without predictive biomarker selection.",
            "BCR-ABL1 T315I gatekeeper mutation: resistant to imatinib, dasatinib, nilotinib, bosutinib. Ponatinib and asciminib (STAMP inhibitor) are the only approved options.",
        ],
        "arrb_note":False,"gpcr_protocol":False,
    },
    "proteins": {
        "label":"Proteins & Structural","icon":"dna","color":"#00e5ff",
        "tagline":"AlphaFold * AlphaMissense * Kinases/Phosphatases * GPCRs * FBM-Filamin * PTMs * Drug design",
        "key_genes":["FLNA","FLNC","ARRB2","EGFR","HER2","KRAS","TP53","BCL2","MDM2","HSP90","GRK2","ADRB2","AGTR1","DRD2","PTEN"],
        "quick_searches":["AlphaFold AlphaMissense protein structure 2024[pdat]","GPCR Filamin cytoskeleton signalling 2024[pdat]","cryo-EM structure membrane protein 2024[pdat]","phosphorylation signalling cancer drug 2024[pdat]"],
        "databases":[("UniProt","https://www.uniprot.org","Gold-standard human proteins"),("AlphaFold DB","https://alphafold.ebi.ac.uk","DeepMind structure predictions"),("AlphaMissense","https://alphamissense.hegelab.org","Per-residue pathogenicity"),("PhosphoSite","https://www.phosphosite.org","PTMs -- phosphorylation, ubiquitination"),("GPCRdb","https://gpcrdb.org","GPCR H8 conservation, FBM motifs"),("STRING DB","https://string-db.org","PPI networks")],
        "domain_facts":[
            "AlphaMissense (DeepMind 2023): scored all 216M possible missense variants in human proteome. Score >=0.564 = pathogenic prediction. Concordant with ClinVar P/LP in ~80% of cases.",
            "FLNA Ser2152: the ONLY validated phosphorylation signal on Filamin A (PhosphoSite highest peak). Conformationally gated by GPCR H8 dislodgement -- PKA cannot phosphorylate in autoinhibited state. All other FLNA phospho-sites are background kinase noise.",
            "H8 FBM mechanism: agonist engages GPCR -- H8 dislodges from membrane -- binds Filamin Ig21 via beta-strand augmentation (Phe inward, Arg outward, Leu inward) -- PKA phosphorylates Ser2152. More proximal than cAMP/IP3/arrestin.",
            "ARRB1/ARRB2 deprioritise: zero confirmed Mendelian disease variants. Double KO mice viable. Phosphorylation codes on ARRB proteins are kinase noise. $4,050,000 in avoidable spend if pursuing ARRB2.",
            "Discordant variants (ClinVar P/LP + AlphaMissense <0.564): act through non-structural mechanisms -- splicing, PPI interface, regulatory. Do NOT do TSA -- do Co-IP or splicing assay instead.",
            "Cryo-EM: now routinely sub-2A for soluble proteins. Below ~1.5A: direct observation of H atoms, water networks, protonation states -- enables drug design without crystal contacts.",
        ],
        "arrb_note":True,"gpcr_protocol":True,
    },
    "microbiome": {
        "label":"Microbiome","icon":"bacteria","color":"#00c896",
        "tagline":"AI functional annotation * TMAO rattling * FMT * Host-microbe * 16S/shotgun * Pathway reannotation",
        "key_genes":["FXR","TLR4","NLRP3","GPR41","GPR43","NOD2","FMO3","FUT2","CARD9","IL10","TGR5","MUC2","AhR","IL18"],
        "quick_searches":["gut microbiome disease mechanism 2024[pdat]","TMAO cardiovascular arrhythmia 2024[pdat]","fecal microbiota transplant clinical 2024[pdat]","microbiome AI machine learning annotation 2024[pdat]"],
        "databases":[("Human Microbiome Project","https://hmpdacc.org","Reference body-site profiles"),("MGnify EBI","https://www.ebi.ac.uk/metagenomics","Metagenome analysis"),("SILVA rRNA","https://www.arb-silva.de","16S/18S taxonomy reference"),("gutMDisorder","http://bio-annotation.cn/gutMDisorder","Gut-disease associations"),("BugSigDB","https://bugsigdb.org","Differential microbiome signatures")],
        "domain_facts":[
            "THE ANNOTATION PROBLEM: Standard tools (KEGG, GO, COG) annotate microbial genes as 'biosynthesis', 'metabolism', 'protein aggregation' -- these terms are useless. This platform uses Claude to reannotate IDs with specific metabolites, host receptor interactions, and disease relevance.",
            "TMAO pathway: gut bacteria convert choline/carnitine -- TMA via TMA lyases (CutC/D) -- liver FMO3 oxidises -- TMAO. Promotes atherosclerosis AND causes GPCR rattling (cardiac arrhythmia via H8-Filamin decoupling).",
            "Akkermansia muciniphila: mucin-degrading, 1-4% of gut microbiome. Inversely associated with obesity, T2D, metabolic syndrome. Promotes GLP-1 secretion, mucus layer integrity, gut barrier function.",
            "SCFAs (butyrate, propionate, acetate): produced by Firmicutes from dietary fibre. Butyrate = primary energy source for colonocytes (70% of needs), HDAC inhibitor, anti-inflammatory. GPR41/GPR43 receptors on immune and enteroendocrine cells.",
            "C. difficile TcdB receptor: binds Frizzled proteins (FZD1/FZD2). Bezlotoxumab (anti-TcdB) FDA approved 2016 -- reduces recurrence by 40%. TcdA binds NECTIN3.",
            "NOD2 in Crohn's disease: most replicated gene. Frameshift variant 3020insC in 15% of Crohn's patients. NOD2 senses muramyl dipeptide from bacterial cell walls -- loss impairs innate response to gut bacteria.",
            "16S vs shotgun metagenomics: 16S cannot resolve species below genus level. Cannot distinguish Bacteroides fragilis (beneficial) from ETBF (enterotoxigenic, carcinogenic). Shotgun required for species-level resolution.",
        ],
        "arrb_note":False,"gpcr_protocol":False,
    },
}

GPCR_PROTOCOL=[
    ("Step 1","Confirm surface expression","Transfect SNAP/CLIP-tagged receptor. SNAP-Surface stain + confocal. Confirm plasma membrane localisation before any assay.","#00e5ff"),
    ("Step 2","G-protein coupling -- cAMP HTRF","Gs: cAMP HTRF (Cisbio 384-well). Gi: GTPgS or cAMP inhibition after forskolin. Primary efficacy readout. WT vs each ClinVar P/LP variant.","#00c896"),
    ("Step 3 -- PRIMARY","Filamin A Ser2152-P (receptor-proximal)","Agonist stimulation -- anti-Filamin A IP -- pSer2152 western (Cell Signaling). H8 dislodgement is the mechanistic signature. MORE PROXIMAL than cAMP, IP3, or beta-arrestin. PhosphoSite highest FLNA peak. Nakamura JBC 2015. IP-protected.","#a855f7"),
    ("Step 4 -- SECONDARY ONLY","Beta-arrestin BRET","RLuc8-receptor + Venus-arrestin2. Biased agonism characterisation ONLY. ARRB2 has zero Mendelian disease variants. ARRB1/ARRB2 KO mice viable. NOT a primary disease readout.","#ff8c42"),
    ("Step 5","Receptor internalisation","SNAP-surface before/after agonist. Measure % receptor lost. Variants in TM bundle or ECLs alter trafficking independently of G-protein coupling.","#ffd60a"),
    ("Step 6","Variant functional panel","Steps 2+3 for each ClinVar P/LP variant simultaneously. Kills cAMP not Filamin-P = G-protein defect. Kills Filamin-P not cAMP = cytoskeletal decoupling. Different biology, different target.","#ff2d55"),
    ("Step 7 -- cardiac only","TMAO rattling assay","Add TMAO 5-50uM. NanoBRET conformational sensor. TMAO increases conformational sampling (rattling) -- misfiring -- reduced Filamin-P -- arrhythmia mechanism.","#ff2d55"),
]

# ── AUTH ──────────────────────────────────────────────────────────────────────
def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()
_USERS={"demo@protellect.com":{"password":_hash("protellect2024"),"name":"Demo User","plan":"free","searches_used":0,"max_searches":10,"lab":{},"onboarded":False},
         "pro@protellect.com":{"password":_hash("pro2024"),"name":"Dr. Researcher","plan":"pro","searches_used":0,"max_searches":500,"lab":{},"onboarded":False}}
def _db():
    if "users_db" not in st.session_state: st.session_state.users_db=_USERS.copy()
    return st.session_state.users_db
def current_user(): return st.session_state.get("user")
def is_logged_in(): return current_user() is not None
def login(email,password):
    db=_db()
    if email not in db: return False,"No account found."
    if db[email]["password"]!=_hash(password): return False,"Incorrect password."
    st.session_state.user={**db[email],"email":email}
    if db[email].get("onboarded"): st.session_state.lab=db[email].get("lab",{})
    return True,"ok"
def register(email,password,name):
    db=_db()
    if email in db: return False,"Email already registered."
    if len(password)<8: return False,"Password must be 8+ chars."
    db[email]={"password":_hash(password),"name":name,"plan":"free","searches_used":0,"max_searches":10,"lab":{},"onboarded":False}
    st.session_state.user={**db[email],"email":email}; return True,"ok"
def logout():
    for k in ["user","domain","lab","onboarded","analysis_cache"]: st.session_state.pop(k,None)
def save_lab(profile):
    u=current_user()
    if not u: return
    db=_db(); e=u["email"]; db[e]["lab"]=profile; db[e]["onboarded"]=True
    st.session_state.user["lab"]=profile; st.session_state.user["onboarded"]=True
    st.session_state.lab=profile; st.session_state.onboarded=True
def can_search():
    u=current_user()
    if not u: return False
    if u.get("plan")=="pro": return True
    return u.get("searches_used",0)<u.get("max_searches",10)
def decrement_search():
    u=current_user()
    if not u or u.get("plan")=="pro": return
    db=_db(); e=u["email"]; db[e]["searches_used"]=db[e].get("searches_used",0)+1
    st.session_state.user["searches_used"]=db[e]["searches_used"]

def render_auth_page():
    st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#010306}
.block-container{padding:2rem 1rem!important;max-width:460px!important;margin:0 auto}
.stTextInput>div>div>input{background:#030810!important;border:1px solid #0d2545!important;color:#d0e8ff!important;border-radius:8px!important}
.stButton>button{background:#00e5ff!important;color:#010306!important;font-weight:700!important;border:none!important;border-radius:8px!important;width:100%!important;font-size:.9rem!important}
.stRadio label{color:#5a8090!important;font-size:.85rem!important}
</style>""",unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;padding:2.5rem 0 1.5rem'><div style='font-size:3rem'>&#128300;</div><div style='font-size:2.4rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div><div style='font-size:.75rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase'>Biology Intelligence Platform</div><div style='width:40px;height:2px;background:#00e5ff;margin:.8rem auto'></div></div>",unsafe_allow_html=True)
    mode=st.radio("",["Sign In","Create Account"],horizontal=True,label_visibility="collapsed")
    if mode=="Sign In":
        email=st.text_input("Email",placeholder="you@lab.com",key="li_email")
        password=st.text_input("Password",type="password",key="li_pw")
        if st.button("Sign In",key="li_btn",type="primary"):
            ok,msg=login(email.strip(),password)
            if ok: st.rerun()
            else: st.error(msg)
        st.markdown("<div style='color:#3a6080;font-size:.74rem;text-align:center;margin-top:.4rem'>Demo: demo@protellect.com / protellect2024</div>",unsafe_allow_html=True)
    else:
        name=st.text_input("Full name",placeholder="Dr. Jane Smith",key="reg_name")
        email=st.text_input("Email",placeholder="you@lab.com",key="reg_email")
        pw=st.text_input("Password (8+ chars)",type="password",key="reg_pw")
        if st.button("Create Account",key="reg_btn",type="primary"):
            ok,msg=register(email.strip(),pw,name.strip())
            if ok: st.rerun()
            else: st.error(msg)

def render_onboarding():
    st.markdown("<div style='text-align:center;padding:2rem 0 1.2rem'><div style='font-size:2.5rem'>&#128300;</div><div style='font-size:2.2rem;font-weight:700;color:#00e5ff'>Protellect</div><div style='font-size:.78rem;color:#3a6080;letter-spacing:.08em;text-transform:uppercase'>Personalise your experience</div><div style='width:40px;height:2px;background:#00e5ff;margin:.6rem auto'></div></div>",unsafe_allow_html=True)
    u=current_user()
    st.markdown(f"<div style='text-align:center;color:#5a8090;font-size:.84rem;margin-bottom:1.2rem'>Welcome, <b style='color:#d0e8ff'>{u.get('name','')}</b></div>",unsafe_allow_html=True)
    with st.form("ob_form"):
        lab_name=st.text_input("Lab / Institute name",placeholder="Smith Lab, Wellcome Sanger Institute",key="ob_lab")
        pi_name=st.text_input("Principal Investigator",placeholder="Prof. Jane Smith",key="ob_pi")
        research_focus=st.text_area("What does your lab research?",placeholder="We study GPCR signalling in cardiac disease, focusing on filamin phosphorylation and arrhythmia...",height=90,key="ob_focus")
        domain_pref=st.selectbox("Primary domain",["Neuroscience & Pharma","Oncology","Proteins & Structural","Microbiome","All equally"],key="ob_domain")
        organisms=st.multiselect("Organisms",["Human","Mouse","Zebrafish","C. elegans","Drosophila","Gut bacteria","In vitro only"],default=["Human"],key="ob_org")
        assay_types=st.multiselect("Primary assays",["Western blot","CRISPR","RNA-seq","16S microbiome","Mass spectrometry","BRET/FRET","SPR/ITC","Flow cytometry","Patch clamp","Computational"],key="ob_assays")
        budget=st.select_slider("Budget tier",["<$10K","$10-50K","$50-200K","$200K-1M",">$1M"],value="$50-200K",key="ob_budget")
        pi_pubmed=st.text_input("PI PubMed search term (to pull your lab papers)",placeholder="Smith J[au] AND GPCR",key="ob_pubmed")
        submitted=st.form_submit_button("Begin Research",type="primary",use_container_width=True)
        if submitted:
            if not lab_name or not research_focus: st.error("Please provide lab name and research focus.")
            else:
                save_lab({"lab_name":lab_name,"pi_name":pi_name,"research_focus":research_focus,"domain_pref":domain_pref,"organisms":organisms,"assay_types":assay_types,"budget":budget,"pi_pubmed":pi_pubmed})
                st.rerun()

# ── SIDEBAR -- domain-specific ─────────────────────────────────────────────────
def render_sidebar(domain_key):
    D=DOMAINS[domain_key]; color=D["color"]; lab=st.session_state.lab or {}
    with st.sidebar:
        # Logo + lab
        st.markdown(f"<div style='color:{color};font-weight:700;font-size:.95rem;padding:.35rem 0'>&#128300; Protellect</div>",unsafe_allow_html=True)
        if lab.get("lab_name"): st.markdown(f"<div style='color:#3a5060;font-size:.7rem;margin-bottom:.35rem'>{lab['lab_name']}</div>",unsafe_allow_html=True)
        # Domain icon + label
        st.markdown(f"<div style='background:{color}18;border:1px solid {color}33;border-radius:8px;padding:.4rem .7rem;margin-bottom:.5rem;font-size:.8rem;color:{color};font-weight:600'>{D['icon'].upper()} {D['label']}</div>",unsafe_allow_html=True)
        # Gene search
        st.markdown("<div style='color:#3a6080;font-size:.68rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin-bottom:.25rem'>Analyse Gene / Protein</div>",unsafe_allow_html=True)
        gene_input=st.text_input("",placeholder="FLNC, EGFR, LRRK2...",key="gene_box",label_visibility="collapsed")
        do_search=st.button("Analyse",key="search_btn",type="primary",use_container_width=True)
        # Quota
        u=current_user()
        if u and u.get("plan","free")=="free":
            used=u.get("searches_used",0); mx=u.get("max_searches",10)
            pct=int(used/mx*100) if mx else 0
            st.markdown(f"<div style='color:#3a6080;font-size:.68rem;text-align:center;margin-top:.2rem'>{used}/{mx} searches used</div>",unsafe_allow_html=True)
        st.markdown("---")
        # Domain-specific quick genes
        st.markdown(f"<div style='color:#3a6080;font-size:.68rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin-bottom:.3rem'>Quick Genes ({D['label'][:8]})</div>",unsafe_allow_html=True)
        for g in D["key_genes"][:10]:
            if st.button(g,key=f"qg_{g}",use_container_width=True):
                st.session_state["_run_gene"]=g; st.rerun()
        st.markdown("---")
        # Lab papers shortcut
        if lab.get("pi_pubmed"):
            if st.button("Pull lab papers",key="lab_papers",use_container_width=True):
                st.session_state["_show_lab_papers"]=True; st.rerun()
        # Domain databases
        st.markdown(f"<div style='color:#3a6080;font-size:.68rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:.3rem 0'>Key Databases</div>",unsafe_allow_html=True)
        for dname,durl,ddesc in D["databases"][:4]:
            st.markdown(f"<a href='{durl}' target='_blank' style='display:block;font-size:.73rem;color:{color};padding:3px 0;border-bottom:1px solid #0d2545;text-decoration:none'>{dname} &#8599;</a>",unsafe_allow_html=True)
        st.markdown("---")
        # Navigation
        if st.button("All Domains",key="back_btn",use_container_width=True):
            st.session_state.domain=None; st.rerun()
        if st.button(f"Sign Out ({u.get('name','').split()[0] if u and u.get('name') else ''})",key="so_btn",use_container_width=True):
            logout(); st.rerun()
    return gene_input,do_search

# ── GENE ANALYSIS (full, all APIs, all tabs) ──────────────────────────────────
def render_gene_analysis(gene,domain_key):
    D=DOMAINS[domain_key]; color=D["color"]; gene=gene.upper().strip()
    if not can_search(): st.error("Search quota reached. Upgrade to Pro."); return
    sh("&#128270;",f"Live Analysis -- {gene}",color)
    with st.spinner(f"Fetching {gene} from UniProt, ClinVar, gnomAD, STRING, OpenTargets, AlphaFold, ClinicalTrials.gov..."):
        pdata=api_uniprot(gene); cv=api_clinvar(gene); partners=api_string(gene)
        ot=api_opentargets(gene); gnomad=api_gnomad(gene); trials=api_clinicaltrials(gene)
        af=api_alphafold(pdata.get("uid","")) if pdata.get("uid") else {}
        am={}  # loaded on demand in AlphaMissense tab
    decrement_search()
    is_arrb=gene in ("ARRB1","ARRB2","BARR1","BARR2")
    gi=gi_score(cv,pdata.get("length",500) if pdata else 500)
    lab=st.session_state.lab or {}

    if is_arrb:
        st.markdown(f"<div style='background:#0a0205;border:2px solid #ff2d55;border-radius:12px;padding:1rem 1.3rem;margin-bottom:.6rem'><div style='color:#ff2d55;font-weight:700;font-size:.98rem;margin-bottom:.2rem'>DEPRIORITISE -- {gene}: $4,050,000 in avoidable spend</div><div style='color:#6a3040;font-size:.79rem;line-height:1.65'>ARRB1/ARRB2 double KO mice viable and fertile. Zero confirmed Mendelian disease variants in ClinVar. Beta-arrestin phosphorylation codes = kinase noise. Redirect to: Filamin A Ser2152-P assay ($2K) * ADRB1 * ADRB2 * AGTR1 * MAS1</div><div style='display:flex;gap:5px;flex-wrap:wrap;margin-top:.45rem'>"+"".join(f"<span style='background:#ff2d5511;border:1px solid #ff2d5533;border-radius:6px;padding:2px 8px;font-size:.69rem;color:#ff8c42'>${v:,} -- {k}</span>" for k,v in [("HTS screen",2500000),("CRISPR x6",150000),("Cryo-EM",500000),("Mouse x2",800000),("BRET screens",100000)])+"</div></div>",unsafe_allow_html=True)

    gc=gi.get("color","#3a5a7a")
    af_link=f"<a href='{af.get('af_url','')}' target='_blank' style='font-size:.72rem;color:#a855f7;margin-left:auto'>AlphaFold &#8599;</a>" if af.get("af_url") else ""
    st.markdown(f"<div style='background:{gc}10;border:1px solid {gc}44;border-radius:11px;padding:.8rem 1.05rem;margin-bottom:.45rem'><div style='color:{gc};font-weight:700;font-size:.9rem'>{gi.get('verdict','')}</div><div style='color:#5a8090;font-size:.77rem;margin-top:2px'>{gi.get('explanation','')}</div><div style='display:flex;gap:12px;margin-top:.4rem;align-items:center'><span style='font-size:.74rem;color:#3a6080'>P/LP: <b style='color:{gc}'>{gi.get('n',0)}</b></span><span style='font-size:.74rem;color:#3a6080'>Per 100aa: <b style='color:{gc}'>{gi.get('per100',0)}</b></span><span style='font-size:.74rem;color:#3a6080'>CRITICAL: <b style='color:{gc}'>{gi.get('n_crit',0)}</b></span><span style='font-size:.74rem;color:#3a6080'>pLI: <b style='color:{gc}'>{gnomad.get('pLI','--')}</b></span>{af_link}</div></div>",unsafe_allow_html=True)

    tabs=st.tabs(["Protein","Variants","AlphaMissense","Pathways & PTMs","Drugs","Trials","Literature","Experiments","Assay Upload"])
    t_prot,t_var,t_am,t_path,t_drugs,t_trial,t_lit,t_exp,t_assay=tabs

    with t_prot:
        c1,c2=st.columns(2)
        with c1:
            if pdata.get("name"):
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:10px;padding:.72rem .95rem;margin-bottom:.4rem'><div style='color:{color};font-weight:600;font-size:.87rem'>{pdata['name']}</div><div style='color:#3a6080;font-size:.71rem'>{gene} * {pdata.get('length',0)} aa</div><div style='color:#3a5060;font-size:.75rem;line-height:1.58;margin-top:.32rem'>{pdata.get('function','')[:400]}{'...' if len(pdata.get('function',''))>400 else ''}</div></div>",unsafe_allow_html=True)
            for d in pdata.get("diseases",[])[:5]:
                st.markdown(f"<div style='padding:3px 0;border-bottom:1px solid #0d2545;font-size:.77rem'><span style='color:#d0e8ff'>{d['name']}</span><div style='color:#2a4050;font-size:.71rem'>{d.get('desc','')[:90]}</div></div>",unsafe_allow_html=True)
            if pdata.get("ptms"):
                sh("PTM","PTM data (UniProt)",color)
                for ptm in pdata["ptms"]: st.markdown(f"<div style='color:#5a8090;font-size:.74rem;padding:2px 0;border-bottom:1px solid #0d2545'>{ptm[:180]}</div>",unsafe_allow_html=True)
            if pdata.get("tissues"):
                sh("","Tissue expression",color)
                for t in pdata["tissues"]: st.markdown(f"<div style='color:#5a8090;font-size:.74rem;padding:2px 0'>{t[:150]}</div>",unsafe_allow_html=True)
        with c2:
            if partners:
                sh("","STRING Partners (score >=700)",color)
                for p in partners: st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.77rem'><span style='color:#d0e8ff'>{p['partner']}</span><span style='color:#00c896;font-size:.72rem'>{p['score']}</span></div>",unsafe_allow_html=True)
            if gnomad:
                sh("","gnomAD Constraint",color); cc=st.columns(3)
                with cc[0]: st.metric("pLI",gnomad.get("pLI","--"))
                with cc[1]: st.metric("o/e LoF",gnomad.get("oe_lof","--"))
                with cc[2]: st.metric("o/e Mis",gnomad.get("oe_mis","--"))
            if ot.get("disease_assoc"):
                sh("","OpenTargets Disease Assoc.",color)
                for da in ot["disease_assoc"][:5]: st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.77rem'><span style='color:#d0e8ff'>{da['name']}</span><span style='color:#ff8c42;font-size:.72rem'>{da['score']}</span></div>",unsafe_allow_html=True)
            if pdata.get("keywords"): sh("","Keywords",color); st.markdown(" ".join(badge(k,"#3a6080") for k in pdata["keywords"][:10]),unsafe_allow_html=True)

    with t_var:
        if is_arrb: warn_box("Disease triage suppressed","ClinVar entries for ARRB proteins reflect GPCR-driven disease co-occurrence, not independent pathogenicity.")
        elif not cv: st.info("No P/LP variants in ClinVar for this gene.")
        else:
            sh("","ClinVar -- Pathogenic / Likely Pathogenic",color)
            info_box("ClinVar is the triage filter -- not the truth source. Multi-star reviewed P/LP variants are the starting point. Validate mechanistically before investing.",color)
            for v in cv[:20]:
                rc={"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}.get(v["ml_rank"],"#3a5a7a")
                with st.expander(f"{badge(v['ml_rank'],rc)} {v['title'][:65]}...",expanded=False):
                    st.markdown(f"{badge(v['cs'],'#4a90d9')} {'*'*v['stars'] if v['stars'] else 'No review'} <a href='{v['url']}' target='_blank' style='font-size:.7rem'>ClinVar &#8599;</a>",unsafe_allow_html=True)
                    if v.get("condition"): st.markdown(f"<div style='color:#5a8090;font-size:.75rem;margin-top:2px'>{v['condition'][:150]}</div>",unsafe_allow_html=True)

    with t_am:
        sh("","AlphaMissense (DeepMind) -- Per-Residue Pathogenicity",color)
        uid_for_am = pdata.get("uid","")
        if uid_for_am and st.button("Load AlphaMissense Data", key=f"load_am_{gene}", type="primary"):
            with st.spinner("Fetching AlphaMissense scores (DeepMind)..."):
                am = api_alphamissense(uid_for_am)
            st.rerun()
        elif not uid_for_am:
            st.info("No UniProt accession -- AlphaMissense not available.")
        if am and am.get("pos_max_scores"):
            cc=st.columns(4)
            with cc[0]: st.metric("AM Pathogenic (>=0.564)",am.get("pathogenic_count",0))
            with cc[1]: st.metric("Ambiguous",am.get("ambiguous_count",0))
            with cc[2]: st.metric("Benign (<0.34)",am.get("benign_count",0))
            with cc[3]: st.metric("Mean AM Score",am.get("mean_score","--"))
            pos_scores=am.get("pos_max_scores",{})
            if pos_scores:
                positions=sorted(pos_scores.keys())[:300]
                scores=[pos_scores[p] for p in positions]
                cv_positions={}
                for v in cv:
                    m=re.findall(r'p\.[A-Za-z]+(\d+)[A-Za-z]',v.get("title",""))
                    for pos in m: cv_positions[int(pos)]=v.get("ml_rank","")
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=positions,y=scores,mode="lines",name="AM score",line=dict(color="#5a8090",width=1),fill="tozeroy",fillcolor="rgba(90,128,144,0.08)"))
                fig.add_hline(y=0.564,line_dash="dash",line_color="#ff8c42",annotation_text="Pathogenic threshold",annotation_font_color="#ff8c42")
                for pos,rank in cv_positions.items():
                    if pos in pos_scores:
                        rc2={"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#5a8090"}.get(rank,"#5a8090")
                        fig.add_trace(go.Scatter(x=[pos],y=[pos_scores[pos]],mode="markers",marker=dict(color=rc2,size=9,symbol="diamond"),showlegend=False,hovertemplate=f"Pos {pos}<br>ClinVar: {rank}<br>AM: {pos_scores[pos]:.3f}<extra></extra>"))
                fig.update_layout(height=280,plot_bgcolor="#010306",paper_bgcolor="#010306",font=dict(color="#d0e8ff",size=10),margin=dict(l=35,r=15,t=35,b=35),title=dict(text=f"AlphaMissense + ClinVar Overlay -- {gene}",font=dict(color=color,size=11)),xaxis=dict(title="Residue position",gridcolor="#0d2545"),yaxis=dict(title="AM Score",gridcolor="#0d2545",range=[0,1]),showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
                if cv:
                    concordant=sum(1 for pos in cv_positions if pos in pos_scores and pos_scores[pos]>=0.564)
                    discordant=sum(1 for pos in cv_positions if pos in pos_scores and pos_scores[pos]<0.564)
                    info_box(f"ClinVar x AlphaMissense concordance: {concordant} concordant (ClinVar P/LP + AM >=0.564 = structural mechanism -- use TSA/pharmacochaperone) * {discordant} discordant (ClinVar P/LP but AM <0.564 = non-structural -- use Co-IP/functional assay instead).",color)
        else: st.info("AlphaMissense not available for this entry.")

    with t_path:
        t_kin,t_gpcr,t_chem=st.tabs(["Kinases & PTMs","GPCR Signalling","Chemical Structures"])
        with t_kin:
            sh("","Phosphorylation Signal vs Noise Rule",color)
            info_box("A phosphorylation site is a VALIDATED SIGNAL only if its specific residue mutation causes human disease (ClinVar P/LP). FLNA Ser2152 is the only validated signal on Filamin A -- conformationally gated by GPCR H8 binding. All other FLNA phospho-sites are background kinase noise. This rule applies universally.",color)
            if pdata.get("ptms"):
                sh("","PTM Data from UniProt",color)
                for ptm in pdata["ptms"]: st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:8px;padding:.55rem .85rem;margin-bottom:.22rem;color:#6a9ab0;font-size:.78rem'>{ptm}</div>",unsafe_allow_html=True)
            sh("","Kinase Reference",color)
            kinases=[("PKA","FLNA Ser2152 (SIGNAL -- FBM-gated), CREB Ser133, HSL Ser563","cAMP","H89, PKI"),("GRK2","ADRB2 Ser355/356, AGTR1 Ser332 (desensitisation)","Gbg after GPCR activation","compound 101, paroxetine scaffold"),("GSK3b","Tau Ser396 (NOISE in cell lines -- no disease variant), b-catenin Ser33","Active by default, inhibited by Akt","Lithium, SB216763, CHIR99021"),("CDK5","Tau Ser202/Thr205 (AT8 epitope -- NFT relevant)","p35 (normal), p25 (aberrant cleavage = toxic)","roscovitine, dinaciclib"),("LRRK2","Rab8A Thr72, Rab10 Thr73","GTP binding, G2019S GOF mutation","BIIB122, DNL151, MLi-2"),]
            for kname,ksubs,kact,kinh in kinases:
                with st.expander(f"{kname}",expanded=False):
                    st.markdown(f"**Substrates:** {ksubs}")
                    st.markdown(f"**Activated by:** {kact}")
                    st.markdown(f"**Inhibitors:** {kinh}")
        with t_gpcr:
            is_gpcr_gene=any(x in gene for x in ["ADRB","AGTR","MAS","CHRM","ADRA","DRD","HTR","CCR","CXCR"])
            is_arrb_gene=gene in ("ARRB1","ARRB2")
            if is_arrb_gene:
                warn_box("Beta-arrestin -- DEPRIORITISE","Zero Mendelian disease variants. KO mice viable. Do not use as primary GPCR readout or drug target. Use Filamin Ser2152-P instead.")
            else:
                sh("","GPCR Signalling Pathways",color)
                st.markdown("<div style='color:#5a8090;font-size:.78rem;margin-bottom:.5rem'>Step 3 (Filamin Ser2152-P) is the IP-protected primary readout. Step 4 (beta-arrestin) is secondary only.</div>",unsafe_allow_html=True)
                for step,title,body,clr in GPCR_PROTOCOL:
                    primary="PRIMARY" in step; secondary="SECONDARY" in step
                    lbl=f"{'* ' if primary else ''}{step} -- {title}"
                    with st.expander(lbl,expanded=primary):
                        st.markdown(f"<div style='background:#020810;border-left:3px solid {clr};padding:.65rem .95rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.79rem;line-height:1.65'>{body}</div>",unsafe_allow_html=True)
                st.markdown(" ".join([src_link("GPCRdb","https://gpcrdb.org"),src_link("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546"),src_link("Nakamura JBC 2015","https://doi.org/10.1074/jbc.M115.671826")]),unsafe_allow_html=True)
        with t_chem:
            sh("","Chemical Structure (PubChem)",color)
            compound=st.text_input("Drug / compound name",placeholder="imatinib, sotorasib, venetoclax",key=f"chem_{gene}")
            if compound:
                with st.spinner("Fetching from PubChem..."):
                    cd=api_pubchem(compound)
                if cd.get("cid"):
                    c1c,c2c=st.columns([1,2])
                    with c1c:
                        if cd.get("img_url"):
                            try: st.image(cd["img_url"],width=180,caption=compound)
                            except: pass
                        _cid = cd.get("cid","")
                        st.markdown(f"<a href='https://pubchem.ncbi.nlm.nih.gov/compound/{_cid}' target='_blank' style='font-size:.72rem'>PubChem {_cid} &#8599;</a>",unsafe_allow_html=True)
                    with c2c:
                        for label,val in [("Formula",cd.get("formula","")),("MW",f"{cd.get('mw','')} Da"),("LogP",str(cd.get("logp",""))),("SMILES",cd.get("smiles","")[:60])]:
                            if val: st.markdown(f"<div style='display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#5a8090'>{label}</span><span style='color:#d0e8ff'>{val}</span></div>",unsafe_allow_html=True)
                else: st.info(f"No structure found for {compound}.")

    with t_drugs:
        if ot.get("drugs"):
            sh("","Known Drugs -- OpenTargets",color)
            ph_l={4:"Approved",3:"Phase 3",2:"Phase 2",1:"Phase 1",0:"Preclinical"}; ph_c={4:"#00c896",3:"#4a90d9",2:"#ffd60a",1:"#5a8090",0:"#3a4050"}
            for drug in ot["drugs"]:
                ph=int(drug.get("phase",0) or 0)
                st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #0d2545;font-size:.79rem'><span style='color:#d0e8ff'>{drug['name']}</span><span style='background:{ph_c.get(ph,'#3a4050')}22;color:{ph_c.get(ph,'#5a8090')};padding:2px 7px;border-radius:6px;font-size:.69rem'>{ph_l.get(ph,'?')}</span></div>",unsafe_allow_html=True)
        if ot.get("tractability"): sh("","Tractability",color); st.markdown(" ".join(badge(t,"#00c896") for t in ot["tractability"]),unsafe_allow_html=True)
        if not ot.get("drugs") and not ot.get("tractability"): st.info("No drug data found.")

    with t_trial:
        sh("","Active Recruiting Trials -- ClinicalTrials.gov",color)
        if not trials: st.info("No actively recruiting trials found.")
        for tr in trials:
            ph_clr="#4a90d9" if "3" in tr.get("phase","") else "#ffd60a" if "2" in tr.get("phase","") else "#5a8090"
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.58rem .82rem;margin-bottom:.22rem;display:flex;justify-content:space-between;align-items:center'><div style='flex:1'><a href='{tr['url']}' target='_blank' style='color:#d0e8ff;font-size:.79rem;font-weight:500'>{tr['title']}</a><div style='color:#2a4050;font-size:.7rem;margin-top:1px'>{tr['sponsor']} * {tr['nct']}</div></div><span style='background:{ph_clr}22;color:{ph_clr};padding:2px 7px;border-radius:6px;font-size:.69rem;margin-left:8px;white-space:nowrap'>{tr['phase'] or '?'}</span></div>",unsafe_allow_html=True)

    with t_lit:
        sh("","PubMed 2022-2025",color)
        lit_q=f"{gene}[gene] 2022:2025[pdat]"
        if lab.get("pi_pubmed"):
            show_lab=st.checkbox("Show only my lab's papers about this gene",key=f"lab_lit_{gene}")
            if show_lab: lit_q=f"{gene} AND ({lab['pi_pubmed']})"
        with st.spinner("Fetching papers..."):
            papers=api_pubmed(lit_q,12)
        if not papers: st.info("No papers found.")
        for p in papers:
            wk=detect_weaknesses(p["title"])
            with st.expander(f"{tier_badge(p['tier'])} {p['title'][:70]}{'...' if len(p['title'])>70 else ''}",expanded=False):
                st.markdown(f"<div style='font-size:.75rem;color:#5a8090'>{p['authors']} * {p['journal']} * {p['year']}</div>",unsafe_allow_html=True)
                pm=p.get("pmid",""); doi=p.get("doi",""); url=p.get("url","")
                if doi: st.markdown(f"<a href='https://doi.org/{doi}' target='_blank' style='font-size:.69rem'>DOI &#8599;</a> <a href='{url}' target='_blank' style='font-size:.69rem'>PubMed {pm} &#8599;</a>",unsafe_allow_html=True)
                else: st.markdown(f"<a href='{url}' target='_blank' style='font-size:.69rem'>PubMed {pm} &#8599;</a>",unsafe_allow_html=True)
                for wt,wb in wk: warn_box(wt,wb)

    with t_exp: render_experiments(gene,pdata,cv,gnomad,ot,partners,am,is_arrb,color,lab)
    with t_assay: render_assay_tab(gene,color,lab)

def render_experiments(gene,pdata,cv,gnomad,ot,partners,am,is_arrb,color,lab):
    if is_arrb: warn_box("Experiments suppressed","Zero disease variants. Redirect investment to genetically validated targets."); return
    n_cv=len(cv); pli=gnomad.get("pLI",0); n_crit=sum(1 for v in cv if v.get("ml_rank")=="CRITICAL")
    n_lof=sum(1 for v in cv if any(k in v.get("title","").lower() for k in ["frameshift","nonsense","stop gained","del"]))
    n_miss=n_cv-n_lof; top_cv=cv[0].get("title","")[:35] if cv else "top pathogenic variant"
    top_part=partners[0]["partner"] if partners else "key interaction partner"
    am_concordant=0
    if am and am.get("pos_max_scores"):
        pos_scores=am["pos_max_scores"]
        for v in cv[:10]:
            m=re.findall(r'p\.[A-Za-z]+(\d+)[A-Za-z]',v.get("title",""))
            for pos in m:
                if int(pos) in pos_scores and pos_scores[int(pos)]>=0.564: am_concordant+=1
    is_gpcr=any(x in gene for x in ["ADRB","AGTR","MAS1","CHRM","ADRA","DRD","HTR","CCR","CXCR"])
    is_kin=any(x in gene for x in ["GRK","CDK","BRAF","EGFR","ALK","FGFR","MET","RET","JAK","ABL","LRRK"])
    is_fil=gene in ("FLNA","FLNB","FLNC")
    is_sm=any("small" in t.lower() for t in ot.get("tractability",[]))
    budget_ok=lab.get("budget","$50-200K") not in ["<$10K","$10-50K"]
    exps=[]
    exps.append({"n":"Rosetta DeltaDeltaG + AlphaMissense","cost":"Free","time":"1-3d","p":.92,"v":8,"first":True,"body":f"Dual zero-cost screen: Rosetta scores structural destabilisation, AlphaMissense (DeepMind) provides independent pathogenicity. Concordant (ClinVar P/LP + AM >=0.564 + DeltaDeltaG >=2 REU) = highest priority -- TSA/chaperone. Discordant (ClinVar P/LP, AM <0.564) = non-structural mechanism -- Co-IP or splicing assay instead. {am_concordant} concordant variants detected."})
    if n_lof>n_miss: exps.append({"n":f"Western blot -- protein level {n_lof} LoF variants","cost":"$500","time":"1 wk","p":.90,"v":9,"first":True,"body":f"LoF-dominant ({n_lof}/{n_cv} P/LP = frameshift/stop-gain). Anti-{gene} antibody (HPA-validated). CRISPR knock-in or patient cells. pLI={pli} -- {'expect absent band (NMD/degradation)' if pli>0.8 else 'may show truncated band (NMD-escape)'}. Absent = supplementation strategy. Truncated = dominant-negative approach."})
    elif n_miss>0: exps.append({"n":f"TSA/DSF -- {min(n_crit+3,8)} missense variants vs WT","cost":"$2,000","time":"2 wks","p":.85,"v":9,"first":True,"body":f"Missense-dominant ({n_miss}/{n_cv}). DSF (SYPRO Orange, 384-well). DeltaTm <=-2C = structurally destabilising -- pharmacochaperone screen (Prestwick 1,280 approved drugs, $2K, 2 wks -- fastest clinical candidate path). DeltaTm <1C = functional mechanism -- Co-IP with {top_part} next. AM concordance strengthens structural interpretation."})
    if is_gpcr: exps.append({"n":f"Filamin Ser2152-P western -- agonist-stimulated {gene}","cost":"$2,000","time":"1 wk","p":.90,"v":10,"first":True,"body":f"H8 helix dislodgement -- Filamin Ig21 binding -- PKA phosphorylates Ser2152. MORE PROXIMAL than cAMP, IP3, or beta-arrestin. Anti-Filamin A IP -- pSer2152 western (Cell Signaling). Variant in H8/ICL3 = reduced Filamin-P despite normal cAMP. PhosphoSite highest FLNA peak = only non-noise signal. Nakamura JBC 2015. IP-protected."})
    if is_gpcr: exps.append({"n":f"cAMP HTRF -- G-protein coupling {top_cv[:20]}...","cost":"$3,000","time":"2 wks","p":.85,"v":8,"first":False,"body":f"Gs/Gi primary coupling. cAMP HTRF (Cisbio 384-well). WT vs each P/LP variant. Kills cAMP not Filamin-P = G-protein defect. Kills Filamin-P not cAMP = cytoskeletal decoupling. Different mechanism, different target."})
    if is_kin: exps.append({"n":f"ADP-Glo kinase assay -- {top_cv[:22]}...","cost":"$5,000","time":"3 wks","p":.85,"v":9,"first":True,"body":f"ADP-Glo (Promega) = most direct kinase activity readout. WT vs {top_cv} at matched concentration (confirm by western first). >=70% reduced = LoF confirmed. Unchanged = allosteric defect -- test {top_part} interaction. Before HTS: KINOMEscan 468-kinase panel ($50K) for selectivity confirmation."})
    if is_fil: exps.append({"n":"SPR -- Filamin Ig21 vs GPCR FBM peptides","cost":"$8,000","time":"3 wks","p":.85,"v":10,"first":True,"body":f"Pathogenic FLNA variants in Ig19-21 disrupt FBM binding. Immobilise Filamin Ig21 on CM5 chip. Analytes: AT1R C-tail (positive control), MAS1 C-tail, {top_cv[:22]}... peptide. KD >10-fold increased = FBM disruption confirmed. Follow with PKA Ser2152-P assay."})
    crispr_ok=n_crit>=2 and budget_ok
    exps.append({"n":f"CRISPR knock-in -- {top_cv[:28]}...","cost":"$25,000","time":"8 wks","p":.80 if crispr_ok else .35,"v":10 if crispr_ok else 3,"first":False,"body":f"{'JUSTIFIED: ' + str(n_crit) + ' CRITICAL variants + budget allows.' if crispr_ok else 'PREMATURE -- run TSA/western first. Only ' + str(n_crit) + ' CRITICAL variants.'} HDR in {gene} locus. Screen >=50 clones Sanger + western. Readout: {'Filamin Ser2152-P' if is_gpcr else 'kinase activity' if is_kin else 'disease-relevant assay'}. Positive = ClinGen PS3 evidence. pLI={pli}."})
    if top_part and top_part!="key interaction partner": exps.append({"n":f"AP-MS -- {gene}:{top_part} WT vs {top_cv[:18]}...","cost":"$15,000","time":"6 wks","p":.75,"v":8,"first":False,"body":f"Endogenous 3xFLAG-tag {gene} via CRISPR. Anti-FLAG IP x 3 replicates. TMT-LC-MS/MS. SAINTexpress + CRAPome filtering. Hypothesis: {top_cv[:25]}... reduces interaction with {top_part}. Gained HSP70/HSP90 = misfolding/dominant-negative."})
    if is_sm or n_miss>5: exps.append({"n":"Pharmacochaperone screen -- Prestwick 1,280 drugs","cost":"$3,000","time":"2 wks","p":.60,"v":8,"first":False,"body":"Screen Prestwick at 10uM by DSF. Flag DeltaTm >=1C. Dose-response top 20. Cellular rescue: add hit to CRISPR mutant cells. Approved drug = known safety, accelerated clinical translation."})
    first=[e for e in exps if e.get("first")]; rest=sorted([e for e in exps if not e.get("first")],key=lambda x:-x["v"])
    for i,exp in enumerate(first+rest):
        border="#00c896" if exp.get("first") else "#0d2545"
        with st.expander(f"{'DO FIRST -- ' if exp.get('first') else f'#{i+1} -- '}{exp['n']}  *  {exp['cost']}  *  {exp['time']}",expanded=(i<2)):
            cl,cr=st.columns([4,1])
            with cl: st.markdown(f"<div style='background:#020810;border-left:3px solid {border};padding:.68rem .95rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.79rem;line-height:1.65'>{exp['body']}</div>",unsafe_allow_html=True)
            with cr: st.markdown(f"<div style='background:#030810;border:1px solid #0d2545;border-radius:9px;padding:.55rem;text-align:center'><div style='color:#3a6080;font-size:.62rem;font-weight:600;text-transform:uppercase'>P(success)</div><div style='color:#ffd60a;font-size:1.1rem;font-weight:700'>{int(exp['p']*100)}%</div><div style='color:#3a6080;font-size:.62rem;margin-top:2px'>Value</div><div style='color:#00c896;font-size:.88rem;font-weight:600'>{exp['v']}/10</div></div>",unsafe_allow_html=True)

def render_assay_tab(gene,color,lab):
    sh("","Upload Assay Data (Wet-lab or Dry-lab)",color)
    st.markdown("<div style='color:#5a8090;font-size:.78rem;margin-bottom:.5rem'>Supported: TSA/DSF, western blot densitometry, RNA-seq DEG tables, 16S OTU tables, ELISA, proteomics, metabolomics, binding kinetics. CSV, TSV, or Excel.</div>",unsafe_allow_html=True)
    uploaded=st.file_uploader("Upload assay file",type=["csv","tsv","xlsx","xls"],key=f"assay_{gene}")
    extra_ctx=st.text_area("Experimental context (optional)",placeholder="e.g. Cells treated with 10uM compound X for 24h. Anti-pSer2152 antibody used.",height=65,key=f"ectx_{gene}")
    if uploaded:
        try:
            df=pd.read_csv(uploaded) if uploaded.name.endswith((".csv",".tsv")) else pd.read_excel(uploaded)
        except: df=pd.DataFrame()
        if df.empty: st.error("Could not parse file."); return
        st.markdown(f"<div style='color:{color};font-size:.78rem;margin-bottom:.3rem'>{df.shape[0]} rows x {df.shape[1]} cols</div>",unsafe_allow_html=True)
        with st.expander("Preview data",expanded=False): st.dataframe(df.head(8),use_container_width=True)
        # Simple auto-analysis
        cols=df.columns.tolist()
        lfc_col=next((c for c in cols if "log2" in c.lower() and "fold" in c.lower()),None)
        pval_col=next((c for c in cols if "padj" in c.lower() or "fdr" in c.lower() or "p_adj" in c.lower()),None)
        tm_col=next((c for c in cols if any(x in c.lower() for x in ["tm","melt","delt"])),None)
        if lfc_col and pval_col:
            sh("","RNA-seq DEG Analysis",color)
            df[lfc_col]=pd.to_numeric(df[lfc_col],errors="coerce"); df[pval_col]=pd.to_numeric(df[pval_col],errors="coerce")
            df=df.dropna(subset=[lfc_col,pval_col]); df["neg_log_p"]=-np.log10(df[pval_col].clip(lower=1e-300)); df["dir"]=df[lfc_col].apply(lambda x:"Up" if x>1 else("Down" if x<-1 else "NS"))
            up=(df["pval_col"]<0.05).sum() if "pval_col" in df.columns else (df[pval_col]<0.05).sum()
            fig=px.scatter(df,x=lfc_col,y="neg_log_p",color="dir",color_discrete_map={"Up":"#ff2d55","Down":"#4a90d9","NS":"#3a5a7a"},title="Volcano Plot",labels={lfc_col:"log2 FC","neg_log_p":"-log10(adj.p)"},height=350)
            fig.add_hline(y=-np.log10(0.05),line_dash="dash",line_color="#ffd60a")
            fig.add_vline(x=1,line_dash="dash",line_color="#ffd60a"); fig.add_vline(x=-1,line_dash="dash",line_color="#ffd60a")
            fig.update_layout(plot_bgcolor="#010306",paper_bgcolor="#010306",font=dict(color="#d0e8ff",size=10))
            st.plotly_chart(fig,use_container_width=True)
        elif tm_col:
            sh("","TSA/DSF Analysis",color)
            df[tm_col]=pd.to_numeric(df[tm_col],errors="coerce")
            samp_col=next((c for c in cols if any(x in c.lower() for x in ["sample","name","variant","protein"])),cols[0])
            wt_tm=None
            wt_rows=df[df[samp_col].astype(str).str.lower().str.contains("wt|wild|control",na=False)]
            if not wt_rows.empty: wt_tm=float(wt_rows[tm_col].mean())
            fig=go.Figure()
            for _,row in df.iterrows():
                tm_v=row[tm_col]; delta=round(tm_v-wt_tm,2) if wt_tm else None
                is_wt="wt" in str(row[samp_col]).lower()
                clr="#00e5ff" if is_wt else ("#ff2d55" if delta and delta<=-2 else "#00c896" if delta and delta>=2 else "#ffd60a")
                fig.add_trace(go.Bar(x=[str(row[samp_col])],y=[tm_v],marker_color=clr,showlegend=False,hovertemplate=f"{row[samp_col]}<br>Tm: {tm_v:.1f}C" + (f"<br>DeltaTm: {delta:.1f}C" if delta else "")))
            if wt_tm: fig.add_hline(y=wt_tm,line_dash="dash",line_color="#00e5ff")
            fig.update_layout(height=300,plot_bgcolor="#010306",paper_bgcolor="#010306",font=dict(color="#d0e8ff",size=10),margin=dict(l=40,r=15,t=35,b=55),xaxis=dict(tickangle=45),title=dict(text="TSA/DSF -- Tm comparison",font=dict(color=color)))
            st.plotly_chart(fig,use_container_width=True)
            info_box("Red bars (DeltaTm <=-2C) = structurally destabilising -- pharmacochaperone screen next. Yellow = marginal -- functional mechanism likely. Green = stabilised compound hit.",color)
        else:
            st.dataframe(df.describe(),use_container_width=True)
        if st.button("AI Interpret Results",key=f"ai_assay_{gene}",type="primary"):
            client=_ai_client()
            if not client: st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets for AI interpretation."); return
            prompt=f"You are a senior biomedical scientist interpreting assay data for {gene}.\n\nLab context: {lab.get('research_focus','')}\nExtra context: {extra_ctx}\n\nData summary:\nColumns: {list(df.columns)}\nShape: {df.shape}\nFirst 5 rows:\n{df.head().to_string()}\nStats:\n{df.describe().to_string()}\n\nProvide: 1) Data quality assessment 2) Key findings for {gene} 3) Biological interpretation 4) Next experiments 5) Potential artefacts. Be specific -- no vague statements."
            with st.spinner("Claude is interpreting your results..."):
                try:
                    resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=1200,messages=[{"role":"user","content":prompt}])
                    interp="".join(b.text for b in resp.content if hasattr(b,"text"))
                    st.markdown(f"<div style='background:#020d10;border:1px solid #00e5ff33;border-radius:10px;padding:.9rem 1.1rem'>{interp}</div>",unsafe_allow_html=True)
                except Exception as e: st.error(f"AI error: {e}")

# ── MICROBIOME DOMAIN (with AI annotation) ─────────────────────────────────────
def render_microbiome_domain():
    color="#00c896"
    gene_input,do_search=render_sidebar("microbiome")
    run_gene=st.session_state.pop("_run_gene",None)
    if do_search and gene_input.strip(): run_gene=gene_input.strip()
    show_lab=st.session_state.pop("_show_lab_papers",False)
    lab=st.session_state.lab or {}
    st.markdown(f"<div style='padding:1rem 1.4rem .45rem;border-bottom:1px solid #0d2545;display:flex;align-items:center;gap:10px'><span style='font-size:1.65rem'>&#129440;</span><div><div style='color:{color};font-weight:700;font-size:1.05rem'>Microbiome Intelligence</div><div style='color:#2a4050;font-size:.74rem'>AI functional annotation * TMAO * FMT * Host-microbe * Pathway reannotation</div></div></div>",unsafe_allow_html=True)
    if run_gene: render_gene_analysis(run_gene,"microbiome"); st.markdown("<hr style='border-color:#0d2545;margin:.5rem 0'>",unsafe_allow_html=True)
    if show_lab and lab.get("pi_pubmed"):
        sh("","Your Lab Papers",color)
        with st.spinner("Fetching lab papers..."):
            lp=api_pubmed(lab["pi_pubmed"]+" 2020:2025[pdat]",6)
        for p in lp:
            _purl = p.get("url",""); _ppmid = p.get("pmid",""); _ptitle = p.get("title","")[:80]; _pauth = p.get("authors",""); _pjnl = p.get("journal",""); _pyr = p.get("year","")
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:8px;padding:.55rem .82rem;margin-bottom:.2rem'><div style='color:#d0e8ff;font-size:.79rem;font-weight:500'>{_ptitle}...</div><div style='color:#3a6080;font-size:.71rem'>{_pauth} * {_pjnl} * {_pyr} * <a href='{_purl}' target='_blank'>PMID {_ppmid}</a></div></div>",unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#0d2545;margin:.5rem 0'>",unsafe_allow_html=True)
    tabs=st.tabs(["AI Gene Annotation","Microbe Profile","Upload Annotation File","Literature","Domain Facts"])
    with tabs[0]:
        sh("","AI-Powered Microbial Gene Function Reannotation",color)
        info_box("THE ANNOTATION PROBLEM SOLVED: Standard tools (KEGG, GO, COG) produce useless annotations like 'biosynthesis', 'chemosynthesis', 'protein aggregation'. This tool uses Claude to translate database IDs into specific metabolites, host receptor interactions, disease relevance, and community-level function. No one else does this.",color)
        ids_input=st.text_area("Paste gene IDs / functional annotations (one per line)",placeholder="COG0001\nK00001\nGO:0009058\nbiosynthesis\nbeta-oxidation of fatty acids\nphosphate ABC transporter",height=110,key="micro_ids")
        ctx=st.text_input("Research context",placeholder="Gut dysbiosis in IBD, Firmicutes-Bacteroidetes ratio changes",key="micro_ctx")
        if st.button("Reannotate with Claude",key="micro_btn",type="primary"):
            if not ids_input.strip(): st.warning("Paste some gene IDs first."); return
            client=_ai_client()
            if not client: st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets."); return
            ids=[l.strip() for l in ids_input.strip().split("\n") if l.strip()][:20]
            prompt=f"""You are a world-leading microbiome bioinformatician solving a critical annotation problem.

PROBLEM: Standard databases annotate microbial genes as "biosynthesis", "metabolism", "protein aggregation" -- these tell researchers NOTHING about what the microbe actually does in the host.

YOUR TASK: For each ID/term below, provide specific, actionable biological annotation:

{chr(10).join(f"- {i}" for i in ids)}

Research context: {ctx}
Lab focus: {lab.get('research_focus','')}

For each, provide:
1. TRUE biological function (NOT vague terms -- specific metabolite, pathway, or mechanism)
2. Specific metabolite produced or consumed
3. Host receptor or pathway interaction
4. Key organisms carrying this function
5. Disease/health relevance with direction (increased = bad/good in which context?)
6. Evidence quality (high/medium/low)
7. Research gap

Respond in this JSON format:
{{"annotations":[{{"id":"gene_id","true_function":"specific not vague","metabolite":"e.g. butyrate not just fatty acid","host_interaction":"e.g. GPR41 on colonocytes","key_organisms":["Faecalibacterium prausnitzii"],"disease_relevance":"decreased in IBD and inversely correlates with CRP","evidence_quality":"high","research_gap":"role in arrhythmia via GPCR rattling unstudied"}}]}}"""
            with st.spinner(f"Claude reannotating {len(ids)} functions..."):
                try:
                    resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=2500,messages=[{"role":"user","content":prompt}])
                    text="".join(b.text for b in resp.content if hasattr(b,"text"))
                    m=re.search(r'\{.*\}',text,re.DOTALL)
                    result=json.loads(m.group()) if m else {"annotations":[],"raw":text}
                except Exception as e:
                    result={"error":str(e),"annotations":[]}
            if result.get("error"): st.error(result["error"])
            elif result.get("annotations"):
                for ann in result["annotations"]:
                    conf_c={"high":"#00c896","medium":"#ffd60a","low":"#ff8c42"}.get(ann.get("evidence_quality","low"),"#5a8090")
                    with st.expander(f"{ann.get('id','')} -- {ann.get('true_function','')[:55]}...",expanded=True):
                        st.markdown(f"<div style='background:#020d10;border-left:3px solid {conf_c};padding:.68rem .95rem;border-radius:0 9px 9px 0'>",unsafe_allow_html=True)
                        for field,label,clr in [("true_function","True function","#00c896"),("metabolite","Metabolite","#4a90d9"),("host_interaction","Host interaction","#a855f7"),("disease_relevance","Disease relevance","#ff8c42"),("research_gap","Research gap","#ffd60a")]:
                            val=ann.get(field,"")
                            if val: st.markdown(f"<div style='margin-bottom:.22rem'><span style='color:{clr};font-weight:600;font-size:.74rem'>{label}:</span> <span style='color:#8ab0c0;font-size:.78rem'>{val}</span></div>",unsafe_allow_html=True)
                        orgs=ann.get("key_organisms",[])
                        if orgs: st.markdown(f"<div style='color:#3a6080;font-size:.72rem'>Organisms: {', '.join(orgs[:4])}</div>",unsafe_allow_html=True)
                        st.markdown(f"<div style='color:{conf_c};font-size:.69rem;margin-top:2px'>Evidence: {ann.get('evidence_quality','?')}</div>",unsafe_allow_html=True)
                        st.markdown("</div>",unsafe_allow_html=True)
            elif result.get("raw"): st.markdown(result["raw"])
    with tabs[1]:
        sh("","Microbe Biological Profile",color)
        taxon=st.text_input("Microbe name",placeholder="Akkermansia muciniphila, Bacteroides fragilis, Faecalibacterium prausnitzii",key="taxon_inp")
        tax_ctx=st.text_input("Host/disease context",placeholder="Gut microbiome in colorectal cancer patients",key="tax_ctx")
        if st.button("Generate Profile",key="taxon_btn",type="primary"):
            if not taxon.strip(): st.warning("Enter a microbe name."); return
            client=_ai_client()
            if not client: st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets."); return
            prompt=f"""Comprehensive biological profile of: {taxon}
Context: {tax_ctx}
Lab focus: {(st.session_state.lab or {}).get('research_focus','')}

Respond as JSON:
{{"organism":"{taxon}","classification":"phylum > class > order > family > genus","gram_status":"pos/neg/neither","metabolism":"aerobic/anaerobic/facultative","key_functions":["SPECIFIC function 1 -- NOT vague biosynthesis","specific function 2"],"metabolites_produced":["butyrate (from fibre fermentation)","not just 'fatty acids'"],"metabolites_consumed":["specific substrates"],"host_receptor_interactions":["GPR41 on colonocytes","TLR4 on macrophages"],"immune_modulation":"specific effect","gut_niche":"location and conditions","disease_associations":[{{"condition":"IBD","direction":"decreased","evidence":"strong"}}],"health_associations":["specific benefit with mechanism"],"therapeutic_potential":"probiotic/drug target/biomarker/none","annotation_confidence":"high/medium/low","key_papers":["Author Year -- finding"]}}"""
            with st.spinner(f"Profiling {taxon}..."):
                try:
                    resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=1800,messages=[{"role":"user","content":prompt}])
                    text="".join(b.text for b in resp.content if hasattr(b,"text"))
                    m=re.search(r'\{.*\}',text,re.DOTALL)
                    profile=json.loads(m.group()) if m else {}
                except Exception as e: profile={"error":str(e)}
            if profile.get("error"): st.error(profile["error"])
            else:
                c1,c2=st.columns(2)
                with c1:
                    for f,l,clr in [("classification","Classification","#00c896"),("gram_status","Gram status","#4a90d9"),("metabolism","Metabolism","#a855f7"),("gut_niche","Gut niche","#ffd60a"),("immune_modulation","Immune modulation","#ff8c42")]:
                        val=profile.get(f,"")
                        if val: st.markdown(f"<div style='padding:3px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:{clr};font-weight:600'>{l}:</span> <span style='color:#d0e8ff'>{val}</span></div>",unsafe_allow_html=True)
                    sh("","Key functions",color)
                    for f in profile.get("key_functions",[]): st.markdown(f"<div style='color:#6a9ab0;font-size:.76rem;padding:2px 0'>-- {f}</div>",unsafe_allow_html=True)
                with c2:
                    if profile.get("metabolites_produced"):
                        sh("","Metabolites produced",color)
                        for m2 in profile["metabolites_produced"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.76rem;padding:2px 0'>* {m2}</div>",unsafe_allow_html=True)
                    if profile.get("disease_associations"):
                        sh("","Disease associations",color)
                        for da in profile["disease_associations"]:
                            dir_c="#ff2d55" if da.get("direction")=="increased" else "#4a90d9"
                            ev_c={"strong":"#00c896","moderate":"#ffd60a","weak":"#ff8c42"}.get(da.get("evidence","weak"),"#5a8090")
                            st.markdown(f"<div style='font-size:.77rem;padding:3px 0;border-bottom:1px solid #0d2545'><span style='color:#d0e8ff'>{da.get('condition','')}</span> <span style='color:{dir_c}'>{da.get('direction','')}</span> <span style='color:{ev_c};font-size:.7rem'>({da.get('evidence','')})</span></div>",unsafe_allow_html=True)
    with tabs[2]:
        sh("","Upload and Reannotate Metagenome Annotation File",color)
        info_box("Upload your functional annotation output from DIAMOND, HUMAnN3, PROKKA, eggNOG-mapper, or any tool producing COG/KEGG/GO/InterPro annotations. Claude will explain what your community is ACTUALLY doing.",color)
        uploaded_micro=st.file_uploader("Upload annotation file (CSV, TSV, TXT)",type=["csv","tsv","txt"],key="micro_file")
        paste_ids=st.text_area("Or paste pathway/function list",placeholder="COG0001\nK00001\nbiosynthesis\nphosphate transport",height=80,key="micro_paste")
        sample_ctx=st.text_input("Sample context",placeholder="Gut microbiome, IBD patient, post-FMT day 7",key="micro_sctx")
        if st.button("Annotate Community",key="annotate_file",type="primary"):
            text_to_parse=paste_ids
            if uploaded_micro:
                try:
                    df_micro=pd.read_csv(uploaded_micro) if uploaded_micro.name.endswith((".csv",".tsv")) else pd.read_csv(uploaded_micro,sep="\t",header=None)
                    text_to_parse="\n".join(df_micro.iloc[:,0].astype(str).tolist()[:50])
                except: text_to_parse=uploaded_micro.read().decode("utf-8","ignore")[:3000]
            if not text_to_parse.strip(): st.warning("Upload a file or paste annotations."); return
            ids2=[l.strip() for l in text_to_parse.split("\n") if l.strip()][:20]
            client=_ai_client()
            if not client: st.warning("Add ANTHROPIC_API_KEY to Streamlit Secrets."); return
            prompt2=f"""Metagenome functional annotation reannotation.

Community functions detected:
{chr(10).join(f"- {i}" for i in ids2)}

Sample context: {sample_ctx}
Lab context: {lab.get('research_focus','')}

Provide community-level interpretation as JSON:
{{"pathway_summary":"what this community is collectively doing","dominant_processes":["SPECIFIC process 1","SPECIFIC process 2"],"key_metabolites_predicted":[{{"metabolite":"butyrate","source":"fibre fermentation by Roseburia","host_effect":"colonocyte energy, HDAC inhibition, anti-inflammatory"}}],"health_implications":"specific disease relevance","missing_functions":"what this community CANNOT do","research_priorities":["what to measure next"]}}"""
            with st.spinner("Interpreting community function..."):
                try:
                    resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=1800,messages=[{"role":"user","content":prompt2}])
                    text2="".join(b.text for b in resp.content if hasattr(b,"text"))
                    m2=re.search(r'\{.*\}',text2,re.DOTALL)
                    res2=json.loads(m2.group()) if m2 else {"pathway_summary":text2}
                except Exception as e: res2={"error":str(e)}
            if res2.get("error"): st.error(res2["error"])
            else:
                if res2.get("pathway_summary"): info_box(res2["pathway_summary"],color)
                if res2.get("dominant_processes"):
                    sh("","Dominant community processes",color)
                    for proc in res2["dominant_processes"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.78rem;padding:2px 0'>-- {proc}</div>",unsafe_allow_html=True)
                if res2.get("key_metabolites_predicted"):
                    sh("","Predicted metabolites reaching host",color)
                    for met in res2["key_metabolites_predicted"][:6]:
                        if isinstance(met,dict): st.markdown(f"<div style='padding:4px 0;border-bottom:1px solid #0d2545;font-size:.78rem'><span style='color:#00c896;font-weight:500'>{met.get('metabolite','')}</span> <span style='color:#3a6060;font-size:.74rem'>from {met.get('source','')} -- {met.get('host_effect','')}</span></div>",unsafe_allow_html=True)
                if res2.get("research_priorities"):
                    sh("","Research priorities",color)
                    for rp in res2["research_priorities"]: st.markdown(f"<div style='color:#6a9ab0;font-size:.76rem;padding:2px 0'>-- {rp}</div>",unsafe_allow_html=True)
    with tabs[3]:
        sh("","Microbiome Literature -- PubMed 2022-2025",color)
        micro_qs=["gut microbiome disease mechanism metabolite 2023 2024[pdat]","TMAO cardiovascular arrhythmia gut bacteria 2023 2024[pdat]","fecal microbiota transplant clinical trial 2023 2024[pdat]","gut-brain axis serotonin 2023 2024[pdat]","microbiome AI machine learning functional annotation 2023 2024[pdat]"]
        sel_q=st.selectbox("Query",micro_qs,key="micro_lit_q")
        if st.button("Fetch papers",key="micro_fetch",type="primary"):
            with st.spinner("Fetching..."): papers=api_pubmed(sel_q,10)
            for p in papers:
                with st.expander(f"{tier_badge(p['tier'])} {p['title'][:70]}...",expanded=False):
                    st.markdown(f"<div style='font-size:.75rem;color:#5a8090'>{p['authors']} * {p['journal']} * {p['year']}</div>",unsafe_allow_html=True)
                    st.markdown(f"<a href='{p['url']}' target='_blank' style='font-size:.69rem'>PubMed {p['pmid']} &#8599;</a>",unsafe_allow_html=True)
    with tabs[4]:
        sh("","Key Facts -- Evidence-Based",color)
        for fact in DOMAINS["microbiome"]["domain_facts"]: st.markdown(f"<div style='display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #0d2545'><span style='color:{color};flex-shrink:0'>--</span><span style='color:#8ab0c0;font-size:.79rem;line-height:1.6'>{fact}</span></div>",unsafe_allow_html=True)

# ── STANDARD DOMAIN ────────────────────────────────────────────────────────────
def render_domain(domain_key):
    D=DOMAINS[domain_key]; color=D["color"]
    gene_input,do_search=render_sidebar(domain_key)
    run_gene=st.session_state.pop("_run_gene",None)
    show_lab=st.session_state.pop("_show_lab_papers",False)
    if do_search and gene_input.strip(): run_gene=gene_input.strip()
    lab=st.session_state.lab or {}
    st.markdown(f"<div style='padding:1rem 1.4rem .45rem;border-bottom:1px solid #0d2545;display:flex;align-items:center;gap:10px'><span style='font-size:1.65rem'>&#128300;</span><div><div style='color:{color};font-weight:700;font-size:1.05rem'>{D['label']}</div><div style='color:#2a4050;font-size:.74rem'>{D['tagline']}</div></div></div>",unsafe_allow_html=True)
    if run_gene: render_gene_analysis(run_gene,domain_key); st.markdown("<hr style='border-color:#0d2545;margin:.5rem 0'>",unsafe_allow_html=True)
    if show_lab and lab.get("pi_pubmed"):
        sh("","Your Lab Papers",color)
        with st.spinner("Fetching..."): lp=api_pubmed(lab["pi_pubmed"]+" 2020:2025[pdat]",6)
        for p in lp:
            _u=p.get('url',''); _pm=p.get('pmid',''); _ti=p.get('title','')[:80]; _au=p.get('authors',''); _jn=p.get('journal',''); _yr=p.get('year','')
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:8px;padding:.55rem .82rem;margin-bottom:.2rem'><div style='color:#d0e8ff;font-size:.79rem;font-weight:500'>{_ti}...</div><div style='color:#3a6080;font-size:.71rem'>{_au} * {_jn} * {_yr} * <a href='{_u}' target='_blank'>PMID {_pm}</a></div></div>",unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#0d2545;margin:.5rem 0'>",unsafe_allow_html=True)
    tab_over,tab_db,tab_lit,tab_facts=st.tabs(["Overview","Databases","Live Literature","Key Facts & Study Errors"])
    with tab_over:
        st.markdown("<div style='padding:.7rem 1.4rem'>",unsafe_allow_html=True)
        sh("","Key Research Targets",color)
        chips="".join(f"<span style='display:inline-block;background:#040c14;border:1px solid {color}44;border-radius:7px;padding:.18rem .58rem;margin:2px;font-size:.73rem;color:{color}'>{g}</span>" for g in D["key_genes"])
        st.markdown(f"<div style='margin-bottom:.7rem'>{chips}</div>",unsafe_allow_html=True)
        if D.get("gpcr_protocol"):
            st.markdown("---")
            sh("","GPCR Study Protocol -- 7 Steps","#00e5ff")
            st.markdown("<div style='color:#3a6080;font-size:.76rem;margin-bottom:.4rem'>Step 3 (Filamin Ser2152-P) is the IP-protected primary readout. Step 4 (beta-arrestin BRET) is secondary only.</div>",unsafe_allow_html=True)
            for step,title,body,clr in GPCR_PROTOCOL:
                primary="PRIMARY" in step
                with st.expander(f"{step} -- {title}",expanded=primary):
                    st.markdown(f"<div style='background:#020810;border-left:3px solid {clr};padding:.62rem .92rem;border-radius:0 8px 8px 0;color:#7ab0c0;font-size:.77rem;line-height:1.62'>{body}</div>",unsafe_allow_html=True)
            st.markdown(" ".join([src_link("GPCRdb","https://gpcrdb.org"),src_link("PhosphoSite FLNA","https://www.phosphosite.org/proteinAction.action?id=2546"),src_link("Nakamura 2015","https://doi.org/10.1074/jbc.M115.671826")]),unsafe_allow_html=True)
        if D.get("arrb_note"):
            st.markdown("---")
            st.markdown(f"<div style='background:#0a0205;border:1px solid #ff2d5533;border-radius:10px;padding:.72rem .95rem'><div style='color:#ff2d55;font-weight:600;font-size:.8rem;margin-bottom:.2rem'>ARRB1/ARRB2 -- Deprioritise</div><div style='color:#5a3040;font-size:.77rem;line-height:1.6'>Zero confirmed Mendelian disease variants. ARRB1/ARRB2 double KO mice viable. Phosphorylation codes = kinase noise. Use Filamin A Ser2152-P instead. Avoidable spend: $4,050,000.</div></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with tab_db:
        st.markdown("<div style='padding:.7rem 1.4rem'>",unsafe_allow_html=True)
        sh("","Databases",color)
        for dname,durl,ddesc in D["databases"]:
            st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:9px;padding:.58rem .85rem;margin-bottom:.22rem;display:flex;justify-content:space-between;align-items:center'><div><a href='{durl}' target='_blank' style='color:#d0e8ff;font-weight:500;font-size:.82rem'>{dname}</a><div style='color:#2a4050;font-size:.71rem'>{ddesc}</div></div></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    with tab_lit:
        st.markdown("<div style='padding:.7rem 1.4rem'>",unsafe_allow_html=True)
        sh("","Live Literature -- PubMed 2022-2025",color)
        qs=D.get("quick_searches",[]); sel_q=st.selectbox("Query",qs,key=f"lit_q_{domain_key}") if qs else None
        if sel_q and st.button("Fetch",key=f"fetch_{domain_key}",type="primary"):
            with st.spinner("Fetching..."): papers=api_pubmed(sel_q,10)
            for p in papers:
                wk=detect_weaknesses(p["title"])
                with st.expander(f"{tier_badge(p['tier'])} {p['title'][:72]}{'...' if len(p['title'])>72 else ''}",expanded=False):
                    st.markdown(f"<div style='font-size:.75rem;color:#5a8090'>{p['authors']} * {p['journal']} * {p['year']}</div>",unsafe_allow_html=True)
                    pm=p.get("pmid",""); doi=p.get("doi",""); url=p.get("url","")
                    if doi: st.markdown(f"<a href='https://doi.org/{doi}' target='_blank' style='font-size:.69rem'>DOI &#8599;</a> <a href='{url}' target='_blank' style='font-size:.69rem'>PubMed {pm} &#8599;</a>",unsafe_allow_html=True)
                    else: st.markdown(f"<a href='{url}' target='_blank' style='font-size:.69rem'>PubMed {pm} &#8599;</a>",unsafe_allow_html=True)
                    for wt,wb in wk: warn_box(wt,wb)
        elif sel_q: st.info("Select a query and click Fetch.")
        st.markdown("</div>",unsafe_allow_html=True)
    with tab_facts:
        st.markdown("<div style='padding:.7rem 1.4rem'>",unsafe_allow_html=True)
        sh("","Evidence-Based Key Facts",color)
        st.markdown("<div style='color:#3a6080;font-size:.76rem;margin-bottom:.4rem'>Genetic evidence takes precedence over in vitro or animal data. Where evidence conflicts with common assumptions, the genetic evidence wins.</div>",unsafe_allow_html=True)
        for fact in D.get("domain_facts",[]): st.markdown(f"<div style='display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #0d2545'><span style='color:{color};flex-shrink:0'>--</span><span style='color:#8ab0c0;font-size:.78rem;line-height:1.6'>{fact}</span></div>",unsafe_allow_html=True)
        sh("","Evidence Tier Reference",color)
        for tier,meta in TIER_MAP.items(): st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid #0d2545'>{badge(tier,meta['c'])}<span style='color:#3a6080;font-size:.75rem'>Weight {meta['w']}/10</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
    st.markdown(f"<div style='color:#1e3a5a;font-size:.68rem;text-align:center;padding:1.2rem 0'>Protellect * {lab.get('lab_name','Biology Intelligence')} * UniProt * ClinVar * gnomAD * STRING * OpenTargets * AlphaFold * AlphaMissense * PubMed * ClinicalTrials.gov * {datetime.now().year}</div>",unsafe_allow_html=True)

# ── SPLASH ────────────────────────────────────────────────────────────────────
def render_splash():
    lab=st.session_state.lab or {}
    st.markdown("<div style='text-align:center;padding:2.8rem 1rem 1.5rem'><div style='font-size:2.8rem'>&#128300;</div><div style='font-size:2.5rem;font-weight:700;color:#00e5ff;letter-spacing:-.03em'>Protellect</div><div style='font-size:.77rem;color:#3a6080;letter-spacing:.1em;text-transform:uppercase;margin:.2rem 0'>Biology Intelligence Platform</div><div style='width:42px;height:2px;background:#00e5ff;margin:.7rem auto'></div></div>",unsafe_allow_html=True)
    if lab.get("lab_name"): st.markdown(f"<div style='text-align:center;color:#3a6080;font-size:.8rem;margin-bottom:1.2rem'>Welcome back, <b style='color:#d0e8ff'>{lab['lab_name']}</b></div>",unsafe_allow_html=True)
    cols=st.columns(4,gap="medium")
    for i,(col,(key,D)) in enumerate(zip(cols,DOMAINS.items())):
        with col:
            lab_dom=lab.get("domain_pref","")
            is_rec=D["label"].lower() in lab_dom.lower() if lab_dom and lab_dom!="All equally" else False
            border=f"border:2px solid {D['color']}88" if is_rec else "border:1px solid #0d2545"
            _bc = f"border:2px solid {D["color"]}88" if is_rec else "border:1px solid #0d2545"
            _rec_badge = f"<div style='background:{D["color"]}22;color:{D["color"]};font-size:.62rem;padding:1px 6px;border-radius:5px;margin-bottom:.25rem'>Recommended</div>" if is_rec else ""
            _dc = D["color"]; _dl = D["label"]; _dt = D["tagline"][:55]
            st.markdown(f"<div style='background:#040c14;{_bc};border-radius:15px;padding:1.4rem .9rem;text-align:center;margin-bottom:.4rem'>{_rec_badge}<div style='font-size:1.9rem;margin-bottom:.35rem'>&#128300;</div><div style='color:{_dc};font-weight:700;font-size:.86rem;margin-bottom:.2rem'>{_dl}</div><div style='color:#2a4050;font-size:.68rem;line-height:1.5'>{_dt}...</div></div>",unsafe_allow_html=True)
            if st.button(D["label"][:12],key=f"open_{key}",use_container_width=True,type="primary"):
                st.session_state.domain=key; st.rerun()
    if lab.get("pi_pubmed"):
        st.markdown("---"); sh("","Your Lab's Recent Papers","#ffd60a")
        if st.button("Load lab papers",key="splash_lab_papers"):
            with st.spinner("Fetching..."): lp=api_pubmed(lab["pi_pubmed"]+" 2020:2025[pdat]",6)
            for p in lp:
                _u=p.get('url',''); _pm=p.get('pmid',''); _ti=p.get('title','')[:80]; _au=p.get('authors',''); _jn=p.get('journal',''); _yr=p.get('year','')
                st.markdown(f"<div style='background:#040c14;border:1px solid #0d2545;border-radius:8px;padding:.55rem .82rem;margin-bottom:.2rem'><div style='color:#d0e8ff;font-size:.79rem;font-weight:500'>{_ti}...</div><div style='color:#3a6080;font-size:.71rem'>{_au} * {_jn} * {_yr} * <a href='{_u}' target='_blank'>PMID {_pm}</a></div></div>",unsafe_allow_html=True)

# ── ROUTER ────────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page(); st.stop()
u=current_user()
if not st.session_state.onboarded and not u.get("onboarded"):
    render_onboarding(); st.stop()
if not st.session_state.lab and u.get("lab"):
    st.session_state.lab=u.get("lab",{})
d=st.session_state.domain
if d is None: render_splash()
elif d=="microbiome": render_microbiome_domain()
else: render_domain(d)
