"""All GPCRome analyses on one matrix, computed together so every view and every claim sees the same facts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .enrichment import EnrichmentResult, enrichment_claims, gsea_preranked
from .evidence import Claim
from .gpcrome import GPCRomeResult, analyse
from .oncocrine import axes as onco_axes, axis_claims
from .programs import PROGRAMS, associate, program_claims


@dataclass
class Workbench:
    gpcrome: GPCRomeResult
    coupling: Dict[str, str]
    coupling_source: str
    seed_table: bool
    enrichment: Optional[EnrichmentResult] = None
    enrich_contrast: str = ""
    enrich_claims: List[Claim] = field(default_factory=list)
    programs: pd.DataFrame = field(default_factory=pd.DataFrame)
    program_claims: List[Claim] = field(default_factory=list)
    axes: pd.DataFrame = field(default_factory=pd.DataFrame)
    axis_claims: List[Claim] = field(default_factory=list)
    program_names: List[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)

    @property
    def claims(self) -> List[Claim]:
        return list(self.gpcrome.claims) + self.enrich_claims + self.program_claims + self.axis_claims


def matrix_ranking(matrix: pd.DataFrame, fg: List[str]) -> pd.Series:
    bg = [c for c in matrix.columns if c not in fg]
    return np.log2((matrix[fg].mean(axis=1) + 1) / (matrix[bg].mean(axis=1) + 1))


def build(matrix: pd.DataFrame, registry: Dict[str, dict], coupling: Dict[str, str], coupling_source: str, *, de_effect: Optional[pd.Series] = None, de_sig: Optional[pd.Series] = None,
          fg: Optional[List[str]] = None, rank_source: str = "auto", metric: str = "log2fc", comparison: str = "", extra_programs: Optional[Dict[str, List[str]]] = None,
          n_perm: int = 2000, seed: int = 0) -> Workbench:
    res = analyse(matrix, registry, coupling, n_perm=n_perm, seed=seed)
    wb = Workbench(res, coupling, coupling_source, seed_table="seed" in coupling_source.lower() or not coupling_source)
    universe = set(registry) | set(coupling)
    scores, contrast, used = None, "", ""
    use_de = de_effect is not None and rank_source in ("auto", "table")
    use_mx = fg and rank_source in ("auto", "matrix") and not (rank_source == "auto" and use_de)
    if use_de:
        s = de_effect[de_effect.index.isin(universe)]
        if metric == "signed_p" and de_sig is not None:
            p = de_sig.reindex(s.index).astype(float).clip(lower=1e-300, upper=1.0)
            s = np.sign(s) * -np.log10(p)
        scores, contrast, used = s, comparison or "your differential table", "your differential table"
    elif use_mx:
        s = matrix_ranking(matrix, list(fg))
        scores, contrast, used = s[s.index.isin(universe)], f"{', '.join(fg)} versus the other contexts", "matrix: foreground versus background"
    if scores is not None:
        wb.enrichment = gsea_preranked(scores, coupling, coupling_source, metric=metric if use_de else "log2 ratio", seed=seed)
        wb.enrich_contrast = contrast
        wb.enrich_claims = enrichment_claims(wb.enrichment, contrast, wb.seed_table)
        wb.params["ranking"] = used
    progs = dict(PROGRAMS)
    progs.update({k: v for k, v in (extra_programs or {}).items() if v})
    gp = [g for g in matrix.index if g in registry]
    wb.programs = associate(matrix, gp, progs, n_perm=n_perm, seed=seed)
    wb.program_claims = program_claims(wb.programs, matrix.shape[1])
    wb.program_names = sorted(progs)
    wb.axes = onco_axes(matrix, coupling)
    wb.axis_claims = axis_claims(wb.axes, matrix.shape[1])
    wb.params.update({"n_perm": n_perm, "seed": seed})
    return wb
