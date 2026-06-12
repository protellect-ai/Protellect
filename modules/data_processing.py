# modules/data_processing.py
from __future__ import annotations
import re, math
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import streamlit as st
from modules.config import AA_HYDRO, AA_CHG, SIG_SCORE, RANK_CLR, RANK_CSS
from modules.utils import ml_rank_fn, score_rank, parse_aa

# UniProt helpers
def g_gene(p):
    try: return p["genes"][0]["geneName"]["value"]
    except: return p.get("primaryAccession","?")

def g_name(p):
    try: return p["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except: return "Unknown protein"

def g_seq(p): 
    return p.get("sequence",{}).get("value","")

def _extract_inheritance(text):
    if not text: return ""
    t = text.lower()
    if "autosomal dominant" in t or "ad inheritance" in t: return "Autosomal Dominant (AD)"
    if "autosomal recessive" in t or "ar inheritance" in t: return "Autosomal Recessive (AR)"
    if "x-linked dominant" in t: return "X-linked Dominant"
    if "x-linked recessive" in t: return "X-linked Recessive"
    if "x-linked" in t: return "X-linked"
    if "y-linked" in t: return "Y-linked"
    if "mitochondrial" in t or "maternal" in t: return "Mitochondrial"
    if "dominant" in t: return "Autosomal Dominant (AD)"
    if "recessive" in t: return "Autosomal Recessive (AR)"
    if "somatic" in t: return "Somatic (acquired — not heritable)"
    if "de novo" in t: return "De novo (new mutation)"
    return ""

def _extract_mutation_type(text):
    if not text: return ""
    t = text.lower()
    if "missense" in t or "p." in t and ">" not in t: return "Missense (letter-swap mutation)"
    if "frameshift" in t or "frame shift" in t or "fs" in text: return "Frameshift (reading-frame shift)"
    if "nonsense" in t or "stop gained" in t or "ter" in t.lower(): return "Stop-gain (early termination)"
    if "splice" in t and "donor" in t: return "Splice-donor disruption"
    if "splice" in t and "acceptor" in t: return "Splice-acceptor disruption"
    if "splice" in t: return "Splice-site disruption"
    if "large deletion" in t or "exon deletion" in t: return "Large deletion"
    if "deletion" in t: return "Deletion"
    if "duplication" in t: return "Duplication"
    if "insertion" in t: return "Insertion"
    return ""

def g_diseases(p):
    out = []
    seen = set()
    
    for c in p.get("comments", []):
        if c.get("commentType") != "DISEASE": continue
        d = c.get("disease", {})
        name = d.get("diseaseId", d.get("diseaseAcronym",""))
        if not name or name in seen: continue
        seen.add(name)
        
        note = ""
        if c.get("note"):
            texts = c.get("note", {}).get("texts", [])
            note = texts[0].get("value", "") if texts else ""
        
        omim_id = ""
        xrefs_raw = d.get("diseaseCrossReferences") or d.get("diseaseCrossReference") or []
        if isinstance(xrefs_raw, dict): xrefs_raw = [xrefs_raw]
        for xref in xrefs_raw:
            if xref.get("database") == "MIM":
                omim_id = xref.get("id","")
                break
        
        desc = d.get("description","")
        inh_text = " ".join([note, desc, name])
        inheritance = _extract_inheritance(inh_text)
        
        mut_type = _extract_mutation_type(note)
        if not mut_type:
            mut_type = _extract_mutation_type(desc)
        
        out.append({
            "name": name,
            "desc": desc,
            "note": note,
            "omim": omim_id,
            "inheritance": inheritance,
            "mutation_type": mut_type,
        })
    
    for f in p.get("features", []):
        if f.get("type") in ("Natural variant", "VARIANT"):
            desc = f.get("description", "")
            if any(k in desc.lower() for k in ["disease", "cancer", "carcinoma", "syndrome", "disorder", "deficiency"]):
                loc = f.get("location", {})
                pos = loc.get("start", {}).get("value", "?")
                orig = f.get("alternativeSequence", {}).get("originalSequence", "")
                alts = f.get("alternativeSequence", {}).get("alternativeSequences", [])
                alt = alts[0] if alts else ""
                matches = re.findall(r"[Ii]n ([A-Z][^;.]+?)(?:;|\.|$)", desc)
                for m in matches[:2]:
                    m = m.strip()
                    if len(m) > 5 and m not in seen:
                        seen.add(m)
                        out.append({
                            "name": m,
                            "desc": f"Variant at position {pos}: {orig}→{alt or '?'}",
                            "note": desc[:200],
                            "omim": "",
                            "inheritance": _extract_inheritance(desc),
                            "mutation_type": f"p.{orig}{pos}{alt}" if orig and alt else desc[:40],
                        })
    return out[:20]

def g_sub(p):
    locs=[]
    for c in p.get("comments",[]):
        if c.get("commentType")=="SUBCELLULAR LOCATION":
            for e in c.get("subcellularLocations",[]):
                v=e.get("location",{}).get("value","")
                if v: locs.append(v)
    return list(dict.fromkeys(locs))

def g_tissue(p):
    for c in p.get("comments",[]):
        if c.get("commentType")=="TISSUE SPECIFICITY":
            t=c.get("texts",[])
            if t: return t[0].get("value","")
    return ""

def g_func(p):
    for c in p.get("comments",[]):
        if c.get("commentType")=="FUNCTION":
            t=c.get("texts",[])
            if t: return t[0].get("value","")
    return ""

def g_xref(p,db):
    for x in p.get("uniProtKBCrossReferences",[]):
        if x.get("database")==db: return x.get("id","")
    return ""

def g_gpcr(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    kws_str = " ".join(kws)
    fn = g_func(p).lower()
    is_structural = any(x in kws_str for x in ["filamin","actin-binding","cytoskeleton","scaffold protein","focal adhesion","sarcomere"])
    if is_structural: return False
    has_gpcr_kw = any(x in kws_str for x in ["gpcr","g protein-coupled receptor","7-transmembrane","rhodopsin","adrenergic receptor","muscarinic","serotonin receptor","dopamine receptor","chemokine receptor","opioid receptor"])
    has_gpcr_fn = any(x in fn for x in ["g protein-coupled","g-protein-coupled","seven-transmembrane","7-transmembrane receptor"])
    return has_gpcr_kw or has_gpcr_fn

def g_gpcr_class(p):
    kws=[k.get("value","") for k in p.get("keywords",[])]
    fn=g_func(p).lower()
    coupling=[]
    kws_str = " ".join(kws)
    if any(x in fn for x in [" gi ", "gi/o","inhibitory g","g(i)","gnai"]): coupling.append("Gi/o (↓ cAMP — inhibitory)")
    if any(x in fn for x in [" gs ","g(s)","stimulatory g","gnas","adenylyl cyclase activat"]): coupling.append("Gs (↑ cAMP — stimulatory)")
    if any(x in fn for x in ["gq","g(q)","phospholipase c","plc","ip3","diacylglycerol","gnaq"]): coupling.append("Gq/11 (↑ Ca²⁺ — calcium mobilisation)")
    if any(x in fn for x in ["g12","g13","rho guanine"]): coupling.append("G12/13 (Rho — cytoskeletal)")
    if not coupling:
        if "adrenergic" in kws_str: coupling.append("Gs/Gi (adrenergic — context-dependent)")
        elif "muscarinic" in kws_str: coupling.append("Gi/Gq (muscarinic — context-dependent)")
        elif "opioid" in kws_str: coupling.append("Gi/o (opioid — inhibitory)")
    return {"coupling": coupling or ["Coupling not determined in UniProt annotation"], "keywords": kws}

def g_ptype(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    kw=" ".join(kws); fn=g_func(p).lower()
    if any(x in kw for x in ["kinase","phosphotransferase"]): return "kinase"
    if any(x in kw for x in ["transcription factor","dna-binding","zinc finger","homeodomain"]): return "transcription_factor"
    if g_gpcr(p): return "gpcr"
    if any(x in kw for x in ["ion channel","voltage-gated","ligand-gated"]): return "ion_channel"
    if any(x in kw for x in ["receptor tyrosine","growth factor receptor","egfr","erbb"]): return "receptor_tyrosine_kinase"
    if any(x in kw for x in ["nuclear receptor","steroid","thyroid hormone receptor"]): return "nuclear_receptor"
    if any(x in kw for x in ["e3 ubiquitin","ubiquitin ligase","cullin"]): return "ubiquitin_system"
    if any(x in kw for x in ["structural","cytoskeletal","actin-binding","filamin","collagen","laminin"]): return "structural"
    if any(x in kw for x in ["chaperone","heat shock protein","hsp"]): return "chaperone"
    if any(x in kw for x in ["receptor"]): return "receptor"
    return "general"

def classify_entity(p):
    ptype = g_ptype(p)
    DRUG_CLASS = {
        "kinase": "ATP-competitive or allosteric kinase inhibitor",
        "gpcr":   "Biased agonist, antagonist, PAM, or NAM",
        "receptor_tyrosine_kinase": "Monoclonal antibody or small molecule TKI",
        "ion_channel": "Pore blocker or gating modifier",
        "nuclear_receptor": "Ligand (agonist/antagonist) or co-activator disruptor",
        "transcription_factor": "PPI inhibitor, PROTAC, or upstream kinase target",
        "structural": "Stabiliser, splice modulator — direct drugging very difficult",
        "enzyme": "Active site inhibitor or allosteric modulator",
        "ubiquitin_system": "PROTAC substrate ligand or E3 ligase inhibitor",
        "chaperone": "HSP90 co-chaperone client or allosteric modulator",
    }
    FIRST_ASSAY = {
        "kinase":  "ADP-Glo kinase activity assay — direct measure of catalytic function loss",
        "gpcr":    "cAMP HTRF (Gs/Gi) + beta-arrestin BRET — biased agonism screen",
        "receptor_tyrosine_kinase": "pY1068/pERK western blot — autophosphorylation readout",
        "ion_channel": "Whole-cell patch clamp or thallium flux assay",
        "nuclear_receptor": "GAL4-UAS luciferase reporter + LanthaScreen TR-FRET",
        "transcription_factor": "EMSA + ChIP-qPCR on known target gene promoter",
        "structural": "Negative-stain EM of mutant vs WT + hydrogen-deuterium exchange (HDX-MS)",
        "enzyme":  "Substrate conversion fluorescence assay — kinetic Km/Vmax",
        "ubiquitin_system": "In vitro ubiquitination cascade assay",
        "chaperone": "Refolding protection assay + client protein western",
    }
    return {
        "ptype": ptype,
        "drug_class": DRUG_CLASS.get(ptype, "Small molecule or biologic — assess tractability first"),
        "first_assay": FIRST_ASSAY.get(ptype, "Variant biochemical activity assay — compare WT vs P/LP variant"),
        "is_enzyme": ptype in ("kinase","enzyme","ubiquitin_system"),
        "is_receptor": ptype in ("gpcr","receptor","receptor_tyrosine_kinase","ion_channel","nuclear_receptor"),
        "is_druggable_class": ptype in ("kinase","gpcr","receptor_tyrosine_kinase","ion_channel","nuclear_receptor"),
    }

def classify_organism(pdata: dict) -> dict:
    org = pdata.get("organism",{})
    sci_name = org.get("scientificName","")
    common   = org.get("commonName","")
    tax_id   = org.get("taxonId",0)
    is_human = ("Homo sapiens" in sci_name) or (tax_id == 9606)
    return {
        "is_human": is_human,
        "scientific_name": sci_name,
        "common_name": common or sci_name,
        "tax_id": tax_id,
        "warning": "" if is_human else (
            f"⚠️ Non-human protein: {sci_name} ({common}). "
            f"ClinVar and disease data apply to human proteins only. "
            f"This protein may have a human orthologue — search by gene symbol instead."
        )
    }

def assess_gpcr_piggybacking(p, cv, gi_data):
    is_gpcr = g_gpcr(p)
    fn = g_func(p).lower()
    kws = [k.get("value","").lower() for k in p.get("keywords",[])]
    has_tm = any(x in kws for x in ["transmembrane","7-tm","seven-transmembrane","membrane"])
    n_path = gi_data.get("n_pathogenic", 0)
    n_total = gi_data.get("n_total", 0)
    
    kws_str = " ".join(kws)
    gene_name_lower = g_gene(p).lower()
    gpcr_associated = any(x in fn for x in [
        "arrestin","grk","gpcr","g protein","adenylyl cyclase","phosphodiesterase",
        "beta-arrestin","g-protein coupled","regulator of g-protein","rgs",
        "receptor kinase","scaffold protein","signal transduction"
    ]) or any(x in kws_str for x in [
        "arrestin","beta-arrestin","grk","gpcr","rgs protein"
    ]) or any(x in gene_name_lower for x in [
        "arrb","grk","rgs","ric8","gnas","gnai","gnaq","gnb","gng"
    ])
    
    variants_cv = cv.get("variants", [])
    germline_path = [
        v for v in variants_cv
        if v.get("score", 0) >= 4
        and not v.get("somatic", False)
        and "germline" in v.get("origin", "").lower()
        and v.get("condition", "Not specified") not in ("Not specified", "not provided", "")
        and not any(s in v.get("condition", "").lower() for s in ["not specified", "not provided", "somatic"])
    ]
    named_conditions = set()
    for v in germline_path:
        for c in v.get("condition", "").split(";"):
            c = c.strip()
            if c and len(c) > 5 and c.lower() not in ("not specified", "not provided"):
                if not (c.lower().startswith("cancer") or c.lower() == "neoplasm"):
                    named_conditions.add(c)
    n_germline_path = len(germline_path)
    n_named_conditions = len(named_conditions)

    known_piggyback_families = any(x in gene_name_lower for x in [
        "arrb", "grk", "rgs", "ric8", "gng", "gnb",
        "gnas", "gnai", "gnaq", "gnaz",
    ]) or any(x in fn for x in [
        "beta-arrestin", "g protein-coupled receptor kinase",
        "regulator of g-protein signaling",
    ])

    if is_gpcr and has_tm and n_germline_path >= 3 and n_named_conditions >= 2:
        return {
            "type": "DIRECT_GPCR",
            "label": "Direct GPCR — mutations independently cause named Mendelian diseases",
            "colour": "#ff2d55",
            "confidence": "HIGH",
            "reasoning": f"{g_gene(p)} is a bona fide GPCR with transmembrane domains and {n_germline_path} confirmed germline pathogenic variants linked to {n_named_conditions} named Mendelian conditions.",
            "investment": "PURSUE — genuine disease driver with strong human genetic evidence.",
        }
    elif is_gpcr and has_tm and n_path > 0 and not known_piggyback_families:
        return {
            "type": "DIRECT_GPCR",
            "label": "GPCR with pathogenic variants — likely direct disease driver",
            "colour": "#ff6b42",
            "confidence": "MEDIUM",
            "reasoning": f"{g_gene(p)} has GPCR transmembrane architecture and {n_path} pathogenic ClinVar entries.",
            "investment": "PROCEED with caution — confirm germline vs somatic status of pathogenic variants.",
        }
    elif gpcr_associated and (n_path == 0 or known_piggyback_families) and n_named_conditions < 2:
        return {
            "type": "PIGGYBACK",
            "label": "⚠️ PIGGYBACK PROTEIN — GPCR-associated but NOT an independent disease driver",
            "colour": "#ff8c42",
            "confidence": "HIGH",
            "reasoning": f"{g_gene(p)} is functionally associated with GPCR signalling but has only {n_germline_path} confirmed germline pathogenic variants with {n_named_conditions} named Mendelian condition(s).",
            "investment": "DEPRIORITISE as primary target. Study GPCR partners instead.",
        }
    else:
        return {
            "type": "NOT_GPCR",
            "label": "Not GPCR-associated",
            "colour": "#3a5a7a",
            "confidence": "HIGH",
            "reasoning": "No GPCR pathway association detected in UniProt annotation.",
            "investment": "N/A — evaluate on genomic integrity alone.",
        }

def compute_gi(cv, protein_length):
    variants=cv.get("variants",[]); total=len(variants)
    germline=[v for v in variants if not v.get("somatic",False)]
    pathogenic=[v for v in germline if v.get("score",0)>=4]
    vus=[v for v in germline if v.get("score",0)==2]
    benign=[v for v in germline if v.get("score",0)<=0]
    n_p=len(pathogenic); n_g=max(len(germline),1); length=max(protein_length or 1,1)
    density=n_p/n_g; per100=(n_p/length)*100
    if total<10:
        return dict(verdict="UNDERSTUDIED",label="Insufficient ClinVar data",css="gi-unknown",
                    color="#1e6080",icon="❓",pursue="neutral",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Too few ClinVar entries to draw conclusions.",pathogenic_list=pathogenic)
    elif n_p==0:
        return dict(verdict="NO DISEASE VARIANTS",label="Zero pathogenic / likely-pathogenic germline variants in ClinVar",
                    css="gi-redundant",color="#3a5a7a",icon="⚪",pursue="deprioritise",density=0,per100=0,
                    n_pathogenic=0,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation=f"Despite {total} ClinVar entries, not a single germline variant causes a Mendelian disease.",
                    pathogenic_list=[])
    elif density<0.01 and n_p<5:
        return dict(verdict="VERY LOW DISEASE BURDEN",label=f"Only {n_p} of {len(germline)} germline variants are disease-causing",
                    css="gi-redundant",color="#4a6a30",icon="🟡",pursue="caution",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Very low pathogenic density. Check if interaction partners carry the actual disease burden.",
                    pathogenic_list=pathogenic)
    elif per100>=1 or (n_p>=20 and density>=0.05):
        return dict(verdict="DISEASE-CRITICAL",label=f"{n_p} disease-causing variants · {per100:.1f} per 100 aa",
                    css="gi-critical",color="#ff2d55",icon="🔴",pursue="prioritise",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Strong genomic evidence. This protein is critical for human physiology.",
                    pathogenic_list=pathogenic)
    elif density>=0.05 or per100>=0.5:
        return dict(verdict="DISEASE-ASSOCIATED",label=f"{n_p} disease-causing variants ({density*100:.1f}% of total)",
                    css="gi-moderate",color="#ff8c42",icon="🟠",pursue="proceed",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Meaningful disease association. Focus on confirmed P/LP variants only.",
                    pathogenic_list=pathogenic)
    else:
        return dict(verdict="MODERATE",label=f"{n_p} disease-causing variants ({density*100:.1f}%)",
                    css="gi-moderate",color="#ffd60a",icon="🟡",pursue="selective",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Some association but low density. Do not extrapolate to nearby benign entries.",
                    pathogenic_list=pathogenic)

def ml_score_variants(variants, sens=50):
    out=[]
    for v in variants:
        name=v.get("variant_name","") or v.get("title","")
        orig,alt=parse_aa(name)
        hd=abs(AA_HYDRO.get(orig,0)-AA_HYDRO.get(alt,0))
        cd=abs(AA_CHG.get(orig,0)-AA_CHG.get(alt,0))
        stop=float(alt=="*"); frame=float("frame" in name.lower())
        stars={"practice guideline":1,"reviewed by expert panel":.9,
               "criteria provided, multiple submitters":.7,"criteria provided, single submitter":.5}.get(v.get("review","").lower(),.2)
        base=v.get("score",0)/5.0
        ml=min(1.0,base*.5+stop*.25+frame*.15+(hd/10)*.05+cd*.03+stars*.02)
        vc=dict(v); vc["ml"]=round(float(ml),3); vc["ml_rank"]=ml_rank_fn(ml, sens, v.get("score", None))
        vc["rank"]=score_rank(v.get("score",0),sens)
        out.append(vc)
    return sorted(out,key=lambda x:-x["ml"])

def detect_csv_type(df):
    cols = " ".join(c.lower() for c in df.columns)
    vals = " ".join(str(v) for v in df.iloc[0].values if v)[:200].lower() if len(df) > 0 else ""
    
    if any(k in cols for k in ["effect_score","fitness","dms","ddg","stability","enrich"]):
        return "dms"
    if ("mutation" in cols or "variant" in cols) and ("effect" in cols or "score" in cols or "fitness" in cols):
        return "dms"
    if re.search(r"[A-Z][0-9]+[A-Z*]", vals):
        return "dms"
    if any(k in cols for k in ["fold","logfc","log2","fpkm","rpkm","tpm","count","expr","deseq","edger"]): return "expression"
    if any(k in cols for k in ["chrom","chr","ref","alt","rsid","vcf","gnomad","af_","allele_freq"]): return "vcf_variants"
    if any(k in cols for k in ["accession","grch","protein change","protein_change","clinicalsignificance","clinical significance","condition","geneidsymbol","gene(s)","variationid"]): return "clinical_variants"
    if any(k in cols for k in ["variant","mutation","hgvs","clinvar","pathogen","classification"]): return "clinical_variants"
    if any(k in cols for k in ["protein","abundance","intensity","peptide","spectral","lfq","tmt"]): return "proteomics"
    if any(k in cols for k in ["pvalue","p_val","padj","fdr","qvalue","z_score","beta","odds_ratio"]): return "stats"
    if any(k in cols for k in ["cell","viability","ic50","ec50","apoptosis","proliferation","caspase"]): return "cell_assay"
    if any(k in cols for k in ["binding","kd","kon","koff","spr","itc","affinity","tm","shift"]): return "binding_assay"
    return "generic"

def analyse_csv_standalone(df, csv_type, goal, gene="", scored=None, variants=None, am_scores=None, protein_length=1):
    import re as _re2
    findings = []
    scored   = scored   or []
    variants = variants or []
    am_scores= am_scores or {}
    
    col_l   = {c: c.lower() for c in df.columns}
    pos_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["residue","position","pos","resi","aa_pos","site"])), None)
    mut_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["mutation","variant","change","substitution","hgvs","mut"])), None)
    eff_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["effect","score","fitness","ddg","stability","enrich",
                     "pathogenicity","functional","activity","log_ratio"])), None)
    fc_col  = next((c for c,l in col_l.items() if any(k in l for k in
                    ["fold","logfc","log2fc","log2_fold","lfc"])), None)
    p_col   = next((c for c,l in col_l.items() if any(k in l for k in
                    ["pvalue","p_val","padj","fdr","qvalue","p.value","p-value"])), None)
    gene_col= next((c for c,l in col_l.items() if any(k in l for k in
                    ["gene","symbol","name","geneid","gene_name","gene_id"])), None)
    
    findings.append(("📋 Dataset",
        f"**{csv_type.replace('_',' ').title()}** · {len(df):,} rows · {len(df.columns)} columns · "
        f"Columns: {', '.join(df.columns.tolist()[:8])}"))
    
    if csv_type == "dms":
        findings.append(("🔬 Assay type identified",
            "**Deep Mutational Scanning (DMS)** — measures the functional effect of every possible "
            "amino acid substitution in a protein. Effect score near 1.0 = highly deleterious."))
        
        mutations = []
        for _, row in df.iterrows():
            pos = None
            if pos_col and _re2.match(r"\d+", str(row.get(pos_col,""))):
                try: pos = int(float(str(row[pos_col]).split(".")[0]))
                except: pass
            mut_str = str(row.get(mut_col, "")) if mut_col else ""
            m = _re2.match(r"([A-Za-z*])([0-9]+)([A-Za-z*])", mut_str)
            if m:
                if pos is None: pos = int(m.group(2))
            eff = None
            if eff_col:
                try: eff = float(row[eff_col])
                except: pass
            mutations.append({"pos": pos, "mut_str": mut_str, "eff": eff})
        
        valid_muts = [m for m in mutations if m["pos"] is not None and m["eff"] is not None]
        
        if valid_muts:
            effs   = [m["eff"] for m in valid_muts]
            n_high = sum(1 for e in effs if e >= 0.7)
            n_med  = sum(1 for e in effs if 0.3 <= e < 0.7)
            n_low  = sum(1 for e in effs if e < 0.3)
            top5   = sorted(valid_muts, key=lambda x: -x["eff"])[:5]
            
            findings.append(("📊 Effect score distribution",
                f"**{n_high}** highly deleterious (≥0.7) · **{n_med}** moderate (0.3–0.7) · "
                f"**{n_low}** tolerated (<0.3) · Mean score: **{sum(effs)/len(effs):.3f}**"))
            
            top5_text = " · ".join(
                f"{m['mut_str']} ({m['eff']:.2f})" for m in top5
            )
            findings.append(("🔴 Most deleterious mutations", top5_text))
            
            findings.append(("🧪 Recommended next experiments",
                f"**1. Validate top {min(5,n_high)} deleterious mutations biochemically** — "
                f"Express {', '.join(m['mut_str'] for m in top5[:3])} as recombinant protein. "
                f"**2. Cross-reference with ClinVar** — submit high-effect positions to ClinVar search. "
                f"**3. Structure-guided targeting** — map deleterious hotspot positions onto AlphaFold structure."))
    
    elif csv_type == "expression":
        if fc_col and df[fc_col].dtype in [float, 'float64', int, 'int64']:
            up   = (df[fc_col] > 1).sum()
            dn   = (df[fc_col] < -1).sum()
            neut = len(df) - up - dn
            findings.append(("📈 Differential expression",
                f"**{up:,}** upregulated (log₂FC > 1) · **{dn:,}** downregulated (log₂FC < −1) · "
                f"**{neut:,}** unchanged · Mean |FC|: {df[fc_col].abs().mean():.2f}"))
        if p_col and df[p_col].dtype in [float, 'float64']:
            sig = (df[p_col] < 0.05).sum()
            sig01 = (df[p_col] < 0.01).sum()
            findings.append(("📊 Statistical significance",
                f"**{sig:,}** significant at p < 0.05 · **{sig01:,}** at p < 0.01 out of {len(df):,} total."))
        findings.append(("🧪 Recommended next experiments",
            "**1. Pathway enrichment** — run GSEA or ORA on significantly changed genes. "
            "**2. ClinVar intersection** — which significantly changed genes also carry ClinVar pathogenic variants? "
            "**3. Validation** — qPCR validate top 5–10 hits in independent samples."))
    
    elif csv_type in ("clinical_variants", "vcf_variants"):
        import re as _re3
        sig_col2    = next((c for c in df.columns if any(k in c.lower() for k in
                           ["significance","classification","clinical sig","clinsig","pathogen"])), None)
        gene_col2   = next((c for c in df.columns if c.lower() in
                           ["gene(s)","gene","genes","gene_symbol","symbol"]), None)
        cond_col    = next((c for c in df.columns if any(k in c.lower() for k in
                           ["condition","disease","phenotype","trait"])), None)
        
        PATH_KEYS  = ["pathogenic","likely pathogenic","pathogenic/likely pathogenic"]
        VUS_KEYS   = ["uncertain significance","conflicting","vus"]
        BENIGN_KEYS= ["benign","likely benign","benign/likely benign"]

        def classify_sig(s):
            s = str(s).lower().strip()
            if any(k in s for k in PATH_KEYS):  return "Pathogenic/LP"
            if any(k in s for k in VUS_KEYS):    return "VUS"
            if any(k in s for k in BENIGN_KEYS): return "Benign/LB"
            return "Other"

        if sig_col2:
            df["_sig_class"] = df[sig_col2].apply(classify_sig)
            n_path  = (df["_sig_class"]=="Pathogenic/LP").sum()
            n_vus   = (df["_sig_class"]=="VUS").sum()
            n_ben   = (df["_sig_class"]=="Benign/LB").sum()
            findings.append(("📊 Classification breakdown",
                f"**{n_path:,}** disease-causing (Pathogenic/LP) · **{n_vus:,}** unknown significance (VUS) · "
                f"**{n_ben:,}** harmless (Benign/LB) · **{len(df):,}** total."))

        if gene_col2 and gene:
            matches = df[df[gene_col2].astype(str).str.upper().str.contains(gene.upper(),na=False)]
            if not matches.empty:
                findings.append((f"✅ {gene} found in this dataset",
                    f"**{gene}** appears in this dataset. Cross-reference these variants with the triage table above."))
        
        findings.append(("🧪 Experimental triage",
            f"**Step 1:** Import this file into Protellect's protein search for each top gene. "
            f"**Step 2:** Cross-reference P/LP variants with AlphaMissense scores. "
            f"**Step 3:** Biochemical activity assay on recombinant WT vs top 5 P/LP variants. "
            f"**Step 4:** CRISPR knock-in of top 3 variants for gold-standard functional evidence."))
    
    return findings

def compute_hotspot_clusters(variants: list, protein_length: int) -> list:
    if not variants or not protein_length: return []
    path_vars = []
    for v in variants:
        if v.get("score",0) >= 3:
            try: path_vars.append(int(v.get("start",0)))
            except: pass
    if not path_vars: return []
    path_vars.sort()
    global_density = len(path_vars) / max(protein_length, 1)
    window, step = 20, 5
    clusters = []
    i = 0
    while i < protein_length - window:
        in_window = [p for p in path_vars if i <= p < i+window]
        local_density = len(in_window) / window
        if local_density >= max(3, global_density * 4) and in_window:
            if clusters and clusters[-1]["end"] >= i:
                clusters[-1]["end"] = i + window
                clusters[-1]["count"] += len(in_window)
                clusters[-1]["positions"].extend(in_window)
            else:
                clusters.append({
                    "start": i, "end": i+window,
                    "count": len(in_window),
                    "positions": in_window,
                    "fold_enrichment": round(local_density / max(global_density, 0.001), 1),
                })
        i += step
    for c in clusters:
        c["positions"] = sorted(set(c["positions"]))
        c["count"] = len(c["positions"])
    return sorted(clusters, key=lambda x: -x["fold_enrichment"])

def compute_experiment_roi(scored: list, gi: dict, ptype: str, gnomad: dict, ot_data: dict) -> list:
    n_path = gi.get("n_pathogenic", 0)
    pli = gnomad.get("pLI", 0.5) if gnomad else 0.5
    n_drugs_known = len(ot_data.get("known_drugs",[])) if ot_data else 0
    tractability = ot_data.get("tractability",{}) if ot_data else {}
    is_small_mol_tractable = bool(tractability.get("Small molecule"))
    n_crit = sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")

    experiments = [
        {
            "name": "AlphaMissense + gnomAD in silico triage (ALL variants)",
            "category": "Computational",
            "cost_usd": 0, "time_weeks": 0.5,
            "p_success": 0.85,
            "value_score": min(10, n_crit * 2 + 3),
            "rationale": f"Zero cost. Eliminates ~50% of candidates before wet lab. {n_crit} CRITICAL variants to rank.",
            "do_first": True,
        },
        {
            "name": "AlphaMissense pathogenicity score review",
            "category": "Computational",
            "cost_usd": 0, "time_weeks": 0.1,
            "p_success": 0.95,
            "value_score": 8,
            "rationale": "AI-predicted pathogenicity for every substitution. Cross-reference with ClinVar to find understudied high-risk variants.",
            "do_first": True,
        },
        {
            "name": "Differential Scanning Fluorimetry (DSF/nanoDSF)",
            "category": "Biochemical",
            "cost_usd": 2000, "time_weeks": 2,
            "p_success": 0.7,
            "value_score": 7 if n_path > 0 else 4,
            "rationale": f"Low cost, fast. Confirms whether pathogenic missense variants destabilise the fold. n_pathogenic={n_path}.",
            "do_first": n_path > 3,
        },
        {
            "name": "Cell viability + apoptosis panel",
            "category": "Cell-based",
            "cost_usd": 3000, "time_weeks": 2,
            "p_success": 0.65,
            "value_score": 6 if n_crit > 0 else 3,
            "rationale": f"Quick phenotypic readout. {n_crit} CRITICAL variants to test in isogenic lines.",
            "do_first": n_crit > 0,
        },
        {
            "name": "CRISPR knock-in (top 3 CRITICAL variants)",
            "category": "Genetic",
            "cost_usd": 25000, "time_weeks": 10,
            "p_success": 0.7 if pli > 0.8 else 0.4,
            "value_score": 10 if n_crit > 0 else 2,
            "rationale": f"Gold standard. pLI={pli:.2f}. Only do after computational + cell viability confirm.",
            "do_first": False,
        },
        {
            "name": "Co-IP + mass spectrometry (interaction network)",
            "category": "Biochemical",
            "cost_usd": 15000, "time_weeks": 6,
            "p_success": 0.75,
            "value_score": 7,
            "rationale": "Identifies which binding partners are lost per mutation. Feeds into drug design.",
            "do_first": False,
        },
        {
            "name": "Small molecule screen (HTS)",
            "category": "Drug discovery",
            "cost_usd": 150000, "time_weeks": 26,
            "p_success": 0.3 if is_small_mol_tractable else 0.1,
            "value_score": 10 if is_small_mol_tractable else 4,
            "rationale": f"Small molecule tractability: {'YES (OpenTargets)' if is_small_mol_tractable else 'LOW'}. {n_drugs_known} existing drugs known.",
            "do_first": False,
        },
        {
            "name": "Antibody development",
            "category": "Drug discovery",
            "cost_usd": 300000, "time_weeks": 52,
            "p_success": 0.4 if False else 0.15,
            "value_score": 9 if False else 3,
            "rationale": "Requires extracellular epitope. Only justified post-Phase I target validation.",
            "do_first": False,
        },
    ]

    import math
    for e in experiments:
        cost_factor  = math.log(e["cost_usd"] + 1) + 0.1
        time_factor  = math.log(e["time_weeks"] * 7 + 1) + 0.1
        e["roi"] = round((e["p_success"] * e["value_score"]) / (cost_factor * time_factor / 10), 2)
        e["roi_label"] = "🟢 Excellent" if e["roi"] > 5 else "🟡 Good" if e["roi"] > 2 else "🟠 Fair" if e["roi"] > 1 else "🔴 Low"

    return sorted(experiments, key=lambda x: -x["roi"])

def estimate_patient_population(diseases: list, cv: dict, gi: dict) -> dict:
    PREVALENCE_DB = {
        "cardiomyopathy": 200, "dilated cardiomyopathy": 40, "hypertrophic cardiomyopathy": 200,
        "breast cancer": 1600, "colorectal cancer": 450, "lung cancer": 700,
        "glanzmann": 0.1, "thrombasthenia": 0.1, "haemophilia": 10,
        "cystic fibrosis": 3, "sickle cell": 30, "thalassemia": 45,
        "parkinson": 160, "alzheimer": 600, "huntington": 5,
        "autism": 700, "intellectual disability": 3000, "epilepsy": 600,
        "leukemia": 130, "lymphoma": 220, "glioma": 30,
    }
    total_prevalence = 0
    matched_diseases = []
    for d in diseases[:8]:
        name_l = d.get("name","").lower()
        for key, prev in PREVALENCE_DB.items():
            if key in name_l:
                total_prevalence += prev
                matched_diseases.append({"disease": d.get("name",""), "prevalence_per_100k": prev})
                break
    world_pop = 8_000_000_000
    if total_prevalence > 0:
        estimated_patients = int((total_prevalence / 100_000) * world_pop)
    else:
        estimated_patients = 0
    n_path = gi.get("n_pathogenic", 0)
    n_total = gi.get("n_total", 1)
    genetic_fraction = min(1.0, n_path / max(n_total, 1) * 3)
    genetically_targetable = int(estimated_patients * genetic_fraction)
    return {
        "estimated_global_patients": estimated_patients,
        "genetically_targetable": genetically_targetable,
        "matched_diseases": matched_diseases,
        "rare_disease": total_prevalence < 50,
        "orphan_eligible": total_prevalence < 5,
        "market_note": (
            "Orphan drug designation eligible (<5/100,000) — significant regulatory incentives." if total_prevalence > 0 and total_prevalence < 5 else
            "Rare disease — potential for breakthrough therapy designation." if total_prevalence < 50 else
            "Common disease — large market, higher regulatory bar."
        ) if total_prevalence > 0 else "Insufficient prevalence data to estimate market size.",
    }

def find_drugged_analogs(pdata: dict, string_data: list, ot_data: dict) -> list:
    analogs = []
    for partner in string_data[:5]:
        gene = partner.get("partner","")
        if gene:
            analogs.append({
                "protein": gene,
                "relationship": "Interaction partner (STRING)",
                "score": partner.get("score",0),
                "implication": f"If {gene} is druggable, its interaction with the target protein may allow indirect targeting.",
            })
    for da in (ot_data.get("disease_associations",[]) if ot_data else [])[:3]:
        analogs.append({
            "protein": da.get("disease",""),
            "relationship": "Shared disease association (OpenTargets)",
            "score": int(da.get("score",0)*1000),
            "implication": "Other proteins in this disease module may serve as proxy targets with established drug precedent.",
        })
    return analogs

def regulatory_pathway_map(diseases: list, patient_data: dict, gi: dict) -> dict:
    is_rare = patient_data.get("rare_disease", False)
    is_orphan = patient_data.get("orphan_eligible", False)
    n_path = gi.get("n_pathogenic", 0)
    has_strong_genetics = gi.get("pursue") in ("prioritise","proceed")
    paths = {}
    if is_orphan:
        paths["Orphan Drug Designation"] = {
            "eligible": True, "timeline": "~90 days for FDA decision",
            "benefits": "7-year market exclusivity · 50% tax credit on clinical trials · waived FDA fees",
            "url": "https://www.fda.gov/patients/rare-diseases-fda/orphan-drug-designation",
            "action": "File ODD application with FDA. Can be done preclinically.",
        }
    if has_strong_genetics and n_path > 10:
        paths["Breakthrough Therapy Designation"] = {
            "eligible": True, "timeline": "~60 days for FDA decision",
            "benefits": "Intensive FDA guidance · rolling review · organisational commitment from FDA",
            "url": "https://www.fda.gov/patients/fast-track-breakthrough-therapy-accelerated-approval-priority-review/breakthrough-therapy",
            "action": "Requires preliminary clinical evidence of substantial improvement. Target Phase 2.",
        }
    if is_rare:
        paths["Fast Track Designation"] = {
            "eligible": True, "timeline": "~60 days",
            "benefits": "More frequent FDA meetings · rolling review",
            "url": "https://www.fda.gov/patients/fast-track-breakthrough-therapy-accelerated-approval-priority-review/fast-track",
            "action": "File early, ideally at IND stage.",
        }
    if not paths:
        paths["Standard Review"] = {
            "eligible": True, "timeline": "~12 months post-NDA/BLA",
            "benefits": "Standard pathway. No special designations unless disease criteria met.",
            "url": "https://www.fda.gov",
            "action": "Focus on robust Phase 3 design with clear primary endpoint.",
        }
    return paths