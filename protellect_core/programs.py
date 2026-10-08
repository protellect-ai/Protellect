"""What does each GPCR track? Association of every GPCR with a marker-gene program (T-cell exhaustion, YAP/TAZ targets, hypoxia ...)
across the contexts (or samples) of an expression matrix.

The program score of a context is the mean of its marker genes' z-scores. Association is a Pearson correlation on log2(expression + 1) with a permutation p-value and
Benjamini-Hochberg FDR. It shows that a receptor and a program rise and fall together; it does not show that one regulates the other.
The built-in marker lists are short curated sets (edit or replace them); they are labelled as such everywhere they are used.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .evidence import Claim, Proof

PROGRAMS: Dict[str, List[str]] = {
    "T-cell exhaustion": ["PDCD1", "HAVCR2", "LAG3", "TIGIT", "TOX", "CTLA4", "ENTPD1"],
    "T-cell cytotoxicity": ["GZMB", "PRF1", "IFNG", "NKG7", "GZMA", "GNLY"],
    "Regulatory T cell": ["FOXP3", "IL2RA", "IKZF2", "TNFRSF18", "CTLA4"],
    "YAP/TAZ targets": ["CCN1", "CYR61", "CCN2", "CTGF", "ANKRD1", "AXL", "AMOTL2"],
    "Hypoxia": ["CA9", "VEGFA", "SLC2A1", "LDHA", "BNIP3", "PGK1"],
    "Myeloid suppression": ["ARG1", "CD163", "MRC1", "TREM2", "SPP1"],
    "Squamous tumour cell": ["EPCAM", "KRT5", "KRT14", "KRT17", "TP63"],
}
CITE_PROG = Proof("Marker-gene programs", "short curated marker lists (editable); not a validated signature", kind="literature")


def _z(m: pd.DataFrame) -> pd.DataFrame:
    l = np.log2(m + 1.0)
    sd = l.std(axis=1).replace(0, np.nan)
    return l.sub(l.mean(axis=1), axis=0).div(sd, axis=0).fillna(0.0)


def program_scores(matrix: pd.DataFrame, programs: Dict[str, List[str]], min_genes: int = 3) -> Dict[str, dict]:
    z = _z(matrix)
    out = {}
    for name, genes in programs.items():
        have = [g.upper() for g in genes if g.upper() in z.index]
        if len(have) >= min_genes:
            out[name] = {"genes": have, "score": z.loc[have].mean(axis=0)}
    return out


def _rankz(v: np.ndarray) -> np.ndarray:
    """Unit-length centred vector, so a dot product is a Pearson correlation. Applied to log2(x+1) values, not ranks: ranks among near-zero contexts are noise."""
    r = np.asarray(v, float) - np.mean(v)
    n = np.sqrt((r ** 2).sum())
    return r / n if n else r


def associate(matrix: pd.DataFrame, gpcr_genes: List[str], programs: Dict[str, List[str]], *, n_perm: int = 2000, seed: int = 0, min_genes: int = 3) -> pd.DataFrame:
    sc = program_scores(matrix, programs, min_genes)
    genes = [g for g in gpcr_genes if g in matrix.index]
    n = matrix.shape[1]
    if not sc or not genes or n < 5:
        return pd.DataFrame(columns=["GPCR", "Program", "Pearson r (log)", "p", "Program genes used", "FDR"])
    rng = np.random.default_rng(seed)
    G = np.vstack([_rankz(np.log2(matrix.loc[g].to_numpy(float) + 1.0)) for g in genes])
    rows = []
    for name, d in sc.items():
        P = _rankz(d["score"].to_numpy(float))
        r = G @ P
        cnt = np.zeros(len(genes))
        for _ in range(n_perm):
            cnt += np.abs(G @ P[rng.permutation(n)]) >= np.abs(r) - 1e-12
        p = (cnt + 1) / (n_perm + 1)
        for i, g in enumerate(genes):
            members = g in d["genes"]
            rows.append({"GPCR": g, "Program": name, "Pearson r (log)": round(float(r[i]), 3), "p": float(p[i]), "Program genes used": len(d["genes"]), "Is a program gene": members})
    t = pd.DataFrame(rows)
    t = t[~t["Is a program gene"]].drop(columns="Is a program gene").reset_index(drop=True)
    order = np.argsort(t["p"].to_numpy())
    ranked = t["p"].to_numpy()[order] * len(t) / (np.arange(len(t)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(len(t))
    q[order] = np.minimum(ranked, 1.0)
    t["FDR"] = q
    return t.sort_values(["FDR", "Pearson r (log)"], ascending=[True, False]).reset_index(drop=True)


def program_claims(t: pd.DataFrame, n_contexts: int, orphans: Optional[set] = None, min_r: float = 0.7, max_fdr: float = 0.05) -> List[Claim]:
    out = []
    if t.empty:
        return out
    best = t[(t["Pearson r (log)"] >= min_r) & (t["FDR"] <= max_fdr)].sort_values("Pearson r (log)", ascending=False).groupby("GPCR").head(1)
    for _, r in best.iterrows():
        counters = []
        if n_contexts < 10:
            counters.append({"check": "few_contexts", "severity": "minor", "text": f"Only {n_contexts} contexts: a correlation across so few points is a weak signal.", "evidence": "matrix"})
        out.append(Claim(
            text=f"{r['GPCR']} tracks the {r['Program']} program (Pearson r (log) {r['Pearson r (log)']:.2f} across {n_contexts} contexts, FDR {r['FDR']:.3g})",
            proofs=[Proof("Your expression matrix", f"{r['GPCR']} versus the mean z-score of {r['Program genes used']} marker genes: r = {r['Pearson r (log)']:.2f}, permutation p = {r['p']:.3g}, BH FDR = {r['FDR']:.3g}"), CITE_PROG],
            kind="inference", basis="The receptor and the program rise and fall together across contexts. That shows association, not that either drives the other.",
            score=float(r["Pearson r (log)"]) * 0.8, counters=counters, tags={"n_supporting": int(r["Program genes used"]), "category": "program", "gene": r["GPCR"], "program": r["Program"]},
            how=["Test whether the receptor is on the cells that carry the program (co-staining or sorting), then perturb the receptor and read out a program marker."]))
    return out
