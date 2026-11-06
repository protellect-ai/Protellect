"""Experiments tab: fit YOUR dose-response and SPR/BLI data."""
from __future__ import annotations

import io
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from ..kinetics import fmt_molar, fmt_time, reading, kinetics

UNITS = {"M": 1.0, "mM": 1e-3, "µM": 1e-6, "nM": 1e-9, "pM": 1e-12}


def _col(df: pd.DataFrame, *names: str) -> Optional[str]:
    low = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        for k, c in low.items():
            if k == n or k.startswith(n):
                return c
    return None


def parse_dose_table(df: pd.DataFrame, unit: str) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Columns: concentration, response, optional group (e.g. 'alone', 'co-expressed'). Returns {group: (conc_M, resp)}."""
    cc, rc, gc = _col(df, "conc", "dose", "ligand"), _col(df, "resp", "signal", "value", "effect"), _col(df, "group", "condition", "sample", "construct")
    if cc is None or rc is None:
        raise ValueError("Need columns named like 'concentration' and 'response' (plus an optional 'group').")
    x = pd.to_numeric(df[cc], errors="coerce") * UNITS[unit]
    y = pd.to_numeric(df[rc], errors="coerce")
    g = df[gc].astype(str) if gc else pd.Series(["all"] * len(df))
    out = {}
    for name in pd.unique(g):
        m = (g == name) & x.notna() & y.notna() & (x > 0)
        if m.sum():
            out[str(name)] = (x[m].to_numpy(), y[m].to_numpy())
    if not out:
        raise ValueError("No usable rows: concentrations must be positive numbers.")
    return out


def parse_spr_table(df: pd.DataFrame, unit: str):
    tc, cc, rc = _col(df, "time", "t"), _col(df, "conc", "analyte"), _col(df, "resp", "signal", "ru", "shift")
    if None in (tc, cc, rc):
        raise ValueError("Need columns named like 'time', 'concentration' and 'response'.")
    t = pd.to_numeric(df[tc], errors="coerce"); c = pd.to_numeric(df[cc], errors="coerce") * UNITS[unit]; r = pd.to_numeric(df[rc], errors="coerce")
    m = t.notna() & c.notna() & r.notna() & (c > 0)
    if not m.any():
        raise ValueError("No usable rows: concentration must be a positive number on every row.")
    return t[m].to_numpy(), c[m].to_numpy(), r[m].to_numpy()


TEMPLATE_DOSE = "concentration,response,group\n1e-10,2,alone\n1e-9,5,alone\n1e-8,20,alone\n1e-7,60,alone\n1e-6,92,alone\n1e-5,99,alone\n1e-10,3,co-expressed\n1e-9,12,co-expressed\n1e-8,48,co-expressed\n1e-7,88,co-expressed\n1e-6,98,co-expressed\n1e-5,100,co-expressed\n"


def _dose_chart(groups, fits):
    import altair as alt
    from ..fitting import _four_pl
    rows, lines = [], []
    for name, (x, y) in groups.items():
        for xi, yi in zip(x, y):
            rows.append({"log10 conc (M)": float(np.log10(xi)), "response": float(yi), "group": name})
        f = fits.get(name)
        if f:
            xs = np.linspace(np.log10(x.min()), np.log10(x.max()), 80)
            for xi, yi in zip(xs, _four_pl(xs, f["bottom"], f["top"], f["log10_ec50"], f["hill"])):
                lines.append({"log10 conc (M)": float(xi), "response": float(yi), "group": name})
    pts = alt.Chart(pd.DataFrame(rows)).mark_circle(size=60).encode(x="log10 conc (M):Q", y="response:Q", color="group:N")
    ln = alt.Chart(pd.DataFrame(lines)).mark_line().encode(x="log10 conc (M):Q", y="response:Q", color="group:N")
    return (pts + ln).properties(height=300)


def _dose_panel() -> None:
    try:
        from ..fitting import compare_dose_response, fit_dose_response
    except ImportError:
        st.warning("This panel needs scipy. Add scipy to requirements.txt and reboot the app.")
        return
    st.markdown("**Dose-response: EC50 and shift between conditions**")
    st.caption("Use this to test whether co-expressing a partner (for example GPR50 with MT1 or MT2) or adding an allosteric compound moves the curve. "
               "It fits your data; it does not predict a shift. Real shifts are only as good as your replicates.")
    st.download_button("Template: dose-response", TEMPLATE_DOSE, file_name="protellect_dose_response_template.csv", key="fit_tpl_dose")
    unit = st.selectbox("Concentration unit in your file", list(UNITS), index=0, key="fit_dose_unit")
    up = st.file_uploader("Dose-response table (CSV)", type=["csv", "tsv", "txt"], key="fit_dose_up")
    if up is None:
        return
    try:
        df = pd.read_csv(io.BytesIO(up.getvalue()), sep=None, engine="python")
        groups = parse_dose_table(df, unit)
        fits, errs = {}, {}
        for name, (x, y) in groups.items():
            try:
                fits[name] = fit_dose_response(x, y)
            except ValueError as e:
                errs[name] = str(e)
    except Exception as e:
        st.warning(f"Could not read the table: {e}")
        return
    st.altair_chart(_dose_chart(groups, fits), use_container_width=True)
    if fits:
        st.dataframe([{"Group": n, "EC50": fmt_molar(f["ec50_M"]), "log10 EC50 95% CI": f"{f['ci95_log10'][0]:.2f} to {f['ci95_log10'][1]:.2f}", "Hill": round(f["hill"], 2),
                       "Top": round(f["top"], 1), "Bottom": round(f["bottom"], 1), "Points": f["n"], "Notes": " ".join(f["warnings"]) or "ok"} for n, f in fits.items()], hide_index=True)
    for n, e in errs.items():
        st.warning(f"{n}: {e}")
    names = list(fits)
    if len(names) >= 2:
        a, b = st.columns(2)
        ga = a.selectbox("Reference curve", names, index=0, key="fit_dose_a")
        gb = b.selectbox("Compare with", names, index=1, key="fit_dose_b")
        if ga != gb:
            try:
                s = compare_dose_response(*groups[ga], *groups[gb])
                direction = "right (less potent)" if s["shift_log10"] > 0 else "left (more potent)"
                if s["significant"]:
                    st.success(f"**{gb}** is shifted {direction} relative to **{ga}**: {s['fold_shift']:.2g}-fold in EC50 (log10 shift {s['shift_log10']:.2f}, 95% CI {s['ci95_shift_log10'][0]:.2f} to {s['ci95_shift_log10'][1]:.2f}; F-test p = {s['p_value']:.3g}).")
                else:
                    st.info(f"No significant EC50 shift between **{ga}** and **{gb}** (log10 shift {s['shift_log10']:.2f}, 95% CI {s['ci95_shift_log10'][0]:.2f} to {s['ci95_shift_log10'][1]:.2f}; p = {s['p_value']:.2g}). That is not proof of no shift: check that the CI is narrow enough to exclude a shift that would matter.")
                for w in s["warnings"]:
                    st.caption(w)
                st.caption("What it might mean: a leftward shift on co-expression is consistent with the partner increasing agonist affinity or coupling efficiency; a rightward shift with competition or reduced surface expression. Control for expression level (surface ELISA or flow) before interpreting either, because expression alone moves EC50.")
            except ValueError as e:
                st.warning(str(e))


TEMPLATE_SPR = "time,concentration,response\n0,2e-8,0\n10,2e-8,3\n# one row per time point per concentration; add at least 2 concentrations; time in seconds from injection start\n"


def _spr_panel() -> None:
    try:
        from ..fitting import fit_kinetics
    except ImportError:
        st.warning("This panel needs scipy. Add scipy to requirements.txt and reboot the app.")
        return
    st.markdown("**SPR / BLI traces: kon, koff and Kd from raw curves**")
    st.caption("Global 1:1 fit across your concentrations. It reports uncertainty and says when the data cannot support the numbers.")
    unit = st.selectbox("Analyte concentration unit", list(UNITS), index=3, key="fit_spr_unit")
    ts = st.number_input("Injection ends at (s from start)", min_value=0.0, value=120.0, key="fit_spr_ts")
    up = st.file_uploader("Sensorgram table (CSV: time, concentration, response)", type=["csv", "tsv", "txt"], key="fit_spr_up")
    if up is None:
        return
    try:
        df = pd.read_csv(io.BytesIO(up.getvalue()), sep=None, engine="python", comment="#")
        t, c, r = parse_spr_table(df, unit)
        f = fit_kinetics(t, c, r, ts)
    except Exception as e:
        st.warning(f"Could not fit: {e}")
        return
    m = st.columns(4)
    m[0].metric("kon (1/M/s)", f"{f['kon_per_M_s']:.3g}"); m[1].metric("koff (1/s)", f"{f['koff_per_s']:.3g}")
    m[2].metric("Kd", fmt_molar(f["Kd_M"])); m[3].metric("Residence time", fmt_time(1 / f["koff_per_s"]))
    for w in f["warnings"]:
        st.warning(w)
    st.caption(f"{f['n_points']} points, {f['n_concentrations']} concentrations; log10 uncertainty kon ±{f['se_log10_kon']:.2f}, koff ±{f['se_log10_koff']:.2f}; residual RMSE {f['rmse']:.3g} (Rmax {f['Rmax']:.3g}).")
    st.markdown(reading(kinetics(f["kon_per_M_s"], f["koff_per_s"])))


def render_fits() -> None:
    with st.expander("Fit your own data: dose-response shifts and SPR/BLI kinetics", expanded=False):
        _dose_panel()
        st.divider()
        _spr_panel()


# ---------------------------------------------------------------- results from external docking / structure prediction
TEMPLATE_SCORES = "name,score,role\nknown_agonist_1,-9.8,binder\nknown_agonist_2,-9.1,binder\ndecoy_1,-6.2,decoy\ndecoy_2,-7.0,decoy\nnew_compound_A,-9.4,query\n"


def parse_score_table(df: pd.DataFrame):
    sc, rc = _col(df, "score", "dock", "energy", "affinity"), _col(df, "role", "label", "class", "type")
    nc = _col(df, "name", "ligand", "compound", "id")
    if sc is None or rc is None:
        raise ValueError("Need columns named like 'score' and 'role' (role is binder, decoy or query).")
    s = pd.to_numeric(df[sc], errors="coerce")
    r = df[rc].astype(str).str.strip().str.lower()
    names = df[nc].astype(str) if nc else pd.Series([str(i) for i in range(len(df))])
    ok = s.notna()
    pos = s[ok & r.isin(["binder", "positive", "known", "active", "1"])].tolist()
    neg = s[ok & r.isin(["decoy", "negative", "inactive", "0"])].tolist()
    q = [(n, float(v)) for n, v, rr, o in zip(names, s, r, ok) if o and rr in ("query", "test", "new", "unknown")]
    return pos, neg, q


def render_external() -> None:
    from ..external import calibrate, interface_reading, parse_confidence_json, reading as ext_reading
    with st.expander("Bring in docking or structure-prediction results and check how far to trust them", expanded=False):
        st.caption("Protellect does not run docking, AlphaFold-Multimer or Boltz. Run them elsewhere (a GPU service or your cluster), then bring the numbers here. "
                   "A raw score means little for an orphan receptor; what makes it usable is how it behaves on ligands you KNOW bind and on decoys, with the same tool and settings.")
        st.markdown("**1. Score table calibration**")
        st.download_button("Template: scores", TEMPLATE_SCORES, file_name="protellect_scores_template.csv", key="ext_tpl")
        lower = st.checkbox("Lower scores are better (docking energies such as Vina)", value=True, key="ext_lower")
        up = st.file_uploader("Scores (CSV: name, score, role = binder / decoy / query)", type=["csv", "tsv", "txt"], key="ext_up")
        if up is not None:
            try:
                pos, neg, q = parse_score_table(pd.read_csv(io.BytesIO(up.getvalue()), sep=None, engine="python"))
                c = calibrate(pos, neg, query=[v for _, v in q], higher_is_better=not lower)
            except Exception as e:
                st.warning(f"Could not calibrate: {e}")
            else:
                (st.success if c["verdict"] == "useful" else st.warning if c["verdict"] == "weak" else st.error)(ext_reading(c))
                if c["queries"]:
                    st.dataframe([{"Compound": n, "Score": f"{x['score']:.2f}", "p vs decoys": f"{x['p_vs_decoys']:.3f}", "Percentile among known binders": f"{x['binder_percentile']:.0f}", "Call": x["call"]}
                                  for (n, _), x in zip(q, c["queries"])], hide_index=True)
        st.divider()
        st.markdown("**2. Structure-prediction confidence (JSON from AlphaFold-Multimer, Boltz, Chai or similar)**")
        j = st.file_uploader("Confidence file", type=["json"], key="ext_json")
        if j is not None:
            try:
                conf = parse_confidence_json(j.getvalue().decode("utf-8", "ignore"))
            except ValueError as e:
                st.warning(str(e))
            else:
                st.dataframe([{"Value": k, "Number": round(v, 3)} for k, v in conf.items()], hide_index=True)
                for line in interface_reading(conf):
                    st.markdown("- " + line)
