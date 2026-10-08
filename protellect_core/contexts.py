"""Where each orphan is actually expressed in the user's matrix, expressed in the precedent library's tissue vocabulary.

The precedent model matches receptors to documented deorphanisations by tissue. Using the experiment-wide setting for every orphan makes them all look alike, so when a
matrix is available each orphan is matched on the contexts where IT is expressed.
"""
from __future__ import annotations

from typing import Dict

from .engine.registry import normalize_tissues


def matrix_tissue_annotations(gp, matrix, frac: float = 0.7, max_ctx: int = 3) -> Dict[str, dict]:
    """{gene: {"tissues": [...], "source": text, "authoritative": True, "contexts": [...]}} for every orphan in the matrix.

    A context counts as 'where it is expressed' when its mean expression is at least `frac` of the receptor's maximum (at most `max_ctx` contexts).
    """
    out: Dict[str, dict] = {}
    if gp is None or matrix is None or not len(getattr(gp, "orphans", [])):
        return out
    for g in gp.orphans["GPCR"]:
        if g not in matrix.index:
            continue
        row = matrix.loc[g].astype(float)
        if not (row.max() > 0):
            continue
        ctxs = [c for c in row.sort_values(ascending=False).index if row[c] >= frac * row.max()][:max_ctx]
        tissues = normalize_tissues(ctxs)
        out[str(g).upper()] = {"tissues": tissues, "source": "your matrix: highest in " + ", ".join(ctxs), "authoritative": True, "contexts": ctxs}
    return out
