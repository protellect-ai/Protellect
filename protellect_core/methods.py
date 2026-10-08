"""An auto-written methods paragraph for the analyses that were actually run, with the exact parameters. Nothing is described that was not done."""
from __future__ import annotations

import datetime

from . import __version__


def methods_markdown(wb, matrix_shape, contexts, n_registry: int, alterations: bool = False) -> str:
    g, p = wb.gpcrome, wb.gpcrome.params
    n_genes, n_ctx = matrix_shape
    v = g.validation
    parts = [f"**Software.** Protellect core v{__version__}, run {datetime.date.today().isoformat()}. Random seed {p.get('seed', 0)}."]
    parts.append(f"**GPCR cell-context analysis.** Expression values for {n_genes} genes across {n_ctx} contexts ({', '.join(contexts)}) were transformed as log2(x + 1). GPCRs were identified from a receptor registry of {n_registry} entries "
                 f"({g.n_gpcr} present in the matrix). Context specificity was calculated with the tau index (Yanai et al. 2005, Bioinformatics 21:650).")
    if len(g.orphans):
        parts.append(f"Signalling of orphan GPCRs was inferred by guilt by association (Oliver 2000, Nature 403:601): the Pearson correlation of log2(x + 1) expression across contexts was computed against every characterised GPCR with a known primary coupling; "
                     f"permutation p-values used {p.get('n_perm')} permutations of the context labels and were corrected across all pairs by Benjamini-Hochberg. Neighbours were required to have r >= {p.get('min_r')}, FDR <= {p.get('max_fdr')} and at least {p.get('min_neighbours')} supporters, "
                     f"and coupling was assigned by an r-weighted vote of up to {p.get('k')} neighbours.")
        parts.append(("The method was tested on the data themselves by hiding each characterised receptor's coupling and predicting it from the others: " + v["note"]) if v.get("ok") else ("Self-test: " + v.get("note", "not performed")))
    parts.append(f"Primary G-protein couplings came from: {wb.coupling_source or 'the built-in seed table (unverified)'} ({len(wb.coupling)} receptors).")
    if wb.enrichment is not None and len(wb.enrichment.table):
        e = wb.enrichment
        parts.append(f"**Coupling-class enrichment.** {e.n_ranked} receptors were ranked by {e.metric} ({wb.params.get('ranking')}; contrast: {wb.enrich_contrast}). A preranked gene-set enrichment test (Subramanian et al. 2005, PNAS 102:15545) was run for the "
                     f"{', '.join(e.table['Coupling class'])} coupling sets (minimum size 5), with a null of {e.n_perm} random gene sets of equal size, normalisation by the mean same-sign null enrichment score, and Benjamini-Hochberg correction across classes.")
    if len(wb.programs):
        parts.append(f"**Programs.** Each GPCR was correlated (Pearson, log2(x + 1)) with the mean z-score of marker-gene programs ({'; '.join(wb.program_names)}); permutation p-values ({p.get('n_perm')} permutations) were corrected by Benjamini-Hochberg across all receptor-program pairs. "
                     "The marker lists are short curated sets and are not validated signatures.")
    if len(wb.axes):
        parts.append("**Oncocrine axes.** For curated ligand-producer and receptor pairs, expression was converted to z-scores across contexts; an axis was reported when a producer gene and a receptor gene each had z >= 1 in some context. Producer expression is a proxy for ligand availability.")
    if alterations:
        parts.append("**Pan-cancer alterations.** Mutation, amplification and deletion frequencies were taken from the supplied table without modification.")
    return "\n\n".join(parts)
