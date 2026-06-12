# modules/utils.py
from __future__ import annotations
import streamlit as st
from modules.config import RANK_CSS, RANK_CLR, PLAIN

def p(term): 
    return PLAIN.get(term, term)

def badge(rank): 
    return f"<span class='badge {RANK_CSS.get(rank,'bN')}'>{rank}</span>"

def sh(icon, title): 
    st.markdown(f"<div class='sh2'><span style='font-size:1.1rem'>{icon}</span><h3>{title}</h3></div>", unsafe_allow_html=True)

def mc(val, label, clr="#00e5ff", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"

def src_link(label, url): 
    return f"<a class='src-badge' style='color:#6ab8d0;' href='{url}' target='_blank'>↗ {label}</a>"

def clean_sig(raw):
    """Normalise raw ClinVar significance string."""
    from modules.config import SIG_LABEL
    s = str(raw).strip()
    return SIG_LABEL.get(s.lower(), s.title() if len(s) > 2 else "Not Classified")

def score_rank(s, sens=50):
    shift=(sens-50)/100
    if s>=5: return "CRITICAL"
    if s>=4-shift: return "HIGH"
    if s>=2-shift: return "MEDIUM"
    return "NEUTRAL"

def ml_rank_fn(ml, sens=50, clinvar_score=None):
    """
    Rank variant by ML score, BUT cap rank based on ClinVar evidence.
    A VUS can never be CRITICAL. A benign variant is always NEUTRAL.
    ML scores alone cannot override clinical genetic classification.
    """
    shift = (sens - 50) / 200
    raw_rank = ("CRITICAL" if ml >= .85 - shift else
                "HIGH"     if ml >= .65 - shift else
                "MEDIUM"   if ml >= .40 - shift else "NEUTRAL")

    if clinvar_score is None:
        return raw_rank

    if clinvar_score >= 4:
        return raw_rank
    elif clinvar_score == 3:
        return "HIGH" if raw_rank == "CRITICAL" else raw_rank
    elif clinvar_score == 2:
        return "MEDIUM" if raw_rank in ("CRITICAL", "HIGH") else raw_rank
    elif clinvar_score == 1:
        return "NEUTRAL"
    else:
        return "NEUTRAL"

def parse_aa(name):
    aa3={"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
         "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
         "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m=re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)",name or "")
    return (aa3.get(m.group(1),"?"),aa3.get(m.group(2),"?")) if m else ("?","?")

def render_citations(papers, n=4):
    if not papers: return
    st.markdown("<div style='color:#5a8090;font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;margin:.7rem 0 .3rem;'>📚 Supporting Literature <span style=\"color:#0a1828;font-size:.6rem;\">(click to open on PubMed)</span></div>", unsafe_allow_html=True)
    for p2 in papers[:n]:
        pt=" ".join(f"<span style='background:#07152a;color:#1a4060;font-size:.64rem;padding:1px 5px;border-radius:6px;margin-left:3px;'>{t.title()}</span>" for t in p2.get("pt",[])[:2])
        st.markdown(f"<div class='cite'><a href='{p2['url']}' target='_blank'>{p2['title'][:110]}</a>{pt}<div class='cm' style='color:#4a7090;'>{p2['authors']} · {p2['journal']} · {p2['year']} · PMID {p2['pmid']}</div></div>", unsafe_allow_html=True)

def classify_experiment_type(abstract: str, title: str) -> str:
    """Classify what type of experiment was done based on paper abstract."""
    text = (title + " " + abstract).lower()
    if any(k in text for k in ["cryo-em","crystal structure","x-ray","nmr structure","alphafold","structural"]): return "🏗️ Structural"
    if any(k in text for k in ["crispr","knockout","knock-in","knockdown","sirna","shrna"]): return "🔬 CRISPR/Genetic"
    if any(k in text for k in ["mouse","rat","zebrafish","in vivo","xenograft","animal model"]): return "🐭 In Vivo"
    if any(k in text for k in ["clinical trial","patient","cohort","clinical study","human subject"]): return "👥 Clinical"
    if any(k in text for k in ["binding","affinity","kinetics","spr","biacore","itc","pull-down","co-ip"]): return "🔗 Binding/Interaction"
    if any(k in text for k in ["phosphorylation","kinase activity","enzyme","substrate","biochemical"]): return "⚗️ Biochemical"
    if any(k in text for k in ["western blot","immunofluorescence","flow cytometry","facs","cell viability","proliferation"]): return "🧫 Cell-Based"
    if any(k in text for k in ["whole genome","sequencing","gwas","variant","mutation","polymorphism"]): return "🧬 Genomics"
    if any(k in text for k in ["drug","inhibitor","compound","therapeutic","treatment","clinical"]): return "💊 Drug/Therapeutic"
    return "📄 Other"
