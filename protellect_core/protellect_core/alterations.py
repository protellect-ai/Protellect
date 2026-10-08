"""Pan-cancer alteration layer: the user's own table of mutation / amplification / deletion frequencies per gene and cancer type."""
from __future__ import annotations

from typing import List

import pandas as pd

SYN = {"gene": ("gene", "symbol", "gene_symbol", "hugo_symbol"), "cancer": ("cancer", "cancer_type", "project", "study", "tumor_type", "tumour_type", "disease"),
       "mut": ("mutation_freq", "mut_freq", "mutation", "mutated", "mutation_frequency", "mut"), "amp": ("amp_freq", "amplification_freq", "amp", "amplification", "gain"),
       "del": ("del_freq", "deletion_freq", "del", "deletion", "loss")}


def parse_alterations(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).strip().lower(): c for c in df.columns}
    pick = {k: next((cols[s] for s in v if s in cols), None) for k, v in SYN.items()}
    if not pick["gene"] or not pick["cancer"] or not any(pick[k] for k in ("mut", "amp", "del")):
        raise ValueError(f"Need a gene column, a cancer-type column and at least one of mutation / amplification / deletion frequency. Columns seen: {list(df.columns)}")
    out = pd.DataFrame({"gene": df[pick["gene"]].astype(str).str.strip().str.upper(), "cancer": df[pick["cancer"]].astype(str).str.strip()})
    for k in ("mut", "amp", "del"):
        v = pd.to_numeric(df[pick[k]], errors="coerce") if pick[k] else pd.Series(0.0, index=df.index)
        out[k] = v.fillna(0.0)
    mx = out[["mut", "amp", "del"]].to_numpy().max()
    if mx > 1.0:                                           # percentages, not fractions
        out[["mut", "amp", "del"]] = out[["mut", "amp", "del"]] / 100.0
    if (out[["mut", "amp", "del"]].to_numpy() > 1.0001).any() or (out[["mut", "amp", "del"]].to_numpy() < 0).any():
        raise ValueError("Frequencies must be between 0 and 1 (or 0 and 100 as percentages).")
    return out[out["gene"].str.len() > 0].reset_index(drop=True)


def summary(alt: pd.DataFrame, gene: str, min_freq: float = 0.05) -> List[dict]:
    g = alt[alt["gene"] == gene.upper()]
    rows = []
    for _, r in g.iterrows():
        kinds = [f"{n} {r[k]:.0%}" for k, n in (("mut", "mutated"), ("amp", "amplified"), ("del", "deleted")) if r[k] >= min_freq]
        if kinds:
            rows.append({"cancer": r["cancer"], "text": ", ".join(kinds), "max": float(max(r["mut"], r["amp"], r["del"]))})
    return sorted(rows, key=lambda x: -x["max"])


def label(alt: pd.DataFrame, gene: str, min_freq: float = 0.05) -> str:
    s = summary(alt, gene, min_freq)
    return "; ".join(f"{x['cancer']} ({x['text']})" for x in s[:3]) if s else ""
