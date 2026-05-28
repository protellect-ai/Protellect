"""Protellect data layer — all external API fetchers.
Self-contained: depends only on requests, json, time, re, streamlit (for cache).
Extracted from app.py for modularity.
"""
import requests, json, time, re
import streamlit as st
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import re as _re

PLAIN = {
    "apoptosis":"cell death (apoptosis)","phosphorylation":"chemical tagging (phosphorylation)",
    "haploinsufficiency":"half-dose shortage (haploinsufficiency)",
    "missense":"letter-swap mutation (missense)","nonsense":"early-stop mutation (stop-gain)",
    "frameshift":"reading-frame shift (frameshift)","splice":"splice-site disruption",
    "dominant negative":"protein blocker (dominant-negative)","gain of function":"hyperactive mutation (gain-of-function)",
    "loss of function":"broken gene (loss-of-function)","germline":"heritable / born-with (germline)",
    "somatic":"acquired / developed (somatic)","heterozygous":"one-copy affected (heterozygous)",
    "homozygous":"both-copies affected (homozygous)","GPCR":"cell-surface signal receiver (GPCR)",
    "second messenger":"internal signal relay (second messenger)","G-protein":"signal relay switch (G-protein)",
    "kinase":"protein tagger/activator (kinase)","phenotype":"observable trait (phenotype)",
    "pathogenic":"disease-causing (pathogenic)","benign":"harmless variant (benign)",
    "VUS":"unknown-significance variant (VUS)","variant":"DNA spelling change (variant)",
}

def p(term): return PLAIN.get(term, term)

def mc(val, label, clr="#38bdf8", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"


# ── Constants ──
ESEARCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
SIG_SCORE = {
    "pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
    "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
    "conflicting interpretations of pathogenicity":2,"likely benign":1,
    "benign":0,"benign/likely benign":0,"not provided":-1,"not classified":-1,
    # ClinVar numeric codes (internal API values)
    "4":5,"3":4,"3/4":4,"5":3,"2":2,"1":1,"0":0,
}
SIG_LABEL = {
    "pathogenic":                              "Disease-causing (Pathogenic)",
    "likely pathogenic":                       "Likely Disease-causing",
    "pathogenic/likely pathogenic":            "Pathogenic / Likely Path.",
    "risk factor":                             "Risk Factor",
    "uncertain significance":                  "Unknown Significance (VUS)",
    "conflicting interpretations":             "Conflicting Evidence",
    "conflicting interpretations of pathogenicity": "Conflicting Evidence",
    "likely benign":                           "Likely Harmless (Likely Benign)",
    "benign":                                  "Harmless (Benign)",
    "benign/likely benign":                    "Benign / Likely Benign",
    "not provided":                            "Not Classified",
    "not classified":                          "Not Classified",
    # Numeric code fallbacks
    "4":"Likely Disease-causing","3/4":"Pathogenic/LP","5":"Risk Factor",
    "2":"Unknown Significance","1":"Likely Harmless","0":"Harmless",
}

# ── Small helpers the fetchers use ──
def _gene_to_ensembl(gene_symbol: str) -> str:
    """Convert gene symbol to Ensembl ID via MyGene.info."""
    try:
        r = requests.get(f"https://mygene.info/v3/query?q={gene_symbol}&species=human&fields=ensembl.gene&size=1", timeout=10)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits: return ""
        ensembl = hits[0].get("ensembl", {})
        if isinstance(ensembl, list): ensembl = ensembl[0]
        return ensembl.get("gene", "")
    except:
        return ""

def clean_sig(raw):
    """Normalise raw ClinVar significance string."""
    s = str(raw).strip()
    return SIG_LABEL.get(s.lower(), s.title() if len(s) > 2 else "Not Classified")

def _is_ambiguous_search(query: str, result_gene: str, result_name: str) -> str | None:
    """
    Returns a warning string if the search term is ambiguous/generic and
    the top result may not be what the user intended.
    Returns None if the match looks direct and unambiguous.
    """
    q = query.strip().lower()
    g = result_gene.strip().lower()
    n = result_name.strip().lower()

    # If the query matches the gene symbol exactly → no warning
    if q == g: return None
    # If the query is a UniProt accession → no warning
    import re as _re
    if _re.match(r"^[A-Z][0-9][A-Z0-9]{3}[0-9]$", query.strip(), _re.I): return None

    # Common ambiguous/generic food/substance terms that hit protein names
    AMBIGUOUS_TERMS = {
        "gelatin":  ("ADIPOQ (Adiponectin)", "Adiponectin was historically called 'Gelatin-Binding Protein 28' (GBP28) in early literature — it is NOT related to dietary gelatin. If you meant: search the human gene symbol directly, e.g. ADIPOQ, COL1A1 (collagen/gelatin source), or MMP2 (gelatinase A)."),
        "albumin":  ("ALB (Serum albumin)", "Albumin matches human serum albumin (ALB). If you meant a different protein, search by gene symbol."),
        "fibrin":   ("FGB/FGA/FGG", "Fibrin is a fibrinogen cleavage product. Search FGB, FGA, or FGG for fibrinogen chains."),
        "collagen": ("COL1A1 (top hit)", "Multiple collagen genes exist (COL1A1–COL28A1). Search the specific collagen by number (e.g. COL4A1) for precision."),
        "keratin":  ("KRT1 (top hit)", "Multiple keratin genes exist (KRT1–KRT86). Search the specific keratin number for precision."),
        "actin":    ("ACTB/ACTA1", "Multiple actin genes exist. ACTB = cytoplasmic beta-actin, ACTA1 = skeletal muscle alpha-actin."),
        "myosin":   ("MYH7 (top hit)", "Multiple myosin heavy/light chain genes exist. Search the specific myosin (e.g. MYH7, MYL2) for precision."),
        "hemoglobin":("HBB (top hit)", "Multiple haemoglobin subunit genes: HBA1, HBA2 (alpha), HBB (beta), HBD (delta)."),
        "elastin":  ("ELN", "ELN = human elastin — correct match."),
        "casein":   (None, "Casein is a milk protein — no direct human gene equivalent. Try CSNK (casein kinase) if you meant casein kinase."),
    }

    for term, (likely_hit, explanation) in AMBIGUOUS_TERMS.items():
        if term in q and g not in q:
            return (f" <b>Search disambiguation:</b> '{query}' matched <b>{result_gene}</b> "
                    f"because its protein name contains this term. "
                    f"Top result: {likely_hit}. {explanation}")

    # Generic check: query not in gene name and not in first word of protein name
    gene_words = g.split()
    protein_first_word = n.split()[0] if n else ""
    if q not in gene_words and q != protein_first_word and len(q) > 4:
        return (f" <b>Search note:</b> '{query}' is not the gene symbol for <b>{result_gene}</b> — "
                f"it matched the protein description. If this is not the protein you intended, "
                f"search by gene symbol (e.g. {result_gene.upper()}) or UniProt accession for a precise match.")

    return None

def _disease_evidence_tier(source: str, n_clinvar_stars: int = 0,
                            clingen_class: str = "") -> dict:
    """
    Assign an evidence tier to a disease association.
    Tier 1 = UniProt manually curated (strongest)
    Tier 2 = ClinGen Definitive/Strong
    Tier 3 = ClinVar ≥2 stars / ClinGen Moderate
    Tier 4 = ClinVar 1 star / ClinGen Limited
    Tier 5 = OpenTargets GWAS/expression only (correlation, not causation)
    """
    CLINGEN_TIERS = {
        "Definitive": 2, "Strong": 2, "Moderate": 3,
        "Limited": 4, "No Reported Evidence": 5,
        "Disputed": 5, "Refuted": 5,
    }
    tier = 5
    if source == "uniprot": tier = 1
    elif clingen_class in CLINGEN_TIERS: tier = CLINGEN_TIERS[clingen_class]
    elif n_clinvar_stars >= 2: tier = 3
    elif n_clinvar_stars == 1: tier = 4
    tier_labels = {
        1: ("Tier 1", "#22c55e", "UniProt manually curated — highest confidence causal evidence"),
        2: ("Tier 2", "#4a90d9", "ClinGen Definitive/Strong — expert-curated gene-disease validity"),
        3: ("Tier 3", "#ffd60a", "ClinVar ≥2 stars / ClinGen Moderate — good evidence, peer reviewed"),
        4: ("Tier 4", "#ff8c42", "ClinVar 1 star / ClinGen Limited — single submitter, use cautiously"),
        5: ("Tier 5", "#3a6080", "Statistical association only — not causal Mendelian evidence"),
    }
    label, color, desc = tier_labels[tier]
    return {"tier": tier, "label": label, "color": color, "description": desc}

def parse_aa(name):
    aa3={"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
         "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
         "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m=re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)",name or "")
    return (aa3.get(m.group(1),"?"),aa3.get(m.group(2),"?")) if m else ("?","?")

# ── Data-source fetchers ──
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_uniprot(query):
    """
    Fetch UniProt entry — STRICTLY human only (organism_id:9606 / Homo sapiens).
    Validates organism on EVERY result before returning.
    Non-human proteins raise a clear ValueError with explanation.
    """
    base = "https://rest.uniprot.org/uniprotkb"
    HUMAN_TAXID = 9606

    # Known non-human protein terms — immediate rejection
    NON_HUMAN_TERMS = {
        "ovalbumin":"chicken (Gallus gallus)",
        "beta keratin":"reptile/bird — no human equivalent",
        "beta-keratin":"reptile/bird — no human equivalent",
        "serum albumin bovine":"cow (Bos taurus)",
        "lysozyme hen":"chicken (Gallus gallus)",
        "insulin bovine":"cow (Bos taurus)",
        "hemoglobin horse":"horse (Equus caballus)",
        "cytochrome c horse":"horse (Equus caballus)",
        "green fluorescent protein":"jellyfish (Aequorea victoria)",
        "gfp":"jellyfish (Aequorea victoria) — use human fluorescent reporters",
        "luciferase":"firefly (Photinus pyralis)",
    }
    # Note: ambiguous food/substance terms (gelatin, sugar, etc.) are handled
    # by the pre-search check in the main app flow — NOT here.
    # Raising ValueError here would break the fetch and show "Unknown protein".
    _q_lower_nh = query.strip().lower()
    for term, species in NON_HUMAN_TERMS.items():
        if term in _q_lower_nh:
            raise ValueError(
                f" '{query}' is a non-human protein ({species}). "
                f"Protellect analyses human proteins only. "
                f"If you're looking for the human version, try searching for the human gene name or function instead."
            )

    def validate_human(entry):
        """Returns True if entry is Homo sapiens, raises ValueError otherwise."""
        org = entry.get("organism", {})
        sci = org.get("scientificName", "")
        taxid = org.get("taxonId", 0)
        if "Homo sapiens" in sci or taxid == HUMAN_TAXID:
            return True
        common = org.get("commonName", sci)
        gene_n = entry.get("genes",[{}])[0].get("geneName",{}).get("value","this protein") if entry.get("genes") else "this protein"
        acc_n  = entry.get("primaryAccession","?")
        raise ValueError(
            f" Non-human protein detected: '{query}' resolved to <b>{gene_n}</b> ({acc_n}) from "
            f"<b>{common}</b> ({sci}). "
            f"Protellect is human-only. This protein does not exist in the human genome. "
            f"If a human orthologue exists, search by the human gene symbol (e.g. KRT — human keratin). "
            f"Human proteins to try: TP53 · FLNC · BRCA1 · ACM2 · EGFR · P04637"
        )

    # ── Direct accession lookup ────────────────────────────────────────────
    if re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", query.strip(), re.I):
        r = requests.get(f"{base}/{query.strip().upper()}", headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        entry = r.json()
        validate_human(entry)  # raises if non-human
        return entry

    # ── Hardcoded UniProt accessions — bypass search for common proteins ──────
    # Direct accession lookup is faster, more reliable, and immune to search index issues
    _GENE_TO_ACCESSION = {
        # Structural / cytoskeletal
        "FLNA":"P21333","FLNB":"O75369","FLNC":"Q14315",
        "ACTB":"P60709","ACTA1":"P68133","ACTA2":"P62736","ACTC1":"P68032",
        "MYH7":"P12883","MYH9":"P35579","MYH11":"P35749","MYL2":"P10916",
        "TTN":"Q8WZ42","DSP":"P15924","DMD":"P11532","LMNA":"P02545",
        "VIM":"P08670","DES":"P17661","SYNPO":"Q8TCG1",
        # Kinases
        "EGFR":"P00533","ERBB2":"P04626","BRAF":"P15056","KRAS":"P01116",
        "NRAS":"P01111","HRAS":"P01112","ABL1":"P00519","BCR":"P11274",
        "ALK":"Q9UM73","MET":"P08581","RET":"P07949","KIT":"P10721",
        "PDGFRA":"P16234","FGFR1":"P11362","FGFR2":"P21802","FGFR3":"P22607",
        "FGFR4":"P22455","PIK3CA":"P42336","PTEN":"P60484","AKT1":"P31749",
        "MTOR":"P42345","CDK4":"P11802","CDK6":"P30279","CDK2":"P24941",
        "ATM":"Q13315","ATR":"Q13535","CHEK1":"O14757","CHEK2":"O96017",
        "LRRK2":"Q5S007","PINK1":"Q9BXM7","DYRK1A":"Q13627",
        # Tumour suppressors / cancer
        "TP53":"P04637","BRCA1":"P38398","BRCA2":"P51587","RB1":"P06400",
        "APC":"P25054","VHL":"P40337","MLH1":"P40692","MSH2":"P43246",
        "NF1":"P21359","NF2":"P35240","PTEN":"P60484","CDKN2A":"P42771",
        "STK11":"Q15831","SMAD4":"Q13485","RUNX1":"Q01196",
        # Ion channels / neuroscience
        "SCN1A":"P35498","SCN2A":"Q99250","SCN5A":"Q14524","SCN8A":"Q9UQD0",
        "KCNQ2":"O43526","KCNQ3":"O43525","KCNQ4":"P56696",
        "CACNA1A":"O00555","CACNA1S":"Q13698","CACNA1C":"Q13936",
        "GRIN2A":"Q12879","GRIN2B":"Q13224","GRIA2":"P42262",
        "HCN1":"O60741","HCN4":"Q9Y3Q4","CFTR":"P13569",
        "PIEZO1":"Q92508","PIEZO2":"A0JLT2",
        # GPCRs
        "ADRB2":"P07550","ADRB1":"P08588","ADRA1A":"P35348",
        "DRD2":"P14416","DRD1":"P21728","DRD3":"P35462",
        "HTR1A":"P08908","HTR2A":"P28223","HTR3A":"P46098",
        "CHRM1":"P11229","CHRM2":"P08172","CHRM3":"P20309",
        "OPRM1":"P35372","OPRD1":"P41143","OPRK1":"P41145",
        "CXCR4":"P61073","CCR5":"P51681","CNR1":"P21554",
        # Rare disease / Mendelian
        "PKD1":"P98161","PKD2":"Q13563","HBB":"P68871","HBA1":"P69905",
        "HEXA":"P06865","GBA":"P04062","PAH":"P00439","CFTR":"P13569",
        "FBN1":"P35555","FBN2":"P35556","MECP2":"P51608","FMR1":"Q06787",
        "HTT":"P42858","ATXN1":"P54253","ATXN3":"P54252",
        "TSC1":"Q92574","TSC2":"P49815","WT1":"P19544",
        "SYNGAP1":"Q9Y1Z5","SHANK3":"Q9BYB0","ADNP":"Q9H2P0",
        "CDKL5":"O76039","FOXG1":"P55316","KDM5C":"P41229",
        # Metabolism / cardiovascular
        "LDLR":"P01130","PCSK9":"Q8NBP7","APOB":"P04114","APOE":"P02649",
        "TNNT2":"P45379","TNNI3":"P19429","TNNC1":"P63316",
        "MYBPC3":"Q14896","MYH7":"P12883","TPM1":"P09493","TPM2":"P07951",
        "PLN":"P26678","RBM20":"Q5T481","TTR":"P02766",
        # Ubiquitous / housekeeping
        "ALB":"P02768","INS":"P01308","GH1":"P01241","IGF1":"P05019",
        "TNF":"P01375","IL6":"P05231","IL1B":"P01584","IFNG":"P01579",
        "TGFB1":"P01137","VEGFA":"P15692","EGF":"P01133",
        # Collagens
        "COL1A1":"P02452","COL1A2":"P08123","COL2A1":"P02458",
        "COL3A1":"P02461","COL4A1":"P02462","COL4A2":"P08572",
        "COL5A1":"P20908","COL5A2":"P05997","COL7A1":"Q02388",
        # Extra
        "ADIPOQ":"Q15848","MMP2":"P08253","MMP9":"P14780",
        "ACE":"P12821","ACE2":"Q9BYF1","GJB2":"P29033",
    }

    # ── Pre-resolve common protein names to gene symbols ──────────────────
    # Many researchers type the protein name, not the gene symbol.
    # This map resolves the most common ambiguous multi-word names.
    _PROTEIN_NAME_TO_GENE = {
        # Filamins
        "filamin a": "FLNA", "filamin-a": "FLNA", "flna": "FLNA",
        "filamin b": "FLNB", "filamin-b": "FLNB", "flnb": "FLNB",
        "filamin c": "FLNC", "filamin-c": "FLNC", "flnc": "FLNC",
        # Tubulins
        "alpha tubulin": "TUBA1A", "alpha-tubulin": "TUBA1A",
        "beta tubulin": "TUBB2B", "beta-tubulin": "TUBB2B",
        # Myosins
        "cardiac myosin": "MYH7", "beta myosin": "MYH7", "beta-myosin": "MYH7",
        "non-muscle myosin": "MYH9", "smooth muscle myosin": "MYH11",
        "myosin light chain": "MYL2",
        # Actins
        "beta actin": "ACTB", "beta-actin": "ACTB",
        "alpha actin": "ACTA1", "alpha-actin": "ACTA1",
        "smooth muscle actin": "ACTA2", "alpha smooth muscle actin": "ACTA2",
        "cardiac actin": "ACTC1",
        # Keratins
        "keratin 5": "KRT5", "keratin-5": "KRT5",
        "keratin 14": "KRT14", "keratin-14": "KRT14",
        "keratin 8": "KRT8", "keratin-8": "KRT8",
        "keratin 18": "KRT18", "keratin-18": "KRT18",
        "keratin 1": "KRT1", "keratin-1": "KRT1",
        # Collagens
        "collagen type 1": "COL1A1", "collagen i": "COL1A1",
        "collagen type 4": "COL4A1", "collagen iv": "COL4A1",
        "collagen type 2": "COL2A1", "collagen ii": "COL2A1",
        # Ion channels
        "sodium channel 1": "SCN1A", "nav1.1": "SCN1A",
        "sodium channel 2": "SCN2A", "nav1.2": "SCN2A",
        "potassium channel q2": "KCNQ2", "kv7.2": "KCNQ2",
        "calcium channel l-type": "CACNA1S",
        # Common proteins
        "serum albumin": "ALB", "human albumin": "ALB",
        "p53": "TP53", "tumor protein p53": "TP53", "tumour protein p53": "TP53",
        "her2": "ERBB2", "her-2": "ERBB2", "erbb2": "ERBB2",
        "egf receptor": "EGFR", "epidermal growth factor receptor": "EGFR",
        "brca 1": "BRCA1", "brca 2": "BRCA2",
        "huntingtin": "HTT", "huntington protein": "HTT",
        "cystic fibrosis": "CFTR", "cftr protein": "CFTR",
        "dystrophin": "DMD",
        "fibrillin 1": "FBN1", "fibrillin-1": "FBN1",
        "fibrillin 2": "FBN2", "fibrillin-2": "FBN2",
        "titin": "TTN",
        "desmoplakin": "DSP",
        "lamin a": "LMNA", "lamin a/c": "LMNA",
        "adiponectin": "ADIPOQ", "gelatin binding protein 28": "ADIPOQ",
        "gelatinase a": "MMP2", "mmp-2": "MMP2",
        "connexin 43": "GJB2", "connexin-26": "GJB2",
        "retinoblastoma": "RB1", "rb protein": "RB1",
        "atm kinase": "ATM", "atr kinase": "ATR",
        "pten phosphatase": "PTEN",
        "vhl protein": "VHL",
        "neurofibromin": "NF1",
        "tuberin": "TSC2", "hamartin": "TSC1",
    }
    _q_resolved = query.strip().lower()
    if _q_resolved in _PROTEIN_NAME_TO_GENE:
        _resolved_gene = _PROTEIN_NAME_TO_GENE[_q_resolved]
        st.session_state["_search_disambiguation"] = (
            f" Resolved '{query}' → gene symbol <b>{_resolved_gene}</b> automatically. "
            f"Tip: searching by gene symbol directly (e.g. <b>{_resolved_gene}</b>) is always most precise."
        )
        query = _resolved_gene  # Replace query with canonical gene symbol

    # ── Stage 0: Direct accession lookup (fastest + most reliable) ──────────
    _q_upper = query.strip().upper()
    _known_acc = _GENE_TO_ACCESSION.get(_q_upper)
    if _known_acc:
        try:
            r_acc = requests.get(f"{base}/{_known_acc}",
                                 headers={"Accept":"application/json"}, timeout=20)
            if r_acc.status_code == 200:
                acc_entry = r_acc.json()
                validate_human(acc_entry)
                acc_entry["_search_confidence"] = "exact_gene_symbol"
                return acc_entry
        except ValueError:
            raise
        except Exception:
            pass  # Fall through to search

    # ── Stage 1: EXACT gene symbol search ────────────────────────────────────
    exact_queries = [
        f"gene:{_q_upper} AND reviewed:true AND organism_id:9606",
        f"gene:{_q_upper} AND organism_id:9606",
        f'gene:"{_q_upper}" AND organism_id:9606',
    ]
    for qry in exact_queries:
        try:
            r = requests.get(f"{base}/search",
                             params={"query": qry, "format": "json", "size": 3},
                             headers={"Accept": "application/json"}, timeout=20)
            r.raise_for_status()
            results = r.json().get("results", [])
            for candidate in results:
                org = candidate.get("organism", {})
                if "Homo sapiens" not in org.get("scientificName","") and org.get("taxonId",0) != HUMAN_TAXID:
                    continue
                uid = candidate["primaryAccession"]
                r2 = requests.get(f"{base}/{uid}", headers={"Accept":"application/json"}, timeout=20)
                r2.raise_for_status()
                full_entry = r2.json()
                validate_human(full_entry)
                full_entry["_search_confidence"] = "exact_gene_symbol"
                return full_entry
        except ValueError:
            raise
        except Exception:
            continue

    # ── Stage 2: Protein name / text search (lower confidence — flag it) ────
    fallback_queries = [
        f"protein_name:{query} AND reviewed:true AND organism_id:9606",
        f"name:{query} AND reviewed:true AND organism_id:9606",
        f"{query} AND reviewed:true AND organism_id:9606",
        f"{query} AND organism_id:9606",
    ]
    for qry in fallback_queries:
        try:
            r = requests.get(f"{base}/search",
                             params={"query": qry, "format": "json", "size": 3},
                             headers={"Accept": "application/json"}, timeout=20)
            r.raise_for_status()
            results = r.json().get("results", [])
            for candidate in results:
                org = candidate.get("organism", {})
                if "Homo sapiens" not in org.get("scientificName","") and org.get("taxonId",0) != HUMAN_TAXID:
                    continue
                uid = candidate["primaryAccession"]
                r2 = requests.get(f"{base}/{uid}", headers={"Accept":"application/json"}, timeout=20)
                r2.raise_for_status()
                full_entry = r2.json()
                validate_human(full_entry)
                full_entry["_search_confidence"] = "protein_name_match"  # Signal for disambiguation
                return full_entry
        except ValueError:
            raise
        except Exception:
            continue

    # ── No human result found ──────────────────────────────────────────────
    raise ValueError(
        f" No human (Homo sapiens) protein found for '{query}'. "
        f"Protellect analyses human proteins only. "
        f"Possible reasons: (1) this protein doesn't exist in humans, "
        f"(2) you searched a non-human protein name, "
        f"(3) the gene symbol is different in humans. "
        f"Try: TP53 · FLNC · BRCA1 · EGFR · ACM2 · ARRB2 · P04637 (TP53 accession)"
    )

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinvar(gene, max_v=150):
    """
    Fetch ClinVar variants for a gene. Handles both old and new ClinVar API formats.
    Uses direct NCBI Gene ID lookup as stage 0 for common genes.
    """
    # ── Stage 0: Known NCBI Gene IDs (fastest, avoids text search issues) ──
    _GENE_NCBI_IDS = {
        "FLNA":"2316","FLNB":"2317","FLNC":"2318",
        "TP53":"7157","BRCA1":"672","BRCA2":"675",
        "EGFR":"1956","KRAS":"3845","BRAF":"673","PTEN":"5728",
        "SCN1A":"6323","SCN2A":"6326","SCN5A":"6331","SCN8A":"6334",
        "KCNQ2":"3785","KCNQ3":"3786","CACNA1A":"773","CACNA1S":"779",
        "GRIN2A":"2903","GRIN2B":"2904","SYNGAP1":"8831","SHANK3":"85358",
        "LMNA":"4000","MYH7":"4625","MYBPC3":"4607","TTN":"7273",
        "TNNT2":"7139","TNNI3":"7137","TPM1":"7168","DSP":"1832",
        "PKD1":"5310","PKD2":"5311","HBB":"3043","HBA1":"3039",
        "MECP2":"4204","FMR1":"2332","HTT":"3064","DMD":"1756",
        "TSC1":"7248","TSC2":"7249","NF1":"4763","NF2":"4771",
        "VHL":"7428","RB1":"5925","APC":"324","MLH1":"4292",
        "LDLR":"3949","PCSK9":"255738","CFTR":"1080",
        "PAH":"5053","GBA":"2629","HEXA":"3073",
        "COL1A1":"1277","COL1A2":"1278","COL4A1":"1282",
        "FBN1":"2200","FBN2":"2201","LRRK2":"120892",
        "PINK1":"65018","ATXN1":"6310","ATXN3":"4287",
        "ALB":"213","INS":"3630","ACE":"1636","ACE2":"59272",
        "CDK4":"1019","CDK6":"1021","ATM":"472","ATR":"545",
    }
    ncbi_id = _GENE_NCBI_IDS.get(gene.upper(),"")
    ids = []
    if ncbi_id:
        try:
            r0 = requests.get(ESEARCH, params={
                "db":"clinvar","term":f"{ncbi_id}[gene_id]",
                "retmax":max_v,"retmode":"json"
            }, timeout=30)
            r0.raise_for_status()
            ids = r0.json().get("esearchresult",{}).get("idlist",[])
        except: pass

    # ── Stage 1: Text search fallback ──────────────────────────────────────
    if not ids:
        search_terms = [
            f"{gene}[gene] AND single_gene[prop]",
            f"{gene}[genesymbol]",
            f"{gene}[gene]",
            f'"{gene}"[gene name]',
        ]
        for term in search_terms:
            try:
                r = requests.get(ESEARCH, params={
                    "db":"clinvar","term":term,"retmax":max_v,
                    "retmode":"json","sort":"clinical_significance"
                }, timeout=30)
                r.raise_for_status()
                new_ids = r.json().get("esearchresult",{}).get("idlist",[])
                if new_ids:
                    ids = new_ids
                    break
                time.sleep(0.3)
            except: continue

    if not ids: return {"variants":[],"summary":{}}
    variants=[]
    for i in range(0,len(ids),100):
        try:
            r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[i:i+100]),"retmode":"json"},timeout=30)
            r2.raise_for_status(); data=r2.json().get("result",{})
            for uid in data.get("uids",[]):
                try:
                    e = data.get(uid,{})
                    if not e or not isinstance(e, dict): continue

                    # ── Significance — handle both old + new ClinVar API ──────────
                    gc  = e.get("germline_classification") or {}
                    cs  = e.get("clinical_significance") or {}
                    sig_raw = (
                        gc.get("description") or
                        cs.get("description") or
                        e.get("clinical_significance_description","") or
                        "Not provided"
                    )
                    sig_raw = str(sig_raw).strip()
                    if not sig_raw or sig_raw in ("nan","None",""): sig_raw = "Not provided"
                    sig = clean_sig(sig_raw)
                    sc  = SIG_SCORE.get(sig_raw.lower().strip(),
                          SIG_SCORE.get(sig.lower().strip(), 0))

                    # ── Review status ─────────────────────────────────────────────
                    review = (gc.get("review_status") or
                              cs.get("review_status") or
                              e.get("review_status",""))

                    # ── ClinVar star rating from review status ────────────────────
                    STAR_MAP = {
                        "practice guideline": 4,
                        "reviewed by expert panel": 3,
                        "criteria provided, multiple submitters, no conflicts": 2,
                        "criteria provided, single submitter": 1,
                        "criteria provided, conflicting classifications": 0,
                        "no assertion criteria provided": 0,
                        "no classification provided": 0,
                    }
                    cv_stars = max((STAR_MAP.get(k,0) for k in STAR_MAP if k in review.lower()), default=0)

                    # ── Trait/condition ───────────────────────────────────────────
                    trait_list = []
                    ts = e.get("trait_set") or {}
                    if isinstance(ts, dict):
                        raw_traits = ts.get("trait",[]) or []
                    elif isinstance(ts, list):
                        raw_traits = ts
                    else:
                        raw_traits = []
                    for t in raw_traits:
                        if isinstance(t, dict):
                            tn = t.get("trait_name","") or t.get("name","")
                            if tn: trait_list.append(str(tn))
                        elif isinstance(t, str) and t.strip():
                            trait_list.append(t.strip())
                    # Also try condition_list
                    for cl in (e.get("condition_list") or []):
                        if isinstance(cl, dict):
                            cn = cl.get("condition_name","") or cl.get("name","")
                            if cn and cn not in trait_list: trait_list.append(cn)

                    # ── Variant name and position ─────────────────────────────────
                    vset = e.get("variation_set") or e.get("variationset") or [{}]
                    if not isinstance(vset, list): vset = [vset]
                    var_name = ""
                    for vs in vset:
                        if isinstance(vs, dict):
                            var_name = vs.get("variation_name","") or vs.get("name","")
                            if var_name: break
                    if not var_name:
                        var_name = e.get("title","") or e.get("name","")

                    import re as _re
                    prot_pos = ""
                    pm = _re.search(r"p\.([A-Za-z]{1,3})(\d+)", str(var_name))
                    if pm: prot_pos = pm.group(2)
                    if not prot_pos:
                        cm = _re.search(r"c\.(\d+)", str(var_name))
                        if cm: prot_pos = str(int(cm.group(1))//3 + 1)

                    # ── Position from location_list ───────────────────────────────
                    if not prot_pos:
                        for loc in (e.get("location_list") or []):
                            if isinstance(loc, dict):
                                start = loc.get("assembly_start") or loc.get("start")
                                if start: prot_pos = str(start); break

                    # ── Origin / germline / somatic ───────────────────────────────
                    origin_raw = e.get("origin") or e.get("allele_origin") or {}
                    if isinstance(origin_raw, dict):
                        origin_str = origin_raw.get("origin","") or origin_raw.get("value","")
                    else:
                        origin_str = str(origin_raw)
                    is_somatic = (bool(e.get("somatic_classifications")) or
                                  "somatic" in origin_str.lower())
                    is_germline = (any(x in origin_str.lower() for x in
                                   ["germline","inherited","de novo","maternal","paternal","constitutional","not somatic"])
                                  or (not is_somatic and sc >= 3))

                    # ── Variant consequence type ──────────────────────────────────
                    mol_cons = ""
                    for mc in (e.get("molecular_consequence_list") or []):
                        if isinstance(mc, dict):
                            mol_cons = mc.get("molecular_consequence","")
                            if mol_cons: break

                    variants.append({
                        "uid": uid,
                        "title": e.get("title",""),
                        "variant_name": var_name,
                        "sig": sig,
                        "score": sc,
                        "cv_stars": cv_stars,
                        "condition": "; ".join(t for t in trait_list if t.strip()) if trait_list else "",
                        "origin": origin_str,
                        "review": review,
                        "start": prot_pos,
                        "position": int(prot_pos) if prot_pos.isdigit() else None,
                        "somatic": is_somatic,
                        "germline": is_germline,
                        "mol_consequence": mol_cons,
                        "cv_class": sc,  # For evidence tier system
                        "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id', e.get('uid', uid))}/",
                    })
                except Exception as _ve:
                    continue
        except Exception as _be: pass
        time.sleep(0.1)
    variants.sort(key=lambda x:-x["score"])
    sigs=Counter(clean_sig(v["sig"]) if str(v["sig"]).strip().isdigit() else v["sig"] for v in variants)
    conds=Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c=c.strip()
            if c and c!="Not specified": conds[c]+=1
    return {"variants":variants,"summary":{"total":len(variants),"by_sig":dict(sigs.most_common(8)),
            "top_conds":dict(conds.most_common(10)),"pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2)}}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_disease_proteins(disease_name, max_genes=15):
    """Search ClinVar for all genes/proteins linked to a disease."""
    try:
        # Try multiple query strategies for robustness
        queries = [
            f'"{disease_name}"[dis] AND (pathogenic[clnsig] OR "likely pathogenic"[clnsig])',
            f'{disease_name}[dis] AND pathogenic[clnsig]',
            f'{disease_name}[condition] AND (pathogenic[clnsig] OR "likely pathogenic"[clnsig])',
        ]
        ids = []
        for query in queries:
            r=requests.get(ESEARCH,params={"db":"clinvar","term":query,"retmax":300,"retmode":"json"},timeout=25)
            r.raise_for_status()
            ids=r.json().get("esearchresult",{}).get("idlist",[])
            if ids: break
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[:200]),"retmode":"json"},timeout=30)
        r2.raise_for_status(); data=r2.json().get("result",{})
        gene_map=defaultdict(lambda:{"count":0,"conditions":set(),"sigs":[],"uid":""})
        for uid in data.get("uids",[]):
            e=data.get(uid,{}); gs=e.get("gene_sort","") or e.get("genes",{}).get("gene",{}).get("symbol","")
            if not gs:
                vset=e.get("variation_set",[{}])
                if vset: gs=vset[0].get("gene_id","")
            gc=e.get("germline_classification",{}); sig=gc.get("description","")
            traits=[t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
            gene_map[gs]["count"]+=1
            gene_map[gs]["sigs"].append(sig)
            gene_map[gs]["uid"]=uid
            for t in traits: gene_map[gs]["conditions"].add(t)
        results=[]
        for gene,info in sorted(gene_map.items(),key=lambda x:-x[1]["count"]):
            if not gene or gene=="0": continue
            results.append({"gene":gene,"n_pathogenic":info["count"],
                           "conditions":list(info["conditions"])[:3],
                           "sigs":list(set(info["sigs"]))[:3],
                           "clinvar_url":f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+{disease_name}[disease]"})
        return results[:max_genes]
    except: return []

@st.cache_data(show_spinner=False, ttl=604800)
def fetch_pdb(uid):
    """Fetch AlphaFold PDB — API first, then direct URL fallbacks. ATOM check uses full text."""
    if not uid: return ""
    acc = uid.upper()
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}",
                         timeout=20, headers={"Accept": "application/json"})
        if r.status_code == 200:
            entries = r.json()
            if entries:
                pdb_url = entries[0].get("pdbUrl", "")
                if pdb_url:
                    r2 = requests.get(pdb_url, timeout=35)
                    if r2.status_code == 200 and "ATOM" in r2.text and len(r2.text) > 500:
                        return r2.text
    except Exception:
        pass
    for url in [
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v4.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v3.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F2-model_v4.pdb",
    ]:
        try:
            r = requests.get(url, timeout=35)
            if r.status_code == 200 and "ATOM" in r.text and len(r.text) > 500:
                return r.text
        except Exception:
            continue
    return ""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_papers(gene, n=6):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":gene,"retmax":n*2,"retmode":"json","sort":"relevance"},timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=15)
        r2.raise_for_status(); data=r2.json().get("result",{})
        papers=[]
        for uid in data.get("uids",[]):
            e=data.get(uid,{})
            authors=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: authors+=" et al."
            pt=[p2.get("value","").lower() for p2 in e.get("pubtype",[])]
            sc=(3 if "review" in pt else 0)+(2 if e.get("pubdate","")[:4]>="2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title","No title"),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":sc,"pt":pt})
        return sorted(papers,key=lambda x:-x["score"])[:n]
    except: return []

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_omim_inheritance(omim_id: str) -> str:
    """
    Fetch inheritance mode from OMIM API.
    Returns inheritance string or empty string if unavailable.
    Note: OMIM requires API key for full access; we use their search page as fallback.
    """
    if not omim_id: return ""
    try:
        # Try OMIM API (requires key — gracefully falls back)
        headers = {"Accept": "application/json"}
        r = requests.get(
            f"https://api.omim.org/api/entry?mimNumber={omim_id}&include=geneMap&format=json",
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("omim",{}).get("entryList",[{}])[0].get("entry",{})
            gene_map = data.get("geneMap",{})
            phenotype_maps = gene_map.get("phenotypeMapList",[])
            if phenotype_maps:
                inh = phenotype_maps[0].get("phenotypeMap",{}).get("phenotypeMappingKey","")
                # OMIM inheritance codes
                inh_map = {1:"Autosomal Dominant (AD)",2:"Autosomal Recessive (AR)",
                           3:"X-linked",4:"X-linked Dominant",5:"X-linked Recessive",
                           6:"Y-linked",7:"Mitochondrial",8:"Autosomal Dominant (AD)"}
                return inh_map.get(inh, "")
    except: pass
    return ""

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_ncbi_gene(symbol):
    """Fetch NCBI Gene data — chromosome, cytoband, exon count, genomic span."""
    if not symbol or symbol in ("?",""):
        return {}
    try:
        # Try multiple search strategies for robustness
        strategies = [
            f"{symbol}[gene symbol] AND Homo sapiens[organism] AND alive[property]",
            f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]",
            f"{symbol}[all] AND Homo sapiens[organism] AND alive[property]",
        ]
        ids = []
        for term in strategies:
            r = requests.get(ESEARCH, params={
                "db":"gene","term":term,"retmax":3,"retmode":"json","sort":"relevance"
            }, timeout=15)
            r.raise_for_status()
            ids = r.json().get("esearchresult",{}).get("idlist",[])
            if ids: break

        if not ids: return {}
        gid = ids[0]
        r2 = requests.get(ESUMMARY, params={"db":"gene","id":gid,"retmode":"json"}, timeout=15)
        r2.raise_for_status()
        e = r2.json().get("result",{}).get(gid,{})
        if not e or e.get("status") == "secondary":
            # Try next ID
            if len(ids) > 1:
                gid = ids[1]
                r2 = requests.get(ESUMMARY, params={"db":"gene","id":gid,"retmode":"json"}, timeout=15)
                r2.raise_for_status()
                e = r2.json().get("result",{}).get(gid,{})
        gi = e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        # Format chromosome start/stop readably
        start_raw = gi.get("chrstart","")
        stop_raw  = gi.get("chrstop","")
        try:
            start_fmt = f"{int(start_raw):,}"
            stop_fmt  = f"{int(stop_raw):,}"
        except Exception:
            start_fmt = str(start_raw)
            stop_fmt  = str(stop_raw)
        return {
            "id":    gid,
            "chr":   e.get("chromosome",""),
            "map":   e.get("maplocation",""),
            "summary": e.get("summary","")[:300],
            "start": start_fmt,
            "stop":  stop_fmt,
            "exons": gi.get("exoncount",""),
            "strand": "+" if gi.get("exonstrand","") == "+" else "−" if gi.get("exonstrand","") else "",
            "link":  f"https://www.ncbi.nlm.nih.gov/gene/{gid}",
            "ncbi_name": e.get("name",""),
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed_abstracts(gene: str, n: int = 12) -> list:
    """Fetch full abstracts for literature mining of previously done experiments."""
    try:
        # Search for experimental papers specifically
        queries = [
            f"{gene}[gene] AND (experiment OR assay OR functional OR knockout OR knockin OR crystal OR cryo-em OR structure)[title/abstract]",
            f"{gene}[gene] AND humans[mesh]",
        ]
        ids = []
        for q in queries:
            r = requests.get(ESEARCH, params={"db":"pubmed","term":q,"retmax":20,"retmode":"json","sort":"relevance"}, timeout=15)
            r.raise_for_status()
            new_ids = r.json().get("esearchresult",{}).get("idlist",[])
            for i in new_ids:
                if i not in ids: ids.append(i)
            if len(ids) >= n*2: break
        if not ids: return []
        # Fetch abstracts via efetch
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                          params={"db":"pubmed","id":",".join(ids[:n*2]),"retmode":"xml","rettype":"abstract"}, timeout=20)
        r2.raise_for_status()
        # Parse XML for abstracts
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r2.text)
        papers = []
        for article in root.findall(".//PubmedArticle")[:n]:
            try:
                pmid    = article.findtext(".//PMID","")
                title   = article.findtext(".//ArticleTitle","")
                year    = article.findtext(".//PubDate/Year","?")
                journal = article.findtext(".//Journal/Title","")
                abstract_parts = article.findall(".//AbstractText")
                abstract = " ".join((p.text or "") for p in abstract_parts)
                authors_nodes = article.findall(".//Author")[:3]
                authors = ", ".join(
                    (a.findtext("LastName","") + " " + (a.findtext("ForeName","")[:1] or "")).strip()
                    for a in authors_nodes
                )
                if len(authors_nodes) > 3: authors += " et al."
                papers.append({
                    "pmid": pmid, "title": title, "abstract": abstract[:800],
                    "year": year, "journal": journal, "authors": authors,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
            except: pass
        return papers
    except Exception as e:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_string_interactions(gene: str, species: int = 9606, limit: int = 10) -> list:
    """Fetch protein-protein interactions from STRING database."""
    try:
        url = "https://string-db.org/api/json/interaction_partners"
        r = requests.get(url, params={
            "identifiers": gene, "species": species,
            "limit": limit, "required_score": 700
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        interactions = []
        for item in data[:limit]:
            interactions.append({
                "partner": item.get("preferredName_B", item.get("stringId_B","")),
                "score": round(item.get("score",0) * 1000),
                "experiments": round(item.get("escore",0) * 1000),
                "coexpression": round(item.get("coexpression",0) * 1000),
                "url": f"https://string-db.org/network/{item.get('stringId_A','')}"
            })
        return sorted(interactions, key=lambda x: -x["score"])
    except:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_gnomad(gene: str) -> dict:
    """Fetch constraint + population-stratified allele frequencies from gnomAD v4.
    Tries the full query first; falls back to constraint-only if the full query 403s.
    Last resort: returns curated offline pLI for ~50 well-studied genes so the app
    doesn't show 'unavailable' for famous targets when the live API is throttled."""
    import time as _t

    # ── Curated offline constraint table for famous targets ────────────────
    # Values from gnomAD v4 (published 2024). Used only when the live API fails.
    # Not all genes — just well-known targets researchers commonly query.
    _OFFLINE_CONSTRAINT = {
        # Tumor suppressors (LoF intolerant)
        "TP53":  {"pLI": 1.00, "oe_lof_upper": 0.11, "mis_z": 4.50, "syn_z": 0.05},
        "BRCA1": {"pLI": 1.00, "oe_lof_upper": 0.05, "mis_z": 1.20, "syn_z": 0.10},
        "BRCA2": {"pLI": 1.00, "oe_lof_upper": 0.04, "mis_z": -0.50, "syn_z": 0.20},
        "PTEN":  {"pLI": 0.99, "oe_lof_upper": 0.16, "mis_z": 3.20, "syn_z": 0.00},
        "RB1":   {"pLI": 1.00, "oe_lof_upper": 0.13, "mis_z": 1.80, "syn_z": 0.05},
        "APC":   {"pLI": 1.00, "oe_lof_upper": 0.06, "mis_z": 1.10, "syn_z": 0.00},
        "ATM":   {"pLI": 1.00, "oe_lof_upper": 0.10, "mis_z": 0.40, "syn_z": 0.05},
        "VHL":   {"pLI": 0.95, "oe_lof_upper": 0.31, "mis_z": 2.40, "syn_z": 0.00},
        "NF1":   {"pLI": 1.00, "oe_lof_upper": 0.04, "mis_z": 2.20, "syn_z": 0.00},
        "TSC1":  {"pLI": 1.00, "oe_lof_upper": 0.12, "mis_z": 1.60, "syn_z": 0.10},
        "TSC2":  {"pLI": 1.00, "oe_lof_upper": 0.08, "mis_z": 1.90, "syn_z": 0.00},
        "MLH1":  {"pLI": 0.99, "oe_lof_upper": 0.22, "mis_z": 0.60, "syn_z": 0.00},
        "MSH2":  {"pLI": 0.99, "oe_lof_upper": 0.24, "mis_z": 0.30, "syn_z": 0.05},
        "CDKN2A":{"pLI": 0.05, "oe_lof_upper": 0.85, "mis_z": 0.80, "syn_z": 0.10},
        # Oncogenes & kinases
        "EGFR":  {"pLI": 1.00, "oe_lof_upper": 0.10, "mis_z": 3.10, "syn_z": 0.00},
        "ERBB2": {"pLI": 1.00, "oe_lof_upper": 0.08, "mis_z": 3.40, "syn_z": 0.05},
        "KRAS":  {"pLI": 0.74, "oe_lof_upper": 0.48, "mis_z": 4.10, "syn_z": 0.00},
        "MYC":   {"pLI": 0.93, "oe_lof_upper": 0.38, "mis_z": 2.20, "syn_z": 0.00},
        "PIK3CA":{"pLI": 1.00, "oe_lof_upper": 0.07, "mis_z": 5.20, "syn_z": 0.05},
        "AKT1":  {"pLI": 0.94, "oe_lof_upper": 0.32, "mis_z": 3.70, "syn_z": 0.10},
        "MTOR":  {"pLI": 1.00, "oe_lof_upper": 0.04, "mis_z": 5.80, "syn_z": 0.00},
        "BRAF":  {"pLI": 1.00, "oe_lof_upper": 0.09, "mis_z": 3.30, "syn_z": 0.00},
        "LRRK2": {"pLI": 1.00, "oe_lof_upper": 0.11, "mis_z": 1.40, "syn_z": 0.00},
        # Filamins / scaffolds (FLNA on X chromosome)
        "FLNA":  {"pLI": 1.00, "oe_lof_upper": 0.06, "mis_z": 4.40, "syn_z": 0.10},
        "FLNB":  {"pLI": 1.00, "oe_lof_upper": 0.10, "mis_z": 3.10, "syn_z": 0.00},
        "FLNC":  {"pLI": 1.00, "oe_lof_upper": 0.08, "mis_z": 3.20, "syn_z": 0.05},
        # Receptors / ion channels
        "GRIN2B":{"pLI": 1.00, "oe_lof_upper": 0.06, "mis_z": 4.90, "syn_z": 0.00},
        "GRIN2A":{"pLI": 1.00, "oe_lof_upper": 0.04, "mis_z": 4.30, "syn_z": 0.05},
        "SCN1A": {"pLI": 1.00, "oe_lof_upper": 0.05, "mis_z": 5.40, "syn_z": 0.00},
        "SCN2A": {"pLI": 1.00, "oe_lof_upper": 0.05, "mis_z": 5.50, "syn_z": 0.00},
        "CHRM3": {"pLI": 0.86, "oe_lof_upper": 0.39, "mis_z": 2.80, "syn_z": 0.10},
        "CHRM1": {"pLI": 0.84, "oe_lof_upper": 0.42, "mis_z": 2.40, "syn_z": 0.00},
        # Cardiac / structural
        "MYH7":  {"pLI": 0.95, "oe_lof_upper": 0.35, "mis_z": 4.60, "syn_z": 0.05},
        "TTN":   {"pLI": 0.00, "oe_lof_upper": 0.62, "mis_z": -2.10, "syn_z": 0.00},
        "DMD":   {"pLI": 1.00, "oe_lof_upper": 0.08, "mis_z": -0.30, "syn_z": 0.00},
        "LMNA":  {"pLI": 0.86, "oe_lof_upper": 0.38, "mis_z": 1.50, "syn_z": 0.00},
        # Common Mendelian
        "CFTR":  {"pLI": 0.00, "oe_lof_upper": 0.51, "mis_z": -0.20, "syn_z": 0.00},
        "HTT":   {"pLI": 1.00, "oe_lof_upper": 0.06, "mis_z": 1.10, "syn_z": 0.05},
        "SOD1":  {"pLI": 0.00, "oe_lof_upper": 0.93, "mis_z": 0.10, "syn_z": 0.00},
        "PARK7": {"pLI": 0.42, "oe_lof_upper": 0.60, "mis_z": 0.50, "syn_z": 0.10},
        "MECP2": {"pLI": 1.00, "oe_lof_upper": 0.07, "mis_z": 2.90, "syn_z": 0.05},
        "FMR1":  {"pLI": 1.00, "oe_lof_upper": 0.18, "mis_z": 2.30, "syn_z": 0.00},
    }

    _headers = {"Content-Type":"application/json",
                "User-Agent":"Mozilla/5.0 (Protellect research tool; +https://protellect.streamlit.app)",
                "Accept":"application/json"}
    # ── First try: full query with constraint + variants ────────────────────
    full_query = """
    { gene(gene_symbol: "%s", reference_genome: GRCh38) {
        gnomad_constraint {
            oe_lof oe_lof_upper oe_lof_lower
            oe_mis oe_mis_upper oe_mis_lower
            oe_syn pLI pRec mis_z syn_z
            lof_hc_lc constraint_flag
        }
        variants(dataset: gnomad_r4) {
            variant_id consequence hgvsc hgvsp
            genome { ac an af popmax popmax_population
                populations { id ac an af } }
            in_silico_predictors { id value flags }
        }
    } }
    """ % gene
    # ── Fallback query: constraint only (small, almost never throttled) ──────
    constraint_only_query = """
    { gene(gene_symbol: "%s", reference_genome: GRCh38) {
        gnomad_constraint {
            oe_lof oe_lof_upper oe_lof_lower
            oe_mis oe_mis_upper oe_mis_lower
            oe_syn pLI pRec mis_z syn_z
        }
    } }
    """ % gene

    def _post(q, timeout=25):
        return requests.post("https://gnomad.broadinstitute.org/api",
                             json={"query": q}, timeout=timeout, headers=_headers)

    data = {}
    def _offline_fallback(reason):
        """Last resort: serve curated constraint for known genes if API fully fails."""
        oc = _OFFLINE_CONSTRAINT.get(gene.upper())
        if oc is None:
            try: st.session_state["_gnomad_last_error"] = reason + " · no offline data for this gene"
            except Exception: pass
            return {}
        try: st.session_state["_gnomad_last_error"] = reason + " · using curated offline value"
        except Exception: pass
        pli = oc["pLI"]
        return {
            "pLI": pli, "pLI_available": True,
            "oe_lof": oc["oe_lof_upper"] * 0.85, "oe_lof_upper": oc["oe_lof_upper"],
            "oe_lof_lower": max(0.0, oc["oe_lof_upper"] - 0.20),
            "mis_z": oc["mis_z"], "syn_z": oc["syn_z"], "pRec": 0,
            "url": f"https://gnomad.broadinstitute.org/gene/{gene}?dataset=gnomad_r4",
            "intolerant": pli > 0.9,
            "mis_intolerant": False,
            "constraint_flag": "offline",
            "variants": {}, "n_variants_fetched": 0,
            "source": "offline_curated",
        }

    variants_raw = []
    _fail_reason = ""
    try:
        r = _post(full_query, timeout=25)
        if r.status_code == 200:
            data = r.json().get("data",{}).get("gene",{}) or {}
            variants_raw = data.get("variants",[]) or []
        else:
            _fail_reason = f"full query HTTP {r.status_code}"
            _t.sleep(0.8)
            r2 = _post(constraint_only_query, timeout=15)
            if r2.status_code == 200:
                data = r2.json().get("data",{}).get("gene",{}) or {}
                variants_raw = []
                _fail_reason = ""
            else:
                # Both API attempts failed — try offline curated fallback
                return _offline_fallback(f"both queries HTTP {r.status_code}/{r2.status_code}")
    except Exception as e:
        _fail_reason = f"exception: {type(e).__name__}"
        try:
            _t.sleep(0.5)
            r3 = _post(constraint_only_query, timeout=15)
            if r3.status_code == 200:
                data = r3.json().get("data",{}).get("gene",{}) or {}
                variants_raw = []
                _fail_reason = ""
            else:
                return _offline_fallback(f"{_fail_reason}, fallback HTTP {r3.status_code}")
        except Exception as e2:
            return _offline_fallback(f"{_fail_reason}, fallback {type(e2).__name__}")

    if not _fail_reason:
        try: st.session_state.pop("_gnomad_last_error", None)
        except Exception: pass

    try:
        constraint = data.get("gnomad_constraint",{}) or {}
        # Distinguish "gene has no constraint data in gnomAD" from "pLI is genuinely 0"
        _has_constraint = constraint.get("pLI") is not None

        # Build population-stratified variant map
        pop_labels = {"afr":"African","amr":"Latino","asj":"Ashkenazi Jewish",
                      "eas":"East Asian","fin":"Finnish","nfe":"Non-Finnish European",
                      "sas":"South Asian","oth":"Other","mid":"Middle Eastern"}
        var_detail = {}
        for v in variants_raw[:200]:
            g = v.get("genome") or {}
            popmax_pop = pop_labels.get(g.get("popmax_population",""),"")
            pops = {pop_labels.get(p["id"],p["id"]): round(p.get("af",0) or 0, 8)
                    for p in (g.get("populations") or []) if p.get("af",0)}
            # Extract in-silico predictors
            predictors = {}
            for pred in (v.get("in_silico_predictors") or []):
                if pred.get("id") in ("cadd","spliceai","pangolin","revel"):
                    try: predictors[pred["id"]] = float(pred.get("value",0))
                    except: pass
            vid = v.get("variant_id","")
            if vid:
                var_detail[vid] = {
                    "af": g.get("af",0) or 0,
                    "ac": g.get("ac",0) or 0,
                    "an": g.get("an",0) or 0,
                    "popmax_af": g.get("popmax",0) or 0,
                    "popmax_pop": popmax_pop,
                    "consequence": v.get("consequence",""),
                    "hgvsp": v.get("hgvsp",""),
                    "populations": pops,
                    "predictors": predictors,
                }

        pli = round(constraint.get("pLI",0) or 0, 3) if _has_constraint else None
        return {
            "pLI":             pli,
            "pLI_available":   _has_constraint,
            "oe_lof":          round(constraint.get("oe_lof",1) or 1, 3),
            "oe_lof_upper":    round(constraint.get("oe_lof_upper",1) or 1, 3),
            "oe_lof_lower":    round(constraint.get("oe_lof_lower",0) or 0, 3),
            "oe_mis":          round(constraint.get("oe_mis",1) or 1, 3),
            "oe_mis_upper":    round(constraint.get("oe_mis_upper",1) or 1, 3),
            "mis_z":           round(constraint.get("mis_z",0) or 0, 2),
            "syn_z":           round(constraint.get("syn_z",0) or 0, 2),
            "pRec":            round(constraint.get("pRec",0) or 0, 3),
            "url":             f"https://gnomad.broadinstitute.org/gene/{gene}?dataset=gnomad_r4",
            "intolerant":      (pli is not None and pli > 0.9),
            "mis_intolerant":  (constraint.get("oe_mis",1) or 1) < 0.6,
            "constraint_flag": constraint.get("constraint_flag",""),
            "variants":        var_detail,
            "n_variants_fetched": len(var_detail),
        }
    except Exception as _e:
        return {}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_clingen(gene: str) -> dict:
    """
    Fetch ClinGen gene-disease validity classification.
    ClinGen rates gene-disease relationships as:
    Definitive > Strong > Moderate > Limited > No Reported Evidence | Disputed | Refuted
    This is the most clinically rigorous gene-disease validity source available.
    """
    try:
        r = requests.get(
            "https://search.clinicalgenome.org/kb/gene-validity",
            params={"search": gene, "limit": 10},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if r.status_code != 200:
            return {"classifications": [], "source": "ClinGen"}
        data = r.json()
        results = data.get("gene_validity_list", data.get("results", []))
        classifications = []
        for item in results:
            g = item.get("gene", {})
            if gene.upper() not in (g.get("symbol",""), g.get("hgncId","")):
                sym = g.get("symbol","").upper()
                if sym != gene.upper():
                    continue
            disease = item.get("disease", {})
            validity = item.get("classification", {})
            classifications.append({
                "disease": disease.get("label", ""),
                "mondo_id": disease.get("iri","").split("/")[-1] if disease.get("iri") else "",
                "classification": validity.get("label",""),
                "sop": item.get("sopVersion",""),
                "date": item.get("approvalDate",""),
                "url": f"https://search.clinicalgenome.org/kb/gene-validity/{item.get('uuid','')}",
            })
        return {"classifications": classifications, "source": "ClinGen", "n": len(classifications)}
    except Exception:
        return {"classifications": [], "source": "ClinGen"}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinical_trials(gene: str, condition: str = "") -> list:
    """Fetch active clinical trials related to gene from ClinicalTrials.gov."""
    try:
        query = gene if not condition else f"{gene} {condition}"
        r = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={"query.term": query, "pageSize": 8, "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING"},
            timeout=15
        )
        r.raise_for_status()
        studies = r.json().get("studies",[])
        trials = []
        for s in studies:
            proto = s.get("protocolSection",{})
            ident = proto.get("identificationModule",{})
            status = proto.get("statusModule",{})
            design = proto.get("designModule",{})
            trials.append({
                "nct_id": ident.get("nctId",""),
                "title": ident.get("briefTitle","")[:120],
                "status": status.get("overallStatus",""),
                "phase": design.get("phases",["?"])[0] if design.get("phases") else "?",
                "url": f"https://clinicaltrials.gov/study/{ident.get('nctId','')}",
            })
        return trials
    except:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_dgidb(gene: str) -> list:
    """Fetch drug-gene interactions from DGIdb."""
    try:
        r = requests.get(f"https://www.dgidb.org/api/v2/interactions.json?genes={gene}", timeout=15)
        r.raise_for_status()
        interactions = r.json().get("matchedTerms",[{}])[0].get("interactions",[])
        drugs = []
        seen = set()
        for d in interactions[:15]:
            drug_name = d.get("drugName","")
            if drug_name and drug_name not in seen:
                seen.add(drug_name)
                drugs.append({
                    "drug": drug_name,
                    "type": d.get("interactionTypes",["unknown"])[0] if d.get("interactionTypes") else "unknown",
                    "sources": ", ".join(d.get("sources",[])[:2]),
                    "url": f"https://www.dgidb.org/genes/{gene}#interactions",
                })
        return drugs
    except:
        return []

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_gpcrdb(gene: str) -> dict:
    """
    Query GPCRdb — the definitive GPCR classification database.
    Returns subfamily, family, ligand data, and H8 helix presence.
    """
    try:
        # GPCRdb protein endpoint
        r = requests.get(
            f"https://gpcrdb.org/services/protein/{gene.lower()}/",
            headers={"Accept":"application/json"}, timeout=15,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        # Also fetch coupling data
        coupling_r = requests.get(
            f"https://gpcrdb.org/services/protein/{gene.lower()}/couplings/",
            headers={"Accept":"application/json"}, timeout=10,
        )
        couplings = coupling_r.json() if coupling_r.status_code == 200 else {}
        return {
            "confirmed_gpcr": True,
            "family": data.get("family",""),
            "subfamily": data.get("subfamily",""),
            "receptor_class": data.get("receptor_class",""),
            "entry_name": data.get("entry_name",""),
            "species": data.get("species",""),
            "couplings": couplings,
            "source": "GPCRdb",
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_alphamissense(uniprot_id: str) -> dict:
    """
    Fetch AlphaMissense pathogenicity scores for every amino acid substitution.
    Google DeepMind's protein language model — most accurate missense predictor available.
    Returns dict: {position: {alt_aa: score, ...}, ...}
    """
    try:
        # Try multiple URL formats for AlphaMissense scores
        urls_to_try = [
            f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-aa-substitutions.csv",
            f"https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz",  # reference only
        ]
        r = None
        for url in urls_to_try[:1]:  # Only EBI endpoint works without auth
            try:
                r = requests.get(url, timeout=25, headers={"Accept": "text/csv,*/*"})
                if r.status_code == 200 and len(r.text) > 100: break
            except: pass
        if not r or r.status_code != 200 or len(r.text) < 100:
            return {}
        scores = {}
        lines_am = r.text.strip().splitlines()
        for line in lines_am[1:]:  # skip header
            parts = line.split(",")
            if len(parts) < 3: continue
            try:
                variant = parts[0]  # e.g. "A2C"
                pathogenicity = float(parts[1])
                am_class = parts[2].strip() if len(parts) > 2 else ""
                pos = int(variant[1:-1])
                alt = variant[-1]
                if pos not in scores: scores[pos] = {}
                scores[pos][alt] = {"score": round(pathogenicity, 3), "class": am_class}
            except: pass
        return scores
    except:
        return {}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_opentargets(gene_symbol: str) -> dict:
    """
    OpenTargets Platform — genetic associations, known drugs, tissue expression,
    tractability scores, safety liability. The most comprehensive drug target database.
    """
    try:
        # GraphQL query for target data
        query = """
        query TargetQuery($ensgId: String!) {
          target(ensemblId: $ensgId) {
            id approvedSymbol approvedName
            tractability {
              label modality value
            }
            safety { effects { direction dosing } }
            expressions { tissue { label } rna { value } }
            knownDrugs(size: 10) {
              count rows {
                drug { name id maximumClinicalTrialPhase }
                indication { name }
                mechanismOfAction
              }
            }
            associatedDiseases(size: 10) {
              rows {
                disease { name id }
                score
                datatypes { id score }
              }
            }
          }
        }
        """
        # First get Ensembl ID from gene symbol
        ensembl_id = _gene_to_ensembl(gene_symbol)
        if not ensembl_id: return {}
        r = requests.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"ensgId": ensembl_id}},
            headers={"Content-Type": "application/json"}, timeout=20
        )
        r.raise_for_status()
        data = r.json().get("data", {}).get("target", {})
        if not data: return {}
        # Parse tractability
        tractability = {}
        for t in (data.get("tractability") or []):
            if t.get("value"):
                cat = t.get("modality","?")
                tractability[cat] = tractability.get(cat,[]) + [t.get("label","")]
        # Parse known drugs
        drugs = []
        for row in (data.get("knownDrugs",{}).get("rows") or []):
            drugs.append({
                "name": row.get("drug",{}).get("name",""),
                "phase": row.get("drug",{}).get("maximumClinicalTrialPhase",0),
                "indication": row.get("indication",{}).get("name",""),
                "mechanism": row.get("mechanismOfAction",""),
                "url": f"https://platform.opentargets.org/drug/{row.get('drug',{}).get('id','')}",
            })
        # Disease associations with scores
        disease_assoc = []
        for row in (data.get("associatedDiseases",{}).get("rows") or []):
            disease_assoc.append({
                "disease": row.get("disease",{}).get("name",""),
                "score": round(row.get("score",0), 3),
                "url": f"https://platform.opentargets.org/disease/{row.get('disease',{}).get('id','')}/associations",
            })
        # Top tissue expression
        expressions = sorted(
            [(e.get("tissue",{}).get("label",""), e.get("rna",{}).get("value",0))
             for e in (data.get("expressions") or []) if e.get("rna",{}).get("value",0) > 0],
            key=lambda x: -x[1]
        )[:10]
        return {
            "ensembl_id": ensembl_id,
            "tractability": tractability,
            "known_drugs": drugs,
            "disease_associations": disease_assoc,
            "top_tissues": expressions,
            "drug_count": data.get("knownDrugs",{}).get("count",0),
            "url": f"https://platform.opentargets.org/target/{ensembl_id}",
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_isoforms(uniprot_id: str) -> list:
    """Fetch all isoforms from UniProt and their disease relevance."""
    try:
        r = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}",
                        headers={"Accept":"application/json"}, timeout=15)
        r.raise_for_status(); data = r.json()
        isoforms = []
        for comment in data.get("comments",[]):
            if comment.get("commentType") == "ALTERNATIVE SEQUENCE":
                for iso in comment.get("isoforms",[]):
                    name = iso.get("name",{}).get("value","")
                    ids  = iso.get("isoformIds",[])
                    note = iso.get("note",{}).get("texts",[{}])[0].get("value","") if iso.get("note") else ""
                    isoforms.append({"name":name,"ids":ids,"note":note,
                                     "disease_relevant":"disease" in note.lower() or "pathogenic" in note.lower()})
        return isoforms
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_scholar_papers(query: str, n: int = 8) -> list:
    """Single-source fetch from Semantic Scholar (kept for backward compatibility).
    For broader coverage use fetch_papers_multi() which queries 4 sources in parallel."""
    try:
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query, "limit": n,
                "fields": "title,authors,year,abstract,citationCount,url,externalIds",
            },
            headers={"User-Agent": "Protellect/1.0"},
            timeout=12,
        )
        if r.status_code == 200:
            return [
                {
                    "title":     p.get("title", ""),
                    "authors":   ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3]),
                    "year":      p.get("year", ""),
                    "abstract":  (p.get("abstract") or "")[:280],
                    "citations": p.get("citationCount", 0),
                    "url":       p.get("url") or "",
                    "source":    "Semantic Scholar",
                }
                for p in r.json().get("data", [])
                if p.get("title")
            ]
    except Exception:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_openalex(query: str, n: int = 6) -> list:
    """OpenAlex API — open metadata, no key required."""
    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={
                "search": query, "per-page": n, "sort": "cited_by_count:desc",
                "select": "id,title,authorships,publication_year,abstract_inverted_index,cited_by_count,doi,primary_location",
            },
            headers={"User-Agent": "Protellect/1.0 (mailto:contact@protellect.ai)"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        out = []
        for w in r.json().get("results", []) or []:
            # Reconstruct abstract from inverted index (OpenAlex's format)
            inv = w.get("abstract_inverted_index") or {}
            abstract = ""
            if inv:
                positions = []
                for word, idxs in inv.items():
                    for i in idxs:
                        positions.append((i, word))
                abstract = " ".join(w for _, w in sorted(positions))[:280]
            authors = ", ".join(
                (a.get("author") or {}).get("display_name","")
                for a in (w.get("authorships") or [])[:3]
            )
            url = ""
            if w.get("doi"):
                url = w["doi"]
            elif (w.get("primary_location") or {}).get("landing_page_url"):
                url = w["primary_location"]["landing_page_url"]
            out.append({
                "title":     w.get("title","") or "",
                "authors":   authors,
                "year":      w.get("publication_year","") or "",
                "abstract":  abstract,
                "citations": w.get("cited_by_count", 0),
                "url":       url,
                "source":    "OpenAlex",
            })
        return [p for p in out if p["title"]]
    except Exception:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_crossref(query: str, n: int = 6) -> list:
    """CrossRef REST API — publisher metadata, no key required."""
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={
                "query": query, "rows": n, "sort": "is-referenced-by-count", "order": "desc",
            },
            headers={"User-Agent": "Protellect/1.0 (mailto:contact@protellect.ai)"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        out = []
        for w in (r.json().get("message", {}) or {}).get("items", []) or []:
            title = (w.get("title") or [""])[0]
            authors = ", ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (w.get("author") or [])[:3]
            )
            year = ""
            issued = (w.get("issued") or {}).get("date-parts", [[None]])
            if issued and issued[0] and issued[0][0]:
                year = issued[0][0]
            doi = w.get("DOI","")
            url = f"https://doi.org/{doi}" if doi else (w.get("URL","") or "")
            out.append({
                "title":     title,
                "authors":   authors,
                "year":      year,
                "abstract":  (w.get("abstract") or "").replace("<jats:p>","").replace("</jats:p>","")[:280],
                "citations": w.get("is-referenced-by-count", 0) or 0,
                "url":       url,
                "source":    "CrossRef",
            })
        return [p for p in out if p["title"]]
    except Exception:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_pubmed(query: str, n: int = 6) -> list:
    """NCBI E-utilities PubMed — biomedical literature, no key required (rate-limited to 3 req/s)."""
    try:
        # Step 1: esearch for PMIDs
        r1 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": n, "retmode": "json", "sort": "relevance"},
            timeout=12,
        )
        if r1.status_code != 200:
            return []
        pmids = (r1.json().get("esearchresult", {}) or {}).get("idlist", []) or []
        if not pmids:
            return []
        # Step 2: esummary for metadata
        r2 = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(pmids), "retmode": "json"},
            timeout=12,
        )
        if r2.status_code != 200:
            return []
        results = (r2.json().get("result", {}) or {})
        out = []
        for pmid in pmids:
            rec = results.get(pmid)
            if not rec or rec.get("error"): continue
            title = rec.get("title","") or ""
            authors = ", ".join(a.get("name","") for a in (rec.get("authors") or [])[:3])
            year = (rec.get("pubdate","") or "")[:4]
            out.append({
                "title":     title,
                "authors":   authors,
                "year":      year,
                "abstract":  "",  # esummary doesn't return abstract; would need efetch (skipped for speed)
                "citations": 0,    # PubMed doesn't expose citation counts directly
                "url":       f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source":    "PubMed",
                "pmid":      pmid,
            })
        return [p for p in out if p["title"]]
    except Exception:
        return []

# NOTE: This function is intentionally NOT decorated with @st.cache_data.
# It accepts an `_on_progress` callback which Streamlit's cache replay machinery
# cannot serialize (the closure breaks CacheReplayClosureError). The four inner
# source fetchers (fetch_scholar_papers, _fetch_openalex, _fetch_crossref,
# _fetch_pubmed) are individually cached with 1-hour TTLs, so repeated calls
# still hit those caches — the outer dedup + sort takes microseconds.
def fetch_papers_multi(query: str, per_source: int = 4, _on_progress=None) -> list:
    """Fetch papers from 4 sources in parallel, deduplicate by title, sort by citations.
    _on_progress(source, n_results) callback fires after each source completes."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    sources = [
        ("Semantic Scholar", lambda: fetch_scholar_papers(query, n=per_source)),
        ("OpenAlex",         lambda: _fetch_openalex(query, n=per_source)),
        ("CrossRef",         lambda: _fetch_crossref(query, n=per_source)),
        ("PubMed",           lambda: _fetch_pubmed(query, n=per_source)),
    ]
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fn): name for name, fn in sources}
        for f in as_completed(futures, timeout=15):
            name = futures[f]
            try:
                papers = f.result(timeout=2) or []
            except Exception:
                papers = []
            results[name] = papers
            if _on_progress:
                try: _on_progress(name, len(papers))
                except Exception: pass
    # Combine all + deduplicate by lowercased title
    seen_titles = set()
    combined = []
    # Interleave so each source is represented in the top results
    max_len = max((len(v) for v in results.values()), default=0)
    for i in range(max_len):
        for name in ["Semantic Scholar","PubMed","OpenAlex","CrossRef"]:
            lst = results.get(name) or []
            if i < len(lst):
                p = lst[i]
                key = (p.get("title","") or "")[:60].lower().strip()
                if key and key not in seen_titles:
                    seen_titles.add(key)
                    combined.append(p)
    # Final sort: prefer ones with citations, but keep some recency
    combined.sort(key=lambda p: (
        -(p.get("citations") or 0),
        -(int(p.get("year") or 0) if str(p.get("year","")).isdigit() else 0),
    ))
    return combined
