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


def _coupling_ml_panel(a: Analysis) -> None:
    """Sequence-based coupling classifier. Tests itself on held-out subfamilies and shows predictions only if it passes."""
    import io
    import pandas as pd
    from ..coupling_ml import evaluate, predict_orphans
    from ..gpcrome import load_couplings
    b = a.b
    with st.expander("Sequence-based coupling classifier (it tests itself first)", expanded=False):
        st.caption("Learns G-protein coupling from loop lengths and composition (ICL2, ICL3, C-tail) and the DRY and NPxxY motifs of GPCR sequences. It is tested by holding out whole receptor "
                   "subfamilies, and a prediction is shown only if it beats guessing the most common class and shuffled labels. The built-in coupling table is small and unverified, so expect it to decline; "
                   "give it a larger verified table (CSV: gene, primary) to get a real test.")
        up = st.file_uploader("Verified coupling table (CSV: gene, primary = Gs / Gi / Gq / G12)", type=["csv"], key="cml_up")
        if st.button("Fetch sequences and run the test", key="cml_run"):
            import protellect_data as _pd
            with st.spinner("Fetching GPCR sequences from UniProt and running leave-subfamily-out testing..."):
                try:
                    labels = ({str(r["gene"]).upper(): str(r["primary"]) for _, r in pd.read_csv(io.BytesIO(up.getvalue())).iterrows()} if up is not None else load_couplings())
                    data = _pd.fetch_gpcr_sequences() if hasattr(_pd, "fetch_gpcr_sequences") else {}
                    if not data:
                        st.session_state["_cml"] = {"error": "Could not fetch GPCR sequences from UniProt (see the data audit on Overview for the last error)."}
                    else:
                        rep = evaluate(data, labels)
                        st.session_state["_cml"] = {"report": rep, "preds": predict_orphans(data, labels, [b.gene.upper()] if b.loaded else [], rep), "n_seq": len(data), "n_labels": len(labels)}
                except Exception as e:
                    st.session_state["_cml"] = {"error": f"{type(e).__name__}: {e}"}
        r = st.session_state.get("_cml")
        if not r:
            return
        if r.get("error"):
            st.warning(r["error"])
            return
        rep = r["report"]
        st.markdown(f"**Self-test:** {rep['n']} labelled receptors usable ({r['n_labels']} labels, {r['n_seq']} sequences fetched); classes: " + ", ".join(f"{k} {v}" for k, v in rep["classes"].items()))
        if "accuracy" in rep:
            st.dataframe([{"Held-out accuracy": f"{rep['accuracy'] * 100:.0f}%", "95% interval": f"{rep['ci95'][0] * 100:.0f}% to {rep['ci95'][1] * 100:.0f}%", "Always-guess-most-common": f"{rep['baseline'] * 100:.0f}%",
                           "Shuffled-label p": f"{rep['p_permutation']:.3f}", "Subfamilies held out": rep["n_groups"]}], hide_index=True)
            st.dataframe([{"Class": k, "Recall": f"{v * 100:.0f}%"} for k, v in rep["per_class_recall"].items()], hide_index=True)
        (st.success if rep["trusted"] else st.warning)(rep["reason"])
        for pr in r.get("preds", []):
            probs = ", ".join(f"{k} {v:.2f}" for k, v in sorted(pr["probabilities"].items(), key=lambda kv: -kv[1]))
            st.markdown(f"**{pr['gene']}:** predicted primary coupling **{pr['top']}** ({probs}). This passed its self-test, but it is a sequence-pattern estimate: test it with a G-protein-selective assay.")


def own_claims(a: Analysis):
    """Precedent hypotheses about the searched orphan itself; shown once, in the Pattern panel."""
    b = a.b
    if not b.loaded:
        return []
    return [c for c in a.hyp_claims if c.tags.get("category") in ("ligand-class", "signaling", "disease-analogy") and c.text.split(":")[0].upper() == b.gene.upper()]


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
        _coupling_ml_panel(a)
        return
    stt = _status(a)
    names = [b.gene] + [x for x in b.aliases if len(x) < 14]
    label = {"orphan": "orphan GPCR", "characterized": "characterised GPCR", "": "not in the receptor registry"}[stt if stt in ("orphan", "characterized") else ""]
    st.markdown(f"**{b.gene}** is a **{label}** per {st.session_state.get('_registry_label', 'the registry')}.")
    shown_any = False
    own = own_claims(a)
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
    _coupling_ml_panel(a)
