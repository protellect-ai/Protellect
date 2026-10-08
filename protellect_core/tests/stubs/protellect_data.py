"""TEST STAND-IN for the real protellect_data.py (not shipped). Realistic SHAPES, fictional-ish values, so the app's own
pipeline runs end to end the way it does with real data (notably AlphaMissense as position -> aa -> {score, class})."""
import functools, random

def _cached(fn):
    @functools.wraps(fn)
    def w(*a, **k): return fn(*a, **k)
    w.clear = lambda *a, **k: None
    return w

_AA = "ACDEFGHIKLMNPQRSTVWY"
_UNI = {
    "TP53": dict(acc="P04637", name="Cellular tumor antigen p53", length=393, gpcr=False,
                 tissue="Ubiquitously expressed. Isoforms are expressed in a wide range of normal tissues.",
                 diseases=[("Li-Fraumeni syndrome", "LFS", "151623", "Autosomal dominant"), ("Hepatocellular carcinoma", "HCC", "114550", "")]),
    "GPR151": dict(acc="Q8TDV0", name="Probable G-protein coupled receptor 151", length=419, gpcr=True,
                   tissue="Expressed in the brain, habenula.", diseases=[]),
    "FFAR1": dict(acc="O14842", name="Free fatty acid receptor 1", length=300, gpcr=True,
                  tissue="Expressed in pancreatic islets (beta cells) and brain.", diseases=[]),
}

def _entry(gene):
    u = _UNI.get(gene.upper())
    if not u: return {}
    comments = [{"commentType": "TISSUE SPECIFICITY", "texts": [{"value": u["tissue"]}]},
                {"commentType": "SUBCELLULAR LOCATION", "subcellularLocations": [{"location": {"value": "Cell membrane" if u["gpcr"] else "Nucleus"}}]}]
    for n, ac, mim, inh in u["diseases"]:
        comments.append({"commentType": "DISEASE", "disease": {"diseaseId": n, "diseaseAcronym": ac, "description": f"{n}. {inh}".strip(),
                         "diseaseCrossReference": {"database": "MIM", "id": mim}}, "note": {"texts": [{"value": inh}]}})
    feats = [{"type": "Domain", "description": "Transmembrane helix 6" if u["gpcr"] else "p53 DNA-binding", "location": {"start": {"value": 102}, "end": {"value": 292}}}]
    return {"organism": {"scientificName": "Homo sapiens", "commonName": "Human", "taxonId": 9606}, "primaryAccession": u["acc"],
            "uniProtkbId": f"{gene.upper()}_HUMAN", "genes": [{"geneName": {"value": gene.upper()}}],
            "proteinDescription": {"recommendedName": {"fullName": {"value": u["name"]}}},
            "sequence": {"value": "".join(random.Random(1).choice(_AA) for _ in range(u["length"])), "length": u["length"]},
            "comments": comments, "features": feats, "keywords": ([{"name": "G-protein coupled receptor"}] if u["gpcr"] else [{"name": "Tumor suppressor"}]),
            "uniProtKBCrossReferences": []}

@_cached
def fetch_uniprot(q, *a, **k): return _entry(str(q))

@_cached
def fetch_clinvar(gene, max_v=150, *a, **k):
    r = random.Random(7); L = _UNI.get(str(gene).upper(), {}).get("length", 300); out = []
    spec = [("Pathogenic", 5, "criteria provided, multiple submitters, no conflicts", 45), ("Likely pathogenic", 4, "criteria provided, single submitter", 25),
            ("Uncertain significance", 2, "criteria provided, single submitter", 60), ("Benign", 0, "criteria provided, multiple submitters, no conflicts", 20)]
    i = 0
    for sig, score, rev, n in spec:
        for _ in range(n):
            pos = r.randint(100, 290) if score >= 4 else r.randint(1, L); i += 1
            out.append({"variant_name": f"NM_000546.6(GENE):c.{pos*3}C>T (p.Arg{pos}Trp)", "title": f"p.Arg{pos}Trp", "sig": sig, "review": rev,
                        "condition": "Li-Fraumeni syndrome" if score >= 4 else "not provided", "start": pos, "position": pos, "score": score,
                        "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{10000+i}/", "somatic": False})
    return {"variants": out[:max_v if isinstance(max_v, int) else 150]}

@_cached
def fetch_gnomad(*a, **k): return {"pLI": 0.0, "oe_lof": 0.31, "oe_lof_upper": 0.52, "mis_z": 3.4}
@_cached
def fetch_string_interactions(*a, **k): return [{"partner": p, "score": s, "url": f"https://string-db.org/network/{p}"} for p, s in
                                                  (("MDM2", .999), ("EP300", .99), ("ATM", .98), ("CHEK2", .97), ("BRCA1", .93), ("CDKN1A", .92))]
@_cached
def fetch_pubmed_abstracts(*a, **k): return [{"pmid": "11111111", "title": "A study of p53", "year": 2023, "abstract": "...", "authors": "Doe J, Roe R", "journal": "Nature", "url": "https://pubmed.ncbi.nlm.nih.gov/11111111/"}]
@_cached
def fetch_pdb(*a, **k): return ""
@_cached
def fetch_papers(*a, **k): return []
@_cached
def fetch_papers_multi(*a, **k): return []
@_cached
def fetch_opentargets(*a, **k):
    return {"tractability": {"Small molecule": "Phase 2 clinical precedence", "Antibody": "Unknown", "PROTAC": "Unknown"},
            "known_drugs": [{"name": "ADVEXIN", "mechanism": "Gene therapy", "indication": "Head and neck cancer", "phase": 3, "url": "https://platform.opentargets.org/"}]}
@_cached
def fetch_ncbi_gene(*a, **k): return {"summary": "Stand-in gene summary."}
@_cached
def fetch_isoforms(*a, **k): return []
@_cached
def fetch_gpcrdb(*a, **k): return {}
@_cached
def fetch_disease_proteins(*a, **k): return []
@_cached
def fetch_dgidb(*a, **k): return [{"drug": "NUTLIN-3", "type": "inhibitor", "sources": "ChEMBL", "url": "https://www.dgidb.org/"}]
@_cached
def fetch_clinical_trials(*a, **k): return [{"nct": "NCT00000001", "title": "Stand-in trial", "phase": "Phase 2", "status": "Recruiting", "url": "https://clinicaltrials.gov/"}]
@_cached
def fetch_clingen(*a, **k): return {"classification": "Definitive"}
@_cached
def fetch_alphamissense(*a, **k):
    r = random.Random(3)
    return {p: {aa: {"score": round(r.random(), 3), "class": r.choice(["pathogenic", "ambiguous", "benign"])} for aa in r.sample(_AA, 5)} for p in range(1, 394)}
