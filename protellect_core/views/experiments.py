"""Experiments: the next experiments, ranked, each one traceable to the evidence that calls for it. No templated protocols, no invented costs or success rates."""
from __future__ import annotations

import streamlit as st

from ..analysis import CITE, rank_variants, variant_plan
from ..evidence import Claim, Proof
from .common import data_audit, render_claims
from .shell import Analysis


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
    return sorted(out, key=lambda c: -c.score)


def render_experiments(a: Analysis, helpers: dict) -> None:
    b = a.b
    ss = st.session_state
    if ss.get("csv_df") is not None and helpers.get("render_csv_experiments"):
        with st.expander(f"Your uploaded data: {ss.get('csv_filename', 'wet-lab data')}", expanded=not b.loaded):
            try:
                helpers["render_csv_experiments"]()
            except Exception as e:
                st.warning(f"Could not analyse the uploaded file: {type(e).__name__}: {e}")
    if not b.loaded and a.summary is None:
        st.info("Search a protein or upload an experiment to get a ranked list of next experiments.")
        return
    st.markdown("#### Next experiments, ranked by the evidence that calls for them")
    st.caption("Each entry names what it would settle and carries the proof behind it. Costs and success probabilities are not shown because no source supports them.")
    render_claims(_experiment_claims(a), b, "exp", limit=10, empty="The data retrieved do not yet call for a specific experiment. See the data audit for what is missing.", how_label="What to do")
    if b.loaded:
        data_audit(b)
