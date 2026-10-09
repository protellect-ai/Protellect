"""Experiments: the next experiments, ranked, each one traceable to the evidence that calls for it. No templated protocols, no invented costs or success rates."""
from __future__ import annotations

import streamlit as st

from ..analysis import CITE, rank_variants, variant_plan
from ..evidence import Claim, Proof
from ..assays import assays_for
from .common import render_claims
from .dossier_view import render_plan
from .shell import Analysis
from ..kinetics import kinetics, reading, fmt_molar, fmt_time


def _experiment_claims(a: Analysis):
    b = a.b
    out = []
    for c in a.hyp_claims[:4]:
        out.append(Claim(text=f"Confirm or refute: {c.text}", proofs=c.proofs, kind="rule", score=10 + c.score, tags=dict(c.tags), how=c.how, basis="This is the assay that directly tests the hypothesis; a positive result in receptor-expressing cells with empty-vector controls is the standard confirmation."))
    for c in a.strategies[:3]:
        out.append(Claim(text=f"{c.text}: first experiment", proofs=c.proofs, kind="rule", score=5 + c.score, tags=dict(c.tags), how=c.how, basis=c.basis))
    plp = [v for v in rank_variants(b) if v.is_plp][:3]
    for v in plp:
        plan = variant_plan(v, b)
        fn = next(s for s in plan if s["step"] in ("Run a functional assay", "Test expression"))
        out.append(Claim(text=f"Functional test for {v.name.split('(')[-1].rstrip(')')[:40] or 'variant'} (residue {v.pos})", kind="rule", score=3 + v.stars,
                         proofs=[Proof("ClinVar", f"{v.significance}, {v.stars} star(s), {v.condition or 'no condition listed'}", v.url or ""), CITE["acmg"]],
                         basis=fn["basis"], tags={"n_supporting": 1, "max_stars": v.stars, "domain": "clinvar"}, how=[fn["do"]]))
    for c in out:
        cat = str(c.tags.get("category", "") or c.tags.get("domain", ""))
        ks = assays_for("variant" if cat == "clinvar" else cat)
        if ks:
            c.tags["assay"] = ks[0]
    return sorted(out, key=lambda c: -c.score)


def _kinetics_panel() -> None:
    with st.expander("Binding kinetics calculator (from rates you measured)", expanded=False):
        st.caption("Arithmetic on your own SPR, BLI or radioligand rates. It does not predict kon or koff; that needs a ligand-bound structure and long simulations.")
        c1, c2, c3 = st.columns(3)
        kon = c1.number_input("kon (1/M/s)", min_value=0.0, value=0.0, format="%.3e", key="kin_kon")
        koff = c2.number_input("koff (1/s)", min_value=0.0, value=0.0, format="%.3e", key="kin_koff")
        conc = c3.number_input("Ligand concentration (M), optional", min_value=0.0, value=0.0, format="%.3e", key="kin_c")
        if kon > 0 and koff > 0:
            r = kinetics(kon, koff, conc or None)
            m = st.columns(3)
            m[0].metric("Kd", fmt_molar(r["Kd_M"])); m[1].metric("Residence time", fmt_time(r["residence_time_s"]))
            m[2].metric("Occupancy at your concentration", f"{r['occupancy'] * 100:.0f}%" if "occupancy" in r else "enter a concentration")
            st.markdown(reading(r))
        else:
            st.info("Enter kon and koff to see Kd, residence time and how long to incubate.")


def render_experiments(a: Analysis, helpers: dict) -> None:
    b = a.b
    ss = st.session_state
    if ss.get("csv_df") is not None and helpers.get("render_csv_experiments"):
        with st.expander(f"Your uploaded data: {ss.get('csv_filename', 'wet-lab data')}", expanded=not b.loaded):
            try:
                helpers["render_csv_experiments"]()
            except Exception as e:
                st.warning(f"Could not analyse the uploaded file: {type(e).__name__}: {e}")
    if not b.loaded and a.summary is None and a.gpcrome is None:
        st.info("Upload an experiment (a differential table, and optionally an expression matrix), or load the example case, to get a plan of next experiments. You do not need to search a protein.")
        return
    planned = render_plan(a)
    claims = _experiment_claims(a)
    if claims or b.loaded:
        st.markdown("#### " + ("More experiments for the protein you searched" if planned else "Next experiments, ranked by the evidence that calls for them"))
        st.caption("Each entry names what it would settle and carries the proof behind it. Costs and success probabilities are not shown because no source supports them.")
        render_claims(claims, b, "exp", limit=10, empty="The protein you searched does not yet call for a specific experiment. See the data audit on the Overview tab for what is missing.", how_label="What to do")
    elif not planned:
        st.info("The experiment you uploaded has no orphan GPCRs and no searched protein, so there is nothing specific to plan from. Check that the receptor list is loaded (Overview, Receptor registry).")
    _kinetics_panel()
