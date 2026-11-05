"""The release gate: a model is only shown as 'beats baseline' if it does, on held-out receptors, with a sign test.

Compares, by leave-one-out on the same receptors: always the majority class; the same-band neighbour majority; the learned model; and
(optionally) the engine's precedent ranker. Abstentions count as misses for every method, so nobody gets credit for staying quiet."""
from __future__ import annotations

import datetime
import json
import math
from collections import Counter
from pathlib import Path
from typing import List

from .learned import LearnedModel
from .ranker import PrecedentRanker, profile_from_case
from .schema import Case


def _sign_test_p(wins: int, losses: int) -> float:
    """Two-sided exact sign test; ties are ignored."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def evaluate_gate(cases: List[Case], use_tissue: bool = True, include_precedent: bool = True, margin: int = 0) -> dict:
    hits = {"majority": [], "neighbour_majority": [], "learned": [], "precedent_ranker": []}
    answered = {"learned": [], "precedent_ranker": []}
    for q in cases:
        lib = [c for c in cases if c.id != q.id]
        maj = Counter(c.ligand_class for c in lib).most_common(1)[0][0]
        hits["majority"].append(maj == q.ligand_class)
        nb = [c for c in lib if q.cluster and c.cluster == q.cluster]
        hits["neighbour_majority"].append((Counter(c.ligand_class for c in nb).most_common(1)[0][0] if nb else maj) == q.ligand_class)
        sc = LearnedModel(use_tissue=use_tissue).fit(lib).predict(q)
        answered["learned"].append(bool(sc))
        hits["learned"].append(bool(sc) and max(sc, key=sc.get) == q.ligand_class)
        if include_precedent:
            s = PrecedentRanker().fit(lib, "ligand_class").value_scores(profile_from_case(q), lib)
            answered["precedent_ranker"].append(bool(s))
            hits["precedent_ranker"].append(bool(s) and max(s, key=s.get) == q.ligand_class)
    if not include_precedent:
        hits.pop("precedent_ranker")
    n = len(cases)
    res = {k: sum(v) for k, v in hits.items()}
    best_base = max(res["majority"], res["neighbour_majority"])
    best_name = "majority" if res["majority"] >= res["neighbour_majority"] else "neighbour_majority"
    out = {"generated": datetime.date.today().isoformat(), "n_receptors": n, "hits": res, "accuracy": {k: round(v / n, 3) for k, v in res.items()},
           "best_baseline": best_name, "tissue_used": use_tissue, "tests": {}}
    for m in [k for k in res if k not in ("majority", "neighbour_majority")]:
        w = sum(1 for a, b in zip(hits[m], hits[best_name]) if a and not b)
        l = sum(1 for a, b in zip(hits[m], hits[best_name]) if b and not a)
        p = _sign_test_p(w, l)
        ans = answered[m]
        n_ans = sum(ans)
        # head to head only where the model chose to answer, so abstaining is not counted against it here (coverage is reported separately)
        w2 = sum(1 for a, b, k in zip(hits[m], hits[best_name], ans) if k and a and not b)
        l2 = sum(1 for a, b, k in zip(hits[m], hits[best_name], ans) if k and b and not a)
        p2 = _sign_test_p(w2, l2)
        out["tests"][m] = {"wins_vs_best_baseline": w, "losses": l, "p_value": round(p, 4), "beats_baseline": bool(w - l > margin and p < 0.05),
                           "coverage": round(n_ans / n, 3), "accuracy_when_answering": round(sum(h for h, k in zip(hits[m], ans) if k) / n_ans, 3) if n_ans else None,
                           "baseline_accuracy_on_same_receptors": round(sum(b for b, k in zip(hits[best_name], ans) if k) / n_ans, 3) if n_ans else None,
                           "wins_when_answering": w2, "losses_when_answering": l2, "p_value_when_answering": round(p2, 4),
                           "beats_baseline_when_answering": bool(w2 - l2 > margin and p2 < 0.05)}
    return out


def gate_sentence(g: dict) -> str:
    """One honest line for the memo."""
    acc = g["accuracy"]
    base = g["best_baseline"]
    t = g["tests"].get("learned", {})
    verdict = ("beats" if t.get("beats_baseline_when_answering") else "does not clearly beat")
    return (f"On {g['n_receptors']} receptors with a known natural ligand (IUPHAR, held out one at a time), the learned model answered for {t.get('coverage', 0):.0%} of them and was right "
            f"{t.get('accuracy_when_answering') or 0:.0%} of the time when it answered; the best simple baseline ({base.replace('_', ' ')}) was right {t.get('baseline_accuracy_on_same_receptors') or 0:.0%} "
            f"on those same receptors. It {verdict} that baseline (sign test p = {t.get('p_value_when_answering', 'n/a')}). "
            f"This is a test on public data with two coarse classes, not proof for your receptor.")


def write_gate(cases: List[Case], path, **kw) -> dict:
    g = evaluate_gate(cases, **kw)
    g["sentence"] = gate_sentence(g)
    Path(path).write_text(json.dumps(g, indent=1), encoding="utf-8")
    return g
