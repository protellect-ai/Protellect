"""The 'ML layer': a small, transparent learned weighting over precedent-similarity features.

For a (query receptor, precedent case) pair we compute a few similarity features. A logistic
regression (plain numpy, no extra dependencies) learns, from historical cases only, which features have actually predicted that two
receptors share a ligand class (or G-protein coupling). It is deliberately simple: the case library
is small, so a deep model would only memorize it. Weights are inspectable via `weights()`.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np

from .schema import Case, QueryProfile

FEATURES = ("tissue_overlap", "neighbor_link", "same_cluster")


def _norm(s: str) -> str:
    return s.strip().lower()


def profile_from_case(c: Case) -> QueryProfile:
    return QueryProfile(id=c.id, names=[c.id, c.gene], tissues=list(c.tissues),
                        neighbors=list(c.neighbors), cluster=c.cluster)


def pair_features(q: QueryProfile, p: Case) -> List[float]:
    qt, pt = {_norm(t) for t in q.tissues}, {_norm(t) for t in p.tissues}
    union = qt | pt
    tissue_overlap = len(qt & pt) / len(union) if union else 0.0

    q_names = {_norm(n) for n in (q.names or [q.id])}
    p_names = {_norm(p.id), _norm(p.gene)}
    qn, pn = {_norm(n) for n in q.neighbors}, {_norm(n) for n in p.neighbors}
    neighbor_link = 1.0 if (qn & p_names) or (pn & q_names) or (qn & pn) else 0.0

    same_cluster = 1.0 if q.cluster and p.cluster and _norm(q.cluster) == _norm(p.cluster) else 0.0
    return [tissue_overlap, neighbor_link, same_cluster]


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logistic(X: np.ndarray, y: np.ndarray, C: float = 1.0, iters: int = 100):
    """L2-regularized logistic regression with balanced class weights, fit by Newton's method.

    Minimizes 0.5*||w||^2 + C * sum_i sw_i * logloss_i (the same convention scikit-learn uses),
    with the intercept unpenalized. Returns (weights, intercept). Deterministic.
    """
    n, d = X.shape
    Xb = np.hstack([X, np.ones((n, 1))])
    n_pos = max(int(y.sum()), 1)
    n_neg = max(n - int(y.sum()), 1)
    sw = np.where(y == 1, n / (2.0 * n_pos), n / (2.0 * n_neg))
    reg = np.diag(np.r_[np.ones(d), 0.0])
    beta = np.zeros(d + 1)
    for _ in range(iters):
        p = _sigmoid(Xb @ beta)
        grad = reg @ beta + C * (Xb.T @ (sw * (p - y)))
        hess = reg + C * (Xb.T * (sw * p * (1 - p))) @ Xb + 1e-9 * np.eye(d + 1)
        step = np.linalg.solve(hess, grad)
        beta -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta[:d], float(beta[d])


class PrecedentRanker:
    def __init__(self, C: float = 1.0):
        self.C = C
        self.model = None
        self.target = "ligand_class"

    def fit(self, library: Sequence[Case], target: str = "ligand_class") -> "PrecedentRanker":
        self.target = target
        X, y = [], []
        for q in library:
            qp = profile_from_case(q)
            for p in library:
                if p.id == q.id:
                    continue
                X.append(pair_features(qp, p))
                y.append(1 if getattr(q, target) == getattr(p, target) else 0)
        if len(set(y)) < 2 or len(y) < 6:
            self.model = None  # not enough signal to learn from: fall back to an unweighted average
            return self
        self.model = fit_logistic(np.array(X, dtype=float), np.array(y, dtype=float), C=self.C)
        return self

    def weights(self) -> Dict[str, float]:
        if self.model is None:
            return {f: 1.0 / len(FEATURES) for f in FEATURES}
        return {f: float(w) for f, w in zip(FEATURES, self.model[0])}

    def pair_score(self, q: QueryProfile, p: Case) -> float:
        feats = pair_features(q, p)
        if not any(feats):
            return 0.0  # no shared evidence at all -> no support, regardless of the model's intercept
        if self.model is None:
            return float(sum(feats) / len(feats))
        w, b = self.model
        return float(_sigmoid(np.dot(w, feats) + b))

    def scored_precedents(self, q: QueryProfile, library: Sequence[Case]) -> List[dict]:
        out = []
        for p in library:
            s = self.pair_score(q, p)
            if s > 0:
                out.append({"case": p, "score": s, "features": dict(zip(FEATURES, pair_features(q, p)))})
        return sorted(out, key=lambda d: d["score"], reverse=True)

    def value_scores(self, q: QueryProfile, library: Sequence[Case]) -> Dict[str, float]:
        """Relative support per candidate value (sums to 1). Empty dict means: no evidence, abstain."""
        totals: Dict[str, float] = {}
        for d in self.scored_precedents(q, library):
            v = getattr(d["case"], self.target)
            totals[v] = totals.get(v, 0.0) + d["score"]
        s = sum(totals.values())
        return {k: v / s for k, v in totals.items()} if s > 0 else {}
