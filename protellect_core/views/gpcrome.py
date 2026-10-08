"""GPCRome analysis and the built-in test case, shown inside the Overview (one window).

One analysis is shown at a time (a selector, not nested expanders, because each claim card carries its own expander).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import example_case
from .. import candidates as cand
from ..alterations import label as alt_label, parse_alterations
from ..explain import plot_note
from ..network import bars_svg
from ..viz import communication_svg, gsea_svg, heatmap_svg
from ..engine.templates import template_csv
from ..enrichment import parse_coupling_table
from ..gpcrome import PATHWAYS, check_truth
from ..methods import methods_markdown
from ..repurpose import table as repurpose_table
from .common import render_claims, svg
from .shell import Analysis

VIEWS = ["Candidates: IO targets and orphans", "Signalling and specificity", "G-protein coupling enrichment", "Programs", "Oncocrine axes", "Pan-cancer alterations", "Methods and downloads"]


def _open_gene(gene: str) -> None:
    st.session_state["_pending_search_query"] = gene          # the app's own mechanism: fills the search box and runs the full analysis


def example_block(a: Analysis) -> None:
    ss = st.session_state
    with st.container(border=True):
        if not ss.get("example_loaded"):
            st.markdown("**Test it: load the example case.** A synthetic cancer-immune dataset (16 cell contexts, an exhausted-versus-effector T-cell contrast, marker programs, ligand producers and a pan-cancer table) "
                        "with known structure planted in invented numbers, so you can check the tool finds what is there and stays silent where nothing is. It is a software test, not biology.")
            st.button("Load the example case", key="ex_load", on_click=example_case.load_into_session, args=(ss,), type="primary")
        else:
            st.warning("**Synthetic example loaded.** Every expression value is invented to test the software; the receptors' couplings are curated annotations, not data from this set. Do not read it as a finding.")
            st.button("Clear the example", key="ex_clear", on_click=example_case.clear_session, args=(ss,))


def _read_upload(up, key):
    """Parse an upload once per file name; returns a DataFrame or None."""
    seen = st.session_state.setdefault("_gp_seen", {})
    if up is None or seen.get(key) == up.name:
        return None
    seen[key] = up.name
    try:
        return pd.read_csv(up, sep=None, engine="python")
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read {up.name}: {e}")
        return None


def _inputs(a: Analysis) -> None:
    ss = st.session_state
    with st.expander("Data and settings for this analysis", expanded=a.wb is None):
        c1, c2, c3 = st.columns(3)
        m = _read_upload(c1.file_uploader("Expression matrix (genes by cell types, tumours or conditions)", type=["csv", "tsv", "txt"], key="gp_up"), "matrix")
        co = _read_upload(c2.file_uploader("G-protein coupling table (optional)", type=["csv", "tsv", "txt"], key="gp_up_coup"), "coupling")
        al = _read_upload(c3.file_uploader("Pan-cancer alteration table (optional)", type=["csv", "tsv", "txt"], key="gp_up_alt"), "alt")
        d1, d2, d3 = st.columns(3)
        d1.download_button("Matrix template", template_csv("matrix"), file_name="protellect_template_matrix.csv", key="gp_tpl")
        d2.download_button("Coupling template", template_csv("coupling"), file_name="protellect_template_coupling.csv", key="gp_tpl_c")
        d3.download_button("Alteration template", template_csv("alterations"), file_name="protellect_template_alterations.csv", key="gp_tpl_a")
        changed = False
        if m is not None:
            ss["gpcrome_matrix"], changed = m, True
        if co is not None:
            try:
                ss["coupling_table"], ss["coupling_source"], changed = parse_coupling_table(co), "uploaded table", True
            except ValueError as e:
                st.error(str(e))
        if al is not None:
            try:
                ss["alterations"], changed = parse_alterations(al), True
            except ValueError as e:
                st.error(str(e))
        if a.matrix is not None:
            st.markdown("**Contrast** (which cell state to compare against the rest)")
            r1, r2 = st.columns([3, 2])
            r1.multiselect("Foreground contexts", list(a.matrix.columns), key="gp_fg", help="For example the exhausted T-cell column. All other contexts form the background.")
            r2.radio("Rank receptors by", ["auto", "table", "matrix"], key="gp_rank_source", horizontal=True,
                     format_func=lambda x: {"auto": "differential table if loaded, else matrix", "table": "differential table", "matrix": "matrix: foreground vs background"}[x])
            st.radio("Ranking metric (differential table)", ["log2fc", "signed_p"], key="gp_metric", horizontal=True, format_func=lambda x: {"log2fc": "fold-change", "signed_p": "sign x -log10(p)"}[x])
        st.markdown("**Your own marker program (optional)**")
        p1, p2 = st.columns([1, 3])
        p1.text_input("Name", key="gp_custom_name", placeholder="e.g. my signature")
        p2.text_area("Gene symbols (3 or more, separated by commas or lines)", key="gp_custom_genes", height=68)
        if changed:
            st.rerun()


def _metrics(a: Analysis) -> None:
    r, wb = a.gpcrome, a.wb
    n_orph = len(r.orphans)
    n_call = int((r.orphans["Predicted coupling"] != "no supported call").sum()) if n_orph else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Contexts", len(r.contexts)); m2.metric("GPCRs recognised", r.n_gpcr); m3.metric("Orphan GPCRs", n_orph); m4.metric("With a supported call", n_call)
    st.caption(f"Coupling table in use: {wb.coupling_source}")
    v = r.validation
    if v.get("ok"):
        good = v["beats_baseline"]
        (st.success if good else st.error)(f"**Self-test on your own data:** {v['note']} " + ("It beats the baseline, so its predictions are shown with their evidence." if good else "It does NOT beat the baseline here, so treat every prediction as unsupported."))
    else:
        st.warning(f"**Self-test not possible:** {v.get('note', '')} Predictions are marked accordingly.")


def _candidates(a: Analysis) -> None:
    plot_note("candidates")
    ss, wb = st.session_state, a.wb
    c1, c2 = st.columns([2, 3])
    direction = c1.radio("Prioritise receptors that are", ["up", "down", "either"], horizontal=True, key="cand_dir", format_func=lambda x: {"up": "higher in the foreground", "down": "lower", "either": "either"}[x])
    c2.caption("Every analysis on your data votes: change in the contrast, coupling-class enrichment, marker programs, cell-context specificity, oncocrine axes, pan-cancer alterations, and recorded drugs (after the lookup in the enrichment view).")
    drug_map = (ss.get("_repurpose") or {}).get("map") if ss.get("_repurpose") else None
    status = dict(zip(wb.gpcrome.all_gpcr["GPCR"], wb.gpcrome.all_gpcr["Status"]))
    hyp = {}
    for c in a.hyp_claims:
        if c.tags.get("category") == "ligand-class":
            hyp.setdefault(c.text.split(":")[0].upper(), c.text.split(": ", 1)[-1][:60])
    df = cand.rank(wb, status, ss.get("alterations"), drug_map, direction, hyp)
    if df.empty:
        st.info("Nothing to rank yet.")
        return
    show = [c for c in df.columns if not c.startswith("_")]
    cfg = {"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")}
    for title, mask, label in (("Immuno-oncology target candidates (characterised receptors)", df["Status"] != "orphan", "characterised"), ("Orphan receptors to deorphanise", df["Status"] == "orphan", "orphan")):
        sub = df[mask].reset_index(drop=True)
        st.markdown(f"**{title}**")
        if sub.empty:
            st.caption("None in this matrix.")
            continue
        st.dataframe(sub[show].head(20), hide_index=True, column_config=cfg)
        st.download_button(f"Download ({label})", sub[show].to_csv(index=False), f"protellect_candidates_{label}.csv", "text/csv", key=f"cand_dl_{label}")
        render_claims(cand.candidate_claims(sub, wb, label, 4), a.b, f"cand_{label}", limit=4, empty="No receptor has support from more than the baseline.")
    with st.expander("How the score is built (weights are design choices, shown in full)"):
        st.dataframe([{"Component": n, "Max points": p, "Rule": r} for n, p, r in cand.WEIGHTS], hide_index=True)
        st.caption("A component that could not be evaluated (for example drugs before the lookup, or alterations without a table) is left out of the denominator, not counted as zero. The score ranks receptors for follow-up; it is not a probability of success.")
    pick = st.selectbox("Open one in every tab", list(df["GPCR"]), key="cand_pick")
    if st.button("Analyse it", key="cand_open"):
        _open_gene(pick)
        st.rerun()                      # a full rerun: this one changes the whole page, unlike the view switches around it


def _signalling(a: Analysis) -> None:
    r, ss = a.gpcrome, st.session_state
    n_orph = len(r.orphans)
    if not n_orph:
        st.info("No orphan GPCRs were recognised in this matrix. Load the full receptor registry (below) so every orphan is recognised.")
    else:
        t = r.orphans.copy()
        alt = ss.get("alterations")
        if alt is not None:
            t["Pan-cancer alterations (>= 5%)"] = [alt_label(alt, g) for g in t["GPCR"]]
        t["_s"] = (t["Predicted coupling"] != "no supported call").astype(int) * 10 + t["Vote share"]
        st.markdown("**Orphan GPCRs, ranked**")
        st.dataframe(t.sort_values("_s", ascending=False).drop(columns="_s"), hide_index=True)
        st.download_button("Download this table (CSV)", t.drop(columns="_s").to_csv(index=False), "protellect_gpcrome_orphans.csv", "text/csv", key="gp_dl")
        st.markdown("**The evidence, with ML validation**")
        shown = render_claims(r.claims, a.b, "gpc", limit=8, empty="No orphan GPCR has a supported call or a strong specificity pattern in this matrix.")
        calls = sorted({c.tags.get("call") for c in shown if c.tags.get("call")})
        if calls:
            st.markdown("**What those couplings would mean for signalling** (textbook; verify before relying on it)")
            for k in calls:
                st.markdown(f"- **{k}:** {PATHWAYS[k]}")
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("Open one in every tab (structure, variants, drugs, genetics)", list(r.orphans["GPCR"]), key="gp_pick")
        c2.button("Analyse it", key="gp_open", on_click=_open_gene, args=(pick,))
    gp = r.all_gpcr
    if len(gp) and a.matrix is not None:
        plot_note("heatmap")
        svg(heatmap_svg(a.matrix, list(gp["GPCR"]), dict(zip(gp["GPCR"], gp["Status"])), a.wb.coupling, dict(zip(gp["GPCR"], gp["Specificity (tau)"]))))
    st.markdown("**Cell-type specificity of every GPCR**")
    only = st.checkbox("Show only context-specific GPCRs (tau >= 0.8)", value=True, key="gp_only")
    t = r.all_gpcr
    st.dataframe(t[t["Specific?"] == "yes"] if only else t, hide_index=True)
    st.caption("Tau runs from 0 (expressed evenly everywhere) to 1 (one context only). Yanai et al. 2005.")


def _drug_lookup(a: Analysis, genes, desired: str) -> None:
    ss = st.session_state
    try:
        import protellect_data as pdm
        fn = getattr(pdm, "fetch_dgidb_many", None)
    except Exception:  # noqa: BLE001
        fn = None
    if fn is None:
        st.info("Drug lookup needs the updated protellect_data.py (it adds fetch_dgidb_many).")
        return
    if st.button("Look up recorded drugs for these receptors", key="rp_go"):
        with st.spinner("Asking DGIdb..."):
            ss["_repurpose"] = {"genes": list(genes), "desired": desired, "map": fn(tuple(genes))}
    rp = ss.get("_repurpose")
    if rp:
        why = {g: f"leading edge of the {c.tags['class']} enrichment" for c in a.wb.enrich_claims for g in c.tags.get("lead", [])}
        t = repurpose_table(rp["genes"], rp["map"], rp["desired"], why)
        if not rp["map"]:
            st.warning("DGIdb returned nothing. Use 'Check data sources now' in the data audit to see why.")
        st.dataframe(t, hide_index=True, column_config={"Source": st.column_config.LinkColumn("Source")})
        st.caption("Recorded drug-gene interactions from DGIdb, filtered by the direction you chose. A record is not an approval or a recommendation: check approval status, dose and tissue exposure before any use.")


def _enrichment(a: Analysis) -> None:
    wb = a.wb
    e = wb.enrichment
    if e is None:
        st.info("To test which G-protein class dominates the receptors that change, load a differential table (sidebar, Your Experiment) or choose foreground contexts under 'Data and settings'.")
        return
    if e.table.empty:
        st.warning(e.note or "No coupling class could be tested.")
        return
    st.caption(f"Ranked by {wb.params.get('ranking')} · contrast: {wb.enrich_contrast} · {e.n_ranked} receptors ranked")
    st.dataframe(e.table.drop(columns=["_lead", "Direction"]), hide_index=True)
    plot_note("enrichment_bars")
    svg(bars_svg(list(e.table["Coupling class"]), [float(x) for x in e.table["NES"]], "Normalised enrichment score by coupling class", "positive: over-represented among receptors higher in the foreground", signed=True, fmt="{:+.2f}",
                 colors=["#34d399" if x >= 0 else "#fb7185" for x in e.table["NES"]]))
    sig_cls = [r_["Coupling class"] for _, r_ in e.table.iterrows() if r_["Significant"] == "yes"] or list(e.table["Coupling class"])
    pick_c = st.selectbox("Enrichment plot for", sig_cls, key="enr_plot_cls")
    plot_note("enrichment_curve")
    svg(gsea_svg(e, pick_c))
    st.caption("NES above 0: the class is over-represented among receptors higher in the foreground. Below 0: among those lower.")
    shown = render_claims(wb.enrich_claims, a.b, "enr", empty="No coupling class is significantly enriched (FDR <= 0.10) in this contrast.")
    leads = sorted({g for c in shown for g in c.tags.get("lead", [])})
    if leads:
        st.markdown("**Repurposing candidates for the leading-edge receptors**")
        sel = st.multiselect("Receptors", leads, default=leads[:12], key="rp_genes")
        desired = st.radio("Direction you want", ["inhibit", "activate"], horizontal=True, key="rp_dir",
                           help="For a class enriched where the receptors promote a harmful state you would usually look for inhibitors; the choice is yours.")
        if sel:
            _drug_lookup(a, sel, desired)


def _programs(a: Analysis) -> None:
    wb = a.wb
    if wb.programs.empty:
        st.info("None of the marker programs has at least 3 genes in this matrix.")
        return
    c1, c2 = st.columns([2, 1])
    prog = c1.selectbox("Program", ["All programs"] + wb.program_names, key="pg_sel")
    min_r = c2.slider("Minimum r", 0.0, 1.0, 0.5, 0.05, key="pg_r")
    t = wb.programs
    t = t[(t["Pearson r (log)"] >= min_r) & ((t["Program"] == prog) if prog != "All programs" else True)]
    plot_note("programs")
    top = t.sort_values("Pearson r (log)", ascending=False).head(12)
    if len(top):
        svg(bars_svg([f"{g} · {p}" for g, p in zip(top["GPCR"], top["Program"])], [float(x) for x in top["Pearson r (log)"]], "Receptor-program correlation across contexts", "Pearson r on log2(expression + 1); the table below has FDR", fmt="{:.2f}"))
    st.dataframe(t.head(60), hide_index=True)
    st.caption("Pearson correlation of log2(expression + 1) with the mean z-score of the program's marker genes across contexts. Association, not regulation. Marker lists are short curated sets, not validated signatures.")
    render_claims(wb.program_claims, a.b, "prg", limit=10, empty="No receptor tracks a program strongly enough (r >= 0.7, FDR <= 0.05).")


def _axes(a: Analysis) -> None:
    wb = a.wb
    if wb.axes.empty:
        st.info("No curated producer and receptor pair has both genes peaking (z >= 1) in some context of this matrix.")
        return
    plot_note("communication")
    svg(communication_svg(wb.axes, wb.coupling))
    st.dataframe(wb.axes, hide_index=True)
    st.caption("Producer expression stands in for ligand availability; secretion and receptor protein are not measured.")
    render_claims(wb.axis_claims, a.b, "ax", limit=8)


def _alterations(a: Analysis) -> None:
    alt = st.session_state.get("alterations")
    if alt is None:
        st.info("Upload a pan-cancer alteration table under 'Data and settings' (gene, cancer type, mutation / amplification / deletion frequency).")
        return
    status = dict(zip(a.gpcrome.all_gpcr["GPCR"], a.gpcrome.all_gpcr["Status"])) if len(a.gpcrome.all_gpcr) else {}
    t = alt[alt["gene"].isin(set(status))].copy()
    t["Status"] = t["gene"].map(status)
    t = t[(t[["mut", "amp", "del"]].max(axis=1) >= 0.05)].sort_values("amp", ascending=False)
    top = t.assign(m=t[["mut", "amp", "del"]].max(axis=1)).sort_values("m", ascending=False).head(12)
    if len(top):
        plot_note("alterations")
        svg(bars_svg([f"{g} · {c}" for g, c in zip(top["gene"], top["cancer"])], [float(x) * 100 for x in top["m"]], "Highest alteration frequency per receptor and cancer type", "% of tumours (mutated, amplified or deleted, whichever is highest)", fmt="{:.0f}%"))
    st.dataframe(t.rename(columns={"gene": "GPCR", "cancer": "Cancer type", "mut": "Mutated", "amp": "Amplified", "del": "Deleted"}), hide_index=True)
    st.caption("From your own table, unchanged. Only receptors in the matrix with a frequency of at least 5% are shown.")


def _methods(a: Analysis) -> None:
    wb = a.wb
    try:
        from .common import get_engine
        n_reg = len(get_engine().registry)
    except Exception:  # noqa: BLE001
        n_reg = 0
    md = methods_markdown(wb, (a.matrix.shape[0], a.matrix.shape[1]), list(a.matrix.columns), n_reg, st.session_state.get("alterations") is not None)
    st.markdown("**Methods paragraph for the analyses you ran** (parameters are filled in from this run)")
    st.markdown(md)
    st.download_button("Download methods (markdown)", md, "protellect_methods.md", key="gp_methods")


_fragment = getattr(st, "fragment", None) or (lambda f: f)      # older Streamlit: no fragments, everything simply reruns


@_fragment
def _views(a: Analysis) -> None:
    """Switching views or changing a selector in here re-renders only this block, so the rest of the page (and your scroll position) stays put."""
    view = st.radio("Analysis", VIEWS, horizontal=True, key="gp_view")
    {"Candidates: IO targets and orphans": _candidates, "Signalling and specificity": _signalling, "G-protein coupling enrichment": _enrichment, "Programs": _programs, "Oncocrine axes": _axes,
     "Pan-cancer alterations": _alterations, "Methods and downloads": _methods}[view](a)


def render_gpcrome(a: Analysis) -> None:
    ss = st.session_state
    st.markdown("#### GPCRome analysis (ML): where each GPCR is active, what it tracks, and what dominates a cell state")
    _inputs(a)
    if a.gpcrome_error:
        st.error(a.gpcrome_error)
        return
    if a.gpcrome is None or a.wb is None:
        st.info("Upload a matrix, or load the example case above, to see cell-type specificity, signalling predictions, coupling enrichment, programs and oncocrine axes.")
        return
    if a.gpcrome.skipped:
        st.warning(a.gpcrome.skipped)
        return
    _metrics(a)
    _views(a)
    if ss.get("example_loaded"):
        chk = check_truth(a.gpcrome, example_case.truth(), a.wb)
        ok = sum(c["ok"] for c in chk)
        with st.expander(f"Software self-check against the planted answers: {ok} of {len(chk)} recovered", expanded=ok != len(chk)):
            st.dataframe([{"Planted answer": c["check"], "Tool said": c["got"], "Recovered": "yes" if c["ok"] else "NO"} for c in chk], hide_index=True)
            st.caption("This only shows the software can find structure that was put there. To test it on real biology, aggregate a public tumour single-cell atlas to one column per cell type "
                       "(for example GSE103322, a head and neck atlas; check the accession) and upload that matrix.")
