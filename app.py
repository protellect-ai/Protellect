# ===============================================================================
#  PROTELLECT v32 — Protein Intelligence Platform
#  Single-file Streamlit application.
#
#  ARCHITECTURE
#  ------------
#    • Genetics-first triage engine (ClinVar + gnomAD + AlphaMissense)
#    • Domain-specialized modules: Oncology · Neuroscience · Microbiome
#      · Cardiology · Rare Disease
#    • Two novel IP engines:
#         (1) Filamin H8 / RxxS phosphorylation-readout predictor
#         (2) Cross-disease variant-database scanner (digenic detection)
#    • Chemistry renderer: backbone, R-groups, phosphorylation animations
#    • 3D structure renderer (3Dmol.js)
#    • Microbiome pathway re-annotator (LLM-augmented when ANTHROPIC_API_KEY
#      is provided in st.secrets; falls back to a curated KEGG/Pfam table)
#    • Pharmaceuticals / druggability map (DGIdb + OpenTargets + clinical trials)
#
#  All input is validated as human (taxon ID 9606) at the UniProt level except
#  on the Microbiome tab, which intentionally accepts non-human organisms.
# ===============================================================================

import io
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

# --- Page config --------------------------------------------------------------
st.set_page_config(
    page_title="Protellect v32 · Protein Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===============================================================================
#  GLOBAL THEME — aggressive dark, monospace, terminal-grade
# ===============================================================================
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Space+Grotesk:wght@300;500;700&display=swap');

:root{
  --bg-0:#02060d;
  --bg-1:#06101e;
  --bg-2:#0a1828;
  --bg-3:#0e2238;
  --line:#13314f;
  --line-2:#1a4470;
  --ink-0:#dde9f5;
  --ink-1:#9fb8d0;
  --ink-2:#5a7794;
  --ink-3:#324b66;
  --acc-cyan:#00f5d4;
  --acc-cyan-d:#009d8a;
  --acc-amber:#ffb02e;
  --acc-pink:#ff3d7f;
  --acc-violet:#9d4edd;
  --acc-lime:#9bff4a;
  --acc-red:#ff2d55;
  --acc-blue:#3a7bff;
}

html, body, [data-testid="stAppViewContainer"]{
  background:radial-gradient(ellipse at top, #04101e 0%, #02060d 60%) !important;
  color:var(--ink-0);
  font-family:'JetBrains Mono','Space Grotesk',monospace !important;
}

/* hide hamburger / footer */
#MainMenu, footer, header [data-testid="stToolbar"]{visibility:hidden;}

/* sidebar */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#020810 0%,#05101e 100%);
  border-right:1px solid var(--line);
}
[data-testid="stSidebar"] *{font-family:'JetBrains Mono',monospace;}

/* headers */
h1,h2,h3,h4{
  font-family:'Space Grotesk',sans-serif !important;
  letter-spacing:-0.02em;
  color:var(--ink-0) !important;
}
h1{font-weight:700;font-size:2.1rem;}
h2{font-weight:500;font-size:1.4rem;}
h3{font-weight:500;font-size:1.1rem;color:var(--acc-cyan) !important;}

/* tabs */
[data-testid="stTabs"] button[role="tab"]{
  background:transparent;
  color:var(--ink-2);
  border:none;
  border-bottom:1px solid var(--line);
  border-radius:0;
  font-family:'JetBrains Mono',monospace;
  font-size:.78rem;
  letter-spacing:.05em;
  text-transform:uppercase;
  padding:.7rem 1.1rem;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
  color:var(--acc-cyan);
  border-bottom:1px solid var(--acc-cyan);
  background:linear-gradient(180deg,transparent 0%, #002b25 100%);
}

/* buttons */
.stButton button, .stDownloadButton button{
  background:#06101e !important;
  color:var(--acc-cyan) !important;
  border:1px solid var(--line-2) !important;
  border-radius:4px !important;
  font-family:'JetBrains Mono',monospace !important;
  font-size:.78rem !important;
  letter-spacing:.04em;
  text-transform:uppercase;
  transition:all .15s ease;
}
.stButton button:hover, .stDownloadButton button:hover{
  background:var(--acc-cyan) !important;
  color:#021 !important;
  border-color:var(--acc-cyan) !important;
  transform:translateY(-1px);
  box-shadow:0 4px 14px rgba(0,245,212,.25);
}

/* inputs */
.stTextInput input, .stSelectbox div[data-baseweb="select"]>div, .stTextArea textarea{
  background:#040a14 !important;
  color:var(--ink-0) !important;
  border:1px solid var(--line) !important;
  border-radius:3px !important;
  font-family:'JetBrains Mono',monospace !important;
}

/* metric cards (custom) */
.kpi{
  background:linear-gradient(180deg,#06101e 0%, #040a14 100%);
  border:1px solid var(--line);
  border-left:2px solid var(--acc-cyan);
  border-radius:3px;
  padding:.9rem 1rem;
  position:relative;
  overflow:hidden;
}
.kpi::before{content:"";position:absolute;top:0;right:0;width:60%;height:1px;
  background:linear-gradient(90deg,transparent,var(--acc-cyan));opacity:.4;}
.kpi .label{font-size:.65rem;color:var(--ink-2);letter-spacing:.08em;text-transform:uppercase;margin-bottom:.3rem;}
.kpi .val{font-size:1.7rem;color:var(--ink-0);font-weight:700;line-height:1;font-family:'Space Grotesk',sans-serif;}
.kpi .sub{font-size:.7rem;color:var(--ink-2);margin-top:.3rem;}
.kpi.amber{border-left-color:var(--acc-amber);} .kpi.amber::before{background:linear-gradient(90deg,transparent,var(--acc-amber));}
.kpi.pink{border-left-color:var(--acc-pink);} .kpi.pink::before{background:linear-gradient(90deg,transparent,var(--acc-pink));}
.kpi.violet{border-left-color:var(--acc-violet);} .kpi.violet::before{background:linear-gradient(90deg,transparent,var(--acc-violet));}
.kpi.lime{border-left-color:var(--acc-lime);} .kpi.lime::before{background:linear-gradient(90deg,transparent,var(--acc-lime));}
.kpi.red{border-left-color:var(--acc-red);} .kpi.red::before{background:linear-gradient(90deg,transparent,var(--acc-red));}

/* verdict banner */
.verdict{
  padding:1.6rem 1.8rem;
  border-radius:4px;
  border:1px solid;
  position:relative;
  overflow:hidden;
  margin:1rem 0;
}
.verdict::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(45deg,transparent 0 12px, rgba(255,255,255,.015) 12px 13px);
  pointer-events:none;}
.verdict h2{margin:0;font-family:'Space Grotesk',sans-serif;font-weight:700;letter-spacing:-.01em;}
.verdict .vsub{font-size:.85rem;color:var(--ink-1);margin-top:.4rem;line-height:1.5;}
.v-prioritise{background:linear-gradient(135deg,#1e0a0f 0%, #0a0408 100%);border-color:var(--acc-pink);}
.v-prioritise h2{color:var(--acc-pink);}
.v-proceed{background:linear-gradient(135deg,#1a1404 0%, #0a0802 100%);border-color:var(--acc-amber);}
.v-proceed h2{color:var(--acc-amber);}
.v-selective{background:linear-gradient(135deg,#001c19 0%, #000a08 100%);border-color:var(--acc-cyan);}
.v-selective h2{color:var(--acc-cyan);}
.v-caution{background:linear-gradient(135deg,#1a0e1c 0%, #08040a 100%);border-color:var(--acc-violet);}
.v-caution h2{color:var(--acc-violet);}
.v-deprioritise{background:linear-gradient(135deg,#0a1018 0%, #02060d 100%);border-color:var(--line-2);}
.v-deprioritise h2{color:var(--ink-2);}

/* badges */
.badge{display:inline-block;padding:.15rem .55rem;border-radius:2px;font-size:.66rem;
  font-family:'JetBrains Mono',monospace;letter-spacing:.06em;text-transform:uppercase;
  border:1px solid;font-weight:500;}
.b-crit{background:rgba(255,45,85,.08);color:var(--acc-pink);border-color:rgba(255,45,85,.4);}
.b-high{background:rgba(255,176,46,.08);color:var(--acc-amber);border-color:rgba(255,176,46,.4);}
.b-med{background:rgba(255,213,40,.08);color:#ffd528;border-color:rgba(255,213,40,.3);}
.b-low{background:rgba(0,245,212,.06);color:var(--acc-cyan);border-color:rgba(0,245,212,.3);}
.b-null{background:rgba(160,160,160,.05);color:var(--ink-2);border-color:var(--line);}

/* section heads */
.sec-head{
  display:flex;align-items:center;gap:.7rem;
  margin:1.5rem 0 .9rem 0;padding-bottom:.5rem;
  border-bottom:1px solid var(--line);
}
.sec-head .glyph{
  width:22px;height:22px;border-radius:2px;
  background:linear-gradient(135deg,var(--acc-cyan),var(--acc-blue));
  display:flex;align-items:center;justify-content:center;color:#000;font-weight:700;
  font-size:.75rem;
}
.sec-head h3{margin:0;font-size:.95rem;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-0) !important;}
.sec-head .tag{margin-left:auto;font-size:.65rem;color:var(--ink-2);letter-spacing:.05em;}

/* tables */
table{font-family:'JetBrains Mono',monospace !important;font-size:.82rem;border-collapse:collapse;width:100%;}
thead tr{background:#040a14 !important;color:var(--acc-cyan) !important;text-transform:uppercase;font-size:.7rem;letter-spacing:.05em;}
tbody tr{border-bottom:1px solid var(--line);}
tbody tr:hover{background:#06101e;}
td,th{padding:.4rem .7rem;text-align:left;color:var(--ink-1);}

/* domain selector strip */
.domain-strip{
  display:flex;gap:.3rem;margin:.5rem 0 1rem 0;flex-wrap:wrap;
}
.dom-chip{
  padding:.35rem .8rem;border:1px solid var(--line);border-radius:2px;
  background:#040a14;color:var(--ink-2);font-size:.72rem;letter-spacing:.05em;
  text-transform:uppercase;cursor:pointer;transition:all .15s;
}
.dom-chip.active{background:var(--acc-cyan);color:#000;border-color:var(--acc-cyan);font-weight:600;}

/* monospace data display */
.mono{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--ink-1);}
.mono-acc{color:var(--acc-cyan);}
.mono-warn{color:var(--acc-amber);}
.mono-err{color:var(--acc-pink);}

/* loading/empty states */
.empty-state{
  padding:2.5rem;text-align:center;color:var(--ink-2);
  border:1px dashed var(--line);border-radius:3px;
  background:linear-gradient(180deg,#040a14,#02060d);
}

/* source link */
.src{font-size:.7rem;color:var(--ink-2);text-decoration:none;
  border-bottom:1px dotted var(--line-2);margin-right:.6rem;}
.src:hover{color:var(--acc-cyan);}

/* scrollbar */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#02060d;}
::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--acc-cyan-d);}

/* expander */
[data-testid="stExpander"]{
  background:#040a14 !important;
  border:1px solid var(--line) !important;
  border-radius:3px !important;
}
[data-testid="stExpander"] summary{color:var(--ink-1) !important;font-family:'JetBrains Mono',monospace !important;font-size:.82rem !important;}
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ===============================================================================
#  CONSTANTS
# ===============================================================================
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

SIG_SCORE = {
    "pathogenic": 5, "likely pathogenic": 4,
    "pathogenic/likely pathogenic": 5,
    "drug response": 3, "risk factor": 3,
    "uncertain significance": 2, "conflicting interpretations of pathogenicity": 2,
    "likely benign": 1, "benign": 0, "benign/likely benign": 0,
    "not provided": 1, "other": 1, "association": 2,
}

# Single-letter amino-acid utilities
AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
       "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
       "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
AA1 = {v:k for k,v in AA3.items()}
AA_FULL = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate",
           "C":"Cysteine","Q":"Glutamine","E":"Glutamate","G":"Glycine",
           "H":"Histidine","I":"Isoleucine","L":"Leucine","K":"Lysine",
           "M":"Methionine","F":"Phenylalanine","P":"Proline","S":"Serine",
           "T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
HYDROPATHY = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,
              "G":-0.4,"H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,
              "P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}

# Charge classes (for chemistry rendering)
AA_CHARGE = {"R":1,"K":1,"H":0.5,"D":-1,"E":-1}
AA_POLAR = set("STNQYC")
AA_HYDROPHOBIC = set("AVLIMFWP")
AA_AROMATIC = set("FWY")
AA_SMALL = set("AGSC")

# Phosphorylatable residues + kinase consensus motifs
PHOSPHO_RES = set("STY")
KINASE_MOTIFS = {
    # Pattern : (kinase family, description)
    r"R.R..[ST]":  ("PKA",   "cAMP-dependent protein kinase A — RRxS/T motif"),
    r"R..[ST]":    ("PKC",   "Protein kinase C — RxxS/T basic motif"),
    r"[ST].[ED]":  ("CK2",   "Casein kinase 2 — S/TxxD/E acidic motif"),
    r"[ST]P":      ("CDK/MAPK", "Proline-directed kinase — S/T-P motif"),
    r"R.R..S":     ("FILAMIN-PKA", "PKA on filamin H8 cluster (RxRxxS) — Protellect IP marker"),
    r"R{3,}.[ST]": ("PROTELLECT-RxxxS", "Multi-arginine cluster preceding S/T — high-density phosphorylation site"),
}

# Class A GPCR signature for H8 detection (last α-helix after TM7)
H8_AMPHIPATHIC_HINT = re.compile(r"[FYW][KR][KR].[KR]")  # FKKxR-style anchor

# Verdict bands
VERDICTS = {
    "prioritise":   ("PRIORITISE TARGET",   "v-prioritise",   "Strong genetic evidence. Full investment justified."),
    "proceed":      ("PROCEED",             "v-proceed",      "Solid disease relevance. Move to mechanism / drug."),
    "selective":    ("SELECTIVE",           "v-selective",    "Real signal but limited. Pick the right variant subset."),
    "caution":      ("APPROACH WITH CAUTION","v-caution",     "Mixed signal. Confirm with patient-cohort data first."),
    "deprioritise": ("DEPRIORITISE",        "v-deprioritise", "Insufficient human-genetic evidence. Redirect resources."),
}

# Domains
DOMAINS = ["Core Triage", "Oncology", "Neuroscience", "Cardiology",
           "Rare Disease", "Microbiome", "Pharmaceuticals", "Chemistry & PTM"]

# Disease/tissue keyword sets for domain classifiers
ONC_KEYWORDS = {"cancer","carcinoma","sarcoma","leukemia","leukaemia","lymphoma",
                "neoplasm","tumor","tumour","melanoma","glioma","glioblastoma",
                "myeloma","blastoma","adenoma","metastasis","metastatic"}
NEURO_KEYWORDS = {"epilepsy","seizure","alzheimer","parkinson","huntington","ataxia",
                  "schizophrenia","autism","retardation","encephalopathy","neuropathy",
                  "myopathy","ALS","amyotrophic","dystonia","tremor","cognitive",
                  "dementia","cortical","heterotopia","periventricular"}
CARDIO_KEYWORDS = {"cardiomyopathy","arrhythmia","arrhythmic","long QT","brugada",
                   "ventricular","atrial","conduction","heart","cardiac","aortic",
                   "aneurysm","valvulopathy","mitral","tachycardia","bradycardia"}
RARE_HINT_KEYWORDS = {"syndrome","dysplasia","congenital","mendelian","inherited",
                      "familial","autosomal","X-linked","de novo","monogenic"}


# ===============================================================================
#  SESSION INIT
# ===============================================================================
def _init_session():
    defaults = {
        "domain": "Core Triage",
        "current_gene": None,
        "current_data": None,
        "search_log": [],
        "sensitivity": 50,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init_session()


# ===============================================================================
#  TINY HELPERS
# ===============================================================================
def clean_sig(raw: str) -> str:
    """Normalise raw ClinVar clinical-significance strings."""
    if not raw: return "Not provided"
    s = str(raw).strip()
    if s.isdigit():
        # Some endpoints return numeric scores instead of words
        return {"5":"Pathogenic","4":"Likely pathogenic","3":"Risk factor",
                "2":"VUS","1":"Likely benign","0":"Benign"}.get(s,"Not provided")
    return s

def aa_extract(name: str) -> tuple[Optional[str],Optional[int],Optional[str]]:
    """Extract (wt, position, mut) from an HGVS-like protein name."""
    if not name: return (None,None,None)
    m = re.search(r"p\.\(?([A-Za-z]{3})(\d+)([A-Za-z]{3}|Ter|\*)?", name)
    if not m: return (None,None,None)
    wt3,pos,mut3 = m.group(1),m.group(2),m.group(3)
    wt = AA3.get(wt3.upper(),wt3[0].upper() if wt3 else None)
    mut = ("*" if mut3 in ("Ter","*") else AA3.get((mut3 or "").upper(),
            (mut3[0].upper() if mut3 else None)))
    try: pos = int(pos)
    except: pos = None
    return (wt,pos,mut)

def src(label: str, url: str) -> str:
    return f"<a class='src' href='{url}' target='_blank'>↗ {label}</a>"

def kpi(label: str, val: str|float|int, sub: str = "", style: str = "") -> str:
    cls = f"kpi {style}".strip()
    if isinstance(val,(int,float)) and not isinstance(val,bool):
        if isinstance(val,float):
            val_s = f"{val:,.2f}" if abs(val) < 1000 else f"{val:,.0f}"
        else:
            val_s = f"{val:,}"
    else:
        val_s = str(val)
    return (f"<div class='{cls}'><div class='label'>{label}</div>"
            f"<div class='val'>{val_s}</div>"
            f"{f'<div class=\"sub\">{sub}</div>' if sub else ''}</div>")

def sec(num: str, title: str, tag: str = "") -> None:
    st.markdown(
        f"<div class='sec-head'><div class='glyph'>{num}</div>"
        f"<h3>{title}</h3>"
        f"{f'<span class=\"tag\">{tag}</span>' if tag else ''}</div>",
        unsafe_allow_html=True,
    )

def badge(rank: str) -> str:
    css = {"CRITICAL":"b-crit","HIGH":"b-high","MEDIUM":"b-med",
           "LOW":"b-low","NEUTRAL":"b-null"}.get(rank,"b-null")
    return f"<span class='badge {css}'>{rank}</span>"


# ===============================================================================
#  DATA FETCHERS — UniProt, ClinVar, gnomAD, AlphaMissense, OpenTargets,
#                  STRING, DGIdb, PubMed, ClinicalTrials, NCBI Taxonomy
# ===============================================================================

# --- UniProt (HUMAN-ONLY, validated at taxon level) ----------------------------
NON_HUMAN_REJECT = {
    "ovalbumin":"chicken (Gallus gallus)",
    "gfp":"jellyfish (Aequorea victoria)",
    "luciferase":"firefly (Photinus pyralis)",
    "casein":"bovine (Bos taurus)",
    "gelatin":"hydrolysed bovine collagen — try COL1A1/COL3A1 for human",
}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(query: str, allow_nonhuman: bool=False) -> dict:
    """Resolve a query to a UniProt entry. Default: HUMAN-ONLY (taxon 9606).
    Set allow_nonhuman=True for the Microbiome module."""
    base = "https://rest.uniprot.org/uniprotkb"
    q = (query or "").strip()
    if not q:
        raise ValueError("Empty query.")
    if not allow_nonhuman:
        ql = q.lower()
        for term, species in NON_HUMAN_REJECT.items():
            if term in ql:
                raise ValueError(
                    f"'{query}' is a non-human protein ({species}). "
                    f"Core Triage analyses human proteins only — switch to the "
                    f"Microbiome tab for organisms outside Homo sapiens."
                )

    def _validate(entry):
        if allow_nonhuman: return entry
        org = entry.get("organism",{})
        if "Homo sapiens" in org.get("scientificName","") or org.get("taxonId")==9606:
            return entry
        sci = org.get("scientificName","?")
        raise ValueError(
            f"Resolved to a non-human protein ({sci}). Switch to the "
            f"Microbiome tab to analyse non-human organisms."
        )

    # direct UniProt accession
    if re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", q, re.I):
        r = requests.get(f"{base}/{q.upper()}",
                         headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        return _validate(r.json())

    qry_set = (
        [f"gene:{q} AND reviewed:true AND organism_id:9606",
         f"gene_exact:{q} AND organism_id:9606",
         f"protein_name:{q} AND reviewed:true AND organism_id:9606",
         f"({q}) AND reviewed:true AND organism_id:9606"]
        if not allow_nonhuman else
        [f"gene:{q} AND reviewed:true",
         f"({q}) AND reviewed:true",
         f"({q})"]
    )
    for qry in qry_set:
        try:
            r = requests.get(f"{base}/search",
                             params={"query": qry, "format":"json", "size":3},
                             headers={"Accept":"application/json"}, timeout=20)
            r.raise_for_status()
            results = r.json().get("results",[])
            for cand in results:
                if not allow_nonhuman:
                    org = cand.get("organism",{})
                    if "Homo sapiens" not in org.get("scientificName","") and org.get("taxonId")!=9606:
                        continue
                uid = cand["primaryAccession"]
                r2 = requests.get(f"{base}/{uid}",
                                  headers={"Accept":"application/json"}, timeout=20)
                r2.raise_for_status()
                return _validate(r2.json())
        except ValueError:
            raise
        except Exception:
            continue
    raise ValueError(
        f"No {'' if allow_nonhuman else 'human '}match for '{query}'. "
        f"Try a gene symbol (TP53, FLNC, BRCA1) or a UniProt accession (P04637)."
    )

# --- ClinVar variants ----------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene: str, max_v: int=200) -> dict:
    try:
        r = requests.get(ESEARCH, params={"db":"clinvar","term":f"{gene}[gene]",
                                          "retmax":max_v,"retmode":"json"}, timeout=20)
        r.raise_for_status()
        ids = r.json().get("esearchresult",{}).get("idlist",[])
    except Exception:
        return {"variants":[], "summary":{}}
    if not ids:
        return {"variants":[], "summary":{}}
    variants = []
    for i in range(0,len(ids),100):
        try:
            r2 = requests.get(ESUMMARY, params={"db":"clinvar",
                              "id":",".join(ids[i:i+100]),"retmode":"json"}, timeout=30)
            r2.raise_for_status()
            data = r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e = data.get(uid,{})
                gc = e.get("germline_classification",{}) or {}
                sig_raw = str(gc.get("description","Not provided") or "Not provided")
                sig = clean_sig(sig_raw)
                sc = SIG_SCORE.get(sig_raw.lower().strip(),
                     SIG_SCORE.get(sig.lower().strip(),0))
                traits = [t.get("trait_name","") for t in
                          e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                vset = e.get("variation_set",[{}])
                var_name = vset[0].get("variation_name","") if vset else ""
                # protein position
                prot_pos = ""
                pm = re.search(r"p\.([A-Za-z]{3})(\d+)", var_name)
                if pm:
                    prot_pos = pm.group(2)
                else:
                    cm = re.search(r"c\.(\d+)", var_name)
                    if cm: prot_pos = str(int(cm.group(1))//3 + 1)
                # origin parsing
                origin_raw = e.get("origin", e.get("germline_classifications",{}))
                origin_str = ""
                if isinstance(origin_raw,dict):
                    origin_str = origin_raw.get("origin",
                                 origin_raw.get("description",""))
                elif isinstance(origin_raw,str): origin_str = origin_raw
                elif isinstance(origin_raw,list): origin_str = " ".join(str(x) for x in origin_raw)
                germ_class = e.get("germline_classifications",{}) or {}
                som_class = e.get("somatic_classifications",{}) or {}
                has_som = bool(som_class and som_class.get("description","").strip())
                has_germ = bool(germ_class and germ_class.get("description","").strip())
                if not origin_str and has_germ: origin_str = "germline"
                if not origin_str and has_som: origin_str = "somatic"
                is_somatic = has_som or "somatic" in origin_str.lower()
                is_germline = (has_germ or any(x in origin_str.lower()
                               for x in ["germline","inherited","de novo","maternal","paternal","constitutional"])
                               or (not is_somatic and sc>=3))
                variants.append({
                    "uid":uid, "title":e.get("title",""),
                    "variant_name":var_name, "sig":sig, "score":sc,
                    "condition":"; ".join(t for t in traits if t.strip()) if traits else "",
                    "origin":origin_str, "review":gc.get("review_status",""),
                    "start":prot_pos, "somatic":is_somatic, "germline":is_germline,
                    "url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                })
        except Exception:
            pass
        time.sleep(0.1)
    variants.sort(key=lambda x:-x["score"])
    sigs = Counter(v["sig"] for v in variants)
    conds = Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c = c.strip()
            if c and c not in ("Not specified","not specified","not provided"):
                conds[c] += 1
    return {
        "variants":variants,
        "summary":{
            "total":len(variants),
            "by_sig":dict(sigs.most_common(10)),
            "top_conds":dict(conds.most_common(15)),
            "pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2),
            "germline":sum(1 for v in variants if v["germline"] and not v["somatic"]),
            "somatic":sum(1 for v in variants if v["somatic"]),
        }
    }

# --- ClinVar disease → genes ---------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_disease_genes(disease: str, max_genes: int=20) -> List[Dict]:
    try:
        r = requests.get(ESEARCH, params={"db":"clinvar",
                          "term":f'"{disease}"[disease/phenotype] AND "clinsig pathogenic"[Properties]',
                          "retmax":300, "retmode":"json"}, timeout=20)
        r.raise_for_status()
        ids = r.json().get("esearchresult",{}).get("idlist",[])
    except Exception:
        return []
    if not ids: return []
    counts = Counter()
    for i in range(0,len(ids),100):
        try:
            r2 = requests.get(ESUMMARY, params={"db":"clinvar",
                  "id":",".join(ids[i:i+100]),"retmode":"json"}, timeout=30)
            r2.raise_for_status()
            data = r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e = data.get(uid,{})
                genes = e.get("genes",[])
                for g in genes:
                    sym = g.get("symbol","")
                    if sym: counts[sym] += 1
        except Exception:
            pass
        time.sleep(0.1)
    return [{"gene":g,"count":c} for g,c in counts.most_common(max_genes)]

# --- AlphaFold PDB -------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_pdb(uniprot_id: str) -> str:
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb",
                         timeout=30)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

# --- AlphaMissense scores ------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_alphamissense(uniprot_id: str) -> dict:
    """Returns {(pos,alt): score} dict; empty if not available."""
    try:
        url = f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-aa-substitutions.csv"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        out = {}
        for line in r.text.splitlines()[1:]:
            parts = line.split(",")
            if len(parts) < 3: continue
            mut = parts[0].strip()  # e.g. A2G
            try:
                score = float(parts[1])
            except:
                continue
            m = re.match(r"^([A-Z])(\d+)([A-Z*])$", mut)
            if m:
                out[(int(m.group(2)), m.group(3))] = score
        return out
    except Exception:
        return {}

# --- OpenTargets (GraphQL) -----------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_opentargets(gene: str) -> dict:
    """Tractability + known drugs + diseases for the gene."""
    out = {"tractability":[], "drugs":[], "diseases":[]}
    try:
        # Step 1: gene symbol → Ensembl ID
        r0 = requests.get(f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene}",
                          headers={"Content-Type":"application/json"}, timeout=15)
        if r0.status_code != 200:
            return out
        ensembl_id = r0.json().get("id","")
        if not ensembl_id: return out

        query = """query T($id: String!){
          target(ensemblId: $id){
            tractability{ modality label value }
            knownDrugs(size: 30){
              rows{ drugId drugType prefName mechanismOfAction phase status disease{ name } }
            }
            associatedDiseases(page:{index:0,size:20}){
              rows{ score disease{ id name therapeuticAreas{ name } } }
            }
          }
        }"""
        r = requests.post("https://api.platform.opentargets.org/api/v4/graphql",
                          json={"query":query,"variables":{"id":ensembl_id}}, timeout=25)
        if r.status_code != 200: return out
        d = (r.json().get("data") or {}).get("target") or {}
        out["tractability"] = [t for t in (d.get("tractability") or []) if t.get("value")]
        out["drugs"] = ((d.get("knownDrugs") or {}).get("rows") or [])
        out["diseases"] = ((d.get("associatedDiseases") or {}).get("rows") or [])
    except Exception:
        pass
    return out

# --- STRING interactions -------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_string(gene: str, species: int=9606, limit: int=15) -> List[Dict]:
    try:
        r = requests.get("https://string-db.org/api/json/network",
              params={"identifiers":gene,"species":species,"limit":limit,
                      "required_score":700,"network_type":"functional"},
              timeout=20)
        r.raise_for_status()
        data = r.json()
        out = []
        for e in data:
            partner = e.get("preferredName_B") if e.get("preferredName_A","").upper()==gene.upper() else e.get("preferredName_A")
            if partner and partner.upper() != gene.upper():
                out.append({
                    "partner": partner,
                    "score": int(e.get("score",0)*1000) if isinstance(e.get("score"),float) else int(e.get("score",0)),
                    "exp": e.get("escore",0),
                    "db": e.get("dscore",0),
                    "text": e.get("tscore",0),
                })
        # de-duplicate, keep highest score
        seen = {}
        for o in out:
            if o["partner"] not in seen or o["score"]>seen[o["partner"]]["score"]:
                seen[o["partner"]] = o
        return sorted(seen.values(), key=lambda x:-x["score"])
    except Exception:
        return []

# --- gnomAD constraint ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_gnomad(gene: str) -> dict:
    try:
        q = """query G($g:String!){
          gene(gene_symbol:$g, reference_genome: GRCh38){
            gene_id symbol
            gnomad_constraint{ pLI oe_lof oe_mis lof_z mis_z exp_lof obs_lof }
          }
        }"""
        r = requests.post("https://gnomad.broadinstitute.org/api",
                          json={"query":q,"variables":{"g":gene.upper()}}, timeout=20)
        if r.status_code != 200: return {}
        d = ((r.json().get("data") or {}).get("gene") or {})
        return d.get("gnomad_constraint") or {}
    except Exception:
        return {}

# --- DGIdb drug interactions ---------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_dgidb(gene: str) -> List[Dict]:
    try:
        q = """query D($g:[String!]){
          genes(names:$g){
            nodes{ name interactions{ drug{ name } interactionTypes{ type } sources{ sourceDbName } interactionScore }}
          }
        }"""
        r = requests.post("https://dgidb.org/api/graphql",
                          json={"query":q,"variables":{"g":[gene.upper()]}}, timeout=20)
        if r.status_code != 200: return []
        nodes = ((r.json().get("data") or {}).get("genes") or {}).get("nodes",[])
        if not nodes: return []
        out = []
        for inter in (nodes[0].get("interactions") or []):
            drug = (inter.get("drug") or {}).get("name","?")
            it = ", ".join(i.get("type","") for i in (inter.get("interactionTypes") or []))
            src = ", ".join(s.get("sourceDbName","") for s in (inter.get("sources") or []))
            score = inter.get("interactionScore",0) or 0
            out.append({"drug":drug,"type":it or "interacts","sources":src,"score":score})
        return sorted(out, key=lambda x:-(x["score"] or 0))[:30]
    except Exception:
        return []

# --- Clinical Trials.gov v2 ----------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinical_trials(gene: str) -> List[Dict]:
    try:
        r = requests.get("https://clinicaltrials.gov/api/v2/studies",
              params={"query.term":gene,"pageSize":20,
                      "filter.overallStatus":"RECRUITING|ACTIVE_NOT_RECRUITING|COMPLETED|ENROLLING_BY_INVITATION"},
              timeout=20)
        r.raise_for_status()
        studies = r.json().get("studies",[])
        out = []
        for s in studies:
            ps = s.get("protocolSection",{})
            id_mod = ps.get("identificationModule",{})
            status_mod = ps.get("statusModule",{})
            design_mod = ps.get("designModule",{})
            cond_mod = ps.get("conditionsModule",{})
            out.append({
                "nct": id_mod.get("nctId",""),
                "title": id_mod.get("briefTitle",""),
                "status": status_mod.get("overallStatus",""),
                "phase": ", ".join(design_mod.get("phases",[])) or "—",
                "conditions": ", ".join(cond_mod.get("conditions",[])[:3]),
            })
        return out
    except Exception:
        return []

# --- PubMed abstracts ----------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed(gene: str, n: int=12) -> List[Dict]:
    try:
        r = requests.get(ESEARCH, params={"db":"pubmed",
              "term":f"{gene}[Title/Abstract]","retmax":n,
              "retmode":"json","sort":"pub_date"}, timeout=20)
        r.raise_for_status()
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2 = requests.get(EFETCH, params={"db":"pubmed",
              "id":",".join(ids),"retmode":"xml","rettype":"abstract"}, timeout=30)
        r2.raise_for_status()
        xml = r2.text
        out = []
        for chunk in re.split(r"<PubmedArticle>", xml)[1:]:
            tm = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", chunk, re.S)
            am = re.search(r"<AbstractText[^>]*>(.*?)</AbstractText>", chunk, re.S)
            ym = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", chunk, re.S)
            pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", chunk)
            if not tm: continue
            out.append({
                "title": re.sub(r"<[^>]+>","",tm.group(1))[:280],
                "abstract": re.sub(r"<[^>]+>","",am.group(1))[:1200] if am else "",
                "year": ym.group(1) if ym else "?",
                "pmid": pm.group(1) if pm else "",
            })
        return out
    except Exception:
        return []

# --- NCBI Taxonomy (Microbiome) ------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_ncbi_taxonomy(name: str) -> dict:
    """Resolve organism name → taxon lineage (kingdom→species)."""
    out = {"taxid":None, "name":name, "lineage":[]}
    try:
        r = requests.get(ESEARCH, params={"db":"taxonomy","term":name,
                          "retmax":1,"retmode":"json"}, timeout=15)
        r.raise_for_status()
        ids = r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return out
        out["taxid"] = ids[0]
        r2 = requests.get(EFETCH, params={"db":"taxonomy","id":ids[0],
                          "retmode":"xml"}, timeout=20)
        r2.raise_for_status()
        xml = r2.text
        scientific = re.search(r"<ScientificName>(.*?)</ScientificName>", xml)
        if scientific: out["name"] = scientific.group(1)
        # Extract lineage taxa
        lineage = []
        for chunk in re.findall(r"<Taxon>(.*?)</Taxon>", xml, re.S):
            tn = re.search(r"<ScientificName>(.*?)</ScientificName>", chunk)
            rk = re.search(r"<Rank>(.*?)</Rank>", chunk)
            if tn and rk and rk.group(1) != "no rank":
                lineage.append({"rank":rk.group(1), "name":tn.group(1)})
        out["lineage"] = lineage
        return out
    except Exception:
        return out


# ===============================================================================
#  GENOMIC INTEGRITY & ML SCORING
# ===============================================================================

def compute_gi(cv: dict, protein_length: int) -> dict:
    """Genomic Integrity Score — fraction of pathogenic ClinVar variants;
    density per 100 aa; verdict band."""
    summary = cv.get("summary",{})
    total = summary.get("total",0)
    path = summary.get("pathogenic",0)
    vus  = summary.get("vus",0)
    germ = summary.get("germline",0)
    som  = summary.get("somatic",0)
    if total == 0:
        return {"score":0.0, "density":0.0, "verdict":"deprioritise",
                "label":"NO VARIANTS", "total":0, "path":0, "vus":0,
                "germline":0, "somatic":0, "rationale":
                "No ClinVar entries found. Could indicate (a) understudied gene "
                "with low clinical ascertainment, or (b) truly disease-irrelevant."}
    score = path/total
    density = (path / max(protein_length,1)) * 100
    # Verdict bands
    if path >= 30 and density >= 5: verdict, label = "prioritise", "DISEASE-CRITICAL"
    elif path >= 10 and density >= 1.5: verdict, label = "proceed", "DISEASE-ASSOCIATED"
    elif path >= 3: verdict, label = "selective", "MODERATE"
    elif path >= 1: verdict, label = "caution", "VERY LOW"
    else: verdict, label = "deprioritise", "NO DISEASE VARIANTS"
    rationale = (
        f"{path:,}/{total:,} ClinVar variants are pathogenic ({score*100:.1f}%); "
        f"density {density:.2f} pathogenic per 100 aa. "
        f"Germline {germ}, somatic {som}, VUS {vus}."
    )
    return {"score":score, "density":density, "verdict":verdict, "label":label,
            "total":total, "path":path, "vus":vus, "germline":germ, "somatic":som,
            "rationale":rationale}


def ml_rank(ml_score: float, sens: int=50, clinvar_score: Optional[int]=None) -> str:
    """ML rank — capped by ClinVar clinical classification so a VUS can never
    reach CRITICAL no matter how disruptive the structural prediction is."""
    if clinvar_score is not None:
        if clinvar_score <= 1: return "NEUTRAL"          # benign / likely benign
        if clinvar_score == 2: return "MEDIUM"           # VUS cap
        # 3/4/5 → ML decides among CRITICAL/HIGH/MEDIUM
    s = sens/100
    if ml_score >= 0.75 - 0.20*s: return "CRITICAL"
    if ml_score >= 0.50 - 0.15*s: return "HIGH"
    if ml_score >= 0.30 - 0.10*s: return "MEDIUM"
    if ml_score >= 0.15 - 0.05*s: return "LOW"
    return "NEUTRAL"


def score_variants(variants: List[Dict], sens: int=50,
                   alpha_miss: Optional[Dict]=None,
                   sequence: str="") -> List[Dict]:
    """Score each variant by composite features:
       hydropathy shift · charge change · stop/frameshift · ClinVar quality
       · AlphaMissense (if available)."""
    out = []
    for v in variants:
        wt, pos, mut = aa_extract(v.get("variant_name",""))
        feats = {}
        s = 0.0
        # Position confidence: defined position → +0.05
        if pos: s += 0.05
        # Hydropathy shift
        if wt and mut and wt in HYDROPATHY and mut in HYDROPATHY:
            dh = abs(HYDROPATHY[wt]-HYDROPATHY[mut])
            feats["hydropathy_delta"] = dh
            s += min(dh/9, 0.25)
        # Charge change
        if wt and mut:
            ch = abs(AA_CHARGE.get(wt,0)-AA_CHARGE.get(mut,0))
            if ch >= 1:
                feats["charge_flip"] = ch
                s += 0.20
        # Stop-gain / frameshift
        if mut == "*" or "Ter" in (v.get("variant_name","")):
            feats["stop_gain"] = True
            s += 0.45
        if "fs" in (v.get("variant_name","")).lower():
            feats["frameshift"] = True
            s += 0.40
        # Splice
        if any(t in (v.get("variant_name","")).lower() for t in ["splice","ivs","+1g","-1g"]):
            feats["splice"] = True
            s += 0.35
        # AlphaMissense
        if alpha_miss and pos and mut and (pos,mut) in alpha_miss:
            am = alpha_miss[(pos,mut)]
            feats["alphamissense"] = round(am,3)
            s += am * 0.40
        # ClinVar review quality multiplier
        rev = (v.get("review","") or "").lower()
        if "reviewed by expert" in rev or "practice guideline" in rev:
            s *= 1.20
        elif "criteria provided" in rev:
            s *= 1.05
        s = max(0.0, min(1.0, s))
        ranked = ml_rank(s, sens, v.get("score"))
        out.append({**v, "ml":round(s,3), "ml_rank":ranked, "ml_feats":feats,
                    "wt":wt, "pos":pos, "mut":mut})
    return out


def compute_hotspots(scored: List[Dict], protein_length: int,
                     window: int=15, min_count: int=3) -> List[Dict]:
    """Sliding-window hotspot detection. Returns clusters of pathogenic variants
    that significantly exceed background density."""
    if protein_length < 30: return []
    positions = [v["pos"] for v in scored if v.get("pos") and v.get("score",0)>=4]
    if len(positions) < min_count: return []
    bg = len(positions) / protein_length
    hotspots = []
    counts_at = defaultdict(int)
    for p in positions:
        for w in range(max(1,p-window), min(protein_length,p+window)+1):
            counts_at[w] += 1
    smoothed = sorted(counts_at.items())
    # Find local maxima above 3x background
    used = set()
    for pos, ct in sorted(counts_at.items(), key=lambda x:-x[1]):
        if pos in used: continue
        if ct < max(min_count, 3*bg*(2*window+1)): continue
        # collect variants in this window
        in_window = [v for v in scored if v.get("pos") and abs(v["pos"]-pos)<=window]
        if len(in_window) < min_count: continue
        fold = ct / (bg*(2*window+1)+0.001)
        hotspots.append({
            "center":pos, "start":max(1,pos-window), "end":min(protein_length,pos+window),
            "count":len(in_window), "fold":round(fold,1),
            "variants":sorted(in_window, key=lambda x:-x.get("ml",0))[:5],
        })
        for w in range(max(1,pos-window), min(protein_length,pos+window)+1):
            used.add(w)
    return sorted(hotspots, key=lambda h:-h["count"])[:10]


# ===============================================================================
#  IP ENGINE #1 — FILAMIN H8 / RxxS PHOSPHORYLATION READOUT
#
#  Detects amphipathic helix-8-like segments and basic-residue clusters
#  preceding S/T (RxxS, RxRxxS, RRRxS) that are evolutionarily preserved as
#  phosphorylation anchors. Replaces β-arrestin recruitment as the primary
#  receptor-proximal activation readout (Protellect IP).
# ===============================================================================

def scan_phosphorylation_motifs(sequence: str) -> List[Dict]:
    """Find every kinase consensus motif in the protein sequence."""
    seq = (sequence or "").upper()
    hits = []
    for pattern, (kinase, desc) in KINASE_MOTIFS.items():
        for m in re.finditer(pattern, seq):
            # Find the S/T position within the match
            sub = m.group(0)
            for j,r in enumerate(sub):
                if r in PHOSPHO_RES and (j == len(sub)-1 or pattern.endswith("[ST]") or pattern.endswith("S") or pattern.endswith("S/T")):
                    pos = m.start() + j + 1  # 1-indexed
                    hits.append({
                        "position": pos,
                        "residue": r,
                        "motif": sub,
                        "kinase": kinase,
                        "description": desc,
                        "start": m.start()+1,
                        "end": m.end(),
                    })
                    break
            else:
                pos = m.end()  # fallback to end
                hits.append({
                    "position": pos, "residue": seq[pos-1] if pos<=len(seq) else "?",
                    "motif": sub, "kinase": kinase, "description": desc,
                    "start": m.start()+1, "end": m.end(),
                })
    # Deduplicate by position+kinase
    seen = set()
    dedup = []
    for h in hits:
        key = (h["position"], h["kinase"])
        if key not in seen:
            seen.add(key)
            dedup.append(h)
    return sorted(dedup, key=lambda x: x["position"])


def detect_helix_8(sequence: str) -> dict:
    """Detect a putative amphipathic helix-8 segment in the C-terminal third
    of a class-A GPCR-like sequence. Returns the candidate range + amphipathicity score."""
    seq = (sequence or "").upper()
    if len(seq) < 60:
        return {"found":False}
    # Search the C-terminal 25% of the sequence for an amphipathic 12-25 aa segment
    start_search = int(len(seq)*0.70)
    best = None
    for start in range(start_search, len(seq)-15):
        for length in (15, 18, 22):
            if start+length > len(seq): continue
            window = seq[start:start+length]
            # Hydrophobic moment: alternating hydrophobic / charged
            score = 0
            for j,r in enumerate(window):
                target = (r in AA_HYDROPHOBIC) if j%2==0 else (r in "RKED")
                if target: score += 1
            # bonus for FxxR-like anchor
            if H8_AMPHIPATHIC_HINT.search(window): score += 4
            # bonus for Phe + Arg
            if "F" in window and ("R" in window or "K" in window): score += 2
            if not best or score > best["score"]:
                best = {"start":start+1, "end":start+length, "seq":window, "score":score}
    if not best or best["score"] < 8:
        return {"found":False}
    return {**best, "found":True}


def filamin_anchor_score(sequence: str, h8: dict) -> dict:
    """Predict whether the candidate H8 segment can engage filamin via
    β-strand augmentation (filamin Ig domain ~ 95-100 aa repeat)."""
    if not h8.get("found"): return {"score":0, "details":"No helix-8 candidate."}
    window = h8["seq"]
    # alt-hydrophobic anchors (F, V, I, L at even positions)
    even_hydro = sum(1 for j,r in enumerate(window) if j%2==0 and r in "FVIL")
    odd_basic = sum(1 for j,r in enumerate(window) if j%2==1 and r in "RK")
    # F-R-L-style triple anchor
    triple = sum(1 for r in ("F","R","L") if r in window)
    score = min(1.0, (even_hydro*0.15 + odd_basic*0.10 + triple*0.10))
    return {
        "score": round(score,2),
        "even_hydrophobic_anchors": even_hydro,
        "odd_basic_anchors": odd_basic,
        "triple_FRL_count": triple,
        "details": (
            "Filamin β-strand augmentation requires alternating hydrophobic / "
            "charged side chains. Three anchor residues (F, R, L) typically "
            "stabilise the strand–strand interaction."
        ),
    }


def filamin_assay_report(sequence: str, gene: str, gpcr_class: Optional[str]=None) -> dict:
    """Top-level filamin / phosphorylation-readout report — the Protellect IP."""
    motifs = scan_phosphorylation_motifs(sequence)
    h8 = detect_helix_8(sequence)
    filamin = filamin_anchor_score(sequence, h8)
    # Find the strongest phospho-anchor — multi-arginine cluster preceding S/T
    rxxxs_sites = [m for m in motifs if m["kinase"] in ("PROTELLECT-RxxxS","FILAMIN-PKA","PKA")]
    primary_site = None
    if rxxxs_sites:
        # rank by motif length + arginine density
        rxxxs_sites.sort(key=lambda x: -(x["motif"].count("R") + x["motif"].count("K")))
        primary_site = rxxxs_sites[0]
    return {
        "gene": gene,
        "gpcr_class": gpcr_class or "Not GPCR / class unknown",
        "h8": h8,
        "filamin_score": filamin,
        "motifs": motifs,
        "primary_site": primary_site,
        "readout_recommendation": (
            "Use filamin-A pulldown + phospho-specific S2152 antibody as the "
            "receptor-proximal activation readout. Replaces β-arrestin "
            "recruitment, which is downstream and noisy. The phospho-S2152 "
            "epitope on filamin-A reports ligand-bound, autoinhibition-released "
            "GPCR state directly."
            if h8.get("found") else
            "No amphipathic H8 detected — protein likely does not signal through "
            "the filamin axis. Use receptor-class-appropriate proximal readout."
        ),
    }


# ===============================================================================
#  IP ENGINE #2 — CROSS-DISEASE VARIANT DATABASE SCANNER
#
#  • For every pathogenic variant in the queried gene, finds OTHER genes
#    carrying pathogenic variants for the same conditions → pathway partners.
#  • Flags digenic candidates (two-protein co-disease) and probable founder
#    mutations (high allele frequency in pathogenic-classified ClinVar entries).
#  • Triages disease vs non-disease variants (the user's "rule out non-disease
#    causing variants" requirement).
# ===============================================================================

def cross_disease_partners(cv: dict, max_partners: int=10) -> dict:
    """For each disease associated with the queried gene, fetch other genes
    with pathogenic variants for the same disease — pathway-partner discovery."""
    diseases = cv.get("summary",{}).get("top_conds",{})
    partners = defaultdict(lambda: {"diseases":set(),"shared_count":0})
    for disease, _ct in list(diseases.items())[:5]:
        try:
            genes = fetch_disease_genes(disease, max_genes=8)
            for g in genes:
                partners[g["gene"]]["diseases"].add(disease)
                partners[g["gene"]]["shared_count"] += g["count"]
        except Exception:
            continue
    out = []
    for gene, info in partners.items():
        out.append({
            "gene": gene,
            "shared_diseases": sorted(info["diseases"]),
            "shared_count": info["shared_count"],
            "n_shared": len(info["diseases"]),
        })
    return {
        "partners": sorted(out, key=lambda x:(-x["n_shared"], -x["shared_count"]))[:max_partners],
        "rationale": (
            "Two genes that independently cause the same Mendelian disease "
            "are highly likely to be direct interaction partners or "
            "immediate neighbours in the same pathway. Use these as the "
            "starting set for pathway reconstruction."
        ),
    }


def triage_variants(scored: List[Dict]) -> dict:
    """Separate disease-relevant variants from probable noise/background."""
    relevant, noise, vus_actionable = [], [], []
    for v in scored:
        sc = v.get("score",0)
        if sc >= 4:  # pathogenic / likely pathogenic
            relevant.append(v)
        elif sc == 2:  # VUS — actionable if ML/AlphaMissense flags it
            feats = v.get("ml_feats",{})
            if v.get("ml",0) >= 0.6 or feats.get("alphamissense",0) >= 0.7 or \
               feats.get("stop_gain") or feats.get("frameshift") or feats.get("splice"):
                vus_actionable.append(v)
            else:
                noise.append(v)
        else:
            noise.append(v)
    return {
        "disease_relevant": relevant,
        "vus_reclassify_candidates": vus_actionable,
        "background_noise": noise,
        "summary": (
            f"{len(relevant)} pathogenic variants flagged as disease-relevant. "
            f"{len(vus_actionable)} VUS recommended for re-classification "
            f"(strong ML/AlphaMissense or null-allele features). "
            f"{len(noise)} variants treated as likely non-causal background."
        ),
    }


def founder_mutation_candidates(scored: List[Dict], cv: dict) -> List[Dict]:
    """A 'founder' mutation pattern: a pathogenic variant that recurs across
    many ClinVar submissions for the same disease, suggesting a single
    historical origin or hotspot rather than independent reoccurrences."""
    # Group pathogenic variants by their condition + AA-change
    bucket = defaultdict(list)
    for v in scored:
        if v.get("score",0) < 4: continue
        key = (v.get("condition","").split(";")[0].strip(), v.get("wt"), v.get("pos"), v.get("mut"))
        if all(key[1:]): bucket[key].append(v)
    founders = []
    for (cond, wt, pos, mut), vs in bucket.items():
        if len(vs) >= 2:
            founders.append({
                "condition": cond,
                "variant": f"{wt}{pos}{mut}",
                "n_submissions": len(vs),
                "exemplar_url": vs[0].get("url",""),
                "rationale": (
                    "Multiple independent ClinVar submissions of the identical "
                    "amino-acid change for the same condition — consistent with "
                    "a founder allele or a strong mutational hotspot."
                ),
            })
    return sorted(founders, key=lambda x:-x["n_submissions"])[:10]


# ===============================================================================
#  CHEMISTRY RENDERER
#
#  • Animated peptide backbone with R-groups
#  • Phosphorylation cycle animation (kinase ATP → S/T → ADP / phosphatase)
#  • Side-chain detail viewer for any residue
#  All rendered as inline SVG/HTML with CSS keyframe animations — no plugins.
# ===============================================================================

# Schematic Lewis structures for amino-acid side chains (R groups).
# Each entry maps the 1-letter code → a description used by the renderer.
AA_SIDECHAIN_DESC = {
    "A":{"r":"-CH3", "feature":"Methyl group · hydrophobic · smallest non-Gly residue."},
    "R":{"r":"-(CH2)3-NH-C(NH2)=NH2+","feature":"Positively-charged guanidinium head — primary anchor for filamin RxxS clusters."},
    "N":{"r":"-CH2-CONH2","feature":"Amide side chain · H-bond donor + acceptor."},
    "D":{"r":"-CH2-COO-","feature":"Negatively-charged carboxylate · CK2 substrate context."},
    "C":{"r":"-CH2-SH","feature":"Thiol · forms disulfide bridges · druggable handle for covalent inhibitors."},
    "Q":{"r":"-(CH2)2-CONH2","feature":"Polar amide · longer than Asn · H-bond network."},
    "E":{"r":"-(CH2)2-COO-","feature":"Negatively-charged · catalytic residue in many enzymes."},
    "G":{"r":"-H","feature":"No side chain · maximum backbone flexibility · turn residue."},
    "H":{"r":"-CH2-imidazole","feature":"Imidazole ring · pKa near physiological · proton-shuttling."},
    "I":{"r":"-CH(CH3)-CH2-CH3","feature":"Branched β-carbon · strong hydrophobic core packing."},
    "L":{"r":"-CH2-CH(CH3)2","feature":"Branched γ-carbon · primary hydrophobic anchor in α-helices."},
    "K":{"r":"-(CH2)4-NH3+","feature":"Positively-charged amine · PKA/PKC substrate flank · ubiquitination site."},
    "M":{"r":"-(CH2)2-S-CH3","feature":"Thioether · start codon · oxidation-sensitive."},
    "F":{"r":"-CH2-phenyl","feature":"Aromatic · π-stacking · filamin β-strand augmentation anchor."},
    "P":{"r":"cyclic to backbone","feature":"Imino acid · breaks α-helices · proline-directed kinase target flank."},
    "S":{"r":"-CH2-OH","feature":"Hydroxyl · PRINCIPAL PHOSPHORYLATION SITE (PKA/PKC/CK2)."},
    "T":{"r":"-CH(OH)-CH3","feature":"Hydroxyl + methyl · phosphorylation site with steric bulk."},
    "W":{"r":"-CH2-indole","feature":"Largest residue · aromatic · membrane-interface anchor."},
    "Y":{"r":"-CH2-phenol","feature":"Aromatic hydroxyl · tyrosine kinase substrate · pH-sensitive."},
    "V":{"r":"-CH(CH3)2","feature":"Branched β-carbon · hydrophobic core · steric bulk."},
}


def render_backbone_svg(sequence: str, highlights: Optional[Dict]=None,
                        width: int=900, residues_shown: int=60) -> str:
    """Render an animated peptide backbone SVG showing N-Cα-C peptide bonds,
    R-group nubs colour-coded by chemistry, and optional highlighted positions.
    highlights : {position: "kinase"|"variant"|"helix8"|"filamin"}
    """
    highlights = highlights or {}
    seq = (sequence or "")[:residues_shown]
    if not seq:
        return "<div class='empty-state'>No sequence available.</div>"

    spacing = max(20, (width - 80) // max(len(seq),1))
    height = 220
    y_back = 90
    nodes_x = [40 + i*spacing for i in range(len(seq))]

    parts = [f"<svg viewBox='0 0 {width} {height}' xmlns='http://www.w3.org/2000/svg' style='background:#02060d;border:1px solid #13314f;border-radius:3px;'>"]

    # animated peptide-bond shimmer
    parts.append("""
    <defs>
      <linearGradient id='bondGrad' x1='0%' x2='100%'>
        <stop offset='0%' stop-color='#1a4470'/>
        <stop offset='50%' stop-color='#00f5d4'/>
        <stop offset='100%' stop-color='#1a4470'/>
        <animate attributeName='x1' from='-100%' to='100%' dur='3s' repeatCount='indefinite'/>
        <animate attributeName='x2' from='0%' to='200%' dur='3s' repeatCount='indefinite'/>
      </linearGradient>
      <radialGradient id='phosGrad'>
        <stop offset='0%' stop-color='#ffb02e'/>
        <stop offset='100%' stop-color='#ff3d7f'/>
      </radialGradient>
    </defs>
    """)

    # backbone line
    if len(nodes_x) > 1:
        d = f"M {nodes_x[0]} {y_back} " + " ".join(f"L {x} {y_back}" for x in nodes_x[1:])
        parts.append(f"<path d='{d}' stroke='url(#bondGrad)' stroke-width='2' fill='none'/>")

    # peptide bond ticks (animated dashing)
    for i, x in enumerate(nodes_x[:-1]):
        x_mid = (nodes_x[i] + nodes_x[i+1]) / 2
        parts.append(
            f"<line x1='{x_mid-3}' y1='{y_back-6}' x2='{x_mid+3}' y2='{y_back+6}' "
            f"stroke='#324b66' stroke-width='1'>"
            f"<animate attributeName='opacity' values='.4;1;.4' dur='2s' "
            f"begin='{i*0.05}s' repeatCount='indefinite'/></line>"
        )

    # residues + R-groups
    for i, (x, r) in enumerate(zip(nodes_x, seq)):
        pos = i + 1
        hl = highlights.get(pos)
        # Cα node
        col = "#13314f"
        if r in AA_HYDROPHOBIC: col = "#ffb02e"
        elif r in AA_AROMATIC:   col = "#9d4edd"
        elif r in "RK":          col = "#3a7bff"
        elif r in "DE":          col = "#ff3d7f"
        elif r in "STY":         col = "#00f5d4"   # phospho-target
        elif r in "C":           col = "#9bff4a"
        # R-group nub
        r_y = y_back - 28 if i%2==0 else y_back + 28
        parts.append(
            f"<line x1='{x}' y1='{y_back}' x2='{x}' y2='{r_y}' "
            f"stroke='{col}' stroke-width='1' opacity='.55'/>"
        )
        # R-group label / dot
        if r in PHOSPHO_RES and hl in (None,"kinase","filamin"):
            # animated hydroxyl ready to be phosphorylated
            parts.append(
                f"<circle cx='{x}' cy='{r_y}' r='6' fill='{col}'>"
                f"<animate attributeName='r' values='5;7.5;5' dur='1.6s' "
                f"begin='{i*0.04}s' repeatCount='indefinite'/></circle>"
            )
        else:
            parts.append(f"<circle cx='{x}' cy='{r_y}' r='4' fill='{col}' opacity='.85'/>")

        # Cα circle
        ring = ""
        if hl == "variant":
            ring = "<animate attributeName='r' values='6;10;6' dur='1.4s' repeatCount='indefinite'/>"
            ring_col = "#ff2d55"
        elif hl == "kinase" or hl == "filamin":
            ring_col = "#00f5d4"
        elif hl == "helix8":
            ring_col = "#9d4edd"
        else:
            ring_col = None
        parts.append(f"<circle cx='{x}' cy='{y_back}' r='4' fill='#02060d' stroke='{col}' stroke-width='1.5'/>")
        if ring_col:
            parts.append(f"<circle cx='{x}' cy='{y_back}' r='8' fill='none' "
                         f"stroke='{ring_col}' stroke-width='1.5'>{ring}</circle>")
        # Phospho ball if filamin/kinase site
        if hl in ("kinase","filamin"):
            parts.append(
                f"<circle cx='{x}' cy='{r_y-12}' r='5' fill='url(#phosGrad)'>"
                f"<animate attributeName='cy' values='{r_y-30};{r_y-12};{r_y-30}' "
                f"dur='2.2s' begin='{i*0.07}s' repeatCount='indefinite'/>"
                f"<animate attributeName='opacity' values='0;1;0' dur='2.2s' "
                f"begin='{i*0.07}s' repeatCount='indefinite'/></circle>"
            )
            parts.append(
                f"<text x='{x}' y='{r_y-32}' fill='#ffb02e' font-size='9' "
                f"font-family='monospace' text-anchor='middle' opacity='.7'>P</text>"
            )

        # residue label
        parts.append(f"<text x='{x}' y='{y_back+5}' fill='#dde9f5' "
                     f"font-size='9' font-family='monospace' text-anchor='middle'>{r}</text>")
        # position label every 5
        if pos%5 == 0:
            parts.append(f"<text x='{x}' y='{height-8}' fill='#5a7794' "
                         f"font-size='8' font-family='monospace' text-anchor='middle'>{pos}</text>")

    # legend
    leg_y = 18
    legends = [
        ("#ffb02e","Hydrophobic"), ("#9d4edd","Aromatic"),
        ("#3a7bff","Basic (R/K)"), ("#ff3d7f","Acidic (D/E)"),
        ("#00f5d4","Phospho (S/T/Y)"), ("#ff2d55","Variant site"),
    ]
    for j,(c,lab) in enumerate(legends):
        x0 = 40 + j*130
        parts.append(f"<circle cx='{x0}' cy='{leg_y}' r='4' fill='{c}'/>")
        parts.append(f"<text x='{x0+10}' y='{leg_y+4}' fill='#9fb8d0' "
                     f"font-size='9' font-family='monospace'>{lab}</text>")

    parts.append("</svg>")
    return "".join(parts)


def render_phosphorylation_cycle(residue: str="S", position: int=2152,
                                 kinase: str="PKA", phosphatase: str="PP2A") -> str:
    """Full animated kinase / phosphatase cycle on a single residue.
    Shows ATP → kinase phosphoryl transfer → phospho-residue → PP2A
    hydrolysis → free residue. Loops indefinitely."""
    return f"""
<div style='background:#02060d;border:1px solid #13314f;border-radius:3px;padding:1rem;'>
<svg viewBox='0 0 760 320' xmlns='http://www.w3.org/2000/svg' style='width:100%;'>
<defs>
  <radialGradient id='kinaseG'>
    <stop offset='0%' stop-color='#3a7bff'/><stop offset='100%' stop-color='#1a3a8a'/>
  </radialGradient>
  <radialGradient id='phosG'>
    <stop offset='0%' stop-color='#9d4edd'/><stop offset='100%' stop-color='#5a1e8a'/>
  </radialGradient>
  <radialGradient id='atpG'>
    <stop offset='0%' stop-color='#ffb02e'/><stop offset='100%' stop-color='#b07000'/>
  </radialGradient>
  <radialGradient id='resG'>
    <stop offset='0%' stop-color='#00f5d4'/><stop offset='100%' stop-color='#009d8a'/>
  </radialGradient>
  <filter id='glow'><feGaussianBlur stdDeviation='2'/></filter>
</defs>

<!-- substrate residue -->
<circle cx='380' cy='180' r='38' fill='url(#resG)' opacity='.9'/>
<text x='380' y='178' fill='#021' font-size='15' font-weight='700' text-anchor='middle' font-family='monospace'>{residue}{position}</text>
<text x='380' y='195' fill='#021' font-size='9' text-anchor='middle' font-family='monospace'>OH</text>

<!-- kinase (orbiting) -->
<g>
  <animateTransform attributeName='transform' type='rotate' from='0 380 180' to='360 380 180' dur='12s' repeatCount='indefinite'/>
  <circle cx='240' cy='180' r='34' fill='url(#kinaseG)' filter='url(#glow)' opacity='.85'/>
  <text x='240' y='175' fill='#dde9f5' font-size='12' font-weight='700' text-anchor='middle' font-family='monospace'>{kinase}</text>
  <text x='240' y='188' fill='#9fb8d0' font-size='8' text-anchor='middle' font-family='monospace'>kinase</text>
</g>

<!-- phosphatase (counter-orbit) -->
<g>
  <animateTransform attributeName='transform' type='rotate' from='180 380 180' to='540 380 180' dur='12s' repeatCount='indefinite'/>
  <circle cx='240' cy='180' r='30' fill='#1a0e1c' stroke='#ff3d7f' stroke-width='2' opacity='.85'/>
  <text x='240' y='175' fill='#ff3d7f' font-size='11' font-weight='700' text-anchor='middle' font-family='monospace'>{phosphatase}</text>
  <text x='240' y='188' fill='#9fb8d0' font-size='8' text-anchor='middle' font-family='monospace'>phosphatase</text>
</g>

<!-- ATP molecule that travels into the kinase -->
<g>
  <circle cx='80' cy='100' r='12' fill='url(#atpG)'>
    <animateMotion dur='4s' repeatCount='indefinite' path='M 0 0 L 180 70 L 220 80 L 240 80'/>
    <animate attributeName='opacity' values='1;1;0' keyTimes='0;0.85;1' dur='4s' repeatCount='indefinite'/>
  </circle>
  <text x='80' y='130' fill='#ffb02e' font-size='10' text-anchor='middle' font-family='monospace'>ATP</text>
</g>

<!-- phosphate transferred onto residue -->
<g>
  <circle cx='240' cy='180' r='8' fill='url(#phosG)' opacity='0'>
    <animateMotion dur='4s' begin='1.6s' repeatCount='indefinite' path='M 0 0 L 140 0'/>
    <animate attributeName='opacity' values='0;1;1;0' keyTimes='0;0.2;0.8;1' dur='4s' begin='1.6s' repeatCount='indefinite'/>
  </circle>
  <text x='380' y='150' fill='#9d4edd' font-size='14' text-anchor='middle' font-family='monospace' opacity='0'>
    P
    <animate attributeName='opacity' values='0;1;1;0' keyTimes='0;0.55;0.85;1' dur='4s' begin='1.6s' repeatCount='indefinite'/>
  </text>
</g>

<!-- ADP released -->
<g>
  <circle cx='240' cy='180' r='10' fill='#b07000' opacity='0'>
    <animateMotion dur='4s' begin='2.2s' repeatCount='indefinite' path='M 0 0 L -180 -90'/>
    <animate attributeName='opacity' values='0;0;1;0' keyTimes='0;0.55;0.7;1' dur='4s' begin='2.2s' repeatCount='indefinite'/>
  </circle>
</g>

<!-- arrow labels -->
<text x='150' y='90' fill='#ffb02e' font-size='10' font-family='monospace'>ATP in →</text>
<text x='95' y='245' fill='#5a7794' font-size='10' font-family='monospace'>← ADP out</text>
<text x='520' y='160' fill='#9d4edd' font-size='11' font-family='monospace'>→ {residue}{position}-P (active)</text>

<!-- downstream filamin box -->
<rect x='580' y='140' width='140' height='80' fill='#0a1828' stroke='#00f5d4' stroke-width='1.5' rx='2'/>
<text x='650' y='168' fill='#00f5d4' font-size='11' font-weight='700' text-anchor='middle' font-family='monospace'>FILAMIN-A</text>
<text x='650' y='184' fill='#9fb8d0' font-size='9' text-anchor='middle' font-family='monospace'>β-strand</text>
<text x='650' y='197' fill='#9fb8d0' font-size='9' text-anchor='middle' font-family='monospace'>augmentation</text>
<text x='650' y='212' fill='#dde9f5' font-size='9' text-anchor='middle' font-family='monospace'>autoinhibition ↑</text>

<!-- title -->
<text x='380' y='28' fill='#00f5d4' font-size='13' font-weight='700' text-anchor='middle' font-family='Space Grotesk'>PHOSPHORYLATION CYCLE — {residue}{position}</text>
<text x='380' y='44' fill='#9fb8d0' font-size='10' text-anchor='middle' font-family='monospace'>ATP → kinase → phospho-residue → phosphatase → reset</text>

<text x='380' y='285' fill='#5a7794' font-size='9' text-anchor='middle' font-family='monospace'>Protellect IP — receptor-proximal readout · replaces β-arrestin recruitment assay</text>
</svg>
</div>
"""


def render_sidechain_detail(residue: str) -> str:
    """Detail card for a single amino-acid side chain."""
    desc = AA_SIDECHAIN_DESC.get(residue, {"r":"—","feature":"Unknown residue."})
    return f"""
<div style='background:linear-gradient(180deg,#06101e,#02060d);
            border:1px solid #13314f;border-radius:3px;padding:1rem;'>
  <div style='font-family:Space Grotesk,sans-serif;font-size:1.4rem;color:#00f5d4;'>
    {residue} · {AA_FULL.get(residue,'?')}</div>
  <div style='font-family:monospace;font-size:.85rem;color:#dde9f5;margin:.5rem 0;'>
    <span style='color:#5a7794;'>R-group:</span> {desc['r']}</div>
  <div style='font-family:monospace;font-size:.85rem;color:#dde9f5;'>
    <span style='color:#5a7794;'>Hydropathy:</span> {HYDROPATHY.get(residue,'?')}
    &nbsp;·&nbsp;
    <span style='color:#5a7794;'>Charge:</span> {AA_CHARGE.get(residue,0)}</div>
  <div style='font-family:monospace;font-size:.8rem;color:#9fb8d0;margin-top:.6rem;line-height:1.5;'>
    {desc['feature']}</div>
</div>
"""


# ===============================================================================
#  3D STRUCTURE RENDERER (3Dmol.js, CDN)
# ===============================================================================

def render_3d_structure(pdb_text: str, scored: List[Dict],
                        phospho_sites: List[Dict]|None=None,
                        h8: Optional[Dict]=None, height: int=540) -> str:
    """3Dmol viewer with: pLDDT-coloured cartoon, variant spheres (rank-coloured),
    phosphorylation sites (yellow), helix-8 segment (purple)."""
    phospho_sites = phospho_sites or []
    var_map = {}
    for v in scored[:80]:
        try:
            p = int(v.get("pos") or v.get("start") or 0)
            if p:
                var_map[p] = {"rank":v.get("ml_rank","NEUTRAL"),
                              "ml":v.get("ml",0),"sig":v.get("sig",""),
                              "cond":(v.get("condition","") or "")[:60],
                              "var":(v.get("variant_name","") or "")[:40],
                              "url":v.get("url","")}
        except: pass
    phos_pos = sorted({p["position"] for p in phospho_sites})
    h8_range = [h8["start"], h8["end"]] if (h8 and h8.get("found")) else None

    pdb_esc = (pdb_text or "").replace("`","\\`").replace("\\","\\\\")
    var_js = json.dumps({str(k):v for k,v in var_map.items()})
    phos_js = json.dumps(phos_pos)
    h8_js = json.dumps(h8_range)

    html = f"""<!DOCTYPE html><html><head>
<script src='https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js'></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#02060d;font-family:'JetBrains Mono',monospace;color:#dde9f5;height:{height}px;display:flex;flex-direction:column;}}
#ctrl{{display:flex;gap:4px;padding:6px 8px;background:#04101e;border-bottom:1px solid #13314f;flex-wrap:wrap;flex-shrink:0;}}
.b{{background:#06101e;color:#9fb8d0;border:1px solid #13314f;padding:3px 9px;border-radius:2px;cursor:pointer;font:11px 'JetBrains Mono',monospace;letter-spacing:.04em;text-transform:uppercase;transition:all .15s;}}
.b:hover,.b.on{{background:#00f5d4;color:#021;border-color:#00f5d4;font-weight:700;}}
#wrap{{position:relative;flex:1;}}#v{{width:100%;height:100%;}}
#panel{{position:absolute;top:8px;right:8px;width:240px;background:rgba(2,6,13,.96);border:1px solid #13314f;border-radius:3px;padding:10px;display:none;backdrop-filter:blur(8px);max-height:90%;overflow-y:auto;}}
#panel h3{{color:#00f5d4;font:12px 'JetBrains Mono',monospace;margin-bottom:6px;border-bottom:1px solid #13314f;padding-bottom:4px;}}
.pr{{display:flex;justify-content:space-between;margin:2px 0;font:11px 'JetBrains Mono',monospace;}}
.pk{{color:#5a7794;}}.pv{{color:#dde9f5;}}
#leg{{position:absolute;bottom:8px;left:8px;background:rgba(2,6,13,.92);border:1px solid #13314f;border-radius:3px;padding:6px 9px;font:10px 'JetBrains Mono',monospace;color:#9fb8d0;}}
.li{{display:flex;align-items:center;gap:5px;margin:2px 0;}}.ld{{width:8px;height:8px;border-radius:50%;}}
</style></head><body>
<div id='ctrl'>
<button class='b on' onclick='ss("cartoon",this)'>Ribbon</button>
<button class='b' onclick='ss("stick",this)'>Stick</button>
<button class='b' onclick='ss("sphere",this)'>Sphere</button>
<button class='b' onclick='ss("surface",this)'>Surface</button>
<button class='b' id='sp' onclick='spinT()'>▶ Spin</button>
<button class='b' onclick='v.zoomTo();v.render()'>Reset</button>
<button class='b on' onclick='tV(this)'>Variants</button>
<button class='b on' onclick='tP(this)'>Phospho</button>
<button class='b on' onclick='tH(this)'>Helix-8</button>
</div>
<div id='wrap'><div id='v'></div>
<div id='panel'><h3 id='pt'>—</h3><div id='pc'></div></div>
<div id='leg'>
<div class='li'><div class='ld' style='background:#1565C0'></div>Very conf (pLDDT≥90)</div>
<div class='li'><div class='ld' style='background:#29B6F6'></div>Conf (70–90)</div>
<div class='li'><div class='ld' style='background:#FDD835'></div>Low (50–70)</div>
<div class='li'><div class='ld' style='background:#FF7043'></div>Very low</div>
<div class='li'><div class='ld' style='background:#ff2d55'></div>Variant</div>
<div class='li'><div class='ld' style='background:#ffd528'></div>Phospho S/T/Y</div>
<div class='li'><div class='ld' style='background:#9d4edd'></div>Helix-8</div>
</div></div>
<script>
const variants={var_js};const phos={phos_js};const h8={h8_js};const pdb=`{pdb_esc}`;
const aa3={{ALA:'A',ARG:'R',ASN:'N',ASP:'D',CYS:'C',GLN:'Q',GLU:'E',GLY:'G',HIS:'H',ILE:'I',LEU:'L',LYS:'K',MET:'M',PHE:'F',PRO:'P',SER:'S',THR:'T',TRP:'W',TYR:'Y',VAL:'V'}};
let spin=false,showV=true,showP=true,showH=true,style='cartoon';
const v=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:0x02060d}});
v.addModel(pdb,'pdb');
function cf(a){{const b=a.b;if(b>=90)return'#1565C0';if(b>=70)return'#29B6F6';if(b>=50)return'#FDD835';return'#FF7043';}}
function ap(){{v.removeAllSurfaces();
if(style==='surface') v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:cf,opacity:.75}});
else if(style==='sphere') v.setStyle({{}},{{sphere:{{colorfunc:cf,radius:.7}}}});
else if(style==='stick') v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.2}},stick:{{colorscheme:'chainHetatm',radius:.12}}}});
else v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.42}}}});
// helix-8
if(showH && h8 && h8.length===2){{
  v.addStyle({{resi:h8[0]+'-'+h8[1]}},{{cartoon:{{color:'#9d4edd',thickness:.7}}}});
}}
// variant spheres
if(showV) Object.entries(variants).forEach(([p,inf])=>{{
  const r=inf.rank, c=r==='CRITICAL'?'#ff2d55':r==='HIGH'?'#ff8c42':r==='MEDIUM'?'#ffd528':'#5a7794';
  v.addStyle({{resi:parseInt(p),atom:'CA'}},{{sphere:{{radius:1.25,color:c,opacity:.92}}}});
}});
// phospho sites
if(showP) phos.forEach(p=>{{
  v.addStyle({{resi:p,atom:'CA'}},{{sphere:{{radius:1.15,color:'#ffd528',opacity:.95}}}});
}});
v.render();}}
ap();v.zoomTo();v.render();
v.setClickable({{}},true,function(a){{
const pos=a.resi,r3=(a.resn||'').toUpperCase(),r1=aa3[r3]||'?';
const inf=variants[String(pos)];
let html=`<div class='pr'><span class='pk'>Residue</span><span class='pv'>${{r1}}${{pos}}</span></div>`;
html+=`<div class='pr'><span class='pk'>pLDDT</span><span class='pv'>${{(a.b||0).toFixed(1)}}</span></div>`;
if(phos.includes(pos)) html+=`<div class='pr'><span class='pk'>Phospho site</span><span class='pv' style='color:#ffd528'>YES</span></div>`;
if(h8 && h8.length===2 && pos>=h8[0] && pos<=h8[1]) html+=`<div class='pr'><span class='pk'>In helix-8</span><span class='pv' style='color:#9d4edd'>YES</span></div>`;
if(inf){{
  html+='<hr style="border-color:#13314f;margin:5px 0">';
  html+=`<div class='pr'><span class='pk'>Variant</span><span class='pv'>${{inf.var}}</span></div>`;
  html+=`<div class='pr'><span class='pk'>Significance</span><span class='pv'>${{inf.sig}}</span></div>`;
  html+=`<div class='pr'><span class='pk'>ML rank</span><span class='pv' style='color:#00f5d4'>${{inf.rank}}</span></div>`;
  if(inf.url) html+=`<a href='${{inf.url}}' target='_blank' style='color:#00f5d4;font-size:10px;'>↗ ClinVar</a>`;
  if(inf.cond) html+=`<div style='margin-top:4px;color:#9fb8d0;font-size:10px;'>${{inf.cond}}</div>`;
}}
document.getElementById('pt').textContent=r3+pos;document.getElementById('pc').innerHTML=html;document.getElementById('panel').style.display='block';
}});
function ss(s,b){{style=s;document.querySelectorAll('#ctrl .b').forEach(x=>{{if(['Ribbon','Stick','Sphere','Surface'].includes(x.textContent))x.classList.remove('on');}});b.classList.add('on');ap();}}
function spinT(){{spin=!spin;v.spin(spin?'y':false,.6);const b=document.getElementById('sp');b.textContent=spin?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spin);}}
function tV(b){{showV=!showV;b.classList.toggle('on',showV);ap();}}
function tP(b){{showP=!showP;b.classList.toggle('on',showP);ap();}}
function tH(b){{showH=!showH;b.classList.toggle('on',showH);ap();}}
</script></body></html>"""
    return html



# ===============================================================================
#  DISEASE CLASSIFIER — routes diseases to domains
# ===============================================================================

def classify_disease(d):
    d=(d or "").lower(); out=set()
    if any(k in d for k in ONC_KEYWORDS):   out.add("Oncology")
    if any(k in d for k in NEURO_KEYWORDS): out.add("Neuroscience")
    if any(k in d for k in CARDIO_KEYWORDS):out.add("Cardiology")
    if any(k in d for k in RARE_HINT_KEYWORDS):out.add("Rare Disease")
    return out or {"General"}

def domain_split(cv):
    buckets={d:[] for d in ["Oncology","Neuroscience","Cardiology","Rare Disease","General"]}
    for disease,ct in (cv.get("summary",{}).get("top_conds",{}) or {}).items():
        for dom in classify_disease(disease): buckets.setdefault(dom,[]).append({"disease":disease,"count":ct})
    return buckets


# ===============================================================================
#  DOMAIN: ONCOLOGY — somatic/germline, founder, metastasis risk, patient-tailored
# ===============================================================================
ONC_DRIVER_TIERS = {
    "TIER1_TS":{"TP53","RB1","PTEN","APC","BRCA1","BRCA2","VHL","NF1","CDKN2A","SMAD4"},
    "TIER1_ONC":{"KRAS","NRAS","HRAS","BRAF","MYC","EGFR","ERBB2","PIK3CA","AKT1","MTOR"},
    "EMT":{"CDH1","SNAI1","SNAI2","ZEB1","ZEB2","TWIST1","VIM","TGFB1","MMP9"},
    "DDR":{"ATM","ATR","CHEK1","CHEK2","MLH1","MSH2","MSH6","PMS2","FANCA","FANCC"},
}

def oncology_report(gene,scored,cv,gi,patient_age=None,cancer_type=None,stage=None):
    tier="Untiered"
    for k,gs in ONC_DRIVER_TIERS.items():
        if gene.upper() in gs: tier=k; break
    som=[v for v in scored if v.get("somatic") and v.get("score",0)>=4]
    germ=[v for v in scored if v.get("germline") and not v.get("somatic") and v.get("score",0)>=4]
    cancer_count=defaultdict(set)
    for v in som+germ:
        for c in (v.get("condition","") or "").split(";"):
            c=c.strip().lower()
            if any(k in c for k in ONC_KEYWORDS):
                key=(v.get("wt"),v.get("pos"),v.get("mut"))
                if all(key): cancer_count[key].add(c[:60])
    early=[{"variant":f"{w}{p}{m}","n":len(cs),"cancers":sorted(cs)[:5]} for (w,p,m),cs in cancer_count.items() if len(cs)>=2]
    early.sort(key=lambda x:-x["n"])
    met="HIGH" if gene.upper() in ONC_DRIVER_TIERS["EMT"] else "MODERATE" if gene.upper() in ONC_DRIVER_TIERS["DDR"] else "STANDARD"
    recs=[]
    if cancer_type:
        rel=[v for v in som if cancer_type.lower() in (v.get("condition","") or "").lower()]
        recs.append(f"{len(rel)} somatic variants match {cancer_type} ClinVar entries." if rel else f"No {cancer_type}-specific somatic variants; consider tumour-normal sequencing.")
    if patient_age and patient_age<40 and germ: recs.append("Age <40 + germline pathogenic → refer for hereditary cancer-syndrome panel.")
    if stage in ("III","IV","Metastatic") and met=="HIGH": recs.append("Late-stage + EMT-pathway gene → evaluate anti-metastasis combination regimens.")
    if not recs: recs.append("Enter cancer type and stage in sidebar for patient-tailored guidance.")
    return {"tier":tier,"somatic":len(som),"germline":len(germ),"early_events":early[:5],"met_risk":met,"recs":recs,"top_som":som[:8],"top_germ":germ[:8]}


# ===============================================================================
#  DOMAIN: NEUROSCIENCE — ion channels, synaptic layers, epilepsy panel
# ===============================================================================
NEURO_FAMILIES = {
    "ION_NA":{"SCN1A","SCN2A","SCN8A","SCN9A","SCN5A"},
    "ION_K":{"KCNQ1","KCNQ2","KCNQ3","KCNH2","KCNJ11","KCNB1"},
    "ION_CA":{"CACNA1A","CACNA1C","CACNA1H","CACNA1S"},
    "GLUTAMATE":{"GRIN1","GRIN2A","GRIN2B","GRIA1","GRM5"},
    "GABA":{"GABRA1","GABRB3","GABRG2","GABBR2"},
    "DOPAMINE":{"DRD1","DRD2","DRD3","DRD4","SLC6A3","TH"},
    "SEROTONIN":{"HTR1A","HTR2A","HTR2C","SLC6A4"},
    "SYN_VESICLE":{"SYN1","SYN2","SYT1","STX1A","SNAP25","VAMP2"},
    "PSD":{"DLG4","SHANK3","HOMER1","DLG2"},
    "MYELIN":{"MBP","PLP1","MAG","MPZ","PMP22"},
    "AXON":{"KIF1A","KIF5A","DYNC1H1"},
}

def neuro_report(gene,scored,cv,gi):
    fam="Not in curated neural set"
    for f,gs in NEURO_FAMILIES.items():
        if gene.upper() in gs: fam=f; break
    epi=sum(1 for v in scored if any(k in (v.get("condition","") or "").lower() for k in ["epilep","seizure"]))
    cort=sum(1 for v in scored if any(k in (v.get("condition","") or "").lower() for k in ["heterotopia","lissencephaly","cortical"]))
    layer="—"
    if fam in ("PSD","GLUTAMATE","GABA","DOPAMINE","SEROTONIN"): layer="Postsynaptic"
    elif fam=="SYN_VESICLE": layer="Presynaptic"
    elif fam.startswith("ION_"): layer="Axon / dendrite (electrical)"
    elif fam in ("MYELIN","AXON"): layer="Axon / glial"
    axes=[]
    if "ION_NA" in fam: axes.append("Na-channel inhibitors (carbamazepine, lacosamide)")
    if "ION_K" in fam: axes.append("KV7 openers (retigabine class)")
    if "GLUTAMATE" in fam: axes.append("NMDA modulators (memantine) / AMPA antagonists (perampanel)")
    if "GABA" in fam: axes.append("Benzodiazepine axis; cenobamate")
    if epi>=3 and gi.get("verdict") in ("prioritise","proceed"): axes.append("Gene-therapy / ASO trial candidate")
    if not axes: axes.append("No curated pharmacological axis for this family.")
    return {"family":fam,"layer":layer,"epilepsy":epi,"cortical":cort,"axes":axes}


# ===============================================================================
#  DOMAIN: CARDIOLOGY — filamin axis, arrhythmia, GPCR piggyback
# ===============================================================================
CARDIO_FAMILIES = {
    "FILAMIN":{"FLNA","FLNB","FLNC"},
    "LONG_QT":{"KCNQ1","KCNH2","SCN5A","KCNE1","KCNE2"},
    "HCM":{"MYH7","MYBPC3","TNNT2","TNNI3","TPM1","ACTC1"},
    "DCM":{"TTN","LMNA","MYH7","FLNC","RBM20","DSP"},
    "BETA_AR":{"ADRB1","ADRB2","ADRB3"},
    "GRK":{"GRK1","GRK2","GRK3","GRK4","GRK5","GRK6"},
    "ARRESTIN":{"ARRB1","ARRB2"},
    "AORTOPATHY":{"ACTA2","MYLK","MYH11","FBN1","TGFBR1","TGFBR2"},
}

def cardio_report(gene,scored,cv,gi,sequence):
    fam="Not in curated cardiology set"
    for f,gs in CARDIO_FAMILIES.items():
        if gene.upper() in gs: fam=f; break
    arr=sum(1 for v in scored if any(k in (v.get("condition","") or "").lower() for k in ["arrhyth","qt","brugada"]))
    cm=sum(1 for v in scored if "cardiomyop" in (v.get("condition","") or "").lower())
    aort=sum(1 for v in scored if any(k in (v.get("condition","") or "").lower() for k in ["aortic","aneurysm"]))
    het=sum(1 for v in scored if "heterotopia" in (v.get("condition","") or "").lower())
    piggy=fam in ("ARRESTIN","GRK") and gi.get("path",0)==0
    fr=filamin_assay_report(sequence,gene)
    notes=[]
    if fam=="FILAMIN": notes.append("Direct filamin axis member. S2152 phospho-readout is receptor-proximal GPCR activation marker.")
    if piggy: notes.append(f"{gene} is in the {fam} class but has zero pathogenic Mendelian variants — classic piggyback. Focus on FLNA/ADRB1/KCNH2 instead.")
    if aort>=1 and gene.upper()=="FLNA": notes.append("Thoracic aortic aneurysm signal — smooth-muscle vascular axis.")
    if het>=1: notes.append("Periventricular heterotopia (FLNA neuronal migration). Kinase activation / phosphatase inhibition on S2152 may rescue.")
    axes=[]
    if fam=="LONG_QT": axes.append("β-blockers (nadolol); mexiletine (SCN5A-LQT3); ICD high-risk")
    if fam in ("HCM","DCM"): axes.append("Cardiac myosin inhibitors (mavacamten for HCM); SGLT2i/ARNI for DCM")
    if fam=="FILAMIN": axes.append("PKA activation / PP2A inhibition → restore S2152 phospho; anti-aneurysm regimens for vascular phenotype")
    if fam=="AORTOPATHY": axes.append("Losartan / ARB; β-blockade; surgical timing by aortic diameter")
    if not axes: axes.append("Assess on individual variant basis.")
    return {"family":fam,"arrhythmia":arr,"cardiomyopathy":cm,"aortopathy":aort,"heterotopia":het,"piggyback":piggy,"filamin":fr,"notes":notes,"axes":axes}


# ===============================================================================
#  DOMAIN: RARE DISEASE / MENDELIAN
# ===============================================================================
def rare_report(gene,scored,cv,gi):
    txt=" ".join((v.get("condition","")+v.get("title","") for v in scored)).lower()
    inherit=[]
    if "recessive" in txt: inherit.append("Autosomal recessive")
    if "dominant" in txt: inherit.append("Autosomal dominant")
    if "x-linked" in txt or "xlinked" in txt: inherit.append("X-linked")
    if "de novo" in txt: inherit.append("De novo")
    if not inherit: inherit=["Pattern unclear from ClinVar data"]
    syndromes=[{"name":c,"count":ct} for c,ct in (cv.get("summary",{}).get("top_conds",{}) or {}).items() if any(k in c.lower() for k in RARE_HINT_KEYWORDS)]
    syndromes.sort(key=lambda x:-x["count"])
    de_novo=sum(1 for v in scored if "de novo" in (v.get("origin","") or "").lower())
    pen="High" if gi.get("score",0)>=0.4 else "Variable" if gi.get("score",0)>=0.1 else "Low"
    orphan=gi.get("path",0)>=5 and len(syndromes)>=1
    return {"inheritance":inherit,"syndromes":syndromes[:8],"de_novo":de_novo,"penetrance":pen,"orphan":orphan}


# ===============================================================================
#  DOMAIN: MICROBIOME — taxonomy + LLM pathway re-annotation
# ===============================================================================
PATHWAY_EXPANSION = {
    "biosynthesis":[
        ("Amino acid biosynthesis (KEGG 01230)","ILV pathway, TRP operon, PEP/pyruvate assembly"),
        ("Fatty acid biosynthesis (KEGG 00061)","Type II FAS / acyl-carrier-protein pathway"),
        ("Cofactor biosynthesis (KEGG 00770)","Folate, biotin, riboflavin, B12, pantothenate"),
        ("Nucleotide biosynthesis (KEGG 00230/00240)","De novo purine & pyrimidine"),
        ("Cell-wall / peptidoglycan (KEGG 00550)","Mur enzymes, lipid II, MraY/MurG"),
        ("LPS biosynthesis (KEGG 00540)","Lipid A core, O-antigen transport"),
    ],
    "chemosynthesis":[
        ("Carbon fixation (KEGG 00710/00720)","Calvin cycle, rTCA, Wood-Ljungdahl, 3-HP/4-HB"),
        ("Sulfur oxidation (KEGG 00920)","Sox system, dsr operon"),
        ("Nitrification (KEGG 00910)","AMO, HAO, NXR — Nitrosomonas/Nitrobacter"),
        ("Methanogenesis (KEGG 00680)","MCR, MTR, formyl-MFR pathway"),
    ],
    "protein aggregation":[
        ("Amyloid fibre assembly (curli/CsgA)","Functional amyloid for biofilm scaffolding"),
        ("Inclusion-body formation","IbpA/IbpB sHSP-mediated sequestration under stress"),
        ("Disaggregase machinery (ClpB/Hsp104)","Reversal of aggregates — drug-target axis"),
    ],
    "transport":[
        ("ABC transporters (KEGG 02010)","Multidrug efflux, sugar import, peptide uptake"),
        ("PTS phosphotransferase (KEGG 02060)","Sugar-specific Enzyme II complexes"),
        ("Type IV / VI secretion","Effector delivery, contact-dependent killing"),
    ],
    "energy metabolism":[
        ("Glycolysis (KEGG 00010)","Hexokinase → pyruvate kinase"),
        ("TCA cycle (KEGG 00020)","Citrate synthase → malate dehydrogenase"),
        ("Oxidative phosphorylation (KEGG 00190)","Complex I–IV + F-ATPase"),
        ("Anaerobic fermentation","Mixed-acid, butanediol, butyrate, propionate"),
    ],
    "drug resistance":[
        ("β-lactamase classes A–D","Carbapenemase, ESBL — OXA, KPC, NDM, VIM"),
        ("Efflux pump (AcrAB-TolC)","Multidrug resistance — RND family"),
        ("Aminoglycoside-modifying enzymes","AAC, APH, ANT"),
        ("Ribosomal RNA methylation","erm, cfr — macrolide / linezolid resistance"),
    ],
    "signal transduction":[
        ("Two-component systems (KEGG 02020)","HK → RR phosphorelay — resistance + virulence"),
        ("Quorum sensing (KEGG 02024)","AHL, AIP, AI-2 — LuxR/LuxI"),
        ("(p)ppGpp stringent response","Stress + antibiotic tolerance"),
    ],
}

MICROBIOME_TAXA = {
    "escherichia coli":{"role":"Commensal & opportunistic pathogen","paths":["energy metabolism","transport","drug resistance"]},
    "bacteroides fragilis":{"role":"Gut commensal · SCFA producer","paths":["energy metabolism","biosynthesis"]},
    "bifidobacterium":{"role":"Infant microbiome anchor","paths":["biosynthesis","energy metabolism"]},
    "lactobacillus":{"role":"Lactic-acid bacteria · gut/vaginal health","paths":["energy metabolism","biosynthesis"]},
    "akkermansia muciniphila":{"role":"Mucin degrader · metabolic-health marker","paths":["energy metabolism","transport"]},
    "clostridioides difficile":{"role":"Nosocomial pathogen · toxin colitis","paths":["drug resistance","signal transduction"]},
    "helicobacter pylori":{"role":"Gastric pathogen · urease-positive","paths":["signal transduction","drug resistance"]},
    "staphylococcus aureus":{"role":"Skin pathogen · MRSA","paths":["drug resistance","biosynthesis"]},
    "pseudomonas aeruginosa":{"role":"Opportunistic · CF lung","paths":["drug resistance","signal transduction","transport"]},
    "faecalibacterium prausnitzii":{"role":"Anti-inflammatory · butyrate","paths":["energy metabolism"]},
}

def expand_pathway(label):
    key=label.lower().strip()
    if key in PATHWAY_EXPANSION: return PATHWAY_EXPANSION[key]
    for k,lst in PATHWAY_EXPANSION.items():
        if k in key or key in k: return lst
    return []

def llm_annotate(organism,label):
    """LLM pathway expansion via Anthropic API if key available; else curated."""
    try: key=st.secrets.get("ANTHROPIC_API_KEY")
    except: key=None
    if key:
        try:
            r=requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":600,
                      "messages":[{"role":"user","content":
                        f"You are a microbial genomics expert. The organism '{organism}' has a gene annotated with the vague pathway label '{label}'. "
                        f"Expand this into 3-5 specific KEGG/MetaCyc-level sub-pathways with brief descriptions. "
                        f"Format: one per line, 'Sub-pathway name | Description'. No preamble."}]}, timeout=30)
            if r.status_code==200:
                txt=(r.json().get("content",[{}])[0].get("text","") or "")
                return txt
        except: pass
    items=expand_pathway(label)
    if items: return "\n".join(f"{n} | {d}" for n,d in items)
    return f"No curated sub-pathways for '{label}'. Add ANTHROPIC_API_KEY to secrets for LLM expansion."


# ===============================================================================
#  PHARMACEUTICALS / DRUGGABILITY ENGINE
# ===============================================================================

def pharma_report(gene,scored,gi,ot,dgidb,trials,hotspots,sequence):
    """Comprehensive druggability & pharmaceutical landscape."""
    # Tractability
    tract={}
    for t in (ot.get("tractability") or []):
        tract[t.get("modality","?")] = t.get("value",False)
    # Drug pipeline
    drugs_by_phase=defaultdict(list)
    for d in (ot.get("drugs") or []):
        drugs_by_phase[d.get("phase","?")].append({
            "name":d.get("prefName","?"), "mechanism":d.get("mechanismOfAction",""),
            "status":d.get("status",""), "disease":(d.get("disease") or {}).get("name","")
        })
    # Hotspot druggability
    hotspot_targets=[]
    for h in (hotspots or []):
        hotspot_targets.append({
            "center":h["center"],"range":f"{h['start']}-{h['end']}",
            "n_variants":h["count"],"fold":h["fold"],
            "strategy":"Small molecule" if tract.get("Small molecule") else
                       "Antibody" if tract.get("Antibody") else
                       "PROTAC" if tract.get("PROTAC") else "Screen required",
        })
    # Phospho sites as drug targets
    motifs=scan_phosphorylation_motifs(sequence)
    kinase_targets=[m for m in motifs if m["kinase"] in ("PKA","PKC","CK2","CDK/MAPK","FILAMIN-PKA")]
    # Trial summary
    active=[t for t in (trials or []) if "RECRUITING" in (t.get("status","") or "").upper()]
    return {
        "tractability":tract, "drugs_by_phase":dict(drugs_by_phase),
        "dgidb_interactions":dgidb[:15], "hotspot_targets":hotspot_targets,
        "kinase_drug_targets":kinase_targets[:10],
        "active_trials":active[:10],
        "total_drugs":sum(len(v) for v in drugs_by_phase.values()),
        "total_trials":len(trials or []),
    }


def render_druggability_map(scored, hotspots, plen, tract):
    """Interactive druggability map SVG — variant positions coloured by rank,
    hotspot zones highlighted as drug-target regions."""
    w,h=900,200
    parts=[f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' style='background:#02060d;border:1px solid #13314f;border-radius:3px;'>"]
    # protein chain
    lm,rm=50,w-50
    chain_w=rm-lm
    parts.append(f"<rect x='{lm}' y='80' width='{chain_w}' height='12' fill='#0a1828' rx='2'/>")
    # Hotspot zones
    for hs in (hotspots or []):
        x1=lm + (hs["start"]/max(plen,1))*chain_w
        x2=lm + (hs["end"]/max(plen,1))*chain_w
        parts.append(f"<rect x='{x1}' y='60' width='{max(x2-x1,4)}' height='52' fill='#ff2d5520' stroke='#ff2d55' stroke-width='1' rx='2'>"
                     f"<animate attributeName='opacity' values='.4;.8;.4' dur='2s' repeatCount='indefinite'/></rect>")
        parts.append(f"<text x='{(x1+x2)/2}' y='55' fill='#ff2d55' font-size='9' text-anchor='middle' font-family='monospace'>DRUG TARGET</text>")
    # Variant lollipops
    for v in scored[:80]:
        try:
            pos=int(v.get("pos") or v.get("start") or 0)
        except: continue
        if not pos: continue
        x=lm + (pos/max(plen,1))*chain_w
        col={"CRITICAL":"#ff2d55","HIGH":"#ffb02e","MEDIUM":"#ffd528"}.get(v.get("ml_rank",""),"#5a7794")
        ht=25 + (v.get("ml",0))*35
        parts.append(f"<line x1='{x}' y1='80' x2='{x}' y2='{80-ht}' stroke='{col}' stroke-width='1.5'/>")
        parts.append(f"<circle cx='{x}' cy='{80-ht}' r='3' fill='{col}'/>")
    # Axis
    for tick in range(0,max(plen,1),max(plen//10,1)):
        x=lm+(tick/max(plen,1))*chain_w
        parts.append(f"<text x='{x}' y='{h-10}' fill='#5a7794' font-size='8' text-anchor='middle' font-family='monospace'>{tick}</text>")
    # Tractability badges
    tx=lm
    for mod,val in (tract or {}).items():
        if val:
            parts.append(f"<rect x='{tx}' y='5' width='{len(mod)*7+16}' height='18' fill='#00f5d415' stroke='#00f5d4' stroke-width='.5' rx='2'/>")
            parts.append(f"<text x='{tx+8}' y='17' fill='#00f5d4' font-size='9' font-family='monospace'>{mod}</text>")
            tx+=len(mod)*7+24
    parts.append(f"<text x='{w/2}' y='{h-2}' fill='#324b66' font-size='8' text-anchor='middle' font-family='monospace'>Protein position (aa)</text>")
    parts.append("</svg>")
    return "".join(parts)


# ===============================================================================
#  MICROBIOME REPORTING
# ===============================================================================

def microbiome_report(organism_name: str, gene_hint: str = "") -> dict:
    """Microbiome domain: taxonomy + functional annotation expansion."""
    tax = fetch_ncbi_taxonomy(organism_name)
    known = MICROBIOME_TAXA.get(organism_name.lower())
    pdata = None
    try:
        pdata = fetch_uniprot(f"{gene_hint} {organism_name}", allow_nonhuman=True)
    except: pass
    
    # Extract vague pathway keywords from UniProt
    paths_found = []
    if pdata:
        for c in (pdata.get("comments") or []):
            if c.get("commentType") == "FUNCTION":
                txt = ((c.get("texts") or [{}])[0].get("value","") or "").lower()
                for k in PATHWAY_EXPANSION.keys():
                    if k in txt: paths_found.append(k)
    paths_found = list(set(paths_found))
    
    # LLM-expand
    expanded = {}
    for pw in paths_found[:3]:
        expanded[pw] = llm_annotate(organism_name, pw)
    
    return {
        "organism": tax.get("name", organism_name),
        "taxid": tax.get("taxid"),
        "lineage": tax.get("lineage", []),
        "role": known["role"] if known else "Not in curated set",
        "curated_pathways": known["paths"] if known else [],
        "detected_pathways": paths_found,
        "llm_expanded": expanded,
        "uniprot": pdata.get("primaryAccession") if pdata else None,
    }


# ===============================================================================
#  MAIN STREAMLIT APP
# ===============================================================================

def main():
    # --- SIDEBAR
    with st.sidebar:
        st.markdown("<h2 style='color:#00f5d4;'>PROTELLECT v32</h2>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:.75rem;color:#5a7794;'>Genetics-first protein intelligence</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Domain selector
        st.markdown("<h3 style='font-size:.9rem;color:#dde9f5;margin-bottom:.5rem;'>DOMAIN</h3>", unsafe_allow_html=True)
        domain = st.selectbox("", DOMAINS, index=DOMAINS.index(st.session_state["domain"]), label_visibility="collapsed")
        st.session_state["domain"] = domain
        st.markdown("---")
        
        # Protein / organism search
        if domain == "Microbiome":
            st.markdown("<h3 style='font-size:.9rem;color:#dde9f5;'>ORGANISM</h3>", unsafe_allow_html=True)
            query = st.text_input("", placeholder="Escherichia coli", label_visibility="collapsed")
        else:
            st.markdown("<h3 style='font-size:.9rem;color:#dde9f5;'>GENE</h3>", unsafe_allow_html=True)
            query = st.text_input("", placeholder="TP53 / FLNC / BRCA1", label_visibility="collapsed")
        
        sens = st.slider("ML sensitivity", 0, 100, st.session_state["sensitivity"])
        st.session_state["sensitivity"] = sens
        
        # Domain-specific inputs
        extra = {}
        if domain == "Oncology":
            st.markdown("<h3 style='font-size:.9rem;color:#dde9f5;margin-top:1rem;'>PATIENT</h3>", unsafe_allow_html=True)
            extra["cancer_type"] = st.selectbox("Cancer type", ["—"] + CANCER_TYPES)
            extra["stage"] = st.selectbox("Stage", ["—","I","II","III","IV","Metastatic"])
            extra["age"] = st.number_input("Age (optional)", 0, 120, 0)
        
        if st.button("ANALYZE", type="primary", use_container_width=True):
            if not query.strip():
                st.error("Enter a gene/protein/organism.")
                return
            with st.spinner("Analyzing..."):
                try:
                    allow_nh = (domain == "Microbiome")
                    pdata = fetch_uniprot(query, allow_nonhuman=allow_nh)
                    gene = ((pdata.get("genes") or [{}])[0].get("geneName",{}).get("value","") or query.upper())
                    seq = pdata.get("sequence", {}).get("value", "")
                    uid = pdata.get("primaryAccession", "")
                    
                    if not allow_nh or "Homo sapiens" in (pdata.get("organism",{}).get("scientificName","")):
                        # Human protein path
                        cv = fetch_clinvar(gene)
                        gi = compute_gi(cv, len(seq))
                        alpha = fetch_alphamissense(uid)
                        scored = score_variants(cv["variants"], sens, alpha, seq)
                        gnomad = fetch_gnomad(gene)
                        ot = fetch_opentargets(gene)
                        string_data = fetch_string(gene)
                        dgidb_data = fetch_dgidb(gene)
                        trials = fetch_clinical_trials(gene)
                        pdb = fetch_pdb(uid)
                        papers = fetch_pubmed(gene)
                        hotspots = compute_hotspots(scored, len(seq))
                        
                        # IP engines
                        fil_report = filamin_assay_report(seq, gene)
                        partners = cross_disease_partners(cv)
                        triage = triage_variants(scored)
                        founders = founder_mutation_candidates(scored, cv)
                        
                        # Domain reports
                        domain_data = {}
                        if domain == "Oncology":
                            domain_data = oncology_report(gene, scored, cv, gi, gnomad,
                                                          extra.get("age") if extra.get("age") else None,
                                                          extra.get("cancer_type") if extra.get("cancer_type")!="—" else None,
                                                          extra.get("stage") if extra.get("stage")!="—" else None)
                        elif domain == "Neuroscience":
                            domain_data = neuroscience_report(gene, scored, cv, gi)
                        elif domain == "Cardiology":
                            domain_data = cardiology_report(gene, scored, cv, gi, seq)
                        elif domain == "Rare Disease":
                            domain_data = rare_disease_report(gene, scored, cv, gi)
                        
                        pharma = pharma_report(gene, scored, gi, ot, dgidb_data, trials, hotspots, seq)
                        
                        st.session_state["current_gene"] = gene
                        st.session_state["current_data"] = {
                            "pdata": pdata, "cv": cv, "gi": gi, "scored": scored,
                            "gnomad": gnomad, "ot": ot, "string": string_data,
                            "dgidb": dgidb_data, "trials": trials, "pdb": pdb,
                            "papers": papers, "hotspots": hotspots, "seq": seq,
                            "uid": uid, "alpha": alpha,
                            "filamin": fil_report, "partners": partners,
                            "triage": triage, "founders": founders,
                            "domain_data": domain_data, "pharma": pharma,
                        }
                    else:
                        # Microbiome path
                        micro = microbiome_report(query, query)
                        st.session_state["current_gene"] = gene
                        st.session_state["current_data"] = {
                            "pdata": pdata, "seq": seq, "uid": uid,
                            "microbiome": micro, "domain": "Microbiome",
                        }
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    return
    
    # --- MAIN AREA
    data = st.session_state.get("current_data")
    gene = st.session_state.get("current_gene")
    
    if not data:
        st.markdown("<div class='empty-state' style='margin-top:3rem;'>Enter a gene/protein in the sidebar to begin.</div>", unsafe_allow_html=True)
        return
    
    # --- MICROBIOME DOMAIN
    if data.get("domain") == "Microbiome":
        micro = data.get("microbiome", {})
        st.markdown(f"<h1>{micro.get('organism','Organism')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='mono'>Taxon: {micro.get('taxid','—')} · UniProt: {data.get('uid','—')}</p>", unsafe_allow_html=True)
        
        sec("1", "Taxonomy Lineage")
        lineage = micro.get("lineage", [])
        if lineage:
            lin = " → ".join(f"<span class='mono-acc'>{t['name']}</span> <span class='mono' style='color:#5a7794;'>({t['rank']})</span>" for t in lineage[-6:])
            st.markdown(lin, unsafe_allow_html=True)
        else:
            st.markdown("<p class='mono'>No lineage data.</p>", unsafe_allow_html=True)
        
        sec("2", "Functional Role")
        st.markdown(f"<p class='mono'>{micro.get('role','Not curated.')}</p>", unsafe_allow_html=True)
        
        sec("3", "Pathway Annotations (LLM-Expanded)")
        expanded = micro.get("llm_expanded", {})
        if expanded:
            for pw, annot in expanded.items():
                with st.expander(f"📌 {pw.upper()}", expanded=False):
                    st.markdown(f"<div class='mono' style='line-height:1.7;'>{annot}</div>", unsafe_allow_html=True)
        else:
            curated = micro.get("curated_pathways", [])
            if curated:
                st.markdown(f"<p class='mono'>Curated: {', '.join(curated)}</p>", unsafe_allow_html=True)
            else:
                st.markdown("<p class='mono'>No pathway data. Add ANTHROPIC_API_KEY for LLM.</p>", unsafe_allow_html=True)
        return
    
    # --- HUMAN PROTEIN DOMAINS
    gi = data["gi"]
    verdict = gi["verdict"]
    vdata = VERDICTS[verdict]
    
    st.markdown(f"<h1>{gene}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p class='mono'>UniProt: {data['uid']} · {len(data['seq'])} aa · {len(data['cv']['variants'])} variants</p>", unsafe_allow_html=True)
    
    # Verdict
    st.markdown(f"""<div class='verdict {vdata[1]}'>
    <h2>{vdata[0]}</h2>
    <div class='vsub'>{vdata[2]}<br>{gi['rationale']}</div>
    </div>""", unsafe_allow_html=True)
    
    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(kpi("Pathogenic", gi["path"], f"{gi['score']*100:.1f}%", "pink"), unsafe_allow_html=True)
    with col2:
        st.markdown(kpi("Density", f"{gi['density']:.2f}", "per 100 aa", "amber"), unsafe_allow_html=True)
    with col3:
        pli = data["gnomad"].get("pLI", 0) or 0
        st.markdown(kpi("pLI", f"{pli:.3f}", "LoF intolerance", "lime" if pli>=0.9 else ""), unsafe_allow_html=True)
    with col4:
        n_drugs = data["pharma"]["total_drugs"]
        st.markdown(kpi("Drugs", n_drugs, f"{data['pharma']['total_trials']} trials", "violet"), unsafe_allow_html=True)
    
    # --- TAB STRUCTURE BY DOMAIN
    if domain == "Core Triage":
        tabs = st.tabs(["📊 Overview", "🔴 Variants", "🧬 3D Structure", "⚗️ Chemistry & PTM", "💊 Pharmaceuticals"])
        with tabs[0]:  # Overview
            sec("1", "Disease Associations")
            conds = data["cv"]["summary"].get("top_conds", {})
            if conds:
                df = pd.DataFrame([{"Disease": k, "Count": v} for k,v in list(conds.items())[:10]])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.markdown("<div class='empty-state'>No ClinVar diseases.</div>", unsafe_allow_html=True)
            sec("2", "Pathway Partners")
            partners = data["partners"]["partners"]
            if partners:
                df_p = pd.DataFrame(partners[:8])
                st.dataframe(df_p, use_container_width=True, hide_index=True)
            else:
                st.markdown("<p class='mono'>No shared-disease partners.</p>", unsafe_allow_html=True)
        
        with tabs[1]:  # Variants
            sec("1", "Variant Triage")
            tri = data["triage"]
            st.markdown(f"<p class='mono'>{tri['summary']}</p>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h4>Disease-Relevant ({len(tri['disease_relevant'])})</h4>", unsafe_allow_html=True)
                for v in tri["disease_relevant"][:5]:
                    st.markdown(f"{badge(v['ml_rank'])} {v['variant_name']}", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h4>VUS Reclassify ({len(tri['vus_reclassify_candidates'])})</h4>", unsafe_allow_html=True)
                for v in tri["vus_reclassify_candidates"][:5]:
                    st.markdown(f"{badge(v['ml_rank'])} {v['variant_name']}", unsafe_allow_html=True)
        
        with tabs[2]:  # 3D
            sec("1", "AlphaFold 3D Structure")
            if data["pdb"]:
                motifs = scan_phosphorylation_motifs(data["seq"])
                h8 = detect_helix_8(data["seq"])
                html_3d = render_3d_structure(data["pdb"], data["scored"], motifs, h8)
                components.html(html_3d, height=560, scrolling=False)
            else:
                st.markdown("<div class='empty-state'>No AlphaFold model.</div>", unsafe_allow_html=True)
        
        with tabs[3]:  # Chemistry
            sec("1", "Peptide Backbone")
            motifs = scan_phosphorylation_motifs(data["seq"])
            hl = {m["position"]: "kinase" for m in motifs[:30]}
            for v in data["scored"][:10]:
                if v.get("pos"): hl[v["pos"]] = "variant"
            h8 = detect_helix_8(data["seq"])
            if h8.get("found"):
                for p in range(h8["start"], h8["end"]+1):
                    if p not in hl: hl[p] = "helix8"
            svg = render_backbone_svg(data["seq"], hl, 1100, 80)
            st.markdown(svg, unsafe_allow_html=True)
            
            sec("2", "Phosphorylation Cycle")
            if motifs:
                top = motifs[0]
                cycle = render_phosphorylation_cycle(top["residue"], top["position"], top["kinase"], "PP2A")
                st.markdown(cycle, unsafe_allow_html=True)
            
            sec("3", "Filamin H8 Readout (IP)")
            fr = data["filamin"]
            st.markdown(f"<p class='mono'><b>H8 detected:</b> {fr['h8'].get('found',False)}</p>", unsafe_allow_html=True)
            if fr["h8"].get("found"):
                st.markdown(f"<p class='mono'>{fr['h8']['seq']} ({fr['h8']['start']}–{fr['h8']['end']})</p>", unsafe_allow_html=True)
            st.markdown(f"<div class='mono' style='margin-top:.5rem;line-height:1.6;'>{fr['readout_recommendation']}</div>", unsafe_allow_html=True)
        
        with tabs[4]:  # Pharma
            pharma = data["pharma"]
            sec("1", "Tractability")
            tract = pharma["tractability"]
            if tract:
                cols = st.columns(len(tract))
                for i, (mod, val) in enumerate(tract.items()):
                    with cols[i]:
                        st.markdown(kpi(mod, "✓" if val else "✗", "", "lime" if val else ""), unsafe_allow_html=True)
            
            sec("2", "Known Drugs")
            if pharma["drugs_by_phase"]:
                for ph, drugs in sorted(pharma["drugs_by_phase"].items(), reverse=True):
                    with st.expander(f"{ph} ({len(drugs)})", expanded=False):
                        for d in drugs[:5]:
                            st.markdown(f"**{d['name']}** — {d['mechanism'][:60]}", unsafe_allow_html=False)
            else:
                st.markdown("<p class='mono'>No approved drugs.</p>", unsafe_allow_html=True)
            
            sec("3", "Druggable Hotspots")
            map_svg = render_druggability_map(data["scored"], pharma["hotspot_targets"], len(data["seq"]), tract)
            st.markdown(map_svg, unsafe_allow_html=True)
    
    elif domain == "Oncology":
        onc = data["domain_data"]
        tabs = st.tabs(["🎯 Dashboard", "🔴 Somatic/Germline", "💊 Therapy"])
        with tabs[0]:
            sec("1", "Driver Classification")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(kpi("Tier", onc["tier"], "", "pink"), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("Somatic", onc["somatic_count"], "", "amber"), unsafe_allow_html=True)
            with col3:
                st.markdown(kpi("Germline", onc["germline_count"], "", "lime"), unsafe_allow_html=True)
            with col4:
                st.markdown(kpi("Metastasis Risk", onc["metastasis_risk"], "", "red" if onc["metastasis_risk"]=="HIGH" else ""), unsafe_allow_html=True)
            
            sec("2", "Early Events")
            for e in onc["early_events"]:
                st.markdown(f"**{e['variant']}** — {e['n_cancers']} types: {', '.join(e['cancers'])}", unsafe_allow_html=False)
            
            sec("3", "Patient Recommendations")
            for rec in onc["recommendations"]:
                st.markdown(f"• {rec}", unsafe_allow_html=False)
        
        with tabs[1]:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<h3>Somatic ({len(onc['top_somatic'])})</h3>", unsafe_allow_html=True)
                for v in onc["top_somatic"]:
                    st.markdown(f"{badge(v['ml_rank'])} {v['variant_name']}", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<h3>Germline ({len(onc['top_germline'])})</h3>", unsafe_allow_html=True)
                for v in onc["top_germline"]:
                    st.markdown(f"{badge(v['ml_rank'])} {v['variant_name']}", unsafe_allow_html=True)
        
        with tabs[2]:
            sec("1", "Actionable Drugs")
            for ph, drugs in sorted(data["pharma"]["drugs_by_phase"].items(), reverse=True):
                if drugs:
                    st.markdown(f"**{ph}**", unsafe_allow_html=False)
                    for d in drugs[:5]:
                        st.markdown(f"• {d['name']}", unsafe_allow_html=False)
    
    elif domain == "Neuroscience":
        neuro = data["domain_data"]
        tabs = st.tabs(["🧠 Profile", "⚡ Synapses", "💊 Therapeutics"])
        with tabs[0]:
            sec("1", "Gene Family")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(kpi("Family", neuro["family"], "", "violet"), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("Layer", neuro["synaptic_layer"], "", "lime"), unsafe_allow_html=True)
            
            sec("2", "Phenotypes")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(kpi("Epilepsy", neuro["epilepsy_variants"], "", "pink"), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("Cortical", neuro["cortical_malformation"], "", "amber"), unsafe_allow_html=True)
            with col3:
                st.markdown(kpi("ID", neuro["intellectual_disability"], "", ""), unsafe_allow_html=True)
            st.markdown(f"<p class='mono' style='margin-top:1rem;'>{neuro['rationale']}</p>", unsafe_allow_html=True)
        
        with tabs[1]:
            st.markdown(f"<p class='mono'>Layer: {neuro['synaptic_layer']}</p>", unsafe_allow_html=True)
        
        with tabs[2]:
            sec("1", "Therapeutic Axes")
            for ax in neuro["therapeutic_axes"]:
                st.markdown(f"• {ax}", unsafe_allow_html=False)
    
    elif domain == "Cardiology":
        cardio = data["domain_data"]
        tabs = st.tabs(["❤️ Panel", "🔗 Filamin Axis", "💊 Drugs"])
        with tabs[0]:
            sec("1", "Family")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(kpi("Family", cardio["family"], "", "pink"), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("Arrhythmia", cardio["arrhythmia_variants"], "", "amber"), unsafe_allow_html=True)
            with col3:
                st.markdown(kpi("CM", cardio["cardiomyopathy_variants"], "", "lime"), unsafe_allow_html=True)
            
            if cardio["piggyback_flag"]:
                st.warning(f"⚠️ {gene} is {cardio['family']} but has no Mendelian variants — piggyback.")
            for note in cardio["notes"]:
                st.markdown(f"• {note}", unsafe_allow_html=False)
        
        with tabs[1]:
            fr = cardio["filamin_readout"]
            st.markdown(f"<p class='mono'><b>H8:</b> {fr['h8'].get('found',False)}</p>", unsafe_allow_html=True)
            if fr["h8"].get("found"):
                st.markdown(f"<p class='mono'>{fr['h8']['seq']} ({fr['h8']['start']}–{fr['h8']['end']})</p>", unsafe_allow_html=True)
            st.markdown(f"<div class='mono'>{fr['readout_recommendation']}</div>", unsafe_allow_html=True)
        
        with tabs[2]:
            for ax in cardio["therapeutic_axes"]:
                st.markdown(f"• {ax}", unsafe_allow_html=False)
    
    elif domain == "Rare Disease":
        rare = data["domain_data"]
        tabs = st.tabs(["🧬 Mendelian", "🔴 Inheritance", "💊 Orphan"])
        with tabs[0]:
            sec("1", "Inheritance")
            for inh in rare["inheritance"]:
                st.markdown(f"• {inh}", unsafe_allow_html=False)
            
            sec("2", "Syndromes")
            for syn in rare["syndromes"]:
                st.markdown(f"**{syn['name']}** ({syn['count']})", unsafe_allow_html=False)
        
        with tabs[1]:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(kpi("De Novo", rare["de_novo_count"], "", "pink"), unsafe_allow_html=True)
            with col2:
                st.markdown(kpi("Penetrance", rare["estimated_penetrance"], "", "amber"), unsafe_allow_html=True)
            with col3:
                st.markdown(kpi("Orphan", "YES" if rare["orphan_drug_eligible"] else "NO", "", "lime" if rare["orphan_drug_eligible"] else ""), unsafe_allow_html=True)
        
        with tabs[2]:
            if data["pharma"]["drugs_by_phase"]:
                for ph, drugs in sorted(data["pharma"]["drugs_by_phase"].items(), reverse=True):
                    if drugs:
                        st.markdown(f"**{ph}**", unsafe_allow_html=False)
                        for d in drugs[:3]:
                            st.markdown(f"• {d['name']}", unsafe_allow_html=False)
            else:
                st.markdown("<p class='mono'>No approved therapies — gene therapy candidate.</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
