"""Evidence-backed analysis. Pure functions: Bundle in, ranked Claims out. Nothing here touches Streamlit or the network.

Every Claim names its proofs. Rules are stated with their basis and cited. Weights in the 'possibility' score are DESIGN
CHOICES (shown in full), not fitted parameters; the score is a prioritisation aid, not a probability.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional

from .adapters import Bundle, LOF_TYPES, Variant, mean_plddt, plddt_at
from .evidence import Claim, Proof

NOISE = {"", "not provided", "not specified", "see cases", "none provided", "not applicable"}
STOP = {"the", "of", "and", "type", "syndrome", "disease", "disorder", "susceptibility", "to", "with", "due"}
CITE = {
    "acmg": Proof("ACMG/AMP guidelines", "Richards et al. 2015, Genet Med 17:405-424", "https://doi.org/10.1038/gim.2015.30", "literature"),
    "lek": Proof("gnomAD constraint", "Lek et al. 2016, Nature 536:285 (pLI >= 0.9 = LoF intolerant)", "https://doi.org/10.1038/nature19057", "literature"),
    "karcz": Proof("gnomAD constraint", "Karczewski et al. 2020, Nature 581:434 (LOEUF)", "https://gnomad.broadinstitute.org/help/constraint", "literature"),
    "am": Proof("AlphaMissense", "Cheng et al. 2023, Science 381:eadg7492 (>0.564 likely pathogenic, <0.34 likely benign)", "https://doi.org/10.1126/science.adg7492", "literature"),
    "review": Proof("ClinVar review status", "NCBI definition of review-status stars", "https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/", "literature"),
}


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1}


def _same_condition(a: str, b: str) -> bool:
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6


def _clinvar_url(b: Bundle) -> str:
    return f"https://www.ncbi.nlm.nih.gov/clinvar/?term={b.gene}%5Bgene%5D"


def _uniprot_url(b: Bundle) -> str:
    return f"https://www.uniprot.org/uniprotkb/{b.uid}/entry" if b.uid else "https://www.uniprot.org/"


def _conditions(v: Variant) -> List[str]:
    return [c.strip() for c in re.split(r"[|;]", v.condition) if c.strip().lower() not in NOISE]


# ------------------------------------------------------------------------------------------------ diseases
def rank_diseases(b: Bundle, ctx=None) -> List[Claim]:
    entries: List[dict] = []
    for d in b.diseases:
        entries.append({"name": d.name, "inh": d.inheritance, "omim": d.omim, "uniprot": True, "variants": []})
    for v in b.plp:
        for cond in _conditions(v):
            hit = next((e for e in entries if _same_condition(e["name"], cond)), None)
            if hit is None:
                hit = {"name": cond, "inh": "", "omim": "", "uniprot": False, "variants": []}
                entries.append(hit)
            hit["variants"].append(v)
    out = []
    for e in entries:
        proofs, vs = [], e["variants"]
        if e["uniprot"]:
            proofs.append(Proof("UniProt", f"Disease annotation on {b.gene} ({b.uid})" + (f", MIM:{e['omim']}" if e["omim"] else ""), _uniprot_url(b)))
        if e["omim"]:
            proofs.append(Proof("OMIM", f"MIM:{e['omim']}", f"https://omim.org/entry/{e['omim']}"))
        stars = max((v.stars for v in vs), default=0)
        if vs:
            ex = ", ".join(v.name.split("(")[-1].rstrip(")")[:24] for v in vs[:2])
            proofs.append(Proof("ClinVar", f"{len(vs)} pathogenic/likely pathogenic variant(s) listing this condition; best review {stars} star(s); e.g. {ex}",
                                vs[0].url or _clinvar_url(b)))
        if not proofs:
            continue
        score = (2.0 if e["uniprot"] else 0.0) + min(3.0, math.log2(1 + len(vs))) + 0.5 * stars
        flag = ""
        if ctx is not None and getattr(ctx, "disease", "") and _same_condition(ctx.disease, e["name"]):
            score += 1.5
            flag = "matches your disease context"
        out.append(Claim(text=e["name"] + (f" ({e['inh']})" if e["inh"] else ""), proofs=proofs, kind="data", score=score,
                         tags={"n_supporting": len(vs) or 1, "max_stars": stars, "domain": "clinvar" if vs else "uniprot", "context_flag": flag,
                               "inheritance": e["inh"], "disease": e["name"]}))
    return sorted(out, key=lambda c: -c.score)


# ------------------------------------------------------------------------------------------------ defects
def defect_claims(b: Bundle) -> List[Claim]:
    plp = b.plp
    if not plp:
        return []
    n = len(plp)
    cons = Counter(v.consequence for v in plp)
    lof = sum(cons[k] for k in LOF_TYPES)
    mis = cons.get("missense", 0)
    cv_proof = Proof("ClinVar", f"{n} germline pathogenic/likely-pathogenic variants for {b.gene}", _clinvar_url(b))
    out = [Claim(text=f"{n} pathogenic/likely-pathogenic variants: {lof} loss-of-function type (nonsense/frameshift/splice), {mis} missense, {n-lof-mis} other.",
                 proofs=[cv_proof], kind="data", score=n, tags={"n_supporting": n, "max_stars": max(v.stars for v in plp), "domain": "clinvar"})]
    pli = b.constraint.get("pLI")
    if lof / n >= 0.5 and pli is not None and pli >= 0.9:
        out.append(Claim(text="Loss of function is the likely disease mechanism.", kind="inference", score=n + 1,
                         basis="Most pathogenic variants truncate the protein and the gene is intolerant of LoF: the pattern expected for haploinsufficiency (Lek 2016).",
                         proofs=[cv_proof, Proof("gnomAD", f"pLI = {pli:.2f}", "https://gnomad.broadinstitute.org/gene/" + b.gene), CITE["lek"]],
                         tags={"mechanism": "loss-of-function", "n_supporting": n, "max_stars": max(v.stars for v in plp), "domain": "clinvar"}))
    elif mis / n >= 0.7:
        out.append(Claim(text="Pathogenic variants are mostly missense: loss- versus gain-of-function cannot be decided from these data.", kind="rule", score=n,
                         basis="Missense-dominant spectra are compatible with loss of function, gain of function or dominant-negative effects; functional assays are needed to distinguish them (ACMG PS3).",
                         proofs=[cv_proof, CITE["acmg"]], tags={"n_supporting": n, "domain": "clinvar", "max_stars": max(v.stars for v in plp)}))
    for d in b.domains:
        k = sum(1 for v in plp if v.pos and d["start"] <= v.pos <= d["end"])
        if k >= 3 and k / n >= 0.2:
            out.append(Claim(text=f"{k} of {n} pathogenic variants fall in {d['desc'] or d['type']} (residues {d['start']}-{d['end']}).", kind="data", score=k,
                             proofs=[cv_proof, Proof("UniProt", f"{d['type']} {d['start']}-{d['end']} {d['desc']}", _uniprot_url(b))],
                             tags={"n_supporting": k, "domain": "clinvar", "max_stars": max(v.stars for v in plp)}))
    for h in sorted(b.hotspots, key=lambda x: -x.fold)[:3]:
        if h.count >= 3 and h.fold >= 2:
            out.append(Claim(text=f"Variant hotspot at residues {h.start}-{h.end}: {h.count} variants, {h.fold:.1f}x enriched over a uniform spread.", kind="data", score=h.count,
                             proofs=[Proof("ClinVar", f"{h.count} variants clustered in {h.start}-{h.end} (clustering computed by Protellect)", _clinvar_url(b))],
                             tags={"n_supporting": h.count, "domain": "clinvar", "max_stars": max(v.stars for v in plp)}))
    return out


# ------------------------------------------------------------------------------------------------ possibility
def possibility(b: Bundle) -> dict:
    comps: List[dict] = []

    def add(name, available, points, max_points, value, rule, proof):
        comps.append({"name": name, "available": available, "points": points if available else 0, "max": max_points, "value": value, "rule": rule, "proof": proof})

    pli, loeuf = b.constraint.get("pLI"), b.constraint.get("oe_lof_upper")
    have = pli is not None or loeuf is not None
    pts = 15 if ((pli or 0) >= 0.9 or (loeuf is not None and loeuf < 0.35)) else 8 if (loeuf is not None and loeuf < 0.6) else 0
    add("Genetic constraint", have, pts, 15, f"pLI {pli if pli is not None else 'n/a'}, LOEUF {loeuf if loeuf is not None else 'n/a'}",
        "15 pts if pLI >= 0.9 or LOEUF < 0.35; 8 pts if LOEUF < 0.6", Proof("gnomAD", "constraint metrics", "https://gnomad.broadinstitute.org/gene/" + b.gene))
    n_plp, n_all = len(b.plp), len(b.variants)
    add("Clinical variant burden", n_all >= 5, 20 if n_plp >= 20 else 12 if n_plp >= 5 else 6 if n_plp >= 1 else 0, 20,
        f"{n_plp} P/LP of {n_all} ClinVar entries", "20 pts if >= 20 P/LP; 12 if >= 5; 6 if >= 1", Proof("ClinVar", f"{n_plp} P/LP of {n_all}", _clinvar_url(b)))
    stars = max((v.stars for v in b.plp), default=0)
    add("Review quality", n_plp > 0, 10 if stars >= 2 else 5 if stars == 1 else 0, 10, f"best P/LP review {stars} star(s)", "10 pts if >= 2 stars; 5 if 1", CITE["review"])
    cg = b.clingen.lower()
    add("Gene-disease validity", bool(b.clingen), 15 if ("definitive" in cg or "strong" in cg) else 8 if "moderate" in cg else 3 if "limited" in cg else 0, 15,
        b.clingen or "n/a", "15 pts definitive/strong; 8 moderate; 3 limited", Proof("ClinGen", b.clingen or "no classification", "https://search.clinicalgenome.org/kb/genes"))
    add("Disease annotation", True, 10 if b.diseases else 0, 10, f"{len(b.diseases)} disease(s) annotated", "10 pts if >= 1 UniProt disease annotation", Proof("UniProt", "disease comments", _uniprot_url(b)))
    pl = mean_plddt(b.pdb)
    add("Structural confidence", pl is not None, 5 if (pl or 0) >= 70 else 2, 5, f"mean pLDDT {pl:.0f}" if pl else "no structure",
        "5 pts if mean pLDDT >= 70; 2 otherwise", Proof("AlphaFold", "mean pLDDT from the structure file", "https://alphafold.ebi.ac.uk/entry/" + b.uid))
    have_tr = bool(b.tractability)
    add("Tractability", have_tr, 10 if (b.tractability.get("Small molecule") or b.tractability.get("Antibody")) else 0, 10,
        ", ".join(k for k, v in b.tractability.items() if v) or "none flagged", "10 pts if small-molecule or antibody tractable", Proof("Open Targets", "tractability", "https://platform.opentargets.org/target"))
    add("Existing drugs / trials", True, 10 if (b.drugs or b.n_known_drugs or b.trials) else 0, 10, f"{len(b.drugs)+b.n_known_drugs} drug record(s), {len(b.trials)} trial(s)",
        "10 pts if any drug-gene record or trial", Proof("DGIdb / Open Targets / ClinicalTrials.gov", "drug and trial records"))
    add("Literature depth", True, 5 if len(b.papers) >= 10 else 0, 5, f"{len(b.papers)} record(s)", "5 pts if >= 10 literature records", Proof("PubMed / Europe PMC", "retrieved records"))
    avail = [c for c in comps if c["available"]]
    mx = sum(c["max"] for c in avail)
    pct = round(100 * sum(c["points"] for c in avail) / mx) if mx else 0
    level = "INSUFFICIENT DATA" if len(avail) < 4 else "HIGH" if pct >= 65 else "MODERATE" if pct >= 40 else "LOW"
    return {"level": level, "pct": pct, "coverage": f"{len(avail)} of {len(comps)} evidence types available", "components": comps,
            "note": "Evidence-weighted prioritisation aid. The weights are design choices shown above, not fitted parameters, and the score is not a probability of success."}


# ------------------------------------------------------------------------------------------------ strategy
def strategy_options(b: Bundle, defects: List[Claim], orphan: bool = False) -> List[Claim]:
    out: List[Claim] = []
    plp = b.plp
    mech = next((c for c in defects if c.tags.get("mechanism") == "loss-of-function"), None)
    cv = Proof("ClinVar", f"{len(plp)} P/LP of {len(b.variants)} variants", _clinvar_url(b))
    mod = ", ".join(k.lower() for k, v in b.tractability.items() if v)
    if mech:
        out.append(Claim(text="Restore or augment function", kind="rule", score=3,
                         basis="For loss-of-function disease the standard strategies increase activity: agonists or positive allosteric modulators (GPCRs and receptors), gene replacement, or pharmacological chaperones where variants destabilise folding.",
                         proofs=[p for p in mech.proofs if p.kind != "literature"][:2] + [Proof("Strategy rule", "LoF -> restore function", kind="rule")],
                         how=["Pick a functional assay that reports activity (signalling readout for a GPCR) and confirm WT vs top pathogenic variants differ (ACMG PS3).",
                              "Test whether activity is rescued by an agonist, PAM or chaperone in cells expressing the variants.",
                              "Check feasibility of delivery to the affected tissue before choosing gene versus small-molecule routes."]))
    elif plp and len(plp) / max(1, len(b.variants)) >= 0.15:
        out.append(Claim(text="Establish the mechanism first (loss vs gain of function)", kind="rule", score=2.5,
                         basis="The variant spectrum does not by itself identify the mechanism, and the right drug direction (activate vs inhibit) depends on it.",
                         proofs=[cv, Proof("Strategy rule", "mechanism unresolved -> functional assays first", kind="rule")],
                         how=["Run a quantitative functional assay on the 3-5 best-reviewed pathogenic missense variants and compare with WT and a benign control.",
                              "Decide direction (activate vs inhibit) only after the assay result."]))
    if orphan:
        out.append(Claim(text="Deorphanisation campaign", kind="rule", score=2.8,
                         basis="No confirmed ligand is on record for this receptor, so the first experiment is to find what activates it, guided by the ranked hypotheses.",
                         proofs=[Proof("Receptor registry", f"{b.gene} listed as an orphan GPCR", "https://www.guidetopharmacology.org/"), Proof("Strategy rule", "orphan -> ligand screen", kind="rule")],
                         how=["Screen the top-ranked ligand class from the hypothesis list in receptor-expressing cells with empty-vector controls.",
                              "Confirm hits with an orthogonal readout, then dose-response."]))
    unc = sum(v.significance == "uncertain" for v in b.variants)
    if b.variants and unc / len(b.variants) >= 0.4 and unc >= 5:
        out.append(Claim(text="Reclassify variants of uncertain significance", kind="rule", score=2,
                         basis="A large share of entries are VUS; functional evidence is what moves them under ACMG criteria.",
                         proofs=[Proof("ClinVar", f"{unc} of {len(b.variants)} entries are uncertain significance", _clinvar_url(b)), CITE["acmg"]],
                         how=["Prioritise VUS with AlphaMissense > 0.564 inside hotspots for a multiplexed functional assay.", "Submit results back to ClinVar with the assay as evidence."]))
    if mod or b.drugs:
        out.append(Claim(text="Build on existing chemistry", kind="rule", score=1.5,
                         basis="Open Targets or drug-gene records show prior chemical matter, which de-risks assay and tool-compound choice.",
                         proofs=[p for p in ([Proof("Open Targets", f"tractability: {mod}", "https://platform.opentargets.org/target")] if mod else []) +
                                 ([Proof("DGIdb", f"{len(b.drugs)} drug-gene interaction(s)", "https://www.dgidb.org/")] if b.drugs else [])] + [Proof("Strategy rule", "prior chemistry -> start from known ligands", kind="rule")],
                         how=["Use the known ligands as positive controls and to calibrate the assay window."]))
    return sorted(out, key=lambda c: -c.score)


# ------------------------------------------------------------------------------------------------ thresholds
def genetic_thresholds(b: Bundle) -> List[dict]:
    c = b.constraint
    rows = []

    def row(metric, val, rule, met, meaning, proof):
        rows.append({"metric": metric, "value": "n/a" if val is None else (f"{val:.3g}" if isinstance(val, float) else str(val)), "threshold": rule,
                     "status": "unavailable" if val is None else ("meets" if met else "does not meet"), "meaning": meaning, "proof": proof})

    row("pLI", c.get("pLI"), ">= 0.9", (c.get("pLI") or 0) >= 0.9, "Gene is intolerant of loss of function.", CITE["lek"])
    row("LOEUF (oe_lof_upper)", c.get("oe_lof_upper"), "< 0.35 (gnomAD v2.1) or < 0.6 (gnomAD v4)", (c.get("oe_lof_upper") if c.get("oe_lof_upper") is not None else 9) < 0.6,
        "Lower means fewer LoF variants than expected: stronger constraint.", CITE["karcz"])
    row("Missense Z", c.get("mis_z"), ">= 3.09", (c.get("mis_z") or 0) >= 3.09, "Fewer missense variants than expected: missense-constrained.",
        Proof("gnomAD constraint", "Samocha et al. 2014 / Lek et al. 2016 (Z >= 3.09)", "https://doi.org/10.1038/ng.3050", "literature"))
    plp = b.plp
    row("Best ClinVar review (P/LP)", max((v.stars for v in plp), default=None), ">= 2 stars", max((v.stars for v in plp), default=0) >= 2,
        "Two or more stars: multiple submitters without conflict, or better.", CITE["review"])
    am_hi = [v for v in b.variants if v.am_score is not None and v.am_score > 0.564]
    row("Variants above the AlphaMissense pathogenic cutoff", len(am_hi) if b.am else None, "AlphaMissense > 0.564", len(am_hi) > 0,
        "Predicted likely pathogenic by AlphaMissense (a prediction, not a measurement).", CITE["am"])
    row("Population frequency rule (ACMG BA1)", "see variant", "allele frequency > 5%", False, "A variant this common is stand-alone evidence of benign; checked per variant, not per gene.", CITE["acmg"])
    return rows


# ------------------------------------------------------------------------------------------------ body systems
SYSTEMS = {
    "Nervous system": ["brain", "neuron", "cerebell", "cortex", "hippocamp", "habenula", "spinal", "nerve", "neuro", "epilep", "ataxia", "autism", "intellectual", "parkinson", "alzheimer", "dementia", "schizo", "striat"],
    "Cardiovascular": ["heart", "cardiac", "cardiomyopathy", "arrhythm", "vascular", "artery", "aort", "endotheli", "long qt", "brugada", "hypertension"],
    "Endocrine & metabolic": ["pancrea", "islet", "insulin", "diabet", "thyroid", "adrenal", "pituitar", "obesity", "metabolic", "lipid", "cholesterol", "adipo"],
    "Immune & blood": ["immune", "lymph", "t cell", "b cell", "macrophage", "neutrophil", "bone marrow", "blood", "anemia", "thrombo", "hemophil", "immunodeficien"],
    "Digestive & liver": ["liver", "hepat", "intestin", "colon", "gut", "gastric", "stomach", "bowel", "colitis", "crohn", "esophag"],
    "Respiratory": ["lung", "pulmon", "airway", "bronch", "cystic fibrosis", "asthma"],
    "Renal & urinary": ["kidney", "renal", "nephr", "bladder", "urinary"],
    "Musculoskeletal": ["muscle", "myopath", "dystroph", "bone", "skelet", "osteo", "cartilage"],
    "Reproductive": ["testis", "ovary", "uter", "placenta", "prostate", "breast", "fertility", "hypogonad"],
    "Skin & connective tissue": ["skin", "keratin", "epiderm", "dermat", "connective tissue", "ehlers"],
    "Eye & ear": ["eye", "retina", "optic", "cochlea", "hearing", "deaf", "macular"],
    "Cancer predisposition": ["cancer", "carcinoma", "tumor", "tumour", "neoplas", "sarcoma", "leukemia", "lymphoma", "melanoma", "li-fraumeni"],
}


def _systems_in(text: str) -> Dict[str, str]:
    t = text.lower()
    return {s: kw for s, kws in SYSTEMS.items() for kw in kws if kw in t}


def body_systems(b: Bundle, diseases: Optional[List[Claim]] = None) -> List[Claim]:
    ev: Dict[str, dict] = {}
    for s, kw in _systems_in(b.tissue_text).items():
        ev.setdefault(s, {"tissue": [], "disease": []})["tissue"].append(kw)
    for d in diseases or []:
        for s, kw in _systems_in(d.tags.get("disease", d.text)).items():
            ev.setdefault(s, {"tissue": [], "disease": []})["disease"].append((d.tags.get("disease", d.text), kw, d))
    out = []
    for s, e in ev.items():
        proofs, parts = [], []
        if e["tissue"]:
            proofs.append(Proof("UniProt", f"Tissue specificity: \"{b.tissue_text[:160]}\"", _uniprot_url(b)))
            parts.append("expressed there")
        for name, kw, d in e["disease"][:3]:
            proofs += [p for p in d.proofs if p.kind == "data"][:1]
            parts.append(f"linked to {name}")
        proofs.append(Proof("Mapping rule", f"keyword match to '{s}' ({', '.join(sorted({e['tissue'][0]} if e['tissue'] else {e['disease'][0][1]}))})", kind="rule"))
        out.append(Claim(text=f"{s}: " + "; ".join(dict.fromkeys(parts)), proofs=proofs, kind="rule", score=len(e["tissue"]) + 2 * len(e["disease"]),
                         basis="Organ system assigned by keyword match on the UniProt tissue text and on disease names; it is a lookup, not a measurement.",
                         tags={"system": s, "n_supporting": len(e["tissue"]) + len(e["disease"]), "has_tissue": bool(e["tissue"]), "n_disease": len(e["disease"])}))
    return sorted(out, key=lambda c: -c.score)


# ------------------------------------------------------------------------------------------------ variants
def rank_variants(b: Bundle) -> List[Variant]:
    order = {"pathogenic": 0, "likely pathogenic": 1, "conflicting": 2, "uncertain": 3, "other": 4, "likely benign": 5, "benign": 6}
    return sorted(b.variants, key=lambda v: (order.get(v.significance, 4), -v.stars, -(v.ml_score or 0), -(v.am_score or 0)))


def variant_plan(v: Variant, b: Bundle) -> List[dict]:
    """Ordered steps for working one variant. Each carries its basis so none is an unexplained instruction."""
    steps = [{"step": "Confirm the classification", "do": f"Open the ClinVar record and read the submitter evidence (review status: {v.review or 'not recorded'}, {v.stars} star(s)).",
              "basis": "Star level shows how independent and expert the interpretation is.", "url": v.url or _clinvar_url(b)}]
    steps.append({"step": "Check population frequency", "do": "Look the variant up in gnomAD. A frequency above 5% is stand-alone evidence it is benign; very low or absent supports pathogenicity.",
                  "basis": "ACMG BA1 / PM2 (Richards 2015).", "url": f"https://gnomad.broadinstitute.org/gene/{b.gene}"})
    pl = plddt_at(b.pdb, v.pos)
    dom = b.domain_at(v.pos)
    steps.append({"step": "Weigh predicted impact", "do": "AlphaMissense " + (f"{v.am_score:.2f} ({v.am_class})" if v.am_score is not None else "not available")
                  + (f"; AlphaFold confidence at residue {v.pos}: pLDDT {pl:.0f}" if pl is not None else "") + (f"; sits in {dom}" if dom else "") + ". Predictions support, but do not replace, functional evidence.",
                  "basis": "ACMG PP3 allows computational evidence at supporting strength only.", "url": "https://alphamissense.hegelab.org/"})
    if v.consequence in LOF_TYPES:
        steps.append({"step": "Test expression", "do": "Measure transcript (RT-qPCR) and protein (Western) in patient-derived or edited cells to see whether the truncated product is lost.",
                      "basis": "Truncating variants usually act by reducing protein; nonsense-mediated decay is the expected route.", "url": ""})
    else:
        kind = ("Measure surface expression (flow cytometry or ELISA) and signalling (Ca2+, cAMP or beta-arrestin) against WT" if b.is_gpcr
                else "Measure protein stability/expression and the protein's own activity against WT")
        steps.append({"step": "Run a functional assay", "do": kind + ", with a known benign variant as negative control.", "basis": "Well-established functional studies are ACMG PS3/BS3 evidence.",
                      "url": "https://doi.org/10.1038/gim.2015.30"})
    steps.append({"step": "Reclassify and share", "do": "Combine the evidence under ACMG/AMP criteria and submit the result and assay to ClinVar.", "basis": "Closes the loop for other labs.", "url": "https://www.ncbi.nlm.nih.gov/clinvar/docs/submit/"})
    return steps
