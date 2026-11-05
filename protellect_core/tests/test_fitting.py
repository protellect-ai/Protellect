import numpy as np, pytest
from protellect_core.fitting import fit_dose_response, compare_dose_response, fit_kinetics, _four_pl

rng = np.random.default_rng(3)
CONC = 10.0 ** np.arange(-10, -4.4, 0.5)


def curve(logec, noise=2.0, top=100, bottom=0, hill=1.0, reps=2):
    x = np.repeat(CONC, reps)
    return x, _four_pl(np.log10(x), bottom, top, logec, hill) + rng.normal(0, noise, len(x))


def test_single_curve_recovers_ec50():
    x, y = curve(-7.5)
    r = fit_dose_response(x, y)
    assert abs(r["log10_ec50"] + 7.5) < 0.15 and r["ci95_log10"][0] < -7.5 < r["ci95_log10"][1] and not r["warnings"]


def test_real_shift_detected_and_no_shift_not_called():
    xa, ya = curve(-8.0); xb, yb = curve(-7.0)
    s = compare_dose_response(xa, ya, xb, yb)
    assert s["significant"] and abs(s["shift_log10"] - 1.0) < 0.25 and 5 < s["fold_shift"] < 20
    lo, hi = s["ci95_shift_log10"]; assert lo < 1.0 < hi
    xc, yc = curve(-8.0); xd, yd = curve(-8.0)
    assert not compare_dose_response(xc, yc, xd, yd)["significant"]


def test_false_positive_rate_under_the_null():
    hits = 0
    for _ in range(60):
        xa, ya = curve(-7.5, noise=4); xb, yb = curve(-7.5, noise=4)
        hits += compare_dose_response(xa, ya, xb, yb)["p_value"] < 0.05
    assert hits <= 8     # ~5% expected; guards against an anti-conservative test


def test_edge_ec50_and_too_few_points_are_flagged():
    x, y = curve(-3.0)
    assert any("edge" in w or "poorly" in w for w in fit_dose_response(x, y)["warnings"])
    with pytest.raises(ValueError):
        fit_dose_response(CONC[:3], [1, 2, 3])


def spr(kon=2e5, koff=2e-3, rmax=100, concs=(2e-8, 1e-7, 5e-7), ts=120, te=400, noise=0.8):
    T, C, R = [], [], []
    for c in concs:
        kobs = kon * c + koff
        req = rmax * kon * c / kobs
        for t in np.arange(0, te, 4.0):
            a = req * (1 - np.exp(-kobs * min(t, ts)))
            v = a * np.exp(-koff * max(t - ts, 0))
            T.append(t); C.append(c); R.append(v + rng.normal(0, noise))
    return T, C, R


def test_kinetics_recovered_within_tolerance():
    T, C, R = spr()
    r = fit_kinetics(T, C, R, 120)
    assert abs(np.log10(r["kon_per_M_s"]) - np.log10(2e5)) < 0.15 and abs(np.log10(r["koff_per_s"]) - np.log10(2e-3)) < 0.15
    assert abs(np.log10(r["Kd_M"]) - np.log10(1e-8)) < 0.2 and not r["warnings"]


def test_kinetics_warns_when_no_dissociation_seen_and_rejects_bad_input():
    T, C, R = spr(koff=1e-5, ts=120, te=200)
    assert any("dissociation" in w for w in fit_kinetics(T, C, R, 120)["warnings"])
    T1, C1, R1 = spr(concs=(1e-7,))
    with pytest.raises(ValueError):
        fit_kinetics(T1, C1, R1, 120)
    with pytest.raises(ValueError):
        fit_kinetics(T, C, R, 9999)
