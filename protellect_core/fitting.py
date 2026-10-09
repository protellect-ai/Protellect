"""Curve fitting for YOUR measured data: dose-response shifts (heterodimer or co-expression effects) and SPR/BLI kinetics.

Both functions fit numbers the user supplies and report uncertainty and warnings. Neither predicts anything about a receptor
that has not been measured.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np
from scipy import stats
from scipy.optimize import least_squares


# ---------------------------------------------------------------- dose-response (4-parameter logistic)
def _four_pl(logx, bottom, top, logec50, hill):
    return bottom + (top - bottom) / (1.0 + 10 ** ((logec50 - logx) * hill))


def fit_dose_response(conc_M: Sequence[float], resp: Sequence[float]) -> Dict:
    """Single curve. conc in molar (must be > 0). Returns EC50 (M) with 95% CI on log10 EC50, Hill, top, bottom."""
    x = np.asarray(conc_M, float); y = np.asarray(resp, float)
    ok = np.isfinite(x) & np.isfinite(y) & (x > 0)
    x, y = x[ok], y[ok]
    if len(x) < 6 or len(set(np.round(np.log10(x), 6))) < 4:
        raise ValueError("Need at least 6 points over at least 4 different concentrations.")
    lx = np.log10(x)
    p0 = [y.min(), y.max(), float(np.median(lx)), 1.0]
    lo = [y.min() - abs(np.ptp(y)), y.min(), lx.min() - 2, 0.2]; hi = [y.max(), y.max() + abs(np.ptp(y)), lx.max() + 2, 5.0]
    r = least_squares(lambda p: _four_pl(lx, *p) - y, p0, bounds=(lo, hi))
    n, k = len(y), 4
    dof = n - k
    s2 = float((r.fun ** 2).sum() / dof)
    try:
        cov = np.linalg.inv(r.jac.T @ r.jac) * s2
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(4, np.nan)
    t = stats.t.ppf(0.975, dof)
    le, sle = float(r.x[2]), float(se[2])
    warn = []
    if le <= lx.min() + 0.05 or le >= lx.max() - 0.05:
        warn.append("EC50 lies at the edge of the concentration range tested; extend the range.")
    if not np.isfinite(sle) or sle > 0.5:
        warn.append("EC50 is poorly determined (95% CI wider than about 1 log unit).")
    return {"bottom": float(r.x[0]), "top": float(r.x[1]), "log10_ec50": le, "ec50_M": 10 ** le, "hill": float(r.x[3]),
            "ci95_log10": (le - t * sle, le + t * sle), "rss": float((r.fun ** 2).sum()), "n": n, "warnings": warn}


def compare_dose_response(conc_a, resp_a, conc_b, resp_b) -> Dict:
    """Is curve B shifted relative to curve A? Global fit with shared bottom, top and Hill, separate vs shared EC50,
    compared by an extra-sum-of-squares F test (1 df). Returns the shift in log10 units, fold shift, p value."""
    xa, ya = np.asarray(conc_a, float), np.asarray(resp_a, float)
    xb, yb = np.asarray(conc_b, float), np.asarray(resp_b, float)
    ma, mb = np.isfinite(xa) & np.isfinite(ya) & (xa > 0), np.isfinite(xb) & np.isfinite(yb) & (xb > 0)
    xa, ya, xb, yb = xa[ma], ya[ma], xb[mb], yb[mb]
    if len(xa) < 6 or len(xb) < 6:
        raise ValueError("Each curve needs at least 6 points.")
    la, lb = np.log10(xa), np.log10(xb)
    yall = np.concatenate([ya, yb]); n = len(yall)
    lo_all = [yall.min() - abs(np.ptp(yall)), yall.min(), min(la.min(), lb.min()) - 2, min(la.min(), lb.min()) - 2, 0.2]
    hi_all = [yall.max(), yall.max() + abs(np.ptp(yall)), max(la.max(), lb.max()) + 2, max(la.max(), lb.max()) + 2, 5.0]
    mid = float(np.median(np.concatenate([la, lb])))

    def full(p):  # bottom, top, ecA, ecB, hill
        return np.concatenate([_four_pl(la, p[0], p[1], p[2], p[4]) - ya, _four_pl(lb, p[0], p[1], p[3], p[4]) - yb])

    def red(p):   # bottom, top, ec, hill
        return np.concatenate([_four_pl(la, p[0], p[1], p[2], p[3]) - ya, _four_pl(lb, p[0], p[1], p[2], p[3]) - yb])

    f = least_squares(full, [yall.min(), yall.max(), mid, mid, 1.0], bounds=(lo_all, hi_all))
    keep = [0, 1, 2, 4]
    g = least_squares(red, [yall.min(), yall.max(), mid, 1.0], bounds=([lo_all[i] for i in keep], [hi_all[i] for i in keep]))
    rss_f, rss_r = float((f.fun ** 2).sum()), float((g.fun ** 2).sum())
    dof = n - 5
    F = max(((rss_r - rss_f) / 1) / (rss_f / dof), 0.0) if rss_f > 0 else float("inf")
    p = float(stats.f.sf(F, 1, dof)) if np.isfinite(F) else 0.0
    shift = float(f.x[3] - f.x[2])
    s2 = rss_f / dof
    try:
        cov = np.linalg.inv(f.jac.T @ f.jac) * s2
        sd = math.sqrt(max(cov[2, 2] + cov[3, 3] - 2 * cov[2, 3], 0))
    except np.linalg.LinAlgError:
        sd = float("nan")
    t = stats.t.ppf(0.975, dof)
    warn = []
    if p < 0.05 and not np.isfinite(sd):
        warn.append("Shift interval could not be estimated.")
    if min(len(xa), len(xb)) < 8:
        warn.append("Few points per curve; replicate curves would make this test far more reliable.")
    return {"log10_ec50_a": float(f.x[2]), "log10_ec50_b": float(f.x[3]), "shift_log10": shift, "fold_shift": 10 ** shift,
            "ci95_shift_log10": (shift - t * sd, shift + t * sd), "F": F, "p_value": p, "dof": dof, "significant": p < 0.05, "warnings": warn}


# ---------------------------------------------------------------- SPR / BLI 1:1 kinetics
def fit_kinetics(t: Sequence[float], conc_M: Sequence[float], resp: Sequence[float], t_switch: float) -> Dict:
    """Global 1:1 Langmuir fit. Rows are (time s, analyte concentration M, response); t_switch is when the injection ends and
    dissociation starts (same for all concentrations, time measured from injection start). Needs >= 2 concentrations."""
    t = np.asarray(t, float); c = np.asarray(conc_M, float); y = np.asarray(resp, float)
    ok = np.isfinite(t) & np.isfinite(c) & np.isfinite(y) & (c > 0) & (t >= 0)
    t, c, y = t[ok], c[ok], y[ok]
    concs = sorted(set(np.round(c, 15)))
    if len(concs) < 2:
        raise ValueError("Need at least 2 analyte concentrations for a reliable kon/koff fit.")
    if not (t.min() < t_switch < t.max()):
        raise ValueError("t_switch must lie inside the time range.")
    assoc = t <= t_switch
    if assoc.sum() < 10 or (~assoc).sum() < 10:
        raise ValueError("Need at least 10 points in both the association and dissociation phases.")

    def model(p, tt, cc):
        lkon, lkoff, rmax = p
        kon, koff = 10 ** lkon, 10 ** lkoff
        kobs = kon * cc + koff
        req = rmax * cc * kon / kobs
        a = req * (1 - np.exp(-kobs * np.minimum(tt, t_switch)))
        d = a * np.exp(-koff * np.maximum(tt - t_switch, 0))
        return d

    best = None
    for lk0 in (3.5, 5, 6.5):
        for lo0 in (-4, -2.5, -1):
            r = least_squares(lambda p: model(p, t, c) - y, [lk0, lo0, float(np.max(y)) * 1.2],
                              bounds=([0, -7, 1e-9], [9, 1, float(np.max(y)) * 20 + 1]))
            if best is None or r.cost < best.cost:
                best = r
    r = best
    n = len(y); dof = n - 3
    s2 = float((r.fun ** 2).sum() / dof)
    try:
        cov = np.linalg.inv(r.jac.T @ r.jac) * s2
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(3, np.nan)
    kon, koff = 10 ** r.x[0], 10 ** r.x[1]
    rmse = math.sqrt(float((r.fun ** 2).mean()))
    warn: List[str] = []
    window = float(t.max() - t_switch)
    if koff * window < 0.05:
        warn.append("Almost no dissociation was observed in the window, so koff is only an upper-bound estimate; lengthen the dissociation phase.")
    if r.x[0] >= 8.99 or r.x[1] <= -6.99 or r.x[1] >= 0.99:
        warn.append("A rate sits at the edge of the allowed range; the fit is not constrained by this data.")
    if rmse > 0.1 * float(np.max(y)):
        warn.append("Residuals exceed 10% of the maximum response; a 1:1 model may not describe this interaction (heterogeneity, rebinding or mass transport).")
    if max(se[0], se[1]) > 0.3:
        warn.append("Rate uncertainty is larger than about two-fold; add concentrations that bracket the Kd.")
    return {"kon_per_M_s": kon, "koff_per_s": koff, "Kd_M": koff / kon, "Rmax": float(r.x[2]), "rmse": rmse,
            "se_log10_kon": float(se[0]), "se_log10_koff": float(se[1]), "n_points": n, "n_concentrations": len(concs), "warnings": warn}
