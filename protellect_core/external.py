"""Bring in scores from tools Protellect does not run (docking, AlphaFold-Multimer, Boltz) and say how far to trust them.

A raw docking score or interface confidence means little for an orphan receptor, because the pocket is uncertain and these
scores are not binding energies. The honest use is calibration: score ligands you KNOW bind this receptor (or a close
relative) and decoys that should not, with the same tool and settings. Then ask where the new compound falls.

Everything here is arithmetic on numbers you provide. Nothing is predicted.
"""
from __future__ import annotations

import json
import math
from typing import Dict, List, Optional, Sequence

import numpy as np


def auroc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Probability that a random known binder outscores a random decoy (higher = better scores; flip signs before calling for 'lower is better')."""
    p, n = np.asarray(pos, float), np.asarray(neg, float)
    if len(p) == 0 or len(n) == 0:
        return float("nan")
    wins = (p[:, None] > n[None, :]).sum() + 0.5 * (p[:, None] == n[None, :]).sum()
    return float(wins / (len(p) * len(n)))


def calibrate(pos: Sequence[float], neg: Sequence[float], query: Optional[Sequence[float]] = None, higher_is_better: bool = True, n_boot: int = 1000, seed: int = 0) -> Dict:
    """Does the score separate known binders from decoys, and where do query compounds fall relative to the decoys?"""
    sgn = 1.0 if higher_is_better else -1.0
    p = sgn * np.asarray([x for x in pos if x is not None and np.isfinite(x)], float)
    n = sgn * np.asarray([x for x in neg if x is not None and np.isfinite(x)], float)
    if len(p) < 5 or len(n) < 10:
        raise ValueError(f"Need at least 5 known binders and 10 decoys to calibrate (got {len(p)} and {len(n)}).")
    a = auroc(p, n)
    rng = np.random.default_rng(seed)
    boots = [auroc(rng.choice(p, len(p)), rng.choice(n, len(n))) for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # threshold maximising Youden's J on the supplied set (optimistic, as it is chosen on the same data)
    cand = np.unique(np.concatenate([p, n]))
    j = [((p >= t).mean() - (n >= t).mean(), t) for t in cand]
    jmax, thr = max(j)
    verdict = ("useful" if lo > 0.7 else "weak" if lo > 0.5 else "not useful")
    out = {"auroc": a, "ci95": (float(lo), float(hi)), "n_binders": int(len(p)), "n_decoys": int(len(n)), "verdict": verdict,
           "threshold": float(sgn * thr), "tpr_at_threshold": float((p >= thr).mean()), "fpr_at_threshold": float((n >= thr).mean()), "queries": []}
    for q in (query or []):
        if q is None or not np.isfinite(q):
            continue
        qs = sgn * float(q)
        frac_decoys_ge = float(((n >= qs).sum() + 1) / (len(n) + 1))     # empirical p with +1 smoothing
        frac_binders_ge = float((p >= qs).mean())
        out["queries"].append({"score": float(q), "p_vs_decoys": frac_decoys_ge, "binder_percentile": float(100 * (1 - frac_binders_ge)),
                               "call": ("looks like the known binders" if frac_decoys_ge < 0.05 and verdict != "not useful" else "indistinguishable from decoys")})
    return out


def reading(c: Dict) -> str:
    lo, hi = c["ci95"]
    if c["verdict"] == "not useful":
        return (f"With this tool and these settings the score does NOT separate known binders from decoys (AUROC {c['auroc']:.2f}, 95% CI {lo:.2f} to {hi:.2f}). "
                "Do not use it to rank compounds for this receptor; try another pose protocol, a different structure, or a different method.")
    s = (f"The score separates known binders from decoys with AUROC {c['auroc']:.2f} (95% CI {lo:.2f} to {hi:.2f}; {c['n_binders']} binders, {c['n_decoys']} decoys). "
         f"At the best cut-off it keeps {c['tpr_at_threshold'] * 100:.0f}% of binders and lets through {c['fpr_at_threshold'] * 100:.0f}% of decoys (chosen on this same set, so optimistic).")
    return s + (" The interval is wide: add more binders and decoys." if hi - lo > 0.3 else "") + " It ranks compounds; it does not give affinity."


_CONF_KEYS = ("ranking_confidence", "confidence_score", "iptm", "ptm", "complex_plddt", "complex_iplddt", "chains_ptm", "plddt", "ligand_iptm", "protein_iptm",
              "affinity_pred_value", "affinity_probability_binary")


def parse_confidence_json(text: str) -> Dict[str, float]:
    """Pull the confidence numbers out of an AlphaFold-Multimer / AlphaFold3 / Boltz / Chai-style JSON, wherever they are nested."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        raise ValueError("That is not valid JSON.")
    found: Dict[str, float] = {}

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                kl = str(k).lower()
                if kl in _CONF_KEYS and kl not in found:
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                        found[kl] = float(v)
                    elif isinstance(v, list) and v and all(isinstance(t, (int, float)) for t in v):
                        found[kl] = float(np.mean(v))
                walk(v)
        elif isinstance(x, list):
            for v in x[:2000]:
                walk(v)
    walk(data)
    if not found:
        raise ValueError("No recognised confidence values (iptm, ptm, plddt, confidence_score, ranking_confidence, affinity) were found.")
    return found


def interface_reading(conf: Dict[str, float]) -> List[str]:
    """Plain statements about what the numbers do and do not say."""
    out = []
    if "iptm" in conf:
        i = conf["iptm"]
        band = "high (a confident interface)" if i >= 0.8 else "intermediate (treat as a hypothesis)" if i >= 0.6 else "low (the predicted interface is not trustworthy)"
        out.append(f"ipTM {i:.2f}: {band}. ipTM is confidence in the predicted arrangement, not binding affinity.")
    if "ptm" in conf and conf["ptm"] < 0.5:
        out.append(f"pTM {conf['ptm']:.2f} is low: the overall fold of the complex is uncertain.")
    if "affinity_pred_value" in conf:
        out.append("An affinity value is present in the file. Treat it as an unvalidated estimate from a model, and calibrate it against known binders and decoys before using it to rank.")
    out.append("Compare with the same tool on known ligand-receptor pairs and on scrambled or unrelated sequences; a number without that comparison cannot support a claim.")
    return out
