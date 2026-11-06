"""Cross-compare what the literature says at each level of evidence (cell, animal, human genetics, human clinical) with human genetic evidence from Open Targets.

What this is, and is not:
- Records come from a Europe PMC search (top records by relevance, with abstracts). Absence among the retrieved records is NOT absence in the literature.
- A record is put in a level by KEYWORDS in its title, abstract and publication type. This is crude: a record can fall in several levels, or none, and the tool does not read the paper or judge whether it supports or argues against the link.
- Open Targets scores are aggregates over several sources; they are not separate studies. The thresholds used to turn a score into a line strength are design choices, listed below.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .audit import EvidenceLine
from .audit_auto import disease_terms

LEVELS = [
    ("human_clinical", "Human clinical (trials, patients)"),
    ("human_genetic", "Human genetics (GWAS, variants, copy number)"),
    ("animal", "Mouse or rat in vivo"),
    ("cell", "Cell or in vitro"),
    ("review", "Review"),
]
LEVEL_NAME = dict(LEVELS)

_KW = {
    "human_clinical": ["randomized", "randomised", "placebo", "double-blind", "double blind", "clinical trial", "phase i ", "phase ii", "phase iii", "phase 1", "phase 2", "phase 3", "in patients", "participants"],
    "human_genetic": ["genome-wide", "gwas", "polymorphism", "single nucleotide", "snp", "variant", "mutation", "mendelian randomi", "copy number", "copy-number", "exome", "genotype", "allele", "haplotype", "heritab", "eqtl", "gene burden"],
    "animal": [" mice", " mouse", "murine", " rats", " rat ", "knockout", "knock-out", "transgenic", "rodent", "zebrafish"],
    "cell": ["cell line", "in vitro", "hek293", "hek 293", "oocyte", "cultured", "primary neuron", "patch-clamp", "patch clamp", "electrophysiolog", "transfected", "organoid", "ipsc"],
}
# How Open Targets association scores become line strengths. Design choices, not fitted to anything.
OT_MODERATE, OT_WEAK = 0.4, 0.1


def build_query(gene: str, names: List[str], disease: str) -> str:
    g = [f'"{x}"' for x in [gene] + [n for n in names if n and n.strip().upper() != gene.upper()]]
    t = disease_terms(disease)
    d = f'("{disease.strip()}"' + (f' OR ({" AND ".join(t)})' if len(t) >= 2 else (f' OR {t[0]}' if t else "")) + ")"
    return f'({" OR ".join(g)}) AND {d}'


def classify(rec: dict) -> List[str]:
    text = " " + (str(rec.get("title", "")) + " " + str(rec.get("abstract", ""))).lower() + " "
    pts = " ".join(rec.get("pubtypes") or []).lower()
    out = []
    if "review" in pts or "review" in str(rec.get("title", "")).lower():
        out.append("review")
    if "clinical trial" in pts or any(k in text for k in _KW["human_clinical"]):
        out.append("human_clinical")
    for lv in ("human_genetic", "animal", "cell"):
        if any(k in text for k in _KW[lv]):
            out.append(lv)
    return out


def comparison(records: List[dict]) -> Dict[str, dict]:
    res = {k: {"n": 0, "papers": []} for k, _ in LEVELS}
    res["unclassified"] = {"n": 0, "papers": []}
    for r in records:
        lv = classify(r) or ["unclassified"]
        for k in lv:
            res[k]["n"] += 1
            res[k]["papers"].append(r)
    for k in res:
        res[k]["papers"] = sorted(res[k]["papers"], key=lambda r: str(r.get("year", "")), reverse=True)[:3]
    return res


def best_ot_row(ot_rows: List[dict], disease: str) -> Optional[dict]:
    terms = disease_terms(disease)
    for r in ot_rows or []:
        if any(t in r.get("disease", "").lower() for t in terms):
            return r
    return (ot_rows or [None])[0]


def has_human_evidence(comp: Dict[str, dict], ot_row: Optional[dict]) -> bool:
    ga = (ot_row or {}).get("datatypes", {}).get("genetic_association", 0.0)
    return ga >= OT_WEAK or comp["human_clinical"]["n"] > 0 or comp["human_genetic"]["n"] > 0


def lines_from_literature(gene: str, disease: str, comp: Dict[str, dict], ot_rows: List[dict], n_records: int) -> List[EvidenceLine]:
    out: List[EvidenceLine] = []
    d = disease.strip()
    row = best_ot_row(ot_rows, disease)
    human = has_human_evidence(comp, row)
    if row:
        for dt, kind, label in (("genetic_association", "genetics", "human genetic association"), ("animal_model", "perturbation", "animal model")):
            sc = row["datatypes"].get(dt, 0.0)
            src = f"Open Targets {dt} score for '{row['disease']}' (aggregates several sources; retrieved by the app)"
            url = f"https://platform.opentargets.org/evidence/{row['id']}" if row.get("id") else ""
            if sc >= OT_WEAK:
                out.append(EvidenceLine(gene=gene, disease=d, kind=kind, direction="supports", strength="moderate" if sc >= OT_MODERATE else "weak",
                                        summary=f"{label.capitalize()} score {sc:.2f} for '{row['disease']}' (thresholds: weak from {OT_WEAK}, moderate from {OT_MODERATE}; design choices)",
                                        source=src, url=url, study_id=f"Open Targets {dt}"))
            else:
                out.append(EvidenceLine(gene=gene, disease=d, kind=kind, direction="neutral", strength="weak",
                                        summary=f"No meaningful {label} score for '{row['disease']}' (score {sc:.2f}; below {OT_WEAK})", source=src, url=url, study_id=f"Open Targets {dt}"))
    n_pre = comp["animal"]["n"] + comp["cell"]["n"]
    if n_pre:
        out.append(EvidenceLine(gene=gene, disease=d, kind="literature", direction="supports", strength="weak",
                                summary=f"{comp['animal']['n']} mouse/rat and {comp['cell']['n']} cell-based records among {n_records} retrieved mention the gene and '{d}' (keyword classification of abstracts; a mention is not a finding, and direction was not judged)",
                                source="Europe PMC search (retrieved by the app)", url="", study_id="Europe PMC preclinical records",
                                tags=[] if human else ["no_human_evidence"]))
    h = comp["human_clinical"]["n"] + comp["human_genetic"]["n"]
    if h:
        out.append(EvidenceLine(gene=gene, disease=d, kind="literature", direction="supports", strength="weak",
                                summary=f"{comp['human_genetic']['n']} human-genetics and {comp['human_clinical']['n']} human-clinical records among {n_records} retrieved mention the gene and '{d}' (keyword classification; a mention is not a finding, and direction was not judged)",
                                source="Europe PMC search (retrieved by the app)", url="", study_id="Europe PMC human records"))
    return out


def gap_statement(comp: Dict[str, dict], ot_row: Optional[dict], n_records: int) -> str:
    pre = comp["animal"]["n"] + comp["cell"]["n"]
    ga = (ot_row or {}).get("datatypes", {}).get("genetic_association", 0.0)
    if pre and not has_human_evidence(comp, ot_row):
        return (f"Among the {n_records} records retrieved, {pre} are animal or cell-based and none were classified as human genetics or human clinical; "
                f"Open Targets' genetic association score is {ga:.2f}. The preclinical evidence has not been matched by human evidence in what was retrieved. "
                "This is not proof that none exists: the search is limited to the top records and the classification is by keyword.")
    if pre and has_human_evidence(comp, ot_row):
        return (f"Preclinical records ({pre}) and human evidence both appear in what was retrieved (human genetics {comp['human_genetic']['n']}, human clinical {comp['human_clinical']['n']}, "
                f"Open Targets genetic association {ga:.2f}). Read the papers: a keyword match does not show the human result agrees with the animal result.")
    return f"Among the {n_records} records retrieved, few were classified as animal or cell-based. Check the search terms."
