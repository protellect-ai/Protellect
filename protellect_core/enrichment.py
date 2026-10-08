"""Which G-protein class dominates the receptors that go up (or down) in a cell state?

Rank GPCRs by how much they change between a foreground and a background (for example exhausted versus effector T cells), then test
whether the receptors of one coupling class (Gs, Gi, Gq, G12) sit disproportionately at the top or bottom of that ranking. This is a preranked
gene-set enrichment test in the style of Subramanian et al. 2005 (PNAS 102:15545): a weighted running-sum statistic, a null made from random
gene sets of the same size, normalisation by the mean same-sign null, and Benjamini-Hochberg correction across the classes.

The result is only as good as the coupling table behind it. The built-in table is a small curated seed that has NOT been verified, and every
claim says so. Load IUPHAR / GproteinDb couplings (or your own) in the app to replace it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .evidence import Claim, Proof

ALIASES = {"gs": "Gs", "gαs": "Gs", "gnas": "Gs", "gi": "Gi", "gi/o": "Gi", "go": "Gi", "gαi": "Gi", "gnai": "Gi", "gq": "Gq", "gq/11": "Gq", "g11": "Gq", "gαq": "Gq", "gnaq": "Gq",
           "g12": "G12", "g12/13": "G12", "g13": "G12", "gα12": "G12"}
CITE_GSEA = Proof("Preranked gene-set enrichment", "Subramanian et al. 2005, PNAS 102:15545", "https://doi.org/10.1073/pnas.0506580102", "literature")
CLASSES = ("Gs", "Gi", "Gq", "G12")


def norm_coupling(x) -> str:
    return ALIASES.get(str(x).strip().lower().replace(" ", ""), "")


def parse_coupling_table(df: pd.DataFrame) -> Dict[str, str]:
    """A user table: a gene column and a primary coupling column (Gs, Gi/o, Gq/11, G12/13 in any common spelling)."""
    cols = {str(c).strip().lower(): c for c in df.columns}
    g = next((cols[c] for c in ("gene", "symbol", "gene_symbol", "receptor") if c in cols), None)
    c = next((cols[k] for k in ("primary", "coupling", "g_protein", "gprotein", "primary_coupling", "g protein") if k in cols), None)
    if g is None or c is None:
        raise ValueError(f"Need a gene column and a coupling column (primary / coupling / g_protein). Columns seen: {list(df.columns)}")
    out = {}
    for gene, coup in zip(df[g].astype(str), df[c].astype(str)):
        k = norm_coupling(coup)
        if gene.strip() and k:
            out[gene.strip().upper()] = k
    if len(out) < 8:
        raise ValueError(f"Only {len(out)} receptors had a recognisable coupling (Gs, Gi/o, Gq/11, G12/13). Need at least 8.")
    return out


def rank_scores(effect: pd.Series, significance: Optional[pd.Series] = None, metric: str = "log2fc") -> pd.Series:
    """Ranking metric per gene: the fold-change itself, or its sign times -log10(p)."""
    if metric == "signed_p" and significance is not None:
        p = significance.astype(float).clip(lower=1e-300, upper=1.0)
        return np.sign(effect) * -np.log10(p)
    return effect.astype(float)


def _es(hit: np.ndarray, w: np.ndarray):
    n, k = len(hit), int(hit.sum())
    if k == 0 or k == n:
        return 0.0, 0
    pos = np.where(hit, w, 0.0)
    sp = pos.sum()
    if sp == 0:
        return 0.0, 0
    run = np.cumsum(pos / sp - (~hit) / (n - k))
    i = int(np.argmax(np.abs(run)))
    return float(run[i]), i


def _bh(p: np.ndarray) -> np.ndarray:
    order = np.argsort(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(p)
    out[order] = np.minimum(ranked, 1.0)
    return out


@dataclass
class EnrichmentResult:
    table: pd.DataFrame
    n_ranked: int
    metric: str
    n_perm: int
    coupling_source: str
    ranked: pd.Series
    note: str = ""
    curves: dict = None


def gsea_preranked(scores: pd.Series, coupling: Dict[str, str], coupling_source: str = "", *, metric: str = "log2fc", n_perm: int = 5000, seed: int = 0,
                   min_size: int = 5, weight: float = 1.0) -> EnrichmentResult:
    s = scores.dropna()
    s = s[~s.index.duplicated()].sort_values(ascending=False, kind="mergesort")
    genes = list(s.index)
    n = len(genes)
    empty = EnrichmentResult(pd.DataFrame(), n, metric, n_perm, coupling_source, s)
    if n < 20:
        empty.note = f"Only {n} receptors with both an expression change and a known coupling; at least 20 are needed."
        return empty
    w = np.abs(s.to_numpy(float)) ** weight
    if w.sum() == 0:
        empty.note = "All ranking values are zero."
        return empty
    rng = np.random.default_rng(seed)
    rows, curves = [], {}
    for cls in CLASSES:
        members = [g for g in genes if coupling.get(g) == cls]
        k = len(members)
        if k < min_size or k >= n:
            continue
        hit = np.array([coupling.get(g) == cls for g in genes])
        es, peak = _es(hit, w)
        pos_w = np.where(hit, w, 0.0)
        curves[cls] = {"run": np.cumsum(pos_w / pos_w.sum() - (~hit) / (n - k)).tolist(), "hits": [int(i) for i in np.where(hit)[0]], "peak": int(peak), "genes": [genes[i] for i in np.where(hit)[0]]}
        idx = np.argsort(rng.random((n_perm, n)), axis=1)[:, :k]
        h = np.zeros((n_perm, n), bool)
        np.put_along_axis(h, idx, True, axis=1)
        pos = np.where(h, w, 0.0)
        sp = pos.sum(axis=1, keepdims=True)
        sp[sp == 0] = 1.0
        run = np.cumsum(pos / sp - (~h) / (n - k), axis=1)
        null = run[np.arange(n_perm), np.argmax(np.abs(run), axis=1)]
        same = null[null * es > 0] if es != 0 else null
        denom = np.mean(np.abs(same)) if len(same) else np.nan
        nes = es / denom if denom and not np.isnan(denom) else np.nan
        p = (1 + np.sum(np.abs(same) >= abs(es))) / (1 + len(same)) if len(same) else 1.0
        lead = [g for i, g in enumerate(genes) if hit[i] and ((es >= 0 and i <= peak) or (es < 0 and i >= peak))]
        rows.append({"Coupling class": cls, "Receptors ranked": k, "ES": round(es, 3), "NES": round(float(nes), 2) if not np.isnan(nes) else np.nan, "p": float(p), "Leading edge": ", ".join(lead), "_lead": lead})
    if not rows:
        empty.note = f"No coupling class has at least {min_size} receptors among the {n} ranked."
        return empty
    t = pd.DataFrame(rows)
    t["FDR"] = _bh(t["p"].to_numpy(float))
    t["Direction"] = np.where(t["NES"] >= 0, "up in foreground", "down in foreground")
    t["Significant"] = np.where((t["FDR"] <= 0.10) & t["NES"].notna(), "yes", "no")
    return EnrichmentResult(t.sort_values("p").reset_index(drop=True), n, metric, n_perm, coupling_source, s, curves=curves)


def enrichment_claims(res: EnrichmentResult, contrast: str, seed_table: bool) -> List[Claim]:
    out = []
    if res.table.empty:
        return out
    for _, r in res.table.iterrows():
        if r["Significant"] != "yes":
            continue
        cls, k, lead, nes = r["Coupling class"], int(r["Receptors ranked"]), list(r["_lead"]), float(r["NES"])
        up = nes >= 0
        counters = []
        if k < 8:
            counters.append({"check": "small_set", "severity": "minor", "text": f"Only {k} {cls}-coupled receptors were ranked, so the class result rests on few genes.", "evidence": "set size"})
        if len(lead) <= 2:
            counters.append({"check": "narrow_leading_edge", "severity": "minor", "text": "The signal comes from one or two receptors.", "evidence": "leading edge"})
        if res.n_ranked < 40:
            counters.append({"check": "few_ranked", "severity": "minor", "text": f"Only {res.n_ranked} receptors were ranked.", "evidence": "ranking size"})
        if seed_table:
            counters.append({"check": "unverified_coupling_table", "severity": "minor", "text": "The coupling table is the built-in seed, which has not been verified. Load IUPHAR or GproteinDb couplings.", "evidence": "coupling table"})
        readout = {"Gs": "cAMP/PKA", "Gq": "Ca2+/PLC", "Gi": "cAMP decrease", "G12": "RhoA"}[cls]
        out.append(Claim(
            text=f"{cls}-coupled receptors are enriched among those {'higher' if up else 'lower'} in {contrast} (NES {nes:+.2f}, FDR {r['FDR']:.3g}); leading edge: {', '.join(lead[:6])}",
            proofs=[Proof("Your ranking", f"{k} {cls}-coupled receptors among {res.n_ranked} ranked ({res.metric}); enrichment score {r['ES']:+.3f}, permutation p = {r['p']:.3g} ({res.n_perm} random sets), BH FDR = {r['FDR']:.3g}"),
                    Proof("Coupling table", res.coupling_source or "built-in seed (unverified)", kind="literature"), CITE_GSEA],
            kind="inference", basis="Receptors of one coupling class are over-represented at one end of the ranking more than random gene sets of the same size would be.",
            score=min(1.0, abs(nes) / 3), counters=counters, tags={"n_supporting": k, "category": "coupling enrichment", "class": cls, "up": up, "lead": lead},
            how=[f"Pick leading-edge receptors with well-validated antagonists or agonists and test whether {cls} signalling ({readout}) changes the phenotype of the foreground cells, using a pathway-selective tool (a chemogenetic receptor of that class, or a pathway inhibitor).",
                 "Confirm the receptor is present at protein level in the foreground cells (flow cytometry or imaging) before functional work."]))
    return out
