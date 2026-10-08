"""Pattern-learned hypotheses: what the learned models say about the searched receptor, and how far to trust them."""
from __future__ import annotations

import streamlit as st

from ..engine.benchmark import retrodict
from ..network import bars_svg
from ..explain import plot_note
from .common import render_claims, svg
from .shell import Analysis


def _status(a: Analysis) -> str:
    return a.engine.registry.get(a.b.gene.upper(), {}).get("status", "")


def render_patterns(a: Analysis) -> None:
    b, eng = a.b, a.engine
    st.markdown("#### Pattern-learned hypotheses")
    st.caption("Models that learn from patterns: the precedent model (trained on documented deorphanisations, with a measured track record) and, when you load a matrix, "
               "the co-expression, enrichment and program analyses that learn from your own data. Each states how far to trust it.")
    if not b.loaded:
        if a.summary is not None:
            n_o = a.summary.n_orphan
            st.info(f"{n_o} orphan GPCR(s) in your experiment have ranked hypotheses in the table below; search one to see its full evidence." if n_o else
                    "No orphan GPCRs were recognised in your experiment. The full receptor list loads automatically; see the registry panel at the bottom if this looks low.")
        elif a.wb is not None:
            st.info("Your matrix is analysed below. Search a receptor to see what each model says about it.")
        else:
            st.info("Search a receptor, upload an experiment, or load the example case to see what the learned models predict.")
        return
    stt = _status(a)
    names = [b.gene] + [x for x in b.aliases if len(x) < 14]
    label = {"orphan": "orphan GPCR", "characterized": "characterised GPCR", "": "not in the receptor registry"}[stt if stt in ("orphan", "characterized") else ""]
    st.markdown(f"**{b.gene}** is a **{label}** per {st.session_state.get('_registry_label', 'the registry')}.")
    shown_any = False
    own = [c for c in a.hyp_claims if c.tags.get("category") in ("ligand-class", "signaling", "disease-analogy") and c.text.split(":")[0].upper() == b.gene.upper()]
    if stt == "orphan" and own:
        shown_any = True
        st.markdown("**Precedent model: what this orphan may bind and couple to**")
        render_claims(own, b, "pat", limit=4)
    r = next((x for x in (retrodict(eng.cases, n) for n in names) if x), None)
    if r:
        shown_any = True
        st.markdown(f"**Blind test of the precedent model on {r['gene']}**")
        st.caption(f"The model was retrained WITHOUT {r['gene']} (leaving {r['library']} other documented cases) and asked which ligand class it would have predicted, using only what was known about the receptor's context. "
                   f"It was resolved in {r['year']}. This is a test of the model, not a prediction about {r['gene']}.")
        if r["ranked"]:
            cols = ["#34d399" if k == r["truth"] else "#38bdf8" for k, _ in r["ranked"]]
            plot_note("retrodiction")
            svg(bars_svg([k + ("  ← documented ligand class" if k == r["truth"] else "") for k, _ in r["ranked"]], [v for _, v in r["ranked"]], "Model's ranking of ligand classes (blind)", f"{r['gene']} held out", colors=cols, fmt="{:.2f}"))
            (st.success if r["hit"] else st.warning)(f"The model's first choice was **{r['ranked'][0][0]}**; the documented class is **{r['truth']}**. " + ("Correct." if r["hit"] else f"The documented class ranked #{r.get('rank_of_truth') or 'not at all'}."))
        else:
            st.warning("The model abstained: nothing in the remaining cases resembled this receptor.")
        st.caption(eng.calibration_note())
    if a.wb is not None and len(a.wb.gpcrome.all_gpcr):
        row = a.wb.gpcrome.all_gpcr[a.wb.gpcrome.all_gpcr["GPCR"] == b.gene.upper()]
        if len(row):
            shown_any = True
            ro = a.wb.gpcrome.orphans[a.wb.gpcrome.orphans["GPCR"] == b.gene.upper()] if len(a.wb.gpcrome.orphans) else None
            st.markdown("**Learned from your matrix**")
            bits = [f"most expressed in **{row.iloc[0]['Most expressed in']}** (tau {row.iloc[0]['Specificity (tau)']:.2f})"]
            if ro is not None and len(ro):
                bits.append(f"predicted coupling: **{ro.iloc[0]['Predicted coupling']}**" + (f" from {ro.iloc[0]['Supported neighbours']}" if ro.iloc[0]["Predicted coupling"] != "no supported call" else ""))
            prog = a.wb.programs[(a.wb.programs["GPCR"] == b.gene.upper()) & (a.wb.programs["FDR"] <= 0.05)].sort_values("Pearson r (log)", ascending=False).head(2) if len(a.wb.programs) else None
            if prog is not None and len(prog):
                bits.append("tracks " + ", ".join(f"{r_['Program']} (r {r_['Pearson r (log)']:.2f})" for _, r_ in prog.iterrows()))
            st.markdown(" · ".join(bits))
    if not shown_any:
        if stt == "characterized":
            st.info(f"{b.gene} is not in the precedent library, so there is no blind test to run, and it is not an orphan, so there is nothing to deorphanise. "
                    "Load a matrix or the example case to see what the co-expression, enrichment and program analyses say about it.")
        elif not b.is_gpcr and stt == "":
            st.info("The pattern models cover GPCRs. For other proteins the evidence-ranked sections below (diseases, defects, variants) are the expectations.")
        else:
            st.info("No pattern-learned hypothesis applies yet. Load a matrix or the example case to add the analyses that learn from your data.")
