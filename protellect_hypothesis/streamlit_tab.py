"""Streamlit UI for the hypothesis engine. Call render_hypothesis_tab() from any page or tab."""
from __future__ import annotations

import pathlib

import pandas as pd
import streamlit as st

from .engine import HypothesisEngine
from .io_parsers import InputError, lookup_frame, parse_experiment
from .llm_debate import PROVIDERS, LLMError, available_providers, debate, make_llm
from .report import hypotheses_table, markdown_report, results_table
from .templates import GENERAL_RULES, NOT_SUPPORTED, SHAPES, template_csv

EXAMPLE = pathlib.Path(__file__).parent / "example_data" / "example_expression.csv"
EXAMPLE_CONTEXT = {"disease": "inflammatory bowel disease", "tissue": "colon biopsy", "comparison": "inflamed vs healthy tissue"}


@st.cache_resource(show_spinner=False)
def _engine_cached(registry_csv: str = "") -> HypothesisEngine:
    from .registry import load_registry_text
    return HypothesisEngine(registry=load_registry_text(registry_csv) if registry_csv else None)


def get_engine() -> HypothesisEngine:
    """The engine, using the full receptor registry if the user loaded one this session."""
    return _engine_cached(st.session_state.get("hyp_registry_csv", ""))


def _secret(name: str):
    """Read a key from Streamlit secrets, falling back to environment variables."""
    import os
    try:
        v = st.secrets.get(name)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name)


def _guide(eng: HypothesisEngine) -> None:
    st.subheader("1. What to upload")
    st.markdown("Upload the **processed result of an experiment you already ran**, in one of three shapes. "
                "Download a template to see the exact columns.")
    for key, s in SHAPES.items():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{s['label']}**  \nFrom: {s['from']}  \nRequired: {s['required']}  \nOptional: {s['optional']}")
            c2.download_button("Download template", template_csv(key), file_name=f"protellect_template_{key}.csv", key=f"hyp_tpl_{key}")
    st.markdown("**Rules for every file**")
    for rule in GENERAL_RULES:
        st.markdown(f"- {rule}")
    st.markdown("**Not supported**")
    for item in NOT_SUPPORTED:
        st.markdown(f"- {item}")

    st.subheader("2. Tell it the context")
    st.markdown("Disease or condition, tissue or cell type, and what was compared. The tissue you enter counts as evidence "
                "that the receptor is active there, so be accurate.")

    st.subheader("3. What you get back")
    st.markdown("- **A table, one row per orphan receptor**: top ligand-class hypothesis, relative support, critic verdict, "
                "likely coupling, and the first experiment to run.\n"
                "- **A hypothesis card per receptor**: ranked hypotheses for ligand class, signaling and a weak disease analogy, each "
                "with the reasoning, the historical precedents used, evidence flags, counter-arguments, and the lab test.\n"
                "- **Downloads**: a spreadsheet (CSV) of every hypothesis, and a readable report you can attach to notes or a grant draft.")
    st.markdown("**This is what that table looks like for the bundled example data** (fictional values):")
    summary = eng.run(parse_experiment(pd.read_csv(EXAMPLE)), EXAMPLE_CONTEXT)
    st.dataframe(results_table(summary), hide_index=True)
    st.caption("Receptors in the same tissue context with little annotation get similar hypotheses, as in this example. "
               "Each card says when that is the case. Adding family-cluster and neighbor annotations sharpens the differences.")
    st.markdown("**How to read the Critic column**")
    st.markdown("- :green[holds up]: few or no counter-arguments.\n"
                "- :orange[weakened]: one major or several minor counter-arguments.\n"
                "- :red[contested]: a refuted pairing, or two or more major counter-arguments.")
    st.subheader("What you will not get")
    st.markdown("- A confirmed ligand or function. Only a wet-lab experiment does that.\n"
                "- A probability. Relative support only ranks one receptor's candidates against each other.\n"
                "- Structural (binding-pocket) analysis. Not in this version.\n"
                "- A diagnosis or a validated biomarker. Diagnostic flags only say whether the signal could be worth investigating.")


def _run(eng: HypothesisEngine, source=None, source_label: str = "", defaults=None, lookup_gene=None,
         extra_annotations=None, kp: str = "hyp") -> None:
    """Context inputs, analysis, results table, downloads and cards.

    source: an already-loaded DataFrame to analyze (hides the uploader). lookup_gene: analyze one receptor by name,
    with no experiment. kp: prefix that keeps widget keys unique when embedded in a larger app.
    """
    d = defaults or {}
    c1, c2 = st.columns(2)
    disease = c1.text_input("Disease or condition", value=d.get("disease", ""), key=f"{kp}_disease", placeholder="e.g. inflammatory bowel disease")
    tissue = c2.text_input("Tissue or cell type", value=d.get("tissue", ""), key=f"{kp}_tissue", placeholder="e.g. colon biopsy")
    comparison = st.text_input("What was compared", value=d.get("comparison", ""), key=f"{kp}_comparison", placeholder="e.g. inflamed vs adjacent healthy tissue")

    parsed = None
    if lookup_gene:
        st.caption(f"Lookup mode for {lookup_gene}: no experiment is supplied, so no experimental signal is used. "
                   "Hypotheses rest on the receptor's annotation and the tissue/disease context above.")
        try:
            parsed = lookup_frame(lookup_gene)
        except InputError as e:
            st.error(str(e))
            return
    else:
        shape = st.selectbox("Data shape", ["auto-detect", "expression", "variant", "screen"], key=f"{kp}_shape")
        max_p = st.number_input("Keep only rows with p/adjusted p up to (0 = no filter)", 0.0, 1.0, 0.05, 0.01, key=f"{kp}_maxp")
        src = None
        if source is not None:
            src = source
            st.caption(f"Analyzing: {source_label or 'the data you already loaded'}")
        else:
            up = st.file_uploader("Upload your processed experiment (CSV or TSV)", type=["csv", "tsv", "txt"], key=f"{kp}_upload")
            use_example = st.button("Use example data", key=f"{kp}_example")
            if up is not None:
                src = pd.read_csv(up, sep=None, engine="python")
            elif use_example or st.session_state.get(f"{kp}_use_example"):
                st.session_state[f"{kp}_use_example"] = True
                src = pd.read_csv(EXAMPLE)
                st.caption("Showing the bundled example (fictional values).")
        if src is None:
            st.info("Upload a file, or click 'Use example data'. See the Guide tab for exactly what to upload.")
            return
        try:
            parsed = parse_experiment(src, None if shape == "auto-detect" else shape, max_p or None)
        except InputError as e:
            st.error(f"Could not read your file: {e}")
            return

    ctx = {"disease": disease, "tissue": tissue, "comparison": comparison}
    summary = eng.run(parsed, ctx, extra_annotations=extra_annotations)
    m1, m2, m3 = st.columns(3)
    m1.metric("Genes read", summary.n_input_genes)
    m2.metric("GPCRs found", summary.n_gpcr)
    m3.metric("Orphan GPCRs", summary.n_orphan)
    if summary.characterized:
        st.caption("Already-characterized GPCRs in your data (no hypotheses needed): " + ", ".join(summary.characterized))
    if summary.n_orphan == 0:
        n_orph = sum(v["status"] == "orphan" for v in eng.registry.values())
        st.success(f"No orphan GPCRs were found in this data. (The receptor registry currently recognizes {n_orph} orphan GPCRs"
                   + ("; load the full list to widen this." if n_orph < 50 else "."))
        return

    st.subheader("Results at a glance")
    st.dataframe(results_table(summary), hide_index=True)
    d1, d2 = st.columns(2)
    d1.download_button("Download all hypotheses (CSV)", hypotheses_table(summary).to_csv(index=False),
                       file_name="protellect_hypotheses.csv", mime="text/csv", key=f"{kp}_dl_csv")
    d2.download_button("Download report (Markdown)",
                       markdown_report(summary, ctx, eng.calibration_note(), eng.library_verified),
                       file_name="protellect_report.md", mime="text/markdown", key=f"{kp}_dl_md")

    providers = available_providers(_secret)
    chosen = None
    if providers:
        chosen = st.selectbox("AI debate provider (optional, runs only when you click a debate button)", providers,
                              format_func=lambda p: PROVIDERS[p]["label"], key=f"{kp}_provider")
    else:
        st.caption("AI debate is off: add GEMINI_API_KEY (free tier may apply) or ANTHROPIC_API_KEY to Streamlit secrets to enable it. "
                   "Everything else works without a key.")

    st.subheader("Hypothesis cards")
    for r in summary.results:
        sig = "" if r.significance is None else f", p = {r.significance:.3g}"
        sig_txt = r.effect_type if r.effect != r.effect else f"{r.effect_type}: {r.effect:.2f}{sig}"
        with st.expander(f"{r.gene}  ({sig_txt})", expanded=False):
            if r.status != "hypotheses":
                st.warning(r.message)
                continue
            if r.message:
                st.caption(r.message)
            for h in r.hypotheses:
                st.markdown(f"**{h.category.replace('-', ' ').title()}: {h.statement}**")
                st.progress(min(max(h.support, 0.0), 1.0), text=f"Relative support {h.support:.2f} (a ranking, not a probability)")
                st.markdown("**Why:** " + " | ".join(h.rationale))
                st.markdown("**Test it:** " + h.test_experiment)
                color = {"holds up": "green", "weakened": "orange", "contested": "red"}.get(h.verdict, "gray")
                n_c = len(h.counterarguments)
                st.markdown(f"**Critic:** :{color}[{h.verdict}] ({n_c} counter-argument{'s' if n_c != 1 else ''})")
                with st.popover("Evidence, flags and caveats"):
                    if h.counterarguments:
                        st.markdown("**Counter-arguments**")
                        for c in h.counterarguments:
                            st.markdown(f"- [{c['severity']}] {c['text']} _(source: {c['evidence']})_")
                    for k, v in h.evidence_axes.items():
                        st.markdown(f"- **{k.replace('_', ' ')}:** {v}")
                    for k, v in h.flags.items():
                        st.markdown(f"- **{k.replace('_', ' ')}:** {v}")
                    for cv in h.caveats:
                        st.markdown(f"- _{cv}_")
                st.divider()
            top = next((h for h in r.hypotheses if h.category == "ligand-class"), None)
            if top is not None and st.button(f"Run AI debate on the top {r.gene} hypothesis", key=f"{kp}_debate_{r.gene}"):
                try:
                    if chosen is None:
                        raise LLMError("No key found. Add GEMINI_API_KEY or ANTHROPIC_API_KEY to Streamlit secrets.")
                    out = debate(r.gene, top.to_dict(), {"disease": disease, "tissue": tissue}, make_llm(chosen, _secret))
                except LLMError as e:
                    out = {"note": f"AI debate unavailable: {e}", "reasons": [], "open_questions": [],
                           "final_verdict": top.verdict, "deterministic_verdict": top.verdict, "dropped": 0}
                st.markdown(f"**AI debate verdict:** {out['final_verdict']} (deterministic critic: {out['deterministic_verdict']})")
                for rs in out["reasons"]:
                    st.markdown(f"- {rs['text']} _(cites {', '.join(rs['cites'])})_")
                for q in out["open_questions"]:
                    st.markdown(f"- Open question (unverified, look it up): {q}")
                if out["note"]:
                    st.caption(out["note"])


def render_hypothesis_tab() -> None:
    st.header("Hypothesis Engine (beta)")
    st.info("Hypotheses, not answers. Every card shows its reasoning, and only a wet-lab experiment can confirm it. "
            "Structural similarity is not included in this version.")
    eng = get_engine()
    if not eng.library_verified:
        st.warning("The historical case library has not been expert-verified yet. Treat all rankings as illustrative.")
    st.caption(eng.calibration_note())
    guide_tab, run_tab = st.tabs(["Guide: what to upload and what you get", "Run an analysis"])
    with guide_tab:
        _guide(eng)
    with run_tab:
        _run(eng)
