"""GPCRome analysis: which GPCRs are specific to which cell context, and what an uncharacterised GPCR probably couples to.

Two analyses on a multi-context expression matrix (genes x contexts such as tumour cells, T cells, macrophages):

1. Specificity (tau, Yanai et al. 2005): how concentrated a gene's expression is in one context (0 = everywhere, 1 = one context).
2. Guilt by association (Oliver 2000): GPCRs with similar expression profiles across contexts tend to share signalling. For each
   orphan GPCR the Pearson correlation (on log2(expression + 1)) with every characterised GPCR is computed, tested by permutation, corrected for the
   number of tests (Benjamini-Hochberg), and the supported neighbours vote on the G-protein class.

The part that keeps this honest is the SELF-TEST: the same method is run on the characterised GPCRs in the user's own matrix
(hide one receptor's coupling, predict it from the others) and its accuracy is compared with a naive baseline. If the method
cannot beat the baseline on the user's data, its predictions are labelled unsupported.
"""
from __future__ import annotations

import pathlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .evidence import Claim, Proof

DATA = pathlib.Path(__file__).parent / "engine" / "data"
MIN_R, MAX_FDR, MIN_NEIGHBOURS, TAU_SPECIFIC = 0.6, 0.10, 2, 0.8

PATHWAYS = {
    "Gq": "Phospholipase C-beta, then IP3/Ca2+ and DAG/PKC. Gq/11 signalling also activates YAP/TAZ through Rho GTPases (Feng 2014, Cancer Cell 25:831; Yu 2012, Cell 150:780).",
    "Gi": "Inhibits adenylyl cyclase (less cAMP) and releases G-beta-gamma to PI3K and MAPK. Gi-coupled receptors for lipid mediators can activate YAP (Yu 2012, Cell 150:780).",
    "Gs": "Adenylyl cyclase, then cAMP, PKA and CREB. Gs-coupled receptors tend to restrain YAP through LATS (Yu 2012, Cell 150:780).",
}
CITE_GBA = Proof("Guilt by association", "Oliver 2000, Nature 403:601 (co-expressed genes tend to share function)", "https://doi.org/10.1038/35001168", "literature")
CITE_TAU = Proof("Tau specificity index", "Yanai et al. 2005, Bioinformatics 21:650", "https://doi.org/10.1093/bioinformatics/bti042", "literature")


def load_couplings(path: Optional[str] = None) -> Dict[str, str]:
    df = pd.read_csv(path or DATA / "gpcr_couplings.csv", dtype=str).fillna("")
    return {g.strip().upper(): c.strip() for g, c in zip(df["gene"], df["primary"]) if g.strip() and c.strip()}


def tau_index(m: pd.DataFrame) -> pd.Series:
    mx = m.max(axis=1).replace(0, np.nan)
    n = m.shape[1]
    return ((1 - m.div(mx, axis=0)).sum(axis=1) / (n - 1)).fillna(0.0)


def _zranks(m: pd.DataFrame) -> np.ndarray:
    """Rows scaled so a dot product is the Pearson correlation of log2(expression + 1) across contexts.
    (Amplitude matters in cell-type matrices; ranks among near-zero contexts are noise, which breaks receptors confined to one context.)"""
    v = np.log2(m.to_numpy(dtype=float) + 1.0)
    v = v - v.mean(axis=1, keepdims=True)
    sd = np.sqrt((v ** 2).sum(axis=1, keepdims=True))
    sd[sd == 0] = 1.0
    return v / sd


def _bh(p: np.ndarray) -> np.ndarray:
    flat = p.ravel()
    order = np.argsort(flat)
    ranked = flat[order] * len(flat) / (np.arange(len(flat)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(flat)
    out[order] = np.minimum(ranked, 1.0)
    return out.reshape(p.shape)


def _vote(neigh: List[tuple], coup: Dict[str, str]):
    w = Counter()
    for g, r in neigh:
        w[coup[g]] += max(r, 0.0)
    tot = sum(w.values())
    if not tot:
        return "", 0.0
    best, val = w.most_common(1)[0]
    return best, val / tot


@dataclass
class GPCRomeResult:
    contexts: List[str]
    n_genes: int
    n_gpcr: int
    orphans: pd.DataFrame
    all_gpcr: pd.DataFrame
    validation: dict
    claims: List[Claim] = field(default_factory=list)
    skipped: str = ""
    params: dict = field(default_factory=dict)


def self_test(z: np.ndarray, genes: List[str], coup: Dict[str, str], k: int = 5) -> dict:
    """Leave one out on the characterised GPCRs in THIS matrix: predict each one's coupling from the others, compare with a baseline."""
    idx = [i for i, g in enumerate(genes) if g in coup]
    n = len(idx)
    if n < 8 or len({coup[genes[i]] for i in idx}) < 2:
        return {"n": n, "ok": False, "note": f"Only {n} characterised GPCRs with a known coupling are in your matrix; at least 8 across 2 or more classes are needed to test the method."}
    corr = z[idx] @ z[idx].T
    hits = base_hits = 0
    for a, i in enumerate(idx):
        others = [b for b in range(n) if b != a]
        order = sorted(others, key=lambda b: -corr[a, b])[:k]
        pred, _ = _vote([(genes[idx[b]], corr[a, b]) for b in order], coup)
        maj = Counter(coup[genes[idx[b]]] for b in others).most_common(1)[0][0]
        truth = coup[genes[i]]
        hits += pred == truth
        base_hits += maj == truth
    return {"n": n, "ok": True, "hits": int(hits), "baseline": int(base_hits), "accuracy": hits / n, "baseline_accuracy": base_hits / n, "beats_baseline": hits > base_hits and hits / n >= 0.6,
            "note": f"On the {n} characterised GPCRs in your matrix, the method recovered {hits} couplings (naive baseline: {base_hits})."}


def analyse(matrix: pd.DataFrame, registry: Dict[str, dict], couplings: Dict[str, str], *, k: int = 5, n_perm: int = 2000, seed: int = 0) -> GPCRomeResult:
    ctx = list(matrix.columns)
    n = len(ctx)
    gp = [g for g in matrix.index if g in registry]
    empty = pd.DataFrame()
    if n < 5 or len(gp) < 5:
        return GPCRomeResult(ctx, len(matrix), len(gp), empty, empty, {"ok": False, "note": "Too few contexts or recognised GPCRs to analyse."}, skipped="Need at least 5 contexts and 5 recognised GPCRs.")
    sub = matrix.loc[gp]
    z = _zranks(sub)
    genes = list(sub.index)
    tau = tau_index(sub)
    top_ctx = sub.idxmax(axis=1)
    val = self_test(z, genes, couplings, k)
    is_orph = np.array([registry[g]["status"] == "orphan" for g in genes])
    known = [i for i, g in enumerate(genes) if (not is_orph[i]) and g in couplings]
    orph = [i for i in range(len(genes)) if is_orph[i]]
    rows, claims = [], []
    all_rows = [{"GPCR": g, "Status": "orphan" if is_orph[i] else "characterised", "Most expressed in": top_ctx[g], "Specificity (tau)": round(float(tau[g]), 2),
                 "Specific?": "yes" if tau[g] >= TAU_SPECIFIC else "no", "Known coupling": couplings.get(g, "")} for i, g in enumerate(genes)]
    if orph and len(known) >= 3:
        rng = np.random.default_rng(seed)
        zo, zk = z[orph], z[known]
        r_obs = zo @ zk.T
        cnt = np.zeros_like(r_obs)
        for _ in range(n_perm):
            cnt += np.abs(zo @ zk[:, rng.permutation(n)].T) >= np.abs(r_obs) - 1e-12
        pv = (cnt + 1) / (n_perm + 1)
        q = _bh(pv)
        for a, i in enumerate(orph):
            g = genes[i]
            cand = [(genes[known[b]], float(r_obs[a, b]), float(pv[a, b]), float(q[a, b])) for b in range(len(known))]
            sup = sorted([c for c in cand if c[1] >= MIN_R and c[3] <= MAX_FDR], key=lambda c: -c[1])[:k]
            call, share = _vote([(c[0], c[1]) for c in sup], couplings) if len(sup) >= MIN_NEIGHBOURS else ("", 0.0)
            rows.append({"GPCR": g, "Predicted coupling": call or "no supported call", "Vote share": round(share, 2), "Supported neighbours": ", ".join(f"{c[0]} (r={c[1]:.2f})" for c in sup) or "none",
                         "Most expressed in": top_ctx[g], "Specificity (tau)": round(float(tau[g]), 2), "Best FDR": round(min(c[3] for c in cand), 4)})
            if call:
                proofs = [Proof("Your expression matrix", f"{c[0]}: Pearson r (log scale) = {c[1]:.2f} across {n} contexts, permutation p = {c[2]:.3g}, BH FDR = {c[3]:.3g}") for c in sup]
                proofs += [Proof("Curated coupling (unverified)", f"{c[0]} primarily couples to {couplings[c[0]]}", kind="literature") for c in sup[:3]]
                if val["ok"]:
                    proofs.append(Proof("Self-test on your matrix", val["note"]))
                counters = []
                if val["ok"] and not val["beats_baseline"]:
                    counters.append({"check": "self_test_failed", "severity": "major", "text": f"The method did not beat a naive baseline on your own characterised GPCRs ({val['hits']} vs {val['baseline']} of {val['n']}), so this prediction is unsupported.", "evidence": "self-test"})
                if not val["ok"]:
                    counters.append({"check": "self_test_unavailable", "severity": "minor", "text": val["note"], "evidence": "self-test"})
                if n < 8:
                    counters.append({"check": "few_contexts", "severity": "minor", "text": f"Only {n} contexts: a correlation across so few points is a weak signal.", "evidence": "matrix"})
                if tau[g] >= 0.9:
                    counters.append({"check": "single_context_driven", "severity": "major", "text": f"{g} is expressed almost entirely in {top_ctx[g]} (tau {tau[g]:.2f}), so its correlation with the neighbours may only mean 'same cell type', not 'same signalling'.", "evidence": "tau specificity"})
                if share < 0.75:
                    counters.append({"check": "split_vote", "severity": "minor", "text": f"The supported neighbours disagree on coupling (top class holds {share:.0%} of the vote).", "evidence": "vote"})
                claims.append(Claim(text=f"{g}: probably couples to {call} (co-expressed with {', '.join(c[0] for c in sup[:3])})", proofs=proofs + [CITE_GBA], kind="inference",
                                    basis="Receptors with similar expression profiles across contexts tend to share signalling. Neighbours were required to have r >= 0.6, permutation FDR <= 0.10 and at least 2 supporters.",
                                    score=share * min(1.0, len(sup) / 5.0), counters=counters, tags={"n_supporting": len(sup), "category": "signaling", "gene": g, "call": call, "pathway": PATHWAYS.get(call, "")},
                                    how=[f"Test coupling with a G-protein-selective readout (for {call}: " + {"Gq": "Ca2+ mobilisation or IP1 accumulation", "Gi": "forskolin-stimulated cAMP decrease", "Gs": "cAMP accumulation"}.get(call, "a G-protein sensor assay") + ") in cells expressing the receptor, with empty-vector controls.",
                                         "Use a surrogate agonist if no ligand is known, or a constitutive-activity assay."]))
            if tau[g] >= TAU_SPECIFIC:
                claims.append(Claim(text=f"{g}: expression is specific to {top_ctx[g]} (tau {tau[g]:.2f})", proofs=[Proof("Your expression matrix", f"{g} values across {n} contexts; highest in {top_ctx[g]} ({float(sub.loc[g].max()):.3g}); next highest {float(np.sort(sub.loc[g].to_numpy())[-2]):.3g}"), CITE_TAU],
                                    kind="data", score=0.5 * float(tau[g]), tags={"n_supporting": n, "category": "specificity", "gene": g}))
    return GPCRomeResult(ctx, len(matrix), len(gp), pd.DataFrame(rows), pd.DataFrame(all_rows), val, claims, params={"k": k, "n_perm": n_perm, "seed": seed, "min_r": MIN_R, "max_fdr": MAX_FDR, "min_neighbours": MIN_NEIGHBOURS, "tau_specific": TAU_SPECIFIC})


def check_truth(res: GPCRomeResult, truth: dict, wb=None) -> List[dict]:
    """Compare results with the answers planted in the synthetic example. Used to show the tool recovers known structure."""
    out = []
    t = res.orphans.set_index("GPCR") if len(res.orphans) else pd.DataFrame()
    for g, want in truth.get("coupling", {}).items():
        got = t.loc[g, "Predicted coupling"] if g in t.index else "missing"
        out.append({"check": f"{g} couples to {want}", "got": got, "ok": got == want})
    for g in truth.get("no_call", []):
        got = t.loc[g, "Predicted coupling"] if g in t.index else "missing"
        out.append({"check": f"{g} (noise control) gets no call", "got": got, "ok": got == "no supported call"})
    for g, want in truth.get("top_context", {}).items():
        got = res.all_gpcr.set_index("GPCR").loc[g, "Most expressed in"] if g in set(res.all_gpcr.get("GPCR", [])) else "missing"
        want = [want] if isinstance(want, str) else want
        out.append({"check": f"{g} most expressed in " + (want[0] if len(want) == 1 else "one of: " + ", ".join(want)), "got": got, "ok": got in want})
    if wb is not None:
        et = wb.enrichment.table if wb.enrichment is not None and len(wb.enrichment.table) else pd.DataFrame()
        for cls, d in truth.get("enrichment", {}).items():
            row = et[et["Coupling class"] == cls] if len(et) else et
            got = "not tested" if not len(row) else (f"{'up' if row.iloc[0]['NES'] >= 0 else 'down'}, FDR {row.iloc[0]['FDR']:.3g}" + ("" if row.iloc[0]["Significant"] == "yes" else " (not significant)"))
            ok = bool(len(row)) and row.iloc[0]["Significant"] == "yes" and (row.iloc[0]["NES"] >= 0) == (d == "up")
            out.append({"check": f"{cls}-coupled receptors enriched {d} in the contrast", "got": got, "ok": ok})
        pt = wb.programs
        for gene, prog in truth.get("programs", {}).items():
            row = pt[(pt["GPCR"] == gene)].sort_values("Pearson r (log)", ascending=False).head(1) if len(pt) else pt
            got = "missing" if not len(row) else f"{row.iloc[0]['Program']} (r {row.iloc[0]['Pearson r (log)']:.2f}, FDR {row.iloc[0]['FDR']:.3g})"
            out.append({"check": f"{gene} tracks {prog}", "got": got, "ok": bool(len(row)) and row.iloc[0]["Program"] == prog and row.iloc[0]["FDR"] <= 0.05})
        ax = wb.axes
        for want in truth.get("oncocrine", []):
            hit = ax[(ax["Ligand"] == want["ligand"]) & (ax["Receptor"] == want["receptor"])] if len(ax) else ax
            ok = bool(len(hit)) and all(hit.iloc[0][k.capitalize() + " context"] == v for k, v in want.items() if k in ("source", "target"))
            got = "missing" if not len(hit) else f"{hit.iloc[0]['Source context']} -> {hit.iloc[0]['Target context']}"
            out.append({"check": f"{want['ligand']} axis to {want['receptor']}" + "".join(f" ({k}: {v})" for k, v in want.items() if k in ("source", "target")), "got": got, "ok": ok})
    return out
