"""Sequence-based G-protein coupling classifier with an honest self-test.

Features come from the loop and motif structure that is known to relate to coupling selectivity: intracellular loop lengths and
composition (ICL2, ICL3), C-terminal tail length, and the DRY and NPxxY motifs. They are computed from the amino-acid sequence
and the seven transmembrane boundaries.

The classifier is trained on whatever labelled receptors you give it and TESTED by leaving out whole receptor subfamilies
(so close paralogs cannot leak the answer). Predictions for orphans are released only if the held-out accuracy beats the
majority-class baseline with a bootstrap interval that excludes it. Otherwise the module says plainly that the labelled set
is too small or the features do not carry the signal. It never reports a prediction that failed its own test.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

MIN_LABELLED = 40
MIN_PER_CLASS = 5
AA = "ACDEFGHIKLMNPQRSTVWY"


def parse_tms(text: str) -> List[Tuple[int, int]]:
    """UniProt 'Transmembrane' feature text -> [(start, end)]."""
    return [(int(a), int(b)) for a, b in re.findall(r"TRANSMEM\s+(\d+)\.\.(\d+)", text or "")]


def _comp(seg: str, letters: str) -> float:
    return sum(seg.count(c) for c in letters) / len(seg) if seg else 0.0


def features(seq: str, tms: Sequence[Tuple[int, int]]) -> Optional[Dict[str, float]]:
    """None unless there are exactly seven transmembrane segments inside the sequence."""
    tms = sorted(tms)
    if len(tms) != 7 or not seq or tms[-1][1] > len(seq):
        return None
    s = lambda a, b: seq[a - 1:b] if b >= a else ""
    icl1 = s(tms[0][1] + 1, tms[1][0] - 1); icl2 = s(tms[2][1] + 1, tms[3][0] - 1); icl3 = s(tms[4][1] + 1, tms[5][0] - 1)
    ctail = seq[tms[6][1]:]; nterm = seq[:tms[0][0] - 1]
    dry_zone = seq[max(tms[2][1] - 4, 0): tms[2][1] + 5]
    f = {"len_icl1": len(icl1), "len_icl2": len(icl2), "len_icl3": len(icl3), "len_ctail": len(ctail), "len_nterm": len(nterm),
         "log_icl3": float(np.log1p(len(icl3))), "log_ctail": float(np.log1p(len(ctail))),
         "dry_like": float(bool(re.search(r"[DE]R[YFHWC]", dry_zone))), "npxxy": float(bool(re.search(r"NP..Y", seq[tms[6][0] - 1: tms[6][1] + 3]))),
         "icl2_hydrophobic": _comp(icl2, "AVILMFWC"), "icl3_basic": _comp(icl3, "KR"), "icl3_acidic": _comp(icl3, "DE"), "icl3_ser_thr": _comp(icl3, "ST"),
         "icl3_pro": _comp(icl3, "P"), "ctail_ser_thr": _comp(ctail, "ST"), "ctail_acidic": _comp(ctail, "DE"), "ctail_basic": _comp(ctail, "KR"),
         "icl2_pro": _comp(icl2, "P"), "icl1_basic": _comp(icl1, "KR")}
    return f


def group_of(gene: str) -> str:
    """Subfamily used for leave-group-out testing: the gene-symbol letters with trailing digits and receptor-subtype suffix removed."""
    g = re.sub(r"\d.*$", "", gene.upper())
    return g or gene.upper()


def _matrix(rows: List[Dict[str, float]], cols: List[str]) -> np.ndarray:
    return np.array([[r[c] for c in cols] for r in rows], float)


def _fit(X, y):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced"))
    m.fit(X, y)
    return m


def evaluate(data: Dict[str, Dict], labels: Dict[str, str], n_boot: int = 500, n_perm: int = 60, seed: int = 0) -> Dict:
    """data: gene -> {'seq': str, 'tms': [(s, e), ...]}; labels: gene -> primary G family. Leave-one-subfamily-out evaluation."""
    rows, genes, y = [], [], []
    for g, lab in labels.items():
        d = data.get(g)
        f = features(d["seq"], d["tms"]) if d else None
        if f and lab:
            rows.append(f); genes.append(g); y.append(lab)
    counts = {c: y.count(c) for c in set(y)}
    keep = {c for c, n in counts.items() if n >= MIN_PER_CLASS}
    idx = [i for i, c in enumerate(y) if c in keep]
    rows = [rows[i] for i in idx]; genes = [genes[i] for i in idx]; y = [y[i] for i in idx]
    out = {"n": len(y), "classes": {c: counts[c] for c in sorted(keep)}, "trusted": False, "cols": list(rows[0]) if rows else []}
    if len(y) < MIN_LABELLED or len(keep) < 2:
        out["reason"] = (f"Only {len(y)} labelled receptors with a seven-transmembrane sequence in classes of at least {MIN_PER_CLASS} (need {MIN_LABELLED} across at least 2 classes). "
                         "A sequence model on so few examples would be noise, so no prediction is shown. Supply a larger, verified coupling table (GPCRdb or Guide to Pharmacology).")
        return out
    cols = out["cols"]; X = _matrix(rows, cols); yv = np.array(y); grp = np.array([group_of(g) for g in genes])

    def cv_predict(labels_vec):
        pred = np.empty(len(labels_vec), dtype=object)
        for gname in np.unique(grp):
            te = grp == gname; tr = ~te
            if len(set(labels_vec[tr])) < 2:
                pred[te] = labels_vec[tr][0] if tr.any() else labels_vec[0]; continue
            pred[te] = _fit(X[tr], labels_vec[tr]).predict(X[te])
        return pred

    pred = cv_predict(yv)
    hit = (pred == yv).astype(float)
    vals, cnt = np.unique(yv, return_counts=True)
    baseline = float(cnt.max() / cnt.sum())            # always guess the most common class overall (a fixed, fair baseline)
    rng = np.random.default_rng(seed); ug = np.unique(grp); accs = []
    for _ in range(n_boot):
        pick = rng.choice(ug, len(ug)); sel = np.concatenate([np.nonzero(grp == g)[0] for g in pick])
        accs.append(hit[sel].mean())
    lo, hi = np.percentile(accs, [2.5, 97.5])
    # label-permutation test: same grouped CV on shuffled labels. Guards against leave-out artefacts and chance.
    obs = float(hit.mean()); ge = 0
    for _ in range(n_perm):
        ge += float((cv_predict(rng.permutation(yv)) == yv).mean()) >= obs
    p_perm = (1 + ge) / (1 + n_perm)
    per = {c: float(hit[yv == c].mean()) for c in sorted(keep)}
    out.update({"accuracy": obs, "ci95": (float(lo), float(hi)), "baseline": baseline, "p_permutation": float(p_perm), "per_class_recall": per, "n_groups": int(len(ug))})
    out["trusted"] = bool(lo > baseline and p_perm < 0.05)
    out["reason"] = ("Held-out accuracy beats always guessing the most common class (interval excludes it) and beats shuffled labels (permutation p = %.3f)." % p_perm if out["trusted"] else
                     "Held-out accuracy does not clearly beat always guessing the most common class and shuffled labels, so the features do not carry usable signal on this labelled set. No prediction is shown.")
    return out


def predict_orphans(data: Dict[str, Dict], labels: Dict[str, str], targets: Sequence[str], report: Dict) -> List[Dict]:
    """Class probabilities for target genes, ONLY if the self-test passed. Empty list otherwise."""
    if not report.get("trusted"):
        return []
    cols = report["cols"]; keep = set(report["classes"])
    rows, y = [], []
    for g, lab in labels.items():
        d = data.get(g); f = features(d["seq"], d["tms"]) if d else None
        if f and lab in keep:
            rows.append(f); y.append(lab)
    m = _fit(_matrix(rows, cols), np.array(y))
    out = []
    for g in targets:
        d = data.get(g); f = features(d["seq"], d["tms"]) if d else None
        if not f:
            continue
        p = m.predict_proba(_matrix([f], cols))[0]
        out.append({"gene": g, "probabilities": {c: round(float(v), 3) for c, v in zip(m.classes_, p)}, "top": str(m.classes_[int(np.argmax(p))])})
    return out
