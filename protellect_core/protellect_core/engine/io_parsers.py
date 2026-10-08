"""Parse a researcher's processed experiment into one standard table.

Accepted shapes (auto-detected from column names, or force with shape=...):
  expression : gene + fold-change column (+ optional p/adjusted-p)
  variant    : gene + variant id column + effect size/odds ratio (+ optional p)
  screen     : gene + phenotype / screen score column (+ optional p)

Output columns: gene, shape, effect, effect_type, significance, signal_character
"""
from __future__ import annotations

import re
from typing import Optional, Union

import numpy as np
import pandas as pd

GENE_COLS = ["gene", "gene_symbol", "symbol", "hgnc_symbol", "gene_name", "geneid", "gene_id"]
LOGFC_COLS = ["log2foldchange", "log2fc", "logfc", "log2_fold_change", "lfc"]
FC_COLS = ["foldchange", "fold_change", "fc"]
P_COLS = ["padj", "adj_p", "adj_p_val", "fdr", "qvalue", "q_value", "pvalue", "p_value", "pval", "p"]
VAR_COLS = ["variant", "rsid", "snp", "variant_id", "rs"]
EFFECT_COLS = ["odds_ratio", "or", "beta", "effect", "effect_size", "log_or"]
SCREEN_COLS = ["phenotype", "phenotype_score", "screen_score", "score", "zscore", "z_score", "z"]

SIGNAL_CHARACTER = {
    "expression": "continuous fold-change (expression association)",
    "variant": "variant association (confirm germline vs somatic from the cohort design)",
    "screen": "functional perturbation phenotype",
    "lookup": "none (lookup by gene name; no experiment supplied)",
}


class InputError(ValueError):
    pass


def _clean(col: str) -> str:
    return re.sub(r"[\s.\-]+", "_", str(col).strip().lower())


def _first(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def parse_experiment(src: Union[str, pd.DataFrame], shape: Optional[str] = None,
                     max_significance: Optional[float] = None) -> pd.DataFrame:
    df = src.copy() if isinstance(src, pd.DataFrame) else pd.read_csv(src, sep=None, engine="python")
    df.columns = [_clean(c) for c in df.columns]
    cols = list(df.columns)

    gene_col = _first(cols, GENE_COLS)
    if gene_col is None:
        raise InputError(f"No gene column found. Columns seen: {cols}. Expected one of {GENE_COLS}.")

    var_col = _first(cols, VAR_COLS)
    logfc_col = _first(cols, LOGFC_COLS)
    fc_col = _first(cols, FC_COLS)
    screen_col = _first(cols, SCREEN_COLS)
    effect_col = _first(cols, EFFECT_COLS)

    if shape is None:
        if var_col:
            shape = "variant"
        elif logfc_col or fc_col:
            shape = "expression"
        elif screen_col:
            shape = "screen"
        else:
            raise InputError(f"Could not tell what kind of experiment this is. Columns seen: {cols}.")

    if shape == "expression":
        eff_col, eff_type = (logfc_col, "log2 fold-change") if logfc_col else (fc_col, "fold-change")
    elif shape == "variant":
        eff_col, eff_type = effect_col, "effect size / odds ratio"
    elif shape == "screen":
        eff_col, eff_type = screen_col, "phenotype score"
    else:
        raise InputError(f"Unknown shape {shape!r}. Use expression, variant, or screen.")
    if eff_col is None:
        raise InputError(f"Shape {shape!r} needs an effect column; columns seen: {cols}.")

    p_col = _first(cols, P_COLS)
    out = pd.DataFrame({
        "gene": df[gene_col].astype(str).str.strip().str.upper(),
        "shape": shape,
        "effect": pd.to_numeric(df[eff_col], errors="coerce"),
        "effect_type": eff_type,
        "significance": pd.to_numeric(df[p_col], errors="coerce") if p_col else np.nan,
    })
    out["signal_character"] = SIGNAL_CHARACTER[shape]
    out = out[(out["gene"] != "") & (out["gene"].str.lower() != "nan")]
    out = out.dropna(subset=["effect"])
    if max_significance is not None and p_col:
        out = out[out["significance"] <= max_significance]
    # one row per gene: keep the strongest effect
    out = out.loc[out["effect"].abs().groupby(out["gene"]).idxmax()].reset_index(drop=True)
    if out.empty:
        raise InputError("No usable rows after cleaning/filtering.")
    return out


def lookup_frame(gene: str) -> pd.DataFrame:
    """A one-row frame for 'look up this receptor' mode: no experiment, so no signal is invented."""
    g = str(gene).strip().upper()
    if not g:
        raise InputError("No gene given.")
    return pd.DataFrame({"gene": [g], "shape": ["lookup"], "effect": [np.nan], "effect_type": ["no experiment (lookup)"],
                         "significance": [np.nan], "signal_character": [SIGNAL_CHARACTER["lookup"]]})


def parse_matrix(src: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """A multi-context expression matrix: one gene column + several numeric context columns (cell types, tumours, conditions).
    Values must be non-negative expression (TPM, counts, or log-normalised >= 0). Returns genes (upper case) x contexts."""
    df = src.copy() if isinstance(src, pd.DataFrame) else pd.read_csv(src, sep=None, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    low = {_clean(c): c for c in df.columns}
    gcol = next((low[c] for c in GENE_COLS if c in low), None)
    if gcol is None:
        raise InputError(f"No gene column found. Columns seen: {list(df.columns)}. Expected one of {GENE_COLS}.")
    num = {}
    for c in df.columns:
        if c == gcol:
            continue
        v = pd.to_numeric(df[c], errors="coerce")
        if v.notna().mean() >= 0.8:
            num[c] = v
    if len(num) < 5:
        raise InputError(f"Need at least 5 numeric context columns (cell types or conditions); found {len(num)}. "
                         "With fewer contexts a co-expression profile carries too little information to use.")
    m = pd.DataFrame(num)
    m.index = df[gcol].astype(str).str.strip().str.upper()
    m = m[m.index.str.len() > 0].dropna(how="all")
    m = m.groupby(level=0).mean()
    if (m.fillna(0) < 0).any().any():
        raise InputError("The matrix has negative values. Use non-negative expression (TPM, counts or log-normalised >= 0). Fold-changes belong in the three-column format.")
    m = m.fillna(0.0)
    m = m[(m > 0).any(axis=1)]
    if m.empty:
        raise InputError("No expressed genes remain after cleaning.")
    return m
