"""A small learned model (softmax regression, numpy only) to compare against the baselines.

Features for a receptor, computed ONLY from the labelled pool it is allowed to see:
  - the share of each ligand class among receptors on its chromosome band (neighbours), and whether it has any neighbour
  - which tissues it is expressed in (if tissue data was supplied)
It can abstain when it has no neighbour and no tissue information. It is deliberately simple: with a few hundred cases a complex model
would only memorise."""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .schema import Case, TISSUE_VOCAB


class LearnedModel:
    def __init__(self, l2: float = 1.0, iters: int = 300, lr: float = 0.5, use_tissue: bool = True):
        self.l2, self.iters, self.lr, self.use_tissue = l2, iters, lr, use_tissue

    def _feats(self, c: Case, pool: List[Case]) -> np.ndarray:
        nb = [p for p in pool if p.id != c.id and c.cluster and p.cluster == c.cluster]
        frac = [sum(1 for p in nb if p.ligand_class == k) / len(nb) if nb else 0.0 for k in self.classes_]
        t = [1.0 if tt in c.tissues else 0.0 for tt in TISSUE_VOCAB] if self.use_tissue else []
        return np.array([1.0, 1.0 if nb else 0.0] + frac + t)

    def fit(self, cases: List[Case]) -> "LearnedModel":
        self.classes_ = sorted({c.ligand_class for c in cases})
        self.pool_ = list(cases)
        X = np.array([self._feats(c, cases) for c in cases])
        y = np.array([self.classes_.index(c.ligand_class) for c in cases])
        Y = np.eye(len(self.classes_))[y]
        W = np.zeros((X.shape[1], len(self.classes_)))
        for _ in range(self.iters):
            Z = X @ W
            P = np.exp(Z - Z.max(1, keepdims=True)); P /= P.sum(1, keepdims=True)
            G = X.T @ (P - Y) / len(X) + self.l2 * W / len(X)
            W -= self.lr * G
        self.W_ = W
        return self

    def predict(self, c: Case) -> Optional[Dict[str, float]]:
        """Class -> probability-like score, or None to abstain (no neighbour and no tissue information)."""
        x = self._feats(c, self.pool_)
        if x[1] == 0.0 and not any(x[2 + len(self.classes_):]):
            return None
        z = x @ self.W_
        p = np.exp(z - z.max()); p /= p.sum()
        return dict(zip(self.classes_, map(float, p)))
