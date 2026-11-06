"""Oncocrine axes: a ligand-producing gene peaks in one cell context and its receptor peaks in another (or the same).

Curated ligand -> producer -> receptor pairs, tested against the user's own matrix with relative expression (z-score across contexts).
Producer expression is a proxy for ligand availability; secretion is not measured, and the claim says so.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .evidence import Claim, Proof

AXES: List[tuple] = [
    ("Prostaglandin E2", ["PTGS2", "PTGES"], ["PTGER1", "PTGER2", "PTGER3", "PTGER4"]),
    ("Adenosine", ["ENTPD1", "NT5E"], ["ADORA1", "ADORA2A", "ADORA2B", "ADORA3"]),
    ("CXCL12", ["CXCL12"], ["CXCR4", "ACKR3"]),
    ("CCL2", ["CCL2"], ["CCR2"]),
    ("CXCL8 (IL-8)", ["CXCL8"], ["CXCR1", "CXCR2"]),
    ("CCL5", ["CCL5"], ["CCR5", "CCR1", "CCR3"]),
    ("CXCL9/10/11", ["CXCL9", "CXCL10", "CXCL11"], ["CXCR3"]),
    ("Lysophosphatidic acid", ["ENPP2"], ["LPAR1", "LPAR2", "LPAR3", "LPAR4", "LPAR5", "LPAR6"]),
    ("Sphingosine-1-phosphate", ["SPHK1", "SPHK2"], ["S1PR1", "S1PR2", "S1PR3", "S1PR4", "S1PR5"]),
    ("Lactate", ["LDHA"], ["HCAR1"]),
    ("Catecholamines", ["TH", "DBH", "PNMT"], ["ADRB1", "ADRB2", "ADRB3", "ADRA1A", "ADRA2A"]),
    ("Histamine", ["HDC"], ["HRH1", "HRH2", "HRH4"]),
]
CITE_AX = Proof("Ligand-producer / receptor pairs", "curated from textbook pharmacology (unverified list)", kind="literature")


def _z(m: pd.DataFrame) -> pd.DataFrame:
    sd = m.std(axis=1).replace(0, np.nan)
    return m.sub(m.mean(axis=1), axis=0).div(sd, axis=0).fillna(0.0)


def axes(matrix: pd.DataFrame, coupling: Dict[str, str] | None = None, min_z: float = 1.0) -> pd.DataFrame:
    z = _z(matrix)
    rows = []
    for lig, prods, recs in AXES:
        pz = [g for g in prods if g in z.index]
        if not pz:
            continue
        score = z.loc[pz].max(axis=0)
        src = score.idxmax()
        zs = float(score.max())
        for rcp in [r for r in recs if r in z.index]:
            tgt = z.loc[rcp].idxmax()
            zt = float(z.loc[rcp].max())
            if zs >= min_z and zt >= min_z:
                best = z.loc[pz, src].idxmax()
                rows.append({"Ligand": lig, "Producer": best, "Source context": src, "Source z": round(zs, 2), "Receptor": rcp, "Receptor coupling": (coupling or {}).get(rcp, ""),
                             "Target context": tgt, "Target z": round(zt, 2), "Relationship": "autocrine / same context" if src == tgt else "paracrine", "Strength": round(min(zs, zt), 2)})
    cols = ["Ligand", "Producer", "Source context", "Source z", "Receptor", "Receptor coupling", "Target context", "Target z", "Relationship", "Strength"]
    t = pd.DataFrame(rows, columns=cols)
    return t.sort_values("Strength", ascending=False).reset_index(drop=True)


def axis_claims(t: pd.DataFrame, n_contexts: int, limit: int = 8) -> List[Claim]:
    out = []
    for _, r in t.head(limit).iterrows():
        counters = [{"check": "expression_proxy", "severity": "minor", "text": "Ligand availability is inferred from the producer gene's expression; secretion and receptor protein are not measured.", "evidence": "design"}]
        if n_contexts < 10:
            counters.append({"check": "few_contexts", "severity": "minor", "text": f"Only {n_contexts} contexts, so 'peaks in' is a coarse statement.", "evidence": "matrix"})
        out.append(Claim(
            text=f"{r['Ligand']}: {r['Producer']} peaks in {r['Source context']} and {r['Receptor']}{' (' + r['Receptor coupling'] + ')' if r['Receptor coupling'] else ''} peaks in {r['Target context']} ({r['Relationship']})",
            proofs=[Proof("Your expression matrix", f"{r['Producer']}: z = {r['Source z']} in {r['Source context']}; {r['Receptor']}: z = {r['Target z']} in {r['Target context']} (z-scores across {n_contexts} contexts)"), CITE_AX],
            kind="inference", basis="A producer of a receptor's ligand and the receptor are each concentrated in particular contexts, which suggests a communication axis between them. It is a hypothesis about signalling, not a measurement of it.",
            score=min(1.0, float(r["Strength"]) / 3), counters=counters, tags={"n_supporting": 2, "category": "oncocrine axis", "ligand": r["Ligand"], "receptor": r["Receptor"]},
            how=[f"Measure {r['Ligand']} in the source cells' conditioned medium or tumour interstitial fluid (ELISA or mass spectrometry), and test the target cells' response to it with and without a receptor antagonist."]))
    return out
