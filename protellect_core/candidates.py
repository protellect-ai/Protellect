"""Ranked shortlists from everything the analyses found: receptors worth pursuing in a cell state (characterised) and orphans worth deorphanising.

The score is a prioritisation aid. Each component, its points and its source are shown, the weights are DESIGN CHOICES (not fitted), and a
component that could not be evaluated is left out of the denominator instead of counting as zero.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .alterations import label as alt_label
from .evidence import Claim, Proof

WEIGHTS = [
    ("Change in the foreground", 3, "rank of the receptor's change among all ranked GPCRs (full points at the top)"),
    ("Leading edge of an enriched coupling class", 2, "in the leading edge of a significant coupling class, in the same direction"),
    ("Tracks a marker program", 2, "Pearson r >= 0.7 and FDR <= 0.05 with a marker-gene program"),
    ("Cell-context specificity", 1, "tau >= 0.8"),
    ("Oncocrine axis", 1, "receptor in a producer-receptor axis"),
    ("Altered in cancer", 1, "alteration frequency >= 5% in your table"),
    ("Recorded drug", 1, "at least one recorded drug-gene interaction (only scored after the drug lookup)"),
]
MAXP = {w[0]: w[1] for w in WEIGHTS}


def rank(wb, status: Dict[str, str], alterations: Optional[pd.DataFrame] = None, drug_map: Optional[dict] = None, direction: str = "up", engine_hyp: Optional[dict] = None) -> pd.DataFrame:
    g = wb.gpcrome.all_gpcr
    if g is None or g.empty:
        return pd.DataFrame()
    ranked = wb.enrichment.ranked if wb.enrichment is not None else None
    pct = None
    if ranked is not None and len(ranked) > 1:
        r = ranked.rank(method="average", ascending=True)
        pct = (r - 1) / (len(ranked) - 1)
    lead = {}
    for c in wb.enrich_claims:
        if (direction == "either") or (c.tags.get("up") == (direction == "up")):
            for gene in c.tags.get("lead", []):
                lead[gene] = c.tags["class"]
    prog = {}
    if len(wb.programs):
        best = wb.programs[(wb.programs["Pearson r (log)"] >= 0.7) & (wb.programs["FDR"] <= 0.05)].sort_values("Pearson r (log)", ascending=False).groupby("GPCR").head(1)
        prog = {r["GPCR"]: f"{r['Program']} (r {r['Pearson r (log)']:.2f})" for _, r in best.iterrows()}
    axis = set(wb.axes["Receptor"]) if len(wb.axes) else set()
    pred = dict(zip(wb.gpcrome.orphans["GPCR"], wb.gpcrome.orphans["Predicted coupling"])) if len(wb.gpcrome.orphans) else {}
    rows = []
    for _, r in g.iterrows():
        gene = r["GPCR"]
        pts, avail, why = {}, {}, []
        avail["Change in the foreground"] = pct is not None and gene in pct.index
        if avail["Change in the foreground"]:
            p = float(pct[gene])
            pts["Change in the foreground"] = 3 * (p if direction == "up" else 1 - p if direction == "down" else abs(2 * p - 1))
            why.append(f"change {float(ranked[gene]):+.2f}")
        avail["Leading edge of an enriched coupling class"] = wb.enrichment is not None and not wb.enrichment.table.empty
        pts["Leading edge of an enriched coupling class"] = 2 if gene in lead else 0
        if gene in lead:
            why.append(f"{lead[gene]} leading edge")
        avail["Tracks a marker program"] = len(wb.programs) > 0
        pts["Tracks a marker program"] = 2 if gene in prog else 0
        if gene in prog:
            why.append(prog[gene])
        avail["Cell-context specificity"] = True
        pts["Cell-context specificity"] = 1 if r["Specificity (tau)"] >= 0.8 else 0
        if r["Specificity (tau)"] >= 0.8:
            why.append(f"specific to {r['Most expressed in']}")
        avail["Oncocrine axis"] = True
        pts["Oncocrine axis"] = 1 if gene in axis else 0
        if gene in axis:
            why.append("in an oncocrine axis")
        al = alt_label(alterations, gene) if alterations is not None else ""
        avail["Altered in cancer"] = alterations is not None
        pts["Altered in cancer"] = 1 if al else 0
        if al:
            why.append("altered: " + al)
        avail["Recorded drug"] = drug_map is not None
        pts["Recorded drug"] = 1 if (drug_map or {}).get(gene) else 0
        mx = sum(MAXP[k] for k, v in avail.items() if v)
        tot = sum(pts[k] for k, v in avail.items() if v)
        row = {"GPCR": gene, "Status": r["Status"], "Score": round(100 * tot / mx) if mx else 0, "Most expressed in": r["Most expressed in"], "Specificity (tau)": r["Specificity (tau)"],
               "Change": round(float(ranked[gene]), 2) if (ranked is not None and gene in ranked.index) else None, "Known coupling": r["Known coupling"] or pred.get(gene, ""),
               "Evidence": "; ".join(why) or "no supporting evidence in these analyses", "_pts": pts, "_avail": avail, "_n_support": sum(1 for k, v in pts.items() if v and avail[k])}
        if engine_hyp and gene in engine_hyp:
            row["Top ligand-class hypothesis"] = engine_hyp[gene]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["Score", "_n_support"], ascending=False).reset_index(drop=True)


def candidate_claims(df: pd.DataFrame, wb, status_label: str, limit: int = 6) -> List[Claim]:
    out = []
    v = wb.gpcrome.validation
    for _, r in df.head(limit).iterrows():
        if r["_n_support"] == 0:
            continue
        proofs = [Proof("Your analyses", f"{k}: {p}/{MAXP[k]} point(s)") for k, p in r["_pts"].items() if p and r["_avail"][k]]
        proofs.append(Proof("Scoring rule", "weights are design choices shown in the app, not fitted parameters", kind="rule"))
        counters = []
        if r["_n_support"] == 1:
            counters.append({"check": "single_line", "severity": "minor", "text": "Only one analysis supports this receptor.", "evidence": "components"})
        if v.get("ok") and not v.get("beats_baseline"):
            counters.append({"check": "self_test_failed", "severity": "major", "text": "The coupling method did not beat the baseline on your data; coupling-based components are unreliable.", "evidence": "self-test"})
        if wb.seed_table and r["_pts"].get("Leading edge of an enriched coupling class"):
            counters.append({"check": "unverified_coupling_table", "severity": "minor", "text": "The leading-edge component rests on the unverified seed coupling table.", "evidence": "coupling table"})
        out.append(Claim(text=f"{r['GPCR']} ({status_label}, score {r['Score']}/100): {r['Evidence']}", proofs=proofs, kind="inference",
                         basis="A weighted sum of independent analyses of your data; each component and weight is shown. It ranks receptors for follow-up and is not a probability of success.",
                         score=r["Score"] / 100, counters=counters, tags={"n_supporting": r["_n_support"], "category": "candidate", "gene": r["GPCR"]},
                         how=["Confirm receptor protein on the relevant cells, then perturb it (antagonist, agonist, knockout) and read out the cell-state marker." if status_label != "orphan" else
                              "Run a G-protein panel and a surrogate-ligand or constitutive-activity assay in receptor-expressing cells with empty-vector controls."]))
    return out
